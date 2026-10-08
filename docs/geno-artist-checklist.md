# Geno animation checklist

What to animate, in what order, and what is safe to leave as a placeholder. The per-row tables (all 351 engine rows, their tiers, fallbacks and the
move timing) are generated: `docs/geno-artist-rows.md` (`python -m tools.geno.artist clips`). Rules behind each line are in `docs/geno-artist-spec.md` section 10.

Placeholders are never silent: the validator counts them, the build report (`build/build-report.md`) lists every row that plays a borrowed clip and which one,
and `PADDED` tells you which borrowed clips were held on their last pose so the move script is not cut short.

## 1. Minimum for a playable prototype (11 clips)

Name each action exactly like the row. Everything else falls back to these (or to `Wait`).

| action | frames (typical) | loop | what the game does with it |
|---|---|---|---|
| `Wait` | 48-90 | loop | idle. **Mandatory**: it is the final fallback for every row without a clip |
| `WalkMiddle` | 28-40 per cycle | loop | walk; also `WalkSlow`/`WalkFast`. Planted foot must slide-free: the importer measures its speed |
| `Run` | 16-24 per cycle | loop | dash/run (`Dash`, `RunDirect`, `RunBrake` borrow it) |
| `JumpF` | 12-16 | once | the jump (`JumpB` borrows it); `KneeBend` (pre-jump squat) borrows `Wait` |
| `JumpAerialF` | 20-30 | once | the double jump (`JumpAerialB` borrows it) |
| `Fall` | 12-20 | loop | falling (`FallF/B`, `FallAerial*`, `FallSpecial*` are safe aliases of it) |
| `Guard` | 10-16 | loop | shield held (`GuardOn`, `GuardOff`, `GuardSetOff`, `GuardReflect` borrow it) |
| `Attack11` | 13+ | once | jab. Strike pose on **frame 3**, length at least **13** |
| `Catch` | 10+ | once | the grab. Reach pose on **frame 6**, length at least 9 |
| `CatchWait` | 20-30 | loop | holding the victim |
| `ThrowF` | 14+ | once | the forward throw (back/up/down borrow it). Release at frame 13 |

Recommended next (a first play session reaches them within seconds): `Landing`, `Turn`, `KneeBend`, `GuardOn`, `GuardOff`, `Squat`, `SquatWait`,
`DamageN1`, `DamageFlyN`, `EscapeF`, `EscapeB`, `EscapeN`, `AttackDash`, `AttackS3S`, `AttackHi3`, `AttackLw3`, `AttackAirN`, `AttackAirF`, `ThrowB`, `ThrowHi`, `ThrowLw`, `CatchAttack`, `Dash`.

## 2. A finished fighter

All rows tagged `finished` in `docs/geno-artist-rows.md` (136 rows): the full normal/aerial/smash set, every damage and knockback state, down/getup/roll, ledge,
shield break, entry/win/lose, the eight `Special*` rows, taunts. Your own moves that are not in the default set (a new special, a new aerial) need an engine
row and a move script: see `docs/learn/geno-fighters/` and `geno.json` `fighter.rows`.

## 3. Which rows may share a clip

| class | rule | examples |
|---|---|---|
| **safe alias** (the Courier ships them) | the same pose, so sharing is final art | `FallF`/`FallB`/`Fall`, `RebirthWait`/`Rebirth`, `RunDirect`/`Run`, `GuardReflect`/`GuardOn`, `CatchPull`/`Catch`, `AttackS3HiS`/`AttackS3Hi`, `OttottoWait`/`Ottotto`, `Entry`/`EntryEnd`/`EntryStart`, `SpecialN`/`SpecialAirN` |
| **placeholder, acceptable for release** | one clip fits a family | item swings (`SwordSwing*`, `BatSwing*`...: one `ItemSwing1/3/4/Dash`), item shoots, scopes, light/heavy throws, `Barrel`, crazy hand rows |
| **placeholder, prototype only** | gameplay-visible, deserves its own pose | every attack, every damage and knockback state, throws, ledge moves, specials, jump/landing |
| **do not share** | the move script is timed to it | two attacks never share a clip silently: the borrowed clip is held to the script length (`<Row>_pad`) but the pose will not match the hit |

