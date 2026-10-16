#!/usr/bin/env python3
"""Validate a MetropoGits City Scene v0.1 document against its UCG."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

if __package__:
    from .canonical_json import (
        CanonicalJsonError,
        canonical_json_bytes,
        loads_strict_json,
        sha256_digest,
    )
    from .validate_ucg import validate_document as validate_ucg_document
else:
    from canonical_json import (
        CanonicalJsonError,
        canonical_json_bytes,
        loads_strict_json,
        sha256_digest,
    )
    from validate_ucg import validate_document as validate_ucg_document


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "city-0.1.schema.json"


def ucg_digest(document: Any) -> str:
    return sha256_digest(document)


def _json_path(parts: list[Any]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _check_unique(errors: list[str], label: str, values: list[str]) -> None:
    duplicates = sorted(_duplicates(values))
    if duplicates:
        errors.append(f"{label} must be unique: {', '.join(duplicates)}")


def _check_sorted(
    errors: list[str], label: str, values: list[Any], key: Callable[[Any], Any]
) -> None:
    if values != sorted(values, key=key):
        errors.append(f"{label} must use canonical order")


def _check_district_hierarchy(
    errors: list[str], districts_by_id: dict[str, dict[str, Any]]
) -> None:
    reported_cycles: set[frozenset[str]] = set()
    for district_id in sorted(districts_by_id):
        chain: list[str] = []
        current: str | None = district_id
        while current is not None and current in districts_by_id:
            if current in chain:
                cycle = frozenset(chain[chain.index(current) :])
                if cycle not in reported_cycles:
                    errors.append(
                        "district hierarchy contains a cycle: "
                        + " -> ".join(sorted(cycle))
                    )
                    reported_cycles.add(cycle)
                break
            chain.append(current)
            current = districts_by_id[current]["parentId"]


def validate_document(scene: Any, ucg: Any) -> list[str]:
    """Return deterministic scene schema and cross-contract errors."""

    ucg_errors = validate_ucg_document(ucg)
    if ucg_errors:
        return [f"ucg: {error}" for error in ucg_errors]

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    schema_errors = sorted(
        validator.iter_errors(scene),
        key=lambda error: (_json_path(list(error.absolute_path)), error.message),
    )
    errors = [
        f"{_json_path(list(error.absolute_path))}: {error.message}"
        for error in schema_errors
    ]
    if schema_errors or not isinstance(scene, dict):
        return errors

    expected_digest = ucg_digest(ucg)
    if scene["ucgDigest"] != expected_digest:
        errors.append(
            f"$.ucgDigest does not match UCG content; expected {expected_digest}"
        )

    districts = scene["districts"]
    buildings = scene["buildings"]
    networks = scene["networks"]
    decorations = scene["decorations"]

    district_ids = [item["id"] for item in districts]
    building_ids = [item["entityId"] for item in buildings]
    network_ids = [item["id"] for item in networks]

    _check_unique(errors, "district IDs", district_ids)
    _check_unique(errors, "building entity IDs", building_ids)
    _check_unique(errors, "network IDs", network_ids)
    _check_sorted(errors, "districts", districts, key=lambda item: item["id"])
    _check_sorted(
        errors, "buildings", buildings, key=lambda item: item["entityId"]
    )
    _check_sorted(errors, "networks", networks, key=lambda item: item["id"])
    _check_sorted(
        errors,
        "decorations",
        decorations,
        key=lambda item: canonical_json_bytes(item),
    )

    districts_by_id = {item["id"]: item for item in districts}
    for index, district in enumerate(districts):
        parent_id = district["parentId"]
        if parent_id is not None and parent_id not in districts_by_id:
            errors.append(
                f"$.districts[{index}].parentId references missing district "
                f"{parent_id!r}"
            )
    _check_district_hierarchy(errors, districts_by_id)

    entities_by_id = {item["id"]: item for item in ucg["entities"]}
    known_evidence = {item["evidenceId"] for item in ucg["evidence"]}
    known_edges = {item["id"] for item in ucg["edges"]}

    for index, building in enumerate(buildings):
        entity_id = building["entityId"]
        entity = entities_by_id.get(entity_id)
        if entity is None:
            errors.append(
                f"$.buildings[{index}].entityId references missing UCG entity "
                f"{entity_id!r}"
            )
        elif entity["kind"] != "FILE":
            errors.append(
                f"$.buildings[{index}].entityId must reference a FILE entity"
            )
        if building["districtId"] not in districts_by_id:
            errors.append(
                f"$.buildings[{index}].districtId references missing district "
                f"{building['districtId']!r}"
            )
        _check_sorted(
            errors,
            f"$.buildings[{index}].evidenceIds",
            building["evidenceIds"],
            key=lambda value: value,
        )
        for evidence_id in building["evidenceIds"]:
            if evidence_id not in known_evidence:
                errors.append(
                    f"$.buildings[{index}].evidenceIds references missing UCG "
                    f"evidence {evidence_id!r}"
                )

    for index, network in enumerate(networks):
        _check_sorted(
            errors,
            f"$.networks[{index}].edgeIds",
            network["edgeIds"],
            key=lambda value: value,
        )
        for edge_id in network["edgeIds"]:
            if edge_id not in known_edges:
                errors.append(
                    f"$.networks[{index}].edgeIds references missing UCG edge "
                    f"{edge_id!r}"
                )

    return sorted(errors)


def _load_json(path: Path, label: str) -> Any:
    try:
        return loads_strict_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, CanonicalJsonError) as error:
        raise ValueError(f"Unable to read {label} JSON: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="City Scene JSON file to validate")
    parser.add_argument(
        "--ucg", type=Path, required=True, help="source UCG JSON document"
    )
    args = parser.parse_args()

    try:
        scene = _load_json(args.input, "City Scene")
        ucg = _load_json(args.ucg, "UCG")
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    errors = validate_document(scene, ucg)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"Valid City Scene document: {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
