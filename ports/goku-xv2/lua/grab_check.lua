-- Grab family gate: every grab / pummel / throw / release / whiff returns Goku to an actionable state within its frame budget, both facings,
-- and Goku held/thrown by the opponent frees up too. Also logs the victim's offset from Goku while held (GRABCHECK held lines).
-- Scene: mode=lab;p1=geno:goku-xv2/hu;p2=<mario|fox|marth|captain>/cpu0 . Logs GRABCHECK lines, ends with GRABCHECK RESULT PASS|FAIL.
local FREE = {}
for _, n in ipairs({ "Wait", "WalkSlow", "WalkMiddle", "WalkFast", "Turn", "Dash", "Run", "RunDirect", "Squat", "SquatWait", "SquatRv",
  "Fall", "FallF", "FallB", "FallAerial", "JumpF", "JumpB", "GuardOn", "Guard" }) do FREE[n] = true end
local function free(p)
  local n = p.motion_name or ""
  if p.in_hitlag or (p.hitlag or 0) > 0 then return false end
  return FREE[n] == true
end
local fails, cases = {}, 0
local function log(fmt, ...) gd.log('GRABCHECK ' .. string.format(fmt, ...)) end
local function verdict(name, side, ok, detail)
  cases = cases + 1
  log('case=%s side=%d %s %s', name, side, ok and 'PASS' or 'FAIL', detail)
  if not ok then fails[#fails + 1] = name .. '/' .. side end
end
local function wait_until_motion(port, pred, maxf)
  for i = 1, maxf do
    local p = gd.player(port)
    if p and pred(p) then return i end
    gd.wait(1)
  end
  return nil
end
local function hold1(spec, f) gd.input(1, spec, f or 2) gd.wait(f or 2) end

local function settle()
  -- both fighters actionable and unheld before any teleport (a held fighter cannot be placed)
  wait_until_motion(1, free, 400)
  wait_until_motion(2, free, 400)
  gd.wait(10)
end

local function reset(side)
  settle()
  gd.cpu_pad(2, {}, 1)
  gd.set_percent(1, 0); gd.set_percent(2, 0)
  gd.teleport(1, 0, 0); gd.teleport(2, side * 30, 0)
  gd.wait(40)
  hold1({ x = side * 60 }, 3) -- face the dummy
  gd.wait(30)
  gd.teleport(1, 0, 0); gd.teleport(2, side * 7, 0)
  gd.wait(2)
  if not wait_until_motion(1, free, 60) then return false end
  return true
end

local function sample_held(side, tag, n)
  for i = 1, n do
    local g, v = gd.player(1), gd.player(2)
    log('held case=%s side=%d f=%d goku=%s af=%d victim=%s dx=%.2f dy=%.2f vfacing=%s', tag, side, i, g.motion_name, g.anim_frame or -1,
      v.motion_name, (v.x - g.x) * side, v.y - g.y, tostring(v.facing))
    gd.wait(3)
  end
end

local shots = false -- turbo frames are not presented: screenshots are black; set true for a --visible run
local function shot(tag)
  if not shots then return end
  local ok, path = gd.screenshot('grabcheck-' .. tag .. '.png')
  log('shot %s queued=%s path=%s', tag, tostring(ok), tostring(path))
end

local function grab_then(name, side, after, budget)
  if not reset(side) then verdict(name, side, false, 'never actionable at start') return end
  hold1({ buttons = 'Z' }, 2)
  local caught = wait_until_motion(1, function(p) return p.motion_name == 'CatchWait' end, 45)
  if not caught then
    verdict(name, side, false, 'grab did not connect (Goku=' .. tostring(gd.player(1).motion_name) .. ')')
    wait_until_motion(1, free, 120)
    return
  end
  sample_held(side, name, 4)
  if side == 1 then shot(name .. '-held') end
  local t0 = gd.match().frame
  after()
  if side == 1 and name:find('throw') then gd.wait(9) shot(name .. '-t9') end
  local got
  for i = 1, budget do
    local g = gd.player(1)
    if free(g) then got = i break end
    if name:find('throw') and i % 10 == 1 and i < 260 then
      log('trace case=%s side=%d t=%d goku=%s af=%d anim=%s hitlag=%s victim=%s', name, side, i, g.motion_name, g.action_frame or -1, tostring(g.anim_name), tostring(g.hitlag), tostring((gd.player(2) or {}).motion_name))
    end
    gd.wait(1)
  end
  local took = gd.match().frame - t0
  verdict(name, side, got ~= nil, string.format('free after %d frames (budget %d) goku=%s', took, budget, tostring(gd.player(1).motion_name)))
  wait_until_motion(1, free, 200)
end

local function whiff(name, side, setup, budget)
  settle()
  gd.cpu_pad(2, {}, 1)
  gd.teleport(1, 0, 0); gd.teleport(2, side * 60, 0)
  gd.wait(40)
  hold1({ x = side * 60 }, 3); gd.wait(20)
  gd.teleport(1, 0, 0); gd.teleport(2, side * 60, 0)
  wait_until_motion(1, free, 60)
  setup()
  local t0 = gd.match().frame
  local got = wait_until_motion(1, free, budget)
  verdict(name, side, got ~= nil, string.format('free after %d frames (budget %d) goku=%s', gd.match().frame - t0, budget, tostring(gd.player(1).motion_name)))
end

gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'script')
    local opp = gd.player(2).character or gd.player(2).kind or '?'
    for _, side in ipairs({ 1, -1 }) do
      grab_then('grab-release', side, function() end, 900)
      grab_then('pummel', side, function() hold1({ buttons = 'A' }, 2) local back = wait_until_motion(1, function(p) return p.motion_name == 'CatchWait' end, 40) log('pummel back in CatchWait after %s frames', tostring(back)) end, 900)
      grab_then('fthrow', side, function() gd.input(1, { x = side * 127 }, 2) end, 300)
      grab_then('bthrow', side, function() gd.input(1, { x = -side * 127 }, 2) end, 300)
      grab_then('uthrow', side, function() gd.input(1, { y = 127 }, 2) end, 300)
      grab_then('dthrow', side, function() gd.input(1, { y = -127 }, 2) end, 300)
      whiff('grab-whiff', side, function() hold1({ buttons = 'Z' }, 2) end, 70)
      whiff('dash-grab-whiff', side, function() gd.input(1, { x = side * 127 }, 18) gd.wait(18) hold1({ buttons = 'Z' }, 2) end, 140)
      whiff('pivot-grab-whiff', side, function() gd.input(1, { x = -side * 127 }, 12) gd.wait(12) gd.input(1, { x = side * 127, buttons = 'Z' }, 2) gd.wait(2) end, 140)
      -- Goku grabbed by the opponent, then thrown / escaping
      for _, th in ipairs({ { 'held-fthrow', { x = -side * 127 } }, { 'held-uthrow', { y = 127 } }, { 'held-dthrow', { y = -127 } }, { 'held-none', {} } }) do
        settle()
        gd.cpu_pad(2, {}, 1)
        gd.set_percent(1, 0)
        gd.teleport(1, 0, 0); gd.teleport(2, side * 7, 0)
        gd.wait(40)
        hold1({ x = side * 60 }, 3); gd.wait(20)
        gd.cpu_pad(2, { x = -side * 60 }, 3); gd.wait(20)
        gd.cpu_pad(2, { buttons = 'Z' }, 2)
        local held = wait_until_motion(1, function(p) return (p.motion_name or ''):find('Capture') ~= nil end, 60)
        if held then
          sample_held(side, th[1], 3)
          gd.wait(10)
          gd.cpu_pad(2, th[2], 2)
          local t0 = gd.match().frame
          local got = wait_until_motion(1, free, 700)
          verdict(th[1], side, got ~= nil, string.format('goku free after %d frames, goku=%s', gd.match().frame - t0, tostring(gd.player(1).motion_name)))
        else
          log('case=%s side=%d SKIP opponent %s could not grab (Goku=%s)', th[1], side, tostring(opp), tostring(gd.player(1).motion_name))
        end
        wait_until_motion(1, free, 300)
      end
    end
    log('RESULT %s opp=%s cases=%d fails=[%s]', #fails == 0 and 'PASS' or 'FAIL', tostring(opp), cases, table.concat(fails, ','))
  end)
  if not ok then log('RESULT FAIL error %s', tostring(why)) end
  gd.quit()
end)
