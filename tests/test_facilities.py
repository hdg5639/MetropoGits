"""A real source-to-facility slice, not handcrafted City role metadata."""

import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.building_forms import building_parts
from metropogits.cli import analyze_repository
from metropogits.facilities import FACILITY_MODELS
from metropogits.layout import generate_city, ROLE_STYLES
from metropogits.preview import render_preview
from metropogits.viewer import render_viewer
from scripts.validate_city import validate_document

FIXTURE = Path(__file__).parent / "fixtures/repositories/polyglot-facilities"


class FacilityTests(unittest.TestCase):
    def test_source_roles_create_all_eleven_facilities_without_inventing_entities(self):
        graph = analyze_repository(FIXTURE, "fixture/facilities")
        original = copy.deepcopy(graph)
        scene = generate_city(graph)
        entities = {e["id"]: e for e in graph["entities"] if e["kind"] == "FILE"}
        self.assertEqual(set(entities), {b["entityId"] for b in scene["buildings"]})
        self.assertEqual(
            set(FACILITY_MODELS),
            {b["archetype"] for b in scene["buildings"]} - {"GENERIC_BUILDING"},
        )
        proofs = {e["evidenceId"]: e for e in graph["evidence"]}
        for building in scene["buildings"]:
            if building["archetype"] not in FACILITY_MODELS:
                continue
            model = FACILITY_MODELS[building["archetype"]]
            role = next(
                r
                for r in entities[building["entityId"]]["roles"]
                if r["value"] == model["role"]
            )
            self.assertTrue(role["evidenceIds"])
            self.assertTrue(
                all(
                    proofs[e]["sourcePath"] == entities[building["entityId"]]["path"]
                    for e in role["evidenceIds"]
                )
            )
        self.assertEqual(original, graph)
        self.assertEqual(validate_document(scene, graph), [])
        self.assertEqual(scene, generate_city(graph))
        data = render_viewer(scene, graph)["assets/viewer-data.js"]
        for name in FACILITY_MODELS:
            self.assertIn(name.encode(), data)
            self.assertIn(
                ('data-roof-form="' + name + '"').encode(), render_preview(scene, graph)
            )

    def test_forms_are_distinct_bounded_and_do_not_change_file_envelopes(self):
        signatures = set()
        for name in FACILITY_MODELS:
            building = dict(
                entityId="actual:file",
                archetype=name,
                x=10,
                z=-20,
                width=6,
                depth=8,
                height=18,
            )
            original = copy.deepcopy(building)
            parts = building_parts(building)
            signatures.add(tuple(tuple(p.values()) for p in parts))
            self.assertLessEqual(len(parts), 6)
            for p in parts:
                self.assertGreater(p["width"], 0)
                self.assertGreater(p["height"], 0)
                self.assertGreater(p["depth"], 0)
                for axis, extent in [("x", "width"), ("z", "depth")]:
                    self.assertGreaterEqual(p[axis], building[axis])
                    self.assertLessEqual(
                        p[axis] + p[extent], building[axis] + building[extent] + 1e-9
                    )
                self.assertLessEqual(p["y"] + p["height"], building["height"] + 1e-9)
            self.assertEqual(building, original)
        self.assertEqual(len(signatures), 11)
        self.assertEqual(ROLE_STYLES["ENTRYPOINT"][0], "GATE")
        self.assertEqual(ROLE_STYLES["TEST"][0], "LIBRARY")

    def test_inbound_api_geometry_preserves_previous_port_envelope(self):
        graph = analyze_repository(FIXTURE, "fixture/facilities")
        current = generate_city(graph)
        with patch.dict(ROLE_STYLES, {"API_ENDPOINT": ("PORT", 15)}):
            previous = generate_city(graph)
        for old, new in zip(previous["buildings"], current["buildings"]):
            self.assertEqual(
                {k: v for k, v in old.items() if k != "archetype"},
                {k: v for k, v in new.items() if k != "archetype"},
            )