A borrowed clip plays at its own length; if it is shorter than the move script the importer holds the last pose (flagged `PADDED`), if longer the move script simply
ends first and the animation is cut at the state change.

## 4. Naming and mapping

- An action named like an engine row serves that row. Row names are the engine's (`Attack11`, `AttackAirF`, `SpecialAirLw`, even the engine's misspellings: `DownFowardU`).
- One clip for several rows: custom property `geno_rows = "WalkSlow,WalkMiddle"` on the action, or `fighter.json` `clips.map`.
- Names that match nothing are warned (`CLIP_UNMAPPED`, with the closest row name); a typo in case or underscores is detected.
- Names are at most 31 characters. Do not name a scratch action like a row.
- Mark scratch actions `ignore` in `fighter.json` or give them no fake user.

## 5. Looping

A loop clip's last key must be the pose one step **before** its first (do not duplicate frame 0 at the end). The wrap step is judged against the clip's own
largest step; a visible pop is `LOOP_SEAM`. Rows that loop are marked `loop` in the tables; `geno_loop` (or the cyclic flag) overrides.
Idle and held states (`Wait`, `Guard`, `CatchWait`, `SquatWait`, `CliffWait`, `DownWaitU/D`, `Fall`, `Damage*Fly*`) are loops; attacks, jumps and getups are one-shots.

## 6. Timing and hit frames

- 60 fps, one key per frame on every animated bone (the Blender exporter and the starter do this for you).
- The default move set is timed to **specific frames** (table in `docs/geno-artist-rows.md`, "Move timing"): the clip's strike pose must be on the script's first hitbox frame and the clip at least as long as the script. Mark the strike frame with the `geno_hit_frames` property or a pose marker named `hit` (Geno panel > Mark hit frame); the validator then compares the two (`HIT_FRAME`).
- Late or early hit by a frame or two: shift the **hitbox**, not the clip: `moves.delay {"fsmash": 1}`. The four charge smashes already carry delay 1 (the engine shows their pose a frame late).
- Animation rate is 1.0 for every authored clip; do not rely on `ANIM_RATE`.
- Check in the LAB, FRAMES mode: scrub with `Q`/`E` and watch the hitbox appear on the fist (spec section 9).

## 7. Root motion

Only on the `translation` bone, only in: `EscapeF/B`, `DownBackU/D`, `PassiveStandF/B`, `CliffClimbSlow/Quick`, `CliffAttackSlow/Quick`, `CliffEscapeSlow/Quick` (list: `docs/geno-artist-rows.md`).
Flag them (`geno_root_motion` or `clips.root_motion`). Every other clip is in place; movement the engine does (walk, dash, jump arc) is never in the clip.
An unflagged clip whose translation bone moves is warned (`ROOT_UNFLAGGED`): that movement is dropped.

## 8. Locomotion speeds

The engine plays walk/run at `rate = ground speed / clip reference speed`. The importer **measures** each clip's planted-foot speed and writes the attributes.
Aim for a top-speed rate between 1x and about 3x:

| clip | game speed (default attributes) | rate should be |
|---|---|---|
| `WalkMiddle` | `walk_max_vel` 1.3 units/frame | the clip's measured speed should be 0.45-1.3 |
| `Run` | `dash_max_velocity` 1.5 | measured 0.5-1.5 |

Courier references: WalkSlow 0.29, WalkMiddle 0.50, WalkFast 0.72, Run 1.32. Longer legs and a longer stride raise the measured speed; a short-legged character
should lower `attributes.walk_max_vel`/`dash_max_velocity` instead (`LOCO_RATE` tells you which). Feet that never plant (`LOCO_UNMEASURED`) get a guessed rate.

## 9. Flagging placeholders

- `build/build-report.md` lists, per borrowed clip, the rows that play it.
- `python -m tools.geno.artist validate fighter.json -v` prints the same counts.
- `PROTOTYPE_INCOMPLETE` names missing prototype clips.
- Release gate (suggested): no `placeholder` row in the `prototype`, `recommended` or `finished` tiers.
