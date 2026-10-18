"""Bounded, deterministic, non-executing structural repository scanner."""

from __future__ import annotations

import argparse
import codecs
import hashlib
import os
import re
import stat
import sys
import xml.etree.ElementTree as ElementTree
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from collections.abc import Iterable
from typing import Any

from metropogits import __version__
from metropogits.catalog import CATALOG_VERSION
from metropogits.module_paths import ModulePaths, parse_module_paths
from metropogits.generated_outputs import (
    JVM_MANIFESTS, MAX_DECLARATION_BYTES, declares_local_bin_output,
)
from scripts.canonical_json import (
    CanonicalJsonError,
    canonical_json_bytes,
    loads_strict_json,
)
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
    ".mjs": "javascript",
    ".cjs": "javascript",
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
    ".mts": "typescript",
    ".cts": "typescript",
    ".vb": "visual-basic",
    ".vue": "vue",
    ".zig": "zig",
}
MAVEN_COORDINATE_PART = re.compile(r"^[A-Za-z0-9_.-]+$")
NPM_PACKAGE_NAME = re.compile(
    r"^(?:@[A-Za-z0-9][A-Za-z0-9._~-]*/)?[A-Za-z0-9][A-Za-z0-9._~-]*$"
)
NPM_DEPENDENCY_SECTIONS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
)
NPM_LOCAL_SPECIFIERS = ("file:", "link:", "npm:", "workspace:")
GRADLE_DEPENDENCY_BLOCK = re.compile(r"\bdependencies\s*\{")
GRADLE_DEPENDENCY_CALL = re.compile(
    r"""(?:^|[;{])\s*
    (?:api|implementation|compile|compileOnly|runtime|runtimeOnly|
       annotationProcessor|testCompile|testImplementation|testCompileOnly|
       testRuntimeOnly|kapt|ksp|classpath)\s*
    (?:\(\s*)?
    (?P<quote>["'])
    (?P<group>[A-Za-z0-9_.-]+):(?P<artifact>[A-Za-z0-9_.-]+)
    (?::[^"']+)?
    (?P=quote)\s*\)?
    (?=\s*(?:[;}]|$))""",
    re.VERBOSE,
)
SPRING_PROPERTIES_NAME = re.compile(
    r"^application(?:-[A-Za-z0-9_.-]+)?\.properties$"
)
SAFE_CONFIG_SIGNATURES = {
    "spring.datasource.driver-class-name": frozenset({"org.postgresql.Driver"}),
}


def _is_xml_ts(prefix: bytes) -> bool:
    """Disambiguate Qt's .ts documents without parsing XML or loading entities.

    Only the already bounded UTF-8 sniff buffer is examined. TypeScript strings,
    comments, type assertions and TSX files must not become XML by substring.
    """
    text = prefix.removeprefix(codecs.BOM_UTF8).lstrip()
    while text.startswith(b'<!--'):
        end = text.find(b'-->')
        if end < 0:
            return False
        text = text[end+3:].lstrip()
    return bool(
        re.match(rb'<\?xml\s[^?]*\?>', text)
        or re.match(rb'<!DOCTYPE\s+TS(?:\s|>)', text)
        or re.match(rb'<TS\s+version\s*=\s*[\"\'][0-9]+\.[0-9]+[\"\']', text)
    )


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
class DeclaredDependency:
    coordinate: str


@dataclass(frozen=True)
class ScannedManifest:
    path: str
    format: str
    ecosystem: str
    dependencies: tuple[DeclaredDependency, ...]


@dataclass(frozen=True)
class ConfigurationFact:
    key: str
    value: str
    line: int


@dataclass(frozen=True)
class ScannedConfiguration:
    path: str
    format: str
    facts: tuple[ConfigurationFact, ...]


@dataclass(frozen=True)
class ScanResult:
    files: tuple[ScannedFile, ...]
    diagnostics: tuple[dict[str, Any], ...]
    manifests: tuple[ScannedManifest, ...] = ()
    configurations: tuple[ScannedConfiguration, ...] = ()
    module_paths: tuple[ModulePaths, ...] = ()


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


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _direct_xml_children(
    element: ElementTree.Element, name: str
) -> list[ElementTree.Element]:
    return [child for child in element if _xml_local_name(child.tag) == name]


