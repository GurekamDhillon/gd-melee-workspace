#!/usr/bin/env python3
"""The victim's thrown animation comes from the thrower's own clips, not the host's.

Melee plays a thrown victim's ThrownF/B/Hi/Lw row (motion rows 262-265, authored for kind 0x21, the
generic thrown skeleton) from the THROWER's animation table: Fighter_ChangeMotionState(victim,
msid, ..., thrower) -> ftData_80085CD8(victim, thrower, anim_id) (melee/src/melee/ft/fighter.c, ftdata.c),
retargeted by common part (ftAnim_8006FCE4 / ftPartsRemap). install_ultimate kept the host's
(Marth's TMarsThrow*, 14/7/13/13 frames) for those rows, so the victim of every Sora throw froze in
a Marth pose a few frames in. Ultimate ships the victim clips with the thrower (e01thrownf/b/hi/lw)
and plays them in step with the throw.
"""
import unittest

import install_ultimate as I


class ThrownRows(unittest.TestCase):
    NAMES = {262: "ThrownF", 263: "ThrownB", 264: "ThrownHi", 265: "ThrownLw", 266: "ThrownlwWomen",
             250: "ThrowLw"}
    BY_KEY = {"thrownf": "e01thrownf", "thrownb": "e01thrownb", "thrownhi": "e01thrownhi",
              "thrownlw": "e01thrownlw", "thrownbigf": "e01thrownbigf", "throwlw": "e01throwlw"}

    def test_foreign_thrown_rows_take_the_fighters_clips(self):
        foreign = {262: (1, 2), 263: (3, 4), 264: (5, 6), 265: (7, 8), 266: (9, 10)}
        taken = I.own_thrown_rows(foreign, self.NAMES, self.BY_KEY)
        self.assertEqual(taken, {262: "e01thrownf", 263: "e01thrownb", 264: "e01thrownhi", 265: "e01thrownlw"})

    def test_no_clip_keeps_the_host_row(self):
        self.assertEqual(I.own_thrown_rows({262: (1, 2)}, self.NAMES, {"thrownb": "x"}), {})

    def test_other_foreign_rows_stay(self):
        self.assertEqual(I.own_thrown_rows({250: (1, 2), 300: (3, 4)}, self.NAMES, self.BY_KEY), {})

    def test_author_kind_is_restamped_to_the_host_kind(self):
        # 0x21 would make the engine read the clip as the generic thrown skeleton
        self.assertEqual(I.restamp_author_kind(0x80000021, 18), 0x80000012)
        self.assertEqual(I.restamp_author_kind(0x00000021, 4), 0x00000004)


class GameTime(unittest.TestCase):
    def anim(self, n):
        vals = [{"translation": {"x": float(f), "y": 0.0, "z": 0.0}, "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
                 "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}} for f in range(n)]
        return {"final_frame_index": float(n - 1), "groups": [{"group_type": "Transform", "nodes": [
            {"name": "Hip", "tracks": [{"values": {"Transform": vals}}]}]}]}

    def xs(self, a):
        return [v["translation"]["x"] for v in a["groups"][0]["nodes"][0]["tracks"][0]["values"]["Transform"]]

    def test_no_rate_is_the_identity(self):
        a = self.anim(10)
        self.assertEqual(self.xs(I.warp_to_game_time(a, [])), [float(f) for f in range(10)])

    def test_rate_below_one_shortens_the_clip(self):
        # r = 0.8 game frames per clip frame from clip frame 4: 5 clip frames take 4 game frames
        a = I.warp_to_game_time(self.anim(10), [(4.0, 0.8)])
        xs = self.xs(a)
        self.assertEqual(xs[:5], [0.0, 1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(xs[5], 5.25)      # 1.25 clip frames per game frame
        self.assertAlmostEqual(xs[6], 6.5)
        self.assertEqual(a["final_frame_index"], len(xs) - 1)
        self.assertLess(len(xs), 10)
        self.assertAlmostEqual(xs[-1], 9.0, delta=1.25)

    def test_rate_above_one_stretches_it(self):
        a = I.warp_to_game_time(self.anim(5), [(2.0, 2.0)])
        xs = self.xs(a)
        self.assertEqual(xs[:3], [0.0, 1.0, 2.0])
        self.assertAlmostEqual(xs[3], 2.5)
        self.assertAlmostEqual(xs[4], 3.0)

    def test_segments_from_the_acmd(self):
        rows = [{"agent": "trail", "kind": "game", "owner": "fighter", "share": False, "script": "game_throwlw",
                 "commands": [{"cmd": "FT_MOTION_RATE", "frame": 20.0, "args": [0.8]},
                              {"cmd": "FT_MOTION_RATE", "frame": 40.0, "args": [1]}]}]
        self.assertEqual(I.motion_rate_segments(rows, "trail", "game_throwlw"), [(20.0, 0.8), (40.0, 1.0)])
        self.assertEqual(I.motion_rate_segments(rows, "trail", "game_throwf"), [])


if __name__ == "__main__":
    unittest.main()
