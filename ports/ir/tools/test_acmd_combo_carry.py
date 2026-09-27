#!/usr/bin/env python3
"""ACMD combo branch and carry conversion checks; no game execution."""
import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acmd_to_ftcmd as ft
import trail_specials_geno as sp
from test_acmd_autolink import attack, clear


ACMD = Path(__file__).resolve().parents[3] / "_build/tmp/ir/trail.acmd.json"


@unittest.skipUnless(ACMD.exists(), "local Sora ACMD export unavailable")
class ComboCarryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r["script"]: r for r in json.loads(ACMD.read_text(encoding="utf-8"))
                    if r.get("agent") == "trail" and r.get("kind") == "game"}

    def test_combo_branch_uses_weak_stage_one_hits_and_rate(self):
        row = self.rows["game_attacks3"]
        combo = ft.combo_branch_tests(row)
        self.assertTrue(combo)
        hits = [c for c in row["commands"] if c["cmd"] == "ATTACK" and c["frame"] == 13]
        normal_hits = [c["named"] for c in hits if ft.default_path(c["when"])]
        combo_hits = [c["named"] for c in hits if ft.default_path(c["when"], combo)]
        self.assertEqual({n["damage"] for n in normal_hits}, {7.2})
        self.assertEqual({n["damage"] for n in combo_hits}, {5.2})
        self.assertEqual({n["kbg"] for n in combo_hits}, {14, 18})
        rates = [c["args"][-1] for c in row["commands"] if c["cmd"] == "FT_MOTION_RATE"
                 and ft.default_path(c["when"], combo)]
        self.assertEqual(rates, [0.8, 1])

    def test_carry_floor_uses_next_window_spacing_and_height(self):
        row = {"commands": [attack(2, 0, 90, fkb=60, set_weight=True, hitlag=.3),
                            attack(2, 1, 90, fkb=60, set_weight=True, hitlag=.3), clear(4),
                            attack(10, 0, 90, fkb=60, set_weight=True, hitlag=.3),
                            attack(10, 1, 90, fkb=60, set_weight=True, hitlag=.3), clear(12),
                            attack(14, 0, 90, fkb=60, set_weight=True, hitlag=.3),
                            attack(14, 1, 90, fkb=60, set_weight=True, hitlag=.3), clear(16)]}
        floor = ft.carry_fkb_floor(row, lambda frame: frame, lambda frame: 2.0)
        first = row["commands"][0]
        last = row["commands"][6]
        self.assertGreater(floor[id(first)], 60)
        self.assertNotIn(id(last), floor)
        # A point victim starts at the centre. The converted first launch stays
        # within half the next 3-unit hitbox radius after eight physics frames.
        fkb = floor[id(first)]
        kb = ((1.4 + .7 * fkb) / .875 + 18)
        rise = 8 * .03 * kb - (.23 + .051) * 8 * 9 / 2
        self.assertLessEqual(abs(rise - 16), 1.5)

    def test_sora_upper_lane_reaches_each_next_carry_box_for_fox(self):
        row = self.rows["game_specialhi"]
        time = sp.game_time(row)
        lane = [next(c for c in row["commands"] if c["cmd"] == "ATTACK"
                     and c["frame"] == frame and c["named"]["id"] == 1)
                for frame in (7, 15, 18, 22, 25, 29)]
        for distance in (55, 44):
            with self.subTest(distance=distance):
                v0 = math.sqrt(2 * .04 * distance)
                velocity = lambda frame: v0 - .04 * (frame - 9)
                floors = ft.carry_fkb_floor(row, time, velocity)
                for hit, following in zip(lane, lane[1:]):
                    start, end = int(time(hit["frame"])), int(time(following["frame"]))
                    count = end - start
                    fkb = floors.get(id(hit), hit["named"]["fkb"])
                    # Fox 75 weight, 0.23 gravity; LINK 2 redirects vertically
                    # and floors launch speed at Sora's speed.
                    kb = (1.4 + .7 * fkb) / .875 + 18
                    launch = max(.03 * kb, velocity(start))
                    relative_y = (hit["named"]["y"] + count * launch
                                  - (.23 + .051) * count * (count + 1) / 2
                                  - sum(velocity(frame) for frame in range(start, end)))
                    self.assertLessEqual(abs(relative_y - following["named"]["y"]),
                                         following["named"]["size"])

    def test_last_carry_wave_uses_source_vector_into_finisher(self):
        row = self.rows["game_specialhi"]
        linked = ft.carry_hit_commands(row)
        last = [c for c in row["commands"] if c["cmd"] == "ATTACK" and c["frame"] == 29]
        self.assertTrue(all(id(c) not in linked for c in last))
        self.assertEqual({c["named"]["angle"] for c in last}, {125, 130, 150})


if __name__ == "__main__":
    unittest.main()
