-- KO percent of the three smash attacks on a Mario dummy at the centre of the stage (no DI, idle CPU), uncharged and fully charged. Tag KOPROBE.
-- CFG: name=<label>. Scene: p1 = the attacker (geno:goku-xv2/hu, mars, captain), p2 = mario/cpu0, any flat stage (bf for the report).
-- For each smash and charge: the dummy distance that gives the most damage (4..13), then the dummy's percent from 30 up in steps of 10 until it loses a stock.
-- Usage: python ports/goku-xv2/tools/kame_run.py ko_probe KOPROBE [--p1 mars] --cfg name=marth --turbo --vs mario
local C = CFG or {}
local function log(fmt, ...) gd.log('KOPROBE ' .. string.format(fmt, ...)) end
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function tp(p, x, y) for i = 1, 60 do if pcall(gd.teleport, p, x, y) then return end gd.wait(20) end error('teleport') end
    local function nm(p) return tostring(gd.player(p).motion_name) end
    local function place(d)
      gd.input(1, {}, 1)
      gd.set_percent(1, 0)
      tp(1, 0, 0); tp(2, 30, 0); gd.wait(40)
      gd.input(1, {x = 60}, 3); gd.wait(28)
      tp(1, 0, 0); gd.wait(2)
      local face = (gd.player(1).facing or 1) >= 0 and 1 or -1
      tp(2, d * face, 0); gd.wait(2)
      return face
    end
    -- one trial: returns the damage dealt and whether the dummy lost a stock
    local function trial(kind, charge, d, pct)
      local face = place(d)
      gd.set_percent(2, pct)
      local stocks0 = gd.player(2).stocks
      local before = gd.player(2).percent
      local spec = {f = {buttons = 'A', x = 127 * face}, u = {buttons = 'A', y = 127}, d = {buttons = 'A', y = -127}}
      local hold = charge == 1 and 70 or 2
      gd.input(1, spec[kind], hold)
      local dmg, ko = 0, false
      for t = 1, 260 do
        gd.wait(1)
        if t <= math.max(hold, 14) then pcall(gd.teleport, 2, gd.player(1).x + face * d, 0) end
        local p2 = gd.player(2)
        if p2.percent > before + 0.01 and dmg == 0 then dmg = p2.percent - before end
        if tostring(p2.motion_name):find('^Dead') then ko = true break end
      end
      gd.wait(60)
      return dmg, ko
    end
    for _, kind in ipairs({'f', 'u', 'd'}) do
      for charge = 0, 1 do
        local bestd, bestdmg = nil, 0
        for _, d in ipairs({4, 6, 8, 10, 13}) do
          local dmg = trial(kind, charge, d, 0)
          if dmg > bestdmg then bestdmg, bestd = dmg, d end
        end
        for _ = 1, 6 do trial(kind, charge, bestd or 6, 0) end   -- warm-up: every fighter is measured with the same full stale-move queue
        local kopct
        if bestd then
          for pct = 40, 300, 10 do
            local _, ko = trial(kind, charge, bestd, pct)
            if ko then kopct = pct break end
          end
        end
        log('%s %ssmash charge=%d: best distance %s, damage at 0%% %.1f, first KO at %s%%', tostring(C.name), kind, charge, tostring(bestd), bestdmg, tostring(kopct))
      end
    end
  end)
  if not ok then log('FAIL %s', tostring(why)) end
  gd.quit()
end)
