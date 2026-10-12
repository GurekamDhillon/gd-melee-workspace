-- Ground and air clips: IT roll, Dragon Rush, light string -> heavy, launcher -> air string, fair spike, charged fsmash, grab.
gd.run(function()
  local ok, why = pcall(function()
    CAP.burners()
    CAP.setup(30, 14, 14, 80, 40)
    local R = CAP.edge()
    local only = CFG and CFG.only

    local function clip(label, o, fn)
      if only and not (',' .. only .. ','):find(',' .. label .. ',', 1, true) then return end
      CAP.reset(o); CAP.clip(label); CAP.rec(true)
      local ok2, e = pcall(fn)
      if not ok2 then CAP.log('FAIL ' .. label .. ' ' .. tostring(e)) end
      CAP.endclip()
    end

    clip('it_roll', {x2 = 40, camx = 18, camz = 60, camy = 9, camiy = 6}, function()
      CAP.wait(20)
      CAP.tap({buttons = 'R'}, 40); CAP.wait(7)
      CAP.tap({buttons = 'R', x = 127}, 8)
      CAP.wait(60)
    end)

    clip('rush', {x2 = 34, camx = 20, camz = 60, camy = 9, camiy = 6}, function()
      CAP.wait(15)
      CAP.tap({buttons = 'B', x = 127}, 2)
      CAP.wait(100)
    end)

    clip('light_heavy', {x2 = 10, camx = 8, camz = 50, camy = 9, camiy = 6}, function()
      CAP.wait(15)
      CAP.tap({buttons = 'A'}, 2)
      CAP.when({'Attack11'}, 6, {buttons = 'A'}, 2, 40)
      CAP.when({'Attack12'}, 10, {buttons = 'A'}, 2, 40)
      CAP.when({'Light3'}, 18, {buttons = 'A'}, 2, 40)
      CAP.when({'Light4'}, 18, {buttons = 'A'}, 2, 40)
      CAP.when({'Light5'}, 16, {cx = 127}, 6, 40)
      CAP.wait(80)
    end)

    clip('launcher_air', {x2 = 10, camx = 8, camz = 50, camy = 9, camiy = 6}, function()
      CAP.wait(15)
      CAP.tap({buttons = 'A'}, 2)
      CAP.when({'Attack11'}, 6, {buttons = 'A'}, 2, 40)
      CAP.when({'Attack12'}, 10, {cy = 127}, 2, 40)
      CAP.when({'HeavyUp'}, 18, {buttons = 'X'}, 2, 60)
      CAP.when({'JumpF', 'JumpB'}, 0, {buttons = 'A'}, 4, 40)
      CAP.when({'AttackAirN'}, 17, {buttons = 'A'}, 4, 40)
      CAP.when({'AttackAirN'}, 17, {buttons = 'A'}, 4, 40)
      CAP.when({'AttackAirN'}, 17, {cy = -127}, 4, 40)
      CAP.wait(100)
    end)

    clip('fair_spike', {x1 = R - 30, x2 = R - 17, camx = R - 22, camz = 55, camy = 13, camiy = 10}, function()
      CAP.wait(10)
      CAP.tap({buttons = 'X'}, 3)
      CAP.when({'JumpF', 'JumpB'}, 8, {buttons = 'A', x = 127}, 3, 40)
      CAP.wait(90)
    end)

    clip('grab', {x2 = 9, camx = 8, camz = 50, camy = 9, camiy = 6}, function()
      CAP.wait(12)
      CAP.tap({buttons = 'Z'}, 2)
      CAP.when({'CatchWait'}, 14, {x = 127}, 2, 60)
      CAP.wait(70)
    end)

    clip('grab_b', {x2 = 9, camx = 8, camz = 50, camy = 9, camiy = 6}, function()
      CAP.wait(12)
      CAP.tap({buttons = 'Z'}, 2)
      CAP.when({'CatchWait'}, 14, {x = -127}, 2, 60)
      CAP.wait(70)
    end)

    clip('fsmash', {x1 = R - 34, x2 = R - 20, pct = 130, camx = R - 22, camz = 85, camy = 16, camiy = 10}, function()
      CAP.wait(10)
      CAP.tap({cx = 127}, 38); CAP.wait(100)
    end)

    CAP.log('DONE')
  end)
  if not ok then CAP.log('FAIL ' .. tostring(why)) end
  gd.quit()
end)
