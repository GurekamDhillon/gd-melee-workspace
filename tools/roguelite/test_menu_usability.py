"""Controller routing contracts, executed by real Lua."""
import shutil, subprocess, unittest
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source
class MenuUsabilityTests(unittest.TestCase):
 def test_primary_focus_back_and_readable_names(self):
  lua=shutil.which('lua') or shutil.which('lua5.4')
  self.assertIsNotNone(lua, 'Lua interpreter required')
  program="""Core=assert(loadfile(arg[1]..'/core.lua'))()
local M=assert(loadfile(arg[1]..'/menus.lua'))()
local p=Core.new_profile(321)
local ctx={menu='collection',profile=p,starter='g1'}
local s=M.new()
assert(M.view(s,ctx).title=='SUPERTIME ENVOY / GENES')
assert(M.update(s,ctx,{confirm=true}).kind=='start','first A must start')
ctx.run=Core.new_run(p);s=M.new()
assert(M.update(s,ctx,{confirm=true}).kind=='resume','saved run must be primary')
for _,b in ipairs(M.view(s,ctx).controls) do if b.id=='gene:g1' then assert(b.label:find('Fire',1,true)) end end
ctx.back_action={kind='home'}
assert(M.update(s,ctx,{back=true}).kind=='home')
s.section='parents'
assert(M.update(s,ctx,{back=true}).kind=='home' and s.section=='main')
ctx.menu='rest';ctx.back_action=nil;s=M.new()
assert(M.update(s,ctx,{confirm=true}).kind=='continue')
assert(M.update(s,ctx,{back=true})==nil)
ctx.back_action={kind='continue'}
assert(M.update(s,ctx,{back=true}).kind=='continue')
print('controller usability contracts passed')"""
  result=subprocess.run([lua,'-',str(game_source.ROGUELITE)],input=program,text=True,capture_output=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)

 def test_reward_preview_budget_and_runtime_identity(self):
  lua=shutil.which('lua') or shutil.which('lua5.4')
  self.assertIsNotNone(lua)
  program=r"""Core=assert(loadfile(arg[1]..'/core.lua'))()
local M=assert(loadfile(arg[1]..'/menus.lua'))()
local p=Core.new_profile(321);local r=Core.new_run(p)
for _,state in pairs(r.runtime) do for i=1,512 do state.seen['event_'..i]=0 end end
local before=assert(Core.snapshot(r))
local s=M.new();local ctx={menu='reward',profile=p,run=r,node={id='arena_a'}}
local instructions=0
debug.sethook(function() instructions=instructions+1000;assert(instructions<=500000,'reward menu exceeded instruction budget') end,'',1000)
local v=M.view(s,ctx);s.focus='reward1'
local action=M.update(s,ctx,{confirm=true})
local result=M.apply(ctx,action)
debug.sethook()
assert(result.ok and result.run and result.reward_claimed)
assert(Core.snapshot(r)==before,'reward preview/mutation changed live source')
local copied=result.run;local id=copied.hosts.player.slots.assault
assert(copied.runtime[id]==copied.hosts.player.state.assault,'copy lost shared runtime identity')
assert(copied.runtime[id]~=r.runtime[id] and copied.runtime[id].seen~=r.runtime[id].seen,'copy aliases source')
assert(copied.runtime[id].seen.event_512==0,'copy lost event history')
assert(Core.snapshot(copied),'reward result failed save validation')
print('reward menu instructions '..instructions)
"""
  result=subprocess.run([lua,'-',str(game_source.ROGUELITE)],input=program,text=True,capture_output=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)

 def test_widescreen_canvas_matches_pointer_controls(self):
  lua=shutil.which('lua') or shutil.which('lua5.4')
  self.assertIsNotNone(lua)
  program=r"""Core=assert(loadfile(arg[1]..'/core.lua'))()
local M=assert(loadfile(arg[1]..'/menus.lua'))()
local p=Core.new_profile(321);local r=Core.new_run(p)
for _,width in ipairs({640,480*16/9,480*21/9}) do
 local area={x=0,y=0,w=width,h=480};local drawn={};local full=false
 local function rect(x,y,w,h)
  assert(x>=0 and y>=0 and x+w<=width+.01 and y+h<=480.01,'draw outside safe area')
 end
 gd={safe_area=function()return area end,fill=function(x,y,w,h)rect(x,y,w,h);if x==0 and y==0 and math.abs(w-width)<.001 and h==480 then full=true end end,
 kit={panel=function(x,y,w,h)rect(x,y,w,h)end,
 button=function(x,y,w,label,selected,opts)rect(x,y,w,opts.h);drawn[#drawn+1]={x=x,y=y,w=w,h=opts.h}end,
 text=function(x,y,text,role,color,align,opts)assert(x>=0 and x+opts.max_w<=width+.01 and y<=480);assert(opts.scale==nil,'fonts must retain natural size')end,
 icon=function(name,x,y,scale)rect(x,y,16*scale,16*scale)end}}
 for _,menu in ipairs({'collection','rest','reward','error','onboarding','settings'}) do
  local ctx={menu=menu,profile=p,run=r,starter='g1',node={id='arena_a'},retry=true}
  local state=M.new();local view=M.view(state,ctx)
  for _,b in ipairs(view.controls) do rect(b.x,b.y,b.w,b.h) end
  if menu=='collection' then
   local start
   for _,b in ipairs(view.controls)do if b.id=='start'then start=b end end
   assert(start.w==274*width/640,'primary action did not expand with canvas')
   local action=M.update(state,ctx,{mx=start.x+start.w-2,my=start.y+5,click=true})
   assert(action.kind=='start','widescreen pointer missed primary control')
  end
  drawn={};M.draw(state,ctx)
  if menu~='reward' then for _,b in ipairs(view.controls)do
   local match=false
   for _,d in ipairs(drawn)do if math.abs(b.x-d.x)<.001 and math.abs(b.w-d.w)<.001 and b.y==d.y and b.h==d.h then match=true end end
   assert(match,'draw/hit-test layout differs for '..b.id)
  end end
 end
 assert(full,'menu left the widescreen canvas unused')
end
"""
  result=subprocess.run([lua,'-',str(game_source.ROGUELITE)],input=program,text=True,capture_output=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
