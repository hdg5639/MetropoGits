import copy
import math
import unittest
from unittest.mock import patch

from metropogits.street_junctions import plan_junctions
from metropogits.street_diagonals import PhysicalMap, plan_diagonals


def fixture():
    paths = [[[0,21],[0,0],[21,0],[21,28]], [[42,21],[42,0],[21,0],[21,28]]]
    pairs = sorted({tuple(sorted((tuple(a),tuple(b)))) for p in paths for a,b in zip(p,p[1:])})
    segments = [dict(id=str(i), start=list(a), end=list(b), width=2, semantic=False) for i,(a,b) in enumerate(pairs)]
    return {'buildings':[]}, dict(segments=[], routes=[{'path':p} for p in paths],
        streetGrid=dict(version='structural-streets/0.2',segments=segments))


class JunctionStreetTests(unittest.TestCase):
    def test_three_arms_move_as_one_and_keep_outer_doors(self):
        scene, routing = fixture()
        original = copy.deepcopy((scene,routing))
        plan = plan_junctions(scene,routing)
        self.assertEqual(original,(scene,routing))
        self.assertEqual(plan['version'],'street-junctions/0.1')
        self.assertEqual(len(plan['junctions']),1)
        j = plan['junctions'][0]
        self.assertEqual(j['original'],[21,0])
        self.assertGreater(j['physical'][1],0)
        self.assertLessEqual(math.dist(j['original'],j['physical']),14)
        self.assertLess(j['afterLength'],j['beforeLength']*.95)
        chains = [plan['chains'][i] for i in j['chainIndexes']]
        self.assertEqual(len(chains),3)
        baseline = PhysicalMap(plan_diagonals(scene,routing))
        for c in chains:
            self.assertEqual(c['physical'][0],j['physical'])
            self.assertEqual(c['physical'][-1],c['path'][-1])
            old_length = sum(math.dist(span[2],span[3])
                for a,b in zip(c['path'],c['path'][1:]) for span in baseline.spans(a,b))
            self.assertLessEqual(c['afterLength'],old_length+1e-8)
        mapper = PhysicalMap(plan)
        for route in routing['routes']:
            path = route['path']
            previous = path[0]
            for a,b in zip(path,path[1:]):
                spans = list(mapper.spans(a,b))
                self.assertEqual(spans[0][2],previous)
                previous = spans[-1][3]
            self.assertEqual(previous,path[-1])

    def test_door_at_branch_and_messaging_arm_are_protected(self):
        scene,routing = fixture()
        routing['routes'].append({'path':[[21,0],[21,28]]})
        self.assertEqual(plan_junctions(scene,routing)['junctions'],[])
        scene,routing = fixture()
        routing['segments']=[dict(start=[21,0],end=[21,28],width=2,kind='MESSAGING_PATH')]
        self.assertEqual(plan_junctions(scene,routing)['junctions'],[])

    def test_order_reversal_and_evidence_counts_do_not_change_plan(self):
        scene,routing = fixture()
        plan = plan_junctions(scene,routing)
        routing['streetGrid']['segments'].reverse()
        for s in routing['streetGrid']['segments']:
            s['start'],s['end']=s['end'],s['start']
        routing['routes'].reverse()
        for r in routing['routes']:
            r['path'].reverse()
            r['edgeIds']=['unrelated']*100
        self.assertEqual(plan,plan_junctions(scene,routing))

    def test_full_width_obstacle_and_unrelated_road_reject_relocation(self):
        scene,routing = fixture()
        scene['buildings']=[dict(x=8,z=3,width=26,depth=20)]
        self.assertEqual(plan_junctions(scene,routing)['junctions'],[])
        scene,routing = fixture()
        routing['streetGrid']['segments'].append(dict(id='other',start=[1,10],end=[41,10],width=2,semantic=False))
        self.assertEqual(plan_junctions(scene,routing)['junctions'],[])

    def test_already_straight_star_stays_unchanged(self):
        scene,routing = fixture()
        routing['streetGrid']['segments']=[dict(id=str(i),start=[21,0],end=p,width=2,semantic=False)
            for i,p in enumerate([[0,0],[42,0],[21,28]])]
        routing['routes']=[]
        p=plan_junctions(scene,routing)
        self.assertEqual(p['junctions'],[])
        self.assertEqual(p['chains'],plan_diagonals(scene,routing)['chains'])

    def test_caps_and_mode_conflicts_are_explicit(self):
        scene,routing=fixture()
        with patch('metropogits.street_junctions.MAX_PROPOSALS',0):
            with self.assertRaisesRegex(ValueError,'proposal limit'):
                plan_junctions(scene,routing)
        with patch('metropogits.street_junctions.MAX_CHECKS',0):
            with self.assertRaisesRegex(ValueError,'limit'):
                plan_junctions(scene,routing)
        from scripts.street_grid import compare
        for flags in ({}, {'aligned':True,'diagonals':True}, {'aligned':True,'curves':True}):
            with self.assertRaisesRegex(ValueError,'aligned'):
                compare({}, {}, junctions=True, **flags)

    def test_real_pipeline_repeats_and_keeps_public_contracts(self):
        from pathlib import Path
        from scripts.canonical_json import loads_strict_json
        from scripts.street_grid import compare
        from metropogits.layout import generate_city
        from scripts.road_consolidation import package
        graph=loads_strict_json((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text(encoding='utf8'))
        scene=generate_city(graph)
        frozen=copy.deepcopy((scene,graph))
        _,routing,report=compare(scene,graph,aligned=True,junctions=True)
        output=package(scene,graph,routing,report)
        self.assertEqual(output,package(scene,graph,routing,report))
        self.assertEqual(frozen,(scene,graph))
        self.assertIn(b'street-junctions/0.1',output['assets/viewer-data.js'])
        self.assertIn(b'civic-infrastructure',output['preview.svg'])
