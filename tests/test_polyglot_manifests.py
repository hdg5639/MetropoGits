"""Read declared dependency identities only; no install, hooks or secret values."""

import tempfile
import unittest
from pathlib import Path

from metropogits.manifests import parse_manifest
from metropogits.scanner import scan_repository, build_structural_ucg
from scripts.canonical_json import canonical_json_bytes
from scripts.validate_ucg import validate_document


class PolyglotManifestTests(unittest.TestCase):
    def test_eight_manifest_shapes_and_normalized_names(self):
        cases = [
            (
                "pyproject",
                '[project]\ndependencies=["FastAPI>=0.1", "SQLAlchemy[asyncio]"]\n',
                "pypi",
                {"fastapi", "sqlalchemy"},
            ),
            (
                "requirements",
                "Django==5.0\n# redis\n-r other.txt\nhttpx>=0.1",
                "pypi",
                {"django", "httpx"},
            ),
            (
                "cargo",
                '[dependencies]\nserde="1"\nalias={package="tokio", version="1"}\n',
                "cargo",
                {"serde", "tokio"},
            ),
            (
                "go",
                "module example.org/app\nrequire (\n example.org/lib v1.0\n)\n",
                "go",
                {"example.org/lib"},
            ),
            (
                "composer",
                '{"require":{"php":"^8", "laravel/framework":"*"}}',
                "composer",
                {"laravel/framework"},
            ),
            (
                "nuget",
                '<Project><ItemGroup><PackageReference Include="Microsoft.EntityFrameworkCore" Version="1"/></ItemGroup></Project>',
                "nuget",
                {"Microsoft.EntityFrameworkCore"},
            ),
            (
                "gemfile",
                'source "https://example.org"\ngem "rails", "~>7"\n',
                "rubygems",
                {"rails"},
            ),
            (
                "pub",
                "dependencies:\n  flutter:\n    sdk: flutter\n  dio: ^5.0\n",
                "pub",
                {"flutter", "dio"},
            ),
        ]
        for kind, text, ecosystem, names in cases:
            with self.subTest(kind=kind):
                actual, packages, _ = parse_manifest(kind, text.encode())
                self.assertEqual(actual, ecosystem)
                self.assertEqual(set(packages), names)

    def test_scanner_integrates_modules_and_exact_dependencies_without_credentials(
        self,
    ):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "main.py").write_text("pass", encoding="utf8")
            (root / "pyproject.toml").write_text(
                '[project]\ndependencies=["fastapi @ https://user:secret@example.org/pkg.whl"]\n',
                encoding="utf8",
            )
            graph = build_structural_ucg(scan_repository(root), "fixture/manifest")
            self.assertEqual(validate_document(graph), [])
            self.assertTrue(
                any(e.get("path") == "pypi/fastapi" for e in graph["entities"])
            )
            self.assertNotIn(b"secret", canonical_json_bytes(graph))
            self.assertTrue(any(e["type"] == "DEPENDS_ON" for e in graph["edges"]))

    def test_malformed_toml_and_xml_entities_are_disclosed_not_executed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "main.cs").write_text("class Main {}", encoding="utf8")
            (root / "Cargo.toml").write_text("[broken", encoding="utf8")
            (root / "app.csproj").write_text(
                '<!DOCTYPE x [<!ENTITY x SYSTEM "file:///secret">]><Project>&x;</Project>',
                encoding="utf8",
            )
            scan = scan_repository(root)
            (root / "broken.csproj").write_text("<Project><ItemGroup>", encoding="utf8")
            scan = scan_repository(root)
            self.assertEqual(scan.manifests, ())
            self.assertEqual(
                sum(e["code"] == "MANIFEST_PARSE_FAILED" for e in scan.diagnostics), 3
            )

    def test_nested_cargo_and_poetry_dependencies_remain_static(self):
        self.assertEqual(
            set(
                parse_manifest(
                    "cargo",
                    b'[target."cfg(windows)".dependencies]\nwindows="1"\n[workspace.dependencies]\nserde="1"',
                )[1]
            ),
            {"windows", "serde"},
        )
        self.assertEqual(
            set(
                parse_manifest(
                    "pyproject",
                    b'[tool.poetry.dependencies]\npython="^3"\nredis="*"\n[tool.poetry.group.dev.dependencies]\npytest="*"',
                )[1]
            ),
            {"redis", "pytest"},
        )

    def test_multiline_ruby_strings_cannot_spoof_gem_declarations(self):
        with self.assertRaises(ValueError):
            parse_manifest("gemfile", b"x = \"\ngem 'fake'\n\"")


if __name__ == "__main__":
    unittest.main()
