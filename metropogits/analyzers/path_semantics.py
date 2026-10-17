"""Conservative semantic claims derived from exact source-path conventions."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from scripts.canonical_json import canonical_json_bytes
from scripts.validate_ucg import validate_document as validate_ucg_document


EXTRACTOR = "path-semantics/0.1"
JSTS_LANGUAGES = frozenset({"javascript", "typescript"})
JSTS_TEST_MARKERS = (".spec.", ".test.")


class PathSemanticsError(ValueError):
    """Raised when path-derived enrichment cannot produce a valid graph."""


@dataclass(frozen=True)
class PathRule:
    capabilities: tuple[str, ...]
    role: str
    rule_id: str
    summary: str
    technology: str | None = None


NEXT_PAGE = PathRule(
    capabilities=("UI",),
    role="UI_PAGE",
    rule_id="path.nextjs.app-page",
    summary="Exact Next.js App Router page path",
    technology="NEXT_JS",
)
NEXT_ROUTE = PathRule(
    capabilities=("API",),
    role="API_ENDPOINT",
    rule_id="path.nextjs.route-handler",
    summary="Exact Next.js App Router route handler path",
    technology="NEXT_JS",
)
TEST_SOURCE = PathRule(
    capabilities=("TEST",),
    role="TEST",
    rule_id="path.test-source",
    summary="Conventional test source path",
)


def _has_sequence(parts: tuple[str, ...], sequence: tuple[str, ...]) -> bool:
    return any(
        parts[index : index + len(sequence)] == sequence
        for index in range(len(parts) - len(sequence) + 1)
    )


def _rules_for(path: str, language: str | None) -> tuple[PathRule, ...]:
    pure_path = PurePosixPath(path)
    parts = pure_path.parts
    parents = parts[:-1]
    name = pure_path.name
    rules: list[PathRule] = []

    if language in JSTS_LANGUAGES and "app" in parents:
        if name == "page.tsx":
            rules.append(NEXT_PAGE)
        elif name == "route.ts":
            rules.append(NEXT_ROUTE)

    if language == "java" and _has_sequence(parts, ("src", "test", "java")):
        rules.append(TEST_SOURCE)
    elif language in JSTS_LANGUAGES and (
        "__tests__" in parents
        or any(marker in name for marker in JSTS_TEST_MARKERS)
    ):
        rules.append(TEST_SOURCE)
    return tuple(sorted(rules, key=lambda rule: rule.rule_id))


def _evidence(path: str, rule: PathRule) -> dict[str, Any]:
    identity = [path, "PATH", rule.rule_id, rule.summary]
    digest = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    return {
        "evidenceId": f"evidence:sha256:{digest}",
        "extractor": EXTRACTOR,
        "kind": "PATH",
        "ruleId": rule.rule_id,
        "sourcePath": path,
        "summary": rule.summary,
    }


def _add_claim(
    entity: dict[str, Any], field: str, value: str, evidence_id: str
) -> None:
    claims = entity.setdefault(field, [])
    existing = next(
        (
            claim
            for claim in claims
            if claim["value"] == value and claim["confidence"] == "DIRECT"
        ),
        None,
    )
    if existing is None:
        claims.append(
            {
                "confidence": "DIRECT",
                "evidenceIds": [evidence_id],
                "value": value,
            }
        )
    else:
        existing["evidenceIds"] = sorted(
            set(existing["evidenceIds"]) | {evidence_id}
        )


def enrich_path_semantics(graph: dict[str, Any]) -> dict[str, Any]:
    """Add exact PATH-evidenced roles without reading or executing source files."""

    document = copy.deepcopy(graph)
    evidence_by_id = {item["evidenceId"]: item for item in document["evidence"]}
    matched_files = 0
    matched_rules = 0
    for entity in document["entities"]:
        if entity["kind"] != "FILE" or "path" not in entity:
            continue
        rules = _rules_for(entity["path"], entity.get("language"))
        if not rules:
            continue
        matched_files += 1
        matched_rules += len(rules)
        for rule in rules:
            item = _evidence(entity["path"], rule)
            evidence_by_id[item["evidenceId"]] = item
            evidence_id = item["evidenceId"]
            _add_claim(entity, "roles", rule.role, evidence_id)
            for capability in rule.capabilities:
                _add_claim(entity, "capabilities", capability, evidence_id)
            if rule.technology:
                _add_claim(entity, "technologies", rule.technology, evidence_id)
        for field in ("capabilities", "roles", "technologies"):
            entity.get(field, []).sort(
                key=lambda claim: (
                    claim["value"],
                    claim["confidence"],
                    claim["evidenceIds"],
                )
            )

    document["evidence"] = sorted(
        evidence_by_id.values(), key=lambda item: item["evidenceId"]
    )
    document["diagnostics"].append(
        {
            "code": "PATH_SEMANTICS_COVERAGE",
            "message": (
                f"Path rules classified {matched_files} file(s) with "
                f"{matched_rules} exact convention match(es)"
            ),
            "severity": "INFO",
        }
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
        raise PathSemanticsError("generated invalid UCG: " + "; ".join(errors))
    return document


__all__ = ["enrich_path_semantics"]
