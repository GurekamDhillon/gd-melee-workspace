# Goku remake, phase 1 (2026-10-11)

Lane `ws/goku-remake-p1`. Every slot of [REMAKE-CANDIDATES.md](REMAKE-CANDIDATES.md) uses its recommended pick (owner: "yea sounds good"), controls are Scheme A (Melee buttons only), and every remade move is **HB-NONE** (animation and timing only, no hitbox; the owner authors them by hand later) except the designed Kamehameha, KiBlast and Counter (**HB-DESIGN**). "Always floating" is animation only: ground rows hover at one constant `HOVER_Y` 2.5 (aerial attacks, getups and ledge rows stay anchored); gameplay keeps Melee ground/air rules. Mobility values: Marth option (c).

Play: `& 'E:\Projects\Melee Workspace\worktrees\gokup1\ports\goku-xv2	ools\play_remake.ps1'` (`-Picker` opens the REMAKE picker with the picks taken).

Reproduce on a checkout whose git-ignored `gameplay.full.json` / `combo/combo.json` predate this: `python ports/goku-xv2/tools/remake_patch.py`, then `xv2_to_artist.py`, `build.py`, `combo_apply.py`; gate: `python ports/goku-xv2/tools/remake_hb.py check`.

## Slots

| # | slot | status | pick | rows changed (clip) |
|---|---|---|---|---|
| 1 | Idle | KEEP | (none) | Sleep <- GOK_BAS_STAND_S |
| 2 | Walk (slow/mid/fast) | OK | xGOK_BAS_WALK | (kept: 1 row(s) already played it) |
| 3 | Run | OK | xGOK_BAS_RUN | (kept: 1 row(s) already played it) |
| 4 | Dash (start) | OK | xGOK_BAS_BOOST_F_00 | (kept: 1 row(s) already played it) |
| 5 | Run brake / stop | GAP | (none) | - |
| 6 | Turn (wait / run) | OK | xGOK_BAS_STAND_S | (kept: 2 row(s) already played it) |
| 7 | Crouch | OK | xGOK_BAS_JUMP | (kept: 3 row(s) already played it) |
| 8 | Jump squat | KEEP | (none) | - |
| 9 | Jump (ground, forward/back) | GAP | (none) | - |
| 10 | Double jump (air jump) | OK | xGOK_BAS_JUMP_FRONT_01 | JumpAerialF <- GOK_BAS_JUMP_FRONT_01, JumpAerialB <- GOK_BAS_JUMP_BACK_01 |
| 11 | Fall | OK | xGOK_BAS_BUKUU_DOWN | (kept: 1 row(s) already played it) |
| 12 | Landing (ground) | OK | xGOK_BAS_JUMP_FRONT_02 | (kept: 2 row(s) already played it) |
| 13 | Shield | OK | xGOK_GRD_KAMAE | (kept: 3 row(s) already played it) |
| 14 | Shield break | OK | xCMN_DMG_UP_F | (kept: 5 row(s) already played it) |
| 15 | Roll / spot dodge / air dodge | PARTIAL | xGOK_BAS_STEP_F_S | (kept: 2 row(s) already played it) |
| 16 | Dizzy | GAP | (none) | - |
| 17 | Jab 1 (L1) | OK | xGOK_ATC_002 | (kept: 1 row(s) already played it) |
| 18 | Jab 2 (L2) | GAP | (none) | - |
| 19 | Jab 3 (L3) | GAP | (none) | - |
| 20 | Rapid jab | OK | xGOK_ATC_028 | (kept: 3 row(s) already played it) |
| 21 | Forward tilt | OK | xGOK_ATC_003 | AttackS3S <- GOK_ATC_003, AttackS3Hi <- GOK_ATC_003, AttackS3HiS <- GOK_ATC_003, AttackS3LwS <- GOK_ATC_003, AttackS3Lw <- GOK_ATC_003 |
| 22 | Up tilt | OK | xGOK_ATC_004 | AttackHi3 <- GOK_ATC_004 |
| 23 | Down tilt | OK | xGOK_ATC_020_S | (kept: 1 row(s) already played it) |
| 24 | Dash attack | WEAK | xGOK_ATC_011 | (kept: 1 row(s) already played it) |
| 25 | Forward smash | OK | xGOK_ATC_007 | AttackS4S <- GOK_ATC_007, AttackS4Hi <- GOK_ATC_007, AttackS4HiS <- GOK_ATC_007, AttackS4LwS <- GOK_ATC_007, AttackS4Lw <- GOK_ATC_007 |
| 26 | Up smash | PARTIAL | xGOK_ATC_004 | (kept: 1 row(s) already played it) |
| 27 | Down smash | OK | xGOK_ATC_012 | (kept: 1 row(s) already played it) |
| 28 | Neutral air | OK | xGOK_ATC_028 | AttackAirN <- GOK_ATC_028 |
| 29 | Forward air | OK | xGOK_ATC_006 | AttackAirF <- GOK_ATC_006 |
| 30 | Back air | GAP | (none) | - |
| 31 | Up air | OK | xGOK_ATC_025 | (kept: 1 row(s) already played it) |
| 32 | Down air | OK | xGOK_ATC_017 | AttackAirLw <- GOK_ATC_017 |
| 33 | Air landings | OK | xGOK_BAS_JUMP_FRONT_02 | (kept: 5 row(s) already played it) |
| 34 | Grab | OK | xGOK_NAG_TSUKAMI | (kept: 2 row(s) already played it) |
| 35 | Grab hold / pummel | GAP | (none) | - |
| 36 | Forward throw | OK | xGOK_ATC_SHOT_F | ThrowF <- GOK_ATC_SHOT_F |
| 37 | Back throw | OK | xCMN_DMG_BLOW_H_B | ThrowB <- CMN_DMG_BLOW_H_B |
| 38 | Up throw | PARTIAL | xGOK_ATC_004 | (kept: 1 row(s) already played it) |
| 39 | Down throw | PARTIAL | xGOK_ATC_012 | (kept: 1 row(s) already played it) |
| 40 | Thrown / captured by others | OK | xCMN_DMG_HEAD_L_F | (kept: 6 row(s) already played it) |
| 41 | Neutral B Kamehameha | KEEP | (none) | - |
| 42 | Side B Dragon Rush | KEEP | (none) | - |
| 43 | Up B Instant Transmission | GAP | (none) | - |
| 44 | Down B counter / ki charge | OK | xAPL_SPA_KTN_C | KiCharge <- APL_SPA_KTN_C |
| 45 | Ki volley | OK | xGOK_ATC_SHOT_N_LOOP | - |
| 46 | Ledge catch / wait | GAP | (none) | - |
| 47 | Ledge climb | GAP | (none) | - |
| 48 | Ledge attack / escape / jump | PARTIAL | xGOK_ATC_012 | (kept: 4 row(s) already played it) |
| 49 | Floor getups | OK | xCMN_BAS_DOWN_STAND_AOMUKE | (kept: 10 row(s) already played it) |
| 50 | Hit stun (hi / mid / low, ground+air) | OK | xCMN_DMG_BODY_L_F | (kept: 7 row(s) already played it) |
| 51 | Fly / tumble | OK | xCMN_DMG_TUMBLE_F | (kept: 5 row(s) already played it) |
| 52 | Wall / ceiling / ottotto | PARTIAL | xCMN_DMG_YOROKE_BODY_F | (kept: 2 row(s) already played it) |
| 53 | Taunt | OK | xCMN_BAS_HIRAMEKI | (kept: 2 row(s) already played it) |
| 54 | Entry | GAP | (none) | - |
| 55 | Victory / results pose | GAP | (none) | - |
| 56 | Rebound / parry | OK | xCMN_BAS_HAJIKI_F_00 | (kept: 1 row(s) already played it) |
| 57 | Miss foot / stamina-out | OK | xCMN_DMG_KUZURE | (kept: 1 row(s) already played it) |

