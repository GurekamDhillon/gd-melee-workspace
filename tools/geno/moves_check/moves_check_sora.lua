-- moves_check.lua for Sora: the same normals, aerials, grabs, throws and landings, then Sora's own specials and their articles.
-- It runs unchanged on the old m-ex install (token ultimatesora) and on the define (geno:ultimate-sora), so the two MOVECHK logs can be diffed
-- line by line (tools/geno/moves_check/moves_diff.py). Articles are read from gd.items(): the frame they appear, their life and path, and
-- the damage Mario takes standing 10 and 24 units in front.
-- Move-by-move check of a Geno define fighter (P1) against Mario (P2, stands) in the LAB.
-- Run as MELEE_PAD_SCRIPT with MELEE_SCENE="mode=lab;p1=geno:<key>/hu;p2=mario/cpu0;stage=fd" (see run_moves_check.sh).
-- For every normal, aerial, grab, throw and special it does two passes from one saved state:
--   A  on an empty stage: records, per logic frame, the action name, action frame and the live hitboxes;
--   B  with P2 placed on the first live hitbox: records whether the move connects, the damage dealt and P2's state.
-- Output: one log line per move, "MOVECHK {json}", then "MOVECHK DONE n". moves_report.py joins these with the
-- declared data (tools.geno.report --frames). Env-free: the fighter is whatever P1 is.
-- Frame convention: a hitbox is live from readout action frame N-2 of its script `wait N` (geno.md 22).
local ONLY = {}  -- fill to run a subset, e.g. ONLY = {jab1 = true}
local M = {}
local order = {}
local function add(name, steps, tm, extra)
  local m = {steps = steps, tm = tm}
  for k, v in pairs(extra or {}) do m[k] = v end
  M[name] = m
  order[#order + 1] = name
end
local function A(spec, n) return {'in', spec, n or 2} end
local function S(n) return {'s', n} end
local function U(set, maxn, minaf) return {'until', set, maxn, minaf or 0} end
local function set(...) local t = {}; for _, v in ipairs({...}) do t[v] = true end; return t end
local AIR = {A({buttons = 'X'}, 2), U(set('JumpF', 'JumpB'), 40, 3)}
local DASH = {A({x = 127}, 4), U(set('Dash', 'Run'), 20, 0)}
local GRABX = {A('Z', 2), U(set('CatchWait'), 60, 0), S(4)}
local function TP(y) return {'tp', y} end
local function cat(...) local r = {}; for _, t in ipairs({...}) do for _, v in ipairs(t) do r[#r + 1] = v end end; return r end

add('jab1', cat({A({buttons = 'A'}), S(40)}), set('Attack11'))
add('jab2', cat({A({buttons = 'A'}), U(set('Attack11'), 30, 5), A({buttons = 'A'}), S(40)}), set('Attack12'))
add('jab3', cat({A({buttons = 'A'}), U(set('Attack11'), 30, 5), A({buttons = 'A'}), U(set('Attack12'), 30, 5), A({buttons = 'A'}), S(40)}), set('Attack13'))
add('dash_attack', cat(DASH, {A({buttons = 'A', x = 70}), S(50)}), set('AttackDash'))
add('ftilt', cat({A({buttons = 'A', x = 45}), S(40)}), set('AttackS3S'))
add('ftilt_up', cat({A({buttons = 'A', x = 45, y = 45}), S(40)}), set('AttackS3Hi', 'AttackS3HiS'))
add('ftilt_down', cat({A({buttons = 'A', x = 45, y = -45}), S(40)}), set('AttackS3Lw', 'AttackS3LwS'))
add('utilt', cat({A({buttons = 'A', y = 35}), S(40)}), set('AttackHi3'))
add('dtilt', cat({A({buttons = 'A', y = -35}), S(40)}), set('AttackLw3'))
add('fsmash', cat({A({cx = 127}), S(70)}), set('AttackS4S'))
add('fsmash_up', cat({A({cx = 100, cy = 60}), S(70)}), set('AttackS4Hi', 'AttackS4HiS'))
add('fsmash_down', cat({A({cx = 100, cy = -60}), S(70)}), set('AttackS4Lw', 'AttackS4LwS'))
add('usmash', cat({A({cy = 127}), S(70)}), set('AttackHi4'))
add('dsmash', cat({A({cy = -127}), S(70)}), set('AttackLw4'))
add('nair', cat(AIR, {A({buttons = 'A'}), S(50)}), set('AttackAirN'), {air = true})
add('fair', cat(AIR, {A({cx = 127}), S(50)}), set('AttackAirF'), {air = true})
add('bair', cat(AIR, {A({cx = -127}), S(50)}), set('AttackAirB'), {air = true})
add('uair', cat(AIR, {A({cy = 127}), S(50)}), set('AttackAirHi'), {air = true})
add('dair', cat(AIR, {A({cy = -127}), S(50)}), set('AttackAirLw'), {air = true})
add('grab', cat({A('Z'), S(40)}), set('Catch'))
add('dash_grab', cat(DASH, {A('Z'), S(50)}), set('CatchDash'))
add('pummel', cat(GRABX, {A({buttons = 'A'}), S(30)}), set('CatchAttack'), {place = 'grab'})
add('fthrow', cat(GRABX, {A({x = 127}, 3), S(60)}), set('ThrowF'), {place = 'grab'})
add('bthrow', cat(GRABX, {A({x = -127}, 3), S(60)}), set('ThrowB'), {place = 'grab'})
add('uthrow', cat(GRABX, {A({y = 127}, 3), S(60)}), set('ThrowHi'), {place = 'grab'})
add('dthrow', cat(GRABX, {A({y = -127}, 3), S(60)}), set('ThrowLw'), {place = 'grab'})
-- landing lag: drop the fighter from 8 units up, start the aerial in the fall, so it lands inside the attack
local function LAND(spec) return {TP(8), S(2), A(spec), S(50)} end
add('land_nair', LAND({buttons = 'A'}), set('AttackAirN'), {landing_only = true})
add('land_fair', LAND({cx = 127}), set('AttackAirF'), {landing_only = true})
add('land_bair', LAND({cx = -127}), set('AttackAirB'), {landing_only = true})
add('land_uair', LAND({cy = 127}), set('AttackAirHi'), {landing_only = true})
add('land_dair', LAND({cy = -127}), set('AttackAirLw'), {landing_only = true})

-- Sora's specials (Geno states in both the m-ex install and the define): the same inputs on both, the motion names are the states'.
local ART = {art = true}
add('n_fire', cat({A({buttons = 'B'}, 3), S(90)}), set('Firaga', 'FiragaFire', 'FiragaEnd', 'FiragaRepeat'), ART)
add('n_fire_held', cat({A({buttons = 'B'}, 40), S(90)}), set('Firaga', 'FiragaFire', 'FiragaEnd', 'FiragaRepeat'), ART)
add('air_n_fire', cat(AIR, {A({buttons = 'B'}, 3), S(90)}), set('FiragaAir', 'FiragaFireAir', 'FiragaEndAir', 'FiragaRepeatAir'), {air = true, art = true})
-- the cast cycle (LA int 0 advances when a cast is entered): the second and third casts are Blizzaga and Thundaga
local ALLN = set('Firaga', 'FiragaFire', 'FiragaEnd', 'FiragaRepeat', 'Blizzaga', 'Thundaga', 'FiragaAir', 'FiragaFireAir', 'FiragaEndAir', 'FiragaRepeatAir', 'BlizzagaAir', 'ThundagaAir')
add('n_cycle2', cat({A({buttons = 'B'}, 3), S(75), A({buttons = 'B'}, 3), S(90)}), ALLN, ART)
add('n_cycle3', cat({A({buttons = 'B'}, 3), S(75), A({buttons = 'B'}, 3), S(75), A({buttons = 'B'}, 3), S(90)}), ALLN, ART)
add('air_n_cycle2', cat(AIR, {A({buttons = 'B'}, 3), S(60), A({buttons = 'B'}, 3), S(60)}), ALLN, {air = true, art = true})
add('air_n_cycle3', cat(AIR, {A({buttons = 'B'}, 3), S(40), A({buttons = 'B'}, 3), S(40), A({buttons = 'B'}, 3), S(60)}), ALLN, {air = true, art = true})
add('s_dash', cat({A({buttons = 'B', x = 127}, 3), S(90)}), set('SStart', 'SStart2', 'SDash1', 'SDash2', 'SDash3', 'SEnd', 'SEndAir', 'SSearch', 'STurnUp', 'STurnDown'))
add('s_dash_chain', cat({A({buttons = 'B', x = 127}, 3), S(14), A({buttons = 'B', x = 127}, 3), S(14), A({buttons = 'B', x = 127}, 3), S(60)}), set('SStart', 'SStart2', 'SDash1', 'SDash2', 'SDash3', 'SEnd', 'SEndAir', 'SSearch', 'STurnUp', 'STurnDown'))
add('air_s_dash', cat(AIR, {A({buttons = 'B', x = 127}, 3), S(90)}), set('SStart', 'SStart2', 'SDash1', 'SDash2', 'SDash3', 'SEnd', 'SEndAir', 'SSearch', 'STurnUp', 'STurnDown'), {air = true})
add('hi', cat({A({buttons = 'B', y = 127}, 3), S(90)}), set('Hi', 'HiAir'))
add('air_hi', cat(AIR, {A({buttons = 'B', y = 127}, 3), S(90)}), set('Hi', 'HiAir'), {air = true})
add('lw_start', cat({A({buttons = 'B', y = -127}, 3), S(90)}), set('LwStart', 'LwAttack', 'LwAttackBack'))
add('air_lw_start', cat(AIR, {A({buttons = 'B', y = -127}, 3), S(90)}), set('LwStartAir', 'LwAttackAir', 'LwAttackBackAir'), {air = true})
add('counter', cat({A({buttons = 'B', y = -127}), S(70)}), set('LwStart', 'LwAttack', 'LwAttackBack'))

-- minimal JSON writer (arrays: tables with [1]; objects otherwise; keys sorted)
local function js(v)
  local t = type(v)
  if t == 'nil' then return 'null' end
  if t == 'boolean' or t == 'number' then
    if t == 'number' then return string.format('%.4g', v) end
    return tostring(v)
  end
  if t == 'string' then return '"' .. v:gsub('[%c"\\]', function(c) return string.format('\\u%04x', c:byte()) end) .. '"' end
  if t == 'table' then
    if v[1] ~= nil or next(v) == nil then
      local r = {}
      for i, x in ipairs(v) do r[i] = js(x) end
      return '[' .. table.concat(r, ',') .. ']'
    end
    local keys = {}
    for k in pairs(v) do keys[#keys + 1] = k end
    table.sort(keys)
    local r = {}
    for _, k in ipairs(keys) do r[#r + 1] = js(k) .. ':' .. js(v[k]) end
    return '{' .. table.concat(r, ',') .. '}'
  end
  return 'null'
end

-- a log line is cut near 2000 characters, so a long record goes out in numbered parts (moves_diff.py joins them)
local function emit(rec)
  local t = js(rec)
  if #t <= 1400 then gd.log('MOVECHK ' .. t); return end
  local n = math.ceil(#t / 1400)
  for i = 1, n do gd.log(string.format('MOVECHKPART %s %d %d %s', rec.name, i, n, t:sub((i - 1) * 1400 + 1, i * 1400))) end
end

local frames
local function sample()
  gd.wait(1)
  local p, m = gd.player(1), gd.player(2)
  local hb = {}
  for _, b in ipairs(gd.hitboxes(1) or {}) do
    hb[#hb + 1] = {bone = b.bone, x = b.x, y = b.y, z = b.z, r = b.radius, dmg = b.damage, ang = b.angle, kbg = b.kbg, bkb = b.bkb}
  end
  local its = {}
  for _, it in ipairs(gd.items() or {}) do
    its[#its + 1] = {k = it.geno_kind or -1, a = it.frame_alive, x = it.x, y = it.y, vx = it.vx, vy = it.vy}
  end
  local f = {it = its, mot = p.motion_name, af = math.floor(p.action_frame or 0), x = p.x, y = p.y, face = p.facing, hb = hb,
             mper = m.percent, mmot = m.motion_name, mx = m.x, my = m.y, mvx = m.vx, mvy = m.vy, per = p.percent,
             hit = (p.hitlag or p.in_hitlag) and 1 or 0}
  frames[#frames + 1] = f
  return f
end

local function run_steps(steps, hook)
  frames = {}
  for _, s in ipairs(steps) do
    if s[1] == 'in' then
      gd.input(1, s[2], s[3])
      for _ = 1, s[3] do
        if hook then hook() end
        sample()
      end
    elseif s[1] == 's' then
      for _ = 1, s[2] do
        if hook then hook() end
        sample()
      end
    elseif s[1] == 'tp' then
      local l = frames[#frames]
      gd.teleport(1, l and l.x or gd.player(1).x, s[2])
    elseif s[1] == 'until' then
      for _ = 1, s[3] do
        local l = frames[#frames]
        if l and s[2][l.mot] and l.af >= s[4] then break end
        if hook then hook() end
        sample()
      end
    end
  end
  return frames
end

local function first_active(fr, tm)
  for i, f in ipairs(fr) do
    if tm[f.mot] and #f.hb > 0 then return i end
  end
end

local function reset(slot)
  gd.input(1, {}, 1)
  gd.loadstate(slot)
  gd.wait(3)
  frames = {}
end

local function seen_list(fr, key)
  local r = {}
  for _, f in ipairs(fr) do
    if r[#r] ~= f[key] then r[#r + 1] = f[key] end
  end
  return r
end


-- the first and last action frame at which the move's own hitboxes were live, and the union of what they were
local function collect(fr, tm)
  local rec = {}
  local lo, hi, groups = nil, nil, {}
  for _, f in ipairs(fr) do
    if tm[f.mot] and #f.hb > 0 then
      lo = lo or f.af
      hi = f.af
      for _, b in ipairs(f.hb) do
        local key = string.format('%d/%.4g/%.4g', b.bone, b.dmg, b.ang)
        if not groups[key] then groups[key] = {bone = b.bone, dmg = b.dmg, ang = b.ang, kbg = b.kbg, bkb = b.bkb, r = b.r, first_af = f.af, last_af = f.af}
        else groups[key].last_af = f.af end
      end
    end
  end
  rec.active_lo, rec.active_hi = lo, hi
  -- landing lag after an aerial: frames spent in a LandingAir* action (unless it is cut short)
  local lf, lname = 0, nil
  for _, f in ipairs(fr) do
    if f.mot and f.mot:find('^LandingAir') then lf = lf + 1; lname = f.mot end
  end
  if lf > 0 then rec.landing = {name = lname, frames = lf} end
  local g = {}
  for _, v in pairs(groups) do g[#g + 1] = v end
  table.sort(g, function(a, b)   -- a total order, so two runs list equal-start groups alike
    for _, k in ipairs({'first_af', 'bone', 'dmg', 'ang', 'bkb', 'kbg', 'r', 'last_af'}) do
      if a[k] ~= b[k] then return a[k] < b[k] end
    end
    return false
  end)
  rec.groups = g
  return rec
end

-- articles seen in a pass: per kind, the pass frame it first showed, the highest frame_alive, its first x/y relative to the fighter and its first speed
local function item_summary(fr)
  local out = {}
  for i, f in ipairs(fr) do
    for _, it in ipairs(f.it or {}) do
      local key = tostring(it.k)
      local o = out[key]
      if not o then
        o = {kind = it.k, first = i, life = 0, dx = (it.x - f.x) * f.face, dy = it.y - f.y, vx = it.vx * f.face, vy = it.vy, n = 0}
        out[key] = o
      end
      o.n = o.n + 1
      if (it.a or 0) > o.life then o.life = it.a end
      o.last = i
    end
  end
  local r = {}
  for _, v in pairs(out) do r[#r + 1] = v end
  table.sort(r, function(a, b) if a.first ~= b.first then return a.first < b.first end return a.kind < b.kind end)
  return r
end

local function check_move(name, mv, slot)
  local rec = {name = name}
  gd.log('MOVECHK START ' .. name)
  reset(slot)
  local fr = run_steps(mv.steps)
  if mv.landing_only then
    -- a short aerial ends before it can land from 8 units up: drop from lower until it lands inside the attack
    for _, h in ipairs({4, 2.5, 1.5}) do
      local landed = false
      for _, f in ipairs(fr) do if f.mot and f.mot:find('^LandingAir') then landed = true end end
      if landed then break end
      mv.steps[1][2] = h
      reset(slot)
      fr = run_steps(mv.steps)
    end
  end
  local copyA = {}
  for i, f in ipairs(fr) do copyA[i] = f end
  rec.seen = seen_list(copyA, 'mot')
  local i = first_active(copyA, mv.tm)
  local inmove = 0
  for _, f in ipairs(copyA) do if mv.tm[f.mot] then inmove = inmove + 1 end end
  rec.frames_in_move = inmove
  rec.items = item_summary(copyA)
  do
    local c = collect(copyA, mv.tm)
    for k, v in pairs(c) do rec[k] = v end
  end
  if mv.place == 'grab' then
    -- throws and the pummel need a held victim, so pass A (empty stage) has nothing to say; Mario is put 5 units in
    -- front and the whole sequence (grab, hold, then the move) is run once with him there.
    local face = copyA[1] and copyA[1].face or 1
    reset(slot)
    gd.teleport(2, copyA[1].x + 5 * face, 0)
    local fr3 = run_steps(mv.steps)
    local c = collect(fr3, mv.tm)
    for k, v in pairs(c) do rec[k] = v end
    rec.captured = false
    for _, ff in ipairs(fr3) do if ff.mmot and ff.mmot:find('^Capture') then rec.captured = true; break end end
    rec.mseen = seen_list(fr3, 'mmot')
    rec.seen = seen_list(fr3, 'mot')
    local hold_per
    for _, ff in ipairs(fr3) do if ff.mot == 'CatchWait' then hold_per = ff.mper; break end end
    local m0 = hold_per or fr3[1].mper
    local mmax = m0
    for _, ff in ipairs(fr3) do if ff.mper > mmax then mmax = ff.mper end end
    rec.hit = mmax > m0
    rec.dmg_dealt = mmax - m0
    local bv, bn = -1, 1
    for n, ff in ipairs(fr3) do
      local v = math.sqrt(ff.mvx ^ 2 + ff.mvy ^ 2)
      if v > bv then bv, bn = v, n end
    end
    rec.launch = {fr3[bn].mvx, fr3[bn].mvy}
    rec.victim_state = fr3[#fr3].mmot
    emit(rec)
    return rec
  end
  if mv.landing_only then
    emit(rec)
    return rec
  end
  if mv.art then
    -- Mario stands 10 and 24 units in front: the damage the move's articles (and the fighter's own hitboxes) do to him
    rec.art_hits = {}
    for _, dist in ipairs({10, 24}) do
      reset(slot)
      local x0 = gd.player(1).x
      local face = gd.player(1).facing or 1
      gd.teleport(2, x0 + dist * face, 0)
      local fr2 = run_steps(mv.steps)
      local m0 = fr2[1].mper
      local mmax = m0
      for _, ff in ipairs(fr2) do if ff.mper > mmax then mmax = ff.mper end end
      rec.art_hits[#rec.art_hits + 1] = {dist = dist, dmg = mmax - m0, mseen = seen_list(fr2, 'mmot'), items = item_summary(fr2)}
    end
  end
  if not i then
    rec.hitbox = false
    emit(rec)
    return rec
  end
  rec.hitbox = true
  local f = copyA[i]
  rec.first_active_af = f.af
  -- pass B: P2 on the first live hitbox (the grab's, for moves that need a held victim)
  local hx, hy = nil, nil
  local pi = i
  if mv.place == 'grab' then
    local gi = first_active(copyA, set('Catch'))
    if gi then pi = gi; hx, hy = copyA[gi].hb[1].x, copyA[gi].hb[1].y end
  end
  if not hx then
    local best = f.hb[1]
    for _, b in ipairs(f.hb) do if (b.x - f.x) * f.face > (best.x - f.x) * f.face then best = b end end
    hx, hy = best.x, best.y
  end
  local my = ((mv.air or hy > 9) and math.max(0, hy - 6)) or 0
  rec.place = {hx - f.x, my}
  reset(slot)
  local done = false
  local fr2 = run_steps(mv.steps, function()
    if not done and #frames == pi - 1 then
      gd.teleport(2, hx, my)
      done = true
    end
  end)
  local m0 = fr2[1].mper
  local mmax = m0
  for _, ff in ipairs(fr2) do if ff.mper > mmax then mmax = ff.mper end end
  rec.B_active = first_active(fr2, mv.tm) ~= nil
  rec.hit = mmax > m0
  rec.mseen = seen_list(fr2, 'mmot')
  if rec.hit then
    local k
    for n, ff in ipairs(fr2) do if ff.mper > m0 then k = n; break end end
    rec.dmg_dealt = fr2[k].mper - m0
    rec.hit_motion = fr2[k].mot
    rec.hit_af = fr2[k].af
    local best, bv = k, -1
    for n = k, math.min(k + 12, #fr2) do
      local v = math.sqrt(fr2[n].mvx ^ 2 + fr2[n].mvy ^ 2)
      if v > bv then bv, best = v, n end
    end
    rec.launch = {fr2[best].mvx, fr2[best].mvy}
    rec.victim_state = fr2[math.min(k + 3, #fr2)].mmot
  end
  if mv.place == 'grab' then
    -- a held victim: did the grab connect at all
    for _, ff in ipairs(fr2) do
      if ff.mmot and ff.mmot:find('^Capture') then rec.captured = true; break end
    end
  end
  emit(rec)
  return rec
end


-- the counter: Mario is put next to the fighter, turns, and jabs at a chosen frame of the counter; early and late
-- are inside the window, "out" is after it. A counter is "worked" when the fighter takes no damage and the
-- counter-strike state is entered.
local function check_counter(name, slot)
  local rec = {name = name, cases = {}}
  gd.log('MOVECHK START ' .. name)
  for _, case in ipairs({{'early', 8}, {'late', 16}, {'out_of_window', 45}}) do
    reset(slot)
    local p0 = gd.player(1)
    local fc = p0.facing or 1
    gd.teleport(2, p0.x + 4 * fc, 0)
    gd.cpu_mode(2, 'script')
    gd.cpu_pad(2, {x = -50 * fc}, 2)
    gd.wait(4)
    local per1 = gd.player(1).percent
    local per2 = gd.player(2).percent
    gd.input(1, {buttons = 'B', y = -127}, 3)
    local seen, mseen, k = {}, {}, 0
    for k = 0, 89 do
      if k == case[2] then gd.cpu_pad(2, {buttons = 'A'}, 2) end
      local f = sample()
      if seen[#seen] ~= f.mot then seen[#seen + 1] = f.mot end
      if mseen[#mseen] ~= f.mmot then mseen[#mseen + 1] = f.mmot end
    end
    gd.cpu_mode(2, 'stand')
    rec.cases[#rec.cases + 1] = {case = case[1], jab_at = case[2], fighter = seen, mario = mseen,
                                 fighter_damage = gd.player(1).percent - per1, mario_damage = gd.player(2).percent - per2}
  end
  emit(rec)
  return rec
end

gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no match')
    gd.cpu_mode(2, 'stand')
    gd.teleport(1, 0, 0)
    gd.teleport(2, -70, 0)
    gd.set_percent(1, 0)
    gd.set_percent(2, 0)
    gd.wait(30)
    local p = gd.player(1)
    gd.log('MOVECHK FIGHTER ' .. js({char = p.char, char_name = p.char_name, motion = p.motion_name, face = p.facing, x = p.x, y = p.y,
                                     attrs = gd.attrs and gd.attrs(1) or nil}))
    gd.savestate(1)
    gd.wait(2)
    local n = 0
    for _, name in ipairs(order) do
      if next(ONLY) == nil or ONLY[name] then
        local ok2, err
        if name == 'counter' then ok2, err = pcall(check_counter, name, 1) else ok2, err = pcall(check_move, name, M[name], 1) end
        if not ok2 then gd.log('MOVECHK ' .. js({name = name, error = tostring(err)})) end
        n = n + 1
      end
    end
    gd.log('MOVECHK DONE ' .. n)
  end)
  if not ok then gd.log('MOVECHK FAIL ' .. tostring(why)) end
  gd.quit()
end)
