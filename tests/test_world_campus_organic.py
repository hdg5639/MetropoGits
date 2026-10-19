"""Whole precinct redevelopment, source conservation and local-address stability."""

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.campus_organic import organic_layout
from metropogits.world.generator import generate_world
from metropogits.world.export import package_world
from metropogits.world.geometry import rectangle
from metropogits.world.validation import validate_world
from test_world_campus import fixture
from test_world_campus_neighborhood import OPTIONS

ORGANIC = dict(OPTIONS, campus_style='organic')


class CampusOrganicTests(unittest.TestCase):
    def test_occupied_frontages_follow_real_fanning_paths_not_global_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        inputs = copy.deepcopy((scene, graph))
        before = generate_world(scene, graph, **dict(OPTIONS, campus_style='landscape'))
        world = generate_world(scene, graph, **ORGANIC)
        self.assertEqual((scene, graph), inputs)
        self.assertEqual(world, generate_world(scene, graph, **ORGANIC))
        site, = world['campusPlan']['sites']
        self.assertEqual(world['campusPlan']['version'], 'campus-plan/0.5')
        self.assertEqual(site['frontagePolicy'], 'FANNING_COMMONS')
        self.assertEqual(site['memberEntityIds'], before['campusPlan']['sites'][0]['memberEntityIds'])
        self.assertEqual(site['retainedMemberEntityIds'], [])
        self.assertTrue(all(len(c['polygon']) == 16 for c in site['courts']))
        # Test occupied full-size parcels, not only unoccupied planning choices.
        bearings = {round(p['angle'] % math.pi, 2) for p in world['parcels']}
        self.assertGreater(len(bearings), 12)
        self.assertTrue(all(p['width'] == 6 and p['depth'] == 6 for p in world['parcels']))
        validation = validate_world(world, scene, graph)
        self.assertEqual(validation['accessibleBuildings'], 48)
        identities = lambda w: {r['id']: (r['source'], r['target'], r['edgeIds'])
                                for r in w['routing']['routes']}
        self.assertEqual(identities(world), identities(before))
        Draft202012Validator(json.loads(Path('schemas/world-0.1.schema.json').read_bytes())).validate(world)
        package = package_world(world, scene, graph, validation)
        Draft202012Validator(json.loads(Path('schemas/planning-0.5.schema.json').read_bytes())).validate(
            json.loads(package['planning.json']))
        bad = copy.deepcopy(world)
        bad['campusPlan']['sites'][0]['groupBearings'][0] += .1
        with self.assertRaises(ValueError):
            validate_world(bad, scene, graph)

    def test_growth_retains_existing_complete_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            before = generate_world(scene, graph, **ORGANIC)
            (repo/'zz_unknown.rs').write_text('fn unknown() {}\n', encoding='utf8')
            graph2 = analyze_repository(repo, repository_id='fixture/campus')
            scene2 = generate_city(graph2)
            after = generate_world(scene2, graph2, previous=before, **ORGANIC)
        validate_world(after, scene2, graph2)
        old = {p['entityId']: p for p in before['parcels']}
        self.assertEqual(sum(p == old.get(p['entityId']) for p in after['parcels']), 48)

    def test_bounded_failure_does_not_return_partial_organic_pocket(self):
        poly = rectangle([0, 0], 0, 35, 30)
        roads = [dict(id=str(i), start=a, end=b, width=3)
                 for i, (a, b) in enumerate(zip(poly, poly[1:]+poly[:1]))]
        zone = dict(id='z', parentId='p', memberEntityIds=list(map(str, range(48))))
        stats = {}
        self.assertIsNone(organic_layout(zone, poly, 0, 'seed', roads, None, {}, stats))
        self.assertIn('organicFallback', stats)
        poly = rectangle([0, 0], 0, 320, 240)
        roads = [dict(id=str(i), start=a, end=b, width=3)
                 for i, (a, b) in enumerate(zip(poly, poly[1:]+poly[:1]))]
        with patch('metropogits.world.campus_neighborhood.MAX_WORK', 0):
            with self.assertRaisesRegex(ValueError, 'work limit'):
                organic_layout(zone, poly, 0, 'seed', roads, None, {}, {})


if __name__ == '__main__':
    unittest.main()
