#!/usr/bin/env python3
"""mod_package.py - copy the release's mods into a staged package, by tools/release/mod_rules.json.

The Linux packager (tools/port/package_linux.py) uses this; it does what the mods block of
build_release.ps1 does for the Windows zip, by the same rules:

  * A file ships only if its path inside the mod matches one of the mod's 'allow' regexes (whole path,
    forward slashes) AND it is tracked in the melee repository (nothing git-ignored or local-only).
  * Any path segment matching 'deny_mod_ids' or named in 'deny_dirs_anywhere' is refused, loudly
    (envoy_drives_sa2, local-assets, the Sora/Kirby/Meta Knight ports, ACE/Akaneia packs ...).
  * Nothing from the disc-data folders, and no disc-data extension, is ever read.
  * 'optional' mods (the Courier, whose .dat files are built original art) are NOT packaged here; the
    Windows script does that behind -IncludeCourier and its build record, and the Linux package
    carries none.
  * Lua example scripts (pc/scripts/examples, minus 'examples_skip') go to scripts/examples/.

It writes mods/README.txt, mods/sources.txt, mods/enabled.txt and scripts/README.txt. check_release_linux.py
then enforces the same table on the result. Command line (a dry run into a folder):

    python3 tools/release/mod_package.py --melee <melee checkout> --dest <staged package folder>
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# Never read from these (relative to the workspace), whatever a caller asks for. Same list as build_release.ps1.
FORBIDDEN = ('_build/ace', '_build/packs', '_build/m-ex', '_build/hsd_export', '_build/card', '_build/card-ace',
             '_build/usa', 'akaneia-build', 'menu/meleedump', 'melee/orig', '_build/local-assets')
DISC_EXT = {'.iso', '.gcm', '.rvz', '.ciso', '.dol', '.dat', '.usd', '.gci'}

MODS_README = """Mods go in this folder, one folder per mod (mod.json + files/ and/or scripts/). Copy trusted mods
here manually. The launcher's Mods tab lists installed mods, enables or disables them, and moves
removed mods into a recoverable .removed folder. Remote installation and updates are not
implemented in this Qt launcher. sources.txt
is an example format for the separate mods-browser tools. The game loads every enabled mod,
online too: fighters and stages are matched with your opponent by their content.

Shipped with this release (enabled.txt lists the ones that are on):
  geno-lab       on   the LAB (SOLO > LAB)
  envoy          on   Envoy mode (needs envoy_drives for its drive models)
  envoy_drives   on   Envoy's original drive models
  vanilla-hero, vanilla-striker, vanilla-caster   off   Geno sample fighters (they use your own disc's
                      Mario files; turn one on in the Mods tab to try it; unreviewed looks and feel)
