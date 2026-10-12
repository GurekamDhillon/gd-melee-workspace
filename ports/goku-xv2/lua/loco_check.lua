-- Locomotion gate (goku-stage playtest 2026-10-11, item 6): dash dance, run reverse, run stop, smash turn and tilt turn. Per row switch it logs the largest joint jump (facing-relative
-- joint positions against the fighter origin, frame to frame) and per row the pelvis (joint 4) travel against the fighter origin, so a pelvis that slides away from the collision
-- and a pose that pops at a switch show up. The same script runs on Captain Falcon as the reference: ledge_run.py --script loco_check --tag LOCOCHK [--p1 captain].
-- Lines: LOCOCHK row ... / LOCOCHK switch A>B jump J ... ; ends with LOCOCHK RESULT PASS|FAIL (gates below).
local PELVIS = 4
local MAX_PELVIS_RANGE = 7.0      -- pelvis travel (max - min, facing-relative) inside one Turn / TurnRun / RunBrake row; retail Falcon's rows measure up to 5.1 in this harness
local MAX_PELVIS_NET = 2.5        -- and where the row leaves it against where it started
local MAX_SWITCH_JUMP = 12.0      -- largest joint jump at a row switch, world-space against the fighter origin (retail Falcon's switches measure up to 10 here)
local function log(fmt, ...) gd.log('LOCOCHK ' .. string.format(fmt, ...)) end
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function tp(p, x, y) for i = 1, 80 do if pcall(gd.teleport, p, x, y) then return end gd.wait(30) end error('teleport') end
    local bads = {}
    local prev, prevname, rowstart, rowname, rowmin, rowmax
    local worst_jump, worst_drift, worst_net = 0, 0, 0
    local rowfirst, rowlast
    local function pose()
      local p = gd.player(1)
      local js = gd.joints(1) or {}
      local t = {}
      for i, j in ipairs(js) do if j.valid and j.x then t[i] = { j.x - p.x, j.y - p.y, (j.x - p.x) * (p.facing or 1) } end end
      return p, t
    end
    local function close_row()
      if rowname and rowmin then
        local drift = rowmax - rowmin
        local net = math.abs((rowlast or 0) - (rowfirst or 0))
        log('row %s frames %d pelvis travel %.2f net %.2f', rowname, rowstart or 0, drift, net)
        if rowname == 'Turn' or rowname == 'TurnRun' or rowname == 'RunBrake' then
          if drift > worst_drift then worst_drift = drift end
          if net > worst_net then worst_net = net end
        end
      end
    end
    local function step(inp, scenario)
      gd.input(1, inp, 1); gd.wait(1)
      local p, t = pose()
      local n = tostring(p.motion_name)
      local pel = t[PELVIS + 1]
      if n ~= rowname then
        close_row()
        local jump = 0
        if prev then
          for i, a in pairs(t) do
            local b = prev[i]
            if b then local d = math.sqrt((a[1] - b[1]) ^ 2 + (a[2] - b[2]) ^ 2); if d > jump then jump = d end end
          end
        end
        log('switch %s %s>%s jump %.2f (anim %s)', scenario, tostring(rowname), n, jump, tostring(p.anim_name))
        if rowname and jump > worst_jump then worst_jump = jump end
        rowname, rowmin, rowmax, rowstart, rowfirst, rowlast = n, nil, nil, 0, nil, nil
      end
      rowstart = (rowstart or 0) + 1
      if pel then rowmin = math.min(rowmin or pel[3], pel[3]); rowmax = math.max(rowmax or pel[3], pel[3]); rowfirst = rowfirst or pel[3]; rowlast = pel[3] end
      prev = t
    end
    local function reset(x)
      gd.input(1, {}, 1); gd.wait(2)
      tp(1, x or -60, 0); tp(2, 150, 0); gd.wait(40)
      gd.input(1, { x = 127 }, 3); gd.wait(3); gd.input(1, {}, 1); gd.wait(40)
      tp(1, x or -60, 0); gd.wait(20); prev, rowname = nil, nil
    end
    local function hold(inp, n, sc) for _ = 1, n do step(inp, sc) end end
    reset(0); hold({ x = 127 }, 6, 'dashdance'); hold({ x = -127 }, 6, 'dashdance'); hold({ x = 127 }, 6, 'dashdance'); hold({ x = -127 }, 6, 'dashdance'); hold({}, 40, 'dashdance'); close_row()
    reset(-45); hold({ x = 127 }, 40, 'runreverse'); hold({ x = -127 }, 30, 'runreverse'); hold({}, 40, 'runreverse'); close_row()
    reset(-45); hold({ x = 127 }, 40, 'runstop'); hold({}, 40, 'runstop'); close_row()
    reset(0); hold({ x = -127 }, 3, 'smashturn'); hold({ x = -127 }, 25, 'smashturn'); hold({}, 30, 'smashturn'); close_row()
    reset(0); hold({ x = 127 }, 3, 'tiltturn0'); hold({}, 20, 'tiltturn0'); hold({ x = -35 }, 18, 'tiltturn'); hold({}, 30, 'tiltturn'); close_row()
    log('SUMMARY worst switch jump %.2f (gate %.1f), worst pelvis travel in a turn/brake row %.2f (gate %.1f), worst net %.2f (gate %.1f)', worst_jump, MAX_SWITCH_JUMP, worst_drift, MAX_PELVIS_RANGE, worst_net, MAX_PELVIS_NET)
    if worst_jump > MAX_SWITCH_JUMP then bads[#bads + 1] = string.format('switch jump %.2f > %.1f', worst_jump, MAX_SWITCH_JUMP) end
    if worst_drift > MAX_PELVIS_RANGE then bads[#bads + 1] = string.format('pelvis travel %.2f > %.1f', worst_drift, MAX_PELVIS_RANGE) end
    if worst_net > MAX_PELVIS_NET then bads[#bads + 1] = string.format('pelvis net drift %.2f > %.1f', worst_net, MAX_PELVIS_NET) end
    assert(#bads == 0, table.concat(bads, '; '))
  end)
  if ok then gd.log('LOCOCHK RESULT PASS') else gd.log('LOCOCHK RESULT FAIL ' .. tostring(why)) end
  gd.quit()
end)
