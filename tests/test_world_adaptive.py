import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from test_world_neighborhoods import fixture
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.affinity import dependency_pairs
from metropogits.world.adaptive import skeleton, profile_plan
from metropogits.world.export import package_world
from metropogits.world.functional import functional_candidates
from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world
from metropogits.world.zoning import planning_document

ROOT = Path(__file__).parents[1]


class AdaptiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene, cls.graph = fixture(Path(directory))
        cls.options = dict(
            zoning="neighborhoods",
            pattern_scale="adaptive",
            planning="radial",
            outline="varied",
            seed="mixed-functional",
        )
        cls.world = generate_world(cls.scene, cls.graph, **cls.options)

    def test_related_verified_roles_share_physical_neighborhoods(self):
        entities = {e["id"]: e for e in self.graph["entities"]}
        pairs = dependency_pairs(
            self.graph,
            dict.fromkeys((b["entityId"] for b in self.scene["buildings"]), "parent"),
        )
        cross = [
            (a, b)
            for a, b in pairs
            if entities[a].get("roles")
            and entities[b].get("roles")
            and {r["value"] for r in entities[a]["roles"]}.isdisjoint(
                {r["value"] for r in entities[b]["roles"]}
            )
        ]
        self.assertEqual(len(cross), 16)
        old = generate_world(
            self.scene, self.graph, **dict(self.options, pattern_scale="district")
        )

        def colocated(world):
            zone = {p["entityId"]: p["zoneId"] for p in world["parcels"]}
            return sum(zone[a] == zone[b] for a, b in cross)

        self.assertEqual(colocated(old), 0)
        self.assertEqual(colocated(self.world), 16)
        report = validate_world(self.world, self.scene, self.graph)
        self.assertEqual(report["representedEdges"], 32)
        self.assertEqual(report["accessibleBuildings"], 48)
        z = self.world["zoning"]["zones"][0]
        self.assertEqual(z["roleCounts"], {"PERSISTENCE_ADAPTER": 16, "SERVICE": 16})
        self.assertEqual(len(z["internalEdgeIds"]), 32)

    def test_same_principal_contains_inherited_and_adapted_patterns(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            for i in range(84):
                (repo / f"Service{i}.java").write_text(
                    f"package demo;\nimport org.springframework.stereotype.Service;\n@Service\nclass Service{i} {{ Store{i} store; }}\n",
                    encoding="utf8",
                )
                (repo / f"Store{i}.java").write_text(
                    f"package demo;\nimport org.springframework.stereotype.Repository;\n@Repository\nclass Store{i} {{}}\n",
                    encoding="utf8",
                )
                (repo / f"Helper{i}.java").write_text(
                    f"package demo; class Helper{i} {{ Service{i} service; }}",
                    encoding="utf8",
                )
            graph = analyze_repository(repo, repository_id="fixture/adaptive-patterns")
            scene = generate_city(graph)
        world = generate_world(scene, graph, **self.options)
        validate_world(world, scene, graph)
        self.assertEqual(len(world["districts"]), 1)
        self.assertEqual(len(world["zoning"]["zones"]), 3)
        self.assertEqual(
            {b["patternMode"] for b in world["zoning"]["blocks"]},
            {"INHERITED", "ADAPTED"},
        )
        self.assertGreater(
            len({b["planningProfile"] for b in world["zoning"]["blocks"]}), 1
        )
        pattern = world["zoning"]["districtPatterns"][0]
        self.assertGreater(len(pattern["protectedStreetIds"]), 0)
        self.assertLess(pattern["roadCount"], pattern["fullFieldRoadCount"])
        self.assertTrue(
            all(
                "SERVICE" in z["roleCounts"]
                and "PERSISTENCE_ADAPTER" in z["roleCounts"]
                for z in world["zoning"]["zones"]
            )
        )

    def test_repeat_schemas_and_source_fidelity(self):
        before = copy.deepcopy((self.scene, self.graph))
        for name, document in (
            ("world-0.1", self.world),
            ("planning-0.5", planning_document(self.world)),
        ):
            Draft202012Validator(
                json.loads((ROOT / f"schemas/{name}.schema.json").read_text())
            ).validate(document)
        other = generate_world(self.scene, self.graph, **self.options)
        report = validate_world(other, self.scene, self.graph)
        self.assertEqual(
            package_world(self.world, self.scene, self.graph, report),
            package_world(other, self.scene, self.graph, report),
        )
        self.assertEqual(before, (self.scene, self.graph))

    def test_shared_skeleton_does_not_overlay_parent_frontage_rows(self):
        roads = [
            dict(id=str(i), sourceLaneId=key, start=[0, 0], end=[10, 0])
            for i, key in enumerate(
                ("row:0", "organic:row:3", "orbit:4:0", "court:0:3",
                 "collector:0", "organic:collector:1", "spoke:2", "spine:0")
            )
        ]
        self.assertEqual(skeleton(roads, stitch=True), roads[4:])
        self.assertEqual(skeleton(roads), roads)
        self.assertTrue(skeleton(roads[:4], stitch=True))
        self.assertEqual(skeleton([], stitch=True), [])
        self.assertEqual(skeleton(roads, stitch=True, morphology=True), [roads[2], *roads[4:]])
        self.assertEqual(self.world["generatorVersion"], "flat-adaptive-neighborhoods/0.3")
        self.assertTrue(all(
            p["version"] == "adaptive-patterns/0.3"
            for p in self.world["zoning"]["districtPatterns"]
        ))

    def test_legacy_adaptive_validation_and_hint_rejection(self):
        # Reconstruct the former reservation policy without external artifacts.
        with patch(
            "metropogits.world.adaptive.skeleton",
            side_effect=lambda roads, **kwargs: skeleton(roads),
        ):
            old = generate_world(self.scene, self.graph, **self.options)
        old["generatorVersion"] = "flat-adaptive-neighborhoods/0.1"
        for p in old["zoning"]["districtPatterns"]:
            p["version"] = "adaptive-patterns/0.1"
        validate_world(old, self.scene, self.graph)
        new = generate_world(self.scene, self.graph, previous=old, **self.options)
        validate_world(new, self.scene, self.graph)
        self.assertFalse(new["anchors"]["reusedDistrictIds"])
        self.assertTrue(any(
            d["reason"] == "incompatible previous world; deterministic cold rebuild"
            for d in new["diagnostics"]
        ))
        wrong = copy.deepcopy(old)
        wrong["generatorVersion"] = new["generatorVersion"]
        with self.assertRaisesRegex(ValueError, "pattern metadata mismatch"):
            validate_world(wrong, self.scene, self.graph)

    def test_invalid_quantized_child_is_repaired_not_accepted(self):
        from metropogits.world.power import power_partition

        calls = 0
        def broken_first(*args):
            nonlocal calls
            cells, allocation = power_partition(*args)
            calls += 1
            if calls == 1:
                key = next(iter(cells))
                cells[key] = list(reversed(cells[key]))
            return cells, allocation

        with patch("metropogits.world.adaptive.power_partition", side_effect=broken_first):
            world = generate_world(self.scene, self.graph, **self.options)
        validate_world(world, self.scene, self.graph)
        self.assertGreater(calls, 1)
        self.assertTrue(any(
            d["reason"] == "adaptive shared-cut quantization repair"
            for d in world["diagnostics"]
        ))

    def test_local_axes_follow_reference_morphology_not_cleanup(self):
        # A ring tangent and a radial spoke imply very different local grids.
        zones = [dict(id="large", memberEntityIds=["a", "b"], internalEdgeIds=[], requestedProfile="RADIAL"),
                 dict(id="mixed", memberEntityIds=["c"], internalEdgeIds=[], requestedProfile="HYBRID")]
        polygons = {k: [[0, 0], [10, 0], [10, 10], [0, 10]] for k in ("large", "mixed")}
        roads = [dict(id="ring", start=[0, 4], end=[10, 4]),
                 dict(id="spoke", start=[9, -20], end=[9, 30])]
        pattern = dict(profile="RADIAL", primaryAxis=0)
        reference = profile_plan(zones, polygons, pattern, roads)
        self.assertNotEqual(reference, profile_plan(zones, polygons, pattern, roads[1:]))
        # Physical removal must never erase a protected source trip's pavement.
        world = copy.deepcopy(self.world)
        used = world["routing"]["segments"][0]["physicalId"]
        world["streets"] = [s for s in world["streets"] if s["id"] != used]
        with self.assertRaises(ValueError):
            validate_world(world, self.scene, self.graph)

    def test_hinted_small_edit_preserves_complete_old_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            old = generate_world(scene, graph, **self.options)
            (repo / "zz_extra.rs").write_text("fn unknown() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/neighborhoods")
            scene = generate_city(graph)
            world = generate_world(scene, graph, previous=old, **self.options)
        validate_world(world, scene, graph)
        frames = {p["entityId"]: p for p in old["parcels"]}
        self.assertTrue(world["anchors"]["reusedDistrictIds"])
        self.assertEqual(old["zoning"]["mainRoads"], world["zoning"]["mainRoads"])
        for p in world["parcels"]:
            if p["entityId"] in frames:
                self.assertEqual(frames[p["entityId"]], p)

    def test_shared_junction_policy_preserves_frames_and_original_trip_budgets(self):
        from metropogits.world.junctions import check_trip_budgets

        shared = generate_world(self.scene, self.graph, street_policy="shared", **self.options)
        self.assertEqual(shared["generatorVersion"], "flat-adaptive-neighborhoods/0.4")
        self.assertEqual(shared["parcels"], self.world["parcels"])
        self.assertEqual(shared["districts"], self.world["districts"])
        self.assertEqual(shared["zoning"], self.world["zoning"])
        self.assertEqual(shared, generate_world(self.scene, self.graph, street_policy="shared", **self.options))
        check_trip_budgets(self.world["routing"], shared["routing"])
        validate_world(shared, self.scene, self.graph)
        schema = json.loads((ROOT / "schemas/world-0.1.schema.json").read_text(encoding="utf8"))
        Draft202012Validator(schema).validate(shared)
        self.assertEqual(shared["diagnostics"][-1]["version"], "shared-junctions/0.1")
        for policy in ("not-a-policy",):
            with self.assertRaises(ValueError):
                generate_world(self.scene, self.graph, street_policy=policy, **self.options)
        with self.assertRaises(ValueError):
            generate_world(self.scene, self.graph, street_policy="shared")
        with self.assertRaises(ValueError):
            generate_world(self.scene, self.graph, street_policy="shared", _route=False, **self.options)
        with patch("metropogits.world.junctions.MAX_CHECKS", 0):
            fallback = generate_world(self.scene, self.graph, street_policy="shared", **self.options)
            validate_world(fallback, self.scene, self.graph)
        self.assertEqual(fallback["streets"], self.world["streets"])
        self.assertEqual(fallback["routing"], self.world["routing"])
        self.assertTrue(fallback["diagnostics"][-1]["budgetExhausted"])

    def test_shared_and_original_geography_hints_remain_compatible_after_small_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            old = generate_world(scene, graph, **self.options)
            (repo / "zz_extra.rs").write_text("fn unknown() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/neighborhoods")
            scene = generate_city(graph)
            shared = generate_world(scene, graph, previous=old, street_policy="shared", **self.options)
            original = generate_world(scene, graph, previous=shared, **self.options)
        validate_world(shared, scene, graph)
        validate_world(original, scene, graph)
        old_frames = {p["entityId"]: p for p in old["parcels"]}
        for world in (shared, original):
            self.assertTrue(world["anchors"]["reusedDistrictIds"])
            self.assertEqual(old["zoning"]["mainRoads"], world["zoning"]["mainRoads"])
            for p in world["parcels"]:
                if p["entityId"] in old_frames:
                    self.assertEqual(old_frames[p["entityId"]], p)

    def test_unknown_files_and_growth_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            for i in range(30):
                (repo / f"CacheAiServer{i}.rs").write_text(
                    "fn unknown() {}", encoding="utf8"
                )
            graph = analyze_repository(repo, repository_id="fixture/adaptive-unknown")
            scene = generate_city(graph)
        world = generate_world(scene, graph, **self.options)
        validate_world(world, scene, graph)
        self.assertTrue(
            all(
                not z["coreClaims"] and not z["roleCounts"]
                for z in world["zoning"]["zones"]
            )
        )
        self.assertEqual(world["routing"]["routes"], [])
        with (
            patch("metropogits.world.functional.MAX_GROWTH_WORK", 1),
            self.assertRaisesRegex(ValueError, "growth work limit"),
        ):
            functional_candidates(
                scene["buildings"],
                {e["id"]: e for e in graph["entities"]},
                "parent",
                graph,
            )

    def test_source_roles_internal_edges_and_skeleton_cannot_be_fabricated(self):
        for change in ("role", "edge", "pattern", "frame"):
            world = copy.deepcopy(self.world)
            if change == "role":
                world["zoning"]["zones"][0]["roleCounts"]["SERVICE"] += 1
            elif change == "edge":
                world["zoning"]["zones"][0]["internalEdgeIds"].append("fake")
            elif change == "pattern":
                world["zoning"]["districtPatterns"][0]["protectedStreetIds"] = []
            else:
                world["parcels"][0]["angle"] += 0.1
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_world(world, self.scene, self.graph)


if __name__ == "__main__":
    unittest.main()
