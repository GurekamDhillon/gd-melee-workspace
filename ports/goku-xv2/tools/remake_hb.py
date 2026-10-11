"""Hitbox policy of the Goku remake (REMAKE-PLAN.md section 1): HB-NONE / HB-DESIGN / HB-AUTHORED, never a generated hitbox.

    python ports/goku-xv2/tools/remake_hb.py strip      one-time: remove the generated hitbox commands, mark every move
    python ports/goku-xv2/tools/remake_hb.py strikes    (after xv2_to_artist.py) record each HB-NONE move's strike window as timing metadata
    python ports/goku-xv2/tools/remake_hb.py check      the gate: scripts agree with the ledger, routes fit the moves; exit 1 on any failure

HB-NONE     animation + timing only; the script carries no hitbox word; `strike` = [[first, last], ...] Melee frames of the row where the XV2 strike lands
            (timing metadata for the Workbench marker and the route-window check, never a collider).
HB-DESIGN   a hitbox the owner accepted as designed (Kamehameha beam tiers, KiBlast article, the Counter answer): kept, named in DESIGN below.
HB-AUTHORED a hitbox the owner placed by hand in the Workbench: needs `authored: {by, date, commit}` on the move.
HB-SAMPLE   a generated STARTING POINT (tools/remake_samples.py), labelled as such in the script header and the ledger; the owner edits it in the Workbench.
HB-GENERATED never allowed here: the check fails.
"""
import json
import re
import sys
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import strip_gameplay as SG  # noqa: E402

HB_WORDS = ('hitbox', 'clear_hitbox', 'clear_hitboxes', 'hitboxes_clear', 'hbstun', 'hbflags', 'hbdmg', 'rehit')
DESIGN = {   # script stem (or combo state) -> why the owner accepted it
    'kame_charge': 'Kamehameha (charge state; owner-accepted design)', 'kame_tap': 'Kamehameha beam tier', 'kame_thin': 'Kamehameha beam tier',
    'kame_mid': 'Kamehameha beam tier', 'kame_full': 'Kamehameha beam tier', 'kame_max': 'Kamehameha beam tier', 'kame_super': 'Super Kamehameha',
    'counter': 'Counter window (state counter key; no sphere)', 'riposte': 'Counter answer (Z-vanish reappear kick, damage scaled from the hit taken)',
    'ki_volley': 'KiBlast articles (combo.json articles[0])', 'ki_blast': 'KiBlast article (single shot)',
}
HEADER = ('# HB-NONE (remake phase 1, 2026-10-11): the generated hitboxes were removed on purpose; animation, sound, movement and timing stay.\n'
          '# The owner authors this move\'s hitbox by hand in the Workbench; its strike window is gameplay.json "strike" (timing metadata only).\n')


def words_of(text):
    return [ln.split(None, 1)[0].lower() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith('#')]


def has_hitbox(text):
    return any(w in HB_WORDS for w in words_of(text))


def strip_text(text):
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if s and not s.startswith('#') and s.split(None, 1)[0].lower() in HB_WORDS:
            continue
        out.append(ln)
    if not text.startswith('# HB-NONE'):
        out = HEADER.rstrip('\n').split('\n') + out
    return '\n'.join(out).rstrip('\n') + '\n'


def read(p):
    return Path(p).read_text(encoding='utf-8')


def write(p, text):
    Path(p).write_text(text, encoding='utf-8', newline='\n')


def hb_of(stem):
    return 'HB-DESIGN' if stem in DESIGN else 'HB-NONE'


def combo_path():
    return PORT / 'combo/combo.json'


def cmd_strip():
    g = json.loads(SG.FULL.read_text(encoding='utf-8'))
    n_files = 0
    for section in ('moves', 'special_adaptations'):
        for m in g[section]:
            stem = Path(m['script']).stem
            if m.get('hb') in ('HB-SAMPLE', 'HB-AUTHORED'):
                continue   # already past HB-NONE: never strip it again
            m['hb'] = hb_of(stem)
            if m['hb'] == 'HB-NONE':
                p = PORT / m['script']
                t = read(p)
                if has_hitbox(t) or not t.startswith('# HB-NONE'):
                    write(p, strip_text(t))
                    n_files += 1
                m['windows'] = []
                if 'design' in m:
                    for k in ('radius', 'role', 'offset', 'window_roles'):
                        m['design'].pop(k, None)
            else:
                m['why_hb'] = DESIGN[stem]
    SG.save(g)
    c = json.loads(combo_path().read_text(encoding='utf-8'))
    for s in c['states']:
        stem = Path(s['script']).stem
        if s.get('hb') in ('HB-SAMPLE', 'HB-AUTHORED'):
            continue
        s['hb'] = hb_of(stem)
        if s['hb'] == 'HB-NONE':
            p = PORT / 'combo' / s['script']
            t = read(p)
            if has_hitbox(t) or not t.startswith('# HB-NONE'):
                write(p, strip_text(t))
                n_files += 1
        else:
            s['why_hb'] = DESIGN[stem]
    combo_path().write_text(json.dumps(c, indent=2) + '\n', encoding='utf-8')
    print('stripped', n_files, 'scripts; gameplay.json regenerated')
    return 0


