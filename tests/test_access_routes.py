import copy
import shutil
import subprocess
import unittest
from pathlib import Path
from collections import deque

from metropogits.access_routes import AccessGrid, PITCH, derive_access_routes


def fixture():
    buildings = [dict(entityId=name, x=x, z=z, width=6, depth=6)
                 for name, x, z in [("A", .5, .5), ("B", 28.5, .5),
                                    ("C", .5, 14.5), ("D", 28.5, 14.5), ("unused", 14.5, .5)]]
    edges = [dict(id="ab", **{"from": "A", "to": "B"}), dict(id="cd", **{"from": "C", "to": "D"}),
             dict(id="cb", **{"from": "C", "to": "B"})]
    scene = dict(buildings=buildings, networks=[dict(id="n", kind="DEPENDENCY_ROAD", edgeIds=[e["id"] for e in edges])])
    return scene, dict(edges=edges)


class AccessRouteTests(unittest.TestCase):
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
