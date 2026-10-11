-- Second LAB match after leaving to the stage select (the owner's crash: "Cannot find symbol ftDataMario" on the second load). Tag SECONDMATCH.
local C = CFG or {}
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 60 end, 6000), 'no first match')
    gd.log('SECONDMATCH first match up')
    local r, reason = gd.lab_leave('sss'); gd.log('SECONDMATCH leave ' .. tostring(r) .. ' ' .. tostring(reason))
    gd.wait(90)
    local C2 = CFG or {}
    if C2.dx then gd.input(1, {x = tonumber(C2.dx)}, 6); gd.wait(20) end
    for i = 1, 40 do gd.input(1, {buttons = 'A'}, 2); gd.wait(30); if gd.match().active then break end end
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 60 end, 3000), 'no second match')
    gd.log('SECONDMATCH PASS second match up, frame ' .. tostring(gd.match().frame))
  end)
  if not ok then gd.log('SECONDMATCH FAIL ' .. tostring(why)) end
  gd.quit()
end)
