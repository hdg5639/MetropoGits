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

    def test_previous_scene_hint_preserves_colliding_file_positions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "src").mkdir()
            for index in range(30):
                (root / "src" / f"m{index:03}.py").write_text(
                    "pass", encoding="utf-8"
                )
            before_graph = build_structural_ucg(
                scan_repository(root), "example/hint"
            )
            before = generate_city(before_graph)
            (root / "src" / "0000.py").write_text("pass", encoding="utf-8")
            after_graph = build_structural_ucg(
                scan_repository(root), "example/hint"
            )

            cold = generate_city(after_graph)
            diagnostics: list[dict] = []
            hinted = generate_city(
                after_graph, previous_scene=before, diagnostics=diagnostics
            )

        before_positions = {
            item["entityId"]: (item["x"], item["z"])
            for item in before["buildings"]
        }
        cold_positions = {
            item["entityId"]: (item["x"], item["z"])
            for item in cold["buildings"]
        }
        hinted_positions = {
            item["entityId"]: (item["x"], item["z"])
            for item in hinted["buildings"]
        }
        cold_moved = {
            entity_id
            for entity_id, position in before_positions.items()
            if cold_positions[entity_id] != position
        }
        self.assertGreater(len(cold_moved), 0)
        self.assertLess(len(cold_moved), len(before_positions))
        before_district_ids = {item["id"] for item in before["districts"]}
        self.assertEqual(
            {
                item["id"]: (item["x"], item["z"])
                for item in before["districts"]
            },
            {
                item["id"]: (item["x"], item["z"])
                for item in cold["districts"]
                if item["id"] in before_district_ids
            },
        )
        self.assertEqual(
            before_positions,
            {
                entity_id: hinted_positions[entity_id]
                for entity_id in before_positions
            },
        )
        self.assertEqual("LAYOUT_HINT_APPLIED", diagnostics[-1]["code"])
        self.assertIn("moved 0 district(s) and 0 building(s)", diagnostics[-1]["message"])

    def test_previous_scene_hint_preserves_existing_district_subtrees(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(10):
                directory = root / f"m{index:03}"
                directory.mkdir()
                (directory / "x.py").write_text("pass", encoding="utf-8")
            before_graph = build_structural_ucg(
                scan_repository(root), "example/district-hint"
            )
            before = generate_city(before_graph)
            added = root / "0000"
            added.mkdir()
            (added / "x.py").write_text("pass", encoding="utf-8")
            after_graph = build_structural_ucg(
                scan_repository(root), "example/district-hint"
            )

            cold = generate_city(after_graph)
            diagnostics: list[dict] = []
            hinted = generate_city(
                after_graph, previous_scene=before, diagnostics=diagnostics
            )

        for collection, identity in (("districts", "id"), ("buildings", "entityId")):
            before_positions = {
                item[identity]: (item["x"], item["z"])
                for item in before[collection]
            }
            cold_positions = {
                item[identity]: (item["x"], item["z"])
                for item in cold[collection]
            }
            hinted_positions = {
                item[identity]: (item["x"], item["z"])
                for item in hinted[collection]
            }
            if collection == "districts":
                self.assertTrue(
                    any(
                        cold_positions[item_id] != position
                        for item_id, position in before_positions.items()
                    )
                )
            self.assertEqual(
                before_positions,
                {
                    item_id: hinted_positions[item_id]
                    for item_id in before_positions
                },
            )
        self.assertEqual("LAYOUT_HINT_APPLIED", diagnostics[-1]["code"])

    def test_malformed_previous_scene_is_ignored_deterministically(self):
        ucg = load_json(FIXTURES / "ucg" / "valid" / "spring-minimal.json")
        cold = generate_city(ucg)
        diagnostics: list[dict] = []

        hinted = generate_city(
            ucg,
            previous_scene={"schemaVersion": "city/invalid"},
            diagnostics=diagnostics,
        )

        self.assertEqual(canonical_json_bytes(cold), canonical_json_bytes(hinted))
        self.assertEqual("LAYOUT_HINT_IGNORED", diagnostics[-1]["code"])
        self.assertEqual("WARNING", diagnostics[-1]["severity"])

    def test_previous_layout_versions_are_not_reused_as_hints(self):
        ucg = load_json(FIXTURES / "ucg" / "valid" / "spring-minimal.json")
        cold = generate_city(ucg)
        for version in (
            "hierarchical-paged/1.0",
            "hierarchical-paged/1.1",
            "hierarchical-paged/1.2",
            "hierarchical-paged/1.3",
        ):
            with self.subTest(version=version):
                previous = {**cold, "layoutAlgorithm": version}
                diagnostics: list[dict] = []

                hinted = generate_city(
                    ucg,
                    previous_scene=previous,
                    diagnostics=diagnostics,
                )

                self.assertEqual(
                    canonical_json_bytes(cold), canonical_json_bytes(hinted)
                )
                self.assertEqual("LAYOUT_HINT_IGNORED", diagnostics[-1]["code"])
                self.assertIn("algorithm family", diagnostics[-1]["message"])

    def test_layout_14_geometry_remains_eligible_as_a_hint(self):
        ucg = load_json(FIXTURES / "ucg" / "valid" / "spring-minimal.json")
        cold = generate_city(ucg)
        previous = {**cold, "layoutAlgorithm": "hierarchical-paged/1.4"}
        diagnostics: list[dict] = []

        hinted = generate_city(ucg, previous_scene=previous, diagnostics=diagnostics)

        self.assertEqual(canonical_json_bytes(cold), canonical_json_bytes(hinted))
        self.assertEqual("LAYOUT_HINT_APPLIED", diagnostics[-1]["code"])

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
        network = scene["networks"][0]
        self.assertEqual(sorted(edge_ids), network["edgeIds"])
        buildings = {item["entityId"]: item for item in scene["buildings"]}
        source_centers = [
            (
                buildings[files[path]]["x"] + buildings[files[path]]["width"] / 2,
                buildings[files[path]]["z"] + buildings[files[path]]["depth"] / 2,
            )
            for path in ("api/First.py", "api/Second.py", "api/Third.py")
        ]
        target = buildings[target_id]
        self.assertEqual(
            [
                sum(item[0] for item in source_centers) / len(source_centers),
                sum(item[1] for item in source_centers) / len(source_centers),
            ],
            network["path"][0],
        )
        self.assertEqual(
            [target["x"] + target["width"] / 2, target["z"] + target["depth"] / 2],
            network["path"][-1],
        )

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

    def test_directory_tree_is_spatially_nested_without_sibling_overlap(self):
        paths = (
            "src/App.py",
            "src/data/Repository.py",
            "src/service/Service.py",
            "src/service/internal/Helper.py",
            "tests/TestApp.py",
        )
        scan = ScanResult(
            files=tuple(
                ScannedFile(path=path, language="python", size_bytes=4)
                for path in paths
            ),
            diagnostics=(),
        )
        ucg = build_structural_ucg(scan, "example/nested")

        scene = generate_city(ucg)

        self.assertEqual("hierarchical-paged/1.5", scene["layoutAlgorithm"])
        self.assertEqual([], validate_document(scene, ucg))
        districts = {item["id"]: item for item in scene["districts"]}
        siblings: dict[str, list[dict]] = {}
        for district in scene["districts"]:
            parent_id = district["parentId"]
            if parent_id is None:
                continue
            parent = districts[parent_id]
            self.assertGreaterEqual(district["x"], parent["x"])
            self.assertGreaterEqual(district["z"], parent["z"])
            self.assertLessEqual(
                district["x"] + district["width"],
                parent["x"] + parent["width"],
            )
            self.assertLessEqual(
                district["z"] + district["depth"],
                parent["z"] + parent["depth"],
            )
            siblings.setdefault(parent_id, []).append(district)

        for group in siblings.values():
            for index, first in enumerate(group):
                for second in group[index + 1 :]:
                    overlaps = (
                        first["x"] < second["x"] + second["width"]
                        and second["x"] < first["x"] + first["width"]
                        and first["z"] < second["z"] + second["depth"]
                        and second["z"] < first["z"] + first["depth"]
                    )
                    self.assertFalse(overlaps)

    def test_buildings_fill_stable_cells_with_visible_separation(self):
        scan = ScanResult(
            files=tuple(
                ScannedFile(
                    path=f"src/File{index:02}.py",
                    language="python",
                    size_bytes=4,
                )
                for index in range(64)
            ),
            diagnostics=(),
        )
        ucg = build_structural_ucg(scan, "example/readable-buildings")

        scene = generate_city(ucg)

        self.assertTrue(
            all(
                item["width"] == 6
                and item["depth"] == 6
                and item["height"] >= 10
                for item in scene["buildings"]
            )
        )
        self.assertEqual([], validate_document(scene, ucg))

    def test_empty_directory_chains_share_a_compact_footprint(self):
        scan = ScanResult(
            files=(
                ScannedFile(
                    path="src/main/java/com/example/service/App.py",
                    language="python",
                    size_bytes=4,
                ),
            ),
            diagnostics=(),
        )
        ucg = build_structural_ucg(scan, "example/compact-chain")

        scene = generate_city(ucg)
        footprints = {
            (item["x"], item["z"], item["width"], item["depth"])
            for item in scene["districts"]
        }

        self.assertEqual(1, len(footprints))
        width, depth = next((width, depth) for _, _, width, depth in footprints)
        self.assertLessEqual(width, 64)
        self.assertLessEqual(depth, 64)
        self.assertEqual([], validate_document(scene, ucg))

    def test_sibling_districts_are_packed_into_a_bounded_grid(self):
        scan = ScanResult(
            files=tuple(
                ScannedFile(
                    path=f"package-{index:02}/App.py",
                    language="python",
                    size_bytes=4,
                )
                for index in range(16)
            ),
            diagnostics=(),
        )
        ucg = build_structural_ucg(scan, "example/compact-siblings")

        scene = generate_city(ucg)
        root = next(
            item for item in scene["districts"] if item["parentId"] is None
        )

        self.assertLessEqual(max(root["width"], root["depth"]), 400)
        self.assertLessEqual(
            max(root["width"], root["depth"])
            / min(root["width"], root["depth"]),
            1.5,
        )
        self.assertEqual([], validate_document(scene, ucg))

    def test_mixed_size_siblings_keep_a_balanced_parent_footprint(self):
        paths = [
            f"large/section-{index:02}/App.py" for index in range(12)
        ] + ["small-a/App.py", "small-b/App.py"]
        scan = ScanResult(
            files=tuple(
                ScannedFile(path=path, language="python", size_bytes=4)
                for path in paths
            ),
            diagnostics=(),
        )
        ucg = build_structural_ucg(scan, "example/mixed-size-siblings")

        scene = generate_city(ucg)
        root = next(
            item for item in scene["districts"] if item["parentId"] is None
        )

        self.assertLessEqual(
            max(root["width"], root["depth"])
            / min(root["width"], root["depth"]),
            1.5,
        )
        self.assertEqual([], validate_document(scene, ucg))

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
                self.assertLessEqual(district["width"], 64)
                self.assertLessEqual(district["depth"], expected_pages * 64)
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

    def test_sparse_district_uses_a_compact_cold_footprint(self):
        scan = ScanResult(
            files=(
                ScannedFile(path="src/Only.py", language="python", size_bytes=4),
            ),
            diagnostics=(),
        )
        ucg = build_structural_ucg(scan, "example/sparse")

        scene = generate_city(ucg)
        district = next(
            item
            for item in scene["districts"]
            if item["id"] == "example/sparse:directory:src"
        )
        building = scene["buildings"][0]

        self.assertEqual((24, 24), (district["width"], district["depth"]))
        self.assertEqual((6, 6), (building["x"], building["z"]))
        self.assertEqual([], validate_document(scene, ucg))


if __name__ == "__main__":
    unittest.main()
