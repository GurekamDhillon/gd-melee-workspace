#!/usr/bin/env python3
"""FT_MOTION_RATE r is game frames per clip frame: the engine's ANIM_RATE (speed) is 1 / r.

Direction fixed from Sora's own data, not from either generator: jab 1 has FT_MOTION_RATE 0.5 over
clip frames 1-6 and cancel_frame 40; fighter_param combo_attack_12_end is 38. Taking r as game
frames per clip frame the cancel lands on game frame 37.5; taking r as a speed it would be 45.
"""
import struct
import unittest

import acmd_to_ftcmd as FT
import check_hitbox_positions as HP


def f32(bits):
    return struct.unpack(">f", struct.pack(">I", bits))[0]


ROW = {"script": "game_attack11", "motion": {}, "commands": [
    {"cmd": "frame", "frame": 1, "args": [1], "when": []},
    {"cmd": "FT_MOTION_RATE", "frame": 1, "args": [0.5], "when": []},
    {"cmd": "frame", "frame": 6, "args": [6], "when": []},
    {"cmd": "FT_MOTION_RATE", "frame": 6, "args": [1], "when": []}]}


class MotionRate(unittest.TestCase):
    def test_translate_puts_the_inverse_as_anim_rate(self):
        words, _ = FT.translate(ROW, {})
        puts = [(words[i + 1], f32(words[i + 2])) for i in range(len(words) - 2)
                if words[i] == (59 << 26) | (0x09 << 20) | (3 << 16)]
        self.assertEqual([v for _, v in puts], [2.0, 1.0])
        self.assertTrue(all(vid == 0x1B for vid, _ in puts))

    def test_checker_clock_multiplies_clip_frames_by_rate(self):
        self.assertEqual(HP.game_time(8, [[1, .5], [6, 1]]), 6)    # 1 + 5*.5 + 2 = 5.5
        self.assertEqual(HP.game_time(40, [[1, .5], [6, 1]]), 38)  # 37.5
        self.assertEqual(HP.game_time(8, [[4, 2], [6, 1]]), 10)    # slow beat: 4 + 2*2 + 2


if __name__ == "__main__":
    unittest.main()
