#!/usr/bin/env python3
"""Contract tests for the native gene-world adapter (review-2 correction).

Runs the real accepted `core.lua`, `gene_behaviors.lua`, `gene_actions.lua` and
`runtime_gene_world.lua` under `lua5.4` with a stateful injected `gd` test
double. Proves the adapter/world contract against the final engine: optional
intent capture/validation, binding identity and drift, capability-gated
refusal before spend, the explicit native-hit acceptance opt-in, body-state
eligibility, provider exact-true ownership, bounded capacity and fail-closed
occlusion.

It is a **contract test, not native hit proof**. The gd double returns booleans;
it does not run Melee collision, hitlag, armor absorption, shields, projectiles
or the collision-loop callback. Root's native armor audit is recorded in
`_build/deepseek-coordination/native-hit-refusal-audit.md`.
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
WORLD = RT / 'runtime_gene_world.lua'

TEST = r'''
local B = assert(loadfile(arg[1]))()
local Core = assert(loadfile(arg[2]))()
local GA = assert(loadfile(arg[3]))()
local GW = assert(loadfile(arg[4]))()

-- Offered cinder/rime stay authoritative; register the unoffered prototypes in
-- memory so the real Core charge/spend APIs can exercise them.
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

local function check(v, m) if not v then error(m or 'assertion failed', 2) end return v end

local function make_gd()
  local g
  g = {players = {}, enemies = {}, calls = {}, refuse = {}, throw = {}, next_handle = 100}
  function g.player(port)
    local p = g.players[port]
    if not p then return nil end
    local o = {} for k, v in pairs(p) do o[k] = v end
    return o
  end
  function g.enemy_state(handle)
    local e = g.enemies[handle]
    if not e or e.alive == false then return nil end
    local o = {} for k, v in pairs(e) do o[k] = v end
    return o
  end
  function g.hit(port, spec)
    g.calls[#g.calls + 1] = {fn = 'hit', port = port, spec = spec}
    if g.throw.hit then error('native hit explosion') end
    if g.refuse.hit then return false end
    return true
  end
  function g.enemy_hurt(handle, spec)
    g.calls[#g.calls + 1] = {fn = 'enemy_hurt', handle = handle, spec = spec}
    if g.throw.enemy_hurt then error('native hurt explosion') end
    if g.refuse.enemy_hurt then return false end
    return true
  end
  function g.enemy_strike(handle, port, spec)
    g.calls[#g.calls + 1] = {fn = 'enemy_strike', handle = handle, port = port, spec = spec}
    if g.throw.enemy_strike then error('native strike explosion') end
    if g.refuse.enemy_strike then return false end
    return true
  end
  function g.impulse(port, spec)
    g.calls[#g.calls + 1] = {fn = 'impulse', port = port, spec = spec}
    if g.throw.impulse then error('native impulse explosion') end
    if g.refuse.impulse then return false end
    return true
  end
  return g
end

local function shield_of(t)
  if t.omit_shield then return nil end
  if t.shield_on then return true end
  return false
end

local function add_player(gd, port, t)
  t = t or {}
  gd.players[port] = {port = port, x = t.x or 0, y = t.y or 0, vx = 0, vy = 0, facing = t.facing or 1,
    percent = 0, stocks = t.stocks or 3, action = t.action or 20, action_frame = 0, anim_frame = 0,
    hitlag = t.hitlag or 0, airborne = t.airborne or false,
    shield_on = shield_of(t),
    body_state = (not t.omit_body) and (t.body_state or 'normal') or nil,
    timed_state = (not t.omit_body) and (t.timed_state or 'normal') or nil,
    invincible = (not t.omit_body) and (t.invincible or 0) or nil,
    intangible = (not t.omit_body) and (t.intangible or 0) or nil,
    in_hitlag = t.in_hitlag or false, in_hitstun = t.in_hitstun or false, cpu = port ~= 1}
end

local function add_enemy(gd, t)
  t = t or {}
  gd.next_handle = gd.next_handle + 1
  local h = gd.next_handle
  gd.enemies[h] = {handle = h, alive = true, kind = t.kind or 'goomba', state = 0, damage = 0, hits = 0,
    attack_id = 0, last_victim = 0, received = 0, last_attacker = 0, last_damage = 0,
    x = t.x or 0, y = t.y or 0, vx = 0, vy = 0, facing = t.facing or -1,
    vulnerable = (t.vulnerable ~= false)}
  return h
end

local function scene(seed, wopts, engopts)
  local profile = Core.new_profile(seed)
  local run = Core.new_run(profile)
  local gd = make_gd()
  local holder = {run = run}
  local engine = {gd = gd, get_run = function() return holder.run end}
  if engopts then for k, v in pairs(engopts) do engine[k] = v end end
  local world = GW.new(Core, engine, wopts)
  return {profile = profile, run = run, gd = gd, holder = holder, world = world}
end

local function bind(s, host, spec)
  local gen, why = s.world.bind(host, spec)
  check(gen ~= nil, 'bind ' .. host .. ': ' .. tostring(why))
  return gen
end

local function install(run, kind, host, slot)
  local id = assert(Core.acquire(run, kind))
  assert(Core.equip(run, host, slot, id))
  return id
end

local function charge(run, host, kind, n, prefix, target)
  for i = 1, n do
    local ev = {host = host, kind = kind, move_id = (prefix or 'x') .. ':' .. i, lineage = 'direct'}
    if target then ev.target = target end
    Core.on_event(run, ev)
  end
end

local function calls(gd, fn)
  local n = 0
  for _, c in ipairs(gd.calls) do if c.fn == fn then n = n + 1 end end
  return n
end
local function last_call(gd, fn)
  for i = #gd.calls, 1, -1 do if gd.calls[i].fn == fn then return gd.calls[i] end end
end
local function has_call(gd, fn) return calls(gd, fn) > 0 end

local visible = function() return true end
local CONTRACT = {native_hit_contract = 'accepted_damage'}

-- =====================================================================
-- 1. Honest capability/eligibility table.
-- =====================================================================
do
  local s = scene(1001, CONTRACT, {visibility = visible})
  local c = s.world.capabilities()
  check(c.schema == 2 and c.contact.enemy_hurt and c.contact.enemy_strike and c.contact.fighter_hit,
    'contact capability flags')
  check(c.contact.impulse == true, 'impulse capability')
  check(c.hit_contract == true, 'explicit hit contract recorded')
  check(c.occluded_fail_closed == false, 'visibility provider recorded')
  -- With the contract, all offered directions resolve; without it, fighter hit
  -- paths are ineligible but the custom-enemy hurt path still resolves.
  check(s.world.supports('cinder', 'assault', 'fighter') == true, 'fighter hit with contract')
  check(s.world.supports('cinder', 'assault', 'enemy') == true, 'fighter->custom hurt')
  check(s.world.supports('cinder', 'traversal', 'self') == true, 'impulse movement')
  check(s.world.supports('rime', 'guard', 'fighter') == true, 'core mark needs no contract')
  check(not s.world.supports('gale', 'traversal', 'self'), 'unoffered family refused')
  local e = s.world.eligibility()
  check(e.cinder.assault[1].direction == 'enemy' or e.cinder.assault[1].direction == 'fighter',
    'eligibility rows present')

  local no_contract = scene(1002, nil, {})
  local ok, why = no_contract.world.supports('cinder', 'assault', 'fighter')
  check(not ok and why == 'native hit acceptance contract not confirmed', 'contract gate report: ' .. tostring(why))
  check(no_contract.world.supports('cinder', 'assault', 'enemy') == true, 'custom hurt still eligible')
  check(no_contract.world.capabilities().occluded_fail_closed == true, 'absent LOS fail-closed reported')

  local no_impulse = scene(1003, CONTRACT, {visibility = visible})
  no_impulse.gd.impulse = nil
  check(no_impulse.world.capabilities().contact.impulse == false, 'missing impulse reported false')
  local ok2, why2 = no_impulse.world.supports('cinder', 'traversal', 'self')
  check(not ok2 and why2 == 'gd.impulse unavailable', 'missing impulse report: ' .. tostring(why2))
end

-- =====================================================================
-- 2. Fighter -> fighter requires and honors the explicit hit contract.
-- =====================================================================
do
  local s = scene(2001, CONTRACT, {visibility = visible})
  add_player(s.gd, 1, {x = 0, facing = 1})
  add_player(s.gd, 2, {x = 5, facing = -1})
  bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(s.run, 'player', 'direct_hit', 3, 'm')
  local ga = GA.new(Core, B, s.world)
  check(ga:begin('player', 'assault'))
  Core.tick(s.run, 1)
  ga:advance()
  local hit = last_call(s.gd, 'hit')
  check(hit and hit.port == 2 and hit.spec.from == 1, 'gd.hit shape')
  check(hit.spec.damage == 10 and hit.spec.angle == 45 and hit.spec.kbg == 70 and hit.spec.bkb == 20,
    'hit fields')
  check(s.run.hosts.player.state.assault.charge == 0, 'charge not spent')

  -- No contract: refused before the native call, no spend.
  local s2 = scene(2002, nil, {visibility = visible})
  add_player(s2.gd, 1, {x = 0, facing = 1})
  add_player(s2.gd, 2, {x = 5, facing = -1})
  bind(s2, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s2, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(s2.run, 'player', 'direct_hit', 3, 'm')
  local ga2 = GA.new(Core, B, s2.world)
  local rec, why = ga2:begin('player', 'assault')
  check(not rec and why == 'native hit acceptance contract not confirmed',
    'contract refusal before begin: ' .. tostring(why))
  check(s2.run.hosts.player.state.assault.charge == 3 and not has_call(s2.gd, 'hit'),
    'contract refusal spent or called native')
end

-- =====================================================================
-- 3. Fighter -> owned custom (audited separate contract, no opt-in).
-- =====================================================================
do
  local s = scene(3001, nil, {visibility = visible})
  add_player(s.gd, 1, {x = 0, facing = 1})
  local h = add_enemy(s.gd, {x = 5, facing = -1})
  bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s, 'mob', {kind = 'enemy', handle = h, team = 'enemy', room = 'r1', token = 'e'})
  charge(s.run, 'player', 'direct_hit', 3, 'm')
  local ga = GA.new(Core, B, s.world)
  check(ga:begin('player', 'assault'))
  Core.tick(s.run, 1)
  ga:advance()
  local hurt = last_call(s.gd, 'enemy_hurt')
  check(hurt and hurt.handle == h and hurt.spec.from == 1 and hurt.spec.reach == 7, 'enemy_hurt shape')
  check(not has_call(s.gd, 'hit'), 'must not use gd.hit for a custom actor')
end

-- =====================================================================
-- 4. Custom enemy -> fighter requires the explicit strike contract.
-- =====================================================================
do
  local s = scene(4001, CONTRACT, {visibility = visible})
  add_player(s.gd, 1, {x = 0, facing = 1})
  local h = add_enemy(s.gd, {x = 5, facing = -1})
  install(s.run, 'cinder', 'mob', 'assault')
  bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s, 'mob', {kind = 'enemy', handle = h, team = 'enemy', room = 'r1', token = 'e'})
  local ability = Core.ability(s.run, 'mob', 'assault')
  charge(s.run, 'mob', 'direct_hit', 3, 'e')
  local ga = GA.new(Core, B, s.world)
  check(ga:begin('mob', 'assault'))
  Core.tick(s.run, 1)
  ga:advance()
  local strike = last_call(s.gd, 'enemy_strike')
  check(strike and strike.handle == h and strike.port == 1, 'enemy_strike shape')
  check(strike.spec.damage == math.floor(ability.damage) and strike.spec.reach == ability.reach,
    'enemy_strike fields')

  local s2 = scene(4002, nil, {visibility = visible})
  add_player(s2.gd, 1, {x = 0, facing = 1})
  local h2 = add_enemy(s2.gd, {x = 5, facing = -1})
  install(s2.run, 'cinder', 'mob', 'assault')
  bind(s2, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s2, 'mob', {kind = 'enemy', handle = h2, team = 'enemy', room = 'r1', token = 'e'})
  charge(s2.run, 'mob', 'direct_hit', 3, 'e')
  local rec, why = GA.new(Core, B, s2.world):begin('mob', 'assault')
  check(not rec and why == 'native strike acceptance contract not confirmed',
    'strike contract refusal: ' .. tostring(why))
  check(not has_call(s2.gd, 'enemy_strike'), 'strike contract refusal still called native')
end

-- =====================================================================
-- 5. Eligibility refusals: team, room, dead, invulnerable, range, facing.
-- =====================================================================
do
  local function preflight_refuses(s, why)
    local plan, reason = GA.new(Core, B, s.world):preflight('player', 'assault')
    check(not plan, 'accepted: ' .. tostring(reason))
    return reason
  end
  local s1 = scene(5001, CONTRACT, {visibility = visible})
  add_player(s1.gd, 1, {x = 0, facing = 1}); add_player(s1.gd, 2, {x = 5, facing = -1})
  bind(s1, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s1, 'ally', {kind = 'player', port = 2, team = 'player', room = 'r1'})
  charge(s1.run, 'player', 'direct_hit', 3, 'm')
  check(preflight_refuses(s1) == 'no valid target', 'same team accepted')

  local s2 = scene(5002, CONTRACT, {visibility = visible, current_room = function() return 'r1' end})
  add_player(s2.gd, 1, {x = 0, facing = 1}); add_player(s2.gd, 2, {x = 5, facing = -1})
  bind(s2, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s2, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r2'})
  charge(s2.run, 'player', 'direct_hit', 3, 'm')
  preflight_refuses(s2)

  local s3 = scene(5003, CONTRACT, {visibility = visible})
  add_player(s3.gd, 1, {x = 0, facing = 1}); add_player(s3.gd, 2, {x = 5, facing = -1})
  bind(s3, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s3, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r2'})
  charge(s3.run, 'player', 'direct_hit', 3, 'm')
  preflight_refuses(s3)

  -- dead (zero stocks) and unknown eligibility.
  local s4 = scene(5004, CONTRACT, {visibility = visible})
  add_player(s4.gd, 1, {x = 0, facing = 1}); add_player(s4.gd, 2, {x = 5, facing = -1, stocks = 0})
  bind(s4, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s4, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(s4.run, 'player', 'direct_hit', 3, 'm')
  preflight_refuses(s4)

  local s5 = scene(5005, CONTRACT, {visibility = visible})
  add_player(s5.gd, 1, {x = 0, facing = 1}); add_player(s5.gd, 2, {x = 5, facing = -1, omit_body = true})
  bind(s5, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s5, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(s5.run, 'player', 'direct_hit', 3, 'm')
  preflight_refuses(s5)

  -- native body/timed state immunity and timers.
  for _, t in ipairs({{body_state = 'invincible'}, {timed_state = 'intangible'},
    {invincible = 30}, {intangible = 12}}) do
    local sx = scene(5006, CONTRACT, {visibility = visible})
    add_player(sx.gd, 1, {x = 0, facing = 1}); add_player(sx.gd, 2, {x = 5, facing = -1, body_state = t.body_state,
      timed_state = t.timed_state, invincible = t.invincible, intangible = t.intangible})
    bind(sx, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
    bind(sx, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
    charge(sx.run, 'player', 'direct_hit', 3, 'm')
    preflight_refuses(sx)
  end

  -- custom enemy invulnerability and optional provider.
  local s7 = scene(5007, CONTRACT, {visibility = visible})
  add_player(s7.gd, 1, {x = 0, facing = 1})
  local h = add_enemy(s7.gd, {x = 5, vulnerable = false})
  bind(s7, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s7, 'mob', {kind = 'enemy', handle = h, team = 'enemy', room = 'r1', token = 'e'})
  charge(s7.run, 'player', 'direct_hit', 3, 'm')
  preflight_refuses(s7)

  local s8 = scene(5008, CONTRACT, {visibility = visible, invulnerable = function(b) return b.host == 'enemy' end})
  add_player(s8.gd, 1, {x = 0, facing = 1}); add_player(s8.gd, 2, {x = 5, facing = -1})
  bind(s8, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s8, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(s8.run, 'player', 'direct_hit', 3, 'm')
  preflight_refuses(s8)

  -- range and facing.
  local s9 = scene(5009, CONTRACT, {visibility = visible})
  add_player(s9.gd, 1, {x = 0, facing = 1}); add_player(s9.gd, 2, {x = 20, facing = -1})
  bind(s9, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s9, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(s9.run, 'player', 'direct_hit', 3, 'm')
  preflight_refuses(s9)

  local s10 = scene(5010, CONTRACT, {visibility = visible})
  add_player(s10.gd, 1, {x = 0, facing = 1}); add_player(s10.gd, 2, {x = -5, facing = 1})
  bind(s10, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s10, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(s10.run, 'player', 'direct_hit', 3, 'm')
  preflight_refuses(s10)

  -- target shielded (native shield_on).
  local s11 = scene(5011, CONTRACT, {visibility = visible})
  add_player(s11.gd, 1, {x = 0, facing = 1}); add_player(s11.gd, 2, {x = 5, facing = -1, shield_on = true})
  bind(s11, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s11, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(s11.run, 'player', 'direct_hit', 3, 'm')
  preflight_refuses(s11)

  -- Incomplete/unknown eligibility must fail closed (no damage), not be
  -- treated as absent-and-safe.
  local function ineligible(t, engopts)
    local sx = scene(5012 + (t.n or 0), CONTRACT,
      engopts or {visibility = visible})
    add_player(sx.gd, 1, {x = 0, facing = 1})
    add_player(sx.gd, 2, {x = 5, facing = -1, body_state = t.body_state, timed_state = t.timed_state,
      omit_body = t.omit_body, omit_shield = t.omit_shield, shield_on = t.shield_on})
    bind(sx, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
    bind(sx, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
    charge(sx.run, 'player', 'direct_hit', 3, 'm')
    preflight_refuses(sx)
    return sx
  end
  ineligible({n = 1, body_state = '?', timed_state = 'normal'})
  ineligible({n = 2, body_state = 'normal', timed_state = '?'})
  ineligible({n = 3, omit_body = true})
  ineligible({n = 4, omit_shield = true})
  ineligible({n = 6}, {visibility = visible, invulnerable = function() return nil end})
  ineligible({n = 7}, {visibility = visible, invulnerable = function() error('no answer') end})

  -- An explicit boolean false is safe; the same target stays eligible.
  local safe = scene(5020, CONTRACT, {visibility = visible,
    invulnerable = function() return false end})
  add_player(safe.gd, 1, {x = 0, facing = 1}); add_player(safe.gd, 2, {x = 5, facing = -1})
  bind(safe, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(safe, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(safe.run, 'player', 'direct_hit', 3, 'm')
  local safe_plan = GA.new(Core, B, safe.world):preflight('player', 'assault')
  check(safe_plan, 'explicit false immunity made the target ineligible')

  -- A complete known-normal target succeeds (not a blanket refusal).
  local normal = scene(5021, CONTRACT, {visibility = visible})
  add_player(normal.gd, 1, {x = 0, facing = 1})
  add_player(normal.gd, 2, {x = 5, facing = -1, body_state = 'normal', timed_state = 'normal',
    invincible = 0, intangible = 0, shield_on = false})
  bind(normal, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(normal, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(normal.run, 'player', 'direct_hit', 3, 'm')
  local normal_ga = GA.new(Core, B, normal.world)
  check(normal_ga:begin('player', 'assault'))
  Core.tick(normal.run, 1)
  normal_ga:advance()
  check(has_call(normal.gd, 'hit') and normal.run.hosts.player.state.assault.charge == 0,
    'known-normal target did not succeed')
end

-- =====================================================================
-- 6. Missing native capability refuses at begin; false/nil/throw refund once.
-- =====================================================================
do
  local n = 6000
  local function scene_custom(mutate)
    n = n + 1
    local s = scene(n, nil, {visibility = visible})
    add_player(s.gd, 1, {x = 0, facing = 1})
    local h = add_enemy(s.gd, {x = 5})
    bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
    bind(s, 'mob', {kind = 'enemy', handle = h, team = 'enemy', room = 'r1', token = 'e'})
    charge(s.run, 'player', 'direct_hit', 3, 'm')
    if mutate then mutate(s) end
    return s
  end

  -- Missing gd.enemy_hurt is a capability failure: refused before spend/call.
  local missing = scene_custom(function(s) s.gd.enemy_hurt = nil end)
  local rec, why = GA.new(Core, B, missing.world):begin('player', 'assault')
  check(not rec and why == 'gd.enemy_hurt unavailable', 'missing API begin: ' .. tostring(why))
  check(missing.run.hosts.player.state.assault.charge == 3, 'missing API spent charge')
  check(not has_call(missing.gd, 'enemy_hurt'), 'missing API produced a call')

  local function refunded(mutate)
    local s = scene_custom(mutate)
    local ga = GA.new(Core, B, s.world)
    check(ga:begin('player', 'assault'))
    Core.tick(s.run, 1)
    ga:advance()
    check(s.run.hosts.player.state.assault.charge == 3, 'charge not refunded')
    check(#ga:view() == 0, 'record not cleaned')
    check(calls(s.gd, 'enemy_hurt') == 1, 'native call not made exactly once')
  end
  refunded(function(s) s.gd.refuse.enemy_hurt = true end)
  refunded(function(s)
    s.gd.enemy_hurt = function(handle, spec)
      s.gd.calls[#s.gd.calls + 1] = {fn = 'enemy_hurt', handle = handle, spec = spec}
      return nil
    end
  end)
  refunded(function(s) s.gd.throw.enemy_hurt = true end)
end

-- =====================================================================
-- 7. Movement and free-state.
-- =====================================================================
do
  local s = scene(7001, nil, {})
  add_player(s.gd, 1, {x = 0, facing = 1})
  install(s.run, 'cinder', 'player', 'traversal')
  bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  charge(s.run, 'player', 'move', 3, 'mv')
  local ga = GA.new(Core, B, s.world)
  check(ga:begin('player', 'traversal'))
  Core.tick(s.run, 1)
  ga:advance()
  local imp = last_call(s.gd, 'impulse')
  check(imp and imp.port == 1 and imp.spec.x == 2.4 and imp.spec.y == 0, 'impulse shape')
  check(s.run.hosts.player.state.traversal.charge == 0, 'movement charge not spent')

  local function movement_refusal(t, why)
    local sx = scene(7002, nil, {})
    add_player(sx.gd, 1, {x = 0, facing = 1, hitlag = t.hitlag, in_hitlag = t.in_hitlag,
      in_hitstun = t.in_hitstun, action = t.action, airborne = t.airborne})
    install(sx.run, 'cinder', 'player', 'traversal')
    bind(sx, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
    charge(sx.run, 'player', 'move', 3, 'mv')
    local plan, reason = GA.new(Core, B, sx.world):preflight('player', 'traversal')
    check(not plan and reason == why, 'movement refusal ' .. tostring(why) .. ': ' .. tostring(reason))
  end
  movement_refusal({hitlag = 1}, 'hitlag')
  movement_refusal({in_hitlag = true}, 'hitlag')
  movement_refusal({in_hitstun = true}, 'hitstun')
  movement_refusal({action = 10}, 'not in a free state')
  movement_refusal({airborne = true}, 'grounded step while airborne')

  local s5 = scene(7005, nil, {})
  add_player(s5.gd, 1, {x = 0, facing = 1})
  install(s5.run, 'cinder', 'player', 'traversal')
  bind(s5, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  charge(s5.run, 'player', 'move', 3, 'mv')
  s5.gd.refuse.impulse = true
  local ga5 = GA.new(Core, B, s5.world)
  check(ga5:begin('player', 'traversal'))
  Core.tick(s5.run, 1)
  ga5:advance()
  check(s5.run.hosts.player.state.traversal.charge == 3, 'impulse refusal lost the charge')

  -- Missing native impulse refuses before spend (capability preflight).
  local s6 = scene(7006, nil, {})
  add_player(s6.gd, 1, {x = 0, facing = 1})
  install(s6.run, 'cinder', 'player', 'traversal')
  bind(s6, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  charge(s6.run, 'player', 'move', 3, 'mv')
  s6.gd.impulse = nil
  local rec, why = GA.new(Core, B, s6.world):begin('player', 'traversal')
  check(not rec and why == 'gd.impulse unavailable', 'missing impulse begin: ' .. tostring(why))
  check(s6.run.hosts.player.state.traversal.charge == 3, 'missing impulse spent charge')
  check(not has_call(s6.gd, 'impulse'), 'missing impulse produced a call')
end

-- =====================================================================
-- 8. Unsupported mechanics refuse before spend; a real provider succeeds.
-- =====================================================================
do
  local function glacier(engopts)
    local s = scene(8001, CONTRACT, engopts)
    add_player(s.gd, 1, {x = 0, facing = 1}); add_player(s.gd, 2, {x = 5, facing = -1})
    install(s.run, 'glacier', 'player', 'assault')
    bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
    bind(s, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
    charge(s.run, 'player', 'direct_hit', 3, 'g')
    return s
  end
  local s = glacier({visibility = visible})
  local ga = GA.new(Core, B, s.world, {admitted = {cinder = true, rime = true, glacier = true}})
  local rec, why = ga:begin('player', 'assault')
  check(not rec and why == 'no native status provider', 'glacier begin: ' .. tostring(why))
  check(s.run.hosts.player.state.assault.charge == 3 and #s.gd.calls == 0, 'unsupported root had side effects')

  local s2 = glacier({visibility = visible, status = function() return true end})
  local ga2 = GA.new(Core, B, s2.world, {admitted = {cinder = true, rime = true, glacier = true}})
  check(ga2:begin('player', 'assault'))
  Core.tick(s2.run, 6)
  ga2:advance()
  check(s2.run.hosts.player.state.assault.charge == 0, 'provided status seam did not apply')
end

-- =====================================================================
-- 9. Deterministic equal-distance target order.
-- =====================================================================
do
  local s = scene(9001, nil, {visibility = visible})
  add_player(s.gd, 1, {x = 0, facing = 1})
  local ha = add_enemy(s.gd, {x = 5})
  local hb = add_enemy(s.gd, {x = 5})
  bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s, 'mob_a', {kind = 'enemy', handle = ha, team = 'enemy', room = 'r1', token = 'e'})
  bind(s, 'mob_b', {kind = 'enemy', handle = hb, team = 'enemy', room = 'r1', token = 'e'})
  charge(s.run, 'player', 'direct_hit', 3, 'm')
  local ga = GA.new(Core, B, s.world)
  local plan = check(ga:preflight('player', 'assault'))
  check(plan.target.host == 'mob_a', 'tie not deterministic')
  check(ga:begin('player', 'assault'))
  Core.tick(s.run, 1)
  ga:advance()
  check(last_call(s.gd, 'enemy_hurt').handle == ha, 'tie applied to wrong handle')
end

-- =====================================================================
-- 10. Forged/NaN/infinite bounds refuse before the native call.
-- =====================================================================
do
  local s = scene(10001, CONTRACT, {})
  add_player(s.gd, 1, {x = 0, facing = 1})
  add_player(s.gd, 2, {x = 5, facing = -1})
  local h = add_enemy(s.gd, {x = 3})
  bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  bind(s, 'mob', {kind = 'enemy', handle = h, team = 'enemy', room = 'r1', token = 'e'})
  s.world.get_run()
  local function effect(target, damage)
    return {host = 'player', slot = 'assault', gene = 'cinder', id = 'r1', move_id = 'forged',
      target = target, target_view = s.world.observe(target), host_view = s.world.observe('player'),
      spec = {effect = {kind = 'burst'}, native = true, targeting = 'opponent',
        occlusion = 'ignore', height = 12, range = 9},
      action = {damage = damage, knockback = {angle = 45, kbg = 70, bkb = 20}, reach = 7}}
  end
  local ok, why = s.world.apply_effect(s.run, effect('enemy', 0 / 0))
  check(not ok and why == 'hit fields outside native bounds', 'NaN damage accepted')
  ok, why = s.world.apply_effect(s.run, effect('enemy', 999))
  check(not ok and why == 'hit fields outside native bounds', 'oversize damage accepted')
  ok, why = s.world.apply_effect(s.run, effect('enemy', math.huge))
  check(not ok and why == 'hit fields outside native bounds', 'infinite damage accepted')
  ok, why = s.world.apply_effect(s.run, effect('mob', 999))
  check(not ok, 'oversize custom damage accepted')
  check(not has_call(s.gd, 'hit') and not has_call(s.gd, 'enemy_hurt'), 'forged bounds reached native')

  install(s.run, 'cinder', 'player', 'traversal')
  local ok2, why2 = s.world.apply_movement(s.run, {host = 'player', slot = 'traversal',
    move_id = 'forged2', spec = {effect = {kind = 'dash', distance = 10, grounded = true}}})
  check(not ok2 and why2 == 'movement outside native impulse bounds', 'oversize movement accepted')

  s.gd.players[1].x = 0 / 0
  check(s.world.observe('player') == nil, 'non-finite position accepted')
end

-- =====================================================================
-- 11. Intent identity: unchanged succeeds; any change cancels before spend.
-- =====================================================================
do
  -- unchanged binding succeeds (Cinder fighter strike with contract).
  local s = scene(11001, CONTRACT, {visibility = visible})
  add_player(s.gd, 1, {x = 0, facing = 1}); add_player(s.gd, 2, {x = 5, facing = -1})
  bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(s.run, 'player', 'direct_hit', 3, 'm')
  local ga = GA.new(Core, B, s.world)
  check(ga:begin('player', 'assault'))
  Core.tick(s.run, 1)
  ga:advance()
  check(has_call(s.gd, 'hit'), 'unchanged binding did not succeed')

  -- movement source rebound to a different port/token: cancel before spend.
  local sm = scene(11002, nil, {})
  add_player(sm.gd, 1, {x = 0}); add_player(sm.gd, 2, {x = 0})
  install(sm.run, 'cinder', 'player', 'traversal')
  bind(sm, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1', token = 'old'})
  charge(sm.run, 'player', 'move', 3, 'mv')
  local gam = GA.new(Core, B, sm.world)
  check(gam:begin('player', 'traversal'))
  bind(sm, 'player', {kind = 'player', port = 2, team = 'player', room = 'r1', token = 'new'})
  Core.tick(sm.run, 1)
  gam:advance()
  check(not has_call(sm.gd, 'impulse'), 'rebound source still moved')
  check(sm.run.hosts.player.state.traversal.charge == 3, 'rebound source not refunded')

  -- Core-owned Rime mark target rebound: cancel before spend, no mark.
  local sr = scene(11003, nil, {visibility = visible})
  add_player(sr.gd, 1, {x = 0}); add_player(sr.gd, 2, {x = 5}); add_player(sr.gd, 3, {x = 5})
  install(sr.run, 'rime', 'player', 'assault')
  bind(sr, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(sr, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1', token = 'old'})
  charge(sr.run, 'player', 'direct_hit', 3, 'm')
  local gar = GA.new(Core, B, sr.world)
  check(gar:begin('player', 'assault'))
  bind(sr, 'enemy', {kind = 'player', port = 3, team = 'enemy', room = 'r1', token = 'new'})
  Core.tick(sr.run, 1)
  gar:advance()
  check(not sr.run.marks.enemy, 'rebound Rime target was marked')
  check(sr.run.hosts.player.state.assault.charge == 3, 'rebound Rime target spent charge')

  -- run reference replaced with a different instance sharing the run id.
  local srun = scene(11004, CONTRACT, {visibility = visible})
  add_player(srun.gd, 1, {x = 0, facing = 1}); add_player(srun.gd, 2, {x = 5, facing = -1})
  bind(srun, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(srun, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(srun.run, 'player', 'direct_hit', 3, 'old')
  local garun = GA.new(Core, B, srun.world)
  check(garun:begin('player', 'assault'))
  local other = Core.new_run(Core.new_profile(11005))
  check(other.id == srun.run.id, 'fixture expected shared run id')
  charge(other, 'player', 'direct_hit', 3, 'new')
  srun.holder.run = other
  Core.tick(other, 1)
  garun:advance()
  check(not has_call(srun.gd, 'hit'), 'cross-run reference still struck')
  check(srun.run.hosts.player.state.assault.charge == 3 and other.hosts.player.state.assault.charge == 3,
    'cross-run reference spent a charge')

  -- room change cancels before spend.
  local room = {id = 'r1'}
  local sroom = scene(11006, CONTRACT, {visibility = visible, current_room = function() return room.id end})
  add_player(sroom.gd, 1, {x = 0, facing = 1}); add_player(sroom.gd, 2, {x = 5, facing = -1})
  bind(sroom, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(sroom, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  charge(sroom.run, 'player', 'direct_hit', 3, 'm')
  local garoom = GA.new(Core, B, sroom.world)
  check(garoom:begin('player', 'assault'))
  room.id = 'r2'
  Core.tick(sroom.run, 1)
  garoom:advance()
  check(not has_call(sroom.gd, 'hit') and sroom.run.hosts.player.state.assault.charge == 3,
    'room change did not cancel before spend')

  -- target handle change cancels before spend.
  local shan = scene(11007, nil, {visibility = visible})
  add_player(shan.gd, 1, {x = 0, facing = 1})
  local h1 = add_enemy(shan.gd, {x = 5}); local h2 = add_enemy(shan.gd, {x = 5})
  bind(shan, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(shan, 'mob', {kind = 'enemy', handle = h1, team = 'enemy', room = 'r1', token = 'e1'})
  charge(shan.run, 'player', 'direct_hit', 3, 'm')
  local gahan = GA.new(Core, B, shan.world)
  check(gahan:begin('player', 'assault'))
  bind(shan, 'mob', {kind = 'enemy', handle = h2, team = 'enemy', room = 'r1', token = 'e2'})
  Core.tick(shan.run, 1)
  gahan:advance()
  check(not has_call(shan.gd, 'enemy_hurt') and shan.run.hosts.player.state.assault.charge == 3,
    'handle change did not cancel before spend')
end

-- =====================================================================
-- 12. Two simultaneous actions never share or overwrite intent.
-- =====================================================================
do
  local s = scene(12001, CONTRACT, {visibility = visible})
  add_player(s.gd, 1, {x = 0, facing = 1})
  local h = add_enemy(s.gd, {x = 5, facing = -1})
  install(s.run, 'cinder', 'mob', 'assault')
  bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s, 'mob', {kind = 'enemy', handle = h, team = 'enemy', room = 'r1', token = 'e'})
  charge(s.run, 'player', 'direct_hit', 3, 'p')
  charge(s.run, 'mob', 'direct_hit', 3, 'e')
  local ga = GA.new(Core, B, s.world)
  check(ga:begin('player', 'assault'))
  check(ga:begin('mob', 'assault'))
  Core.tick(s.run, 1)
  ga:advance()
  check(calls(s.gd, 'enemy_hurt') == 1 and calls(s.gd, 'enemy_strike') == 1,
    'two simultaneous actions interfered')
  check(s.run.hosts.player.state.assault.charge == 0 and s.run.hosts.mob.state.assault.charge == 0,
    'simultaneous actions did not both spend')
end

-- =====================================================================
-- 13. Provider ownership: exact-true, retained refusal, reset releases.
-- =====================================================================
do
  local admitted = {admitted = {cinder = true, rime = true, bulwark = true}}
  local function bulwark(seed, guard, mutate)
    local s = scene(seed, {native_hit_contract = 'accepted_damage'}, {visibility = visible, guard = guard})
    add_player(s.gd, 1, {x = 0, facing = 1})
    install(s.run, 'bulwark', 'player', 'guard')
    bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
    charge(s.run, 'player', 'defend', 3, 'd')
    if mutate then mutate(s) end
    local ga = GA.new(Core, B, s.world, admitted)
    check(ga:begin('player', 'guard'))
    Core.tick(s.run, 1)
    ga:advance()
    Core.tick(s.run, 1)
    ga:advance()
    return s, ga
  end

  -- (a) provider returns false plus an identifiable token: refused, charge
  -- refunded, token still cleaned up through the provider.
  local rel_a = 0
  local s1 = bulwark(13001, {apply = function() return false, {contrib = {id = 'tok'}} end,
    release = function(r, t) rel_a = rel_a + 1 return true end})
  check(s1.run.hosts.player.state.guard.charge == 3 and #s1.world.contributions() == 0,
    'false+token accepted or token leaked')
  check(rel_a == 1, 'false+token cleanup did not release exactly once')

  -- (b) provider returns nil plus a token: same refusal-owned cleanup.
  local rel_b = 0
  local s2 = bulwark(13002, {apply = function() return nil, {contrib = {id = 'tok'}} end,
    release = function(r, t) rel_b = rel_b + 1 return true end})
  check(s2.run.hosts.player.state.guard.charge == 3 and #s2.world.contributions() == 0,
    'nil+token accepted or token leaked')
  check(rel_b == 1, 'nil+token cleanup did not release exactly once')

  -- (c) table success {ok=true,contrib} is NOT strict exact true: refused with
  -- the token cleaned up.
  local rel_c = 0
  local s3 = bulwark(13003, {apply = function() return {ok = true, contrib = {id = 'tok'}} end,
    release = function(r, t) rel_c = rel_c + 1 return true end})
  check(s3.run.hosts.player.state.guard.charge == 3 and #s3.world.contributions() == 0,
    'table success accepted')
  check(rel_c == 1, 'table-success token not cleaned up')

  -- (d) exact true owns the token; reset releases it through the provider.
  local rel_d = 0
  local s4 = bulwark(13004, {apply = function() return true, {contrib = {id = 'tok'}} end,
    release = function(r, t) rel_d = rel_d + 1 return true end})
  check(#s4.world.contributions() == 1, 'exact-true token not owned')
  check(s4.world.reset(s4.run) == true, 'reset failed with a releasable token')
  check(rel_d == 1 and #s4.world.contributions() == 0, 'reset did not release through the provider')

  -- (e) refused cleanup is retained; reset refuses and keeps it, then retries.
  local refused_release = true
  local rel_e = 0
  local s5 = bulwark(13005, {apply = function() return true, {contrib = {id = 'tok2'}} end,
    release = function(r, t) rel_e = rel_e + 1 if refused_release then return false end return true end})
  local ok5, detail5 = s5.world.reset(s5.run)
  check(ok5 == false and #s5.world.contributions() == 1, 'reset forgot a refused token')
  refused_release = false
  check(s5.world.reset(s5.run) == true and #s5.world.contributions() == 0, 'retry reset did not release')

  -- (f) cleanup uses the owning run, never a later run.
  local seen = {}
  local s6 = bulwark(13006, {apply = function() return true, {contrib = {id = 'tok3'}} end,
    release = function(r, t) seen[#seen + 1] = r return true end})
  local owner = s6.run
  local later = Core.new_run(Core.new_profile(13007))
  check(later ~= owner, 'fixture expected a distinct run')
  s6.holder.run = later
  check(s6.world.reset(later) == true, 'reset after promotion failed')
  check(#seen == 1 and seen[1] == owner, 'cleanup used a later run instead of the owning run')
end

-- =====================================================================
-- 14. Direct seam metadata, observation shape and Core mark ownership.
-- =====================================================================
do
  local s = scene(14001, CONTRACT, {visibility = visible})
  add_player(s.gd, 1, {x = 0, facing = 1}); add_player(s.gd, 2, {x = 5, facing = -1})
  install(s.run, 'rime', 'player', 'assault')
  bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s, 'enemy', {kind = 'player', port = 2, team = 'enemy', room = 'r1'})
  s.world.get_run()
  local v = check(s.world.observe('enemy'), 'observe nil')
  check(v.gen and v.ref == 'p:2' and v.team == 'enemy' and v.room == 'r1', 'observe identity')
  check(v.body_state == 'normal' and v.vulnerable == true and v.shielding == false, 'observe eligibility fields')

  -- Rime assault mark: Core writes run.marks, no adapter native call.
  charge(s.run, 'player', 'direct_hit', 3, 'mk')
  local ga = GA.new(Core, B, s.world)
  check(ga:begin('player', 'assault'))
  Core.tick(s.run, 1)
  ga:advance()
  check(s.run.marks.enemy and s.run.marks.enemy.source == 'player', 'Core mark not applied')
  check(#s.gd.calls == 0, 'adapter double-applied the Rime mark')
end

-- =====================================================================
-- 15. Injected world without the optional intent hooks stays compatible.
-- =====================================================================
do
  local run = Core.new_run(Core.new_profile(15001))
  local holder = {run = run}
  local applies = 0
  local w = {}
  w.get_run = function() return holder.run end
  w.observe = function(host)
    if host == 'player' then return {host = host, x = 0, y = 0, facing = 1, alive = true} end
    if host == 'enemy' then return {host = host, x = 5, y = 0, facing = -1, alive = true} end
    return nil
  end
  w.can_start = function() return true end
  w.query = function() return {host = 'enemy', x = 5, y = 0, facing = -1, alive = true} end
  w.occluded = function() return false end
  w.apply_effect = function() applies = applies + 1 return true end
  check(w.capture_intent == nil and w.validate_intent == nil, 'fixture must omit the hooks')
  charge(run, 'player', 'direct_hit', 3, 'm')
  local ga = GA.new(Core, B, w)
  check(ga:begin('player', 'assault'))
  Core.tick(run, 1)
  ga:advance()
  check(applies == 1 and run.hosts.player.state.assault.charge == 0,
    'injected world without intent hooks no longer works')
end

-- =====================================================================
-- 16. Custom-enemy traversal is an impossible native direction: refused at
--     begin with no spend/refund/native call; fighter traversal still works.
-- =====================================================================
do
  local s = scene(16001, nil, {})
  add_player(s.gd, 1, {x = 0, facing = 1})
  local h = add_enemy(s.gd, {x = 5})
  install(s.run, 'cinder', 'mob', 'traversal')
  bind(s, 'player', {kind = 'player', port = 1, team = 'player', room = 'r1'})
  bind(s, 'mob', {kind = 'enemy', handle = h, team = 'enemy', room = 'r1', token = 'e'})
  charge(s.run, 'mob', 'move', 3, 'mv')
  local ga = GA.new(Core, B, s.world)
  local rec, why = ga:begin('mob', 'traversal')
  check(not rec and why == 'gd.impulse requires a fighter port', 'custom traversal begin: ' .. tostring(why))
  check(s.run.hosts.mob.state.traversal.charge == 3, 'custom traversal spent charge')
  check(not has_call(s.gd, 'impulse'), 'custom traversal produced a native call')

  install(s.run, 'cinder', 'player', 'traversal')
  charge(s.run, 'player', 'move', 3, 'pm')
  local gap = GA.new(Core, B, s.world)
  check(gap:begin('player', 'traversal'), 'fighter traversal begin refused')
  Core.tick(s.run, 1)
  gap:advance()
  check(has_call(s.gd, 'impulse'), 'fighter traversal no longer succeeds')
end

print('gene-world contract: 16 groups passed against accepted dependencies (contract only; not native hit proof)')
'''



class GeneWorldTests(unittest.TestCase):
    def test_contract(self):
        lua = shutil.which('lua5.4') or shutil.which('lua')
        self.assertIsNotNone(lua, 'Lua interpreter required; do not substitute a mock')
        result = subprocess.run(
            [lua, '-', str(BEHAVIORS), str(CORE), str(ACTIONS), str(WORLD)],
            input=TEST, text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('gene-world contract: 16 groups passed', result.stdout)

    def test_sources_exist(self):
        for path in (BEHAVIORS, CORE, ACTIONS, WORLD):
            self.assertTrue(path.is_file(), f'missing {path}')


if __name__ == '__main__':
    unittest.main()
