-- Live probe of the four ground specials (and a grab) of P1 against an idle P2 at three ranges.
-- Logs: every distinct live item (articles/projectiles: kind, owner, first frame) and every connected hit
-- (on_hit info: damage, angle, kbg, bkb, wbk, element, shield damage, item or fighter hitbox) as ACEPROBE
-- lines of "key=value" pairs, plus the P1 action sequence. Gameplay numbers only.
--   MELEE_TURBO=1 MELEE_SCENE="mode=vs;p1=mex:27;p2=mario;stage=fd" MELEE_PAD_SCRIPT=<this file>
-- Output: scripts-data/pad_script/probe.txt (collect with tools/research/ace_hitbox_batch.sh style loops).
local out = {}
local function put(s) out[#out + 1] = s end
local cur = { trial = "-", range = 0 }
local NL = string.char(10)

function on_hit(attacker, victim, info)
  local parts = { "HIT", "trial=" .. cur.trial, "range=" .. cur.range, "atk=" .. tostring(attacker), "vic=" .. tostring(victim) }
  for _, k in ipairs({ "dealt", "damage", "angle", "kbg", "bkb", "wbk", "element_name", "shield_damage", "hitbox", "item", "attacker_sub", "group", "bone", "hit_air", "hit_ground" }) do
    if info and info[k] ~= nil then parts[#parts + 1] = k .. "=" .. tostring(info[k]) end
  end
  put(table.concat(parts, " "))
end

local specials = {
  { "B", "B" },
  { "sideB", { buttons = "B", x = 127 } },
  { "upB", { buttons = "B", y = 127 } },
  { "downB", { buttons = "B", y = -127 } },
  { "grab", "Z" },
  { "jab", "A" },
  { "ftilt", { buttons = "A", x = 60 } },
  { "fsmash", { cx = 127 } },
  { "usmash", { cy = 127 } },
  { "dsmash", { cy = -127 } },
}
local ranges = { 10, 28, 70 }
if gd.lab_env and gd.lab_env("QUICK") then ranges = { 12 } end

local function ready()
  local a, b = gd.player(1), gd.player(2)
  return a and b and a.action == 14 and b.action == 14
end
local function settle(p)
  if not gd.wait_until(ready, 300) then put("STUCK before trial=" .. cur.trial .. " range=" .. cur.range .. " p1action=" .. tostring(gd.player(1) and gd.player(1).action)) gd.wait(30) end
  gd.set_percent(2, 0)
  gd.set_percent(1, 0)
  gd.set_stocks(1, 99)
  gd.set_stocks(2, 99)
  local ok1, e1 = pcall(gd.teleport, 1, 0, 0)
  local ok2, e2 = pcall(gd.teleport, 2, p, 0)
  if not (ok1 and ok2) then put("TELEPORT-REFUSED trial=" .. cur.trial .. " range=" .. cur.range .. " " .. tostring(e1 or e2)) gd.wait(240) end
  gd.wait(5)
  gd.wait_until(ready, 600)
  gd.wait(10)
end

gd.run(function()
  gd.wait_until(function() return gd.match().active and gd.player(1) ~= nil and gd.player(2) ~= nil end, 3000)
  gd.wait_until(ready, 900)
  local p1 = gd.player(1)
  put("HEAD char=" .. tostring(p1.char_name) .. " kind=" .. tostring(p1.kind))
  for _, sp in ipairs(specials) do
    for _, r in ipairs(ranges) do
      cur.trial, cur.range = sp[1], r
      settle(r)
      local seen = {}
      local last = -1
      gd.input(1, sp[2], 3)
      for f = 1, 110 do
        gd.wait(1)
        local p = gd.player(1)
        if p and p.action ~= last then
          put("ACT trial=" .. sp[1] .. " range=" .. r .. " f=" .. f .. " action=" .. tostring(p.action) .. " name=" .. tostring(p.motion_name))
          last = p.action
        end
        for _, it in ipairs(gd.items() or {}) do
          local key = tostring(it.kind) .. "/" .. tostring(it.owner_port)
          if not seen[key] then
            seen[key] = true
            put("ITEM trial=" .. sp[1] .. " range=" .. r .. " f=" .. f .. " kind=" .. tostring(it.kind) .. " owner=" .. tostring(it.owner_port) .. " layer=" .. tostring(it.layer))
          end
        end
        local hb = gd.hitboxes(1)
        if hb and f % 3 == 0 then
          for _, h in ipairs(hb) do
            if h.id and h.id >= 4 then put("THROWNHB trial=" .. sp[1] .. " f=" .. f .. " dmg=" .. tostring(h.damage)) end
          end
        end
      end
      gd.wait(20)
      gd.data_write("probe.txt", table.concat(out, NL) .. NL) -- partial output survives a stuck trial
    end
  end
  local okw, why = gd.data_write("probe.txt", table.concat(out, NL) .. NL)
  gd.log("ACEPROBEDONE " .. tostring(okw) .. " lines=" .. #out)
  gd.quit()
end)
