import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.access_routes import derive_access_routes
from metropogits.layout import generate_city
from metropogits.road_consolidation import _bends, consolidate_routes
from scripts.avenue_reservation import LAYOUT, MAX_MOVEMENT, candidates, door, reserve, study
from scripts.canonical_json import canonical_json_bytes
from scripts.parcel_pilot import pavement_intersections
from scripts.parcel_viewer import export_scene


def fixture():
    buildings = [dict(entityId=f'b{i}', districtId='leaf', x=7.5+(i if i < 4 else i+3)*14,
                      z=7.5, width=6, depth=6, height=10, archetype='GENERIC_BUILDING', evidenceIds=[])
                 for i in range(8)]
    buildings.append(dict(buildings[0], entityId='blocker', x=77.5))
    # Four resolved file pairs, six independently identified relations per pair.
    edges = [dict(id=f'e{i}-{j}', **{'from': f'b{i}', 'to': f'b{7-i}'}) for i in range(4) for j in range(6)]
    scene = dict(layoutAlgorithm=LAYOUT, buildings=buildings,
                 districts=[dict(id='leaf', parentId=None, x=0, z=0, width=168, depth=35,
                                 footprint=[dict(x=0, z=0, width=168, depth=35)])],
                 networks=[dict(id='n', kind='DEPENDENCY_ROAD', edgeIds=[e['id'] for e in edges])])
    routing = consolidate_routes(derive_access_routes(scene, dict(edges=edges)), merge_junctions=True, avenues=True)
    return scene, routing


