#!/usr/bin/env python3
"""Capture installed effects with the existing engine in a separate test profile."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from showcase import ROOT, BUILD, CATALOGUE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso',type=Path,required=True)
    parser.add_argument('--port',type=int,default=51700)
    args=parser.parse_args()
    profile=ROOT/'_build/effects-tour-profile'
    mod=profile/'mods/effects_tour'
    (mod/'scripts').mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'tools/effects_lab/capture_tour.lua',mod/'scripts/main.lua')
    (mod/'mod.json').write_text(json.dumps(dict(id='effects_tour',name='Native Effects Catalogue',version='1.0.0',author='GD',kind='script',api_version=1,gameplay=True,rollback_safe=False,entry='scripts/main.lua')))
    for package,*_ in CATALOGUE:
        paths=list((BUILD/'mods').glob('*/fx/'+package))
        if not paths: raise FileNotFoundError('Installed effect package missing: '+package)
        shutil.copytree(paths[0],mod/'fx'/package,dirs_exist_ok=True)
    (profile/'mods/enabled.txt').write_text('effects_tour\n')
    (profile/'settings.cfg').write_text('onboarded=1\n')
    data=profile/'data/effects_tour_main'
    # Eliminate stale evidence if the engine fails before a new capture completes.
    data.mkdir(parents=True,exist_ok=True)
    for p in data.glob('*.png'): p.unlink()
    for name in ('complete.txt','evidence.tsv'):
        (data/name).unlink(missing_ok=True)
    env=os.environ.copy()
    env.update(MELEE_MODS_DIR=str(profile/'mods'),MELEE_SCRIPT_DATA_DIR=str(profile/'data'),
               MELEE_CARD_PATH=str(profile/'card'),MELEE_SETTINGS_CFG=str(profile/'settings.cfg'),
               MELEE_CONSOLE_PORT=str(args.port),MELEE_FPS='60',MELEE_WINDOW_W='1280',
               MELEE_WINDOW_H='960',MELEE_RENDER_SCALE='2')
    if os.name == 'nt':
        bash=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Git/bin/bash.exe'
        env['GW_BUILD_ROOT']=str(BUILD)
        command=[str(bash), str(ROOT/'tools/port/run.sh'), 'effects-tour-'+uuid.uuid4().hex[:10],
                 '--iso',str(args.iso.resolve())]
    else:
        command=[str(BUILD/'melee'),'--iso',str(args.iso.resolve())]
    result=subprocess.run(command,env=env,cwd=ROOT)
    if result.returncode: raise SystemExit(result.returncode)
    if not (data/'complete.txt').exists(): raise RuntimeError('Native sweep did not complete')
    for package,*_ in CATALOGUE:
        if not (data/(package+'.png')).exists(): raise RuntimeError('Missing native capture: '+package)
    print(data)

if __name__=='__main__': main()
