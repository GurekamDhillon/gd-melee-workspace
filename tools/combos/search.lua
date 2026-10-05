-- @name: combo tree search
-- @gameplay: true
-- In-game DFS over Fox inputs against an idle victim; reads tree.lua (tools/combos/tree.py export-lua) first and writes
-- results_<tag>.jsonl for tree.py merge. See tools/combos/README.md. Load: console "load <this file>", then ts_go.
local ATT, VIC = 1, 2
local A, B, X = 0x100, 0x200, 0x400
local CFG = {ax = -72, vx = -63, maxdepth = 40, topk = 4, killp = 50, Hmax = 46, ATTCHAR = "fox"}
local SL = {}          -- slot ownership: SL[slot] = node
local luaload = load
local co, loaded, saved = nil, false, false
local T = {nodes = 0, evals = 0}
S0 = nil

local function lg(...) gd.log("TS " .. string.format(...)) end
function on_loadstate() loaded = true end
function on_savestate() saved = true end

local function y() coroutine.yield() end
local function load(slot)
  loaded = false; gd.loadstate(slot)
  repeat y() until loaded
end
local function save(slot)
  saved = false; gd.savestate(slot)
  y()
  assert(saved, "savestate did not fire")
end

local function sgn(v) return v >= 0 and 1 or -1 end

-- ---------------------------------------------------------------- candidate generation
local function pad_put(p, f, t) p[f] = p[f] or {}; for k, v in pairs(t) do p[f][k] = v end end
local function mk_aerial(p, kind, f, face, dir)
  if kind == "nair" then pad_put(p, f, {buttons = A})
  elseif kind == "uair" then pad_put(p, f, {cy = 127})
  elseif kind == "dair" then pad_put(p, f, {cy = -127})
  elseif kind == "fair" then pad_put(p, f, {cx = 127 * face})
  elseif kind == "bair" then pad_put(p, f, {cx = -127 * face}) end
end
local function drift(p, from, to, dx)
  if dx == 0 then return end
  for f = from, to do pad_put(p, f, {x = dx}) end
end

