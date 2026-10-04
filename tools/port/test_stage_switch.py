"""Standalone stage-switch fixtures. Compiles tests only, never the game."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_build/tmp/stage-switch-tests'

def compile_test(source, output, extra=(), language='c'):
    vc = Path('C:/Program Files/Microsoft Visual Studio/18/Community/VC/Tools/MSVC/14.51.36231')
    sdk = Path('C:/Program Files (x86)/Windows Kits/10')
    version = '10.0.26100.0'
    env = os.environ.copy()
    env['PATH'] = str(vc / 'bin/Hostx64/x64') + os.pathsep + env['PATH']
    args = [str(vc / 'bin/Hostx64/x64/cl.exe'), '/nologo',
            '/TP' if language=='cpp' else '/TC',
            '/std:c++17' if language=='cpp' else '/std:c11', '/W3',
            '/I' + str(vc / 'include'), '/I' + str(sdk / 'Include' / version / 'ucrt'),
            '/I' + str(sdk / 'Include' / version / 'shared'),
            '/I' + str(sdk / 'Include' / version / 'um'), str(source),
            '/Fo' + str(output.with_suffix('.obj')), '/Fe' + str(output), *extra,
            '/link', '/LIBPATH:' + str(vc / 'lib/x64'),
            '/LIBPATH:' + str(sdk / 'Lib' / version / 'ucrt/x64'),
            '/LIBPATH:' + str(sdk / 'Lib' / version / 'um/x64')]
    subprocess.run(args, cwd=OUT, env=env, check=True)

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ['stage_dat_test', 'stage_queue_test', 'stage_slots_test']:
        exe = OUT / (name + '.exe')
        compile_test(ROOT / 'melee/pc/tests' / (name + '.c'), exe)
        subprocess.run([str(exe)], check=True)
