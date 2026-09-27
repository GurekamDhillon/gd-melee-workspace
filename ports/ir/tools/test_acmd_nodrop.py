"""Failures that used to produce plausible, incomplete moves."""
import unittest
import json
from pathlib import Path
import tempfile

import acmd_to_ftcmd as FT
from acmd_loss import load_allowlist, write_losses


def row(*commands):
    return {"script": "game_test", "commands": list(commands)}


def cmd(name, *, frame=3, named=None, args=None, when=None):
    result = {"cmd": name, "frame": frame, "args": [] if args is None else args,
              "when": [] if when is None else when}
    if named is not None:
        result["named"] = named
    return result


def attack(**changes):
    named = {"id": 0, "bone": "top", "damage": 5, "size": 3, "x": 0, "y": 0,
             "z": 0, "angle": 45, "kbg": 100, "fkb": 0, "bkb": 20}
    named.update(changes)
    return cmd("ATTACK", named=named)


class NoDropTest(unittest.TestCase):
    def test_unknown_macro_fails_with_location(self):
        with self.assertRaisesRegex(ValueError, "game_test.*frame 3.*MYSTERY"):
            FT.translate(row(cmd("MYSTERY")), {"top": 0})

    def test_unparsed_attack_fails(self):
        with self.assertRaisesRegex(ValueError, "ATTACK.*arguments"):
            FT.translate(row(cmd("ATTACK", args=[1, 2])), {"top": 0})

    def test_partial_capsule_fails(self):
        with self.assertRaisesRegex(ValueError, "capsule"):
            FT.translate(row(attack(x2=4, y2=None, z2=0)), {"top": 0})

    def test_unknown_effect_fails(self):
        with self.assertRaisesRegex(ValueError, "effect"):
            FT.translate(row(attack(effect="collision_attr_unknown")), {"top": 0})

    def test_unmapped_bone_fails(self):
        with self.assertRaisesRegex(ValueError, "bone"):
            FT.translate(row(attack(bone="missing")), {"top": 0})

    def test_out_of_range_angle_fails(self):
        with self.assertRaisesRegex(ValueError, "angle"):
            FT.translate(row(attack(angle=900)), {"top": 0})

    def test_attack_abs_secondary_id_requires_review(self):
        args = [{"const": FT.ABS_THROW}, 2, 5, 45, 100, 0, 20]
        with self.assertRaisesRegex(ValueError, "ATTACK_ABS.id"):
            FT.translate(row(cmd("ATTACK_ABS", args=args)), {"top": 0})

    def test_special_angle_approximation_requires_review(self):
        with self.assertRaisesRegex(ValueError, "ATTACK.angle.368"):
            FT.translate(row(attack(angle=368)), {"top": 0})

    def test_slot_loss_has_machine_readable_detail(self):
        hits = [cmd("ATTACK", frame=3, named={**attack()["named"], "id": i, "x": 10*i})
                for i in range(5)]
        _, report = FT.translate(row(*hits), {"top": 0})
        self.assertTrue(report["losses"])
        self.assertEqual(report["losses"][0]["move"], "game_test")
        self.assertEqual(report["losses"][0]["frame"], 3)
        self.assertIn("four", report["losses"][0]["why"])

    def test_exact_reviewed_allowlist_records_who_and_why(self):
        approved = {("command", "MYSTERY"):
                    {"reason": "fixture omits a visual-only call", "approved_by": "test reviewer",
                     "moves": ["game_test"]}}
        _, report = FT.translate(row(cmd("MYSTERY")), {"top": 0}, allowlist=approved)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp, "conversion_losses.json")
            write_losses(output, report)
            loss = json.loads(output.read_text(encoding="utf-8"))["losses"][0]
        self.assertEqual((loss["move"], loss["frame"], loss["what"], loss["approved_by"]),
                         ("game_test", 3, "MYSTERY arguments []", "test reviewer"))

    def test_wildcard_allowlist_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "acmd_allowlist.json")
            source.write_text(json.dumps({"version": 1, "entries": [
                {"kind": "command", "name": "*", "reason": "broad", "approved_by": "nobody",
                 "moves": ["game_test"]}]}),
                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid or duplicate"):
                load_allowlist(source)


if __name__ == "__main__":
    unittest.main()
