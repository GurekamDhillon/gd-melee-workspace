#!/usr/bin/env python3
"""Actual Lua integration with deterministic engine stubs; not an in-engine playtest."""
from pathlib import Path
import subprocess
import tempfile
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
from tools.roguelite import prepare

from tools.test_support import require_executable
LUA = require_executable('lua5.4', 'lua')
PRELUDE = r'''
local last_scene;local pending_scene;local scene_ended=false;local files={};local mx,my,mb=-1000,-1000,0; local controls=0; local tick=100;local pause=false;local request=true
local ps={[1]={x=-42,y=0,vx=0,vy=0,stocks=99,percent=0,facing=1,action=14,airborne=false,hitlag=0,costume=0},[2]={x=28,y=0,vx=0,vy=0,stocks=99,percent=0,facing=-1,action=14,airborne=false,hitlag=0,costume=0}}
local models={};local enemies={};local serial=0;local writes=0;local hits=0;local claims={};local masks={};local commands={};local cpu={};local fail_write=false;local fail_hit=false;local refuse_platform=false;local refuse_teleport={};local isolated=false;local refuse_isolation=false
local kit=setmetatable({roles={},row={pitch=36}}, {__index=function() return function() return 1 end end})
gd={buttons={A=256,B=512,UP=8,DOWN=4,LEFT=1,RIGHT=2},kit=kit,
 log=function() end,data_read=function(n)if n=='config.txt' then return files[n] or 'generator=legacy' end return files[n]end,
 data_write=function(n,s) if fail_write then error('disk full') end files[n]=s;writes=writes+1;return true end,
 command=function(n,f)commands[n]=f end,input=function(p)claims[p]=true end,
 input_mask=function(p,b)masks[p]=b end,release_pad=function(p)claims[p]=nil end,
 tbd_request=function()local v=request;request=false;return v end,
 scene_launch=function(opts)
 last_scene=opts.p1
 assert((opts.mode=='lab' and opts.p2=='none') or (opts.mode=='vs' and opts.p2=='fox/c0/cpu9'),'unsupported scene grammar')
 assert(opts.stocks==99 and opts.items=='off' and opts.time==0,'unbounded/native-scene rules mismatch')
 pending_scene=opts;scene_ended=false;tick=0
 end,match=function()return {active=true,frame=tick,netplay=false,stage=37}end,
 player=function(p)return ps[p]end,pad=function()return {buttons=controls}end,
 pause=function()pause=true end,resume=function()pause=false end,paused=function()return pause end,
 mouse=function()return mx,my,mb end,
 set_stocks=function(p,n)ps[p].stocks=n end,set_percent=function(p,n)ps[p].percent=n end,
 teleport=function(p,x,y)if refuse_teleport[p] then error('fighter respawning') end ps[p].x=x;ps[p].y=y end,
 model_load=function()serial=serial+1;return serial end,model_spawn=function()serial=serial+1;return serial end,model_despawn=function()return true end,model_release=function()end,
 stage_add_platform=function()if refuse_platform then return nil,'pool exhausted' end serial=serial+1;models[serial]=true;return serial end,
 stage_remove=function(h)models[h]=nil end,
 stage_isolate=function(value)if value~=nil then if value and refuse_isolation then return false end isolated=value end return isolated end,
 spawn_enemy=function(kind,x,y,opts)serial=serial+1;enemies[serial]={kind=kind,x=x,y=y,facing=opts.facing,hits=0,received=0,attack_id=1,damage=0};return serial end,
 enemy_state=function(h)return enemies[h]end,enemy_strike=function()return true end,enemy_hurt=function(h,spec)enemies[h].damage=enemies[h].damage+spec.damage;return true end,
 enemy_remove=function(h)enemies[h]=nil end,enemy_alive=function(h)return enemies[h]~=nil end,cpu_mode=function(p,m)assert(ps[p],'absent CPU touched');cpu[p]=m;return true end,
 hit=function(p,opts)if fail_hit then return false end hits=hits+1;ps[p].percent=ps[p].percent+opts.damage;return true end,
 impulse=function()return true end,fx_play=function()return 0 end,fx_end=function()end,
 parts_clear=function()end,parts=function()return {geometry_signature='unknown'}end,
 fill=function()end,project=function(x,y)return x+320,240-y end}
local function fixture_scene_tick()
 if request then request=false;commands.rogue_start() end
 if not pending_scene then return end
 if not scene_ended then
  on_match_end();ps[2]=nil;cpu[2]=nil;scene_ended=true
  ps[1]={x=0,y=0,vx=0,vy=0,stocks=99,percent=0,facing=1,action=14,airborne=false,hitlag=0,costume=0}
  if pending_scene.p2~='none' then ps[2]={x=28,y=0,vx=0,vy=0,stocks=99,percent=0,facing=-1,action=14,airborne=false,hitlag=0,costume=0} end
 end
 tick=tick+1
 if tick>91 then pending_scene=nil end
end
gd.data_write_atomic=gd.data_write; -- deterministic safe writer fixture
'''
TEST = r'''
local function step(b) controls=b or 0;fixture_scene_tick();on_tick() end
local function press(b)step(0);step(b);step(0)end
local function frame()tick=tick+1;on_frame()end
local function state()return roguelite_state()end
local function click(id)
 local view=state().menu_view;assert(view,'No menu for '..id)
 local found
 for _,control in ipairs(view.controls) do if control.id==id then found=control;break end end
 assert(found,'Missing menu control '..id);mx=found.x+found.w/2;my=found.y+found.h/2;mb=0;step(0);mb=1;step(0);mb=0;step(0);mx=-1000;my=-1000
 for i=1,10 do if not state().loading then break end;step(0) end
 if state().loading then error('preload did not settle') end
 if state().menu==nil and not state().active and state().ready then step(0) end
end
local function door(side)
 ps[1].x=side=='left' and -104 or 104;ps[1].y=0;press(4)
 if pending_scene then for i=1,140 do step();if not pending_scene and state().ready then break end end;for i=1,12 do if state().active or state().menu then break end;step() end end
end
step();assert(not state().ready);step();assert(not state().ready);tick=91;step();assert(state().ready and state().menu=='collection')
assert(claims[4] and not claims[1]);assert(pause)
-- Collection starter selection saves, without creating free genes or locks.
local collection_writes=writes
click('gene:g3');click('starter');assert(state().menu_view.starter=='g3' and writes==collection_writes+1)
click('gene:g1');click('starter');assert(state().menu_view.starter=='g1' and writes==collection_writes+2)
assert(not state().profile.genes.g4 and not state().profile.genes.g1.locks.potency)
refuse_teleport[1]=true;click('start')
assert(state().node=='entry' and not state().active and not pause and state().menu==nil)
refuse_teleport[1]=nil;step(0);assert(state().active and not pause)
assert(ps[2]==nil and isolated)
-- Player-only exploration cannot farm defense charge.
on_action_change(1,179,181,false)
assert(state().run.hosts.player.state.guard.charge==0)
ps[1].x=104;ps[1].y=0;step(4);step(4);step(4)
assert(state().node=='trail' and state().command=='root');step(0);assert(next(models))
-- Door cannot steal down while inside the three-way command menu.
ps[1].x=-104;ps[1].y=0;press(1);assert(state().node=='trail');press(4);assert(state().node=='trail')
press(8);press(8)
local enemy_handle=next(enemies);assert(enemy_handle)
-- Real queued enemy contacts use the current move instance; duplicate events and
-- retired handles cannot charge again. The release targets the custom actor.
ps[1].x=0;ps[1].y=0;enemies[enemy_handle].x=4;enemies[enemy_handle].y=0
for i=1,3 do
 on_action_change(1,14,44,false)
 on_enemy_hit({handle=enemy_handle,from=1,damage=3})
 on_enemy_hit({handle=enemy_handle,from=1,damage=3})
end
assert(state().run.hosts.player.state.assault.charge==3)
press(1);press(1)
assert(enemies[enemy_handle].damage==10 and state().run.hosts.player.state.assault.charge==0)
assert(state().run.hosts.enemy_trail_1)
for i=1,100 do frame() end
on_enemy_defeated({handle=enemy_handle});enemies[enemy_handle]=nil
on_enemy_hit({handle=enemy_handle,from=1,damage=3})
assert(state().run.hosts.player.state.assault.charge==0)
door('left');assert(state().node=='arena_a' and cpu[2]=='fight')
local r=state().run
assert(r.hosts.enemy_arena_a and r.hosts.enemy_arena_a.slots.assault)
-- Distinct genuine attack instances charge; duplicate contact does not.
on_action_change(1,14,44,false);on_hit(1,2,{item=false});on_hit(1,2,{item=false})
local charge=r.hosts.player.state.assault.charge;assert(charge==1)
for i=1,2 do on_action_change(1,44,44,false);on_hit(1,2,{item=false}) end
assert(r.hosts.player.state.assault.charge==3)
ps[1].x=0;ps[1].y=0;ps[2].x=4;ps[2].y=0
press(1);press(1);assert(hits==1 and state().run.hosts.player.state.assault.charge==0)
-- Injected hit does not consume subsequent genuine collision credit.
on_action_change(1,44,44,false);on_hit(1,2,{item=false})
for i=1,3 do on_action_change(1,179,181,false) end
assert(state().run.hosts.player.state.guard.charge==3)
-- Native refusal must retain the charge; test fresh cooldown-expired state.
for i=1,100 do frame() end
for i=1,3 do on_action_change(1,44,44,false);on_hit(1,2,{item=false}) end
fail_hit=true;press(1);press(1);fail_hit=false
assert(state().run.hosts.player.state.assault.charge==3)
-- Arena clear is an observed native stock transition, not percent threshold.
ps[2].stocks=98;frame();assert(state().menu=='reward' and pause)
-- A callback while reward UI is paused cannot earn charge.
state().run.hosts.player.state.guard.charge=0
on_action_change(1,179,181,false)
assert(state().run.hosts.player.state.guard.charge==0)
local potency=state().run.genes[state().run.hosts.player.slots.assault].base.potency
click('reward1');assert(state().run.progress.claimed.arena_a)
-- Cleared arena remains ineligible after its menu has closed.
assert(state().menu==nil)
on_action_change(1,179,181,false)
assert(state().run.hosts.player.state.guard.charge==0)
local arena_checkpoint={};for name,value in pairs(files) do arena_checkpoint[name]=value end
assert(state().run.genes[state().run.hosts.player.slots.assault].upgrades.potency==2)
refuse_teleport[1]=true;door('right')
assert(state().node=='rest' and not state().active and not pause and state().menu==nil and ps[2]==nil)
refuse_teleport[1]=nil;step(4);step(4)
assert(state().active and state().menu=='rest' and pause)
-- Fusion consumes authored parents, re-equips child, retains ancestry.
click('gene:r1');click('parents');click('gene:r3');click('confirm')
local child=state().run.hosts.player.slots.assault;assert(#state().run.genes[child].parents==2)
click('continue');assert(not pause)
door('right');assert(state().node=='approach')
-- A native despawn (walked offstage) has no defeat callback but cannot lock a door.
enemy_handle=next(enemies);enemies[enemy_handle]=nil;frame()
assert(state().run.progress.cleared.approach)
door('right');assert(state().node=='boss')
ps[2].stocks=98;frame();assert(state().menu==nil)
ps[2].stocks=98;frame();assert(state().menu=='reward');click('reward1')
door('right');assert(state().run.status=='success' and state().menu=='collection')
assert(state().profile.finished[state().run.id].export)
local checkpoint_a,checkpoint_b=files['checkpoint-a.txt'],files['checkpoint-b.txt']
assert(checkpoint_a and checkpoint_b and writes>3)
on_draw();commands.rogue_state();commands.rogue_route('4242');commands.rogue_route('bogus');on_unload();assert(not claims[4] and masks[1]==0 and not pause)
print('runtime: native-entry wait, collection/starter saves, doors, commands, genes, shield charge, refusal, stocks, rewards, fusion and export passed (engine stubs)')
'''

