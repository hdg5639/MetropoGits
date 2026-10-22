import copy
import math
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.architecture_catalog import CATALOG, compile_parts
from metropogits.world.compounds import derive_compounds
from metropogits.world.export import package_world, view_data
from metropogits.world.generator import generate_world
from metropogits.world.geometry import inside, nearest, rectangle
from metropogits.world.modern_massing import modern_grammar
from metropogits.world.urban_architecture import urban_world
from metropogits.world.urban_land import admit_land, validate_land
from metropogits.world.validation import validate_world


def land_fixture(angle=0):
    c, s = math.cos(angle), math.sin(angle)
    def at(x, z):
        return [c*x-s*z, s*x+c*z]
    parcels = []
    for i in range(2):
        center = at(i*24, 0)
        parcels.append(dict(entityId=f"file:{i}", districtId="owner", sourceDistrictId="owner",
                            center=center, angle=angle, width=6, depth=6, height=10,
                            footprint=rectangle(center, angle, 6, 6), parcel=rectangle(center, angle, 8, 8),
                            entrance=at(i*24, 3), streetPoint=at(i*24, 5),
                            archetype="GENERIC_BUILDING", evidenceIds=[], styleVariant="default", parts=[]))
    world = dict(seed="fixed", parcels=parcels, districts=[dict(id="owner", polygon=rectangle([0,0],0,200,200))],
                 streets=[dict(id="road", start=at(-40,5), end=at(60,5), width=2, access=False)] +
                         [dict(id=f"access:{i}",start=p["entrance"],end=p["streetPoint"],width=1,access=True)
                          for i,p in enumerate(parcels)])
    graph = dict(repository=dict(id="repo"), entities=[dict(id=f"file:{i}",kind="FILE",path=f"app/{i}.py",
                       roles=[dict(value="SERVICE", confidence="DIRECT", evidenceIds=["proof"])]) for i in range(2)],
                 evidence=[dict(evidenceId="proof",kind="AST")], edges=[])
    return world, graph


