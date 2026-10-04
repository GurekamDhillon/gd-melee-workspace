"""Extract production retry director; standalone C and real Lua, no game launch."""
import shutil
import subprocess
from test_stage_switch import ROOT, compile_test
from test_stage_switch_fix3 import function

def main():
    out=ROOT/'_build/tmp/stage-retry-demo-tests'
    out.mkdir(parents=True,exist_ok=True)
    src=(ROOT/'melee/pc/platform/gw_script_stage_slots.inc').read_text()
    names=['gs_stage_request','gs_stage_cancel','gs_stage_logic_tick','gs_stage_presentation_tick']
    (out/'stage_retry_native.inc').write_text(''.join(function(src,n) for n in names))
    exe=out/'stage_retry_test.exe'
    compile_test(ROOT/'melee/pc/tests/stage_retry_test.c',exe,['/I'+str(out)])
    subprocess.run([str(exe)],check=True,timeout=10)
    lua=shutil.which('lua')
    assert lua, 'real Lua required for demo fixture'
    subprocess.run([lua,str(ROOT/'melee/pc/tests/stage_demo_rotation_test.lua'),str(ROOT/'melee/pc/scripts/examples/stage_switch_demo/scripts/main.lua')],check=True,timeout=10)

if __name__=='__main__':main()
