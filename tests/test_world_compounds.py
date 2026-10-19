"""Restore role facilities without removing rotated-ground safety checks."""
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.world.compounds import derive_compounds
from metropogits.world.geometry import rectangle, inside
from metropogits.world.export import view_data, render_svg
from metropogits.world.generator import generate_world
from test_world_campus import fixture
from test_world_campus_neighborhood import OPTIONS


def compact():
    angle=.37;c,s=math.cos(angle),math.sin(angle)
    parcels=[]
    for i in range(16):
        x,z=(i%4)*7.4,(i//4)*7.4
        center=[c*x-s*z,s*x+c*z];identity=f'f{i:02}'
        parcels.append(dict(entityId=identity,districtId='d',zoneId='d',center=center,angle=angle,
            width=6,depth=6,height=10,archetype='LIBRARY',evidenceIds=['ev'],
            footprint=rectangle(center,angle,6,6),parcel=rectangle(center,angle,7,7),
            entrance=[center[0]+3*s,center[1]-3*c],streetPoint=[center[0]+5*s,center[1]-5*c]))
    return dict(parcels=parcels,streets=[],districts=[dict(id='d',polygon=rectangle([10,10],0,150,150))]),dict(
        entities=[dict(id=p['entityId'],kind='FILE',path=f'src/{p["entityId"]}.test.ts') for p in parcels],
        evidence=[dict(evidenceId='ev',ruleId='path.test-source')],edges=[])


class WorldCompoundTests(unittest.TestCase):
    def test_rotated_sources_promote_with_exact_members_and_bounded_geometry(self):
        w,g=compact();original=copy.deepcopy((w,g));facilities,note=derive_compounds(w,g)
        self.assertEqual(original,(w,g));self.assertEqual(len(facilities),1)
        f,=facilities
        self.assertEqual(f['tier'],'campus');self.assertEqual(len(f['memberEntityIds']),16)
        self.assertEqual(f['role'],'TEST');self.assertEqual(f['evidenceIds'],['ev'])
        self.assertTrue(all(inside(v,f['physicalModel']['footprint'],-.001)
            for part in f['physicalModel']['parts'] for v in part['footprint']))
        self.assertGreater(note['checks'],0)
        w['parcels'].reverse();g['entities'].reverse()
        self.assertEqual(facilities,derive_compounds(w,g)[0])

    def test_real_streets_unknown_roles_and_unrelated_occupants_are_not_covered(self):
        w,g=compact()
        w['streets']=[dict(id='public',start=[4,-40],end=[4,70],width=3,access=False)]
        from metropogits.street_diagonals import overlap
        from metropogits.world.geometry import ribbon
        for f in derive_compounds(w,g)[0]:
            self.assertFalse(overlap(f['physicalModel']['footprint'],ribbon([4,-40],[4,70],3)))
        g['evidence'][0]['ruleId']='unverified.test-name'
        self.assertEqual(derive_compounds(w,g)[0],[])
        w,g=compact();w['parcels'][5]['archetype']='GENERIC_BUILDING'
        blocker=w['parcels'][5]['parcel']
        for f in derive_compounds(w,g)[0]:
            self.assertNotIn('f05',f['memberEntityIds'])
            self.assertFalse(overlap(f['physicalModel']['footprint'],blocker))
        with patch('metropogits.world.compounds.MAX_CHECKS',0):
            facilities,note=derive_compounds(*compact())
        self.assertEqual(facilities,[]);self.assertIn('limit',note['fallback'])
        with patch('metropogits.world.compounds.MAX_CANDIDATES',0):
            facilities,note=derive_compounds(*compact())
        self.assertEqual(facilities,[]);self.assertIn('candidate limit',note['fallback'])

    def test_world_export_restores_compounds_without_canonical_or_route_mutation(self):
        with tempfile.TemporaryDirectory() as directory:s,g=fixture(Path(directory))
        w=generate_world(s,g,**dict(OPTIONS,campus_style='fabric'))
        original=copy.deepcopy((w,s,g));data=view_data(w,s,g)
        self.assertEqual(original,(w,s,g))
        self.assertIn('roleCompounds',data['streets'])
        self.assertEqual(data['streets']['orientedEntityIds'],sorted(p['entityId'] for p in w['parcels']))
        # The old safety guard remains; physical model supplies its replacement.
        model,graph=compact();facilities,_=derive_compounds(model,graph)
        base=dict(w);base['parcels']=[]
        svg=render_svg(base,landscape=False,compounds=facilities)
        self.assertIn(b'data-aggregate-id=',svg)
        self.assertIn(b'data-member-entity-ids=',svg)
        self.assertNotIn(b'data-entity-id="visual:',svg)

    def test_modules_roles_and_natural_reserves_remain_separate(self):
        from metropogits.street_diagonals import overlap
        w,g=compact()
        for i,e in enumerate(g['entities']):e['path']=('a' if i<8 else 'b')+'/'+e['id']+'.test.ts'
        g['entities'] += [dict(id=k,kind='MODULE',path=k) for k in ('a','b')]
        paths={e['id']:e['path'].split('/')[0] for e in g['entities'] if e['kind']=='FILE'}
        for f in derive_compounds(w,g)[0]:
            self.assertEqual(len({paths[k] for k in f['memberEntityIds']}),1)
        lake=rectangle([9,9],0,8,8)
        w['terrain']=dict(features=[dict(noBuildPolygon=lake)])
        for f in derive_compounds(w,g)[0]:self.assertFalse(overlap(f['physicalModel']['footprint'],lake))
        w,g=compact();g['evidence'] += [dict(evidenceId='api',ruleId='path.nextjs.route-handler')]
        for i,p in enumerate(w['parcels']):
            if i<8:p.update(archetype='GATE',evidenceIds=['api'])
        for f in derive_compounds(w,g)[0]:
            self.assertEqual({w['parcels'][int(k[1:])]['archetype'] for k in f['memberEntityIds']},
                             {f['archetypeCounts'][0]['archetype']})
        facilities,_=derive_compounds(w,g)
        for i,a in enumerate(facilities):
            for b in facilities[:i]:
                self.assertFalse(overlap(a['physicalModel']['footprint'],b['physicalModel']['footprint']))
