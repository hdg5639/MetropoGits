"""Bounded lexical Java analysis with evidence-backed Spring rules."""

from __future__ import annotations

import copy
import hashlib
import os
import re
import stat
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from metropogits.catalog import (
    CatalogFact,
    manifest_catalog_facts,
    resolve_catalog_claims,
)
from metropogits.scanner import (
    ScanLimits,
    ScanResult,
    ScannedFile,
    configuration_evidence,
)
from scripts.canonical_json import canonical_json_bytes
from scripts.stable_ids import make_edge_id, make_entity_id
from scripts.validate_ucg import validate_document as validate_ucg_document


EXTRACTOR = "java-static/0.1"
IDENTIFIER = r"[A-Za-z_$][A-Za-z0-9_$]*"
QUALIFIED_NAME = rf"{IDENTIFIER}(?:\.{IDENTIFIER})*"
PACKAGE_PATTERN = re.compile(rf"(?m)^\s*package\s+({QUALIFIED_NAME})\s*;")
IMPORT_PATTERN = re.compile(
    rf"(?m)^\s*import\s+(?P<static>static\s+)?"
    rf"(?P<name>{QUALIFIED_NAME}(?:\.\*)?)\s*;"
)
TYPE_PATTERN = re.compile(
    rf"(?m)"
    rf"^[ \t]*(?P<annotations>(?:@{QUALIFIED_NAME}"
    rf"(?:[ \t]*\([^()\r\n]*\))?[ \t]*(?:\r?\n[ \t]*|[ \t]+))*)"
    rf"(?:(?:public|protected|private|abstract|final|static|sealed|"
    rf"non-sealed|strictfp)\s+)*"
    rf"(?P<kind>@interface|class|interface|enum|record)\s+"
    rf"(?P<name>{IDENTIFIER})(?P<tail>[^{{}};]*)\{{"
)
ANNOTATION_PATTERN = re.compile(rf"@(?P<name>{QUALIFIED_NAME})")
RELATION_PATTERN = {
    "EXTENDS": re.compile(
        r"\bextends\s+(?P<types>.*?)(?=\bimplements\b|\bpermits\b|$)",
        re.DOTALL,
    ),
    "IMPLEMENTS": re.compile(
        r"\bimplements\s+(?P<types>.*?)(?=\bpermits\b|$)", re.DOTALL
    ),
}

SPRING_RULES = {
    "org.springframework.context.annotation.Configuration": (
        3,
        "CONFIGURATION",
        "SPRING_FRAMEWORK",
        None,
        "spring.configuration",
    ),
    "org.springframework.stereotype.Component": (
        4,
        "GENERAL_COMPONENT",
        "SPRING_FRAMEWORK",
        None,
        "spring.component",
    ),
    "org.springframework.stereotype.Controller": (
        0,
        "ENTRYPOINT",
        "SPRING_MVC",
        None,
        "spring.controller",
    ),
    "org.springframework.stereotype.Repository": (
        2,
        "PERSISTENCE_ADAPTER",
        "SPRING_FRAMEWORK",
        None,
        "spring.repository",
    ),
    "org.springframework.stereotype.Service": (
        1,
        "SERVICE",
        "SPRING_FRAMEWORK",
        None,
        "spring.service",
    ),
    "org.springframework.web.bind.annotation.RestController": (
        0,
        "ENTRYPOINT",
        "SPRING_MVC",
        "API",
        "spring.controller.rest",
    ),
}
SPRING_WILDCARD_PACKAGES = {qualified.rsplit(".", 1)[0] for qualified in SPRING_RULES}
JPA_REPOSITORY = "org.springframework.data.jpa.repository.JpaRepository"


class JavaAnalysisError(ValueError):
    """Raised when Java analysis cannot produce a valid graph."""


@dataclass(frozen=True)
class JavaImport:
    name: str
    line: int
    is_static: bool


@dataclass(frozen=True)
class JavaType:
    kind: str
    name: str
    qualified_name: str
    line: int
    end_line: int
    annotations: tuple[tuple[str, int], ...]
    relations: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class JavaUnit:
    path: str
    file_id: str
    package: str
    imports: tuple[JavaImport, ...]
    types: tuple[JavaType, ...]