def _direct_xml_text(element: ElementTree.Element, name: str) -> str | None:
    matches = _direct_xml_children(element, name)
    if len(matches) != 1 or matches[0].text is None:
        return None
    value = matches[0].text.strip()
    return value or None


def _parse_maven_manifest(content: bytes) -> tuple[DeclaredDependency, ...]:
    if b"<!DOCTYPE" in content.upper():
        raise ScannerError("DOCTYPE declarations are not accepted in Maven manifests")
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise ScannerError("manifest is not well-formed XML") from error
    if _xml_local_name(root.tag) != "project":
        raise ScannerError("manifest root must be a Maven project")

    dependencies: set[str] = set()
    for container in _direct_xml_children(root, "dependencies"):
        for dependency in _direct_xml_children(container, "dependency"):
            group_id = _direct_xml_text(dependency, "groupId")
            artifact_id = _direct_xml_text(dependency, "artifactId")
            if not group_id or not artifact_id:
                continue
            if "${" in group_id or "${" in artifact_id:
                continue
            if not all(
                MAVEN_COORDINATE_PART.fullmatch(value)
                for value in (group_id, artifact_id)
            ):
                continue
            dependencies.add(f"{group_id}:{artifact_id}")
    return tuple(DeclaredDependency(item) for item in sorted(dependencies))


def _gradle_code_line(
    line: str, in_block_comment: bool, multiline_quote: str | None
) -> tuple[str, str, bool, str | None]:
    code: list[str] = []
    structure: list[str] = []
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(line):
        character = line[index]
        following = line[index + 1] if index + 1 < len(line) else ""
        triplet = line[index : index + 3]
        if multiline_quote is not None:
            if triplet == multiline_quote:
                code.extend((" ", " ", " "))
                structure.extend((" ", " ", " "))
                multiline_quote = None
                index += 3
            else:
                code.append(" ")
                structure.append(" ")
                index += 1
            continue
        if in_block_comment:
            if character == "*" and following == "/":
                code.extend((" ", " "))
                structure.extend((" ", " "))
                in_block_comment = False
                index += 2
            else:
                code.append(" ")
                structure.append(" ")
                index += 1
            continue
        if triplet in {"'''", '\"\"\"'}:
            code.extend((" ", " ", " "))
            structure.extend((" ", " ", " "))
            multiline_quote = triplet
            index += 3
            continue
        if quote is not None:
            code.append(character)
            structure.append(" ")
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            index += 1
            continue
        if character == "/" and following == "*":
            code.extend((" ", " "))
            structure.extend((" ", " "))
            in_block_comment = True
            index += 2
            continue
        if character == "/" and following == "/":
            padding = " " * (len(line) - index)
            code.append(padding)
            structure.append(padding)
            break
        code.append(character)
        if character in {"'", '"'}:
            quote = character
            structure.append(" ")
        else:
            structure.append(character)
        index += 1
    return (
        "".join(code),
        "".join(structure),
        in_block_comment,
        multiline_quote,
    )


def _parse_gradle_manifest(content: bytes) -> tuple[DeclaredDependency, ...]:
    try:
        source = content.decode("utf-8")
    except UnicodeError as error:
        raise ScannerError("manifest is not valid UTF-8") from error

    dependencies: set[str] = set()
    depth = 0
    dependency_depths: list[int] = []
    in_block_comment = False
    multiline_quote: str | None = None
    for line in source.splitlines():
        code, structure, in_block_comment, multiline_quote = _gradle_code_line(
            line, in_block_comment, multiline_quote
        )
        starts = list(GRADLE_DEPENDENCY_BLOCK.finditer(structure))
        started_depths: list[tuple[int, int]] = []
        for match in starts:
            prefix = structure[: match.end()]
            started_depths.append(
                (
                    match.start(),
                    depth + prefix.count("{") - prefix.count("}"),
                )
            )
        for match in GRADLE_DEPENDENCY_CALL.finditer(code):
            prefix = structure[: match.start()]
            current_depth = depth + prefix.count("{") - prefix.count("}")
            active_depths = dependency_depths + [
                dependency_depth
                for position, dependency_depth in started_depths
                if position < match.start()
            ]
            if any(current_depth >= item for item in active_depths):
                dependencies.add(
                    f"{match.group('group')}:{match.group('artifact')}"
                )
        dependency_depths.extend(item for _, item in started_depths)
        depth += structure.count("{") - structure.count("}")
        dependency_depths = [
            dependency_depth
            for dependency_depth in dependency_depths
            if depth >= dependency_depth
        ]
    return tuple(DeclaredDependency(item) for item in sorted(dependencies))


