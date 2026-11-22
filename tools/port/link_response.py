#!/usr/bin/env python3
"""Regenerate a lane response list from the curated baseline, never glob objects."""
import argparse
from pathlib import Path
import os


def absent_tu_objects(workspace, melee):
    """Objects of listed game TUs whose source this tree lacks (an older or newer branch)."""
    if melee is None:
        return set()
    names = (workspace / '_build/masstest/files.txt').read_text().splitlines()
    return {'masstest/out/' + n.strip().replace('/', '_') + '.obj'
            for n in names if n.strip() and not (melee / n.strip()).exists()}


def response_text(workspace, build, melee=None):
    workspace, build = Path(workspace), Path(build)
    skip = absent_tu_objects(workspace, melee)
    entries = []
    for line in (workspace / '_build/melee_link_objects.rsp').read_text().splitlines():
        entry = line.strip().strip('"').replace('\\', '/')
        if not entry:
            continue
        if not entry.startswith('../masstest/'):
            raise ValueError(f'Unexpected baseline response entry: {entry}')
        if entry.removeprefix('../') in skip:
            continue
        obj = build / entry.removeprefix('../')
        entries.append('"' + obj.resolve().as_posix() + '"')
    return '\n'.join(entries) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--build-root', required=True, type=Path)
    parser.add_argument('--melee', type=Path, default=os.environ.get('GW_MELEE') or None)
    args = parser.parse_args()
    target = args.build_root / 'melee_link_objects.rsp'
    if target.resolve() == (args.root / '_build/melee_link_objects.rsp').resolve():
        return  # preserve the curated shared input
    content = response_text(args.root.resolve(), args.build_root.resolve(),
                            Path(args.melee).resolve() if args.melee else None)
    if not target.exists() or target.read_text() != content:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(f'.rsp.{os.getpid()}.tmp')
        temporary.write_text(content)
        temporary.replace(target)


if __name__ == '__main__':
    main()
