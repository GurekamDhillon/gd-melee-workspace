-- proof.lua - plays a Geno fighter (P1) through idle, walk, run, jump, jab, shield and grab against a standing Mario (P2) in the LAB
-- and logs one ARTPROOF line per scenario: the motion names and the AUTHORED CLIP names (anim_name, from the figatree symbol) it passed
-- through, the path, the first live hitbox (bone, damage, frame), shield and grab results. Headless friendly (run_scene.sh).
-- tools/geno/artist/proof_report.py reads the lines.
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
local function emit(rec) gd.log('ARTPROOF ' .. js(rec)) end
local function reset() gd.input(1, {}, 1); gd.loadstate(1); gd.wait(3) end

local function run(name, steps, opts)
  opts = opts or {}
  reset()
  if opts.p2x then gd.teleport(2, opts.p2x, 0) end
  local mseen, aseen, path, n = {}, {}, {}, 0
  local rec = {name = name}
  local function add(list, v) if v and list[#list] ~= v then list[#list + 1] = v end end
  local p2mseen, p2per0 = {}, gd.player(2).percent
  local function sample()
    gd.wait(1); n = n + 1
    local p = gd.player(1)
    add(mseen, p.motion_name); add(aseen, p.anim_name)
    add(p2mseen, gd.player(2).motion_name)
    if n % 6 == 0 then path[#path + 1] = {p.x, p.y} end
    local hb = gd.hitboxes(1)
    if hb and #hb > 0 and not rec.hit_frame then
      rec.hit_frame = n; rec.hit_af = p.anim_frame_f; rec.hit_bone = hb[1].bone; rec.hit_damage = hb[1].damage
      rec.hit_pos = {hb[1].x, hb[1].y, hb[1].z}
      local j = gd.joints(1, true)
      if j and j[hb[1].bone + 1] then rec.hit_bone_pos = {j[hb[1].bone + 1].x, j[hb[1].bone + 1].y, j[hb[1].bone + 1].z} end
    end
    if p.shield and p.shield > 0 then rec.shield_max = math.max(rec.shield_max or 0, p.shield) end
  end
  for _, s in ipairs(steps) do
    if s[1] == 'in' then gd.input(1, s[2], s[3]); for _ = 1, s[3] do sample() end
    else for _ = 1, s[2] do sample() end end
  end
  local p = gd.player(1)
  rec.motions, rec.clips, rec.path, rec.frames = mseen, aseen, path, n
  rec.x, rec.y, rec.face = p.x, p.y, p.facing
  rec.p2_motions = p2mseen
  rec.p2_damage = gd.player(2).percent - p2per0
  rec.hurtboxes = p.hurtbox_count; rec.joints = p.joint_count
  emit(rec)
end

gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no match')
    gd.cpu_mode(2, 'stand'); gd.teleport(1, 0, 0); gd.teleport(2, -90, 0); gd.set_percent(1, 0); gd.set_percent(2, 0)
    gd.wait(30); gd.savestate(1); gd.wait(2)
    local function I(spec, n) return {'in', spec, n} end
    local function S(n) return {'s', n} end
    run('idle', {S(90)})
    run('walk', {I({x = 40}, 40), I({}, 30)})
    run('run', {I({x = 127}, 40), I({}, 40)})
    run('jump', {I({buttons = 'X'}, 12), I({}, 90)})
    run('doublejump', {I({buttons = 'X'}, 2), S(14), I({buttons = 'X'}, 2), I({}, 80)})
    run('jab', {I({buttons = 'A'}, 2), I({}, 40)}, {p2x = 9})
    run('shield', {I({buttons = 'L'}, 30), I({}, 20)})
    run('grab', {I({buttons = 'Z'}, 2), S(40)}, {p2x = 7})
    run('grab_throw', {I({buttons = 'Z'}, 2), S(35), I({x = 127}, 3), S(60)}, {p2x = 7})
    run('hurtbox_dump', {S(2)})
    local hb = gd.hurtboxes(1)
    local dump = {}
    for i, h in ipairs(hb or {}) do dump[i] = {id = h.id, bone = h.bone, r = h.radius, a = {h.ax, h.ay, h.az}, b = {h.bx, h.by, h.bz}} end
    emit({name = 'hurtboxes', list = dump})
    local j = gd.joints(1, true)
    local jd = {}
    for i, q in ipairs(j or {}) do jd[i] = {q.index, q.parent, q.x, q.y, q.z} end
    emit({name = 'joints', list = jd})
    gd.log('ARTPROOF DONE')
  end)
  if not ok then gd.log('ARTPROOF FAIL ' .. tostring(why)) end
  gd.quit()
end)
