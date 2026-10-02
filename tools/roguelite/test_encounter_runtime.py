#!/usr/bin/env python3
"""Actual Lua encounter-orchestrator invariants; engine stubs, not a playtest.

Loads the real core, catalogues, EnemyGenes, TechAI and progress modules plus
the new runtime orchestrator, and drives it through saved resolved fixture
specs with an injected gd boundary. It verifies supported scheduling, refusal
and rollback, stable-id defeat evidence, respawn/error policy, stock/wave
continuation, partial resume, gene-host buffs and bounded cleanup. It does not
establish native combat, visuals or normal-speed gameplay.
"""
from pathlib import Path
import shutil
import subprocess
from unittest import TestCase, main
import game_source

ROOT = Path(__file__).resolve().parents[2]
RT = game_source.ROGUELITE
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

MODULES = [RT / name for name in (
    'core.lua', 'encounter_catalogue.lua', 'enemy_catalogue.lua', 'progress.lua',
    'enemy_genes.lua', 'technical_ai.lua', 'runtime_encounters.lua')]

PRELUDE = r'''
local C=assert(dofile(arg[1])); local Enc=assert(dofile(arg[2])); local EnemyCat=assert(dofile(arg[3]))
local P=assert(dofile(arg[4])); local EnemyGenes=assert(dofile(arg[5])); local TechAI=assert(dofile(arg[6]))
local R=assert(dofile(arg[7]))
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
local function count(t) local n=0 for _ in pairs(t) do n=n+1 end return n end
local function any_kind(events,kind) for _,e in ipairs(events or {}) do if e.kind==kind then return e end end return nil end

local profile=C.new_profile(4242)
local run=C.new_run(profile)
local actors,next_handle={},0
local fail_remove_until=0; local remove_attempts=0; local spawn_calls=0; local refuse_spawn=nil
local deny_state=false
local cpu,tech={},{}; local tech_ok=true
local players={[1]={x=0,y=0,percent=0,stocks=99},[2]={x=28,y=0,percent=0,stocks=99}}
local tells={}
local gd={}
gd.log=function() end
gd.spawn_enemy=function(kind,x,y,opts)
 spawn_calls=spawn_calls+1
 if refuse_spawn and refuse_spawn(spawn_calls) then return nil,'pool exhausted' end
 next_handle=next_handle+1
 actors[next_handle]={kind=kind,x=x,y=y,alive=true,vulnerable=true,hits=0,received=0,attack_id=1,damage=0,facing=opts and opts.facing or 1}
 return next_handle
end
gd.enemy_state=function(h) if deny_state then return nil end return actors[h] end
gd.enemy_alive=function(h) return actors[h]~=nil and actors[h].alive==true end
gd.enemy_remove=function(h)
 remove_attempts=remove_attempts+1
 if remove_attempts<=fail_remove_until then return false end
 if actors[h] then actors[h]=nil end
 return true
end
gd.enemy_strike=function() return true end
gd.cpu_technical=function(port,skill,seed)
 if not tech_ok then return false end
 if skill==nil then return {enabled=true,skill=tech[port] and tech[port].skill or 0} end
 if skill==0 then tech[port]=nil; return true end
 tech[port]={skill=skill,seed=seed}; return true
end
gd.cpu_mode=function(port,mode) cpu[port]=mode; return true end
gd.player=function(port) return players[port] end
gd.set_stocks=function(port,n) players[port].stocks=n end
_G.gd=gd -- TechAI reads the engine table from the sandbox global, as bundled

local function make_rt(over)
 over=over or {}
 return R.new(C,gd,{EnemyGenes=EnemyGenes,EnemyCatalogue=EnemyCat,TechAI=TechAI,Progress=P},
  {get_run=function() return run end, on_event=function(e) tells[#tells+1]=e end,
   bounds=over.bounds or {min_x=-200,max_x=200,min_y=-200,max_y=200},
   max_respawns=over.max_respawns, max_actors=over.max_actors, max_custom=over.max_custom,
   max_fighter_waves=over.max_fighter_waves, cleanup_attempts=over.cleanup_attempts,
   buff_fighters=over.buff_fighters, fighter_family=over.fighter_family, fighter_slot=over.fighter_slot})
end
local function node_for(room,enc_id,over)
 local n={id=room,kind='arena',encounter_spec=clone(Enc.encounters[enc_id])}
 if over then for k,v in pairs(over) do n[k]=v end end
 return n
end
local function progress_for(room) return P.new('run1',room,{supplies=2,lives=3}) end
local function enemy_hosts() local n=0 for h in pairs(run.hosts) do if h:sub(1,6)=='enemy_' then n=n+1 end end return n end
local function live_actors() return count(actors) end
'''


