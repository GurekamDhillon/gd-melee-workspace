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
    a = ap.parse_args()
    slots = json.loads((PORT / 'remake-candidates.json').read_text(encoding='utf-8'))
    metrics = (load(PREV / 'metrics.json', {}) or {}).get('clips', {})
    lib = {c['name'] for c in (load(LIB, {}) or {}).get('clips', [])}
    bad = []
    for s in slots:
        for c in s['candidates']:
            n = c['clip']
            if lib and not n.startswith('(') and not n.endswith('*') and n not in lib:
                bad.append((s['slot'], n))
    if bad:
        print('unknown clips:', bad)
        if a.check:
            return 1
    out = ['# Goku remake: candidate animation sheet', '',
           'One row per Melee slot. **Pick by animation merit only** (pose silhouette, feel, timing, direction, combo role); hitbox fit is not a',
           'criterion (hitboxes are authored by hand afterwards, see REMAKE-PLAN.md section 1). `rec` marks the recommended pick; write yours in',
           '`owner pick`. Clip names are XV2 library actions (`x` + source name), all present in `goku.blend`. "metrics" are measured by',
           '`tools/remake_preview.py` (frames; peak forward reach of a hand or foot from the pelvis, in model units; peak height above the pelvis;',
           'the fastest limb and its frame = the likely strike frame). Montage PNGs (6 frames, first to last, character faces right) are in',
           '`_build/goku-xv2/remake-previews/<clip>.png` and embedded in `candidate-sheet.html` (local only: XV2-derived).', '',
           'Preview any clip: LAB `& "ports\\goku-xv2\\tools\\clips.ps1" <clip>`; Blender: `tools/blender/geno_workbench/launch_goku.py`, assign the',
           'action; or the montage PNG. The recommendations below come from XV2 usage (which BAC/input plays the clip), clip length and the',
           'measured motion; **only a sample of montages was looked at by the planner (marked `seen`); the rest are for the owner to review.**', '']
    htm = ['<!doctype html><meta charset="utf-8"><title>Goku remake candidates</title><style>body{font:14px system-ui;margin:16px;background:#fff;color:#111}'
           'table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:4px;vertical-align:top}img{max-width:420px;display:block}'
           '.rec{background:#eaffea}h2{margin-top:28px}.pick{min-width:110px}</style><h1>Goku remake: candidate animations</h1>']
    group = None
    seen = {'xGOK_BAS_STAND_S', 'xGOK_BAS_BUKUU_F_S', 'xGOK_ATC_000', 'xGOK_ATC_001', 'xGOK_ATC_005', 'xGOK_ATC_007'}
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
            cand_md.append('`%s`%s: %s (%s)' % (n, tag, c['why'], metric_text(m)))
            img = PREV / (n + '.png') if key else None
            if img and img.exists():
                b = base64.b64encode(img.read_bytes()).decode()
                im = '<img src="data:image/png;base64,%s">' % b
            else:
                im = ''
            cand_h.append('<div class="%s"><b>%s</b>%s<br>%s<br><small>%s</small>%s</div>' % (
                'rec' if n == s['recommended'] else '', html.escape(n), tag, html.escape(c['why']), html.escape(metric_text(m)), im))
        role = s['role'] + ('; combo: ' + s['combo_role'] if s['combo_role'] else '')
        out.append('| %s | %s | %s | %s | %s |  |' % (s['slot'], s['rows'], s['current'], role, '<br>'.join(cand_md)))
        htm.append('<tr><td>%s<br><small>%s</small></td><td>%s</td><td>%s</td><td class=pick></td></tr>' % (
            html.escape(s['slot']), html.escape(s['rows']), html.escape(s['current']), ''.join(cand_h)))
        n_rows += 1
    htm.append('</table>')
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
    print('slots', n_rows, 'appendix rows', len(fid['rows']) if fid else 0)
    return 0


if __name__ == '__main__':
    sys.exit(main())
