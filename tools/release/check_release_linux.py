#!/usr/bin/env python3
"""check_release_linux.py - prove a Linux release folder or tarball holds only what we may redistribute.

    python3 tools/release/check_release_linux.py <folder | .tar.xz | .tar.gz | .zip> [--repo-root <workspace>]

The Linux counterpart of tools/release/check_release.ps1, with the same content rules. Exit 0 = clean;
anything else = do not publish, every problem is listed. tools/port/package_linux.py runs it on the
folder before it writes the tarball.

  1. Allowlist by area (top-level files, bin/, lib/, launcher/, assets/, licenses/, udev/, mods/, scripts/).
     A new kind of file has to be added here on purpose.
  2. Denylist: disc and save extensions (.iso .gcm .rvz .dol .dat .usd .hps .gci .png .wav ...), and folders
     named after the places disc data lives (ace, packs, akaneia-build, meleedump, card, userdata ...).
  3. Content sniffing on every file whatever its name: a GameCube/Wii disc header, an RVZ/WIA/CISO
     container, a memory-card save ("GALE01"... at offset 0), an HSD archive (first word = the file's own
     size), a DOL (text section table at 0x100).
  4. assets/ui must be byte-identical to the art committed as _build/ui in the workspace repo.
  5. Mods are required (the Linux package carries the same mods as the Windows zip) and checked against tools/release/mod_rules.json (the same table the Windows packager copies
     by): a known mod id, only paths its allow patterns name, never-package ids (envoy_drives_sa2,
     local-assets, ported/private fighters, ACE/Akaneia packs) fail by name. The single `.dat` exception is
     the Courier's own built files: listed in mods/original-assets.json with a matching sha256, a path
     matching the mod's original_dat pattern, under 8 MB, holding the mod's own symbol and no `Ply<Other>_`
     symbol. A disc file and a built original look alike by extension; the record, the path and the symbols
     are how they are told apart.
  6. No file over 64 MB, no personal path (/home/<name>/, C:\\Users\\<name>\\) in our own binaries, maps and
     text, the licence files present, version.txt declaring the netplay protocol the code uses
     (tools/release/netplay_protocol.ps1), runtime.sha256 and manifest.json matching every file.
"""
import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

DISC_EXT = {'.iso', '.gcm', '.rvz', '.wia', '.ciso', '.wbfs', '.nkit', '.gcz', '.dol', '.dat', '.usd', '.hps',
            '.thp', '.mth', '.ssm', '.sem', '.gci', '.sav', '.raw', '.tpl', '.bnr', '.rel', '.elf', '.png', '.bmp',
            '.tga', '.dds', '.jpg', '.jpeg', '.tex', '.bin', '.wav', '.ogg', '.mp3', '.obj', '.glb'}
DISC_DIRS = {'ace', 'packs', 'akaneia-build', 'akaneia', 'meleedump', 'card', 'card-ace', 'card-empty', 'card-trophy',
             'userdata', 'crashlogs', 'hsd_export', 'm-ex', 'menutex', 'gltf', 'orig', 'files', 'sys'}
TOP_FILES = {'version.txt', 'README.txt', 'IMPLEMENTATION_STATUS.md', 'manifest.json', 'runtime.sha256',
             'launch-melee', 'GD-Melee', 'gd-melee-diagnose.sh', 'netplay_server.txt', 'HOW TO PLAY ONLINE.txt'}
MOD_TOP_FILES = {'README.txt', 'sources.txt', 'enabled.txt', 'original-assets.json'}
REQUIRED = ['README.txt', 'version.txt', 'bin/melee', 'bin/version.txt', 'launcher/bin/gd-melee-launcher',
            'licenses/GPL-2.0.txt', 'licenses/THIRD-PARTY-NOTICES.txt', 'runtime.sha256', 'manifest.json']
# files we built ourselves: scanned for personal paths (third-party libraries are not)
OWN_BINARIES = {'bin/melee', 'bin/melee-graphics-probe', 'bin/melee-pc.msvc.map', 'launcher/bin/gd-melee-launcher',
                'launcher/bin/melee-graphics-probe'}
TEXT_EXT = {'.lua', '.wgsl', '.json', '.txt', '.md', '.genoasm', '.words', '.sh', '.rules', '.conf', '.dat'}
PERSONAL = re.compile(rb'(?i)(?:/home/|/Users/|[A-Z]:[\\/]Users[\\/])(?!Public[\\/]|Default[\\/]|runner/|builder/|build/|user/)[A-Za-z0-9._-]{2,}[\\/]')
MAX_BYTES = 64 * 1024 * 1024


def be32(b, o):
    return int.from_bytes(b[o:o + 4], 'big') if len(b) >= o + 4 else -1


