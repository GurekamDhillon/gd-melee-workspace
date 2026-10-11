-- Audio capture scenario: B once, charge for `hold` frames (default 700), B again to fire, `tail` frames more (default 200). No screenshots. Run with the audio dump:
--   KAME_AUDIO_DUMP=<wav> python ports/goku-xv2/tools/kame_run.py kame_audio KAMEAUDIO --cfg hold=1500      (kame_run.py sets MELEE_VOLUME=0: nothing is played aloud)
-- The WAV is the engine's final mix at full scale; tools/kame_audio_check.py reads it with the log. Prints "KAMEAUDIO fire=<frame>" at the firing press.
local C = CFG or {}
local HOLD = tonumber(C.hold or 700)
local TAIL = tonumber(C.tail or 200)
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    gd.teleport(1, 0, 0); gd.teleport(2, 60, 0); gd.set_percent(1, 0); gd.set_percent(2, 0); gd.wait(30)
    if C.ki and gd.combo_ki then gd.combo_ki(1, tonumber(C.ki)) end
    gd.log('KAMEAUDIO start=' .. tostring(gd.match().frame))
    gd.input(1, {buttons = 'B'}, 2)
    gd.wait(HOLD)
    if C.act ~= 'none' then gd.input(1, {buttons = C.act or 'B'}, 2) end
    gd.log('KAMEAUDIO fire=' .. tostring(gd.match().frame) .. ' state=' .. tostring(gd.player(1).motion_name))
    gd.wait(TAIL)
    gd.log('KAMEAUDIO end=' .. tostring(gd.match().frame) .. ' state=' .. tostring(gd.player(1).motion_name))
  end)
  if not ok then gd.log('KAMEAUDIO FAIL ' .. tostring(why)) end
  gd.quit()
end)
