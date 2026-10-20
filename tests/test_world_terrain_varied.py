"""Nature diversity is seeded, terrain-first and independent of source semantics."""

import copy
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from metropogits.world.elevation import surface
from metropogits.world.generator import generate_world
from metropogits.world.geometry import inside, rectangle
from metropogits.world.terrain import validate_terrain
from metropogits.world.terrain_varied import generate_varied_terrain
from metropogits.world.validation import validate_world
from metropogits.world.export import package_world
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from test_world_neighborhoods import fixture


class VariedTerrainTests(unittest.TestCase):
    def test_seed_corpus_varies_counts_positions_shapes_and_through_waterways(self):
        envelope = rectangle([0, 0], 0, 1000, 700)
        terrains = [generate_varied_terrain(envelope, str(i)) for i in range(16)]
        signatures = []
        for i, t in enumerate(terrains):
            self.assertEqual(t, generate_varied_terrain(envelope, str(i)))
            validate_terrain(t, str(i))
            counts = Counter(f["kind"] for f in t["features"])
            signatures.append(
                (counts["LAKE"], counts["HILL"], len(t["channel"]["tributaries"]))
            )
            self.assertGreater(counts["LAKE"], 0)
            self.assertLessEqual(len(t["features"]), 48)
            for path in [t["channel"]["centerline"], *t["channel"]["tributaries"]]:
                self.assertFalse(inside(path[-1], envelope))
            field = surface(t)
            for f in t["features"]:
                if f["kind"] == "LAKE":
                    heights = [field.height(p) for p in f["polygon"]]
                    self.assertLess(max(heights) - min(heights), 0.0002)
        self.assertGreaterEqual(len(set(signatures)), 8)
        self.assertGreater(max(x[1] for x in signatures), 1)
        self.assertTrue(
            any(len(p) == 4 for t in terrains for p in t["channel"]["tributaries"])
        )
        bad = copy.deepcopy(terrains[0])
        bad["features"].pop()
        with self.assertRaises(ValueError):
            validate_terrain(bad, "0")

    def test_small_and_large_domains_have_different_landform_budgets(self):
        small = [
            generate_varied_terrain(rectangle([0, 0], 0, 120, 90), str(i))
            for i in range(6)
        ]
        large = [
            generate_varied_terrain(rectangle([0, 0], 0, 1000, 700), str(i))
            for i in range(6)
        ]

        def count(ts):
            return sum(f["kind"] == "HILL" for t in ts for f in t["features"])

        self.assertGreater(count(large), count(small))

    def test_real_pipeline_and_legacy_independence(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        options = dict(
            zoning="neighborhoods",
            pattern_scale="adaptive",
            planning="varied",
            outline="varied",
            terrain="varied-landscape",
            street_policy="porous",
            seed="nature-test",
        )
        w = generate_world(scene, graph, **options)
        result = validate_world(w, scene, graph)
        self.assertEqual(result["accessibleBuildings"], len(scene["buildings"]))
        self.assertEqual(w, generate_world(scene, graph, **options))
        p = package_world(w, scene, graph, result)
        for schema, name in [
            ("world-0.1", "world.json"),
            ("planning-0.5", "planning.json"),
        ]:
            Draft202012Validator(
                json.loads(Path("schemas", schema + ".schema.json").read_bytes())
            ).validate(json.loads(p[name]))
        self.assertEqual(json.loads(p["city.json"]), scene)
        self.assertEqual(json.loads(p["graph.ucg.json"]), graph)

    def test_compatible_source_growth_retains_terrain_and_every_existing_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            options = dict(
                zoning="neighborhoods",
                pattern_scale="adaptive",
                planning="varied",
                outline="varied",
                terrain="varied-landscape",
                street_policy="porous",
                seed="nature-test",
            )
            old = generate_world(scene, graph, **options)
            (repo / "zz_unknown.rs").write_text("fn x() {}", encoding="utf8")
            graph2 = analyze_repository(repo, repository_id="fixture/neighborhoods")
            scene2 = generate_city(graph2)
            after = generate_world(scene2, graph2, previous=old, **options)
        validate_world(after, scene2, graph2)
        self.assertEqual(old["terrain"], after["terrain"])
        frames = {p["entityId"]: p for p in after["parcels"]}
        for p in old["parcels"]:
            self.assertEqual(p, frames[p["entityId"]])

    def test_union_budget_fails_explicitly_without_silently_losing_nature(self):
        with (
            patch("metropogits.world.terrain_varied.MAX_WORK", 0),
            self.assertRaisesRegex(ValueError, "work limit"),
        ):
            generate_varied_terrain(rectangle([0, 0], 0, 1000, 700), "0")
