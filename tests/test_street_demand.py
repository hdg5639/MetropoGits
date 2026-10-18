import copy
import unittest
from unittest.mock import patch

from metropogits.street_demand import demand_pavement, clip_paint
from metropogits.access_routes import svg_access_lines


def fixture():
    street = dict(id='street',start=[7,0],end=[21,0],width=3.5)
    route = dict(id='trip',kind='DEPENDENCY_ROAD',source='a',target='b',edgeIds=['e'],networkIds=['n'])
    segment = dict(id='segment',start=[0,0],end=[28,0],width=3.5,kind='DEPENDENCY_ROAD',
                   routeIds=['trip'],access=False)
    routing = dict(version='visual-access/0.3',status='COMPLETE',unresolvedEdgeIds=[],
        routes=[route],segments=[segment],junctions=[],streetGrid=dict(version='structural-streets/0.2',
        segments=[street],assignment=dict(assignedRouteIds=['trip'])))
    surfaces=[dict(segmentId='street',points=[[7,-.375],[21,-1.75],[21,1.75],[7,.375]])]
    hierarchy=dict(segments={'segment':dict(width=2.5)})
    return routing,hierarchy,surfaces


class StreetDemandTests(unittest.TestCase):
    def test_full_centerline_retained_and_taper_intersected_with_safe_grade(self):
        routing,hierarchy,surfaces=fixture()
        frozen=copy.deepcopy((routing,hierarchy,surfaces))
        result=demand_pavement(routing,hierarchy,surfaces)
        pieces=result['segments']['segment']
        self.assertEqual(28,sum(p['end'][0]-p['start'][0] for p in pieces))
        self.assertEqual([0,0],pieces[0]['start'])
        self.assertEqual([28,0],pieces[-1]['end'])
        for a,b in zip(pieces,pieces[1:]):
            self.assertEqual(a['end'],b['start'])
        self.assertEqual([False,True,True,False],[p['structural'] for p in pieces])
        for p in pieces:
            for x,z in p['points']:
                self.assertLessEqual(abs(z),1.25+1e-8)
                if p['structural']:
                    self.assertLessEqual(abs(z),(.75+(x-7)*2.75/14)/2+1e-8)
        self.assertEqual(frozen,(routing,hierarchy,surfaces))
        self.assertEqual(result,demand_pavement(routing,hierarchy,list(reversed(surfaces))))

    def test_crossing_parallel_offset_and_uncovered_connector_do_not_claim_street_overlap(self):
        routing,hierarchy,surfaces=fixture()
        for a,b in (([14,-14],[14,14]),([0,1],[28,1])):
            routing['segments'][0].update(start=a,end=b)
            pieces=demand_pavement(routing,hierarchy,surfaces)['segments']['segment']
            self.assertEqual(1,len(pieces))
            self.assertFalse(pieces[0]['structural'])

    def test_paint_clips_to_wide_enough_spans_without_new_paths(self):
        pieces=[dict(start=[0,0],end=[7,0],width=.75),dict(start=[7,0],end=[14,0],width=2.5)]
        self.assertEqual([dict(start=[7,0],end=[10,0])],clip_paint(dict(start=[5,0],end=[10,0]),pieces))
        self.assertEqual([],clip_paint(dict(start=[0,0],end=[4,0]),pieces))

    def test_old_mode_other_kinds_and_resource_cap(self):
        routing,hierarchy,surfaces=fixture()
        with patch('metropogits.street_demand.MAX_PIECES',1):
            with self.assertRaisesRegex(ValueError,'surface limit'):
                demand_pavement(routing,hierarchy,surfaces)
        routing['segments'][0]['kind']='HTTP_HIGHWAY'
        self.assertEqual({},demand_pavement(routing,hierarchy,surfaces)['segments'])
        routing['streetGrid']['version']='structural-streets/0.1'
        self.assertIsNone(demand_pavement(routing,hierarchy))

    def test_svg_retains_evidence_for_each_presentation_fragment(self):
        routing,_,_=fixture()
        svg='\n'.join(svg_access_lines(routing,lambda x,z:(x,z)))
        self.assertIn('data-access-segment-id="segment"',svg)
        self.assertIn('data-route-indexes="0"',svg)
        self.assertIn('trip',svg)
        self.assertIn('"e"',svg.replace('&quot;','"'))
