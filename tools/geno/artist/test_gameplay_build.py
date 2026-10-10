"""Stage B transaction tests use synthetic authored files and mock tool boundaries."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.geno.artist import gameplay_cache, pipeline


class GameplayBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "fighter.json"
        self.config.write_text('// Supported author note\n' + json.dumps({
            "schema": "geno-artist/1", "key": "2nd-fighter",
            "art": {"glb": "authored.glb"}, "attributes": {"weight": 110}}), encoding="utf-8")
        (self.root / "authored.glb").write_text("authored fixture; never imported")
        self.out = self.root / "package"
        self.bd = self.out / "build"
        self.bd.mkdir(parents=True)
        for name in ("plan.json", "GnSecondAJ.dat", "GnSecond_red.dat"):
            (self.bd / name).write_text("{}" if name.endswith(".json") else "authored cached fixture")
        gameplay_cache.write(self.config, self.bd, token="Second",
                             costumes=[{"name": "red", "label": "Red", "team": "red"}],
                             height=12, ref_speeds={"Run": 1.5})
        self.installed = self.out / "mods/2nd-fighter"
        self.installed.mkdir(parents=True)
        (self.installed / "old.txt").write_text("previous installed package")
        self.enabled = self.out / "mods/enabled.txt"
        self.enabled.write_text("geno-lab\n2nd-fighter\n")
        self.lab = self.out / "mods/geno-lab"
        self.lab.mkdir()
        (self.lab / "authored.txt").write_text("preserve LAB")

    def assemble(self, fighter, build_dir, mod_dir, scale, speeds, log):
        self.assertEqual(fighter.key, "2nd-fighter")
        self.assertEqual(fighter.cfg["attributes"]["weight"], 110)
        self.assertEqual(fighter.token, "Second")
        self.assertEqual(speeds, {"Run": 1.5})
        self.assertEqual(Path(build_dir), self.bd)
        staged = Path(mod_dir)
        self.assertNotEqual(staged, self.installed)
        staged.mkdir()
        (staged / "geno.json").write_text(json.dumps({"key": fighter.key, "weight": 110}))
        (staged / "mod.json").write_text(json.dumps({"id": fighter.key}))
        return 1, []

    def test_valid_commented_digit_key_installs_only_after_check_without_art_tools(self):
        result = SimpleNamespace(returncode=0, stdout="checked", stderr="")
        with patch.object(pipeline.A, "assemble", side_effect=self.assemble), \
             patch.object(pipeline.subprocess, "run", return_value=result) as check, \
             patch.object(pipeline, "export_from_blend", side_effect=AssertionError("unexpected export")), \
             patch.object(pipeline.convert, "build_models", side_effect=AssertionError("unexpected models")):
            code, fighter = pipeline.build_gameplay(str(self.config), str(self.out), log=lambda _: None)
        self.assertEqual(code, 0)
        self.assertEqual(fighter.key, "2nd-fighter")
        self.assertFalse((self.installed / "old.txt").exists())
        self.assertEqual(json.loads((self.installed / "geno.json").read_text())["weight"], 110)
        self.assertEqual(self.enabled.read_text(), "geno-lab\n2nd-fighter\n")
        self.assertEqual((self.lab / "authored.txt").read_text(), "preserve LAB")
        self.assertEqual(check.call_args.args[0][1:3], ["-m", "tools.geno.check"])

    def test_failed_check_preserves_the_installed_package(self):
        result = SimpleNamespace(returncode=7, stdout="", stderr="synthetic checker failure")
        with patch.object(pipeline.A, "assemble", side_effect=self.assemble), \
             patch.object(pipeline.subprocess, "run", return_value=result):
            code, fighter = pipeline.build_gameplay(str(self.config), str(self.out), log=lambda _: None)
        self.assertEqual(code, 7)
        self.assertIsNone(fighter)
        self.assertEqual((self.installed / "old.txt").read_text(), "previous installed package")
        self.assertFalse((self.installed / "geno.json").exists())

    def test_missing_stage_a_contract_refuses_before_assembly(self):
        (self.bd / gameplay_cache.NAME).unlink()
        with patch.object(pipeline.A, "assemble") as assemble:
            with self.assertRaisesRegex(pipeline.ArtistError, "full build"):
                pipeline.build_gameplay(str(self.config), str(self.out), log=lambda _: None)
        assemble.assert_not_called()
        self.assertTrue((self.installed / "old.txt").exists())


if __name__ == "__main__":
    unittest.main()
