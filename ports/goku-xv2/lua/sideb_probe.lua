-- Side B (Rush) numbers: horizontal travel and vertical drop over the move, on the ground and in the air. Tag SIDEB.
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
    gd.cpu_mode(2, 'stand')
    local function tp(p, x, y) for i = 1, 40 do if pcall(gd.teleport, p, x, y) then return end gd.wait(20) end error('tp') end
    for _, air in ipairs({false, true}) do
      tp(1, 0, 0); tp(2, -150, 0); gd.combo_ki(1, 50); gd.set_percent(1, 0); gd.wait(40)
      gd.input(1, {x = 60}, 3); gd.wait(25)
      tp(1, 0, air and 100 or 0); gd.wait(2)
      local face = (gd.player(1).facing or 1) >= 0 and 1 or -1
      local g0 = gd.player(1)
      gd.input(1, {x = 127 * face, buttons = 'B'}, 2)
      local trace, last = {}, nil
      for t = 1, 70 do
        gd.wait(1)
        local p = gd.player(1)
        if tostring(p.motion_name) == 'Rush' then last = {t = t, x = p.x, y = p.y} end
        if t % 10 == 0 then trace[#trace + 1] = string.format('%d:%s dx%.1f dy%.1f', t, tostring(p.motion_name), (p.x - g0.x) * face, p.y - g0.y) end
      end
      gd.log(string.format('SIDEB %s: during Rush last frame t=%s dx %.1f dy %.1f | %s', air and 'air' or 'ground', last and last.t or 'nil', last and (last.x - g0.x) * face or 0, last and last.y - g0.y or 0, table.concat(trace, ' ')))
      gd.wait(60)
    end
  end)
  if not ok then gd.log('SIDEB FAIL ' .. tostring(why)) end
  gd.quit()
end)
