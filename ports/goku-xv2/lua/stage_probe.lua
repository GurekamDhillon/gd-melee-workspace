gd.run(function()
  assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
  local b = gd.stage_bounds()
  local function dump(t, pre) for k, v in pairs(t) do if type(v) == 'table' then dump(v, pre .. k .. '.') else gd.log('PROBE ' .. pre .. k .. '=' .. tostring(v)) end end end
  dump(b or {}, '')
  gd.quit()
end)
