"""Fidelity ledger: every Melee animation row and every move, against the XV2 source.

python ports/goku-xv2/tools/fidelity.py   (after xv2_to_artist.py; reads ANIM-ROWS.json and gameplay.json)
  -> ports/goku-xv2/FIDELITY.md, ports/goku-xv2/fidelity.json

Status: SOURCE (an XV2 clip as-is), SPLICED (a hand-spliced recipe, splices.json, wired), SOURCE-RETIMED (an XV2 clip cropped/held/scaled to a Melee length; the
factor is given), CROSS-PORT (a retail Melee action retargeted onto Goku's rig; source and reason given), AUTHORED (no XV2 equivalent: why), PLACEHOLDER (plays another row's clip; counted at the top),
NONE (Melee plays no animation for it). Evidence names files the owner can open.
"""
import json
import sys
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import strip_gameplay as SG
ROOT = PORT.parents[1]
RUNS = '_build/agents/goku-polish/runs/'

# what was checked, by row (native runs and their logs; CLIPS; offline previews)
EVIDENCE = {
    **{r: [RUNS + 'gp-loco2/melee-pc.log (native: Turn, Dash, Run, RunBrake, TurnRun, Squat rows played)']
       for r in ('Turn', 'TurnRun', 'Dash', 'RunBrake', 'Squat', 'SquatWait', 'SquatRv')},
    **{r: [RUNS + 'gp-ledge6-fd/melee-pc.log, gp-ledge6-bf/melee-pc.log (native: FD and Battlefield, both sides, every ledge option; Mario reference gp-ledge6-mario)']
       for r in ('CliffCatch', 'CliffWait', 'CliffClimbQuick', 'CliffClimbSlow', 'CliffAttackQuick', 'CliffAttackSlow',
                 'CliffEscapeQuick', 'CliffEscapeSlow', 'CliffJumpQuick1', 'CliffJumpQuick2', 'CliffJumpSlow1', 'CliffJumpSlow2')},
}
DEVIATION = {
    'Turn': 'XV2 has no turn (characters always face the target): Wait pose with an authored 180-degree yaw.',
    'TurnRun': 'No XV2 run-turn: BOOST_F_02 skid with an authored 180-degree yaw.',
    'CliffCatch': 'XV2 has no ledges: BAS_JUMP_BACK_00 f12 (arms overhead) leaned 40 degrees, TransN hang offset authored.',
    'Entry': 'Kept long on purpose: the XV2 intro GOK_DEM_START is 210 frames (Melee entries are about 10). Flagged, owner to decide a crop.',
    'CliffWait': 'XV2 has no ledges: held overhead hang (as CliffCatch).',
}


def cross_note(cp):
    """The ledger text of a cross-port row: why, and what the retarget does not carry (from the tool's own report)."""
    nc = cp.get('not_carried', {})
    worst = max(cp.get('end_effector_error_max', {'-': 0}).values())
    sj = Path(__file__).resolve().parents[3] / '_build/goku-xv2/cross-port' / cp.get('row', cp['action']) / 'scale.json'
    carried = json.loads(sj.read_text()).get('bones', {}) if sj.exists() else {}
    cs = ('CARRIED (2026-10-09, artist bank scale tracks, fighter.json clips.scale_bones): bone scale on %s, peak x%.2f = the Luigi x1.8 thigh stretch at gain %.2f (DEVIATION: damped so the foot reaches about 13 behind, the scaled-Luigi reach; the full stretch gave 18 on his leg proportions; measured in game, lua/bair_reach.lua); ' % (
        ', '.join(sorted(carried)), max(max(b['values']) for b in carried.values()), next(iter(carried.values())).get('gain', 1.0))) if carried else ''
    return (('source: Melee %s %s (retail, vanilla disc), retargeted by bone role; reason: %s. ' + cs + 'Not carried: scale tracks on source joints %s '
            "(the other 8 source joints with scale keys have no counterpart role), translation tracks on non-hip joints %s, "
            'unnamed source joints %s, Goku fingers/thumbs (no source role). Worst end-effector offset from the scaled source %.2f units. '
            "Hitboxes: Luigi's spheres moved to Goku's bone of the same role, scaled x%.3f."
            ) % (cp['fighter'].capitalize(), cp['action'], cp['reason'], nc.get('scale_tracks'), nc.get('translation_tracks'),
               nc.get('rotation_tracks_unmapped'), worst, cp['ratio']))


