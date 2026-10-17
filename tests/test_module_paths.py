import json
import tempfile
import unittest
from pathlib import Path

from metropogits.analyzers.jsts import enrich_jsts_graph
from metropogits.module_paths import parse_module_paths
from metropogits.scanner import ScanLimits, build_structural_ucg, scan_repository
from scripts.canonical_json import canonical_json_bytes


class ModulePathTests(unittest.TestCase):
    def test_maintained_alias_fixture_has_one_local_link_and_one_unresolved_reference(self):
        root = Path(__file__).parent / "fixtures/repositories/jsts-aliases"
        limits = ScanLimits()
        scan = scan_repository(root, limits)
        graph = enrich_jsts_graph(root, scan, build_structural_ucg(scan, "fixture/aliases"), limits)
        self.assertEqual(["src/lib/session.ts"], [target for _, target, _ in self.imports(graph)])
        self.assertEqual(1, sum(d["code"] == "JSTS_IMPORT_UNRESOLVED" for d in graph["diagnostics"]))

    def analyze(self, files, limits=None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for path, content in files.items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            limits = limits or ScanLimits()
            scan = scan_repository(root, limits)
            graph = enrich_jsts_graph(root, scan, build_structural_ucg(scan, "fixture/aliases"), limits)
            repeated = enrich_jsts_graph(root, scan, build_structural_ucg(scan, "fixture/aliases"), limits)
            self.assertEqual(canonical_json_bytes(graph), canonical_json_bytes(repeated))
            self.assertFalse((root / "executed.marker").exists())
            return graph

    def imports(self, graph):
        entities = {entity["id"]: entity for entity in graph["entities"]}
        return [(entities[edge["from"]]["path"], entities[edge["to"]]["path"], edge)
                for edge in graph["edges"] if edge["type"] == "IMPORTS"]

    def test_paths_bind_scanned_local_files_with_import_and_config_evidence(self):
        graph = self.analyze({
            "portal/tsconfig.json": '{"compilerOptions":{"paths":{"@/*":["./*"]}}}',
            "portal/app/page.tsx": 'import { auth } from "@/lib/auth"; import "react";',
            "portal/lib/auth.ts": 'export const auth = 1;',
            "elsewhere/entry.ts": 'import "@/lib/auth";',
        })
        imports = self.imports(graph)
        self.assertEqual(2, len(imports))
        local = next(edge for _, target, edge in imports if target == "portal/lib/auth.ts")
        self.assertEqual("RESOLVED", local["confidence"])
        evidence = {item["evidenceId"]: item for item in graph["evidence"]}
        self.assertEqual({"IMPORT", "CONFIG"}, {evidence[key]["kind"] for key in local["evidenceIds"]})
        self.assertFalse(any(entity["path"].startswith("npm/@/") for entity in graph["entities"]))

    def test_exact_longest_prefix_base_url_suffix_and_ordered_fallback(self):
        graph = self.analyze({
            "tsconfig.json": json.dumps({"compilerOptions": {"baseUrl": "src", "paths": {
                "@/*": ["wrong/*"], "@/api/*": ["missing/*", "api/*"],
                "@/api/exact": ["exact"], "assets/*.js": ["api/*"]}}}),
            "entry.ts": 'import "@/api/exact"; import "@/api/client"; import "assets/client.js";',
            "src/exact.ts": "export {};", "src/api/client.ts": "export {};",
            "src/wrong/api/client.ts": "export {};",
        })
        self.assertCountEqual(["src/exact.ts", "src/api/client.ts", "src/api/client.ts"],
                              [target for _, target, _ in self.imports(graph)])

    def test_nested_configs_shadow_outer_and_invalid_config_does_not_leak(self):
        files = {
            "tsconfig.json": '{"compilerOptions":{"paths":{"@/*":["lib/*"]}}}',
            "lib/x.ts": "export {};",
            "nested/entry.ts": 'import "@/x";',
            "nested/lib/x.ts": "export {};",
            "nested/tsconfig.json": '{"compilerOptions":{"paths":{"@/*":["lib/*"]}}}',
        }
        self.assertEqual("nested/lib/x.ts", self.imports(self.analyze(files))[0][1])
        for config in ('{}', '{"extends":"../tsconfig.json"}', '{bad', '// JSONC\n{}'):
            with self.subTest(config=config):
                files["nested/tsconfig.json"] = config
                self.assertEqual([], self.imports(self.analyze(files)))

    def test_missing_ambiguous_ignored_and_escaping_targets_are_not_external_packages(self):
        graph = self.analyze({
            "tsconfig.json": '{"compilerOptions":{"paths":{"@/*":["./*"],"escape":["../outside"]}}}',
            "entry.ts": 'import "@/missing"; import "@/ambiguous"; import "@/node_modules/hidden"; import "escape";',
            "ambiguous.ts": "export {};", "ambiguous.js": "export {};",
            "node_modules/hidden.ts": "export {};",
        })
        self.assertEqual([], self.imports(graph))
        self.assertIn("JSTS_IMPORT_AMBIGUOUS", {item["code"] for item in graph["diagnostics"]})

    def test_config_limits_and_invalid_forms(self):
        for data in ({"extends": "./base"}, {"compilerOptions": {"baseUrl": "C:/secret"}},
                     {"compilerOptions": {"paths": {"@/*": ["/secret/*"]}}},
                     {"compilerOptions": {"paths": {"*/*": ["x"]}}},
                     {"compilerOptions": {"paths": {"x": ["x"] * 17}}}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_module_paths("tsconfig.json", json.dumps(data).encode())
        graph = self.analyze({"tsconfig.json": " " * 300, "entry.ts": 'import "@/x";'},
                             ScanLimits(max_file_bytes=100))
        self.assertEqual([], self.imports(graph))
        self.assertIn("FILE_SIZE_LIMIT", {item["code"] for item in graph["diagnostics"]})

    def test_catchall_mapping_does_not_reinterpret_absolute_or_url_imports(self):
        graph = self.analyze({
            "tsconfig.json": '{"compilerOptions":{"paths":{"*":["target.ts"]}}}',
            "entry.ts": 'import "/absolute"; import "https://example.invalid/module";',
            "target.ts": "export {};",
        })
        self.assertEqual([], self.imports(graph))


if __name__ == "__main__":
    unittest.main()
