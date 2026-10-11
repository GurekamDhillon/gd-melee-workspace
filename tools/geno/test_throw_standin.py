"""Synthetic tests for authored throw stand-in propagation; no assets are read."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.geno import throw_standin
from tools.geno.artist import assemble, gameplay_cache


class ThrowStandInTests(unittest.TestCase):
    def test_known_tokens_aliases_and_rejected_values(self):
        self.assertEqual(len(throw_standin.CHOICES), 26)
        for name in throw_standin.CHOICES:
            self.assertEqual(throw_standin.validate(name), name)
        self.assertEqual(throw_standin.validate("falcon"), "falcon")
        self.assertEqual(throw_standin.validate("FOX"), "FOX")
        for value in (None, True, 2, {}, "nana", "unknown", " fox"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                throw_standin.validate(value)

    def test_copy_is_optional_and_rejects_before_mutation(self):
        fighter = {"define": {"base": "none"}, "unrelated": [1]}
        throw_standin.apply(fighter, {})
        self.assertNotIn("thrown_as", fighter)
        throw_standin.apply(fighter, {"thrown_as": "samus"})
        self.assertEqual(fighter["thrown_as"], "samus")
        before = dict(fighter)
        with self.assertRaises(ValueError):
            throw_standin.apply(fighter, {"thrown_as": "nana"})
        self.assertEqual(fighter, before)
        with self.assertRaises(ValueError):
            throw_standin.apply({"define": {"base": "mario"}}, {"thrown_as": "fox"})

    def test_gameplay_cache_does_not_require_art_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "fighter.json"
            config.write_text(json.dumps({"key": "synthetic", "art": {}}))
            before = gameplay_cache.signature(config)
            config.write_text(json.dumps({"key": "synthetic", "art": {}, "thrown_as": "fox"}))
            self.assertEqual(gameplay_cache.signature(config), before)

    def test_artist_assembly_persists_setting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            striker = root / "pc/geno/mods/vanilla-striker"
            (striker / "moves").mkdir(parents=True)
            (striker / "geno.json").write_text(json.dumps({"fighters": [{"states": [], "specials": {}, "subactions": []}]}))
            build = root / "build"
            build.mkdir()
            (build / "plan.json").write_text(json.dumps({"joints": [], "roles": {}}))
            defaults = root / "data"
            defaults.mkdir()
            (defaults / "default_attributes.json").write_text(json.dumps({"attributes": {}, "ai": {}, "kirby_copy": {}, "jumps": {}, "special_attributes": {}}))
            fighter = SimpleNamespace(cfg={"thrown_as": "falco"}, key="synthetic", name="Synthetic", token="Synth", costumes=[])
            with patch.object(assemble.spec, "game_dir", return_value=str(root)), \
                 patch.object(assemble.spec, "DATA", str(defaults)), \
                 patch.object(assemble.spec, "workspace_root", return_value=str(root)), \
                 patch.object(assemble, "joint_map", return_value=({}, [])):
                assemble.assemble(fighter, str(build), str(root / "package"), 1, {})
            output = json.loads((root / "package/geno.json").read_text())
            self.assertGreaterEqual(output["geno"], 10)
            self.assertEqual(output["fighters"][0]["thrown_as"], "falco")

    def test_invalid_artist_setting_preserves_existing_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "package"
            package.mkdir()
            existing = package / "authored.json"
            existing.write_text("preserve this package")
            fighter = SimpleNamespace(cfg={"thrown_as": "nana"})
            with self.assertRaisesRegex(assemble.ArtistError, "thrown_as"):
                assemble.assemble(fighter, str(Path(tmp) / "absent-build"), str(package), 1, {})
            self.assertEqual(existing.read_text(), "preserve this package")

    def test_goku_stage_b_propagates_before_asset_work(self):
        path = Path(__file__).resolve().parents[2] / "ports/goku-xv2/tools/build.py"
        spec = importlib.util.spec_from_file_location("synthetic_goku_build", path)
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "gameplay.json"
            config.write_bytes(b'\xef\xbb\xbf{"thrown_as":"samus"}')
            self.assertEqual(build.load(config)["thrown_as"], "samus")
        cfg = {"thrown_as": "samus", "geometry_reference_height": 12,
               "source_ir": "synthetic.json", "host_ir": "synthetic-host.json", "states": []}
        fighter = {"define": {"base": "none"}}
        plan = {"joint_count": 1, "row_clips": [], "ftdata": {"x44_ecb": [{"role": "TopN"}]}}
        class Boundary(Exception):
            pass
        real_apply = throw_standin.apply
        def stop_after_override(target, authored):
            real_apply(target, authored)
            raise Boundary()
        with patch.object(build, "generated", side_effect=lambda value: Path(value)), \
             patch.object(build, "load", side_effect=[cfg, {"geometry": {"height": 12}}, {}, {}, plan, {"fighters": [fighter]}]), \
             patch.object(build.throw_standin, "apply", side_effect=stop_after_override):
            with self.assertRaises(Boundary):
                build.apply(Path("synthetic-package"), Path("synthetic-art"))
        self.assertEqual(fighter["thrown_as"], "samus")


if __name__ == "__main__":
    unittest.main()
