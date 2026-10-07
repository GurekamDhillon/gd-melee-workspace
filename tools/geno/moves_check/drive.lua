-- Headless driver for a whole mode with a Geno fighter as P1. run_drive.sh prepends `local MODE = "win" | "lose"`.
--   win  : P1 is flown by the debug cursor to the nearest living foe and attacks it (gd.fly_attack), so every stage
--          ends; the fighter is not playing its own moves (that is moves_check.lua's job). Items are picked up when
--          no foe is left. Stage clears, boss hands, team stages, bonus stages, results and credits are real.
--   lose : P1 stands still, the CPU takes its stocks: the fighter's damage, KO, death and loser's results path.
-- Presses START every 90 ticks while no match is running (result screens wait for it). Logs "DRIVE ..." lines and quits
-- 300 frames after the results screen of a versus match, or after the Classic credits (STAFFROLL left / MOVIE_END).
local n, quit_at, scenes, nofoe = 0, nil, {}, 0
local function log(s) gd.log('DRIVE ' .. s) end
local function foes(p1)
  local l = {}
  for _, p in ipairs(gd.players()) do
    if p.port ~= 1 and (p.stocks or 1) > 0 and type(p.x) == 'number'
       and not (p1.team and p.team == p1.team and p1.team >= 0 and gd.match().teams) then l[#l + 1] = p end
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
  log('scene ' .. tostring(name) .. ' prev ' .. tostring(prev) .. ' tick ' .. n)
  if MODE == 'win' or MODE == 'lose' then
    if name == 'GS_RESULTS' or name == 'GS_MOVIE_END' then quit_at = n + 600 end
  end
end
function on_tick()
  n = n + 1
  if quit_at and n >= quit_at then
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
  if n % 600 == 0 then
    local s = {}
    for _, p in ipairs(gd.players()) do
      s[#s + 1] = ('P%d %s %.0f%% st=%s %s'):format(p.port, tostring(p.char_name), p.percent or 0, tostring(p.stocks), tostring(p.motion_name))
    end
    log('frame ' .. tostring(m.frame) .. ' ' .. table.concat(s, ' | '))
  end
  if MODE ~= 'win' or m.frame < 90 then return end
  local p1 = gd.player(1)
  if not p1 or type(p1.x) ~= 'number' or (p1.stocks or 0) <= 0 then return end
  if not gd.fly_enabled_once then gd.fly_enabled_once = true; pcall(gd.fly_speed, 3.2) end
  local t = nearest(foes(p1), p1.x, p1.y)
  -- the stage is won but the 1P results overlay is still a "match": it waits for START (retail's own rule)
  nofoe = t and 0 or nofoe + 1
  if nofoe > 200 and nofoe % 120 == 0 then gd.input(1, 'START', 5) end
  if t then
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
