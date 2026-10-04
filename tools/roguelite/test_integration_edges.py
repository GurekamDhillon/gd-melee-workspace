"""Run the bundled Lua against focused integration edges, without importing test_runtime."""
import ast
from pathlib import Path
import shutil
import subprocess
import unittest
import prepare

HERE = Path(__file__).resolve().parent
TREE = ast.parse((HERE / 'test_runtime.py').read_text())
PRELUDE = next(ast.literal_eval(n.value) for n in TREE.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PRELUDE' for t in n.targets))
WRAPPED = ';(function()\n' + prepare.bundle() + '\nend)()\n'
SETUP = r'''
local function step(b)controls=b or 0;fixture_scene_tick();on_tick()end
local function press(b)step(0);step(b);step(0)end
local function state()return roguelite_state()end
local function click(id)
 for _,c in ipairs(state().menu_view.controls) do if c.id==id then mx=c.x+c.w/2;my=c.y+c.h/2;mb=0;step();mb=1;step();mb=0;step();mx=-1000;my=-1000;for i=1,10 do if not state().loading then break end;step() end;assert(not state().loading);if state().menu==nil and not state().active and state().ready then step() end;return end end
 error('missing control '..id)
end
step();step();tick=91;step();click('start');ps[1].x=104;ps[1].y=0;press(4)
assert(state().node=='trail' and state().active)
local handle=next(enemies);assert(handle);ps[1].x=0;ps[1].facing=1;enemies[handle].x=4;enemies[handle].y=0
local function charge()
 for i=1,3 do on_action_change(1,14,44,false);on_enemy_hit({handle=handle,from=1,damage=2}) end
end
local function cast()press(1);press(1);press(1)end
local function frame()tick=tick+1;on_frame()end
local function door(side)
 ps[1].x=side=='left' and -104 or 104;ps[1].y=0;press(4)
 if pending_scene then for i=1,140 do step();if not pending_scene and state().ready then break end end;for i=1,12 do if state().active or state().menu then break end;step() end end
end
local function arena()
 on_enemy_defeated({handle=handle});enemies[handle]=nil;door('left')
 assert(state().node=='arena_a');ps[2].stocks=98;frame();assert(state().menu=='reward')
end
'''

class IntegrationEdges(unittest.TestCase):
    def run_lua(self, code, before_setup=''):
        lua = shutil.which('lua5.4') or shutil.which('lua')
        self.assertIsNotNone(lua)
        p = subprocess.run([lua, '-'], input='local CORE_PATH='+__import__('json').dumps((prepare.SOURCE / 'core.lua').as_posix())+'\n'+PRELUDE+WRAPPED+before_setup+SETUP+code, text=True, capture_output=True)
        if p.returncode:
            import re
            line = re.search(r'stdin:(\d+):', p.stderr)
            if line:
                program = 'local CORE_PATH='+__import__('json').dumps(str(prepare.SOURCE / 'core.lua'))+'\n'+PRELUDE+WRAPPED+before_setup+SETUP+code
                p.stderr += '\nFailing Lua: ' + program.splitlines()[int(line.group(1))-1]
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)

    def test_refusal_restore_and_lethal_dedup(self):
        self.run_lua(r'''
charge();local old=state().run
old.marks.enemy_trail_1={source='player',expires=999}
local snapshot=assert(loadfile(CORE_PATH))()
local before=snapshot.snapshot(old)
gd.enemy_hurt=function()return false end;cast()
assert(state().run~=old and snapshot.snapshot(state().run)==before,'refusal lost run state')
-- Adapter must use the replaced run, including its shared cooldown/mark state.
enemies[handle].hits=1;tick=tick+1;on_frame()
assert(state().run.hosts.enemy_trail_1.state.assault.charge==1)
on_action_change(1,14,44,false);on_enemy_hit({handle=handle,from=1,damage=99})
on_enemy_defeated({handle=handle});enemies[handle]=nil
local q=state().run.hosts.player.state.assault.charge
on_enemy_hit({handle=handle,from=1,damage=99});assert(state().run.hosts.player.state.assault.charge==q)
assert(state().run.progress.cleared.trail)
''')

    def test_nearest_target_skips_invulnerable_actor(self):
        self.run_lua(r'''
charge();enemies[handle].vulnerable=false
local attempts=0
gd.enemy_hurt=function()attempts=attempts+1;return false end
cast()
assert(attempts==0,'invulnerable enemy was offered for activation')
''')

    def test_checkpoint_corruption_preserves_older_pair(self):
        self.run_lua(r'''
local a,b=files['checkpoint-a.txt'],files['checkpoint-b.txt'];assert(a and b)
local function generation(s)return tonumber(s:match('^TBD%d (%d+)'))end
local newest=generation(a)>generation(b) and 'checkpoint-a.txt' or 'checkpoint-b.txt'
local older=newest=='checkpoint-a.txt' and b or a
files[newest]=files[newest]:sub(1,30)
on_unload()
''' + WRAPPED + r'''
assert(state().run and state().run.status=='active','valid older pair was discarded')
assert(state().fighter.id=='falco' and state().run_fighter.id=='falco')
assert(files[newest]~=older,'load overwrote corrupt evidence')
''')

    def test_reward_save_failure_rolls_back_then_claims_once(self):
        self.run_lua(r'''
arena()
local C=assert(loadfile(CORE_PATH))();local before=C.snapshot(state().run)
local old_writes=writes;fail_write=true;click('reward1')
assert(state().menu=='reward' and pause and writes==old_writes)
assert(C.snapshot(state().run)==before,'failed save kept claimed reward or upgraded gene')
fail_write=false;click('reward1')
assert(state().menu==nil and not pause and state().run.progress.claimed.arena_a)
local id=state().run.hosts.player.slots.assault
assert(state().run.genes[id].upgrades.potency==2,'reward retried twice')
''')

    def test_finish_save_failure_retry_preserves_progress_and_exports_once(self):
        self.run_lua(r'''
arena();click('reward1');door('right');assert(state().menu=='rest');click('continue')
door('right');local h=next(enemies);enemies[h]=nil;frame();door('right')
assert(state().node=='boss');ps[2].stocks=98;frame();ps[2].stocks=98;frame();click('reward1')
local C=assert(loadfile(CORE_PATH))();local before=C.snapshot(state().profile)
local runid=state().run.id;local count=0;for _ in pairs(state().profile.genes)do count=count+1 end
fail_write=true;door('right')
assert(state().node=='boss' and state().run.status=='active' and not pending_scene,'refused handover replaced the active room')
assert(C.snapshot(state().profile)==before and not state().profile.finished[runid])
fail_write=false
local atomic=gd.data_write_atomic;local finish_writes=0
-- First persist the scene handover destination; refuse the sole terminal finish write.
gd.data_write_atomic=function(n,value)
 finish_writes=finish_writes+1
 if finish_writes==2 then fail_write=true end
 return atomic(n,value)
end
door('right')
assert(finish_writes==2,'terminal entry must not add an intermediate arrival save')
assert(state().menu=='error' and pause and not state().active and state().run.status=='active')
assert(C.snapshot(state().profile)==before and not state().profile.finished[runid])
assert(state().run.progress.claimed.boss and state().run.progress.cleared.arena_a)
fail_write=false;gd.data_write_atomic=atomic;click('retry')
assert(state().menu=='collection' and state().run.status=='success')
assert(state().profile.finished[runid].export)
local after=0;for _ in pairs(state().profile.genes)do after=after+1 end
assert(after==count+1,'finish retry exported multiple individuals')
''')

    def test_empty_floor_exact_and_unload_restores_paused_scene(self):
        self.run_lua(r'''
assert(isolated and not pause)
local floors,platform_count=0,0
for h,p in pairs(floor_params) do if models[h] then
 platform_count=platform_count+1
 if p.y==0 then floors=floors+1;assert(p.x==0 and p.width==260 and p.opts.passthrough==false and p.opts.ledges==true) end
end end
local D=assert(loadfile((CORE_PATH:gsub('core.lua$','dungeon.lua'))))()
local node=D.generate(state().run.world_seed).nodes[state().node]
assert(floors==1 and platform_count==1+#node.room.platforms)
for _,expected in ipairs(node.room.platforms) do
 local found=false
 for h,p in pairs(floor_params) do if models[h] and p.y~=0 and p.x==expected.x and p.y==expected.y and p.width==expected.width then found=true end end
 assert(found,'physical route platform changed during isolation')
end
gd.pause();assert(pause);on_unload()
assert(not isolated and not pause and not next(models) and not next(enemies))
''', before_setup=r'''
local floor_params={};local original_platform=gd.stage_add_platform
gd.stage_add_platform=function(x,y,width,opts)
 local h,why=original_platform(x,y,width,opts)
 if h then floor_params[h]={x=x,y=y,width=width,opts=opts} end
 return h,why
end
''')

    def test_empty_stage_refusal_cleans_geometry_preserves_checkpoint(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                self.run_lua(r'''
on_enemy_defeated({handle=handle});enemies[handle]=nil
local a,b=files['checkpoint-a.txt'],files['checkpoint-b.txt'];local prior=writes
local C=assert(loadfile(CORE_PATH))();local saved_profile=C.snapshot(state().profile)
local lives=state().run.stocks;local runid=state().run.id
''' + ('gd.stage_isolate=nil\n' if missing else 'refuse_isolation=true\n') + r'''
door('left')
assert(not state().active and state().menu=='error' and pause)
assert(not next(models) and not next(enemies),'failed isolation leaked owned geometry')
''' + (r"assert(writes==prior and files['checkpoint-a.txt']==a and files['checkpoint-b.txt']==b)" if missing else r'''
assert(writes==prior+1,'handover must persist exactly one destination checkpoint')
local directory=CORE_PATH:match('^(.*)/core.lua$')
local CP=assert(loadfile(directory..'/checkpoint.lua'))()
local Codec=assert(loadfile(directory..'/codec.lua'))()
local newest=files['checkpoint-a.txt']
if tonumber(files['checkpoint-b.txt']:match('^TBD3 (%d+)'))>tonumber(newest:match('^TBD3 (%d+)')) then newest=files['checkpoint-b.txt'] end
local decoded=assert(CP.decode(newest,C,Codec))
assert(decoded.run.id==runid and decoded.run.progress.room=='arena_a')
assert(decoded.run.stocks==lives and C.snapshot(decoded.profile)==saved_profile)
assert(decoded.run.progress.cleared.trail and not decoded.run.progress.cleared.arena_a and not decoded.run.progress.claimed.arena_a)
''') + r'''
on_unload();assert(not pause)
''')

    def test_entry_asset_work_yields_before_teleport_even_without_game_frames(self):
        self.run_lua("assert(state().active)", before_setup=r'''
local serial_tick,construction_tick=0,-1
local original_tick=on_tick
on_tick=function()serial_tick=serial_tick+1;original_tick()end
local original_platform=gd.stage_add_platform
gd.stage_add_platform=function(...)construction_tick=serial_tick;return original_platform(...)end
local original_load=gd.model_load;local original_spawn=gd.model_spawn
local load_tick=-1;local load_count=0
gd.model_load=function(...)
 assert(serial_tick~=load_tick,'multiple cold model loads in one callback')
 load_tick=serial_tick;load_count=load_count+1;assert(load_count<=6)
 return original_load(...)
end
gd.model_spawn=function(...)
 assert(serial_tick>load_tick,'spawn work ran in model disk-load callback')
 return original_spawn(...)
end
local original_teleport=gd.teleport
gd.teleport=function(...)
 assert(serial_tick>construction_tick,'asset construction and complete_entry ran in same hook')
 return original_teleport(...)
end
''')

    def test_pending_entry_isolation_loss_preserves_checkpoint(self):
        self.run_lua(r'''
on_enemy_defeated({handle=handle});enemies[handle]=nil
refuse_teleport[1]=true;door('left');assert(not state().active and state().menu==nil)
local a,b=files['checkpoint-a.txt'],files['checkpoint-b.txt'];local prior=writes
isolated=false;refuse_teleport[1]=nil;step()
assert(not state().active and state().menu=='error' and pause)
assert(writes==prior and files['checkpoint-a.txt']==a and files['checkpoint-b.txt']==b)
''')

    def test_isolation_loss_fails_closed_before_tick_or_frame_gameplay(self):
        for callback in ('step()', 'frame()'):
            with self.subTest(callback=callback):
                self.run_lua(r'''
local prior=state().run.frame;local a,b=files['checkpoint-a.txt'],files['checkpoint-b.txt']
isolated=false
''' + callback + r'''
assert(not state().active and state().menu=='error' and pause)
assert(state().run.frame==prior and not next(models) and not next(enemies))
assert(files['checkpoint-a.txt']==a and files['checkpoint-b.txt']==b)
''')


if __name__ == '__main__':
    unittest.main()
