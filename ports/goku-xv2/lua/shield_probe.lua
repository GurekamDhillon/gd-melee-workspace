-- Where the shield bubble is centred, relative to the fighter (x forward-relative, y up), in GuardOn / Guard / the idle. Tag SHIELDPROBE.
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
    gd.cpu_mode(2, 'stand')
    local function tp(p, x, y) for i = 1, 40 do if pcall(gd.teleport, p, x, y) then return end gd.wait(20) end error('tp') end
    tp(1, 0, 0); tp(2, 80, 0); gd.wait(30)
    local out = {}
    local function snap(tag)
      local p = gd.player(1)
      local face = (p.facing or 1) >= 0 and 1 or -1
      out[#out + 1] = string.format('%s %s on=%s sx=%.1f sy=%.1f r=%.1f (dx %.1f dy %.1f)', tag, tostring(p.motion_name), tostring(p.shield_on), p.shield_x or 0, p.shield_y or 0, p.shield_r or 0, ((p.shield_x or 0) - p.x) * face, (p.shield_y or 0) - p.y)
    end
    snap('idle')
    gd.input(1, {buttons = 'L'}, 40)
    for t = 1, 30 do gd.wait(1) if t == 3 or t == 8 or t == 20 or t == 29 then snap('guard t=' .. t) end end
    gd.input(1, {}, 1); gd.wait(30)
    for t = 1, 40 do gd.wait(1) if t % 10 == 0 then snap('idle after t=' .. t) end end
    gd.log('SHIELDPROBE ' .. table.concat(out, ' | '))
  end)
  if not ok then gd.log('SHIELDPROBE FAIL ' .. tostring(why)) end
  gd.quit()
end)
