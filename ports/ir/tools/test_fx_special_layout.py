#!/usr/bin/env python3
"""Sora's effect bindings against the generators' current state layout.

The tool's own bindings are built in memory from the ACMD dump (nothing shared on disk is read), so
these checks hold whatever the default output directories contain. Expected frames are transcribed
from the effect scripts (effect_specialn1start ... in the Ghidra dump), not from the generator.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import trail_fx_bindings as FX
import trail_magic_geno as M

ROOT = Path(__file__).resolve().parents[3]
STAGED_GENO = ROOT / '_build' / 'audit-20261003' / 'sora-fx' / 'staged-specials' / 'geno.json'


def frames(state):
    return [(c['frame'], c['package'][7:], c.get('end_frame')) for c in state['calls']]


class SpecialLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dump = ROOT / '_build' / 'ultimate-vfx' / 'ef_trail'
        acmd = Path(os.environ.get('GW_GHIDRA_PROJECTS', Path.home() / 'ghidra-projects')) / 'sora_acmd'
        if not dump.is_dir() or not acmd.is_dir():
            raise unittest.SkipTest('the effect dump or the Ghidra ACMD dump is not on this machine')
        import plan_parts
        from convert_ultimate_anim import INSTANCES
        sets, own = FX.own_names(str(dump))
        rows, body = FX.parsed_rows(str(acmd), own)
        joint_of = {j['name'].lower(): i for i, j in enumerate(plan_parts.plan(body)['joints'])}
        joint_of['top'] = 0
        scripts, _common, _after, _losses = FX.census(rows, own, joint_of, 1.0)
        host_ir = json.loads(Path(INSTANCES, 'marth.melee.ir.json').read_text(encoding='utf-8'))
        cls.scripts = scripts
        cls.bindings = FX.bind(scripts, host_ir, 'marth', set(sets), str(acmd))
        cls.states = {s['state']: s for s in cls.bindings['states']}

    def test_search_effect_plays_when_the_turn_starts(self):
        # effect_specialssearch fires SonicTurn at frame 9; the SEARCH state is 9 frames long, so the
        # call is never seen there: it belongs to frame 0 of the three turn states.
        self.assertNotIn('SSearch', self.states)
        for state, row in (('SStart2', 304), ('STurnUp', 317), ('STurnDown', 318)):
            self.assertEqual(self.states[state]['subaction'], row)
            self.assertEqual(sorted((c['situation'], c['frame'], c['package']) for c in self.states[state]['calls']),
                             [('air', 0, 'P_TrailSonicTurn'), ('ground', 0, 'P_TrailSonicTurn')])

    def test_dashes_use_their_own_script_and_end_has_none(self):
        for n in (1, 2, 3):
            self.assertTrue(self.states['SDash%d' % n]['script'].startswith('effect_specials%d' % n))
        for state in ('SEnd', 'SEndAir'):
            self.assertNotIn(state, self.states)

    def test_every_clock_is_the_clip(self):
        for st in self.bindings['states']:
            self.assertEqual(st['clock'], 'animation', st['state'])

    def test_magic_has_one_state_per_cast_part_in_clip_frames(self):
        expected = {
            # FireShot / FireKeyblade are at frame 18 = the end of specialn1start, i.e. frame 0 of specialn1
            'Firaga': ('effect_specialn1start', [(0, 'FireHold', None)]),
            'FiragaFire': ('effect_specialn1+effect_specialn1start',
                           [(0, 'FireShot', 13), (0, 'FireKeyblade', None), (1, 'FireImpact', None),
                            (1, 'FireImpact', None)]),
            'FiragaEnd': ('effect_specialn1end', [(0, 'FireEnd', None)]),
            'FiragaRepeat': ('effect_specialn12',
                             [(0, 'FireEnd', None), (13, 'FireHold', None),
                              (29, 'FireShot', None), (29, 'FireKeyblade', None)]),
            'Blizzaga': ('effect_specialn2',
                         [(0, 'IceHold', None), (0, 'IceSwordFlare', 36), (24, 'IceShot', None)]),
            'Thundaga': ('effect_specialn3', [(0, 'ThunderHold', None), (26, 'ThunderShot', None)]),
        }
        for state, (script, calls) in expected.items():
            self.assertEqual(self.states[state]['script'], script, state)
            self.assertEqual(self.states[state]['subaction'], M.CAST_ROW[state], state)
            self.assertEqual(frames(self.states[state]), calls, state)
            air = state + 'Air'
            self.assertEqual(self.states[air]['subaction'], M.CAST_ROW[air], air)
            if '+' not in script:
                self.assertEqual(self.states[air]['script'], script.replace('effect_special', 'effect_specialair', 1))
        # the air script carries the same shape natively: FireShot at 0 of specialairn1, detached at 13
        self.assertEqual(frames(self.states['FiragaFireAir']), frames(self.states['FiragaFire']))
        # the air Blizzaga script starts its hold at 13, not 0
        self.assertEqual(frames(self.states['BlizzagaAir'])[0][0], 13)

    def test_every_bound_row_exists_in_the_current_profile(self):
        if not STAGED_GENO.exists():
            self.skipTest('no staged profile')
        FX.check_against_geno(self.bindings, json.loads(STAGED_GENO.read_text(encoding='utf-8'))['fighters'][0])

    def test_every_special_call_is_bound(self):
        # The unbound rest are approved losses of non-special moves (aerials the host rows do not carry).
        losses = FX.audit_unbound(self.scripts, self.bindings)
        self.assertEqual([x for x in losses if not x.get('approved_by')], [])
        self.assertEqual([x['move'] for x in losses if 'special' in x['move'] or 'attacks3' in x['move']], [])


class CarryTest(unittest.TestCase):
    def test_call_at_the_last_frame_moves_to_successors_and_takes_their_end(self):
        call = {'frame': 9.0, 'effect': 'e', 'package': 'P_TrailX', 'source': ['f', 0]}
        states = [{'state': 'A', 'subaction': 1, 'clock': 'animation', 'script': 'effect_a', 'calls': [call]},
                  {'state': 'B', 'subaction': 2, 'clock': 'animation', 'script': 'effect_b', 'calls': []}]
        by_script = {'effect_b': {'end_calls': [{'effect': 'e', 'frame': 13.0, 'macro': 'EFFECT_DETACH_KIND'}]}}
        saved = dict(FX.HANDOFF)
        FX.HANDOFF.clear()
        FX.HANDOFF['A'] = ('B', 'C')
        try:
            FX.carry_past_end(states, by_script, {'A': 9}, {'A': 1, 'B': 2, 'C': 3})
        finally:
            FX.HANDOFF.clear()
            FX.HANDOFF.update(saved)
        self.assertEqual([s['state'] for s in states], ['B', 'C'])
        b, c = states
        self.assertEqual((b['calls'][0]['frame'], b['calls'][0]['end_frame'], b['calls'][0]['end_event']), (0.0, 13.0, 'detach'))
        self.assertEqual((c['subaction'], c['calls'][0]['frame']), (3, 0.0))
        self.assertEqual(call['frame'], 9.0, 'the census call itself is not modified')

    def test_late_call_with_no_successor_is_an_error(self):
        states = [{'state': 'A', 'subaction': 1, 'clock': 'animation', 'script': 'effect_a',
                   'calls': [{'frame': 5.0, 'effect': 'e', 'package': 'P_TrailX'}]}]
        with self.assertRaisesRegex(ValueError, 'A: effect calls at frame >= 5 never play'):
            FX.carry_past_end(states, {}, {'A': 5}, {})


class ProfileCheckTest(unittest.TestCase):
    @staticmethod
    def bindings(*pairs):
        return {'states': [{'state': n, 'subaction': r, 'calls': []} for n, r in pairs]}

    def test_row_mismatch_and_overlaid_host_row_fail(self):
        fighter = {'states': [{'name': 'SSearch', 'subaction': 314}, {'name': 'Hi', 'subaction': 321}]}
        FX.check_against_geno(self.bindings(('SSearch', 314), ('Attack11', 46)), fighter)
        with self.assertRaisesRegex(ValueError, 'SSearch: bound to row 300'):
            FX.check_against_geno(self.bindings(('SSearch', 300)), fighter)
        with self.assertRaisesRegex(ValueError, 'host row 321 is the profile.s state Hi'):
            FX.check_against_geno(self.bindings(('AttackX', 321)), fighter)


class AttachTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        pk = self.tmp / 'pk'
        (pk / 'tex').mkdir(parents=True)
        (pk / 'mesh').mkdir()
        for name in ('P_TrailFireBullet', 'P_TrailKeybladeFlare'):
            (pk / (name + '.gfx.json')).write_text(json.dumps(
                {'textures': [{'file': 'tex/%s.png' % name}], 'meshes': [{'file': 'mesh/%s.json' % name}]}))
            (pk / 'tex' / (name + '.png')).write_bytes(b'png')
            (pk / 'mesh' / (name + '.json')).write_text('{}')
        (pk / 'tex' / 'unused.png').write_bytes(b'x')
        self.pk = pk
        self.mod = self.tmp / 'mod'
        self.mod.mkdir()
        geno = {'geno': 5, 'fighters': [{'attach': 'PlUs.dat', 'states': [{'name': 'Hi', 'subaction': 321}],
                                         'articles': [{'name': 'Fire'}, {'name': 'FireLast', 'fx': 'keep'},
                                                      {'name': 'Mystery'}]}]}
        (self.mod / 'geno.json').write_text(json.dumps(geno))
        self.bindings = {'geno_fx_bindings': 1, 'states': [
            {'state': 'Hi', 'subaction': 321, 'calls': [{'package': 'P_TrailKeybladeFlare'}]}]}

    def test_attach_sets_key_copies_referenced_assets_and_article_fx(self):
        out = FX.attach_to(str(self.mod), str(self.pk), self.bindings, attach='PlUs.dat')
        fighter = json.loads((self.mod / 'geno.json').read_text())['fighters'][0]
        self.assertEqual(fighter['fx_bindings'], 'fx/fx_bindings.json')
        self.assertEqual([a.get('fx') for a in fighter['articles']], ['P_TrailFireBullet', 'keep', None])
        self.assertEqual(out['articles_filled'], ['Fire'])
        fx = self.mod / 'fx'
        self.assertTrue((fx / 'P_TrailKeybladeFlare' / 'P_TrailKeybladeFlare.gfx.json').exists())
        self.assertTrue((fx / 'P_TrailKeybladeFlare' / 'tex' / 'P_TrailKeybladeFlare.png').exists())
        self.assertFalse((fx / 'P_TrailKeybladeFlare' / 'tex' / 'unused.png').exists())
        self.assertEqual(json.loads((fx / 'fx_bindings.json').read_text()), self.bindings)
        FX.attach_to(str(self.mod), str(self.pk), self.bindings, attach='PlUs.dat')   # idempotent

    def test_attach_refuses_a_binding_the_profile_does_not_have(self):
        self.bindings['states'][0]['subaction'] = 999
        with self.assertRaisesRegex(ValueError, 'do not match'):
            FX.attach_to(str(self.mod), str(self.pk), self.bindings)
        fighter = json.loads((self.mod / 'geno.json').read_text())['fighters'][0]
        self.assertNotIn('fx_bindings', fighter)


if __name__ == '__main__':
    unittest.main()
