gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
    gd.cpu_mode(2, 'stand')
    local function tp(p, x, y) for i = 1, 60 do if pcall(gd.teleport, p, x, y) then return end gd.wait(20) end error('tp') end
    for _, d in ipairs({2, 6}) do
      tp(1, 0, 0); tp(2, 30, 0); gd.set_percent(2, 0); gd.wait(40)
      gd.input(1, {x = 60}, 3); gd.wait(25)
      tp(1, 0, 0); gd.wait(2)
      local face = (gd.player(1).facing or 1) >= 0 and 1 or -1
      tp(2, d * face, 0); gd.wait(2)
      gd.input(1, (CFG and CFG.kind == 'f') and {buttons = 'A', x = 127 * face} or {buttons = 'A', y = 127}, 2)
      for t = 1, 50 do
        gd.wait(1)
        if t <= 10 then pcall(gd.teleport, 2, gd.player(1).x + face * d, 0) end
        local p, q = gd.player(1), gd.player(2)
        local hb = {}
        local okh, hbs = pcall(gd.hitboxes, 1)
        if okh and type(hbs) == 'table' then for _, h in ipairs(hbs) do hb[#hb + 1] = string.format('id%d(%.0f,%.0f r%.1f d%.0f a%.0f)', h.id, h.x, h.y, h.radius, h.damage, h.angle) end end
        if t >= 6 and t <= 30 and t % 2 == 0 then gd.log(string.format('USDBG d=%d t=%d P1 %s | P2 %s x=%.1f y=%.1f pct=%.1f hitlag=%s | %s', d, t, tostring(p.motion_name), tostring(q.motion_name), q.x, q.y, q.percent, tostring(q.hitlag), table.concat(hb, ' '))) end
      end
    end
  end)
  if not ok then gd.log('USDBG FAIL ' .. tostring(why)) end
  gd.quit()
end)
