import unittest

import trail_magic_geno as MG


class MagicNoDropTest(unittest.TestCase):
    def test_article_id_alias_fails(self):
        n = {"id": 4, "bone": "top", "damage": 5, "size": 2, "x": 0, "y": 0,
             "z": 0, "angle": 45, "kbg": 100, "fkb": 0, "bkb": 20}
        row = {"script": "game_fly", "commands": [{"cmd": "ATTACK", "frame": 0,
                                                   "when": [], "named": n}]}
        with self.assertRaisesRegex(ValueError, "four article hitbox slots"):
            MG.hitboxes_of(row, 1, [], "fire")

    def test_article_capsule_end_gets_spheres(self):
        n = {"id": 0, "bone": "top", "damage": 5, "size": 2, "x": 0, "y": 0,
             "z": 0, "x2": 0, "y2": 0, "z2": 10, "angle": 45,
             "kbg": 100, "fkb": 0, "bkb": 20}
        row = {"script": "game_fly", "commands": [{"cmd": "ATTACK", "frame": 0,
                                                   "when": [], "named": n}]}
        hits = MG.hitboxes_of(row, 1, [], "fire")
        self.assertEqual([h["slot"] for h in hits], [0, 1, 2, 3])
        self.assertEqual([h["offset"][0] for h in hits], [0, 3.333, 6.667, 10])


if __name__ == "__main__":
    unittest.main()
