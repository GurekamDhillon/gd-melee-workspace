-- Ledge set gate (Marth's ledge rows, Mario's ledge attacks; headless, turbo ok; combo package). Prints LEDGECHK lines so tools/ledge_run.py reads it:
--   python ports/goku-xv2/tools/ledge_run.py --script ledge_set_check --name goku-ledge-set --mods <combo-package/mods>
-- For Quick (percent < 100) and Slow (>= 100): fall onto the right ledge of Battlefield facing it, then
--   hang (CliffCatch -> CliffWait, held 70 frames: it must stay CliffWait), and for each option (getup / attack / roll / jump) check that
--   the expected actions play in order, each lasts its row length (+-3 frames of the cross-ported row), and the fighter ends in an ordinary state on the stage / in the air
--   (no stuck Cliff* state, no Lua fault). Result per option: LEDGECHK SET <Quick|Slow> <option>: <Action>=<frames> ... -> <end state>.
-- Row lengths (frames) are the cross-port row lengths (cross-port clip samples; the retail row length + 1):
local LEN = {
  Quick = {CliffCatch = 9, CliffClimbQuick = 34, CliffAttackQuick = 57, CliffEscapeQuick = 50, CliffJumpQuick1 = 13, CliffJumpQuick2 = 41},
  Slow  = {CliffCatch = 9, CliffClimbSlow = 60, CliffAttackSlow = 71, CliffEscapeSlow = 80, CliffJumpSlow1 = 20, CliffJumpSlow2 = 41},
}
local TOL = 3
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    local function name() return tostring(gd.player(1).motion_name) end
    local function tp(p, x, y)
      for i = 1, 80 do
        if pcall(gd.teleport, p, x, y) then return end
        gd.wait(30)
      end
      error('could not teleport port ' .. p)
    end
    local function nofault()
      local lua = assert(gd.fighter_lua(1))
      assert(lua.faults == 0, 'Lua fault: ' .. tostring(lua.last_fault))
    end
    local sb = assert(gd.stage_bounds(), 'no stage bounds')
    local R, top = sb.main_floor.right, sb.main_floor.top
    local bads = {}
    local function chk(c, m) if not c then bads[#bads + 1] = m; gd.log('LEDGECHK FAIL ' .. m) end end

    -- fall onto the ledge facing it; returns true once CliffCatch is entered
    local function grab_ledge()
      for _, p in ipairs({{8, -14}, {5, -10}, {12, -18}, {3, -8}, {16, -24}}) do
        gd.input(1, {}, 1); gd.wait(2)
        tp(1, R - 30, top); tp(2, sb.main_floor.left + 20, top)
        gd.wait(20)
        gd.input(1, {x = -127}, 6); gd.wait(8)       -- turn to face the stage (left) on the floor
        gd.input(1, {}, 1); gd.wait(14)
        tp(1, R + p[1], top + p[2]); gd.wait(1)
        for t = 1, 45 do
          gd.input(1, {x = -40}, 1); gd.wait(1); nofault()
          if name() == 'CliffCatch' then return true end
        end
      end
      return false
    end

    -- run one option; returns the list {action, frames} and the final state
    local function run_option(speed, pct, opt, stick, button)
      gd.set_percent(1, pct); gd.set_percent(2, 0)
      if not grab_ledge() then chk(false, speed .. ' ' .. opt .. ': never caught the ledge'); return end
      local seq, cur, curmax = {}, 'CliffCatch', 0
      local function push() seq[#seq + 1] = {cur, curmax + 1} end
      -- hang: CliffCatch then CliffWait, held 70 frames
      local waited = 0
      for t = 1, 40 do
        gd.input(1, {}, 1); gd.wait(1); nofault()
        local n = name()
        if n ~= cur then push(); cur = n; curmax = 0 end
        curmax = math.max(curmax, gd.player(1).action_frame or 0)
        if n == 'CliffWait' then waited = waited + 1 end
        if waited >= 70 then break end
      end
      for t = waited, 70 do
        gd.input(1, {}, 1); gd.wait(1); nofault()
        local n = name()
        if n ~= cur then push(); cur = n; curmax = 0 end
        curmax = math.max(curmax, gd.player(1).action_frame or 0)
        waited = waited + (n == 'CliffWait' and 1 or 0)
      end
      chk(cur == 'CliffWait', speed .. ' ' .. opt .. ': did not hang in CliffWait (state ' .. cur .. ')')
      -- the option: hold for a few frames, then release and follow the states until an ordinary one
      local inp = {x = stick.x or 0, y = stick.y or 0}
      if button then inp.buttons = button end
      local held = 0
      for t = 1, 400 do
        if held < 3 then gd.input(1, inp, 1); held = held + 1 else gd.input(1, {}, 1) end
        gd.wait(1); nofault()
        local n = name()
        if n ~= cur then push(); cur = n; curmax = 0 end
        curmax = math.max(curmax, gd.player(1).action_frame or 0)
        if n:sub(1, 5) ~= 'Cliff' and t > 8 then
          if n ~= 'Fall' and n ~= 'JumpF' and n ~= 'JumpB' and n ~= 'JumpAerialF' and n ~= 'JumpAerialB' then break end
          if t > 60 then break end
        end
      end
      push()
      local parts = {}
      for _, s in ipairs(seq) do parts[#parts + 1] = s[1] .. '=' .. s[2] end
      local final = cur
      gd.log(string.format('LEDGECHK SET %s %s: %s -> %s', speed, opt, table.concat(parts, ' '), final))
      chk(final:sub(1, 5) ~= 'Cliff', speed .. ' ' .. opt .. ': stuck in ' .. final)
      for _, s in ipairs(seq) do
        local want = LEN[speed][s[1]]
        if want then chk(math.abs(s[2] - want) <= TOL, string.format('%s %s: %s lasted %d, row length %d', speed, opt, s[1], s[2], want)) end
      end
      return seq
    end

    local function has(seq, nm) for _, s in ipairs(seq or {}) do if s[1] == nm then return true end end return false end
    for _, speed in ipairs({'Quick', 'Slow'}) do
      local pct = speed == 'Quick' and 0 or 130
      local sfx = speed
      local s
      s = run_option(speed, pct, 'getup', {x = -127}); chk(has(s, 'CliffClimb' .. sfx), speed .. ' getup did not play CliffClimb' .. sfx)
      s = run_option(speed, pct, 'attack', {}, 'A');  chk(has(s, 'CliffAttack' .. sfx), speed .. ' attack did not play CliffAttack' .. sfx)
      s = run_option(speed, pct, 'roll', {}, 'R'); chk(has(s, 'CliffEscape' .. sfx), speed .. ' roll did not play CliffEscape' .. sfx)
      s = run_option(speed, pct, 'jump', {}, 'X');    chk(has(s, 'CliffJump' .. sfx .. '1') and has(s, 'CliffJump' .. sfx .. '2'), speed .. ' jump did not play CliffJump' .. sfx .. '1/2')
    end
    assert(#bads == 0, table.concat(bads, '; '))
  end)
  if ok then gd.log('LEDGECHK RESULT PASS') else gd.log('LEDGECHK RESULT FAIL ' .. tostring(why)) end
  gd.quit()
end)
