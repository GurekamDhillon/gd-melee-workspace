#!/usr/bin/env python3
"""Offline checks for the Ultimate ACMD versus Geno LAB report."""
import unittest
from pathlib import Path

import framedata_check as FD


ROOT = Path(__file__).resolve().parents[3]
MARTH = ROOT / "_build/agents/alpha/runs/alpha-fd-marth/scripts-data/geno-lab_lab/framedata/marth/v1"


class FrameDataCheckTest(unittest.TestCase):
    def test_marth_export_parses_without_ultimate_source(self):
        data = FD.load_export(MARTH)
        self.assertEqual(data["fighter"], "marth")
        self.assertEqual(len(data["moves"]), 22)
        self.assertEqual(sum(len(m["hitboxes"]) for m in data["moves"]), 96)
        self.assertEqual(data["moves"][8]["hitboxes"][0]["windows"], [(4, 7)])

    def test_translated_words_define_hitbox_window_and_iasa(self):
        row = {"motion": {"cancel_frame": 7}, "commands": [
            {"frame": 2, "cmd": "ATTACK", "when": [], "named": {
                "id": 0, "bone": "haver", "damage": 3.6, "angle": 45,
                "kbg": 80, "fkb": 0, "bkb": 20, "size": 2,
                "x": 1, "y": 2, "z": 3, "effect": "collision_attr_cutup"}},
            {"frame": 5, "cmd": "AttackModule::clear_all", "when": [], "args": []},
        ]}
        move = FD.expected_from_row(row, {"top": 0, "haver": 78}, 1.25)
        self.assertEqual(move["iasa"], 7)
        self.assertEqual(move["hitboxes"], [{"id": 0, "start": 2, "end": 4,
            "damage": 4, "angle": 45, "kbg": 80, "bkb": 20,
            "radius": 2.5, "bone": 78, "offset": [1.25, 2.5, 3.75]}])

    def test_comparison_flags_only_values_beyond_thresholds(self):
        expected = {"id": 0, "start": 8, "end": 10, "damage": 4,
                    "angle": 45, "kbg": 80, "bkb": 20, "radius": 2,
                    "bone": 78, "offset": [0, 0, 0]}
        measured = {"id": 0, "start": 9, "end": 11, "damage": 4.5,
                    "angle": 45, "kbg": 80, "bkb": 20, "radius": 2.2,
                    "bone": 78, "offset": None}
        self.assertEqual(FD.compare_hitbox(expected, measured), [])
        measured.update(start=10, end=12, damage=4.6, angle=46, kbg=81,
                        bkb=21, radius=2.21, bone=0)
        self.assertEqual(set(FD.compare_hitbox(expected, measured)),
                         {"start", "end", "damage", "angle", "kbg", "bkb", "radius", "bone"})

    def test_straight_angle_state_uses_converter_mapping(self):
        self.assertEqual(FD.script_for_state("AttackS3S"), "game_attacks3")
        self.assertEqual(FD.script_for_state("AttackS4S"), "game_attacks4")
        self.assertIsNone(FD.script_for_state("Neutral B"))

    def test_other_angles_are_not_missing_when_script_is_measured(self):
        export = {"fighter": "test", "moves": [
            {"name": "AttackS3S", "iasa": None, "hitboxes": []}]}
        rows = {"game_attacks3": {"commands": [], "motion": None}}
        report = FD.compare(export, rows, {"top": 0}, 1.0)
        self.assertEqual([m["name"] for m in report["moves"]], ["AttackS3S"])

    def test_unclosed_hitbox_has_unknown_end(self):
        row = {"commands": [{"frame": 2, "cmd": "ATTACK", "when": [], "named": {
            "id": 0, "bone": "top", "damage": 2, "angle": 45, "kbg": 80,
            "fkb": 0, "bkb": 20, "size": 2, "x": 0, "y": 0, "z": 0,
            "effect": "collision_attr_normal"}}]}
        move = FD.expected_from_row(row, {"top": 0}, 1.0)
        self.assertIsNone(move["hitboxes"][0]["end"])

    def test_motion_rate_changes_expected_game_frames(self):
        row = {"motion": {"cancel_frame": 40}, "commands": [
            {"frame": 1, "cmd": "FT_MOTION_RATE", "args": [0.5], "when": []},
            {"frame": 6, "cmd": "FT_MOTION_RATE", "args": [1], "when": []},
            {"frame": 8, "cmd": "ATTACK", "when": [], "named": {
                "id": 0, "bone": "top", "damage": 2, "angle": 45, "kbg": 80,
                "fkb": 0, "bkb": 20, "size": 2, "x": 0, "y": 0, "z": 0,
                "effect": "collision_attr_normal"}},
            {"frame": 11, "cmd": "AttackModule::clear_all", "args": [], "when": []},
        ]}
        move = FD.expected_from_row(row, {"top": 0}, 1.0)
        self.assertEqual((move["hitboxes"][0]["start"], move["hitboxes"][0]["end"]), (13, 15))
        self.assertEqual(move["iasa"], 45)

    def test_same_visible_hitbox_reissued_is_one_lab_window(self):
        named = {"id": 0, "bone": "top", "damage": 2, "angle": 45,
                 "kbg": 80, "fkb": 0, "bkb": 20, "size": 2,
                 "x": 0, "y": 0, "z": 0, "effect": "collision_attr_normal"}
        row = {"commands": [
            {"frame": 2, "cmd": "ATTACK", "when": [], "named": named},
            {"frame": 3, "cmd": "ATTACK", "when": [], "named": dict(named, x=1)},
            {"frame": 5, "cmd": "AttackModule::clear_all", "when": [], "args": []},
        ]}
        move = FD.expected_from_row(row, {"top": 0}, 1.0)
        self.assertEqual(len(move["hitboxes"]), 1)
        self.assertEqual((move["hitboxes"][0]["start"], move["hitboxes"][0]["end"]), (2, 4))
        self.assertEqual(move["hitboxes"][0]["offsets"], [[0, 0, 0], [1, 0, 0]])

    def test_unexpected_measured_iasa_is_reported(self):
        result = FD.compare_move("Attack11", "game_attack11",
                                 {"iasa": None, "hitboxes": []},
                                 {"iasa": 20, "hitboxes": []})
        self.assertEqual(result["counts"], {"iasa_extra": 1})


if __name__ == "__main__":
    unittest.main()
