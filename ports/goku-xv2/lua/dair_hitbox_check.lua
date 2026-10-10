-- Down air hitbox gate: Goku short-hops and presses down + A far from the dummy, and logs, for every logic frame of the
-- aerial, which hitbox ids the ENGINE reports active (gd.player(1).hitboxes). Used to confirm that the windows in
-- moves/dair.genoasm / gameplay.json are what the game really runs (Workbench hitbox-order bug, 2026-10-10).
-- Scene: mode=lab;p1=geno:goku-xv2/hu;p2=mario/cpu0 . Logs DAIRHB lines, ends with DAIRHB RESULT.
local function log(fmt, ...) gd.log('DAIRHB ' .. string.format(fmt, ...)) end

gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'script')
    gd.cpu_pad(2, {}, 1)
    gd.teleport(1, 0, 0); gd.teleport(2, 400, 0)
    gd.wait(60)
    gd.input(1, { buttons = 'X' }, 3); gd.wait(3)               -- short hop
    for _ = 1, 30 do
      local m = gd.player(1).motion_name or ''
      if m == 'JumpF' or m == 'JumpB' or m == 'JumpAerialF' then break end
      gd.wait(1)
    end
    gd.wait(6)
    gd.input(1, { y = -127, buttons = 'A' }, 2); gd.wait(1)
    local seen, max_live, first = {}, 0, nil
    for _ = 1, 60 do
      local p = gd.player(1)
      local ids = {}
      for _, h in ipairs(p.hitboxes or {}) do ids[#ids + 1] = h.id end
      table.sort(ids)
      local m = p.motion_name or '?'
      if #ids > 0 then
        first = first or p.action_frame
        max_live = math.max(max_live, #ids)
        for _, id in ipairs(ids) do seen[id] = true end
      end
      log('motion=%s action_frame=%s hitbox_ids=%s', m, tostring(p.action_frame), table.concat(ids, ','))
      if m ~= 'AttackAirLw' and first then break end
      gd.wait(1)
    end
    local distinct = 0
    for _ in pairs(seen) do distinct = distinct + 1 end
    log('RESULT first_active_action_frame=%s max_simultaneous=%d distinct_ids=%d', tostring(first), max_live, distinct)
  end)
  if not ok then gd.log('DAIRHB FAIL ' .. tostring(why)) end
  gd.quit()
end)
