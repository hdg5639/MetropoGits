"""One physical presentation mesh for curves, curbs, CPU and both viewers."""

import copy
import unittest
from unittest.mock import patch

from metropogits.street_diagonals import overlap
from metropogits.world.geometry import rectangle, ribbon
from metropogits.world.street_mesh import street_mesh


def world(roads, classes):
    return dict(
        streets=[dict(s, access=s.get("access", False)) for s in roads],
        parcels=[],
        streetPlan=dict(
            segments={r["id"]: dict(streetClass=c) for r, c in zip(roads, classes)}
        ),
    )


class StreetMeshTests(unittest.TestCase):
    def test_pedestrian_and_service_paint_stops_at_vehicle_curb_without_changing_routes(
        self,
    ):
        roads = [
            dict(id="car", start=[-20, 0], end=[20, 0], width=4),
            dict(id="walk", start=[0, -12], end=[0, 0], width=1.2),
            dict(id="door", start=[10, -5], end=[10, 0], width=0.7, access=True),
        ]
        w = world(roads, ["LOCAL", "PEDESTRIAN", "SERVICE"])
        saved = copy.deepcopy(w)
        mesh = street_mesh(w)
        car = ribbon(roads[0]["start"], roads[0]["end"], 4)
        walks = [m for m in mesh if m["streetClass"] in ("PEDESTRIAN", "SERVICE")]
        self.assertTrue(walks)
        self.assertFalse(any(overlap(m["points"], car) for m in walks))
        self.assertEqual(w, saved)
        self.assertEqual(mesh, street_mesh(w))
        self.assertTrue(all(len(m["points"]) == 4 for m in mesh))

    def test_bend_join_fills_outer_gap_without_miter_spikes_or_neighbor_invasion(self):
        roads = [
            dict(id="a", start=[0, 0], end=[20, 0], width=4),
            dict(id="b", start=[0, 0], end=[0, 20], width=4),
        ]
        w = world(roads, ["LOCAL", "LOCAL"])
        mesh = street_mesh(w)
        parcel = rectangle([-0.5, -0.5], 0, 0.3, 0.3)
        self.assertTrue(any(overlap(m["points"], parcel) for m in mesh))
        # Every added corner stays within the half-width disk: no acute miter.
        for m in mesh:
            for x, z in m["points"]:
                if x < 0 and z < 0:
                    self.assertLessEqual(x * x + z * z, 4.0001)
        w["parcels"] = [dict(parcel=parcel)]
        safe = street_mesh(w)
        self.assertFalse(any(overlap(m["points"], parcel) for m in safe))
        self.assertLess(len(safe), len(mesh))

    def test_crossing_levels_and_resource_limits_do_not_get_hidden_by_cosmetics(self):
        roads = [
            dict(id="a", start=[0, 0], end=[20, 0], width=4, bridgeId="bridge"),
            dict(id="b", start=[0, 0], end=[0, 20], width=4),
        ]
        w = world(roads, ["LOCAL", "LOCAL"])
        self.assertEqual(len(street_mesh(w)), 4)
        with (
            patch("metropogits.world.street_mesh.MAX_INDEX", 0),
            self.assertRaisesRegex(ValueError, "limit"),
        ):
            street_mesh(w)

    def test_curved_pedestrian_loop_has_join_faces_too_without_painting_the_carriageway(
        self,
    ):
        roads = [
            dict(id="a", start=[0, 0], end=[10, 0], width=1.2),
            dict(id="b", start=[0, 0], end=[0, 10], width=1.2),
        ]
        mesh = street_mesh(world(roads, ["PEDESTRIAN", "PEDESTRIAN"]))
        self.assertGreater(len(mesh), 4)
        self.assertTrue(
            any(
                overlap(m["points"], rectangle([-0.15, -0.15], 0, 0.1, 0.1))
                for m in mesh
            )
        )
