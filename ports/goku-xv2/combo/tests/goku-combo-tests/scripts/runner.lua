-- @name: Goku combo route tests (geno 11 combo graph)
-- @gameplay: true
-- Plays authored combo specs (missions/combo-specs/<id>.txt, listed in index.txt) against P2 for every percent x DI cell and
-- reads each link the way the LAB's COMBO mode does (docs/geno.md 14.15): a link is TRUE when the next hit lands before the
-- victim's first actionable frame after the previous hit; otherwise it is escapable by `gap` frames. It also checks the INTENT:
-- the combo routes taken (gd.combo) must be exactly the spec's `routes`, in order (which ender follows which string position).
-- missions/combo-run.txt (written by run_combo_tests.py): vs = <fighter>, specs = id,id,..., visible = 0|1
-- Output: COMBOTEST lines, then "COMBOTEST RESULT: PASS" or "COMBOTEST RESULT: FAIL <cells>". P1 is Goku (human port, gd.input),
-- P2 the victim (human port: neutral except its DI). Offline LAB on FD.
local K = gd.kit
local run = { vs = "?", specs = {}, visible = false }
local specs, failed_cells, cells_run = {}, {}, 0
local si, cell, phase, t, quit_t = 1, nil, "boot", 0, 0
local clean_saved = false
local W = 0xF2EEE6FF
local GOLD, OK, BAD, DIM = 0xF2C14EFF, 0x6BD17AFF, 0xFF5A4FFF, 0x9A968FFF

