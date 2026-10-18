import copy
import json
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import patch

from metropogits.access_routes import PITCH, _id, _pair
from metropogits.layout import generate_city
from metropogits.road_consolidation import _bends, _search, consolidate_routes
from scripts.canonical_json import canonical_json_bytes
from scripts.road_consolidation import compare, package
from scripts.road_metrics import road_metrics


def fixture(length=40, separate_kinds=False):
    paths = [[(x, 0) for x in range(length+1)], [(x, 1) for x in range(length+1)],
             [(0, 0), (0, 1)], [(length, 0), (length, 1)]]
    segments, routes = {}, []
    for i, nodes in enumerate(paths):
        kind = 'HTTP_HIGHWAY' if separate_kinds and i == 1 else 'DEPENDENCY_ROAD'
        identity, ids = f'r{i}', []
        points = [[x*PITCH, z*PITCH] for x, z in nodes]
        for a, b in zip(points, points[1:]):
            start, end = sorted((a, b))
            key = _id('access-segment', [kind, start, end])
            segments.setdefault(key, dict(id=key, kind=kind, start=start, end=end,
                                           width=.5, access=False, routeIds=[]))['routeIds'].append(identity)
            ids.append(key)
        routes.append(dict(id=identity, kind=kind, source=f's{i}', target=f't{i}',
                           edgeIds=[f'e{i}'], networkIds=['n'], path=points, segmentIds=ids,
                           latticeSteps=len(nodes)-1))
    return dict(version='visual-access/0.2', status='COMPLETE', routes=routes,
                segments=sorted(segments.values(), key=lambda s: s['id']), junctions=[],
                diagnostics=[], unresolvedEdgeIds=[], searchExpansions=0)


def atomic(routing):
    result = set()
    for s in routing['segments']:
        if s['access']:
            continue
        a, b = [tuple(round(v/PITCH) for v in p) for p in (s['start'], s['end'])]
        dx, dz = (b[0] > a[0])-(b[0] < a[0]), (b[1] > a[1])-(b[1] < a[1])
        for i in range(abs(b[0]-a[0])+abs(b[1]-a[1])):
            left = a[0]+i*dx, a[1]+i*dz
            right = left[0]+dx, left[1]+dz
            result.add((s['kind'], _pair(left, right)))
    return result


