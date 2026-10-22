import copy
import tempfile
import unittest
from pathlib import Path

from metropogits.street_diagonals import overlap
from metropogits.world.compounds import derive_compounds
from metropogits.world.geometry import inside, ribbon, rectangle
from metropogits.world.generator import generate_world
from metropogits.world.export import package_world, view_data
from metropogits.world.validation import validate_world
from test_world_compounds import compact
from test_world_campus import fixture
from test_world_campus_neighborhood import OPTIONS


def campus(shared=False):
    w, g = compact()
    ids = [p["entityId"] for p in w["parcels"]]
    zone = dict(
        id="d",
        parentId="d",
        polygon=w["districts"][0]["polygon"],
        memberEntityIds=ids,
        memberClaims=[
            dict(
                entityId=k,
                roles=[dict(value="TEST", confidence="DIRECT", evidenceIds=["ev"])],
            )
            for k in ids
        ],
    )
    w["zoning"] = dict(zones=[zone])
    w["campusPlan"] = dict(sites=[dict(zoneId="d", memberEntityIds=ids, courts=[])])
    g["edges"] = [
        dict(
            id="edge:" + k,
            type="REFERENCES",
            confidence="DIRECT",
            evidenceIds=["ev"],
            **{"from": k, "to": "external-target" if shared else "f00"},
        )
        for k in ids
        if k != "f00"
    ]
    if shared:
        g["entities"].append(dict(id="external-target", kind="FILE", path="target.ts"))
    return w, g


class CampusLandmarkTests(unittest.TestCase):
    def test_related_actual_files_form_large_persistent_complex_with_exact_proof(self):
        w, g = campus()
        before = copy.deepcopy((w, g))
        fs, note = derive_compounds(w, g, campus_landmarks=True)
        landmark = [f for f in fs if f.get("campusProgram")]
        self.assertEqual(len(landmark), 1)
        f = landmark[0]
        self.assertEqual(
            f["memberEntityIds"], sorted(p["entityId"] for p in w["parcels"])
        )
        self.assertEqual(f["campusProgram"]["kind"], "VALIDATION")
        self.assertEqual(f["sourceEdgeIds"], sorted(e["id"] for e in g["edges"]))
        self.assertGreater(
            f["physicalModel"]["width"] * f["physicalModel"]["depth"], 400
        )
        self.assertLessEqual(f["height"], 36)
        self.assertTrue(
            all(
                inside(v, f["physicalModel"]["footprint"], -0.001)
                for part in f["physicalModel"]["parts"]
                for v in part["footprint"]
            )
        )
        self.assertEqual(before, (w, g))
        self.assertEqual((fs, note), derive_compounds(w, g, campus_landmarks=True))
        w["parcels"].reverse()
        g["entities"].reverse()
        g["edges"].reverse()
        self.assertEqual(fs, derive_compounds(w, g, campus_landmarks=True)[0])

    def test_shared_target_affinity_preserves_original_edges_not_a_fake_peer_link(self):
        w, g = campus(shared=True)
        f = next(
            f
            for f in derive_compounds(w, g, campus_landmarks=True)[0]
            if f.get("campusProgram")
        )
        self.assertEqual(f["sharedTargetIds"], ["external-target"])
        self.assertNotIn("external-target", f["memberEntityIds"])
        self.assertEqual(
            set(f["sourceEdgeIds"]),
            {e["id"] for e in g["edges"] if e["from"] in f["memberEntityIds"]},
        )
        self.assertTrue(all(e["to"] == "external-target" for e in g["edges"]))
        g["edges"] = []
        self.assertFalse(
            any(
                f.get("campusProgram")
                for f in derive_compounds(w, g, campus_landmarks=True)[0]
            )
        )

    def test_public_roads_other_files_nature_and_courts_remain_clear(self):
        w, g = campus()
        street = dict(id="public", start=[4, -40], end=[4, 70], width=3, access=False)
        w["streets"] = [street]
        for f in derive_compounds(w, g, campus_landmarks=True)[0]:
            self.assertFalse(
                overlap(
                    f["physicalModel"]["footprint"],
                    ribbon(street["start"], street["end"], 3),
                )
            )
        # Existing no-evidence role compounds remain unchanged when opt-in is off.
        before = derive_compounds(w, g)
        self.assertEqual(before, derive_compounds(w, g, campus_landmarks=False))
        for kind in ("nature", "court", "unrelated"):
            w, g = campus()
            if kind == "unrelated":
                blocker = w["parcels"][5]
                blocker["archetype"] = "GENERIC_BUILDING"
                w["campusPlan"]["sites"][0]["memberEntityIds"].remove(
                    blocker["entityId"]
                )
                protected = blocker["parcel"]
            else:
                protected = rectangle([9, 12], 0, 8, 8)
                if kind == "nature":
                    w["terrain"] = dict(features=[dict(noBuildPolygon=protected)])
                else:
                    w["campusPlan"]["sites"][0]["courts"] = [dict(polygon=protected)]
            for f in derive_compounds(w, g, campus_landmarks=True)[0]:
                self.assertFalse(
                    overlap(f["physicalModel"]["footprint"], protected), kind
                )

    def test_module_ownership_and_bounded_safe_fallback_are_preserved(self):
        from unittest.mock import patch

        w, g = campus()
        for i, e in enumerate(g["entities"]):
            e["path"] = ("a" if i < 8 else "b") + "/" + e["path"]
        g["entities"] += [dict(id=k, kind="MODULE", path=k) for k in ("a", "b")]
        paths = {
            e["id"]: e["path"].split("/")[0]
            for e in g["entities"]
            if e["kind"] == "FILE"
        }
        for f in derive_compounds(w, g, campus_landmarks=True)[0]:
            self.assertEqual(len({paths[k] for k in f["memberEntityIds"]}), 1)
        with patch("metropogits.world.compounds.MAX_CHECKS", 0):
            fs, note = derive_compounds(*campus(), campus_landmarks=True)
            self.assertEqual(fs, [])
            self.assertIn("limit", note["fallback"])
        with patch("metropogits.world.campus_landmarks.MAX_AFFINITY_WORK", 0):
            fs, note = derive_compounds(*campus(shared=True), campus_landmarks=True)
            self.assertEqual(fs, [])
            self.assertIn("affinity work limit", note["fallback"])

    def test_real_pipeline_export_keeps_world_graph_and_trips_identical(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory))
        w = generate_world(scene, graph, **dict(OPTIONS, campus_style="programmed"))
        validation = validate_world(w, scene, graph)
        a = package_world(w, scene, graph, validation, building_style="purposeful")
        b = package_world(
            w,
            scene,
            graph,
            validation,
            building_style="purposeful",
            campus_landmarks=True,
        )
        for key in (
            "world.json",
            "city.json",
            "graph.ucg.json",
            "planning.json",
            "validation.json",
        ):
            self.assertEqual(a[key], b[key])
        data = view_data(
            w, scene, graph, building_style="purposeful", campus_landmarks=True
        )
        self.assertEqual(data["routing"]["routes"], w["routing"]["routes"])
        self.assertEqual(
            b,
            package_world(
                w,
                scene,
                graph,
                validation,
                building_style="purposeful",
                campus_landmarks=True,
            ),
        )
        with self.assertRaises(ValueError):
            view_data(w, scene, graph, role_compounds=False, campus_landmarks=True)
