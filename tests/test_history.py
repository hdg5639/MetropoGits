from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from metropogits.history import HistoryError, HistorySnapshot, build_history
from metropogits.layout import generate_city
from metropogits.viewer import ViewerError, render_history_viewer
from scripts.canonical_json import canonical_json_bytes, loads_strict_json
from scripts.validate_history import SCHEMA_PATH, validate_document


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "ucg" / "valid" / "spring-minimal.json"


def load_graph(revision: str) -> dict:
    graph = loads_strict_json(FIXTURE.read_text(encoding="utf-8"))
    graph["repository"]["revision"] = revision
    return graph


def snapshots() -> list[HistorySnapshot]:
    first = load_graph("revision-1")
    second = copy.deepcopy(first)
    second["repository"]["revision"] = "revision-2"
    service = next(
        entity
        for entity in second["entities"]
        if entity["id"] == "demo:file:src/UserService.java"
    )
    service["language"] = "kotlin"
    second["entities"].append(
        {
            "id": "demo:file:src/NewWorker.java",
            "kind": "FILE",
            "language": "java",
            "path": "src/NewWorker.java",
            "roles": [],
        }
    )
    second["entities"].sort(key=lambda item: item["id"])
    third = copy.deepcopy(second)
    third["repository"]["revision"] = "revision-3"
    third["entities"] = [
        entity
        for entity in third["entities"]
        if entity["id"] != "demo:file:src/NewWorker.java"
    ]
    return [
        HistorySnapshot(first, generate_city(first)),
        HistorySnapshot(second, generate_city(second)),
        HistorySnapshot(third, generate_city(third)),
    ]