class RoadConsolidationTests(unittest.TestCase):
    def test_real_detour_reuses_road_and_removes_parallel_pavement(self):
        before = fixture()
        original = copy.deepcopy(before)
        after = consolidate_routes(before)
        self.assertEqual(original, before)
        self.assertGreater(after['consolidation']['accepted'], 0)
        self.assertTrue(atomic(after) < atomic(before))
        old, new = road_metrics(before), road_metrics(after)
        self.assertLess(new['pavementCenterlineLength'], old['pavementCenterlineLength'])
        self.assertLess(new['nearbyParallelPairLength'], old['nearbyParallelPairLength'])
        self.assertGreater(new['routeLength'], old['routeLength'])
        self.assertEqual('visual-access/0.3', after['version'])
        self.check_provenance(before, after)

    def check_provenance(self, before, after):
        old = {r['id']: r for r in before['routes']}
        segments = {s['id']: s for s in after['segments']}
        self.assertEqual(set(old), {r['id'] for r in after['routes']})
        for route in after['routes']:
            source = old[route['id']]
            for key in ('kind', 'source', 'target', 'edgeIds', 'networkIds'):
                self.assertEqual(source[key], route[key])
            self.assertEqual(source['path'][0], route['path'][0])
            self.assertEqual(source['path'][-1], route['path'][-1])
            self.assertLessEqual(_bends(route['path']), _bends(source['path'])+2)
            self.assertEqual(len(route['path']), len(route['segmentIds'])+1)
            for i, sid in enumerate(route['segmentIds']):
                segment = segments[sid]
                self.assertIn(route['id'], segment['routeIds'])
                self.assertEqual(sorted(route['path'][i:i+2]), sorted([segment['start'], segment['end']]))
        for segment in after['segments']:
            self.assertEqual(sorted(r['id'] for r in after['routes'] if segment['id'] in r['segmentIds']), segment['routeIds'])
        for junction in after['junctions']:
            for sid in junction['segmentIds']:
                self.assertIn(junction['point'], [segments[sid]['start'], segments[sid]['end']])

    def test_independent_shortest_path_bound_and_no_compounded_detour(self):
        before = fixture()
        after = consolidate_routes(before)
        adjacency = {}
        for _, (a, b) in atomic(before):
            adjacency.setdefault(a, set()).add(b)
            adjacency.setdefault(b, set()).add(a)
        for route in after['routes']:
            start, end = [tuple(round(v/PITCH) for v in p) for p in (route['path'][0], route['path'][-1])]
            queue, seen = deque([(start, 0)]), {start}
            while queue:
                node, distance = queue.popleft()
                if node == end:
                    break
                for neighbor in adjacency[node]-seen:
                    seen.add(neighbor)
                    queue.append((neighbor, distance+1))
            self.assertLessEqual(route['latticeSteps']*90, distance*100)
        with self.assertRaisesRegex(ValueError, 'complete visual-access/0.2'):
            consolidate_routes(after)

    def test_short_route_cannot_take_excessive_detour(self):
        before = fixture(length=10)
        after = consolidate_routes(before)
        self.assertEqual(atomic(before), atomic(after))
        self.assertEqual(0, after['consolidation']['accepted'])

    def test_cannot_route_over_another_network_kind(self):
        before = fixture(separate_kinds=True)
        after = consolidate_routes(before)
        self.assertEqual(atomic(before), atomic(after))
        self.check_provenance(before, after)

    def test_other_building_access_spur_is_not_a_through_road(self):
        before = fixture()
        for segment in before['segments']:
            if segment['start'][0] == segment['end'][0] == 0:
                segment['access'] = True
        after = consolidate_routes(before)
        self.assertEqual(atomic(before), atomic(after))
        self.check_provenance(before, after)

    def test_budget_exhaustion_retains_atomic_safe_result(self):
        before = fixture()
        for budget in (0, 5, 100):
            with patch('metropogits.road_consolidation.MAX_SEARCH_STATES', budget):
                after = consolidate_routes(before)
            self.assertLessEqual(after['consolidation']['searchStates'], budget)
            self.assertTrue(atomic(after) <= atomic(before))
            self.check_provenance(before, after)

    def test_multi_route_removal_rolls_back_when_one_replacement_fails(self):
        before = fixture()
        for route in list(before['routes']):
            duplicate = copy.deepcopy(route)
            duplicate.update(id=route['id']+'copy', source=route['source']+'copy', edgeIds=[route['edgeIds'][0]+'copy'])
            before['routes'].append(duplicate)
            for segment in before['segments']:
                if route['id'] in segment['routeIds']:
                    segment['routeIds'].append(duplicate['id'])
        calls = []
        def fail_second(*args):
            calls.append(1)
            return _search(*args) if len(calls) == 1 else None
        with patch('metropogits.road_consolidation.MAX_ATTEMPTS', 1), patch('metropogits.road_consolidation._search', side_effect=fail_second):
            after = consolidate_routes(before)
        self.assertEqual(2, len(calls))
        self.assertEqual(0, after['consolidation']['accepted'])
        self.assertEqual(atomic(before), atomic(after))
        self.check_provenance(before, after)

    def test_label_memory_budget_retains_paths(self):
        before = fixture()
        with patch('metropogits.road_consolidation.MAX_SEARCH_LABELS', 1):
            after = consolidate_routes(before)
        self.assertTrue(after['consolidation']['limitReached'])
        self.assertGreater(after['consolidation']['searchLabelLimitHits'], 0)
        self.assertEqual(atomic(before), atomic(after))
        self.check_provenance(before, after)

    def test_input_order_and_repeat_are_deterministic(self):
        before = fixture()
        expected = canonical_json_bytes(consolidate_routes(before))
        before['routes'].reverse()
        before['segments'].reverse()
        self.assertEqual(expected, canonical_json_bytes(consolidate_routes(before)))

    def test_partial_and_resource_oversize_rejected(self):
        before = fixture()
        before['status'] = 'PARTIAL'
        with self.assertRaises(ValueError):
            consolidate_routes(before)
        with patch('metropogits.road_consolidation.MAX_ROUTE_STEPS', 3):
            with self.assertRaisesRegex(ValueError, 'route-step limit'):
                consolidate_routes(fixture())

    def test_full_package_shares_routes_and_keeps_canonical_city(self):
        graph = json.loads((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text(encoding='utf-8'))
        scene = generate_city(graph)
        original = canonical_json_bytes(scene)
        _, routing, report = compare(scene, graph)
        artifacts = package(scene, graph, routing, report)
        self.assertEqual(original, artifacts['city.json'])
        data = json.loads(artifacts['assets/viewer-data.js'].decode().split('=', 1)[1].rstrip(';\n'))
        self.assertEqual(routing, data['routing'])
        self.assertEqual(scene, data['scene'])
        self.assertIn(b'SHARED ROAD STUDY', artifacts['index.html'])
        self.assertEqual('visual-access/0.3', json.loads(artifacts['manifest.json'])['options']['routingVersion'])
        self.assertEqual(artifacts, package(scene, graph, routing, report))
