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

from metropogits.layout import generate_city
from metropogits.metropolis import (
    MetropolisError,
    MetropolisMember,
    build_metropolis,
)
from metropogits.viewer import ViewerError, render_metropolis_viewer
from scripts.canonical_json import canonical_json_bytes, loads_strict_json
from scripts.stable_ids import make_edge_id
from scripts.validate_city import validate_document as validate_city_document
from scripts.validate_metropolis import (
    LINKS_SCHEMA_PATH,
    SCHEMA_PATH,
    validate_document,
)
from scripts.validate_ucg import validate_document as validate_ucg_document


ROOT = Path(__file__).parents[1]
UCG_FIXTURE = ROOT / "tests" / "fixtures" / "ucg" / "valid" / "spring-minimal.json"
LINK_FIXTURE = ROOT / "tests" / "fixtures" / "metropolis" / "links.json"


def member(repository_id: str) -> MetropolisMember:
    graph = loads_strict_json(UCG_FIXTURE.read_text(encoding="utf-8"))
    old_ids = [entity["id"] for entity in graph["entities"]]
    id_mapping = {
        entity_id: entity_id.replace("demo:", f"{repository_id}:", 1)
        for entity_id in old_ids
    }
    graph["repository"]["id"] = repository_id
    graph["repository"]["revision"] = f"{repository_id}-revision"
    for entity in graph["entities"]:
        entity["id"] = id_mapping[entity["id"]]
    for edge in graph["edges"]:
        edge["from"] = id_mapping[edge["from"]]
        edge["to"] = id_mapping[edge["to"]]
        edge["id"] = make_edge_id(
            edge["from"], edge["type"], edge["to"], "fixture"
        )
    graph["entities"].sort(key=lambda item: item["id"])
    graph["edges"].sort(key=lambda item: item["id"])
    return MetropolisMember(graph, generate_city(graph))


def link_manifest() -> dict:
    return loads_strict_json(LINK_FIXTURE.read_text(encoding="utf-8"))


class MetropolisTests(unittest.TestCase):
    def test_schemas_are_valid_draft_2020_12(self):
        for path in (LINKS_SCHEMA_PATH, SCHEMA_PATH):
            Draft202012Validator.check_schema(
                json.loads(path.read_text(encoding="utf-8"))
            )

    def test_link_fixture_is_valid(self):
        self.assertEqual([], validate_document(link_manifest()))

    def test_build_merges_cities_and_only_verified_links(self):
        artifacts = build_metropolis(
            [member("other"), member("demo")], link_manifest()
        )

        self.assertEqual([], validate_document(artifacts.document))
        self.assertEqual([], validate_ucg_document(artifacts.ucg))
        self.assertEqual([], validate_city_document(artifacts.scene, artifacts.ucg))
        self.assertEqual(
            ["demo", "other"],
            [item["id"] for item in artifacts.document["repositories"]],
        )
        self.assertEqual(4, len(artifacts.scene["buildings"]))
        cross_edges = [
            edge for edge in artifacts.ucg["edges"] if edge["type"] == "HTTP_CALL"
        ]
        self.assertEqual(1, len(cross_edges))
        self.assertTrue(cross_edges[0]["evidenceIds"])
        self.assertEqual(
            1,
            sum(
                item["code"] == "FEDERATION_LINK_UNRESOLVED"
                for item in artifacts.ucg["diagnostics"]
            ),
        )
        self.assertEqual(
            1,
            sum(
                network["kind"] == "HTTP_HIGHWAY"
                for network in artifacts.scene["networks"]
            ),
        )

    def test_build_is_deterministic_across_member_order(self):
        first = build_metropolis([member("demo"), member("other")], link_manifest())
        second = build_metropolis([member("other"), member("demo")], link_manifest())

        self.assertEqual(
            canonical_json_bytes(first.document), canonical_json_bytes(second.document)
        )
        self.assertEqual(canonical_json_bytes(first.ucg), canonical_json_bytes(second.ucg))
        self.assertEqual(
            canonical_json_bytes(first.scene), canonical_json_bytes(second.scene)
        )

    def test_missing_evidence_and_target_are_rejected(self):
        missing_evidence = link_manifest()
        missing_evidence["links"][0]["evidenceRefs"][0]["evidenceId"] = "missing"
        with self.assertRaisesRegex(MetropolisError, "missing evidence"):
            build_metropolis(
                [member("demo"), member("other")], missing_evidence
            )

        missing_target = link_manifest()
        missing_target["links"][0]["to"]["entityId"] = "other:file:missing.java"
        with self.assertRaisesRegex(MetropolisError, "target must resolve"):
            build_metropolis([member("demo"), member("other")], missing_target)

    def test_unresolved_link_cannot_claim_a_target_entity(self):
        manifest = link_manifest()
        manifest["links"][1]["to"]["entityId"] = "other:file:src/UserService.java"

        errors = validate_document(manifest)

        self.assertTrue(any("UNRESOLVED" in error for error in errors), errors)

    def test_viewer_exposes_verified_and_unresolved_outcomes(self):
        artifacts = build_metropolis(
            [member("demo"), member("other")], link_manifest()
        )
        viewer = render_metropolis_viewer(
            artifacts.document, artifacts.scene, artifacts.ucg
        )

        self.assertIn("assets/viewer-metropolis.js", viewer)
        self.assertIn("assets/viewer-3d.js", viewer)
        self.assertIn('id="metropolis-link"', viewer["index.html"].decode("utf-8"))
        script = viewer["assets/viewer-metropolis.js"].decode("utf-8")
        data = viewer["assets/viewer-data.js"].decode("utf-8")
        self.assertNotIn("innerHTML", script)
        self.assertIn("UNRESOLVED", data)
        self.assertIn("evidenceRefs", script)

    def test_viewer_rejects_digest_mismatch(self):
        artifacts = build_metropolis(
            [member("demo"), member("other")], link_manifest()
        )
        document = copy.deepcopy(artifacts.document)
        document["mergedCityDigest"] = "sha256:" + "0" * 64

        with self.assertRaisesRegex(ViewerError, "digests do not match"):
            render_metropolis_viewer(document, artifacts.scene, artifacts.ucg)

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_metropolis_javascript_parses(self):
        artifacts = build_metropolis(
            [member("demo"), member("other")], link_manifest()
        )
        viewer = render_metropolis_viewer(
            artifacts.document, artifacts.scene, artifacts.ucg
        )
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "viewer-metropolis.js"
            script.write_bytes(viewer["assets/viewer-metropolis.js"])
            completed = subprocess.run(
                ["node", "--check", str(script)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)

    def test_cli_builds_metropolis_artifacts(self):
        members = [member("demo"), member("other")]
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            member_paths: list[Path] = []
            for index, item in enumerate(members):
                path = workspace / f"member-{index}"
                path.mkdir()
                (path / "graph.ucg.json").write_bytes(canonical_json_bytes(item.ucg))
                (path / "city.json").write_bytes(canonical_json_bytes(item.scene))
                member_paths.append(path)
            links_path = workspace / "links.json"
            links_path.write_bytes(canonical_json_bytes(link_manifest()))
            output = workspace / "metropolis"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "metropogits",
                    "metropolis",
                    "--member",
                    str(member_paths[0]),
                    "--member",
                    str(member_paths[1]),
                    "--links",
                    str(links_path),
                    "--out",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            document = json.loads((output / "metropolis.json").read_text("utf-8"))

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual([], validate_document(document))
        self.assertIn("Built metropolis with 2 repositories", completed.stdout)


if __name__ == "__main__":
    unittest.main()
