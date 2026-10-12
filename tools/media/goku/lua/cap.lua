-- CAP: the capture helper prepended to every clip script (tools/media/goku/capture_run.py). gd.screenshot is queued for the
-- next presented frame and written by a worker thread; CAP.wait(n) does one screenshot per logic frame.
CAP = {on = false, n = 0, nclip = 0}
function CAP.log(s) gd.log('CAP ' .. s) end
function CAP.clip(label)            -- start a new clip; frame numbers restart
  CAP.nclip = CAP.nclip + 1; CAP.n = 0; CAP.clip_label = label
  CAP.log(string.format('CLIP %02d %s match_frame=%d', CAP.nclip, label, gd.match().frame))
end
-- Video pass: the logic is paused while recording and on_tick (which keeps running while paused) steps ONE logic frame per
-- CFG.pace presented frames. Each CAP.wait then resumes after exactly one step and shoots it, so no frame is skipped or doubled
-- whatever the machine load (realtime catch-up ticks and turbo both lose or corrupt frames), and the PNG writer gets time.
CAP.stepmode = CFG and CFG.step == '1'
CAP.lead = tonumber(CFG and CFG.lead) or 24
CAP.tail = tonumber(CFG and CFG.tail) or 36
CAP.pace = tonumber(CFG and CFG.pace) or 3
local tickn = 0
function on_tick()
  if CAP.stepping then
    tickn = tickn + 1
    if tickn % CAP.pace == 0 then gd.step(1) end
  end
end
function CAP.rec(on)
  CAP.on = on
  if CAP.stepmode then
    if on then gd.pause(); CAP.stepping = true else CAP.stepping = false; gd.resume() end
  end
  local lead = CAP.lead_o or CAP.lead
  if on and lead > 0 then CAP.wait(lead) end     -- a beat of idle before the move so the lower-third lands first
end
CAP.noshot = CFG and CFG.noshot == '1'      -- audio pass: same script, no screenshots, realtime
local lastmot = {}
local function trace()
  for port = 1, 2 do
    local p = gd.player(port)
    local m = p and tostring(p.motion_name)
    if m ~= lastmot[port] then
      lastmot[port] = m
      CAP.log(string.format('MOT c%02d f%d P%d %s x=%.1f y=%.1f pct=%.0f', CAP.nclip, CAP.n, port, m, p.x or 0, p.y or 0, p.percent or 0))
    end
  end
end
-- The game's own ki bar is a host overlay (not in gd.screenshot), so the per-frame ki value is logged for the compositor to redraw it.
local kibuf, kistart = {}, 1
local function kiflush()
  if #kibuf > 0 then CAP.log(string.format('KIS %02d %d %s', CAP.nclip, kistart, table.concat(kibuf, ','))) end
  kibuf = {}
