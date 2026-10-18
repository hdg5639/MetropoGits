import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.generator import generate_world
from metropogits.world.export import package_world, view_data
from metropogits.world.radial import radial_slots
from metropogits.world.validation import validate_world
from metropogits.world.geometry import inside


def fixture(repo, count=40):
    for i in range(count):
        (repo / f"f{i}.ts").write_text(
            f"import {{value}} from './f{(i + 1) % count}';\nexport const next = value;\n",
            encoding="utf8",
        )
    graph = analyze_repository(repo, repository_id="fixture/radial")
    return generate_city(graph), graph


class WorldPlanningTests(unittest.TestCase):
    def test_radial_world_exports_real_paths_and_non_cardinal_frontages(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        frozen = copy.deepcopy((scene, graph))
        world = generate_world(scene, graph, planning="radial")
        validation = validate_world(world, scene, graph)
        self.assertTrue(
            all(d["planningProfile"] == "RADIAL" for d in world["districts"])
        )
        angles = {round(p["angle"] % math.pi, 2) for p in world["parcels"]}
        self.assertGreater(len(angles), 12)
        self.assertEqual(validation["accessibleBuildings"], 40)
        self.assertEqual(validation["trips"], 40)
        for parcel in world["parcels"]:
            # The entrance follows the same local frame as the entire mesh.
            front = [-math.sin(parcel["angle"]), math.cos(parcel["angle"])]
            self.assertAlmostEqual(
                sum(
                    (parcel["center"][j] - parcel["entrance"][j]) * front[j]
                    for j in (0, 1)
                ),
                parcel["depth"] / 2,
                delta=0.001,
            )
            self.assertTrue(
                all(inside(p, parcel["parcel"]) for p in parcel["footprint"])
            )
        schema = json.loads(
            (Path(__file__).parents[1] / "schemas/world-0.1.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(world)
        repeat = generate_world(scene, graph, planning="radial")
        self.assertEqual(world, repeat)
        artifacts = package_world(world, scene, graph, validation)
        self.assertEqual(artifacts, package_world(repeat, scene, graph, validation))
        self.assertEqual(frozen, (scene, graph))
        data = view_data(world, scene, graph)
        self.assertEqual(len(data["scene"]["buildings"]), 40)
        self.assertEqual(data["canonicalScene"], scene)
        self.assertEqual(data["routing"]["routes"], world["routing"]["routes"])

    def test_compatible_radial_hints_preserve_positions_and_frontages(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            original = generate_world(scene, graph, planning="radial")
            (repo / "new.rs").write_text("fn new_file() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/radial")
            scene = generate_city(graph)
            changed = generate_world(scene, graph, planning="radial", previous=original)
        validate_world(changed, scene, graph)
        old = {p["entityId"]: p for p in original["parcels"]}
        for p in changed["parcels"]:
            if p["entityId"] in old:
                self.assertEqual(p, old[p["entityId"]])
        self.assertEqual(changed["envelope"], original["envelope"])
        self.assertTrue(changed["anchors"]["reusedDistrictIds"])
        # Changing the policy is a documented cold replan, never false reuse.
        cold = generate_world(scene, graph, planning="mixed", previous=original)
        self.assertFalse(cold["anchors"]["reusedDistrictIds"])
        self.assertIn("incompatible", cold["diagnostics"][0]["reason"])

    def test_grid_remains_default_and_legacy_world_validates(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory), 3)
        implicit = generate_world(scene, graph)
        self.assertEqual(implicit, generate_world(scene, graph, planning="grid"))
        self.assertNotIn("planningPolicy", implicit)
        self.assertEqual(implicit["generatorVersion"], "flat-capacity/0.1")
        validate_world(implicit, scene, graph)
        with self.assertRaisesRegex(ValueError, "planning policy"):
            generate_world(scene, graph, planning="guess-from-framework-name")

    def test_mixed_local_capacity_fallback_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory), 3)
        with (
            patch("metropogits.world.generator.draw", return_value=0.1),
            patch("metropogits.world.generator.radial_slots", return_value=([], [], 0)),
        ):
            world = generate_world(scene, graph, planning="mixed")
        validate_world(world, scene, graph)
        self.assertTrue(all(d["planningProfile"] == "GRID" for d in world["districts"]))
        self.assertTrue(
            any("local GRID fallback" in d["reason"] for d in world["diagnostics"])
        )

    def test_candidate_limits_and_invalid_parcels_fail_clearly(self):
        polygon = [[-100, -100], [100, -100], [100, 100], [-100, 100]]
        for name in ("MAX_CANDIDATES", "MAX_STREETS", "MAX_CHECKS", "MAX_INDEX"):
            with patch(f"metropogits.world.radial.{name}", 0):
                with self.assertRaisesRegex(ValueError, "limit"):
                    radial_slots(polygon, "seed")
        self.assertEqual(radial_slots([[0, 0], [1, 0], [0, 1]], "seed")[0], [])
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory), 3)
        world = generate_world(scene, graph)
        # Independent parcel rejection, not just a test of visible building collisions.
        p = world["parcels"][0]
        p["parcel"] = [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1]]
        with self.assertRaisesRegex(ValueError, "escaped its parcel"):
            validate_world(world, scene, graph)
        world = generate_world(scene, graph)
        world["parcels"][0]["parcel"] = copy.deepcopy(world["districts"][0]["polygon"])
        with self.assertRaisesRegex(ValueError, "parcel overlap"):
            validate_world(world, scene, graph)

    def test_invalid_hint_profile_and_infeasible_radial_mode_fail_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory), 3)
        previous = generate_world(scene, graph, planning="radial")
        previous["districts"][0]["planningProfile"] = "UNSUPPORTED"
        with self.assertRaisesRegex(ValueError, "previous world planning profile"):
            generate_world(scene, graph, planning="radial", previous=previous)
        with patch(
            "metropogits.world.generator.radial_slots", return_value=([], [], 0)
        ):
            with self.assertRaisesRegex(ValueError, "infeasible after bounded"):
                generate_world(scene, graph, planning="radial")

    def test_radial_grammar_never_requires_supported_language_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            for i in range(25):
                (repo / f"unknown{i}.rs").write_text("fn unknown() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/rust-planning")
            scene = generate_city(graph)
            world = generate_world(scene, graph, planning="radial")
        validate_world(world, scene, graph)
        self.assertTrue(
            all(p["archetype"] == "GENERIC_BUILDING" for p in world["parcels"])
        )
        self.assertFalse(world["routing"]["routes"])
