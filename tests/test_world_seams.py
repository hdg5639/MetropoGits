import copy
import unittest
from unittest.mock import patch

from metropogits.world.seams import stitch_unused_streets


def road(key, a, b, access=False):
    return dict(id=key, start=a, end=b, width=3, access=access)


class LocalSeamTests(unittest.TestCase):
    def setUp(self):
        self.streets = [
            road("duplicate", [0, 0], [30, 0]),
            road("trunk", [0, 4], [30, 4]),
            road("left", [0, 0], [0, 4]),
            road("right", [30, 0], [30, 4]),
            road("driveway", [0, 4], [-3, 4], True),
        ]
        self.reserved = [self.streets[1]]
        self.routing = dict(
            segments=[dict(physicalId="trunk")], routes=[dict(path=[[0, 4], [30, 4]])]
        )
        self.parcels = [dict(entrance=[-3, 4])]

    def run_pass(self, **kwargs):
        return stitch_unused_streets(
            kwargs.get("streets", self.streets),
            kwargs.get("reserved", self.reserved),
            kwargs.get("routing", self.routing),
            self.parcels,
        )

    def test_only_unused_duplicate_is_removed_without_moving_or_rerouting(self):
        original = copy.deepcopy(
            (self.streets, self.reserved, self.routing, self.parcels)
        )
        streets, note = self.run_pass()
        self.assertEqual(note["removedStreetIds"], ["duplicate"])
        self.assertEqual(
            {s["id"] for s in streets}, {s["id"] for s in self.streets} - {"duplicate"}
        )
        self.assertEqual(
            original, (self.streets, self.reserved, self.routing, self.parcels)
        )
        self.assertEqual(
            self.run_pass(streets=list(reversed(self.streets))), (streets, note)
        )

    def test_real_trip_and_reserved_curve_piece_are_not_thinned(self):
        protected = dict(
            segments=[dict(physicalId="duplicate"), dict(physicalId="trunk")]
        )
        streets, note = self.run_pass(routing=protected)
        self.assertEqual(len(streets), len(self.streets))
        self.assertEqual(note["removedStreetIds"], [])
        streets, note = self.run_pass(reserved=[*self.reserved, self.streets[0]])
        self.assertEqual(len(streets), len(self.streets))

    def test_connectivity_alone_is_not_a_reason_to_remove_a_road(self):
        long = [
            road("duplicate", [0, 0], [30, 0]),
            road("trunk", [0, 4], [30, 4]),
            road("left", [0, 0], [-100, 0]),
            road("detour", [-100, 0], [0, 4]),
            road("right", [30, 0], [30, 4]),
        ]
        streets, note = self.run_pass(streets=long, reserved=long[1:])
        self.assertEqual(len(streets), len(long))
        self.assertEqual(note["removedStreetIds"], [])

    def test_work_budgets_retain_geometry_instead_of_guessing(self):
        with patch("metropogits.world.seams.MAX_CHECKS", 0):
            streets, note = self.run_pass()
        self.assertEqual(len(streets), len(self.streets))
        self.assertIn("budget", note)
        with patch("metropogits.world.seams.MAX_STATES", 1):
            streets, note = self.run_pass()
        self.assertEqual(len(streets), len(self.streets))
        self.assertTrue(note["budgetExhausted"])
