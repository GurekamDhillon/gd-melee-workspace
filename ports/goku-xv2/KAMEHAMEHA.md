# Goku's Kamehameha (neutral B), rework of 2026-10-10

Owner brief: the old one was a ball projectile with a trail ("really lame"). This is a charge you can store, then a **sustained
multi-hit beam** from the hands with an authored bright core and glow. Everything here is our own design and our own effects;
no XV2 or Nintendo data is in it. Numbers are Melee-scaled design values, all re-tunable in `tools/gen_kame.py` (hit and beam
numbers), `lua/goku.lua` (charge rules, damage scaling, recoil) and `tools/fx_build.py` (the look).

Branches: workspace `ws/goku-kamehameha`, game `agent/goku-kamehameha` (no engine change was needed; the game lane only has the
untouched build used to run it).

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

## 3. Visuals (our own, cosmetic, rollback-safe)

`tools/fx_build.py` writes the effect packages (Geno effect IR, `docs`: `melee/docs/geno.md` section 20). They only read the
fighter's joint matrix and the state clock, never write gameplay state, and the effect runtime re-simulates on rollback.

* **Charge ball** `P_TrailGokuKameCharge`, bound to `KameCharge` on `hand.R`: one long-lived glow + white core that grows over the
  60 charge frames and then holds, four step flares at 15/30/45/60 growing in size, sparks drawn inward. Drawn without depth
  test because the cupped hands sit behind the body in the pose.
* **Beam** `P_TrailGokuKameTap|Mid|Full|Super`, bound to the release states on `hand.R` at the frame the hands thrust: three mesh
  cylinders (outer glow, body, white hot core) that grow out to the beam length in 3-6 frames and close at the end, a muzzle
  flare, a tip flare (the impact flare; it sits at the beam's end, it does not move with a hit), a spark burst at the tip, and
  sparks streaming down the beam. Full and Super add a muzzle flash at release.
* **Direction** is measured, not guessed: `tools/kame_geom.py` records the hand frame's world axes (a hitbox probe) and the
  beam direction in it; the hit spheres and the effect meshes use the same vector.
* **Audio**: `tools/kame_audio.py` synthesises the sounds (nothing sampled) and `build.py` ships them as `audio.voice` rows on
  Mewtwo's Shadow Ball sound ids, which Goku never plays otherwise (log: `Goku: plays its own voice line (GnKameStep1.gnsnd)`).
* **Not done**: screen shake and full-screen flash on the full release (fighter scripts have no camera command; `gd.camera_shake`
  is a gameplay-script API), the impact flare following the victim, angled beams, a dedicated "HA!" voice.

The old article projectiles (`KameTap/Mid/Full/Super`, `KameOrb`) stay declared in `gameplay.json` (article indices are shared with
`combo_apply.py` and the engine tables) but nothing spawns them any more.

## 4. How it is built and run

```
python ports/goku-xv2/tools/gen_kame.py        # the five move scripts (numbers in the table at its top)
python ports/goku-xv2/tools/kame_audio.py      # the sounds -> _build/goku-xv2/audio
python ports/goku-xv2/tools/fx_build.py        # the effect packages
python ports/goku-xv2/tools/build.py --gameplay-only --no-audit --fighter _build/goku-xv2/author-source/fighter.json
python ports/goku-xv2/tools/kame_run.py kame_check KAMECHECK --turbo     # the headless gate (needs GW_MELEE / GW_BUILD_ROOT / GW_FIGHTERBUILD)
python ports/goku-xv2/tools/kame_run.py kame_shots KAME --cfg hold=62  # frame strips (offscreen); --cfg tag= gap= camx= camz= dist= air=1 tail=
```

`kame_check.lua` asserts: the beam multi-hits (Mid >= 2, Full >= 3), damage and beam length rise with the tier, a 60-frame
charge hits harder than 45, Full is under 30%, the air beam hovers, shield stores the level, B resumes it, a stored full charge
fires on the B press, a hit wipes a partial charge, and `gd.rewind_test(120)` across charge, release and beam reports 0
differing bytes.

To try it in the LAB (visible, the owner's machine, after merging or from this worktree's package):

```powershell
$env:MELEE_MODS_DIR = 'E:\Projects\Melee Workspace\worktrees\kame\_build\goku-xv2\author-source\package\mods'
$env:MELEE_SCENE = 'mode=lab;p1=geno:goku-xv2/hu;p2=mario/cpu0;stage=fd;items=off;time=0'
$env:GW_MELEE = 'E:\Projects\Melee Workspace\worktrees\kame-game'; $env:GW_BUILD_ROOT = 'E:\Projects\Melee Workspace\_build\agents\goku-kamehameha'
& 'C:\Program Files\Git\bin\bash.exe' 'E:\Projects\Melee Workspace\tools\port\run.sh' --realtime kame-try --iso $env:GW_ISO_VANILLA
```

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
