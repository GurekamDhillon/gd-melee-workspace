-- LAB timeline check for Ultimate Final Cutter rising sword hitboxes.
-- @name: Ultimate Kirby Final Cutter probe
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby final-cutter", 0, 0
local rows = {{action=386, anim=325}, {action=390, anim=329}}
local expected = {{2,5},{2,5},{2,5},{2,5},
                  {4,5},{4,5},{4,5},{4,5},{20,2},{29,2}}

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
    local hits = {}
    if timeline then
      for _, event in ipairs(timeline.events) do
        if event.op == 11 then hits[#hits + 1] = event end
      end
    end
    local ok = timeline and timeline.anim_id == row.anim and #hits == #expected
    if ok then
      for i, event in ipairs(hits) do
        if event.frame ~= expected[i][1] or event.damage ~= expected[i][2] then
          ok = false
          break
        end
      end
    end
    check("up-B row " .. row.anim, ok,
      string.format("anim=%s hits=%d/%d first=%s", timeline and tostring(timeline.anim_id) or "nil",
        #hits, #expected, hits[1] and (hits[1].frame .. "/" .. hits[1].damage) or "none"))
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
