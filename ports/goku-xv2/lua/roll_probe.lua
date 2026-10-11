-- Measure a roll: motion, frames, intangibility, x travel, visibility per frame. Tag ROLLPROBE. CFG: dir=1 forward / -1 back, spot=1 for the spot dodge, air=1 air dodge.
local C = CFG or {}
gd.run(function()
  assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
  gd.cpu_mode(2, 'stand')
  gd.teleport(1, 0, 0); gd.teleport(2, 60, 0); gd.set_percent(1, 0); gd.wait(60)
  gd.teleport(1, 0, 0); gd.wait(5)
  local p0 = gd.player(1)
  local face = (p0.facing or 1) >= 0 and 1 or -1
  local d = tonumber(C.dir or 1)
  local inp = {buttons = 'L'}
  if C.spot == '1' then inp.y = -127 else inp.x = 127 * d * face end
  gd.input(1, inp, 4)
  local x0, first_t, last_int, int_n, tele_n, log = p0.x, nil, nil, 0, 0, {}
  for t = 1, 80 do
    gd.wait(1)
    local p = gd.player(1)
    local m = tostring(p.motion_name)
    if m:find('Escape') then
      first_t = first_t or t
      local int = ((p.intangible or 0) > 0 or tostring(p.body_state) ~= 'normal') and 1 or 0
      int_n = int_n + int
      log[#log + 1] = string.format('%d:%s:i%d:x%.1f%s', t, m, int, (p.x or 0) - x0, (p.hidden and ':H' or '') .. ':' .. tostring(p.body_state))
    end
  end
  gd.log('ROLLPROBE ' .. tostring(C.name) .. ' facing ' .. face .. ' escape frames ' .. #log .. ' intangible frames ' .. int_n .. ' x travel ' .. string.format('%.1f', (gd.player(1).x or 0) - x0))
  gd.log('ROLLPROBE trace ' .. table.concat(log, ' '))
  gd.quit()
end)
