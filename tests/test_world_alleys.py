"""Long rows gain only rare, safe, connected structural cuts."""

import copy
import math
import unittest
from unittest.mock import patch

from metropogits.street_diagonals import overlap
from metropogits.world.alleys import add_alleys, MIN_SPACING, WIDTH
from metropogits.world.geometry import rectangle, ribbon
from metropogits.world.infrastructure import atomic_streets


def fixture(count=14):
    streets = [dict(start=a, end=b, width=3, access=False) for a, b in (
        ([-12, 0], [12*count, 0]), ([-12, 24], [12*count, 24]),
        ([-12, 0], [-12, 24]), ([12*count, 0], [12*count, 24]))]
    parcels = []
    for row, z in enumerate((6, 18)):
        for i in range(count):
            x, angle = i*12, row*math.pi
            parcels.append(dict(entityId=f"row{row}-{i}", districtId="parent", zoneId="zone",
                                center=[x, z], angle=angle, streetPoint=[x, row*24],
                                parcel=rectangle([x, z], angle, 8, 8)))
            streets.append(dict(start=[x, row*24], end=[x, z-3 if row == 0 else z+3],
                                width=.7, access=True))
    districts = [dict(id="parent", polygon=[[-16, -8], [12*count+4, -8],
                                            [12*count+4, 32], [-16, 32]])]
    return atomic_streets(streets), parcels, districts


class AlleyTests(unittest.TestCase):
    def test_sparse_full_width_cuts_preserve_parcels_and_connect_existing_streets(self):
        streets, parcels, districts = fixture()
        original = copy.deepcopy((streets, parcels, districts))
        extra, note = add_alleys(streets, parcels, districts)
        self.assertEqual(len(extra), 1)
        self.assertIsNone(note["budgetExhausted"])
        self.assertEqual((streets, parcels, districts), original)
        self.assertEqual((extra, note), add_alleys(streets[::-1], parcels[::-1], districts))
        physical = atomic_streets(streets + extra)
        for s in extra:
            self.assertEqual(s["width"], WIDTH)
            self.assertFalse(s["access"])
            for p in parcels:
                self.assertFalse(overlap(ribbon(s["start"], s["end"], WIDTH+.4), p["parcel"]))
            for at in (s["start"], s["end"]):
                self.assertGreaterEqual(sum(at in (e["start"], e["end"]) for e in physical), 3)
        self.assertGreaterEqual(len(note["corridors"][0]["rowEntityIds"]), 6)

    def test_short_rows_and_fully_blocked_gaps_gain_no_alley(self):
        self.assertEqual(add_alleys(*fixture(3))[0], [])
        streets, parcels, districts = fixture()
        parcels.append(dict(entityId="barrier", districtId="parent", zoneId="zone",
                            center=[72, 12], angle=0, streetPoint=[72, 0],
                            parcel=rectangle([72, 12], 0, 190, 2)))
        self.assertEqual(add_alleys(streets, parcels, districts)[0], [])

    def test_nearby_cross_streets_suppress_redundant_cuts(self):
        streets, parcels, districts = fixture()
        streets = atomic_streets(streets + [dict(start=[x, 0], end=[x, 24], width=1.6, access=False)
                                          for x in range(6, 12*14, 12)])
        self.assertEqual(add_alleys(streets, parcels, districts)[0], [])

    def test_frequency_is_bounded_even_on_very_long_rows(self):
        streets, parcels, districts = fixture(100)
        extra, note = add_alleys(streets, parcels, districts)
        self.assertEqual(len(extra), 2)
        centers = [s["center"] for s in note["corridors"]]
        self.assertGreaterEqual(math.dist(*centers), MIN_SPACING)
        with patch("metropogits.world.alleys.MAX_ALLEYS", 1):
            self.assertEqual(len(add_alleys(streets, parcels, districts)[0]), 1)

    def test_budget_exhaustion_retains_safe_original_input(self):
        for key in ("MAX_INDEX", "MAX_CHECKS", "MAX_CANDIDATES", "MAX_STATES"):
            with self.subTest(key=key), patch("metropogits.world.alleys."+key, 0):
                extra, note = add_alleys(*fixture())
                self.assertEqual(extra, [])
                self.assertTrue(note["budgetExhausted"])


if __name__ == "__main__":
    unittest.main()