local function log(fmt, ...) gd.log("COMBOTEST " .. string.format(fmt, ...)) end
local function trim(s) return (s:gsub("^%s+", ""):gsub("%s+$", "")) end
local function list(s)
  local out = {}
  for x in (s or ""):gmatch("[^,]+") do out[#out + 1] = trim(x) end
  return out
end
local function kv(text)
  local o = {}
  for line in (text or ""):gmatch("[^\r\n]+") do
    local k, v = line:match("^%s*([%w_]+)%s*=%s*(.-)%s*$")
    if k and not line:match("^%s*#") then o[k] = v end
  end
  return o
end

local function load_specs()
  local cfg = kv(gd.mod_read("missions/combo-run.txt") or "")
  run.vs = cfg.vs or "?"
  run.visible = cfg.visible == "1"
  run.trace = cfg.trace == "1"
  run.shield = cfg.shield == "1"
  run.modes = list(cfg.modes or "single,hold,grab,spot,roll,jump")
  local ids = list(cfg.specs or "")
  if #ids == 0 then ids = list((gd.mod_read("missions/combo-specs/index.txt") or ""):gsub("\r?\n", ",")) end
  for _, id in ipairs(ids) do
    local text = gd.mod_read("missions/combo-specs/" .. id .. ".txt")
    if text then
      local s = kv(text)
      s.id = id
      s.tokens = list(s.inputs)
      s.routes = list(s.routes or "")
      s.percents = list(s.percents or "0")
      s.dis = list(s.di or "none")
      local raw_expect = s.expect_true or ""
      s.expect_true = {}
      for _, p in ipairs(list(raw_expect)) do s.expect_true[tonumber(p)] = true end
      s.expect_di, s.expect_vs = {}, {}
      for _, d in ipairs(list(kv(text).expect_di or "")) do s.expect_di[d] = true end
      for _, v in ipairs(list(kv(text).expect_vs or "")) do s.expect_vs[v] = true end
      s.p1x, s.dist = tonumber(s.p1x or "-20"), tonumber(s.distance or "9")
      s.ki = tonumber(s.ki or "0")
      s.ki_need = s.ki_route and true or false
      specs[#specs + 1] = s
    else
      log("missing spec %s", id)
      failed_cells[#failed_cells + 1] = id .. ":missing"
    end
  end
end

-- the LAB's actionable reading (lab.lua LD.actionable, stage D): free states, IASA, a landing past its lag, a damage state out of hitstun
local FREE = {}
for _, n in ipairs({ "Wait", "WalkSlow", "WalkMiddle", "WalkFast", "Turn", "Dash", "Run", "RunDirect", "Squat", "SquatWait", "SquatRv",
  "Fall", "FallF", "FallB", "FallAerial", "FallAerialF", "FallAerialB", "JumpF", "JumpB", "JumpAerialF", "JumpAerialB", "GuardOn",
  "Guard", "CliffWait", "Ottotto", "OttottoWait", "DownWaitU", "DownWaitD" }) do FREE[n] = true end
local function actionable(p)
  local name = p.motion_name or ""
  if p.in_hitlag then return false end
  if p.iasa or FREE[name] then return true end
  if name == "Landing" then return (p.anim_frame or 0) >= 4 end
  if name == "DamageFall" or name:find("^DamageFly") or name:find("^Damage%a+%d$") then return not p.in_hitstun end
  return false
end

-- an attacker input token: A A> A^ Av (light), C> C< C^ Cv (heavy, the C-stick), B B> B^ Bv (special), X (jump), Z (grab),
-- S> S^ Sv S< (the stick alone: throws). Directions are facing-relative.
local function pad_for(tok, facing)
  local b, d = tok:sub(1, 1), tok:sub(2, 2)
  local x, y = 0, 0
  if d == ">" then x = 127 * facing elseif d == "<" then x = -127 * facing elseif d == "^" then y = 127 elseif d == "v" then y = -127 end
  if b == "A" then return { buttons = "A", x = math.floor(x * 0.6), y = math.floor(y * 0.6) } end
  if b == "C" then return { cx = x, cy = y } end
  if b == "B" then return { buttons = "B", x = x, y = y } end
  if b == "X" then return { buttons = "X", x = x } end
  if b == "Z" then return { buttons = "Z" } end
  return { x = x, y = y }
end

-- DI on the victim: none / in / out / survival / random (seeded per cell), from the hit's launch angle; two steps like the LAB's
-- clean DI (just past the stick line, then the full stick) so the DI is not also an SDI flick
local function di_stick(how, c)
  local h = c.lasthit
  if not h or how == "none" then return 0, 0 end
  local a = h.angle or 45
  if a == 361 then a = h.grounded and 0 or 44 end
  if how == "random" then
    c.seed = (c.seed * 1103515245 + 12345) % 2147483648
    local pick = ({ "none", "in", "out", "survival" })[(c.seed // 65536) % 4 + 1]
    c.di_pick = c.di_pick or pick
    how = c.di_pick
    if how == "none" then return 0, 0 end
  end
  local dir = h.dir
  local lx, ly = math.cos(math.rad(a)) * dir, math.sin(math.rad(a))
  local px, py = -ly, lx -- the CCW perpendicular
  if how == "in" then
    if px * dir > 0 then px, py = -px, -py end
  elseif how == "out" then
    if px * dir < 0 then px, py = -px, -py end
  else -- survival: the perpendicular that turns the launch toward 45 degrees on its side
    local goal = math.rad(dir > 0 and 45 or 135)
    local r1 = math.atan(ly + 0.3 * py, lx + 0.3 * px)
    local r2 = math.atan(ly - 0.3 * py, lx - 0.3 * px)
    if math.abs(r2 - goal) < math.abs(r1 - goal) then px, py = -px, -py end
  end
  return px, py
end

function on_hit(attacker, victim, info)
  if not cell or cell.done or attacker ~= 1 or victim ~= 2 then return end
  local now = gd.match().frame
  local p1, p2 = gd.player(1), gd.player(2)
  local h = { f = now, move = p1 and p1.motion_name or "?", dealt = info.dealt or 0, angle = info.angle,
              grounded = info.victim_grounded, dir = (p2 and p1 and p2.x >= p1.x) and 1 or -1, item = info.item }
  cell.hits[#cell.hits + 1] = h
  cell.lasthit = h
  cell.lag_f = 0
end

local function new_cell(s, pct, di)
  local seed = 7
  for ch in (s.id .. pct .. di):gmatch(".") do seed = (seed * 31 + ch:byte()) % 2147483648 end
  return { s = s, pct = tonumber(pct), di = di, hits = {}, k = 1, taken = {}, last_taken = -1, t = 0, seed = seed, lag_f = 0,
           press_f = nil, done = false }
end

local function route_open(name)
  local c = gd.combo(1, true)
  if not c then return false end
  for _, r in ipairs(c.routes) do
    if r.name == name and r.state >= 1 then return true end
  end
  return false
end

-- the routes the next token is meant to take: the spec's routes, one per non-first, non-"~" token, in order
local function token_route(s, k)
  local n = 0
  for i = 2, k do
    if s.tokens[i]:sub(1, 1) ~= "~" and not s.tokens[i]:find("@") then n = n + 1 end
  end
  local tok = s.tokens[k]
  if k == 1 or tok:sub(1, 1) == "~" or tok:find("@") then return nil end
  return s.routes[n]
end

local function finish(c)
  c.done = true
  local s = c.s
  local links, trues, gaps, first_drop = 0, 0, {}, nil
  -- the victim's first actionable frame after each hit (recorded per frame in c.act)
  for i = 1, #c.hits - 1 do
    local h, nx = c.hits[i], c.hits[i + 1]
    links = links + 1
    local free = h.free
    if free == nil or free >= nx.f then
      trues = trues + 1
      gaps[#gaps + 1] = string.format("T%+d", free and (free - nx.f) or 0)
    else
      gaps[#gaps + 1] = string.format("E%d", nx.f - free)
      first_drop = first_drop or i
    end
  end
  local got = table.concat(c.taken, ">")
  local want = table.concat(s.routes, ">")
  local intent_ok = got == want
  local all_true = links > 0 and trues == links and #c.hits >= tonumber(s.min_hits or (#s.routes + 1))
  local expected = s.expect_true[c.pct] and c.di ~= "random"
  -- a spec may narrow where a true combo is intended: expect_di (the DI cells, e.g. none) and expect_vs (the victims it is tuned for)
  if expected and next(s.expect_di) and not s.expect_di[c.di] then expected = false end
  if expected and next(s.expect_vs) and not s.expect_vs[run.vs] then expected = false end
  -- only a cell the spec EXPECTS to be a true combo can fail; elsewhere the cell is a read (a dropped string is a result, not a failure)
  local ok = (not expected) or (intent_ok and all_true)
  log("cell spec=%s vs=%s pct=%d di=%s hits=%d true=%d/%d gaps=%s drop=%s intent=%s taken=[%s] ki=%.1f expect=%s -> %s",
      s.id, run.vs, c.pct, c.di, #c.hits, trues, links, table.concat(gaps, ","), first_drop and ("link" .. first_drop) or "-",
      intent_ok and "ok" or ("want[" .. want .. "]"), got, c.ki_end or 0, expected and "true" or "read", ok and "PASS" or "FAIL")
  cells_run = cells_run + 1
  if not ok then failed_cells[#failed_cells + 1] = string.format("%s/%s/%d/%s", s.id, run.vs, c.pct, c.di) end
end

local queue = {}
local function next_spec_cells(s)
  queue = {}
  if run.shield then
    -- SHIELD cells: one per dummy mode, at 0% (percent and DI do not matter on a shield); a spec says `shield = skip` when it has nothing to block
    if s.shield ~= "skip" then
      for _, mode in ipairs(run.modes) do queue[#queue + 1] = { pct = "0", di = "none", shield = mode } end
    end
    return
  end
  for _, pct in ipairs(s.percents) do
    for _, di in ipairs(s.dis) do queue[#queue + 1] = { pct = pct, di = di } end
  end
end

-- ===================================================================================================================================
-- SHIELD cells (owner rules, 2026-10-09): the dummy shields; the attacker MASHES the spec's tokens (one every 6 frames, cycling: A spam,
-- A A C, side-B ...). Asserted: (1) no combo route fires on block (gd.combo taken stays 0: only Melee-native follow-ups); (2) no closed
-- loop: of 3 consecutive blocked moves the defender is actionable at least once between them; (3) no shield break within 8 blocked hits.
-- Reported per blocked move: the attacker's frame advantage on block (victim free frame minus attacker free frame, + = the attacker acts
-- first), the shield HP lost, the pushback, the gap (frames between the defender's first actionable frame and the next blocked hit), and
-- what the dummy's out-of-shield option did.
local MASH_PERIOD, SHIELD_FRAMES = 6, 300
local function add_block(c, p1, p2, now)
  local prev = c.blocks[#c.blocks]
  if prev and now - prev.f <= 1 then return end -- the hook and the motion reading saw the same hit
  -- one blocked MOVE = consecutive shield hits of the same attacker motion without its action frame going back
  local same = prev and prev.move == (p1.motion_name or "?") and (p1.action_frame or 0) >= prev.af and now - prev.f < 40
  c.blocks[#c.blocks + 1] = { f = now, move = p1.motion_name or "?", af = p1.action_frame or 0, x2 = p2.x, x1 = p1.x,
                              sh_before = c.prev_shield or p2.shield, sh_after = p2.shield, same = same and true or false }
end

-- the engine's hook (a queued observation; it can be missed when the queue is busy) and, as the reading that never misses, the defender's own
-- shield-stun motion: GuardSetOff entered, or restarted by a second hit (its action frame goes back)
function on_shield_hit(port, action, sub)
  if not cell or cell.done or not cell.shield or port ~= 2 then return end
  local p1, p2 = gd.player(1), gd.player(2)
  if not p1 or not p2 then return end
  add_block(cell, p1, p2, gd.match().frame)
end

local function mash_pad(tok, facing)
  local raw = tok:gsub("^~", ""):gsub("@.*$", "")
  return pad_for(raw, facing)
end

local function shield_frame(c)
  local s = c.s
  local p1, p2 = gd.player(1), gd.player(2)
  local now = gd.match().frame
  c.t = c.t + 1
  local dir = (p1.x <= p2.x) and 1 or -1
  if c.t == 1 or c.t == 3 or c.t == 12 then gd.log(string.format('COMBOSHIELD dbg t=%d shield=%s motion=%s', c.t, tostring(p2.shield), tostring(p2.motion_name))) end
  if c.t == 1 then gd.set_shield(2, 60) end -- the savestate carries the last cell's shield damage: every cell starts from a full shield
  -- the dummy: shield held until its out-of-shield option, then neutral
  if not c.oos then
    gd.input(2, { buttons = "R", r = 255 }, 1)
  end
  if p2.shield and p2.shield <= 0.5 and (p2.motion_name or ""):find("Break") then c.broke = true end
  c.motions[p2.motion_name or "?"] = true
  do
    local m2, af2 = p2.motion_name or "", p2.action_frame or 0
    if m2 == "GuardSetOff" and (c.pm2 ~= "GuardSetOff" or af2 <= (c.paf2 or 99)) then add_block(c, p1, p2, now) end
    c.pm2, c.paf2 = m2, af2
  end
  -- block bookkeeping: the defender's / attacker's first free frame after each blocked move's last hit
  for i, b in ipairs(c.blocks) do
    if b.free == nil and now > b.f and not p2.in_hitlag and actionable(p2) then
      b.free = now
      b.dx = math.abs(p2.x - b.x2)
      b.gapx = math.abs(p2.x - p1.x)
    end
    if b.afree == nil and now > b.f and not p1.in_hitlag and actionable(p1) then b.afree = now end
  end
  c.prev_shield = p2.shield
  -- out-of-shield option at the defender's first actionable frame after a blocked hit
  local last = c.blocks[#c.blocks]
  local mode = c.shield
  if mode ~= "hold" and mode ~= "single" and last and not c.oos and last.free == now then
    c.oos = { f = now, mode = mode }
    if mode == "grab" then gd.input(2, { buttons = "Z" }, 2)
    elseif mode == "spot" then gd.input(2, { buttons = "R", r = 255, y = -127 }, 2)
    elseif mode == "roll" then gd.input(2, { buttons = "R", r = 255, x = 127 * dir }, 2)
    elseif mode == "jump" then gd.input(2, { buttons = "X" }, 2)
    elseif mode == "upb" then gd.input(2, { buttons = "B", y = 127 }, 2) end
  elseif c.oos and c.oos.mode == "jump" and not c.oos.aired and p2.airborne and now - c.oos.f < 20 then
    c.oos.aired = now
    gd.input(2, { buttons = "A" }, 2) -- the aerial after the shield jump (nair)
  end
  if c.oos and not c.oos.hit_f then
    local m1 = p1.motion_name or ""
    if m1:find("Capture") or m1:find("^Damage") or m1:find("^Thrown") or m1:find("Down") then c.oos.hit_f = now end
  end
  -- the attacker: wait for the shield to be up, then mash
  c.up = c.up or (((p2.motion_name or "") == "Guard") and now or nil)
  if c.up and now >= c.up + 4 and (now - c.up - 4) % MASH_PERIOD == 0 and not (c.shield == "single" and (c.mk or 0) >= 1) then
    c.mk = (c.mk or 0) + 1
    local tok = c.pool[(c.mk - 1) % #c.pool + 1]
    gd.input(1, mash_pad(tok, p1.facing or 1), 2)
    if c.mk <= 3 then gd.log(string.format('COMBOSHIELD dbg press %d tok=%s p1=%s af=%s (%.1f,%.1f) p2=%s (%.1f,%.1f)', c.mk, tok, tostring(p1.motion_name), tostring(p1.action_frame), p1.x, p1.y, tostring(p2.motion_name), p2.x, p2.y)) end
  end
  local cs = gd.combo(1)
  -- routes count only while the victim has not been hit: once the dummy has left its shield and been hit, routes on that hit are legitimate
  if cs and c.taken0 == nil then c.taken0 = cs.taken end -- gd.combo's taken counts since the spawn: the savestate carries the earlier specs' links
  if cs and #c.hits == 0 then c.routes_taken = cs.taken - c.taken0 end
  if cs and cs.taken ~= (c.seen_taken or c.taken0 or 0) then
    c.seen_taken = cs.taken
    c.rnames = (c.rnames or "") .. string.format("%s@%d(hits=%d,blk=%d) ", cs.last_name or "?", now, #c.hits, #c.blocks)
  end
  if c.up and now - c.up > (c.shield == "single" and 100 or SHIELD_FRAMES) then c.done = true end
  if c.t > SHIELD_FRAMES + 120 then c.done = true end
  if not c.done then return end
  -- ---- the verdict
  local moves = {}
  for _, b in ipairs(c.blocks) do
    if b.same and #moves > 0 then
      local m = moves[#moves]
      m.last = b
      m.hits = m.hits + 1
      m.hp = m.hp + math.max(0, (b.sh_before or 0) - (b.sh_after or 0))
    else
      moves[#moves + 1] = { first = b, last = b, hits = 1, hp = math.max(0, (b.sh_before or 0) - (b.sh_after or 0)) }
    end
  end
  local adv, gaps, push, hp = {}, {}, {}, {}
  local chain, best = 0, 0
  for j, m in ipairs(moves) do
    local lb = m.last
    local a = (lb.free and lb.afree) and (lb.free - lb.afree) or nil
    adv[#adv + 1] = a and string.format("%+d", a) or "?"
    hp[#hp + 1] = string.format("%.1f", m.hp)
    push[#push + 1] = lb.dx and string.format("%.1f", lb.dx) or "?"
    local nx = moves[j + 1]
    chain = chain + 1 -- this move joins the run
    if nx then
      local gap = lb.free and (nx.first.f - lb.free) or nil
      gaps[#gaps + 1] = gap and tostring(gap) or "lock"
      if gap and gap >= 1 then chain = 0 end -- the defender was actionable before the next blocked move
    else
      gaps[#gaps + 1] = lb.free and "free" or "lock"
    end
    if chain > best then best = chain end
  end
  local taken = c.routes_taken or 0
  local fails = {}
  if #c.blocks == 0 then fails[#fails + 1] = "noblock" end
  if taken > 0 then fails[#fails + 1] = "route-on-block" end
  if best > 2 then fails[#fails + 1] = "closed-loop" end
  -- rule 3: no automatic shield break from a string. Holding a shield drains it by itself (a 300-frame hold breaks one with 8 blocked jabs),
  -- so the assertion is on what the blocked hits TAKE: the first 6 blocked moves must not cost half a full shield (30 of 60)
  local taken_hp = 0
  for j = 1, math.min(6, #moves) do taken_hp = taken_hp + moves[j].hp end
  if taken_hp >= 30 then fails[#fails + 1] = string.format("shield-damage-%.0f", taken_hp) end
  local mot = {}
  for k in pairs(c.motions) do mot[#mot + 1] = k end
  table.sort(mot)
  gd.log('COMBOSHIELD motions ' .. s.id .. ' ' .. run.vs .. ' ' .. c.shield .. ': ' .. table.concat(mot, ','))
  local oos = c.oos and string.format("%s@+%d", c.oos.mode, c.oos.f - (c.blocks[1] and c.blocks[1].f or c.oos.f)) or "-"
  gd.log(string.format("COMBOSHIELD cell spec=%s vs=%s mode=%s blocks=%d moves=%d routes=%d chain=%d adv=[%s] hp=[%s] push=[%s] gap=[%s] oos=%s connects=%s break=%s hits=%d fired=<%s> -> %s%s",
    s.id, run.vs, c.shield, #c.blocks, #moves, taken, best, table.concat(adv, ","), table.concat(hp, ","), table.concat(push, ","), table.concat(gaps, ","),
    oos, tostring(c.oos ~= nil and c.oos.hit_f ~= nil), tostring(c.broke or false), #c.hits, c.rnames or "", #fails == 0 and "PASS" or "FAIL", #fails == 0 and "" or (" " .. table.concat(fails, "+"))))
  cells_run = cells_run + 1
  if #fails > 0 then failed_cells[#failed_cells + 1] = string.format("%s/%s/shield-%s", s.id, run.vs, c.shield) end
end

local function cell_frame(c)
  local s = c.s
  local p1, p2 = gd.player(1), gd.player(2)
  local now = gd.match().frame
  c.t = c.t + 1
  -- the victim: actionable after the last hit?
  local last = c.hits[#c.hits]
  if last and last.free == nil and now > last.f and actionable(p2) then last.free = now end
  -- a throw has no hit event: the grab and the throw are one hit, dated when the victim leaves Thrown* (the LAB's COMBO reading)
  local vn = p2.motion_name or ""
  if vn:find("^Thrown") then c.thrown = true
  elseif c.thrown then
    c.thrown = nil
    c.hits[#c.hits + 1] = { f = now, move = "Throw", dealt = 0, dir = 1 }
  end
  -- the victim's DI while it is in hitlag
  if p2.in_hitlag and c.lasthit then
    c.lag_f = c.lag_f + 1
    local x, y = di_stick(c.di, c)
    local m = c.lag_f <= 3 and 0.3 or 1.0
    gd.input(2, { x = math.floor(x * 127 * m), y = math.floor(y * 127 * m) }, 1)
  end
  -- the routes taken (gd.combo counts them)
  local cs = gd.combo(1)
  if cs and cs.taken ~= c.last_taken then
    if c.last_taken >= 0 then c.taken[#c.taken + 1] = cs.last_name end
    c.last_taken = cs.taken
  end
  c.ki_end = cs and cs.ki or 0
  if run.trace and c.k > 5 then log("trace f=%d p1=%s af=%d (%.1f,%.1f) p2=%s (%.1f,%.1f)", now, p1.motion_name or "?", p1.action_frame or -1, p1.x, p1.y, p2.motion_name or "?", p2.x, p2.y) end
  -- the attacker's next token
  local tok = s.tokens[c.k]
  if tok and not c.wait_release then
    local fire = false
    local raw = tok:gsub("^~", ""):gsub("@.*$", "")
    if c.k == 1 then
      fire = c.t >= 2 and actionable(p1)
    elseif tok:find("@") then
      fire = p1.action_frame == tonumber(tok:match("@(%d+)"))
    elseif tok:sub(1, 1) == "~" then
      fire = ((actionable(p1) and not (p1.motion_name or ""):find("^Catch")) or p1.motion_name == "CatchWait") and not p1.in_hitlag
    else
      fire = route_open(token_route(s, c.k))
    end
    if fire then
      gd.input(1, pad_for(raw, p1.facing or 1), 2)
      log("press spec=%s k=%d tok=%s motion=%s af=%d hitlag=%s p1=(%.1f,%.1f) p2=(%.1f,%.1f) %s", s.id, c.k, tok, p1.motion_name, p1.action_frame, tostring(p1.in_hitlag), p1.x, p1.y, p2.x, p2.y, p2.motion_name or "?")
      c.k = c.k + 1
      c.press_f = now
      c.wait_release = 3
    elseif c.press_f and now - c.press_f > 90 then
      c.k = #s.tokens + 1 -- the next link never opened: the string dropped
    end
  elseif c.wait_release then
    c.wait_release = c.wait_release - 1
    if c.wait_release <= 0 then c.wait_release = nil end
  end
  -- the end: every token pressed, then the victim free for 30 frames (or 240 frames after the last press)
  if c.k > #s.tokens then
    c.end_t = c.end_t or 0
    c.end_t = c.end_t + 1
    local lh = c.hits[#c.hits]
    if (lh and lh.free and now - lh.free >= 30) or c.end_t > 240 then finish(c) end
  end
end

function on_frame()
  if phase == "end" then
    quit_t = quit_t + 1
    if quit_t == 30 and not run.visible then gd.quit() end
    return
  end
  if not gd.match().active then return end
  local p1, p2 = gd.player(1), gd.player(2)
  if not p1 or not p2 then return end
  t = t + 1
  if phase == "boot" then
    load_specs()
    if gd.combo(1) == nil then
      log("P1 has no combo graph (is the geno 11 Goku package mounted?)")
      gd.log("COMBOTEST RESULT: FAIL no combo graph")
      phase = "end"
      return
    end
    phase, t = "place", 0
    return
  end
  local s = specs[si]
  if s == nil then
    gd.log(#failed_cells == 0 and string.format("COMBOTEST RESULT: PASS (%d cells, vs %s)", cells_run, run.vs)
      or ("COMBOTEST RESULT: FAIL " .. table.concat(failed_cells, " ")))
    phase = "end"
    return
  end
  if phase == "place" then
    -- both standing, then placed: P1 at the spec's x, P2 `distance` in front, a savestate the cells start from
    -- wait for both to be standing and free first (the match's entry, the last spec's end), then place, settle, save
    if t == 1 then s.placed = nil end
    if t == 1 and clean_saved then gd.loadstate(2) end -- every spec starts from the same clean state (the last spec's cells leave P1 / P2 anywhere)
    if not s.placed then
      local untouchable = (tonumber(p2.intangible) or 0) > 0 or (tonumber(p2.invincible) or 0) > 0 or p2.intangible == true or p2.invincible == true
      if t >= 30 and actionable(p1) and actionable(p2) and not p1.airborne and not p2.airborne and not untouchable then
        if not clean_saved then gd.savestate(2) clean_saved = true end
        gd.teleport(1, s.p1x, 0)
        gd.teleport(2, s.p1x + s.dist, s.p2y and tonumber(s.p2y) or 0)
        s.placed = t
      end
      return
    end
    if t == s.placed + 60 then gd.savestate(1) end
    if t == s.placed + 64 then next_spec_cells(s) phase, t = "load", 0 end
    return
  end
  if phase == "load" then
    local q = queue[1]
    if q == nil then si, phase, t = si + 1, "place", 0 return end
    if t == 1 then gd.loadstate(1) end
    if t == 4 then
      gd.set_percent(2, tonumber(q.pct))
      if s.ki > 0 and gd.combo_ki then gd.combo_ki(1, s.ki) end
    end
    if t == 6 then
      table.remove(queue, 1)
      cell = new_cell(s, q.pct, q.di)
      if q.shield then
        cell.shield, cell.blocks, cell.motions, cell.pool = q.shield, {}, {}, {}
        for _, tk in ipairs(s.tokens) do
          local r = tk:gsub("^~", ""):gsub("@.*$", "")
          if r:sub(1, 1) ~= "X" and r:sub(1, 1) ~= "Z" and r:sub(1, 1) ~= "S" then cell.pool[#cell.pool + 1] = tk end
        end
        if #cell.pool == 0 then cell.pool = { "A" } end
        if q.shield == "single" then cell.pool = { (s.tokens[1]:gsub("^~", "")) } end
      end
      phase, t = "cell", 0
    end
    return
  end
  if phase == "cell" then
    if cell.shield then shield_frame(cell) else cell_frame(cell) end
    if cell.done then phase, t = "load", 0 end
  end
end

function on_draw()
  if not run.visible or not K then return end
  local y = 120
  local function line(s, col) K.text(24, y, s, "caption", col or W, "left") y = y + 18 end
  line("GOKU COMBO TESTS  vs " .. run.vs, GOLD)
  if cell then
    line(string.format("%s   %d%%   DI %s", cell.s.name or cell.s.id, cell.pct, cell.di))
    line("intent: " .. table.concat(cell.s.routes, " > "), DIM)
    line("taken:  " .. table.concat(cell.taken, " > "), OK)
    for i, h in ipairs(cell.hits) do
      local nx = cell.hits[i + 1]
      local txt = string.format("hit %d  %s  %.1f%%", i, h.move, h.dealt)
      local col = W
      if nx then
        if h.free and h.free < nx.f then txt, col = txt .. string.format("   ESCAPABLE %d f", nx.f - h.free), BAD
        else txt, col = txt .. "   TRUE", OK end
      end
      line(txt, col)
    end
  end
  local c = gd.combo(1, false)
  if c then
    line(string.format("links %d/%d   ki %.0f/%.0f", c.links, c.max_links, c.ki, c.ki_max), GOLD)
    for _, r in ipairs(c.routes) do
      line(string.format("%s %s -> %s  [%s %s] f%d-%s", r.state == 2 and ">>" or "  ", r.name, r.to, r.input, r.dir, r.lo,
        r.hi > 0 and tostring(r.hi) or "end"), r.state == 2 and OK or DIM)
    end
  end
  line(string.format("cells %d   failed %d", cells_run, #failed_cells), #failed_cells == 0 and OK or BAD)
end
