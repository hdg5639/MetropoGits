#!/usr/bin/env python3
"""Validate a declarative MetropoGits technology catalog and its fixtures."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

if __package__:
    from .canonical_json import CanonicalJsonError, loads_strict_json
else:
    from canonical_json import CanonicalJsonError, loads_strict_json


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "catalog-0.1.schema.json"
FIXTURE_SCHEMA_VERSION = "catalog-fixture/0.1"
FACT_KINDS = frozenset(
    {"ANNOTATION", "AST", "CALL", "CONFIG", "IMPORT", "INHERITANCE", "MANIFEST"}
)
DIRECT_EVIDENCE = frozenset(
    {"ANNOTATION", "AST", "CALL", "CONFIG", "IMPORT", "INHERITANCE"}
)
PATTERN_META = re.compile(r"[\*?\[\]{}()|^$+]")


def _json_path(parts: list[Any]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _check_sorted(errors: list[str], label: str, values: list[Any], key: Any) -> None:
    if values != sorted(values, key=key):
        errors.append(f"{label} must use canonical order")


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _required_fact_pairs(rule: dict[str, Any]) -> set[tuple[str, str]]:
    match = rule["match"]
    required = {("MANIFEST", value) for value in match["packageCoordinates"]}
    required.update(
        (signature["kind"], signature["value"]) for signature in match["codeSignatures"]
    )
    required.update(
        ("CONFIG", f"{signature['key']}={signature['value']}")
        for signature in match["configSignatures"]
    )
    return required


def _rule_matches(rule: dict[str, Any], facts: set[tuple[str, str]]) -> bool:
    if not _required_fact_pairs(rule).issubset(facts):
        return False
    blocked = {
        (predicate["kind"], predicate["value"])
        for predicate in rule["negativePredicates"]
    }
    return facts.isdisjoint(blocked)


def _validate_fixture_document(
    document: Any, label: str
) -> tuple[list[str], set[tuple[str, str]]]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return [f"{label}: root must be an object"], set()
    allowed = {"schemaVersion", "facts"}
    unknown = sorted(set(document) - allowed)
    if unknown:
        errors.append(f"{label}: unknown fields: {', '.join(unknown)}")
    if document.get("schemaVersion") != FIXTURE_SCHEMA_VERSION:
        errors.append(f"{label}.schemaVersion must be {FIXTURE_SCHEMA_VERSION!r}")
    raw_facts = document.get("facts")
    if not isinstance(raw_facts, list) or not raw_facts:
        errors.append(f"{label}.facts must be a non-empty array")
        return errors, set()
    facts: list[tuple[str, str]] = []
    for index, fact in enumerate(raw_facts):
        fact_label = f"{label}.facts[{index}]"
        if not isinstance(fact, dict) or set(fact) != {"kind", "value"}:
            errors.append(f"{fact_label} must contain only kind and value")
            continue
        kind = fact["kind"]
        value = fact["value"]
        if kind not in FACT_KINDS:
            errors.append(f"{fact_label}.kind is unsupported")
        if not isinstance(value, str) or not value or len(value) > 240:
            errors.append(f"{fact_label}.value must be 1..240 characters")
        elif PATTERN_META.search(value):
            errors.append(f"{fact_label}.value must be an exact literal")
        if kind in FACT_KINDS and isinstance(value, str) and value:
            facts.append((kind, value))
    if len(set(facts)) != len(facts):
        errors.append(f"{label}.facts must be unique")
    if facts != sorted(facts):
        errors.append(f"{label}.facts must use canonical order")
    return errors, set(facts)


def _fixture_path(root: Path, fixture_id: str) -> Path:
    parts = fixture_id.split("/")
    candidate = root.joinpath(*parts[:-1], f"{parts[-1]}.json")
    resolved_root = root.resolve(strict=False)
    resolved_candidate = candidate.resolve(strict=False)
    if (
        resolved_candidate == resolved_root
        or resolved_root not in resolved_candidate.parents
    ):
        raise ValueError("fixture path escapes the fixture root")
    return candidate


def _validate_fixtures(
    rule: dict[str, Any], fixture_root: Path, errors: list[str]
) -> None:
    for outcome in ("positive", "negative"):
        for fixture_id in rule["fixtures"][outcome]:
            label = f"fixture {fixture_id!r}"
            try:
                path = _fixture_path(fixture_root, fixture_id)
                document = loads_strict_json(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, CanonicalJsonError, ValueError) as error:
                errors.append(f"{label} cannot be loaded: {error}")
                continue
            fixture_errors, facts = _validate_fixture_document(document, label)
            errors.extend(fixture_errors)
            if fixture_errors:
                continue
            matched = _rule_matches(rule, facts)
            if outcome == "positive" and not matched:
                errors.append(f"{label} does not match rule {rule['id']!r}")
            if outcome == "negative" and matched:
                errors.append(
                    f"{label} unexpectedly matches rule {rule['id']!r}; "
                    "add verified evidence or a negative predicate"
                )


def validate_document(document: Any, fixture_root: Path | None = None) -> list[str]:
    """Return deterministic schema, policy, and optional fixture errors."""

    schema_path = (
        (ROOT / "schemas" / "catalog-0.2.schema.json")
        if isinstance(document, dict) and document.get("schemaVersion") == "catalog/0.2"
        else SCHEMA_PATH
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
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

    rules = document["rules"]
    rule_ids = [rule["id"] for rule in rules]
    duplicates = sorted(_duplicates(rule_ids))
    if duplicates:
        errors.append(f"rule IDs must be unique: {', '.join(duplicates)}")
    _check_sorted(errors, "rules", rules, key=lambda rule: rule["id"])

    for index, rule in enumerate(rules):
        label = f"$.rules[{index}]"
        match = rule["match"]
        produces = rule["produces"]
        required_evidence = rule["requiredEvidence"]
        fixtures = rule["fixtures"]

        _check_sorted(
            errors,
            f"{label}.match.packageCoordinates",
            match["packageCoordinates"],
            key=lambda value: value,
        )
        _check_sorted(
            errors,
            f"{label}.match.codeSignatures",
            match["codeSignatures"],
            key=lambda item: (item["kind"], item["value"]),
        )
        _check_sorted(
            errors,
            f"{label}.match.configSignatures",
            match["configSignatures"],
            key=lambda item: (item["key"], item["value"]),
        )
        _check_sorted(
            errors,
            f"{label}.negativePredicates",
            rule["negativePredicates"],
            key=lambda item: (item["kind"], item["value"]),
        )
        for field in ("capabilities", "roles"):
            _check_sorted(
                errors,
                f"{label}.produces.{field}",
                produces[field],
                key=lambda value: value,
            )
        _check_sorted(
            errors,
            f"{label}.requiredEvidence",
            required_evidence,
            key=lambda value: value,
        )
        _check_sorted(
            errors,
            f"{label}.references",
            rule["references"],
            key=lambda item: (item["url"], item["title"], item["license"]),
        )
        for outcome in ("negative", "positive"):
            _check_sorted(
                errors,
                f"{label}.fixtures.{outcome}",
                fixtures[outcome],
                key=lambda value: value,
            )
        overlap = sorted(set(fixtures["positive"]) & set(fixtures["negative"]))
        if overlap:
            errors.append(
                f"{label}.fixtures positive and negative sets overlap: "
                + ", ".join(overlap)
            )

        evidence = set(required_evidence)
        signature_evidence = {item["kind"] for item in match["codeSignatures"]}
        if match["packageCoordinates"] and "MANIFEST" not in evidence:
            errors.append(
                f"{label}.requiredEvidence must include MANIFEST for package coordinates"
            )
        missing_code_evidence = sorted(signature_evidence - evidence)
        if missing_code_evidence:
            errors.append(
                f"{label}.requiredEvidence is missing code signature kinds: "
                + ", ".join(missing_code_evidence)
            )
        if match["configSignatures"] and "CONFIG" not in evidence:
            errors.append(
                f"{label}.requiredEvidence must include CONFIG for config signatures"
            )

        has_direct_signature = bool(
            match["codeSignatures"] or match["configSignatures"]
        )
        if produces["usage"] == "DIRECT" and (
            not has_direct_signature or not (evidence & DIRECT_EVIDENCE)
        ):
            errors.append(
                f"{label}.produces.usage DIRECT requires a code/config signature "
                "and matching direct evidence"
            )
        if produces["usage"] == "DECLARED" and (
            produces["capabilities"]
            or produces["roles"]
            or produces["archetypeFamily"] != "LIBRARY"
        ):
            errors.append(
                f"{label}.produces DECLARED rules may only emit technology and "
                "the LIBRARY archetype"
            )

        coordinates = match["packageCoordinates"]
        if rule["ecosystem"] == "maven" and any(
            coordinate.count(":") != 1 for coordinate in coordinates
        ):
            errors.append(
                f"{label}.match.packageCoordinates must use exact group:artifact values"
            )
        if rule["ecosystem"] == "npm" and any(
            ":" in coordinate or coordinate.startswith("/")
            for coordinate in coordinates
        ):
            errors.append(
                f"{label}.match.packageCoordinates must use exact npm package names"
            )

        if fixture_root is not None:
            _validate_fixtures(rule, fixture_root, errors)

    return sorted(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="catalog JSON file to validate")
    parser.add_argument(
        "--fixtures",
        type=Path,
        help="fixture root (defaults to a fixtures directory beside the catalog)",
    )
    args = parser.parse_args()

    try:
        document = loads_strict_json(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, CanonicalJsonError) as error:
        print(f"Unable to read catalog JSON: {error}", file=sys.stderr)
        return 2

    fixture_root = args.fixtures or args.input.parent / "fixtures"
    errors = validate_document(document, fixture_root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"Valid catalog document: {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
