import copy
import hashlib
import json
import unittest
import xml.etree.ElementTree as element_tree
from pathlib import Path

from metropogits.layout import generate_city
from metropogits.preview import PreviewError, render_preview
from metropogits.scanner import ScanResult, ScannedFile, build_structural_ucg


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
        root = element_tree.fromstring(first)
        self.assertEqual("{http://www.w3.org/2000/svg}svg", root.tag)
        self.assertEqual(
            "f3109603492ff063d7ee56995ed6b4e493bb370fdc8b65fba6b2dc3cc75bbc13",
            hashlib.sha256(first).hexdigest(),
        )

    def test_preview_contains_buildings_districts_and_networks(self):
        preview = render_preview(self.scene, self.ucg).decode("utf-8")

        self.assertIn('id="districts"', preview)
        self.assertIn('id="buildings"', preview)
        self.assertIn('id="networks"', preview)
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
        district_group = preview.find("svg:g[@id='districts']", namespace)
        district_rect = district_group.find("svg:g/svg:rect", namespace)

        self.assertGreater(float(district_rect.attrib["x"]), 250)
        self.assertLess(float(district_rect.attrib["x"]), 400)

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


if __name__ == "__main__":
    unittest.main()
