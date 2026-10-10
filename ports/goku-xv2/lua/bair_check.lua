-- Back air gate (cross-port: Melee Luigi's AttackAirB). Goku short-hops and presses back + A, both facings, with the dummy behind him
-- (best of several spacings); logs whether the hit connected and how long the aerial and the landing lasted.
-- Scene: mode=lab;p1=geno:goku-xv2/hu;p2=<fox|marth|mario|captain>/cpu0 . Logs BAIRCHECK lines, ends with BAIRCHECK RESULT.
local function log(fmt, ...) gd.log('BAIRCHECK ' .. string.format(fmt, ...)) end
local FREE = {}
for _, n in ipairs({ "Wait", "WalkSlow", "WalkMiddle", "WalkFast", "Turn", "Dash", "Run", "Squat", "SquatWait", "Fall", "FallF", "FallB", "FallAerial" }) do FREE[n] = true end
local function grounded_free(p) return FREE[p.motion_name or ""] == true and not (p.in_hitlag or (p.hitlag or 0) > 0) end

gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'script')
    local opp = gd.player(2).character or gd.player(2).kind or '?'
    local connected, cases = 0, 0
    for _, side in ipairs({ 1, -1 }) do
      local hit = false
      for _, d in ipairs({ 8, 11, 14 }) do
        -- settle both, face the side, put the dummy behind Goku
        for _ = 1, 200 do if grounded_free(gd.player(1)) then break end gd.wait(1) end
        gd.cpu_pad(2, {}, 1)
        gd.set_percent(1, 0); gd.set_percent(2, 0)
        gd.teleport(1, 0, 0); gd.teleport(2, side * 30, 0)
        gd.wait(40)
        gd.input(1, { x = side * 60 }, 3); gd.wait(30)          -- face `side`
        gd.teleport(1, 0, 0); gd.teleport(2, -side * d, 0)
        gd.wait(6)
        local before = gd.player(2).percent
        local facing = gd.player(1).facing
        gd.input(1, { buttons = 'X' }, 3); gd.wait(3)           -- short hop (tap)
        -- wait for the rise, then back + A
        local up = 0
        for i = 1, 30 do
          local p = gd.player(1)
          if (p.motion_name or '') == 'JumpF' or (p.motion_name or '') == 'JumpB' or (p.motion_name or '') == 'JumpAerialF' then up = i break end
          gd.wait(1)
        end
        gd.wait(6)
        gd.input(1, { x = -side * 127, buttons = 'A' }, 2); gd.wait(2)
        local trace, last, n = {}, nil, 0
        local dmg_at, hit_frame = nil, nil
        for f = 1, 140 do
          local p = gd.player(1)
          local m = p.motion_name or '?'
          if m ~= last then
            if last then trace[#trace + 1] = string.format('%s:%d', last, n) end
            last, n = m, 0
          end
          n = n + 1
          if not hit_frame and gd.player(2).percent > before then hit_frame = f; dmg_at = gd.player(2).percent - before end
          if grounded_free(p) and f > 20 then break end
          gd.wait(1)
        end
        trace[#trace + 1] = string.format('%s:%d', last or '?', n)
        cases = cases + 1
        local hitnow = hit_frame ~= nil
        log('opp=%s side=%d dist=%d facing=%s hit=%s frame=%s dmg=%.1f trace=%s', tostring(opp), side, d, tostring(facing), tostring(hitnow), tostring(hit_frame),
          dmg_at or 0, table.concat(trace, ' '))
        if hitnow then hit = true break end
      end
      if hit then connected = connected + 1 end
    end
    log('RESULT opp=%s connected %d of 2 facings (back air from behind, best of 3 spacings)', tostring(opp), connected)
  end)
  if not ok then gd.log('BAIRCHECK FAIL ' .. tostring(why)) end
  gd.quit()
end)
