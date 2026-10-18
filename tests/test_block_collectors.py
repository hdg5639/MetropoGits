import copy
import unittest
from collections import defaultdict
from unittest.mock import patch

from metropogits.access_routes import derive_access_routes
from metropogits.block_collectors import _expand, _geometry_score, _rebuild, _tree, _tree_path, plan_collectors
from metropogits.access_routes import PITCH, _pair
from metropogits.road_consolidation import _bends
from scripts.canonical_json import canonical_json_bytes
from scripts.parcel_pilot import pavement_intersections
from scripts.road_metrics import road_metrics


def fixture():
    buildings = [dict(entityId=f'b{i}', districtId='d', x=x, z=z, width=2, depth=2)
                 for i, (x, z) in enumerate(((2,2),(16,2),(2,16),(16,16),(9,9),(9,2))) ]
    edges = [dict(id=f'e{i}-{j}', **{'from':f'b{i}', 'to':f'b{j}'})
             for i in range(6) for j in range(6) if i != j]
    scene = dict(buildings=buildings, districts=[dict(id='d', parentId=None,x=0,z=0,width=21,depth=21)],
                 networks=[dict(id='n',kind='DEPENDENCY_ROAD',edgeIds=[e['id'] for e in edges])])
    return scene, derive_access_routes(scene, dict(edges=edges))


