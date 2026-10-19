"""Through-flow water and conditional source-backed mountain infrastructure."""

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from test_world_neighborhoods import fixture
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.elevation import surface
from metropogits.world.export import package_world, view_data
from metropogits.world.generator import generate_world
from metropogits.world.geometry import inside, rectangle
from metropogits.world.river_landscape import generate_landscape_terrain, natural_faces, validate_landscape
from metropogits.world.elevation import annotate
from metropogits.world.infrastructure import atomic_streets, route_world
from metropogits.world.validation import validate_world


class RiverLandscapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene,cls.graph=fixture(Path(directory))
        cls.options=dict(zoning="neighborhoods",pattern_scale="adaptive",planning="varied",
                         outline="varied",terrain="river-landscape",street_policy="permeable",seed="landscape-test")
        cls.world=generate_world(cls.scene,cls.graph,**cls.options)

    def test_main_and_smaller_tributary_extend_beyond_bounded_city_growth(self):
        w=self.world
        validate_world(w,self.scene,self.graph)
        channel=w["terrain"]["channel"]
        self.assertEqual(len(channel["centerline"]),11)
        self.assertEqual(len(channel["tributaries"]),1)
        branch=channel["tributaries"][0]
        self.assertIn(branch[0],channel["centerline"])
        expanded=[[x*2.2,z*2.2] for x,z in w["terrain"]["initialEnvelope"]]
        for p in (channel["centerline"][0],channel["centerline"][-1],branch[-1]):
            self.assertFalse(inside(p,expanded))
        self.assertFalse(any(f["kind"]=="LAKE" for f in w["terrain"]["features"]))
        self.assertEqual(sum(f["kind"]=="RIVER" for f in w["terrain"]["features"]),12)
        s=surface(w["terrain"])
        for a,b in zip(branch,branch[1:]):
            self.assertEqual(s.height([(a[j]+b[j])/2 for j in (0,1)]),0)

    def test_shared_render_mesh_is_clipped_to_city_and_source_contract_is_intact(self):
        w=self.world
        features=natural_faces(w)
        self.assertTrue(features)
        for f in features:
            for face in f["faces"]:
                for x,y,z in face["points"]:
                    self.assertTrue(inside([x,z],w["envelope"],-.001))
        p=package_world(w,self.scene,self.graph,validate_world(w,self.scene,self.graph))
        self.assertEqual(json.loads(p["city.json"]),self.scene)
        self.assertEqual(json.loads(p["graph.ucg.json"]),self.graph)
        self.assertEqual(view_data(w,self.scene,self.graph)["terrain"]["features"],features)
        root=Path(__file__).parents[1]
        for schema,key in (("world-0.1.schema.json","world.json"),("planning-0.5.schema.json","planning.json")):
            Draft202012Validator(json.loads((root/"schemas"/schema).read_text(encoding="utf8"))).validate(json.loads(p[key]))
        self.assertEqual(w,generate_world(self.scene,self.graph,**self.options))
        self.assertEqual(p,package_world(w,self.scene,self.graph,validate_world(w,self.scene,self.graph)))

    def test_tunnels_have_complete_real_trips_and_open_portal_geometry(self):
        w=self.world
        used={s["physicalId"] for s in w["routing"]["segments"]}
        for tunnel in w["terrain"]["tunnels"]:
            roads=[s for s in w["streets"] if s.get("tunnelId")==tunnel["id"]]
            if not roads:
                continue
            self.assertTrue(any(s["id"] in used for s in roads))
            self.assertAlmostEqual(sum(math.dist(s["start"],s["end"]) for s in roads),math.dist(*tunnel["path"]),delta=.003)
            f=next(f for f in natural_faces(w) if f["id"]==tunnel["hillId"])
            self.assertTrue(any(p.get("surface")=="tunnel" for p in f["faces"]))
        forged=copy.deepcopy(w)
        forged["streets"][0]["tunnelId"]="invented"
        with self.assertRaisesRegex(ValueError,"tunnel"):
            validate_landscape(forged)
        trapped=copy.deepcopy(w)
        trapped["terrain"]["channel"]["centerline"][0]=[0,0]
        with self.assertRaisesRegex(ValueError,"endpoint"):
            validate_landscape(trapped)

    def test_small_unsupported_input_has_real_access_but_no_fake_tunnel_traffic(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory)
            (repo/"unknown.rs").write_text("fn main() {}",encoding="utf8")
            graph=analyze_repository(repo,repository_id="fixture/through-solo")
            scene=generate_city(graph)
            w=generate_world(scene,graph,**self.options)
        self.assertEqual(w["routing"]["routes"],[])
        self.assertFalse(any(s.get("tunnelId") for s in w["streets"]))
        self.assertEqual(validate_world(w,scene,graph)["accessibleBuildings"],1)

    def test_real_source_pair_uses_certified_tunnel_with_a_cut_opening(self):
        envelope=rectangle([0,0],0,700,500)
        terrain=generate_landscape_terrain(envelope,"1234567890abcdef")
        self.assertEqual(len(terrain["tunnels"]),1)
        tunnel=terrain["tunnels"][0]
        parcels=[dict(entityId="fixture/neighborhoods:file:"+name,districtId="fixture/neighborhoods:directory:.",entrance=p)
                 for name,p in zip(("Service0.java","Store0.java"),tunnel["path"])]
        streets=atomic_streets([dict(start=tunnel["path"][0],end=tunnel["path"][1],width=3.5,access=False)])
        annotate(streets,[],terrain)
        routing,_,_=route_world(self.graph,parcels,streets)
        world=dict(terrain=terrain,envelope=envelope,streets=streets,routing=routing)
        self.assertEqual(len(routing["routes"]),1)
        self.assertTrue(routing["routes"][0]["edgeIds"])
        self.assertEqual(streets[0]["tunnelId"],tunnel["id"])
        validate_landscape(world)
        mountain=next(f for f in natural_faces(world) if f["id"]==tunnel["hillId"])
        self.assertTrue(any(f.get("surface")=="tunnel" for f in mountain["faces"]))
        forged=copy.deepcopy(world)
        forged["routing"]["segments"]=[]
        with self.assertRaisesRegex(ValueError,"no evidenced trip"):
            validate_landscape(forged)

    def test_new_shore_and_junction_work_caps_fail_explicitly(self):
        from metropogits.world.river_landscape import joined_streets

        with patch("metropogits.world.river_landscape.MAX_WORK",0),self.assertRaisesRegex(ValueError,"work limit"):
            generate_landscape_terrain(rectangle([0,0],0,700,500),"1234567890abcdef")
        with self.assertRaisesRegex(ValueError,"input limit"):
            joined_streets([{}]*50_001,[],{})

    def test_compatible_growth_retains_immutable_terrain_and_complete_frames(self):
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
