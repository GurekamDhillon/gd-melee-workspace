-- Kamehameha: tap, charged, max (Super needs ki 100 and a full charge). Frames 1-based per clip; 6 s of footage each at most.
gd.run(function()
  local ok, why = pcall(function()
    CAP.burners()
    CAP.setup(38, 18, 12, 72, 40)
    -- Neutral B: B once starts the self-running charge (60 units, about 130 frames to full); B again fires the level reached.
    local function kame(label, wait2, ki, tail)
      CAP.reset{ki = ki, camx = 18, camz = 72, camy = 12, camiy = 8}
      CAP.clip(label); CAP.rec(true)
      gd.input(1, {buttons = 'B'}, 2)
      CAP.wait(wait2)
      gd.input(1, {buttons = 'B'}, 2)
      CAP.wait(tail or 90)
      CAP.endclip()
    end
    kame('kame_tap', 14, 0, 80)
    kame('kame_charged', 90, 0, 90)
    kame('kame_max', 140, 100, 110)
    CAP.log('DONE')
  end)
  if not ok then CAP.log('FAIL ' .. tostring(why)) end
  gd.quit()
end)
