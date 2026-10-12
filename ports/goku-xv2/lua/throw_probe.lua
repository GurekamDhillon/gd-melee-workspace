-- Measure a forward (or other) throw: motion/anim frames, the victim's percent steps, items/articles spawned (position, speed, owner, lifetime), hitboxes.
-- Tag THROWPROBE. CFG: dir=f|b|u|d (default f; p = a pummel: A once), name=<label>. Scene: p1 = the thrower (mewtwo, geno:goku-xv2/hu), p2 = mario dummy.
-- Usage: python ports/goku-xv2/tools/kame_run.py throw_probe THROWPROBE --p1 mewtwo --cfg name=mewtwo --cfg dir=f --turbo
local C = CFG or {}
local function log(fmt, ...) gd.log('THROWPROBE ' .. string.format(fmt, ...)) end
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function tp(p, x, y) for i = 1, 60 do if pcall(gd.teleport, p, x, y) then return end gd.wait(20) end error('teleport') end
    local dir = C.dir or 'f'
    gd.set_percent(1, 0); gd.set_percent(2, 0)
    tp(1, 0, 0); tp(2, 30, 0); gd.wait(40)
    gd.input(1, {x = 60}, 3); gd.wait(30)
    tp(1, 0, 0); tp(2, 7, 0); gd.wait(3)
    local side = ((gd.player(1).facing or 1) >= 0) and 1 or -1
    tp(2, 7 * side, 0); gd.wait(2)
    gd.input(1, {buttons = 'Z'}, 2)
    local caught
    for i = 1, 60 do
      gd.wait(1)
      if gd.player(1).motion_name == 'CatchWait' then caught = i break end
    end
    assert(caught, 'no grab: ' .. tostring(gd.player(1).motion_name))
    gd.wait(8)
    local g, v = gd.player(1), gd.player(2)
    log('%s grabbed after %d frames; victim offset dx %.2f dy %.2f', tostring(C.name), caught, (v.x - g.x) * side, v.y - g.y)
    local spec = {f = {x = 127 * side}, b = {x = -127 * side}, u = {y = 127}, d = {y = -127}, p = {buttons = 'A'}}
    gd.input(1, spec[dir] or spec.f, 3)
    local p0 = gd.player(2).percent or 0
    gd.wait(1)
    local okt, tl = pcall(gd.timeline, 1)
    if okt and type(tl) == 'table' then
      log('timeline motion %s end_frame %s stop %s, %d events', tostring(tl.motion_name or tl.motion), tostring(tl.end_frame), tostring(tl.stop_reason), #(tl.events or {}))
      for i, e in ipairs(tl.events or {}) do
        if i > 70 then break end
        local parts = {}
        for k, v in pairs(e) do
          if k == 'words' and type(v) == 'table' then
            local w = {}
            for _, x in ipairs(v) do w[#w + 1] = string.format('%08X', x & 0xFFFFFFFF) end
            v = table.concat(w, ',')
          end
          parts[#parts + 1] = k .. '=' .. tostring(v)
        end
        table.sort(parts)
        log('  ev %s', table.concat(parts, ' '):sub(1, 220))
      end
    end
    local lastp, lastm, lasti = p0, nil, -1
    local nitems = 0
    for t = 1, 140 do
      gd.wait(1)
      local a, b = gd.player(1), gd.player(2)
      if a.motion_name ~= lastm then
        log('t=%d P1 %s af=%.1f | P2 %s', t, tostring(a.motion_name), a.anim_frame or -1, tostring(b.motion_name))
        lastm = a.motion_name
      end
      if t % 4 == 0 and t < 90 then log('t=%d P2 x %.1f y %.1f %s hitstun %s', t, b.x - a.x, b.y - a.y, tostring(b.motion_name), tostring(b.hitstun)) end
      if (b.percent or 0) ~= lastp then
        log('t=%d P1 %s af=%.1f victim percent %.1f -> %.1f (total %.1f) vx %.2f vy %.2f %s', t, tostring(a.motion_name), a.anim_frame or -1, lastp, b.percent, b.percent - p0,
          b.vel_x or 0, b.vel_y or 0, tostring(b.motion_name))
        lastp = b.percent
      end
      if C.hb and t >= 8 and t <= 26 and t % 3 == 0 then
        local okh, hb = pcall(gd.hitboxes, 1)
        if okh and type(hb) == 'table' then
          for _, h in ipairs(hb) do
            local ks = {}
            for k, v in pairs(h) do if type(v) == 'number' then ks[#ks + 1] = string.format('%s=%.1f', k, v) end end
            table.sort(ks)
            log('t=%d hitbox %s | victim %.1f,%.1f', t, table.concat(ks, ' '), b.x, b.y)
          end
        end
        local okv, hz = pcall(gd.hurtboxes, 2)
        if okv and type(hz) == 'table' and t == 12 then
          for _, h in ipairs(hz) do log('t=%d hurt %s state %s a(%.1f,%.1f) b(%.1f,%.1f) r=%.1f', t, tostring(h.bone), tostring(h.state), h.ax, h.ay, h.bx, h.by, h.radius) end
        end
      end
      local items = gd.items() or {}
      if #items ~= lasti then
        lasti = #items
        log('t=%d items %d', t, #items)
      end
      for _, it in ipairs(items) do
        if nitems == 1 and (it.frame_alive or 0) == 2 then
          local ks = {}
          for k, v in pairs(it) do ks[#ks + 1] = k .. '=' .. tostring(v) end
          table.sort(ks)
          log('item row: %s', table.concat(ks, ' '):sub(1, 400))
          local okh, hb = pcall(gd.hitboxes, 1, true)
          if okh and type(hb) == 'table' then log('P1 hitboxes: %d', #hb) end
        end
        if nitems >= 1 and nitems <= 2 and (it.frame_alive or 0) > 1 then
          log('t=%d   item kind %s age %s x %.1f y %.1f vx %.2f vy %.2f state %s', t, tostring(it.kind), tostring(it.frame_alive), it.x, it.y, it.vx or 0, it.vy or 0, tostring(it.state))
        end
        if (it.frame_alive or 0) <= 1 then
          nitems = nitems + 1
          log('t=%d spawn #%d kind %s owner %s x %.1f y %.1f vx %.2f vy %.2f facing %s', t, nitems, tostring(it.kind), tostring(it.owner_port), it.x, it.y, it.vx or 0, it.vy or 0, tostring(it.facing))
        end
      end
      if t > 30 and a.motion_name == 'Wait' and (b.motion_name == 'Wait' or (b.motion_name or ''):find('Fall')) then break end
    end
    log('%s done: victim total damage %.1f, %d item spawns', tostring(C.name), (gd.player(2).percent or 0) - p0, nitems)
  end)
  if not ok then log('FAIL %s', tostring(why)) end
  gd.quit()
end)
