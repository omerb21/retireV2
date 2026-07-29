from __future__ import annotations

import asyncio
import gc
import io
import importlib.util
import os
import stat
import subprocess
import zipfile
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import CreateTable

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.m02_intake import (
    M02IntakeRecord,
    M02PreservedBlob,
    M02PreservedSource,
)
from app.services.m02_storage import (
    MAX_FILE_BYTES,
    M02FileError,
    M02StorageConfigurationError,
    M02StorageCleanupError,
    M02OwnedReader,
    ManagedLocalStorage,
    StagedResourceState,
    StagedUpload,
    _DirectoryHandleKind,
    _TrustedDirectory,
    _WindowsDirectoryApi,
    _validate_text,
)


PARENT_REVISION = "f3a7c9d2e610"
PKG007_REVISION = "b6d8e2f4a701"
ACTOR = "system:m02-intake:M02 intake workflow"


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_alembic(db_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    return subprocess.run(
        ["alembic", *args],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        check=True,
        text=True,
    )


@pytest.fixture
def api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[tuple[TestClient, sessionmaker[Session], Path], None, None]:
    storage_root = tmp_path / "managed-m02"
    monkeypatch.setenv("M02_STORAGE_ROOT", str(storage_root.resolve()))
    load_all_models()
    engine = create_engine(f"sqlite:///{tmp_path / 'pkg007.db'}")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, expire_on_commit=False)
    with session_local() as session:
        session.add_all(
            [
                Client(client_id=1, display_name="One", id_number="001"),
                Client(client_id=2, display_name="Two", id_number="002"),
            ]
        )
        session.commit()

    def override_get_db():
        with session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), session_local, storage_root
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _manual_payload(**overrides) -> dict:
    payload = {
        "declared_provider_name": None,
        "product_name": "Declared fund",
        "product_identifier": None,
        "declared_account_reference": None,
        "declared_total_balance_amount": "1000.25",
        "declared_monthly_pension_amount": "10.50",
        "declared_component_values": [
            {"label": "opaque component", "value": "12.340"}
        ],
        "declared_statement_date": "2026-01-01",
        "declared_start_date": "2001-01-01",
        "declared_product_type": "declared only",
        "source_type": "manual",
        "declared_basis": "user declaration",
        "notes": "not verified",
    }
    payload.update(overrides)
    return payload


def _upload(
    client: TestClient,
    client_id: int,
    files: list[tuple[str, bytes, str]],
    **metadata,
):
    form = {
        "source_type": "clearinghouse",
        "declared_provider_name": "Provider",
        "product_name": "Fund",
        "declared_account_reference": "Declared-1",
        **metadata,
    }
    return client.post(
        f"/api/clients/{client_id}/m02/intakes/upload",
        data=form,
        files=[("files", (name, content, mime)) for name, content, mime in files],
    )


def _xlsx_bytes(*, unsafe: bool = False, macro: bool = False) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml"/>'
                if macro
                else '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            )
            + "</Types>",
        )
        archive.writestr("xl/workbook.xml", "<workbook/>")
        if unsafe:
            archive.writestr("../escape.txt", "no")
        if macro:
            archive.writestr("xl/vbaProject.bin", b"macro")
    return stream.getvalue()


def test_manual_intake_is_declared_only_and_uses_server_provenance(api) -> None:
    client, session_local, storage_root = api

    response = client.post(
        "/api/clients/1/m02/intakes/manual", json=_manual_payload()
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["lifecycle_status"] == "metadata_review"
    assert body["preservation_status"] == "not_applicable"
    assert body["source"] is None
    assert body["declared_start_date"] == "2001-01-01"
    assert body["declared_product_type"] == "declared only"
    assert body["manual_technical_reference"].startswith("M02-MANUAL-")
    assert body["manual_technical_reference_is_account"] is False
    assert body["created_by_actor"] == ACTOR
    assert body["actor_is_authentication"] is False
    assert body["diagnostics"] == [
        "M02_PROVIDER_MISSING",
        "M02_DECLARED_ACCOUNT_MISSING",
    ]
    assert "accepted_for_review" in body["allowed_lifecycle_targets"]
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM pension_holding")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM m07_evidence_revisions")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM fixation_runs")) == 0


