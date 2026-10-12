gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
    gd.cpu_mode(2, 'stand')
    local function tp(p, x, y) for i = 1, 40 do if pcall(gd.teleport, p, x, y) then return end gd.wait(20) end error('tp') end
    tp(1, 0, 0); tp(2, 60, 0); gd.combo_ki(1, 0); gd.wait(40)
    tp(1, 0, 90); gd.wait(2)
    gd.input(1, {y = -127, buttons = 'B'}, 4)
    gd.wait(3)
    gd.input(1, {buttons = 'B'}, 60)
    for t = 1, 40 do
      gd.wait(1)
      local p = gd.player(1)
      if t == 2 then local ks = {} for k, v in pairs(p) do if tostring(k):find('vel') or tostring(k):find('speed') or tostring(k):find('fast') or tostring(k):find('fall') then ks[#ks+1] = k .. '=' .. tostring(v) end end gd.log('ACDBG keys ' .. table.concat(ks, ' ')) local l = gd.fighter_lua(1) gd.log('ACDBG lua faults ' .. tostring(l.faults) .. ' ' .. tostring(l.last_fault)) end
      if t % 3 == 1 then gd.log(string.format('ACDBG t=%d %s y=%.1f ki=%s af=%s', t, tostring(p.motion_name), p.y, tostring((gd.combo(1) or {}).ki), tostring(p.anim_frame))) end
    end
  end)
  if not ok then gd.log('ACDBG FAIL ' .. tostring(why)) end
  gd.quit()
end)
