import copy
import hashlib
import json
import unittest
import xml.etree.ElementTree as element_tree
from pathlib import Path

from metropogits.layout import generate_city
from metropogits.preview import (
    PreviewError,
    _district_label_candidates,
    _major_district_ids,
    render_preview,
)
from metropogits.scanner import ScanResult, ScannedFile, build_structural_ucg
from scripts.canonical_json import canonical_json_bytes, loads_strict_json


FIXTURES = Path(__file__).parent / "fixtures"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.ucg = load_json(FIXTURES / "ucg" / "valid" / "spring-minimal.json")
        self.scene = generate_city(self.ucg)

    def test_preview_is_deterministic_valid_svg(self):
        first = render_preview(self.scene, self.ucg)
        second = render_preview(self.scene, self.ucg)

        self.assertEqual(first, second)
        strict_scene = loads_strict_json(canonical_json_bytes(self.scene).decode())
        self.assertEqual(first, render_preview(strict_scene, self.ucg))
        root = element_tree.fromstring(first)
        self.assertEqual("{http://www.w3.org/2000/svg}svg", root.tag)
        self.assertEqual(
            # Same minimal geometry; derived routing metadata now records 0.2.
            "58073bbebb5fdf14bf90552cad54f6014ef6dba7a3a54ce5d2c92b064cbc48e5",
            hashlib.sha256(first).hexdigest(),
        )

    def test_preview_contains_buildings_districts_and_networks(self):
        preview = render_preview(self.scene, self.ucg).decode("utf-8")

        self.assertIn('id="districts"', preview)
        self.assertIn('id="buildings"', preview)
        self.assertIn('id="networks"', preview)

    def test_preview_marks_each_building_with_an_archetype_roof_form(self):
        preview = render_preview(self.scene, self.ucg).decode("utf-8")

        self.assertEqual(
            len(self.scene["buildings"]), preview.count("data-roof-form=")
        )
        self.assertIn('data-roof-form="SERVICE_OFFICE"', preview)
        self.assertIn('data-roof-form="STRUCTURED_WAREHOUSE"', preview)

    def test_preview_distinguishes_visual_blocks_from_evidence_roads(self):
        preview = render_preview(self.scene, self.ucg).decode("utf-8")
        occupied_districts = {
            building["districtId"] for building in self.scene["buildings"]
        }

        self.assertIn('id="civic-blocks"', preview)
        self.assertIn('id="structural-streets"', preview)
        self.assertIn("Visual street infrastructure; not dependency evidence", preview)
        self.assertIn("Visual civic block; no dependency claim", preview)
        self.assertEqual(
            len(occupied_districts), preview.count("data-civic-district=")
        )
        self.assertEqual(
            len(self.scene["networks"]), preview.count("data-network-id=")
        )
        self.assertIn("SERVICE_OFFICE", preview)
        self.assertIn("STRUCTURED_WAREHOUSE", preview)
        self.assertIn(self.ucg["edges"][0]["id"], preview)

    def test_preview_omits_redundant_empty_directory_boundaries(self):
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
        ucg = build_structural_ucg(scan, "example/compact-preview")
        scene = generate_city(ucg)

        preview = render_preview(scene, ucg).decode("utf-8")

        self.assertEqual(1, preview.count("data-district-id="))
        self.assertIn(">service</text>", preview)
        self.assertIn("src/main/java/com/example/service", preview)

    def test_square_city_is_centered_in_a_wide_preview(self):
        scan = ScanResult(
            files=(
                ScannedFile(
                    path="src/App.py",
                    language="python",
                    size_bytes=4,
                ),
            ),
            diagnostics=(),
        )
        ucg = build_structural_ucg(scan, "example/centered-preview")
        scene = generate_city(ucg)

        preview = element_tree.fromstring(render_preview(scene, ucg))
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        district_group = preview.find(".//svg:g[@id='districts']", namespace)
        district_rect = district_group.find("svg:g/svg:rect", namespace)

        self.assertGreater(float(district_rect.attrib["x"]), 250)
        self.assertLess(float(district_rect.attrib["x"]), 400)

    def test_overlapping_district_labels_prefer_populated_deeper_district(self):
        scene = {
            "buildings": [{"districtId": "child"}],
            "districts": [
                {
                    "depth": 30,
                    "id": "root",
                    "parentId": None,
                    "width": 30,
                    "x": 0,
                    "z": 0,
                },
                {
                    "depth": 30,
                    "id": "child",
                    "parentId": "root",
                    "width": 30,
                    "x": 0,
                    "z": 0,
                },
            ],
        }

        selected = _district_label_candidates(
            scene,
            {"child", "root"},
            {"child": "nested/child"},
            {"root"},
            "repository",
            lambda x, z: (float(x) + 100, float(z) + 100),
            500,
            500,
        )

        self.assertEqual({"child": "ch…"}, selected)

    def test_major_districts_follow_large_structural_branches(self):
        districts = [
            {"id": "root", "parentId": None},
            {"id": "backend", "parentId": "root"},
            {"id": "frontend", "parentId": "root"},
            {"id": "tiny", "parentId": "root"},
            {"id": "auth", "parentId": "backend"},
            {"id": "ops", "parentId": "backend"},
            {"id": "portal", "parentId": "frontend"},
        ]
        buildings = [
            {"districtId": district_id, "entityId": f"{district_id}-{index}"}
            for district_id, count in (("auth", 80), ("ops", 200), ("portal", 100))
            for index in range(count)
        ] + [{"districtId": "tiny", "entityId": "tiny-0"}]

        self.assertEqual(
            {"auth", "ops", "portal"},
            _major_district_ids({"buildings": buildings, "districts": districts}),
        )

    def test_preview_marks_major_structural_districts(self):
        scan = ScanResult(
            files=(
                ScannedFile(path="api/App.py", language="python", size_bytes=4),
                ScannedFile(path="web/App.py", language="python", size_bytes=4),
            ),
            diagnostics=(),
        )
        ucg = build_structural_ucg(scan, "example/major-districts")
        scene = generate_city(ucg)

        preview = render_preview(scene, ucg).decode("utf-8")

        self.assertIn('id="major-districts"', preview)
        self.assertEqual(2, preview.count("Major structural district"))

    def test_untrusted_labels_are_xml_escaped(self):
        ucg = copy.deepcopy(self.ucg)
        ucg["repository"]["id"] = "demo<unsafe>&\u0001"
        scene = generate_city(ucg)

        preview = render_preview(scene, ucg).decode("utf-8")

        element_tree.fromstring(preview)
        self.assertNotIn("demo<unsafe>", preview)
        self.assertNotIn("\u0001", preview)
        self.assertIn("demo&lt;unsafe&gt;&amp;�", preview)

    def test_preview_has_no_script_or_webgl_dependency(self):
        preview = render_preview(self.scene, self.ucg).decode("utf-8").lower()

        self.assertNotIn("<script", preview)
        self.assertNotIn("webgl", preview)
        self.assertNotIn("foreignobject", preview)

    def test_invalid_scene_is_rejected(self):
        scene = copy.deepcopy(self.scene)
        scene["buildings"][0]["entityId"] = "missing"

        with self.assertRaisesRegex(PreviewError, "invalid City Scene"):
            render_preview(scene, self.ucg)

    def test_dimensions_are_bounded(self):
        with self.assertRaisesRegex(PreviewError, "width must be between"):
            render_preview(self.scene, self.ucg, width=100)
        with self.assertRaisesRegex(PreviewError, "height must be between"):
            render_preview(self.scene, self.ucg, height=5000)

    def test_street_surfaces_and_civic_plots_stay_below_header(self):
        from metropogits.cli import analyze_repository

        graph = analyze_repository(FIXTURES / "repositories" / "spring-positive")
        scene = generate_city(graph)
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        root = element_tree.fromstring(render_preview(scene, graph))
        world = root.find("svg:g[@id='scene-content']", namespace)
        self.assertEqual("url(#scene-clip)", world.attrib["clip-path"])
        for rect in world.findall(".//svg:rect", namespace):
            self.assertGreaterEqual(float(rect.attrib["y"]), 64)
            self.assertLessEqual(float(rect.attrib["y"]) + float(rect.attrib["height"]), 675.01)


if __name__ == "__main__":
    unittest.main()
