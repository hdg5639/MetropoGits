import copy
import json
import unittest
from unittest.mock import patch

from metropogits.street_diagonals import overlap
from metropogits.world.export import package_world, view_data
from metropogits.world.geometry import area, inside, ribbon
from metropogits.world.landscape import expanded, generate_landscape, subtract
from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world
from test_procedural_world import fixture


def land():
    return dict(seed="landscape-fixture", districts=[dict(id="parent", polygon=[
        [-65, -65], [65, -65], [65, 65], [-65, 65]])],
        parcels=[dict(entityId="actual-file", parcel=[[-30, -30], [-10, -30], [-10, -10], [-30, -10]])],
        streets=[dict(id="main", start=[-65, 0], end=[65, 0], width=6, access=False),
                 dict(id="driveway", start=[-20, -10], end=[-20, 0], width=.7, access=True),
                 dict(id="cross", start=[0, -65], end=[0, 65], width=8, access=False)])


class LandscapeTests(unittest.TestCase):
    def test_convex_subtraction_retains_safe_area_not_an_aabb(self):
        square = [[-10, -10], [10, -10], [10, 10], [-10, 10]]
        diamond = [[0, -5], [5, 0], [0, 5], [-5, 0]]
        parts = subtract(square, diamond)
        self.assertAlmostEqual(sum(area(p) for p in parts), 350)
        for i, p in enumerate(parts):
            self.assertFalse(overlap(p, diamond))
            self.assertTrue(all(inside(v, square) for v in p))
            for other in parts[i + 1:]:
                self.assertFalse(overlap(p, other))
        self.assertGreater(area(expanded(diamond, .6)), area(diamond))
        self.assertTrue(all(inside(v, expanded(diamond, .6), .59) for v in diamond))

    def test_every_patch_and_tree_avoids_real_parcels_streets_and_doors(self):
        w = land()
        result = generate_landscape(w)
        self.assertTrue(result["decorative"])
        self.assertIsNone(result["diagnostics"]["budgetExhausted"])
        self.assertGreater(len(result["patches"]), 0)
        self.assertGreater(len(result["trees"]), 0)
        obstacles = [p["parcel"] for p in w["parcels"]] + [
            ribbon(s["start"], s["end"], s["width"]) for s in w["streets"]]
        patches = {p["id"]: p for p in result["patches"]}
        for p in patches.values():
            self.assertTrue(all(inside(v, w["districts"][0]["polygon"]) for v in p["polygon"]))
            self.assertFalse(any(overlap(p["polygon"], o) for o in obstacles))
            self.assertNotIn("entityId", p)
            self.assertNotIn("edgeIds", p)
        for t in result["trees"]:
            if t.get("kind") == "STREET_TREE":
                self.assertFalse(any(overlap(
                    [[t["center"][0] + t["radius"] * c, t["center"][1] + t["radius"] * s]
                     for c, s in ((1, 0), (0, 1), (-1, 0), (0, -1))], o) for o in obstacles))
                continue
            for face in t["faces"]:
                self.assertTrue(all(inside([x, z], patches[t["patchId"]]["polygon"])
                                    and 0 <= y <= t["height"] for x, y, z in face["points"]))

    def test_repetition_order_and_administrative_cuts_do_not_change_planting(self):
        w = land()
        original = copy.deepcopy(w)
        a = generate_landscape(w)
        self.assertEqual(w, original)
        self.assertEqual(a, generate_landscape(w))
        w["streets"].reverse()
        w["zoning"] = dict(zones=[dict(id="a-new-administrative-cut")])
        self.assertEqual(a, generate_landscape(w))

    def test_optional_budget_exhaustion_never_uses_an_incomplete_obstacle_index(self):
        w = land()
        with patch("metropogits.world.landscape.MAX_INDEX", 1):
            result = generate_landscape(w)
        self.assertEqual(result["patches"], [])
        self.assertEqual(result["trees"], [])
        self.assertEqual(result["diagnostics"]["budgetExhausted"], "spatial index")
        with patch("metropogits.world.landscape.MAX_CHECKS", 0):
            result = generate_landscape(w)
        self.assertEqual(result["diagnostics"]["budgetExhausted"], "obstacle checks")
        self.assertLessEqual(result["diagnostics"]["checks"], 1)
        with patch("metropogits.world.landscape.MAX_BROAD_CHECKS", 0):
            result = generate_landscape(w)
        self.assertEqual(result["diagnostics"]["budgetExhausted"], "broad phase")
        with patch("metropogits.world.landscape.MAX_CANDIDATES", 2):
            result = generate_landscape(w)
        self.assertEqual(result["diagnostics"]["budgetExhausted"], "candidates")
        self.assertEqual(result["diagnostics"]["candidates"], 3)

    def test_export_continuous_ground_preserves_all_truth_and_geometry(self):
        scene, graph = fixture()
        world = generate_world(scene, graph, zoning="neighborhoods", pattern_scale="adaptive")
        original = copy.deepcopy((world, scene, graph))
        report = validate_world(world, scene, graph)
        package = package_world(world, scene, graph, report)
        self.assertEqual(package, package_world(world, scene, graph, report))
        scape = json.loads(package["landscape.json"])
        data = view_data(world, scene, graph)
        self.assertEqual(data["landscape"], scape)
        self.assertEqual({p["districtId"] for p in data["occupiedGround"]["pads"]},
                         {d["id"] for d in world["districts"]})
        self.assertEqual(data["routing"]["routes"], world["routing"]["routes"])
        self.assertEqual(data["scene"]["decorations"], [])
        self.assertIn(b"Landscape (decorative)", package["index.html"])
        self.assertIn(b"Flat landscaping (decorative)", package["preview.svg"])
        self.assertEqual(json.loads(package["world.json"]), world)
        self.assertEqual(json.loads(package["city.json"]), scene)
        self.assertEqual(json.loads(package["graph.ucg.json"]), graph)
        self.assertEqual(original, (world, scene, graph))
        ablation = package_world(world, scene, graph, report, landscaping=False)
        self.assertNotIn("landscape.json", ablation)
        for name in ("world.json", "city.json", "graph.ucg.json", "planning.json"):
            self.assertEqual(package[name], ablation[name])

    def test_legacy_default_world_does_not_opt_into_landscaping(self):
        scene, graph = fixture()
        world = generate_world(scene, graph)
        result = package_world(world, scene, graph, validate_world(world, scene, graph))
        self.assertNotIn("landscape.json", result)
        self.assertNotIn("landscape", view_data(world, scene, graph))
