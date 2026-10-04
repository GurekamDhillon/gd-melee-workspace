"""Standalone tests of current retail moving collision and scoped StageInfo restore."""
import subprocess
from test_stage_switch import ROOT, OUT, compile_test
from test_stage_switch_ledges import function

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    source = (ROOT / 'melee/src/melee/mp/mplib.c').read_text()
    (OUT / 'stage_joint_retail.inc').write_text(function(source, 'mpLib_80055E9C'))
    exe = OUT / 'stage_joint_motion_test.exe'
    compile_test(ROOT / 'melee/pc/tests/stage_joint_motion_test.c', exe, ['/I' + str(OUT)])
    subprocess.run([str(exe)], check=True)
    source = (ROOT / 'melee/pc/gameworld/script_game.c').read_text()
    (OUT / 'stage_cpu_retail.inc').write_text(function(source, 'script_cpu_mode_pair') + function(source, 'script_cpu_mode_persist'))
    exe = OUT / 'stage_cpu_respawn_test.exe'
    compile_test(ROOT / 'melee/pc/tests/stage_cpu_respawn_test.c', exe, ['/I' + str(OUT)])
    subprocess.run([str(exe)], check=True)
    source = (ROOT / 'melee/pc/gameworld/script_stage_slot_dynamic.inc').read_text()
    (OUT / 'stage_context_retail.inc').write_text(function(source, 'script_slot_context_begin') + function(source, 'script_slot_context_end'))
    exe = OUT / 'stage_context_test.exe'
    compile_test(ROOT / 'melee/pc/tests/stage_context_test.c', exe, ['/I' + str(OUT)])
    subprocess.run([str(exe)], check=True)
