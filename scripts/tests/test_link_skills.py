"""Offline checks for link_skills.py using temporary target directories."""
import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "link_skills.py"
spec = importlib.util.spec_from_file_location("link_skills", SCRIPT)
linker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linker)

NAME = "spec-mode"


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.target = base / "target"
        self.legacy = base / "legacy"
        self.backup = base / "backup"
        self.target.mkdir()
        self.legacy.mkdir()
        self.source = linker.SKILLS_DIR / NAME

    def run_linker(self, apply=False, force=False):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = linker.run([self.target], [self.legacy], {NAME}, apply, force, self.backup)
        return code, out.getvalue()

    def copy_source(self, dest):
        shutil.copytree(self.source, dest)

    def test_check_is_read_only(self):
        code, out = self.run_linker()
        self.assertEqual(code, 1)
        self.assertIn("missing", out)
        self.assertFalse((self.target / NAME).exists())

    def test_apply_links_missing(self):
        code, _ = self.run_linker(apply=True)
        self.assertEqual(code, 0)
        self.assertEqual((self.target / NAME).resolve(), self.source.resolve())
        self.assertEqual(self.run_linker()[0], 0)

    def test_identical_copy_is_backed_up_then_linked(self):
        self.copy_source(self.target / NAME)
        (self.target / NAME / ".DS_Store").write_text("ignored")
        self.run_linker(apply=True)
        self.assertTrue((self.target / NAME).is_symlink())
        self.assertTrue(any(self.backup.rglob("SKILL.md")))

    def test_differing_copy_requires_force(self):
        self.copy_source(self.target / NAME)
        (self.target / NAME / "SKILL.md").write_text("local edit")
        _, out = self.run_linker(apply=True)
        self.assertIn("skipped", out)
        self.assertFalse((self.target / NAME).is_symlink())
        self.run_linker(apply=True, force=True)
        self.assertTrue((self.target / NAME).is_symlink())
        backups = list(self.backup.rglob("SKILL.md"))
        self.assertEqual(backups[0].read_text(), "local edit")

    def test_legacy_copy_is_retired_and_local_only_reported(self):
        self.copy_source(self.legacy / NAME)
        other = self.target / "third-party"
        other.mkdir()
        (other / "SKILL.md").write_text("---\nname: third-party\n---\n")
        _, out = self.run_linker(apply=True)
        self.assertFalse((self.legacy / NAME).exists())
        self.assertIn("local-only    third-party", out)
        self.assertTrue(other.is_dir() and not other.is_symlink())


if __name__ == "__main__":
    unittest.main()
