-- Aerial landing gate (owner #7, #12): Goku short-hops, throws each aerial at several delays (so he lands in different parts of the clip),
-- with and without an L-cancel, and logs per landing: the motion trace with frame counts, the landing lag (frames spent in Landing*), and the
-- lowest posed JOINT height relative to the floor (baseline = the same on a grounded Wait). A joint below the baseline - SINK_EPS = sinking.
-- Scene: mode=lab;p1=geno:goku-xv2/hu;p2=mario/cpu0 . Logs LANDCHECK lines, ends with LANDCHECK RESULT.
local SINK_EPS = 0.9
local function log(fmt, ...) gd.log('LANDCHECK ' .. string.format(fmt, ...)) end
local FREE = {}
for _, n in ipairs({ "Wait", "WalkSlow", "WalkMiddle", "WalkFast", "Turn", "Dash", "Run", "Squat", "SquatWait" }) do FREE[n] = true end
local function grounded_free(p) return FREE[p.motion_name or ""] == true and not (p.in_hitlag or (p.hitlag or 0) > 0) end

local function min_joint_y()
  local js = gd.joints(1)
  local m, root = nil, gd.player(1).y or 0
  for _, j in ipairs(js or {}) do
    if j.valid and j.y then if not m or j.y < m then m = j.y end end
  end
  return (m or 0) - root, root
end

local AERIALS = {
  nair = { buttons = 'A' },
  fair = { x = 100, buttons = 'A' },
  bair = { x = -100, buttons = 'A' },
  uair = { y = 100, buttons = 'A' },
  dair = { y = -100, buttons = 'A' },
}
local ORDER = { 'nair', 'fair', 'bair', 'uair', 'dair' }

gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    gd.teleport(2, 60, 0)
    gd.wait(60)
    for _ = 1, 100 do if grounded_free(gd.player(1)) then break end gd.wait(1) end
    local base = min_joint_y()
    log('baseline: lowest joint %.2f relative to the root on a grounded Wait', base)
    local worst, bad, cases = 0, 0, 0
    for _, name in ipairs({'fair'}) do
      for _, lc in ipairs({ false }) do
        for _, delay in ipairs({ 8 }) do
          for _ = 1, 200 do if grounded_free(gd.player(1)) then break end gd.wait(1) end
          gd.teleport(1, -20, 0); gd.wait(20)
          gd.input(1, { buttons = 'X' }, 3); gd.wait(3)
          for _ = 1, 30 do
            local m = gd.player(1).motion_name or ''
            if m == 'JumpF' or m == 'JumpB' or m == 'JumpAerialF' then break end
            gd.wait(1)
          end
          gd.wait(delay)
          local spec = AERIALS[name]
          gd.input(1, { x = spec.x, y = spec.y, buttons = spec.buttons }, 2); gd.wait(2)
          local trace, last, n, land_n, sink, sink_f, seen_air = {}, nil, 0, 0, 0, nil, false
          local lc_pressed = false; local dbg = 0
          for f = 1, 160 do
            local p = gd.player(1)
            local m = p.motion_name or '?'
            if m ~= last then
              if last then trace[#trace + 1] = string.format('%s:%d', last, n) end
              last, n = m, 0
            end
            n = n + 1
            if p.airborne then seen_air = true
              if (p.y or 99) < 9 then
                local js = gd.joints(1); local mn, who, ty = 1e9, -1, nil
                for _, j in ipairs(js or {}) do if j.valid and j.y and j.y < mn then mn, who = j.y, j.index end end
                if (p.y or 99) < 0.5 then
                  local near = {}
                  for _, j in ipairs(js or {}) do if j.valid and j.y and j.y > -1.2 and j.y < 1.2 then near[#near + 1] = string.format('%d:%.2f', j.index, j.y) end end
                  log('  NEAR0 root=%.2f joints near floor: %s', p.y, table.concat(near, ' '))
                end
                log('  AIR %s d=%d motion=%s animf=%s root_y=%.2f vy=%s minjoint_abs=%.2f (joint %s)', name, delay, m, tostring(p.anim_frame), p.y or -1, tostring(p.vy or p.speed_y), mn, tostring(who))
              end
            end
            if lc and p.airborne and not lc_pressed and (p.y or 99) < 7 and (p.vy or p.speed_y or -1) < 0 then
              gd.input(1, { l = 200 }, 4); lc_pressed = true
            end
            if seen_air and not p.airborne then
              dbg = (dbg or 0) + 1
              if dbg <= 8 then
                local js = gd.joints(1); local mn, who = 1e9, -1
                for _, j in ipairs(js or {}) do if j.valid and j.y and j.y < mn then mn, who = j.y, j.index end end
                log('  DBG %s d=%d t+%d motion=%s animf=%s root_y=%.2f minjoint_abs=%.2f (joint %s)', name, delay, dbg, m, tostring(p.anim_frame), p.y or -1, mn, tostring(who))
              end
              local rel, root = min_joint_y()
              local s = base - rel
              if s > sink then sink, sink_f = s, f end
              if m:find('Landing') then land_n = land_n + 1 end
            end
            if seen_air and grounded_free(p) and f > 15 then break end
            gd.wait(1)
          end
          trace[#trace + 1] = string.format('%s:%d', last or '?', n)
          cases = cases + 1
          local flag = sink > SINK_EPS and 'SINK' or 'ok'
          if sink > SINK_EPS then bad = bad + 1 end
          if sink > worst then worst = sink end
          log('%s lcancel=%s delay=%d landing_frames=%d max_sink=%.2f(f%s) %s trace=%s', name, tostring(lc), delay, land_n, sink, tostring(sink_f), flag, table.concat(trace, ' '))
        end
      end
    end
    log('RESULT cases=%d sinking=%d worst_sink=%.2f', cases, bad, worst)
  end)
  if not ok then gd.log('LANDCHECK FAIL ' .. tostring(why)) end
  gd.quit()
end)