class BlockCollectorTests(unittest.TestCase):
    def check_routes(self, scene, before, after):
        self.assertEqual(0, pavement_intersections(after, scene['buildings']))
        old = {r['id']:r for r in before['routes']}
        segments = {s['id']:s for s in after['segments']}
        memberships = {key:set() for key in segments}
        for route in after['routes']:
            base = old[route['id']]
            for key in ('id','kind','source','target','edgeIds','networkIds'):
                self.assertEqual(base[key],route[key])
            self.assertEqual((base['path'][0],base['path'][-1]), (route['path'][0],route['path'][-1]))
            self.assertLessEqual(route['latticeSteps'], max(base['latticeSteps']*3//2,base['latticeSteps']+4))
            self.assertLessEqual(_bends(route['path']),_bends(base['path'])+4)
            self.assertEqual(len(route['path'])-1,len(route['segmentIds']))
            for i,key in enumerate(route['segmentIds']):
                self.assertEqual(sorted(route['path'][i:i+2]), sorted([segments[key]['start'],segments[key]['end']]))
                memberships[key].add(route['id'])
        for key,members in memberships.items():
            self.assertTrue(members)
            self.assertEqual(members,set(segments[key]['routeIds']))

    def test_collectors_preserve_real_doors_evidence_width_and_original_bounds(self):
        scene, original = fixture()
        frozen = copy.deepcopy((scene,original))
        after = plan_collectors(scene, original, original)
        self.check_routes(scene, original, after)
        self.assertEqual(frozen,(scene,original))
        self.assertTrue(after['blockCollectors']['accepted'])
        self.assertLess(road_metrics(after)['pavementCenterlineLength'],road_metrics(original)['pavementCenterlineLength'])
        self.assertEqual(canonical_json_bytes(after),canonical_json_bytes(plan_collectors(scene,original,original)))

    def test_rebuild_and_expansion_roundtrip_preserves_memberships(self):
        scene, original = fixture()
        paths,widths = _expand(original)
        after = _rebuild(original,paths,widths)
        self.check_routes(scene,original,after)
        self.assertEqual(_expand(after),(paths,widths))

    def test_limit_retains_safe_paths_and_reports_truncation(self):
        scene, original = fixture()
        with patch('metropogits.block_collectors.MAX_STATES',0):
            after = plan_collectors(scene,original,original)
        self.assertTrue(after['blockCollectors']['limitReached'])
        self.assertFalse(after['blockCollectors']['accepted'])
        self.assertEqual(original['routes'],after['routes'])

    def test_invalid_bounds_or_changed_provenance_rejected(self):
        scene, original = fixture()
        bad = copy.deepcopy(original)
        bad['version'] = 'visual-access/0.3'
        with self.assertRaises(ValueError):
            plan_collectors(scene,bad,original)
        bad = copy.deepcopy(original)
        bad['routes'][0]['edgeIds'] = ['fabricated']
        with self.assertRaises(ValueError):
            plan_collectors(scene,original,bad)

    def test_empty_unknown_input_remains_empty(self):
        scene, original = fixture()
        original.update(routes=[],segments=[],junctions=[])
        after = plan_collectors(scene,original,original)
        self.assertEqual([],after['routes'])
        self.assertFalse(after['blockCollectors']['limitReached'])

    def test_disconnected_tree_does_not_invent_connector(self):
        graph = {(0,0):{(1,0)},(1,0):{(0,0)},(4,0):set()}
        self.assertIsNone(_tree(graph,[(0,0),(4,0)],(0,0),set(),[0]))

    def test_tree_path_preserves_endpoints_and_shares_real_segments(self):
        graph = {(x,z):{(a,b) for a,b in ((x-1,z),(x+1,z),(x,z-1),(x,z+1))
                         if 0 <= a <= 4 and 0 <= b <= 4} for x in range(5) for z in range(5)}
        terminals = [(0,0),(4,0),(4,4),(0,4),(2,2)]
        tree = _tree(graph,terminals,terminals[0],set(),[0])
        self.assertEqual(len(tree)-1,sum(map(len,tree.values()))//2)
        for a in terminals:
            for b in terminals:
                path = _tree_path(tree,a,b)
                self.assertEqual((a,b),(path[0],path[-1]))
                self.assertTrue(all(y in graph[x] for x,y in zip(path,path[1:])))

    def test_fast_geometry_guard_matches_independent_full_metrics(self):
        scene, original = fixture()
        for routing in (original,plan_collectors(scene,original,original)):
            paths,_ = _expand(routing)
            kinds = {r['id']:r['kind'] for r in routing['routes']}
            keys = {(kinds[r],_pair(a,b)) for r,p in paths.items() for a,b in zip(p,p[1:])}
            incidence = defaultdict(int)
            access_length = 0
            for segment in routing['segments']:
                if segment['access']:
                    access_length += sum(abs(a-b) for a,b in zip(segment['start'],segment['end']))
                    for point in (segment['start'],segment['end']):
                        incidence[segment['kind'],tuple(v/PITCH for v in point)] += 1
            length,junctions,parallel = _geometry_score(keys,incidence)
            metrics = road_metrics(routing)
            self.assertEqual(metrics['pavementCenterlineLength'],length*PITCH+access_length)
            self.assertEqual(metrics['junctions'],junctions)
            self.assertEqual(metrics['nearbyParallelPairLength'],parallel*PITCH)

    def test_semantic_networks_cannot_borrow_other_kind_roads(self):
        scene, original = fixture()
        other = copy.deepcopy(original)
        for route in other['routes']:
            route.update(id='http-'+route['id'],kind='HTTP_HIGHWAY',networkIds=['http'])
            route['segmentIds'] = ['http-'+s for s in route['segmentIds']]
        for segment in other['segments']:
            segment.update(id='http-'+segment['id'],kind='HTTP_HIGHWAY',routeIds=['http-'+r for r in segment['routeIds']])
        original['routes'] += other['routes']
        original['segments'] += other['segments']
        paths,widths = _expand(original)
        original = _rebuild(original,paths,widths)
        after = plan_collectors(scene,original,original)
        self.check_routes(scene,original,after)
        segments = {s['id']:s for s in after['segments']}
        for route in after['routes']:
            self.assertTrue(all(segments[s]['kind']==route['kind'] for s in route['segmentIds']))

    def test_geometry_limits_skip_block_without_losing_routes(self):
        scene, original = fixture()
        for cap in ('MAX_BLOCK_NODES','MAX_TERMINALS'):
            with patch('metropogits.block_collectors.'+cap,1):
                after = plan_collectors(scene,original,original)
            self.assertFalse(after['blockCollectors']['accepted'])
            self.check_routes(scene,original,after)

    def test_invalid_door_cannot_be_silently_replaced(self):
        scene, original = fixture()
        changed = copy.deepcopy(original)
        changed['routes'][0]['path'][0][0] += .1
        with self.assertRaises(ValueError):
            plan_collectors(scene,original,changed)
