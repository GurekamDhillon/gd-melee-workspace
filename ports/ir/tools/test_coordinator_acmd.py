"""Offline checks for the coordinator-approved Sora conversion paths."""
import struct
import unittest

import acmd_parse as AP
import acmd_to_ftcmd as FT
import trail_magic_geno as MAGIC
import trail_specials_geno as SPECIALS
from acmd_loss import LossGuard


def command(name, frame, **extra):
    return {"cmd": name, "frame": frame, "args": [], "when": [], **extra}


def attack(hit_id=0, damage=2.8, rehit=0):
    return {"id": hit_id, "bone": "top", "damage": damage, "angle": 45,
            "kbg": 90, "fkb": 0, "bkb": 20, "size": 3, "x": hit_id * 8,
            "y": 0, "z": 0, "rehit": rehit}


class CoordinatorAcmdTest(unittest.TestCase):
    def test_detector_capsule_uses_hbflags_seven_after_remap(self):
        n = attack(5, 0)
        n.update(x=0, x2=0, y2=0, z2=8, disable_hitlag=True, flinchless=True)
        row = {"script": "test", "commands": [command("ATTACK", 3, named=n)]}
        words, _ = FT.translate(row, {"top": 0})
        flags = [(w, words[i + 1]) for i, w in enumerate(words[:-1])
                 if w & 0xFFFF0000 == 0xEFC20000]
        slots = {(w >> 23) & 7 for w in words if w >> 26 == 11}
        self.assertGreater(len(slots), 1)
        self.assertEqual({((w >> 8) & 15, value) for w, value in flags},
                         {(1 << slot, 7) for slot in slots})

    def test_counter_force_reaction_survives_hitbox_replacement(self):
        row = {"agent": "trail", "script": "game_speciallw", "commands": [
            command("ATTACK", 7, named=attack(5, 9)),
            command("AttackModule::set_force_reaction", 7, args=[5, True, False]),
            command("ATTACK", 10, named=attack(5, 9))]}
        tl = SPECIALS.Timeline()
        SPECIALS.hit_events(tl, row, lambda f: f, {"top": 0}, [], "LwAttack", losses=[])
        words = tl.words(12, [])
        active = [(w, words[i + 1]) for i, w in enumerate(words[:-1])
                  if w & 0xFFFF0000 == 0xEFC20000 and words[i + 1] == 8]
        self.assertGreaterEqual(len(active), 2)

    def test_magic_body_detector_is_a_live_hitbox(self):
        n = attack(0, 0)
        n.update(disable_hitlag=True, flinchless=True)
        row = {"agent": "trail", "script": "game_specialn2", "commands": [
            command("ATTACK", 22, named=n),
            command("AttackModule::clear", 24, args=[0])]}
        self.assertEqual(MAGIC.audit_magic_row(row, article=False), [])
        words = MAGIC.body_attack_words(n, 1.0)
        self.assertTrue(any(w & 0xFFFF0000 == 0xEFC20000 and words[i + 1] == 7
                            for i, w in enumerate(words[:-1])))

    def test_firaga_start_detector_is_emitted_and_cleared(self):
        n = attack(0, 0)
        n.update(disable_hitlag=True, flinchless=True)
        row = {"agent": "trail", "script": "game_specialn1start", "commands": [
            command("ATTACK", 16, named=n)]}
        events = MAGIC.firaga_detector_events(row, 1.0, 18)
        self.assertEqual([f for f, _ in events], [16, 18])
        self.assertIn(7, events[0][1])
        self.assertIn(16 << 26, events[1][1])

    def test_fighter_reaction_stun_follows_spawn_and_replacement(self):
        row = {"script": "test", "commands": [
            command("ATTACK", 3, named=attack(0, 5)),
            command("AttackModule::set_add_reaction_frame_revised", 3,
                    args=[0, 11, False]),
            command("ATTACK", 6, named=attack(0, 6)),
            command("AttackModule::set_add_reaction_frame_revised", 6,
                    args=[0, 8, False])]}
        words, _ = FT.translate(row, {"top": 0})
        stun = [(w, words[i + 1]) for i, w in enumerate(words[:-1])
                if w & 0xFFFF0000 == 0xEFB20000]
        self.assertEqual(stun, [(0xEFB20100, 0), (0xEFB20100, 11),
                                (0xEFB20100, 0), (0xEFB20100, 8)])

    def test_reaction_stun_uses_remapped_slot_and_capsule_mask(self):
        n = attack(5, 9)
        n.update(x=0, x2=0, y2=0, z2=6)
        row = {"script": "test", "commands": [
            command("ATTACK", 3, named=n),
            command("AttackModule::set_add_reaction_frame_revised", 3,
                    args=[5, 12, False])]}
        words, _ = FT.translate(row, {"top": 0})
        spawned = {(w >> 23) & 7 for w in words if w >> 26 == 11}
        stun = [(w, words[i + 1]) for i, w in enumerate(words[:-1])
                if w & 0xFFFF0000 == 0xEFB20000]
        self.assertGreater(len(spawned), 1)
        self.assertEqual(stun[-1], (0xEFB20000 | (sum(1 << i for i in spawned) << 8), 12))

    def test_reaction_stun_before_first_spawn_is_carried_to_slot(self):
        row = {"script": "test", "commands": [
            command("AttackModule::set_add_reaction_frame_revised", 2,
                    args=[5, 11, False]),
            command("ATTACK", 3, named=attack(5, 5))]}
        words, report = FT.translate(row, {"top": 0})
        self.assertEqual(report["pending_reaction_stun"],
                         [{"frame": 2, "id": 5, "frames": 11}])
        slot = next((w >> 23) & 7 for w in words if w >> 26 == 11)
        self.assertTrue(any(w == FT.hbstun(1 << slot, 11)[0] and words[i + 1] == 11
                            for i, w in enumerate(words[:-1])))

    def test_reaction_stun_out_of_range_fails(self):
        row = {"script": "test", "commands": [
            command("ATTACK", 3, named=attack()),
            command("AttackModule::set_add_reaction_frame_revised", 3,
                    args=[0, 256, False])]}
        with self.assertRaisesRegex(ValueError, "set_add_reaction_frame_revised.*256"):
            FT.translate(row, {"top": 0})

    def test_dropped_source_bonus_follows_later_slot_entry(self):
        row = {"script": "test", "commands": [
            *(command("ATTACK", 3, named=attack(i, 9 if i < 4 else 1))
              for i in range(5)),
            command("AttackModule::set_add_reaction_frame_revised", 3,
                    args=[4, 12, False]),
            command("AttackModule::clear", 6, args=[0])]}
        words, report = FT.translate(row, {"top": 0})
        stun = [(w, words[i + 1]) for i, w in enumerate(words[:-1])
                if w & 0xFFFF0000 == 0xEFB20000 and words[i + 1] == 12]
        self.assertEqual(len(stun), 1)
        self.assertTrue(report["dropped_hitboxes"])

    def test_geno_special_overlay_emits_reaction_stun(self):
        row = {"agent": "trail", "script": "game_attacks32", "commands": [
            command("ATTACK", 7, named=attack(5, 5)),
            command("AttackModule::set_add_reaction_frame_revised", 7,
                    args=[5, 10, False])]}
        tl = SPECIALS.Timeline()
        SPECIALS.hit_events(tl, row, lambda f: f, {"top": 0}, [], "S3Combo2", losses=[])
        words = tl.words(10, [])
        self.assertTrue(any(w & 0xFFFF0000 == 0xEFB20000 and words[i + 1] == 10
                            for i, w in enumerate(words[:-1])))

    def test_article_reaction_stun_replaces_active_window(self):
        row = {"agent": "trail_fire", "script": "game_fly", "commands": [
            command("ATTACK", 0, named=attack(0, 5)),
            command("AttackModule::set_add_reaction_frame_revised", 0,
                    args=[0, 9, False]),
            command("ATTACK", 10, named=attack(0, 5)),
            command("AttackModule::set_add_reaction_frame_revised", 10,
                    args=[0, 7, False])]}
        hits = MAGIC.hitboxes_of(row, 1.0, [], "fire")
        self.assertEqual([(h["start"], h["stun"]) for h in hits], [(1, 9), (11, 7)])

    def test_negative_article_stun_is_rejected(self):
        row = {"agent": "trail_fire", "script": "game_fly2", "commands": [
            command("ATTACK", 0, named=attack(0, 5)),
            command("AttackModule::set_add_reaction_frame_revised", 0,
                    args=[0, -1, False])]}
        with self.assertRaisesRegex(ValueError, "set_add_reaction_frame_revised.*-1"):
            MAGIC.hitboxes_of(row, 1.0, [], "fire")

    def test_fractional_damage_and_rehit_follow_remapped_spawn(self):
        row = {"script": "test", "commands": [
            *(command("ATTACK", 3, named=attack(i, 9.8 if i == 4 else 5, 2 if i == 4 else 0))
              for i in range(5)), command("AttackModule::clear_all", 6)]}
        words, report = FT.translate(row, {"top": 0})
        self.assertTrue(report["losses"])  # the fifth source box needs four-slot arbitration
        float_word = struct.unpack(">I", struct.pack(">f", 9.8))[0]
        hbdmg = [i for i, w in enumerate(words) if w >> 26 == 59 and (w >> 20) & 63 == 0x3A]
        for i in hbdmg:
            self.assertEqual(words[i + 1], float_word)
            self.assertEqual(words[i - 5] >> 26, 11)
        self.assertTrue(any(w >> 26 == 59 and (w >> 20) & 63 == 0x38 and
                            words[i + 1] == 2 for i, w in enumerate(words[:-1])))
        self.assertTrue(any(w >> 26 == 59 and (w >> 20) & 63 == 0x38 and
                            words[i + 1] == 0 for i, w in enumerate(words[:-1])))

    def test_hurt_state_uses_converted_hurtbone(self):
        row = {"script": "test", "commands": [
            command("HIT_NODE", 7, args=["kneer", {"const": "0xc50"}]),
            command("HIT_NODE", 11, args=["kneer", {"const": "0xc90"}])]}
        words, _ = FT.translate(row, {"kneer": 40}, hurt_joint_of_bone={"kneer": 23})
        hurt = [w for w in words if w >> 26 == 28]
        self.assertEqual([(w >> 18 & 255, w & 0x3FFFF) for w in hurt], [(23, 2), (23, 0)])

    def test_article_capsule_and_reflect_absorb_flags(self):
        n = attack(0, 5, 0)
        n.update(size=3.6, x=0, y=.4, z=0, x2=0, y2=10, z2=0,
                 reflectable=True, absorbable=False)
        row = {"agent": "trail_thunder", "script": "game_fall", "commands": [
            command("ATTACK", 5, named=n)]}
        hits = MAGIC.hitboxes_of(row, 1.0, [], "bolt")
        self.assertEqual(len(hits), 3)
        self.assertEqual([h["slot"] for h in hits], [0, 1, 2])
        self.assertEqual([h["offset"][1] for h in hits], [.4, 5.2, 10])
        self.assertTrue(all(h["hits"]["reflect"] and not h["hits"]["absorb"] for h in hits))

    def test_param_one_helper_is_parsed(self):
        commands = AP.parse_body("FUN_7100054560(param_1,aLStack_40);", None, {},
                                 {"7100054560": "FOOT_EFFECT"})
        self.assertEqual([c["cmd"] for c in commands], ["FOOT_EFFECT"])

    def test_return_value_constructor_is_not_an_acmd_argument(self):
        commands = AP.parse_body("lib::L2CValue::L2CValue(param_1,0);\nreturn;", None, {}, {})
        self.assertEqual(commands, [])

    def test_allowlist_rejects_different_source_move(self):
        guard = LossGuard("trail/game_attack12", {("command", "MYSTERY"):
                          {"moves": ["trail/game_attack11"], "reason": "reviewed",
                           "approved_by": "coordinator"}})
        with self.assertRaisesRegex(ValueError, "trail/game_attack12.*MYSTERY"):
            guard.omit(8, "command", "MYSTERY", "MYSTERY call")


if __name__ == "__main__":
    unittest.main()
