# Goku remake: candidate animation sheet

Rebuilt 2026-10-11 from the OWNER own descriptions: `ROW-NOTES.md` (all 303 LAB rows) and `CLIP-NOTES.md` (the library clips covered so far).
The earlier planner candidates were found unreliable and are gone. **Only clips the owner described are listed**; every candidate quotes the
owner words and the LAB row it was described in. A clip marked "unclear", "terrible" or "looks wrong" is excluded (list at the end).
A slot with no good described clip is a **GAP**, with the undescribed library clips most worth looking at next ("look next").

Status: OK = a described clip fits; KEEP = engine default / designed animation stays; PARTIAL = part of the slot has a pick, part is a GAP;
WEAK = only a fallback the owner rated poorly; GAP = nothing described fits. `rec` marks the recommended pick; write yours in `owner pick`.
Animations only: hitboxes are authored by hand afterwards (REMAKE-PLAN.md section 1). Always floating is visual only (standing clips are
acceptable). Clip names are XV2 library actions (`x` + source name). Metrics come from `tools/remake_preview.py` (local); montage PNGs are
XV2-derived and never committed. Preview any clip in the LAB (REMAKE or CLIPS mode) or with `tools/clips.ps1 <clip>`.


## 1 Locomotion (always floating)

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| **KEEP** Idle | Wait, Rebirth, RebirthWait, Sleep | GOK_BAS_STAND_S (Sleep still ground STAND) | Resting stance; must loop, tiny bob, readable as hovering | `(engine default floating idle)` **rec**: owner: "idle, floating" (rows 2-6, 32, 33, 65 are the engine default and the owner is happy with them). No XV2 clip is needed. |  |
| **OK** Walk (slow/mid/fast) | WalkSlow, WalkMiddle, WalkFast | GOK_BAS_WALK (ground walk, 70f) x one clip | No walking: a slow drift whose rate scales with stick | `xGOK_BAS_WALK` **rec**: owner: "slow walk forward" (row 7 WalkSlow; 8, 9 "identical"). Ground walk shown while floating (visual only); the owner described no flying drift clip. (70f; reach 2.7 R_Foot f0; high 0.5; fastest L_Foot f24)<br>**look next** (undescribed): `xGOK_BAS_BUKUU_F_S`, `xGOK_BAS_BUKUU_B_S` | **xGOK_BAS_WALK** |
| **OK** Run | Run, RunDirect | GOK_BAS_RUN (ground run, 30f) | Full-speed travel, loop | `xGOK_BAS_RUN` **rec**: owner: "run cycle, loops perfectly" (row 13 Run). (30f; reach 7.8 R_Hand f12; high 5.7; fastest L_Hand f24) | **xGOK_BAS_RUN** |
| **OK** Dash (start) | Dash | BOOST_F_00 x0.55, eased into Run | Dash burst before Run | `xGOK_BAS_BOOST_F_00` **rec**: owner: "initial dash" (row 12 Dash). (24f; reach 5.4 L_Hand f0; high 4.3; fastest R_Foot f22) | **xGOK_BAS_BOOST_F_00** |
| **GAP** Run brake / stop | RunBrake | BOOST_F_02 from f6 x0.75 | Stopping out of Run | **look next** (undescribed): `xCMN_BAS_BRAKE_S`, `xCMN_BAS_BRAKE_B_S`, `xGOK_BAS_BUKUU_B_S`<br>note: The only clip used (xGOK_BAS_BOOST_F_02) was described as "meant to be runbrake/skid stop, but looks wrong" (row 14): excluded. |  |
| **OK** Turn (wait / run) | Turn, TurnRun | authored 180 yaw on Wait / BOOST_F_02 + yaw | Turnaround; the earlier note "XV2 has no turn" is wrong, CMN has one | `xGOK_BAS_STAND_S` **rec**: owner: "turn around" (row 10 Turn). Turn (wait). (100f; reach 5.4 L_Hand f0; high 4.5; fastest R_Foot f90)<br>`xGOK_BAS_BOOST_F_02`: owner: "turn run" (row 11 TurnRun). Turn while running (TurnRun only; excluded for RunBrake). (19f; reach 5.4 L_Hand f18; high 4.3; fastest R_Foot f10)<br>**look next** (undescribed): `xCMN_BAS_TURN` | **xGOK_BAS_STAND_S** |
| **OK** Crouch | Squat, SquatWait, SquatRv | GOK_BAS_JUMP landing-crouch crop (grounded) | A floating crouch: sink and tuck, never touching the floor | `xGOK_BAS_JUMP` **rec**: owner: "crouch start (fast, short) / crouch hold / unsquat" (rows 30, 31, 34 Squat*). (70f; reach 6.2 L_Hand f4; high 9.6; fastest R_Hand f2) | **xGOK_BAS_JUMP** |
| **KEEP** Jump squat | KneeBend | JUMP crop | 4-frame squat before the jump (Melee: jump_startup_time) | `(engine default jump squat)` **rec**: owner: "jump squat" (row 15, engine default); no complaint. |  |
| **GAP** Jump (ground, forward/back) | JumpF, JumpB | JUMP_FRONT_00 / JUMP_BACK_00 x0.33 (55f; owner: poor, punch list 9; queue 4: <= 40f) | Rise out of a jump; Melee row length = rise | **look next** (undescribed): `xGOK_BAS_BUKUU_UP`, `xGOK_BAS_JUMP_BACK_02`, `xGOK_BAS_BOOST_F_01`<br>note: xGOK_BAS_JUMP_FRONT_00 and xGOK_BAS_JUMP_BACK_00 are "terrible jump forward/backward" (rows 16, 17): excluded. |  |
| **OK** Double jump (air jump) | JumpAerialF, JumpAerialB | JUMP_FRONT_01 / BACK_01 x0.27 (60f) | Second jump in the air; reads as a burst | `xGOK_BAS_JUMP_FRONT_01` **rec**: owner: "terrible front flip; serviceable if spin is faster" (row 18 JumpAerialF). Needs a faster spin (retime). (16f; reach 2.9 L_Hand f4; high 2.8; fastest L_Foot f2)<br>`xGOK_BAS_JUMP_BACK_01`: owner: "terrible back flip; serviceable if spin is faster" (row 19 JumpAerialB). Needs a faster spin (retime). (16f; reach 2.9 L_Hand f8; high 3.0; fastest L_Foot f2) | **xGOK_BAS_JUMP_FRONT_01** |
| **OK** Fall | Fall, FallF/B, FallAerial*, FallSpecial*, Pass | GOK_BAS_BUKUU_DOWN (adapted) | Falling and helpless fall | `xGOK_BAS_BUKUU_DOWN` **rec**: owner: "fall, looks good" (rows 20-28 Fall*). (50f; reach 2.4 L_Hand f8; high 9.9; fastest L_Hand f20) | **xGOK_BAS_BUKUU_DOWN** |
| **OK** Landing (ground) | Landing, LandingFallSpecial, LandingAir* | JUMP_FRONT_02 from f10 (aliased to all 5 air landings) | Touch-down settle; Melee lag frames stay | `xGOK_BAS_JUMP_FRONT_02` **rec**: owner: "land from a jump" (row 35 Landing; rows 73-76 "landing (from aerials?)"). (31f; reach 5.5 L_Hand f24; high 8.6; fastest R_Foot f2) | **xGOK_BAS_JUMP_FRONT_02** |

## 2 Defence

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| **OK** Shield | GuardOn, Guard, GuardOff, GuardSetOff, GuardReflect | GRD_KAMAE (ground) / GRD_L | Hold shield, release, hit-in-shield | `xGOK_GRD_KAMAE` **rec**: owner: "start guard / hold guard" (rows 37, 38 GuardOn, Guard). GuardOn/Guard. (130f; reach 5.8 L_Foot f52; high 4.3; fastest R_Hand f2)<br>`xGOK_GRD_L`: owner: "release guard" (row 39 GuardOff). GuardOff only. (30f; reach 6.2 L_Foot f4; high 4.7; fastest L_Hand f4) | **xGOK_GRD_KAMAE** |
| **OK** Shield break | ShieldBreakFly/Fall/DownU/D/StandU/D | CMN dizzy / stun rows | Shield broken | `xCMN_DMG_UP_F` **rec**: owner: "knocked down onto his back" (row 177 DamageFlyHi; 264, 274, 286). ShieldBreakFly. (49f; reach 7.7 L_Foot f16; high 7.6; fastest L_Hand f6)<br>`xCMN_DMG_TUMBLE_F`: owner: "launched: rapid 360 spin along head-to-toe axis (tumble candidate)" (row 29 DamageFall). ShieldBreakFall (row 287 uses it). (69f; reach 8.1 L_Hand f68; high 5.4; fastest R_Foot f40)<br>`xCMN_BAS_DOWN_STAND_AOMUKE`: owner: "get-up" (row 186 DownStandU). ShieldBreakStandU. (40f; reach 7.8 R_Foot f0; high 2.1; fastest R_Hand f26)<br>`xCMN_BAS_DOWN_STAND_UTSUBUSE`: owner: "get-up from a knockdown/missed tech" (row 194 DownStandD). ShieldBreakStandD. (40f; reach 8.4 R_Hand f0; high 3.1; fastest L_Foot f14)<br>`xCMN_DMG_DOWN_BOUND_UTSUBUSE`: owner: "lying face down (techable?)" (row 191 DownBoundD). ShieldBreakDownD. (59f; reach 9.5 L_Hand f2; high 5.1; fastest L_Hand f8)<br>note: ShieldBreakDownU (xCMN_DMG_DOWN_BOUND_AOMUKE) is "unclear": excluded. | **xCMN_DMG_UP_F** |
| **PARTIAL** Roll / spot dodge / air dodge | EscapeF, EscapeB, EscapeN, EscapeAir | STEP_F_S, STEP_B_S, STEP_L_S x1.85/1.5 | Dodges: intangible frames are Melee rules | `xGOK_BAS_STEP_F_S` **rec**: owner: "dodge/dash forward, keeps facing" (row 42 EscapeF). Roll forward. (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4)<br>`xGOK_BAS_STEP_B_S`: owner: "dodge/dash backward, keeps facing" (row 43 EscapeB). Roll back. (45f; reach 6.2 R_Foot f18; high 4.9; fastest L_Hand f6)<br>**look next** (undescribed): `xGOK_BAS_STEP_R_S`, `xGOK_GRD_L_L_S`, `xGOK_GRD_L_R_S`<br>note: Spot dodge and air dodge: GAP. xGOK_BAS_STEP_L_S is "unclear: tiptoeing sideways" (rows 41, 44): excluded. | **xGOK_BAS_STEP_F_S** |
| **GAP** Dizzy | Furafura | GOK_BAS_STUN_02 | Stun | **look next** (undescribed): `xGOK_BAS_STUN_00`, `xGOK_BAS_STUN_01`, `xGOK_BAS_STUN_02`, `xCMN_BAS_STUN_01_S`, `xCMN_BAS_STUN_02_S`<br>note: No dizzy clip was described. |  |

