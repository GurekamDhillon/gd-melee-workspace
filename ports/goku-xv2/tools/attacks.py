"""Attack-feel pass (2026-10-08): provisional picks from XV2's own BCM/BAC data, built to Melee feel.

python ports/goku-xv2/tools/attacks.py   (then xv2_to_artist.py --build, or build.py when only scripts changed)
Writes moves/<move>.genoasm, updates gameplay.json (windows, IASA, design, pick) and tools/move-crops.json (the
clip crop that puts the XV2 strike pose on the Melee startup frame), and PICKS.md (the owner's review page).

Each move: the XV2 BAC entry it comes from (Goku's BCM: light string 300-304, heavy follow-ups, launcher, etc.),
the source strike frame (the limb's measured peak, the BAC hitbox event), a crop start so that strike lands on a
Melee startup frame, sweetspot + sourspot spheres on the striking limb, Melee-range knockback for a mid-weight
rushdown, a common Melee swing sound (166 small / 165 medium / 164 large), IASA and, for aerials, the landing-lag
flag window (auto-cancel outside it). Every number is a provisional design value; PICKS.md lists each for review.
"""
import json
import sys
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import strip_gameplay as SG
SCALE = 1.5  # build.py retargets hitbox sizes by the model scale: sizes here are final, written / 1.5
INV = {c['name']: i for i, c in enumerate(json.loads((PORT / 'ANIM-ROWS.json').read_text(encoding='utf-8'))['body_source_inventory'])}

