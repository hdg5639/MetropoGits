import json
import unittest
from pathlib import Path

from metropogits.layout import generate_city
from metropogits.scanner import ScanResult, ScannedFile, build_structural_ucg
from metropogits.streets import derive_street_grid
from scripts.canonical_json import canonical_json_bytes


FIXTURES = Path(__file__).parent / "fixtures"


class StreetGridTests(unittest.TestCase):
    def test_network_corridors_are_nonsemantic_and_deterministic(self):
        ucg = json.loads(
            (FIXTURES / "ucg" / "valid" / "spring-minimal.json").read_text(
                encoding="utf-8"
            )
        )
        scene = generate_city(ucg)

        first = derive_street_grid(scene)
        second = derive_street_grid(scene)

        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        self.assertFalse(first["semantic"])
        self.assertTrue(first["rectangles"])
        self.assertTrue(
            any(item["tier"] == "ROUTE_ACCESS" for item in first["rectangles"])
        )
        for rectangle in first["rectangles"]:
            for building in scene["buildings"]:
                self.assertFalse(rectangle["x"] < building["x"] + building["width"]
                                 and rectangle["x"] + rectangle["width"] > building["x"]
                                 and rectangle["z"] < building["z"] + building["depth"]
                                 and rectangle["z"] + rectangle["depth"] > building["z"])

    def test_top_level_gap_without_a_relation_is_not_a_road(self):
        scan = ScanResult(
            files=(
                ScannedFile(path="backend/App.py", language="python", size_bytes=4),
                ScannedFile(path="frontend/App.py", language="python", size_bytes=4),
            ),
            diagnostics=(),
        )
        scene = generate_city(
            build_structural_ucg(scan, "example/street-projection")
        )

        streets = derive_street_grid(scene)

        self.assertEqual([], streets["rectangles"])
        self.assertEqual([], streets["surfaces"])

    def test_shared_paths_split_at_junctions_with_exact_provenance(self):
        scene = {"networks": [
            dict(id="a", edgeIds=["ea"], path=[[0, 0], [28, 0]]),
            dict(id="b", edgeIds=["eb"], path=[[7, 0], [28, 0]]),
            dict(id="c", edgeIds=["ec"], path=[[14, -14], [14, 14]]),
        ]}
        grid = derive_street_grid(scene)
        shared = next(s for s in grid["segments"] if s["start"] == [7, 0])
        self.assertEqual([14, 0], shared["end"])
        self.assertEqual(["a", "b"], shared["networkIds"])
        self.assertEqual(["ea", "eb"], shared["edgeIds"])
        self.assertEqual([dict(point=[14, 0], degree=4, networkIds=["a", "b", "c"])], grid["junctions"])
        scene["networks"].reverse()
        self.assertEqual(grid, derive_street_grid(scene))

    def test_paint_follows_exact_unrounded_path_and_never_rectangle_long_axis(self):
        scene = {"networks": [dict(id="n", edgeIds=["edge"], path=[[1.25, 2.75], [1.25, 50.25]])]}
        grid = derive_street_grid(scene)
        self.assertEqual([1.25, 2.75], grid["segments"][0]["start"])
        stripes = [s for s in grid["surfaces"] if s["color"] == "#a2a996"]
        self.assertTrue(stripes)
        for stripe in stripes:
            self.assertAlmostEqual(1.25, stripe["x"] + stripe["width"] / 2)
            self.assertLess(stripe["width"], stripe["depth"])
            self.assertEqual(["n"], stripe["networkIds"])

    def test_diagonal_legacy_path_does_not_get_fabricated_orthogonal_pavement(self):
        scene = {"networks": [dict(id="n", edgeIds=["edge"], path=[[0, 0], [10, 10]])]}
        self.assertEqual([], derive_street_grid(scene)["surfaces"])


if __name__ == "__main__":
    unittest.main()