def _run(body):
    program = PRELUDE + '\n' + body
    result = subprocess.run([LUA, '-', *[str(m) for m in MODULES]],
                            input=program, text=True, capture_output=True)
    if result.returncode != 0:
        Path('/tmp/encounter-runtime-failure.lua').write_text(program)
        raise AssertionError(result.stdout + result.stderr)


class EncounterRuntimeTests(TestCase):
    def test_plan_scheduling_and_refusal(self):
        _run(r'''
-- pincer_pair: two goombas and a redead share one concurrent custom wave.
local rt=make_rt()
local ok,pl=rt:plan(node_for('r','pincer_pair')); assert(ok,pl)
assert(#pl.entities==3 and #pl.waves==1 and pl.fighters==0)
for _,e in ipairs(pl.entities) do assert(e.role=='custom' and e.id:match('^enemy_r_%d+$')) end
-- hunter_pair: two fighters cannot share the single CPU port, so they wave.
ok,pl=rt:plan(node_for('r','hunter_pair')); assert(ok,pl)
assert(pl.fighters==2 and #pl.waves==2)
for _,w in ipairs(pl.waves) do assert(#w==1) end
-- custom actors before a fighter keep their wave, then the fighter gets its own.
ok,pl=rt:plan(node_for('r','skyline_denial')); assert(ok,pl)
assert(#pl.waves==2 and #pl.waves[1]==2 and #pl.waves[2]==1 and pl.entities[3].role=='fighter')
ok,pl=rt:plan(node_for('r','guard_post')); assert(ok,pl)
assert(pl.entities[1].fall=='despawn' and pl.entities[1].family=='rime')
ok,pl=rt:plan(node_for('r','champ_cinder')); assert(ok,pl)
assert(pl.fighters==1 and pl.entities[1].stocks==2 and pl.entities[1].family=='cinder')
-- Fighter family/slot policy: deterministic supported default, explicit
-- supported override, and refusal of unsupported explicit families/slots.
ok,pl=rt:plan(node_for('r','aerial_duel')); assert(ok,pl)
assert(pl.entities[1].role=='fighter' and pl.entities[1].family=='cinder'
 and pl.entities[1].slot=='assault' and pl.entities[1].buff==1)
local spec=clone(Enc.encounters.aerial_duel); spec.enemies[1].family='rime'; spec.enemies[1].slot='guard'
ok,pl=rt:plan({id='r',encounter_spec=spec}); assert(ok,pl)
assert(pl.entities[1].family=='rime' and pl.entities[1].slot=='guard')
local rt2=make_rt({fighter_family='rime'})
ok,pl=rt2:plan(node_for('r','aerial_duel')); assert(ok,pl)
assert(pl.entities[1].family=='rime')
local el=rt:eligibility()
assert(el.families[1]=='cinder' and el.families[2]=='rime' and el.buff_fighters==true
 and el.fighter_family=='cinder' and el.fighter_slot=='assault' and el.champion_potency==4)
assert(rt:status().eligibility and rt:status().fighter==nil)
-- Unsupported explicit families are refused, never silently converted.
bad=clone(Enc.encounters.scout_pair); bad.enemies={{kind='goomba',count=1,level=3,family='kinetic'}}
assert(not rt:plan({id='r',encounter_spec=bad}))
bad=clone(Enc.encounters.aerial_duel); bad.enemies={{kind='fighter',count=1,level=6,family='sigil'}}
assert(not rt:plan({id='r',encounter_spec=bad}))
bad=clone(Enc.encounters.aerial_duel); bad.enemies={{kind='fighter',count=1,level=6,slot='cargo'}}
assert(not rt:plan({id='r',encounter_spec=bad}))
assert(not pcall(R.new,C,gd,{EnemyGenes=EnemyGenes,EnemyCatalogue=EnemyCat,TechAI=TechAI,Progress=P},
 {get_run=function() return run end,fighter_family='kinetic'}))
-- Refusals: no spec, empty composition, unknown kind, multiple champions,
-- more fighter waves than the port supports, actor budget.
assert(not rt:plan({id='r',encounter_spec=nil}))
assert(not rt:plan(node_for('r','scout_pair',{encounter_spec={version=1,id='x',enemies={}}})))
bad=clone(Enc.encounters.scout_pair); bad.enemies={{kind='metaknight',count=1,level=3}}
assert(not rt:plan({id='r',encounter_spec=bad}))
bad=clone(Enc.encounters.champ_cinder); bad.enemies={{kind='champion',count=2,level=8,family='cinder'}}
assert(not rt:plan({id='r',encounter_spec=bad}))
bad=clone(Enc.encounters.hunter_pair); bad.enemies={{kind='fighter',count=6,level=5}}
assert(not rt:plan({id='r',encounter_spec=bad}))
bad=clone(Enc.encounters.scout_pair); bad.enemies={{kind='goomba',count=8,level=3},{kind='goomba',count=8,level=3}}
assert(not rt:plan({id='r',encounter_spec=bad}))
-- A kind the catalogue describes with an adventure host but the native spawn
-- list does not implement must not appear functional.
local cat=clone(EnemyCat); cat.enemies.ghost={id='ghost',host='adventure',motion='walk',ledge='turn',fall='despawn',genes={'kinetic'}}
local rt3=R.new(C,gd,{EnemyGenes=EnemyGenes,EnemyCatalogue=cat,TechAI=TechAI,Progress=P},{get_run=function() return run end})
bad=clone(Enc.encounters.scout_pair); bad.enemies={{kind='ghost',count=1,level=3}}
assert(not rt3:plan({id='r',encounter_spec=bad}))
print('encounter plan: scheduling policy and controlled refusal passed')
''')

    def test_spawn_refusal_rolls_back_actors_and_hosts(self):
        _run(r'''
local p=progress_for('r2')
local rt=make_rt()
refuse_spawn=function(n) return n==2 end
local ok,why=rt:begin(node_for('r2','pincer_pair'),p)
assert(not ok and tostring(why):find('spawn refused',1,true),tostring(why))
assert(live_actors()==0,'owned native actors leaked after rollback')
assert(enemy_hosts()==0,'owned gene host leaked after rollback')
assert(#rt:states()==0 and not rt:status().active)
-- The run must still serialize; a half-torn-down begin is not a valid state.
assert(C.snapshot(run))
refuse_spawn=nil
assert(rt:begin(node_for('r2','pincer_pair'),p))
assert(live_actors()==3 and enemy_hosts()==3)
assert(rt:clear())
assert(live_actors()==0 and enemy_hosts()==0)
-- A gene-host refusal after a successful native spawn also rolls back.
deny_state=true
local ok2,why2=rt:begin(node_for('r2','guard_post'),p)
deny_state=false
assert(not ok2 and tostring(why2):find('gene host refused',1,true),tostring(why2))
assert(live_actors()==0 and enemy_hosts()==0,'attach refusal leaked a host or actor')
assert(C.snapshot(run))
print('encounter spawn: refusal rolls back actors and hosts passed')
''')

    def test_defeat_evidence_is_stable_and_idempotent(self):
        _run(r'''
local p=progress_for('r3')
local rt=make_rt()
assert(rt:begin(node_for('r3','scout_pair'),p))
local live={} for h in pairs(actors) do live[#live+1]=h end table.sort(live)
local h1=live[1]
-- Provenance maps a native handle to its saved stable id.
local status=rt:hit({handle=h1,id='contact-1',from=1,damage=4})
assert(status.handled and status.entity=='enemy_r3_1' and status.host=='enemy_r3_1')
assert(not rt:hit({handle=h1,id='contact-1'}).handled,'duplicate contact charged again')
-- A confirmed defeat writes the stable id and ignores duplicate/stale evidence.
local _,events=rt:defeat(h1,p)
assert(any_kind(events,'defeat') and p.defeated.enemy_r3_1)
assert(not any_kind(events,'clear'))
local _,dup=rt:defeat(h1,p); assert(any_kind(dup,'ignored'),'duplicate defeat was not ignored')
local _,stale=rt:defeat(999,p); assert(any_kind(stale,'ignored'),'stale handle was not ignored')
assert(p.defeated.enemy_r3_2==nil and not rt:status().cleared)
local h2
for h in pairs(actors) do h2=h end
local _,fin=rt:defeat(h2,p)
assert(p.defeated.enemy_r3_2 and any_kind(fin,'clear'))
print('encounter defeat: stable ids, duplicate/stale harmless, clear once passed')
''')

    def test_vanished_or_escaped_actor_is_not_defeat(self):
        _run(r'''
local p=progress_for('r4')
local rt=make_rt({max_respawns=1})
assert(rt:begin(node_for('r4','guard_post'),p))
local entity=rt:composition()[1]
local h=entity.handle
assert(h)
-- A native despawn is not a defeat: it is respawned on the same stable id.
actors[h].alive=false
local _,events=rt:update(p)
assert(any_kind(events,'respawn') and not p.defeated[entity.id])
assert(not rt:status().cleared)
-- Leaving the camera is not a defeat either; with the budget spent it is a
-- hard error, never a silent clear.
local entity2=rt:composition()[1]
assert(entity2.handle~=h and actors[entity2.handle])
actors[entity2.handle].x=9999
local _,escaped=rt:update(p)
assert(any_kind(escaped,'error') and not p.defeated[entity.id] and not rt:status().cleared)
assert(rt:status().error)
local _,again=rt:update(p)
assert(#again==0,'error repeated every frame')
print('encounter respawn: vanished/escaped is not defeat, budget raises error passed')
''')

    def test_stock_wave_continuation_and_partial_resume(self):
        _run(r'''
local p=progress_for('r5')
local rt=make_rt()
assert(rt:begin(node_for('r5','hunter_pair'),p))
assert(rt:status().wave==1 and rt:status().entities==2 and rt.active_fighter.id=='enemy_r5_1')
assert(any_kind(select(2,rt:stock(1,99,98,p)),'ignored'),'wrong port observed')
assert(any_kind(select(2,rt:stock(2,98,99,p)),'ignored'),'non-decreasing stock observed')
local _,s1=rt:stock(2,99,98,p)
assert(any_kind(s1,'stock') and any_kind(s1,'defeat') and p.defeated.enemy_r5_1)
assert(any_kind(s1,'wave') and rt:status().wave==2 and rt.active_fighter.id=='enemy_r5_2')
local _,s2=rt:stock(2,99,98,p)
assert(p.defeated.enemy_r5_2 and any_kind(s2,'clear'))
-- After the clear there is no live fighter; stale observations are ignored.
assert(any_kind(select(2,rt:stock(2,99,98,p)),'ignored'),'post-clear stock accepted')
-- Partial resume skips the saved defeat and starts at the next wave.
local p2=progress_for('r6'); assert(P.defeat(p2,'enemy_r6_1'))
local rt2=make_rt()
assert(rt2:begin(node_for('r6','hunter_pair'),p2))
assert(rt2:status().wave==2 and rt2.active_fighter and rt2.active_fighter.id=='enemy_r6_2')
-- A partially fought single champion resumes from encounter_kos.
local p3=progress_for('r7'); p3.encounter_kos.r7=1
local rt3=make_rt()
assert(rt3:begin(node_for('r7','champ_cinder'),p3))
assert(rt3.active_fighter.remaining==1)
local _,sc=rt3:stock(2,99,98,p3)
assert(p3.defeated.enemy_r7_1 and any_kind(sc,'clear'))
print('encounter stocks: wave continuation and partial resume passed')
''')

    def test_gene_host_buffs_and_cleanup(self):
        _run(r'''
-- A custom actor keeps the immutable gene and the adapter's encounter buff.
local p=progress_for('r8')
local rt=make_rt()
assert(rt:begin(node_for('r8','guard_post'),p))
local e=rt:composition()[1]
local host=e.host; local gene=run.hosts[host].slots.assault
assert(gene and run.genes[gene].kind=='rime')
assert(run.genes[gene].base.potency==8,'adapter mutated the immutable base')
assert(C.ability(run,host,'assault').damage==9 and C.ability(run,host,'assault').cost==1)
assert(rt:clear())
assert(run.hosts[host]==nil and run.genes[gene]==nil,'custom gene host leaked')
-- A champion owns a fighter CPU host plus a stronger encounter potency buff.
local p2=progress_for('r9')
local rt2=make_rt()
assert(rt2:begin(node_for('r9','champ_cinder'),p2))
assert(rt2.active_fighter.remaining==2)
local host2='enemy_r9_1'; local gene2=run.hosts[host2].slots.assault
assert(gene2 and run.genes[gene2].kind=='cinder')
assert(C.resolve(run,host2,'assault').potency==12)
assert(tech[2] and tech[2].skill>=1 and cpu[2]=='fight')
assert(rt2:clear())
assert(run.hosts[host2]==nil and run.genes[gene2]==nil,'champion gene host leaked')
print('encounter genes: adapter buff, champion host buff and cleanup passed')
''')

    def test_ordinary_fighter_gene_buffs(self):
        _run(r'''
-- An ordinary fighter is a real gene host too: deterministic cinder default,
-- +1 potency buff, immutable base.
local p=progress_for('f1')
local rt=make_rt()
assert(rt:begin(node_for('f1','aerial_duel'),p))
local ae=rt:active_entity()
assert(ae and ae.kind=='fighter' and ae.family=='cinder' and ae.buff==1 and ae.host=='enemy_f1_1')
local host=ae.host; local gene=run.hosts[host].slots.assault
assert(gene and run.genes[gene].kind=='cinder')
assert(run.genes[gene].base.potency==8,'fighter buff mutated the immutable base')
assert(C.resolve(run,host,'assault').potency==9 and C.ability(run,host,'assault').damage==9)
assert(rt:status().fighter.host==host and rt:status().fighter.family=='cinder')
-- Duplicate/stale fighter evidence stays harmless.
assert(any_kind(select(2,rt:stock(2,98,99,p)),'ignored'))
assert(any_kind(select(2,rt:defeat(123,p)),'ignored'))
local _,s=rt:stock(2,99,98,p)
assert(p.defeated.enemy_f1_1 and any_kind(s,'clear'))
assert(rt:clear())
assert(run.hosts[host]==nil and run.genes[gene]==nil,'fighter gene host leaked')
-- An explicit supported row family/slot is a real placement.
local p2=progress_for('f2')
local spec=node_for('f2','aerial_duel')
spec.encounter_spec.enemies[1].family='rime'; spec.encounter_spec.enemies[1].slot='guard'
local rt2=make_rt()
assert(rt2:begin(spec,p2))
local h2=rt2:active_entity().host
assert(run.hosts[h2].slots.guard and run.genes[run.hosts[h2].slots.guard].kind=='rime')
assert(C.resolve(run,h2,'guard').potency==9)
assert(rt2:clear())
-- Explicit opt-out still yields a functional fighter CPU with no Core host.
local p3=progress_for('f3')
local rt3=make_rt({buff_fighters=false})
assert(rt3:begin(node_for('f3','aerial_duel'),p3))
assert(run.hosts[rt3:active_entity().host]==nil and tech[2] and cpu[2]=='fight')
assert(rt3:clear())
-- opts-level family policy applies to champions and ordinary fighters alike.
local p4=progress_for('f4')
local rt4=make_rt({fighter_family='rime'})
assert(rt4:begin(node_for('f4','elite_twin'),p4))
assert(rt4:active_entity().family=='rime')
assert(rt4:clear())
print('encounter fighters: gene/buff policy, immutability, override and opt-out passed')
''')

    def test_cleanup_retries_pending_and_mixed_hosts(self):
        _run(r'''
-- A transient native removal failure is retried inside the cleanup budget.
local p=progress_for('r10')
local rt=make_rt({cleanup_attempts=4})
assert(rt:begin(node_for('r10','scout_pair'),p))
remove_attempts=0; fail_remove_until=2
assert(rt:clear())
assert(remove_attempts>=3,'cleanup did not retry removal')
-- reset() must not erase live ownership; a persistent removal refusal must
-- return the pending ownership so it can be retried, not silently dropped.
local p2=progress_for('r11')
local rt2=make_rt({cleanup_attempts=2})
assert(rt2:begin(node_for('r11','scout_pair'),p2))
assert(not rt2:reset(),'reset erased live owned actors')
assert(rt2:has_live())
fail_remove_until=math.huge
local ok,why,pending=rt2:clear()
assert(not ok and tostring(why):find('pending',1,true),tostring(why))
assert(pending and #pending==2 and tostring(pending[1].reason):find('could not remove',1,true))
assert(rt2:has_live(),'pending ownership was erased')
fail_remove_until=0
assert(rt2:clear(),'retry after recovery must succeed')
assert(not rt2:has_live())
-- A mixed custom+fighter encounter releases every host and modifier on exit.
local p3=progress_for('r12')
local rt3=make_rt()
assert(rt3:begin(node_for('r12','skyline_denial'),p3))
assert(enemy_hosts()==2)
local live={} for h in pairs(actors) do live[#live+1]=h end table.sort(live)
assert(rt3:defeat(live[1],p3))
local _,d2=rt3:defeat(live[2],p3)
assert(any_kind(d2,'wave') and rt3:active_entity())
assert(enemy_hosts()==3,'fighter wave host was not created')
assert(rt3:clear())
assert(enemy_hosts()==0 and live_actors()==0,'mixed encounter leaked ownership')
-- Actor and fighter budgets are enforced before any native spawn.
local rt4=make_rt({max_actors=2})
assert(not rt4:plan(node_for('r','pincer_pair')),'actor budget ignored')
local rt5=make_rt({max_fighter_waves=1})
assert(not rt5:plan(node_for('r','hunter_pair')),'fighter wave budget ignored')
print('encounter cleanup: retries, pending ownership, mixed hosts and budgets passed')
''')


if __name__ == '__main__':
    main()
