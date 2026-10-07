#!/usr/bin/env python3
"""Exercise the transaction-safe reward resolver against real Core/Progress/catalogue Lua.

These are pure-module tests: no engine, no native build. They prove the resolver's
own contracts (supported-definition filtering, stat caps, tradeoff atomicity,
target/family filtering, one-time claims, snapshot round trips and the deferred
effect rollback contract), not in-engine play.
"""
from pathlib import Path
import shutil
import subprocess
import unittest
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source

SOURCE = game_source.ROGUELITE

PRELUDE = r'''
local S=arg[1]
local Core=assert(loadfile(S..'/core.lua'))()
local Progress=assert(loadfile(S..'/progress.lua'))()
local EC=assert(loadfile(S..'/encounter_catalogue.lua'))()
local GC=assert(loadfile(S..'/gene_catalogue.lua'))()
local R=assert(loadfile(S..'/runtime_rewards.lua'))()
local rt=R.new(Core,{Progress=Progress,EncounterCatalogue=EC,GeneCatalogue=GC})
local function fresh(seed,supplies)
 local p=Core.new_profile(seed); local run=Core.new_run(p)
 local prog=Progress.new(run.id,'room1',{supplies=supplies or 2})
 Progress.complete_objective(prog,'room1','done')
 return run,prog
end
local function psig(p)
 local n=0 for _ in pairs(p.claimed) do n=n+1 end
 return tostring(p.supplies)..'/'..n..'/'..tostring(p.objectives.room1)
end
local function snapshot(run,prog) return assert(Core.snapshot(run))..'|'..psig(prog) end
'''


