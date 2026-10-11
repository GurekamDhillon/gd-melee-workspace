"""Build the Goku remake candidate sheet from remake-candidates.json.

python ports/goku-xv2/tools/remake_sheet.py [--check]

Reads  ports/goku-xv2/remake-candidates.json  (hand-authored: slots, candidates, why, recommended pick)
       _build/goku-xv2/remake-previews/metrics.json  (tools/remake_preview.py; local, XV2-derived)
       ports/goku-xv2/fidelity.json (appendix: every Melee row and its current clip; optional)
Writes ports/goku-xv2/REMAKE-CANDIDATES.md (committed: clip NAMES, frame counts and measured numbers only)
       _build/goku-xv2/remake-previews/candidate-sheet.html (local: embeds the montage PNGs; never commit)
--check fails when a candidate clip is not in the clip library (names starting with '(' or ending '*' are notes).
"""
import argparse
import re
import shutil
import base64
import html
import json
import os
from pathlib import Path
import sys

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[1]
MAIN = Path(os.environ.get('GW_MAIN', ROOT))   # the checkout that holds _build and the git-ignored fidelity.json
PREV = MAIN / '_build/goku-xv2/remake-previews'
LIB = MAIN / '_build/goku-xv2/author-source/clip-library.json'
LAB_DATA = MAIN / '_build/goku-xv2/lab-data/geno-lab_lab'   # where the LAB's REMAKE page saves (tools/remake.ps1)
PICKS = PORT / 'remake-picks.json'
NOTES = PORT / 'remake-notes.json'
CLIP_NOTES = PORT / 'CLIP-NOTES.md'


def sync_lab():
    """Copy the LAB's picks and notes files next to the plan (committed: clip names, frame numbers and the owner's own words)."""
    for name, dst in (('remake-picks.json', PICKS), ('remake-notes.json', NOTES)):
        src = LAB_DATA / name
        if src.exists():
            shutil.copyfile(src, dst)
            print('synced', src, '->', dst)


def read_picks():
    """{slot number: {clip, in, out, browse}} from remake-picks.json (one object per line, as the LAB writes it)."""
    out = {}
    d = load(PICKS, None)
    for p in (d or {}).get('picks', []):
        out[p['n']] = p
    return out


def read_notes():
    d = load(NOTES, None)
    return {n['clip']: n['note'] for n in (d or {}).get('notes', []) if n.get('note')}


def write_clip_notes(notes):
    """Put the notes in the 'what it is' column of CLIP-NOTES.md (a note replaces that cell; rows without a note are untouched)."""
    if not CLIP_NOTES.exists() or not notes:
        return 0
    n, out = 0, []
    for ln in CLIP_NOTES.read_text(encoding='utf-8').splitlines():
        cells = [c.strip() for c in ln.strip().strip('|').split('|')]
        if len(cells) >= 7 and cells[0] in notes:
            cells[3] = notes[cells[0]].replace('|', '/')
            ln = '| ' + ' | '.join(cells) + ' |'
            n += 1
        out.append(ln)
    CLIP_NOTES.write_text(chr(10).join(out) + chr(10), encoding='utf-8')
    return n


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except OSError:
        return default


