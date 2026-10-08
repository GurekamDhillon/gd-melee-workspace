-- Coordinator-only game proof. This needs a running LAB scene and was not executed by the author-guide task.
-- run_scene.sh launches a game window even when it calls itself "headless".
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), "no match")
    gd.cpu_mode(2, "stand")
    gd.teleport(1, 0, 0)
    gd.teleport(2, -55, 0) -- safely on FD, outside the palm's reach
    gd.wait(30)
    assert(gd.fighter_lua(1), "P1 needs Pip's fighter Lua")
    gd.savestate(1)
    gd.wait(2)
    for _, air in ipairs({false, true}) do
      for _, held in ipairs({false, true}) do
        gd.input(1, {}, 1)
        gd.loadstate(1)
        gd.wait(3)
        if air then gd.teleport(1, 0, 30); gd.wait(2) end
        local p1_start, p2_start = gd.player(1), gd.player(2)
        gd.input(1, {buttons = "B"}, held and 30 or 2)
        local pulses, active, seen = {}, false, false
        for tick = 1, 85 do
          gd.wait(1)
          local p = gd.player(1)
          local victim = gd.player(2)
          assert(not p.in_hitlag and not victim.in_hitlag, "contact/hitlag invalidates isolated timing")
          assert(p.percent == p1_start.percent and victim.percent == p2_start.percent, "unexpected damage")
          assert(p.stocks == p1_start.stocks and victim.stocks == p2_start.stocks, "unexpected KO/respawn")
          assert(math.abs(p.x - victim.x) > 30, "P2 entered the isolated test space")
          local boxes = gd.hitboxes(1) or {}
          if p.motion_name == "PalmSkip" then
            seen = true
            if #boxes > 0 and not active then
              pulses[#pulses + 1] = boxes[1].damage
              gd.log(string.format("PIPCHECK pulse air=%s held=%s n=%d damage=%.3f readout=%s clip=%s bone=%s",
                tostring(air), tostring(held), #pulses, boxes[1].damage,
                tostring(p.action_frame), tostring(p.anim_frame_f), tostring(boxes[1].bone)))
            end
            active = #boxes > 0
          else active = false end
        end
        assert(seen and #pulses == 2, "PalmSkip must enter and produce two separated pulses")
        assert(math.abs(pulses[1] - 5) < 0.01, "first pulse must be 5")
        assert(math.abs(pulses[2] - (held and 11 or 8)) < 0.01, "second pulse must start with final damage")
        local state = assert(gd.fighter_lua(1), "missing Lua state")
        assert(state.faults == 0, "fighter Lua faulted")
        assert(state.state.boosted == held, "held input was not latched")
        local recovered = gd.player(1)
        assert(recovered.motion_name == "Wait", "special did not recover and settle into Wait")
        assert(not recovered.in_hitstun and not recovered.in_hitlag, "recovery is not actionable")
        assert(#(gd.hitboxes(1) or {}) == 0, "hitbox survived recovery")
      end
    end
    gd.input(1, {}, 1)
    gd.log("PIPCHECK PASS 4 casts: tap/hold, ground/air, two pulses, damage, recovery, zero Lua faults")
  end)
  if not ok then gd.log("PIPCHECK FAIL " .. tostring(why)) end
  gd.quit()
end)