# name: row, BAC, clip, source strike frame, crop start, startup, windows [(frame, dur, [(role, dmg, size, angle, bkb, kbg)])],
#       iasa, sfx, frames, aerial(landing flag window) or None, why
S = lambda role, dmg, size, angle, bkb, kbg: (role, dmg, size, angle, bkb, kbg)
MOVES = {
    'jab1': ('Attack11', 300, 'GOK_ATC_002', 12, 9, [(3, 2, [S('HAND_L', 3, 3.4, 361, 8, 50), S('ARM_L', 2, 2.6, 361, 8, 50)])],
             18, 166, 24, None, 'XV2 light 1 (BCM Light root -> BAC 300): left jab; strike f12 put on Melee f3'),
    'jab2': ('Attack12', 301, 'GOK_ATC_003', 5, 1, [(4, 2, [S('HAND_R', 3, 3.4, 361, 8, 50), S('ARM_R', 2, 2.6, 361, 8, 50)])],
             20, 166, 26, None, 'XV2 light 2 (BAC 301, Light after 300): right straight; peak f5 on f4'),
    'jab3': ('Attack13', 302, 'GOK_ATC_017', 12, 6, [(6, 3, [S('FOOT_L', 5, 4.0, 40, 30, 100), S('LEG_L', 4, 3.2, 40, 30, 100)])],
             30, 165, 34, None, 'XV2 light 3 (BAC 302): left kick ends the Melee jab; strike f12 on f6'),
    'dash_attack': ('AttackDash', 337, 'GOK_ATC_011', 21, 13, [(8, 3, [S('FOOT_R', 11, 4.2, 50, 40, 80), S('LEG_R', 9, 3.4, 50, 40, 80)]),
                                                                (11, 4, [S('FOOT_R', 7, 3.6, 361, 20, 70)])],
                    36, 165, 38, None, 'XV2 heavy string (BAC 337): flying side kick; clean f8-10, late f11-14'),
    'ftilt': ('AttackS3S', 475, 'GOK_ATC_008', 12, 5, [(7, 3, [S('FOOT_R', 10, 4.0, 361, 10, 100), S('LEG_R', 8, 3.0, 361, 10, 100)])],
              26, 165, 30, None, 'XV2 BAC 475 (his forward rush kick): forward kick at chest height; strike f12 on f7'),
    'utilt': ('AttackHi3', 310, 'GOK_ATC_013', 28, 20, [(8, 5, [S('HAND_R', 9, 4.0, 90, 30, 120), S('ARM_R', 7, 3.2, 95, 30, 110)])],
              28, 165, 30, None, 'XV2 heavy 1 (BAC 310): rising arm swing over the head; peak f28 on f8'),
    'dtilt': ('AttackLw3', 370, 'GOK_ATC_020_S', 17, 11, [(6, 4, [S('FOOT_R', 9, 3.6, 75, 25, 110), S('LEG_R', 7, 3.0, 80, 25, 100), S('FLOOR:2.4:7.5', 7, 3.4, 80, 25, 100)])],
              22, 165, 26, None, 'XV2 BAC 370 (low slide kick): low forward; peak f17 on f6, pops up'),
    'fsmash': ('AttackS4S', 343, 'GOK_ATC_006', 17, 5, [(12, 4, [S('HAND_R', 16, 4.4, 40, 30, 98), S('ARM_R', 13, 3.4, 40, 25, 95)])],
               42, 164, 46, None, 'XV2 light-string finisher (BAC 343: boost + lunging strike): hand +9.6 forward; peak f17 on f12'),
    'usmash': ('AttackHi4', 342, 'GOK_ATC_004', 17, 5, [(12, 5, [S('HAND_R', 16, 4.4, 85, 35, 100), S('ARM_R', 13, 3.4, 85, 30, 95)])],
               40, 164, 44, None, 'XV2 BAC 342 (light string 3: the uppercut, his launcher): over the head; peak f17 on f12'),
    'dsmash': ('AttackLw4', 341, 'GOK_ATC_012', 10, 2, [(8, 4, [S('FOOT_R', 14, 4.2, 30, 25, 95), S('HAND_L', 14, 4.2, 30, 25, 95), S('FLOOR:2.4:8', 11, 3.4, 30, 20, 90), S('FLOOR:2.4:-8', 11, 3.4, 30, 20, 90)])],
               38, 164, 42, None, 'XV2 BAC 341 (light string 2: split sweep): low both sides; peak f10 on f8'),
    'nair': ('AttackAirN', 312, 'GOK_ATC_007', 15, 9, [(6, 4, [S('FOOT_R', 12, 4.0, 361, 20, 100), S('FOOT_L', 10, 3.6, 361, 20, 100)]),
                                                       (10, 14, [S('FOOT_R', 8, 3.4, 361, 10, 100)])],
             40, 165, 44, (3, 26), 'XV2 heavy string 3 (BAC 312, first clip): split kick as a sex kick; clean f6-9, late f10-23'),
    'fair': ('AttackAirF', 320, 'GOK_ATC_007', 15, 5, [(10, 3, [S('FOOT_R', 13, 4.0, 50, 30, 100), S('LEG_R', 10, 3.0, 50, 25, 95)])],
             40, 165, 44, (7, 26), 'XV2 heavy finisher after LLLL (BAC 320): forward kick; peak f15 on f10 (a 44-frame row: not under 0.55x of Mario fair)'),
    'bair': ('AttackAirB', 335, 'GOK_ATC_010', 16, 10, [(6, 4, [S('HAND_L', 13, 4.0, 361, 10, 100), S('ARM_L', 10, 3.0, 361, 10, 100)])],
             30, 165, 34, (3, 20), 'XV2 heavy string 1 (BAC 335): backhand behind him; peak f16 on f6'),
    'uair': ('AttackAirHi', None, 'GOK_ATC_025', 14, 7, [(6, 8, [S('FOOT_L', 11, 6.0, 80, 25, 100), S('LEG_L', 8, 4.8, 80, 20, 100)])],
             30, 165, 34, (4, 22), 'XV2 ATC_025 (somersault kick; no Goku BCM node, library clip): straight up; peak f14 on f7. Combo retune 2026-10-09: active f6-13, spheres 6.0/4.8'),
    'dair': ('AttackAirLw', 312, 'GOK_ATC_007', 8, 2, [(6, 3, [S('FOOT_L', 14, 4.2, 270, 20, 90)]), (9, 6, [S('FOOT_L', 10, 3.6, 361, 15, 90)])],
             36, 164, 40, (4, 26), 'XV2 BAC 312 clip, leg straight down at f8: stomp; spike f6-8, late f9-14. No XV2 aerial stomp exists'),
}


