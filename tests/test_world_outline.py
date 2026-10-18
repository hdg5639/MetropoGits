import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from test_world_planning import fixture
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.geometry import area, centroid, inside
from metropogits.world.outline import varied_outline
from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world
from metropogits.world.export import package_world
from metropogits.world.seed import derive


class WorldOutlineTests(unittest.TestCase):
    def test_seeded_shapes_are_convex_reproducible_and_more_than_rotated_ellipses(self):
        families, counts, signatures = set(), set(), set()
        for i in range(128):
            seed = derive(str(i))
            poly, family = varied_outline(seed)
            self.assertEqual((poly, family), varied_outline(seed))
            self.assertTrue(inside(centroid(poly), poly))
            self.assertGreater(area(poly), 1)
            self.assertTrue(all(inside(p, poly) for p in poly))
            families.add(family)
            counts.add(len(poly))
            signatures.add(tuple(map(tuple, poly)))
        self.assertEqual(families, {"compact", "elongated", "angular", "asymmetric"})
        self.assertGreater(len(counts), 3)
        self.assertEqual(len(signatures), 128)

    def test_actual_varied_world_preserves_facts_and_compatible_hints(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            scene, graph = fixture(repo)
            world = generate_world(scene, graph, planning="hybrid", outline="varied")
            report = validate_world(world, scene, graph)
            repeat = generate_world(scene, graph, planning="hybrid", outline="varied")
            self.assertEqual(world, repeat)
            self.assertEqual(
                package_world(world, scene, graph, report),
                package_world(repeat, scene, graph, report),
            )
            schema = json.loads(
                (
                    Path(__file__).parents[1] / "schemas/world-0.1.schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(world)
            before = {p["entityId"]: p for p in world["parcels"]}
            (repo / "new.rs").write_text("fn added() {}", encoding="utf8")
            graph = analyze_repository(repo, repository_id="fixture/radial")
            scene = generate_city(graph)
            changed = generate_world(
                scene, graph, planning="hybrid", outline="varied", previous=world
            )
            validate_world(changed, scene, graph)
            self.assertEqual(world["envelope"], changed["envelope"])
            self.assertTrue(changed["anchors"]["reusedDistrictIds"])
            for p in changed["parcels"]:
                if p["entityId"] in before:
                    self.assertEqual(p, before[p["entityId"]])

    def test_outline_switch_replans_and_legacy_option_remains_default(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, graph = fixture(Path(directory), 6)
        original = generate_world(scene, graph)
        self.assertEqual(original, generate_world(scene, graph, outline="ellipse"))
        self.assertNotIn("outlinePolicy", original)
        changed = generate_world(scene, graph, previous=original, outline="varied")
        self.assertFalse(changed["anchors"]["reusedDistrictIds"])
        self.assertNotEqual(original["envelope"], changed["envelope"])
        with self.assertRaisesRegex(ValueError, "outline policy"):
            generate_world(scene, graph, outline="unbounded-coastline")
