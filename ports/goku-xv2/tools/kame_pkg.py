"""Rebuild the Kamehameha viewing package in one go (local, git-ignored outputs):

    python ports/goku-xv2/tools/kame_pkg.py [--skip-audio] [--skip-fx]

gen_kame.py (move scripts) -> xv2_fx.py (effects) -> xv2_audio.py (clips) -> build.py --gameplay-only -> combo_apply.py
Result: _build/goku-xv2/combo-kame/mods (point MELEE_MODS_DIR / KAME_MODS at it). Needs GW_MELEE, GW_BUILD_ROOT and GW_FIGHTERBUILD
(ports/ir/tools/fighterbuild/bin/Release/net8.0/fighterbuild.dll in the main workspace) exported, like kame_run.py.
"""
import argparse, os, subprocess, sys
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
WT = PORT.parents[1]
T = PORT / 'tools'


def run(*a):
    print('>', ' '.join(str(x) for x in a), flush=True)
    subprocess.run([sys.executable, *map(str, a)], check=True, cwd=WT)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--skip-audio', action='store_true'); ap.add_argument('--skip-fx', action='store_true'); ap.add_argument('--probe', action='store_true', help='gen_kame.py --probe: zero-damage hitboxes on hand.R for tools/kame_ball.py (never ship)')
    a = ap.parse_args()
    if a.probe:
        os.environ['KAME_PROBE'] = '1'
    run(T / 'gen_kame.py', *(['--probe'] if a.probe else []))
    if not a.skip_fx:
        run(T / 'xv2_fx.py', *(['--probe'] if a.probe else []))
    if not a.skip_audio:
        run(T / 'xv2_audio.py')
    run(T / 'build.py', '--gameplay-only', '--no-audit', '--fighter', '_build/goku-xv2/author-source/fighter.json')
    run(PORT / 'combo/combo_apply.py', '--src', '_build/goku-xv2/author-source/package/mods', '--out', '_build/goku-xv2/combo-kame/mods')
    print('package:', WT / '_build/goku-xv2/combo-kame/mods')


if __name__ == '__main__':
    main()
