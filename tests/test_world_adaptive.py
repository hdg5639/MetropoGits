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
