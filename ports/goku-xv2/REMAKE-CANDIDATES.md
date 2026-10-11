# Goku remake: candidate animation sheet

One row per Melee slot. **Pick by animation merit only** (pose silhouette, feel, timing, direction, combo role); hitbox fit is not a
criterion (hitboxes are authored by hand afterwards, see REMAKE-PLAN.md section 1). `rec` marks the recommended pick; write yours in
`owner pick`. Clip names are XV2 library actions (`x` + source name), all present in `goku.blend`. "metrics" are measured by
`tools/remake_preview.py` (frames; peak forward reach of a hand or foot from the pelvis, in model units; peak height above the pelvis;
the fastest limb and its frame = the likely strike frame). Montage PNGs (6 frames, first to last, character faces right) are in
`_build/goku-xv2/remake-previews/<clip>.png` and embedded in `candidate-sheet.html` (local only: XV2-derived).

Preview any clip: LAB `& "ports\goku-xv2\tools\clips.ps1" <clip>`; Blender: `tools/blender/geno_workbench/launch_goku.py`, assign the
action; or the montage PNG. The recommendations below come from XV2 usage (which BAC/input plays the clip), clip length and the
measured motion; **only a sample of montages was looked at by the planner (marked `seen`); the rest are for the owner to review.**


## 1 Locomotion (always floating)

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| Idle | Wait, Rebirth, RebirthWait, Sleep | GOK_BAS_STAND_S (Sleep still ground STAND) | Resting stance; must loop, tiny bob, readable as hovering | `xGOK_BAS_STAND_S` **rec** seen: XV2 sky idle, already the idle; prone flight stance, 100f loop (100f; reach 5.4 L_Hand f0; high 4.5; fastest R_Foot f90)<br>`xGOK_BAS_STAND_00_S`: alternate sky idle (100f; reach 6.2 L_Hand f10; high 3.4; fastest R_Foot f36)<br>`xGOK_BAS_STAND_01_S`: alternate sky idle (100f; reach 6.2 L_Hand f16; high 4.6; fastest L_Hand f36)<br>`xGOK_BAS_STAND_SS3_S`: 211f power-stance idle (hair-up / aura mood); long, loop point must be checked (180f; reach 1.5 L_Hand f38; high 0.5; fastest L_Foot f100) |  |
| Walk (slow/mid/fast) | WalkSlow, WalkMiddle, WalkFast | GOK_BAS_WALK (ground walk, 70f) x one clip | No walking: a slow drift whose rate scales with stick | `xGOK_BAS_BUKUU_F_S` **rec** seen: XV2 fly-forward (floating travel); 40f loop, head-first dive posture, reads as gliding (40f; reach 9.2 L_Hand f2; high 4.8; fastest L_Hand f34)<br>`xGOK_BAS_STEP_F_S`: 45f air step forward; reads as a lunge, may look jittery looped (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4)<br>`xGOK_BAS_BOOST_F_01`: sustained boost; strongest "flying" read but too fast for a walk even at low rate (180f; reach 2.5 L_Hand f0; high 5.2; fastest R_Hand f96) |  |
| Run | Run, RunDirect | GOK_BAS_RUN (ground run, 30f) | Full-speed travel, loop | `xGOK_BAS_BOOST_F_01` **rec**: XV2 sustained boost (257f, loop a stable 30-40f crop); the obvious fast-flight clip (180f; reach 2.5 L_Hand f0; high 5.2; fastest R_Hand f96)<br>`xGOK_BAS_BUKUU_F_S` seen: same as walk at a higher rate (one clip for both = consistent, less distinct) (40f; reach 9.2 L_Hand f2; high 4.8; fastest L_Hand f34)<br>`xGOK_BAS_STEP_F_S`: repeated steps; weaker (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4) |  |
| Dash (start) | Dash | BOOST_F_00 x0.55, eased into Run | Dash burst before Run | `xGOK_BAS_BOOST_F_00` **rec**: XV2 boost launch (24f), already used (24f; reach 5.4 L_Hand f0; high 4.3; fastest R_Foot f22)<br>`xGOK_BAS_STEP_F_S`: 45f step; slower burst (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4)<br>`xGOK_BAS_BUKUU_F_S` seen: just the glide; no burst (40f; reach 9.2 L_Hand f2; high 4.8; fastest L_Hand f34) |  |
| Run brake / stop | RunBrake | BOOST_F_02 from f6 x0.75 | Stopping out of Run | `xGOK_BAS_BOOST_F_02` **rec**: XV2 boost stop (19f), already used (19f; reach 5.4 L_Hand f18; high 4.3; fastest R_Foot f10)<br>`xCMN_BAS_BRAKE_S`: 55f sky brake (CMN), longer and softer (55f; reach 7.8 R_Foot f0; high 5.0; fastest R_Foot f2)<br>`xGOK_BAS_STAND_S` seen: plain ease into idle, no skid (100f; reach 5.4 L_Hand f0; high 4.5; fastest R_Foot f90) |  |
| Turn (wait / run) | Turn, TurnRun | authored 180 yaw on Wait / BOOST_F_02 + yaw | Turnaround; the earlier note "XV2 has no turn" is wrong, CMN has one | `xCMN_BAS_TURN`: CMN has a 27f turn clip (not yet used; check that it is a floating pose) (27f; reach 5.9 L_Hand f0; high 4.0; fastest L_Hand f10)<br>`xCMN_BAS_BRAKE_B_S`: 55f backward brake as a run-turn (55f; reach 8.0 L_Foot f22; high 8.6; fastest R_Hand f4)<br>`xGOK_BAS_STEP_B_S`: 45f back step as a run-turn (45f; reach 6.2 R_Foot f18; high 4.9; fastest L_Hand f6)<br>`xGOK_BAS_STAND_S` **rec** seen: keep authored yaw ramp (current) (100f; reach 5.4 L_Hand f0; high 4.5; fastest R_Foot f90) |  |
| Crouch | Squat, SquatWait, SquatRv | GOK_BAS_JUMP landing-crouch crop (grounded) | A floating crouch: sink and tuck, never touching the floor | `xGOK_BAS_BUKUU_DOWN` **rec**: XV2 descend hover, hold a low frame; floating by definition (50f; reach 2.4 L_Hand f8; high 9.9; fastest L_Hand f20)<br>`xGOK_GRD_KAMAE_S`: sky guard stance: low, coiled (130f; reach 5.7 L_Hand f2; high 4.3; fastest R_Hand f4)<br>`xGOK_BAS_STEP_B_S`: 45f back step, use the settle frames (45f; reach 6.2 R_Foot f18; high 4.9; fastest L_Hand f6) |  |
| Jump squat | KneeBend | JUMP crop | 4-frame squat before the jump (Melee: jump_startup_time) | `xGOK_BAS_BUKUU_UP` **rec**: first frames of the ascend hover (50f; reach 2.2 L_Hand f8; high 1.8; fastest L_Hand f40)<br>`xGOK_BAS_BOOST_F_00`: first frames of the boost launch (24f; reach 5.4 L_Hand f0; high 4.3; fastest R_Foot f22)<br>`xGOK_BAS_JUMP_FRONT_00`: first 7f of XV2 jump start (current family) (19f; reach 5.9 R_Hand f12; high 4.3; fastest R_Hand f16) |  |
| Jump (ground, forward/back) | JumpF, JumpB | JUMP_FRONT_00 / JUMP_BACK_00 x0.33 (55f; owner: poor, punch list 9; queue 4: <= 40f) | Rise out of a jump; Melee row length = rise | `xGOK_BAS_BUKUU_UP` **rec**: 50f ascend hover; floating rise, the natural fit (50f; reach 2.2 L_Hand f8; high 1.8; fastest L_Hand f40)<br>`xGOK_BAS_JUMP_FRONT_01`: XV2 jump arc body (60f) cropped to 40 (16f; reach 2.9 L_Hand f4; high 2.8; fastest L_Foot f2)<br>`xGOK_BAS_STEP_F_S`: air step as a hop (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4)<br>`xGOK_BAS_BOOST_F_00`: boost-up launch (24f; reach 5.4 L_Hand f0; high 4.3; fastest R_Foot f22) |  |
| Double jump (air jump) | JumpAerialF, JumpAerialB | JUMP_FRONT_01 / BACK_01 x0.27 (60f) | Second jump in the air; reads as a burst | `xGOK_BAS_STEP_F_S` **rec**: forward air step burst (F); STEP_B_S for B (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4)<br>`xGOK_BAS_BUKUU_UP`: ascend hover again (50f; reach 2.2 L_Hand f8; high 1.8; fastest L_Hand f40)<br>`xGOK_BAS_JUMP_BACK_01`: XV2 back jump arc (B) (16f; reach 2.9 L_Hand f8; high 3.0; fastest L_Foot f2)<br>`xGOK_BAS_BOOST_F_00`: boost burst, distinct from the first jump (24f; reach 5.4 L_Hand f0; high 4.3; fastest R_Foot f22) |  |
| Fall | Fall, FallF/B, FallAerial*, FallSpecial*, Pass | GOK_BAS_BUKUU_DOWN (adapted) | Falling and helpless fall | `xGOK_BAS_BUKUU_DOWN` **rec**: XV2 descend; already used (50f; reach 2.4 L_Hand f8; high 9.9; fastest L_Hand f20)<br>`xGOK_BAS_JUMP_FRONT_02`: 17f falling pose from the jump body (31f; reach 5.5 L_Hand f24; high 8.6; fastest R_Foot f2)<br>`xGOK_BAS_STUN_00_S`: 31f dazed sky pose for FallSpecial (helpless) (31f; reach 5.5 L_Hand f8; high 4.4; fastest L_Hand f14) |  |
| Landing (ground) | Landing, LandingFallSpecial, LandingAir* | JUMP_FRONT_02 from f10 (aliased to all 5 air landings) | Touch-down settle; Melee lag frames stay | `xGOK_BAS_BOOST_F_02` **rec**: boost stop tail, a braking settle (19f; reach 5.4 L_Hand f18; high 4.3; fastest R_Foot f10)<br>`xGOK_BAS_STEP_F_S`: end of the air step, easing to rest (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4)<br>`xGOK_BAS_BUKUU_UP`: last frames: a soft rise into idle (50f; reach 2.2 L_Hand f8; high 1.8; fastest L_Hand f40)<br>`xGOK_BAS_JUMP_FRONT_02`: current (31f; reach 5.5 L_Hand f24; high 8.6; fastest R_Foot f2) |  |

