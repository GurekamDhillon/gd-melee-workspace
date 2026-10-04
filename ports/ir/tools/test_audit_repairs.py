"""Behavioral regressions from the October 2026 conversion audit."""
import copy
import hashlib
import json
import unittest

import acmd_to_ftcmd as FT
import install_ultimate as IU
import trail_magic_geno as MG
import trail_specials_geno as SP
import check_hitbox_positions as HP


def attack(idx=0, **extra):
    n = dict(id=idx, bone='top', damage=5, angle=45, kbg=100, fkb=0, bkb=20,
             size=3, x=0, y=0, z=0)
    n.update(extra)
    return dict(cmd='ATTACK', frame=3, args=[], named=n)


def row(*commands):
    return dict(script='game_test', commands=list(commands))


def commands(words):
    out = []
    at = 0
    while at < len(words):
        out.append(words[at] >> 26)
        at += IU.cmd_len(words[at])
    return out


class ConversionAuditRepairs(unittest.TestCase):
    def test_motion_rate_is_game_frames_per_clip_frame_in_every_clock(self):
        # FT_MOTION_RATE r: one clip frame takes r game frames (2026-10-03: the engine jab went from a
        # first hit on action frame 12 to 4 with this direction; the 2026-10-03 morning repair had it inverted).
        source = row(dict(cmd='FT_MOTION_RATE', frame=1, args=[.5]),
                     dict(cmd='FT_MOTION_RATE', frame=6, args=[1]))
        self.assertEqual(MG.game_time(source)(8), 5.5)   # 1 + 5 x 0.5 + 2, unrounded
        self.assertEqual(SP.game_time(source)(8), 5.5)
        self.assertEqual(HP.game_time(8, [[1, .5], [6, 1]]), 6)

    def test_attack_then_clear_at_same_frame_finishes_disabled(self):
        words, _ = FT.translate(row(attack(), dict(cmd='AttackModule::clear_all', frame=3, args=[])), {'top': 0})
        ops = commands(words)
        self.assertLess(ops.index(11), ops.index(16))

    def test_clear_then_attack_at_same_frame_keeps_new_attack(self):
        words, _ = FT.translate(row(dict(cmd='AttackModule::clear_all', frame=3, args=[]), attack()), {'top': 0})
        ops = commands(words)
        self.assertLess(ops.index(16), ops.index(11))

    def test_special_attack_then_clear_at_same_frame_finishes_disabled(self):
        timeline = SP.Timeline()
        SP.hit_events(timeline, row(attack(), dict(cmd='AttackModule::clear_all', frame=3, args=[])),
                      lambda frame: frame, {'top': 0}, [], 'fixture', audit=False)
        ops = commands(timeline.words(5, []))
        self.assertLess(ops.index(11), ops.index(16))

    def test_unknown_gameplay_condition_is_rejected(self):
        hit = attack()
        hit['when'] = [dict(test='damage > 50', holds=True)]
        with self.assertRaisesRegex(ValueError, 'condition'):
            FT.translate(row(hit), {'top': 0})

    def test_unknown_condition_using_flag_variable_is_rejected(self):
        hit = attack()
        hit['when'] = [dict(test='uVar4 > 50', holds=False)]
        with self.assertRaisesRegex(ValueError, 'condition'):
            FT.translate(row(hit), {'top': 0})

    def test_unknown_nested_condition_cannot_hide_behind_unselected_flag(self):
        with self.assertRaisesRegex(ValueError, 'unsupported ACMD condition'):
            FT.default_path([dict(test='(uVar4 & 1) != 0', holds=True),
                             dict(test='damage > 50', holds=False)])

    def test_nonpositive_baked_motion_rate_is_rejected(self):
        for rate in (0, -1):
            source = row(dict(cmd='FT_MOTION_RATE', frame=1, args=[rate]))
            for converter in (MG.game_time, SP.game_time):
                with self.subTest(rate=rate, converter=converter.__module__):
                    with self.assertRaisesRegex(ValueError, 'motion rate'):
                        converter(source)(8)

    def test_article_simultaneous_ids_have_distinct_slots(self):
        hits = MG.hitboxes_of(row(attack(0), attack(1, x=10)), 1, [], 'fixture')
        self.assertEqual(len({h['slot'] for h in hits}), 2)

    def test_article_replacement_reuses_its_slots_without_stealing_other_id(self):
        replacement = attack(0, damage=6)
        replacement['frame'] = 6
        hits = MG.hitboxes_of(row(attack(0), attack(1, x=10), replacement), 1, [], 'fixture')
        self.assertEqual(hits[0]['slot'], hits[2]['slot'])
        self.assertNotEqual(hits[1]['slot'], hits[2]['slot'])

    def test_article_same_spawn_frame_replacement_leaves_no_previous_capsule_samples(self):
        capsule = attack(0, size=2, x2=0, y2=0, z2=10)
        sphere = attack(0)
        capsule['frame'] = sphere['frame'] = 0
        hits = MG.hitboxes_of(row(capsule, sphere), 1, [], 'fixture')
        live = [h for h in hits if h['start'] <= 1 and (h['end'] == 0 or h['end'] >= 1)]
        self.assertEqual(len(live), 1)

    def test_article_capsules_cannot_overcommit_four_live_slots(self):
        with self.assertRaisesRegex(ValueError, 'four.*slots'):
            MG.hitboxes_of(row(attack(0, size=2, x2=0, y2=0, z2=10), attack(1)), 1, [], 'fixture')

    def test_article_nonzero_rehit_is_honestly_rejected(self):
        with self.assertRaisesRegex(ValueError, 'article.*rehit'):
            MG.hitboxes_of(row(attack(rehit=7)), 1, [], 'fixture')

    def test_modified_moveset_payload_does_not_reuse_source_audit(self):
        doc = {'fighter': 'fixture', 'rows': {'44': {'words': [0]}}, 'report': {}, 'omissions': []}
        payload = json.dumps(doc, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        doc['audit'] = dict(version=1, source_sha256=hashlib.sha256(b'[]').hexdigest(),
                            converter_sha256=IU.acmd_converter_digest(),
                            payload_sha256=hashlib.sha256(payload).hexdigest())
        IU.verify_moveset_audit(doc, b'[]')
        changed = copy.deepcopy(doc)
        changed['rows']['44']['words'] = [16 << 26, 0]
        with self.assertRaisesRegex(ValueError, 'payload|words'):
            IU.verify_moveset_audit(changed, b'[]')


if __name__ == '__main__':
    unittest.main()
