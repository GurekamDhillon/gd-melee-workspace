-- Kamehameha frame strips for the native charge model (B once starts the self-running charge, B again fires the level).
-- Config (tools/kame_run.py --cfg k=v): hold = frames from the first B to the firing B (default 60), tag (file prefix), tail (frames after the fire, default 80),
-- gap (frames between shots after the fire, default 4), hgap (between shots while charging, default 30), air=1 (fire from the air), face=left (Goku faces left,
-- victim on the left), dist (victim distance), camx / camz / fov / camy (the clean side camera), zoom=1 (a tighter camera on the hands), fire=0 (never fire: shoot the charge only).
-- Prints "KAMESHOT <path>" per shot. The LAB display is CLEAN (kame_run.py sets MELEE_LAB_UI=0: no hitbox overlay).
local C = CFG or {}
local HOLD = tonumber(C.hold or 60)
local TAG = C.tag or 'kame'
local AIR = C.air == '1'
local LEFT = C.face == 'left'
local GAP = tonumber(C.gap or 4)
local HGAP = tonumber(C.hgap or 30)
local DIST = tonumber(C.dist or 38) * (LEFT and -1 or 1)
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    gd.teleport(1, 0, AIR and 40 or 0); gd.teleport(2, DIST, 0)
    gd.set_percent(1, 0); gd.set_percent(2, 0); gd.wait(30)
    if LEFT then gd.input(1, {x = -127}, 6); gd.wait(20); gd.teleport(1, 0, AIR and 40 or 0); gd.teleport(2, DIST, 0); gd.wait(10) end
    local g = gd.player(1)
    gd.log(string.format('KAME goku x=%.1f y=%.1f facing=%s', g.x or -1, g.y or -1, tostring(g.facing)))
    if C.cam ~= '0' then
      local sgn = LEFT and -1 or 1
      local cx = tonumber(C.camx or (20 * sgn))
      local zoom = C.zoom == '1'
      gd.camera_set{eye = {x = cx, y = tonumber(C.camy or (zoom and 12 or 14)), z = tonumber(C.camz or (zoom and 42 or 95))},
                    interest = {x = cx, y = AIR and 40 or (zoom and 9 or 10), z = 0}, fov = tonumber(C.fov or 40)}
    end
    local n = 0
    local function shot(label)
      n = n + 1
      local _, path = gd.screenshot(string.format('%s_%02d_%s', TAG, n, label))
      gd.log('KAMESHOT ' .. tostring(path))
    end
    gd.input(1, {buttons = 'B'}, 2)
    local fired = false
    local t = 0
    local total = HOLD + tonumber(C.tail or 80)
    while t < total do
      gd.wait(1); t = t + 1
      if t == HOLD and C.fire ~= '0' then gd.input(1, {buttons = 'B'}, 2); fired = true end
      local gap = (t <= HOLD) and HGAP or GAP
      if t % gap == 0 or t == HOLD then
        local p = gd.player(1)
        local lua = gd.fighter_lua(1)
        shot(string.format('t%04d_%s_af%d_c%d', t, tostring(p.motion_name), p.action_frame or -1, (lua and lua.state.charge) or -1))
        local hb = gd.hitboxes(1) or {}
        gd.log(string.format('KAME t=%d state=%s af=%s hitboxes=%d p2pct=%.1f', t, tostring(p.motion_name), tostring(p.action_frame), #hb, gd.player(2).percent or -1))
      end
    end
    gd.wait(12)   -- the last screenshot is written a few frames after the call
    gd.log('KAME DONE')
  end)
  if not ok then gd.log('KAME FAIL ' .. tostring(why)) end
  gd.quit()
end)
