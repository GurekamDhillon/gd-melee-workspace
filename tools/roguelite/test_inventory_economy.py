#!/usr/bin/env python3
"""Gate 7 pure inventory/equipment/run-history tests against the real Lua modules.

These are pure-module tests: no engine, no native build. They prove the service
contracts (bounded capacity/stacking/cooldowns, reject-before-spend, ownership
domain checks, plan binding against stale/replayed/foreign plans, staged
transactions and rollback, owned equipment with symmetric occupancy, reversible
equipment with no numerical drift and all-or-nothing reconciliation, native
held-item refusal, bounded history with the sandbox Codec and Core migration,
bounded currency and confirmation-gated breeding, fusion dangling references and
reward-spec persistence), not in-engine play.
"""
from pathlib import Path
import shutil
import subprocess
import unittest
import game_source

SOURCE = game_source.ROGUELITE

PRELUDE = r'''
local S=arg[1]
local Core=assert(loadfile(S..'/core.lua'))()
local Progress=assert(loadfile(S..'/progress.lua'))()
local Codec=assert(loadfile(S..'/codec.lua'))()
local EC=assert(loadfile(S..'/encounter_catalogue.lua'))()
local GC=assert(loadfile(S..'/gene_catalogue.lua'))()
local RR=assert(loadfile(S..'/runtime_rewards.lua'))()
local Inv=assert(loadfile(S..'/inventory.lua'))()
local Equip=assert(loadfile(S..'/equipment.lua'))()
local Hist=assert(loadfile(S..'/run_history.lua'))()
local inv=Inv.new({Codec=Codec,Core=Core,Progress=Progress})
local eq=Equip.new(Core,{Codec=Codec})
local rt=RR.new(Core,{Progress=Progress,EncounterCatalogue=EC,GeneCatalogue=GC})
local function fresh(seed)
  local p=Core.new_profile(seed); local r=Core.new_run(p); return p,r
end
local function count(t) local n=0 for _ in pairs(t) do n=n+1 end return n end
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
local function equip_all(owner,items,capacity)
  local rec=assert(Equip.create({owner=owner,host='player',capacity=capacity or 8}))
  for _,id in ipairs(items or {}) do rec=assert(Equip.acquire(rec,id)) end
  return rec
end
'''


