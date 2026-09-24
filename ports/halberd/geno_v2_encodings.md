# Geno v2 encodings for the Meta Knight translator (Phase 1 / Phase 4)

Copy of the MK-relevant part of `worktrees/beta/docs/geno.md` section 16 (private branch
`private/geno`); that section wins if they differ. v1 encodings (vars, CHG, REHIT, LINK, overlays)
are unchanged: `geno_v1_encodings.md`. v2 is additive: `"geno": 2` in geno.json (a v1 exe reads the
v1 keys and logs the rest).

## 1. What v2 gives MK

| MK piece | v2 feature | how to emit |
|---|---|---|
| Glide (Brawl statuses 0x84-0x88) | Geno states with glide behaviours | 5 `states` (below) |
| Glide from a held air jump (16 frames) | built into `geno.glide.start` | `"glide": {"hold_frames": 16}` (default) |
| Shuttle Loop -> Glide (PSA Change Action 0x85, anim end, in air) | CHG to a Geno state | `CHG ANIM_END -> GENO(0)` + `CHGAND AIR`, then the FallSpecial fallback CHG |
| Mach Tornado (native rise / drift) | `geno.tornado` | a state + `"specials": {"n": ...}` |
| Drill Rush (native steering) | `geno.drill.start` / `geno.drill` / `geno.drill.end` | states + `"specials": {"s": ...}` |
| MK's paramSpecialN / S and Misc Glide words | behaviour parameters | `"tornado"`, `"drill"`, `"glide"` blocks, word by word (`w00`..) |

## 2. States

State n (0-based, list order) = Melee motion `0x400 + n`. Script target word: `0x2000000n`
(kind 2 GENO). geno.json targets may name it: `"geno:Glide"`.

Recommended order for MK (keep it: the script targets use the index):

```json
"states": [
  { "name": "GlideStart",   "behavior": "geno.glide.start",   "subaction": <GlideStart sa> },
  { "name": "Glide",        "behavior": "geno.glide",         "subaction": <GlideDirection sa> },
  { "name": "GlideAttack",  "behavior": "geno.glide.attack",  "subaction": <GlideAttack sa>, "move_id": <id> },
  { "name": "GlideLanding", "behavior": "geno.glide.landing", "subaction": <GlideLanding sa> },
  { "name": "GlideEnd",     "behavior": "geno.glide.end",     "subaction": <GlideEnd sa> },
  { "name": "Tornado",      "behavior": "geno.tornado",       "subaction": <SpecialNSpin sa>, "next": "geno:TornadoEnd" },
  { "name": "TornadoEnd",   "behavior": "geno.air", "subaction": <SpecialNEnd sa>, "phys": "auto", "coll": "both", "next": "helpless" },
  { "name": "DrillStart",   "behavior": "geno.drill.start",   "subaction": <SpecialSStart sa> },
  { "name": "Drill",        "behavior": "geno.drill",         "subaction": <SpecialSDrill sa> },
  { "name": "DrillEnd",     "behavior": "geno.drill.end",     "subaction": <SpecialSEnd / SpecialAirSEnd sa> }
],
"specials": { "n": "geno:Tornado", "s": "geno:DrillStart" }
```

(Tornado's start (Brawl SpecialN 0x112) can be a `geno.air` state with `"next": "geno:Tornado"`
if the start clip matters; otherwise bind `n` to Tornado directly.)

State keys: `name`, `behavior`, `subaction` (an index in PlBm's subaction table, or
`"motion:N"` / `"special:N"` = that motion's subaction), `like` (a motion whose row gives flags /
move id / camera), `flags`, `move_id`, `next`, `land`, `landing_lag`, and per-slot callback
overrides `anim` / `iasa` / `phys` / `coll` (names in geno.md 16.2, or `"like"`). Targets: motion
id, `"motion:N"`, `"special:N"`, `"geno:N"`, `"geno:Name"`, `"auto"` (Wait / Fall), `"helpless"`
(Wait / FallSpecial).

