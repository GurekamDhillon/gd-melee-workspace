-- Measures every own animation row's length (anim_end) of Goku in the native game; prints ROWLEN <name> <frames>.
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 60 end, 6000), 'no LAB match')
    gd.log('ROWLEN stage match-ready')
    gd.cpu_mode(2, 'stand'); gd.wait(10)
    local rows = gd.anim_rows(1)
    gd.log('ROWLEN stage rows=' .. tostring(rows and #rows))
    local n = 0
    for _, r in ipairs(rows or {}) do
      if n < 3 then gd.log('ROWLEN stage preview ' .. tostring(r.row)) end
      gd.anim_preview(1, r.row, 0)
      gd.wait(2)
      local p = gd.player(1)
      gd.log(string.format('ROWLEN %s %d %s', tostring(r.name), r.row, tostring(p.anim_end)))
      n = n + 1
    end
    gd.anim_preview(1, nil)
    gd.log('ROWLEN DONE ' .. n)
  end)
  if not ok then gd.log('ROWLEN FAIL ' .. tostring(why)) end
  gd.quit()
end)
