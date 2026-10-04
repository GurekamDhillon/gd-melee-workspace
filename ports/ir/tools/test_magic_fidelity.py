"""Sora's neutral special (magic) fidelity: the generated geno.json / overlay words / clips.json.

Runs trail_magic_geno.py on the audit ACMD parse (the one whose sidecar matches the current parser,
passed explicitly) and checks the six casts against the fidelity audit
(_research/ultimate-trail-specials-fidelity-2026-10-03.md section 1). Skips when the parse or the
upstream param tooling is not on this machine.
"""
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACMD = os.path.join(ROOT, "_build", "tmp", "codex-nodrop-run", "trail.acmd.json")
sys.path.insert(0, HERE)
import trail_magic_geno as MG  # noqa: E402
from install_ultimate import cmd_len  # noqa: E402

REAL_CLIPS = {
    "Firaga": "d00specialn1start", "FiragaFire": "d00specialn1", "FiragaEnd": "d00specialn1end",
    "FiragaRepeat": "d00specialn12", "Blizzaga": "d00specialn2", "Thundaga": "d00specialn3",
    "FiragaAir": "d00specialairn1start", "FiragaFireAir": "d00specialairn1",
    "FiragaEndAir": "d00specialairn1end", "FiragaRepeatAir": "d00specialairn12",
    "BlizzagaAir": "d00specialairn2", "ThundagaAir": "d00specialairn3"}
GROUND = ["Firaga", "FiragaFire", "FiragaEnd", "FiragaRepeat", "Blizzaga", "Thundaga"]
LA_CYCLE, LA_CHAIN, LA_HOP = 0, 8, 9
ANIM_RATE, FACING, VEL_X, VEL_Y, HELD, STICK_X, STICK_Y = 0x1B, 0x01, 0x02, 0x03, 0x13, 0x08, 0x09


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def f32(word):
    return struct.unpack(">f", struct.pack(">I", word))[0]


def decode(words):
    """Flat ftcmd decode: (anim frame, kind, detail). Frames count SyncWaits and unrolled loops once."""
    out, at, frame = [], 0, 0
    loops = []
    while at < len(words):
        w = words[at]
        op = w >> 26
        if op == 59:
            ln = max(1, (w >> 16) & 15)
            sub = (w >> 20) & 63
            out.append((frame, "geno", {"sub": sub, "words": words[at:at + ln]}))
            at += ln
        elif op == 1:
            frame += w & 0x3FFFFFF
            at += 1
        elif op == 3:
            loops.append((frame, w & 0x3FFFFFF))
            out.append((frame, "setloop", w & 0x3FFFFFF))
            at += 1
        elif op == 4:
            start, count = loops.pop()
            frame += (frame - start) * (count - 1)       # the body ran `count` times (Melee's SetLoop / ExecuteLoop)
            out.append((frame, "execloop", count))
            at += 1
        elif op == 0:
            break
        else:
            out.append((frame, "op%d" % op, words[at]))
            at += cmd_len(w)
    return out


def geno_cmds(words, sub):
    return [(f, d["words"]) for f, kind, d in decode(words) if kind == "geno" and d["sub"] == sub]


def put_rates(words):
    """(frame, rate) PUTs of engine value ANIM_RATE; a counted loop is not expected around them."""
    return [(f, f32(w[2])) for f, w in geno_cmds(words, 0x09) if w[1] == ANIM_RATE]


def spawns(words):
    return [(f, w[2] & 0xFF, (w[2] >> 8) & 0xFF, ((w[2] >> 16) & 0xFFFF)) for f, w in geno_cmds(words, 0x20)
            if w[1] == 5]


def chg_targets(words):
    return [(f, w[1]) for f, w in geno_cmds(words, 0x30)]


