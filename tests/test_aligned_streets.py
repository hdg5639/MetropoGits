import copy
import unittest
from unittest.mock import patch

from metropogits.access_routes import AccessGrid, derive_access_routes
from metropogits.structural_streets import build_streets, assign_streets, _adjacency, _components
from metropogits.street_connectivity import join_components
from scripts.canonical_json import canonical_json_bytes
from scripts.parcel_pilot import pavement_intersections
import test_block_collectors as collector_checks
from test_block_collectors import fixture


class AlignedStreetTests(unittest.TestCase):
    def test_aligned_seed_keeps_clear_boundary_instead_of_cutting_building_centers(self):
        buildings=[dict(entityId=f'b{x}-{z}',districtId='d',x=x*7+.5,z=z*7+.5,width=6,depth=6)
                   for x in range(6) for z in range(6)]
        scene=dict(buildings=buildings,districts=[dict(id='d',parentId=None)],networks=[])
        streets=build_streets(scene,aligned=True)
        self.assertEqual('structural-streets/0.2',streets['version'])
        self.assertEqual('COMPLETE',streets['status'])
        self.assertEqual(36,len(streets['entrances']))
        self.assertEqual(0,pavement_intersections(streets,buildings))
        # Grid line z=28 is inside the dense block, along the gap, not z=24.5
        # through the centers. Assert continuous infrastructure across this row.
        runs=[s for s in streets['segments'] if s['start'][1]==s['end'][1]==28]
        self.assertEqual(42,sum(s['end'][0]-s['start'][0] for s in runs))

    def test_relations_input_order_and_building_properties_do_not_move_infrastructure(self):
        scene,_=fixture()
        frozen=copy.deepcopy(scene)
        result=build_streets(scene,aligned=True)
        self.assertEqual(frozen,scene)
        scene['networks']=[]
        scene['buildings'].reverse()
        scene['districts'].reverse()
        for b in scene['buildings']:
            b['height']=999
            b['archetype']='GATE'
        self.assertEqual(canonical_json_bytes(result),canonical_json_bytes(build_streets(scene,aligned=True)))

    def test_assignment_preserves_doors_complete_bounds_and_memberships(self):
        scene,original=fixture()
        frozen=copy.deepcopy((scene,original))
        result=assign_streets(scene,original,aligned=True)
        collector_checks.BlockCollectorTests().check_routes(scene,original,result)
        self.assertEqual(0,pavement_intersections(result,scene['buildings']))
        self.assertEqual(frozen,(scene,original))
        self.assertEqual(canonical_json_bytes(result),canonical_json_bytes(assign_streets(scene,original,aligned=True)))

    def test_wave_neighbors_retain_local_alternate_connections_and_are_bounded(self):
        grid=AccessGrid([dict(entityId='outside',x=100,z=100,width=6,depth=6)])
        grid.bounds=(-1,-1,8,8)
        seeds={((0,0),(0,1)),((6,0),(6,1)),((0,6),(1,6)),((6,6),(7,6))}
        groups=_components(_adjacency(seeds))
        budget=[0]
        keys=set(seeds)
        self.assertTrue(join_components(grid,keys,groups,budget,1000))
        adjacency=_adjacency(keys)
        self.assertEqual(1,len(_components(adjacency)))
        self.assertGreaterEqual(len(keys),len(adjacency))  # a local cycle, not only a tree
        self.assertLessEqual(budget[0],100)
        limited=set(seeds)
        self.assertFalse(join_components(grid,limited,groups,[0],0))
        self.assertEqual(seeds,limited)

    def test_limits_and_no_relations_remain_explicit(self):
        scene,original=fixture()
        with patch('metropogits.structural_streets.MAX_STEPS',0):
            self.assertEqual('PARTIAL',build_streets(scene,aligned=True)['status'])
        with patch('metropogits.structural_streets.MAX_SEED_STEPS',0):
            with self.assertRaises(ValueError):
                build_streets(scene,aligned=True)
        scene['networks']=[]
        original=derive_access_routes(scene,dict(edges=[]))
        result=assign_streets(scene,original,aligned=True)
        self.assertFalse(result['routes'])
        self.assertTrue(result['streetGrid']['segments'])
        self.assertTrue(all(not s['semantic'] for s in result['streetGrid']['segments']))

    def test_old_experiment_is_unchanged_by_optional_mode(self):
        scene,original=fixture()
        self.assertEqual(assign_streets(scene,original),assign_streets(scene,original,aligned=False))
        self.assertEqual('structural-streets/0.1',build_streets(scene)['version'])
