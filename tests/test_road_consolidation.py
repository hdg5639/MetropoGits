import copy
import heapq
import json
import unittest
from collections import defaultdict, deque
from pathlib import Path
from unittest.mock import patch

from metropogits.access_routes import PITCH, _id, _pair
from metropogits.layout import generate_city
from metropogits.road_consolidation import _avenue_search, _avenue_spines, _bends, _junction_links, _search, consolidate_routes
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


def avenue_fixture(length=40, separate_kinds=False):
    result = fixture(length, separate_kinds)
    for i in range(4):
        route = copy.deepcopy(result['routes'][0])
        route.update(id=f'avenue{i}', source=f'as{i}', target=f'at{i}', edgeIds=[f'ae{i}-{j}' for j in range(6)])
        result['routes'].append(route)
        for segment in result['segments']:
            if 'r0' in segment['routeIds']:
                segment['routeIds'].append(route['id'])
    return result


def junction_fixture(short_route=False, separate_kinds=False, separation=2):
    paths = [[(x, 0) for x in range(41)], [(x, 1) for x in range(41)],
             [(x, 0) for x in range(21)] + [(x, 1) for x in range(20, 41)],
             [(x, 1) for x in range(21+separation)] + [(x, 0) for x in range(20+separation, 41)]]
    if short_route:
        paths.append([(19, 0), (20, 0), (20, 1), (21, 1)])
    segments, routes = {}, []
    for i, nodes in enumerate(paths):
        kind = 'HTTP_HIGHWAY' if separate_kinds and i == 3 else 'DEPENDENCY_ROAD'
        points = [[x*PITCH, z*PITCH] for x, z in nodes]
        ids = []
        for a, b in zip(points, points[1:]):
            start, end = sorted((a, b))
            key = _id('access-segment', [kind, start, end])
            segments.setdefault(key, dict(id=key, kind=kind, start=start, end=end,
                                          width=.5, access=False, routeIds=[]))['routeIds'].append(f'r{i}')
            ids.append(key)
        routes.append(dict(id=f'r{i}', kind=kind, source=f's{i}', target=f't{i}',
                           edgeIds=[f'e{i}'], networkIds=['n'], path=points, segmentIds=ids, latticeSteps=len(nodes)-1))
    return dict(version='visual-access/0.2', status='COMPLETE', routes=routes,
                segments=list(segments.values()), junctions=[], diagnostics=[], unresolvedEdgeIds=[], searchExpansions=0)


