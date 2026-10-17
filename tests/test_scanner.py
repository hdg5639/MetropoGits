import tempfile
import unittest
from pathlib import Path

from metropogits.scanner import (
    ScanLimits,
    ScannerError,
    build_structural_ucg,
    scan_repository,
)
from scripts.canonical_json import canonical_json_bytes
from scripts.validate_ucg import validate_document


class ScannerTests(unittest.TestCase):
    def test_scan_builds_deterministic_structural_ucg(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "src" / "feature").mkdir(parents=True)
            (root / "node_modules").mkdir()
            (root / "src" / "App.java").write_text("class App {}", encoding="utf-8")
            (root / "src" / "feature" / "worker.ex").write_text(
                "defmodule Worker do\nend", encoding="utf-8"
            )
            (root / "node_modules" / "ignored.js").write_text(
                "alert('ignored')", encoding="utf-8"
            )
            (root / "README.md").write_text("documentation", encoding="utf-8")
            (root / ".env").write_text("TOKEN=secret", encoding="utf-8")
            (root / "binary.py").write_bytes(b"print('x')\x00binary")

            first = build_structural_ucg(scan_repository(root), "example/repo")
            second = build_structural_ucg(scan_repository(root), "example/repo")

        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        self.assertEqual([], validate_document(first))
        files = [entity for entity in first["entities"] if entity["kind"] == "FILE"]
        self.assertEqual(
            ["src/App.java", "src/feature/worker.ex"],
            [entity["path"] for entity in files],
        )
        self.assertEqual(["java", "elixir"], [entity["language"] for entity in files])
        self.assertTrue(all(edge["type"] == "CONTAINS" for edge in first["edges"]))
        self.assertTrue(
            any(item["code"] == "BINARY_FILE_SKIPPED" for item in first["diagnostics"])
        )
        self.assertFalse(
            any("secret" in str(item).lower() for item in first["diagnostics"])
        )

    def test_oversized_file_is_skipped_with_diagnostic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "large.py").write_text("x" * 11, encoding="utf-8")

            result = scan_repository(root, ScanLimits(max_file_bytes=10))

        self.assertEqual((), result.files)
        self.assertTrue(
            any(item["code"] == "FILE_SIZE_LIMIT" for item in result.diagnostics)
        )

    def test_utf8_character_split_at_sniff_boundary_is_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "unicode.py").write_text("aaaérest", encoding="utf-8")

            result = scan_repository(root, ScanLimits(sniff_bytes=4))

        self.assertEqual(["unicode.py"], [item.path for item in result.files])

    def test_file_limit_returns_bounded_partial_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("a.py", "b.py", "c.py"):
                (root / name).write_text("pass", encoding="utf-8")

            result = scan_repository(root, ScanLimits(max_files=2))

        self.assertEqual(["a.py", "b.py"], [item.path for item in result.files])
        self.assertTrue(
            any(item["code"] == "FILE_LIMIT_REACHED" for item in result.diagnostics)
        )

    def test_total_size_limit_returns_bounded_partial_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.py").write_text("pass", encoding="utf-8")
            (root / "b.py").write_text("pass", encoding="utf-8")

            result = scan_repository(root, ScanLimits(max_total_bytes=6))

        self.assertEqual(["a.py"], [item.path for item in result.files])
        self.assertTrue(
            any(
                item["code"] == "TOTAL_SIZE_LIMIT_REACHED"
                for item in result.diagnostics
            )
        )

    def test_depth_limit_skips_deeper_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "one" / "two").mkdir(parents=True)
            (root / "one" / "two" / "deep.py").write_text("pass", encoding="utf-8")

            result = scan_repository(root, ScanLimits(max_depth=1))

        self.assertEqual((), result.files)
        self.assertTrue(
            any(item["code"] == "DEPTH_LIMIT_REACHED" for item in result.diagnostics)
        )

    def test_scanner_never_executes_source_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "executed.marker"
            (root / "malicious.py").write_text(
                f"from pathlib import Path\nPath({str(marker)!r}).touch()",
                encoding="utf-8",
            )

            result = scan_repository(root)

            self.assertFalse(marker.exists())

        self.assertEqual(1, len(result.files))

    def test_maven_dependencies_create_manifest_evidenced_edges(self):
        fixture = Path(__file__).parent / "fixtures" / "repositories" / "maven-manifest"

        scan = scan_repository(fixture)
        graph = build_structural_ucg(scan, "example/maven")

        self.assertEqual(["pom.xml"], [item.path for item in scan.manifests])
        self.assertEqual(
            ["org.springframework:spring-context"],
            [
                dependency.coordinate
                for dependency in scan.manifests[0].dependencies
            ],
        )
        dependencies = [
            edge for edge in graph["edges"] if edge["type"] == "DEPENDS_ON"
        ]
        self.assertEqual(1, len(dependencies))
        entities = {item["id"]: item for item in graph["entities"]}
        self.assertEqual("MODULE", entities[dependencies[0]["from"]]["kind"])
        self.assertEqual(
            "EXTERNAL_PACKAGE", entities[dependencies[0]["to"]]["kind"]
        )
        evidence = {item["evidenceId"]: item for item in graph["evidence"]}
        self.assertEqual(
            "MANIFEST", evidence[dependencies[0]["evidenceIds"][0]]["kind"]
        )
        self.assertFalse(
            any(
                entity.get("technologies")
                for entity in graph["entities"]
            )
        )
        self.assertEqual([], validate_document(graph))

    def test_shared_maven_dependency_uses_one_external_package_entity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in (root / "first", root / "second"):
                directory.mkdir()
                (directory / "pom.xml").write_text(
                    """<project><dependencies><dependency>
<groupId>com.example</groupId><artifactId>shared</artifactId>
</dependency></dependencies></project>""",
                    encoding="utf-8",
                )
            (root / "App.java").write_text("class App {}", encoding="utf-8")

            graph = build_structural_ucg(scan_repository(root), "example/maven")

        packages = [
            entity
            for entity in graph["entities"]
            if entity["kind"] == "EXTERNAL_PACKAGE"
        ]
        dependencies = [
            edge for edge in graph["edges"] if edge["type"] == "DEPENDS_ON"
        ]
        self.assertEqual(1, len(packages))
        self.assertEqual(2, len(dependencies))
        self.assertEqual([], validate_document(graph))

    def test_gradle_literal_dependencies_create_manifest_evidenced_edges(self):
        fixture = Path(__file__).parent / "fixtures" / "repositories" / "gradle-manifest"

        scan = scan_repository(fixture)
        graph = build_structural_ucg(scan, "example/gradle")

        self.assertEqual(["build.gradle.kts"], [item.path for item in scan.manifests])
        self.assertEqual("gradle", scan.manifests[0].format)
        self.assertEqual(
            ["org.springframework:spring-context"],
            [item.coordinate for item in scan.manifests[0].dependencies],
        )
        dependency = next(
            edge for edge in graph["edges"] if edge["type"] == "DEPENDS_ON"
        )
        evidence = {item["evidenceId"]: item for item in graph["evidence"]}
        manifest_evidence = evidence[dependency["evidenceIds"][0]]
        self.assertEqual("manifest.gradle/0.1", manifest_evidence["extractor"])
        self.assertEqual("gradle.dependency", manifest_evidence["ruleId"])
        package = next(
            item for item in graph["entities"] if item["id"] == dependency["to"]
        )
        self.assertEqual(
            "maven/org/springframework/spring-context", package["path"]
        )
        self.assertEqual([], validate_document(graph))

    def test_gradle_parser_ignores_comments_dynamic_and_project_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "executed.marker"
            (root / "App.kt").write_text("class App", encoding="utf-8")
            (root / "build.gradle").write_text(
                '''def documentation = """
dependencies {
  implementation 'string:ignored:1.0'
}
"""
dependencies {
  // implementation 'commented:dependency:1.0'
  /* implementation 'blocked:dependency:1.0' */
  implementation project(':local')
  implementation files('local.jar')
  implementation "${dynamic}:artifact:1.0"
  implementation 'literal:accepted:1.0'
}; implementation 'outside:ignored:1.0'
file('executed.marker').createNewFile()
''',
                encoding="utf-8",
            )

            scan = scan_repository(root)

            self.assertFalse(marker.exists())

        self.assertEqual(
            ["literal:accepted"],
            [item.coordinate for item in scan.manifests[0].dependencies],
        )

    def test_npm_dependencies_create_manifest_evidenced_edges(self):
        fixture = Path(__file__).parent / "fixtures" / "repositories" / "npm-manifest"

        scan = scan_repository(fixture)
        graph = build_structural_ucg(scan, "example/npm")

        self.assertEqual(["package.json"], [item.path for item in scan.manifests])
        self.assertEqual("npm", scan.manifests[0].format)
        self.assertEqual(
            ["@types/node", "react", "redis"],
            [item.coordinate for item in scan.manifests[0].dependencies],
        )
        dependencies = [
            edge for edge in graph["edges"] if edge["type"] == "DEPENDS_ON"
        ]
        self.assertEqual(3, len(dependencies))
        evidence = {item["evidenceId"]: item for item in graph["evidence"]}
        self.assertTrue(
            all(
                evidence[edge["evidenceIds"][0]]["extractor"]
                == "manifest.npm/0.1"
                for edge in dependencies
            )
        )
        package_paths = {
            item["path"]
            for item in graph["entities"]
            if item["kind"] == "EXTERNAL_PACKAGE"
        }
        self.assertEqual({"npm/@types/node", "npm/react", "npm/redis"}, package_paths)
        self.assertEqual([], validate_document(graph))

    def test_npm_parser_rejects_duplicate_keys_and_ignores_local_specifiers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "index.js").write_text("export {};", encoding="utf-8")
            (root / "package.json").write_text(
                '{"dependencies":{"safe":"1"},"dependencies":{"bad":"2"}}',
                encoding="utf-8",
            )

            invalid = scan_repository(root)

            (root / "package.json").write_text(
                """{
  "dependencies": {
    "local-file": "file:../local",
    "local-link": "link:../local",
    "local-workspace": "workspace:*",
    "alias": "npm:real-package@1.0.0",
    "remote": "^1.0.0"
  }
}""",
                encoding="utf-8",
            )
            local = scan_repository(root)

        self.assertEqual((), invalid.manifests)
        self.assertTrue(
            any(
                item["code"] == "MANIFEST_PARSE_FAILED"
                for item in invalid.diagnostics
            )
        )
        self.assertEqual(
            ["remote"],
            [item.coordinate for item in local.manifests[0].dependencies],
        )

    def test_npm_lockfile_uses_only_root_direct_dependencies(self):
        fixture = Path(__file__).parent / "fixtures" / "repositories" / "npm-lockfile"

        scan = scan_repository(fixture)
        graph = build_structural_ucg(scan, "example/npm-lock")

        self.assertEqual(["package-lock.json"], [item.path for item in scan.manifests])
        self.assertEqual("npm-lock", scan.manifests[0].format)
        self.assertEqual(
            ["@types/node", "react"],
            [item.coordinate for item in scan.manifests[0].dependencies],
        )
        package_paths = {
            item["path"]
            for item in graph["entities"]
            if item["kind"] == "EXTERNAL_PACKAGE"
        }
        self.assertNotIn("npm/transitive-only", package_paths)
        self.assertEqual({"npm/@types/node", "npm/react"}, package_paths)
        self.assertEqual([], validate_document(graph))

    def test_legacy_npm_lockfile_is_rejected_without_guessing_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "index.js").write_text("export {};", encoding="utf-8")
            (root / "package-lock.json").write_text(
                '{"lockfileVersion":1,"dependencies":{"redis":{"version":"4"}}}',
                encoding="utf-8",
            )

            scan = scan_repository(root)

        self.assertEqual((), scan.manifests)
        self.assertTrue(
            any(
                item["code"] == "MANIFEST_PARSE_FAILED"
                and item.get("sourcePath") == "package-lock.json"
                for item in scan.diagnostics
            )
        )

    def test_spring_properties_emit_only_allowlisted_non_secret_config_evidence(self):
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "repositories"
            / "postgresql-config"
        )

        scan = scan_repository(fixture)
        graph = build_structural_ucg(scan, "example/postgresql")

        self.assertEqual(
            ["src/main/resources/application.properties"],
            [item.path for item in scan.configurations],
        )
        self.assertEqual(
            ["spring.datasource.driver-class-name=org.postgresql.Driver"],
            [
                f"{fact.key}={fact.value}"
                for item in scan.configurations
                for fact in item.facts
            ],
        )
        config_evidence = [
            item for item in graph["evidence"] if item["kind"] == "CONFIG"
        ]
        self.assertEqual(1, len(config_evidence))
        self.assertEqual(1, config_evidence[0]["startLine"])
        serialized = canonical_json_bytes(graph)
        self.assertNotIn(b"must-never-appear", serialized)
        self.assertNotIn(b"spring.datasource.password", serialized)
        self.assertEqual([], validate_document(graph))

    def test_ambiguous_spring_property_is_skipped_without_leaking_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "App.java").write_text("class App {}", encoding="utf-8")
            (root / "application.properties").write_text(
                "spring.datasource.driver-class-name=org.postgresql.Driver\n"
                "spring.datasource.driver-class-name=org.postgresql.Driver\n"
                "spring.datasource.password=secret-value\n",
                encoding="utf-8",
            )

            scan = scan_repository(root)

        self.assertEqual((), scan.configurations)
        self.assertTrue(
            any(item["code"] == "CONFIG_PARSE_FAILED" for item in scan.diagnostics)
        )
        self.assertNotIn("secret-value", repr(scan.diagnostics))

    def test_maven_parser_ignores_management_plugins_and_interpolation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "App.java").write_text("class App {}", encoding="utf-8")
            (root / "pom.xml").write_text(
                """<project>
  <dependencies>
    <dependency><groupId>${group}</groupId><artifactId>dynamic</artifactId></dependency>
  </dependencies>
  <dependencyManagement><dependencies>
    <dependency><groupId>managed</groupId><artifactId>only</artifactId></dependency>
  </dependencies></dependencyManagement>
  <build><plugins><plugin><dependencies>
    <dependency><groupId>plugin</groupId><artifactId>only</artifactId></dependency>
  </dependencies></plugin></plugins></build>
</project>""",
                encoding="utf-8",
            )

            scan = scan_repository(root)

        self.assertEqual((), scan.manifests[0].dependencies)

    def test_malformed_or_doctype_maven_manifest_is_rejected_safely(self):
        for content in ("<project>", "<!DOCTYPE project><project />"):
            with self.subTest(content=content):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    (root / "App.java").write_text("class App {}", encoding="utf-8")
                    (root / "pom.xml").write_text(content, encoding="utf-8")

                    scan = scan_repository(root)

                self.assertEqual((), scan.manifests)
                self.assertTrue(
                    any(
                        item["code"] == "MANIFEST_PARSE_FAILED"
                        for item in scan.diagnostics
                    )
                )

    def test_symlink_is_not_followed_when_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root.parent / f"{root.name}-outside.py"
            outside.write_text("secret = True", encoding="utf-8")
            link = root / "linked.py"
            try:
                link.symlink_to(outside)
            except OSError:
                outside.unlink(missing_ok=True)
                self.skipTest("symbolic links are unavailable")
            try:
                result = scan_repository(root)
            finally:
                outside.unlink(missing_ok=True)

        self.assertEqual((), result.files)
        self.assertTrue(
            any(item["code"] == "SYMLINK_SKIPPED" for item in result.diagnostics)
        )

    def test_invalid_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing"

            with self.assertRaisesRegex(ScannerError, "not accessible"):
                scan_repository(missing)


if __name__ == "__main__":
    unittest.main()
