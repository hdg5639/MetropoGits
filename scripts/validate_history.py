#!/usr/bin/env python3
"""Validate a MetropoGits history timeline v0.1 document."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

if __package__:
    from .canonical_json import (
        CanonicalJsonError,
        canonical_json_bytes,
        loads_strict_json,
    )
else:
    from canonical_json import CanonicalJsonError, canonical_json_bytes, loads_strict_json


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "history-0.1.schema.json"
TRANSITION_FIELDS = (
    "addedEntityIds",
    "removedEntityIds",
    "changedEntityIds",
    "unchangedEntityIds",
)


def _json_path(parts: list[Any]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def validate_document(document: Any) -> list[str]:
    """Return deterministic schema and cross-reference errors."""

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema_errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: (_json_path(list(error.absolute_path)), error.message),
    )
    errors = [
        f"{_json_path(list(error.absolute_path))}: {error.message}"
        for error in schema_errors
    ]
    if schema_errors or not isinstance(document, dict):
        return errors

    frames = document["frames"]
    revisions = [frame["revision"] for frame in frames]
    if len(set(revisions)) != len(revisions):
        errors.append("frame revisions must be unique")
    if [frame["index"] for frame in frames] != list(range(len(frames))):
        errors.append("frame indexes must be contiguous and start at zero")

    transitions = document["transitions"]
    if len(transitions) != len(frames) - 1:
        errors.append("transitions must connect every adjacent frame")
    for index, transition in enumerate(transitions):
        if index + 1 >= len(frames):
            break
        if transition["fromRevision"] != revisions[index]:
            errors.append(f"$.transitions[{index}].fromRevision is not adjacent")
        if transition["toRevision"] != revisions[index + 1]:
            errors.append(f"$.transitions[{index}].toRevision is not adjacent")
        seen: set[str] = set()
        for field in TRANSITION_FIELDS:
            values = transition[field]
            if values != sorted(values):
                errors.append(
                    f"$.transitions[{index}].{field} must use canonical order"
                )
            overlap = sorted(seen & set(values))
            if overlap:
                errors.append(
                    f"$.transitions[{index}] classifications overlap: "
                    + ", ".join(overlap)
                )
            seen.update(values)

    lineages = document["lineages"]
    if lineages != sorted(lineages, key=lambda item: item["lineageId"]):
        errors.append("lineages must use canonical order")
    lineage_ids = [item["lineageId"] for item in lineages]
    if len(set(lineage_ids)) != len(lineage_ids):
        errors.append("lineage IDs must be unique")
    known_revisions = set(revisions)
    revision_positions = {revision: index for index, revision in enumerate(revisions)}
    for index, lineage in enumerate(lineages):
        lineage_revisions = [item["revision"] for item in lineage["revisions"]]
        entity_ids = {item["entityId"] for item in lineage["revisions"]}
        if len(entity_ids) != 1:
            errors.append(f"$.lineages[{index}] must reference one stable entity ID")
        else:
            entity_id = next(iter(entity_ids))
            digest = hashlib.sha256(
                canonical_json_bytes([document["repositoryId"], entity_id])
            ).hexdigest()
            if lineage["lineageId"] != f"lineage:sha256:{digest}":
                errors.append(f"$.lineages[{index}].lineageId is not deterministic")
        if len(set(lineage_revisions)) != len(lineage_revisions):
            errors.append(f"$.lineages[{index}].revisions must be unique")
        if any(revision not in known_revisions for revision in lineage_revisions):
            errors.append(f"$.lineages[{index}] references an unknown revision")
            continue
        if lineage_revisions != sorted(
            lineage_revisions, key=revision_positions.__getitem__
        ):
            errors.append(f"$.lineages[{index}].revisions must follow frame order")
        if lineage["firstRevision"] != lineage_revisions[0]:
            errors.append(f"$.lineages[{index}].firstRevision is inconsistent")
        if lineage["lastRevision"] != lineage_revisions[-1]:
            errors.append(f"$.lineages[{index}].lastRevision is inconsistent")
    return sorted(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="history JSON file to validate")
    args = parser.parse_args()
    try:
        document = loads_strict_json(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, CanonicalJsonError) as error:
        print(f"Unable to read history JSON: {error}", file=sys.stderr)
        return 2
    errors = validate_document(document)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Valid history document: {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
