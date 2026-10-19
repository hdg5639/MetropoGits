"""Physical street functions must not invent source relationships or geometry."""

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
from metropogits.world.generator import generate_world
from metropogits.world.export import package_world, view_data
from metropogits.world.geometry import inside, ribbon
from metropogits.world.infrastructure import atomic_streets
from metropogits.world.street_hierarchy import derive_street_plan, marking_surfaces
from metropogits.world.validation import validate_world
from test_world_neighborhoods import fixture


def network():
    roads = [
        dict(start=a, end=b, width=3.5, access=access)
        for a, b, access in (
            ([0, 0], [100, 0], False),
            ([0, 0], [0, 50], False),
            ([0, 50], [100, 50], False),
            ([100, 0], [100, 50], False),
            ([50, 50], [50, 53], True),
        )
    ]
    return dict(
        streets=atomic_streets(roads),
        topology=dict(edges=[dict(start=[0, 0], end=[100, 0], districtIds=["a", "b"])]),
        zoning=dict(
            mainRoads=[dict(id="spine", start=[0, 50], end=[100, 50])],
            zones=[dict(id="z", accessPorts=[[0, 0], [0, 50]])],
        ),
        parcels=[dict(entityId="source", entrance=[50, 53], streetPoint=[50, 50])],
    )


class StreetHierarchyTests(unittest.TestCase):
    def test_offline_classes_and_connected_coarse_graph_leave_originals_untouched(self):
        world = network()
        before = copy.deepcopy(world)
        plan = derive_street_plan(world)
        self.assertEqual(world, before)
        self.assertEqual(plan["summary"]["componentCount"], 1)
        self.assertEqual(plan["summary"]["unattachedEntityIds"], [])
        self.assertEqual(plan["summary"]["unattachedPortIds"], [])
        self.assertEqual(plan["summary"]["classCounts"]["SERVICE"], 1)
        self.assertEqual(plan["summary"]["classCounts"]["PEDESTRIAN"], 0)
        self.assertTrue(
            any("COARSE_CONNECTOR" in p["reasons"] for p in plan["segments"].values())
        )
        adjacency = {}
        for s in world["streets"]:
            cls = plan["segments"][s["id"]]["streetClass"]
            self.assertEqual(cls == "SERVICE", s["access"])
            if s["id"] in plan["backboneStreetIds"]:
                a, b = tuple(s["start"]), tuple(s["end"])
                adjacency.setdefault(a, set()).add(b)
                adjacency.setdefault(b, set()).add(a)
        visited = set()
        queue = [min(adjacency)]
        while queue:
            at = queue.pop()
            if at not in visited:
                visited.add(at)
                queue.extend(adjacency[at] - visited)
        self.assertEqual(visited, set(adjacency))
        world["streets"].reverse()
        world["zoning"]["mainRoads"].reverse()
        self.assertEqual(derive_street_plan(world), plan)

    def test_no_source_edge_requirement_and_no_fake_component_or_port_attachment(self):
        world = network()
        world["streets"] += atomic_streets(
            [dict(start=[200, 0], end=[230, 0], width=3, access=False)]
        )
        world["zoning"]["zones"][0]["accessPorts"].append([999, 999])
        world["parcels"].append(
            dict(entityId="missing", entrance=[999, 999], streetPoint=[999, 999])
        )
        world["parcels"].append(
            dict(
                entityId="disconnected-frontage",
                entrance=[215, 0],
                streetPoint=[50, 50],
            )
        )
        plan = derive_street_plan(world)
        self.assertEqual(plan["summary"]["componentCount"], 2)
        self.assertEqual(
            plan["summary"]["unattachedEntityIds"], ["disconnected-frontage", "missing"]
        )
        self.assertEqual(len(plan["summary"]["unattachedPortIds"]), 1)
        self.assertNotIn("edgeIds", plan)
        self.assertTrue(
            all(
                "LOCAL_CENTER" in p["reasons"]
                for k, p in plan["segments"].items()
                if next(s for s in world["streets"] if s["id"] == k)["start"]
                == [200, 0]
            )
        )

    def test_diagonal_structural_markings_stay_in_real_pavement_and_clear_junctions(
        self,
    ):
        world = network()

        def rotate(p):
            return [
                round((p[0] - p[1]) / math.sqrt(2), 4),
                round((p[0] + p[1]) / math.sqrt(2), 4),
            ]

        for s in world["streets"]:
            s["start"], s["end"] = rotate(s["start"]), rotate(s["end"])
        for group in (world["topology"]["edges"], world["zoning"]["mainRoads"]):
            for r in group:
                r["start"], r["end"] = rotate(r["start"]), rotate(r["end"])
        world["parcels"] = []
        world["zoning"]["zones"] = []
        world["streetPlan"] = derive_street_plan(world)
        pieces = marking_surfaces(world)
        self.assertTrue(pieces)
        roads = {s["id"]: s for s in world["streets"]}
        for p in pieces:
            s = roads[p["physicalId"]]
            self.assertTrue(p["structuralMarking"])
            self.assertTrue(
                all(
                    inside(v, ribbon(s["start"], s["end"], s["width"]), -0.001)
                    for v in p["points"]
                )
            )
        self.assertEqual(pieces, marking_surfaces(world))

    def test_work_limits_are_explicit_instead_of_silently_dropping_infrastructure(self):
        for key in ("MAX_STREETS", "MAX_INDEX", "MAX_CHECKS", "MAX_STATES"):
            with (
                self.subTest(key=key),
                patch("metropogits.world.street_hierarchy." + key, 0),
            ):
                with self.assertRaisesRegex(ValueError, "street hierarchy"):
                    derive_street_plan(network())
        world = network()
        world["streetPlan"] = derive_street_plan(world)
        with patch("metropogits.world.street_hierarchy.MAX_PAINT", 0):
            with self.assertRaisesRegex(ValueError, "paint work limit"):
                marking_surfaces(world)


class WorldStreetPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene, cls.graph = fixture(Path(directory))
        cls.options = dict(
            zoning="neighborhoods",
            pattern_scale="adaptive",
            street_policy="porous",
            planning="varied",
            outline="varied",
            seed="hierarchy-test",
        )
        cls.world = generate_world(
            cls.scene, cls.graph, **cls.options, street_hierarchy=True
        )

    def test_additive_flag_keeps_every_old_geometry_fact_and_exact_repeat(self):
        bare = generate_world(self.scene, self.graph, **self.options)
        self.assertEqual(
            {k: v for k, v in self.world.items() if k != "streetPlan"}, bare
        )
        self.assertEqual(
            self.world,
            generate_world(
                self.scene, self.graph, **self.options, street_hierarchy=True
            ),
        )
        validate_world(self.world, self.scene, self.graph)
        schema = json.loads(
            Path("schemas/world-0.1.schema.json").read_text(encoding="utf8")
        )
        Draft202012Validator(schema).validate(self.world)

    def test_independent_reconstruction_rejects_forged_class_or_missing_source_access(
        self,
    ):
        bad = copy.deepcopy(self.world)
        key = next(iter(bad["streetPlan"]["segments"]))
        bad["streetPlan"]["segments"][key]["streetClass"] = "PEDESTRIAN"
        with self.assertRaisesRegex(ValueError, "street hierarchy"):
            validate_world(bad, self.scene, self.graph)
        bad = copy.deepcopy(self.world)
        bad["streetPlan"]["frontages"].pop(next(iter(bad["streetPlan"]["frontages"])))
        with self.assertRaisesRegex(ValueError, "street hierarchy"):
            validate_world(bad, self.scene, self.graph)

    def test_cpu_browser_and_planning_share_classification_without_source_changes(self):
        result = validate_world(self.world, self.scene, self.graph)
        package = package_world(self.world, self.scene, self.graph, result)
        self.assertEqual(
            package, package_world(self.world, self.scene, self.graph, result)
        )
        planning = json.loads(package["planning.json"])
        self.assertEqual(planning["streetPlan"], self.world["streetPlan"])
        schema = json.loads(
            Path("schemas/planning-0.5.schema.json").read_text(encoding="utf8")
        )
        Draft202012Validator(schema).validate(planning)
        data = view_data(self.world, self.scene, self.graph)
        self.assertEqual(
            data["physicalStreetPlan"]["summary"], self.world["streetPlan"]["summary"]
        )
        profiles = self.world["streetPlan"]["segments"]
        for s in data["routing"]["segments"]:
            self.assertEqual(s["streetClass"], profiles[s["physicalId"]]["streetClass"])
        self.assertIn(b"Street hierarchy (structural)", package["index.html"])
        self.assertTrue(data["physicalStreetPlan"]["markings"])
        # Single-parent fixture has no interdistrict arterial; README must not
        # manufacture one just to expose paint. Collector pavement still renders.
        self.assertEqual(
            self.world["streetPlan"]["summary"]["classCounts"]["ARTERIAL"], 0
        )
        self.assertTrue(b'fill="#45565f"' in package["showcase.svg"])
        self.assertTrue(
            b'data-structural="street-marking"' not in package["showcase.svg"]
        )

    def test_hinted_small_edit_can_cross_presentation_flag_without_moving_old_frames(
        self,
    ):
        # Reuse the maintained, terrain-feasible porous growth golden case.
        options = dict(self.options, terrain="river-landscape", seed="porous-test")
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            old = generate_world(scene, graph, **options)
            validate_world(old, scene, graph)
            (repo / "zz_extra.rs").write_text("fn generic() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/neighborhoods")
            scene = generate_city(graph)
            new = generate_world(
                scene, graph, previous=old, street_hierarchy=True, **options
            )
        self.assertEqual(old["terrain"], new["terrain"])
        frames = {p["entityId"]: p for p in new["parcels"]}
        for p in old["parcels"]:
            self.assertEqual(p, frames[p["entityId"]])
        self.assertTrue("streetPlan" in new)
        validate_world(new, scene, graph)


if __name__ == "__main__":
    unittest.main()
