-- Ledge position gate (goku-stage playtest 2026-10-11, item 3): where the body hangs and where each ledge option ends, measured against the ledge point
-- (right ledge of Battlefield, stage_bounds main_floor right/top), headless, turbo ok. Lines: LEDGEPOS ... ; ends with LEDGEPOS RESULT PASS|FAIL.
--   python ports/goku-xv2/tools/ledge_run.py --script ledge_hang_check --name goku-ledge-pos --mods <combo-package/mods>
--   (retail reference: ledge_run.py --p1 captain --tag LEDGEPOS --script ledge_hang_check ... : the same harness on Captain Falcon; Goku's own hand joints 25 / 49 are logged as J25 / J49,
--    other fighters log the five joints nearest the ledge point.)
-- Hang: CliffCatch then CliffWait, sampled over 30 frames. The hands of a hanging fighter are at the ledge point (retail: within HAND_TOL units); a hang drawn in the air
-- (the toes at the ledge) puts the hands ~19 units above it. Options (getup / attack / roll / jump, Quick and Slow): the position when the Cliff rows end must be on the stage
-- (x inside the ledge by 0..INSIDE_MAX, feet on the floor) for getup / attack / roll.
local HAND_TOL = 8.0
local INSIDE_MAX = 45.0
local HANDS = { 25, 49 }
local function log(fmt, ...) gd.log('LEDGEPOS ' .. string.format(fmt, ...)) end
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function name() return tostring(gd.player(1).motion_name) end
    local function tp(p, x, y)
      for i = 1, 80 do
        if pcall(gd.teleport, p, x, y) then return end
        gd.wait(30)
      end
      error('could not teleport port ' .. p)
    end
    local function nofault()
      local lua = gd.fighter_lua(1)
      if lua then assert(lua.faults == 0, 'Lua fault: ' .. tostring(lua.last_fault)) end
    end
    local sb = assert(gd.stage_bounds(), 'no stage bounds')
    local R, top = sb.main_floor.right, sb.main_floor.top
    local bads = {}
    local function chk(c, m) if not c then bads[#bads + 1] = m; gd.log('LEDGEPOS FAIL ' .. m) end end
    local function d2(j) return math.sqrt((j.x - R) ^ 2 + (j.y - top) ^ 2) end
    local function snap()
      local p = gd.player(1)
      local js = gd.joints(1) or {}
      local hm, hs = 1e9, {}
      for _, i in ipairs(HANDS) do
        local j = js[i + 1]
        if j and j.valid and j.x then hs[#hs + 1] = string.format('J%d dx %.1f dy %.1f', i, j.x - R, j.y - top); hm = math.min(hm, d2(j)) end
      end
      local near = {}
      for i, j in ipairs(js) do if j.valid and j.x then near[#near + 1] = { i - 1, d2(j), j.x - R, j.y - top } end end
      table.sort(near, function(a, b) return a[2] < b[2] end)
      local ns = {}
      for k = 1, math.min(5, #near) do ns[#ns + 1] = string.format('j%d(%.1f,%.1f)', near[k][1], near[k][3], near[k][4]) end
      local topy = -1e9
      for _, j in ipairs(js) do if j.valid and j.y and j.y > topy then topy = j.y end end
      return p, hm, table.concat(hs, ' '), table.concat(ns, ' '), topy - top
    end

    local function grab_ledge()
      for _, p in ipairs({ { 8, -14 }, { 5, -10 }, { 12, -18 }, { 3, -8 }, { 16, -24 } }) do
        gd.input(1, {}, 1); gd.wait(2)
        tp(1, R - 30, top); tp(2, sb.main_floor.left + 20, top)
        gd.wait(20)
        gd.input(1, { x = -127 }, 6); gd.wait(8)
        gd.input(1, {}, 1); gd.wait(14)
        tp(1, R + p[1], top + p[2]); gd.wait(1)
        for t = 1, 45 do
          gd.input(1, { x = -40 }, 1); gd.wait(1); nofault()
          if name() == 'CliffCatch' then return true end
        end
      end
      return false
    end

    local hang_min
    local function run_option(speed, pct, opt, stick, button, want_stage)
      gd.set_percent(1, pct); gd.set_percent(2, 0)
      if not grab_ledge() then chk(false, speed .. ' ' .. opt .. ': never caught the ledge'); return end
      local waited = 0
      for t = 1, 70 do
        gd.input(1, {}, 1); gd.wait(1); nofault()
        local p, hm, hs, ns, topy = snap()
        if opt == 'getup' and speed == 'Quick' and (name() == 'CliffCatch' or (name() == 'CliffWait' and waited % 6 == 0)) then
          log('hang %s f%d %s dx %.2f dy %.2f hands[%s] hand_min %.2f top_joint_above_ledge %.2f nearest[%s]', speed, p.action_frame or -1, name(), p.x - R, p.y - top, hs, hm, topy, ns)
        end
        if name() == 'CliffWait' then
          waited = waited + 1
          if waited >= 10 and (not hang_min or hm < 1e8) and opt == 'getup' and speed == 'Quick' then hang_min = hm end
        end
      end
      chk(name() == 'CliffWait', speed .. ' ' .. opt .. ': did not hang (state ' .. name() .. ')')
      local inp = { x = stick.x or 0, y = stick.y or 0 }
      if button then inp.buttons = button end
      local held, first = 0, nil
      local seq = {}
      for t = 1, 400 do
        if held < 3 then gd.input(1, inp, 1); held = held + 1 else gd.input(1, {}, 1) end
        gd.wait(1); nofault()
        local n = name()
        if #seq == 0 or seq[#seq] ~= n then seq[#seq + 1] = n end
        if n:sub(1, 5) ~= 'Cliff' and t > 8 then
          local p = gd.player(1)
          first = { n, p.x - R, p.y - top, p.ground_or_air or p.grounded }
          break
        end
      end
      if first then
        gd.wait(1)
        log('end %s %s via %s -> %s dx %.2f dy %.2f', speed, opt, table.concat(seq, '>'), first[1], first[2], first[3])
        if want_stage then
          chk(first[2] <= 1.0 and first[2] >= -INSIDE_MAX, string.format('%s %s: ended at dx %.1f (stage is dx < 0, within %d)', speed, opt, first[2], INSIDE_MAX))
          chk(math.abs(first[3]) <= 3.0, string.format('%s %s: ended dy %.1f off the stage top', speed, opt, first[3]))
        end
      else
        chk(false, speed .. ' ' .. opt .. ': stuck in Cliff')
      end
    end
    for _, speed in ipairs({ 'Quick', 'Slow' }) do
      local pct = speed == 'Quick' and 0 or 130
      run_option(speed, pct, 'getup', { x = -127 }, nil, true)
      run_option(speed, pct, 'attack', {}, 'A', true)
      run_option(speed, pct, 'roll', {}, 'R', true)
      run_option(speed, pct, 'jump', {}, 'X', false)
    end
    log('SUMMARY hang hand_min (Quick, CliffWait f10-70) = %s ; tolerance %.1f', tostring(hang_min), HAND_TOL)
    chk(hang_min ~= nil and hang_min <= HAND_TOL, string.format('hands %.1f from the ledge point on CliffWait (tolerance %.1f)', hang_min or -1, HAND_TOL))
    assert(#bads == 0, table.concat(bads, '; '))
  end)
  if ok then gd.log('LEDGEPOS RESULT PASS') else gd.log('LEDGEPOS RESULT FAIL ' .. tostring(why)) end
  gd.quit()
end)
