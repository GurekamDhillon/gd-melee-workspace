-- Exercise common host states around the additive Ultimate Kirby slot in one match.
-- @name: Ultimate Kirby native regression
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby native-regression", 0, 0

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function step(p1, p2)
  -- gd.input counts PADRead samples, several of which can occur per logic frame.
  -- Keep each override alive until the next explicit spec, including stick changes.
  gd.input(1, p1 or {x = 0, y = 0}, 1000)
  gd.input(2, p2 or {x = 0, y = 0}, 1000)
  gd.wait(1)
  return gd.player(1), gd.player(2)
end

local function drive(p1, p2, frames)
  local a, b
  for _ = 1, frames do a, b = step(p1, p2) end
  return a, b
end

local function reset()
  gd.loadstate(2)
  drive({}, {}, 8) -- load occurs on the next boundary; clear both pad overrides
  local a, b = gd.player(1), gd.player(2)
  return a and b and a.action == 14 and b.action == 14 and
    a.percent == 0 and b.percent == 0
end

local function main()
  local ready = gd.wait_until(function()
    local a, b = gd.player(1), gd.player(2)
    return gd.match().active and a and b and a.action == 14 and
      b.action == 14 and not a.airborne and not b.airborne
  end, 1200)
  check("spawn", ready)
  if not ready then return end
  check("additive slot", gd.player(1).char_name == "ultimate kirby")

  -- Put a human Fox within jab range while preserving normal facing/physics.
  for _ = 1, 300 do
    local a, b = gd.player(1), gd.player(2)
    if math.abs(b.x - a.x) < 9 then break end
    step({x = 0, y = 0}, {x = b.x > a.x and -45 or 45, y = 0})
  end
  drive({}, {}, 8)
  local a, b = gd.player(1), gd.player(2)
  check("jab range", math.abs(b.x - a.x) < 11,
    string.format("gap=%.2f", math.abs(b.x - a.x)))
  if math.abs(b.x - a.x) >= 11 then return end
  gd.savestate(2)
  drive({}, {}, 8)

  local guards, peak = {}, 0
  drive({buttons = "L", x = 0, y = 0}, {}, 12)
  for frame = 1, 35 do
    a = step({buttons = "L", x = 0, y = 0},
             frame <= 8 and {buttons = "A", x = 0, y = 0} or {x = 0, y = 0})
    if a then
      guards[a.motion_name or tostring(a.action)] = true
      peak = math.max(peak, a.percent)
    end
  end
  local guard_seen = false
  for name in pairs(guards) do
    if name:sub(1, 5) == "Guard" then guard_seen = true end
  end
  check("guard action", guard_seen)
  check("shielded jab no damage", peak == 0, string.format("peak=%.1f", peak))

  check("reset after shield", reset())
  local damage_seen, damage_peak = false, 0
  for frame = 1, 35 do
    a = step({x = 0, y = 0},
             frame <= 8 and {buttons = "A", x = 0, y = 0} or {x = 0, y = 0})
    if a then
      damage_peak = math.max(damage_peak, a.percent)
      if (a.motion_name or ""):sub(1, 6) == "Damage" then damage_seen = true end
    end
  end
  check("Fox jab damages Kirby", damage_peak > 0,
    string.format("peak=%.1f", damage_peak))
  check("damage action", damage_seen)

  check("reset after damage", reset())
  local roll_seen = false
  drive({buttons = "L", x = 0, y = 0}, {}, 8)
  local facing = (gd.player(1) or {}).facing or 1
  for frame = 1, 30 do
    a = step(frame <= 8 and {buttons = "L", x = facing * 127, y = 0} or
             {x = 0, y = 0}, {})
    if a and (a.motion_name or ""):sub(1, 7) == "EscapeF" then
      roll_seen = true
    end
  end
  check("out-of-shield roll", roll_seen)
end

gd.run(function()
  local ok, err = pcall(main)
  if not ok then check("probe error", false, tostring(err)) end
  gd.input(1, {}, 1000)
  gd.input(2, {}, 1000)
  gd.log(string.format("%s RESULT %s (%d/%d checks passed)",
    tag, failures == 0 and "PASS" or "FAIL", checks - failures, checks))
  gd.quit()
end)
