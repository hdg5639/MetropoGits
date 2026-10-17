import json
import tempfile
import unittest
from pathlib import Path

import yaml

from metropogits.github_action import ActionInputError, run_action


ROOT = Path(__file__).parents[1]


def action_environment(workspace: Path, output_file: Path) -> dict[str, str]:
    return {
        "GITHUB_OUTPUT": str(output_file),
        "GITHUB_REPOSITORY": "example/project",
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_SHA": "0123456789abcdef",
        "GITHUB_WORKSPACE": str(workspace),
        "INPUT_OUTPUT": "generated-city",
        "INPUT_REPOSITORY": ".",
        "INPUT_THEME": "minimal",
    }


class GithubActionTests(unittest.TestCase):
    def test_action_builds_static_artifacts_and_exports_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            output_file = workspace / "github-output.txt"
            (workspace / "src").mkdir()
            (workspace / "src" / "App.java").write_text(
                "public class App {}", encoding="utf-8"
            )

            manifest = run_action(action_environment(workspace, output_file))
            outputs = dict(
                line.split("=", 1)
                for line in output_file.read_text(encoding="utf-8").splitlines()
            )
            graph = json.loads(
                (workspace / "generated-city" / "graph.ucg.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual("COMPLETE", manifest["status"])
        self.assertEqual("COMPLETE", outputs["status"])
        self.assertTrue(outputs["artifact-path"].endswith("generated-city"))
        self.assertTrue(outputs["manifest-path"].endswith("manifest.json"))
        self.assertEqual("example/project", graph["repository"]["id"])
        self.assertEqual("0123456789abcdef", graph["repository"]["revision"])
        self.assertEqual(
            "https://github.com/example/project",
            graph["repository"]["sourceUrl"],
        )

    def test_action_rejects_output_outside_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            escaped = workspace.parent / f"{workspace.name}-escaped"
            environment = action_environment(workspace, workspace / "github-output.txt")
            environment["INPUT_OUTPUT"] = f"../{escaped.name}"

            with self.assertRaisesRegex(
                ActionInputError, "must remain inside GITHUB_WORKSPACE"
            ):
                run_action(environment)

        self.assertFalse(escaped.exists())

    def test_action_rejects_absolute_repository_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            environment = action_environment(workspace, workspace / "github-output.txt")
            environment["INPUT_REPOSITORY"] = str(workspace)

            with self.assertRaisesRegex(
                ActionInputError, "must be relative to GITHUB_WORKSPACE"
            ):
                run_action(environment)

    def test_action_rejects_multiline_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            environment = action_environment(workspace, workspace / "github-output.txt")
            environment["INPUT_REPO_ID"] = "safe\nstatus=forged"

            with self.assertRaisesRegex(ActionInputError, "single line"):
                run_action(environment)

    def test_action_metadata_and_workflow_are_valid_yaml(self):
        action = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))
        workflow = yaml.load(
            (ROOT / "examples" / "github-pages.yml").read_text(encoding="utf-8"),
            Loader=yaml.BaseLoader,
        )

        self.assertEqual("composite", action["runs"]["using"])
        self.assertEqual(
            "${{ steps.build.outputs.artifact-path }}",
            action["outputs"]["artifact-path"]["value"],
        )
        self.assertEqual("read", workflow["permissions"]["contents"])
        self.assertEqual("write", workflow["jobs"]["deploy"]["permissions"]["pages"])

    def test_official_workflow_actions_are_pinned_to_full_shas(self):
        workflow = (ROOT / "examples" / "github-pages.yml").read_text(encoding="utf-8")
        official_uses = [
            line.strip().split("uses: ", 1)[1].split(" #", 1)[0]
            for line in workflow.splitlines()
            if "uses: actions/" in line
        ]

        self.assertEqual(5, len(official_uses))
        for reference in official_uses:
            _, revision = reference.rsplit("@", 1)
            self.assertRegex(revision, r"^[0-9a-f]{40}$")
        self.assertNotIn("pull_request_target", workflow)
        self.assertIn("persist-credentials: false", workflow)

    def test_action_install_uses_the_runtime_constraint_lock(self):
        action = (ROOT / "action.yml").read_text(encoding="utf-8")

        self.assertIn(
            '--constraint "$GITHUB_ACTION_PATH/requirements-lock.txt"', action
        )


if __name__ == "__main__":
    unittest.main()