def movemap():
    p = ROOT / '_build/goku-xv2/movemap/movemap.json'
    if not p.exists():
        p = ROOT.parent.parent / '_build/goku-xv2/movemap/movemap.json' if (ROOT.parent.name == 'worktrees') else p
    return json.loads(p.read_text(encoding='utf-8'))['moves']


def strike_frames(rowinfo, bac_hint, moves):
    """Melee-frame strike windows of a row: the movemap's BAC hits that land while the row's clip plays (bac_hint first), mapped through start / time_factor."""
    clip, start = rowinfo.get('source_name'), rowinfo.get('start') or 0
    tf = rowinfo.get('time_factor') or 1.0
    frames = rowinfo.get('frames') or 0
    if not clip or rowinfo.get('hold_source') is not None:
        return None
    best = None
    for m in moves:
        bac = int(m['id'].rsplit('/', 1)[1]) if m['id'].startswith('subaction:chara/GOK/GOK_PLAYER.bac/') else None
        t = m['timeline']
        if not t.get('hit') or not any(a['clip_name'] == clip for a in t['anim']):
            continue
        wins = []
        for h in t['hit']:
            seg = [a for a in t['anim'] if a['frame'] <= h['frame']]
            seg = seg[-1] if seg else None
            if not seg or seg['clip_name'] != clip:
                continue
            cf = seg['start'] + (h['frame'] - seg['frame']) * seg['speed']
            a = (cf - start) / tf
            b = (cf + max(h.get('dur') or 1, 1) - start) / tf
            if b < 0 or a > frames:
                continue
            wins.append([max(0, int(round(a))), min(frames, int(round(b)))])
        if wins and (best is None or bac == bac_hint):
            best = wins
            if bac == bac_hint:
                break
    return best


STRIKE_OVERRIDE = {   # rows that chain several clips (events): the BAC's own hit frames, which are the row's frames 1:1
    'Homing': ([[33, 39]], 'XV2 homing-strike hit f33-38'),
    'Rush': ([[40, 44]], 'XV2 knockback-attack hit f40-43; NOTE the row is cropped to 40 frames, so the strike is past its end (row to be lengthened when the hitbox is authored)'),
}


def cmd_strikes():
    g = json.loads(SG.path().read_text(encoding='utf-8'))
    full = json.loads(SG.FULL.read_text(encoding='utf-8')) if SG.FULL.exists() else g
    rows = json.loads((PORT / 'ANIM-ROWS.json').read_text(encoding='utf-8'))['rows']
    by_motion = {r['motion']: r for r in rows if r.get('source')}
    by_name = {r['row']: r for r in rows if r.get('source')}
    moves = movemap()
    out = {}
    for m in full['moves']:
        if m.get('hb') != 'HB-NONE':
            continue
        r = by_motion.get(m['motions'][0])
        hint = (m.get('pick') or {}).get('bac')
        out[m['name']] = strike_frames(r['source'], hint, moves) if r else None
    for m in full['special_adaptations']:
        if m.get('hb') != 'HB-NONE':
            continue
        r = by_name.get(m['name'])
        hint = (m.get('pick') or {}).get('bac')
        out[m['name']] = strike_frames(r['source'], hint, moves) if r else None
    for k, (w, _) in STRIKE_OVERRIDE.items():
        if k in {x['name'] for x in full['special_adaptations']}:
            out[k] = w
    for key in ('moves', 'special_adaptations'):
        for m in full[key]:
            if m['name'] in out:
                m['strike'] = out[m['name']] or []
                m['strike_note'] = STRIKE_OVERRIDE[m['name']][1] if m['name'] in STRIKE_OVERRIDE else 'XV2 strike frames mapped to this row\'s Melee frames' if out[m['name']] else 'no XV2 strike lands in this crop (or the row holds a pose): none recorded'
    SG.save(full)
    print('strike windows:', json.dumps(out))
    return 0


