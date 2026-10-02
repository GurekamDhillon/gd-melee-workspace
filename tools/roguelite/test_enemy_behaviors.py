#!/usr/bin/env python3
"""Actual-Lua enemy/boss behaviour invariants; engine stubs, not a playtest.

Loads the real Core, catalogues, Codec and the new encounter/boss behaviour
modules and drives the pure observation -> decision -> legal-request boundary
with injected observations. It proves the authored archetypes/compositions, the
six-archetype and twelve-composition targets, three distinct boss controllers,
observable-only history and delayed visible phase inputs, reaction-delayed
fairness, Core-legal ability requests, tell target/slot retention, the
simultaneous-tell arbiter, separated measured counters, generation-safe
ownership, escape not-defeat, room-aware ledge/recovery, real boss defeat and
resume lifecycles and the run/checkpoint-bound progress addon. It does not
establish native combat, visuals or normal-speed gameplay; those remain pending.
"""
from pathlib import Path
import shutil
import subprocess
from unittest import TestCase, main

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

MODULES = [RT / name for name in (
    'core.lua', 'codec.lua', 'encounter_catalogue.lua', 'enemy_catalogue.lua',
    'encounter_behaviors.lua', 'boss_behaviors.lua')]

PRELUDE = r'''
local C=assert(dofile(arg[1])); local Codec=assert(dofile(arg[2]))
local Enc=assert(dofile(arg[3])); local EnemyCat=assert(dofile(arg[4]))
local B=assert(dofile(arg[5])); local Boss=assert(dofile(arg[6]))
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
local function count(t) local n=0 for _ in pairs(t) do n=n+1 end return n end
local function any_kind(evs,kind) for _,e in ipairs(evs or {}) do if e.kind==kind then return e end end return nil end
local function ability_req(reqs) for _,q in ipairs(reqs or {}) do if q.kind=='ability' then return q end end return nil end

local function charged_run(family,slot,trigger,n)
 local p=C.new_profile(4242); local r=C.new_run(p)
 local host='enemy_test_1'
 local id=assert(C.acquire(r,family)); assert(C.equip(r,host,slot,id))
 for i=1,(n or 3) do assert(C.on_event(r,{host=host,kind=trigger or 'direct_hit',move_id=host..':m'..i,lineage='direct'})) end
 return r,host,id
end

-- A charged run for an explicit profile seed/host/family, to build two profiles
-- that share the same textual run id and gene id.
local function charged_run_for(profile_seed,host,family,slot,trigger,n)
 local p=C.new_profile(profile_seed); local r=C.new_run(p)
 local id=assert(C.acquire(r,family)); assert(C.equip(r,host,slot or 'assault',id))
 for i=1,(n or 3) do assert(C.on_event(r,{host=host,kind=trigger or 'direct_hit',move_id=host..':x'..i,lineage='direct'})) end
 return r,id
end

local BOUNDS=function() return {min_x=-100,max_x=100,min_y=-40,max_y=40,center_x=0,floor_y=40} end
local function selfpose(over)
 local s={id='enemy_test_1',x=0,y=0,vx=0,vy=0,facing=1,grounded=true,airborne=false,on_stage=true,hitlag=0,action=14,kos=0,hits_taken=0,alive=true}
 for k,v in pairs(over or {}) do s[k]=v end return s
end
local function tgt(over)
 local t={id='player',port=1,kind='player',x=4,y=0,vx=0,vy=0,facing=-1,grounded=true,airborne=false,offstage=false,hitlag=0,action=14,attacking=false,vulnerable=true,percent=0}
 for k,v in pairs(over or {}) do t[k]=v end return t
end
local function obs(over)
 local o={frame=0,bounds=BOUNDS(),self=selfpose(),targets={tgt()}}
 for k,v in pairs(over or {}) do o[k]=v end return o
end

local function make_manager(r,over)
 over=over or {}
 local events={}
 local m=B.new(C,{get_run=function() return r end,on_event=function(e) events[#events+1]=e end,
  visible=over.visible,actions=over.actions,permission=over.permission},
  {max_actors=over.max_actors,max_simultaneous_tells=over.max_simultaneous_tells,
   tell_gap=over.tell_gap,seed=over.seed})
 m.events=events
 return m
end

local function add_agent(m,over)
 local a={id='enemy_test_1',host='enemy_test_1',archetype='pressure',slot='assault',family='cinder',level=5,seed=11}
 for k,v in pairs(over or {}) do a[k]=v end
 return m:add(a)
end

-- A manager whose authoritative run can be swapped mid-flight, so a test can
-- change manager.get_run() between a tell start and its release.
local function make_holder_manager(holder,over)
 over=over or {}
 local events={}
 local m=B.new(C,{get_run=function() return holder.run end,on_event=function(e) events[#events+1]=e end,
  visible=over.visible,actions=over.actions,permission=over.permission},
  {max_actors=over.max_actors,max_simultaneous_tells=over.max_simultaneous_tells,
   tell_gap=over.tell_gap,seed=over.seed})
 m.events=events
 return m
end

-- Drive until the first tell, returning {event=, frame=}. Starts at the
-- manager's current decision frame so it is safe to call more than once.
local function drive_to_tell(m,id,obs_for,frames)
 local base=m.frame or 0
 for f=base,base+(frames or 60) do
  local ok,o=m:tick(f,{[id]=obs_for(f)})
  if ok then
   local t=any_kind(o.events,'tell')
   if t then return {event=t,frame=f} end
  end
 end
 return nil
end
local function drive_to_ability(m,id,obs_for,frames)
 local base=m.frame or 0
 for f=base,base+(frames or 90) do
  local ok,o=m:tick(f,{[id]=obs_for(f)})
  if ok then
   local q=ability_req(o.requests)
   if q then return {request=q,frame=f} end
  end
 end
 return nil
end
'''

def _run(body):
    program = PRELUDE + '\n' + body
    result = subprocess.run([LUA, '-', *[str(m) for m in MODULES]],
                            input=program, text=True, capture_output=True)
    if result.returncode != 0:
        Path('/tmp/enemy-behaviors-failure.lua').write_text(program)
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout


