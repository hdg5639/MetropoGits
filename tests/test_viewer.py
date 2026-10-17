import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from metropogits.layout import generate_city
from metropogits.viewer import ViewerError, render_viewer
from scripts.canonical_json import loads_strict_json


FIXTURE_ROOT = Path(__file__).parent / "fixtures"


def load_fixture() -> dict:
    return loads_strict_json(
        (FIXTURE_ROOT / "ucg" / "valid" / "spring-minimal.json").read_text(
            encoding="utf-8"
        )
    )


class ViewerTests(unittest.TestCase):
    def test_viewer_is_deterministic_and_file_protocol_compatible(self):
        graph = load_fixture()
        scene = generate_city(graph)

        first = render_viewer(scene, graph)
        second = render_viewer(scene, graph)

        self.assertEqual(first, second)
        self.assertEqual(
            {
                "assets/viewer-activity.js",
                "assets/viewer-data.js",
                "assets/viewer.css",
                "assets/viewer-filters.js",
                "assets/viewer.js",
                "index.html",
            },
            set(first),
        )
        html = first["index.html"].decode("utf-8")
        self.assertIn("Content-Security-Policy", html)
        self.assertIn('data-filter="role"', html)
        self.assertIn('data-filter="confidence"', html)
        self.assertIn('id="synthetic-activity"', html)
        self.assertIn("not measured runtime traffic", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("fetch(", first["assets/viewer.js"].decode("utf-8"))

    def test_untrusted_graph_text_is_encoded_as_javascript_data(self):
        graph = copy.deepcopy(load_fixture())
        graph["repository"]["sourceUrl"] = "</script><img src=x onerror=alert(1)>"
        scene = generate_city(graph)

        artifacts = render_viewer(scene, graph)
        viewer_data = artifacts["assets/viewer-data.js"].decode("utf-8")

        self.assertNotIn("</script>", viewer_data)
        self.assertNotIn("<img", viewer_data)
        self.assertIn(r"\u003c/script\u003e", viewer_data)

    def test_viewer_script_avoids_html_injection_sinks(self):
        script = render_viewer(generate_city(load_fixture()), load_fixture())[
            "assets/viewer.js"
        ].decode("utf-8")

        self.assertNotIn("innerHTML", script)
        self.assertNotIn("outerHTML", script)
        self.assertNotIn("eval(", script)
        self.assertIn("textContent", script)

    def test_invalid_scene_is_rejected(self):
        graph = load_fixture()
        scene = generate_city(graph)
        scene["ucgDigest"] = "sha256:" + "0" * 64

        with self.assertRaisesRegex(ViewerError, "invalid City Scene"):
            render_viewer(scene, graph)

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_viewer_javascript_parses(self):
        graph = load_fixture()
        artifacts = render_viewer(generate_city(graph), graph)
        with tempfile.TemporaryDirectory() as temporary:
            for name in ("viewer-activity.js", "viewer-filters.js", "viewer.js"):
                script = Path(temporary) / name
                script.write_bytes(artifacts[f"assets/{name}"])
                completed = subprocess.run(
                    ["node", "--check", str(script)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_synthetic_activity_is_deterministic_and_path_bounded(self):
        script = """
require(process.argv[1]);
const activity = globalThis.METROPOGITS_ACTIVITY;
const first = activity.phaseForId("network:demo");
const second = activity.phaseForId("network:demo");
process.stdout.write(JSON.stringify({
  first,
  second,
  midpoint: activity.pointAlongPath([[0, 0], [10, 0], [10, 10]], 0.75),
  start: activity.pointAlongPath([[2, 3], [4, 5]], -1),
  end: activity.pointAlongPath([[2, 3], [4, 5]], 2),
}));
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-activity.js"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        result = json.loads(completed.stdout)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(result["first"], result["second"])
        self.assertGreaterEqual(result["first"], 0)
        self.assertLess(result["first"], 1)
        self.assertEqual([10, 5], result["midpoint"])
        self.assertEqual([2, 3], result["start"])
        self.assertEqual([4, 5], result["end"])

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_category_filters_cover_buildings_and_networks(self):
        graph = load_fixture()
        graph["entities"][0]["technologies"] = [
            {
                "confidence": "DECLARED",
                "evidenceIds": ["ev2"],
                "value": "SPRING_DATA",
            }
        ]
        scene = generate_city(load_fixture())
        script = """
const fs = require("fs");
require(process.argv[1]);
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const index = globalThis.METROPOGITS_FILTERS.createIndex(input.scene, input.ucg);
const apply = (filters) => index.filter({
  confidence: "", language: "", role: "", technology: "", ...filters,
});
process.stdout.write(JSON.stringify({
  all: apply({}),
  confidence: apply({ confidence: "DIRECT" }),
  language: apply({ language: "java" }),
  options: index.options,
  role: apply({ role: "SERVICE" }),
  technology: apply({ technology: "SPRING_DATA" }),
}));
"""

        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-filters.js"
                ),
            ],
            input=json.dumps({"scene": scene, "ucg": graph}),
            capture_output=True,
            text=True,
            check=False,
        )
        result = json.loads(completed.stdout)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(2, len(result["all"]["buildingIds"]))
        self.assertEqual(1, len(result["all"]["networkIds"]))
        self.assertEqual(
            ["demo:file:src/UserService.java"], result["role"]["buildingIds"]
        )
        self.assertEqual(1, len(result["role"]["networkIds"]))
        self.assertEqual(
            ["demo:file:src/UserRepository.java"],
            result["technology"]["buildingIds"],
        )
        self.assertEqual(1, len(result["technology"]["networkIds"]))
        self.assertEqual(2, len(result["language"]["buildingIds"]))
        self.assertEqual(
            ["demo:file:src/UserService.java"],
            result["confidence"]["buildingIds"],
        )
        self.assertEqual([], result["confidence"]["networkIds"])
        self.assertEqual(["java"], result["options"]["languages"])
        self.assertEqual(["PERSISTENCE_ADAPTER", "SERVICE"], result["options"]["roles"])
        self.assertEqual(["SPRING_DATA"], result["options"]["technologies"])


if __name__ == "__main__":
    unittest.main()
