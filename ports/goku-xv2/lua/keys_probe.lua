gd.run(function()
  assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
  local p = gd.player(1); local k = {}
  for key, v in pairs(p) do k[#k + 1] = key .. '=' .. tostring(v) end
  table.sort(k); gd.log('KEYS ' .. table.concat(k, ' '))
  gd.quit()
end)
