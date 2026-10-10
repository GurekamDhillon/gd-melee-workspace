-- @name: Ledge timing probe
-- @gameplay: true
-- P1 Goku at the left FD ledge, P2 Falcon at the right one. Per trial: teleport, fall into CliffCatch (252), then pulse one input
-- every other frame from the first frame seen in 252 until the action leaves {252,253}; log the latency in logic frames.
local function log(fmt, ...) gd.log("LEDGE " .. string.format(fmt, ...)) end
local TRIALS = {
  { id = "idle" },
  { id = "jump",   inp = function(side) return { buttons = "X" } end },
  { id = "attack", inp = function(side) return { buttons = "A" } end },
  { id = "climb",  inp = function(side) return { x = 100 * side } end },
  { id = "roll",   inp = function(side) return { buttons = "R", r = 255 } end },
  { id = "drop",   inp = function(side) return { x = -100 * side } end },
  { id = "dropdn", inp = function(side) return { y = -100 } end },
}
local S = {}
for p = 1, 2 do S[p] = { side = (p == 1) and 1 or -1, ph = "setup", t = 0, tr = 1 } end
local t0, quit_t = nil, 0
local done = false
local X0, Y0 = 89, 6

function on_frame()
  if done then quit_t = quit_t + 1 if quit_t > 20 then gd.quit() end return end
  if not gd.match().active then return end
  t0 = t0 or gd.frame()
  if gd.frame() - t0 < 40 then return end
  local fin = true
  for p = 1, 2 do
    local s = S[p]
    local pl = gd.player(p)
    if pl and s.tr <= #TRIALS then
      fin = false
      local tr = TRIALS[s.tr]
      s.t = s.t + 1
      if s.ph == "setup" then
        if s.t == 1 then gd.release(p) end
        if s.t == 5 then gd.teleport(p, -s.side * X0, Y0) end
        if s.t >= 6 then s.ph, s.t, s.cs, s.ws = "fall", 0, nil, nil end
      elseif s.ph == "fall" then
        gd.input(p, { x = 40 * s.side }, 1)
        if s.t % 10 == 0 and s.tr == 1 then log("diag p=%d t=%d act=%d x=%.1f y=%.1f air=%s", p, s.t, pl.action, pl.x, pl.y, tostring(pl.airborne)) end
        if pl.action == 252 then s.ph, s.t, s.cs = "hang", 0, gd.frame()
        elseif s.t > 200 then log("FAIL p=%d trial=%s never caught the ledge (act=%d x=%.1f y=%.1f)", p, tr.id, pl.action, pl.x, pl.y); s.ph, s.t = "recover", 0 end
      elseif s.ph == "hang" then
        if pl.action == 253 and not s.ws then s.ws = gd.frame() end
        local left = pl.action ~= 252 and pl.action ~= 253
        if left then
          log("RESULT trial=%s p=%d %s catch_len=%s latency=%d new_action=%d", tr.id, p, gd.char_name(pl.char), s.ws and (s.ws - s.cs) or "n/a", gd.frame() - s.cs, pl.action)
          s.ph, s.t = "recover", 0
        elseif tr.id == "idle" and s.t > 30 then
          log("RESULT trial=idle p=%d %s catch_len=%s latency=none(30f)", p, gd.char_name(pl.char), s.ws and (s.ws - s.cs) or "n/a")
          s.ph, s.t = "recover", 0
        elseif tr.inp and s.t % 2 == 0 then
          gd.input(p, tr.inp(s.side), 1)
        else
          gd.input(p, {}, 1)
        end
      elseif s.ph == "recover" then
        gd.input(p, {}, 1)
        if s.t >= 110 then s.tr, s.ph, s.t = s.tr + 1, "setup", 0 end
      end
    end
  end
  if fin then done = true end
end