## 2 Defence

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| Shield | GuardOn, Guard, GuardOff, GuardSetOff, GuardReflect | GRD_KAMAE (ground) / GRD_L | Hold shield, release, hit-in-shield | `xGOK_GRD_KAMAE_S` **rec**: sky guard (130f): the floating shield stance (130f; reach 5.7 L_Hand f2; high 4.3; fastest R_Hand f4)<br>`xGOK_GRD_L_S`: 30f guard-hit flinch (sky), for GuardSetOff (30f; reach 4.9 L_Hand f0; high 4.7; fastest L_Hand f4)<br>`xGOK_GRD_L_L_S`: left shield hit variant; _R_S right (30f; reach 5.2 L_Hand f24; high 7.4; fastest L_Hand f4)<br>`xGOK_GRD_KAMAE`: ground guard, current (130f; reach 5.8 L_Foot f52; high 4.3; fastest R_Hand f2) |  |
| Shield break | ShieldBreakFly/Fall/DownU/D/StandU/D | CMN dizzy / stun rows | Shield broken | `xGOK_GRD_BREAK_S` **rec**: 90f sky guard-break, the XV2 clip made for this (90f; reach 8.0 L_Foot f18; high 9.0; fastest R_Hand f6)<br>`xGOK_GRD_BREAK`: ground guard-break (90f; reach 7.9 L_Foot f20; high 9.0; fastest R_Hand f6)<br>`xGOK_BAS_STUN_02_S`: 73f dizzy (also Furafura) (73f; reach 5.5 L_Hand f68; high 4.3; fastest L_Hand f46) |  |
| Roll / spot dodge / air dodge | EscapeF, EscapeB, EscapeN, EscapeAir | STEP_F_S, STEP_B_S, STEP_L_S x1.85/1.5 | Dodges: intangible frames are Melee rules | `xGOK_BAS_STEP_F_S` **rec**: forward roll as a sidestep-dash (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4)<br>`xGOK_BAS_STEP_B_S`: back roll (45f; reach 6.2 R_Foot f18; high 4.9; fastest L_Hand f6)<br>`xGOK_BAS_STEP_L_S`: spot dodge (L; R_S mirrored variant); also air dodge (45f; reach 6.0 L_Hand f4; high 4.5; fastest L_Hand f8)<br>`xGOK_BAS_BOOST_F_00`: air dodge as a boost burst (24f; reach 5.4 L_Hand f0; high 4.3; fastest R_Foot f22) |  |
| Dizzy | Furafura | GOK_BAS_STUN_02 | Stun | `xGOK_BAS_STUN_02_S` **rec**: 73f sky dizzy (73f; reach 5.5 L_Hand f68; high 4.3; fastest L_Hand f46)<br>`xGOK_BAS_STUN_01_S`: 40f (40f; reach 2.9 L_Foot f4; high 2.0; fastest R_Hand f6)<br>`xCMN_DMG_KANASHIBARI`: 220f frozen/paralysed (180f; reach 3.2 L_Foot f34; high 5.7; fastest L_Hand f12) |  |

