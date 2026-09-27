-- Native-slot neutral-B inhale, swallow, and Fox copy input route.
-- @name: Ultimate Kirby Inhale control
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby inhale", 0, 0

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function sample(spec1, spec2, frames, names)
  for _ = 1, frames do
    gd.input(1, spec1, 2)
    gd.input(2, spec2, 2)
    gd.wait(1)
    local p = gd.player(1)
    if p then names[p.motion_name or "?"] = true end
  end
end

local function seen(names, part)
  for name in pairs(names) do
    if string.find(name, part, 1, true) then return true end
  end
  return false
end

local function list(names)
  local out = {}
  for name in pairs(names) do out[#out + 1] = name end
  table.sort(out)
  return table.concat(out, ",")
end

local function main()
  local ready = gd.wait_until(function()
    local p = gd.match().active and gd.player(1)
    return p and p.action == 14 and not p.airborne and gd.player(2)
  end, 1200)
  check("spawn with Fox", ready)
  if not ready then return end
  check("own slot", gd.player(1).char_name == "ultimate kirby")

  local approach = {}
  for _ = 1, 75 do
    local p1, p2 = gd.player(1), gd.player(2)
    if math.abs(p2.x - p1.x) < 19 then break end
    sample({}, {x = p2.x > p1.x and -70 or 70}, 1, approach)
  end
  local gap = math.abs(gd.player(2).x - gd.player(1).x)
  check("Fox approaches inhale range", gap < 23, string.format("gap %.1f", gap))
  if gap >= 23 then return end

  local inhale = {}
  sample({buttons = "B"}, {}, 100, inhale)
  check("Inhale startup", seen(inhale, "SpecialN"), list(inhale))
  check("Inhale hold/capture", seen(inhale, "SpecialNLoop") or seen(inhale, "Eat"), list(inhale))
  check("Fox captured", seen(inhale, "Eat"), list(inhale))
  if not seen(inhale, "Eat") then return end

  sample({}, {}, 2, inhale)
  local swallow = {}
  sample({buttons = "B"}, {}, 1, swallow)
  sample({}, {}, 65, swallow)
  check("swallow action", seen(swallow, "SpecialNDrink"), list(swallow))
  local recovered = gd.wait_until(function()
    local p = gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 120)
  check("swallow recovery", recovered)
  if not recovered then return end

  local copied = {}
  sample({buttons = "B"}, {}, 1, copied)
  sample({}, {}, 48, copied)
  check("Fox copy action", seen(copied, "FxSpecialN"), list(copied))
end

gd.run(function()
  local ok, err = pcall(main)
  if not ok then check("probe error", false, tostring(err)) end
  gd.input(1, {}, 2)
  gd.input(2, {}, 2)
  gd.log(string.format("%s RESULT %s (%d/%d checks passed)",
    tag, failures == 0 and "PASS" or "FAIL", checks - failures, checks))
  gd.quit()
end)
