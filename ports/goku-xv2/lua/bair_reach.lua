-- Back air reach (owner #11): short hop, bair, and per frame the active hitboxes' position behind Goku (root-relative, facing-signed, positive =
-- behind) plus the sphere radius. Logs BAIRREACH lines; effective reach = max(behind + radius). Scene: p1=geno:goku-xv2/hu, p2=mario.
local function log(fmt, ...) gd.log('BAIRREACH ' .. string.format(fmt, ...)) end
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand'); gd.teleport(2, 80, 0); gd.wait(30)
    gd.teleport(1, 0, 0); gd.wait(30)
    gd.input(1, { buttons = 'X' }, 3); gd.wait(3)
    for _ = 1, 30 do local m = gd.player(1).motion_name or ''; if m == 'JumpF' or m == 'JumpB' or m == 'JumpAerialF' then break end gd.wait(1) end
    gd.wait(6)
    local face = gd.player(1).facing or 1
    gd.input(1, { x = -face * 127, buttons = 'A' }, 2); gd.wait(2)
    local best, shown = -99, false
    for f = 1, 40 do
      local p = gd.player(1)
      local hbs = gd.hitboxes(1) or {}
      for i, h in ipairs(hbs) do
        if not shown then
          local ks = {}
          for k in pairs(h) do ks[#ks + 1] = k end
          table.sort(ks); log('hitbox keys: %s', table.concat(ks, ','))
          shown = true
        end
        local hx = h.x or h.px or (h.pos and h.pos.x) or 0
        local hy = h.y or h.py or (h.pos and h.pos.y) or 0
        local r = h.size or h.radius or 0
        local behind = -(hx - (p.x or 0)) * face
        log('f=%d motion=%s hb%d behind=%.2f up=%.2f radius=%.2f reach=%.2f', f, tostring(p.motion_name), i, behind, hy - (p.y or 0), r, behind + r)
        if behind + r > best then best = behind + r end
      end
      local js = gd.joints(1) or {}
      local fr = js[7 + 1]
      if fr and fr.x then log('f=%d FOOT_R behind=%.2f up=%.2f', f, -(fr.x - (p.x or 0)) * face, fr.y - (p.y or 0)) end
      gd.wait(1)
    end
    log('RESULT effective reach behind = %.2f units', best)
  end)
  if not ok then gd.log('BAIRREACH FAIL ' .. tostring(why)) end
  gd.quit()
end)
