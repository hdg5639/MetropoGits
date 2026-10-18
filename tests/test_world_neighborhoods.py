import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.blocks import road_block_plan
from metropogits.world.export import package_world, view_data
from metropogits.world.generator import generate_world
from metropogits.world.geometry import area, inside
from metropogits.world.neighborhoods import neighborhood_candidates
from metropogits.world.validation import validate_world
from metropogits.world.zoning import planning_document
from metropogits.world.zone_access import access_corridors

ROOT = Path(__file__).parents[1]


def fixture(repo):
    for i in range(16):
        for name, annotation, body in (
            ("Service", "Service", f"Store{i} store;"),
            ("Store", "Repository", ""),
        ):
            (repo / f"{name}{i}.java").write_text(
                f"package demo;\nimport org.springframework.stereotype.{annotation};\n@{annotation}\nclass {name}{i} {{{body}}}\n",
                encoding="utf8",
            )
        (repo / f"Helper{i}.java").write_text(
            f"package demo;\nclass Helper{i} {{ Service{i} service; }}\n",
            encoding="utf8",
        )
    graph = analyze_repository(repo, repository_id="fixture/neighborhoods")
    return generate_city(graph), graph


class NeighborhoodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene, cls.graph = fixture(Path(directory))
        cls.options = dict(
            zoning="neighborhoods",
            planning="varied",
            outline="varied",
            seed="neighborhood-fixture",
        )
        cls.world = generate_world(cls.scene, cls.graph, **cls.options)

    def test_source_cores_stay_physically_in_their_neighborhood(self):
        report = validate_world(self.world, self.scene, self.graph)
        self.assertEqual(report["buildings"], 48)
        self.assertEqual(report["trips"], 32)
        parcels = {p["entityId"]: p for p in self.world["parcels"]}
        edges = {e["id"]: e for e in self.graph["edges"]}
        supporters = []
        for zone in self.world["zoning"]["zones"]:
            for key in zone["coreEntityIds"]:
                self.assertEqual(parcels[key]["zoneId"], zone["id"])
                self.assertTrue(
                    all(inside(v, zone["polygon"]) for v in parcels[key]["parcel"])
                )
            for support in zone["supportingMembers"]:
                supporters.append(support["entityId"])
                self.assertEqual(parcels[support["entityId"]]["zoneId"], zone["id"])
                self.assertTrue(support["coreEdgeIds"])
                self.assertTrue(all(key in edges for key in support["coreEdgeIds"]))
        self.assertEqual(len(supporters), 8)
        self.assertEqual(len(set(supporters)), 8)

    def test_schemas_full_bytes_and_immutable_source_facts(self):
        before = copy.deepcopy((self.scene, self.graph))
        for name, doc in (
            ("world-0.1", self.world),
            ("planning-0.3", planning_document(self.world)),
        ):
            Draft202012Validator(
                json.loads((ROOT / f"schemas/{name}.schema.json").read_text())
            ).validate(doc)
        other = generate_world(self.scene, self.graph, **self.options)
        validation = validate_world(other, self.scene, self.graph)
        self.assertEqual(self.world, other)
        self.assertEqual(
            package_world(self.world, self.scene, self.graph, validation),
            package_world(other, self.scene, self.graph, validation),
        )
        self.assertEqual(before, (self.scene, self.graph))
        data = view_data(self.world, self.scene, self.graph)
        self.assertTrue(
            all(s["color"] == "#26333e" for s in data["streets"]["surfaces"])
        )
        self.assertEqual(
            len(data["neighborhoodPlan"]["blocks"]), len(self.world["zoning"]["blocks"])
        )

    def test_local_pattern_change_cannot_regenerate_main_roads_or_blocks(self):
        # Deliberately replace the complete local grammar policy, not just a
        # color/seed. The upstream road/block planner has no profile parameter.
        with patch(
            "metropogits.world.neighborhood_layout.local_profile", return_value="GRID"
        ):
            other = generate_world(self.scene, self.graph, **self.options)
        validate_world(other, self.scene, self.graph)
        self.assertEqual(
            self.world["zoning"]["mainRoads"], other["zoning"]["mainRoads"]
        )
        self.assertEqual(
            [(b["id"], b["polygon"]) for b in self.world["zoning"]["blocks"]],
            [(b["id"], b["polygon"]) for b in other["zoning"]["blocks"]],
        )

    def test_actual_road_cuts_exist_before_any_local_grammar(self):
        polygon = [[0, 0], [300, 0], [300, 240], [0, 240]]
        identities = [str(i) for i in range(150)]
        zone = dict(id="zone", memberEntityIds=identities)
        blocks, roads, ports = road_block_plan(
            [zone], {"zone": polygon}, {}, {}, "seed", polygon
        )
        self.assertEqual(len(blocks), 3)
        self.assertTrue(roads)
        self.assertTrue(ports["zone"])
        self.assertTrue(any("ROAD_CUT" in b["boundaryTypes"] for b in blocks))
        self.assertAlmostEqual(
            sum(area(b["polygon"]) for b in blocks), area(polygon), delta=0.03
        )
        self.assertTrue(all("planningProfile" not in b for b in blocks))
        with (
            patch("metropogits.world.blocks.MAX_BLOCKS", 1),
            self.assertRaisesRegex(ValueError, "block count limit"),
        ):
            road_block_plan([zone], {"zone": polygon}, {}, {}, "seed", polygon)

    def test_backbone_ports_prefer_actual_cross_neighborhood_affinity(self):
        parent = [[0, 0], [200, 0], [100, 200]]
        polygons = {
            "a": [[0, 0], [200, 0], [100, 80]],
            "b": [[200, 0], [100, 200], [100, 80]],
            "c": [[100, 200], [0, 0], [100, 80]],
        }
        local = {key: [] for key in polygons}
        _, ordinary = access_corridors(polygons, local, parent, return_ports=True)
        _, weighted = access_corridors(
            polygons, local, parent, return_ports=True, affinity={("a", "c"): 16}
        )
        self.assertNotIn((50, 40), ordinary["a"])
        self.assertIn((50, 40), weighted["a"])
        self.assertIn((50, 40), weighted["c"])

    def test_hinted_new_unknown_file_keeps_existing_full_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            first = generate_world(scene, graph, **self.options)
            (repo / "unrelated.rs").write_text("fn unused() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/neighborhoods")
            scene = generate_city(graph)
            other = generate_world(scene, graph, previous=first, **self.options)
        validate_world(other, scene, graph)
        old = {p["entityId"]: p for p in first["parcels"]}
        self.assertTrue(other["anchors"]["reusedDistrictIds"])
        for parcel in other["parcels"]:
            if parcel["entityId"] in old:
                self.assertEqual(parcel, old[parcel["entityId"]])
        self.assertEqual(first["zoning"]["mainRoads"], other["zoning"]["mainRoads"])

    def test_unknowns_and_ambiguous_affinity_do_not_invent_supporting_members(self):
        entities = {e["id"]: e for e in self.graph["entities"]}
        no_edges = dict(self.graph, edges=[])
        candidates = neighborhood_candidates(
            self.scene["buildings"], entities, "parent", no_edges
        )
        self.assertFalse(any(z["supportingMembers"] for z in candidates))
        self.assertEqual(sum(len(z["memberEntityIds"]) for z in candidates), 48)
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            for i in range(30):
                (repo / f"AiCacheServer{i}.rs").write_text(
                    "fn unknown() {}", encoding="utf8"
                )
            graph = analyze_repository(
                repo, repository_id="fixture/unknown-neighborhood"
            )
            scene = generate_city(graph)
            world = generate_world(scene, graph, **self.options)
        validate_world(world, scene, graph)
        self.assertEqual(len(world["zoning"]["zones"]), 1)
        self.assertEqual(world["zoning"]["zones"][0]["coreClaims"], [])
        self.assertEqual(world["routing"]["routes"], [])

    def test_core_support_road_and_block_tampering_is_rejected(self):
        for mutation in ("core", "support", "road", "block"):
            world = copy.deepcopy(self.world)
            zone = next(z for z in world["zoning"]["zones"] if z["supportingMembers"])
            if mutation == "core":
                zone["coreEntityIds"].pop()
            elif mutation == "support":
                zone["supportingMembers"][0]["coreEdgeIds"] = ["made-up"]
            elif mutation == "road":
                world["zoning"]["mainRoads"][0]["width"] = 999
            else:
                world["parcels"][0]["blockId"] = "missing"
            with (
                self.subTest(mutation=mutation),
                self.assertRaisesRegex(ValueError, "zoning|neighborhood"),
            ):
                validate_world(world, self.scene, self.graph)
        malformed = copy.deepcopy(self.world)
        malformed["zoning"]["blocks"] = None
        with self.assertRaisesRegex(ValueError, "previous world block"):
            generate_world(self.scene, self.graph, previous=malformed, **self.options)


if __name__ == "__main__":
    unittest.main()
