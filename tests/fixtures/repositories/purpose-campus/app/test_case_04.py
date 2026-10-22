import unittest
from .model import Payload
from .service import run
from .data import frame
from .store import engine
class Case04(unittest.TestCase):
    def test_value(self):
        self.assertIsNotNone(frame)
        self.assertIsNotNone(engine)
        self.assertEqual(run(Payload('example')), 'example')
