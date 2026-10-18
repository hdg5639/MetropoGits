import copy
import math
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.block_orientation import (
    BlockMap,
    cage,
    cross,
    plan_blocks,
    presentation,
    update_parcels,
)
from metropogits.frontage_parcels import area, corners, inside, transform
from metropogits.occupied_ground import occupied_ground


def fixture():
    outer = corners(dict(x=0, z=0, width=40, depth=40))
    inner = corners(dict(x=14, z=14, width=12, depth=12))
    triangles = cage(outer, inner, [20, 20], math.pi / 6, [1, 0])
    return dict(blocks=[dict(bounds=[0, 0, 40, 40], triangles=triangles)])


class BlockOrientationTests(unittest.TestCase):
    def test_planner_moves_entrances_with_whole_envelopes_and_is_stable(self):
        scene = dict(
            districts=[dict(id="d", parentId=None, x=0, z=0, width=40, depth=40)],
            buildings=[
                dict(entityId=str(i), districtId="d", x=x, z=17, width=6, depth=6)
                for i, x in enumerate((10, 24))
            ],
        )
        models = {}
        for b in scene["buildings"]:
            poly = corners(b)
            # Deliberately tiny visible roof must not define the collision envelope.
            models[b["entityId"]] = dict(
                footprint=poly,
                parts=[
                    dict(footprint=corners(dict(x=b["x"] + 2, z=19, width=2, depth=2)))
                ],
                pinnedDoors=[poly[0]],
                frontageEdge=poly[2:],
                center=[b["x"] + 3, 20],
                frontagePoint=[b["x"] + 3, 23],
                entrance=poly[0],
                angle=0,
                frontageGap=1,
            )
        routing = dict(
            parcelPlan=dict(buildings=models, changedFootprintIds=[]),
            diagonalPlan=dict(chains=[dict(physical=[[0, 0], [40, 14]])]),
            routes=[dict(id="r", segmentIds=["s"], source="0", target="1")],
        )
        paths = {"s": [[10, 17], [24, 17]]}
        frozen = copy.deepcopy((scene, routing))
        result = plan_blocks(scene, routing, [], paths)
        self.assertEqual(len(result["blocks"]), 1)
        with patch("metropogits.block_orientation.MAX_PLAN_CHECKS", 0):
            with self.assertRaisesRegex(ValueError, "planning work limit"):
                plan_blocks(scene, routing, [], paths)
        self.assertEqual((scene, routing), frozen)
        scene["buildings"].reverse()
        self.assertEqual(result, plan_blocks(scene, routing, [], paths))
        scene["districts"].append(
            dict(id="far", parentId=None, x=1000, z=1000, width=20, depth=20)
        )
        self.assertEqual(result, plan_blocks(scene, routing, [], paths))
        routing["blockPlan"] = result
        moved = update_parcels(scene, routing)
        mapper = BlockMap(result)
        for key, p in moved["buildings"].items():
            self.assertTrue(inside(p["footprint"], scene["districts"][:1]))
            self.assertAlmostEqual(area(p["footprint"]), 36)
            self.assertLess(
                math.dist(p["entrance"], mapper.point(models[key]["entrance"])), 1e-8
            )
        physical = mapper.line(*paths["s"])
        self.assertLessEqual(
            sum(math.dist(a, b) for a, b in zip(physical, physical[1:])), 28
        )
        # Near-edge envelopes must remain in-owner even if the roof is tiny.
        scene["buildings"][0]["x"] = 33
        models["1"]["footprint"] = corners(scene["buildings"][0])
        models["1"]["pinnedDoors"] = []
        result = plan_blocks(scene, routing, [], paths)
        routing["blockPlan"] = result
        for p in update_parcels(scene, routing)["buildings"].values():
            self.assertTrue(inside(p["footprint"], scene["districts"][:1]))

    def test_fixed_boundary_rigid_interior_and_positive_partition(self):
        plan = fixture()
        mapper = BlockMap(plan)
        for p in (
            [0, 0],
            [40, 40],
            [0, 17],
            [40, 23],
            [11, 0],
            [22, 40],
            [-1, 10],
            [50, 10],
        ):
            self.assertLess(math.dist(mapper.point(p), p), 1e-8)
        for p in ([14, 14], [26, 26], [20, 20], [22, 17]):
            self.assertLess(
                math.dist(
                    mapper.point(p), transform([p], [20, 20], math.pi / 6, [1, 0])[0]
                ),
                1e-8,
            )
        for t in plan["blocks"][0]["triangles"]:
            self.assertGreater(cross(*t["target"]), 0)
        self.assertAlmostEqual(
            sum(area(t["target"]) for t in plan["blocks"][0]["triangles"]), 1600
        )
        self.assertIsNone(
            cage(
                corners(dict(x=0, z=0, width=10, depth=10)),
                corners(dict(x=1, z=1, width=8, depth=8)),
                [5, 5],
                math.pi / 4,
                [0, 0],
            )
        )

    def test_surface_partition_preserves_area_and_connected_paths(self):
        mapper = BlockMap(fixture())
        poly = corners(dict(x=-5, z=-5, width=50, depth=50))
        pieces = mapper.polygon(poly)
        self.assertAlmostEqual(sum(area(p) for p in pieces), 2500)
        self.assertTrue(all(len(p) == 4 for p in pieces))
        path = mapper.line([-5, 20], [45, 20])
        self.assertGreater(len(path), 4)
        self.assertEqual(path[0], [-5, 20])
        self.assertEqual(path[-1], [45, 20])
        # Adjacent source segments share exactly one mapped endpoint, including doors.
        door = [16, 20]
        self.assertLess(
            math.dist(mapper.line([-5, 20], door)[-1], mapper.line(door, [45, 20])[0]),
            1e-8,
        )

    def test_presentation_is_derived_and_resource_limited(self):
        routing = dict(blockPlan=fixture())
        surfaces = [dict(points=corners(dict(x=0, z=0, width=40, depth=40)))]
        pavement = dict(segments={"s": copy.deepcopy(surfaces)})
        curves = dict(
            segments={"s": [[-5, 20], [45, 20]]},
            paintSegments={"s": [dict(start=[0, 20], end=[40, 20])]},
        )
        frozen = copy.deepcopy((routing, surfaces, pavement, curves))
        result = presentation(routing, surfaces, pavement, curves)
        self.assertEqual(result, presentation(routing, surfaces, pavement, curves))
        self.assertEqual(frozen, (routing, surfaces, pavement, curves))
        self.assertEqual(set(result[2]["segments"]), {"s"})
        with patch("metropogits.block_orientation.MAX_PIECES", 1):
            with self.assertRaisesRegex(ValueError, "limit"):
                presentation(routing, surfaces, pavement, curves)

    def test_missing_frontage_and_empty_input_degrade(self):
        s = dict(districts=[], buildings=[])
        r = dict(diagonalPlan=dict(chains=[]), routes=[])
        self.assertEqual(plan_blocks(s, r, [], {})["blocks"], [])
        self.assertEqual(BlockMap({}).line([0, 0], [2, 2]), [[0, 0], [2, 2]])

    def test_pipeline_contract_and_real_packaging(self):
        from scripts.canonical_json import loads_strict_json
        from metropogits.layout import generate_city
        from scripts.street_grid import compare
        from scripts.road_consolidation import package

        graph = loads_strict_json(
            (
                Path(__file__).parent / "fixtures/ucg/valid/spring-minimal.json"
            ).read_text(encoding="utf8")
        )
        scene = generate_city(graph)
        frozen = copy.deepcopy((scene, graph))
        before, routing, report = compare(scene, graph, aligned=True, blocks=True)
        result = package(scene, graph, routing, report)
        self.assertEqual(result, package(scene, graph, routing, report))
        self.assertEqual((scene, graph), frozen)
        self.assertIn("block-plan.json", result)
        self.assertIn("occupied-ground.json", result)
        self.assertIn(b"occupied-ground/0.1", result["assets/viewer-data.js"])
        self.assertIn(b"occupied-ground", result["preview.svg"])
        self.assertEqual(
            [r["edgeIds"] for r in before["routes"]],
            [r["edgeIds"] for r in routing["routes"]],
        )
        with self.assertRaisesRegex(ValueError, "aligned"):
            compare(scene, graph, blocks=True)


