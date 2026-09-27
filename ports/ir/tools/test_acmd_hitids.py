#!/usr/bin/env python3
"""Offline checks for Ultimate hitbox IDs mapped onto Melee's four slots."""
import json
from pathlib import Path
import unittest

import acmd_to_ftcmd as FT


ROOT = Path(__file__).resolve().parents[3]
SORA_ACMD = ROOT / "_build/tmp/ir/trail.acmd.json"


def attack(frame, hit_id, damage=5, size=3):
    return {"frame": float(frame), "cmd": "ATTACK", "when": [], "named": {
        "id": hit_id, "bone": "top", "damage": damage, "size": size,
        "x": 0, "y": 0, "z": 0, "angle": 45, "kbg": 100, "fkb": 0, "bkb": 20,
    }}


def clear(frame, hit_id=None):
    return {"frame": float(frame), "cmd": "AttackModule::clear_all" if hit_id is None else "AttackModule::clear",
            "args": [] if hit_id is None else [hit_id], "when": []}


def decoded(words):
    """Return frame, operation, and slot for hitbox commands."""
    frame, result, i = 0, [], 0
    while i < len(words):
        w = words[i]
        op = w >> 26
        if op == 2:
            frame = w & 0x3FFFFFF
        elif op == 11:
            result.append((frame, "hit", (w >> 23) & 7))
            i += 4
        elif op == 15:
            result.append((frame, "remove", w & 0x3FFFFFF))
        elif op == 16:
            result.append((frame, "clear", None))
        elif op == 34:
            i += 2
        elif op == 59:
            i += 2
        elif op == 56:
            i += 1
        i += 1
    return result


