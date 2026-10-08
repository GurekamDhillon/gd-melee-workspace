-- Defence check for a Geno fighter (P1) being hit by Mario (P2, scripted) in the LAB. Emits MOVECHK records
-- (the format moves_diff.py reads) so an old port and its define can be diffed: per scenario the motion names seen, the path every 6th
-- frame (x, y), the highest point and the end position. Scenarios: walk, dash, run and stop, turn, kneebend, short hop, full hop, double jump,
-- air drift, fast fall, shield, roll, spot dodge, air dodge, crouch, ledge-less landing, wavedash.
local function js(v)
  local t = type(v)
  if t == 'nil' then return 'null' end
  if t == 'boolean' then return tostring(v) end
  if t == 'number' then return string.format('%.4g', v) end
  if t == 'string' then return '"' .. v:gsub('[%c"\\]', function(c) return string.format('\\u%04x', c:byte()) end) .. '"' end
  if t == 'table' then
    if v[1] ~= nil or next(v) == nil then
      local r = {}
      for i, x in ipairs(v) do r[i] = js(x) end
      return '[' .. table.concat(r, ',') .. ']'
    end
    local keys = {}
    for k in pairs(v) do keys[#keys + 1] = k end
    table.sort(keys)
    local r = {}
    for _, k in ipairs(keys) do r[#r + 1] = js(k) .. ':' .. js(v[k]) end
    return '{' .. table.concat(r, ',') .. '}'
  end
  return 'null'
end
local function emit(rec)
  local t = js(rec)
  if #t <= 1400 then gd.log('MOVECHK ' .. t); return end
  local n = math.ceil(#t / 1400)
  for i = 1, n do gd.log(string.format('MOVECHKPART %s %d %d %s', rec.name, i, n, t:sub((i - 1) * 1400 + 1, i * 1400))) end
end
local function reset() gd.input(1, {}, 1); gd.cpu_mode(2, 'stand'); gd.loadstate(1); gd.wait(3) end
-- Mario stands `dist` units in front of the fighter, turned to it, and presses `pad` for `n` frames at frame `at`; P1 holds `hold` (shield, nothing)
local function case(name, dist, mario_y, at, pad, n, hold, p1y, frames)
  reset()
  gd.teleport(1, 0, p1y or 0)
  gd.teleport(2, dist, mario_y or 0)
  gd.cpu_mode(2, 'script')
  gd.cpu_pad(2, {x = -40}, 3); gd.wait(5)
  gd.cpu_pad(2, {}, 1)
  local seen, mseen, path, n_ = {}, {}, {}, 0
  local p0 = gd.player(1).percent
  if hold then gd.input(1, hold, frames) end
  for k = 0, frames - 1 do
    if k == at then gd.cpu_pad(2, pad, n) end
    gd.wait(1); n_ = n_ + 1
    local p, m = gd.player(1), gd.player(2)
    if seen[#seen] ~= p.motion_name then seen[#seen + 1] = p.motion_name end
    if mseen[#mseen] ~= m.motion_name then mseen[#mseen + 1] = m.motion_name end
    if n_ % 6 == 0 then path[#path + 1] = {p.x, p.y} end
  end
  local p = gd.player(1)
  emit({name = name, seen = seen, mseen = mseen, path = path, dmg = p.percent - p0, x = p.x, y = p.y})
end
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no match')
    gd.teleport(1, 0, 0); gd.teleport(2, -60, 0); gd.set_percent(1, 0); gd.set_percent(2, 0)
    gd.wait(30); gd.savestate(1); gd.wait(2)
    case('def_jab', 5, 0, 10, {buttons = 'A'}, 2, nil, 0, 90)
    case('def_utilt', 5, 0, 10, {buttons = 'A', y = 100}, 2, nil, 0, 90)
    case('def_dtilt', 6, 0, 10, {buttons = 'A', y = -100}, 2, nil, 0, 90)
    case('def_fsmash', 8, 0, 10, {cx = 127}, 2, nil, 0, 120)
    case('def_usmash_air', 4, 0, 10, {cy = 127}, 2, nil, 6, 120)
    case('def_fair_air', 8, 14, 10, {cx = 127}, 2, nil, 14, 90)
    case('def_shield_jab', 5, 0, 10, {buttons = 'A'}, 2, {buttons = 'L'}, 0, 90)
    case('def_shield_fsmash', 8, 0, 10, {cx = 127}, 2, {buttons = 'L'}, 0, 110)
    case('def_grab', 4, 0, 10, {buttons = 'Z'}, 2, nil, 0, 150)
    case('def_grab_throw', 4, 0, 10, {buttons = 'Z'}, 2, nil, 0, 150)
    gd.log('MOVECHK DONE 10')
  end)
  if not ok then gd.log('MOVECHK FAIL ' .. tostring(why)) end
  gd.quit()
end)
