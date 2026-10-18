import copy
import json
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from metropogits.access_routes import derive_access_routes, _pair
from metropogits.layout import generate_city
from metropogits.block_collectors import _expand, _rebuild
from metropogits.road_frontage import _surface
from metropogits.shared_frontage import _compress, _score, _search, plan_shared_frontages
from scripts.canonical_json import canonical_json_bytes
from scripts.road_metrics import road_metrics
from scripts.road_consolidation import compare, package
from test_block_collectors import fixture
import test_road_frontage as frontage_checks


def positive_fixture():
    buildings = [dict(entityId=f'b{i}', districtId='d', x=1+(i % 3)*7, z=1+(i//3)*7,
                      width=3, depth=3) for i in range(4)]
    edges = [dict(id=f'e{i}', **{'from': f'b{i}', 'to': f'b{(i+1) % 4}'}) for i in range(4)]
    scene = dict(buildings=buildings, districts=[dict(id='d', parentId=None, x=0, z=0, width=28, depth=21)],
                 networks=[dict(id='n', kind='DEPENDENCY_ROAD', edgeIds=[e['id'] for e in edges])])
    return scene, derive_access_routes(scene, dict(edges=edges))


class SharedFrontageTests(unittest.TestCase):
    def test_complete_trip_replanning_preserves_geometry_evidence_and_bounds(self):
        scene, original = positive_fixture()
        frozen = copy.deepcopy((scene, original))
        result = plan_shared_frontages(scene, original, original)
        frontage_checks.RoadFrontageTests().check(scene, original, result)
        self.assertEqual(frozen, (scene, original))
        self.assertTrue(result['sharedFrontage']['accepted'])
        before, after = road_metrics(original), road_metrics(result)
        self.assertLess(after['pavementCenterlineLength'], before['pavementCenterlineLength'])
        for key in ('junctions', 'nearbyParallelPairLength', 'turns'):
            self.assertLessEqual(after[key], before[key])

    def test_repeat_and_reversed_scene_order_are_identical(self):
        scene, original = fixture()
        first = plan_shared_frontages(scene, original, original)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(plan_shared_frontages(scene, original, original)))
        scene['buildings'].reverse()
        scene['districts'].reverse()
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(plan_shared_frontages(scene, original, original)))

    def test_failed_incident_path_rolls_back_entire_entrance(self):
        scene, original = fixture()
        with patch('metropogits.shared_frontage._search', return_value=None):
            after = plan_shared_frontages(scene, original, original)
        self.assertFalse(after['sharedFrontage']['accepted'])
        self.assertEqual(original['routes'], after['routes'])
        frontage_checks.RoadFrontageTests().check(scene, original, after)

    def test_resource_caps_preserve_every_relation(self):
        scene, original = fixture()
        for cap in ('MAX_ENTRANCES', 'MAX_PROPOSALS', 'MAX_SEARCH_STATES', 'MAX_GRAPH_EDGES', 'MAX_TRIP_STATES', 'MAX_TRIP_LABELS'):
            with self.subTest(cap=cap), patch('metropogits.shared_frontage.'+cap, 0):
                after = plan_shared_frontages(scene, original, original)
                self.assertTrue(after['sharedFrontage']['limitReached'])
                self.assertFalse(after['sharedFrontage']['accepted'])
                frontage_checks.RoadFrontageTests().check(scene, original, after)

    def test_invalid_or_compounded_provenance_is_rejected(self):
        scene, original = fixture()
        for mutation in ('version', 'status', 'edgeIds', 'repeat'):
            bad = copy.deepcopy(original)
            if mutation == 'edgeIds':
                bad['routes'][0]['edgeIds'] = ['fabricated']
            elif mutation == 'repeat':
                bad['sharedFrontage'] = {}
            else:
                bad[mutation] = 'invalid'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                plan_shared_frontages(scene, original, bad)

    def test_unknown_and_empty_input_do_not_create_roads(self):
        scene, original = fixture()
        original.update(routes=[], segments=[], junctions=[])
        scene['buildings'] = []
        result = plan_shared_frontages(scene, original, original)
        self.assertEqual([], result['routes'])
        self.assertEqual([], result['segments'])
        self.assertFalse(result['sharedFrontage']['limitReached'])

    def test_candidate_graph_is_not_exported_as_unused_pavement(self):
        scene, original = fixture()
        result = plan_shared_frontages(scene, original, original)
        used = {sid for route in result['routes'] for sid in route['segmentIds']}
        self.assertEqual(used, {s['id'] for s in result['segments']})
        frontage_checks.RoadFrontageTests().check(scene, original, result)

    def test_final_bend_regression_restores_prior_geometry(self):
        scene, original = fixture()
        result = plan_shared_frontages(scene, original, original)
        report = result['sharedFrontage']
        self.assertTrue(report['rolledBack'])
        self.assertTrue(report['candidateAccepted'])
        self.assertFalse(report['accepted'])
        self.assertGreater(report['candidateBends'], report['beforeBends'])
        for key in ('routes', 'segments', 'junctions'):
            self.assertEqual(original[key], result[key])

    def test_mixed_kind_endpoint_keeps_one_consistent_door(self):
        scene, original = positive_fixture()
        route = copy.deepcopy(original['routes'][0])
        route.update(id='http-route', kind='HTTP_HIGHWAY')
        original['routes'].append(route)
        result = plan_shared_frontages(scene, original, original)
        protected = {route['source'], route['target']}
        self.assertFalse(protected & {item['entityId'] for item in result['sharedFrontage']['accepted']})
        old = {r['id']: r for r in original['routes']}
        for current in result['routes']:
            for name, index in (('source', 0), ('target', -1)):
                if current[name] in protected:
                    self.assertEqual(old[current['id']]['path'][index], current['path'][index])

    def test_input_route_limit_does_not_silently_truncate(self):
        scene, original = fixture()
        with patch('metropogits.shared_frontage.MAX_INPUT_ROUTES', 1), self.assertRaises(ValueError):
            plan_shared_frontages(scene, original, original)

    def test_comparison_packages_the_same_routes_for_viewer_and_preview(self):
        graph = json.loads((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text(encoding='utf-8'))
        scene = generate_city(graph)
        before, after, report = compare(scene, graph, shared_frontage=True)
        self.assertIn('blockGateways', before)
        self.assertIn('sharedFrontage', report)
        artifacts = package(scene, graph, after, report)
        data = json.loads(artifacts['assets/viewer-data.js'].decode().split('=', 1)[1].rstrip(';\n'))
        self.assertEqual(after, data['routing'])
        self.assertEqual(canonical_json_bytes(scene), artifacts['city.json'])
        self.assertEqual(artifacts, package(scene, graph, after, report))
        self.assertIn(b'access-routing', artifacts['preview.svg'])
        self.assertIn(b'access-routing', artifacts['showcase.svg'])

    def test_membership_score_matches_expanded_geometry_oracle(self):
        scene, original = positive_fixture()
        paths, _ = _expand(original)
        routes = {r['id']: r for r in original['routes']}
        usage, doors = {}, {}
        for rid, nodes in paths.items():
            r = routes[rid]
            usage.setdefault(r['kind'], Counter()).update(_pair(a, b) for a, b in zip(nodes, nodes[1:]))
            for entity, index in ((r['source'], 0), (r['target'], -1)):
                doors[r['kind'], entity] = r['kind'], tuple(r['path'][index]), nodes[index]
        self.assertEqual(_surface(paths, routes, doors)[0], _score(usage, doors, ()))

    def test_prior_frontage_may_collapse_trip_to_access_only(self):
        scene = dict(buildings=[dict(entityId='a', x=1, z=1, width=3, depth=3),
                                dict(entityId='b', x=8, z=1, width=3, depth=3)])
        route = dict(id='r', kind='DEPENDENCY_ROAD', source='a', target='b', edgeIds=['e'],
                     networkIds=['n'], path=[[3.5, 1], [10.5, 1]], segmentIds=[])
        seed = dict(version='visual-access/0.2', status='COMPLETE', routes=[route],
                    segments=[], junctions=[], unresolvedEdgeIds=[])
        widths = {('DEPENDENCY_ROAD', ((i, 0), (i+1, 0))): .7 for i in (1, 2)}
        original = _rebuild(seed, {'r': [(1, 0), (2, 0), (3, 0)]}, widths)
        seed['routes'][0]['path'] = [[4, 3.5], [8, 3.5]]
        baseline = _rebuild(seed, {'r': [(2, 1)]}, widths)
        result = plan_shared_frontages(scene, original, baseline)
        self.assertEqual(baseline['routes'], result['routes'])
        self.assertEqual(baseline['segments'], result['segments'])
        frontage_checks.RoadFrontageTests().check(scene, original, result)

    def test_compression_retains_internal_bends_and_port_boundaries(self):
        points = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]
        graph = {p: set() for p in points}
        for a, b in zip(points, points[1:]):
            graph[a].add(b)
            graph[b].add(a)
        compiled = _compress(graph, {points[0], points[-1]})
        self.assertEqual(tuple(points), compiled[points[0]][0][1])
        self.assertEqual(1, compiled[points[0]][0][3])
        self.assertIsNone(_search(compiled, points[0], points[-1], Counter(), 4, 0, (0, 0), (0, 0), [0, 0]))
        self.assertEqual(points, _search(compiled, points[0], points[-1], Counter(), 4, 1, (0, 0), (0, 0), [0, 0]))
        split = _compress(graph, {points[0], points[2], points[-1]})
        self.assertEqual(points[2], split[points[0]][0][0])

    def test_search_respects_terminal_heading_and_disconnected_graph(self):
        graph = _compress({(0, 0): {(1, 0)}, (1, 0): {(0, 0)}}, {(0, 0), (1, 0)})
        self.assertIsNone(_search(graph, (0, 0), (1, 0), Counter(), 1, 0, (0, 0), (0, 1), [0, 0]))
        self.assertIsNone(_search(graph, (0, 0), (2, 0), Counter(), 3, 3, (0, 0), (0, 0), [0, 0]))


if __name__ == '__main__':
    unittest.main()
