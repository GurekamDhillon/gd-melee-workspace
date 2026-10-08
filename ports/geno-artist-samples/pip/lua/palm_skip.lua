-- Palm Skip: two palm beats; hold B through action frame 12 to strengthen beat two.
-- Constants/functions only in the module. Per-cast state belongs to the rollback block.
local M = {}

function M.enter(ctx)
  ctx.state.boosted = false
  ctx.velocity(0.8, ctx.self.vel_y)
end

function M.frame(ctx)
  local frame = ctx.self.action_frame
  if frame == 10 then ctx.velocity(0, ctx.self.vel_y) end
  if frame == 12 then ctx.state.boosted = ctx.input.special_held end
  -- Entry primes the ftcmd timer: the script's frame-14 beat starts on action tick 13.
  if frame >= 13 and frame <= 16 then
    ctx.hitbox_damage(1, ctx.state.boosted and 11 or 8)
  end
end

return M
