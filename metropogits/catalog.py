"""Load and apply the bundled declarative technology catalog."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from scripts.canonical_json import loads_strict_json
from scripts.validate_catalog import validate_document as validate_catalog_document


CATALOG_VERSION = "0.2.0"
CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / CATALOG_VERSION
    / "catalog.json"
)
CLAIM_FIELDS = ("capabilities", "roles", "technologies")


class CatalogError(ValueError):
    """Raised when the bundled catalog cannot be loaded safely."""


@dataclass(frozen=True, order=True)
class CatalogFact:
    kind: str
    value: str
    evidence_id: str


@lru_cache(maxsize=1)
def load_bundled_catalog() -> dict[str, Any]:
    """Return the validated bundled catalog release."""

    try:
        document = loads_strict_json(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise CatalogError(f"unable to load bundled catalog: {error}") from error
    errors = validate_catalog_document(document)
    if errors:
        raise CatalogError("bundled catalog is invalid: " + "; ".join(errors))
    if document["catalogVersion"] != CATALOG_VERSION:
        raise CatalogError("bundled catalog version does not match its release path")
    return document


def _required_facts(rule: dict[str, Any]) -> set[tuple[str, str]]:
    match = rule["match"]
    result = {("MANIFEST", value) for value in match["packageCoordinates"]}
    result.update(
        (signature["kind"], signature["value"])
        for signature in match["codeSignatures"]
    )
    result.update(
        ("CONFIG", f"{signature['key']}={signature['value']}")
        for signature in match["configSignatures"]
    )
    return result


def resolve_catalog_claims(
    facts: Iterable[CatalogFact],
) -> dict[str, list[dict[str, Any]]]:
    """Resolve exact facts into deterministic evidence-backed UCG claims."""

    evidence_by_fact: dict[tuple[str, str], set[str]] = {}
    for fact in facts:
        evidence_by_fact.setdefault((fact.kind, fact.value), set()).add(
            fact.evidence_id
        )
    available = set(evidence_by_fact)
    claims: dict[tuple[str, str, str], set[str]] = {}

    for rule in load_bundled_catalog()["rules"]:
        required = _required_facts(rule)
        blocked = {
            (predicate["kind"], predicate["value"])
            for predicate in rule["negativePredicates"]
        }
        if not required.issubset(available) or not available.isdisjoint(blocked):
            continue
        evidence_ids = {
            evidence_id
            for fact in required
            for evidence_id in evidence_by_fact[fact]
        }
        confidence = (
            "DIRECT" if rule["produces"]["usage"] == "DIRECT" else "INFERRED"
        )
        outputs = {
            "technologies": [rule["produces"]["technology"]],
            "capabilities": rule["produces"]["capabilities"],
            "roles": rule["produces"]["roles"],
        }
        for field in CLAIM_FIELDS:
            for value in outputs[field]:
                claims.setdefault((field, value, confidence), set()).update(evidence_ids)

    result = {field: [] for field in CLAIM_FIELDS}
    for (field, value, confidence), evidence_ids in sorted(claims.items()):
        result[field].append(
            {
                "confidence": confidence,
                "evidenceIds": sorted(evidence_ids),
                "value": value,
            }
        )
    return result


def manifest_catalog_facts(
    graph: dict[str, Any], source_path: str
) -> tuple[CatalogFact, ...]:
    """Return manifest facts from the closest module scope containing a source."""

    entities = {item["id"]: item for item in graph["entities"]}
    evidence = {item["evidenceId"]: item for item in graph["evidence"]}
    source = PurePosixPath(source_path)
    candidates: list[tuple[int, CatalogFact]] = []
    for edge in graph["edges"]:
        if edge["type"] != "DEPENDS_ON":
            continue
        module = entities.get(edge["from"])
        package = entities.get(edge["to"])
        if not module or module["kind"] != "MODULE" or not package:
            continue
        if package["kind"] != "EXTERNAL_PACKAGE":
            continue
        module_directory = PurePosixPath(module["path"]).parent
        if module_directory != PurePosixPath("."):
            try:
                source.relative_to(module_directory)
            except ValueError:
                continue
        package_path = package.get("path", "")
        if package_path.startswith("maven/"):
            segments = package_path.removeprefix("maven/").split("/")
            if len(segments) < 2:
                continue
            coordinate = f"{'.'.join(segments[:-1])}:{segments[-1]}"
        elif package_path.startswith("npm/"):
            coordinate = package_path.removeprefix("npm/")
        else:
            continue
        depth = 0 if module_directory == PurePosixPath(".") else len(module_directory.parts)
        for evidence_id in edge["evidenceIds"]:
            item = evidence.get(evidence_id)
            if item and item["kind"] == "MANIFEST":
                candidates.append(
                    (depth, CatalogFact("MANIFEST", coordinate, evidence_id))
                )
    if not candidates:
        return ()
    closest_depth = max(item[0] for item in candidates)
    return tuple(
        sorted({fact for depth, fact in candidates if depth == closest_depth})
    )
