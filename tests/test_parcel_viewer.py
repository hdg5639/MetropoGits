import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.layout import generate_city
from scripts.canonical_json import canonical_json_bytes
from scripts.parcel_viewer import BASELINE, LAYOUT, export_scene, package
from scripts.stable_ids import make_edge_id
from scripts.validate_city import validate_document


class ParcelViewerTests(unittest.TestCase):
    def setUp(self):
        self.graph = json.loads((Path(__file__).parent / 'fixtures/ucg/valid/spring-minimal.json').read_text())
        self.baseline = generate_city(self.graph)

    def test_valid_export_preserves_facts_and_complete_routes(self):
        before = copy.deepcopy((self.baseline, self.graph))
        scene, routing, decision = export_scene(self.baseline, self.graph)
        self.assertEqual([], validate_document(scene, self.graph))
        self.assertEqual(LAYOUT, scene['layoutAlgorithm'])
        self.assertEqual(before, (self.baseline, self.graph))
        self.assertEqual('BASELINE_RETAINED', decision['selection'])
        self.assertEqual(self.baseline['districts'], scene['districts'])
        self.assertEqual(self.baseline['buildings'], scene['buildings'])
        self.assertEqual([{k: v for k, v in n.items() if k != 'path'} for n in self.baseline['networks']],
                         [{k: v for k, v in n.items() if k != 'path'} for n in scene['networks']])
        self.assertEqual({e for n in scene['networks'] for e in n['edgeIds']},
                         {e for r in routing['routes'] for e in r['edgeIds']})
        self.assertEqual(0, decision['fullCityRouting']['pavementBuildingIntersections'])

    def test_determinism_canonical_order_and_default_unchanged(self):
        before = canonical_json_bytes(generate_city(self.graph))
        expected = canonical_json_bytes(list(export_scene(self.baseline, self.graph)))
        self.assertEqual(expected, canonical_json_bytes(list(export_scene(self.baseline, self.graph))))
        for key in ('buildings', 'districts', 'networks'):
            self.baseline[key].reverse()
        with self.assertRaisesRegex(ValueError, 'canonical order'):
            export_scene(self.baseline, self.graph)
        self.assertEqual(before, canonical_json_bytes(generate_city(self.graph)))
        self.assertEqual(BASELINE, generate_city(self.graph)['layoutAlgorithm'])

    def test_hint_locks_positions_and_preserves_current_attributes(self):
        previous, _, _ = export_scene(self.baseline, self.graph)
        self.baseline['buildings'][0]['height'] += 1
        original = copy.deepcopy(previous)
        scene, _, report = export_scene(self.baseline, self.graph, previous)
        self.assertEqual('HINT_APPLIED', report['selection'])
        self.assertEqual(original, previous)
        self.assertEqual([(b['x'], b['z']) for b in previous['buildings']],
                         [(b['x'], b['z']) for b in scene['buildings']])
        self.assertEqual(self.baseline['buildings'][0]['height'], scene['buildings'][0]['height'])

    def test_selected_overrides_move_only_coordinates_and_refresh_network_path(self):
        buildings = copy.deepcopy(self.baseline['buildings'])
        first, second = buildings
        first['x'], second['x'] = second['x'], first['x']
        first['z'], second['z'] = second['z'], first['z']
        proposal = dict(status='EXPERIMENTAL', safeCandidate=True,
                        selection='CANDIDATE_SELECTED', overrides=buildings)
        self.baseline['networks'][0]['path'] = [[-700, -700], [-693, -700]]
        with patch('scripts.parcel_viewer.experiment', return_value=proposal):
            scene, _, decision = export_scene(self.baseline, self.graph)
        self.assertEqual(buildings, scene['buildings'])
        self.assertEqual('CANDIDATE_SELECTED', decision['selection'])
        self.assertNotEqual(self.baseline['networks'][0]['path'], scene['networks'][0]['path'])

    def test_hint_keeps_positions_when_current_relationships_change(self):
        previous, _, _ = export_scene(self.baseline, self.graph)
        edge = copy.deepcopy(self.graph['edges'][0])
        edge['from'], edge['to'] = edge['to'], edge['from']
        edge['id'] = make_edge_id(edge['from'], edge['type'], edge['to'])
        self.graph['edges'].append(edge)
        self.graph['edges'].sort(key=lambda e: e['id'])
        current = generate_city(self.graph)
        scene, routing, _ = export_scene(current, self.graph, previous)
        self.assertNotEqual(previous['ucgDigest'], scene['ucgDigest'])
        self.assertEqual([(b['x'], b['z']) for b in previous['buildings']],
                         [(b['x'], b['z']) for b in scene['buildings']])
        self.assertIn(edge['id'], {e for r in routing['routes'] for e in r['edgeIds']})

    def test_hint_cannot_transfer_colliding_geometry(self):
        previous, _, _ = export_scene(self.baseline, self.graph)
        previous['buildings'][1].update(x=previous['buildings'][0]['x'], z=previous['buildings'][0]['z'])
        with self.assertRaisesRegex(ValueError, 'invalid experimental scene'):
            export_scene(self.baseline, self.graph, previous)

    def test_rejects_incompatible_hint_and_default_does_not_relabel(self):
        with self.assertRaisesRegex(ValueError, 'incompatible experimental hint'):
            export_scene(self.baseline, self.graph, self.baseline)
        previous, _, _ = export_scene(self.baseline, self.graph)
        diagnostics = []
        default = generate_city(self.graph, previous_scene=previous, diagnostics=diagnostics)
        self.assertEqual(BASELINE, default['layoutAlgorithm'])
        self.assertTrue(diagnostics)
        previous['buildings'].pop()
        with self.assertRaisesRegex(ValueError, 'incompatible experimental hint'):
            export_scene(self.baseline, self.graph, previous)

    def test_directory_geometry_hint_rejection(self):
        previous, _, _ = export_scene(self.baseline, self.graph)
        # Translate a complete, still valid old city. No silent cold reset.
        for district in previous['districts']:
            district['x'] += 7
            for rect in district['footprint']:
                rect['x'] += 7
        for building in previous['buildings']:
            building['x'] += 7
        self.assertEqual([], validate_document(previous, self.graph))
        with self.assertRaisesRegex(ValueError, 'directory geometry changed'):
            export_scene(self.baseline, self.graph, previous)

    def test_fail_closed_on_partial_coverage_or_intersection(self):
        _, routing, _ = export_scene(self.baseline, self.graph)
        partial = copy.deepcopy(routing)
        partial['status'] = 'PARTIAL'
        empty = copy.deepcopy(routing)
        empty['routes'] = []
        for unsafe in (partial, empty):
            with self.subTest(status=unsafe['status']), patch('scripts.parcel_viewer.derive_access_routes', return_value=unsafe):
                with self.assertRaisesRegex(ValueError, 'full-city access routing failed'):
                    export_scene(self.baseline, self.graph)
        with patch('scripts.parcel_viewer.pavement_intersections', return_value=1):
            with self.assertRaisesRegex(ValueError, 'full-city access routing failed'):
                export_scene(self.baseline, self.graph)

    def test_all_consumers_share_scene_routes_and_manifest_contract(self):
        scene, routing, decision = export_scene(self.baseline, self.graph)
        artifacts = package(scene, self.graph, routing, decision)
        self.assertIn(b'EXPERIMENTAL PARCEL LAYOUT', artifacts['index.html'])
        payload = json.loads(artifacts['assets/viewer-data.js'].decode().split('=', 1)[1].rstrip(';\n'))
        self.assertEqual(scene, payload['scene'])
        self.assertEqual(routing, payload['routing'])
        self.assertEqual(self.graph, json.loads(artifacts['graph.ucg.json']))
        manifest = json.loads(artifacts['manifest.json'])
        self.assertEqual('COMPLETE', manifest['status'])
        self.assertTrue(manifest['options']['experimental'])
        self.assertEqual(0, manifest['diagnostics']['count'])
        for record in manifest['artifacts']:
            content = artifacts[record['path']]
            self.assertEqual('sha256:' + hashlib.sha256(content).hexdigest(), record['sha256'])
            self.assertEqual(len(content), record['bytes'])
            self.assertIn('mediaType', record)
        self.assertEqual(artifacts, package(scene, self.graph, routing, decision))

    def test_cli_ignores_input_scripts_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'graph.ucg.json').write_bytes(canonical_json_bytes(self.graph))
            (root / 'city.json').write_bytes(canonical_json_bytes(self.baseline))
            (root / 'index.html').write_text('UNTRUSTED INPUT HTML')
            out = root / 'export'
            command = [sys.executable, '-m', 'scripts.parcel_viewer', str(root), '--out', str(out)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertNotIn('UNTRUSTED', (out / 'index.html').read_text(encoding='utf-8'))
            before = (out / 'city.json').read_bytes()
            repeat = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(2, repeat.returncode)
            self.assertIn('must not already exist', repeat.stderr)
            self.assertEqual(before, (out / 'city.json').read_bytes())

    def test_invalid_or_wrong_layout_input_rejected(self):
        self.baseline['layoutAlgorithm'] = LAYOUT
        with self.assertRaisesRegex(ValueError, 'expected a city/0.2 baseline'):
            export_scene(self.baseline, self.graph)
        self.baseline['buildings'][0]['entityId'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'invalid input'):
            export_scene(self.baseline, self.graph)

    def test_bad_cli_input_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'graph.ucg.json').write_text('{"duplicate":1,"duplicate":2}', encoding='utf-8')
            out = root / 'export'
            result = subprocess.run([sys.executable, '-m', 'scripts.parcel_viewer', str(root),
                                     '--out', str(out)], capture_output=True, text=True)
            self.assertEqual(2, result.returncode)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