def run(code):
    try:
        subprocess.run([LUA, '-'], input=code, text=True, check=True)
    except subprocess.CalledProcessError:
        failure = Path(__file__).resolve().parents[2] / '_build/tmp/roguelite-runtime-failure.lua'
        failure.parent.mkdir(parents=True, exist_ok=True)
        failure.write_text(code)
        raise

bundle = prepare.bundle()
wrapped = '(function()\n' + bundle + '\nend)()\ncommands.rogue_start()\n'
RECOVERY = r'''
-- Keep the older complete pair when newest checkpoint is truncated.
local ga=tonumber(files['checkpoint-a.txt']:match('TBD%d (%d+)'))
local gb=tonumber(files['checkpoint-b.txt']:match('TBD%d (%d+)'))
files[ga>gb and 'checkpoint-a.txt' or 'checkpoint-b.txt']='TBD1 99 120 80\ntruncated'
request=true;tick=0
'''
RESTORED = r'''
assert(roguelite_state().profile and roguelite_state().run)
step();step();tick=91;step();assert(roguelite_state().ready)
-- A throwing native write is contained; it cannot disable the gameplay script.
fail_write=true;click('gene:g3');click('discard');click('discard');fail_write=false
assert(roguelite_state().feedback.notification.kind=='error')
assert(roguelite_state().feedback.notification.title:find('write/readback failed',1,true))
on_unload()
files['checkpoint-a.txt']='TBD1 '..string.rep('9',400)..' 1 0\nx'
files['checkpoint-b.txt']='invalid';request=true;tick=0
'''
INVALID = r'''
assert(roguelite_state().menu=='error')
local before_a=files['checkpoint-a.txt'];step();step();tick=91;step();press(256)
assert(roguelite_state().menu=='error' and files['checkpoint-a.txt']==before_a)
print('runtime: torn newest checkpoint recovery, throwing save containment, huge generation rejection and invalid-file preservation passed')
'''
RESUME_ARENA = r'''
files=arena_checkpoint;request=true;tick=0;on_unload();
'''
CHECK_ARENA = r'''
step();step();tick=91;step();click('resume');for i=1,140 do step() end
assert(roguelite_state().node=='arena_a' and roguelite_state().menu==nil)
assert(roguelite_state().run.progress.claimed.arena_a and cpu[2]=='stand')
print('runtime: claimed arena resumes with stand CPU and no duplicate reward')
'''
TIMEOUT = r'''
local before_a,before_b=files['checkpoint-a.txt'],files['checkpoint-b.txt']
refuse_teleport[1]=true;click('start')
for i=1,600 do step(0) end
assert(roguelite_state().menu=='error' and not roguelite_state().active and pause)
assert(roguelite_state().toast:find('placement timed out',1,true))
assert(next(models)==nil and files['checkpoint-a.txt']==before_a and files['checkpoint-b.txt']==before_b)
print('runtime: permanent actor refusal cleans geometry, explains transition error and preserves checkpoint')
'''
DEATH = r'''
local function press(b)controls=0;on_tick();controls=b;on_tick();controls=0;on_tick()end
on_tick();on_tick();tick=91;on_tick()
local start
for _,c in ipairs(roguelite_state().menu_view.controls) do if c.id=='start' then start=c end end
assert(start);mx=start.x+4;my=start.y+4;mb=1;on_tick();mb=0;on_tick()
for i=1,12 do if roguelite_state().active then break end;on_tick() end
assert(roguelite_state().active)
local before=roguelite_state().profile.next_id
for i=1,3 do ps[1].stocks=98;tick=tick+1;on_frame() end
assert(roguelite_state().run.status=='failure' and roguelite_state().menu=='collection')
assert(roguelite_state().profile.next_id==before)
assert(roguelite_state().profile.finished[roguelite_state().run.id].outcome=='failure')
print('runtime: three observed stock losses end run without adding a collection gene (engine stubs)')
'''
ROSTER_START = r'''
click('fighter');click('fighter:link');click('costume:next');click('accept')
assert(state().fighter.id=='link' and state().fighter.costume==1)
click('start');assert(not state().ready and last_scene=='link/c1')
step();tick=91;step();assert(state().ready and not state().active);for i=1,12 do if state().active then break end;step() end;assert(state().active and state().node=='entry')
assert(state().run_fighter.id=='link' and state().run_fighter.costume==1)
on_unload();request=true;tick=0
'''
ROSTER_PREFERENCE = r'''
step();step();tick=91;step();assert(last_scene=='link/c1')
click('fighter');click('fighter:falco');click('accept')
assert(state().fighter.id=='falco' and state().run_fighter.id=='link')
on_unload();request=true;tick=0
'''
ROSTER_RESUME = r'''
step();step();tick=91;step();assert(last_scene=='falco/c0')
click('resume');assert(not state().ready and last_scene=='link/c1')
step();tick=91;step();assert(not state().active);for i=1,12 do if state().active then break end;step() end;assert(state().active and state().node=='entry')
assert(state().run_fighter.id=='link' and state().run_fighter.costume==1)
print('runtime: fighter/costume actually relaunches scene; atomic A/B checkpoint keeps saved-run fighter separate from next-run choice')
on_unload()
-- The legacy envelope has no character metadata and therefore means Falco 0.
-- Rewrite the current TBD3 saves (and any TBD2) into roster-less TBD1.
for name,raw in pairs(files) do if name:match('checkpoint') then
 local g,pl,rl=raw:match('TBD3 (%d+) (%d+) (%d+)')
 if g then
  pl,rl=tonumber(pl),tonumber(rl)
  local body=raw:match('\n(.*)$')
  files[name]='TBD1 '..g..' '..pl..' '..rl..'\n'..body:sub(1,pl+rl)
 else
  local g2,pl2,rl2,ml2,body2=raw:match('TBD2 (%d+) (%d+) (%d+) (%d+)\n(.*)')
  if g2 then files[name]='TBD1 '..g2..' '..pl2..' '..rl2..'\n'..body2:sub(1,tonumber(pl2)+tonumber(rl2)) end
 end
end end
request=true;tick=0
'''
ROSTER_LEGACY = r'''
assert(state().fighter.id=='falco' and state().run_fighter.id=='falco')
assert(state().run and state().run.status=='active')
print('runtime: legacy TBD1 checkpoint migrates losslessly with original Falco choice')
'''
# Preserve an unsupported future slot while loading and saving the older pair.
FUTURE_SETUP = r'''
local function gen(s) return tonumber(s:match('TBD%d (%d+)')) end
local a,b=files['checkpoint-a.txt'],files['checkpoint-b.txt']
assert(gen(a) and gen(b),'expected two valid saves to seed the fixture')
-- Put the unsupported future envelope in the OLDER slot; the newer stays valid.
FUTURE_SLOT=gen(a)>=gen(b) and 'checkpoint-b.txt' or 'checkpoint-a.txt'
FUTURE_BYTES='TBD4 999 1 0 0 0 0 00000000\nx'
files[FUTURE_SLOT]=FUTURE_BYTES
request=true;tick=0
'''
FUTURE_CHECK = r'''
step();step();tick=91;step();assert(state().ready)
assert(files[FUTURE_SLOT]==FUTURE_BYTES,'future checkpoint lost during load')
-- A save-triggering interaction must not overwrite the preserved future slot.
click('gene:g3');click('discard');click('discard')
assert(files[FUTURE_SLOT]==FUTURE_BYTES,'future checkpoint overwritten by save')
local other=FUTURE_SLOT=='checkpoint-a.txt' and 'checkpoint-b.txt' or 'checkpoint-a.txt'
assert(files[other] and files[other]:match('^TBD3'),'no replacement checkpoint was written')
print('runtime: unsupported future checkpoint slot preserved across saves')
'''

