import json
import unittest
from pathlib import Path

from metropogits.road_paint import dash_segments, junction_trims
from metropogits.access_routes import svg_access_lines
from metropogits.road_hierarchy import derive_road_hierarchy
from test_road_hierarchy import fixture


class RoadPaintTests(unittest.TestCase):
    def test_shared_cpu_browser_dash_contract(self):
        cases = json.loads((Path(__file__).parent/'fixtures/road-paint.json').read_text(encoding='utf-8'))
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(case['expected'], dash_segments(case['start'], case['end'], case['trims']))

    def test_visible_junctions_trim_without_cross_kind_joining(self):
        segments = [dict(id=str(i), kind='DEPENDENCY_ROAD', start=[0, 0], end=end)
                    for i, end in enumerate(([10, 0], [-10, 0], [0, 10]))]
        routing = dict(junctions=[dict(point=[0, 0], segmentIds=['0', '1', '2'])])
        widths = {s['id']: 2.5 for s in segments}
        self.assertEqual({str(i): [1.55, 0] for i in range(3)}, junction_trims(routing, segments, widths))
        self.assertEqual({}, junction_trims(routing, segments[:2], widths))
        segments[-1]['kind'] = 'HTTP_HIGHWAY'
        self.assertEqual({}, junction_trims(routing, segments, widths))

    def test_svg_paint_is_nonsemantic_and_keeps_exact_routing_metadata(self):
        scene, routing = fixture()
        routing['segments'][0]['width'] = 3.5
        hierarchy = derive_road_hierarchy(scene, routing)
        svg = '\n'.join(svg_access_lines(routing, lambda x, z: (x, z), hierarchy=hierarchy))
        self.assertIn('data-road-paint="arterial-dash"', svg)
        self.assertIn('aria-hidden="true"', svg)
        self.assertIn('64 unique edges', svg)
        self.assertEqual(1, svg.count('data-access-segment-id='))
        self.assertIn('id="access-routing"', svg)


if __name__ == '__main__':
    unittest.main()
