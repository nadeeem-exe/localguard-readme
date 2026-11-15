"""Offline metadata inventory for files in a local directory."""

from __future__ import annotations

import os
import re
import struct
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

MAX_FILE_SIZE = 1_000_000
MAX_MEMBER_SIZE = 256_000
IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "build",
    "dist",
}
OFFICE_PROPERTIES = {
    "title": "title",
    "subject": "subject",
    "creator": "author",
    "keywords": "keywords",
    "description": "description",
    "lastModifiedBy": "last_modified_by",
    "created": "created",
    "modified": "modified",
}


@dataclass(frozen=True)
class MetadataEntry:
    path: str
    format: str
    size_bytes: int
    modified_utc: str
    metadata: dict[str, str]

    def to_dict(self) -> dict[str, str | int | dict[str, str]]:
        return asdict(self)


@dataclass(frozen=True)
class MetadataResult:
    files_inspected: int
    entries: list[MetadataEntry]
    errors: list[str]


def _iter_files(root: Path):
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if name not in IGNORED_DIRECTORIES
            and not (current_path / name).is_symlink()
        ]
        for filename in filenames:
            path = current_path / filename
            if not path.is_symlink():
                yield path


def _office_metadata(path: Path) -> dict[str, str]:
    try:
        with zipfile.ZipFile(path) as archive:
            info = archive.getinfo("docProps/core.xml")
            if info.file_size > MAX_MEMBER_SIZE:
                return {}
            content = archive.read(info)
    except (KeyError, OSError, zipfile.BadZipFile):
        return {}

    root = ElementTree.fromstring(content)
    fields: dict[str, str] = {}
    for element in root.iter():
        name = element.tag.rsplit("}", 1)[-1]
        key = OFFICE_PROPERTIES.get(name)
        value = (element.text or "").strip()
        if key and value:
            fields[key] = value
    return fields


def _pdf_metadata(content: bytes) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key in ("Title", "Author", "Subject", "Keywords", "Creator", "Producer"):
        pattern = rb"/" + key.encode("ascii") + rb"\s*\(([^()]*(?:\\.[^()]*)*)\)"
        match = re.search(pattern, content)
        if match:
            value = match.group(1).decode("latin-1", errors="replace")
            value = re.sub(r"\\([\\()])", r"\1", value).strip()
            if value:
                fields[key.lower()] = value
    return fields


def _image_metadata(format_name: str, content: bytes) -> dict[str, str]:
    if format_name == "JPEG":
        return {"exif_present": "true"} if b"Exif\x00\x00" in content else {}
    if format_name == "TIFF":
        return {"exif_possible": "true"}
    if format_name == "PNG":
        return {"text_metadata_present": "true"} if b"tEXt" in content or b"iTXt" in content else {}
    return {}


def _inspect_file(path: Path) -> tuple[str, dict[str, str]]:
    extension = path.suffix.lower()
    if extension in {".docx", ".xlsx", ".pptx"}:
        return "Office Open XML", _office_metadata(path)

    content = path.read_bytes()
    if content.startswith(b"%PDF-"):
        return "PDF", _pdf_metadata(content)
    if content.startswith(b"\xff\xd8\xff"):
        return "JPEG", _image_metadata("JPEG", content)
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG", _image_metadata("PNG", content)
    if content.startswith((b"II*\x00", b"MM\x00*")):
        if len(content) >= 8:
            endian = "<" if content[:2] == b"II" else ">"
            offset = struct.unpack(endian + "I", content[4:8])[0]
            if offset < len(content):
                return "TIFF", _image_metadata("TIFF", content)
        return "TIFF", {}
    return path.suffix.lstrip(".").upper() or "unknown", {}


def inspect_directory(directory: Path) -> MetadataResult:
    """Inventory basic file metadata and common document metadata, without network access."""
    root = directory.resolve()
    entries: list[MetadataEntry] = []
    errors: list[str] = []
    files_inspected = 0

    for path in _iter_files(root):
        try:
            stat = path.stat()
            if stat.st_size > MAX_FILE_SIZE:
                continue
            format_name, metadata = _inspect_file(path)
        except (OSError, ValueError, ElementTree.ParseError, zipfile.LargeZipFile) as exc:
            errors.append(f"{path}: {exc}")
            continue

        files_inspected += 1
        if metadata:
            modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            entries.append(
                MetadataEntry(
                    path=path.relative_to(root).as_posix(),
                    format=format_name,
                    size_bytes=stat.st_size,
                    modified_utc=modified,
                    metadata=metadata,
                )
            )

    return MetadataResult(
        files_inspected=files_inspected,
        entries=entries,
        errors=errors,
    )
