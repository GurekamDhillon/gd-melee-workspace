-- Tilt first-active-frame gate (goku-stage playtest 2026-10-11, items 1 and 2): utilt's hitboxes start on action frame 8 and ftilt's on 5, and utilt's sphere sits on the striking hand
-- (hand.R, joint 25; the earlier build had them on hand.L, joint 49). Lines: TILTCHECK ... ; ends with TILTCHECK RESULT PASS|FAIL.
local WANT = { utilt = 8, ftilt = 5 }
local TOL = 1     -- the script frame and the engine's action_frame count differ by at most one
local function log(fmt, ...) gd.log('TILTCHECK ' .. string.format(fmt, ...)) end
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function tp(p, x, y) for i = 1, 80 do if pcall(gd.teleport, p, x, y) then return end gd.wait(30) end error('teleport') end
    local bads = {}
    for _, mv in ipairs({ 'utilt', 'ftilt' }) do
      for rep = 1, 2 do
        gd.input(1, {}, 1); gd.wait(2)
        tp(1, 0, 0); tp(2, 140, 0); gd.wait(40)
        gd.input(1, { x = 127 }, 3); gd.wait(3); gd.input(1, {}, 1); gd.wait(30)   -- face right
        tp(1, 0, 0); gd.wait(20)
        local inp = mv == 'utilt' and { y = 100, buttons = 'A' } or { x = 80, buttons = 'A' }
        gd.input(1, inp, 2)
        local first, hand = nil, nil
        for t = 1, 60 do
          gd.wait(1)
          local p = gd.player(1)
          local hbs = gd.hitboxes(1) or {}
          if #hbs > 0 and not first then
            first = p.action_frame or t
            local js = gd.joints(1) or {}
            local h = hbs[1]
            local best, bj = 1e9, nil
            for _, ji in ipairs({ 25, 49 }) do
              local j = js[ji + 1]
              if j and j.x then
                local d = math.sqrt((j.x - h.x) ^ 2 + (j.y - h.y) ^ 2)
                if d < best then best, bj = d, ji end
              end
            end
            hand = bj
            log('%s rep%d: first active frame %s (motion %s), nearest hand joint %s (%.2f)', mv, rep, tostring(first), tostring(p.motion_name), tostring(bj), best)
          end
          if first and #hbs == 0 then break end
        end
        if not first then bads[#bads + 1] = mv .. ': never active' else
          if math.abs(first - WANT[mv]) > TOL then bads[#bads + 1] = string.format('%s first active frame %d, want %d', mv, first, WANT[mv]) end
          if mv == 'utilt' and hand ~= 25 then bads[#bads + 1] = 'utilt sphere is nearest hand joint ' .. tostring(hand) .. ', want 25 (hand.R)' end
        end
        gd.wait(60)
      end
    end
    assert(#bads == 0, table.concat(bads, '; '))
  end)
  if ok then gd.log('TILTCHECK RESULT PASS') else gd.log('TILTCHECK RESULT FAIL ' .. tostring(why)) end
  gd.quit()
end)
