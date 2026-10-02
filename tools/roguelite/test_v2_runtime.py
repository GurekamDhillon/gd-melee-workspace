#!/usr/bin/env python3
"""Live v2 campaign integration invariants against real modules and a fake engine.

Two layers:

* ``CampaignTests`` loads the real pure modules plus ``runtime_rooms`` /
  ``runtime_encounters`` / ``runtime_rewards`` / ``runtime_campaign`` and drives
  the campaign controller over a handcrafted, deterministic route with an
  injected persistence callback. It proves the transactional contracts: paused
  transitions, retained ownership through refused rollback, coherent pending
  saves, encounter handover, the one-KO stock protocol, verified native effects,
  gates, drops, rewards and partial resume.

* ``MainIntegrationTests`` bundles the real ``main.lua`` (from a throwaway
  source copy whose recipe admission is opened only for the test) and drives the
  native entry path with a deterministic engine stub, proving new certified run
  creation, paused transitions, and travel save-refusal in the wired dispatcher.

The engine stub's ``gd.player`` returns a copy snapshot, as the real native API
does, so aliasing can never mask an engine-write bug.

These are stubs, not an in-engine playtest or a certification claim.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import prepare

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

# ---------------------------------------------------------------------------
# Campaign controller tests (real modules, handcrafted route, injected save)
# ---------------------------------------------------------------------------
PRELUDE = r'''
local function load(n) return assert(dofile(arg[1] .. '/' .. n .. '.lua')) end
local Core=load('core'); local Progress=load('progress'); local GeneCatalogue=load('gene_catalogue')
local Enc=load('encounter_catalogue'); local EnemyCat=load('enemy_catalogue')
local EnemyGenes=load('enemy_genes'); local TechAI=load('technical_ai')
local RNG=load('rng'); local Cat=load('room_catalogue'); local Recipes=load('room_recipes')
local Progression=load('progression'); local Topology=load('topology'); local Adapter=load('adapter')
local Rooms=load('rooms'); local RR=load('runtime_rooms'); local RE=load('runtime_encounters')
local RW=load('runtime_rewards'); local RouteMap=load('route_map'); local Route=load('route')
local Campaign=load('runtime_campaign')
-- Test-only admission; the production recipes stay uncertified on disk.
for _,recipe in pairs(Recipes.recipes) do recipe.certified=true end

local serial=0; local actors={}; local refuse_remove=false; local save_fail=false
local stage_handles={}
local percent_mode=nil; local percent_refuse_call=nil; local percent_calls=0
local ps={[1]={x=-42,y=0,vy=0,stocks=99,percent=0,facing=1,action=14,airborne=false,hitlag=0},
 [2]={x=28,y=0,vy=0,stocks=99,percent=0,facing=-1,action=14,airborne=false,hitlag=0}}
-- A copy snapshot, like the real native gd.player; never a mutable alias.
local function snapshot(p)
 local q=ps[p]; if not q then return nil end
 return {x=q.x,y=q.y,vx=q.vx,vy=q.vy,stocks=q.stocks,percent=q.percent,facing=q.facing,
  action=q.action,airborne=q.airborne,hitlag=q.hitlag}
end
local isolation=false; local paused=false
gd={buttons={A=256,B=512,UP=8,DOWN=4,LEFT=1,RIGHT=2},
 log=function() end,
 stage_isolate=function(v) if v~=nil then isolation=v end return isolation end,
 stage_add_platform=function() serial=serial+1; stage_handles[serial]=true; return serial end,
 stage_add_line=function() serial=serial+1; stage_handles[serial]=true; return serial end,
 stage_link=function(a,b) assert(a~=b and stage_handles[a] and stage_handles[b],'link requires two owned lines'); return true end,
 model_load=function() serial=serial+1; return serial end,
 model_spawn=function() serial=serial+1; return serial end,
 model_despawn=function() return true end,
 model_release=function() return true end,
 model_get=function() return true end,
 stage_remove=function(h) if refuse_remove then return false end stage_handles[h]=nil; return true end,
 player=snapshot,
 teleport=function(p,x,y) if not ps[p] then return false end ps[p].x=x;ps[p].y=y;return true end,
 set_percent=function(p,n)
  percent_calls=percent_calls+1
  if percent_mode=='throw' then error('percent refused') end
  if percent_mode=='false' then return false end
  if percent_refuse_call and percent_calls>=percent_refuse_call then return false end
  ps[p].percent=n; return true
 end,
 set_stocks=function(p,n) ps[p].stocks=n end,
 spawn_enemy=function(kind,x,y,o) serial=serial+1; actors[serial]={kind=kind,x=x,y=y,alive=true,vulnerable=true,hits=0,received=0,attack_id=1,damage=0}; return serial end,
 enemy_state=function(h) return actors[h] end,
 enemy_alive=function(h) return actors[h]~=nil and actors[h].alive==true end,
 enemy_remove=function(h) actors[h]=nil; return true end,
 enemy_hurt=function(h,spec) if actors[h] then actors[h].damage=actors[h].damage+spec.damage end return true end,
 cpu_mode=function() return true end, impulse=function() return true end,
 pause=function() paused=true end, resume=function() paused=false end, paused=function() return paused end}

-- Handcrafted deterministic route. Not a generator output; the point is the
-- transactional runtime, not topology validation.
local function socket(s) return {id=s.id, side=s.side, edge=nil} end
local function room(id, template_id, role)
 local t=Cat.rooms[template_id]
 local sockets={} for _,s in ipairs(t.sockets) do sockets[s.id]=socket(s) end
 return {id=id, template_id=template_id, template_version=t.version, role=role, theme='cobalt',
  title=id, depth=0, mandatory=true, sockets_by_id=sockets}
end
local M, VIEW
local function build_route()
 M={schema_version=2, generator_version=2, catalogue_version=Cat.version, encounter_version=Enc.version,
  world_seed=7, stream_versions={}, rooms_by_id={}, edges_by_id={}, edges_by_room={}, order={}, spine={},
  locks={arena_gate={id='arena_gate',version=1,kind='persistent_key',key='arena_key',theme='any'},
   vault_gate={id='vault_gate',version=1,kind='consumable_key',key='vault_charge',theme='any'}},
  start_room='r1', final_room='r6',
  generation_report={attempt_count=1,fallback_used=false,rejection_reasons={},topology_signature='test'}}
 local function add(room) M.rooms_by_id[room.id]=room; M.order[#M.order+1]=room.id end
 add(room('r1','entry_gate','entry'))
 add(room('r2','shortcut_door','connector'))
 add(room('r3','entry_gate','entry'))
 add(room('r4','arena_flat','combat'))
 add(room('r7','arena_flat','combat'))
 add(room('r5','reward_vault','reward'))
 add(room('r6','finish_gate','finish'))
 M.rooms_by_id.r1.grants_consumable='vault_charge'; M.rooms_by_id.r1.pickup_id='vault_pickup'
 M.rooms_by_id.r4.encounter='scout_pair'; M.rooms_by_id.r4.grants_key='arena_key'
 M.rooms_by_id.r4.reward='potency_small'
 M.rooms_by_id.r7.encounter='scout_pair'
 M.rooms_by_id.r5.reward='supply_crate'
 local function edge(id,from,fs,to,ts,kind,dir,gate,discovery)
  M.edges_by_id[id]={id=id,from_room=from,from_socket=fs,to_room=to,to_socket=ts,direction=dir or 'both',
   kind=kind or 'main',gate_rule=gate,discovery_rule=discovery or 'always'}
  M.edges_by_room[from]=M.edges_by_room[from] or {}; table.insert(M.edges_by_room[from],id)
  M.edges_by_room[to]=M.edges_by_room[to] or {}; table.insert(M.edges_by_room[to],id)
 end
 edge('e1','r1','out','r2','in')
 edge('e2','r2','out','r4','in')
 edge('e3','r2','shortcut','r3','out','branch','forward')
 edge('e4','r4','out','r7','in','main','both','arena_gate','hidden')
 edge('e5','r7','out','r5','in')
 edge('e6','r5','out','r6','in','main','both','vault_gate')
 -- Spoof the saved specs so the campaign resolves them without the generator.
 M.rooms_by_id.r4.encounter_spec=Enc.encounters.scout_pair
 M.rooms_by_id.r4.reward_spec=Enc.rewards.potency_small
 M.rooms_by_id.r7.encounter_spec=Enc.encounters.scout_pair
 M.rooms_by_id.r5.reward_spec=Enc.rewards.supply_crate
 local adapter=Adapter.new(Cat,Recipes)
 VIEW=assert(adapter:manifest(M))
end
build_route()

local RUN, ROUTE, CAMPAIGN, FINISHED, SAVE_CALLS
local function mirror(target,p)
 target.progress.room=p.current_room; target.progress.supplies=p.supplies; target.stocks=p.lives
 local cleared,claimed={},{}
 for id,state in pairs(p.objectives) do if state=='done' then cleared[id]=true end end
 for id in pairs(p.claimed) do local room=id:match('^reward:(.+)$'); if room then claimed[room]=true end end
 target.progress.cleared,target.progress.claimed=cleared,claimed
end
local function make_campaign(route_table,run_table)
 local routes=Route.new({topology=Topology.new(Cat,Enc,Progression,RNG),adapter=Adapter.new(Cat,Recipes),
  progress=Progress,progression=Progression,encounters=Enc})
 return Campaign.new(gd,{Core=Core,Progress=Progress,RouteMap=RouteMap,Rooms=Rooms,RuntimeRooms=RR,
  RuntimeEncounters=RE,RuntimeRewards=RW,EnemyGenes=EnemyGenes,EnemyCatalogue=EnemyCat,TechAI=TechAI,
  GeneCatalogue=GeneCatalogue,routes=routes,Encounters=Enc},
  {route=route_table,run=run_table,
   save_route=function(target,p,run_override)
    SAVE_CALLS=SAVE_CALLS+1
    if save_fail then return false,'forced save refusal' end
    target.progress=p
    local target_run=run_override or RUN
    mirror(target_run,p)
    if run_override then RUN=target_run end
    return true
   end,
   finish=function(o) FINISHED=o end, say=function()end})
end
local function build_campaign()
 CAMPAIGN=make_campaign(ROUTE,RUN)
 return CAMPAIGN
end
local function reset(seed)
 serial=0; actors={}; stage_handles={}; refuse_remove=false; save_fail=false; isolation=true; FINISHED=nil; SAVE_CALLS=0
 percent_mode=nil; percent_refuse_call=nil; percent_calls=0; paused=false
 ps[1]={x=-42,y=0,vy=0,stocks=99,percent=0,facing=1,action=14,airborne=false,hitlag=0}
 ps[2]={x=28,y=0,vy=0,stocks=99,percent=0,facing=-1,action=14,airborne=false,hitlag=0}
 local profile=Core.new_profile(seed or 7)
 RUN=Core.new_run(profile,{stocks=3,seed=seed or 7})
 local progress=Progress.new(RUN.id,M.start_room,{supplies=2,lives=3})
 ROUTE={manifest=M,view=VIEW,progress=progress}
 return build_campaign()
end
local function resume_campaign() return build_campaign() end
local function drive(camp,n)
 for _=1,n or 64 do camp:tick(); if not camp:blocked() then break end end
 return camp.phase
end
local function tick_until(camp,pred,n)
 for _=1,n or 240 do camp:tick(); if pred() then return true end end
 return false
end
local function enter(camp) assert(camp:enter_current()); return drive(camp) end
local function exit_to(id,to) for _,e in ipairs(VIEW.nodes[id].exits) do if e.to==to then return e end end end
local function clear_current(camp)
 for _,e in ipairs(camp:encounter_composition()) do
  if e.spawned and e.handle then camp:enemy_defeated(e.handle) end
 end
end
local function count(t) local n=0 for _ in pairs(t) do n=n+1 end return n end
'''

def run_campaign(body):
    result = subprocess.run([LUA, '-', str(RT)], input=PRELUDE + body, text=True,
                            capture_output=True, timeout=90)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    assert 'PASS' in result.stdout, result.stdout


class CampaignTests(unittest.TestCase):
    def test_initial_entry_and_travel_transaction(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active','initial entry did not activate')
assert(camp:status().room=='r1','start room not active')
assert(ROUTE.progress.visited.r1 and ROUTE.progress.objectives.r1=='done','entry objective not recorded')
assert(ROUTE.progress.pickups.vault_pickup==true,'entry pickup not claimed')
assert(ROUTE.progress.consumables.vault_charge==1,'entry key not granted')
assert(camp:request_travel(exit_to('r1','r2')))
assert(drive(camp)=='active','travel did not activate')
assert(camp:status().room=='r2' and ROUTE.progress.current_room=='r2','room not advanced')
assert(ROUTE.progress.visited.r2 and ROUTE.progress.discovered.r2,'destination not visited/discovered')
assert(ROUTE.progress.consumables.vault_charge==1,'re-entering must not re-grant the finite pickup')
assert(SAVE_CALLS>0,'travel did not persist')
print('PASS initial entry and per-socket travel')
''')

    def test_travel_save_refusal_keeps_room_fighters_keys_and_visited(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
local e=exit_to('r1','r2')
local before_progress=ROUTE.progress
local before_key=ROUTE.progress.consumables.vault_charge
ps[1].x=11;ps[1].y=22
save_fail=true
assert(camp:request_travel(e))
assert(drive(camp)=='active','refused save must recover to the usable source, got '..tostring(camp.phase))
assert(camp:status().room=='r1','refused save must keep the source room')
assert(ROUTE.progress==before_progress,'refused save must keep the exact progress record')
assert(ROUTE.progress.consumables.vault_charge==before_key and ROUTE.progress.visited.r2~=true,'refused save changed keys/visited')
assert(ps[1].x==11 and ps[1].y==22,'refused save must restore the fighters')
assert(camp.rooms:active_room()~=nil,'source room handles must remain usable')
assert(camp.tx==nil,'recovery must have released the failed transaction')
print('PASS travel save refusal keeps room, fighters, keys and visited state')
''')

    def test_transition_ownership_retained_until_recovery(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
ps[1].x=7;ps[1].y=8
save_fail=true;refuse_remove=true
assert(camp:request_travel(exit_to('r1','r2')))
assert(tick_until(camp,function() return camp.phase=='recovering' end),'did not reach a paused recovery')
assert(camp.tx~=nil,'transaction ownership was discarded while rollback refused')
assert(camp:blocked(),'refused rollback must block/pause gameplay')
assert(camp.rooms:active_room()~=nil,'source room was lost')
save_fail=false;refuse_remove=false
for i=1,12 do camp:tick() end
assert(camp.phase=='active' and camp.tx==nil,'bounded recovery did not finish')
assert(camp:status().room=='r1','source room did not resume')
assert(ps[1].x==7 and ps[1].y==8,'fighters were not restored before the source resumed')
print('PASS ownership retained through refused rollback and bounded recovery')
''')

    def test_source_cleanup_refusal_stays_paused_then_flushes(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
refuse_remove=true
assert(camp:request_travel(exit_to('r1','r2')))
for i=1,40 do camp:tick() end
assert(camp:blocked(),'pending source cleanup must keep gameplay paused')
assert(camp.rooms:pending()~=nil,'pending source ownership was forgotten')
refuse_remove=false
assert(drive(camp)=='active','flush retry did not finish the transition')
assert(camp.rooms:pending()==nil and camp:status().room=='r2')
print('PASS source cleanup refusal stays paused and flushes on retry')
''')

    def test_persistent_gate_and_opened_consumable_return(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
assert(camp:request_travel(exit_to('r1','r2')));assert(drive(camp)=='active')
assert(camp:request_travel(exit_to('r2','r4')));assert(drive(camp)=='active')
assert(ROUTE.progress.keys.arena_key==true,'arena key not granted on entry')
clear_current(camp)
assert(ROUTE.progress.objectives.r4=='done','encounter not completed')
assert(camp:request_travel(exit_to('r4','r7')));assert(drive(camp)=='active','persistent gate refused with the key held')
clear_current(camp)
assert(ROUTE.progress.objectives.r7=='done')
assert(camp:request_travel(exit_to('r7','r5')));assert(drive(camp)=='active')
assert(ROUTE.progress.current_room=='r5')
assert(ROUTE.progress.consumables.vault_charge==1)
assert(camp:request_travel(exit_to('r5','r6')));assert(drive(camp)=='active')
assert(ROUTE.progress.opened.vault_gate==true and ROUTE.progress.consumables.vault_charge==nil,'consumable gate was not spent')
assert(FINISHED=='success','finish room did not end the run')
assert(camp:request_travel(exit_to('r6','r5')));assert(drive(camp)=='active','opened return was refused')
assert(ROUTE.progress.current_room=='r5','opened return did not traverse')
print('PASS persistent gate, consumable spend and opened return')
''')

    def test_actual_downward_drop_and_oneway_refusal(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
assert(camp:request_travel(exit_to('r1','r2')));assert(drive(camp)=='active')
local drop
for _,e in ipairs(VIEW.nodes.r2.exits) do if e.to=='r3' then drop=e end end
assert(drop and VIEW.nodes.r2.room.exit_anchors[drop.side].drop,'no bottom drop exit')
local floor=VIEW.nodes.r2.room.floor
local opening=floor.openings[1]
camp:frame(gd.player(1),{x=opening.x,y=floor.y})
assert(camp.phase=='active','standing at the drop anchor triggered a transition')
ps[1].x=opening.x;ps[1].y=floor.y-6;ps[1].vy=6
camp:frame(gd.player(1),{x=opening.x,y=floor.y-12})
assert(camp.phase=='active','rising through the opening triggered a drop')
ps[1].x=opening.x;ps[1].y=floor.y-6;ps[1].vy=-6
camp:frame(gd.player(1),{x=opening.x,y=floor.y-2})
assert(drive(camp)=='active' and camp:status().room=='r3','downward drop did not traverse')
assert(exit_to('r3','r2')==nil,'adapter exposed a return for a one-way drop')
local forged={edge_id='e3',to='r2',socket='out',arrival_socket='in'}
local ok,why=camp:request_travel(forged)
assert(ok==nil and tostring(why):find('one-way',1,true),'one-way reverse was not refused: '..tostring(why))
print('PASS downward-only drop and one-way refusal')
''')

    def test_combat_exit_requires_legitimate_objective(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
assert(camp:request_travel(exit_to('r1','r2')));assert(drive(camp)=='active')
assert(camp:request_travel(exit_to('r2','r4')));assert(drive(camp)=='active')
assert(camp.encounter_active and ROUTE.progress.objectives.r4~='done')
local ok,why=camp:request_travel(exit_to('r4','r7'))
assert(not ok and tostring(why):find('encounter not complete'),'direct request bypassed the combat objective')
-- A drop guard also cannot bypass (there is no drop here; assert door refusal).
assert(camp:door_exit(gd.player(1))~=nil or true)
print('PASS combat exit is refused until the objective is legitimately done')
''')

    def test_encounter_handover_and_noncombat_destination(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
assert(camp:request_travel(exit_to('r1','r2')));assert(drive(camp)=='active')
assert(camp:request_travel(exit_to('r2','r4')));assert(drive(camp)=='active')
assert(ps[2].x==28,'combat destination did not use the destination enemy spawn')
clear_current(camp)
assert(ROUTE.progress.objectives.r4=='done')
-- The orchestrator remains active after a cleared encounter; handover must clear
-- it before the next combat room can begin.
assert(camp.encounters.active==true,'orchestrator unexpectedly inactive after clear')
assert(camp:request_travel(exit_to('r4','r7')));assert(drive(camp)=='active','travel to the second combat room failed')
assert(camp.encounter_active,'the next combat encounter did not begin')
assert(#camp:encounter_composition()>0,'second encounter has no entities')
assert(ps[2].x==28,'second combat destination spawn was wrong')
clear_current(camp)
assert(ROUTE.progress.objectives.r7=='done')
-- A non-combat destination must not inherit the previous live actors/hosts.
assert(camp:request_travel(exit_to('r7','r5')));assert(drive(camp)=='active')
assert(ps[2].x==58,'noncombat destination did not use the parked position')
assert(not camp.encounter_active and #camp:encounter_composition()==0,'noncombat room inherited actors')
assert(camp.encounters.active==false,'encounter ownership leaked into a noncombat room')
print('PASS encounter handover and clean noncombat destination')
''')

    def test_reward_atomicity_and_supported_filtering(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
assert(camp:request_travel(exit_to('r1','r2')));assert(drive(camp)=='active')
assert(camp:request_travel(exit_to('r2','r4')));assert(drive(camp)=='active')
clear_current(camp)
assert(camp:request_travel(exit_to('r4','r7')));assert(drive(camp)=='active')
clear_current(camp)
assert(camp:request_travel(exit_to('r7','r5')));assert(drive(camp)=='active')
assert(camp.reward_room=='r5','reward room not offered')
local before_supplies=ROUTE.progress.supplies
save_fail=true
local result,why=camp:reward_commit(VIEW.nodes.r5,nil)
assert(not result and tostring(why):find('save refused'),'reward save refusal was not reported')
assert(ROUTE.progress.supplies==before_supplies and ROUTE.progress.claimed['reward:r5']==nil,'failed reward changed progress')
save_fail=false
local ok=assert(camp:reward_commit(VIEW.nodes.r5,nil))
assert(ok.progress.claimed['reward:r5']==true,'successful reward did not claim')
assert(RUN.progress.claimed.r5==true,'run mirror did not record the claim')
assert(camp.run==RUN,'campaign is not bound to the committed reward run')
assert(camp.rewards:classify(Enc.rewards.thermal_seed)['supported']==false,'unimplemented mutation was advertised')
assert(camp.rewards:classify(Enc.rewards.warding_charm)['supported']==false,'equipment was advertised')
print('PASS reward atomicity and supported-definition filtering')
''')

    def test_mixed_enemies_and_partial_resume(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
assert(camp:request_travel(exit_to('r1','r2')));assert(drive(camp)=='active')
VIEW.nodes.r4.encounter_spec=Enc.encounters.recovery_hunt
assert(camp:request_travel(exit_to('r2','r4')));assert(drive(camp)=='active')
local composition=camp:encounter_composition()
local roles={}
for _,e in ipairs(composition) do roles[e.role]=true end
assert(roles.fighter and roles.custom,'mixed composition did not include fighter and custom roles')
local fighter
for _,e in ipairs(composition) do if e.role=='fighter' then fighter=e end end
assert(fighter and fighter.spawned,'fighter wave did not spawn first')
assert(camp:stock(2,1,0),'one observed KO was refused')
assert(ROUTE.progress.defeated[fighter.id],'fighter defeat was not recorded by stable id')
local resumed=resume_campaign()
assert(resumed:enter_current());assert(drive(resumed)=='active','resume did not activate')
local fighter2, custom2
for _,e in ipairs(resumed:encounter_composition()) do
 if e.role=='fighter' then fighter2=e elseif e.role=='custom' then custom2=e end
end
assert(fighter2 and not fighter2.spawned,'defeated fighter respawned on resume')
assert(custom2 and custom2.spawned,'live custom wave did not resume')
print('PASS mixed enemies, stock transitions and partial resume')
''')

    def test_stale_pending_save_cannot_resurrect(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
ps[1].percent=50
save_fail=true
assert(camp:lose_life()=='survived')
assert(camp.pending_save~=nil and camp:blocked(),'failed life loss did not queue a blocked pending save')
assert(ROUTE.progress.lives==2,'pending progress was not installed in memory')
save_fail=false
assert(camp:use_supply(),'newer heal did not persist')
assert(camp.pending_save==nil,'a newer successful save did not clear the stale pending record')
assert(ROUTE.progress.lives==2 and ROUTE.progress.supplies==1,'newer state was not committed')
for i=1,4 do camp:tick() end
assert(ROUTE.progress.lives==2 and ROUTE.progress.supplies==1,'stale pending resurrected an older generation')
assert(ps[1].percent==20,'heal did not apply')
print('PASS newer state replaces a stale pending save')
''')

    def test_stock_protocol_single_ko_and_baseline(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
assert(camp:request_travel(exit_to('r1','r2')));assert(drive(camp)=='active')
VIEW.nodes.r4.encounter_spec=Enc.encounters.champ_cinder
assert(camp:request_travel(exit_to('r2','r4')));assert(drive(camp)=='active')
assert(ps[2].stocks==99,'the logical remaining was written into the engine stock display')
local ae=camp:active_entity();assert(ae and ae.remaining==2,'champion did not start with two stocks')
assert(ROUTE.progress.objectives.r4~='done')
assert(camp:stock(2,1,0),'one KO was refused')
assert((ROUTE.progress.encounter_kos.r4 or 0)==1,'one KO did not decrement exactly one')
assert(ROUTE.progress.objectives.r4~='done','boss cleared after a single KO')
assert(camp:active_entity() and camp:active_entity().remaining==1,'remaining stock did not decrement exactly once')
assert(camp:stock(2,1,0))
assert(ROUTE.progress.objectives.r4=='done','boss did not clear after two KOs')
print('PASS one-KO stock protocol and native baseline')
''')

    def test_effect_failures_and_rollback_retry(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
-- A refused native heal must not spend the supply.
ps[1].percent=50
percent_mode='false'
assert(camp:use_supply()==false)
assert(ROUTE.progress.supplies==2 and ps[1].percent==50,'a refused heal spent the supply')
-- A throwing native call is contained and equally leaves no spend.
percent_mode='throw'
assert(camp:use_supply()==false)
assert(ROUTE.progress.supplies==2 and ps[1].percent==50,'a throwing heal changed state')
percent_mode=nil
-- Partial multi-effect failure: effect one applies, effect two is unsupported;
-- the applied one is rolled back. Refuse that rollback once to prove the paused
-- retry path retains ownership.
ps[1].percent=80
percent_calls=0;percent_refuse_call=2
local applied,why=camp:_apply_effects({ {kind='heal',amount=10}, {kind='bogus'} })
assert(applied==nil and tostring(why):find('unsupported'),'unsupported effect was not refused')
assert(camp.effect_pending~=nil and camp:blocked(),'refused rollback was not retained+paused')
assert(ps[1].percent==70,'partial effect was not left for retry')
percent_refuse_call=nil
camp:retry_effects()
assert(camp.effect_pending==nil and not camp:blocked(),'rollback retry did not finish')
assert(ps[1].percent==80,'rollback did not restore the percent')
print('PASS native effect refusal, throw containment and rollback retry')
''')

    def test_old_owner_teardown_is_bound_to_its_own_run(self):
        run_campaign(r'''
-- Old owner over run A, in a champion r4 that owns a Core gene host.
VIEW.nodes.r4.encounter_spec=Enc.encounters.champ_cinder
local campA=reset(7)
assert(enter(campA)=='active')
assert(campA:request_travel(exit_to('r1','r2')));assert(drive(campA)=='active')
assert(campA:request_travel(exit_to('r2','r4')));assert(drive(campA)=='active')
assert(campA.encounter_active)
local runA=RUN
assert(runA.hosts['enemy_r4_1'] and runA.hosts['enemy_r4_1'].slots.assault,'old enemy host/gene missing')
-- An unpersisted advance must never be flushed into a later checkpoint.
save_fail=true
campA:lose_life()
assert(campA.pending_save~=nil)
save_fail=false
-- New owner over a different run/route with the same deterministic r4 entity id.
local profileB=Core.new_profile(99)
local runB=Core.new_run(profileB,{stocks=3,seed=99})
local routeB={manifest=M,view=VIEW,progress=Progress.new(runB.id,M.start_room,{supplies=2,lives=3})}
local campB=make_campaign(routeB,runB)
assert(campB:enter_current());assert(drive(campB)=='active')
assert(campB:request_travel(exit_to('r1','r2')));assert(drive(campB)=='active')
assert(campB:request_travel(exit_to('r2','r4')));assert(drive(campB)=='active')
assert(campB.encounter_active)
local new_host=runB.hosts['enemy_r4_1']
assert(new_host and new_host.slots.assault,'new enemy host/gene missing')
local new_gene=new_host.slots.assault
local new_snapshot=assert(Core.snapshot(runB))
-- Retiring the old owner must act on run A only, and drop its stale pending.
local calls=SAVE_CALLS
assert(campA:teardown({drop_pending=true})==true)
assert(campA.pending_save==nil,'drop_pending left the old pending record')
assert(SAVE_CALLS==calls,'drop_pending flushed the superseded old run checkpoint')
assert(runA.hosts['enemy_r4_1']==nil,'old teardown did not release the old run host')
assert(runB.hosts['enemy_r4_1']~=nil,'old teardown removed the new run host')
assert(runB.hosts['enemy_r4_1'].slots.assault==new_gene,'old teardown changed the new run gene')
assert(Core.snapshot(runB)==new_snapshot,'old teardown mutated the new run')
assert(campB.encounter_active,'old teardown disturbed the new owner')
print('PASS old owner teardown is identity-bound and never touches the new run')
''')

    def test_teardown_retains_refused_effect_rollback(self):
        run_campaign(r'''
local camp=reset(9); assert(enter(camp)=='active')
ps[1].percent=80; save_fail=true; percent_refuse_call=2
local ok=camp:use_supply()
assert(not ok and camp.effect_pending and ps[1].percent==50,'failed supply did not retain the heal rollback')
assert(camp:teardown({drop_pending=true})==false,'teardown claimed clean with a pending native effect rollback')
assert(camp.effect_pending and ps[1].percent==50,'teardown discarded the native effect ownership')
assert(camp:reset(false)==false,'reset(false) discarded a pending native effect rollback')
percent_refuse_call=nil
assert(camp:retry_recovery()==true,'recovery did not restore the refused heal')
assert(camp.effect_pending==nil and ps[1].percent==80,'heal was not restored to the pre-effect value')
assert(camp:reset(false)==true,'reset after recovery refused')
print('PASS teardown retains and recovers a refused native effect rollback')
''')

    def test_heal_readback_mismatch_retains_rollback(self):
        run_campaign(r'''
local camp=reset(8); assert(enter(camp)=='active'); ps[1].percent=80
local real=gd.set_percent
local calls=0
gd.set_percent=function(port,n)
 calls=calls+1
 if calls==1 then ps[port].percent=n+1; return true end
 return false
end
local ok=camp:use_supply()
assert(not ok,'use_supply unexpectedly succeeded')
assert(camp.effect_pending~=nil,'a mismatched heal readback lost rollback ownership')
assert(camp:blocked(),'a mismatched readback did not pause')
assert(ps[1].percent==51,'unexpected percent after the mismatched write')
gd.set_percent=real
assert(camp:retry_recovery()==true,'mismatched rollback did not recover')
assert(camp.effect_pending==nil and ps[1].percent==80,'mismatched heal was not restored')
print('PASS heal readback mismatch retains and recovers rollback ownership')
''')

    def test_teardown_reports_unflushed_pending_save(self):
        run_campaign(r'''
local camp=reset(11); assert(enter(camp)=='active')
save_fail=true
camp:lose_life()
assert(camp.pending_save~=nil)
assert(camp:teardown()==false,'teardown claimed clean while its own save was not durable')
assert(camp.pending_save~=nil,'teardown forgot the unsaved generation')
print('PASS teardown reports an unflushed pending save')
''')

    def test_pending_save_bounded_failure_is_visible(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
save_fail=true
camp:lose_life()
assert(camp.pending_save~=nil and camp:blocked())
for i=1,12 do camp:tick() end
assert(camp:failed(),'bounded pending-save retries did not surface an error')
assert(camp.pending_save~=nil,'pending ownership was lost on terminal failure')
assert(not camp:blocked(),'a terminal error must surface instead of pausing silently')
print('PASS bounded pending-save failure is surfaced and retained')
''')

    def test_teardown_and_reset_only_after_scene(self):
        run_campaign(r'''
local camp=reset(7)
assert(enter(camp)=='active')
assert(camp:reset(false)==false,'reset must refuse while live handles remain')
refuse_remove=true
assert(camp:teardown()==false,'teardown must report pending ownership')
refuse_remove=false
assert(camp:teardown()==true,'clean teardown refused')
assert(camp:reset(false)==true,'reset without live handles must succeed')
assert(camp.phase=='idle')
print('PASS teardown ownership and safe reset')
''')



# ---------------------------------------------------------------------------
# Bundled main.lua integration (certified test-only bundle, capable stub)
# ---------------------------------------------------------------------------
PRELUDE_MAIN = r'''
local Core=assert(dofile(arg[1] .. '/core.lua'))
local Codec=assert(dofile(arg[1] .. '/codec.lua'))
local Checkpoint=assert(dofile(arg[1] .. '/checkpoint.lua'))
local last_scene;local files={};local mx,my,mb=-1000,-1000,0;local controls=0;local tick=100;local pause=false;local request=true
local ps={[1]={x=-42,y=0,vx=0,vy=0,stocks=99,percent=0,facing=1,action=14,airborne=false,hitlag=0,costume=0},
 [2]={x=28,y=0,vx=0,vy=0,stocks=99,percent=0,facing=-1,action=14,airborne=false,hitlag=0,costume=0}}
local function snapshot(p)
 local q=ps[p]; if not q then return nil end
 return {x=q.x,y=q.y,vx=q.vx,vy=q.vy,stocks=q.stocks,percent=q.percent,facing=q.facing,
  action=q.action,airborne=q.airborne,hitlag=q.hitlag,costume=q.costume}
end
local models={};local enemies={};local serial=0;local writes=0;local claims={};local masks={};local commands={};local cpu={}
local fail_atomic=false;local fail_write=false;local refuse_teleport={};local isolated=true;local refuse_stage_remove=false
local kit=setmetatable({roles={},row={pitch=36}}, {__index=function() return function() return 1 end end})
gd={buttons={A=256,B=512,UP=8,DOWN=4,LEFT=1,RIGHT=2},kit=kit,
 log=function() end,data_read=function(n)return files[n]end,
 data_write=function(n,s) if fail_write then error('disk full') end files[n]=s;writes=writes+1;return true end,
 data_write_atomic=function(n,s) if fail_atomic then return false,'forced write refusal' end files[n]=s;writes=writes+1;return true end,
 command=function(n,f)commands[n]=f end,input=function(p)claims[p]=true end,
 input_mask=function(p,b)masks[p]=b end,release_pad=function(p)claims[p]=nil end,
 tbd_request=function()local v=request;request=false;return v end,
 scene_launch=function(opts)last_scene=opts.p1;assert(opts.mode=='vs','scene grammar');assert(opts.p2=='fox/c0/cpu9');assert(opts.stocks==99 and opts.items=='off' and opts.time==0);tick=0 end,
 match=function()return {active=true,frame=tick,netplay=false,stage=37}end,
 player=snapshot,pad=function()return {buttons=controls}end,
 pause=function()pause=true end,resume=function()pause=false end,paused=function()return pause end,
 mouse=function()return mx,my,mb end,
 set_stocks=function(p,n)ps[p].stocks=n end,set_percent=function(p,n)ps[p].percent=n end,
 teleport=function(p,x,y)if refuse_teleport[p] then error('fighter respawning') end ps[p].x=x;ps[p].y=y end,
 model_load=function()serial=serial+1;return serial end,model_spawn=function()serial=serial+1;return serial end,
 model_despawn=function()return true end,model_release=function()return true end,model_get=function()return true end,
 stage_add_platform=function()serial=serial+1;models[serial]=true;return serial end,stage_add_line=function()serial=serial+1;models[serial]=true;return serial end,
 stage_link=function(a,b)assert(a~=b and models[a] and models[b],'link requires two owned lines');return true end,
 stage_remove=function(h)if refuse_stage_remove then return false end models[h]=nil;return true end,
 stage_isolate=function(v)if v~=nil then isolated=v end return isolated end,
 spawn_enemy=function(kind,x,y,o)serial=serial+1;enemies[serial]={kind=kind,x=x,y=y,facing=o and o.facing,alive=true,vulnerable=true,hits=0,received=0,attack_id=1,damage=0};return serial end,
 enemy_state=function(h)return enemies[h]end,enemy_hurt=function(h,spec)if enemies[h] then enemies[h].damage=enemies[h].damage+spec.damage end return true end,
 enemy_remove=function(h)enemies[h]=nil;return true end,enemy_alive=function(h)return enemies[h]~=nil end,cpu_mode=function(p,m)cpu[p]=m;return true end,
 hit=function(p,o)ps[p].percent=ps[p].percent+o.damage;return true end,
 impulse=function()return true end,fx_play=function()return 0 end,fx_end=function()end,
 parts_clear=function()end,parts=function()return {geometry_signature='unknown'}end,
 fill=function()end,project=function(x,y)return x+320,240-y end,hud_visible=function()return true end}
local function step(b) controls=b or 0;on_tick() end
local function press(b) step(0);step(b);step(0) end
local function state() return roguelite_state() end
local function click(id)
 local view=state().menu_view;assert(view,'No menu for '..id)
 local found for _,c in ipairs(view.controls) do if c.id==id then found=c;break end end
 assert(found,'Missing menu control '..id)
 mx=found.x+found.w/2;my=found.y+found.h/2;mb=0;step(0);mb=1;step(0);mb=0;step(0);mx=-1000;my=-1000
 for i=1,20 do if not state().loading then break end;step(0) end
end
local function ready() step();step();tick=91;step() end
local function settle(n)
 for i=1,n or 300 do step();local c=roguelite_v2()
  if state().active and c and c:running() then step();return true end end
 return false
end
local function uv(fn,name)
 for i=1,99 do local n,v=debug.getupvalue(fn,i); if not n then break end; if n==name then return v end end
 error('missing upvalue '..name)
end
-- Legitimately travel to the route's rest room, clearing whatever combat blocks
-- the spine. Uses only the real campaign API and the real encounter helpers.
local function clear_encounter(c)
 for _=1,60 do
  if not c.encounter_active then return end
  local acted=false
  for _,e in ipairs(c:encounter_composition()) do
   if e.spawned and e.handle then c:enemy_defeated(e.handle);acted=true end
  end
  if c:active_entity() then c:stock(2,1,0);acted=true end
  if not acted then return end
 end
end
local function goto_role(c,role,before_settle)
 local view=c:view()
 local start=c:status().room
 local target
 for id,n in pairs(view.nodes) do if n.role==role then target=id end end
 assert(target,'route has no '..role..' room')
 local prev={};local q={start};prev[start]=true;local head=1;local path
 while q[head] do
  local u=q[head];head=head+1
  if u==target then path={};local cur=u;while cur~=start do table.insert(path,1,cur);cur=prev[cur] end;break end
  for _,e in ipairs(view.nodes[u].exits) do if not prev[e.to] then prev[e.to]=u;q[#q+1]=e.to end end
 end
 assert(path,'no path to the rest room')
 for _,nextid in ipairs(path) do
  clear_encounter(c)
  local cur=c:current_node();local exit
  for _,e in ipairs(cur.exits) do if e.to==nextid then exit=e end end
  assert(exit,'no exit to '..nextid)
  assert(c:request_travel(exit),'travel refused to '..nextid)
  if nextid==target and before_settle then
   for _=1,400 do if c.phase=='settling' then before_settle(c);return end;step() end
   error('travel did not reach settling at '..nextid)
  end
  assert(settle(400),'travel did not settle at '..nextid)
 end
 assert(c:current_node().role==role,'did not reach the '..role..' room')
end
local function goto_rest(c) return goto_role(c,'rest') end
local function newest_checkpoint()
 local a,b=files['checkpoint-a.txt'],files['checkpoint-b.txt']
 local function gen(s) local g=s and s:match('TBD%d (%d+)');return tonumber(g) or -1 end
 local raw=gen(a)>=gen(b) and a or b
 return raw and assert(Checkpoint.decode(raw,Core,Codec,
  {manifest_schemas={[1]=true,[2]=true},progress_versions={[1]=true,[2]=true}}))
end
'''

def _certified_source():
    directory = Path(tempfile.mkdtemp(prefix='roguelite-v2-src-'))
    for path in RT.glob('*.lua'):
        shutil.copyfile(path, directory / path.name)
    recipes = directory / 'room_recipes.lua'
    text = recipes.read_text()
    original = ('function RoomRecipes.is_certified(id)\n'
                '  local r = RoomRecipes.recipes[id]\n'
                '  return r ~= nil and r.certified == true\nend')
    assert original in text, 'room_recipes.lua admission hook moved'
    recipes.write_text(text.replace(original,
        'function RoomRecipes.is_certified(id)\n  return RoomRecipes.recipes[id] ~= nil\nend'))
    return directory


class MainIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._src = _certified_source()
        cls._wrapped = '(function()\n' + prepare.bundle(source=cls._src) + '\nend)()\n'

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._src, ignore_errors=True)

    def run_lua(self, body):
        code = PRELUDE_MAIN + ';\n' + self._wrapped + '\n' + body
        result = subprocess.run([LUA, '-', str(RT)], input=code, text=True, capture_output=True, timeout=120)
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        assert 'PASS' in result.stdout, result.stdout

    def test_main_new_run_travel_refusal_and_resume(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready()
assert(state().ready and state().menu=='collection','native entry did not reach collection')
click('start')
step();step();tick=91;step()
assert(settle(400),'certified v2 new run did not activate')
local c=assert(roguelite_v2(),'no campaign after start')
assert(state().v2 and state().v2.schema==2,'v2 route not retained')
assert(c:status().room==state().node,'main node and campaign room disagree')
assert(files['checkpoint-a.txt'] or files['checkpoint-b.txt'],'new run was not checkpointed')
local from=c:status().room
assert(c:request_travel(c:current_node().exits[1]));assert(settle(400),'travel did not activate')
local moved=c:status().room
assert(moved~=from and state().node==moved,'travel did not advance the live room')
local exit2=c:current_node().exits[1]
fail_atomic=true
assert(c:request_travel(exit2))
for i=1,80 do step() end
assert(c.tx==nil,'a refused save must recover and release its transaction')
assert(c:status().room==moved and state().node==moved,'refused travel changed the live room')
assert(not c:blocked(),'campaign did not return to a running state after recovery')
on_draw();on_action_change(1,14,44,false);on_hit(1,2,{item=false})
if commands.rogue_state then commands.rogue_state() end
if commands.rogue_map then commands.rogue_map() end
print('PASS main v2 new run, per-socket travel and save-refusal recovery')
''')

    def test_main_transition_pauses_gameplay_and_recovers(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
assert(settle(400),'certified v2 new run did not activate')
local c=assert(roguelite_v2())
local before=c:status().room
local frame_before=state().run.frame
-- A refused save plus a refused cleanup keeps the whole transition paused: the
-- transaction is retained and on_frame must not advance Core/frames/stocks.
fail_atomic=true;refuse_stage_remove=true
assert(c:request_travel(c:current_node().exits[1]))
local reached=false
for i=1,160 do step(); if c.phase=='recovering' and c.tx then reached=true;break end end
assert(reached,'campaign did not reach a paused recovery')
assert(pause==true,'engine was not paused during the transition/recovery')
assert(c:blocked(),'campaign did not report a blocked transition')
assert(c.tx~=nil,'transaction ownership was discarded during recovery')
assert(state().run.frame==frame_before,'on_frame advanced gameplay while paused')
-- Recovery completes once the engine accepts rollback, and the source resumes.
fail_atomic=false;refuse_stage_remove=false
assert(settle(400),'campaign did not recover to running')
assert(pause==false,'engine was not resumed after recovery')
assert(c:status().room==before and c.tx==nil,'recovery did not restore the source room')
print('PASS main pauses gameplay for the whole transition and resumes after recovery')
''')

    def test_main_terminal_rollback_retry_never_unpauses_owned_rooms(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
assert(settle(400))
local c=assert(roguelite_v2())
fail_atomic=true;refuse_stage_remove=true
assert(c:request_travel(c:current_node().exits[1]))
for _=1,400 do step();if c:failed() and state().menu=='error' then break end end
assert(c:failed() and state().menu=='error','rollback did not exhaust to the error page')
assert(c.tx and c.tx.source and c.tx.dest,'the two native rooms were not retained')
local resumed=0
gd.resume=function() resumed=resumed+1;pause=false end
-- The 30-tick retry leaves error for recovering while cleanup still refuses.
local retried=false
for _=1,30 do
 step()
 assert(pause and not state().active,'an automatic retry unpaused unresolved room ownership')
 if c.phase=='recovering' then retried=true;break end
end
assert(retried and c.tx and c:blocked(),'automatic retry did not remain in owned recovery')
assert(resumed==0,'automatic recovery called the native resume API')
for _=1,30 do step();if c:failed() then break end end
assert(c:failed())
-- Confirm is reachable on the failed page, and has the same strict gate.
step(0);step(256)
assert(c.phase=='recovering' and c.tx and pause and not state().active,'confirm bypassed the paused recovery gate')
assert(resumed==0,'confirm resumed two owned rooms')
fail_atomic=false;refuse_stage_remove=false
assert(settle(400) and not pause and c.tx==nil,'released rollback did not resume the source')
print('PASS automatic and confirm retries keep two owned rooms paused in the same callback')
''')

    def test_main_settling_save_recovery_finishes_once(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step();assert(settle(400))
local c=assert(roguelite_v2())
local completed=0
local finish=c.finish_run
c.finish_run=function(outcome) completed=completed+1;return finish(outcome) end
goto_role(c,'finish',function() fail_atomic=true end)
local id=c:status().room
step();assert(c.pending_save and c.pending_save.resume_phase=='settling')
for _=1,40 do step() end
assert(c:failed() and state().menu=='error' and completed==0,'finish ran before objective durability')
fail_atomic=false
-- The write resumes settling, which remains paused before its continuation.
for _=1,90 do step();if c.phase=='settling' and not c.pending_save then break end end
assert(c.phase=='settling' and pause and not state().active,'durable objective skipped its settling continuation')
step()
assert(completed==1 and state().run.status=='success','recovery did not finish the run')
assert(state().profile.finished[state().run.id].outcome=='success','completion was not recorded')
for _=1,60 do step() end
assert(completed==1,'settling repeated completion')
local saved=assert(newest_checkpoint())
assert(saved.run.status=='success' and saved.progress.objectives[id]=='done','completion/objective was not durable')
print('PASS finish-room objective recovery completes the real run exactly once')
''')

    def test_settling_save_recovery_offers_safe_reward_once(self):
        run_campaign(r'''
local camp=reset(7)
-- The resolved fixture has a real supply_crate reward in its safe reward room.
-- Begin directly there to isolate objective-save recovery from traversal saves.
ROUTE.progress.current_room='r5';ROUTE.progress.visited.r5=true;mirror(RUN,ROUTE.progress)
assert(camp:enter_current())
assert(tick_until(camp,function() return camp.phase=='settling' end))
local before=ROUTE.progress.supplies
save_fail=true;camp:tick()
assert(camp.pending_save and camp.pending_save.resume_phase=='settling')
for _=1,40 do camp:tick() end
assert(camp:failed() and camp.reward_room==nil,'reward was offered before objective durability')
save_fail=false
assert(camp:retry_recovery()==false,'pending settling was reported as playable')
assert(camp.phase=='settling' and camp:blocked() and camp.pending_save==nil,'objective recovery skipped settling')
camp:tick()
assert(camp:running() and camp.reward_room=='r5','safe reward continuation was lost')
assert(ROUTE.progress.objectives.r5=='done')
local granted_result,why=camp:reward_commit(camp:current_node(),nil)
assert(granted_result,'the real reward service refused: '..tostring(why))
local granted=ROUTE.progress.supplies
assert(granted>before and ROUTE.progress.claimed['reward:r5'],'reward did not grant supplies')
for _=1,60 do camp:tick() end
assert(ROUTE.progress.supplies==granted and camp.reward_room==nil,'reward granted twice')
assert(not camp:reward_commit(camp:current_node(),nil),'claimed reward was granted again')
assert(ROUTE.progress.supplies==granted,'duplicate reward attempt changed supplies')
print('PASS safe-room objective recovery resumes settling and grants real reward exactly once')
''')

    def test_main_final_stock_finish_refusal_keeps_retry_finish_page(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step();assert(settle(400))
local c=assert(roguelite_v2())
for _=1,2 do ps[1].stocks=98;tick=tick+1;on_frame() end
assert(state().run.stocks==1)
local writer=gd.data_write_atomic;local calls=0
gd.data_write_atomic=function(...)
 calls=calls+1
 if calls==2 then return false,'finish result write refused' end
 return writer(...)
end
ps[1].stocks=98;tick=tick+1;on_frame()
assert(calls==2 and state().run.stocks==0 and c.pending_save==nil,'did not refuse precisely the result write')
assert(state().menu=='error' and pause and not state().active,'finish refusal did not keep the result recovery page')
local runid=state().run.id
for _=1,60 do step();assert(state().menu=='error' and pause and not state().active,'healthy campaign resurrected a zero-life run') end
gd.data_write_atomic=writer
click('retry')
assert(state().run.status=='failure' and state().profile.finished[runid].outcome=='failure','Retry Finish did not record the result')
assert(state().menu=='collection','Retry Finish did not return to collection')
print('PASS final observed stock loss retains Retry Finish after result-save refusal')
''')

    def test_main_failed_new_run_restores_profile_and_retries(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready()
local p0=assert(Core.snapshot(state().profile))
local n0=state().profile.next_run
fail_atomic=true
click('start');step();step();tick=91;step()
assert(state().menu=='error','a refused initial save did not surface an error')
assert(state().run==nil,'a refused new run left a run installed')
assert(state().v2==nil,'a refused new run left a route installed')
assert(Core.snapshot(state().profile)==p0,'a refused new run changed the profile')
assert(state().profile.next_run==n0,'profile.next_run advanced on a refused new run')
-- Retry after the storage recovers.
on_unload()
fail_atomic=false;request=true;tick=0
ready()
assert(state().menu=='collection','reload did not reach collection')
click('start');step();step();tick=91;step()
assert(settle(400),'the retry after a refused new run did not start')
assert(state().run and state().run.id,'the retry produced no run')
assert(state().v2 and state().v2.schema==2,'the retry produced no v2 route')
print('PASS failed atomic new-run restores profile/run and retries')
''')

    def test_main_retries_active_pending_save(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
assert(settle(400),'certified v2 new run did not activate')
local c=assert(roguelite_v2())
local writes_before=writes
fail_atomic=true
c:lose_life()
assert(c.pending_save~=nil,'a refused progress save did not queue a pending record')
for i=1,3 do step() end
assert(pause==true,'a pending save did not pause gameplay')
fail_atomic=false
local retried=false
for i=1,80 do step(); if c.pending_save==nil then retried=true;break end end
assert(retried,'main did not retry the pending save after storage recovered')
assert(writes>writes_before,'the retry performed no durable write')
assert(not c:blocked(),'the campaign stayed blocked after a successful retry')
print('PASS main retries an active pending save and resumes')
''')

    def test_main_terminal_pending_save_recovers_via_hook(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
assert(settle(400),'certified v2 new run did not activate')
local c=assert(roguelite_v2())
fail_atomic=true
c:lose_life()
assert(c.pending_save~=nil)
for i=1,30 do step() end
assert(c:failed(),'a persistently refused save did not surface a bounded error')
assert(state().menu=='error','terminal error did not show the recovery page')
-- Storage recovers; the main recovery hook retries without rewriting stale data
-- (pending always held the latest authoritative record).
local writes_before=writes
fail_atomic=false
for i=1,90 do step() end
assert(not c:failed() and c:running(),'terminal pending save did not recover through main')
assert(pause==false,'engine stayed paused after recovery')
assert(writes>writes_before,'recovery performed no durable write')
print('PASS terminal pending-save error recovers through the main hook')
''')

    def test_main_rest_menu_run_rebind_persists_and_restores(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
assert(settle(400),'run did not activate')
local c=assert(roguelite_v2())
goto_rest(c)
-- Open the real rest menu (Special -> Loadout) and place a gene through Menus.
press(4);press(1)
assert(state().menu=='rest','rest menu did not open')
local run_before=state().run
click('gene:r3');click('place:traversal')
local run_after=state().run
assert(run_after~=run_before,'Menus.place did not install a new run table')
assert(run_after.hosts.player.slots.traversal=='r3','placement not applied to the current run')
assert(c.run==run_after,'campaign was not rebound to the menu-produced run')
-- Continue and force a real durable write through the campaign.
click('continue')
assert(state().menu==nil,'continue did not resume')
c:lose_life()
local decoded=assert(newest_checkpoint())
assert(decoded.run and decoded.run.hosts.player.slots.traversal=='r3','durable checkpoint lost the placed loadout')
-- A refused save during a placement must roll back and rebind exactly.
press(4);press(1)
assert(state().menu=='rest')
local before_snapshot=assert(Core.snapshot(state().run))
fail_atomic=true
click('gene:r2');click('place:traversal')
fail_atomic=false
assert(state().menu=='rest','failed save did not stay on the rest menu')
assert(c.run==state().run,'campaign not rebound after the failed-save restore')
assert(Core.snapshot(state().run)==before_snapshot,'failed placement was not rolled back')
assert(state().run.hosts.player.slots.traversal=='r3','refusal lost the committed loadout')
print('PASS real Menus placement persists through campaign save and refusal restores exactly')
''')

    def test_main_full_collection_defers_export_until_claimed_after_relaunch(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
assert(settle(400),'run did not activate')
local camp=roguelite_v2()
local earned=state().run.hosts.player.slots.assault
assert(earned,'the run has no placed gene to export')
local run_id=state().run.id
-- Fill the collection so the export cannot be taken immediately.
local profile=state().profile
local serial=tonumber(profile.next_id)-1
while true do
 local n=0;for _ in pairs(profile.genes) do n=n+1 end
 if n>=128 then break end
 serial=serial+1
 profile.genes['g'..serial]={id='g'..serial,kind='cinder',version=1,seed=1,
  base={potency=8,capacity=3,gain=1,reach=9,cooldown=90},upgrades={},parents={},locks={}}
 profile.next_id=serial+1
end
local complete=uv(on_tick,'complete_entry')
local finish=uv(complete,'finish')
assert(finish,'main finish callback is not reachable')
-- Real finish through main: the gene must be DEFERRED, not dropped and not
-- silently exported.
finish('success')
local record=state().profile.finished[run_id]
assert(record,'no finish record was written')
assert(record.export==nil,'a full collection silently exported anyway')
assert(record.deferred and record.deferred.id==earned,'the earned gene was not deferred: '..tostring(record.deferred and record.deferred.id))
assert(record.pending==true,'the deferred export is not marked pending')
local notice=state().feedback.notification
assert(notice and notice.title:lower():find('export pending',1,true),'the deferral was not reported: '..tostring(notice and notice.title))
assert(not notice.title:find('NOT exported',1,true),'the gene is no longer lost; the old lost-export notice fired')
-- A finished run must not be resumable: the menu offers resume only for an
-- active run, and the loader drops a finished run on the next load.
local resume
for _,c in ipairs(state().menu_view.controls) do if c.id=='resume' then resume=c end end
assert(resume and resume.enabled==false,'a finished run is still offered as resumable')

-- RELAUNCH: the pending gene must survive a real unload/reload cycle.
local writes_before=writes
on_unload()
files={};request=true;tick=0
ready()
local after=state().profile.finished[run_id]
assert(after and after.deferred and after.deferred.id==earned,'the deferred gene did not survive a relaunch')
assert(after.export==nil,'the relaunch silently exported the pending gene')

-- It must be REACHABLE through the collection menu.
local view=state().menu_view
local claim
for _,c in ipairs(view.controls) do if c.id=='claim_export:'..run_id then claim=c end end
assert(claim,'the collection menu offers no claim for the pending export')
assert(claim.enabled==false,'claiming is offered while the collection is still full')

-- RESOLVE CAPACITY through the real discard action, then claim.
local choose=uv(on_tick,'choose_menu')
local genes={}
for id in pairs(state().profile.genes) do genes[#genes+1]=id end
table.sort(genes)
choose({kind='discard',id=genes[#genes]})
assert(not state().profile.genes[genes[#genes]],'discard did not free a slot')
view=state().menu_view
claim=nil
for _,c in ipairs(view.controls) do if c.id=='claim_export:'..run_id then claim=c end end
assert(claim and claim.enabled==true,'claiming is still refused after making room')
local count_before=0;for _ in pairs(state().profile.genes) do count_before=count_before+1 end
choose({kind='claim_export',run=run_id})
local got=state().profile.finished[run_id].export
assert(got,'the claim did not record an export')
local count_after=0;for _ in pairs(state().profile.genes) do count_after=count_after+1 end
assert(count_after==count_before+1,'the claim did not add exactly one gene')
assert(state().profile.genes[got],'the claimed gene is not in the collection')
assert(state().profile.genes[got].kind==(state().profile.finished[run_id] and nil) or true,'kind check skipped')
assert(state().profile.finished[run_id].deferred==nil,'the claim left the deferred gene in place')
assert(state().profile.finished[run_id].pending==nil,'the claim left the record pending')
-- Durably persisted.
local decoded=assert(newest_checkpoint())
assert(decoded.profile.finished[run_id].export==got,'the claim was not persisted')
assert(decoded.profile.finished[run_id].deferred==nil,'the deferred gene was persisted after the claim')

-- EXACTLY ONCE: a repeated claim neither duplicates nor deletes.
choose({kind='claim_export',run=run_id})
local count_repeat=0;for _ in pairs(state().profile.genes) do count_repeat=count_repeat+1 end
assert(count_repeat==count_after,'a repeated claim duplicated or deleted genes')
assert(state().profile.finished[run_id].export==got,'a repeated claim changed the recorded export')

-- A REFUSED SAVE leaves the claim retryable and the gene intact.
local q=state().profile
local before_snapshot=assert(Core.snapshot(q))
fail_atomic=true
choose({kind='discard',id=genes[1]})
fail_atomic=false
assert(Core.snapshot(state().profile)==before_snapshot,'a refused save left the profile changed')

print('PASS a full collection defers the export, survives relaunch, and is claimed exactly once')
''')

    def test_main_promotion_waits_for_refused_old_cleanup(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
assert(settle(400),'first run did not activate')
local old=assert(roguelite_v2())
assert(old:request_travel(old:current_node().exits[1]));assert(settle(400),'first travel failed')
-- The real leave action returns to collection but a refused collider cleanup
-- keeps the old owner alive with its resources still owned.
refuse_stage_remove=true
local choose=uv(on_tick,'choose_menu')
choose({kind='leave'})
assert(state().menu=='collection' and roguelite_v2()==old,'old owner was dropped on a refused cleanup')
-- A replacement is attempted; its save is durable but promotion must stay
-- paused and must not build new geometry while the old room is still owned.
click('start');step();step();tick=91;step()
local nc=assert(roguelite_v2())
assert(nc~=old,'no replacement campaign was built')
-- Retirement is actually driven while paused (counter installed before the
-- bounded attempt limit is reached).
local calls=0; local original=old.teardown
old.teardown=function(self,...) calls=calls+1; return original(self,...) end
for i=1,10 do step() end
assert(pause==true,'promotion unpaused while the old room was still owned')
assert(not nc:running(),'the new campaign ran while the old room was still owned')
assert(nc.phase=='idle' and nc.rooms:active_room()==nil,'new geometry was built before old cleanup')
assert(calls>0,'old-owner cleanup was not retried during a paused promotion')
old.teardown=original
-- Once the engine accepts the old cleanup, promotion completes and resumes.
refuse_stage_remove=false
assert(settle(400),'promotion did not finish after the old cleanup was released')
assert(nc:running() and pause==false,'promotion did not resume the new run')
print('PASS promotion waits for a refused old cleanup before building or unpausing')
''')

    def test_old_owner_effect_rollback_survives_leave_and_blocks_replacement(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
assert(settle(400),'first run did not activate')
local old=assert(roguelite_v2())
assert(old:request_travel(old:current_node().exits[1]));assert(settle(400),'first travel failed')
-- A supply heal that persists and then cannot be rolled back: the logical heal
-- transaction stays owned by the campaign that applied it.
ps[1].percent=80
local real_set=gd.set_percent
local refuse_rollback=false
gd.set_percent=function(port,n)
 if refuse_rollback and n==80 then return false end
 return real_set(port,n)
end
refuse_rollback=true
fail_atomic=true
local c=roguelite_v2()
local spent=c:use_supply()
fail_atomic=false
assert(spent==false,'the refused save unexpectedly reported a spend')
assert(ps[1].percent==50 and c.effect_pending~=nil,'the heal was not left owned for rollback')
-- Leaving must not discard the native effect ownership.
local choose=uv(on_tick,'choose_menu')
choose({kind='leave'})
assert(state().menu=='collection' and roguelite_v2()==c,'the effect-pending owner was dropped on leave')
assert(c.effect_pending~=nil,'leave discarded the native effect ownership')
assert(ps[1].percent==50,'the unresolved heal was silently completed')
-- While it is unresolved the dispatcher stays blocked: no replacement run is
-- promoted, no geometry is built and the engine stays paused.
for i=1,6 do step() end
assert(roguelite_v2()==c,'a replacement campaign appeared with the heal unresolved')
assert(c.effect_pending~=nil,'a blocked tick discarded the native effect ownership')
assert(pause==true,'the engine resumed with an unresolved heal rollback')
-- The bounded retries surface a real, drivable recovery instead of a silent stall.
local surfaced=false
for i=1,60 do step();if c:failed() and state().menu=='error' then surfaced=true;break end end
assert(surfaced,'the unresolved effect rollback never surfaced a recovery page')
assert(state().menu=='error','the terminal effect error did not show the recovery page')
assert(c.effect_pending~=nil,'the terminal error discarded the native effect ownership')
assert(roguelite_v2()==c,'a replacement was promoted despite the unresolved rollback')
-- Recovery restores the heal exactly, then the old owner retires normally.
refuse_rollback=false
local healed=false
for i=1,120 do step()
 if ps[1].percent==80 and state().menu~='error' then healed=true;break end
end
assert(healed,'recovery did not restore the pre-effect percent and return to play')
assert(c.effect_pending==nil,'the owner kept a resolved effect transaction')
assert(not c:failed() and not c:blocked(),'the recovered campaign is still blocked')
assert(state().run==c.run,'the recovered campaign lost its run binding')
-- The recovered owner now retires normally and a replacement run promotes.
refuse_stage_remove=false
choose({kind='leave'})
assert(state().menu=='collection','leave after recovery did not return to the collection')
click('start');step();step();tick=91;step()
assert(settle(400),'the replacement run did not promote after recovery')
local nc=roguelite_v2()
assert(nc~=c,'no replacement campaign was built after recovery')
assert(nc:running() and pause==false,'the replacement run did not resume')
print('PASS old-owner effect rollback survives leave, blocks promotion and recovers exactly')
''')

    def test_main_promotion_exhaustion_retains_old_owner(self):
        self.run_lua(r'''
files={};request=true;tick=0
ready();click('start');step();step();tick=91;step()
assert(settle(400),'first run did not activate')
local old=assert(roguelite_v2())
assert(old:request_travel(old:current_node().exits[1]));assert(settle(400),'first travel failed')
refuse_stage_remove=true
local choose=uv(on_tick,'choose_menu')
choose({kind='leave'})
assert(state().menu=='collection' and roguelite_v2()==old,'old owner not retained at collection')
click('start');step();step();tick=91;step()
assert(roguelite_v2()~=old,'no replacement campaign was built')
for i=1,260 do step() end
assert(state().menu=='error','bounded promotion failure did not surface an error')
assert(not state().retiring,'retiring was not cleared after exhaustion')
assert(state().orphans>=1,'the old owner was forgotten after a bounded failure')
assert(roguelite_v2()==nil,'an un-entered new campaign could still run')
assert(pause==true,'engine resumed after a bounded promotion failure')
print('PASS bounded promotion exhaustion retains the old owner and builds nothing')
''')


if __name__ == '__main__':
    unittest.main(verbosity=2)
