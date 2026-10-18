import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.generated_outputs import declares_local_bin_output
from metropogits.scanner import scan_repository, ScanLimits, build_structural_ucg
from metropogits.layout import generate_city
from scripts.canonical_json import canonical_json_bytes


class GeneratedOutputsTests(unittest.TestCase):
    def test_exact_declaration_and_root_negation_order(self):
        for content in [b"bin/\n", b"/bin/  \r\n", b"bin/\n!**/src/main/**/bin/\n!**/src/test/**/bin/",
                        b"bin/\n!bin/\nbin/", b"bin/\n!bin/keep.py"]:
            self.assertTrue(declares_local_bin_output(content), content)
        for content in [b"# bin/", b" bin/", b"bin", b"**/bin/", b"bin/\n!bin/", b"bin/\n!/bin",
                        b"bin/\n!**/bin/", b"bin/\n!b*/", b"bin/\n!*/", b"bin/\n!b[ia]n/",
                        b"bin/\n!\\bin/", b"bin/\n!**/b?n/"]:
            self.assertFalse(declares_local_bin_output(content), content)
        with self.assertRaises(ValueError):
            declares_local_bin_output(b"bin/\n" + b"x" * 65536)

    def create_module(self, root, ignore=b"bin/\n!**/src/main/**/bin/\n"):
        for path, content in {
            "app/build.gradle": b"dependencies {}", "app/.gitignore": ignore,
            "app/src/main/resources/schema.sql": b"select 1;",
            "app/src/main/bin/tool.py": b"pass",
            "app/bin/main/schema.sql": b"select 1;",
            "bin/tool.py": b"pass", "other/bin/main/script.py": b"pass",
        }.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    def test_scoped_output_exclusion_preserves_source_bins_and_other_modules(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.create_module(root)
            with patch("subprocess.run", side_effect=AssertionError("No repo execution")):
                scan = scan_repository(root)
            self.assertEqual(["app/src/main/bin/tool.py", "app/src/main/resources/schema.sql",
                              "bin/tool.py", "other/bin/main/script.py"], [f.path for f in scan.files])
            exclusions = [d for d in scan.diagnostics if d["code"] == "GENERATED_OUTPUT_EXCLUDED"]
            self.assertEqual(["app/bin"], [d["sourcePath"] for d in exclusions])
            self.assertEqual(canonical_json_bytes(build_structural_ucg(scan, "fixture")),
                             canonical_json_bytes(build_structural_ucg(scan_repository(root), "fixture")))

    def test_missing_manifest_negation_or_invalid_declaration_preserves_files(self):
        for ignore in [b"bin/\n!bin/", b"bin/\n\xff", b"bin/\n\x00", b"# no declaration"]:
            with self.subTest(ignore=ignore), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.create_module(root, ignore)
                self.assertIn("app/bin/main/schema.sql", [f.path for f in scan_repository(root).files])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.create_module(root)
            result = scan_repository(root, excluded_paths=[root / "app/build.gradle"])
            self.assertIn("app/bin/main/schema.sql", [f.path for f in result.files])
            result = scan_repository(root, excluded_paths=[root / "app/.gitignore"])
            self.assertIn("app/bin/main/schema.sql", [f.path for f in result.files])

    def test_declaration_limits_are_bounded_and_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.create_module(root, b"bin/\n" + b"#" * 65536)
            result = scan_repository(root)
            self.assertIn("app/bin/main/schema.sql", [f.path for f in result.files])
            self.assertTrue(any(d["code"] == "OUTPUT_DECLARATION_UNREADABLE" for d in result.diagnostics))
            self.create_module(root)
            result = scan_repository(root, ScanLimits(max_total_bytes=5))
            self.assertTrue(any(d["code"] == "TOTAL_SIZE_LIMIT_REACHED" for d in result.diagnostics))

    def test_linked_metadata_cannot_authorize_output_exclusion(self):
        for name in [".gitignore", "build.gradle"]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.create_module(root)
                metadata = root / "app" / name
                metadata.write_bytes(metadata.read_bytes() + b"\n#" + b"x" * 257)
                unique_size = metadata.stat().st_size
                # Exercise the shared reparse guard without requiring Windows
                # symlink privileges. Both the manifest and declaration count.
                with patch("metropogits.scanner._is_reparse_point", side_effect=lambda value: value.st_size == unique_size):
                    result = scan_repository(root)
                self.assertIn("app/bin/main/schema.sql", [f.path for f in result.files])
                self.assertTrue(any(d["code"] == "SYMLINK_SKIPPED" for d in result.diagnostics))

    def test_generated_copy_addition_does_not_change_entities_or_existing_sites(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src/App.java").write_text("class App {}", encoding="utf-8")
            (root / "build.gradle").write_text("dependencies {}", encoding="utf-8")
            (root / ".gitignore").write_text("bin/\n", encoding="utf-8")
            before = build_structural_ucg(scan_repository(root), "fixture")
            city = generate_city(before)
            (root / "bin/main").mkdir(parents=True)
            (root / "bin/main/schema.sql").write_text("select 1;", encoding="utf-8")
            after = build_structural_ucg(scan_repository(root), "fixture")
            next_city = generate_city(after, previous_scene=city)
            for field in ["entities", "edges", "evidence"]:
                self.assertEqual(before[field], after[field])
            self.assertEqual(city["buildings"], next_city["buildings"])
            self.assertEqual(city["districts"], next_city["districts"])
