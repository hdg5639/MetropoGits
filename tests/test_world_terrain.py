"""Nature reserves precede source assignment and never erase source truth."""

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
from metropogits.street_diagonals import overlap
from metropogits.world.export import package_world, view_data
from metropogits.world.generator import generate_world
from metropogits.world.geometry import area, inside, ribbon
from metropogits.world.infrastructure import atomic_streets
from metropogits.world.terrain import adapt_roads, generate_terrain, outside, validate_terrain
from metropogits.world.validation import validate_world


class TerrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.scene, cls.graph = fixture(Path(directory))
        cls.options = dict(zoning="neighborhoods", pattern_scale="adaptive",
                           planning="varied", outline="varied", seed="terrain-test",
                           terrain="lake-district", street_policy="permeable")
        cls.world = generate_world(cls.scene, cls.graph, **cls.options)

    def test_line_clipping_cuts_water_not_source_endpoints(self):
        square = [[-5,-5],[5,-5],[5,5],[-5,5]]
        self.assertEqual(outside([-12,0],[12,0],square), [([-12,0],[-5.,0.]),([5.,0.],[12,0])])
        self.assertEqual(outside([0,0],[12,0],square), [([5.,0.],[12,0])])
        self.assertEqual(outside([-2,0],[2,0],square), [])
        self.assertEqual(outside([-12,8],[12,8],square), [([-12,8],[12,8])])
        self.assertEqual(outside([-12,0],[-8,0],square), [([-12,0],[-8,0])])

    def test_global_terrain_is_independent_of_urban_objects_and_canonical(self):
        terrain = self.world["terrain"]
        self.assertEqual(terrain, generate_terrain(terrain["initialEnvelope"], self.world["seed"]))
        validate_terrain(terrain, self.world["seed"])
        for f in terrain["features"]:
            self.assertTrue(all(inside(p, terrain["initialEnvelope"]) for p in f["roadPolygon"]))
            self.assertNotIn("entityId", f)
            self.assertNotIn("edgeIds", f)
            self.assertTrue(all(inside([x,z], f["polygon"]) for face in f["faces"] for x,y,z in face["points"]))
            for face in f["faces"]:
                a,b,c = face["points"][:3]
                self.assertGreater((b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]), 0)
                self.assertTrue(all(0 <= y <= f["height"] for x,y,z in face["points"]))
        bad = copy.deepcopy(terrain)
        bad["features"][0]["center"][0] += 1
        with self.assertRaisesRegex(ValueError, "global field"):
            validate_terrain(bad, self.world["seed"])

    def test_real_urban_adaptation_preserves_truth_but_not_flat_coordinates(self):
        world = self.world
        flat = generate_world(self.scene, self.graph, **dict(self.options, terrain="flat"))
        self.assertNotEqual(world["parcels"], flat["parcels"])
        self.assertEqual({p["entityId"] for p in world["parcels"]}, {p["entityId"] for p in flat["parcels"]})
        self.assertEqual({r["id"]:r["edgeIds"] for r in world["routing"]["routes"]},
                         {r["id"]:r["edgeIds"] for r in flat["routing"]["routes"]})
        self.assertEqual(world, generate_world(self.scene, self.graph, **self.options))
        cold = generate_world(self.scene, self.graph, previous=flat, **self.options)
        self.assertEqual(cold["parcels"], world["parcels"])
        self.assertTrue(any("incompatible previous world" in d["reason"] for d in cold["diagnostics"]))
        validate_world(world, self.scene, self.graph)
        schema = json.loads((Path(__file__).parents[1]/"schemas/world-0.1.schema.json").read_text(encoding="utf8"))
        Draft202012Validator(schema).validate(world)
        for f in world["terrain"]["features"]:
            self.assertTrue(all(not overlap(p["parcel"], f["noBuildPolygon"]) for p in world["parcels"]))
            self.assertTrue(all(not overlap(ribbon(s["start"],s["end"],s["width"]), f["noBuildPolygon"])
                                for s in world["streets"]))

    def test_terrain_exists_before_the_first_source_population(self):
        from metropogits.world.adaptive import populate

        events = []
        def terrain(*args):
            events.append("terrain")
            return generate_terrain(*args)
        def population(*args, **kwargs):
            self.assertEqual(events[0], "terrain")
            events.append("population")
            return populate(*args, **kwargs)
        with (patch("metropogits.world.generator.generate_terrain", side_effect=terrain),
              patch("metropogits.world.adaptive.populate", side_effect=population)):
            generate_world(self.scene, self.graph, **self.options)
        self.assertEqual(events.count("terrain"), 1)
        self.assertIn("population", events)

    def test_geometry_and_budget_failures_are_not_silently_ignored(self):
        f = self.world["terrain"]["features"][0]
        roads = [dict(id="arterial",start=[f["center"][0]-100,f["center"][1]],
                      end=[f["center"][0]+100,f["center"][1]], width=3.5, access=False)]
        adapted = adapt_roads(roads, self.world["terrain"])
        self.assertGreaterEqual(len(adapted), 2)
        self.assertTrue(all(not overlap(ribbon(s["start"],s["end"],s["width"]),f["noBuildPolygon"]) for s in adapted))
        bad = copy.deepcopy(self.world)
        bad["streets"] = atomic_streets(bad["streets"]+roads)
        with self.assertRaises(ValueError):
            validate_world(bad, self.scene, self.graph)
        with patch("metropogits.world.terrain.MAX_WORK", 0), self.assertRaisesRegex(ValueError,"work limit"):
            adapt_roads(roads, self.world["terrain"])

    def test_shared_geometry_reaches_both_exports_without_changing_city_or_ucg(self):
        world = self.world
        original = copy.deepcopy((world,self.scene,self.graph))
        package = package_world(world,self.scene,self.graph,validate_world(world,self.scene,self.graph))
        self.assertEqual(package,package_world(world,self.scene,self.graph,validate_world(world,self.scene,self.graph)))
        self.assertEqual(view_data(world,self.scene,self.graph)["terrain"],world["terrain"])
        self.assertIn(b'Natural terrain (procedural)',package["index.html"])
        self.assertIn(b'data-environmental="natural-terrain"',package["showcase.svg"])
        self.assertEqual(json.loads(package["world.json"]),world)
        self.assertEqual(json.loads(package["city.json"]),self.scene)
        self.assertEqual(json.loads(package["graph.ucg.json"]),self.graph)
        planning_schema=json.loads((Path(__file__).parents[1]/"schemas/planning-0.5.schema.json").read_text(encoding="utf8"))
        Draft202012Validator(planning_schema).validate(json.loads(package["planning.json"]))
        self.assertEqual(original,(world,self.scene,self.graph))
        scape=json.loads(package["landscape.json"])
        ablation=package_world(world,self.scene,self.graph,validate_world(world,self.scene,self.graph),landscaping=False)
        self.assertIn(b'Terrain-first lakes and hills (procedural)',ablation["showcase.svg"])
        self.assertNotIn("landscape.json",ablation)
        self.assertEqual(ablation["world.json"],package["world.json"])
        for patch_land in scape["patches"]:
            self.assertTrue(all(not overlap(patch_land["polygon"],f["noBuildPolygon"]) for f in world["terrain"]["features"]))

    def test_hinted_growth_keeps_nature_and_existing_complete_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory)
            scene,graph=fixture(repo)
            old=generate_world(scene,graph,**self.options)
            (repo/"zz_extra.rs").write_text("fn generic() {}",encoding="utf8")
            graph=analyze_repository(repo,repository_id="fixture/neighborhoods")
            scene=generate_city(graph)
            world=generate_world(scene,graph,previous=old,**self.options)
        self.assertEqual(old["terrain"],world["terrain"])
        old_frames={p["entityId"]:p for p in old["parcels"]}
        self.assertTrue(world["anchors"]["reusedDistrictIds"])
        for p in world["parcels"]:
            if p["entityId"] in old_frames:
                self.assertEqual(p,old_frames[p["entityId"]])
        self.assertGreaterEqual(area(world["envelope"]),area(old["envelope"])-.01)
        validate_world(world,scene,graph)

    def test_sparse_unknown_input_reserves_enough_space_before_creating_nature(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo/"unknown.rs").write_text("fn main() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/terrain-solo")
            scene = generate_city(graph)
            world = generate_world(scene, graph, **self.options)
        self.assertEqual(len(world["parcels"]), 1)
        self.assertEqual(world["routing"]["routes"], [])
        self.assertGreaterEqual(area(world["terrain"]["initialEnvelope"]), 3999)
        self.assertTrue(world["terrain"]["features"])
        validate_world(world, scene, graph)

    def test_empty_eroded_backbone_reports_zero_supply_instead_of_fake_ports(self):
        from metropogits.world.terrain import terrain_plan

        polygon = [[0,0],[5,0],[5,5],[0,5]]
        plans, main, boundary, ports, pattern = terrain_plan(
            {"zone": ([], [], 0, None)}, [], [], {"zone": {(2,2)}}, {}, polygon, {"features": []})
        self.assertEqual(plans["zone"][0], [])
        self.assertEqual(main+boundary, [])
        self.assertEqual(ports, {"zone": set()})
