"""Architectural styling is deterministic, shared and geometry-neutral."""

import copy
import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from metropogits.world.export import package_world, render_svg, view_data
from metropogits.world.generator import generate_world
from metropogits.world.materials import PALETTES, REGIONS, palette_for, part_material, policy, stable_index
from metropogits.world.validation import validate_world
from test_world_campus import fixture


class MaterialTests(unittest.TestCase):
    def test_roles_do_not_select_wall_material_and_only_top_roofs_get_accents(self):
        part = dict(y=0, height=10)
        for identity in ("file/a", "한글/🌆.ts", "unknown.rs"):
            generic = dict(entityId=identity, archetype="GENERIC_BUILDING")
            before = part_material(generic, part, 10)
            self.assertIn(before["wall"], [p[0] for p in PALETTES])
            for role in policy()["roleColors"]:
                b = dict(generic, archetype=role)
                result = part_material(b, part, 10)
                self.assertEqual(before["wall"], result["wall"])
                if role != "GENERIC_BUILDING":
                    self.assertNotEqual(before["roof"], result["roof"])
                self.assertEqual(before, part_material(b, part, 20))
                full = part_material(b, part, 10, True)
                self.assertEqual(full["wall"], policy()["roleColors"][role])
                self.assertEqual(full["roof"], full["wall"])
            self.assertEqual(before, part_material(dict(generic, archetype="UNKNOWN_TECH"), part, 10))
        self.assertGreater(len({stable_index(str(i), len(PALETTES)) for i in range(40)}), 4)

    def test_quarter_regions_vary_by_neighbourhood_and_keep_the_legacy_fallback(self):
        self.assertTrue(all(0 <= index < len(PALETTES) for region in REGIONS for index in region))
        part = dict(y=0, height=10)
        # No neighbourhood id: the original whole-palette choice is unchanged.
        plain = dict(entityId="file/a", archetype="GENERIC_BUILDING")
        self.assertEqual(palette_for(plain), PALETTES[stable_index("file/a", len(PALETTES))])
        quarters = {}
        for quarter in (f"zone/{i}" for i in range(60)):
            walls = {palette_for(dict(entityId=f"{quarter}/f{n}", zoneId=quarter))[0] for n in range(30)}
            region = REGIONS[stable_index(quarter, len(REGIONS))]
            self.assertTrue(walls <= {PALETTES[i][0] for i in region})
            quarters[quarter] = region
        # Different quarters pick different styles, so a city is not one uniform mix.
        self.assertGreaterEqual(len({tuple(r) for r in quarters.values()}), len(REGIONS) - 1)
        # zoneId wins over the source districtId, matching the viewer's district field.
        both = dict(entityId="x", zoneId="zone/1", districtId="src/other")
        self.assertEqual(palette_for(both), palette_for(dict(entityId="x", districtId="zone/1")))
        # Roles still never choose the wall.
        for role in policy()["roleColors"]:
            self.assertEqual(part_material(dict(both, archetype=role), part, 10)["wall"],
                             part_material(dict(both, archetype="GENERIC_BUILDING"), part, 10)["wall"])

    @unittest.skipUnless(shutil.which("node"), "Node is required for renderer parity")
    def test_viewer_matches_python_for_quarter_regions(self):
        cases = [[dict(entityId=f"{q}/{n}", archetype="SERVICE_OFFICE", **{key: q}), dict(y=0, height=8), 8, False]
                 for q in ("zone/a", "한글/구역", "src/main") for n in range(6) for key in ("zoneId", "districtId")]
        module = (Path(__file__).parents[1] / "metropogits/viewer_assets/viewer-filters.js").as_uri()
        code = f"import {json.dumps(module)};let input='';for await(const c of process.stdin)input+=c;const d=JSON.parse(input);console.log(JSON.stringify(d.cases.map(c=>METROPOGITS_FILTERS.materialPart(d.policy,...c))));"
        result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", code],
                                input=json.dumps(dict(policy=policy(), cases=cases)), text=True,
                                capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), [part_material(*c) for c in cases])

    @unittest.skipUnless(shutil.which("node"), "Node is required for renderer parity")
    def test_python_and_viewer_match_unicode_shading_top_accents_and_full_tint(self):
        cases = []
        for identity in ("file/a", "한글/🌆.ts", "café.rs"):
            for role in (*policy()["roleColors"], "UNKNOWN_TECH"):
                for shade in (0, .08, .28):
                    for top in (10, 20):
                        for strong in (False, True):
                            cases.append([dict(entityId=identity, archetype=role), dict(y=2, height=8, shade=shade), top, strong])
        for kind in (12, 13, 14):
            for strong in (False, True):
                cases.append([dict(entityId="entrance", archetype="SERVICE_OFFICE"),
                              dict(y=0, height=2, materialKind=kind), 10, strong])
        module = (Path(__file__).parents[1] / "metropogits/viewer_assets/viewer-filters.js").as_uri()
        code = f"import {json.dumps(module)};let input='';for await(const c of process.stdin)input+=c;const d=JSON.parse(input);console.log(JSON.stringify(d.cases.map(c=>METROPOGITS_FILTERS.materialPart(d.policy,...c))));"
        result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", code],
                                input=json.dumps(dict(policy=policy(), cases=cases)), text=True,
                                capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), [part_material(*c) for c in cases])

    def test_package_changes_only_presentation_and_cpu_faces_keep_exact_source_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory), count=4)
        world = generate_world(scene, graph, seed="material-fixture")
        saved = copy.deepcopy((world, scene, graph))
        validation = validate_world(world, scene, graph)
        before = package_world(world, scene, graph, validation)
        self.assertEqual(before, package_world(world, scene, graph, validation, building_style="semantic"))
        after = package_world(world, scene, graph, validation, building_style="architectural")
        self.assertEqual(after, package_world(world, scene, graph, validation, building_style="architectural"))
        self.assertEqual(saved, (world, scene, graph))
        for name in ("world.json", "city.json", "graph.ucg.json", "validation.json"):
            self.assertEqual(before[name], after[name])
        semantic = view_data(world, scene, graph)
        architectural = view_data(world, scene, graph, building_style="architectural")
        self.assertEqual(architectural.pop("buildingMaterials"), policy())
        self.assertEqual(semantic, architectural)
        self.assertIn(b'Walls: procedural / Roof accents: roles', after["index.html"])
        self.assertNotIn(b'data-action="toggle-role-colors"', before["index.html"])
        self.assertIn(b'data-action="toggle-role-colors"', after["index.html"])
        self.assertEqual(json.loads(after["manifest.json"])["options"]["buildingStyle"], "architectural")
        def faces(svg):
            return [(e.attrib["data-entity-id"], e.attrib["points"])
                    for e in ET.fromstring(svg).iter() if "data-entity-id" in e.attrib]
        self.assertEqual(faces(before["preview.svg"]), faces(after["preview.svg"]))
        self.assertNotEqual(before["preview.svg"], after["preview.svg"])
        self.assertIn(b'Procedural walls / role roof accents', after["preview.svg"])
        for function, args in ((view_data, (world, scene, graph)), (render_svg, (world,)),
                               (package_world, (world, scene, graph, validation))):
            with self.assertRaisesRegex(ValueError, "presentation style"):
                function(*args, building_style="unsupported")
