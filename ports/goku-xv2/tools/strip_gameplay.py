"""Regenerate the committed, stripped gameplay.json from the full local gameplay.full.json.

    python ports/goku-xv2/tools/strip_gameplay.py            # gameplay.full.json -> gameplay.json
    python ports/goku-xv2/tools/strip_gameplay.py --check    # exit 1 if gameplay.json is not the stripped full file

gameplay.full.json is git-ignored and carries the source-game (XV2) measurement fields: candidate windows, picks, pose
reviews, BAC ids, clip names, strike frames, clip lengths and timing notes. gameplay.json is what is committed: the same
structure and the authored Melee design values (damage, angle, KBG/BKB, sizes, offsets, windows, IASA), without those fields.

The tools read the full file when it exists and fall back to the stripped one (`load()` / `path()` below), and tolerate the
stripped fields being absent. Tools that write gameplay data (attacks.py, cross_port.py) call `save()`, which writes the full
file and regenerates the stripped one in the same step.
"""
import argparse
import copy
import json
from pathlib import Path
import sys

PORT = Path(__file__).resolve().parents[1]
FULL = PORT / 'gameplay.full.json'
STRIPPED = PORT / 'gameplay.json'

# Keys removed at every depth of moves[] / special_adaptations[] / states[]. They are source-game derived: BAC ids and clip
# names (pick, clip), strike and crop frames, candidate windows, pose reviews, clip lengths measured from the source clip,
# the source variant index and the timing prose that quotes them.
STRIP_KEYS = ('source_candidate_windows', 'source_windows', 'pick', 'pose_review', 'timing', 'source_variant',
              'minimum_clip_frames', 'clip', 'bac', 'bcm', 'source_strike', 'crop_start')
SECTIONS = ('moves', 'special_adaptations', 'states')


def _clean(node):
    if isinstance(node, dict):
        return {k: _clean(v) for k, v in node.items() if k not in STRIP_KEYS}
    if isinstance(node, list):
        return [_clean(v) for v in node]
    return node


def strip(full):
    """Return a stripped deep copy of a full gameplay dict (the input is not modified)."""
    out = copy.deepcopy(full)
    for section in SECTIONS:
        if section in out:
            out[section] = _clean(out[section])
    return out


def dumps(data):
    return json.dumps(data, indent=2) + '\n'


def path():
    """The gameplay file the tools read: the full local one when present, else the committed stripped one."""
    return FULL if FULL.exists() else STRIPPED


def load():
    return json.loads(path().read_text(encoding='utf-8'))


def save(data):
    """Write gameplay data. With a full local file this updates it and regenerates the stripped one; without one
    it refuses, so source-derived fields are never written into the committed file."""
    if not FULL.exists():
        raise SystemExit('gameplay.full.json is missing: this tool needs the full local gameplay data '
                         '(the committed gameplay.json is stripped and must not be edited by hand-run tools)')
    FULL.write_text(dumps(data), encoding='utf-8')
    STRIPPED.write_text(dumps(strip(data)), encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true', help='verify gameplay.json equals the stripped gameplay.full.json')
    args = ap.parse_args(argv)
    if not FULL.exists():
        print('gameplay.full.json not found; nothing to strip (gameplay.json is already the committed stripped file)')
        return 1 if args.check else 0
    text = dumps(strip(json.loads(FULL.read_text(encoding='utf-8'))))
    if args.check:
        same = STRIPPED.exists() and STRIPPED.read_text(encoding='utf-8') == text
        print('gameplay.json is the stripped gameplay.full.json' if same else 'gameplay.json differs from the stripped gameplay.full.json')
        return 0 if same else 1
    STRIPPED.write_text(text, encoding='utf-8')
    print('wrote', STRIPPED)
    return 0


if __name__ == '__main__':
    sys.exit(main())
