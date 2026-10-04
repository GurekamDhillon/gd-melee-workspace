"""Real bundled Lua with strict player-only scene lifecycle doubles."""
import ast
from pathlib import Path
import shutil
import subprocess
import unittest
import prepare


class PlayerOnlyLifecycleTests(unittest.TestCase):
    def test_terminal_entry_single_finish_transaction(self):
        self.run_lifecycle(terminal=True)

    def test_exploration_combat_handover_preserves_run(self):
        self.run_lifecycle()

    def run_lifecycle(self, terminal=False):
        tree = ast.parse(Path(__file__).with_name('test_runtime.py').read_text())
        prelude = next(ast.literal_eval(n.value) for n in tree.body
                       if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PRELUDE' for t in n.targets))
        strict = r'''
local launched,ended=false,false
local scene_opts
gd.scene_launch=function(opts)
 scene_opts=opts;if opts.mode=='menu' then launched=true;ended=false;tick=0;return true end
 assert(opts.p1)
 assert((opts.mode=='lab' and opts.p2=='none') or (opts.mode=='vs' and opts.p2=='fox/c0/cpu9'))
 launched=true;ended=false;tick=0
end
local function actor(p) assert(ps[p],'absent fighter touched: '..p);return ps[p] end
gd.set_stocks=function(p,n)actor(p).stocks=n end
gd.set_percent=function(p,n)actor(p).percent=n end
gd.teleport=function(p,x,y)actor(p).x=x;actor(p).y=y end
gd.cpu_mode=function(p,m)actor(p);cpu[p]=m;return true end
local baseline={camera={left=-100,right=100,bottom=-20,top=60},blast={left=-200,right=200,bottom=-100,top=120}}
local bounds=baseline
gd.stage_bounds=function(value) if value==false then bounds=baseline elseif value then bounds=value end return bounds end
'''
        test = r'''
local function step(b)
 controls=b or 0
 if launched then
  if not ended then on_match_end();ps[2]=nil;ended=true
   ps[1]={x=0,y=0,vx=0,vy=0,stocks=99,falls=0,percent=0,facing=1,action=14,airborne=false,hitlag=0,costume=0}
   if scene_opts.p2~='none' then ps[2]={x=28,y=0,vx=0,vy=0,stocks=99,percent=0,facing=-1,action=14,airborne=false,hitlag=0,costume=0} end
  end
  tick=tick+1
  if tick>91 then launched=false end
 end
 on_tick()
end
local function settle() for i=1,140 do step() end end
local function click(id)
 local v=roguelite_state().menu_view;local c
 for _,b in ipairs(v.controls) do if b.id==id then c=b end end
 assert(c,'missing '..id);mx=c.x+c.w/2;my=c.y+c.h/2
 mb=0;step();mb=1;step();mb=0;step();mx=-1000;my=-1000;settle()
end
local function door(side)
 local n=roguelite_state().run.progress.room
 ps[1].x=side=='left' and -104 or 104;ps[1].y=0
 step();step(4);step();settle()
 assert(roguelite_state().run.progress.room~=n,'door did not travel')
end
step();settle();assert(roguelite_state().ready and not ps[2],'collection must be player-only')
click('start');assert(roguelite_state().active and not ps[2],'entry must be player-only')
local r=roguelite_state().run;local id=r.id;local seed=r.world_seed
local equipped=r.hosts.player.slots.assault
-- LAB has infinite native respawn: falls advance while stocks stay unchanged.
ps[1].falls=1;tick=tick+1;on_frame()
assert(roguelite_state().run.stocks==2 and ps[1].stocks==99,'solo death did not consume a logical life')
tick=tick+1;on_frame();on_frame();assert(roguelite_state().run.stocks==2,'one fall counted twice')
ps[1].falls=2;ps[1].stocks=98;tick=tick+1;on_frame()
assert(roguelite_state().run.stocks==1,'fall plus native stock drop counted twice')
assert(bounds.camera.left==-130 and bounds.blast.left==-265,'widened bounds must preserve original blast margin')
-- Same-host entry must stop when its destination checkpoint is refused.
local saved_a,saved_b=files['checkpoint-a.txt'],files['checkpoint-b.txt']
fail_write=true
ps[1].x=104;ps[1].y=0;step();step(4);step();settle()
assert(not roguelite_state().active and roguelite_state().menu=='error',
 'refused same-host checkpoint continued gameplay')
assert(files['checkpoint-a.txt']==saved_a and files['checkpoint-b.txt']==saved_b,
 'refused same-host checkpoint changed durable bytes')
local before=roguelite_state().run.frame
tick=tick+1;on_frame()
assert(roguelite_state().run.frame==before,'blocked entry advanced gameplay')
fail_write=false;request=true;settle();click('resume')
assert(roguelite_state().active and roguelite_state().node=='trail' and not ps[2],
 'resume after storage recovery did not activate destination')
for h in pairs(enemies) do on_enemy_defeated({handle=h});enemies[h]=nil end
ps[1].percent=37
-- A refused destination checkpoint must not launch a combat scene.
fail_write=true;ps[1].x=-104;ps[1].y=0;step();step(4);step()
assert(roguelite_state().run.progress.room=='trail' and not ps[2],'refused save changed scene/progress')
fail_write=false
door('left');assert(roguelite_state().node=='arena_a' and ps[2] and cpu[2]=='fight')
assert(ps[1].percent==37,'scene handover healed the player')
assert(ps[2].x==56,'fighter uses authored combat spawn')
assert(roguelite_state().run.id==id and roguelite_state().run.world_seed==seed,'scene handover replaced run')
assert(roguelite_state().run.stocks==1,'scene handover or fall-counter reset charged a life')
assert(roguelite_state().run.hosts.player.slots.assault==equipped,'scene handover changed loadout')
ps[2].stocks=98;tick=tick+1;on_frame();assert(roguelite_state().menu=='reward')
click('reward1')
-- Refused native release retains ownership and refuses scene replacement.
local remove=gd.stage_remove;gd.stage_remove=function()return false end
ps[1].x=104;ps[1].y=0;step();step(4);step()
assert(roguelite_state().run.progress.room=='arena_a' and scene_opts.mode=='vs' and ps[2],
 'cleanup refusal replaced the source scene')
assert(roguelite_state().menu=='error','cleanup refusal must be surfaced')
gd.stage_remove=remove;request=true;settle();assert(roguelite_state().menu=='collection' and not ps[2],'reopen after cleanup refusal: '..tostring(roguelite_state().menu))
click('resume');assert(roguelite_state().node=='arena_a' and ps[2],'resume after cleanup refusal failed')
ps[1].percent=37
door('right');assert(roguelite_state().node=='rest' and not ps[2],'rest must return to player-only')
assert(ps[1].percent==37,'return handover healed the player')
assert(roguelite_state().run.id==id and roguelite_state().run.progress.cleared.arena_a)
assert(roguelite_state().run.stocks==1,'returning to solo changed logical lives')
click('continue')
ps[1].falls=1;tick=tick+1;on_frame()
assert(roguelite_state().run.status=='failure' and roguelite_state().menu=='collection' and not ps[2],
 'final solo fall did not finish the run')
step();step(512);assert(scene_opts.mode=='menu' and not roguelite_state().ready,'B must return to the native menu')
assert(files['checkpoint-a.txt'] or files['checkpoint-b.txt'],'home must retain checkpoint')
on_unload();assert(bounds==baseline,'bounds must restore on unload')
print('player-only exploration/combat scene handover preserves run and progress')
'''
        if terminal:
            test = test[:test.index("ps[1].falls=1;tick=tick+1;on_frame()\nassert(roguelite_state().run.status=='failure'")] + r"""
door('right');assert(roguelite_state().node=='approach')
for h in pairs(enemies) do on_enemy_defeated({handle=h});enemies[h]=nil end
door('right');assert(roguelite_state().node=='boss')
for i=1,2 do ps[2].stocks=98;tick=tick+1;on_frame() end
click('reward1')
local attempts=0;local writer=gd.data_write_atomic
-- The handover destination saves successfully; refuse the finish transaction.
gd.data_write_atomic=function(...) attempts=attempts+1;if attempts>=2 then return false end return writer(...) end
ps[1].x=104;ps[1].y=0;step();step(4);step();settle()
assert(attempts==2,'terminal entry wrote an intermediate arrival checkpoint')
assert(roguelite_state().menu=='error' and not roguelite_state().active and roguelite_state().run.status=='active',
 'refused finish must roll back and freeze')
local a,b=files['checkpoint-a.txt'],files['checkpoint-b.txt']
local frame=roguelite_state().run.frame
tick=tick+1;on_frame();settle()
assert(files['checkpoint-a.txt']==a and files['checkpoint-b.txt']==b and roguelite_state().run.frame==frame,
 'refused finish changed bytes or continued gameplay')
gd.data_write_atomic=function(...) attempts=attempts+1;return writer(...) end
click('retry')
assert(attempts==3 and roguelite_state().run.status=='success' and roguelite_state().menu=='collection',
 'finish retry did not use one durable transaction')
on_unload()
"""
        result = subprocess.run([shutil.which('lua') or shutil.which('lua5.4'), '-'],
                                input=prelude + strict + '(function()\n' + prepare.bundle() + '\nend)()\n' + test,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
