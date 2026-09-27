-- Live action sampling for the expanded Ultimate Kirby animation set.
-- @name: Ultimate Kirby expanded animation smoke
-- @version: 1.0.0
-- @gameplay: true

local tag = "ultimate-kirby expanded-animation"
local checks, failures = 0, 0

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s %s", tag, ok and "PASS" or "FAIL", label,
    detail or ""))
end

local function motion(p)
  return p and (p.motion_name or gd.motion_name(p.action, 1)) or "?"
end

local function step(spec)
  gd.input(1, spec or {}, 2)
  gd.wait(1)
  return gd.player(1)
end

local function drive(spec, frames)
  local seen, last = {}, nil
  for _ = 1, frames do
    last = step(spec)
    seen[motion(last)] = true
  end
  return seen, last
end

local function shot(label)
  local p = gd.player(1)
  gd.screenshot("ultimate-kirby-expanded-" .. label)
  gd.log(string.format("%s shot=%s action=%s motion=%s frame=%s",
    tag, label, p and p.action or "nil", motion(p), p and p.action_frame or "nil"))
end

local function has(seen, prefix)
  for name in pairs(seen) do
    if name:sub(1, #prefix) == prefix then return true end
  end
  return false
end

local function idle(timeout)
  return gd.wait_until(function()
    local p = gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, timeout)
end

local function main()
  check("spawn", gd.wait_until(function()
    local p = gd.match().active and gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 1200))
  if failures > 0 then return end
  gd.debug_draw(1, gd.draw.MODEL)
  gd.debug_draw(2, gd.draw.MODEL)
  gd.debug_stage(0)
  drive({}, 180)

  local guard = drive({buttons = "L"}, 18)
  check("guard visual state", has(guard, "Guard"))
  shot("guard")
  local roll = drive({buttons = "L", x = 127}, 18)
  check("forward roll visual state", has(roll, "EscapeF"))
  shot("roll")
  drive({}, 65)
  check("roll returns to idle", idle(120))

  local jab = {}
  for frame = 1, 150 do
    local p = step(frame % 3 == 1 and {buttons = "A"} or {})
    jab[motion(p)] = true
    if has(jab, "Attack100") then break end
  end
  check("rapid jab visual state", has(jab, "Attack100"))
  shot("rapid-jab")
  drive({}, 85)
  check("rapid jab returns to idle", idle(120))

  local inhale = drive({buttons = "B"}, 35)
  check("Inhale visual state", has(inhale, "SpecialN"))
  shot("inhale")
  drive({}, 95)
  check("Inhale returns to idle", idle(120))

  local stone = drive({buttons = "B", y = -127}, 2)
  local rest = drive({}, 36)
  for name in pairs(rest) do stone[name] = true end
  check("Stone visual state", has(stone, "SpecialLw"))
  shot("stone")
  drive({}, 20)
end

gd.run(function()
  local ok, err = pcall(main)
  if not ok then check("probe error", false, tostring(err)) end
  gd.input(1, {}, 2)
  gd.log(string.format("%s RESULT %s (%d/%d checks passed)", tag,
    failures == 0 and "PASS" or "FAIL", checks - failures, checks))
  gd.quit()
end)
