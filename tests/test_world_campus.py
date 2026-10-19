"""Campus morphology is opt-in, connected, capacity-safe and source-evidenced."""

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
from metropogits.world.campus import _quad, courtyard_layout, eligibility
from metropogits.world.export import package_world
from metropogits.world.generator import generate_world
from metropogits.world.geometry import rectangle, ribbon
from metropogits.street_diagonals import overlap
from metropogits.world.landscape import generate_landscape
from metropogits.world.validation import validate_world


def fixture(repo, count=24):
    for i in range(count):
        (repo / f"suite_{i}.test.ts").write_text(
            f'import {{value}} from "./helper_{i}";\nexport const result=value;\n',
            encoding="utf8",
        )
        (repo / f"helper_{i}.ts").write_text("export const value=1;\n", encoding="utf8")
    graph = analyze_repository(repo, repository_id="fixture/campus")
    return generate_city(graph), graph


class CampusKernelTests(unittest.TestCase):
    def test_name_only_is_not_evidence_and_seeded_choice_is_not_a_role_mapping(self):
        zone = dict(
            id="tests/lab",
            parentId="p",
            memberEntityIds=[str(i) for i in range(24)],
            memberClaims=[],
        )
        self.assertFalse(eligibility(zone, {}, "seed")["eligible"])
        zone["memberClaims"] = [
            dict(
                entityId=str(i),
                roles=[dict(value="TEST", confidence="DIRECT", evidenceIds=[f"e{i}"])],
            )
            for i in range(12)
        ]
        decisions = [eligibility(zone, {}, str(i)) for i in range(24)]
        self.assertTrue(all(d["eligible"] for d in decisions))
        self.assertTrue(any(d["draw"] < d["probability"] for d in decisions))
        self.assertTrue(any(d["draw"] >= d["probability"] for d in decisions))
        zone["memberClaims"][0]["roles"][0]["confidence"] = "UNKNOWN"
        self.assertNotIn("0", eligibility(zone, {}, "seed")["supportingEntityIds"])
        zone["memberClaims"] = []
        pairs = {(str(i), str((i + 1) % 24)): 1 for i in range(24)}
        self.assertTrue(eligibility(zone, pairs, "seed")["eligible"])
        pairs.update({(str(i), "outside-" + str(i)): 1 for i in range(24)})
        self.assertFalse(eligibility(zone, pairs, "seed")["eligible"])

    def test_corners_rotate_whole_plots_and_overfull_or_thin_land_falls_back(self):
        plots, walks, court, _ = _quad([0, 0], 0.3, 25, 17, "N", "quad")
        self.assertEqual(len(plots), 19)
        self.assertTrue(
            any(
                abs(math.sin(p["angle"] - 0.3)) > 0.6
                and abs(math.cos(p["angle"] - 0.3)) > 0.6
                for p in plots
            )
        )
        self.assertTrue(walks)
        self.assertTrue(court["polygon"])
        for a, b in ((17, 13), (25, 17), (33, 21), (41, 25), (49, 29)):
            choices = _quad([0, 0], 0.3, a, b, "N", "corners")[0]
            self.assertFalse(
                any(
                    overlap(p["polygon"], q["polygon"])
                    for i, p in enumerate(choices)
                    for q in choices[:i]
                )
            )
        poly = rectangle([0, 0], 0, 220, 180)
        roads = [
            dict(id=str(i), start=a, end=b, width=3, access=False)
            for i, (a, b) in enumerate(zip(poly, poly[1:] + poly[:1]))
        ]
        zone = dict(id="z", parentId="p", memberEntityIds=[str(i) for i in range(16)])
        self.assertIsNotNone(courtyard_layout(zone, poly, 0, "quad", roads, None, {}))
        self.assertIsNone(
            courtyard_layout(
                zone, rectangle([0, 0], 0, 15, 220), 0, "quad", roads, None, {}
            )
        )
        with (
            patch("metropogits.world.campus.MAX_CENTERS", 0),
            self.assertRaisesRegex(ValueError, "candidate limit"),
        ):
            courtyard_layout(zone, poly, 0, "quad", roads, None, {})


class CampusWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene, cls.graph = fixture(Path(directory))
        cls.options = dict(
            seed="campus-fixture",
            zoning="neighborhoods",
            pattern_scale="adaptive",
            planning="varied",
            outline="varied",
            street_policy="porous",
        )
        cls.world = generate_world(cls.scene, cls.graph, **cls.options, campus=True)

    def test_real_fixture_selects_connected_members_without_creating_source_facts(self):
        w = self.world
        report = validate_world(w, self.scene, self.graph)
        self.assertEqual(report["accessibleBuildings"], 48)
        self.assertTrue(w["campusPlan"]["sites"])
        self.assertGreater(w["streetPlan"]["summary"]["classCounts"]["PEDESTRIAN"], 0)
        pedestrian = {
            k
            for k, s in w["streetPlan"]["segments"].items()
            if s["streetClass"] == "PEDESTRIAN"
        }
        self.assertTrue(
            pedestrian & {s["physicalId"] for s in w["routing"]["segments"]}
        )
        for site in w["campusPlan"]["sites"]:
            for p in w["parcels"]:
                if (
                    p["zoneId"] != site["zoneId"]
                    or p["entityId"] in site["memberEntityIds"]
                ):
                    continue
                self.assertFalse(
                    any(
                        overlap(
                            ribbon(p["entrance"], p["streetPoint"], 0.9),
                            ribbon(s["start"], s["end"], s["width"] + 0.2),
                        )
                        for s in site["walkways"]
                    )
                )
        self.assertEqual(
            w, generate_world(self.scene, self.graph, **self.options, campus=True)
        )
        package = package_world(w, self.scene, self.graph, report)
        self.assertEqual(json.loads(package["city.json"]), self.scene)
        self.assertEqual(json.loads(package["graph.ucg.json"]), self.graph)
        for asset in ("viewer.js", "viewer-3d.js"):
            self.assertIn(b"campus-member", package["assets/" + asset])
            self.assertIn(
                b"not a research or runtime-communication claim",
                package["assets/" + asset],
            )
        for schema, doc in [
            ("world-0.1", "world.json"),
            ("planning-0.5", "planning.json"),
        ]:
            Draft202012Validator(
                json.loads(
                    Path("schemas", schema + ".schema.json").read_text(encoding="utf8")
                )
            ).validate(json.loads(package[doc]))
        old = generate_world(self.scene, self.graph, **self.options)
        self.assertNotIn("campusPlan", old)
        self.assertEqual(old["envelope"], w["envelope"])
        self.assertEqual(
            {z["id"]: z["polygon"] for z in old["zoning"]["zones"]},
            {z["id"]: z["polygon"] for z in w["zoning"]["zones"]},
        )
        selected = {s["zoneId"] for s in w["campusPlan"]["sites"]}
        self.assertEqual(
            [p for p in old["parcels"] if p["zoneId"] not in selected],
            [p for p in w["parcels"] if p["zoneId"] not in selected],
        )
        self.assertEqual(
            {
                r["id"]: (r["source"], r["target"], r["edgeIds"])
                for r in old["routing"]["routes"]
            },
            {
                r["id"]: (r["source"], r["target"], r["edgeIds"])
                for r in w["routing"]["routes"]
            },
        )

    def test_forged_courts_and_member_lists_are_rejected_by_reconstruction(self):
        bad = copy.deepcopy(self.world)
        self.assertTrue(bad["campusPlan"]["sites"])
        bad["campusPlan"]["sites"][0]["memberEntityIds"].append("fake")
        with self.assertRaisesRegex(ValueError, "campus"):
            validate_world(bad, self.scene, self.graph)

    def test_same_policy_growth_preserves_existing_source_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            old = generate_world(scene, graph, **self.options, campus=True)
            (repo / "zz_extra.rs").write_text("fn generic() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/campus")
            scene = generate_city(graph)
            new = generate_world(
                scene, graph, previous=old, **self.options, campus=True
            )
        validate_world(new, scene, graph)
        frames = {p["entityId"]: p for p in new["parcels"]}
        self.assertTrue(all(frames[p["entityId"]] == p for p in old["parcels"]))

    def test_work_budget_retains_the_original_grammar_and_source_access(self):
        with patch("metropogits.world.campus.MAX_CENTERS", 0):
            retained = generate_world(
                self.scene, self.graph, **self.options, campus=True
            )
            validate_world(retained, self.scene, self.graph)
        bare = generate_world(self.scene, self.graph, **self.options)
        self.assertEqual(retained["campusPlan"]["sites"], [])
        self.assertTrue(
            any(
                d["reason"] == "RESOURCE_LIMIT_FALLBACK"
                for d in retained["campusPlan"]["decisions"].values()
            )
        )
        self.assertEqual(retained["parcels"], bare["parcels"])
        self.assertEqual(retained["streets"], bare["streets"])

    def test_procedural_trees_do_not_fill_the_reserved_court(self):
        landscape = generate_landscape(self.world)
        for site in self.world["campusPlan"]["sites"]:
            for court in site["courts"]:
                self.assertFalse(
                    any(
                        overlap(
                            rectangle(t["center"], 0, t["radius"] * 2, t["radius"] * 2),
                            court["polygon"],
                        )
                        for t in landscape["trees"]
                    )
                )


if __name__ == "__main__":
    unittest.main()