"""
SCRIPTS_README = """Lua scripts. Every scripts/<name>.lua and scripts/<id>/ (with a mod.json) here loads when the game
starts. examples/ is not loaded automatically: press ` in the game for the console and type
  load examples/state_overlay      (a frame-data overlay, F2 toggles)
  load examples/tm_lite            (F5/F6 save/load state, F9 reset percent)
The scripting reference: https://github.com/GurekamDhillon/gd-melee-workspace/blob/master/docs/scripting.md
"""


def load_rules(path=None):
    return json.loads((Path(path) if path else HERE / 'mod_rules.json').read_text(encoding='utf-8'))


def denied(rules, rel):
    """True when a path (or mod id) has a segment on the never-package list."""
    deny = re.compile(rules['deny_mod_ids'])
    low = {d.lower() for d in rules['deny_dirs_anywhere']}
    return any(deny.fullmatch(seg) or seg.lower() in low for seg in re.split(r'[\\/]', rel) if seg)


def allow_regex(mod):
    return re.compile('(?:' + '|'.join(f'(?:{a})' for a in mod['allow']) + ')')


def tracked_files(melee, source):
    """Paths under <source> that git tracks in the melee checkout, relative to <source>."""
    out = subprocess.run(['git', '-C', str(melee), 'ls-files', '--', source], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f'cannot list tracked files of {melee}: {out.stderr.strip()}')
    return {line[len(source) + 1:] for line in out.stdout.splitlines()}


def copy_in(src, dst, workspace=ROOT):
    full = Path(src).resolve()
    posix = full.as_posix().lower()
    for f in FORBIDDEN:
        if posix.startswith((Path(workspace).resolve() / f).as_posix().lower()):
            raise SystemExit(f'refusing to package {full}: it is under {f} (disc data or local-only)')
    if full.suffix.lower() in DISC_EXT:
        raise SystemExit(f'refusing to package {full}: disc data extension')
    if not full.is_file():
        raise SystemExit(f'missing: {full}')
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, dst)


def stage_mods(melee, dest, rules=None, workspace=ROOT, log=print):
    """Copy every non-optional mod of the rule table, the example scripts and the mods/scripts readmes into
    the staged package <dest>. Returns (enabled ids, off ids, warnings). Raises SystemExit on a refusal."""
    rules = rules or load_rules()
    melee, dest, workspace = Path(melee), Path(dest), Path(workspace)
    enabled, off, warnings = [], [], []
    for mid, mod in rules['mods'].items():
        if denied(rules, mid):
            raise SystemExit(f"mod_rules.json lists '{mid}', which is on the never-package list")
        if mod.get('optional'):
            continue
        src = melee / mod['source']
        if not (src / 'mod.json').is_file():
            warnings.append(f"no {mod['source']} in the melee checkout: the package has no '{mid}' mod")
            continue
        allow, tracked, count = allow_regex(mod), tracked_files(melee, mod['source']), 0
        for f in sorted(p for p in src.rglob('*') if p.is_file()):
            in_mod = f.relative_to(src).as_posix()
            if not allow.fullmatch(in_mod):
                continue
            if denied(rules, in_mod):
                raise SystemExit(f'refusing {mid}/{in_mod}: on the never-package list')
            if in_mod not in tracked:
                raise SystemExit(f'refusing {mid}/{in_mod}: matches the allow list but is not tracked in git (a local file?)')
            copy_in(f, dest / 'mods' / mid / in_mod, workspace)
            count += 1
        log(f"  mod {mid}: {count} files{' (on)' if mod.get('default_on') else ' (off)'}")
        (enabled if mod.get('default_on') else off).append(mid)
    mods = dest / 'mods'
    mods.mkdir(parents=True, exist_ok=True)
    (mods / 'README.txt').write_text(MODS_README, encoding='ascii')
    sources = workspace / 'tools/mods_browser/sources.example.txt'
    if sources.is_file():
        copy_in(sources, mods / 'sources.txt', workspace)
    (mods / 'enabled.txt').write_text('\n'.join(["# Enabled mods for the next launch (the launcher's Mods tab edits this file)"] + enabled) + '\n',
                                      encoding='ascii')
    if off:
        log(f"  installed but off: {', '.join(off)}")
    examples = melee / 'pc/scripts/examples'
    if examples.is_dir():
        for f in sorted(p for p in examples.rglob('*') if p.is_file() and p.suffix in ('.lua', '.json')):
            rel = f.relative_to(examples).as_posix()
            if rel.split('/')[0] in rules['examples_skip']:
                continue
            if denied(rules, rel):
                raise SystemExit(f'refusing examples/{rel}: on the never-package list')
            copy_in(f, dest / 'scripts/examples' / rel, workspace)
        (dest / 'scripts').mkdir(parents=True, exist_ok=True)
        (dest / 'scripts/README.txt').write_text(SCRIPTS_README, encoding='ascii')
    else:
        warnings.append('no pc/scripts/examples in the melee checkout: the package has no example scripts')
    for w in warnings:
        log('warning: ' + w)
    return enabled, off, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--melee', type=Path, required=True)
    ap.add_argument('--dest', type=Path, required=True)
    a = ap.parse_args(argv)
    stage_mods(a.melee, a.dest)
    return 0


if __name__ == '__main__':
    sys.exit(main())
