"""Offline Aerial Sweep carry regression, with no game or extracted data needed."""
import copy
import unittest

import acmd_to_ftcmd as ft
import trail_specials_geno as sp
from trail_upb_model import simulate
from test_acmd_autolink import attack, clear


def sweep_row():
    """The four surviving source boxes in each Sora up-special window."""
    waves = (
        (7, ((0, 4.2, 7.6, 116, 86, 4.2), (1, 12.6, 7.6, 82, 88, 4.2))),
        (8, ((2, 4.2, 16.8, 120, 110, 4.2), (3, 12.6, 16.8, 86, 108, 4.2))),
        (15, ((0, 7.6, -6.6, 124, 80, 2.4), (1, 12.2, -6.6, 70, 82, 2.4),
              (2, 7.6, -12.2, 122, 106, 2.4), (3, 12.2, -12.2, 78, 108, 2.4))),
        (18, ((0, 4.6, 6.4, 92, 76, 2.8), (1, 10, 6.4, 62, 78, 2.8),
              (2, 4.6, 14.6, 100, 108, 2.8), (3, 10, 14.6, 72, 106, 2.8))),
        (22, ((0, 8.8, -6.6, 92, 88, 2.4), (1, 13.4, -6.6, 46, 84, 2.4),
              (2, 8.8, -12.2, 88, 102, 2.4), (3, 13.4, -12.2, 48, 106, 2.4))),
        (25, ((0, 7.2, 6.4, 90, 74, 2.8), (1, 12.6, 6.4, 72, 72, 2.8),
              (2, 7.2, 14.6, 92, 98, 2.8), (3, 12.6, 14.6, 72, 96, 2.8))),
        (29, ((0, 8.2, -6.6, 130, 125, 2.4), (1, 12.8, -6.6, 110, 150, 2.4),
              (2, 8.2, -12.2, 150, 130, 2.4), (3, 12.8, -12.2, 150, 150, 2.4))),
    )
    commands = [{"frame": 4.0, "cmd": "FT_MOTION_RATE", "args": [2]},
                {"frame": 6.0, "cmd": "FT_MOTION_RATE", "args": [1]}]
    for frame, boxes in waves:
        for hit_id, y, z, fkb, angle, size in boxes:
            c = attack(frame, hit_id, angle, fkb, set_weight=True, hitlag=.3)
            c["named"].update(y=y, z=z, size=size)
            commands.append(c)
        if frame != 7:
            commands.append(clear({8: 10, 15: 18, 18: 21, 22: 25,
                                   25: 28, 29: 32}[frame]))
    finisher = attack(39, 3, 62, 0, bkb=44)
    finisher["named"].update(y=7.4, y2=9.6, x2=0, z=8.4, z2=8.4, size=5.2,
                             set_weight=False, hitlag=1)
    commands += [finisher, clear(42)]
    return {"agent": "trail", "script": "game_specialhi", "commands": commands}


class SweepConversionTest(unittest.TestCase):
    def test_carry_plan_corrects_weight_and_alternating_lanes(self):
        row = sweep_row()
        plan = ft.carry_adjustments(row, sp.UPB_CARRY_PROFILE)
        by_frame_id = {(c["frame"], c["named"]["id"]): plan[id(c)]
                       for c in row["commands"] if c["cmd"] == "ATTACK"}
        self.assertEqual(by_frame_id[(7.0, 1)]["fkb"], 49)
        self.assertEqual(by_frame_id[(15.0, 0)]["z"], 6.6)
        self.assertEqual(by_frame_id[(29.0, 0)]["fkb"], 66)
        self.assertEqual(by_frame_id[(29.0, 1)]["fkb"], 33)
        self.assertTrue(by_frame_id[(29.0, 1)]["carry"])
        self.assertGreater(by_frame_id[(29.0, 1)]["stun"], 0)
        self.assertEqual(by_frame_id[(39.0, 3)]["size"], 8)

    def test_profile_rejects_changed_source_lane(self):
        row = copy.deepcopy(sweep_row())
        for command in row["commands"]:
            if command["cmd"] == "ATTACK" and command["frame"] == 22:
                command["named"]["z"] *= -1
        with self.assertRaisesRegex(ValueError, "lane"):
            ft.carry_adjustments(row, sp.UPB_CARRY_PROFILE)

    def test_special_generator_emits_profile_geometry_link_and_stun(self):
        row = sweep_row()
        allowlist = {("case", key): {"reason": "fixture", "approved_by": "test",
                                         "moves": ["trail/game_specialhi"]}
                     for key in ("ATTACK.set_weight", "ATTACK.hitlag")}
        timeline = sp.Timeline()
        sp.hit_events(timeline, row, lambda frame: frame, {"top": 0}, [], "Hi",
                      audit=False, allowlist=allowlist, carry_profile=sp.UPB_CARRY_PROFILE)
        hits = [(frame, words) for frame, _, _, words in timeline.ev if words[0] >> 26 == 11]
        self.assertTrue(any(frame == 7 and (words[3] >> 5) & 511 == 49
                            for frame, words in hits))
        self.assertTrue(any(frame == 15 and ((words[2] & 65535) / 256) > 6
                            for frame, words in hits))
        self.assertTrue(any(frame == 29 and 0xEF920100 in words
                            for frame, words in hits))
        self.assertTrue(any(0xEFB20100 in words for _, words in hits))

    def test_continuous_trajectory_reaches_all_seven_windows(self):
        row = sweep_row()
        for distance in (55, 44):
            for fighter in ("Fox", "Marth", "Bowser", "Jigglypuff"):
                with self.subTest(distance=distance, fighter=fighter):
                    trace = simulate(row, distance, fighter, sp.UPB_CARRY_PROFILE)
                    self.assertEqual([p["frame"] for p in trace["contacts"]],
                                     [9, 17, 20, 24, 27, 31, 41])
                    self.assertTrue(all(p["incoming_hitstun"] > 0
                                        for p in trace["contacts"][1:]))
                    self.assertGreaterEqual(min(p["radius"] + p["reach"] - p["distance"]
                                                for p in trace["contacts"]), .5)


if __name__ == "__main__":
    unittest.main()
