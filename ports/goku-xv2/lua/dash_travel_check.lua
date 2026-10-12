-- Dash grab / dash attack travel gate (goku-stage playtest 2026-10-11, item 5) and standing grab reach (item 4).
-- From a dash (Dash, action frame 3) press Z (dash grab) or A (dash attack) and log per frame the motion, x and velocity; travel = x at the end of the attack minus x at the press.
-- Also the standing grab (Z from Wait): the active hitboxes' reach in front of the fighter (facing-signed hit x + radius). Lines: DASHTRAVEL ... ; ends with DASHTRAVEL RESULT PASS|FAIL.
-- Goku and the retail reference run the same script: ledge_run.py --script dash_travel_check --tag DASHTRAVEL [--p1 captain] .
-- Goku passes when the travel is > MIN_TRAVEL and within TRAVEL_RATIO (0.5 .. 2.0) of the value in REF below (Captain Falcon's, measured in this harness), and the grab reach >= GRAB_REACH_MIN.
local REF = { dash_grab = nil, dash_attack = nil }     -- filled from the Falcon reference run (see the commit message)
local MIN_TRAVEL, GRAB_REACH_MIN = 1.0, 0.0
local function log(fmt, ...) gd.log('DASHTRAVEL ' .. string.format(fmt, ...)) end
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
    local sb = assert(gd.stage_bounds(), 'no stage bounds')
    local bads = {}
    local function chk(c, m) if not c then bads[#bads + 1] = m; gd.log('DASHTRAVEL FAIL ' .. m) end end
    local function reset()
      gd.input(1, {}, 1); gd.wait(2)
      tp(1, -60, 0); tp(2, 150, 0)
      gd.wait(40)
      gd.input(1, { x = 127 }, 3); gd.wait(3); gd.input(1, {}, 1); gd.wait(30)   -- face right
      tp(1, -60, 0); gd.wait(30)
    end
    local results = {}
    for _, kind in ipairs({ 'dash_grab', 'dash_attack' }) do
      local btn = kind == 'dash_grab' and 'Z' or 'A'
      for rep = 1, 2 do
        reset()
        local pressed = false
        local x0, name0, f0
        for t = 1, 40 do
          gd.input(1, { x = 127 }, 1); gd.wait(1)
          local p = gd.player(1)
          if name() == 'Dash' and (p.action_frame or 0) >= 3 + rep * 3 then
            local q = gd.player(1)
            x0 = q.x; f0 = q.vel_x
            gd.input(1, { x = 0, buttons = btn }, 1); gd.wait(1); pressed = true; break
          end
        end
        chk(pressed, kind .. ': never in Dash')
        if pressed then
          local seq, last, vlog, maxreach = {}, nil, {}, -99
          local xe, n_att = x0, 0
          for t = 1, 100 do
            gd.input(1, {}, 1); gd.wait(1)
            local p = gd.player(1)
            local n = name()
            if n ~= last then seq[#seq + 1] = n; last = n end
            if n:sub(1, 6) == 'Attack' or n:sub(1, 5) == 'Catch' then xe = p.x; n_att = n_att + 1 end
            if t <= 24 and t % 2 == 0 then vlog[#vlog + 1] = string.format('%s%.2f/%.2f', '', p.x - x0, p.vel_x or -9) end
            for _, h in ipairs(gd.hitboxes(1) or {}) do
              local r = ((h.x or 0) - p.x) * (p.facing or 1) + (h.size or h.radius or 0)
              if r > maxreach then maxreach = r end
            end
            if t > 6 and n:sub(1, 6) ~= 'Attack' and n:sub(1, 5) ~= 'Catch' and n ~= 'Dash' then break end
          end
          local travel = xe - x0
          log('%s rep%d: vel_x at press %.3f travel %.2f over %d frames; hitbox reach %.2f; motions %s; (x-x0 / vel every 2 frames) %s', kind, rep, f0 or -9, travel, n_att, maxreach, table.concat(seq, '>'), table.concat(vlog, ' '))
          results[kind] = math.max(results[kind] or -1e9, travel)
          chk(travel > MIN_TRAVEL, string.format('%s rep%d travelled %.2f (<= %.1f): stops dead', kind, rep, travel, MIN_TRAVEL))
        end
      end
      if REF[kind] and results[kind] then
        chk(results[kind] >= 0.5 * REF[kind] and results[kind] <= 2.0 * REF[kind], string.format('%s travel %.2f not within 0.5..2x of the reference %.2f', kind, results[kind], REF[kind]))
      end
    end
    -- standing grab reach
    reset(); gd.wait(20)
    local best, first_active, seq = -99, nil, {}
    gd.input(1, { buttons = 'Z' }, 1); gd.wait(1)
    for t = 1, 40 do
      gd.input(1, {}, 1); gd.wait(1)
      local p = gd.player(1)
      for _, h in ipairs(gd.hitboxes(1) or {}) do
        local r = ((h.x or 0) - p.x) * (p.facing or 1) + (h.size or h.radius or 0)
        first_active = first_active or t
        if r > best then best = r end
        if t == first_active then log('grab hitbox f%d: x %.2f y %.2f radius %.2f (fighter x %.2f y %.2f)', t, h.x - p.x, h.y - p.y, h.size or h.radius or 0, p.x, p.y) end
      end
    end
    log('standing grab: first active frame %s, reach in front %.2f units', tostring(first_active), best)
    chk(best >= GRAB_REACH_MIN, string.format('standing grab reach %.2f < %.1f', best, GRAB_REACH_MIN))
    assert(#bads == 0, table.concat(bads, '; '))
  end)
  if ok then gd.log('DASHTRAVEL RESULT PASS') else gd.log('DASHTRAVEL RESULT FAIL ' .. tostring(why)) end
  gd.quit()
end)
