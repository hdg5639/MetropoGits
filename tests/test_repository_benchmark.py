import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from scripts.repository_benchmark import benchmark_case, main, summarize, write_report


class RepositoryBenchmarkTests(unittest.TestCase):
    def test_real_build_repeat_timing_and_no_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root/'unsupported'
            repo.mkdir()
            marker = root/'executed'
            (repo/'tool.py').write_text(f'from pathlib import Path\nPath({str(marker)!r}).touch()\n', encoding='utf-8')
            with patch('scripts.repository_benchmark.git_identity', return_value={'revision': 'a'*40}):
                result = benchmark_case(repo, root/'output', streets=True)
            self.assertFalse(marker.exists())
            self.assertEqual(result['summary']['adapterProcessed'], 1)
            self.assertEqual(result['summary']['structuralOnly'], 0)
            # The Python AST adapter now observes the explicit pathlib import;
            # it must still never execute the marker-writing target.
            self.assertEqual(result['summary']['dependencyEdges'], 1)
            self.assertEqual(result['summary']['nonGenericRatio'], 0)
            self.assertTrue(result['determinism']['identicalArtifacts'])
            self.assertTrue(result['determinism']['identicalBuildingPositions'])
            self.assertIsNone(result['viewerPerformance'])
            self.assertGreater(result['profiledStageSeconds']['scan'], 0)
            self.assertEqual(result['streets']['assignedRoutes'], 0)
            self.assertTrue((root/'output/streets/index.html').is_file())

    def test_processed_is_not_resolved_and_skipped_is_disclosed(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo/'a.ts').write_text("import './missing';\n", encoding='utf-8')
            (repo/'b.ts').write_text('export const n=1;\n', encoding='utf-8')
            (repo/'widget.svelte').write_text('<p>Hello</p>', encoding='utf-8')
            graph = analyze_repository(repo, 'test/mixed')
            graph['diagnostics'].append(dict(code='JSTS_ANALYSIS_SKIPPED', sourcePath='b.ts'))
            result = summarize(graph, generate_city(graph))
            self.assertEqual(result['files'], 3)
            self.assertEqual(result['adapterProcessed'], 1)
            self.assertEqual(result['structuralOnly'], 2)
            self.assertTrue(result['unresolvedDiagnostics'])
            self.assertEqual(result['dependencyConfidence'].get('RESOLVED', 0), 0)

    def test_output_inside_input_is_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch('sys.argv', ['benchmark', '--repo', str(root), '--out', str(root/'generated')]):
                with self.assertRaises(SystemExit):
                    main()
            self.assertFalse((root/'generated').exists())

    def test_failure_gallery_escapes_untrusted_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_report(root, {'cases': [{'name': '<script>', 'error': '<img onerror=x>'}]})
            html = (root/'index.html').read_text(encoding='utf-8')
            self.assertNotIn('<script>', html)
            self.assertNotIn('<img onerror=', html)


if __name__ == '__main__':
    unittest.main()
