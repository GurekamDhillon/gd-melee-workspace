#!/usr/bin/env python3
"""Read-only relocation audit. Never sources .env or prints its values.

Default: tracked and untracked nonignored files, plus local .env and Git pointers.
--all: also inspect ignored text/generated files, lane response lists and caches.
Exit 1 means findings; exit 2 means incomplete inspection; exit 0 means no findings.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import stat

ABSOLUTE = re.compile(r"(?i)(?:\b[a-z]:[/\\]|(?<![A-Za-z0-9/])/(?:mnt/)?[c-e]/)[^\r\n\"<>|]*")
LEGACY = re.compile(r"(?i)Desktop[/\\]|GD.s Melee[/\\]")
TEXT = {'.py', '.sh', '.bat', '.cmd', '.ps1', '.psm1', '.lua', '.c', '.cpp',
        '.h', '.hpp', '.json', '.toml', '.yaml', '.yml', '.ini', '.cfg', '.conf',
        '.rsp', '.txt', '.md', '.cmake', '.ninja', '.d', '.xml', '.props', '.cs',
        '.vcxproj', '.sln', '.html', '.js', '.ts', '.css', '.env'}


def scan(path: Path, label: str):
    """Yield locations only for secrets; ordinary files include matched path text."""
    try:
        data = path.read_bytes()
    except OSError:
        yield f'UNREADABLE {label}'
        return
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        text = data.decode('utf-16', errors='replace')
    elif b'\x00' in data[:4096]:
        return
    else:
        text = data.decode('utf-8-sig', errors='replace')
    secret = path.name == '.env' or path.name.startswith('.env.')
    for number, line in enumerate(text.splitlines(), 1):
        matches = list(ABSOLUTE.finditer(line))
        if not matches and not LEGACY.search(line):
            continue
        if secret:
            key = re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=', line)
            detail = (key[1] if key else 'comment/entry') + ' [value redacted]'
        else:
            detail = ' | '.join(m[0].strip() for m in matches) or 'legacy relative location'
        yield f'{label}:{number}: {detail}'


def git(root, *args):
    return subprocess.check_output(['git', '-c', 'safe.directory=' + str(root.resolve()).replace('\\', '/'), '-C', str(root), *args], stderr=subprocess.DEVNULL)


def audit(root: Path, include_ignored=False):
    files = set()
    errors = []
    try:
        names = git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')
        files.update(root / os.fsdecode(n) for n in names.split(b'\0') if n)
    except (OSError, subprocess.CalledProcessError):
        errors.append('UNREADABLE git file inventory')
    if include_ignored:
        for folder, dirs, names in os.walk(root, followlinks=False, onerror=lambda exc: errors.append(f"UNREADABLE directory: {exc.filename}")):
            # Windows junctions are reparse points even on Python without is_junction().
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', '.venv'}
                       and not ((Path(folder) / d).lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
                                if os.name == 'nt' else (Path(folder) / d).is_symlink())]
            for name in names:
                p = Path(folder) / name
                if p.suffix.lower() in TEXT or name in {'.git', '.env', 'CMakeCache.txt'} or name.startswith('.env.'):
                    files.add(p)
    files.update(root.glob('.env*'))
    files.add(root / '.git')
    # Include the common checkout's private settings and all registered worktree pointers.
    # Do not alter or recursively scan Git object databases.
    try:
        main_root = Path(os.fsdecode(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir')).strip()).parent
    except (OSError, subprocess.CalledProcessError):
        main_root = root
    for repo in (root, main_root / 'melee'):
        if not repo.exists():
            continue
        try:
            common = Path(os.fsdecode(git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')).strip())
            files.update(common.parent.glob('.env*'))
            files.add(common / 'config')
            for registration in (common / 'worktrees').glob('*'):
                pointer = registration / 'gitdir'
                files.add(pointer)
                if pointer.is_file():
                    files.add(Path(pointer.read_text().strip()))
                files.add(registration / 'commondir')
                files.add(registration / 'config.worktree')
        except (OSError, subprocess.CalledProcessError):
            errors.append(f'UNREADABLE git metadata: {repo.name}')
    findings = []
    for p in sorted(files):
        if p.is_dir() or not p.exists():
            continue
        try:
            label = p.relative_to(root).as_posix()
        except ValueError:
            label = str(p)
        findings.extend(scan(p, label))
    return findings + errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--all', action='store_true', help='include ignored text, caches and build lanes (can be slow)')
    args = parser.parse_args()
    sys.stdout.reconfigure(errors='backslashreplace')
    rows = audit(args.root.resolve(), args.all)
    for row in rows:
        print(row)
    print(f'{len(rows)} finding(s); read-only, no settings sourced or files changed.')
    return 2 if any(row.startswith('UNREADABLE') for row in rows) else int(bool(rows))


if __name__ == '__main__':
    raise SystemExit(main())
