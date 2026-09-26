-- Joint probe: port 1's animation symbol, animation frame and every joint's world position,
-- one "JP" line every EVERY game frames, at most LIMIT lines. Only reads (gd.player, gd.joints).
-- ports/ir/tools/compare_joints.py rebuilds the same pose from the source and compares.
local EVERY, LIMIT = 3, 4000
local n, tick = 0, 0

function on_frame()
  tick = tick + 1
  if n >= LIMIT or tick % EVERY ~= 0 then return end
  local p = gd.player(1)
  if not p or not p.anim_symbol then return end
  local js = gd.joints(1, true)   -- fresh: every matrix brought up to date first
  if not js then return end
  local parts = {}
  for i, j in ipairs(js) do
    -- a joint whose matrix the game did not compute this frame (valid = false) is logged as "-"
    if j.valid then
      parts[i] = string.format("%.4f,%.4f,%.4f", j.x or 0, j.y or 0, j.z or 0)
    else
      parts[i] = "-"
    end
  end
  gd.log(string.format("JPF %s %.3f %d %s", p.anim_symbol, p.anim_frame_f or -1, p.facing or 0,
                       table.concat(parts, ";")))
  n = n + 1
end
