"""Command-line interface for LocalGuard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from localguard.metadata import inspect_directory
from localguard.scanner import scan_directory


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="localguard",
        description="Run offline security checks against files in a local project.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="find likely credentials in local text files")
    scan.add_argument("directory", nargs="?", type=Path, default=Path("."))
    scan.add_argument("--json", action="store_true", help="print machine-readable JSON")
    metadata = subparsers.add_parser(
        "metadata",
        help="inspect metadata in local files (offline)",
    )
    metadata.add_argument("directory", nargs="?", type=Path, default=Path("."))
    metadata.add_argument("--json", action="store_true", help="print machine-readable JSON")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if not args.directory.is_dir():
        print(f"error: not a directory: {args.directory}", file=sys.stderr)
        return 2

    if args.command == "metadata":
        result = inspect_directory(args.directory)
        if args.json:
            print(
                json.dumps(
                    {
                        "files_inspected": result.files_inspected,
                        "entries": [entry.to_dict() for entry in result.entries],
                        "errors": result.errors,
                    },
                    indent=2,
                )
            )
        else:
            print(f"Inspected {result.files_inspected} local file(s).")
            for entry in result.entries:
                print(f"{entry.path} ({entry.format}, {entry.size_bytes} bytes)")
                print(f"  modified_utc: {entry.modified_utc}")
                for key, value in entry.metadata.items():
                    print(f"  {key}: {value}")
            for error in result.errors:
                print(f"error: {error}", file=sys.stderr)
            if not result.entries:
                print("No supported embedded metadata found.")
        return 2 if result.errors else 0

    result = scan_directory(args.directory)
    if args.json:
        print(
            json.dumps(
                {
                    "files_scanned": result.files_scanned,
                    "findings": [finding.to_dict() for finding in result.findings],
                    "errors": result.errors,
                },
                indent=2,
            )
        )
    else:
        print(f"Scanned {result.files_scanned} text file(s).")
        for finding in result.findings:
            print(f"{finding.path}:{finding.line}: {finding.rule}: {finding.message}")
        for error in result.errors:
            print(f"error: {error}", file=sys.stderr)
        if not result.findings:
            print("No likely credentials found.")

    return 2 if result.errors else 1 if result.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
