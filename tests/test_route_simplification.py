import copy
import json
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from metropogits.access_routes import _pair
from metropogits.block_collectors import _expand, _rebuild
from metropogits.layout import generate_city
from metropogits.route_simplification import _search, simplify_routes
from metropogits.shared_frontage import _compress
from scripts.canonical_json import canonical_json_bytes
from scripts.road_consolidation import compare, package
from scripts.road_metrics import road_metrics
from test_block_collectors import fixture
import test_road_frontage as oracle


def loop_fixture():
    # Equal-length alternatives around a block, used by several real trips.
    paths = {
        'a': [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)],
        'b': [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)],
        'c': [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)],
    }
    routes = [dict(id=rid, kind='DEPENDENCY_ROAD', source='s', target='t',
                   edgeIds=['edge-'+rid], networkIds=['network'],
                   path=[[0, 0], [7, 7]], segmentIds=[]) for rid in paths]
    seed = dict(version='visual-access/0.2', status='COMPLETE', routes=routes,
                segments=[], junctions=[], unresolvedEdgeIds=[])
    widths = {('DEPENDENCY_ROAD', _pair(a, b)): .7
              for nodes in paths.values() for a, b in zip(nodes, nodes[1:])}
    return _rebuild(seed, paths, widths)


class RouteSimplificationTests(unittest.TestCase):
    def test_atomic_corridor_removal_redirects_all_users_without_new_pavement(self):
        before = loop_fixture()
        after = simplify_routes(before, before)
        report = after['routeSimplification']
        self.assertFalse(report['accepted'])  # Equal trips are not individually changed.
        self.assertTrue(report['removedCorridors'])
        self.assertLess(road_metrics(after)['pavementCenterlineLength'], road_metrics(before)['pavementCenterlineLength'])
        self.assertTrue(set(_expand(after)[1]) <= set(_expand(before)[1]))
        paths = _expand(after)[0]
        self.assertEqual(paths['a'], paths['b'])
        self.assertEqual(paths['a'], paths['c'])
        for segment in after['segments']:
            self.assertEqual(['a', 'b', 'c'], segment['routeIds'])
        canonical_json_bytes(after)  # Developer metadata must also be valid JSON.

    def test_fixture_bounds_widths_identity_and_fixed_doors(self):
        scene, before = fixture()
        frozen = copy.deepcopy(before)
        after = simplify_routes(before, before)
        oracle.RoadFrontageTests().check(scene, before, after)
        self.assertEqual(frozen, before)
        old = {r['id']: r for r in before['routes']}
        for route in after['routes']:
            self.assertEqual([old[route['id']]['path'][i] for i in (0, -1)], [route['path'][i] for i in (0, -1)])
        a, b = road_metrics(before), road_metrics(after)
        for key in ('pavementCenterlineLength', 'turns', 'junctions', 'nearbyParallelPairLength'):
            self.assertLessEqual(b[key], a[key])

    def test_determinism_and_route_input_order(self):
        before = loop_fixture()
        expected = canonical_json_bytes(simplify_routes(before, before))
        self.assertEqual(expected, canonical_json_bytes(simplify_routes(before, before)))
        reversed_input = copy.deepcopy(before)
        reversed_input['routes'].reverse()
        reversed_input['segments'].reverse()
        self.assertEqual(expected, canonical_json_bytes(simplify_routes(before, reversed_input)))

    def test_failed_user_rolls_back_whole_corridor(self):
        before = loop_fixture()
        calls = []
        def fail_second(*args):
            calls.append(args)
            if len(calls) <= 3:
                return None  # Skip the three independent smoothing attempts.
            return None if (len(calls)-3) % 2 == 0 else _search(*args)
        # With single-user candidate forbidden, failure in a multi-user proposal
        # must not partially redirect its first successful user.
        from metropogits.route_simplification import _corridors
        def multi_user(*args):
            return [c for c in _corridors(*args) if len(set().union(*(args[2][k] for k in c[2]))) > 1]
        with patch('metropogits.route_simplification._corridors', side_effect=multi_user), patch('metropogits.route_simplification._search', side_effect=fail_second):
            after = simplify_routes(before, before)
        self.assertFalse(after['routeSimplification']['removedCorridors'])
        self.assertEqual(_expand(before), _expand(after))
        self.assertGreaterEqual(len(calls), 5)

    def test_smoothing_reduces_bends_without_lengthening_trip(self):
        before = loop_fixture()
        paths, widths = _expand(before)
        paths['a'] = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2)]
        for a, b in zip(paths['a'], paths['a'][1:]):
            widths['DEPENDENCY_ROAD', _pair(a, b)] = .7
        before = _rebuild(before, paths, widths)
        with patch('metropogits.route_simplification.MAX_ROUNDS', 0):
            after = simplify_routes(before, before)
        accepted = after['routeSimplification']['accepted']
        self.assertTrue(any(r['routeId'] == 'a' and r['removedBends'] > 0 for r in accepted))
        self.assertTrue(all(r['removedSteps'] >= 0 and r['removedBends'] >= 0 for r in accepted))

    def test_different_semantic_kinds_do_not_offer_shared_detours(self):
        before = loop_fixture()
        paths, widths = _expand(before)
        before['routes'][2]['kind'] = 'HTTP_HIGHWAY'
        for a, b in zip(paths['c'], paths['c'][1:]):
            widths['HTTP_HIGHWAY', _pair(a, b)] = .7
        before = _rebuild(before, paths, widths)
        after = simplify_routes(before, before)
        self.assertEqual(_expand(before), _expand(after))
        self.assertFalse(after['routeSimplification']['removedCorridors'])

    def test_caps_keep_complete_paths(self):
        scene, before = fixture()
        for cap in ('MAX_STATES', 'MAX_TRIP_STATES', 'MAX_LABELS', 'MAX_GRAPH_EDGES'):
            with self.subTest(cap=cap), patch('metropogits.route_simplification.'+cap, 0):
                after = simplify_routes(before, before)
                self.assertTrue(after['routeSimplification']['limitReached'])
                oracle.RoadFrontageTests().check(scene, before, after)
                self.assertEqual(_expand(before), _expand(after))
        with patch('metropogits.route_simplification.MAX_PROPOSALS', 0):
            after = simplify_routes(loop_fixture(), loop_fixture())
            self.assertTrue(after['routeSimplification']['limitReached'])
            self.assertFalse(after['routeSimplification']['removedCorridors'])
        with patch('metropogits.route_simplification.MAX_ROUTES', 0), self.assertRaises(ValueError):
            simplify_routes(before, before)

    def test_invalid_or_compounded_input_rejected(self):
        before = loop_fixture()
        for mutation in ('status', 'version', 'edgeIds', 'duplicate', 'repeat', 'bounds'):
            bad = copy.deepcopy(before)
            if mutation in ('status', 'version'):
                bad[mutation] = 'invalid'
            elif mutation == 'edgeIds':
                bad['routes'][0]['edgeIds'] = ['fake']
            elif mutation == 'duplicate':
                bad['routes'].append(copy.deepcopy(bad['routes'][0]))
            elif mutation == 'repeat':
                bad['routeSimplification'] = {}
            else:
                bad['routes'][0]['path'][0] = [-10000, 0]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                simplify_routes(before, bad)

    def test_empty_input_and_access_only_remain_unchanged(self):
        for routing in (
            dict(version='visual-access/0.2', status='COMPLETE', routes=[], segments=[], junctions=[]),
            _rebuild(dict(version='visual-access/0.2', status='COMPLETE',
                          routes=[dict(id='r', kind='DEPENDENCY_ROAD', source='s', target='t',
                                       edgeIds=['e'], networkIds=['n'], path=[[0, 3.5], [7, 3.5]], segmentIds=[])],
                          segments=[], junctions=[]), {'r': [(1, 1)]}, {}),
        ):
            after = simplify_routes(routing, routing)
            for key in ('routes', 'segments', 'junctions'):
                self.assertEqual(routing[key], after[key])

    def test_search_never_uses_removed_edges_and_obeys_headings(self):
        a, b = (0, 0), (1, 0)
        graph = _compress({a: {b}, b: {a}}, {a, b})
        usage = Counter({_pair(a, b): 1})
        self.assertEqual([a, b], _search(graph, a, b, usage, 1, 0, (0, 0), (0, 0), [0, 0]))
        self.assertIsNone(_search(graph, a, b, usage, 1, 0, (0, 0), (0, 1), [0, 0]))
        self.assertIsNone(_search(graph, a, b, Counter(), 2, 2, (0, 0), (0, 0), [0, 0]))

    def test_explicit_comparison_shares_renderer_geometry_without_scene_change(self):
        graph = json.loads((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text(encoding='utf-8'))
        scene = generate_city(graph)
        before, after, report = compare(scene, graph, simplify=True)
        self.assertIn('sharedFrontage', before)
        self.assertNotIn('routeSimplification', before)
        self.assertIn('routeSimplification', report)
        artifacts = package(scene, graph, after, report)
        data = json.loads(artifacts['assets/viewer-data.js'].decode().split('=', 1)[1].rstrip(';\n'))
        self.assertEqual(after, data['routing'])
        self.assertEqual(canonical_json_bytes(scene), artifacts['city.json'])
        self.assertEqual(artifacts, package(scene, graph, after, report))


if __name__ == '__main__':
    unittest.main()
