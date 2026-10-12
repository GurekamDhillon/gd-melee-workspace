gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
    gd.cpu_mode(2, 'stand')
    local function tp(p, x, y) for i = 1, 60 do if pcall(gd.teleport, p, x, y) then return end gd.wait(20) end error('tp') end
    tp(1, 0, 0); tp(2, 30, 0); gd.wait(40)
    gd.input(1, {x = 60}, 3); gd.wait(28)
    tp(1, 0, 0); gd.wait(2)
    local face = (gd.player(1).facing or 1) >= 0 and 1 or -1
    tp(2, 4 * face, 0); gd.wait(2)
    gd.set_percent(2, 250)
    local s0 = gd.player(2).stocks
    gd.input(1, {buttons = 'A', x = 127 * face}, 2)
    for t = 1, 200 do
      gd.wait(1)
      local p = gd.player(2)
      if t % 10 == 0 then gd.log(string.format('KODBG t=%d %s x=%.0f y=%.0f stocks=%s pct=%s', t, tostring(p.motion_name), p.x, p.y, tostring(p.stocks), tostring(p.percent))) end
    end
  end)
  if not ok then gd.log('KODBG FAIL ' .. tostring(why)) end
  gd.quit()
end)