Hitboxes, GFX and SFX of these states come from their subaction scripts (Melee commands + v1 Geno
commands: REHIT for the tornado's / drill's rehit rates, LINK for Drill Rush's angle 365). The
behaviours only move MK and choose transitions.

## 3. Script words

| what | words |
|---|---|
| CHG ANIM_END -> GENO(0) | `0xEF020100 0x20000000` |
| CHGAND AIR | `0xEF110300` |
| CHG ANIM_END -> FallSpecial (fallback, after) | `0xEF020100 0x00000023` |
| GET GENO_STATE into LA int 0 | `0xEC820000 0x0000001E` |

New engine values: `0x1E` GENO_STATE (i, -1 when not in one), `0x20..0x27` MOVE_F0-7 (f, W),
`0x28..0x2F` MOVE_I0-7 (i, W). Glide: MOVE_F0 angle (deg, + up), F1 speed, F2 sink, F3 pitch rate;
MOVE_I0 frames gliding, I1 end reason (1 button, 2 stall, 3 attack, 4 timeout), I2 stall, I3 wall.
Tornado: F0 spin rate; I0 countdown, I1 frames since the last lift, I2 tap armed, I3 lifts.
Drill: F0 pitch, F1 speed; I0 frames, I1 hit something, I2 bounce request, I3 bounce reason.

## 4. Parameter blocks = MK's Brawl words

Emit the Brawl blocks as they are (`"glide": {"w00": 80.0, ... "w21": 0}`, `"tornado": {"w00":
..}` = paramSpecialN w00-w19, `"drill": {"w00": ..}` = paramSpecialS w00-w05). The defaults are
already MK's values, so an MK profile only needs overrides. Names (the words' meanings, recovered
from sora_melee / ft_metaknight.rel):

- glide: w00 angle_max 80, w01 angle_min -70, w02 start_vy 0.75, w03 start_gravity 1.0, w04
  start_vx 1.0, w05 speed 1.7, w06 speed_accel 0.04, w07 max_speed 2.2, w08 stall_speed 0.7, w09
  sink_accel 0.03, w10 max_sink 0.6, w11 recover_angle 15, w12 dive_angle -25, w13 dive_bonus 0.03,
  w14 (unused), w15 deadzone 0.25, w16 pitch_up 0.55, w17 pitch_down 0.75, w18 max_pitch_rate 7,
  w19 stall_pitch 1.0, w20 wing_node 44 (Brawl partial anim, unused), w21 (unused).
  Extras: hold_frames 16, from_ground_jump 0, entry 1, end_buttons 14 (shield|special|jump),
  max_frames 0, end_helpless 0, pose_center 0 (90 with the 181-frame GlideDirection clip: pose by
  angle).
- tornado (param ids 4000-4016, 24000 = w11, 24001 = w16): w00 entry_vy 1.0, w01 entry_vx_mul 0.7,
  w02 start_rate 80, w03 ground_accel 0.12, w04 ground_speed 2.0, w05 air_accel 0.1, w06 air_speed
  1.7, w07 brake 0.008, w08 gravity -0.08, w09 max_fall 0.5, w10 tap_vy 1.0, w11 tap_cooldown 10,
  w12 max_rise 1.4, w13 tap_rate 16, w14 max_rate 80, w15 rate_decay 1.5, w16 spin_frames 70,
  w17 late_decay 2.0, w18 end_rate 10. Extras: max_speed 2.5, end_helpless 1.
