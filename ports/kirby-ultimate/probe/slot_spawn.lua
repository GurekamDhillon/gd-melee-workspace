-- Spawn smoke test for an explicitly staged Ultimate Kirby m-ex slot.
-- @name: Ultimate Kirby slot spawn
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby slot", 0, 0

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function main()
  local ready = gd.wait_until(function()
    local p = gd.match().active and gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 1200)
  check("spawn", ready, "P1 reaches grounded Wait")
  if not ready then return end
  local p = gd.player(1)
  gd.log(string.format("%s TRACE character=%s kind=%s costume=%s action=%s",
    tag, tostring(p.char_name), tostring(p.kind), tostring(p.costume), tostring(p.action)))
  check("own fighter", p.char_name and p.char_name:lower() == "ultimate kirby",
    "MxDt name resolves to this slot")
  check("costume 0", p.costume == 0, "c00 model archive loads")
  check("LAB", gd.lab_mode and gd.lab_mode())
  local x = p.x
  for _ = 1, 25 do gd.input(1, {x = 45}, 2); gd.wait(1) end
  p = gd.player(1)
  check("walk", p.x > x + 0.5, string.format("x %.2f -> %.2f", x, p.x))
end

gd.run(function()
  local ok, err = pcall(main)
  if not ok then check("probe error", false, tostring(err)) end
  gd.input(1, {}, 2)
  gd.log(string.format("%s RESULT %s (%d/%d checks passed)",
    tag, failures == 0 and "PASS" or "FAIL", checks - failures, checks))
  gd.quit()
end)
