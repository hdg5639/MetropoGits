"""Vue/Svelte relationships come from real script blocks with original lines."""

import tempfile
import unittest
from pathlib import Path

from metropogits.cli import analyze_repository
from metropogits.analyzers.component_scripts import script_source
from metropogits.analyzers.common import AnalysisError


class ComponentScriptTests(unittest.TestCase):
    def test_vue_svelte_imports_and_file_resolution_keep_original_line(self):
        for suffix in ("vue", "svelte"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / "store.ts").write_text(
                    "export const store = 1;", encoding="utf8"
                )
                (root / f"View.{suffix}").write_text(
                    '<!-- <script>import "evil";</script> -->\n<script lang="ts">\nimport {store} from "./store";\n</script>\n<p>import "fake"</p>',
                    encoding="utf8",
                )
                (root / "main.ts").write_text(
                    f'import View from "./View.{suffix}";', encoding="utf8"
                )
                graph = analyze_repository(root, "fixture/sfc")
                paths = {e["id"]: e.get("path") for e in graph["entities"]}
                links = {
                    (paths[e["from"]], paths[e["to"]])
                    for e in graph["edges"]
                    if e["type"] == "IMPORTS"
                }
                self.assertEqual(
                    links,
                    {(f"View.{suffix}", "store.ts"), ("main.ts", f"View.{suffix}")},
                )
                evidence = [
                    e
                    for e in graph["evidence"]
                    if e["kind"] == "IMPORT" and e["sourcePath"].endswith(suffix)
                ]
                self.assertEqual(evidence[0]["startLine"], 3)

    def test_unclosed_script_is_rejected_not_silently_parsed_as_markup(self):
        with self.assertRaises(AnalysisError):
            script_source('<script>import "x";')

    def test_markup_and_comments_cannot_create_fake_code(self):
        source = "<!-- <script>bad()</script> --><p>import x</p>"
        self.assertFalse(script_source(source).strip())
