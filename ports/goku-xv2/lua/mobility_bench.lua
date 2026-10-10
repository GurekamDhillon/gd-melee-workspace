-- Mobility bench: per-frame position/velocity of port 1 on FD, so Goku can be compared with any stock fighter.
-- Scene: mode=lab;p1=<geno:goku-xv2/hu | fox/hu | captain/hu | marth/hu>;p2=mario/cpu0;stage=fd;items=off;time=0
-- Run: MELEE_TURBO=1 MELEE_PAD_SCRIPT=<this file> tools/port/run.sh batch NAME --iso ISO
-- Logs MOB summary lines; per-frame rows (test,f,x,y,vx,vy,dx,dy,motion,air) go to the script data file mobtrace.csv.
-- dx is the measured position change since the previous frame; vx is the engine's reported velocity.
-- A dx that disagrees with vx means something other than velocity is moving the fighter (animation translation, lua, ...).
-- The script log is capped (about 400 lines per run), so per-frame rows go to ONE data file instead of the log.
local TRACE_ROWS = {}
local NL = string.char(10)
local function out(fmt, ...) gd.log('MOB ' .. string.format(fmt, ...)) end

local prev
local SEEN = {}
local function snap(test, f)
  local p = gd.player(1)
  local dx = prev and (p.x - prev.x) or 0
  local s = { x = p.x, y = p.y, vx = p.vx or 0, vy = p.vy or 0, dx = dx, dy = prev and (p.y - prev.y) or 0,
    m = p.motion_name or '?', air = p.airborne, face = p.facing or 1, af = p.anim_frame }
  prev = s
  if not SEEN[s.m] and test then
    SEEN[s.m] = true
    local okt, tl = pcall(gd.timeline, 1)
    if okt and type(tl) == 'table' then
      gd.log(string.format('MOB motion_len %s end_frame=%s length=%s anim=%s', s.m, tostring(tl.end_frame), tostring(tl.length), tostring(tl.animation_name or tl.anim_name or tl.animation)))
    end
  end
  if test then
    TRACE_ROWS[#TRACE_ROWS + 1] = string.format('%s,%d,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%s,%s,%s', test, f, s.x, s.y, s.vx, s.vy, s.dx, s.dy, s.m, tostring(s.air), tostring(s.af))
  end
  return s
end

local function hold(test, spec, frames, cb)
  local f0 = 0
  for i = 1, frames do
    gd.input(1, spec, 1); gd.wait(1)
    local s = snap(test, i)
    if cb then cb(s, i) end
  end
end

local function settle(x0)
  gd.input(1, {}, 1)
  gd.teleport(1, x0 or 0, 0)
  for _ = 1, 120 do
    gd.wait(1)
    local p = gd.player(1)
    if not p.airborne and p.motion_name == 'Wait' and math.abs(p.vx or 0) < 0.01 then break end
  end
  gd.wait(8)
  prev = nil
  snap(nil, 0)
end

local function face_right()
  -- a tap right on the ground turns a left-facing fighter; the scene starts facing right so this is a safeguard
  if (gd.player(1).facing or 1) < 0 then
    gd.input(1, { x = 127 }, 3); gd.wait(40)
  end
end

gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand'); gd.teleport(2, -70, 0)
    local a = gd.attrs(1) or {}
    local ks = { 'walk_max', 'dash_initial', 'dash_max', 'run_animation_scaling', 'jump_squat', 'hop_v', 'jump_v', 'gravity',
      'terminal_velocity', 'fast_fall', 'air_drift', 'air_friction', 'weight' }
    local parts = {}
    for _, k in ipairs(ks) do if a[k] ~= nil then parts[#parts + 1] = k .. '=' .. tostring(a[k]) end end
    out('fighter=%s attrs %s', tostring(gd.player(1).char_name), table.concat(parts, ' '))
    do
      local all = {}
      for k, v in pairs(a) do all[#all + 1] = k .. '=' .. tostring(v) end
      table.sort(all)
      for i = 1, #all, 12 do out('allattrs %s', table.concat(all, ' ', i, math.min(i + 11, #all))) end
    end
    local ca = gd.cpu_attrs and gd.cpu_attrs(1) or {}
    local cp = {}
    for k, v in pairs(ca) do cp[#cp + 1] = k .. '=' .. tostring(v) end
    table.sort(cp)
    out('cpu_attrs %s', table.concat(cp, ' '))
    gd.wait(30)
    settle(-80); face_right(); settle(-80)

    -- 1. dash + run: hold full right from rest, 70 frames
    do
      local first_run, maxv, dash_first, dash_peak = nil, 0, nil, 0
      local run_af, run_af_max = {}, 0
      local x0 = gd.player(1).x
      local d5, d30
      hold('dashrun', { x = 127 }, 45, function(s, i)
        if s.m == 'Dash' and not dash_first then dash_first = i end
        if s.m == 'Dash' and math.abs(s.vx) > dash_peak then dash_peak = math.abs(s.vx) end
        if s.m == 'Run' and not first_run then first_run = i end
        if math.abs(s.vx) > maxv then maxv = math.abs(s.vx) end
        if s.m == 'Run' and s.af then run_af[#run_af + 1] = s.af; if s.af > run_af_max then run_af_max = s.af end end
        if i == 5 then d5 = s.x - x0 end
        if i == 30 then d30 = s.x - x0 end
      end)
      local p = gd.player(1)
      out('dash_first_frame=%s dash_peak_vx=%.3f run_first_frame=%s run_max_vx=%.3f dist5=%.2f dist30=%.2f dist45=%.2f run_steady_dx=%.3f',
        tostring(dash_first), dash_peak, tostring(first_run), maxv, d5 or -1, d30 or -1, p.x - x0, prev.dx)
      local n = #run_af
      if n > 6 then
        local rate = 0
        for k = n - 4, n do local d = run_af[k] - run_af[k - 1]; if d > 0 then rate = d end end
        out('run_cadence anim_frames_per_frame=%.3f cycle_max_anim_frame=%.1f stride_units_per_cycle=%.2f', rate, run_af_max, rate > 0 and (run_af_max / rate) * math.abs(prev.dx) or -1)
      end
      do
        local top, jn = -1e9, 0
        for _, j in ipairs(gd.joints(1) or {}) do if j.valid and j.y and j.y > top then top = j.y end end
        out('height_joint_top_above_root=%.2f', top - gd.player(1).y)
      end
      -- 2. run turn: flip the stick
      local mn, motions, last = 99, {}, nil
      hold('runturn', { x = -127 }, 25, function(s, i)
        if s.m ~= last then motions[#motions + 1] = s.m .. '@' .. i; last = s.m end
        if i == 1 then mn = s.vx end
      end)
      out('runturn motions %s', table.concat(motions, ','))
      settle(-20)
    end

    -- 3. walk (full tilt) 40 frames
    do
      local x0 = gd.player(1).x
      local maxv = 0
      hold('walk', { x = 60 }, 40, function(s) if math.abs(s.vx) > maxv then maxv = math.abs(s.vx) end end)
      out('walk(x=60) max_vx=%.3f dist40=%.2f', maxv, gd.player(1).x - x0)
      settle(-20)
    end

    -- 4/5. jumps: standing (no stick), standing with stick held, short hop, full hop, run jump, then double jump
    local function jump(name, held_frames, stick_x, pre_run)
      settle(pre_run and -80 or -30)
      if pre_run then hold(name .. '_pre', { x = 127 }, pre_run, nil); prev = nil end
      local x_takeoff, y0 = nil, gd.player(1).y
      local peak, air_f, left, land_f = 0, 0, false, nil
      local x_start = gd.player(1).x
      local squat = nil
      local dj_gain
      for i = 1, 140 do
        local spec = { x = stick_x or 0 }
        if i <= held_frames then spec.buttons = 'X' end
        gd.input(1, spec, 1); gd.wait(1)
        local s = snap(name, i)
        if s.air and not left then left = true; air_f = 0; squat = i - 1; x_takeoff = s.x; peak = 0 end
        if left then
          if s.air then air_f = air_f + 1 end
          if s.y - y0 > peak then peak = s.y - y0 end
          if not s.air then land_f = i; break end
        end
      end
      gd.input(1, {}, 1)
      local p = gd.player(1)
      out('%s squat_frames=%s peak_height=%.3f airtime=%d horiz_dist=%.2f land_x_from_start=%.2f', name, tostring(squat), peak, air_f,
        (x_takeoff and (p.x - x_takeoff)) or -1, p.x - x_start)
      return p
    end
    jump('jump_full_still', 8, 0)
    jump('jump_short_still', 2, 0)
    jump('jump_full_stick', 8, 127)
    jump('jump_short_stick', 2, 127)
    jump('jump_full_run', 8, 127, 22)

    -- double jump: full hop, then at frame 25 of the flight press X again (stick neutral)
    do
      settle(-30)
      local y0 = gd.player(1).y
      local peak, dj_peak, dj_started, dj_vy, dj_f = 0, 0, false, nil, nil
      local air_f, left = 0, false
      for i = 1, 200 do
        local spec = {}
        if i <= 8 then spec.buttons = 'X' end
        if left and air_f == 25 then spec.buttons = 'X' end
        gd.input(1, spec, 1); gd.wait(1)
        local s = snap('doublejump', i)
        if s.air then left = true; air_f = air_f + 1 end
        if left and air_f == 26 then dj_started = true; dj_vy = s.vy end
        if s.y - y0 > peak then peak = s.y - y0 end
        if left and not s.air then break end
      end
      out('doublejump (at air frame 25) first_vy=%.3f peak_height_total=%.3f total_air=%d', dj_vy or -1, peak, air_f)
      gd.input(1, {}, 1)
    end

    -- 6. fall speed, fast fall, air drift: drop from y=90 with no stick, then with stick, then fast fall
    local function drop(name, stick_x, ff)
      settle(-40)
      gd.teleport(1, -40, 90); prev = nil
      local maxfall, maxvx, ffmax = 0, 0, 0
      for i = 1, 120 do
        local spec = { x = stick_x or 0 }
        if ff and i > 40 then spec.y = (i % 2 == 0) and -127 or 0 end
        if ff and i > 40 then spec.y = -127 end
        gd.input(1, spec, 1); gd.wait(1)
        local s = snap(name, i)
        if not s.air then break end
        if -s.vy > maxfall then maxfall = -s.vy end
        if math.abs(s.vx) > maxvx then maxvx = math.abs(s.vx) end
      end
      out('%s max_fall_speed=%.3f max_air_vx=%.3f', name, maxfall, maxvx)
      gd.input(1, {}, 1)
    end
    drop('fall_neutral', 0, false)
    drop('fall_drift_full', 127, false)
    -- fast fall: flick down only after the fighter is already falling (first 40 frames hold neutral)
    drop('fall_fastfall', 0, true)
  end)
  if not ok then gd.log('MOB FAIL ' .. tostring(why)) end
  local okw, werr = pcall(gd.data_write, 'mobtrace.csv', 'test,f,x,y,vx,vy,dx,dy,motion,air,anim_frame' .. NL .. table.concat(TRACE_ROWS, NL) .. NL)
  gd.log('MOB trace rows=' .. #TRACE_ROWS .. ' write=' .. tostring(okw) .. ' ' .. tostring(werr))
  gd.log('MOB DONE')
  gd.quit()
end)
