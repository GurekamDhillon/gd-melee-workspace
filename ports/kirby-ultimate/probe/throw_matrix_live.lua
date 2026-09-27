-- Four real grabs and throws in one LAB match, restored from one neutral state.
-- @name: Ultimate Kirby live throw matrix
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby throw-matrix", 0, 0
local variants = {
  {name = "forward", motion = "ThrowF", damage = 5,
   stick = function(facing) return {x = facing * 127} end},
  {name = "back", motion = "ThrowB", damage = 8,
   stick = function(facing) return {x = -facing * 127} end},
  {name = "up", motion = "ThrowHi", damage = 10,
   stick = function() return {y = 127} end},
  {name = "down", motion = "ThrowLw", damage = 2,
   stick = function() return {y = -127} end},
}

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function step(spec, motions)
  gd.input(1, spec, 2)
  gd.input(2, {}, 2)
  gd.wait(1)
  local p = gd.player(1)
  if p then motions[p.motion_name or tostring(p.action)] = true end
end

local function drive(spec, frames, motions)
  for _ = 1, frames do step(spec, motions) end
end

local function main()
  local ready = gd.wait_until(function()
    local p1, p2 = gd.player(1), gd.player(2)
    return gd.match().active and p1 and p1.action == 14 and
      not p1.airborne and p2 and p2.action == 14
  end, 1200)
  check("spawn", ready)
  if not ready then return end
  check("own slot", gd.player(1).char_name == "ultimate kirby")
  for _ = 1, 300 do
    local p1, p2 = gd.player(1), gd.player(2)
    local gap = p2.x - p1.x
    if math.abs(gap) < 8 then break end
    step({x = gap > 0 and 45 or -45}, {})
  end
  drive({}, 8, {})
  local gap = math.abs(gd.player(2).x - gd.player(1).x)
  check("neutral grab setup", gap < 12,
    string.format("gap=%.2f", gap))
  if gap >= 12 then return end

  gd.savestate(2)
  drive({}, 8, {}) -- save happens at the next frame boundary; settle pad overrides
  for index, variant in ipairs(variants) do
    if index > 1 then
      gd.loadstate(2)
      drive({}, 8, {}) -- load happens at the next frame boundary
    end
    local own, victim = gd.player(1), gd.player(2)
    local neutral = own and victim and own.action == 14 and
      victim.action == 14 and math.abs(victim.x - own.x) < 12 and
      victim.percent == 0
    check(variant.name .. " reset", neutral,
      string.format("own=%s victim=%s pct=%s", tostring(own and own.action),
        tostring(victim and victim.action), tostring(victim and victim.percent)))
    if not neutral then return end

    local grab = {}
    drive({buttons = "Z"}, 1, grab)
    local z = gd.pad(1)
    gd.log(string.format("%s trace %s Z=%s action=%s", tag, variant.name,
      tostring(z and z.Z), tostring((gd.player(1) or {}).action)))
    drive({}, 32, grab)
    check(variant.name .. " grab", grab.CatchWait,
      string.format("own=%s victim=%s", tostring((gd.player(1) or {}).action),
        tostring((gd.player(2) or {}).action)))
    if not grab.CatchWait then return end

    local motions, max_damage = {}, 0
    step(variant.stick(gd.player(1).facing or 1), motions)
    for _ = 1, 85 do
      step({}, motions)
      local p2 = gd.player(2)
      if p2 then max_damage = math.max(max_damage, p2.percent) end
    end
    check(variant.name .. " action", motions[variant.motion])
    check(variant.name .. " hit", max_damage >= variant.damage and
      max_damage <= (variant.name == "down" and 35 or variant.damage + 5),
      string.format("peak victim damage %.1f%%", max_damage))
  end
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
