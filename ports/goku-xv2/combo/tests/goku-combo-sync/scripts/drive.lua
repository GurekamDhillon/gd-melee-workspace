-- @name: Goku combo strings (SyncTest / rewind driver)
-- @gameplay: true
-- Both fighters are pad-driven (scene p2=<victim>/hu), so every input goes through gd.input, which the bench SyncTest records and replays;
-- nothing here writes game state (no teleport, no CPU script). Every 300 frames P1 (Goku, a geno 11 combo define) walks up to P2 and plays a
-- string; the strings rotate: (0) A A A, heavy-up launcher, short-hop jump-cancel, A, heavy-down ender; (1) A A A A A, heavy-forward finisher;
-- (2) A A, side-B Dragon Rush; (3) A, neutral-B ki volley, then A A, heavy-down sweep. Pair with
--   MELEE_SYNCTEST_BENCH=1 MELEE_SYNCTEST_CURATED=1 MELEE_SYNCTEST=12     (the whole run is rolled back and resimulated every frame)
-- and, in a second run, missions/sync-run.txt rewind = 1: at match frame 900 gd.rewind_test() resimulates 120 frames and compares bytes.
-- The curated hash folds Geno_ComboBlock (links, ki, buffers, contact) for a combo define, so a route taken differently on resimulation shows up.
local function kv(text)
  local o = {}
  for line in (text or ""):gmatch("[^\r\n]+") do
    local k, v = line:match("^%s*([%w_]+)%s*=%s*(.-)%s*$")
    if k and not line:match("^%s*#") then o[k] = v end
  end
  return o
end
local cfg, done, rw_started = nil, false, false
local END = 2500

local STRINGS = {
  { { 22, "A" }, { 40, "A" }, { 60, "A" }, { 82, "C^" }, { 104, "X" }, { 134, "A" }, { 150, "Cv" } },
  { { 22, "A" }, { 40, "A" }, { 60, "A" }, { 80, "A" }, { 100, "A" }, { 122, "C>" } },
  { { 22, "A" }, { 40, "A" }, { 62, "B>" } },
  { { 22, "A" }, { 40, "B" }, { 90, "A" }, { 110, "A" }, { 130, "Cv" } },
}
local PADS = { A = { buttons = "A" }, B = { buttons = "B" }, ["B>"] = { buttons = "B", x = 127 }, X = { buttons = "X", y = 0 },
  ["C^"] = { cy = 127 }, ["Cv"] = { cy = -127 }, ["C>"] = { cx = 127 } }

function on_frame()
  local m = gd.match()
  if not m.active or done then return end
  cfg = cfg or kv(gd.mod_read("missions/sync-run.txt") or "")
  local rel = m.frame - 150
  if rel >= 0 then
    local phase, cycle = rel % 330, math.floor(rel / 330)
    local p1, p2 = gd.player(1), gd.player(2)
    if p1 and p2 and phase < 90 then
      local d = p2.x - p1.x
      if math.abs(d) > 9 then gd.input(1, { x = d > 0 and 127 or -127 }, 1) end
    end
    local s = STRINGS[cycle % #STRINGS + 1]
    for _, st in ipairs(s) do
      if phase == st[1] + 90 then
        local pad = {}
        for k, v in pairs(PADS[st[2]]) do pad[k] = v end
        if st[2]:sub(1, 1) ~= "C" and p1 and p2 and p2.x < p1.x and pad.x then pad.x = -pad.x end
        gd.input(1, pad, 2)
        if cycle < 2 then gd.log(string.format('COMBOSYNC press c=%d ph=%d %s p1=%s af=%s dx=%.1f p2=%s', cycle, phase, st[2], tostring(p1 and p1.motion_name), tostring(p1 and p1.action_frame), (p2 and p1) and (p2.x - p1.x) or 0, tostring(p2 and p2.motion_name))) end
      end
    end
  end
  if cfg.rewind == "1" and m.frame == 900 and not rw_started then
    rw_started = true
    local ok, why = gd.rewind_test(120, true)
    gd.log(string.format("COMBOSYNC rewind_test started: %s %s", tostring(ok), tostring(why)))
  end
  if m.frame >= END then
    done = true
    local c = gd.combo(1)
    local r = gd.rewind_test_result and gd.rewind_test_result() or nil
    gd.log(string.format("COMBOSYNC END frame %d links_taken %s ki %s rewind %s", m.frame, c and tostring(c.taken) or "n/a", c and tostring(c.ki) or "n/a",
      r and string.format("pass=%s diff=%s compared=%s", tostring(r.pass), tostring(r.diff), tostring(r.diff_compared)) or "n/a"))
    gd.quit()
  end
end
