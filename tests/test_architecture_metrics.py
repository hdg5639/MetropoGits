import copy
import unittest

from metropogits.world.architecture_catalog import compile_parts, grammar
from metropogits.world.architecture_metrics import occupancy, geometry_metrics


class RenderedGeometryMetricTests(unittest.TestCase):
    def model(self, form, angle=0, center=(0, 0), width=20, depth=14):
        model = dict(entityId=form, center=list(center), angle=angle, width=width, depth=depth, height=40)
        return dict(model, parts=compile_parts(model, grammar(form)))

    def test_actual_geometry_ignores_translation_yaw_material_and_minor_scale_changes(self):
        first = self.model('court')
        moved = self.model('court', .73, (123, -457), 30, 18)
        for part in moved['parts']:
            part['materialKind'] = 3
        self.assertEqual(occupancy(first), occupancy(moved))
        self.assertNotEqual(occupancy(first), occupancy(self.model('tower')))
        self.assertNotEqual(occupancy(self.model('tower')), occupancy(self.model('sawtooth')))

    def test_repeated_meshes_are_detected_even_if_every_catalog_label_is_different(self):
        models = [self.model('tower'), self.model('tower', .8, (40, 30)), self.model('court')]
        for i, model in enumerate(models):
            model['entityId'] = str(i)
        profiles = {str(i): dict(family='invented-label-' + str(i), verifiedRole=None,
                                massingLayout='different-label-' + str(i)) for i in range(3)}
        saved = copy.deepcopy(models)
        result = geometry_metrics(dict(parcels=models), profiles)
        self.assertEqual(result['normalizedShapeCount'], 2)
        self.assertEqual(result['largestExactRepeat'], 2)
        self.assertEqual(result['neutralRoleSources'], 3)
        self.assertEqual(models, saved)


if __name__ == '__main__':
    unittest.main()
