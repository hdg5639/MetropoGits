import copy
import heapq
import unittest
from collections import defaultdict, deque
from contextlib import ExitStack
from unittest.mock import patch

from metropogits.access_routes import PITCH, _id, _pair
from metropogits.road_consolidation import _avenue_search, _bends, _bridge_keys, consolidate_routes
from scripts.canonical_json import canonical_json_bytes
import test_road_consolidation as baseline_tests
from test_road_consolidation import atomic


def routing_fixture(paths, kinds=None):
    segments, routes = {}, []
    for i, nodes in enumerate(paths):
        identity = f'r{i}'
        kind = kinds[i] if kinds else 'DEPENDENCY_ROAD'
        points = [[x*PITCH,z*PITCH] for x,z in nodes]
        ids = []
        for a,b in zip(points,points[1:]):
            start,end = sorted((a,b))
            key = _id('access-segment',[kind,start,end])
            segments.setdefault(key,dict(id=key,kind=kind,start=start,end=end,width=.5,
                                         access=False,routeIds=[]))['routeIds'].append(identity)
            ids.append(key)
        routes.append(dict(id=identity,kind=kind,source=f's{i}',target=f't{i}',edgeIds=[f'e{i}'],
                           networkIds=['n'],path=points,segmentIds=ids,latticeSteps=len(nodes)-1))
    return dict(version='visual-access/0.2',status='COMPLETE',routes=routes,
                segments=list(segments.values()),junctions=[],diagnostics=[],unresolvedEdgeIds=[],searchExpansions=0)


STAIRS = [(0,0),(1,0),(1,1),(2,1),(2,2),(3,2),(3,3)]
STRAIGHT = [(0,0),(1,0),(2,0),(3,0),(3,1),(3,2),(3,3)]
ELBOWS = [[(0,0),(1,0),(2,0),(3,0),(3,1)],[(0,0),(0,1),(1,1),(2,1),(3,1)]]


