"""Bounded, non-executing JavaScript and TypeScript module analysis."""

from __future__ import annotations

import copy
import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from metropogits.module_paths import alias_targets, config_for_file, safe_relative
from typing import Any

from metropogits.scanner import ScanLimits, ScanResult, ScannedFile
from scripts.canonical_json import canonical_json_bytes
from scripts.stable_ids import make_edge_id, make_entity_id
from scripts.validate_ucg import validate_document as validate_ucg_document


EXTRACTOR = "jsts-static/0.1"
LANGUAGES = frozenset({"javascript", "typescript"})
MODULE_EXTENSIONS = (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs")
REGEX_PREFIX_KEYWORDS = frozenset(
    {
        "await",
        "case",
        "delete",
        "do",
        "else",
        "in",
        "instanceof",
        "new",
        "of",
        "return",
        "throw",
        "typeof",
        "void",
        "yield",
    }
)
REGEX_PREFIX_PUNCTUATION = frozenset("([{=,:;!&|?+-*%^~<>")


class JsTsAnalysisError(ValueError):
    """Raised when JS/TS analysis cannot safely produce a valid graph."""


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int


@dataclass(frozen=True)
class ModuleReference:
    line: int
    specifier: str
    syntax: str


def _read_source(root: Path, scanned: ScannedFile, limit: int) -> str:
    resolved_root = root.resolve(strict=True)
    candidate = resolved_root.joinpath(*PurePosixPath(scanned.path).parts)
    resolved_candidate = candidate.resolve(strict=True)
    if resolved_root not in resolved_candidate.parents:
        raise JsTsAnalysisError("source path escapes repository root")
    metadata = candidate.stat(follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or candidate.is_symlink():
        raise JsTsAnalysisError("source is no longer a regular file")
    if metadata.st_size > limit:
        raise JsTsAnalysisError("source exceeds analyzer size limit")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(candidate, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > limit:
            raise JsTsAnalysisError("opened source violates analyzer limits")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = -1
            content = stream.read(limit + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(content) > limit:
        raise JsTsAnalysisError("source exceeds analyzer size limit")
    try:
        return content.decode("utf-8")
    except UnicodeError as error:
        raise JsTsAnalysisError("source is not valid UTF-8") from error


def _regex_can_start(previous: Token | None) -> bool:
    if previous is None:
        return True
    if previous.kind == "PUNCT":
        return previous.value in REGEX_PREFIX_PUNCTUATION
    return previous.kind == "IDENT" and previous.value in REGEX_PREFIX_KEYWORDS


def _tokenize(source: str) -> tuple[Token, ...]:
    tokens: list[Token] = []
    index = 0
    line = 1
    previous: Token | None = None

    def remember(token: Token) -> None:
        nonlocal previous
        tokens.append(token)
        previous = token

    while index < len(source):
        character = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""

        if character in " \t\f\v":
            index += 1
            continue
        if character in "\r\n":
            if character == "\r" and following == "\n":
                index += 1
            line += 1
            index += 1
            continue
        if character == "/" and following == "/":
            index += 2
            while index < len(source) and source[index] not in "\r\n":
                index += 1
            continue
        if character == "/" and following == "*":
            start_line = line
            index += 2
            while index + 1 < len(source) and source[index : index + 2] != "*/":
                if source[index] == "\n":
                    line += 1
                index += 1
            if index + 1 >= len(source):
                raise JsTsAnalysisError(
                    f"unterminated block comment starting at line {start_line}"
                )
            index += 2
            continue
        if character in {"'", '"'}:
            quote = character
            start_line = line
            index += 1
            value: list[str] = []
            escaped = False
            while index < len(source):
                character = source[index]
                if character == quote:
                    index += 1
                    remember(
                        Token(
                            "ESCAPED_STRING" if escaped else "STRING",
                            "".join(value),
                            start_line,
                        )
                    )
                    break
                if character in "\r\n":
                    raise JsTsAnalysisError(
                        f"unterminated string literal starting at line {start_line}"
                    )
                if character == "\\":
                    escaped = True
                    index += 2
                    continue
                value.append(character)
                index += 1
            else:
                raise JsTsAnalysisError(
                    f"unterminated string literal starting at line {start_line}"
                )
            continue
        if character == "`":
            start_line = line
            index += 1
            while index < len(source):
                character = source[index]
                if character == "\\":
                    index += 2
                    continue
                if character == "`":
                    index += 1
                    break
                if character == "\n":
                    line += 1
                index += 1
            else:
                raise JsTsAnalysisError(
                    f"unterminated template literal starting at line {start_line}"
                )
            continue
        jsx_closing_tag = (
            previous is not None
            and previous.kind == "PUNCT"
            and previous.value == "<"
            and index > 0
            and source[index - 1] == "<"
            and (following.isalpha() or following in {"_", "$", ">"})
        )
        jsx_text_slash = (
            previous is not None
            and previous.kind == "PUNCT"
            and previous.value == ">"
            and following == "{"
        )
        if (
            character == "/"
            and _regex_can_start(previous)
            and not jsx_closing_tag
            and not jsx_text_slash
        ):
            start_line = line
            index += 1
            in_character_class = False
            while index < len(source):
                character = source[index]
                if character == "\\":
                    index += 2
                    continue
                if character in "\r\n":
                    raise JsTsAnalysisError(
                        f"unterminated regular expression starting at line {start_line}"
                    )
                if character == "[":
                    in_character_class = True
                elif character == "]":
                    in_character_class = False
                elif character == "/" and not in_character_class:
                    index += 1
                    while index < len(source) and source[index].isalpha():
                        index += 1
                    remember(Token("REGEX", "", start_line))
                    break
                index += 1
            else:
                raise JsTsAnalysisError(
                    f"unterminated regular expression starting at line {start_line}"
                )
            continue
        if character.isalpha() or character in {"_", "$"}:
            start = index
            index += 1
            while index < len(source) and (
                source[index].isalnum() or source[index] in {"_", "$"}
            ):
                index += 1
            remember(Token("IDENT", source[start:index], line))
            continue
        if character in "(){}[];,.=:+-*?!&|<>/%":
            remember(Token("PUNCT", character, line))
            index += 1
            continue
        remember(Token("OTHER", character, line))
        index += 1

    return tuple(tokens)


def _from_reference(
    tokens: tuple[Token, ...], start: int, syntax: str
) -> ModuleReference | None:
    for index in range(start, min(len(tokens), start + 200)):
        token = tokens[index]
        if token.kind == "PUNCT" and token.value == ";":
            return None
        if token.kind == "IDENT" and token.value == "from":
            if index + 1 < len(tokens) and tokens[index + 1].kind == "STRING":
                specifier = tokens[index + 1]
                return ModuleReference(specifier.line, specifier.value, syntax)
            return None
    return None


def _module_references(tokens: tuple[Token, ...]) -> tuple[ModuleReference, ...]:
    references: set[ModuleReference] = set()
    for index, token in enumerate(tokens):
        if token.kind != "IDENT":
            continue
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        if token.value == "import":
            if following and following.kind == "PUNCT" and following.value == ".":
                continue
            if (
                following
                and following.kind == "PUNCT"
                and following.value == "("
                and index + 3 < len(tokens)
                and tokens[index + 2].kind == "STRING"
                and tokens[index + 3].kind == "PUNCT"
                and tokens[index + 3].value == ")"
            ):
                specifier = tokens[index + 2]
                references.add(
                    ModuleReference(specifier.line, specifier.value, "dynamic-import")
                )
            elif following and following.kind == "STRING":
                references.add(
                    ModuleReference(following.line, following.value, "esm-import")
                )
            else:
                reference = _from_reference(tokens, index + 1, "esm-import")
                if reference:
                    references.add(reference)
        elif token.value == "export":
            cursor = index + 1
            if (
                cursor < len(tokens)
                and tokens[cursor].kind == "IDENT"
                and tokens[cursor].value == "type"
            ):
                cursor += 1
            if cursor < len(tokens) and tokens[cursor].value in {"*", "{"}:
                reference = _from_reference(tokens, cursor + 1, "esm-export")
                if reference:
                    references.add(reference)
        elif (
            token.value == "require"
            and (index == 0 or tokens[index - 1].value != ".")
            and following
            and following.kind == "PUNCT"
            and following.value == "("
            and index + 3 < len(tokens)
            and tokens[index + 2].kind == "STRING"
            and tokens[index + 3].kind == "PUNCT"
            and tokens[index + 3].value == ")"
        ):
            specifier = tokens[index + 2]
            references.add(
                ModuleReference(specifier.line, specifier.value, "commonjs-require")
            )
    return tuple(
        sorted(references, key=lambda item: (item.line, item.specifier, item.syntax))
    )


def _normalized_local_base(importer: str, specifier: str) -> str | None:
    if not specifier.startswith(("./", "../")):
        return None
    parts = list(PurePosixPath(importer).parent.parts)
    for part in specifier.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    return "/".join(parts) if parts else None


def _local_candidates(
    importer: str, specifier: str, files_by_path: dict[str, str]
) -> list[str]:
    base = _normalized_local_base(importer, specifier)
    if base is None or "?" in base or "#" in base:
        return []
    suffix = PurePosixPath(base).suffix.lower()
    candidates = [base] if suffix in MODULE_EXTENSIONS else []
    if not candidates:
        candidates.extend(base + extension for extension in MODULE_EXTENSIONS)
        candidates.extend(f"{base}/index{extension}" for extension in MODULE_EXTENSIONS)
    return sorted(
        path
        for path in dict.fromkeys(candidates)
        if path in files_by_path and path != importer
    )


def _external_package_path(specifier: str) -> str | None:
    if (
        not specifier
        or specifier.startswith((".", "/", "#", "@/"))
        or "://" in specifier
        or "\\" in specifier
    ):
        return None
    parts = specifier.split("/")
    package = "/".join(parts[:2]) if specifier.startswith("@") else parts[0]
    return f"npm/{package}" if package and package != "@" else None


def _evidence(path: str, reference: ModuleReference) -> dict[str, Any]:
    summary = f"Explicit {reference.syntax} module reference"
    identity = [path, reference.line, "IMPORT", summary, reference.specifier]
    digest = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    return {
        "endLine": reference.line,
        "evidenceId": f"evidence:sha256:{digest}",
        "extractor": EXTRACTOR,
        "kind": "IMPORT",
        "ruleId": f"jsts.{reference.syntax}",
        "sourcePath": path,
        "startLine": reference.line,
        "summary": summary,
    }


def _diagnostic(
    code: str, severity: str, message: str, source_path: str | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "code": code,
        "message": message,
        "severity": severity,
    }
    if source_path:
        result["sourcePath"] = source_path
    return result


def enrich_jsts_graph(
    root: Path,
    scan: ScanResult,
    graph: dict[str, Any],
    limits: ScanLimits,
) -> dict[str, Any]:
    """Add conservative JS/TS module relationships without running source code."""

    document = copy.deepcopy(graph)
    entities_by_path = {
        entity["path"]: entity
        for entity in document["entities"]
        if entity["kind"] == "FILE"
    }
    files_by_path = {
        item.path: entities_by_path[item.path]["id"]
        for item in scan.files
        if item.language in LANGUAGES
    }
    references_by_path: dict[str, tuple[ModuleReference, ...]] = {}
    for scanned in scan.files:
        if scanned.language not in LANGUAGES:
            continue
        try:
            source = _read_source(root, scanned, limits.max_file_bytes)
            references_by_path[scanned.path] = _module_references(_tokenize(source))
        except (OSError, JsTsAnalysisError) as error:
            document["diagnostics"].append(
                _diagnostic(
                    "JSTS_ANALYSIS_SKIPPED",
                    "WARNING",
                    f"JavaScript/TypeScript analysis skipped: {error}",
                    scanned.path,
                )
            )

    document["diagnostics"].append(
        _diagnostic(
            "JSTS_ANALYZER_COVERAGE",
            "INFO",
            (
                f"JavaScript/TypeScript static module analysis processed "
                f"{len(references_by_path)} file(s); capabilities=staticImports,configuredPaths"
            ),
        )
    )

    evidence_by_id = {item["evidenceId"]: item for item in document["evidence"]}
    existing_entity_ids = {item["id"] for item in document["entities"]}
    new_entities: dict[str, dict[str, Any]] = {}
    new_edges: dict[str, dict[str, Any]] = {}
    repository_id = document["repository"]["id"]

    def remember_edge(edge: dict[str, Any]) -> None:
        existing = new_edges.get(edge["id"])
        if existing is None:
            new_edges[edge["id"]] = edge
            return
        existing["evidenceIds"] = sorted(
            set(existing["evidenceIds"]) | set(edge["evidenceIds"])
        )

    for path, references in sorted(references_by_path.items()):
        source_id = files_by_path[path]
        config = config_for_file(path, scan.module_paths)
        for reference in references:
            target_id: str | None = None
            confidence = "DIRECT"
            config_evidence = None
            relative = reference.specifier.startswith(("./", "../"))
            alias = alias_targets(config, reference.specifier) if (
                config and config.supported and not relative and safe_relative(reference.specifier)
            ) else None
            blocked = config is not None and not config.supported and not relative
            if relative or alias or blocked:
                candidates = []
                if relative:
                    candidates = _local_candidates(path, reference.specifier, files_by_path)
                elif alias:
                    pattern, targets = alias
                    for target in targets:
                        if not safe_relative(target):
                            continue
                        candidates = _local_candidates(config.path, f"./{config.base}/{target}", files_by_path)
                        if candidates:
                            break
                    identity = [config.path, config.base, pattern, list(dict(config.mappings)[pattern])]
                    digest = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
                    config_evidence = dict(evidenceId=f"evidence:sha256:{digest}", kind="CONFIG",
                                           extractor="jsts-paths/0.1", sourcePath=config.path,
                                           ruleId="jsts.configured-path", summary=f"Explicit compilerOptions.paths mapping: {pattern}")
                if len(candidates) == 1:
                    target_id = files_by_path[candidates[0]]
                    confidence = "RESOLVED"
                elif len(candidates) > 1:
                    document["diagnostics"].append(
                        _diagnostic(
                            "JSTS_IMPORT_AMBIGUOUS",
                            "WARNING",
                            "Local module reference matches multiple scanned files",
                            path,
                        )
                    )
                else:
                    document["diagnostics"].append(
                        _diagnostic(
                            "JSTS_IMPORT_UNRESOLVED",
                            "INFO",
                            "Local module reference could not be resolved from supported configuration and scanned files",
                            path,
                        )
                    )
            else:
                external_path = _external_package_path(reference.specifier)
                if external_path:
                    target_id = make_entity_id(
                        repository_id, "EXTERNAL_PACKAGE", external_path
                    )
                    if target_id not in existing_entity_ids:
                        new_entities[target_id] = {
                            "id": target_id,
                            "kind": "EXTERNAL_PACKAGE",
                            "path": external_path,
                        }
                else:
                    document["diagnostics"].append(
                        _diagnostic(
                            "JSTS_IMPORT_UNRESOLVED",
                            "INFO",
                            "Module reference uses an unsupported resolution form",
                            path,
                        )
                    )
            if target_id is None:
                continue
            evidence = _evidence(path, reference)
            evidence_by_id[evidence["evidenceId"]] = evidence
            edge_evidence_ids = [evidence["evidenceId"]]
            if config_evidence:
                evidence_by_id[config_evidence["evidenceId"]] = config_evidence
                edge_evidence_ids.append(config_evidence["evidenceId"])
            edge_id = make_edge_id(
                source_id,
                "IMPORTS",
                target_id,
                f"{reference.syntax}:{reference.specifier}",
            )
            remember_edge(
                {
                    "confidence": confidence,
                    "evidenceIds": sorted(edge_evidence_ids),
                    "from": source_id,
                    "id": edge_id,
                    "to": target_id,
                    "type": "IMPORTS",
                }
            )

    document["entities"].extend(new_entities.values())
    document["edges"].extend(new_edges.values())
    document["entities"].sort(key=lambda item: item["id"])
    document["edges"].sort(key=lambda item: item["id"])
    document["evidence"] = sorted(
        evidence_by_id.values(), key=lambda item: item["evidenceId"]
    )
    document["diagnostics"].sort(
        key=lambda item: (
            item["code"],
            item.get("sourcePath", ""),
            item["message"],
        )
    )

    errors = validate_ucg_document(document)
    if errors:
        raise JsTsAnalysisError("generated invalid UCG: " + "; ".join(errors))
    return document
