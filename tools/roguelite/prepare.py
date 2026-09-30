#!/usr/bin/env python3
"""Bundle pure modules with runtime into the offline TBD mod. Art is supplied separately."""
import argparse
import json
from pathlib import Path
import shutil
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite'
ROOM_KIT = ROOT / 'menu/out_roguelite/room-kit'

def install_room_kit(mod):
    required = ('bf_floor_4m', 'bf_floor_end_trim', 'bf_wall_solid_4m',
                'bf_beam_4m', 'bf_rear_post_4m', 'bf_wall_doorway_4m')
    names = [name + suffix for name in required for suffix in ('.gxmesh', '.coll.json')]
    names += ['bf_kit.gxtex', 'bf_kit.glow.gxtex']
    missing = [name for name in names if not (ROOM_KIT / name).is_file()]
    if missing:
        raise FileNotFoundError('Regenerate the BF room kit before installation: ' + ', '.join(missing))
    destination = mod / 'models'
    destination.mkdir(exist_ok=True)
    for name in names:
        shutil.copyfile(ROOM_KIT / name, destination / name)

def bundle(source=SOURCE):
    chunks = []
    for name, local in [('core', 'Core'), ('rng', 'Rng'), ('codec', 'Codec'), ('room_catalogue', 'RoomCatalogue'), ('encounter_catalogue', 'EncounterCatalogue'), ('progression', 'Progression'), ('checkpoint', 'Checkpoint'), ('topology', 'Topology'), ('legacy', 'Legacy'), ('dungeon', 'Dungeon'), ('commands', 'Commands'), ('roster', 'Roster'), ('bindings', 'Bindings'), ('visuals', 'Visuals'), ('feedback', 'Feedback'), ('menus', 'Menus'), ('rooms', 'Rooms'), ('enemy_genes', 'EnemyGenes'), ('technical_ai', 'TechAI')]:
        chunks.append(f'local {local} = (function()\n{(source / (name + ".lua")).read_text()}\nend)()\n')
    chunks.append((source / 'main.lua').read_text())
    return '\n'.join(chunks)

def install(app, enable=False, restore=False, demo=False):
    app = Path(app).resolve()
    mods = app / 'mods'
    mods.mkdir(parents=True, exist_ok=True)
    enabled, backup = mods / 'enabled.txt', mods / 'roguelite-enabled.backup'
    if restore:
        if backup.exists():
            shutil.copyfile(backup, enabled)
        return
    # Read the whole bundle before creating an incomplete installed mod.
    script = bundle()
    mod = mods / 'roguelite'
    (mod / 'scripts').mkdir(parents=True, exist_ok=True)
    (mod / 'scripts/main.lua').write_text(script)
    (mod / 'mod.json').write_text(json.dumps({
        'id': 'roguelite', 'name': 'TBD: Genes and Routes', 'version': '0.1.0',
        'author': 'GD', 'kind': 'script', 'api_version': 1, 'gameplay': True,
        'rollback_safe': False, 'entry': 'scripts/main.lua'}, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('roguelite_effect_recipes', ROOT / 'tools/effects_lab/recipes.py')
    recipes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recipes)
    recipes.build(mod)
    spec = importlib.util.spec_from_file_location('roguelite_fx_assets', ROOT / 'tools/roguelite/fx_assets.py')
    fx_assets = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fx_assets)
    fx_assets.build(mod)
    spec = importlib.util.spec_from_file_location('roguelite_room_assets', ROOT / 'tools/roguelite/room_assets.py')
    room_assets = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(room_assets)
    room_assets.build(mod)
    install_room_kit(mod)
    art = ROOT / 'menu/out_roguelite'
    metadata = json.loads((art / 'manifest.json').read_text())
    (mod / 'ui').mkdir(exist_ok=True)
    textures = []
    for texture in metadata['textures']:
        shutil.copyfile(art / 'gx' / (texture['name'] + '.gxtex'), mod / 'ui' / (texture['name'] + '.gxtex'))
        textures.append({'name': texture['name'], 'size_1x': texture['size_1x'], 'tint': 'bone'})
    (mod / 'ui/roguelite_ui.json').write_text(json.dumps({'textures': textures}, indent=2) + '\n')
    (mod / 'ui/kit.json').unlink(missing_ok=True)  # superseded metadata authored by this installer
    data = app / 'scripts-data/roguelite_main'
    data.mkdir(parents=True, exist_ok=True)
    (data / 'config.txt').write_text('demo=' + str(demo).lower() + '\n')
    if enable:
        if not backup.exists():
            backup.write_text(enabled.read_text() if enabled.exists() else '')
        enabled.write_text('roguelite\n')
    return mod

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app-dir', type=Path, default=ROOT / '_build/agents/linux')
    p.add_argument('--enable', action='store_true')
    p.add_argument('--restore', action='store_true')
    p.add_argument('--demo', action='store_true', help='Launch the TBD collection automatically for review')
    args = p.parse_args()
    print(install(args.app_dir, args.enable, args.restore, args.demo))

if __name__ == '__main__':
    main()
