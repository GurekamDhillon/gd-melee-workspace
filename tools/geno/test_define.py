"""Disc-free tests for complete native definitions, not executable acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from tools.test_support import GAME, require_game

require_game('pc/geno/geno.h')
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

    STRIKER = GAME / "pc/geno/mods/vanilla-striker"
    HERO = GAME / "pc/geno/mods/vanilla-hero"

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
        require_game("pc/geno/mods/vanilla-striker/geno.json")
        require_game("pc/geno/mods/vanilla-hero/geno.json")
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
        require_game("pc/geno/mods/vanilla-striker/geno.json")
        self.assertEqual(check.validate(check.load_json(self.STRIKER / "geno.json"), self.STRIKER), [])
        allowed = {".json", ".words", ".genoasm", ".md", ".gitkeep", ".png"}
        for p in self.STRIKER.rglob("*"):
            if p.is_file():
                self.assertIn(p.suffix.lower() or p.name, allowed, p)


class ArticleDefineTests(unittest.TestCase):
    """Slice 3: geno 8, a define with its own article, effect and named sounds (the resolver)."""

    CASTER = GAME / "pc/geno/mods/vanilla-caster"

    def test_caster_checks_clean_and_has_text_files_only(self):
        require_game("pc/geno/mods/vanilla-caster/geno.json")
        self.assertEqual(check.validate(check.load_json(self.CASTER / "geno.json"), self.CASTER), [])
        for p in self.CASTER.rglob("*"):
            if p.is_file():
                self.assertIn(p.suffix.lower() or p.name, {".json", ".words", ".genoasm", ".md"}, p)

    def test_articles_and_sounds_need_geno_8_and_names_must_resolve(self):
        require_game("pc/geno/mods/vanilla-caster/geno.json")
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

    # ---- slice 6: costumes as declared colour sets, and a define's own menu and HUD art ----------------------------------------------
    COURIER = GAME / "pc/geno/mods/vanilla-courier"

    @staticmethod
    def gxtex(fmt=5, w=4, h=4):
        """a .gxtex container: 64-byte big-endian header (magic, version, format, w, h, tlut format, tlut entries, image size, tlut size,
        image offset, tlut offset), then a 32-byte image"""
        import struct
        return b"GXTX" + struct.pack(">I", 1) + struct.pack(">9I", fmt, w, h, 0xFFFFFFFF, 0, 32, 0, 64, 0) + bytes(64 - 44) + bytes(32)

    def test_courier_declares_colours_and_art_and_checks_clean(self):
        require_game("pc/geno/mods/vanilla-courier/geno.json")
        data = check.load_json(self.COURIER / "geno.json")
        f = data["fighters"][0]
        self.assertEqual([c.get("team") for c in f["fighter"]["costumes"]], [None, "red", "blue", "green"])
        self.assertTrue(all(c["name"] for c in f["fighter"]["costumes"]))
        self.assertEqual(set(f["presentation"]), {"icon", "portrait", "stock", "emblem"})
        self.assertEqual(f["ai"], {"like": "mario"})
        self.assertEqual(f["kirby_copy"], "none")
        self.assertEqual(check.validate(data, self.COURIER), [])

    def test_ai_kirby_copy_audio_rules(self):
        require_game("pc/geno/mods/vanilla-courier/geno.json")
        data = check.load_json(self.COURIER / "geno.json")
        def messages(mutate, geno=10):
            bad = copy.deepcopy(data); bad["geno"] = geno; mutate(bad["fighters"][0])
            return [e["message"] for e in check.validate(bad, self.COURIER)]
        self.assertTrue(any("needs geno: 10" in m for m in messages(lambda f: None, 9)), "ai/kirby_copy at 9")
        for like in ("nobody", "nana", 3):
            self.assertTrue(messages(lambda f, like=like: f.__setitem__("ai", {"like": like})), like)
        self.assertTrue(messages(lambda f: f["ai"].__setitem__("extra", 1)))
        for copy_ in ("mario", "retail:kirby", "retail:nana", "retail:", True):
            self.assertTrue(messages(lambda f, c=copy_: f.__setitem__("kirby_copy", c)), copy_)
        for good in ("none", "retail:mario", "retail:falcon", "retail:marth"):
            self.assertEqual(messages(lambda f, c=good: f.__setitem__("kirby_copy", c)), [], good)
        self.assertEqual(messages(lambda f: f.__setitem__("ai", {"like": "fox"})), [])
        # audio: presentation, geno 9; missing files are warnings; names, ids and duplicates are checked
        ok = {"announcer": "c.gnsnd", "voice": [{"sfx": 5, "file": "v.gnsnd", "volume": 90}]}
        self.assertEqual(messages(lambda f: f.__setitem__("audio", ok), 9), [x for x in messages(lambda f: None, 9)])   # only the ai/kirby 10-gate message remains
        for bad in ({"announcer": "c.wav"}, {"announcer": "d/c.gnsnd"}, {"voice": []}, {"voice": [{"sfx": 0, "file": "v.gnsnd"}]},
                    {"voice": [{"sfx": 5, "file": "v.gnsnd", "volume": 128}]}, {"voice": [{"sfx": 5, "file": "v.gnsnd"}, {"sfx": 5, "file": "w.gnsnd"}]},
                    {"voice": [{"sfx": 5}]}, {"hi": 1}):
            self.assertTrue(messages(lambda f, b=bad: f.__setitem__("audio", b)), bad)

    def test_audio_files_are_checked_when_present(self):
        require_game("pc/geno/mods/vanilla-hero/geno.json")
        import shutil
        from tools.geno import audio
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hero"
            shutil.copytree(GAME / "pc/geno/mods/vanilla-hero", root)
            data = check.load_json(root / "geno.json")
            data["geno"] = 9
            data["fighters"][0]["audio"] = {"announcer": "h_call.gnsnd", "voice": [{"sfx": 12, "file": "h_v.gnsnd"}]}
            self.assertEqual(check.validate(data, root), [])
            self.assertEqual(len([w for w in check.WARNINGS if ".audio." in w["path"]]), 2, check.WARNINGS)   # not built yet: silent
            (root / "files").mkdir(exist_ok=True)
            audio.write_tone(root / "files" / "h_call.gnsnd", 440, 120)
            audio.write_tone(root / "files" / "h_v.gnsnd", 880, 60)
            self.assertEqual(check.validate(data, root), [])
            self.assertEqual([w for w in check.WARNINGS if ".audio." in w["path"]], [])
            (root / "files" / "h_v.gnsnd").write_bytes(b"GNSDxxxx")
            self.assertTrue(any("shorter than" in e["message"] for e in check.validate(data, root)))
            (root / "files" / "h_v.gnsnd").write_bytes((root / "files" / "h_call.gnsnd").read_bytes())
            (root / "geno.json").write_text(json.dumps(data, indent=2))
            from tools.geno.define import export_package
            out = Path(tmp) / "export"
            export_package(root, out)
            self.assertTrue(any(out.rglob("h_call.gnsnd")) and any(out.rglob("h_v.gnsnd")))   # the package's own clips travel with it

    def test_presentation_needs_geno_9_and_known_keys_and_plain_gxtex_names(self):
        require_game("pc/geno/mods/vanilla-courier/geno.json")
        data = check.load_json(self.COURIER / "geno.json")
        bad = copy.deepcopy(data); bad["geno"] = 8
        self.assertTrue(check.validate(bad, self.COURIER))     # base none needs 9 as well: either message is the refusal
        hero = check.load_json(GAME / "pc/geno/mods/vanilla-hero/geno.json")
        hero["fighters"][0]["presentation"] = {"icon": "hero_icon.gxtex"}
        messages = [e["message"] for e in check.validate(hero, GAME / "pc/geno/mods/vanilla-hero")]
        self.assertTrue(any("needs geno: 9" in m for m in messages), messages)
        hero["geno"] = 9
        self.assertEqual(check.validate(hero, GAME / "pc/geno/mods/vanilla-hero"), [])   # a donor-based define may declare art at 9
        for key, value in (("banner", "a.gxtex"), ("icon", "a.png"), ("icon", "sub/a.gxtex"), ("icon", "..a.gxtex"), ("icon", ["a.gxtex"]),
                           ("stock", []), ("stock", ["a.gxtex"] * 17)):
            bad = copy.deepcopy(hero); bad["fighters"][0]["presentation"] = {key: value}
            self.assertTrue(check.validate(bad, GAME / "pc/geno/mods/vanilla-hero"), (key, value))

    def test_costume_team_and_name_rules(self):
        require_game("pc/geno/mods/vanilla-courier/geno.json")
        data = check.load_json(self.COURIER / "geno.json")
        bad = copy.deepcopy(data); bad["fighters"][0]["fighter"]["costumes"][0]["team"] = "red"
        messages = [e["message"] for e in check.validate(bad, self.COURIER)]
        self.assertTrue(any("already declared by costume 0" in m for m in messages), messages)
        for key, value in (("team", "purple"), ("name", ""), ("name", "x" * 24), ("name", "tab	here")):
            bad = copy.deepcopy(data); bad["fighters"][0]["fighter"]["costumes"][1][key] = value
            self.assertTrue(check.validate(bad, self.COURIER), (key, value))
        bad = copy.deepcopy(data); bad["fighters"][0]["presentation"]["portrait"] = ["a.gxtex"] * 5
        self.assertTrue(any("5 entries for 4 costumes" in e["message"] for e in check.validate(bad, self.COURIER)))

    def test_art_files_are_checked_when_present_and_missing_is_a_warning(self):
        require_game("pc/geno/mods/vanilla-hero/geno.json")
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hero"
            shutil.copytree(GAME / "pc/geno/mods/vanilla-hero", root)
            data = check.load_json(root / "geno.json")
            data["geno"] = 9
            data["fighters"][0]["presentation"] = {"icon": "h_icon.gxtex", "stock": "h_stock.gxtex"}
            self.assertEqual(check.validate(data, root), [])
            art = [w for w in check.WARNINGS if ".presentation." in w["path"]]
            self.assertEqual(len(art), 2, check.WARNINGS)                    # not built yet: the game draws the fallback
            (root / "files").mkdir(exist_ok=True)
            (root / "files" / "h_icon.gxtex").write_bytes(self.gxtex(5))
            (root / "files" / "h_stock.gxtex").write_bytes(self.gxtex(5))
            self.assertEqual(check.validate(data, root), [])
            self.assertEqual([w for w in check.WARNINGS if ".presentation." in w["path"]], [])
            (root / "files" / "h_stock.gxtex").write_bytes(self.gxtex(9))     # C8: a stock icon carries no palette
            messages = [e["message"] for e in check.validate(data, root)]
            self.assertTrue(any("palette format" in m for m in messages), messages)
            (root / "files" / "h_stock.gxtex").write_bytes(b"nope")
            self.assertTrue(any("not a v1 .gxtex" in e["message"] for e in check.validate(data, root)))
            (root / "files" / "h_stock.gxtex").write_bytes(self.gxtex(5))
            (root / "geno.json").write_text(json.dumps(data, indent=2))
            from tools.geno.define import export_package
            out = Path(tmp) / "export"
            export_package(root, out)
            self.assertTrue(any(out.rglob("h_icon.gxtex")))   # the package's own art travels with it


class FighterLuaTests(unittest.TestCase):
    """Slice 5: a define's "lua" block (docs/geno.md section 23). Text only; the engine's own checks (frozen environment, closure scan,
    budgets) are native and tested by `build.sh --native-test geno-lua`."""

    CHARGER = GAME / "pc/geno/mods/vanilla-charger"

    def messages(self, data):
        return [e["message"] for e in check.validate(data, self.CHARGER)]

    def test_charger_checks_clean_and_has_text_files_only(self):
        require_game("pc/geno/mods/vanilla-charger/geno.json")
        self.assertEqual(check.validate(check.load_json(self.CHARGER / "geno.json"), self.CHARGER), [])
        for p in self.CHARGER.rglob("*"):
            if p.is_file():
                self.assertIn(p.suffix.lower() or p.name, {".json", ".words", ".genoasm", ".md", ".lua", ".gitkeep"}, p)

    def test_lua_contract_errors(self):
        require_game("pc/geno/mods/vanilla-charger/geno.json")
        data = check.load_json(self.CHARGER / "geno.json")
        bad = copy.deepcopy(data); bad["geno"] = 8
        self.assertTrue(any("needs" in m and "geno" in m for m in self.messages(bad)), self.messages(bad))
        bad = copy.deepcopy(data); bad["fighters"][0]["states"][0]["lua"]["frame"] = "no_such_fn"
        self.assertTrue(any("not a function of the module" in m for m in self.messages(bad)), self.messages(bad))
        bad = copy.deepcopy(data); del bad["fighters"][0]["lua"]
        self.assertTrue(any("no \"lua\" block" in m for m in self.messages(bad)), self.messages(bad))
        bad = copy.deepcopy(data); bad["fighters"][0]["lua"]["state"]["bad name"] = "int"
        self.assertTrue(self.messages(bad))
        bad = copy.deepcopy(data); bad["fighters"][0]["lua"]["state"]["x"] = "string"
        self.assertTrue(self.messages(bad))   # schema: int / float / bool
        bad = copy.deepcopy(data); bad["fighters"][0]["lua"]["source"] = "return {}"
        self.assertTrue(any("exactly one" in m for m in self.messages(bad)), self.messages(bad))
        bad = copy.deepcopy(data); bad["fighters"][0]["lua"]["script"] = "../outside.lua"
        self.assertTrue(any("relative path" in m for m in self.messages(bad)), self.messages(bad))
        bad = copy.deepcopy(data); bad["fighters"][0]["states"][1]["name"] = "Elsewhere"
        self.assertTrue(any("never targeted" in m for m in self.messages(bad)), self.messages(bad))   # ctx.go("Release") no longer resolves
        attach = {"geno": 10, "fighters": [{"attach": "kirby", "lua": {"source": "return {}"}}]}
        self.assertTrue(any("is for a define" in m for m in self.messages(attach)), self.messages(attach))


    RIPOSTE = GAME / "pc/geno/mods/vanilla-riposte"

    def module_messages(self, body, state=None):
        """The Charger's entry with its module replaced by `body` (functions charge_enter, charge_frame, release_enter, release_frame)."""
        data = check.load_json(self.CHARGER / "geno.json")
        data["fighters"][0]["lua"] = {"source": body, "state": state or {"charge": "int", "charged": "bool"}}
        return [e["message"] for e in check.validate(data, self.CHARGER)]

    FNS = "function M.charge_enter(ctx) end function M.charge_frame(ctx) end function M.release_enter(ctx) end function M.release_frame(ctx) end "

    def wrap(self, extra):
        return "local M = {} " + self.FNS.replace("function M.charge_frame(ctx) end", "function M.charge_frame(ctx) ctx.go('Release') " + extra + " end") + "return M"

    def test_riposte_checks_clean_and_has_text_files_only(self):
        require_game("pc/geno/mods/vanilla-riposte/geno.json")
        self.assertEqual(check.validate(check.load_json(self.RIPOSTE / "geno.json"), self.RIPOSTE), [])
        for p in self.RIPOSTE.rglob("*"):
            if p.is_file():
                self.assertIn(p.suffix.lower() or p.name, {".json", ".words", ".genoasm", ".md", ".lua", ".gitkeep"}, p)

    def test_module_text_is_checked_against_the_engine_api(self):
        require_game("pc/geno/mods/vanilla-charger/geno.json")
        self.assertEqual(self.module_messages(self.wrap("local s = ctx.state s.charge = s.charge + 1")), [])
        cases = [
            ("ctx.explode()", "ctx.explode does not exist"),
            ("local x = ctx.self.hp", "ctx.self.hp does not exist"),
            ("local i = ctx.input local y = i.special_down", "ctx.input.special_down does not exist"),
            ("local s = ctx.state s.chargee = 1", "ctx.state.chargee, which is not declared"),
            ("ctx.state.charged = 1", "bool slot"),
            ("ctx.state.charge = 1.5", "int slot"),
            ("ctx.go('Nowhere')", "no state of that name"),
            ("ctx.hitbox_damage(16, 5)", "mask 16 is outside 1..15"),
            ("for k, v in pairs(ctx.self) do end", "pairs is not in the sandbox"),
            ("local t = string.rep('x', 3)", "string is not in the sandbox"),
            ("local r = math.random(5)", "math.random is not in the sandbox"),
            ("pcall(error)", "pcall is not in the sandbox"),
        ]
        for extra, want in cases:
            messages = self.module_messages(self.wrap(extra))
            self.assertTrue(any(want in m for m in messages), (extra, messages))
        # the same words in a comment or a string are not code
        self.assertEqual(self.module_messages(self.wrap("-- pairs(ctx) string.rep ctx.explode()\n local s = 'pairs ctx.self.hp'")), [])

    def test_the_api_is_read_from_the_engine(self):
        require_game("pc/geno/mods/vanilla-charger/geno.json")
        from . import lua_check
        a = lua_check.api()
        self.assertTrue({"go", "velocity", "hitbox_damage", "loop", "turn"} <= a["cmds"], a["cmds"])
        self.assertTrue({"special_held", "attack_pressed", "stick_fwd"} <= a["input"], a["input"])
        self.assertTrue({"hit_damage", "hit_from", "countered", "anim_ended", "action_frame"} <= a["self"], a["self"])
        self.assertEqual(a["math"], {"abs", "min", "max", "floor", "ceil", "sqrt", "tointeger", "huge", "pi"})

    def test_lua_counter_template_checks_clean(self):
        require_game("pc/geno/mods/vanilla-charger/geno.json")
        from . import new
        with tempfile.TemporaryDirectory() as tmp:
            root = new.create(Path(tmp) / "my-counter", "my-counter", "My Counter", template="lua-counter")
            data = check.load_json(root / "geno.json")
            self.assertEqual(data["geno"], 10)
            self.assertEqual(check.validate(data, root), [])
            data["fighters"][0]["lua"]["state"] = {}
            self.assertTrue(any("ctx.state.power, which is not declared" in e["message"] for e in check.validate(data, root)))


if __name__ == "__main__":
    unittest.main()
