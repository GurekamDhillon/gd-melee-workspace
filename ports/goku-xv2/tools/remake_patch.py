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
KIBLAST_KI = 5                 # meter cost of one ki blast (XV2's is free; a spam-able projectile needs a cost, the owner asked for one)
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
    flight = [('Flight', 'FlightUp', {'enter': 'flight_enter', 'frame': 'flight_frame'}), ('FlightU', 'FlightUp', {'frame': 'flight_frame'}),
              ('FlightF', 'FlightF', {'frame': 'flight_frame'}), ('FlightB', 'FlightB', {'frame': 'flight_frame'})]
    for name, row, lua in flight:
        if not any(x['name'] == name for x in g['states']):
            g['states'].append({'name': name, 'behavior': 'geno.air', 'subaction': 'clip:' + row, 'like': 'motion:347', 'iasa': 'none', 'move_tag': 'special',
                                'lua': lua, 'pick': 'owner 2026-10-11: Up B is XV2-style flight (BUKUU clips), free steering, then the special fall'})
            changed = True
    if not any(x['name'] == 'Flight' for x in g['special_adaptations']):
        g['special_adaptations'].append({'name': 'Flight', 'parity': 'move:special_hi', 'script': 'moves/flight.genoasm', 'minimum_clip_frames': 30})
        changed = True
    if g['specials'].get('hi') != 'geno:Flight' or g['specials'].get('air_hi') != 'geno:Flight':
        g['specials']['hi'] = g['specials']['air_hi'] = 'geno:Flight'
        changed = True
    for slot in ('age', 'fly', 'pose'):
        if slot not in g['lua']['state']:
            g['lua']['state'][slot] = 'int'
            changed = True
    # phase 4: the aerials thrown out of the flight (Geno states sharing the aerials' rows' scripts) and the Instant Transmission rolls
    base = {'FlightNair': ('nair', 65), 'FlightFair': ('fair', 66), 'FlightBair': ('bair', 67), 'FlightUair': ('uair', 68), 'FlightDair': ('dair', 69)}
    moves = {m['name']: m for m in g['moves']}
    for name, (mv, motion) in base.items():
        if not any(x['name'] == name for x in g['states']):
            g['states'].append({'name': name, 'behavior': 'geno.air', 'subaction': 'clip:' + name, 'like': 'motion:%d' % motion, 'iasa': 'interrupt', 'move_tag': 'aerial',
                                'lua': {'frame': 'flightair_frame'}, 'pick': 'owner 2026-10-11: an aerial out of the flight; a hit keeps air control, a miss ends in the special fall'})
            changed = True
        for x in g['states']:
            if x['name'] == name and x.get('iasa') != 'interrupt':
                x['iasa'] = 'interrupt'   # the aerial scripts carry IASA commands
                changed = True
        want_ad = {'name': name, 'parity': moves[mv]['parity'], 'script': moves[mv]['script'], 'minimum_clip_frames': moves[mv].get('minimum_clip_frames', 30),
                   'hb': moves[mv].get('hb', 'HB-NONE'), 'windows': moves[mv].get('windows', [])}
        if moves[mv].get('strike'):
            want_ad['strike'] = moves[mv]['strike']
        old = next((x for x in g['special_adaptations'] if x['name'] == name), None)
        if old is None:
            g['special_adaptations'].append(want_ad)
            changed = True
        elif {k: old.get(k) for k in want_ad} != want_ad:
            old.update(want_ad)
            changed = True
    for name, motion, script_ in (('escape_f', 233, 'moves/escape_f.genoasm'), ('escape_b', 234, 'moves/escape_b.genoasm'), ('escape_n', 235, 'moves/escape_n.genoasm')):
        if name not in moves:
            g['moves'].append({'name': name, 'parity': 'move:special_lw', 'motions': [motion], 'tag': 'special', 'script': script_, 'windows': [], 'iasa': 30, 'hb': 'HB-NONE',
                               'design': {}, 'timing': 'owner 2026-10-11 phase 4: Instant Transmission roll, Mewtwo roll timing'})
            changed = True
    if 'kil' not in g['lua']['state']:
        g['lua']['state']['kil'] = 'float'
        changed = True
    want_controls = {'layouts': [{'name': 'A', 'buttons': {'A': 'A'}},
                                 {'name': 'B', 'buttons': {'Y': 'Down'}}]}
    if g.get('controls') != want_controls:
        g['controls'] = want_controls   # layout A = Melee buttons (Scheme A); layout B = X-only jump, Y = the blast input (D-pad Down) = KiBlast
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
    ground_idle = ['motion:%d' % m for m in (14, 15, 16, 17, 18, 20, 21, 23, 24, 39, 40, 41, 42)]   # Wait, Walk x3, Turn, Dash, Run, RunBrake, KneeBend, Squat x3, Landing
    want.append({'name': 'Blast>KiBlast', 'from': ground_idle, 'to': 'geno:KiBlast', 'input': 'blast', 'on': 'any', 'where': 'ground', 'window': [1, 0],
                 'ki_cost': KIBLAST_KI, 'priority': 5,
                 'source': 'XV2 Blast tap (ki blast, free in XV2); here it costs ki; input = layout B (Y -> D-pad Down) or the D-pad itself'})
    fly_from = ['geno:Flight', 'geno:FlightU', 'geno:FlightF', 'geno:FlightB']
    for dname, to in (('forward', 'geno:FlightFair'), ('back', 'geno:FlightBair'), ('up', 'geno:FlightUair'), ('down', 'geno:FlightDair')):
        want.append({'name': 'Fly>A %s' % dname, 'from': fly_from, 'to': to, 'input': 'light', 'dir': dname, 'on': 'any', 'where': 'air', 'window': [4, 0], 'priority': 12,
                     'source': 'owner 2026-10-11: A out of the flight with the stick direction = that aerial'})
        want.append({'name': 'Fly>C %s' % dname, 'from': fly_from, 'to': to, 'input': 'heavy', 'dir': dname, 'on': 'any', 'where': 'air', 'window': [4, 0], 'priority': 14,
                     'source': 'owner 2026-10-11: the C-stick out of the flight = that aerial'})
    want.append({'name': 'Fly>A nair', 'from': fly_from, 'to': 'geno:FlightNair', 'input': 'light', 'dir': 'any', 'on': 'any', 'where': 'air', 'window': [4, 0], 'priority': 10,
                 'source': 'owner 2026-10-11: A out of the flight, stick neutral = nair'})
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
