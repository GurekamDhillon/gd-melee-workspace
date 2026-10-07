-- det_input.lua: seeded pseudo-random input for the cross-platform determinism proof.
--
--   MELEE_PAD_SCRIPT=<this file> MELEE_SCENE="mode=vs;at=match;p1=fox/c0/hu/stocks99;p2=marth/c0/hu/stocks99;stage=fd;time=0"
--   DET.frames   match frames to play before quitting (default 3600)
--   DET.seed     input seed (default 12345)
--   DET.bias     0..100: how often a stick is pushed toward the opponent (default 55)
--
-- Both players are driven with gd.input (ports 1 and 2). The generator is integer-only (a
-- 31-bit LCG), and the only game state it reads is the two fighters' x positions to pick a
-- direction, so two builds that hold identical state feed identical input; a build that drifts
-- is then caught by the state digest (MELEE_XHASH_LOG), not hidden by the script.
-- The sandbox has no os/io: the runner (run_win.sh / run_linux.sh) writes a copy of this file with a
-- first line `DET = {frames=..., seed=..., bias=...}`.
local cfg = DET or {}
local N = cfg.frames or 3600
local seed = cfg.seed or 12345
local BIAS = cfg.bias or 55

local function rnd(n)
  seed = (seed * 1103515245 + 12345) % 2147483648
  return (seed // 65536) % n
end

local BTN = { 0, 0, 0, 0, "A", "A", "A", "B", "B", "X", "Y", "Z", "A+B", "L", "R", "A+Z" }

local function sample(me, opp)
  local dir = 1
  if me ~= nil and opp ~= nil and opp.x < me.x then dir = -1 end
  local r = rnd(100)
  local x, y = 0, 0
  if r < BIAS then x = dir * (30 + rnd(98))
  elseif r < BIAS + 12 then x = -dir * (20 + rnd(108))
  elseif r < BIAS + 28 then x = rnd(255) - 127 end
  if rnd(100) < 22 then y = rnd(255) - 127 end
  local cx, cy = 0, 0
  if rnd(100) < 12 then cx = rnd(255) - 127; cy = rnd(255) - 127 end
  local spec = { buttons = BTN[rnd(#BTN) + 1], x = x, y = y, cx = cx, cy = cy }
  if rnd(100) < 8 then spec.l = rnd(256) end
  if rnd(100) < 8 then spec.r = rnd(256) end
  return spec, 2 + rnd(9)
end

gd.run(function()
  gd.wait_until(function() return gd.match().active and gd.player(1) ~= nil and gd.player(2) ~= nil end, 6000)
  local start = gd.match().frame
  local free_at = { 0, 0 }
  gd.log("DET: start frame " .. start .. " seed " .. seed .. " frames " .. N)
  while gd.match().frame - start < N do
    local f = gd.match().frame - start
    local p1, p2 = gd.player(1), gd.player(2)
    for port = 1, 2 do
      if f >= free_at[port] then
        local spec, n = sample(port == 1 and p1 or p2, port == 1 and p2 or p1)
        gd.input(port, spec, n)
        free_at[port] = f + n
      end
    end
    if f % 600 == 0 and p1 ~= nil and p2 ~= nil then
      gd.log(string.format("DET: f=%d p1 x=%.4f y=%.4f %%=%.1f st=%d act=%d | p2 x=%.4f y=%.4f %%=%.1f st=%d act=%d",
        f, p1.x, p1.y, p1.percent, p1.stocks, p1.action, p2.x, p2.y, p2.percent, p2.stocks, p2.action))
    end
    gd.wait(1)
  end
  gd.log("DET: done at match frame " .. gd.match().frame)
  gd.quit()
end)
