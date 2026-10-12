-- Owner's re-shoots of the first reel: Dragon Rush that connects, a full-ki powered flight that ends in a flight aerial that hits,
-- and a Super Kamehameha charged past the 10 second full tier (docs: KAMEHAMEHA.md 0c: full at 600 frames, Super needs ki 100).
gd.run(function()
  local ok, why = pcall(function()
    CAP.burners()
    CAP.setup(30, 14, 14, 80, 40)
    local only = CFG and CFG.only
    local function clip(label, o, fn)
      if only and not (',' .. only .. ','):find(',' .. label .. ',', 1, true) then return end
      CAP.reset(o); CAP.clip(label); CAP.rec(true)
      local ok2, e = pcall(fn)
      if not ok2 then CAP.log('FAIL ' .. label .. ' ' .. tostring(e)) end
      CAP.endclip()
    end

    -- Side B with the dummy inside its reach (14-22 units connects): the strike hits and the Rush Combo plays out
    clip('rush_hit', {x2 = 16, camx = 26, camz = 72, camy = 11, camiy = 8}, function()
      CAP.wait(10)
      CAP.tap({buttons = 'B', x = 127}, 2)
      CAP.wait(110)
    end)

    -- full ki: a long powered flight steered through a few directions, then a flight aerial at the opponent
    clip('flight_power', {ki = 100, x1 = 0, x2 = 46, camx = 26, camz = 98, camy = 26, camiy = 22}, function()
      local function hold(x, y, n) for _ = 1, n do CAP.stick(x, y); CAP.wait(1) end end
      CAP.wait(6)
      CAP.tap({buttons = 'B', y = 127}, 3); CAP.wait(3)
      hold(90, 90, 18)          -- up and forward
      hold(0, 127, 12)          -- straight up
      hold(-100, 70, 16)        -- back and up
      for _ = 1, 50 do          -- then in on the opponent
        local me, fa = gd.player(1), gd.player(2)
        local dx, dy = (fa.x - tonumber(CFG and CFG.off or 6)) - me.x, (fa.y + tonumber(CFG and CFG.h or 18)) - me.y
        local d = math.sqrt(dx * dx + dy * dy)
        if d < tonumber(CFG and CFG.reach or 4) then break end
        CAP.stick(127 * dx / d, 127 * dy / d); CAP.wait(1)
      end
      hold(0, 0, tonumber(CFG and CFG.stop or 5))       -- bleed the flight speed off so the aerial has time to swing at him
      local aer = (CFG and CFG.aer) or 'nair'
      local spec = aer == 'dair' and {buttons = 'A', y = -100} or aer == 'nair' and {buttons = 'A'} or aer == 'bair' and {buttons = 'A', x = -100} or {buttons = 'A', x = 100}
      CAP.when_fn(function() return true end, spec, 4, 1)
      CAP.wait(110)
      CAP.stick_flush()
    end)

    -- Super Kamehameha: ki 100, hold the charge past the 600 frame full tier, then fire
    clip('kame_super', {ki = 100, x2 = 38, camx = 18, camz = 72, camy = 12, camiy = 8}, function()
      CAP.tap({buttons = 'B'}, 2)
      CAP.wait(tonumber(CFG and CFG.charge or 660))
      CAP.tap({buttons = 'B'}, 2)
      CAP.wait(120)
    end)

    CAP.log('DONE')
  end)
  if not ok then CAP.log('FAIL ' .. tostring(why)) end
  gd.quit()
end)