## 3 Normals (ground)

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| **OK** Jab 1 (L1) | Attack11 | ATC_002 from f9 (BAC 300) | Opener, fast, safe; string link 1; combo: starter; links to jab2 | `xGOK_ATC_002` **rec**: owner: "flying position, left-hand punch in front (jab 1?)" (row 46 Attack11). (45f; reach 9.9 L_Hand f14; high 6.2; fastest L_Hand f12) | **xGOK_ATC_002** |
| **GAP** Jab 2 (L2) | Attack12 | ATC_003 (BAC 301) | Second string hit; combo: link 2 | `xGOK_ATC_003` **rec**: owner: "standing right-hand punch, harder than a jab; tilt candidate, not smash" (row 47 Attack12). Fallback only: the owner wants this one as a tilt, so it is also the Forward tilt pick. (41f; reach 7.5 R_Hand f6; high 8.8; fastest R_Hand f6)<br>**look next** (undescribed): `xGOK_ATC_000`, `xGOK_ATC_001`, `xGOK_ATC_009`, `xGOK_ATC_010`<br>note: No described clip is a second jab. |  |
| **GAP** Jab 3 (L3) | Attack13, Light3 state | ATC_017 (BAC 302) | Third hit, ends jab / continues string; combo: link 3; Light4 = ATC_009, Light5 = ATC_022 in the combo package | **look next** (undescribed): `xGOK_ATC_009`, `xGOK_ATC_014`, `xGOK_ATC_015`, `xGOK_ATC_016`<br>note: The only described kick, xGOK_ATC_017, is a spike candidate (Down air). |  |
| **OK** Rapid jab | Attack100Start/Loop/End | ATC_028 (5-hit flurry) | Held-A flurry | `xGOK_ATC_028` **rec**: owner: "flying, follow-up of a left punch into multi-kick aerial" (rows 49-51 Attack100*). Loop/exit of the same clip (rows 50, 51: "loop of 49" / "exit of 49"); the loop point still needs choosing. (65f; reach 8.7 R_Foot f18; high 7.9; fastest R_Foot f18)<br>`xGOK_ATC_SHOT_N_LOOP`: owner: "while floating, firing ki blasts from the hands (like Mega Man's in Ultimate)" (rows 150, 154, 158, 162 ItemScopeRapid*). Alternative: a ki-fire rapid jab. (14f; reach 6.0 L_Hand f10; high 5.0; fastest L_Hand f6) | **xGOK_ATC_028** |
| **OK** Forward tilt | AttackS3S, S3Hi, S3HiS, S3LwS, S3Lw | ATC_008 (BAC 475) for all five rows | Spacing poke; Hi/Lw rows are angled variants (currently the same clip); combo: starter; spacing | `xGOK_ATC_003` **rec**: owner: "standing right-hand punch, harder than a jab; tilt candidate, not smash" (row 47 Attack12). (41f; reach 7.5 R_Hand f6; high 8.8; fastest R_Hand f6)<br>`xGOK_ATC_007`: owner: "standing roundhouse-ish kick; standing fsmash/ftilt candidate" (rows 68, 69 AttackAirN/F; row 72 AttackAirLw). Alternative. (49f; reach 6.9 R_Foot f16; high 7.6; fastest R_Foot f16)<br>`xGOK_ATC_008`: owner: "standing left-foot kick in front; starts floating midway" (rows 53-57 AttackS3*). Alternative: a kick tilt. (47f; reach 8.8 R_Foot f26; high 6.1; fastest R_Foot f12) | **xGOK_ATC_003** |
| **OK** Up tilt | AttackHi3 | ATC_013 from f20 (owner: dumb, punch list 2) | Anti-air; combo: starter; anti-air | `xGOK_ATC_004` **rec**: owner: "launcher; utilt/usmash candidate" (row 66 AttackHi4). (43f; reach 7.1 L_Hand f10; high 10.5; fastest R_Hand f14)<br>`xGOK_ATC_025`: owner: "up air material, but animated from standing, not flying" (row 71 AttackAirHi). Weak alternative: up-air material. (61f; reach 7.4 R_Hand f24; high 8.2; fastest R_Foot f22) | **xGOK_ATC_004** |
| **OK** Down tilt | AttackLw3 | ATC_020_S from f11 (low slide kick) | Low poke; combo: starter; low | `xGOK_ATC_020_S` **rec**: owner: "flying low kick" (row 59 AttackLw3). Current Dtilt source, no complaint. (51f; reach 8.4 R_Foot f12; high 9.7; fastest R_Hand f8)<br>`xGOK_ATC_012`: owner: "low sweep; dtilt/dsmash candidate" (row 67 AttackLw4). Alternative. (40f; reach 9.3 R_Hand f4; high 5.0; fastest R_Foot f10) | **xGOK_ATC_020_S** |
| **WEAK** Dash attack | AttackDash | ATC_011 from f13 (flying side kick) | Run-in; combo: starter | `xGOK_ATC_011` **rec**: owner: "standing jumping-backwards thrust kick (dash attack: meh)" (row 52 AttackDash). Fallback only; the owner rates it meh. (70f; reach 8.6 R_Foot f16; high 5.5; fastest R_Hand f16)<br>**look next** (undescribed): `xGOK_ATC_024`, `xGOK_ATC_021_S`, `xGOK_BAS_BOOST_F_01` | **xGOK_ATC_011** |
| **OK** Forward smash | AttackS4S, S4Hi, S4HiS, S4LwS, S4Lw | ATC_006 from f5 (BAC 343) for all five rows | Charge-able finisher | `xGOK_ATC_007` **rec**: owner: "standing roundhouse-ish kick; standing fsmash/ftilt candidate" (rows 68, 69 AttackAirN/F; row 72 AttackAirLw). Fair spike clip xGOK_ATC_006 is kept for Forward air. (49f; reach 6.9 R_Foot f16; high 7.6; fastest R_Foot f16)<br>`xGOK_ATC_008`: owner: "standing left-foot kick in front; starts floating midway" (rows 53-57 AttackS3*). Alternative. (47f; reach 8.8 R_Foot f26; high 6.1; fastest R_Foot f12) | **xGOK_ATC_007** |
| **PARTIAL** Up smash | AttackHi4 | ATC_004 from f5 (BAC 342 uppercut) | Launcher / anti-air finisher; combo: launcher (route target HeavyUp) | `xGOK_ATC_004` **rec**: owner: "launcher; utilt/usmash candidate" (row 66 AttackHi4). Same clip as Up tilt (the only described launcher); retime or crop to tell them apart. (43f; reach 7.1 L_Hand f10; high 10.5; fastest R_Hand f14)<br>**look next** (undescribed): `xGOK_ATC_026`, `xGOK_ATC_027`, `xGOK_ATC_029`, `xGOK_ATC_005` | **xGOK_ATC_004** |
| **OK** Down smash | AttackLw4 | ATC_012 from f2 (split sweep, BAC 341) | Low two-sided sweep; combo: route target dsmash | `xGOK_ATC_012` **rec**: owner: "low sweep; dtilt/dsmash candidate" (row 67 AttackLw4). (40f; reach 9.3 R_Hand f4; high 5.0; fastest R_Foot f10)<br>`xGOK_ATC_020_S`: owner: "flying low kick" (row 59 AttackLw3). Alternative. (51f; reach 8.4 R_Foot f12; high 9.7; fastest R_Hand f8) | **xGOK_ATC_012** |

## 4 Aerials

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| **OK** Neutral air | AttackAirN | ATC_007 from f9 (split kick, 18 active frames) | Multi-hit sex-kick; Nair>Nair chain; combo: link; chains to itself | `xGOK_ATC_028` **rec**: owner: "flying, follow-up of a left punch into multi-kick aerial" (rows 49-51 Attack100*). "multi-kick aerial". (65f; reach 8.7 R_Foot f18; high 7.9; fastest R_Foot f18)<br>`xGOK_ATC_007`: owner: "standing roundhouse-ish kick; standing fsmash/ftilt candidate" (rows 68, 69 AttackAirN/F; row 72 AttackAirLw). Alternative. (49f; reach 6.9 R_Foot f16; high 7.6; fastest R_Foot f16) | **xGOK_ATC_028** |
| **OK** Forward air | AttackAirF | ATC_007 from f5 (same clip as nair; punch list 4) | Forward ender; combo: ender | `xGOK_ATC_006` **rec**: owner: "flying, two-hand clasped slam in front; fair spike candidate" (rows 60-64 AttackS4*). Spike fair. (58f; reach 9.1 L_Hand f18; high 9.5; fastest R_Hand f18)<br>`xGOK_ATC_007`: owner: "standing roundhouse-ish kick; standing fsmash/ftilt candidate" (rows 68, 69 AttackAirN/F; row 72 AttackAirLw). Alternative (row 69). (49f; reach 6.9 R_Foot f16; high 7.6; fastest R_Foot f16) | **xGOK_ATC_006** |
| **GAP** Back air | AttackAirB | CROSS-PORT Melee Luigi AttackAirB (owner: looks and works as intended) | Back attack | **look next** (undescribed): `xGOK_ATC_014`, `xGOK_ATC_015`, `xGOK_ATC_016`, `xGOK_ATC_018_S`, `xGOK_ATC_019_S`<br>note: Row 70 is Luigi's back air ("Luigi back air?"): not an XV2 move. |  |
| **OK** Up air | AttackAirHi | ATC_025 from f6 (somersault kick; owner: looks good, keep) | Juggle / launcher follow-up; combo: route: Uair>Nair | `xGOK_ATC_025` **rec**: owner: "up air material, but animated from standing, not flying" (row 71 AttackAirHi). Standing animation: needs a floating read. (61f; reach 7.4 R_Hand f24; high 8.2; fastest R_Foot f22) | **xGOK_ATC_025** |
| **OK** Down air | AttackAirLw | ATC_007 f2 (leg down at f8; grounded; punch list 6) | Spike / stomp; combo: ender (spike) | `xGOK_ATC_017` **rec**: owner: "flying position, downward kick; spike/meteor candidate" (row 48 Attack13). Spike. (42f; reach 7.2 L_Foot f12; high 8.6; fastest L_Hand f12)<br>`xGOK_ATC_006`: owner: "flying, two-hand clasped slam in front; fair spike candidate" (rows 60-64 AttackS4*). Alternative spike. (58f; reach 9.1 L_Hand f18; high 9.5; fastest R_Hand f18) | **xGOK_ATC_017** |
| **OK** Air landings | LandingAirN/F/B/Hi/Lw | alias of Landing | Landing lag poses (Melee lag stays) | `xGOK_BAS_JUMP_FRONT_02` **rec**: owner: "land from a jump" (row 35 Landing; rows 73-76 "landing (from aerials?)"). (31f; reach 5.5 L_Hand f24; high 8.6; fastest R_Foot f2) | **xGOK_BAS_JUMP_FRONT_02** |

