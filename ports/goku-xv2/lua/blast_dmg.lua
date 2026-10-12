gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
    gd.cpu_mode(2, 'stand')
    local function tp(p, x, y) for i = 1, 40 do if pcall(gd.teleport, p, x, y) then return end gd.wait(20) end error('tp') end
    for rep = 1, 3 do
      tp(1, 0, 0); tp(2, 30, 0); gd.combo_ki(1, 50); gd.set_percent(2, 0); gd.wait(40)
      gd.input(1, {x = 60}, 3); gd.wait(25)
      local face = (gd.player(1).facing or 1) >= 0 and 1 or -1
      tp(2, 30 * face, 0); gd.wait(2)
      local p0 = gd.player(2).percent
      gd.input(1, {buttons = 'DOWN'}, 2)
      local last = p0
      for t = 1, 70 do gd.wait(1) local pp = gd.player(2).percent if pp ~= last then gd.log(string.format('BLASTDMG rep %d t=%d %.2f -> %.2f (+%.2f)', rep, t, last, pp, pp - last)) last = pp end end
      gd.wait(40)
    end
  end)
  if not ok then gd.log('BLASTDMG FAIL ' .. tostring(why)) end
  gd.quit()
end)
