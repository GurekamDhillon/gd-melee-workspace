#!/usr/bin/env python3
"""Install the offline part lab beside a local build; never modifies the ISO."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import sys
import uuid
from make_presets import build

ROOT=Path(__file__).resolve().parents[2]
CHECKOUT=Path(os.environ.get('GW_MELEE', ROOT/'melee')).expanduser().resolve()
ROSTER={'falco':'Fc','mario':'Mr','kirby':'Kb','pikachu':'Pk','bowser':'Kp','marth':'Ms','link':'Lk','gamewatch':'Gw',
 'fox':'Fx','captain':'Ca','donkey':'Dk','luigi':'Lg','samus':'Ss','ness':'Ns','peach':'Pe','yoshi':'Ys','popo':'Pp',
 'sheik':'Sk','zelda':'Zd','pichu':'Pc','drmario':'Dr','roy':'Fe','ganondorf':'Gn','mewtwo':'Mt','jigglypuff':'Pr','younglink':'Cl'}

def costume_files():
    """Use the same authored stock ordering as the engine, including accessory costumes."""
    result={}
    for source in (CHECKOUT/'src/melee/ft/kinds').glob('*/*.c'):
        text=source.read_text()
        strings=dict(re.findall(r'char\s+(\w+)\[\]\s*=\s*"([^"]+)"',text))
        for code,body in re.findall(r'Fighter_CostumeStrings\s+ft(\w+)_Init_CostumeStrings\[\]\s*=\s*\{(.*?)\n\};',text,re.S):
            names=[]
            for symbol in re.findall(r'\{\s*(\w+)\s*,',body):
                name=strings.get(symbol)
                if name is None:raise ValueError('Unresolved costume filename: '+symbol)
                names.append(name+'dat' if name.endswith('.') else name)
            result[code]=names
    return result

def literal(value):
    if isinstance(value,bool):return 'true' if value else 'false'
    if isinstance(value,str):return json.dumps(value)
    if isinstance(value,(int,float)):return str(value)
    if isinstance(value,list):return '{'+','.join(map(literal,value))+'}'
    return '{'+','.join('['+literal(k)+']='+literal(v) for k,v in value.items())+'}'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app-dir',type=Path,default=Path(os.environ.get('GW_BUILD_ROOT', ROOT/'_build')))
    p.add_argument('--iso',type=Path)
    p.add_argument('--fighters',default='falco')
    p.add_argument('--roster',action='store_true');p.add_argument('--quick',action='store_true')
    p.add_argument('--interactive',action='store_true');p.add_argument('--restore',action='store_true')
    p.add_argument('--no-scan',action='store_true',help='Open the live panel without capturing the model again')
    p.add_argument('--showcase',action='store_true',help='Rotate seven FX presets and save a screenshot of each')
    p.add_argument('--rainbow',action='store_true',help='Start the live panel with independent animated colours on every part')
    p.add_argument('--costume',type=int,default=0,help='Stock costume index; scanned independently from other costumes')
    p.add_argument('--list-costumes',action='store_true')
    args=p.parse_args();app=args.app_dir.resolve();mods=app/'mods'
    enabled=mods/'enabled.txt';backup=mods/'parts-lab-enabled.backup'
    if args.restore:
        if backup.exists():shutil.copyfile(backup,enabled)
        return
    fighters=list(ROSTER) if args.roster else args.fighters.split(',')
    if any(f not in ROSTER for f in fighters):p.error('Unknown stock fighter alias')
    costumes=costume_files()
    if args.list_costumes:
        for f in fighters:print(f+': '+', '.join(str(i)+'='+name for i,name in enumerate(costumes[ROSTER[f]])))
        return
    if args.iso is None:p.error('--iso is required to fingerprint the scanned assets')
    if args.no_scan and not args.interactive:p.error('--no-scan requires --interactive')
    if args.rainbow and (not args.interactive or args.showcase):p.error('--rainbow requires --interactive and cannot combine with --showcase')
    sys.path.insert(0,str(ROOT/'tools/mex_port'))
    from mex_hsd import Gcm
    disc=Gcm(args.iso)
    assets={}
    for f in fighters:
        files=costumes[ROSTER[f]]
        if not 0<=args.costume<len(files):p.error(f'{f} has costume indices 0..{len(files)-1}')
        assets[f]=hashlib.sha256(disc.read(files[args.costume])).hexdigest()
    mod=mods/'character_parts_lab';(mod/'scripts').mkdir(parents=True,exist_ok=True)
    source=CHECKOUT/'pc/scripts/examples/character_parts_lab/main.lua'
    shutil.copyfile(source,mod/'scripts/main.lua')
    (mod/'mod.json').write_text(json.dumps({'id':'character_parts_lab','name':'Character parts and shader lab','version':'1.0.0',
      'author':'GD','kind':'script','api_version':1,'gameplay':True,'rollback_safe':False,'entry':'scripts/main.lua'},indent=2)+'\n')
    build(mod)
    if not backup.exists() and enabled.exists():shutil.copyfile(enabled,backup)
    enabled.write_text('character_parts_lab\n')
    data=app/'scripts-data/character_parts_lab_main';data.mkdir(parents=True,exist_ok=True)
    if (data/'batch-done.json').exists():(data/'batch-done.json').unlink()
    config={'fighters':fighters,'batch':not args.interactive,'autoscan':not args.no_scan,'quick':args.quick,'assets':assets,'showcase':args.showcase,'costume':args.costume,'rainbow':args.rainbow,'run_id':uuid.uuid4().hex}
    (data/'config.lua').write_text('return '+literal(config)+'\n')
    print('Installed:',mod);print('Reports:',data);print('Fighters:',','.join(fighters))
    print('Launch the executable with --iso, then run analyze.py on the reports directory.')
if __name__=='__main__':main()
