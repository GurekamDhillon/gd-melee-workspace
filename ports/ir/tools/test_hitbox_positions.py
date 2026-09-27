"""Geometry and installed-word regressions for the standing position check."""
import unittest

import numpy as np

import acmd_to_ftcmd as FT
import check_hitbox_positions as HP


class PositionTest(unittest.TestCase):
    def test_overlay_source_action_end_clears_firaga_detector(self):
        row = {"script": "game_specialn1start", "commands": [{
            "cmd": "ATTACK", "frame": 16, "args": [], "when": [],
            "named": {"id": 0, "bone": "top", "damage": 0, "size": 2.8,
                      "x": 0, "y": 7.2, "z": 3.2}}]}
        events = HP.overlay_source_events(row, {"rates": [[1, .8], [10, 1]],
                                                 "source_end": 18})
        self.assertEqual([at for at, _, _ in events], [14, 16])
        self.assertEqual(len(HP.live_source(events, 14)), 1)
        self.assertEqual(HP.live_source(events, 16), [])

    def test_both_capsule_ends_must_be_covered(self):
        pose = [np.eye(4)]
        source = {"id": 0, "bone": "top", "size": 2, "x": 0, "y": 0, "z": 0,
                  "x2": 10, "y2": 0, "z2": 0}
        near = FT.hitbox_words(0, 0, 5, 2, 0, 0, 0, 45, 100, 0, 20, 0, 0)
        far = FT.hitbox_words(1, 0, 5, 2, 10, 0, 0, 45, 100, 0, 20, 0, 0)
        self.assertEqual(HP.uncovered_endpoints(source, [near, far], pose, {"top": 0}, .5), [])
        self.assertEqual(HP.uncovered_endpoints(source, [near], pose, {"top": 0}, .5), ["end"])

    def test_joint_transform_is_applied_to_both_sides(self):
        pose = [np.eye(4), np.eye(4)]
        pose[1][:3, 3] = [20, 0, 0]
        source = {"id": 0, "bone": "arm", "size": 2, "x": 0, "y": 0, "z": 0}
        on_arm = FT.hitbox_words(0, 1, 5, 2, 0, 0, 0, 45, 100, 0, 20, 0, 0)
        on_root = FT.hitbox_words(0, 0, 5, 2, 0, 0, 0, 45, 100, 0, 20, 0, 0)
        self.assertFalse(HP.uncovered_endpoints(source, [on_arm], pose, {"arm": 1}, .5))
        self.assertEqual(HP.uncovered_endpoints(source, [on_root], pose, {"arm": 1}, .5), ["start"])

    def test_missing_installed_script_fails(self):
        with self.assertRaisesRegex(ValueError, "no installed script"):
            HP.read_installed_words(None, None, 0)

    def test_article_capsule_end_must_be_covered(self):
        source = {"id": 0, "bone": "top", "size": 2, "x": 0, "y": 0, "z": 0,
                  "x2": 0, "y2": 0, "z2": 8}
        article = {"slot": 0, "size": 2, "offset": [0, 0, 0], "start": 1, "end": 0}
        self.assertEqual(HP.uncovered_article_endpoints(source, [article], 1), ["end"])

    def test_live_installed_words_track_replacement_and_clear(self):
        first = FT.hitbox_words(0, 0, 5, 2, 0, 0, 0, 45, 100, 0, 20, 0, 0)
        second = FT.hitbox_words(0, 0, 5, 2, 8, 0, 0, 45, 100, 0, 20, 0, 0)
        events = HP.hitbox_events([(2 << 26) | 2, *first, (2 << 26) | 3, *second,
                                   (2 << 26) | 4, 16 << 26, 0])
        self.assertEqual(HP.live_spheres(events, 2), [first])
        self.assertEqual(HP.live_spheres(events, 3), [second])
        self.assertEqual(HP.live_spheres(events, 4), [])

    def test_conditional_hitbox_is_checked_on_both_paths(self):
        hit = FT.hitbox_words(0, 0, 5, 2, 0, 0, 0, 45, 100, 0, 20, 0, 0)
        conditional = (59 << 26) | (0x10 << 20) | (3 << 16)
        paths = HP.hitbox_event_paths([conditional, 0, 5, *hit, 0])
        self.assertEqual(len(paths), 2)
        self.assertEqual(sorted(len(HP.live_spheres(p, 0)) for p in paths), [0, 1])

    def test_geno_change_registration_does_not_hide_hitboxes(self):
        hit = FT.hitbox_words(0, 0, 5, 2, 0, 0, 0, 45, 100, 0, 20, 0, 0)
        change = (59 << 26) | (0x30 << 20) | (2 << 16)
        paths = HP.hitbox_event_paths([*hit, change, 7, 0])
        self.assertEqual(HP.live_spheres(paths[0], 1), [hit])

    def test_unmapped_orig_requires_audited_base_row(self):
        orig = (59 << 26) | (0x13 << 20) | (1 << 16)
        HP.check_unmapped_overlay([orig, 0], 10, {10})
        with self.assertRaisesRegex(ValueError, "audited base row"):
            HP.check_unmapped_overlay([orig, 0], 10, set())


if __name__ == "__main__":
    unittest.main()