## GAP / KEEP slots (no pick: the row keeps its current clip)

- 1 Idle [KEEP]: GOK_BAS_STAND_S (Sleep still ground STAND)
- 5 Run brake / stop [GAP]: BOOST_F_02 from f6 x0.75
- 8 Jump squat [KEEP]: JUMP crop
- 9 Jump (ground, forward/back) [GAP]: JUMP_FRONT_00 / JUMP_BACK_00 x0.33 (55f; owner: poor, punch list 9; queue 4: <= 40f)
- 16 Dizzy [GAP]: GOK_BAS_STUN_02
- 18 Jab 2 (L2) [GAP]: ATC_003 (BAC 301)
- 19 Jab 3 (L3) [GAP]: ATC_017 (BAC 302)
- 30 Back air [GAP]: CROSS-PORT Melee Luigi AttackAirB (owner: looks and works as intended)
- 35 Grab hold / pummel [GAP]: TSUKAMI held f22+ ; CMN_BAS_HAJIKI_B_00
- 41 Neutral B Kamehameha [KEEP]: xGOK_SPA_KMH
- 42 Side B Dragon Rush [KEEP]: BOOST_F_00 + STEP_F_S + ATC_013
- 43 Up B Instant Transmission [GAP]: xGOK_ESC_KUR_C
- 46 Ledge catch / wait [GAP]: JUMP_BACK_00 f12 authored lean
- 47 Ledge climb [GAP]: JUMP crouch crop, TransN path
- 54 Entry [GAP]: GOK_DEM_START 210f
- 55 Victory / results pose [GAP]: n/a

