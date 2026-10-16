import json
import unittest
from pathlib import Path

from scripts.stable_ids import (
    StableIdError,
    make_edge_id,
    make_entity_id,
    normalize_relative_path,
    normalize_repository_id,
    repository_id_from_root,
)


class StableIdTests(unittest.TestCase):
    def test_repository_namespace_is_normalized(self):
        self.assertEqual("openai/metropogits", normalize_repository_id("openai\\metropogits"))

    def test_repository_namespace_rejects_private_or_unsafe_paths(self):
        for namespace in ("C:\\Users\\person\\repo", "/srv/repo", "../repo", "team/도시"):
            with self.subTest(namespace=namespace):
                with self.assertRaises(StableIdError):
                    normalize_repository_id(namespace)

    def test_local_repository_id_is_stable_and_does_not_expose_path(self):
        root = Path("fixtures/repository").resolve()

        first = repository_id_from_root(root)
        second = repository_id_from_root(root)

        self.assertEqual(first, second)
        self.assertRegex(first, r"^local-sha256-[0-9a-f]{16}$")
        self.assertNotIn("fixtures", first)

    def test_relative_path_normalizes_separators_and_unicode(self):
        decomposed = "src/cafe\u0301/File.java"

        self.assertEqual("src/café/File.java", normalize_relative_path(decomposed))
        self.assertEqual("src/App.java", normalize_relative_path("./src//App.java"))

    def test_relative_path_rejects_absolute_and_traversal_inputs(self):
        for path in (
            "C:\\repo\\App.java",
            "C:repo\\App.java",
            "/repo/App.java",
            "src/../App.java",
        ):
            with self.subTest(path=path):
                with self.assertRaises(StableIdError):
                    normalize_relative_path(path)

    def test_file_entity_id_percent_encodes_each_path_segment(self):
        result = make_entity_id("demo", "FILE", "src/한 글#1.py")

        self.assertEqual(
            "demo:file:src/%ED%95%9C%20%EA%B8%80%231.py",
            result,
        )

    def test_symbol_entity_id_requires_and_encodes_qualified_symbol(self):
        result = make_entity_id(
            "demo", "SYMBOL", "src/App.java", "example.App#run()"
        )

        self.assertEqual(
            "demo:symbol:src/App.java#example.App%23run%28%29",
            result,
        )
        with self.assertRaisesRegex(StableIdError, "requires a qualified symbol"):
            make_entity_id("demo", "SYMBOL", "src/App.java")

    def test_edge_id_is_stable_and_directional(self):
        source = "demo:file:src/App.java"
        target = "demo:file:src/Store.java"

        first = make_edge_id(source, "REFERENCES", target)
        second = make_edge_id(source, "REFERENCES", target)
        reversed_edge = make_edge_id(target, "REFERENCES", source)

        self.assertEqual(first, second)
        self.assertEqual(
            "edge:sha256:637851bc76e08660062a25bceced0a3c9a9f734c3bced2a167a54487616a8fdb",
            first,
        )
        self.assertNotEqual(first, reversed_edge)

    def test_edge_discriminator_changes_identity(self):
        source = "demo:file:src/App.java"
        target = "demo:external-system:orders"

        first = make_edge_id(source, "HTTP_CALL", target, "GET /orders")
        second = make_edge_id(source, "HTTP_CALL", target, "POST /orders")

        self.assertNotEqual(first, second)

    def test_unknown_kinds_are_rejected(self):
        with self.assertRaisesRegex(StableIdError, "unsupported entity kind"):
            make_entity_id("demo", "BUILDING", "src/App.java")
        with self.assertRaisesRegex(StableIdError, "unsupported edge kind"):
            make_edge_id("source", "GUESSES", "target")

    def test_ucg_fixture_uses_stable_entity_and_edge_ids(self):
        fixture = Path("tests/fixtures/ucg/valid/spring-minimal.json")
        ucg = json.loads(fixture.read_text(encoding="utf-8"))

        for entity in ucg["entities"]:
            self.assertEqual(
                entity["id"],
                make_entity_id(ucg["repository"]["id"], entity["kind"], entity["path"]),
            )
        for edge in ucg["edges"]:
            self.assertEqual(
                edge["id"],
                make_edge_id(edge["from"], edge["type"], edge["to"]),
            )


if __name__ == "__main__":
    unittest.main()
