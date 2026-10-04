"""Standalone production-source fixtures; never build or launch the game."""
import subprocess
import sys
from test_stage_switch import ROOT, OUT, compile_test
from test_stage_switch_fix3 import function

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT/'melee/pc/gameworld/script_stage_music.inc'
    assert source.exists(), 'switch music still starts synchronously in the frozen transition'
    (OUT/'stage_music_queue_retail.inc').write_text(source.read_text())
    exe=OUT/'stage_transition_freeze_test.exe'
    compile_test(ROOT/'melee/pc/tests/stage_transition_freeze_test.c',exe,['/I'+str(OUT)])
    subprocess.run([str(exe)],check=True,timeout=10)
    synth=(ROOT/'melee/src/sysdolphin/baselib/synth.c').read_text()
    body=function(synth,'HSD_SynthPStreamStart')
    start=body.index('    do {');end=body.index('while (HSD_Synth_804D7778 != 0);',start)+len('while (HSD_Synth_804D7778 != 0);')
    (OUT/'stage_synth_wait_retail.inc').write_text(body[start:end])
    director=(ROOT/'melee/pc/platform/gw_script_stage_slots.inc').read_text()
    (OUT/'stage_transition_presentation_retail.inc').write_text(function(director,'gs_stage_presentation_tick'))
    shaders=(ROOT/'melee/pc/platform/gw_shader_runtime.inc').read_text()
    (OUT/'stage_post_clear_retail.inc').write_text(function(shaders,'gw_Post_Clear')+function(shaders,'gw_Post_Protect'))
    for name in ['stage_synth_wait_test','stage_transition_cover_test','stage_post_clear_test']:
        exe=OUT/(name+'.exe')
        extension='.cpp' if name.endswith('clear_test') else '.c'
        compile_test(ROOT/'melee/pc/tests'/(name+extension),exe,
                     ['/I'+str(OUT),'/I'+str(ROOT/'melee/pc/platform')],
                     language='cpp' if extension=='.cpp' else 'c')
        subprocess.run([str(exe)],check=True,timeout=10)
    slots=(ROOT/'melee/pc/gameworld/script_stage_slots.inc').read_text()
    for name in ['ScriptGame_StageSwitch','ScriptGame_StageSlotsRelease']:
        assert 'lbAudioAx_80023F28(' not in function(slots,name)
    native=(ROOT/'melee/pc/platform/gw_script.c').read_text()
    tick=function(native,'gw_Script_Tick')
    assert tick.index('gs_hook_all("on_tick"')<tick.index('gw_ScriptGame_StageMusicTick(')
    assert '!gs.paused && !gs_hitstop_live()' in tick
    binding=(ROOT/'melee/pc/platform/gw_script_shaders.inc').read_text()
    assert 'if(owner>0)' in function(binding,'l_post_clear')
    print('switch/release only queue; normal-loop music follows hooks and pause/freeze gates passed')
    if '--check-before' in sys.argv:
        # Reproduce the old behavior in ignored generated fixture inputs only.
        # No production source, executable copy or game process is modified.
        (OUT/'stage_synth_wait_retail.inc').write_text('do {} while (HSD_Synth_804D7778 != 0);')
        exe=OUT/'stage_synth_wait_before.exe'
        compile_test(ROOT/'melee/pc/tests/stage_synth_wait_test.c',exe,['/I'+str(OUT)])
        try:
            subprocess.run([str(exe)],check=True,timeout=1,capture_output=True)
            raise AssertionError('old empty wait unexpectedly completed')
        except subprocess.TimeoutExpired:
            print('BEFORE: empty retail wait reproduced non-progress (fixture timeout)')
        old=function(shaders,'gw_Post_Clear')
        old=old[:old.index('// Zero means')]+'''posts.each([&](uint32_t,int o,Post& p){if((!owner||owner==o)&&p.owns_shader)assets.remove(uint32_t(p.shader),o);});
  posts.clear(owner);refresh_stages();}
'''
        (OUT/'stage_post_clear_retail.inc').write_text(old+function(shaders,'gw_Post_Protect'))
        exe=OUT/'stage_post_clear_before.exe'
        compile_test(ROOT/'melee/pc/tests/stage_post_clear_test.cpp',exe,
                     ['/I'+str(OUT),'/I'+str(ROOT/'melee/pc/platform')],language='cpp')
        result=subprocess.run([str(exe)],capture_output=True,timeout=10)
        assert result.returncode!=0, 'old owner-zero wildcard unexpectedly preserved passes'
        print('BEFORE: old post_clear fails engine/foreign ownership assertions')
        # Restore the production-derived inputs for subsequent standalone checks.
        (OUT/'stage_synth_wait_retail.inc').write_text(body[start:end])
        (OUT/'stage_post_clear_retail.inc').write_text(function(shaders,'gw_Post_Clear')+function(shaders,'gw_Post_Protect'))

if __name__=='__main__': main()
