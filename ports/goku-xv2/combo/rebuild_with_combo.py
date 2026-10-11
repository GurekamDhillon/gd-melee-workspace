"""The Creator's rebuild for Goku: the maintained build, then the combo layer on its output.

    python ports/goku-xv2/combo/rebuild_with_combo.py [build.py args...]

workbench.json points mods_dir at the COMBO package, so the game the Creator runs has the combo states (Light3..5, HeavyRush,
HeavyUp, HeavyFinish, KiVolley) that the combo strings step through. The maintained build writes author-source/package/mods
(14 states, no combo); combo_apply.py copies that into combo-package/mods and appends the combo states. Without this wrapper a
Creator rebuild would leave combo-package stale and a `geno:` string step would have no state to pose.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = HERE.parent
ROOT = PORT.parents[1]
BUILT = ROOT / '_build/goku-xv2/author-source/package/mods'


def run(argv):
    print('+', ' '.join(str(a) for a in argv), flush=True)
    code = subprocess.call([str(a) for a in argv], cwd=str(ROOT))
    if code:
        raise SystemExit(code)


def main(argv):
    run([sys.executable, PORT / 'tools/build.py', *argv])
    run([sys.executable, HERE / 'combo_apply.py', '--src', BUILT, '--out', ROOT / '_build/goku-xv2/combo-package/mods'])


if __name__ == '__main__':
    main(sys.argv[1:])
