"""Bounded, deterministic, non-executing structural repository scanner."""

from __future__ import annotations

import argparse
import codecs
import os
import stat
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from collections.abc import Iterable
from typing import Any

from metropogits import __version__
from scripts.canonical_json import canonical_json_bytes
from scripts.stable_ids import (
    make_edge_id,
    make_entity_id,
    normalize_relative_path,
    normalize_repository_id,
)
from scripts.validate_ucg import validate_document as validate_ucg_document


DEFAULT_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".gradle",
        ".hg",
        ".idea",
        ".svn",
        ".venv",
        ".vscode",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "out",
        "target",
        "vendor",
        "venv",
    }
)
SENSITIVE_FILENAMES = frozenset(
    {
        "credentials.json",
        "id_dsa",
        "id_ed25519",
        "id_rsa",
        "secrets.json",
        "secrets.yaml",
        "secrets.yml",
    }
)
SENSITIVE_SUFFIXES = frozenset({".jks", ".key", ".p12", ".pem", ".pfx"})
LANGUAGES_BY_EXTENSION = {
    ".c": "c",
    ".cc": "cpp",
    ".clj": "clojure",
    ".cljs": "clojure",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".dart": "dart",
    ".ex": "elixir",
    ".exs": "elixir",
    ".fs": "fsharp",
    ".fsx": "fsharp",
    ".go": "go",
    ".h": "c",
    ".hpp": "cpp",
    ".hrl": "erlang",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".lua": "lua",
    ".m": "objective-c",
    ".php": "php",
    ".py": "python",
    ".r": "r",
    ".rb": "ruby",
    ".rs": "rust",
    ".scala": "scala",
    ".sh": "shell",
    ".sol": "solidity",
    ".sql": "sql",
    ".svelte": "svelte",
    ".swift": "swift",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vb": "visual-basic",
    ".vue": "vue",
    ".zig": "zig",
}


class ScannerError(ValueError):
    """Raised when a repository cannot be scanned safely."""


@dataclass(frozen=True)
class ScanLimits:
    max_entries: int = 100_000
    max_files: int = 50_000
    max_file_bytes: int = 2 * 1024 * 1024
    max_total_bytes: int = 512 * 1024 * 1024
    max_depth: int = 64
    sniff_bytes: int = 8192

    def __post_init__(self) -> None:
        positive = {
            "max_entries": self.max_entries,
            "max_files": self.max_files,
            "max_file_bytes": self.max_file_bytes,
            "max_total_bytes": self.max_total_bytes,
            "sniff_bytes": self.sniff_bytes,
        }
        for name, value in positive.items():
            if value <= 0:
                raise ScannerError(f"{name} must be greater than zero")
        if self.max_depth < 0:
            raise ScannerError("max_depth must not be negative")


@dataclass(frozen=True)
class ScannedFile:
    path: str
    language: str
    size_bytes: int


@dataclass(frozen=True)
class ScanResult:
    files: tuple[ScannedFile, ...]
    diagnostics: tuple[dict[str, Any], ...]


def _is_sensitive_file(name: str) -> bool:
    lowered = name.lower()
    return (
        lowered == ".env"
        or lowered.startswith(".env.")
        or lowered in SENSITIVE_FILENAMES
        or Path(lowered).suffix in SENSITIVE_SUFFIXES
    )


def _is_reparse_point(file_stat: os.stat_result) -> bool:
    attributes = getattr(file_stat, "st_file_attributes", 0)
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(marker and attributes & marker)


def _read_prefix_safely(
    path: Path, expected: os.stat_result, byte_limit: int
) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ScannerError("entry is not a regular file")
        expected_identity = (expected.st_dev, expected.st_ino)
        if all(expected_identity) and (opened.st_dev, opened.st_ino) != expected_identity:
            raise ScannerError("entry changed while it was being opened")
        if (
            opened.st_size != expected.st_size
            or opened.st_mtime_ns != expected.st_mtime_ns
        ):
            raise ScannerError("entry changed while it was being opened")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = -1
            return stream.read(byte_limit)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _diagnostic(
    code: str, severity: str, message: str, source_path: str | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "code": code,
        "message": message,
        "severity": severity,
    }
    if source_path is not None:
        result["sourcePath"] = source_path
    return result


