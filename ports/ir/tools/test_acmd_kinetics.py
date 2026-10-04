#!/usr/bin/env python3
"""SET_SPEED_EX / suspend_energy / resume_energy become Geno PUTs of VEL_Y (a plain row's only way
to move the fighter): a held speed while gravity is suspended, a single set otherwise."""
import struct
import unittest

import acmd_to_ftcmd as FT

PUT = (59 << 26) | (0x09 << 20) | (3 << 16)
VEL_X, FWD_VEL, VEL_Y = 0x02, 0x05, 0x03
GRAV = {"const": "0x4a8"}
TYPE = {"const": "0x348"}


def f32(bits):
    return struct.unpack(">f", struct.pack(">I", bits))[0]


def cmd(frame, name, *args):
    return {"cmd": name, "frame": frame, "args": list(args), "when": []}


def dair(extra=()):
    return {"script": "game_attackairlw", "motion": {}, "commands": [
        cmd(1, "KineticModule::suspend_energy", GRAV),
        cmd(2, "SET_SPEED_EX", 0, 1.2, TYPE),
        cmd(14, "SET_SPEED_EX", 0, -3.2, TYPE),
        cmd(40, "KineticModule::resume_energy", GRAV), *extra]}


def puts(words):
    """(value id, float) of every PUT with the frame it runs on, from AsyncWait words."""
    out, frame, i = [], 0, 0
    while i < len(words):
        w = words[i]
        op = w >> 26
        if op == 2:
            frame = w & 0x3FFFFF
        if w & 0xFFF00000 == PUT & 0xFFF00000 and op == 59 and ((w >> 20) & 0x3F) == 9:
            out.append((frame, words[i + 1], f32(words[i + 2])))
            i += 3
            continue
        i += 1
    return out


class Kinetics(unittest.TestCase):
    K = {"speed_ratio": 1.0, "gravity": 0.07}

    def test_held_speed_while_gravity_is_suspended(self):
        words, rep = FT.translate(dair(), {}, kinetics=self.K)
        vy = {f: v for f, vid, v in puts(words) if vid == VEL_Y}
        self.assertEqual(sorted(vy), list(range(2, 40)))
        self.assertAlmostEqual(vy[2], 1.2 + 0.07, places=5)     # gravity of the same frame is cancelled
        self.assertAlmostEqual(vy[13], 1.2 + 0.07, places=5)
        self.assertAlmostEqual(vy[14], -3.2 + 0.07, places=5)
        self.assertAlmostEqual(vy[39], -3.2 + 0.07, places=5)
        self.assertFalse([1 for f, vid, v in puts(words) if vid in (VEL_X, FWD_VEL)])

    def test_speed_ratio_scales_ultimate_units(self):
        words, _ = FT.translate(dair(), {}, kinetics={"speed_ratio": 1.5, "gravity": 0.0})
        vy = {f: v for f, vid, v in puts(words) if vid == VEL_Y}
        self.assertAlmostEqual(vy[2], 1.8, places=5)

    def test_single_set_without_suspension(self):
        row = {"script": "m", "motion": {}, "commands": [cmd(5, "SET_SPEED_EX", 0.5, 0.0, TYPE)]}
        words, _ = FT.translate(row, {}, kinetics=self.K)
        got = puts(words)
        self.assertEqual([(f, vid) for f, vid, _ in got], [(5, FWD_VEL), (5, VEL_Y)])
        self.assertAlmostEqual(got[0][2], 0.5, places=5)

    def test_a_dive_past_terminal_raises_the_fall_limit_instead_of_losing_speed(self):
        words, rep = FT.translate(dair(), {}, kinetics={"speed_ratio": 1.0, "gravity": 0.07, "terminal": 1.8})
        self.assertFalse([l for l in rep["losses"] if l.get("source") == "kinetics approximation"])
        puts = [(words[i + 1], struct.unpack(">f", struct.pack(">I", words[i + 2]))[0])
                for i, w in enumerate(words[:-2]) if w == FT.PUT_WORD]
        limits = [v for vid, v in puts if vid == FT.V_FALL_LIMIT]
        dives = [v for vid, v in puts if vid == FT.V_VEL_Y and v < -1.8]
        self.assertTrue(dives)
        self.assertEqual(len(limits), 1)                       # raised once, where the dive begins
        self.assertGreaterEqual(limits[0], -min(dives))        # and it admits the fastest dive speed
        first_limit = next(i for i, (vid, _) in enumerate(puts) if vid == FT.V_FALL_LIMIT)
        first_dive = next(i for i, (vid, v) in enumerate(puts) if vid == FT.V_VEL_Y and v < -1.8)
        self.assertLess(first_limit, first_dive)

    def test_without_kinetics_the_commands_are_losses_as_before(self):
        # the allowlist approves exactly trail/game_attackairlw; an unlisted move must still fail
        row = dict(dair(), script="game_other")
        row["agent"] = "trail"
        with self.assertRaises(ValueError):
            FT.translate(row, {})


if __name__ == "__main__":
    unittest.main()
