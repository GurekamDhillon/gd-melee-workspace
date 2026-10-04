#!/usr/bin/env python3
"""Generate/install original effects without touching enabled mods unless --enable is explicit."""
import argparse
import json
import os
from pathlib import Path
import shutil
import uuid
from recipes import build, VERSION
ROOT=Path(__file__).resolve().parents[2]
CHECKOUT=Path(os.environ.get('GW_MELEE', ROOT/'melee')).expanduser().resolve()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app-dir',type=Path,default=Path(os.environ.get('GW_BUILD_ROOT', ROOT/'_build')))
    p.add_argument('--enable',action='store_true');p.add_argument('--restore',action='store_true')
    playback=p.add_mutually_exclusive_group()
    playback.add_argument('--validate',action='store_true',help='Run nine capture/cleanup cases and quit')
    playback.add_argument('--loop',action='store_true',help='Start interactive playback looping')
    args=p.parse_args();app=args.app_dir.resolve();mods=app/'mods';mods.mkdir(parents=True,exist_ok=True)
    enabled=mods/'enabled.txt';backup=mods/'effects-lab-enabled.backup'
    if args.restore:
        if backup.exists():shutil.copyfile(backup,enabled)
        return
    mod=mods/'effects_lab';(mod/'scripts').mkdir(parents=True,exist_ok=True)
    shutil.copyfile(CHECKOUT/'pc/scripts/examples/effects_lab/main.lua',mod/'scripts/main.lua')
    (mod/'mod.json').write_text(json.dumps({'id':'effects_lab','name':'Parametric Effects Lab','version':'0.2.0','author':'GD','kind':'script','api_version':1,'gameplay':True,'rollback_safe':False,'entry':'scripts/main.lua'},indent=2)+'\n')
    build(mod)
    data=app/'scripts-data/effects_lab_main';data.mkdir(parents=True,exist_ok=True)
    run_id=uuid.uuid4().hex
    (data/'config.lua').write_text('return {validate=%s,loop=%s,recipe=%d,run_id="%s"}\n' %
        (str(args.validate).lower(),str(args.loop).lower(),VERSION,run_id))
    if args.validate:
        (data/'validation-done.txt').write_text('pending recipe=%d run=%s\n' % (VERSION,run_id))
    if args.enable:
        if not backup.exists():backup.write_text(enabled.read_text() if enabled.exists() else '')
        enabled.write_text('effects_lab\n')
    print(mod)
if __name__=='__main__':main()