## 3 Normals (ground)

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| Jab 1 (L1) | Attack11 | ATC_002 from f9 (BAC 300) | Opener, fast, safe; string link 1; combo: starter; links to jab2 | `xGOK_ATC_002` **rec**: XV2 light 1 (BAC 300): left jab (45f; reach 9.9 L_Hand f14; high 6.2; fastest L_Hand f12)<br>`xGOK_ATC_001` seen: XV2 forward light (BAC 460, single activation): kick-flip (35f; reach 7.2 L_Hand f4; high 6.3; fastest R_Hand f8)<br>`xGOK_ATC_000` seen: XV2 base attack pose, short (31f; reach 5.7 L_Foot f24; high 5.2; fastest L_Hand f2)<br>`xGOK_ATC_027`: XV2 light (BAC 340) used by the ki-volley string (39f; reach 7.9 L_Hand f4; high 8.6; fastest L_Hand f2) |  |
| Jab 2 (L2) | Attack12 | ATC_003 (BAC 301) | Second string hit; combo: link 2 | `xGOK_ATC_003` **rec**: XV2 light 2: right straight (41f; reach 7.5 R_Hand f6; high 8.8; fastest R_Hand f6)<br>`xGOK_ATC_029`: 55f light (BAC 351) (55f; reach 8.2 R_Foot f0; high 8.3; fastest R_Hand f4)<br>`xGOK_ATC_001` seen: forward light (35f; reach 7.2 L_Hand f4; high 6.3; fastest R_Hand f8) |  |
| Jab 3 (L3) | Attack13, Light3 state | ATC_017 (BAC 302) | Third hit, ends jab / continues string; combo: link 3; Light4 = ATC_009, Light5 = ATC_022 in the combo package | `xGOK_ATC_017` **rec**: XV2 light 3: left kick (42f; reach 7.2 L_Foot f12; high 8.6; fastest L_Hand f12)<br>`xGOK_ATC_009`: XV2 light 4 clip (BAC 303) (47f; reach 7.6 R_Foot f12; high 6.0; fastest R_Foot f12)<br>`xGOK_ATC_022`: XV2 light 5 / air light (BAC 304, 375) (36f; reach 5.6 L_Hand f28; high 5.5; fastest L_Hand f6) |  |
| Rapid jab | Attack100Start/Loop/End | ATC_028 (5-hit flurry) | Held-A flurry | `xGOK_ATC_028` **rec**: XV2 5-hit flurry (BAC 336/350): the only multi-hit clip (65f; reach 8.7 R_Foot f18; high 7.9; fastest R_Foot f18)<br>`xGOK_ATC_000` seen: pose loop (31f; reach 5.7 L_Foot f24; high 5.2; fastest L_Hand f2)<br>`xGOK_ATC_029`: 55f (55f; reach 8.2 R_Foot f0; high 8.3; fastest R_Hand f4) |  |
| Forward tilt | AttackS3S, S3Hi, S3HiS, S3LwS, S3Lw | ATC_008 (BAC 475) for all five rows | Spacing poke; Hi/Lw rows are angled variants (currently the same clip); combo: starter; spacing | `xGOK_ATC_008` **rec**: XV2 rush kick (47f), forward kick (47f; reach 8.8 R_Foot f26; high 6.1; fastest R_Foot f12)<br>`xGOK_ATC_016`: 38f heavy (BAC 325) (40f; reach 7.8 L_Hand f12; high 5.3; fastest L_Hand f12)<br>`xGOK_ATC_015`: 30f heavy (BAC 480) (32f; reach 7.8 R_Hand f12; high 5.0; fastest R_Hand f8)<br>`xGOK_ATC_001` seen: forward light (35f; reach 7.2 L_Hand f4; high 6.3; fastest R_Hand f8) |  |
| Up tilt | AttackHi3 | ATC_013 from f20 (owner: dumb, punch list 2) | Anti-air; combo: starter; anti-air | `xGOK_ATC_013`: XV2 heavy 1 (BAC 310) rising arm swing, current (38f; reach 8.4 R_Foot f10; high 8.6; fastest R_Foot f10)<br>`xGOK_ATC_004`: 43f uppercut (BAC 342) (43f; reach 7.1 L_Hand f10; high 10.5; fastest R_Hand f14)<br>`xGOK_ATC_025` **rec**: 61f somersault kick (BAC 365) (61f; reach 7.4 R_Hand f24; high 8.2; fastest R_Foot f22)<br>`xGOK_ATC_018_S`: 26f sky attack, unreviewed (26f; reach 10.3 R_Hand f6; high 9.2; fastest R_Hand f6) |  |
| Down tilt | AttackLw3 | ATC_020_S from f11 (low slide kick) | Low poke; combo: starter; low | `xGOK_ATC_020_S` **rec**: 51f low kick (BAC 370) (51f; reach 8.4 R_Foot f12; high 9.7; fastest R_Hand f8)<br>`xGOK_ATC_012`: 40f split sweep (BAC 341) (40f; reach 9.3 R_Hand f4; high 5.0; fastest R_Foot f10)<br>`xGOK_ATC_024`: 70f spinning low (BAC 360) (70f; reach 6.7 R_Hand f14; high 8.3; fastest R_Foot f28) |  |
| Dash attack | AttackDash | ATC_011 from f13 (flying side kick) | Run-in; combo: starter | `xGOK_ATC_011` **rec**: 70f flying side kick (BAC 337) (70f; reach 8.6 R_Foot f16; high 5.5; fastest R_Hand f16)<br>`xGOK_ATC_021_S`: 40f sky boost strike (BAC 465) (40f; reach 7.3 L_Foot f8; high 9.7; fastest L_Hand f8)<br>`xGOK_ATC_006`: 58f boost lunge (BAC 343) (58f; reach 9.1 L_Hand f18; high 9.5; fastest R_Hand f18)<br>`xGOK_ATC_030`: 145f late heavy (BAC 352) (145f; reach 8.0 L_Hand f74; high 9.6; fastest R_Hand f80) |  |
| Forward smash | AttackS4S, S4Hi, S4HiS, S4LwS, S4Lw | ATC_006 from f5 (BAC 343) for all five rows | Charge-able finisher | `xGOK_ATC_006` **rec**: 58f lunging strike (58f; reach 9.1 L_Hand f18; high 9.5; fastest R_Hand f18)<br>`xGOK_ATC_005` seen: 57f heavy (BAC 338) (57f; reach 7.7 L_Foot f24; high 8.9; fastest L_Foot f18)<br>`xGOK_ATC_030`: 145f late smash; very slow (145f; reach 8.0 L_Hand f74; high 9.6; fastest R_Hand f80)<br>`xGOK_ATC_011`: flying kick (70f; reach 8.6 R_Foot f16; high 5.5; fastest R_Hand f16) |  |
| Up smash | AttackHi4 | ATC_004 from f5 (BAC 342 uppercut) | Launcher / anti-air finisher; combo: launcher (route target HeavyUp) | `xGOK_ATC_004` **rec**: 43f uppercut, current, his launcher (HeavyUp uses it) (43f; reach 7.1 L_Hand f10; high 10.5; fastest R_Hand f14)<br>`xGOK_ATC_025`: somersault kick (61f; reach 7.4 R_Hand f24; high 8.2; fastest R_Foot f22)<br>`xGOK_ATC_013`: rising arm swing (38f; reach 8.4 R_Foot f10; high 8.6; fastest R_Foot f10) |  |
| Down smash | AttackLw4 | ATC_012 from f2 (split sweep, BAC 341) | Low two-sided sweep; combo: route target dsmash | `xGOK_ATC_012` **rec**: 40f split sweep (40f; reach 9.3 R_Hand f4; high 5.0; fastest R_Foot f10)<br>`xGOK_ATC_024`: 70f spinning, two hits (BAC 360) (70f; reach 6.7 R_Hand f14; high 8.3; fastest R_Foot f28)<br>`xGOK_ATC_007` seen: 49f split kick (49f; reach 6.9 R_Foot f16; high 7.6; fastest R_Foot f16) |  |

