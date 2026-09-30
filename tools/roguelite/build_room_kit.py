#!/usr/bin/env python3
"""Rebuild our original BF modular room assets without modifying editor scripts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / 'melee/worktrees/linux'


def build(blender, output, texture_size=1024, samples=48):
    output = Path(output)
    with tempfile.TemporaryDirectory(prefix='roguelite-room-kit-') as scratch:
        scratch = Path(scratch)
        editor = scratch / 'editor.lua'
        shutil.copyfile(NATIVE / 'pc/scripts/examples/map_editor/scripts/main.lua', editor)
        models = scratch / 'models'
        subprocess.run([
            blender, '--factory-startup', '--background', '--python',
            str(NATIVE / 'pc/assets_src/bf_interior/export_kit.py'), '--',
            '--output', str(models), '--editor', str(editor),
            '--texture-size', str(texture_size), '--samples', str(samples),
        ], check=True, cwd=ROOT)
        files = []
        output.mkdir(parents=True, exist_ok=True)
        for path in sorted(models.iterdir()):
            if path.suffix not in ('.gxmesh', '.gxtex', '.json', '.png'):
                continue
            raw = path.read_bytes()
            shutil.copyfile(path, output / path.name)
            files.append(dict(name=path.name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        if not files:
            raise RuntimeError('BF exporter produced no assets')
        (output / 'manifest.json').write_text(json.dumps(dict(
            version=1, authoring_source='melee/worktrees/linux/pc/assets_src/bf_interior/export_kit.py',
            unit=6.5, texture_size=texture_size, samples=samples, files=files,
        ), indent=2) + '\n')
    print(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', default=shutil.which('blender') or 'blender')
    parser.add_argument('--output', type=Path, default=ROOT / 'menu/out_roguelite/room-kit')
    parser.add_argument('--texture-size', type=int, default=1024)
    parser.add_argument('--samples', type=int, default=48)
    args = parser.parse_args()
    build(args.blender, args.output, args.texture_size, args.samples)


if __name__ == '__main__':
    main()
