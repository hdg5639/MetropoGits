import json
import shutil
import subprocess
import unittest
from pathlib import Path

from metropogits.layout import generate_city
from metropogits.building_forms import FORMS, building_parts
from metropogits.projection import aggregate_parts, derive_blocks
from metropogits.scanner import ScanResult, ScannedFile, build_structural_ucg
from metropogits.territory import derive_district_territories


def projection_fixture():
    paths = [
        f"{module}/{package}/File{i:03}.py"
        for module in ("API", "frontend", "frontend/app")
        for package in ("config", "service", "tests")
        for i in range(35)
    ]
    graph = build_structural_ucg(
        ScanResult(
            files=tuple(
                ScannedFile(path=p, language="python", size_bytes=4)
                for p in sorted(paths)
            ),
            diagnostics=(),
        ),
        "fixture/projection",
    )
    return generate_city(graph), graph


class ProjectionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_archetype_silhouettes_match_webgl(self):
        buildings = [
            dict(
                entityId=f"file:{i}",
                archetype=archetype,
                x=13.5,
                z=-21,
                width=6,
                depth=8,
                height=20,
            )
            for archetype in [*FORMS, "GENERIC_BUILDING"]
            for i in range(8)
        ]
        script = """
require(process.argv[1]);
const data = JSON.parse(require('fs').readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(data.map(globalThis.METROPOGITS_BUILDING_FORMS.partsFor)));
"""
        result = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1] / "metropogits/viewer_assets/viewer-3d.js"
                ),
            ],
            input=json.dumps(buildings),
            capture_output=True,
            text=True,
            check=True,
        )
        expected = json.loads(result.stdout)
        for building, parts in zip(buildings, expected):
            actual = building_parts(building)
            self.assertEqual(len(parts), len(actual))
            for left, right in zip(parts, actual):
                for key in left:
                    self.assertAlmostEqual(left[key], right[key], places=8)

    def test_blocks_cover_every_file_once_and_parts_stay_in_plots(self):
        scene, _ = projection_fixture()
        blocks = derive_blocks(scene)
        members = [m for b in blocks for m in b["memberEntityIds"]]
        self.assertEqual(
            sorted(b["entityId"] for b in scene["buildings"]), sorted(members)
        )
        for block in blocks:
            parts = aggregate_parts(block)
            self.assertEqual(
                len(block["memberEntityIds"]), sum(p["representedCount"] for p in parts)
            )
            for part in parts:
                self.assertTrue(
                    any(
                        p["x"] <= part["x"]
                        and p["z"] <= part["z"]
                        and part["x"] + part["width"] <= p["x"] + p["width"] + 1e-9
                        and part["z"] + part["depth"] <= p["z"] + p["depth"] + 1e-9
                        for p in block["plots"]
                    )
                )

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_cpu_projection_matches_viewer_geometry_and_membership(self):
        scene, _ = projection_fixture()
        territories = derive_district_territories(scene)
        script = """
require(process.argv[1]);
const data = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const api = globalThis.METROPOGITS_FILTERS;
const blocks = api.createLodPolicy(data.scene, data.territories).aggregates;
process.stdout.write(JSON.stringify({blocks, parts: blocks.map(api.aggregateParts)}));
"""
        result = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits/viewer_assets/viewer-filters.js"
                ),
            ],
            input=json.dumps(dict(scene=scene, territories=territories)),
            capture_output=True,
            text=True,
            check=True,
        )
        expected = json.loads(result.stdout)
        blocks = derive_blocks(scene, territories)

        def normalized(value):
            if isinstance(value, float):
                return round(value, 8)
            if isinstance(value, list):
                return [normalized(v) for v in value]
            if isinstance(value, dict):
                return {k: normalized(v) for k, v in value.items()}
            return value

        # Browser locale sorting may change list order, never membership or
        # geometry. Compare presentation IDs, with canonical member ordering.
        def by_id(blocks, parts):
            return {
                block["id"]: dict(
                    block={
                        **block,
                        "memberEntityIds": sorted(block["memberEntityIds"]),
                    },
                    parts=parts[index],
                )
                for index, block in enumerate(blocks)
            }

        self.assertEqual(
            normalized(by_id(expected["blocks"], expected["parts"])),
            normalized(by_id(blocks, [aggregate_parts(b) for b in blocks])),
        )