## 4 Aerials

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| Neutral air | AttackAirN | ATC_007 from f9 (split kick, 18 active frames) | Multi-hit sex-kick; Nair>Nair chain; combo: link; chains to itself | `xGOK_ATC_007` seen: 49f split kick (BAC 312/320) (49f; reach 6.9 R_Foot f16; high 7.6; fastest R_Foot f16)<br>`xGOK_ATC_022` **rec**: 33f air light (BAC 375) (36f; reach 5.6 L_Hand f28; high 5.5; fastest L_Hand f6)<br>`xGOK_ATC_024`: 70f spin, 2 hits (BAC 360) (70f; reach 6.7 R_Hand f14; high 8.3; fastest R_Foot f28)<br>`xGOK_ATC_029`: 55f (55f; reach 8.2 R_Foot f0; high 8.3; fastest R_Hand f4) |  |
| Forward air | AttackAirF | ATC_007 from f5 (same clip as nair; punch list 4) | Forward ender; combo: ender | `xGOK_ATC_023` **rec**: 34f air heavy (BAC 377), the XV2 heavy aerial (36f; reach 8.6 L_Foot f10; high 7.8; fastest R_Hand f10)<br>`xGOK_ATC_016`: 38f heavy (40f; reach 7.8 L_Hand f12; high 5.3; fastest L_Hand f12)<br>`xGOK_ATC_008`: 47f rush kick (47f; reach 8.8 R_Foot f26; high 6.1; fastest R_Foot f12)<br>`xGOK_ATC_005` seen: 57f heavy (57f; reach 7.7 L_Foot f24; high 8.9; fastest L_Foot f18) |  |
| Back air | AttackAirB | CROSS-PORT Melee Luigi AttackAirB (owner: looks and works as intended) | Back attack | `(Luigi AttackAirB)` **rec**: keep: the owner choice; needs the disc; not an XV2 clip (no metrics)<br>`xGOK_ATC_024`: 70f XV2 own back attack (BAC 360, input Heavy+Backwards): not yet considered as an aerial (70f; reach 6.7 R_Hand f14; high 8.3; fastest R_Foot f28)<br>`xGOK_ATC_010`: 41f backhand (BAC 335) (41f; reach 7.4 L_Hand f4; high 4.7; fastest L_Hand f12) |  |
| Up air | AttackAirHi | ATC_025 from f6 (somersault kick; owner: looks good, keep) | Juggle / launcher follow-up; combo: route: Uair>Nair | `xGOK_ATC_025` **rec**: 61f somersault kick, keep (61f; reach 7.4 R_Hand f24; high 8.2; fastest R_Foot f22)<br>`xGOK_ATC_004`: uppercut (43f; reach 7.1 L_Hand f10; high 10.5; fastest R_Hand f14)<br>`xGOK_ATC_013`: rising arm swing (38f; reach 8.4 R_Foot f10; high 8.6; fastest R_Foot f10) |  |
| Down air | AttackAirLw | ATC_007 f2 (leg down at f8; grounded; punch list 6) | Spike / stomp; combo: ender (spike) | `xGOK_ATC_020_S` **rec**: 51f sky low kick (BAC 370): a downward foot (51f; reach 8.4 R_Foot f12; high 9.7; fastest R_Hand f8)<br>`xGOK_ATC_022`: 33f air light (36f; reach 5.6 L_Hand f28; high 5.5; fastest L_Hand f6)<br>`xGOK_ATC_026`: 51f heavy (BAC 330/496) (51f; reach 9.9 L_Hand f12; high 7.4; fastest R_Hand f18)<br>`xGOK_ATC_018_S`: 26f sky attack (26f; reach 10.3 R_Hand f6; high 9.2; fastest R_Hand f6) |  |
| Air landings | LandingAirN/F/B/Hi/Lw | alias of Landing | Landing lag poses (Melee lag stays) | `xGOK_BAS_BOOST_F_02` **rec**: settle tail (as Landing) (19f; reach 5.4 L_Hand f18; high 4.3; fastest R_Foot f10)<br>`xGOK_BAS_STEP_F_S`: step tail (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4)<br>`xGOK_BAS_BUKUU_DOWN`: end of a descend (50f; reach 2.4 L_Hand f8; high 9.9; fastest L_Hand f20) |  |

