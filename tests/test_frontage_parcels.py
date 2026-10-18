import copy
import math
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from metropogits.frontage_parcels import (
    area,
    corners,
    inside,
    nearest,
    plan_parcels,
    transform,
)
from metropogits.street_diagonals import ribbon


def fixture():
    building = dict(
        entityId="file",
        districtId="district",
        x=16,
        z=5,
        width=6,
        depth=6,
        height=10,
        archetype="SERVICE_OFFICE",
    )
    scene = dict(
        buildings=[building],
        districts=[dict(id="district", x=0, z=0, width=50, depth=50)],
    )
    routing = dict(
        routes=[],
        segments=[],
        streetGrid=dict(
            segments=[
                dict(id="a", start=[0, 0], end=[30, 0], width=2),
                dict(id="b", start=[30, 0], end=[30, 30], width=2),
            ]
        ),
        diagonalPlan=dict(
            chains=[
                dict(
                    path=[[0, 0], [30, 0], [30, 30]],
                    physical=[[0, 0], [15, 15], [30, 30]],
                    beforeLength=60,
                    widthStations=[0, 1],
                    widths=[2, 2],
                )
            ]
        ),
    )
    return scene, routing


def plan(scene, routing):
    with ExitStack() as stack:
        stack.enter_context(
            patch("metropogits.frontage_parcels.derive_road_hierarchy", return_value={})
        )
        stack.enter_context(
            patch("metropogits.frontage_parcels.street_rectangles", return_value=[])
        )
        stack.enter_context(
            patch("metropogits.frontage_parcels.demand_pavement", return_value={})
        )
        stack.enter_context(
            patch(
                "metropogits.frontage_parcels.curved_presentation",
                return_value=(
                    [dict(points=ribbon([0, 0], [30, 30], 2))],
                    dict(segments={}),
                    None,
                ),
            )
        )
        return plan_parcels(scene, routing)


class FrontageParcelTests(unittest.TestCase):
    def test_whole_building_faces_diagonal_and_moves_into_frontage(self):
        scene, routing = fixture()
        original = copy.deepcopy((scene, routing))
        p = plan(scene, routing)["buildings"]["file"]
        self.assertAlmostEqual(p["angle"], math.pi / 4)
        self.assertGreater(p["displacement"], 1)
        self.assertLessEqual(p["displacement"], 7)
        self.assertAlmostEqual(area(p["footprint"]), 36)
        self.assertAlmostEqual(p["frontageGap"], 1)
        self.assertTrue(inside(p["footprint"], scene["districts"]))
        q = nearest(p["center"], [0, 0], [30, 30])
        self.assertGreater(
            sum((q[i] - p["center"][i]) * p["facing"][i] for i in (0, 1)), 0
        )
        for part in p["parts"]:
            expected = transform(corners(part), p["pivot"], p["angle"], p["shift"])
            self.assertEqual(part["footprint"], expected)
        self.assertEqual((scene, routing), original)

    def test_existing_door_vetoes_disconnection(self):
        scene, routing = fixture()
        routing["routes"] = [
            dict(source="file", target="other", path=[[16, 8], [0, 0]])
        ]
        self.assertEqual(plan(scene, routing)["buildings"], {})

    def test_collision_and_concave_owner_fail_closed(self):
        scene, routing = fixture()
        scene["buildings"].append(
            dict(scene["buildings"][0], entityId="neighbor", x=10, z=10)
        )
        p = plan(scene, routing)
        from metropogits.street_diagonals import overlap

        footprints = [
            p["buildings"].get(b["entityId"], {}).get("footprint", corners(b))
            for b in scene["buildings"]
        ]
        self.assertFalse(overlap(*footprints))
        # All four vertices lie in the arms, but a concave notch cuts the interior.
        self.assertFalse(
            inside(
                [[0, 0], [6, 0], [6, 6], [0, 6]],
                [
                    dict(x=0, z=0, width=6, depth=1),
                    dict(x=0, z=1, width=1, depth=5),
                    dict(x=5, z=1, width=1, depth=5),
                ],
            )
        )

    def test_order_reversal_repeat_and_unrelated_district_stability(self):
        scene, routing = fixture()
        baseline = plan(scene, routing)
        routing["streetGrid"]["segments"].reverse()
        for s in routing["streetGrid"]["segments"]:
            s["start"], s["end"] = s["end"], s["start"]
        self.assertEqual(baseline, plan(scene, routing))
        scene["districts"].append(dict(id="far", x=1000, z=1000, width=30, depth=30))
        scene["buildings"].append(
            dict(
                scene["buildings"][0],
                entityId="far-file",
                districtId="far",
                x=1001,
                z=1001,
            )
        )
        self.assertEqual(baseline["buildings"], plan(scene, routing)["buildings"])

    def test_resource_limit_is_explicit(self):
        with patch("metropogits.frontage_parcels.MAX_CHECKS", 0):
            with self.assertRaisesRegex(ValueError, "limit"):
                plan(*fixture())
        with patch("metropogits.frontage_parcels.MAX_INDEX_ENTRIES", 0):
            with self.assertRaisesRegex(ValueError, "spatial index limit"):
                plan(*fixture())

    def test_rectangular_envelope_keeps_size_and_height_when_rotated(self):
        scene, routing = fixture()
        building = scene["buildings"][0]
        building.update(width=4, depth=8, height=0.5)
        p = plan(scene, routing)["buildings"]["file"]
        self.assertAlmostEqual(p["angle"], math.pi / 4)
        self.assertAlmostEqual(area(p["footprint"]), 32)
        self.assertAlmostEqual(math.dist(*p["frontageEdge"]), 4)
        self.assertTrue(all(part["y"] + part["height"] <= 0.5 + 1e-8 for part in p["parts"]))

    def test_real_pipeline_packaging_preserves_source_and_dimensions(self):
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
        _, routing, report = compare(scene, graph, aligned=True, parcels=True)
        output = package(scene, graph, routing, report)
        self.assertEqual(output, package(scene, graph, routing, report))
        self.assertEqual(frozen, (scene, graph))
        self.assertIn(b"street-parcels/0.1", output["assets/viewer-data.js"])
        self.assertIn("parcel-plan.json", output)
