import copy
import unittest
from unittest.mock import patch

from metropogits.access_routes import AccessGrid, PITCH, _pair
from metropogits.block_collectors import _expand
from metropogits.road_frontage import _approaches, _doors, _surface, plan_frontages
from metropogits.road_consolidation import _bends
from scripts.canonical_json import canonical_json_bytes
from scripts.parcel_pilot import pavement_intersections
from scripts.road_metrics import road_metrics
from test_block_collectors import fixture


def length(points):
    return sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(points,points[1:]))


class RoadFrontageTests(unittest.TestCase):
    def check(self,scene,original,after):
        self.assertEqual(0,pavement_intersections(after,scene['buildings']))
        old = {r['id']:r for r in original['routes']}
        buildings = {b['entityId']:b for b in scene['buildings']}
        segments = {s['id']:s for s in after['segments']}
        doors = {}
        memberships = {key:set() for key in segments}
        for route in after['routes']:
            base = old[route['id']]
            for key in ('id','kind','source','target','edgeIds','networkIds'):
                self.assertEqual(base[key],route[key])
            for entity,index in ((route['source'],0),(route['target'],-1)):
                door = route['path'][index]
                if entity in doors:
                    self.assertEqual(doors[entity],door)
                doors[entity] = door
                b = buildings[entity]
                self.assertTrue(b['x'] <= door[0] <= b['x']+b['width'])
                self.assertTrue(b['z'] <= door[1] <= b['z']+b['depth'])
                self.assertTrue(door[0] in (b['x'],b['x']+b['width']) or door[1] in (b['z'],b['z']+b['depth']))
            n = base['latticeSteps']
            self.assertLessEqual(length(route['path']),max(n*3//2,n+4)*PITCH+length(base['path'])-n*PITCH)
            self.assertLessEqual(_bends(route['path']),_bends(base['path'])+4)
            self.assertEqual(len(route['path'])-1,len(route['segmentIds']))
            for i,key in enumerate(route['segmentIds']):
                self.assertEqual(sorted(route['path'][i:i+2]),sorted([segments[key]['start'],segments[key]['end']]))
                memberships[key].add(route['id'])
        self.assertEqual(set(old),{r['id'] for r in after['routes']})
        for key,members in memberships.items():
            self.assertTrue(members)
            self.assertEqual(sorted(members),segments[key]['routeIds'])

    def test_shared_collector_precedes_consistent_door_reorientation(self):
        scene,original = fixture()
        frozen = copy.deepcopy((scene,original))
        after = plan_frontages(scene,original,original)
        self.assertTrue(after['roadFrontage']['accepted'])
        self.check(scene,original,after)
        self.assertEqual(frozen,(scene,original))
        before_metrics,after_metrics = road_metrics(original),road_metrics(after)
        self.assertLess(after_metrics['pavementCenterlineLength'],before_metrics['pavementCenterlineLength'])
        self.assertLess(after_metrics['turns'],before_metrics['turns'])
        self.assertEqual(canonical_json_bytes(after),canonical_json_bytes(plan_frontages(scene,original,original)))

    def test_failed_candidate_rolls_back_all_incident_relations(self):
        scene,original = fixture()
        with patch('metropogits.road_frontage._approaches',return_value={}):
            after = plan_frontages(scene,original,original)
        self.assertFalse(after['roadFrontage']['accepted'])
        self.check(scene,original,after)
        self.assertEqual(_expand(original),_expand(after))
        self.assertTrue(after['roadFrontage']['rejected']['incident_route_bounds_or_connectivity'])

    def test_budget_exhaustion_keeps_every_relation_and_reports_limit(self):
        scene,original = fixture()
        with patch('metropogits.road_frontage.MAX_STATES',0):
            after = plan_frontages(scene,original,original)
        self.assertTrue(after['roadFrontage']['limitReached'])
        self.assertFalse(after['roadFrontage']['accepted'])
        self.check(scene,original,after)

    def test_unknown_and_isolated_files_do_not_receive_roads(self):
        scene,original = fixture()
        original.update(routes=[],segments=[],junctions=[])
        after = plan_frontages(scene,original,original)
        self.assertEqual([],after['routes'])
        self.assertEqual([],after['segments'])

    def test_frontage_pass_cannot_compound_or_change_provenance(self):
        scene,original = fixture()
        after = plan_frontages(scene,original,original)
        with self.assertRaises(ValueError):
            plan_frontages(scene,original,after)
        bad = copy.deepcopy(original)
        bad['routes'][0]['edgeIds'] = ['fake']
        with self.assertRaises(ValueError):
            plan_frontages(scene,original,bad)

    def test_approaches_must_actually_touch_reserved_collector(self):
        graph = {(0,0):{(1,0)},(1,0):{(0,0),(2,0)},(2,0):{(1,0)}}
        paths = _approaches((0,0),(0,0),{(2,0)},graph,set(),[0])
        self.assertTrue(paths)
        self.assertTrue(all((2,0) in run for choices in paths.values() for _,run in choices))
        self.assertFalse(_approaches((0,0),(0,0),{(4,0)},graph,set(),[0]))

    def test_neighbor_building_blocks_entrance_face(self):
        building = dict(entityId='b',x=2,z=2,width=2,depth=2)
        blocker = dict(entityId='wall',x=4,z=0,width=4,depth=7)
        doors = _doors(AccessGrid([building,blocker]),building)
        self.assertTrue(doors)
        self.assertTrue(all(door[0] != 4 for _,door in doors))

    def test_surface_guard_counts_changed_access_and_zero_through_routes(self):
        scene,original = fixture()
        for routing in (original,plan_frontages(scene,original,original)):
            paths,_ = _expand(routing)
            routes = {r['id']:r for r in routing['routes']}
            segments = {s['id']:s for s in routing['segments']}
            doors,fixed = {},set()
            for identity,route in routes.items():
                if identity not in paths:
                    for sid in route['segmentIds']:
                        s = segments[sid]
                        fixed.add((s['kind'],*_pair(tuple(s['start']),tuple(s['end']))))
                else:
                    for entity,index in ((route['source'],0),(route['target'],-1)):
                        doors[route['kind'],entity] = route['kind'],tuple(route['path'][index]),paths[identity][index]
            score,_ = _surface(paths,routes,doors,fixed)
            metrics = road_metrics(routing)
            self.assertEqual((metrics['pavementCenterlineLength'],metrics['junctions'],metrics['nearbyParallelPairLength']),
                             (score[0],score[1],score[2]*PITCH))

    def test_scene_input_order_does_not_change_planned_frontages(self):
        scene,original = fixture()
        reordered = copy.deepcopy(scene)
        reordered['buildings'].reverse()
        reordered['districts'].reverse()
        self.assertEqual(canonical_json_bytes(plan_frontages(scene,original,original)),
                         canonical_json_bytes(plan_frontages(reordered,original,original)))

    def test_candidate_limit_does_not_partially_move_incident_routes(self):
        scene,original = fixture()
        with patch('metropogits.road_frontage.MAX_CANDIDATES',1):
            after = plan_frontages(scene,original,original)
        self.assertEqual(1,after['roadFrontage']['attempts'])
        self.assertTrue(after['roadFrontage']['limitReached'])
        self.check(scene,original,after)

    def test_local_approach_step_limit_is_enforced_on_reconstructed_paths(self):
        graph = {(x,z):{(a,b) for a,b in ((x-1,z),(x+1,z),(x,z-1),(x,z+1))
                         if 0 <= a <= 4 and 0 <= b <= 4} for x in range(5) for z in range(5)}
        with patch('metropogits.road_frontage.MAX_APPROACH_STEPS',3):
            paths = _approaches((0,0),(0,0),{(1,0)},graph,set(),[0])
        self.assertTrue(paths)
        self.assertTrue(all(len(run)-1 <= 3 for choices in paths.values() for _,run in choices))
