-- Goku destination gameplay design. All persistent values use declared rollback slots.
-- The ki meter (ctx.self.ki, ctx.ki) belongs to the combo engine (geno 11). Lines ending in '-- @KI' use it: build.py strips
-- them for the geno 10 package (lua/goku.lua) and ships the full text as lua/goku_ki.lua, which combo_apply.py installs.
local M = {}
local STEP, TAP, MID, FULL = 15, 15, 45, 60   -- charge frames: 15 a step; tap < 15 <= mid < 45 <= full; 60 is the cap (4 steps)
local SUPER_KI = 100                -- full ki + full charge = Super Kamehameha
local VANISH_KI = 10                -- a Z-vanish counter costs this
-- Charge model: Samus Charge Shot (ftsamusspecialn.c) and Mewtwo Shadow Ball (ftmewtwospecialn.c).
--  * the level is kept on the fighter when the move is put away (shield = Samus Hold_IASA L/R -> Cancel, Mewtwo Loop L/R -> Cancel);
--  * a full stored charge fires at once on the next B (Samus Start_Anim / Mewtwo Start_Anim skip the loop at max); a partial one resumes;
--  * the air charges like Mewtwo's (air Loop states), entry halves the vertical speed (MT:455);
--  * a hit wipes a partial charge but a full one survives (ftMt_SpecialN_OnDeath: zero "only if not at max"), here read as: percent rose since
--    the charge was put away. KO resets the whole Lua block (Geno_FighterReset), like ftMt_Init_OnDeath zeroing the charge.
--  * no auto-fire at full: he stays in the loop with the ball at full size (Mewtwo LoopFull waits for a button; Samus drops to Cancel).
local function release(ctx)
  local s = ctx.state
  local c = s.charge
  s.stored = 0
  if c >= FULL and ctx.ki and ctx.self.ki and ctx.self.ki >= SUPER_KI then ctx.ki(-SUPER_KI) ctx.go("KameSuper") return end -- @KI
  if c >= MID then ctx.go("KameFull"); return end
  if c >= TAP then ctx.go("KameMid"); return end
  ctx.go("KameTap")
end
function M.charge_enter(ctx)
  local s = ctx.state
  if s.stored > 0 and s.stored < FULL and ctx.self.percent > s.stored_pct then s.stored = 0 end  -- hit since: a partial charge is gone
  s.charge = s.stored
  if ctx.self.air then ctx.velocity(ctx.self.vel_x * ctx.self.facing, ctx.self.vel_y * 0.5) end
  if s.charge >= FULL then release(ctx) end   -- a full stored charge fires on the B press
end
function M.charge_frame(ctx)
  local s = ctx.state
  if ctx.input.shield_pressed then
    -- put the charge away (L/R), kept at any level; B again resumes it
    s.stored = s.charge
    s.stored_pct = ctx.self.percent
    ctx.go("auto")
    return
  end
  if ctx.input.attack_pressed then release(ctx) return end   -- Mewtwo fires on A as well as B
  if ctx.input.special_held then
    if s.charge < FULL then s.charge = s.charge + 1 end
    if ctx.self.anim_ended then ctx.loop() end
    return
  end
  release(ctx)
end
-- the beam releases: a short step back on the ground (Mewtwo recoil: gr_vel = -facing * x4 * level); in the air the body hovers while the
-- beam lasts (vertical speed 0, the horizontal drifts off) and then falls
local function recoil(ctx, v) ctx.velocity(-v, 0) end
local function hover(ctx, frames)
  if ctx.self.air and ctx.self.action_frame < frames then ctx.velocity(ctx.self.vel_x * ctx.self.facing * 0.94, 0) end
end
function M.tap_enter(ctx) recoil(ctx, 0.6) end
function M.mid_enter(ctx) recoil(ctx, 0.9) end
function M.full_enter(ctx) recoil(ctx, 1.2) end
function M.super_enter(ctx) recoil(ctx, 1.6) end
-- damage of the drag hits scales with the charge in every tier: base x (0.8 + 0.4 x charge / 60), set on the live beam spheres each frame of the beam window
-- (game frames of the state; the final launching hit is not touched)
local function beam(ctx, lo, hi, base)
  local f = ctx.self.action_frame
  if f >= lo and f <= hi then ctx.hitbox_damage(15, base * (0.8 + 0.4 * math.min(ctx.state.charge, FULL) / FULL)) end
end
function M.tap_frame(ctx) hover(ctx, 24) beam(ctx, 6, 19, 1.2) end
function M.mid_frame(ctx) hover(ctx, 44) beam(ctx, 7, 34, 1.0) end
function M.full_frame(ctx) hover(ctx, 66) beam(ctx, 9, 48, 1.2) end
function M.super_frame(ctx) hover(ctx, 124) beam(ctx, 55, 114, 1.6) end
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
