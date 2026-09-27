#!/usr/bin/env python3
"""Offline checks for Ultimate hitbox IDs mapped onto Melee's four slots."""
import json
from pathlib import Path
import unittest

import acmd_to_ftcmd as FT


ROOT = Path(__file__).resolve().parents[3]
SORA_ACMD = ROOT / "_build/tmp/ir/trail.acmd.json"


def attack(frame, hit_id, damage=5, size=3, *, angle=45, fkb=0, x=0, y=0, z=0):
    return {"frame": float(frame), "cmd": "ATTACK", "when": [], "named": {
        "id": hit_id, "bone": "top", "damage": damage, "size": size,
        "x": x, "y": y, "z": z, "angle": angle, "kbg": 100, "fkb": fkb, "bkb": 20,
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
            i += ((w >> 16) & 15) - 1
        elif op == 56:
            i += 1
        i += 1
    return result


def live_boxes(words):
    """Snapshot slot -> (angle, FKB, Y, Z) after each frame's commands."""
    frame, live, snapshots, i = 0, {}, {}, 0
    while i < len(words):
        w = words[i]
        op = w >> 26
        if op == 2:
            frame = w & 0x3FFFFFF
        elif op == 11:
            w2, w3 = words[i + 2:i + 4]
            signed = lambda v: v - 0x10000 if v & 0x8000 else v
            live[(w >> 23) & 7] = ((w3 >> 23) & 0x1FF, (w3 >> 5) & 0x1FF,
                                    signed(w2 >> 16) / 256, signed(w2 & 0xFFFF) / 256)
            i += 4
        elif op == 15:
            live.pop(w & 0x3FFFFFF, None)
        elif op == 16:
            live.clear()
        elif op == 34:
            i += 2
        elif op == 59:
            i += ((w >> 16) & 15) - 1
        elif op == 56:
            i += 1
        snapshots[frame] = dict(live)
        i += 1
    return snapshots


def live_geometry(words, target_frame):
    """Decode the actual Melee sphere geometry live after a frame's commands."""
    frame, live, i = 0, {}, 0
    signed = lambda v: v - 0x10000 if v & 0x8000 else v
    while i < len(words):
        w = words[i]
        op = w >> 26
        if op == 2:
            frame = w & 0x3FFFFFF
        elif op == 11:
            w1, w2 = words[i + 1:i + 3]
            live[(w >> 23) & 7] = ((w >> 11) & 0xFF, w1 >> 16,
                                    signed(w1 & 0xFFFF) / 256,
                                    signed(w2 >> 16) / 256,
                                    signed(w2 & 0xFFFF) / 256)
            i += 4
        elif op == 15:
            live.pop(w & 0x3FFFFFF, None)
        elif op == 16:
            live.clear()
        elif op == 34:
            i += 2
        elif op == 59:
            i += ((w >> 16) & 15) - 1
        elif op == 56:
            i += 1
        if frame > target_frame:
            break
        i += 1
    return live


def links(words):
    """Return (mask, mode) for complete two-word Geno LINK commands."""
    result, i = [], 0
    while i < len(words):
        w = words[i]
        op = w >> 26
        if op == 59:
            size = (w >> 16) & 15
            if (w >> 20) & 63 == 0x39:
                assert size == 2
                result.append(((w >> 8) & 255, words[i + 1]))
        else:
            size = 5 if op == 11 else 3 if op == 34 else 2 if op == 56 else 1
        i += size
    return result


class HitIdTest(unittest.TestCase):
    def translate(self, commands):
        fixture_cases = {("case", "ATTACK.angle.366"):
                         {"reason": "slot allocation fixture", "approved_by": "test fixture",
                          "moves": ["<unnamed move>"]}}
        return FT.translate({"commands": commands}, {"top": 0}, allowlist=fixture_cases)

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
        words, rep = self.translate([attack(2, 0, 5, 3, x=0), attack(2, 1, 5, 2, x=20),
                                     attack(2, 2, 5, 4, x=40), attack(2, 3, 5, 5, x=60),
                                     attack(2, 4, 6, 1, x=80), attack(2, 5, 1, 9, x=100)])
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

    def test_distinct_linking_box_beats_higher_damage(self):
        words, rep = self.translate([*(attack(2, i, 10, x=20*i) for i in range(4)),
                                     attack(2, 4, 1, 2, fkb=60, x=100)])
        self.assertEqual([d["id"] for d in rep["dropped_hitboxes"]], [3])
        self.assertTrue(any(box[1] == 60 for box in live_boxes(words)[2].values()))

    def test_near_duplicate_drops_before_distinct_linking_role(self):
        words, rep = self.translate([attack(2, 0, 3, angle=86, fkb=100, x=0),
                                     attack(2, 1, 3, angle=92, fkb=110, x=0),
                                     attack(2, 2, 3, angle=120, fkb=100, x=20),
                                     attack(2, 3, 3, angle=150, fkb=100, x=40),
                                     attack(2, 4, 1, angle=366, x=60)])
        self.assertEqual([d["id"] for d in rep["dropped_hitboxes"]], [1])
        self.assertTrue(any(box[0] == 361 for box in live_boxes(words)[2].values()))
        self.assertIn((1 << 1, 2), links(words))

    def test_repeated_hit_windows_count_as_linking_loop(self):
        words, rep = self.translate([attack(2, 0, 1), clear(3), attack(4, 0, 1, x=0),
                                     *(attack(4, i, 10, x=20*i) for i in range(1, 5))])
        self.assertEqual([d["id"] for d in rep["dropped_hitboxes"]], [4])
        self.assertEqual(len(live_boxes(words)[4]), 4)

    def test_dropped_box_promotes_when_a_slot_clears(self):
        words, rep = self.translate([*(attack(2, i) for i in range(5)), clear(3, 0), clear(4, 4)])
        self.assertEqual(decoded(words)[-3:], [(3, "remove", 0), (3, "hit", 0),
                                               (4, "remove", 0)])
        self.assertEqual([d["id"] for d in rep["dropped_hitboxes"]], [4])

    def test_replacement_can_promote_a_more_important_dropped_box(self):
        words, rep = self.translate([attack(2, 0, 6, x=0), attack(2, 1, 5, x=20),
                                     attack(2, 2, 5, x=40), attack(2, 3, 5, x=60),
                                     attack(2, 4, 4, x=80), attack(3, 0, 1, x=0)])
        self.assertEqual(decoded(words)[-2:], [(3, "remove", 0), (3, "hit", 0)])
        self.assertEqual([d["id"] for d in rep["dropped_hitboxes"]], [4, 0])

    def test_grab_far_end_above_three_gets_a_valid_slot(self):
        grab = {"frame": 2.0, "cmd": "CATCH", "when": [], "named": {
            "id": 2, "bone": "top", "size": 3, "x": 0, "y": 0, "z": 1,
            "x2": 0, "y2": 0, "z2": 5, "status": {"const": "0x80c"},
            "situation": {"const": "0xe7cc"}}}
        words, rep = self.translate([grab, {"frame": 4.0, "cmd": "GrabModule::clear_all", "when": []}])
        self.assertEqual(decoded(words), [(2, "hit", 2), (2, "hit", 0), (4, "clear", None)])
        self.assertEqual(rep["grab_boxes"], 1)

    def test_ordinary_grab_remove_keeps_legacy_bytes(self):
        grab = {"frame": 2.0, "cmd": "CATCH", "when": [], "named": {
            "id": 0, "bone": "top", "size": 3, "x": 0, "y": 0, "z": 1,
            "x2": None, "status": {"const": "0x80c"}, "situation": {"const": "0xe7cc"}}}
        remove = {"frame": 4.0, "cmd": "GrabModule::clear", "args": [0], "when": []}
        words, _ = self.translate([grab, remove])
        self.assertEqual(decoded(words), [(2, "hit", 0), (4, "remove", 0), (4, "remove", 2)])

    def test_low_ids_keep_original_words(self):
        commands = [attack(2, 0), attack(2, 1), attack(3, 0, 6), clear(4, 1), clear(5)]
        words, rep = self.translate(commands)
        rehit = lambda slot: [(59 << 26) | (0x38 << 20) | (2 << 16) | (1 << (slot + 8)), 0]
        expected = [(2 << 26) | 2, *FT.hitbox_words(0, 0, 5, 3, 0, 0, 0, 45, 100, 0, 20, 0, 0),
                    *rehit(0), *FT.hitbox_words(1, 0, 5, 3, 0, 0, 0, 45, 100, 0, 20, 0, 0),
                    *rehit(1), (2 << 26) | 3,
                    *FT.hitbox_words(0, 0, 6, 3, 0, 0, 0, 45, 100, 0, 20, 0, 0), *rehit(0),
                    (2 << 26) | 4, (15 << 26) | 1,
                    (59 << 26) | (0x38 << 20) | (2 << 16) | (1 << (1 + 8)), 0,
                    (2 << 26) | 5, 16 << 26,
                    (59 << 26) | (0x38 << 20) | (2 << 16) | (15 << 8), 0, 0]
        self.assertEqual(words, expected)
        self.assertFalse(rep["losses"])

    def test_long_capsule_covers_blade_and_x_axis_with_four_slots(self):
        a = attack(10, 0, size=2.4, x=0, y=2.4, z=6.2)
        b = attack(10, 1, size=2.4, x=0, y=2.4, z=6.2)
        a["named"].update(x2=0, y2=2.41, z2=14.6)
        b["named"].update(x2=0, y2=2.41, z2=19.8)
        words, rep = self.translate([a, b, clear(12)])
        live = live_geometry(words, 10)
        self.assertEqual(len(live), 4)
        self.assertTrue(rep["losses"])
        self.assertTrue(all(joint == 0 and radius == 614 for joint, radius, *_ in live.values()))
        self.assertTrue(any(abs(z - 19.8) < .25 for _, _, _, _, z in live.values()))
        for z in (6.2, 8, 10, 12, 14, 16, 18, 19.8):
            self.assertTrue(any(abs(cz - z) <= radius / 256 + .02
                                for _, radius, _, _, cz in live.values()), z)
        x_capsule = attack(2, 0, size=2, x=1, y=0, z=0)
        x_capsule["named"].update(x2=9, y2=0, z2=0)
        x_words, _ = self.translate([x_capsule, clear(4)])
        self.assertTrue(any(abs(x - 9) < .02 for _, _, x, _, _ in live_geometry(x_words, 2).values()))

    def test_very_long_capsule_has_bounded_candidate_count_and_keeps_tip(self):
        n = attack(2, 0, size=1)["named"]
        n.update(x2=100, y2=0, z2=0)
        spheres = FT.attack_spheres(n, 0)
        self.assertLessEqual(len(spheres), 8)
        self.assertEqual(spheres[-1]["capsule"][1], (100, 0, 0))

    def test_unresolved_capsule_end_fails(self):
        n = attack(2, 0, size=2, z=3)["named"]
        n.update(x2="unresolved", y2=0, z2=9)
        with self.assertRaisesRegex(ValueError, "capsule"):
            FT.attack_spheres(n, 0)

    def test_capsule_replacement_and_id_clear_release_every_slot(self):
        first = attack(2, 0, size=2)
        first["named"].update(x2=0, y2=0, z2=8)
        second = attack(3, 0, size=2)
        second["named"].update(x2=0, y2=0, z2=12)
        words, _ = self.translate([first, second, clear(4, 0)])
        self.assertTrue(any(abs(z - 12) < .02 for _, _, _, _, z in live_geometry(words, 3).values()))
        self.assertEqual(live_geometry(words, 4), {})

    @unittest.skipUnless(SORA_ACMD.exists(), "local Sora ACMD export unavailable")
    @unittest.skip("current Sora ACMD needs reviewed loss cases before translation")
    def test_sora_down_tilt_reaches_blade_tip(self):
        row = next(r for r in json.loads(SORA_ACMD.read_text(encoding="utf-8"))
                   if r.get("agent") == "trail" and r.get("script") == "game_attacklw3")
        words, _ = FT.translate(row, {"top": 0})
        live = live_geometry(words, 10)
        self.assertEqual(len(live), 4)
        self.assertTrue(any(abs(z - 19.8) < .25 for _, _, _, _, z in live.values()))
        self.assertEqual(live_geometry(words, 12), {})

    @unittest.skipUnless(SORA_ACMD.exists(), "local Sora ACMD export unavailable")
    @unittest.skip("current Sora ACMD needs reviewed loss cases before translation")
    def test_sora_combo_special_overlay_keeps_capsule_tip(self):
        import trail_specials_geno as sp
        row = next(r for r in json.loads(SORA_ACMD.read_text(encoding="utf-8"))
                   if r.get("agent") == "trail" and r.get("script") == "game_attacks33")
        tl = sp.Timeline()
        sp.hit_events(tl, row, lambda f: f, {"top": 0}, [], "S3Combo3")
        z_centres = [((w[2] & 0xFFFF) - (0x10000 if w[2] & 0x8000 else 0)) / 256
                     for frame, _, _, w in tl.ev if frame == 12 and w and w[0] >> 26 == 11]
        self.assertTrue(any(abs(z - 14) < .5 for z in z_centres), z_centres)

    @unittest.skipUnless(SORA_ACMD.exists(), "local Sora ACMD export unavailable")
    @unittest.skip("current Sora ACMD needs reviewed loss cases before translation")
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

    @unittest.skipUnless(SORA_ACMD.exists(), "local Sora ACMD export unavailable")
    @unittest.skip("current Sora ACMD needs reviewed loss cases before translation")
    def test_sora_up_tilt_and_up_special_keep_linking_coverage(self):
        rows = {r["script"]: r for r in json.loads(SORA_ACMD.read_text(encoding="utf-8"))
                if r.get("agent") == "trail" and r.get("kind") == "game"}
        tilt, _ = FT.translate(rows["game_attackhi3"], {"top": 0})
        tilt_live = live_boxes(tilt)
        self.assertEqual([mode for _, mode in links(tilt) if mode == 2], [2] * 4)
        for frame, angle, fkb, z in ((12, 88, 62, 0), (16, 88, 62, 0), (20, 104, 22, 8.6)):
            with self.subTest(move="up tilt", frame=frame):
                self.assertTrue(any(a == angle and kb == fkb and abs(pz-z) < .02
                                    for a, kb, _, pz in tilt_live[frame].values()))
                self.assertEqual(len(tilt_live[frame]), 4)
        for script in ("game_specialhi", "game_specialairhi"):
            with self.subTest(move=script):
                words, _ = FT.translate(rows[script], {"top": 0})
                self.assertEqual([mode for _, mode in links(words)].count(2), 20)
                self.assertEqual([mode for _, mode in links(words)].count(0), 5)
                snapshots = live_boxes(words)
                for frame in (8, 15, 18, 22, 25, 29):
                    boxes = list(snapshots[frame].values())
                    self.assertEqual(len(boxes), 4)
                    self.assertTrue(all(fkb > 0 for _, fkb, _, _ in boxes))
                    self.assertEqual(len({(round(y, 1), round(z, 1)) for _, _, y, z in boxes}), 4)


if __name__ == "__main__":
    unittest.main()
