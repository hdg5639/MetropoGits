from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.validate_catalog import SCHEMA_PATH, validate_document


ROOT = Path(__file__).parents[1]
CATALOG_ROOT = ROOT / "catalog" / "0.1.0"
CATALOG_PATH = CATALOG_ROOT / "catalog.json"
FIXTURE_ROOT = CATALOG_ROOT / "fixtures"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CatalogContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_json(CATALOG_PATH)

    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    def test_bundled_catalog_and_fixtures_are_valid(self):
        self.assertEqual([], validate_document(self.catalog, FIXTURE_ROOT))

    def test_specialized_semantics_require_direct_signatures(self):
        catalog = copy.deepcopy(self.catalog)
        rule = catalog["rules"][0]
        rule["match"]["codeSignatures"] = []
        rule["produces"]["usage"] = "DIRECT"
        rule["requiredEvidence"] = ["MANIFEST"]

        errors = validate_document(catalog)

        self.assertTrue(
            any("DIRECT requires a code/config signature" in error for error in errors),
            errors,
        )

    def test_declared_dependency_cannot_emit_specialized_semantics(self):
        catalog = copy.deepcopy(self.catalog)
        rule = catalog["rules"][0]
        rule["match"]["codeSignatures"] = []
        rule["produces"]["usage"] = "DECLARED"
        rule["requiredEvidence"] = ["MANIFEST"]

        errors = validate_document(catalog)

        self.assertTrue(
            any("DECLARED rules may only emit technology" in error for error in errors),
            errors,
        )

    def test_pattern_package_coordinate_is_rejected(self):
        catalog = copy.deepcopy(self.catalog)
        catalog["rules"][0]["match"]["packageCoordinates"] = [
            "org.springframework:*"
        ]

        errors = validate_document(catalog)

        self.assertTrue(
            any("packageCoordinates[0]" in error for error in errors), errors
        )

    def test_negative_fixture_that_matches_is_rejected(self):
        catalog = copy.deepcopy(self.catalog)
        catalog["rules"][0]["negativePredicates"] = []
        with tempfile.TemporaryDirectory() as temporary:
            fixtures = Path(temporary)
            target = fixtures / "spring"
            target.mkdir()
            (target / "service.json").write_text(
                (FIXTURE_ROOT / "spring" / "service.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            (target / "service-lookalike.json").write_text(
                (FIXTURE_ROOT / "spring" / "service.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            errors = validate_document(catalog, fixtures)

        self.assertTrue(
            any("unexpectedly matches" in error for error in errors), errors
        )

    def test_missing_fixture_is_rejected(self):
        catalog = copy.deepcopy(self.catalog)
        catalog["rules"][0]["fixtures"]["positive"] = ["missing/example"]

        errors = validate_document(catalog, FIXTURE_ROOT)

        self.assertTrue(any("cannot be loaded" in error for error in errors), errors)

    def test_module_cli_validates_catalog_with_sibling_fixtures(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "metropogits",
                "validate",
                "--input",
                str(CATALOG_PATH),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("Valid catalog/0.1 document", completed.stdout)


if __name__ == "__main__":
    unittest.main()
