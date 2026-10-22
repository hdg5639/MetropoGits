import copy
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.generator import generate_world
from metropogits.world.compounds import derive_compounds
from metropogits.world.validation import validate_world

from metropogits.world.campus_reservation import program_demand, reserve_precinct
from metropogits.world.geometry import inside, rectangle


class CampusReservationTests(unittest.TestCase):
    def test_unreserved_parent_keeps_its_existing_programmed_campus(self):
        from metropogits.world.campus import apply_campuses
        decisions, sites = {'z': {'reason': 'EXISTING'}}, {'z': {'geometry': 'existing'}}
        with patch('metropogits.world.campus.apply_campuses', return_value=(decisions, sites)) as retained:
            actual = apply_campuses({}, {}, [], {}, 'seed', [], None, {}, 'precinct')
        self.assertEqual(retained.call_args.args[-1], 'programmed')
        self.assertEqual(actual[0], decisions)
        self.assertEqual(actual[1]['z']['geometry'], 'existing')
        self.assertEqual(actual[1]['z']['architecturalSites'], [])
        self.assertEqual(actual[1]['z']['estateFallback'], 'NO_SAFE_RESERVATION_PROGRAMMED_RETAINED')

    def test_source_pipeline_reservation_is_reconstructed_and_legacy_is_unchanged(self):
        graph = analyze_repository(Path('tests/fixtures/repositories/purpose-campus'), repository_id='fixture/purpose-campus')
        city = generate_city(graph)
        original = copy.deepcopy((city, graph))
        options = dict(seed='purpose-4', zoning='neighborhoods', pattern_scale='adaptive',
                       planning='varied', outline='varied', street_policy='porous', street_hierarchy=True, campus=True)
        legacy = generate_world(city, graph, campus_style='estate', **options)
        world = generate_world(city, graph, campus_style='precinct', **options)
        self.assertEqual((city, graph), original)
        self.assertEqual(world, generate_world(city, graph, campus_style='precinct', **options))
        self.assertEqual(world['envelope'], legacy['envelope'])
        self.assertEqual([d['polygon'] for d in world['districts']], [d['polygon'] for d in legacy['districts']])
        self.assertEqual(world['campusPlan']['version'], 'campus-plan/0.9')
        valid = validate_world(world, city, graph)
        self.assertEqual(valid['accessibleBuildings'], 31)
        Draft202012Validator(json.loads(Path('schemas/world-0.1.schema.json').read_text(encoding='utf8'))).validate(world)
        groups, _ = derive_compounds(world, graph, campus_landmarks=True)
        self.assertGreaterEqual(sum(len(c['memberEntityIds']) for c in groups if c.get('campusProgram')), 20)
        forged = copy.deepcopy(world)
        forged['zoning']['districtPatterns'][0]['campusReservation']['physicalProgram']['total'] += 1
        with self.assertRaises(ValueError):
            validate_world(forged, city, graph)
        self.assertEqual(legacy, generate_world(city, graph, campus_style='estate', **options))
        migrated = generate_world(city, graph, campus_style='precinct', previous=legacy, **options)
        validate_world(migrated, city, graph)
        self.assertEqual(migrated['envelope'], legacy['envelope'])
        self.assertEqual([d['polygon'] for d in migrated['districts']], [d['polygon'] for d in legacy['districts']])

    def test_program_reserves_land_before_roads_and_preserves_outside_endpoints(self):
        ids = [str(i) for i in range(16)]
        zone = dict(id='z', memberEntityIds=ids, memberClaims=[])
        pairs = {(a, b): 1 for i, a in enumerate(ids) for b in ids[i+1:]}
        road = dict(id='road', start=[-100, 0], end=[100, 0], width=4, structural=True)
        poly = rectangle([0, 0], 0, 100, 100)
        pattern = dict(id='p', protectedStreetIds=['road'], roadCount=1)
        original = copy.deepcopy((zone, road, poly, pattern))
        # Seed changes selection, not determinism within a seed.
        for i in range(20):
            result, out = reserve_precinct([zone], {'z': poly}, str(i), [road], pattern, None, pairs)
            if 'campusReservation' in out:
                break
        self.assertIn('campusReservation', out)
        self.assertEqual(out['campusReservation']['physicalProgram'], program_demand(zone, pairs))
        self.assertEqual((zone, road, poly, pattern), original)
        endpoints = [p for r in result for p in (r['start'], r['end'])]
        self.assertIn([-100, 0], endpoints)
        self.assertIn([100, 0], endpoints)
        self.assertTrue(all(not inside([(r['start'][j]+r['end'][j])/2 for j in (0, 1)], poly, .1) for r in result))
        self.assertEqual((result, out), reserve_precinct([zone], {'z': poly}, str(i), [road], pattern, None, pairs))
        blocked = dict(features=[dict(noBuildPolygon=rectangle([50, 0], 0, 12, 12))])
        self.assertEqual(reserve_precinct([zone], {'z': poly}, str(i), [road], pattern, blocked, pairs), ([road], pattern))
        # Actual program demand cannot be satisfied by a tiny site.
        self.assertEqual(reserve_precinct([zone], {'z': rectangle([0, 0], 0, 12, 12)}, str(i), [road], pattern, None, pairs), ([road], pattern))


if __name__ == '__main__':
    unittest.main()
