-- Verify the dedicated Ultimate Kirby arrival plays through and returns to control.
-- @name: Ultimate Kirby native Entry visual proof
-- @version: 1.0.0
-- @gameplay: true

gd.run(function()
  if not gd.wait_until(function() return gd.match().active end, 600) then
    gd.log("ultimate-entry RESULT FAIL no active match")
    return
  end
  gd.debug_draw(1, gd.draw.MODEL)
  gd.debug_stage(0)
  local marks, shots, seen_entry, seen_exit = {0, 35, 60, 90, 115}, {}, false, false
  for frame = 1, 185 do
    local p = gd.player(1)
    if p then
      if p.anim_id == 489 then
        seen_entry = true
        for _, mark in ipairs(marks) do
          if p.anim_frame and p.anim_frame >= mark and not shots[mark] then
            shots[mark] = true
            gd.screenshot("ultimate-kirby-native-entry-" .. mark)
          end
        end
      elseif seen_entry and (p.action == 14 or p.anim_id == 0) then
        seen_exit = true
      end
      if frame <= 10 or frame % 10 == 0 or p.anim_id == 489 and p.anim_frame and
          (p.anim_frame < 2 or p.anim_frame > 117) then
        gd.log(string.format("ultimate-entry t=%d action=%s anim_id=%s anim=%.2f x=%.2f y=%.2f visible=%s",
          frame, tostring(p.action), tostring(p.anim_id), p.anim_frame or -1,
          p.x or 0, p.y or 0, tostring(p.visible)))
      end
    end
    gd.wait(1)
  end
  local count = 0
  for _, mark in ipairs(marks) do if shots[mark] then count = count + 1 end end
  gd.log(string.format("ultimate-entry RESULT %s clips=%d/5 entered=%s exited=%s",
    seen_entry and seen_exit and count == 5 and "PASS" or "FAIL", count,
    tostring(seen_entry), tostring(seen_exit)))
end)
