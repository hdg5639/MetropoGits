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

    def test_project_uses_apache_2_license(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        inventory = (ROOT / "docs" / "DEPENDENCY_INVENTORY.md").read_text(
            encoding="utf-8"
        )
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertIn("Apache License", license_text)
        self.assertIn("Version 2.0, January 2004", license_text)
        self.assertIn("END OF TERMS AND CONDITIONS", license_text)
        self.assertEqual({"file": "LICENSE"}, project["project"]["license"])
        self.assertIn("Apache License 2.0", contributing)
        self.assertIn("No bundled attribution currently requires", inventory)

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
            "hierarchical-paged/1.6",
            "hierarchical-paged/1.7",
            "hierarchical-paged/1.8",
            "hierarchical-paged/1.9",
            "empty directory with exactly one child shares that child's footprint",
            "4 by 4 footprint to 6 by 6",
            "small width bias",
            "unused row and column",
            "previous scene as a hint, never authority",
            "child district outside its parent district",
            "65, 100, and at least 1,000 files",
            "cold-layout collision fixture",
        ):
            self.assertIn(required_text, adr)
        self.assertRegex(adr, r"moves zero existing\s+buildings")

    def test_browser_native_webgl_runtime_is_recorded(self):
        decision = (ROOT / "docs" / "adr" / "ADR-002.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Status: Accepted", decision)
        self.assertIn("browser-native JavaScript", decision)
        self.assertIn("automatic fallback", decision)
        self.assertIn("performs no network request", decision)

    def test_stable_v1_requires_genuine_3d_with_a_fallback(self):
        decision = (ROOT / "docs" / "adr" / "ADR-005.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Status: Accepted", decision)
        self.assertIn("genuine interactive 3D viewer", decision)
        self.assertIn("graceful fallback", decision)
        self.assertIn("existing versioned City Scene and UCG contracts", decision)

    def test_publication_requires_explicit_maintainer_approval(self):
        decision = (ROOT / "docs" / "adr" / "ADR-007.md").read_text(
            encoding="utf-8"
        )
        active_workflows = list((ROOT / ".github" / "workflows").glob("*.yml"))

        self.assertIn("Status: Accepted", decision)
        self.assertIn("public repository conversion and Pages activation are deferred", decision)
        self.assertIn("explicitly approves", decision)
        self.assertEqual(["ci.yml"], [path.name for path in active_workflows])


if __name__ == "__main__":
    unittest.main()
