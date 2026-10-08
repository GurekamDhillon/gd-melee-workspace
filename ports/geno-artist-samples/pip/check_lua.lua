-- Offline behaviour checks only; the engine suite checks its sandbox separately.
local M = dofile(arg[1] or "ports/geno-artist-samples/pip/lua/palm_skip.lua")
local function cast(held)
  local damage, velocity = {}, {}
  local ctx = {
    state = { boosted = true }, input = { special_held = held },
    self = { action_frame = 0, air = false, vel_y = -0.25 },
    velocity = function(f, u) velocity[#velocity + 1] = {f, u} end,
    hitbox_damage = function(mask, value) damage[#damage + 1] = {mask, value} end,
  }
  M.enter(ctx)
  assert(ctx.state.boosted == false, "entry must reset a previous cast's boost")
  assert(velocity[1][1] == 0.8, "entry steps forward")
  for frame = 1, 17 do
    ctx.self.action_frame = frame
    M.frame(ctx)
    if frame < 13 then assert(#damage == 0, "first pulse keeps its authored damage") end
    if frame == 13 then assert(#damage == 1, "boost applies on the first tick of beat two") end
  end
  assert(ctx.state.boosted == held, "B at frame 12 latches the boost")
  assert(#damage == 4 and damage[1][1] == 1, "second pulse changes slot zero only")
  assert(damage[1][2] == (held and 11 or 8), "held and released casts differ")
  assert(#velocity == 2 and velocity[2][1] == 0, "one brake at frame 10")
  assert(velocity[2][2] == -0.25, "braking preserves aerial vertical speed")
end
cast(false)
cast(true)
print("Pip Lua: held/released casts, reset, timing, mask and brake PASS")
