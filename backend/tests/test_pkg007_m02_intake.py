from __future__ import annotations

import io
import os
import subprocess
import zipfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.m02_intake import (
    M02IntakeRecord,
    M02PreservedBlob,
    M02PreservedSource,
)
from app.services.m02_storage import MAX_FILE_BYTES, M02FileError


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
    client, session_local, _ = api

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
    client, session_local, _ = api
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
