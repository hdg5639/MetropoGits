"""Sparse cross-streets reclaim vacant supply, not source buildings."""

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
from metropogits.street_diagonals import overlap
from metropogits.world.geometry import nearest, rectangle, ribbon
from metropogits.world.infrastructure import atomic_streets
from metropogits.world.permeability import MIN_SPACING, WIDTH, reserve_links
from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world
from metropogits.world.seams import stitch_unused_streets
from metropogits.world.adaptive import retained_addresses
from metropogits.world.planning import populate, slots
from test_world_neighborhoods import fixture


def plan(curved=False, dense=False, short=False):
    xs = list(range(0, 241, 20))
    rows = [
        [[x, z + (12 * math.sin(x / 240 * math.pi) if curved else 0)] for x in xs]
        for z in (0, 30, 60)
    ]
    roads = [
        dict(start=a, end=b, width=3, access=False)
        for row in rows
        for a, b in zip(row, row[1:])
    ]
    roads += [
        dict(start=rows[0][i], end=rows[-1][i], width=4, access=False) for i in (0, -1)
    ]
    if short:
        roads += [
            dict(start=[x, 0], end=[x, 72], width=2, access=False)
            for x in range(10, 240, 10)
        ]
    slots = (
        [
            dict(
                id=f"s{i}",
                polygon=rectangle([10 + i * 6, 15], 0, 5.9 if dense else 2, 20),
            )
            for i in range(39)
        ]
        if dense
        else []
    )
    # Supply remote vacant lots as well, ensuring reclamation has real slack.
    slots += [
        dict(id=f"reserve{i}", polygon=rectangle([10 + i * 5, -15], 0, 3, 3))
        for i in range(35)
    ]
    return (
        {"zone": (slots, roads, 0, None)},
        [],
        [],
        [[-10, -22], [250, -22], [250, 88], [-10, 88]],
        dict(id="pattern", seed="0123456789abcdef"),
        {"zone": 24},
    )


class PermeabilityTests(unittest.TestCase):
    def test_shortcuts_do_not_make_zero_dependency_building_frontages_disposable(self):
        streets = [
            dict(id=str(i), start=a, end=b, width=3, access=False)
            for i, (a, b) in enumerate(
                (
                    ([0, 0], [30, 0]),
                    ([0, 4], [30, 4]),
                    ([0, 0], [0, 4]),
                    ([30, 0], [30, 4]),
                )
            )
        ]
        parcels = [dict(entrance=[15, -3], streetPoint=[15, 0])]
        ordinary, _ = stitch_unused_streets(
            streets, streets[1:], dict(segments=[]), parcels
        )
        self.assertNotIn("0", {s["id"] for s in ordinary})
        preserved, _ = stitch_unused_streets(
            streets, streets[1:], dict(segments=[]), parcels, preserve_frontages=True
        )
        self.assertIn("0", {s["id"] for s in preserved})

    def test_curved_rows_gain_two_ended_shortcuts_without_source_mutation(self):
        args = plan(curved=True)
        before = copy.deepcopy(args)
        plans, roads, p = reserve_links(*args)
        self.assertEqual(args, before)
        self.assertEqual(len(roads), 1)
        self.assertIsNone(p["permeability"]["budgetExhausted"])
        self.assertEqual(plans, args[0])
        physical = atomic_streets(args[0]["zone"][1] + roads)
        for r in roads:
            self.assertGreater(
                r["previousDistance"], math.dist(r["start"], r["end"]) * 1.9
            )
            self.assertEqual(r["width"], WIDTH)
            for at in (r["start"], r["end"]):
                self.assertGreaterEqual(
                    sum(at in (s["start"], s["end"]) for s in physical), 3
                )
        reverse = copy.deepcopy(args)
        reverse[0]["zone"][1].reverse()
        reverse[0]["zone"][0].reverse()
        other = reserve_links(*reverse)
        self.assertEqual(other[1:], (roads, p))

    def test_dense_rows_reserve_a_gap_before_file_assignment(self):
        args = plan(dense=True)
        result, roads, p = reserve_links(*args)
        self.assertTrue(roads)
        # Pin candidates to the occupied first band; no gap-only fallback.
        args[0]["zone"][1][:] = [
            r for r in args[0]["zone"][1] if max(r["start"][1], r["end"][1]) <= 30
        ]
        args[0]["zone"][0][:] = [
            s for s in args[0]["zone"][0] if s["id"].startswith("s")
        ]
        args[0]["zone"][1].extend(
            dict(start=[x, 0], end=[x, 30], width=3, access=False) for x in (0, 240)
        )
        args[3][:] = [[-3, -3], [243, -3], [243, 33], [-3, 33]]
        result, roads, p = reserve_links(*args)
        self.assertTrue(p["permeability"]["reclaimedSlotIds"])
        self.assertGreaterEqual(len(result["zone"][0]), 24)
        for r in roads:
            self.assertTrue(
                all(
                    not overlap(ribbon(r["start"], r["end"], WIDTH + 0.6), s["polygon"])
                    for s in result["zone"][0]
                )
            )

    def test_short_existing_routes_and_protected_terrain_suppress_cuts(self):
        self.assertEqual(reserve_links(*plan(short=True))[1], [])
        args = plan()
        terrain = dict(
            features=[dict(noBuildPolygon=[[-10, 4], [250, 4], [250, 56], [-10, 56]])]
        )
        # Avoid invoking general terrain clipping on this deliberately minimal fixture.
        with patch("metropogits.world.terrain.adapt_roads", side_effect=lambda r, t: r):
            self.assertEqual(reserve_links(*args, terrain=terrain)[1], [])

    def test_capacity_frequency_and_work_are_bounded(self):
        args = plan(dense=True)
        args[-1]["zone"] = len(args[0]["zone"][0])
        result, roads, p = reserve_links(*args)
        self.assertFalse(p["permeability"]["reclaimedSlotIds"])
        self.assertEqual(len(result["zone"][0]), len(args[0]["zone"][0]))
        args = plan()
        args[-1]["zone"] = 250
        _, roads, p = reserve_links(*args)
        self.assertLessEqual(len(roads), 3)
        self.assertTrue(
            all(
                math.dist(a["center"], b["center"]) >= MIN_SPACING
                for i, a in enumerate(roads)
                for b in roads[i + 1 :]
            )
        )
        for key in (
            "MAX_ROADS",
            "MAX_INDEX",
            "MAX_CHECKS",
            "MAX_CANDIDATES",
            "MAX_STATES",
        ):
            with (
                self.subTest(key=key),
                patch("metropogits.world.permeability." + key, 0),
            ):
                result, roads, p = reserve_links(*plan())
                self.assertEqual(roads, [])
                self.assertTrue(p["permeability"]["budgetExhausted"])


class PorousWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene, cls.graph = fixture(Path(directory))
        cls.options = dict(
            zoning="neighborhoods",
            pattern_scale="adaptive",
            planning="varied",
            outline="varied",
            seed="porous-test",
            street_policy="porous",
        )
        cls.world = generate_world(cls.scene, cls.graph, **cls.options)

    def test_world_schema_truth_determinism_and_legacy_hint_boundary(self):
        world = self.world
        validate_world(world, self.scene, self.graph)
        self.assertEqual(world, generate_world(self.scene, self.graph, **self.options))
        schema = json.loads(
            Path("schemas/world-0.1.schema.json").read_text(encoding="utf8")
        )
        Draft202012Validator(schema).validate(world)
        old = generate_world(
            self.scene, self.graph, **dict(self.options, street_policy="permeable")
        )
        hinted = generate_world(self.scene, self.graph, previous=old, **self.options)
        self.assertEqual(hinted["parcels"], world["parcels"])
        self.assertTrue(
            any(
                "incompatible previous world" in d["reason"]
                for d in hinted["diagnostics"]
            )
        )

        def identity(w):
            return {
                r["id"]: (r["source"], r["target"], r["edgeIds"])
                for r in w["routing"]["routes"]
            }

        self.assertEqual(identity(world), identity(old))

    def test_forged_reservations_do_not_pass_independent_validation(self):
        bad = copy.deepcopy(self.world)
        bad["zoning"]["districtPatterns"][0]["permeability"]["reclaimedSlotIds"].append(
            "fabricated"
        )
        with self.assertRaisesRegex(ValueError, "pattern"):
            validate_world(bad, self.scene, self.graph)

    def test_reclaiming_one_occupied_candidate_moves_only_its_original_file(self):
        candidates = slots(
            [[-100, -100], [100, -100], [100, 100], [-100, 100]], "address-test"
        )[0]
        population = self.scene["buildings"]
        paths = {
            e["id"]: e["path"] for e in self.graph["entities"] if e["kind"] == "FILE"
        }
        original = populate(population, candidates, "parent", paths, "address-test")
        chosen = original[0]["slotId"]
        remaining = [s for s in candidates if s["id"] != chosen]
        preferred = retained_addresses(
            population, candidates, remaining, "parent", paths, "address-test", {}
        )
        updated = populate(
            population, remaining, "parent", paths, "address-test", preferred
        )
        self.assertEqual(
            sum(a["slotId"] != b["slotId"] for a, b in zip(original, updated)), 1
        )

    def test_hinted_small_edit_preserves_existing_frames_and_nature(self):
        options = dict(self.options, terrain="river-landscape")
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            old = generate_world(scene, graph, **options)
            (repo / "zz_extra.rs").write_text("fn generic() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/neighborhoods")
            scene = generate_city(graph)
            new = generate_world(scene, graph, previous=old, **options)
        self.assertEqual(old["terrain"], new["terrain"])
        frames = {p["entityId"]: p for p in new["parcels"]}
        for p in old["parcels"]:
            self.assertEqual(p, frames[p["entityId"]])
        validate_world(new, scene, graph)

    def test_reserved_corridor_requires_real_full_width_pavement(self):
        bad = copy.deepcopy(self.world)
        link = bad["zoning"]["districtPatterns"][0]["permeability"]["corridors"][0]
        affected = []
        for s in bad["streets"]:
            if all(
                math.dist(p, nearest(p, link["start"], link["end"])) < 0.001
                for p in (s["start"], s["end"])
            ):
                affected.append(s)
                s["width"] = 0.1
        self.assertTrue(affected)
        with self.assertRaisesRegex(ValueError, "backbone|reserved"):
            validate_world(bad, self.scene, self.graph)


if __name__ == "__main__":
    unittest.main()
