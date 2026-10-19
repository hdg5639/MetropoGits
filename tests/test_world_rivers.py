"""Connected natural barriers precede and certify physical bridge routes."""

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
from metropogits.street_diagonals import overlap
from metropogits.world.export import package_world, view_data
from metropogits.world.generator import generate_world
from metropogits.world.geometry import inside, ribbon
from metropogits.block_orientation import clip
from metropogits.world.geometry import area
from metropogits.world.rivers import generate_river, river_roads, crossing_piece, height_at
from metropogits.world.terrain import validate_terrain
from metropogits.world.validation import validate_world


class RiverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene,cls.graph=fixture(Path(directory))
        cls.options=dict(zoning="neighborhoods",pattern_scale="adaptive",planning="varied",
                         outline="varied",terrain="river-corridor",street_policy="permeable",seed="river-test")
        cls.world=generate_world(cls.scene,cls.graph,**cls.options)

    def test_connected_channel_is_fixed_before_city_and_canonical(self):
        t=self.world["terrain"]
        self.assertEqual(t,generate_river(t["initialEnvelope"],self.world["seed"]))
        validate_terrain(t,self.world["seed"])
        water=[f for f in t["features"] if f["kind"]=="RIVER"]
        self.assertEqual(len(water),8)
        for a,b in zip(water,water[1:]):
            self.assertEqual(len({tuple(p) for p in a["polygon"]}&{tuple(p) for p in b["polygon"]}),2)
        for p in t["channel"]["centerline"]:
            self.assertTrue(any(inside(p,f["polygon"]) for f in water))
        water=[f for f in t["features"] if f["kind"] != "HILL"]
        for f in water:
            for face in f["faces"]:
                if face["color"] != "#83927a":
                    continue
                poly=[[x,z] for x,y,z in face["points"]][::-1]
                for other in water:
                    self.assertLess(area(clip(poly,other["polygon"])), .002)
        roads=river_roads(t)
        for r in roads:
            if not crossing_piece(r,t):
                self.assertFalse(any(overlap(ribbon(r["start"],r["end"],r["width"]),f["noBuildPolygon"]) for f in t["features"]))
        bad=copy.deepcopy(t)
        bad["crossings"][0]["heights"][1]+=.1
        with self.assertRaisesRegex(ValueError,"global field"):
            validate_terrain(bad,self.world["seed"])

    def test_bridge_routing_preserves_exact_source_endpoints_and_physical_profiles(self):
        world=self.world
        validate_world(world,self.scene,self.graph)
        self.assertEqual(world,generate_world(self.scene,self.graph,**self.options))
        lake=generate_world(self.scene,self.graph,**dict(self.options,terrain="lake-district"))
        self.assertEqual({p["entityId"] for p in world["parcels"]},{p["entityId"] for p in lake["parcels"]})
        def identity(w):
            return {r["id"]:(r["source"],r["target"],r["edgeIds"]) for r in w["routing"]["routes"]}
        self.assertEqual(identity(world),identity(lake))
        self.assertTrue(any(s.get("bridgeId") for s in world["streets"]))
        by_id={s["id"]:s for s in world["streets"]}
        for s in world["routing"]["segments"]:
            self.assertEqual(s.get("heights"),by_id[s["physicalId"]].get("heights"))
        for c in world["terrain"]["crossings"]:
            self.assertEqual(c["heights"][::3],[.08,.08])
            for a,b,y,z in zip(c["path"],c["path"][1:],c["heights"],c["heights"][1:]):
                self.assertLessEqual(abs(y-z)/math.dist(a,b),c["maxGrade"])

    def test_forged_bridge_permit_and_missing_or_flattened_span_are_rejected(self):
        for mutation in ("flatten","missing","invented"):
            bad=copy.deepcopy(self.world)
            s=next(s for s in bad["streets"] if s.get("bridgeId"))
            if mutation=="flatten":
                s["heights"]=[.08,.08]
            elif mutation=="missing":
                bad["streets"].remove(s)
            else:
                s["start"][0]+=3
            with self.assertRaises(ValueError):
                validate_world(bad,self.scene,self.graph)

    def test_whole_parcels_and_ordinary_full_width_roads_avoid_water(self):
        t=self.world["terrain"]
        for f in t["features"]:
            for p in self.world["parcels"]:
                self.assertFalse(overlap(p["parcel"],f["noBuildPolygon"]))
            for s in self.world["streets"]:
                if not s.get("bridgeId"):
                    self.assertFalse(overlap(ribbon(s["start"],s["end"],s["width"]),f["noBuildPolygon"]))

    def test_compatibility_schema_and_all_renderer_profiles(self):
        world=self.world
        p=package_world(world,self.scene,self.graph,validate_world(world,self.scene,self.graph))
        root=Path(__file__).parents[1]
        for schema,document in (("world-0.1.schema.json","world.json"),("planning-0.5.schema.json","planning.json")):
            Draft202012Validator(json.loads((root/"schemas"/schema).read_text(encoding="utf8"))).validate(json.loads(p[document]))
        data=view_data(world,self.scene,self.graph)
        self.assertEqual(data["terrain"],world["terrain"])
        self.assertTrue(data["infrastructure"]["structural"])
        self.assertTrue(data["infrastructure"]["faces"])
        self.assertIn(b'data-structural="shared-bridge"',p["preview.svg"])
        self.assertEqual(json.loads(p["city.json"]),self.scene)
        self.assertEqual(json.loads(p["graph.ucg.json"]),self.graph)
        for s in data["streets"]["surfaces"]:
            if "heights" in s:
                self.assertEqual(s["pointHeights"],[height_at(s,v) for v in s["points"]])
        self.assertEqual(p,package_world(world,self.scene,self.graph,validate_world(world,self.scene,self.graph)))

    def test_hints_keep_river_and_existing_full_frames_after_small_edit(self):
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

    def test_small_unknown_has_no_fake_traffic_and_union_work_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory)
            (repo/"unknown.rs").write_text("fn main() {}",encoding="utf8")
            graph=analyze_repository(repo,repository_id="fixture/river-solo")
            scene=generate_city(graph)
            world=generate_world(scene,graph,**self.options)
        self.assertEqual(len(world["parcels"]),1)
        self.assertEqual(world["routing"]["routes"],[])
        validate_world(world,scene,graph)
        with patch("metropogits.world.rivers.MAX_WORK",0),self.assertRaisesRegex(ValueError,"work limit"):
            river_roads(world["terrain"])