class HistoryTests(unittest.TestCase):
    def test_schema_is_valid_draft_2020_12(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)

    def test_history_tracks_added_removed_changed_and_lineage(self):
        timeline = build_history(snapshots())

        self.assertEqual([], validate_document(timeline))
        self.assertEqual(
            ["revision-1", "revision-2", "revision-3"],
            [frame["revision"] for frame in timeline["frames"]],
        )
        first_transition = timeline["transitions"][0]
        self.assertEqual(
            ["demo:file:src/NewWorker.java"], first_transition["addedEntityIds"]
        )
        self.assertEqual(
            ["demo:file:src/UserService.java"],
            first_transition["changedEntityIds"],
        )
        self.assertEqual(
            ["demo:file:src/NewWorker.java"],
            timeline["transitions"][1]["removedEntityIds"],
        )
        worker = next(
            lineage
            for lineage in timeline["lineages"]
            if lineage["path"] == "src/NewWorker.java"
        )
        self.assertEqual("revision-2", worker["firstRevision"])
        self.assertEqual("revision-2", worker["lastRevision"])
        self.assertEqual(1, len(worker["revisions"]))

    def test_history_is_deterministic(self):
        first = build_history(snapshots())
        second = build_history(snapshots())

        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_history_rejects_missing_duplicate_and_cross_repository_revisions(self):
        missing = snapshots()[:2]
        missing[1].ucg["repository"]["revision"] = None
        with self.assertRaisesRegex(HistoryError, "must include a revision"):
            build_history(missing)

        duplicate = snapshots()[:2]
        duplicate[1].ucg["repository"]["revision"] = "revision-1"
        duplicate[1] = HistorySnapshot(
            duplicate[1].ucg, generate_city(duplicate[1].ucg)
        )
        with self.assertRaisesRegex(HistoryError, "duplicate history revision"):
            build_history(duplicate)

        foreign = snapshots()[:2]
        foreign[1].ucg["repository"]["id"] = "other/repository"
        with self.assertRaisesRegex(HistoryError, "same repository"):
            build_history(foreign)

        conflicting_path = snapshots()[:2]
        service = next(
            entity
            for entity in conflicting_path[1].ucg["entities"]
            if entity["id"] == "demo:file:src/UserService.java"
        )
        service["path"] = "src/RenamedService.java"
        conflicting_path[1] = HistorySnapshot(
            conflicting_path[1].ucg, generate_city(conflicting_path[1].ucg)
        )
        with self.assertRaisesRegex(HistoryError, "maps to multiple paths"):
            build_history(conflicting_path)

    def test_history_viewer_embeds_safe_revision_switcher(self):
        ordered = snapshots()
        timeline = build_history(ordered)
        viewer_snapshots = [
            {"scene": item.scene, "ucg": item.ucg} for item in ordered
        ]

        artifacts = render_history_viewer(timeline, viewer_snapshots)

        self.assertEqual(
            {
                "assets/viewer-activity.js",
                "assets/viewer-data.js",
                "assets/viewer-filters.js",
                "assets/viewer-history.js",
                "assets/viewer.js",
                "assets/viewer.css",
                "index.html",
            },
            set(artifacts),
        )
        html = artifacts["index.html"].decode("utf-8")
        self.assertIn('id="history-revision"', html)
        self.assertIn("viewer-history.js", html)
        self.assertNotIn("innerHTML", artifacts["assets/viewer-history.js"].decode())

    def test_history_viewer_rejects_frame_mismatch(self):
        ordered = snapshots()
        timeline = build_history(ordered)
        viewer_snapshots = [
            {"scene": item.scene, "ucg": item.ucg} for item in ordered
        ]
        viewer_snapshots[0] = copy.deepcopy(viewer_snapshots[0])
        viewer_snapshots[0]["ucg"]["repository"]["revision"] = "wrong"

        with self.assertRaisesRegex(ViewerError, "does not match"):
            render_history_viewer(timeline, viewer_snapshots)

    def test_history_viewer_escapes_untrusted_revision(self):
        ordered = snapshots()[:2]
        ordered[1].ucg["repository"]["revision"] = "</script><img>"
        ordered[1] = HistorySnapshot(
            ordered[1].ucg, generate_city(ordered[1].ucg)
        )
        artifacts = render_history_viewer(
            build_history(ordered),
            [{"scene": item.scene, "ucg": item.ucg} for item in ordered],
        )
        viewer_data = artifacts["assets/viewer-data.js"].decode("utf-8")

        self.assertNotIn("</script>", viewer_data)
        self.assertIn(r"\u003c/script\u003e", viewer_data)

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_history_viewer_javascript_parses(self):
        ordered = snapshots()
        artifacts = render_history_viewer(
            build_history(ordered),
            [{"scene": item.scene, "ucg": item.ucg} for item in ordered],
        )
        with tempfile.TemporaryDirectory() as temporary:
            for name in ("viewer-history.js", "viewer.js"):
                script = Path(temporary) / name
                script.write_bytes(artifacts[f"assets/{name}"])
                completed = subprocess.run(
                    ["node", "--check", str(script)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)

    def test_cli_builds_static_history_artifacts(self):
        ordered = snapshots()[:2]
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            snapshot_paths: list[Path] = []
            for index, snapshot in enumerate(ordered):
                path = workspace / f"snapshot-{index}"
                path.mkdir()
                (path / "graph.ucg.json").write_bytes(
                    canonical_json_bytes(snapshot.ucg)
                )
                (path / "city.json").write_bytes(
                    canonical_json_bytes(snapshot.scene)
                )
                snapshot_paths.append(path)
            output = workspace / "history"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "metropogits",
                    "history",
                    "--snapshot",
                    str(snapshot_paths[0]),
                    "--snapshot",
                    str(snapshot_paths[1]),
                    "--out",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            timeline = json.loads((output / "history.json").read_text("utf-8"))
            overlapping = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "metropogits",
                    "history",
                    "--snapshot",
                    str(snapshot_paths[0]),
                    "--snapshot",
                    str(snapshot_paths[1]),
                    "--out",
                    str(snapshot_paths[0]),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual([], validate_document(timeline))
        self.assertIn("Built history with 2 revisions", completed.stdout)
        self.assertEqual(2, overlapping.returncode)
        self.assertIn("must not overlap", overlapping.stderr)


if __name__ == "__main__":
    unittest.main()
