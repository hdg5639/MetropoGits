import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from metropogits.world.architecture import massing, purpose_world
from metropogits.world.campus_programmed import ProgrammedFabric
from metropogits.world.export import package_world, view_data
from metropogits.world.generator import generate_world
from metropogits.world.geometry import inside
from metropogits.world.source_programs import program_summary
from metropogits.world.validation import validate_world
from test_world_campus import fixture
from test_world_campus_neighborhood import OPTIONS


class SourceArchitectureTests(unittest.TestCase):
    def test_same_family_changes_with_observed_role_responsibility(self):
        b = dict(entityId="actual:file", archetype="SERVICE_OFFICE")
        inbound = massing(b, dict(incoming=10, outgoing=1))
        outbound = massing(b, dict(incoming=1, outgoing=10))
        self.assertNotEqual(inbound, outbound)
        self.assertIn("Shared service", inbound[1])
        self.assertIn("Multi-target service", outbound[1])
        unknown = massing(
            dict(b, archetype="GENERIC_BUILDING"), dict(incoming=20, outgoing=20)
        )
        self.assertIn("Unclassified", unknown[1])

    def test_program_is_evidenced_and_keeps_unknown_members_neutral(self):
        zone = dict(
            memberEntityIds=["a", "b"],
            memberClaims=[
                dict(
                    entityId="a",
                    roles=[
                        dict(value="TEST", confidence="DIRECT", evidenceIds=["proof"])
                    ],
                ),
                dict(
                    entityId="b",
                    roles=[dict(value="SERVICE", confidence="UNKNOWN", evidenceIds=[])],
                ),
            ],
        )
        self.assertEqual(program_summary(zone)["kind"], "VALIDATION")
        self.assertEqual(program_summary(zone)["classifiedMemberCount"], 1)
        self.assertEqual(program_summary(zone)["evidenceIds"], ["proof"])
        self.assertEqual(
            program_summary(dict(zone, memberClaims=[]))["kind"], "COLLABORATION"
        )

    def test_purposeful_campus_and_geometry_are_real_deterministic_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        original = copy.deepcopy((scene, graph))
        world = generate_world(scene, graph, **dict(OPTIONS, campus_style="programmed"))
        validation = validate_world(world, scene, graph)
        Draft202012Validator(
            json.loads(Path("schemas/world-0.1.schema.json").read_bytes())
        ).validate(world)
        self.assertEqual(
            world,
            generate_world(scene, graph, **dict(OPTIONS, campus_style="programmed")),
        )
        self.assertTrue(world["campusPlan"]["sites"])
        for site in world["campusPlan"]["sites"]:
            self.assertEqual(site["sourceProgram"]["kind"], "VALIDATION")
            self.assertEqual(
                set(site["memberEntityIds"]),
                {
                    p["entityId"]
                    for p in world["parcels"]
                    if p.get("zoneId") == site["zoneId"]
                },
            )
            self.assertTrue(site["sourceProgram"]["evidenceIds"])
        before = copy.deepcopy(world)
        styled, profiles = purpose_world(world, graph)
        for p in styled["parcels"]:
            self.assertTrue(profiles[p["entityId"]]["derived"])
            for part in p["parts"]:
                self.assertLessEqual(part["y"] + part["height"], p["height"] + 1e-7)
                self.assertTrue(
                    all(inside(v, p["footprint"], -0.0003) for v in part["footprint"])
                )
        self.assertEqual(before, world)
        self.assertEqual(original, (scene, graph))
        data = view_data(world, scene, graph, building_style="purposeful")
        self.assertEqual(
            set(data["buildingPrograms"]), {p["entityId"] for p in world["parcels"]}
        )
        a = package_world(
            world, scene, graph, validation, building_style="architectural"
        )
        b = package_world(world, scene, graph, validation, building_style="purposeful")
        self.assertEqual(a["world.json"], b["world.json"])
        self.assertEqual(a["graph.ucg.json"], b["graph.ucg.json"])
        self.assertNotEqual(a["showcase.svg"], b["showcase.svg"])
        self.assertEqual(
            b,
            package_world(world, scene, graph, validation, building_style="purposeful"),
        )

    def test_anchor_roles_are_mixed_without_ignoring_real_affinity(self):
        zone = dict(
            memberEntityIds=["test", "service"],
            memberClaims=[
                dict(
                    entityId=k,
                    roles=[
                        dict(value=r, confidence="DIRECT", evidenceIds=[k + "-proof"])
                    ],
                )
                for k, r in [("test", "TEST"), ("service", "SERVICE")]
            ],
        )
        form = ProgrammedFabric(
            zone, [[-100, -100], [100, -100], [100, 100], [-100, 100]], 0, "seed", []
        )
        self.assertEqual(
            form.anchor(
                ["service", "test"],
                {"service": 1, "test": 8},
                {"test": {"service": 1}, "service": {"test": 1}},
                [],
            ),
            "test",
        )
