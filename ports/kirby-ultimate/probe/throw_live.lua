-- Real input and collision check for Ultimate Kirby's grab and four throws.
-- Fox costume 0/1/2/3 selects forward/back/up/down for isolated LAB runs.
-- @name: Ultimate Kirby live throw
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby throw-live", 0, 0
local variants = {
  [0] = {name = "forward", motion = "ThrowF", damage = 5, stick = function(f) return {x = f * 127} end},
  [1] = {name = "back", motion = "ThrowB", damage = 8, stick = function(f) return {x = -f * 127} end},
  [2] = {name = "up", motion = "ThrowHi", damage = 10, stick = function() return {y = 127} end},
  [3] = {name = "down", motion = "ThrowLw", damage = 2, stick = function() return {y = -127} end},
}

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function drive(spec, frames, seen)
  for _ = 1, frames do
    gd.input(1, spec, 2)
    gd.input(2, {}, 2)
    gd.wait(1)
    local p = gd.player(1)
    if p then seen[p.motion_name or tostring(p.action)] = true end
  end
end

local function names(seen)
  local out = {}
  for name in pairs(seen) do out[#out + 1] = name end
  table.sort(out)
  return table.concat(out, ",")
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
  local variant = variants[gd.player(2).costume]
  check("throw variant", variant ~= nil,
    string.format("Fox costume=%s", tostring(gd.player(2).costume)))
  if not variant then return end

  for _ = 1, 300 do
    local p1, p2 = gd.player(1), gd.player(2)
    local gap = p2.x - p1.x
    if math.abs(gap) < 8 then break end
    drive({x = gap > 0 and 45 or -45}, 1, {})
  end
  drive({}, 8, {})
  local p1, p2 = gd.player(1), gd.player(2)
  local gap = p2.x - p1.x
  check("grab range", math.abs(gap) < 12,
    string.format("gap=%.2f facing=%s", gap, tostring(p1.facing)))
  if math.abs(gap) >= 12 then return end

  local before = p2.percent
  local grab = {}
  drive({buttons = "Z"}, 1, grab)
  drive({}, 32, grab)
  local held = gd.player(1)
  check("standing grab input", grab.Catch or grab.CatchPull or grab.CatchWait,
    names(grab))
  check("victim captured", grab.CatchWait or (held and held.action == 216),
    string.format("motions=%s p1=%s p2=%s", names(grab),
      tostring(held and held.action), tostring((gd.player(2) or {}).action)))
  if not (grab.CatchWait or (held and held.action == 216)) then return end

  local throw = {}
  local direction = gd.player(1).facing or 1
  drive(variant.stick(direction), 1, throw)
  local max_percent = before
  for frame = 1, 85 do
    drive({}, 1, throw)
    local own, victim = gd.player(1), gd.player(2)
    if victim then max_percent = math.max(max_percent, victim.percent) end
    if frame % 10 == 0 or frame == 1 then
      gd.log(string.format("%s trace f=%d own=%s/%.1f y=%.2f vy=%.2f air=%s victim=%s/%.1f y=%.2f stocks=%s",
        tag, frame, tostring(own and own.action),
        own and own.anim_frame or -1, own and own.y or -1,
        own and own.vy or -1, tostring(own and own.airborne),
        tostring(victim and victim.action), victim and victim.percent or -1,
        victim and victim.y or -1, tostring(victim and victim.stocks)))
    end
  end
  local damage = (gd.player(2) or {}).percent - before
  check(variant.name .. " throw action", throw[variant.motion], names(throw))
  check(variant.name .. " throw hit", max_percent - before >= variant.damage and
    max_percent - before <= (variant.name == "down" and 35 or variant.damage + 5),
    string.format("victim damage final=%.1f%% peak=%.1f%%", damage,
      max_percent - before))
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