local function gen(node)
  local c = {}
  local a, v = node.a, node.v
  local face, dir, ground, hl = a.facing, node.dir, not a.airborne, a.hitlag
  local function add(name, p) c[#c + 1] = {name = name, pad = p} end
  local es = {0, 1, 2, 3, 5, 8}
  for _, e in ipairs(es) do
    local d = hl + e
    if d < 1 then d = 1 end
    if ground then
      local p
      p = {}; pad_put(p, d, {buttons = A}); add("jab e" .. e, p)
      for _, sv in ipairs({40, 70}) do
        p = {}; for f = math.max(1, d - 4), d do pad_put(p, f, {x = dir * sv}) end; pad_put(p, d, {buttons = A}); add("ftilt" .. sv .. " e" .. e, p)
        p = {}; for f = math.max(1, d - 4), d do pad_put(p, f, {x = -dir * sv}) end; pad_put(p, d, {buttons = A}); add("ftilt-back" .. sv .. " e" .. e, p)
      end
      p = {}; for f = math.max(1, d - 4), d do pad_put(p, f, {y = 55}) end; pad_put(p, d, {buttons = A}); add("utilt e" .. e, p)
      p = {}; for f = math.max(1, d - 4), d do pad_put(p, f, {y = -55}) end; pad_put(p, d, {buttons = A}); add("dtilt e" .. e, p)
      p = {}; pad_put(p, d, {cy = 127}); add("usmash e" .. e, p)
      p = {}; pad_put(p, d, {cx = dir * 127}); add("fsmash e" .. e, p)
      p = {}; pad_put(p, d, {cy = -127}); add("dsmash e" .. e, p)
      p = {}; pad_put(p, d, {x = dir * 127, buttons = B}); add("sideB e" .. e, p)
      p = {}; pad_put(p, d, {y = 127, buttons = B}); add("upB e" .. e, p)
      p = {}; pad_put(p, d, {y = -127, buttons = B}); add("shine e" .. e, p)
      p = {}; pad_put(p, d, {cx = -dir * 127}); add("fsmashback e" .. e, p)
    else
      local p = {}; pad_put(p, d, {y = -127, buttons = B}); add("shineair e" .. e, p)
      for _, k in ipairs({"nair", "uair", "dair", "fair", "bair"}) do
        for _, dr in ipairs({-1, 0, 1}) do
          local p = {}; drift(p, 1, d, dir * dr * 127); mk_aerial(p, k, d, face, dir); add(k .. " e" .. e .. " dr" .. dr, p)
        end
      end
      local p = {}; pad_put(p, d, {x = dir * 127, buttons = B}); add("sideB e" .. e, p)
      p = {}; pad_put(p, d, {y = 127, buttons = B}); add("upB e" .. e, p)
      p = {}; pad_put(p, d, {x = dir * 127, y = 127, buttons = B}); add("upB-d e" .. e, p)
    end
  end
  -- jump, wavedash, then a follow-up (waveshine, wavedash-usmash, wavedash-jab, wavedash-grab-less)
  if ground then
    for _, e in ipairs({0, 1, 2, 3}) do
      local d = math.max(1, hl + e)
      for _, a in ipairs({3, 4, 5}) do
        for _, wd in ipairs({dir, -dir}) do
          for _, fol in ipairs({"shine", "usmash", "jab", "fsmash", "dtilt"}) do
            for _, w in ipairs({4, 6, 8, 10, 12, 14, 17, 20, 24}) do
              local p = {}
              pad_put(p, d, {buttons = X})
              pad_put(p, d + a, {buttons = 0x20, r = 255, x = wd * 127, y = -46})
              local t = d + a + w
              if fol == "shine" then pad_put(p, t, {y = -127, buttons = B})
              elseif fol == "usmash" then pad_put(p, t, {cy = 127})
              elseif fol == "jab" then pad_put(p, t, {buttons = A})
              elseif fol == "fsmash" then pad_put(p, t, {cx = dir * 127})
              else for f = t - 4, t do pad_put(p, f, {y = -55}) end; pad_put(p, t, {buttons = A}) end
              add("wd" .. (wd == dir and "F" or "B") .. ">" .. fol .. " e" .. e .. " a" .. a .. " w" .. w, p)
            end
          end
        end
      end
    end
  end
  -- jump then aerial (ground jump from window, or the double jump)
  for _, e in ipairs({0, 1, 3, 8, 14, 22, 30}) do
    local d = math.max(1, hl + e)
    for _, k in ipairs({"nair", "uair", "dair", "fair", "bair"}) do
      for _, j in ipairs({1, 2, 4, 6, 9, 13}) do
        for _, dr in ipairs({0, 1}) do
          local p = {}
          local jf = ground and (d + 3) or (d)
          pad_put(p, d, {buttons = X})
          drift(p, d, jf + j, dir * dr * 127)
          mk_aerial(p, k, jf + j, face, dir)
          add("jump>" .. k .. " e" .. e .. " j" .. j .. " dr" .. dr, p)
        end
      end
    end
  end
  if CFG.loop == 1 and node.v.x < (CFG.edge or 62) then
    local f = {}
    for _, cd in ipairs(c) do
      local n = cd.name
      if n:find("^shine e") or n:find("^jab e") or n:find("^wdF>jab") or n:find("^wdF>shine") then f[#f + 1] = cd end
    end
    c = f
  end
  if CFG.rootonly and node.depth == 0 then
    local f = {}
    for _, cd in ipairs(c) do if cd.name:find("dair", 1, true) and cd.name:find("jump", 1, true) then f[#f + 1] = cd end end
    c = f
  end
  return c
end

-- ---------------------------------------------------------------- evaluation
local function info()
  local a, v = gd.player(ATT), gd.player(VIC)
  return a, v
end
local function node_ctx(n)
  n.a, n.v = info()
  n.dir = sgn(n.v.x - n.a.x)
  if math.abs(n.v.x - n.a.x) < 0.5 then n.dir = n.a.facing end
end

-- run one candidate from node (already loaded, f=0), until the first hit or the horizon.
-- returns result; if commit_slot is given, saves a snapshot at the hit frame.
local function run(node, cand, commit_slot, H)
  local p0 = node.v.percent
  local falls0 = node.v.falls
  local res = {hit = false}
  for f = 1, H do
    local a, v = info()
    if f > 1 then
      if v.percent > p0 + 0.001 then
        res.hit = true; res.hf = f; res.dmg = v.percent - p0; res.vhs = v.hitstun; res.amove = a.action
        res.vi = v.in_hitstun; res.vact = v.action; res.ahl = a.hitlag; res.a, res.v = a, v
        if commit_slot then save(commit_slot) end
        return res
      end
      if (node.depth > 0 and not v.in_hitstun) or v.falls ~= falls0 then res.stunbreak = f; return res end
    end
    local s = cand.pad[f]
    if s then gd.cpu_pad(ATT, s, 1) end
    y()
  end
  return res
end

local function ensure(node)
  if node.slot and SL[node.slot] == node then return end
  -- rebuild by replay from parent
  local par = node.parent
  ensure(par)
  local slot = node.slot or (2 + (node.depth % 3))
  load(par.slot)
  node_ctx(par)
  local r = run(par, node.cand, slot, CFG.Hmax * 2)
  assert(r.hit, "rebuild failed")
  node.slot = slot; SL[slot] = node
end

-- after the last hit, does the victim die with no further input?
local function killcheck(node)
  load(node.slot)
  local f0 = gd.player(VIC).falls
  local k = nil
  for f = 1, 200 do
    y()
    local v = gd.player(VIC)
    if v.falls ~= f0 then return f, v end
  end
  return nil
end

local function dump_path(node, tag)
  local lines, chain = {}, {}
  local n = node
  while n.parent do table.insert(chain, 1, n); n = n.parent end
  local abs = 0
  for _, nd in ipairs(chain) do
    lines[#lines + 1] = string.format("# %s dmg=%.1f vp=%.1f hf=%d", nd.cand.name, nd.dmg, nd.vp, nd.hf)
    local fs = {}
    for f in pairs(nd.cand.pad) do fs[#fs + 1] = f end
    table.sort(fs)
    for _, f in ipairs(fs) do
      if f < nd.hf then
        local s = nd.cand.pad[f]
        lines[#lines + 1] = string.format("%d %d %d %d %d %d", abs + f, s.x or 0, s.y or 0, s.cx or 0, s.cy or 0, s.buttons or 0)
      end
    end
    abs = abs + nd.hf
  end
  gd.data_write("path_" .. tag .. ".txt", table.concat(lines, "\n") .. "\n")
end

local best = {depth = 0}

-- ------------------------------------------------------------ the combo tree (tools/combos), read FIRST
-- tree.lua in the data folder is `python tools/combos/tree.py export-lua <tree.json>`; results are written as
-- results_<tag>.jsonl lines that `tree.py merge` takes.
local TREE = nil
do
  local txt = gd.data_read("tree.lua")
  if txt then
    local f = luaload(txt)
    if f then local ok, t = pcall(f); if ok then TREE = t end end
  end
end
local REC = {}
local NL = string.char(10)
local function jstr(x) local t = tostring(x):gsub('[%c"' .. string.char(92) .. ']', '_'); return '"' .. t .. '"' end
local function rec(node, cand, r, result)
  local ins = {}
  local fs = {}
  for f in pairs(cand.pad) do fs[#fs + 1] = f end
  table.sort(fs)
  for _, f in ipairs(fs) do
    local sm = cand.pad[f]
    ins[#ins + 1] = string.format('{"f":%d,"x":%d,"y":%d,"cx":%d,"cy":%d,"buttons":%d}', f, sm.x or 0, sm.y or 0, sm.cx or 0, sm.cy or 0, sm.buttons or 0)
  end
  local e = string.format('{"move":%s,"result":%s,"inputs":[%s],"confirmed":1,"source":"search"', jstr(cand.name), jstr(result), table.concat(ins, ","))
  if result == "true" then
    e = e .. string.format(',"hit_frame":%d,"damage":%.1f,"victim_hitstun":%d,"fox_action_at_hit":%d,"victim_percent_after":%.1f', r.hf, r.dmg, r.vhs, r.amove, node.v.percent + r.dmg)
  elseif result == "broke" then
    e = e .. string.format(',"broke_frame":%d', r.stunbreak or 0)
  end
  e = e .. "}"
  REC[#REC + 1] = string.format('{"path":%s,"situation":{"victim_percent":[%.1f,%.1f],"grounded":%s},"edge":%s}', jstr(node.path), node.v.percent, node.v.percent, tostring(not node.a.airborne), e)
end
local function flush()
  local head = string.format('{"header":{"attacker":"fox","victim":"falco","stage":"fd","rules":"000005fb"}}')
  gd.data_write("results_" .. (CFG.tag or "run") .. ".jsonl", head .. NL .. table.concat(REC, NL) .. NL)
end

local function try_children(node, list)
  for i = 1, math.min(CFG.topk, #list) do
    local cand = list[i]
    local slot = 2 + (node.depth % 3)
    ensure(node)
    load(node.slot); node_ctx(node)
    local r = run(node, cand, slot, CFG.Hmax)
    if not r.hit then
      lg("DRIFT known link %s did not hit now (engine or tree changed)", cand.name)
    else
      local child = {parent = node, depth = node.depth + 1, cand = cand, slot = slot, hf = r.hf, dmg = r.dmg, amove = r.amove,
                     vp = r.v.percent, path = node.path .. "/" .. cand.name}
      SL[slot] = child
      if cand.known then rec(node, cand, r, "true") end
      lg("COMMIT d=%d %s dmg=%.1f vp=%.1f vhs=%.0f amove=%d hf=%d%s", child.depth, cand.name, r.dmg, r.v.percent, r.vhs, r.amove, r.hf, cand.known and " (tree)" or "")
      if child.depth > best.depth then best = child; dump_path(child, "best") end
      if r.v.percent >= CFG.killp then
        local kf, kv = killcheck(child)
        lg("KILLCHECK vp=%.1f -> %s", r.v.percent, kf and ("KO at +" .. kf) or "survives")
        if kf then dump_path(child, "KO"); flush(); lg("DONE KO depth=%d vp=%.1f", child.depth, r.v.percent); return true end
        ensure(child)
      end
      if child.depth < CFG.maxdepth and DFS(child) then return true end
    end
  end
  return false
end

function DFS(node)
  T.nodes = T.nodes + 1
  ensure(node)
  load(node.slot); node_ctx(node)
  local cands = gen(node)
  -- 1. what the tree already knows about this situation
  local known = {}
  local tn = TREE and TREE.nodes[node.path]
  if tn then for _, e in ipairs(tn.edges) do known[e.move] = e end end
  local known_ok, new, skipped = {}, {}, 0
  for _, cand in ipairs(cands) do
    local e = known[cand.name]
    if e then
      if e.result == "true" then
        cand.known = true
        cand.res = {hit = true, hf = e.hit_frame, dmg = e.damage, vhs = e.victim_hitstun, amove = e.fox_action_at_hit or 0, vi = true}
        cand.score = e.damage + 0.35 * e.victim_hitstun - 0.05 * e.hit_frame + (((e.fox_action_at_hit or 0) == 360) and (CFG.bshine or 15) or 0)
        known_ok[#known_ok + 1] = cand
      else
        skipped = skipped + 1
      end
    else
      new[#new + 1] = cand
    end
  end
  table.sort(known_ok, function(p, q) return p.score > q.score end)
  lg("NODE depth=%d path=%s p=%.1f cands=%d tree-true=%d tree-skipped=%d new=%d", node.depth, node.path, node.v.percent, #cands, #known_ok, skipped, #new)
  if #known_ok > 0 and try_children(node, known_ok) then return true end
  -- 2. new candidates only
  local ok = {}
  for i, cand in ipairs(new) do
    load(node.slot)
    local r = run(node, cand, nil, CFG.Hmax)
    T.evals = T.evals + 1
    if r.hit and r.vi then
      cand.res = r
      rec(node, cand, r, "true")
      local move_pen = 0
      local n = node
      while CFG.loop ~= 1 and n and n.cand do if n.amove == r.amove then move_pen = move_pen + 7 end; n = n.parent end
      cand.score = (CFG.loop == 1 and 0.8 * (r.v.x - node.v.x) or 0) + r.dmg + 0.35 * r.vhs - move_pen - 0.05 * r.hf + ((r.amove == 360 or r.amove == 361 or r.amove == 362) and (CFG.bshine or 15) or 0)
      ok[#ok + 1] = cand
    elseif r.hit then
      rec(node, cand, r, "broke")      -- hit, but the victim was already out of hitstun
    elseif r.stunbreak then
      rec(node, cand, r, "broke")
    else
      rec(node, cand, r, "whiff")
    end
  end
  flush()
  table.sort(ok, function(p, q) return p.score > q.score end)
  lg("NODE depth=%d evaluated=%d valid=%d top=%s", node.depth, #new, #ok,
     ok[1] and (ok[1].name .. string.format(" dmg=%.1f vhs=%.0f", ok[1].res.dmg, ok[1].res.vhs)) or "-")
  return try_children(node, ok)
end
local dfs = DFS

local function main()
  S0 = {depth = 0, slot = 1, cand = nil, hf = 0, dmg = 0, vp = 0, path = string.format("@ax%d_vx%d", CFG.ax, CFG.vx)}
  SL[1] = S0
  load(1)
  S0.a, S0.v = info()
  node_ctx(S0)
  lg("S0 start a=(%.1f,%.1f) v=(%.1f,%.1f) face=%d", S0.a.x, S0.a.y, S0.v.x, S0.v.y, S0.a.facing)
  local ok = dfs(S0)
  lg("SEARCH END ok=%s nodes=%d evals=%d bestdepth=%d", tostring(ok), T.nodes, T.evals, best.depth)
end

-- ---------------------------------------------------------------- driver
local mode, wf, tp = "idle", 0, nil
function on_match_start()
  mode = "warm"; wf = 0; tp = nil
  gd.cpu_mode(ATT, "script"); gd.cpu_mode(VIC, "stand")
  lg("match start")
end
function on_frame()
  if mode == "warm" then
    wf = wf + 1
    local a, v = gd.player(ATT), gd.player(VIC)
    if wf > 2 and not tp and a.action == 14 and v.action == 14 and not a.airborne and not v.airborne then
      gd.teleport(ATT, CFG.ax, 0); gd.teleport(VIC, CFG.vx, 0); tp = wf
    end
    if tp and wf == tp + 25 then gd.savestate(1); mode = "idle"; tp = nil; lg("S0 saved") end
    return
  end
  if co and coroutine.status(co) == "suspended" then
    local ok, err = coroutine.resume(co)
    if not ok then lg("ERROR %s", tostring(err)); co = nil end
  end
end
gd.command("ts_go", function(args)
  for k, v in string.gmatch(args or "", "(%w+)=(%-?[%d%.]+)") do CFG[k] = tonumber(v) end
  co = coroutine.create(main)
  gd.resume()
end, "ts_go [k=v...]")
gd.command("ts_stop", function() co = nil end, "")
