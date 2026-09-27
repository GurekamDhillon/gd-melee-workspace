-- Compare decoded FigaTree joint origins with the game's computed matrices.
-- @name: Ultimate Kirby joint telemetry
-- @version: 1.0.0
-- @gameplay: true

local tag = "ultimate-kirby joint-telemetry"

local function step(spec)
  gd.input(1, spec or {}, 2)
  gd.wait(1)
  return gd.player(1)
end

local function drive(spec, frames)
  local p
  for _ = 1, frames do p = step(spec) end
  return p
end

local function dump(label)
  local p = gd.player(1)
  local joints = gd.joints(1) or {}
  gd.log(string.format("%s state=%s action=%s motion=%s anim_id=%s symbol=%s anim=%.3f x=%.3f y=%.3f joints=%d",
    tag, label, tostring(p.action), tostring(p.motion_name), tostring(p.anim_id),
    tostring(p.anim_symbol), p.anim_frame or -1, p.x or 0, p.y or 0, #joints))
  if label == "inhale" then
    local timeline = gd.timeline(1, p.action)
    gd.log(string.format("%s timeline action=%s anim_id=%s anim_name=%s",
      tag, p.action, tostring(timeline and timeline.anim_id),
      tostring(timeline and timeline.anim_name)))
  end
  -- gd.joints indexes ftParts (59 entries with placeholders), not the 46-node
  -- FigaTree DFS. FootL/FootR DFS 36/42 correspond to ftParts 49/55.
  for _, index in ipairs({1, 2, 4, 6, 25, 30, 49, 55}) do
    local joint = joints[index + 1]
    gd.log(string.format("%s joint=%d valid=%s pos=(%.3f,%.3f,%.3f) parent=%s",
      tag, index, tostring(joint and joint.valid), joint and joint.x or -999,
      joint and joint.y or -999, joint and joint.z or -999,
      tostring(joint and joint.parent)))
  end
end

gd.run(function()
  local ok, err = pcall(function()
    assert(gd.wait_until(function()
      local p = gd.match().active and gd.player(1)
      return p and p.action == 14 and not p.airborne
    end, 1200), "spawn")
    drive({}, 190)
    dump("idle")
    drive({buttons = "L"}, 18)
    dump("guard")
    drive({buttons = "L", x = 127}, 18)
    dump("roll")
    drive({}, 65)
    assert(gd.wait_until(function()
      local p = gd.player(1)
      return p and p.action == 14 and not p.airborne
    end, 120), "post-roll idle")
    drive({buttons = "B"}, 35)
    dump("inhale")
    drive({}, 95)
    assert(gd.wait_until(function()
      local p = gd.player(1)
      return p and p.action == 14 and not p.airborne
    end, 120), "post-Inhale idle")
    drive({buttons = "B", y = -127}, 2)
    drive({}, 36)
    dump("stone")
  end)
  gd.log(string.format("%s RESULT %s%s", tag, ok and "PASS" or "FAIL",
    ok and "" or (" error=" .. tostring(err))))
  gd.quit()
end)
