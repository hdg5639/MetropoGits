import copy
import heapq
import shutil
import subprocess
import unittest
from pathlib import Path
from collections import deque
from unittest.mock import patch

from metropogits.access_routes import AccessGrid, PITCH, derive_access_routes, svg_access_lines
from scripts.road_metrics import road_metrics


def fixture():
    buildings = [dict(entityId=name, x=x, z=z, width=6, depth=6)
                 for name, x, z in [("A", .5, .5), ("B", 28.5, .5),
                                    ("C", .5, 14.5), ("D", 28.5, 14.5), ("unused", 14.5, .5)]]
    edges = [dict(id="ab", **{"from": "A", "to": "B"}), dict(id="cd", **{"from": "C", "to": "D"}),
             dict(id="cb", **{"from": "C", "to": "B"})]
    scene = dict(buildings=buildings, networks=[dict(id="n", kind="DEPENDENCY_ROAD", edgeIds=[e["id"] for e in edges])])
    return scene, dict(edges=edges)


class AccessRouteTests(unittest.TestCase):
    def test_directional_search_matches_independent_dijkstra(self):
        class TinyGrid(AccessGrid):
            def __init__(self):
                self.expansions = 0

            def neighbors(self, node):
                x, z = node
                for other in ((x-1, z), (x, z-1), (x, z+1), (x+1, z)):
                    if 0 <= other[0] <= 5 and 0 <= other[1] <= 5 and other not in {(2, 2), (2, 3), (4, 1)}:
                        yield other, 2 if (x+z+sum(other)) % 3 else .5

        grid = TinyGrid()
        usage = {tuple(sorted((node, other))): (sum(node)+sum(other)) % 9
                 for node in ((x, z) for x in range(6) for z in range(6))
                 for other, _ in grid.neighbors(node)}

        def transition(a, b, heading, clearance, terminal=(0, 0)):
            direction = (b[0]-a[0], b[1]-a[1])
            turn = int(heading != (0, 0) and heading != direction)
            turn += int(terminal != (0, 0) and terminal != direction)
            weight = min(100, 98 - (2 if clearance >= 1.5 else 0) - min(6, usage.get(tuple(sorted((a, b))), 0)) + turn*2)
            self.assertGreaterEqual(weight, 90)
            self.assertLessEqual(weight, 100)
            return weight, turn, direction

        # No heuristic; retain all arrival directions and compare lexicographic
        # optimum, not just endpoints or an arbitrary expected drawing.
        for start in ((0, 0), (1, 4), (5, 0)):
            cases = [(end, a, b) for end in ((0, 5), (5, 5), (4, 2), start)
                     for a, b in [((0, 0), (0, 0)), ((1, 0), (0, 1)), ((-1, 0), (1, 0))]]
            for end, start_heading, end_heading in cases:
                queue = [(0, 0, start, start_heading)]
                seen = set()
                while queue:
                    cost, bends, node, heading = heapq.heappop(queue)
                    if (node, heading) in seen:
                        continue
                    seen.add((node, heading))
                    if node == end:
                        optimum = cost, bends
                        break
                    for other, clearance in grid.neighbors(node):
                        weight, turn, direction = transition(node, other, heading, clearance,
                                                             end_heading if other == end else (0, 0))
                        heapq.heappush(queue, (cost+weight, bends+turn, other, direction))
                path = grid.route(start, end, usage, start_heading, end_heading)
                score, bends, heading = 0, 0, start_heading
                for a, b in zip(path, path[1:]):
                    weight, turn, heading = transition(a, b, heading, dict(grid.neighbors(a))[b],
                                                       end_heading if b == end else (0, 0))
                    score += weight
                    bends += turn
                self.assertEqual(optimum, (score, bends))
                self.assertEqual(start, path[0])
                self.assertEqual(end, path[-1])

    def test_bend_budget_and_resource_exhaustion(self):
        scene, _ = fixture()
        grid = AccessGrid(scene["buildings"])
        path = grid.route((-2, -2), (10, -1), {})
        headings = [(b[0]-a[0], b[1]-a[1]) for a, b in zip(path, path[1:])]
        self.assertEqual(1, sum(a != b for a, b in zip(headings, headings[1:])))
        # Align both short access spurs, not only the lattice portion.
        path = grid.route((-2, -2), (10, -1), {}, (1, 0), (0, 1))
        headings = [(1, 0), *[(b[0]-a[0], b[1]-a[1]) for a, b in zip(path, path[1:])], (0, 1)]
        self.assertEqual(1, sum(a != b for a, b in zip(headings, headings[1:])))
        with patch("metropogits.access_routes.MAX_EXPANSIONS", 0):
            self.assertIsNone(grid.route((-2, -2), (10, -1), {}))

    def test_geometry_metrics_are_length_weighted_and_do_not_change_inputs(self):
        routing = dict(routes=[dict(path=[[0, 0], [2, 0], [4, 0], [4, 2]])],
                       segments=[dict(start=[0, 0], end=[4, 0], access=False, kind="DEPENDENCY_ROAD", routeIds=["a", "b"]),
                                 dict(start=[1, 3.5], end=[3, 3.5], access=False, kind="DEPENDENCY_ROAD", routeIds=["c"])],
                       junctions=[], unresolvedEdgeIds=[])
        original = copy.deepcopy(routing)
        metrics = road_metrics(routing)
        self.assertEqual(1, metrics["turns"])
        self.assertEqual(6, metrics["routeLength"])
        self.assertEqual(6, metrics["pavementCenterlineLength"])
        self.assertEqual(4, metrics["sharedCenterlineLength"])
        self.assertEqual(2, metrics["nearbyParallelPairLength"])
        self.assertEqual(original, routing)

    def test_svg_hierarchy_preserves_paths_and_geometry(self):
        routes = [dict(id=str(i), kind="DEPENDENCY_ROAD", source="A", target=str(i),
                       edgeIds=[f"edge-{i}"], networkIds=[str(i)]) for i in range(4)]
        segment = dict(id="shared", start=[0, 0], end=[7, 0], width=.5,
                       access=False, kind="DEPENDENCY_ROAD", routeIds=[r["id"] for r in routes])
        routing = dict(version="test", status="COMPLETE", unresolvedEdgeIds=[],
                       routes=routes, segments=[segment])
        original = copy.deepcopy(routing)
        def project(x, z):
            return x, z
        shared = "\n".join(svg_access_lines(routing, project))
        filtered = "\n".join(svg_access_lines(routing, project, network_ids={"0"}))
        self.assertIn('fill="#52677b"', shared)
        self.assertIn('fill="#33465a"', filtered)
        self.assertIn('data-route-indexes="0 1 2 3"', shared)
        self.assertIn('data-route-indexes="0"', filtered)
        for output in (shared, filtered):
            self.assertIn('points="0.000,-0.250 7.000,-0.250 7.000,0.250 0.000,0.250"', output)
        self.assertEqual(original, routing)

    @unittest.skipUnless(shutil.which("node"), "Node unavailable")
    def test_shared_viewer_policy(self):
        subprocess.run(["node", "--test", str(Path(__file__).with_name("access_routes.test.mjs"))],
                       check=True, capture_output=True, text=True, encoding="utf-8")

    def test_exact_pairs_shared_segments_and_boundary_endpoints(self):
        scene, graph = fixture()
        routing = derive_access_routes(scene, graph)
        self.assertEqual("COMPLETE", routing["status"])
        self.assertEqual({("A", "B"), ("C", "D"), ("C", "B")}, {(r["source"], r["target"]) for r in routing["routes"]})
        self.assertEqual({"ab", "cd", "cb"}, {e for r in routing["routes"] for e in r["edgeIds"]})
        self.assertTrue(any(len(s["routeIds"]) > 1 for s in routing["segments"]))
        self.assertTrue(routing["junctions"])
        buildings = {b["entityId"]: b for b in scene["buildings"]}
        grid = AccessGrid(scene["buildings"])
        segments = {s["id"]: s for s in routing["segments"]}
        for route in routing["routes"]:
            self.assertEqual(len(route["path"])-1, len(route["segmentIds"]))
            for i, identity in enumerate(route["segmentIds"]):
                segment = segments[identity]
                self.assertEqual(sorted([segment["start"],segment["end"]]), sorted(route["path"][i:i+2]))
            for entity_id, point in ((route["source"], route["path"][0]), (route["target"], route["path"][-1])):
                b = buildings[entity_id]
                self.assertTrue(point[0] in (b["x"], b["x"]+b["width"]) or point[1] in (b["z"], b["z"]+b["depth"]))
        for segment in routing["segments"]:
            if not segment["access"]:
                self.assertGreaterEqual(grid.clearance(segment["start"], segment["end"]), segment["width"] / 2)

    def test_determinism_and_no_input_mutation(self):
        scene, graph = fixture()
        original = copy.deepcopy((scene, graph))
        first = derive_access_routes(scene, graph)
        self.assertEqual(original, (scene, graph))
        scene["buildings"].reverse()
        graph["edges"].reverse()
        scene["networks"][0]["edgeIds"].reverse()
        self.assertEqual(first, derive_access_routes(scene, graph))

    def test_pavement_never_enters_buildings_and_sharing_detour_is_bounded(self):
        scene, graph = fixture()
        routing = derive_access_routes(scene, graph)
        grid = AccessGrid(scene["buildings"])
        for segment in routing["segments"]:
            a, b = segment["start"], segment["end"]
            half = segment["width"] / 2
            dx, dz = (0, half) if a[1] == b[1] else (half, 0)
            left, right = min(a[0],b[0])-dx, max(a[0],b[0])+dx
            top, bottom = min(a[1],b[1])-dz, max(a[1],b[1])+dz
            for building in scene["buildings"]:
                self.assertFalse(left < building["x"]+building["width"] and right > building["x"]
                                 and top < building["z"]+building["depth"] and bottom > building["z"])
        for route in routing["routes"]:
            start = tuple(round(v/PITCH) for v in route["path"][1])
            end = tuple(round(v/PITCH) for v in route["path"][-2])
            queue, distances = deque([start]), {start:0}
            while queue and end not in distances:
                current = queue.popleft()
                for other, _ in grid.neighbors(current):
                    if other not in distances:
                        distances[other] = distances[current]+1
                        queue.append(other)
            self.assertLessEqual(route["latticeSteps"], distances[end]*100/90)

    def test_self_reference_retains_its_return_path_without_new_neighbors(self):
        scene, graph = fixture()
        graph["edges"] = [dict(id="self", **{"from":"A","to":"A"})]
        scene["networks"][0]["edgeIds"] = ["self"]
        route = derive_access_routes(scene, graph)["routes"][0]
        self.assertEqual(route["path"][0], route["path"][-1])
        self.assertEqual(len(route["path"])-1,len(route["segmentIds"]))
        self.assertEqual("A",route["target"])

    def test_no_relation_means_no_roads_and_limits_do_not_invent_fallbacks(self):
        scene, graph = fixture()
        scene["networks"] = []
        self.assertEqual([], derive_access_routes(scene, graph)["segments"])
        scene, graph = fixture()
        scene["buildings"][0]["x"] = 1e6
        result = derive_access_routes(scene, graph)
        self.assertEqual("PARTIAL", result["status"])
        self.assertCountEqual(["ab", "cb", "cd"], result["unresolvedEdgeIds"])
        self.assertEqual([], result["segments"])


if __name__ == "__main__":
    unittest.main()
