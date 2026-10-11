"""Write the LAB's REMAKE picker data: missions/remake-slots.txt (read by the LAB CLIPS page, category REMAKE).

python ports/goku-xv2/tools/remake_lab_data.py [--out DIR/missions/remake-slots.txt]

Reads ports/goku-xv2/remake-candidates.json (+ local metrics and clip library when present) and writes one tab-separated file:
  S <n> <group> <slot> <melee rows> <current text> <current clip guess> <role> <recommended> <combo role>
  K <candidate clip> <reason> <metrics>
  N <clip> <frames> <candidate for> <owner's note: the 'what it is' cell of CLIP-NOTES.md>   (every clip, in CLIP-NOTES order)
The default output is _build/goku-xv2/author-source/package/mods/geno-lab/missions/ (git-ignored). Clip names, reasons and measured numbers only.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[1]
MAIN = Path(os.environ.get('GW_MAIN', ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from remake_sheet import LIB, PREV, load, metric_text  # noqa: E402

DEFAULT_OUT = MAIN / '_build/goku-xv2/author-source/package/mods/geno-lab/missions/remake-slots.txt'


def guess_current(text, names):
    """The library clip a 'current' description names ('GOK_BAS_STAND_S (...)', 'BOOST_F_00 x0.55'), or ''."""
    m = re.search(r'[A-Z0-9]+_[A-Z0-9_]*[A-Z0-9]', text)
    if not m:
        return ''
    tok = m.group(0)
    if 'x' + tok in names:
        return 'x' + tok
    for n in sorted(names):
        if n.endswith('_' + tok) and n.startswith('x'):
            return n
    return ''


def role_text(s):
    """The role column, prefixed with the status of a slot that is not plain OK and followed by what to look at for a GAP."""
    st = s.get('status', '')
    r = ('[%s] ' % st if st in ('GAP', 'PARTIAL', 'WEAK', 'KEEP') else '') + s['role']
    if s.get('gap_look'):
        r += ' | look next (undescribed): ' + ', '.join(g[1:] for g in s['gap_look'])
    return r


def clean(s):
    return re.sub(r'[\t\r\n]+', ' ', str(s)).strip()


def clip_notes():
    """Rows of CLIP-NOTES.md: (clip, frames, candidate for, what it is)."""
    p = PORT / 'CLIP-NOTES.md'
    if not p.exists():
        p = MAIN / 'ports/goku-xv2/CLIP-NOTES.md'
    rows = []
    if p.exists():
        for ln in p.read_text(encoding='utf-8').splitlines():
            c = [x.strip() for x in ln.strip().strip('|').split('|')]
            if len(c) >= 7 and c[0].startswith('x'):
                rows.append((c[0], c[1], c[2], c[3]))
    return rows


def build():
    slots = json.loads((PORT / 'remake-candidates.json').read_text(encoding='utf-8'))
    metrics = (load(PREV / 'metrics.json', {}) or {}).get('clips', {})
    names = {c['name'] for c in (load(LIB, {}) or {}).get('clips', [])}
    out = []
    for i, s in enumerate(slots, 1):
        out.append('\t'.join(['S', str(i), clean(s['group']), clean(s['slot']), clean(s['rows']), clean(s['current']),
                              guess_current(s['current'], names), clean(role_text(s)), clean(s['recommended']), clean(s.get('combo_role', ''))]))
        for c in s['candidates']:
            n = c['clip']
            out.append('\t'.join(['K', clean(n), clean(c['why']), metric_text(metrics.get(n)) if n.startswith('x') else '']))
    for clip, frames, cand, what in clip_notes():
        out.append('\t'.join(['N', clean(clip), clean(frames), clean(cand), clean(what)]))
    return out, len(slots)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    a = ap.parse_args()
    lines, n = build()
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('slots', n, 'lines', len(lines), '->', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
