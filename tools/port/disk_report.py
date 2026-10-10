"""Where the disk went under _build, and what is safe to clean. Deletes NOTHING.

    python tools/port/disk_report.py [--build DIR] [--top N] [--old-days D]

Lists the largest entries under _build (top level), every agent build root under _build/agents/ with
its runs/ subtotal and newest file date, then a suggested cleanup list: idle agent roots, old
sweeps, old release staging, and run sandboxes beyond the retention (prune_runs.py). Symlinks and
junctions are not followed; a hardlinked file is counted once (the first directory that holds it), so
the sizes add up to what the drive really loses. A root with a running melee-pc.exe is flagged IN USE
and never suggested. Run the suggested commands yourself.
"""
import argparse
import os
from pathlib import Path
import re
import stat
import sys
import time

GIB = 1024 ** 3
REPARSE = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)
SWEEP_RE = re.compile(r'^(sweep|crash[-_]?sweep)', re.I)
RELEASE_RE = re.compile(r'^(release|win-rc|.*-extract$|.*staging)', re.I)


def is_link(st):
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, 'st_file_attributes', 0) & REPARSE)


class Scanner:
    """Sizes directories; hardlinked files (nlink > 1) are counted once across the whole scan."""

    def __init__(self):
        self.seen = set()

    def size(self, path):
        """Return (bytes, newest_mtime, file_count) of a path, not following links."""
        total, newest, count = 0, 0.0, 0
        stack = [str(path)]
        while stack:
            d = stack.pop()
            try:
                it = os.scandir(d)
            except OSError:
                continue
            with it:
                for e in it:
                    try:
                        st = e.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    if is_link(st):
                        continue
                    if stat.S_ISDIR(st.st_mode):
                        stack.append(e.path)
                        continue
                    newest = max(newest, st.st_mtime)
                    count += 1
                    # scandir's stat() has no inode/link count on Windows; lstat does.
                    try:
                        st = os.lstat(e.path)
                    except OSError:
                        continue
                    if st.st_nlink > 1:
                        key = (st.st_dev, st.st_ino)
                        if key in self.seen:
                            continue
                        self.seen.add(key)
                    total += st.st_size
        return total, newest, count


def fmt_gb(n):
    return f'{n / GIB:8.2f} GB'


def age_days(mtime, now):
    return (now - mtime) / 86400 if mtime else float('inf')


def fmt_age(mtime, now):
    return 'empty' if not mtime else f'{age_days(mtime, now):.1f}d ago'


def live_exe_dirs():
    """Directories (normalized) that hold a running melee-pc.exe, or None if unknown."""
    sys.path.insert(0, str(Path(__file__).parent))
    import prune_runs
    live = prune_runs.live_games()
    if live is None:
        return None
    return [prune_runs.normalized(Path(p).parent) for p in live]


def in_use(path, live_dirs):
    if not live_dirs:
        return False
    n = str(Path(path).resolve()).replace('\\', '/').casefold().rstrip('/') + '/'
    return any((d + '/').startswith(n) for d in live_dirs)


def suggestions(top_rows, agent_rows, now, old_days, live_dirs, runs_keep=10):
    """Pure: rows are dicts {name, path, bytes, newest, runs_count?, runs_bytes?}. Returns [(bytes, text)]."""
    out = []
    for r in agent_rows:
        if in_use(r['path'], live_dirs):
            continue
        if age_days(r['newest'], now) >= old_days:
            out.append((r['bytes'], f"agent root '{r['name']}' idle {fmt_age(r['newest'], now)}: "
                                    f"tools/port/agent_rm.sh {r['name']}   (after confirming its lane is finished)"))
        elif r.get('runs_count', 0) > runs_keep:
            out.append((r['runs_bytes'], f"agent root '{r['name']}' has {r['runs_count']} run sandboxes: "
                                         f"GW_BUILD_ROOT=_build/agents/{r['name']} python tools/port/prune_runs.py "
                                         f"--root _build/agents/{r['name']}/runs --keep {runs_keep} --current none"))
    for r in top_rows:
        if not r.get('dir', True) or in_use(r['path'], live_dirs) or age_days(r['newest'], now) < old_days:
            continue
        if SWEEP_RE.match(r['name']):
            out.append((r['bytes'], f"old sweep _build/{r['name']} ({fmt_age(r['newest'], now)}): keep results.md/json, "
                                    f"delete its runs/ (rm -rf _build/{r['name']}/runs)"))
        elif RELEASE_RE.match(r['name']):
            out.append((r['bytes'], f"old release staging _build/{r['name']} ({fmt_age(r['newest'], now)}): "
                                    f"rm -rf _build/{r['name']}   (keep any zip you still need to ship)"))
    return sorted(out, key=lambda x: -x[0])


