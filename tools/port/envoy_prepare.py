"""Prepare an Envoy folder using explicitly supplied, existing authored room-kit assets."""
import argparse
import importlib.util
from pathlib import Path
import os
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
MELEE = Path(os.environ.get('GW_MELEE') or ROOT / 'melee').expanduser().resolve()
SOURCE=MELEE/'pc/scripts/examples/envoy'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def bundle():
    return load('envoy_bundle',Path(__file__).with_name('envoy_bundle.py')).bundle()

def prepare(output,kit):
    output=Path(output).resolve();kit=Path(kit).resolve()
    if output.exists():
        raise FileExistsError('Choose a new output folder; existing folders are preserved')
    if output==SOURCE.resolve() or SOURCE.resolve() in output.parents:
        raise ValueError('Prepare into a local output folder, not the source mod')
    parts=['bf_floor_4m']
    parts += [name for name in ('bf_wall_solid_4m','bf_wall_doorway_4m','bf_door_leaf','bf_beam_4m') if (kit/(name+'.gxmesh')).is_file()]
    assets=load('maze_generate',ROOT/'tools/maze/generate.py').kit_files(kit,parts)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.envoy-',dir=output.parent) as temp:
        stage=Path(temp)/'complete'
        shutil.copytree(SOURCE,stage,ignore=shutil.ignore_patterns('data','models','__pycache__'))
        bundled=load('envoy_bundle',Path(__file__).with_name('envoy_bundle.py'))
        (stage/'scripts/main.lua').write_bytes(bundled.bundle().encode('utf-8'))
        import json
        (stage/'items/drive/item.json').write_bytes((json.dumps(bundled.drive_definition(),indent=2)+'\n').encode('utf-8'))
        # Root models serve the optional garden placeholder; mission meshes
        # use the engine's missions/ listing scope.
        folders=['models','missions/models']+[str(p.relative_to(stage)/'models') for p in (stage/'missions').iterdir() if p.is_dir()]
        for folder in folders:
            target=stage/folder;target.mkdir(parents=True,exist_ok=True)
            for name,data in assets.items():(target/name).write_bytes(data)
        stage.rename(output)
    return output

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(prepare(args.output,args.kit))

if __name__=='__main__':main()
