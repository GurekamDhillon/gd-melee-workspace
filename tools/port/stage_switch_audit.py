"""Measure private disc stage archive bytes and production-reader acceptance.
Outputs aggregate facts only; neither extracts nor retains disc assets.
"""
from pathlib import Path
import json
import re
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mex_port'))
from mex_hsd import Gcm
from test_stage_switch import ROOT, OUT, compile_test

STAGES = {'Final Destination':'GrNLa.dat', 'Battlefield':'GrNBa.dat',
          "Yoshi's Story":'GrSt.dat', 'Dream Land':'GrOp.dat',
          'Fountain of Dreams':'GrIz.dat', 'Pokemon Stadium':'GrPs.dat'}

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    exe = OUT / 'stage_dat_audit.exe'
    compile_test(ROOT / 'melee/pc/tests/stage_dat_audit.c', exe)
    env = (ROOT / '.env').read_text()
    paths = re.findall(r'^export GW_ISO_(VANILLA|ACE)="([^"]+)"', env, re.M)
    result = {}
    for label, path in paths:
        try:
            disc=Gcm(path)
            rows={}
            for name,file in STAGES.items():
                raw=disc.read(file)
                p=subprocess.run([str(exe)], input=raw, capture_output=True, check=True)
                values=[int(x) for x in p.stdout.split()]
                rows[name]=dict(zip(['reader_status','dat_bytes','vertices','lines','joints','groups','decoded_collision_bytes',
                                    'model_reader_status','model_joints','texture_unique_bytes','model_runtime_allowance'],values))
            result[label]=rows
        except (OSError, KeyError) as error:
            result[label]={'unavailable':str(error)}
    target=ROOT/'_build/tmp/codex-stage-switch-memory.json'
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
