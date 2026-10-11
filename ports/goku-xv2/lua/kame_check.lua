-- Kamehameha gates (headless, turbo ok): beam hits several times, damage/duration scale with charge, store/resume/instant-fire rules,
-- the air hover, rewind exactness. Tag: KAMECHECK. Run: python ports/goku-xv2/tools/kame_run.py kame_check KAMECHECK --turbo
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    -- a Max beam can KO the dummy (it respawns for a while): wait for a fighter that can be moved
    local function tp(port, x, y)
      for i = 1, 40 do
        local ok = pcall(gd.teleport, port, x, y)
        if ok then return end
        gd.wait(30)
      end
      error('could not teleport port ' .. port)
    end
    local function reset(py, vx)
      vx = vx or 30
      gd.input(1, {}, 1); gd.wait(2)
      tp(1, 0, py or 0); tp(2, vx, 0)
      gd.set_percent(1, 0); gd.set_percent(2, 0); gd.wait(70)
      tp(1, 0, py or 0); tp(2, vx, 0); gd.set_percent(2, 0); gd.wait(3)
    end
    local results = {}
    -- native model: B once enters the self-running charge; B again fires at the current level. `hold` = frames from the enter press to the fire press
    local function fire(name, hold, want, py, vx)
      reset(py, vx)
      gd.input(1, {buttons = 'B'}, 2); gd.wait(hold)
      gd.input(1, {buttons = 'B'}, 2)
      local hits, last, first, dmg, hbframes, rel, y0, ymin, ymax = 0, 0, nil, 0, 0, nil, nil, 1e9, -1e9
      local maxhb = 0   -- the highest live drag-hit damage (after the Lua scaling, before staling)
      local seen = false
      for t = 1, 170 do
        gd.wait(1)
        local p1, p2 = gd.player(1), gd.player(2)
        if p1.motion_name == want then
          seen = true
          rel = rel or t
          local live = gd.hitboxes(1) or {}
          if #live > 0 then hbframes = hbframes + 1 end
          if p1.action_frame < 40 then for _, h in ipairs(live) do maxhb = math.max(maxhb, h.damage) end end
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
      local r = {hits = hits, dmg = dmg, hb = hbframes, seen = seen, rel = rel, span = ymax - ymin, maxhb = maxhb}
      results[name] = r
      gd.log(string.format('KAMECHECK case=%s want=%s seen=%s hits=%d damage=%.2f hit_frames=%s..%s hitbox_frames=%d release_at=%s y_span=%.2f drag_dmg=%.2f',
        name, want, tostring(seen), hits, dmg, tostring(first), tostring(last), hbframes, tostring(rel), r.span, maxhb))
      assert(seen, 'state not reached: ' .. want)
      return r
    end
    -- the chant tiers (lua/goku.lua T1..T4 = units 5 / 17 / 35 / 53; a unit every 10th frame after the 10-frame Start = the beats "ka" 60, "me" 180, "ha" 360, "me" 540; full at 610 = ~10 s)
    local tap = fire('tap', 14, 'KameTap', 0, 24)        -- B before "ka" is finished (ages 11 to 19): tier 0, the quick blast
    local thin = fire('thin', 80, 'KameThin', 0, 28)      -- after "ka" (1 s)
    local mid = fire('mid', 240, 'KameMid')               -- after "me" (3 s)
    local full = fire('full', 440, 'KameFull')             -- after "ha" (6 s)
    local mx = fire('max', 580, 'KameMax')                -- after the last "me" (9 s): the full chant
    local smx = fire('stored_max', 660, 'KameMax')        -- auto-stored at the end of the chant, fired from the store
    assert(tap.hits >= 1, 'tap never hit')
    assert(thin.hits >= 2 and mid.hits >= 2 and full.hits >= 3 and mx.hits >= 4, 'beams do not multi-hit: thin ' .. thin.hits .. ' mid ' .. mid.hits .. ' full ' .. full.hits .. ' max ' .. mx.hits)
    assert(tap.dmg < thin.dmg and thin.dmg < mid.dmg and mid.dmg < full.dmg and full.dmg < mx.dmg, 'damage does not rise with the tier')
    assert(tap.hb < thin.hb and thin.hb < mid.hb and mid.hb < full.hb and full.hb < mx.hb, 'beam duration does not rise with the tier')
    assert(mx.dmg <= 48 and smx.dmg <= 48, 'max beam too strong: ' .. mx.dmg)
    local air = fire('air_max', 580, 'KameMax', 45)
    assert(air.span < 6, 'no hover during the air beam: y span ' .. air.span)

    -- shield cancel at 30 charge frames stores and leaves; B resumes; auto-store at full; roll cancel keeps the level; a hit wipes a partial charge
    local function lua_state() return assert(gd.fighter_lua(1)).state end
    -- end a case with nothing stored: B enters (a stored full charge fires at once, a partial one resumes), B again fires the level
    local function clean()
      gd.input(1, {buttons = 'B'}, 2); gd.wait(14)
      if lua_state().stored > 0 then gd.input(1, {buttons = 'B'}, 2) end
      gd.wait(220)
      assert(lua_state().stored == 0, 'clean() left a stored charge: ' .. lua_state().stored)
    end
    reset()
    gd.input(1, {buttons = 'B'}, 2); gd.wait(270)
    local c0 = lua_state().charge
    gd.input(1, {buttons = 'L'}, 2); gd.wait(4)
    local st = lua_state()
    gd.log(string.format('KAMECHECK store: charge before %d, stored %d, state %s', c0, st.stored, tostring(gd.player(1).motion_name)))
    assert(st.stored >= 20 and st.stored <= 34, 'store failed')
    assert(gd.player(1).motion_name == 'KameStore2', 'shield did not enter the tier-2 flash state KameStore2: ' .. tostring(gd.player(1).motion_name))
    gd.wait(30)
    assert(tostring(gd.player(1).motion_name):sub(1, 9) ~= 'KameStore', 'KameStore did not end')
    gd.input(1, {buttons = 'B'}, 2); gd.wait(3)
    local resumed = lua_state().charge
    gd.log('KAMECHECK resume: charge on re-entry ' .. resumed)
    assert(resumed >= st.stored, 'stored charge not resumed')
    gd.wait(14); gd.input(1, {buttons = 'B'}, 2); gd.wait(220)
    -- the charge runs by itself: no button held; at full on the ground it auto-stores and exits, B fires it at once
    reset()
    gd.input(1, {buttons = 'B'}, 2); gd.wait(640)
    local ss = lua_state()
    gd.log(string.format('KAMECHECK autostore: stored %d state %s', ss.stored, tostring(gd.player(1).motion_name)))
    assert(ss.stored >= 60, 'full charge did not store by itself')
    assert(gd.player(1).motion_name ~= 'KameCharge', 'still in the charge loop at full on the ground')
    gd.wait(45)
    gd.input(1, {buttons = 'B'}, 2)
    local instant = false
    for i = 1, 8 do gd.wait(1); local m = gd.player(1).motion_name; if m == 'KameMax' or m == 'KameSuper' then instant = true; break end end
    gd.log('KAMECHECK instant: stored full fired at once = ' .. tostring(instant))
    assert(instant, 'stored full charge did not fire on B')
    gd.wait(200)
    -- roll cancel (stick flick during the loop, the natives' ftCo_8009917C): leaves the charge into a roll with the level kept
    reset()
    gd.input(1, {buttons = 'B'}, 2); gd.wait(50)
    local cr = lua_state().charge
    gd.input(1, {x = 0}, 1); gd.wait(1); gd.input(1, {x = 127}, 3)
    local rolled = false
    for i = 1, 6 do gd.wait(1); local m = tostring(gd.player(1).motion_name); if m:find('Escape') or m:find('Roll') then rolled = true end end
    gd.log(string.format('KAMECHECK roll: charge %d stored %d rolled=%s state %s', cr, lua_state().stored, tostring(rolled), tostring(gd.player(1).motion_name)))
    assert(rolled, 'roll cancel did not leave the charge into a roll')
    assert(lua_state().stored >= cr - 2, 'roll cancel lost the level')
    gd.wait(60); clean()
    -- a hit since storing wipes a partial charge
    reset()
    gd.input(1, {buttons = 'B'}, 2); gd.wait(100)
    gd.input(1, {buttons = 'L'}, 2); gd.wait(4)
    gd.set_percent(1, 12); gd.wait(45)
    gd.input(1, {buttons = 'B'}, 3); gd.wait(3)
    local wiped = lua_state().charge
    gd.log('KAMECHECK wipe: charge after a hit = ' .. wiped)
    assert(wiped < 6, 'partial charge survived a hit')
    gd.wait(14); gd.input(1, {buttons = 'B'}, 2); gd.wait(220)
    -- a stored FULL charge survives a hit
    reset()
    gd.input(1, {buttons = 'B'}, 2); gd.wait(640)
    gd.set_percent(1, 12); gd.wait(45)
    gd.input(1, {buttons = 'B'}, 3); gd.wait(3)
    local kept = lua_state().charge
    local mk = tostring(gd.player(1).motion_name)
    gd.log('KAMECHECK fullkeep: after a hit, charge/state ' .. kept .. ' ' .. mk)
    assert(kept >= 60 or mk == 'KameMax' or mk == 'KameSuper', 'a full stored charge did not survive a hit')
    gd.wait(200)

    -- rewind exactness across the last chant beat (the 540 shake / flash events), the auto-store at full and the store flash
    reset()
    gd.input(1, {buttons = 'B'}, 2); gd.wait(520)
    assert(gd.rewind_test(160, true), 'rewind refused (charge)')
    for i = 1, 500 do
      gd.wait(1)
      local r = gd.rewind_test_result()
      if r and r.phase == 0 and r.pass ~= nil then
        gd.log(string.format('KAMECHECK rewind_charge pass=%s diff_compared=%s', tostring(r.pass), tostring(r.diff_compared)))
        assert(r.pass and r.diff_compared == 0, 'rewind (charge) differs: ' .. tostring(r.text))
        break
      end
    end
    gd.wait(60); gd.input(1, {buttons = 'B'}, 2); gd.wait(200)
    -- rewind exactness across charge + release + beam
    reset()
    gd.input(1, {buttons = 'B'}, 2); gd.wait(40)
    gd.input(1, {buttons = 'B'}, 2)
    gd.wait(10)
    assert(gd.rewind_test(120, true), 'rewind refused')
    local done = false
    for i = 1, 400 do
      gd.wait(1)
      local r = gd.rewind_test_result()
      if r and r.phase == 0 and r.pass ~= nil then
        gd.log(string.format('KAMECHECK rewind pass=%s diff_compared=%s', tostring(r.pass), tostring(r.diff_compared)))
        assert(r.pass and r.diff_compared == 0, 'rewind differs: ' .. tostring(r.text))
        done = true
        break
      end
    end
    assert(done, 'rewind never finished')
    gd.log('KAMECHECK PASS')
  end)
  if not ok then gd.log('KAMECHECK FAIL ' .. tostring(why)) end
  gd.quit()
end)
