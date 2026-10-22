import copy
import unittest

from metropogits.world.district_skyline import district_skyline, allocated_height
from metropogits.world.architecture_catalog import catalog_world
from metropogits.world.architecture_height import height_capacity
from test_reference_skyline import fixture


class DistrictSkylineTests(unittest.TestCase):
    def test_continuous_context_is_not_a_reference_hub_or_source_facility(self):
        w, g, ids = fixture()
        plan = district_skyline(w, g)
        without = district_skyline(w, dict(g, edges=[]))
        self.assertEqual(plan["allocations"], without["allocations"])
        self.assertEqual(plan["districts"]["owner"]["preferredTypology"], "CONVENTIONAL_MIXED_USE")
        self.assertEqual(plan["districts"]["owner"]["centers"][0]["center"], [16, 4])
        center = plan["allocations"][ids[2]]
        edge = plan["allocations"][ids[0]]
        self.assertGreater(center["fieldIntensity"], edge["fieldIntensity"])
        self.assertGreater(allocated_height(42, "tower", center), allocated_height(42, "tower", edge))
        self.assertLess(allocated_height(42, "tower", center), 42)
        self.assertGreater(allocated_height(140, "tower", center), 42)

    def test_order_duplicate_observations_and_unrelated_owner_cannot_reshuffle_heights(self):
        w, g, _ = fixture()
        a, profiles = catalog_world(w, g)
        saved = copy.deepcopy((w, g))
        changed = copy.deepcopy(g)
        changed["edges"] += copy.deepcopy(g["edges"])
        for key in ("edges", "entities", "evidence"):
            changed[key].reverse()
        b = catalog_world(dict(w, parcels=list(reversed(w["parcels"]))), changed)[0]
        self.assertEqual({p["entityId"]: p for p in a["parcels"]},
                         {p["entityId"]: p for p in b["parcels"]})
        c = copy.deepcopy(w)
        c["parcels"].append(dict(c["parcels"][0], entityId="other", districtId="other", center=[500, 500]))
        changed["entities"].append(dict(id="other", kind="FILE", path="other/file.py", roles=[]))
        self.assertEqual(a["parcels"], catalog_world(c, changed)[0]["parcels"][:-1])
        self.assertEqual((w, g), saved)
        for p in a["parcels"]:
            self.assertEqual(p["height"], profiles[p["entityId"]]["heightAllocation"]["allocatedHeight"])
            self.assertLessEqual(p["height"], profiles[p["entityId"]]["heightPolicy"]["capacity"])

    def test_composition_does_not_move_or_remove_horizontal_source_geography(self):
        w, g, _ = fixture()
        a, profiles = catalog_world(w, g)
        self.assertEqual(len(a["parcels"]), len(w["parcels"]))
        for before, after in zip(w["parcels"], a["parcels"]):
            self.assertEqual({k: v for k, v in before.items() if k != "height"},
                             {k: after[k] for k in before if k != "height"})
            self.assertEqual(after["sourceHeight"], before["height"])
            profile = profiles[before["entityId"]]
            self.assertEqual(height_capacity(before, profile["heightPolicy"]["form"]), profile["heightPolicy"]["capacity"])
        for v in (-1, 1.1, float("nan")):
            with self.assertRaises(ValueError):
                allocated_height(42, "tower", dict(fieldIntensity=v))


if __name__ == "__main__":
    unittest.main()