def _npm_dependencies_from_sections(
    document: dict[str, Any]
) -> tuple[DeclaredDependency, ...]:
    dependencies: set[str] = set()
    for section_name in NPM_DEPENDENCY_SECTIONS:
        if section_name not in document:
            continue
        section = document[section_name]
        if not isinstance(section, dict):
            raise ScannerError(f"npm {section_name} must be an object")
        for package_name, version in section.items():
            if not isinstance(version, str):
                raise ScannerError("npm dependency versions must be strings")
            if not NPM_PACKAGE_NAME.fullmatch(package_name):
                continue
            if version.strip().lower().startswith(NPM_LOCAL_SPECIFIERS):
                continue
            dependencies.add(package_name)
    return tuple(DeclaredDependency(item) for item in sorted(dependencies))


def _parse_npm_manifest(content: bytes) -> tuple[DeclaredDependency, ...]:
    try:
        document = loads_strict_json(content.decode("utf-8"))
    except (UnicodeError, CanonicalJsonError) as error:
        raise ScannerError("manifest is not valid strict JSON") from error
    if not isinstance(document, dict):
        raise ScannerError("npm manifest root must be an object")
    return _npm_dependencies_from_sections(document)


def _parse_npm_lockfile(content: bytes) -> tuple[DeclaredDependency, ...]:
    try:
        document = loads_strict_json(content.decode("utf-8"))
    except (UnicodeError, CanonicalJsonError) as error:
        raise ScannerError("lockfile is not valid strict JSON") from error
    if not isinstance(document, dict):
        raise ScannerError("npm lockfile root must be an object")
    packages = document.get("packages")
    if not isinstance(packages, dict):
        raise ScannerError("npm lockfile requires a packages object")
    root_package = packages.get("")
    if not isinstance(root_package, dict):
        raise ScannerError("npm lockfile requires a root package entry")
    return _npm_dependencies_from_sections(root_package)


def _parse_spring_properties(content: bytes) -> tuple[ConfigurationFact, ...]:
    try:
        source = content.decode("utf-8")
    except UnicodeError as error:
        raise ScannerError("configuration is not valid UTF-8") from error

    recognized: dict[str, ConfigurationFact] = {}
    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith(("#", "!")):
            continue
        match = re.fullmatch(
            r"(?P<key>[A-Za-z0-9._-]+)\s*(?:=|:)\s*(?P<value>[^\s#]+)\s*",
            line,
        )
        if match is None:
            continue
        key = match.group("key")
        value = match.group("value")
        allowed_values = SAFE_CONFIG_SIGNATURES.get(key)
        if allowed_values is None or value not in allowed_values:
            continue
        if key in recognized:
            raise ScannerError("configuration contains an ambiguous duplicate key")
        recognized[key] = ConfigurationFact(key, value, line_number)
    return tuple(sorted(recognized.values(), key=lambda item: (item.key, item.value)))


def _manifest_evidence(
    manifest: ScannedManifest, coordinate: str
) -> dict[str, Any]:
    rule_id = f"{manifest.format}.dependency"
    identity = [manifest.path, "MANIFEST", coordinate, rule_id]
    digest = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    return {
        "evidenceId": f"evidence:sha256:{digest}",
        "extractor": f"manifest.{manifest.format}/0.1",
        "kind": "MANIFEST",
        "ruleId": rule_id,
        "sourcePath": manifest.path,
        "summary": (
            f"Declared {'npm' if manifest.format == 'npm' else manifest.format.title()} "
            f"dependency {coordinate}"
        ),
    }


