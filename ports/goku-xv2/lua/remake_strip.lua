-- Remake phase 1 frame strips, one slot group per run (CLEAN display: no hitbox overlay; the moves are HB-NONE, so this is the animation only).
-- Config (kame_run.py --cfg group=loco|normals|aerials|grab|specials|defence|damage): prints "RSTRIP <move> <path>" per screenshot (8 per move, every STEP frames).
-- tools/remake_strips.py joins them into one strip PNG per move and one sheet per group.
local C = CFG or {}
local GROUP = C.group or 'loco'
local STEP = tonumber(C.step or 4)
local SHOTS = tonumber(C.shots or 8)
local MOVES = {
  loco = {
    {'walk', {x = 70}, 40, 'hold'}, {'run', {x = 127}, 40, 'hold'}, {'crouch', {y = -127}, 40, 'hold'}, {'turn', {x = -127}, 4},
    {'jump', {buttons = 'X'}, 3}, {'doublejump', {buttons = 'X'}, 3, 'air'}, {'fall', {}, 1, 'air'},
  },
  normals = {
    {'jab', {buttons = 'A'}, 2}, {'ftilt', {x = 60, buttons = 'A'}, 2}, {'utilt', {y = 60, buttons = 'A'}, 2}, {'dtilt', {y = -60, buttons = 'A'}, 2},
    {'dashattack', {x = 127, buttons = 'A'}, 8}, {'fsmash', {cx = 127}, 2}, {'usmash', {cy = 127}, 2}, {'dsmash', {cy = -127}, 2},
  },
  aerials = {
    {'nair', {buttons = 'A'}, 2, 'air'}, {'fair', {cx = 127}, 2, 'air'}, {'bair', {cx = -127}, 2, 'air'}, {'uair', {cy = 127}, 2, 'air'}, {'dair', {cy = -127}, 2, 'air'},
  },
  grab = {
    {'grab', {buttons = 'Z'}, 2}, {'dashgrab', {x = 127, buttons = 'Z'}, 8},
  },
  defence = {
    {'shield', {buttons = 'L'}, 30, 'hold'}, {'rollF', {buttons = 'L', x = 127}, 4}, {'rollB', {buttons = 'L', x = -127}, 4}, {'spotdodge', {buttons = 'L', y = -127}, 4},
    {'airdodge', {buttons = 'L', x = 90}, 3, 'air'},
  },
  specials = {
    {'neutralB', {buttons = 'B'}, 2}, {'sideB', {x = 127, buttons = 'B'}, 2}, {'upB', {y = 127, buttons = 'B'}, 2}, {'downB_tap', {y = -127, buttons = 'B'}, 3},
    {'downB_hold', {y = -127, buttons = 'B'}, 60, 'hold'}, {'homing', {buttons = 'L+B', x = 127}, 2, 'shield', 50},
  },
}
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function clean() for _, pt in ipairs({1, 2}) do pcall(gd.debug_draw, pt, 0) end end
    local function cam()
      if C.cam == '0' then return end
      local p = gd.player(1)
      local x, y = p.x or 0, p.y or 0
      gd.camera_set{eye = {x = x, y = y + 14, z = 95}, interest = {x = x, y = y + 10, z = 0}, fov = 40}
    end
    for _, mv in ipairs(MOVES[GROUP]) do
      local name, spec, frames, mode, ki = mv[1], mv[2], mv[3], mv[4], mv[5]
      gd.input(1, {}, 1); gd.wait(3)
      gd.teleport(1, 0, 0); gd.teleport(2, 38, 0); gd.set_percent(1, 0); gd.set_percent(2, 0)
      if gd.combo_ki then gd.combo_ki(1, ki or 50) end
      gd.wait(50); clean(); cam()
      if mode == 'air' then gd.input(1, {buttons = 'X'}, 3); gd.wait(14) end
      if mode == 'shield' then gd.input(1, {buttons = 'L'}, 14); gd.wait(12) end
      if name == 'fall' then gd.input(1, {buttons = 'X'}, 3); gd.wait(40) end
      gd.input(1, spec, frames)
      for i = 1, SHOTS do
        gd.wait(STEP); clean(); cam()
        local _, path = gd.screenshot(string.format('rs_%s_%s_%02d', GROUP, name, i))
        gd.log('RSTRIP ' .. name .. ' ' .. tostring(path) .. ' ' .. tostring(gd.player(1).motion_name))
      end
      gd.input(1, {}, 1); gd.wait(30)
    end
    gd.log('RSTRIP PASS')
  end)
  if not ok then gd.log('RSTRIP FAIL ' .. tostring(why)) end
  gd.quit()
end)
