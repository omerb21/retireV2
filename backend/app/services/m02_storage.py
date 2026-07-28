from __future__ import annotations

import hashlib
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
        root = raw_root.resolve(strict=False)
        cls._validate_safe_root(root)
        try:
            root.mkdir(parents=True, exist_ok=True)
            (root / ".temporary").mkdir(exist_ok=True)
            (root / "objects").mkdir(exist_ok=True)
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
        unsafe_roots = {
            repository_root,
            repository_root / "frontend",
            repository_root / "backend",
            repository_root / "public",
            repository_root / "static",
        }
        for unsafe in unsafe_roots:
            unsafe = unsafe.resolve(strict=False)
            if root == unsafe or unsafe in root.parents:
                raise M02StorageConfigurationError(
                    "M02_STORAGE_ROOT must be outside repository, home, cwd, public, and static roots"
                )

    def new_temporary_path(self) -> Path:
        return self.temporary_root / f"{uuid4().hex}.upload"

    def place(self, temporary_path: Path) -> str:
        storage_key = f"objects/{uuid4().hex[:2]}/{uuid4().hex}"
        destination = self.resolve_key(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
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
        resolved = (self.root / Path(*key_path.parts)).resolve(strict=False)
        if self.root not in resolved.parents:
            raise M02StorageConfigurationError("Storage key escaped managed root")
        return resolved

    def delete_key(self, storage_key: str) -> None:
        try:
            self.resolve_key(storage_key).unlink(missing_ok=True)
        except OSError:
            pass

    def cleanup_temporary(self, temporary_path: Path | None) -> None:
        if temporary_path is None:
            return
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
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
    detected: tuple[str, str] | None = None
    if content.startswith(b"\xef\xbb\xbf"):
        candidates = (("utf-8-sig", "utf-8-bom"),)
    else:
        candidates = (
            ("utf-8", "utf-8"),
            ("cp1255", "windows-1255"),
            ("iso8859_8", "iso-8859-8"),
            ("latin-1", "latin-1"),
        )
    decoded = ""
    for codec, label in candidates:
        try:
            decoded = content.decode(codec)
            detected = (codec, label)
            break
        except UnicodeDecodeError:
            continue
    if detected is None:
        raise M02FileError(
            "M02_UNSUPPORTED_TEXT_ENCODING", "The text encoding is not supported"
        )
    control_count = sum(
        1 for character in decoded if ord(character) < 32 and character not in "\t\r\n\f"
    )
    if control_count / max(len(decoded), 1) > 0.02:
        raise M02FileError(
            "M02_UNSUPPORTED_BINARY_TEXT", "Binary text content is not accepted"
        )
    return detected[1]


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
