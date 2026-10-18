import copy
import unittest

from scripts.canonical_json import canonical_json_bytes
from scripts.parcel_pilot import band_quotas, contains, experiment, frontage_band, propose, render_report, sites


def fixture():
    district = dict(id='leaf', parentId='root', x=0, z=0, width=49, depth=49)
    district['footprint'] = [{k: district[k] for k in ('x', 'z', 'width', 'depth')}]
    buildings = [dict(entityId=f'b{i}', districtId='leaf', x=.5+(i % 4)*7, z=.5+(i//4)*7,
                      width=6, depth=6, height=10, archetype='GENERIC_BUILDING', evidenceIds=[])
                 for i in range(12)]
    buildings.append(dict(buildings[0], entityId='outside', districtId='other', x=70.5, z=21.5))
    edges = [dict(id=f'e{i}', **{'from': f'b{i}', 'to': 'outside'}) for i in range(12)]
    edges += [dict(id=f'local{i}', **{'from': f'b{i}', 'to': f'b{i+1}'}) for i in range(11)]
    scene = dict(districts=[district], buildings=buildings,
                 networks=[dict(id='n', kind='DEPENDENCY_ROAD', edgeIds=[e['id'] for e in edges])])
    return scene, dict(edges=edges)


class ParcelPilotTests(unittest.TestCase):
    def test_evidence_and_ownership_preserved_without_input_mutation(self):
        scene, graph = fixture()
        original = copy.deepcopy((scene, graph))
        report = experiment(scene, graph)
        self.assertEqual(original, (scene, graph))
        self.assertTrue(report['safeCandidate'])
        self.assertTrue(report['unchangedOutsideDistrict'])
        self.assertTrue(report['movements'])
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
        available = sites(district, axis, report['phase'])
        quotas = band_quotas(available, district, axis, report['phase'], len(report['overrides']))
        actual = dict.fromkeys(quotas, 0)
        for building in report['overrides']:
            actual[frontage_band((building['x'], building['z']), district, axis, report['phase'])] += 1
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
