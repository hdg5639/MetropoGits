import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from test_world_neighborhoods import fixture
from metropogits.world.district_patterns import street_field
from metropogits.world.export import package_world
from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world
from metropogits.world.zoning import planning_document

ROOT = Path(__file__).parents[1]


class DistrictPatternTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene, cls.graph = fixture(Path(directory))
        cls.options = dict(
            zoning="neighborhoods",
            pattern_scale="district",
            outline="varied",
            seed="inherited-patterns",
        )
        cls.world = generate_world(
            cls.scene, cls.graph, planning="radial", **cls.options
        )

    def test_all_five_patterns_survive_real_semantic_subdivision_without_fallback(self):
        for profile in ("grid", "radial", "organic", "industrial", "hybrid"):
            with self.subTest(profile=profile):
                world = generate_world(
                    self.scene, self.graph, planning=profile, **self.options
                )
                report = validate_world(world, self.scene, self.graph)
                self.assertEqual(report["accessibleBuildings"], 48)
                self.assertEqual(report["representedEdges"], 32)
                self.assertGreater(len(world["zoning"]["zones"]), 1)
                self.assertEqual(
                    {p["profile"] for p in world["zoning"]["districtPatterns"]},
                    {profile.upper()},
                )
                self.assertEqual(
                    {b["planningProfile"] for b in world["zoning"]["blocks"]},
                    {profile.upper()},
                )
                self.assertFalse(
                    any("fallback" in d["reason"] for d in world["diagnostics"])
                )
                actual = {p["entityId"]: p["zoneId"] for p in world["parcels"]}
                for z in world["zoning"]["zones"]:
                    self.assertTrue(
                        all(actual[k] == z["id"] for k in z["memberEntityIds"])
                    )

    def test_reserved_street_field_exists_without_source_assignment_and_ignores_labels(
        self,
    ):
        parent = self.world["districts"][0]
        candidates, roads, pattern = street_field(
            parent["polygon"], parent["localSeed"], "RADIAL", parent["id"]
        )
        self.assertEqual(roads, self.world["zoning"]["mainRoads"])
        self.assertEqual([pattern], self.world["zoning"]["districtPatterns"])
        self.assertGreater(len(candidates), 48)
        from metropogits.world.neighborhoods import neighborhood_candidates

        original = neighborhood_candidates

        def renamed(*args):
            return [dict(z, label="Different label") for z in original(*args)]

        with patch(
            "metropogits.world.generator.neighborhood_candidates", side_effect=renamed
        ):
            other = generate_world(
                self.scene, self.graph, planning="radial", **self.options
            )
        self.assertEqual(
            self.world["zoning"]["mainRoads"], other["zoning"]["mainRoads"]
        )
        self.assertEqual(self.world["parcels"], other["parcels"])

    def test_schema_repeat_bytes_and_source_contracts(self):
        source = copy.deepcopy((self.scene, self.graph))
        for name, doc in (
            ("world-0.1", self.world),
            ("planning-0.4", planning_document(self.world)),
        ):
            Draft202012Validator(
                json.loads((ROOT / f"schemas/{name}.schema.json").read_text())
            ).validate(doc)
        other = generate_world(
            self.scene, self.graph, planning="radial", **self.options
        )
        validation = validate_world(other, self.scene, self.graph)
        self.assertEqual(
            package_world(self.world, self.scene, self.graph, validation),
            package_world(other, self.scene, self.graph, validation),
        )
        self.assertEqual(source, (self.scene, self.graph))

    def test_hinted_growth_keeps_all_frames_and_shared_pattern(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            first = generate_world(scene, graph, planning="radial", **self.options)
            (repo / "new.rs").write_text("fn unknown() {}", encoding="utf8")
            from metropogits.cli import analyze_repository
            from metropogits.layout import generate_city

            graph = analyze_repository(repo, repository_id="fixture/neighborhoods")
            scene = generate_city(graph)
            other = generate_world(
                scene, graph, planning="radial", previous=first, **self.options
            )
        validate_world(other, scene, graph)
        old = {p["entityId"]: p for p in first["parcels"]}
        self.assertTrue(other["anchors"]["reusedDistrictIds"])
        self.assertEqual(first["zoning"]["mainRoads"], other["zoning"]["mainRoads"])
        for p in other["parcels"]:
            if p["entityId"] in old:
                self.assertEqual(p, old[p["entityId"]])

    def test_inheritance_and_pattern_tampering_are_rejected(self):
        for field in ("pattern", "angle", "boundary", "road", "scale"):
            world = copy.deepcopy(self.world)
            if field == "pattern":
                world["zoning"]["districtPatterns"][0]["hub"][0] += 1
            elif field == "angle":
                world["parcels"][0]["angle"] += 0.1
            elif field == "boundary":
                world["zoning"]["blocks"][0]["boundaryTypes"][0] = "ROAD_CUT"
            elif field == "road":
                world["zoning"]["mainRoads"][0]["width"] += 1
            else:
                world.pop("patternScale")
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_world(world, self.scene, self.graph)
        with self.assertRaisesRegex(ValueError, "requires neighborhoods"):
            generate_world(self.scene, self.graph, pattern_scale="district")

    def test_subdivision_work_is_bounded(self):
        with (
            patch("metropogits.world.district_patterns.MAX_SUBDIVISION_WORK", 1),
            self.assertRaisesRegex(ValueError, "subdivision work limit"),
        ):
            generate_world(self.scene, self.graph, planning="radial", **self.options)

    def test_old_block_mode_hints_do_not_silently_change_meaning(self):
        old = generate_world(
            self.scene,
            self.graph,
            **dict(self.options, pattern_scale="block", planning="radial"),
        )
        world = generate_world(
            self.scene, self.graph, previous=old, planning="radial", **self.options
        )
        validate_world(world, self.scene, self.graph)
        self.assertEqual(world["anchors"]["reusedDistrictIds"], [])
        self.assertTrue(
            any(
                d["reason"].startswith("incompatible previous")
                for d in world["diagnostics"]
            )
        )


if __name__ == "__main__":
    unittest.main()