class RewardRuntimeTests(unittest.TestCase):
    def run_lua(self, body):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua, 'Lua interpreter required')
        result = subprocess.run([lua, '-', str(SOURCE)], input=PRELUDE + body, text=True,
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS', result.stdout)

    def test_supported_definitions(self):
        self.run_lua(r'''
local defs={}
for _,d in ipairs(rt:supported_definitions()) do defs[d.id]=d end
assert(defs.potency_small.supported and defs.potency_small.mechanic=='core_reward_stat')
assert(defs.glass_cannon.supported and defs.glass_cannon.mechanic=='core_reward_tradeoff')
assert(defs.supply_crate.supported and defs.supply_crate.mechanic=='progress_supply')
assert(defs.repair_kit.supported and defs.repair_kit.requires_effect=='heal')
assert(defs.charge_flask.supported and defs.charge_flask.requires_effect=='charge')
assert(not defs.thermal_seed.supported and defs.thermal_seed.reason:find('not implemented'))
assert(not defs.rime_bloom.supported and defs.rime_bloom.reason:find('not implemented'))
assert(not defs.warding_charm.supported and defs.warding_charm.reason:find('equipment'))
assert(not defs.overcharge.supported and defs.overcharge.reason:find('family'))
assert(not defs.storm_pin.supported and defs.storm_pin.reason:find('family'))
for _,d in ipairs(rt:supported_definitions()) do
 assert(d.supported == false or d.supported == true)
 if not d.supported then assert(d.reason,'unsupported definition needs a reason') end
end
print('PASS supported definitions')
''')

    def test_upgrade_preview_commit_and_unplaced_target(self):
        self.run_lua(r'''
local run,prog=fresh(101)
local ctx={run=run,progress=prog,spec=EC.rewards.potency_large,target='r1',room_id='room1'}
local before=Core.resolve(run,'player','assault').potency
local origin=snapshot(run,prog)
local view=assert(rt:preview(ctx))
assert(view.kind=='upgrade' and view.benefit[1].stat=='potency')
assert(snapshot(run,prog)==origin,'preview mutated the source')
local result=assert(rt:commit(ctx))
assert(snapshot(run,prog)==origin,'commit mutated the source')
assert(Core.resolve(run,'player','assault').potency==before)
local after=Core.resolve(result.run,'player','assault').potency
assert(after==before+5)
assert(view.benefit[1].after==after and #view.cost==0)
assert(result.progress.claimed['reward:room1'] and not prog.claimed['reward:room1'])
assert(Core.snapshot(result.run) and Progress.validate(result.progress))
-- An unplaced gene previews and commits the same base+upgrade stat.
local v2=assert(rt:preview({run=run,progress=prog,spec=EC.rewards.reach_small,target='r3',room_id='room1'}))
local c2=assert(rt:commit({run=run,progress=prog,spec=EC.rewards.reach_small,target='r3',room_id='room1'}))
assert(v2.changes[1].after==16 and c2.run.genes.r3.upgrades.reach==3)
assert(not run.genes.r3.upgrades.reach)
print('PASS upgrade preview/commit')
''')

    def test_upgrade_cap_boundaries(self):
        self.run_lua(r'''
local run,prog=fresh(102)
assert(Core.reward(run,'r1','potency',20))
local v,w=rt:preview({run=run,progress=prog,spec=EC.rewards.potency_small,target='r1',room_id='room1'})
assert(not v and w=='no effect at the current cap')
local cs,ws=rt:commit({run=run,progress=prog,spec=EC.rewards.potency_large,target='r1',room_id='room1'})
assert(not cs and ws=='no effect at the current cap')
local run2,prog2=fresh(103)
assert(Core.reward(run2,'r1','cooldown',-89))
local v3,w3=rt:preview({run=run2,progress=prog2,spec=EC.rewards.cooldown_trim,target='r1',room_id='room1'})
assert(not v3 and w3=='no effect at the current cap')
print('PASS cap boundaries')
''')

    def test_tradeoff_all_or_nothing(self):
        self.run_lua(r'''
local run,prog=fresh(201)
local view=assert(rt:preview({run=run,progress=prog,spec=EC.rewards.glass_cannon,target='r1',room_id='room1'}))
assert(view.benefit[1].stat=='potency' and view.benefit[1].after==16)
assert(view.cost[1].stat=='capacity' and view.cost[1].after==2)
local res=assert(rt:commit({run=run,progress=prog,spec=EC.rewards.glass_cannon,target='r1',room_id='room1'}))
local st=Core.resolve(res.run,'player','assault')
assert(st.potency==16 and st.capacity==2)
local run2,prog2=fresh(202)
assert(Core.reward(run2,'r1','potency',20))
local snap=snapshot(run2,prog2)
local a,aw=rt:commit({run=run2,progress=prog2,spec=EC.rewards.glass_cannon,target='r1',room_id='room1'})
assert(not a and aw=='tradeoff cannot apply its gain at the current cap')
assert(snapshot(run2,prog2)==snap)
local run3,prog3=fresh(203)
assert(Core.reward(run3,'r1','capacity',-2))
local snap3=snapshot(run3,prog3)
local b,bw=rt:commit({run=run3,progress=prog3,spec=EC.rewards.glass_cannon,target='r1',room_id='room1'})
assert(not b and bw=='tradeoff cannot pay the full advertised cost for capacity')
assert(snapshot(run3,prog3)==snap3)
local run4,prog4=fresh(204)
local v4=assert(rt:preview({run=run4,progress=prog4,spec=EC.rewards.short_fuse,target='r1',room_id='room1'}))
assert(v4.benefit[1].stat=='cooldown' and v4.cost[1].stat=='gain')
print('PASS tradeoff atomicity')
''')

    def test_tradeoff_full_effective_cost(self):
        self.run_lua(r'''
-- capacity 1.5 cannot pay the advertised 1: 0.5 paid would award the full +6.
local run,prog=fresh(801)
assert(Core.reward(run,'r1','capacity',-1.5))
assert(math.abs(Core.resolve(run,'player','assault').capacity-1.5)<1e-9)
local origin=snapshot(run,prog)
local c,w=rt:commit({run=run,progress=prog,spec=EC.rewards.glass_cannon,target='r1',room_id='room1'})
assert(not c and w=='tradeoff cannot pay the full advertised cost for capacity')
assert(snapshot(run,prog)==origin)
-- A modifier that clamps the effective gain is not a partial-cost loophole.
local run2,prog2=fresh(802)
assert(Core.apply_modifier(run2,'player','assault',{id='drain',stat='gain',add=-0.75}))
assert(math.abs(Core.resolve(run2,'player','assault').gain-0.25)<1e-9)
local c2,w2=rt:commit({run=run2,progress=prog2,spec=EC.rewards.slow_burn,target='r1',room_id='room1'})
assert(not c2 and w2=='tradeoff cannot pay the full advertised cost for gain')
-- An ordinary full-cost tradeoff still succeeds and both sides move fully.
local run3,prog3=fresh(803)
local ok=assert(rt:commit({run=run3,progress=prog3,spec=EC.rewards.glass_cannon,target='r1',room_id='room1'}))
local st=Core.resolve(ok.run,'player','assault')
assert(st.potency==16 and st.capacity==2)
-- Overlapping add/remove is refused; repeated resolution is deterministic.
local dup=rt:classify({id='x',version=1,kind='tradeoff',family='any',add={potency=2},remove={potency=1}})
assert(not dup.supported and dup.reason:find('twice'))
local a=assert(rt:commit({run=run3,progress=prog3,spec=EC.rewards.slow_burn,target='r1',room_id='room1'}))
local b=assert(rt:commit({run=run3,progress=prog3,spec=EC.rewards.slow_burn,target='r1',room_id='room1'}))
assert(Core.snapshot(a.run)==Core.snapshot(b.run) and a.message==b.message)
print('PASS full effective cost')
''')

    def test_progress_run_ownership(self):
        self.run_lua(r'''
local run,prog=fresh(701)
local foreign=Progress.new('run_foreign','room1',{supplies=2})
Progress.complete_objective(foreign,'room1','done')
local origin=snapshot(run,prog)
local v,w=rt:preview({run=run,progress=foreign,spec=EC.rewards.potency_small,target='r1',room_id='room1'})
assert(not v and w=='progress belongs to another run')
local c,cw=rt:commit({run=run,progress=foreign,spec=EC.rewards.potency_small,target='r1',room_id='room1'})
assert(not c and cw=='progress belongs to another run')
assert(snapshot(run,prog)==origin)
-- Matching progress still resolves and commits unchanged.
local ok=assert(rt:commit({run=run,progress=prog,spec=EC.rewards.potency_small,target='r1',room_id='room1'}))
assert(ok.progress.run_id==run.id and ok.progress.claimed['reward:room1'])
print('PASS progress ownership')
''')

    def test_family_and_target_filtering(self):
        self.run_lua(r'''
local run,prog=fresh(301)
local v,w=rt:preview({run=run,progress=prog,spec=EC.rewards.glass_cannon,target='r2',room_id='room1'})
assert(not v and w=='target family is incompatible with this reward')
local v2,w2=rt:preview({run=run,progress=prog,spec=EC.rewards.brittle_guard,target='r1',room_id='room1'})
assert(not v2 and w2=='target family is incompatible with this reward')
local offer=assert(rt:preview({run=run,progress=prog,spec=EC.rewards.glass_cannon,room_id='room1'}))
assert(#offer.targets==2)
for _,t in ipairs(offer.targets) do assert(t.kind=='cinder' and t.supported) end
local offer2=assert(rt:preview({run=run,progress=prog,spec=EC.rewards.brittle_guard,room_id='room1'}))
assert(#offer2.targets==1 and offer2.targets[1].id=='r2')
-- Family aliases come from Core.definitions, not a guessed name mapping.
assert(rt:gene_family('cinder')=='fire' and rt:gene_family('rime')=='frost')
assert(#rt:family_kinds('cobalt')==0)
assert(#rt:targets(run,EC.rewards.glass_cannon)==2)
-- Enemy-owned genes are never eligible.
local enemy=assert(Core.acquire(run,'cinder'))
assert(Core.equip(run,'enemy_room','assault',enemy))
local offer3=assert(rt:preview({run=run,progress=prog,spec=EC.rewards.potency_small,room_id='room1'}))
for _,t in ipairs(offer3.targets) do assert(t.id~=enemy) end
local ev,ew=rt:commit({run=run,progress=prog,spec=EC.rewards.potency_small,target=enemy,room_id='room1'})
assert(not ev and ew=='enemy-owned genes cannot be modified')
print('PASS family/target filtering')
''')

    def test_claims_and_objectives(self):
        self.run_lua(r'''
local run,prog=fresh(401)
local r=assert(rt:commit({run=run,progress=prog,spec=EC.rewards.supply_crate,room_id='room1'}))
local v,w=rt:preview({run=r.run,progress=r.progress,spec=EC.rewards.supply_crate,room_id='room1'})
assert(not v and w=='reward already claimed')
local run2,prog2=fresh(402)
Progress.enter(prog2,'room2')
local v2,w2=rt:preview({run=run2,progress=prog2,spec=EC.rewards.supply_crate,room_id='room2'})
assert(not v2 and w2=='objective not fulfilled')
local v3,w3=rt:preview({run=run2,progress=prog2,spec=EC.rewards.supply_crate,room_id='room9'})
assert(not v3 and w3=='room not visited')
local v4,w4=rt:preview({run=run2,progress=prog2,spec=EC.rewards.supply_crate,room_id=''})
assert(not v4 and w4=='invalid room id')
-- A forged spec is refused before any mechanics run.
local forge={id='supply_crate',version=1,kind='consumable',family='any',supply=5}
local v5,w5=rt:commit({run=run2,progress=prog2,spec=forge,room_id='room1'})
assert(not v5 and w5=='reward specification does not match the catalogue')
print('PASS claims/objectives')
''')

    def test_supplies_and_deferred_effects(self):
        self.run_lua(r'''
local run,prog=fresh(501,8)
local v=assert(rt:preview({run=run,progress=prog,spec=EC.rewards.supply_crate,room_id='room1'}))
assert(v.changes[1].before==8 and v.changes[1].after==9)
local r=assert(rt:commit({run=run,progress=prog,spec=EC.rewards.supply_crate,room_id='room1'}))
assert(r.progress.supplies==9 and Progress.validate(r.progress))
local runX,progX=fresh(502,9)
local vx,wx=rt:preview({run=runX,progress=progX,spec=EC.rewards.supply_crate,room_id='room1'})
assert(not vx and wx=='supplies are already full')
local run2,prog2=fresh(503)
local origin=Core.snapshot(run2)
local vh,wh=rt:preview({run=run2,progress=prog2,spec=EC.rewards.repair_kit,room_id='room1'})
assert(not vh and wh=='heal requires a staged effect contract')
local h=assert(rt:commit({run=run2,progress=prog2,spec=EC.rewards.repair_kit,room_id='room1',effects={version=1,heal=true}}))
assert(#h.effects==1 and h.effects[1].kind=='heal' and h.effects[1].amount==30)
assert(h.progress.claimed['reward:room1'] and Core.snapshot(run2)==origin)
local vc,wc=rt:preview({run=run2,progress=prog2,spec=EC.rewards.charge_flask,target='r1',room_id='room1'})
assert(not vc and wc=='charge requires a staged effect contract')
local c=assert(rt:commit({run=run2,progress=prog2,spec=EC.rewards.charge_flask,target='r1',room_id='room1',effects={version=1,charge=true}}))
assert(c.effects[1].kind=='charge' and c.effects[1].slot=='assault' and c.effects[1].target==3)
run2.hosts.player.state.assault.charge=3
local cf,wf=rt:commit({run=run2,progress=prog2,spec=EC.rewards.charge_flask,target='r1',room_id='room1',effects={version=1,charge=true}})
assert(not cf and wf=='charge is already full')
run2=assert(Core.restore(origin))
local cv,wv=rt:commit({run=run2,progress=prog2,spec=EC.rewards.repair_kit,room_id='room1',effects={version=2,heal=true}})
assert(not cv and wv=='unsupported effect contract version')
print('PASS supplies/deferred effects')
''')

    def test_snapshot_roundtrip_and_rollback_contract(self):
        self.run_lua(r'''
local run,prog=fresh(601)
local origin=Core.snapshot(run)
local a=assert(rt:commit({run=run,progress=prog,spec=EC.rewards.potency_large,target='r1',room_id='room1'}))
-- The caller may discard the transaction (e.g. a later native step failed): the
-- resolver never touched the originals, so rollback is simply not committing.
assert(Core.snapshot(run)==origin and not prog.claimed['reward:room1'])
assert(#a.effects==0)
local text=assert(Core.snapshot(a.run))
local restored=assert(Core.restore(text))
assert(Core.resolve(restored,'player','assault').potency==15)
local b=assert(rt:commit({run=run,progress=prog,spec=EC.rewards.potency_large,target='r1',room_id='room1'}))
assert(Core.snapshot(b.run)==text and b.progress.claimed['reward:room1'])
assert(Progress.validate(b.progress))
print('PASS snapshot/rollback contract')
''')

    def test_classify_refusals(self):
        self.run_lua(r'''
assert(not rt:classify({id='x',version=1,kind='upgrade',family='any',stat='luck',delta=1}).supported)
assert(not rt:classify({id='x',version=1,kind='mutation',family='fire',reaction='thermal_shock'}).supported)
assert(not rt:classify({id='x',version=1,kind='equipment',family='any',slot='charm',stat='capacity',delta=1}).supported)
assert(not rt:classify({id='x',version=2,kind='upgrade',family='any',stat='potency',delta=1}).supported)
assert(not rt:classify({id='',version=1,kind='upgrade'}).supported)
local c=rt:classify({id='x',version=1,kind='tradeoff',family='any',add={potency=2}})
assert(not c.supported and c.reason=='tradeoff is missing its cost')
local d=rt:classify({id='x',version=1,kind='tradeoff',family='any',add={potency=2},remove={potency=1}})
assert(not d.supported and d.reason:find('twice'))
local e=rt:classify({id='x',version=1,kind='consumable',family='any',supply=1,heal=2})
assert(not e.supported and e.reason=='consumable needs exactly one effect')
local f=rt:classify({id='x',version=1,kind='consumable',family='any',charge=99})
assert(not f.supported and f.reason=='invalid charge amount')
print('PASS classify refusals')
''')


if __name__ == '__main__':
    unittest.main()