def test_runtime():
    run(PRELUDE + wrapped + TEST + RECOVERY + wrapped + RESTORED + wrapped + INVALID)
    run(PRELUDE + wrapped + TEST + RESUME_ARENA + wrapped + CHECK_ARENA)
    run(PRELUDE + wrapped + TEST + TIMEOUT)
    run(PRELUDE + wrapped + DEATH)
    run(PRELUDE + wrapped + TEST + ROSTER_START + wrapped + ROSTER_PREFERENCE + wrapped + ROSTER_RESUME + wrapped + ROSTER_LEGACY)
    run(PRELUDE + wrapped + TEST + FUTURE_SETUP + wrapped + FUTURE_CHECK)
    # Installation defaults and enable/restore must preserve the prior enabled list.
    with tempfile.TemporaryDirectory() as temp:
        app = Path(temp)
        (app / 'mods').mkdir()
        enabled = app / 'mods/enabled.txt'
        enabled.write_text('effects_lab\nexisting\n')
        mod = prepare.install(app)
        assert enabled.read_text() == 'effects_lab\nexisting\n'
        assert (mod / 'ui/roguelite_ui.json').exists()
        assert not (mod / 'ui/kit.json').exists()
        assert (mod / 'fx/SolarEruption/SolarEruption.gfx.json').exists()
        prepare.install(app, enable=True)
        assert enabled.read_text() == 'roguelite\n'
        prepare.install(app, restore=True)
        assert enabled.read_text() == 'effects_lab\nexisting\n'
        subprocess.run([LUA, '-', str(mod / 'scripts/main.lua')], input='assert(loadfile(arg[1]))', text=True, check=True)
    print('runtime: install defaults, isolated enable/restore, original art/FX and bundled Lua syntax passed')


if __name__ == '__main__':
    test_runtime()
