#!/usr/bin/env python3
"""Validate a MetropoGits UCG v0.1 document."""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "ucg-0.1.schema.json"
CLAIM_FIELDS = ("technologies", "capabilities", "roles")


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


def _is_normalized_relative_path(value: str) -> bool:
    return (
        value == posixpath.normpath(value)
        and not value.startswith("/")
        and not re.match(r"^[A-Za-z]:/", value)
        and "\\" not in value
        and ".." not in value.split("/")
    )


def _check_sorted(
    errors: list[str], label: str, values: list[Any], key: Any
) -> None:
    if values != sorted(values, key=key):
        errors.append(f"{label} must use canonical order")


def _check_evidence_references(
    errors: list[str], label: str, evidence_ids: list[str], known: set[str]
) -> None:
    _check_sorted(errors, label, evidence_ids, key=lambda value: value)
    for evidence_id in evidence_ids:
        if evidence_id not in known:
            errors.append(f"{label} references missing evidence {evidence_id!r}")


def validate_document(document: Any) -> list[str]:
    """Return deterministic contract errors for a decoded UCG document."""

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    schema_errors = sorted(
        validator.iter_errors(document),
        key=lambda error: (_json_path(list(error.absolute_path)), error.message),
    )
    errors = [
        f"{_json_path(list(error.absolute_path))}: {error.message}"
        for error in schema_errors
    ]
    if schema_errors or not isinstance(document, dict):
        return errors

    entities = document["entities"]
    edges = document["edges"]
    evidence = document["evidence"]

    entity_ids = [item["id"] for item in entities]
    edge_ids = [item["id"] for item in edges]
    evidence_ids = [item["evidenceId"] for item in evidence]

    for label, values in (
        ("entity IDs", entity_ids),
        ("edge IDs", edge_ids),
        ("evidence IDs", evidence_ids),
    ):
        duplicates = sorted(_duplicates(values))
        if duplicates:
            errors.append(f"{label} must be unique: {', '.join(duplicates)}")

    _check_sorted(errors, "entities", entities, key=lambda item: item["id"])
    _check_sorted(errors, "edges", edges, key=lambda item: item["id"])
    _check_sorted(errors, "evidence", evidence, key=lambda item: item["evidenceId"])

    known_entities = set(entity_ids)
    known_evidence = set(evidence_ids)

    for index, entity in enumerate(entities):
        if "path" in entity and not _is_normalized_relative_path(entity["path"]):
            errors.append(f"$.entities[{index}].path must be a normalized relative path")
        for field in CLAIM_FIELDS:
            claims = entity.get(field, [])
            _check_sorted(
                errors,
                f"$.entities[{index}].{field}",
                claims,
                key=lambda claim: (
                    claim["value"],
                    claim["confidence"],
                    claim["evidenceIds"],
                ),
            )
            for claim_index, claim in enumerate(claims):
                label = f"$.entities[{index}].{field}[{claim_index}].evidenceIds"
                _check_evidence_references(
                    errors, label, claim["evidenceIds"], known_evidence
                )
                if claim["confidence"] in {"DIRECT", "RESOLVED"} and not claim[
                    "evidenceIds"
                ]:
                    errors.append(
                        f"{label} must not be empty for {claim['confidence']} claims"
                    )

    for index, edge in enumerate(edges):
        for endpoint in ("from", "to"):
            if edge[endpoint] not in known_entities:
                errors.append(
                    f"$.edges[{index}].{endpoint} references missing entity "
                    f"{edge[endpoint]!r}"
                )
        _check_evidence_references(
            errors,
            f"$.edges[{index}].evidenceIds",
            edge["evidenceIds"],
            known_evidence,
        )

    for index, item in enumerate(evidence):
        if not _is_normalized_relative_path(item["sourcePath"]):
            errors.append(
                f"$.evidence[{index}].sourcePath must be a normalized relative path"
            )
        if item.get("endLine", 1) < item.get("startLine", 1):
            errors.append(f"$.evidence[{index}].endLine must be >= startLine")

    return sorted(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UCG JSON file to validate")
    args = parser.parse_args()

    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"Unable to read UCG JSON: {error}", file=sys.stderr)
        return 2

    errors = validate_document(document)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"Valid UCG document: {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