def test_manual_missing_product_blocks_review_but_not_save(api) -> None:
    client, _, _ = api
    created = client.post(
        "/api/clients/1/m02/intakes/manual",
        json=_manual_payload(
            product_name=None,
            product_identifier=None,
            declared_product_type=None,
        ),
    )
    assert created.status_code == 201
    assert "M02_PRODUCT_IDENTITY_MISSING" in created.json()["diagnostics"]

    blocked = client.post(
        f"/api/clients/1/m02/intakes/{created.json()['intake_id']}/lifecycle",
        json={"target_status": "accepted_for_review"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "M02_METADATA_INCOMPLETE"


def test_manual_metadata_update_is_atomic_and_terminal_is_read_only(api) -> None:
    client, _, _ = api
    row = client.post(
        "/api/clients/1/m02/intakes/manual", json=_manual_payload()
    ).json()
    updated = client.put(
        f"/api/clients/1/m02/intakes/{row['intake_id']}",
        json={"product_name": " Corrected ", "source_type": "manual-corrected"},
    )
    assert updated.status_code == 200
    assert updated.json()["product_name"] == "Corrected"
    accepted = client.post(
        f"/api/clients/1/m02/intakes/{row['intake_id']}/lifecycle",
        json={"target_status": "accepted_for_review"},
    )
    assert accepted.status_code == 200
    locked = client.put(
        f"/api/clients/1/m02/intakes/{row['intake_id']}",
        json={"product_name": "Not allowed"},
    )
    assert locked.status_code == 409
    reopened = client.post(
        f"/api/clients/1/m02/intakes/{row['intake_id']}/lifecycle",
        json={"target_status": "metadata_review"},
    )
    assert reopened.status_code == 200


@pytest.mark.parametrize(
    ("name", "content", "mime", "encoding"),
    [
        ("source.pdf", b"%PDF-1.7\nopaque", "application/pdf", None),
        ("source.xml", "<x>שלום</x>".encode("utf-8"), "application/xml", "utf-8"),
        ("source.dat", "שלום".encode("cp1255"), "application/octet-stream", "windows-1255"),
        ("source.csv", b"\xef\xbb\xbfcol\nvalue", "text/csv", "utf-8-bom"),
        (
            "source.xlsx",
            _xlsx_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            None,
        ),
    ],
)
def test_every_allowed_opaque_type_is_preserved_without_parsing(
    api, name: str, content: bytes, mime: str, encoding: str | None
) -> None:
    client, _, storage_root = api
    response = _upload(client, 1, [(name, content, mime)])

    assert response.status_code == 200, response.text
    result = response.json()["results"][0]
    assert result["status"] == "preserved"
    intake = result["intake"]
    assert intake["lifecycle_status"] == "uploaded"
    assert intake["source"]["detected_text_encoding"] == encoding
    assert intake["source"]["byte_size"] == len(content)
    assert len(intake["source"]["sha256_checksum"]) == 64
    stored_files = [
        path
        for path in storage_root.rglob("*")
        if path.is_file() and ".temporary" not in path.parts
    ]
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == content


@pytest.mark.parametrize(
    ("name", "content", "mime", "code"),
    [
        ("bad.exe", b"not executable", "application/octet-stream", "M02_UNSUPPORTED_EXTENSION"),
        ("empty.pdf", b"", "application/pdf", "M02_EMPTY_FILE"),
        ("bad.pdf", b"not pdf", "application/pdf", "M02_SIGNATURE_MISMATCH"),
        ("wrong.pdf", b"%PDF-1.7", "text/plain", "M02_MIME_MISMATCH"),
        ("nul.dat", b"abc\x00def", "text/plain", "M02_UNSUPPORTED_BINARY_TEXT"),
        (
            "unsafe.xlsx",
            _xlsx_bytes(unsafe=True),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "M02_INVALID_OOXML_CONTAINER",
        ),
        (
            "macro.xlsx",
            _xlsx_bytes(macro=True),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "M02_INVALID_OOXML_CONTAINER",
        ),
    ],
)
def test_invalid_files_fail_per_file_without_rows_or_orphans(
    api, name: str, content: bytes, mime: str, code: str
) -> None:
    client, session_local, storage_root = api
    response = _upload(client, 1, [(name, content, mime)])
    assert response.status_code == 200
    assert response.json()["results"][0]["error_code"] == code
    with session_local() as session:
        assert session.scalar(select(M02IntakeRecord).limit(1)) is None
        assert session.scalar(select(M02PreservedSource).limit(1)) is None
        assert session.scalar(select(M02PreservedBlob).limit(1)) is None
    assert not [path for path in storage_root.rglob("*") if path.is_file()]


def test_mixed_batch_commits_success_and_retains_separate_failure(api) -> None:
    client, session_local, _ = api
    response = _upload(
        client,
        1,
        [
            ("good.pdf", b"%PDF-good", "application/pdf"),
            ("bad.pdf", b"bad", "application/pdf"),
            ("data.dat", b"opaque text", "text/plain"),
        ],
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert [result["status"] for result in results] == [
        "preserved",
        "failed",
        "preserved",
    ]
    assert [result["selection_index"] for result in results] == [0, 1, 2]
    assert response.json()["request_error"] is None
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 2
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 2


def test_exact_size_limit_is_accepted_and_one_byte_over_is_rejected(api) -> None:
    client, _, _ = api
    accepted_content = b"%PDF-" + (b"a" * (MAX_FILE_BYTES - 5))
    accepted = _upload(
        client, 1, [("limit.pdf", accepted_content, "application/pdf")]
    )
    assert accepted.status_code == 200
    assert accepted.json()["results"][0]["status"] == "preserved"
    assert (
        accepted.json()["results"][0]["intake"]["source"]["byte_size"]
        == MAX_FILE_BYTES
    )

    rejected_content = b"%PDF-" + (b"a" * (MAX_FILE_BYTES - 4))
    rejected = _upload(
        client, 1, [("over.pdf", rejected_content, "application/pdf")]
    )
    assert rejected.status_code == 200
    assert rejected.json()["results"][0]["error_code"] == "M02_FILE_TOO_LARGE"


def test_storage_failure_retains_only_safe_failed_intake(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, _ = api

    def fail_place(_self, _temporary_path):
        raise M02FileError(
            "M02_PRESERVATION_FAILED", "The source could not be preserved"
        )

    monkeypatch.setattr(
        "app.services.m02_storage.ManagedLocalStorage.place", fail_place
    )
    response = _upload(
        client, 1, [("valid.pdf", b"%PDF-valid", "application/pdf")]
    )
    result = response.json()["results"][0]
    assert result["status"] == "failed"
    assert result["error_code"] == "M02_PRESERVATION_FAILED"
    assert result["intake"]["preservation_status"] == "failed"
    assert result["intake"]["source"] is None
    assert result["intake"]["preservation_failure_code"] == "M02_PRESERVATION_FAILED"
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 1
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 0


def test_request_level_failure_is_distinct_and_keeps_prior_commit(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, storage_root = api
    import app.api.m02_intake_routes as routes

    original = routes.preserve_staged_upload
    call_count = 0

    def fail_second(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("request framework interrupted")
        return original(*args, **kwargs)

    monkeypatch.setattr(routes, "preserve_staged_upload", fail_second)
    response = _upload(
        client,
        1,
        [
            ("committed.pdf", b"%PDF-first", "application/pdf"),
            ("uncommitted.pdf", b"%PDF-second", "application/pdf"),
        ],
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1
    assert response.json()["results"][0]["status"] == "preserved"
    assert response.json()["request_error"] == {
        "code": "M02_BATCH_REQUEST_FAILED",
        "message": "The upload request could not be completed",
    }
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 1
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 1
    assert not [
        path
        for path in storage_root.rglob(".temporary/*")
        if path.is_file()
    ]
    assert len(
        [
            path
            for path in storage_root.rglob("*")
            if path.is_file() and ".temporary" not in path.parts
        ]
    ) == 1


def test_same_client_duplicate_reuses_blob_but_cross_client_does_not(api) -> None:
    client, session_local, storage_root = api
    content = b"%PDF-identical"
    first = _upload(client, 1, [("one.pdf", content, "application/pdf")]).json()[
        "results"
    ][0]["intake"]
    second = _upload(client, 1, [("two.pdf", content, "application/pdf")]).json()[
        "results"
    ][0]["intake"]
    other = _upload(client, 2, [("three.pdf", content, "application/pdf")]).json()[
        "results"
    ][0]["intake"]

    assert first["duplicate_candidate"] is False
    assert second["duplicate_candidate"] is True
    assert second["duplicate_of_intake_id"] == first["intake_id"]
    assert other["duplicate_candidate"] is False
    assert other["duplicate_of_intake_id"] is None
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 3
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 3
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 2
    assert len(
        [
            path
            for path in storage_root.rglob("*")
            if path.is_file() and ".temporary" not in path.parts
        ]
    ) == 2


def test_same_batch_duplicate_reuses_one_blob_and_keeps_both_sources(api) -> None:
    client, session_local, storage_root = api
    content = b"%PDF-same-batch"
    response = _upload(
        client,
        1,
        [
            ("first.pdf", content, "application/pdf"),
            ("second.pdf", content, "application/pdf"),
        ],
    )
    assert response.status_code == 200
    intakes = [result["intake"] for result in response.json()["results"]]
    assert [item["duplicate_candidate"] for item in intakes] == [False, True]
    assert intakes[1]["duplicate_of_intake_id"] == intakes[0]["intake_id"]
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 1
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 2
    assert len(
        [
            path
            for path in storage_root.rglob("*")
            if path.is_file() and ".temporary" not in path.parts
        ]
    ) == 1


def test_cleanup_failure_preserves_already_committed_file_result(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, _ = api
    def fail_cleanup(self, *, primary_error=None):
        raise M02StorageCleanupError(
            "injected cleanup failure",
            primary_error=primary_error,
            cleanup_errors=(OSError("injected OS cleanup failure"),),
        )

    monkeypatch.setattr(StagedUpload, "cleanup", fail_cleanup)
    response = _upload(
        client, 1, [("cleanup.pdf", b"%PDF-cleanup", "application/pdf")]
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["status"] == "preserved"
    assert body["request_error"] == {
        "code": "M02_STORAGE_CLEANUP_FAILED",
        "message": "Managed upload cleanup could not be completed",
    }
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 1
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 1


def test_superseding_candidate_requires_newer_same_source_and_explicit_transition(api) -> None:
    client, _, _ = api
    older = client.post(
        "/api/clients/1/m02/intakes/manual",
        json=_manual_payload(declared_statement_date="2025-01-01"),
    ).json()
    accepted = client.post(
        f"/api/clients/1/m02/intakes/{older['intake_id']}/lifecycle",
        json={"target_status": "accepted_for_review"},
    )
    assert accepted.status_code == 200
    equal = client.post(
        "/api/clients/1/m02/intakes/manual",
        json=_manual_payload(declared_statement_date="2025-01-01"),
    ).json()
    different = client.post(
        "/api/clients/1/m02/intakes/manual",
        json=_manual_payload(
            source_type="other", declared_statement_date="2026-01-01"
        ),
    ).json()
    newer = client.post(
        "/api/clients/1/m02/intakes/manual",
        json=_manual_payload(declared_statement_date="2026-01-01"),
    ).json()
    assert equal["superseding_candidate"] is False
    assert different["superseding_candidate"] is False
    assert newer["superseding_candidate"] is True
    assert newer["superseding_intake_id"] == older["intake_id"]
    still_accepted = client.get(
        f"/api/clients/1/m02/intakes/{older['intake_id']}"
    ).json()
    assert still_accepted["lifecycle_status"] == "accepted_for_review"
    superseded = client.post(
        f"/api/clients/1/m02/intakes/{older['intake_id']}/lifecycle",
        json={"target_status": "superseded"},
    )
    assert superseded.status_code == 200


@pytest.mark.parametrize(
    ("start", "target"),
    [
        ("uploaded", "metadata_review"),
        ("uploaded", "rejected"),
        ("metadata_review", "accepted_for_review"),
        ("metadata_review", "rejected"),
        ("accepted_for_review", "metadata_review"),
        ("accepted_for_review", "rejected"),
    ],
)
def test_locked_lifecycle_transitions(api, start: str, target: str) -> None:
    client, session_local, _ = api
    row = client.post(
        "/api/clients/1/m02/intakes/manual", json=_manual_payload()
    ).json()
    with session_local() as session:
        persisted = session.get(M02IntakeRecord, row["intake_id"])
        persisted.lifecycle_status = start
        if start == "uploaded":
            persisted.record_kind = "uploaded_source"
            persisted.manual_technical_reference = None
            persisted.preservation_status = "preserved"
            persisted.declared_provider_name = "Provider"
            persisted.declared_account_reference = "Account"
        session.commit()
    payload = {"target_status": target}
    if target == "rejected":
        payload["rejection_reason_code"] = "USER_REJECTED"
    response = client.post(
        f"/api/clients/1/m02/intakes/{row['intake_id']}/lifecycle", json=payload
    )
    assert response.status_code == 200, response.text


def test_same_state_skipped_and_terminal_transitions_fail_safely(api) -> None:
    client, _, _ = api
    row = client.post(
        "/api/clients/1/m02/intakes/manual", json=_manual_payload()
    ).json()
    same = client.post(
        f"/api/clients/1/m02/intakes/{row['intake_id']}/lifecycle",
        json={"target_status": "metadata_review"},
    )
    skipped = client.post(
        f"/api/clients/1/m02/intakes/{row['intake_id']}/lifecycle",
        json={"target_status": "superseded"},
    )
    rejected = client.post(
        f"/api/clients/1/m02/intakes/{row['intake_id']}/lifecycle",
        json={"target_status": "rejected", "rejection_reason_code": "USER_REJECTED"},
    )
    terminal = client.post(
        f"/api/clients/1/m02/intakes/{row['intake_id']}/lifecycle",
        json={"target_status": "metadata_review"},
    )
    assert same.status_code == skipped.status_code == terminal.status_code == 409
    assert rejected.status_code == 200


def test_client_isolation_and_attachment_download(api) -> None:
    client, _, _ = api
    intake = _upload(
        client, 1, [("report.pdf", b"%PDF-private", "application/pdf")]
    ).json()["results"][0]["intake"]
    source_id = intake["source"]["source_id"]

    foreign_intake = client.get(f"/api/clients/2/m02/intakes/{intake['intake_id']}")
    foreign_source = client.get(
        f"/api/clients/2/m02/sources/{source_id}/download"
    )
    download = client.get(f"/api/clients/1/m02/sources/{source_id}/download")

    assert foreign_intake.status_code == foreign_source.status_code == 404
    assert foreign_intake.json()["detail"] == foreign_source.json()["detail"]
    assert download.status_code == 200
    assert download.content == b"%PDF-private"
    assert download.headers["x-content-type-options"] == "nosniff"
    assert download.headers["content-disposition"].startswith("attachment;")
    assert "objects/" not in download.headers["content-disposition"]


def test_no_delete_or_preview_routes_exist(api) -> None:
    client, _, _ = api
    row = client.post(
        "/api/clients/1/m02/intakes/manual", json=_manual_payload()
    ).json()
    assert (
        client.delete(f"/api/clients/1/m02/intakes/{row['intake_id']}").status_code
        == 405
    )
    assert (
        client.get(f"/api/clients/1/m02/intakes/{row['intake_id']}/preview").status_code
        == 404
    )


def test_storage_configuration_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("M02_STORAGE_ROOT", raising=False)
    from app.services.m02_storage import (
        M02StorageConfigurationError,
        ManagedLocalStorage,
    )

    with pytest.raises(M02StorageConfigurationError) as error:
        ManagedLocalStorage.from_environment()
    assert error.value.code == "M02_STORAGE_CONFIGURATION_BLOCKED"


def test_upload_route_returns_stable_storage_error_without_managed_path(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _, _ = api

    def fail_storage(_cls):
        raise M02StorageConfigurationError(
            "private path C:/managed/customer-storage is unavailable"
        )

    monkeypatch.setattr(
        ManagedLocalStorage,
        "from_environment",
        classmethod(fail_storage),
    )
    response = _upload(
        client, 1, [("source.pdf", b"%PDF-source", "application/pdf")]
    )
    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "M02_STORAGE_UNAVAILABLE",
        "message": "Managed source storage is unavailable",
    }
    assert "customer-storage" not in response.text


def test_managed_directory_open_normalizes_not_a_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.m02_storage as storage_module

    target = tmp_path / "managed"
    monkeypatch.setattr(
        storage_module.os,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            NotADirectoryError("private managed path")
        ),
    )
    with pytest.raises(M02StorageConfigurationError) as error:
        _TrustedDirectory._open_posix(target)
    assert isinstance(error.value.__cause__, NotADirectoryError)
    assert "private managed path" not in str(error.value)


class _FakeWindowsDirectoryApi:
    def __init__(
        self,
        openings: list[tuple[int, int, tuple[int, int]] | BaseException],
        close_error: BaseException | None = None,
    ) -> None:
        self.openings = list(openings)
        self.closed: list[int] = []
        self.close_error = close_error

    def open_directory(self, _path: Path) -> tuple[int, int, tuple[int, int]]:
        value = self.openings.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    def close_handle(self, handle: int) -> None:
        self.closed.append(handle)
        if self.close_error is not None:
            raise self.close_error


def test_windows_directory_contract_uses_pinned_non_reparse_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.m02_storage as storage_module

    posix_closes: list[int] = []
    monkeypatch.setattr(storage_module.os, "close", posix_closes.append)
    arguments = _WindowsDirectoryApi.create_file_arguments(Path("managed"))
    assert arguments[1] == _WindowsDirectoryApi.GENERIC_READ
    assert arguments[2] == _WindowsDirectoryApi.SHARE_READ_WRITE
    assert (
        arguments[5] & _WindowsDirectoryApi.FILE_FLAG_OPEN_REPARSE_POINT
    ) != 0
    assert (
        arguments[5] & _WindowsDirectoryApi.FILE_FLAG_BACKUP_SEMANTICS
    ) != 0

    api = _FakeWindowsDirectoryApi(
        [(77, _WindowsDirectoryApi.FILE_ATTRIBUTE_DIRECTORY, (4, 9))]
    )
    directory = _TrustedDirectory._open_windows(Path("managed"), api=api)
    assert directory._handle == 77
    assert directory.identity == (4, 9)
    directory.close()
    directory.close()
    assert api.closed == [77]
    assert posix_closes == []


def test_windows_directory_rejects_reparse_and_closes_handle() -> None:
    api = _FakeWindowsDirectoryApi(
        [
            (
                88,
                _WindowsDirectoryApi.FILE_ATTRIBUTE_DIRECTORY
                | _WindowsDirectoryApi.FILE_ATTRIBUTE_REPARSE_POINT,
                (4, 10),
            )
        ]
    )
    with pytest.raises(M02StorageConfigurationError):
        _TrustedDirectory._open_windows(Path("managed"), api=api)
    assert api.closed == [88]


def test_windows_directory_identity_mismatch_is_typed_and_closes_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.m02_storage as storage_module

    pinned_api = _FakeWindowsDirectoryApi([])
    directory = _TrustedDirectory(
        Path("managed"), 70, (5, 11), windows_api=pinned_api
    )
    probe_api = _FakeWindowsDirectoryApi(
        [(71, _WindowsDirectoryApi.FILE_ATTRIBUTE_DIRECTORY, (5, 12))]
    )
    monkeypatch.setattr(storage_module, "_windows_directory_api", lambda: probe_api)
    with pytest.raises(M02StorageConfigurationError, match="identity changed"):
        directory._verify_windows_path_identity()
    assert probe_api.closed == [71]
    assert directory.identity == (5, 11)
    directory.close()
    assert pinned_api.closed == [70]


def test_windows_identity_mismatch_preserves_primary_when_close_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.m02_storage as storage_module

    directory = _TrustedDirectory(
        Path("managed"),
        70,
        (5, 11),
        windows_api=_FakeWindowsDirectoryApi([]),
    )
    probe_api = _FakeWindowsDirectoryApi(
        [(71, _WindowsDirectoryApi.FILE_ATTRIBUTE_DIRECTORY, (5, 12))],
        close_error=OSError("injected close failure"),
    )
    monkeypatch.setattr(storage_module, "_windows_directory_api", lambda: probe_api)
    with pytest.raises(M02StorageConfigurationError, match="identity changed") as error:
        directory._verify_windows_path_identity()
    assert probe_api.closed == [71]
    assert any("Secondary managed-directory close failure" in note for note in error.value.__notes__)


def test_windows_directory_api_failure_is_typed_without_path_disclosure() -> None:
    api = _FakeWindowsDirectoryApi([PermissionError("C:/private/managed")])
    with pytest.raises(M02StorageConfigurationError) as error:
        _TrustedDirectory._open_windows(Path("C:/private/managed"), api=api)
    assert isinstance(error.value.__cause__, PermissionError)
    assert "C:/private/managed" not in str(error.value)
    assert api.closed == []


@pytest.mark.parametrize(
    "failure",
    [
        PermissionError("allocation failed"),
        RuntimeError("open function failed"),
        ValueError("argument preparation failed"),
    ],
)
def test_windows_pre_acquisition_failures_never_close_or_fallback(
    failure: BaseException, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.m02_storage as storage_module

    api = _FakeWindowsDirectoryApi([failure])
    posix_closes: list[int] = []
    monkeypatch.setattr(storage_module.os, "close", posix_closes.append)
    with pytest.raises(M02StorageConfigurationError) as error:
        _TrustedDirectory._open_windows(Path("managed"), api=api)
    assert error.value.__cause__ is failure
    assert api.closed == []
    assert posix_closes == []
    assert not getattr(error.value, "__notes__", ())


def test_windows_invalid_handle_sentinel_is_never_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.m02_storage as storage_module

    api = _FakeWindowsDirectoryApi(
        [(-1, _WindowsDirectoryApi.FILE_ATTRIBUTE_DIRECTORY, (0, 0))]
    )
    posix_closes: list[int] = []
    monkeypatch.setattr(storage_module.os, "close", posix_closes.append)
    with pytest.raises(M02StorageConfigurationError):
        _TrustedDirectory._open_windows(Path("managed"), api=api)
    assert api.closed == []
    assert posix_closes == []


def test_posix_directory_close_uses_descriptor_backend_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.m02_storage as storage_module

    posix_closes: list[int] = []
    windows_api = _FakeWindowsDirectoryApi([])
    monkeypatch.setattr(storage_module.os, "close", posix_closes.append)
    directory = _TrustedDirectory(
        Path("managed"),
        41,
        (2, 3),
        windows_api=windows_api,
        handle_kind=_DirectoryHandleKind.POSIX,
    )
    directory.close()
    directory.close()
    assert posix_closes == [41]
    assert windows_api.closed == []


class _DirectoryStat:
    st_mode = stat.S_IFDIR | 0o700
    st_dev = 7
    st_ino = 19


def test_posix_root_fstat_failure_closes_descriptor_once_and_preserves_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.m02_storage as storage_module

    closed: list[int] = []
    primary = OSError("injected fstat failure")
    monkeypatch.setattr(storage_module.os, "open", lambda *_args, **_kwargs: 51)
    monkeypatch.setattr(
        storage_module.os,
        "fstat",
        lambda _fd: (_ for _ in ()).throw(primary),
    )
    monkeypatch.setattr(storage_module.os, "close", closed.append)
    with pytest.raises(M02StorageConfigurationError) as error:
        _TrustedDirectory._open_posix(Path("managed"))
    assert error.value.__cause__ is primary
    assert closed == [51]


def test_posix_child_fstat_failure_closes_child_but_not_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.m02_storage as storage_module

    closed: list[int] = []
    primary = OSError("injected child fstat failure")
    parent = _TrustedDirectory(
        Path("managed"),
        60,
        (7, 18),
        handle_kind=_DirectoryHandleKind.POSIX,
    )
    monkeypatch.setattr(storage_module.os, "open", lambda *_args, **_kwargs: 61)
    monkeypatch.setattr(
        storage_module.os,
        "fstat",
        lambda _fd: (_ for _ in ()).throw(primary),
    )
    monkeypatch.setattr(storage_module.os, "close", closed.append)
    try:
        with pytest.raises(M02StorageConfigurationError) as error:
            parent._open_posix_child("objects")
        assert error.value.__cause__ is primary
        assert closed == [61]
        assert parent._closed is False
    finally:
        parent.close()
    assert closed == [61, 60]
    del parent
    gc.collect()
    assert closed == [61, 60]


def test_posix_child_post_open_identity_failure_closes_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.m02_storage as storage_module

    closed: list[int] = []
    verifications = 0
    parent = _TrustedDirectory(
        Path("managed"),
        70,
        (7, 18),
        handle_kind=_DirectoryHandleKind.POSIX,
    )

    def fail_child_identity(_directory):
        nonlocal verifications
        verifications += 1
        if verifications == 2:
            raise M02StorageConfigurationError("injected child identity failure")

    monkeypatch.setattr(storage_module.os, "open", lambda *_args, **_kwargs: 71)
    monkeypatch.setattr(storage_module.os, "fstat", lambda _fd: _DirectoryStat())
    monkeypatch.setattr(storage_module.os, "close", closed.append)
    monkeypatch.setattr(_TrustedDirectory, "_verify_path_identity", fail_child_identity)
    try:
        with pytest.raises(M02StorageConfigurationError, match="child identity"):
            parent._open_posix_child("objects")
        assert closed == [71]
        assert parent._closed is False
    finally:
        parent.close()
    assert closed == [71, 70]
    del parent
    gc.collect()
    assert closed == [71, 70]


def test_posix_root_constructor_failure_closes_descriptor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.m02_storage as storage_module

    closed: list[int] = []
    primary = RuntimeError("injected constructor failure")
    monkeypatch.setattr(storage_module.os, "open", lambda *_args, **_kwargs: 81)
    monkeypatch.setattr(storage_module.os, "fstat", lambda _fd: _DirectoryStat())
    monkeypatch.setattr(storage_module.os, "close", closed.append)
    monkeypatch.setattr(
        _TrustedDirectory,
        "__init__",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(primary),
    )
    with pytest.raises(RuntimeError) as error:
        _TrustedDirectory._open_posix(Path("managed"))
    assert error.value is primary
    assert closed == [81]


def test_posix_post_open_close_failure_preserves_primary_diagnostically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.m02_storage as storage_module

    primary = OSError("injected fstat failure")
    close_calls: list[int] = []

    def fail_close(descriptor):
        close_calls.append(descriptor)
        raise OSError("injected close failure")

    monkeypatch.setattr(storage_module.os, "open", lambda *_args, **_kwargs: 91)
    monkeypatch.setattr(
        storage_module.os,
        "fstat",
        lambda _fd: (_ for _ in ()).throw(primary),
    )
    monkeypatch.setattr(storage_module.os, "close", fail_close)
    with pytest.raises(M02StorageConfigurationError) as error:
        _TrustedDirectory._open_posix(Path("managed"))
    assert error.value.__cause__ is primary
    assert close_calls == [91]
    assert any(
        "Secondary managed-directory close failure" in note
        for note in primary.__notes__
    )


def test_posix_success_transfers_descriptor_until_idempotent_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.m02_storage as storage_module

    closed: list[int] = []
    monkeypatch.setattr(storage_module.os, "open", lambda *_args, **_kwargs: 101)
    monkeypatch.setattr(storage_module.os, "fstat", lambda _fd: _DirectoryStat())
    monkeypatch.setattr(storage_module.os, "close", closed.append)
    directory = _TrustedDirectory._open_posix(Path("managed"))
    assert closed == []
    directory.close()
    directory.close()
    assert closed == [101]


def test_blob_identity_is_immutable(api) -> None:
    client, session_local, _ = api
    _upload(client, 1, [("immutable.pdf", b"%PDF-immutable", "application/pdf")])
    with session_local() as session:
        blob = session.scalar(select(M02PreservedBlob))
        assert blob is not None
        blob.byte_size += 1
        with pytest.raises(ValueError, match="immutable"):
            session.commit()


def test_pkg007_migration_is_additive_and_downgrades(tmp_path: Path) -> None:
    db_path = tmp_path / "pkg007-migration.db"
    _run_alembic(db_path, "upgrade", PARENT_REVISION)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO clients (client_id, display_name, id_number) "
                "VALUES (77, 'Existing', '00077')"
            )
        )
    engine.dispose()

    _run_alembic(db_path, "upgrade", PKG007_REVISION)
    upgraded = create_engine(f"sqlite:///{db_path.as_posix()}")
    inspector = inspect(upgraded)
    assert {
        "m02_intake_records",
        "m02_preserved_sources",
        "m02_preserved_blobs",
    }.issubset(inspector.get_table_names())
    with upgraded.connect() as connection:
        assert connection.scalar(
            text("SELECT display_name FROM clients WHERE client_id = 77")
        ) == "Existing"
    upgraded.dispose()

    _run_alembic(db_path, "downgrade", PARENT_REVISION)
    downgraded = create_engine(f"sqlite:///{db_path.as_posix()}")
    assert not {
        "m02_intake_records",
        "m02_preserved_sources",
        "m02_preserved_blobs",
    }.intersection(inspect(downgraded).get_table_names())
    with downgraded.connect() as connection:
        assert connection.scalar(
            text("SELECT display_name FROM clients WHERE client_id = 77")
        ) == "Existing"
    downgraded.dispose()


def test_pkg007_is_single_alembic_head() -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///./pkg007-head-check.db"
    result = subprocess.run(
        ["alembic", "heads"],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        check=True,
        text=True,
    )
    assert result.stdout.strip() == f"{PKG007_REVISION} (head)"


def test_pkg007_migration_compiles_portable_postgresql_ddl() -> None:
    migration_path = (
        _backend_root()
        / "alembic"
        / "versions"
        / "b6d8e2f4a701_pkg007_m02_intake.py"
    )
    spec = importlib.util.spec_from_file_location("pkg007_migration", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = io.StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql",
        opts={"as_sql": True, "output_buffer": output},
    )
    module.op = Operations(context)
    module.upgrade()
    sql = output.getvalue()
    assert "GLOB" not in sql
    assert "instr(" not in sql
    assert "char(92)" not in sql
    assert "sha256_checksum ~ '^[0-9a-f]{64}$'" in sql
    assert "storage_key NOT LIKE" in sql


def test_pkg007_model_compiles_portable_postgresql_ddl() -> None:
    sql = str(
        CreateTable(M02PreservedBlob.__table__).compile(
            dialect=postgresql.dialect()
        )
    )
    assert "GLOB" not in sql
    assert "instr(" not in sql
    assert "char(92)" not in sql
    assert "sha256_checksum ~ '^[0-9a-f]{64}$'" in sql
    assert "storage_key NOT LIKE" in sql


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("שלום עולם".encode("cp1255"), "windows-1255"),
        ("שלום עולם".encode("iso8859_8"), ("windows-1255", "iso-8859-8")),
        ("Résumé déjà vu, pension statement".encode("latin-1"), "latin-1"),
        ("שלום עולם".encode("utf-8"), "utf-8"),
        (b"\xef\xbb\xbfvalid,statement\n1,2", "utf-8-bom"),
    ],
)
def test_text_likeness_preserves_supported_encodings(
    tmp_path: Path, content: bytes, expected: str | tuple[str, ...]
) -> None:
    path = tmp_path / "source.dat"
    path.write_bytes(content)
    detected = _validate_text(path)
    assert detected in expected if isinstance(expected, tuple) else detected == expected
    assert path.read_bytes() == content


@pytest.mark.parametrize(
    "content",
    [
        b"\xff" * 256,
        bytes(range(1, 256)),
        b"valid\x00text",
        b"\x01\x02\x03\x04" * 64,
    ],
)
def test_text_likeness_rejects_binary_and_control_heavy_content(
    tmp_path: Path, content: bytes
) -> None:
    path = tmp_path / "source.dat"
    path.write_bytes(content)
    with pytest.raises(M02FileError) as error:
        _validate_text(path)
    assert error.value.code == "M02_UNSUPPORTED_BINARY_TEXT"


def test_storage_rejects_repository_cwd_public_and_static_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _backend_root().parent.resolve()
    for unsafe in (
        Path.cwd(),
        repository,
        repository / "backend",
        repository / "frontend",
        repository / "frontend" / "public",
        repository / "frontend" / "static",
    ):
        monkeypatch.setenv("M02_STORAGE_ROOT", str(unsafe))
        with pytest.raises(M02StorageConfigurationError):
            ManagedLocalStorage.from_environment()


def test_storage_rejects_root_and_managed_directory_symlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    root_link = tmp_path / "root-link"
    try:
        root_link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links are unavailable")
    monkeypatch.setenv("M02_STORAGE_ROOT", str(root_link.absolute()))
    with pytest.raises(M02StorageConfigurationError):
        ManagedLocalStorage.from_environment()

    safe_root = tmp_path / "safe-root"
    safe_root.mkdir()
    (safe_root / "objects").mkdir()
    (safe_root / ".temporary").symlink_to(target, target_is_directory=True)
    monkeypatch.setenv("M02_STORAGE_ROOT", str(safe_root.absolute()))
    with pytest.raises(M02StorageConfigurationError):
        ManagedLocalStorage.from_environment()


def test_storage_rejects_symlinked_final_directory_and_windows_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "managed"
    monkeypatch.setenv("M02_STORAGE_ROOT", str(root.absolute()))
    storage = ManagedLocalStorage.from_environment()
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = storage.object_root / "aa"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links are unavailable")
    with pytest.raises(M02StorageConfigurationError):
        storage.resolve_key("objects/aa/object")
    for key in ("../outside", "objects/../outside", r"objects\outside", "C:/outside"):
        with pytest.raises(M02StorageConfigurationError):
            storage.resolve_key(key)


def test_archived_case_blocks_all_m02_mutations_but_keeps_reads_and_reopen(
    api,
) -> None:
    client, session_local, _ = api
    existing = _upload(
        client, 1, [("before.pdf", b"%PDF-before", "application/pdf")]
    ).json()["results"][0]["intake"]
    with session_local() as session:
        session.get(Client, 1).status = "archived"
        session.commit()

    mutation_responses = [
        client.post("/api/clients/1/m02/intakes/manual", json=_manual_payload()),
        client.put(
            f"/api/clients/1/m02/intakes/{existing['intake_id']}",
            json={"product_name": "blocked"},
        ),
        _upload(client, 1, [("blocked.pdf", b"%PDF-blocked", "application/pdf")]),
        client.post(
            f"/api/clients/1/m02/intakes/{existing['intake_id']}/lifecycle",
            json={"target_status": "metadata_review"},
        ),
    ]
    assert all(response.status_code == 409 for response in mutation_responses)
    assert all(
        response.json()["detail"]["code"] == "archived_case_read_only"
        for response in mutation_responses
    )
    assert client.get("/api/clients/1/m02/intakes").status_code == 200
    assert (
        client.get(
            f"/api/clients/1/m02/sources/{existing['source']['source_id']}/download"
        ).status_code
        == 200
    )

    with session_local() as session:
        session.get(Client, 1).status = "delivered"
        session.commit()
    assert (
        client.post("/api/clients/1/m02/intakes/manual", json=_manual_payload()).status_code
        == 201
    )


def test_lifecycle_notes_persist_only_on_successful_transition(api) -> None:
    client, _, _ = api
    row = client.post(
        "/api/clients/1/m02/intakes/manual", json=_manual_payload(notes="prior")
    ).json()
    invalid = client.post(
        f"/api/clients/1/m02/intakes/{row['intake_id']}/lifecycle",
        json={"target_status": "metadata_review", "notes": "must not persist"},
    )
    assert invalid.status_code == 409
    assert client.get(
        f"/api/clients/1/m02/intakes/{row['intake_id']}"
    ).json()["notes"] == "prior"
    accepted = client.post(
        f"/api/clients/1/m02/intakes/{row['intake_id']}/lifecycle",
        json={"target_status": "accepted_for_review", "notes": "reviewed transition"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["notes"] == "reviewed transition"


def test_concurrent_same_client_uploads_reuse_one_blob_without_orphans(api) -> None:
    client, session_local, storage_root = api
    content = b"%PDF-concurrent-identical"

    def submit(index: int):
        with TestClient(app) as concurrent_client:
            return _upload(
                concurrent_client,
                1,
                [(f"same-{index}.pdf", content, "application/pdf")],
            )

    with ThreadPoolExecutor(max_workers=3) as executor:
        responses = list(executor.map(submit, range(3)))
    assert all(response.status_code == 200 for response in responses)
    intakes = [response.json()["results"][0]["intake"] for response in responses]
    assert sum(not item["duplicate_candidate"] for item in intakes) == 1
    assert sum(item["duplicate_candidate"] for item in intakes) == 2
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 1
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 3
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 3
    stored = [
        path
        for path in storage_root.rglob("*")
        if path.is_file() and ".temporary" not in path.parts
    ]
    assert len(stored) == 1


def test_download_stream_uses_open_descriptor_without_path_reopen(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _, _ = api
    intake_row = _upload(
        client, 1, [("descriptor.pdf", b"%PDF-descriptor", "application/pdf")]
    ).json()["results"][0]["intake"]
    original_open = Path.open

    def reject_managed_reopen(path: Path, *args, **kwargs):
        if "objects" in path.parts:
            raise AssertionError("managed source was reopened by path")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_managed_reopen)
    response = client.get(
        f"/api/clients/1/m02/sources/{intake_row['source']['source_id']}/download"
    )
    assert response.status_code == 200
    assert response.content == b"%PDF-descriptor"


def test_open_descriptor_serves_original_inode_after_path_replacement(api) -> None:
    client, session_local, storage_root = api
    original_content = b"%PDF-original-inode"
    _upload(
        client, 1, [("inode.pdf", original_content, "application/pdf")]
    )
    with session_local() as session:
        storage_key = session.scalar(select(M02PreservedBlob.storage_key))
    storage = ManagedLocalStorage(storage_root)
    reader = storage.open_key(storage_key)
    path = storage.resolve_key(storage_key)
    moved = path.with_name(f"{path.name}-opened")
    replaced = False
    try:
        path.rename(moved)
        path.write_bytes(b"%PDF-replacement")
        replaced = True
    except OSError:
        pass
    finally:
        storage.close()
    assert reader.read() == original_content
    reader.close()
    reader.close()
    assert reader.close_count == 1
    if replaced:
        assert path.read_bytes() == b"%PDF-replacement"


def test_staged_directory_replacement_race_never_writes_attacker_directory(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, storage_root = api
    original = _TrustedDirectory.create_file
    attempted = False
    attacker_directory = storage_root / ".temporary"
    approved_moved = storage_root / ".temporary-approved"

    def swap_before_create(directory, name):
        nonlocal attempted
        if directory.path.name == ".temporary" and name.endswith(".upload") and not attempted:
            attempted = True
            try:
                directory.path.rename(approved_moved)
                attacker_directory.mkdir()
            except OSError:
                pass
        return original(directory, name)

    monkeypatch.setattr(_TrustedDirectory, "create_file", swap_before_create)
    response = _upload(
        client, 1, [("race.pdf", b"%PDF-staged-race", "application/pdf")]
    )
    assert attempted is True
    assert not [
        path for path in attacker_directory.rglob("*") if path.is_file()
    ]
    if approved_moved.exists():
        assert response.status_code == 503
        assert response.json()["detail"] == {
            "code": "M02_STORAGE_UNAVAILABLE",
            "message": "Managed source storage is unavailable",
        }
        assert str(storage_root) not in response.text
        with session_local() as session:
            assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 0
    else:
        assert response.status_code == 200
        assert response.json()["results"][0]["status"] == "preserved"


def test_final_directory_replacement_race_never_writes_attacker_directory(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, storage_root = api
    original = _TrustedDirectory.create_link_from
    attempted = False
    attacker_directory: Path | None = None
    approved_moved: Path | None = None
    swapped = False

    def swap_before_link(directory, source, source_name, destination_name):
        nonlocal attempted, attacker_directory, approved_moved, swapped
        if directory.path.parent.name == "objects" and not attempted:
            attempted = True
            attacker_directory = directory.path
            approved_moved = directory.path.with_name(f"{directory.path.name}-approved")
            try:
                directory.path.rename(approved_moved)
                attacker_directory.mkdir()
                swapped = True
            except OSError:
                pass
        return original(directory, source, source_name, destination_name)

    monkeypatch.setattr(_TrustedDirectory, "create_link_from", swap_before_link)
    response = _upload(
        client, 1, [("race.pdf", b"%PDF-final-race", "application/pdf")]
    )
    assert attempted is True
    assert attacker_directory is not None
    if swapped:
        assert not [
            path for path in attacker_directory.rglob("*") if path.is_file()
        ]
    if swapped and approved_moved is not None and approved_moved.exists():
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert detail["code"] == "M02_STORAGE_CLEANUP_FAILED"
        assert detail["diagnostic_chain"] == [
            "M02_STORAGE_CONFIGURATION_BLOCKED",
            "M02_FINAL_PLACEMENT_SUCCEEDED",
            "M02_STORAGE_CLEANUP_FAILED",
        ]
        assert str(storage_root) not in response.text
        assert not [path for path in approved_moved.rglob("*") if path.is_file()]
        with session_local() as session:
            assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 0
            assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 0
    else:
        assert response.status_code == 200
        assert response.json()["results"][0]["status"] == "preserved"


def test_final_link_transfers_owner_before_post_link_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "managed"
    root.mkdir()
    storage = ManagedLocalStorage(root)
    staged = storage.new_staged_upload(
        original_filename="owner.pdf",
        extension=".pdf",
        declared_mime_type="application/pdf",
        validated_media_type="application/pdf",
    )
    with staged.open_write() as target:
        target.write(b"%PDF-owner")

    def fail_after_link(_directory, _source):
        raise M02StorageConfigurationError("injected post-link verification failure")

    monkeypatch.setattr(_TrustedDirectory, "verify_link_from", fail_after_link)
    with pytest.raises(M02StorageConfigurationError):
        storage.place(staged)
    assert staged.resource_state == "final-created-uncommitted"
    assert staged.final_storage_key is not None
    assert staged.final_directory is not None
    staged.cleanup()
    staged.cleanup()
    assert staged.resource_state == "cleaned"
    assert not [path for path in root.rglob("*") if path.is_file()]
    storage.close()


def test_staged_resource_state_model_allows_only_declared_transitions(
    tmp_path: Path,
) -> None:
    root = tmp_path / "managed"
    root.mkdir()
    storage = ManagedLocalStorage(root)

    shared = storage.new_staged_upload(
        original_filename="shared.pdf",
        extension=".pdf",
        declared_mime_type="application/pdf",
        validated_media_type="application/pdf",
    )
    assert shared.resource_state == "staged-only"
    shared.mark_shared_existing()
    assert shared.resource_state == "shared-existing"
    shared.mark_committed()
    assert shared.resource_state == "committed"
    shared.cleanup()
    assert shared.resource_state == "cleaned"

    invalid = storage.new_staged_upload(
        original_filename="invalid.pdf",
        extension=".pdf",
        declared_mime_type="application/pdf",
        validated_media_type="application/pdf",
    )
    invalid.cleanup()
    assert invalid.resource_state == "cleaned"
    with pytest.raises(M02StorageConfigurationError, match="Invalid staged-resource"):
        invalid.mark_shared_existing()
    storage.close()


def test_staged_resource_transition_matrix_is_closed() -> None:
    allowed = {
        ("staged-only", "final-created-uncommitted"),
        ("staged-only", "shared-existing"),
        ("staged-only", "cleanup-pending"),
        ("final-created-uncommitted", "committed"),
        ("final-created-uncommitted", "cleanup-pending"),
        ("shared-existing", "committed"),
        ("shared-existing", "cleanup-pending"),
        ("committed", "cleanup-pending"),
        ("cleanup-pending", "cleaned"),
        ("cleanup-pending", "cleanup-failed"),
        ("cleanup-failed", "cleanup-pending"),
    }
    states = list(StagedResourceState)
    for source in states:
        for target in states:
            staged = StagedUpload(
                storage=object(),  # type: ignore[arg-type]
                temporary_name="state.upload",
                original_filename="state.pdf",
                extension=".pdf",
                declared_mime_type="application/pdf",
                validated_media_type="application/pdf",
                _resource_state=source,
            )
            if (source.value, target.value) in allowed:
                staged._transition(target)
                assert staged.resource_state == target.value
            else:
                with pytest.raises(
                    M02StorageConfigurationError,
                    match="Invalid staged-resource transition",
                ):
                    staged._transition(target)


def test_staged_unlink_failure_after_final_link_keeps_owner_for_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "managed"
    root.mkdir()
    storage = ManagedLocalStorage(root)
    staged = storage.new_staged_upload(
        original_filename="unlink.pdf",
        extension=".pdf",
        declared_mime_type="application/pdf",
        validated_media_type="application/pdf",
    )
    with staged.open_write() as target:
        target.write(b"%PDF-unlink")
    storage_key = storage.place(staged)
    final_path = storage.resolve_key(storage_key)
    final_identity = staged.final_directory.identity
    original_unlink = storage._temporary_directory.unlink
    failures_remaining = 2

    def fail_staged_unlink(name, *, missing_ok=True):
        nonlocal failures_remaining
        if name == staged.temporary_name and failures_remaining:
            failures_remaining -= 1
            raise PermissionError("injected staged-source unlink failure")
        return original_unlink(name, missing_ok=missing_ok)

    monkeypatch.setattr(storage._temporary_directory, "unlink", fail_staged_unlink)
    with pytest.raises(M02StorageCleanupError) as error:
        staged.cleanup()
    assert error.value.diagnostic_codes == (
        "M02_FINAL_PLACEMENT_SUCCEEDED",
        "M02_STORAGE_CLEANUP_FAILED",
    )
    assert staged.resource_state == "cleanup-failed"
    assert staged.final_storage_key == storage_key
    assert staged.final_directory is not None
    assert staged.final_directory.identity == final_identity
    assert final_path.read_bytes() == b"%PDF-unlink"
    assert staged.temporary_path.exists()

    with pytest.raises(M02StorageCleanupError):
        staged.cleanup()
    assert staged.resource_state == "cleanup-failed"
    assert staged.final_directory is not None
    assert staged.final_directory.identity == final_identity

    staged.cleanup()
    assert staged.resource_state == "cleaned"
    assert not final_path.exists()
    assert not staged.temporary_path.exists()
    staged.cleanup()
    storage.close()


def test_final_directory_close_failure_becomes_structured_and_retries_without_unlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "managed"
    root.mkdir()
    storage = ManagedLocalStorage(root)
    staged = storage.new_staged_upload(
        original_filename="close.pdf",
        extension=".pdf",
        declared_mime_type="application/pdf",
        validated_media_type="application/pdf",
    )
    with staged.open_write() as target:
        target.write(b"%PDF-close")
    storage_key = storage.place(staged)
    final_path = storage.resolve_key(storage_key)
    final_directory = staged.final_directory
    final_identity = final_directory.identity
    original_unlink = final_directory.unlink
    original_close = final_directory.close
    unlink_calls = 0
    close_calls = 0

    def track_unlink(name, *, missing_ok=True):
        nonlocal unlink_calls
        unlink_calls += 1
        return original_unlink(name, missing_ok=missing_ok)

    def fail_close_once():
        nonlocal close_calls
        close_calls += 1
        if close_calls == 1:
            raise OSError("injected final-directory close failure")
        return original_close()

    monkeypatch.setattr(final_directory, "unlink", track_unlink)
    monkeypatch.setattr(final_directory, "close", fail_close_once)
    primary = M02FileError(
        "M02_PERSISTENCE_FAILED", "Injected primary persistence failure"
    )
    with pytest.raises(M02StorageCleanupError) as error:
        staged.cleanup(primary_error=primary)

    assert error.value.primary_error is primary
    assert isinstance(error.value.cleanup_errors[0], OSError)
    assert error.value.cleanup_steps == ("FINAL_DIRECTORY_CLOSE",)
    assert error.value.diagnostic_codes == (
        "M02_PERSISTENCE_FAILED",
        "M02_FINAL_PLACEMENT_SUCCEEDED",
        "M02_STORAGE_CLEANUP_FAILED",
    )
    assert staged.resource_state == "cleanup-failed"
    assert staged.final_removed is True
    assert staged.final_directory_closed is False
    assert staged.final_directory is final_directory
    assert staged.final_directory.identity == final_identity
    assert not final_path.exists()

    staged.cleanup()
    assert staged.resource_state == "cleaned"
    assert staged.final_directory_closed is True
    assert staged.final_directory is None
    assert unlink_calls == 1
    assert close_calls == 2
    staged.cleanup()
    assert unlink_calls == 1
    assert close_calls == 2
    storage.close()


def test_committed_close_failure_never_deletes_final_and_retries_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "managed"
    root.mkdir()
    storage = ManagedLocalStorage(root)
    staged = storage.new_staged_upload(
        original_filename="committed.pdf",
        extension=".pdf",
        declared_mime_type="application/pdf",
        validated_media_type="application/pdf",
    )
    with staged.open_write() as target:
        target.write(b"%PDF-committed")
    storage_key = storage.place(staged)
    final_path = storage.resolve_key(storage_key)
    staged.mark_committed()
    final_directory = staged.final_directory
    original_close = final_directory.close
    close_calls = 0

    def fail_close_once():
        nonlocal close_calls
        close_calls += 1
        if close_calls == 1:
            raise OSError("injected committed close failure")
        return original_close()

    monkeypatch.setattr(final_directory, "close", fail_close_once)
    with pytest.raises(M02StorageCleanupError) as error:
        staged.cleanup()
    assert error.value.cleanup_steps == ("FINAL_DIRECTORY_CLOSE",)
    assert staged.resource_state == "cleanup-failed"
    assert staged.final_removed is False
    assert final_path.read_bytes() == b"%PDF-committed"

    staged.cleanup()
    assert staged.resource_state == "cleaned"
    assert final_path.read_bytes() == b"%PDF-committed"
    assert close_calls == 2
    storage.close()


def test_committed_close_failure_reaches_batch_api_without_deleting_blob(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, storage_root = api
    original_cleanup = StagedUpload.cleanup
    injected = False

    def cleanup_with_close_failure(staged, *, primary_error=None):
        nonlocal injected
        if staged.final_directory is not None and not injected:
            injected = True
            original_close = staged.final_directory.close
            failed_once = False

            def fail_once():
                nonlocal failed_once
                if not failed_once:
                    failed_once = True
                    raise OSError("injected final-directory close failure")
                return original_close()

            monkeypatch.setattr(staged.final_directory, "close", fail_once)
        return original_cleanup(staged, primary_error=primary_error)

    monkeypatch.setattr(StagedUpload, "cleanup", cleanup_with_close_failure)
    response = _upload(
        client, 1, [("committed.pdf", b"%PDF-committed", "application/pdf")]
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "preserved"
    assert response.json()["request_error"] == {
        "code": "M02_STORAGE_CLEANUP_FAILED",
        "message": "Managed upload cleanup could not be completed",
    }
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 1
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 1
    objects = [
        path
        for path in storage_root.rglob("*")
        if path.is_file() and ".temporary" not in path.parts
    ]
    assert len(objects) == 1
    assert objects[0].read_bytes() == b"%PDF-committed"


def test_managed_temporary_directory_close_failure_is_structured_and_retryable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "managed"
    root.mkdir()
    storage = ManagedLocalStorage(root)
    original_temp_close = storage._temporary_directory.close
    original_object_close = storage._object_directory.close
    original_root_close = storage._root_directory.close
    close_counts = {"temporary": 0, "objects": 0, "root": 0}

    def fail_temp_once():
        close_counts["temporary"] += 1
        if close_counts["temporary"] == 1:
            raise OSError("injected temporary-directory close failure")
        return original_temp_close()

    def close_objects():
        close_counts["objects"] += 1
        return original_object_close()

    def close_root():
        close_counts["root"] += 1
        return original_root_close()

    monkeypatch.setattr(storage._temporary_directory, "close", fail_temp_once)
    monkeypatch.setattr(storage._object_directory, "close", close_objects)
    monkeypatch.setattr(storage._root_directory, "close", close_root)
    with pytest.raises(M02StorageCleanupError) as error:
        storage.close()
    assert error.value.cleanup_steps == ("TEMP_DIRECTORY_CLOSE",)
    assert isinstance(error.value.cleanup_errors[0], OSError)
    assert storage._closed is False

    storage.close()
    assert storage._closed is True
    assert close_counts == {"temporary": 2, "objects": 2, "root": 2}
    storage.close()
    assert close_counts == {"temporary": 2, "objects": 2, "root": 2}


@pytest.mark.parametrize("completed_count", [1, 2])
@pytest.mark.parametrize("raw_close_failure", [False, True])
def test_batch_preserves_committed_results_when_storage_close_fails(
    api,
    monkeypatch: pytest.MonkeyPatch,
    completed_count: int,
    raw_close_failure: bool,
) -> None:
    client, session_local, _ = api
    import app.api.m02_intake_routes as routes

    retained_storage: list[ManagedLocalStorage] = []
    close_calls = 0
    original_storage_close = ManagedLocalStorage.close
    original_storage_factory = routes._storage

    def create_failing_storage():
        storage = original_storage_factory()
        retained_storage.append(storage)

        def fail_close():
            nonlocal close_calls
            close_calls += 1
            if raw_close_failure:
                raise OSError("injected raw storage close failure")
            raise M02StorageCleanupError(
                "injected typed storage close failure",
                cleanup_errors=(OSError("injected close failure"),),
                cleanup_steps=("TEMP_DIRECTORY_CLOSE",),
            )

        monkeypatch.setattr(storage, "close", fail_close)
        return storage

    monkeypatch.setattr(routes, "_storage", create_failing_storage)
    try:
        response = _upload(
            client,
            1,
            [
                (
                    f"committed-{index}.pdf",
                    f"%PDF-committed-{index}".encode(),
                    "application/pdf",
                )
                for index in range(completed_count)
            ],
        )
    finally:
        for storage in retained_storage:
            storage.close = original_storage_close.__get__(  # type: ignore[method-assign]
                storage, ManagedLocalStorage
            )
            storage.close()
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == completed_count
    assert all(result["status"] == "preserved" for result in body["results"])
    assert body["request_error"] == {
        "code": "M02_STORAGE_CLEANUP_FAILED",
        "message": "Managed upload cleanup could not be completed",
    }
    assert close_calls == 1
    assert len(retained_storage) == 1
    with session_local() as session:
        assert (
            session.scalar(text("SELECT COUNT(*) FROM m02_intake_records"))
            == completed_count
        )


def test_per_file_failure_is_preserved_when_storage_close_fails(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, _ = api
    import app.api.m02_intake_routes as routes

    retained_storage: list[ManagedLocalStorage] = []
    close_calls = 0
    original_storage_close = ManagedLocalStorage.close
    original_storage_factory = routes._storage

    def create_failing_storage():
        storage = original_storage_factory()
        retained_storage.append(storage)

        def fail_close():
            nonlocal close_calls
            close_calls += 1
            raise M02StorageCleanupError(
                "injected typed storage close failure",
                cleanup_errors=(OSError("injected close failure"),),
                cleanup_steps=("OBJECT_DIRECTORY_CLOSE",),
            )

        monkeypatch.setattr(storage, "close", fail_close)
        return storage

    monkeypatch.setattr(routes, "_storage", create_failing_storage)
    try:
        response = _upload(
            client, 1, [("invalid.pdf", b"not-a-pdf", "application/pdf")]
        )
    finally:
        for storage in retained_storage:
            storage.close = original_storage_close.__get__(  # type: ignore[method-assign]
                storage, ManagedLocalStorage
            )
            storage.close()
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["status"] == "failed"
    assert body["results"][0]["error_code"] == "M02_SIGNATURE_MISMATCH"
    assert body["request_error"]["code"] == "M02_STORAGE_CLEANUP_FAILED"
    assert close_calls == 1
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 0


@pytest.mark.parametrize("raw_close_failure", [False, True])
def test_primary_batch_and_storage_close_failures_share_structured_api_detail(
    api, monkeypatch: pytest.MonkeyPatch, raw_close_failure: bool
) -> None:
    client, session_local, storage_root = api
    import app.api.m02_intake_routes as routes

    retained_storage: list[ManagedLocalStorage] = []
    close_calls = 0
    original_storage_close = ManagedLocalStorage.close
    original_storage_factory = routes._storage

    def fail_batch(*_args, **_kwargs):
        raise RuntimeError("injected primary batch failure")

    def create_failing_storage():
        storage = original_storage_factory()
        retained_storage.append(storage)

        def fail_close():
            nonlocal close_calls
            close_calls += 1
            if raw_close_failure:
                raise OSError("private path injected raw close failure")
            raise M02StorageCleanupError(
                "injected typed storage close failure",
                cleanup_errors=(OSError("injected close failure"),),
                cleanup_steps=("ROOT_DIRECTORY_CLOSE",),
            )

        monkeypatch.setattr(storage, "close", fail_close)
        return storage

    monkeypatch.setattr(routes, "preserve_staged_upload", fail_batch)
    monkeypatch.setattr(routes, "_storage", create_failing_storage)
    try:
        response = _upload(
            client, 1, [("batch.pdf", b"%PDF-batch", "application/pdf")]
        )
    finally:
        for storage in retained_storage:
            storage.close = original_storage_close.__get__(  # type: ignore[method-assign]
                storage, ManagedLocalStorage
            )
            storage.close()
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["code"] == "M02_STORAGE_CLEANUP_FAILED"
    assert detail["diagnostic_chain"] == [
        "M02_BATCH_REQUEST_FAILED",
        "M02_STORAGE_CLEANUP_FAILED",
    ]
    assert detail["cleanup_steps"] == [
        "STORAGE_CLOSE" if raw_close_failure else "ROOT_DIRECTORY_CLOSE"
    ]
    assert "private path" not in response.text
    assert close_calls == 1
    assert len(retained_storage) == 1
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 0
    assert not [path for path in storage_root.rglob("*") if path.is_file()]


def test_batch_reports_staged_unlink_failure_after_final_link_without_rows(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, storage_root = api
    original_commit = Session.commit
    original_unlink = _TrustedDirectory.unlink
    failed_once = False

    def fail_m02_commit(session):
        if any(
            isinstance(item, (M02IntakeRecord, M02PreservedBlob, M02PreservedSource))
            for item in session.new
        ):
            raise SQLAlchemyError("injected DB commit failure")
        return original_commit(session)

    def fail_staged_unlink(directory, name, *, missing_ok=True):
        nonlocal failed_once
        if (
            directory.path.name == ".temporary"
            and name.endswith(".upload")
            and not failed_once
        ):
            failed_once = True
            raise PermissionError("injected staged-source unlink failure")
        return original_unlink(directory, name, missing_ok=missing_ok)

    monkeypatch.setattr(Session, "commit", fail_m02_commit)
    monkeypatch.setattr(_TrustedDirectory, "unlink", fail_staged_unlink)
    response = _upload(
        client, 1, [("unlink.pdf", b"%PDF-unlink", "application/pdf")]
    )
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["code"] == "M02_STORAGE_CLEANUP_FAILED"
    assert detail["diagnostic_chain"] == [
        "M02_PERSISTENCE_FAILED",
        "M02_FINAL_PLACEMENT_SUCCEEDED",
        "M02_STORAGE_CLEANUP_FAILED",
    ]
    assert str(storage_root) not in response.text
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 0


def test_database_commit_failure_cleans_final_object_without_orphan(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, storage_root = api
    original_commit = Session.commit

    def fail_m02_commit(session):
        if any(
            isinstance(item, (M02IntakeRecord, M02PreservedBlob, M02PreservedSource))
            for item in session.new
        ):
            raise SQLAlchemyError("injected DB commit failure")
        return original_commit(session)

    monkeypatch.setattr(Session, "commit", fail_m02_commit)
    response = _upload(
        client, 1, [("database.pdf", b"%PDF-database", "application/pdf")]
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "failed"
    assert response.json()["results"][0]["error_code"] == "M02_PERSISTENCE_FAILED"
    assert not [path for path in storage_root.rglob("*") if path.is_file()]
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 0


@pytest.mark.parametrize("completed_count", [1, 2])
def test_batch_preserves_all_committed_results_when_later_cleanup_fails(
    api, monkeypatch: pytest.MonkeyPatch, completed_count: int
) -> None:
    client, session_local, _ = api
    original_cleanup = StagedUpload.cleanup

    def fail_invalid_cleanup(self, *, primary_error=None):
        if self.original_filename == "broken.pdf":
            raise M02StorageCleanupError(
                "injected later cleanup failure",
                primary_error=primary_error,
                cleanup_errors=(OSError("injected cleanup failure"),),
            )
        return original_cleanup(self, primary_error=primary_error)

    monkeypatch.setattr(StagedUpload, "cleanup", fail_invalid_cleanup)
    files = [
        (
            f"committed-{index}.pdf",
            f"%PDF-committed-{index}".encode(),
            "application/pdf",
        )
        for index in range(completed_count)
    ]
    files.append(("broken.pdf", b"not-a-pdf", "application/pdf"))
    response = _upload(client, 1, files)

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == completed_count
    assert all(result["status"] == "preserved" for result in body["results"])
    assert body["request_error"] == {
        "code": "M02_STORAGE_CLEANUP_FAILED",
        "message": "Managed upload cleanup could not be completed",
    }
    with session_local() as session:
        assert (
            session.scalar(text("SELECT COUNT(*) FROM m02_intake_records"))
            == completed_count
        )


def test_shared_blob_remains_when_duplicate_cleanup_fails(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, storage_root = api
    original_cleanup = StagedUpload.cleanup

    def fail_duplicate_cleanup(self, *, primary_error=None):
        if self.original_filename == "duplicate.pdf":
            raise M02StorageCleanupError(
                "injected duplicate cleanup failure",
                primary_error=primary_error,
                cleanup_errors=(OSError("injected cleanup failure"),),
            )
        return original_cleanup(self, primary_error=primary_error)

    monkeypatch.setattr(StagedUpload, "cleanup", fail_duplicate_cleanup)
    content = b"%PDF-shared"
    response = _upload(
        client,
        1,
        [
            ("first.pdf", content, "application/pdf"),
            ("duplicate.pdf", content, "application/pdf"),
        ],
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == 2
    assert response.json()["request_error"]["code"] == "M02_STORAGE_CLEANUP_FAILED"
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 1
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 2
    objects = [
        path
        for path in storage_root.rglob("*")
        if path.is_file() and ".temporary" not in path.parts
    ]
    assert len(objects) == 1
    assert objects[0].read_bytes() == content


def test_validation_cleanup_failure_preserves_primary_diagnostic(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, _ = api

    def fail_cleanup(self, *, primary_error=None):
        raise M02StorageCleanupError(
            "injected validation cleanup failure",
            primary_error=primary_error,
            cleanup_errors=(OSError("injected cleanup failure"),),
        )

    monkeypatch.setattr(StagedUpload, "cleanup", fail_cleanup)
    response = _upload(
        client, 1, [("invalid.pdf", b"not-a-pdf", "application/pdf")]
    )
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["code"] == "M02_STORAGE_CLEANUP_FAILED"
    assert detail["diagnostic_chain"] == [
        "M02_SIGNATURE_MISMATCH",
        "M02_STORAGE_CLEANUP_FAILED",
    ]
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 0


def test_checksum_cleanup_failure_preserves_both_diagnostics(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, _ = api
    import app.services.m02_storage as storage_module

    class FailingDigest:
        def update(self, _chunk):
            raise M02FileError("M02_CHECKSUM_FAILED", "Injected checksum failure")

        def hexdigest(self):
            return "0" * 64

    def fail_cleanup(self, *, primary_error=None):
        raise M02StorageCleanupError(
            "injected checksum cleanup failure",
            primary_error=primary_error,
            cleanup_errors=(OSError("injected cleanup failure"),),
        )

    monkeypatch.setattr(storage_module.hashlib, "sha256", lambda: FailingDigest())
    monkeypatch.setattr(StagedUpload, "cleanup", fail_cleanup)
    response = _upload(
        client, 1, [("checksum.pdf", b"%PDF-checksum", "application/pdf")]
    )
    assert response.status_code == 500
    assert response.json()["detail"]["diagnostic_chain"] == [
        "M02_CHECKSUM_FAILED",
        "M02_STORAGE_CLEANUP_FAILED",
    ]
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 0


def test_database_cleanup_failure_rolls_back_rows_and_preserves_diagnostic_chain(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, _ = api
    original_commit = Session.commit

    def fail_m02_commit(session):
        if any(
            isinstance(item, (M02IntakeRecord, M02PreservedBlob, M02PreservedSource))
            for item in session.new
        ):
            raise SQLAlchemyError("injected DB commit failure")
        return original_commit(session)

    def fail_cleanup(self, *, primary_error=None):
        raise M02StorageCleanupError(
            "injected DB cleanup failure",
            primary_error=primary_error,
            cleanup_errors=(OSError("injected cleanup failure"),),
        )

    monkeypatch.setattr(Session, "commit", fail_m02_commit)
    monkeypatch.setattr(StagedUpload, "cleanup", fail_cleanup)
    response = _upload(
        client, 1, [("database.pdf", b"%PDF-database", "application/pdf")]
    )
    assert response.status_code == 500
    assert response.json()["detail"]["diagnostic_chain"] == [
        "M02_PERSISTENCE_FAILED",
        "M02_STORAGE_CLEANUP_FAILED",
    ]
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 0


def test_request_failure_cleanup_failure_is_not_generic_only(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_local, _ = api
    import app.api.m02_intake_routes as routes

    def fail_request(*_args, **_kwargs):
        raise RuntimeError("injected request failure")

    def fail_cleanup(self, *, primary_error=None):
        raise M02StorageCleanupError(
            "injected request cleanup failure",
            primary_error=primary_error,
            cleanup_errors=(OSError("injected cleanup failure"),),
        )

    monkeypatch.setattr(routes, "preserve_staged_upload", fail_request)
    monkeypatch.setattr(StagedUpload, "cleanup", fail_cleanup)
    response = _upload(
        client, 1, [("request.pdf", b"%PDF-request", "application/pdf")]
    )
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "M02_STORAGE_CLEANUP_FAILED"
    assert response.json()["detail"]["diagnostic_chain"] == [
        "M02_BATCH_REQUEST_FAILED",
        "M02_STORAGE_CLEANUP_FAILED",
    ]
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_intake_records")) == 0


def test_staged_owner_cleanup_is_idempotent_and_never_deletes_committed_or_shared_blob(
    api,
) -> None:
    client, session_local, storage_root = api
    content = b"%PDF-owner-contract"
    first = _upload(client, 1, [("first.pdf", content, "application/pdf")])
    second = _upload(client, 1, [("second.pdf", content, "application/pdf")])
    assert first.status_code == second.status_code == 200
    with session_local() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_blobs")) == 1
        assert session.scalar(text("SELECT COUNT(*) FROM m02_preserved_sources")) == 2
    objects = [
        path
        for path in storage_root.rglob("*")
        if path.is_file() and ".temporary" not in path.parts
    ]
    assert len(objects) == 1
    assert objects[0].read_bytes() == content


class _ControlledReader:
    def __init__(self, reads):
        self._reads = iter(reads)
        self.close_count = 0
        self.closed = False

    def read(self, _size=-1):
        value = next(self._reads)
        if isinstance(value, BaseException):
            raise value
        return value

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.close_count += 1


def test_download_header_failure_closes_descriptor_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.api.m02_intake_routes as routes

    reader = _ControlledReader([b""])
    monkeypatch.setattr(routes, "quote", lambda *_args, **_kwargs: (_ for _ in ()).throw(
        RuntimeError("header failure")
    ))
    with pytest.raises(RuntimeError, match="header failure"):
        routes._build_download_response(reader, "file.pdf")
    assert reader.close_count == 1


def test_download_response_construction_failure_closes_descriptor_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.api.m02_intake_routes as routes

    reader = _ControlledReader([b""])

    class FailingResponse:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("response construction failure")

    monkeypatch.setattr(routes, "M02DownloadResponse", FailingResponse)
    with pytest.raises(RuntimeError, match="response construction failure"):
        routes._build_download_response(reader, "file.pdf")
    assert reader.close_count == 1


def test_download_never_iterated_can_be_closed_exactly_once() -> None:
    from app.api.m02_intake_routes import _build_download_response

    reader = _ControlledReader([b"unused"])
    response = _build_download_response(reader, "file.pdf")
    response.close()
    response.close()
    assert reader.close_count == 1


@pytest.mark.parametrize(
    "reads",
    [
        [OSError("first read failure")],
        [b"first", OSError("mid-stream failure")],
    ],
)
def test_download_read_failures_close_descriptor_once(reads) -> None:
    from app.api.m02_intake_routes import _build_download_response

    reader = _ControlledReader(reads)
    response = _build_download_response(reader, "file.pdf")
    stream = response._stream_reader()
    if reads[0] == b"first":
        assert next(stream) == b"first"
    with pytest.raises(OSError):
        next(stream)
    assert reader.close_count == 1


def test_download_normal_completion_closes_descriptor_once_and_preserves_headers() -> None:
    from app.api.m02_intake_routes import _build_download_response

    reader = _ControlledReader([b"one", b"two", b""])
    response = _build_download_response(reader, "opaque.pdf")
    assert b"".join(response._stream_reader()) == b"onetwo"
    response.close()
    assert reader.close_count == 1
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].startswith("attachment;")


def test_download_cancellation_closes_descriptor_once() -> None:
    from app.api.m02_intake_routes import _build_download_response

    reader = _ControlledReader([b"one", b""])
    response = _build_download_response(reader, "opaque.pdf")
    scope = {"type": "http", "asgi": {"spec_version": "2.4"}}

    async def receive():
        await asyncio.Event().wait()

    async def send(message):
        if message["type"] == "http.response.body":
            raise asyncio.CancelledError()

    asyncio.run(response(scope, receive, send))
    assert reader.close_count == 1
