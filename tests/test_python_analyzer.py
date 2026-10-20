"""AST resolution, boundaries and non-execution rather than framework guessing."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.analyzers.python import enrich_python_graph
from metropogits.cli import analyze_repository
from metropogits.scanner import ScanLimits, build_structural_ucg, scan_repository
from scripts.canonical_json import canonical_json_bytes
from scripts.validate_ucg import validate_document

FIXTURE = Path(__file__).parent / "fixtures/repositories/polyglot-python"


def analyze(root):
    scan = scan_repository(root)
    return enrich_python_graph(
        root, scan, build_structural_ucg(scan, "fixture/python"), ScanLimits()
    )


class PythonAnalyzerTests(unittest.TestCase):
    def test_relative_imports_inheritance_and_declarations_have_exact_evidence(self):
        graph = analyze(FIXTURE)
        self.assertEqual(validate_document(graph), [])
        paths = {e["id"]: e.get("path") for e in graph["entities"]}
        local = [
            (e["type"], paths[e["from"]], paths[e["to"]])
            for e in graph["edges"]
            if e["type"] != "CONTAINS"
        ]
        self.assertIn(("IMPORTS", "app/service.py", "app/store.py"), local)
        self.assertIn(("EXTENDS", "app/service.py", "app/store.py"), local)
        self.assertIn(("REFERENCES", "app/main.py", "app/service.py"), local)
        self.assertTrue(any(e["kind"] == "SYMBOL" for e in graph["entities"]))
        self.assertTrue(all(e["startLine"] >= 1 for e in graph["evidence"]))
        self.assertEqual(
            canonical_json_bytes(graph), canonical_json_bytes(analyze(FIXTURE))
        )

    def test_plain_python_uses_ast_and_never_executes_main_or_imports(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            marker = root / "executed.txt"
            (root / "main.py").write_text(
                f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
                encoding="utf8",
            )
            graph = analyze_repository(root, repository_id="fixture/plain")
            self.assertFalse(marker.exists())
            self.assertTrue(
                any(
                    e["code"] == "PYTHON_ANALYZER_COVERAGE" and e["parsedFiles"] == 1
                    for e in graph["diagnostics"]
                )
            )

    def test_comments_and_strings_do_not_create_import_edges(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "main.py").write_text(
                '# import fastapi\ns = "import redis"\n', encoding="utf8"
            )
            graph = analyze(root)
            self.assertFalse(any(e["type"] == "IMPORTS" for e in graph["edges"]))

    def test_syntax_errors_retain_structural_file_and_report_skip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "bad.py").write_text("def broken(:", encoding="utf8")
            graph = analyze(root)
            self.assertEqual(sum(e["kind"] == "FILE" for e in graph["entities"]), 1)
            self.assertTrue(
                any(
                    e["code"] == "PYTHON_ANALYSIS_SKIPPED" for e in graph["diagnostics"]
                )
            )

    def test_src_layout_and_ambiguity_do_not_guess_by_basename(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "src/pkg").mkdir(parents=True)
            (root / "src/pkg/__init__.py").write_text("", encoding="utf8")
            (root / "src/pkg/util.py").write_text("def f(): pass", encoding="utf8")
            (root / "main.py").write_text(
                "from pkg.util import f\nf()", encoding="utf8"
            )
            graph = analyze(root)
            target = next(
                e["id"] for e in graph["entities"] if e.get("path") == "src/pkg/util.py"
            )
            self.assertTrue(
                any(
                    e["to"] == target and e["type"] == "IMPORTS" for e in graph["edges"]
                )
            )
            (root / "pkg").mkdir()
            (root / "pkg/util.py").write_text("def f(): pass", encoding="utf8")
            graph = analyze(root)
            self.assertTrue(
                any(
                    e["code"] == "PYTHON_IMPORT_AMBIGUOUS" for e in graph["diagnostics"]
                )
            )

    def test_unresolved_relative_and_wildcard_are_disclosed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "main.py").write_text(
                "from ...missing import x\nfrom os import *", encoding="utf8"
            )
            graph = analyze(root)
            codes = {e["code"] for e in graph["diagnostics"]}
            self.assertIn("PYTHON_IMPORT_UNRESOLVED", codes)
            self.assertIn("PYTHON_WILDCARD_UNRESOLVED", codes)

    def test_ast_node_budget_retains_generic_structure(self):
        with patch("metropogits.analyzers.python.MAX_NODES", 1):
            graph = analyze(FIXTURE)
        self.assertEqual(sum(e["kind"] == "FILE" for e in graph["entities"]), 4)
        self.assertTrue(
            any(e["code"] == "PYTHON_ANALYSIS_SKIPPED" for e in graph["diagnostics"])
        )

    def test_framework_calls_are_bound_to_imports_and_not_shadowed_names(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "main.py").write_text(
                "from fastapi import FastAPI as API\napp = API()\n@app.get('/x')\ndef endpoint(): pass\n",
                encoding="utf8",
            )
            graph = analyze(root)
            self.assertTrue(
                any(
                    "python:fastapi.FastAPI.get" in e["summary"]
                    for e in graph["evidence"]
                )
            )
            (root / "main.py").write_text(
                "from fastapi import FastAPI as API\nAPI = object\napp = API()\n",
                encoding="utf8",
            )
            graph = analyze(root)
            self.assertFalse(
                any(
                    e["kind"] == "CALL" and "fastapi" in e["summary"]
                    for e in graph["evidence"]
                )
            )


if __name__ == "__main__":
    unittest.main()
