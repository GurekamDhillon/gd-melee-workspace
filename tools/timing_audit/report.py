#!/usr/bin/env python3
"""Render _build/timing-audit/actionability.md from data.json (written by audit.py)."""
import json, statistics as S
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_build/timing-audit'
d = json.loads((OUT / 'data.json').read_text())
nat, ports, cls = d['native'], d['ports'], d['classes']
FIGHTERS = ['Goku', 'MetaKnight', 'Sora']
MOVE_PREFIX = ('Attack', 'Special', 'Appeal', 'Entry', 'Throw', 'Thrown', 'Catch', 'Rebirth', 'Kinoko', 'Ottotto',
               'Wait', 'Walk', 'Run', 'Fall', 'Jump', 'Dead', 'Sleep', 'Swim', 'Ladder', 'Capture', 'Final', 'Taro',
               'Heavy', 'Item', 'Lift', 'Lightthrow', 'Light', 'Swing', 'Fire', 'Shoot', 'Beam', 'Hammer', 'Screw', 'Photo',
               'Barrel', 'Cargo', 'Bury', 'Shoulder', 'Sleep', 'Stun', 'Down', 'Flag', 'Escape')
# states whose duration/actionability is the clip length (Anim callback) or a frame counter; movement/defence/ledge only
KEEP = None


def stats(name):
    v = sorted(x[name] for x in nat.values() if name in x)
    return (v[0], S.median(v), v[-1], len(v)) if len(v) >= 12 else None


# decomp-verified: duration set by an attribute and the clip is rate-scaled to it (ftCo_Landing*/LandingAir: rate=(len+0.1)/lag;
# Rebound, Run), or ended by a frame counter (Kneebend: jump_startup_time; CliffWait: hang timer)
RATE = ('Landing', 'LandingFallSpecial', 'LandingAirN', 'LandingAirF', 'LandingAirB', 'LandingAirHi', 'LandingAirLw', 'Rebound', 'ReboundStop')
TIMER = ('Kneebend', 'KneebendTurn', 'CliffWait', 'Guard')


def kind(n):
    if n in RATE:
        return 'RATE(attr)'
    if n in TIMER:
        return 'TIMER'
    c = cls.get(n)
    if not c:
        return 'other'
    if c['anim'] and not c['iasa']:
        return 'LOCK'     # leaves only when the clip ends; no input can cancel it
    if c['anim']:
        return 'anim+iasa'
    return 'iasa/timer'


rows = []
for n, c in cls.items():
    st = stats(n if n in nat['Mario'] else c['sm'])
    if not st:
        continue
    for f in FIGHTERS:
        v = ports[f].get(n)
        if v is None:
            continue
        lo, med, hi, k = st
        rows.append(dict(f=f, state=n, kind=kind(n), port=v, lo=lo, med=med, hi=hi,
                         over=v - hi, under=lo - v, ratio=v / med if med else 0))


def flag(r):
    if r['port'] > r['hi'] * 1.25 and r['over'] >= 3:
        return 'SLOW'
    if r['port'] < r['lo'] * 0.75 and r['under'] >= 3:
        return 'fast'
    return ''


for r in rows:
    r['flag'] = flag(r)
LOCK_FIRST = {'RATE(attr)': 4, 'TIMER': 4, 'LOCK': 0, 'anim+iasa': 1, 'iasa/timer': 2, 'other': 3}
L = ['# Actionability / animation-length audit', '',
     'Frames = FigaTree end frame (the game anim_end); port Goku = plan.json bank frames - 1. Native = 25 vanilla fighters (min/median/max); Kirby is excluded by owner request.',
     'Kind: **LOCK** = state ends only when the clip ends and has no IASA (the clip length IS the lockout); anim+iasa = ends at clip end but inputs can cancel earlier; RATE(attr)/TIMER = duration is an attribute or counter, the clip length is irrelevant to actionability; iasa/timer = ended by input/frame counter (clip length does not gate it; clip may still be what the player sees).',
     'Flag: SLOW = port > native max x1.25 and >= 3 frames over; fast = port < native min x0.75 and >= 3 frames under.', '']
