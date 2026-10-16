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
