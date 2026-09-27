-- Movement smoke probe for a human P1 Kirby host (retail Kirby or an m-ex clone).
-- Run with MELEE_PAD_SCRIPT pointing at this file, MELEE_INPUT=none, and
-- MELEE_SCENE="mode=training;p1=kirby;stage=fd" (or the clone's scene token).
-- Results are lines tagged "ultimate-kirby movement" in melee-pc.log.
-- @name: Ultimate Kirby movement probe
-- @version: 1.0.0
-- @gameplay: true

local tag = "ultimate-kirby movement"
local failures, checks = 0, 0

local function record()
  local p = assert(gd.player(1), "P1 fighter disappeared")
  return {
    frame = gd.match().frame,
    action = p.action,
    motion = p.motion_name or (gd.motion_name and gd.motion_name(p.action, 1)) or "?",
    x = p.x, y = p.y, vx = p.vx, vy = p.vy, ground_vel = p.ground_vel,
    air = p.airborne, used = p.jumps_used, max = p.jumps_max,
  }
end

local function describe(s)
  return string.format("f=%d action=%s/%s x=%.3f y=%.3f vx=%.3f vy=%.3f ground_vel=%.3f air=%s jumps=%s/%s",
    s.frame, tostring(s.action), s.motion, s.x, s.y, s.vx, s.vy, s.ground_vel,
    tostring(s.air), tostring(s.used), tostring(s.max))
end

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

-- gd.input written by a task is read by the game on the following logic frame.
-- Refresh it every frame and sample after that frame, so the trace is tied to
-- actual game state rather than the number of requested button presses.
local function drive(label, spec, frames)
  local first, last = record(), nil
  local seen, names = {}, {}
  local active_hits = {}
  local min_x, max_x = first.x, first.x
  local min_y, max_y = first.y, first.y
  local min_vx, max_vx = first.vx, first.vx
  local min_vy, max_vy = first.vy, first.vy
  local min_gv, max_gv = first.ground_vel, first.ground_vel
  for _ = 1, frames do
    gd.input(1, spec, 2)
    gd.wait(1)
    last = record()
    local hitboxes = gd.hitboxes(1) or {}
    if #hitboxes > 0 then
      active_hits[#active_hits + 1] = { frame = last.frame, action = last.action,
        motion = last.motion, hitboxes = hitboxes }
    end
    if not seen[last.motion] then
      seen[last.motion] = true
      names[#names + 1] = last.motion
    end
    min_x, max_x = math.min(min_x, last.x), math.max(max_x, last.x)
    min_y, max_y = math.min(min_y, last.y), math.max(max_y, last.y)
    min_vx, max_vx = math.min(min_vx, last.vx), math.max(max_vx, last.vx)
    min_vy, max_vy = math.min(min_vy, last.vy), math.max(max_vy, last.vy)
    min_gv, max_gv = math.min(min_gv, last.ground_vel), math.max(max_gv, last.ground_vel)
  end
  gd.log(string.format("%s TRACE %s start=[%s] end=[%s] motions=%s x=[%.3f,%.3f] y=[%.3f,%.3f] vx=[%.3f,%.3f] vy=[%.3f,%.3f] ground_vel=[%.3f,%.3f]",
    tag, label, describe(first), describe(last), table.concat(names, ","),
    min_x, max_x, min_y, max_y, min_vx, max_vx, min_vy, max_vy, min_gv, max_gv))
  return { first = first, last = last, seen = seen, active_hits = active_hits, min_x = min_x,
    max_x = max_x, min_y = min_y, max_y = max_y,
    min_vx = min_vx, max_vx = max_vx, min_vy = min_vy, max_vy = max_vy,
    min_gv = min_gv, max_gv = max_gv }
end

local function check_live_hammer(label, trace, action, damage, angle, min_windows)
  local frames = {}
  local matches = {}
  for _, sample in ipairs(trace.active_hits) do
    local hits = sample.hitboxes
    frames[#frames + 1] = sample.frame
    if sample.action == action and #hits == 2 then
      local both_match = true
      for _, hit in ipairs(hits) do
        if hit.damage ~= damage or hit.angle ~= angle or hit.kbg ~= 78
          or hit.bkb ~= 60 or hit.element_name ~= "fire" then
          both_match = false
        end
      end
      if both_match then matches[#matches + 1] = sample.frame end
    end
  end
  local windows, previous = 0, nil
  for _, frame in ipairs(matches) do
    if previous == nil or frame > previous + 1 then windows = windows + 1 end
    previous = frame
  end
  check(label, windows >= min_windows,
    string.format("action %d expected two %d%%/%d-degree fire hits in %d window(s); matched %d, active frames: %s",
      action, damage, angle, min_windows, windows, table.concat(frames, ",")))
end

local function saw_prefix(trace, prefix)
  for name in pairs(trace.seen) do
    if name:sub(1, #prefix) == prefix then return true end
  end
  return false
end

local function check_hammer_script(action, row, damage, angle, frames)
  -- gd.timeline takes a fighter action state, not a PlKb.dat animation row.
  -- Kirby action states 383/384 play animation rows 322/323 respectively.
  local timeline = gd.timeline(1, action)
  local hits = {}
  if timeline then
    for _, event in ipairs(timeline.events) do
      if event.op == 11 then hits[#hits + 1] = event end
    end
  end
  local ok = timeline ~= nil and timeline.anim_id == row and #hits == #frames
  if ok then
    for i, hit in ipairs(hits) do
      if hit.frame ~= frames[i] or hit.damage ~= damage or hit.angle ~= angle
        or hit.kbg ~= 78 or hit.bkb ~= 60 or hit.element_name ~= "fire" then
        ok = false
        break
      end
    end
  end
  check("side B IR payload row " .. row, ok,
    string.format("action %d anim %s expected %d fire hitboxes, %d%%/%d degrees, active frames %s; saw %d hitboxes",
      action, timeline and tostring(timeline.anim_id) or "nil",
      #frames, damage, angle, table.concat(frames, ","), #hits))
end

local function main()
  if not gd.wait_until(function()
    local p = gd.match().active and gd.player(1)
    return p and p.action == 14 and not p.airborne -- Wait
  end, 1200) then
    check("match ready", false, "no standing P1 within 1200 logic frames")
    return
  end
  local p = gd.player(1)
  check("P1 is human", not p.cpu, "gd.input does not drive CPU fighters")
  if p.cpu then return end
  check("LAB mode", gd.lab_mode and gd.lab_mode(), "scene and LAB script active")
  -- gd.timeline reports 1-based active frames; Ultimate IR event counters are
  -- 0-based, so source counters 11/25 appear here as active frames 12/26.
  check_hammer_script(383, 322, 19, 48, {12, 12})
  check_hammer_script(384, 323, 16, 50, {12, 12, 26, 26})
  drive("settle", {}, 20)

  local walk = drive("walk right", { x = 45 }, 25)
  check("walk", saw_prefix(walk, "Walk") and walk.last.x > walk.first.x + 0.5
    and walk.max_gv > 0.05, "Walk state, rightward position and ground velocity")

  drive("walk release", {}, 12)
  local run = drive("dash and run right", { x = 127 }, 32)
  check("run", (run.seen.Run or run.seen.RunDirect) and run.last.x > run.first.x + 5
    and run.max_gv > 0.1, "Run state, rightward position and ground velocity")

  drive("run release", {}, 28)
  local crouch = drive("crouch", { y = -127 }, 20)
  check("crouch", saw_prefix(crouch, "Squat") and not crouch.last.air,
    "Squat state while grounded")
  drive("crouch release", {}, 15)

  local launch = drive("ground jump press", { buttons = "X" }, 2)
  local rise = drive("ground jump rise", {}, 26)
  local ground_motion = launch.seen.KneeBend or launch.seen.JumpF
    or rise.seen.KneeBend or rise.seen.JumpF or rise.seen.JumpB
  check("ground jump", ground_motion and rise.last.air
    and rise.max_y > launch.first.y + 1 and rise.max_vy > 0.1,
    "jump state, airborne flag, height and upward velocity")

  for n = 1, 5 do
    local press = drive("air jump " .. n .. " press", { buttons = "Y" }, 2)
    local rise_air = drive("air jump " .. n .. " rise", {}, 8)
    local expected = "JumpAerialF" .. n
    local motion_ok = press.seen[expected] or rise_air.seen[expected]
    local count_ok = press.first.used == nil or
      (rise_air.last.used ~= nil and rise_air.last.used == press.first.used + 1)
    check("air jump " .. n, motion_ok and count_ok and rise_air.last.air
      and rise_air.max_vy > 0.1 and rise_air.max_y > press.first.y + 0.1,
      expected .. ", jump count increment, airborne and upward motion")
    if n < 5 then drive("air jump " .. n .. " gate", {}, 23) end
  end
  local final = record()
  check("six total jumps", final.used == nil or final.used == 6,
    "one ground jump plus five air jumps")

  -- Let the hop chain land before probing the ground side special. This checks
  -- the input-to-action route only; damage and hitboxes belong to the port.
  local landed = drive("land before side B", {}, 180)
  local side_press = drive("side B press", { buttons = "B", x = 127 }, 2)
  local side_follow = drive("side B follow", {}, 24)
  local side_motion = side_press.seen.SpecialS or side_press.seen.SpecialAirS
    or side_follow.seen.SpecialS or side_follow.seen.SpecialAirS
    or saw_prefix(side_press, "SideB") or saw_prefix(side_follow, "SideB")
  check("side B action", not landed.last.air and side_motion
    and (side_press.last.action ~= side_press.first.action
      or side_follow.last.action ~= side_press.first.action),
    "grounded B + side stick enters a side-special action")
  check_live_hammer("ground side B live hitboxes", side_follow, 383, 19, 48, 1)

  local ready = gd.wait_until(function()
    local fighter = gd.player(1)
    return fighter and fighter.action == 14 and not fighter.airborne
  end, 180)
  check("ground side B recovery", ready, "Kirby returns to Wait onstage")
  if not ready then return end
  drive("air side B launch", { buttons = "X" }, 2)
  local air_setup = drive("air side B setup", {}, 8)
  local air_press = drive("air side B press", { buttons = "B", x = 127 }, 2)
  local air_follow = drive("air side B follow", {}, 34)
  check("air side B action", air_setup.last.air and
    (air_press.seen.SpecialAirS or air_follow.seen.SpecialAirS),
    "airborne B + side stick enters SpecialAirS")
  check_live_hammer("air side B live hitboxes", air_follow, 384, 16, 50, 2)
end

gd.run(function()
  local ok, err = pcall(main)
  if not ok then check("probe error", false, tostring(err)) end
  gd.input(1, {}, 2)
  gd.log(string.format("%s RESULT %s (%d/%d checks passed)",
    tag, failures == 0 and "PASS" or "FAIL", checks - failures, checks))
  gd.quit()
end)
