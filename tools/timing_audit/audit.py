#!/usr/bin/env python3
"""Actionability / animation-length audit: ported fighters vs the native roster.

    source .env; python tools/timing_audit/audit.py            # writes _build/timing-audit/*.json + actionability.md

Reads LOCALLY (nothing is committed, nothing disc-derived is written outside _build/):
  native  : each native Pl??.dat + Pl??AJ.dat on GW_ISO_VANILLA -> frames of every common motion row
            (build_melee_fighter.read_motions; 'frames' is the FigaTree end frame = the game's anim_end)
  goku    : plan.json of the built package (bank frames - 1 per row_clips[row]; rowlen_sync.py convention)
  mk/sora : the installed slot's Pl??.dat + Pl??AJ.dat (same reader as native)
and the decomp (ft/ftmotionstates.c) to classify each common state by what ENDS / RELEASES it:
  anim   : its Anim callback leaves the state when ftAnim_IsFramesRemaining() is false (clip length = state length)
  iasa   : its IASA callback is non-empty (inputs can cancel it before the clip ends)
  timer  : it ends on a frame counter / attribute (jump squat, hang timer, hitstun ...), clip length irrelevant
"""
import json, os, re, statistics, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/mex_port'))
sys.path.insert(0, str(ROOT / 'ports/ir/tools'))
import mex_hsd  # noqa: E402
import build_melee_fighter as B  # noqa: E402

GAME = Path(os.environ.get('GW_GAME', ROOT / 'worktrees/goku-polish'))
FT = GAME / 'src/melee/ft'
OUT = ROOT / '_build/timing-audit'
NATIVE = {'Ca': 'Falcon', 'Dk': 'DK', 'Dr': 'Doc', 'Fc': 'Falco', 'Fe': 'Roy', 'Fx': 'Fox', 'Gn': 'Ganon',
          'Gw': 'GnW', 'Kp': 'Bowser', 'Lg': 'Luigi', 'Lk': 'Link', 'Mr': 'Mario', 'Ms': 'Marth', 'Mt': 'Mewtwo',
          'Ns': 'Ness', 'Pc': 'Pichu', 'Pe': 'Peach', 'Pk': 'Pikachu', 'Pp': 'IceClimbers', 'Pr': 'Jigglypuff',
          'Sk': 'Sheik', 'Ss': 'Samus', 'Ys': 'Yoshi', 'Zd': 'Zelda', 'Cl': 'YLink'}   # Kirby (Kb) deliberately left out
PORTS = {
    'MetaKnight': (ROOT / 'ports/halberd/mods-slot/metaknight-slot/files', 'PlBm'),
    'Sora': (ROOT / '_build/agents/alpha/sora/mods/ultimate-trail-slot/files', 'PlUs'),
}
GOKU_PLAN = ROOT / '_build/goku-xv2/author-source/package/mods/goku-xv2/files/plan.json'


def common_names():
    text = (FT / 'kinds/ftCommon/forward.h').read_text(encoding='utf-8')
    blk = text[text.index('typedef enum ftCo_Submotion {'):]
    blk = blk[:blk.index('} ftCo_Submotion;')]
    return [n for n in re.findall(r'ftCo_SM_(\w+)', blk) if n not in ('None', 'Count')]


def classify():
    """state name -> {anim, iasa}, from ftmotionstates.c + the callbacks' bodies."""
    ms = (FT / 'ftmotionstates.c').read_text(encoding='utf-8')
    src = {}
    for p in FT.rglob('*.c'):
        src[p] = p.read_text(encoding='utf-8', errors='replace')
    allsrc = '\n'.join(src.values())

    def body(fn):
        m = re.search(r'\n(?:static\s+)?(?:bool|void|int)\s+' + re.escape(fn) + r'\s*\([^)]*\)\s*\{', allsrc)
        if not m:
            return None
        i, depth = m.end(), 1
        while depth and i < len(allsrc):
            depth += {'{': 1, '}': -1}.get(allsrc[i], 0)
            i += 1
        return allsrc[m.end():i - 1]

    out = {}
    for m in re.finditer(r'// ftCo_MS_(\w+) = (\d+)\s*\n\s*ftCo_SM_(\w+),\s*\n\s*\w+,\s*\n\s*[^\n]*\n\s*(\w+),\s*\n\s*(\w+),', ms):
        name, num, sm, anim, iasa = m.groups()
        ab, ib = body(anim), body(iasa)
        # follow one level of delegation (e.g. CliffAttack_Anim -> CliffClimb_Anim)
        d = re.fullmatch(r'\s*(\w+)\(gobj\);\s*', ab or '')
        if d and body(d.group(1)):
            ab = body(d.group(1))
        out[name] = {'ms': int(num), 'sm': sm, 'anim': bool(ab and 'IsFramesRemaining' in ab),
                     'iasa': bool(ib and ib.strip())}
    return out


def read_set(files, pl_code, names):
    pl = mex_hsd.Archive((files / f'{pl_code}.dat').read_bytes())
    aj = (files / f'{pl_code}AJ.dat').read_bytes()
    return {r['decomp']: r['frames'] for r in B.read_motions(pl, aj, names) if r['frames'] is not None}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = common_names()
    iso = os.environ['GW_ISO_VANILLA']
    disc = mex_hsd.Gcm(iso)
    native = {}
    for code, label in NATIVE.items():
        pl = mex_hsd.Archive(disc.read(f'Pl{code}.dat'))
        aj = disc.read(f'Pl{code}AJ.dat')
        native[label] = {r['decomp']: r['frames'] for r in B.read_motions(pl, aj, names) if r['frames'] is not None}
    ports = {}
    for label, (files, code) in PORTS.items():
        ports[label] = read_set(files, code, names)
    plan = json.loads(GOKU_PLAN.read_text(encoding='utf-8'))
    goku = {}
    for i, n in enumerate(names):
        c = plan['row_clips'][i] if i < len(plan['row_clips']) else None
        if c and plan['bank']['clips'][c]['frames']:
            goku[n] = float(plan['bank']['clips'][c]['frames'] - 1)
    ports['Goku'] = goku
    cls = classify()
    (OUT / 'data.json').write_text(json.dumps({'native': native, 'ports': ports, 'classes': cls}, indent=1), encoding='utf-8')
    print('native', len(native), 'rows/ea', len(next(iter(native.values()))), 'classified', len(cls),
          {k: len(v) for k, v in ports.items()})


if __name__ == '__main__':
    main()
