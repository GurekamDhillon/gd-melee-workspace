"""Per-route table for the report / RESULTS.md: python route_table.py <name> -> one line per spec: per victim, at each percent, the DI cells that are TRUE (all links true and the intent taken), else the first drop link.
Cell code: T = true combo (all links true and at least min_hits hits), a number n = the string drops at link n (escapable), w = every link that happened was true but the next hit never landed (whiff), - = no link."""
import json, sys, collections
from pathlib import Path
R = Path(__file__).resolve().parents[4] / '_build/goku-xv2/combo/results'
SPECS = Path(__file__).resolve().parent / 'goku-combo-tests/missions/combo-specs'


def need(spec):
    kv = {}
    for line in (SPECS / f'{spec}.txt').read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    routes = [r for r in kv.get('routes', '').split(',') if r.strip()]
    return int(kv.get('min_hits', len(routes) + 1))

d = json.load(open(R / f'{sys.argv[1]}.json'))
NAMES = {'fox': 'Fox', 'captain': 'Falcon', 'purin': 'Puff', 'mars': 'Marth'}
spec = collections.OrderedDict()
for c in d['cells']:
    spec.setdefault(c['spec'], collections.OrderedDict()).setdefault(c['vs'], collections.OrderedDict()).setdefault(c['pct'], {})[c['di']] = c
lines = []
for s, vs in spec.items():
    lines.append(s)
    for v, pcts in vs.items():
        parts = []
        for p, dis in pcts.items():
            cell = []
            for di in ('none', 'in', 'out', 'survival'):
                c = dis.get(di)
                if not c:
                    continue
                ok = c['links'] > 0 and c['true'] == c['links']
                if ok and c['hits'] >= need(s):
                    cell.append('T')
                elif ok:
                    cell.append('w')  # every link that happened was true, but the next hit never landed (a whiff: the string ends short)
                else:
                    cell.append(c['drop'].replace('link', '') if c['drop'] != '-' else '-')
            parts.append(f"{p}%[" + ','.join(cell) + ']')
        lines.append(f"  {NAMES.get(v, v):7s} " + ' '.join(parts))
print('\n'.join(lines))
print('(DI order in each bracket: none, in, out, survival)')
