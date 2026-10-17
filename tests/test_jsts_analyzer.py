import tempfile
import unittest
from pathlib import Path

from metropogits.analyzers.jsts import enrich_jsts_graph
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.scanner import ScanLimits, build_structural_ucg, scan_repository
from scripts.canonical_json import canonical_json_bytes
from scripts.validate_ucg import validate_document


FIXTURES = Path(__file__).parent / "fixtures" / "repositories"


def analyze(root: Path) -> dict:
    limits = ScanLimits()
    scan = scan_repository(root, limits)
    graph = build_structural_ucg(scan, "fixture/jsts")
    return enrich_jsts_graph(root, scan, graph, limits)


def files_by_name(graph: dict) -> dict[str, dict]:
    return {
        Path(entity["path"]).name: entity
        for entity in graph["entities"]
        if entity["kind"] == "FILE"
    }


class JsTsAnalyzerTests(unittest.TestCase):
    def test_explicit_module_forms_create_evidenced_edges(self):
        graph = analyze(FIXTURES / "jsts-basic")
        files = files_by_name(graph)
        import_edges = [edge for edge in graph["edges"] if edge["type"] == "IMPORTS"]
        local_edges = [edge for edge in import_edges if ":file:" in edge["to"]]
        external_edges = [
            edge for edge in import_edges if ":external-package:" in edge["to"]
        ]

        self.assertEqual(4, len(local_edges))
        self.assertTrue(all(edge["confidence"] == "RESOLVED" for edge in local_edges))
        self.assertEqual(1, len(external_edges))
        self.assertEqual("DIRECT", external_edges[0]["confidence"])
        external = next(
            entity
            for entity in graph["entities"]
            if entity["id"] == external_edges[0]["to"]
        )
        self.assertEqual("npm/react", external["path"])

        fake_id = files["fake.ts"]["id"]
        self.assertFalse(any(edge["to"] == fake_id for edge in import_edges))
        evidence = {item["evidenceId"]: item for item in graph["evidence"]}
        self.assertTrue(
            all(
                evidence[edge["evidenceIds"][0]]["extractor"] == "jsts-static/0.1"
                for edge in import_edges
            )
        )
        self.assertEqual(
            {
                "jsts.commonjs-require",
                "jsts.dynamic-import",
                "jsts.esm-export",
                "jsts.esm-import",
            },
            {
                evidence[evidence_id]["ruleId"]
                for edge in import_edges
                for evidence_id in edge["evidenceIds"]
            },
        )
        self.assertEqual([], validate_document(graph))

    def test_cli_composes_jsts_adapter_and_city_networks(self):
        graph = analyze_repository(
            FIXTURES / "jsts-basic", repository_id="fixture/cli-jsts"
        )
        coverage = next(
            item for item in graph["diagnostics"] if item["code"] == "ANALYZER_COVERAGE"
        )
        scene = generate_city(graph)
        local_import_ids = sorted(
            edge["id"]
            for edge in graph["edges"]
            if edge["type"] == "IMPORTS"
            and ":file:" in edge["from"]
            and ":file:" in edge["to"]
        )
        network_edge_ids = sorted(
            edge_id for network in scene["networks"] for edge_id in network["edgeIds"]
        )

        self.assertIn("6 JavaScript/TypeScript file(s)", coverage["message"])
        self.assertEqual(4, len(local_import_ids))
        self.assertEqual(local_import_ids, network_edge_ids)

    def test_npm_manifest_and_import_share_package_without_claiming_unused_usage(self):
        root = FIXTURES / "npm-manifest"

        graph = analyze_repository(root, repository_id="fixture/npm")

        packages = {
            entity["path"]: entity
            for entity in graph["entities"]
            if entity["kind"] == "EXTERNAL_PACKAGE"
        }
        self.assertEqual(3, len(packages))
        react_id = packages["npm/react"]["id"]
        redis_id = packages["npm/redis"]["id"]
        react_edges = [
            edge
            for edge in graph["edges"]
            if edge["to"] == react_id
        ]
        redis_edges = [
            edge
            for edge in graph["edges"]
            if edge["to"] == redis_id
        ]
        self.assertEqual({"DEPENDS_ON", "IMPORTS"}, {edge["type"] for edge in react_edges})
        self.assertEqual(["DEPENDS_ON"], [edge["type"] for edge in redis_edges])
        self.assertFalse(any(entity.get("technologies") for entity in graph["entities"]))
        self.assertEqual([], validate_document(graph))

    def test_analysis_is_deterministic_and_never_executes_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "executed.marker"
            (root / "danger.js").write_text(
                "require('fs').writeFileSync('executed.marker', 'bad');",
                encoding="utf-8",
            )

            first = analyze(root)
            second = analyze(root)

        self.assertFalse(marker.exists())
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_ambiguous_and_escaping_relative_imports_stay_unresolved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "entry.ts").write_text(
                'import "./target";\nimport "../outside";', encoding="utf-8"
            )
            (root / "target.js").write_text("export {};", encoding="utf-8")
            (root / "target.ts").write_text("export {};", encoding="utf-8")

            graph = analyze(root)

        imports = [edge for edge in graph["edges"] if edge["type"] == "IMPORTS"]
        diagnostic_codes = [item["code"] for item in graph["diagnostics"]]
        self.assertEqual([], imports)
        self.assertIn("JSTS_IMPORT_AMBIGUOUS", diagnostic_codes)
        self.assertIn("JSTS_IMPORT_UNRESOLVED", diagnostic_codes)

    def test_malformed_file_is_skipped_without_losing_safe_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "broken.ts").write_text('import "unterminated\n', encoding="utf-8")
            (root / "safe.ts").write_text("export {};", encoding="utf-8")

            graph = analyze(root)

        skipped = [
            item
            for item in graph["diagnostics"]
            if item["code"] == "JSTS_ANALYSIS_SKIPPED"
        ]
        self.assertEqual(1, len(skipped))
        self.assertEqual("broken.ts", skipped[0]["sourcePath"])
        self.assertIn("safe.ts", files_by_name(graph))


if __name__ == "__main__":
    unittest.main()
