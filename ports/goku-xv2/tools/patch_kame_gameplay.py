"""One-off (kept for the record): the Kamehameha rework's changes to gameplay.json / gameplay.full.json (lua slot, release-state Lua hooks)."""
import json, sys
from pathlib import Path
P = Path(__file__).resolve().parents[1]
for fn in ('gameplay.json', 'gameplay.full.json'):
    p = P / fn
    if not p.exists():
        continue
    g = json.loads(p.read_text(encoding='utf-8'))
    g['lua']['state'].setdefault('stored_pct', 'float')
    for st in g['states']:
        key = {'KameTap': 'tap', 'KameMid': 'mid', 'KameFull': 'full', 'KameSuper': 'super'}.get(st['name'])
        if key:
            st['lua'] = {'enter': key + '_enter', 'frame': key + '_frame'}
    p.write_text(json.dumps(g, indent=2, ensure_ascii=False), encoding='utf-8')
    print('patched', fn)