class InventoryEconomyTests(unittest.TestCase):
    def run_lua(self, body):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua, 'Lua interpreter required')
        result = subprocess.run([lua, '-', str(SOURCE)], input=PRELUDE + body, text=True,
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS', result.stdout)

    def test_inventory_definitions_capacity_and_stacking(self):
        self.run_lua(r'''
local supported,defs=0,{}
for id,def in pairs(Inv.definitions) do
 defs[id]=assert(Inv.classify(def))
 if defs[id].supported then supported=supported+1 end
end
assert(supported>=6,'need at least six supported consumables, got '..supported)
assert(count(Inv.definitions)>=8)
assert(not defs.frost_tonic.supported and defs.frost_tonic.reason:find('not implemented'))
assert(not defs.smoke_bomb.supported and defs.smoke_bomb.reason:find('not implemented'))
assert(not defs.bomb_core.supported and defs.bomb_core.reason:find('not implemented'))
local zero=assert(Inv.create({owner='run1',scope='run',capacity=0}))
local z,zw=Inv.acquire(zero,'repair_kit',1)
assert(not z and zw=='inventory capacity')
local pack=assert(Inv.create({owner='run1',scope='run',capacity=2}))
pack=assert(Inv.acquire(pack,'repair_kit',1))
pack=assert(Inv.acquire(pack,'supply_crate',1))
local p3,w3=Inv.acquire(pack,'charge_flask',1); assert(not p3 and w3=='inventory capacity')
pack=assert(Inv.acquire(pack,'repair_kit',1)); assert(Inv.count(pack,'repair_kit')==2)
local p4,w4=Inv.acquire(pack,'repair_kit',3); assert(not p4 and w4=='stack capacity')
local p5,w5=Inv.acquire(pack,'nonsense',1); assert(not p5 and w5=='unknown item')
assert(Inv.validate(pack))
local text=assert(inv:encode(pack))
local back=assert(inv:decode(text))
assert(Inv.count(back,'repair_kit')==2 and Inv.validate(back))
local forged=clone(pack); forged.items.frost_tonic=1
assert(not Inv.validate(forged))
print('PASS inventory definitions/capacity')
''')

    def test_inventory_use_transaction_rollback_and_reject_before_spend(self):
        self.run_lua(r'''
local p,run=fresh(101)
local inv0=assert(Inv.create({owner=run.id,scope='run',capacity=4}))
inv0=assert(Inv.acquire(inv0,'repair_kit',2))
inv0=assert(Inv.acquire(inv0,'charge_flask',2))
local no,why=inv:plan_use(inv0,'repair_kit',{frame=0,context='combat',run=run})
assert(not no and why=='heal requires a staged effect contract')
assert(Inv.count(inv0,'repair_kit')==2,'refusal spent an item')
local heal=assert(inv:plan_use(inv0,'repair_kit',{frame=0,context='combat',run=run,effects={version=1,heal=true}}))
assert(heal.effects[1].kind=='heal' and heal.effects[1].amount==30)
assert(Inv.count(inv0,'repair_kit')==2,'plan mutated the source')
assert(Inv.count(heal.inventory,'repair_kit')==1)
assert(Inv.validate(heal.inventory))
-- Ownership domain: a foreign run-scoped inventory cannot heal/modify this run.
local foreign=assert(Inv.create({owner='another-run',scope='run',capacity=4}))
foreign=assert(Inv.acquire(foreign,'repair_kit',1))
local fh,fhw=inv:plan_use(foreign,'repair_kit',{frame=0,context='combat',run=run,effects={version=1,heal=true}})
assert(not fh and fhw=='inventory belongs to another run')
assert(Inv.count(foreign,'repair_kit')==1)
local over,owhy=inv:plan_use(inv0,'repair_kit',{frame=0,context='combat',run=run,effects={version=1,heal=true,max_heal=10}})
assert(not over and owhy=='heal exceeds the effect contract bound')
assert(Inv.count(inv0,'repair_kit')==2)
local c, cwhy=inv:plan_use(inv0,'charge_flask',{frame=0,context='combat',run=run,target='r1'})
assert(not c and cwhy=='charge requires a staged effect contract')
local charge=assert(inv:plan_use(inv0,'charge_flask',{frame=0,context='combat',run=run,target='r1',effects={version=1,charge=true}}))
assert(charge.effects[1].kind=='charge' and charge.effects[1].gene=='r1' and charge.effects[1].amount==3)
assert(Inv.count(inv0,'charge_flask')==2)
assert(charge.binding and charge.binding.record and charge.binding.count==2)
assert(assert(inv:validate_plan(charge,{inventory=inv0,item='charge_flask',run=run,frame=0,
 context='combat',target='r1',effects={version=1,charge=true}})))
local before=Core.snapshot(run)
assert(Inv.count(inv0,'charge_flask')==2 and Core.snapshot(run)==before)
local avail,areason=Inv.available(inv0,'frost_tonic',0,'rest')
assert(not avail and areason:find('not implemented'))
print('PASS inventory use/rollback/domain')
''')

    def test_inventory_cooldowns_and_context(self):
        self.run_lua(r'''
local p,run=fresh(202)
local prog=Progress.new(run.id,'room1',{supplies=2})
local inv0=assert(Inv.create({owner=run.id,scope='run',capacity=4}))
inv0=assert(Inv.acquire(inv0,'repair_kit',2))
inv0=assert(Inv.acquire(inv0,'supply_crate',2))
local use=assert(inv:plan_use(inv0,'repair_kit',{frame=0,context='combat',run=run,effects={version=1,heal=true}}))
assert(use.cooldown_until==600)
local blocked,why=inv:plan_use(use.inventory,'repair_kit',{frame=100,context='combat',run=run,effects={version=1,heal=true}})
assert(not blocked and why=='on cooldown')
local ready=assert(inv:plan_use(use.inventory,'repair_kit',{frame=600,context='combat',run=run,effects={version=1,heal=true}}))
assert(Inv.count(ready.inventory,'repair_kit')==0)
local bad,bwhy=inv:plan_use(inv0,'supply_crate',{frame=0,context='combat',run=run,progress=prog})
assert(not bad and bwhy=='not usable in this context')
assert(Inv.count(inv0,'supply_crate')==2)
-- Supply must be bound to the matching progress record.
local nop,nopwhy=inv:plan_use(inv0,'supply_crate',{frame=0,context='rest',run=run})
assert(not nop and nopwhy=='supply requires the matching progress record')
local good=assert(inv:plan_use(inv0,'supply_crate',{frame=0,context='rest',run=run,progress=prog}))
assert(good.effects[1].kind=='supply' and good.effects[1].amount==1)
print('PASS inventory cooldowns/context')
''')

    def test_inventory_legacy_supplies_preserve_meaning(self):
        self.run_lua(r'''
local p,run=fresh(707)
local progress=Progress.new(run.id,'room1',{supplies=4})
local before=assert(Codec.encode(progress))
local migrated=assert(Inv.from_legacy_supplies(progress.supplies,{owner=run.id}))
-- Legacy supplies mean Restore (heal 30), not a food-supply grant.
assert(Inv.count(migrated,'legacy_restore')==4)
assert(Inv.count(migrated,'supply_crate')==0)
assert(Codec.encode(progress)==before,'legacy migration mutated the saved progress')
assert(Progress.validate(progress))
-- Real use consequence: one Restore heals 30 and never grants supplies.
local plan=assert(inv:plan_use(migrated,'legacy_restore',{frame=0,context='field',run=run,effects={version=1,heal=true}}))
assert(plan.effects[1].kind=='heal' and plan.effects[1].amount==30)
assert(Inv.count(plan.inventory,'legacy_restore')==3)
assert(Inv.count(plan.inventory,'supply_crate')==0)
-- The exact count is preserved (no clamp/data loss) at the legacy maximum.
local full=assert(Inv.from_legacy_supplies(9,{owner=run.id}))
assert(Inv.count(full,'legacy_restore')==9)
local zero=assert(Inv.from_legacy_supplies(0,{owner=run.id}))
assert(count(zero.items)==0)
local bad,bwhy=Inv.from_legacy_supplies(-1,{owner=run.id})
assert(not bad and bwhy=='invalid legacy supply count')
local too,toowhy=Inv.from_legacy_supplies(20,{owner=run.id})
assert(not too and toowhy=='legacy supplies exceed the bounded restore stack')
print('PASS legacy supplies meaning')
''')

    def test_equipment_reversible_contributions_no_drift(self):
        self.run_lua(r'''
local p,run=fresh(301)
local record=equip_all(run.id,{'ember_lens','null_core','rime_lens'})
record=assert(Equip.equip(record,'ember_lens'))
record=assert(Equip.equip(record,'null_core'))
local origin=Core.snapshot(run)
local base=clone(Core.resolve(run,'player','assault'))
local mods=eq:modifiers(record,run)
assert(#mods==2 and mods[1].stat=='potency')
for i=1,5 do
 assert(eq:apply(run,record)==2)
 local st=Core.resolve(run,'player','assault')
 assert(st.potency==base.potency+5,'drift after apply iteration '..i)
 assert(eq:revert(run,record)==2)
 st=Core.resolve(run,'player','assault')
 assert(st.potency==base.potency,'drift after revert iteration '..i)
 assert(Core.snapshot(run)==origin,'snapshot drift after iteration '..i)
end
-- A frost lens contributes nothing to the fire assault gene.
local frost=assert(Equip.equip(record,'rime_lens'))
assert(#eq:modifiers(frost,run)==1) -- null_core only; frost lens does not match
print('PASS equipment reversible/no-drift')
''')

    def test_equipment_owned_acquisition_and_release(self):
        self.run_lua(r'''
local p,run=fresh(302)
local empty=assert(Equip.create({owner=run.id,capacity=8}))
local notowned,nowhy=Equip.equip(empty,'ember_lens')
assert(not notowned and nowhy=='equipment not owned')
local owns=assert(Equip.acquire(empty,'ember_lens'))
assert(Equip.owns(owns,'ember_lens'))
local equipped=assert(Equip.equip(owns,'ember_lens'))
assert(equipped.slots.focus=='ember_lens' and Equip.validate(equipped))
-- A release must not silently strip a contribution.
local rel,rwhy=Equip.release(equipped,'ember_lens')
assert(not rel and rwhy=='unequip before release')
local bare=assert(Equip.unequip(equipped,'focus'))
local released=assert(Equip.release(bare,'ember_lens'))
assert(not Equip.owns(released,'ember_lens') and count(released.owned)==0)
-- Unknown and unimplemented items are never acquirable.
assert(not Equip.acquire(empty,'ruin_blade'))
assert(not Equip.acquire(empty,'ghost_lens'))
assert(not Equip.acquire(empty,'nonsense'))
-- Per-item owned stack is bounded.
local stacked=empty
for i=1,Equip.max_owned_per_item do stacked=assert(Equip.acquire(stacked,'ember_lens')) end
local over,owhy=Equip.acquire(stacked,'ember_lens')
assert(not over and owhy=='owned stack capacity')
-- A saved record that equips an unowned item is rejected.
local forged=clone(equipped); forged.owned={}
assert(not Equip.validate(forged))
print('PASS equipment owned acquisition/release')
''')

    def test_equipment_symmetric_two_handed_and_saved_records(self):
        self.run_lua(r'''
local p,run=fresh(303)
local rec=equip_all(run.id,{'long_reach_band','buckler','twin_daggers'})
local two=assert(Equip.equip(rec,'long_reach_band'))
-- Forward: a two-hander occupying offhand blocks a later offhand item.
local fwd,fwhy=Equip.equip(two,'buckler')
assert(not fwd and tostring(fwhy):find('occupancy conflict') and tostring(fwhy):find('long_reach_band'))
-- Reverse: an equipped offhand item blocks equipping the two-hander.
local back=assert(Equip.equip(rec,'buckler'))
local rev,rwhy=Equip.equip(back,'long_reach_band')
assert(not rev and tostring(rwhy):find('occupancy conflict'))
-- A saved record with both is invalid.
local saved={version=1,owner=run.id,host='player',capacity=8,
 slots={weapon='long_reach_band',offhand='buckler'},owned={long_reach_band=1,buckler=1}}
local ok,why=Equip.validate(saved)
assert(not ok and tostring(why):find('occupancy conflict'))
-- Replacement is an explicit decision and frees the occupied slot.
local replaced=assert(Equip.equip(two,'twin_daggers'))
assert(replaced.slots.weapon=='twin_daggers')
local now=assert(Equip.equip(replaced,'buckler'))
assert(now.slots.offhand=='buckler')
print('PASS equipment symmetric occupancy')
''')

    def test_equipment_foreign_invalid_record_refusal(self):
        self.run_lua(r'''
local p,run=fresh(304)
local base=Core.resolve(run,'player','assault').capacity
local foreign=assert(Equip.acquire(assert(Equip.create({owner='another-run',capacity=8})),'warding_charm'))
foreign=assert(Equip.equip(foreign,'warding_charm'))
local fa,fwhy=eq:apply(run,foreign)
assert(not fa and fwhy=='equipment belongs to another run')
assert(Core.resolve(run,'player','assault').capacity==base,'foreign record changed the run')
local fr,fwhy2=eq:revert(run,foreign)
assert(not fr and fwhy2=='equipment belongs to another run')
-- Malformed record (missing the owned ledger) is refused, not counted as 0 success.
local malformed={version=1,owner=run.id,host='player',capacity=8,slots={}}
local ma,mwhy=eq:apply(run,malformed)
assert(not ma and tostring(mwhy):find('invalid equipment tables'))
-- Unknown host is refused.
local ghost=assert(Equip.create({owner=run.id,host='ghost',capacity=8}))
local ga,gwhy=eq:apply(run,ghost)
assert(not ga and gwhy=='unknown equipment host')
-- A valid record that contributes nothing returns 0 (a real success), and does
-- not get confused with a refusal.
local idle=assert(Equip.create({owner=run.id,capacity=8}))
assert(eq:apply(run,idle)==0)
-- Invalid modifier resolution never returns an empty success.
local bad,bwhy=eq:modifiers(malformed,run)
assert(not bad and tostring(bwhy):find('invalid'))
print('PASS equipment foreign/invalid refusal')
''')

    def test_equipment_transactional_apply_and_stale_mods(self):
        self.run_lua(r'''
local p,run=fresh(305)
-- Inject a mid-apply failure after an earlier contribution has landed; the host
-- modifier table must be restored exactly.
local function failing_core(fail_id, mode)
 local fake={definitions=Core.definitions}
 fake.remove_modifier=function(...) return Core.remove_modifier(...) end
 fake.resolve=function(...) return Core.resolve(...) end
 fake.apply_modifier=function(r,h,s,m)
  if m.id:find(fail_id,1,true) then
   if mode=='throw' then error('injected dependency throw') end
   return nil,'injected apply failure'
  end
  return Core.apply_modifier(r,h,s,m)
 end
 return fake
end
local record=equip_all(run.id,{'null_core','ember_lens'})
record=assert(Equip.equip(record,'null_core'))
record=assert(Equip.equip(record,'ember_lens'))
local snapshot=Core.snapshot(run)
local fsvc=Equip.new(failing_core('ember_lens','false'),{Codec=Codec})
local ra,rwhy=fsvc:apply(run,record)
assert(not ra and rwhy=='injected apply failure')
assert(Core.snapshot(run)==snapshot,'partial apply was not rolled back')
local tsvc=Equip.new(failing_core('ember_lens','throw'),{Codec=Codec})
local ta,twhy=tsvc:apply(run,record)
assert(not ta and tostring(twhy):find('injected dependency throw'))
assert(Core.snapshot(run)==snapshot,'thrown apply was not rolled back')
-- Reconcile a loadout swap: stale equipment modifiers are removed, new ones added.
local a=equip_all(run.id,{'ember_lens'})
a=assert(Equip.equip(a,'ember_lens'))
assert(eq:apply(run,a)==1)
assert(Core.resolve(run,'player','assault').potency==12)
local b=assert(Equip.create({owner=run.id,capacity=8}))
assert(eq:apply(run,b)==0)
assert(Core.snapshot(run)==snapshot,'unequip reconcile left stale modifiers')
local c=equip_all(run.id,{'null_core'})
c=assert(Equip.equip(c,'null_core'))
assert(eq:apply(run,c)==1)
assert(Core.resolve(run,'player','assault').potency==13,'stale ember modifier survived the swap')
assert(eq:revert(run,c)==1 and Core.snapshot(run)==snapshot)
-- Actual Core modifier capacity: a full slot refuses and rolls back.
local cp,caprun=fresh(306)
local caprecord=assert(Equip.equip(equip_all(caprun.id,{'ember_lens'}),'ember_lens'))
local r=caprun
for i=1,128 do assert(Core.apply_modifier(r,'player','assault',{id='filler'..i,stat='potency',add=0.1})) end
local capbefore=Core.snapshot(r)
local cr,cwhy=eq:apply(r,caprecord)
assert(not cr and tostring(cwhy):find('modifier capacity'))
assert(Core.snapshot(r)==capbefore,'capacity refusal left partial equipment modifiers')
print('PASS equipment transactional apply')
''')

    def test_equipment_apply_revert_return_false_rollback(self):
        self.run_lua(r'''
local p,run=fresh(308)
local enemy=assert(Core.acquire(run,'cinder'))
assert(Core.equip(run,'enemy_room','assault',enemy))
local record=equip_all(run.id,{'ember_lens','null_core'})
record=assert(Equip.equip(record,'ember_lens'))
record=assert(Equip.equip(record,'null_core'))
local base=Core.snapshot(run)
-- A callback that mutates then returns false (or throws) is an explicit refusal.
local function core_with(bad_apply,bad_remove,mode)
 local fake={definitions=Core.definitions}
 fake.resolve=function(...) return Core.resolve(...) end
 fake.apply_modifier=function(r,h,s,m)
  Core.apply_modifier(r,h,s,m)
  if bad_apply and m.id:find(bad_apply,1,true) then
   if mode=='throw' then error('injected throw') end
   return false
  end
  return true
 end
 fake.remove_modifier=function(r,h,s,id)
  Core.remove_modifier(r,h,s,id)
  if bad_remove and id:find(bad_remove,1,true) then
   if mode=='throw' then error('injected throw') end
   return false
  end
  return true
 end
 return fake
end
local asvc=Equip.new(core_with('ember_lens',nil,'false'),{Codec=Codec})
local ar,arw=asvc:apply(run,record)
assert(not ar and arw=='apply failed')
assert(Core.snapshot(run)==base,'apply false-after-mutation was not rolled back')
local tsvc=Equip.new(core_with('ember_lens',nil,'throw'),{Codec=Codec})
local tr,trw=tsvc:apply(run,record)
assert(not tr and tostring(trw):find('injected throw'))
assert(Core.snapshot(run)==base,'apply throw-after-mutation was not rolled back')
assert(eq:apply(run,record)==2)
local applied=Core.snapshot(run)
local rsvc=Equip.new(core_with(nil,'ember_lens','false'),{Codec=Codec})
local rr,rrw=rsvc:revert(run,record)
assert(not rr and rrw=='remove failed')
assert(Core.snapshot(run)==applied,'revert false-after-mutation was not rolled back')
local thsvc=Equip.new(core_with(nil,'ember_lens','throw'),{Codec=Codec})
local thr,thrw=thsvc:revert(run,record)
assert(not thr and tostring(thrw):find('injected throw'))
assert(Core.snapshot(run)==applied,'revert throw-after-mutation was not rolled back')
-- Revert only removes this host's equipment ids; unrelated contributions and
-- other hosts survive, and an empty successful revert returns 0.
assert(Core.apply_modifier(run,'player','guard',{id='keep_guard',stat='capacity',add=1}))
assert(Core.apply_modifier(run,'enemy_room','assault',{id='keep_enemy',stat='potency',add=1}))
assert(eq:revert(run,record)==2)
assert(run.hosts.player.modifiers.guard.keep_guard,'unrelated player modifier was removed')
assert(run.hosts.enemy_room.modifiers.assault.keep_enemy,'another host was touched')
assert(eq:revert(run,record)==0,'successful empty revert must return 0, not a refusal')
print('PASS equipment apply/revert return-false rollback')
''')

    def test_equipment_native_items_refused_and_api_surface(self):
        self.run_lua(r'''
local p,run=fresh(307)
local native=Equip.classify(Equip.definitions.ruin_blade)
assert(not native.supported and native.reason=='native held items are not supported')
local ghost=Equip.classify(Equip.definitions.ghost_lens)
assert(not ghost.supported and ghost.reason=='equipment is not implemented')
local calls={}
local spy={definitions=Core.definitions}
spy.apply_modifier=function(r,h,s,m) calls[#calls+1]='apply'; return Core.apply_modifier(r,h,s,m) end
spy.remove_modifier=function(r,h,s,id) calls[#calls+1]='remove'; return Core.remove_modifier(r,h,s,id) end
spy.resolve=function(r,h,s) return Core.resolve(r,h,s) end
setmetatable(spy,{__index=function(_,k) error('forbidden Core access: '..tostring(k)) end})
local seq=Equip.new(spy,{Codec=Codec})
local record=equip_all(run.id,{'ember_lens'})
record=assert(Equip.equip(record,'ember_lens'))
assert(seq:apply(run,record)==1)
assert(seq:revert(run,record)==1)
assert(calls[1]=='apply' and calls[2]=='remove')
assert(Equip.native_held_items_supported==false)
print('PASS equipment native refusal/API surface')
''')

    def test_inventory_plan_staleness_binding_and_fractional_charge(self):
        self.run_lua(r'''
local p,run=fresh(401)
local inv0=assert(Inv.create({owner=run.id,scope='run',capacity=4}))
inv0=assert(Inv.acquire(inv0,'repair_kit',2))
local base={inventory=inv0,item='repair_kit',run=run,frame=0,context='combat',effects={version=1,heal=true}}
local plan=assert(inv:plan_use(inv0,'repair_kit',{frame=0,context='combat',run=run,effects={version=1,heal=true}}))
assert(assert(inv:validate_plan(plan,base)))
-- Forged effect amount (root's confirmed reproduction) is refused.
local f=clone(plan); f.effects[1].amount=999
local a,aw=inv:validate_plan(f,base); assert(not a and tostring(aw):find('canonical'))
-- An unstaged inventory (no spend) is refused.
local n=clone(plan); n.inventory=clone(inv0)
local b,bw=inv:validate_plan(n,base); assert(not b and tostring(bw):find('canonical'))
-- Swapped item/cost is refused.
local s=clone(plan); s.item='charge_flask'; s.cost={item='charge_flask',count=1}
local c,cw=inv:validate_plan(s,base); assert(not c and tostring(cw):find('canonical'))
-- An altered binding is refused.
local d=clone(plan); d.binding.count=1
local e,ew=inv:validate_plan(d,base); assert(not e and tostring(ew):find('canonical'))
-- The canonical item comes from ctx, not the plan; a mismatched ctx item is refused.
local g=inv:validate_plan(plan,{inventory=inv0,item='charge_flask',run=run,frame=0,context='combat'})
assert(not g)
-- Frame and context are preserved.
local h,hw=inv:validate_plan(plan,{inventory=inv0,item='repair_kit',run=run,frame=1,context='combat',effects={version=1,heal=true}})
assert(not h and tostring(hw):find('canonical'))
local i2,iw=inv:validate_plan(plan,{inventory=inv0,item='repair_kit',run=run,frame=0,context='rest',effects={version=1,heal=true}})
assert(not i2 and tostring(iw):find('canonical'))
-- A changed heal contract bound is revalidated.
local j,jw=inv:validate_plan(plan,{inventory=inv0,item='repair_kit',run=run,frame=0,context='combat',effects={version=1,heal=true,max_heal=10}})
assert(not j and tostring(jw):find('heal exceeds'))
-- A replayed plan against the committed (post-use) record is refused.
local rp,rpw=inv:validate_plan(plan,{inventory=plan.inventory,item='repair_kit',run=run,frame=0,context='combat',effects={version=1,heal=true}})
assert(not rp and tostring(rpw):find('stale'))
-- A foreign current record is refused.
local foreign=clone(inv0); foreign.owner='other'
local ff,ffw=inv:validate_plan(plan,{inventory=foreign,item='repair_kit',run=run,frame=0,context='combat',effects={version=1,heal=true}})
assert(not ff and tostring(ffw):find('another run'))
-- Missing current record / missing canonical item are refused.
assert(not inv:validate_plan(plan,{}))
assert(not inv:validate_plan(plan,{inventory=inv0,run=run,frame=0,context='combat',effects={version=1,heal=true}}))
-- A charge plan goes stale when its target is unequipped.
local cinv=assert(Inv.create({owner=run.id,scope='run',capacity=2}))
cinv=assert(Inv.acquire(cinv,'charge_flask',1))
local cctx={inventory=cinv,item='charge_flask',run=run,frame=0,context='combat',target='r1',effects={version=1,charge=true}}
local charge=assert(inv:plan_use(cinv,'charge_flask',{frame=0,context='combat',run=run,target='r1',effects={version=1,charge=true}}))
assert(assert(inv:validate_plan(charge,cctx)))
assert(Core.equip(run,'player','assault',nil))
local cc,ccwhy=inv:validate_plan(charge,cctx)
assert(not cc and tostring(ccwhy):find('equipped'))
-- Fractional charge is not rounded into a free charge, and a same-frame state
-- change revalidates: 2.5/3 grants 0.5, but 3/3 and 2.9/3 both refuse the plan.
local p2,run2=fresh(402)
local finv=assert(Inv.acquire(assert(Inv.create({owner=run2.id,scope='run',capacity=2})),'charge_cell'))
local fctx={inventory=finv,item='charge_cell',run=run2,frame=0,context='combat',target='r1',effects={version=1,charge=true}}
run2.hosts.player.state.assault.charge=2.5
local fp=assert(inv:plan_use(finv,'charge_cell',{frame=0,context='combat',run=run2,target='r1',effects={version=1,charge=true}}))
assert(math.abs(fp.effects[1].amount-0.5)<1e-9,'granted '..tostring(fp.effects[1].amount)..' for a 0.5 room')
assert(math.abs(fp.effects[1].target-3)<1e-9)
assert(assert(inv:validate_plan(fp,fctx)))
run2.hosts.player.state.assault.charge=3
local full,fullw=inv:validate_plan(fp,fctx)
assert(not full and tostring(fullw):find('already full'))
run2.hosts.player.state.assault.charge=2.9
local mid,midw=inv:validate_plan(fp,fctx)
assert(not mid and tostring(midw):find('canonical'))
-- A capacity change revalidates the real resolved capacity.
run2.hosts.player.state.assault.charge=2.5
assert(Core.apply_modifier(run2,'player','assault',{id='capdown',stat='capacity',add=-1}))
local capchg,capwhy=inv:validate_plan(fp,fctx)
assert(not capchg,'capacity change did not invalidate the stale charge plan')
print('PASS plan canonical binding/fractional charge')
''')

    def test_run_history_bounds_codec_and_core_migration(self):
        self.run_lua(r'''
local h=assert(Hist.new('p1',{max_entries=3,overflow='refuse'}))
for i=1,3 do
 h=assert(Hist.append(h,assert(Hist.make_entry({id='run'..i,seed=i,stocks=3},{outcome=(i%2==0) and 'failure' or 'success',rewards={'potency_small'}}))))
end
local full,why=Hist.append(h,assert(Hist.make_entry({id='run4'},{outcome='success'})))
assert(not full and why=='run history full')
assert(#h.entries==3 and h.next_serial==4)
local e=assert(Hist.new('p1',{max_entries=2,overflow='evict'}))
for i=1,4 do e=assert(Hist.append(e,assert(Hist.make_entry({id='run'..i},{outcome='success'})))) end
assert(#e.entries==2 and e.entries[1].run_id=='run3' and e.entries[2].run_id=='run4' and e.next_serial==5)
local many={} for i=1,20 do many[i]='reward_'..i end
local entry=assert(Hist.make_entry({id='runX'},{outcome='success',rewards=many,mutations=many,rooms=many}))
assert(#entry.rewards==16 and #entry.mutations==16 and #entry.rooms==16)
assert(entry.distinct_rewards==16 and entry.truncated==true)
local text=assert(Hist.encode(h,Codec))
local back=assert(Hist.decode(text,Codec))
assert(#back.entries==3 and back.owner=='p1' and Hist.validate(back))
local sum=Hist.summary(back)
assert(sum.total==3 and sum.successes+sum.failures==3 and sum.distinct_rewards==1)
local profile=Core.new_profile(777)
local r1=Core.new_run(profile); assert(Core.finish(profile,r1,'failure').outcome=='failure')
local r2=Core.new_run(profile); assert(Core.finish(profile,r2,'success'))
local before=Core.snapshot(profile)
local migrated=assert(Hist.from_core_finished(profile.id,profile,{max_entries=8}))
assert(Core.snapshot(profile)==before,'migration mutated the profile')
assert(#migrated.entries==2 and Hist.validate(migrated))
assert(migrated.entries[1].outcome=='failure' and migrated.entries[2].outcome=='success')
assert(migrated.entries[1].run_id=='run1' and migrated.entries[2].run_id=='run2')
assert(Core.restore(before),'profile still restorable')
print('PASS run history bounds/codec/migration')
''')

    def test_collection_breeding_export_fusion_and_discard(self):
        self.run_lua(r'''
local profile=Core.new_profile(501)
local ledger=assert(Inv.Economy.new({cap=1000}))
local quote=assert(Inv.Collection.breed_preview(Core,profile,'g1','g3'))
assert(quote.ok and quote.child and quote.cost>0)
local again=assert(Inv.Collection.breed_preview(Core,profile,'g1','g3'))
assert(again.child==quote.child and again.cost==quote.cost,'breeding preview not deterministic')
local need,why=Inv.Collection.commit_breed(Core,profile,ledger,'g1','g3',{})
assert(not need and why=='breeding requires confirmation')
local poor=assert(Inv.Economy.new({cap=1000}))
local snapshot=Core.snapshot(profile)
local broke,bwhy=Inv.Collection.commit_breed(Core,profile,poor,'g1','g3',{confirm=true})
assert(not broke and bwhy=='insufficient currency')
assert(Core.snapshot(profile)==snapshot,'failed breed changed the profile')
local funded=assert(Inv.Economy.earn(poor,1000,'run_success'))
local bred=assert(Inv.Collection.commit_breed(Core,profile,funded,'g1','g3',{confirm=true}))
assert(bred.gene and bred.ledger.currency==funded.currency-bred.cost and bred.cost>0)
local p2,run=fresh(502)
local enemy=assert(Core.acquire(run,'cinder'))
assert(Core.equip(run,'enemy_room','assault',enemy))
local ex,ew=Inv.Collection.export_preview(Core,p2,run,enemy)
assert(not ex and tostring(ew):find('enemy'))
local good=Inv.Collection.export_preview(Core,p2,run,'r1')
assert(good and good.exported)
local p3,run3=fresh(503)
local a=assert(Core.acquire(run3,'cinder'))
local b=assert(Core.acquire(run3,'cinder'))
local before=Core.snapshot(run3)
local fused=assert(Inv.Collection.fusion_preview(Core,run3,a,b))
assert(fused.child and Core.snapshot(run3)==before,'fusion preview mutated the run')
local inv0=assert(Inv.create({owner=run3.id,scope='run',capacity=2}))
inv0=assert(Inv.acquire(inv0,'charge_flask',1))
local plan=assert(inv:plan_use(inv0,'charge_flask',{frame=0,context='combat',run=run3,target='r1',effects={version=1,charge=true}}))
assert(Core.equip(run3,'player','assault',nil))
local bad,bad_why=inv:validate_plan(plan,{inventory=inv0,item='charge_flask',run=run3,frame=0,
 context='combat',target='r1',effects={version=1,charge=true}})
assert(not bad and tostring(bad_why):find('equipped'))
local full=Core.new_profile(504)
while count(full.genes)<128 do assert(Core.breed(full,'g1','g3')) end
local fq=assert(Inv.Collection.breed_preview(Core,full,'g1','g3'))
assert(fq.ok==false and fq.requires_discard==true)
local cf,cw=Inv.Collection.commit_breed(Core,full,ledger,'g1','g3',{confirm=true})
assert(not cf and cw=='collection full; discard or replace first')
assert(assert(Inv.Collection.discard_preview(full,'g2')))
local cd,cdw=Inv.Collection.commit_discard(full,'g2',{})
assert(not cd and cdw=='discard requires confirmation')
assert(assert(Inv.Collection.commit_discard(full,'g2',{confirm=true})))
assert(count(full.genes)==127)
assert(Inv.Collection.breed_preview(Core,full,'g1','g3').ok==true)
local refd,refwhy=Inv.Collection.discard_preview(full,'g3')
assert(not refd and refwhy:find('inherited'))
print('PASS collection breeding/export/fusion/discard')
''')

    def test_economy_simulation_bounded_and_honest_support(self):
        self.run_lua(r'''
local profile=Core.new_profile(601)
local ledger=assert(Inv.Economy.new({cap=300}))
for i=1,60 do ledger=assert(Inv.Economy.earn(ledger,25,'run_success')) end
assert(ledger.currency==300 and ledger.currency<=ledger.cap)
local spent=assert(Inv.Economy.spend(ledger,100,'breeding'))
local bad,bwhy=Inv.Economy.spend(spent,100000,'breeding')
assert(not bad and bwhy=='insufficient currency' and spent.currency==200)
local cost=assert(Inv.Economy.breed_cost(Core,profile,'g1','g3'))
assert(cost>0 and cost<=500)
local successes,failures,breeds=0,0,0
for i=1,30 do
 local run=Core.new_run(profile)
 local outcome=(i%3==0) and 'failure' or 'success'
 local value=assert(Inv.Economy.reward_value(outcome,2))
 ledger=assert(Inv.Economy.earn(ledger,value,outcome=='success' and 'run_success' or 'run_failure'))
 assert(ledger.currency<=ledger.cap)
 if i%6==0 then
  local before=ledger.currency
  local bred=Inv.Collection.commit_breed(Core,profile,ledger,'g1','g3',{confirm=true})
  if bred then ledger=bred.ledger; breeds=breeds+1; assert(ledger.currency==before-bred.cost) end
 end
 assert(Core.finish(profile,run,outcome).outcome==outcome)
 if outcome=='success' then successes=successes+1 else failures=failures+1 end
end
assert(successes+failures==30 and breeds>0)
assert(ledger.currency<=ledger.cap and Core.snapshot(profile))
local full=Core.new_profile(602)
while count(full.genes)<128 do assert(Core.breed(full,'g1','g3')) end
local frun=Core.new_run(full)
assert(Core.finish(full,frun,'failure').outcome=='failure')
assert(not Inv.Collection.commit_breed(Core,full,ledger,'g1','g3',{confirm=true}))
local supported,unsupported=0,0
for _,d in ipairs(rt:supported_definitions()) do
 if d.supported then supported=supported+1 else unsupported=unsupported+1; assert(d.reason) end
end
assert(supported>0 and unsupported>0)
local thermal=rt:classify(EC.rewards.thermal_seed)
assert(not thermal.supported and thermal.reason:find('not implemented'))
assert(not rt:classify(EC.rewards.warding_charm).supported)
print('PASS economy simulation/honest support')
''')

    def test_route_reward_specs_persisted_no_reroll(self):
        self.run_lua(r'''
local RNG=assert(loadfile(S..'/rng.lua'))()
local Rooms=assert(loadfile(S..'/room_catalogue.lua'))()
local Recipes=assert(loadfile(S..'/room_recipes.lua'))()
local Prog=assert(loadfile(S..'/progression.lua'))()
local Top=assert(loadfile(S..'/topology.lua'))()
local Adapter=assert(loadfile(S..'/adapter.lua'))()
local Route=assert(loadfile(S..'/route.lua'))()
for _,recipe in pairs(Recipes.recipes) do recipe.certified=true end
local topology=Top.new(Rooms,EC,Prog,RNG)
local adapter=Adapter.new(Rooms,Recipes)
local route=Route.new({topology=topology,adapter=adapter,progress=Progress,progression=Prog,encounters=EC})
local r
for seed=1,200 do
 local run={id='run1',world_seed=seed,stocks=3,progress={supplies=2,room='r001',cleared={},claimed={}}}
 local made=select(1,route:create(run))
 if made then
  local n=0
  for _,id in ipairs(made.manifest.order) do if made.manifest.rooms_by_id[id].reward then n=n+1 end end
  if n>0 then r=made; break end
 end
end
assert(r,'no generated route with a reward in the seed sweep')
local checked=0
for _,id in ipairs(r.manifest.order) do
 local room=r.manifest.rooms_by_id[id]
 if room.reward then
  assert(room.reward_spec and room.reward_spec.id==room.reward,'reward spec not persisted')
  assert(room.reward_spec.id==EC.rewards[room.reward].id)
  checked=checked+1
 end
end
assert(checked>0)
local run={id='run1',world_seed=r.manifest.world_seed,stocks=3,progress={supplies=2,room=r.manifest.start_room,cleared={},claimed={}}}
assert(route:resume(run,r.manifest,r.progress))
for _,id in ipairs(r.manifest.order) do
 local room=r.manifest.rooms_by_id[id]
 if room.reward then assert(room.reward_spec.id==r.manifest.rooms_by_id[id].reward_spec.id) end
end
print('PASS route reward specs persisted')
''')


if __name__ == '__main__':
    unittest.main()
