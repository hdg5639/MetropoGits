import copy
import unittest
from unittest.mock import patch

from metropogits.street_surfaces import tapered_surfaces
from metropogits.structural_streets import street_rectangles
from metropogits.access_routes import svg_access_lines


def segment(name, a, b, width, **extra):
    return dict(id=name, start=a, end=b, width=width, semantic=False, **extra)


class StreetSurfaceTests(unittest.TestCase):
    def test_transition_is_continuous_bounded_and_ends_at_full_width(self):
        source = [segment('narrow', [0,0], [7,0], .75),
                  segment('wide', [7,0], [35,0], 3.5)]
        frozen = copy.deepcopy(source)
        surfaces = tapered_surfaces(source)
        wide = [s for s in surfaces if s['segmentId'] == 'wide']
        self.assertGreater(len(wide), 1)
        self.assertEqual(.75, max(p[1] for p in wide[0]['points'] if p[0] == 7)*2)
        self.assertEqual(3.5, wide[-1]['depth'])
        self.assertEqual(source, frozen)
        self.assertEqual(surfaces, tapered_surfaces(source[::-1]))
        self.check_subset(source, surfaces)

    def check_subset(self, segments, surfaces):
        originals = {s['id']: s for s in segments}
        for surface in surfaces:
            s = originals[surface['segmentId']]
            a,b = s['start'],s['end']
            horizontal = a[1] == b[1]
            axis, cross = (0,1) if horizontal else (1,0)
            for p in surface['points']:
                self.assertLessEqual(min(a[axis],b[axis]), p[axis])
                self.assertLessEqual(p[axis], max(a[axis],b[axis]))
                self.assertLessEqual(abs(p[cross]-a[cross]), s['width']/2+1e-9)
            self.assertFalse(surface['semantic'])
        self.assertEqual(set(originals), {s['segmentId'] for s in surfaces})

    def test_interior_t_junction_and_crossing_share_width_without_moving_centerlines(self):
        source = [segment('trunk', [0,0], [28,0], 3.5),
                  segment('branch', [14,0], [14,7], .75),
                  segment('cross', [14,-7], [14,0], 1.5)]
        surfaces = tapered_surfaces(source)
        self.check_subset(source, surfaces)
        for s in surfaces:
            if s['segmentId'] == 'trunk':
                for x,z in s['points']:
                    if x == 14:
                        self.assertAlmostEqual(.375, abs(z))

    def test_door_stub_does_not_narrow_trunk_and_uniform_run_is_one_quad(self):
        source = [segment('trunk',[0,0],[70,0],3.5),
                  segment('door',[35,0],[35,.5],.7,entrance=True)]
        surfaces = tapered_surfaces(source)
        self.assertEqual(2,len(surfaces))
        self.assertEqual(3.5,next(s for s in surfaces if s['segmentId']=='trunk')['depth'])
        self.check_subset(source, surfaces)

    def test_short_wide_gap_does_not_become_a_diamond(self):
        source = [segment('left',[0,0],[7,0],.75),
                  segment('bulge',[7,0],[21,0],3.5),
                  segment('right',[21,0],[28,0],.75)]
        surfaces=tapered_surfaces(source)
        self.assertEqual(.75,next(s for s in surfaces if s['segmentId']=='bulge')['depth'])
        self.check_subset(source,surfaces)

    def test_empty_reverse_vertical_legacy_and_resource_limit(self):
        self.assertEqual([],tapered_surfaces([]))
        source = [segment('vertical',[0,28],[0,0],3.5),segment('thin',[0,35],[0,28],.75)]
        self.check_subset(source,tapered_surfaces(source))
        legacy = street_rectangles(dict(streetGrid=dict(version='structural-streets/0.1',segments=source)))
        self.assertTrue(all('points' not in s for s in legacy))
        with patch('metropogits.street_surfaces.MAX_SAMPLES',2):
            with self.assertRaisesRegex(ValueError,'sample limit'):
                tapered_surfaces(source)

    def test_cpu_preview_uses_the_same_taper_points_as_viewer_packaging(self):
        source = [segment('thin',[0,0],[7,0],.75),segment('wide',[7,0],[35,0],3.5)]
        routing = dict(version='visual-access/0.3',status='COMPLETE',unresolvedEdgeIds=[],
            routes=[],segments=[],streetGrid=dict(version='structural-streets/0.2',segments=source,
                assignment=dict(assignedRouteIds=[])))
        surfaces = street_rectangles(routing)
        svg = '\n'.join(svg_access_lines(routing,lambda x,z:(x,z)))
        self.assertEqual(svg,'\n'.join(svg_access_lines(routing,lambda x,z:(x,z))))
        for s in surfaces:
            encoded = ' '.join(f'{x:.3f},{z:.3f}' for x,z in s['points'])
            self.assertIn(f'points="{encoded}"',svg)
        self.assertIn('not source relationships',svg)
