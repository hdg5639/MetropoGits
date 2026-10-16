#!/usr/bin/env python3
"""Validate MetropoGits cross-repository link and metropolis documents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

if __package__:
    from .canonical_json import CanonicalJsonError, loads_strict_json
else:
    from canonical_json import CanonicalJsonError, loads_strict_json


ROOT = Path(__file__).resolve().parents[1]
LINKS_SCHEMA_PATH = ROOT / "schemas" / "metropolis-links-0.1.schema.json"
SCHEMA_PATH = ROOT / "schemas" / "metropolis-0.1.schema.json"


def _json_path(parts: list[Any]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _schema_errors(document: Any, path: Path) -> list[str]:
    schema = json.loads(path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: (_json_path(list(error.absolute_path)), error.message),
    )
    return [
        f"{_json_path(list(error.absolute_path))}: {error.message}"
        for error in errors
    ]


def _validate_links(
    links: list[dict[str, Any]], known_repositories: set[str] | None
) -> list[str]:
    errors: list[str] = []
    ids = [link["id"] for link in links]
    duplicates = sorted({link_id for link_id in ids if ids.count(link_id) > 1})
    if duplicates:
        errors.append("link IDs must be unique: " + ", ".join(duplicates))
    if links != sorted(links, key=lambda item: item["id"]):
        errors.append("links must use canonical order")

    for index, link in enumerate(links):
        label = f"$.links[{index}]"
        source = link["from"]
        target = link["to"]
        evidence_refs = link["evidenceRefs"]
        if source["repositoryId"] is None or source["entityId"] is None:
            errors.append(f"{label}.from must identify a repository entity")
        if source["label"] is not None:
            errors.append(f"{label}.from.label must be null")
        if evidence_refs != sorted(
            evidence_refs, key=lambda item: (item["repositoryId"], item["evidenceId"])
        ):
            errors.append(f"{label}.evidenceRefs must use canonical order")
        if source["repositoryId"] is not None and not any(
            item["repositoryId"] == source["repositoryId"]
            for item in evidence_refs
        ):
            errors.append(f"{label} requires evidence from its source repository")

        if link["status"] == "VERIFIED":
            if target["repositoryId"] is None or target["entityId"] is None:
                errors.append(f"{label}.to must identify a verified repository entity")
            if target["label"] is not None:
                errors.append(f"{label}.to.label must be null for VERIFIED links")
        else:
            if target["entityId"] is not None or target["label"] is None:
                errors.append(
                    f"{label}.to must have a label and no entity for UNRESOLVED links"
                )

        if (
            source["repositoryId"] is not None
            and target["repositoryId"] == source["repositoryId"]
        ):
            errors.append(f"{label} must connect distinct repositories")
        if known_repositories is not None:
            referenced = {
                source["repositoryId"],
                target["repositoryId"],
                *(item["repositoryId"] for item in evidence_refs),
            }
            unknown = sorted(
                item
                for item in referenced
                if item is not None and item not in known_repositories
            )
            if unknown:
                errors.append(
                    f"{label} references unknown repositories: " + ", ".join(unknown)
                )
    return errors


def validate_document(document: Any) -> list[str]:
    """Validate either a link manifest or a generated metropolis document."""

    if not isinstance(document, dict):
        return ["$: root must be an object"]
    schema_version = document.get("schemaVersion")
    if schema_version == "metropolis-links/0.1":
        errors = _schema_errors(document, LINKS_SCHEMA_PATH)
        if errors:
            return errors
        return sorted(_validate_links(document["links"], None))
    if schema_version == "metropolis/0.1":
        errors = _schema_errors(document, SCHEMA_PATH)
        if errors:
            return errors
        repositories = document["repositories"]
        repository_ids = [item["id"] for item in repositories]
        if len(set(repository_ids)) != len(repository_ids):
            errors.append("repository IDs must be unique")
        if repositories != sorted(repositories, key=lambda item: item["id"]):
            errors.append("repositories must use canonical order")
        errors.extend(_validate_links(document["links"], set(repository_ids)))
        return sorted(errors)
    return [f"unsupported schemaVersion: {schema_version!r}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        document = loads_strict_json(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, CanonicalJsonError) as error:
        print(f"Unable to read metropolis JSON: {error}", file=sys.stderr)
        return 2
    errors = validate_document(document)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Valid {document['schemaVersion']} document: {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
