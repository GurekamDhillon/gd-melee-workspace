#!/usr/bin/env python3
"""Compile/run standalone roster tests using discovered MSVC; never build/run the game.

All test inputs are synthetic. Compiler locations are discovered and never logged.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import roster_stress

ROOT=Path(__file__).resolve().parents[2]


def main():
    base=Path(os.environ.get('ProgramFiles',''))
    kits=Path(os.environ.get('ProgramFiles(x86)',''))/'Windows Kits/10'
    compilers=sorted(base.glob('Microsoft Visual Studio/*/*/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe'))
    sdks=sorted((kits/'Include').glob('*'))
    if not compilers or not sdks:
        print('roster checks: MSVC/Windows SDK unavailable');return 1
    compiler=compilers[-1];vc=compiler.parents[3];sdk=sdks[-1]
    out=ROOT/'_build/tmp/roster-registry-tests';out.mkdir(parents=True,exist_ok=True)
    fixture=roster_stress.native_manifest('Sonic',31,30,100,b'table',b'fighter',b'animation')
    (out/'catalog.gwr').write_bytes(fixture)
    mods=out/'mods';folder=mods/'sonic-test';folder.mkdir(parents=True,exist_ok=True)
    (folder/'roster.gwr').write_bytes(fixture)
    env=os.environ.copy();env['PATH']=str(compiler.parent)+os.pathsep+env.get('PATH','')
    results=[]
    for test in ('roster_registry','roster_catalog','roster_runtime'):
        output=out/(test+'.next.exe')
        args=[str(compiler),'/nologo','/TC','/std:c11','/W3',
              '/I'+str(vc/'include'),'/I'+str(sdk/'ucrt'),'/I'+str(sdk/'shared'),'/I'+str(sdk/'um'),
              f'melee/pc/tests/{test}_test.c','/Fo'+str(out/(test+'.obj')),
              '/Fe'+str(output),'/link','/LIBPATH:'+str(vc/'lib/x64'),
              '/LIBPATH:'+str(kits/'Lib'/sdk.name/'ucrt/x64'),
              '/LIBPATH:'+str(kits/'Lib'/sdk.name/'um/x64')]
        compiled=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True)
        if compiled.returncode:
            print(f'{test}: compilation failed (compiler diagnostics withheld to avoid host paths)');return 1
        command=[str(output)]
        if test=='roster_catalog':command.append(str((out/'catalog.gwr').relative_to(ROOT)))
        if test=='roster_runtime':command.append(str(mods.relative_to(ROOT)))
        executed=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=30)
        if executed.returncode:
            print(f'{test}: failed with exit {executed.returncode}');return 1
        print(executed.stdout.strip())
        output.replace(out/(test+'.exe'))
        results.append({'test':test,'result':'PASS','compiler':'MSVC C11 x64'})
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,subprocess.TimeoutExpired):
        print('roster checks: compiler/test execution unavailable');raise SystemExit(1)
