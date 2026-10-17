from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def pinned_requirements(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = line.split(";", 1)[0].strip()
        name, version = requirement.split("==", 1)
        result[name.lower().replace("_", "-")] = version
    return result


class GovernanceTests(unittest.TestCase):
    def test_sensitive_paths_have_explicit_owners(self):
        codeowners = (ROOT / ".github" / "CODEOWNERS").read_text(
            encoding="utf-8"
        )

        for path in (
            "* @hdg5639",
            "/.github/ @hdg5639",
            "/action.yml @hdg5639",
            "/catalog/ @hdg5639",
            "/metropogits/analyzers/ @hdg5639",
            "/schemas/ @hdg5639",
            "/scripts/ @hdg5639",
        ):
            self.assertIn(path, codeowners)

    def test_security_and_pull_request_policies_cover_release_boundaries(self):
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        pull_request = (
            ROOT / ".github" / "pull_request_template.md"
        ).read_text(encoding="utf-8")

        self.assertIn("security/advisories/new", security)
        self.assertIn("Do not open a public issue", security)
        self.assertIn("must never execute analyzed repository code", security)
        self.assertIn("one independently reviewable task per commit", contributing)
        self.assertIn("Generated `dist/` content", contributing)
        self.assertIn("New dependencies are pinned", pull_request)
        self.assertIn("Semantic claims include evidence", pull_request)

    def test_dependency_inventory_matches_the_python_311_lock(self):
        locked = pinned_requirements(ROOT / "requirements-lock.txt")
        direct = pinned_requirements(ROOT / "requirements-dev.txt")
        inventory = (ROOT / "docs" / "DEPENDENCY_INVENTORY.md").read_text(
            encoding="utf-8"
        )
        expected = {
            "attrs": "25.4.0",
            "jsonschema": "4.25.1",
            "jsonschema-specifications": "2025.9.1",
            "pyyaml": "6.0.2",
            "referencing": "0.37.0",
            "rpds-py": "0.28.0",
            "ruff": "0.14.2",
            "typing-extensions": "4.15.0",
        }

        self.assertEqual(expected, locked)
        for name, version in direct.items():
            self.assertEqual(version, locked[name])
        for name, version in locked.items():
            display_name = {"pyyaml": "PyYAML", "ruff": "Ruff"}.get(name, name)
            self.assertRegex(
                inventory,
                rf"\| \[{re.escape(display_name)}\]\([^\n]+\) \| {re.escape(version)} \|",
            )

        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(["jsonschema==4.25.1"], project["project"]["dependencies"])
        for build_requirement in project["build-system"]["requires"]:
            name, version = build_requirement.split("==", 1)
            self.assertRegex(
                inventory,
                rf"\| \[{re.escape(name)}\]\([^\n]+\) \| {re.escape(version)} \|",
            )

    def test_missing_project_license_is_an_explicit_release_blocker(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        inventory = (ROOT / "docs" / "DEPENDENCY_INVENTORY.md").read_text(
            encoding="utf-8"
        )
        license_exists = any(
            (ROOT / name).is_file()
            for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")
        )

        if license_exists:
            self.assertNotIn("has not selected a project license", contributing)
            self.assertNotIn("currently has no `LICENSE`", inventory)
        else:
            self.assertIn("has not selected a project license", contributing)
            self.assertIn("currently has no `LICENSE`", inventory)

    def test_stable_spatial_allocator_decision_is_recorded(self):
        adr = (ROOT / "docs" / "adr" / "ADR-004.md").read_text(
            encoding="utf-8"
        )

        for required_text in (
            "Status: Accepted",
            "hierarchical-paged/1.0",
            "hierarchical-paged/1.1",
            "hierarchical-paged/1.2",
            "hierarchical-paged/1.3",
            "hierarchical-paged/1.4",
            "hierarchical-paged/1.5",
            "empty directory with exactly one child shares that child's footprint",
            "4 by 4 footprint to 6 by 6",
            "small width bias",
            "previous scene as a hint, never authority",
            "child district outside its parent district",
            "65, 100, and at least 1,000 files",
            "cold-layout collision fixture",
        ):
            self.assertIn(required_text, adr)
        self.assertRegex(adr, r"moves zero existing\s+buildings")


if __name__ == "__main__":
    unittest.main()