class RoadContinuityTests(unittest.TestCase):
    def cleanup(self, before, **limits):
        with ExitStack() as stack:
            for key in ('MAX_ATTEMPTS','MAX_JUNCTION_ATTEMPTS','MAX_AVENUE_ATTEMPTS','MAX_BACKBONE_ATTEMPTS'):
                stack.enter_context(patch('metropogits.road_consolidation.'+key,0))
            for key,value in limits.items():
                stack.enter_context(patch('metropogits.road_consolidation.'+key,value))
            return consolidate_routes(before,continuity=True)

    def check_routes(self,before,after):
        baseline_tests.RoadConsolidationTests().check_provenance(before,after,additional_bends=0)
        old = {r['id']:r for r in before['routes']}
        for route in after['routes']:
            n = old[route['id']]['latticeSteps']
            self.assertLessEqual(route['latticeSteps'],max(n*3//2,n+4))
        self.assertTrue(atomic(after) <= atomic(before))

    def test_alignment_removes_staircase_without_lengthening_or_new_bends(self):
        before = routing_fixture([STAIRS,STRAIGHT])
        original = copy.deepcopy(before)
        after = self.cleanup(before,MAX_CONTINUITY_ATTEMPTS=0)
        self.assertEqual(before,original)
        self.assertEqual(1,after['roadContinuity']['alignedRoutes'])
        self.assertEqual(6,after['roadContinuity']['bendsBefore'])
        self.assertEqual(2,after['roadContinuity']['bendsAfter'])
        self.assertTrue(atomic(after) < atomic(before))
        self.check_routes(before,after)
        self.assertTrue(all(r['latticeSteps']==6 for r in after['routes']))

    def test_reconsidered_cycle_removes_a_corridor_without_adding_turns(self):
        before = routing_fixture(ELBOWS)
        after = self.cleanup(before,MAX_ALIGNMENT_ATTEMPTS=0)
        self.assertEqual(1,after['roadContinuity']['accepted'])
        self.assertEqual(1,after['roadContinuity']['bridgeProtectedCorridors'])
        self.assertTrue(atomic(after) < atomic(before))
        self.check_routes(before,after)

    def test_alignment_and_cycle_search_cannot_cross_semantic_kinds(self):
        before = routing_fixture([STAIRS,STRAIGHT],['DEPENDENCY_ROAD','HTTP_HIGHWAY'])
        after = self.cleanup(before)
        self.assertEqual(atomic(before),atomic(after))
        self.assertEqual(0,after['roadContinuity']['candidates'])
        self.check_routes(before,after)

    def test_bridge_check_matches_independent_removal_connectivity(self):
        graph = defaultdict(lambda:defaultdict(set))
        for kind in ('DEPENDENCY_ROAD','HTTP_HIGHWAY'):
            edges = list(zip(STAIRS,STAIRS[1:]))+list(zip(STRAIGHT,STRAIGHT[1:]))
            edges += [((3,3),(4,3)),((8,0),(8,1))]
            if kind == 'HTTP_HIGHWAY':
                edges = list(zip(STAIRS,STAIRS[1:]))
            for a,b in edges:
                graph[kind][a].add(b)
                graph[kind][b].add(a)
        expected = set()
        for kind,nodes in graph.items():
            for a in nodes:
                for b in nodes[a]:
                    queue,seen = deque([a]),{a}
                    while queue:
                        point = queue.popleft()
                        for other in nodes[point]:
                            if _pair(point,other) != _pair(a,b) and other not in seen:
                                seen.add(other)
                                queue.append(other)
                    if b not in seen:
                        expected.add((kind,_pair(a,b)))
        self.assertEqual(expected,_bridge_keys(graph))
        # Long linear input must not exhaust recursion.
        long = defaultdict(lambda:defaultdict(set))
        for x in range(2500):
            long['DEPENDENCY_ROAD'][x,0].add((x+1,0))
            long['DEPENDENCY_ROAD'][x+1,0].add((x,0))
        self.assertEqual(2500,len(_bridge_keys(long)))

    def test_turn_cost_includes_entrance_and_exit_headings(self):
        graph = defaultdict(set)
        for path in ELBOWS:
            for a,b in zip(path,path[1:]):
                graph[a].add(b)
                graph[b].add(a)
        for path,heading,terminal in [(ELBOWS[0],(1,0),(0,1)),(ELBOWS[1],(0,1),(1,0))]:
            actual = _avenue_search((0,0),(3,1),graph,set(),4,heading,terminal,3,[0,0],set(),turn_penalty=200)
            self.assertEqual(path,actual)

    def test_atomic_cycle_failure_does_not_install_partial_replacements(self):
        before = routing_fixture([*ELBOWS,*ELBOWS])
        calls = []
        def fail_alternate(*args,**kwargs):
            calls.append(1)
            return _avenue_search(*args,**kwargs) if len(calls)%2 else None
        with patch('metropogits.road_consolidation._avenue_search',side_effect=fail_alternate):
            after = self.cleanup(before,MAX_ALIGNMENT_ATTEMPTS=0)
        self.assertEqual(4,len(calls))
        self.assertEqual(0,after['roadContinuity']['accepted'])
        self.assertEqual(atomic(before),atomic(after))
        self.check_routes(before,after)

    def test_turn_weighted_search_matches_independent_bounded_dijkstra(self):
        graph = defaultdict(set)
        for x in range(4):
            for z in range(4):
                for other in ((x+1,z),(x,z+1)):
                    if other[0]<4 and other[1]<4 and (x,z)!=(1,1) and other!=(1,1):
                        graph[x,z].add(other)
                        graph[other].add((x,z))
        start,end = (0,0),(3,3)
        for limit,bound,heading,terminal in [(6,1,(0,0),(0,0)),(8,3,(1,0),(1,0)),(8,2,(0,1),(0,-1))]:
            queue,seen,optimum = [(0,start,heading,0,0)],set(),None
            while queue:
                cost,point,direction,steps,bends = heapq.heappop(queue)
                state = point,direction,steps,bends
                if state in seen:
                    continue
                seen.add(state)
                if point==end:
                    if bends+int(terminal!=(0,0) and direction!=terminal)<=bound:
                        optimum=cost
                        break
                    continue
                for other in graph[point]:
                    ndirection=other[0]-point[0],other[1]-point[1]
                    nbends=bends+int(direction!=(0,0) and direction!=ndirection)
                    if steps<limit and nbends<=bound:
                        ncost=cost+100+200*(nbends-bends)
                        if other==end and terminal!=(0,0) and ndirection!=terminal:
                            ncost+=200
                        heapq.heappush(queue,(ncost,other,ndirection,steps+1,nbends))
            path=_avenue_search(start,end,graph,set(),limit,heading,terminal,bound,[0,0],set(),turn_penalty=200)
            actual=None
            if path:
                first=(path[1][0]-path[0][0],path[1][1]-path[0][1])
                last=(path[-1][0]-path[-2][0],path[-1][1]-path[-2][1])
                bends=_bends(path)+int(heading!=(0,0) and heading!=first)+int(terminal!=(0,0) and terminal!=last)
                actual=(len(path)-1)*100+200*bends
            self.assertEqual(optimum,actual)

    def test_resource_limits_retain_safe_complete_paths(self):
        before = routing_fixture([STAIRS,STRAIGHT])
        for key,value in [('MAX_SEARCH_STATES',1),('MAX_SEARCH_LABELS',1)]:
            after = self.cleanup(before,**{key:value})
            self.assertTrue(after['roadContinuity']['limitReached'])
            self.assertEqual(atomic(before),atomic(after))
            self.check_routes(before,after)

    def test_determinism_and_legacy_routing_remains_separate(self):
        before = routing_fixture([STAIRS,STRAIGHT,*ELBOWS])
        after = consolidate_routes(before,continuity=True)
        legacy = consolidate_routes(before,urban=True)
        self.assertNotIn('roadContinuity',legacy)
        self.assertLessEqual(sum(_bends(r['path']) for r in after['routes']),
                             sum(_bends(r['path']) for r in legacy['routes']))
        before['routes'].reverse()
        before['segments'].reverse()
        for s in before['segments']:
            s['routeIds'].reverse()
        self.assertEqual(canonical_json_bytes(after),canonical_json_bytes(consolidate_routes(before,continuity=True)))
        with self.assertRaisesRegex(ValueError,'complete visual-access/0.2'):
            consolidate_routes(after,continuity=True)
