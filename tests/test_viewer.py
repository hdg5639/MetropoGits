import copy
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
                "assets/viewer-data.js",
                "assets/viewer.css",
                "assets/viewer.js",
                "index.html",
            },
            set(first),
        )
        html = first["index.html"].decode("utf-8")
        self.assertIn("Content-Security-Policy", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("fetch(", first["assets/viewer.js"].decode("utf-8"))

    def test_untrusted_graph_text_is_encoded_as_javascript_data(self):
        graph = copy.deepcopy(load_fixture())
        graph["repository"]["sourceUrl"] = (
            "</script><img src=x onerror=alert(1)>"
        )
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
            script = Path(temporary) / "viewer.js"
            script.write_bytes(artifacts["assets/viewer.js"])
            completed = subprocess.run(
                ["node", "--check", str(script)],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(0, completed.returncode, completed.stderr)


if __name__ == "__main__":
    unittest.main()
