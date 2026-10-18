import copy
import math
import unittest
from unittest.mock import patch

from metropogits.street_diagonals import arrangement, plan_diagonals, PhysicalMap, ribbon, overlap
from metropogits.street_curves import curved_presentation


def fixture():
    streets = [dict(id=str(i), start=a, end=b, width=2, semantic=False)
               for i, (a, b) in enumerate([([0, 0], [21, 0]), ([21, 0], [21, 21]),
                                          ([0, 0], [-14, 0]), ([0, 0], [0, -14])])]
    access = [dict(s, kind='DEPENDENCY_ROAD', access=False, routeIds=['r']) for s in streets[:2]]
    for s in access:
        s.pop('semantic')
    routing = dict(streetGrid=dict(version='structural-streets/0.2', segments=streets),
                   segments=access, routes=[dict(id='r', path=[[0, 0], [21, 0], [21, 21]], edgeIds=['e'])])
    return dict(buildings=[]), routing


class StreetDiagonalTests(unittest.TestCase):
    def test_chord_and_oblique_junction_preserve_terminals(self):
        scene, routing = fixture()
        plan = plan_diagonals(scene, routing)
        self.assertEqual(len(plan['chains']), 1)
        chain = plan['chains'][0]
        self.assertEqual(chain['path'], [[0, 0], [21, 0], [21, 21]])
        self.assertEqual(chain['physical'], [[0, 0], [10.5, 10.5], [21, 21]])
        self.assertAlmostEqual(plan['afterLength'], math.sqrt(2)*21)
        mapper = PhysicalMap(plan)
        forward = list(mapper.spans([0, 0], [21, 0]))
        reverse = list(mapper.spans([21, 21], [21, 0]))
        self.assertEqual((forward[0][2], forward[-1][3]), ([0, 0], [10.5, 10.5]))
        self.assertEqual((reverse[0][2], reverse[-1][3]), ([21, 21], [10.5, 10.5]))
        self.assertEqual(list(mapper.spans([-14, 0], [0, 0]))[0][2:], ([-14, 0], [0, 0], None))

    def test_crossings_collinear_overlaps_and_interior_door(self):
        scene, routing = fixture()
        streets = routing['streetGrid']['segments']
        streets.append(dict(id='cross', start=[14, -7], end=[14, 7], width=1, semantic=False))
        edges, adj = arrangement(streets)
        self.assertEqual(len(adj[(14, 0)]), 4)
        self.assertIn(((0, 0), (14, 0)), edges)
        # Crossing remains a terminal, never removed by a chord.
        for c in plan_diagonals(scene, routing)['chains']:
            self.assertNotIn([14, 0], c['path'][1:-1])
        scene, routing = fixture()
        routing['routes'].append(dict(path=[[21, 0], [30, 0]]))
        self.assertEqual(plan_diagonals(scene, routing)['chains'], [])

    def test_full_width_collision_and_new_crossing_rejected(self):
        scene, routing = fixture()
        # Centerline clears this box, but the full road does not.
        scene['buildings'] = [dict(x=9, z=10, width=.5, depth=.5)]
        plan = plan_diagonals(scene, routing)
        self.assertEqual(plan['chains'], [])
        self.assertEqual(plan['rejected']['building'], 1)
        scene, routing = fixture()
        routing['streetGrid']['segments'].append(dict(id='other', start=[8, 10], end=[14, 10], width=1, semantic=False))
        self.assertEqual(plan_diagonals(scene, routing)['rejected']['street'], 1)

    def test_input_order_evidence_counts_and_nonmutation(self):
        scene, routing = fixture()
        frozen = copy.deepcopy(routing)
        plan = plan_diagonals(scene, routing)
        self.assertEqual(routing, frozen)
        routing['segments'].reverse()
        routing['streetGrid']['segments'].reverse()
        for s in routing['streetGrid']['segments']+routing['segments']:
            s['start'], s['end'] = s['end'], s['start']
        routing['routes'][0]['edgeIds'] = ['other']*100
        self.assertEqual(plan, plan_diagonals(scene, routing))

    def test_shared_presentation_and_unaffected_tapers(self):
        scene, routing = fixture()
        routing['diagonalPlan'] = plan_diagonals(scene, routing)
        from metropogits.structural_streets import street_rectangles
        from metropogits.street_demand import demand_pavement
        hierarchy = dict(segments={s['id']: dict(width=2, lanePattern='DASHED') for s in routing['segments']})
        surfaces = street_rectangles(routing)
        pavement = demand_pavement(routing, hierarchy, surfaces)
        frozen = copy.deepcopy((routing, surfaces, pavement))
        result = curved_presentation(routing, surfaces, pavement, hierarchy)
        self.assertEqual(result, curved_presentation(routing, surfaces, pavement, hierarchy))
        self.assertEqual(frozen, (routing, surfaces, pavement))
        ss, pp, physical = result
        self.assertEqual(physical['segments']['0'][-1], physical['segments']['1'][0])
        self.assertTrue(physical['paintSegments']['0'])
        for surface in ss:
            ps = surface['points']
            area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ps, ps[1:]+ps[:1]))
            self.assertLess(area, 0)
        for s in surfaces:
            if s['segmentId'] in ('2', '3'):
                self.assertIn(s, ss)
        for p in pp['segments']['0']:
            self.assertAlmostEqual(p['start'][0], p['start'][1])
        for p in physical['paintSegments']['0']:
            self.assertAlmostEqual(p['start'][0], p['start'][1])

    def test_modes_and_caps_fail_explicitly(self):
        scene, routing = fixture()
        with self.assertRaisesRegex(ValueError, 'aligned'):
            plan_diagonals(scene, {})
        routing['curvePlan'] = {'corners': []}
        with self.assertRaisesRegex(ValueError, 'corner'):
            plan_diagonals(scene, routing)
        with patch('metropogits.street_diagonals.MAX_EDGES', 1):
            with self.assertRaisesRegex(ValueError, 'limit'):
                arrangement(routing['streetGrid']['segments'])
        with patch('metropogits.street_diagonals.MAX_CHECKS', 1):
            routing.pop('curvePlan')
            with self.assertRaisesRegex(ValueError, 'limit'):
                plan_diagonals(scene, routing)
        with self.assertRaisesRegex(ValueError, 'finite'):
            arrangement([dict(start=[0, 0], end=[1, 0], width=float('nan'))])
        from scripts.street_grid import compare
        with self.assertRaisesRegex(ValueError, 'aligned'):
            compare({}, {}, diagonals=True)

    def test_unrelated_parallel_road_stays_fixed(self):
        scene, routing = fixture()
        routing['streetGrid']['segments'].append(dict(id='parallel', start=[0, -8], end=[21, -8], width=1, semantic=False))
        plan = plan_diagonals(scene, routing)
        self.assertTrue(plan['chains'])
        self.assertEqual(list(PhysicalMap(plan).spans([0, -8], [21, -8]))[0][2:], ([0, -8], [21, -8], None))
        self.assertFalse(overlap(plan['chains'][0]['polygon'], ribbon([0, -8], [21, -8], 1)))

    def test_short_throat_does_not_thin_whole_corridor(self):
        scene, routing = fixture()
        routing['streetGrid']['segments'][0]['width'] = .76
        routing['streetGrid']['segments'][1]['width'] = 3.5
        plan = plan_diagonals(scene, routing)
        chain = plan['chains'][0]
        self.assertEqual(chain['widths'], [.76, 3.5, 3.5, 3.5])
        spans = list(PhysicalMap(plan).spans([0, 0], [21, 0]))
        self.assertAlmostEqual(spans[0][4][0], .76)
        self.assertAlmostEqual(spans[-1][4][-1], 3.5)
        for left, right in zip(spans, spans[1:]):
            self.assertEqual(left[3], right[2])
            self.assertAlmostEqual(left[4][1], right[4][0])

    def test_real_pipeline_repeated_package_and_canonical_identity(self):
        from pathlib import Path
        from scripts.canonical_json import loads_strict_json
        from metropogits.layout import generate_city
        from scripts.street_grid import compare
        from scripts.road_consolidation import package
        graph = loads_strict_json((Path(__file__).parent/'fixtures/ucg/valid/spring-minimal.json').read_text(encoding='utf8'))
        scene = generate_city(graph)
        frozen = copy.deepcopy((scene, graph))
        _, routing, report = compare(scene, graph, aligned=True, diagonals=True)
        output = package(scene, graph, routing, report)
        self.assertEqual(output, package(scene, graph, routing, report))
        self.assertEqual((scene, graph), frozen)
        self.assertIn(b'street-diagonals/0.1', output['assets/viewer-data.js'])
        self.assertIn(b'civic-infrastructure', output['preview.svg'])
