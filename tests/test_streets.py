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

    def test_top_level_gap_becomes_a_boulevard(self):
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

        self.assertTrue(
            any(item["tier"] == "BOULEVARD" for item in streets["rectangles"])
        )


if __name__ == "__main__":
    unittest.main()
