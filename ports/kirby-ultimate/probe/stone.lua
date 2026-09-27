-- Native Kirby Stone state and Ultimate aerial combat payload in the m-ex slot.
-- @name: Ultimate Kirby Stone
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby stone", 0, 0

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function drive(spec, frames)
  local actions, motions, hits = {}, {}, {}
  for _ = 1, frames do
    gd.input(1, spec, 2)
    gd.wait(1)
    local p = gd.player(1)
    if p then
      actions[p.action] = true
      motions[p.motion_name or "?"] = true
      for _, h in ipairs(gd.hitboxes(1) or {}) do
        if h.active then hits[#hits + 1] = h end
      end
    end
  end
  return actions, motions, hits
end

local function has_name(motions, needle)
  for name in pairs(motions) do
    if string.find(name, needle, 1, true) then return true end
  end
  return false
end

local function hit(hits, damage, angle, kbg, bkb)
  for _, h in ipairs(hits) do
    if h.damage == damage and h.angle == angle and h.kbg == kbg and h.bkb == bkb then
      return true, h
    end
  end
  return false, nil
end

local function composed_rows()
  local normal = gd.timeline(1, 50)
  local nh = {}
  for _, e in ipairs(normal and normal.events or {}) do
    if e.op == 11 then nh[#nh + 1] = {e.frame, e.damage} end
  end
  check("native-slot forward tilt", normal and normal.anim_id == 52
    and #nh == 3 and nh[1][1] == 10 and nh[1][2] == 12
    and nh[2][1] == 19 and nh[2][2] == 9
    and nh[3][1] == 28 and nh[3][2] == 6)

  local throw = gd.timeline(1, 220)
  local release = nil
  for _, e in ipairs(throw and throw.events or {}) do
    if e.op == 20 then release = e.frame end
  end
  check("native-slot back throw", throw and throw.anim_id == 248 and release == 42,
    "release " .. tostring(release))

  local grab = gd.timeline(1, 214)
  local active = nil
  for _, e in ipairs(grab and grab.events or {}) do
    if e.op == 11 then active = e.frame end
  end
  check("native-slot dash grab", grab and grab.anim_id == 243 and active == 10,
    "active " .. tostring(active))

  for _, row in ipairs({{386, 325}, {390, 329}}) do
    local cutter = gd.timeline(1, row[1])
    local count, first, last = 0, nil, nil
    for _, e in ipairs(cutter and cutter.events or {}) do
      if e.op == 11 then
        count = count + 1
        first = first or e
        last = e
      end
    end
    check("native-slot Final Cutter " .. row[2], cutter and cutter.anim_id == row[2]
      and count == 10 and first.frame == 2 and first.damage == 5
      and last.frame == 29 and last.damage == 2,
      "hitboxes " .. count)
  end
end

local function main()
  local ready = gd.wait_until(function()
    local p = gd.match().active and gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 1200)
  check("spawn", ready)
  if not ready then return end
  check("own slot", gd.player(1).char_name == "ultimate kirby")
  composed_rows()

  local _, ground, ground_hits = drive({buttons = "B", y = -127}, 1)
  local _, more_ground, more_hits = drive({}, 48)
  for name in pairs(more_ground) do ground[name] = true end
  check("ground Stone startup", has_name(ground, "SpecialLw1"))
  check("ground Stone hold", has_name(ground, "SpecialLw"))
  check("ground source still deferred", #ground_hits + #more_hits == 0)
  drive({buttons = "B"}, 1)
  local _, ending = drive({}, 36)
  check("Stone button cancel", has_name(ending, "SpecialLwEnd"))
  local recovered = gd.wait_until(function()
    local p = gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 120)
  check("ground recovery", recovered)
  if not recovered then return end

  drive({buttons = "X"}, 1)
  drive({}, 5)
  check("jumped for aerial Stone", gd.player(1).airborne)
  local _, air_start = drive({buttons = "B", y = -127}, 1)
  local _, air, air_hits = drive({}, 70)
  for name in pairs(air) do air_start[name] = true end
  check("aerial Stone startup", has_name(air_start, "SpecialAirLwStart"))
  check("aerial Stone active", has_name(air_start, "SpecialAirLw"))
  local matched, observed = hit(air_hits, 18, 70, 76, 69)
  check("Ultimate aerial hitbox", matched,
    observed and string.format("size %.2f", observed.radius) or "18/70/76/69 missing")
end

gd.run(function()
  local ok, err = pcall(main)
  if not ok then check("probe error", false, tostring(err)) end
  gd.input(1, {}, 2)
  gd.log(string.format("%s RESULT %s (%d/%d checks passed)",
    tag, failures == 0 and "PASS" or "FAIL", checks - failures, checks))
  gd.quit()
end)
