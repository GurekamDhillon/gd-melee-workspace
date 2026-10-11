"""Offline gameplay invariants; these do not claim a runtime play test."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

PORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT / 'tools'))
import strip_gameplay as SG

class Gameplay(unittest.TestCase):
    def module(self):
        path = PORT / 'tools/build.py'
        self.assertTrue(path.exists(), 'Gameplay build wrapper is missing')
        spec = importlib.util.spec_from_file_location('goku_gameplay_build', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_missing_parity_refuses(self):
        module = self.module()
        with self.assertRaisesRegex(ValueError, 'parity'):
            module.move_source({'parity': [], 'behavior': {'moves': []}}, 'jab')

    def test_raw_hitbox_word0_gets_the_role_joint(self):
        module = self.module()
        plan = {'roles': {'upper_leg.R': [5], 'lower_leg.R': [6]}}
        src = chr(10).join(['hitbox raw=@HITW0:UPLEG_R:0x2C800001@,0x00010000,0x00020003,0x00000000,0x00000000',
                            'hitbox raw=@HITW0:LEG_R:0x2C000001@,0x00040005,0x00060007,0x00000000,0x00000000']) + chr(10)
        out = module.bind(src, plan, 1)
        self.assertIn('0x2C802801,0x00010000', out)
        self.assertIn('0x2C003001,0x00040005', out)

    def test_dimension_scaling_preserves_capture_flags_and_authored_input(self):
        module = self.module()
        plan = {'roles':{'hand.L':[7],'translation':[2]}}
        source = ('hitbox slot=0 joint=@HAND_L@ damage=3 size=3.2 x=-1 y=2 z=0 angle=361 kbg=40 fkb=0 bkb=10\n'
                  'hitbox raw=@GRAB_WORD0@,0x01000080,0x02000200,0x12345678,0x0000008B\n')
        scaled = module.bind(source,plan,2)
        self.assertIn('size=6.4 x=-2 y=4 z=0 angle=361',scaled)
        self.assertIn('0x2C001000,0x02000100,0x04000400,0x12345678,0x0000008B',scaled)
        self.assertEqual(scaled,module.bind(source,plan,2))
        article = {'spawn':[12,10],'velocity':[3,0],'hitboxes':[{'size':3,'offset':[0,0,-3]}]}
        self.assertEqual(module.scale_articles([article],2)[0],
                         {'spawn':[24,20],'velocity':[3,0],'hitboxes':[{'size':6,'offset':[0,0,-6]}]})
        self.assertEqual(article['spawn'],[12,10])

    def test_move_coverage_and_charge(self):
        self.module()
        config = SG.load()
        self.assertEqual(set(config['specials']), {'n','s','hi','lw','air_n','air_s','air_hi','air_lw'})
        # 3 Kamehameha tiers + the charge orb (KameOrb) + the Super Kamehameha (KameSuper), added in the 2026-10-09 specials pass
        self.assertEqual({a['name'] for a in config['articles']}, {'KameTap','KameMid','KameFull','KameOrb','KameSuper'})
        self.assertEqual(config['lua']['state']['charge'], 'int')
        for state in config['states']:
            if state['name'] not in ('KameCharge', 'KiCharge') and not state['name'].startswith('KameStore'):  # both hold while the button is down (KiCharge added 2026-10-09)
                self.assertEqual(state['iasa'], 'interrupt')
        self.assertEqual(config['jumps']['max'], 2)

    def test_46_explicit_host_design_attributes(self):
        module = self.module()
        if not (PORT/'ir/goku.xv2.ir.json').exists():
            self.skipTest('local source IR not present')
        ir = json.loads((PORT/'ir/goku.xv2.ir.json').read_text())
        host = json.loads((PORT/'ir/host.melee.ir.json').read_text())
        attrs, evidence = module.attributes(ir, host)
        self.assertEqual(len(attrs), 46)
        self.assertEqual(set(attrs), {e['field'] for e in evidence})
        self.assertTrue(all(e['classification'] == 'destination design' for e in evidence))

    def test_rapid_flow_has_entry_and_finite_exit(self):
        config = SG.load()
        moves = {m['name']:m for m in config['moves']}
        self.assertEqual(moves['rapid_jab']['motions'],[48])
        for name in ('jab1','jab2'):
            self.assertIn('jab_rapid state=1',(PORT/moves[name]['script']).read_text())
        self.assertIn('CHG motion:48 ALWAYS ONCE',(PORT/moves['rapid_start']['script']).read_text())
        self.assertIn('CHG motion:49 ALWAYS ONCE',(PORT/moves['rapid_jab']['script']).read_text())
        self.assertIn('CHG auto ALWAYS ONCE',(PORT/moves['rapid_end']['script']).read_text())

    def test_remake_moves_carry_no_generated_hitbox(self):
        """Remake phase 1 (REMAKE-PLAN.md section 1): every move is HB-NONE (no hitbox word) or an owner-accepted HB-DESIGN; never generated."""
        import remake_hb
        config = SG.load()
        for section in ('moves', 'special_adaptations'):
            for m in config[section]:
                self.assertIn(m.get('hb'), ('HB-NONE', 'HB-SAMPLE', 'HB-DESIGN', 'HB-AUTHORED'), m['name'])
                text = (PORT / m['script']).read_text(encoding='utf-8')
                if m['hb'] == 'HB-NONE':
                    self.assertFalse(remake_hb.has_hitbox(text), m['name'] + ' is HB-NONE but its script has a hitbox')
                    self.assertEqual(m.get('windows'), [], m['name'])
                    for k in ('radius', 'role', 'offset'):
                        self.assertNotIn(k, m.get('design', {}), m['name'])
                elif m['hb'] == 'HB-DESIGN':
                    self.assertIn(Path(m['script']).stem, remake_hb.DESIGN, m['name'])

    def test_hitbox_flag_fields_default_to_the_plain_encoding(self):
        self.module()
        from tools.geno import script
        plain = script.assemble('hitbox slot=0 joint=3 damage=5 size=2 angle=45 kbg=80 bkb=20', [])
        flagged = script.assemble('hitbox slot=0 joint=3 damage=5 size=2 angle=45 kbg=80 bkb=20 clank=1 sfx_kind=2 sfx_severity=3', [])
        self.assertEqual(plain[:3], flagged[:3])
        self.assertEqual(plain[3] & 31, 0)
        self.assertEqual(flagged[3] & 31, 0b00010)
        self.assertEqual((flagged[4] >> 2 & 31, flagged[4] >> 7 & 7), (2, 3))
        with self.assertRaisesRegex(ValueError, 'outside'):
            script.assemble('hitbox clank=2', [])

    def test_stripped_gameplay_has_no_source_fields_and_keeps_design(self):
        full = {'moves': [{'name': 'jab1', 'motions': [44], 'windows': [[3, 2]], 'iasa': 18, 'source_variant': 0,
                           'minimum_clip_frames': 20, 'timing': 'x', 'pose_review': 'y', 'source_candidate_windows': [[12, 4]],
                           'pick': {'bac': 1, 'clip': 'c', 'source_strike': 12},
                           'design': {'damage': 3, 'angle': 361, 'kbg': 50, 'bkb': 8, 'radius': 3.4, 'role': 'HAND_L'}}],
                'special_adaptations': [{'name': 'Rush', 'script': 'moves/rush.genoasm', 'minimum_clip_frames': 35}],
                'states': [{'name': 'Recovery', 'subaction': 300, 'pick': 'p', 'clip': 'Recovery', 'iasa': 'interrupt'}],
                'articles': [{'name': 'KameTap', 'hitboxes': [{'damage': 6}]}]}
        stripped = SG.strip(full)
        self.assertEqual(stripped['moves'][0], {'name': 'jab1', 'motions': [44], 'windows': [[3, 2]], 'iasa': 18,
                                                 'design': full['moves'][0]['design']})
        self.assertEqual(stripped['special_adaptations'], [{'name': 'Rush', 'script': 'moves/rush.genoasm'}])
        self.assertEqual(stripped['states'], [{'name': 'Recovery', 'subaction': 300, 'iasa': 'interrupt'}])
        self.assertEqual(stripped['articles'], full['articles'])
        self.assertIn('pick', full['moves'][0])            # the input is not modified
        self.assertEqual(SG.strip(stripped), stripped)       # idempotent

    def test_committed_gameplay_json_is_stripped(self):
        text = SG.STRIPPED.read_text(encoding='utf-8')
        committed = json.loads(text)
        self.assertEqual(SG.strip(committed), committed)
        for word in ('BAC', 'GOK_', 'Luigi', 'source_candidate_windows', 'pose_review', 'source_strike'):
            self.assertNotIn(word, text)
        if SG.FULL.exists():
            self.assertEqual(SG.dumps(SG.strip(json.loads(SG.FULL.read_text(encoding='utf-8')))), text,
                             'gameplay.json is stale: run tools/strip_gameplay.py')

    def test_stripped_gameplay_loads_for_the_move_tables(self):
        config = json.loads(SG.STRIPPED.read_text(encoding='utf-8'))
        for move in config['moves']:
            self.assertTrue((PORT / move['script']).exists(), move['script'])

if __name__ == '__main__':
    unittest.main()