## Specials and controls

- Neutral B: Kamehameha tiers, unchanged. XV2 puts the ki blast on Blast tap; here it stays off Neutral B (the Kamehameha tap tier is the quick beam). The ki blast is the KiBlast state (combo package), fireable from the LAB moves list; the combo cancel Lx>Ki Volley still shoots it.
- Side B: the XV2 knockback attack (Heavy+Blast, BAC 419), the existing Rush row. `xCMN_BAS_UKEMI_F` is shelved as a tumble-exit candidate.
- Shield + B (stick neutral, inside the dead zone): Homing dash strike (XV2 BAC 476: BOOST_F_00 then ATC_008, 66 frames), combo route `Guard>Homing`, 20 ki. Owner 2026-10-11: shield + direction + B was too hard to input without rolling or spot dodging, so the route reads the stick as neutral and never competes with roll / spot dodge (jump out of shield is untouched). XV2 homes on the target; fighter Lua has no opponent query, so it dashes straight (recorded loss). Reuses the Rush Lua (the module is at the 24-function cap).
- Shield + Down B: nothing (the route `Guard>Vanish` was removed). Vanish is the Down B tap counter only.
- Down B tap: the vanish counter (Z-vanish). Down B hold: ki charge on `APL_SPA_KTN_C` (XV2 Energy Charge), only while ki < 100, ends at 100.
- Layout B (X-only jump, Y = ki blast) is owner-approved but waits for the `fighters[].controls` define format of `agent/css-controls` (docs/geno.md section 26) and a route input class for it.

## Evidence

Offline: `remake_hb.py check` ok (HB-NONE 30, HB-DESIGN 9 moves; combo states HB-NONE 6, HB-DESIGN 2; 30 routes); pytest `ports/goku-xv2/tests` 79 passed, 2 environment failures (test_host reads a `melee/` dir the worktree lacks). Ground audit: 144 rows, hover 78, anchored 66, BELOW the floor 0.
In game (muted, off-screen, combo package): `lua/specials_check.lua` SPECHECK PASS (homing, no homing at 5 ki, shield + direction rolls, shield + Down B does nothing); `kame_check` KAMECHECK PASS on the geno-10 package (on the combo package its hold-max case fires the Super at 100 ki by design); `second_match` PASS; `landing_check` 40 cases, 0 sinking; `pad_check` no leak; rewind over 120 frames across the homing strike: 0 bytes differ; native suite 397 of 397.
Owed: frame strips (the headless screenshot camera shows the stage, not the fighters; `lua/remake_strip.lua` + `tools/remake_strips.py` are in place for a run with a working camera), and every look-and-feel claim, for a human at a monitor.

