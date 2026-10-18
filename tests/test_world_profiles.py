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

    def test_new_frontage_resource_bounds_fail_closed(self):
        from metropogits.world.organic import organic_slots

        polygon = [[-100, -100], [100, -100], [100, 100], [-100, 100]]
        for name in ("MAX_SEGMENTS", "MAX_CANDIDATES", "MAX_INDEX", "MAX_CHECKS"):
            with patch(f"metropogits.world.frontage.{name}", 0):
                with self.assertRaisesRegex(ValueError, "limit"):
                    organic_slots(polygon, "seed")
