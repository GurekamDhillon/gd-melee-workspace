-- Ki: ground charge, air charge descent, shield -> dash kick (homing), D-pad ki blast barrage.
gd.run(function()
  local ok, why = pcall(function()
    CAP.burners()
    CAP.setup(40, 18, 14, 70, 40)
    local only = CFG and CFG.only
    local function clip(label, o, fn)
      if only and not (',' .. only .. ','):find(',' .. label .. ',', 1, true) then return end
      CAP.reset(o); CAP.clip(label); CAP.rec(true)
      local ok2, e = pcall(fn)
      if not ok2 then CAP.log('FAIL ' .. label .. ' ' .. tostring(e)) end
      CAP.endclip()
    end

    clip('ki_charge', {ki = 0, x2 = 30, camx = 8, camz = 50, camy = 9, camiy = 6}, function()
      CAP.wait(10)
      CAP.tap({buttons = 'B', y = -127}, 100)
      CAP.wait(100); CAP.wait(20)
    end)

    clip('ki_charge_air', {ki = 0, x1 = 0, y1 = 40, x2 = 30, camx = 8, camz = 70, camy = 24, camiy = 18, settle = 3}, function()
      CAP.tap({buttons = 'B', y = -127}, 90)
      CAP.wait(110)
    end)

    clip('dash_kick', {ki = 60, x2 = 22, camx = 12, camz = 60, camy = 10, camiy = 7}, function()
      CAP.wait(10)
      CAP.tap({buttons = 'R'}, 40); CAP.wait(14)
      CAP.tap({buttons = 'R'}, 3); CAP.wait(0)
      CAP.tap({buttons = 'R B'}, 3)
      CAP.wait(80)
    end)

    clip('ki_blast', {ki = 100, x2 = 60, camx = 24, camz = 75, camy = 12, camiy = 9}, function()
      CAP.wait(10)
      CAP.tap({buttons = 'DOWN'}, 140)   -- held past frame 22 the blast chains into alternating hands
      CAP.wait(150); CAP.wait(30)
    end)

    CAP.log('DONE')
  end)
  if not ok then CAP.log('FAIL ' .. tostring(why)) end
  gd.quit()
end)
