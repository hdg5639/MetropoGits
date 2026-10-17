import json
import tempfile
import unittest
from pathlib import Path

from metropogits.layout import generate_city
from metropogits.scanner import (
    ScanResult,
    ScannedFile,
    build_structural_ucg,
    scan_repository,
)
from scripts.canonical_json import canonical_json_bytes
from scripts.stable_ids import make_edge_id
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

    def test_edges_between_districts_are_aggregated_without_losing_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "api").mkdir()
            (root / "data").mkdir()
            for name in ("First.py", "Second.py", "Third.py"):
                (root / "api" / name).write_text("pass", encoding="utf-8")
            (root / "data" / "Store.py").write_text("pass", encoding="utf-8")
            ucg = build_structural_ucg(scan_repository(root), "example/repo")

        files = {entity["path"]: entity["id"] for entity in ucg["entities"]}
        target_id = files["data/Store.py"]
        edge_ids: list[str] = []
        for index, source_path in enumerate(
            ("api/First.py", "api/Second.py", "api/Third.py"), start=1
        ):
            evidence_id = f"aggregate-evidence-{index}"
            edge_id = make_edge_id(
                files[source_path], "REFERENCES", target_id, "aggregate-fixture"
            )
            edge_ids.append(edge_id)
            ucg["evidence"].append(
                {
                    "evidenceId": evidence_id,
                    "extractor": "acceptance-fixture",
                    "kind": "AST",
                    "sourcePath": source_path,
                    "summary": "Verified fixture reference",
                }
            )
            ucg["edges"].append(
                {
                    "confidence": "RESOLVED",
                    "evidenceIds": [evidence_id],
                    "from": files[source_path],
                    "id": edge_id,
                    "to": target_id,
                    "type": "REFERENCES",
                }
            )
        ucg["edges"].sort(key=lambda item: item["id"])
        ucg["evidence"].sort(key=lambda item: item["evidenceId"])

        scene = generate_city(ucg)

        self.assertEqual(1, len(scene["networks"]))
        self.assertEqual(sorted(edge_ids), scene["networks"][0]["edgeIds"])

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

    def test_large_directories_expand_in_bounded_non_overlapping_pages(self):
        for file_count in (65, 100, 1_000):
            with self.subTest(file_count=file_count):
                scan = ScanResult(
                    files=tuple(
                        ScannedFile(
                            path=f"src/File{index:04}.py",
                            language="python",
                            size_bytes=4,
                        )
                        for index in range(file_count)
                    ),
                    diagnostics=(),
                )
                ucg = build_structural_ucg(scan, "example/large")

                scene = generate_city(ucg)

                self.assertEqual([], validate_document(scene, ucg))
                district = next(
                    item
                    for item in scene["districts"]
                    if item["id"] == "example/large:directory:src"
                )
                expected_pages = (file_count + 63) // 64
                self.assertEqual(64, district["width"])
                self.assertEqual(expected_pages * 64, district["depth"])
                positions = {
                    (building["x"], building["z"])
                    for building in scene["buildings"]
                }
                self.assertEqual(file_count, len(positions))
                for building in scene["buildings"]:
                    self.assertGreaterEqual(building["x"], district["x"])
                    self.assertGreaterEqual(building["z"], district["z"])
                    self.assertLessEqual(
                        building["x"] + building["width"],
                        district["x"] + district["width"],
                    )
                    self.assertLessEqual(
                        building["z"] + building["depth"],
                        district["z"] + district["depth"],
                    )


if __name__ == "__main__":
    unittest.main()
