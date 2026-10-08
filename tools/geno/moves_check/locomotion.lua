-- Locomotion and defence check for a Geno fighter (P1) standing against Mario (P2, a standing dummy) in the LAB. Emits MOVECHK records
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
local function reset() gd.input(1, {}, 1); gd.loadstate(1); gd.wait(3) end
local function run(name, steps)
  reset()
  local seen, path, ymax, n = {}, {}, 0, 0
  local function sample()
    gd.wait(1); n = n + 1
    local p = gd.player(1)
    if seen[#seen] ~= p.motion_name then seen[#seen + 1] = p.motion_name end
    if n % 6 == 0 then path[#path + 1] = {p.x, p.y} end
    if p.y > ymax then ymax = p.y end
  end
  for _, s in ipairs(steps) do
    if s[1] == 'in' then gd.input(1, s[2], s[3]); for _ = 1, s[3] do sample() end
    else for _ = 1, s[2] do sample() end end
  end
  local p = gd.player(1)
  emit({name = name, seen = seen, path = path, ymax = ymax, x = p.x, y = p.y, frames = n, face = p.facing})
end
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no match')
    gd.cpu_mode(2, 'stand'); gd.teleport(1, 0, 0); gd.teleport(2, -90, 0); gd.set_percent(1, 0); gd.set_percent(2, 0)
    gd.wait(30); gd.savestate(1); gd.wait(2)
    local function S(n) return {'s', n} end
    local function I(spec, n) return {'in', spec, n} end
    run('loco_walk', {I({x = 40}, 40), I({}, 30)})
    run('loco_walk_fast', {I({x = 90}, 40), I({}, 30)})
    run('loco_dash', {I({x = 127}, 4), I({}, 30)})
    run('loco_run_stop', {I({x = 127}, 40), I({}, 40)})
    run('loco_run_turn', {I({x = 127}, 30), I({x = -127}, 30), I({}, 30)})
    run('loco_turn', {I({x = -40}, 12), I({}, 20)})
    run('loco_crouch', {I({y = -90}, 30), I({}, 20)})
    run('loco_fullhop', {I({buttons = 'X'}, 12), I({}, 80)})
    run('loco_shorthop', {I({buttons = 'X'}, 2), I({}, 70)})
    run('loco_doublejump', {I({buttons = 'X'}, 2), S(14), I({buttons = 'X'}, 2), I({}, 80)})
    run('loco_triplejump', {I({buttons = 'X'}, 2), S(14), I({buttons = 'X'}, 2), S(14), I({buttons = 'X'}, 2), I({}, 80)})
    run('loco_airdrift', {I({buttons = 'X'}, 2), I({x = 127}, 40), I({}, 40)})
    run('loco_fastfall', {I({buttons = 'X'}, 12), S(20), I({y = -127}, 40), I({}, 20)})
    run('loco_shield', {I({buttons = 'L'}, 30), I({}, 20)})
    run('loco_roll_f', {I({buttons = 'L', x = 127}, 3), I({}, 45)})
    run('loco_roll_b', {I({buttons = 'L', x = -127}, 3), I({}, 45)})
    run('loco_spotdodge', {I({buttons = 'L', y = -127}, 3), I({}, 40)})
    run('loco_airdodge', {I({buttons = 'X'}, 2), S(10), I({buttons = 'L', x = 90, y = 40}, 3), I({}, 50)})
    run('loco_wavedash', {I({buttons = 'X'}, 2), S(3), I({buttons = 'L', x = 100, y = -90}, 3), I({}, 40)})
    run('loco_jump_in_place_land', {I({buttons = 'X'}, 12), I({}, 90)})
    run('loco_shield_grab', {I({buttons = 'L'}, 10), I({buttons = 'Z'}, 2), I({}, 40)})
    run('loco_ledge_fall', {I({x = 127}, 40), S(60), I({}, 120)})
    gd.log('MOVECHK DONE 21')
  end)
  if not ok then gd.log('MOVECHK FAIL ' .. tostring(why)) end
  gd.quit()
end)
