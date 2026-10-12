-- gd.set_scale check (tag SCALECHECK): set 1.3 on P1 and compare against 1.0: scale readback, hurtbox extent and radius,
-- ECB size, jab reach (farthest active hitbox edge) and the farthest distance at which the jab connects (hurt/hit tests); then rewind exactness across a
-- scale write, and that the scale clamps to 0.5..2.0. The refused-online half is the source test pc/tests/set_scale_source_test.py.
local function span()
  local lo, hi, rmax, n = 1e9, -1e9, 0, 0
  for _, h in ipairs(gd.hurtboxes(1) or {}) do
    lo = math.min(lo, h.ay, h.by); hi = math.max(hi, h.ay, h.by); rmax = math.max(rmax, h.radius); n = n + 1
  end
  return hi - lo, rmax, n
end
local function ecb_h()
  local e = gd.player(1).ecb
  return e.top.y - e.bottom.y
end
local function reach()
  local best = 0
  local p0 = gd.player(1)
  gd.input(1, {buttons = 'A'}, 2)
  for _ = 1, 20 do
    gd.wait(1)
    for _, hb in ipairs(gd.hitboxes(1) or {}) do
      local x = math.abs((hb.bx or hb.x or 0) - p0.x) + (hb.radius or hb.size or 0)
      best = math.max(best, x)
    end
  end
  return best
end
-- the farthest P2 distance at which P1's jab still connects (the hurt/hit tests scale at use)
local function max_hit_dist()
  local best = 0
  for d = 8, 44, 2 do
    for _ = 1, 20 do
      if pcall(function() gd.teleport(1, 0, 0); gd.teleport(2, d, 0) end) then break end
      gd.wait(15)
    end
    gd.set_percent(2, 0); gd.wait(45)
    gd.input(1, {buttons = 'A'}, 2); gd.wait(25)
    if (gd.player(2).percent or 0) > 0 then best = d end
  end
  return best
end
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
    gd.cpu_mode(2, 'stand')
    gd.teleport(1, 0, 0); gd.teleport(2, 120, 0); gd.set_percent(1, 0); gd.wait(40)
    local s0, r0, n0 = span(); local e0 = ecb_h(); local w0 = reach()
    gd.wait(40)
    gd.log(string.format('SCALECHECK base: scale %.2f span %.2f radius %.2f (%d boxes) ecb_h %.2f jab reach %.2f', gd.player(1).scale, s0, r0, n0, e0, w0))
    gd.set_scale(1, 1.3); gd.wait(40)
    local s1, r1 = span(); local e1 = ecb_h(); local w1 = reach()
    gd.wait(40)
    gd.log(string.format('SCALECHECK 1.3: scale %.3f span %.2f radius %.2f ecb_h %.2f jab reach %.2f', gd.player(1).scale, s1, r1, e1, w1))
    assert(math.abs(gd.player(1).scale - 1.3) < 0.001, 'scale readback')
    assert(s1 > s0 * 1.2 and s1 < s0 * 1.4, 'hurtbox span did not scale ~1.3: ' .. s0 .. ' -> ' .. s1)
    -- gd.hurtboxes reports the raw capsule radius; retail multiplies by x34_scale.y where the capsule is tested, so the radius is proven by hits below
    assert(e1 > e0 * 1.15, 'ECB did not grow: ' .. e0 .. ' -> ' .. e1)
    assert(w0 > 0 and w1 > w0 * 1.1, 'jab reach did not scale: ' .. w0 .. ' -> ' .. w1)
    gd.set_scale(1, 1.0); local h0 = max_hit_dist()
    gd.set_scale(1, 1.3); local h1 = max_hit_dist()
    gd.log(string.format('SCALECHECK farthest jab hit: scale 1.0 at %d, 1.3 at %d', h0, h1))
    assert(h0 > 0 and h1 >= h0 + 2, 'hit range did not grow with the scale: ' .. h0 .. ' -> ' .. h1)
    gd.set_scale(1, 9); assert(math.abs(gd.player(1).scale - 2.0) < 0.001, 'clamp high')
    gd.set_scale(1, 0.1); assert(math.abs(gd.player(1).scale - 0.5) < 0.001, 'clamp low')
    gd.set_scale(1, 1.3); gd.wait(10)
    -- rewind consistency across a scale write
    assert(gd.rewind_test(120, true), 'rewind refused')
    local done = false
    for _ = 1, 400 do
      gd.wait(1)
      local r = gd.rewind_test_result()
      if r and r.phase == 0 and r.pass ~= nil then
        gd.log(string.format('SCALECHECK rewind pass=%s diff_compared=%s', tostring(r.pass), tostring(r.diff_compared)))
        assert(r.pass and r.diff_compared == 0, 'rewind differs: ' .. tostring(r.text))
        done = true
        break
      end
    end
    assert(done, 'rewind never finished')
    gd.log('SCALECHECK PASS')
  end)
  if not ok then gd.log('SCALECHECK FAIL ' .. tostring(why)) end
  gd.quit()
end)
