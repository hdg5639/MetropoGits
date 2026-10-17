"""Presentation-only role aggregation: membership, exclusion and LOD contracts."""
import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which("node"), "Node.js required")
class RoleLandmarkTests(unittest.TestCase):
    def test_role_landmark_contracts(self):
        result = subprocess.run(
            ["node", "--test", "tests/role_landmarks.test.mjs"],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
            encoding="utf-8", timeout=30,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