## 5 Grabs and throws

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| Grab | Catch, CatchDash(Pull), CatchPull | NAG_TSUKAMI (BAC 600) | Standing / dash / pivot grab | `xGOK_NAG_TSUKAMI` **rec**: 52f XV2 grab (BAC 600), used (52f; reach 11.0 R_Hand f14; high 6.0; fastest R_Hand f10)<br>`xGOK_ATC_003`: right straight reach (41f; reach 7.5 R_Hand f6; high 8.8; fastest R_Hand f6)<br>`xGOK_ATC_015`: 30f short heavy (32f; reach 7.8 R_Hand f12; high 5.0; fastest R_Hand f8) |  |
| Grab hold / pummel | CatchWait, CatchAttack, CatchCut | TSUKAMI held f22+ ; CMN_BAS_HAJIKI_B_00 | Hold, pummel, release | `xGOK_NAG_TSUKAMI` **rec**: hold pose f22-45; pummel crop (52f; reach 11.0 R_Hand f14; high 6.0; fastest R_Hand f10)<br>`xGOK_ATC_002`: jab as pummel (45f; reach 9.9 L_Hand f14; high 6.2; fastest L_Hand f12)<br>`xGOK_ATC_029`: 55f light as pummel (55f; reach 8.2 R_Foot f0; high 8.3; fastest R_Hand f4) |  |
| Forward throw | ThrowF | GNY_NAG_A f16-45 (BAC 601) | Toss | `xGNY_NAG_A` **rec**: 201f XV2 throw (borrowed GNY clip) (180f; reach 9.9 R_Hand f0; high 10.6; fastest R_Foot f12)<br>`xGOK_ATC_005` seen: heavy, as a punch throw (57f; reach 7.7 L_Foot f24; high 8.9; fastest L_Foot f18)<br>`xGOK_ATC_011`: flying kick (70f; reach 8.6 R_Foot f16; high 5.5; fastest R_Hand f16) |  |
| Back throw | ThrowB | GNY_NAG_A turned 180 (authored) | Throw behind | `xGNY_NAG_D`: 157f XV2 slam (BAC 602/603) (169f; reach 8.4 L_Foot f70; high 7.6; fastest R_Hand f154)<br>`xGOK_ATC_010`: 41f backhand (41f; reach 7.4 L_Hand f4; high 4.7; fastest L_Hand f12)<br>`xGOK_ATC_024` **rec**: 70f spin (Backwards heavy) (70f; reach 6.7 R_Hand f14; high 8.3; fastest R_Foot f28) |  |
| Up throw | ThrowHi | ATC_004 uppercut (authored choice) | Throw up | `xGOK_ATC_004` **rec**: uppercut (43f; reach 7.1 L_Hand f10; high 10.5; fastest R_Hand f14)<br>`xGOK_ATC_025`: somersault kick (61f; reach 7.4 R_Hand f24; high 8.2; fastest R_Foot f22)<br>`xGOK_ATC_013`: rising swing (38f; reach 8.4 R_Foot f10; high 8.6; fastest R_Foot f10) |  |
| Down throw | ThrowLw | ATC_012 sweep (authored choice) | Throw down | `xGNY_NAG_D` **rec**: 157f slam into ground (169f; reach 8.4 L_Foot f70; high 7.6; fastest R_Hand f154)<br>`xGOK_ATC_012`: split sweep (40f; reach 9.3 R_Hand f4; high 5.0; fastest R_Foot f10)<br>`xGOK_ATC_020_S`: low kick (51f; reach 8.4 R_Foot f12; high 9.7; fastest R_Hand f8) |  |
| Thrown / captured by others | Thrown*, Capture*, ShoulderedWait... | CMN_DMG clips / Falcon stand-ins | Victim poses (many rows) | `xCMN_DMG_BODY_L_F_S` **rec**: 34f sky hit-stun (34f; reach 6.9 L_Hand f2; high 3.0; fastest R_Hand f2)<br>`xCMN_DMG_AIR_F`: 30f air hit (30f; reach 7.8 R_Foot f0; high 6.2; fastest R_Hand f6)<br>`xCMN_DMG_BLOW_F`: 20f blown (20f; reach 7.4 R_Foot f0; high 5.7; fastest R_Foot f12) |  |

