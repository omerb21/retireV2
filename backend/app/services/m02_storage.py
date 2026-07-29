from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import stat
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol
from uuid import uuid4

from fastapi import UploadFile


MAX_FILE_BYTES = 26_214_400
CHUNK_SIZE = 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".xml", ".dat", ".csv", ".xlsx"}
MIME_BY_EXTENSION = {
    ".pdf": {"application/pdf"},
    ".xml": {"application/xml", "text/xml"},
    ".dat": {"", "text/plain", "application/octet-stream"},
    ".csv": {"text/csv"},
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    },
}
VALIDATED_MEDIA_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".xml": "application/xml",
    ".dat": "text/plain",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class M02StorageConfigurationError(RuntimeError):
    code = "M02_STORAGE_CONFIGURATION_BLOCKED"


class M02StorageCleanupError(RuntimeError):
    code = "M02_STORAGE_CLEANUP_FAILED"

    def __init__(
        self,
        message: str,
        *,
        primary_error: BaseException | None = None,
        cleanup_errors: tuple[BaseException, ...] = (),
        operational_diagnostics: tuple[str, ...] = (),
        cleanup_steps: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.primary_error = primary_error
        self.cleanup_errors = cleanup_errors
        self.operational_diagnostics = operational_diagnostics
        self.cleanup_steps = cleanup_steps
        self.diagnostic_codes = tuple(
            code
            for code in (
                getattr(primary_error, "code", None),
                *operational_diagnostics,
                self.code,
            )
            if code is not None
        )


class M02FileError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class M02OwnedReader:
    def __init__(self, stream: io.BufferedReader):
        self._stream = stream
        self._closed = False
        self.close_count = 0

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.close_count += 1
        self._stream.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


class _WindowsDirectoryApiProtocol(Protocol):
    def open_directory(self, path: Path) -> tuple[int, int, tuple[int, int]]: ...

    def close_handle(self, handle: int) -> None: ...


class _WindowsDirectoryApi:
    GENERIC_READ = 0x80000000
    SHARE_READ_WRITE = 0x1 | 0x2
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    FILE_ATTRIBUTE_DIRECTORY = 0x10
    FILE_ATTRIBUTE_REPARSE_POINT = 0x400

    @classmethod
    def create_file_arguments(cls, path: Path) -> tuple[object, ...]:
        return (
            str(path),
            cls.GENERIC_READ,
            cls.SHARE_READ_WRITE,
            None,
            cls.OPEN_EXISTING,
            cls.FILE_FLAG_BACKUP_SEMANTICS
            | cls.FILE_FLAG_OPEN_REPARSE_POINT,
            None,
        )

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        class FileInformation(ctypes.Structure):
            _fields_ = [
                ("dwFileAttributes", wintypes.DWORD),
                ("ftCreationTimeLow", wintypes.DWORD),
                ("ftCreationTimeHigh", wintypes.DWORD),
                ("ftLastAccessTimeLow", wintypes.DWORD),
                ("ftLastAccessTimeHigh", wintypes.DWORD),
                ("ftLastWriteTimeLow", wintypes.DWORD),
                ("ftLastWriteTimeHigh", wintypes.DWORD),
                ("dwVolumeSerialNumber", wintypes.DWORD),
                ("nFileSizeHigh", wintypes.DWORD),
                ("nFileSizeLow", wintypes.DWORD),
                ("nNumberOfLinks", wintypes.DWORD),
                ("nFileIndexHigh", wintypes.DWORD),
                ("nFileIndexLow", wintypes.DWORD),
            ]

        self._ctypes = ctypes
        self._wintypes = wintypes
        self._file_information = FileInformation
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._create_file = self._kernel32.CreateFileW
        self._create_file.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self._create_file.restype = wintypes.HANDLE

    def open_directory(self, path: Path) -> tuple[int, int, tuple[int, int]]:
        handle = self._create_file(*self.create_file_arguments(path))
        invalid = self._wintypes.HANDLE(-1).value
        if handle == invalid:
            raise OSError(
                self._ctypes.get_last_error(), "Unable to pin managed directory"
            )
        info = self._file_information()
        if not self._kernel32.GetFileInformationByHandle(
            handle, self._ctypes.byref(info)
        ):
            primary_error = OSError(
                self._ctypes.get_last_error(),
                "Unable to identify managed directory",
            )
            _close_windows_handle_preserving_error(
                self, int(handle), primary_error
            )
            raise primary_error
        identity = (
            info.dwVolumeSerialNumber,
            (info.nFileIndexHigh << 32) | info.nFileIndexLow,
        )
        return int(handle), info.dwFileAttributes, identity

    def close_handle(self, handle: int) -> None:
        if not self._kernel32.CloseHandle(handle):
            raise OSError(
                self._ctypes.get_last_error(),
                "Unable to close managed directory handle",
            )


def _windows_directory_api() -> _WindowsDirectoryApiProtocol:
    return _WindowsDirectoryApi()


def _record_secondary_close_failure(
    primary_error: BaseException, close_error: BaseException
) -> None:
    logging.getLogger(__name__).error(
        "M02 managed-directory handle cleanup failed",
        exc_info=close_error,
        extra={
            "event_code": M02StorageCleanupError.code,
            "primary_error_code": getattr(primary_error, "code", None),
        },
    )
    primary_error.add_note(
        f"Secondary managed-directory close failure: {type(close_error).__name__}"
    )


def _close_windows_handle_preserving_error(
    api: _WindowsDirectoryApiProtocol,
    handle: int,
    primary_error: BaseException,
) -> None:
    try:
        api.close_handle(handle)
    except BaseException as close_error:
        _record_secondary_close_failure(primary_error, close_error)


def _close_posix_descriptor_preserving_error(
    descriptor: int,
    primary_error: BaseException,
) -> None:
    try:
        os.close(descriptor)
    except BaseException as close_error:
        _record_secondary_close_failure(primary_error, close_error)


class _DirectoryHandleKind(str, Enum):
    WINDOWS = "windows"
    POSIX = "posix"


class _TrustedDirectory:
    """Pinned directory identity used for all managed relative filesystem actions."""

    def __init__(
        self,
        path: Path,
        handle: int,
        identity: tuple[int, int],
        windows_api: _WindowsDirectoryApiProtocol | None = None,
        handle_kind: _DirectoryHandleKind | None = None,
    ):
        self.path = path
        self._handle = handle
        self.identity = identity
        self._windows_api = windows_api
        self.handle_kind = handle_kind or (
            _DirectoryHandleKind.WINDOWS
            if windows_api is not None
            else _DirectoryHandleKind.POSIX
        )
        self._closed = False

    @classmethod
    def open(cls, path: Path) -> "_TrustedDirectory":
        if os.name == "nt":
            return cls._open_windows(path)
        return cls._open_posix(path)

    @classmethod
    def _open_posix(cls, path: Path) -> "_TrustedDirectory":
        descriptor: int | None = None
        ownership_transferred = False
        try:
            flags = (
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            descriptor = os.open(path, flags)
            opened = os.fstat(descriptor)
            if not stat.S_ISDIR(opened.st_mode):
                raise M02StorageConfigurationError(
                    "Managed directory is not a directory"
                )
            trusted = cls(
                path,
                descriptor,
                (opened.st_dev, opened.st_ino),
                handle_kind=_DirectoryHandleKind.POSIX,
            )
            ownership_transferred = True
            return trusted
        except BaseException as error:
            if descriptor is not None and not ownership_transferred:
                _close_posix_descriptor_preserving_error(descriptor, error)
            if isinstance(error, M02StorageConfigurationError):
                raise
            if isinstance(error, OSError):
                raise M02StorageConfigurationError(
                    "Managed directory is unavailable"
                ) from error
            raise

    @classmethod
    def _open_windows(
        cls,
        path: Path,
        api: _WindowsDirectoryApiProtocol | None = None,
    ) -> "_TrustedDirectory":
        api = api or _windows_directory_api()
        handle: int | None = None
        try:
            candidate_handle, attributes, identity = api.open_directory(path)
            if candidate_handle == -1:
                raise M02StorageConfigurationError(
                    "Managed directory is unavailable"
                )
            handle = candidate_handle
            if (
                not attributes & _WindowsDirectoryApi.FILE_ATTRIBUTE_DIRECTORY
                or attributes & _WindowsDirectoryApi.FILE_ATTRIBUTE_REPARSE_POINT
            ):
                raise M02StorageConfigurationError(
                    "Managed directory must not be a reparse point"
                )
            return cls(
                path,
                handle,
                identity,
                windows_api=api,
                handle_kind=_DirectoryHandleKind.WINDOWS,
            )
        except M02StorageConfigurationError as error:
            if handle is not None:
                _close_windows_handle_preserving_error(api, handle, error)
            raise
        except Exception as error:
            if handle is not None:
                _close_windows_handle_preserving_error(api, handle, error)
            if isinstance(error, M02StorageConfigurationError):
                raise
            raise M02StorageConfigurationError(
                "Managed directory is unavailable"
            ) from error

    def _verify_path_identity(self) -> None:
        try:
            if self._closed:
                raise M02StorageConfigurationError(
                    "Managed directory handle is closed"
                )
            if os.name != "nt":
                current = os.stat(self.path, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != self.identity:
                    raise M02StorageConfigurationError(
                        "Managed directory identity changed"
                    )
                return
            self._verify_windows_path_identity()
        except M02StorageConfigurationError:
            raise
        except OSError as error:
            raise M02StorageConfigurationError(
                "Managed directory identity is unavailable"
            ) from error

    def _verify_windows_path_identity(self) -> None:
        pinned = _TrustedDirectory._open_windows(self.path)
        primary_error: BaseException | None = None
        try:
            if pinned.identity != self.identity:
                raise M02StorageConfigurationError(
                    "Managed directory identity changed"
                )
        except BaseException as error:
            primary_error = error
            raise
        finally:
            try:
                pinned.close()
            except BaseException as close_error:
                if primary_error is None:
                    raise
                _record_secondary_close_failure(primary_error, close_error)

    def open_child(self, name: str, *, create: bool = False) -> "_TrustedDirectory":
        _validate_relative_name(name)
        if os.name != "nt":
            return self._open_posix_child(name, create=create)
        try:
            if create:
                self._verify_path_identity()
                (self.path / name).mkdir(exist_ok=True)
                self._verify_path_identity()
            child = _TrustedDirectory.open(self.path / name)
            self._verify_path_identity()
            return child
        except M02StorageConfigurationError:
            raise
        except OSError as error:
            raise M02StorageConfigurationError(
                "Managed child directory is unavailable"
            ) from error

    def _open_posix_child(
        self, name: str, *, create: bool = False
    ) -> "_TrustedDirectory":
        descriptor: int | None = None
        child: _TrustedDirectory | None = None
        ownership_transferred = False
        try:
            _validate_relative_name(name)
            if create:
                try:
                    os.mkdir(name, dir_fd=self._handle)
                except FileExistsError:
                    pass
            flags = (
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            descriptor = os.open(name, flags, dir_fd=self._handle)
            opened = os.fstat(descriptor)
            if not stat.S_ISDIR(opened.st_mode):
                raise M02StorageConfigurationError(
                    "Managed child is not a directory"
                )
            child = _TrustedDirectory(
                self.path / name,
                descriptor,
                (opened.st_dev, opened.st_ino),
                handle_kind=_DirectoryHandleKind.POSIX,
            )
            self._verify_path_identity()
            child._verify_path_identity()
            ownership_transferred = True
            return child
        except BaseException as error:
            if descriptor is not None and not ownership_transferred:
                if child is not None:
                    child._closed = True
                _close_posix_descriptor_preserving_error(descriptor, error)
            if isinstance(error, M02StorageConfigurationError):
                raise
            if isinstance(error, OSError):
                raise M02StorageConfigurationError(
                    "Managed child directory is unavailable"
                ) from error
            raise

    def create_file(self, name: str) -> BinaryIO:
        try:
            _validate_relative_name(name)
            flags = (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_BINARY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            if os.name != "nt":
                descriptor = os.open(name, flags, 0o600, dir_fd=self._handle)
            else:
                self._verify_path_identity()
                descriptor = os.open(self.path / name, flags, 0o600)
            try:
                self._verify_path_identity()
            except BaseException:
                os.close(descriptor)
                try:
                    if os.name != "nt":
                        os.unlink(name, dir_fd=self._handle)
                    else:
                        os.unlink(self.path / name)
                except OSError:
                    pass
                raise
            return io.BufferedWriter(io.FileIO(descriptor, mode="wb", closefd=True))
        except M02StorageConfigurationError:
            raise
        except OSError as error:
            raise M02StorageConfigurationError(
                "Managed file could not be created"
            ) from error

    def open_file(self, name: str) -> io.BufferedReader:
        try:
            _validate_relative_name(name)
            flags = (
                os.O_RDONLY
                | getattr(os, "O_BINARY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            if os.name != "nt":
                descriptor = os.open(name, flags, dir_fd=self._handle)
            else:
                self._verify_path_identity()
                descriptor = os.open(self.path / name, flags)
            try:
                self._verify_path_identity()
            except BaseException:
                os.close(descriptor)
                raise
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode):
                os.close(descriptor)
                raise M02StorageConfigurationError(
                    "Managed object is not a regular file"
                )
            return io.BufferedReader(io.FileIO(descriptor, mode="rb", closefd=True))
        except M02StorageConfigurationError:
            raise
        except OSError as error:
            raise M02StorageConfigurationError(
                "Managed object is unavailable"
            ) from error

    def create_link_from(
        self,
        source: "_TrustedDirectory",
        source_name: str,
        destination_name: str,
    ) -> None:
        _validate_relative_name(source_name)
        _validate_relative_name(destination_name)
        if os.name != "nt":
            os.link(
                source_name,
                destination_name,
                src_dir_fd=source._handle,
                dst_dir_fd=self._handle,
                follow_symlinks=False,
            )
        else:
            source._verify_path_identity()
            self._verify_path_identity()
            os.link(source.path / source_name, self.path / destination_name)

    def verify_link_from(self, source: "_TrustedDirectory") -> None:
        source._verify_path_identity()
        self._verify_path_identity()

    def unlink(self, name: str, *, missing_ok: bool = True) -> None:
        _validate_relative_name(name)
        try:
            if os.name != "nt":
                os.unlink(name, dir_fd=self._handle)
            else:
                self._verify_path_identity()
                os.unlink(self.path / name)
            self._verify_path_identity()
        except FileNotFoundError:
            if not missing_ok:
                raise

    def close(self) -> None:
        if self._closed:
            return
        if self.handle_kind == _DirectoryHandleKind.POSIX:
            os.close(self._handle)
        else:
            assert self._windows_api is not None
            self._windows_api.close_handle(self._handle)
        self._closed = True

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


def _validate_relative_name(name: str) -> None:
    if (
        not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or ":" in name
    ):
        raise M02StorageConfigurationError("Managed operation requires a relative name")


class StagedResourceState(str, Enum):
    STAGED_ONLY = "staged-only"
    FINAL_CREATED_UNCOMMITTED = "final-created-uncommitted"
    COMMITTED = "committed"
    SHARED_EXISTING = "shared-existing"
    CLEANUP_PENDING = "cleanup-pending"
    CLEANED = "cleaned"
    CLEANUP_FAILED = "cleanup-failed"


_ALLOWED_RESOURCE_TRANSITIONS = {
    StagedResourceState.STAGED_ONLY: {
        StagedResourceState.FINAL_CREATED_UNCOMMITTED,
        StagedResourceState.SHARED_EXISTING,
        StagedResourceState.CLEANUP_PENDING,
    },
    StagedResourceState.FINAL_CREATED_UNCOMMITTED: {
        StagedResourceState.COMMITTED,
        StagedResourceState.CLEANUP_PENDING,
    },
    StagedResourceState.SHARED_EXISTING: {
        StagedResourceState.COMMITTED,
        StagedResourceState.CLEANUP_PENDING,
    },
    StagedResourceState.COMMITTED: {StagedResourceState.CLEANUP_PENDING},
    StagedResourceState.CLEANUP_PENDING: {
        StagedResourceState.CLEANED,
        StagedResourceState.CLEANUP_FAILED,
    },
    StagedResourceState.CLEANUP_FAILED: {StagedResourceState.CLEANUP_PENDING},
    StagedResourceState.CLEANED: set(),
}


@dataclass
class StagedUpload:
    storage: "ManagedLocalStorage"
    temporary_name: str
    original_filename: str
    extension: str
    declared_mime_type: str
    validated_media_type: str
    detected_text_encoding: str | None = None
    sha256_checksum: str = ""
    byte_size: int = 0
    final_storage_key: str | None = None
    final_directory: _TrustedDirectory | None = None
    final_object_name: str | None = None
    cleaned: bool = False
    temporary_removed: bool = False
    final_removed: bool = False
    final_directory_closed: bool = False
    cleanup_failure_steps: tuple[str, ...] = ()
    _resource_state: StagedResourceState = StagedResourceState.STAGED_ONLY
    _cleanup_origin_state: StagedResourceState | None = None

    @property
    def temporary_path(self) -> Path:
        return self.storage.temporary_root / self.temporary_name

    def open_write(self) -> BinaryIO:
        return self.storage._temporary_directory.create_file(self.temporary_name)

    def open_read(self) -> io.BufferedReader:
        return self.storage._temporary_directory.open_file(self.temporary_name)

    @property
    def resource_state(self) -> str:
        return self._resource_state.value

    @property
    def committed(self) -> bool:
        return (
            self._resource_state == StagedResourceState.COMMITTED
            or self._cleanup_origin_state == StagedResourceState.COMMITTED
        )

    def _transition(self, target: StagedResourceState) -> None:
        if target not in _ALLOWED_RESOURCE_TRANSITIONS[self._resource_state]:
            raise M02StorageConfigurationError(
                f"Invalid staged-resource transition: "
                f"{self._resource_state.value} -> {target.value}"
            )
        self._resource_state = target

    def mark_final(
        self,
        storage_key: str,
        directory: _TrustedDirectory,
        object_name: str,
    ) -> None:
        self._transition(StagedResourceState.FINAL_CREATED_UNCOMMITTED)
        self.final_storage_key = storage_key
        self.final_directory = directory
        self.final_object_name = object_name

    def mark_shared_existing(self) -> None:
        self._transition(StagedResourceState.SHARED_EXISTING)

    def mark_committed(self) -> None:
        if self._resource_state == StagedResourceState.STAGED_ONLY:
            self.mark_shared_existing()
        self._transition(StagedResourceState.COMMITTED)

    def cleanup(self, *, primary_error: BaseException | None = None) -> None:
        if self.cleaned:
            return
        if self._resource_state == StagedResourceState.CLEANUP_FAILED:
            self._transition(StagedResourceState.CLEANUP_PENDING)
        else:
            self._cleanup_origin_state = self._resource_state
            self._transition(StagedResourceState.CLEANUP_PENDING)
        failures: list[BaseException] = []
        failure_steps: list[str] = []
        if not self.temporary_removed:
            try:
                self.storage._temporary_directory.unlink(self.temporary_name)
                self.temporary_removed = True
            except BaseException as error:
                failures.append(error)
                failure_steps.append("STAGED_UNLINK")
        owns_uncommitted_final = (
            self._cleanup_origin_state
            == StagedResourceState.FINAL_CREATED_UNCOMMITTED
        )
        if (
            not failures
            and self.final_storage_key is not None
            and owns_uncommitted_final
            and self.final_directory is not None
            and self.final_object_name is not None
            and not self.final_removed
        ):
            try:
                self.final_directory.unlink(self.final_object_name)
                self.final_removed = True
            except BaseException as error:
                failures.append(error)
                failure_steps.append("FINAL_UNLINK")
        if (
            not failures
            and self.final_directory is not None
            and owns_uncommitted_final
            and not self.final_directory_closed
        ):
            try:
                self.final_directory.close()
                self.final_directory_closed = True
            except BaseException as error:
                failures.append(error)
                failure_steps.append("FINAL_DIRECTORY_CLOSE")
            else:
                self.final_directory = None
        elif (
            not failures
            and self.final_directory is not None
            and self._cleanup_origin_state == StagedResourceState.COMMITTED
            and not self.final_directory_closed
        ):
            try:
                self.final_directory.close()
                self.final_directory_closed = True
            except BaseException as error:
                failures.append(error)
                failure_steps.append("FINAL_DIRECTORY_CLOSE")
            else:
                self.final_directory = None
        if failures:
            self.cleanup_failure_steps = tuple(failure_steps)
            self._transition(StagedResourceState.CLEANUP_FAILED)
            logging.getLogger(__name__).error(
                "M02 staged-resource cleanup failed",
                extra={
                    "event_code": M02StorageCleanupError.code,
                    "primary_error_code": getattr(primary_error, "code", None),
                },
            )
            raise M02StorageCleanupError(
                "A staged M02 resource could not be cleaned up",
                primary_error=primary_error,
                cleanup_errors=tuple(failures),
                cleanup_steps=self.cleanup_failure_steps,
                operational_diagnostics=(
                    ("M02_FINAL_PLACEMENT_SUCCEEDED",)
                    if owns_uncommitted_final
                    else ()
                ),
            )
        self.cleanup_failure_steps = ()
        self._transition(StagedResourceState.CLEANED)
        self.cleaned = True


def safe_original_filename(value: str | None) -> str:
    candidate = (value or "").replace("\\", "/").split("/")[-1].strip()
    candidate = "".join(
        character
        for character in candidate
        if ord(character) >= 32 and character not in {'"', "\r", "\n"}
    )
    if not candidate or candidate in {".", ".."}:
        raise M02FileError("M02_UNSAFE_FILENAME", "A safe filename is required")
    if len(candidate) > 255:
        stem = Path(candidate).stem[:200]
        suffix = Path(candidate).suffix[:16]
        candidate = f"{stem}{suffix}"
    return candidate


class ManagedLocalStorage:
    def __init__(self, root: Path):
        self.root = root
        self.temporary_root = root / ".temporary"
        self.object_root = root / "objects"
        self._root_directory = _TrustedDirectory.open(root)
        try:
            self._temporary_directory = self._root_directory.open_child(
                ".temporary", create=True
            )
            self._object_directory = self._root_directory.open_child(
                "objects", create=True
            )
        except BaseException:
            self._root_directory.close()
            raise
        self._closed = False

    @classmethod
    def from_environment(cls) -> "ManagedLocalStorage":
        configured = os.getenv("M02_STORAGE_ROOT", "").strip()
        if not configured:
            raise M02StorageConfigurationError("M02_STORAGE_ROOT is required")
        raw_root = Path(configured)
        if not raw_root.is_absolute():
            raise M02StorageConfigurationError("M02_STORAGE_ROOT must be absolute")
        cls._reject_symlink(raw_root)
        root = raw_root.resolve(strict=False)
        cls._validate_safe_root(root)
        try:
            root.mkdir(parents=True, exist_ok=True)
            cls._reject_symlink(root)
        except OSError as error:
            raise M02StorageConfigurationError(
                "M02_STORAGE_ROOT is unavailable or not writable"
            ) from error
        storage = cls(root)
        probe_name = f".write-probe-{uuid4().hex}"
        try:
            with storage._root_directory.create_file(probe_name) as handle:
                handle.write(b"m02")
            storage._root_directory.unlink(probe_name)
        except BaseException:
            storage.close()
            raise
        return storage

    @staticmethod
    def _validate_safe_root(root: Path) -> None:
        repository_root = Path(__file__).resolve().parents[3]
        cwd = Path.cwd().resolve(strict=False)
        unsafe_roots = {
            repository_root,
            repository_root / "frontend",
            repository_root / "frontend" / "public",
            repository_root / "frontend" / "static",
            repository_root / "backend",
            repository_root / "public",
            repository_root / "static",
            cwd,
        }
        for unsafe in unsafe_roots:
            unsafe = unsafe.resolve(strict=False)
            if (
                root == unsafe
                or unsafe in root.parents
                or root in unsafe.parents
            ):
                raise M02StorageConfigurationError(
                    "M02_STORAGE_ROOT must be isolated from repository, cwd, public, and static roots"
                )

    @staticmethod
    def _reject_symlink(path: Path) -> None:
        try:
            if path.exists() or path.is_symlink():
                if stat.S_ISLNK(path.lstat().st_mode):
                    raise M02StorageConfigurationError(
                        "Managed storage paths must not be symbolic links"
                    )
        except OSError as error:
            raise M02StorageConfigurationError(
                "Managed storage path metadata is unavailable"
            ) from error

    @staticmethod
    def _assert_contained(root: Path, path: Path) -> Path:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=False)
        if resolved == resolved_root or resolved_root in resolved.parents:
            return resolved
        raise M02StorageConfigurationError("Managed storage path escaped its root")

    def _validate_managed_path(self, path: Path, *, require_exists: bool = False) -> Path:
        self._reject_symlink(self.root)
        self._reject_symlink(self.temporary_root)
        self._reject_symlink(self.object_root)
        resolved = self._assert_contained(self.root, path)
        current = path
        while current != self.root:
            self._reject_symlink(current)
            current = current.parent
        if require_exists and not path.exists():
            raise M02StorageConfigurationError("Managed storage object is unavailable")
        return resolved

    def new_staged_upload(
        self,
        *,
        original_filename: str,
        extension: str,
        declared_mime_type: str,
        validated_media_type: str,
    ) -> StagedUpload:
        return StagedUpload(
            storage=self,
            temporary_name=f"{uuid4().hex}.upload",
            original_filename=original_filename,
            extension=extension,
            declared_mime_type=declared_mime_type,
            validated_media_type=validated_media_type,
        )

    def place(self, staged: StagedUpload) -> str:
        if staged.storage is not self:
            raise M02StorageConfigurationError("Staged resource belongs to another root")
        shard_name = uuid4().hex[:2]
        object_name = uuid4().hex
        storage_key = f"objects/{shard_name}/{object_name}"
        shard = self._object_directory.open_child(shard_name, create=True)
        ownership_transferred = False
        try:
            shard.create_link_from(
                self._temporary_directory,
                staged.temporary_name,
                object_name,
            )
            staged.mark_final(storage_key, shard, object_name)
            ownership_transferred = True
            shard.verify_link_from(self._temporary_directory)
        except FileExistsError:
            return self.place(staged)
        except OSError as error:
            raise M02FileError(
                "M02_PRESERVATION_FAILED", "The source could not be preserved"
            ) from error
        finally:
            if not ownership_transferred:
                shard.close()
        return storage_key

    def resolve_key(self, storage_key: str) -> Path:
        key_path = PurePosixPath(storage_key)
        if (
            key_path.is_absolute()
            or ".." in key_path.parts
            or not key_path.parts
            or key_path.parts[0] != "objects"
        ):
            raise M02StorageConfigurationError("Invalid persisted storage key")
        candidate = self.root / Path(*key_path.parts)
        return self._validate_managed_path(candidate)

    def open_key(self, storage_key: str) -> M02OwnedReader:
        key_path = self._validated_key(storage_key)
        shard = self._object_directory.open_child(key_path.parts[1])
        try:
            return M02OwnedReader(shard.open_file(key_path.parts[2]))
        finally:
            shard.close()

    @staticmethod
    def _validated_key(storage_key: str) -> PurePosixPath:
        key_path = PurePosixPath(storage_key)
        if (
            key_path.is_absolute()
            or len(key_path.parts) != 3
            or key_path.parts[0] != "objects"
        ):
            raise M02StorageConfigurationError("Invalid persisted storage key")
        _validate_relative_name(key_path.parts[1])
        _validate_relative_name(key_path.parts[2])
        return key_path

    def delete_key(self, storage_key: str) -> None:
        shard: _TrustedDirectory | None = None
        try:
            key_path = self._validated_key(storage_key)
            shard = self._object_directory.open_child(key_path.parts[1])
            shard.unlink(key_path.parts[2])
        except (OSError, M02StorageConfigurationError) as error:
            logging.getLogger(__name__).error(
                "M02 cleanup failed for a managed persisted object",
                extra={"event_code": M02StorageCleanupError.code},
            )
            raise M02StorageCleanupError(
                "A managed persisted object could not be cleaned up"
            ) from error
        finally:
            if shard is not None:
                shard.close()

    def cleanup_temporary(self, temporary_path: Path | None) -> None:
        if temporary_path is None:
            return
        try:
            if temporary_path.parent != self.temporary_root:
                raise M02StorageConfigurationError("Temporary path escaped managed root")
            self._temporary_directory.unlink(temporary_path.name)
        except (OSError, M02StorageConfigurationError) as error:
            logging.getLogger(__name__).error(
                "M02 cleanup failed for a managed temporary object",
                extra={"event_code": M02StorageCleanupError.code},
            )
            raise M02StorageCleanupError(
                "A managed temporary object could not be cleaned up"
            ) from error

    def close(self) -> None:
        if self._closed:
            return
        failures: list[BaseException] = []
        failure_steps: list[str] = []
        for step, directory in (
            ("TEMP_DIRECTORY_CLOSE", self._temporary_directory),
            ("OBJECT_DIRECTORY_CLOSE", self._object_directory),
            ("ROOT_DIRECTORY_CLOSE", self._root_directory),
        ):
            try:
                directory.close()
            except BaseException as error:
                failures.append(error)
                failure_steps.append(step)
        if failures:
            logging.getLogger(__name__).error(
                "M02 managed-storage directory cleanup failed",
                extra={"event_code": M02StorageCleanupError.code},
            )
            raise M02StorageCleanupError(
                "Managed storage directory cleanup could not be completed",
                cleanup_errors=tuple(failures),
                cleanup_steps=tuple(failure_steps),
            )
        self._closed = True

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


async def stage_and_validate_upload(
    storage: ManagedLocalStorage, upload: UploadFile
) -> StagedUpload:
    filename = safe_original_filename(upload.filename)
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise M02FileError(
            "M02_UNSUPPORTED_EXTENSION", "The submitted file type is not supported"
        )
    declared_mime = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if declared_mime not in MIME_BY_EXTENSION[extension]:
        raise M02FileError(
            "M02_MIME_MISMATCH", "The declared media type does not match the file type"
        )

    staged = storage.new_staged_upload(
        original_filename=filename,
        extension=extension,
        declared_mime_type=declared_mime,
        validated_media_type=VALIDATED_MEDIA_BY_EXTENSION[extension],
    )
    digest = hashlib.sha256()
    byte_size = 0
    try:
        with staged.open_write() as target:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break
                byte_size += len(chunk)
                if byte_size > MAX_FILE_BYTES:
                    raise M02FileError(
                        "M02_FILE_TOO_LARGE", "The file exceeds the 25 MiB limit"
                    )
                digest.update(chunk)
                target.write(chunk)
        if byte_size == 0:
            raise M02FileError("M02_EMPTY_FILE", "The file is empty")
        staged.detected_text_encoding = _validate_type(staged, extension)
        staged.sha256_checksum = digest.hexdigest()
        staged.byte_size = byte_size
        return staged
    except BaseException as primary_error:
        try:
            staged.cleanup(primary_error=primary_error)
        except M02StorageCleanupError as cleanup_error:
            raise cleanup_error from primary_error
        raise
    finally:
        await upload.close()


def _validate_type(staged: StagedUpload, extension: str) -> str | None:
    if extension == ".pdf":
        with staged.open_read() as source:
            if source.read(5) != b"%PDF-":
                raise M02FileError(
                    "M02_SIGNATURE_MISMATCH", "The PDF signature is invalid"
                )
        return None
    if extension == ".xlsx":
        with staged.open_read() as source:
            _validate_xlsx(source)
        return None
    with staged.open_read() as source:
        return _validate_text_content(source.read())


def _validate_text(path: Path) -> str:
    return _validate_text_content(path.read_bytes())


def _validate_text_content(content: bytes) -> str:
    if b"\x00" in content:
        raise M02FileError(
            "M02_UNSUPPORTED_BINARY_TEXT", "Binary or NUL-bearing text is not accepted"
        )
    if content.startswith(b"\xef\xbb\xbf"):
        candidates = (("utf-8-sig", "utf-8-bom"),)
    else:
        candidates = (
            ("utf-8", "utf-8"),
            ("cp1255", "windows-1255"),
            ("iso8859_8", "iso-8859-8"),
            ("latin-1", "latin-1"),
        )
    detected: tuple[str, str, float] | None = None
    for codec, label in candidates:
        try:
            decoded = content.decode(codec)
        except UnicodeDecodeError:
            continue
        score = _text_likeness_score(decoded)
        if score is not None and (detected is None or score > detected[2]):
            detected = (codec, label, score)
    if detected is None:
        raise M02FileError(
            "M02_UNSUPPORTED_BINARY_TEXT",
            "Binary or unsupported text content is not accepted",
        )
    return detected[1]


def _text_likeness_score(decoded: str) -> float | None:
    control_count = sum(
        1
        for character in decoded
        if (
            ord(character) < 32
            and character not in "\t\r\n\f"
        )
        or 0x7F <= ord(character) <= 0x9F
    )
    meaningful_count = sum(
        1
        for character in decoded
        if character.isalnum()
        or character.isspace()
        or character in ".,;:!?-_/'\"()[]{}<>@#$%^&*+=|\\"
        or "\u0590" <= character <= "\u05ff"
    )
    if (
        control_count / max(len(decoded), 1) > 0.02
        or meaningful_count / max(len(decoded), 1) < 0.70
        or (len(decoded) >= 32 and len(set(decoded)) < 3)
    ):
        return None
    hebrew_count = sum("\u0590" <= character <= "\u05ff" for character in decoded)
    latin_count = sum(
        ("a" <= character.lower() <= "z") or "\u00c0" <= character <= "\u024f"
        for character in decoded
    )
    mixed_script_penalty = 0.25 if hebrew_count and latin_count else 0.0
    return meaningful_count / max(len(decoded), 1) - mixed_script_penalty


def _validate_xlsx(path: Path | BinaryIO) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            lowered = {name.lower() for name in names}
            if "[content_types].xml" not in lowered or "xl/workbook.xml" not in lowered:
                raise M02FileError(
                    "M02_INVALID_OOXML_CONTAINER", "The XLSX container identity is invalid"
                )
            total_size = 0
            for item in archive.infolist():
                posix_name = PurePosixPath(item.filename.replace("\\", "/"))
                if (
                    posix_name.is_absolute()
                    or ".." in posix_name.parts
                    or re.match(r"^[A-Za-z]:", item.filename)
                ):
                    raise M02FileError(
                        "M02_INVALID_OOXML_CONTAINER", "The XLSX container has an unsafe path"
                    )
                if item.flag_bits & 0x1:
                    raise M02FileError(
                        "M02_INVALID_OOXML_CONTAINER", "Encrypted XLSX members are not accepted"
                    )
                lowered_name = item.filename.lower()
                if "vbaproject" in lowered_name or lowered_name.endswith((".bin", ".vba")):
                    raise M02FileError(
                        "M02_INVALID_OOXML_CONTAINER", "Macro-enabled XLSX content is not accepted"
                    )
                total_size += item.file_size
                if total_size > MAX_FILE_BYTES:
                    raise M02FileError(
                        "M02_INVALID_OOXML_CONTAINER",
                        "The XLSX declared uncompressed size exceeds 25 MiB",
                    )
            content_types = archive.read("[Content_Types].xml").lower()
            if b"macroenabled" in content_types or b"vba" in content_types:
                raise M02FileError(
                    "M02_INVALID_OOXML_CONTAINER", "Macro-enabled workbook types are not accepted"
                )
    except M02FileError:
        raise
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        raise M02FileError(
            "M02_INVALID_OOXML_CONTAINER", "The XLSX container is invalid"
        ) from error