def cmd_check():
    problems = []
    g = json.loads(SG.path().read_text(encoding='utf-8'))
    counts = {}
    for section in ('moves', 'special_adaptations'):
        for m in g[section]:
            hb = m.get('hb')
            stem = Path(m['script']).stem
            text = read(PORT / m['script'])
            counts[hb] = counts.get(hb, 0) + 1
            if hb == 'HB-NONE':
                if has_hitbox(text):
                    problems.append('%s: ledger says HB-NONE but %s carries a hitbox word' % (m['name'], m['script']))
                if m.get('windows'):
                    problems.append('%s: HB-NONE with windows %s' % (m['name'], m['windows']))
                d = m.get('design', {})
                for k in ('radius', 'role', 'offset'):
                    if k in d:
                        problems.append('%s: HB-NONE design still has %s' % (m['name'], k))
            elif hb == 'HB-SAMPLE':
                if not has_hitbox(text) or 'HB-SAMPLE' not in text[:200]:
                    problems.append('%s: HB-SAMPLE needs hitbox words and the HB-SAMPLE header in %s' % (m['name'], m['script']))
                if not m.get('windows'):
                    problems.append('%s: HB-SAMPLE without windows' % m['name'])
            elif hb == 'HB-DESIGN':
                if stem not in DESIGN:
                    problems.append('%s: HB-DESIGN but not in the accepted list' % m['name'])
            elif hb == 'HB-AUTHORED':
                if not m.get('authored'):
                    problems.append('%s: HB-AUTHORED without authored {by,date,commit}' % m['name'])
            else:
                problems.append('%s: hb is %r (HB-GENERATED or missing is not allowed)' % (m['name'], hb))
    c = json.loads(combo_path().read_text(encoding='utf-8'))
    for s in c['states']:
        counts['combo:' + str(s.get('hb'))] = counts.get('combo:' + str(s.get('hb')), 0) + 1
        text = read(PORT / 'combo' / s['script'])
        if s.get('hb') == 'HB-NONE' and has_hitbox(text):
            problems.append('combo state %s: HB-NONE but %s carries a hitbox word' % (s['name'], s['script']))
        if s.get('hb') == 'HB-SAMPLE' and not has_hitbox(text):
            problems.append('combo state %s: HB-SAMPLE without hitbox words' % s['name'])
        if s.get('hb') not in ('HB-NONE', 'HB-SAMPLE', 'HB-DESIGN', 'HB-AUTHORED'):
            problems.append('combo state %s: hb is %r' % (s['name'], s.get('hb')))
    # routes: source / target exist, the window opens inside the move's row
    names = {m['name'] for m in g['moves']} | {s['name'] for s in c['states']} | {s['name'] for s in g['states']} | {m['name'] for m in g['special_adaptations']}
    rows = json.loads((PORT / 'ANIM-ROWS.json').read_text(encoding='utf-8'))['rows'] if (PORT / 'ANIM-ROWS.json').exists() else []
    frames_of_motion = {r['motion']: (r.get('source') or {}).get('frames') for r in rows}
    motion_of = {m['name']: m['motions'][0] for m in g['moves']}
    n_routes = 0
    for r in c['combo']['routes']:
        n_routes += 1
        srcs = r['from'] if isinstance(r['from'], list) else [r['from']]
        for s in srcs:
            nm = s.split(':', 1)[1] if s.startswith('geno:') else s
            if not (s.startswith('motion:') or nm in names or nm == '*'):
                problems.append('route %s: source %s does not exist' % (r['name'], s))
            mot = motion_of.get(nm)
            fr = frames_of_motion.get(mot) if mot is not None else None
            if fr and r.get('window') and r['window'][0] >= fr:
                problems.append('route %s: window %s opens after %s ends (%d frames)' % (r['name'], r['window'], nm, fr))
    print('hb counts', json.dumps(counts, sort_keys=True), '| routes', n_routes)
    for p in problems:
        print('FAIL', p)
    print('remake_check:', 'FAIL' if problems else 'ok')
    return 1 if problems else 0


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    sys.exit({'strip': cmd_strip, 'strikes': cmd_strikes, 'check': cmd_check}[cmd]())
