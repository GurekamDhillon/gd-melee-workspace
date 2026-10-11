-- Frame-by-frame traces of the charge move for retail Samus, retail Mewtwo and Goku, same inputs. Config: CFG.who (tag), CFG.scen (tap|shield30|roll|jump|full|stored).
-- Prints "KTRACE who scen t=<frame since the first B> motion af=<action frame> grounded" every frame whose motion changes, plus a state line each 10 frames.
local C = CFG or {}
local WHO, SCEN = C.who or 'x', C.scen or 'tap'
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    gd.input(1, {}, 1); gd.wait(2)
    gd.teleport(1, 0, 0); gd.teleport(2, 60, 0); gd.wait(40)
    local last, t0 = nil, 0
    local function step(n)
      for i = 1, n do
        gd.wait(1); t0 = t0 + 1
        local p = gd.player(1)
        local m = tostring(p.motion_name)
        if m ~= last then gd.log(string.format('KTRACE %s %s t=%d -> %s af=%s air=%s', WHO, SCEN, t0, m, tostring(p.action_frame), tostring(p.air))) last = m end
      end
    end
    local function press(spec, n) gd.input(1, spec, n or 2) end
    -- measure the floor's right edge (walk off it) for the ledge scenarios
    local EDGE
    local function tp(port, x, y)   -- a fighter that fell off is dead / respawning for a while: retry
      for i = 1, 60 do
        if pcall(gd.teleport, port, x, y) then return end
        gd.wait(30)
      end
      error('could not teleport port ' .. port)
    end
    local function find_edge()
      tp(1, 40, 0); gd.wait(5)
      for i = 1, 200 do
        gd.input(1, {x = 127}, 1); gd.wait(1)
        local q = gd.player(1)
        local m = tostring(q.motion_name)
        if m:find('Fall') or m:find('Cliff') or (q.y and q.y < -0.5) then return q.x end
      end
      return nil
    end
    local function reset_ground(x, y) gd.input(1, {}, 1); gd.wait(2); tp(1, x, y or 0); tp(2, x - 60, 0); gd.wait(40) end
    local at = tonumber(C.at or 32)
    local scen_n = SCEN:match('^(%a+)')
    if SCEN == 'ledge_fwd' or SCEN == 'ledge_back' or SCEN == 'takeoff' then
      EDGE = find_edge(); gd.log('KTRACE ' .. WHO .. ' ' .. SCEN .. ' edge x=' .. tostring(EDGE))
      assert(EDGE, 'no edge found')
      gd.wait(60); gd.input(1, {}, 1); gd.wait(2); tp(1, 0, 0); gd.wait(200)   -- it fell off and respawns
    end
    if scen_n == 'airjump' or SCEN == 'land' then reset_ground(0, 0); gd.teleport(1, 0, SCEN == 'land' and 18 or 45); gd.wait(3) end
    if SCEN == 'ledge_fwd' or SCEN == 'ledge_back' then
      tp(1, EDGE - 2, -4); tp(2, 0, 0); gd.wait(2)
    end
    if SCEN == 'takeoff' then tp(1, EDGE - 30, 0); gd.wait(30); gd.input(1, {x = 127}, 18) ; step(16) end
    press({buttons = 'B'}, 2)
    if SCEN == 'ledge_fwd' then gd.input(1, {x = -127}, 90); step(90)   -- the stage is to the left of the edge: toward it
    elseif SCEN == 'ledge_back' then gd.input(1, {x = 127}, 40); step(90)
    elseif SCEN == 'takeoff' then step(120)
    elseif SCEN == 'land' then step(120)
    elseif scen_n == 'jump' or scen_n == 'airjump' then
      step(at)
      local k = C.key or 'X'
      if k == 'up' then gd.input(1, {y = 127}, 3) else press({buttons = k}, 2) end
      step(100)
      local lua = gd.fighter_lua(1)
      gd.log(string.format('KTRACE %s %s end: motion=%s charge=%s stored=%s', WHO, SCEN, tostring(gd.player(1).motion_name), tostring(lua and lua.state and lua.state.charge), tostring(lua and lua.state and lua.state.stored)))
    elseif SCEN == 'tap' then step(15); press({buttons = 'B'}, 2); step(120)
    elseif SCEN == 'shield30' then step(32); press({buttons = 'L'}, 2); step(80)
    elseif SCEN == 'roll' then step(32); gd.input(1, {x = 0}, 1); gd.wait(1); gd.input(1, {x = 127}, 3); step(90)
    elseif SCEN == 'full' then step(260)
    elseif SCEN == 'stored' then step(32); press({buttons = 'L'}, 2); step(80); press({buttons = 'B'}, 2); step(120)
    end
    gd.log('KTRACE DONE ' .. WHO .. ' ' .. SCEN)
  end)
  if not ok then gd.log('KTRACE FAIL ' .. tostring(why)) end
  gd.quit()
end)
