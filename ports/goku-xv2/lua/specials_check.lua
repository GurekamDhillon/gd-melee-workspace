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

    -- 5. Side B out of the shield with 50 ki: Homing, the route spends 20
    reset(50)
    gd.input(1, {buttons = 'L'}, 14); gd.wait(12)
    assert(name() == 'Guard' or name() == 'GuardOn', 'no shield: ' .. name())
    local k0 = ki()
    gd.input(1, {buttons = 'L+B', x = 127}, 2)
    local s5 = track(80)
    local k5 = ki()
    gd.log(string.format('SPECHECK homing: Homing %s ki %.1f -> %.1f', tostring(s5.Homing), k0, k5))
    assert((s5.Homing or 0) >= 40, 'Side B out of the shield did not enter Homing')
    assert(math.abs((k0 - k5) - 20) < 0.5, 'homing cost is not 20 ki: ' .. (k0 - k5))
    gd.input(1, {}, 1); gd.wait(40)

    -- 6. the same input with too little ki does nothing
    reset(5)
    gd.input(1, {buttons = 'L'}, 14); gd.wait(12)
    gd.input(1, {buttons = 'L+B', x = 127}, 2)
    local s6 = track(40)
    gd.log(string.format('SPECHECK homing_broke: Homing %s ki %.1f', tostring(s6.Homing), ki()))
    assert((s6.Homing or 0) == 0 and math.abs(ki() - 5) < 0.5, 'Homing fired without the meter')
    gd.input(1, {}, 1); gd.wait(30)

    -- 7. Down B out of the shield (the vanish) with 50 ki: Counter; with 5 ki: nothing
    reset(50)
    gd.input(1, {buttons = 'L'}, 14); gd.wait(12)
    gd.input(1, {buttons = 'L+B', y = -127}, 2)
    local s7 = track(40)
    gd.log(string.format('SPECHECK guard_vanish: Counter %s', tostring(s7.Counter)))
    assert((s7.Counter or 0) > 10, 'Down B out of the shield did not vanish')
    gd.input(1, {}, 1); gd.wait(60)
    reset(5)
    gd.input(1, {buttons = 'L'}, 14); gd.wait(12)
    gd.input(1, {buttons = 'L+B', y = -127}, 2)
    local s8 = track(40)
    assert((s8.Counter or 0) == 0, 'the vanish fired with ki 5')
    gd.input(1, {}, 1); gd.wait(30)

    -- 8. rewind exactness across the homing strike
    reset(50)
    gd.input(1, {buttons = 'L'}, 14); gd.wait(12)
    gd.input(1, {buttons = 'L+B', x = 127}, 2); gd.wait(12)
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
