import copy
import math
import unittest
import tempfile
import contextlib
import io
import shutil
from pathlib import Path
from unittest.mock import patch

from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.capacity import architectural_programs, fit_programs
from metropogits.world.export import package_world, view_data
from metropogits.world.generator import generate_world
from metropogits.world.geometry import rectangle
from metropogits.world.validation import validate_world


class CapacityReplanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parent / 'fixtures/repositories/reference-center'
        cls.graph = analyze_repository(root, repository_id='capacity-fixture')
        cls.scene = generate_city(cls.graph)

    def options(self, **extra):
        return dict(seed='capacity-1', planning='varied', outline='varied',
                    zoning='neighborhoods', pattern_scale='adaptive',
                    street_policy='porous', street_hierarchy=True, capacity_replan=True, **extra)

    def test_real_source_programs_are_allocated_before_roads_and_reproducible(self):
        s, g = self.scene, self.graph
        before = copy.deepcopy((s, g))
        w = generate_world(s, g, **self.options())
        valid = validate_world(w, s, g)
        self.assertEqual(before, (s, g))
        self.assertEqual(w, generate_world(s, g, **self.options()))
        self.assertEqual(w['capacityPlan']['counts'], {'ALLOCATED': 12, 'DEFERRED_REPLAN': 0})
        self.assertEqual(valid['accessibleBuildings'], 12)
        self.assertEqual(valid['buildingOverlaps'], 0)
        self.assertEqual(valid['roadOverlaps'], 0)
        self.assertGreater(len({(p['width'], p['depth']) for p in w['parcels']}), 2)
        programs = architectural_programs(s, g)
        for p in w['parcels']:
            self.assertEqual((p['width'], p['depth']), (programs[p['entityId']]['width'], programs[p['entityId']]['depth']))
        for d in w['capacityPlan']['districts'].values():
            self.assertGreater(d['allocatedLandArea'], d['requiredParcelArea'])
        data = view_data(w, s, g, building_style='urban')
        self.assertEqual(data['urbanLandPlan']['counts']['DEFERRED_REPLAN'], 0)
        package = package_world(w, s, g, valid, building_style='urban')
        self.assertIn('urban-land.json', package)
        self.assertIn('capacityPlan', package['world.json'].decode())
        import json
        reloaded = json.loads(package['world.json'])
        self.assertEqual(validate_world(reloaded, s, g), valid)
        self.assertEqual(reloaded['streetPlan']['version'], 'street-plan/0.2')

    def test_capacity_contract_rejects_shrink_missing_sources_and_forged_programs(self):
        w = generate_world(self.scene, self.graph, **self.options())
        for edit in ('shrink', 'omit', 'forge', 'defer'):
            bad = copy.deepcopy(w)
            key = bad['parcels'][0]['entityId']
            if edit == 'shrink':
                bad['parcels'][0]['width'] -= 1
            elif edit == 'omit':
                bad['parcels'].pop()
            elif edit == 'forge':
                bad['capacityPlan']['programs'][key]['evidenceIds'] = ['invented']
            else:
                bad['capacityPlan']['counts']['DEFERRED_REPLAN'] = 1
            with self.assertRaises(ValueError):
                validate_world(bad, self.scene, self.graph)

    def test_export_cannot_publish_a_legacy_deferred_plan_as_success(self):
        world = generate_world(self.scene, self.graph, **self.options())
        valid = validate_world(world, self.scene, self.graph)
        with patch('metropogits.world.urban_architecture.urban_world',
                   return_value=(world, {}, dict(counts={'DEFERRED_REPLAN': 1}))):
            with self.assertRaisesRegex(ValueError, 'unresolved physical capacity'):
                package_world(world, self.scene, self.graph, valid, building_style='urban')

    def test_variable_parcels_follow_oblique_frontage_and_never_consume_terrain(self):
        for angle in (0, .4, 1.2):
            c, s = math.cos(angle), math.sin(angle)
            def at(x, z):
                return [c * x - s * z, s * x + c * z]
            polygon = rectangle([0, 0], angle, 180, 120)
            lane = dict(id='frontage', start=at(-75, 0), end=at(75, 0), width=4, access=False)
            population = [dict(entityId=f'source:{i}', width=w, depth=d) for i, (w, d) in enumerate(((6, 6), (14, 10), (36, 18)))]
            plan = fit_programs(population, polygon, ([], [lane], angle, None), [], None, 'fixed')
            self.assertEqual(len(plan[0]), 3)
            self.assertEqual(len({round(abs(p['polygon'][1][0] - p['polygon'][0][0]), 2) for p in plan[0]}), 3)
            terrain = dict(features=[dict(id='protected', noBuildPolygon=polygon)])
            self.assertFalse(fit_programs(population, polygon, ([], [lane], angle, None), [], terrain, 'fixed')[0])

    def test_exhausted_capacity_is_error_not_successful_deferred_world(self):
        with patch('metropogits.world.capacity.fit_programs', side_effect=lambda m, p, plan, *a, **kw: ([], *plan[1:])):
            with self.assertRaisesRegex(ValueError, 'capacity infeasible'):
                generate_world(self.scene, self.graph, **self.options())

    def test_physical_linear_ramp_does_not_quantize_redundant_micro_grid_cuts(self):
        from metropogits.world.elevation import annotate, validate_profiles
        class Field:
            def height(self, p):
                return 1 + p[1] * .17
            def profile(self, a, b):
                return [[0, 0, 1.08], [0, .0004, 1.0801], [0, .0012, 1.0802]]
        road = dict(id='ramp', start=[0, 0], end=[0, .0012], width=.7, access=True, linearRamp=True)
        with patch('metropogits.world.elevation.surface', return_value=Field()), \
             patch('metropogits.world.rivers.crossing_piece', return_value={}), \
             patch('metropogits.world.river_landscape.tunnel_piece', return_value={}):
            annotate([road], [], {})
            self.assertEqual(len(road['heightProfile']), 2)
            validate_profiles([road], [], {})

    def test_programmed_campus_has_variable_lots_and_all_real_source_members(self):
        graph = analyze_repository(Path(__file__).parent / 'fixtures/repositories/purpose-campus',
                                   repository_id='capacity-campus')
        scene = generate_city(graph)
        options = self.options(campus=True, campus_style='precinct')
        options['seed'] = 'campus-estates-1'
        world = generate_world(scene, graph, **options)
        valid = validate_world(world, scene, graph)
        self.assertEqual(valid['accessibleBuildings'], 31)
        self.assertEqual(len(world['campusPlan']['sites']), 1)
        site = world['campusPlan']['sites'][0]
        self.assertEqual(set(site['memberEntityIds']), {b['entityId'] for b in scene['buildings']})
        self.assertTrue(site['courts'])
        self.assertTrue(site['sourceProgram']['evidenceIds'])
        self.assertGreater(len({(p['width'], p['depth']) for p in world['parcels']}), 3)
        data = view_data(world, scene, graph, building_style='urban', campus_landmarks=True)
        complexes = data['streets']['roleCompounds']
        self.assertEqual(len(complexes), 4)
        self.assertGreaterEqual(sum(len(c['memberEntityIds']) for c in complexes), 12)
        self.assertTrue(world['capacityPlan']['architecturalSites'])
        from metropogits.world.export import render_svg
        from xml.etree import ElementTree
        ordinary = copy.deepcopy(complexes)
        for c in ordinary:
            c['role'] = 'SOURCE_COMPLEX:VALIDATION'
        svg = render_svg(world, building_style='urban', graph=graph, compounds=ordinary)
        labels = [t.text for t in ElementTree.fromstring(svg).iter('{http://www.w3.org/2000/svg}text')]
        for c in ordinary:
            self.assertNotIn(f"{c['title']} · {len(c['memberEntityIds'])} files", labels)
            self.assertIn(c['id'].encode(), svg)
        # File doors inside a certified complex are logical interior addresses,
        # not public asphalt painted through its new ground-floor solids.
        from metropogits.world.street_mesh import street_mesh
        from metropogits.world.geometry import area
        from metropogits.block_orientation import clip
        from metropogits.world.urban_land import ClearanceIndex
        ground = ClearanceIndex()
        for c in complexes:
            model = c['physicalModel']
            for i, part in enumerate(model['parts']):
                if part['y'] <= model.get('baseElevation', 0) + .15 and part.get('materialKind') not in (12, 13, 14):
                    ground.add((c['id'], i), part['footprint'])
        for pavement in street_mesh(world, compounds=complexes):
            poly = pavement['points']
            for key in {k for cell in ground.cells_for(poly) for k in ground.cells[cell]}:
                self.assertLessEqual(area(clip(poly, ground.shapes[key])), .001)
        # Private planning units must never appear as invented source entities.
        self.assertEqual({p['entityId'] for p in world['parcels']}, {b['entityId'] for b in scene['buildings']})
        forged = copy.deepcopy(world)
        next(p for p in forged['parcels'] if p.get('architecturalSiteId'))['architecturalSiteId'] = 'invented'
        with self.assertRaises(ValueError):
            validate_world(forged, scene, graph)

    def test_quantized_micro_junction_is_coalesced_without_deleting_access(self):
        from metropogits.world.capacity import stabilize_infrastructure
        roads = [dict(id=str(i), start=a, end=b, width=3, access=False) for i, (a, b) in enumerate(
            (([0, 0], [.0001, 0]), ([.0001, 0], [10, 0])))]
        parcels = [dict(entrance=[10, 0], streetPoint=[0, 0])]
        streets, _ = stabilize_infrastructure(roads, parcels, dict(crossings=[], tunnels=[]))
        self.assertEqual(len(streets), 1)
        self.assertEqual({tuple(streets[0][k]) for k in ('start', 'end')}, {(0, 0), (10, 0)})

    def test_cli_accepts_strict_json_previous_geometry_and_emits_a_physical_plan(self):
        from scripts.canonical_json import canonical_json_bytes
        from scripts.procedural_world import main
        import json
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'build'
            source.mkdir()
            for name, document in (('city.json', self.scene), ('graph.ucg.json', self.graph)):
                (source / name).write_bytes(canonical_json_bytes(document))
            previous = generate_world(self.scene, self.graph, **self.options())
            (root / 'previous.json').write_bytes(canonical_json_bytes(previous))
            args = ['procedural_world', str(source), '--out', str(root / 'result'), '--seed', 'capacity-1',
                    '--planning', 'varied', '--outline', 'varied', '--zoning', 'neighborhoods',
                    '--pattern-scale', 'adaptive', '--street-policy', 'porous', '--street-hierarchy',
                    '--building-style', 'urban', '--previous-world', str(root / 'previous.json')]
            with patch('sys.argv', args), contextlib.redirect_stdout(io.StringIO()):
                main()
            output = json.loads((root / 'result/world.json').read_text(encoding='utf8'))
            self.assertEqual(output['capacityPlan']['counts']['DEFERRED_REPLAN'], 0)
            self.assertEqual([(d['id'], d['polygon'], d['anchor']) for d in previous['districts']],
                             [(d['id'], d['polygon'], d['anchor']) for d in output['districts']])

    def test_small_hinted_growth_retains_the_unrelated_district(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'input'
            shutil.copytree(Path(__file__).parent / 'fixtures/repositories/reference-center', root)
            (root / 'other').mkdir()
            (root / 'other/standalone.py').write_text('VALUE = 1\n', encoding='utf8')
            graph = analyze_repository(root, repository_id='capacity-stability')
            scene = generate_city(graph)
            baseline = generate_world(scene, graph, **self.options())
            (root / 'app/zadded.py').write_text('VALUE = 2\n', encoding='utf8')
            changed_graph = analyze_repository(root, repository_id='capacity-stability')
            changed_scene = generate_city(changed_graph)
            grown = generate_world(changed_scene, changed_graph, previous=baseline, **self.options())
            validate_world(grown, changed_scene, changed_graph)
            old = next(p for p in baseline['parcels'] if p['entityId'].endswith('other/standalone.py'))
            new = next(p for p in grown['parcels'] if p['entityId'] == old['entityId'])
            self.assertEqual((old['center'], old['angle'], old['width'], old['depth']),
                             (new['center'], new['angle'], new['width'], new['depth']))

    def test_unsupported_language_is_complete_without_invented_roles_or_routes(self):
        graph = analyze_repository(Path(__file__).parent / 'fixtures/repositories/architecture-unknown',
                                   repository_id='capacity-unknown')
        scene = generate_city(graph)
        world = generate_world(scene, graph, **self.options())
        valid = validate_world(world, scene, graph)
        self.assertEqual(valid['accessibleBuildings'], 3)
        self.assertEqual(valid['trips'], 0)
        self.assertEqual(world['capacityPlan']['counts']['DEFERRED_REPLAN'], 0)
        self.assertTrue(all(p['family'] == 'NEUTRAL_MIXED_BUILDING' and not p['evidenceIds']
                            for p in world['capacityPlan']['programs'].values()))

    def test_hierarchy_port_ids_survive_integer_float_canonical_roundtrip(self):
        import json
        from scripts.canonical_json import canonical_json_bytes
        from metropogits.world.street_hierarchy import derive_street_plan
        world = generate_world(self.scene, self.graph, **self.options())
        world['zoning']['zones'][0]['accessPorts'].append([0.0, 1.0])
        before = derive_street_plan(world)
        after = derive_street_plan(json.loads(canonical_json_bytes(world)))
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
