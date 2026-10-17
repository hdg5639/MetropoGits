from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


class ContinuousIntegrationTests(unittest.TestCase):
    def test_quality_workflow_is_least_privilege_and_pinned(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        workflow = yaml.load(source, Loader=yaml.BaseLoader)

        self.assertEqual("read", workflow["permissions"]["contents"])
        self.assertEqual(
            "read", workflow["jobs"]["quality"]["permissions"]["contents"]
        )
        self.assertIn("pull_request", workflow["on"])
        self.assertIn("push", workflow["on"])
        self.assertNotIn("pull_request_target", source)
        self.assertNotIn("secrets.", source)
        self.assertIn("persist-credentials: false", source)

        references = [
            match.group(1)
            for match in re.finditer(r"uses:\s+actions/[^@\s]+@([^\s#]+)", source)
        ]
        self.assertEqual(2, len(references))
        for revision in references:
            self.assertRegex(revision, r"^[0-9a-f]{40}$")

    def test_quality_workflow_runs_required_local_gates(self):
        source = WORKFLOW.read_text(encoding="utf-8")

        for command in (
            "python -m pip check",
            "ruff check metropogits scripts tests",
            "python -m compileall -q metropogits scripts tests",
            'node --check "$script"',
            "python -m unittest discover -s tests -v",
        ):
            self.assertIn(command, source)

    def test_direct_development_requirements_are_exactly_pinned(self):
        requirements = [
            line.strip()
            for line in (ROOT / "requirements-dev.txt").read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertIn("ruff==0.14.2", requirements)
        for requirement in requirements:
            self.assertRegex(
                requirement,
                r"^[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+$",
            )


if __name__ == "__main__":
    unittest.main()
