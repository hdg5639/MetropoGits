import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.access_routes import svg_access_lines
from metropogits.layout import generate_city
from metropogits.structural_streets import assign_streets, build_streets, street_rectangles
from metropogits.viewer import render_viewer
from metropogits.preview import render_preview
from metropogits.showcase import render_showcase
from scripts.canonical_json import canonical_json_bytes
from scripts.parcel_pilot import pavement_intersections
from scripts.street_grid import compare
from test_block_collectors import fixture
import test_road_frontage as frontage_checks


class StructuralStreetTests(unittest.TestCase):
    def test_geometry_is_independent_of_relations_and_input_order(self):
        scene, _ = fixture()
        frozen = copy.deepcopy(scene)
        first = canonical_json_bytes(build_streets(scene))
        self.assertEqual(frozen, scene)
        scene['networks'] = []
        scene['buildings'].reverse()
        scene['districts'].reverse()
        self.assertEqual(first, canonical_json_bytes(build_streets(scene)))

    def test_all_buildings_receive_safe_structural_access_without_dependencies(self):
        scene, _ = fixture()
        scene['networks'] = []
        streets = build_streets(scene)
        self.assertEqual('COMPLETE', streets['status'])
        self.assertEqual(1, streets['componentCount'])
        self.assertEqual(len(scene['buildings']), len(streets['entrances']))
        self.assertTrue(streets['segments'])
        self.assertEqual(0, pavement_intersections(streets, scene['buildings']))
        self.assertTrue(all(not s['semantic'] and 'edgeIds' not in s for s in streets['segments']))
        rectangles = street_rectangles({'streetGrid': streets})
        self.assertTrue(all(r['width'] > 0 and r['depth'] > 0 for r in rectangles))

    def test_assignment_preserves_all_ids_bounds_doors_and_provenance(self):
        scene, original = fixture()
        frozen = copy.deepcopy((scene, original))
        result = assign_streets(scene, original)
        self.assertEqual(frozen, (scene, original))
        frontage_checks.RoadFrontageTests().check(scene, original, result)
        report = result['streetGrid']['assignment']
        assigned, fallback = map(set, (report['assignedRouteIds'], report['fallbackRouteIds']))
        self.assertTrue(assigned)
        self.assertFalse(assigned & fallback)
        self.assertEqual({r['id'] for r in original['routes']}, assigned | fallback)
        self.assertEqual(canonical_json_bytes(result), canonical_json_bytes(assign_streets(scene, original)))

    def test_failed_search_preserves_every_route_and_discloses_fallback(self):
        scene, original = fixture()
        with patch('metropogits.structural_streets.MAX_ROUTE_STATES', 0):
            result = assign_streets(scene, original)
        self.assertEqual([], result['streetGrid']['assignment']['assignedRouteIds'])
        self.assertEqual(len(original['routes']), len(result['streetGrid']['assignment']['fallbackRouteIds']))
        frontage_checks.RoadFrontageTests().check(scene, original, result)

    def test_structural_caps_and_invalid_hierarchy_fail_safely(self):
        scene, _ = fixture()
        for limit in ('MAX_CELLS', 'MAX_BUILDINGS', 'MAX_SEED_STEPS'):
            with self.subTest(limit=limit), patch('metropogits.structural_streets.'+limit, 0):
                with self.assertRaises(ValueError):
                    build_streets(scene)
        with patch('metropogits.structural_streets.MAX_STEPS', 0):
            self.assertEqual('PARTIAL', build_streets(scene)['status'])
        scene['districts'][0]['parentId'] = 'd'
        with self.assertRaises(ValueError):
            build_streets(scene)

    def test_empty_scene_and_no_relations_remain_honest(self):
        scene, original = fixture()
        original.update(routes=[], segments=[], junctions=[])
        result = assign_streets(scene, original)
        self.assertFalse(result['routes'])
        self.assertTrue(result['streetGrid']['segments'])
        scene['buildings'] = []
        self.assertFalse(assign_streets(scene, original)['streetGrid']['segments'])

    def test_svg_discloses_infrastructure_and_retains_all_route_metadata(self):
        scene, original = fixture()
        result = assign_streets(scene, original)
        svg = '\n'.join(svg_access_lines(result, lambda x,z: (x,z)))
        self.assertIn('Structural streets: visual, not source relationships', svg)
        self.assertIn('fallbackRouteIds', svg)
        for route in original['routes']:
            self.assertIn(route['id'], svg)

    def test_opt_in_packaging_preserves_city_and_legacy_lod_obstacles(self):
        graph = json.loads((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text(encoding='utf-8'))
        scene = generate_city(graph)
        frozen = canonical_json_bytes(scene)
        before, after, _ = compare(scene, graph)
        def data(routing):
            assets = render_viewer(scene, graph, routing=routing)
            return assets, json.loads(assets['assets/viewer-data.js'].decode().split('=',1)[1].strip()[:-1])
        old, old_data = data(before)
        new, new_data = data(after)
        self.assertNotIn(b'STRUCTURAL STREET EXPERIMENT', old['index.html'])
        self.assertIn(b'STRUCTURAL STREET EXPERIMENT', new['index.html'])
        self.assertIn(b'id="street-diagnostics"', new['index.html'])
        self.assertNotIn(b'id="street-diagnostics"', old['index.html'])
        self.assertEqual(old_data['streets']['rectangles'], new_data['streets']['rectangles'])
        self.assertEqual(frozen, canonical_json_bytes(scene))
        self.assertEqual(frozen, canonical_json_bytes(new_data['scene']))
        for render in (render_preview, render_showcase):
            self.assertIn(b'Structural streets (visual)', render(scene, graph, routing=after))
            self.assertNotIn(b'Structural streets (visual)', render(scene, graph, routing=before))


if __name__ == '__main__':
    unittest.main()
