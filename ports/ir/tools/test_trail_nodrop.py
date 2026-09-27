import unittest

import trail_specials_geno as SP


class TrailNoDropTest(unittest.TestCase):
    def test_unrepresentable_hitbox_id_fails(self):
        row = {"script": "game_specialtest", "commands": [
            {"cmd": "ATTACK", "frame": 3, "when": [], "named": {
                "id": "unresolved", "bone": "top", "damage": 5, "size": 3,
                "x": 0, "y": 0, "z": 0, "angle": 45, "kbg": 100, "fkb": 0, "bkb": 20}}]}
        with self.assertRaisesRegex(ValueError, "hitbox id"):
            SP.hit_events(SP.Timeline(), row, lambda x: x, {"top": 0}, [], "test")

    def test_unhandled_special_command_fails(self):
        row = {"script": "game_specialtest", "commands": [
            {"cmd": "UNKNOWN", "frame": 4, "args": [1], "when": []}]}
        with self.assertRaisesRegex(ValueError, "UNKNOWN"):
            SP.audit_special_row(row, {"top": 0})


if __name__ == "__main__":
    unittest.main()
