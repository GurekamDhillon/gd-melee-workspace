-- @name: Projectile probe
-- @gameplay: true
-- Goku (P1) jabs once in the LAB (the driver put a CALL geno.article.spawn in the jab through the Workbench); logs every live Goku article each frame:
--   PROJPROBE f=<tick> kind=<geno_kind> id=<n> x= y= vx= vy= alive= facing=
-- plus the fighter's position at the first sight of each article id (PROJPROBE spawn ...).  The driver
-- (run_projectile_check.py) compares those rows with the path the Blender add-on predicts.
local function log(fmt, ...) gd.log("PROJPROBE " .. string.format(fmt, ...)) end
local phase, t, quit_t = "boot", 0, 0
local seen = {}
function on_frame()
  if phase == "end" then
    quit_t = quit_t + 1
    if quit_t == 20 then gd.quit() end
    return
  end
  local m = gd.match()
  if phase == "boot" then
    if m.active and m.frame > 90 and gd.lab_mode() then
      gd.cpu_mode(2, "stand"); gd.teleport(1, 0, 0); gd.teleport(2, -55, 0)
      gd.set_percent(1, 0); gd.set_percent(2, 0)
      phase, t = "wait", 0
    end
    return
  end
  t = t + 1
  if phase == "wait" then
    if t == 30 then phase, t = "run", 0; log("start") end
    return
  end
  if t == 2 then gd.input(1, { buttons = "A" }, 1) end
  if t % 6 == 0 then
    local p = gd.player(1)
    log("state t=%d motion=%s af=%s items=%d lua=%s", t, tostring(p and p.motion_name), tostring(p and p.action_frame), #(gd.items() or {}), tostring(gd.fighter_lua(1) ~= nil))
  end
  for _, it in ipairs(gd.items() or {}) do
    if it.owner_port == 1 then
      it.geno_kind = it.geno_kind or -1
      if not seen[it.id] then
        seen[it.id] = true
        local p = gd.player(1)
        log("spawn tick=%d kind=%d id=%d px=%.4f py=%.4f x=%.4f y=%.4f vx=%.4f vy=%.4f facing=%s", t, it.geno_kind, it.id, p.x or 0, p.y or 0, it.x, it.y, it.vx, it.vy, tostring(it.facing))
      end
      log("f=%d kind=%d id=%d x=%.4f y=%.4f vx=%.4f vy=%.4f alive=%d", t, it.geno_kind, it.id, it.x, it.y, it.vx, it.vy, it.frame_alive or -1)
    end
  end
  if t >= 80 then phase = "end"; log("done") end
end