def _mask_non_code(source: str) -> str:
    """Mask comments and literals while preserving offsets and line breaks."""

    result = list(source)
    index = 0
    state = "code"
    while index < len(source):
        character = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        triple = source[index : index + 3]

        if state == "code":
            if character == "/" and following == "/":
                result[index] = result[index + 1] = " "
                index += 2
                state = "line_comment"
                continue
            if character == "/" and following == "*":
                result[index] = result[index + 1] = " "
                index += 2
                state = "block_comment"
                continue
            if triple == '"""':
                result[index : index + 3] = [" ", " ", " "]
                index += 3
                state = "text_block"
                continue
            if character == '"':
                result[index] = " "
                index += 1
                state = "string"
                continue
            if character == "'":
                result[index] = " "
                index += 1
                state = "character"
                continue
            index += 1
            continue

        if state == "line_comment":
            if character in "\r\n":
                state = "code"
            else:
                result[index] = " "
            index += 1
            continue

        if state == "block_comment":
            if character == "*" and following == "/":
                result[index] = result[index + 1] = " "
                index += 2
                state = "code"
            else:
                if character not in "\r\n":
                    result[index] = " "
                index += 1
            continue

        if state == "text_block":
            if triple == '"""':
                result[index : index + 3] = [" ", " ", " "]
                index += 3
                state = "code"
            else:
                if character not in "\r\n":
                    result[index] = " "
                index += 1
            continue

        if character == "\\" and following:
            result[index] = " "
            if following not in "\r\n":
                result[index + 1] = " "
            index += 2
            continue
        if (state == "string" and character == '"') or (
            state == "character" and character == "'"
        ):
            result[index] = " "
            index += 1
            state = "code"
            continue
        if character not in "\r\n":
            result[index] = " "
        index += 1

    return "".join(result)


def _top_level_offsets(source: str, offsets: list[int]) -> set[int]:
    requested = sorted(set(offsets))
    result: set[int] = set()
    depth = 0
    cursor = 0
    for offset in requested:
        while cursor < offset:
            if source[cursor] == "{":
                depth += 1
            elif source[cursor] == "}":
                depth = max(0, depth - 1)
            cursor += 1
        if depth == 0:
            result.add(offset)
    return result


def _split_types(value: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(value):
        if character == "<":
            depth += 1
        elif character == ">":
            depth = max(0, depth - 1)
        elif character == "," and depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])

    names: list[str] = []
    for part in parts:
        match = re.search(QUALIFIED_NAME, part.strip())
        if match:
            names.append(match.group(0))
    return names


def _parse_unit(path: str, file_id: str, source: str) -> JavaUnit:
    masked = _mask_non_code(source)
    line_starts = [0] + [
        index + 1 for index, character in enumerate(masked) if character == "\n"
    ]

    def line_number(offset: int) -> int:
        return bisect_right(line_starts, offset)

    package_match = PACKAGE_PATTERN.search(masked)
    package = package_match.group(1) if package_match else ""
    imports = tuple(
        JavaImport(
            name=match.group("name"),
            line=line_number(match.start()),
            is_static=bool(match.group("static")),
        )
        for match in IMPORT_PATTERN.finditer(masked)
    )

    matches = list(TYPE_PATTERN.finditer(masked))
    top_level = _top_level_offsets(masked, [match.start("kind") for match in matches])
    types: list[JavaType] = []
    for match in matches:
        if match.start("kind") not in top_level:
            continue
        name = match.group("name")
        qualified_name = f"{package}.{name}" if package else name
        annotation_start = match.start("annotations")
        annotations = tuple(
            (
                annotation.group("name"),
                line_number(annotation_start + annotation.start()),
            )
            for annotation in ANNOTATION_PATTERN.finditer(match.group("annotations"))
        )
        relations: list[tuple[str, str]] = []
        tail = match.group("tail")
        for edge_type, pattern in RELATION_PATTERN.items():
            relation = pattern.search(tail)
            if relation:
                relations.extend(
                    (edge_type, target)
                    for target in _split_types(relation.group("types"))
                )
        types.append(
            JavaType(
                kind=match.group("kind").upper(),
                name=name,
                qualified_name=qualified_name,
                line=line_number(match.start("kind")),
                end_line=line_number(match.end() - 1),
                annotations=annotations,
                relations=tuple(relations),
            )
        )

    return JavaUnit(path, file_id, package, imports, tuple(types))