end
local function kisample()
  local ok2, cb = pcall(gd.combo, 1)
  if #kibuf == 0 then kistart = CAP.n end
  kibuf[#kibuf + 1] = string.format('%d', math.floor(((ok2 and cb and cb.ki) or 0) + 0.5))
  if #kibuf >= 60 then kiflush() end
end
-- follow camera: keep P1 framed by moving the camera with him (CAP.follow{dx, dy, z, iy, fov}; CAP.follow(nil) turns it off)
function CAP.follow(o) CAP.fol = o end
local function follow_tick()
  local o = CAP.fol
  if not o then return end
  local p = gd.player(1)
  if not p then return end
  local cx = p.x + (o.dx or 0)
  CAP.fx = CAP.fx and (CAP.fx + (cx - CAP.fx) * 0.25) or cx          -- a little smoothing
  CAP.fy = CAP.fy and (CAP.fy + (p.y - CAP.fy) * 0.25) or p.y
  gd.camera_set{eye = {x = CAP.fx, y = CAP.fy + (o.dy or 4), z = o.z or 55}, interest = {x = CAP.fx - (o.dx or 0) * 0.6, y = CAP.fy + (o.iy or 2), z = 0}, fov = o.fov or 40}
end
function CAP.wait(k)
  for _ = 1, k do
    gd.wait(1)
    follow_tick()
    trace()
    if CAP.on and CAP.noshot then CAP.n = CAP.n + 1; kisample() end
    if CAP.on and not CAP.noshot then
      CAP.tick = (CAP.tick or 0) + 1
      if CAP.tick % (tonumber(CFG and CFG.every) or 1) == 0 then
        CAP.n = CAP.n + 1
        gd.screenshot(string.format('c%02d_f%05d', CAP.nclip, CAP.n))
        kisample()
      end
    end
  end
end
function CAP.endclip()
  CAP.wait(CAP.tail)                  -- a beat after the move
  kiflush()
  CAP.log(string.format('ENDCLIP %02d frames=%d match_frame=%d', CAP.nclip, CAP.n, gd.match().frame))
  CAP.on = false
end
-- park the fighters mid-stage and frame them
function CAP.setup(dist, camx, camy, camz, fov)
  assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
  gd.cpu_mode(2, 'stand')
  gd.teleport(1, 0, 0); gd.teleport(2, dist or 38, 0)
  gd.set_percent(1, 0); gd.set_percent(2, 0); gd.wait(30)
  gd.camera_set{eye = {x = camx or 20, y = camy or 14, z = camz or 95}, interest = {x = camx or 20, y = (camy or 14) - 4, z = 0}, fov = fov or 40}
end

-- Slow the game down while recording so the PNG writer thread keeps up (a 2x-render PNG takes ~100 ms; shots at 60/s overflow
-- its queue and crash the game). The sandbox has no os library and caps a script call at 500 ms / 2M instructions, so burn
-- time with K extra tasks per frame, each spinning CFG.spin loop iterations only while recording.
function CAP.burners()
  local K, S = tonumber(CFG and CFG.burn) or 0, tonumber(CFG and CFG.spin) or 900000
  for _ = 1, K do
    gd.run(function() while true do if CAP.on then for _ = 1, S do end end gd.wait(1) end end)
  end
end

-- start the next clip from a clean state: fighters placed, percent 0, ki set, camera framed
function CAP.reset(o)
  o = o or {}
  CAP.lead_o = o.lead
  gd.input(1, {}, 1); gd.wait(2)
  CAP.tp(1, o.x1 or 0, o.y1 or 0); CAP.tp(2, o.x2 or 38, o.y2 or 0)
  gd.set_percent(1, 0); gd.set_percent(2, o.pct or 0)
  if o.ki then gd.combo_ki(1, o.ki) end
  gd.wait(o.settle or 40)
  local cx = o.camx or 20
  gd.camera_set{eye = {x = cx, y = o.camy or 14, z = o.camz or 95}, interest = {x = cx, y = o.camiy or ((o.camy or 14) - 4), z = 0}, fov = o.fov or 40}
end
-- teleport that waits out a respawning or held fighter
function CAP.tp(port, x, y)
  for _ = 1, 120 do
    if pcall(gd.teleport, port, x, y) then return end
    gd.wait(15)
  end
  error('could not teleport port ' .. port)
end

-- Pad helpers. gd.input holds count logic frames; sticks -127..127 (x forward = +127 for a fighter facing right), triggers 0..255.
function CAP.tap(spec, n) gd.input(1, spec, n or 2) end
local function in_list(m, list) for _, v in ipairs(list) do if m == v then return true end end return false end
-- wait (recording) until P1 is in one of `states` at action frame >= af, then tap `spec` for n frames. Returns false on timeout.
function CAP.when(states, af, spec, n, timeout)
  if type(states) == 'string' then states = {states} end
  CAP.wseq = (CAP.wseq or 0) + 1
  local seq = CAP.wseq
  if CAP.sched == nil then               -- audio pass: the tap frames come from the video pass (CFG.when = "seq:match_frame,...")
    CAP.sched = {}
    for q, f in tostring(CFG and CFG.when or ''):gmatch('(%d+):(-?%d+)') do CAP.sched[tonumber(q)] = tonumber(f) end
  end
  local replay = CFG and CFG.when ~= nil
  for _ = 1, timeout or 90 do
    local p = gd.player(1)
    local hit
    if replay then hit = CAP.sched[seq] and CAP.sched[seq] >= 0 and gd.match().frame >= CAP.sched[seq]
    else hit = in_list(tostring(p.motion_name), states) and (p.action_frame or 0) >= af end
    if hit then
      CAP.log(string.format('WT %d %d', seq, gd.match().frame))
      gd.input(1, spec, n or 2); return true
    end
    CAP.wait(1)
  end
  CAP.log(string.format('WT %d -1', seq))
  CAP.log('WHEN timeout ' .. table.concat(states, ','))
  return false
end
-- stage edge: right ledge x and floor top, for off-stage KO framing
function CAP.edge()
  local sb = gd.stage_bounds()
  return sb.main_floor.right, sb.main_floor.top
end
