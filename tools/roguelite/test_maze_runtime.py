"""Actual bundled maze runtime with strict queued native-scene doubles."""
import ast
from pathlib import Path
import shutil
import subprocess
import unittest
import json
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
from tools.roguelite import prepare

TREE=ast.parse(Path(__file__).with_name('test_runtime.py').read_text())
PRELUDE=next(ast.literal_eval(n.value) for n in TREE.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PRELUDE' for t in n.targets))
ENGINE=r"""
files['config.txt']='generator=maze'
local lines={};local line_calls=0;local fail_line
local original_read=gd.data_read
gd.data_read=function(n) if n=='config.txt' then return 'generator=maze' end return original_read(n) end
gd.stage_add_line=function(x0,y0,x1,y1,kind,opts)
 line_calls=line_calls+1
 if line_calls==fail_line then return nil,'line allocation refused' end
 serial=serial+1;models[serial]=true
 lines[serial]={x0=x0,y0=y0,x1=x1,y1=y1,kind=kind,opts=opts}
 return serial
end
local remove=gd.stage_remove
gd.stage_remove=function(h)lines[h]=nil;return remove(h) end
local baseline={camera={left=-100,right=100,bottom=-20,top=60},blast={left=-200,right=200,bottom=-100,top=120}}
local bounds=baseline
gd.stage_bounds=function(v)if v==false then bounds=baseline elseif v then bounds=v end return bounds end
"""
HELPERS=r"""
local C=assert(loadfile(SOURCE..'/core.lua'))()
local CP=assert(loadfile(SOURCE..'/checkpoint.lua'))()
local Codec=assert(loadfile(SOURCE..'/codec.lua'))()
local function step(b)controls=b or 0;fixture_scene_tick();on_tick()end
local function settle()for i=1,160 do step()end end
local function press(b)step();step(b);step()end
local function state()return roguelite_state()end
local function click(id)
 local view=assert(state().menu_view);local target
 for _,c in ipairs(view.controls)do if c.id==id then target=c end end
 assert(target,'missing control '..id)
 mx=target.x+target.w/2;my=target.y+target.h/2;mb=0;step();mb=1;step();mb=0;step();mx=-1000;my=-1000;settle()
end
local function decoded()
 local a,b=files['checkpoint-a.txt'],files['checkpoint-b.txt']
 if not a then return assert(CP.decode(b,C,Codec)) end
 if not b then return assert(CP.decode(a,C,Codec)) end
 local ga=tonumber(a:match('^TBD3 (%d+)'));local gb=tonumber(b:match('^TBD3 (%d+)'))
 return assert(CP.decode(ga>gb and a or b,C,Codec))
end
local function clear_current()
 local n=decoded().manifest.nodes[state().node]
 if state().menu=='rest' then click('continue') end
 if (n.kind=='arena' or n.kind=='boss') and not state().run.progress.cleared[n.id] then
  for i=1,(n.kind=='boss' and 2 or 1)do ps[2].stocks=98;tick=tick+1;on_frame()end
  assert(state().menu=='reward');click('reward1')
 end
 for h in pairs(enemies)do on_enemy_defeated({handle=h});enemies[h]=nil end
end
local handover_sides={}
local function travel(e)
 clear_current()
 local manifest=decoded().manifest;local n=manifest.nodes[state().node];local a=n.room.exit_anchors[e.side]
 local destination=manifest.nodes[e.to]
 local combat=destination.kind=='arena' or destination.kind=='boss'
 local handover=combat~=(ps[2]~=nil)
 ps[1].x=a.x;ps[1].y=a.y;press(4);settle()
 assert(state().node==e.to,'maze door missed '..e.side..' to '..e.to)
 if handover and destination.kind~='exit' then
  handover_sides[e.side]=true
  local opposite={left='right',right='left',top='bottom',bottom='top'}
  local side=opposite[e.side];local expected=destination.room.exit_anchors[side]
  local x=expected.x+(side=='left' and 12 or side=='right' and -12 or 0)
  assert(ps[1].x==x and ps[1].y==expected.y+2,
   'handover lost reciprocal '..e.side..' arrival: '..ps[1].x..','..ps[1].y)
 end
end
local function start()
 step();settle();assert(state().menu=='collection' and ps[2]==nil)
 click('start');assert(state().active and state().route_mode=='maze' and ps[2]==nil)
 assert(decoded().manifest.generator_version==3)
end
"""

class MazeRuntimeTests(unittest.TestCase):
    def run_lua(self,body,reload_body=''):
        wrapped=';(function()\n'+prepare.bundle()+'\nend)()\ncommands.rogue_start()\n'
        code='local SOURCE='+json.dumps(str(prepare.SOURCE))+'\n'+PRELUDE+ENGINE+wrapped+HELPERS+body
        if reload_body:
            main=(prepare.SOURCE/'main.lua').read_text()
            resume_bundle=prepare.bundle().replace(main,"Maze.generate=function() error('resume must not regenerate') end\n"+main,1)
            resume_wrapped=';(function()\n'+resume_bundle+'\nend)()\ncommands.rogue_start()\n'
            code+=resume_wrapped+reload_body.replace("-- RELOAD_BUNDLE",resume_wrapped)
        result=subprocess.run([shutil.which('lua') or shutil.which('lua5.4'),'-'],input=code,text=True,capture_output=True)
        if result.returncode:
            import re
            line=re.search(r'stdin:(\d+):',result.stderr)
            if line:result.stderr+='\nFailing Lua: '+code.splitlines()[int(line.group(1))-1]
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_real_wall_kinds_four_sockets_and_scene_handover(self):
        self.run_lua(r"""
start()
local manifest=decoded().manifest;local runid=state().run.id
local count=0;local kinds={}
for _,l in pairs(lines)do count=count+1;kinds[l.kind]=(kinds[l.kind]or 0)+1;assert(l.opts.ledges==false)
 if l.kind=='left_wall'then assert(l.y0<l.y1)elseif l.kind=='right_wall'then assert(l.y0>l.y1)else assert(l.kind=='floor' and l.x0<l.x1)end
end
assert(count==6 and kinds.left_wall==2 and kinds.right_wall==2 and kinds.floor==2)
assert(bounds.camera.bottom==-36 and bounds.camera.top==80)
local visited,sides={},{}
local function walk(id)
 visited[id]=true
 for _,e in ipairs(manifest.nodes[id].exits)do
  if manifest.nodes[e.to].kind~='exit' and not visited[e.to]then
   ps[1].percent=37;local lives=state().run.stocks
   travel(e);sides[e.side]=true
   assert(ps[1].percent==37 and state().run.stocks==lives and state().run.id==runid,'handover changed logical state')
   local kind=manifest.nodes[e.to].kind
   assert((kind=='arena' or kind=='boss')==(ps[2]~=nil),'maze CPU admission wrong')
   walk(e.to)
   local back for _,b in ipairs(manifest.nodes[e.to].exits)do if b.to==id then back=b end end
   travel(assert(back));sides[back.side]=true
  end
 end
end
walk(manifest.start)
assert(sides.left and sides.right and sides.top and sides.bottom,'four physical socket routes not exercised')
assert(handover_sides.top and handover_sides.bottom,'North/South scene handovers not exercised')
local seen=0 for _ in pairs(visited)do seen=seen+1 end assert(seen==11)
on_unload();assert(not next(models) and not next(lines) and bounds==baseline)
""")

    def test_wall_allocation_refusal_releases_owned_collision(self):
        self.run_lua(r"""
step();settle();fail_line=3;click('start')
assert(state().menu=='error' and not state().active)
assert(not next(models) and not next(lines),'refused wall construction leaked collision')
assert(state().run.status=='active' and not state().run.progress.cleared.entry)
""")

    def test_resume_uses_saved_resolved_maze_and_protects_future_generator(self):
        self.run_lua(r"""
start();local saved=decoded();local signature=Codec.encode(saved.manifest)
local oldid=state().run.id;on_unload();request=true;tick=0
""",r"""
step();settle();click('resume')
assert(state().run.id==oldid and Codec.encode(decoded().manifest)==signature,'resume regenerated maze')
local spawn=decoded().manifest.nodes[state().node].room.spawn
assert(ps[1].x==spawn.x and ps[1].y==spawn.y+2,'ordinary Resume inherited a doorway arrival')
local saved=decoded();saved.manifest.generator_version=99
local future=CP.encode({generation=saved.generation+100,profile=C.snapshot(saved.profile),run=C.snapshot(saved.run),manifest=Codec.encode(saved.manifest),roster=saved.roster})
files['checkpoint-a.txt']=future;files['checkpoint-b.txt']=future
on_unload();request=true;tick=0
-- Future generator refusal must preserve bytes rather than replace this run.
-- RELOAD_BUNDLE
step();settle()
assert(state().save_error and files['checkpoint-a.txt']==future and files['checkpoint-b.txt']==future,'future generator checkpoint overwritten')
""")

    def test_seed_mismatch_preserves_checkpoint_and_refuses_regeneration(self):
        self.run_lua(r"""
start();local saved=decoded();saved.manifest.seed=saved.run.world_seed+1
local forged=CP.encode({generation=saved.generation+100,profile=C.snapshot(saved.profile),run=C.snapshot(saved.run),manifest=Codec.encode(saved.manifest),roster=saved.roster})
files['checkpoint-a.txt']=forged;files['checkpoint-b.txt']=forged
on_unload();request=true;tick=0
""",r"""
step();settle()
assert(state().save_error and not state().active)
assert(files['checkpoint-a.txt']==forged and files['checkpoint-b.txt']==forged,'mismatched seed checkpoint overwritten')
""")
