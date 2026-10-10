#!/usr/bin/env python3
"""Side-by-side table from mobility_bench.lua run logs.  usage: mobility_table.py label=RUN_DIR [label=RUN_DIR ...]"""
import re, sys
from pathlib import Path

def parse(run):
    out = {}
    for line in Path(run, 'melee-pc.log').read_text(errors='replace').splitlines():
        m = re.search(r'\] MOB (\S+) (.*)$', line)
        if not m or m.group(1) in ('trace', 'DONE', 'FAIL', 'cpu_attrs', 'fighter=' ):
            continue
        key = m.group(1)
        rest = m.group(2)
        if key.startswith('fighter='):
            continue
        for kv in re.finditer(r'(\w[\w()=\-.]*?)=(-?[\d.]+|\w+)', rest):
            out[f'{key}.{kv.group(1)}'] = kv.group(2)
        if key == 'runturn':
            out['runturn.motions'] = rest.replace('motions ', '')
    return out

def main(argv):
    cols = [a.split('=', 1) for a in argv]
    data = {lab: parse(p) for lab, p in cols}
    keys = []
    for d in data.values():
        for k in d:
            if k not in keys:
                keys.append(k)
    w = max(len(k) for k in keys) + 1
    print('metric'.ljust(w) + ''.join(lab.rjust(12) for lab, _ in cols))
    for k in keys:
        print(k.ljust(w) + ''.join(str(data[lab].get(k, '-')).rjust(12) for lab, _ in cols))

if __name__ == '__main__':
    main(sys.argv[1:])
