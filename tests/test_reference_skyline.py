import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.architecture_catalog import catalog_world, compile_parts, grammar
from metropogits.world.skyline import reference_centers, skyline_massing
from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world


def fixture():
    ids = [f"file:{i}" for i in range(10)]
    world = dict(
        seed="fixed",
        parcels=[
            dict(
                entityId=k,
                districtId="owner",
                center=[(i % 5) * 8, (i // 5) * 8],
                width=6,
                depth=6,
                height=16,
                angle=0.63,
                archetype="GENERIC_BUILDING",
            )
            for i, k in enumerate(ids)
        ],
    )
    graph = dict(
        entities=[
            dict(id=k, path=f"src/{i}.py", kind="FILE") for i, k in enumerate(ids)
        ],
        evidence=[dict(evidenceId=f"ev:{i}", kind="IMPORT") for i in range(1, 10)],
        edges=[
            dict(
                id=f"edge:{i}",
                type="IMPORTS",
                confidence="DIRECT",
                **{"from": k, "to": ids[0], "evidenceIds": [f"ev:{i}"]},
            )
            for i, k in enumerate(ids[1:], 1)
        ],
    )
    return world, graph, ids


class ReferenceSkylineTests(unittest.TestCase):
    def test_real_python_library_gets_a_center_without_becoming_a_business_service(
        self,
    ):
        graph = analyze_repository(
            Path("tests/fixtures/repositories/reference-center"),
            repository_id="fixture/reference-center",
        )
        scene = generate_city(graph)
        world = generate_world(
            scene,
            graph,
            seed="reference-center",
            zoning="neighborhoods",
            pattern_scale="adaptive",
            planning="varied",
            outline="varied",
            street_policy="porous",
            street_hierarchy=True,
        )
        validate_world(world, scene, graph)
        saved = copy.deepcopy((world, scene, graph))
        _, profiles = catalog_world(world, graph)
        cores = [
            (k, p)
            for k, p in profiles.items()
            if p.get("skyline", {}).get("tier") == "CORE"
        ]
        self.assertEqual(len(cores), 1)
        self.assertTrue(cores[0][0].endswith("app/shared.py"))
        self.assertEqual(cores[0][1]["skyline"]["centerIncomingFiles"], 10)
        self.assertTrue(all(p["verifiedRole"] is None for p in profiles.values()))
        self.assertEqual(saved, (world, scene, graph))

    def test_one_static_hub_distinct_file_counts_and_no_fabricated_roles(self):
        world, graph, ids = fixture()
        # Duplicate observations/symbol edges must not inflate incoming files.
        graph["edges"] += copy.deepcopy(graph["edges"])
        saved = copy.deepcopy((world, graph))
        plan = reference_centers(world, graph, ids)
        self.assertEqual(plan[ids[0]]["tier"], "CORE")
        self.assertEqual(plan[ids[0]]["centerIncomingFiles"], 9)
        self.assertEqual({p["centerEntityId"] for p in plan.values()}, {ids[0]})
        self.assertEqual(
            {p["tier"] for k, p in plan.items() if k != ids[0]}, {"LINKED"}
        )
        self.assertEqual(saved, (world, graph))
        styled, profiles = catalog_world(world, graph)
        self.assertTrue(
            all(
                not p["verifiedRole"] and not p["roleEvidenceIds"]
                for p in profiles.values()
            )
        )
        self.assertTrue(all(p["family"] == "generic" for p in profiles.values()))
        self.assertEqual(styled, catalog_world(world, graph)[0])
        self.assertGreater(
            profiles[ids[0]]["renderedHeight"], profiles[ids[1]]["renderedHeight"]
        )

    def test_unknown_unresolved_manifest_or_sparse_input_does_not_invent_a_center(self):
        for confidence, edge_type in (
            ("INFERRED", "IMPORTS"),
            ("UNKNOWN", "IMPORTS"),
            ("DIRECT", "DEPENDS_ON"),
        ):
            w, g, ids = fixture()
            for edge in g["edges"]:
                edge.update(confidence=confidence, type=edge_type)
            self.assertEqual(reference_centers(w, g, ids), {})
        w, g, ids = fixture()
        self.assertEqual(reference_centers(w, dict(g, edges=[]), ids), {})
        self.assertEqual(reference_centers(w, g, ids[:7]), {})
        w["campusPlan"] = dict(sites=[dict(memberEntityIds=ids)])
        self.assertEqual(reference_centers(w, g, ids), {})

    def test_owners_and_spatial_context_are_not_new_graph_relations(self):
        w, g, ids = fixture()
        g["edges"] = g["edges"][:7]
        plan = reference_centers(w, g, ids)
        self.assertEqual(plan[ids[-1]]["tier"], "CONTEXT")
        self.assertTrue(plan[ids[-1]]["contextIsNotARelationship"])
        self.assertEqual(plan[ids[-1]]["relationEvidenceIds"], [])
        w["parcels"][-1]["districtId"] = "other"
        self.assertNotIn(ids[-1], reference_centers(w, g, ids))
        w["parcels"][-1]["center"] = [500, 500]
        before = reference_centers(w, g, ids)
        g["entities"].append(
            dict(id="unrelated", path="elsewhere.unknown", kind="FILE")
        )
        g["entities"].reverse()
        g["edges"].reverse()
        w["parcels"].reverse()
        self.assertEqual(before, reference_centers(w, g, reversed(ids)))

    def test_masses_never_expand_the_original_rotated_physical_height_capacity(self):
        w, g, ids = fixture()
        plan = reference_centers(w, g, ids)
        with patch("metropogits.world.skyline.MAX_WORK", 1):
            with self.assertRaisesRegex(
                ValueError, "reference skyline spatial work limit"
            ):
                reference_centers(w, g, ids)
        for tier in ("CORE", "LINKED", "CONTEXT"):
            for width, depth, height in ((6, 6, 16), (2, 3, 40), (20, 12, 9)):
                source = dict(w["parcels"][0], width=width, depth=depth, height=height)
                specs, budget, profile = skyline_massing(
                    dict(plan[ids[0]], tier=tier), source, grammar("bar")
                )
                self.assertLessEqual(budget, height)
                self.assertEqual(profile["tier"], tier)
                parts = compile_parts(dict(source, height=budget), specs)
                self.assertTrue(
                    all(p["y"] + p["height"] <= height + 0.0003 for p in parts)
                )
                self.assertLessEqual(len(parts), 18)


if __name__ == "__main__":
    unittest.main()
