import json
import tempfile
import unittest
from pathlib import Path

from metropogits.layout import generate_city
from metropogits.scanner import build_structural_ucg, scan_repository
from scripts.canonical_json import canonical_json_bytes
from scripts.validate_city import validate_document


FIXTURES = Path(__file__).parent / "fixtures"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class LayoutTests(unittest.TestCase):
    def test_spring_fixture_generates_valid_role_aware_scene(self):
        ucg = load_json(FIXTURES / "ucg" / "valid" / "spring-minimal.json")

        scene = generate_city(ucg)

        self.assertEqual([], validate_document(scene, ucg))
        archetypes = {
            building["entityId"]: building["archetype"]
            for building in scene["buildings"]
        }
        self.assertEqual(
            "STRUCTURED_WAREHOUSE",
            archetypes["demo:file:src/UserRepository.java"],
        )
        self.assertEqual(
            "SERVICE_OFFICE", archetypes["demo:file:src/UserService.java"]
        )
        self.assertEqual(1, len(scene["networks"]))
        self.assertEqual(
            ucg["edges"][0]["id"], scene["networks"][0]["edgeIds"][0]
        )

    def test_same_ucg_produces_identical_scene_bytes(self):
        ucg = load_json(FIXTURES / "ucg" / "valid" / "spring-minimal.json")

        first = canonical_json_bytes(generate_city(ucg, "minimal"))
        second = canonical_json_bytes(generate_city(ucg, "minimal"))

        self.assertEqual(first, second)

    def test_unknown_languages_receive_generic_buildings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "lib").mkdir()
            (root / "lib" / "worker.ex").write_text(
                "defmodule Worker do\nend", encoding="utf-8"
            )
            ucg = build_structural_ucg(scan_repository(root), "example/repo")

        scene = generate_city(ucg)

        self.assertEqual(1, len(scene["buildings"]))
        self.assertEqual("GENERIC_BUILDING", scene["buildings"][0]["archetype"])
        self.assertEqual([], scene["buildings"][0]["evidenceIds"])

    def test_small_change_preserves_existing_positions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "src" / "alpha.py").write_text("pass", encoding="utf-8")
            (root / "src" / "omega.py").write_text("pass", encoding="utf-8")
            before = generate_city(
                build_structural_ucg(scan_repository(root), "example/repo")
            )

            (root / "src" / "new_file.py").write_text("pass", encoding="utf-8")
            after = generate_city(
                build_structural_ucg(scan_repository(root), "example/repo")
            )

        before_districts = {
            item["id"]: (item["x"], item["z"]) for item in before["districts"]
        }
        after_districts = {
            item["id"]: (item["x"], item["z"]) for item in after["districts"]
        }
        self.assertEqual(before_districts, after_districts)
        before_buildings = {
            item["entityId"]: (item["x"], item["z"])
            for item in before["buildings"]
        }
        after_buildings = {
            item["entityId"]: (item["x"], item["z"])
            for item in after["buildings"]
        }
        for entity_id, position in before_buildings.items():
            self.assertEqual(position, after_buildings[entity_id])

    def test_top_level_file_uses_synthetic_root_district(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.go").write_text("package main", encoding="utf-8")
            ucg = build_structural_ucg(scan_repository(root), "example/repo")

        scene = generate_city(ucg)

        root_district = next(
            district for district in scene["districts"] if district["parentId"] is None
        )
        self.assertEqual(root_district["id"], scene["buildings"][0]["districtId"])


if __name__ == "__main__":
    unittest.main()
