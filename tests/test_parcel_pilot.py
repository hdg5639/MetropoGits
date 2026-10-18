import copy
import unittest
from unittest.mock import patch

from scripts.canonical_json import canonical_json_bytes
from scripts.parcel_pilot import (GUARDED_METRICS, MAX_ROUTED_CANDIDATES, band_quotas,
                                 contains, empty_rectangle, experiment, frontage_band,
                                 propose, rejection_reasons, render_report, sites)


def fixture(distributed=False):
    district = dict(id='leaf', parentId='root', x=0, z=0, width=49, depth=49)
    district['footprint'] = [{k: district[k] for k in ('x', 'z', 'width', 'depth')}]
    buildings = [dict(entityId=f'b{i}', districtId='leaf', x=.5+(i % 4)*7, z=.5+(i//4)*7,
                      width=6, depth=6, height=10, archetype='GENERIC_BUILDING', evidenceIds=[])
                 for i in range(12)]
    if distributed:
        for i, building in enumerate(buildings):
            building.update(x=.5+(i % 4)*14, z=.5+(i//4)*21)
    buildings.append(dict(buildings[0], entityId='outside', districtId='other', x=70.5, z=21.5))
    edges = [dict(id=f'e{i}', **{'from': f'b{i}', 'to': 'outside'}) for i in range(12)]
    edges += [dict(id=f'local{i}', **{'from': f'b{i}', 'to': f'b{i+1}'}) for i in range(11)]
    scene = dict(districts=[district], buildings=buildings,
                 networks=[dict(id='n', kind='DEPENDENCY_ROAD', edgeIds=[e['id'] for e in edges])])
    return scene, dict(edges=edges)


class ParcelPilotTests(unittest.TestCase):
    def test_evidence_and_ownership_preserved_without_input_mutation(self):
        scene, graph = fixture(distributed=True)
        original = copy.deepcopy((scene, graph))
        report = experiment(scene, graph)
        self.assertEqual(original, (scene, graph))
        self.assertTrue(report['safeCandidate'])
        self.assertTrue(report['unchangedOutsideDistrict'])
        self.assertEqual('CANDIDATE_SELECTED', report['selection'])
        self.assertTrue(report['movements'])
        metrics = report['variants']['candidate']['metrics']
        self.assertEqual([], rejection_reasons(metrics, report['variants']['baseline']['metrics']))
        self.assertEqual([], report['candidateAudits'][report['selectedCandidate']]['rejectedBecause'])
        candidate = report['variants']['candidate']['buildings']
        for before, after in zip(sorted(scene['buildings'], key=lambda b: b['entityId']), candidate):
            self.assertEqual({k: v for k, v in before.items() if k not in ('x', 'z')},
                             {k: v for k, v in after.items() if k not in ('x', 'z')})
            if after['districtId'] == 'leaf':
                self.assertTrue(contains(scene['districts'][0], after['x'], after['z'], 6, 6))
            else:
                self.assertEqual(before, after)
        self.assertEqual(len(candidate), len({(b['x'], b['z']) for b in candidate}))
        for variant in report['variants'].values():
            self.assertEqual(sorted(e['id'] for e in graph['edges']),
                             sorted(e for r in variant['routing']['routes'] for e in r['edgeIds']))
            self.assertEqual(0, variant['metrics']['pavementBuildingIntersections'])

    def test_determinism_and_array_permutation(self):
        scene, graph = fixture()
        expected = canonical_json_bytes(experiment(scene, graph))
        for value in scene.values():
            value.reverse()
        graph['edges'].reverse()
        scene['networks'][0]['edgeIds'].reverse()
        self.assertEqual(expected, canonical_json_bytes(experiment(scene, graph)))

    def test_no_roads_or_insufficient_capacity_degrades(self):
        scene, graph = fixture()
        scene['networks'] = []
        self.assertEqual('NOT_APPLICABLE', propose(scene, graph)['status'])
        scene, graph = fixture()
        scene['districts'][0].update(width=7, depth=7)
        self.assertEqual('NOT_APPLICABLE', propose(scene, graph)['status'])

    def test_reference_attraction_does_not_empty_street_blocks(self):
        scene, graph = fixture()
        report = propose(scene, graph)
        axis = 0 if report['orientation'] == 'vertical' else 1
        district = scene['districts'][0]
        available = sites(district, axis, report['phase'], report['blockWidth'], report['crossing'])
        quotas = band_quotas(available, district, axis, report['phase'], len(report['overrides']), report['blockWidth'], report['crossing'])
        actual = dict.fromkeys(quotas, 0)
        for building in report['overrides']:
            actual[frontage_band((building['x'], building['z']), district, axis, report['phase'], report['blockWidth'], report['crossing'])] += 1
        self.assertEqual(quotas, actual)
        self.assertTrue(all(actual.values()))

    def test_unrelated_addition_preserves_pilot_sites(self):
        scene, graph = fixture()
        expected = propose(scene, graph)
        scene['buildings'].append(dict(scene['buildings'][-1], entityId='isolated', x=140.5))
        self.assertEqual(expected, propose(scene, graph))

    def test_strict_decimal_reader_and_safe_geometry(self):
        from scripts.canonical_json import loads_strict_json
        scene, graph = fixture()
        report = experiment(loads_strict_json(canonical_json_bytes(scene).decode()), graph)
        self.assertEqual(0, report['geometryChecks']['outsideOwnership'])
        self.assertEqual(0, report['geometryChecks']['overlappingBuildingPairs'])
        self.assertTrue(report['safeCandidate'])

    def test_empty_rectangle_matches_independent_exhaustive_grid(self):
        district = dict(x=0, z=0, width=21, depth=21)
        rectangles = [{(x, z) for x in range(x0, x1) for z in range(z0, z1)}
                      for x0 in range(3) for x1 in range(x0+1, 4)
                      for z0 in range(3) for z1 in range(z0+1, 4)]
        for mask in range(512):
            occupied = {(i % 3, i//3) for i in range(9) if mask & (1 << i)}
            buildings = [dict(x=x*7+.5, z=z*7+.5, width=6, depth=6) for x, z in occupied]
            expected = max([len(r)*49 for r in rectangles if not r & occupied] or [0])
            self.assertEqual(expected, empty_rectangle(district, buildings))
        district['footprint'] = [dict(x=0, z=0, width=7, depth=21)]
        self.assertEqual(147, empty_rectangle(district, []))

    def test_guards_reject_each_regression_and_evidence_loss(self):
        baseline = {k: 100 for k in GUARDED_METRICS}
        baseline.update(exactEdgeCoverage=True, pavementBuildingIntersections=0,
                        outsideOwnership=0, overlappingBuildingPairs=0)
        self.assertEqual([], rejection_reasons(baseline, baseline))
        for key in GUARDED_METRICS:
            self.assertEqual([key+' regressed'], rejection_reasons(dict(baseline, **{key: 101}), baseline))
        for key in ('pavementBuildingIntersections', 'outsideOwnership', 'overlappingBuildingPairs'):
            self.assertEqual([key], rejection_reasons(dict(baseline, **{key: 1}), baseline))
        self.assertEqual(['incomplete edge coverage'], rejection_reasons(dict(baseline, exactEdgeCoverage=False), baseline))

    def test_all_candidates_rejected_keeps_baseline_and_limits_routing(self):
        from metropogits.access_routes import derive_access_routes
        with patch('scripts.parcel_pilot.derive_access_routes', wraps=derive_access_routes) as router:
            report = experiment(*fixture())
        self.assertLessEqual(router.call_count, MAX_ROUTED_CANDIDATES+1)
        self.assertEqual('BASELINE_RETAINED', report['selection'])
        self.assertIsNone(report['selectedCandidate'])
        self.assertTrue(all(a['rejectedBecause'] for a in report['candidateAudits']))
        self.assertEqual([], report['overrides'])
        self.assertEqual([], report['movements'])
        self.assertEqual(report['variants']['baseline'], report['variants']['candidate'])

    def test_shortlist_is_unique_bounded_and_covers_variable_block_width(self):
        options = propose(*fixture(), alternatives=True)
        self.assertLessEqual(len(options), MAX_ROUTED_CANDIDATES)
        self.assertEqual(len(options), len({canonical_json_bytes(o['overrides']) for o in options}))
        self.assertGreater(len({o['blockWidth'] for o in options}), 1)

    def test_concave_footprint_and_resource_ceiling(self):
        district = dict(x=0, z=0, width=49, depth=49,
                        footprint=[dict(x=0, z=0, width=14, depth=49),
                                   dict(x=14, z=0, width=35, depth=14)])
        for axis in (0, 1):
            for phase in range(3):
                for x, z in sites(district, axis, phase):
                    self.assertTrue(any(contains(r, x, z, 6, 6) for r in district['footprint']))
        district.update(width=7000, depth=7000)
        self.assertEqual([], sites(district, 0, 0))

    def test_child_district_is_not_relocated(self):
        scene, graph = fixture()
        scene['districts'].append(dict(scene['districts'][0], id='child', parentId='leaf'))
        self.assertEqual('NOT_APPLICABLE', propose(scene, graph)['status'])

    def test_selection_not_dependent_on_project_name_and_report_escaped(self):
        scene, graph = fixture()
        report = experiment(scene, graph)
        report['district']['id'] = '<script>alert(1)</script>'
        rendered = render_report(report)
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn('NOT the default city', rendered)
        self.assertIn('Content-Security-Policy', rendered)


if __name__ == '__main__':
    unittest.main()