## 6 Specials

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| Neutral B Kamehameha | SpecialN, SpecialAirN, Kame* | xGOK_SPA_KMH | Accepted design (owner) | `xGOK_SPA_KMH_*` **rec**: not up for choice; unchanged (no metrics) |  |
| Side B Dragon Rush | SpecialS, SpecialAirS (+Rush, RushCombo) | BOOST_F_00 + STEP_F_S + ATC_013 | Dash strike and recovery; combo: route: Rush>RushCombo; XV2 BAC 426/427 use ATC_022/023 | `xGOK_ATC_021_S` **rec**: 40f sky boost strike (BAC 465) (40f; reach 7.3 L_Foot f8; high 9.7; fastest L_Hand f8)<br>`xGOK_ATC_011`: flying side kick (70f; reach 8.6 R_Foot f16; high 5.5; fastest R_Hand f16)<br>`xGOK_ATC_013`: rising swing (current) (38f; reach 8.4 R_Foot f10; high 8.6; fastest R_Foot f10)<br>`xGOK_ATC_006`: lunge (58f; reach 9.1 L_Hand f18; high 9.5; fastest R_Hand f18) |  |
| Up B Instant Transmission | SpecialHi, SpecialAirHi | xGOK_ESC_KUR_C | Teleport recovery | `xGOK_ESC_KUR_C` **rec**: accepted (146f; reach 9.1 L_Hand f64; high 9.6; fastest L_Hand f20)<br>`xGOK_BAS_BOOST_F_00`: alt vanish (24f; reach 5.4 L_Hand f0; high 4.3; fastest R_Foot f22) |  |
| Down B counter / ki charge | SpecialLw, SpecialAirLw, KiCharge | ESC_KUR_C x0.6 + ATC_008 / BLT_POW_C | Counter and ki charge | `xGOK_ESC_KUR_C`: blink (counter), current (146f; reach 9.1 L_Hand f64; high 9.6; fastest L_Hand f20)<br>`xCMN_BLT_POW_GOK` **rec**: 101f Goku-specific ki charge pose (101f; reach 8.8 R_Hand f40; high 11.5; fastest R_Hand f40)<br>`xCMN_BLT_POW_C`: current ki charge (101f; reach 8.9 R_Hand f40; high 11.5; fastest R_Hand f40) |  |
| Ki volley | KiVolley (combo) | ATC_SHOT_N | Neutral-B cancel | `xGOK_ATC_SHOT_N` **rec**: 40f; _F / _B / _L / _R directional (40f; reach 5.7 L_Hand f2; high 5.2; fastest R_Hand f8)<br>`xGOK_ATC_SHOT_F`: 40f forward blast (40f; reach 10.9 R_Hand f14; high 5.0; fastest L_Hand f8) |  |

