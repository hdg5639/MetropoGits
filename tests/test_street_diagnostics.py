import random
import unittest
from collections import deque
from unittest.mock import patch

from metropogits.shared_frontage import _compress
from metropogits.street_diagnostics import distance_within, explain_failure
from metropogits.structural_streets import _adjacency, assign_streets
from test_block_collectors import fixture


class StreetDiagnosticTests(unittest.TestCase):
    def test_distance_proof_and_joint_constraint_are_distinct(self):
        a,b,c = (0,0),(1,0),(1,1)
        adjacency = _adjacency({(a,b),(b,c)})
        graph = _compress(adjacency,{a,c})
        components = dict.fromkeys(adjacency,0)
        self.assertEqual('distance_limit',explain_failure(graph,components,a,c,1,[0])['reason'])
        result = explain_failure(graph,components,a,c,2,[0])
        self.assertEqual('joint_constraints',result['reason'])
        self.assertEqual(2,result['shortestLatticeSteps'])
        self.assertEqual(0,distance_within(graph,a,a,0,[0]))

    def test_missing_access_disconnection_and_caps_are_not_distance_proofs(self):
        a,b = (0,0),(1,0)
        self.assertEqual('missing_access',explain_failure({}, {},a,b,1,[0])['reason'])
        self.assertEqual('connector_search_limit',explain_failure({}, {},a,b,1,[0],connector_capped=True)['reason'])
        self.assertEqual('disconnected_streets',explain_failure({}, {a:0,b:1},a,b,1,[0])['reason'])
        self.assertEqual('route_search_limit',explain_failure({}, {a:0,b:0},a,b,1,[0],search_capped=True)['reason'])
        with patch('metropogits.street_diagnostics.MAX_DIAGNOSTIC_STATES',0):
            self.assertEqual('diagnostic_search_limit',explain_failure({}, {a:0,b:0},a,b,1,[0])['reason'])

    def test_shortest_length_matches_independent_unit_graph_bfs(self):
        rng = random.Random(17)
        for _ in range(30):
            keys = set()
            for x in range(5):
                for z in range(5):
                    for other in ((x+1,z),(x,z+1)):
                        if max(other)<5 and rng.random()<.8:
                            keys.add(((x,z),other))
            adjacency = _adjacency(keys)
            a,b = (0,0),(4,4)
            graph = _compress(adjacency,{a,b})
            distances,queue = {a:0},deque([a])
            while queue:
                node=queue.popleft()
                for other in adjacency.get(node,()):
                    if other not in distances:
                        distances[other]=distances[node]+1
                        queue.append(other)
            for limit in (6,8,12):
                result=distance_within(graph,a,b,limit,[0])
                if distances.get(b,float('inf'))<=limit:
                    self.assertEqual(distances[b],result)
                else:
                    self.assertIs(result,False)

    def test_diagnostic_budget_does_not_change_routing_or_fallback_partition(self):
        scene,original = fixture()
        before=assign_streets(scene,original)
        with patch('metropogits.street_diagnostics.MAX_DIAGNOSTIC_STATES',0):
            after=assign_streets(scene,original)
        for key in ('routes','segments','junctions'):
            self.assertEqual(before[key],after[key])
        for result in (before,after):
            report=result['streetGrid']['assignment']
            self.assertEqual(report['fallbackRouteIds'],[r['routeId'] for r in report['fallbackReasons']])
            self.assertEqual(len(report['fallbackRouteIds']),sum(report['fallbackReasonCounts'].values()))
            self.assertEqual(len(set(report['fallbackRouteIds'])),len(report['fallbackReasons']))

    def test_no_structural_geometry_reports_reason_without_dropping_relationships(self):
        scene,original=fixture()
        with patch('metropogits.structural_streets.build_streets',return_value={'segments':[]}):
            after=assign_streets(scene,original)
        report=after['streetGrid']['assignment']
        self.assertEqual({'no_structural_streets':len(original['routes'])},report['fallbackReasonCounts'])
        self.assertEqual(original['routes'],after['routes'])
