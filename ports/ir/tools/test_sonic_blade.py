"""Sonic Blade's generated states against the status-code spec
(_research/ultimate-sonic-blade-spec-2026-10-03.md). Word-level checks only: they prove what the
generator emits, not how the move plays in the game."""
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest

import trail_specials_geno as sp
from test_trail_specials import decode

ACMD = os.path.join(sp.ROOT, "_build", "tmp", "codex-nodrop-run", "trail.acmd.json")
READY = os.path.exists(ACMD + ".audit.json") and os.path.exists(sp.VL)


def f32(bits):
    return struct.unpack(">f", struct.pack(">I", bits))[0]


@unittest.skipUnless(READY, "needs the audited local ACMD parse and the Ultimate extraction")
class SonicBlade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        subprocess.run([sys.executable, "-B", sp.__file__, "--acmd", ACMD, "--host", "marth", "-o", cls.tmp.name],
                       check=True, capture_output=True, text=True)
        cls.doc = json.load(open(os.path.join(cls.tmp.name, "geno.json"), encoding="utf-8"))["fighters"][0]
        cls.clips = json.load(open(os.path.join(cls.tmp.name, "clips.json"), encoding="utf-8"))["subaction_clips"]
        cls.names = [s["name"] for s in cls.doc["states"]]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def state(self, name):
        return next(s for s in self.doc["states"] if s["name"] == name)

    def events(self, name):
        row = self.state(name)["subaction"]
        overlay = next(o for o in self.doc["subactions"] if o["index"] == row)
        return decode(os.path.join(self.tmp.name, overlay["file"]))

    def targets(self, name):
        return {self.names[e["words"][1] & 0xFFFF] for e in self.events(name)
                if e["sub"] == 0x30 and e["words"][1] >> 28 == 2}

    def calls(self, name, hook):
        return [e for e in self.events(name) if e["sub"] == 0x20 and e["words"][1] == hook]

    def puts(self, name, value):
        return [e for e in self.events(name) if e["sub"] == 0x09 and e["words"][1] == value]

    def test_state_graph_is_dash_search_turn_dash(self):
        self.assertEqual(self.targets("SStart"), {"SDash1"})
        for dash in ("SDash1", "SDash2"):
            self.assertEqual(self.targets(dash), {"SSearch", "SEnd", "SEndAir"})
        self.assertEqual(self.targets("SDash3"), {"SEnd", "SEndAir"})
        self.assertEqual(self.targets("SSearch"), {"SStart2", "STurnUp", "STurnDown", "SEnd", "SEndAir"})
        for turn in ("SStart2", "STurnUp", "STurnDown"):
            self.assertEqual(self.targets(turn), {"SDash2", "SDash3"})

    def test_first_dash_is_never_aimed(self):
        for name in ("SStart", "SDash1"):
            self.assertFalse([e for e in self.events(name) if e["sub"] == 0x20 and e["words"][1] in (
                sp.HOOK_LOCKON, sp.HOOK_AIM_STICK, sp.HOOK_DASH_SEARCH, sp.HOOK_DASH_AIM)], name)
        entry = [e for e in self.events("SDash1") if e["frame"] == 0]
        speed = [e for e in entry if e["sub"] == 0x01 and (e["words"][0] >> 8) & 255 == sp.var(sp.RAF, 0)]
        self.assertAlmostEqual(f32(speed[0]["words"][1]), 3.2, places=5)
        self.assertTrue(self.puts("SDash1", sp.V_FWD_VEL))

    def test_aim_is_the_full_circle_with_no_clamp(self):
        # the old port clamped through geno.lockon / geno.aim_stick arguments; neither is used now
        for name in self.names:
            if name.startswith("S") and not name.startswith("S3"):
                self.assertFalse(self.calls(name, sp.HOOK_LOCKON) + self.calls(name, sp.HOOK_AIM_STICK), name)
        search = self.calls("SSearch", sp.HOOK_DASH_SEARCH)
        self.assertEqual([e["frame"] for e in search], list(range(9)))          # every frame of search_frame
        self.assertTrue(all(e["words"][2] == (25 | (50 << 8)) for e in search))   # stick 0.25, sphere 50
        for dash in ("SDash2", "SDash3"):
            aim = self.calls(dash, sp.HOOK_DASH_AIM)
            self.assertEqual([(e["frame"], e["words"][2]) for e in aim], [(0, 20 | (40 << 8) | (140 << 16))])
            self.assertTrue(self.puts(dash, sp.V_VEL_X) and self.puts(dash, sp.V_VEL_Y))   # world axes
            self.assertFalse(self.puts(dash, sp.V_FWD_VEL))
            air = self.puts(dash, sp.V_AIR)
            self.assertEqual([(e["frame"], e["words"][2]) for e in air], [(0, 1)])         # always airborne

    def test_dash_speed_decays_and_powered_is_not_hit_based(self):
        for dash, want in (("SDash2", 3.2 * 0.92), ("SDash3", 3.2 * 0.92 * 0.92)):
            entry = [e for e in self.events(dash) if e["frame"] == 0]
            mul = [f32(e["words"][1]) for e in entry if e["sub"] == 0x04 and not e["words"][0] & 0x80]
            self.assertAlmostEqual(mul[0], want, places=4)
            self.assertAlmostEqual(mul[1], want, places=4)
            self.assertIn(0.85, [round(m, 2) for m in mul])
            self.assertIn(1.15, [round(m, 2) for m in mul])
            every = self.events(dash)
            self.assertFalse([e for e in every if e["sub"] in (0x08, 0x12) and
                              sp.V_ATTACK_CONNECTED_PREV in e["words"][1:2]], "powered must not read a hit flag")
            guards = [e for e in every if e["frame"] == 3 and e["sub"] == 0x10 and
                      (e["words"][0] >> 8) & 255 == sp.var(sp.LAI, sp.SONIC_POWER_N)]
            self.assertEqual([e["words"][1] for e in guards], [0, 1])               # 3.0 % set / 5.2 % set

    def test_follow_up_is_stick_or_latched_special(self):
        for dash in ("SDash1", "SDash2"):
            ev = self.events(dash)
            latch = [e for e in ev if e["sub"] == 0x12 and e["words"][1] == sp.V_PRESSED]
            self.assertEqual([e["frame"] for e in latch], list(range(3, 13)))       # window opens f3 (flag 0xe65c)
            end = max(e["frame"] for e in ev)
            stick = [e for e in ev if e["frame"] == end and e["sub"] == 0x12 and e["words"][1] == sp.V_STICK_LEN]
            self.assertEqual(len(stick), 1)
            self.assertAlmostEqual(f32(stick[0]["words"][2]), 0.25, places=5)
            self.assertEqual((stick[0]["words"][0] >> 4) & 7, sp.GE)

    def test_timing_and_kinetics(self):
        for dash in ("SDash1", "SDash2", "SDash3"):
            rate = [f32(e["words"][2]) for e in self.puts(dash, sp.V_ANIM_RATE)]
            self.assertAlmostEqual(rate[0], 13 / 12, places=5)                      # 13-frame clip in attack_frame 12
            self.assertEqual(max(e["frame"] for e in self.events(dash)), 13)
            self.assertEqual(self.state(dash)["phys"], "none")
        self.assertEqual(max(e["frame"] for e in self.events("SSearch")), 9)
        for name in ("SSearch", "SStart2", "STurnUp", "STurnDown", "SEnd", "SEndAir"):
            self.assertEqual(self.state(name)["phys"], "brake", name)
        self.assertEqual(sorted(round(f32(e["words"][2]), 2) for e in self.puts("SSearch", sp.V_MOVE_F5)), [0.24, 0.34])
        cap = [e for e in self.calls("SSearch", sp.HOOK_BRAKE) if e["frame"] == 0]
        self.assertEqual(cap[0]["words"][2], 200 << 16)                             # keep at most 2.0 of the dash
        for name, clip in (("SEnd", 56), ("SEndAir", 41)):
            rates = sorted(round(f32(e["words"][2]), 4) for e in self.puts(name, sp.V_ANIM_RATE))
            self.assertEqual(rates, sorted(round(clip / n, 4) for n in (35, 40, 45)))
        self.assertEqual(round(f32(self.puts("SEnd", sp.V_MOVE_F5)[0]["words"][2]), 2), 0.12)
        self.assertEqual([round(f32(self.puts("SEndAir", v)[0]["words"][2]), 2) for v in
                          (sp.V_MOVE_F5, sp.V_MOVE_F6, sp.V_MOVE_F7)], [0.35, 0.08, 1.5])
        self.assertFalse(self.puts("SEndAir", sp.V_VEL_Y))                          # no invented +1.5 pop
        self.assertEqual(self.state("SEndAir")["landing_lag"], 20)

    def test_turn_clips(self):
        self.assertEqual([self.clips[str(self.state(n)["subaction"])] for n in ("SSearch", "SStart2", "STurnUp", "STurnDown")],
                         ["d01specialssearch", "d01specialsstart2", "d01specialsup", "d01specialsdown"])
        # earlier states keep their numbers: installed profiles and scripts refer to them
        self.assertEqual(self.names[:7], ["SStart", "SStart2", "SDash1", "SDash2", "SDash3", "SEnd", "SEndAir"])
        self.assertEqual(self.names[-3:], ["SSearch", "STurnUp", "STurnDown"])


