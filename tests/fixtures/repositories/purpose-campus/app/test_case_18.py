import unittest
from .model import Payload
from .service import run
from .api import get_value
class Case18(unittest.TestCase):
    def test_value(self):
        self.assertTrue(callable(get_value))
        self.assertEqual(run(Payload('example')), 'example')
