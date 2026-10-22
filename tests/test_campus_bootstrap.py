import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.cold_start import PlanningFrame, cold_start
from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world

OPTIONS = dict(seed='purpose-4', zoning='neighborhoods', pattern_scale='adaptive',
               planning='varied', outline='varied', street_policy='porous',
               street_hierarchy=True, campus=True)


class CampusBootstrapTests(unittest.TestCase):
    def test_real_prepass_skips_routing_and_matches_full_baseline_geography(self):
        graph = analyze_repository(Path('tests/fixtures/repositories/purpose-campus'), repository_id='fixture/purpose-campus')
        city = generate_city(graph)
        original = copy.deepcopy((city, graph))
        with patch('metropogits.world.generator.route_world', side_effect=AssertionError('prepass routed dependencies')):
            frame = generate_world(city, graph, campus_style='programmed', _planning_frame=True, **OPTIONS)
        self.assertIsInstance(frame, PlanningFrame)
        self.assertNotIn('routing', frame.hint)
        self.assertNotIn('streets', frame.hint)
        baseline = generate_world(city, graph, campus_style='programmed', **OPTIONS)
        self.assertEqual(frame.hint['envelope'], baseline['envelope'])
        self.assertEqual(frame.hint['districts'], baseline['districts'])
        self.assertEqual(frame.hint['zoning']['zones'], baseline['zoning']['zones'])
        self.assertEqual(frame.hint['zoning']['blocks'], baseline['zoning']['blocks'])
        migrated = generate_world(city, graph, previous=baseline, campus_style='precinct', **OPTIONS)
        bootstrapped = generate_world(city, graph, campus_style='precinct', campus_bootstrap=True, **OPTIONS)
        self.assertEqual(bootstrapped, generate_world(city, graph, campus_style='precinct', campus_bootstrap=True, **OPTIONS))
        validate_world(bootstrapped, city, graph)
        note = bootstrapped['diagnostics'][-1]
        self.assertEqual(note['source'], 'INTERNAL_PLANNING_NOT_CACHED_WORLD')
        self.assertEqual(note['baselineRoutingPasses'], 0)
        self.assertEqual(note['actualCampusStyle'], 'precinct')
        bootstrapped['diagnostics'].pop()
        self.assertEqual(bootstrapped, migrated)
        self.assertEqual((city, graph), original)

    def test_invalid_combinations_fail_before_any_planning(self):
        def forbidden(*args, **kwargs):
            self.fail('invalid bootstrap invoked planner')
        wrapped = cold_start(forbidden)
        for options in (
            dict(campus_bootstrap='yes'),
            dict(campus_bootstrap=True),
            dict(campus_bootstrap=True, campus=True, campus_style='estate'),
            dict(campus_bootstrap=True, campus=True, campus_style='precinct', previous={}),
        ):
            with self.assertRaises(ValueError):
                wrapped({}, {}, **options)

    def test_single_prepass_and_fallback_are_disclosed_without_fake_success(self):
        calls = []
        def implementation(scene, graph, **options):
            calls.append(options)
            if options.get('_planning_frame'):
                return PlanningFrame(dict(envelope='own computed frame'))
            return dict(campusPlan=dict(style='programmed'), diagnostics=[])
        world = cold_start(implementation)({}, {}, campus=True, campus_style='precinct', campus_bootstrap=True)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]['campus_style'], 'programmed')
        self.assertEqual(calls[1]['previous'], dict(envelope='own computed frame'))
        self.assertEqual(world['diagnostics'][-1]['actualCampusStyle'], 'programmed')


if __name__ == '__main__':
    unittest.main()