def metric_text(m):
    if not m:
        return 'no metrics'
    r, h, p = m['max_forward_reach'], m['max_height_above_pelvis'], m['fastest_effector']
    return '%df; reach %.1f %s f%d; high %.1f; fastest %s f%d' % (
        m['source_last'] - m['source_first'] + 1, r['value'], r['bone'].replace('b_', ''), r['frame'],
        h['value'], p['bone'].replace('b_', ''), p['frame'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--sync-picks', action='store_true', help="first copy the LAB's remake-picks.json / remake-notes.json here and fold the notes into CLIP-NOTES.md")
    a = ap.parse_args()
    if a.sync_picks:
        sync_lab()
        print('CLIP-NOTES rows updated:', write_clip_notes(read_notes()))
    picks, notes = read_picks(), read_notes()
    slots = json.loads((PORT / 'remake-candidates.json').read_text(encoding='utf-8'))
    metrics = (load(PREV / 'metrics.json', {}) or {}).get('clips', {})
    lib = {c['name'] for c in (load(LIB, {}) or {}).get('clips', [])}
    excl = load(PORT / 'remake-unclear.json', []) or []
    bad = []
    for s in slots:
        for g in s.get('gap_look', []):
            if lib and g not in lib:
                bad.append((s['slot'], g))
    for e in excl:
        if lib and e['clip'] not in lib:
            bad.append(('excluded', e['clip']))
    for i, s in enumerate(slots, 1):
        s['_n'] = i
        for c in s['candidates']:
            n = c['clip']
            if lib and not n.startswith('(') and not n.endswith('*') and n not in lib:
                bad.append((s['slot'], n))
    if bad:
        print('unknown clips:', bad)
        if a.check:
            return 1
    out = ['# Goku remake: candidate animation sheet', '',
           'Rebuilt 2026-10-11 from the OWNER own descriptions: `ROW-NOTES.md` (all 303 LAB rows) and `CLIP-NOTES.md` (the library clips covered so far).',
           'The earlier planner candidates were found unreliable and are gone. **Only clips the owner described are listed**; every candidate quotes the',
           'owner words and the LAB row it was described in. A clip marked "unclear", "terrible" or "looks wrong" is excluded (list at the end).',
           'A slot with no good described clip is a **GAP**, with the undescribed library clips most worth looking at next ("look next").',
           '',
           'Status: OK = a described clip fits; KEEP = engine default / designed animation stays; PARTIAL = part of the slot has a pick, part is a GAP;',
           'WEAK = only a fallback the owner rated poorly; GAP = nothing described fits. `rec` marks the recommended pick; write yours in `owner pick`.',
           'Animations only: hitboxes are authored by hand afterwards (REMAKE-PLAN.md section 1). Always floating is visual only (standing clips are',
           'acceptable). Clip names are XV2 library actions (`x` + source name). Metrics come from `tools/remake_preview.py` (local); montage PNGs are',
           'XV2-derived and never committed. Preview any clip in the LAB (REMAKE or CLIPS mode) or with `tools/clips.ps1 <clip>`.', '']
    htm = ['<!doctype html><meta charset="utf-8"><title>Goku remake candidates</title><style>body{font:14px system-ui;margin:16px;background:#fff;color:#111}'
           'table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:4px;vertical-align:top}img{max-width:420px;display:block}'
           '.rec{background:#eaffea}h2{margin-top:28px}.pick{min-width:110px}</style><h1>Goku remake: candidate animations</h1>']
    group = None
    seen = set()
    n_rows = 0
    for s in slots:
        if s['group'] != group:
            group = s['group']
            out += ['', '## ' + group, '', '| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |', '|---|---|---|---|---|---|']
            htm.append('<h2>%s</h2><table><tr><th>slot</th><th>current</th><th>candidates</th><th class=pick>owner pick</th></tr>' % html.escape(group))
        cand_md, cand_h = [], []
        for c in s['candidates']:
            n = c['clip']
            key = n if n.startswith('x') else None
            m = metrics.get(key) if key else None
            tag = ' **rec**' if n == s['recommended'] else ''
            tag += ' seen' if n in seen else ''
            cand_md.append('`%s`%s: %s%s%s' % (n, tag, c['why'], (' (' + metric_text(m) + ')') if m else '', (' **owner: ' + notes[n] + '**') if n in notes else ''))
            img = PREV / (n + '.png') if key else None
            if img and img.exists():
                b = base64.b64encode(img.read_bytes()).decode()
                im = '<img src="data:image/png;base64,%s">' % b
            else:
                im = ''
            cand_h.append('<div class="%s"><b>%s</b>%s<br>%s<br><small>%s</small>%s</div>' % (
                'rec' if n == s['recommended'] else '', html.escape(n), tag, html.escape(c['why']), html.escape(metric_text(m)), im))
        role = s['role'] + ('; combo: ' + s['combo_role'] if s['combo_role'] else '')
        pk = picks.get(s['_n'])
        pick_txt = ''
        if pk:
            pick_txt = '**%s**' % pk['clip']
            if pk.get('in') or pk.get('out'):
                pick_txt += ' f%s..f%s' % (pk.get('in') or 1, pk.get('out') or 'end')
            if pk.get('browse'):
                pick_txt += ' (not a candidate)'
        st = s.get('status', '')
        if s.get('gap_look'):
            cand_md.append('**look next** (undescribed): ' + ', '.join('`%s`' % g for g in s['gap_look']))
        if s.get('note'):
            cand_md.append('note: ' + s['note'])
        out.append('| %s | %s | %s | %s | %s | %s |' % (('**%s** ' % st if st else '') + s['slot'], s['rows'], s['current'], role, '<br>'.join(cand_md) or '(none)', pick_txt))
        htm.append('<tr><td>%s<br><small>%s</small></td><td>%s</td><td>%s</td><td class=pick>%s</td></tr>' % (
            html.escape(s['slot']), html.escape(s['rows']), html.escape(s['current']), ''.join(cand_h),
            html.escape(pick_txt.replace('**', ''))))
        n_rows += 1
    htm.append('</table>')
    out += ['', '## GAP and partial slots (nothing good described yet)', '', '| slot | status | look next (undescribed library clips) | why |', '|---|---|---|---|']
    for s in slots:
        if s.get('status') in ('GAP', 'PARTIAL', 'WEAK'):
            out.append('| %d %s | %s | %s | %s |' % (s['_n'], s['slot'], s['status'], ', '.join('`%s`' % g for g in s.get('gap_look', [])), s.get('note', '')))
    out += ['', '## Excluded: the owner called these unclear, terrible or wrong (second look wanted)', '', '| clip | owner | where |', '|---|---|---|']
    for e in excl:
        out.append('| `%s` | %s | %s |' % (e['clip'], e['owner'], e['rows']))
    fid = load(PORT / 'fidelity.json') or load(MAIN / 'ports/goku-xv2/fidelity.json')
    if fid:
        out += ['', '## Appendix: every Melee row and its current source clip (no row is silent)', '',
                '`decision` is filled by the owner: keep / pick (sheet slot above) / n/a. Rows of items, mounts and other fighters are carried as they are.', '',
                '| motion | row | status | current clip | decision |', '|---|---|---|---|---|']
        for r in fid['rows']:
            out.append('| %s | %s | %s | %s |  |' % (r['motion'], r['row'], r['status'], r.get('how') or r.get('source_clip') or '-'))
    (PORT / 'REMAKE-CANDIDATES.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
    if PREV.exists():
        (PREV / 'candidate-sheet.html').write_text(''.join(htm), encoding='utf-8')
    print('picks', len(picks), 'notes', len(notes), end=' ')
    print('slots', n_rows, 'appendix rows', len(fid['rows']) if fid else 0)
    return 0


if __name__ == '__main__':
    sys.exit(main())
