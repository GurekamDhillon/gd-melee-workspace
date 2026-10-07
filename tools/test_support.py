"""Explicit prerequisites shared by workspace tests (also usable by unittest)."""
import os
import re
import shutil
from pathlib import Path
from unittest import SkipTest

ROOT = Path(__file__).resolve().parents[1]
GAME = Path(os.environ.get('GW_MELEE') or ROOT / 'melee').expanduser().resolve()


def require_path(path, reason):
    path = Path(path)
    if not path.exists():
        raise SkipTest(reason)
    return path


def require_game(relative):
    return require_path(GAME / relative, f'requires game checkout (GW_MELEE or <root>/melee): {relative}')


def require_executable(*names):
    for name in names:
        executable = shutil.which(name)
        if executable:
            return executable
    raise SkipTest('requires executable on PATH: ' + ' or '.join(names))


def require_legacy_reentry():
    """Some old fixtures exercise re-entry without unloading the Lua director."""
    runtime = require_game('pc/scripts/examples/roguelite/main.lua').read_text(encoding='utf-8')
    if not re.search(r'gd\.tbd_request\s*\(', runtime):
        raise SkipTest('requires legacy gd.tbd_request director re-entry; removed in script API 2')
