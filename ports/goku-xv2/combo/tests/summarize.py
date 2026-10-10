"""Compact matrix of a results json: python summarize.py <name> [spec-substring] -> per spec, victim: pct:di -> true/links (drop) verdict."""
import json, sys, collections
from pathlib import Path
R = Path(__file__).resolve().parents[4] / '_build/goku-xv2/combo/results'
d = json.load(open(R / f'{sys.argv[1]}.json'))
flt = sys.argv[2] if len(sys.argv) > 2 else ''
agg = collections.OrderedDict()
for c in d['cells']:
    if flt in c['spec']:
        agg.setdefault(c['spec'], collections.OrderedDict()).setdefault(c['vs'], []).append(c)
for s, v in agg.items():
    print(s)
    for vs, l in v.items():
        print('  %-7s' % vs, ' '.join(f"{c['pct']}{c['di'][0]}:{c['true']}/{c['links']}h{c['hits']}{'' if c['verdict']=='PASS' else '!'}" for c in l))
