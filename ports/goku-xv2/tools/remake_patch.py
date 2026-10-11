"""Idempotent data patch of the Goku remake, phase 1 (2026-10-11). Run after pulling the remake commits onto a checkout whose git-ignored
gameplay.full.json / combo/combo.json predate them:

    python ports/goku-xv2/tools/remake_patch.py

1. gameplay.full.json: the Homing state and move (Side B out of the shield), KiCharge's provenance note, then remake_hb.py strip (HB-NONE / HB-DESIGN),
   which also regenerates the committed gameplay.json.
2. combo/combo.json (git-ignored): hb marks, the shield route (Guard>Homing, stick neutral; the old Guard>Vanish is removed), the KiVolley clip from the picker's pick.
Both files are written only when something changed.
"""
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PORT = HERE.parent
sys.path.insert(0, str(HERE))
import strip_gameplay as SG  # noqa: E402
import remake_apply  # noqa: E402

GUARD_ON, GUARD = 178, 179     # motion numbers of GuardOn / Guard (ANIM-ROWS.json)
HOMING_KI = 20                 # meter cost of the homing strike (XV2: 100 stamina = 1 bar; Melee meter 0-100, Counter 10, Rush 15, Super 100): owner may retune


def patch_gameplay():
    g = json.loads(SG.FULL.read_text(encoding='utf-8'))
    changed = False
    if not any(s['name'] == 'Homing' for s in g['states']):
        g['states'].append({'name': 'Homing', 'behavior': 'geno.ground', 'subaction': 'clip:Homing', 'like': 'motion:345', 'phys': 'auto', 'coll': 'both',
                            'iasa': 'interrupt', 'move_tag': 'special', 'lua': {'enter': 'rush_enter', 'frame': 'rush_frame'},
                            'pick': 'owner, remake phase 1: XV2 homing dash strike (BAC 476, Guard+Heavy), Side B out of the shield'})
        changed = True
    if not any(s['name'] == 'Homing' for s in g['special_adaptations']):
        g['special_adaptations'].append({'name': 'Homing', 'parity': 'move:special_s', 'script': 'moves/homing.genoasm', 'minimum_clip_frames': 60})
        changed = True
    for s in g['states']:
        if s['name'] == 'KiCharge' and 'Energy Charge' not in s.get('pick', ''):
            s['pick'] = 'owner decision 2026-10-11: XV2 Energy Charge (skill 591) clip APL_SPA_KTN_C, looped while Down B is held; usable only while ki < 100'
            changed = True
    if changed:
        SG.save(g)
    return changed


def patch_combo():
    p = PORT / 'combo/combo.json'
    c = json.loads(p.read_text(encoding='utf-8'))
    routes = c['combo']['routes']
    changed = False
    want = [
        {'name': 'Guard>Homing', 'from': ['motion:%d' % GUARD_ON, 'motion:%d' % GUARD], 'to': 'geno:Homing', 'input': 'special', 'dir': 'neutral', 'on': 'any',
         'where': 'ground', 'window': [1, 0], 'ki_cost': HOMING_KI, 'priority': 20,
         'source': 'XV2 BAC 476 (Guard+Heavy, 100 stamina); owner 2026-10-11: shield + B with the stick neutral (so it never competes with roll / spot dodge), meter-costed'},
    ]
    if any(r['name'] == 'Guard>Vanish' for r in routes):   # owner 2026-10-11: shield + Down B was too hard to input; vanish is the Down B tap only
        routes[:] = [r for r in routes if r['name'] != 'Guard>Vanish']
        changed = True
    have = {r['name']: r for r in routes}
    for w in want:
        if have.get(w['name']) != w:
            routes[:] = [r for r in routes if r['name'] != w['name']] + [w]
            changed = True
    picks = remake_apply.load_picks()
    pk = picks.get(45)
    for s in c['states']:
        if s['name'] == 'KiVolley' and pk and s['clip'] != pk['clip']:
            s['clip'] = pk['clip']
            changed = True
    if not any(s['name'] == 'KiBlast' for s in c['states']):
        c['states'].append({'name': 'KiBlast', 'clip': 'xGOK_ATC_SHOT_N', 'script': 'moves/ki_blast.genoasm', 'like': 'motion:343', 'move_tag': 'special',
                            'bac': 0, 'bcm': 'design', 'hb': 'HB-DESIGN', 'why_hb': 'KiBlast article (single shot)'})
        changed = True
    if changed:
        p.write_text(json.dumps(c, indent=2) + '\n', encoding='utf-8')
    return changed


def main():
    a = patch_gameplay()
    b = patch_combo()
    rc = subprocess.run([sys.executable, str(HERE / 'remake_hb.py'), 'strip']).returncode
    print('gameplay patched' if a else 'gameplay already patched', '| combo patched' if b else '| combo already patched')
    return rc


if __name__ == '__main__':
    sys.exit(main())
