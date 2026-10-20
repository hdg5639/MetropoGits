"""Preserve real street topology when replacing a neighborhood with campus."""

import copy
import unittest
from metropogits.world.campus import retains_external_connections


def road(a, b, width=3.5):
    return dict(start=a, end=b, width=width, access=False)


class CampusConnectionTests(unittest.TestCase):
    def test_campus_cannot_leave_a_retained_shortcut_as_an_island(self):
        # Both shortcut ends were on local streets replaced by campus walks.
        external = [road([0, 0], [0, 30]), road([12, 10], [12, 20], 1.8)]
        original = [road([0, 10], [12, 10]), road([0, 20], [12, 20])]
        replacement = [
            road([0, 4], [6, 4]),
            road([6, 4], [6, 26]),
            road([6, 26], [0, 26]),
        ]
        before = copy.deepcopy((external, original, replacement))
        self.assertFalse(retains_external_connections(original, replacement, external))
        self.assertEqual(before, (external, original, replacement))
        # A genuine replacement connection preserves existing accessibility.
        self.assertTrue(
            retains_external_connections(
                original, replacement + [road([6, 10], [12, 10])], external
            )
        )

    def test_distinct_existing_components_are_not_invented_as_connected(self):
        roads = [road([0, 0], [0, 10]), road([30, 0], [30, 10])]
        self.assertTrue(retains_external_connections([], [], roads))
        # Preserving extra connections is allowed; inventing source edges is not
        # this helper's job. It only certifies existing physical infrastructure.
        self.assertTrue(
            retains_external_connections([], [road([0, 5], [30, 5])], roads)
        )
