#!/usr/bin/env python3
"""Offline regression checks for Ultimate special angles and carry windows."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acmd_to_ftcmd as ft
import trail_specials_geno as sp


def attack(frame, hit_id, angle, fkb=60, *, set_weight=False, hitlag=1.0, bkb=0):
    return {"frame": float(frame), "cmd": "ATTACK", "when": [], "named": {
        "id": hit_id, "bone": "top", "damage": 2, "size": 3,
        "x": 0, "y": 0, "z": 0, "x2": None, "y2": None, "z2": None,
        "angle": angle, "kbg": 100, "fkb": fkb, "bkb": bkb,
        "set_weight": set_weight, "hitlag": hitlag, "rehit": 0,
    }}


def clear(frame):
    return {"frame": float(frame), "cmd": "AttackModule::clear_all", "when": [], "args": []}


def commands(words):
    """Only the command kinds needed by these fixtures."""
    out = []
    i = 0
    while i < len(words):
        w = words[i]
        op = w >> 26
        size = 5 if op == 11 else ((w >> 16) & 15 if op == 59 else 1)
        out.append(words[i:i + size])
        i += size
    return out


class AutolinkTest(unittest.TestCase):
    def test_repeated_set_weight_windows_follow_attacker_without_changing_hit_words(self):
        commands_in = []
        for frame in (2, 6, 10):
            commands_in += [attack(frame, 0, 80, fkb=70, set_weight=True, hitlag=0.3),
                            attack(frame, 4, 108, fkb=82, set_weight=True, hitlag=0.3),
                            clear(frame + 2)]
        commands_in += [attack(15, 0, 62, fkb=0, bkb=44), clear(17)]
        row = {"commands": commands_in}
        words, _ = ft.translate(row, {"top": 0})
        cmds = commands(words)
        hits = [c for c in cmds if c[0] >> 26 == 11]
        self.assertEqual([(c[3] >> 23) & 0x1FF for c in hits], [80, 108] * 3 + [62])
        self.assertEqual([(c[3] >> 5) & 0x1FF for c in hits], [70, 82] * 3 + [0])
        links = [c for c in cmds if c[0] >> 26 == 59 and (c[0] >> 20) & 63 == 0x39]
        self.assertEqual(sum(c[1] == 2 for c in links), 6)
        self.assertEqual(sum(c[1] == 0 for c in links), 3)
        self.assertNotEqual(cmds[cmds.index(hits[-1]) + 1][0] >> 26, 59)

    def test_two_windows_do_not_trigger_carry_rule(self):
        row = {"commands": [attack(2, 0, 80, set_weight=True, hitlag=0.3),
                            attack(2, 1, 108, set_weight=True, hitlag=0.3), clear(4),
                            attack(6, 0, 80, set_weight=True, hitlag=0.3),
                            attack(6, 1, 108, set_weight=True, hitlag=0.3), clear(8)]}
        words, _ = ft.translate(row, {"top": 0})
        self.assertFalse(any(c[0] >> 26 == 59 and (c[0] >> 20) & 63 == 0x39
                             for c in commands(words)))

    def test_modes_fallback_and_lifecycle(self):
        row = {"commands": [attack(1, 0, 365), attack(2, 0, 366),
                            attack(3, 0, 367), attack(4, 0, 368, fkb=90), clear(5),
                            attack(6, 0, 45)]}
        words, _ = ft.translate(row, {"top": 0})
        cmds = commands(words)
        hits = [c for c in cmds if c[0] >> 26 == 11]
        self.assertEqual([(c[3] >> 23) & 0x1FF for c in hits], [361, 361, 361, 361, 45])
        self.assertEqual([(c[3] >> 5) & 0x1FF for c in hits], [60, 60, 60, 20, 60])
        links = [c for c in cmds if c[0] >> 26 == 59 and (c[0] >> 20) & 63 == 0x39]
        self.assertEqual(links, [[0xEF920100, 1], [0xEF920100, 2],
                                 [0xEF920100, 2], [0xEF920100, 0]])
        self.assertEqual(cmds.index([0xEF920100, 0]), cmds.index(hits[3]) + 1)

    def test_remapped_hit_uses_resident_slot(self):
        row = {"commands": [attack(1, i, 45) for i in range(4)] +
                           [attack(1, 4, 367)]}
        words, _ = ft.translate(row, {"top": 0})
        cmds = commands(words)
        linked = [(cmds[i - 1][0] >> 23) & 7 for i, c in enumerate(cmds)
                  if c == [0xEF920800, 2]]
        self.assertEqual(linked, [3])

    def test_specials_timeline_uses_same_encoding(self):
        row = {"commands": [attack(2, 0, 367), clear(3)]}
        tl = sp.Timeline()
        sp.hit_events(tl, row, lambda f: f, {"top": 0}, [], "fixture")
        cmds = commands(tl.words(4, []))
        self.assertIn([0xEF920100, 2], cmds)
        self.assertIn([0xEF920100, 0], cmds)


if __name__ == "__main__":
    unittest.main()
