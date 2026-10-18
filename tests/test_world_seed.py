import unittest

from metropogits.world.seed import derive, draw, world_seed


class WorldSeedTests(unittest.TestCase):
    def test_domain_separation_and_unicode_normalization(self):
        self.assertNotEqual(derive("ab", "c"), derive("a", "bc"))
        self.assertEqual(derive("caf\u00e9"), derive("cafe\u0301"))
        self.assertNotEqual(derive("district", "a"), derive("building", "a"))
        self.assertEqual(len(derive("a")), 16)

    def test_counter_streams_are_order_independent(self):
        seed = world_seed("owner/project")
        streams = {name: derive(seed, "district", name) for name in ("a", "b")}
        expected = {
            name: [draw(streams[name], i) for i in range(4)] for name in streams
        }
        draw(derive(seed, "district", "unrelated"), 100)
        actual = {
            name: [draw(streams[name], i) for i in range(4)]
            for name in reversed(streams)
        }
        self.assertEqual(actual, expected)
        self.assertTrue(all(0 <= x < 1 for values in actual.values() for x in values))
        self.assertNotEqual(seed, world_seed("owner/project", "other"))
        with self.assertRaises(ValueError):
            draw(seed, -1)

    def test_namespace_and_seed_limits(self):
        for namespace, override in (("", None), ("x" * 4097, None), ("ok", "x" * 4097)):
            with self.assertRaises(ValueError):
                world_seed(namespace, override)