def _read_source(root: Path, scanned: ScannedFile, limit: int) -> str:
    resolved_root = root.resolve(strict=True)
    candidate = resolved_root.joinpath(*PurePosixPath(scanned.path).parts)
    resolved_candidate = candidate.resolve(strict=True)
    if resolved_root not in resolved_candidate.parents:
        raise JavaAnalysisError("source path escapes repository root")
    metadata = candidate.stat(follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or candidate.is_symlink():
        raise JavaAnalysisError("source is no longer a regular file")
    if metadata.st_size > limit:
        raise JavaAnalysisError("source exceeds analyzer size limit")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(candidate, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > limit:
            raise JavaAnalysisError("opened source violates analyzer limits")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = -1
            content = stream.read(limit + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(content) > limit:
        raise JavaAnalysisError("source exceeds analyzer size limit")
    try:
        return content.decode("utf-8")
    except UnicodeError as error:
        raise JavaAnalysisError("source is not valid UTF-8") from error


def _evidence(
    path: str,
    start_line: int,
    end_line: int,
    kind: str,
    summary: str,
    rule_id: str | None = None,
) -> dict[str, Any]:
    identity = [path, start_line, end_line, kind, summary, rule_id]
    digest = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    result: dict[str, Any] = {
        "endLine": end_line,
        "evidenceId": f"evidence:sha256:{digest}",
        "extractor": EXTRACTOR,
        "kind": kind,
        "sourcePath": path,
        "startLine": start_line,
        "summary": summary,
    }
    if rule_id:
        result["ruleId"] = rule_id
    return result


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


def _annotation_identity(
    annotation: str,
    exact_imports: dict[str, str],
    wildcard_packages: set[str],
) -> str | None:
    if annotation in SPRING_RULES:
        return annotation
    if "." in annotation:
        return None
    imported = exact_imports.get(annotation)
    if imported in SPRING_RULES:
        return imported
    matches = sorted(
        f"{package}.{annotation}"
        for package in wildcard_packages & SPRING_WILDCARD_PACKAGES
        if f"{package}.{annotation}" in SPRING_RULES
    )
    return matches[0] if len(matches) == 1 else None


def _claim(value: str, evidence_id: str) -> dict[str, Any]:
    return {
        "confidence": "DIRECT",
        "evidenceIds": [evidence_id],
        "value": value,
    }


def _add_claim(entity: dict[str, Any], field: str, claim: dict[str, Any]) -> None:
    claims = entity.setdefault(field, [])
    existing = next(
        (
            item
            for item in claims
            if item["value"] == claim["value"]
            and item["confidence"] == claim["confidence"]
        ),
        None,
    )
    if existing is None:
        claims.append(claim)
    else:
        existing["evidenceIds"] = sorted(
            set(existing["evidenceIds"]) | set(claim["evidenceIds"])
        )
    claims.sort(
        key=lambda item: (
            item["value"],
            item["confidence"],
            item["evidenceIds"],
        )
    )


def _resolve_local_type(
    name: str,
    unit: JavaUnit,
    qualified_files: dict[str, list[str]],
) -> str | None:
    exact_imports = {
        item.name.rsplit(".", 1)[-1]: item.name
        for item in unit.imports
        if not item.is_static and not item.name.endswith(".*")
    }
    candidates = [name]
    if "." not in name:
        if name in exact_imports:
            candidates.insert(0, exact_imports[name])
        if unit.package:
            candidates.append(f"{unit.package}.{name}")
    for candidate in candidates:
        matches = qualified_files.get(candidate, [])
        if len(matches) == 1:
            return matches[0]
    return None


def _configuration_catalog_facts(
    scan: ScanResult, source_path: str
) -> tuple[CatalogFact, ...]:
    source = PurePosixPath(source_path)
    candidates: list[tuple[int, CatalogFact]] = []
    for configuration in scan.configurations:
        configuration_directory = PurePosixPath(configuration.path).parent
        if configuration_directory.parts[-3:] == ("src", "main", "resources"):
            scope_parts = configuration_directory.parts[:-3]
            configuration_directory = (
                PurePosixPath(*scope_parts) if scope_parts else PurePosixPath(".")
            )
        if configuration_directory != PurePosixPath("."):
            try:
                source.relative_to(configuration_directory)
            except ValueError:
                continue
        depth = (
            0
            if configuration_directory == PurePosixPath(".")
            else len(configuration_directory.parts)
        )
        for fact in configuration.facts:
            evidence = configuration_evidence(configuration, fact)
            candidates.append(
                (
                    depth,
                    CatalogFact(
                        "CONFIG",
                        f"{fact.key}={fact.value}",
                        evidence["evidenceId"],
                    ),
                )
            )
    if not candidates:
        return ()
    closest_depth = max(item[0] for item in candidates)
    return tuple(
        sorted({fact for depth, fact in candidates if depth == closest_depth})
    )


def enrich_java_graph(
    root: Path,
    scan: ScanResult,
    graph: dict[str, Any],
    limits: ScanLimits,
) -> dict[str, Any]:
    """Add bounded Java declarations, imports, relations, and Spring claims."""

    document = copy.deepcopy(graph)
    entities_by_path = {
        entity["path"]: entity
        for entity in document["entities"]
        if entity["kind"] == "FILE"
    }
    java_files = [item for item in scan.files if item.language == "java"]
    units: list[JavaUnit] = []
    for scanned in java_files:
        entity = entities_by_path[scanned.path]
        try:
            source = _read_source(root, scanned, limits.max_file_bytes)
            unit = _parse_unit(scanned.path, entity["id"], source)
            units.append(unit)
            if not unit.types:
                document["diagnostics"].append(
                    _diagnostic(
                        "JAVA_TYPE_NOT_FOUND",
                        "INFO",
                        "No top-level Java type declaration was recognized",
                        scanned.path,
                    )
                )
        except (OSError, JavaAnalysisError) as error:
            document["diagnostics"].append(
                _diagnostic(
                    "JAVA_ANALYSIS_SKIPPED",
                    "WARNING",
                    f"Java analysis skipped: {error}",
                    scanned.path,
                )
            )

    non_java_count = len(scan.files) - len(java_files)
    document["diagnostics"].append(
        _diagnostic(
            "JAVA_ANALYZER_COVERAGE",
            "INFO",
            (
                f"Java static analysis processed {len(units)} file(s); "
                f"{non_java_count} non-Java file(s) were not processed by this adapter; "
                "capabilities=imports,declarations,inheritance,frameworkRules"
            ),
        )
    )

    qualified_files: dict[str, list[str]] = {}
    for unit in units:
        for declared_type in unit.types:
            qualified_files.setdefault(declared_type.qualified_name, []).append(
                unit.file_id
            )
    for file_ids in qualified_files.values():
        file_ids.sort()

    evidence_by_id = {item["evidenceId"]: item for item in document["evidence"]}
    new_entities: dict[str, dict[str, Any]] = {}
    new_edges: dict[str, dict[str, Any]] = {}
    repository_id = document["repository"]["id"]

    def remember_evidence(item: dict[str, Any]) -> str:
        evidence_by_id[item["evidenceId"]] = item
        return item["evidenceId"]

    for unit in units:
        file_entity = entities_by_path[unit.path]
        catalog_facts = list(manifest_catalog_facts(document, unit.path))
        catalog_facts.extend(_configuration_catalog_facts(scan, unit.path))
        exact_imports = {
            item.name.rsplit(".", 1)[-1]: item.name
            for item in unit.imports
            if not item.is_static and not item.name.endswith(".*")
        }
        wildcard_packages = {
            item.name[:-2]
            for item in unit.imports
            if not item.is_static and item.name.endswith(".*")
        }

        for imported in unit.imports:
            if imported.is_static:
                continue
            import_evidence = _evidence(
                unit.path,
                imported.line,
                imported.line,
                "IMPORT",
                "Explicit Java import",
                "java.import",
            )
            evidence_id = remember_evidence(import_evidence)
            catalog_facts.append(CatalogFact("IMPORT", imported.name, evidence_id))
            local_targets = qualified_files.get(imported.name, [])
            if len(local_targets) > 1:
                document["diagnostics"].append(
                    _diagnostic(
                        "JAVA_IMPORT_AMBIGUOUS",
                        "WARNING",
                        "Java import matches multiple local declarations",
                        unit.path,
                    )
                )
                continue
            if len(local_targets) == 1 and local_targets[0] != unit.file_id:
                target_id = local_targets[0]
                edge_id = make_edge_id(
                    unit.file_id, "IMPORTS", target_id, imported.name
                )
                new_edges[edge_id] = {
                    "confidence": "RESOLVED",
                    "evidenceIds": [evidence_id],
                    "from": unit.file_id,
                    "id": edge_id,
                    "to": target_id,
                    "type": "IMPORTS",
                }
            else:
                external_name = (
                    imported.name[:-2]
                    if imported.name.endswith(".*")
                    else imported.name.rsplit(".", 1)[0]
                )
                external_path = external_name.replace(".", "/")
                external_id = make_entity_id(
                    repository_id, "EXTERNAL_PACKAGE", external_path
                )
                new_entities[external_id] = {
                    "id": external_id,
                    "kind": "EXTERNAL_PACKAGE",
                    "path": external_path,
                }
                edge_id = make_edge_id(
                    unit.file_id, "IMPORTS", external_id, imported.name
                )
                new_edges[edge_id] = {
                    "confidence": "DIRECT",
                    "evidenceIds": [evidence_id],
                    "from": unit.file_id,
                    "id": edge_id,
                    "to": external_id,
                    "type": "IMPORTS",
                }

        role_candidates: list[tuple[int, str, str, str | None, str]] = []
        for declared_type in unit.types:
            declaration_evidence = _evidence(
                unit.path,
                declared_type.line,
                declared_type.end_line,
                "AST",
                f"Java {declared_type.kind.lower()} declaration",
                "java.declaration",
            )
            declaration_evidence_id = remember_evidence(declaration_evidence)
            symbol_id = make_entity_id(
                repository_id,
                "SYMBOL",
                unit.path,
                declared_type.qualified_name,
            )
            new_entities[symbol_id] = {
                "id": symbol_id,
                "kind": "SYMBOL",
                "language": "java",
                "path": unit.path,
            }
            declaration_edge_id = make_edge_id(
                unit.file_id, "DECLARES", symbol_id, declared_type.qualified_name
            )
            new_edges[declaration_edge_id] = {
                "confidence": "DIRECT",
                "evidenceIds": [declaration_evidence_id],
                "from": unit.file_id,
                "id": declaration_edge_id,
                "to": symbol_id,
                "type": "DECLARES",
            }

            for annotation, line in declared_type.annotations:
                identity = _annotation_identity(
                    annotation, exact_imports, wildcard_packages
                )
                if identity is None:
                    continue
                priority, role, technology, capability, rule_id = SPRING_RULES[identity]
                annotation_evidence = _evidence(
                    unit.path,
                    line,
                    line,
                    "ANNOTATION",
                    "Verified Spring annotation",
                    rule_id,
                )
                annotation_evidence_id = remember_evidence(annotation_evidence)
                catalog_facts.append(
                    CatalogFact("ANNOTATION", identity, annotation_evidence_id)
                )
                role_candidates.append(
                    (
                        priority,
                        role,
                        technology,
                        capability,
                        annotation_evidence_id,
                    )
                )

            for edge_type, target_name in declared_type.relations:
                relation_evidence = _evidence(
                    unit.path,
                    declared_type.line,
                    declared_type.end_line,
                    "INHERITANCE",
                    f"Explicit Java {edge_type.lower()} declaration",
                    "java.inheritance",
                )
                relation_evidence_id = remember_evidence(relation_evidence)
                target_file_id = _resolve_local_type(target_name, unit, qualified_files)
                if target_file_id and target_file_id != unit.file_id:
                    edge_id = make_edge_id(
                        unit.file_id, edge_type, target_file_id, target_name
                    )
                    new_edges[edge_id] = {
                        "confidence": "RESOLVED",
                        "evidenceIds": [relation_evidence_id],
                        "from": unit.file_id,
                        "id": edge_id,
                        "to": target_file_id,
                        "type": edge_type,
                    }
                elif target_name == "JpaRepository" and (
                    exact_imports.get("JpaRepository") == JPA_REPOSITORY
                    or "org.springframework.data.jpa.repository" in wildcard_packages
                ):
                    repository_evidence = _evidence(
                        unit.path,
                        declared_type.line,
                        declared_type.end_line,
                        "INHERITANCE",
                        "Verified Spring Data repository inheritance",
                        "spring.repository",
                    )
                    repository_evidence_id = remember_evidence(repository_evidence)
                    catalog_facts.append(
                        CatalogFact(
                            "INHERITANCE",
                            JPA_REPOSITORY,
                            repository_evidence_id,
                        )
                    )
                    role_candidates.append(
                        (
                            2,
                            "PERSISTENCE_ADAPTER",
                            "SPRING_DATA_JPA",
                            None,
                            repository_evidence_id,
                        )
                    )
                else:
                    document["diagnostics"].append(
                        _diagnostic(
                            "JAVA_RELATION_UNRESOLVED",
                            "INFO",
                            "Java inheritance target could not be bound locally",
                            unit.path,
                        )
                    )

        if role_candidates:
            selected = min(role_candidates, key=lambda item: (item[0], item[1]))
            _, role, technology, capability, evidence_id = selected
            _add_claim(file_entity, "roles", _claim(role, evidence_id))
            _add_claim(
                file_entity,
                "technologies",
                _claim(technology, evidence_id),
            )
            if capability:
                _add_claim(
                    file_entity,
                    "capabilities",
                    _claim(capability, evidence_id),
                )

        catalog_claims = resolve_catalog_claims(catalog_facts)
        for field, claims in catalog_claims.items():
            for claim in claims:
                _add_claim(file_entity, field, claim)

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
        raise JavaAnalysisError("generated invalid UCG: " + "; ".join(errors))
    return document
