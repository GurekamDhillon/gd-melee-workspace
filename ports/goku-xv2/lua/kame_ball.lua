-- Charge-ball placement probe. Needs the package built with `gen_kame.py --probe` (zero-damage hitboxes at hand.R: origin, +10 x, +10 y, +10 z).
-- Per sampled frame prints "KBALL t=<n> af=<af> hR=x,y,z hL=x,y,z o=.. ax=.. ay=.. az=.." (world units); tools/kame_ball.py turns them into the hands-midpoint
-- in hand.R's own frame and (with CFG.off) the distance from the ball to the midpoint. CFG: face=left, air=1 (jump first), n (frames, default 90), every (default 3), warm=
local C = CFG or {}
local LEFT = C.face == 'left'
local N = tonumber(C.n or 90)
local EVERY = tonumber(C.every or 3)
local FROM = tonumber(C.from or 0)        -- first frame to log (the script log is capped at ~400 lines)
local HOLD = tonumber(C.hold or 0)     -- frames after the first B before ACT is pressed (0 = never)
local ACT = C.act or 'L'              -- L = store the charge, B = fire it
local STOREB = tonumber(C.storeb or 0) -- frames after the store before the next B resumes (0 = no resume)
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    for _, pt in ipairs({1, 2}) do pcall(gd.debug_draw, pt, 0) end
    gd.teleport(1, 0, 0); gd.teleport(2, 60 * (LEFT and -1 or 1), 0)
    gd.set_percent(1, 0); gd.set_percent(2, 0); gd.wait(30)
    if LEFT then gd.input(1, {x = -127}, 6); gd.wait(20); gd.teleport(1, 0, 0); gd.wait(10) end
    if C.air == '1' then gd.input(1, {buttons = 'X'}, 3); gd.wait(14) end
    local f = gd.player(1).facing
    gd.log('KBALL facing=' .. tostring(f))
    if C.ki and gd.combo_ki then gd.combo_ki(1, tonumber(C.ki)) end
    gd.input(1, {buttons = 'B'}, 2)
    for t = 1, N do
      gd.wait(1)
      if HOLD > 0 and t == HOLD then gd.input(1, {buttons = ACT}, 2) end
      if HOLD > 0 and STOREB > 0 and t == HOLD + STOREB then gd.input(1, {buttons = 'B'}, 2) end
      if t % EVERY == 0 and t >= FROM then
        local p = gd.player(1)
        local js = gd.joints(1, true) or {}
        local hr, hl = js[26], js[50]       -- list index = joint index + 1 (hand.R = 25, hand.L = 49)
        local hb = gd.hitboxes(1) or {}
        if t == EVERY then gd.log('KBALL nhb=' .. #hb) end
        local pos = {}
        for _, h in ipairs(hb) do pos[(h.id or h.slot or #pos) + 1] = h end
        local function s(h) return h and string.format('%.3f,%.3f,%.3f', h.px or h.x, h.py or h.y, h.pz or h.z) or 'nil' end
        local fxs = {}
        for _, r in ipairs(gd.fx() or {}) do if tostring(r.package):find('BallProbe') and r.bbox then local b = r.bbox; fxs[#fxs + 1] = string.format('%s=%.3f,%.3f,%.3f', tostring(r.package):sub(-1), (b.min.x + b.max.x) / 2, (b.min.y + b.max.y) / 2, (b.min.z + b.max.z) / 2) end end
        gd.log(string.format('KBALL t=%d st=%s af=%s hR=%s hL=%s o=%s ax=%s ay=%s az=%s fx=%s', t, tostring(p.motion_name), tostring(p.action_frame),
          s(hr), s(hl), s(pos[1]), s(pos[2]), s(pos[3]), s(pos[4]), table.concat(fxs, ';')))
      end
    end
    gd.log('KBALL DONE')
  end)
  if not ok then gd.log('KBALL FAIL ' .. tostring(why)) end
  gd.quit()
end)
