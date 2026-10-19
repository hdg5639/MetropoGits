"""Graded ground is a planning input, not a render-only building translation."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from test_world_neighborhoods import fixture
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.elevation import surface, build_surface, suitable, validate_profiles, pavement, foundation_faces
from metropogits.world.export import package_world, view_data
from metropogits.world.generator import generate_world
from metropogits.world.geometry import rectangle
from metropogits.world.validation import validate_world


class ElevationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene,cls.graph=fixture(Path(directory))
        cls.options=dict(zoning="neighborhoods",pattern_scale="adaptive",planning="varied",
                         outline="varied",terrain="river-valley",street_policy="permeable",seed="valley-test")
        cls.world=generate_world(cls.scene,cls.graph,**cls.options)

    def test_global_lattice_has_shared_heights_and_complete_breakpoints(self):
        s=surface(self.world["terrain"])
        for i in range(-12,13):
            p=[i*16,210]
            self.assertAlmostEqual(s.height([p[0]-.000001,p[1]]),s.height([p[0]+.000001,p[1]]),places=5)
        profile=s.profile([-210,190],[220,277])
        self.assertGreater(len(profile),20)
        for a,b in zip(profile,profile[1:]):
            for t in (.2,.5,.8):
                p=[a[j]+t*(b[j]-a[j]) for j in (0,1)]
                self.assertAlmostEqual(a[2]+t*(b[2]-a[2]),s.height(p)+.08,delta=.0002)

    def test_sparse_water_geometry_retries_before_urban_allocation_not_budget_weakening(self):
        repo=Path(__file__).parent/"fixtures/repositories/spring-positive"
        graph=analyze_repository(repo,repository_id="fixture/valley-e2e")
        scene=generate_city(graph)
        w=generate_world(scene,graph,**dict(self.options,seed=None,namespace="fixture/valley-e2e"))
        self.assertEqual(len(w["parcels"]),6)
        self.assertGreaterEqual(w["terrain"]["elevation"]["waterAttempt"],1)
        validate_world(w,scene,graph)

    def test_sloped_lot_is_rejected_before_assignment(self):
        t=self.world["terrain"]
        blocked=False
        for x in range(-250,251,25):
            slot=dict(polygon=rectangle([x,180],.2,80,60),entrance=[x,150],streetPoint=[x,147])
            if not suitable(slot,t):
                blocked=True
                break
        self.assertTrue(blocked)
        self.assertEqual(build_surface(t,self.world["districts"]),self.world["surface"])

    def test_profiles_foundations_schemas_and_exact_source_conservation(self):
        w=self.world
        validate_world(w,self.scene,self.graph)
        self.assertEqual(w,generate_world(self.scene,self.graph,**self.options))
        validate_profiles(w["streets"],w["parcels"],w["terrain"])
        old=generate_world(self.scene,self.graph,**dict(self.options,terrain="river-corridor"))
        self.assertEqual({p["entityId"] for p in old["parcels"]},{p["entityId"] for p in w["parcels"]})
        self.assertEqual({r["id"]:r["edgeIds"] for r in old["routing"]["routes"]},{r["id"]:r["edgeIds"] for r in w["routing"]["routes"]})
        root=Path(__file__).parents[1]
        package=package_world(w,self.scene,self.graph,validate_world(w,self.scene,self.graph))
        for schema,key in (("world-0.1.schema.json","world.json"),("planning-0.5.schema.json","planning.json")):
            Draft202012Validator(json.loads((root/"schemas"/schema).read_text(encoding="utf8"))).validate(json.loads(package[key]))
        self.assertEqual(json.loads(package["city.json"]),self.scene)
        self.assertEqual(json.loads(package["graph.ucg.json"]),self.graph)
        self.assertEqual(package,package_world(w,self.scene,self.graph,validate_world(w,self.scene,self.graph)))
        data=view_data(w,self.scene,self.graph)
        for p in w["parcels"]:
            model=data["routing"]["parcelPlan"]["buildings"][p["entityId"]]
            self.assertTrue(model["foundationFaces"])
            for a,b in zip(model["parts"],p["parts"]):
                self.assertAlmostEqual(a["y"],b["y"]+p["baseElevation"])
                self.assertEqual(a["height"],b["height"])

    def test_ground_pavement_and_platform_contact_are_exact(self):
        w=self.world
        s=surface(w["terrain"])
        for r in w["streets"]:
            if r["access"] or r.get("bridgeId"):
                continue
            for f in pavement(r,w["terrain"],"#123456"):
                for p,y in zip(f["points"],f["pointHeights"]):
                    self.assertAlmostEqual(y,s.height(p)+.08,delta=.0002)
        for p in w["parcels"]:
            lo,hi=s.range(p["footprint"])
            self.assertAlmostEqual(p["foundationLow"],lo,delta=.0001)
            self.assertAlmostEqual(p["baseElevation"],hi+.04,delta=.0001)
            for face in foundation_faces(p,w["terrain"]):
                a,b=face["points"][2:]
                for t in (.2,.5,.8):
                    x,z=a[0]+(b[0]-a[0])*t,a[2]+(b[2]-a[2])*t
                    self.assertAlmostEqual(a[1]+(b[1]-a[1])*t,s.height([x,z]),delta=.0002)

    def test_forged_height_ground_or_platform_are_rejected(self):
        for mode in ("street","ground","platform"):
            w=copy.deepcopy(self.world)
            if mode=="street":
                w["streets"][0]["heightProfile"][0][2]+=1
            elif mode=="ground":
                w["surface"]["values"][0][0]+=1
            else:
                w["parcels"][0]["baseElevation"]+=1
            with self.assertRaises(ValueError):
                validate_world(w,self.scene,self.graph)

    def test_hinted_new_file_retains_terrain_and_old_complete_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory)
            scene,graph=fixture(repo)
            old=generate_world(scene,graph,**self.options)
            (repo/"zz_extra.rs").write_text("fn generic() {}",encoding="utf8")
            graph=analyze_repository(repo,repository_id="fixture/neighborhoods")
            scene=generate_city(graph)
            new=generate_world(scene,graph,previous=old,**self.options)
        self.assertEqual(old["terrain"],new["terrain"])
        frames={p["entityId"]:p for p in new["parcels"]}
        for p in old["parcels"]:
            self.assertEqual(p,frames[p["entityId"]])
        validate_world(new,scene,graph)

    def test_unknown_source_stays_generic_and_mesh_limits_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory)
            (repo/"unknown.rs").write_text("fn main() {}",encoding="utf8")
            graph=analyze_repository(repo,repository_id="fixture/valley-solo")
            scene=generate_city(graph)
            w=generate_world(scene,graph,**self.options)
        self.assertEqual(len(w["parcels"]),1)
        self.assertEqual(w["routing"]["routes"],[])
        validate_world(w,scene,graph)
        with patch("metropogits.world.elevation.MAX_CELLS",0),self.assertRaisesRegex(ValueError,"limit"):
            build_surface(w["terrain"],w["districts"])
