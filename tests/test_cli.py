import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as element_tree
from pathlib import Path

from metropogits.cli import build_repository
from scripts.validate_city import validate_document as validate_city_document
from scripts.validate_ucg import validate_document as validate_ucg_document


class CliTests(unittest.TestCase):
    def test_build_repository_creates_deterministic_artifact_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            repository = workspace / "repository"
            output = repository / "generated-output"
            (repository / "src").mkdir(parents=True)
            (repository / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
            (repository / "src" / "worker.ex").write_text(
                "defmodule Worker do\nend", encoding="utf-8"
            )
            marker = repository / "executed.marker"
            (repository / "src" / "danger.py").write_text(
                f"from pathlib import Path\nPath({str(marker)!r}).touch()",
                encoding="utf-8",
            )

            first_manifest = build_repository(
                repository, output, "example/project", theme="minimal"
            )
            first_bytes = {
                path.name: path.read_bytes() for path in sorted(output.iterdir())
            }
            second_manifest = build_repository(
                repository, output, "example/project", theme="minimal"
            )
            second_bytes = {
                path.name: path.read_bytes() for path in sorted(output.iterdir())
            }

            self.assertFalse(marker.exists())

        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(
            {
                "README_SNIPPET.md",
                "city.json",
                "graph.ucg.json",
                "manifest.json",
                "preview.svg",
            },
            set(first_bytes),
        )
        graph = json.loads(first_bytes["graph.ucg.json"])
        scene = json.loads(first_bytes["city.json"])
        manifest = json.loads(first_bytes["manifest.json"])
        self.assertEqual([], validate_ucg_document(graph))
        self.assertEqual([], validate_city_document(scene, graph))
        element_tree.fromstring(first_bytes["preview.svg"])
        self.assertEqual("manifest/0.1", manifest["schemaVersion"])
        self.assertNotIn(str(repository), first_bytes["manifest.json"].decode("utf-8"))

        artifacts = {item["path"]: item for item in manifest["artifacts"]}
        for name, record in artifacts.items():
            self.assertEqual(len(first_bytes[name]), record["bytes"])
            self.assertEqual(
                f"sha256:{hashlib.sha256(first_bytes[name]).hexdigest()}",
                record["sha256"],
            )

    def test_module_cli_runs_end_to_end_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            repository = workspace / "repository"
            output = workspace / "artifacts"
            repository.mkdir()
            (repository / "main.go").write_text("package main", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "metropogits",
                    "build",
                    "--repo",
                    str(repository),
                    "--repo-id",
                    "example/cli",
                    "--out",
                    str(output),
                ],
                cwd=Path(__file__).parents[1],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertTrue((output / "preview.svg").is_file())
            self.assertIn("Built 4 artifacts", completed.stdout)

    def test_module_cli_rejects_unknown_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            document = Path(temporary) / "unknown.json"
            document.write_text('{"schemaVersion":"unknown/1"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "metropogits",
                    "validate",
                    "--input",
                    str(document),
                ],
                cwd=Path(__file__).parents[1],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(2, completed.returncode)
        self.assertIn("unsupported schemaVersion", completed.stderr)

    def test_build_rejects_repository_root_as_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            (repository / "main.py").write_text("pass", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must not be the repository root"):
                build_repository(repository, repository, "example/project")


if __name__ == "__main__":
    unittest.main()
