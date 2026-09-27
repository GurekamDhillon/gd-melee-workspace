-- Verify a deliberately large FigaTree Rot/TRAY offset survives early and late frames.
-- @name: Ultimate Kirby FigaTree duration sentinel
-- @version: 1.0.0
-- @gameplay: true

gd.run(function()
  local ok, err = pcall(function()
    assert(gd.wait_until(function()
      local p = gd.match().active and gd.player(1)
      return p and p.action == 14 and not p.airborne
    end, 1200), "spawn")
    gd.input(1, {buttons = "B"}, 2)
    assert(gd.wait_until(function()
      local p = gd.player(1)
      return p and p.action == 354
    end, 90), "inhale loop")
    local function sample(label)
      local p = gd.player(1)
      local joint = (gd.joints(1) or {})[3]
      assert(p and p.action == 354 and p.anim_id == 306 and joint and joint.valid,
             label .. " wrong action or joint")
      gd.log(string.format("ultimate-kirby sentinel %s frame=%.3f rot_y=%.3f player_y=%.3f",
        label, p.anim_frame or -1, joint.y or -999, p.y or -999))
      assert(joint.y > 15, label .. " converted +20 TRAY not applied")
    end
    gd.wait(1)
    sample("early")
    gd.wait(14)
    sample("late")
  end)
  gd.log("ultimate-kirby sentinel RESULT " .. (ok and "PASS" or "FAIL " .. tostring(err)))
  gd.quit()
end)
