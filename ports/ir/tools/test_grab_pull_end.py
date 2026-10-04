#!/usr/bin/env python3
"""A converted grab ends its pull (Melee op 20) where the grab window closes.

Melee's CatchPull state (ftCo_CatchPull_Anim, ftCo_Catch.c) keeps playing the Catch clip and leaves
for CatchWait only when the clip runs out or the script sets throw_flags_b3 (op 20). Marth's own
Catch / CatchDash scripts (PlMs.dat 0x6538 / 0x65BC) end the window with `Clear hitboxes; op 20`.
A converted grab script without the op kept the victim in the pull for the whole clip (48 frames
measured on Sora, 2026-10-03).
"""
import unittest

import acmd_to_ftcmd as FT

ALLOW = {("command", n): {"reason": "fixture", "approved_by": "test fixture", "moves": ["<unnamed move>"]}
         for n in ("GrabModule::set_rebound", "WorkModule::on_flag", "UNCONSUMED_ACMD_ARGS")}


def catch(frame, i, z):
    return {"cmd": "CATCH", "frame": frame, "named": {
        "id": i, "bone": "top", "size": 3.3, "x": 0.0, "y": 6.6, "z": z, "x2": 0.0, "y2": 6.6, "z2": z + 4,
        "status": {"const": "0x80c"}, "situation": {"const": "0xe7cc"}}}


def ops_by_frame(words):
    frame, out, i = 0, [], 0
    while i < len(words):
        op = words[i] >> 26
        if op == 2:
            frame = words[i] & 0x3FFFFFF
        out.append((frame, op))
        i += FT_len(words[i])
    return out


def FT_len(word):
    import install_ultimate as I
    return I.cmd_len(word)


class GrabPullEnd(unittest.TestCase):
    def convert(self, clear_cmd="GrabModule::clear_all"):
        row = {"agent": "x", "script": "game_catch", "commands": [
            catch(9.0, 0, 4.6),
            {"cmd": clear_cmd, "frame": 11.0, "args": [{"const": "0xe7d4"}]}]}
        return FT.translate(row, {"top": 0}, 1.25, allowlist=ALLOW)

    def test_pull_ends_with_the_grab_window(self):
        words, rep = self.convert()
        ops = ops_by_frame(words)
        self.assertIn((11, 16), ops)                 # clear hitboxes
        self.assertIn((11, 20), ops)                 # op 20 on the same frame: throw_flags_b3
        self.assertEqual(rep.get("grab_pull_end_frame"), 11.0)

    def test_no_pull_end_without_a_grab(self):
        row = {"agent": "x", "script": "game_attack", "commands": [
            {"cmd": "AttackModule::clear_all", "frame": 5.0, "args": []}]}
        words, rep = FT.translate(row, {"top": 0}, 1.25, allowlist=ALLOW)
        self.assertNotIn(20, [op for _, op in ops_by_frame(words)])


if __name__ == "__main__":
    unittest.main()
