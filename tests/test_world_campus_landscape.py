"""Local group bearings, full membership and soft commons, not role sorting."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator
from test_world_campus import fixture
from test_world_campus_neighborhood import OPTIONS
from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world
from metropogits.world.campus_landscape import landscape_layout
from metropogits.world.geometry import rectangle


class CampusLandscapeTests(unittest.TestCase):
    def test_complete_precinct_with_distinct_group_bearings_and_rounder_commons(self):
        with tempfile.TemporaryDirectory() as directory:scene,graph=fixture(Path(directory))
        before=generate_world(scene,graph,**OPTIONS)
        after=generate_world(scene,graph,**dict(OPTIONS,campus_style='landscape'))
        site=after['campusPlan']['sites'][0]
        self.assertEqual(site['memberEntityIds'],before['campusPlan']['sites'][0]['memberEntityIds'])
        # This intentionally interlocked dense fixture cannot safely rotate its
        # wings. Keep access/capacity instead of forcing a visually false success.
        self.assertEqual(site['groupRotations'],[0,0])
        self.assertTrue(all(len(c['polygon'])==16 for c in site['courts']))
        self.assertTrue(any(':corner:' in r['id'] for r in site['walkways']))
        self.assertGreater(len(site['walkways']),len(before['campusPlan']['sites'][0]['walkways']))
        self.assertEqual(validate_world(after,scene,graph)['accessibleBuildings'],48)
        Draft202012Validator(json.loads(Path('schemas/world-0.1.schema.json').read_bytes())).validate(after)
        self.assertEqual(after,generate_world(scene,graph,**dict(OPTIONS,campus_style='landscape')))
        identities=lambda w:{r['id']:(r['source'],r['target'],r['edgeIds']) for r in w['routing']['routes']}
        self.assertEqual(identities(after),identities(before))
        bad=copy.deepcopy(after);bad['campusPlan']['sites'][0]['groupRotations'][0]+=.1
        with self.assertRaises(ValueError):validate_world(bad,scene,graph)

    def test_roomy_source_neighborhood_really_gets_different_coordinated_bearings(self):
        poly=rectangle([0,0],0,320,240)
        roads=[dict(id=str(i),start=a,end=b,width=3) for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1]))]
        zone=dict(id='z',parentId='p',memberEntityIds=list(map(str,range(48))))
        stats={}
        plots,walks,site=landscape_layout(zone,poly,0,'seed',roads,None,{},stats)
        self.assertGreaterEqual(len(plots),48)
        self.assertTrue(all(abs(a)>.1 for a in site['groupRotations']))
        self.assertGreater(len(set(site['groupRotations'])),1)
        self.assertEqual(site['memberEntityIds'],sorted(zone['memberEntityIds']))