class AvenueReservationTests(unittest.TestCase):
    def test_real_clearance_gain_preserves_through_roads_and_provenance(self):
        scene, routing = fixture()
        original = copy.deepcopy((scene, routing))
        changed, after, report = reserve(scene, routing)
        self.assertEqual(original, (scene, routing))
        self.assertEqual('CANDIDATE_SELECTED', report['selection'])
        self.assertGreater(report['surfaceAreaGain'], 0)
        self.assertEqual(scene['districts'], changed['districts'])
        self.assertEqual(0, pavement_intersections(after, changed['buildings']))
        old_segments = {s['id']: s for s in routing['segments']}
        new_segments = {s['id']: s for s in after['segments']}
        old = {r['id']: r for r in routing['routes']}
        movement = {m['entityId']: m['distance'] for m in report['movements']}
        for route in after['routes']:
            before = old[route['id']]
            for key in ('id', 'source', 'target', 'edgeIds', 'networkIds', 'kind', 'latticeSteps'):
                self.assertEqual(before[key], route[key])
            self.assertEqual(before['path'][1:-1], route['path'][1:-1])
            self.assertEqual(_bends(before['path']), _bends(route['path']))
            def length(path):
                return sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a, b in zip(path, path[1:]))
            self.assertLessEqual(abs(length(route['path'])-length(before['path'])),
                                 sum(movement.get(route[k], 0) for k in ('source', 'target'))+1e-8)
        for identity, before in old_segments.items():
            if not before['access']:
                after_segment = new_segments[identity]
                self.assertEqual(before['routeIds'], after_segment['routeIds'])
                self.assertGreaterEqual(after_segment['width'], before['width'])
        old_buildings = {b['entityId']: b for b in scene['buildings']}
        for b in changed['buildings']:
            before = old_buildings[b['entityId']]
            self.assertEqual({k: v for k, v in before.items() if k not in ('x', 'z')},
                             {k: v for k, v in b.items() if k not in ('x', 'z')})
            if b['entityId'] not in movement:
                self.assertEqual(before, b)
            else:
                self.assertLessEqual(movement[b['entityId']], MAX_MOVEMENT)

    def test_determinism_and_unrelated_addition_leave_existing_sites_fixed(self):
        scene, routing = fixture()
        first = reserve(scene, routing)
        self.assertEqual(canonical_json_bytes(list(first)), canonical_json_bytes(list(reserve(scene, routing))))
        scene['buildings'].reverse()
        routing['routes'].reverse()
        routing['segments'].reverse()
        self.assertEqual(canonical_json_bytes(list(first)), canonical_json_bytes(list(reserve(scene, routing))))
        scene['buildings'].append(dict(scene['buildings'][0], entityId='unrelated', districtId='other', x=210, z=35))
        scene['districts'].append(dict(id='other', parentId=None, x=196, z=28, width=42, depth=28,
                                       footprint=[dict(x=196, z=28, width=42, depth=28)]))
        changed = reserve(scene, routing)[0]
        self.assertEqual(first[0]['buildings'], [b for b in changed['buildings'] if b['entityId'] != 'unrelated'])

    def test_no_demand_deduplicates_edges_and_does_not_create_roads(self):
        scene, routing = fixture()
        for route in routing['routes']:
            route['edgeIds'] = ['same']*100
        changed, after, report = reserve(scene, routing)
        self.assertEqual('BASELINE_RETAINED', report['selection'])
        self.assertEqual(0, report['candidates'])
        self.assertEqual({b['entityId']: b for b in scene['buildings']}, {b['entityId']: b for b in changed['buildings']})
        self.assertEqual(routing['segments'], after['segments'])

    def test_foreign_blocker_and_concave_ownership_reject_candidates(self):
        scene, routing = fixture()
        scene['buildings'][-1]['districtId'] = 'other'
        self.assertEqual([], candidates(scene, routing))
        scene, routing = fixture()
        scene['districts'][0]['footprint'] = [dict(x=0, z=0, width=50, depth=35), dict(x=115, z=0, width=53, depth=35)]
        self.assertEqual([], candidates(scene, routing))

    def test_failed_candidate_is_atomic_and_budget_falls_back(self):
        scene, routing = fixture()
        for target in ('place', 'reconnect'):
            with patch('scripts.avenue_reservation.'+target, side_effect=ValueError('blocked')):
                changed, after, report = reserve(scene, routing)
            self.assertEqual('BASELINE_RETAINED', report['selection'])
            self.assertEqual(routing, after)
            self.assertEqual(sorted(scene['buildings'], key=lambda b: b['entityId']), changed['buildings'])
            self.assertEqual('blocked', report['candidateAudits'][0]['rejectedBecause'])
        with patch('scripts.avenue_reservation.MAX_CANDIDATES', 0):
            _, after, report = reserve(scene, routing)
        self.assertEqual('BASELINE_RETAINED', report['selection'])
        self.assertTrue(report['limitReached'])

    def test_fixed_access_rejects_crossing_or_missing_frontage(self):
        b = dict(x=7.5, z=7.5, width=6, depth=6)
        self.assertEqual([7.5, 10.5], door(b, [8, 10.5], [7, 10.5]))
        with self.assertRaisesRegex(ValueError, 'misses building frontage'):
            door(b, [8, 14], [7, 14])
        with self.assertRaisesRegex(ValueError, 'crosses fixed access port'):
            door(b, [14, 10.5], [13, 10.5])

    def test_version_and_partial_routing_rejected(self):
        scene, routing = fixture()
        scene['layoutAlgorithm'] = 'hierarchical-paged/1.14'
        with self.assertRaisesRegex(ValueError, 'experimental parcel'):
            reserve(scene, routing)
        scene['layoutAlgorithm'] = LAYOUT
        routing['status'] = 'PARTIAL'
        with self.assertRaises(ValueError):
            reserve(scene, routing)

    def test_valid_pipeline_fallback_and_same_structure_hint(self):
        graph = json.loads((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text())
        baseline = generate_city(graph)
        with self.assertRaisesRegex(ValueError, 'not relabeled'):
            study(baseline, graph)
        scene, _, _ = export_scene(baseline, graph)
        before, chosen, after, report = study(scene, graph)
        self.assertEqual('BASELINE_RETAINED', report['selection'])
        self.assertEqual(before, after)
        self.assertEqual(scene, chosen)
        hinted = study(scene, graph, chosen)
        self.assertEqual('HINT_APPLIED', hinted[3]['selection'])
        self.assertEqual(chosen['buildings'], hinted[1]['buildings'])
        chosen['buildings'].pop()
        with self.assertRaisesRegex(ValueError, 'incompatible experimental hint'):
            study(scene, graph, chosen)

    def test_cli_fresh_assets_manifest_and_overwrite_refusal(self):
        graph = json.loads((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text())
        scene, _, _ = export_scene(generate_city(graph), graph)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'city.json').write_bytes(canonical_json_bytes(scene))
            (root/'graph.ucg.json').write_bytes(canonical_json_bytes(graph))
            (root/'index.html').write_text('UNTRUSTED')
            command = [sys.executable, '-m', 'scripts.avenue_reservation', str(root), '--out', str(root/'out')]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertNotIn('UNTRUSTED', (root/'out/after/index.html').read_text(encoding='utf-8'))
            manifest = json.loads((root/'out/after/manifest.json').read_text())
            self.assertEqual('avenue-reservation/0.1', manifest['options']['reservationVersion'])
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(2, result.returncode)
            self.assertIn('must not already exist', result.stderr)


if __name__ == '__main__':
    unittest.main()
