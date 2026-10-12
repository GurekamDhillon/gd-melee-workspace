"""Report old run directories and agent roots; never delete or follow reparse points.

python tools/port/housekeeping_report.py --build E:/path/to/_build --days 7 [--json]

Sizes are logical file bytes, including hardlinks, NOT reclaimable disk estimates.
Agent-root rows include their runs, so rows overlap. Branches are current registered
worktree HEADs; name-based ownership is inferred, not historical proof.
"""
import argparse
import json
import math
import os
from pathlib import Path
import stat
import sys
import time

DAY = 86400
REPARSE = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)


def is_link(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & REPARSE)


class Reader:
    """Read-only traversal. Check ancestors too: lstat alone protects only the leaf."""
    def __init__(self):
        self.links = {}
        self.warnings = set()

    def flag_link(self, path):
        try:
            target = os.readlink(path)
        except OSError:
            target = '(target unavailable)'
        self.links[str(path)] = {'path': str(path), 'target': target}

    def checked(self, path):
        path = Path(os.path.abspath(path))  # lexical normalization, never resolve a link
        for parent in (*reversed(path.parents), path):
            try:
                info = parent.lstat()
            except FileNotFoundError:
                return None
            except OSError as exc:
                self.warnings.add(f'{parent}: {exc}')
                return None
            if is_link(info):
                self.flag_link(parent)
                return None
        return info

    def children(self, path):
        info = self.checked(path)
        if info is None or not stat.S_ISDIR(info.st_mode):
            return []
        try:
            with os.scandir(path) as entries:
                return sorted((Path(e.path) for e in entries), key=str)
        except OSError as exc:
            self.warnings.add(f'{path}: {exc}')
            return []

    def text(self, path):
        info = self.checked(path)
        if info is None or not stat.S_ISREG(info.st_mode):
            return ''
        if info.st_size > 2 * 1024 * 1024:
            self.warnings.add(f'{path}: metadata exceeds 2 MiB; not read')
            return ''
        try:
            return path.read_text(encoding='utf-8', errors='replace')
        except OSError as exc:
            self.warnings.add(f'{path}: {exc}')
            return ''

    def scan(self, path):
        total, newest, sources = 0, 0.0, set()
        incomplete = False
        stack = [path]
        while stack:
            current = stack.pop()
            try:
                info = current.lstat()
                if is_link(info):
                    self.flag_link(current)
                    continue
                newest = max(newest, info.st_mtime)
                if stat.S_ISDIR(info.st_mode):
                    with os.scandir(current) as entries:
                        stack.extend(Path(e.path) for e in entries)
                elif stat.S_ISREG(info.st_mode):
                    total += info.st_size
                    if current.name == 'CMakeCache.txt':
                        for line in self.text(current).splitlines():
                            key, sep, value = line.partition('=')
                            if sep and key.split(':')[0] in ('CMAKE_HOME_DIRECTORY', 'GW_MELEE'):
                                sources.add(value)
            except OSError as exc:
                self.warnings.add(f'{current}: {exc}')
                incomplete = True
        return total, newest, sources, incomplete


def absolute(path, base):
    return Path(os.path.abspath(base / path)) if not Path(path).is_absolute() else Path(os.path.abspath(path))


def worktrees(reader, repo):
    """Read Git's registry directly; no worktree operations, branch changes or locks."""
    git_dir = repo / '.git'
    info = reader.checked(git_dir)
    if info is None:
        return []
    if stat.S_ISREG(info.st_mode):
        pointer = reader.text(git_dir).strip()
        if not pointer.startswith('gitdir: '):
            return []
        git_dir = absolute(pointer[8:], repo)
    common = reader.text(git_dir / 'commondir').strip()
    common = absolute(common, git_dir) if common else git_dir

    def record(path, head):
        branch = head.removeprefix('ref: refs/heads/') if head.startswith('ref: refs/heads/') else '(detached ' + head[:12] + ')'
        return {'worktree': str(path), 'branch': branch, 'repo': str(repo)}

    result = []
    head = reader.text(common / 'HEAD').strip()
    # The ordinary checkout has .git/ at the repository root.
    if head:
        result.append(record(common.parent, head))
    for reg in reader.children(common / 'worktrees'):
        pointer = reader.text(reg / 'gitdir').strip()
        head = reader.text(reg / 'HEAD').strip()
        if pointer and head:
            result.append(record(absolute(pointer, reg).parent, head))
    return result


def contains(parent, child):
    parent, child = os.path.normcase(os.path.abspath(parent)), os.path.normcase(os.path.abspath(child))
    try:
        return os.path.commonpath([parent, child]) == parent
    except ValueError:
        return False


