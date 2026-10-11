# Goku's Kamehameha (neutral B), rework of 2026-10-10

Owner brief: the old one was a ball projectile with a trail ("really lame"). This is a charge you can store, then a **sustained
multi-hit beam** from the hands. The gameplay (sections 1, 2, 5, 6) is our own design with Melee-scaled numbers, re-tunable in
`tools/gen_kame.py` (hit and beam numbers) and `lua/goku.lua` (charge rules, damage scaling, recoil).

**2026-10-10, second pass (`ws/goku-kame-xv2`): the presentation is now XV2's own.** The owner saw the first rework and asked for a direct
port of Goku's Xenoverse 2 Kamehameha: its effects (charge ball, beam, impact particles) and its voice and sound effects. Section 3 describes
what replaced the invented look; the full inventory (BAC entries, BSA, EEPK, textures, ACB cues) and every approximation are in
`_research/xv2-kamehameha-2026-10-10.md`. **XV2 data is never committed**: the converters (`tools/xv2_fx.py`, `tools/xv2_audio.py`, and the extractors
`tools/xv2x/`) read the local game install and write git-ignored `_build/` outputs, exactly like the Goku model. The invented effects
(`tools/fx_build.py`'s `P_TrailGokuKame*`) and synthesised sounds (`tools/kame_audio.py`) stay in the tree as the fallback when the local conversion is absent.

Branches: workspace `ws/goku-kamehameha`, game `agent/goku-kamehameha` (no engine change was needed; the game lane only has the
untouched build used to run it).

## 0. Charge, native model (2026-10-10, owner: "doesn't behave like Mewtwo or Samus charges at all"); supersedes the hold-to-charge rules below

Press B **once**: the move starts (10 frames of Start, no input), then the loop charges **by itself**, half a unit a frame (60 units = full, about 130 frames after B;
traced: retail Samus reaches full 133 frames after B, Mewtwo 137). In the loop, in the natives' order (`ftSs_SpecialNHold_IASA`, `ftMt_SpecialNLoop_IASA`): a stick/C-stick flick
rolls (`ftCo_8009917C`, new Lua target `ctx.go("roll")`), B fires at the current level, L/R stores and leaves (state `KameStore`, 9 frames with a flash; natives' Cancel is 8). **Jump and
spot dodge do not cancel in either native** (no branch in either IASA; traced: Samus and Mewtwo keep charging when X is pressed), so Goku does not either. On the ground, **full auto-stores**
(Samus `ftSs_SpecialNHold_Anim`: x2230 >= x18 -> Cancel holding the level). B with a stored charge: full fires at once, partial resumes from the level. **Air** follows Mewtwo
(`ftMt_SpecialAirNLoop_*`): it charges, B / L/R work, no roll, and at full it waits (no auto-store). Samus's air B fires at once instead; Mewtwo is closer because the Kamehameha is aimed
and charging it is the point. A hit wipes a partial stored charge, a stored full one survives (owner). The level is kept in `stored` every frame, so a roll, a cancel or a hit never loses it.
Traces (retail Samus | retail Mewtwo | Goku, tap, shield at 30, roll, jump, full, fire from stored): `tools/kame_traces.py` -> `_build/xv2-kame/traces/*.txt`; summary in the research note.

## 0b. The chant tiers (2026-10-10, owner: each syllable raises the tier, each tier looks and behaves differently); supersedes the Tap/Mid/Full table in section 2

XV2's chant "ka-me-ha-me" (VOX cue 0, BDB_GOK_071, 0.905 s) is cut at its energy minima into four syllables (`tools/xv2_audio.py`, `SYLLABLES`: 0-0.205, 0.205-0.325, 0.325-0.51, 0.51-0.905 s)
and spread across the charge; the release plays the "HA!" (cue 1). A syllable's onset raises the tier. Frames are counted from the B press (state start); the charge runs 1 unit per 2 frames after
10 frames of Start (60 units = 130 frames = auto-store on the ground).

| tier | reached at | voice trigger / heard | charge units | release state | startup (frames after B fires) | beam (game frames) | spheres (radius / reach, model units) | drag hit | finisher | pushes Goku back | look (XV2 package) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | B at ages 11 to 19 | before "ka" is finished | 0-4 | `KameTap` | 5 | 8 | 2.0 / 16 | 1.0% fixed kb 8, 4 stun | 2%, 55 deg, kbg 40 bkb 20 | 0.3 | `P_TrailGokuXKameTap`: small head, no muzzle |
| 1 | "ka" said, age 20 | 7 / ~12 to 19 | 5 | `KameThin` | 6 | 20 | 2.4 / 21 | 1.1%, kb 7 | 3%, 55 deg, kbg 50 bkb 25 | 0.6 | `...Thin` head x2.6 |
| 2 | "me" age 44 | 44 / 44 | 17 | `KameMid` | 6 | 28, 6 hits | 3.2 / 25 | 1.0%, kb 8, 6 stun | 4%, 45 deg, kbg 80 bkb 35 | 0.9 | `...Mid` x3.5 + muzzle |
| 3 | "ha" age 80 | 80 / 80 | 35 | `KameFull` | 8 | 40, 8 hits | 4.2 / 32.5 | 1.2%, kb 8, 6 stun | 7%, 40 deg, kbg 90 bkb 50 | 1.2 | `...Full` x4.6 + muzzle |
| 4 | last "me" age 114 | 114 / 114 | 52 | `KameMax` | 10 | 50, 10 hits | 5.4 / 42 | 1.3%, kb 8, 6 stun | 10%, 38 deg, kbg 95 bkb 60 | 2.0 | `...Max` x5.8 + muzzle x1.6 |
| Super | tier 4 + full 60 units + ki 100 | its own 4 syllables compressed into 54 frames | 60 | `KameSuper` | 54 | 60 | 6.0 / 46 | 2.2% | 16%, 40 deg, kbg 80 bkb 60 | 1.6 | `P_TrailGokuXKameSuper*` |

Drag-hit damage is scaled by the charge units as before (x(0.8 + 0.4 x units/60)). Numbers live in `tools/gen_kame.py` (`TIERS`), `lua/goku.lua` (thresholds `T1..T4`, recoil) and `tools/xv2_fx.py` (`TIERS`). The charge visuals step with the chant:
`P_TrailGokuXKameCharge` grows its ball at animation frames 20 / 44 / 80 / 114 (x0.45 / 0.65 / 0.85 / 1.1 of full) with a bigger CrgON flash each time, and the aura (`P_TrailGokuAura`) is re-attached larger at
44 / 80 / 114 (x1.3 / 1.6 / 2.0). Storing (shield, or the auto-store) enters `KameStore1..4` for the tier reached, each a 9-frame flash at that tier's ball size (`P_TrailGokuXKameStore1..4`); a stored
tier 4 fires on the next B and survives a hit, a partial tier is wiped by one. Look parameters for the engine FX lane: `python ports/goku-xv2/tools/xv2_lane_params.py` -> `_build/xv2-kame/fx/lane_params.json`
(ribbon width/alpha/colour curves and scroll speeds, glare materials, camera events); the per-tier suggestions are in the research note, "Parameters for the FX lane".

## 0c. The 10 second charge and the integrated look (2026-10-10, owner: "like 10 seconds for max charge or something dumb"); supersedes the timings in 0 and 0b

**One tunable**: `CHARGE_FRAMES = 600` in `lua/goku.lua` (a charge unit every `CHARGE_FRAMES / 60 = 10` frames) and the same constant in `tools/gen_kame.py` (voice and hum schedule);
`tools/xv2_fx.py` `CHANT_AT` / `BALL` hold the effect beats. Input is unchanged (B once starts, B fires the current tier, L/R stores keeping it, a flick rolls). **Full charge holds forever, on the ground and in the air, like Mewtwo's `LoopFull`: there is no auto-store** (supersedes the auto-store in sections 0 and 0b; KAMECHECK holds a full charge for 25 s and still fires it).

| beat (state frame / seconds) | syllable | tier reached | unit | what steps |
|---|---|---|---|---|
| 0-60 (first second) | (hum starts) | 0 Tap: B before "ka" fires a quick blast | 0-4 | ball 0.25 -> 0.45, first gathering ring |
| 60 / 1 s | "ka" (voice trigger at 55: the clip has 5 frames of silence) | 1 Thin | 5 | ball and aura step, flash, ground ring 1, hum 70 -> 76 |
| 180 / 3 s | "me" | 2 Mid | 17 | step, ground ring 2, hum rises one pitch step (x1.15) |
| 360 / 6 s | "ha" | 3 Full | 35 | step, ground ring 3 (wider), hum x1.32 |
| 540 / 9 s | last "me" | 4 Max | 53 | step, ground ring 4, shake starts building (0.006 then 0.010), tiny flash, hum x1.52, ring period 9 frames |
| 600 / 10 s | | full (60 units): the charge holds here indefinitely (no auto-store); B fires Max, or Super if ki is 100 | 60 | |

Between beats the ball (`P_TrailGokuXKameCharge`, XV2 Kmh_Crg) keeps growing (10 size steps), the gathering rings (engine ring + dissolve) contract faster at each tier, flat
pressure rings (`P_TrailGokuXKamePressure`, bound to the floor joint) leave the feet at each beat and pulse in between, the motes are soft particles, and the aura is re-attached
larger at each beat. The charge state's effects run on the state frame clock (`"clock": "game"`); its clip is stretched (ANIM_RATE 0.114 from clip frame 20) so it does not loop and
restart the script before 17 s. The hum is XV2's charge SE resampled up in three steps (`GnKameHum2..4`, ids 200133/36/39), re-triggered with rising level.

Rebalance (owner-approved 2026-10-10: Max finisher 15, Super 24; tiers 0-3 are unchanged; the 10 / 16 in 0b are superseded):

| tier | drag hit (x charge scale) | finisher | knockback growth / base | pushes back |
|---|---|---|---|---|
| 0 Tap | 1.0 | 2 | 40 / 20 | 0.3 |
| 1 Thin | 1.1 | 3 | 50 / 25 | 0.6 |
| 2 Mid | 1.0 | 4 | 80 / 35 | 0.9 |
| 3 Full | 1.2 | 7 | 90 / 50 | 1.2 |
| 4 Max (was 1.3 / 10 / 95 / 60) | 1.7 | 15 | 105 / 70 | 2.0 |
| Super (was 2.2 / 16 / 80 / 60) | 2.6 | 24 | 90 / 70 | 1.6 |

Look per tier (`tools/xv2_fx.py` `LOOK`): the beam is native ribbon layers bound to the SAME joint (hand.R), emitter rotation and direction D as the hit spheres, from the hand to
the head dome: Tap core only; Thin glow + core; Mid + streaks and one head ring; Full + cloud, XV2's second ribbon set and two rings; Max the third set (widest/longest), white-hot
core, three dissolve rings, the stronger muzzle, shake 0.028 x 24 and a 0.15 flash; Super its own packages (CKM ribbons, Bas x2.5) with shake 0.032 x 36 then 0.05 x 70 (the
camera clip GOK_CAM_CKM_C moves 1.6 / 0.4 / 5.0 m over 225 frames; approximated as two decaying shakes) and a 0.2 flash. The release flash is faint and short everywhere else
(Mid shake only, Full 0.05 x 2 frames, Tap/Thin none): the muzzle dome is 8 frames at alpha 0.42.

Approximations (see also the research note): XV2's width over segment AGE (comet tail: core 0.69 m -> 0.2 at 11 f -> 0.05 at 18 f) is mapped to a width curve over the strip position
(`width_keys`, age = (1 - position) x 22 frames) and floored at 42 % of the head width so the beam never pinches off before the hands; XV2's alpha fade over age is not applied at
the hand end (only the head end eases out); XV2's Kmh_Ring is a custom polygon band (ShapeDraw) approximated by the engine ring; the camera clip is two shakes, not the moving camera.

## 1. Charge: modelled on Samus Charge Shot and Mewtwo Shadow Ball

Read from the decomp (`src/melee/ft/kinds/ftSamus/ftsamusspecialn.c`, `.../ftMewtwo/ftmewtwospecialn.c`, items
`it/kinds/itsamuschargeshot.c`, `itmewtwoshadowball.c`). The numbers (frames per step, max level, damage) are read from the
character `.dat` at run time and the `.dat` is not in the repo, so the table gives the rule, not the figure.

| | Mewtwo Shadow Ball | Samus Charge Shot | Goku Kamehameha |
|---|---|---|---|
| states | Start, Loop, LoopFull, Cancel, End; the same set in the air (`MT_MS_*`, `forward.h:47-56`) | Start 343, Hold 344, Cancel 345, Fire 346; air has only Start 347 and Fire 348 (`ftsamus.c:54`) | one charge state (ground and air), then Tap / Mid / Full / Super release states |
| charge counter | `u.mt.x2234_shadowBallCharge`, +1 per `CHARGE_ITERATIONS + 1` frames (`MT:536-580`) | `u.ss.x2230`, +1 per `x20 + 1` frames (`SS:193-231`) | Lua slot `charge`, +1 per frame, 60 = full (4 steps of 15); `stored` keeps it |
| max / at max | `CHARGE_CYCLES`; LoopFull, **no auto-fire**, waits for A or B (`MT:896`) | `x18`; drops to Cancel holding the charge (`SS:223-231`) | 60 frames; stays in the loop at full size, **no auto-fire** (Mewtwo) |
| fire input | B, or A, pressed (B needs `releaseLag <= 0`) | B pressed again in Hold | B **released** (hold style, as before), or A pressed (Mewtwo) |
| store / cancel, ground | shield (L/R) -> Cancel keeps the level; stick-flick roll (`ftCo_8009917C`) removes the ball, keeps the level | L/R -> Cancel keeps the level; flick roll cancels, keeps the level | shield (L/R, pressed) keeps the level at any level. **Roll cancel not built** (`ctx.go` only reaches Geno states or auto) |
| store / cancel, air | L/R -> AirCancel; no roll test in the air | none: air B fires the stored level at once | shield (L/R) keeps the level (Mewtwo) |
| jump, spot dodge | not accepted | not accepted | not accepted (same as both) |
| stored level lives in | `u.mt` (fighter union), kept across ground/air | `u.ss`, kept across ground/air | Lua block (a game global: snapshotted, hashed, rollback-safe), kept across ground/air |
| B with a stored charge | full: skips the loop, fires (`MT:466-500`); partial: resumes from the level | full: Start goes to Fire (`SS:170`); partial: resumes | full (60): fires on the B press (`charge_enter` -> release); partial: resumes from the level, fires on release |
| a hit while stored | wipes unless at max (`ftMt_SpecialN_OnDeath`, installed on the SpecialN states) | wipes (`ftSs_SpecialN_80129258`, on take-damage and death) | percent rose since it was put away -> a partial charge is wiped, a **full one survives** (Mewtwo rule); a hit while charging leaves the state, so the next B starts from 0 |
| KO | zeroed (`ftMt_Init_OnDeath`) | zeroed (`ftSs_Init_OnDeath`) | the Lua block is zeroed with the fighter (`Geno_FighterReset`); **not exercised in a stock loss** (owed) |
| air entry | halves vertical speed (`MT:455`) | none (air B fires) | halves vertical speed (`charge_enter`) |
| ledge | walking off while charging: Samus Hold goes to Fire in the air (`SS:354`); Mewtwo maps ground to air states | same | the state is `geno.ground`/`coll: both`: it follows the floor under it into the air with the charge kept; no special ledge rule |
| visible indicator | held ball scaled by level/max, effects at 25/50/75% and max | orb scaled by level/max, full-charge effect (efSync 0x480/0x481) | ki ball between the cupped hands, grows over the 60 frames (`P_TrailGokuKameCharge`), a white flare + chime at every 15-frame step, sparks drawn in, ki aura (`P_TrailGokuAura`) |
| charge sounds | `ft_80088510` 4 steps (200121..200130) | 5 steps (`ftSs_Unk3_803CE6B8`) | four own synthesised steps (`tools/kame_audio.py`), played by the script at 15/30/45/60 |
| release startup | script-driven (`.dat` subaction) | script-driven | Tap 5, Mid 6, Full 8 frames after the state starts (Super 54: the charge pose is in the state) |
| endlag | `x14 LANDING_LAG` special-fall in the air | `x24` special-fall in the air | about 15 / 25 / 35 frames after the final hit (Tap / Mid / Full); air: falls at the end |
| recoil | `gr_vel = -facing * x4 * level`, air `x8 * level` | air only: `self_vel.x = facing * x1C * level` | step back 0.6 / 0.9 / 1.2 / 1.6 on release; in the air the body **hovers** while the beam lasts and then falls |

Where Goku deliberately differs: hold-to-charge and release-to-fire (the owner asked for "hold B"; Samus and Mewtwo charge
without holding), and the beam.

## 2. Release: tiers, frame data, numbers

The charge picks the tier when B is released (or A pressed): **Tap** < 15, **Mid** 15-44, **Full** 45-60, **Super** = 60 and ki >= 100
(ki exists only in the combo package; `lua/goku.lua` has the `-- @KI` line). The beam is **four hit spheres along the hands**
re-hitting every 5 frames (drag hits: fixed knockback, extra hitstun, no hitlag so the beam keeps its rhythm), built out over the
first 3 clip frames, then a **launching final hit** when the beam ends. The pose is held by slowing the animation
(`ANIM_RATE`) during the beam, so "locked in the firing pose" is the clip itself, with a recoil step.

| | Tap | Mid | Full (60 = max) | Super |
|---|---|---|---|---|
| charge to pick it | < 15 | 15-44 | 45-60 | 60 + ki 100 |
| startup (state start to first hitbox) | 5 | 6 | 8 | 54 |
| beam length (game frames) | 14 | 28 | 40 | 60 |
| hit radius (world; model units x1.43) | 3.4 | 4.6 | 6.0 | 8.6 |
| reach from the hand (world) | 33 | 40 | 52 | 74 (final hit +7) |
| drag hit, every 5 frames: base damage x(0.8 + 0.4 x charge/60) | 1.2 (1.0 at charge 6) | 1.0 | 1.2 (1.36 at 50, 1.44 at 60) | 2.2 |
| drag hit knockback | fixed 8, kbg 60, +5/6 stun frames, no hitlag | same | same | same |
| final launching hit (5 frames, spheres 5 units further out) | 3%, 50 deg, kbg 60 bkb 25 | 4%, 45 deg, kbg 80 bkb 35 | 7%, 40 deg, kbg 90 bkb 50 | 16%, 40 deg, kbg 80 bkb 60 |
| total length (state frames, measured) | 41 | 64 | 87 | ~127 |
| measured on a Mario 24-34 units away, FD, every hit landing (hits / damage, staling included) | 5 / 5.0% | 7 / 11.6% | 11 / 22.9% (50 held); 11 / 22.8% (62 held) | 11 / 31.7% (ki gate forced in a built copy) |

The 50-frame and 62-frame Full beams do the same total here because staling (the second beam in a row is staled) cancels the 6%
higher drag damage; the live drag-hit damage the check reads is 1.36 and 1.44.

Balance reading: a Full beam that lands every hit does 22.9%, a little under a full Samus Charge Shot (25%), over 87 frames of
commitment, and only a victim who stays in the beam takes every hit (the drag pushes it forward about 2 units a hit and the
final hit meets it at the end: hit frames spread over about 45 frames). Shield interaction was not tested. It is punishable on whiff (about 35 frames after the Full beam, 87 in all), and it is a charge: the safe use is the Tap/Mid beam as a zoner, the Full beam as a commit. Super is above both
by design (ki 100 is a full meter).

Beam angle: **straight along the facing** this pass. A stick-angled beam (up/down, like Sora's `geno.aim_stick`) would need the
body to turn with it, which hitbox offsets in the hand frame cannot do; it is an owner decision (section 6).

## 3. Visuals and sound (XV2's own, converted locally; cosmetic, rollback-safe)

The effect packages are Geno effect IR (`melee/docs/geno.md` section 20) written by `tools/xv2_fx.py` from the local XV2 dumps. They only read the
fighter's joint matrix and the state clock, never write gameplay state, and the effect runtime re-simulates on rollback. Bound in `tools/build.py` (`FX_STATES`).

* **Charge** `P_TrailGokuXKameCharge` (`KameCharge`, `hand.R`): XV2 effect 0: `Kmh_Crg` (the ball's sprite stack; stepped up x0.4 / 0.6 / 1.0 at charge frames
  0 / 20 / 40 like XV2's x0.4 / 0.6 / 1.0 repeats), `Kmh_CrgON` (the flash at each 15-frame step), `Kmh_tsubu` (motes); drawn without depth test.
* **Muzzle** `P_TrailGokuXKameMuzzle` (release): `Kmh_Fire.emo`, the flare dome.
* **Beam** `P_TrailGokuXKameTap|Mid|Full` (release): the XV2 beam is a projectile head with trail ribbons, and so is this: three scrolling ribbons from the hand
  to the head (`Kmh_Beam.etr`: beam00 white core, ring_beamCor blue streaks, T2_UV01 cloud), the head (`Kmh_Bas.emo` dome and shells with the UV-scroll and colours of
  their material rows, `Kmh_Hand.emo` ball, both with their `obj.ema` pose) and the head particles (`Fireptcl`, `4ptcl`, `LineAll`, `Wav`). One scale per tier makes the
  head as wide as the hit sphere (Tap 2.6, Mid 3.5, Full 4.6 model units per XV2 metre).
* **Super** (`KameSuper`): `P_TrailGokuXKameSuperCharge`, `...SuperMuzzle`, `...Super` from skill `ULT/000_GOK_CKM` (Bas x2.5, Hand x0.9, ribbons from `Ckm_Beam.etr`, particles
  Tail / Wav / Last / FireLine / 4ptcl / LineAll), scale 3.2.
* **Direction** is measured, not guessed: `tools/kame_geom.py` records the hand frame's world axes (a hitbox probe) and the beam direction in it; the hit spheres and
  the effects use the same vector.
* **Voice and SFX**: `tools/xv2_audio.py` converts Goku's own lines and the skill SEs from the game's ACBs (Japanese default, `--lang en` for English) to `.gnsnd`;
  `build.py` ships them as `audio.voice` rows on Mewtwo's Shadow Ball ids (Goku never plays them). The charge starts the "ka-me-ha-me" line and the charge SE (BAC frame 0),
  the release plays the shout and the shot SE (BAC frame 58, two frames after the projectile). The old 15-frame chimes are gone. Log: `Goku: plays its own voice line (GnKameVoxCharge.gnsnd)`.
* **Not done / approximated**: the shock-ring bands (`ShapeDraw`) are dropped, dynamic lights, camera shake and the refraction ribbon are not converted, `Vortex` and
  position-curve modifiers are not mapped, the BasB length pulse is not played; see the research note's list. Screen shake / flash still need an engine hook.

The old article projectiles (`KameTap/Mid/Full/Super`, `KameOrb`) stay declared in `gameplay.json` (article indices are shared with
`combo_apply.py` and the engine tables) but nothing spawns them any more.

## 4. How it is built and run

```
python ports/goku-xv2/tools/gen_kame.py        # the five move scripts (numbers in the table at its top)
# the XV2 conversion (local data only; needs the game install, see the research note):
dotnet build tools/xv2x/audio/Xv2Audio.csproj -c Release -o _build/xv2-kame/audio/tool   # then Xv2Audio list|get|acb fills _build/xv2-kame/audio/wav
dotnet build tools/xv2x/fx/Xv2Fx.csproj -c Release                                       # Xv2Fx emb|emo|emp|etr|ema|emm, then python -I tools/xv2x/fx/dds2png.py
python ports/goku-xv2/tools/xv2_audio.py [--lang en]   # the voice and SFX -> _build/goku-xv2/audio (.gnsnd)
python ports/goku-xv2/tools/xv2_fx.py                  # the effect packages -> _build/goku-xv2/fx/P_TrailGokuXKame*
python ports/goku-xv2/tools/kame_audio.py      # (fallback) synthesised sounds
python ports/goku-xv2/tools/fx_build.py        # (fallback) the invented effect packages
python ports/goku-xv2/tools/build.py --gameplay-only --no-audit --fighter _build/goku-xv2/author-source/fighter.json
python ports/goku-xv2/tools/kame_run.py kame_check KAMECHECK --turbo     # the headless gate (needs GW_MELEE / GW_BUILD_ROOT / GW_FIGHTERBUILD)
python ports/goku-xv2/tools/kame_run.py kame_shots KAME --cfg hold=62  # frame strips (offscreen); --cfg tag= gap= camx= camz= dist= air=1 tail=
python ports/goku-xv2/tools/kame_try.py --tag NAME --every 3 [--super]   # regenerate the XV2 effects, copy them into the built package, shoot, tile a contact sheet
                                                                         # (_build/xv2-kame/sheets/NAME.png); --super runs a package copy whose full charge fires the Super
```

`kame_check.lua` asserts: the beam multi-hits (Mid >= 2, Full >= 3), damage and beam length rise with the tier, a 60-frame
charge hits harder than 45, Full is under 30%, the air beam hovers, shield stores the level, B resumes it, a stored full charge
fires on the B press, a hit wipes a partial charge, and `gd.rewind_test(120)` across charge, release and beam reports 0
differing bytes.

To try it in the LAB (visible, the owner's machine, after merging or from this worktree's package):

```powershell
$env:MELEE_MODS_DIR = 'E:\Projects\Melee Workspace\worktrees\kamexv2\_build\goku-xv2\author-source\package\mods'
$env:MELEE_SCENE = 'mode=lab;p1=geno:goku-xv2/hu;p2=mario/cpu0;stage=fd;items=off;time=0'
$env:GW_MELEE = 'E:\Projects\Melee Workspace\worktrees\kamexv2-game'; $env:GW_BUILD_ROOT = 'E:\Projects\Melee Workspace\_build\agents\kamexv2'
& 'C:\Program Files\Git\bin\bash.exe' 'E:\Projects\Melee Workspace\tools\port\run.sh' --realtime kame-try --iso $env:GW_ISO_VANILLA
```

XV2's own body clip, held in place in the LAB's CLIPS page: `& 'E:\Projects\Melee Workspace\worktrees\kamexv2\ports\goku-xv2\tools\clips.ps1' xGOK_SPA_KMH` (the script points at the main workspace's package unless `MELEE_MODS_DIR` is set first).

Hold B (neutral special), release to fire; shield while charging stores it; B again resumes or fires a full one.

## 5. Known limits

* The Super Kamehameha needs the ki meter (combo package); here it was exercised by forcing the full-charge route in a built copy
  of the Lua, so its real gate (ki >= 100) is untested in this lane.
* The charge ball's placement between the hands is approximate (hand.R origin + a small offset; the pose hides it behind the body,
  so it is drawn over the body). It needs the owner's eye.
* Resuming a stored charge replays the ball's growth from small (the effect has no input from the charge slot) and the step
  chimes replay from 15 again.
* The beam's visual end and the hit spheres' reach agree (52 world for Full) but the glow's soft outer band looks like a slab
  from some angles; both facings use the same hand-frame math (not both-facing screenshotted).
* A KO resetting the stored charge was not exercised.

## 6. Owner decisions

1. **Super Kamehameha at ki 100** is kept; its tier numbers (16% final, 2.0 per drag hit) are above Full on purpose. Keep, or tone down?
2. **Hold-to-charge, release-to-fire** (as before) vs Samus/Mewtwo's "tap, charge on its own, B again fires". The store/resume rules
   work either way; the second needs a small Lua change.
3. **Stick-angled beam** (up/down): needs an engine/skeleton option or a set of angled release states (3 more clips of rows through
   the artist pipeline). Not done.
4. **Screen shake / flash on full release**: needs a small engine hook (a script-driven `camera_shake` for fighter scripts).
5. **Roll-cancel** while charging (both natives have it on the ground): needs `ctx.go` to reach the common roll states.
6. Whether a **hit should wipe a stored full charge** (Samus does; Mewtwo keeps a full one; this build keeps it).

### 0d. Retail check and open notes (2026-10-10)

- Retail Mewtwo (decomp plus engine traces): no jump cancel at any charge frame (X, Y, up at 10/25/40/80/140 stay in `SpecialNLoop`/`LoopFull`); an air charge that lands becomes the ground loop keeping the charge; no cliff catch in the Mewtwo SpecialN Coll callbacks. Goku matches: no jump cancel, no ledge grab out of the charge. Ledge/takeoff traces were inconclusive; the owner's report of a jump or ledge cancel is unconfirmed (owner question pending).
- The Max hold hum goes silent after about 17 s (the script clip freezes at a very low rate); a true looping hold hum needs a new Geno state and is not built.
- The XV2 ki-charge aura (common EEPK) is not ported: no dump of it exists locally.