class UrbanArchitectureTests(unittest.TestCase):
    def test_complete_variable_land_requests_preserve_frontage_at_multiple_yaws(self):
        for angle in (0, .37, 1.2, -2.1):
            w,g = land_fixture(angle)
            saved = copy.deepcopy((w,g))
            physical,plan = admit_land(w,g,[])
            self.assertEqual(plan["counts"], {"ADMITTED":2})
            validate_land(w,physical,g,[],plan)
            for before,after in zip(w["parcels"],physical["parcels"]):
                self.assertEqual((after["width"],after["depth"]),(12,10))
                self.assertEqual(after["entrance"],before["entrance"])
                self.assertEqual(after["streetPoint"],before["streetPoint"])
                self.assertTrue(all(inside(p,after["footprint"],-.001) for p in before["footprint"]))
                self.assertLess(min(math.dist(after["entrance"],nearest(after["entrance"],a,b))
                                    for a,b in zip(after["footprint"],after["footprint"][1:]+after["footprint"][:1])),.001)
            self.assertEqual(saved,(w,g))

    def test_nature_courts_roads_and_certified_complexes_are_not_consumed(self):
        for kind in ("terrain", "road", "court", "complex"):
            w,g = land_fixture()
            compounds = []
            obstruction = rectangle([12,-4],0,80,4)
            if kind == "terrain":
                w["terrain"] = dict(features=[dict(id="lake",noBuildPolygon=obstruction)])
            if kind == "road":
                w["streets"].append(dict(id="rear",start=[-30,-4],end=[55,-4],width=4,access=False))
            if kind == "court":
                w["campusPlan"] = dict(sites=[dict(memberEntityIds=[],courts=[dict(id="court",polygon=obstruction)])])
            if kind == "complex":
                compounds = [dict(id="complex",memberEntityIds=["file:0","file:1"],physicalModel=dict(footprint=obstruction))]
            physical,plan = admit_land(w,g,compounds)
            self.assertEqual(physical,w)
            self.assertNotIn("ADMITTED",plan["counts"])
            self.assertTrue(all(d["request"]["area"] == 120 for d in plan["decisions"].values()))

    def test_forgery_resource_limits_order_and_unknown_evidence(self):
        w,g = land_fixture()
        physical,plan = admit_land(w,g,[])
        changed = copy.deepcopy(physical)
        changed["parcels"][0]["width"] = 100
        with self.assertRaises(ValueError):
            validate_land(w,changed,g,[],plan)
        with patch("metropogits.world.urban_land.MAX_CHECKS",0):
            with self.assertRaisesRegex(ValueError,"urban land clearance limit"):
                admit_land(w,g,[])
        reverse = copy.deepcopy(w)
        reverse["parcels"].reverse()
        reverse["streets"].reverse()
        other,record = admit_land(reverse,g,[])
        self.assertEqual(plan,record)
        self.assertEqual({p["entityId"]:p for p in physical["parcels"]}, {p["entityId"]:p for p in other["parcels"]})
        for e in g["entities"]:
            e["roles"][0]["evidenceIds"] = ["absent"]
        _,neutral = admit_land(w,g,[])
        self.assertTrue(all(d["request"]["kind"] == "NEUTRAL_BLOCK" and not d["request"]["evidenceIds"] for d in neutral["decisions"].values()))

    def test_modern_systems_have_broad_cores_and_structurally_different_silhouettes(self):
        seen = set()
        shapes = set()
        from metropogits.world.architecture_metrics import occupancy
        envelope = dict(width=16,depth=12,height=48,center=[0,0],angle=.53)
        for i in range(64):
            specs,layout = modern_grammar("tower",envelope,str(i))
            seen.add(layout)
            parts = compile_parts(envelope,specs)
            shapes.add(occupancy(dict(envelope,parts=parts)))
            self.assertTrue(parts)
            # Composed setback cores may span several connected vertical
            # sections; test substantial volumes, not an old single-box height.
            self.assertGreaterEqual(max(s["width"] for s in specs if s["height"]>.2),.36)
            self.assertLessEqual(len(parts),18)
        self.assertGreaterEqual(len(seen),7)
        self.assertGreaterEqual(len(shapes),7)
        narrow = dict(envelope,width=6,depth=6)
        for i in range(16):
            specs,layout = modern_grammar("tower",narrow,str(i))
            self.assertNotEqual(layout,"LINKED_TOWERS_ON_PODIUM")
            self.assertGreaterEqual(max(s["width"] for s in specs if s["height"]>.3),.62)
        for form in {r["grammar"] for r in CATALOG.values()}:
            specs,_ = modern_grammar(form,envelope,"pinned")
            compile_parts(envelope,specs)

    def test_real_unknown_pipeline_has_shared_physical_meshes_and_unchanged_canonical_bytes(self):
        graph = analyze_repository(Path("tests/fixtures/repositories/architecture-unknown"),repository_id="fixture/architecture-unknown")
        scene = generate_city(graph)
        world = generate_world(scene,graph,seed="urban-unknown",zoning="neighborhoods",pattern_scale="adaptive",street_hierarchy=True)
        saved = copy.deepcopy((world,scene,graph))
        valid = validate_world(world,scene,graph)
        physical,profiles,land = urban_world(world,graph)
        self.assertTrue(land["counts"].get("ADMITTED"))
        self.assertTrue(all(not p["verifiedRole"] and not p["roleEvidenceIds"] for p in profiles.values()))
        data = view_data(world,scene,graph,building_style="urban",campus_landmarks=True)
        baseline = view_data(world,scene,graph,building_style="catalog",campus_landmarks=True)
        self.assertEqual(data["streets"]["surfaces"],baseline["streets"]["surfaces"])
        self.assertEqual(data["scene"]["schemaVersion"],"world-view/0.3")
        self.assertFalse(data["scene"]["networks"])
        self.assertEqual({b["entityId"]:b["height"] for b in data["scene"]["buildings"]},
                         {p["entityId"]:p["height"] for p in physical["parcels"]})
        a = package_world(world,scene,graph,valid,building_style="urban",campus_landmarks=True)
        b = package_world(world,scene,graph,valid,building_style="catalog",campus_landmarks=True)
        self.assertEqual(a,package_world(world,scene,graph,valid,building_style="urban",campus_landmarks=True))
        for name in ("world.json","city.json","graph.ucg.json","planning.json"):
            self.assertEqual(a[name],b[name])
        self.assertIn("urban-land.json",a)
        self.assertIn(b"urban-land.json physical admission", a["showcase.svg"])
        self.assertNotEqual(a["showcase.svg"],b["showcase.svg"])
        self.assertEqual(saved,(world,scene,graph))
        self.assertEqual(derive_compounds(world,graph,campus_landmarks=True)[0],[])


if __name__ == "__main__":
    unittest.main()
