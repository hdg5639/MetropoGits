import copy
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from metropogits.cli import analyze_repository, main
from metropogits.layout import generate_city
from metropogits.showcase import render_showcase
from metropogits.preview import PreviewError
from scripts.canonical_json import canonical_json_bytes, loads_strict_json
from scripts.stable_ids import make_edge_id
from metropogits.scanner import ScanResult, ScannedFile, build_structural_ucg
from test_projection import projection_fixture


NS = {"s": "http://www.w3.org/2000/svg"}


def metadata(svg):
    return json.loads(ET.fromstring(svg).find("s:metadata", NS).text)


class ShowcaseTests(unittest.TestCase):
    def test_unknown_languages_keep_real_file_buildings(self):
        graph = analyze_repository(
            Path(__file__).parent / "fixtures/repositories/structural-showcase"
        )
        scene = generate_city(graph)
        result = metadata(render_showcase(scene, graph))
        self.assertEqual(3, len(scene["buildings"]))
        self.assertEqual(
            {"GENERIC_BUILDING"}, {b["archetype"] for b in scene["buildings"]}
        )
        self.assertEqual(
            3, sum(m["kind"] == "file" for m in result["mappings"].values())
        )
        self.assertFalse(
            any(m["kind"] == "network" for m in result["mappings"].values())
        )

    def test_network_budget_discloses_omitted_routes_without_losing_edges(self):
        scan = ScanResult(
            files=tuple(
                ScannedFile(
                    path=f"module{i:02}/File.py", language="python", size_bytes=4
                )
                for i in range(32)
            ),
            diagnostics=(),
        )
        graph = build_structural_ucg(scan, "fixture/routes")
        files = [e for e in graph["entities"] if e["kind"] == "FILE"]
        graph["evidence"] = [
            dict(
                evidenceId="fixture:evidence",
                sourcePath=files[0]["path"],
                extractor="fixture",
                kind="AST",
                summary="Synthetic relation fixture",
            )
        ]
        for i in range(1, len(files)):
            edge = dict(
                id=make_edge_id(files[0]["id"], "REFERENCES", files[i]["id"]),
                type="REFERENCES",
                confidence="DIRECT",
                evidenceIds=["fixture:evidence"],
            )
            edge["from"], edge["to"] = files[0]["id"], files[i]["id"]
            graph["edges"].append(edge)
        graph["edges"].sort(key=lambda e: e["id"])
        scene = generate_city(graph)
        result = metadata(render_showcase(scene, graph))
        shown = {k: v for k, v in result["mappings"].items() if v["kind"] == "network"}
        self.assertEqual(31, len(scene["networks"]))
        self.assertEqual(24, len(shown))
        self.assertEqual(7, len(result["hiddenNetworkIds"]))
        self.assertEqual(
            {n["id"] for n in scene["networks"]},
            set(shown) | set(result["hiddenNetworkIds"]),
        )
        for network in scene["networks"]:
            if network["id"] in shown:
                self.assertEqual(network["edgeIds"], shown[network["id"]]["edgeIds"])

    def setUp(self):
        self.graph = analyze_repository(
            Path(__file__).parent / "fixtures/repositories/spring-positive",
            "fixture/showcase",
        )
        self.scene = generate_city(self.graph)

    def test_deterministic_projection_preserves_inputs_and_evidence(self):
        before = canonical_json_bytes([self.scene, self.graph])
        svg = render_showcase(self.scene, self.graph)
        self.assertEqual(svg, render_showcase(self.scene, self.graph))
        # The CLI's strict Decimal loader must produce exactly the same SVG.
        strict_scene = loads_strict_json(canonical_json_bytes(self.scene).decode())
        self.assertEqual(svg, render_showcase(strict_scene, self.graph))
        self.assertEqual(before, canonical_json_bytes([self.scene, self.graph]))
        mapping = metadata(svg)["mappings"]
        for b in self.scene["buildings"]:
            self.assertEqual(b["entityId"], mapping[b["entityId"]]["entityId"])
        for n in self.scene["networks"]:
            self.assertEqual(n["edgeIds"], mapping[n["id"]]["edgeIds"])
        self.assertNotIn(b"<script", svg)
        self.assertNotIn(b"<foreignObject", svg)

    def test_large_city_has_complete_aggregate_membership_and_bounded_routes(self):
        scene, graph = projection_fixture()
        result = metadata(render_showcase(scene, graph))
        members = [
            m
            for value in result["mappings"].values()
            if value["kind"] == "visual-block"
            for m in value["memberEntityIds"]
        ]
        self.assertEqual(
            sorted(b["entityId"] for b in scene["buildings"]), sorted(members)
        )
        self.assertLessEqual(
            sum(v["kind"] == "network" for v in result["mappings"].values()), 24
        )
        self.assertTrue(
            all(
                v.get("semantic") is False
                for v in result["mappings"].values()
                if v["kind"] == "structural-streets"
            )
        )

    def test_geometry_stays_in_content_and_labels_do_not_collide(self):
        for scene, graph in [(self.scene, self.graph), projection_fixture()]:
            for width, height in [(1200, 675), (640, 360), (320, 240)]:
                root = ET.fromstring(render_showcase(scene, graph, width, height))
                info = json.loads(root.find("s:metadata", NS).text)
                box = info["camera"]["contentBounds"]
                for polygon in root.findall(".//s:polygon", NS):
                    for pair in polygon.attrib["points"].split():
                        x, y = map(float, pair.split(","))
                        self.assertGreaterEqual(x, box["x"] - 0.001)
                        self.assertLessEqual(x, box["x"] + box["width"] + 0.001)
                        self.assertGreaterEqual(y, box["y"] - 0.001)
                        self.assertLessEqual(y, box["y"] + box["height"] + 0.001)
                labels = info["labels"]
                for i, a in enumerate(labels):
                    for b in labels[i + 1 :]:
                        self.assertFalse(
                            a["x"] < b["x"] + b["width"]
                            and a["x"] + a["width"] > b["x"]
                            and a["y"] < b["y"] + b["height"]
                            and a["y"] + a["height"] > b["y"]
                        )

    def test_untrusted_text_and_invalid_contract(self):
        graph = copy.deepcopy(self.graph)
        graph["repository"]["id"] = "<script>&\u0001"
        svg = render_showcase(generate_city(graph), graph)
        ET.fromstring(svg)
        self.assertNotIn(b"<script>", svg)
        self.assertNotIn(b"\x01", svg)
        scene = copy.deepcopy(self.scene)
        scene["buildings"][0]["entityId"] = "missing"
        with self.assertRaises(PreviewError):
            render_showcase(scene, self.graph)
        with self.assertRaises(PreviewError):
            render_showcase(self.scene, self.graph, width=100)

    def test_cli_mode_remains_opt_in_for_render(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scene.json").write_bytes(canonical_json_bytes(self.scene))
            (root / "graph.json").write_bytes(canonical_json_bytes(self.graph))
            args = [
                "render",
                "--scene",
                str(root / "scene.json"),
                "--graph",
                str(root / "graph.json"),
                "--out",
                str(root / "result.svg"),
            ]
            self.assertEqual(0, main(args))
            self.assertNotIn(b"showcase-metadata", (root / "result.svg").read_bytes())
            self.assertEqual(0, main([*args, "--mode", "showcase"]))
            self.assertEqual(
                "showcase/0.1",
                metadata((root / "result.svg").read_bytes())["projectionVersion"],
            )
