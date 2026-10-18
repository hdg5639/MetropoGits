import copy
import unittest
from unittest.mock import patch

from metropogits.access_routes import derive_access_routes
from metropogits.block_collectors import _expand
from metropogits.block_gateways import _fan, _groups, plan_gateways
from scripts.canonical_json import canonical_json_bytes
from scripts.road_metrics import road_metrics
import test_block_collectors as collectors
import test_road_frontage as frontage_tests
from metropogits.road_frontage import plan_frontages


def fixture():
    scene,routing = collectors.fixture()
    scene['districts'][0]['width'] = 14
    scene['districts'].append(dict(id='right',parentId=None,x=14,z=0,width=7,depth=21))
    for building in scene['buildings']:
        if building['x'] > 14:
            building['districtId'] = 'right'
    return scene,routing


class BlockGatewayTests(unittest.TestCase):
    def test_joint_gateway_keeps_all_sources_doors_and_original_budgets(self):
        scene,original = fixture()
        frozen = copy.deepcopy((scene,original))
        after = plan_gateways(scene,original,original)
        collectors.BlockCollectorTests().check_routes(scene,original,after)
        self.assertEqual(frozen,(scene,original))
        groups = after['blockGateways']['accepted']
        self.assertTrue(groups)
        self.assertTrue(all(g['crossingsBefore'] > g['crossingsAfter'] for g in groups))
        self.assertTrue(any(g['changedRoutes'] >= 2 for g in groups))
        self.assertTrue(any(g['retainedRoutes'] for g in groups))
        before_metrics,after_metrics = road_metrics(original),road_metrics(after)
        self.assertLess(after_metrics['pavementCenterlineLength'],before_metrics['pavementCenterlineLength'])
        for key in ('junctions','nearbyParallelPairLength','turns'):
            self.assertLessEqual(after_metrics[key],before_metrics[key])

    def test_repeatability_and_input_order(self):
        scene,original = fixture()
        after = plan_gateways(scene,original,original)
        shuffled_scene,shuffled_routes = copy.deepcopy((scene,original))
        shuffled_scene['buildings'].reverse()
        shuffled_scene['districts'].reverse()
        # Public routes are canonically ordered; geometry is independent of scene order.
        self.assertEqual(canonical_json_bytes(after),canonical_json_bytes(plan_gateways(shuffled_scene,original,shuffled_routes)))
        self.assertEqual(canonical_json_bytes(after),canonical_json_bytes(plan_gateways(scene,original,original)))

    def test_changed_frontage_keeps_original_world_budget_not_new_port_budget(self):
        scene,original = fixture()
        frontage = plan_frontages(scene,original,original)
        self.assertTrue(frontage['roadFrontage']['accepted'])
        after = plan_gateways(scene,original,frontage)
        frontage_tests.RoadFrontageTests().check(scene,original,after)
        old = {r['id']:r for r in frontage['routes']}
        for route in after['routes']:
            self.assertEqual([route['path'][i] for i in (0,-1)],
                             [old[route['id']]['path'][i] for i in (0,-1)])

    def test_unreachable_gateway_retains_whole_old_geometry(self):
        scene,original = fixture()
        with patch('metropogits.block_gateways._fan',return_value={}):
            after = plan_gateways(scene,original,original)
        self.assertFalse(after['blockGateways']['accepted'])
        self.assertEqual(_expand(original),_expand(after))
        collectors.BlockCollectorTests().check_routes(scene,original,after)

    def test_resource_limits_leave_complete_routes(self):
        scene,original = fixture()
        for constant in ('MAX_STATES','MAX_PROPOSALS','MAX_DISTRICTS','MAX_PATCHES'):
            with self.subTest(constant=constant), patch('metropogits.block_gateways.'+constant,0):
                after = plan_gateways(scene,original,original)
                self.assertTrue(after['blockGateways']['limitReached'])
                self.assertFalse(after['blockGateways']['accepted'])
                self.assertEqual(_expand(original),_expand(after))

    def test_one_proposal_never_partially_applies_invalid_paths(self):
        scene,original = fixture()
        with patch('metropogits.block_gateways.MAX_PROPOSALS',1):
            after = plan_gateways(scene,original,original)
        self.assertTrue(after['blockGateways']['limitReached'])
        collectors.BlockCollectorTests().check_routes(scene,original,after)

    def test_unknown_and_sparse_fallback(self):
        scene,original = fixture()
        original.update(routes=[],segments=[],junctions=[])
        after = plan_gateways(scene,original,original)
        self.assertEqual([],after['routes'])
        self.assertEqual([],after['segments'])
        self.assertFalse(after['blockGateways']['accepted'])

    def test_provenance_and_repeated_pass_are_rejected(self):
        scene,original = fixture()
        bad = copy.deepcopy(original)
        bad['routes'][0]['edgeIds'] = ['fabricated']
        with self.assertRaises(ValueError):
            plan_gateways(scene,original,bad)
        bad = plan_gateways(scene,original,original)
        with self.assertRaises(ValueError):
            plan_gateways(scene,original,bad)
        with self.assertRaises(ValueError):
            plan_gateways(scene,bad,original)

    def test_grouping_separates_opposite_boundary_normals(self):
        forward = [((0,0),(1,0)),((0,2),(1,2))]
        reverse = [((1,0),(0,0)),((1,2),(0,2))]
        groups = list(_groups(forward+reverse,{e:1 for e in forward+reverse}))
        self.assertTrue(groups)
        self.assertTrue(all(set(g).issubset(forward) or set(g).issubset(reverse) for g in groups))

    def test_semantic_kinds_do_not_share_route_memberships(self):
        scene,_ = fixture()
        edges = [dict(id=f'e{i}-{j}',**{'from':f'b{i}','to':f'b{j}'}) for i in range(6) for j in range(6) if i != j]
        scene['networks'] = [dict(id='a',kind='DEPENDENCY_ROAD',edgeIds=[e['id'] for e in edges[:15]]),
                             dict(id='b',kind='MESSAGING_PATH',edgeIds=[e['id'] for e in edges[15:]])]
        original = derive_access_routes(scene,dict(edges=edges))
        after = plan_gateways(scene,original,original)
        collectors.BlockCollectorTests().check_routes(scene,original,after)
        routes = {r['id']:r for r in after['routes']}
        for segment in after['segments']:
            self.assertTrue(all(routes[r]['kind'] == segment['kind'] for r in segment['routeIds']))

    def test_fan_paths_are_simple_and_use_only_graph_edges(self):
        graph = {(x,z):{(a,b) for a,b in ((x-1,z),(x+1,z),(x,z-1),(x,z+1))
                        if 0 <= a <= 3 and 0 <= b <= 3} for x in range(4) for z in range(4)}
        fan = _fan(graph,(0,0),(1,0),[0])
        self.assertEqual(set(graph),set(fan))
        for destination,paths in fan.items():
            for _,path in paths:
                self.assertEqual((0,0),path[0])
                self.assertEqual(destination,path[-1])
                self.assertEqual(len(path),len(set(path)))
                self.assertTrue(all(b in graph[a] for a,b in zip(path,path[1:])))


if __name__ == '__main__':
    unittest.main()
