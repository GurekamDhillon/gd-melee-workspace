-- falcon_parity.lua (also used for the Fox template, tools/geno/falcon_parity/README.md): per-frame state trace of a retail template fighter (P1) against Mario (P2, a second scripted pad) in the LAB, for
-- retail Falcon (p1=captain/hu) and the standalone Geno Falcon (p1=geno:geno-falcon/hu). The two runs get the same inputs from
-- the same saved state; tools/geno/falcon_parity/parity_diff.py compares the two logs line by line.
--
-- One log line per logic frame per scenario:  PF <scenario> <n> | <P1 fields> | <P2 fields>
-- The line starts with R<hex>, the game's random seed (gd.rng), so the first frame two runs part ways in RNG draws shows at once.
-- Fields (floats as %.9g, so a float32 reads back exactly): motion id, action frame, animation frame, x y vx vy ground_vel, facing,
-- percent, hitlag, hitstun, kb vx vy, shield, jumps used, intangible/invincible, then the live hitboxes of the fighter
-- (bone damage angle kbg bkb wbk size x y z) and a hash of all hurtbox capsules (pose and body parity).
-- Per scenario:  PS <scenario> frames=<n> hash=<fnv> seen=<motion names>.  Last line: PS TOTAL <hash>.
--
-- `CFG` (prepended by run_parity.sh) may hold ONLY = {name=true,...} (a subset) and DETAIL = true (also dump every hurtbox).
local CFG = CFG or {}
local ONLY = CFG.ONLY
local S, order = {}, {}
local function add(name, setup, steps) S[name] = {setup = setup or {}, steps = steps}; order[#order + 1] = name end

-- ---- input vocabulary ---------------------------------------------------------------------------------------------------------
local N = {}                                   -- neutral
local function st(n, p1, p2) return {n, p1 or N, p2 or N} end
local function seq(...) local r = {}; for _, t in ipairs({...}) do for _, v in ipairs(t) do r[#r + 1] = v end end; return r end
local function rep(n, t) local r = {}; for _ = 1, n do for _, v in ipairs(t) do r[#r + 1] = v end end; return r end
local function W(n) return {st(n)} end         -- wait n frames
local DASH = {st(4, {x = 127}), st(8, {x = 100})}
local JUMP = {st(3, {buttons = 'X'}), st(1)}   -- full hop from the ground is longer: hold X
local FULLHOP = {st(14, {buttons = 'X'})}
local SHORTHOP = {st(2, {buttons = 'X'}), st(3)}
local function air(spec, n) return {st(n or 2, spec)} end

-- where the fighters start (P1 at x, P2 at x2; Mario faces right: P2 stands behind or in front accordingly)
local FAR = {p1 = {0, 0}, p2 = {-100, 0}}
local function NEAR(dx, dy, pct) return {p1 = {0, 0}, p2 = {dx, dy or 0}, pct2 = pct} end

-- ---- ground attacks (a miss with Mario far away, then connecting placements) --------------------------------------------------
local function atk(name, steps, hitdx, hitdy, wait, pct)
  add(name, FAR, seq(steps, W(wait or 40)))
  if hitdx then add(name .. '_h', NEAR(hitdx, hitdy, pct), seq(steps, W(wait or 40))) end
end
atk('jab1', {st(3, {buttons = 'A'})}, 9)
atk('jab12', {st(3, {buttons = 'A'}), st(5), st(3, {buttons = 'A'})}, 9, 0, 40)
atk('jab123', {st(3, {buttons = 'A'}), st(5), st(3, {buttons = 'A'}), st(5), st(3, {buttons = 'A'})}, 9, 0, 50)
atk('jab_hold', {st(60, {buttons = 'A'})}, 9, 0, 40)
atk('dash_attack', seq(DASH, {st(3, {buttons = 'A', x = 70})}), 28, 0, 50)
atk('ftilt', {st(3, {buttons = 'A', x = 45})}, 12, 0)
atk('ftilt_up', {st(3, {buttons = 'A', x = 45, y = 45})}, 12, 0)
atk('ftilt_down', {st(3, {buttons = 'A', x = 45, y = -45})}, 12, 0)
atk('utilt', {st(3, {buttons = 'A', y = 35})}, 6, 0)
atk('dtilt', {st(3, {buttons = 'A', y = -35})}, 14, 0)
atk('fsmash', {st(3, {buttons = 'A', x = 127})}, 14, 0, 70)
atk('fsmash_up', {st(3, {buttons = 'A', x = 100, y = 70})}, 14, 0, 70)
atk('fsmash_down', {st(3, {buttons = 'A', x = 100, y = -70})}, 14, 0, 70)
atk('usmash', {st(3, {buttons = 'A', y = 127})}, 6, 0, 70)
atk('dsmash', {st(3, {buttons = 'A', y = -127})}, 12, 0, 70)
atk('csmash_f', {st(3, {cx = 127})}, 14, 0, 70)
atk('csmash_u', {st(3, {cy = 127})}, 6, 0, 70)
atk('csmash_d', {st(3, {cy = -127})}, 12, 0, 70)
atk('fsmash_charge', {st(40, {cx = 127})}, 14, 0, 80)
atk('usmash_charge', {st(40, {cy = 127})}, 6, 0, 80)
atk('dsmash_charge', {st(40, {cy = -127})}, 12, 0, 80)
atk('fsmash_hit_high_pct', {st(3, {cx = 127})}, 14, 0, 70, 120)
add('dash_attack_far_hit', NEAR(34, 0), seq(DASH, {st(3, {buttons = 'A', x = 70})}, W(50)))

-- ---- aerials: short hop and full hop, miss and hit; auto-cancel and landing ----------------------------------------------------
local function aer(name, spec, hitdx, hitdy)
  local sh = seq(SHORTHOP, {st(2, spec)}, W(60))
  local fh = seq({st(14, {buttons = 'X'})}, {st(2, spec)}, W(70))
  add(name .. '_sh', FAR, sh)
  add(name .. '_fh', FAR, fh)
  if hitdx then add(name .. '_sh_h', NEAR(hitdx, hitdy), sh); add(name .. '_fh_h', NEAR(hitdx, hitdy), fh) end
end
aer('nair', {buttons = 'A'}, 8, 0)
aer('fair', {cx = 127}, 14, 0)
aer('bair', {cx = -127}, -14, 0)
aer('uair', {cy = 127}, 2, 0)
aer('dair', {cy = -127}, 4, 0)
-- landing lag: start the aerial in the fall (drop from 8 up), plus an L-cancel press just before landing
for _, a in ipairs({{'nair', {buttons = 'A'}}, {'fair', {cx = 127}}, {'bair', {cx = -127}}, {'uair', {cy = 127}}, {'dair', {cy = -127}}}) do
  add('land_' .. a[1], {p1 = {0, 8}, p2 = {-100, 0}}, seq({st(2, a[2])}, W(60)))
  add('lcancel_' .. a[1], {p1 = {0, 8}, p2 = {-100, 0}}, seq({st(2, a[2]), st(2), st(2, {buttons = 'L'})}, W(60)))
end

-- ---- grabs, pummel, throws, being grabbed ------------------------------------------------------------------------------------------
local GRAB = {st(3, {buttons = 'Z'}), st(36)}
add('grab_miss', FAR, seq({st(3, {buttons = 'Z'})}, W(50)))
add('dash_grab_miss', FAR, seq(DASH, {st(3, {buttons = 'Z'})}, W(50)))
add('grab_hold', NEAR(8), seq(GRAB, W(30)))
add('pummel', NEAR(8), seq(GRAB, {st(3, {buttons = 'A'}), st(10), st(3, {buttons = 'A'})}, W(20)))
add('fthrow', NEAR(8), seq(GRAB, {st(3, {x = 127})}, W(60)))
add('bthrow', NEAR(8), seq(GRAB, {st(3, {x = -127})}, W(60)))
add('uthrow', NEAR(8), seq(GRAB, {st(3, {y = 127})}, W(60)))
add('dthrow', NEAR(8), seq(GRAB, {st(3, {y = -127})}, W(60)))
add('dash_grab', NEAR(26), seq(DASH, {st(3, {buttons = 'Z'})}, W(60)))
add('grab_release_wait', NEAR(8), seq(GRAB, W(140)))
add('grab_mash_out', NEAR(8), seq({st(3, {buttons = 'Z'})}, {st(2, N, {x = 127}), st(2, N, {x = -127}), st(2, N, {x = 127}), st(2, N, {x = -127})},
  {st(2, N, {y = 127}), st(2, N, {y = -127}), st(2, N, {x = 127}), st(2, N, {x = -127}), st(2, N, {y = 127}), st(2, N, {y = -127})}, W(60)))
add('grab_air_throw_f', {p1 = {0, 0}, p2 = {8, 0}}, seq(GRAB, {st(3, {x = 127})}, W(60)))
-- being grabbed by Mario: pulled, held, and thrown / released by mashing
local MZ = {st(3, N, {buttons = 'Z'})}
add('grabbed_hold', {p1 = {10, 0}, p2 = {0, 0}}, seq(MZ, W(60)))
add('grabbed_fthrow', {p1 = {10, 0}, p2 = {0, 0}}, seq(MZ, W(36), {st(3, N, {x = 127})}, W(70)))
add('grabbed_bthrow', {p1 = {10, 0}, p2 = {0, 0}}, seq(MZ, W(36), {st(3, N, {x = -127})}, W(70)))
add('grabbed_uthrow', {p1 = {10, 0}, p2 = {0, 0}}, seq(MZ, W(36), {st(3, N, {y = 127})}, W(70)))
add('grabbed_dthrow', {p1 = {10, 0}, p2 = {0, 0}}, seq(MZ, W(36), {st(3, N, {y = -127})}, W(70)))
add('grabbed_pummel', {p1 = {10, 0}, p2 = {0, 0}}, seq(MZ, W(36), {st(3, N, {buttons = 'A'}), st(10), st(3, N, {buttons = 'A'})}, W(40)))
add('grabbed_mash', {p1 = {10, 0}, p2 = {0, 0}}, seq(MZ, W(10), rep(8, {st(2, {x = 127}), st(2, {x = -127})}), W(60)))
add('grabbed_shield_grab', {p1 = {10, 0}, p2 = {0, 0}}, seq({st(10, {buttons = 'L'}, {buttons = 'Z'})}, W(50)))

-- ---- specials: ground and air, miss and hit ----------------------------------------------------------------------------------------
local function sp(name, steps, hitdx, hitdy, wait, air_start)
  local pre = air_start or {}
  add(name, FAR, seq(pre, steps, W(wait or 90)))
  if hitdx then add(name .. '_h', NEAR(hitdx, hitdy), seq(pre, steps, W(wait or 90))) end
end
local HOP = seq({st(3, {buttons = 'X'}), st(3)})
sp('neutral_b', {st(3, {buttons = 'B'})}, 16, 0, 110)
sp('neutral_b_back', {st(3, {buttons = 'B', x = -80})}, -16, 0, 110)
sp('neutral_b_up', {st(3, {buttons = 'B', y = 100})}, 16, 0, 110)
sp('neutral_b_down', {st(3, {buttons = 'B', y = -100})}, 16, 0, 110)
sp('neutral_b_held', {st(40, {buttons = 'B'})}, 16, 0, 110)
sp('air_neutral_b', {st(3, {buttons = 'B'})}, 16, 0, 110, HOP)
sp('air_neutral_b_back', {st(3, {buttons = 'B', x = -80})}, -16, 0, 110, HOP)
sp('air_neutral_b_up', {st(3, {buttons = 'B', y = 100})}, 16, 0, 110, HOP)
sp('air_neutral_b_down', {st(3, {buttons = 'B', y = -100})}, 16, 4, 110, HOP)
-- Fox extras (retail Fox against the Geno Fox define; harmless for Falcon): rapid Blaster, a Blaster hold into the lasers, the Reflector against a hit and a Mario fireball, shine into jump, Illusion/Firefox travel
sp('fox_blaster_rapid', rep(5, {st(2, {buttons = 'B'}), st(5)}), 60, 0, 120)
sp('fox_air_blaster_rapid', rep(4, {st(2, {buttons = 'B'}), st(5)}), 60, 0, 120, HOP)
sp('fox_shine_hold', {st(3, {buttons = 'B', y = -127}), st(40, {y = -127})}, 14, 0, 100)
sp('fox_shine_jc', {st(3, {buttons = 'B', y = -127}), st(8), st(3, {buttons = 'X'})}, 14, 0, 100)
add('fox_reflect_fireball', NEAR(70), seq({st(2, {buttons = 'B', y = -127}, {buttons = 'B'}), st(50, {y = -127})}, W(60)))
add('fox_reflect_hit', NEAR(14), seq({st(2, {buttons = 'B', y = -127}), st(30, {y = -127}, {buttons = 'A'})}, W(60)))
sp('fox_illusion_short', {st(3, {buttons = 'B', x = 127}), st(2)}, 20, 0, 120)
sp('fox_firefox_up_right', {st(3, {buttons = 'B', y = 127}), st(30, {x = 90, y = 90})}, 4, 6, 140)
sp('fox_air_firefox_down_left', {st(3, {buttons = 'B', y = 127}), st(30, {x = -90, y = -90})}, 4, 6, 140, HOP)
-- Marth extras (retail Marth against the Geno Marth define): Dancing Blade strings (tap B up to four times, up / down inputs), Shield Breaker held and released, Counter against a hit and a fireball, sword tip and base ranges
sp('marth_dancing_blade_4', seq({st(3, {buttons = 'B', x = 127})}, rep(3, {st(10), st(3, {buttons = 'B', x = 127})})), 20, 0, 140)
sp('marth_dancing_blade_updown', {st(3, {buttons = 'B', x = 127}), st(12), st(3, {buttons = 'B', y = 100}), st(12), st(3, {buttons = 'B', y = -100}), st(12), st(3, {buttons = 'B', x = 127})}, 20, 0, 140)
sp('marth_air_dancing_blade', seq({st(3, {buttons = 'B', x = 127})}, rep(2, {st(10), st(3, {buttons = 'B', y = 100})})), 22, 0, 140, HOP)
sp('marth_shield_breaker_full', {st(130, {buttons = 'B'})}, 30, 0, 140)
sp('marth_shield_breaker_release', {st(20, {buttons = 'B'}), st(3)}, 30, 0, 140)
add('marth_counter_hit', NEAR(14), seq({st(2, {buttons = 'B', y = -127}), st(30, {y = -127}, {buttons = 'A'})}, W(80)))
add('marth_counter_fireball', NEAR(70), seq({st(2, {buttons = 'B', y = -127}, {buttons = 'B'}), st(50, {y = -127})}, W(80)))
atk('marth_fsmash_tip', {st(3, {cx = 127})}, 26, 0, 50)
atk('marth_fsmash_base', {st(3, {cx = 127})}, 10, 0, 50)
atk('marth_dair_tip', seq(HOP, {st(3, {cy = -127})}), 12, -6, 60)
-- Jigglypuff extras (Down B Rest, Up B Sing, Side B Pound, Neutral B Rollout, five jumps): Rest against a near and far Mario and in the air, Sing sleep, Rollout charge and release, a jump in every air slot
sp('puff_rest', {st(3, {buttons = 'B', y = -127})}, 8, 0, 200)
sp('puff_rest_air', {st(3, {buttons = 'B', y = -127})}, 8, 0, 200, HOP)
atk('puff_rest_high_pct', {st(3, {buttons = 'B', y = -127})}, 8, 0, 200, 110)
sp('puff_sing', {st(3, {buttons = 'B', y = 127})}, 14, 0, 260)
sp('puff_sing_air', {st(3, {buttons = 'B', y = 127})}, 14, 0, 260, HOP)
sp('puff_pound', {st(3, {buttons = 'B', x = 127})}, 14, 0, 120)
sp('puff_pound_air', {st(3, {buttons = 'B', x = 127})}, 14, 0, 120, HOP)
sp('puff_rollout_tap', {st(3, {buttons = 'B'})}, 20, 0, 140)
sp('puff_rollout_charged', {st(70, {buttons = 'B'}), st(3, {x = 127})}, 20, 0, 160)
sp('puff_rollout_air', {st(40, {buttons = 'B'}), st(3, {x = 127})}, 20, 0, 160, HOP)
add('puff_jumps5', FAR, seq(FULLHOP, rep(5, seq(W(14), {st(3, {buttons = 'X', x = 60})})), W(120)))
add('puff_jumps5_back', FAR, seq(FULLHOP, rep(5, seq(W(10), {st(3, {buttons = 'X', x = -100})})), W(120)))
add('puff_jumps_rest_air', FAR, seq(FULLHOP, rep(3, seq(W(12), {st(3, {buttons = 'X'})})), {st(3, {buttons = 'B', y = -127})}, W(200)))
add('puff_shield_break_fly', {p1 = {10, 0}, p2 = {0, 0}}, seq({st(6, {buttons = 'L'})}, rep(9, {st(3, {buttons = 'L'}, {cx = 127}), st(34, {buttons = 'L'})}), W(300)))
-- Zelda extras (Neutral B Nayru's Love, Side B Din's Fire with its steering, Up B Farore's Wind, Down B transform and back): the transform is exercised both ways in one run
sp('zelda_nayru', {st(3, {buttons = 'B'})}, 14, 0, 140)
sp('zelda_nayru_air', {st(3, {buttons = 'B'})}, 14, 0, 140, HOP)
sp('zelda_dins_fire', {st(3, {buttons = 'B', x = 127}), st(30, {y = 90})}, 40, 0, 160)
sp('zelda_dins_fire_hold', {st(3, {buttons = 'B', x = 127}), st(40, {buttons = 'B', y = -90})}, 40, 0, 160)
sp('zelda_dins_fire_air', {st(3, {buttons = 'B', x = 127})}, 40, 0, 160, HOP)
sp('zelda_farore', {st(3, {buttons = 'B', y = 127}), st(30, {x = 127, y = 60})}, 4, 6, 200)
sp('zelda_farore_air', {st(3, {buttons = 'B', y = 127}), st(30, {x = -127, y = 60})}, 4, 6, 200, HOP)
sp('zelda_transform_sheik', {st(3, {buttons = 'B', y = -127})}, 14, 0, 160)
sp('zelda_transform_air', {st(3, {buttons = 'B', y = -127})}, 14, 0, 200, HOP)
add('zelda_transform_roundtrip', FAR, seq({st(3, {buttons = 'B', y = -127})}, W(110), {st(3, {buttons = 'B', y = -127})}, W(110), {st(3, {buttons = 'A'})}, W(60)))
add('zelda_transform_hit', NEAR(14, 0, 60), seq({st(3, {buttons = 'B', y = -127})}, W(110), {st(3, {buttons = 'A'})}, W(30), {st(3, {buttons = 'B'})}, W(60), {st(3, {buttons = 'B', y = -127})}, W(110)))
add('zelda_transform_percent', {p1 = {0, 0}, p2 = {-100, 0}, pct1 = 77}, seq({st(3, {buttons = 'B', y = -127})}, W(110), {st(3, {buttons = 'B', y = -127})}, W(110)))
-- Sheik extras (Neutral B Needle Storm charge and fire, Side B Chain, Up B Vanish, Down B back to Zelda)
sp('sheik_needle_tap', {st(3, {buttons = 'B'})}, 30, 0, 140)
sp('sheik_needle_charged', {st(80, {buttons = 'B'}), st(3)}, 30, 0, 200)
sp('sheik_needle_cancel', {st(40, {buttons = 'B'}), st(3, {buttons = 'L'})}, 30, 0, 160)
sp('sheik_needle_air', {st(30, {buttons = 'B'})}, 30, 0, 160, HOP)
sp('sheik_chain', {st(3, {buttons = 'B', x = 127})}, 22, 0, 140)
sp('sheik_chain_air', {st(3, {buttons = 'B', x = 127})}, 22, 0, 140, HOP)
sp('sheik_chain_up', {st(3, {buttons = 'B', x = 127, y = 70})}, 22, 8, 140, HOP)
sp('sheik_vanish', {st(3, {buttons = 'B', y = 127}), st(20, {x = 127})}, 4, 0, 160)
sp('sheik_vanish_air', {st(3, {buttons = 'B', y = 127}), st(20, {x = -127, y = 60})}, 4, 0, 160, HOP)
sp('side_b', {st(3, {buttons = 'B', x = 127})}, 20, 0, 120)
sp('side_b_back', {st(3, {buttons = 'B', x = -127})}, -20, 0, 120)
sp('side_b_up', {st(3, {buttons = 'B', x = 127, y = 60})}, 20, 0, 120)
sp('air_side_b', {st(3, {buttons = 'B', x = 127})}, 22, 0, 120, HOP)
sp('air_side_b_back', {st(3, {buttons = 'B', x = -127})}, -22, 0, 120, HOP)
sp('up_b', {st(3, {buttons = 'B', y = 127})}, 4, 6, 120)
sp('up_b_fwd', {st(3, {buttons = 'B', y = 127}), st(12, {x = 127})}, 4, 6, 120)
sp('up_b_back', {st(3, {buttons = 'B', y = 127}), st(12, {x = -127})}, 4, 6, 120)
sp('air_up_b', {st(3, {buttons = 'B', y = 127})}, 4, 6, 120, HOP)
sp('air_up_b_fwd', {st(3, {buttons = 'B', y = 127}), st(12, {x = 127})}, 4, 6, 120, HOP)
sp('down_b', {st(3, {buttons = 'B', y = -127})}, 14, 0, 100)
sp('air_down_b', {st(3, {buttons = 'B', y = -127})}, 12, 0, 100, HOP)
sp('air_down_b_high', {st(3, {buttons = 'B', y = -127})}, 12, 0, 100, seq({st(14, {buttons = 'X'})}))
-- Falcon Dive / Raptor Boost / Falcon Kick follow-ups: throw direction held after the grab, and a catch followed by landing
sp('up_b_catch_throw_f', {st(3, {buttons = 'B', y = 127}), st(30, {x = 127})}, 4, 6, 140)
sp('up_b_catch_throw_b', {st(3, {buttons = 'B', y = 127}), st(30, {x = -127})}, 4, 6, 140)
sp('air_up_b_catch_hold', {st(3, {buttons = 'B', y = 127}), st(40, {y = 127})}, 4, 6, 140, HOP)
sp('side_b_catch_hold', {st(3, {buttons = 'B', x = 127}), st(30, {x = 127})}, 20, 0, 140)

-- ---- movement ----------------------------------------------------------------------------------------------------------------------
add('walk_slow', FAR, seq({st(40, {x = 30})}, W(20)))
add('walk_mid', FAR, seq({st(40, {x = 60})}, W(20)))
add('walk_fast', FAR, seq({st(40, {x = 90})}, W(20)))
add('dash', FAR, seq({st(4, {x = 127})}, W(40)))
add('dash_dance', FAR, seq({st(4, {x = 127}), st(4, {x = -127}), st(4, {x = 127}), st(4, {x = -127})}, W(30)))
add('run_stop', FAR, seq({st(50, {x = 127})}, W(40)))
add('run_turn', FAR, seq({st(30, {x = 127}), st(30, {x = -127})}, W(30)))
add('turn_stand', FAR, seq({st(8, {x = -50})}, W(20)))
add('crouch', FAR, seq({st(30, {y = -90})}, W(20)))
add('shorthop', FAR, seq(SHORTHOP, W(60)))
add('fullhop', FAR, seq(FULLHOP, W(90)))
add('double_jump', FAR, seq(FULLHOP, W(10), {st(3, {buttons = 'X'})}, W(80)))
add('double_jump_back', FAR, seq(FULLHOP, W(10), {st(3, {buttons = 'X', x = -127})}, W(80)))
add('air_drift', FAR, seq(FULLHOP, {st(40, {x = 127})}, W(40)))
add('fast_fall', FAR, seq(FULLHOP, W(20), {st(40, {y = -127})}, W(30)))
add('jump_fwd', FAR, seq({st(14, {buttons = 'X', x = 127})}, W(90)))
add('jump_back', FAR, seq({st(14, {buttons = 'X', x = -127})}, W(90)))
add('shield', FAR, seq({st(30, {buttons = 'L'})}, W(20)))
add('shield_tilt', FAR, seq({st(30, {buttons = 'L', x = 100, y = 50})}, W(20)))
add('shield_light', FAR, seq({st(30, {l = 80})}, W(20)))
add('roll_f', FAR, seq({st(3, {buttons = 'L', x = 127})}, W(50)))
add('roll_b', FAR, seq({st(3, {buttons = 'L', x = -127})}, W(50)))
add('spot_dodge', FAR, seq({st(3, {buttons = 'L', y = -127})}, W(40)))
add('air_dodge_neutral', FAR, seq(FULLHOP, W(8), {st(3, {buttons = 'L'})}, W(60)))
add('air_dodge_dir', FAR, seq(FULLHOP, W(8), {st(3, {buttons = 'L', x = 90, y = 40})}, W(60)))
add('wavedash', FAR, seq(SHORTHOP, {st(3, {buttons = 'L', x = 100, y = -90})}, W(40)))
add('wavedash_back', FAR, seq(SHORTHOP, {st(3, {buttons = 'L', x = -100, y = -90})}, W(40)))
add('shield_grab', FAR, seq({st(10, {buttons = 'L'}), st(3, {buttons = 'Z'})}, W(40)))
add('shield_jump', FAR, seq({st(10, {buttons = 'L'}), st(3, {buttons = 'X'})}, W(60)))
add('taunt_up', FAR, seq({st(3, {buttons = 'DUP'})}, W(120)))
add('taunt_down', FAR, seq({st(3, {buttons = 'DDOWN'})}, W(120)))
add('taunt_side', FAR, seq({st(3, {buttons = 'DLEFT'})}, W(120)))
add('landing_light', {p1 = {0, 6}, p2 = {-100, 0}}, W(40))
add('landing_heavy', {p1 = {0, 60}, p2 = {-100, 0}}, W(60))
add('landing_fastfall', {p1 = {0, 60}, p2 = {-100, 0}}, seq({st(20, {y = -127})}, W(40)))

-- ---- being hit: reactions, DI, techs, shield, shield break ------------------------------------------------------------------------
local P2FS = {st(3, N, {cx = 127})}      -- Mario's forward smash (c-stick) toward +x
local function hit(name, p2steps, p1steps, pct, p1pos)
  add(name, {p1 = p1pos or {10, 0}, p2 = {0, 0}, pct1 = pct or 0}, seq(p2steps, p1steps or {}, W(120)))
end
hit('hit_jab', {st(3, N, {buttons = 'A'})}, nil, 0)
hit('hit_ftilt', {st(3, N, {buttons = 'A', x = 45})}, nil, 0)
hit('hit_utilt', {st(3, N, {buttons = 'A', y = 35})}, nil, 0, {2, 0})
hit('hit_dtilt', {st(3, N, {buttons = 'A', y = -35})}, nil, 0)
hit('hit_fsmash_low', P2FS, nil, 0)
hit('hit_fsmash_mid', P2FS, nil, 60)
hit('hit_fsmash_high', P2FS, nil, 120)
hit('hit_usmash', {st(3, N, {cy = 127})}, nil, 60, {2, 0})
hit('hit_dsmash', {st(3, N, {cy = -127})}, nil, 60)
hit('hit_fsmash_di_up', P2FS, {st(60, {x = 0, y = 127})}, 60)
hit('hit_fsmash_di_away', P2FS, {st(60, {x = 127})}, 60)
hit('hit_fsmash_di_in', P2FS, {st(60, {x = -127})}, 60)
hit('hit_fsmash_tech', P2FS, rep(14, {st(2, {buttons = 'L'}), st(4)}), 40)
hit('hit_fsmash_tech_f', P2FS, rep(14, {st(2, {buttons = 'L', x = 127}), st(4)}), 40)
hit('hit_fsmash_tech_b', P2FS, rep(14, {st(2, {buttons = 'L', x = -127}), st(4)}), 40)
hit('hit_fsmash_notech', P2FS, nil, 40)
hit('hit_fsmash_asdi', P2FS, seq(W(5), {st(3, {cx = 0, cy = 127})}), 60)
hit('hit_up_tech', {st(3, N, {cy = 127})}, rep(14, {st(2, {buttons = 'L'}), st(4)}), 60, {2, 0})
hit('hit_getup_attack', P2FS, seq(W(60), {st(3, {y = 127}), st(3, {buttons = 'A'})}), 40)
hit('hit_getup_roll', P2FS, seq(W(60), {st(3, {x = 127})}), 40)
hit('hit_getup_stand', P2FS, seq(W(60), {st(3, {y = 127})}), 40)
-- aerial hit and meteor
add('hit_air_bair', {p1 = {10, 14}, p2 = {0, 0}, pct1 = 40}, seq({st(8, N, {buttons = 'X'}), st(3, N, {cx = -127})}, W(120)))
add('hit_air_dair_meteor', {p1 = {2, 22}, p2 = {0, 0}, pct1 = 40}, seq({st(10, N, {buttons = 'X'}), st(3, N, {cy = -127})}, W(120)))
-- shield: hits on a shielding Falcon, a long string to break it, a grab through it
add('shield_hit_jab', {p1 = {10, 0}, p2 = {0, 0}}, seq({st(3, {buttons = 'L'}, {buttons = 'A'})}, {st(30, {buttons = 'L'})}, W(40)))
add('shield_hit_fsmash', {p1 = {10, 0}, p2 = {0, 0}}, seq({st(6, {buttons = 'L'})}, {st(3, {buttons = 'L'}, {cx = 127})}, {st(40, {buttons = 'L'})}, W(40)))
add('shield_break', {p1 = {10, 0}, p2 = {0, 0}}, seq({st(6, {buttons = 'L'})}, rep(7, {st(3, {buttons = 'L'}, {cx = 127}), st(34, {buttons = 'L'})}), W(240)))
add('shield_grabbed', {p1 = {10, 0}, p2 = {0, 0}}, seq({st(8, {buttons = 'L'})}, {st(3, {buttons = 'L'}, {buttons = 'Z'})}, {st(40, {buttons = 'L'})}, W(70)))
-- KO and respawn
add('ko_bottom', {p1 = {0, -150}, p2 = {-100, 0}}, W(330))
add('ko_side', {p1 = {260, 20}, p2 = {-100, 0}}, W(330))
add('ko_top', {p1 = {0, 230}, p2 = {-100, 0}}, W(330))

-- ---- ledge: from below the stage's left edge -----------------------------------------------------------------------------------------
local LEDGE = {p1 = {-76, -12}, p2 = {100, 0}}
local function ledge(name, after, pre)
  add(name, LEDGE, seq(pre or {st(8, {x = 40})}, W(40), after, W(120)))
end
ledge('ledge_hang', {})
ledge('ledge_getup', {st(3, {y = 127})})
ledge('ledge_getup_late', seq(W(60), {st(3, {y = 127})}))
ledge('ledge_attack', {st(3, {buttons = 'A'})})
ledge('ledge_roll', {st(3, {x = 127})})
ledge('ledge_roll_late', seq(W(70), {st(3, {x = 127})}))
ledge('ledge_jump', {st(3, {buttons = 'X'})})
ledge('ledge_jump_in', {st(3, {buttons = 'X', x = 127})})
ledge('ledge_drop', {st(3, {y = -127})})
ledge('ledge_drop_back', {st(3, {x = -127})})
ledge('ledge_drop_airdodge', seq({st(3, {y = -127})}, W(6), {st(3, {buttons = 'L', x = 100})}))
ledge('ledge_drop_jump', seq({st(3, {y = -127})}, W(6), {st(3, {buttons = 'X'})}))
ledge('ledge_drop_upb', seq({st(3, {y = -127})}, W(6), {st(3, {buttons = 'B', y = 127})}))
ledge('ledge_timeout', {}, nil)
ledge('ledge_shield_getup', {st(3, {buttons = 'L'})})
-- recovery: up-B and side-B toward the ledge from below and beside it
add('recover_upb_from_below', {p1 = {-90, -30}, p2 = {100, 0}}, seq({st(3, {buttons = 'B', y = 127}), st(40, {x = 127, y = 60})}, W(150)))
add('recover_upb_straight', {p1 = {-90, -30}, p2 = {100, 0}}, seq({st(3, {buttons = 'B', y = 127}), st(40, {x = 127})}, W(150)))
add('recover_sideb', {p1 = {-90, -10}, p2 = {100, 0}}, seq({st(3, {buttons = 'B', x = 127}), st(40, {x = 127})}, W(150)))
add('recover_jump_upb', {p1 = {-100, -25}, p2 = {100, 0}}, seq({st(3, {buttons = 'X', x = 127}), st(8), st(3, {buttons = 'B', y = 127}), st(40, {x = 127})}, W(150)))
add('recover_falcon_kick', {p1 = {-90, -10}, p2 = {100, 0}}, seq({st(3, {buttons = 'B', y = -127, x = 60}), st(40, {x = 60})}, W(150)))
add('recover_airdodge_ledge', {p1 = {-80, -12}, p2 = {100, 0}}, seq({st(3, {buttons = 'L', x = 90})}, W(120)))


-- ---- more coverage (round 2): hits from the front and by percent, tumble, techs, downs, projectile, edge states ---------------------------------
local P2TURN = {st(6, N, {x = -50}), st(4)}
local function hitf(name, p2steps, p1steps, pct, p1pos)   -- Mario turned toward Falcon (a hit from the front)
  add(name, {p1 = p1pos or {-10, 0}, p2 = {0, 0}, pct1 = pct or 0}, seq(P2TURN, p2steps, p1steps or {}, W(140)))
end
local P2FSL = {st(3, N, {cx = -127})}
for _, pct in ipairs({0, 30, 60, 90, 120, 160}) do
  hit('hitb_fsmash_p' .. pct, P2FS, nil, pct)
  hitf('hitf_fsmash_p' .. pct, P2FSL, nil, pct)
end
hitf('hitf_jab', {st(3, N, {buttons = 'A'})}, nil, 0)
hitf('hitf_ftilt', {st(3, N, {buttons = 'A', x = 45})}, nil, 0)
hitf('hitf_utilt', {st(3, N, {buttons = 'A', y = 35})}, nil, 0, {-4, 0})
hitf('hitf_dtilt', {st(3, N, {buttons = 'A', y = -35})}, nil, 0)
hitf('hitf_usmash', {st(3, N, {cy = 127})}, nil, 80, {-4, 0})
hitf('hitf_dsmash', {st(3, N, {cy = -127})}, nil, 80)
hitf('hitf_bair_fh', {st(3, N, {cx = -127})}, nil, 20)
hit('hit_fsmash_p100_tech', P2FS, rep(14, {st(2, {buttons = 'L'}), st(4)}), 100)
hit('hit_fsmash_p100_tech_f', P2FS, rep(14, {st(2, {buttons = 'L', x = 127}), st(4)}), 100)
hit('hit_fsmash_p100_tech_b', P2FS, rep(14, {st(2, {buttons = 'L', x = -127}), st(4)}), 100)
hit('hit_fsmash_p100_notech', P2FS, nil, 100)
hit('hit_fsmash_p100_down_stand', P2FS, seq(W(70), {st(3, {y = 127})}), 100)
hit('hit_fsmash_p100_down_attack', P2FS, seq(W(70), {st(3, {buttons = 'A'})}), 100)
hit('hit_fsmash_p100_down_roll_f', P2FS, seq(W(70), {st(3, {x = 127})}), 100)
hit('hit_fsmash_p100_down_roll_b', P2FS, seq(W(70), {st(3, {x = -127})}), 100)
hit('hit_fsmash_p100_down_wait', P2FS, W(200), 100)
hit('hit_fsmash_p100_di_down', P2FS, {st(60, {y = -127})}, 100)
hit('hit_fsmash_p100_airdodge', P2FS, seq(W(12), {st(3, {buttons = 'L'})}), 100)
hit('hit_fsmash_p100_upb', P2FS, seq(W(20), {st(3, {buttons = 'B', y = 127})}), 100)
hit('hit_fsmash_p100_jump', P2FS, seq(W(20), {st(3, {buttons = 'X'})}), 100)
hit('hit_dsmash_p60_meteorish', {st(3, N, {cy = -127})}, nil, 60)
hit('hit_usmash_p100', {st(3, N, {cy = 127})}, nil, 100, {2, 0})
hit('hit_usmash_p160_top', {st(3, N, {cy = 127})}, nil, 160, {2, 0})
add('hit_air_usmash', {p1 = {2, 9}, p2 = {0, 0}, pct1 = 30}, seq(W(4), {st(3, N, {cy = 127})}, W(140)))
add('hit_air_fsmash', {p1 = {10, 9}, p2 = {0, 0}, pct1 = 50}, seq(W(2), {st(3, N, {cx = 127})}, W(140)))
add('hit_air_nair', {p1 = {6, 12}, p2 = {0, 0}, pct1 = 10}, seq(W(2), {st(3, N, {buttons = 'X'}), st(8), st(3, N, {buttons = 'A'})}, W(140)))
add('hit_projectile', {p1 = {40, 0}, p2 = {0, 0}, pct1 = 0}, seq({st(3, N, {buttons = 'B'})}, W(120)))
add('hit_projectile_shield', {p1 = {40, 0}, p2 = {0, 0}, pct1 = 0}, seq({st(60, {buttons = 'L'}, {buttons = 'B'})}, W(80)))
add('hit_shield_air', {p1 = {10, 0}, p2 = {0, 0}}, seq({st(8, {buttons = 'L'})}, {st(3, {buttons = 'L'}, {buttons = 'A', y = 35})}, {st(30, {buttons = 'L'})}, W(40)))
-- walls of the world: ledge-edge states
add('teeter', {p1 = {62, 0}, p2 = {-100, 0}}, seq({st(30, {x = 40})}, W(40)))
add('run_off_edge', {p1 = {50, 0}, p2 = {-100, 0}}, seq({st(60, {x = 127})}, W(60)))
add('walk_off_edge_jump', {p1 = {60, 0}, p2 = {-100, 0}}, seq({st(14, {x = 60}), st(3, {buttons = 'X'})}, W(60)))
add('down_b_off_edge', {p1 = {60, 0}, p2 = {-100, 0}}, seq({st(3, {buttons = 'B', y = -127})}, W(100)))
add('down_b_off_edge_fwd', {p1 = {56, 0}, p2 = {-100, 0}}, seq({st(3, {buttons = 'B', y = -127, x = 100})}, {st(40, {x = 100})}, W(100)))
add('side_b_off_edge', {p1 = {56, 0}, p2 = {-100, 0}}, seq({st(3, {buttons = 'B', x = 127})}, W(110)))
add('up_b_off_edge_catch', {p1 = {56, 0}, p2 = {74, -6}}, seq({st(3, {buttons = 'B', y = 127}), st(30, {x = 127})}, W(130)))
add('up_b_catch_air_throw', {p1 = {0, 20}, p2 = {6, 20}}, seq({st(3, {buttons = 'B', y = 127})}, W(130)))
add('up_b_catch_air_d', {p1 = {0, 20}, p2 = {6, 20}}, seq({st(3, {buttons = 'B', y = 127}), st(30, {y = -127})}, W(130)))
add('ko_left', {p1 = {-260, 20}, p2 = {100, 0}}, W(330))
add('ko_top_fast', {p1 = {0, 150}, p2 = {100, 0}}, seq({st(60, N)}, W(300)))
add('dash_grab_20', NEAR(20), seq(DASH, {st(3, {buttons = 'Z'})}, W(80)))
add('dash_grab_24', NEAR(24), seq(DASH, {st(3, {buttons = 'Z'})}, W(80)))
add('dash_grab_30', NEAR(30), seq(DASH, {st(3, {buttons = 'Z'})}, W(80)))
add('taunt_right', FAR, seq({st(3, {buttons = 'DRIGHT'})}, W(120)))
add('walk_fast_long', FAR, seq({st(60, {x = 127})}, W(10)))
add('jump_fwd_double_fwd', FAR, seq({st(14, {buttons = 'X', x = 127})}, W(8), {st(3, {buttons = 'X', x = 127})}, W(60)))
add('fall_after_double', FAR, seq(FULLHOP, W(10), {st(3, {buttons = 'X'})}, W(70), {st(30, {x = -127})}, W(30)))
add('run_direct', FAR, seq({st(20, {x = 127}), st(30, {x = -127})}, W(30)))
add('crouch_attack', FAR, seq({st(10, {y = -90}), st(3, {buttons = 'A', y = -90})}, W(40)))
add('crouch_shield', FAR, seq({st(10, {y = -90}), st(10, {buttons = 'L', y = -90})}, W(30)))
add('aerial_grab_ledge_hop', LEDGE, seq({st(8, {x = 40})}, W(40), {st(3, {y = -127})}, W(4), {st(3, {buttons = 'X'})}, W(8), {st(3, {cx = 127})}, W(80)))


-- tumble, tech and the down states, from the front at 70% (the knockback keeps Falcon on the stage)
for _, o in ipairs({{'wait', W(200)}, {'stand', seq(W(60), {st(3, {y = 127})})}, {'attack', seq(W(60), {st(3, {buttons = 'A'})})},
                    {'roll_f', seq(W(60), {st(3, {x = 127})})}, {'roll_b', seq(W(60), {st(3, {x = -127})})},
                    {'stand_l', seq(W(70), {st(3, {y = 127})})}, {'attack_l', seq(W(70), {st(3, {buttons = 'A'})})},
                    {'roll_f_l', seq(W(70), {st(3, {x = 127})})}, {'roll_b_l', seq(W(70), {st(3, {x = -127})})},
                    {'tech', rep(14, {st(2, {buttons = 'L'}), st(4)})}, {'tech_f', rep(14, {st(2, {buttons = 'L', x = 127}), st(4)})},
                    {'tech_b', rep(14, {st(2, {buttons = 'L', x = -127}), st(4)})}}) do
  hitf('hitf_fsmash_p70_' .. o[1], P2FSL, o[2], 70)
end
hitf('hitf_dsmash_p70_wait', {st(3, N, {cy = -127})}, W(200), 70)
hitf('hitf_usmash_p110_wait', {st(3, N, {cy = 127})}, W(200), 110, {-4, 0})

-- ---- run -------------------------------------------------------------------------------------------------------------------------------
local function f9(v) return string.format('%.9g', v or 0) end
local function fnv(h, s)
  for i = 1, #s do h = ((h ~ s:byte(i)) * 16777619) & 0xFFFFFFFF end
  return h
end
local function fields(p, port)
  local hb = {}
  for _, b in ipairs(gd.hitboxes(port) or {}) do
    hb[#hb + 1] = string.format('%d,%s,%s,%s,%s,%s,%s,%s,%s,%s', b.bone or -1, f9(b.damage), f9(b.angle), f9(b.kbg), f9(b.bkb), f9(b.wbk), f9(b.radius), f9(b.x), f9(b.y), f9(b.z))
  end
  local hu = gd.hurtboxes(port) or {}
  local hh = 2166136261
  for _, u in ipairs(hu) do
    hh = fnv(hh, string.format('%d,%s,%s,%s,%s,%s,%s,%s,%s;', u.bone or -1, tostring(u.state), f9(u.ax), f9(u.ay), f9(u.az), f9(u.bx), f9(u.by), f9(u.bz), f9(u.radius)))
  end
  local detail = ''
  if CFG.DETAIL then
    local t = {}
    for _, u in ipairs(hu) do t[#t + 1] = string.format('%d:%s,%s,%s|%s,%s,%s|%s', u.bone or -1, f9(u.ax), f9(u.ay), f9(u.az), f9(u.bx), f9(u.by), f9(u.bz), f9(u.radius)) end
    detail = ' HU[' .. table.concat(t, ';') .. ']'
  end
  return string.format('%d %d %s %s %s %s %s %s %d %s %s %s %s %s %s %s %d %d %d %s HB[%s] H%08x%s',
    p.action or -1, math.floor(p.action_frame or 0), f9(p.anim_frame_f), f9(p.x), f9(p.y), f9(p.vx), f9(p.vy), f9(p.ground_vel),
    p.facing or 0, f9(p.percent), f9(p.hitlag), f9(p.hitstun), f9(p.kb_vx), f9(p.kb_vy), f9(p.shield), f9(p.scale),
    p.jumps_used or 0, p.intangible or 0, p.invincible or 0, tostring(p.body_state), table.concat(hb, ';'), hh, detail)
end

gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no match')
    gd.teleport(1, 0, 0); gd.teleport(2, -100, 0); gd.set_percent(1, 0); gd.set_percent(2, 0)
    gd.wait(30); gd.savestate(1); gd.wait(2)
    local total, count = 2166136261, 0
    for _, name in ipairs(order) do
      if not ONLY or ONLY[name] then
        local sc = S[name]
        gd.input(1, {}, 1); gd.input(2, {}, 1)
        gd.loadstate(1); gd.wait(3)
        local s = sc.setup
        if s.p1 then gd.teleport(1, s.p1[1], s.p1[2]) end
        if s.p2 then gd.teleport(2, s.p2[1], s.p2[2]) end
        gd.set_percent(1, s.pct1 or 0); gd.set_percent(2, s.pct2 or 0)
        gd.wait(2)
        local h, n, seen, last = 2166136261, 0, {}, nil
        for _, step in ipairs(sc.steps) do
          local frames, i1, i2 = step[1], step[2], step[3]
          if i1 == N then gd.input(1, {}, frames) else gd.input(1, i1, frames) end
          if i2 == N then gd.input(2, {}, frames) else gd.input(2, i2, frames) end
          for _ = 1, frames do
            gd.wait(1); n = n + 1
            local a, b = gd.player(1), gd.player(2)
            local line = string.format('R%08x ', gd.rng()) .. fields(a, 1) .. ' | ' .. fields(b, 2)
            h = fnv(h, line)
            gd.log(string.format('PF %s %d | %s', name, n, line))
            if a.motion_name ~= last then seen[#seen + 1] = a.motion_name; last = a.motion_name end
          end
        end
        gd.log(string.format('PS %s frames=%d hash=%08x seen=%s', name, n, h, table.concat(seen, '>')))
        total = fnv(total, string.format('%08x', h)); count = count + 1
      end
    end
    gd.log(string.format('PS TOTAL %08x scenarios=%d', total, count))
    gd.log('PS DONE')
  end)
  if not ok then gd.log('PS FAIL ' .. tostring(why)) end
  gd.quit()
end)
