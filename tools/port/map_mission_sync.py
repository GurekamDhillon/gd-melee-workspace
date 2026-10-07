#!/usr/bin/env python3
"""Embed the map editor's mission.lua into main.lua (the engine loads one entry file per mod).

    python tools/port/map_mission_sync.py          # rewrite the generated block in main.lua
    python tools/port/map_mission_sync.py --check  # exit 1 if main.lua is stale

mission.lua stays the source of truth: it loads on its own under plain lua for the tests.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MELEE = Path(os.environ.get('GW_MELEE') or ROOT / 'melee').expanduser().resolve()
DIR = MELEE / 'pc/scripts/examples/map_editor/scripts'
BEGIN = '-- BEGIN GENERATED MISSION (scripts/mission.lua; regenerate with tools/port/map_mission_sync.py)\n'
END = '-- END GENERATED MISSION\n'


def block():
    return BEGIN + 'local Mission = (function()\n' + (DIR / 'mission.lua').read_text(encoding='utf-8') + 'end)()\n' + END


def main(argv):
    path = DIR / 'main.lua'
    text = path.read_text(encoding='utf-8')
    pattern = re.compile(r'-- BEGIN GENERATED MISSION[^\n]*\n.*?-- END GENERATED MISSION\n', re.S)
    if not pattern.search(text):
        sys.exit('main.lua has no generated mission block')
    if len(pattern.findall(text)) != 1:
        sys.exit('main.lua must have exactly one generated mission block')
    new = pattern.sub(lambda _: block(), text, count=1)
    if '--check' in argv:
        if new != text:
            sys.exit('main.lua embeds a stale mission.lua; run tools/port/map_mission_sync.py')
        return
    if new != text:
        path.write_bytes(new.encode('utf-8'))


if __name__ == '__main__':
    main(sys.argv[1:])
