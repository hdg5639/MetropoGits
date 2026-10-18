import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.generator import generate_world
from metropogits.world.export import package_world
from metropogits.world.validation import validate_world
from metropogits.world.geometry import area, partition, shared_boundaries
from metropogits.world.infrastructure import atomic_streets


def fixture():
    graph = json.loads(
        (Path(__file__).parent / "fixtures/ucg/valid/spring-minimal.json").read_text(
            encoding="utf8"
        )
    )
    return generate_city(graph), graph


class ProceduralWorldTests(unittest.TestCase):
    def test_real_contract_and_repeatable_exports_preserve_legacy_source(self):
        scene, graph = fixture()
        original = copy.deepcopy((scene, graph))
        world = generate_world(scene, graph)
        report = validate_world(world, scene, graph)
        self.assertEqual(world, generate_world(scene, graph))
        schema = json.loads(
            (Path(__file__).parents[1] / "schemas/world-0.1.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(world)
        artifacts = package_world(world, scene, graph, report)
        self.assertEqual(artifacts, package_world(world, scene, graph, report))
        self.assertEqual(json.loads(artifacts["city.json"]), scene)
        self.assertEqual(json.loads(artifacts["graph.ucg.json"]), graph)
        self.assertEqual(original, (scene, graph))
        self.assertEqual(report["accessibleBuildings"], len(scene["buildings"]))
        self.assertEqual(len(world["routing"]["routes"]), 1)
        self.assertIn(b"PROCEDURAL FLAT WORLD", artifacts["index.html"])

    def test_changed_seed_moves_world_without_changing_facts(self):
        scene, graph = fixture()
        a = generate_world(scene, graph, seed="a")
        b = generate_world(scene, graph, seed="b")
        self.assertNotEqual(a["envelope"], b["envelope"])
        self.assertNotEqual(
            [p["center"] for p in a["parcels"]], [p["center"] for p in b["parcels"]]
        )
        for world in (a, b):
            validate_world(world, scene, graph)
        self.assertEqual(a["ucgDigest"], b["ucgDigest"])
        self.assertEqual(a["sourceCityDigest"], b["sourceCityDigest"])

    def test_shuffled_inputs_and_revision_do_not_reroll_physical_geography(self):
        scene, graph = fixture()
        a = generate_world(scene, graph)
        scene["buildings"].reverse()
        scene["districts"].reverse()
        with self.assertRaisesRegex(ValueError, "canonical order"):
            generate_world(scene, graph)
        scene["buildings"].sort(key=lambda b: b["entityId"])
        scene["districts"].sort(key=lambda d: d["id"])
        graph["repository"]["revision"] = "next-revision"
        # Canonical digests reflect serialization; geometry must not depend on iteration order.
        scene["ucgDigest"] = __import__(
            "scripts.canonical_json", fromlist=["sha256_digest"]
        ).sha256_digest(graph)
        b = generate_world(scene, graph)
        self.assertEqual(a["parcels"], b["parcels"])
        self.assertEqual(a["districts"], b["districts"])

    def test_capacity_cuts_share_topology_and_conserve_area(self):
        poly = [[0, 0], [100, 0], [100, 100], [0, 100]]
        result = partition(poly, [("a", 1), ("b", 3), ("c", 6)], "seed")
        result, envelope = shared_boundaries(result, poly)
        self.assertAlmostEqual(
            sum(area(p) for p in result.values()), area(envelope), places=2
        )
        self.assertAlmostEqual(area(result["a"]), 1000, delta=0.02)
        edges = {}
        for key, p in result.items():
            for a, b in zip(p, p[1:] + p[:1]):
                edges.setdefault(tuple(sorted((tuple(a), tuple(b)))), set()).add(key)
        self.assertTrue(any(len(owners) == 2 for owners in edges.values()))

    def test_hints_preserve_existing_positions_after_small_file_addition(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            for i in range(12):
                (repo / f"f{i}.rs").write_text("fn example() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/unknown")
            scene = generate_city(graph)
            a = generate_world(scene, graph)
            (repo / "new.rs").write_text("fn added() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/unknown")
            scene = generate_city(graph)
            b = generate_world(scene, graph, previous=a)
            validate_world(b, scene, graph)
            self.assertEqual(a["envelope"], b["envelope"])
            old = {p["entityId"]: p["center"] for p in a["parcels"]}
            self.assertEqual(
                old,
                {
                    p["entityId"]: p["center"]
                    for p in b["parcels"]
                    if p["entityId"] in old
                },
            )
            self.assertTrue(b["anchors"]["reusedDistrictIds"])

    def test_quantized_T_junction_still_connects_both_streets(self):
        raw = [
            dict(start=[-18.0857, 2.2311], end=[15.5434, 3.117], width=4, access=False),
            dict(
                start=[0.0077, -0.2933], end=[-0.0713, 2.7056], width=0.7, access=True
            ),
        ]
        streets = atomic_streets(raw)
        self.assertTrue(
            any(
                s["start"] == [-0.0713, 2.7056] or s["end"] == [-0.0713, 2.7056]
                for s in streets
                if not s["access"]
            )
        )

    def test_broken_evidence_geometry_and_access_fail_validation(self):
        scene, graph = fixture()
        world = generate_world(scene, graph)
        for kind in ("drop", "size", "route", "overlap"):
            broken = copy.deepcopy(world)
            if kind == "drop":
                broken["parcels"].pop()
            elif kind == "size":
                broken["parcels"][0]["width"] += 1
            elif kind == "route":
                broken["routing"]["routes"][0]["source"] = broken["routing"]["routes"][
                    0
                ]["target"]
            else:
                broken["parcels"][1]["center"] = broken["parcels"][0]["center"]
                broken["parcels"][1]["footprint"] = broken["parcels"][0]["footprint"]
            with self.assertRaises(ValueError):
                validate_world(broken, scene, graph)

    def test_resource_caps_fail_explicitly(self):
        scene, graph = fixture()
        for module, limit in (
            ("planning", "MAX_FILES"),
            ("infrastructure", "MAX_PAIRS"),
            ("infrastructure", "MAX_STATES"),
        ):
            with patch(f"metropogits.world.{module}.{limit}", 0):
                with self.assertRaisesRegex(ValueError, "limit"):
                    generate_world(scene, graph)

    def test_malformed_hints_fail_with_a_bounded_diagnostic(self):
        scene, graph = fixture()
        for hint in (
            [],
            {},
            dict(districts=[None], parcels=[]),
            dict(districts=[], parcels=[], envelope=None),
        ):
            with self.assertRaisesRegex(ValueError, "previous world"):
                generate_world(scene, graph, previous=hint)
