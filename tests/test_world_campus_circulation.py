"""Purposeful structural walking circulation does not depend on code traffic."""

import copy
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.world.campus_circulation import prune_campus_tails
from metropogits.world.generator import generate_world
from metropogits.world.geometry import nearest
from metropogits.world.infrastructure import atomic_streets
from metropogits.world.validation import validate_world
from test_world_campus import fixture
from test_world_campus_neighborhood import OPTIONS


def walk(a, b, suffix="core:0:wing:0", **fields):
    return dict(id="world:campus-court:test:" + suffix, start=a, end=b,
                width=1.2, access=False, **fields)


def clean(raw, *, parcels=(), used=(), reserved=()):
    streets = atomic_streets(raw)
    site = dict(scope="NEIGHBORHOOD", walkways=[r for r in raw if "campus" in r["id"]])
    return prune_campus_tails(streets, [site], reserved, parcels,
                              dict(segments=[dict(physicalId=k) for k in used]))


class CampusCirculationTests(unittest.TestCase):
    def test_prune_past_actual_frontage_but_keep_unknown_unreferenced_source_access(self):
        raw = [walk([0, 0], [30, 0]), walk([10, 0], [10, 4], "door")]
        raw[1].update(access=True, width=.7)
        parcel = dict(entrance=[10, 4], streetPoint=[10, 0])
        original = copy.deepcopy(raw)
        kept, note = clean(raw, parcels=[parcel], reserved=[dict(start=[0, 0], end=[0, 5])])
        # Both empty tails may go; the actual doorway spur remains despite zero trips.
        self.assertEqual(len(kept), 1)
        self.assertTrue(kept[0]["access"])
        self.assertEqual(note["removedLength"], 30)
        self.assertEqual(original, raw)

    def test_courts_promenades_gates_vehicle_and_neighbor_corridors_survive_without_traffic(self):
        raw = [walk([0, 0], [8, 0], "core:0:loop:0"),
               walk([8, 0], [16, 0], "promenade:0:1:0"),
               walk([16, 0], [24, 0], "exterior-gate:0"),
               walk([8, 0], [8, 10]),
               walk([0, 0], [-10, 0], "vehicle"),
               dict(id="neighbor", start=[24, 0], end=[34, 0], width=1.2, access=False)]
        raw[4]["width"] = 3
        kept, note = clean(raw, reserved=[raw[-1]])
        self.assertEqual(len(note["removedStreetIds"]), 1)
        self.assertEqual(note["removedLength"], 10)
        self.assertEqual(len(kept), 5)

    def test_split_intersections_frontages_routes_and_crossings_are_protected(self):
        raw = [walk([0, 0], [30, 0]), walk([15, -10], [15, 10], "core:1:wing:0"),
               walk([15, 10], [20, 10], "promenade:0:1:0")]
        streets = atomic_streets(raw)
        used = [s["id"] for s in streets if s["start"] == [0, 0]]
        kept, note = clean(raw, used=used)
        self.assertEqual(note["removedLength"], 25)
        self.assertTrue(set(used).issubset({s["id"] for s in kept}))
        self.assertTrue(any([15, 0] in (s["start"], s["end"]) for s in kept))
        streets = [dict(s, bridgeId="protected") for s in streets]
        retained, note = prune_campus_tails(streets, [dict(scope="NEIGHBORHOOD", walkways=raw)], [], [], {})
        self.assertEqual(streets, retained)
        self.assertFalse(note["removedStreetIds"])

    def test_bounds_keep_original_output_and_old_pockets_are_untouched(self):
        raw = [walk([0, 0], [30, 0])]
        with patch("metropogits.world.campus_circulation.MAX_CHECKS", 0):
            kept, note = clean(raw)
        self.assertEqual(kept, atomic_streets(raw))
        self.assertIn("limit", note["fallback"])
        self.assertFalse(note["removedStreetIds"])
        streets = atomic_streets(raw)
        self.assertEqual(prune_campus_tails(streets, [dict(walkways=raw)], [], [], {})[0], streets)

    def test_whole_pipeline_preserves_every_frame_and_exact_trip_after_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        with patch("metropogits.world.campus_circulation.prune_campus_tails",
                   side_effect=lambda streets, *args: (streets, dict(reason="test baseline"))):
            before = generate_world(scene, graph, **OPTIONS)
        after = generate_world(scene, graph, **OPTIONS)
        self.assertEqual(before["parcels"], after["parcels"])
        self.assertEqual(before["campusPlan"], after["campusPlan"])
        self.assertEqual(before["zoning"], after["zoning"])
        self.assertEqual(before["routing"], after["routing"])
        self.assertEqual(before["networks"], after["networks"])
        self.assertEqual(validate_world(after, scene, graph)["accessibleBuildings"], 48)
        note = next(n for n in after["diagnostics"] if n.get("version") == "campus-circulation/0.1")
        self.assertGreater(note["removedLength"], 70)
        kept, again = prune_campus_tails(after["streets"], after["campusPlan"]["sites"],
                                      after["zoning"]["mainRoads"] + after["topology"]["edges"],
                                      after["parcels"], after["routing"])
        self.assertEqual(after["streets"], kept)
        self.assertEqual(again["removedStreetIds"], [])
        self.assertEqual(after, generate_world(scene, graph, **OPTIONS))
        forged = copy.deepcopy(after)
        note = next(n for n in forged["diagnostics"] if n.get("version") == "campus-circulation/0.1")
        note["removedLength"] += 1
        with self.assertRaisesRegex(ValueError, "circulation"):
            validate_world(forged, scene, graph)
        # Even forged geometry/IDs cannot excuse deleting a real public loop.
        loops = [r for site in after["campusPlan"]["sites"] for r in site["walkways"]
                 if ":loop:" in r["id"]]
        protected = next(s for s in after["streets"] if s["width"] == 1.2
                         and s["id"] not in {r["physicalId"] for r in after["routing"]["segments"]}
                         and any(all(math.dist(p, nearest(p, r["start"], r["end"])) < .002
                                     for p in (s["start"], s["end"])) for r in loops))
        forged = copy.deepcopy(after)
        forged["streets"] = [s for s in forged["streets"] if s["id"] != protected["id"]]
        note = next(n for n in forged["diagnostics"] if n.get("version") == "campus-circulation/0.1")
        note["removedStreetIds"] = sorted(note["removedStreetIds"] + [protected["id"]])
        note["removedStreets"] = sorted(note["removedStreets"] + [
            {k: protected[k] for k in ("id", "start", "end", "width", "access")}], key=lambda s: s["id"])
        note["removedLength"] = round(note["removedLength"] + math.dist(protected["start"], protected["end"]), 4)
        with self.assertRaisesRegex(ValueError, "purposeful"):
            validate_world(forged, scene, graph)


if __name__ == "__main__":
    unittest.main()
