import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from test_world_planning import fixture
from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world
from metropogits.world.export import package_world


class WorldProfileTests(unittest.TestCase):
    def check_profile(self, profile):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        world = generate_world(scene, graph, planning=profile)
        report = validate_world(world, scene, graph)
        self.assertEqual(report["accessibleBuildings"], 40)
        self.assertEqual(report["trips"], 40)
        self.assertTrue(
            all(d["planningProfile"] == profile.upper() for d in world["districts"])
        )
        schema = json.loads(
            (Path(__file__).parents[1] / "schemas/world-0.1.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(world)
        repeated = generate_world(scene, graph, planning=profile)
        self.assertEqual(world, repeated)
        self.assertEqual(
            package_world(world, scene, graph, report),
            package_world(repeated, scene, graph, report),
        )
        return world

    def test_organic_is_a_real_nonorthogonal_corridor_graph(self):
        world = self.check_profile("organic")
        directions = {
            round(
                math.atan2(s["end"][1] - s["start"][1], s["end"][0] - s["start"][0])
                % math.pi,
                2,
            )
            for s in world["streets"]
            if not s["access"]
        }
        self.assertGreater(len(directions), 15)
        self.assertTrue(all(p["blockProfile"] == "ORGANIC" for p in world["parcels"]))

    def test_industrial_has_wide_spines_deeper_lots_and_actual_dead_ends(self):
        world = self.check_profile("industrial")
        self.assertTrue(any(s["width"] == 7 for s in world["streets"]))
        self.assertTrue(
            all(p["blockProfile"] == "INDUSTRIAL" for p in world["parcels"])
        )
        from metropogits.world.geometry import area

        self.assertTrue(
            all(abs(area(p["parcel"]) - 90) < 0.01 for p in world["parcels"])
        )
        adjacent = {}
        for s in world["streets"]:
            if not s["access"]:
                for p in (s["start"], s["end"]):
                    adjacent[tuple(p)] = adjacent.get(tuple(p), 0) + 1
        self.assertTrue(any(count == 1 for count in adjacent.values()))
        self.assertEqual(world["districts"][0]["areaDemand"]["parcelArea"], 40 * 90)

    def test_hybrid_contains_two_real_connected_grammars_in_one_district(self):
        world = self.check_profile("hybrid")
        self.assertEqual(len(world["districts"]), 1)
        self.assertEqual(
            {p["blockProfile"] for p in world["parcels"]}, {"GRID", "ORGANIC"}
        )
        self.assertEqual(len(world["districts"][0]["planningRegions"]), 2)
        import copy

        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        broken = copy.deepcopy(world)
        broken["parcels"][0]["planningRegionId"] = "missing"
        with self.assertRaisesRegex(ValueError, "hybrid parcel ownership"):
            validate_world(broken, scene, graph)

    def test_varied_selects_all_five_without_redefining_legacy_mixed(self):
        from metropogits.world.generator import requested_profile
        from metropogits.world.seed import derive

        choices = {requested_profile("varied", derive(str(i))) for i in range(100)}
        self.assertEqual(choices, {"GRID", "RADIAL", "ORGANIC", "INDUSTRIAL", "HYBRID"})
        self.assertLessEqual(
            {requested_profile("mixed", derive(str(i))) for i in range(100)},
            {"GRID", "RADIAL"},
        )

    def test_organic_hints_preserve_original_sites_after_file_addition(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            first = generate_world(scene, graph, planning="organic")
            (repo / "extra.rs").write_text("fn added() {}", encoding="utf8")
            from metropogits.cli import analyze_repository
            from metropogits.layout import generate_city

            graph = analyze_repository(repo, repository_id="fixture/radial")
            changed = generate_world(
                generate_city(graph), graph, planning="organic", previous=first
            )
        self.assertEqual(first["envelope"], changed["envelope"])
        old = {p["entityId"]: p for p in first["parcels"]}
        for p in changed["parcels"]:
            if p["entityId"] in old:
                self.assertEqual(p, old[p["entityId"]])

    def test_industrial_and_hybrid_hints_keep_existing_parcels(self):
        from metropogits.cli import analyze_repository
        from metropogits.layout import generate_city

        for profile in ("industrial", "hybrid"):
            with (
                self.subTest(profile=profile),
                tempfile.TemporaryDirectory() as directory,
            ):
                repo = Path(directory)
                scene, graph = fixture(repo)
                first = generate_world(scene, graph, planning=profile)
                (repo / "extra.rs").write_text("fn added() {}", encoding="utf8")
                graph = analyze_repository(repo, repository_id="fixture/radial")
                scene = generate_city(graph)
                changed = generate_world(scene, graph, planning=profile, previous=first)
                validate_world(changed, scene, graph)
                self.assertTrue(changed["anchors"]["reusedDistrictIds"])
                old = {p["entityId"]: p for p in first["parcels"]}
                for p in changed["parcels"]:
                    if p["entityId"] in old:
                        self.assertEqual(p, old[p["entityId"]])

    def test_new_frontage_resource_bounds_fail_closed(self):
        from metropogits.world.organic import organic_slots

        polygon = [[-100, -100], [100, -100], [100, 100], [-100, 100]]
        for name in ("MAX_SEGMENTS", "MAX_CANDIDATES", "MAX_INDEX", "MAX_CHECKS"):
            with patch(f"metropogits.world.frontage.{name}", 0):
                with self.assertRaisesRegex(ValueError, "limit"):
                    organic_slots(polygon, "seed")
