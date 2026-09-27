-- Same-camera motion/phase capture for the dedicated Ultimate Kirby LAB slot.
-- @name: Ultimate Kirby animation phase capture
-- @version: 1.0.0
-- @gameplay: true

local tag = "ultimate-kirby animation-phase"
local shots = 0

local function input(spec)
  gd.input(1, spec or {}, 2)
  gd.wait(1)
  return gd.player(1)
end

local function drive(spec, frames)
  local p
  for _ = 1, frames do p = input(spec) end
  return p
end

local function shot(name)
  shots = shots + 1
  local p = gd.player(1)
  local ok, path = gd.screenshot("ultimate-kirby-phase-" .. name)
  gd.log(string.format("%s shot=%s ok=%s action=%s action_frame=%s anim=%.2f x=%.3f y=%.3f path=%s",
    tag, name, tostring(ok), tostring(p and p.action), tostring(p and p.action_frame),
    p and p.anim_frame or -1, p and p.x or 0, p and p.y or 0, tostring(path)))
end

local function loop_pair(name, spec, duration, near_end)
  local before, after, last
  for _ = 1, duration do
    local p = input(spec)
    if p then
      if not before and p.anim_frame >= near_end then
        shot(name .. "-before")
        before = {frame = p.anim_frame, x = p.x, y = p.y, action = p.action}
      elseif before and not after and last and p.anim_frame + 3 < last.frame then
        shot(name .. "-after")
        after = {frame = p.anim_frame, x = p.x, y = p.y, action = p.action}
        break
      end
      last = {frame = p.anim_frame, action = p.action}
    end
  end
  gd.log(string.format("%s loop=%s before=%s after=%s dx=%.3f dy=%.3f",
    tag, name, before and before.frame or "none", after and after.frame or "none",
    before and after and after.x - before.x or 0,
    before and after and after.y - before.y or 0))
end

local function cutter(name, airborne)
  if airborne then
    input({buttons = "X"})
    drive({}, 8)
  end
  local previous
  input({buttons = "B", y = 127})
  for _ = 1, 125 do
    local p = input({})
    if p and p.action >= 385 and p.action <= 392 then
      if p.action ~= previous then
        shot(name .. "-state-" .. p.action)
        gd.log(string.format("%s route=%s state=%d action_frame=%s anim=%.2f x=%.3f y=%.3f",
          tag, name, p.action, tostring(p.action_frame), p.anim_frame, p.x, p.y))
        previous = p.action
      end
      if p.action_frame == 8 or p.action_frame == 20 then
        shot(name .. "-" .. p.action .. "-f" .. p.action_frame)
      end
    end
  end
end

gd.run(function()
  local ok, err = pcall(function()
    local ready = gd.wait_until(function()
      local p = gd.match().active and gd.player(1)
      return p and p.action == 14 and not p.airborne
    end, 1200)
    assert(ready, "LAB match did not enter idle")
    gd.debug_draw(1, gd.draw.MODEL)
    gd.debug_draw(2, gd.draw.MODEL)
    gd.debug_stage(0)
    drive({}, 200)
    shot("idle-start")
    loop_pair("idle", {}, 150, 107)
    drive({x = 45}, 15)
    loop_pair("walk", {x = 45}, 140, 42)
    drive({}, 15)
    drive({x = 127}, 20)
    loop_pair("run", {x = 127}, 130, 37)
    drive({}, 15)
    drive({buttons = "X"}, 2)
    drive({}, 26)
    local launch = gd.player(1)
    assert(launch and launch.airborne and launch.jumps_used == 1,
      "ground jump did not launch with one jump used")
    shot("groundjump")
    local previous_action
    for jump = 1, 5 do
      local before = gd.player(1)
      local used = before.jumps_used
      drive({buttons = "Y"}, 2)
      local rise = drive({}, 8)
      gd.log(string.format("%s airjump=%d before_used=%s used=%s action=%s motion=%s airborne=%s vy=%.3f",
        tag, jump, tostring(used), tostring(rise.jumps_used), tostring(rise.action),
        tostring(rise.motion_name), tostring(rise.airborne), rise.vy))
      assert(rise.airborne and rise.jumps_used == used + 1,
        "air jump " .. jump .. " did not consume exactly one jump")
      assert(rise.motion_name == "JumpAerialF" .. jump and rise.action ~= previous_action,
        "air jump " .. jump .. " did not enter its distinct action")
      shot("airjump-" .. jump)
      previous_action = rise.action
      if jump < 5 then drive({}, 23) end
    end
    assert(gd.player(1).jumps_used == 6, "six total jumps were not consumed")
    local grounded = gd.wait_until(function()
      local p = gd.player(1)
      return p and p.action == 14 and not p.airborne
    end, 240)
    if grounded then cutter("ground-cutter", false) end
    gd.wait_until(function()
      local p = gd.player(1)
      return p and p.action == 14 and not p.airborne
    end, 240)
    cutter("air-cutter", true)
    drive({}, 20) -- let the final screenshot encoder drain before quit
  end)
  gd.log(string.format("%s RESULT %s shots=%d%s", tag,
    ok and "PASS" or "FAIL", shots, ok and "" or (" error=" .. tostring(err))))
  gd.quit()
end)
