import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.layout import generate_city
from metropogits.route_simplification import simplify_routes
from metropogits.shared_frontage import refine_failed_frontages, plan_shared_frontages
from scripts.canonical_json import canonical_json_bytes
from scripts.road_consolidation import compare, package
from scripts.road_metrics import road_metrics
from test_block_collectors import fixture
import test_road_frontage as frontage_checks


class FrontageRefinementTests(unittest.TestCase):
    def setUp(self):
        self.scene, self.original = fixture()
        self.base = simplify_routes(self.original, self.original)

    def test_moves_consistent_door_and_reduces_pavement_without_losing_relationships(self):
        frozen = copy.deepcopy((self.scene, self.original, self.base))
        result = refine_failed_frontages(self.scene, self.original, self.base)
        frontage_checks.RoadFrontageTests().check(self.scene, self.original, result)
        self.assertTrue(result['frontageRefinement']['accepted'])
        self.assertEqual(frozen, (self.scene, self.original, self.base))
        self.assertEqual(self.base['routeSimplification'], result['routeSimplification'])
        before, after = road_metrics(self.base), road_metrics(result)
        self.assertLess(after['pavementCenterlineLength'], before['pavementCenterlineLength'])
        for key in ('turns', 'junctions', 'nearbyParallelPairLength'):
            self.assertLessEqual(after[key], before[key])

    def test_repeat_and_input_order_are_deterministic(self):
        first = refine_failed_frontages(self.scene, self.original, self.base)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(
            refine_failed_frontages(self.scene, self.original, self.base)))
        self.scene['buildings'].reverse()
        self.base['routeSimplification']['constraints']['samples'].reverse()
        second = refine_failed_frontages(self.scene, self.original, self.base)
        # Historical reports retain the supplied order; the new decision and
        # all route geometry must be independent of diagnostic sample order.
        for key in ('frontageRefinement', 'routes', 'segments', 'junctions'):
            self.assertEqual(first[key], second[key])

    def test_failed_incident_trip_preserves_the_entire_baseline(self):
        with patch('metropogits.shared_frontage._search', return_value=None):
            result = refine_failed_frontages(self.scene, self.original, self.base)
        self.assertFalse(result['frontageRefinement']['accepted'])
        for key in ('routes', 'segments', 'junctions'):
            self.assertEqual(self.base[key], result[key])

    def test_caps_keep_safe_complete_routes(self):
        for name in ('REFINEMENT_STATES', 'REFINEMENT_ENTRANCES', 'MAX_GRAPH_EDGES', 'MAX_TRIP_STATES', 'MAX_PROPOSALS'):
            with self.subTest(name=name), patch('metropogits.shared_frontage.'+name, 0):
                result = refine_failed_frontages(self.scene, self.original, self.base)
                self.assertTrue(result['frontageRefinement']['limitReached'])
                self.assertFalse(result['frontageRefinement']['accepted'])
                frontage_checks.RoadFrontageTests().check(self.scene, self.original, result)

    def test_no_samples_or_no_roads_is_a_noop(self):
        self.base['routeSimplification']['constraints']['samples'] = []
        for empty in (False, True):
            if empty:
                self.base.update(routes=[], segments=[], junctions=[])
                self.original.update(routes=[], segments=[], junctions=[])
            result = refine_failed_frontages(self.scene, self.original, self.base)
            self.assertEqual(0, result['frontageRefinement']['attempts'])
            for key in ('routes', 'segments', 'junctions'):
                self.assertEqual(self.base[key], result[key])

    def test_invalid_provenance_repeat_and_oversized_samples_fail(self):
        for mutation in ('missing', 'repeat', 'sample', 'samples_limit', 'duplicate', 'identity', 'original'):
            original, base = copy.deepcopy((self.original, self.base))
            if mutation == 'missing':
                del base['routeSimplification']
            elif mutation == 'repeat':
                base['frontageRefinement'] = {}
            elif mutation == 'sample':
                base['routeSimplification']['constraints']['samples'][0]['routeId'] = 'absent'
            elif mutation == 'samples_limit':
                base['routeSimplification']['constraints']['samples'] *= 25
            elif mutation == 'duplicate':
                base['routes'].append(copy.deepcopy(base['routes'][0]))
            elif mutation == 'identity':
                base['routes'][0]['edgeIds'] = ['invented']
            else:
                original['version'] = 'visual-access/0.3'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                refine_failed_frontages(self.scene, original, base)

    def test_prior_report_is_preserved_and_legacy_repeat_guard_still_applies(self):
        self.base['sharedFrontage'] = {'version': 'shared-frontage/0.1', 'historic': True}
        result = refine_failed_frontages(self.scene, self.original, self.base)
        self.assertEqual(self.base['sharedFrontage'], result['sharedFrontage'])
        with self.assertRaises(ValueError):
            plan_shared_frontages(self.scene, self.original, result)
        with self.assertRaises(ValueError):
            refine_failed_frontages(self.scene, self.original, result)

    def test_only_nearby_entrances_can_change(self):
        self.base['routeSimplification']['constraints']['samples'] = self.base['routeSimplification']['constraints']['samples'][:1]
        rid = self.base['routeSimplification']['constraints']['samples'][0]['routeId']
        route = next(r for r in self.base['routes'] if r['id'] == rid)
        with patch('metropogits.shared_frontage.REFINEMENT_RADIUS', 0):
            result = refine_failed_frontages(self.scene, self.original, self.base)
        self.assertLessEqual(result['frontageRefinement']['nearbyBuildings'], 2)
        self.assertTrue({a['entityId'] for a in result['frontageRefinement']['accepted']}
                        <= {route['source'], route['target']})

    def test_cli_packaging_keeps_same_city_graph_and_renderer_paths(self):
        graph = json.loads((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text(encoding='utf-8'))
        scene = generate_city(graph)
        before, after, report = compare(scene, graph, refine_frontage=True)
        self.assertIn('routeSimplification', before)
        self.assertIn('frontageRefinement', report)
        artifacts = package(scene, graph, after, report)
        data = json.loads(artifacts['assets/viewer-data.js'].decode().split('=', 1)[1].rstrip(';\n'))
        self.assertEqual(after, data['routing'])
        self.assertEqual(canonical_json_bytes(scene), artifacts['city.json'])
        self.assertEqual(canonical_json_bytes(graph), artifacts['graph.ucg.json'])
        self.assertEqual(artifacts, package(scene, graph, after, report))


if __name__ == '__main__':
    unittest.main()
