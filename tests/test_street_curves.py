import copy
import math
import unittest
from unittest.mock import patch

from metropogits.street_curves import CurveMap, plan_curves, curved_presentation


def fixture():
    return {'buildings':[]}, {'streetGrid':{'version':'structural-streets/0.2','segments':[
        dict(id='a',start=[0,0],end=[21,0],width=2),
        dict(id='b',start=[0,0],end=[0,21],width=2)]}}


class StreetCurveTests(unittest.TestCase):
    def test_geographic_determinism_and_independence(self):
        scene,routing=fixture()
        frozen=copy.deepcopy(routing)
        plan=plan_curves(scene,routing)
        self.assertEqual(len(plan['corners']),1)
        self.assertEqual(plan['corners'][0]['radius'],9.45)
        routing['routes']=[{'id':'unrelated'}]
        routing['streetGrid']['segments'].reverse()
        self.assertEqual(plan,plan_curves(scene,routing))
        self.assertNotIn('curvePlan',frozen)

    def test_branch_and_obstacle_stay_square(self):
        scene,routing=fixture()
        routing['streetGrid']['segments'].append(dict(id='c',start=[0,0],end=[-21,0],width=2))
        self.assertEqual(plan_curves(scene,routing)['corners'],[])
        scene,routing=fixture()
        scene['buildings']=[dict(x=.5,z=.5,width=3,depth=3)]
        self.assertEqual(plan_curves(scene,routing)['corners'],[])

    def test_quadratic_centerline_tangent_and_fixed_exterior(self):
        scene,routing=fixture()
        mapper=CurveMap(plan_curves(scene,routing))
        radius=mapper.corners[0]['radius']
        self.assertEqual(mapper.point([radius,0]),[radius,0])
        self.assertEqual(mapper.point([0,0]),[radius/4,radius/4])
        a,b,c=mapper.point([.00001,0]),mapper.point([0,0]),mapper.point([0,.00001])
        before=[b[i]-a[i] for i in (0,1)]
        after=[c[i]-b[i] for i in (0,1)]
        cosine=sum(before[i]*after[i] for i in (0,1))/(math.hypot(*before)*math.hypot(*after))
        self.assertGreater(cosine,.999999)
        self.assertEqual(mapper.point([50,50]),[50,50])
        for i in range(-20,21):
            for j in range(-20,21):
                p=mapper.point([i*radius/20,j*radius/20])
                self.assertTrue(all(abs(v)<=radius+1e-8 for v in p))

    def test_shared_pavement_and_centerline_do_not_mutate_inputs(self):
        scene,routing=fixture()
        routing['curvePlan']=plan_curves(scene,routing)
        routing['segments']=[dict(id='a',start=[0,0],end=[21,0],width=2)]
        piece=dict(points=[[0,-1],[21,-1],[21,1],[0,1]],start=[0,0],end=[21,0],width=2,maxWidth=2)
        surfaces=[dict(piece,segmentId='a')]
        pavement=dict(segments={'a':[piece]})
        frozen=copy.deepcopy((routing,surfaces,pavement))
        s,p,c=curved_presentation(routing,surfaces,pavement)
        self.assertEqual(frozen,(routing,surfaces,pavement))
        self.assertEqual([x['points'] for x in s],[x['points'] for x in p['segments']['a']])
        self.assertEqual(c['segments']['a'][0],CurveMap(routing['curvePlan']).point([0,0]))
        self.assertEqual(c['segments']['a'][-1],[21,0])
        self.assertEqual((s,p,c),curved_presentation(routing,surfaces,pavement))

    def test_legacy_and_resource_limits(self):
        self.assertEqual(curved_presentation({},None,None),(None,None,None))
        with self.assertRaisesRegex(ValueError,'aligned'):
            plan_curves({}, {})
        scene,routing=fixture()
        mapper=CurveMap(plan_curves(scene,routing))
        with patch('metropogits.street_curves.MAX_PIECES',2):
            with self.assertRaisesRegex(ValueError,'sample limit'):
                plan_curves(scene,routing)
            with self.assertRaisesRegex(ValueError,'limit'):
                mapper.line([0,0],[21,0])

    def test_support_regions_never_overlap(self):
        scene,routing=fixture()
        routing['streetGrid']['segments'].append(dict(id='c',start=[0,21],end=[21,21],width=2))
        corners=plan_curves(scene,routing)['corners']
        for i,a in enumerate(corners):
            for b in corners[i+1:]:
                self.assertGreaterEqual(max(abs(a['point'][j]-b['point'][j]) for j in (0,1)),a['radius']+b['radius'])

    def test_corner_joint_faces_up_and_never_exceeds_empty_support(self):
        scene,routing=fixture()
        routing['curvePlan']=plan_curves(scene,routing)
        routing['segments']=[]
        from metropogits.structural_streets import street_rectangles
        surfaces,_,_=curved_presentation(routing,street_rectangles(routing),{'segments':{}})
        joints=[s for s in surfaces if s['id'].startswith('curve-joint')]
        self.assertTrue(joints)
        radius=routing['curvePlan']['corners'][0]['radius']
        for joint in joints:
            ps=joint['points']
            area=sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(ps,ps[1:]+ps[:1]))
            self.assertLess(area,0)  # Negative X/Z area is upward, not culled.
            self.assertTrue(all(abs(v)<radius for p in ps for v in p))

    def test_real_pipeline_curved_viewer_and_svg_repeat_exactly(self):
        from pathlib import Path
        from scripts.canonical_json import loads_strict_json
        from metropogits.layout import generate_city
        from metropogits.access_routes import derive_access_routes
        from metropogits.structural_streets import assign_streets
        from scripts.road_consolidation import package
        graph=loads_strict_json((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text(encoding='utf8'))
        scene=generate_city(graph)
        routing=assign_streets(scene,derive_access_routes(scene,graph),aligned=True)
        frozen=copy.deepcopy((scene,graph,routing))
        routing['curvePlan']=plan_curves(scene,routing)
        output=package(scene,graph,routing,{'test':'curves'})
        self.assertEqual(output,package(scene,graph,routing,{'test':'curves'}))
        self.assertIn(b'"streetCurves"',output['assets/viewer-data.js'])
        self.assertIn(b'access-routing',output['preview.svg'])
        self.assertIn(b'access-routing',output['showcase.svg'])
        original=copy.deepcopy(routing)
        original.pop('curvePlan')
        self.assertEqual(frozen,(scene,graph,original))
