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
        self.assertIn("Content-Security-Policy", html)
        self.assertIn('data-filter="role"', html)
        self.assertIn('data-filter="confidence"', html)
        self.assertIn('id="synthetic-activity"', html)
        self.assertIn("not measured runtime traffic", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("fetch(", first["assets/viewer.js"].decode("utf-8"))

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
  "CACHE_TOWER", "EXCHANGE", "PORT", "CONTROL_CENTER",
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
        self.assertEqual(8, len({json.dumps(parts, sort_keys=True) for parts in forms.values()}))
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
  { id: "root", parentId: null },
  { id: "app", parentId: "root" },
  { id: "leaf", parentId: "app" },
  { id: "deep", parentId: "leaf" },
];
const buildings = Array.from({ length: 300 }, (_, index) => ({
  archetype: index < 12 ? "SERVICE_OFFICE" : "GENERIC_BUILDING",
  districtId: "leaf",
  entityId: `building-${index}`,
}));
const networks = Array.from({ length: 100 }, (_, index) => ({
  edgeIds: Array.from({ length: 100 - index }, (_, edge) => `edge-${index}-${edge}`),
  id: `network-${String(index).padStart(3, "0")}`,
}));
const policy = globalThis.METROPOGITS_FILTERS.createLodPolicy({
  buildings,
  districts,
  networks,
});
const buildingIds = buildings.map((building) => building.entityId);
const networkIds = networks.map((network) => network.id);
const overview = policy.visibility("overview", buildingIds, networkIds);
const district = policy.visibility("district", buildingIds, networkIds);
const detail = policy.visibility("detail", buildingIds, networkIds);
const aggregate = policy.aggregates[0];
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
    memberCount: aggregate.memberEntityIds.length,
    membersAreUnique: new Set(aggregate.memberEntityIds).size === buildingIds.length,
  },
  aggregateCounts: [overview.aggregateIds.length, district.aggregateIds.length],
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
        result = json.loads(completed.stdout)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertTrue(result["deterministic"])
        self.assertEqual(["overview", "district", "detail"], result["levels"])
        self.assertEqual("detail", result["forcedLevel"])
        self.assertEqual([300, 100], result["detailCounts"])
        self.assertEqual([24, 64], result["networkCounts"])
        self.assertEqual([1, 0], result["aggregateCounts"])
        self.assertEqual(0, result["overviewBuildingCount"])
        self.assertEqual(300, result["aggregate"]["memberCount"])
        self.assertTrue(result["aggregate"]["membersAreUnique"])
        self.assertEqual(
            [
                {"archetype": "GENERIC_BUILDING", "count": 288},
                {"archetype": "SERVICE_OFFICE", "count": 12},
            ],
            result["aggregate"]["archetypeCounts"],
        )
        self.assertEqual(1, len(result["selectedAggregate"]))
        self.assertEqual(
            [f"network-{index:03d}" for index in range(24)],
            result["overviewNetworks"],
        )
        self.assertGreaterEqual(result["districtCount"], 12)
        self.assertLess(result["districtCount"], 300)
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
