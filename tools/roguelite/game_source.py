"""The one place that resolves which game checkout the roguelite suite tests.

The suite was written on a machine whose game checkout sat at
``melee/worktrees/linux``, and 45 modules hardcoded that lane. They now resolve
every game-side path from here, so the same tests run against any checkout:

    GW_MELEE=/path/to/melee python3 -m unittest discover -s tools/roguelite

With GW_MELEE unset the default is ``<workspace>/melee``.

Importing this module raises :class:`GameSourceError` when the selected checkout
has no roguelite sources, so a wrong checkout fails immediately and says what to
do instead of surfacing as a hundred unrelated assertion errors. Tests that need
nothing from the game checkout should not import this module: they stay runnable
with no checkout at all.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class GameSourceError(RuntimeError):
    """The selected game checkout does not carry the roguelite sources."""


def _selected() -> tuple[Path, bool]:
    configured = os.environ.get('GW_MELEE')
    if configured:
        return Path(configured).expanduser().resolve(), True
    return (ROOT / 'melee').resolve(), False


GAME, FROM_ENV = _selected()

SCRIPTS = GAME / 'pc' / 'scripts'
ROGUELITE = SCRIPTS / 'examples' / 'roguelite'
CERTIFICATION = SCRIPTS / 'examples' / 'roguelite_certification'
PLATFORM = GAME / 'pc' / 'platform'
ASSETS_SRC = GAME / 'pc' / 'assets_src'

if not ROGUELITE.is_dir():
    _origin = f'GW_MELEE={GAME}' if FROM_ENV else f'the default {ROOT / "melee"}'
    raise GameSourceError(
        f'no roguelite sources at {ROGUELITE}\n'
        f'  selected: {_origin}\n'
        f'  fix: point GW_MELEE at the game checkout (branch pc-port), e.g.\n'
        f'       GW_MELEE=/path/to/melee python3 -m unittest discover -s tools/roguelite'
    )
