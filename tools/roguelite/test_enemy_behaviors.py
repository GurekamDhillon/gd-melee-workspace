#!/usr/bin/env python3
"""Actual-Lua enemy/boss behaviour invariants; engine stubs, not a playtest.

Loads the real Core, catalogues, Codec and the new encounter/boss behaviour
modules, then drives the pure observation -> decision -> legal-request boundary
with injected observations. It proves the authored archetypes/compositions, the
six-archetype and twelve-composition targets, three distinct boss controllers,
reaction-delayed fairness, Core-legal ability requests, the simultaneous-tell
arbiter, separated measured counters, determinism, bounded ownership, escape
not-defeat, room-aware ledge/recovery and the boss progress addon. It does not
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

-- Real Core run with a charged enemy gene host; charge comes from real direct
-- events, not a scripted percentage or a hidden grant.
local function charged_run(family,slot,trigger,n)
 local p=C.new_profile(4242); local r=C.new_run(p)
 local host='enemy_test_1'
 local id=assert(C.acquire(r,family)); assert(C.equip(r,host,slot,id))
 for i=1,(n or 3) do assert(C.on_event(r,{host=host,kind=trigger or 'direct_hit',move_id=host..':m'..i,lineage='direct'})) end
 return r,host,id
end

local BOUNDS=function() return {min_x=-100,max_x=100,min_y=-40,max_y=40,center_x=0,floor_y=40} end
local function selfpose(over)
 local s={id='enemy_test_1',x=0,y=0,vx=0,vy=0,facing=1,grounded=true,airborne=false,on_stage=true,hitlag=0,action=14,kos=0,hits_taken=0}
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
  visible=over.visible,actions=over.actions},
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
    def test_catalogue_targets_and_real_contracts(self):
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
print('catalogue: 6 archetypes, 12 compositions, 3 bosses validated')
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

    def test_reaction_delay_vision_and_monotonic_time(self):
        _run(r'''
-- Out-of-vision target: no tell even though ready and in reach.
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local saw=false
for f=0,40 do local _,o=m:tick(f,{enemy_test_1=obs({frame=f,targets={tgt({x=180})}})}); if any_kind(o.events,'tell') then saw=true end end
assert(not saw,'out-of-vision target produced a tell')
-- Reaction delay: a newly visible target cannot be acted on immediately.
local r2,h2=charged_run('cinder','assault','direct_hit',3)
local m2=make_manager(r2); assert(add_agent(m2))
local first=nil
for f=0,30 do local _,o=m2:tick(f,{enemy_test_1=obs({frame=f})}); if any_kind(o.events,'tell') then first=f;break end end
assert(first and first>=5,'reaction delay not honoured: first tell at '..tostring(first))
-- Occlusion hides a normally visible target.
local r3,h3=charged_run('cinder','assault','direct_hit',3)
local m3=make_manager(r3,{visible=function() return false end}); assert(add_agent(m3))
local occluded=false
for f=0,40 do local _,o=m3:tick(f,{enemy_test_1=obs({frame=f})}); if any_kind(o.events,'tell') then occluded=true end end
assert(not occluded,'occluded target produced a tell')
-- Decision time is monotonic.
assert(m3:tick(41,{}))
local bad,reason=m3:tick(3,{})
assert(not bad and tostring(reason):find('monotonic',1,true))
print('observation: reaction delay, vision/occlusion and monotonic time enforced')
''')

    def test_core_legal_ability_requests_only(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local req
for f=0,40 do local _,o=m:tick(f,{enemy_test_1=obs({frame=f})}); req=ability_req(o.requests); if req then break end end
assert(req and req.kind=='ability' and req.slot=='assault' and req.host==host)
local a=C.ability(r,host,'assault')
assert(req.reach==a.reach and req.damage==a.damage,'request did not use real Core ability')
assert(req.move_id:match('^enemy_test_1:assault:%d+$'),'request lacks stable provenance')
-- Not ready: charge from real events is zero, so no tell or request.
local p=C.new_profile(7); local r2=C.new_run(p); local host2='enemy_test_1'
local id=assert(C.acquire(r2,'cinder')); assert(C.equip(r2,host2,'assault',id))
local m2=make_manager(r2); assert(add_agent(m2,{id='enemy_test_1'}))
local committed=false
for f=0,40 do local _,o=m2:tick(f,{enemy_test_1=obs({frame=f})}); if any_kind(o.events,'tell') or ability_req(o.requests) then committed=true end end
assert(not committed,'unready ability was requested (unearned charge)')
-- Out of reach: visible but too far, no tell.
local r3,h3=charged_run('cinder','assault','direct_hit',3)
local m3=make_manager(r3); assert(add_agent(m3))
local far=false
for f=0,40 do local _,o=m3:tick(f,{enemy_test_1=obs({frame=f,targets={tgt({x=50})}})}); if any_kind(o.events,'tell') then far=true end end
assert(not far,'out-of-reach ability was requested')
print('core legality: ready/reach/committed only, stable provenance')
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
local req
for f=0,60 do local _,o=m:tick(f,{enemy_test_1=obs({frame=f})}); req=ability_req(o.requests); if req then break end end
assert(req,'no request produced')
local before=m:counters(req.actor)
assert(before.ability.opportunities>=before.ability.requests and before.ability.successes==0,'success claimed without evidence')
assert(m:confirm(req.move_id,true),'confirmation refused')
local after=m:counters(req.actor)
assert(after.ability.successes==1,'confirmed success not counted')
assert(after.requests==before.requests,'confirmation changed the request count')
assert(not m:confirm(req.move_id,true),'duplicate confirmation accepted')
-- A request that is never confirmed leaves successes at zero.
local m2=make_manager(charged_run('cinder','assault','direct_hit',3)); assert(add_agent(m2))
for f=0,60 do m2:tick(f,{enemy_test_1=obs({frame=f})}) end
assert(m2:counters('enemy_test_1').ability.successes==0,'unconfirmed request counted as success')
print('counters: opportunities/requests/successes separate and measured')
''')

    def test_bounded_ownership_escape_and_cleanup(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r,{max_actors=1})
assert(add_agent(m,{id='enemy_a'}))
local second,why=m:add({id='enemy_b',archetype='pressure',host='x'})
assert(not second and tostring(why):find('budget',1,true),'actor budget ignored')
local _,e=m:remove('enemy_a','escaped')
assert(e.kind=='escaped' and e.escaped==true and e.defeated==false,'escape reported as defeat')
assert(not m:has_live())
assert(add_agent(m,{id='enemy_a'}))
local _,d=m:remove('enemy_a','defeated')
assert(d.kind=='defeat' and d.defeated==true and d.escaped==false)
assert(add_agent(m,{id='enemy_a'}))
local removed=m:release()
assert(#removed==1 and not m:has_live() and m:count()==0)
print('ownership: bounded, escaped != defeated, cleanup safe')
''')

    def test_room_aware_ledge_and_recovery(self):
        _run(r'''
-- A grounded actor stops before walking off a ledge.
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m,{archetype='zone'}))
local _,o=m:tick(0,{enemy_test_1=obs({frame=0,
 self=selfpose({x=10,y=40,grounded=true}),
 targets={tgt({x=90,y=0,grounded=false})},
 terrain={ledges={{x=14,side='right'}}},
 bounds={min_x=-100,max_x=100,min_y=-200,max_y=40,center_x=0,floor_y=40}})})
assert(#o.requests>=1 and o.requests[1].kind=='move' and o.requests[1].dir==0,'ledge was not avoided')
-- An off-stage actor asks for a legal recovery toward centre, never a teleport.
local r2,h2=charged_run('cinder','assault','direct_hit',3)
local m2=make_manager(r2); assert(add_agent(m2,{archetype='aerial'}))
local _,o2=m2:tick(0,{enemy_test_1=obs({frame=0,
 self=selfpose({x=40,y=-90,on_stage=false,grounded=false,airborne=true})})})
local rec=o2.requests[1]
assert(rec and rec.kind=='recover' and rec.jump==true and rec.dir==-1,'recovery request wrong')
assert(rec.teleport==nil)
local c=m2:counters('enemy_test_1')
assert(c.recovery.opportunities>=1 and c.recovery.requests>=1)
print('navigation: ledge avoid and recovery request are legal and bounded')
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
  for _,q in ipairs(o.requests or {}) do log[#log+1]='req:'..tostring(q.slot) end
 end
 return table.concat(log,',')
end
local a=stream(1234); local b=stream(1234)
assert(a==b and #a>0,'same seed produced a different decision stream')
print('determinism: identical seed yields identical decisions')
''')

    def test_optional_gene_actions_callback(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(add_agent(m))
local saw
for f=0,40 do local _,o=m:tick(f,{enemy_test_1=obs({frame=f})}); saw=ability_req(o.requests) or saw end
assert(saw,'no request without actions callback')
local submitted=0
local r2,h2=charged_run('cinder','assault','direct_hit',3)
local m2=make_manager(r2,{actions={available=function() return false end,submit=function() submitted=submitted+1 end}})
assert(add_agent(m2))
local refused
for f=0,40 do local _,o=m2:tick(f,{enemy_test_1=obs({frame=f})}); refused=ability_req(o.requests) or refused end
assert(refused and refused.refused==true,'actions.available refusal not surfaced')
assert(m2:counters().refused>=1 and submitted==0,'refusal still submitted')
print('gene_actions callback: optional, explicit and non-fabricating')
''')

    def test_boss_phases_timing_and_vulnerability(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r)
assert(Boss.attach(m,{id='boss1',host=host,family='cinder',level=8,seed=7},'warden'))
local s=Boss.state(m,'boss1',0)
assert(s.phase==1 and s.phase_id=='measure' and s.phases==3)
local _,o=m:tick(0,{boss1=obs({frame=0,self=selfpose({kos=0})})})
assert(not any_kind(o.events,'phase'))
local _,o1=m:tick(1,{boss1=obs({frame=1,self=selfpose({kos=1})})})
local ph=any_kind(o1.events,'phase'); assert(ph and ph.phase==2 and ph.phase_id=='advance')
local s2=Boss.state(m,'boss1',1)
assert(s2.motion=='advance' and s2.tell_frames==16 and s2.recovery_frames==16,'phase did not change mechanics')
-- A committed attack opens a real vulnerability window during recovery.
local req,f_at
for f=2,60 do
 local _,of=m:tick(f,{boss1=obs({frame=f,self=selfpose({kos=1})})})
 if ability_req(of.requests) then req=ability_req(of.requests);f_at=f;break end
end
assert(req and req.kind=='ability','boss never produced a legal ability request')
local vs=Boss.state(m,'boss1',f_at)
assert(vs.vulnerable==true and vs.vulnerable_reason=='recovery','recovery vulnerability window missing')
print('boss phases: observed transitions, distinct timing, vulnerability window')
''')

    def test_boss_attack_choices_and_addon_resume(self):
        _run(r'''
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r); assert(Boss.attach(m,{id='boss1',host=host,family='cinder',level=8,seed=3},'warden'))
m.by_id.boss1.phase=2
local _,o=m:tick(0,{boss1=obs({frame=0,self=selfpose({kos=1})})})
assert(Boss.state(m,'boss1',0).motion=='advance')
local addon=Boss.progress_new()
m.by_id.boss1.completed=true
assert(Boss.progress_sync(addon,'champ_cinder',m,'boss1',50))
assert(Boss.progress_validate(addon))
assert(Boss.progress_phase(addon,'champ_cinder')==m.by_id.boss1.phase)
assert(Boss.progress_reward_eligible(addon,'champ_cinder'))
assert(Boss.progress_claim_reward(addon,'champ_cinder'))
assert(not Boss.progress_reward_eligible(addon,'champ_cinder'))
local again,why=Boss.progress_claim_reward(addon,'champ_cinder')
assert(not again and tostring(why):find('already',1,true),'duplicate reward allowed')
local text=assert(Boss.progress_encode(addon,Codec))
local decoded=assert(Boss.progress_decode(text,Codec))
assert(decoded.bosses.champ_cinder.rewarded==true)
local bad=clone(decoded); bad.bosses.champ_cinder.phase=99
assert(not Boss.progress_validate(bad),'out-of-range phase accepted')
bad=clone(decoded); bad.bosses.champ_cinder.bogus=1
assert(not Boss.progress_validate(bad),'unknown field accepted')
local r2,h2=charged_run('cinder','assault','direct_hit',3)
local m2=make_manager(r2)
assert(Boss.resume(m2,{id='boss1',host=h2,family='cinder',level=8,seed=3},'warden',decoded.bosses.champ_cinder))
assert(m2.by_id.boss1.phase==decoded.bosses.champ_cinder.phase,'resume lost the phase')
local sigs={} for id,c in pairs(Boss.controllers) do sigs[c.signature]=true end
assert(count(sigs)==3,'boss signatures not distinct')
print('boss choices and addon: deterministic, resumable, no duplicate reward')
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
                       'archetype', 'composition', 'callback', 'pending'):
            self.assertIn(needle.lower(), text.lower())


if __name__ == '__main__':
    main()