def configuration_evidence(
    configuration: ScannedConfiguration, fact: ConfigurationFact
) -> dict[str, Any]:
    rule_id = f"config.{configuration.format}.{fact.key}"
    identity = [
        configuration.path,
        "CONFIG",
        fact.key,
        fact.value,
        fact.line,
        rule_id,
    ]
    digest = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    return {
        "endLine": fact.line,
        "evidenceId": f"evidence:sha256:{digest}",
        "extractor": f"config.{configuration.format}/0.1",
        "kind": "CONFIG",
        "ruleId": rule_id,
        "sourcePath": configuration.path,
        "startLine": fact.line,
        "summary": f"Recognized non-secret configuration key {fact.key}",
    }


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
    manifests: list[ScannedManifest] = []
    configurations: list[ScannedConfiguration] = []
    module_paths: list[ModulePaths] = []
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

        local_bin_output = False
        # Bounded metadata checks only; never execute or follow a build file.
        jvm_module = False
        if any(entry.name == "bin" for entry in entries):
            for candidate in entries:
                if candidate.name not in JVM_MANIFESTS or is_explicitly_excluded(candidate.path):
                    continue
                try:
                    candidate_stat = candidate.stat(follow_symlinks=False)
                    if stat.S_ISREG(candidate_stat.st_mode) and not candidate.is_symlink() and not _is_reparse_point(candidate_stat):
                        jvm_module = True
                        break
                except OSError:
                    pass

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

            is_module_config = entry.name in {"tsconfig.json", "jsconfig.json"}
            if is_module_config:
                # Even an unreadable/linked/oversized config blocks outer aliases.
                module_paths.append(ModulePaths(relative_path, supported=False))
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
                if entry.name == "bin" and local_bin_output:
                    diagnostics.append(_diagnostic(
                        "GENERATED_OUTPUT_EXCLUDED", "INFO",
                        "Module-local bin output excluded by .gitignore beside a JVM manifest",
                        relative_path,
                    ))
                    continue
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

            if entry.name == ".gitignore" and jvm_module:
                if entry_stat.st_size > min(limits.max_file_bytes, MAX_DECLARATION_BYTES):
                    diagnostics.append(_diagnostic("OUTPUT_DECLARATION_UNREADABLE", "WARNING",
                                                   "Output declaration exceeds size limit; bin preserved", relative_path))
                    continue
                if total_bytes + entry_stat.st_size > limits.max_total_bytes:
                    diagnostics.append(_diagnostic("TOTAL_SIZE_LIMIT_REACHED", "WARNING",
                                                   "Scan stopped before exceeding total byte limit", relative_path))
                    halted = True
                    break
                try:
                    content = _read_prefix_safely(Path(entry.path), entry_stat, MAX_DECLARATION_BYTES + 1)
                    total_bytes += len(content)
                    local_bin_output = declares_local_bin_output(content)
                except (OSError, UnicodeError, ScannerError, ValueError):
                    diagnostics.append(_diagnostic("OUTPUT_DECLARATION_UNREADABLE", "WARNING",
                                                   "Output declaration could not be read safely; bin preserved", relative_path))
                continue

            manifest_format = {
                "build.gradle": "gradle",
                "build.gradle.kts": "gradle",
                "package.json": "npm",
                "package-lock.json": "npm-lock",
                "pom.xml": "maven",
            }.get(entry.name)
            if manifest_format is not None:
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
                    content = _read_prefix_safely(
                        Path(entry.path), entry_stat, limits.max_file_bytes + 1
                    )
                    dependencies = (
                        _parse_maven_manifest(content)
                        if manifest_format == "maven"
                        else (
                            _parse_gradle_manifest(content)
                            if manifest_format == "gradle"
                            else (
                                _parse_npm_manifest(content)
                                if manifest_format == "npm"
                                else _parse_npm_lockfile(content)
                            )
                        )
                    )
                except (OSError, UnicodeError, ScannerError):
                    diagnostics.append(
                        _diagnostic(
                            "MANIFEST_PARSE_FAILED",
                            "WARNING",
                            f"{manifest_format.title()} manifest could not be parsed safely",
                            relative_path,
                        )
                    )
                    continue
                manifests.append(
                    ScannedManifest(
                        relative_path,
                        manifest_format,
                        "npm" if manifest_format.startswith("npm") else "maven",
                        dependencies,
                    )
                )
                total_bytes += entry_stat.st_size
                continue

            if is_module_config or SPRING_PROPERTIES_NAME.fullmatch(entry.name):
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
                    content = _read_prefix_safely(
                        Path(entry.path), entry_stat, limits.max_file_bytes + 1
                    )
                    if is_module_config:
                        total_bytes += entry_stat.st_size
                        module_paths[-1] = parse_module_paths(relative_path, content)
                        continue
                    facts = _parse_spring_properties(content)
                except (OSError, UnicodeError, ScannerError, ValueError, RecursionError):
                    diagnostics.append(
                        _diagnostic(
                            "CONFIG_PARSE_FAILED",
                            "WARNING",
                            "Module paths config unsupported or invalid (strict JSON, no extends)"
                            if is_module_config else "Spring properties could not be parsed safely",
                            relative_path,
                        )
                    )
                    continue
                configurations.append(
                    ScannedConfiguration(relative_path, "spring-properties", facts)
                )
                total_bytes += entry_stat.st_size
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

            if extension == '.ts' and _is_xml_ts(prefix):
                language = 'xml'
                diagnostics.append(_diagnostic(
                    'SOURCE_FORMAT_DISAMBIGUATED', 'INFO',
                    'XML .ts document retained structurally; not TypeScript source', relative_path,
                ))
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
    manifests.sort(key=lambda item: item.path)
    configurations.sort(key=lambda item: item.path)
    diagnostics.sort(
        key=lambda item: (
            item["code"],
            item.get("sourcePath", ""),
            item["message"],
        )
    )
    return ScanResult(
        tuple(files),
        tuple(diagnostics),
        tuple(manifests),
        tuple(configurations),
        tuple(sorted(module_paths, key=lambda item: item.path)),
    )


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

    module_ids: dict[str, str] = {}
    external_package_ids: dict[tuple[str, str], str] = {}
    evidence: list[dict[str, Any]] = []
    for manifest in scan.manifests:
        if manifest.ecosystem not in {"maven", "npm"}:
            continue
        module_id = make_entity_id(repository_id, "MODULE", manifest.path)
        module_ids[manifest.path] = module_id
        entities.append(
            {
                "id": module_id,
                "kind": "MODULE",
                "path": manifest.path,
            }
        )
        for dependency in manifest.dependencies:
            if manifest.ecosystem == "maven":
                group_id, artifact_id = dependency.coordinate.split(":", 1)
                package_path = (
                    "maven/" + group_id.replace(".", "/") + "/" + artifact_id
                )
            else:
                package_path = f"npm/{dependency.coordinate}"
            package_key = (manifest.ecosystem, dependency.coordinate)
            package_id = make_entity_id(
                repository_id, "EXTERNAL_PACKAGE", package_path
            )
            if package_key not in external_package_ids:
                external_package_ids[package_key] = package_id
                entities.append(
                    {
                        "id": package_id,
                        "kind": "EXTERNAL_PACKAGE",
                        "path": package_path,
                    }
                )
            manifest_evidence = _manifest_evidence(manifest, dependency.coordinate)
            evidence.append(manifest_evidence)
    for configuration in scan.configurations:
        evidence.extend(
            configuration_evidence(configuration, fact)
            for fact in configuration.facts
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
    for manifest in scan.manifests:
        module_id = module_ids.get(manifest.path)
        if module_id is None:
            continue
        parent = str(PurePosixPath(manifest.path).parent)
        if parent in directory_ids:
            parent_id = directory_ids[parent]
            edges.append(
                {
                    "confidence": "DIRECT",
                    "evidenceIds": [],
                    "from": parent_id,
                    "id": make_edge_id(parent_id, "CONTAINS", module_id),
                    "to": module_id,
                    "type": "CONTAINS",
                }
            )
        for dependency in manifest.dependencies:
            package_id = external_package_ids[
                (manifest.ecosystem, dependency.coordinate)
            ]
            manifest_evidence = _manifest_evidence(manifest, dependency.coordinate)
            edges.append(
                {
                    "confidence": "DIRECT",
                    "evidenceIds": [manifest_evidence["evidenceId"]],
                    "from": module_id,
                    "id": make_edge_id(
                        module_id,
                        "DEPENDS_ON",
                        package_id,
                        dependency.coordinate,
                    ),
                    "to": package_id,
                    "type": "DEPENDS_ON",
                }
            )

    document: dict[str, Any] = {
        "diagnostics": list(scan.diagnostics),
        "edges": sorted(edges, key=lambda item: item["id"]),
        "entities": sorted(entities, key=lambda item: item["id"]),
        "evidence": sorted(evidence, key=lambda item: item["evidenceId"]),
        "generator": {
            "catalogVersion": CATALOG_VERSION,
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
