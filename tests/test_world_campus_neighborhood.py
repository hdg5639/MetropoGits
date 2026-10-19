"""CAMPUS plans a complete neighborhood, not an eight-file garden pocket."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.campus_neighborhood import neighborhood_layout
from metropogits.world.export import package_world
from metropogits.world.generator import generate_world
from metropogits.world.geometry import rectangle
from metropogits.world.validation import validate_world
from test_world_campus import fixture

OPTIONS = dict(
    seed="campus-fixture",
    zoning="neighborhoods",
    pattern_scale="adaptive",
    street_policy="porous",
    planning="varied",
    outline="varied",
    campus=True,
    campus_style="neighborhood",
)


class CampusNeighborhoodTests(unittest.TestCase):
    def test_all_members_share_a_precinct_with_real_activity_groups_and_pedestrian_access(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        original = copy.deepcopy((scene, graph))
        world = generate_world(scene, graph, **OPTIONS)
        self.assertEqual(world, generate_world(scene, graph, **OPTIONS))
        self.assertEqual(original, (scene, graph))
        self.assertEqual(world["campusPlan"]["version"], "campus-plan/0.3")
        (site,) = world["campusPlan"]["sites"]
        self.assertEqual(len(site["memberEntityIds"]), 48)
        self.assertEqual(site["retainedMemberEntityIds"], [])
        self.assertEqual(len(site["activityCenters"]), 2)
        self.assertTrue(all(p["blockProfile"] == "CAMPUS" for p in world["parcels"]))
        self.assertEqual(world["zoning"]["blocks"][0]["urbanGrammar"], "CAMPUS")
        for group in site["activityCenters"]:
            members = [p for p in world["parcels"] if p["slotId"] in group["slotIds"]]
            self.assertGreaterEqual(len(members), 6)
            self.assertIn(group["anchorEntityId"], [p["entityId"] for p in members])
        validation = validate_world(world, scene, graph)
        self.assertEqual(validation["accessibleBuildings"], 48)
        self.assertEqual(validation["trips"], 24)
        self.assertGreater(
            world["streetPlan"]["summary"]["classCounts"]["PEDESTRIAN"], 0
        )
        package = package_world(world, scene, graph, validation)
        schema = json.loads(Path("schemas/world-0.1.schema.json").read_bytes())
        Draft202012Validator(schema).validate(world)
        self.assertEqual(package, package_world(world, scene, graph, validation))
        for name in ("viewer-3d.js", "viewer.js"):
            self.assertIn(b"CAMPUS NEIGHBORHOOD", package["assets/" + name])
            self.assertIn(b"campus-group", package["assets/" + name])
        forged = copy.deepcopy(world)
        forged["campusPlan"]["sites"][0]["memberEntityIds"].pop()
        with self.assertRaises(ValueError):
            validate_world(forged, scene, graph)
        forged = copy.deepcopy(world)
        forged["campusPlan"]["version"] = "campus-plan/0.2"
        forged["campusPlan"]["style"] = "varied"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(forged)

    def test_full_capacity_failure_retains_the_original_grammar_not_a_small_pocket(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        with patch(
            "metropogits.world.campus_neighborhood.neighborhood_layout",
            return_value=None,
        ):
            world = generate_world(scene, graph, **OPTIONS)
            validate_world(world, scene, graph)
        self.assertEqual(world["campusPlan"]["sites"], [])
        self.assertIn(
            "FULL_NEIGHBORHOOD_FIT_FALLBACK",
            [d["reason"] for d in world["campusPlan"]["decisions"].values()],
        )
        self.assertFalse(
            any(p.get("blockProfile") == "CAMPUS" for p in world["parcels"])
        )
        poly = rectangle([0, 0], 0, 35, 30)
        roads = [
            dict(id=str(i), start=a, end=b, width=3)
            for i, (a, b) in enumerate(zip(poly, poly[1:] + poly[:1]))
        ]
        stats = {}
        self.assertIsNone(
            neighborhood_layout(
                dict(id="z", parentId="p", memberEntityIds=list(map(str, range(48)))),
                poly,
                0,
                "seed",
                roads,
                None,
                {},
                stats,
            )
        )
        self.assertIn("rejected", stats)

    def test_nearby_source_growth_reuses_existing_precinct_addresses(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            before = generate_world(scene, graph, **OPTIONS)
            (repo / "zz_unknown.rs").write_text("fn unknown() {}\n", encoding="utf8")
            graph2 = analyze_repository(repo, repository_id="fixture/campus")
            scene2 = generate_city(graph2)
            after = generate_world(scene2, graph2, previous=before, **OPTIONS)
        validate_world(after, scene2, graph2)
        old = {p["entityId"]: p for p in before["parcels"]}
        preserved = [
            p["entityId"]
            for p in after["parcels"]
            if p["entityId"] in old and p == old[p["entityId"]]
        ]
        self.assertEqual(len(preserved), 48)
        self.assertEqual(len(after["campusPlan"]["sites"][0]["memberEntityIds"]), 49)
        for identity in old:
            self.assertIn(identity, {p["entityId"] for p in after["parcels"]})
