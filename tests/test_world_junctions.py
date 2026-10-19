import copy
import heapq
import math
import unittest
from collections import defaultdict
from unittest.mock import patch

from metropogits.world.junctions import (
    check_trip_budgets, consolidate_junctions, path_length, protect, trip_limit,
)


def road(key, a, b, access=False):
    return dict(id=key, start=a, end=b, width=3, access=access)


def trip(key, path):
    return dict(id=key, source="source:"+key, target="target:"+key, kind="DEPENDENCY_ROAD",
                edgeIds=["actual:"+key], networkIds=["network"], path=path)


def shortest(streets, route):
    # Independent full endpoint search, not the optimizer's replacement witness.
    adjacency = defaultdict(list)
    for s in streets:
        a, b = tuple(s["start"]), tuple(s["end"])
        adjacency[a].append(b)
        adjacency[b].append(a)
    start, end = tuple(route["path"][0]), tuple(route["path"][-1])
    costs, prior, queue = {start: 0}, {start: None}, [(0, start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost != costs[node]:
            continue
        if node == end:
            nodes = []
            while node is not None:
                nodes.append(list(node))
                node = prior[node]
            return dict(route, path=list(reversed(nodes)))
        for other in adjacency[node]:
            value = cost + math.dist(node, other)
            if value < costs.get(other, math.inf):
                costs[other], prior[other] = value, node
                heapq.heappush(queue, (value, other))
    raise AssertionError("lost source-target path")


class SharedJunctionTests(unittest.TestCase):
    def setUp(self):
        self.streets = [road("shortcut", [0, 0], [30, 0]),
                        road("main", [0, 4], [30, 4]),
                        road("left", [0, 0], [0, 4]), road("right", [30, 0], [30, 4]),
                        road("source-door", [-4, 0], [0, 0], True),
                        road("target-door", [30, 0], [34, 0], True)]
        self.routing = dict(routes=[trip("a-b", [[-4, 0], [0, 0], [30, 0], [34, 0]])])

    def test_used_shortcut_really_merges_into_existing_junctions(self):
        original = copy.deepcopy((self.streets, self.routing))
        kept, note = consolidate_junctions(self.streets, [self.streets[1]], [], self.routing)
        self.assertEqual(note["removedStreetIds"], ["shortcut"])
        self.assertEqual(note["affectedTripIds"], ["a-b"])
        route = shortest(kept, self.routing["routes"][0])
        self.assertIn([0, 4], route["path"])
        self.assertIn([30, 4], route["path"])
        check_trip_budgets(self.routing, dict(routes=[route]))
        self.assertEqual(original, (self.streets, self.routing))
        self.assertEqual(consolidate_junctions(list(reversed(self.streets)),
                                             [self.streets[1]], [], self.routing), (kept, note))

    def test_parent_curve_and_actual_tangent_frontage_never_disappear(self):
        parcel = dict(streetPoint=[15, 0], angle=0, entrance=[15, -4])
        _, frontage = protect(self.streets, [self.streets[1]], [parcel])
        self.assertIn("shortcut", frontage)
        kept, _ = consolidate_junctions(self.streets, [self.streets[1]], [parcel], self.routing)
        self.assertIn(self.streets[0], kept)
        self.assertIn(self.streets[1], kept)
        self.assertTrue(all(s in kept for s in self.streets if s["access"]))

    def test_existing_connectivity_is_not_permission_for_a_large_detour(self):
        streets = [road("shortcut", [0, 0], [30, 0]), road("main", [0, 30], [30, 30]),
                   road("left", [0, 0], [0, 30]), road("right", [30, 0], [30, 30])]
        kept, note = consolidate_junctions(streets, [streets[1]], [], dict(routes=[
            trip("a-b", [[0, 0], [30, 0]])]))
        self.assertEqual(len(kept), len(streets))
        self.assertEqual(note["removedStreetIds"], [])

    def test_cumulative_budget_is_relative_to_original_not_last_detour(self):
        streets = [road("first", [0, 0], [20, 0]), road("second", [20, 0], [40, 0]),
                   road("main-a", [0, 8], [20, 8]), road("main-b", [20, -8], [40, -8]),
                   road("a", [0, 0], [0, 8]), road("b", [20, 0], [20, 8]),
                   road("c", [20, 0], [20, -8]), road("d", [40, 0], [40, -8]),
                   road("source", [-4, 0], [0, 0], True), road("target", [40, 0], [44, 0], True)]
        before = trip("across", [[-4, 0], [0, 0], [20, 0], [40, 0], [44, 0]])
        kept, note = consolidate_junctions(streets, streets[2:4], [], dict(routes=[before]))
        self.assertTrue(note["removedStreetIds"])
        self.assertFalse({"first", "second"}.issubset(note["removedStreetIds"]))
        after = shortest(kept, before)
        self.assertLessEqual(path_length(after["path"]), trip_limit(path_length(before["path"])))
        check_trip_budgets(dict(routes=[before]), dict(routes=[after]))

    def test_trip_identity_and_length_guard_are_independent(self):
        old = self.routing
        changed = copy.deepcopy(old)
        changed["routes"][0]["target"] = "not-the-target"
        with self.assertRaisesRegex(ValueError, "identity"):
            check_trip_budgets(old, changed)
        changed = copy.deepcopy(old)
        changed["routes"][0]["path"].insert(1, [500, 500])
        with self.assertRaisesRegex(ValueError, "budget"):
            check_trip_budgets(old, changed)

    def test_exhausted_work_retains_certified_geometry(self):
        for name in ("MAX_INDEX", "MAX_STATES", "MAX_ATTEMPTS", "MAX_ROUTE_WORK"):
            with self.subTest(name=name), patch("metropogits.world.junctions."+name, 0):
                kept, note = consolidate_junctions(self.streets, [self.streets[1]], [], self.routing)
            self.assertEqual(len(kept), len(self.streets))
            self.assertTrue(note["budgetExhausted"])
