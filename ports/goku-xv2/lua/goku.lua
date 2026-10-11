-- Goku destination gameplay design. All persistent values use declared rollback slots.
-- The ki meter (ctx.self.ki, ctx.ki) belongs to the combo engine (geno 11). Lines ending in '-- @KI' use it: build.py strips
-- them for the geno 10 package (lua/goku.lua) and ships the full text as lua/goku_ki.lua, which combo_apply.py installs.
local M = {}
local FULL = 60   -- charge units: 60 = the cap (full), tiered by the chant below
local SUPER_KI = 100                -- full ki + full charge = Super Kamehameha
local VANISH_KI = 10                -- a Z-vanish counter costs this
local KI_MAX = 100                  -- the meter's cap (combo.json meter): Down B hold charges only below it
-- Charge model (owner, 2026-10-10: it must behave like the natives). Ground = Samus Charge Shot, air = Mewtwo Shadow Ball. Cited from the decomp:
--  * B once enters the move (ftSs_SpecialN_Enter, 343): a Start phase with no input and no charging (ftSs_SpecialNStart_Anim), then the Hold loop (344)
--    which charges BY ITSELF, one step every x20+1 frames (ftSs_SpecialNHold_Anim: mv.ss.unk3.x4 > x20 -> u.ss.x2230 += 1). Here: START frames of lag,
--    then +1 charge unit every UNIT frames (retail Samus reaches full 133 frames after B, Mewtwo 137; the owner's Goku takes CHARGE_FRAMES, see below), 60 = full.
--  * Hold IASA (ftSs_SpecialNHold_IASA), in this order: roll cancel (ftCo_8009917C, a stick/C-stick flick, enters Escape F/B, the level kept), B pressed
--    = fire at the current level (state 346), L/R pressed = Cancel (345, level kept). There is NO jump, spot-dodge or A branch in either native.
--  * At full the ground move AUTO-STORES: ftSs_SpecialNHold_Anim sets x2230 = max and goes to Cancel (345) holding it. Here: state KameStore (the flash).
--  * B with a stored charge (ftSs_SpecialNStart_Anim: x2230 == x18 -> state 346 at once; a partial level re-enters Hold and resumes from it).
--  * In the air Samus's B fires at once (ftSs_SpecialAirNStart_Anim, x0 = 1 -> 348); Mewtwo's air move charges (ftMt_SpecialAirNLoop_Anim) with IASA B/A = fire
--    once releaseLag <= 0, L/R = Cancel, NO roll (ftMt_SpecialAirNLoop_IASA), and at full it stays in LoopFull waiting for an input (no auto-store). Goku's air
--    move is Mewtwo's: it is a beam you aim, and the charge is the point of it.
--  * A hit: a partial charge is wiped, a full one survives (owner's rule, Mewtwo ftMt_SpecialN_OnDeath: zero only if not at max). Here the level is kept
--    in `stored` every frame while charging and wiped on the next entry if the percent rose since.
--  * KO resets the whole Lua block (Geno_FighterReset), like ftSs/ftMt Init_OnDeath zeroing the charge.
local START = 10   -- frames of Start before the loop takes input and charges (Samus Start anim / Mewtwo releaseLag)
-- THE CHARGE TIME (owner, 2026-10-10: "like 10 seconds for max charge or something dumb"): CHARGE_FRAMES game frames from the end of Start to a full charge, one
-- charge unit every CHARGE_FRAMES / FULL = 10 frames. tools/gen_kame.py has the same constant (the voice and hum schedule) and tools/xv2_fx.py the same beats (the effects).
local CHARGE_FRAMES = 600
local UNIT = CHARGE_FRAMES // FULL
-- The chant tiers the charge: XV2's "ka-me-ha-me" is cut into four syllables (tools/xv2_audio.py) spread over it as beats: "ka" 1 s, "me" 3 s, "ha" 6 s, the last "me" 9 s (state
-- frames 60 / 180 / 360 / 540), and each beat raises the tier. A syllable at state frame B is unit (B - START) / UNIT. Tier 0 = released before "ka" (the first second);
-- Max = the last "me" at 9 s; 60 units (frame 610, ~10 s) auto-stores on the ground.
local T1, T2, T3, T4 = 5, 17, 35, 53
local function tier_of(c)
  if c >= T4 then return 4 elseif c >= T3 then return 3 elseif c >= T2 then return 2 elseif c >= T1 then return 1 end
  return 0
end
-- (literal ctx.go names: the package validator finds a state's targets by scanning for them)
local function go_tier(ctx, t)
  if t >= 4 then ctx.go("KameMax") elseif t == 3 then ctx.go("KameFull") elseif t == 2 then ctx.go("KameMid") elseif t == 1 then ctx.go("KameThin") else ctx.go("KameTap") end
end
local function go_store(ctx, t)   -- the stored-charge flash shows the tier
  if t >= 4 then ctx.go("KameStore4") elseif t == 3 then ctx.go("KameStore3") elseif t == 2 then ctx.go("KameStore2") else ctx.go("KameStore1") end
end
local function release(ctx)
  local s = ctx.state
  local c = s.charge
  s.stored = 0
  if c >= FULL and ctx.ki and ctx.self.ki and ctx.self.ki >= SUPER_KI then ctx.ki(-SUPER_KI) ctx.go("KameSuper") return end -- @KI
  go_tier(ctx, tier_of(c))
end
function M.charge_enter(ctx)
  local s = ctx.state
  if s.stored > 0 and s.stored < T4 and ctx.self.percent > s.stored_pct then s.stored = 0 end  -- hit since: a partial tier is gone, a stored full tier (4) survives
  s.charge = s.stored
  s.age = 0
  if ctx.self.air then ctx.velocity(ctx.self.vel_x * ctx.self.facing, ctx.self.vel_y * 0.5) end
  if s.charge >= T4 then release(ctx) end   -- a stored full tier fires on the B press
end
function M.charge_frame(ctx)
  local s = ctx.state
  s.age = s.age + 1
  s.stored = s.charge                  -- whatever way the state ends (cancel, roll, a hit), the level is kept; a hit wipes a partial tier on the next entry
  s.stored_pct = ctx.self.percent
  if ctx.self.anim_ended then ctx.loop() end
  if s.age <= START then return end
  if ctx.input.shield_pressed then go_store(ctx, tier_of(s.charge)) return end   -- L/R: Cancel, level kept; the flash shows the tier
  if ctx.input.special_pressed then release(ctx) return end                  -- B: fire at the current level
  if not ctx.self.air then ctx.go("roll") end                                -- ground roll cancel (ftCo_8009917C); a no-op unless the stick was flicked
  if s.charge < FULL and s.age % UNIT == 0 then   -- one charge unit every UNIT frames: full CHARGE_FRAMES after Start (the natives take ~133 / 137; the owner wants ~10 s)
    s.charge = s.charge + 1
    s.stored = s.charge
    -- at FULL it stays in the loop on the ground AND in the air, like Mewtwo's LoopFull (ftMt_SpecialNLoopFull_Anim never changes state; owner: it can be held forever): it
    -- leaves only by B (fire), L/R (store), a roll flick, or a hit; Samus's auto-store (ftSs_SpecialNHold_Anim) is not used
  end
end
-- the beam releases: a short step back on the ground (Mewtwo recoil: gr_vel = -facing * x4 * level); in the air the body hovers while the
-- beam lasts (vertical speed 0, the horizontal drifts off) and then falls
local function recoil(ctx, v) ctx.velocity(-v, 0) end
local function hover(ctx, frames)
  if ctx.self.air and ctx.self.action_frame < frames then ctx.velocity(ctx.self.vel_x * ctx.self.facing * 0.94, 0) end
end
function M.tap_enter(ctx) recoil(ctx, 0.3) end
function M.thin_enter(ctx) recoil(ctx, 0.6) end
function M.mid_enter(ctx) recoil(ctx, 0.9) end
function M.full_enter(ctx) recoil(ctx, 1.2) end
function M.max_enter(ctx) recoil(ctx, 2.0) end   -- the full chant shoves him back the furthest
function M.super_enter(ctx) recoil(ctx, 1.6) end
-- damage of the drag hits scales with the charge in every tier: base x (0.8 + 0.4 x charge / 60), set on the live beam spheres each frame of the beam window
-- (game frames of the state; the final launching hit is not touched)
local function beam(ctx, lo, hi, base)
  local f = ctx.self.action_frame
  if f >= lo and f <= hi then ctx.hitbox_damage(15, base * (0.8 + 0.4 * math.min(ctx.state.charge, FULL) / FULL)) end
end
function M.tap_frame(ctx) hover(ctx, 18) beam(ctx, 6, 13, 1.2) end
function M.thin_frame(ctx) hover(ctx, 30) beam(ctx, 7, 26, 1.0) end
function M.mid_frame(ctx) hover(ctx, 44) beam(ctx, 7, 34, 1.0) end
function M.full_frame(ctx) hover(ctx, 66) beam(ctx, 9, 48, 1.2) end
function M.max_frame(ctx) hover(ctx, 84) beam(ctx, 11, 60, 1.7) end
function M.super_frame(ctx) hover(ctx, 124) beam(ctx, 55, 114, 2.6) end
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
  -- hold = the XV2 Energy Charge (skill 591): usable only while ki < 100 (at full meter the hold stays the vanish blink)
  local full = false
  full = ctx.self.ki >= KI_MAX -- @KI
  if ctx.self.action_frame == 12 and ctx.input.special_held and not full then ctx.go("KiCharge") return end
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
  if ctx.self.ki >= KI_MAX then ctx.go("auto") return end -- @KI the charge ends at a full meter (XV2: usable only while ki < 100)
  if ctx.ki then ctx.ki(0.8) end -- @KI 0 to 100 in about two seconds of holding
end
-- Homing dash strike (XV2 BAC 476, Guard+Heavy; here Side B out of the shield, ki cost on the route): the dash is Lua like the Rush; XV2 homes on the
-- target for the first 14 frames (engine.homing_movement), which Fighter Lua cannot read (no opponent query), so it dashes straight ahead at the same pace.
function M.homing_enter(ctx)
  ctx.velocity(2.8, 0)
end
function M.homing_frame(ctx)
  local f = ctx.self.action_frame
  if f == 14 then ctx.velocity(0.7, 0) end
  if f == 33 then ctx.velocity(0.3, 0) end
end
-- Not called: names the cape reappear states so the offline reachability check sees them (the engine picks them by behaviour order).
function M.it_targets(ctx) ctx.go("ITEnd") ctx.go("ITEndAir") ctx.go("RushCombo") ctx.go("KameSuper") ctx.go("Homing") end
return M
