-- Flight (Up B) with a flight aerial, a reverse ledge grab from flight, and the four ledge options.
gd.run(function()
  local ok, why = pcall(function()
    CAP.burners()
    CAP.setup(30, 14, 14, 80, 40)
    local R, top = CAP.edge()
    local only = CFG and CFG.only
    local function clip(label, o, fn)
      if only and not (',' .. only .. ','):find(',' .. label .. ',', 1, true) then return end
      CAP.reset(o); CAP.clip(label); CAP.rec(true)
      local ok2, e = pcall(fn)
      if not ok2 then CAP.log('FAIL ' .. label .. ' ' .. tostring(e)) end
      CAP.endclip()
    end

    -- Up B: a 20-frame steerable rise (8 directions), then helpless. A or C-stick during it is a flight aerial.
    clip('flight_aerial', {x1 = 0, x2 = 26, y2 = 0, camx = 14, camz = 70, camy = 14, camiy = 10}, function()
      CAP.wait(10)
      CAP.tap({buttons = 'B', y = 127}, 3); CAP.wait(3)
      for t = 1, 8 do CAP.tap({x = 90, y = 90}, 1); CAP.wait(1) end
      CAP.when({'Flight', 'FlightU', 'FlightF', 'FlightB'}, 8, {buttons = 'A', x = 127}, 3, 20)
      CAP.wait(80)
    end)

    -- fly in from off stage with his back to the ledge: the ledge is caught going the other way
    clip('flight_ledge', {x1 = R + 14, y1 = top - 18, x2 = R - 60, camx = R - 4, camz = 60, camy = -6, camiy = -10, settle = 3}, function()
      CAP.tap({buttons = 'B', y = 127}, 3); CAP.wait(3)
      for t = 1, 40 do
        CAP.tap({x = -90, y = 90}, 1); CAP.wait(1)
        if tostring(gd.player(1).motion_name):sub(1, 5) == 'Cliff' then break end
      end
      CAP.wait(60)
    end)

    local function grab_ledge()
      for _, p in ipairs({{8, -14}, {5, -10}, {12, -18}, {3, -8}, {16, -24}}) do
        gd.input(1, {}, 1); gd.wait(2)
        CAP.tp(1, R - 30, top); CAP.tp(2, -60, top)
        gd.wait(20)
        gd.input(1, {x = -127}, 6); gd.wait(8)
        gd.input(1, {}, 1); gd.wait(14)
        CAP.tp(1, R + p[1], top + p[2]); gd.wait(1)
        for t = 1, 45 do
          gd.input(1, {x = -40}, 1); gd.wait(1)
          if tostring(gd.player(1).motion_name) == 'CliffCatch' then return true end
        end
      end
      return false
    end
    local function ledge_opt(label, inp, btn, pct)
      if only and not (',' .. only .. ','):find(',' .. label .. ',', 1, true) then return end
      CAP.reset{x2 = -60, camx = R - 10, camz = 60, camy = -8, camiy = -14, settle = 5}
      gd.set_percent(1, pct or 0)
      if not grab_ledge() then CAP.log('FAIL ' .. label .. ' no ledge'); return end
      CAP.clip(label); CAP.rec(true)
      CAP.wait(36)                       -- hang
      local spec = {x = inp.x or 0, y = inp.y or 0, buttons = btn}
      gd.input(1, spec, 3)
      CAP.wait(75)
      CAP.endclip()
    end
    ledge_opt('ledge_getup', {x = -127})
    ledge_opt('ledge_attack', {}, 'A')
    ledge_opt('ledge_roll', {}, 'R')
    ledge_opt('ledge_jump', {}, 'X')

    CAP.log('DONE')
  end)
  if not ok then CAP.log('FAIL ' .. tostring(why)) end
  gd.quit()
end)