def script(name, m):
    row, bac, clip, peak, start, wins, iasa, sfx, frames, air, why = m
    L = ['# PICK: provisional (attack-feel pass 2026-10-08). %s' % why,
         '# Source: %s clip %s, strike f%d; crop from f%d. Numbers are Melee design values, not XV2 data.' % (('BAC %d' % bac) if bac is not None else 'library', clip, peak, start),
         'PUT ANIM_RATE 1.0']
    first = wins[0][0]
    if air:
        L.append('wait_until %d' % air[0])
        L.append('cmd_var idx=0 value=1')
    L.append('wait_until %d' % max(1, first - 2))
    L.append('sfx behavior=1 sfx_id=%d volume=127 panning=64' % sfx)
    for f, d, spheres in wins:
        L.append('wait_until %d' % f)
        for slot, (role, dmg, size, angle, bkb, kbg) in enumerate(spheres):
            off = (0.0, 0.0, 0.0)
            if role.startswith('FLOOR'):  # floor reach (2026-10-09): a sphere on the floor-level root joint, y/z in Melee units in front of him
                _, fy, fz = role.split(':')
                role, off = 'FLOOR', (0.0, float(fy) / SCALE, float(fz) / SCALE)
            L.append('hitbox slot=%d joint=@%s@ damage=%d size=%.2f x=%.2f y=%.2f z=%.2f angle=%d kbg=%d fkb=0 bkb=%d' % (slot, role, dmg, size / SCALE, off[0], off[1], off[2], angle, kbg, bkb))
        L.append('wait %d' % d)
        L.append('clear_hitboxes')
    if air:
        L.append('wait_until %d' % air[1])
        L.append('cmd_var idx=0 value=0')
    return L


def main():
    gp = SG.load()
    crops = json.loads((PORT / 'tools/move-crops.json').read_text(encoding='utf-8'))
    by = {m['name']: m for m in gp['moves']}
    cross = {e['move'] for e in json.loads((PORT / 'tools/cross-port.json').read_text(encoding='utf-8')).values()}
    picks = []
    for name, m in MOVES.items():
        if name in cross:  # owned by tools/cross_port.py (a retail Melee action), not an XV2 pick
            continue
        row, bac, clip, peak, start, wins, iasa, sfx, frames, air, why = m
        old = (PORT / 'moves' / (name + '.genoasm')).read_text(encoding='utf-8') if (PORT / 'moves' / (name + '.genoasm')).exists() else ''
        keep = [l for l in old.splitlines() if l.strip().startswith(('jab_combo', 'jab_rapid'))]
        L = script(name, m)
        L += keep + ['wait_until %d' % iasa, 'iasa']
        (PORT / 'moves' / (name + '.genoasm')).write_text('\n'.join(L) + '\n', encoding='utf-8')
        g = by[name]
        if g.get('timing', '').startswith('BAC static') and 'source_candidate_windows' not in g:
            g['source_candidate_windows'] = g.get('windows')
        g['windows'] = [[f, d] for f, d, sp in wins for _ in sp]
        g['iasa'] = iasa
        g['minimum_clip_frames'] = min(frames, iasa + 2)
        top = wins[0][2][0]
        g['design'] = dict(g.get('design', {}), damage=top[1], angle=top[3], bkb=top[4], kbg=top[5], radius=top[2], role=top[0],
                           window_roles=[s[0] for f, d, sp in wins for s in sp])
        g['timing'] = 'destination design (attack-feel pass 2026-10-08): ' + why
        g['pick'] = {'status': 'provisional', 'bac': bac, 'clip': clip, 'source_strike': peak, 'crop_start': start,
                     'startup': wins[0][0], 'why': why}
        crops[row] = {'clip': INV[clip], 'start': start, 'frames': frames, 'move': name,
                      'note': 'PICK provisional (%s): %s' % (('BAC %d' % bac) if bac is not None else 'library', why)}
        picks.append((name, row, bac, clip, start, frames, wins, iasa, air, why))
    SG.save(gp)  # full file + regenerated stripped gameplay.json
    (PORT / 'tools/move-crops.json').write_text(json.dumps(crops, indent=2) + '\n', encoding='utf-8')
    write_picks(picks)
    print('attacks: %d moves' % len(picks))


