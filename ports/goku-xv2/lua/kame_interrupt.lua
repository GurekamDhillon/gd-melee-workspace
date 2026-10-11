-- Muted realtime MELEE_AUDIO_DUMP probe; use kame_run.py without --turbo.
-- CFG.act = hit/store/roll/spot/fire; the late hum retrigger leaves a long tail to detect.
local C = CFG or {}
local act = C.act or 'store'
local direct_pending = false
function on_tick()
  if direct_pending and gd.paused() and gd.player(1).motion_name == 'EscapeN' then
    direct_pending = false; gd.resume()
  end
end
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    gd.teleport(1, 0, 0); gd.teleport(2, 60, 0)
    gd.set_percent(1, 0); gd.set_percent(2, 0); gd.wait(30)
    gd.log('KAMEAUDIO start=' .. gd.match().frame)
    gd.input(1, {buttons = 'B'}, 2); gd.wait(560)
    assert(gd.player(1).motion_name == 'KameCharge', 'not charging')
    gd.log('KAMEHUM before=' .. gd.match().frame .. ' act=' .. act .. ' state=' .. gd.player(1).motion_name)
    if act == 'hit' then
      assert(gd.hit(1, {damage = 8, angle = 45, kbg = 60, bkb = 40, from = 2}), 'hit refused')
    elseif act == 'store' then gd.input(1, {buttons = 'L'}, 2)
    elseif act == 'roll' then gd.input(1, {x = 127}, 3)
    elseif act == 'spot' then
      -- Goku uses ftCo_8009917C, which cancels only sideways. Spotdodge follows
      -- the native shield-store path; do not silently add a new move cancel.
      gd.input(1, {buttons = 'L'}, 2)
      assert(gd.wait_until(function() return gd.player(1).motion_name:find('KameStore') end, 12), 'no store before spotdodge')
      gd.log('KAMEHUM stored=' .. gd.match().frame .. ' state=' .. gd.player(1).motion_name)
      assert(gd.wait_until(function() return not gd.player(1).motion_name:find('KameStore') end, 90), 'store did not finish')
      gd.input(1, {buttons = 'L'}, 60); gd.wait(5)
      gd.input(1, {buttons = 'L', y = -127}, 8)
      assert(gd.wait_until(function() return gd.player(1).motion_name == 'EscapeN' end, 15), 'no shield spotdodge')
    elseif act == 'spot_direct' then
      -- Direct LAB transition also exercises EscapeN as the first state after charge.
      local id
      for _, row in ipairs(gd.motion_list(1)) do if row.name == 'EscapeN' then id = row.id end end
      direct_pending = true
      assert(id and gd.set_motion(1, id, 1), 'EscapeN preview refused')
      gd.wait(1)
    elseif act == 'fire' then gd.input(1, {buttons = 'B'}, 2)
    else error('unknown act ' .. act) end
    assert(gd.wait_until(function() return gd.player(1).motion_name ~= 'KameCharge' end, 12), 'charge did not exit')
    local m = gd.player(1).motion_name
    gd.log('KAMEAUDIO fire=' .. gd.match().frame .. ' state=' .. m)
    gd.log('KAMEHUM exit=' .. gd.match().frame .. ' act=' .. act .. ' state=' .. m)
    if act == 'hit' then assert(m:find('Damage'), 'no damage state: ' .. m)
    elseif act == 'store' then assert(m:find('KameStore'), 'no store: ' .. m)
    elseif act == 'roll' then assert(m == 'EscapeF' or m == 'EscapeB', 'no roll: ' .. m)
    elseif act == 'spot' or act == 'spot_direct' then assert(m == 'EscapeN', 'no spotdodge: ' .. m)
    else assert(m == 'KameMax', 'no normal Max fire: ' .. m) end
    gd.wait(180)
    gd.log('KAMEHUM PASS act=' .. act)
  end)
  if not ok then gd.log('KAMEHUM FAIL ' .. tostring(why)) end
  gd.quit()
end)
