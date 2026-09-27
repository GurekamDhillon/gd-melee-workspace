-- Live input check for Ultimate Kirby's staged rapid-jab loop.
-- @name: Ultimate Kirby rapid jab
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby rapid-jab", 0, 0

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function step(spec)
  gd.input(1, spec, 2)
  gd.wait(1)
  return gd.player(1)
end

local function main()
  local ready = gd.wait_until(function()
    local p = gd.match().active and gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 1200)
  check("spawn", ready)
  if not ready then return end

  local loop_seen, end_seen = false, false
  local zero, one = 0, 0
  local actions = {}
  for frame = 1, 150 do
    local p = step(frame % 3 == 1 and {buttons = "A"} or {})
    if p then
      actions[p.action] = true
      if p.action == 48 then loop_seen = true end
      if loop_seen and p.action == 49 then end_seen = true end
      if p.action == 48 then
        for _, h in ipairs(gd.hitboxes(1) or {}) do
          if h.damage == 0 then zero = zero + 1 end
          if h.damage == 1 then one = one + 1 end
        end
      end
    end
    if loop_seen and zero > 0 and one > 0 then break end
  end
  check("input enters rapid-jab loop", loop_seen,
    string.format("jab1=%s jab2=%s loop=%s", tostring(actions[44]),
      tostring(actions[45]), tostring(actions[48])))
  check("zero and one damage pulses visible", zero > 0 and one > 0,
    string.format("zero=%d one=%d", zero, one))

  if loop_seen then
    for _ = 1, 80 do
      local p = step({})
      if p and p.action == 49 then end_seen = true end
      if end_seen then break end
    end
  end
  check("button release enters finisher", end_seen)
end

gd.run(function()
  local ok, err = pcall(main)
  if not ok then check("probe error", false, tostring(err)) end
  gd.input(1, {}, 2)
  gd.log(string.format("%s RESULT %s (%d/%d checks passed)",
    tag, failures == 0 and "PASS" or "FAIL", checks - failures, checks))
  gd.quit()
end)