def netplay_protocol():
    text = (HERE / 'netplay_protocol.ps1').read_text(encoding='utf-8')
    m = re.search(r'function Get-NetplayProtocol \{ return (\d+) \}', text)
    if not m:
        raise SystemExit('cannot read the protocol number from tools/release/netplay_protocol.ps1')
    return int(m[1])


def load_entries(path):
    """-> list of (relative path with '/', bytes, is_symlink)"""
    entries, problems = [], []
    if path.is_dir():
        for p in sorted(path.rglob('*')):
            if p.is_symlink():
                entries.append((p.relative_to(path).as_posix(), b'', True))
            elif p.is_file():
                entries.append((p.relative_to(path).as_posix(), p.read_bytes(), False))
        return entries, problems
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as z:
            names = [(i.filename, i) for i in z.infolist() if not i.filename.endswith('/')]
            data = [(n, z.read(i), False) for n, i in names]
    else:
        with tarfile.open(path) as t:
            data = []
            for m in t:
                if m.issym() or m.islnk():
                    data.append((m.name, b'', True))
                elif m.isfile():
                    data.append((m.name, t.extractfile(m).read(), False))
    tops = {n.split('/')[0] for n, _, _ in data}
    if len(tops) != 1:
        problems.append(f'archive should contain one top-level folder, found: {", ".join(sorted(tops))}')
    for n, b, s in data:
        entries.append((n.split('/', 1)[1] if len(tops) == 1 and '/' in n else n, b, s))
    return entries, problems


def sha(b):
    return hashlib.sha256(b).hexdigest()


def git_ui_blobs(repo):
    out = subprocess.run(['git', '-C', str(repo), 'ls-tree', '-r', 'HEAD', '--', '_build/ui'],
                         capture_output=True, text=True).stdout
    blobs = {}
    for line in out.splitlines():
        meta, name = line.split('\t', 1)
        blobs[name[len('_build/'):]] = meta.split()[2]
    return blobs


def git_blob_sha(b):
    return hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest()


