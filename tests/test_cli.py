import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as element_tree
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from metropogits.cli import (
    EXIT_INTERNAL_ERROR,
    EXIT_INVALID_INPUT,
    EXIT_PARTIAL,
    EXIT_RESOURCE_LIMIT,
    build_repository,
    main,
)
from scripts.validate_city import validate_document as validate_city_document
from scripts.validate_ucg import validate_document as validate_ucg_document


class CliTests(unittest.TestCase):
    def test_build_repository_creates_deterministic_artifact_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            repository = workspace / "repository"
            output = repository / "generated-output"
            (repository / "src").mkdir(parents=True)
            (repository / "src" / "main.py").write_text(
                "print('hello')", encoding="utf-8"
            )
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
                path.relative_to(output).as_posix(): path.read_bytes()
                for path in sorted(output.rglob("*"))
                if path.is_file()
            }
            second_manifest = build_repository(
                repository, output, "example/project", theme="minimal"
            )
            second_bytes = {
                path.relative_to(output).as_posix(): path.read_bytes()
                for path in sorted(output.rglob("*"))
                if path.is_file()
            }

            self.assertFalse(marker.exists())

        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(
            {
                "README_SNIPPET.md",
                "assets/viewer-activity.js",
                "assets/viewer-3d.js",
                "assets/viewer-data.js",
                "assets/viewer.css",
                "assets/viewer-filters.js",
                "assets/viewer.js",
                "city.json",
                "graph.ucg.json",
                "index.html",
                "manifest.json",
                "preview.svg",
                "showcase.svg",
            },
            set(first_bytes),
        )
        graph = json.loads(first_bytes["graph.ucg.json"])
        scene = json.loads(first_bytes["city.json"])
        manifest = json.loads(first_bytes["manifest.json"])
        self.assertEqual([], validate_ucg_document(graph))
        self.assertEqual([], validate_city_document(scene, graph))
        element_tree.fromstring(first_bytes["preview.svg"])
        element_tree.fromstring(first_bytes["showcase.svg"])
        self.assertIn(b'(showcase.svg)', first_bytes['README_SNIPPET.md'])
        self.assertEqual("manifest/0.1", manifest["schemaVersion"])
        self.assertIn("codes", manifest["diagnostics"])
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
            self.assertTrue((output / "showcase.svg").is_file())
            self.assertIn("Built 12 artifacts", completed.stdout)

    def test_build_accepts_previous_scene_and_reports_hint_churn(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            repository = workspace / "repository"
            output = workspace / "artifacts"
            (repository / "src").mkdir(parents=True)
            for index in range(30):
                (repository / "src" / f"m{index:03}.py").write_text(
                    "pass", encoding="utf-8"
                )
            arguments = [
                "build",
                "--repo",
                str(repository),
                "--repo-id",
                "example/cli-hint",
                "--out",
                str(output),
            ]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(0, main(arguments))
            before = json.loads(
                (output / "city.json").read_text(encoding="utf-8")
            )
            (repository / "src" / "0000.py").write_text("pass", encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        *arguments,
                        "--previous-scene",
                        str(output / "city.json"),
                    ]
                )
            after = json.loads(
                (output / "city.json").read_text(encoding="utf-8")
            )
            manifest = json.loads(
                (output / "manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(0, exit_code)
        before_positions = {
            item["entityId"]: (item["x"], item["z"])
            for item in before["buildings"]
        }
        after_positions = {
            item["entityId"]: (item["x"], item["z"])
            for item in after["buildings"]
        }
        self.assertEqual(
            before_positions,
            {
                entity_id: after_positions[entity_id]
                for entity_id in before_positions
            },
        )
        self.assertIn(
            {"code": "LAYOUT_HINT_APPLIED", "count": 1},
            manifest["diagnostics"]["codes"],
        )

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

    def test_json_build_reports_resource_limited_partial_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            repository = workspace / "repository"
            output = workspace / "artifacts"
            repository.mkdir()
            (repository / "a.py").write_text("pass", encoding="utf-8")
            (repository / "b.py").write_text("pass", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "metropogits",
                    "build",
                    "--repo",
                    str(repository),
                    "--repo-id",
                    "example/limited",
                    "--out",
                    str(output),
                    "--max-files",
                    "1",
                    "--json",
                ],
                cwd=Path(__file__).parents[1],
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(completed.stdout)
            manifest = json.loads(
                (output / "manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(EXIT_RESOURCE_LIMIT, completed.returncode)
        self.assertEqual("PARTIAL", payload["status"])
        self.assertEqual(EXIT_RESOURCE_LIMIT, payload["exitCode"])
        self.assertEqual(
            [{"code": "FILE_LIMIT_REACHED", "count": 1}],
            [
                item
                for item in payload["diagnostics"]["codes"]
                if item["code"] == "FILE_LIMIT_REACHED"
            ],
        )
        self.assertEqual(payload["diagnostics"], manifest["diagnostics"])

    def test_json_build_distinguishes_non_limit_partial_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            repository = workspace / "repository"
            output = workspace / "artifacts"
            repository.mkdir()
            (repository / "good.py").write_text("pass", encoding="utf-8")
            (repository / "binary.py").write_bytes(b"safe-prefix\x00binary")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--json",
                        "build",
                        "--repo",
                        str(repository),
                        "--repo-id",
                        "example/partial",
                        "--out",
                        str(output),
                    ]
                )
            payload = json.loads(stdout.getvalue())
            city_written = (output / "city.json").is_file()

        self.assertEqual(EXIT_PARTIAL, exit_code)
        self.assertEqual("PARTIAL", payload["status"])
        self.assertTrue(city_written)

    def test_json_usage_failure_is_structured(self):
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["build", "--json"])
        payload = json.loads(stdout.getvalue())

        self.assertEqual(EXIT_INVALID_INPUT, exit_code)
        self.assertEqual("FAILED", payload["status"])
        self.assertEqual("INVALID_INPUT", payload["error"]["category"])
        self.assertEqual(EXIT_INVALID_INPUT, payload["exitCode"])

    def test_json_internal_failure_hides_exception_message(self):
        stdout = io.StringIO()

        with patch("metropogits.cli._run", side_effect=RuntimeError("source secret")):
            with redirect_stdout(stdout):
                exit_code = main(["build", "--repo", ".", "--out", "dist", "--json"])
        payload = json.loads(stdout.getvalue())

        self.assertEqual(EXIT_INTERNAL_ERROR, exit_code)
        self.assertEqual("INTERNAL_ERROR", payload["error"]["category"])
        self.assertNotIn("source secret", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
