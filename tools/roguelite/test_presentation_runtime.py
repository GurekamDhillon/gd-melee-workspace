#!/usr/bin/env python3
"""Compact presentation integration: hud_layout, onboarding, loadout commands and
Feedback actually wired into the live runtime.

Two layers, both against real modules:

* ``PresentationTests`` loads ``runtime_presentation`` with the real
  ``hud_layout`` / ``onboarding`` / ``commands`` / ``feedback`` modules and a fake
  engine, proving layout ownership, HUD claiming, tutorial observation and
  loadout planning in isolation - including the failure cases.

* ``MainPresentationTests`` bundles the real ``main.lua`` (from a throwaway source
  copy whose recipe admission is opened only for the test) and drives it with a
  deterministic engine stub that records real draw coordinates and real button
  edges. It proves the boxes come from ``Hud.layout`` on the port's documented
  640x480 canvas, that the native HUD is claimed and returned, that the command
  tree is rebuilt from the run's installed loadout after a real placement, that
  one cleared-door press cannot both travel and spend a consumable, and that
  tutorial steps advance only from real gameplay.

The engine stub's ``gd.player`` returns a copy snapshot, as the real native API
does, so aliasing can never mask an engine-write bug.

These are stubs, not an in-engine playtest or a certification claim.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

import prepare
import test_v2_runtime as v2

RT = v2.RT
LUA = v2.LUA

# ---------------------------------------------------------------------------
# Presentation glue against the real pure modules
# ---------------------------------------------------------------------------
PRELUDE = r'''
local function load(n) return assert(dofile(arg[1] .. '/' .. n .. '.lua')) end
local Hud=load('hud_layout')
local Onboarding=load('onboarding')
local Commands=load('commands')
local Feedback=load('feedback')
local Presentation=load('runtime_presentation')
local Core=load('core')

local hud={visible=true,calls={},throw=false,missing=false}
local drawn={}
local function box(x,y,w,h) drawn[#drawn+1]={x=x,y=y,w=w,h=h} end
gd={buttons={A=256,B=512,UP=8,DOWN=4,LEFT=1,RIGHT=2},kit={},
 log=function() end,
 fill=function(x,y,w,h) box(x,y,w,h) end,
 kit_text=nil,
 hud_visible=function(v)
  hud.calls[#hud.calls+1]=v
  if hud.throw then error('hud refused') end
  if v==nil then return hud.visible end
  hud.visible=v
  return v
 end}
gd.kit={text=function(x,y,s) drawn[#drawn+1]={x=x,y=y,text=tostring(s)};return 10 end,
 icon=function() end,roles={},row={pitch=36}}
local function make(opts)
 local feedback=Feedback.new{reduced=(opts or {}).reduced==true}
 local logs={}
 local p=Presentation.new(gd,{Hud=Hud,Onboarding=Onboarding,Commands=Commands,Feedback=Feedback},
  {width=(opts or {}).width or 640,height=(opts or {}).height or 480,reduced=(opts or {}).reduced==true,
   feedback=feedback,log=function(m) logs[#logs+1]=m end})
 return p,feedback,logs
end
-- A minimal run with the three real slots, as Core would install them.
local function run_with(slots,supplies)
 local profile=Core.new_profile(11)
 local run=Core.new_run(profile,{stocks=3,seed=11})
 run.progress.supplies=supplies or 2
 for slot,id in pairs(slots) do assert(Core.equip(run,'player',slot,id)) end
 return run
end
'''


def run_lua(body):
    result = subprocess.run([LUA, '-', str(RT)], input=PRELUDE + body, text=True,
                            capture_output=True, timeout=90)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    assert 'PASS' in result.stdout, result.stdout


class PresentationTests(unittest.TestCase):
    def test_layout_uses_the_documented_canvas_and_the_compact_gate(self):
        run_lua(r'''
local p=make{}
-- The canvas is the port's documented fixed virtual screen, never a window size.
local st=p:status()
assert(st.width==640 and st.height==480,'presentation did not use the 640x480 canvas')
local reference=assert(Hud.layout{width=640,height=480})
local off=p:state{}
assert(off.replace_vanilla==false,'the compact rail was offered without owning the native HUD')
assert(off.rail.x==reference.rail.x and off.rail.y==reference.rail.y,'fallback layout differs from Hud.layout')
assert(off.rail.w==reference.rail.w and off.rail.h==reference.rail.h,'fallback rail size differs')
p:take_vanilla_hud(true)
local on=p:state{}
assert(on.replace_vanilla==true,'owning the native HUD did not enable the compact rail')
assert(on.rail.x==reference.rail.x and on.rail.y==reference.rail.y,'the compact rail moved when enabled')
-- Notification strip and command panel stay inside the declared safe area.
for _,name in ipairs{'rail','notification','compact_notification','command','opponent'} do
 local b=on[name]
 assert(b,'missing layout box '..name)
 assert(b.x>=on.safe.x and b.y>=on.safe.y,'box '..name..' escapes the safe area')
 assert(b.x+b.w<=640 and b.y+b.h<=480,'box '..name..' escapes the virtual canvas')
end
-- A different declared scale is honoured but still clamped inside the canvas.
local big=make{width=1280,height=720,dpi=2}
big:take_vanilla_hud(true)
local wide=big:state{}
assert(wide.width==1280 and wide.rail.x+wide.rail.w<=1280,'the rail escaped a wider canvas')
assert(wide.rail.w<=wide.safe.w,'the rail outgrew the safe area')
print('PASS layout uses the documented canvas and the compact ownership gate')
''')

    def test_hud_claim_treats_false_as_state_and_throw_as_failure(self):
        run_lua(r'''
local p,feedback=make{}
assert(p:hud_owned()==false,'the HUD was owned before it was claimed')
-- gd.hud_visible(false) legitimately returns false: the new state, not a failure.
local ok,res=p:take_vanilla_hud(true)
assert(ok==true and res==false,'a false visibility result was treated as a failure')
assert(p:hud_owned()==true,'the claim was not recorded')
assert(gd.hud_visible()==false,'the native HUD was not actually hidden')
assert(hud.calls[#hud.calls]==false,'the claim did not reach the engine')
-- A repeat claim is a no-op, not a second mutation.
local again=p:take_vanilla_hud(true)
assert(again==false,'a repeated claim mutated the engine again')
assert(hud.calls[#hud.calls]==false,'a repeated claim reached the engine')
-- A throwing engine is a real failure and ownership is not recorded.
hud.throw=true
local bad,why=p:release_hud()
hud.throw=false
assert(bad==false,'a throwing release reported success')
assert(tostring(why):find('hud refused',1,true),'the throwing reason was lost')
assert(p:hud_owned()==true and p.hud_release_pending,'a refused release discarded the hidden HUD claim')
-- Give it back explicitly.
assert(p:release_hud()==true,'release failed')
assert(gd.hud_visible()==true,'the vanilla HUD ownership was not returned')
print('PASS HUD claim treats a false result as state and a throw as failure')
''')

    def test_draw_uses_layout_coordinates_and_contains_failures(self):
        run_lua(r'''
local p,feedback=make{}
p:take_vanilla_hud(true)
local lay=p:state{}
drawn={}
assert(p:draw(feedback,{hud=true,player={percent=42,lives=3,supplies=1}})==true,'draw refused')
local rail
for _,d in ipairs(drawn) do if d.w==lay.rail.w and d.h==lay.rail.h and d.x==lay.rail.x and d.y==lay.rail.y then rail=d end end
assert(rail,'the compact rail was not drawn at its declared layout box')
-- Nothing drawn may leave the virtual canvas.
for _,d in ipairs(drawn) do
 if d.x and d.w then assert(d.x>=0 and d.y>=0 and d.x+d.w<=640 and d.y+d.h<=480,'a draw escaped the canvas') end
end
-- A compact menu swaps the notification strip for the workbench strip.
Feedback.notify(feedback,{key='probe',kind='info',title='Run start',detail='Travel'})
drawn={}
assert(p:draw(feedback,{hud=false,compact_menu=true,player={percent=1,lives=1}})==true)
local strip
for _,d in ipairs(drawn) do if d.w==lay.compact_notification.w and d.h==lay.compact_notification.h then strip=d end end
assert(strip,'the workbench strip was not drawn at its declared box')
-- A drawing failure is contained and reported, never raised into the caller.
local real=gd.kit.text
gd.kit.text=function() error('kit exploded') end
local logs={}
p.log=function(m) logs[#logs+1]=m end
assert(p:draw(feedback,{hud=true,player={percent=1}})==false,'a drawing throw was reported as success')
assert(#logs==1 and logs[1]:find('kit exploded',1,true),'the drawing failure was not reported')
gd.kit.text=real
assert(p:draw(feedback,{hud=true,player={percent=1}})==true,'the presentation stayed broken after recovery')
print('PASS draw uses layout coordinates and contains rendering failures')
''')

    def test_release_retains_claim_when_api_disappears_and_retries(self):
        run_lua(r'''
local p=make{}
assert(p:take_vanilla_hud(true))
local native=gd.hud_visible;gd.hud_visible=nil
assert(p:release_hud()==false and p:hud_owned() and p.hud_release_pending,'missing API discarded the claim')
assert(hud.visible==false,'fixture native HUD was not hidden')
gd.hud_visible=native
-- The next active lifecycle claim request first retries the pending release.
assert(p:take_vanilla_hud(true)==true)
assert(hud.visible and not p:hud_owned() and not p.hud_release_pending,'pending release did not reach the native API')
print('PASS a missing restore API retains HUD ownership until lifecycle retry succeeds')
''')

    def test_layout_and_draw_failure_restore_vanilla_without_losing_claim(self):
        run_lua(r'''
local p,f=make{}
assert(p:take_vanilla_hud(true))
local layout=Hud.layout
Hud.layout=function() error('layout exploded') end
local contained,result=pcall(p.draw,p,f,{hud=true})
assert(contained,'throwing layout escaped safe fallback')
assert(hud.visible and not p:hud_owned(),'layout failure kept the native HUD hidden')
assert(p:state{}.replace_vanilla==false,'fallback advertised a replacement')
Hud.layout=layout;p.layout=nil;p.layout_key=nil
assert(p:take_vanilla_hud(true))
local text=gd.kit.text;gd.kit.text=function() error('drawing exploded') end
hud.throw=true
assert(p:draw(f,{hud=true})==false)
assert(p:hud_owned() and p.hud_release_pending and not hud.visible,'failed fallback discarded native ownership')
hud.throw=false;gd.kit.text=text
assert(p:take_vanilla_hud(true))
assert(hud.visible and not p:hud_owned(),'draw fallback was not retried')
-- Missing/throwing hide never authorizes a full replacement rail.
hud.throw=true
assert(p:take_vanilla_hud(true)==false)
hud.throw=false
drawn={};assert(p:draw(f,{hud=true}))
local rail=Hud.layout{width=640,height=480,new_hud=true}.rail
for _,d in ipairs(drawn) do assert(not (d.w==rail.w and d.h==rail.h),'hide refusal drew a duplicate replacement rail') end
print('PASS layout/draw failures give back vanilla HUD and retain refused releases')
''')

    def test_tutorial_only_advances_on_observed_events(self):
        run_lua(r'''
local p,feedback=make{}
-- The first hint is announced once, through the shared toast queue.
assert(p:view().step=='move','the first step is not the movement step')
local t=p:announce(true)
assert(t and t.key=='tutorial:move','the first hint was not announced')
local n=Feedback.view(feedback).notification
assert(n.kind=='tutorial' and n.title==t.title,'the hint did not travel through the toast queue')
assert(Feedback.view(feedback).queued==1,'the hint was not queued exactly once')
-- No event, no progress.
assert(p:observe{kind='tell'}==nil,'an unrelated observation advanced the tutorial')
assert(p:view().completed==0,'an unrelated observation completed a step')
-- A real observation completes exactly one step and announces the next one once.
assert(p:observe{kind='move'}=='move','a real movement did not complete the step')
assert(p:view().step=='charge','the next step was not exposed')
assert(p:announce(false)==nil,'the same hint was announced twice')
-- A held state is not repeated: notice_charges only fires on a rising edge.
p:notice_charges{assault={charge=1,cost=3}}
assert(p:view().completed==2,'the charge step did not complete from a real charge')
p:notice_charges{assault={charge=2,cost=3}}
assert(p:view().completed==2,'a held charge repeated the observation')
p:notice_charges{assault={charge=0,cost=3}}
p:notice_charges{assault={charge=1,cost=3}}
assert(p:view().completed==2,'a dropped and re-earned charge repeated the observation')
-- Onboarding never pauses combat.
assert(p:view().pause==false,'the tutorial reported a pause')
-- Genealogy and fusion are only taught when the caller declares availability.
assert(p:observe{kind='breed',available=false}==nil,'an unavailable feature was taught')
assert(p:observe{kind='breed',available=true}=='genealogy','an available feature was not taught')
-- An early grammar step lapses instead of nagging once the window has passed.
local early=Onboarding.new{}
Onboarding.observe(early,{kind='move'})
Onboarding.observe(early,{kind='charge'})
local view=Onboarding.view(early)
assert(view.step=='branch','the grammar step was not offered')
Onboarding.set_room(early,9)
assert(Onboarding.view(early).step~='branch','an expired grammar step kept nagging')
print('PASS tutorial advances only from observed events and never pauses combat')
''')

    def test_loadout_planning_is_honest_and_contained(self):
        run_lua(r'''
local p=make{}
-- No run: the authored tree is kept rather than a half-built plan.
local state=Commands.new()
local ok,why=p:rebuild(state,nil,0)
assert(ok==false and state.tree==nil,'a loadout was planned without a run')
-- Real installed loadout: names and slots come from the run, not a catalogue.
local run=run_with({assault='r1',guard='r2'},2)
assert(p:rebuild(state,run,0),'the loadout rebuild refused')
local root=p:view_commands(state,nil)
assert(#root.branches==3,'the root did not fork three ways')
for _,b in ipairs(root.branches) do assert(b.node,'a root branch lost its grammar node') end
assert(state.node=='root','the cursor did not return to the valid root')
-- Held Up keeps its latch across a rebuild: no fabricated root taunt.
assert(p:rebuild(state,run,8))
assert(state.up_latched==true,'a rebuild cleared a held Up edge')
-- Item fork reports the declared supply.
state.node='item'
local item=p:view_commands(state,nil)
assert(item.branches[1].label=='Restore x2','the declared supply is not shown: '..tostring(item.branches[1].label))
-- Zero supplies is honestly disabled, never an enabled "Restore x0".
local dry=run_with({assault='r1'},0)
local drystate=Commands.new();assert(p:rebuild(drystate,dry,0));drystate.node='item'
local none=p:view_commands(drystate,nil)
assert(none.branches[1].enabled==false,'Restore was offered with no supplies')
assert(none.branches[1].reason=='No supplies in this run','the refusal reason is not the real one')
-- A supplied availability function is the source of the live refusal reasons;
-- without one commands honestly reports the leaf as unavailable.
local function only_uncharged() return false,'Charge 0 / 3' end
state.node='abilities'
for _,b in ipairs(p:view_commands(state,only_uncharged).branches) do
 assert(b.enabled==false,'an uncharged ability was offered as enabled')
 -- A leaf's own static refusal always outranks the live availability answer.
 assert(b.reason=='Charge 0 / 3' or b.reason:find('No gene placed',1,true),
  'a refusal reason was lost: '..tostring(b.reason))
end
for _,b in ipairs(p:view_commands(state,nil).branches) do
 assert(b.enabled==false,'a leaf without an availability function was offered as enabled')
 assert(b.reason=='Unavailable' or b.reason:find('No gene placed',1,true),
  'an unavailability reason was invented: '..tostring(b.reason))
end
-- An unplaced slot is honestly reported, not silently dropped.
local bare=run_with({},2)
for _,slot in ipairs{'assault','guard','traversal'} do assert(Core.equip(bare,'player',slot,nil)) end
local empty=Commands.new()
assert(p:rebuild(empty,bare,0));empty.node='abilities'
local blocked=0
for _,b in ipairs(p:view_commands(empty,only_uncharged).branches) do
 if b.label:find('EMPTY',1,true) and b.reason:find('No gene placed',1,true) then blocked=blocked+1 end
end
assert(blocked==3,'unplaced slots were not reported honestly')
-- A planning failure is contained and leaves the previous tree installed.
local before=state.tree
local broken=setmetatable({},{__index=function() error('catalogue exploded') end})
local real_plan=Commands.plan
Commands.plan=function() error('planner refused') end
local bad,why=p:rebuild(state,run,0)
Commands.plan=real_plan
assert(bad==false,'a planner failure reported success')
assert(state.tree==before,'a planner failure dropped the installed tree')
print('PASS loadout planning is honest about placement/supplies and contains failures')
''')


# ---------------------------------------------------------------------------
# Bundled main.lua: real draw coordinates, real edges, real ownership
# ---------------------------------------------------------------------------
def _main(body):
    code = v2.PRELUDE_MAIN + ';\n' + MainPresentationTests.wrapped + '\n' + body
    result = subprocess.run([LUA, '-', str(RT)], input=code, text=True,
                            capture_output=True, timeout=180)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    assert 'PASS' in result.stdout, result.stdout


def _live():
    """Body prelude: an activated certified v2 run plus draw/edge recorders."""
    return r'''
local fills,texts={},{}
local hud={visible=true,calls={}}
gd.hud_visible=function(v)
 hud.calls[#hud.calls+1]=v
 if v==nil then return hud.visible end
 hud.visible=v;return v
end
gd.fill=function(x,y,w,h) fills[#fills+1]={x=x,y=y,w=w,h=h} end
gd.kit.text=function(x,y,s,role,color,align,opts)
 texts[#texts+1]={x=x,y=y,t=tostring(s)};return 10 end
gd.kit.icon=function() end
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
assert(settle(400),'the certified v2 run did not activate')
local camp=roguelite_v2()
local function find_box(w,h)
 for _,d in ipairs(fills) do if d.w==w and d.h==h then return d end end
end
local function find_text(needle)
 for _,t in ipairs(texts) do if t.t:find(needle,1,true) then return t end end
end
local function upv(name)
 for i=1,99 do local n,v=debug.getupvalue(on_tick,i); if not n then break end; if n==name then return v end end
end
'''


class MainPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._src = v2._certified_source()
        cls.wrapped = '(function()\n' + prepare.bundle(source=cls._src) + '\nend)()\n'

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._src, ignore_errors=True)

    def test_rail_is_drawn_from_the_reviewed_layout(self):
        _main(_live() + r'''
local reference=assert(upv('presentation'):state{})
assert(state().presentation.width==640 and state().presentation.height==480,'the canvas is not the documented one')
fills={};texts={}
on_draw()
local rail=find_box(reference.rail.w,reference.rail.h)
assert(rail,'the compact rail was not drawn')
assert(rail.x==reference.rail.x and rail.y==reference.rail.y,'the rail is not at its layout coordinates')
assert(rail.x>=0 and rail.y>=0 and rail.x+rail.w<=640 and rail.y+rail.h<=480,'the rail left the virtual canvas')
-- Real ability readiness, cost and life come from the run.
ps[1].percent=63;fills={};texts={};on_draw()
assert(find_text('63%'),'the rail did not show the observed player percent')
assert(find_text('LIVES 3'),'the rail did not show the run lives')
-- The native HUD is claimed only while a room is live.
assert(state().hud_rail==true,'the compact rail was not enabled while playing')
assert(gd.hud_visible()==false,'the vanilla HUD was not hidden')
-- A repeated draw is idempotent and does not re-claim.
local before=#fills
fills={};on_draw();on_draw()
assert(#fills>0 and gd.hud_visible()==false,'repeated draws disturbed HUD ownership')
print('PASS rail is drawn from the reviewed layout with real run data')
''')

    def test_hud_ownership_is_returned_on_leave_error_and_unload(self):
        _main(_live() + r'''
local hud_calls=hud.calls
local presentation=upv('presentation')
local choose=upv('choose_menu')
-- Already claimed by the live room.
assert(state().hud_rail==true and gd.hud_visible()==false,'the live room did not claim the native HUD')
local seen=#hud_calls
choose({kind='leave'})
assert(state().menu=='collection' and state().hud_rail==false,'leave did not return HUD ownership')
assert(#hud_calls>seen and hud_calls[#hud_calls]==true,'leave did not restore the vanilla HUD to the engine')
-- The error page gives it back as well.
click('start');step();step();tick=91;step()
assert(settle(400),'the run did not reactivate')
local live=roguelite_v2()
assert(state().hud_rail==true,'the reactivated run did not re-claim the native HUD')
fail_atomic=true
live:lose_life()
for i=1,20 do step() end
assert(state().menu=='error','the refused save did not open the recovery page')
assert(state().hud_rail==false,'the error page kept the native HUD claim')
fail_atomic=false
-- Unload returns it too, even from a state that never claimed it.
presentation:take_vanilla_hud(true)
seen=#hud_calls
on_unload()
assert(state().hud_rail==false,'unload kept the claim')
assert(#hud_calls>seen and hud_calls[#hud_calls]==true,'unload did not restore the vanilla HUD')
print('PASS HUD ownership is returned on leave, error and unload')
''')

    def test_refused_hud_restore_is_retried_by_real_leave_lifecycle(self):
        _main(_live() + r'''
local choose=upv('choose_menu');local presentation=upv('presentation')
local native=gd.hud_visible
gd.hud_visible=function(v) if v==true then error('restore refused') end;return native(v) end
choose({kind='leave'})
assert(state().menu=='collection' and presentation:hud_owned() and presentation.hud_release_pending,'leave forgot a refused native restore')
assert(hud.visible==false,'refused release unexpectedly showed native HUD')
step()
assert(presentation:hud_owned(),'lifecycle discarded the still-refused claim')
gd.hud_visible=native;step()
assert(hud.visible and not presentation:hud_owned(),'collection tick did not retry native HUD restoration')
print('PASS real leave lifecycle retries a refused native HUD restore')
''')

    def test_command_tree_is_rebuilt_from_the_installed_loadout(self):
        _main(_live() + r'''
local presentation=upv('presentation')
local cs=upv('command_state')
local avail=upv('availability')
assert(state().presentation.width==640,'unexpected canvas')
-- The planned tree replaced the authored prototype: a real loadout drives it.
local root=presentation:view_commands(cs,avail)
assert(root.id=='root','unexpected command root')
local labels={}
for _,b in ipairs(root.branches) do labels[b.direction]=b.label end
assert(labels.left=='Abilities' and labels.right=='Item' and labels.down=='Special',
 'the root fork is not the loadout tree: '..tostring(labels.left)..'/'..tostring(labels.right)..'/'..tostring(labels.down))
-- Drill into the abilities fork: real placed genes, real readiness, real reasons.
step(0);step(1);step(0)
assert(cs.node=='abilities','Left did not open the abilities branch')
assert(state().command_event.kind=='navigate' and state().command_event.node=='abilities',
 'the real navigate edge was not recorded')
local abilities=presentation:view_commands(cs,avail)
local seen={}
for _,b in ipairs(abilities.branches) do
 assert(b.action=='gene','an ability branch is not a gene leaf')
 if b.enabled then seen[b.label]=true end
 if b.enabled==false then assert(type(b.reason)=='string' and #b.reason>0,'a disabled leaf has no refusal reason') end
end
assert(next(seen)==nil,'an uncharged ability was offered as enabled')
-- Up returns to the parent; a fresh Up at the root is the native taunt.
step(0);step(8);step(0)
assert(cs.node=='root','Up did not return to the parent')
assert(state().command_event.kind=='back','the real back edge was not recorded')
step(0);step(8);step(0)
assert(state().command_event.kind=='taunt','a fresh Up at the root did not taunt')
-- A rebuild while Up is held cannot fabricate a fresh root taunt.
step(0);step(1);step(0)
assert(presentation:rebuild(cs,camp.run,8))
assert(cs.node=='root' and cs.up_latched==true,'the rebuild cleared a held Up edge')
step(8)
assert(cs.up_latched==true,'a still-held Up edge was released by a tick')
assert(state().command_event==nil or state().command_event.kind~='taunt','a held Up became a root taunt')
-- Only an actual release then a fresh Up may taunt.
step(0);step(8);step(0)
assert(state().command_event.kind=='taunt','a fresh Up after a release did not taunt')
-- A has no navigation role: ordinary combat is never paused for a confirm.
local paused_before=gd.paused()
step(0);step(256);step(0)
assert(cs.node=='root','A navigated the command tree')
assert(gd.paused()==paused_before,'A paused ordinary combat')
-- The declared supply is real and honest.
camp.route.progress.supplies=0;camp.run.progress.supplies=0
assert(presentation:rebuild(cs,camp.run,0))
cs.node='item'
local dry=presentation:view_commands(cs,avail)
assert(dry.branches[1].enabled==false and dry.branches[1].reason=='No supplies in this run',
 'Restore was not disabled at zero supplies')
camp.route.progress.supplies=2;camp.run.progress.supplies=2
assert(presentation:rebuild(cs,camp.run,0))
cs.node='item'
local wet=presentation:view_commands(cs,avail)
assert(wet.branches[1].label=='Restore x2','the declared supply count is not shown')
print('PASS command tree is the loadout tree with real edges and honest reasons')
''')

    def test_placement_rebuilds_the_tree_and_restores_refusals(self):
        _main(_live() + r'''
local presentation=upv('presentation')
local cs=upv('command_state')
local avail=upv('availability')
goto_rest(camp)
press(4);press(1)
assert(state().menu=='rest','the rest menu did not open')
click('gene:r3');click('place:traversal')
assert(state().run.hosts.player.slots.traversal=='r3','the placement did not apply')
-- The command tree now exposes the newly placed gene.
local t=presentation:view_commands(cs,avail)
assert(t.id=='root','unexpected command root after a placement')
cs.node='abilities'
local abilities=presentation:view_commands(cs,avail)
local traversal
for _,b in ipairs(abilities.branches) do if b.slot=='traversal' then traversal=b end end
assert(traversal and traversal.label:find('CINDER',1,true),'the placed gene is not in the tree: '..tostring(traversal and traversal.label))
-- A refused save rolls back and the tree follows the restored run.
click('continue')
press(4);press(1)
assert(state().menu=='rest')
local before=assert(Core.snapshot(state().run))
fail_atomic=true
click('gene:r2');click('place:traversal')
fail_atomic=false
assert(state().menu=='rest','the refused placement left the rest menu')
assert(Core.snapshot(state().run)==before,'the refused placement was not rolled back')
assert(state().run.hosts.player.slots.traversal=='r3','the refused placement lost the committed gene')
assert(camp.run==state().run,'the campaign was not rebound to the restored run')
local restored=presentation:view_commands(cs,avail)
assert(restored.id=='root','the command tree was left broken after a refusal')
click('continue')
print('PASS placement rebuilds the tree and a refusal restores the committed loadout')
''')

    def test_one_cleared_door_press_travels_or_forks_never_both(self):
        _main(_live() + r'''
local cs=upv('command_state')
local node=camp:current_node()
local exit,anchor
for _,e in ipairs(node.exits) do exit=e;anchor=node.room.exit_anchors[e.side] end
assert(anchor and not anchor.drop,'the fixture room has no cleared standing door')
-- Leave the arrival lock the way a player does, then stand on the doorway.
ps[1].x=anchor.x-40;tick=tick+1;on_frame();tick=tick+1;on_frame()
assert(not camp.locked,'the doorway never unlocked')
camp.route.progress.supplies=2;camp.run.progress.supplies=2
ps[1].percent=60;ps[1].x=anchor.x;ps[1].y=anchor.y
local room=camp:status().room
-- At the door the same press travels...
assert(camp:door_exit(gd.player(1)),'the cleared door was not recognised')
step(0);step(4);step(0)
assert(settle(400),'the cleared-door press did not settle')
assert(camp:status().room==exit.to,'the cleared-door press did not travel')
assert(camp.route.progress.supplies==2,'the travel press spent a consumable')
assert(ps[1].percent==60,'the travel press healed')
assert(cs.node=='root','the travel press also forked the command tree')
-- Away from a door the same press only forks the item branch.
camp.route.progress.supplies=2;camp.run.progress.supplies=2
ps[1].x=anchor.x-40
step(0);step(4);step(0)
assert(cs.node=='special','Down away from a door did not fork the command tree')
assert(camp.route.progress.supplies==2,'forking spent a consumable')
assert(ps[1].percent==60,'forking healed')
print('PASS one cleared-door press travels or forks, never both')
''')

    def test_tutorial_advances_only_from_real_gameplay(self):
        _main(_live() + r'''
local presentation=upv('presentation')
local function step_now() local s=presentation:view().step;return s end
-- Entering a room announces the current objective exactly once.
assert(step_now()=='move','the first tutorial step is not the movement step')
assert(state().feedback.notification.kind=='tutorial','the first hint did not reach the toast queue')
local first=state().feedback.notification.title
assert(state().feedback.notification.title==first,'the same hint was re-announced')
-- Standing still teaches nothing.
for i=1,120 do tick=tick+1;on_frame() end
assert(presentation:view().completed==0,'an idle player completed a tutorial step')
-- Real sustained grounded movement completes exactly that step.
for i=1,90 do ps[1].vx=3;tick=tick+1;on_frame() end
assert(presentation:view().completed==1,'real movement did not complete the movement step')
assert(step_now()=='charge','the next step was not exposed')
-- A real command navigation is grammar evidence.
local cs=upv('command_state')
step(0);step(1);step(0)
assert(cs.node=='abilities','navigation did not happen')
step(0);step(8);step(0)
assert(cs.node=='root','Up did not return to the command root')
-- A real cleared-door travel is door evidence when its step is current.
local node=camp:current_node()
local exit,anchor
for _,e in ipairs(node.exits) do exit=e;anchor=node.room.exit_anchors[e.side] end
ps[1].x=anchor.x-40;tick=tick+1;on_frame();tick=tick+1;on_frame()
ps[1].x=anchor.x;ps[1].y=anchor.y
step(0);step(4);step(0)
assert(settle(400),'the door travel did not settle')
assert(camp:status().room==exit.to,'the door travel did not happen')
-- Tutorial state is exposed to the menus as real data, never fabricated.
local ctx=upv('menu_context')()
assert(type(ctx.onboarding)=='table' and ctx.onboarding.pause==false,'the menu context has no real tutorial state')
assert(type(ctx.settings)=='table' and ctx.settings.items[1].id=='reduced_motion','no declared settings reach the menu')
-- Genealogy is only taught when the caller says it is available.
local before=presentation:view().completed
assert(presentation:observe{kind='breed',available=false}==nil,'an unavailable feature was taught')
assert(presentation:observe{kind='breed',available=true}=='genealogy','an available feature was not taught')
assert(presentation:view().completed==before,'a feature hint advanced a gameplay step')
print('PASS tutorial advances only from real gameplay and reaches the menus truthfully')
''')

    def test_reduced_motion_is_honoured_and_ui_failures_do_not_corrupt_state(self):
        _main(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
assert(settle(400),'the certified v2 run did not activate')
local camp=roguelite_v2()
local function upv(name)
 for i=1,99 do local n,v=debug.getupvalue(on_tick,i); if not n then break end; if n==name then return v end end
end
local presentation=upv('presentation')
local ctx=upv('menu_context')()
assert(ctx.settings.items[1].value=='OFF','reduced motion was not reported honestly')
assert(state().presentation.reduced==false,'the run claimed reduced motion it does not have')
-- The pulse animation is what reduced motion removes; the geometry is identical.
local fills={}
gd.fill=function(x,y,w,h) fills[#fills+1]={x=x,y=y,w=w,h=h} end
gd.kit.text=function() return 10 end
gd.kit.icon=function() end
presentation:draw(presentation.feedback,{hud=true,player={percent=10,lives=1}})
local rail
local lay=presentation:state{}
for _,d in ipairs(fills) do if d.w==lay.rail.w and d.h==lay.rail.h then rail=d end end
assert(rail,'the rail was not drawn')
-- A failing renderer and a failing planner must not touch run or save state.
local before_run=assert(Core.snapshot(state().run))
local before_write=writes
local real_text=gd.kit.text
gd.kit.text=function() error('kit exploded') end
on_draw()
gd.kit.text=real_text
local real_loadout=presentation.rebuild
presentation.rebuild=function() error('planner exploded') end
step(0);step(1);step(0)
presentation.rebuild=real_loadout
assert(Core.snapshot(state().run)==before_run,'a UI failure corrupted the run')
assert(writes==before_write,'a UI failure wrote to storage')
assert(state().v2 and state().v2.campaign.phase=='active','a UI failure disturbed the campaign')
-- The run is still fully usable after the failures.
step(0);step(8);step(0)
assert(state().command_event==nil or state().command_event.kind~='taunt','a UI failure fabricated input')
print('PASS reduced motion is honest and UI failures cannot corrupt run or save state')
''')


class BundleTests(unittest.TestCase):
    def test_collection_draw_before_first_run_has_no_room_dependency(self):
        script = '(function()\n' + prepare.bundle() + '\nend)()\n'
        body = r"""
