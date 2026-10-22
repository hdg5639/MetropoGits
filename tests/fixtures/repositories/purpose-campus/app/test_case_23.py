import unittest
from .model import Payload
from .service import run
class Case23(unittest.TestCase):
    def test_value(self):
        self.assertEqual(run(Payload('example')), 'example')
