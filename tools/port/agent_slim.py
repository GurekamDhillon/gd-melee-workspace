"""End-of-lane cleanup of ONE agent build root: delete the bulk, keep the evidence.

    python tools/port/agent_slim.py <name>          # dry run: list what would go and how much
    python tools/port/agent_slim.py <name> --yes    # do it

Acts only inside _build/agents/<name>. Keeps logs, text/JSON/Markdown results, crashlogs/,
results/ and scripts-data directories, perf.json, and the .map files (crash RVAs); deletes the
rest (exe/dll copies, objects, caches). Junctions are unlinked, never followed. Refuses while a
melee-pc.exe runs from inside the root. To remove the root entirely use tools/port/agent_rm.sh.
"""
import argparse
import os
from pathlib import Path
import shutil
import stat
import sys

KEEP_SUFFIXES = ('.log', '.md', '.json', '.txt', '.map', '.csv', '.tsv')
KEEP_DIRS = ('crashlogs', 'results', 'scripts-data')
REPARSE = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)


def is_link(path):
    st = os.lstat(path)
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, 'st_file_attributes', 0) & REPARSE)


def keep(rel_parts):
    """True when a file at this path (relative to the root) is evidence."""
    if any(p.lower() in KEEP_DIRS for p in rel_parts[:-1]):
        return True
    return rel_parts[-1].lower().endswith(KEEP_SUFFIXES)


def plan(root):
    """Return (files_to_delete, links_to_unlink, bytes). Pure scan; touches nothing."""
    root = Path(root)
    files, links, total = [], [], 0
    for dirpath, dirs, names in os.walk(root):
        for d in list(dirs):
            full = os.path.join(dirpath, d)
            if is_link(full):
                links.append(full)
                dirs.remove(d)
        for n in names:
            full = os.path.join(dirpath, n)
            rel = Path(full).relative_to(root).parts
            if is_link(full):
                links.append(full)
            elif not keep(rel):
                files.append(full)
                total += os.lstat(full).st_size
    return files, links, total


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('name')
    ap.add_argument('--yes', action='store_true')
    ap.add_argument('--agents', type=Path, default=Path(os.environ.get('GW_ROOT', Path(__file__).resolve().parents[2])) / '_build' / 'agents')
    a = ap.parse_args(argv)
    if not a.name.replace('-', '').replace('_', '').isalnum():
        print('name must be [A-Za-z0-9_-]+', file=sys.stderr)
        return 1
    root = (a.agents / a.name)
    if not root.is_dir() or root.resolve().parent != a.agents.resolve():
        print(f'no such agent root: {root}', file=sys.stderr)
        return 1
    sys.path.insert(0, str(Path(__file__).parent))
    import prune_runs
    live = prune_runs.live_games()
    if live is None:
        print('refusing: running games could not be listed', file=sys.stderr)
        return 1
    rn = prune_runs.normalized(root) + '/'
    if any(prune_runs.normalized(p).startswith(rn) for p in live):
        print('refusing: a game is running from this root', file=sys.stderr)
        return 1
    files, links, total = plan(root)
    print(f'{root}: {len(files)} files ({total / 2**20:.0f} MB) and {len(links)} links to remove')
    if not a.yes:
        print('dry run; pass --yes to delete')
        return 0
    for f in files:
        os.chmod(f, stat.S_IWRITE)
        os.unlink(f)
    for l in links:
        try:
            os.unlink(l)
        except OSError:
            os.rmdir(l)  # a directory junction: removes the link only
    for dirpath, _, _ in os.walk(root, topdown=False):
        try:
            os.rmdir(dirpath)  # only succeeds when empty
        except OSError:
            pass
    print('done')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
