"""Materialize the pure Lua maze as an ordinary mission folder; no engine calls.

python tools/maze/generate.py 7 --size 12 --kit menu/out_roguelite/room-kit \
    --output _build/tmp/maze-mod --prepare-mod
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'melee/pc/scripts/examples/missions/scripts'


def safe_name(name):
    if not name or len(name) > 64 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
        raise ValueError('Unsafe mission name')


def generate(seed, size=12, name='generated', length=None, loops=True, boss=False, library=None):
    """Return mounted-mod-relative file bytes, produced by the Lua implementation."""
    safe_name(name)
    command = [shutil.which('lua') or 'lua', 'tools/maze/emit.lua',
                             str(seed), str(size), name, str('' if length is None else length),
                             'loops' if loops else 'no-loops', 'boss' if boss else '']
    if library is not None:
        command.append(str(Path(library).resolve()))
    return emitted(command)


def emitted(command):
    result = subprocess.run(command,
                            cwd=ROOT, capture_output=True, timeout=60)
    if result.returncode:
        raise ValueError(result.stderr.decode('utf-8', errors='replace'))
    # Windows text stdout translates LF to CRLF. Lengths count pre-translation
    # bytes; output is ASCII Lua data, so normalize the transport first.
    output = result.stdout.replace(b'\r\n', b'\n')
    files = {}
    while output:
        header, output = output.split(b'\n', 1)
        path, size_text = header.decode('ascii').split('\t')
        count = int(size_text)
        if count > len(output):
            raise ValueError('Truncated Lua output')
        files[path], output = output[:count], output[count:]
    return files


def world(seed, regions=4, size=12, name='world', library=None, reroll_region=None, region_seed=None):
    """Generate one continuous world through the same Lua implementation."""
    safe_name(name)
    if (reroll_region is None) != (region_seed is None):
        raise ValueError('Both reroll_region and region_seed are required')
    if reroll_region is not None and not 1 <= reroll_region <= regions:
        raise ValueError('Reroll region is outside the world')
    command = [shutil.which('lua') or 'lua', 'tools/maze/emit.lua', 'world', str(seed),
               str(regions), str(size), name, '', str(Path(library).resolve()) if library else '']
    if reroll_region is not None:
        command += [str(reroll_region), str(region_seed)]
    return emitted(command)


def starters():
    return generate('starter')


def kit_files(kit, parts=('bf_floor_4m',)):
    kit = Path(kit)
    names = set()
    for part in parts:
        safe_name(part)
        names.update((part + '.gxmesh', part + '.coll.json'))
        sidecar = json.loads((kit / (part + '.coll.json')).read_text(encoding='utf-8'))
        for key in ('atlas', 'glow'):
            name = sidecar.get(key)
            if name:
                safe_name(name)
                names.add(name + '.gxtex')
                if key == 'atlas' and (kit / (name + '.glow.gxtex')).is_file():
                    names.add(name + '.glow.gxtex')
    return {name: (kit / name).read_bytes() for name in sorted(names)}


def materialize(files, output, kit, name, prepare_mod=False):
    """Stage a complete folder before publishing; never modifies source assets."""
    safe_name(name)
    output = Path(output).resolve()
    prefix = 'missions/' + name + '/'
    assets = kit_files(kit, files.get('maze-assets.txt', b'bf_floor_4m\n').decode('ascii').splitlines())
    target = output / 'missions' / name
    if prepare_mod and output.exists() and any(output.iterdir()):
        raise FileExistsError('Preparing a mod requires an empty output directory')
    if target.exists():
        raise FileExistsError(f'Refusing to overwrite {target}; choose a new output/name')
    publication = {path: data for path, data in files.items() if path.startswith(prefix)}
    publication[prefix + 'maze-map.txt'] = files['maze-map.txt']
    for asset, data in assets.items():
        publication[prefix + 'models/' + asset] = data
    if prepare_mod:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from tools.port.missions_bundle import bundle
        publication['scripts/main.lua'] = bundle().encode('utf-8')
        publication['mod.json'] = (SCRIPTS.parent / 'mod.json').read_bytes()
        publication.update(starters())
        if 'missions/maze-chunks/library.lua' in files:
            publication['missions/maze-chunks/library.lua'] = files['missions/maze-chunks/library.lua']
        for asset, data in assets.items():
            publication['missions/models/' + asset] = data
    destination = output if prepare_mod else target
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.maze-', dir=destination.parent) as temp:
        stage = Path(temp) / 'complete'
        for path, data in publication.items():
            relative = Path(path if prepare_mod else path[len(prefix):])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Unsafe generated path')
            staged = stage / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(data)
        if prepare_mod and output.exists():
            output.rmdir()  # Only the verified empty destination; no recursive deletion.
        stage.rename(destination)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('seed', type=int)
    parser.add_argument('--size', type=int, default=12)
    parser.add_argument('--length', type=int)
    parser.add_argument('--no-loops', action='store_true')
    parser.add_argument('--boss', action='store_true')
    parser.add_argument('--library', type=Path, help='Authored missions/maze-chunks/library.lua')
    parser.add_argument('--name', default='generated')
    parser.add_argument('--kit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepare-mod', action='store_true')
    args = parser.parse_args()
    files = generate(args.seed, args.size, args.name, args.length, not args.no_loops, args.boss, args.library)
    print(materialize(files, args.output, args.kit, args.name, args.prepare_mod))
    print(files['maze-map.txt'].decode('ascii'))


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    main()
