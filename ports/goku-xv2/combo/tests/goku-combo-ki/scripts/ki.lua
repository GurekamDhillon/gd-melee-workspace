-- @name: Goku ki gates (geno 11 combo meter + the ki-gated moves of lua/goku_ki.lua)
-- @gameplay: true
-- P1 Goku, P2 Mario standing apart (human ports). Every test loads the same savestate, sets the meter with gd.combo_ki and plays pad input:
--   kicharge   : hold down-B 150 frames from ki 0 -> the meter rises (0.8 a frame once KiCharge runs): at least 60 afterwards
--   counter-lo : ki 5, tap down-B  -> the vanish needs 10: the move ends (Counter is left within 8 frames)
--   counter-ok : ki 50, tap down-B, P2 jabs inside the window -> Riposte is entered and the meter drops by 10
--   super-ok   : ki 100, hold B 75 frames, release -> KameSuper is entered and spends 100 (meter back near 0: the hit gives a little)
--   super-lo   : ki 99, the same -> KameFull, not KameSuper, the meter is untouched
-- Output: KITEST lines and "KITEST RESULT: PASS" / "FAIL <tests>".
local function log(fmt, ...) gd.log("KITEST " .. string.format(fmt, ...)) end
local phase, t, ti, quit_t = "boot", 0, 1, 0
local failed, seen = {}, nil

local TESTS = {
  { id = "kicharge", ki = 0, frames = 190,
    run = function(f, p1) if f <= 150 then gd.input(1, { buttons = "B", y = -127 }, 1) end end,
    check = function(r) return r.ki_end >= 60 and r.max_ki >= 60, string.format("ki_end=%.1f", r.ki_end) end },
  { id = "counter-lo", ki = 5, frames = 40,
    run = function(f) if f == 2 then gd.input(1, { buttons = "B", y = -127 }, 1) end end, -- a one-frame tap: special_held is false at action frame 2
    check = function(r) return not r.counter_at_16 and not r.riposte, string.format("counter_at_16=%s riposte=%s", tostring(r.counter_at_16), tostring(r.riposte)) end },
  { id = "counter-ok", ki = 50, frames = 80,
    run = function(f, p1, p2)
      if f == 2 then gd.input(1, { buttons = "B", y = -127 }, 1) end
      if f == 6 then gd.input(2, { buttons = "A" }, 2) end
    end,
    check = function(r) return r.riposte and r.min_ki <= 42, string.format("riposte=%s min_ki=%.1f (50 - 10 for the vanish + 1.5 for the hit taken) ki_end=%.1f", tostring(r.riposte), r.min_ki, r.ki_end) end },
  { id = "super-ok", ki = 100, frames = 140,
    run = function(f) if f >= 2 and f <= 76 then gd.input(1, { buttons = "B" }, 1) end end,
    check = function(r) return r.super and r.ki_end <= 8, string.format("super=%s ki_end=%.1f", tostring(r.super), r.ki_end) end },
  { id = "super-lo", ki = 99, frames = 140,
    run = function(f) if f >= 2 and f <= 76 then gd.input(1, { buttons = "B" }, 1) end end,
    check = function(r) return (not r.super) and r.full and r.ki_end > 98, string.format("super=%s full=%s ki_end=%.1f", tostring(r.super), tostring(r.full), r.ki_end) end },
}

local res
function on_frame()
  if phase == "end" then
    quit_t = quit_t + 1
    if quit_t == 30 then gd.quit() end
    return
  end
  if not gd.match().active then return end
  local p1, p2 = gd.player(1), gd.player(2)
  if not p1 or not p2 then return end
  t = t + 1
  if phase == "boot" then
    if gd.combo(1) == nil then
      gd.log("KITEST RESULT: FAIL no combo graph")
      phase = "end"
      return
    end
    if t >= 30 then phase, t = "place", 0 end
    return
  end
  if phase == "place" then
    if t == 40 then gd.teleport(1, -20, 0) gd.teleport(2, -14, 0) end
    if t == 100 then gd.savestate(1) end
    if t == 104 then phase, t = "load", 0 end
    return
  end
  local T = TESTS[ti]
  if T == nil then
    gd.log(#failed == 0 and "KITEST RESULT: PASS" or ("KITEST RESULT: FAIL " .. table.concat(failed, " ")))
    phase = "end"
    return
  end
  if phase == "load" then
    if t == 1 then gd.loadstate(1) end
    if t == 5 then gd.combo_ki(1, T.ki) end
    if t == 8 then
      res = { max_ki = 0, ki_end = 0, min_ki = 1e9 }
      phase, t = "run", 0
    end
    return
  end
  if phase == "run" then
    T.run(t, p1, p2)
    if T.id == 'kicharge' and t % 10 == 0 then log('trace f=%d p1=%s af=%s ki=%.1f', t, tostring(p1.motion_name), tostring(p1.action_frame), (gd.combo(1) or {}).ki or -1) end
    if false then log('trace f=%d p1=%s af=%s p2=%s (%.1f vs %.1f)', t, tostring(p1.motion_name), tostring(p1.action_frame), tostring(p2.motion_name), p1.x, p2.x) end
    local m = p1.motion_name or ""
    local c = gd.combo(1)
    local ki = c and c.ki or 0
    if ki > res.max_ki then res.max_ki = ki end
    if ki < res.min_ki then res.min_ki = ki end
    res.ki_end = ki
    if m == "Counter" and t == 16 then res.counter_at_16 = true end
    if m == "Riposte" then res.riposte = true end
    if m == "KameSuper" then res.super = true end
    if m == "KameFull" then res.full = true end
    if m == "KiCharge" then res.kicharge = true end
    if t >= T.frames then
      local ok, why = T.check(res)
      log("test=%s ki0=%d %s motion_end=%s -> %s", T.id, T.ki, why, m, ok and "PASS" or "FAIL")
      if not ok then failed[#failed + 1] = T.id end
      ti = ti + 1
      phase, t = "load", 0
    end
  end
end