def owners_for(name, sources, registry, main_game=None):
    sourced = []
    for source in sorted(sources):
        matches = [w for w in registry if contains(w['worktree'], source)]
        # Pick the closest checkout for this source, retaining independently proven owners.
        closest = [w for w in matches if not any(w != other and contains(w['worktree'], other['worktree']) for other in matches)]
        for owner in closest:
            if owner not in sourced:
                sourced.append(owner)
    if sourced:
        return sourced, 'CMake source path'
    if main_game is not None:
        return [w for w in registry if os.path.normcase(w['worktree']) == os.path.normcase(str(main_game))], 'main game checkout convention (inferred)'
    return [w for w in registry if Path(w['worktree']).name == name], 'name convention (inferred)'


def report(build, workspace, days, now=None):
    now = time.time() if now is None else now
    build, workspace = Path(os.path.abspath(build)), Path(os.path.abspath(workspace))
    reader = Reader()
    rows = []
    info = reader.checked(build)
    if info is not None and stat.S_ISDIR(info.st_mode):
        registry = worktrees(reader, workspace) + worktrees(reader, workspace / 'melee')

        def add(path, kind, name=None, main=False, inherited=None):
            info = reader.checked(path)
            if info is None or not stat.S_ISDIR(info.st_mode):
                return None
            size, newest, sources, incomplete = reader.scan(path)
            # Copied dependency sources under the build tree are not checkout evidence.
            sources = {s for s in sources if Path(s).is_absolute() and not contains(build, s)}
            owners, basis = inherited or owners_for(name or path.name, sources, registry,
                                                    workspace / 'melee' if main else None)
            owner_label = ''
            if kind == 'run':
                try:
                    metadata = json.loads(reader.text(path / 'run.json') or '{}')
                    if isinstance(metadata, dict) and isinstance(metadata.get('owner'), str):
                        owner_label = metadata['owner']
                except ValueError:
                    reader.warnings.add(f'{path / "run.json"}: invalid JSON')
                if main and basis != 'CMake source path' and ' / ' in owner_label:
                    lane = owner_label.split(' / ', 1)[0]
                    if lane != 'main':
                        owners, _ = owners_for(lane, set(), registry)
                        basis = 'run owner label (inferred)'
            age = max(0.0, (now - newest) / DAY)
            if age >= days or incomplete:
                rows.append({'kind': kind, 'path': str(path), 'bytes': size,
                             'age_days': None if incomplete else age, 'incomplete': incomplete,
                             'owners': owners, 'ownership_basis': basis if owners else 'unknown',
                             'ownership_ambiguous': len(owners) > 1, 'owner_label': owner_label})
            return owners, basis

        for path in reader.children(build / 'runs'):
            add(path, 'run', main=True)
        for path in reader.children(build / 'agents'):
            ownership = add(path, 'agent')
            if ownership is not None:
                for run in reader.children(path / 'runs'):
                    add(run, 'run', inherited=ownership)
    elif not reader.links:
        reader.warnings.add(f'{build}: build directory missing or not a directory')
    return {'build': str(build), 'older_than_days': days, 'entries': sorted(rows, key=lambda r: r['path']),
            'reparse_points': sorted(reader.links.values(), key=lambda r: r['path']),
            'warnings': sorted(reader.warnings)}


def finite_days(value):
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError('days must be finite non-negative')
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError('days must be finite non-negative')
    return number


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    default = Path(os.environ.get('GW_ROOT', Path(__file__).absolute().parents[2])) / '_build'
    ap.add_argument('--build', type=Path, default=default)
    ap.add_argument('--workspace', type=Path, help='workspace repo (default: parent of --build)')
    ap.add_argument('--days', '--old-days', type=finite_days, default=7.0)
    ap.add_argument('--json', action='store_true', help='machine-readable report on stdout')
    args = ap.parse_args(argv)
    data = report(args.build, args.workspace or args.build.parent, args.days)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Report only: {data['build']} / runs and agents older than {args.days:g} days")
        print('Logical bytes include hardlinks; agent rows include their runs. Sizes overlap and are not reclaim estimates.')
        print('Branches are current worktree HEADs; inferred ownership is not historical proof. No files are deleted.')
        for row in data['entries']:
            age = 'unknown (incomplete scan)' if row['incomplete'] else f"{row['age_days']:.1f}d"
            owner = '; '.join(f"{w['worktree']} [{w['branch']}]" for w in row['owners']) or 'unknown'
            ambiguous = ' AMBIGUOUS' if row['ownership_ambiguous'] else ''
            print(f"{row['kind']:5} {row['bytes']:12,d} bytes ({row['bytes'] / 1024**3:.2f} GiB) {age:>8} {row['path']}")
            print(f"      owner={owner} / {row['ownership_basis']}{ambiguous}")
            if row['owner_label']:
                print(f"      run owner label={row['owner_label']}")
        if not data['entries']:
            print('No old candidates found.')
        for link in data['reparse_points']:
            print(f"REPARSE (not followed, target bytes excluded): {link['path']} -> {link['target']}")
        for warning in data['warnings']:
            print('WARNING: ' + warning)
    return 0


if __name__ == '__main__':
    sys.exit(main())
