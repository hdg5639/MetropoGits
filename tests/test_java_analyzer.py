import tempfile
import unittest
from pathlib import Path

from metropogits.analyzers.java import enrich_java_graph
from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.scanner import ScanLimits, build_structural_ucg, scan_repository
from scripts.canonical_json import canonical_json_bytes
from scripts.validate_ucg import validate_document


FIXTURES = Path(__file__).parent / "fixtures" / "repositories"


def analyze(root: Path) -> dict:
    limits = ScanLimits()
    scan = scan_repository(root, limits)
    graph = build_structural_ucg(scan, "fixture/java")
    return enrich_java_graph(root, scan, graph, limits)


def files_by_name(graph: dict) -> dict[str, dict]:
    return {
        Path(entity["path"]).name: entity
        for entity in graph["entities"]
        if entity["kind"] == "FILE"
    }


class JavaAnalyzerTests(unittest.TestCase):
    def test_cli_analysis_runs_java_adapter(self):
        graph = analyze_repository(
            FIXTURES / "spring-positive", repository_id="fixture/cli-java"
        )

        files = files_by_name(graph)
        self.assertEqual(
            "ENTRYPOINT", files["UserController.java"]["roles"][0]["value"]
        )
        self.assertTrue(any(edge["type"] == "IMPORTS" for edge in graph["edges"]))

    def test_spring_roles_use_verified_annotations_and_specific_precedence(self):
        graph = analyze(FIXTURES / "spring-positive")
        files = files_by_name(graph)

        expected = {
            "AccountRepository.java": "PERSISTENCE_ADAPTER",
            "ApplicationConfiguration.java": "CONFIGURATION",
            "AuditComponent.java": "GENERAL_COMPONENT",
            "UserController.java": "ENTRYPOINT",
            "UserRepository.java": "PERSISTENCE_ADAPTER",
            "UserService.java": "SERVICE",
        }
        self.assertEqual(
            expected,
            {name: entity["roles"][0]["value"] for name, entity in files.items()},
        )
        controller = files["UserController.java"]
        self.assertEqual(
            ["API"], [item["value"] for item in controller["capabilities"]]
        )
        self.assertEqual(
            ["SPRING_MVC"],
            [item["value"] for item in controller["technologies"]],
        )
        evidence = {item["evidenceId"]: item for item in graph["evidence"]}
        for name, role in expected.items():
            claim = files[name]["roles"][0]
            self.assertEqual("DIRECT", claim["confidence"])
            item = evidence[claim["evidenceIds"][0]]
            self.assertEqual(
                "ANNOTATION" if name != "AccountRepository.java" else "INHERITANCE",
                item["kind"],
            )
            self.assertEqual(files[name]["path"], item["sourcePath"])
            self.assertGreaterEqual(item["startLine"], 1)
            self.assertGreaterEqual(item["endLine"], item["startLine"])

    def test_negative_near_matches_do_not_create_spring_roles(self):
        graph = analyze(FIXTURES / "spring-negative")

        for entity in files_by_name(graph).values():
            self.assertEqual([], entity["roles"])
            self.assertFalse(
                any(
                    "POSTGRES" in claim["value"].upper()
                    for claim in entity.get("technologies", [])
                )
            )

    def test_catalog_rules_create_evidence_backed_technology_archetypes(self):
        graph = analyze(FIXTURES / "technology-positive")
        files = files_by_name(graph)
        expected = {
            "HttpGateway.java": (
                "SPRING_REST_CLIENT",
                "API",
                "HTTP_CLIENT",
                "PORT",
            ),
            "KafkaPublisher.java": (
                "APACHE_KAFKA",
                "STREAM",
                "MESSAGE_PRODUCER",
                "EXCHANGE",
            ),
            "MongoStore.java": (
                "MONGODB",
                "DOCUMENT_DB",
                "DOCUMENT_PERSISTENCE_ADAPTER",
                "DOCUMENT_DEPOT",
            ),
            "RabbitGateway.java": (
                "RABBITMQ",
                "QUEUE",
                "MESSAGE_ADAPTER",
                "EXCHANGE",
            ),
            "RedisStore.java": (
                "REDIS",
                "CACHE",
                "CACHE_ADAPTER",
                "CACHE_TOWER",
            ),
        }
        evidence = {item["evidenceId"]: item for item in graph["evidence"]}
        scene = generate_city(graph)
        archetypes = {
            Path(entity["path"]).name: building["archetype"]
            for entity in graph["entities"]
            if entity["kind"] == "FILE"
            for building in scene["buildings"]
            if building["entityId"] == entity["id"]
        }

        self.assertEqual("0.5.0", graph["generator"]["catalogVersion"])
        for name, (technology, capability, role, archetype) in expected.items():
            entity = files[name]
            self.assertEqual([technology], [item["value"] for item in entity["technologies"]])
            self.assertEqual([capability], [item["value"] for item in entity["capabilities"]])
            self.assertEqual([role], [item["value"] for item in entity["roles"]])
            self.assertEqual(archetype, archetypes[name])
            for field in ("technologies", "capabilities", "roles"):
                claim = entity[field][0]
                self.assertEqual("DIRECT", claim["confidence"])
                self.assertTrue(claim["evidenceIds"])
                self.assertEqual(
                    {"IMPORT", "MANIFEST"},
                    {evidence[item]["kind"] for item in claim["evidenceIds"]},
                )

    def test_catalog_near_match_imports_remain_unclassified(self):
        graph = analyze(FIXTURES / "technology-negative")

        for entity in files_by_name(graph).values():
            self.assertEqual([], entity["roles"])
            self.assertEqual([], entity.get("capabilities", []))
            self.assertEqual([], entity.get("technologies", []))

    def test_declared_technology_without_code_usage_remains_unclassified(self):
        graph = analyze(FIXTURES / "technology-declared-only")

        for entity in files_by_name(graph).values():
            self.assertEqual([], entity["roles"])
            self.assertEqual([], entity.get("capabilities", []))
            self.assertEqual([], entity.get("technologies", []))
        self.assertTrue(any(edge["type"] == "DEPENDS_ON" for edge in graph["edges"]))

    def test_postgresql_requires_manifest_inheritance_and_safe_config_evidence(self):
        graph = analyze(FIXTURES / "postgresql-config")
        repository = files_by_name(graph)["AccountRepository.java"]
        evidence = {item["evidenceId"]: item for item in graph["evidence"]}

        self.assertIn(
            "POSTGRESQL",
            [item["value"] for item in repository["technologies"]],
        )
        self.assertIn(
            "RELATIONAL_DB",
            [item["value"] for item in repository["capabilities"]],
        )
        postgresql = next(
            item
            for item in repository["technologies"]
            if item["value"] == "POSTGRESQL"
        )
        self.assertEqual("DIRECT", postgresql["confidence"])
        self.assertEqual(
            {"CONFIG", "INHERITANCE", "MANIFEST"},
            {evidence[item]["kind"] for item in postgresql["evidenceIds"]},
        )
        self.assertNotIn("must-never-appear", canonical_json_bytes(graph).decode())
        self.assertEqual([], validate_document(graph))

    def test_catalog_intersects_nearest_manifest_and_code_evidence(self):
        graph = analyze(FIXTURES / "spring-manifest-usage")
        service = files_by_name(graph)["CatalogService.java"]
        evidence = {item["evidenceId"]: item for item in graph["evidence"]}

        self.assertEqual(["SERVICE"], [item["value"] for item in service["roles"]])
        self.assertEqual(
            ["SPRING_FRAMEWORK"],
            [item["value"] for item in service["technologies"]],
        )
        for field in ("roles", "technologies"):
            claim = service[field][0]
            self.assertEqual(
                {"ANNOTATION", "IMPORT", "MANIFEST"},
                {evidence[item]["kind"] for item in claim["evidenceIds"]},
            )
        self.assertEqual([], validate_document(graph))

    def test_catalog_does_not_borrow_manifest_from_sibling_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "declared").mkdir()
            (root / "declared" / "pom.xml").write_text(
                """<project><dependencies><dependency>
<groupId>org.springframework</groupId><artifactId>spring-context</artifactId>
</dependency></dependencies></project>""",
                encoding="utf-8",
            )
            (root / "source").mkdir()
            (root / "source" / "SiblingService.java").write_text(
                "import org.springframework.stereotype.Service;\n"
                "@Service public class SiblingService {}\n",
                encoding="utf-8",
            )

            graph = analyze(root)

        service = files_by_name(graph)["SiblingService.java"]
        evidence = {item["evidenceId"]: item for item in graph["evidence"]}
        claim_evidence = {
            evidence[item]["kind"] for item in service["roles"][0]["evidenceIds"]
        }
        self.assertEqual({"ANNOTATION"}, claim_evidence)

    def test_local_imports_create_evidenced_file_edges_and_city_networks(self):
        graph = analyze(FIXTURES / "spring-positive")
        local_imports = [
            edge
            for edge in graph["edges"]
            if edge["type"] == "IMPORTS"
            and ":file:" in edge["from"]
            and ":file:" in edge["to"]
        ]

        self.assertEqual(2, len(local_imports))
        self.assertTrue(all(edge["confidence"] == "RESOLVED" for edge in local_imports))
        self.assertTrue(all(edge["evidenceIds"] for edge in local_imports))
        local_relationships = [
            edge
            for edge in graph["edges"]
            if edge["type"] in {"IMPORTS", "REFERENCES"}
            and ":file:" in edge["from"]
            and ":file:" in edge["to"]
        ]
        scene = generate_city(graph)
        self.assertEqual(2, len(scene["networks"]))
        self.assertEqual(
            sorted(edge["id"] for edge in local_relationships),
            sorted(
                edge_id
                for network in scene["networks"]
                for edge_id in network["edgeIds"]
            ),
        )

    def test_same_package_field_type_creates_resolved_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Target.java").write_text(
                "package demo;\npublic class Target {}\n", encoding="utf-8"
            )
            (root / "Consumer.java").write_text(
                "package demo;\n"
                "public class Consumer {\n"
                "  private final Target target;\n"
                "}\n",
                encoding="utf-8",
            )

            graph = analyze(root)

        files = {item["path"]: item["id"] for item in graph["entities"] if item["kind"] == "FILE"}
        references = [edge for edge in graph["edges"] if edge["type"] == "REFERENCES"]
        self.assertEqual(1, len(references))
        self.assertEqual(files["Consumer.java"], references[0]["from"])
        self.assertEqual(files["Target.java"], references[0]["to"])
        evidence = {item["evidenceId"]: item for item in graph["evidence"]}
        reference_evidence = evidence[references[0]["evidenceIds"][0]]
        self.assertEqual("AST", reference_evidence["kind"])
        self.assertEqual(3, reference_evidence["startLine"])
        self.assertEqual("RESOLVED", references[0]["confidence"])
        self.assertEqual([], validate_document(graph))

    def test_comments_strings_and_unused_imports_do_not_create_references(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Target.java").write_text(
                "package demo;\npublic class Target {}\n", encoding="utf-8"
            )
            (root / "Consumer.java").write_text(
                "package other;\n"
                "import demo.Target;\n"
                "public class Consumer {\n"
                "  // Target appears only in a comment\n"
                '  private final String label = "Target";\n'
                "}\n",
                encoding="utf-8",
            )

            graph = analyze(root)

        self.assertEqual(
            [], [edge for edge in graph["edges"] if edge["type"] == "REFERENCES"]
        )

    def test_ambiguous_wildcard_type_is_not_resolved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "first").mkdir()
            (root / "second").mkdir()
            (root / "first" / "Target.java").write_text(
                "package first;\npublic class Target {}\n", encoding="utf-8"
            )
            (root / "second" / "Target.java").write_text(
                "package second;\npublic class Target {}\n", encoding="utf-8"
            )
            (root / "Consumer.java").write_text(
                "package demo;\n"
                "import first.*;\n"
                "import second.*;\n"
                "public class Consumer { Target target; }\n",
                encoding="utf-8",
            )

            graph = analyze(root)

        self.assertEqual(
            [], [edge for edge in graph["edges"] if edge["type"] == "REFERENCES"]
        )

    def test_declarations_create_stable_symbol_entities(self):
        root = FIXTURES / "spring-positive"
        first = analyze(root)
        second = analyze(root)

        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        self.assertEqual([], validate_document(first))
        symbols = [entity for entity in first["entities"] if entity["kind"] == "SYMBOL"]
        declares = [edge for edge in first["edges"] if edge["type"] == "DECLARES"]
        self.assertEqual(6, len(symbols))
        self.assertEqual(6, len(declares))
        self.assertTrue(all(edge["evidenceIds"] for edge in declares))

    def test_mixed_repository_discloses_structural_only_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "App.java").write_text("class App {}", encoding="utf-8")
            (root / "worker.py").write_text("pass", encoding="utf-8")

            graph = analyze(root)

        coverage = [
            item
            for item in graph["diagnostics"]
            if item["code"] == "JAVA_ANALYZER_COVERAGE"
        ]
        self.assertEqual(1, len(coverage))
        self.assertIn("1 non-Java file(s)", coverage[0]["message"])

    def test_same_line_annotation_is_recognized(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "InlineService.java").write_text(
                "import org.springframework.stereotype.Service;\n"
                "@Service public class InlineService {}\n",
                encoding="utf-8",
            )

            graph = analyze(root)

        service = files_by_name(graph)["InlineService.java"]
        self.assertEqual("SERVICE", service["roles"][0]["value"])


if __name__ == "__main__":
    unittest.main()