def merged_worktrees(wtdir, base='main'):
    """[(bytes, path, branch, repo)] for worktrees under wtdir whose branch is merged into `base`.
    Looks in the workspace repo and its melee/ checkout. Read-only git queries."""
    import subprocess
    wtdir = Path(wtdir)
    if not wtdir.is_dir():
        return []
    root = wtdir.parent
    found, scan = [], Scanner()
    here = Path(os.environ.get('GW_ROOT', Path(__file__).resolve().parents[2]))
    melee = Path(os.environ.get('GW_MELEE', here / 'melee'))
    for repo in dict.fromkeys([root, root / 'melee', here, melee]):
        try:
            lst = subprocess.run(['git', '-C', str(repo), 'worktree', 'list', '--porcelain'],
                                 capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            continue
        rb = next((c for c in (base, 'pc-port') if subprocess.run(
            ['git', '-C', str(repo), 'rev-parse', '--verify', '-q', c], capture_output=True).returncode == 0), None)
        if rb is None:
            continue
        for blk in lst.split('\n\n'):
            f = dict(l.split(' ', 1) for l in blk.splitlines() if ' ' in l)
            path, br = f.get('worktree'), f.get('branch', '').replace('refs/heads/', '')
            if not path or not br or br == rb:
                continue
            try:
                if wtdir.resolve() not in Path(path).resolve().parents:
                    continue
                merged = subprocess.run(['git', '-C', str(repo), 'branch', '--merged', rb, '--list', br],
                                        capture_output=True, text=True).stdout
            except OSError:
                continue
            if br in [m.strip(' *+') for m in merged.splitlines()]:
                found.append((scan.size(path)[0], path, br, str(repo)))
    return sorted({f[1]: f for f in found}.values(), reverse=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    default_build = Path(os.environ.get('GW_ROOT', Path(__file__).resolve().parents[2])) / '_build'
    ap.add_argument('--build', type=Path, default=default_build)
    ap.add_argument('--worktrees', type=Path, default=None, help='dir of git worktrees (default <workspace>/worktrees)')
    ap.add_argument('--top', type=int, default=25)
    ap.add_argument('--old-days', type=float, default=3.0, help='age after which a root/sweep/staging counts as idle')
    a = ap.parse_args(argv)
    a.worktrees = a.worktrees or (default_build.parent / 'worktrees')
    build = a.build
    if not build.is_dir():
        print(f'no such directory: {build}', file=sys.stderr)
        return 1
    now = time.time()
    scan = Scanner()
    live_dirs = live_exe_dirs()

    # Agent roots first so their hardlinks are attributed to them, not to the shared _build/masstest.
    agent_rows = []
    agents = build / 'agents'
    if agents.is_dir():
        for p in sorted(agents.iterdir()):
            if p.is_dir() and not is_link(p.lstat()):
                b, newest, _ = scan.size(p)
                row = {'name': p.name, 'path': str(p), 'bytes': b, 'newest': newest, 'runs_count': 0, 'runs_bytes': 0}
                runs = p / 'runs'
                if runs.is_dir():
                    rows = [x for x in runs.iterdir() if x.is_dir()]
                    row['runs_count'] = len(rows)
                    row['runs_bytes'] = sum(scan.size(x)[0] for x in rows)
                agent_rows.append(row)
    top_rows, links = [], []
    for p in sorted(build.iterdir()):
        if p.name == 'agents':
            continue
        try:
            st = p.lstat()
        except OSError:
            continue
        if is_link(st):
            try:
                target = os.readlink(p)
            except OSError:
                target = '?'
            links.append((p.name, target))
            continue
        elif p.is_dir():
            b, newest, _ = scan.size(p)
            top_rows.append({'name': p.name, 'path': str(p), 'bytes': b, 'newest': newest, 'dir': True})
        else:
            top_rows.append({'name': p.name, 'path': str(p), 'bytes': st.st_size, 'newest': st.st_mtime})
    agents_total = sum(r['bytes'] for r in agent_rows)
    total = agents_total + sum(r['bytes'] for r in top_rows)

    print(f'disk report for {build}  (links not followed, hardlinks counted once)')
    print(f'total under _build: {fmt_gb(total).strip()}   (agents/ {fmt_gb(agents_total).strip()})')
    if live_dirs is None:
        print('warning: running games could not be listed; "IN USE" flags are unavailable')
    print(f'\nLargest entries in _build (top {a.top}):')
    for r in sorted(top_rows, key=lambda r: -r['bytes'])[:a.top]:
        flag = '  IN USE' if in_use(r['path'], live_dirs) else ''
        print(f"  {fmt_gb(r['bytes'])}  {r['name']:<34} {fmt_age(r['newest'], now)}{flag}")
    print(f'\nAgent build roots (_build/agents/, {len(agent_rows)}):')
    for r in sorted(agent_rows, key=lambda r: -r['bytes']):
        flag = '  IN USE' if in_use(r['path'], live_dirs) else ''
        print(f"  {fmt_gb(r['bytes'])}  {r['name']:<34} {fmt_age(r['newest'], now)}  runs: {r['runs_count']}{flag}")
    if links:
        print(f'\nJunctions/symlinks in _build (not followed, 0 bytes counted here; the target is on whatever drive it names,')
        print('and a target on this same drive frees nothing by being a link - delete the data, not the link):')
        for n, t in links:
            print(f'  {n:<34} -> {t}')
    wt = merged_worktrees(a.worktrees)
    print(f'\nMerged-branch worktrees under {a.worktrees} (safe candidates; `git worktree remove` after a clean `git status`):')
    if not wt:
        print('  none found (or git unavailable)')
    for size, path, branch, repo in wt:
        print(f'  {fmt_gb(size)}  {path}   [{branch} merged]   git -C "{repo}" worktree remove "{path}"')
    sug = suggestions(top_rows, agent_rows, now, a.old_days, live_dirs)
    print(f'\nSuggested cleanup (nothing was deleted; review, then run what you agree with):')
    if not sug:
        print('  nothing obvious')
    for b, text in sug:
        print(f'  {fmt_gb(b)}  {text}')
    print(f'  potential total: {fmt_gb(sum(b for b, _ in sug)).strip()} (upper bound; entries do not overlap)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
