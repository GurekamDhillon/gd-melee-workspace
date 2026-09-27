-- Visible LAB sequence: charge Hammer, walk during charge, release, then air release.
-- @name: Ultimate Kirby Side B showcase
-- @version: 1.0.0
-- @gameplay: true

local tag = "ultimate-kirby side-b showcase"
local checks, failures = 0, 0

local function check(name, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", name,
    detail and (": " .. detail) or ""))
end

local function drive(spec, frames, actions)
  for _ = 1, frames do
    gd.input(1, spec, 2)
    gd.wait(1)
    local p = gd.player(1)
    if p then actions[p.action] = true end
  end
end

local function shot(name)
  local p = gd.player(1)
  local ok, path = gd.screenshot("ultimate-kirby-side-b-" .. name)
  gd.log(string.format("%s shot %s queued=%s action=%s anim=%.1f y=%.2f path=%s",
    tag, name, tostring(ok), tostring(p and p.action),
    p and p.anim_frame or -1, p and p.y or -1, tostring(path)))
  return ok
end

gd.run(function()
  local ok, err = pcall(function()
    local ready = gd.wait_until(function()
      local p = gd.match().active and gd.player(1)
      return p and p.action == 14 and not p.airborne
    end, 1200)
    check("spawn", ready)
    if not ready then return end
    check("own slot", gd.player(1).char_name == "ultimate kirby")
    gd.debug_draw(1, gd.draw.MODEL)
    gd.debug_draw(2, gd.draw.MODEL)
    gd.debug_stage(0)
    gd.wait(30)

    local start_x = gd.player(1).x
    local charged = {}
    drive({buttons = "B", x = 127}, 35, charged)
    check("charge begins", charged[1024])
    check("charge screenshot queued", shot("charge"))
    drive({buttons = "B", x = 127}, 90, charged)
    local end_x = gd.player(1).x
    check("walk while charging", end_x > start_x + 10,
      string.format("x %.2f to %.2f", start_x, end_x))
    check("charge walk screenshot queued", shot("charge-walk"))
    local ground = {}
    drive({}, 13, ground)
    check("full ground release", ground[1026])
    check("ground release screenshot queued", shot("ground-release"))

    local settled = gd.wait_until(function()
      local p = gd.player(1)
      return p and p.action == 14 and not p.airborne
    end, 180)
    check("ground recovery", settled)
    if not settled then return end
    local air = {}
    drive({buttons = "X"}, 1, air)
    drive({}, 6, air)
    check("jump before aerial Hammer", gd.player(1).airborne)
    drive({buttons = "B", x = 127}, 18, air)
    check("aerial charge", air[1027] and gd.player(1).airborne)
    check("aerial charge screenshot queued", shot("air-charge"))
    drive({}, 12, air)
    check("aerial release", air[1028] or air[1029])
    check("air release screenshot queued", shot("air-release"))
  end)
  if not ok then check("probe error", false, tostring(err)) end
  gd.input(1, {}, 2)
  gd.log(string.format("%s INPUT ROUTE %s (%d/%d; visual review required)", tag,
    failures == 0 and "PASS" or "FAIL", checks - failures, checks))
  gd.label("Ultimate Kirby Side B showcase - controller is yours")
  while true do gd.wait(120) end
end)