def check(path, repo=ROOT):
    rules = json.loads((HERE / 'mod_rules.json').read_text(encoding='utf-8'))
    deny_ids = re.compile(rules['deny_mod_ids'])
    problems = []
    fail = problems.append
    entries, more = load_entries(Path(path))
    problems.extend(more)
    if not entries:
        fail(f'no files found in {path}')
    seen = {}
    for rel, b, sym in entries:
        if rel in seen:
            fail(f'{rel} : duplicate entry')
        seen[rel] = None if sym else sha(b)  # a symlink's content is its target's: not compared
    original = {}
    for rel, b, _ in entries:
        if rel == 'mods/original-assets.json':
            try:
                for f in json.loads(b)['files']:
                    if not re.fullmatch(r'[0-9a-f]{64}', f['sha256']) or not f['path']:
                        raise ValueError('bad entry')
                    original[f['path']] = f['sha256']
            except Exception as e:  # noqa: BLE001 - any malformed record is a failure
                fail(f'mods/original-assets.json is malformed: {e}')

    ui = git_ui_blobs(repo)
    if not ui:
        fail(f'cannot verify required ui art (no committed _build/ui at {repo})')

    for rel, b, sym in entries:
        parts = rel.split('/')
        name, dirs = parts[-1], parts[:-1]
        ext = Path(name).suffix.lower()
        if sym:
            target_ok = rel.startswith('launcher/') and ('.so' in name)
            if not target_ok:
                fail(f'{rel} : symbolic links are only allowed for launcher shared libraries')
            continue
        if rel.startswith('/') or '..' in parts or '\\' in rel:
            fail(f'{rel} : unsafe release path')

        # 2. denylist
        orig = False
        mod_rule = rules['mods'].get(dirs[1]) if len(dirs) >= 2 and dirs[0] == 'mods' else None
        in_mod = '/'.join(parts[2:]) if mod_rule else ''
        if ext == '.dat' and mod_rule and mod_rule.get('original_dat') and re.fullmatch(mod_rule['original_dat'], in_mod):
            orig = True
            txt = b.decode('latin-1')
            prefix = mod_rule['original_dat_symbol_prefix']
            if rel not in original:
                fail(f'{rel} : a .dat that mods/original-assets.json does not list is disc data (or could be) and never ships')
                orig = False
            elif original[rel] != seen[rel]:
                fail(f'{rel} : sha256 does not match mods/original-assets.json')
                orig = False
            elif len(b) > 8 * 1024 * 1024:
                fail(f'{rel} : an original .dat is never this big')
                orig = False
            elif prefix.lower() not in txt.lower():
                fail(f"{rel} : holds none of the mod's own symbols ('{prefix}')")
                orig = False
            else:
                for m in re.finditer(r'Ply([A-Za-z0-9]+)_', txt):
                    if not m[1].startswith(prefix):
                        fail(f"{rel} : contains another fighter's symbol ({m[0]}): that is disc-derived")
                        orig = False
                        break
        if ext in DISC_EXT and not orig:
            fail(f"{rel} : '{ext}' files are disc data (or could hold it) and never ship")
        own_files = bool(mod_rule) and len(dirs) >= 3 and dirs[2] == 'files' and re.fullmatch(
            '(?:' + '|'.join(f'(?:{a})' for a in mod_rule['allow']) + ')', in_mod) is not None
        for d in dirs:
            if d.lower() in DISC_DIRS and not (own_files and d == 'files'):
                fail(f"{rel} : inside a '{d}' folder, which is where disc data or saves live")
            if d.lower() in rules['deny_dirs_anywhere']:
                fail(f"{rel} : inside a '{d}' folder, which is local-only")

        # 1. allowlist
        ok = False
        top = dirs[0] if dirs else ''
        if not dirs:
            ok = name in TOP_FILES
        elif top == 'bin':
            ok = len(dirs) == 1 and name in {'melee', 'melee-pc.msvc.map', 'version.txt', 'melee-graphics-probe'}
        elif top == 'lib':
            ok = len(dirs) == 1 and '.so' in name
        elif top == 'launcher':
            ok = ('.so' in name) or ext in {'.conf', '.txt', '.json', '.qm'} or (ext == '' and b[:4] == b'\x7fELF')
        elif top == 'assets':
            if dirs[1:2] == ['ui']:
                ok = len(dirs) == 2 and ext in {'.gxtex', '.json'}
            elif dirs[1:2] == ['fonts']:
                ok = len(dirs) == 2 and ext in {'.ttf', '.otf', '.txt'}
        elif top == 'licenses':
            ok = len(dirs) == 1 and ext == '.txt'
        elif top == 'udev':
            ok = len(dirs) == 1 and ext == '.rules'
        elif top == 'mods':
            if len(dirs) == 1:
                ok = name in MOD_TOP_FILES
            else:
                mid = dirs[1]
                if deny_ids.fullmatch(mid):
                    fail(f"{rel} : mod '{mid}' is on the never-package list (private, ported, local or disc-derived)")
                    ok = True
                elif not mod_rule:
                    fail(f"{rel} : mod '{mid}' is not a mod this release carries (tools/release/mod_rules.json)")
                    ok = True
                else:
                    ok = re.fullmatch('(?:' + '|'.join(f'(?:{a})' for a in mod_rule['allow']) + ')', in_mod) is not None
        elif top == 'scripts':
            ok = rel == 'scripts/README.txt' or (len(dirs) >= 2 and dirs[1] == 'examples' and ext in {'.lua', '.json'})
            if len(dirs) >= 3 and dirs[1] == 'examples' and dirs[2] in rules['examples_skip']:
                fail(f"{rel} : '{dirs[2]}' is a mod now (mods/{dirs[2]}), not an example script")
                ok = True
        if not ok:
            fail(f'{rel} : not on the release allowlist (tools/release/check_release_linux.py)')

        # 3. sniffing
        if len(b) >= 0x20 and be32(b, 0x1C) == 0xC2339F3D:
            fail(f'{rel} : contains a GameCube disc header')
        if len(b) >= 0x20 and be32(b, 0x18) == 0x5D1C9EA3:
            fail(f'{rel} : contains a Wii disc header')
        if b[:4] in (b'RVZ\x01', b'WIA\x01', b'CISO'):
            fail(f'{rel} : is a compressed disc image')
        if re.fullmatch(rb'G[A-Z]{2}[EPJ]', b[:4]) and re.fullmatch(rb'[0-9A-Z]{2}', b[4:6]):
            fail(f'{rel} : starts with a game ID ({b[:6].decode()}): a memory-card save or disc header')
        if not orig and b[:4] != b'\x7fELF' and len(b) >= 0x20 and be32(b, 0) == len(b):
            fail(f"{rel} : looks like an HSD archive (.dat): its first word is its own size")
        if len(b) >= 0x100 and b[:4] != b'\x7fELF':
            t0, a0, entry = be32(b, 0), be32(b, 0x48), be32(b, 0xE0)
            if t0 == 0x100 and 0x80000000 <= a0 < 0x81800000 and 0x80000000 <= entry < 0x81800000:
                fail(f'{rel} : looks like a DOL (GameCube executable)')
        if rel in OWN_BINARIES or ext in TEXT_EXT:
            m = PERSONAL.search(b)
            if m:
                fail(f'{rel} : contains a personal path ({m[0].decode("latin-1")}...)')

        # 4. ui art
        if top == 'assets' and dirs[1:2] == ['ui']:
            key = 'ui/' + name
            if key not in ui:
                fail(f'{rel} : not committed under _build/ui in the workspace repo')
            elif ui[key] != git_blob_sha(b) and (ext != '.json' or ui[key] != git_blob_sha(b.replace(b'\r\n', b'\n'))):
                fail(f'{rel} : differs from the committed _build/ui art')
        if len(b) > MAX_BYTES:
            fail(f'{rel} : {len(b) // 2**20} MB is too big for anything we ship')

    for r in REQUIRED:
        if r not in seen:
            fail(f'missing required file: {r}')
    for key in ui:
        if 'assets/' + key not in seen:
            fail(f'missing required file: assets/{key}')
    for mid, rule in rules['mods'].items():
        if rule.get('default_on') and f'mods/{mid}/mod.json' not in seen:
            fail(f'missing required file: mods/{mid}/mod.json')
        if rule.get('default_on') or f'mods/{mid}/mod.json' in seen:
            for need in rule.get('required', []):
                if f'mods/{mid}/{need}' not in seen:
                    fail(f'missing required file: mods/{mid}/{need}')
    if 'mods/enabled.txt' in seen:
        text = next(b for r, b, _ in entries if r == 'mods/enabled.txt').decode('utf-8', 'replace')
        listed_on = set()
        for line in text.splitlines():
            eid = line.split('#', 1)[0].strip()
            if not eid:
                continue
            listed_on.add(eid)
            er = rules['mods'].get(eid)
            if not er:
                fail(f"mods/enabled.txt names '{eid}', which is not a mod this release carries")
            elif not er.get('default_on'):
                fail(f"mods/enabled.txt turns on '{eid}', which must ship off by default")
            elif f'mods/{eid}/mod.json' not in seen:
                fail(f"mods/enabled.txt names '{eid}', which is not in the package")
        for mid, rule in rules['mods'].items():
            if rule.get('default_on') and mid not in listed_on:
                fail(f"mods/enabled.txt does not turn on '{mid}', which ships on by default")
    else:
        fail('missing required file: mods/enabled.txt')

    by_rel = {r: b for r, b, _ in entries}
    if 'version.txt' in by_rel:
        text = by_rel['version.txt'].decode('utf-8', 'replace')
        found = re.findall(r'(?m)^netplay_protocol\s+(\d+)\s*$', text)
        if found != [str(netplay_protocol())]:
            fail(f'version.txt must declare netplay_protocol {netplay_protocol()} exactly once')
        if 'bin/version.txt' in by_rel and by_rel['bin/version.txt'] != by_rel['version.txt']:
            fail('bin/version.txt differs from version.txt')
    # manifests: every file listed once with the right hash, nothing listed that is absent
    if 'runtime.sha256' in by_rel:
        listed = {}
        for line in by_rel['runtime.sha256'].decode().splitlines():
            m = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
            if not m:
                fail('malformed runtime.sha256 line')
            elif m[2] in listed:
                fail(f'{m[2]} : duplicate runtime.sha256 entry')
            else:
                listed[m[2]] = m[1]
        for r, h in seen.items():
            if r in ('runtime.sha256', 'manifest.json'):
                continue
            if r not in listed:
                fail(f'{r} : not in runtime.sha256')
            elif h is not None and listed[r] != h:
                fail(f'{r} : sha256 does not match runtime.sha256')
        for r in listed:
            if r not in seen:
                fail(f'{r} : listed in runtime.sha256 but missing')
    if 'manifest.json' in by_rel:
        try:
            files = json.loads(by_rel['manifest.json'])['files']
            for r, h in seen.items():
                if r == 'manifest.json':
                    continue
                if h is not None and files.get(r) != h and not (r == 'runtime.sha256' and r not in files):
                    fail(f'{r} : not in manifest.json or its sha256 does not match')
            for r in files:
                if r not in seen:
                    fail(f'{r} : listed in manifest.json but missing')
        except Exception as e:  # noqa: BLE001
            fail(f'manifest.json is malformed: {e}')
    return problems, len(entries), sum(len(b) for _, b, _ in entries) / 2**20


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('path', type=Path)
    ap.add_argument('--repo-root', type=Path, default=ROOT)
    a = ap.parse_args(argv)
    problems, count, mb = check(a.path, a.repo_root)
    if problems:
        print(f'RELEASE CHECK FAILED: {a.path}')
        for p in problems:
            print('  x ' + p)
        return 1
    print(f'release check OK: {count} files, {mb:.1f} MB, no disc data ({a.path})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
