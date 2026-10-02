#!/usr/bin/env python3
"""Exercise the real gene-behavior and action-transaction Lua modules.

Runs the actual Lua files with a deterministic fake native world. The fake world
proves the transaction/concurrency contract (phases, targeted refunds, ownership,
slot-scoped earning, cleanup); it does not prove native collision, hitstop or
controller play. Prototype gene definitions are registered into the in-memory
Core table so the real charge/spend APIs can be exercised for the unoffered
families; production admission is still cinder/rime only.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite'
BEHAVIORS = RT / 'gene_behaviors.lua'
CORE = RT / 'core.lua'
ACTIONS = RT / 'gene_actions.lua'

TEST = r'''
local B = assert(loadfile(arg[1]))()
local Core = assert(loadfile(arg[2]))()
local GA = assert(loadfile(arg[3]))()

-- Register unoffered prototype definitions in-memory only so the real Core
-- charge/spend APIs can drive every family. cinder/rime stay authoritative.
local function register_prototypes()
  for id, g in pairs(B.genes) do
    if not Core.definitions[id] then
      local variants = {}
      for slot, spec in pairs(g.placements) do
        variants[slot] = {name = id .. '_' .. slot, trigger = spec.trigger,
          action = spec.action, category = spec.category}
      end
      Core.definitions[id] = {version = 1, name = id, family = g.family, recipe = 'TestOnly', variants = variants}
    end
  end
end
register_prototypes()

local function clone(v)
  if type(v) ~= 'table' then return v end
  local o = {}
  for k, x in pairs(v) do o[k] = clone(x) end
  return o
end

local function scene(seed)
  local p = Core.new_profile(seed)
  local r = Core.new_run(p)
  local obs = {player = {x = 0, y = 0, facing = 1}, enemy = {x = 5, y = 0, facing = -1}}
  local st = {occluded = false, can_start = true, refuse_effect = false, throw_effect = false,
    refuse_movement = false, refuse_release = false, replace_called = false, calls = {},
    refuse_host = nil, on_apply_effect = nil, on_apply_guard = nil, on_apply_conversion = nil,
    query_host = nil}
  local holder = {run = r}
  local w = {}
  w.get_run = function() return holder.run end
  w.replace_run = function() st.replace_called = true end
  w.can_start = function() if st.can_start == false then return false, 'not free' end return true end
  w.observe = function(host)
    local o = obs[host]
    if not o then
      -- Arbitrary named targets (route-saturation fixtures) read as a live
      -- opponent so the engine's range/occlusion policy can run.
      return {host = host, x = 5, y = 0, facing = -1, alive = true}
    end
    return {host = host, x = o.x, y = o.y, facing = o.facing or 1, alive = o.alive ~= false,
      reflecting = o.reflecting, shielding = o.shielding}
  end
  w.query = function(host)
    if st.query_host then
      local e = obs.enemy
      return {host = st.query_host, x = e.x, y = e.y, facing = -1, alive = true}
    end
    local hx = obs[host] and obs[host].x or 0
    local chosen
    for h, o in pairs(obs) do
      if h ~= host and o.alive ~= false then
        if not chosen or math.abs(o.x - hx) < math.abs(chosen.x - hx) then
          chosen = {host = h, x = o.x, y = o.y, facing = o.facing or 1, alive = true,
            reflecting = o.reflecting, shielding = o.shielding}
        end
      end
    end
    return chosen
  end
  w.occluded = function() return st.occluded end
  w.apply_effect = function(rr, req)
    st.calls[#st.calls + 1] = {seam = 'apply_effect', req = req}
    if st.on_apply_effect then st.on_apply_effect(rr, req) end
    if st.throw_effect then error('native explosion') end
    if st.refuse_effect or st.refuse_host == req.host then return false, 'refused' end
    return true
  end
  w.apply_movement = function(rr, req)
    st.calls[#st.calls + 1] = {seam = 'apply_movement', req = req}
    if st.refuse_movement then return false, 'refused' end
    return true
  end
  w.apply_status = function(rr, req)
    st.calls[#st.calls + 1] = {seam = 'apply_status', req = req}
    return true
  end
  w.apply_guard = function(rr, req)
    st.calls[#st.calls + 1] = {seam = 'apply_guard', req = req}
    if st.on_apply_guard then st.on_apply_guard(rr, req) end
    local mid = 'guard:' .. req.move_id
    assert(Core.apply_modifier(rr, req.host, req.slot, {id = mid, stat = 'potency', add = 5, expires = rr.frame + 300}))
    return true, {contrib = {kind = 'guard', id = mid}}
  end
  w.release_guard = function(rr, contrib)
    st.calls[#st.calls + 1] = {seam = 'release_guard'}
    if st.refuse_release then return false, 'release refused' end
    assert(Core.remove_modifier(rr, contrib.host, contrib.slot, contrib.id))
    return true
  end
  w.apply_conversion = function(rr, req)
    st.calls[#st.calls + 1] = {seam = 'apply_conversion', req = req}
    if st.on_apply_conversion then st.on_apply_conversion(rr, req) end
    local mid = 'conv:' .. req.move_id
    assert(Core.apply_modifier(rr, req.host, req.slot, {id = mid, stat = 'gain', add = 1, expires = rr.frame + 300}))
    return true, {contrib = {kind = 'conversion', id = mid}}
  end
  w.release_conversion = function(rr, contrib)
    st.calls[#st.calls + 1] = {seam = 'release_conversion'}
    if st.refuse_release then return false, 'release refused' end
    assert(Core.remove_modifier(rr, contrib.host, contrib.slot, contrib.id))
    return true
  end
  return r, obs, st, w, holder
end

local function charge(r, host, kind, n, prefix, target)
  for i = 1, n do
    local ev = {host = host, kind = kind, move_id = (prefix or 'x') .. ':' .. i, lineage = 'direct'}
    if target then ev.target = target end
    Core.on_event(r, ev)
  end
end

local function install(r, kind, host, slot)
  local id = assert(Core.acquire(r, kind))
  assert(Core.equip(r, host, slot, id))
  return id
end

local function seam_calls(st, seam)
  local n = 0
  for _, c in ipairs(st.calls) do if c.seam == seam then n = n + 1 end end
  return n
end

-- 1. Contract, honest status counts and unsupported spend policy.
assert(B.validate(B))
assert(B.from_core(Core))
local status = B.status()
assert(status.families == 6 and status.genes == 12, 'content counts')
assert(status.offered == 2 and status.prototype_pending_native == 10, 'offered/prototype split')
assert(status.reactions == 6 and status.reactions_modelled == 1, 'reaction counts')
do
  local bad = clone(B)
  bad.genes.cinder.placements.assault.spend = 'start'
  assert(not pcall(B.validate, bad), 'unsupported spend point accepted')
end

-- 2. Cost, spend point, targeted refund (findings 2 and 4).
do
  local r, obs, st, w = scene(2001)
  local ga = GA.new(Core, B, w)
  local before = assert(Core.snapshot(r))
  local rec, why = ga:begin('player', 'assault')
  assert(not rec and why == 'not ready', tostring(why))
  assert(Core.snapshot(r) == before, 'unready begin mutated the run')
  charge(r, 'player', 'direct_hit', 3, 'm')
  local active = assert(ga:begin('player', 'assault'))
  assert(active.phase == 'startup' and r.hosts.player.state.assault.charge == 3, 'spent during startup')
  local first = seam_calls(st, 'apply_effect')
  ga:advance()
  assert(r.hosts.player.state.assault.charge == 0, 'charge not spent at release')
  for _ = 1, 8 do Core.tick(r, 1); ga:advance() end
  assert(seam_calls(st, 'apply_effect') == first + 1, 'repeat multihit applied more than once')
  assert(#ga:provenance() == 1, 'provenance missing')

  -- Unrelated state must survive a refused action's refund.
  assert(Core.apply_modifier(r, 'player', 'guard', {id = 'unrelated', stat = 'potency', add = 7}))
  local guard_potency = Core.resolve(r, 'player', 'guard').potency
  assert(Core.equip(r, 'player', 'traversal', 'r3'))
  charge(r, 'player', 'move', 2, 'tr')
  local traversal_charge = r.hosts.player.state.traversal.charge
  Core.tick(r, 200)
  charge(r, 'player', 'direct_hit', 3, 'ref')
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(Core.resolve(r, 'player', 'guard').potency == guard_potency, 'refund erased unrelated modifier')
  assert(r.hosts.player.state.traversal.charge == traversal_charge, 'refund erased unrelated charge')
  assert(r.hosts.player.state.assault.charge == 3, 'refund did not restore the action cost')
  assert(Core.ability(r, 'player', 'assault').ready, 'refund did not restore readiness')
  assert(ga.stats.refunded == 1, 'refund not counted')
  assert(not st.replace_called, 'engine replaced the whole run')
  st.refuse_effect = false
  Core.remove_modifier(r, 'player', 'guard', 'unrelated')

  -- A throwing native callback is a refusal, not a silent success.
  Core.tick(r, 200)
  charge(r, 'player', 'direct_hit', 3, 'thr')
  st.throw_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.hosts.player.state.assault.charge == 3, 'throwing callback leaked the charge')
  assert(#ga:view() == 0, 'throwing callback left a live record')
  st.throw_effect = false
end

-- 3. Simultaneous actors: one refusal must not disturb another action's run.
do
  local r, obs, st, w = scene(2002)
  local ga = GA.new(Core, B, w)
  install(r, 'cinder', 'enemy', 'assault')
  charge(r, 'player', 'direct_hit', 3, 'p')
  charge(r, 'enemy', 'direct_hit', 3, 'e')
  assert(Core.equip(r, 'player', 'traversal', 'r3'))
  charge(r, 'player', 'move', 2, 'pt')
  local third = r.hosts.player.state.traversal.charge
  local run_id = r.id
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  assert(ga:begin('enemy', 'assault'))
  ga:advance()
  assert(r.id == run_id, 'run identity changed across simultaneous actions')
  assert(r.hosts.player.state.assault.charge == 3, 'player refusal not refunded')
  assert(r.hosts.enemy.state.assault.charge == 3, 'enemy refusal not refunded')
  assert(r.hosts.player.state.traversal.charge == third, 'third slot charge disturbed')
  assert(#ga:view() == 0, 'records not cleaned after simultaneous refusals')
  assert(not st.replace_called, 'replace_run used for a refund')
  -- Now let the enemy succeed while the player refuses.
  st.refuse_effect = false
  Core.tick(r, 200)
  charge(r, 'player', 'direct_hit', 3, 'p2')
  charge(r, 'enemy', 'direct_hit', 3, 'e2')
  st.refuse_effect = true
  assert(ga:begin('enemy', 'assault'))
  -- player has no charge headroom? ensure ready
  st.refuse_effect = false
  local ok = ga:begin('player', 'assault')
  if ok then ga:advance() else assert(false, 'player action refused unexpectedly') end
  Core.tick(r, 1)
  ga:advance()
  local player
  for _, e in ipairs(ga:provenance()) do if e.source == 'player' then player = e end end
  assert(player and player.spent and player.applied, 'player action did not complete')
end

-- 4. Equipment change cancels a pending action instead of spending a replacement.
do
  local r, obs, st, w = scene(2003)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, glacier = true}})
  install(r, 'glacier', 'player', 'assault')
  charge(r, 'player', 'direct_hit', 6, 'g')
  local cost = Core.ability(r, 'player', 'assault').cost
  assert(ga:begin('player', 'assault'))
  Core.tick(r, 2)
  ga:advance()
  assert(r.hosts.player.state.assault.charge == cost, 'spent during startup')
  -- Swap in a different gene before release.
  local rime = install(r, 'rime', 'player', 'assault')
  Core.tick(r, 4)
  ga:advance()
  local rime_charge = r.hosts.player.state.assault.charge
  assert(rime_charge == 0, 'replacement gene charge was spent: ' .. tostring(rime_charge))
  assert(r.hosts.player.slots.assault == rime, 'replacement gene not equipped')
  assert(#ga:view() == 0 and #ga:provenance() == 0, 'swap did not cancel cleanly')
  -- The uncharged replacement must not expose false readiness.
  assert(not Core.ability(r, 'player', 'assault').ready, 'replacement gene exposed false readiness')
  local again, rwhy = ga:begin('player', 'assault')
  assert(not again and rwhy == 'not ready', 'replacement action allowed: ' .. tostring(rwhy))
end

-- 5. Startup window, dodge, and fail-closed free-state/occlusion seams.
do
  local r, obs, st, w = scene(2004)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, glacier = true}})
  install(r, 'glacier', 'player', 'assault')
  charge(r, 'player', 'direct_hit', 6, 'g')
  local cost = Core.ability(r, 'player', 'assault').cost
  assert(ga:begin('player', 'assault'))
  Core.tick(r, 1)
  ga:advance()
  assert(r.hosts.player.state.assault.charge == cost, 'spent during startup')
  obs.enemy.x = 100
  Core.tick(r, 5)
  ga:advance()
  assert(r.hosts.player.state.assault.charge == cost, 'dodge did not preserve charge')
  assert(#ga:view() == 0, 'dodge not cleaned up')
  obs.enemy.x = 5
  -- Free-state seam is promised: fail closed when absent.
  local saved = w.can_start
  w.can_start = nil
  local plan, why = ga:preflight('player', 'assault')
  assert(not plan and why == 'free-state seam missing', tostring(why))
  w.can_start = saved
  -- Occlusion seam is promised for line specs.
  saved = w.occluded
  w.occluded = nil
  plan, why = ga:preflight('player', 'assault')
  assert(not plan and why == 'occlusion seam missing', tostring(why))
  w.occluded = saved
  st.occluded = true
  plan, why = ga:preflight('player', 'assault')
  assert(not plan and why == 'target occluded', tostring(why))
  st.occluded = false
  obs.enemy.reflecting = true
  plan, why = ga:preflight('player', 'assault')
  assert(not plan and why == 'target reflects', tostring(why))
  obs.enemy.reflecting = nil
  obs.enemy.shielding = true
  plan, why = ga:preflight('player', 'assault')
  assert(not plan and why == 'target shielded', tostring(why))
  obs.enemy.shielding = nil
  -- Control route uses the status seam after the startup window.
  local saved_apply = w.apply_status
  w.apply_status = nil
  plan, why = ga:preflight('player', 'assault')
  assert(not plan and why == 'native apply_status seam missing', tostring(why))
  w.apply_status = saved_apply
  assert(ga:begin('player', 'assault'))
  Core.tick(r, 6)
  ga:advance()
  assert(seam_calls(st, 'apply_status') >= 1, 'control route did not use apply_status')
end

-- 6. Refund restores the mark a refused reaction consumed.
do
  local r, obs, st, w = scene(2005)
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'defend', 3, 'mk')
  assert(ga:begin('player', 'guard'))
  ga:advance()
  assert(r.marks.enemy, 'rime mark missing')
  Core.tick(r, 1)
  ga:advance()
  charge(r, 'player', 'direct_hit', 3, 'th')
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.marks.enemy and r.marks.enemy.source == 'player', 'refused reaction erased the mark')
  assert(r.hosts.player.state.assault.charge == 3, 'refused reaction did not refund')
  st.refuse_effect = false
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(not r.marks.enemy, 'successful thermal shock did not consume the mark')
end

-- 7. Slot-scoped earning: a per_target gene must not inflate a per_move gene.
do
  local r, obs, st, w = scene(2006)
  -- Make emberline traversal charge from direct_hit in Core too, so the two
  -- slots share one move kind but differ in authored earning policy.
  Core.definitions.emberline.variants.traversal.trigger = 'direct_hit'
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, brand = true, emberline = true}})
  assert(Core.equip(r, 'player', 'guard', nil))
  install(r, 'brand', 'player', 'assault')     -- per_target
  install(r, 'emberline', 'player', 'traversal') -- per_move
  local a = ga:on_event({host = 'player', kind = 'direct_hit', move_id = 'mv', target = 'enemy'})
  local brand1 = r.hosts.player.state.assault.charge
  local ember1 = r.hosts.player.state.traversal.charge
  assert(a > 0 and brand1 > 0 and ember1 > 0, 'first target did not charge')
  local b = ga:on_event({host = 'player', kind = 'direct_hit', move_id = 'mv', target = 'enemy2'})
  assert(b > 0, 'second target did not charge')
  assert(r.hosts.player.state.assault.charge > brand1, 'per_target slot did not earn per target')
  assert(r.hosts.player.state.traversal.charge == ember1, 'per_move slot was inflated by per_target keying')
  -- Reaction, projectile and reflected provenance never charge.
  assert(ga:on_event({host = 'player', kind = 'direct_hit', move_id = 'r', target = 'enemy', reaction = true}) == 0)
  assert(ga:on_event({host = 'player', kind = 'direct_hit', move_id = 'p', target = 'enemy', projectile = true}) == 0)
  assert(ga:on_event({host = 'player', kind = 'direct_hit', move_id = 'f', target = 'enemy', reflected = true}) == 0)
end

-- 8. Contribution ownership: promised release seam, expiry, retry, capacity.
do
  local r, obs, st, w = scene(2007)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, bulwark = true, glacier = true}})
  install(r, 'bulwark', 'player', 'guard')
  local base = Core.resolve(r, 'player', 'guard').potency
  -- Missing release seam must refuse activation before any spend.
  local saved = w.release_guard
  w.release_guard = nil
  charge(r, 'player', 'defend', 7, 'd')
  local plan, why = ga:preflight('player', 'guard')
  assert(not plan and why == 'release seam missing', tostring(why))
  w.release_guard = saved
  assert(Core.ability(r, 'player', 'guard').ready)
  assert(ga:begin('player', 'guard'))
  ga:advance()
  assert(Core.resolve(r, 'player', 'guard').potency == base + 5, 'guard contribution not applied')
  Core.tick(r, 1)
  ga:advance()
  assert(ga:contribution_count() == 1 and #ga:provenance() == 1, 'settled contribution not owned')
  -- Release refuses: handle retained and retried, then reported stuck.
  st.refuse_release = true
  Core.tick(r, 200)
  ga:advance()
  assert(ga:contribution_count() == 1, 'refused release forgot the handle')
  Core.tick(r, 200)
  ga:advance()
  Core.tick(r, 200)
  ga:advance()
  assert(ga:contribution_count() == 1, 'refused handle not retained through retries')
  assert(ga.stats.stuck >= 1, 'stuck contribution not reported')
  -- Room leave confirms release and reports zero refused.
  st.refuse_release = false
  local released, refused = ga:on_room_leave()
  assert(released == 1 and refused == 0, 'room leave did not confirm release')
  assert(Core.resolve(r, 'player', 'guard').potency == base, 'room leave drifted potency')
  assert(ga:contribution_count() == 0, 'room leave left a handle')
end

do
  -- Contribution capacity is enforced before offering.
  local r, obs, st, w = scene(2008)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, bulwark = true, glacier = true},
    caps = {contributions = 1}})
  install(r, 'bulwark', 'player', 'guard')
  charge(r, 'player', 'defend', 7, 'd')
  assert(ga:begin('player', 'guard'))
  ga:advance()
  Core.tick(r, 1)
  ga:advance()
  assert(ga:contribution_count() == 1, 'first contribution not owned')
  install(r, 'glacier', 'player', 'guard')
  Core.tick(r, 200)
  charge(r, 'player', 'defend', 7, 'd2')
  local plan, why = ga:preflight('player', 'guard')
  assert(not plan and why == 'contribution capacity', tostring(why))
end

-- 9. Movement route, refusal refund and enemy parity.
do
  local r, obs, st, w = scene(2009)
  local ga = GA.new(Core, B, w)
  install(r, 'cinder', 'player', 'traversal')
  charge(r, 'player', 'move', 3, 'mv')
  assert(ga:begin('player', 'traversal'))
  ga:advance()
  assert(seam_calls(st, 'apply_movement') == 1, 'movement route not used')
  Core.tick(r, 1)
  ga:advance()
  Core.tick(r, 200)
  charge(r, 'player', 'move', 3, 'mv2')
  st.refuse_movement = true
  assert(ga:begin('player', 'traversal'))
  ga:advance()
  assert(r.hosts.player.state.traversal.charge == 3, 'movement refusal lost charge')
  st.refuse_movement = false
  install(r, 'cinder', 'enemy', 'assault')
  charge(r, 'enemy', 'direct_hit', 3, 'e')
  assert(ga:begin('enemy', 'assault'))
  ga:advance()
  Core.tick(r, 1)
  ga:advance()
  local enemy
  for _, e in ipairs(ga:provenance()) do if e.source == 'enemy' then enemy = e end end
  assert(enemy and enemy.target == 'player', 'enemy parity provenance wrong')
end

-- 10. Caps: record, provenance and bounded lifetime.
do
  local r, obs, st, w = scene(2010)
  local ga = GA.new(Core, B, w, {caps = {records = 1, provenance = 1, lifetime = 2}})
  install(r, 'cinder', 'player', 'traversal')
  charge(r, 'player', 'direct_hit', 3, 'a')
  charge(r, 'player', 'move', 3, 't')
  assert(ga:begin('player', 'assault'))
  local rec, why = ga:begin('player', 'traversal')
  assert(not rec and why == 'action record cap', tostring(why))
  Core.tick(r, 3)
  ga:advance()
  assert(#ga:view() == 0, 'bounded lifetime did not cancel the action')
  assert(#ga:provenance() <= 1, 'provenance cap exceeded')
end

-- 12. A slot swap during the native callback refunds the original gene only.
do
  local r, obs, st, w = scene(3001)
  local ga = GA.new(Core, B, w)
  local original = r.hosts.player.slots.assault
  charge(r, 'player', 'direct_hit', 3, 'sw')
  local cost = Core.ability(r, 'player', 'assault').cost
  local replacement
  st.on_apply_effect = function(rr) replacement = install(rr, 'rime', 'player', 'assault') end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(replacement and r.hosts.player.slots.assault == replacement, 'swap hook did not equip')
  assert(r.runtime[replacement].charge == 0, 'replacement gene received the refund')
  assert(r.runtime[original].charge == cost, 'original gene was not refunded')
  assert(r.runtime[original].ready_at == 0, 'original readiness was not restored')
  assert(#ga:view() == 0, 'swap action not cleaned up')
end

-- 13. Target-mark rollback compares the owned value and leaves a concurrent mark.
do
  local r, obs, st, w = scene(3002)
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'defend', 3, 'mk')
  assert(ga:begin('player', 'guard'))
  ga:advance()
  Core.tick(r, 1)
  ga:advance()
  assert(r.marks.enemy and r.marks.enemy.source == 'player', 'rime mark missing')
  -- Another host writes a mark through Core while our strike is in flight.
  install(r, 'rime', 'ally', 'guard')
  charge(r, 'ally', 'defend', 3, 'ag')
  charge(r, 'player', 'direct_hit', 3, 'th')
  st.on_apply_effect = function(rr) assert(Core.activate(rr, 'ally', 'guard', {target = 'enemy'})) end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.marks.enemy and r.marks.enemy.source == 'ally', 'concurrent foreign mark was erased')
  st.on_apply_effect = nil
  st.refuse_effect = false
  -- A consumed foreign mark is restored when nobody else changes it.
  Core.tick(r, 200)
  local ally_guard = r.hosts.ally.state.guard; ally_guard.charge = 3; ally_guard.ready_at = 0
  assert(Core.activate(r, 'ally', 'guard', {target = 'enemy'}))
  charge(r, 'player', 'direct_hit', 3, 'th2')
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.marks.enemy and r.marks.enemy.source == 'ally', 'consumed foreign mark not restored')
  st.refuse_effect = false
end

-- 14. Two profiles both expose `run1`; identity is the run instance, not the id.
do
  local pA = Core.new_profile(4001); local rA = Core.new_run(pA)
  local pB = Core.new_profile(4002); local rB = Core.new_run(pB)
  assert(rA.id == rB.id and rA.id == 'run1', 'fixture must share run1')
  local r, obs, st, w, holder = scene(4000)
  install(rA, 'cinder', 'player', 'assault'); charge(rA, 'player', 'direct_hit', 3, 'a')
  install(rB, 'cinder', 'player', 'assault'); charge(rB, 'player', 'direct_hit', 3, 'b')
  local ga = GA.new(Core, B, w)
  holder.run = rA
  assert(ga:begin('player', 'assault'))
  holder.run = rB
  ga:advance()
  assert(rB.hosts.player.state.assault.charge == 3, 'spent a gene from the wrong run instance')
  assert(rA.hosts.player.state.assault.charge == 3, 'original run state disturbed')
  assert(#ga:view() == 0, 'cross-run pending action not cancelled')
end

-- 15. Contribution capacity counts pending reservations, not only settled handles.
do
  local r, obs, st, w = scene(3003)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, bulwark = true},
    caps = {contributions = 1}})
  install(r, 'bulwark', 'player', 'guard')
  install(r, 'bulwark', 'enemy', 'guard')
  charge(r, 'player', 'defend', 7, 'dp')
  charge(r, 'enemy', 'defend', 7, 'de')
  assert(ga:begin('player', 'guard'))
  local rec, why = ga:begin('enemy', 'guard')
  assert(not rec and why == 'contribution capacity', tostring(why))
  ga:advance(); Core.tick(r, 1); ga:advance()
  assert(ga:contribution_count() == 1, 'first contribution not owned')
  Core.tick(r, 200)
  charge(r, 'enemy', 'defend', 7, 'de2')
  local plan2, why2 = ga:preflight('enemy', 'guard')
  assert(not plan2 and why2 == 'contribution capacity', tostring(why2))
  -- Releasing the handle frees capacity again (no permanent stuck reservation).
  Core.tick(r, 400); ga:advance()
  assert(ga:contribution_count() == 0, 'handle not expired')
  Core.tick(r, 200); charge(r, 'enemy', 'defend', 7, 'de3')
  local plan3 = ga:preflight('enemy', 'guard')
  assert(plan3, 'capacity was not freed after release')
end

-- 16. Cleanup during the native callback must not orphan the effect handle.
do
  local r, obs, st, w = scene(3004)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, bulwark = true}})
  install(r, 'bulwark', 'player', 'guard')
  local base = Core.resolve(r, 'player', 'guard').potency
  charge(r, 'player', 'defend', 7, 'cl')
  assert(ga:begin('player', 'guard'))
  st.on_apply_guard = function() ga:on_room_leave() end
  ga:advance()
  st.on_apply_guard = nil
  assert(ga:contribution_count() == 0, 'reentrant cleanup orphaned a handle')
  assert(Core.resolve(r, 'player', 'guard').potency == base, 'reentrant cleanup left the modifier')
  assert(#ga:view() == 0, 'reentrant cleanup left the record')
end

-- 17. convert/siphon release through release_conversion, not release_convert.
do
  local r, obs, st, w = scene(3005)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, convert = true}})
  install(r, 'convert', 'player', 'guard')
  local base = Core.resolve(r, 'player', 'guard').gain
  charge(r, 'player', 'defend', 6, 'cv')
  assert(ga:begin('player', 'guard'))
  ga:advance()
  assert(seam_calls(st, 'apply_conversion') == 1, 'conversion route not used')
  Core.tick(r, 1); ga:advance()
  assert(ga:contribution_count() == 1, 'conversion handle not owned')
  Core.tick(r, 400); ga:advance()
  assert(seam_calls(st, 'release_conversion') == 1, 'release_conversion seam not used')
  assert(ga:contribution_count() == 0 and Core.resolve(r, 'player', 'guard').gain == base,
    'conversion cleanup drifted')
  local saved = w.release_conversion
  w.release_conversion = nil
  Core.tick(r, 200); charge(r, 'player', 'defend', 6, 'cv2')
  local plan, why = ga:preflight('player', 'guard')
  assert(not plan and why == 'release seam missing', tostring(why))
  w.release_conversion = saved
end

-- 19. Free-state is re-checked at the spend point, not only at begin.
do
  local r, obs, st, w = scene(5001)
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'direct_hit', 3, 'fs')
  assert(ga:begin('player', 'assault'))
  local before = assert(Core.snapshot(r))
  st.can_start = false
  local hits = seam_calls(st, 'apply_effect')
  ga:advance()
  assert(seam_calls(st, 'apply_effect') == hits, 'hit despite losing free-state')
  assert(Core.snapshot(r) == before, 'lost free-state still mutated the run')
  assert(r.hosts.player.state.assault.charge == 3, 'charge spent without free-state')
  assert(#ga:view() == 0, 'not-free action not cleaned up')
  st.can_start = true
end

-- 20. Authored refund=never keeps the charge spent but still cleans up.
do
  local r, obs, st, w = scene(5002)
  local neverB = clone(B)
  neverB.genes.emberline.placements.assault.refund = 'never'
  local ga = GA.new(Core, neverB, w, {admitted = {cinder = true, rime = true, emberline = true}})
  install(r, 'emberline', 'player', 'assault')
  charge(r, 'player', 'direct_hit', 6, 'nv')
  assert(Core.ability(r, 'player', 'assault').ready)
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.hosts.player.state.assault.charge == 0, 'refund=never refunded the charge')
  assert(#ga:view() == 0, 'refund=never did not clean up')
  assert(ga.stats.refunded == 0, 'refund=never counted a refund')
  st.refuse_effect = false
  -- The default on_refuse policy still refunds.
  install(r, 'cinder', 'player', 'assault')
  Core.tick(r, 200)
  charge(r, 'player', 'direct_hit', 3, 'nv2')
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.hosts.player.state.assault.charge == 3, 'on_refuse did not refund')
  st.refuse_effect = false
end

-- 21. Unrelated state written during the refused callback survives.
do
  local r, obs, st, w = scene(5003)
  local ga = GA.new(Core, B, w)
  assert(Core.equip(r, 'player', 'traversal', 'r3'))
  charge(r, 'player', 'direct_hit', 3, 'ap')
  local guard_potency = Core.resolve(r, 'player', 'guard').potency
  st.on_apply_effect = function(rr)
    Core.apply_modifier(rr, 'player', 'guard', {id = 'during', stat = 'potency', add = 9})
    Core.on_event(rr, {host = 'player', kind = 'move', move_id = 'during-move', lineage = 'direct'})
  end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(Core.resolve(r, 'player', 'guard').potency == guard_potency + 9, 'callback-time modifier erased')
  assert(r.hosts.player.state.traversal.charge > 0, 'callback-time charge erased')
  assert(r.hosts.player.state.assault.charge == 3, 'action cost not refunded')
  st.on_apply_effect = nil; st.refuse_effect = false
end

-- 22. A per-host refusal and a success in one advance stay independent.
do
  local r, obs, st, w = scene(5004)
  local ga = GA.new(Core, B, w)
  install(r, 'cinder', 'enemy', 'assault')
  charge(r, 'player', 'direct_hit', 3, 'p')
  charge(r, 'enemy', 'direct_hit', 3, 'e')
  st.refuse_host = 'player'
  assert(ga:begin('player', 'assault'))
  assert(ga:begin('enemy', 'assault'))
  ga:advance()
  assert(r.hosts.player.state.assault.charge == 3, 'player refusal not refunded')
  assert(r.hosts.enemy.state.assault.charge == 0, 'enemy success did not spend')
  Core.tick(r, 1); ga:advance()
  local player, enemy
  for _, ev in ipairs(ga:provenance()) do
    if ev.source == 'player' then player = ev end
    if ev.source == 'enemy' then enemy = ev end
  end
  assert(not player, 'refused player recorded provenance')
  assert(enemy and enemy.applied, 'successful enemy missing provenance')
  st.refuse_host = nil
end

-- 23. A siphon conversion executes and releases through release_conversion.
do
  local r, obs, st, w = scene(5005)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, siphon = true}})
  install(r, 'siphon', 'player', 'assault')
  local base = Core.resolve(r, 'player', 'assault').gain
  charge(r, 'player', 'direct_hit', 6, 'si')
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(seam_calls(st, 'apply_conversion') == 1, 'siphon conversion did not execute')
  assert(st.calls[#st.calls].req.target == 'enemy', 'siphon did not target the opponent')
  Core.tick(r, 1); ga:advance()
  assert(ga:contribution_count() == 1, 'siphon handle not owned')
  Core.tick(r, 400); ga:advance()
  assert(seam_calls(st, 'release_conversion') == 1, 'siphon did not release via release_conversion')
  assert(Core.resolve(r, 'player', 'assault').gain == base, 'siphon cleanup drifted')
end

-- 24. nil->mark->nil interleaving must not resurrect an old mark.
do
  local r, obs, st, w = scene(6001)
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'defend', 3, 'og')
  assert(Core.activate(r, 'player', 'guard', {target = 'enemy'}))
  assert(r.marks.enemy and r.marks.enemy.source == 'player')
  install(r, 'rime', 'ally', 'guard'); install(r, 'cinder', 'ally', 'traversal')
  charge(r, 'ally', 'defend', 3, 'ag'); charge(r, 'ally', 'move', 3, 'at')
  charge(r, 'player', 'direct_hit', 3, 'pf')
  st.on_apply_effect = function(rr)
    assert(Core.activate(rr, 'ally', 'guard', {target = 'enemy'}))
    assert(Core.activate(rr, 'ally', 'traversal', {target = 'enemy'}))
  end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(not r.marks.enemy, 'refund resurrected a mark another action consumed')
  st.on_apply_effect = nil; st.refuse_effect = false
end

-- 25. A callback tick past the captured mark's expiry must not restore it.
do
  local r, obs, st, w = scene(6002)
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'defend', 3, 'eg')
  assert(Core.activate(r, 'player', 'guard', {target = 'enemy'}))
  local expiry = r.marks.enemy.expires
  charge(r, 'player', 'direct_hit', 3, 'ef')
  st.on_apply_effect = function(rr) Core.tick(rr, 181) end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.frame > expiry, 'fixture did not pass the expiry')
  assert(not r.marks.enemy, 'expired mark was restored')
  st.on_apply_effect = nil; st.refuse_effect = false
end

-- 26. A refused fire restores its consumed, still-live mark exactly once.
do
  local r, obs, st, w = scene(6003)
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'defend', 3, 'rg')
  assert(Core.activate(r, 'player', 'guard', {target = 'enemy'}))
  local rev_after_mark = Core.mark_revision(r, 'enemy')
  charge(r, 'player', 'direct_hit', 3, 'rf')
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.marks.enemy and r.marks.enemy.source == 'player', 'live mark not restored')
  assert(Core.mark_revision(r, 'enemy') > rev_after_mark, 'restore did not bump the revision')
  -- A second restore with the now-stale revision is refused, so the mark cannot
  -- be duplicated by an out-of-order refund.
  assert(Core.restore_mark(r, 'enemy', r.marks.enemy, rev_after_mark) == nil,
    'stale restore accepted a second time')
  st.refuse_effect = false
end

-- 27. Run identity: a restored run starts revision-free, and stale revisions are
-- refused; forget_run cleans the registry.
do
  local r, obs, st, w = scene(6004)
  charge(r, 'player', 'defend', 3, 'rr')
  assert(Core.activate(r, 'player', 'guard', {target = 'enemy'}))
  local rev = Core.mark_revision(r, 'enemy')
  assert(rev and rev > 0, 'mark revision not tracked')
  local fresh = assert(Core.restore(assert(Core.snapshot(r))))
  assert(fresh ~= r, 'restore must create a fresh run instance')
  assert(Core.mark_revision(fresh, 'enemy') == 0, 'restored run leaked revisions')
  assert(Core.restore_mark(fresh, 'enemy', {source = 'player', expires = fresh.frame + 180}, rev) == nil,
    'stale revision from another run instance accepted')
  assert(Core.mark_revision(r, 'enemy') == rev, 'original run revision changed')
  assert(Core.reset_mark_revisions(r))
  assert(Core.mark_revision(r, 'enemy') == 0, 'reset did not clear the target map')
  -- Invalidation, not merely zero: the pre-reset revision must never match.
  assert(Core.restore_mark(r, 'enemy', {source = 'player', expires = r.frame + 180}, rev) == nil,
    'stale revision became valid after reset')
  local s = r.hosts.player.state.guard; s.charge = 3; s.ready_at = 0
  assert(Core.activate(r, 'player', 'guard', {target = 'enemy'}))
  assert(Core.mark_revision(r, 'enemy') > rev, 'revision clock rewound across reset')
  assert(Core.forget_run(r))
  assert(Core.mark_revision(r, 'enemy') == 0)
end

-- 28. Real Core refuses mark capacity at the bound without mutation or spend.
do
  local r, obs, st, w = scene(7001)
  local cap = 256
  local function ready()
    local s = r.hosts.player.state.guard
    s.charge = 3; s.ready_at = 0
  end
  for i = 1, cap do
    ready()
    assert(Core.activate(r, 'player', 'guard', {target = 't' .. i}), 'core mark ' .. i .. ' refused')
  end
  assert(Core.mark_revision(r, 't' .. cap) ~= nil, 'bound target not tracked')
  ready()
  local before = assert(Core.snapshot(r))
  local a, why = Core.activate(r, 'player', 'guard', {target = 'overflow'})
  assert(not a and why == 'mark revision capacity', tostring(why))
  assert(Core.snapshot(r) == before, 'saturated core activate mutated or spent')
  assert(not r.marks.overflow, 'saturated core activate left a mark')
  -- A tracked target keeps working; an untracked mutation is still refused.
  ready()
  assert(Core.activate(r, 'player', 'guard', {target = 't1'}), 'tracked target became unusable')
  assert(Core.mark_revision(r, 't1') ~= nil)
  assert(Core.restore_mark(r, 'never_seen', {source = 'player', expires = r.frame + 180}, 0) == nil,
    'restore created an untracked target at saturation')
end

-- 29. The action engine crosses 64 targets and refuses at capacity cleanly.
do
  local r, obs, st, w = scene(7002)
  local ga = GA.new(Core, B, w)
  local cap = 256
  local function ready()
    local s = r.hosts.player.state.guard
    s.charge = 3; s.ready_at = 0
  end
  for i = 1, cap do
    ready()
    st.query_host = 'room' .. i .. '_enemy'
    assert(ga:begin('player', 'guard'), 'engine mark ' .. i .. ' refused')
    ga:advance()
    Core.tick(r, 1); ga:advance()
  end
  assert(Core.mark_revision(r, 'room1_enemy') ~= nil, 'engine marks not tracked')
  -- Beyond the bound: no charge spent, no residual mark.
  ready()
  st.query_host = 'room_overflow_enemy'
  local rec, why = ga:begin('player', 'guard')
  assert(not rec and why == 'mark revision capacity', tostring(why))
  assert(r.hosts.player.state.guard.charge == 3, 'saturated engine mark spent charge')
  assert(not r.marks.room_overflow_enemy, 'saturated engine mark left a mark')
  -- A tracked target keeps working at saturation.
  ready()
  st.query_host = 'room1_enemy'
  assert(ga:begin('player', 'guard'), 'tracked engine target refused')
  ga:advance()
  Core.tick(r, 1); ga:advance()
  -- Room leave resets the target map once nothing is pending, and invalidates
  -- all pre-leave revisions rather than rewinding the clock.
  local stale_rev = Core.mark_revision(r, 'room1_enemy')
  assert(stale_rev and stale_rev > 0)
  ga:on_room_leave()
  assert(Core.mark_revision(r, 'room1_enemy') == 0, 'leave did not clear the target map')
  assert(Core.restore_mark(r, 'room1_enemy', {source = 'player', expires = r.frame + 180}, stale_rev) == nil,
    'pre-leave revision became valid after leave')
  ready()
  st.query_host = 'room_after_enemy'
  assert(ga:begin('player', 'guard'), 'post-leave mark refused')
  ga:advance()
  assert(r.marks.room_after_enemy, 'post-leave mark not set')
  assert(Core.mark_revision(r, 'room_after_enemy') > stale_rev, 'clock rewound across leave')
  st.query_host = nil
end

-- 30. Reentrant room-leave must invalidate a pending refund's revision.
do
  local r, obs, st, w = scene(8001)
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'defend', 3, 'og')
  assert(Core.activate(r, 'player', 'guard', {target = 'enemy'}))
  assert(r.marks.enemy and r.marks.enemy.source == 'player')
  install(r, 'rime', 'ally', 'guard'); install(r, 'cinder', 'ally', 'traversal')
  charge(r, 'ally', 'defend', 3, 'ag'); charge(r, 'ally', 'move', 3, 'at')
  charge(r, 'player', 'direct_hit', 3, 'pf')
  st.on_apply_effect = function(rr)
    ga:on_room_leave()                                            -- reset target map
    assert(Core.activate(rr, 'ally', 'guard', {target = 'enemy'}))    -- mark
    assert(Core.activate(rr, 'ally', 'traversal', {target = 'enemy'})) -- consume
  end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(not r.marks.enemy, 'reentrant reset resurrected the player mark')
  st.on_apply_effect = nil; st.refuse_effect = false
  -- Fresh actions remain usable after the reset.
  local s = r.hosts.player.state.guard; s.charge = 3; s.ready_at = 0
  assert(ga:begin('player', 'guard'), 'fresh action refused after reset')
  ga:advance()
  assert(r.marks.enemy and r.marks.enemy.source == 'player', 'fresh mark not set after reset')
end

-- 31. Restore refuses a retired source host and never creates an orphan mark.
do
  local r, obs, st, w = scene(8002)
  assert(Core.restore_mark(r, 'enemy', {source = 'missing_host', expires = r.frame + 180}, 0) == nil,
    'restored a mark whose source host does not exist')
  assert(not r.marks.enemy, 'refused restore mutated marks')
  assert(Core.snapshot(r), 'run snapshot invalid after refused restore')
end

do
  -- Retiring the mark's source inside the native callback must not orphan it.
  local r, obs, st, w = scene(8003)
  local ga = GA.new(Core, B, w)
  install(r, 'rime', 'ally', 'guard')
  charge(r, 'ally', 'defend', 3, 'dm')
  assert(Core.activate(r, 'ally', 'guard', {target = 'enemy'}))
  charge(r, 'player', 'direct_hit', 3, 'df')
  st.on_apply_effect = function() r.hosts.ally = nil end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(not r.marks.enemy, 'refused restore created an orphan mark')
  assert(Core.snapshot(r), 'run snapshot invalid after callback source retirement')
  st.on_apply_effect = nil; st.refuse_effect = false
end

-- 32. A later same-slot activation owns the cooldown (default Cinder repro).
do
  local r, obs, st, w = scene(8202)
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'direct_hit', 3, 'first')
  st.on_apply_effect = function(rr)
    ga:on_room_leave()
    assert(Core.tick(rr, 90))
    charge(rr, 'player', 'direct_hit', 3, 'next')
    assert(Core.activate(rr, 'player', 'assault', {target = 'enemy'}))
    assert(rr.hosts.player.state.assault.ready_at == 180)
  end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.hosts.player.state.assault.ready_at == 180,
    'refund clobbered the newer activation cooldown')
  assert(r.hosts.player.state.assault.charge == 0,
    'refund clobbered the newer activation charge')
  assert(ga.stats.refund_refused == 1, 'refused conditional restore was not reported')
  st.on_apply_effect = nil; st.refuse_effect = false
end

-- 33. Same-frame equal ready_at ABA is rejected by the spend revision. Cooldown
-- makes a natural second activation impossible, so this re-arms the slot as a
-- fixture; both activations land on the same frame+90 value.
do
  local r, obs, st, w = scene(8203)
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'direct_hit', 3, 'first')
  st.on_apply_effect = function(rr)
    local s = rr.hosts.player.state.assault
    s.charge = 3; s.ready_at = 0
    assert(Core.activate(rr, 'player', 'assault', {target = 'enemy'}))
    assert(rr.hosts.player.state.assault.ready_at == 90)
  end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.hosts.player.state.assault.ready_at == 90,
    'same-frame newer cooldown was clobbered')
  assert(r.hosts.player.state.assault.charge == 0)
  assert(ga.stats.refund_refused == 1, 'refused conditional restore was not reported')
  st.on_apply_effect = nil; st.refuse_effect = false
end

-- 34. A no-spend callback that only earns charge still restores the cooldown.
do
  local r, obs, st, w = scene(8204)
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'direct_hit', 3, 'first')
  st.on_apply_effect = function(rr)
    Core.tick(rr, 90)
    Core.on_event(rr, {host = 'player', kind = 'direct_hit', move_id = 'earned', lineage = 'direct'})
  end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.hosts.player.state.assault.ready_at == 0, 'earn-only refund did not restore the cooldown')
  assert(r.hosts.player.state.assault.charge == 3, 'earned charge was lost on refund')
  st.on_apply_effect = nil; st.refuse_effect = false
end

-- 35. A room clear with no newer spend keeps an ordinary in-flight refund.
do
  local r, obs, st, w = scene(8301)
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'direct_hit', 3, 'first')
  st.on_apply_effect = function() ga:on_room_leave() end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.hosts.player.state.assault.charge == 3, 'room reset lost the refundable spend')
  assert(r.hosts.player.state.assault.ready_at == 0, 'room reset lost the refunded cooldown')
  assert(ga.stats.refunded == 1, 'ordinary refund not counted')
  st.on_apply_effect = nil; st.refuse_effect = false
end

-- 36. A moved runtime state owns its newer spend across slots.
do
  local r, obs, st, w = scene(8302)
  local ga = GA.new(Core, B, w)
  local original = r.hosts.player.slots.assault
  charge(r, 'player', 'direct_hit', 3, 'first')
  st.on_apply_effect = function(rr)
    assert(Core.equip(rr, 'player', 'assault', nil))
    assert(Core.equip(rr, 'player', 'traversal', original))
    assert(Core.tick(rr, 90))
    charge(rr, 'player', 'move', 3, 'next')
    assert(Core.activate(rr, 'player', 'traversal', {target = 'enemy'}))
    assert(rr.hosts.player.state.traversal.ready_at == 180)
  end
  st.refuse_effect = true
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(r.hosts.player.state.traversal.ready_at == 180, 'moved state cooldown was clobbered')
  assert(r.hosts.player.state.traversal.charge == 0, 'moved state charge was clobbered')
  assert(ga.stats.refund_refused == 1, 'refused conditional restore was not reported')
  st.on_apply_effect = nil; st.refuse_effect = false
end

-- 37. Adversarial behavior data.
do
  local bad = clone(B)
  bad.reactions.thermal_shock.output = {'rime'}
  bad.reactions.plasma_surge.input = {'rime'}
  assert(not pcall(B.validate, bad), 'recursive reaction chain accepted')
  bad = clone(B)
  bad.genes.cinder.placements.assault.effect = {kind = 'dash'}
  assert(not pcall(B.validate, bad), 'route mismatch accepted')
  bad = clone(B)
  bad.genes.cinder.placements.assault.range = 999
  assert(not pcall(B.validate, bad), 'out-of-range placement accepted')
  bad = clone(B)
  bad.genes.gale.placements.traversal = nil
  assert(not pcall(B.validate, bad), 'single-placement gene accepted')
  local drifted = clone(Core)
  drifted.definitions.cinder.variants.assault.action = 'drifted'
  assert(not B.from_core(drifted), 'core drift not detected')
end

print('gene action contract: 36 finding groups passed')
'''


class GeneActionTests(unittest.TestCase):
    def test_contract_and_transaction(self):
        lua = shutil.which('lua5.4') or shutil.which('lua')
        self.assertIsNotNone(lua, 'Lua interpreter required; do not substitute a mock')
        result = subprocess.run([lua, '-', str(BEHAVIORS), str(CORE), str(ACTIONS)],
                                input=TEST, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('36 finding groups passed', result.stdout)

    def test_sources_exist(self):
        for path in (BEHAVIORS, CORE, ACTIONS):
            self.assertTrue(path.is_file(), f'missing {path}')


if __name__ == '__main__':
    unittest.main()
