-- Is a Goku smash a full hit or a phantom hit (damage, no knockback)? For each dummy distance, tap and fully charged: damage and how far the dummy is sent in 26 frames. Tag PHANTOM.
-- CFG: kind=f|u|d (default u), name=<dummy label>. Scene: p1 = Goku, p2 = the dummy (--vs mario|captain|fox|mars|purin|ganon|koopa).
local C = CFG or {}
local kind = C.kind or 'u'
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
    gd.cpu_mode(2, 'stand')
    local function tp(p, x, y) for i = 1, 60 do if pcall(gd.teleport, p, x, y) then return end gd.wait(20) end error('tp') end
    local out = {}
    for _, d in ipairs({2, 4, 6, 8}) do
      for _, hold in ipairs({2, 70}) do
        tp(1, 0, 0); tp(2, 30, 0); gd.set_percent(2, 0); gd.wait(40)
        gd.input(1, {x = 60}, 3); gd.wait(25)
        tp(1, 0, 0); gd.wait(2)
        local face = (gd.player(1).facing or 1) >= 0 and 1 or -1
        tp(2, d * face, 0); gd.wait(2)
        local before = gd.player(2).percent
        local spec = ({f = {buttons = 'A', x = 127 * face}, u = {buttons = 'A', y = 127}, d = {buttons = 'A', y = -127}})[kind]
        gd.input(1, spec, hold)
        local dmg, far
        for t = 1, 120 do
          gd.wait(1)
          if t <= math.max(hold, 10) then pcall(gd.teleport, 2, gd.player(1).x + face * d, 0) end
          local q = gd.player(2)
          if q.percent > before + 0.01 then
            local x0, y0 = q.x, q.y
            dmg = q.percent - before
            gd.wait(26)
            local r = gd.player(2)
            far = math.sqrt((r.x - x0) ^ 2 + (r.y - y0) ^ 2)
            out[#out + 1] = string.format('d%d %s: %.1f%% sent %.1f %s', d, hold > 2 and 'charged' or 'tap', dmg, far, far < 1 and 'PHANTOM(no launch)' or 'launched')
            break
          end
        end
        if not dmg then out[#out + 1] = string.format('d%d %s: no hit', d, hold > 2 and 'charged' or 'tap') end
        gd.wait(50)
      end
    end
    gd.log(string.format('PHANTOM %s %ssmash vs %s: %s', 'goku', kind, tostring(C.name), table.concat(out, ' | ')))
  end)
  if not ok then gd.log('PHANTOM FAIL ' .. tostring(why)) end
  gd.quit()
end)
