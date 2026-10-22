import math
import unittest

from metropogits.street_diagonals import overlap
from metropogits.world.compound_sites import units, subdivision
from metropogits.world.geometry import rectangle, ribbon


class CompoundSiteTests(unittest.TestCase):
    def test_whole_site_reservation_preserves_every_variable_source_and_exterior_access(self):
        members = [dict(entityId=f'file:{i}', cohortId='proved-cohort', width=w, depth=d,
                        blockProfile='CAMPUS') for i, (w, d) in enumerate(((36, 18), (24, 14), (10, 8), (6, 6)))]
        request, = units(members)
        self.assertGreater(request['width'] * request['depth'], sum(b['width'] * b['depth'] for b in members))
        for angle in (0, .47, 1.7, -2.2):
            c, s = math.cos(angle), math.sin(angle)
            slot = dict(center=[12, -30], angle=angle,
                        streetPoint=[12 - s * (request['depth'] / 2 + 4), -30 + c * (request['depth'] / 2 + 4)])
            choices, walks = subdivision(request, slot, 'fixed')
            self.assertEqual({p['entityId'] for p in choices}, {b['entityId'] for b in members})
            self.assertEqual(len(walks), 5)
            sources = {b['entityId']: b for b in members}
            footprints = [rectangle(p['center'], p['angle'], sources[p['entityId']]['width'], sources[p['entityId']]['depth']) for p in choices]
            for i, p in enumerate(choices):
                self.assertEqual(p['blockProfile'], 'CAMPUS')
                self.assertTrue(all(not overlap(footprints[i], other) for other in footprints[i + 1:]))
                self.assertTrue(all(not overlap(footprints[i], ribbon(r['start'], r['end'], r['width'])) for r in walks))
                access = ribbon(p['entrance'], p['streetPoint'], .7)
                self.assertTrue(all(not overlap(access, other) for j, other in enumerate(footprints) if i != j))

    def test_unrelated_sources_cannot_become_a_shared_facility(self):
        population = [dict(entityId=f'file:{i}', width=12, depth=10) for i in range(5)]
        self.assertEqual(units(population), population)
