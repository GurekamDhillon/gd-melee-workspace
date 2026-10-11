"""Run lua/kame_trace.lua for retail Samus, retail Mewtwo and Goku over the six charge scenarios and print them side by side.

    python ports/goku-xv2/tools/kame_traces.py [--scen tap,shield30,...]   -> _build/xv2-kame/traces/<scen>.txt (needs the same env as kame_run.py)
"""
import argparse, re, subprocess, sys
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
WT = PORT.parents[1]
WHO = {'samus': 'samus/hu', 'mewtwo': 'mewtwo/hu', 'goku': 'geno:goku-xv2/hu'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scen', default='tap,shield30,roll,jump,full,stored')
    ap.add_argument('--who', default='samus,mewtwo,goku')
    a = ap.parse_args()
    out = WT / '_build/xv2-kame/traces'; out.mkdir(parents=True, exist_ok=True)
    for sc_full in a.scen.split(','):
        sc, _, rest = sc_full.partition('@')
        at, _, key = rest.partition(':')
        extra = (['--cfg', 'at=' + at] if at else []) + (['--cfg', 'key=' + key] if key else [])
        sc_file = sc_full.replace('@', '_at').replace(':', '_')
        rows = {}
        for w in a.who.split(','):
            r = subprocess.run([sys.executable, str(PORT / 'tools/kame_run.py'), 'kame_trace', 'KTRACE', '--turbo', '--p1', WHO[w], '--name', f'ktrace-{w}-{sc_file}',
                                '--cfg', f'who={w}', '--cfg', f'scen={sc}'] + extra, capture_output=True, text=True)
            rows[w] = [l.split('KTRACE ', 1)[1] for l in (r.stdout + r.stderr).splitlines() if 'KTRACE ' in l and (' t=' in l or ' end:' in l or ' edge ' in l)]
        n = max(len(v) for v in rows.values())
        lines = ['== ' + sc_full] + ['%-44s | %-44s | %s' % tuple((rows.get(w, [''] * n)[i].split(' ', 2)[2] if i < len(rows.get(w, [])) else '') for w in ('samus', 'mewtwo', 'goku')) for i in range(n)]
        (out / (sc_file + '.txt')).write_text('\n'.join(lines), encoding='utf-8')
        print('\n'.join(lines))


if __name__ == '__main__':
    main()
