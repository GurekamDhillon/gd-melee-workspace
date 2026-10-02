#!/usr/bin/env python3
"""Exercise the real gene-behavior and action-transaction Lua modules.

Runs the actual Lua files with a deterministic fake native world. The fake world
proves the transaction contract (phases, costs, refunds, provenance, cleanup);
it does not prove native collision, hitstop or controller play. Prototype gene
definitions are registered into the in-memory Core table so the real charge and
spend APIs can be exercised for the unoffered families; production admission is
still cinder/rime only.
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

-- Register the unoffered prototype definitions in-memory only, so the real
-- Core charge/spend APIs can drive the transaction for every family. cinder and
-- rime keep their authoritative definitions untouched.
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

local function fresh(seed)
  local p = Core.new_profile(seed)
  local r = Core.new_run(p)
  return p, r
end

local function install(r, kind, host, slot)
  local id = assert(Core.acquire(r, kind))
  assert(Core.equip(r, host, slot, id))
  return id
end

local function charge(r, host, kind, n, prefix, target)
  for i = 1, n do
    local ev = {host = host, kind = kind, move_id = (prefix or 'x') .. ':' .. i, lineage = 'direct'}
    if target then ev.target = target end
    Core.on_event(r, ev)
  end
end

local function world_for(run, obs)
  local st = {occluded = false, refuse_effect = false, refuse_movement = false, calls = {}}
  local w = {}
  w.get_run = function() return run end
  w.can_start = function() return true end
  w.observe = function(host)
    local o = obs[host]
    if not o then return nil end
    return {host = host, x = o.x, y = o.y, facing = o.facing or 1, alive = o.alive ~= false,
      reflecting = o.reflecting, shielding = o.shielding}
  end
  w.query = function(host)
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
  w.apply_effect = function(r, req)
    st.calls[#st.calls + 1] = {seam = 'apply_effect', req = req}
    if st.refuse_effect then return false, 'refused' end
    return true
  end
  w.apply_movement = function(r, req)
    st.calls[#st.calls + 1] = {seam = 'apply_movement', req = req}
    if st.refuse_movement then return false, 'refused' end
    return true
  end
  w.apply_status = function(r, req)
    st.calls[#st.calls + 1] = {seam = 'apply_status', req = req}
    return true
  end
  w.apply_guard = function(r, req)
    st.calls[#st.calls + 1] = {seam = 'apply_guard', req = req}
    local mid = 'guard:' .. req.move_id
    assert(Core.apply_modifier(r, req.host, req.slot, {id = mid, stat = 'potency', add = 5, expires = r.frame + 300}))
    return true, {contrib = {kind = 'guard', id = mid, host = req.host, slot = req.slot}}
  end
  w.release_guard = function(r, contrib)
    st.calls[#st.calls + 1] = {seam = 'release_guard'}
    assert(Core.remove_modifier(r, contrib.host, contrib.slot, contrib.id))
  end
  w.apply_conversion = function(r, req)
    st.calls[#st.calls + 1] = {seam = 'apply_conversion', req = req}
    local mid = 'conv:' .. req.move_id
    assert(Core.apply_modifier(r, req.host, req.slot, {id = mid, stat = 'gain', add = 1, expires = r.frame + 300}))
    return true, {contrib = {kind = 'conversion', id = mid, host = req.host, slot = req.slot}}
  end
  w.release_conversion = function(r, contrib)
    st.calls[#st.calls + 1] = {seam = 'release_conversion'}
    assert(Core.remove_modifier(r, contrib.host, contrib.slot, contrib.id))
  end
  return st, w
end

local function scene(seed)
  local _, r = fresh(seed)
  local obs = {player = {x = 0, y = 0, facing = 1}, enemy = {x = 5, y = 0, facing = -1}}
  local st, w = world_for(r, obs)
  return r, obs, st, w
end

local function seam_calls(st, seam)
  local n = 0
  for _, c in ipairs(st.calls) do if c.seam == seam then n = n + 1 end end
  return n
end

-- 1. Contract and admission.
assert(B.validate(B))
assert(B.from_core(Core))
local admitted = B.admitted_defaults()
assert(admitted.cinder and admitted.rime and not admitted.emberline and not admitted.glacier)

do
  local r, obs, st, w = scene(1001)
  local ga = GA.new(Core, B, w)

  -- 2. Costs and refusals: an unready action is refused without mutating the run.
  local before = assert(Core.snapshot(r))
  local rec, why = ga:begin('player', 'assault')
  assert(not rec and why == 'not ready', tostring(why))
  assert(Core.snapshot(r) == before, 'unready begin mutated the run')
  assert(not ga:begin('ghost', 'assault'))
  assert(not ga:begin('player', 'bogus'))
  charge(r, 'player', 'direct_hit', 3, 'm')
  assert(Core.ability(r, 'player', 'assault').ready)
  -- 3. Spend point: charge is held through startup and released at activation.
  local active = assert(ga:begin('player', 'assault'))
  assert(active.phase == 'startup' and r.hosts.player.state.assault.charge == 3, 'spent during startup')
  local first = seam_calls(st, 'apply_effect')
  ga:advance()
  assert(r.hosts.player.state.assault.charge == 0, 'charge not spent at release')
  -- 4. One application per move instance even when the active window is polled.
  for _ = 1, 8 do Core.tick(r, 1); ga:advance() end
  assert(seam_calls(st, 'apply_effect') == first + 1, 'repeat multihit applied more than once')
  local prov = ga:provenance()
  assert(#prov == 1 and prov[1].source == 'player' and prov[1].target == 'enemy', 'provenance wrong')
  assert(prov[1].spent and prov[1].applied and prov[1].move_id ~= nil, 'provenance flags wrong')
  -- Native refusal restores the pre-spend snapshot (reversible refund).
  Core.tick(r, 200)
  charge(r, 'player', 'direct_hit', 3, 'ref')
  st.refuse_effect = true
  local before_ref = assert(Core.snapshot(r))
  assert(ga:begin('player', 'assault'))
  ga:advance()
  assert(#ga:view() == 0, 'refused action not cleaned up')
  assert(Core.snapshot(r) == before_ref, 'effect refusal did not restore the run')
  assert(r.hosts.player.state.assault.charge == 3, 'effect refusal did not refund charge')
  assert(ga.stats.restored == 1, 'refund not counted')
  st.refuse_effect = false
  -- Move-id dedup: one attack instance charges once.
  Core.tick(r, 200)
  r.hosts.player.state.assault.charge = 0
  assert(Core.on_event(r, {host = 'player', kind = 'direct_hit', move_id = 'dup', lineage = 'direct'}) > 0)
  assert(Core.on_event(r, {host = 'player', kind = 'direct_hit', move_id = 'dup', lineage = 'direct'}) == 0,
    'move-id dedup failed')
  -- Reaction lineage never charges.
  assert(ga:on_event({host = 'player', kind = 'direct_hit', move_id = 'r', lineage = 'reaction'}) == 0,
    'reaction charged')
  -- Cinder's guard counter is a defense placement that targets an opponent and
  -- therefore releases through the strike seam, matching the current runtime.
  install(r, 'cinder', 'player', 'guard')
  Core.tick(r, 200)
  charge(r, 'player', 'defend', 3, 'gd')
  assert(Core.ability(r, 'player', 'guard').ready)
  local strikes = seam_calls(st, 'apply_effect')
  assert(ga:begin('player', 'guard'))
  ga:advance()
  assert(seam_calls(st, 'apply_effect') == strikes + 1, 'guard counter did not use the strike seam')
end

do
  -- 5. Startup window, dodge and occlusion on a prototyping gene.
  local r, obs, st, w = scene(1002)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, glacier = true}})
  install(r, 'glacier', 'player', 'assault')
  charge(r, 'player', 'direct_hit', 6, 'g')
  assert(Core.ability(r, 'player', 'assault').ready)
  local cost = Core.ability(r, 'player', 'assault').cost
  assert(assert(ga:begin('player', 'assault')).phase == 'startup')
  Core.tick(r, 1)
  ga:advance()
  assert(r.hosts.player.state.assault.charge == cost, 'spent during the startup window')
  obs.enemy.x = 100
  Core.tick(r, 5)
  ga:advance()
  assert(r.hosts.player.state.assault.charge == cost, 'dodge did not preserve charge')
  assert(#ga:view() == 0, 'dodged action not cleaned up')
  obs.enemy.x = 5
  -- Occlusion refuses the cast and any release.
  Core.tick(r, 200)
  charge(r, 'player', 'direct_hit', 5, 'g2')
  st.occluded = true
  local plan, why = ga:preflight('player', 'assault')
  assert(not plan and why == 'target occluded', tostring(why))
  st.occluded = false
  -- 6. Shields and reflection refuse the target.
  obs.enemy.reflecting = true
  plan, why = ga:preflight('player', 'assault')
  assert(not plan and why == 'target reflects', tostring(why))
  obs.enemy.reflecting = nil
  obs.enemy.shielding = true
  plan, why = ga:preflight('player', 'assault')
  assert(not plan and why == 'target shielded', tostring(why))
  obs.enemy.shielding = nil
  -- Control route reaches the status seam after the startup window.
  local rec = assert(ga:begin('player', 'assault'))
  Core.tick(r, 6)
  ga:advance()
  assert(seam_calls(st, 'apply_status') >= 1, 'control route did not use apply_status')
end

do
  -- 7. Reversible defense contribution: apply, interrupt, and room-leave cleanup.
  local r, obs, st, w = scene(1003)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, bulwark = true}})
  install(r, 'bulwark', 'player', 'guard')
  local base = Core.resolve(r, 'player', 'guard').potency
  charge(r, 'player', 'defend', 7, 'd')
  assert(Core.ability(r, 'player', 'guard').ready)
  assert(ga:begin('player', 'guard'))
  ga:advance()
  assert(Core.resolve(r, 'player', 'guard').potency == base + 5, 'guard contribution not applied')
  assert(ga:interrupt('player', 'guard', 'test'))
  assert(Core.resolve(r, 'player', 'guard').potency == base, 'interrupt did not release contribution')
  -- Settle then leave the room: owned reversible state is released too.
  Core.tick(r, 200)
  charge(r, 'player', 'defend', 7, 'd2')
  assert(ga:begin('player', 'guard'))
  ga:advance()
  Core.tick(r, 1)
  ga:advance()
  assert(Core.resolve(r, 'player', 'guard').potency == base + 5, 'settled contribution not active')
  ga:on_room_leave()
  assert(Core.resolve(r, 'player', 'guard').potency == base, 'room leave did not release contribution')
  assert(#ga:provenance() == 0, 'room leave did not clear evidence')
end

do
  -- 8. Resource conversion route: apply and release without numerical drift.
  local r, obs, st, w = scene(1004)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, convert = true}})
  install(r, 'convert', 'player', 'guard')
  local base = Core.resolve(r, 'player', 'guard').gain
  charge(r, 'player', 'defend', 6, 'c')
  assert(Core.ability(r, 'player', 'guard').ready)
  assert(ga:begin('player', 'guard'))
  ga:advance()
  assert(seam_calls(st, 'apply_conversion') == 1, 'conversion route not used')
  assert(Core.resolve(r, 'player', 'guard').gain == base + 1, 'conversion contribution not applied')
  Core.tick(r, 1)
  ga:advance()
  ga:on_room_leave()
  assert(Core.resolve(r, 'player', 'guard').gain == base, 'conversion cleanup drifted')
end

do
  -- 9. Movement route and refusal refund.
  local r, obs, st, w = scene(1005)
  local ga = GA.new(Core, B, w)
  install(r, 'cinder', 'player', 'traversal')
  charge(r, 'player', 'move', 3, 'mv')
  assert(Core.ability(r, 'player', 'traversal').ready)
  assert(ga:begin('player', 'traversal'))
  ga:advance()
  assert(seam_calls(st, 'apply_movement') == 1, 'movement route not used')
  Core.tick(r, 1)
  ga:advance()
  Core.tick(r, 200)
  charge(r, 'player', 'move', 3, 'mv2')
  st.refuse_movement = true
  local before = assert(Core.snapshot(r))
  assert(ga:begin('player', 'traversal'))
  ga:advance()
  assert(Core.snapshot(r) == before, 'movement refusal did not restore the run')
  assert(Core.ability(r, 'player', 'traversal').charge == 3, 'movement refusal lost charge')
end

do
  -- 10. Enemy parity: the same contract accepts a non-player host.
  local r, obs, st, w = scene(1006)
  local ga = GA.new(Core, B, w)
  install(r, 'cinder', 'enemy', 'assault')
  charge(r, 'enemy', 'direct_hit', 3, 'e')
  assert(Core.ability(r, 'enemy', 'assault').ready)
  local rec = assert(ga:begin('enemy', 'assault'))
  assert(rec.host == 'enemy')
  ga:advance()
  Core.tick(r, 1)
  ga:advance()
  local prov = ga:provenance()
  assert(#prov == 1 and prov[1].source == 'enemy' and prov[1].target == 'player', 'enemy provenance wrong')
end

do
  -- 11. Thermal Shock: fire consumes a rime mark, reaction never recharges.
  local r, obs, st, w = scene(1007)
  local ga = GA.new(Core, B, w)
  -- Starter equips cinder (assault) and rime (guard).
  charge(r, 'player', 'defend', 3, 'mk')
  assert(Core.ability(r, 'player', 'guard').ready)
  assert(ga:begin('player', 'guard'))
  ga:advance()
  assert(r.marks.enemy and r.marks.enemy.source == 'player', 'rime mark not applied')
  Core.tick(r, 1)
  ga:advance()
  charge(r, 'player', 'direct_hit', 3, 'th')
  assert(Core.ability(r, 'player', 'assault').ready)
  assert(ga:begin('player', 'assault'))
  ga:advance()
  Core.tick(r, 1)
  ga:advance()
  local prov = ga:provenance()
  local thermal
  for _, e in ipairs(prov) do if e.reaction == 'thermal_shock' then thermal = e end end
  assert(thermal, 'thermal shock not recorded')
  assert(not r.marks.enemy, 'thermal shock did not consume the mark')
  -- A reaction-lineage event must not charge the source again.
  Core.tick(r, 200)
  assert(ga:on_event({host = 'player', kind = 'direct_hit', move_id = 're', reaction = true}) == 0)
end

do
  -- 12. Per-target earning uses Core's existing move-id keying.
  local r, obs, st, w = scene(1008)
  local ga = GA.new(Core, B, w, {admitted = {cinder = true, rime = true, brand = true}})
  assert(Core.equip(r, 'player', 'traversal', nil))
  assert(Core.equip(r, 'player', 'guard', nil))
  install(r, 'brand', 'player', 'assault')
  local a = ga:on_event({host = 'player', kind = 'direct_hit', move_id = 'p', target = 'enemy'})
  local b = ga:on_event({host = 'player', kind = 'direct_hit', move_id = 'p', target = 'enemy2'})
  local c = ga:on_event({host = 'player', kind = 'direct_hit', move_id = 'p', target = 'enemy'})
  assert(a and a > 0 and b and b > 0, 'per-target earning did not charge each target')
  assert(c == 0, 'per-target earning charged a repeated target')
end

do
  -- 13. Caps: record and provenance bounds, deterministic refusal.
  local r, obs, st, w = scene(1009)
  local ga = GA.new(Core, B, w, {caps = {records = 1, provenance = 1}})
  install(r, 'cinder', 'player', 'traversal')
  charge(r, 'player', 'direct_hit', 3, 'a')
  charge(r, 'player', 'move', 3, 't')
  assert(ga:begin('player', 'assault'))
  local rec, why = ga:begin('player', 'traversal')
  assert(not rec and why == 'action record cap', tostring(why))
  -- Settle one action, then a second; provenance keeps at most one entry.
  ga:advance()
  Core.tick(r, 1)
  ga:advance()
  assert(#ga:provenance() <= 1, 'provenance cap exceeded')
end

do
  -- 14. Missing native seam refuses rather than faking the hit.
  local r, obs, st, w = scene(1010)
  w.apply_effect = nil
  local ga = GA.new(Core, B, w)
  charge(r, 'player', 'direct_hit', 3, 's')
  local plan, why = ga:preflight('player', 'assault')
  assert(not plan and why == 'native apply_effect seam missing', tostring(why))
end

do
  -- 15. Adversarial behavior data is refused.
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

print('gene action contract: 15 scenarios passed')
'''


class GeneActionTests(unittest.TestCase):
    def test_contract_and_transaction(self):
        lua = shutil.which('lua5.4') or shutil.which('lua')
        self.assertIsNotNone(lua, 'Lua interpreter required; do not substitute a mock')
        result = subprocess.run([lua, '-', str(BEHAVIORS), str(CORE), str(ACTIONS)],
                                input=TEST, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('15 scenarios passed', result.stdout)

    def test_sources_exist(self):
        for path in (BEHAVIORS, CORE, ACTIONS):
            self.assertTrue(path.is_file(), f'missing {path}')


if __name__ == '__main__':
    unittest.main()