- drill (4017-4020, 24002 = w04): w00 start_vx_mul 0.5, w01 start_vy 1.0, w02 start_gravity -0.08,
  w03 steer 3.0, w04 end_frames 10. Extras: speed 2.0 (only when the Drill clip has no TransN root
  motion; MK's SpecialSDrill does: convert it with TransN), angle_max 0 (none, as Brawl), bounce 7
  (1 wall, 2 hit, 4 shield), pop_vx 1.0, pop_vy 2.1, end_helpless 1.

**Param-id numbering is confirmed** (fn_111_81A8 getters): float ids count float words only (4011 =
N w12 ... 4016 = N w18; 4017-4020 = S w00-w03), int ids 24000 = N w11, 24001 = N w16, 24002 = S w04.
The IR's "inferred" labels are right.

## 5. Behaviour notes the translator should know

- Glide ends on a **stall** (speed or velocity below w08) - Brawl's Glide action does the same
  (RA-Bit16) - on A (GlideAttack), on shield / special / jump (GlideEnd), on landing
  (GlideLanding). No time limit (Brawl has none). GlideAttack and GlideEnd go to Fall.
- Glide_Landing's extra Brawl thresholds (common params 3169/3170) are not applied.
- The tornado ends when its spin rate runs down to w18 (the PSA's `IC-Basic[24] <= 10`), not at a
  fixed frame; B taps (10-frame cooldown) lift +1.0 (rise cap 1.4) and add 16 to the rate. The
  translator should NOT emit the PSA's Change Action to SpecialNEnd; `next` does it.
- Drill Rush's pitch follows the stick (up climbs, either facing), speed = the clip's root motion;
  SpecialSEnd eases the pitch back and, in the air, pops MK back (-1, +2.1). The translator should
  drop the air-end "Set/Add Momentum" event (the behaviour applies it) and the PSA's own Change
  Actions between the drill statuses (`next` handles them).
- Brawl's partial wing animation (GlideWing over GlideDirection) has no Melee equivalent; emit
  GlideDirection as the Glide state's subaction and set `"pose_center": 90` once the clip is
  converted.

## 6. v3 additions (Geno v3, `"geno": 3`; geno.md section 17 wins)

v3 is additive (a v2 exe reads the v2 keys). What changed for MK:

| MK piece | v3 feature | how it is emitted (tools/build_mk.py) |
|---|---|---|
| Shuttle Loop (no MK code: TransN + PSA) | `geno.anim_motion` states | UpB (SpecialHi, ground), UpBAir (SpecialAirHiStart), UpBLoop (SpecialHiLoop), UpBLand (SpecialHiEnd); `"specials": {"hi": "geno:UpB", "air_hi": "geno:UpBAir"}` |
| Dimensional Cape | `geno.cape`, `geno.cape.attack`, `geno.cape.end` | CapeStart / CapeStartAir, CapeN / NAir / F / FAir / B / BAir, CapeEnd / CapeEndAir (this order); `"lw"` / `"air_lw"` |
| Drill Rush | the v2 states, corrected from Brawl's code | DrillEndGround BEFORE DrillEnd (the engine pairs ground, air); `"drill": {"bounce": 0}` |
| Allow/Disallow Ledgegrab | engine value LEDGE `0x30` | `PUT LEDGE n` at the PSA frame: `0xEC930000 0x00000030 n` |
| Visibility (a vanish over several states) | engine value HIDDEN `0x31` | `PUT HIDDEN 1/0`: `0xEC930000 0x00000031 1` |
| Disable / Enable Horizontal Gravity | MOTION_GRAVITY `0x34` (f) | `PUT MOTION_GRAVITY 0.0 / 1.0` |
| Change Action 0x85 (Glide) from the up-B | unchanged v2 CHG | `CHG ANIM_END -> GENO(Glide)` + `CHGAND AIR`, then `CHG ANIM_END -> Fall` |

Rows: the v3 states play Kirby copy-ability rows 352-365 (after the v2 ones), repointed at MK's clips;
animation-driven (`0x80000004`): UpB, UpBAir, UpBLoop and the six cape slash rows. The main exe keeps
the old approximations on Kirby's special rows (Final Cutter 324-331, stone 332-337, hammer 322/323).

State keys (v3): `"ledge"` (none / front / both), `"liftoff"` (default true), `"origin"` (the clip's
frame-0 offset moves the first frame: SpecialHi, SpecialHiLoop), `"gravity"`, `"facing": "entry"`
(the cape reappears), `"land": "stay"`.

MK choices (Brawl evidence in parentheses):
- UpB `"liftoff": true` instead of `PUT AIR 1` at 5 (Brawl sets the air situation at 5 while its clip
  is still on the floor until 7; Melee would land an airborne fighter at floor height at once).
- UpB / UpBLoop `PUT LEDGE 2` at 7 (Allow Ledgegrab 2 @7); the glide after it ends helpless
  (`glide.script_entry_helpless`, Brawl LA-Bit61); landing in the loop -> UpBLand (32 frames, no
  interrupt) -> Wait.
- Cape start `PUT HIDDEN 1` at 12 (Visibility off), intangible at 17 (Body Collision 2); decision at 26
  (held B or A -> slash; stick x vs facing picks N / "F" (back) / "B" (forward)); slash rows: BodyColl 2
  at 0, `PUT HIDDEN 0` + BodyColl 0 at 1, N and B `PUT FACING 0` at 1, 14% at f6-7, ModelVis(0,0) at the
  last frame; end rows: `PUT HIDDEN 0`, `PUT LEDGE 2` at 0, ground IASA 28, air `PUT MOTION_GRAVITY` 0 at
  0 / 1 at 10. Ground reappears `"liftoff": false` (the clips' TransN pops 17.5 up at frame 1).
- Drill: `PUT LEDGE 1` at 20 (Allow Ledgegrab 1 @20); DrillEnd (air) `"coll": "anim_motion"`,
  `"ledge": "both"`, `"land": "motion:43"`, `"next": "helpless"`; DrillEndGround `"coll": "ground"`,
  `"next": "auto"`.
- `"cape"` block = paramSpecialLw w00-w05 (0.5, 0.4, 0.5, 2.5, 0.5, 2.5): keep_vx, keep_vy,
  steer_accel_x, steer_max_x, steer_accel_y, steer_max_y (ids 4021-4026, read by MK kinetic types
  0x69 / 0x6A only). Extras: steer_frame 12, decide_frame 26, neutral_x 0.3 (inferred), attack_buttons 3.
