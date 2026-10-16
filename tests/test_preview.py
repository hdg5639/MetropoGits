import copy
import hashlib
import json
import unittest
import xml.etree.ElementTree as element_tree
from pathlib import Path

from metropogits.layout import generate_city
from metropogits.preview import PreviewError, render_preview


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
            "716792d62b98dd9dfe461e8966d50629364693000937926194113171674d39cc",
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
