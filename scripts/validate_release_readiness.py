#!/usr/bin/env python3
"""Validate release-readiness evidence and referenced local tests."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

if __package__:
    from .canonical_json import CanonicalJsonError, loads_strict_json
else:
    from canonical_json import CanonicalJsonError, loads_strict_json


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "release-readiness-0.1.schema.json"
EXPECTED_REQUIREMENTS = {f"FR-{index:03d}" for index in range(1, 17)}
EXPECTED_ACCEPTANCE = {f"AC-{index:03d}" for index in range(1, 15)}
EXPECTED_RELEASE_CHECKS = {
    "ACCEPTANCE_EVIDENCE",
    "CONTRACT_BASELINES",
    "DECISION_COMPLIANCE",
    "FRESH_REPOSITORY_PUBLISHING",
    "GOVERNANCE_REVIEW",
    "INSPECTOR_INTEGRITY",
    "LOCAL_ONLY_PIPELINE",
    "P0_REQUIREMENTS",
    "PROJECT_LICENSE",
    "REPRODUCIBLE_ARTIFACTS",
}


def _json_path(parts: list[Any]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _schema_errors(document: Any) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: (_json_path(list(error.absolute_path)), error.message),
    )
    return [
        f"{_json_path(list(error.absolute_path))}: {error.message}"
        for error in errors
    ]


def _check_ids(entries: list[dict[str, Any]], expected: set[str], label: str) -> list[str]:
    ids = [entry["id"] for entry in entries]
    errors: list[str] = []
    if len(ids) != len(set(ids)):
        errors.append(f"{label} IDs must be unique")
    if ids != sorted(ids):
        errors.append(f"{label} must use canonical ID order")
    missing = sorted(expected - set(ids))
    unexpected = sorted(set(ids) - expected)
    if missing:
        errors.append(f"{label} missing IDs: " + ", ".join(missing))
    if unexpected:
        errors.append(f"{label} has unexpected IDs: " + ", ".join(unexpected))
    return errors


def _safe_path(reference: str) -> Path | None:
    raw_path = reference.split("::", 1)[0]
    pure = PurePosixPath(raw_path)
    if pure.is_absolute() or ".." in pure.parts or "\\" in raw_path:
        return None
    resolved = (ROOT / Path(*pure.parts)).resolve(strict=False)
    if resolved != ROOT and ROOT not in resolved.parents:
        return None
    return resolved


def _test_selector_exists(reference: str, path: Path) -> bool:
    parts = reference.split("::")
    if len(parts) != 3 or not parts[2].startswith("test_"):
        return False
    try:
        module = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError):
        return False
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == parts[1]:
            return any(
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name == parts[2]
                for child in node.body
            )
    return False


def _validate_evidence(entries: list[dict[str, Any]], label: str) -> list[str]:
    errors: list[str] = []
    for index, entry in enumerate(entries):
        prefix = f"$.{label}[{index}]"
        if entry["evidence"] != sorted(entry["evidence"]):
            errors.append(f"{prefix}.evidence must use canonical order")
        if entry["status"] == "BLOCKED":
            if entry["blocker"] is None:
                errors.append(f"{prefix}.blocker is required for BLOCKED status")
        elif entry["blocker"] is not None:
            errors.append(f"{prefix}.blocker must be null unless status is BLOCKED")
        if entry["status"] == "AUTOMATED" and not any(
            "::" in reference for reference in entry["evidence"]
        ):
            errors.append(f"{prefix} requires a test selector for AUTOMATED status")
        for reference in entry["evidence"]:
            path = _safe_path(reference)
            if path is None:
                errors.append(f"{prefix}.evidence has unsafe path: {reference}")
            elif not path.is_file():
                errors.append(f"{prefix}.evidence path does not exist: {reference}")
            elif "::" in reference and not _test_selector_exists(reference, path):
                errors.append(f"{prefix}.evidence test does not exist: {reference}")
    return errors


def validate_document(document: Any) -> list[str]:
    """Return deterministic validation errors for a readiness document."""

    errors = _schema_errors(document)
    if errors:
        return errors
    errors.extend(
        _check_ids(
            document["requirements"], EXPECTED_REQUIREMENTS, "requirements"
        )
    )
    errors.extend(
        _check_ids(
            document["acceptanceCriteria"],
            EXPECTED_ACCEPTANCE,
            "acceptanceCriteria",
        )
    )
    errors.extend(
        _check_ids(
            document["releaseChecks"], EXPECTED_RELEASE_CHECKS, "releaseChecks"
        )
    )
    for label in ("requirements", "acceptanceCriteria", "releaseChecks"):
        errors.extend(_validate_evidence(document[label], label))

    release_checks = {
        entry["id"]: entry for entry in document["releaseChecks"]
    }
    aggregate_sources = {
        "P0_REQUIREMENTS": document["requirements"],
        "ACCEPTANCE_EVIDENCE": document["acceptanceCriteria"],
    }
    for check_id, entries in aggregate_sources.items():
        release_check = release_checks.get(check_id)
        if release_check is None:
            continue
        expected_status = (
            "AUTOMATED"
            if all(entry["status"] == "AUTOMATED" for entry in entries)
            else "BLOCKED"
        )
        if release_check["status"] != expected_status:
            errors.append(
                f"{check_id} must be {expected_status} for current entry statuses"
            )

    acceptance_by_id = {
        entry["id"]: entry for entry in document["acceptanceCriteria"]
    }
    acceptance_010 = acceptance_by_id.get("AC-010")
    publishing_check = release_checks.get("FRESH_REPOSITORY_PUBLISHING")
    if acceptance_010 is not None and publishing_check is not None:
        publishing_status = (
            "AUTOMATED" if acceptance_010["status"] == "AUTOMATED" else "BLOCKED"
        )
        if publishing_check["status"] != publishing_status:
            errors.append(
                "FRESH_REPOSITORY_PUBLISHING must be "
                f"{publishing_status} for AC-010 status"
            )

    blocked = any(
        item["status"] == "BLOCKED"
        for label in ("requirements", "acceptanceCriteria", "releaseChecks")
        for item in document[label]
    )
    expected_state = "BLOCKED" if blocked else "READY"
    if document["releaseState"] != expected_state:
        errors.append(f"releaseState must be {expected_state} for current statuses")

    license_exists = any(
        (ROOT / name).is_file() for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")
    )
    license_checks = [
        item for item in document["releaseChecks"] if item["id"] == "PROJECT_LICENSE"
    ]
    if len(license_checks) != 1:
        errors.append("releaseChecks must contain PROJECT_LICENSE exactly once")
    elif license_exists == (license_checks[0]["status"] == "BLOCKED"):
        errors.append("PROJECT_LICENSE status does not match repository license state")
    return sorted(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        document = loads_strict_json(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, CanonicalJsonError) as error:
        print(f"Unable to read readiness JSON: {error}", file=sys.stderr)
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