def classify(r):
    s = r.get('source') or {}
    st = (s.get('status') or '') + ' ' + (r.get('status') or '')
    if r.get('status') == 'no-animation':
        return 'NONE', ''
    if s.get('splice') and s['splice'].get('wired'):
        sp = s['splice']
        return 'SPLICED', 'recipe %s, %d frames: %s' % (sp['name'], s.get('frames', 0), sp['summary'])
    if s.get('cross_port'):
        cp = s['cross_port']
        return 'CROSS-PORT', 'Melee %s %s, %d frames, size ratio %.3f' % (cp['fighter'].capitalize(), cp['action'], s.get('frames', 0), cp['ratio'])
    if r.get('status') == 'placeholder' or not s:
        return 'PLACEHOLDER', 'plays ' + str(r.get('clip'))
    if 'authored' in st.lower() and 'source crop' not in st.lower():
        return 'AUTHORED', s.get('status', '')
    factor = s.get('time_factor')
    held = s.get('hold_source') is not None
    if factor or held or s.get('start') or (s.get('frames') and s.get('frames') != s.get('source_frames')):
        bits = []
        if s.get('start'):
            bits.append('from f%d' % s['start'])
        if factor:
            bits.append('x%g speed' % factor)
        if held:
            bits.append('held at f%d' % s['hold_source'])
        bits.append('%d frames' % s.get('frames', 0))
        return 'SOURCE-RETIMED', ', '.join(bits)
    return 'SOURCE', ''


