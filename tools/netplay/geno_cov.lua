-- geno_cov.lua - OBSERVER for the Geno online proofs (slice 7): what the two fighters actually did during an online match.
-- Reads only. Every 1200 match frames (and once more on the last frame it sees) it logs, per port:
--   GENOCOV f=<frame> p1 moves=<distinct motions seen> geno=<distinct Geno states (motion >= 0x400) seen> luafaults=<n> stocks=<n> pct=<n>
-- plus the list of Geno motions seen so far, so a log shows that the Charger's Lua charge, the Striker's specials and the
-- Courier's own states really ran on both peers. It is not a gameplay script (it writes nothing).
--
--   MELEE_SCRIPT=<path to this file>
--
-- @name: Geno online coverage
-- @version: 1.0.0
-- @gameplay: false

local seen, gseen, last = {}, {}, 0
local function note(port)
  local p = gd.player(port)
  if not p then return end
  local m = p.action or p.motion
  if m == nil then return end
  seen[port] = seen[port] or {}
  gseen[port] = gseen[port] or {}
  seen[port][m] = (seen[port][m] or 0) + 1
  if m >= 0x400 then gseen[port][m] = (gseen[port][m] or 0) + 1 end
end

local function count(t) local n = 0 for _ in pairs(t or {}) do n = n + 1 end return n end

local function report(f)
  for port = 1, 2 do
    local p = gd.player(port)
    local l = gd.fighter_lua and gd.fighter_lua(port) or nil
    local list = {}
    for m, c in pairs(gseen[port] or {}) do list[#list + 1] = string.format("%x:%d", m, c) end
    table.sort(list)
    gd.log(string.format("GENOCOV f=%d p%d moves=%d geno=%d luafaults=%s stocks=%s pct=%s [%s]", f, port, count(seen[port]), count(gseen[port]),
      l and tostring(l.faults) or "n/a", p and tostring(p.stocks) or "?", p and tostring(p.percent) or "?", table.concat(list, " ")))
  end
end

function on_frame()
  local m = gd.match()
  if not m.active then return end
  last = m.frame
  note(1) note(2)
  if m.frame % 1200 == 0 then report(m.frame) end
end

function on_match_end() report(last) end
