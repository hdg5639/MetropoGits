"""Pavement coverage is preserved, while coplanar overdraw and stray paint go."""

import copy
import unittest
from unittest.mock import patch

from metropogits.block_orientation import clip
from metropogits.world.geometry import area, inside, ribbon
from metropogits.world.street_hierarchy import marking_surfaces
from metropogits.world.street_mesh import street_mesh
from test_world_street_mesh import world


class StreetCleanupTests(unittest.TestCase):
    def assert_disjoint(self, mesh):
        for i, a in enumerate(mesh):
            for b in mesh[:i]:
                self.assertLess(area(clip(a["points"], b["points"])), 0.00015)

    def test_single_owner_asphalt_keeps_union_coverage_not_layered_rectangles(self):
        roads = [
            dict(id="east", start=[0, 0], end=[20, 0], width=4),
            dict(id="north", start=[0, 0], end=[0, 20], width=4),
        ]
        w = world(roads, ["COLLECTOR", "LOCAL"])
        saved = copy.deepcopy(w)
        mesh = street_mesh(w)
        self.assert_disjoint(mesh)
        # Two80-unit rectangles,4 shared units, plus2-unit safe outer bevel.
        self.assertAlmostEqual(sum(area(m["points"]) for m in mesh), 158, places=4)
        self.assertEqual(w, saved)
        w["streets"].reverse()
        self.assertEqual(street_mesh(w), mesh)

    def test_overlapping_walks_also_form_a_single_surface_without_changing_modes(self):
        roads = [
            dict(id="east", start=[0, 0], end=[20, 0], width=4),
            dict(id="north", start=[0, 0], end=[0, 20], width=4),
        ]
        mesh = street_mesh(world(roads, ["PEDESTRIAN", "PEDESTRIAN"]))
        self.assert_disjoint(mesh)
        self.assertAlmostEqual(sum(area(m["points"]) for m in mesh), 158, places=4)
        self.assertTrue(all(m["streetClass"] == "PEDESTRIAN" for m in mesh))

    def test_junction_class_comes_from_hierarchy_not_accidental_maximum_width(self):
        roads = [
            dict(id="arterial", start=[0, 0], end=[20, 0], width=3),
            dict(id="local", start=[0, 0], end=[0, 20], width=5),
        ]
        mesh = street_mesh(world(roads, ["ARTERIAL", "LOCAL"]))
        corner = [
            m
            for m in mesh
            if inside([-0.3, -0.3], list(reversed(m["points"])), 0.00001)
        ]
        self.assertTrue(corner)
        self.assertTrue(all(m["streetClass"] == "ARTERIAL" for m in corner))

    def test_narrow_forks_do_not_leave_crossing_dashes_in_the_shared_mouth(self):
        roads = [
            dict(id="main", start=[0, 0], end=[40, 0], width=4),
            dict(id="branch", start=[0, 0], end=[40, 6], width=4),
        ]
        w = world(roads, ["COLLECTOR", "COLLECTOR"])
        saved = copy.deepcopy(w)
        markings = marking_surfaces(w)
        self.assertTrue(markings)
        lookup = {s["id"]: s for s in roads}
        for m in markings:
            other = lookup["main" if m["physicalId"] == "branch" else "branch"]
            self.assertLess(
                area(clip(m["points"], ribbon(other["start"], other["end"], 4))),
                0.00015,
            )
            self.assertTrue(m["structuralMarking"])
        self.assertEqual(w, saved)
        self.assertEqual(markings, marking_surfaces(w))

    def test_collinear_atomic_spans_keep_paint_and_overpasses_keep_their_levels(self):
        roads = [
            dict(id="a", start=[-20, 0], end=[0, 0], width=4),
            dict(id="b", start=[0, 0], end=[20, 0], width=4),
        ]
        w = world(roads, ["COLLECTOR", "COLLECTOR"])
        marks = marking_surfaces(w)
        self.assertEqual({m["physicalId"] for m in marks}, {"a", "b"})
        roads = [
            dict(
                id="bridge", start=[-20, 0], end=[20, 0], width=4, bridgeId="elevated"
            ),
            dict(id="ground", start=[0, -20], end=[0, 20], width=4),
        ]
        w = world(roads, ["COLLECTOR", "COLLECTOR"])
        mesh = street_mesh(w)
        self.assertGreater(sum(area(m["points"]) for m in mesh), 300)
        marks = marking_surfaces(w)
        self.assertTrue(
            any(
                area(clip(m["points"], ribbon([0, -20], [0, 20], 4))) > 0.001
                for m in marks
                if m["physicalId"] == "bridge"
            )
        )

    def test_work_exhaustion_is_explicit(self):
        roads = [
            dict(id="a", start=[0, 0], end=[40, 0], width=4),
            dict(id="b", start=[0, 0], end=[40, 6], width=4),
        ]
        w = world(roads, ["COLLECTOR", "COLLECTOR"])
        with (
            patch("metropogits.world.street_markings.MAX_INDEX", 0),
            self.assertRaisesRegex(ValueError, "limit"),
        ):
            marking_surfaces(w)
        with (
            patch("metropogits.world.street_mesh.MAX_WORK", 0),
            self.assertRaisesRegex(ValueError, "limit"),
        ):
            street_mesh(w)