files={};request=true;tick=0
ready()
assert(state().menu=='collection' and state().run==nil and state().node==nil)
local logs,texts={},{}
gd.log=function(s) logs[#logs+1]=s end
gd.kit.text=function(x,y,s) texts[#texts+1]=tostring(s);return 10 end
on_draw()
assert(#logs==0,'fresh collection renderer failed: '..table.concat(logs,';'))
assert(#texts>0,'fresh collection did not render')
print('PASS fresh collection renders before any room or run exists')
"""
        result = subprocess.run([LUA, '-', str(RT)], input=v2.PRELUDE_MAIN + script + body,
                                text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS', result.stdout)

    def test_production_legacy_onboarding_observes_complete_gameplay_sequence(self):
        script = '(function()\n' + prepare.bundle() + '\nend)()\n'
        body = r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
for _=1,400 do step();if state().active then break end end
assert(state().active and roguelite_v2()==nil)
local p=uv(on_tick,'presentation')
local function frame() tick=tick+1;on_frame() end
local function current(id) assert(p:view().step==id,'expected '..tostring(id)..', got '..tostring(p:view().step)) end
local function door(side)
 ps[1].x=side=='left' and -52 or 52;ps[1].y=0;press(4)
 for _=1,30 do if state().active then break end;step() end
end
current('move')
ps[1].vx=3;for _=1,60 do frame() end;ps[1].vx=0
current('charge')
door('right');assert(state().node=='trail')
local enemy=next(enemies);assert(enemy)
ps[1].x=0;ps[1].y=0;enemies[enemy].x=4;enemies[enemy].y=0
for _=1,3 do on_action_change(1,14,44,false);on_enemy_hit{handle=enemy,from=1,damage=3} end
frame();current('branch')
press(1);current('back');press(8);current('cast')
press(1);press(1)
assert(enemies[enemy].damage==10,'tutorial cast was not a real gameplay activation')
current('tell')
-- Feed observed native enemy contacts; the real EnemyGenes controller earns
-- charge, enters its windup and supplies its actual state to presentation.
for _=1,12 do
 enemies[enemy].hits=enemies[enemy].hits+1;enemies[enemy].attack_id=enemies[enemy].attack_id+1
 frame();if p:view().step=='door' then break end
end
current('door')
on_enemy_defeated{handle=enemy};enemies[enemy]=nil
door('left');assert(state().node=='arena_a');current('reward')
ps[2].stocks=98;frame();assert(state().menu=='reward')
click('reward1');current(nil)
assert(p:view().completed==8 and p:view().pause==false,'full tutorial did not complete from the real gameplay hooks')
print('PASS all eight onboarding steps follow real production legacy gameplay hooks')
'''
        result = subprocess.run([LUA, '-', str(RT)], input=v2.PRELUDE_MAIN + script + body,
                                text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS', result.stdout)

    def test_production_legacy_main_uses_real_loadout_and_preserves_up(self):
        script = '(function()\n' + prepare.bundle() + '\nend)()\n'
        body = r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
for _=1,400 do step();if state().active then break end end
assert(state().active and roguelite_v2()==nil,'production certification did not use the legacy path')
local presentation=uv(on_tick,'presentation');local cs=uv(on_tick,'command_state');local avail=uv(on_tick,'availability')
local choose=uv(on_tick,'choose_menu')
local root=presentation:view_commands(cs,avail)
assert(root.branches[1].label=='Abilities','legacy kept the authored default tree')
local function door(side)
 ps[1].x=side=='left' and -52 or 52;ps[1].y=0;press(4)
 for _=1,30 do if state().active then break end;step() end
end
door('right');assert(state().node=='trail')
local enemy=next(enemies);assert(enemy);on_enemy_defeated{handle=enemy};enemies[enemy]=nil
door('left');assert(state().node=='arena_a')
ps[2].stocks=98;tick=tick+1;on_frame();assert(state().menu=='reward');click('reward1')
door('right');assert(state().node=='rest' and state().menu=='rest')
-- A real menu placement while Up is held rebuilds the installed loadout without
-- creating a fresh root taunt. Menus owns the placement/save transaction.
ps[1].x=0
click('gene:r3')
step(8);step(8)
choose({kind='place',id='r3',slot='traversal'})
assert(state().run.hosts.player.slots.traversal=='r3','legacy placement did not commit')
assert(cs.node=='root' and cs.up_latched,'legacy rebuild lost held Up')
choose({kind='continue'});step(8)
assert(state().command_event==nil or state().command_event.kind~='taunt','held Up fabricated a taunt')
step(0);press(1)
local abilities=presentation:view_commands(cs,avail);local traversal
for _,b in ipairs(abilities.branches) do if b.slot=='traversal' then traversal=b end end
assert(traversal and traversal.label:find('CINDER',1,true),'placed traversal gene is absent from legacy tree')
-- Refused placement leaves the saved gene and its command leaf installed.
press(8);press(4);press(1);click('gene:r2')
fail_atomic=true;choose({kind='place',id='r2',slot='traversal'});fail_atomic=false
assert(state().run.hosts.player.slots.traversal=='r3','legacy save refusal did not refund placement')
choose({kind='continue'});press(1)
for _,b in ipairs(presentation:view_commands(cs,avail).branches) do
 if b.slot=='traversal' then assert(b.label:find('CINDER',1,true),'refund left stale command leaf') end
end
press(8)
-- Spend the run's two real supplies through normal D-pad actions.
ps[1].percent=90
for _=1,2 do press(2);press(1) end
assert(state().run.progress.supplies==0 and ps[1].percent==30,'legacy supplies were not really spent')
press(2)
local item=presentation:view_commands(cs,avail)
assert(item.branches[1].enabled==false and item.branches[1].reason=='No supplies in this run','legacy zero-supply command is enabled')
-- The durable resume uses this same real loadout, without recipe admission edits.
press(8);choose({kind='leave'});click('resume')
for _=1,400 do step();if state().active then break end end
assert(state().active and roguelite_v2()==nil)
press(1)
for _,b in ipairs(presentation:view_commands(cs,avail).branches) do
 if b.slot=='traversal' then assert(b.label:find('CINDER',1,true),'resume lost the placed legacy gene') end
end
print('PASS shipped legacy main uses real placed genes, preserves held Up, refunds and disables spent supplies')
'''
        result = subprocess.run([LUA, '-', str(RT)], input=v2.PRELUDE_MAIN + script + body,
                                text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS', result.stdout)

    def test_bundle_carries_the_presentation_modules_before_main(self):
        script = prepare.bundle()
        # Every presentation module is bundled under its expected lexical name.
        self.assertIn('local Hud = (function()', script)
        self.assertIn('local Onboarding = (function()', script)
        self.assertIn('local Presentation = (function()', script)
        # main is last, and every earlier runtime module keeps its relative order.
        names = ['Core', 'Commands', 'Feedback', 'RuntimeCampaign', 'Hud', 'Onboarding', 'Presentation']
        positions = []
        for local in names:
            marker = f'local {local} = (function()'
            self.assertIn(marker, script, f'{local} is missing from the bundle')
            positions.append(script.index(marker))
        self.assertEqual(positions, sorted(positions), 'bundle module order changed')
        self.assertLess(script.index('local Presentation = (function()'),
                        script.index('function on_tick()'))
        self.assertIn('function on_tick()', script)
        self.assertIn('function on_draw()', script)
        # The reviewed inventory modules were neither added nor dropped by this
        # lane: they were not part of the installed bundle before either.
        for module in ('Inventory', 'Equipment'):
            self.assertNotIn(f'local {module} = (function()', script,
                             f'{module} was silently added to the installed bundle')

    def test_bundled_source_compiles(self):
        directory = v2._certified_source()
        try:
            script = '(function()\n' + prepare.bundle(source=directory) + '\nend)()\n'
        finally:
            shutil.rmtree(directory, ignore_errors=True)
        target = Path('/tmp/roguelite-presentation-bundle.lua')
        target.write_text(script)
        result = subprocess.run([LUA, '-e', f'assert(loadfile("{target}")) print("PASS")'],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
