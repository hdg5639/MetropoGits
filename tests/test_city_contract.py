import json
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.validate_city import SCHEMA_PATHS, ucg_digest, validate_document


FIXTURES = Path(__file__).parent / "fixtures"
UCG_FIXTURE = FIXTURES / "ucg" / "valid" / "spring-minimal.json"
VALID_SCENE = FIXTURES / "city" / "valid" / "spring-minimal.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class CityContractTests(unittest.TestCase):
    def setUp(self):
        self.ucg = load_json(UCG_FIXTURE)
        self.scene = load_json(VALID_SCENE)

    def test_schema_is_valid_draft_2020_12(self):
        for schema_path in SCHEMA_PATHS.values():
            Draft202012Validator.check_schema(load_json(schema_path))

    def test_valid_fixture_satisfies_contract(self):
        self.assertEqual([], validate_document(self.scene, self.ucg))

    def test_digest_uses_canonical_ucg_content(self):
        reordered = dict(reversed(list(self.ucg.items())))

        self.assertEqual(ucg_digest(self.ucg), ucg_digest(reordered))
        self.assertEqual(self.scene["ucgDigest"], ucg_digest(self.ucg))

    def test_digest_mismatch_is_rejected(self):
        scene = deepcopy(self.scene)
        scene["ucgDigest"] = "sha256:" + "0" * 64

        errors = validate_document(scene, self.ucg)

        self.assertTrue(any("does not match UCG content" in error for error in errors))

    def test_orphan_references_are_rejected(self):
        scene = load_json(FIXTURES / "city" / "invalid" / "orphan-references.json")

        errors = validate_document(scene, self.ucg)

        self.assertTrue(any("missing UCG entity" in error for error in errors), errors)
        self.assertTrue(any("missing district" in error for error in errors), errors)
        self.assertTrue(any("missing UCG evidence" in error for error in errors), errors)
        self.assertTrue(any("missing UCG edge" in error for error in errors), errors)

    def test_district_cycle_is_rejected(self):
        scene = deepcopy(self.scene)
        scene["districts"] = [
            {
                "depth": 10,
                "id": "demo:directory:a",
                "parentId": "demo:directory:b",
                "width": 10,
                "x": 0,
                "z": 0,
            },
            {
                "depth": 10,
                "id": "demo:directory:b",
                "parentId": "demo:directory:a",
                "width": 10,
                "x": 10,
                "z": 0,
            },
        ]
        scene["buildings"] = []

        errors = validate_document(scene, self.ucg)

        self.assertTrue(any("contains a cycle" in error for error in errors), errors)

    def test_semantic_decoration_is_rejected(self):
        scene = deepcopy(self.scene)
        scene["decorations"] = [{"kind": "TREE", "semantic": True}]

        errors = validate_document(scene, self.ucg)

        self.assertTrue(any("False was expected" in error for error in errors), errors)

    def test_noncanonical_building_order_is_rejected(self):
        scene = deepcopy(self.scene)
        scene["buildings"].reverse()

        errors = validate_document(scene, self.ucg)

        self.assertIn("buildings must use canonical order", errors)

    def test_building_outside_its_district_is_rejected(self):
        scene = deepcopy(self.scene)
        district = scene["districts"][0]
        scene["buildings"][0]["x"] = district["x"] + district["width"]

        errors = validate_document(scene, self.ucg)

        self.assertTrue(any("lies outside district" in error for error in errors))

    def test_overlapping_buildings_are_rejected(self):
        scene = deepcopy(self.scene)
        scene["buildings"][1]["x"] = scene["buildings"][0]["x"]
        scene["buildings"][1]["z"] = scene["buildings"][0]["z"]

        errors = validate_document(scene, self.ucg)

        self.assertTrue(any("overlap in district" in error for error in errors))

    def test_child_district_outside_parent_is_rejected(self):
        scene = deepcopy(self.scene)
        parent = scene["districts"][0]
        scene["districts"].append(
            {
                "depth": 10,
                "id": "demo:directory:src/child",
                "parentId": parent["id"],
                "width": 10,
                "x": parent["x"] + parent["width"],
                "z": parent["z"],
            }
        )
        scene["districts"].sort(key=lambda item: item["id"])

        errors = validate_document(scene, self.ucg)

        self.assertTrue(any("lies outside parent" in error for error in errors))

    def test_overlapping_sibling_districts_are_rejected(self):
        scene = deepcopy(self.scene)
        parent = scene["districts"][0]
        for name in ("alpha", "beta"):
            scene["districts"].append(
                {
                    "depth": 10,
                    "id": f"demo:directory:src/{name}",
                    "parentId": parent["id"],
                    "width": 10,
                    "x": parent["x"] + 1,
                    "z": parent["z"] + 1,
                }
            )
        scene["districts"].sort(key=lambda item: item["id"])

        errors = validate_document(scene, self.ucg)

        self.assertTrue(any("sibling districts" in error for error in errors))

    def test_polygon_scene_allows_overlapping_bounds_with_disjoint_land(self):
        scene = {
            "buildings": [],
            "decorations": [],
            "districts": [
                {
                    "depth": 14,
                    "footprint": [{"depth": 14, "width": 21, "x": 0, "z": 0}],
                    "id": "root",
                    "parentId": None,
                    "width": 21,
                    "x": 0,
                    "z": 0,
                },
                {
                    "depth": 14,
                    "footprint": [
                        {"depth": 7, "width": 14, "x": 0, "z": 0},
                        {"depth": 7, "width": 7, "x": 0, "z": 7},
                    ],
                    "id": "root/alpha",
                    "parentId": "root",
                    "width": 14,
                    "x": 0,
                    "z": 0,
                },
                {
                    "depth": 14,
                    "footprint": [
                        {"depth": 7, "width": 7, "x": 14, "z": 0},
                        {"depth": 7, "width": 14, "x": 7, "z": 7},
                    ],
                    "id": "root/beta",
                    "parentId": "root",
                    "width": 14,
                    "x": 7,
                    "z": 0,
                },
            ],
            "layoutAlgorithm": "hierarchical-paged/1.11",
            "networks": [],
            "schemaVersion": "city/0.2",
            "theme": "minimal",
            "ucgDigest": ucg_digest(self.ucg),
        }

        self.assertEqual([], validate_document(scene, self.ucg))

        overlapping = deepcopy(scene)
        overlapping["districts"][2]["footprint"][0]["x"] = 7
        errors = validate_document(overlapping, self.ucg)

        self.assertTrue(any("footprints" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