for f in FIGHTERS:
    fr = [r for r in rows if r['f'] == f]
    lock = [r for r in fr if r['kind'] == 'LOCK']
    L += [f'## {f}', f'rows compared {len(fr)}; SLOW {sum(r["flag"]=="SLOW" for r in fr)} '
          f'(of which LOCK {sum(r["flag"]=="SLOW" and r["kind"]=="LOCK" for r in fr)}); fast {sum(r["flag"]=="fast" for r in fr)}; '
          f'LOCK rows {len(lock)}', '',
          'Worst SLOW rows (by frames over native max; LOCK first among ties above 5 frames):', '',
          '| state | kind | port | native min/med/max | over max |', '|---|---|---|---|---|']
    slow = sorted((r for r in fr if r['flag'] == 'SLOW'), key=lambda r: (-(r['over']), LOCK_FIRST[r['kind']]))
    for r in slow[:40]:
        L.append(f"| {r['state']} | {r['kind']} | {r['port']:g} | {r['lo']:g}/{r['med']:g}/{r['hi']:g} | +{r['over']:g} |")
    L.append('')
L += ['## Every ledge / defence / landing / getup state', '', '| state | kind | native min/med/max | Goku | MetaKnight | Sora |', '|---|---|---|---|---|---|']
SECTION = ('Cliff', 'Landing', 'Turn', 'Squat', 'Guard', 'Escape', 'Passive', 'Down', 'Ottotto', 'Wall', 'Stop', 'Rebound',
           'Dash', 'Run', 'Jump', 'Kneebend', 'Damage', 'Catch', 'Throw', 'Pass', 'Fall', 'Appeal')
seen = set()
for n in cls:
    st = stats(n if n in nat['Mario'] else cls[n]['sm'])
    if not st or not n.startswith(SECTION) or n in seen:
        continue
    seen.add(n)
    cells = []
    for f in FIGHTERS:
        v = ports[f].get(n)
        r = next((x for x in rows if x['f'] == f and x['state'] == n), None)
        cells.append('-' if v is None else f"{v:g}{' **' + r['flag'] + '**' if r and r['flag'] else ''}")
    L.append(f"| {n} | {kind(n)} | {st[0]:g}/{st[1]:g}/{st[2]:g} | " + ' | '.join(cells) + ' |')
(OUT / 'actionability.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
json.dump(rows, open(OUT / 'rows.json', 'w'))
print('rows', len(rows), {f: (sum(r['f'] == f and r['flag'] == 'SLOW' for r in rows), sum(r['f'] == f and r['flag'] == 'SLOW' and r['kind'] == 'LOCK' for r in rows)) for f in FIGHTERS})

# in-game ledge probe (tools/timing_audit/probe): logic frames from first CliffCatch frame to leaving CliffCatch/CliffWait with the
# input pulsed every other frame from that first frame (Goku/Falcon on FD in one match; MK and Sora each beside Falcon on the ACE disc)
extra = ['', '## In-game ledge probe (turbo, scripted pad; latency = frames from the first CliffCatch frame to the first action off the ledge)', '',
         '| fighter | CliffCatch length | earliest jump / attack / climb / roll / drop | Falcon in the same run |', '|---|---|---|---|',
         '| Goku | 6 | 7 / 7 / 7 / 7 / 7 | 7-9 |', '| Meta Knight | 20 | 21 / 21 / 21 / 21 / 21 | 7-9 |',
         '| Sora | 19 | 19-21 (jump 19, attack 19, climb 21, roll 19, drop 21) | 7-9 |', '',
         'Source: `LEDGE RESULT` lines in `_build/agents/goku-polish/runs/ledge2`, `ledge_mk`, `ledge_sora` `melee-pc.log`.']
with open(OUT / 'actionability.md', 'a', encoding='utf-8') as fh:
    fh.write('\n'.join(extra) + '\n')
