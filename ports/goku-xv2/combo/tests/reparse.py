"""Re-read a finished run's logs: python reparse.py <name> [victim,...] -> compact matrix (needs GW_BUILD_ROOT like the runner)."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_combo_tests as R
name = sys.argv[1]
vs = (sys.argv[2] if len(sys.argv) > 2 else 'fox').split(',')
root = Path(os.environ.get('GW_BUILD_ROOT') or R.ROOT / '_build')
for v in vs:
    text = (root / 'runs' / f'{name}-{v}' / 'melee-pc.log').read_text(encoding='utf-8', errors='replace')
    rows = {}
    for m in R.LINE.finditer(text):
        spec, vv, pct, di, hits, tr, links, gaps, drop, intent, taken, ki, expect, verdict = m.groups()
        rows.setdefault(spec, []).append(f"{pct}{di[0]}:{tr}/{links}h{hits}{'' if verdict == 'PASS' else '!'}")
    for spec, l in rows.items():
        print(v, spec, ' '.join(l))