class HitIdTest(unittest.TestCase):
    def translate(self, commands):
        return FT.translate({"commands": commands}, {"top": 0})

    def test_free_slot_is_reused_after_clear(self):
        words, rep = self.translate([attack(2, 0), attack(2, 4), clear(3, 0), attack(4, 5),
                                     clear(5, 4), clear(6, 5)])
        self.assertEqual(decoded(words), [(2, "hit", 0), (2, "hit", 1), (3, "remove", 0),
                                          (4, "hit", 0), (5, "remove", 1), (6, "remove", 0)])
        self.assertEqual(rep.get("dropped_hitboxes", []), [])

    def test_same_id_replacement_keeps_slot_and_hit_group(self):
        words, _ = self.translate([attack(2, 4, 2), attack(3, 4, 7), clear(4, 4)])
        self.assertEqual(decoded(words), [(2, "hit", 0), (3, "hit", 0), (4, "remove", 0)])
        self.assertEqual([(w >> 20) & 7 for w in words if w >> 26 == 11], [0, 0])

    def test_overflow_keeps_damage_then_radius_and_reports_every_drop(self):
        words, rep = self.translate([attack(2, 0, 5, 3), attack(2, 1, 5, 2),
                                     attack(2, 2, 5, 4), attack(2, 3, 5, 5),
                                     attack(2, 4, 6, 1), attack(2, 5, 1, 9)])
        events = decoded(words)
        self.assertEqual(events[-2:], [(2, "remove", 1), (2, "hit", 1)])
        self.assertEqual([d["id"] for d in rep["dropped_hitboxes"]], [1, 5])
        self.assertEqual(sum(kind == "hit" for _, kind, _ in events), 5)

    def test_equal_priority_keeps_earlier_box(self):
        words, rep = self.translate([attack(2, 0, 5, 3), attack(2, 1, 5, 3),
                                     attack(2, 2, 5, 3), attack(2, 3, 5, 3),
                                     attack(2, 4, 6, 3)])
        self.assertEqual(decoded(words)[-2:], [(2, "remove", 3), (2, "hit", 3)])
        self.assertEqual(rep["dropped_hitboxes"][0]["id"], 3)

    def test_dropped_box_promotes_when_a_slot_clears(self):
        words, rep = self.translate([*(attack(2, i) for i in range(5)), clear(3, 0), clear(4, 4)])
        self.assertEqual(decoded(words)[-3:], [(3, "remove", 0), (3, "hit", 0),
                                               (4, "remove", 0)])
        self.assertEqual([d["id"] for d in rep["dropped_hitboxes"]], [4])

    def test_replacement_can_promote_a_more_important_dropped_box(self):
        words, rep = self.translate([attack(2, 0, 6), attack(2, 1, 5), attack(2, 2, 5),
                                     attack(2, 3, 5), attack(2, 4, 4), attack(3, 0, 1)])
        self.assertEqual(decoded(words)[-2:], [(3, "remove", 0), (3, "hit", 0)])
        self.assertEqual([d["id"] for d in rep["dropped_hitboxes"]], [4, 0])

    def test_grab_far_end_above_three_gets_a_valid_slot(self):
        grab = {"frame": 2.0, "cmd": "CATCH", "when": [], "named": {
            "id": 2, "bone": "top", "size": 3, "x": 0, "y": 0, "z": 1,
            "x2": 0, "y2": 0, "z2": 5, "situation": {"const": "0xe7cc"}}}
        words, rep = self.translate([grab, {"frame": 4.0, "cmd": "GrabModule::clear_all", "when": []}])
        self.assertEqual(decoded(words), [(2, "hit", 2), (2, "hit", 0), (4, "clear", None)])
        self.assertEqual(rep["grab_boxes"], 1)

    def test_ordinary_grab_remove_keeps_legacy_bytes(self):
        grab = {"frame": 2.0, "cmd": "CATCH", "when": [], "named": {
            "id": 0, "bone": "top", "size": 3, "x": 0, "y": 0, "z": 1,
            "x2": None, "situation": {"const": "0xe7cc"}}}
        remove = {"frame": 4.0, "cmd": "GrabModule::clear", "args": [0], "when": []}
        words, _ = self.translate([grab, remove])
        self.assertEqual(decoded(words), [(2, "hit", 0)])
        self.assertNotIn((2 << 26) | 4, words)

    def test_low_ids_keep_original_words(self):
        commands = [attack(2, 0), attack(2, 1), attack(3, 0, 6), clear(4, 1), clear(5)]
        words, rep = self.translate(commands)
        expected = [(2 << 26) | 2, *FT.hitbox_words(0, 0, 5, 3, 0, 0, 0, 45, 100, 0, 20, 0, 0),
                    *FT.hitbox_words(1, 0, 5, 3, 0, 0, 0, 45, 100, 0, 20, 0, 0),
                    (2 << 26) | 3, *FT.hitbox_words(0, 0, 6, 3, 0, 0, 0, 45, 100, 0, 20, 0, 0),
                    (2 << 26) | 4, (15 << 26) | 1, (2 << 26) | 5, 16 << 26, 0]
        self.assertEqual(words, expected)
        self.assertNotIn("dropped_hitboxes", rep)

    @unittest.skipUnless(SORA_ACMD.exists(), "local Sora ACMD export unavailable")
    def test_sora_listed_moves(self):
        rows = {r["script"]: r for r in json.loads(SORA_ACMD.read_text(encoding="utf-8"))
                if r.get("agent") == "trail" and r.get("kind") == "game"}
        cases = {"game_attack12": (7, 2), "game_attackairhi": (10, 1),
                 "game_attackhi3": (12, 3), "game_attacks4": (18, 8)}
        for script, (first_frame, drop_count) in cases.items():
            with self.subTest(script=script):
                words, rep = FT.translate(rows[script], {"top": 0})
                events = decoded(words)
                self.assertTrue(any(f == first_frame and kind == "hit" for f, kind, _ in events))
                self.assertEqual(len(rep["dropped_hitboxes"]), drop_count)
                live = set()
                for _, kind, slot in events:
                    if kind == "hit":
                        self.assertLess(slot, 4)
                        live.add(slot)
                    elif kind == "remove":
                        self.assertIn(slot, live)
                        live.remove(slot)
                    elif kind == "clear":
                        live.clear()
                    self.assertLessEqual(len(live), 4)
                if script == "game_attackairhi":
                    self.assertEqual(rep["dropped_hitboxes"][0]["id"], 3)
                    self.assertEqual([e for e in events if e[0] == 10][-2:],
                                     [(10, "remove", 3), (10, "hit", 3)])
                    self.assertIn((12, "remove", 3), events)
                if script == "game_attacks4":
                    self.assertEqual(sum(f == 21 and kind == "hit" for f, kind, _ in events), 2)


if __name__ == "__main__":
    unittest.main()
