from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.canonical_json import loads_strict_json
from scripts.validate_release_readiness import (
    EXPECTED_ACCEPTANCE,
    EXPECTED_REQUIREMENTS,
    SCHEMA_PATH,
    validate_document,
)


ROOT = Path(__file__).parents[1]
READINESS_PATH = ROOT / "release" / "readiness.json"


def readiness_document() -> dict:
    return loads_strict_json(READINESS_PATH.read_text(encoding="utf-8"))


class ReleaseReadinessTests(unittest.TestCase):
    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(
            json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        )

    def test_readiness_maps_every_p0_requirement_and_required_acceptance(self):
        document = readiness_document()

        self.assertEqual([], validate_document(document))
        self.assertEqual(
            EXPECTED_REQUIREMENTS,
            {item["id"] for item in document["requirements"]},
        )
        self.assertEqual(
            EXPECTED_ACCEPTANCE,
            {item["id"] for item in document["acceptanceCriteria"]},
        )
        self.assertTrue(
            all(item["status"] == "AUTOMATED" for item in document["requirements"])
        )
        self.assertTrue(
            all(
                item["status"] == "AUTOMATED"
                for item in document["acceptanceCriteria"]
            )
        )

    def test_missing_test_selector_is_rejected(self):
        document = readiness_document()
        document["requirements"][0]["evidence"] = [
            "tests/test_scanner.py::ScannerTests::test_missing"
        ]

        errors = validate_document(document)

        self.assertTrue(any("test does not exist" in error for error in errors), errors)

    def test_release_state_tracks_blockers(self):
        document = readiness_document()
        document["releaseState"] = "READY"

        errors = validate_document(document)

        self.assertIn("releaseState must be BLOCKED for current statuses", errors)

    def test_current_release_blockers_are_explicit(self):
        document = readiness_document()
        blocked = [
            item
            for item in document["releaseChecks"]
            if item["status"] == "BLOCKED"
        ]

        self.assertEqual(
            ["DECISION_COMPLIANCE", "PROJECT_LICENSE"],
            [item["id"] for item in blocked],
        )
        self.assertTrue(all(item["blocker"] for item in blocked))

    def test_noncanonical_and_unsafe_evidence_is_rejected(self):
        document = copy.deepcopy(readiness_document())
        document["requirements"][0]["evidence"] = ["../outside.py"]

        errors = validate_document(document)

        self.assertTrue(any("unsafe path" in error for error in errors), errors)

    def test_cli_validates_readiness_document(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "metropogits",
                "validate",
                "--input",
                str(READINESS_PATH),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("Valid release-readiness/0.1 document", completed.stdout)


if __name__ == "__main__":
    unittest.main()