## 7 Ledge and getups

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| Ledge catch / wait | CliffCatch, CliffWait | JUMP_BACK_00 f12 authored lean | Hang | `xGOK_BAS_BUKUU_UP`: arms-down hover as a one-hand hang (50f; reach 2.2 L_Hand f8; high 1.8; fastest L_Hand f40)<br>`xGOK_BAS_JUMP_BACK_00` **rec**: arms overhead (current) (19f; reach 5.8 R_Foot f14; high 8.3; fastest R_Hand f10)<br>`xGOK_GRD_L_S`: guard-hit pose, braced (30f; reach 4.9 L_Hand f0; high 4.7; fastest L_Hand f4) |  |
| Ledge climb | CliffClimbSlow/Quick | JUMP crouch crop, TransN path | Get up | `xGOK_BAS_BUKUU_UP` **rec**: float up and over (50f; reach 2.2 L_Hand f8; high 1.8; fastest L_Hand f40)<br>`xGOK_BAS_STEP_F_S`: step over (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4)<br>`xGOK_BAS_BOOST_F_00`: boost over (24f; reach 5.4 L_Hand f0; high 4.3; fastest R_Foot f22) |  |
| Ledge attack / escape / jump | CliffAttack*, CliffEscape*, CliffJump* | ATC_012 / STEP_F_S | Getup attack, roll, jump | `xGOK_ATC_012` **rec**: low sweep (current) (40f; reach 9.3 R_Hand f4; high 5.0; fastest R_Foot f10)<br>`xGOK_ATC_008`: rush kick (47f; reach 8.8 R_Foot f26; high 6.1; fastest R_Foot f12)<br>`xGOK_BAS_STEP_F_S`: roll (45f; reach 9.2 L_Hand f12; high 6.7; fastest L_Hand f4)<br>`xGOK_BAS_BOOST_F_00`: jump (24f; reach 5.4 L_Hand f0; high 4.3; fastest R_Foot f22) |  |
| Floor getups | DownBound*, DownWait*, DownStand*, DownAttack*, DownForward/Back/Spot*, Passive* | CMN_BAS_DOWN_*_S, UKEMI | Knockdown and tech | `xCMN_BAS_DOWN_AOMUKE_S` **rec**: sky knockdown (supine) 100f; UTSUBUSE_S prone (100f; reach 7.3 L_Foot f62; high -0.8; fastest R_Foot f32)<br>`xCMN_BAS_UKEMI_N`: tech in place; UKEMI_F/B/L/R/U rolls (36f; reach 5.9 L_Hand f28; high 6.4; fastest R_Foot f10)<br>`xGOK_ATC_012`: getup attack (current) (40f; reach 9.3 R_Hand f4; high 5.0; fastest R_Foot f10) |  |

## 8 Damage

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| Hit stun (hi / mid / low, ground+air) | DamageHi1-3, N1-3, Lw1-3, Air1-3 | CMN_DMG_HEAD/BODY/LEG_L_F, AIR_F | Flinch | `xCMN_DMG_BODY_L_F_S` **rec**: 34f sky flinch; HEAD_/LEG_ _S exist (34f; reach 6.9 L_Hand f2; high 3.0; fastest R_Hand f2)<br>`xCMN_DMG_HEAD_L_F_S`: head flinch sky (34f; reach 5.4 L_Hand f32; high 4.7; fastest L_Hand f2)<br>`xCMN_DMG_AIR_F`: 30f air (30f; reach 7.8 R_Foot f0; high 6.2; fastest R_Hand f6) |  |
| Fly / tumble | DamageFly*, DamageFall, DeadUp* | CMN_DMG_BLOW/UP/DIVE/TUMBLE | Launched states | `xCMN_DMG_BLOW_F`: 20f blown (20f; reach 7.4 R_Foot f0; high 5.7; fastest R_Foot f12)<br>`xCMN_DMG_TUMBLE_F` **rec**: 69f tumble (69f; reach 8.1 L_Hand f68; high 5.4; fastest R_Foot f40)<br>`xCMN_DMG_BLOW_SPIN`: 136f spin (136f; reach 8.3 L_Foot f108; high 7.5; fastest L_Hand f12)<br>`xCMN_DMG_UP_F`: 49f up-blown (49f; reach 7.7 L_Foot f16; high 7.6; fastest L_Hand f6) |  |
| Wall / ceiling / ottotto | StopWall, StopCeil, Ottotto* | CMN_DMG_WALL_BOUND, YOROKE | Impacts and edge wobble | `xCMN_DMG_WALL_BOUND_F` **rec**: 46f wall bound (46f; reach 7.4 R_Foot f0; high 6.5; fastest L_Foot f2)<br>`xCMN_DMG_YOROKE_BODY_F_S`: 85f stagger sky (85f; reach 8.1 R_Hand f24; high 2.5; fastest R_Foot f2)<br>`xCMN_DMG_YOROKE_HEAD_F_S`: 43f (43f; reach 5.3 L_Hand f28; high 6.7; fastest L_Hand f4) |  |

## 9 Showpieces