## Phase 2 (2026-10-11, same branches)

- **HB-SAMPLE hitboxes** on every move that has XV2 hit data (21 moves + 6 combo states): see [REMAKE-SAMPLES.md](REMAKE-SAMPLES.md) for the derivation, the BDM-to-angle table, the damage formula and the per-move table. Three spheres along the leading limb's bone chain, tip strongest; a build fails if a sample sphere floats off its limb.
- **Combos are alive**: the jab string links on real hits (SAMPLECHECK: 4 links taken in one string, last route L3>L4); every route window is checked against its source move's active frames by `remake_hb.py check`.
- **Layout B**: Goku declares `controls` (docs/geno.md section 26): layout A (Melee buttons, default) and layout B (`"Y": "Down"`, X is then the only jump). The new combo input class `blast` is D-pad Down, so under layout B Y = ki blast; route `Blast>KiBlast` (ground idle / walk / run / dash / crouch / landing), **5 ki**. The D-pad itself fires it too. SPECHECK: `kiblast: KiBlast 39 ki 50.0 -> 45.0`, nothing at 2 ki. Air blasts are not wired (the state is a ground state).
- **Engine (game branch)**: Lua module cap 24 -> 48 functions (native test `geno-lua`: 40 load, 49 refused), combo input class `blast`.

## Phase 3 (2026-10-11): no hover, Up B is flight

Owner after playing phase 2: Up B is "whack"; Goku "still floats noticeably above the ground walking/running". New direction, superseding "always floating" and HOVER_Y.

- **Ground rows are grounded and planted.** `HOVER_Y` is deleted. Every standing ground row (idle, walk, run, dash, turn, crouch, landing, guard, rolls, ground attacks, grabs, throws, getups, taunt ...) uses a grounded XV2 clip and is **PLANTED**: `xv2_to_artist.py` shifts its pelvis track on every frame so the lowest skinned vertex is exactly on the floor. Gate: `ground_audit.py` fails a build with any planted row more than 0.6 model units off the floor on any frame (floating or sinking). Result: 95 planted rows, 49 anchored (aerial attacks, shield-break flight, ledge rows, items), below-the-floor rows 0, planted rows off the floor 0.
- Clip choices (grounded, from the owner's notes): idle / Sleep / Rebirth = `GOK_BAS_STAND` (was the floating `_S`); walk = `GOK_BAS_WALK`; run = `GOK_BAS_RUN`; **dash = the first 14 frames of the run cycle** (XV2 has no ground dash; the picked `BOOST_F_00` is a flight clip); turn = STAND with the authored 180 yaw, run-turn = RUN with the yaw; **run brake = STAND** (the boost brake is a flight clip; no ground skid exists); crouch / jump squat = the `GOK_BAS_JUMP` landing crouch crop; landing = `JUMP_FRONT_02` crop; shield = `GRD_KAMAE`; floor-wait rows = the ground `CMN_BAS_DOWN_*` (not `_S`). Rolls and dodges keep `STEP_*_S` (XV2 has no ground step clip) and are planted. Attacks keep the picks (some are flight-stance clips) and are planted too, so they stay on the floor.
- **Up B = flight** (XV2 BUKUU style). Takeoff (a grounded Up B leaves the floor with the script value AIR), then free steering with the control stick for 60 frames (0.8 units per frame at full stick, about 40 units: a Marth / Falcon sized recovery), clips `BUKUU_UP` / `BUKUU_F_S` / `BUKUU_B_S` by stick direction; stick at rest climbs slowly. **10 ki**; with less, a weak 22-frame flight at 0.45 speed. B or A ends it early. The end is the special fall (helpless, the usual landing lag), so he stays edgeguardable; the special fall catches ledges as retail does, and the flight states are `geno.air` states with the air collision (ledge grab applies while falling). All motion is Lua velocity from slots (`age`, `fly`, `pose`), so rewind, savestate and netplay replay it. Instant Transmission (the old Up B) stays defined but is no longer bound.
- No attack out of flight (skipped on purpose).
