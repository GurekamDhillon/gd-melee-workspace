-- Same-camera walk facing samples on the combined native visual pack.
-- @name: Ultimate Kirby walk facing audit
-- @version: 1.0.0
-- @gameplay: true

local tag = "ultimate-kirby facing"
local function sample(label)
  local p = gd.player(1)
  local j = gd.joints(1) or {}
  local body = j[7] or {}
  gd.log(string.format("%s %s action=%s motion=%s anim_id=%s anim=%.3f facing=%s x=%.3f body=(%.3f,%.3f,%.3f)",
    tag, label, tostring(p.action), tostring(p.motion_name), tostring(p.anim_id),
    p.anim_frame or -1, tostring(p.facing), p.x or 0,
    body.x or -999, body.y or -999, body.z or -999))
  local ok, path = gd.screenshot("ultimate-kirby-facing-" .. label)
  assert(ok, "screenshot " .. label)
  gd.log(string.format("%s shot=%s path=%s", tag, label, tostring(path)))
end

gd.run(function()
  local ok, err = pcall(function()
    assert(gd.wait_until(function()
      local p = gd.match().active and gd.player(1)
      return p and p.action == 14 and not p.airborne
    end, 1200), "spawn")
    gd.debug_draw(1, gd.draw.MODEL)
    gd.debug_draw(2, gd.draw.MODEL)
    gd.debug_stage(0)
    gd.wait(180)
    sample("idle")
    for frame = 1, 36 do
      gd.input(1, {x = 45}, 2)
      gd.wait(1)
      if frame == 6 or frame == 12 or frame == 18 or frame == 24 or frame == 30 or frame == 36 then
        sample("walk-" .. frame)
      end
    end
    gd.wait(5)
  end)
  gd.log(string.format("%s RESULT %s%s", tag, ok and "PASS" or "FAIL",
    ok and "" or " error=" .. tostring(err)))
  gd.quit()
end)