def main():
    rows = json.loads((PORT / 'ANIM-ROWS.json').read_text(encoding='utf-8'))['rows']
    lens = json.loads((PORT / 'row-lengths.json').read_text(encoding='utf-8')) if (PORT / 'row-lengths.json').exists() else {}
    game = SG.load()
    audit = json.loads((ROOT / '_build/goku-xv2/ground-audit.json').read_text(encoding='utf-8')) if (ROOT / '_build/goku-xv2/ground-audit.json').exists() else {}
    out_rows, counts = [], {}
    for r in rows:
        status, how = classify(r)
        s = r.get('source') or {}
        rec = {'row': r['row'], 'motion': r['motion'], 'status': status, 'clip': r.get('clip'),
               'source': s.get('source_name'), 'source_clip': s.get('clip'), 'how': how,
               'deviation': DEVIATION.get(r['row'], s.get('status', '') if status in ('AUTHORED', 'SOURCE-RETIMED', 'SPLICED') else
                                          (cross_note(s['cross_port']) if status == 'CROSS-PORT' else '')),
               'checked': EVIDENCE.get(r['row'], [])}
        gm = s.get('ground_mode')
        if gm:
            ga = audit.get('rows', {}).get(r['row'], {})
            rec['ground'] = {'mode': 'HOVER' if gm == 'HOVER' else 'ANCHORED', 'shift': s.get('ground_shift'), 'min_y': ga.get('min_y'),
                             'below_frames': ga.get('below_frames'), 'feet_up_frames': ga.get('feet_up_frames'), 'frames': ga.get('frames')}
            rec['deviation'] = (rec['deviation'] + ' ' if rec['deviation'] else '') + (
                '[HOVER: lowest point held %.1f above the floor]' % audit.get('hover_y', 2.0) if gm == 'HOVER' else
                '[ANCHORED: lowest point on the floor line, flight-stance pose kept]')
        ln = lens.get(r['row'])
        if ln:
            rec['frames'] = {'goku': ln['goku'], 'mario': ln['mario']}
            if (s.get('loop') or r.get('status') == 'own' and s.get('loop')):
                rec['frames']['note'] = 'loops: length free'
            elif ln['mario'] > 3 and ln['goku'] > 0 and not (0.55 <= ln['goku'] / ln['mario'] <= 1.7):
                rec['length_flag'] = 'length %d vs Mario %d' % (ln['goku'], ln['mario'])
        counts[status] = counts.get(status, 0) + 1
        out_rows.append(rec)
    moves = []
    for m in game['moves']:
        d = m.get('design', {})
        moves.append({'move': m['name'], 'motions': m['motions'], 'windows': m.get('windows'), 'iasa': m.get('iasa'),
                      'damage': d.get('damage'), 'angle': d.get('angle'), 'bkb': d.get('bkb'), 'kbg': d.get('kbg'),
                      'roles': d.get('window_roles'), 'timing': m.get('timing', ''), 'pose_review': m.get('pose_review', ''),
                      'source_windows': m.get('source_candidate_windows'),
                      'open_items': 'attack pass done (2026-10-08/09): limb spheres, sweet/sour spots, Melee swing sounds; hit sounds/effects are Melee defaults per element and damage; XV2 hit sparks/aura/trails: effects pass pending'})
    doc = {'schema': 'goku-fidelity/1', 'counts': counts, 'rows': out_rows, 'moves': moves}
    (PORT / 'fidelity.json').write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
    L = ['# Goku XV2 fidelity ledger', '',
         'Generated by `tools/fidelity.py` from ANIM-ROWS.json and gameplay.json. Every Melee animation row and every move, '
         'against the XV2 source. Status: SOURCE (XV2 clip as-is), SOURCE-RETIMED (cropped/held/scaled to Melee length), CROSS-PORT (a retail Melee action retargeted onto Goku; owner choice), '
         'SPLICED (segments of XV2 / cross-port clips joined by recipe, splices.json; wired recipes only), AUTHORED (no XV2 equivalent), PLACEHOLDER (plays another row\'s clip), NONE (Melee plays nothing).', '',
         '**Counts:** ' + ', '.join('%s %d' % (k, v) for k, v in sorted(counts.items())) + '  ',
         '**Placeholders a player can see: %d** (target 0).' % counts.get('PLACEHOLDER', 0), '',
         'Row lengths are measured in game (`row-lengths.json`, LAB anim_preview on Goku and Mario); a row more than 1.7x or under 0.55x of Mario is flagged.', '',
         '**Length flags: %d**' % sum(1 for r in out_rows if r.get('length_flag')), '',
         '**Ground audit** (`tools/ground_audit.py`, every frame of every ground row through the built bank): ' +
         ('%(rows)d rows, HOVER %(hover)d, ANCHORED %(anchor)d; **BELOW the floor: %(below_rows)d rows** (target 0, the build fails otherwise); hover rows off by more than the stride: %(hover_off_rows)d; %(ledge_rows_below)d ledge rows hang below the ledge by design.' % audit['counts'] if audit.get('counts') else 'not run.'),
         'Floating idle (owner #14, 2026-10-09): Wait, Rebirth and RebirthWait use GOK_BAS_STAND_S, the XV2 aerial ("_S" = sky) idle, SOURCE-RETIMED (the ground idle GOK_BAS_STAND is no longer used); Wait keeps the clip own 0.4-unit float bob under one constant lift (frame 0 at HOVER_Y 2.0, loop low 1.58). Turn, RunBrake, SquatRv, the ledge getups and every attack/catch/escape exit ease into that pose; Landing, GuardOff ease into it and GuardOn, Dash, Squat start from it. Walk, Run and crouch are unchanged. Alternates: STAND_00_S (clip 88), STAND_01_S (89), one constant `WAIT_CLIP`. '
         'Hybrid hover stance (owner, 2026-10-09): HOVER rows (idle, walk, run, dash, turn, shield, landing) keep the lowest point %.1f units above the floor; ANCHORED rows (attacks, grabs, throws, escapes, knockdown, ledge getups) keep the XV2 flight-stance pose with the lowest point on the floor line on their lowest frame; aerial rows are untouched. Punch-list pass (2026-10-09): ANCHORED rows that begin or end standing (ground attacks, catch/throw ends, escapes, ground landings, getups) are BLENDED at those ends: the lowest point starts/ends at the hover height and ramps (smoothstep, 6 frames) to the floor anchor, and exit poses ease into Wait (rows whose hitboxes end before the last 6 frames), so no row snaps between hover and floor; crouch (Squat, SquatWait, SquatRv) is now ANCHORED (grounded) and blends in/out at its ends. ECB (owner #7, landings that sank to the torso): the engine builds the ECB from six joints (head, shoulders, knees, hip) and his folded flight-stance aerials lifted them 5-8 units, so he touched down that far inside the floor (root y -8.3 measured); the hip slot of the ECB joint list is now TopN (plan-level, Goku only), keeping the ECB bottom at the root in every pose. ECB bottom in the air is therefore 0 (was knee height minus 2): he lands a few units earlier than a retail-layout ECB would. Lower hurtboxes (feet, shins) are 1.6 units fatter so low attacks still hit the hovering stance; dtilt and dsmash carry a floor-level sphere.' % audit.get('hover_y', 2.0), '',
         '## Animation rows', '', '| row | status | XV2 source | how | frames (Goku / Mario) | deviation | checked |', '|---|---|---|---|---|---|---|']
    for r in out_rows:
        fr = r.get('frames')
        L.append('| %s | %s | %s | %s | %s | %s | %s |' % (r['row'], r['status'], r['source'] or '-', r['how'] or '-',
            ('%d / %d%s' % (fr['goku'], fr['mario'], ' **FLAG**' if r.get('length_flag') else '')) if fr else '-',
            (r['deviation'] or '-').replace('|', '/'), '; '.join(r['checked']) or '-'))
    L += ['', '## Moves', '', '| move | windows | IASA | damage | angle | BKB/KBG | limbs | source windows | timing / pose | open |',
          '|---|---|---|---|---|---|---|---|---|---|']
    for m in moves:
        L.append('| %s | %s | %s | %s | %s | %s/%s | %s | %s | %s | %s |' % (
            m['move'], m['windows'], m['iasa'], m['damage'], m['angle'], m['bkb'], m['kbg'], m['roles'], m['source_windows'],
            (m['timing'] + ' ' + m['pose_review']).replace('|', '/'), m['open_items']))
    L += ['', '## Visual gaps (with plan)', '',
          '- Shading: engine toon ramp (bands, cool shadow tint, edge darkening). The XV2 DYT palettes were read (63 DYT textures, 128x128 DXT1; e.g. Bust left/right edge means (0.02,0.08,0.01) / (0.22,0.20,0.07)): they are dark per-material colour tables whose row/column meaning is not decoded, not a lighting tint, so `toon.shadow_tint` stays the designed cool tint. Open: decode the DYT line lookup.',
          '- Eyes/face: XV2 composes eyes from separate textures; the atlas carries a baked default. Open: bake the source eye layer into the atlas.',
          '- Select screen: icon 64x56, portrait 136x188 and stock icon 24x24 are rendered from his own converted model (tools/presentation_art.py: Kamehameha pose for the portrait, Wait for the head crops) and declared in `presentation`. On-screen look owed (needs a human at the character select).',
          '- Effects: original particle packages (ki aura, charge orb, three beams, vanish burst, dash streaks; tools/fx_build.py) are bound to states and articles. XV2 hit sparks are not bound (state-driven bindings cannot fire on a hit); hits use Melee element effects. Look owed on screen.',
          '- HUD: the ki meter exists in the combo engine (geno 11); drawing it in a match is engine work not done (see the report).',
          '- Hair/belt: rigid (no secondary motion). Plan: Geno dynamics bones if the engine path is cheap.',
          '- Outline: view-angle edge darkening, not an inverted hull.']
    (PORT / 'FIDELITY.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print(json.dumps(counts))


if __name__ == '__main__':
    main()