| slot | Melee rows | current source | role (combo role) | candidates (rec = recommended; metrics) | owner pick |
|---|---|---|---|---|---|
| Taunt | AppealSL, AppealSR (both) | CMN lobby gesture (118) | Taunt | `xGOK_BAS_STAND_SS3_S` **rec**: 211f power-up stance (180f; reach 1.5 L_Hand f38; high 0.5; fastest L_Foot f100)<br>`xCMN_BAS_HIRAMEKI`: 90f "idea" gesture (90f; reach 6.2 L_Hand f2; high 4.8; fastest L_Hand f18)<br>`xCMN_BAS_KYORYOKU_C`: 140f power gesture (140f; reach 6.1 L_Hand f0; high 9.9; fastest L_Hand f20)<br>`xCMN_LBY_STAND`: 100f lobby (current family) (100f; reach -0.0 L_Hand f98; high 0.1; fastest R_Hand f90) |  |
| Entry | Entry, EntryStart, EntryEnd | GOK_DEM_START 210f | Spawn-in | `xGOK_DEM_START` **rec**: 210f XV2 intro; crop to 90 (180f; reach 4.1 L_Hand f172; high 6.4; fastest L_Hand f170)<br>`xXBG_DEM_KokuhukuHenshin_00`: 371f transformation (180f; reach 5.5 L_Hand f178; high 4.1; fastest R_Hand f16)<br>`xGOK_BAS_STAND_SS3_S`: power stance (180f; reach 1.5 L_Hand f38; high 0.5; fastest L_Foot f100) |  |
| Victory / results pose | (results screen, not a fighter row) | n/a | Win poses are outside the 351 rows; chosen with the results-screen pass | `xGOK_BAS_STAND_SS3` **rec**: 211f (180f; reach 1.5 L_Hand f46; high 0.5; fastest R_Hand f80)<br>`xGOK_DEM_START`: 210f (180f; reach 4.1 L_Hand f172; high 6.4; fastest L_Hand f170)<br>`xCMN_BAS_HIRAMEKI`: 90f (90f; reach 6.2 L_Hand f2; high 4.8; fastest L_Hand f18) |  |

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
| 25 | JumpF | SOURCE-RETIMED | x0.33 speed, 55 frames |  |
| 26 | JumpB | SOURCE-RETIMED | x0.33 speed, 55 frames |  |
| 27 | JumpAerialF | SOURCE-RETIMED | x0.27 speed, 60 frames |  |
| 28 | JumpAerialB | SOURCE-RETIMED | x0.27 speed, 60 frames |  |
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
| 51 | AttackS3Hi | AUTHORED | explicit prototype reuse of AttackS3S; directional pose authored-needed |  |
| 52 | AttackS3HiS | AUTHORED | explicit prototype reuse of AttackS3S; directional pose authored-needed |  |
| 53 | AttackS3S | SOURCE-RETIMED | from f5, 30 frames |  |
| 54 | AttackS3LwS | AUTHORED | explicit prototype reuse of AttackS3S; directional pose authored-needed |  |
| 55 | AttackS3Lw | AUTHORED | explicit prototype reuse of AttackS3S; directional pose authored-needed |  |
| 56 | AttackHi3 | SOURCE-RETIMED | from f20, 30 frames |  |
| 57 | AttackLw3 | SOURCE-RETIMED | from f11, 26 frames |  |
| 58 | AttackS4Hi | AUTHORED | explicit prototype reuse of AttackS4S; directional pose authored-needed |  |
| 59 | AttackS4HiS | AUTHORED | explicit prototype reuse of AttackS4S; directional pose authored-needed |  |
| 60 | AttackS4S | SOURCE-RETIMED | from f5, 46 frames |  |
| 61 | AttackS4LwS | AUTHORED | explicit prototype reuse of AttackS4S; directional pose authored-needed |  |
| 62 | AttackS4Lw | AUTHORED | explicit prototype reuse of AttackS4S; directional pose authored-needed |  |
| 63 | AttackHi4 | SOURCE-RETIMED | from f5, 44 frames |  |
| 64 | AttackLw4 | SOURCE-RETIMED | from f2, 42 frames |  |
| 65 | AttackAirN | SOURCE-RETIMED | from f9, 44 frames |  |
| 66 | AttackAirF | SOURCE-RETIMED | from f5, 44 frames |  |
| 67 | AttackAirB | CROSS-PORT | Melee Luigi AttackAirB, 30 frames, size ratio 1.722 |  |
| 68 | AttackAirHi | SOURCE-RETIMED | from f7, 34 frames |  |
| 69 | AttackAirLw | SOURCE-RETIMED | from f2, 40 frames |  |
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
| 219 | ThrowF | SOURCE-RETIMED | from f16, 30 frames |  |
| 220 | ThrowB | SOURCE-RETIMED | from f16, 38 frames |  |
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
| 343 | SpecialN | SOURCE-RETIMED | held at f40, 45 frames |  |
| 344 | SpecialAirN | SOURCE-RETIMED | from f48, x1.4 speed, 32 frames |  |
| 345 | SpecialS | SOURCE-RETIMED | 40 frames |  |
| 346 | SpecialAirS | SOURCE-RETIMED | 40 frames |  |
| 347 | SpecialHi | SOURCE-RETIMED | x0.7 speed, 26 frames |  |
| 348 | SpecialAirHi | SOURCE-RETIMED | x0.7 speed, 26 frames |  |
| 349 | SpecialLw | SOURCE-RETIMED | x0.39 speed, 46 frames |  |
| 350 | SpecialAirLw | SOURCE-RETIMED | from f1, 46 frames |  |
