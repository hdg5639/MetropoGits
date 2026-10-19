"""Count topology, not water mesh tiles; preserve evidence and old geography."""

import copy
import json
import math
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.elevation import surface
from metropogits.world.export import package_world
from metropogits.world.generator import generate_world
from metropogits.world.geometry import inside, nearest, rectangle
from metropogits.world.terrain import validate_terrain
from metropogits.world.validation import validate_world
from metropogits.world.watershed import generate_watershed_terrain
from test_world_neighborhoods import fixture


class WatershedTests(unittest.TestCase):
    def test_medium_scale_seeds_change_counts_and_parent_topology_not_only_yaw(self):
        envelope = rectangle([0, 0], 0, 450, 360)
        counts = set()
        nested = 0
        forms = set()
        for i in range(16):
            terrain = generate_watershed_terrain(envelope, str(i))
            self.assertEqual(terrain, generate_watershed_terrain(envelope, str(i)))
            validate_terrain(terrain, str(i))
            lines = terrain["channel"]["waterways"]
            by_id = {r["id"]: r for r in lines}
            kinds = Counter(r["kind"] for r in lines)
            counts.add((kinds["MAIN"], kinds["TRIBUTARY"]))
            self.assertLessEqual(len(terrain["features"]), 64)
            self.assertLessEqual(len(terrain["crossings"]), 8)
            self.assertEqual(terrain["channel"]["centerline"], lines[0]["centerline"])
            self.assertEqual(
                terrain["channel"]["tributaries"], [r["centerline"] for r in lines[1:]]
            )
            for r in lines:
                path = r["centerline"]
                self.assertGreaterEqual(len(path), 6)
                self.assertFalse(inside(path[-1], envelope))
                self.assertTrue(any(inside(p, envelope) for p in path[1:-1]))
                if r["kind"] == "MAIN":
                    self.assertIsNone(r["parentId"])
                    self.assertFalse(inside(path[0], envelope))
                else:
                    parent = by_id[r["parentId"]]
                    self.assertIn(path[0], parent["centerline"])
                    self.assertLess(r["width"], parent["width"])
                    nested += parent["kind"] == "TRIBUTARY"
                    # Bends must depart from a straight ray as well as vary yaw.
                    forms.add(len(path))
                    self.assertGreater(
                        max(
                            math.dist(p, nearest(p, path[0], path[-1]))
                            for p in path[1:-1]
                        ),
                        0.2,
                    )
            field = surface(terrain)
            for f in terrain["features"]:
                if f["kind"] == "LAKE":
                    levels = [field.height(p) for p in f["polygon"]]
                    self.assertLess(max(levels) - min(levels), 0.0002)
        self.assertGreaterEqual(len(counts), 6)
        self.assertTrue(any(m == 2 for m, b in counts))
        self.assertTrue(any(b == 0 for m, b in counts))
        self.assertGreater(nested, 0)
        self.assertGreater(len(forms), 1)

    def test_tiny_domain_does_not_receive_a_large_river_tree(self):
        for i in range(6):
            t = generate_watershed_terrain(rectangle([0, 0], 0, 120, 90), str(i))
            self.assertEqual(len(t["channel"]["waterways"]), 1)
            self.assertEqual(len(t["crossings"]), 1)

    def test_full_pipeline_schema_repeat_growth_and_immutable_source(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            opts = dict(
                zoning="neighborhoods",
                pattern_scale="adaptive",
                planning="varied",
                outline="varied",
                terrain="watershed-landscape",
                street_policy="porous",
                seed="water-fixture",
                street_hierarchy=True,
                campus=True,
                campus_style="fabric",
            )
            old = generate_world(scene, graph, **opts)
            validation = validate_world(old, scene, graph)
            package = package_world(old, scene, graph, validation)
            self.assertEqual(old, generate_world(scene, graph, **opts))
            for schema, name in [
                ("world-0.1", "world.json"),
                ("planning-0.5", "planning.json"),
            ]:
                Draft202012Validator(
                    json.loads(Path("schemas", schema + ".schema.json").read_bytes())
                ).validate(json.loads(package[name]))
            self.assertEqual(json.loads(package["city.json"]), scene)
            self.assertEqual(json.loads(package["graph.ucg.json"]), graph)
            (repo / "zz_unknown.rs").write_text("fn untouched() {}", encoding="utf8")
            graph2 = analyze_repository(repo, repository_id="fixture/neighborhoods")
            scene2 = generate_city(graph2)
            new = generate_world(scene2, graph2, previous=old, **opts)
            validate_world(new, scene2, graph2)
            self.assertEqual(old["terrain"], new["terrain"])
            frames = {p["entityId"]: p for p in new["parcels"]}
            for p in old["parcels"]:
                self.assertEqual(p, frames[p["entityId"]])

    def test_forged_parent_count_and_projection_are_rejected(self):
        t = generate_watershed_terrain(rectangle([0, 0], 0, 450, 360), "1")
        for key in ("parent", "kind", "projection"):
            bad = copy.deepcopy(t)
            if key == "parent":
                bad["channel"]["waterways"][-1]["parentId"] = "not-a-channel"
            elif key == "kind":
                bad["channel"]["waterways"][0]["kind"] = "TRIBUTARY"
            else:
                bad["channel"]["tributaries"].pop()
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_terrain(bad, "1")

    def test_budget_exhaustion_never_silently_drops_water(self):
        with (
            patch("metropogits.world.terrain_varied.MAX_WORK", 0),
            self.assertRaisesRegex(ValueError, "work limit"),
        ):
            generate_watershed_terrain(rectangle([0, 0], 0, 450, 360), "1")
        with (
            patch("metropogits.world.watershed.MAX_WATERWAYS", 0),
            self.assertRaisesRegex(ValueError, "topology resource limit"),
        ):
            generate_watershed_terrain(rectangle([0, 0], 0, 450, 360), "1")
