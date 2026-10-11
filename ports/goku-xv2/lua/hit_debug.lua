-- Debug: run one input at a dummy and print live hitbox spheres each frame (tag HITDBG). CFG: dist, y, btn, x, cx, cy, z, air=1
local C = CFG or {}
gd.run(function()
  assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
  gd.cpu_mode(2, 'stand')
  gd.teleport(1, 0, tonumber(C.y or 0)); gd.teleport(2, tonumber(C.dist or 8), 0)
  gd.set_percent(2, 0); gd.wait(60)
  gd.teleport(1, 0, tonumber(C.y or 0)); gd.teleport(2, tonumber(C.dist or 8), 0); gd.wait(3)
  if C.air == '1' then gd.input(1, {buttons = 'X'}, 3); gd.wait(6) end
  local inp = {buttons = C.btn, x = tonumber(C.x), y = tonumber(C.sy), cx = tonumber(C.cx), cy = tonumber(C.cy)}
  gd.input(1, inp, 2)
  for t = 1, tonumber(C.n or 50) do
    gd.wait(1)
    local p, m = gd.player(1), gd.player(2)
    local hb = gd.hitboxes(1) or {}
    local s = ''
    for _, h in ipairs(hb) do s = s .. string.format(' [%.1f,%.1f,%.1f r%.1f d%.0f]', h.x or -1, h.y or -1, h.z or -1, h.size or h.radius or -1, h.damage or -1) end
    if #hb > 0 or t % 10 == 0 then gd.log(string.format('HITDBG t%d %s f%d goku(%.1f,%.1f) mario(%.1f,%.1f) pct %.1f%s', t, tostring(p.motion_name), p.action_frame or -1, p.x, p.y, m.x, m.y, m.percent, s)) end
  end
  gd.quit()
end)
