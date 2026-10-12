"""Build the Goku alpha test zip: the staged game exe plus the Goku mod, to drop over a 0.3.0-rc5 install.

    python tools/media/goku/make_goku_zip.py [--exe E:/.../melee-pc.exe] [--mods E:/.../combo-package/mods]
        [--out _build/goku-media/package/GokuAlpha-test.zip] [--label "alpha 2026-10-12"]

Contents (a drop-in, not a full install; the rc5 files it does not touch stay as they are):
  melee-pc.exe                    the staged build (the Goku mod needs its engine changes)
  mods/goku-xv2/                  the fighter (model, animations, scripts, effects, sounds), built from Xenoverse 2 data
  mods/geno-lab/                  the LAB package the fighter was built against (small; same id as rc5's, replaces it)
  GOKU-ALPHA-README.txt           install steps, controls, known issues
  MANIFEST.sha256                 sha256 of every file
mods/enabled.txt is NOT shipped (it would overwrite the player's own list): the README says to switch Goku on in the launcher's
Mods tab, or add the line goku-xv2. No disc images or disc-derived files are included (checked below). Goku is never committed
or put on GitHub: the zip lands under _build/goku-media (git-ignored) and is shared by a link the owner chooses.
"""
import argparse, hashlib, json, sys, zipfile
from pathlib import Path

MAIN = Path('E:/Projects/Melee Workspace')
README = """GOKU - ALPHA test build ({label})
=====================================

This is an alpha: hitboxes are still being hand-authored, balance is unfinished, some animations are rough, and bugs are
expected. Bug reports are the point of this build.

INSTALL (over GD's Melee 0.3.0-rc5)
  1. Close the game. Unzip this into your GD's Melee folder and say yes to replace melee-pc.exe and mods/geno-lab.
  2. Start GD Melee, open the Mods tab and make sure "goku-xv2" is ticked
     (or add a line "goku-xv2" to mods/enabled.txt).
  3. Pick Goku on the character select. You need your own Melee disc image as always; none is included.

Online: both players need this same build. TODO-CONFIRM online status of this build.

CONTROLS
  Light string      A, A, A, A, A (each hit must connect)
  Heavy             C-stick off a light hit: up = launcher, forward = finisher, down = down smash
  Kamehameha        B starts the charge, B again fires. Shield stores it.
  Dragon Rush       forward + B (then the Rush Combo if it hits)
  Flight            up + B, then A or the C-stick for a flight aerial
  Ki charge         hold down + B (ground or air)
  Ki blast          D-pad down (hold for a barrage)
  Dash kick         shield, then B (costs ki)
  Instant Transmission roll   shield + left or right
  The yellow ki bar fills with hits and charging and is spent by specials.

KNOWN ISSUES
  - Alpha balance and hitboxes: numbers will change
  - Some animations are rough
  - TODO-CONFIRM known issues from the owner's playtest

Report bugs in the Discord bugs channel: what you pressed, the stage, what you expected.
"""


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--exe', default=str(MAIN / '_build/agents/gokustage/melee-pc.exe'))
    ap.add_argument('--mods', default=str(MAIN / '_build/goku-media/final/mods'))   # tools/media/goku/assemble_package.py
    ap.add_argument('--out', default=str(MAIN / '_build/goku-media/package/GokuAlpha-test.zip'))
    ap.add_argument('--label', default='alpha 2026-10-12')
    a = ap.parse_args()
    exe, mods, out = Path(a.exe), Path(a.mods), Path(a.out)
    files = [(exe, 'melee-pc.exe')]
    for mod in ('goku-xv2', 'geno-lab'):
        root = mods / mod
        assert (root / 'mod.json').exists(), 'no mod.json in %s' % root
        for p in sorted(root.rglob('*')):
            if p.is_file():
                files.append((p, 'mods/%s/%s' % (mod, p.relative_to(root).as_posix())))
    bad = [n for _, n in files if n.lower().endswith(('.iso', '.gcm', '.ciso', '.rvz', '.nkit.iso'))]
    assert not bad, 'disc images in the package: %s' % bad
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest = []
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p, name in files:
            z.write(p, name)
            manifest.append('%s  %s' % (sha(p), name))
        z.writestr('GOKU-ALPHA-README.txt', README.format(label=a.label))
        z.writestr('MANIFEST.sha256', '\n'.join(manifest) + '\n')
    ver = {m: json.loads((mods / m / 'mod.json').read_text(encoding='utf-8')).get('version') for m in ('goku-xv2', 'geno-lab')}
    print('%s: %.1f MiB, %d files, mods %s, exe %s (%.1f MiB)' % (out, out.stat().st_size / 1048576, len(files) + 2, ver, exe.name, exe.stat().st_size / 1048576))
    if README.count('TODO-CONFIRM'):
        print('README still has TODO-CONFIRM lines: fill them in before the zip is shared')


if __name__ == '__main__':
    main()
