-- LAB runtime check for the staged Ultimate normal-attack ftcmd payload.
-- @name: Ultimate Kirby normal-attack probe
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby normals", 0, 0

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

-- Each pair is an active frame (LAB's 1-based convention) and damage.
-- This table is generated from the locally built Ultimate Kirby IR's c00
-- game script events, with fractional damage rounded for Melee ftcmd.
local rows = {
  [46] = {{4,2},{4,2},{4,2},{4,2}},
  [47] = {{4,2},{4,2}},
  [51] = {{4,3},{4,3},{4,3}},
  [52] = {{10,12},{19,9},{28,6}},
  [53] = {{6,8},{6,8},{6,7}},
  [55] = {{6,8},{6,8},{6,7}},
  [57] = {{6,8},{6,8},{6,7}},
  [58] = {{5,5},{5,5},{7,4},{7,4}},
  [59] = {{5,6},{5,6}},
  [60] = {{14,15},{17,11}},
  [62] = {{14,15},{17,11}},
  [64] = {{14,15},{17,11}},
  [66] = {{15,15},{15,15},{15,14},{18,14},{18,14},{18,13},{20,13},{20,13},{20,12}},
  [67] = {{11,14},{11,14}},
  [68] = {{11,10},{13,8},{17,6},{22,4}},
  [69] = {{11,4},{11,4},{18,4},{26,6}},
  [70] = {{7,13},{10,8}},
  [71] = {{11,10},{11,10}},
  [72] = {{19,1},{22,1},{25,1},{28,1},{31,1},{35,2}},
  [187] = {{17,7},{21,7}},
  [195] = {{17,7},{21,7}},
  [221] = {{21,9}},
  [222] = {{21,9}},
  [245] = {{2,1}},
}

-- gd.timeline takes the fighter action state, while PlKb.dat ftcmd is indexed
-- by animation row. These are the common action IDs from ftCommon/forward.h.
local actions = {
  [46]=44, [47]=45, [51]=49, [52]=50, [53]=51, [55]=53,
  [57]=55, [58]=56, [59]=57, [60]=58, [62]=60, [64]=62,
  [66]=63, [67]=64, [68]=65, [69]=66, [70]=67, [71]=68, [72]=69,
  [187]=187, [195]=195, [221]=256, [222]=257, [245]=217,
}

local function main()
  if not gd.wait_until(function()
    local p = gd.match().active and gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 1200) then
    check("match ready", false, "no standing P1 within 1200 logic frames")
    return
  end
  check("LAB mode", gd.lab_mode and gd.lab_mode())
  for row, expected in pairs(rows) do
    local timeline = gd.timeline(1, actions[row])
    local hits = {}
    if timeline then
      for _, event in ipairs(timeline.events) do
        if event.op == 11 then hits[#hits + 1] = event end
      end
    end
    local ok = timeline ~= nil and timeline.anim_id == row and #hits == #expected
    if ok then
      for i, hit in ipairs(hits) do
        if hit.frame ~= expected[i][1] or hit.damage ~= expected[i][2] then
          ok = false
          break
        end
      end
    end
    check("normal row " .. row, ok,
      string.format("action=%d anim=%s hits=%d/%d first=%s", actions[row],
        timeline and tostring(timeline.anim_id) or "nil",
        #hits, #expected, hits[1] and (hits[1].frame .. "/" .. hits[1].damage) or "none"))
    -- A full timeline walk is costly; each frame starts a fresh script budget.
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
