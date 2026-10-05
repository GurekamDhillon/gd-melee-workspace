"""Disc-free tests for complete native definitions, not executable acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.geno import check, script


class DefineAuthorTests(unittest.TestCase):
    def test_new_is_definition_not_overlay_and_checks(self):
        from tools.geno.new import create
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hero"
            create(root, "vanilla-hero", "Vanilla Hero", "mario")
            data = check.load_json(root / "geno.json")
            self.assertEqual(data["geno"], 6)
            f = data["fighters"][0]
            self.assertNotIn("attach", f)
            self.assertEqual(f["define"]["base"], "mario")
            self.assertEqual(check.validate(data, root), [])
            self.assertTrue(f["attributes"])
            self.assertTrue(f["subactions"])
            self.assertFalse(any(p.suffix.lower() in (".dat", ".usd", ".ssm") for p in root.rglob("*")))
            words = script.assemble((root / "moves/hero-jab.genoasm").read_text())
            self.assertTrue(words)
            from tools.geno.define import export_package
            out = Path(tmp) / "export"
            export_package(root, out)
            self.assertEqual(check.validate(check.load_json(out / "geno.json"), out), [])
            self.assertEqual(json.loads((out / "manifest.runtime.json").read_text())["backend"], "geno.define.v1")

    def test_definition_rejects_unsupported_contracts(self):
        from tools.geno.new import create
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hero"
            create(root, "hero", "Hero", "mario")
            data = check.load_json(root / "geno.json")
            for field, value in (("base", "kirby"), ("common", "melee.common.v2"), ("resources", "private/archive.dat")):
                bad = copy.deepcopy(data)
                bad["fighters"][0]["define"][field] = value
                self.assertTrue(check.validate(bad, root), field)
            bad = copy.deepcopy(data); bad["fighters"][0]["attach"] = "mario"
            self.assertTrue(check.validate(bad, root))
            bad = copy.deepcopy(data); bad["geno"] = 5
            self.assertTrue(check.validate(bad, root))
            with self.assertRaises(ValueError):
                create(Path(tmp) / "unsupported", "hero", "Hero", "kirby")
            with self.assertRaises(ValueError):
                create(root, "hero", "Hero", "mario")

    def test_export_refuses_unlisted_disc_payload(self):
        from tools.geno.new import create
        from tools.geno.define import export_package
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hero"
            create(root, "hero", "Hero", "mario")
            (root / "MxDt.dat").write_bytes(b"synthetic")
            with self.assertRaises(ValueError):
                export_package(root, Path(tmp) / "export")

    def test_native_script_and_state_row_bounds(self):
        from tools.geno.new import create
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hero"
            create(root, "hero", "Hero", "mario")
            data = check.load_json(root / "geno.json")
            for index in (302, 303, 304, 1023):
                bad = copy.deepcopy(data)
                bad["fighters"][0]["subactions"][0]["index"] = index
                self.assertEqual(bool(check.validate(bad, root)), index >= 303)
                bad = copy.deepcopy(data)
                bad["fighters"][0]["common_states"] = [{"motion": 44, "subaction": index}]
                self.assertEqual(bool(check.validate(bad, root)), index >= 303)


class MoveSetAuthorTests(unittest.TestCase):
    """Slice 2: geno 7, the checks a move-set author needs, `moves` sugar, the effective-graph report."""

    STRIKER = Path(__file__).resolve().parents[2] / "melee/pc/geno/mods/vanilla-striker"
    HERO = Path(__file__).resolve().parents[2] / "melee/pc/geno/mods/vanilla-hero"

    def make(self, tmp, template="striker-skeleton"):
        from tools.geno.new import create
        root = Path(tmp) / "mf"
        create(root, "mf", "My Fighter", "mario", template)
        return root, check.load_json(root / "geno.json")

    def test_v6_refuses_v7_keys_and_attributes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, data = self.make(tmp)
            self.assertEqual(check.validate(data, root), [])
            bad = copy.deepcopy(data); bad["geno"] = 6
            messages = [e["message"] for e in check.validate(bad, root)]
            self.assertTrue(any("needs geno: 7" in m for m in messages), messages)   # landingairn_lag is past the first 40
            bad = copy.deepcopy(data); bad["fighters"][0]["special_attributes"] = [{"index": 1, "float": 1.0}]
            self.assertEqual(check.validate(bad, root), [])
            bad["geno"] = 6; bad["fighters"][0]["attributes"] = {"walk_max_vel": 1.5}
            self.assertTrue(any("needs geno: 7" in e["message"] for e in check.validate(bad, root)))
            bad = copy.deepcopy(data); bad["fighters"][0]["articles"] = []
            self.assertTrue(check.validate(bad, root))   # articles stay refused until slice 3

    def test_unreachable_state_and_iasa_callback_and_unbound_special(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, data = self.make(tmp)
            (root / "moves/state.words").write_text("0x5C000000\n")           # IASA, then End
            f = data["fighters"][0]
            f["states"] = [{"name": "Lonely", "behavior": "geno.ground", "subaction": 295}]
            f["subactions"].append({"index": 295, "file": "moves/state.words"})
            messages = [e["message"] for e in check.validate(data, root)]
            self.assertTrue(any("unreachable" in m for m in messages), messages)
            self.assertTrue(any("IASA" in m and "iasa callback is none" in m for m in messages), messages)
            f["states"][0]["iasa"] = "interrupt"
            f["specials"] = {"n": "geno:Lonely"}
            self.assertEqual(check.validate(data, root), [])
            unbound = {w["path"].rsplit(".", 1)[1] for w in check.WARNINGS}
            self.assertEqual(unbound, {"s", "hi", "lw", "air_s", "air_hi", "air_lw"})   # air_n follows n

    def test_moves_sugar_expands_to_engine_keys(self):
        from tools.geno.define import expand_moves, export_package
        with tempfile.TemporaryDirectory() as tmp:
            root, data = self.make(tmp)
            f = data["fighters"][0]
            f["subactions"] = []
            f["moves"] = {"ftilt": {"motion": 53, "words": "moves/ftilt.words", "tag": "tilt"}}
            self.assertEqual(check.validate(data, root), [])
            out = expand_moves(data)["fighters"][0]
            self.assertNotIn("moves", out)
            self.assertEqual(out["subactions"], [{"index": 55, "file": "moves/ftilt.words", "move_tag": "tilt"}])
            self.assertEqual(out["common_states"], [{"motion": 53, "move_tag": "tilt"}])
            (root / "geno.json").write_text(json.dumps(data))
            export_package(root, Path(tmp) / "export")
            exported = json.loads((Path(tmp) / "export/geno.json").read_text())
            self.assertNotIn("moves", exported["fighters"][0])
            self.assertEqual(check.validate(exported, Path(tmp) / "export"), [])

    def test_report_golden_hero_and_striker(self):
        from tools.geno import report
        hero, _b, _f = report.build(self.HERO)
        self.assertEqual(hero["counts"], {"own": 1, "inherited": 350, "donor-special": 0})
        self.assertEqual(hero["attributes"], ["walk_max_vel"])
        self.assertEqual(set(hero["specials"].values()), {"DONOR"})
        self.assertFalse(hero["donor_free"])
        row = next(r for r in hero["rows"] if r["motion"] == 44)
        self.assertTrue(row["kind"].startswith("own (script overlay on row 46"))
        striker, base, fighter = report.build(self.STRIKER)
        self.assertTrue(striker["donor_free"], striker["attack_rows_missing"])
        self.assertEqual(striker["attack_rows_own"], striker["attack_rows_total"])
        self.assertNotIn("DONOR", striker["specials"].values())
        self.assertEqual(striker["counts"]["donor-special"], 8)
        frames = report.frame_table(base, fighter)
        fair = next(r for r in frames if r["index"] == 69)
        self.assertEqual((fair["iasa"], fair["hitboxes"][0]["start"], fair["hitboxes"][0]["damage"]), (52, 19, 10))
        self.assertIn("donor-free", report.text(striker))

    def test_striker_package_checks_clean_and_has_text_files_only(self):
        self.assertEqual(check.validate(check.load_json(self.STRIKER / "geno.json"), self.STRIKER), [])
        allowed = {".json", ".words", ".genoasm", ".md", ".gitkeep", ".png"}
        for p in self.STRIKER.rglob("*"):
            if p.is_file():
                self.assertIn(p.suffix.lower() or p.name, allowed, p)


class ArticleDefineTests(unittest.TestCase):
    """Slice 3: geno 8, a define with its own article, effect and named sounds (the resolver)."""

    CASTER = Path(__file__).resolve().parents[2] / "melee/pc/geno/mods/vanilla-caster"

    def test_caster_checks_clean_and_has_text_files_only(self):
        self.assertEqual(check.validate(check.load_json(self.CASTER / "geno.json"), self.CASTER), [])
        for p in self.CASTER.rglob("*"):
            if p.is_file():
                self.assertIn(p.suffix.lower() or p.name, {".json", ".words", ".genoasm", ".md"}, p)

    def test_articles_and_sounds_need_geno_8_and_names_must_resolve(self):
        data = check.load_json(self.CASTER / "geno.json")
        bad = copy.deepcopy(data); bad["geno"] = 7
        messages = [e["message"] for e in check.validate(bad, self.CASTER)]
        self.assertTrue(any("needs geno: 8" in m for m in messages), messages)
        bad = copy.deepcopy(data); bad["fighters"][0]["articles"][0]["spawn_sound"] = "Nope"
        messages = [e["message"] for e in check.validate(bad, self.CASTER)]
        self.assertTrue(any("not a name in sounds" in m for m in messages), messages)   # no donor fallback
        bad = copy.deepcopy(data); bad["fighters"][0]["sounds"].append(dict(bad["fighters"][0]["sounds"][0]))
        self.assertTrue(any("duplicate sound name" in e["message"] for e in check.validate(bad, self.CASTER)))
        bad = copy.deepcopy(data); bad["fighters"][0]["sounds"][0]["retail_sfx"] = 0
        self.assertTrue(check.validate(bad, self.CASTER))   # schema: engine sound id 1..999999


if __name__ == "__main__":
    unittest.main()
