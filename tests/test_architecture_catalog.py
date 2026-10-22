import copy
import math
import tempfile
import unittest
from pathlib import Path

from metropogits.world.architecture_catalog import (
    CATALOG,
    FAMILIES,
    ROLE_CHOICES,
    catalog_world,
    compile_parts,
    face_normal,
    frontage_details,
    grammar,
    part,
    select,
    unit_faces,
)
from metropogits.world.export import package_world, view_data
from metropogits.world.generator import generate_world
from metropogits.world.geometry import inside
from metropogits.world.seed import derive
from metropogits.world.validation import validate_world
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from test_world_campus import fixture
from test_world_campus_neighborhood import OPTIONS


class ArchitectureCatalogTests(unittest.TestCase):
    def test_complete_vocabulary_compiles_inside_rotated_source_envelopes(self):
        self.assertEqual(len(CATALOG), 85)
        self.assertEqual(len(FAMILIES), 16)
        for identity, recipe in CATALOG.items():
            for angle in (0, 0.43, 2.1):
                envelope = dict(
                    center=[33, -27], width=12, depth=8, height=17, angle=angle
                )
                p = compile_parts(envelope, grammar(recipe["grammar"]))
                bound = compile_parts(envelope, [part(0, 0, 0, 1, 1, 1)])[0][
                    "footprint"
                ]
                self.assertLessEqual(len(p), 18, identity)
                self.assertLessEqual(sum(len(v.get("meshFaces", [])) for v in p), 240)
                for v in p:
                    self.assertTrue(
                        all(inside(t, bound, -0.0003) for t in v["footprint"]), identity
                    )
                    self.assertLessEqual(v["y"] + v["height"], 17.0002, identity)
                    for f in v.get("meshFaces", []):
                        for x, y, z in f["points"]:
                            self.assertTrue(inside([x, z], bound, -0.0003), identity)
                            self.assertTrue(0 <= y <= 17.0002, identity)

    def test_all_primitives_face_outwards_including_dome_poles_and_roof_caps(self):
        for shape in ("DRUM", "CHAMFER", "DOME", "GABLE", "SAWTOOTH"):
            center = [0.5, 0 if shape == "DOME" else 0.3, 0.5]
            for points, surface in unit_faces(shape):
                n = face_normal(points)
                mid = [
                    sum(p[i] for p in points) / len(points) - center[i]
                    for i in range(3)
                ]
                self.assertGreaterEqual(
                    sum(a * b for a, b in zip(n, mid)), -1e-8, (shape, surface, points)
                )
                self.assertAlmostEqual(math.hypot(*n), 1)

    def test_frontage_modules_preserve_massing_and_stay_inside_all_rotated_lots(self):
        for recipe in CATALOG.values():
            for width, depth, height in ((2, 3, 40), (12, 8, 17), (40, 30, 36)):
                envelope = dict(
                    center=[33, -27],
                    width=width,
                    depth=depth,
                    height=height,
                    angle=0.67,
                )
                specs = grammar(recipe["grammar"])
                saved = copy.deepcopy(specs)
                detailed, profile = frontage_details(specs, envelope, recipe["family"])
                self.assertEqual(specs, saved)
                self.assertEqual(detailed[: len(specs)], specs)
                models = compile_parts(envelope, detailed)
                bound = compile_parts(envelope, [part(0, 0, 0, 1, 1, 1)])[0][
                    "footprint"
                ]
                self.assertLessEqual(len(models), 18)
                for model in models:
                    self.assertTrue(
                        all(inside(p, bound, -0.0004) for p in model["footprint"])
                    )
                    self.assertLessEqual(model["y"] + model["height"], height + 0.0003)
                if profile:
                    self.assertTrue(profile["decorative"])
                    self.assertLessEqual(profile["doorHeight"], 3.2)
                    # First detail is the door. Its outward normal must retain
                    # the same road-facing +Z axis, even on diagonal parcels.
                    door = models[len(specs)]
                    edge = [
                        door["footprint"][2][i] - door["footprint"][1][i]
                        for i in (0, 1)
                    ]
                    self.assertGreater(
                        edge[0] * -math.sin(0.67) + edge[1] * math.cos(0.67), 0
                    )

    def test_loading_and_public_frontage_are_visual_not_new_semantic_claims(self):
        envelope = dict(center=[0, 0], width=30, depth=20, height=18, angle=0)
        specs = grammar("bar")
        public, p = frontage_details(specs, envelope, "generic")
        loading, loading_profile = frontage_details(specs, envelope, "relational")
        self.assertEqual(p["style"], "SHELTERED_LOBBY")
        self.assertEqual(loading_profile["style"], "LOADING_BAY")
        self.assertEqual(public[len(specs)]["materialKind"], 12)
        self.assertEqual(loading[len(specs)]["materialKind"], 13)
        self.assertGreater(len(public), len(loading))  # bounded side posts
        # No centre post or lobby may plug a gateway opening.
        gate = grammar("gate")
        detailed, _ = frontage_details(gate, envelope, "api")
        self.assertTrue(
            all(not (s["x"] < 0.5 < s["x"] + s["width"]) for s in detailed[len(gate) :])
        )
        # Missing room is an honest omission, not a reserve/road collision.
        full = [part(0, 0, 0, 1, 1, 1)]
        self.assertEqual(frontage_details(full, envelope, "generic"), (full, None))

    def test_evidence_gates_do_not_turn_names_or_manifest_dependencies_into_facilities(
        self,
    ):
        proof = {"ok": dict(kind="IMPORT"), "declared": dict(kind="MANIFEST")}
        topology = dict(incoming=0, outgoing=0)
        neutral = dict(
            roles=[dict(value="SERVICE", confidence="UNKNOWN", evidenceIds=["ok"])]
        )
        self.assertTrue(
            select(neutral, topology, "seed", proof)[0].startswith(
                ("GENERIC", "UNCLASSIFIED")
            )
        )
        entity = dict(
            roles=[
                dict(value="MESSAGE_PRODUCER", confidence="DIRECT", evidenceIds=["ok"])
            ],
            technologies=[
                dict(value="KAFKA", confidence="DIRECT", evidenceIds=["declared"])
            ],
        )
        self.assertNotEqual(select(entity, topology, "seed", proof)[0], "KAFKA_PORT")
        entity["technologies"][0]["evidenceIds"] = ["ok"]
        self.assertEqual(select(entity, topology, "seed", proof)[0], "KAFKA_PORT")
        entity["roles"][0]["evidenceIds"] = ["missing"]
        self.assertTrue(
            select(entity, topology, "seed", proof)[0].startswith(
                ("GENERIC", "UNCLASSIFIED")
            )
        )

    def test_general_roles_never_activate_specialized_prototype_claims(self):
        ev = {"ok": dict(kind="AST")}
        for role, forbidden in [
            ("TEST", {"SIMULATION_CHAMBER", "FUZZING_RANGE", "BENCHMARK_ARENA"}),
            ("AUTH_CONFIGURATION", {"TOKEN_VAULT", "POLICY_ARCHIVE", "WATCHTOWER"}),
            (
                "CONFIGURATION",
                {"CLUSTER_CONTROL_TOWER", "CI_ASSEMBLY_LINE", "CONTAINER_YARD"},
            ),
        ]:
            e = dict(roles=[dict(value=role, confidence="DIRECT", evidenceIds=["ok"])])
            for seed in range(40):
                selected = select(e, dict(incoming=20, outgoing=20), str(seed), ev)[0]
                self.assertNotIn(selected, forbidden)
        self.assertTrue(
            all(k in CATALOG for choices in ROLE_CHOICES.values() for k in choices)
        )

    def test_narrow_lots_keep_roof_slopes_and_round_primitives_in_physical_proportion(
        self,
    ):
        envelope = dict(center=[0, 0], angle=0.3, width=3, depth=5, height=40)
        p = compile_parts(envelope, [part(0, 0, 0, 1, 1, 1, "DOME")])[0]
        self.assertLessEqual(p["height"], 1.8)
        p = compile_parts(envelope, [part(0, 0, 0, 1, 1, 1, "DRUM")])[0]
        self.assertLessEqual(p["height"], 6.6)
        roof = compile_parts(envelope, [part(0, 0, 0, 1, 0.3, 1, "GABLE")])[0]
        levels = sorted({v[1] for f in roof["meshFaces"] for v in f["points"]})
        self.assertLessEqual(levels[-1] - levels[-2], 3 * 0.3 + 0.0002)

    def test_invalid_grammar_and_geometry_fail_instead_of_dropping_sources(self):
        envelope = dict(center=[0, 0], width=10, depth=10, height=10, angle=0)
        for specs in (
            [part(0, 0, 0, 1, 1, 1)] * 19,
            [part(0.5, 0, 0, 1, 1, 1)],
            [part(0, 0, 0, 1, 1, 1, "UNKNOWN")],
        ):
            with self.assertRaises(ValueError):
                compile_parts(envelope, specs)

    def test_unknown_language_gets_neutral_architecture_without_invented_proof(self):
        root = Path("tests/fixtures/repositories/architecture-unknown")
        graph = analyze_repository(root, repository_id="fixture/architecture-unknown")
        scene = generate_city(graph)
        world = generate_world(scene, graph, seed="unknown")
        styled, profiles = catalog_world(world, graph)
        self.assertEqual(len(profiles), 3)
        self.assertEqual(len(styled["parcels"]), 3)
        self.assertTrue(
            all(
                p["family"] == "generic" and not p["roleEvidenceIds"]
                for p in profiles.values()
            )
        )
        self.assertFalse(world["routing"]["routes"])

    def test_real_pipeline_preserves_source_contracts_and_shared_render_meshes(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        world = generate_world(scene, graph, **dict(OPTIONS, campus_style="programmed"))
        original = copy.deepcopy((world, scene, graph))
        valid = validate_world(world, scene, graph)
        styled, profiles = catalog_world(world, graph)
        self.assertEqual(styled, catalog_world(world, graph)[0])
        self.assertEqual(len(profiles), len(world["parcels"]))
        self.assertTrue(
            all(
                p["visualSeed"] == derive(world["seed"], identity, "architecture/0.1")
                for identity, p in profiles.items()
            )
        )
        self.assertTrue(any(p["roleEvidenceIds"] for p in profiles.values()))
        self.assertTrue(
            all(
                bool(p["roleEvidenceIds"]) == bool(p["verifiedRole"])
                for p in profiles.values()
            )
        )
        self.assertTrue(
            all(
                p["family"] == "generic"
                for p in profiles.values()
                if not p["verifiedRole"]
            )
        )
        geometry = {p["entityId"]: p["parts"] for p in styled["parcels"]}
        changed = copy.deepcopy(graph)
        changed["entities"].append(
            dict(id="unrelated", kind="FILE", path="elsewhere.unknown", roles=[])
        )
        other = catalog_world(world, changed)[0]
        self.assertEqual(
            geometry, {p["entityId"]: p["parts"] for p in other["parcels"]}
        )
        data = view_data(
            world, scene, graph, building_style="catalog", campus_landmarks=True
        )
        plain = view_data(
            world, scene, graph, building_style="purposeful", campus_landmarks=True
        )
        self.assertEqual(
            [f["memberEntityIds"] for f in data["streets"]["roleCompounds"]],
            [f["memberEntityIds"] for f in plain["streets"]["roleCompounds"]],
        )
        self.assertEqual(data["routing"]["routes"], plain["routing"]["routes"])
        a = package_world(
            world,
            scene,
            graph,
            valid,
            building_style="purposeful",
            campus_landmarks=True,
        )
        b = package_world(
            world, scene, graph, valid, building_style="catalog", campus_landmarks=True
        )
        for name in ("world.json", "city.json", "graph.ucg.json", "planning.json"):
            self.assertEqual(a[name], b[name], name)
        self.assertNotEqual(a["showcase.svg"], b["showcase.svg"])
        self.assertEqual(
            b,
            package_world(
                world,
                scene,
                graph,
                valid,
                building_style="catalog",
                campus_landmarks=True,
            ),
        )
        for entity in profiles:
            self.assertIn(entity.encode(), b["assets/viewer-data.js"])
        self.assertEqual(original, (world, scene, graph))


if __name__ == "__main__":
    unittest.main()
