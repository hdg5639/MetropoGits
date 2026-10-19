"""Garden clusters change physical morphology, never source semantics."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from metropogits.street_diagonals import overlap
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.campus import courtyard_layout
from metropogits.world.campus_forms import tech_park
from metropogits.world.export import package_world
from metropogits.world.generator import generate_world
from metropogits.world.geometry import rectangle, ribbon
from metropogits.world.validation import validate_world
from test_world_campus import fixture


class CampusFormTests(unittest.TestCase):
    def test_two_gardens_have_clear_whole_parcels_and_connected_walking_space(self):
        for side in ("N", "S", "E", "W"):
            plots, walks, courts, _ = tech_park([0, 0], 0.3, 17, 13, side, "park")
            self.assertEqual(len(plots), 9)
            self.assertEqual(len(courts), 2)
            self.assertFalse(overlap(courts[0]["polygon"], courts[1]["polygon"]))
            for i, p in enumerate(plots):
                self.assertFalse(
                    any(overlap(p["polygon"], q["polygon"]) for q in plots[:i])
                )
                self.assertFalse(
                    any(overlap(p["polygon"], c["polygon"]) for c in courts)
                )
                self.assertFalse(
                    any(
                        overlap(p["polygon"], ribbon(w["start"], w["end"], 1.35))
                        for w in walks
                    )
                )
            self.assertFalse(
                any(
                    overlap(c["polygon"], ribbon(w["start"], w["end"], 1.35))
                    for c in courts
                    for w in walks
                )
            )
            poly = rectangle([0, 0], 0, 200, 180)
            roads = [
                dict(id=str(i), start=a, end=b, width=3, access=False)
                for i, (a, b) in enumerate(zip(poly, poly[1:] + poly[:1]))
            ]
            zone = dict(
                id="z", parentId="p", memberEntityIds=[str(i) for i in range(24)]
            )
            layout = courtyard_layout(
                zone,
                poly,
                0.3,
                "park",
                roads,
                None,
                {},
                max_courts=1,
                variant="TECH_PARK",
            )
            self.assertIsNotNone(layout)
            self.assertEqual(layout[2]["variant"], "TECH_PARK")

    def test_varied_world_is_reconstructable_and_does_not_reclassify_files(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        options = dict(
            seed="campus-fixture",
            zoning="neighborhoods",
            pattern_scale="adaptive",
            street_policy="porous",
            planning="varied",
            outline="varied",
            campus=True,
        )
        old = generate_world(scene, graph, **options)
        world = generate_world(scene, graph, **options, campus_style="varied")
        validate_world(world, scene, graph)
        self.assertEqual(world["campusPlan"]["version"], "campus-plan/0.2")
        self.assertEqual(world["campusPlan"]["style"], "varied")
        self.assertTrue(world["campusPlan"]["sites"])
        self.assertTrue(
            any(s["variant"] == "TECH_PARK" for s in world["campusPlan"]["sites"])
        )
        self.assertEqual(world["envelope"], old["envelope"])
        self.assertEqual(
            {z["id"]: z["polygon"] for z in world["zoning"]["zones"]},
            {z["id"]: z["polygon"] for z in old["zoning"]["zones"]},
        )
        self.assertEqual(
            world, generate_world(scene, graph, **options, campus_style="varied")
        )
        switched = generate_world(
            scene, graph, previous=old, **options, campus_style="varied"
        )
        self.assertEqual(switched["parcels"], world["parcels"])
        self.assertTrue(
            any(
                d.get("reason")
                == "incompatible previous world; deterministic cold rebuild"
                for d in switched["diagnostics"]
            )
        )
        package = package_world(
            world, scene, graph, validate_world(world, scene, graph)
        )
        self.assertEqual(json.loads(package["city.json"]), scene)
        self.assertEqual(json.loads(package["graph.ucg.json"]), graph)
        for name, document in (
            ("world-0.1", "world.json"),
            ("planning-0.5", "planning.json"),
        ):
            Draft202012Validator(
                json.loads(
                    Path("schemas", name + ".schema.json").read_text(encoding="utf8")
                )
            ).validate(json.loads(package[document]))
        bad = copy.deepcopy(world)
        bad["campusPlan"]["style"] = "quad"
        with self.assertRaisesRegex(ValueError, "campus"):
            validate_world(bad, scene, graph)
        bad["campusPlan"] = None
        with self.assertRaisesRegex(ValueError, "campus"):
            validate_world(bad, scene, graph)
        with self.assertRaisesRegex(ValueError, "previous campus"):
            generate_world(scene, graph, previous=bad, **options, campus_style="varied")

    def test_style_requires_campus_and_unknown_styles_fail_explicitly(self):
        for options in (
            dict(campus_style="varied"),
            dict(campus=True, campus_style="magic"),
        ):
            with self.assertRaisesRegex(ValueError, "campus style"):
                generate_world({}, {}, **options)

    def test_unavailable_preferred_form_uses_the_verified_quad_planner(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))

        def unavailable(*args, **kwargs):
            return (
                None
                if kwargs.get("variant") == "TECH_PARK"
                else courtyard_layout(*args, **kwargs)
            )

        with patch(
            "metropogits.world.campus.courtyard_layout", side_effect=unavailable
        ):
            world = generate_world(
                scene,
                graph,
                seed="campus-fixture",
                zoning="neighborhoods",
                pattern_scale="adaptive",
                street_policy="porous",
                planning="varied",
                outline="varied",
                campus=True,
                campus_style="varied",
            )
            validate_world(world, scene, graph)
        self.assertTrue(world["campusPlan"]["sites"])
        self.assertEqual(
            {s["variant"] for s in world["campusPlan"]["sites"]}, {"ACADEMIC_QUAD"}
        )

    def test_hinted_small_edit_keeps_existing_garden_source_frames(self):
        options = dict(
            seed="campus-fixture",
            zoning="neighborhoods",
            pattern_scale="adaptive",
            street_policy="porous",
            planning="varied",
            outline="varied",
            campus=True,
            campus_style="varied",
        )
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            before = generate_world(scene, graph, **options)
            (repo / "zz_extra.rs").write_text("fn unknown() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/campus")
            scene = generate_city(graph)
            after = generate_world(scene, graph, previous=before, **options)
        validate_world(after, scene, graph)
        frames = {p["entityId"]: p for p in after["parcels"]}
        self.assertTrue(all(frames[p["entityId"]] == p for p in before["parcels"]))


if __name__ == "__main__":
    unittest.main()