class RoadConsolidationTests(unittest.TestCase):
    def avenue_only(self, routing):
        with patch('metropogits.road_consolidation.MAX_ATTEMPTS', 0), patch('metropogits.road_consolidation.MAX_JUNCTION_ATTEMPTS', 0):
            return consolidate_routes(routing, merge_junctions=True, avenues=True)

    def test_avenue_reuses_continuous_high_demand_road_with_real_detour(self):
        before = avenue_fixture()
        original = copy.deepcopy(before)
        after = self.avenue_only(before)
        decision = after['avenueConsolidation']
        self.assertEqual(before, original)
        self.assertEqual(1, len(decision['spines']))
        self.assertEqual([[0, 0], [140, 0]], decision['spines'][0]['path'])
        self.assertEqual(1, decision['accepted'])
        self.assertGreater(decision['avenueRouteStepsAfter'], decision['avenueRouteStepsBefore'])
        self.assertTrue(atomic(after) < atomic(before))
        self.assertEqual(42, next(r for r in after['routes'] if r['id'] == 'r1')['latticeSteps'])
        self.check_provenance(before, after)

    def test_avenue_does_not_invent_demand_or_cross_semantic_kinds(self):
        low = self.avenue_only(fixture())
        self.assertEqual([], low['avenueConsolidation']['spines'])
        self.assertEqual(atomic(fixture()), atomic(low))
        other = avenue_fixture(separate_kinds=True)
        after = self.avenue_only(other)
        self.assertEqual(0, after['avenueConsolidation']['accepted'])
        self.assertEqual(atomic(other), atomic(after))

    def test_avenue_limits_and_atomic_rollback(self):
        short = avenue_fixture(length=10)
        after = self.avenue_only(short)
        self.assertEqual(atomic(short), atomic(after))
        self.assertEqual(0, after['avenueConsolidation']['accepted'])
        before = avenue_fixture()
        for option, limit in [('MAX_AVENUE_ATTEMPTS', 0), ('MAX_SEARCH_STATES', 1), ('MAX_SEARCH_LABELS', 1)]:
            with patch('metropogits.road_consolidation.'+option, limit):
                after = self.avenue_only(before)
            self.assertEqual(atomic(before), atomic(after))
            self.assertTrue(after['avenueConsolidation']['limitReached'])
            self.check_provenance(before, after)

    def test_avenue_search_prefers_longer_shared_path_without_exceeding_bounds(self):
        # A preference is not an unconditional command to use the avenue.
        paths = [[(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)],
                 [(0, 0), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (4, 0)]]
        graph = defaultdict(set)
        for path in paths:
            for a, b in zip(path, path[1:]):
                graph[a].add(b)
                graph[b].add(a)
        preferred = {_pair(a, b) for a, b in zip(paths[1], paths[1][1:])}
        # Shorter still wins here (400 < 480), so preference cannot mean forced detour.
        actual = _avenue_search((0,0), (4,0), graph, set(), 6, (0,0), (0,0), 2, [0,0], preferred)
        self.assertEqual(paths[0], actual)
        blocked = {_pair((1,0), (2,0))}
        self.assertIsNone(_avenue_search((0,0), (4,0), graph, blocked, 5, (0,0), (0,0), 2, [0,0], preferred))
        self.assertEqual(paths[1], _avenue_search((0,0), (4,0), graph, blocked, 6, (0,0), (0,0), 2, [0,0], preferred))

        direct = [(x,0) for x in range(21)]
        detour = [(0,0), *[(x,1) for x in range(21)], (20,0)]
        graph = defaultdict(set)
        for path in [direct, detour]:
            for a, b in zip(path, path[1:]):
                graph[a].add(b)
                graph[b].add(a)
        preferred = {_pair(a,b) for a,b in zip(detour,detour[1:])}
        self.assertEqual(detour, _avenue_search((0,0), (20,0), graph, set(), 22, (0,0), (0,0), 2, [0,0], preferred))
        self.assertEqual(direct, _avenue_search((0,0), (20,0), graph, set(), 21, (0,0), (0,0), 2, [0,0], preferred))

    def test_avenue_search_matches_independent_bounded_dijkstra(self):
        graph = defaultdict(set)
        for x in range(5):
            for z in range(4):
                for other in [(x+1,z),(x,z+1)]:
                    if other[0] < 5 and other[1] < 4 and other != (2,2) and (x,z) != (2,2):
                        graph[x,z].add(other)
                        graph[other].add((x,z))
        preferred = {_pair(a,b) for a in graph for b in graph[a] if a[1] == b[1] == 1}
        start, end = (0,0), (4,3)
        for limit, bend_limit, heading, terminal in [(7,1,(0,0),(0,0)), (9,3,(0,1),(1,0)), (9,2,(1,0),(0,-1))]:
            queue, seen, optimum = [(0,start,heading,0,0)], set(), None
            while queue:
                cost, point, direction, steps, bends = heapq.heappop(queue)
                state = point, direction, steps, bends
                if state in seen:
                    continue
                seen.add(state)
                if point == end and bends + int(terminal != (0,0) and direction != terminal) <= bend_limit:
                    optimum = cost
                    break
                for other in graph[point]:
                    ndirection = other[0]-point[0], other[1]-point[1]
                    nbends = bends+int(direction != (0,0) and direction != ndirection)
                    if steps < limit and nbends <= bend_limit:
                        heapq.heappush(queue,(cost+(80 if _pair(point,other) in preferred else 100),other,ndirection,steps+1,nbends))
            path = _avenue_search(start,end,graph,set(),limit,heading,terminal,bend_limit,[0,0],preferred)
            actual = sum(80 if _pair(a,b) in preferred else 100 for a,b in zip(path,path[1:])) if path else None
            self.assertEqual(optimum,actual)

    def test_avenue_multi_route_failure_rolls_back_every_path(self):
        before = avenue_fixture()
        duplicate = copy.deepcopy(before['routes'][1])
        duplicate.update(id='r1copy', source='s1copy', edgeIds=['e1copy'])
        before['routes'].append(duplicate)
        for s in before['segments']:
            if 'r1' in s['routeIds']:
                s['routeIds'].append('r1copy')
        calls = []
        def fail_second(*args):
            calls.append(1)
            return _avenue_search(*args) if len(calls) == 1 else None
        with patch('metropogits.road_consolidation._avenue_search', side_effect=fail_second):
            after = self.avenue_only(before)
        self.assertEqual(2, len(calls))
        self.assertEqual(0, after['avenueConsolidation']['accepted'])
        self.assertEqual(atomic(before), atomic(after))
        self.check_provenance(before,after)

    def test_avenue_spines_require_contiguous_length_and_distinct_files(self):
        routes = {str(i): dict(edgeIds=['same']*50, source=f's{i}', target=f't{i}') for i in range(4)}
        users = {('DEPENDENCY_ROAD', _pair((x,0),(x+1,0))): set(routes) for x in [0,1,2,4,5,6]}
        self.assertEqual((set(), []), _avenue_spines(users, routes))
        for i, route in routes.items():
            route['edgeIds'] = [f'{i}-{j}' for j in range(6)]
        self.assertEqual((set(), []), _avenue_spines(users, routes))
        users[('DEPENDENCY_ROAD', _pair((3,0),(4,0)))] = set(routes)
        preferred, spines = _avenue_spines(users, routes)
        self.assertEqual(7, len(preferred))
        self.assertEqual(1, len(spines))

    def test_avenue_determinism_frozen_bounds_and_package(self):
        before = avenue_fixture()
        expected = canonical_json_bytes(self.avenue_only(before))
        before['routes'].reverse()
        before['segments'].reverse()
        for s in before['segments']:
            s['routeIds'].reverse()
        self.assertEqual(expected, canonical_json_bytes(self.avenue_only(before)))
        with self.assertRaisesRegex(ValueError, 'junction consolidation first'):
            consolidate_routes(before, avenues=True)
        with self.assertRaisesRegex(ValueError, 'complete visual-access/0.2'):
            self.avenue_only(self.avenue_only(before))
        graph = json.loads((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text(encoding='utf-8'))
        scene = generate_city(graph)
        baseline, routing, report = compare(scene, graph, avenues=True)
        self.assertNotIn('avenueConsolidation', baseline)
        self.assertIn('avenueConsolidation', report)
        self.assertEqual(canonical_json_bytes(scene), package(scene, graph, routing, report)['city.json'])

    def test_short_junction_links_reassign_routes_to_remaining_crossing(self):
        before = junction_fixture()
        with patch('metropogits.road_consolidation.MAX_ATTEMPTS', 0):
            after = consolidate_routes(before, merge_junctions=True)
        self.assertGreater(after['junctionConsolidation']['accepted'], 0)
        self.assertLess(len(after['junctions']), 4)
        self.assertTrue(atomic(after) < atomic(before))
        self.check_provenance(before, after)
        for route in after['routes']:
            a, b = [tuple(v/PITCH for v in p) for p in (route['path'][0], route['path'][-1])]
            bound = int((abs(a[0]-b[0])+abs(a[1]-b[1]))*100//90)
            self.assertLessEqual(route['latticeSteps'], bound)

    def test_junction_short_dependency_protects_link_from_excessive_detour(self):
        before = junction_fixture(short_route=True)
        with patch('metropogits.road_consolidation.MAX_ATTEMPTS', 0):
            after = consolidate_routes(before, merge_junctions=True)
        self.assertIn(('DEPENDENCY_ROAD', _pair((20, 0), (20, 1))), atomic(after))
        self.check_provenance(before, after)
        self.assertEqual(3, next(r for r in after['routes'] if r['id'] == 'r4')['latticeSteps'])

    def test_junction_pass_cannot_reuse_other_kind(self):
        before = junction_fixture(separate_kinds=True)
        with patch('metropogits.road_consolidation.MAX_ATTEMPTS', 0):
            after = consolidate_routes(before, merge_junctions=True)
        self.assertEqual(0, after['junctionConsolidation']['accepted'])
        self.assertEqual(atomic(before), atomic(after))
        self.check_provenance(before, after)

    def test_junction_candidates_exclude_fixed_ports_and_long_links(self):
        source = junction_fixture()
        adjacency, users = defaultdict(lambda: defaultdict(set)), {}
        for key in atomic(source):
            kind, (a, b) = key
            adjacency[kind][a].add(b)
            adjacency[kind][b].add(a)
            users[key] = {'r'}
        links = _junction_links(adjacency, set(), users)
        self.assertTrue(links)
        self.assertTrue(all(len(link[2]) <= 2 for link in links))
        ports = {('DEPENDENCY_ROAD', (x, z)) for x in (20, 22) for z in (0, 1)}
        self.assertEqual([], _junction_links(adjacency, ports, users))
        with patch('metropogits.road_consolidation.MAX_JUNCTION_LINK_STEPS', 1):
            self.assertTrue(all(len(link[2]) == 1 for link in _junction_links(adjacency, set(), users)))
        adjacency, users = defaultdict(lambda: defaultdict(set)), {}
        for key in atomic(junction_fixture(separation=5)):
            kind, (a, b) = key
            adjacency[kind][a].add(b)
            adjacency[kind][b].add(a)
            users[key] = {'r'}
        # Five-step links between crossings are not silently truncated into candidates.
        self.assertTrue(all(len(link[2]) == 1 for link in _junction_links(adjacency, set(), users)))

    def test_junction_multi_route_failure_rolls_back_all_replacements(self):
        before = junction_fixture()
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
        with patch('metropogits.road_consolidation.MAX_ATTEMPTS', 0), patch('metropogits.road_consolidation.MAX_JUNCTION_ATTEMPTS', 1), patch('metropogits.road_consolidation._search', side_effect=fail_second):
            after = consolidate_routes(before, merge_junctions=True)
        self.assertEqual(2, len(calls))
        self.assertEqual(0, after['junctionConsolidation']['accepted'])
        self.assertEqual(atomic(before), atomic(after))
        self.check_provenance(before, after)

    def test_junction_budgets_preserve_atomic_routes_and_original_limits(self):
        before = junction_fixture()
        for option, limit in [('MAX_JUNCTION_ATTEMPTS', 0), ('MAX_SEARCH_STATES', 1), ('MAX_SEARCH_LABELS', 1)]:
            with patch('metropogits.road_consolidation.MAX_ATTEMPTS', 0), patch('metropogits.road_consolidation.'+option, limit):
                after = consolidate_routes(before, merge_junctions=True)
            self.assertEqual(atomic(before), atomic(after))
            self.check_provenance(before, after)
        # Both stages share limits frozen from the original 0.2 routes.
        after = consolidate_routes(before, merge_junctions=True)
        self.check_provenance(before, after)
        with self.assertRaisesRegex(ValueError, 'complete visual-access/0.2'):
            consolidate_routes(after, merge_junctions=True)

    def test_junction_opt_in_determinism_and_package_compatibility(self):
        before = junction_fixture()
        expected = canonical_json_bytes(consolidate_routes(before, merge_junctions=True))
        before['routes'].reverse()
        before['segments'].reverse()
        self.assertEqual(expected, canonical_json_bytes(consolidate_routes(before, merge_junctions=True)))
        self.assertNotIn('junctionConsolidation', consolidate_routes(before))
        graph = json.loads((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text(encoding='utf-8'))
        scene = generate_city(graph)
        baseline, routing, report = compare(scene, graph, merge_junctions=True)
        self.assertEqual('visual-access/0.3', baseline['version'])
        self.assertIn('junctionConsolidation', report)
        artifacts = package(scene, graph, routing, report)
        data = json.loads(artifacts['assets/viewer-data.js'].decode().split('=', 1)[1].rstrip(';\n'))
        self.assertEqual(routing, data['routing'])
        self.assertEqual(canonical_json_bytes(scene), artifacts['city.json'])

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
