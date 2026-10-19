"""Different campus compositions must affect occupied geometry, not just labels."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from jsonschema import Draft202012Validator
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.campus_fabric import Fabric, fabric_layout, COMPOSITIONS
from metropogits.world.generator import generate_world
from metropogits.world.export import package_world
from metropogits.world.geometry import rectangle
from metropogits.world.validation import validate_world
from test_world_campus import fixture
from test_world_campus_neighborhood import OPTIONS

OPTIONS = dict(OPTIONS, campus_style='fabric')


class CampusFabricTests(unittest.TestCase):
    def test_full_source_neighborhood_has_nonradial_different_compositions(self):
        with tempfile.TemporaryDirectory() as directory:
            s,g = fixture(Path(directory))
        original = copy.deepcopy((s,g))
        w = generate_world(s,g,**OPTIONS)
        self.assertEqual(original,(s,g))
        self.assertEqual(w,generate_world(s,g,**OPTIONS))
        site, = w['campusPlan']['sites']
        self.assertEqual(site['frontagePolicy'],'FITTED_NONRADIAL_COMMONS')
        self.assertEqual(len(site['memberEntityIds']),48)
        self.assertEqual(len({c['kind'] for c in site['compositions']}),len(site['courts']))
        self.assertTrue(all(':fan:' not in r['id'] for r in site['walkways']))
        self.assertTrue(any(':fabric:' in r['id'] for r in site['walkways']))
        self.assertTrue(all(len(c['polygon'])!=16 for c in site['courts']))
        validation = validate_world(w,s,g)
        self.assertEqual(validation['accessibleBuildings'],48)
        package = package_world(w,s,g,validation)
        for schema,value in [('world-0.1',w),('planning-0.5',json.loads(package['planning.json']))]:
            Draft202012Validator(json.loads(Path(f'schemas/{schema}.schema.json').read_bytes())).validate(value)
        bad = copy.deepcopy(w);bad['campusPlan']['sites'][0]['compositions'][0]['kind']='FAN'
        with self.assertRaises(ValueError):validate_world(bad,s,g)

    def test_adjacent_source_growth_preserves_all_old_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory);s,g=fixture(repo);before=generate_world(s,g,**OPTIONS)
            (repo/'zz_unknown.rs').write_text('fn unknown() {}\n',encoding='utf8')
            g2=analyze_repository(repo,repository_id='fixture/campus');s2=generate_city(g2)
            after=generate_world(s2,g2,previous=before,**OPTIONS)
        validate_world(after,s2,g2)
        old={p['entityId']:p for p in before['parcels']}
        self.assertEqual(sum(p==old.get(p['entityId']) for p in after['parcels']),48)

    def test_seeded_compositions_have_distinct_outline_and_path_topology(self):
        poly=rectangle([0,0],0,320,240)
        roads=[dict(id=str(i),start=a,end=b,width=3) for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1]))]
        firsts=set();outlines=set();edge_counts=set()
        for seed in map(str,range(8)):
            form=Fabric(poly,0,seed,roads);firsts.add(form.kind(0))
            for i in range(3):
                outlines.add(tuple(map(tuple,form.lawn([0,0],0,i))))
                paths=form.branches([[0,0]]*3,0,64,
                    lambda a,b,key:dict(start=a,end=b,id=key),lambda a,b,c:True,[])
                edge_counts.add(len([r for r in paths if f'core:{i}:' in r['id']]))
        self.assertEqual(firsts,set(COMPOSITIONS))
        self.assertGreater(len(outlines),3);self.assertGreater(len(edge_counts),1)
        with patch('metropogits.world.campus_neighborhood.MAX_WORK',0):
            with self.assertRaisesRegex(ValueError,'work limit'):
                fabric_layout(dict(id='z',parentId='p',memberEntityIds=list(map(str,range(48)))),poly,0,'seed',roads,None,{}, {})
