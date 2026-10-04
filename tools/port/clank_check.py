"""Standalone clank checks: no game build/launch; x86 MSVC and Dawn Null."""
from pathlib import Path
import os, subprocess, sys, uuid
ROOT=Path(__file__).resolve().parents[2]
MELEE=ROOT/'melee';OUT=ROOT/'_build/tmp/clank-check';OUT.mkdir(parents=True,exist_ok=True)
vs=Path(os.environ.get('GW_SHADER_MSVC','C:/Program Files/Microsoft Visual Studio/18/Community/VC/Tools/MSVC/14.51.36231'))
sdk=Path('C:/Program Files (x86)/Windows Kits/10');v='10.0.26100.0'
env=os.environ.copy();compiler=vs/'bin/Hostx64/x86/cl.exe'
env['INCLUDE']=';'.join(str(p) for p in [vs/'include',*[sdk/'Include'/v/x for x in ('ucrt','shared','um')]])
env['LIB']=';'.join(str(p) for p in [vs/'lib/x86',sdk/'Lib'/v/'ucrt/x86',sdk/'Lib'/v/'um/x86'])
env['PATH']=str(compiler.parent)+';'+str(ROOT/'_build')+';'+env['PATH']
def run(cmd):subprocess.run([str(x) for x in cmd],cwd=OUT,env=env,check=True)
for name in ('clank_presentation_test','clank_event_test'):
 run([compiler,'/nologo','/TC','/std:c11',MELEE/'pc/tests'/f'{name}.c','/Fo'+str(OUT/f'{name}.obj'),'/Fe'+str(OUT/f'{name}.exe')]);run([OUT/f'{name}.exe'])
run([compiler,'/nologo','/TC','/std:c11',MELEE/'pc/tests/clank_presentation_api_test.c',MELEE/'pc/platform/gw_lua.c','/Fo'+str(OUT)+'/', '/Fe'+str(OUT/'lua-api.exe')]);run([OUT/'lua-api.exe'])
if '--shader' in sys.argv:
 includes=[MELEE/'pc/platform',MELEE/'extern/aurora/include',ROOT/'_build/ax86/_deps/dawn-src/include',ROOT/'_build/ax86m/_deps/dawn-build/gen/include']
 run([compiler,'/nologo','/std:c++20','/EHsc','/MD','/Gy','/Gw','/DWEBGPU_DAWN',*['/I'+str(p) for p in includes],MELEE/'pc/tests/clank_shader_test.cpp','/Fo'+str(OUT/'shader.obj'),'/Fe'+str(OUT/'shader.exe'),'/link','/OPT:REF','ole32.lib',ROOT/'_build/ax86m/_deps/dawn-build/src/dawn/native/webgpu_dawn.lib'])
 fixture=OUT/('fixture-'+uuid.uuid4().hex);inside=fixture/'root';outside=fixture/'outside';inside.mkdir(parents=True);outside.mkdir()
 (inside/'good.wgsl').write_text('return vec4f(1.0);');(outside/'stolen.wgsl').write_text('return vec4f(0.0);')
 run(['cmd','/c','mklink','/J',inside/'junction',outside])
 run([OUT/'shader.exe',MELEE/'pc/geno/mods/shader-demo',inside,ROOT/'experiment/clank_impact'])
