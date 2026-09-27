-- Record the native Kirby spawn action and actual playback of row 238.
-- @name: Ultimate Kirby entry visual audit
-- @version: 1.0.0
-- @gameplay: true

local tag = "ultimate-kirby entry audit"

gd.run(function()
  local seen, shots = {}, {}
  local active = gd.wait_until(function() return gd.match().active end, 600)
  if not active then
    gd.log(tag .. " RESULT FAIL no active match")
    return
  end
  gd.debug_draw(1, gd.draw.MODEL)
  gd.debug_stage(0)
  for frame = 1, 180 do
    local p = gd.player(1)
    if p then
      seen[p.action] = true
      if frame <= 50 or frame % 10 == 0 or p.action == 14 then
        gd.log(string.format("%s t=%d action=%s anim_id=%s anim=%.2f y=%.2f visible=%s",
          tag, frame, tostring(p.action), tostring(p.anim_id),
          p.anim_frame or -1, p.y or 0, tostring(p.visible)))
      end
      for _, mark in ipairs({0, 5, 10, 20, 40, 60, 80, 100, 115}) do
        if p.anim_id == 238 and p.anim_frame and p.anim_frame >= mark and not shots[mark] then
          shots[mark] = true
          gd.screenshot("ultimate-kirby-entry-" .. mark)
        end
      end
    end
    gd.wait(1)
  end
  gd.log(string.format("%s RESULT %s entry_action=%s row238_frames=%s",
    tag, seen[323] and "PASS" or "INCOMPLETE", tostring(seen[323]),
    table.concat((function()
      local result = {}
      for _, mark in ipairs({0, 5, 10, 20, 40, 60, 80, 100, 115}) do
        if shots[mark] then result[#result + 1] = tostring(mark) end
      end
      return result
    end)(), ",")))
end)
