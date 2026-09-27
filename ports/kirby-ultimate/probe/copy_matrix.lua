-- Native-slot swallow and copied neutral-B route against selected Melee fighters.
-- @name: Ultimate Kirby copy matrix
-- @version: 1.0.0
-- @gameplay: true

local tag, checks, failures = "ultimate-kirby copy-matrix", 0, 0
local prefixes = {
  fox = "Fx", falco = "Fc", samus = "Ss", link = "Lk", younglink = "Cl",
  donkeykong = "Dk", donkey = "Dk", dk = "Dk",
  mrgamewatch = "Gw", gamewatch = "Gw",
  mario = "Mr", drmario = "Dr", luigi = "Lg", captainfalcon = "Ca",
  pikachu = "Pk", pichu = "Pc", ness = "Ns", bowser = "Kp", koopa = "Kp",
  yoshi = "Ys", jigglypuff = "Pr", peach = "PeSpecialLw",
  iceclimbers = "Pp", popo = "Pp", nana = "Pp",
  marth = "Ms", roy = "Fe",
  mewtwo = "Mt", zelda = "Zd", sheik = "Sk", ganondorf = "Gn",
  ganon = "Gn",
}

local function check(label, ok, detail)
  checks = checks + 1
  if not ok then failures = failures + 1 end
  gd.log(string.format("%s %s %s%s", tag, ok and "PASS" or "FAIL", label,
    detail and (": " .. detail) or ""))
end

local function sample(spec1, spec2, frames, names)
  for _ = 1, frames do
    gd.input(1, spec1, 2)
    gd.input(2, spec2, 2)
    gd.wait(1)
    local p = gd.player(1)
    if p then names[p.motion_name or "?"] = true end
  end
end

local function seen(names, part)
  for name in pairs(names) do
    if string.find(name, part, 1, true) then return true end
  end
  return false
end

local function list(names)
  local out = {}
  for name in pairs(names) do out[#out + 1] = name end
  table.sort(out)
  return table.concat(out, ",")
end

local function main()
  local ready = gd.wait_until(function()
    local p1, p2 = gd.player(1), gd.player(2)
    return gd.match().active and p1 and p1.action == 14 and
      not p1.airborne and p2
  end, 1200)
  local p1, p2 = gd.player(1), gd.player(2)
  check("spawn", ready,
    string.format("active=%s p1=%s/%s p2=%s/%s", tostring(gd.match().active),
      tostring(p1 and p1.char_name), tostring(p1 and p1.action),
      tostring(p2 and p2.char_name), tostring(p2 and p2.action)))
  if not ready then return end
  local own, target = gd.player(1), gd.player(2)
  check("own slot", own.char_name == "ultimate kirby")
  local key = string.lower(target.char_name or ""):gsub("[^%a]", "")
  local prefix = prefixes[key]
  check("known copy target", prefix ~= nil,
    string.format("target=%s key=%s prefix=%s", tostring(target.char_name), key,
      tostring(prefix)))
  if not prefix then return end

  -- Approach with Kirby so slow or stationary copy targets are covered too.
  -- Stop on the first frame in range to avoid running through the target.
  for _ = 1, 240 do
    local p1, p2 = gd.player(1), gd.player(2)
    if math.abs(p2.x - p1.x) < 19 then break end
    sample({x = p2.x > p1.x and 70 or -70}, {}, 1, {})
  end
  local gap = math.abs(gd.player(2).x - gd.player(1).x)
  check("target approaches inhale range", gap < 23,
    string.format("gap %.1f", gap))
  if gap >= 23 then return end

  local inhale = {}
  sample({buttons = "B"}, {}, 110, inhale)
  check("Inhale startup", seen(inhale, "SpecialN"), list(inhale))
  check("target captured", seen(inhale, "Eat"), list(inhale))
  if not seen(inhale, "Eat") then return end
  sample({}, {}, 2, inhale)
  local swallow = {}
  sample({buttons = "B"}, {}, 1, swallow)
  sample({}, {}, 70, swallow)
  check("swallow action", seen(swallow, "SpecialNDrink"), list(swallow))
  local recovered = gd.wait_until(function()
    local p = gd.player(1)
    return p and p.action == 14 and not p.airborne
  end, 120)
  check("swallow recovery", recovered)
  if not recovered then return end

  local copied = {}
  sample({buttons = "B"}, {}, 1, copied)
  sample({}, {}, 75, copied)
  local expected = string.find(prefix, "Special", 1, true) and prefix or
    (prefix .. "SpecialN")
  check("copied neutral B", seen(copied, expected),
    string.format("target=%s motions=%s", tostring(target.char_name), list(copied)))
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
