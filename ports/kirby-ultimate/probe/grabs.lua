-- LAB timeline check for Ultimate standing/dash grab windows.
-- @name: Ultimate Kirby grab window probe
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby grabs", 0, 0
local rows = {
  {action=212, anim=242, active=7, clear=9},
  {action=214, anim=243, active=10, clear=12},
}

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function main()
  if not gd.wait_until(function()
    local p = gd.match().active and gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 1200) then
    check("match ready", false)
    return
  end
  check("LAB mode", gd.lab_mode and gd.lab_mode())
  for _, row in ipairs(rows) do
    local timeline = gd.timeline(1, row.action)
    local active, clear = {}, {}
    if timeline then
      for _, event in ipairs(timeline.events) do
        if event.op == 11 then active[#active + 1] = event.frame end
        if event.op == 16 then clear[#clear + 1] = event.frame end
      end
    end
    local ok = timeline and timeline.anim_id == row.anim and #active > 0 and #clear == 1
    if ok then
      for _, frame in ipairs(active) do
        if frame ~= row.active then ok = false end
      end
      ok = ok and clear[1] == row.clear
    end
    check("grab row " .. row.anim, ok,
      string.format("anim=%s active=%s clear=%s", timeline and tostring(timeline.anim_id) or "nil",
        active[1] and tostring(active[1]) or "nil", clear[1] and tostring(clear[1]) or "nil"))
    gd.wait(1)
  end
end

gd.run(function()
  local ok, err = pcall(main)
  if not ok then check("probe error", false, tostring(err)) end
  gd.log(string.format("%s RESULT %s (%d/%d checks passed)",
    tag, failures == 0 and "PASS" or "FAIL", checks - failures, checks))
  gd.quit()
end)
