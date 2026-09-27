-- LAB check for staged Ultimate absolute throw values and release frames.
-- @name: Ultimate Kirby throw absolute probe
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby throws", 0, 0
local rows = {
  {action=219, anim=247, damage=5, angle=75, kbg=125, bkb=40, release=46},
  {action=220, anim=248, damage=8, angle=130, kbg=120, bkb=30, release=42},
  {action=221, anim=249, damage=10, angle=78, kbg=74, bkb=75, release=52},
  {action=222, anim=250, damage=2, angle=63, kbg=180, bkb=60, release=59},
}

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function field(word, shift, width)
  return math.floor(word / (2 ^ shift)) % (2 ^ width)
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
    local absolutes, release = {}, nil
    if timeline then
      for _, event in ipairs(timeline.events) do
        if event.op == 34 then absolutes[#absolutes + 1] = event end
        if event.op == 20 then release = event.frame end
      end
    end
    local ok = timeline and timeline.anim_id == row.anim and #absolutes == 2
    if ok then
      local words, catch = absolutes[1].words, absolutes[2].words
      ok = field(words[1], 0, 23) == row.damage
        and field(words[2], 23, 9) == row.angle
        and field(words[2], 14, 9) == row.kbg
        and field(words[3], 23, 9) == row.bkb
        and field(catch[1], 0, 23) == 3
        and release == row.release
    end
    check("throw row " .. row.anim, ok,
      string.format("anim=%s damage=%s release=%s", timeline and tostring(timeline.anim_id) or "nil",
        absolutes[1] and tostring(field(absolutes[1].words[1], 0, 23)) or "nil", tostring(release)))
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
