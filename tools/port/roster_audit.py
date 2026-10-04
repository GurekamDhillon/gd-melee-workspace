#!/usr/bin/env python3
"""Mechanical roster limit census; no discs, builds, or generated bridge reads.

Emits every old-constant reference, transitively derived macro and array extent,
plus byte-id declarations/comparisons and literal bounds in roster consumers.
This is a review inventory, not a proof that arbitrary numeric bounds are absent.
"""
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
SEEDS={'GW_MEX_SLOT_COUNT','FT_MEX_SLOT_COUNT','GW_MEX_CSS_ICON_MAX',
       'CSS_ICON_MAX','GENO_MAX_PROFILES','Ft_Kind_Max','ChKind_Cap',
       'GW_FTFUNC_KIND_MAX','FS_MAX_FIGHTERS','FE_NP_MAX_CK'}


def census():
    files=[]
    for base in ('melee/pc/platform','melee/pc/gameworld','melee/pc/geno','melee/src/melee'):
        for path in sorted((ROOT/base).rglob('*')):
            if path.suffix in ('.c','.h','.inc','.cpp') and path.name!='gw_mex_bridge.c':
                files.append((path,path.read_text(encoding='utf-8',errors='replace').splitlines()))
    constants=set(SEEDS)
    changed=True
    while changed:
        changed=False
        for _,lines in files:
            for line in lines:
                m=re.match(r'\s*#\s*define\s+(\w+)\s+(.+)',line)
                if m and m[1] not in constants and set(re.findall(r'\b\w+\b',m[2]))&constants:
                    constants.add(m[1]);changed=True
    out=[]
    for path,lines in files:
        for i,line in enumerate(lines,1):
            words=set(re.findall(r'\b\w+\b',line))
            reason=None
            if words&constants:reason='constant'
            if '[' in line and words&constants:reason='array/bounds'
            if re.search(r'\b(s8|u8|int8_t|uint8_t)\b',line) and re.search(r'kind|char|fighter|profile',line,re.I):reason='byte id'
            if re.search(r'kind|ckind|fighter|profile|icon',line,re.I) and re.search(r'\b(32|64|94|127|128|255|256)\b',line):reason=reason or 'literal bound'
            if re.search(r'(ckind|char_kind|fighter_kind)\s*(<\s*0|==\s*-1)',line):reason='signed sentinel'
            if reason:out.append({'file':path.relative_to(ROOT).as_posix(),'line':i,
                                  'reason':reason,'source':line.strip()})
    return {'constants':sorted(constants),'entries':out}


def main():
    result=census();dest=ROOT/'_build/tmp';dest.mkdir(parents=True,exist_ok=True)
    (dest/'roster-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    rows=['# Mechanical roster census','', 'Source references; no game executed.', '',
          '| Location | Classification | Source |','|---|---|---|']
    rows.extend(f"| {e['file']}:{e['line']} | {e['reason']} | `{e['source'].replace('|',' / ')}` |"
                for e in result['entries'])
    (dest/'roster-audit.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    print(f"Roster census: {len(result['constants'])} constants, {len(result['entries'])} references; "
          "_build/tmp/roster-audit.md")


if __name__=='__main__':main()
