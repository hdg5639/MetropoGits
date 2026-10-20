"""Optional terrain-first mountain ranges, not mandatory cones on every map."""

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.export import package_world
from metropogits.world.generator import generate_world
from metropogits.world.geometry import area, inside, rectangle
from metropogits.world.mountains import generate_mountain_terrain, mountain_landform
from metropogits.world.terrain import validate_terrain
from metropogits.world.validation import validate_world
from test_world_neighborhoods import fixture


class MountainTerrainTests(unittest.TestCase):
    def test_seeded_counts_include_no_mountains_and_multiple_real_ranges(self):
        envelope = rectangle([0, 0], 0, 600, 440)
        counts, forms = set(), set()
        for i in range(6):
            terrain = generate_mountain_terrain(envelope, str(i))
            self.assertEqual(terrain, generate_mountain_terrain(envelope, str(i)))
            validate_terrain(terrain, str(i))
            ranges = [
                f for f in terrain["features"] if f.get("landform") == "MOUNTAIN_RANGE"
            ]
            counts.add(len(ranges))
            self.assertLessEqual(len(terrain["features"]), 64)
            self.assertLessEqual(len(terrain["crossings"]), 8)
            for f in ranges:
                self.assertGreater(f["height"], 35)
                self.assertLessEqual(f["height"], 160)
                self.assertGreaterEqual(len(f["summits"]), 2)
                self.assertTrue(all(inside(p, envelope) for p in f["roadPolygon"]))
                forms.add((f["height"], tuple(f["center"])))
            # Water topology is retained even in mountain-free seeds.
            self.assertTrue(terrain["channel"]["waterways"])
            for waterway in terrain["channel"]["waterways"]:
                self.assertFalse(inside(waterway["centerline"][-1], envelope))
        self.assertEqual(counts, {0, 1, 2})
        self.assertGreater(len(forms), 4)
        terrain = generate_mountain_terrain(envelope, "3")
        altered = copy.deepcopy(terrain)
        next(f for f in altered["features"] if f.get("summits"))["summits"].pop()
        with self.assertRaises(ValueError):
            validate_terrain(altered, "3")

    def test_continuous_ridge_mesh_covers_base_once_without_overlapping_cone_props(
        self,
    ):
        for seed in ("first", "second"):
            f = mountain_landform([20, -10], 90, 43, 0.47, seed)
            self.assertLessEqual(len(f["faces"]), 64)
            self.assertEqual(max(p[1] for p in f["summits"]), f["height"])
            total = 0
            for face in f["faces"]:
                points = [[p[0], p[2]] for p in face["points"]]
                total += area(points)
                self.assertGreater(area(points), 0)
                self.assertTrue(all(inside(p, f["polygon"], -0.0002) for p in points))
            self.assertAlmostEqual(total, area(f["polygon"]), delta=0.04)
            self.assertTrue(all(inside(p, f["noBuildPolygon"]) for p in f["polygon"]))
            self.assertGreater(math.dist(f["summits"][0], f["summits"][-1]), 35)
            self.assertEqual(f, mountain_landform([20, -10], 90, 43, 0.47, seed))

    def test_pipeline_preserves_source_access_schemas_repeat_and_growth_hints(self):
        options = dict(
            zoning="neighborhoods",
            pattern_scale="adaptive",
            planning="varied",
            outline="varied",
            terrain="mountain-landscape",
            street_policy="porous",
            seed="mountain-3",
            street_hierarchy=True,
            campus=True,
            campus_style="programmed",
        )
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            original = copy.deepcopy((scene, graph))
            world = generate_world(scene, graph, **options)
            validation = validate_world(world, scene, graph)
            self.assertEqual(validation["accessibleBuildings"], 48)
            self.assertEqual(validation["trips"], 32)
            for key in ("buildingOverlaps", "roadOverlaps", "ownerEscapes"):
                self.assertEqual(validation[key], 0)
            again = generate_world(scene, graph, **options)
            self.assertEqual(world, again)
            package = package_world(
                world, scene, graph, validation, building_style="purposeful"
            )
            self.assertEqual(
                package,
                package_world(
                    again, scene, graph, validation, building_style="purposeful"
                ),
            )
            for schema, filename in (
                ("world-0.1", "world.json"),
                ("planning-0.5", "planning.json"),
            ):
                Draft202012Validator(
                    json.loads(Path("schemas", schema + ".schema.json").read_bytes())
                ).validate(json.loads(package[filename]))
            self.assertEqual(json.loads(package["city.json"]), scene)
            self.assertEqual(json.loads(package["graph.ucg.json"]), graph)
            self.assertEqual(original, (scene, graph))
            # A genuinely small plan is allowed to fit no mountain at all.
            self.assertFalse(
                any(
                    f.get("landform") == "MOUNTAIN_RANGE"
                    for f in world["terrain"]["features"]
                )
            )
            (repo / "zz_unknown.rs").write_text("fn extra() {}", encoding="utf8")
            graph2 = analyze_repository(repo, repository_id="fixture/neighborhoods")
            scene2 = generate_city(graph2)
            grown = generate_world(scene2, graph2, previous=world, **options)
            validate_world(grown, scene2, graph2)
            self.assertEqual(grown["terrain"], world["terrain"])
            frames = {p["entityId"]: p for p in grown["parcels"]}
            for p in world["parcels"]:
                self.assertEqual(p, frames[p["entityId"]])

    def test_tall_feature_contract_does_not_weaken_legacy_height_limit(self):
        schema = json.loads(Path("schemas/world-0.1.schema.json").read_bytes())
        validator = Draft202012Validator(
            dict(schema["properties"]["terrain"], **{"$defs": schema["$defs"]})
        )
        terrain = generate_mountain_terrain(rectangle([0, 0], 0, 600, 440), "3")
        validator.validate(terrain)
        old = copy.deepcopy(terrain)
        old.update(version="terrain/0.6", preset="watershed-landscape")
        with self.assertRaises(ValidationError):
            validator.validate(old)