## 5 Grabs and throws

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| **OK** Grab | Catch, CatchDash(Pull), CatchPull | NAG_TSUKAMI (BAC 600) | Standing / dash / pivot grab | `xGOK_NAG_TSUKAMI` **rec**: owner: "from standing, lunges forward to grab" (rows 242-245 Catch*). (52f; reach 11.0 R_Hand f14; high 6.0; fastest R_Hand f10) | **xGOK_NAG_TSUKAMI** |
| **GAP** Grab hold / pummel | CatchWait, CatchAttack, CatchCut | TSUKAMI held f22+ ; CMN_BAS_HAJIKI_B_00 | Hold, pummel, release | **look next** (undescribed): `xGOK_ATC_000`, `xGOK_ATC_001`, `xGNY_NAG_D`, `xCMN_BAS_RECEIVE`<br>note: Rows 244, 245 reuse the lunge clip; nothing described is a hold or a pummel. |  |
| **OK** Forward throw | ThrowF | GNY_NAG_A f16-45 (BAC 601) | Toss | `xGOK_ATC_SHOT_F` **rec**: owner: "firing a ki blast" (rows 79-83, 85-88 LightThrow*). Inference: a point-blank ki blast as the forward throw (owner only said it fires a ki blast). (40f; reach 10.9 R_Hand f14; high 5.0; fastest L_Hand f8)<br>**look next** (undescribed): `xGOK_ATC_SHOT_B`<br>note: xGNY_NAG_A is "unclear" (row 247): excluded. | **xGOK_ATC_SHOT_F** |
| **OK** Back throw | ThrowB | GNY_NAG_A turned 180 (authored) | Throw behind | `xCMN_DMG_BLOW_H_B` **rec**: owner: "from behind, blasting a character's back (throw candidate)" (row 263 ThrownB; 273). (36f; reach 5.7 L_Hand f0; high 3.8; fastest L_Hand f4) | **xCMN_DMG_BLOW_H_B** |
| **PARTIAL** Up throw | ThrowHi | ATC_004 uppercut (authored choice) | Throw up | `xGOK_ATC_004` **rec**: owner: "launcher; utilt/usmash candidate" (row 66 AttackHi4). Row 249 reuse; duplicates Up tilt / Up smash. (43f; reach 7.1 L_Hand f10; high 10.5; fastest R_Hand f14)<br>**look next** (undescribed): `xGOK_ATC_SHOT_B`, `xGOK_ATC_026`, `xGOK_ATC_027` | **xGOK_ATC_004** |
| **PARTIAL** Down throw | ThrowLw | ATC_012 sweep (authored choice) | Throw down | `xGOK_ATC_012` **rec**: owner: "low sweep; dtilt/dsmash candidate" (row 67 AttackLw4). Row 250 reuse; duplicates Down smash. (40f; reach 9.3 R_Hand f4; high 5.0; fastest R_Foot f10)<br>**look next** (undescribed): `xGNY_NAG_D`, `xGOK_ATC_029`<br>note: xGNY_NAG_A is "unclear": excluded. | **xGOK_ATC_012** |
| **OK** Thrown / captured by others | Thrown*, Capture*, ShoulderedWait... | CMN_DMG clips / Falcon stand-ins | Victim poses (many rows) | `xCMN_DMG_HEAD_L_F` **rec**: owner: "standing, takes damage" (row 165 DamageHi1; 251-255 Capture*). Captured/pulled and wait. (34f; reach 5.1 L_Hand f32; high 5.4; fastest L_Hand f2)<br>`xCMN_DMG_HEAD_H_F`: owner: "standing, takes harder damage (head?)" (row 166 DamageHi2; 253, 256 CaptureDamage*). Capture damage. (34f; reach 5.9 L_Foot f4; high 9.5; fastest R_Hand f2)<br>`xCMN_DMG_YOROKE_BODY_F`: owner: "slightly launched, stumbles back" (row 170 DamageN3; 210, 211 Ottotto*). Thrown, stumbling. (85f; reach 8.1 R_Hand f24; high 2.5; fastest R_Foot f2) | **xCMN_DMG_HEAD_L_F** |

## 6 Specials

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| **KEEP** Neutral B Kamehameha | SpecialN, SpecialAirN, Kame* | xGOK_SPA_KMH | Accepted design (owner) | note: Kamehameha keeps its designed animation (owner decision); no remake pick. |  |
| **KEEP** Side B Dragon Rush | SpecialS, SpecialAirS (+Rush, RushCombo) | BOOST_F_00 + STEP_F_S + ATC_013 | Dash strike and recovery; combo: route: Rush>RushCombo; XV2 BAC 426/427 use ATC_022/023 | `xCMN_BAS_UKEMI_F`: SHELVED for Side B (owner 2026-10-11). TUMBLE-EXIT candidate: XV2 hit-recovery / tumble exit; used as the forward getup / tech roll (slot 49). owner: "aerial recovery/tumble exit into a dragon dive / flying dash" (rows 188, 196, 200 DownForward*, PassiveStandF). New find: tumble exit into a dragon dive / flying dash. (61f; reach 8.3 R_Hand f10; high 4.3; fastest L_Hand f8)<br>`xGOK_BAS_BOOST_F_00`: owner: "initial dash" (row 12 Dash). Alternative: dash start. (24f; reach 5.4 L_Hand f0; high 4.3; fastest R_Foot f22)<br>**look next** (undescribed): `xGOK_ATC_021_S`, `xGOK_ATC_022`, `xGOK_ATC_023`<br>note: Owner decision (2026-10-11): Side B is the XV2 knockback attack (Heavy+Blast, BAC 419: BOOST_F_00 > STEP_F_S > ATC_013), i.e. the existing Rush row. xCMN_BAS_UKEMI_F is SHELVED for Side B: in XV2 it is a hit-recovery / tumble exit, kept here as a TUMBLE-EXIT candidate (floor getup / tech roll, slot 49) only. The homing dash strike (BOOST_F_00 > ATC_008, BAC 476) is Side B out of the shield: state Homing. |  |
| **GAP** Up B Instant Transmission | SpecialHi, SpecialAirHi | xGOK_ESC_KUR_C | Teleport recovery | **look next** (undescribed): `xGOK_ESC_KUR_C`, `xGOK_ESC_KUR_S_C`, `xCMN_BAS_GATE_IN`, `xCMN_BAS_GATE_OUT`<br>note: Nothing described fits a teleport. |  |
| **OK** Down B counter / ki charge | SpecialLw, SpecialAirLw, KiCharge | ESC_KUR_C x0.39 (tap: Z-vanish counter) / APL_SPA_KTN_C (hold: ki charge) | Counter and ki charge | `xAPL_SPA_KTN_C` **rec**: owner decision 2026-10-11 (research section 12, faithful to the XV2 data): Down B hold = ki charge on XV2 Energy Charge (skill 591, APL_SPA_KTN_C, 140 frames), usable only while ki < 100. Replaces the CMN_BAS_HIRAMEKI recommendation (that stays the Taunt pick). Floating variant for the picker: xAPL_SPA_KTN_S_C. (140f; reach 6.0 L_Hand f138; high 9.9; fastest L_Hand f20)<br>`xCMN_BAS_HIRAMEKI`: owner: "charge-up: looks great" (rows 239, 240 AppealSR/SL). Ki charge. The Counter keeps its designed animation (owner decision). (90f; reach 6.2 L_Hand f2; high 4.8; fastest L_Hand f18)<br>**look next** (undescribed): `xCMN_BLT_POW_GOK`, `xCMN_BLT_POW_C` | **xAPL_SPA_KTN_C** (not a candidate) |
| **OK** Ki volley | KiVolley (combo) | ATC_SHOT_N | Neutral-B cancel | `xGOK_ATC_SHOT_N_LOOP` **rec**: owner: "while floating, firing ki blasts from the hands (like Mega Man's in Ultimate)" (rows 150, 154, 158, 162 ItemScopeRapid*). New find: floating ki volley. (14f; reach 6.0 L_Hand f10; high 5.0; fastest L_Hand f6)<br>`xGOK_ATC_SHOT_N`: owner: "firing a ki blast" (row 84 LightThrowDrop). Single blast. (40f; reach 5.7 L_Hand f2; high 5.2; fastest R_Hand f8) | **xGOK_ATC_SHOT_N_LOOP** |

