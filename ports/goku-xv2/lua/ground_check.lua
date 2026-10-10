-- Hybrid hover stance gate: low ground attacks of other fighters must still hit Goku's hovering stance, from both sides.
-- Scene: mode=lab;p1=geno:goku-xv2/hu;p2=<fox|marth|captain>/cpu0 . Logs GROUNDCHECK lines.
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'script')
    local opp = gd.player(2).character or gd.player(2).kind or '?'
    local attacks = {
      {'dtilt', {y = -80, buttons = 'A'}, 2},
      {'dsmash', {y = -127, buttons = 'A'}, 2},
    }
    local total, hits = 0, 0
    for _, a in ipairs(attacks) do
      for _, side in ipairs({1, -1}) do
        local connected = false
        for _, d in ipairs({9, 12, 15}) do
          gd.teleport(1, 0, 0); gd.teleport(2, side * d, 0)
          gd.set_percent(1, 0); gd.set_percent(2, 0)
          gd.cpu_pad(2, {x = -side * 60}, 2)   -- face Goku
          gd.wait(14)
          local before = gd.player(1).percent
          local spec = {x = 0, y = a[2].y, buttons = a[2].buttons}
          gd.cpu_pad(2, spec, 2)
          gd.wait(60)
          local after = gd.player(1).percent
          gd.log(string.format('GROUNDCHECK opp=%s attack=%s side=%d dist=%d p2facing=%s goku %.1f -> %.1f p2state=%s', tostring(opp), a[1], side, d,
            tostring(gd.player(2).facing), before, after, tostring(gd.player(2).motion_name)))
          if after > before then connected = true; break end
          gd.wait(30)
        end
        total = total + 1
        if connected then hits = hits + 1 end
      end
    end
    gd.log(string.format('GROUNDCHECK RESULT opp=%s connected %d of %d (dtilt/dsmash x both sides, best of 3 spacings)', tostring(opp), hits, total))
  end)
  if not ok then gd.log('GROUNDCHECK FAIL ' .. tostring(why)) end
  gd.quit()
end)
