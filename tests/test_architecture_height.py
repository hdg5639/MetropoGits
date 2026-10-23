import copy
import unittest
from pathlib import Path

from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.architecture_catalog import catalog_world, CATALOG, select
from metropogits.world.architecture_height import (
    RATIOS,
    height_capacity,
    validate_architectural_heights,
)
from metropogits.world.export import view_data, package_world
from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world
from test_reference_skyline import fixture


class ArchitecturalHeightTests(unittest.TestCase):
    def test_ten_is_not_a_ceiling_or_replaced_with_another_universal_ceiling(self):
        source = dict(width=6, depth=6, height=10)
        self.assertEqual(height_capacity(source, "tower"), 54)
        self.assertEqual(
            height_capacity(dict(source, width=20, depth=20), "tower"), 180
        )
        for form in RATIOS:
            self.assertEqual(
                height_capacity(source, form),
                height_capacity(dict(source, height=1_000_000), form),
            )
        for recipe in CATALOG.values():
            self.assertIn(recipe["grammar"], RATIOS)
        for bad in (0, -2, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                height_capacity(dict(source, width=bad), "tower")

    def test_import_counts_and_unclassified_names_do_not_assign_skyscraper_heights(
        self,
    ):
        w, g, _ = fixture()
        a, p = catalog_world(w, g)
        b, _ = catalog_world(w, dict(g, edges=[]))
        self.assertEqual(a["parcels"], b["parcels"])
        self.assertTrue(
            all("skyline" not in v and not v["verifiedRole"] for v in p.values())
        )
        service = dict(
            roles=[dict(value="SERVICE", confidence="DIRECT", evidenceIds=["e"])]
        )
        self.assertEqual(
            select(service, dict(incoming=0), "stable", {"e": dict(kind="AST")})[0],
            select(service, dict(incoming=900), "stable", {"e": dict(kind="AST")})[0],
        )

    def test_independent_validation_rejects_forged_capacity_mesh_and_source_geometry(
        self,
    ):
        w, g, _ = fixture()
        styled, profiles = catalog_world(w, g)
        validate_architectural_heights(w, styled, profiles, g)
        for change in ("capacity", "form", "part", "mesh", "geography", "allocation"):
            bad, p = copy.deepcopy(styled), copy.deepcopy(profiles)
            model = bad["parcels"][0]
            profile = p[model["entityId"]]
            if change == "capacity":
                model["height"] *= 2
            if change == "form":
                profile["heightPolicy"]["form"] = "unknown"
            if change == "part":
                model["parts"][0]["height"] = model["height"] + 1
            if change == "mesh":
                model["parts"][0]["meshFaces"] = [
                    dict(points=[[0, model["height"] + 1, 0]])
                ]
            if change == "geography":
                model["center"][0] += 1
            if change == "allocation":
                profile["heightAllocation"]["fieldIntensity"] = 1
            with self.assertRaises(ValueError):
                validate_architectural_heights(w, bad, p, g)

    def test_real_world_keeps_canonical_height_but_all_render_targets_use_physical_capacity(
        self,
    ):
        g = analyze_repository(
            Path("tests/fixtures/repositories/reference-center"),
            repository_id="fixture/reference-center",
        )
        s = generate_city(g)
        w = generate_world(
            s, g, seed="height-policy", zoning="neighborhoods", pattern_scale="adaptive"
        )
        saved = copy.deepcopy((w, s, g))
        valid = validate_world(w, s, g)
        styled, profiles = catalog_world(w, g)
        self.assertTrue(any(v["renderedHeight"] > 10 for v in profiles.values()))
        self.assertTrue(all(v["sourceHeight"] == 10 for v in profiles.values()))
        data = view_data(w, s, g, building_style="catalog", campus_landmarks=True)
        self.assertEqual(data["scene"]["schemaVersion"], "world-view/0.2")
        heights = {p["entityId"]: p["height"] for p in styled["parcels"]}
        self.assertEqual(
            {b["entityId"]: b["height"] for b in data["scene"]["buildings"]}, heights
        )
        self.assertEqual(data["canonicalScene"], s)
        for k, m in data["routing"]["parcelPlan"]["buildings"].items():
            self.assertEqual(m["height"], heights[k])
            self.assertEqual(m["sourceHeight"], 10)
        a = package_world(
            w, s, g, valid, building_style="catalog", campus_landmarks=True
        )
        self.assertEqual(
            a,
            package_world(
                w, s, g, valid, building_style="catalog", campus_landmarks=True
            ),
        )
        old = package_world(
            w, s, g, valid, building_style="semantic", campus_landmarks=True
        )
        for name in ("world.json", "city.json", "graph.ucg.json", "planning.json"):
            self.assertEqual(a[name], old[name])
        self.assertIn(b"physicalHeightPolicyVersion", a["manifest.json"])
        self.assertNotEqual(a["showcase.svg"], old["showcase.svg"])
        self.assertEqual(saved, (w, s, g))
        for name in ("viewer.js", "viewer-3d.js"):
            text = Path("metropogits/viewer_assets", name).read_text(encoding="utf8")
            self.assertIn("if(program.heightPolicy)", text)
            self.assertIn("Legacy source-scene height", text)
            self.assertIn("inside derived architectural capacity", text)
            self.assertIn("District height allocation", text)
            self.assertIn("not a constructed master plan", text)


if __name__ == "__main__":
    unittest.main()