## 7 Ledge and getups

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| **GAP** Ledge catch / wait | CliffCatch, CliffWait | JUMP_BACK_00 f12 authored lean | Hang | **look next** (undescribed): `xGOK_BAS_BUKUU_UP`, `xCMN_BAS_RECOVER`, `xCMN_BAS_TAM_00`<br>note: xGOK_BAS_JUMP_BACK_00 (rows 216, 217) is "terrible jump backward": excluded. |  |
| **GAP** Ledge climb | CliffClimbSlow/Quick | JUMP crouch crop, TransN path | Get up | **look next** (undescribed): `xGOK_BAS_BUKUU_UP`, `xCMN_BAS_RECOVER`, `xCMN_BAS_TAM_01`<br>note: Row 219 reuses the crouch clip; the owner described no climb. |  |
| **PARTIAL** Ledge attack / escape / jump | CliffAttack*, CliffEscape*, CliffJump* | ATC_012 / STEP_F_S | Getup attack, roll, jump | `xGOK_ATC_012` **rec**: owner: "low sweep; dtilt/dsmash candidate" (row 67 AttackLw4). Ledge attack (rows 221, 222). (40f; reach 9.3 R_Hand f4; high 5.0; fastest R_Foot f10)<br>`xGOK_BAS_STEP_F_S`: owner: "dodge/dash forward, keeps facing" (row 42 EscapeF). Ledge escape (rows 223, 224). (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4)<br>**look next** (undescribed): `xGOK_BAS_BUKUU_UP`, `xGOK_BAS_BOOST_F_01`<br>note: Ledge jump: GAP (xGOK_BAS_JUMP_FRONT_00 is "terrible"). | **xGOK_ATC_012** |
| **OK** Floor getups | DownBound*, DownWait*, DownStand*, DownAttack*, DownForward/Back/Spot*, Passive* | CMN_BAS_DOWN_*_S, UKEMI | Knockdown and tech | `xCMN_BAS_DOWN_STAND_AOMUKE` **rec**: owner: "get-up" (row 186 DownStandU). Stand up from face up. (40f; reach 7.8 R_Foot f0; high 2.1; fastest R_Hand f26)<br>`xCMN_BAS_DOWN_STAND_UTSUBUSE`: owner: "get-up from a knockdown/missed tech" (row 194 DownStandD). Stand up from face down. (40f; reach 8.4 R_Hand f0; high 3.1; fastest L_Foot f14)<br>`xCMN_BAS_UKEMI_N`: owner: "one-arm push-up into a landing in fighting stance" (row 199 Passive). New find: push-up getup (tech in place). (36f; reach 5.9 L_Hand f28; high 6.4; fastest R_Foot f10)<br>`xCMN_BAS_UKEMI_F`: owner: "aerial recovery/tumble exit into a dragon dive / flying dash" (rows 188, 196, 200 DownForward*, PassiveStandF). New find: forward roll as tumble exit. (61f; reach 8.3 R_Hand f10; high 4.3; fastest L_Hand f8)<br>`xCMN_BAS_UKEMI_B`: owner: "handspring/cartwheel" (rows 189, 197, 201 DownBack*, PassiveStandB). Back roll. (80f; reach 8.7 R_Hand f14; high 8.2; fastest R_Hand f18)<br>`xCMN_DMG_DOWN_BOUND_UTSUBUSE`: owner: "lying face down (techable?)" (row 191 DownBoundD). Bounce onto the face. (59f; reach 9.5 L_Hand f2; high 5.1; fastest L_Hand f8)<br>note: Wait/damage/spot-dodge rows (xCMN_BAS_DOWN_AOMUKE_S, xCMN_DMG_DOWN_BOUND_*_H) are "unclear": excluded. | **xCMN_BAS_DOWN_STAND_AOMUKE** |

## 8 Damage

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| **OK** Hit stun (hi / mid / low, ground+air) | DamageHi1-3, N1-3, Lw1-3, Air1-3 | CMN_DMG_HEAD/BODY/LEG_L_F, AIR_F | Flinch | `xCMN_DMG_BODY_L_F` **rec**: owner: "standing, takes damage (stomach)" (row 168 DamageN1). (34f; reach 6.8 L_Hand f4; high 2.4; fastest R_Hand f2)<br>`xCMN_DMG_BODY_H_F`: owner: "standing, takes harder damage (stomach)" (row 169 DamageN2). Harder. (34f; reach 7.3 L_Hand f4; high 2.4; fastest L_Hand f4)<br>`xCMN_DMG_HEAD_L_F`: owner: "standing, takes damage" (row 165 DamageHi1; 251-255 Capture*). (34f; reach 5.1 L_Hand f32; high 5.4; fastest L_Hand f2)<br>`xCMN_DMG_HEAD_H_F`: owner: "standing, takes harder damage (head?)" (row 166 DamageHi2; 253, 256 CaptureDamage*). Harder. (34f; reach 5.9 L_Foot f4; high 9.5; fastest R_Hand f2)<br>`xCMN_DMG_YOROKE_HEAD_F`: owner: "standing, takes even harder damage (head?)" (row 167 DamageHi3). Hardest. (43f; reach 5.3 L_Hand f28; high 6.7; fastest L_Hand f4)<br>`xCMN_DMG_AIR_F`: owner: "hit back while in the air (?)" (row 174 DamageAir1). Air. (30f; reach 7.8 R_Foot f0; high 6.2; fastest R_Hand f6)<br>`xCMN_DMG_AIR_F_L`: owner: "hit back in the air, different pose" (row 175 DamageAir2). Air. (28f; reach 4.9 R_Foot f12; high 4.0; fastest L_Foot f6)<br>note: Low hits (xCMN_DMG_LEG_*) are "unclear": excluded. | **xCMN_DMG_BODY_L_F** |
| **OK** Fly / tumble | DamageFly*, DamageFall, DeadUp* | CMN_DMG_BLOW/UP/DIVE/TUMBLE | Launched states | `xCMN_DMG_TUMBLE_F` **rec**: owner: "launched: rapid 360 spin along head-to-toe axis (tumble candidate)" (row 29 DamageFall). (69f; reach 8.1 L_Hand f68; high 5.4; fastest R_Foot f40)<br>`xCMN_DMG_AIR_SPIN_L`: owner: "head down, feet up: falling/tumbling" (row 176 DamageAir3). (30f; reach 7.9 R_Foot f18; high 7.3; fastest L_Hand f6)<br>`xCMN_DMG_UP_F`: owner: "knocked down onto his back" (row 177 DamageFlyHi; 264, 274, 286). (49f; reach 7.7 L_Foot f16; high 7.6; fastest L_Hand f6)<br>`xCMN_DMG_BLOW_H_F`: owner: "flying backwards after a hit to the stomach" (row 0 DeadUpFallHitCamera; 1 "identical to 0"). Also the KO fly-off (DeadUp*). (36f; reach 8.1 L_Foot f8; high 3.5; fastest R_Foot f4)<br>`xCMN_DMG_UP_BODY_F`: owner: "launched up, about to transition into 14" (row 180 DamageFlyTop). (69f; reach 7.7 R_Foot f34; high 7.6; fastest L_Hand f28)<br>note: xCMN_DMG_BLOW_SPIN ("similar to 15") and xCMN_DMG_DIVE_F ("maybe same as 14") are ambiguous: excluded. | **xCMN_DMG_TUMBLE_F** |
| **PARTIAL** Wall / ceiling / ottotto | StopWall, StopCeil, Ottotto* | CMN_DMG_WALL_BOUND, YOROKE | Impacts and edge wobble | `xCMN_DMG_YOROKE_BODY_F` **rec**: owner: "slightly launched, stumbles back" (row 170 DamageN3; 210, 211 Ottotto*). Ottotto only. (85f; reach 8.1 R_Hand f24; high 2.5; fastest R_Foot f2)<br>**look next** (undescribed): `xCMN_DMG_WALL_DOWN_AOMUKE`, `xCMN_DMG_WALL_DOWN_UTSUBUSE`, `xCMN_DMG_DOKKAN_LOOP_F`, `xCMN_DMG_KANTSU_F`<br>note: Wall and ceiling: GAP. xCMN_DMG_WALL_BOUND_F/B and xCMN_BAS_UKEMI_U are "unclear": excluded. | **xCMN_DMG_YOROKE_BODY_F** |

## 9 Showpieces

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| **OK** Taunt | AppealSL, AppealSR (both) | CMN lobby gesture (118) | Taunt | `xCMN_BAS_HIRAMEKI` **rec**: owner: "charge-up: looks great" (rows 239, 240 AppealSR/SL). (90f; reach 6.2 L_Hand f2; high 4.8; fastest L_Hand f18) | **xCMN_BAS_HIRAMEKI** |
| **GAP** Entry | Entry, EntryStart, EntryEnd | GOK_DEM_START 210f | Spawn-in | **look next** (undescribed): `xCMN_BAS_GATE_IN`, `xCMN_BAS_GATE_OUT`, `xCMN_DEM_RISAN`, `xGOK_ULT_CKM_C`, `xGOK_BAS_STAND_SS3`<br>note: xGOK_DEM_START is "idle/guard, unclear" (row 238): excluded. |  |
| **GAP** Victory / results pose | (results screen, not a fighter row) | n/a | Win poses are outside the 351 rows; chosen with the results-screen pass | `xCMN_BAS_HIRAMEKI` **rec**: owner: "charge-up: looks great" (rows 239, 240 AppealSR/SL). Stopgap only: the owner says "looks great" but it is also the Taunt pick. (90f; reach 6.2 L_Hand f2; high 4.8; fastest L_Hand f18)<br>**look next** (undescribed): `xGOK_BAS_STAND_SS3`, `xGOK_BAS_STAND_SS3_S`, `xCMN_BAS_KYORYOKU_C`, `xCMN_BAS_KYORYOKU_F`, `xGOK_ULT_CKM_C` |  |

## 10 New finds (owner)

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| **OK** Rebound / parry | Rebound, GuardReflect, GuardSetOff | xCMN_BAS_HAJIKI_F_00 (Rebound row 45) | Deflecting a projectile | `xCMN_BAS_HAJIKI_F_00` **rec**: owner: "flying position, parries/deflects (projectile)" (row 45 Rebound). (38f; reach 9.3 R_Hand f14; high 8.1; fastest R_Hand f16) | **xCMN_BAS_HAJIKI_F_00** |
| **OK** Miss foot / stamina-out | MissFoot | xCMN_DMG_KUZURE (row 215) | Lying exhausted | `xCMN_DMG_KUZURE` **rec**: owner: "lying down exhausted (stamina-out candidate)" (row 215 MissFoot). (78f; reach 8.4 R_Hand f76; high 2.6; fastest R_Hand f60) | **xCMN_DMG_KUZURE** |

