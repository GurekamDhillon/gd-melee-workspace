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
      -- the tap and the charged shot are measured back to back at each distance with the dummy held there until the release (the damage is staled by every earlier use of the
      -- move, so only a pair taken together says anything about the charge); the best pair judges the charge
      local function shot(d, hold)
        reset(d, 0, 0)
        local g0 = gd.player(1)
        local face = (g0.facing or 1) >= 0 and 1 or -1
        local before = gd.player(2).percent
        gd.input(1, {buttons = 'A', x = spec.x and spec.x * face or nil, y = spec.y}, hold)
        local frozen, last_af = 0, nil
        for t = 1, 150 do
          gd.wait(1); nofault()
          local p = gd.player(1)
          if gd.player(2).percent <= before + 0.01 and t <= math.max(hold, 10) then pcall(gd.teleport, 2, p.x + face * d, 0) end   -- never re-pin on the hit frame: a teleport cancels the knockback
          if hold > 2 and t > 25 and t < 60 and tostring(p.motion_name):find('Attack') then
            if last_af and math.abs((p.anim_frame or 0) - last_af) < 0.01 then frozen = frozen + 1 end
            last_af = p.anim_frame
          end
          if gd.player(2).percent > before + 0.01 then
            local dmg_hit, x_hit, y_hit = gd.player(2).percent - before, gd.player(2).x, gd.player(2).y
            gd.wait(26)   -- hitlag and the first frames of the launch: how far the dummy has been sent is the knockback (charged damage feeds the knockback formula)
            local q = gd.player(2)
            return dmg_hit, frozen, math.sqrt((q.x - x_hit) ^ 2 + (q.y - y_hit) ^ 2)
          end
        end
        return nil, frozen
      end
      local best, held = nil, 0
      for _, d in ipairs(dists) do
        local tap, _, tap_far = shot(d, 2)
        local chg, frozen, chg_far = shot(d, 70)
        held = math.max(held, frozen)
        if tap and chg and (not best or tap > best[1]) then best = {tap, chg, tap_far, chg_far} end   -- the distance with the full hit (most damage): that is the one that must launch
      end
      gd.log(string.format('SAMPLECHECK smash charge %s: tap %s%%, charged %s%%, anim held %s frames, dummy sent %.1f (tap) vs %.1f (charged) units in 26 frames', label, tostring(best and best[1]), tostring(best and best[2]), tostring(held), best and best[3] or 0, best and best[4] or 0))
      if best and best[3] < 5 then error(label .. ' smash is a PHANTOM hit on the dummy: ' .. string.format('%.1f%% damage but the dummy was sent only %.1f units (a hitbox that only grazes the hurtbox does damage and no knockback)', best[1], best[3])) end
      if best and best[4] < best[3] * 1.1 then error(label .. ' charged smash does not send the dummy further: ' .. best[3] .. ' -> ' .. best[4]) end
      if not best then error(label .. ' smash did not connect tapped and charged at the same distance') end
      if best[2] < best[1] * 1.15 then error(label .. ' smash damage does not scale with the charge: ' .. best[1] .. ' -> ' .. best[2]) end
      if held < 15 then error(label .. ' smash animation did not hold while charging') end
    end
    smash('fsmash', {x = 127}, {7, 9, 11})
    smash('usmash', {y = 127}, {2, 4, 6, 8, 10})
    smash('dsmash', {y = -127}, {7, 9, 11})
    -- Spikes (owner 2026-10-11). fair = Mario's AttackAirF structure (two spheres, five frames, both 280); dair = a small tip spike for three frames, sourspot (angle 40, low knockback)
    -- on the legs and on the tip afterwards. Each probe pins the dummy's centre on a chosen hitbox of the move (read from gd.hitboxes) while the move runs, then measures where the
    -- dummy goes over the next 24 frames (hitlag included): a spike goes down, a sourspot forward and up.
    do
      local function aerial_probe(label, spec, hb_id, only_when_id0_off, away_from)
        reset(70, 90, 0, 0)
        tp(2, -200, 0)
        local g0 = gd.player(1)
        local face = (g0.facing or 1) >= 0 and 1 or -1
        gd.input(1, spec, 2)
        local before = gd.player(2).percent
        local hit_at, y0, x0, peak, ytrace = nil, nil, nil, 0, {}
        for t = 1, 60 do
          gd.wait(1); nofault()
          if not hit_at and gd.player(2).percent > before + 0.01 then hit_at, y0, x0 = t, gd.player(2).y, gd.player(2).x end   -- see the hit BEFORE re-pinning: a teleport cancels the knockback
          if not hit_at then
            local okh, hbs = pcall(gd.hitboxes, 1)
            local want, spike, ref = nil, false, nil
            if okh and type(hbs) == 'table' then
              for _, h in ipairs(hbs) do
                if h.id == 0 then spike = true end
                if h.id == hb_id then want = h end
                
              end
              if only_when_id0_off and spike then want = nil end
            end
            if want then
              local px, py = want.x, want.y
              if away_from then py = py + away_from end   -- stand this far above the sphere's centre: clear of the spike sphere at the foot tip
              pcall(gd.teleport, 2, px, py - 8)
            end
          end
          if not hit_at and gd.player(2).percent > before + 0.01 then
            hit_at, y0, x0 = t, gd.player(2).y, gd.player(2).x
          end
          if hit_at then peak = math.max(peak, gd.player(2).y - y0) if (t - hit_at) % 3 == 0 then ytrace[#ytrace + 1] = string.format('%.1f/%.1f', gd.player(2).y - y0, (gd.player(2).x - x0) * face) end end
          if hit_at and t >= hit_at + 24 then break end
        end
        if not hit_at then gd.log('SAMPLECHECK ' .. label .. ': no hit') return nil end
        local dy, dx = gd.player(2).y - y0, (gd.player(2).x - x0) * face
        local spiked = peak < 0.5 and dy < -1.5   -- a meteor never rises; a sourspot (angle 40) climbs before it falls
        gd.log(string.format('SAMPLECHECK %s: hit at frame %d, then dy %.1f dx %.1f, rose at most %.1f (%s) [dy/dx every 3 frames: %s]', label, hit_at, dy, dx, peak, spiked and 'spike' or 'sideways / up', table.concat(ytrace, ' ')))
        return spiked and -10 or 10, dx
      end
      local dy
      dy = aerial_probe('fair fist (slot 0)', {buttons = 'A', x = 127}, 0, false)
      assert(dy and dy < -1.5, 'a fair hit on the fist spikes (angle 280)')
      dy = aerial_probe('fair forearm (slot 1)', {buttons = 'A', x = 127}, 1, false)
      assert(dy and dy < -1.5, 'a fair hit on the forearm also spikes: Marios fair has no sourspot')
      dy = aerial_probe('dair tip, spike frames (slot 0)', {buttons = 'A', y = -127}, 0, false)
      assert(dy and dy < -1.5, 'a dair hit on the foot tip at the spike frames spikes (angle 290)')
      dy = aerial_probe('dair upper leg, spike frames (slot 2, clear of the tip)', {buttons = 'A', y = -127}, 2, false, 9)
      assert(dy and dy > -1.5, 'a dair hit on the upper leg (sourspot) must not spike: dy ' .. tostring(dy))
      dy = aerial_probe('dair tip, after the spike frames (slot 3)', {buttons = 'A', y = -127}, 3, true)
      assert(dy and dy > -1.5, 'a late dair hit on the tip (sourspot) must not spike: dy ' .. tostring(dy))
    end
    -- The grab family (owner 2026-10-11, CROSS-PORT): Catch / CatchDash / CatchWait / CatchAttack / ThrowB / ThrowLw are Captain Falcon's, ThrowHi is Marth's (tentative), ThrowF is
    -- Mewtwo's (five ki blasts). References are retail numbers measured with lua/throw_probe.lua against this same Mario dummy: Falcon pummel 3.0, bthrow 9.0, dthrow 7.0,
    -- Marth uthrow 4.0, Mewtwo fthrow 9.5 (5.0 release + five 0.9 shadow-ball hits, spawns 7 frames apart). Each: grab connects, the move's damage is close to the reference,
    -- the victim is released (no longer held or thrown) and Goku is actionable again.
    do
      local function face_dummy()
        tp(1, 0, 0); tp(2, 30, 0); gd.set_percent(1, 0); gd.set_percent(2, 0); gd.wait(40)
        gd.input(1, {x = 60}, 3); gd.wait(30)
        tp(1, 0, 0); tp(2, 7, 0); gd.wait(3)
        local face = (gd.player(1).facing or 1) >= 0 and 1 or -1
        tp(2, 7 * face, 0); gd.wait(2)
        return face
      end
      local function grab_dummy(face)
        gd.input(1, {buttons = 'Z'}, 2)
        local caught
        for i = 1, 60 do gd.wait(1) if name() == 'CatchWait' then caught = i break end end
        assert(caught, 'grab: no catch (' .. name() .. ')')
        gd.wait(8)
        return caught
      end
      local function release_check(label, free_budget)
        local free_at
        for t = 1, 160 do
          gd.wait(1); nofault()
          local n2 = tostring(gd.player(2).motion_name)
          if not free_at and name() == 'Wait' and not n2:find('Thrown') and not n2:find('Catch') and not n2:find('Capture') then free_at = t end
          if free_at and t > free_at + 10 then break end
        end
        assert(free_at and free_at <= free_budget, label .. ': Goku or the victim was not released in time: ' .. tostring(free_at))
        return free_at
      end
      -- pummel: A in the hold = Falcon's CatchAttack, 3% a hit
      do
        local face = face_dummy()
        local c = grab_dummy(face)
        local p0 = gd.player(2).percent or 0
        gd.input(1, {buttons = 'A'}, 3)
        local seen_pummel = false
        for t = 1, 40 do gd.wait(1) if name() == 'CatchAttack' then seen_pummel = true end end
        local dmg = (gd.player(2).percent or 0) - p0
        gd.log(string.format('SAMPLECHECK pummel: CatchAttack %s, +%.1f%% (Falcon 3.0), grab connected after %d frames', tostring(seen_pummel), dmg, c))
        assert(seen_pummel and dmg >= 2.0 and dmg <= 4.0, 'pummel is not Falcon CatchAttack damage: ' .. dmg)
        gd.input(1, {x = 127 * face}, 3)   -- then out of it with a forward throw
        release_check('pummel', 140)
        gd.wait(30)
      end
      local cases = {
        {'fthrow', 'ThrowF', function(f) return {x = 127 * f} end, 9.5, 2.0, 5},   -- release lowered to 1 (a Geno article hit adds 1: 1.8 a ball, not 0.9): 1.2 + 5 x 1.8
        {'bthrow', 'ThrowB', function(f) return {x = -127 * f} end, 9.0, 2.0, 0},
        {'dthrow', 'ThrowLw', function(f) return {y = -127} end, 7.0, 2.0, 0},
        {'uthrow', 'ThrowHi', function(f) return {y = 127} end, 4.0, 2.0, 0},
      }
      for _, cs in ipairs(cases) do
        local label, motion, stick, ref, tol, want_balls = cs[1], cs[2], cs[3], cs[4], cs[5], cs[6]
        local face = face_dummy()
        grab_dummy(face)
        local p0 = gd.player(2).percent or 0
        gd.input(1, stick(face), 3)
        local steps, spawns, lastp, seen_throw, v_dx0, v_dxe = 0, 0, p0, false, nil, nil
        local f_at
        for t = 1, 140 do
          gd.wait(1); nofault()
          if name() == motion then seen_throw = true end
          local pp = gd.player(2).percent or 0
          if pp ~= lastp then steps = steps + 1 lastp = pp end
          for _, it in ipairs(gd.items() or {}) do if (it.frame_alive or 0) == 2 and it.owner_port == 1 then spawns = spawns + 1 end end
          if seen_throw and not f_at and name() == 'Wait' then f_at = t end
          if f_at and t > f_at + 12 then break end
        end
        local total = (gd.player(2).percent or 0) - p0
        local g, v = gd.player(1), gd.player(2)
        gd.log(string.format('SAMPLECHECK %s: %s seen=%s, %d damage steps, %d ki blasts, total %.1f%% (reference %.1f%%), Wait again at %s, victim now %s at dx %.1f',
          label, motion, tostring(seen_throw), steps, spawns, total, ref, tostring(f_at), tostring(v.motion_name), (v.x - g.x) * face))
        assert(seen_throw, label .. ': the throw state never ran')
        assert(math.abs(total - ref) <= tol, label .. ' total damage is not close to the source thrower: ' .. total .. ' vs ' .. ref)
        if want_balls > 0 then assert(steps >= want_balls + 1, label .. ' did not release ' .. want_balls .. ' ki blasts that hit (' .. steps .. ' damage steps)') end
        assert(f_at and f_at <= 110, label .. ': Goku did not get actionable after the throw: ' .. tostring(f_at))
        gd.wait(45)
        local n2 = tostring(gd.player(2).motion_name)
        assert(not n2:find('Thrown') and not n2:find('Catch') and not n2:find('Capture'), label .. ': the victim is still held (' .. n2 .. ')')
      end
      -- rewind across a throw (the victim rides the ported grab anchor; the ki blasts are articles): the replay must match to the byte
      for _, rc in ipairs({{'fthrow', function(f) return {x = 127 * f} end}, {'bthrow', function(f) return {x = -127 * f} end}}) do
        local face = face_dummy()
        grab_dummy(face)
        gd.input(1, rc[2](face), 3)
        gd.wait(22)
        assert(gd.rewind_test(100, true), rc[1] .. ': rewind refused')
        local done = false
        for _ = 1, 400 do
          gd.wait(1)
          local r = gd.rewind_test_result()
          if r and r.phase == 0 and r.pass ~= nil then
            gd.log(string.format('SAMPLECHECK rewind %s pass=%s diff_compared=%s', rc[1], tostring(r.pass), tostring(r.diff_compared)))
            assert(r.pass and r.diff_compared == 0, rc[1] .. ': rewind differs: ' .. tostring(r.text))
            done = true
            break
          end
        end
        assert(done, rc[1] .. ': rewind never finished')
        gd.wait(80)
      end
      -- dash grab: a run into Z connects
      do
        tp(1, 0, 0); tp(2, 40, 0); gd.set_percent(2, 0); gd.wait(40)
        gd.input(1, {x = 60}, 3); gd.wait(25)
        tp(1, -10, 0); tp(2, 14, 0); gd.wait(2)
        local face = (gd.player(1).facing or 1) >= 0 and 1 or -1
        gd.input(1, {x = 127 * face}, 18)
        gd.wait(10)
        gd.input(1, {x = 127 * face, buttons = 'Z'}, 2)
        local got
        for i = 1, 60 do gd.wait(1) if name() == 'CatchWait' then got = i break end end
        gd.log('SAMPLECHECK dash_grab: ' .. (got and ('grabbed after ' .. got .. ' frames') or ('no grab, state ' .. name())))
        assert(got, 'the dash grab did not connect')
        gd.wait(60)
        gd.input(1, {x = 127 * face}, 3); gd.wait(120)
      end
    end
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
