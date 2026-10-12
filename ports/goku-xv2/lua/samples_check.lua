-- Phase 2 gate: every HB-SAMPLE move connects with a Mario dummy (turbo ok, combo package). Tag: SAMPLECHECK.
-- Each move is tried at several distances; it passes when P2's percent rises. Also: the jab string takes its routes (combo links), no Lua faults.
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function name() return tostring(gd.player(1).motion_name) end
    local function tp(p, x, y) for i = 1, 40 do if pcall(gd.teleport, p, x, y) then return end gd.wait(20) end error('teleport') end
    local function reset(dist, y, ki, my)
      gd.input(1, {}, 1); gd.wait(3)
      tp(1, 0, y or 0); tp(2, dist, my or 0)
      gd.set_percent(1, 0); gd.set_percent(2, 0)
      gd.combo_ki(1, ki or 0)
      gd.wait(45)
      tp(1, 0, y or 0); tp(2, dist, my or 0); gd.set_percent(2, 0); gd.wait(3)
    end
    local function nofault() local l = assert(gd.fighter_lua(1)); assert(l.faults == 0, 'Lua fault ' .. tostring(l.last_fault)) end
    local results, miss = {}, {}
    local lastseen
    local function try(label, setup, input, frames, watch, dists)
      for _, d in ipairs(dists or {7, 11, 15}) do
        reset(d, setup.y, setup.ki, setup.my)
        if setup.pre then setup.pre() end
        gd.input(1, input, frames)
        local before, seen, links0 = gd.player(2).percent, {}, (gd.combo(1) or {}).taken or 0
        for t = 1, watch do
          gd.wait(1); nofault()
          if setup.pin then local g = gd.player(1); pcall(gd.teleport, 2, g.x + (setup.facing or 1) * d, g.y + setup.pin) end
          seen[name()] = true
          lastseen = seen
          if setup.grab and name() == 'CatchWait' then gd.log('SAMPLECHECK ' .. label .. ' grabbed at dist ' .. d) results[label] = 1 return true end
          if gd.player(2).percent > before + 0.01 then
            local dmg = gd.player(2).percent - before
            local c = gd.combo(1) or {}
            gd.log(string.format('SAMPLECHECK %-12s hit at dist %d: +%.1f%% (P2 %s), links %s', label, d, dmg, tostring(gd.player(2).motion_name), tostring((c.taken or 0) - links0)))
            results[label] = (results[label] or 0) + 1
            return true
          end
        end
      end
      local names = {}
      for k in pairs(lastseen or {}) do names[#names + 1] = k end
      table.sort(names)
      gd.log('SAMPLECHECK ' .. label .. ' MISS at every distance; motions seen: ' .. table.concat(names, ','))
      miss[#miss + 1] = label
      return false
    end
    local ground = {}
    try('jab1', ground, {buttons = 'A'}, 2, 40)
    try('ftilt', ground, {x = 60, buttons = 'A'}, 2, 50)
    try('utilt', ground, {y = 60, buttons = 'A'}, 2, 50, {2, 4, 7})
    try('dtilt', ground, {y = -60, buttons = 'A'}, 2, 50)
    try('dashattack', ground, {x = 127, buttons = 'A'}, 20, 70, {14, 20, 26})
    try('fsmash', ground, {cx = 127}, 2, 80)
    try('usmash', ground, {cy = 127}, 2, 80, {2, 4, 7})
    try('dsmash', ground, {cy = -127}, 2, 80)
    try('grab', {grab = true}, {buttons = 'Z'}, 2, 40, {5, 8, 11})
    try('rush', ground, {x = 127, buttons = 'B'}, 2, 90, {10, 20, 30})
    try('homing', {ki = 60, pre = function() gd.input(1, {buttons = 'L'}, 14); gd.wait(12) end}, {buttons = 'L+B'}, 2, 90, {10, 20, 30})
    -- aerials: Goku hangs high in the air (he falls slowly), the dummy is held at an offset from him every frame (pin = height offset, distance tried below)
    try('nair', {y = 40, my = 40, pin = 3}, {buttons = 'A'}, 2, 70, {3, 6, 9})
    try('fair', {y = 40, my = 40, pin = 4}, {cx = 127}, 2, 60, {5, 8, 11})
    try('uair', {y = 40, my = 50, pin = 11}, {cy = 127}, 2, 60, {0, 3, 6})
    try('dair', {y = 40, my = 36, pin = -4}, {cy = -127}, 2, 60, {0, 3, 6})
    -- smash charge (Melee's: hold A through the wind-up, up to 60 frames, damage x1.3671): a tapped smash against the same smash held 70 frames
    local function smash(label, spec, dists)
      local out = {}
      for _, hold in ipairs({2, 70}) do
        local got
        for _, d in ipairs(dists) do
          reset(d, 0, 0)
          local g0 = gd.player(1)
          local face = (g0.facing or 1) >= 0 and 1 or -1
          local before = gd.player(2).percent
          local inp = {buttons = 'A', x = spec.x and spec.x * face or nil, y = spec.y}
          gd.input(1, inp, hold)
          local frozen, last_af = 0, nil
          for t = 1, 150 do
            gd.wait(1); nofault()
            local p = gd.player(1)
            -- a charge lasts ~70 frames and the ECBs push the pair apart (Goku is built at 1.2, so further than before): hold the dummy at the tested distance until the release
            if hold > 2 and t <= hold then pcall(gd.teleport, 2, p.x + face * d, 0) end
            if hold > 2 and t > 25 and t < 60 and tostring(p.motion_name):find('Attack') then
              if last_af and math.abs((p.anim_frame or 0) - last_af) < 0.01 then frozen = frozen + 1 end
              last_af = p.anim_frame
            end
            if gd.player(2).percent > before + 0.01 then got = gd.player(2).percent - before break end
          end
          if not got and hold > 2 then local seen = {} gd.log(string.format('SAMPLECHECK smash %s charged miss at dist %d: P1 %s x%.1f, P2 %s x%.1f', label, d, tostring(gd.player(1).motion_name), gd.player(1).x, tostring(gd.player(2).motion_name), gd.player(2).x)) end
          if got then out.frozen = (out.frozen or 0) + frozen break end
        end
        out[hold] = got
      end
      gd.log(string.format('SAMPLECHECK smash charge %s: tap %s%%, charged %s%%, anim held %s frames', label, tostring(out[2]), tostring(out[70]), tostring(out.frozen)))
      if not (out[2] and out[70]) then error(label .. ' smash did not connect tapped or charged') end
      if out[70] < out[2] * 1.15 then error(label .. ' smash damage does not scale with the charge: ' .. out[2] .. ' -> ' .. out[70]) end
      if (out.frozen or 0) < 15 then error(label .. ' smash animation did not hold while charging') end
    end
    smash('fsmash', {x = 127}, {7, 9, 11})
    smash('usmash', {y = 127}, {2, 4, 6, 8, 10})
    smash('dsmash', {y = -127}, {7, 9, 11})
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
