import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.affinity import optimize_addresses
from metropogits.world.export import package_world, view_data
from metropogits.world.generator import generate_world
from metropogits.world.soft import address_digest
from metropogits.world.validation import validate_world
from metropogits.world.zoning import planning_document

ROOT = Path(__file__).parents[1]


def fixture(repo):
    for i in range(16):
        (repo / f"Service{i}.java").write_text(
            f"package demo;\nimport org.springframework.stereotype.Service;\n@Service\n"
            f"class Service{i} {{ Store{i} store; }}\n",
            encoding="utf8",
        )
        (repo / f"Store{i}.java").write_text(
            f"package demo;\nimport org.springframework.stereotype.Repository;\n@Repository\n"
            f"class Store{i} {{ }}\n",
            encoding="utf8",
        )
    graph = analyze_repository(repo, repository_id="fixture/soft-zoning")
    return generate_city(graph), graph


class SoftZoningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene, cls.graph = fixture(Path(directory))
        cls.options = dict(planning="varied", outline="varied", seed="soft-fixture")
        cls.base = generate_world(cls.scene, cls.graph, **cls.options)
        cls.world = generate_world(cls.scene, cls.graph, zoning="soft", **cls.options)

    def test_soft_influences_keep_physical_land_streets_and_occupied_addresses(self):
        report = validate_world(self.world, self.scene, self.graph)
        self.assertEqual(report["buildings"], 32)
        self.assertEqual(report["trips"], 16)
        for key in ("envelope", "districts", "streets"):
            self.assertEqual(self.base[key], self.world[key])
        self.assertEqual(
            address_digest(self.base["parcels"]), address_digest(self.world["parcels"])
        )
        stats = self.world["softZoning"]["optimization"][0]
        self.assertGreater(stats["movedBuildings"], 0)
        self.assertLess(stats["energyAfter"], stats["energyBefore"])
        self.assertLess(
            stats["meanDependencyDistanceAfter"], stats["meanDependencyDistanceBefore"]
        )
        zones = self.world["softZoning"]["zones"]
        self.assertTrue(
            any(
                set(z["memberEntityIds"]) != set(z["referenceEntityIds"]) for z in zones
            )
        )
        roles = {e["id"]: e.get("roles", []) for e in self.graph["entities"]}
        for zone in zones:
            for claim in zone["memberClaims"]:
                self.assertEqual(claim["roles"], roles[claim["entityId"]])

    def test_all_five_grammars_work_without_semantic_replanning(self):
        for policy in ("grid", "radial", "organic", "industrial", "hybrid"):
            with self.subTest(policy=policy):
                options = dict(planning=policy, outline="varied", seed="soft-fixture")
                base = generate_world(self.scene, self.graph, **options)
                soft = generate_world(self.scene, self.graph, zoning="soft", **options)
                validate_world(soft, self.scene, self.graph)
                self.assertEqual(base["streets"], soft["streets"])
                self.assertEqual(base["districts"], soft["districts"])

    def test_schemas_repeat_bytes_and_original_source_facts(self):
        original = copy.deepcopy((self.scene, self.graph))
        for schema, doc in (
            ("world-0.1", self.world),
            ("planning-0.2", planning_document(self.world)),
        ):
            Draft202012Validator(
                json.loads((ROOT / f"schemas/{schema}.schema.json").read_text())
            ).validate(doc)
        again = generate_world(self.scene, self.graph, zoning="soft", **self.options)
        self.assertEqual(self.world, again)
        validation = validate_world(again, self.scene, self.graph)
        self.assertEqual(
            package_world(self.world, self.scene, self.graph, validation),
            package_world(again, self.scene, self.graph, validation),
        )
        data = view_data(self.world, self.scene, self.graph)
        self.assertTrue(data["softZoning"]["influenceOnly"])
        self.assertEqual(data["canonicalScene"], self.scene)
        self.assertEqual(
            len(data["occupiedGround"]["pads"]), len(self.base["districts"])
        )
        self.assertEqual(original, (self.scene, self.graph))

    def test_hint_growth_pins_existing_building_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            first = generate_world(scene, graph, zoning="soft", **self.options)
            (repo / "new.rs").write_text("fn unknown() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/soft-zoning")
            scene = generate_city(graph)
            changed = generate_world(
                scene, graph, zoning="soft", previous=first, **self.options
            )
        validate_world(changed, scene, graph)
        old = {p["entityId"]: p for p in first["parcels"]}
        for parcel in changed["parcels"]:
            if parcel["entityId"] in old:
                # Influence membership may change when centers change; physical
                # addresses, complete meshes and all source facts must not move.
                self.assertEqual(
                    {k: v for k, v in parcel.items() if k != "zoneId"},
                    {k: v for k, v in old[parcel["entityId"]].items() if k != "zoneId"},
                )
        self.assertEqual(changed["softZoning"]["optimization"][0]["movedBuildings"], 0)

    def test_unknown_language_has_no_invented_affinity_or_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            for i in range(30):
                (repo / f"Server{i}.rs").write_text("fn main() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/unknown-soft")
            scene = generate_city(graph)
            base = generate_world(scene, graph, **self.options)
            soft = generate_world(scene, graph, zoning="soft", **self.options)
        validate_world(soft, scene, graph)
        self.assertEqual(
            [p["center"] for p in base["parcels"]],
            [p["center"] for p in soft["parcels"]],
        )
        self.assertEqual(soft["softZoning"]["optimization"][0]["sourcePairCount"], 0)
        self.assertEqual(soft["softZoning"]["zones"][0]["memberClaims"], [])

    def test_bounded_optimizer_preserves_members_without_losing_dependencies(self):
        parcels = [
            dict(entityId=str(i), slotId=str(i), center=[i * 10, 0], width=6, depth=6)
            for i in range(12)
        ]
        pairs = {(str(i), str(11 - i)): 1 for i in range(6)}
        with patch("metropogits.world.affinity.MAX_EVALUATIONS", 1):
            assignment, report = optimize_addresses(parcels, pairs, {}, "seed")
        self.assertEqual(set(assignment), {p["entityId"] for p in parcels})
        self.assertEqual(len(set(assignment.values())), 12)
        self.assertTrue(report["workLimitReached"])
        self.assertEqual(report["sourcePairCount"], 6)
        self.assertLessEqual(report["energyAfter"], report["energyBefore"])

    def test_evidence_ownership_digest_and_stats_tampering_fail_closed(self):
        for mutation in ("reference", "occupant", "digest", "energy"):
            world = copy.deepcopy(self.world)
            zone = world["softZoning"]["zones"][0]
            if mutation == "reference":
                zone["referenceClaims"][0]["roles"][0]["evidenceIds"] = ["made-up"]
            elif mutation == "occupant":
                zone["memberEntityIds"].pop()
            elif mutation == "digest":
                world["softZoning"]["addressDigest"] = "sha256:fake"
            else:
                world["softZoning"]["optimization"][0]["energyAfter"] = 1e20
            with (
                self.subTest(mutation=mutation),
                self.assertRaisesRegex(ValueError, "soft"),
            ):
                validate_world(world, self.scene, self.graph)
        world = dict(self.world, softZoning=None)
        with self.assertRaisesRegex(ValueError, "previous soft"):
            generate_world(self.scene, self.graph, zoning="soft", previous=world)


if __name__ == "__main__":
    unittest.main()
