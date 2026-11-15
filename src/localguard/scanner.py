"""Local-only checks for accidentally committed credentials."""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

MAX_FILE_SIZE = 1_000_000
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

RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    (
        "github-token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    (
        "credential-assignment",
        re.compile(
            r"""(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|secret|token)\b"""
            r"""\s*[:=]\s*['"]?([A-Za-z0-9/_+=.-]{8,})"""
        ),
    ),
)
PLACEHOLDER_VALUES = {
    "changeme",
    "example",
    "dummy",
    "placeholder",
    "redacted",
    "replace_me",
    "your_token",
    "your_api_key",
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


@dataclass(frozen=True)
class ScanResult:
    findings: list[Finding]
    errors: list[str]
    files_scanned: int


def _is_placeholder(line: str) -> bool:
    lowered = line.lower()
    return any(value in lowered for value in PLACEHOLDER_VALUES)


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


def scan_directory(directory: Path) -> ScanResult:
    """Scan a local directory without making network requests or exposing matched values."""
    root = directory.resolve()
    findings: list[Finding] = []
    errors: list[str] = []
    files_scanned = 0

    for path in _iter_files(root):
        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                continue
            content = path.read_bytes()
        except OSError as exc:
            errors.append(f"{path}: {exc}")
            continue

        if b"\x00" in content:
            continue
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            continue

        files_scanned += 1
        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule, pattern in RULES:
                match = pattern.search(line)
                if match is None:
                    continue
                if rule == "credential-assignment" and _is_placeholder(line):
                    continue
                findings.append(
                    Finding(
                        path=path.relative_to(root).as_posix(),
                        line=line_number,
                        rule=rule,
                        message="Potential credential detected; matched value is hidden.",
                    )
                )

    return ScanResult(findings=findings, errors=errors, files_scanned=files_scanned)
