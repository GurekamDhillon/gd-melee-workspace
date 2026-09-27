-- Input-route check for Kirby's native Final Cutter statuses and sword hits.
-- @name: Ultimate Kirby Final Cutter live
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby cutter-live", 0, 0

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function drive(spec, frames, actions, damages)
  for _ = 1, frames do
    gd.input(1, spec, 2)
    gd.wait(1)
    local p = gd.player(1)
    if p then
      actions[p.action] = true
      for _, h in ipairs(gd.hitboxes(1) or {}) do
        if h.active then damages[h.damage] = true end
      end
    end
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

  local ground, hits = {}, {}
  drive({buttons = "B", y = 127}, 1, ground, hits)
  drive({}, 115, ground, hits)
  check("ground input enters Final Cutter", ground[385])
  check("ground-to-air rises", ground[390], "native ground start routes to air rising row")
  check("ground sword early 5%", hits[5])
  check("ground sword late 2%", hits[2])
  gd.log(tag .. " ground states " .. table.concat((function()
    local out = {}
    for action in pairs(ground) do
      if action >= 385 and action <= 392 then out[#out + 1] = action end
    end
    table.sort(out)
    return out
  end)(), ","))

  local settled = gd.wait_until(function()
    local p = gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 180)
  check("ground recovery", settled)
  if not settled then return end
  drive({buttons = "X"}, 1, {}, {})
  drive({}, 5, {}, {})
  check("jumped", gd.player(1).airborne)
  local air, air_hits = {}, {}
  drive({buttons = "B", y = 127}, 1, air, air_hits)
  drive({}, 115, air, air_hits)
  check("air input enters Final Cutter", air[389])
  check("air rising status", air[390])
  check("air sword early 5%", air_hits[5])
  check("air sword late 2%", air_hits[2])
end

gd.run(function()
  local ok, err = pcall(main)
  if not ok then check("probe error", false, tostring(err)) end
  gd.input(1, {}, 2)
  gd.log(string.format("%s RESULT %s (%d/%d checks passed)",
    tag, failures == 0 and "PASS" or "FAIL", checks - failures, checks))
  gd.quit()
end)