def scan_repository(
    root: str | Path,
    limits: ScanLimits | None = None,
    excluded_paths: Iterable[str | Path] = (),
) -> ScanResult:
    limits = limits or ScanLimits()
    root_path = Path(root)
    try:
        resolved_root = root_path.resolve(strict=True)
    except OSError as error:
        raise ScannerError(f"repository root is not accessible: {error}") from error
    if not resolved_root.is_dir():
        raise ScannerError("repository root must be a directory")

    excluded_absolute = {
        os.path.normcase(os.path.abspath(Path(path))) for path in excluded_paths
    }

    def is_explicitly_excluded(path: str | Path) -> bool:
        candidate = os.path.normcase(os.path.abspath(path))
        for excluded_path in excluded_absolute:
            try:
                if os.path.commonpath([candidate, excluded_path]) == excluded_path:
                    return True
            except ValueError:
                continue
        return False

    files: list[ScannedFile] = []
    diagnostics: list[dict[str, Any]] = []
    excluded: Counter[str] = Counter()
    entry_count = 0
    total_bytes = 0
    halted = False

    def visit(directory: Path, relative_directory: str, depth: int) -> None:
        nonlocal entry_count, halted, total_bytes
        if halted:
            return
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name)
        except OSError as error:
            diagnostics.append(
                _diagnostic(
                    "DIRECTORY_UNREADABLE",
                    "WARNING",
                    f"Directory could not be read: {error.__class__.__name__}",
                    relative_directory or None,
                )
            )
            return

        for entry in entries:
            if halted:
                break
            if is_explicitly_excluded(entry.path):
                continue
            entry_count += 1
            if entry_count > limits.max_entries:
                diagnostics.append(
                    _diagnostic(
                        "ENTRY_LIMIT_REACHED",
                        "WARNING",
                        f"Scan stopped after {limits.max_entries} entries",
                    )
                )
                halted = True
                break

            raw_relative = (
                f"{relative_directory}/{entry.name}"
                if relative_directory
                else entry.name
            )
            try:
                relative_path = normalize_relative_path(raw_relative)
                entry_stat = entry.stat(follow_symlinks=False)
            except (OSError, ValueError) as error:
                diagnostics.append(
                    _diagnostic(
                        "ENTRY_UNREADABLE",
                        "WARNING",
                        f"Entry metadata could not be read: {error.__class__.__name__}",
                        raw_relative.replace("\\", "/"),
                    )
                )
                continue

            if entry.is_symlink() or _is_reparse_point(entry_stat):
                diagnostics.append(
                    _diagnostic(
                        "SYMLINK_SKIPPED",
                        "WARNING",
                        "Symbolic link or reparse point was not followed",
                        relative_path,
                    )
                )
                continue

            if stat.S_ISDIR(entry_stat.st_mode):
                if entry.name.lower() in DEFAULT_EXCLUDED_DIRECTORIES:
                    excluded["ignored directories"] += 1
                    continue
                child_depth = depth + 1
                if child_depth > limits.max_depth:
                    diagnostics.append(
                        _diagnostic(
                            "DEPTH_LIMIT_REACHED",
                            "WARNING",
                            f"Directory exceeds maximum depth {limits.max_depth}",
                            relative_path,
                        )
                    )
                    continue
                visit(Path(entry.path), relative_path, child_depth)
                continue

            if not stat.S_ISREG(entry_stat.st_mode):
                excluded["non-regular entries"] += 1
                continue
            if _is_sensitive_file(entry.name):
                excluded["sensitive files"] += 1
                continue

            extension = Path(entry.name).suffix.lower()
            language = LANGUAGES_BY_EXTENSION.get(extension)
            if language is None:
                excluded["non-source files"] += 1
                continue
            if entry_stat.st_size > limits.max_file_bytes:
                diagnostics.append(
                    _diagnostic(
                        "FILE_SIZE_LIMIT",
                        "WARNING",
                        f"File exceeds maximum size {limits.max_file_bytes} bytes",
                        relative_path,
                    )
                )
                continue
            if len(files) >= limits.max_files:
                diagnostics.append(
                    _diagnostic(
                        "FILE_LIMIT_REACHED",
                        "WARNING",
                        f"Scan stopped after {limits.max_files} eligible files",
                    )
                )
                halted = True
                break
            if total_bytes + entry_stat.st_size > limits.max_total_bytes:
                diagnostics.append(
                    _diagnostic(
                        "TOTAL_SIZE_LIMIT_REACHED",
                        "WARNING",
                        f"Scan stopped before exceeding {limits.max_total_bytes} bytes",
                    )
                )
                halted = True
                break

            try:
                prefix = _read_prefix_safely(
                    Path(entry.path), entry_stat, limits.sniff_bytes
                )
                if entry_stat.st_size <= limits.sniff_bytes:
                    prefix.decode("utf-8")
                else:
                    decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
                    decoder.decode(prefix, final=False)
            except (OSError, UnicodeError, ScannerError) as error:
                code = (
                    "BINARY_FILE_SKIPPED"
                    if isinstance(error, UnicodeError)
                    else "FILE_UNREADABLE"
                )
                diagnostics.append(
                    _diagnostic(
                        code,
                        "WARNING",
                        "File was not accepted as safe UTF-8 source text",
                        relative_path,
                    )
                )
                continue
            if b"\x00" in prefix:
                diagnostics.append(
                    _diagnostic(
                        "BINARY_FILE_SKIPPED",
                        "WARNING",
                        "File contains binary data",
                        relative_path,
                    )
                )
                continue

            files.append(ScannedFile(relative_path, language, entry_stat.st_size))
            total_bytes += entry_stat.st_size

    visit(resolved_root, "", 0)

    for reason in sorted(excluded):
        count = excluded[reason]
        diagnostics.append(
            _diagnostic(
                "EXCLUSION_SUMMARY",
                "INFO",
                f"Excluded {count} {reason}",
            )
        )
    if not files:
        diagnostics.append(
            _diagnostic(
                "NO_ELIGIBLE_FILES",
                "WARNING",
                "No eligible UTF-8 source files were found",
            )
        )

    files.sort(key=lambda item: item.path)
    diagnostics.sort(
        key=lambda item: (
            item["code"],
            item.get("sourcePath", ""),
            item["message"],
        )
    )
    return ScanResult(tuple(files), tuple(diagnostics))