class EnemyBehaviorTests(TestCase):
    def test_catalogue_targets_contract_and_real_contracts(self):
        _run(r'''
assert(B.validate(C,EnemyCat,Enc),'authored data failed validation')
assert(count(B.archetypes)==6 and count(B.compositions)==12)
local sigs={}; local custom,fighter=0,0
for id,a in pairs(B.archetypes) do
 local sig=table.concat({a.motion,a.reaction,a.tell_frames,a.recovery_frames,a.reaction_trigger,a.ledge},'|')
 assert(not sigs[sig],'archetype signature repeated: '..id); sigs[sig]=true
 if a.host=='custom' then custom=custom+1 else fighter=fighter+1 end
end
assert(custom>0 and fighter>0,'archetypes do not span custom/fighter hosts')
for id,comp in pairs(B.compositions) do
 assert(Enc.encounters[id],'composition '..id..' has no encounter row')
 for _,row in ipairs(comp.actors) do
  assert(C.definitions[row.family] and C.definitions[row.family].variants[row.slot])
 end
end
assert(Boss.validate(C,Enc))
assert(count(Boss.controllers)==3 and count(Boss.compositions)==3)
-- The explicit observation adapter contract exists and names the real meanings.
assert(B.adapter_contract.version==1)
assert(B.adapter_contract.self_kos and B.adapter_contract.self_hits_taken)
assert(B.adapter_contract.custom_received and B.adapter_contract.custom_hits)
-- Height is upward from the floor, not below it.
local x,y=B.placement({center_x=0,floor_y=10,min_x=-50,max_x=50},0,1)
assert(y>10,'placement height is below the floor: '..tostring(y))
print('catalogue: 6 archetypes, 12 compositions, 3 bosses and contract validated')
''')

    def test_observation_boundary_ignores_hidden_input(self):
        _run(r'''
local clean,why=B.sanitize_obs(obs()); assert(clean and not why)
local dirty,werr,dropped=B.sanitize_obs({frame=0,bounds=BOUNDS(),
 self=selfpose({input=1,teleport={x=999},buttons=255}),targets={tgt({input=9})},secret='x'})
assert(dirty and not werr)
assert(dirty.self.input==nil and dirty.self.buttons==nil and dirty.self.teleport==nil)
assert(dropped>=4,'hidden fields were not dropped: '..tostring(dropped))
assert(B.sanitize_obs({frame=0,bounds=BOUNDS(),self={x='no',y=0}})==nil,'invalid self accepted')
local r,host=charged_run('cinder','assault','direct_hit',3)
local m1=make_manager(r); assert(add_agent(m1))
local m2=make_manager(r); assert(add_agent(m2))
local n1,n2=0,0
for f=0,40 do
 local _,a=m1:tick(f,{enemy_test_1=obs({frame=f})})
 for _,e in ipairs(a.events) do if e.kind=='tell' then n1=n1+1 end end
 local _,b=m2:tick(f,{enemy_test_1=obs({frame=f,self=selfpose({input=f,buttons=3}),extra=1})})
 for _,e in ipairs(b.events) do if e.kind=='tell' then n2=n2+1 end end
end
assert(n1==n2 and n1>0,'hidden input changed the decision stream')
assert(m2.hidden_ignored>0,'hidden fields were not counted')
print('observation boundary: hidden input dropped and inert')
''')

    def test_visibility_predicate_requires_exact_true(self):
        _run(r'''
-- A configured predicate must return exactly true; nil and other truthy values
-- fail closed with no tell, no ability request and no private target history.
local function never_acts(val)
 local m=make_manager(charged_run('cinder','assault','direct_hit',3),{visible=function() return val end})
 assert(add_agent(m))
 local acting=false
 for f=0,40 do local _,o=m:tick(f,{enemy_test_1=obs({frame=f})}); if any_kind(o.events,'tell') or ability_req(o.requests) then acting=true end end
 local ag=m.by_id.enemy_test_1
 local n=0 for _ in pairs(ag.hist) do n=n+1 end
 return acting, n, ag.visible_now and ag.visible_now['player']
end
local bad=function(acting,n,vis,val)
 assert(not acting,'non-true predicate value granted a tell/attack: '..tostring(val))
 assert(n==0,'non-true predicate retained private target history')
 assert(vis~=true,'non-true predicate marked the target visible')
end
bad(never_acts(nil))
for _,val in ipairs({false,0,1,'yes',{},function() end}) do
 local acting,n,vis=never_acts(val)
 bad(acting,n,vis,val)
end
-- Exactly true grants visibility and a normal attack.
local mt=make_manager(charged_run('cinder','assault','direct_hit',3),{visible=function() return true end})
assert(add_agent(mt))
assert(drive_to_ability(mt,'enemy_test_1',function(f) return obs({frame=f}) end,60),'true predicate did not grant visibility')
-- An existing tell is cancelled when visibility changes true -> nil.
local grant=true
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r,{visible=function() return grant end}); assert(add_agent(m))
local t=drive_to_tell(m,'enemy_test_1',function(f) return obs({frame=f}) end,40)
assert(t,'no tell while visibility granted')
grant=false
local aborted,released=false,false
for f=t.frame+1,t.event.until_frame do
 local _,o=m:tick(f,{enemy_test_1=obs({frame=f})})
 local a=any_kind(o.events,'tell_abort'); if a then aborted=a end
 if ability_req(o.requests) then released=true end
end
assert(aborted and not released,'visibility true->nil did not cancel the tell')
print('visibility: exact-true predicate, fail closed, tell cancels on loss')
''')

    def test_malformed_observations_refuse_safely(self):
        _run(r'''
-- Direct sanitize: malformed inputs never raise and never admit invalid actors.
local ok0,o0=pcall(B.sanitize_obs,{targets={}})
assert(ok0 and o0==nil,'missing-self observation threw or was admitted')
local ok1,o1=pcall(B.sanitize_obs,{self='bad',targets={false}})
assert(ok1 and o1==nil,'non-table self observation threw or was admitted')
local ok2,o2=pcall(B.sanitize_obs,{self=selfpose({x=0/0})})
assert(ok2 and o2==nil,'non-finite self observation admitted')
local ok3,obs3,why3,dropped3=pcall(B.sanitize_obs,{self=selfpose(),targets={false,tgt({x='no'}),tgt()}})
assert(ok3 and obs3 and not why3,'mixed malformed targets did not resolve')
assert(#obs3.targets==1 and obs3.targets[1].id=='player','invalid targets admitted')
assert(dropped3>=1)
-- Public update path: malformed observation is refused, no history retained.
local m=make_manager(charged_run('cinder','assault','direct_hit',3)); assert(add_agent(m))
m:tick(0,{enemy_test_1=obs({frame=0})}) -- establishes history
assert(next(m.by_id.enemy_test_1.hist)~=nil)
local okT,ticked,oT=pcall(function() return m:tick(1,{enemy_test_1={self='bad',targets={false,nil}}}) end)
assert(okT and ticked)
assert(any_kind(oT.events,'observation_refused'))
assert(next(m.by_id.enemy_test_1.visible_now)==nil,'refused observation kept a visible target')
assert(next(m.by_id.enemy_test_1.hist)==nil,'refused observation retained invisible history')
-- Non-finite target coordinates are dropped, not admitted.
local _,oT2=m:tick(2,{enemy_test_1=obs({frame=2,targets={tgt({x=0/0}),tgt({id='p2',y=0/0})}})})
assert(m.by_id.enemy_test_1.visible_now['player']==nil and m.by_id.enemy_test_1.visible_now['p2']==nil,'invalid coordinates admitted')
local _,oMissing=m:tick(3,{enemy_test_1={self=selfpose()}})
assert(#oMissing.requests>=0) -- targets omitted entirely: safe, no throw
print('malformed observations: refused/dropped safely, no invalid actors')
''')

    def test_reaction_delay_vision_monotonic_and_reveal(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local saw=false
for f=0,40 do local _,o=m:tick(f,{enemy_test_1=obs({frame=f,targets={tgt({x=180})}})}); if any_kind(o.events,'tell') then saw=true end end
assert(not saw,'out-of-vision target produced a tell')
-- A target occluded until frame 10 only gets a reaction after first reveal.
local r2,h2=charged_run('cinder','assault','direct_hit',3)
local m2=make_manager(r2,{visible=function(a,t,s,f) return f>=10 end}); assert(add_agent(m2))
local first=nil
for f=0,40 do local _,o=m2:tick(f,{enemy_test_1=obs({frame=f})}); if any_kind(o.events,'tell') then first=f;break end end
assert(first and first>=15,'reveal reaction not delayed after reveal: '..tostring(first))
-- Monotonic decision time.
local m3=make_manager(charged_run('cinder','assault','direct_hit',3)); assert(add_agent(m3))
assert(m3:tick(41,{}))
local bad,reason=m3:tick(3,{})
assert(not bad and tostring(reason):find('monotonic',1,true))
print('observation: vision, reveal reaction and monotonic time enforced')
''')

    def test_core_legal_ability_requests_only(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local found=drive_to_ability(m,'enemy_test_1',function(f) return obs({frame=f}) end,60)
assert(found,'no ability request')
local req=found.request
assert(req.kind=='ability' and req.slot=='assault' and req.host==host and req.generation)
local a=C.ability(r,host,'assault')
assert(req.reach==a.reach and req.damage==a.damage,'request did not use real Core ability')
assert(req.move_id:match('^enemy_test_1#%d+:assault:%d+$'),'request lacks stable generation provenance')
-- Not ready: zero real charge means no tell or request ever.
local p=C.new_profile(7); local r2=C.new_run(p); local host2='enemy_test_1'
local id=assert(C.acquire(r2,'cinder')); assert(C.equip(r2,host2,'assault',id))
local m2=make_manager(r2); assert(add_agent(m2,{id='enemy_test_1'}))
local committed=false
for f=0,40 do local _,o=m2:tick(f,{enemy_test_1=obs({frame=f})}); if any_kind(o.events,'tell') or ability_req(o.requests) then committed=true end end
assert(not committed,'unready ability was requested (unearned charge)')
-- Dead or hit-stunned actors are ineligible to act.
local m3=make_manager(charged_run('cinder','assault','direct_hit',3)); assert(add_agent(m3))
local _,dead=m3:tick(0,{enemy_test_1=obs({frame=0,self=selfpose({alive=false})})})
assert(#dead.requests==0 and not any_kind(dead.events,'tell'))
local _,hurt=m3:tick(1,{enemy_test_1=obs({frame=1,self=selfpose({hitlag=4})})})
assert(#hurt.requests==0 and not any_kind(hurt.events,'tell'))
assert(m3:counters('enemy_test_1').ineligible>=2,'ineligible actions were not surfaced')
print('core legality: ready/reach/eligible only, generation provenance')
''')

    def test_ineligible_aborts_pending_tell(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local t=drive_to_tell(m,'enemy_test_1',function(f) return obs({frame=f}) end,40)
assert(t)
local _,o=m:tick(t.frame+1,{enemy_test_1=obs({frame=t.frame+1,self=selfpose({alive=false})})})
local abort=any_kind(o.events,'tell_abort')
assert(abort and abort.reason=='ineligible','death did not abort the advertised tell')
assert(#o.requests==0)
print('ineligible: death/hitlag cancels an advertised tell')
''')

    def test_tell_retains_target_and_slot(self):
        _run(r'''
-- Two targets; the advertised target is moved out of reach before release. The
-- tell must cancel, not silently switch to the other target.
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local tell,tell_frame
for f=0,40 do
 local _,o=m:tick(f,{enemy_test_1=obs({frame=f,targets={tgt({id='player',x=4}),tgt({id='player2',x=-4})}})})
 local e=any_kind(o.events,'tell'); if e then tell,tell_frame=e,f;break end
end
assert(tell and tell.target=='player' and tell.slot=='assault')
assert(tell.move_id and tell.generation)
local abort
for f=tell_frame+1,tell.until_frame do
 local _,o=m:tick(f,{enemy_test_1=obs({frame=f,targets={tgt({id='player',x=95}),tgt({id='player2',x=-4})}})})
 local a=any_kind(o.events,'tell_abort'); if a then abort=a end
 local q=ability_req(o.requests)
 assert(not q or q.target=='player','tell switched to another target: '..tostring(q and q.target))
end
assert(abort and abort.target=='player','out-of-reach advertised target was not cancelled')
print('tell retention: exact target/slot/instance or cancel')
''')

    def test_simultaneous_tell_arbiter(self):
        _run(r'''
local p=C.new_profile(99); local r=C.new_run(p)
for _,host in ipairs({'enemy_a','enemy_b'}) do local id=assert(C.acquire(r,'cinder')); assert(C.equip(r,host,'assault',id)) end
for _,host in ipairs({'enemy_a','enemy_b'}) do
 for i=1,3 do assert(C.on_event(r,{host=host,kind='direct_hit',move_id=host..':m'..i,lineage='direct'})) end
end
local m=make_manager(r,{max_simultaneous_tells=1,tell_gap=6})
assert(m:add({id='enemy_a',host='enemy_a',archetype='pressure',slot='assault',family='cinder',seed=1}))
assert(m:add({id='enemy_b',host='enemy_b',archetype='pressure',slot='assault',family='cinder',seed=2}))
local tells_by_frame={}
for f=0,60 do
 local _,o=m:tick(f,{['enemy_a']=obs({frame=f,self=selfpose({id='enemy_a'})}),
  ['enemy_b']=obs({frame=f,self=selfpose({id='enemy_b'})})})
 for _,e in ipairs(o.events) do if e.kind=='tell' then tells_by_frame[f]=(tells_by_frame[f] or 0)+1 end end
end
for f,n in pairs(tells_by_frame) do assert(n<=1,'simultaneous tells on frame '..f) end
local starts={} for f in pairs(tells_by_frame) do starts[#starts+1]=f end table.sort(starts)
for i=2,#starts do assert(starts[i]-starts[i-1]>=6,'tells not spaced for a response window') end
local c=m:counters()
assert(c.tells>=2 and c.deferred>0,'arbiter deferral and tells were not measured')
print('arbiter: no overlapping tells, mandatory response spacing')
''')

    def test_counters_separate_and_confirmed(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local found=drive_to_ability(m,'enemy_test_1',function(f) return obs({frame=f}) end,60)
assert(found)
local req=found.request
local before=m:counters(req.actor)
assert(before.ability.opportunities>=before.ability.requests and before.ability.successes==0,'success claimed without evidence')
assert(m:confirm(req.move_id,true),'confirmation refused')
local after=m:counters(req.actor)
assert(after.ability.successes==1,'confirmed success not counted')
assert(not m:confirm(req.move_id,true),'duplicate confirmation accepted')
local m2=make_manager(charged_run('cinder','assault','direct_hit',3)); assert(add_agent(m2))
for f=0,60 do m2:tick(f,{enemy_test_1=obs({frame=f})}) end
assert(m2:counters('enemy_test_1').ability.successes==0,'unconfirmed request counted as success')
print('counters: opportunities/requests/successes separate and measured')
''')

    def test_bounded_ownership_generation_and_cleanup(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r,{max_actors=1})
assert(add_agent(m,{id='enemy_a'}))
local second,why=m:add({id='enemy_b',archetype='pressure',host='x'})
assert(not second and tostring(why):find('budget',1,true),'actor budget ignored')
-- A live tell/request cannot be confirmed after the actor is removed and the
-- same stable id is re-added.
local found=drive_to_ability(m,'enemy_a',function(f) return obs({frame=f,self=selfpose({id='enemy_a'})}) end,60)
assert(found,'no request for generation test')
local old=found.request.move_id
assert(m:confirm(old,true))
local found2=drive_to_ability(m,'enemy_a',function(f) return obs({frame=f,self=selfpose({id='enemy_a'})}) end,120)
assert(found2)
local stale=found2.request.move_id
m:remove('enemy_a','escaped')
assert(add_agent(m,{id='enemy_a'})) -- new incarnation, new generation
assert(not m:confirm(stale,true),'stale confirmation crossed an incarnation')
assert(m:counters('enemy_a').ability.successes==0,'old success leaked to the new actor')
local _,e=m:remove('enemy_a','escaped')
assert(e.kind=='escaped' and e.escaped==true and e.defeated==false,'escape reported as defeat')
assert(m:release() and not m:has_live())
print('ownership: bounded, generation-safe, escaped != defeated, cleanup safe')
''')

    def test_room_aware_ledge_and_recovery(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m,{archetype='zone'}))
local _,o=m:tick(0,{enemy_test_1=obs({frame=0,
 self=selfpose({x=10,y=40,grounded=true}),
 targets={tgt({x=90,y=0,grounded=false})},
 terrain={ledges={{x=14,side='right'}}},
 bounds={min_x=-100,max_x=100,min_y=-200,max_y=40,center_x=0,floor_y=40}})})
assert(o.requests[1] and o.requests[1].kind=='move' and o.requests[1].dir==0,'ledge was not avoided')
local r2,h2=charged_run('cinder','assault','direct_hit',3)
local m2=make_manager(r2); assert(add_agent(m2,{archetype='aerial'}))
local _,o2=m2:tick(0,{enemy_test_1=obs({frame=0,
 self=selfpose({x=40,y=-90,on_stage=false,grounded=false,airborne=true})})})
local rec=o2.requests[1]
assert(rec and rec.kind=='recover' and rec.jump==true and rec.dir==-1 and rec.capability=='aerial','recovery request wrong')
assert(rec.teleport==nil)
print('navigation: ledge avoid and honest capability-tagged recovery')
''')

    def test_positioning_anchor_is_combat_movement(self):
        _run(r'''
-- Warden phase 3 demands the left wall; at x=50 with a near target the boss must
-- request movement toward the anchor, not stand still.
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r)
assert(Boss.attach(m,{id='boss1',host=host,family='cinder',level=8,seed=7},'warden'))
m.by_id.boss1.phase=3
local _,o=m:tick(0,{boss1=obs({frame=0,self=selfpose({id='boss1',x=50}),targets={tgt({x=54})}})})
local move=o.requests[1]
assert(move and move.kind=='move' and move.dir==-1,'anchor demand not requested: dir='..tostring(move and move.dir))
assert(move.capability=='grounded' and move.jump==false,'grounded capability not honest')
print('positioning: phase anchor drives bounded combat movement')
''')

    def test_determinism_same_seed(self):
        _run(r'''
local function stream(seed)
 local r,host=charged_run('cinder','assault','direct_hit',3)
 local m=make_manager(r,{seed=seed}); assert(add_agent(m,{archetype='elite',seed=seed}))
 local log={}
 for f=0,50 do
  local _,o=m:tick(f,{enemy_test_1=obs({frame=f})})
  for _,e in ipairs(o.events or {}) do log[#log+1]=e.kind..':'..tostring(e.slot) end
  for _,q in ipairs(o.requests or {}) do log[#log+1]='req:'..q.kind..':'..tostring(q.slot) end
 end
 return table.concat(log,',')
end
local a=stream(1234); local b=stream(1234)
assert(a==b and #a>0,'same seed produced a different decision stream')
print('determinism: identical seed yields identical decisions')
''')

    def test_callbacks_fail_closed_and_surface(self):
        _run(r'''
-- A thrown visibility predicate fails closed and is surfaced.
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r,{visible=function() error('boom') end}); assert(add_agent(m))
local saw=false
for f=0,30 do local _,o=m:tick(f,{enemy_test_1=obs({frame=f})}); if any_kind(o.events,'tell') then saw=true end end
assert(not saw,'thrown visible callback failed open')
assert(m:counters().surfaced>=1,'thrown callback was not surfaced')
-- A denying permission surfaces and leaves no confirmable request.
local m2=make_manager(charged_run('cinder','assault','direct_hit',3),{permission=function() return false end})
assert(add_agent(m2))
local denied
for f=0,80 do local _,o=m2:tick(f,{enemy_test_1=obs({frame=f})}); local q=ability_req(o.requests); if q then denied=q end end
assert(denied and denied.refused==true,'permission denial not surfaced on the request')
assert(m2:counters().denied>=1 and not m2:confirm(denied.move_id,true),'denied request stayed actionable')
-- A failed submit is surfaced and not confirmable.
local m3=make_manager(charged_run('cinder','assault','direct_hit',3),{actions={submit=function() return false,'no slot' end}})
assert(add_agent(m3))
local failed
for f=0,80 do local _,o=m3:tick(f,{enemy_test_1=obs({frame=f})}); local q=ability_req(o.requests); if q then failed=q end end
assert(failed and failed.failed==true,'failed submit not surfaced')
assert(m3:counters().failed>=1 and not m3:confirm(failed.move_id,true),'failed request stayed actionable')
print('callbacks: fail closed, surfaced, never silently actionable')
''')

    def test_optional_gene_actions_callback(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local saw=drive_to_ability(m,'enemy_test_1',function(f) return obs({frame=f}) end,60)
assert(saw,'no request without actions callback')
local submitted=0
local r2,h2=charged_run('cinder','assault','direct_hit',3)
local m2=make_manager(r2,{actions={available=function() return false end,submit=function() submitted=submitted+1 end}})
assert(add_agent(m2))
local refused
for f=0,60 do local _,o=m2:tick(f,{enemy_test_1=obs({frame=f})}); local q=ability_req(o.requests); if q then refused=q end end
assert(refused and refused.refused==true,'actions.available refusal not surfaced')
assert(m2:counters().refused>=1 and submitted==0,'refusal still submitted')
print('gene_actions callback: optional, explicit and non-fabricating')
''')

    def test_module_does_not_mutate_run(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local before=assert(C.snapshot(r))
local m=make_manager(r); assert(add_agent(m,{archetype='elite'}))
local req
for f=0,80 do local _,o=m:tick(f,{enemy_test_1=obs({frame=f})}); req=ability_req(o.requests) or req end
assert(C.snapshot(r)==before,'decision layer mutated the run')
if req then assert(req.teleport==nil and req.charge==nil) end
print('isolation: run state unchanged; no teleport/charge fabrication')
''')

    def test_boss_mechanics_not_schema(self):
        _run(r'''
-- Each controller's transitions must change authored mechanics, not just fields.
local function attach(controller,family)
 local r,host=charged_run(family,'assault',family=='rime' and 'direct_hit' or 'direct_hit',3)
 local m=make_manager(r)
 assert(Boss.attach(m,{id='boss1',host=host,family=family,level=8,seed=7},controller))
 return m,host
end
-- Warden: KO advances measure(spacing,tell20) -> advance(advance,tell16,dual slots).
local m,h=attach('warden','cinder')
local p1=Boss.state(m,'boss1',0)
local _,o1=m:tick(0,{boss1=obs({frame=0,self=selfpose({id='boss1',kos=0})})})
local _,o2=m:tick(1,{boss1=obs({frame=1,self=selfpose({id='boss1',kos=1})})})
local ph=any_kind(o2.events,'phase'); assert(ph and ph.phase==2)
local p2=Boss.state(m,'boss1',1)
assert(p1.motion~=p2.motion and p1.tell_frames~=p2.tell_frames,'warden phase mechanics unchanged')
assert(#Boss.controllers.warden.phases[1].attack_slots~=#Boss.controllers.warden.phases[2].attack_slots,'warden slots unchanged')
-- Glacier: measured hits advance hold -> advance with a longer recovery.
local gm,gh=attach('glacier','rime')
local _,go=gm:tick(0,{boss1=obs({frame=0,self=selfpose({id='boss1',hits_taken=0})})})
local _,go2=gm:tick(1,{boss1=obs({frame=1,self=selfpose({id='boss1',hits_taken=2})})})
local gph=any_kind(go2.events,'phase'); assert(gph and gph.phase==2)
local g2=Boss.state(gm,'boss1',1)
assert(g2.motion=='advance' and g2.recovery_frames==26,'glacier phase mechanics unchanged')
-- Tempest: visible offstage advances aerial circle -> aerial dive with a longer recovery.
local tm,th=attach('tempest','rime')
local _,to=tm:tick(0,{boss1=obs({frame=0,self=selfpose({id='boss1'}),targets={tgt({offstage=true,x=4})}})})
local tph
for f=1,30 do
 local _,oo=tm:tick(f,{boss1=obs({frame=f,self=selfpose({id='boss1'}),targets={tgt({offstage=true,x=4})}})})
 tph=any_kind(oo.events,'phase') or tph
end
assert(tph and tph.phase==2,'tempest did not advance on a visible offstage target')
local t2=Boss.state(tm,'boss1',30)
assert(t2.tell_frames==14 and t2.recovery_frames==22,'tempest phase mechanics unchanged')
print('boss mechanics: authored transitions change real behaviour')
''')

    def test_boss_phase_inputs_are_delayed_and_visible(self):
        _run(r'''
-- An occluded offstage target must not drive a Tempest transition at frame 0.
local r,host=charged_run('rime','assault','direct_hit',3)
local m=make_manager(r)
assert(Boss.attach(m,{id='boss1',host=host,family='rime',level=8,seed=7},'tempest'))
local _,o=m:tick(0,{boss1=obs({frame=0,self=selfpose({id='boss1'}),targets={tgt({offstage=true,x=999})}})})
assert(not any_kind(o.events,'phase'),'occluded offstage target drove a phase transition')
assert(Boss.state(m,'boss1',0).phase==1)
print('boss phase inputs: delayed and visibility-filtered')
''')

    def test_visibility_loss_invalidates_history(self):
        _run(r'''
-- Visible through frame 10, occluded since 11. Old stale history must not let
-- the actor attack at frame 197.
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r,{visible=function(a,t,s,f) return f<=10 end}); assert(add_agent(m))
local attacked=false
for f=0,197 do
 local _,o=m:tick(f,{enemy_test_1=obs({frame=f})})
 if ability_req(o.requests) then attacked=true end
end
assert(not attacked,'stale occluded history still attacked at 197')
assert(m:counters('enemy_test_1').ability.requests==0)
-- A tell that starts while visible must abort once line of sight is lost.
local r2,h2=charged_run('cinder','assault','direct_hit',3)
local m2=make_manager(r2,{visible=function(a,t,s,f) return f<8 end}); assert(add_agent(m2))
local t=drive_to_tell(m2,'enemy_test_1',function(f) return obs({frame=f}) end,8)
assert(t,'no tell while visible')
local aborted=false
for f=t.frame+1,t.event.until_frame do
 local _,o=m2:tick(f,{enemy_test_1=obs({frame=f})})
 if any_kind(o.events,'tell_abort') then aborted=true end
 assert(not ability_req(o.requests),'LOS loss still released an attack')
end
assert(aborted,'LOS failure did not invalidate existing history')
print('visibility loss: stale history invalidated, tell aborts')
''')

    def test_boss_vulnerability_windows(self):
        _run(r'''
-- Warden opens a recovery window after a committed attack.
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(Boss.attach(m,{id='boss1',host=host,family='cinder',level=8,seed=7},'warden'))
local found=drive_to_ability(m,'boss1',function(f) return obs({frame=f,self=selfpose({id='boss1',kos=0})}) end,80)
assert(found,'warden never attacked')
local vs=Boss.state(m,'boss1',found.frame)
assert(vs.vulnerable==true and vs.vulnerable_reason=='recovery','warden recovery window missing')
-- The window is bounded and expires.
assert(Boss.state(m,'boss1',found.frame+18).vulnerable==false,'warden recovery window did not expire')
-- Glacier on_recovery must open after a successful attack, not only a tell abort.
local gr,gh=charged_run('rime','assault','direct_hit',3)
local gm=make_manager(gr); assert(Boss.attach(gm,{id='boss1',host=gh,family='rime',level=8,seed=7},'glacier'))
local gfound=drive_to_ability(gm,'boss1',function(f) return obs({frame=f,self=selfpose({id='boss1'})}) end,90)
assert(gfound,'glacier never attacked')
local gvs=Boss.state(gm,'boss1',gfound.frame)
assert(gvs.vulnerable==true and gvs.vulnerable_reason=='recovery','glacier successful-attack recovery stayed invulnerable')
assert(Boss.state(gm,'boss1',gfound.frame+16).vulnerable==false,'glacier window did not expire')
print('boss vulnerability: committed attacks open bounded recovery windows')
''')

    def test_movement_is_not_recovery_vulnerability(self):
        _run(r'''
-- An uncharged boss that only patrols/moves must never be "recovering".
local p=C.new_profile(55); local r=C.new_run(p); local host='enemy_test_1'
local id=assert(C.acquire(r,'rime')); assert(C.equip(r,host,'assault',id)) -- no charge
local m=make_manager(r); assert(Boss.attach(m,{id='boss1',host=host,family='rime',level=8,seed=7},'glacier'))
local vuln_events=0; local move_requests=0
for f=0,120 do
 local _,o=m:tick(f,{boss1=obs({frame=f,self=selfpose({id='boss1'})})})
 if any_kind(o.events,'vulnerable') then vuln_events=vuln_events+1 end
 for _,q in ipairs(o.requests) do if q.kind=='move' then move_requests=move_requests+1 end end
end
assert(move_requests>0,'uncharged boss never moved')
assert(vuln_events==0,'movement opened a recovery/vulnerability window')
assert(Boss.state(m,'boss1',120).vulnerable==false)
print('movement: patrol is not recovery and never opens vulnerability')
''')

    def test_nil_callback_seams_fail_closed(self):
        _run(r'''
-- A configured callback must return exactly true; nil is a denial/failure.
local function drive(m)
 local last
 for f=0,80 do local _,o=m:tick(f,{enemy_test_1=obs({frame=f})}); last=ability_req(o.requests) or last end
 return last
end
local m=make_manager(charged_run('cinder','assault','direct_hit',3),{permission=function() return nil end})
assert(add_agent(m))
local req=drive(m)
assert(req and req.refused==true,'nil permission not denied')
assert(m:counters().denied>=1 and not m:confirm(req.move_id,true),'nil permission left a confirmable request')
local m2=make_manager(charged_run('cinder','assault','direct_hit',3),{actions={available=function() return nil end}})
assert(add_agent(m2))
local req2=drive(m2)
assert(req2 and req2.refused==true,'nil availability not refused')
assert(not m2:confirm(req2.move_id,true),'nil availability left a confirmable request')
local m3=make_manager(charged_run('cinder','assault','direct_hit',3),{actions={submit=function() return nil end}})
assert(add_agent(m3))
local req3=drive(m3)
assert(req3 and req3.failed==true,'nil submit not failed')
assert(m3:counters().failed>=1 and not m3:confirm(req3.move_id,true),'nil submit left a confirmable request')
print('callbacks: exact-true protocol, nil fails closed')
''')

    def test_tell_binds_gene_instance(self):
        _run(r'''
-- The tell binds the Cinder gene instance; swapping in a charged Rime after the
-- tell must cancel without spending, not release the new family.
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local t=drive_to_tell(m,'enemy_test_1',function(f) return obs({frame=f}) end,40)
assert(t and t.event.gene,'tell did not advertise a gene instance')
local advertised=t.event.gene
-- Replace the equipped gene with a different, fully charged family.
assert(C.equip(r,host,'assault',nil))
local rime=assert(C.acquire(r,'rime')); assert(C.equip(r,host,'assault',rime))
for i=1,3 do assert(C.on_event(r,{host=host,kind='direct_hit',move_id=host..':rime'..i,lineage='direct'})) end
assert(C.ability(r,host,'assault').ready)
local aborted,released=false,false
for f=t.frame+1,t.event.until_frame do
 local _,o=m:tick(f,{enemy_test_1=obs({frame=f})})
 local a=any_kind(o.events,'tell_abort'); if a then aborted=a end
 if ability_req(o.requests) then released=true end
end
assert(aborted and aborted.reason=='gene_changed','gene swap was not cancelled')
assert(not released,'tell released the replacement gene instance')
assert(C.ability(r,host,'assault').charge==3,'cancelled tell spent the replacement charge')
print('tell gene binding: exact instance or cancel without spend')
''')

    def test_tell_binds_owned_run_table(self):
        _run(r'''
-- Two profiles both produce textual run1 with a gene r4. The tell must bind the
-- exact owned run TABLE, not the reused strings.
local holder={}
local r1=charged_run_for(4242,'enemy_test_1','cinder')
holder.run=r1
local m=make_holder_manager(holder); assert(add_agent(m))
local t=drive_to_tell(m,'enemy_test_1',function(f) return obs({frame=f}) end,40)
assert(t)
local r2=charged_run_for(777,'enemy_test_1','rime')
assert(r2.id=='run1' and r2.genes['r4'] and r2.genes['r4'].kind=='rime','test setup: expected textual collision')
holder.run=r2 -- same 'run1'/'r4' strings, different tables
local aborted,released=false,false
for f=t.frame+1,t.event.until_frame do
 local _,o=m:tick(f,{enemy_test_1=obs({frame=f})})
 local a=any_kind(o.events,'tell_abort'); if a then aborted=a end
 if ability_req(o.requests) then released=true end
end
assert(aborted and aborted.reason=='run_changed','foreign run table with matching ids not detected')
assert(not released,'release fired against a foreign run')
print('tell run binding: exact owned run table, not textual run1')
''')

    def test_tell_binds_reconstructed_run_instance(self):
        _run(r'''
-- The same profile's run reconstructed from a snapshot has identical ids but a
-- different table; it must not satisfy the tell.
local holder={}
local r1=charged_run_for(4242,'enemy_test_1','cinder')
holder.run=r1
local m=make_holder_manager(holder); assert(add_agent(m))
local t=drive_to_tell(m,'enemy_test_1',function(f) return obs({frame=f}) end,40)
assert(t)
local restored=assert(C.restore(assert(C.snapshot(r1))))
assert(restored~=r1 and restored.id==r1.id and restored.genes['r4'],'snapshot should reconstruct equal ids')
holder.run=restored
local aborted,released=false,false
for f=t.frame+1,t.event.until_frame do
 local _,o=m:tick(f,{enemy_test_1=obs({frame=f})})
 local a=any_kind(o.events,'tell_abort'); if a then aborted=a end
 if ability_req(o.requests) then released=true end
end
assert(aborted and aborted.reason=='run_changed','reconstructed run instance accepted')
assert(not released,'release fired against a reconstructed run')
print('tell run binding: reconstructed run instance rejected')
''')

    def test_tell_rejects_reused_gene_id(self):
        _run(r'''
-- A different gene table that reuses the same id string ('r4') must cancel.
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local t=drive_to_tell(m,'enemy_test_1',function(f) return obs({frame=f}) end,40)
assert(t)
local original=r.genes['r4']
r.genes['r4']=clone(original) -- same id, same kind/action, new table identity
local aborted,released=false,false
for f=t.frame+1,t.event.until_frame do
 local _,o=m:tick(f,{enemy_test_1=obs({frame=f})})
 local a=any_kind(o.events,'tell_abort'); if a then aborted=a end
 if ability_req(o.requests) then released=true end
end
assert(aborted and aborted.reason=='gene_changed','reused gene id accepted')
assert(not released,'release fired against a same-id different gene table')
r.genes['r4']=original
print('tell gene binding: reused id rejected by table identity')
''')

    def test_tell_state_drift_cancels(self):
        _run(r'''
-- Reinitialising the host slot state table (same gene, same charge) is drift and
-- must cancel without spending.
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local t=drive_to_tell(m,'enemy_test_1',function(f) return obs({frame=f}) end,40)
assert(t)
r.hosts[host].state.assault={charge=3,ready_at=0,seen={}}
local aborted,released=false,false
for f=t.frame+1,t.event.until_frame do
 local _,o=m:tick(f,{enemy_test_1=obs({frame=f})})
 local a=any_kind(o.events,'tell_abort'); if a then aborted=a end
 if ability_req(o.requests) then released=true end
end
assert(aborted and aborted.reason=='state_changed','host slot state drift accepted')
assert(not released,'release fired after slot state drift')
assert(C.ability(r,host,'assault').charge==3,'drift cancelled with a spend')
print('tell state binding: host slot state drift cancels without spend')
''')

    def test_boss_defeat_lifecycle_and_addon_binding(self):
        _run(r'''
local owner=Boss.owner_key('p4242','run1')
assert(owner=='p4242/run1')
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(Boss.attach(m,{id='boss1',host=host,family='cinder',level=8,seed=7},'warden'))
m:tick(0,{boss1=obs({frame=0,self=selfpose({id='boss1',kos=0})})})
local addon=Boss.progress_new(owner,'run1',1)
local ctx={owner=owner,run_id='run1',generation=1}
assert(Boss.progress_sync(addon,'champ_cinder',m,'boss1',5,ctx))
assert(Boss.progress_validate(addon))
assert(not Boss.progress_reward_eligible(addon,'champ_cinder',ctx),'reward before completion')
local ok,ev=Boss.defeat(m,addon,'champ_cinder','boss1',6,ctx)
assert(ok and ev.kind=='defeat','boss defeat lifecycle failed')
assert(m.by_id.boss1==nil,'boss agent survived defeat')
assert(addon.bosses.champ_cinder.completed==true)
assert(Boss.progress_reward_eligible(addon,'champ_cinder',ctx))
assert(Boss.progress_claim_reward(addon,'champ_cinder',ctx))
local again,why=Boss.progress_claim_reward(addon,'champ_cinder',ctx)
assert(not again and tostring(why):find('already',1,true),'duplicate reward allowed')
-- Same textual run id from another profile lineage cannot claim.
local foreign=Boss.progress_new(Boss.owner_key('p7','run1'),'run1',1)
assert(Boss.progress_validate(foreign))
local fctx={owner=Boss.owner_key('p7','run1'),run_id='run1',generation=1}
foreign.bosses.champ_cinder=clone(addon.bosses.champ_cinder)
assert(not Boss.progress_reward_eligible(foreign,'champ_cinder',ctx),'foreign profile matched by run id')
local fe,why2=Boss.progress_claim_reward(foreign,'champ_cinder',ctx)
assert(not fe and tostring(why2):find('owner mismatch',1,true),'foreign owner accepted')
local text=assert(Boss.progress_encode(addon,Codec))
local decoded=assert(Boss.progress_decode(text,Codec))
assert(decoded.owner==owner and decoded.run_id=='run1' and decoded.generation==1 and decoded.bosses.champ_cinder.rewarded==true)
print('boss lifecycle: defeat completes, owner-bound addon, no foreign/duplicate reward')
''')

    def test_boss_resume_binding_and_phase(self):
        _run(r'''
local entry={controller='warden',family='cinder',phase=2,phase_frames=123,kos=1,hits=2,completed=true,rewarded=false}
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r)
local bad,why=Boss.resume(m,{id='boss1',host=host,family='cinder',level=8,seed=3},'glacier',entry)
assert(not bad and tostring(why):find('mismatch',1,true),'Glacier adopted a Warden record')
-- A matching resume restores phase, elapsed phase time and completion, but a
-- completed boss is inert: it never requests or attacks.
local m2=make_manager(charged_run('cinder','assault','direct_hit',3))
assert(Boss.resume(m2,{id='boss1',host=host,family='cinder',level=8,seed=3},'warden',entry))
assert(m2.by_id.boss1.phase==2 and m2.by_id.boss1.completed==true)
local retired,requests=0,0
for f=200,240 do
 local _,o=m2:tick(f,{boss1=obs({frame=f,self=selfpose({id='boss1',kos=1})})})
 if any_kind(o.events,'retired') then retired=retired+1 end
 requests=requests+#o.requests
end
assert(retired==1,'completed resume did not report retirement once')
assert(requests==0,'completed resumed boss acted')
local s=Boss.state(m2,'boss1',200)
assert(s.phase_frames==123,'resume discarded elapsed phase time')
assert(s.completed==true,'resume discarded completion')
local badentry=clone(entry); badentry.phase=99
assert(not Boss.progress_validate_entry(badentry),'out-of-range phase accepted')
badentry=clone(entry); badentry.bogus=1
assert(not Boss.progress_validate_entry(badentry),'unknown field accepted')
print('boss resume: controller-bound, preserves state, completed actor inert')
''')

    def test_boss_three_controllers_distinct_mechanics(self):
        _run(r'''
local seen={}
for id,c in pairs(Boss.controllers) do seen[id]={phases=#c.phases,family=c.family,host=c.host}; assert(#c.phases>=3) end
assert(seen.warden and seen.glacier and seen.tempest)
local wa=Boss.controllers.warden.phases[1]
local gl=Boss.controllers.glacier.phases[1]
local te=Boss.controllers.tempest.phases[1]
assert(wa.positioning.anchor~=gl.positioning.anchor or wa.positioning.demand~=gl.positioning.demand)
assert(te.motion=='aerial' and gl.motion=='hold' and wa.motion=='spacing')
print('boss controllers: three distinct phase/positioning/vulnerability machines')
''')

    def test_contract_doc_exists(self):
        path = ROOT / 'docs/ENEMY-BEHAVIOR-CONTRACT.md'
        self.assertTrue(path.is_file(), 'contract document missing')
        text = path.read_text()
        for needle in ('observation', 'reaction', 'request', 'boss', 'progress addon',
                       'archetype', 'composition', 'callback', 'generation', 'eligible',
                       'visible', 'adapter'):
            self.assertIn(needle.lower(), text.lower())


if __name__ == '__main__':
    main()
