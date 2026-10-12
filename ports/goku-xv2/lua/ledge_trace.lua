-- debug trace of one flight (LEDGETR)
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
    gd.cpu_mode(2, 'stand')
    local sb = gd.stage_bounds(); local R = sb.main_floor.right
    local function tp(p,x,y) for i=1,80 do if pcall(gd.teleport,p,x,y) then return end gd.wait(30) end end
    for _, face in ipairs({1, -1}) do
      gd.input(1, {}, 1); gd.wait(2)
      tp(1, R-30, 0); tp(2, -40, 0); gd.wait(30)
      gd.input(1, {x = 127*face}, 6); gd.wait(8); gd.input(1, {}, 1); gd.wait(14)
      tp(1, R-30, 0); gd.wait(2)
      tp(1, R+14, -16); gd.combo_ki(1, 0); gd.wait(2)
      local c = gd.combo(1)
      gd.log(string.format('LEDGETR start face %s ki %s', tostring(gd.player(1).facing), tostring(c and c.ki)))
      gd.input(1, {y = 127, buttons = 'B'}, 2)
      for t = 1, 30 do
        gd.wait(1)
        if t >= 3 then gd.input(1, {x = -127, y = 0}, 1) end
        local p = gd.player(1); local cc = gd.combo(1)
        local fl = gd.fighter_lua(1); local ss = ''
        if fl and fl.state then for k, v in pairs(fl.state) do ss = ss .. k .. '=' .. tostring(v) .. ' ' end end
        if t == 1 and fl then for k, v in pairs(fl) do gd.log('LEDGETR fl key ' .. k .. ' ' .. tostring(v)) end end
        gd.log(string.format('LEDGETR face %d t%d %s x %.1f y %.1f f %s vx %.2f vy %.2f ki %s slots %s', face, t, tostring(p.motion_name), p.x, p.y, tostring(p.facing), p.vel_x or -9, p.vel_y or -9, tostring(cc and cc.ki), ss))
        if tostring(p.motion_name):sub(1,5) == 'Cliff' then break end
      end
      gd.input(1, {y=-127}, 4); gd.wait(10)
    end
  end)
  gd.log('LEDGETR done ' .. tostring(ok) .. ' ' .. tostring(why))
  gd.quit()
end)
