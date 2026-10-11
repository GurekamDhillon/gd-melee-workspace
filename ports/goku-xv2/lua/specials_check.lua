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
    local function reset(k)
      gd.input(1, {}, 1); gd.wait(3)
      gd.teleport(1, 0, 0); gd.teleport(2, 60, 0)
      gd.set_percent(1, 0); gd.set_percent(2, 0)
      gd.combo_ki(1, k or 0)
      gd.wait(40)
      gd.teleport(1, 0, 0); gd.teleport(2, 60, 0)
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

    -- 7c. Up B = flight (phase 3): takeoff from the ground, steering, 60 frames, then the special fall
    local function flight(label, k, stick, held, hi)
      reset(k)
      if hi then gd.teleport(1, 0, hi); gd.wait(3) end
      local g0 = gd.player(1)
      local face = (g0.facing or 1) >= 0 and 1 or -1
      gd.input(1, {y = 127, buttons = 'B'}, 2)
      local x0, y0, flown, fell, seen, lastfly, xe, ye = g0.x, g0.y, 0, nil, {}, nil, g0.x, g0.y
      local kb = ki()
      local trace, lastn = {}, nil
      for t = 1, 140 do
        gd.wait(1); nofault()
        local n = name()
        seen[n] = (seen[n] or 0) + 1
        if n ~= lastn then local st = gd.fighter_lua(1).state; trace[#trace + 1] = n .. '@' .. t .. '(age ' .. tostring(st.age) .. ' fly ' .. tostring(st.fly) .. ')'; lastn = n end
        if n:sub(1, 6) == 'Flight' then flown = flown + 1; lastfly = t end
        if t == 8 and stick then gd.input(1, {x = (stick.x or 0) * face, y = stick.y}, 70) end
        if held and t == held then gd.input(1, {buttons = 'B'}, 2) end
        local p = gd.player(1)
        if n:sub(1, 6) == 'Flight' then xe, ye = p.x, p.y end
        if (n == 'FallSpecial' or n == 'FallSpecialF' or n == 'FallSpecialB') and not fell then fell = t end
      end
      gd.log('SPECHECK trace ' .. table.concat(trace, ' '))
      gd.log(string.format('SPECHECK flight %s (facing %d): flight frames %d, dx %.1f dy %.1f, special fall from t%s, ki %.1f -> %.1f, states %s', label, face, flown, (xe - x0) * face, ye - y0, tostring(fell), kb, ki(),
        (function() local l = {} for k, v in pairs(seen) do l[#l + 1] = k .. ':' .. v end table.sort(l) return table.concat(l, ' ') end)()))
      return flown, (xe - x0) * face, ye - y0, fell, seen
    end
    local bads = {}
    local function chk(c, m) if not c then bads[#bads + 1] = m; gd.log('SPECHECK flightcheck FAIL ' .. m) end end
    local fl, dx, dy, fell = flight('up', 50, {y = 127, x = 0})
    chk(fl >= 56 and fl <= 66, 'flight did not last about 60 frames: ' .. fl)
    chk(dy > 20, 'flight did not climb: ' .. dy)
    chk(fell, 'flight did not end in the special fall (helpless)')
    chk(math.abs((50 - ki()) - 10) < 0.5, 'flight cost is not 10 ki')
    local _, dxf, _, _, sf = flight('forward (air start)', 50, {x = 127, y = 0}, nil, 50)
    chk(dxf > 12 and (sf.FlightF or 0) > 5, 'forward steering failed: dx ' .. dxf)
    local _, dxb, _, _, sb = flight('back (air start)', 50, {x = -127, y = 0}, nil, 50)
    chk(dxb < -8 and (sb.FlightB or 0) > 5, 'back steering failed: dx ' .. dxb)
    local fe, _, _, felle = flight('early end (B)', 50, nil, 25)
    chk(fe < 40 and felle and felle < 45, 'B did not end the flight early: ' .. fe)
    local fw, _, dyw = flight('no ki', 0)
    chk(fw >= 18 and fw <= 28 and dyw < 25, 'the no-ki flight is not the weak short one: ' .. fw)
    gd.input(1, {}, 1); gd.wait(100)

    assert(#bads == 0, 'flight checks failed: ' .. table.concat(bads, '; '))
    -- 7d. the flight ends in the special fall beside a ledge and Goku catches it (retail's ledge snap on a special fall)
    local caught = false
    for _, pos in ipairs({{90, -8}, {92, -14}, {89, -4}}) do      -- the right ledge (x 85.6): Goku faces left, toward the stage, as retail's ledge snap wants
      if not caught then
        reset(50)
        gd.teleport(1, pos[1], pos[2]); gd.wait(2)
        gd.input(1, {y = 127, buttons = 'B'}, 2)
        local seen7 = {}
        for t = 1, 150 do
          gd.wait(1); nofault()
          seen7[name()] = true
          if t == 6 then gd.input(1, {x = -127, y = 0}, 4) end       -- drift toward the stage, then end the flight early with B
          if t == 14 then gd.input(1, {buttons = 'B'}, 2) end
          if name() == 'CliffCatch' or name() == 'CliffWait' then caught = true break end
        end
        local l7 = {}
        for k in pairs(seen7) do l7[#l7 + 1] = k end
        table.sort(l7)
        gd.log(string.format('SPECHECK ledge from (%d,%d): caught=%s states %s', pos[1], pos[2], tostring(caught), table.concat(l7, ',')))
      end
    end
    assert(caught, 'the special fall after flight did not catch the ledge from any start')
    gd.input(1, {}, 1); gd.wait(60)

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