def build_structural_ucg(
    scan: ScanResult,
    repository_id: str,
    revision: str | None = None,
    source_url: str | None = None,
) -> dict[str, Any]:
    repository_id = normalize_repository_id(repository_id)
    directory_paths: set[str] = set()
    for file in scan.files:
        parent = PurePosixPath(file.path).parent
        while str(parent) != ".":
            directory_paths.add(str(parent))
            parent = parent.parent

    directory_ids = {
        path: make_entity_id(repository_id, "DIRECTORY", path)
        for path in directory_paths
    }
    entities: list[dict[str, Any]] = [
        {
            "id": directory_ids[path],
            "kind": "DIRECTORY",
            "path": path,
        }
        for path in directory_paths
    ]
    file_ids: dict[str, str] = {}
    for file in scan.files:
        entity_id = make_entity_id(repository_id, "FILE", file.path)
        file_ids[file.path] = entity_id
        entities.append(
            {
                "id": entity_id,
                "kind": "FILE",
                "language": file.language,
                "path": file.path,
                "roles": [],
            }
        )

    edges: list[dict[str, Any]] = []
    for path, entity_id in directory_ids.items():
        parent = str(PurePosixPath(path).parent)
        if parent in directory_ids:
            parent_id = directory_ids[parent]
            edges.append(
                {
                    "confidence": "DIRECT",
                    "evidenceIds": [],
                    "from": parent_id,
                    "id": make_edge_id(parent_id, "CONTAINS", entity_id),
                    "to": entity_id,
                    "type": "CONTAINS",
                }
            )
    for file in scan.files:
        parent = str(PurePosixPath(file.path).parent)
        if parent in directory_ids:
            parent_id = directory_ids[parent]
            entity_id = file_ids[file.path]
            edges.append(
                {
                    "confidence": "DIRECT",
                    "evidenceIds": [],
                    "from": parent_id,
                    "id": make_edge_id(parent_id, "CONTAINS", entity_id),
                    "to": entity_id,
                    "type": "CONTAINS",
                }
            )

    document: dict[str, Any] = {
        "diagnostics": list(scan.diagnostics),
        "edges": sorted(edges, key=lambda item: item["id"]),
        "entities": sorted(entities, key=lambda item: item["id"]),
        "evidence": [],
        "generator": {
            "catalogVersion": "0.1.0",
            "name": "metropogits",
            "version": __version__,
        },
        "repository": {
            "id": repository_id,
            "revision": revision,
            "sourceUrl": source_url,
        },
        "schemaVersion": "ucg/0.1",
    }
    errors = validate_ucg_document(document)
    if errors:
        raise ScannerError("generated invalid UCG: " + "; ".join(errors))
    return document


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--revision")
    parser.add_argument("--source-url")
    parser.add_argument("--max-entries", type=int, default=ScanLimits.max_entries)
    parser.add_argument("--max-files", type=int, default=ScanLimits.max_files)
    parser.add_argument("--max-file-bytes", type=int, default=ScanLimits.max_file_bytes)
    parser.add_argument("--max-total-bytes", type=int, default=ScanLimits.max_total_bytes)
    parser.add_argument("--max-depth", type=int, default=ScanLimits.max_depth)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        limits = ScanLimits(
            max_entries=args.max_entries,
            max_files=args.max_files,
            max_file_bytes=args.max_file_bytes,
            max_total_bytes=args.max_total_bytes,
            max_depth=args.max_depth,
        )
        scan = scan_repository(args.repo, limits)
        document = build_structural_ucg(
            scan, args.repo_id, args.revision, args.source_url
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(canonical_json_bytes(document))
    except (OSError, ScannerError, ValueError) as error:
        print(f"Repository scan failed: {error}", file=sys.stderr)
        return 2

    print(f"Wrote structural UCG for {len(scan.files)} files: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
