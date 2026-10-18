import copy
import unittest

from metropogits.access_routes import svg_access_lines
from metropogits.road_hierarchy import demand_grade, derive_road_hierarchy
from scripts.canonical_json import canonical_json_bytes


def fixture():
    scene = dict(districts=[dict(id='root', parentId=None), dict(id='a', parentId='root'),
                           dict(id='b', parentId='root')],
                 buildings=[dict(entityId=f'f{i}', districtId='a' if i < 8 else 'b') for i in range(16)])
    routes = [dict(id=f'r{i}', source=f'f{i % 8}', target=f'f{8 + i % 8}', kind='DEPENDENCY_ROAD',
                   edgeIds=[f'e{i}', f'e{i}'], networkIds=['n']) for i in range(64)]
    segment = dict(id='s', kind='DEPENDENCY_ROAD', access=False, width=1.2,
                   start=[0, 0], end=[7, 0], routeIds=[r['id'] for r in routes])
    return scene, dict(version='visual-access/0.3', status='COMPLETE', unresolvedEdgeIds=[],
                       routes=routes, segments=[segment])


class RoadHierarchyTests(unittest.TestCase):
    def test_thresholds_and_nontraffic_grades(self):
        cases = [(False, 3, 16, 3, 'ALLEY'), (False, 100, 2, 100, 'ALLEY'),
                 (False, 4, 3, 0, 'STREET'), (False, 23, 8, 0, 'STREET'),
                 (False, 24, 7, 0, 'STREET'), (False, 24, 8, 0, 'AVENUE'),
                 (False, 63, 16, 16, 'AVENUE'), (False, 64, 15, 16, 'AVENUE'),
                 (False, 64, 16, 15, 'AVENUE'), (False, 64, 16, 16, 'TRUNK'),
                 (True, 1000, 1000, 1000, 'ACCESS')]
        for access, edges, files, cross, expected in cases:
            self.assertEqual(demand_grade(access, edges, files, cross), expected)

    def test_deduplication_clearance_and_no_mutation(self):
        scene, routing = fixture()
        originals = copy.deepcopy((scene, routing))
        profile = derive_road_hierarchy(scene, routing)['segments']['s']
        self.assertEqual(profile['grade'], 'TRUNK')
        for key, expected in [('edgeCount', 64), ('crossDistrictEdgeCount', 64),
                              ('sourceCount', 8), ('targetCount', 8), ('buildingCount', 16),
                              ('majorDistrictCount', 2), ('unassignedBuildingCount', 0)]:
            self.assertEqual(profile[key], expected)
        self.assertEqual(profile['width'], 1.2)
        self.assertTrue(profile['clearanceLimited'])
        self.assertEqual((scene, routing), originals)

    def test_unknown_ownership_never_invents_a_major_district(self):
        scene, routing = fixture()
        for b in scene['buildings'][8:]:
            b['districtId'] = 'root'
        profile = derive_road_hierarchy(scene, routing)['segments']['s']
        self.assertEqual(profile['crossDistrictEdgeCount'], 0)
        self.assertEqual(profile['majorDistrictCount'], 1)
        self.assertEqual(profile['unassignedBuildingCount'], 8)
        self.assertEqual(profile['grade'], 'AVENUE')

    def test_nested_directories_are_not_extra_services(self):
        scene, routing = fixture()
        scene['districts'] += [dict(id='package', parentId='a'), dict(id='leaf', parentId='package')]
        # Keep the major selection at a: enough direct buildings remain there.
        scene['buildings'][0]['districtId'] = 'leaf'
        profile = derive_road_hierarchy(scene, routing)['segments']['s']
        self.assertEqual(profile['majorDistrictCount'], 2)
        self.assertEqual(profile['crossDistrictEdgeCount'], 64)

    def test_order_duplicate_memberships_empty_and_semantic_kind(self):
        scene, routing = fixture()
        baseline = canonical_json_bytes(derive_road_hierarchy(scene, routing))
        scene['districts'].reverse()
        scene['buildings'].reverse()
        routing['routes'].reverse()
        routing['segments'][0]['routeIds'].reverse()
        routing['segments'][0]['routeIds'] *= 2
        self.assertEqual(canonical_json_bytes(derive_road_hierarchy(scene, routing)), baseline)
        routing['segments'][0]['kind'] = 'MESSAGING_PATH'
        self.assertEqual(canonical_json_bytes(derive_road_hierarchy(scene, routing)), baseline)
        self.assertEqual(derive_road_hierarchy(dict(districts=[], buildings=[]), dict(routes=[], segments=[]))['segments'], {})

    def test_svg_preserves_full_grade_when_filtered_and_semantic_color(self):
        scene, routing = fixture()
        profile = derive_road_hierarchy(scene, routing)
        for r in routing['routes'][1:]:
            r['networkIds'] = ['hidden']
        svg = '\n'.join(svg_access_lines(routing, lambda x, z: (x, z), network_ids={'n'}, hierarchy=profile))
        self.assertIn('data-road-grade="TRUNK"', svg)
        self.assertIn('64 unique edges', svg)
        self.assertIn('1 visible evidenced relation paths', svg)
        self.assertIn('0.000,-0.600 7.000,-0.600', svg)
        routing['segments'][0]['kind'] = 'HTTP_HIGHWAY'
        svg = '\n'.join(svg_access_lines(routing, lambda x, z: (x, z), hierarchy=profile))
        self.assertIn('fill="#f97316"', svg)


if __name__ == '__main__':
    unittest.main()
