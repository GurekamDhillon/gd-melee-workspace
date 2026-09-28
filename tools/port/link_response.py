#!/usr/bin/env python3
"""Regenerate a lane response list from the curated baseline, never glob objects."""
import argparse
from pathlib import Path
import os


def response_text(workspace, build):
    workspace, build = Path(workspace), Path(build)
    entries = []
    for line in (workspace / '_build/melee_link_objects.rsp').read_text().splitlines():
        entry = line.strip().strip('"').replace('\\', '/')
        if not entry:
            continue
        if not entry.startswith('../masstest/'):
            raise ValueError(f'Unexpected baseline response entry: {entry}')
        obj = build / entry.removeprefix('../')
        try:
            relative = os.path.relpath(obj, workspace / '_build/ax86m')
        except ValueError:  # explicit build root on another drive
            relative = str(obj.resolve())
        entries.append('"' + relative.replace('\\', '/') + '"')
    return '\n'.join(entries) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--build-root', required=True, type=Path)
    args = parser.parse_args()
    target = args.build_root / 'melee_link_objects.rsp'
    if target.resolve() == (args.root / '_build/melee_link_objects.rsp').resolve():
        return  # preserve the curated shared input
    content = response_text(args.root.resolve(), args.build_root.resolve())
    if not target.exists() or target.read_text() != content:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(f'.rsp.{os.getpid()}.tmp')
        temporary.write_text(content)
        temporary.replace(target)


if __name__ == '__main__':
    main()