## GAP and partial slots (nothing good described yet)

| slot | status | look next (undescribed library clips) | why |
|---|---|---|---|
| 5 Run brake / stop | GAP | `xCMN_BAS_BRAKE_S`, `xCMN_BAS_BRAKE_B_S`, `xGOK_BAS_BUKUU_B_S` | The only clip used (xGOK_BAS_BOOST_F_02) was described as "meant to be runbrake/skid stop, but looks wrong" (row 14): excluded. |
| 9 Jump (ground, forward/back) | GAP | `xGOK_BAS_BUKUU_UP`, `xGOK_BAS_JUMP_BACK_02`, `xGOK_BAS_BOOST_F_01` | xGOK_BAS_JUMP_FRONT_00 and xGOK_BAS_JUMP_BACK_00 are "terrible jump forward/backward" (rows 16, 17): excluded. |
| 15 Roll / spot dodge / air dodge | PARTIAL | `xGOK_BAS_STEP_R_S`, `xGOK_GRD_L_L_S`, `xGOK_GRD_L_R_S` | Spot dodge and air dodge: GAP. xGOK_BAS_STEP_L_S is "unclear: tiptoeing sideways" (rows 41, 44): excluded. |
| 16 Dizzy | GAP | `xGOK_BAS_STUN_00`, `xGOK_BAS_STUN_01`, `xGOK_BAS_STUN_02`, `xCMN_BAS_STUN_01_S`, `xCMN_BAS_STUN_02_S` | No dizzy clip was described. |
| 18 Jab 2 (L2) | GAP | `xGOK_ATC_000`, `xGOK_ATC_001`, `xGOK_ATC_009`, `xGOK_ATC_010` | No described clip is a second jab. |
| 19 Jab 3 (L3) | GAP | `xGOK_ATC_009`, `xGOK_ATC_014`, `xGOK_ATC_015`, `xGOK_ATC_016` | The only described kick, xGOK_ATC_017, is a spike candidate (Down air). |
| 24 Dash attack | WEAK | `xGOK_ATC_024`, `xGOK_ATC_021_S`, `xGOK_BAS_BOOST_F_01` |  |
| 26 Up smash | PARTIAL | `xGOK_ATC_026`, `xGOK_ATC_027`, `xGOK_ATC_029`, `xGOK_ATC_005` |  |
| 30 Back air | GAP | `xGOK_ATC_014`, `xGOK_ATC_015`, `xGOK_ATC_016`, `xGOK_ATC_018_S`, `xGOK_ATC_019_S` | Row 70 is Luigi's back air ("Luigi back air?"): not an XV2 move. |
| 35 Grab hold / pummel | GAP | `xGOK_ATC_000`, `xGOK_ATC_001`, `xGNY_NAG_D`, `xCMN_BAS_RECEIVE` | Rows 244, 245 reuse the lunge clip; nothing described is a hold or a pummel. |
| 38 Up throw | PARTIAL | `xGOK_ATC_SHOT_B`, `xGOK_ATC_026`, `xGOK_ATC_027` |  |
| 39 Down throw | PARTIAL | `xGNY_NAG_D`, `xGOK_ATC_029` | xGNY_NAG_A is "unclear": excluded. |
| 43 Up B Instant Transmission | GAP | `xGOK_ESC_KUR_C`, `xGOK_ESC_KUR_S_C`, `xCMN_BAS_GATE_IN`, `xCMN_BAS_GATE_OUT` | Nothing described fits a teleport. |
| 46 Ledge catch / wait | GAP | `xGOK_BAS_BUKUU_UP`, `xCMN_BAS_RECOVER`, `xCMN_BAS_TAM_00` | xGOK_BAS_JUMP_BACK_00 (rows 216, 217) is "terrible jump backward": excluded. |
| 47 Ledge climb | GAP | `xGOK_BAS_BUKUU_UP`, `xCMN_BAS_RECOVER`, `xCMN_BAS_TAM_01` | Row 219 reuses the crouch clip; the owner described no climb. |
| 48 Ledge attack / escape / jump | PARTIAL | `xGOK_BAS_BUKUU_UP`, `xGOK_BAS_BOOST_F_01` | Ledge jump: GAP (xGOK_BAS_JUMP_FRONT_00 is "terrible"). |
| 52 Wall / ceiling / ottotto | PARTIAL | `xCMN_DMG_WALL_DOWN_AOMUKE`, `xCMN_DMG_WALL_DOWN_UTSUBUSE`, `xCMN_DMG_DOKKAN_LOOP_F`, `xCMN_DMG_KANTSU_F` | Wall and ceiling: GAP. xCMN_DMG_WALL_BOUND_F/B and xCMN_BAS_UKEMI_U are "unclear": excluded. |
| 54 Entry | GAP | `xCMN_BAS_GATE_IN`, `xCMN_BAS_GATE_OUT`, `xCMN_DEM_RISAN`, `xGOK_ULT_CKM_C`, `xGOK_BAS_STAND_SS3` | xGOK_DEM_START is "idle/guard, unclear" (row 238): excluded. |
| 55 Victory / results pose | GAP | `xGOK_BAS_STAND_SS3`, `xGOK_BAS_STAND_SS3_S`, `xCMN_BAS_KYORYOKU_C`, `xCMN_BAS_KYORYOKU_F`, `xGOK_ULT_CKM_C` |  |

## Excluded: the owner called these unclear, terrible or wrong (second look wanted)

| clip | owner | where |
|---|---|---|
| `xGOK_BAS_BOOST_F_02` | meant to be runbrake/skid stop, but looks wrong | row 14 RunBrake |
| `xGOK_BAS_JUMP_FRONT_00` | terrible jump forward | row 16 JumpF |
| `xGOK_BAS_JUMP_BACK_00` | terrible jump backward | row 17 JumpB |
| `xGOK_BAS_STEP_L_S` | unclear: tiptoeing sideways | row 41 EscapeN, row 44 EscapeAir |
| `xGOK_BAS_STAND` | Luigi back air? | row 70 AttackAirB |
| `xCMN_BAS_ITM` | similar to 77 | row 78 LightGet |
| `xCMN_DMG_LEG_L_F` | unclear | row 171 DamageLw1 |
| `xCMN_DMG_LEG_H_F` | unclear | row 172 DamageLw2 |
| `xCMN_DMG_YOROKE_LEG_F` | unclear | row 173 DamageLw3 |
| `xCMN_DMG_DIVE_F` | maybe same as 14 | row 179 DamageFlyLw |
| `xCMN_DMG_BLOW_SPIN` | similar to 15 | row 181 DamageFlyRoll |
| `xCMN_DMG_DOWN_BOUND_AOMUKE` | unclear | row 183 DownBoundU, row 265 ThrownLw, row 266 ThrownlwWomen, row 275 ThrownFLw, row 288 ShieldBreakDownU |
| `xCMN_BAS_DOWN_AOMUKE_S` | unclear | row 184 DownWaitU |
| `xCMN_DMG_DOWN_BOUND_AOMUKE_H` | unclear | row 185 DownDamageU, row 190 DownSpotU |
| `xCMN_BAS_DOWN_UTSUBUSE_S` | unclear | row 192 DownWaitD |
| `xCMN_DMG_DOWN_BOUND_UTSUBUSE_H` | unclear | row 193 DownDamageD, row 198 DownSpotD |
| `xCMN_DMG_WALL_BOUND_F` | unclear | row 202 PassiveWall, row 213 StopWall |
| `xCMN_BAS_UKEMI_U` | unclear | row 204 PassiveCeil |
| `xCMN_DMG_WALL_BOUND_B` | unclear | row 214 StopCeil |
| `xGOK_DEM_START` | idle/guard, unclear | row 238 EntryStart |
| `xCMN_BAS_HAJIKI_B_00` | unclear | row 246 CatchCut, row 257 CaptureCut |
| `xGNY_NAG_A` | unclear | row 247 ThrowF, row 248 ThrowB, row 259 CaptureNeck, row 260 CaptureFoot, row 267 ShoulderedWait, row 268 ShoulderedWalkSlow, row 269 Should |

## Appendix: every Melee row and its current source clip (no row is silent)

`decision` is filled by the owner: keep / pick (sheet slot above) / n/a. Rows of items, mounts and other fighters are carried as they are.

