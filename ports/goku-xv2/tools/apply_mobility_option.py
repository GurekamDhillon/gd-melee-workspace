#!/usr/bin/env python3
"""Merge one option from proposals/mobility-options.json into gameplay.json `attributes` (and gameplay.full.json when present).
usage: apply_mobility_option.py a_falcon|a_falcon_pinned_only|b_fox|c_marth|none [--dir PORT_DIR]
Existing attribute overrides are kept; the option's keys win. `none` removes the mobility keys the options set."""
import json, sys
from pathlib import Path
port = Path(__file__).resolve().parents[1]
args = [a for a in sys.argv[1:]]
opt = args[0]
opts = json.loads((port/'proposals/mobility-options.json').read_text())
allkeys = set().union(*[set(v) for k, v in opts.items() if isinstance(v, dict)])
for name in ('gameplay.json', 'gameplay.full.json'):
    p = port/name
    if not p.is_file():
        continue
    g = json.loads(p.read_text())
    attrs = {k: v for k, v in g.get('attributes', {}).items() if k not in allkeys}
    if opt != 'none':
        attrs.update(opts[opt])
    if attrs:
        g['attributes'] = attrs
    else:
        g.pop('attributes', None)
    p.write_text(json.dumps(g, indent=2) + '\n')
    print(name, '->', opt, len(attrs), 'attribute overrides')
