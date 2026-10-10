-- Dump gd.timeline for every motion of P1's fighter as one log line per motion ("ACEHB {json}").
-- Run (headless, offscreen, turbo):
--   MELEE_TURBO=1 MELEE_SCENE="mode=vs;p1=mex:27;p2=none;stage=fd" MELEE_PAD_SCRIPT=<this file> \
--     tools/port/run.sh --test name --iso "$GW_ISO_ACE"     (see tools/research/ace_hitbox_collect.py)
-- Parse the log with tools/research/ace_hitbox_collect.py. The output is gameplay numbers only
-- (ids, frames, damage, angles, kb); nothing here reads disc assets, but the raw logs stay out of git.
local BS = string.char(92)
local NL = string.char(10)
local function esc(s) return (s:gsub("[%c\"" .. BS .. "]", function(c) return string.format("%su%04x", BS, c:byte()) end)) end
local function enc(v)
  local t = type(v)
  if t == "nil" then return "null" end
  if t == "boolean" or t == "number" then
    if t == "number" and (v ~= v or v == math.huge or v == -math.huge) then return "null" end
    return tostring(v)
  end
  if t == "string" then return '"' .. esc(v) .. '"' end
  if t == "table" then
    if #v > 0 or next(v) == nil then
      local o = {}
      for i = 1, #v do o[i] = enc(v[i]) end
      return "[" .. table.concat(o, ",") .. "]"
    end
    local o = {}
    for k, x in pairs(v) do o[#o + 1] = '"' .. esc(tostring(k)) .. '":' .. enc(x) end
    table.sort(o)
    return "{" .. table.concat(o, ",") .. "}"
  end
  return "null"
end
local PORT = tonumber(1) or 1
local MAXM = tonumber(gd.lab_env and gd.lab_env("MAXM") or 700) or 700
gd.run(function()
  gd.wait_until(function() return gd.match().active and gd.player(PORT) ~= nil end, 3000)
  gd.wait(30)
  local p = gd.player(PORT)
  gd.log("ACEHBHEAD " .. enc({ port = PORT, char = p.char, char_name = p.char_name, kind = p.kind }))
  local out = {}
  out[1] = enc({ head = { port = PORT, char = p.char, char_name = p.char_name, kind = p.kind } })
  for m = 0, MAXM do
    if m % 6 == 0 then gd.wait(1) end -- stay under the 500 ms per-call task budget
    local ok, tl = pcall(gd.timeline, PORT, m)
    if ok and tl then
      tl.script = nil
      local ok2, line = pcall(enc, tl)
      out[#out + 1] = ok2 and line or "{}"
    end
  end
  local okw, why = gd.data_write("timeline.jsonl", table.concat(out, NL) .. NL)
  gd.log("ACEHBDONE " .. tostring(okw) .. " " .. tostring(why) .. " motions=" .. (#out - 1))
  gd.quit()
end)
