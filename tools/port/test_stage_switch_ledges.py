"""Run real BF/YS archive ledge fixtures without saving disc data or launching game."""
from pathlib import Path
import re
import subprocess
import sys
from test_stage_switch import ROOT, OUT, compile_test
sys.path.insert(0, str(ROOT / 'tools/mex_port'))
from mex_hsd import Gcm

def function(source, name):
    start = source.index(name + '(')
    start = source.rfind('\n', 0, start) + 1
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    mplib = (ROOT / 'melee/src/melee/mp/mplib.c').read_text()
    mpcoll = (ROOT / 'melee/src/melee/mp/mpcoll.c').read_text()
    (OUT / 'stage_ledge_retail.inc').write_text(function(mplib, 'mpLib_80051BA8_Floor') + function(mpcoll, 'mpColl_80044164') + function(mpcoll, 'mpColl_800443C4'))
    exe = OUT / 'stage_ledge_search_test.exe'
    compile_test(ROOT / 'melee/pc/tests/stage_ledge_search_test.c', exe, ['/I' + str(OUT)])
    env = (ROOT / '.env').read_text()
    path = re.search(r'^export GW_ISO_VANILLA="([^"]+)"', env, re.M)[1]
    disc = Gcm(path)
    for file in ['GrNBa.dat', 'GrSt.dat']:
        result = subprocess.run([str(exe)], input=disc.read(file), capture_output=True, check=True)
        print(file + ': ' + result.stdout.decode().strip())
