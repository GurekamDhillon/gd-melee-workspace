-- Ground/hover blend trace (owner #1, #3): for each grounded action, log the lowest FOOT joint height above the floor (root-relative) at the first and last frames of every motion segment, so a snap between
-- hover (idle ~2.0 above the floor) and an anchored row shows as a jump. Scene: mode=lab;p1=geno:goku-xv2/hu;p2=mario/cpu0 .
-- Logs GROUNDTRACE lines, ends with GROUNDTRACE DONE.
local function log(fmt, ...) gd.log('GROUNDTRACE ' .. string.format(fmt, ...)) end
local function lowest()
  -- lowest of the four foot joints (b_R_Foot 7, b_R_Toe 9, b_L_Foot 13, b_L_Toe 15; list index = joint + 1) above the root = the floor line
  local js, m = gd.joints(1) or {}, nil
  local root = gd.player(1).y or 0
  for _, ji in ipairs({ 7, 9, 13, 15 }) do local j = js[ji + 1]; if j and j.y and (not m or j.y < m) then m = j.y end end
  return (m or 0) - root
end
local function settle()
  for _ = 1, 200 do
    local m = gd.player(1).motion_name or ''
    if m == 'Wait' then break end
    gd.wait(1)
  end
  gd.wait(10)
end

gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    gd.teleport(1, -12, 0); gd.teleport(2, 40, 0)
    gd.wait(60)
    log('idle lowest joint (relative to root) = %.2f', lowest())
    local function run_action(name, plan, frames_after)
      settle()
      local segs, last, cur = {}, nil, nil
      local function sample()
        local m = gd.player(1).motion_name or '?'
        if m ~= last then cur = { m = m, v = {} }; segs[#segs + 1] = cur; last = m end
        cur.v[#cur.v + 1] = lowest()
      end
      plan(sample)
      for _ = 1, frames_after do gd.wait(1); sample() end
      for _, s in ipairs(segs) do
        local n, f, l = #s.v, {}, {}
        for i = 1, math.min(3, n) do f[#f + 1] = string.format('%.2f', s.v[i]) end
        for i = math.max(1, n - 2), n do l[#l + 1] = string.format('%.2f', s.v[i]) end
        local mn = math.huge
        for _, x in ipairs(s.v) do if x < mn then mn = x end end
        log('%s %-14s n=%-3d first=[%s] last=[%s] min=%.2f', name, s.m, n, table.concat(f, ' '), table.concat(l, ' '), mn)
      end
    end
    local function press(spec, n, sample) gd.input(1, spec, n); for _ = 1, n do gd.wait(1); sample() end end
    run_action('jab', function(s) press({ buttons = 'A' }, 2, s); for _ = 1, 3 do gd.wait(1); s() end; press({ buttons = 'A' }, 2, s) end, 80)
    run_action('ftilt', function(s) press({ x = 60, buttons = 'A' }, 2, s) end, 60)
    run_action('utilt', function(s) press({ y = 50, buttons = 'A' }, 2, s) end, 60)
    run_action('dtilt', function(s) press({ y = -50, buttons = 'A' }, 2, s) end, 60)
    run_action('crouch', function(s) press({ y = -127 }, 40, s) end, 30)
    run_action('grab', function(s) press({ buttons = 'Z' }, 2, s) end, 70)
    run_action('shield', function(s) press({ l = 200 }, 30, s) end, 30)
    log('RESULT PASS DONE')
  end)
  if not ok then gd.log('GROUNDTRACE FAIL ' .. tostring(why)) end
  gd.quit()
end)
