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
CURRENT_REVISION = "95222c79dce8"
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




































def test_storage_configuration_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("M02_STORAGE_ROOT", raising=False)
    from app.services.m02_storage import (
        M02StorageConfigurationError,
        ManagedLocalStorage,
    )

    with pytest.raises(M02StorageConfigurationError) as error:
        ManagedLocalStorage.from_environment()
    assert error.value.code == "M02_STORAGE_CONFIGURATION_BLOCKED"




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
    with upgraded.begin() as connection:
        assert connection.scalar(
            text("SELECT display_name FROM clients WHERE client_id = 77")
        ) == "Existing"
        connection.execute(
            text(
                "INSERT INTO m02_intake_records "
                "(intake_id, client_id, record_kind, manual_technical_reference, "
                "source_type, lifecycle_status, preservation_status, "
                "created_by_actor, updated_by_actor, lifecycle_decided_by_actor) "
                "VALUES ('base', 77, 'manual', 'M02-MANUAL-BASE', 'manual', "
                "'metadata_review', 'not_applicable', 'test', 'test', 'test')"
            )
        )
        assert connection.execute(
            text(
                "SELECT duplicate_candidate, superseding_candidate "
                "FROM m02_intake_records WHERE intake_id = 'base'"
            )
        ).one() == (0, 0)
        connection.execute(
            text(
                "INSERT INTO m02_intake_records "
                "(intake_id, client_id, record_kind, manual_technical_reference, "
                "source_type, lifecycle_status, preservation_status, "
                "duplicate_candidate, duplicate_of_intake_id, created_by_actor, "
                "updated_by_actor, lifecycle_decided_by_actor) "
                "VALUES ('duplicate', 77, 'manual', 'M02-MANUAL-DUPLICATE', "
                "'manual', 'metadata_review', 'not_applicable', TRUE, 'base', "
                "'test', 'test', 'test')"
            )
        )
        assert connection.scalar(
            text(
                "SELECT duplicate_candidate FROM m02_intake_records "
                "WHERE intake_id = 'duplicate'"
            )
        ) == 1
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


def test_pkg009_revision_remains_in_the_linear_migration_chain() -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///./pkg007-head-check.db"
    result = subprocess.run(
        ["alembic", "history", "-r", f"{CURRENT_REVISION}:heads"],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        check=True,
        text=True,
    )
    assert CURRENT_REVISION in result.stdout


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
    normalized_sql = " ".join(sql.lower().split())
    assert "GLOB" not in sql
    assert "instr(" not in sql
    assert "char(92)" not in sql
    assert "sha256_checksum ~ '^[0-9a-f]{64}$'" in sql
    assert "storage_key NOT LIKE" in sql
    assert "duplicate_candidate boolean default false not null" in normalized_sql
    assert "superseding_candidate boolean default false not null" in normalized_sql
    assert "duplicate_candidate = false" in normalized_sql
    assert "duplicate_candidate = true" in normalized_sql
    assert "superseding_candidate = false" in normalized_sql
    assert "superseding_candidate = true" in normalized_sql
    assert "duplicate_candidate boolean default 0" not in normalized_sql
    assert "superseding_candidate boolean default 0" not in normalized_sql
    assert "duplicate_candidate = 0" not in normalized_sql
    assert "duplicate_candidate = 1" not in normalized_sql
    assert "superseding_candidate = 0" not in normalized_sql
    assert "superseding_candidate = 1" not in normalized_sql


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
    import app.services.pension_source_download as routes

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
    import app.services.pension_source_download as routes

    reader = _ControlledReader([b""])

    class FailingResponse:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("response construction failure")

    monkeypatch.setattr(routes, "M02DownloadResponse", FailingResponse)
    with pytest.raises(RuntimeError, match="response construction failure"):
        routes._build_download_response(reader, "file.pdf")
    assert reader.close_count == 1


def test_download_never_iterated_can_be_closed_exactly_once() -> None:
    from app.services.pension_source_download import _build_download_response

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
    from app.services.pension_source_download import _build_download_response

    reader = _ControlledReader(reads)
    response = _build_download_response(reader, "file.pdf")
    stream = response._stream_reader()
    if reads[0] == b"first":
        assert next(stream) == b"first"
    with pytest.raises(OSError):
        next(stream)
    assert reader.close_count == 1


def test_download_normal_completion_closes_descriptor_once_and_preserves_headers() -> None:
    from app.services.pension_source_download import _build_download_response

    reader = _ControlledReader([b"one", b"two", b""])
    response = _build_download_response(reader, "opaque.pdf")
    assert b"".join(response._stream_reader()) == b"onetwo"
    response.close()
    assert reader.close_count == 1
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].startswith("attachment;")


def test_download_cancellation_closes_descriptor_once() -> None:
    from app.services.pension_source_download import _build_download_response

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
