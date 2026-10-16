import json
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.validate_ucg import SCHEMA_PATH, validate_document


FIXTURES = Path(__file__).parent / "fixtures" / "ucg"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class UcgContractTests(unittest.TestCase):
    def setUp(self):
        self.valid_document = load_json(FIXTURES / "valid" / "spring-minimal.json")

    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    def test_valid_fixtures_satisfy_contract(self):
        for fixture in sorted((FIXTURES / "valid").glob("*.json")):
            with self.subTest(fixture=fixture.name):
                self.assertEqual([], validate_document(load_json(fixture)))

    def test_orphan_edge_fixture_is_rejected(self):
        errors = validate_document(load_json(FIXTURES / "invalid" / "orphan-edge.json"))

        self.assertTrue(
            any("references missing entity" in error for error in errors), errors
        )
        self.assertTrue(
            any("references missing evidence" in error for error in errors), errors
        )

    def test_unsupported_edge_kind_is_rejected_by_schema(self):
        document = deepcopy(self.valid_document)
        document["edges"][0]["type"] = "GUESSES"

        errors = validate_document(document)

        self.assertTrue(any("GUESSES" in error for error in errors), errors)

    def test_direct_claim_without_evidence_is_rejected(self):
        document = deepcopy(self.valid_document)
        document["entities"][1]["roles"][0]["evidenceIds"] = []

        errors = validate_document(document)

        self.assertTrue(
            any("must not be empty for DIRECT claims" in error for error in errors),
            errors,
        )

    def test_noncanonical_order_is_rejected(self):
        document = deepcopy(self.valid_document)
        document["entities"].reverse()

        errors = validate_document(document)

        self.assertIn("entities must use canonical order", errors)

    def test_non_normalized_source_path_is_rejected(self):
        document = deepcopy(self.valid_document)
        document["evidence"][0]["sourcePath"] = "src/../secrets.env"

        errors = validate_document(document)

        self.assertTrue(
            any("sourcePath must be a normalized relative path" in error for error in errors),
            errors,
        )

    def test_reversed_source_range_is_rejected(self):
        document = deepcopy(self.valid_document)
        document["evidence"][0]["startLine"] = 2

        errors = validate_document(document)

        self.assertTrue(any("endLine must be >= startLine" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
