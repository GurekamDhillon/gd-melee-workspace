"""Refresh row-lengths.json 'goku' from the built plan.json (bank frames - 1 = the game's anim_end).
Verified 2026-10-09: equal to the in-game measurement on 154 of 154 rows that were measured and not re-cropped since.
(The LAB anim_preview measurement script lua/measure_rows.lua hangs on its first preview; not used.)"""
import json
from pathlib import Path
PORT = Path(__file__).resolve().parents[1]
plan = json.loads((PORT.parents[1] / '_build/goku-xv2/author-source/package/mods/goku-xv2/files/plan.json').read_text(encoding='utf-8'))
p = PORT / 'row-lengths.json'
old = json.loads(p.read_text(encoding='utf-8'))
rc, bank, changed = plan['row_clips'], plan['bank']['clips'], []
for name, v in old.items():
    clip = rc[v['row']] if v['row'] < len(rc) else None
    if clip and bank[clip]['frames'] - 1 != v['goku']:
        v['goku'] = float(bank[clip]['frames'] - 1)
        v['basis'] = 'plan.json bank frames-1'
        changed.append(name)
p.write_text(json.dumps(old, indent=1), encoding='utf-8')
print(len(changed), 'rows updated', changed)
