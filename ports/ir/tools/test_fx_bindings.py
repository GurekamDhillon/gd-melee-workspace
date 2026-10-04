#!/usr/bin/env python3
"""Offline checks for trail's imported packages and fighter effect bindings.

The expected calls below were transcribed from the Ghidra C, not copied from the
binding generator. ACMD's bone-local offsets use the same 1.0 scale as
acmd_to_ftcmd.translate for this Ultimate-rig port.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import jsonschema

import trail_fx_bindings as FX
import trail_magic_geno as M

ROOT = Path(__file__).resolve().parents[3]
# SORA_FX_PACKAGES points the file checks at another package directory (a copy under _build/...).
OUT = Path(os.environ.get('SORA_FX_PACKAGES') or ROOT / '_build' / 'tmp' / 'codex-fx' / 'trail')


class FxBindingsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bindings = json.loads((OUT / 'fx_bindings.json').read_text())
        cls.states = {s['state']: s for s in cls.bindings['states']}

    def test_schemas_and_package_references(self):
        binding_schema = json.loads((ROOT / 'ports/ir/schema/fx_bindings.schema.json').read_text())
        package_schema = json.loads((ROOT / 'ports/ir/schema/effects.schema.json').read_text())
        jsonschema.validate(self.bindings, binding_schema)
        subactions = [s['subaction'] for s in self.bindings['states']]
        self.assertEqual(len(subactions), len(set(subactions)), 'duplicate Melee subaction binding')
        packages = sorted(OUT.glob('*.gfx.json'))
        self.assertEqual(len(packages), 113)
        for path in packages:
            package = json.loads(path.read_text())
            jsonschema.validate(package, package_schema)
            for asset in package['textures'] + package['meshes']:
                self.assertTrue((OUT / asset['file']).exists(), (path.name, asset['file']))
            for emitter in package['emitters']:
                if emitter['kind'] == 'mesh':
                    self.assertIsNotNone(emitter.get('mesh'), (path.name, emitter['name']))
        for state in self.bindings['states']:
            for call in state['calls']:
                self.assertTrue((OUT / (call['package'] + '.gfx.json')).exists())

    def assert_calls(self, state, expected):
        self.assertIn(state, self.states)
        actual = [(c['frame'], c['package'], c['bone'], c['offset'])
                  for c in self.states[state]['calls']]
        self.assertEqual(actual, expected)

    def test_jab_1(self):
        # effect/0x5b268858f__0xf9df84764.c:121, frame 8, haver + (0,0,0).
        self.assert_calls('Attack11', [(8, 'P_TrailKeybladeFlare', 'haver', [0, 0, 0])])

    def test_forward_smash(self):
        # effect/0x5b268858f__0xf2fdd9e6c.c:164,196, frame 14, haver + (0,0,0).
        # The frame-0 common flash at line 78 has no trail package and is census-only.
        self.assert_calls('AttackS4', [
            (14, 'P_TrailKeybladeFlare', 'haver', [0, 0, 0]),
            (14, 'P_TrailKeybladeLight', 'haver', [0, 0, 0]),
        ])

    def test_sonic_blade_dash(self):
        # effect/0x5b268858f__0x1059acd9d6.c:75,123,224: frames 1,2,9.
        # SonicAttack/Impact use rot-local offsets (0,-2,20)/(0,-2,23).
        # The state serves ground and air: each situation carries its own script's calls.
        for situation in ('ground', 'air'):
            actual = [(c['frame'], c['package'], c['bone'], c['offset'])
                      for c in self.states['SDash2']['calls'] if c.get('situation') == situation]
            self.assertEqual(actual, [
                (1, 'P_TrailKeybladeFlare', 'haver', [0, 0, 0]),
                (2, 'P_TrailSonicAttack', 'rot', [0, -2, 20]),
                (9, 'P_TrailSonicImpact', 'rot', [0, -2, 23]),
            ])

    def test_up_special(self):
        # effect/0x5b268858f__0x100c239a30.c:225, frame 6, haver + (0,0,0).
        # Other calls in the script name common-pool hashes; see effect_census.json.
        self.assert_calls('Hi', [(6, 'P_TrailKeybladeFlare', 'haver', [0, 0, 0])])

    def test_counter(self):
        # effect/0x5b268858f__0x1092406257.c:149,316,418: frames 2,8,8.
        # CounterAttack is top-local; KeybladeLight is haver + (0,5,0).
        self.assert_calls('LwAttack', [
            (2, 'P_TrailKeybladeFlare', 'haver', [0, 0, 0]),
            (8, 'P_TrailCounterAttack', 'top', [0, 0, 0]),
            (8, 'P_TrailKeybladeLight', 'haver', [0, 5, 0]),
        ])


if __name__ == '__main__':
    unittest.main()
