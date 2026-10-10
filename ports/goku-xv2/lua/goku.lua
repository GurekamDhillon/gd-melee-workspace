-- Goku destination gameplay design. All persistent values use declared rollback slots.
-- The ki meter (ctx.self.ki, ctx.ki) belongs to the combo engine (geno 11). Lines ending in '-- @KI' use it: build.py strips
-- them for the geno 10 package (lua/goku.lua) and ships the full text as lua/goku_ki.lua, which combo_apply.py installs.
local M = {}
local TAP, MID, FULL = 20, 45, 60   -- charge frames: tap < 20 <= mid < 45 <= full; 60 is the cap
local SUPER_KI = 100                -- full ki + full charge = Super Kamehameha
local VANISH_KI = 10                -- a Z-vanish counter costs this
function M.charge_enter(ctx)
  -- a stored charge (shield while charging) resumes where it was left
  ctx.state.charge = ctx.state.stored
  ctx.state.stored = 0
end
function M.charge_frame(ctx)
  local s = ctx.state
  if ctx.input.shield_pressed and s.charge >= 10 then
    -- store the charge: Melee-style, B again resumes it
    s.stored = s.charge
    ctx.go("auto")
    return
  end
  if ctx.input.special_held and s.charge < FULL then
    s.charge = s.charge + 1
    if ctx.self.anim_ended then ctx.loop() end
    return
  end
  if ctx.input.special_held then
    if ctx.self.anim_ended then ctx.loop() end
    return
  end
  if s.charge >= FULL and ctx.ki and ctx.self.ki and ctx.self.ki >= SUPER_KI then ctx.ki(-SUPER_KI) ctx.go("KameSuper") return end -- @KI
  if s.charge >= MID then ctx.go("KameFull"); return end
  if s.charge >= TAP then ctx.go("KameMid"); return end
  ctx.go("KameTap")
end
function M.rush_enter(ctx)
  -- Dragon Rush / Super Dash: the dash is the move; in the air it keeps its height (a recovery)
  if ctx.self.air then ctx.velocity(2.6, 0.3) else ctx.velocity(2.6, 0) end
end
function M.rush_frame(ctx)
  if ctx.self.action_frame == 20 then ctx.velocity(0.5, ctx.self.vel_y) end
end
function M.rushcombo_enter(ctx)
  ctx.velocity(1.4, 0)
end
function M.rushcombo_frame(ctx)
  local f = ctx.self.action_frame
  if f == 8 or f == 15 then ctx.velocity(1.4, ctx.self.air and 0.2 or 0) end
  if f == 22 then ctx.velocity(0.4, ctx.self.vel_y) end
end
function M.recovery_enter(ctx)
  -- Ground liftoff and vertical launch are the first two ftcmd writes.
  if ctx.self.air then ctx.velocity(0.4, 3.6) end
end
function M.counter_frame(ctx)
  -- down B tap = Z-vanish counter, which costs ki: with too little ki it is only the blink (hold = ki charge)
  if ctx.self.action_frame == 2 and ctx.self.ki and ctx.self.ki < VANISH_KI and not ctx.input.special_held then ctx.go("auto") return end -- @KI
  if ctx.self.action_frame == 12 and ctx.input.special_held then ctx.go("KiCharge") return end
end
function M.riposte_enter(ctx)
  ctx.turn()  -- Z-vanish: reappear facing the attacker
  ctx.state.counter_damage = math.min(18, math.max(10, ctx.self.hit_damage * 1.25))
  if ctx.ki then ctx.ki(-VANISH_KI) end -- @KI
end
function M.riposte_frame(ctx)
  ctx.hitbox_damage(1, ctx.state.counter_damage)
end
function M.kicharge_frame(ctx)
  if ctx.self.anim_ended then ctx.loop() end -- hold the charge clip until released
  if not ctx.input.special_held then ctx.go("auto") return end
  if ctx.ki then ctx.ki(0.8) end -- @KI 0 to 100 in about two seconds of holding
end
-- Not called: names the cape reappear states so the offline reachability check sees them (the engine picks them by behaviour order).
function M.it_targets(ctx) ctx.go("ITEnd") ctx.go("ITEndAir") ctx.go("RushCombo") ctx.go("KameSuper") end
return M
