-- Skull Kid (ACE m-ex 40) up-tilt vs an idle Mario swept across x offsets. Needs the DIAG build where
-- gd.hitboxes(port,true) slot id 4 is the real x914[4] alias (xDF4[0]), not the thrown hitbox.
-- Logs per frame: every enabled hitbox slot (id,state,bone,world x/y/z,radius,damage), victim hurtcapsules at f=12,
-- and every connected hit (on_hit info). Gameplay numbers only.
--   MELEE_TURBO=1 MELEE_SCENE="mode=vs;p1=mex:40;p2=mario;stage=fd" MELEE_PAD_SCRIPT=<this file>
local out = {}
local NL = string.char(10)
local function put(s) out[#out + 1] = s end
local cur = { x = 0 }
function on_hit(attacker, victim, info)
  local parts = { "HIT", "x=" .. cur.x, "atk=" .. tostring(attacker), "vic=" .. tostring(victim) }
  for _, k in ipairs({ "dealt", "damage", "angle", "kbg", "bkb", "hitbox", "item", "bone", "group" }) do
    if info and info[k] ~= nil then parts[#parts + 1] = k .. "=" .. tostring(info[k]) end
  end
  put(table.concat(parts, " "))
end
local function ready()
  local a, b = gd.player(1), gd.player(2)
  return a and b and a.action == 14 and b.action == 14
end
local xs = { 6, 9, 12, 15, 18, 21, -6, -9, -12, -15 }
if gd.lab_env and gd.lab_env("QUICK") then xs = { 10 } end
gd.run(function()
  gd.wait_until(function() return gd.match().active and gd.player(1) ~= nil and gd.player(2) ~= nil end, 3000)
  gd.wait_until(ready, 900)
  put("HEAD char=" .. tostring(gd.player(1).char_name))
  for _, x in ipairs(xs) do
    cur.x = x
    gd.set_percent(1, 0); gd.set_percent(2, 0); gd.set_stocks(1, 99); gd.set_stocks(2, 99)
    pcall(gd.teleport, 1, 0, 0); pcall(gd.teleport, 2, x, 0)
    gd.wait(5); gd.wait_until(ready, 600); gd.wait(10)
    gd.input(1, { buttons = "A", y = 70 }, 3)
    local last = -1
    for f = 1, 45 do
      gd.wait(1)
      local p = gd.player(1)
      if p and p.action ~= last then
        put("ACT x=" .. x .. " f=" .. f .. " action=" .. tostring(p.action) .. " name=" .. tostring(p.motion_name))
        last = p.action
      end
      local hb = gd.hitboxes(1, true)
      if hb then
        for _, h in ipairs(hb) do
          if h.state and h.state > 0 then
            put(string.format("HB x=%d f=%d id=%d state=%d bone=%s hx=%.2f hy=%.2f hz=%.2f r=%.2f dmg=%.1f", x, f, h.id, h.state,
              tostring(h.bone), h.x or 0, h.y or 0, h.z or 0, h.radius or 0, h.damage or 0))
          end
        end
      end
      if f == 12 or f == 13 then
        for _, hc in ipairs(gd.hurtboxes(2) or {}) do
          put(string.format("HURT x=%d f=%d id=%d a=%.2f,%.2f,%.2f b=%.2f,%.2f,%.2f r=%.2f st=%s", x, f, hc.id, hc.ax, hc.ay, hc.az, hc.bx, hc.by, hc.bz, hc.radius, tostring(hc.state)))
        end
      end
    end
    gd.wait(20)
    gd.data_write("slot4.txt", table.concat(out, NL) .. NL)
  end
  gd.data_write("slot4.txt", table.concat(out, NL) .. NL)
  gd.log("SLOT4DONE lines=" .. #out)
  gd.quit()
end)