| motion | row | status | current clip | decision |
|---|---|---|---|---|
| 0 | DeadDown | NONE | - |  |
| 1 | DeadLeft | NONE | - |  |
| 2 | DeadRight | NONE | - |  |
| 3 | DeadUp | NONE | - |  |
| 4 | DeadUpStar | SOURCE-RETIMED | 60 frames |  |
| 5 | DeadUpStarIce | NONE | - |  |
| 6 | DeadUpFall | SOURCE-RETIMED | 69 frames |  |
| 7 | DeadUpFallHitCamera | SOURCE-RETIMED | 36 frames |  |
| 8 | DeadUpFallHitCameraFlat | SOURCE-RETIMED | 36 frames |  |
| 9 | DeadUpFallIce | NONE | - |  |
| 10 | DeadUpFallHitCameraIce | NONE | - |  |
| 11 | Sleep | SOURCE-RETIMED | 100 frames |  |
| 12 | Rebirth | SOURCE-RETIMED | 100 frames |  |
| 13 | RebirthWait | SOURCE-RETIMED | 100 frames |  |
| 14 | Wait | SOURCE-RETIMED | 100 frames |  |
| 15 | WalkSlow | SOURCE-RETIMED | 70 frames |  |
| 16 | WalkMiddle | SOURCE-RETIMED | 70 frames |  |
| 17 | WalkFast | SOURCE-RETIMED | 70 frames |  |
| 18 | Turn | AUTHORED | authored: Wait pose, 180-degree yaw ramp |  |
| 19 | TurnRun | AUTHORED | authored: boost-stop skid crop + 180-degree yaw, eased into Run |  |
| 20 | Dash | SOURCE-RETIMED | x0.55 speed, 14 frames |  |
| 21 | Run | SOURCE-RETIMED | 30 frames |  |
| 22 | RunDirect | SOURCE-RETIMED | 30 frames |  |
| 23 | RunBrake | SOURCE-RETIMED | from f6, x0.75 speed, 16 frames |  |
| 24 | KneeBend | SOURCE-RETIMED | 8 frames |  |
| 25 | JumpF | SOURCE-RETIMED | x0.5 speed, 36 frames |  |
| 26 | JumpB | SOURCE-RETIMED | x0.5 speed, 36 frames |  |
| 27 | JumpAerialF | SOURCE-RETIMED | x1 speed, 16 frames |  |
| 28 | JumpAerialB | SOURCE-RETIMED | x1 speed, 16 frames |  |
| 29 | Fall | SOURCE-RETIMED | 50 frames |  |
| 30 | FallF | SOURCE-RETIMED | 50 frames |  |
| 31 | FallB | SOURCE-RETIMED | 50 frames |  |
| 32 | FallAerial | SOURCE-RETIMED | 50 frames |  |
| 33 | FallAerialF | SOURCE-RETIMED | 50 frames |  |
| 34 | FallAerialB | SOURCE-RETIMED | 50 frames |  |
| 35 | FallSpecial | SOURCE-RETIMED | 50 frames |  |
| 36 | FallSpecialF | SOURCE-RETIMED | 50 frames |  |
| 37 | FallSpecialB | SOURCE-RETIMED | 50 frames |  |
| 38 | DamageFall | SOURCE-RETIMED | 69 frames |  |
| 39 | Squat | SOURCE-RETIMED | from f50, 7 frames |  |
| 40 | SquatWait | AUTHORED | authored hold of the crouch (GOK_BAS_JUMP f56) |  |
| 41 | SquatRv | SOURCE-RETIMED | from f56, 10 frames |  |
| 42 | Landing | SOURCE-RETIMED | from f10, 20 frames |  |
| 43 | LandingFallSpecial | SOURCE-RETIMED | from f10, 20 frames |  |
| 44 | Attack11 | SOURCE-RETIMED | from f9, 24 frames |  |
| 45 | Attack12 | SOURCE-RETIMED | from f1, 26 frames |  |
| 46 | Attack13 | SOURCE-RETIMED | from f6, 34 frames |  |
| 47 | Attack100Start | SOURCE-RETIMED | 51 frames |  |
| 48 | Attack100Loop | SOURCE-RETIMED | 51 frames |  |
| 49 | Attack100End | SOURCE-RETIMED | 51 frames |  |
| 50 | AttackDash | SOURCE-RETIMED | from f13, 38 frames |  |
| 51 | AttackS3Hi | SOURCE-RETIMED | 41 frames |  |
| 52 | AttackS3HiS | SOURCE-RETIMED | 41 frames |  |
| 53 | AttackS3S | SOURCE-RETIMED | 41 frames |  |
| 54 | AttackS3LwS | SOURCE-RETIMED | 41 frames |  |
| 55 | AttackS3Lw | SOURCE-RETIMED | 41 frames |  |
| 56 | AttackHi3 | SOURCE-RETIMED | x1.5 speed, 30 frames |  |
| 57 | AttackLw3 | SOURCE-RETIMED | from f11, 26 frames |  |
| 58 | AttackS4Hi | SOURCE-RETIMED | 49 frames |  |
| 59 | AttackS4HiS | SOURCE-RETIMED | 49 frames |  |
| 60 | AttackS4S | SOURCE-RETIMED | 49 frames |  |
| 61 | AttackS4LwS | SOURCE-RETIMED | 49 frames |  |
| 62 | AttackS4Lw | SOURCE-RETIMED | 49 frames |  |
| 63 | AttackHi4 | SOURCE-RETIMED | from f5, 44 frames |  |
| 64 | AttackLw4 | SOURCE-RETIMED | from f2, 42 frames |  |
| 65 | AttackAirN | SOURCE-RETIMED | 65 frames |  |
| 66 | AttackAirF | SOURCE-RETIMED | 58 frames |  |
| 67 | AttackAirB | CROSS-PORT | Melee Luigi AttackAirB, 30 frames, size ratio 1.722 |  |
| 68 | AttackAirHi | SOURCE-RETIMED | from f7, 34 frames |  |
| 69 | AttackAirLw | SOURCE-RETIMED | 42 frames |  |
| 70 | LandingAirN | SOURCE-RETIMED | from f10, 20 frames |  |
| 71 | LandingAirF | SOURCE-RETIMED | from f10, 20 frames |  |
| 72 | LandingAirB | SOURCE-RETIMED | from f10, 20 frames |  |
| 73 | LandingAirHi | SOURCE-RETIMED | from f10, 20 frames |  |
| 74 | LandingAirLw | SOURCE-RETIMED | from f10, 20 frames |  |
| 75 | DamageHi1 | SOURCE-RETIMED | 20 frames |  |
| 76 | DamageHi2 | SOURCE-RETIMED | 26 frames |  |
| 77 | DamageHi3 | SOURCE-RETIMED | 34 frames |  |
| 78 | DamageN1 | SOURCE-RETIMED | 20 frames |  |
| 79 | DamageN2 | SOURCE-RETIMED | 26 frames |  |
| 80 | DamageN3 | SOURCE-RETIMED | x1.4 speed, 40 frames |  |
| 81 | DamageLw1 | SOURCE-RETIMED | 20 frames |  |
| 82 | DamageLw2 | SOURCE-RETIMED | 26 frames |  |
| 83 | DamageLw3 | SOURCE-RETIMED | 34 frames |  |
| 84 | DamageAir1 | SOURCE-RETIMED | 20 frames |  |
| 85 | DamageAir2 | SOURCE-RETIMED | 24 frames |  |
| 86 | DamageAir3 | SOURCE-RETIMED | 30 frames |  |
| 87 | DamageFlyHi | SOURCE-RETIMED | 40 frames |  |
| 88 | DamageFlyN | SOURCE-RETIMED | 36 frames |  |
| 89 | DamageFlyLw | SOURCE-RETIMED | 31 frames |  |
| 90 | DamageFlyTop | SOURCE-RETIMED | 40 frames |  |
| 91 | DamageFlyRoll | SOURCE-RETIMED | 60 frames |  |
| 92 | LightGet | SOURCE-RETIMED | x2.5 speed, 8 frames |  |
| 93 | HeavyGet | SOURCE-RETIMED | 30 frames |  |
| 94 | LightThrowF | SOURCE-RETIMED | 30 frames |  |
| 95 | LightThrowB | SOURCE-RETIMED | 30 frames |  |
| 96 | LightThrowHi | SOURCE-RETIMED | 30 frames |  |
| 97 | LightThrowLw | SOURCE-RETIMED | 30 frames |  |
| 98 | LightThrowDash | SOURCE-RETIMED | 30 frames |  |
| 99 | LightThrowDrop | SOURCE-RETIMED | 20 frames |  |
| 100 | LightThrowAirF | SOURCE-RETIMED | 30 frames |  |
| 101 | LightThrowAirB | SOURCE-RETIMED | 30 frames |  |
| 102 | LightThrowAirHi | SOURCE-RETIMED | 30 frames |  |
| 103 | LightThrowAirLw | SOURCE-RETIMED | 30 frames |  |
| 104 | HeavyThrowF | SOURCE-RETIMED | 30 frames |  |
| 105 | HeavyThrowB | SOURCE-RETIMED | 30 frames |  |
| 106 | HeavyThrowHi | SOURCE-RETIMED | 30 frames |  |
| 107 | HeavyThrowLw | SOURCE-RETIMED | 30 frames |  |
| 108 | LightThrowF4 | SOURCE-RETIMED | 30 frames |  |
| 109 | LightThrowB4 | SOURCE-RETIMED | 30 frames |  |
| 110 | LightThrowHi4 | SOURCE-RETIMED | 30 frames |  |
| 111 | LightThrowLw4 | SOURCE-RETIMED | 30 frames |  |
| 112 | LightThrowAirF4 | SOURCE-RETIMED | 30 frames |  |
| 113 | LightThrowAirB4 | SOURCE-RETIMED | 30 frames |  |
| 114 | LightThrowAirHi4 | SOURCE-RETIMED | 30 frames |  |
| 115 | LightThrowAirLw4 | SOURCE-RETIMED | 30 frames |  |
| 116 | HeavyThrowF4 | SOURCE-RETIMED | 30 frames |  |
| 117 | HeavyThrowB4 | SOURCE-RETIMED | 30 frames |  |
| 118 | HeavyThrowHi4 | SOURCE-RETIMED | 30 frames |  |
| 119 | HeavyThrowLw4 | SOURCE-RETIMED | 30 frames |  |
| 120 | SwordSwing1 | SOURCE-RETIMED | 28 frames |  |
| 121 | SwordSwing3 | SOURCE-RETIMED | from f4, 28 frames |  |
| 122 | SwordSwing4 | SOURCE-RETIMED | from f5, 45 frames |  |
| 123 | SwordSwingDash | SOURCE-RETIMED | from f13, 36 frames |  |
| 124 | BatSwing1 | SOURCE-RETIMED | 28 frames |  |
| 125 | BatSwing3 | SOURCE-RETIMED | from f4, 28 frames |  |
| 126 | BatSwing4 | SOURCE-RETIMED | from f5, 45 frames |  |
| 127 | BatSwingDash | SOURCE-RETIMED | from f13, 36 frames |  |
| 128 | ParasolSwing1 | SOURCE-RETIMED | 28 frames |  |
| 129 | ParasolSwing3 | SOURCE-RETIMED | from f4, 28 frames |  |
| 130 | ParasolSwing4 | SOURCE-RETIMED | from f5, 45 frames |  |
| 131 | ParasolSwingDash | SOURCE-RETIMED | from f13, 36 frames |  |
| 132 | HarisenSwing1 | SOURCE-RETIMED | 28 frames |  |
| 133 | HarisenSwing3 | SOURCE-RETIMED | from f4, 28 frames |  |
| 134 | HarisenSwing4 | SOURCE-RETIMED | from f5, 45 frames |  |
| 135 | HarisenSwingDash | SOURCE-RETIMED | from f13, 36 frames |  |
| 136 | StarRodSwing1 | SOURCE-RETIMED | 28 frames |  |
| 137 | StarRodSwing3 | SOURCE-RETIMED | from f4, 28 frames |  |
| 138 | StarRodSwing4 | SOURCE-RETIMED | from f5, 45 frames |  |
| 139 | StarRodSwingDash | SOURCE-RETIMED | from f13, 36 frames |  |
| 140 | LipstickSwing1 | SOURCE-RETIMED | 28 frames |  |
| 141 | LipstickSwing3 | SOURCE-RETIMED | from f4, 28 frames |  |
| 142 | LipstickSwing4 | SOURCE-RETIMED | from f5, 45 frames |  |
| 143 | LipstickSwingDash | SOURCE-RETIMED | from f13, 36 frames |  |
| 144 | ItemParasolOpen | SOURCE-RETIMED | 20 frames |  |
| 145 | ItemParasolFall | SOURCE-RETIMED | 50 frames |  |
| 146 | ItemParasolFallSpecial | SOURCE-RETIMED | 50 frames |  |
| 147 | ItemParasolDamageFall | SOURCE-RETIMED | 69 frames |  |
| 148 | LGunShoot | SOURCE-RETIMED | 30 frames |  |
| 149 | LGunShootAir | SOURCE-RETIMED | 30 frames |  |
| 150 | LGunShootEmpty | SOURCE-RETIMED | 30 frames |  |
| 151 | LGunShootAirEmpty | SOURCE-RETIMED | 30 frames |  |
| 152 | FireFlowerShoot | SOURCE-RETIMED | 30 frames |  |
| 153 | FireFlowerShootAir | SOURCE-RETIMED | 30 frames |  |
| 154 | ItemScrew | SOURCE-RETIMED | 30 frames |  |
| 155 | ItemScrewAir | SOURCE-RETIMED | 30 frames |  |
| 156 | DamageScrew | SOURCE-RETIMED | 40 frames |  |
| 157 | DamageScrewAir | SOURCE-RETIMED | 40 frames |  |
| 158 | ItemScopeStart | SOURCE-RETIMED | 15 frames |  |
| 159 | ItemScopeRapid | SOURCE-RETIMED | 7 frames |  |
| 160 | ItemScopeFire | SOURCE-RETIMED | 30 frames |  |
| 161 | ItemScopeEnd | SOURCE-RETIMED | 15 frames |  |
| 162 | ItemScopeAirStart | SOURCE-RETIMED | 15 frames |  |
| 163 | ItemScopeAirRapid | SOURCE-RETIMED | 7 frames |  |
| 164 | ItemScopeAirFire | SOURCE-RETIMED | 30 frames |  |
| 165 | ItemScopeAirEnd | SOURCE-RETIMED | 15 frames |  |
| 166 | ItemScopeStartEmpty | SOURCE-RETIMED | 15 frames |  |
| 167 | ItemScopeRapidEmpty | SOURCE-RETIMED | 7 frames |  |
| 168 | ItemScopeFireEmpty | SOURCE-RETIMED | 30 frames |  |
| 169 | ItemScopeEndEmpty | SOURCE-RETIMED | 15 frames |  |
| 170 | ItemScopeAirStartEmpty | SOURCE-RETIMED | 15 frames |  |
| 171 | ItemScopeAirRapidEmpty | SOURCE-RETIMED | 7 frames |  |
| 172 | ItemScopeAirFireEmpty | SOURCE-RETIMED | 30 frames |  |
| 173 | ItemScopeAirEndEmpty | SOURCE-RETIMED | 15 frames |  |
| 174 | LiftWait | SOURCE-RETIMED | 60 frames |  |
| 175 | LiftWalk1 | SOURCE-RETIMED | 70 frames |  |
| 176 | LiftWalk2 | SOURCE-RETIMED | 70 frames |  |
| 177 | LiftTurn | SOURCE-RETIMED | held at f0, 12 frames |  |
| 178 | GuardOn | SOURCE-RETIMED | 8 frames |  |
| 179 | Guard | SOURCE-RETIMED | 130 frames |  |
| 180 | GuardOff | SOURCE-RETIMED | x1.8 speed, 16 frames |  |
| 181 | GuardSetOff | SOURCE-RETIMED | 16 frames |  |
| 182 | GuardReflect | SOURCE-RETIMED | 8 frames |  |
| 183 | DownBoundU | SOURCE-RETIMED | x2.2 speed, 26 frames |  |
| 184 | DownWaitU | SOURCE-RETIMED | 60 frames |  |
| 185 | DownDamageU | SOURCE-RETIMED | x2.5 speed, 20 frames |  |
| 186 | DownStandU | SOURCE-RETIMED | x1.3 speed, 30 frames |  |
| 187 | DownAttackU | AUTHORED | AUTHORED: XV2 has no getup attack; the low split sweep from the ground |  |
| 188 | DownFowardU | SOURCE-RETIMED | x1.7 speed, 35 frames |  |
| 189 | DownBackU | SOURCE-RETIMED | x2.2 speed, 35 frames |  |
| 190 | DownSpotU | SOURCE-RETIMED | x2.5 speed, 20 frames |  |
| 191 | DownBoundD | SOURCE-RETIMED | x2.2 speed, 26 frames |  |
| 192 | DownWaitD | SOURCE-RETIMED | 60 frames |  |
| 193 | DownDamageD | SOURCE-RETIMED | x2.5 speed, 20 frames |  |
| 194 | DownStandD | SOURCE-RETIMED | x1.3 speed, 30 frames |  |
| 195 | DownAttackD | AUTHORED | AUTHORED: XV2 has no getup attack; the low split sweep from the ground |  |
| 196 | DownFowardD | SOURCE-RETIMED | x1.7 speed, 35 frames |  |
| 197 | DownBackD | SOURCE-RETIMED | x2.2 speed, 35 frames |  |
| 198 | DownSpotD | SOURCE-RETIMED | x2.5 speed, 20 frames |  |
| 199 | Passive | SOURCE-RETIMED | x1.4 speed, 26 frames |  |
| 200 | PassiveStandF | SOURCE-RETIMED | x1.5 speed, 40 frames |  |
| 201 | PassiveStandB | SOURCE-RETIMED | x2 speed, 40 frames |  |
| 202 | PassiveWall | SOURCE-RETIMED | x2.3 speed, 20 frames |  |
| 203 | PassiveWallJump | SOURCE-RETIMED | x0.47 speed, 40 frames |  |
| 204 | PassiveCeil | SOURCE-RETIMED | x1.5 speed, 30 frames |  |
| 205 | ShieldBreakFly | SOURCE-RETIMED | 40 frames |  |
| 206 | ShieldBreakFall | SOURCE-RETIMED | 69 frames |  |
| 207 | ShieldBreakDownU | SOURCE-RETIMED | x2.2 speed, 26 frames |  |
| 208 | ShieldBreakDownD | SOURCE-RETIMED | x2.2 speed, 26 frames |  |
| 209 | ShieldBreakStandU | SOURCE-RETIMED | x1.3 speed, 30 frames |  |
| 210 | ShieldBreakStandD | SOURCE-RETIMED | x1.3 speed, 30 frames |  |
| 211 | Furafura | SOURCE-RETIMED | 73 frames |  |
| 212 | Catch | SOURCE-RETIMED | 32 frames |  |
| 213 | CatchPull | SOURCE-RETIMED | from f8, 4 frames |  |
| 214 | CatchDash | AUTHORED | explicit prototype reuse of Catch; directional pose authored-needed |  |
| 215 | CatchDashPull | AUTHORED | explicit prototype reuse of Catch; directional pose authored-needed |  |
| 216 | CatchWait | AUTHORED | authored hold from source catch pose |  |
| 217 | CatchAttack | SOURCE-RETIMED | from f22, 24 frames |  |
| 218 | CatchCut | SOURCE-RETIMED | 30 frames |  |
| 219 | ThrowF | SOURCE-RETIMED | 40 frames |  |
| 220 | ThrowB | SOURCE-RETIMED | 36 frames |  |
| 221 | ThrowHi | AUTHORED | AUTHORED choice: XV2 has one throw; the uppercut launches up |  |
| 222 | ThrowLw | AUTHORED | AUTHORED choice: XV2 has one throw; the low split sweep slams down |  |
| 223 | CapturePulledHi | SOURCE-RETIMED | x0.35 speed, 20 frames |  |
| 224 | CaptureWaitHi | SOURCE-RETIMED | held at f6, 30 frames |  |
| 225 | CaptureDamageHi | SOURCE-RETIMED | x1.5 speed, 14 frames |  |
| 226 | CapturePulledLw | SOURCE-RETIMED | x0.35 speed, 20 frames |  |
| 227 | CaptureWaitLw | SOURCE-RETIMED | held at f6, 30 frames |  |
| 228 | CaptureDamageLw | SOURCE-RETIMED | x1.5 speed, 14 frames |  |
| 229 | CaptureCut | SOURCE-RETIMED | 30 frames |  |
| 230 | CaptureJump | SOURCE-RETIMED | x0.38 speed, 50 frames |  |
| 231 | CaptureNeck | SOURCE-RETIMED | held at f8, 30 frames |  |
| 232 | CaptureFoot | SOURCE-RETIMED | held at f8, 30 frames |  |
| 233 | EscapeF | SOURCE-RETIMED | 45 frames |  |
| 234 | EscapeB | SOURCE-RETIMED | 45 frames |  |
| 235 | EscapeN | SOURCE-RETIMED | x1.85 speed, 24 frames |  |
| 236 | EscapeAir | SOURCE-RETIMED | x1.5 speed, 30 frames |  |
| 237 | ReboundStop | SOURCE-RETIMED | 31 frames |  |
| 238 | Rebound | SOURCE-RETIMED | 38 frames |  |
| 239 | ThrownF | SOURCE-RETIMED | held at f4, 60 frames |  |
| 240 | ThrownB | SOURCE-RETIMED | held at f4, 60 frames |  |
| 241 | ThrownHi | SOURCE-RETIMED | held at f4, 60 frames |  |
| 242 | ThrownLw | SOURCE-RETIMED | held at f4, 60 frames |  |
| 243 | ThrownlwWomen | SOURCE-RETIMED | held at f4, 60 frames |  |
| 244 | Pass | SOURCE-RETIMED | 50 frames |  |
| 245 | Ottotto | SOURCE-RETIMED | x2 speed, 14 frames |  |
| 246 | OttottoWait | SOURCE-RETIMED | from f20, 40 frames |  |
| 247 | FlyReflectWall | SOURCE-RETIMED | x2.3 speed, 20 frames |  |
| 248 | FlyReflectCeil | SOURCE-RETIMED | x2.3 speed, 20 frames |  |
| 249 | StopWall | SOURCE-RETIMED | x2.3 speed, 20 frames |  |
| 250 | StopCeil | SOURCE-RETIMED | x7 speed, 6 frames |  |
| 251 | MissFoot | SOURCE-RETIMED | 30 frames |  |
| 252 | CliffCatch | AUTHORED | authored: overhead hang pose dropping onto the ledge |  |
| 253 | CliffWait | AUTHORED | authored: held overhead hang |  |
| 254 | CliffClimbSlow | AUTHORED | authored: hang to standing, BAS_JUMP crouch crop, TransN path ledge to stage |  |
| 255 | CliffClimbQuick | AUTHORED | authored: hang to standing, BAS_JUMP crouch crop, TransN path ledge to stage |  |
| 256 | CliffAttackSlow | AUTHORED | authored: hang to GOK_ATC_012 low sweep on the stage |  |
| 257 | CliffAttackQuick | AUTHORED | authored: hang to GOK_ATC_012 low sweep on the stage |  |
| 258 | CliffEscapeSlow | AUTHORED | authored: hang to forward roll (BAS_STEP_F_S) onto the stage |  |
| 259 | CliffEscapeQuick | AUTHORED | authored: hang to forward roll (BAS_STEP_F_S) onto the stage |  |
| 260 | CliffJumpSlow1 | AUTHORED | authored: hang pulling up to the ledge top |  |
| 261 | CliffJumpSlow2 | SOURCE-RETIMED | 19 frames |  |
| 262 | CliffJumpQuick1 | AUTHORED | authored: hang pulling up to the ledge top |  |
| 263 | CliffJumpQuick2 | SOURCE-RETIMED | 19 frames |  |
| 264 | AppealSR | AUTHORED | AUTHORED choice: XV2 lobby gesture as the taunt |  |
| 265 | AppealSL | AUTHORED | AUTHORED choice: XV2 lobby gesture as the taunt |  |
| 266 | ShoulderedWait | SOURCE-RETIMED | held at f8, 30 frames |  |
| 267 | ShoulderedWalkSlow | SOURCE-RETIMED | held at f8, 30 frames |  |
| 268 | ShoulderedWalkMiddle | SOURCE-RETIMED | held at f8, 30 frames |  |
| 269 | ShoulderedWalkFast | SOURCE-RETIMED | held at f8, 30 frames |  |
| 270 | ShoulderedTurn | SOURCE-RETIMED | held at f8, 12 frames |  |
| 271 | ThrownFF | SOURCE-RETIMED | held at f4, 60 frames |  |
| 272 | ThrownFB | SOURCE-RETIMED | held at f4, 60 frames |  |
| 273 | ThrownFHi | SOURCE-RETIMED | held at f4, 60 frames |  |
| 274 | ThrownFLw | SOURCE-RETIMED | held at f4, 60 frames |  |
| 275 | CaptureCaptain | SOURCE-RETIMED | held at f8, 30 frames |  |
| 276 | CaptureYoshi | SOURCE-RETIMED | held at f8, 30 frames |  |
| 277 | YoshiEgg | SOURCE-RETIMED | held at f8, 30 frames |  |
| 278 | CaptureKoopa | SOURCE-RETIMED | held at f8, 30 frames |  |
| 279 | CaptureDamageKoopa | SOURCE-RETIMED | x1.5 speed, 14 frames |  |
| 280 | CaptureWaitKoopa | SOURCE-RETIMED | held at f8, 30 frames |  |
| 281 | ThrownKoopaF | SOURCE-RETIMED | from f8, 60 frames |  |
| 282 | ThrownKoopaB | SOURCE-RETIMED | from f8, 60 frames |  |
| 283 | CaptureKoopaAir | SOURCE-RETIMED | held at f8, 30 frames |  |
| 284 | CaptureDamageKoopaAir | SOURCE-RETIMED | x1.5 speed, 14 frames |  |
| 285 | CaptureWaitKoopaAir | SOURCE-RETIMED | held at f8, 30 frames |  |
| 286 | ThrownKoopaAirF | SOURCE-RETIMED | from f8, 60 frames |  |
| 287 | ThrownKoopaAirB | SOURCE-RETIMED | from f8, 60 frames |  |
| 288 | CaptureKirby | SOURCE-RETIMED | held at f8, 30 frames |  |
| 289 | CaptureWaitKirby | SOURCE-RETIMED | held at f8, 30 frames |  |
| 290 | ThrownKirbyStar | SOURCE-RETIMED | from f8, 60 frames |  |
| 291 | ThrownCopyStar | SOURCE-RETIMED | from f8, 60 frames |  |
| 292 | ThrownKirby | SOURCE-RETIMED | from f8, 60 frames |  |
| 293 | BarrelWait | SOURCE-RETIMED | held at f8, 30 frames |  |
| 294 | Bury | SOURCE-RETIMED | from f50, 7 frames |  |
| 295 | BuryWait | SOURCE-RETIMED | from f56, held at f56, 30 frames |  |
| 296 | BuryJump | SOURCE-RETIMED | 19 frames |  |
| 297 | DamageSong | SOURCE-RETIMED | 30 frames |  |
| 298 | DamageSongWait | SOURCE-RETIMED | 60 frames |  |
| 299 | DamageSongRv | SOURCE-RETIMED | 40 frames |  |
| 300 | DamageBind | SOURCE-RETIMED | 60 frames |  |
| 301 | CaptureMewtwo | SOURCE-RETIMED | held at f8, 30 frames |  |
| 302 | CaptureMewtwoAir | SOURCE-RETIMED | held at f8, 30 frames |  |
| 303 | ThrownMewtwo | SOURCE-RETIMED | from f8, 60 frames |  |
| 304 | ThrownMewtwoAir | SOURCE-RETIMED | from f8, 60 frames |  |
| 305 | WarpStarJump | SOURCE-RETIMED | 19 frames |  |
| 306 | WarpStarFall | SOURCE-RETIMED | 50 frames |  |
| 307 | HammerWait | SOURCE-RETIMED | from f18, 28 frames |  |
| 308 | HammerWalk | SOURCE-RETIMED | from f18, 28 frames |  |
| 309 | HammerTurn | SOURCE-RETIMED | from f18, 28 frames |  |
| 310 | HammerKneeBend | SOURCE-RETIMED | from f18, 28 frames |  |
| 311 | HammerFall | SOURCE-RETIMED | from f18, 28 frames |  |
| 312 | HammerJump | SOURCE-RETIMED | from f18, 28 frames |  |
| 313 | HammerLanding | SOURCE-RETIMED | from f18, 28 frames |  |
| 314 | KinokoGiantStart | SOURCE-RETIMED | 40 frames |  |
| 315 | KinokoGiantStartAir | SOURCE-RETIMED | 40 frames |  |
| 316 | KinokoGiantEnd | SOURCE-RETIMED | 40 frames |  |
| 317 | KinokoGiantEndAir | SOURCE-RETIMED | 40 frames |  |
| 318 | KinokoSmallStart | SOURCE-RETIMED | 40 frames |  |
| 319 | KinokoSmallStartAir | SOURCE-RETIMED | 40 frames |  |
| 320 | KinokoSmallEnd | SOURCE-RETIMED | 40 frames |  |
| 321 | KinokoSmallEndAir | SOURCE-RETIMED | 40 frames |  |
| 322 | Entry | SOURCE-RETIMED | 210 frames |  |
| 323 | EntryStart | SOURCE-RETIMED | 210 frames |  |
| 324 | EntryEnd | SOURCE-RETIMED | 210 frames |  |
| 325 | DamageIce | SOURCE-RETIMED | held at f20, 2 frames |  |
| 326 | DamageIceJump | SOURCE-RETIMED | held at f20, 2 frames |  |
| 327 | CaptureMasterHand | SOURCE-RETIMED | held at f8, 30 frames |  |
| 328 | CaptureDamageMasterHand | SOURCE-RETIMED | x1.5 speed, 14 frames |  |
| 329 | CaptureWaitMasterHand | SOURCE-RETIMED | held at f8, 30 frames |  |
| 330 | ThrownMasterHand | SOURCE-RETIMED | from f8, 60 frames |  |
| 331 | CaptureKirbyYoshi | SOURCE-RETIMED | held at f8, 30 frames |  |
| 332 | KirbyYoshiEgg | SOURCE-RETIMED | held at f8, 30 frames |  |
| 333 | CaptureLeadead | SOURCE-RETIMED | held at f8, 30 frames |  |
| 334 | CaptureLikelike | SOURCE-RETIMED | held at f8, 30 frames |  |
| 335 | DownReflect | SOURCE-RETIMED | x2.2 speed, 26 frames |  |
| 336 | CaptureCrazyHand | SOURCE-RETIMED | held at f8, 30 frames |  |
| 337 | CaptureDamageCrazyHand | SOURCE-RETIMED | x1.5 speed, 14 frames |  |
| 338 | CaptureWaitCrazyHand | SOURCE-RETIMED | held at f8, 30 frames |  |
| 339 | ThrownCrazyHand | SOURCE-RETIMED | from f8, 60 frames |  |
| 340 | Barrel | SOURCE-RETIMED | 40 frames |  |
| 341 | AppealSR | AUTHORED | AUTHORED choice: XV2 lobby gesture as the taunt |  |
| 342 | AppealSL | AUTHORED | AUTHORED choice: XV2 lobby gesture as the taunt |  |
| 343 | SpecialN | SOURCE-RETIMED | held at f40, 135 frames |  |
| 344 | SpecialAirN | SOURCE-RETIMED | from f48, x1.4 speed, 32 frames |  |
| 345 | SpecialS | SOURCE-RETIMED | 66 frames |  |
| 346 | SpecialAirS | SOURCE-RETIMED | 66 frames |  |
| 347 | SpecialHi | SOURCE-RETIMED | x0.7 speed, 26 frames |  |
| 348 | SpecialAirHi | SOURCE-RETIMED | x0.7 speed, 26 frames |  |
| 349 | SpecialLw | SOURCE-RETIMED | x0.39 speed, 46 frames |  |
| 350 | SpecialAirLw | SOURCE-RETIMED | from f1, 46 frames |  |
