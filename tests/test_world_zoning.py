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
from metropogits.block_orientation import clip
from metropogits.world.generator import generate_world
from metropogits.world.geometry import area, inside
from metropogits.world.power import power_partition
from metropogits.world.export import package_world, view_data
from metropogits.world.validation import validate_world
from metropogits.world.zoning import candidates, planning_document
from metropogits.world.zone_access import access_corridors

ROOT = Path(__file__).parents[1]
SQUARE = [[0, 0], [250, 0], [250, 250], [0, 250]]


def fixture(repo):
    for i in range(12):
        for role, annotation in (("Service", "Service"), ("Store", "Repository")):
            (repo / f"{role}{i}.java").write_text(
                f"package demo;\nimport org.springframework.stereotype.{annotation};\n@{annotation}\nclass {role}{i} {{}}\n",
                encoding="utf8",
            )
    for i in range(24):
        (repo / f"case{i}.test.ts").write_text(
            f"import {{ next }} from './case{(i + 1) % 24}.test';\nexport const testValue = next;\n",
            encoding="utf8",
        )
        (repo / f"utility{i}.rs").write_text("fn unrelated() {}\n", encoding="utf8")
    graph = analyze_repository(repo, repository_id="fixture/zoning")
    return generate_city(graph), graph


class PowerCellTests(unittest.TestCase):
    def test_access_ports_do_not_pave_every_cell_border(self):
        polygons = {
            str(i): [
                [i * 100, 0],
                [(i + 1) * 100, 0],
                [(i + 1) * 100, 100],
                [i * 100, 100],
            ]
            for i in range(3)
        }
        roads = {
            key: [dict(start=[i * 100, 50], end=[(i + 1) * 100, 50])]
            for i, key in enumerate(polygons)
        }
        parent = [[0, 0], [300, 0], [300, 100], [0, 100]]
        connections = access_corridors(polygons, roads, parent)
        length = sum(math.dist(r["start"], r["end"]) for r in connections)
        self.assertGreater(length, 0)
        self.assertLess(length, 3 * 400)
        self.assertTrue(all(r["access"] is False for r in connections))

    def test_balanced_power_cells_are_clipped_disjoint_and_repeatable(self):
        demands = [("a", 1), ("b", 3), ("c", 6)]
        parts, report = power_partition(SQUARE, demands, "seed")
        self.assertEqual(report["algorithm"], "clipped-power/0.1")
        self.assertLessEqual(report["maxRelativeAreaError"], 0.0151)
        self.assertAlmostEqual(sum(map(area, parts.values())), area(SQUARE), delta=0.1)
        for i, (key, weight) in enumerate(demands):
            self.assertAlmostEqual(
                area(parts[key]) / area(SQUARE), weight / 10, delta=0.015
            )
            self.assertTrue(all(inside(p, SQUARE) for p in parts[key]))
            for other, _ in demands[:i]:
                self.assertLess(area(clip(parts[key], parts[other])), 0.001)
        self.assertEqual(
            (parts, report), power_partition(SQUARE, list(reversed(demands)), "seed")
        )

    def test_solver_has_bounded_explicit_deterministic_fallback(self):
        with patch("metropogits.world.power.MAX_ITERATIONS", 0):
            parts, report = power_partition(SQUARE, [("a", 1), ("b", 50)], "seed")
        self.assertEqual(report["algorithm"], "capacity-bisection/0.1")
        self.assertIn("fallbackReason", report)
        self.assertAlmostEqual(area(parts["a"]), area(SQUARE) / 51, delta=0.1)

    def test_limits_and_unsupported_land_are_rejected(self):
        for demands in (
            [],
            [("x", 0)],
            [("x", math.inf)],
            [("x", 1), ("x", 2)],
            [(str(i), 1) for i in range(8)],
        ):
            with (
                self.subTest(demands=demands),
                self.assertRaisesRegex(ValueError, "demands|limit"),
            ):
                power_partition(SQUARE, demands, "seed")
        for polygon in (
            list(reversed(SQUARE)),
            [[0, 0], [100, 0], [50, 50], [100, 100], [0, 100]],
            [[0, 0], [math.nan, 0], [0, 100]],
        ):
            with self.assertRaisesRegex(ValueError, "convex"):
                power_partition(polygon, [("x", 1)], "seed")


class SemanticZoningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene, cls.graph = fixture(Path(directory))
        cls.world = generate_world(
            cls.scene, cls.graph, zoning="semantic", outline="varied"
        )

    def test_real_analyzed_roles_produce_exact_neighborhoods_and_access(self):
        w = self.world
        report = validate_world(w, self.scene, self.graph)
        self.assertEqual(report["buildings"], 72)
        self.assertEqual(report["accessibleBuildings"], 72)
        self.assertEqual(report["trips"], 24)
        zones = w["zoning"]["zones"]
        self.assertEqual(
            {z["clusterKey"] for z in zones},
            {
                "SERVICE_QUARTER",
                "INDUSTRIAL_LOGISTICS",
                "CAMPUS_RESEARCH",
                "GENERAL_MIXED",
            },
        )
        self.assertEqual(sum(len(z["memberEntityIds"]) for z in zones), 72)
        self.assertEqual(len(w["districts"]), 1)
        self.assertTrue(
            all(z["allocation"]["algorithm"] == "clipped-power/0.1" for z in zones)
        )
        self.assertTrue(
            all(p["zoneId"] in {z["id"] for z in zones} for p in w["parcels"])
        )

    def test_both_versioned_schemas_and_immutable_inputs(self):
        original = copy.deepcopy((self.scene, self.graph))
        report = validate_world(self.world, self.scene, self.graph)
        artifacts = package_world(self.world, self.scene, self.graph, report)
        for name, document in (
            ("world", self.world),
            ("planning", planning_document(self.world)),
        ):
            schema = json.loads((ROOT / f"schemas/{name}-0.1.schema.json").read_text())
            Draft202012Validator(schema).validate(document)
        self.assertEqual(
            json.loads(artifacts["planning.json"]), planning_document(self.world)
        )
        self.assertIn(b"data-zone-id", artifacts["showcase.svg"])
        again = generate_world(
            self.scene, self.graph, zoning="semantic", outline="varied"
        )
        self.assertEqual(self.world, again)
        self.assertEqual(
            artifacts, package_world(again, self.scene, self.graph, report)
        )
        self.assertEqual(original, (self.scene, self.graph))

    def test_seed_changes_geometry_but_not_zone_identity_or_source_members(self):
        other = generate_world(
            self.scene, self.graph, zoning="semantic", seed="another"
        )
        validate_world(other, self.scene, self.graph)
        expected = [
            (z["id"], z["classification"], z["memberEntityIds"])
            for z in self.world["zoning"]["zones"]
        ]
        self.assertEqual(
            expected,
            [
                (z["id"], z["classification"], z["memberEntityIds"])
                for z in other["zoning"]["zones"]
            ],
        )
        self.assertNotEqual(self.world["envelope"], other["envelope"])

    def test_unclassified_district_skips_internal_voronoi_and_name_guesses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(30):
                (root / f"AiStorageServer{i}.rs").write_text(
                    "fn unknown() {}", encoding="utf8"
                )
            graph = analyze_repository(root, repository_id="fixture/unknown-zoning")
            scene = generate_city(graph)
            world = generate_world(scene, graph, zoning="semantic")
        validate_world(world, scene, graph)
        self.assertEqual(len(world["zoning"]["zones"]), 1)
        zone = world["zoning"]["zones"][0]
        self.assertEqual(zone["clusterKey"], "GENERAL_MIXED")
        self.assertEqual(zone["allocation"]["algorithm"], "unsplit/0.1")
        self.assertEqual(zone["memberClaims"], [])

    def test_viewer_zones_are_derived_and_retain_canonical_city(self):
        data = view_data(self.world, self.scene, self.graph)
        self.assertEqual(data["canonicalScene"], self.scene)
        self.assertEqual(len(data["semanticZoning"]), 4)
        self.assertTrue(
            all(
                b["districtId"] in data["semanticZoning"]
                for b in data["scene"]["buildings"]
            )
        )
        self.assertEqual(data["routing"]["routes"], self.world["routing"]["routes"])

    def test_membership_evidence_and_parcel_tampering_fail(self):
        for mutation in ("evidence", "membership", "polygon", "parcel"):
            w = copy.deepcopy(self.world)
            zone = next(z for z in w["zoning"]["zones"] if z["memberClaims"])
            if mutation == "evidence":
                zone["memberClaims"][0]["roles"][0]["evidenceIds"] = ["made-up"]
            elif mutation == "membership":
                zone["memberEntityIds"].pop()
            elif mutation == "polygon":
                zone["polygon"][0] = [9999, 9999]
            else:
                w["parcels"][0]["zoneId"] = "missing"
            with (
                self.subTest(mutation=mutation),
                self.assertRaisesRegex(ValueError, "zoning|semantic parcel"),
            ):
                validate_world(w, self.scene, self.graph)

    def test_unknown_names_weak_claims_and_tiny_groups_do_not_invent_semantics(self):
        members = self.scene["buildings"]
        entities = copy.deepcopy({e["id"]: e for e in self.graph["entities"]})
        for entity in entities.values():
            for role in entity.get("roles", []):
                role["confidence"] = "INFERRED"
        zones = candidates(members, entities, "parent")
        self.assertEqual([z["clusterKey"] for z in zones], ["GENERAL_MIXED"])
        self.assertEqual(zones[0]["classification"]["evidenceIds"], [])
        entities = {e["id"]: e for e in self.graph["entities"]}
        tiny = candidates(members[:3], entities, "parent")
        self.assertEqual([z["clusterKey"] for z in tiny], ["GENERAL_MIXED"])

    def test_hinted_growth_keeps_unrelated_zones_and_building_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            first = generate_world(scene, graph, zoning="semantic")
            (repo / "another.rs").write_text("fn another() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/zoning")
            scene = generate_city(graph)
            changed = generate_world(scene, graph, zoning="semantic", previous=first)
        validate_world(changed, scene, graph)
        self.assertEqual(first["envelope"], changed["envelope"])
        self.assertTrue(changed["anchors"]["reusedDistrictIds"])
        old = {p["entityId"]: p for p in first["parcels"]}
        for p in changed["parcels"]:
            if p["entityId"] in old:
                self.assertEqual(p, old[p["entityId"]])

    def test_explicit_grammar_fallback_does_not_erase_test_evidence(self):
        with patch("metropogits.world.zoning.organic_slots", return_value=([], [], 0)):
            w = generate_world(self.scene, self.graph, zoning="semantic")
        validate_world(w, self.scene, self.graph)
        campus = next(
            z for z in w["zoning"]["zones"] if z["clusterKey"] == "CAMPUS_RESEARCH"
        )
        self.assertEqual(campus["planningProfile"], "GRID")
        self.assertEqual(len(campus["memberClaims"]), 24)
        self.assertTrue(
            any("local GRID fallback" in d["reason"] for d in w["diagnostics"])
        )

    def test_conflicting_options_and_malformed_hints_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "selects neighborhood"):
            generate_world(self.scene, self.graph, planning="radial", zoning="semantic")
        malformed = copy.deepcopy(self.world)
        malformed["zoning"]["zones"][0]["polygon"] = []
        with self.assertRaisesRegex(ValueError, "previous world polygon"):
            generate_world(
                self.scene, self.graph, previous=malformed, zoning="semantic"
            )


if __name__ == "__main__":
    unittest.main()
