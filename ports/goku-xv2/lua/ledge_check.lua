-- Up B (flight) reverse ledge catch gate (headless, turbo ok; combo package, geno 11). Tag: LEDGECHK.
-- Run: python ports/goku-xv2/tools/kame_run.py ledge_check LEDGECHK --turbo --cfg stage=bf   (KAME_MODS = the combo package's mods)
-- A weak flight (ki 0: 22 frames, speed 0.9) is flown into the right ledge of the stage from below and beside it, a grid of start positions, with
--   AWAY  = facing away from the ledge (the owner's case: the ledge is behind him), stick toward the ledge, and
--   TOWARD = facing the ledge, same stick direction.
-- The ledge window is the last 5 flight frames (goku.lua FLY_LEDGE): AWAY must only ever catch in them (flight frames 17..21 (22 - 5 .. 22 - 1)), TOWARD must still catch,
-- and catch before the window (so the engine's own front grab is untouched). Results per trial: LEDGECHK trial <kind> dx dy -> catch at flight frame F, facing a -> b.
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function name() return tostring(gd.player(1).motion_name) end
    local function tp(p, x, y)
      for i = 1, 80 do
        if pcall(gd.teleport, p, x, y) then return end
        gd.wait(30)
      end
      error('could not teleport port ' .. p)
    end
    local function nofault()
      local lua = assert(gd.fighter_lua(1))
      assert(lua.faults == 0, 'Lua fault: ' .. tostring(lua.last_fault))
    end
    local sb = assert(gd.stage_bounds(), 'no stage bounds')
    local R = sb.main_floor.right
    gd.log(string.format('LEDGECHK stage main floor %.1f..%.1f top %.1f', sb.main_floor.left, R, sb.main_floor.top))
    local function is_flight(n) return n:sub(1, 6) == 'Flight' and #n <= 7 end

    -- one trial. face = +1 faces right (away from the right ledge), -1 faces left (toward it). Start at (R + dx, ytop + dy) in the air.
    local function trial(face, dx, dy, sy)
      gd.input(1, {}, 1); gd.wait(2)
      tp(1, R - 30, sb.main_floor.top); tp(2, sb.main_floor.left + 20, sb.main_floor.top)
      gd.set_percent(1, 0); gd.set_percent(2, 0)
      gd.combo_ki(1, 0)
      gd.wait(30)
      -- turn on the floor: a short walk/dash in the wanted direction, then stop
      gd.input(1, {x = 127 * face}, 6); gd.wait(8)
      gd.input(1, {}, 1); gd.wait(14)
      tp(1, R - 30, sb.main_floor.top); gd.wait(2)
      local f0 = gd.player(1).facing >= 0 and 1 or -1
      tp(1, R + dx, sb.main_floor.top + dy)
      gd.combo_ki(1, 0)
      gd.wait(2)
      -- Up B in the air, then the stick toward the stage (x < 0 is toward the right ledge from outside) and slightly down for the 'natural' variant
      local toward = -1                     -- from outside the right edge, the stage is to the left
      gd.input(1, {y = 127, buttons = 'B'}, 2)
      local flown, cat, facing_at, last = 0, nil, nil, nil
      for t = 1, 70 do
        gd.wait(1); nofault()
        local n = name()
        if is_flight(n) then flown = flown + 1 end
        if t >= 3 and t < 63 then gd.input(1, {x = 127 * toward, y = sy}, 1) end
        if n:sub(1, 5) == 'Cliff' and not cat then cat = flown; facing_at = gd.player(1).facing >= 0 and 1 or -1; break end
        last = n
      end
      local res = {face = f0, flown = flown, cat = cat, facing_after = facing_at, last = last}
      -- reset: drop off the ledge / finish
      gd.input(1, {y = -127}, 4); gd.wait(6); gd.input(1, {}, 1)
      return res
    end

    local bads, away_catch, toward_catch_early, away_early, away_in, toward_n = {}, 0, 0, 0, 0, 0
    local function chk(c, m) if not c then bads[#bads + 1] = m; gd.log('LEDGECHK FAIL ' .. m) end end
    for _, sy in ipairs({0, -40}) do
      for _, dy in ipairs({-30, -22, -16, -10, -5}) do
        for _, dx in ipairs({26, 22, 18, 14, 10, 6, 3}) do
          for _, kind in ipairs({'AWAY', 'TOWARD'}) do
            local face = kind == 'AWAY' and 1 or -1
            local r = trial(face, dx, dy, sy)
            gd.log(string.format('LEDGECHK trial %s stickY %d dx %d dy %d -> face %d, flight frames %d, catch at flight frame %s, facing after %s, last %s', kind, sy, dx, dy, r.face, r.flown, tostring(r.cat), tostring(r.facing_after), tostring(r.last)))
            if kind == 'AWAY' then
              chk(r.face == 1, 'AWAY trial did not start facing away')
              if r.cat then
                away_catch = away_catch + 1
                if r.cat >= 17 and r.cat <= 21 then away_in = away_in + 1 else away_early = away_early + 1; chk(false, 'AWAY caught before the window at flight frame ' .. r.cat .. ' (dx ' .. dx .. ' dy ' .. dy .. ')') end
                chk(r.facing_after == -1, 'AWAY catch did not turn him to the ledge')
              end
            else
              chk(r.face == -1, 'TOWARD trial did not start facing the ledge')
              if r.cat then toward_n = toward_n + 1; if r.cat < 17 then toward_catch_early = toward_catch_early + 1 end end
            end
          end
        end
      end
    end
    gd.log(string.format('LEDGECHK summary: AWAY catches %d (in window %d, early %d); TOWARD catches %d (before the window %d)', away_catch, away_in, away_early, toward_n, toward_catch_early))
    chk(away_in >= 1, 'no AWAY catch in the window at all')
    chk(toward_n >= 1, 'no TOWARD catch at all (the forward grab is broken)')
    assert(#bads == 0, table.concat(bads, '; '))
  end)
  if ok then gd.log('LEDGECHK RESULT PASS') else gd.log('LEDGECHK RESULT FAIL ' .. tostring(why)) end
  gd.quit()
end)
