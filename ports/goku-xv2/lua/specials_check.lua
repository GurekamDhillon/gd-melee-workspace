-- Remake phase 1 special-input gates (headless, turbo ok; combo package, geno 11). Tag: SPECHECK.
-- Down B hold = ki charge (only while ki < 100), Down B tap = the vanish counter, Side B out of the shield = the homing dash strike (meter-costed),
-- Down B out of the shield = the vanish (needs ki), rewind exactness across the homing strike, no Lua faults.
-- Run: python ports/goku-xv2/tools/kame_run.py specials_check SPECHECK --turbo   (KAME_MODS = the combo package's mods)
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function name() return tostring(gd.player(1).motion_name) end
    local function ki() local c = gd.combo(1); return c and c.ki or -1 end
    local function tp(p, x, y)
      for i = 1, 80 do
        if pcall(gd.teleport, p, x, y) then return end
        gd.wait(30)
      end
      error('could not teleport port ' .. p)
    end
    local function reset(k)
      gd.input(1, {}, 1); gd.wait(3)
      tp(1, 0, 0); tp(2, 60, 0)
      gd.set_percent(1, 0); gd.set_percent(2, 0)
      gd.combo_ki(1, k or 0)
      gd.wait(40)
      tp(1, 0, 0); tp(2, 60, 0)
      gd.combo_ki(1, k or 0); gd.wait(2)
    end
    local function nofault()
      local lua = assert(gd.fighter_lua(1))
      assert(lua.faults == 0, 'Lua fault: ' .. tostring(lua.last_fault))
    end
    local function track(frames, set)
      local seen = {}
      for t = 1, frames do
        gd.wait(1)
        seen[name()] = (seen[name()] or 0) + 1
        nofault()
        if set then set(t) end
      end
      return seen
    end

    -- 1. Down B hold below 100 ki: Counter, then KiCharge from f12, the meter rises
    reset(0)
    gd.input(1, {y = -127, buttons = 'B'}, 90)
    local s1 = track(80)
    local k1 = ki()
    gd.log(string.format('SPECHECK kicharge: Counter %s KiCharge %s ki %.1f', tostring(s1.Counter), tostring(s1.KiCharge), k1))
    assert((s1.KiCharge or 0) > 30, 'Down B hold did not reach KiCharge')
    assert(k1 > 20, 'the meter did not rise while charging')
    gd.input(1, {}, 1); gd.wait(30)
    assert(name() ~= 'KiCharge', 'KiCharge did not end on release: ' .. name())

    -- 2. Down B hold at a full meter: the hold stays the vanish (no charge state)
    reset(100)
    gd.input(1, {y = -127, buttons = 'B'}, 60)
    local s2 = track(50)
    gd.log(string.format('SPECHECK kicharge_full: KiCharge %s Counter %s ki %.1f', tostring(s2.KiCharge), tostring(s2.Counter), ki()))
    assert((s2.KiCharge or 0) == 0, 'KiCharge entered at ki 100')
    gd.input(1, {}, 1); gd.wait(40)

    -- 3. charging stops by itself at 100 (start at 90, hold)
    reset(90)
    gd.input(1, {y = -127, buttons = 'B'}, 200)
    local s3 = track(150)
    gd.log(string.format('SPECHECK kicharge_cap: KiCharge frames %s ki %.1f', tostring(s3.KiCharge), ki()))
    assert(ki() >= 99.9 and ki() <= 100.01, 'meter ended at ' .. ki())
    assert(name() ~= 'KiCharge', 'still charging at a full meter')
    gd.input(1, {}, 1); gd.wait(20)

    -- 4. Down B tap: the vanish counter blink, not the charge
    reset(50)
    gd.input(1, {y = -127, buttons = 'B'}, 3)
    local s4 = track(60)
    gd.log(string.format('SPECHECK vanish_tap: Counter %s KiCharge %s', tostring(s4.Counter), tostring(s4.KiCharge)))
    assert((s4.Counter or 0) > 10 and (s4.KiCharge or 0) == 0, 'Down B tap is not the Counter blink')

    -- 5. shield + B (stick neutral) with 50 ki: Homing, the route spends 20
    reset(50)
    gd.input(1, {buttons = 'L'}, 14); gd.wait(12)
    assert(name() == 'Guard' or name() == 'GuardOn', 'no shield: ' .. name())
    local k0 = ki()
    gd.input(1, {buttons = 'L+B'}, 2)
    local s5 = track(80)
    local k5 = ki()
    gd.log(string.format('SPECHECK homing: Homing %s ki %.1f -> %.1f', tostring(s5.Homing), k0, k5))
    assert((s5.Homing or 0) >= 40, 'Side B out of the shield did not enter Homing')
    assert(math.abs((k0 - k5) - 20) < 0.5, 'homing cost is not 20 ki: ' .. (k0 - k5))
    gd.input(1, {}, 1); gd.wait(40)

    -- 6. the same input with too little ki does nothing
    reset(5)
    gd.input(1, {buttons = 'L'}, 14); gd.wait(12)
    gd.input(1, {buttons = 'L+B'}, 2)
    local s6 = track(40)
    gd.log(string.format('SPECHECK homing_broke: Homing %s ki %.1f', tostring(s6.Homing), ki()))
    assert((s6.Homing or 0) == 0 and math.abs(ki() - 5) < 0.5, 'Homing fired without the meter')
    gd.input(1, {}, 1); gd.wait(30)

    -- 7. shield + Down B is NOT a vanish any more (owner: too hard to input); shield + a stick direction alone stays a roll / spot dodge, never Homing
    reset(50)
    gd.input(1, {buttons = 'L'}, 14); gd.wait(12)
    gd.input(1, {buttons = 'L+B', y = -127}, 2)
    local s7 = track(40)
    assert((s7.Counter or 0) == 0 and (s7.Homing or 0) == 0, 'shield + Down B still fires something: Counter ' .. tostring(s7.Counter))
    gd.input(1, {}, 1); gd.wait(60)
    reset(50)
    gd.input(1, {buttons = 'L'}, 14); gd.wait(12)
    gd.input(1, {buttons = 'L', x = 127}, 3)
    local s8 = track(40)
    gd.log(string.format('SPECHECK roll: Homing %s EscapeF %s', tostring(s8.Homing), tostring(s8.EscapeF)))
    assert((s8.Homing or 0) == 0 and (s8.EscapeF or 0) > 5, 'shield + stick must roll, not Homing')
    gd.input(1, {}, 1); gd.wait(30)

    -- 7b. the blast input (D-pad Down; layout B maps Y to it) fires the KiBlast state for 5 ki, and nothing without the meter
    reset(50)
    gd.teleport(2, -70, 0); gd.wait(2)   -- the dummy behind him: a landed blast would earn +4 ki
    local kb0 = ki()
    gd.input(1, {buttons = 'DOWN'}, 2)
    local s9 = track(40)
    gd.log(string.format('SPECHECK kiblast: KiBlast %s ki %.1f -> %.1f', tostring(s9.KiBlast), kb0, ki()))
    assert((s9.KiBlast or 0) >= 15, 'the blast input did not enter KiBlast')
    assert(math.abs((kb0 - ki()) - 5) < 0.5, 'the ki blast cost is not 5: ' .. (kb0 - ki()))
    gd.input(1, {}, 1); gd.wait(30)
    reset(2)
    gd.input(1, {buttons = 'DOWN'}, 2)
    local s10 = track(30)
    assert((s10.KiBlast or 0) == 0, 'the ki blast fired without the meter')
    gd.input(1, {}, 1); gd.wait(20)

    -- 7c. Up B = flight (phase 4: ki-limited): takeoff from the ground, steering, a length that scales with the ki, no regen, the special fall, aerials out of the flight
    local bads = {}
    local function chk(c, m) if not c then bads[#bads + 1] = m; gd.log('SPECHECK flightcheck FAIL ' .. m) end end
    local function flight(label, k, stick, held, hi, atk, pin)
      reset(k)
      if hi then gd.teleport(1, 0, hi); gd.wait(3) end
      local g0 = gd.player(1)
      local face = (g0.facing or 1) >= 0 and 1 or -1
      gd.input(1, {y = 127, buttons = 'B'}, 2)
      local x0, y0, flown, fell, seen, xe, ye = g0.x, g0.y, 0, nil, {}, g0.x, g0.y
      local kb, kprev, regen, trace, lastn = ki(), ki(), false, {}, nil
      for t = 1, 200 do
        gd.wait(1); nofault()
        local n = name()
        seen[n] = (seen[n] or 0) + 1
        if n ~= lastn then trace[#trace + 1] = n .. '@' .. t; lastn = n end
        if n:sub(1, 6) == 'Flight' and #n <= 7 then
          flown = flown + 1
          local kk = ki()
          if kk > kprev + 0.02 then regen = true end
          kprev = kk
        end
        if t == 8 and stick then gd.input(1, {x = (stick.x or 0) * face, y = stick.y}, stick.n or 150) end
        if held and t == held then gd.input(1, {buttons = 'B'}, 2) end
        if atk and t == atk.t then gd.input(1, {buttons = 'A', x = (atk.x or 0) * face, y = atk.y}, 2) end
        if pin then local g = gd.player(1); pcall(gd.teleport, 2, g.x + face * pin[1], g.y + pin[2]) end
        local p = gd.player(1)
        if n:sub(1, 6) == 'Flight' and #n <= 7 then xe, ye = p.x, p.y end
        if (n == 'FallSpecial' or n == 'FallSpecialF' or n == 'FallSpecialB') and not fell then fell = t end
        if n == 'Wait' and t > 20 then break end
      end
      local l = {}
      for kx, v in pairs(seen) do l[#l + 1] = kx .. ':' .. v end
      table.sort(l)
      gd.log(string.format('SPECHECK flight %s (facing %d): flight frames %d, dx %.1f dy %.1f, special fall from t%s, ki %.1f -> %.1f regen=%s states %s', label, face, flown,
        (xe - x0) * face, ye - y0, tostring(fell), kb, ki(), tostring(regen), table.concat(l, ' ')))
      return {frames = flown, dx = (xe - x0) * face, dy = ye - y0, fell = fell, seen = seen, regen = regen, kend = ki(), kstart = kb, trace = trace}
    end
    local f100 = flight('ki 100 (diagonal, so the top blast zone stays out of it)', 100, {y = 90, x = 90})
    chk(f100.frames >= 112 and f100.frames <= 126, 'ki 100 did not fly about 120 frames (2 s): ' .. f100.frames)
    chk(f100.dy > 100 and f100.dx > 100, 'ki 100 flight did not cover about 135 units each way: ' .. f100.dx .. ' ' .. f100.dy)
    chk(f100.fell, 'ki 100 flight did not end in the special fall')
    chk(f100.kend < 1.5, 'the flight did not run the ki down to 0: ' .. f100.kend)
    chk(not f100.regen, 'ki came back during the flight')
    local f50 = flight('ki 50', 50, {y = 127, x = 0})
    chk(f50.frames >= 54 and f50.frames <= 66 and f50.dy > 75, 'ki 50 did not fly about 60 frames and ~96 units: ' .. f50.frames .. ' ' .. f50.dy)
    chk(f50.fell and f50.kend < 1.5, 'ki 50 flight did not end at 0 ki in the special fall')
    local f20 = flight('ki 20 (the minimum)', 20, {y = 127, x = 0})
    chk(f20.frames >= 20 and f20.frames <= 28 and f20.kend < 1.5 and f20.dy > 30, 'ki 20 is not a 24-frame powered flight: ' .. f20.frames)
    local f10 = flight('ki 10 (below the minimum: weak)', 10, {y = 127, x = 0})
    chk(f10.frames >= 18 and f10.frames <= 26 and math.abs(f10.kend - 10) < 0.5, 'ki 10 is not the weak free flight: ' .. f10.frames)
    local ff = flight('forward (air start)', 30, {x = 127, y = 0, n = 34}, nil, 50)
    chk(ff.dx > 25 and (ff.seen.FlightF or 0) > 5, 'forward steering failed: dx ' .. ff.dx)
    local fb = flight('back (air start)', 30, {x = -127, y = 0, n = 34}, nil, 50)
    chk(fb.dx < -25 and (fb.seen.FlightB or 0) > 5, 'back steering failed: dx ' .. fb.dx)
    local fe = flight('early end (B)', 100, nil, 25)
    chk(fe.frames < 40 and fe.fell and fe.fell < 45 and fe.kend > 100 - 40 * 0.84, 'B did not end the flight early: ' .. fe.frames)
    -- flight -> fair that hits: normal air control afterwards (no special fall)
    local fh = flight('A+forward -> fair, dummy in reach', 100, {x = 0, y = 0}, nil, 100, {t = 14, x = 127, y = 0}, {6, 4})
    chk((fh.seen.FlightFair or 0) > 10, 'A + forward out of the flight did not enter FlightFair')
    chk(not fh.fell, 'a connected flight aerial ended in the special fall')
    gd.log('SPECHECK flight hit trace: ' .. table.concat(fh.trace, ' '))
    -- flight -> fair that whiffs: the special fall when it ends
    local fm = flight('A+forward -> fair, whiff', 100, {x = 0, y = 0}, nil, 100, {t = 14, x = 127, y = 0}, nil)
    chk((fm.seen.FlightFair or 0) > 10, 'whiff case did not enter FlightFair')
    chk(fm.fell, 'a whiffed flight aerial did not end in the special fall')
    gd.log('SPECHECK flight whiff trace: ' .. table.concat(fm.trace, ' '))
    -- after a connected aerial he can act: a double jump
    reset(100)
    gd.teleport(1, 0, 100); gd.wait(3)
    local fc = (gd.player(1).facing or 1) >= 0 and 1 or -1
    gd.input(1, {y = 127, buttons = 'B'}, 2)
    local acted = false
    for t = 1, 140 do
      gd.wait(1); nofault()
      local g = gd.player(1)
      pcall(gd.teleport, 2, g.x + fc * 6, g.y + 4)
      if t == 8 then gd.input(1, {x = 0, y = 0}, 100) end
      if t == 14 then gd.input(1, {buttons = 'A', x = 127 * fc}, 2) end
      if t > 30 and (name() == 'Fall' or name() == 'FallAerial') then
        gd.input(1, {buttons = 'X'}, 3); gd.wait(4)
        if name():find('JumpAerial') then acted = true end
        break
      end
    end
    chk(acted, 'after a connected flight aerial Goku could not double jump (no air control)')
    gd.input(1, {}, 1); gd.wait(60)
    assert(#bads == 0, 'flight checks failed: ' .. table.concat(bads, '; '))

    -- 7d. the flight ends in the special fall beside a ledge and Goku catches it (retail's ledge snap on a special fall)
    local caught = false
    for _, pos in ipairs({{90, -8}, {92, -14}, {89, -4}}) do      -- the ledge in front of him (x +-85.6): he must face the stage for retail's ledge snap
      if not caught then
        reset(50)
        local fl = (gd.player(1).facing or 1) >= 0 and 1 or -1
        gd.teleport(1, -fl * pos[1], pos[2]); gd.wait(2)
        gd.input(1, {y = 127, buttons = 'B'}, 2)
        local seen7 = {}
        for t = 1, 150 do
          gd.wait(1); nofault()
          seen7[name()] = true
          if t == 6 then gd.input(1, {x = fl * 127, y = 0}, 4) end       -- drift toward the stage, then end the flight early with B
          if t == 14 then gd.input(1, {buttons = 'B'}, 2) end
          if name() == 'CliffCatch' or name() == 'CliffWait' then caught = true break end
        end
        local l7 = {}
        for k in pairs(seen7) do l7[#l7 + 1] = k end
        table.sort(l7)
        gd.log(string.format('SPECHECK ledge from (%d,%d) facing %d: caught=%s states %s', -fl * pos[1], pos[2], fl, tostring(caught), table.concat(l7, ',')))
      end
    end
    assert(caught, 'the special fall after flight did not catch the ledge from any start')
    gd.input(1, {}, 1); gd.wait(60)

    -- 7e. rolls are Instant Transmission (phase 4): the Mewtwo roll timing (37 frames, intangible f5-22, 52 units), a hidden gap, ends grounded and actionable
    local function roll(label, dir, spot)
      reset(0)
      local g0 = gd.player(1)
      local face = (g0.facing or 1) >= 0 and 1 or -1
      local x0 = g0.x
      local inp = {buttons = 'L'}
      if spot then inp.y = -127 else inp.x = 127 * dir * face end
      gd.input(1, inp, 4)
      local esc, intang, hid, first, actionable = 0, 0, 0, nil, nil
      for t = 1, 70 do
        gd.wait(1); nofault()
        local p = gd.player(1)
        local n = tostring(p.motion_name)
        if n:find('Escape') then
          esc = esc + 1
          first = first or t
          if (p.intangible or 0) > 0 or tostring(p.body_state) ~= 'normal' then intang = intang + 1 end
          if p.hidden then hid = hid + 1 end
        elseif first and not actionable and (n == 'Wait' or n:find('Walk') or n == 'Turn' or n == 'Guard' or n == 'GuardOn') then
          actionable = t
        end
      end
      local p = gd.player(1)
      local face_end = (p.facing or 1) >= 0 and 1 or -1
      gd.log(string.format('SPECHECK roll %s: escape frames %d, intangible %d, hidden %d, dx %.1f, actionable at t%s, airborne=%s, facing %d -> %d', label, esc, intang, hid, (p.x - x0) * face, tostring(actionable), tostring(p.airborne), face, face_end))
      return {esc = esc, intang = intang, hid = hid, dx = (p.x - x0) * face, actionable = actionable, air = p.airborne, flipped = face_end ~= face}
    end
    local rf = roll('forward', 1)
    chk(rf.esc >= 34 and rf.esc <= 40, 'roll is not the 37-frame Mewtwo timing: ' .. rf.esc)
    chk(rf.intang >= 15 and rf.intang <= 20, 'roll intangible frames are not the Mewtwo 16-18: ' .. rf.intang)
    chk(rf.hid >= 15 and rf.hid <= 20, 'roll is not invisible for the intangible gap: ' .. rf.hid)
    chk(math.abs(rf.dx - 27.3) < 3, 'roll distance is not 27.3 units: ' .. rf.dx)
    chk(rf.actionable and rf.actionable <= 45 and not rf.air, 'the roll does not end grounded and actionable at the Melee timing')
    chk(rf.flipped, 'a forward roll must end facing the other way (Melee: Mario and Mewtwo flip)')
    local rb = roll('back', -1)
    chk(not rb.flipped, 'a back roll must keep the facing')
    chk(math.abs(rb.dx + 27.3) < 3 and rb.hid >= 15, 'back roll is not a 27.3-unit teleport back: ' .. rb.dx)
    local rs = roll('spot dodge', 1, true)
    chk(rs.hid >= 10 and rs.intang >= 10 and math.abs(rs.dx) < 2, 'spot dodge is not an in-place vanish: hidden ' .. rs.hid .. ' dx ' .. rs.dx)
    chk(not rs.flipped, 'the spot dodge must keep the facing')
    assert(#bads == 0, 'roll checks failed: ' .. table.concat(bads, '; '))

    -- 8. rewind exactness across the homing strike
    reset(50)
    gd.input(1, {buttons = 'L'}, 14); gd.wait(12)
    gd.input(1, {buttons = 'L+B'}, 2); gd.wait(12)
    assert(gd.rewind_test(120, true), 'rewind refused')
    local done = false
    for i = 1, 400 do
      gd.wait(1)
      local r = gd.rewind_test_result()
      if r and r.phase == 0 and r.pass ~= nil then
        gd.log(string.format('SPECHECK rewind pass=%s diff_compared=%s', tostring(r.pass), tostring(r.diff_compared)))
        assert(r.pass and r.diff_compared == 0, 'rewind differs: ' .. tostring(r.text))
        done = true
        break
      end
    end
    assert(done, 'rewind never finished')
    nofault()
    gd.log('SPECHECK PASS')
  end)
  if not ok then gd.log('SPECHECK FAIL ' .. tostring(why)) end
  gd.quit()
end)
