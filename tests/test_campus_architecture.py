"""Purpose silhouettes on the already-certified physical footprint."""

import copy
import unittest
from pathlib import Path

from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.architecture_catalog import catalog_compounds
from metropogits.world.campus_architecture import campus_massing
from metropogits.world.geometry import inside, rectangle
from metropogits.world.export import view_data
from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world
from test_campus_estates import OPTIONS


def compound(kind, roles, width=32, depth=16, angle=0.47):
    return dict(
        id="compound:fixture",
        role="CAMPUS:" + kind,
        height=26,
        memberEntityIds=["file:a", "file:b"],
        evidenceIds=["evidence:role"],
        sourceEdgeIds=["edge:ab"],
        campusProgram=dict(
            kind=kind,
            roleCounts=roles,
            classifiedMemberCount=2,
            evidenceIds=["evidence:role"],
        ),
        physicalModel=dict(
            center=[30, -20],
            angle=angle,
            width=width,
            depth=depth,
            baseElevation=7,
            footprint=rectangle([30, -20], angle, width, depth),
        ),
    )


class CampusArchitectureTests(unittest.TestCase):
    PROGRAMS = [
        ("VALIDATION", {"TEST": 2}),
        ("DATA", {"DATA_MODEL": 2}),
        ("DATA", {"PERSISTENCE_ADAPTER": 1, "DATA_MODEL": 1}),
        ("APPLICATION", {"SERVICE": 1, "TEST": 1}),
        ("INTERFACE", {"UI_PAGE": 2}),
        ("COMPUTE", {"DATA_PROCESSOR": 2}),
        ("TOOLING", {"CLI_ENTRYPOINT": 2}),
    ]

    def test_physical_campuses_vary_real_solid_geometry_without_changing_role_proof(self):
        from metropogits.world.architecture_metrics import occupancy
        from scripts.urban_capacity_audit import rendered_models
        for kind, roles in self.PROGRAMS:
            shapes, layouts = set(), set()
            for seed in range(20):
                source = compound(kind, roles, width=48, depth=34)
                source.update(id=f'physical-complex:{seed}', physicalProgramVersion='capacity-replan/0.2')
                before = copy.deepcopy(source)
                actual = catalog_compounds([source])[0]
                models, _ = rendered_models(dict(parcels=[]), {}, [actual])
                shapes.add(occupancy(models['parcels'][0]))
                layouts.add(actual['architecture']['campusMassing']['layout'])
                self.assertEqual(source, before)
                self.assertEqual(actual['memberEntityIds'], source['memberEntityIds'])
                self.assertEqual(actual['architecture']['campusMassing']['roleEvidenceIds'], ['evidence:role'])
            self.assertGreaterEqual(len(shapes), 3, kind)
            self.assertGreaterEqual(len(layouts), 3, kind)

    def test_real_sources_keep_exact_members_routes_and_individual_meshes(self):
        graph = analyze_repository(
            Path("tests/fixtures/repositories/purpose-campus"),
            repository_id="fixture/purpose-campus",
        )
        scene = generate_city(graph)
        world = generate_world(scene, graph, **OPTIONS)
        saved = copy.deepcopy((world, scene, graph))
        validate_world(world, scene, graph)
        data = view_data(
            world, scene, graph, building_style="catalog", campus_landmarks=True
        )
        again = view_data(
            world, scene, graph, building_style="catalog", campus_landmarks=True
        )
        self.assertEqual(data, again)
        complexes = data["streets"]["roleCompounds"]
        active = [
            c for c in complexes if c.get("architecture", {}).get("campusMassing")
        ]
        self.assertEqual(len(active), 4)
        self.assertEqual(sum(len(c["memberEntityIds"]) for c in active), 28)
        evidence = {e["evidenceId"] for e in graph["evidence"]}
        self.assertTrue(
            all(
                set(c["architecture"]["campusMassing"]["roleEvidenceIds"]) <= evidence
                for c in active
            )
        )
        plain = view_data(
            world, scene, graph, building_style="purposeful", campus_landmarks=True
        )
        self.assertEqual(data["routing"]["routes"], plain["routing"]["routes"])
        self.assertEqual(
            [c["memberEntityIds"] for c in complexes],
            [c["memberEntityIds"] for c in plain["streets"]["roleCompounds"]],
        )
        self.assertEqual(saved, (world, scene, graph))

    def test_purpose_changes_large_volumes_not_just_labels_or_colour(self):
        silhouettes = []
        for kind, roles in self.PROGRAMS:
            result = catalog_compounds([compound(kind, roles)])[0]
            profile = result["architecture"]["campusMassing"]
            self.assertEqual(profile["programKind"], kind)
            self.assertTrue(profile["presentationOnly"])
            self.assertEqual(profile["roleEvidenceIds"], ["evidence:role"])
            silhouettes.append(
                [
                    (p["footprint"], p["y"], p["height"], p["primitive"])
                    for p in result["physicalModel"]["parts"]
                    if p["materialKind"] < 12
                ]
            )
        self.assertEqual(len({str(v) for v in silhouettes}), len(self.PROGRAMS))
        # Data-model evidence alone cannot select storage halls.
        self.assertEqual(
            campus_massing(compound("DATA", {"DATA_MODEL": 2}))[2]["layout"],
            "ARCHIVE_FINGERS",
        )

    def test_missing_unrelated_or_unknown_role_proof_keeps_old_neutral_geometry(self):
        for summary in (
            {},
            dict(kind="VALIDATION", roleCounts={"TEST": 2}, classifiedMemberCount=2),
            dict(
                kind="VALIDATION",
                roleCounts={"SERVICE": 2},
                classifiedMemberCount=2,
                evidenceIds=["proof"],
            ),
            dict(
                kind="COLLABORATION",
                roleCounts={},
                classifiedMemberCount=0,
                evidenceIds=["proof"],
            ),
        ):
            source = compound("COLLABORATION", {})
            source["campusProgram"] = summary
            self.assertIsNone(campus_massing(source))
            self.assertNotIn(
                "campusMassing", catalog_compounds([source])[0]["architecture"]
            )

    def test_rotated_deep_small_and_elevated_sites_preserve_certified_envelopes(self):
        for kind, roles in self.PROGRAMS:
            for width, depth in ((32, 16), (16, 32), (8, 8), (17.58, 7.98)):
                for angle in (0, 0.47, 2.7):
                    source = compound(kind, roles, width, depth, angle)
                    saved = copy.deepcopy(source)
                    result = catalog_compounds([source])[0]
                    self.assertEqual(source, saved)
                    self.assertEqual(result, catalog_compounds([source])[0])
                    for k in (
                        "id",
                        "memberEntityIds",
                        "sourceEdgeIds",
                        "evidenceIds",
                        "campusProgram",
                        "height",
                    ):
                        self.assertEqual(result[k], source[k])
                    for k, v in source["physicalModel"].items():
                        self.assertEqual(result["physicalModel"][k], v)
                    parts = result["physicalModel"]["parts"]
                    self.assertLessEqual(len(parts), 18)
                    self.assertLessEqual(
                        sum(len(p.get("meshFaces", [])) for p in parts), 240
                    )
                    for p in parts:
                        self.assertGreaterEqual(p["y"], 7)
                        self.assertLessEqual(p["y"] + p["height"], 33.0003)
                        self.assertTrue(
                            all(
                                inside(v, source["physicalModel"]["footprint"], -0.0004)
                                for v in p["footprint"]
                            )
                        )
                        for face in p.get("meshFaces", []):
                            for x, y, z in face["points"]:
                                self.assertTrue(7 <= y <= 33.0003)
                                self.assertTrue(
                                    inside(
                                        [x, z],
                                        source["physicalModel"]["footprint"],
                                        -0.0004,
                                    )
                                )

    def test_frontage_dressing_is_on_real_ground_wall_after_axis_adaptation(self):
        for kind, roles in self.PROGRAMS:
            for width, depth in ((32, 16), (16, 32)):
                source = compound(kind, roles, width, depth)
                specs, _, _ = campus_massing(source)
                result = catalog_compounds([source])[0]
                detail = result["architecture"]["frontageDetail"]
                self.assertIsNotNone(detail)
                self.assertEqual(detail["frontageAxis"], "LOCAL_POSITIVE_Z")
                self.assertGreater(len(result["physicalModel"]["parts"]), len(specs))


if __name__ == "__main__":
    unittest.main()
