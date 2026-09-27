-- LAB input check for the native Geno Ultimate Kirby Hammer charge prototype.
-- @name: Ultimate Kirby Hammer charge
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby hammer", 0, 0

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function drive(spec, frames)
  local seen, hits = {}, {}
  for _ = 1, frames do
    gd.input(1, spec, 2)
    gd.wait(1)
    local p = gd.player(1)
    if p then
      seen[p.action] = true
      for _, h in ipairs(gd.hitboxes(1) or {}) do hits[#hits + 1] = h end
    end
  end
  return seen, hits
end

local function hit_damage(hits, value)
  for _, hit in ipairs(hits) do
    if hit.damage == value then return true end
  end
  return false
end

local function main()
  local ready = gd.wait_until(function()
    local p = gd.match().active and gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 1200)
  check("spawn", ready)
  if not ready then return end
  check("own slot", gd.player(1).char_name == "ultimate kirby")

  local hold, early_hits = drive({buttons = "B", x = 127}, 15)
  check("weak hold state", hold[1024], "B held enters Geno HammerHold")
  check("hold has no hitbox", #early_hits == 0)
  local weak, weak_hits = drive({}, 24)
  check("weak release state", weak[1025], "releasing B before full charge enters HammerWeak")
  check("weak hit", hit_damage(weak_hits, 19), "Ultimate weak Hammer damage 19")
  check("weak motion", (gd.timeline(1, 1025) or {}).anim_id == 322)

  local settled = gd.wait_until(function()
    local p = gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 180)
  check("recovery", settled)
  if not settled then return end
  local x = gd.player(1).x
  local charge, charged_hits = drive({buttons = "B", x = 127}, 122)
  check("charged hold state", charge[1024] and gd.player(1).action == 1024)
  check("charged hold walk", gd.player(1).x > x + 10,
    string.format("x %.2f -> %.2f", x, gd.player(1).x))
  check("charged hold has no hitbox", #charged_hits == 0)
  local max, max_hits = drive({}, 25)
  check("max release state", max[1026], "full charge enters HammerMax")
  check("max hit", hit_damage(max_hits, 35), "Ultimate full Hammer damage 35")
  check("max motion", (gd.timeline(1, 1026) or {}).anim_id == 5)
end

gd.run(function()
  local ok, err = pcall(main)
  if not ok then check("probe error", false, tostring(err)) end
  gd.input(1, {}, 2)
  gd.log(string.format("%s RESULT %s (%d/%d checks passed)",
    tag, failures == 0 and "PASS" or "FAIL", checks - failures, checks))
  gd.quit()
end)
