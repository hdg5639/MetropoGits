import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from metropogits.layout import generate_city
from metropogits.viewer import ViewerError, render_viewer
from scripts.canonical_json import loads_strict_json


FIXTURE_ROOT = Path(__file__).parent / "fixtures"


def load_fixture() -> dict:
    return loads_strict_json(
        (FIXTURE_ROOT / "ucg" / "valid" / "spring-minimal.json").read_text(
            encoding="utf-8"
        )
    )


class ViewerTests(unittest.TestCase):
    def test_structure_overlay_is_opt_in_street_presentation_not_scene_mutation(self):
        from metropogits.access_routes import derive_access_routes
        from metropogits.structural_streets import assign_streets
        from metropogits.city_context import city_context
        graph=load_fixture()
        scene=generate_city(graph)
        frozen=copy.deepcopy(scene)
        plain=render_viewer(scene,graph)
        self.assertNotIn(b'data-action="toggle-structure"',plain['index.html'])
        original=derive_access_routes(scene,graph)
        routing=assign_streets(scene,original,aligned=True)
        output=render_viewer(scene,graph,routing)
        self.assertIn(b'data-action="toggle-structure" aria-pressed="false"',output['index.html'])
        self.assertIn(b'"cityContext":{"ground":',output['assets/viewer-data.js'])
        self.assertEqual(frozen,scene)
        self.assertEqual(output,render_viewer(scene,graph,routing))
        self.assertIsNone(city_context(original))

    @unittest.skipUnless(shutil.which("node"), "Node unavailable")
    def test_camera_navigation_policy(self):
        subprocess.run(["node", "--test", str(Path(__file__).with_name("camera_navigation.test.mjs"))],
                       check=True, capture_output=True, text=True, encoding="utf-8")

    def test_navigation_controls_are_packaged_for_both_renderers(self):
        artifacts = render_viewer(generate_city(load_fixture()), load_fixture())
        html = artifacts["index.html"].decode("utf-8")
        for action in ("toggle-pan", "pan-left", "pan-right", "pan-up", "pan-down"):
            self.assertIn(f'data-action="{action}"', html)
        self.assertIn('id="district-jump"', html)
        for name in ("viewer-3d.js", "viewer.js"):
            source = artifacts[f"assets/{name}"].decode("utf-8")
            self.assertIn("filterEngine.cameraKeyAction(event)", source)
            self.assertIn('districtJump.addEventListener("change"', source)
            self.assertIn('event.button !== 0 ? "pan"', source)

    def test_legend_has_its_own_row_outside_the_canvas_stage(self):
        artifacts = render_viewer(generate_city(load_fixture()), load_fixture())
        html = artifacts["index.html"].decode("utf-8")
        css = artifacts["assets/viewer.css"].decode("utf-8")
        self.assertIn('<div class="city-stage">', html)
        self.assertIn('</div>\n        <div class="legend"', html)
        self.assertIn('grid-template-rows: minmax(0, 1fr) auto', css)
        self.assertNotIn('bottom: 0.8rem', css)

    def test_viewer_is_deterministic_and_file_protocol_compatible(self):
        graph = load_fixture()
        scene = generate_city(graph)

        first = render_viewer(scene, graph)
        second = render_viewer(scene, graph)

        self.assertEqual(first, second)
        self.assertEqual(
            {
                "assets/viewer-activity.js",
                "assets/viewer-3d.js",
                "assets/viewer-data.js",
                "assets/viewer.css",
                "assets/viewer-filters.js",
                "assets/viewer.js",
                "index.html",
            },
            set(first),
        )
        html = first["index.html"].decode("utf-8")
        viewer_data = first["assets/viewer-data.js"].decode("utf-8")
        self.assertIn("Content-Security-Policy", html)
        self.assertIn('data-filter="role"', html)
        self.assertIn('data-filter="confidence"', html)
        self.assertIn('id="synthetic-activity"', html)
        self.assertIn("not measured runtime traffic", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("fetch(", first["assets/viewer.js"].decode("utf-8"))
        self.assertIn('"territories":{"cellSize":7,"districts":[', viewer_data)
        payload = json.loads(viewer_data.removeprefix("globalThis.METROPOGITS_DATA=").strip().removesuffix(";"))
        self.assertEqual("network.path", payload["streets"]["basis"])
        self.assertTrue(payload["streets"]["segments"])
        self.assertIn("Route corridor (derived)", html)

    def test_viewer_assets_are_subpath_safe(self):
        graph = load_fixture()
        html = render_viewer(generate_city(graph), graph)["index.html"].decode(
            "utf-8"
        )

        self.assertNotRegex(html, r'''(?:href|src)=["']/''')
        self.assertIn('href="assets/viewer.css"', html)
        self.assertIn('src="assets/viewer.js"', html)
        self.assertIn('src="assets/viewer-3d.js"', html)
        self.assertLess(html.index("viewer-3d.js"), html.index("viewer.js"))
        self.assertIn('href="preview.svg"', html)

    def test_untrusted_graph_text_is_encoded_as_javascript_data(self):
        graph = copy.deepcopy(load_fixture())
        graph["repository"]["sourceUrl"] = "</script><img src=x onerror=alert(1)>"
        scene = generate_city(graph)

        artifacts = render_viewer(scene, graph)
        viewer_data = artifacts["assets/viewer-data.js"].decode("utf-8")

        self.assertNotIn("</script>", viewer_data)
        self.assertNotIn("<img", viewer_data)
        self.assertIn(r"\u003c/script\u003e", viewer_data)

    def test_viewer_script_avoids_html_injection_sinks(self):
        artifacts = render_viewer(generate_city(load_fixture()), load_fixture())
        for name in ("assets/viewer-3d.js", "assets/viewer.js"):
            script = artifacts[name].decode("utf-8")
            self.assertNotIn("innerHTML", script)
            self.assertNotIn("outerHTML", script)
            self.assertNotIn("eval(", script)
            self.assertNotIn("fetch(", script)
            self.assertIn("textContent", script)

    def test_invalid_scene_is_rejected(self):
        graph = load_fixture()
        scene = generate_city(graph)
        scene["ucgDigest"] = "sha256:" + "0" * 64

        with self.assertRaisesRegex(ViewerError, "invalid City Scene"):
            render_viewer(scene, graph)

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_viewer_javascript_parses(self):
        graph = load_fixture()
        artifacts = render_viewer(generate_city(graph), graph)
        with tempfile.TemporaryDirectory() as temporary:
            for name in (
                "viewer-activity.js",
                "viewer-filters.js",
                "viewer-3d.js",
                "viewer.js",
            ):
                script = Path(temporary) / name
                script.write_bytes(artifacts[f"assets/{name}"])
                completed = subprocess.run(
                    ["node", "--check", str(script)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_webgl_math_projects_camera_target_to_viewport_center(self):
        script = """
require(process.argv[1]);
const math = globalThis.METROPOGITS_WEBGL_MATH;
const view = math.lookAt([10, 10, 10], [0, 0, 0], [0, 1, 0]);
const projection = math.perspective(Math.PI / 4, 16 / 9, 0.1, 100);
const matrix = math.multiply(projection, view);
const center = math.projectPoint(matrix, [0, 0, 0], 1600, 900);
process.stdout.write(JSON.stringify({ center, behind: math.projectPoint(matrix, [20, 20, 20], 1600, 900) }));
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-3d.js"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        result = json.loads(completed.stdout)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertAlmostEqual(800, result["center"]["x"], places=6)
        self.assertAlmostEqual(450, result["center"]["y"], places=6)
        self.assertIsNone(result["behind"])

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_semantic_archetypes_have_distinct_bounded_3d_forms(self):
        script = """
require(process.argv[1]);
const forms = globalThis.METROPOGITS_BUILDING_FORMS;
const archetypes = [
  "GATE", "SERVICE_OFFICE", "STRUCTURED_WAREHOUSE", "DOCUMENT_DEPOT",
  "CACHE_TOWER", "EXCHANGE", "PORT", "CONTROL_CENTER", "LIBRARY",
];
const result = Object.fromEntries(archetypes.map((archetype) => {
  const building = { archetype, depth: 6, entityId: `demo:${archetype}`, height: 18, width: 6, x: 10, z: 20 };
  return [archetype, forms.partsFor(building)];
}));
process.stdout.write(JSON.stringify(result));
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-3d.js"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        forms = json.loads(completed.stdout)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(9, len({json.dumps(parts, sort_keys=True) for parts in forms.values()}))
        for parts in forms.values():
            self.assertGreaterEqual(len(parts), 3)
            for part in parts:
                self.assertGreater(part["width"], 0)
                self.assertGreater(part["height"], 0)
                self.assertGreater(part["depth"], 0)
                self.assertGreaterEqual(part["x"], 10)
                self.assertGreaterEqual(part["z"], 20)
                self.assertLessEqual(part["x"] + part["width"], 16)
                self.assertLessEqual(part["z"] + part["depth"], 26)
                self.assertLessEqual(part["y"] + part["height"], 18.000001)

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_network_categories_have_distinct_layered_road_profiles(self):
        script = """
require(process.argv[1]);
process.stdout.write(JSON.stringify(globalThis.METROPOGITS_NETWORK_STYLES));
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-3d.js"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        profiles = json.loads(completed.stdout)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(
            {"DEPENDENCY_ROAD", "HTTP_HIGHWAY", "MESSAGING_PATH"},
            set(profiles),
        )
        self.assertEqual(
            3,
            len({json.dumps(profile, sort_keys=True) for profile in profiles.values()}),
        )
        for profile in profiles.values():
            self.assertGreater(profile["shoulder"], profile["surface"])
            self.assertGreater(profile["surface"], profile["marking"])

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_webgl_camera_policy_favors_city_scale_composition(self):
        script = """
require(process.argv[1]);
process.stdout.write(JSON.stringify(globalThis.METROPOGITS_CAMERA_POLICY));
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-3d.js"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        policy = json.loads(completed.stdout)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertGreater(policy["horizontalMargin"], 0.9)
        self.assertGreater(policy["verticalMargin"], 0.9)
        self.assertGreater(policy["pitch"], 0.5)
        self.assertLess(policy["pitch"], 0.7)
        self.assertLess(policy["yaw"], -0.5)
        self.assertGreater(policy["yaw"], -0.8)

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_perspective_framing_keeps_extreme_points_inside_view(self):
        subprocess.run(["node", "--test", str(Path(__file__).with_name("camera_framing.test.mjs"))],
                       check=True, capture_output=True, encoding="utf-8")

    def test_webgl_renderer_has_explicit_2d_fallback_boundary(self):
        artifacts = render_viewer(generate_city(load_fixture()), load_fixture())
        webgl = artifacts["assets/viewer-3d.js"].decode("utf-8")
        fallback = artifacts["assets/viewer.js"].decode("utf-8")

        self.assertIn('canvas.getContext("webgl"', webgl)
        self.assertIn('METROPOGITS_RENDERER = "webgl"', webgl)
        self.assertIn("restoreCanvasForFallback", webgl)
        self.assertIn('METROPOGITS_RENDERER === "webgl"', fallback)
        self.assertIn('METROPOGITS_RENDERER = "canvas-2d"', fallback)

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_synthetic_activity_is_deterministic_and_path_bounded(self):
        script = """
require(process.argv[1]);
const activity = globalThis.METROPOGITS_ACTIVITY;
const first = activity.phaseForId("network:demo");
const second = activity.phaseForId("network:demo");
process.stdout.write(JSON.stringify({
  first,
  second,
  midpoint: activity.pointAlongPath([[0, 0], [10, 0], [10, 10]], 0.75),
  start: activity.pointAlongPath([[2, 3], [4, 5]], -1),
  end: activity.pointAlongPath([[2, 3], [4, 5]], 2),
}));
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-activity.js"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        result = json.loads(completed.stdout)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(result["first"], result["second"])
        self.assertGreaterEqual(result["first"], 0)
        self.assertLess(result["first"], 1)
        self.assertEqual([10, 5], result["midpoint"])
        self.assertEqual([2, 3], result["start"])
        self.assertEqual([4, 5], result["end"])

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_category_filters_cover_buildings_and_networks(self):
        graph = load_fixture()
        graph["entities"][0]["technologies"] = [
            {
                "confidence": "DECLARED",
                "evidenceIds": ["ev2"],
                "value": "SPRING_DATA",
            }
        ]
        scene = generate_city(load_fixture())
        script = """
const fs = require("fs");
require(process.argv[1]);
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const index = globalThis.METROPOGITS_FILTERS.createIndex(input.scene, input.ucg);
const apply = (filters) => index.filter({
  confidence: "", language: "", role: "", technology: "", ...filters,
});
process.stdout.write(JSON.stringify({
  all: apply({}),
  confidence: apply({ confidence: "DIRECT" }),
  language: apply({ language: "java" }),
  options: index.options,
  role: apply({ role: "SERVICE" }),
  technology: apply({ technology: "SPRING_DATA" }),
}));
"""

        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-filters.js"
                ),
            ],
            input=json.dumps({"scene": scene, "ucg": graph}),
            capture_output=True,
            text=True,
            check=False,
        )
        result = json.loads(completed.stdout)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(2, len(result["all"]["buildingIds"]))
        self.assertEqual(1, len(result["all"]["networkIds"]))
        self.assertEqual(
            ["demo:file:src/UserService.java"], result["role"]["buildingIds"]
        )
        self.assertEqual(1, len(result["role"]["networkIds"]))
        self.assertEqual(
            ["demo:file:src/UserRepository.java"],
            result["technology"]["buildingIds"],
        )
        self.assertEqual(1, len(result["technology"]["networkIds"]))
        self.assertEqual(2, len(result["language"]["buildingIds"]))
        self.assertEqual(
            ["demo:file:src/UserService.java"],
            result["confidence"]["buildingIds"],
        )
        self.assertEqual([], result["confidence"]["networkIds"])
        self.assertEqual(["java"], result["options"]["languages"])
        self.assertEqual(["PERSISTENCE_ADAPTER", "SERVICE"], result["options"]["roles"])
        self.assertEqual(["SPRING_DATA"], result["options"]["technologies"])

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_district_labels_are_decluttered_by_priority_and_viewport(self):
        script = """
require(process.argv[1]);
const select = globalThis.METROPOGITS_FILTERS.selectNonOverlappingLabels;
const candidates = [
  { id: "low", x: 10, y: 10, width: 80, height: 16, priority: 1 },
  { id: "high", x: 20, y: 12, width: 80, height: 16, priority: 10 },
  { id: "separate", x: 150, y: 40, width: 70, height: 16, priority: 1 },
  { id: "outside", x: 270, y: 40, width: 70, height: 16, priority: 100 },
];
process.stdout.write(JSON.stringify(select(candidates, 300, 120)));
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-filters.js"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(["high", "separate"], json.loads(completed.stdout))

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_major_districts_follow_large_structural_branches(self):
        script = """
require(process.argv[1]);
const districts = [
  { id: "root", parentId: null },
  { id: "backend", parentId: "root" },
  { id: "frontend", parentId: "root" },
  { id: "tiny", parentId: "root" },
  { id: "auth", parentId: "backend" },
  { id: "ops", parentId: "backend" },
  { id: "portal", parentId: "frontend" },
];
const buildings = [
  ...Array.from({ length: 80 }, (_, index) => ({ districtId: "auth", entityId: `auth-${index}` })),
  ...Array.from({ length: 200 }, (_, index) => ({ districtId: "ops", entityId: `ops-${index}` })),
  ...Array.from({ length: 100 }, (_, index) => ({ districtId: "portal", entityId: `portal-${index}` })),
  { districtId: "tiny", entityId: "tiny-0" },
];
process.stdout.write(JSON.stringify(
  globalThis.METROPOGITS_FILTERS.majorDistrictIds({ buildings, districts }),
));
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-filters.js"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(["auth", "ops", "portal"], json.loads(completed.stdout))

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_large_city_lod_is_deterministic_and_progressive(self):
        script = """
require(process.argv[1]);
const districts = [
  { depth: 220, id: "root", parentId: null, width: 240, x: 0, z: 0 },
  { depth: 190, id: "app", parentId: "root", width: 220, x: 10, z: 10 },
  { depth: 160, id: "leaf", parentId: "app", width: 200, x: 20, z: 20 },
  { depth: 20, id: "deep", parentId: "leaf", width: 20, x: 30, z: 30 },
];
const buildings = Array.from({ length: 300 }, (_, index) => ({
  archetype: index < 12 ? "SERVICE_OFFICE" : "GENERIC_BUILDING",
  depth: 6,
  districtId: "leaf",
  entityId: `building-${index}`,
  height: 10,
  width: 6,
  x: 24 + (index % 20) * 9,
  z: 24 + Math.floor(index / 20) * 9,
}));
const networks = Array.from({ length: 100 }, (_, index) => ({
  edgeIds: Array.from({ length: 100 - index }, (_, edge) => `edge-${index}-${edge}`),
  id: `network-${String(index).padStart(3, "0")}`,
}));
const territoryData = { districts: [{
  id: "leaf",
  landmarkPlot: { depth: 135, width: 180, x: 22, z: 22 },
  rectangles: [{ depth: 135, width: 180, x: 22, z: 22 }],
}] };
const policy = globalThis.METROPOGITS_FILTERS.createLodPolicy(
  { buildings, districts, networks },
  territoryData,
);
const buildingIds = buildings.map((building) => building.entityId);
const networkIds = networks.map((network) => network.id);
const overview = policy.visibility("overview", buildingIds, networkIds);
const district = policy.visibility("district", buildingIds, networkIds);
const detail = policy.visibility("detail", buildingIds, networkIds);
const aggregate = policy.aggregates[0];
const aggregateMembers = policy.aggregates.flatMap((item) => item.memberEntityIds);
const aggregatePlots = policy.aggregates.flatMap((item) =>
  item.plots.map((plot) => ({ ...plot, aggregateId: item.id })),
);
const aggregateDistrict = districts.find((district) => district.id === aggregate.districtId);
const aggregateParts = globalThis.METROPOGITS_FILTERS.aggregateParts(aggregate);
const aggregatePlot = territoryData.districts[0].landmarkPlot;
const overlaps = aggregatePlots.flatMap((left, leftIndex) =>
  aggregatePlots.slice(leftIndex + 1).filter((right) =>
    left.aggregateId !== right.aggregateId
    && left.x < right.x + right.width
    && right.x < left.x + left.width
    && left.z < right.z + right.depth
    && right.z < left.z + left.depth
  ).map((right) => [left.aggregateId, right.aggregateId])
);
const filteredIds = new Set(buildingIds.slice(0, 10));
const filteredOverview = policy.visibility("overview", filteredIds, networkIds);
const spreadFacility = {
  archetypeCounts: [{ archetype: "GENERIC_BUILDING", count: 64 }],
  depth: 100,
  height: 32,
  id: "visual:block:spread",
  memberEntityIds: Array.from({ length: 64 }, (_, index) => `spread-${index}`),
  plots: [
    { depth: 10, width: 10, x: 0, z: 0 },
    { depth: 10, width: 10, x: 90, z: 0 },
    { depth: 10, width: 10, x: 0, z: 90 },
    { depth: 10, width: 10, x: 90, z: 90 },
  ],
  width: 100,
  x: 0,
  z: 0,
};
const spreadParts = globalThis.METROPOGITS_FILTERS.aggregateParts(spreadFacility);
const spreadCentersX = spreadParts.map((part) => part.x + part.width / 2);
const spreadCentersZ = spreadParts.map((part) => part.z + part.depth / 2);
const balancedFacility = {
  archetypeCounts: [{ archetype: "GENERIC_BUILDING", count: 36 }],
  depth: 100,
  height: 32,
  id: "visual:block:balanced",
  memberEntityIds: Array.from({ length: 36 }, (_, index) => `balanced-${index}`),
  plots: [0, 45, 90].flatMap((z) => [0, 45, 90].map((x) => ({
    depth: 10,
    width: 10,
    x,
    z,
  }))),
  width: 100,
  x: 0,
  z: 0,
};
const balancedParts = globalThis.METROPOGITS_FILTERS.aggregateParts(balancedFacility);
const balancedCenter = balancedParts.reduce((center, part) => ({
  x: center.x + part.x + part.width / 2,
  z: center.z + part.z + part.depth / 2,
}), { x: 0, z: 0 });
const nestedDistricts = [
  { depth: 240, id: "nested-root", parentId: null, width: 240, x: 0, z: 0 },
  { depth: 220, id: "frontend", parentId: "nested-root", width: 220, x: 0, z: 0 },
  { depth: 100, id: "app", parentId: "frontend", width: 100, x: 20, z: 20 },
  { depth: 60, id: "tests", parentId: "frontend", width: 100, x: 20, z: 130 },
];
const nestedBuildings = [
  ...Array.from({ length: 6 }, (_, index) => ({
    archetype: "GENERIC_BUILDING",
    depth: 6,
    districtId: "frontend",
    entityId: `frontend-${index}`,
    height: 10,
    width: 6,
    x: index % 2 ? 180 : 2,
    z: 25 + Math.floor(index / 2) * 8,
  })),
  ...Array.from({ length: 100 }, (_, index) => ({
    archetype: "GENERIC_BUILDING",
    depth: 6,
    districtId: "app",
    entityId: `app-${index}`,
    height: 10,
    width: 6,
    x: 20 + (index % 10) * 8,
    z: 20 + Math.floor(index / 10) * 8,
  })),
  ...Array.from({ length: 80 }, (_, index) => ({
    archetype: "LIBRARY",
    depth: 6,
    districtId: "tests",
    entityId: `tests-${index}`,
    height: 10,
    width: 6,
    x: 20 + (index % 10) * 8,
    z: 130 + Math.floor(index / 10) * 7,
  })),
];
const nestedTerritories = { districts: [
  { id: "frontend", rectangles: [{ depth: 220, width: 220, x: 0, z: 0 }] },
  { id: "app", rectangles: [{ depth: 100, width: 100, x: 20, z: 20 }] },
  { id: "tests", rectangles: [{ depth: 60, width: 100, x: 20, z: 130 }] },
] };
const nestedPolicy = globalThis.METROPOGITS_FILTERS.createLodPolicy(
  { buildings: nestedBuildings, districts: nestedDistricts, networks: [] },
  nestedTerritories,
);
const nestedPlots = nestedPolicy.aggregates.flatMap((facility) =>
  facility.plots.map((plot) => ({ ...plot, aggregateId: facility.id })),
);
const nestedOverlaps = nestedPlots.flatMap((left, leftIndex) =>
  nestedPlots.slice(leftIndex + 1).filter((right) =>
    left.aggregateId !== right.aggregateId
    && left.x < right.x + right.width
    && right.x < left.x + left.width
    && left.z < right.z + right.depth
    && right.z < left.z + left.depth
  )
);
process.stdout.write(JSON.stringify({
  deterministic: JSON.stringify(overview) === JSON.stringify(
    policy.visibility("overview", buildingIds, networkIds),
  ),
  districtCount: district.buildingIds.length,
  districtVisibility: {
    deepAtDetail: policy.districtVisible("deep", "detail"),
    deepAtDistrict: policy.districtVisible("deep", "district"),
    leafAtOverview: policy.districtVisible("leaf", "overview"),
    rootAtOverview: policy.districtVisible("root", "overview"),
  },
  forcedLevel: policy.levelForZoom(1, true),
  levels: [
    policy.levelForZoom(1),
    policy.levelForZoom(1.5),
    policy.levelForZoom(2.5),
  ],
  aggregate: {
    archetypeCounts: aggregate.archetypeCounts,
    blockNamespace: aggregate.id.startsWith("visual:block:"),
    facilityContained: aggregate.x >= aggregateDistrict.x
      && aggregate.z >= aggregateDistrict.z
      && aggregate.x + aggregate.width <= aggregateDistrict.x + aggregateDistrict.width
      && aggregate.z + aggregate.depth <= aggregateDistrict.z + aggregateDistrict.depth,
    facilityInOccupiedPlot: aggregate.plots.every((plot) =>
      plot.x >= aggregatePlot.x
      && plot.z >= aggregatePlot.z
      && plot.x + plot.width <= aggregatePlot.x + aggregatePlot.width
      && plot.z + plot.depth <= aggregatePlot.z + aggregatePlot.depth
    ),
    memberCount: aggregate.memberEntityIds.length,
    memberDistrictIds: aggregate.memberDistrictIds,
    partsContained: aggregateParts.every((part) =>
      aggregate.plots.some((plot) =>
        part.x >= plot.x
        && part.z >= plot.z
        && part.x + part.width <= plot.x + plot.width
        && part.z + part.depth <= plot.z + plot.depth
      )
    ),
    parts: aggregateParts.map((part) => ({
      archetype: part.archetype,
      representedCount: part.representedCount,
    })),
  },
  allMembers: {
    count: aggregateMembers.length,
    unique: new Set(aggregateMembers).size,
  },
  aggregateCounts: [overview.aggregateIds.length, district.aggregateIds.length],
  filteredAggregatesMatch: filteredOverview.aggregateIds.every((aggregateId) =>
    policy.aggregates.find((item) => item.id === aggregateId)
      .memberEntityIds.some((entityId) => filteredIds.has(entityId))
  ),
  overlapCount: overlaps.length,
  representativeSpread: {
    count: spreadParts.length,
    x: Math.max(...spreadCentersX) - Math.min(...spreadCentersX),
    z: Math.max(...spreadCentersZ) - Math.min(...spreadCentersZ),
  },
  representativeBalance: {
    count: balancedParts.length,
    x: balancedCenter.x / balancedParts.length,
    z: balancedCenter.z / balancedParts.length,
  },
  nestedMajorDistricts: {
    ids: globalThis.METROPOGITS_FILTERS.majorDistrictIds({
      buildings: nestedBuildings,
      districts: nestedDistricts,
    }),
    overlapCount: nestedOverlaps.length,
  },
  selectedAggregate: policy.visibility(
    "district",
    buildingIds,
    networkIds,
    { id: aggregate.id, kind: "aggregate" },
  ).aggregateIds,
  overviewBuildingCount: overview.buildingIds.length,
  overviewNetworks: overview.networkIds,
  detailCounts: [detail.buildingIds.length, detail.networkIds.length],
  networkCounts: [overview.networkIds.length, district.networkIds.length],
}));
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-filters.js"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result["deterministic"])
        self.assertEqual(["overview", "district", "detail"], result["levels"])
        self.assertEqual("detail", result["forcedLevel"])
        self.assertEqual([300, 64], result["detailCounts"])
        self.assertEqual([24, 64], result["networkCounts"])
        self.assertEqual([17, 0], result["aggregateCounts"])
        self.assertEqual(0, result["overviewBuildingCount"])
        self.assertGreater(result["aggregate"]["memberCount"], 1)
        self.assertLess(result["aggregate"]["memberCount"], 30)
        self.assertEqual({"count": 300, "unique": 300}, result["allMembers"])
        self.assertTrue(result["aggregate"]["blockNamespace"])
        self.assertEqual(["leaf"], result["aggregate"]["memberDistrictIds"])
        self.assertTrue(result["aggregate"]["facilityContained"])
        self.assertTrue(result["aggregate"]["facilityInOccupiedPlot"])
        self.assertTrue(result["aggregate"]["partsContained"])
        self.assertEqual(
            result["aggregate"]["memberCount"],
            sum(item["representedCount"] for item in result["aggregate"]["parts"]),
        )
        self.assertEqual(0, result["overlapCount"])
        self.assertEqual(8, result["representativeSpread"]["count"])
        self.assertGreaterEqual(result["representativeSpread"]["x"], 90)
        self.assertGreaterEqual(result["representativeSpread"]["z"], 90)
        self.assertEqual(6, result["representativeBalance"]["count"])
        self.assertGreaterEqual(result["representativeBalance"]["x"], 40)
        self.assertLessEqual(result["representativeBalance"]["x"], 60)
        self.assertGreaterEqual(result["representativeBalance"]["z"], 40)
        self.assertLessEqual(result["representativeBalance"]["z"], 60)
        self.assertEqual(["app", "tests"], result["nestedMajorDistricts"]["ids"])
        self.assertEqual(0, result["nestedMajorDistricts"]["overlapCount"])
        self.assertTrue(result["filteredAggregatesMatch"])
        self.assertEqual(1, len(result["selectedAggregate"]))
        self.assertEqual(
            [f"network-{index:03d}" for index in range(24)],
            result["overviewNetworks"],
        )
        self.assertGreaterEqual(result["districtCount"], 12)
        self.assertEqual(result["districtCount"], 300)
        self.assertEqual(
            {
                "deepAtDetail": True,
                "deepAtDistrict": False,
                "leafAtOverview": True,
                "rootAtOverview": True,
            },
            result["districtVisibility"],
        )

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_nearest_manifest_dependencies_are_labeled_as_declarations(self):
        graph = {
            "edges": [
                {
                    "evidenceIds": ["root-evidence"],
                    "from": "root-module",
                    "to": "root-package",
                    "type": "DEPENDS_ON",
                },
                {
                    "evidenceIds": ["nested-evidence"],
                    "from": "nested-module",
                    "to": "nested-package",
                    "type": "DEPENDS_ON",
                },
            ],
            "entities": [
                {"id": "file", "kind": "FILE", "path": "apps/web/src/App.java"},
                {"id": "root-module", "kind": "MODULE", "path": "pom.xml"},
                {
                    "id": "nested-module",
                    "kind": "MODULE",
                    "path": "apps/web/pom.xml",
                },
                {
                    "id": "root-package",
                    "kind": "EXTERNAL_PACKAGE",
                    "path": "maven/example/root",
                },
                {
                    "id": "nested-package",
                    "kind": "EXTERNAL_PACKAGE",
                    "path": "maven/org/postgresql/postgresql",
                },
            ],
        }
        script = """
require(process.argv[1]);
const fs = require("fs");
const graph = JSON.parse(fs.readFileSync(0, "utf8"));
const result = globalThis.METROPOGITS_FILTERS.declaredDependenciesForEntity(
  graph,
  "file",
);
process.stdout.write(JSON.stringify(result));
"""
        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(
                    Path(__file__).parents[1]
                    / "metropogits"
                    / "viewer_assets"
                    / "viewer-filters.js"
                ),
            ],
            input=json.dumps(graph),
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(
            [
                {
                    "coordinate": "org.postgresql:postgresql",
                    "ecosystem": "MAVEN",
                    "evidenceIds": ["nested-evidence"],
                }
            ],
            json.loads(completed.stdout),
        )


if __name__ == "__main__":
    unittest.main()
