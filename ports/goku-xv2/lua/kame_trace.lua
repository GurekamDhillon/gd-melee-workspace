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
    press({buttons = 'B'}, 2)
    if SCEN == 'tap' then step(2); press({buttons = 'B'}, 2); step(120)
    elseif SCEN == 'shield30' then step(32); press({buttons = 'L'}, 2); step(80)
    elseif SCEN == 'roll' then step(32); gd.input(1, {x = 0}, 1); gd.wait(1); gd.input(1, {x = 127}, 3); step(90)
    elseif SCEN == 'jump' then step(32); press({buttons = 'X'}, 2); step(80)
    elseif SCEN == 'full' then step(260)
    elseif SCEN == 'stored' then step(32); press({buttons = 'L'}, 2); step(80); press({buttons = 'B'}, 2); step(120)
    end
    gd.log('KTRACE DONE ' .. WHO .. ' ' .. SCEN)
  end)
  if not ok then gd.log('KTRACE FAIL ' .. tostring(why)) end
  gd.quit()
end)
