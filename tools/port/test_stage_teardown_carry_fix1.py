"""Stream retail collision fixtures; extract the actual continuous carry body."""
import re
import struct
import subprocess
import sys
from test_stage_switch import ROOT, OUT, compile_test
from test_stage_switch_fix3 import function

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'stage_carry_fix1_retail.inc').write_text(
        (ROOT/'melee/pc/gameworld/script_stage_slot_carry.inc').read_text())
    (OUT/'stage_detach_fix1_retail.inc').write_text(function(
        (ROOT/'melee/pc/gameworld/script_stage_slots.inc').read_text(),'script_switch_detach'))
    exe=OUT/'stage_carry_fix1_test.exe'
    compile_test(ROOT/'melee/pc/tests/stage_carry_fix1_test.c',exe,
                 ['/I'+str(OUT),'/I'+str(ROOT/'melee/pc/gameworld')])
    sys.path.insert(0,str(ROOT/'tools/mex_port'))
    from mex_hsd import Gcm
    path=re.search(r'^export GW_ISO_VANILLA="([^"]+)"',(ROOT/'.env').read_text(),re.M)[1]
    disc=Gcm(path)
    payload=b''
    for name in ['GrNLa.dat','GrNBa.dat','GrSt.dat','GrOp.dat','GrIz.dat']:
        data=disc.read(name);payload+=struct.pack('<I',len(data))+data
    result=subprocess.run([str(exe)],input=payload,capture_output=True,timeout=15)
    print(result.stdout.decode().strip())
    if result.returncode:
        print(result.stderr.decode().strip())
        raise SystemExit(result.returncode)
