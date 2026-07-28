from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import shutil
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
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


class M02FileError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class StagedUpload:
    temporary_path: Path
    original_filename: str
    extension: str
    declared_mime_type: str
    validated_media_type: str
    detected_text_encoding: str | None
    sha256_checksum: str
    byte_size: int


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
            for managed in (root / ".temporary", root / "objects"):
                cls._reject_symlink(managed)
                managed.mkdir(exist_ok=True)
                cls._reject_symlink(managed)
                cls._assert_contained(root, managed)
            probe = root / f".write-probe-{uuid4().hex}"
            with probe.open("x", encoding="ascii") as handle:
                handle.write("m02")
            probe.unlink()
        except OSError as error:
            raise M02StorageConfigurationError(
                "M02_STORAGE_ROOT is unavailable or not writable"
            ) from error
        return cls(root)

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

    def new_temporary_path(self) -> Path:
        self._validate_managed_path(self.temporary_root, require_exists=True)
        return self.temporary_root / f"{uuid4().hex}.upload"

    def place(self, temporary_path: Path) -> str:
        self._validate_managed_path(temporary_path, require_exists=True)
        storage_key = f"objects/{uuid4().hex[:2]}/{uuid4().hex}"
        destination = self.resolve_key(storage_key)
        self._reject_symlink(destination.parent)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._validate_managed_path(destination.parent, require_exists=True)
        self._reject_symlink(destination)
        try:
            os.link(temporary_path, destination)
        except FileExistsError:
            return self.place(temporary_path)
        except OSError as error:
            raise M02FileError(
                "M02_PRESERVATION_FAILED", "The source could not be preserved"
            ) from error
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

    def open_key(self, storage_key: str) -> io.BufferedReader:
        path = self.resolve_key(storage_key)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor: int | None = None
        try:
            before = path.lstat()
            if not stat.S_ISREG(before.st_mode):
                raise M02StorageConfigurationError("Preserved source is not a regular file")
            descriptor = os.open(path, flags)
            opened = os.fstat(descriptor)
            after = path.lstat()
            if (
                not stat.S_ISREG(opened.st_mode)
                or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
                or (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino)
            ):
                os.close(descriptor)
                descriptor = None
                raise M02StorageConfigurationError(
                    "Preserved source changed during secure open"
                )
            self._validate_managed_path(path, require_exists=True)
            stream = io.BufferedReader(io.FileIO(descriptor, mode="rb", closefd=True))
            descriptor = None
            return stream
        except (OSError, M02StorageConfigurationError):
            if descriptor is not None:
                os.close(descriptor)
            raise

    def delete_key(self, storage_key: str) -> None:
        try:
            path = self.resolve_key(storage_key)
            self._reject_symlink(path)
            path.unlink(missing_ok=True)
        except (OSError, M02StorageConfigurationError) as error:
            logging.getLogger(__name__).error(
                "M02 cleanup failed for a managed persisted object",
                extra={"event_code": M02StorageCleanupError.code},
            )
            raise M02StorageCleanupError(
                "A managed persisted object could not be cleaned up"
            ) from error

    def cleanup_temporary(self, temporary_path: Path | None) -> None:
        if temporary_path is None:
            return
        try:
            self._validate_managed_path(temporary_path)
            self._reject_symlink(temporary_path)
            temporary_path.unlink(missing_ok=True)
        except (OSError, M02StorageConfigurationError) as error:
            logging.getLogger(__name__).error(
                "M02 cleanup failed for a managed temporary object",
                extra={"event_code": M02StorageCleanupError.code},
            )
            raise M02StorageCleanupError(
                "A managed temporary object could not be cleaned up"
            ) from error


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

    temporary_path = storage.new_temporary_path()
    digest = hashlib.sha256()
    byte_size = 0
    try:
        with temporary_path.open("xb") as target:
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
        encoding = _validate_type(temporary_path, extension)
        return StagedUpload(
            temporary_path=temporary_path,
            original_filename=filename,
            extension=extension,
            declared_mime_type=declared_mime,
            validated_media_type=VALIDATED_MEDIA_BY_EXTENSION[extension],
            detected_text_encoding=encoding,
            sha256_checksum=digest.hexdigest(),
            byte_size=byte_size,
        )
    except BaseException:
        storage.cleanup_temporary(temporary_path)
        raise
    finally:
        await upload.close()


def _validate_type(path: Path, extension: str) -> str | None:
    if extension == ".pdf":
        with path.open("rb") as source:
            if source.read(5) != b"%PDF-":
                raise M02FileError(
                    "M02_SIGNATURE_MISMATCH", "The PDF signature is invalid"
                )
        return None
    if extension == ".xlsx":
        _validate_xlsx(path)
        return None
    return _validate_text(path)


def _validate_text(path: Path) -> str:
    content = path.read_bytes()
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


def _validate_xlsx(path: Path) -> None:
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
