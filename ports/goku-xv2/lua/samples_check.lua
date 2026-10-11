-- Phase 2 gate: every HB-SAMPLE move connects with a Mario dummy (turbo ok, combo package). Tag: SAMPLECHECK.
-- Each move is tried at several distances; it passes when P2's percent rises. Also: the jab string takes its routes (combo links), no Lua faults.
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function name() return tostring(gd.player(1).motion_name) end
    local function tp(p, x, y) for i = 1, 40 do if pcall(gd.teleport, p, x, y) then return end gd.wait(20) end error('teleport') end
    local function reset(dist, y, ki)
      gd.input(1, {}, 1); gd.wait(3)
      tp(1, 0, y or 0); tp(2, dist, 0)
      gd.set_percent(1, 0); gd.set_percent(2, 0)
      gd.combo_ki(1, ki or 0)
      gd.wait(45)
      tp(1, 0, y or 0); tp(2, dist, 0); gd.set_percent(2, 0); gd.wait(3)
    end
    local function nofault() local l = assert(gd.fighter_lua(1)); assert(l.faults == 0, 'Lua fault ' .. tostring(l.last_fault)) end
    local results, miss = {}, {}
    local function try(label, setup, input, frames, watch, dists)
      for _, d in ipairs(dists or {7, 11, 15}) do
        reset(d, setup.y, setup.ki)
        if setup.pre then setup.pre() end
        gd.input(1, input, frames)
        local before, seen, links0 = gd.player(2).percent, {}, (gd.combo(1) or {}).taken or 0
        for t = 1, watch do
          gd.wait(1); nofault()
          seen[name()] = true
          if gd.player(2).percent > before + 0.01 then
            local dmg = gd.player(2).percent - before
            local c = gd.combo(1) or {}
            gd.log(string.format('SAMPLECHECK %-12s hit at dist %d: +%.1f%% (P2 %s), links %s', label, d, dmg, tostring(gd.player(2).motion_name), tostring((c.taken or 0) - links0)))
            results[label] = (results[label] or 0) + 1
            return true
          end
        end
      end
      gd.log('SAMPLECHECK ' .. label .. ' MISS at every distance')
      miss[#miss + 1] = label
      return false
    end
    local ground = {}
    try('jab1', ground, {buttons = 'A'}, 2, 40)
    try('ftilt', ground, {x = 60, buttons = 'A'}, 2, 50)
    try('utilt', ground, {y = 60, buttons = 'A'}, 2, 50)
    try('dtilt', ground, {y = -60, buttons = 'A'}, 2, 50)
    try('dashattack', ground, {x = 127, buttons = 'A'}, 20, 70, {14, 20, 26})
    try('fsmash', ground, {cx = 127}, 2, 80)
    try('usmash', ground, {cy = 127}, 2, 80)
    try('dsmash', ground, {cy = -127}, 2, 80)
    try('grab', ground, {buttons = 'Z'}, 2, 40)
    try('rush', ground, {x = 127, buttons = 'B'}, 2, 90, {10, 20, 30})
    try('homing', {ki = 60, pre = function() gd.input(1, {buttons = 'L'}, 14); gd.wait(12) end}, {buttons = 'L+B'}, 2, 90, {10, 20, 30})
    local air = {y = 7}
    local function ja(btn) return function() gd.input(1, {buttons = 'X'}, 3); gd.wait(6) end end
    try('nair', {y = 0, pre = ja()}, {buttons = 'A'}, 2, 70)
    try('fair', {y = 0, pre = ja()}, {cx = 127}, 2, 60)
    try('uair', {y = 0, pre = ja()}, {cy = 127}, 2, 60)
    try('dair', {y = 0, pre = ja()}, {cy = -127}, 2, 60, {3, 6, 9})
    -- the jab string: A pressed at the XV2 rhythm, on hit the routes link
    reset(8, 0, 0)
    local links = 0
    for i = 1, 5 do
      gd.input(1, {buttons = 'A'}, 2); gd.wait(14)
    end
    local c = gd.combo(1) or {}
    gd.log(string.format('SAMPLECHECK jabstring: links taken %s last route %s, P2 %.1f%%', tostring(c.taken), tostring(c.last_name), gd.player(2).percent))
    nofault()
    if #miss > 0 then error('no hit: ' .. table.concat(miss, ' ')) end
    gd.log('SAMPLECHECK PASS')
  end)
  if not ok then gd.log('SAMPLECHECK FAIL ' .. tostring(why)) end
  gd.quit()
end)