@unittest.skipUnless(READY, "needs the audited local ACMD parse and the Ultimate extraction")
class GrabPull(unittest.TestCase):
    """A successful grab plays Sora's own pull-in clip, not the rest of the (whiff) grab clip."""

    def test_pull_states_get_the_pull_clip_on_a_row_with_an_empty_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable, "-B", sp.__file__, "--acmd", ACMD, "--host", "marth", "-o", tmp],
                           check=True, capture_output=True, text=True)
            doc = json.load(open(os.path.join(tmp, "geno.json"), encoding="utf-8"))["fighters"][0]
            clips = json.load(open(os.path.join(tmp, "clips.json"), encoding="utf-8"))["subaction_clips"]
            row = sp.PULL_ROWS["marth"]
            self.assertEqual(sorted((m["motion"], m["subaction"]) for m in doc["motion_anims"]),
                             [(213, row), (215, row)])            # CatchPull and CatchDashPull
            self.assertEqual(clips[str(row)], "e00catchpull")
            self.assertNotIn(row, [s["subaction"] for s in doc["states"]])   # a spare row, no state on it
            overlay = next(o for o in doc["subactions"] if o["index"] == row)
            events = decode(os.path.join(tmp, overlay["file"]))
            self.assertEqual([e["words"] for e in events], [[0]])            # the host's script is gone


if __name__ == "__main__":
    unittest.main()
