-- Kamehameha gates (headless, turbo ok): beam hits several times, damage/duration scale with charge, store/resume/instant-fire rules,
-- the air hover, rewind exactness. Tag: KAMECHK. Run: python ports/goku-xv2/tools/kame_run.py kame_check KAMECHK --turbo
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function reset(py, vx)
      vx = vx or 30
      gd.input(1, {}, 1); gd.wait(2)
      gd.teleport(1, 0, py or 0); gd.teleport(2, vx, 0)
      gd.set_percent(1, 0); gd.set_percent(2, 0); gd.wait(70)
      gd.teleport(1, 0, py or 0); gd.teleport(2, vx, 0); gd.set_percent(2, 0); gd.wait(3)
    end
    local results = {}
    local function fire(name, hold, want, py, vx)
      reset(py, vx)
      gd.input(1, {buttons = 'B'}, hold)
      local hits, last, first, dmg, hbframes, rel, y0, ymin, ymax = 0, 0, nil, 0, 0, nil, nil, 1e9, -1e9
      local seen = false
      for t = 1, hold + 160 do
        gd.wait(1)
        local p1, p2 = gd.player(1), gd.player(2)
        if p1.motion_name == want then
          seen = true
          rel = rel or t
          if (#(gd.hitboxes(1) or {})) > 0 then hbframes = hbframes + 1 end
          if not y0 then y0 = p1.y end
          if p1.action_frame < 60 then ymin = math.min(ymin, p1.y); ymax = math.max(ymax, p1.y) end
        end
        if p2.percent > dmg + 0.001 then
          hits = hits + 1; dmg = p2.percent
          first = first or t; last = t
        end
        local lua = assert(gd.fighter_lua(1))
        assert(lua.faults == 0, 'Lua fault: ' .. tostring(lua.last_fault))
      end
      local r = {hits = hits, dmg = dmg, hb = hbframes, seen = seen, rel = rel, span = ymax - ymin}
      results[name] = r
      gd.log(string.format('KAMECHK case=%s want=%s seen=%s hits=%d damage=%.2f hit_frames=%s..%s hitbox_frames=%d release_at=%s y_span=%.2f',
        name, want, tostring(seen), hits, dmg, tostring(first), tostring(last), hbframes, tostring(rel), r.span))
      assert(seen, 'state not reached: ' .. want)
      return r
    end
    local tap = fire('tap', 6, 'KameTap', 0, 24)
    local mid = fire('mid', 30, 'KameMid')
    local full = fire('full', 50, 'KameFull')
    local max = fire('max', 64, 'KameFull')
    assert(tap.hits >= 1, 'tap never hit')
    assert(mid.hits >= 2 and full.hits >= 3, 'beam does not multi-hit: mid ' .. mid.hits .. ' full ' .. full.hits)
    assert(tap.dmg < mid.dmg and mid.dmg < full.dmg, 'damage does not scale with the tier')
    assert(tap.hb < mid.hb and mid.hb < full.hb, 'beam duration does not scale with the tier')
    assert(max.dmg > full.dmg, 'a full 60-frame charge does not hit harder than 45')
    assert(full.dmg <= 30 and max.dmg <= 30, 'full beam too strong: ' .. full.dmg)
    local air = fire('air_full', 50, 'KameFull', 45)
    assert(air.span < 6, 'no hover during the air beam: y span ' .. air.span)

    -- store with shield, resume, instant fire, hit wipe
    local function lua_state() return assert(gd.fighter_lua(1)).state end
    reset()
    gd.input(1, {buttons = 'B'}, 32); gd.wait(31)
    local c0 = lua_state().charge
    gd.input(1, {buttons = 'L'}, 2); gd.wait(4)
    local st = lua_state()
    gd.log(string.format('KAMECHK store: charge before %d, stored %d, state %s', c0, st.stored, tostring(gd.player(1).motion_name)))
    assert(st.stored >= 29 and st.stored <= 33, 'store failed')
    assert(gd.player(1).motion_name ~= 'KameCharge', 'still charging after shield')
    gd.wait(45)
    gd.input(1, {buttons = 'B'}, 6); gd.wait(3)
    local resumed = lua_state().charge
    gd.log('KAMECHK resume: charge on re-entry ' .. resumed)
    assert(resumed >= st.stored, 'stored charge not resumed')
    gd.wait(200)
    -- a stored FULL charge fires on the next B press
    reset()
    gd.input(1, {buttons = 'B'}, 66); gd.wait(65)
    gd.input(1, {buttons = 'L'}, 2); gd.wait(4)
    assert(lua_state().stored >= 60, 'full charge not stored')
    gd.wait(45)
    gd.input(1, {buttons = 'B'}, 2)
    local instant = false
    for i = 1, 8 do gd.wait(1); local m = gd.player(1).motion_name; if m == 'KameFull' or m == 'KameSuper' then instant = true; break end end
    gd.log('KAMECHK instant: stored full fired at once = ' .. tostring(instant))
    assert(instant, 'stored full charge did not fire on B')
    gd.wait(200)
    -- a hit since storing wipes a partial charge
    reset()
    gd.input(1, {buttons = 'B'}, 32); gd.wait(31)
    gd.input(1, {buttons = 'L'}, 2); gd.wait(4)
    gd.set_percent(1, 12); gd.wait(45)
    gd.input(1, {buttons = 'B'}, 3); gd.wait(3)
    local wiped = lua_state().charge
    gd.log('KAMECHK wipe: charge after a hit = ' .. wiped)
    assert(wiped < 6, 'partial charge survived a hit')
    gd.wait(100)

    -- rewind exactness across charge + release + beam
    reset()
    gd.input(1, {buttons = 'B'}, 40)
    gd.wait(20)
    assert(gd.rewind_test(120, true), 'rewind refused')
    local done = false
    for i = 1, 400 do
      gd.wait(1)
      local r = gd.rewind_test_result()
      if r and r.phase == 0 and r.pass ~= nil then
        gd.log(string.format('KAMECHK rewind pass=%s diff_compared=%s', tostring(r.pass), tostring(r.diff_compared)))
        assert(r.pass and r.diff_compared == 0, 'rewind differs: ' .. tostring(r.text))
        done = true
        break
      end
    end
    assert(done, 'rewind never finished')
    gd.log('KAMECHK PASS')
  end)
  if not ok then gd.log('KAMECHK FAIL ' .. tostring(why)) end
  gd.quit()
end)