class MagicGeneratorOutput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(ACMD) or not os.path.exists(ACMD + ".audit.json") or not os.path.exists(MG.PARAMXML):
            raise unittest.SkipTest("audit ACMD parse or ParamXML not on this machine")
        cls.tmp = tempfile.TemporaryDirectory()
        r = subprocess.run([sys.executable, "-B", os.path.join(HERE, "trail_magic_geno.py"), "--acmd", ACMD,
                            "--attach", "PlUs.dat", "-o", cls.tmp.name], capture_output=True, text=True)
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        cls.out = cls.tmp.name
        cls.doc = load(os.path.join(cls.out, "geno.json"))["fighters"][0]
        cls.states = {s["name"]: s for s in cls.doc["states"]}
        cls.index = {s["name"]: i for i, s in enumerate(cls.doc["states"])}
        cls.over = {o["index"]: [int(x, 16) for x in o["words"]] for o in cls.doc["subactions"]}
        cls.articles = {a["name"]: a for a in cls.doc["articles"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def words(self, name):
        return self.over[self.states[name]["subaction"]]

    # ---- 1. the real clips on the six casts ----------------------------------------------------
    def test_every_cast_has_a_state_on_its_own_common_row(self):
        names = GROUND + [n + "Air" if not n.endswith("Air") else n for n in GROUND]
        self.assertEqual(sorted(self.states), sorted(set(REAL_CLIPS)))
        rows = [self.states[n]["subaction"] for n in REAL_CLIPS]
        self.assertEqual(len(set(rows)), len(rows), "two casts share a host row (they would share a clip)")
        self.assertTrue(all(r < 341 for r in rows), "rows must be common (host independent) subactions")
        self.assertEqual(len(names), 12)

    def test_clips_json_names_the_real_magic_clips_not_the_item_scope_ones(self):
        clips = load(os.path.join(self.out, "clips.json"))["subaction_clips"]
        for name, clip in REAL_CLIPS.items():
            self.assertEqual(clips[str(self.states[name]["subaction"])], clip, name)
        self.assertFalse([c for c in clips.values() if "itemscope" in c])
        manifest = load(os.path.join(self.out, "overlay_sources.json"))
        self.assertEqual(manifest["row_clips"], clips)

    def test_geno_json_does_not_exceed_the_registry_node_pool(self):
        def count(x):
            if isinstance(x, dict):
                return 1 + sum(count(v) for v in x.values())
            if isinstance(x, list):
                return 1 + sum(count(v) for v in x)
            return 1
        # JDOC_NODES is 2048 for the whole merged file; trail_specials_geno's states / file-backed
        # overlays add 213 values (staged-install/geno.json 1317 - staged-magic 1104), keep margin
        self.assertLess(count(self.doc) + 270, 2048)

    # ---- real timing: scripts in clip frames, rates as 1/FT_MOTION_RATE ---------------------------
    def test_blizzaga_runs_in_clip_frames_with_the_acmd_rates(self):
        w = self.words("Blizzaga")
        rates = put_rates(w)
        self.assertEqual([(f, round(r, 4)) for f, r in rates],
                         [(1, 2.0), (19, 1.0), (24, 0.8), (40, 1.0), (42, 1.25), (57, 1.0)])
        self.assertEqual([f for f, *_ in spawns(w)], [24, 26, 28, 30, 32, 34, 36, 38])
        self.assertEqual([a for *_, a in spawns(w)], [4, 16, 65528, 24, 65534, 12, 65522, 0])
        tail = chg_targets(w)
        self.assertEqual(tail[-1][0], 63, "ends with the 63-frame clip")

    def test_firaga_parts_follow_their_clip_lengths_and_rates(self):
        start = self.words("Firaga")
        self.assertEqual([(f, round(r, 4)) for f, r in put_rates(start)], [(1, 1.25), (10, 1.0)])
        self.assertEqual(chg_targets(start)[-1], (18, 0x20000000 | self.index["FiragaFire"]))
        fire = self.words("FiragaFire")
        self.assertEqual([(f, round(r, 4)) for f, r in put_rates(fire)], [(1, 0.5), (6, 1.0)])
        end = self.words("FiragaEnd")
        self.assertEqual([(f, round(r, 4)) for f, r in put_rates(end)], [(0, 2.5), (11, 2.0), (15, 1.0)])
        self.assertEqual([f for f, k, d in decode(end) if k == "op23"], [16])
        rep = self.words("FiragaRepeat")
        self.assertEqual([(f, round(r, 4)) for f, r in put_rates(rep)], [(0, 2.0), (26, 1.0)])

    def test_air_clips_have_the_same_timing(self):
        for g, a in (("Firaga", "FiragaAir"), ("FiragaFire", "FiragaFireAir"), ("FiragaEnd", "FiragaEndAir"),
                     ("FiragaRepeat", "FiragaRepeatAir"), ("Blizzaga", "BlizzagaAir"), ("Thundaga", "ThundagaAir")):
            self.assertEqual(put_rates(self.words(g)), put_rates(self.words(a)), g)

    # ---- 2. Firaga chain ---------------------------------------------------------------------------
    def test_firaga_window_reads_press_and_stick_guard_from_the_audit(self):
        fire = self.words("FiragaFire")
        floats = [f32(w[2]) for _, w in geno_cmds(fire, 0x12) if w[1] in (STICK_X, STICK_Y)]
        self.assertEqual(sorted(set(round(x, 3) for x in floats)), [-0.6, -0.5, 0.5, 0.6])
        held = [f for f, w in geno_cmds(fire, 0x12) if w[1] == HELD]
        self.assertTrue(held)
        decoded = decode(fire)
        loops = [(f, c) for f, k, c in decoded if k == "setloop"]
        polled = [f for f, w in geno_cmds(fire, 0x12) if w[1] == HELD]
        # the window is clip frames 0-13 (flag 0x52e0 raised f0, dropped f14): no poll at or after f14
        self.assertEqual(min(polled), 0)
        self.assertLess(max(polled), 14)
        self.assertTrue(loops, "the poll is a counted loop (node pool)")

    def test_firaga_fire_branches_to_repeat_or_end_and_repeat_returns(self):
        i = self.index
        fire = self.words("FiragaFire")
        targets = [t for _, t in chg_targets(fire)]
        self.assertEqual(targets, [0x20000000 | i["FiragaRepeat"], 0x20000000 | i["FiragaEnd"]])
        self.assertEqual(chg_targets(self.words("FiragaRepeat"))[-1][1], 0x20000000 | i["FiragaFire"])
        self.assertEqual(chg_targets(self.words("FiragaEnd"))[-1][1], 14)  # Wait
        self.assertEqual(chg_targets(self.words("FiragaFireAir"))[0][1], 0x20000000 | i["FiragaRepeatAir"])
        self.assertEqual(chg_targets(self.words("FiragaRepeatAir"))[-1][1], 0x20000000 | i["FiragaFireAir"])

    def test_first_shot_is_fire_and_the_chained_shot_is_the_reduced_stun_variant(self):
        fire = self.words("FiragaFire")
        sp = spawns(fire)
        self.assertEqual([(f, a) for f, a, *_ in sp], [(0, list(self.articles).index("Fire")),
                                                       (0, list(self.articles).index("FireRepeat"))])
        base, rep = self.articles["Fire"], self.articles["FireRepeat"]
        strip = lambda h: {k: v for k, v in h.items() if k != "stun"}
        self.assertEqual([strip(h) for h in base["hitboxes"]], [strip(h) for h in rep["hitboxes"]])
        self.assertEqual([h["stun"] for h in base["hitboxes"]], [9, 7, 5])
        # game_fly2 is +1 / -1 / -3: a negative bonus cannot be represented (stun is 0..255): clamped to 0
        self.assertEqual([h["stun"] for h in rep["hitboxes"]], [1, 0, 0])
        chain = [w[1] for _, w in geno_cmds(self.words("FiragaRepeat"), 0x01) if (w[0] >> 8) & 0xFF == LA_CHAIN]
        self.assertEqual(chain, [1], "the repeat state marks the next fireball as a chained one")
        start = [w[1] for _, w in geno_cmds(self.words("Firaga"), 0x01) if (w[0] >> 8) & 0xFF == LA_CHAIN]
        self.assertEqual(start, [0])

    # ---- 3. air hop ---------------------------------------------------------------------------------
    def test_air_casts_hop_and_ground_casts_do_not(self):
        def hop(name):
            w = self.words(name)
            puts = [(f, ww) for f, ww in geno_cmds(w, 0x09) if ww[1] in (VEL_X, VEL_Y)]
            adds = [f32(ww[1]) for _, ww in geno_cmds(w, 0x02)]
            return puts, adds
        for n in ("FiragaFireAir", "BlizzagaAir", "ThundagaAir"):
            puts, adds = hop(n)
            self.assertEqual({p[1][1] for p in puts}, {VEL_X, VEL_Y}, n)
            self.assertIn(1.0, [round(a, 4) for a in adds], n)
        facing = [f32(ww[1]) for _, ww in geno_cmds(self.words("BlizzagaAir"), 0x04)]
        self.assertIn(-0.3, [round(x, 4) for x in facing], "x hop is -0.3 * facing")
        for n in GROUND + ["FiragaAir", "FiragaEndAir", "FiragaRepeatAir"]:
            puts, _ = hop(n)
            self.assertFalse([p for p in puts if p[1][1] in (VEL_X, VEL_Y)], n)

    def test_firaga_hops_once_per_cast(self):
        start = [ww for _, ww in geno_cmds(self.words("FiragaAir"), 0x01)]
        self.assertTrue(any(ww[0] >> 8 & 0xFF == LA_HOP and ww[1] == 0 for ww in start), "cast start clears the flag")
        fire = self.words("FiragaFireAir")
        sets = [ww for _, ww in geno_cmds(fire, 0x01) if ww[0] >> 8 & 0xFF == LA_HOP]
        self.assertTrue(any(ww[1] == 1 for ww in sets), "the hop sets the flag")

    # ---- 4. projectile lifetimes, terrain ----------------------------------------------------------
    def test_ice_shards_are_removed_at_the_weapon_script_frames(self):
        self.assertEqual(self.articles["Ice"]["lifetime"], 13)
        self.assertEqual(self.articles["IceLast"]["lifetime"], 15)
        self.assertEqual(self.articles["Fire"]["lifetime"], 40)

    def test_fire_and_ice_despawn_on_stage_contact_explicitly(self):
        for n in ("Fire", "FireRepeat", "Ice", "IceLast"):
            self.assertTrue(self.articles[n]["despawn"]["stage"], n)
            self.assertTrue(self.articles[n]["despawn"].get("hit", True), n)

    # ---- 5. the cycle advances when a cast is entered (= left, whatever the reason) ------------------
    def test_cycle_variable_moves_at_cast_entry_not_at_the_spawn(self):
        for name, nxt in (("Firaga", 1), ("Blizzaga", 2), ("Thundaga", 0)):
            for sfx in ("", "Air"):
                w = self.words(name + sfx)
                sets = [(f, ww[1]) for f, ww in geno_cmds(w, 0x01) if (ww[0] >> 8) & 0xFF == LA_CYCLE]
                self.assertEqual(sets, [(0, nxt)], name + sfx)
        for name in ("FiragaFire", "FiragaEnd", "FiragaRepeat", "FiragaFireAir", "FiragaEndAir", "FiragaRepeatAir"):
            sets = [ww for f, ww in geno_cmds(self.words(name), 0x01) if (ww[0] >> 8) & 0xFF == LA_CYCLE]
            self.assertFalse(sets, name)

    def test_specials_still_select_by_the_cycle(self):
        sp = self.doc["specials"]
        self.assertEqual(sp["n"]["targets"], ["geno:Firaga", "geno:Blizzaga", "geno:Thundaga"])
        self.assertEqual(sp["air_n"]["targets"], ["geno:FiragaAir", "geno:BlizzagaAir", "geno:ThundagaAir"])

    def test_iasa_opens_at_the_acmd_cancel_frames(self):
        def iasa_frames(name):
            return [f for f, k, d in decode(self.words(name)) if k == "op23"]
        self.assertEqual(iasa_frames("FiragaEnd"), [16])
        self.assertEqual(iasa_frames("Thundaga"), [70])
        self.assertEqual(self.states["FiragaEnd"]["iasa"], "interrupt")

    def test_manifest_covers_the_hitbox_rows_and_the_new_article(self):
        m = load(os.path.join(self.out, "overlay_sources.json"))
        rows = {e["name"]: e for e in m["rows"]}
        self.assertEqual(sorted(rows), ["Blizzaga", "BlizzagaAir", "Firaga", "FiragaAir"])
        self.assertTrue(all(e["rates"] == [] for e in m["rows"]), "overlay frames are clip frames")
        self.assertIn(("FireRepeat", "trail_fire", "game_fly2"),
                      [(a["name"], a["agent"], a["script"]) for a in m["articles"]])


class RateSemantics(unittest.TestCase):
    def test_ft_motion_rate_is_game_frames_per_clip_frame(self):
        # Sora's jab (rate 0.5 over clip frames 1-6, first hit at frame 8) is a ~6-frame jab only if a
        # rate below 1 is FASTER: the engine's ANIM_RATE (speed) is 1 / FT_MOTION_RATE.
        self.assertAlmostEqual(MG.anim_rate(0.5), 2.0)
        self.assertAlmostEqual(MG.anim_rate(2), 0.5)
        with self.assertRaises(ValueError):
            MG.anim_rate(0)

    def test_adjust_motion_frame_commands_are_rate_changes(self):
        row = {"commands": [{"cmd": "FT_MOTION_RATE", "frame": 0, "args": [0.4]},
                            {"cmd": "FT_START_ADJUST_MOTION_FRAME_REVISED_arg1", "frame": 11, "args": [0.5]},
                            {"cmd": "FT_START_ADJUST_MOTION_FRAME_arg1", "frame": 57, "args": [1]}]}
        self.assertEqual(MG.rate_events(row), [(0, 0.4), (11, 0.5), (57, 1)])


if __name__ == "__main__":
    unittest.main()
