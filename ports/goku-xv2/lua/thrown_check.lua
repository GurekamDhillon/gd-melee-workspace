-- Thrown-victim gate: Goku (a base:"none" define) grabs a retail fighter and throws it all four ways, both facings. The victim must play the
-- stand-in thrower's thrown rows (geno.json "thrown_as", Captain Falcon by default), not freeze: it enters a Thrown* state, its animation
-- frame advances, it stays near Goku, and it is released (no hang). Also logs the hold (CatchWait) and a pummel.
-- Scene (tools/run_lua_check.py): p1=geno:goku-xv2/hu;p2=<victim>/cpu0. Logs THROWN lines, ends with THROWN RESULT PASS|FAIL.
local SHOTS = false -- true for a --visible run: screenshots of the held and thrown frames (turbo frames are not presented)
local FREE = {}
for _, n in ipairs({ "Wait", "WalkSlow", "WalkMiddle", "WalkFast", "Turn", "Dash", "Run", "RunDirect", "Squat", "SquatWait", "SquatRv",
  "Fall", "FallF", "FallB", "FallAerial", "JumpF", "JumpB", "GuardOn", "Guard" }) do FREE[n] = true end
local function free(p)
  local n = p.motion_name or ""
  if p.in_hitlag or (p.hitlag or 0) > 0 then return false end
  return FREE[n] == true
end
local fails, cases = {}, 0
local victim_name = '?'
local function log(fmt, ...) gd.log('THROWN ' .. string.format(fmt, ...)) end
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
  hold1({ x = side * 60 }, 3)
  gd.wait(30)
  gd.teleport(1, 0, 0); gd.teleport(2, side * 7, 0)
  gd.wait(2)
  return wait_until_motion(1, free, 60) ~= nil
end
local function shot(tag)
  if not SHOTS then return end
  local ok, path = gd.screenshot('thrown-' .. victim_name .. '-' .. tag .. '.png')
  log('shot %s queued=%s path=%s', tag, tostring(ok), tostring(path))
end
local function is_thrown(n) return (n or ''):find('^Thrown') ~= nil end

local function grab(side)
  hold1({ buttons = 'Z' }, 2)
  return wait_until_motion(1, function(p) return p.motion_name == 'CatchWait' end, 45)
end

local function throw_case(name, side, spec)
  if not reset(side) then verdict(name, side, false, 'never actionable at start') return end
  if not grab(side) then verdict(name, side, false, 'grab did not connect') wait_until_motion(1, free, 120) return end
  gd.wait(6)
  local v0 = gd.player(2)
  local held_name = v0.motion_name
  shot(name .. '-held')
  gd.input(1, spec, 2)
  local thrown_frames, seen, frames_set, nframes = 0, {}, {}, 0
  local maxdx, maxdy, mindy, last_af = 0, -1e9, 1e9, nil
  local enter_f
  for i = 1, 160 do
    local g, v = gd.player(1), gd.player(2)
    local mn = v.motion_name or '?'
    if is_thrown(mn) then
      thrown_frames = thrown_frames + 1
      seen[mn] = true
      local af = v.anim_frame or -1
      local key = string.format('%.2f', af)
      if not frames_set[key] then frames_set[key] = true; nframes = nframes + 1 end
      local dx, dy = (v.x - g.x) * side, v.y - g.y
      if math.abs(dx) > maxdx then maxdx = math.abs(dx) end
      if dy > maxdy then maxdy = dy end
      if dy < mindy then mindy = dy end
      if thrown_frames == 1 or thrown_frames % 4 == 1 then
        log('thrown name=%s side=%d t=%d goku=%s gaf=%.2f victim=%s vaf=%.2f dx=%.2f dy=%.2f', name, side, i, g.motion_name, g.anim_frame or -1, mn, af, dx, dy)
      end
      if thrown_frames == 3 then shot(name .. '-t3') end
      if thrown_frames == 9 then shot(name .. '-t9') end
    end
    if thrown_frames > 0 and not is_thrown(mn) and not (mn or ''):find('Capture') then break end
    gd.wait(1)
  end
  local names = {}
  for k in pairs(seen) do names[#names + 1] = k end
  table.sort(names)
  local ok = thrown_frames >= 3 and nframes >= 3 and maxdx < 40 and maxdy < 40 and mindy > -20
  verdict(name, side, ok, string.format('held=%s thrown=%s frames=%d distinct_af=%d maxdx=%.1f dy=[%.1f,%.1f]', tostring(held_name),
    table.concat(names, '+'), thrown_frames, nframes, maxdx, mindy, maxdy))
  local got = wait_until_motion(1, free, 400)
  if not got then verdict(name .. '-goku-free', side, false, 'goku=' .. tostring(gd.player(1).motion_name)) end
end

local function pummel_case(side)
  local name = 'pummel'
  if not reset(side) then verdict(name, side, false, 'never actionable at start') return end
  if not grab(side) then verdict(name, side, false, 'grab did not connect') wait_until_motion(1, free, 120) return end
  gd.wait(6)
  hold1({ buttons = 'A' }, 2)
  local names, afs, n = {}, {}, 0
  for i = 1, 50 do
    local v = gd.player(2)
    local mn = v.motion_name or '?'
    if not names[mn] then names[mn] = true; n = n + 1 end
    afs[string.format('%.1f', v.anim_frame or -1)] = true
    if i == 6 then shot('pummel') end
    gd.wait(1)
  end
  local list = {}
  for k in pairs(names) do list[#list + 1] = k end
  table.sort(list)
  local back = gd.player(1).motion_name
  verdict(name, side, back == 'CatchWait' or back == 'CatchAttack' or (back or ''):find('Catch') ~= nil, 'victim motions ' .. table.concat(list, '+') .. ' goku=' .. tostring(back))
  -- release by a forward throw so the case ends cleanly
  gd.input(1, { x = side * 127 }, 2)
  wait_until_motion(1, free, 400)
end

gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'script')
    victim_name = tostring(gd.player(2).character or gd.player(2).kind or '?'):gsub('[^%w]', '')
    for _, side in ipairs({ 1, -1 }) do
      throw_case('fthrow', side, { x = side * 127 })
      throw_case('bthrow', side, { x = -side * 127 })
      throw_case('uthrow', side, { y = 127 })
      throw_case('dthrow', side, { y = -127 })
      pummel_case(side)
    end
    log('RESULT %s victim=%s cases=%d fails=[%s]', #fails == 0 and 'PASS' or 'FAIL', victim_name, cases, table.concat(fails, ','))
  end)
  if not ok then log('RESULT FAIL error %s', tostring(why)) end
  gd.quit()
end)
