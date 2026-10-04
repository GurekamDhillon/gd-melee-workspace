"""Fix3 standalone fixtures only. Private DATs streamed, never persisted."""
from pathlib import Path
import re
import subprocess
import sys
from test_stage_switch import ROOT, OUT, compile_test

def function(source, name):
    match = re.search(r'[^\n]*\b'+re.escape(name)+r'\([^;{}]*\)\s*\{', source)
    if not match:
        raise ValueError(name)
    start, pos = match.start(), match.end()
    depth = 1
    while depth:
        depth += (source[pos] == '{') - (source[pos] == '}')
        pos += 1
    return source[start:pos]+'\n'

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    src = (ROOT/'melee/pc/platform/gw_script.c').read_text()
    models = (ROOT/'melee/pc/platform/gw_script_model_api.inc').read_text()
    names = ['gs_push_fail','gs_stage_state_refuse','l_savestate','l_loadstate']
    (OUT/'stage_slot_lua_retail.inc').write_text(''.join(function(src,n) for n in names)+function(models,'gs_model_options'))
    lua = ROOT/'melee/pc/third_party/lua-5.4.7/src'
    sources = [str(p) for p in lua.glob('*.c') if p.name not in ['lua.c','luac.c']]
    exe = OUT/'stage_slot_lua_test.exe'
    compile_test(ROOT/'melee/pc/tests/stage_slot_lua_test.c',exe,['/I'+str(lua),'/Fo'+str(OUT)+'/', '/I'+str(OUT),*sources])
    world = ROOT/'melee/pc/scripts/examples/missions/scripts/world.lua'
    original = world.read_text()
    patch = (ROOT/'_build/tmp/codex-stage-switch-fix3-missions.diff').read_text()
    helper = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))+'\n'
    # Diff can align a shared `end` as context, moving the added block's
    # boundary. Extract from its comment and restore its closing function end.
    helper=helper[helper.index('  -- Static exported levels only;'):]
    if not helper.rstrip().endswith('  end'):helper+='  end\n'
    proposed = OUT/'stage_missions_proposed.lua'
    proposed.write_text(original.replace('  function W.load(g,name,level,staging)',helper+'  function W.load(g,name,level,staging)',1))
    subprocess.run([str(exe),str(proposed)],check=True,timeout=10)
    for name in ['l_state_save','l_state_load','l_rewind_test']:
        body = function(src,name)
        assert 'gs_stage_state_refuse(L,' in body
        assert body.index('gs_stage_state_refuse(L,') < body.index('return gs_push_fail(')
    ground = (ROOT/'melee/src/melee/gr/ground.c').read_text()
    (OUT/'stage_scale_retail.inc').write_text(function(ground,'Ground_801C39C0')+function(ground,'Ground_801C3BB4'))
    fd = (ROOT/'melee/src/melee/gr/grlast.c').read_text()
    table = re.search(r'static s16 grNLa_803E8010\[\]\[4\] = \{.*?\};',fd,re.S)[0].replace('s16','short')
    backdrop = (ROOT/'melee/src/melee/gr/grlast_stage_slots.inc').read_text()
    (OUT/'stage_fd_backdrop_retail.inc').write_text(table+'\n'+function(fd,'do_anime')+function(backdrop,'Ground_StageSlotFDBackdrop'))
    director = (ROOT/'melee/pc/platform/gw_script_stage_slots.inc').read_text()
    (OUT/'stage_indicator_retail.inc').write_text(function(director,'gs_stage_indicator_draw')+function(src,'gw_Script_DrawCount')+function(src,'gw_Script_DrawAt'))
    audio = (ROOT/'melee/src/melee/lb/lbaudio_ax.c').read_text()
    (OUT/'stage_music_retail.inc').write_text(function(audio,'lbAudioAx_80023F28_helper1'))
    for name in ['stage_cover_test','stage_fd_backdrop_test','stage_scale_test','stage_indicator_test','stage_music_test']:
        exe = OUT/(name+'.exe')
        compile_test(ROOT/'melee/pc/tests'/(name+'.c'),exe,['/I'+str(OUT)])
        if name != 'stage_scale_test':subprocess.run([str(exe)],check=True,timeout=10)
    sys.path.insert(0,str(ROOT/'tools/mex_port'))
    from mex_hsd import Gcm
    iso = re.search(r'^export GW_ISO_VANILLA="([^"]+)"',(ROOT/'.env').read_text(),re.M)[1]
    disc = Gcm(iso)
    for file,kind in [('GrNBa.dat','bf'),('GrSt.dat','ys')]:
        result = subprocess.run([str(OUT/'stage_scale_test.exe'),kind],input=disc.read(file),capture_output=True,check=True,timeout=10)
        print(file+': '+result.stdout.decode().strip())
    print('state_save/state_load/rewind_test early refusal source checks passed')
    scene=(ROOT/'melee/pc/platform/gw_runtime.c').read_text()
    assert re.search(r'\{"dreamland64",\s*28\}',scene)
    assert re.search(r'\{"dl",\s*17\}',scene)
    assert re.search(r'\{"dl",\s*28\}',director)
    docs=(ROOT/'docs/scripting.md').read_text()
    for name in ['Final Destination','Battlefield',"Yoshi's Story",'Dream Land 64','Fountain of Dreams','Pokemon Stadium']:
        assert '| '+name+' |' in docs
    print('six legal slot/scene name table and Dream Land/Green Greens alias contracts passed')
