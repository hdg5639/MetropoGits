import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from metropogits.cli import main


class WorldCityCommandTests(unittest.TestCase):
    def test_city_command_writes_a_static_procedural_city_without_running_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            repository = workspace / "repository"
            (repository / "src").mkdir(parents=True)
            marker = workspace / "executed.marker"
            for index in range(14):
                (repository / "src" / f"module{index}.py").write_text(
                    f"import module{(index + 1) % 14}\nfrom pathlib import Path\n"
                    f"Path({str(marker)!r}).touch()\n", encoding="utf-8")
            output = workspace / "city"
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = main(["city", "--repo", str(repository), "--out", str(output), "--seed", "test"])
            self.assertEqual(code, 0, stream.getvalue())
            for name in ("index.html", "showcase.svg", "world.json", "city.json"):
                self.assertTrue((output / name).is_file(), name)
            self.assertFalse(marker.exists())
            self.assertIn("Built procedural city", stream.getvalue())

    def test_city_refuses_a_nonempty_output_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            repository = workspace / "repository"
            repository.mkdir()
            (repository / "a.py").write_text("x = 1", encoding="utf-8")
            output = workspace / "city"
            output.mkdir()
            (output / "keep.txt").write_text("keep", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                code = main(["city", "--repo", str(repository), "--out", str(output)])
            self.assertNotEqual(code, 0)
            self.assertEqual((output / "keep.txt").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
