"""Browser-free audit harness regression tests; Chrome capture stays opt-in."""
import shutil
import subprocess
import unittest
from pathlib import Path


class ViewerAuditTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for audit tests")
    def test_audit_harness_contracts(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["node", "--test", "tests/viewer_audit.test.mjs"],
            cwd=root, capture_output=True, text=True, encoding="utf-8",
            check=False, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
