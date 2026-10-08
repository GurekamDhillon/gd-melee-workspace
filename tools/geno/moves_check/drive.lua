-- Headless driver for a whole mode with a Geno fighter as P1. run_drive.sh prepends `local MODE = "win" | "lose"`.
--   win  : P1 is flown by the debug cursor to the nearest living foe and attacks it (gd.fly_attack), so every stage
--          ends; the fighter is not playing its own moves (that is moves_check.lua's job). Items are picked up when
--          no foe is left. Stage clears, boss hands, team stages, bonus stages, results and credits are real.
--   play : P1 plays its own moves: every 40 ticks it is put next to the nearest foe, turned toward it, and the next input
--          of a fixed rotation (jab, tilts, smashes, grab, the four specials, aerials) is held; if a scene lasts more
--          than 9000 ticks it falls back to `win` so the stage still ends.
--   kirby: P1 stands; P2 (a Kirby, CPU in script mode) is put next to it, turned, and holds B (the inhale) for 90 ticks,
--          then waits 120 and tries again: a define as a Kirby copy source (known default arm, geno.md 22.1).
--   lose : P1 stands still, the CPU takes its stocks: the fighter's damage, KO, death and loser's results path.
-- Presses START every 90 ticks while no match is running (result screens wait for it). Logs "DRIVE ..." lines and quits
-- 300 frames after the results screen of a versus match, or after the Classic credits (STAFFROLL left / MOVIE_END).
local n, quit_at, scenes, nofoe, last_scene = 0, nil, {}, 0, 0
local last_sum, same_for = -1, 0
local ROT = {{buttons='A'}, {buttons='A', x=45}, {cx=127}, {buttons='B'}, {buttons='A', y=35}, {cy=127}, {buttons='B', x=127}, 'Z',
             {buttons='A', y=-35}, {cy=-127}, {buttons='B', y=127}, {buttons='B', y=-127}, {buttons='X'}, {buttons='A'}, {cx=-127}, {buttons='A', x=45}}
local rot_i = 0
local kirby_init = false
local seen_mot, seen_n = {}, 0
local function note_motion(p)
  local k = tostring(p.motion_name)
  if not seen_mot[k] then seen_mot[k] = true; seen_n = seen_n + 1 end
end
local function log(s) gd.log('DRIVE ' .. s) end
local function foes(p1)
  local l, teams, nteams = {}, {}, 0
  for _, p in ipairs(gd.players()) do
    if p.team and not teams[p.team] then teams[p.team] = true; nteams = nteams + 1 end
  end
  -- teammates only when the match really has more than one team (a plain versus match reports team 0 for all)
  local allies = nteams > 1
  for _, p in ipairs(gd.players()) do
    if p.port ~= 1 and (p.stocks or 1) > 0 and type(p.x) == 'number'
       and not (allies and p1.team and p.team == p1.team and p1.team >= 0) then l[#l + 1] = p end
  end
  return l
end
local function nearest(l, x, y)
  local b, bd
  for _, e in ipairs(l) do
    local d = (e.x - x) ^ 2 + (e.y - y) ^ 2
    if not bd or d < bd then b, bd = e, d end
  end
  return b
end
function on_scene(kind, name, prev)
  scenes[#scenes + 1] = name
  last_scene = n
  log('scene ' .. tostring(name) .. ' prev ' .. tostring(prev) .. ' tick ' .. n)
  if MODE == 'win' or MODE == 'lose' or MODE == 'play' then
    if name == 'GS_RESULTS' or name == 'GS_MOVIE_END' then quit_at = n + 600 end
  end
end
function on_action_change(port, old, new, sub)
  if port == 1 and TRACE then
    local p = gd.player(1)
    log(('act %s(%s) -> %s(%s) sub %s af %s x %.1f y %.1f'):format(tostring(gd.motion_name(old, 1)), tostring(old), tostring(gd.motion_name(new, 1)),
        tostring(new), tostring(sub), tostring(p and p.anim_symbol), p and p.x or 0, p and p.y or 0))
  end
end
function on_tick()
  n = n + 1
  if n > 700000 and not quit_at then log('CAP: 700000 ticks'); quit_at = n + 5 end
  if n - last_scene > 60000 and not quit_at then log('STALL: no scene change for 60000 ticks'); quit_at = n + 5 end
  if quit_at and n >= quit_at then
    local ml = {}
    for k in pairs(seen_mot) do ml[#ml + 1] = k end
    table.sort(ml)
    log('P1 motions seen (' .. seen_n .. '): ' .. table.concat(ml, ' '))
    log('quit after ' .. table.concat(scenes, ' > '))
    gd.quit()
    quit_at = nil
    return
  end
  local m = gd.match()
  if not (m and m.active) then
    if n % 90 == 0 then gd.input(1, 'START', 5) end
    return
  end
  do local q = gd.player(1); if q then note_motion(q) end end
  if n % 600 == 0 then
    local s = {}
    for _, p in ipairs(gd.players()) do
      s[#s + 1] = ('P%d %s %.0f%% st=%s t%s %s'):format(p.port, tostring(p.char_name), p.percent or 0, tostring(p.stocks), tostring(p.team), tostring(p.motion_name))
    end
    log('frame ' .. tostring(m.frame) .. ' teams=' .. tostring(m.teams) .. ' ' .. table.concat(s, ' | '))
  end
  if MODE == 'kirby' and m.frame > 90 then
    local p1, p2 = gd.player(1), gd.player(2)
    if p1 and p2 and type(p1.x) == 'number' then
      if not kirby_init then kirby_init = true; gd.cpu_mode(2, 'script'); log('kirby: P2 is ' .. tostring(p2.char_name)) end
      local k = (n - 200) % 260
      if n > 200 and k == 0 then
        local dir = p1.facing or 1
        gd.teleport(2, p1.x + 8 * dir, p1.y)
        gd.cpu_pad(2, {x = -60 * dir}, 3)
      elseif n > 200 and k == 10 then
        gd.cpu_pad(2, {buttons = 'B'}, 90)
      end
      if n % 60 == 0 then log(('kirby: P1 %s %s | P2 %s %s'):format(tostring(p1.char_name), tostring(p1.motion_name), tostring(p2.char_name), tostring(p2.motion_name))) end
    end
    if n > 3000 then quit_at = quit_at or (n + 5) end
    return
  end
  if (MODE ~= 'win' and MODE ~= 'play') or m.frame < 90 then return end
  local p1 = gd.player(1)
  if not p1 or type(p1.x) ~= 'number' or (p1.stocks or 0) <= 0 then return end
  if not gd.fly_enabled_once then gd.fly_enabled_once = true; pcall(gd.fly_speed, 3.2) end
  local t = nearest(foes(p1), p1.x, p1.y)
  -- the stage is won but the 1P results overlay is still a "match": it waits for START (retail's own rule)
  nofoe = t and 0 or nofoe + 1
  if nofoe > 200 and nofoe % 120 == 0 then gd.input(1, 'START', 5) end
  -- a living foe that is not being hurt for 600 ticks (a boss waiting in Sleep after the final results are up): tap START
  local sum = 0
  for _, p in ipairs(gd.players()) do sum = sum + (p.percent or 0) + (p.stocks or 0) * 1000 end
  if sum == last_sum then same_for = same_for + 1 else same_for = 0; last_sum = sum end
  if same_for > 600 and same_for % 120 == 0 then gd.input(1, 'START', 5) end
  local playing = MODE == 'play' and (n - last_scene) < 2500
  if t and playing then
    local dir = (t.x >= p1.x) and 1 or -1
    if n % 40 == 0 then
      pcall(gd.teleport, 1, t.x - 7 * dir, t.y)
      gd.input(1, {x = 60 * dir}, 3)
    elseif n % 40 == 6 then
      rot_i = rot_i % #ROT + 1
      local spec = ROT[rot_i]
      if type(spec) == 'table' then
        local sp = {}
        for k, v in pairs(spec) do sp[k] = (k == 'x' or k == 'cx') and v * dir or v end
        gd.input(1, sp, 30)
      else
        gd.input(1, spec, 30)
      end
    end
  elseif t then
    if pcall(gd.fly_target, 1, t.x, t.y + 4) then pcall(gd.fly_attack, 1, true, 6, 9) end
  elseif gd.items then
    pcall(gd.fly_attack, 1, false)
    local it = nearest(gd.items() or {}, p1.x, p1.y)
    if it and type(it.x) == 'number' then
      pcall(gd.fly_target, 1, it.x, it.y)
      if (it.x - p1.x) ^ 2 + (it.y - p1.y) ^ 2 < 100 and n % 20 < 4 then pcall(gd.input, 1, 'A', 2) end
    end
  end
end
log('driver loaded, mode ' .. tostring(MODE))