SPECIALS = [
    ('Neutral B: Kamehameha', 'skill/SPA/000_GOK_KMH.bac 12', 'xGOK_SPA_KMH', 'f0-40 cup hands (charge), hold f47, fire f48-120',
     'XV2 Kamehameha (SuperSkill1); entry 12 is its charge-hold variant (40 -> hold 47 -> 48-120)', 'lab clips play skill/SPA/000_GOK_KMH/000_GOK_KMH.bac:12'),
    ('Neutral B at full ki: Super Kamehameha', 'skill/ULT/000_GOK_CKM.bac 0', 'xGOK_ULT_CKM_C', 'f0-30, 30-70, 70-225',
     'XV2 Super Kamehameha (UltimateSkill1)', 'lab clips play skill/ULT/000_GOK_CKM/000_GOK_CKM.bac:0'),
    ('Side B: Dragon Rush', 'GOK_PLAYER.bac 419', 'xGOK_BAS_BOOST_F_00 > xGOK_BAS_STEP_F_S > xGOK_ATC_013', 'boost f0-20, step f20-30, strike f40',
     'XV2 BAC 419, input Heavy+Blast: his rush into a strike (combo agent: heavy_rush)', 'lab clips play chara/GOK/GOK_PLAYER.bac:419'),
    ('Up B: Instant Transmission', 'skill/ESC/001_GOK_KUR.bac 0', 'xGOK_ESC_KUR_C', 'vanish f0-18, gone f18-70, reappear',
     'XV2 evasive skill 001_GOK_KUR (Instant Transmission); 8-direction teleport per the approved scheme', 'lab clips play skill/ESC/001_GOK_KUR/001_GOK_KUR.bac:0'),
    ('Down B tap: Z-vanish counter', 'skill/ESC/001_GOK_KUR.bac 1', 'xGOK_ESC_KUR_C', 'vanish f0-18 then reappear behind',
     'the same vanish, short: XV2\'s Z-vanish reads as this instant-transmission blink', 'lab clips show xGOK_ESC_KUR_C 10'),
    ('Down B hold: ki charge', 'skill/BLT/1080_CMN_POW.bac 11', 'xCMN_BLT_POW_C', 'f0-100 power-up pose (loop the middle)',
     'XV2 charge / power-up blast stance', 'lab clips play skill/BLT/1080_CMN_POW/1080_CMN_POW.bac:11'),
    ('Ki volley (string cancel)', 'skill/BLT/1080_CMN_POW.bac 0/1', 'xGOK_ATC_SHOT_N / xGOK_ATC_SHOT_F', 'f4-39',
     'XV2 basic ki blast (Blast); combo agent: ki_volley', 'lab clips play skill/BLT/1080_CMN_POW/1080_CMN_POW.bac:1'),
]


def write_picks(picks):
    L = ['# Goku move picks for review (provisional, 2026-10-08, specials updated 2026-10-09)', '',
         'Derived from XV2\'s own data: the BCM input tree of `chara/GOK/GOK_PLAYER.bcm` (light string BAC 300-304, heavy',
         'follow-ups by string position, the launcher, jump-chase 410/411) and the skill BACs. Mapped onto the approved scheme',
         '(A string, tilts as directional starters, C-stick/smash heavy enders, aerial strings, B specials). Approve or swap',
         'each line; to view one, open the LAB (`ports/goku-xv2/tools/clips.ps1`) and type the CLIPS command in the console',
         '(or pass the clip/move as the script\'s argument). Frame numbers are action frames (1 = the first).', '',
         '## Normals', '', '| input | Melee row | XV2 source | clip, crop | startup / active | IASA | why | view |', '|---|---|---|---|---|---|---|---|']
    for name, row, bac, clip, start, frames, wins, iasa, air, why in picks:
        act = ', '.join('f%d-%d' % (f, f + d - 1) for f, d, sp in wins)
        view = 'lab clips play chara/GOK/GOK_PLAYER.bac:%d' % bac if bac is not None else 'lab clips play x%s' % clip
        L.append('| %s | %s | %s | %s from f%d, %d frames | %s | %d%s | %s | `%s` |' % (
            name, row, ('BAC %d' % bac) if bac is not None else 'library', clip, start, frames, act, iasa,
            (', landing flag f%d-%d' % air) if air else '', why, view))
    L += [''] + (PORT / 'tools/picks-specials.md').read_text(encoding='utf-8').splitlines()  # maintained by hand (specials pass 2026-10-09)
    (PORT / 'PICKS.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
