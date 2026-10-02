#!/usr/bin/env python3
"""Gate 8 command/menu/HUD/onboarding behavior in the real Lua modules.

These are real-module tests: they load `commands.lua`, `hud_layout.lua`,
`feedback.lua`, `onboarding.lua` and `menus.lua` (plus Core/Progress/RouteMap
for the menu and map cases) and drive them through the Lua interpreter. Nothing
here is a Python translation of the policy.

Coverage: command hierarchy, Up mask release, root taunt, held-button debounce,
neutral/chord handling, open/close of the loadout tree; HUD layout bounds and
safe areas at 4:3/16:9 and high DPI; mouse/controller focus on the new screens;
notification lifetimes and tutorial coalescing; map spoiler boundary.
"""
from pathlib import Path
import shutil
import subprocess
import unittest
import game_source

ROOT = Path(__file__).resolve().parents[2]
RT = game_source.ROGUELITE


def _lua():
    return shutil.which('lua') or shutil.which('lua5.4') or shutil.which('luajit')


class MenuPolishTests(unittest.TestCase):
    maxDiff = None

    def run_lua(self, modules, program):
        lua = _lua()
        self.assertIsNotNone(lua, 'Lua interpreter required; do not translate the policy to Python')
        result = subprocess.run(
            [lua, '-', *[str(m) for m in modules]], input=program, text=True,
            capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    # ----- commands ---------------------------------------------------------
    def test_command_hierarchy_upmask_taunt_debounce_neutral(self):
        program = r'''
local C=assert(loadfile(arg[1]))()
local s=C.new()
local allow=function() return true end
local function press(b,fn) C.update(s,0,fn or allow);return C.update(s,b,fn or allow) end
-- Root: a fresh Up is the normal native taunt and is not masked.
C.reset(s);local e,m=press(8);assert(e.kind=='taunt' and m==7,'root taunt')
-- Hierarchy: Left/Left/Left reaches depth 2 then executes and returns to root.
e,m=press(1);assert(e.node=='magic' and m==15)
e,m=press(1);assert(e.node=='fire' and C.view(s).depth==2)
e,m=press(1);assert(e.kind=='execute' and e.family=='cinder' and e.slot=='assault' and s.node=='root' and m==7)
-- Up returns one level; the popped Up stays masked until release.
press(1);press(1);e,m=press(8);assert(e.kind=='back' and s.node=='magic' and m==15)
e,m=press(8);assert(e.kind=='back' and s.node=='root' and m==15)
e,m=C.update(s,8,allow);assert(not e and m==15,'held up at root must not taunt')
e,m=C.update(s,0,allow);assert(not e and m==7,'release clears the up mask')
e,m=press(8);assert(e.kind=='taunt' and m==7,'fresh up after release taunts')
-- Held-button debounce: a held direction never repeats its navigation.
press(1);local n=s.node
for i=1,90 do local ev=C.update(s,1,allow);assert(not ev and s.node==n,'held direction repeated') end
C.update(s,0,allow)
press(1);assert(s.node=='fire','release then press must advance again')
-- Neutral/chord: opposing diagonal performs no action and must release.
C.reset(s);press(1);assert(s.node=='magic')
e,m=press(9);assert(not e and m==15 and s.node=='magic','chord must be inert')
assert(not C.update(s,1,allow),'still-chorded press must not act')
assert(s.node=='magic')
C.update(s,0,allow);e,m=press(1);assert(e.node=='fire','neutral release restores selection')
-- Face buttons do not collide with the D-pad.
C.reset(s);e,m=press(0x301);assert(e.node=='magic' and m==15)
print('commands hierarchy/upmask/taunt/debounce/neutral ok')
'''
        self.run_lua([RT / 'commands.lua'], program)

    def test_command_loadout_tree_open_close_and_assignments(self):
        program = r'''
local C=assert(loadfile(arg[1]))()
local allow=function() return true end
local run={genes={a={kind='cinder'},b={kind='rime'},c={kind='cinder'}},
 hosts={player={slots={assault='a',guard='b'}}}}
local s=C.new()
local t=C.loadout(s,run,{capacities={items={restore=2},supplies=2}})
-- Every level forks left/right/down; abilities are two presses from root.
local v=C.view(s);assert(v.branches[1].label=='Abilities' and #v.branches==3)
C.update(s,0,allow);local e=C.update(s,1,allow)
assert(e.kind=='navigate' and s.node=='abilities','open abilities')
assert(C.view(s).depth==1)
C.update(s,0,allow);e=C.update(s,1,allow)
assert(e.kind=='execute' and e.family=='cinder' and e.slot=='assault','two-press cast')
-- Only installed loadout appears; no catalogue ids leak into the tree.
local serial={}for _,br in ipairs(C.view(s).branches)do serial[#serial+1]=br.slot or br.node end
assert(#serial==3)
assert(t.abilities.branches[2].family=='rime' and t.abilities.branches[2].slot=='guard')
-- Empty slot is honestly blocked, not silently castable.
local bare={genes={},hosts={player={slots={}}}}
local tb=C.plan(bare,{});local sb=C.new();C.install(sb,tb)
C.update(sb,0,allow);C.update(sb,1,allow);C.update(sb,0,allow)
local eb=C.update(sb,1,allow);assert(eb.kind=='blocked' and eb.action=='gene' and eb.slot=='assault',tostring(eb and eb.kind))
-- Prepared branch assignments are explicit, validated data.
local t2=C.plan(run,{assign={abilities={left='traversal',down='assault'}},capacities={items={restore=0}}})
local a=C.assignments(t2)
assert(a.abilities.left=='traversal' and a.abilities.down=='assault' and a.abilities.right=='guard')
assert(a.root.left=='abilities' and a.root.right=='items' and a.root.down=='special')
assert(t2.item.branches[1].blocked=='No supplies in this run','empty supply must be honest')
local ok,why=pcall(C.plan,run,{assign={abilities={left='nope'}}})
assert(not ok,'unknown assignment must be refused')
-- Partial assignments reconcile into a permutation: no installed slot dropped,
-- no duplicate path. Only truly invalid assignments are refused.
local tp=C.plan(run,{assign={abilities={left='guard'}}})
local ap=C.assignments(tp);local seen={}
for _,d in ipairs({'left','right','down'}) do
 assert(not seen[ap.abilities[d]],'duplicate ability path '..d);seen[ap.abilities[d]]=true
end
assert(seen.assault and seen.guard and seen.traversal,'partial ability assignment dropped a slot')
local tr=C.plan(run,{assign={root={left='special'}}})
local ar=C.assignments(tr);local rseen={}
for _,d in ipairs({'left','right','down'}) do assert(not rseen[ar.root[d]],'duplicate root path');rseen[ar.root[d]]=true end
assert(rseen.abilities and rseen.items and rseen.special,'partial root assignment dropped a node')
assert(not pcall(C.plan,run,{assign={abilities={left='guard',right='guard'}}}),'repeated assignment not refused')
assert(not pcall(C.plan,run,{assign={abilities={side='assault'}}}),'unknown direction not refused')
-- Declared zero supply is blocked, never an enabled Restore x0.
local tz=C.plan(run,{capacities={supplies=0}})
assert(tz.item.branches[1].blocked=='No supplies in this run' and tz.item.branches[1].label=='No supplies')
-- Installing nil restores the authored default tree; a rebuild mid-branch
-- returns to the valid root. The held-button edge history is preserved, so a
-- direction that was already held cannot re-fire on the swapped tree.
C.install(s,nil);assert(C.view(s).title=='COMMAND' and C.view(s).branches[1].label=='Magic')
local sm=C.new();C.install(sm,t)
C.update(sm,0,allow);C.update(sm,1,allow);assert(sm.node=='abilities')
C.install(sm,nil)
assert(sm.node=='root' and C.view(sm).title=='COMMAND','rebuild did not return to root')
assert(C.update(sm,1,allow)==nil and sm.node=='root','held direction re-fired after rebuild')
C.install(sm,t);C.update(sm,0,allow);C.update(sm,1,allow);assert(sm.node=='abilities')
C.install(sm,tp);assert(sm.node=='root','rebuild left a stale node')
-- Held Up contract: rebuilding the tree while Up is held must not fabricate a
-- taunt. The latch must survive until the button is released.
local su=C.new();C.install(su,t)
C.update(su,0,allow);C.update(su,1,allow);assert(su.node=='abilities')
C.update(su,0,allow)
local eu,mu=C.update(su,8,allow);assert(eu.kind=='back' and su.node=='root' and mu==15)
C.install(su,t)
eu,mu=C.update(su,8,allow)
assert(not eu and mu==15 and su.node=='root','held Up after rebuild emitted '..tostring(eu and eu.kind))
eu,mu=C.update(su,0,allow);assert(not eu and mu==7)
eu,mu=C.update(su,8,allow);assert(eu.kind=='taunt' and mu==7,'fresh Up after release must taunt')
-- Passing current buttons syncs exactly: held Up stays latched.
local sv=C.new();C.install(sv,t);C.update(sv,0,allow);C.update(sv,1,allow);C.update(sv,0,allow)
C.update(sv,8,allow);assert(sv.up_latched)
C.install(sv,t,8);local ev,mv=C.update(sv,8,allow);assert(not ev and mv==15,'explicit held buttons not synced')
print('commands loadout/open-close/assignments ok')
'''
        self.run_lua([RT / 'commands.lua'], program)

    # ----- HUD --------------------------------------------------------------
    def test_hud_layout_bounds_safe_areas_and_command_expansion(self):
        program = r'''
local H=assert(loadfile(arg[1]))()
local function inb(r,w,h) assert(r.x>=0 and r.y>=0 and r.x+r.w<=w+0.01 and r.y+r.h<=h+0.01,'out of bounds') end
for _,vp in ipairs({{640,480,1,'4:3'},{854,480,1,'16:9'},{640,480,1.5,'4:3'},{854,480,2,'16:9'}}) do
 local l=assert(H.layout{width=vp[1],height=vp[2],dpi=vp[3],new_hud=true,command=true})
 assert(l.aspect==vp[4],'aspect '..l.aspect)
 inb(l.safe,vp[1],vp[2]);inb(l.rail,vp[1],vp[2]);inb(l.notification,vp[1],vp[2]);inb(l.command,vp[1],vp[2])
 inb(l.fallback.lives,vp[1],vp[2]);inb(l.fallback.damage,vp[1],vp[2])
 -- Fallback life/damage stay readable and never overlap.
 assert(l.fallback.lives.w>=40 and l.fallback.lives.h>=14)
 assert(l.fallback.damage.x>=l.fallback.lives.x+l.fallback.lives.w)
 assert(H.avoids_center(l,l.command),'command panel entered center band')
 local g=H.command_expanded(l,4);inb(g,vp[1],vp[2]);assert(H.avoids_center(l,g))
end
-- Vanilla cluster is only replaced when the new HUD is actually available.
assert(H.layout{width=640,height=480}.replace_vanilla==false)
assert(H.layout{width=640,height=480,new_hud=true}.replace_vanilla==true)
-- Unknown/malformed viewports refuse instead of guessing.
assert(not H.layout{width=0,height=480})
assert(not H.layout{width='x',height=480})
assert(H.aspect(640,480)=='4:3' and H.aspect(854,480)=='16:9' and H.aspect(1000,480)=='other')
print('hud layout bounds/safe areas/command expansion ok')
'''
        self.run_lua([RT / 'hud_layout.lua'], program)

    # ----- menus + map ------------------------------------------------------
    def test_menu_focus_mouse_new_screens_and_map_spoilers(self):
        program = r'''
Core=assert(loadfile(arg[1]))()
local M=assert(loadfile(arg[2]))()
local RouteMap=assert(loadfile(arg[3]))()
local Progress=assert(loadfile(arg[4]))()
local C=Core
local p=C.new_profile(77);local r=C.new_run(p)
-- Controller focus moves between controls and confirms the same action.
local s=M.new();local ctx={menu='rest',run=r,profile=p,starter='g1'}
local v=M.view(s,ctx);assert(#v.controls>0)
s.focus='continue';local moved=M.update(s,ctx,{up=true});assert(moved==nil)
assert(s.focus and s.focus~='continue','up did not move focus')
local a=M.update(s,ctx,{confirm=true});assert(a and a.kind,'controller confirm produced no action')
-- Mouse click focuses and activates a control in one event.
s=M.new();v=M.view(s,ctx);local target=M.view(s,ctx).controls[1]
local clicked=M.update(s,ctx,{mx=target.x+4,my=target.y+4,click=true})
assert(clicked==nil or type(clicked)=='table')
assert(s.focus==target.id,'mouse did not focus the clicked control')
-- Declared full capacity offers discard, and discard needs a second press.
local cap_ctx={menu='collection',profile=p,run=r,starter='g1',capacity={count=128,max=128,full=true}}
local sc=M.new();local vc=M.view(sc,cap_ctx);assert(vc.capacity_note and vc.capacity_note:find('/'))
local disc;for _,b in ipairs(vc.controls) do if b.id=='discard' then disc=b end end
assert(disc and disc.action.destructive,'full capacity gave no destructive discard')
local first=M.update(sc,cap_ctx,{mx=disc.x+3,my=disc.y+3,click=true})
assert(first and first.kind=='blocked' and first.confirm_pending=='discard','no confirm prompt')
-- Changing the selected identity after a prompt must invalidate it: the same
-- click can never confirm a discard for a different gene.
local function button2(view,id) for _,b in ipairs(view.controls) do if b.id==id then return b end end end
local g1=button2(M.view(sc,cap_ctx),'gene:g1');assert(g1)
M.update(sc,cap_ctx,{mx=g1.x+3,my=g1.y+3,click=true});assert(sc.selected=='g1')
local d1=button2(M.view(sc,cap_ctx),'discard')
assert(M.update(sc,cap_ctx,{mx=d1.x+3,my=d1.y+3,click=true}).kind=='blocked')
local g2=button2(M.view(sc,cap_ctx),'gene:g2');assert(g2)
M.update(sc,cap_ctx,{mx=g2.x+3,my=g2.y+3,click=true});assert(sc.selected=='g2')
local d2=button2(M.view(sc,cap_ctx),'discard')
local stale=M.update(sc,cap_ctx,{mx=d2.x+3,my=d2.y+3,click=true})
assert(stale.kind=='blocked','selection change did not invalidate the pending discard')
local confirmed=M.update(sc,cap_ctx,{mx=d2.x+3,my=d2.y+3,click=true})
assert(confirmed.kind=='discard' and confirmed.id=='g2','fresh two-press confirm failed')
-- Reset invalidates the pending prompt as well.
local d3=button2(M.view(sc,cap_ctx),'discard')
assert(M.update(sc,cap_ctx,{mx=d3.x+3,my=d3.y+3,click=true}).kind=='blocked')
M.reset(sc,'collection')
local d4=button2(M.view(sc,cap_ctx),'discard');assert(d4)
assert(M.update(sc,cap_ctx,{mx=d4.x+3,my=d4.y+3,click=true}).kind=='blocked','reset did not invalidate pending')
assert(M.update(sc,cap_ctx,{mx=d4.x+3,my=d4.y+3,click=true}).kind=='discard')
-- Onboarding view exposes no forced pause and routes through the same focus path.
local O=assert(loadfile(arg[5]))()
local ob=O.new()
local so=M.new();local vo=M.view(so,{menu='onboarding',onboarding=O.view(ob)})
assert(vo.no_pause==true and vo.onboarding.step=='move')
local ko;for _,b in ipairs(vo.controls) do if b.id=='onboarding_skip' then ko=b end end
local oa=M.update(so,{menu='onboarding',onboarding=O.view(ob)},{mx=ko.x+2,my=ko.y+2,click=true})
assert(oa and oa.kind=='onboarding_skip')
-- Settings only expose declared data; nothing is invented.
local ss=M.new();local vs=M.view(ss,{menu='settings',settings={items={{id='fx',label='FX LEVEL',value='MEDIUM'}}}})
assert(vs.settings and #vs.settings==1)
local vs2=M.view(M.new(),{menu='settings'})
assert(vs2.error,'absent settings declaration must not fabricate options')
-- Ending screen shows the declared outcome and lines only.
local se=M.new();local ve=M.view(se,{menu='ending',ending={outcome='success',lines={'Exported r1'},next='COLLECTION'}})
assert(ve.title=='RUN COMPLETE' and ve.lines[1]=='Exported r1')
-- Map spoiler boundary: build a real map with undiscovered rooms and make sure
-- no tests are running against a map that leaked them.
local function clone(t) if type(t)~='table' then return t end local o={} for k,x in pairs(t) do o[k]=clone(x) end return o end
local function ser(t) local ty=type(t) if ty=='string' then return string.format('%q',t) end if ty~='table' then return tostring(t) end local ps={} for k,x in pairs(t) do ps[#ps+1]=ser(k)..'='..ser(x) end table.sort(ps) return '{'..table.concat(ps,',')..'}' end
local manifest={schema_version=2,world_seed=1,generation_report={topology_signature='x'},
 rooms_by_id={r001={id='r001',title='Threshold',role='entry',theme='c',depth=0,mandatory=true,sockets_by_id={out={id='out',side='right',edge='e1'}}},
  r002={id='r002',title='Court',role='combat',theme='f',depth=1,mandatory=true,reward='reward_secret',sockets_by_id={enter={id='enter',side='left',edge='e1'},out={id='out',side='right',edge='e2'}}},
  r004={id='r004',title='Deep Vault',role='reward',theme='i',depth=2,reward='reward_hidden',sockets_by_id={enter={id='enter',side='left',edge='e2'}}}},
 edges_by_id={e1={id='e1',from_room='r001',from_socket='out',to_room='r002',to_socket='enter',direction='both',kind='main'},
  e2={id='e2',from_room='r002',from_socket='out',to_room='r004',to_socket='enter',direction='both',kind='branch'}}}
local pr=Progress.new('run1','r001');pr.current_room='r002';pr.visited.r002=true;pr.discovered.r002=true;pr.revealed.e1=true
local map=assert(RouteMap.build(manifest,pr))
assert(map.rooms.r004==nil,'fixture leaked an undiscovered room')
local sm=M.new();local vm=M.view(sm,{menu='map',map=map})
local text=ser(vm)
for _,needle in ipairs({'r004','Deep Vault','reward_secret','reward_hidden'}) do
 assert(not text:find(needle,1,true),'map screen leaked spoiler '..needle)
end
assert(vm.map_current=='r002')
-- New screens render through the same bounds-checking engine stub.
local draws=0
local function bounds(x,y,w,h) assert(x>=0 and y>=0 and x+w<=640.01 and y+h<=480.01,'draw oob');draws=draws+1 end
local function kittext(x,y,txt,role,color,align,opts) assert(type(txt)=='string' and opts and opts.max_w and x+opts.max_w<=640);draws=draws+1 end
gd={fill=bounds,kit={panel=function(x,y,w,h) bounds(x,y,w,h) end,button=function(x,y,w,txt,sel,opts) bounds(x,y,w,opts.h) end,text=kittext,icon=function(n,x,y,s) assert(n:match('^rogue_'));bounds(x,y,16*s,16*s) end}}
M.draw(sm,{menu='map',map=map})
-- A real-sized run paginates instead of drawing past the safe area.
local manifest2={schema_version=2,world_seed=2,generation_report={},rooms_by_id={},edges_by_id={}}
for i=1,20 do local id=string.format('r%03d',i)
 manifest2.rooms_by_id[id]={id=id,title='Room '..i,role='combat',theme='c',depth=i-1,sockets_by_id={}} end
local pr2=Progress.new('run2','r001');pr2.current_room='r001'
for i=1,20 do local id=string.format('r%03d',i);pr2.visited[id]=true;pr2.discovered[id]=true end
local map2=assert(RouteMap.build(manifest2,pr2));assert(map2.counts.discovered_rooms==20)
local sm2=M.new();local vm2=M.view(sm2,{menu='map',map=map2})
assert(vm2.map_pages==3,'expected 3 pages, got '..tostring(vm2.map_pages))
local nx;for _,b in ipairs(vm2.controls) do if b.id=='next' then nx=b end end
assert(nx,'no page control for a 20-room map')
M.draw(sm2,{menu='map',map=map2})
M.update(sm2,{menu='map',map=map2},{mx=nx.x+2,my=nx.y+2,click=true})
assert(sm2.page==2)
assert(M.view(sm2,{menu='map',map=map2}).page==2,'map page reset on view')
M.draw(sm2,{menu='map',map=map2})
M.draw(M.new(),{menu='onboarding',onboarding=O.view(O.new())})
M.draw(M.new(),{menu='settings',settings={items={{id='fx',label='FX LEVEL',value='MEDIUM'}}}})
M.draw(M.new(),{menu='ending',ending={outcome='failure',lines={'Run upgrades lost'}}})
assert(draws>20)
print('menu focus/mouse/new screens/map spoilers ok')
'''
        self.run_lua([RT / 'core.lua', RT / 'menus.lua', RT / 'route_map.lua',
                      RT / 'progress.lua', RT / 'onboarding.lua'], program)

    # ----- notifications ----------------------------------------------------
    def test_notification_lifetimes_and_tutorial_coalescing(self):
        program = r'''
local F=assert(loadfile(arg[1]))()
local O=assert(loadfile(arg[2]))()
-- The cast tutorial must describe the real control: command leaves auto-execute
-- on the D-pad, so it must not tell the player to press A.
local cast
for _,st in ipairs(O.core()) do if st.id=='cast' then cast=st end end
assert(cast,'no cast tutorial step')
assert(not cast.hint:lower():find('press a',1,true),'cast hint still says press A')
assert(cast.hint:find('Left / Right / Down',1,true),'cast hint not aligned to the D-pad')
assert(cast.hint:find('final branch',1,true))
local s=F.new()
-- Tutorial notices coalesce by step key and cannot turn into spam.
local step=O.toast(O.new())
assert(step and step.key=='tutorial:move')
assert(F.tutorial(s,step))
for i=1,200 do F.tutorial(s,step) end
local v=F.view(s)
assert(v.queued==1 and v.notification.count==99,'tutorial spam was not coalesced')
-- Lifetime is honoured and frozen while paused.
F.update(s,{},0,false,nil)
for i=1,30 do F.update(s,{},1,false,nil) end
assert(F.view(s).queued==1)
F.reset(s);assert(F.tutorial(s,{title='Move and attack',key='tutorial:move',ttl=20}))
for i=1,20 do F.update(s,{},1,false,nil) end
assert(F.view(s).queued==0,'tutorial lifetime not honoured')
-- A warning preempts a tutorial and the tutorial never preempts a warning.
F.reset(s);assert(F.tutorial(s,{title='Move',key='tutorial:move',ttl=600}))
assert(F.notify(s,{kind='blocked',key='door',title='Locked',ttl=600}))
assert(F.view(s).notification.kind=='blocked')
-- Enemy tell uses the clear channel with warning semantics, not celebration.
F.reset(s);assert(F.tell(s,{key='tell:r1',title='INCOMING'}))
assert(F.view(s).notification.kind=='tell' and not F.view(s).notification.celebrate)
print('notification lifetimes/tutorial coalescing ok')
'''
        self.run_lua([RT / 'feedback.lua', RT / 'onboarding.lua'], program)


    def test_hud_feedback_fallback_and_replace_gate(self):
        program = r'''
local F=assert(loadfile(arg[1]))()
local H=assert(loadfile(arg[2]))()
local fills,texts,tpos={},{},{}
local vp_w,vp_h=640,480
gd={fill=function(x,y,w,h,c) assert(x>=0 and y>=0 and x+w<=vp_w+0.01 and y+h<=vp_h+0.01,'fill oob');fills[#fills+1]={x=x,y=y,w=w,h=h} end,
 kit={text=function(x,y,t,role,color,align,o) assert(o and o.max_w,'no max_w');texts[#texts+1]=t;tpos[#tpos+1]={x=x,y=y,w=o.max_w,t=t} end,
 icon=function(n) assert(n:match('^rogue_')) end}}
local function has(f,x,y,w,h) for _,r in ipairs(f) do if r.x==x and r.y==y and r.w==w and r.h==h then return true end end return false end
local function inside(r,x,y,w,h) return x>=r.x-.01 and y>=r.y-.01 and x+w<=r.x+r.w+.01 and y+h<=r.y+r.h+.01 end
local function ov(a,b) return a.x<b.x+b.w and b.x<a.x+a.w and a.y<b.y+b.h and b.y<a.y+a.h end
local function owned(rects,f) for _,r in ipairs(rects) do if inside(r,f.x,f.y,f.w,f.h) then return true end end return false end
-- New HUD unavailable: only fallback anchors draw; life/damage readable; no box.
local fb=assert(H.layout{width=640,height=480});assert(fb.replace_vanilla==false)
fills={};tpos={};local s=F.new()
F.draw(s,{layout=fb,player={percent=42,lives=2,supplies=1}})
local shown=table.concat(texts,'|')
assert(shown:find('LIVES 2',1,true) and shown:find('42%',1,true),'fallback lost life/damage')
assert(not has(fills,fb.rail.x,fb.rail.y,fb.rail.w,fb.rail.h),'fallback drew the compact rail')
assert(has(fills,fb.fallback.lives.x,fb.fallback.lives.y,fb.fallback.lives.w,fb.fallback.lives.h),'fallback anchor missing')
-- A missing opponent label must not crash; the safe default is used.
assert(F.notify(s,{kind='info',key='k',title='Ready',detail='ok'}))
F.draw(s,{layout=fb,player={percent=42,lives=2},opponent={percent=5,lives=1}})
-- Actual drawn boxes at small/dpi2 and normal windows must lie inside their
-- owned layout rects, the rail and opponent must not intersect, and the third
-- charge bar must remain inside the rail (the dpi2 cap bug).
for _,cfg in ipairs({{640,480,1},{640,480,2},{854,480,1},{854,480,2}}) do
 vp_w,vp_h=cfg[1],cfg[2]
 local lay=assert(H.layout{width=vp_w,height=vp_h,dpi=cfg[3],new_hud=true})
 fills={};texts={};tpos={}
 local st=F.new();assert(F.notify(st,{kind='info',key='k',title='Ready',detail='ok'}))
 F.draw(st,{layout=lay,player={percent=42,lives=2,supplies=1},opponent={label='CHAMPION',percent=87,lives=2}})
 local r,o,n=lay.rail,lay.opponent,lay.notification
 assert(has(fills,r.x,r.y,r.w,r.h),'rail not drawn from layout')
 assert(has(fills,n.x,n.y,n.w,n.h),'notification not drawn from layout')
 assert(not ov(r,o),'rail/opponent overlap at '..vp_w..' dpi'..cfg[3])
 for _,f in ipairs(fills) do
  assert(owned({r,o,n},f),string.format('fill not in an owned rect %.0f,%.0f %.0fx%.0f at %d dpi%d',f.x,f.y,f.w,f.h,vp_w,cfg[3]))
 end
 for _,t in ipairs(tpos) do
  assert(owned({r,o,n},{x=t.x,y=t.y,w=t.w,h=0}),string.format('text "%s" outside owned rect at %d dpi%d',t.t,vp_w,cfg[3]))
 end
 local bar_x=r.x+math.floor(9*lay.content_scale+0.5)+2*math.floor(81*lay.content_scale+0.5)
 local bar_w=math.floor(73*lay.content_scale+0.5)
 assert(inside(r,bar_x,r.y+math.floor(53*lay.content_scale+0.5),bar_w,1),'third charge bar outside rail')
 assert(lay.rail.h==(cfg[3]==2 and 122 or 61),'rail height not scaled: '..lay.rail.h)
 local safe=lay.safe
 assert(n.x>=safe.x and n.y>=safe.y and n.x+n.w<=safe.x+safe.w and n.y+n.h<=safe.y+safe.h,'notification outside safe')
 assert(table.concat(texts,'|'):find('CHAMPION',1,true))
end
-- Compact workbench strip: one line that fits the strip at dpi 1 and dpi 2.
for _,cfg in ipairs({{640,480,1},{640,480,2}}) do
 vp_w,vp_h=cfg[1],cfg[2]
 local lay=assert(H.layout{width=vp_w,height=vp_h,dpi=cfg[3],new_hud=true})
 fills={};texts={};tpos={}
 local st=F.new();assert(F.notify(st,{kind='info',key='k',title='Ready',detail='ok'}))
 F.draw(st,{hud=false,compact_menu=true,layout=lay})
 local c=lay.compact_notification
 for _,f in ipairs(fills) do assert(inside(c,f.x,f.y,f.w,f.h),'compact fill outside strip') end
 local sc=math.max(1,math.floor(lay.compact_scale+0.5))
 for _,t in ipairs(tpos) do
  assert(t.x>=c.x and t.x+t.w<=c.x+c.w+.01,'compact text width spill')
  assert(t.y+sc*14<=c.y+c.h+.01,'compact text baseline '..t.y..' spills strip bottom '..(c.y+c.h))
 end
end
print('hud feedback fallback/replace layout coords ok')
'''
        self.run_lua([RT / 'feedback.lua', RT / 'hud_layout.lua'], program)


if __name__ == '__main__':
    unittest.main()
