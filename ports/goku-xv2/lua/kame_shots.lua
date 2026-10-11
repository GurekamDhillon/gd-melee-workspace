-- Kamehameha frame strips: charge, release, beam, impact. Config keys: hold (frames B is held, default 62), tag (file prefix),
-- tail (frames after the hold, default 120), air=1 (fire from the air), gap (frames between shots, default 4), dist (victim x). Prints "KAMESHOT <path>" per shot.
local C = CFG or {}   -- the runner (tools/kame_run.py --cfg k=v) prepends CFG={...}; the sandbox has no os.getenv
local HOLD = tonumber(C.hold or 62)
local TAG = C.tag or 'kame'
local AIR = C.air == '1'
local GAP = tonumber(C.gap or 4)
local DIST = tonumber(C.dist or 38)
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand'); gd.teleport(1, 0, AIR and 40 or 0); gd.teleport(2, DIST, 0)
    gd.set_percent(1, 0); gd.set_percent(2, 0); gd.wait(30)
    local cam = gd.camera_get()
    gd.log('KAME camera ' .. tostring(cam and cam.eye and (cam.eye.x or cam.eye[1])) .. ' ' .. tostring(cam and cam.eye and (cam.eye.y or cam.eye[2])) .. ' ' .. tostring(cam and cam.eye and (cam.eye.z or cam.eye[3])) .. ' fov ' .. tostring(cam and cam.fov))
    local g = gd.player(1)
    gd.log(string.format('KAME goku x=%.1f y=%.1f facing=%s', g.x or -1, g.y or -1, tostring(g.facing)))
    if C.cam ~= '0' then
      local cx = tonumber(C.camx or 20)
      gd.camera_set{eye = {x = cx, y = 14, z = tonumber(C.camz or 95)}, interest = {x = cx, y = 10, z = 0}, fov = tonumber(C.fov or 40)}
    end
    local n = 0
    local function shot(label)
      n = n + 1
      local okp, path = gd.screenshot(string.format('%s_%02d_%s', TAG, n, label))
      gd.log('KAMESHOT ' .. tostring(path))
    end
    gd.input(1, {buttons = 'B'}, HOLD)
    local total = HOLD + tonumber(C.tail or 120)
    for t = 1, total do
      gd.wait(1)
      if t % GAP == 0 then
        local p = gd.player(1)
        local lua = gd.fighter_lua(1)
        shot(string.format('t%03d_%s_af%d_c%d', t, tostring(p.motion_name), p.action_frame or -1, (lua and lua.state.charge) or -1))
        local hb = gd.hitboxes(1) or {}
        gd.log(string.format('KAME t=%d state=%s af=%s hitboxes=%d p2pct=%.1f p2x=%.1f p2=%s', t, tostring(p.motion_name), tostring(p.action_frame), #hb, gd.player(2).percent or -1, gd.player(2).x or -1, tostring(gd.player(2).motion_name)))
      end
    end
    gd.wait(12)   -- the last screenshot is written a few frames after the call
    gd.log('KAME DONE')
  end)
  if not ok then gd.log('KAME FAIL ' .. tostring(why)) end
  gd.quit()
end)
