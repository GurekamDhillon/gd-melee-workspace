-- Pad takeover gate: opening and closing the LAB menu must not leave the human's pad claimed by the LAB.
-- A state machine on on_tick (a task would stall: the open menu pauses the logic frames gd.wait counts). It claims P1 itself (START opens the menu,
-- B closes it), releases its own claim, then claims P1 once more. If the LAB still owns the port at that moment the engine logs
-- "pad: P1 script release (owner N)" between the PADCHECK markers; tools/run_lua_check.py fails on it.
-- Scene: mode=lab;p1=geno:goku-xv2/hu;p2=mario/cpu0 .
local t, started = 0, false
function on_tick()
  if not started then
    local m = gd.match()
    if not (m and m.active and m.frame > 90) then return end
    started = true
  end
  t = t + 1
  if t == 30 then gd.input(1, { buttons = 'START' }, 3)
  elseif t == 120 then gd.input(1, { buttons = 'B' }, 3)          -- the menu closes (menu_close holds the ports neutral for 10 frames)
  elseif t == 400 then for p = 1, 4 do gd.release(p) end
  elseif t == 700 then gd.log('PADCHECK released')                -- the LAB's own hold has run out
  elseif t == 702 then gd.input(1, {}, 1)                         -- a second claim: logs "script release (owner N)" first when someone else still owns P1
  elseif t == 720 then gd.release(1)
  elseif t == 740 then gd.log('PADCHECK END') gd.quit() end
end
