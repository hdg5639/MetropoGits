"""Do not let independent bridge ramps create inconsistent shared nodes."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_world_neighborhoods import fixture
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.generator import generate_world
from metropogits.world.river_landscape import _bridge_conflict, _planned_crossing
from metropogits.world.rivers import blocks_ground_connection
from metropogits.world.validation import validate_world


def bridge(path):
    return dict(id="bridge", path=path, width=4.5)


class BridgeJunctionTests(unittest.TestCase):
    def test_ground_alley_can_meet_bank_but_not_elevated_deck_or_ramp(self):
        c = dict(
            bridge([[0, 0], [10, 0], [20, 0], [30, 0]]),
            heights=[0.08, 0.95, 0.95, 0.08],
        )
        terrain = dict(crossings=[c])
        with patch("metropogits.world.elevation.surface") as field:
            field.return_value.height.return_value = 0
            self.assertFalse(blocks_ground_connection([0, -10], [0, 0], terrain))
            self.assertTrue(blocks_ground_connection([5, -10], [5, 0], terrain))
            self.assertTrue(blocks_ground_connection([15, -10], [15, 10], terrain))
            self.assertTrue(blocks_ground_connection([3, 0], [8, 0], terrain))
            self.assertFalse(blocks_ground_connection([50, -10], [50, 10], terrain))

    def test_entire_ramps_are_checked_not_only_water_decks(self):
        first = bridge([[0, 0], [10, 0], [20, 0], [30, 0]])
        crossing = bridge([[5, -10], [5, 2], [5, 6], [5, 12]])
        separated = bridge([[50, -10], [50, 2], [50, 6], [50, 12]])
        self.assertTrue(_bridge_conflict(crossing, [first]))
        self.assertFalse(_bridge_conflict(separated, [first]))

    def test_bounded_alternative_never_drops_a_blocked_required_crossing(self):
        existing = bridge([[0, 0], [10, 0], [20, 0], [30, 0]])
        blocked = bridge([[5, -10], [5, 2], [5, 6], [5, 12]])
        safe = bridge([[50, -10], [50, 2], [50, 6], [50, 12]])
        envelope = [[-100, -100], [100, -100], [100, 100], [-100, 100]]
        original = copy.deepcopy(existing)
        with patch(
            "metropogits.world.river_landscape._crossing", side_effect=[blocked, safe]
        ) as make:
            result = _planned_crossing(
                [0, 0], [100, 0], 0.5, [], "stable", envelope, [existing]
            )
        self.assertEqual(result, safe)
        self.assertEqual(make.call_count, 2)
        self.assertEqual(make.call_args_list[0].args[2], [50, 0])
        self.assertEqual(make.call_args_list[1].args[2], [35, 0])
        self.assertEqual(existing, original)
        with patch(
            "metropogits.world.river_landscape._crossing", return_value=None
        ) as make:
            self.assertIsNone(
                _planned_crossing(
                    [0, 0], [100, 0], 0.5, [], "stable", envelope, [existing]
                )
            )
            self.assertEqual(make.call_count, 1)
        with patch(
            "metropogits.world.river_landscape._crossing", return_value=blocked
        ) as make:
            with self.assertRaisesRegex(ValueError, "placement budget"):
                _planned_crossing(
                    [0, 0], [100, 0], 0.5, [], "stable", envelope, [existing]
                )
            self.assertEqual(make.call_count, 5)

    def test_previously_rejected_seed_and_hinted_growth_are_complete_and_repeatable(
        self,
    ):
        options = dict(
            zoning="neighborhoods",
            pattern_scale="adaptive",
            street_policy="porous",
            planning="varied",
            outline="varied",
            terrain="river-landscape",
            seed="hierarchy-test",
            street_hierarchy=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            old = generate_world(scene, graph, **options)
            result = validate_world(old, scene, graph)
            self.assertEqual(result["accessibleBuildings"], 48)
            self.assertEqual(old, generate_world(scene, graph, **options))
            self.assertEqual(len(old["terrain"]["crossings"]), 3)
            self.assertTrue(
                all(
                    not _bridge_conflict(c, old["terrain"]["crossings"][:i])
                    for i, c in enumerate(old["terrain"]["crossings"])
                )
            )
            (repo / "zz_extra.rs").write_text("fn generic() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/neighborhoods")
            scene = generate_city(graph)
            grown = generate_world(scene, graph, previous=old, **options)
            self.assertEqual(
                validate_world(grown, scene, graph)["accessibleBuildings"], 49
            )
        self.assertEqual(old["terrain"], grown["terrain"])
        frames = {p["entityId"]: p for p in grown["parcels"]}
        self.assertTrue(all(frames[p["entityId"]] == p for p in old["parcels"]))


if __name__ == "__main__":
    unittest.main()