class OccupiedGroundTests(unittest.TestCase):
    def scene(self):
        return dict(
            districts=[dict(id="d", parentId=None, x=0, z=0, width=100, depth=100)],
            buildings=[
                dict(entityId=str(i), districtId="d", x=x, z=10, width=6, depth=6)
                for i, x in enumerate((10, 17, 80))
            ],
        )

    def test_ground_supports_do_not_fill_empty_reservations(self):
        scene = self.scene()
        frozen = copy.deepcopy(scene)
        result = occupied_ground(scene, {})
        self.assertEqual(scene, frozen)
        self.assertEqual(len(result["pads"]), 2)
        self.assertLess(result["padAreaUpperBound"], 300)
        self.assertEqual(result["allocatedRootArea"], 10000)
        self.assertEqual(
            sorted(k for p in result["pads"] for k in p["memberEntityIds"]),
            ["0", "1", "2"],
        )
        for b in scene["buildings"]:
            pad = next(
                p for p in result["pads"] if b["entityId"] in p["memberEntityIds"]
            )
            from metropogits.block_orientation import clip

            self.assertAlmostEqual(
                sum(area(clip(corners(b), p)) for p in pad["polygons"]), 36
            )
        self.assertTrue(
            all(
                inside(p, scene["districts"])
                for pad in result["pads"]
                for p in pad["polygons"]
            )
        )

    def test_rotated_support_concave_ownership_order_and_local_stability(self):
        scene = self.scene()
        poly = transform(corners(scene["buildings"][0]), [13, 13], math.pi / 4, [0, 0])
        parcels = {"0": dict(footprint=poly)}
        result = occupied_ground(scene, parcels)
        scene["buildings"].reverse()
        self.assertEqual(result, occupied_ground(scene, parcels))
        scene["districts"].append(
            dict(id="other", parentId=None, x=1000, z=1000, width=100, depth=100)
        )
        scene["buildings"].append(
            dict(
                scene["buildings"][0],
                entityId="far",
                districtId="other",
                x=1010,
                z=1010,
            )
        )
        self.assertEqual(
            result["pads"],
            [
                p
                for p in occupied_ground(scene, parcels)["pads"]
                if p["districtId"] == "d"
            ],
        )
        # A disconnected owner must retain its gap, even when merging pads.
        scene = self.scene()
        scene["districts"][0]["footprint"] = [
            dict(x=0, z=0, width=16, depth=100),
            dict(x=17, z=0, width=83, depth=100),
        ]
        self.assertTrue(
            all(
                inside(p, scene["districts"][0]["footprint"])
                for pad in occupied_ground(scene, {})["pads"]
                for p in pad["polygons"]
            )
        )

    def test_resource_limits(self):
        for limit in ("MAX_CLIP_CHECKS", "MAX_MERGE_CHECKS"):
            with patch("metropogits.occupied_ground." + limit, 0):
                with self.assertRaisesRegex(ValueError, "limit"):
                    occupied_ground(self.scene(), {})
