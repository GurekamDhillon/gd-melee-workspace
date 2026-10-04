# Sonic Blade (Sora / `trail` side special) - behaviour specification from the status code

Dated 2026-10-03. Supersedes `_research/ultimate-sonic-blade-steering.md` and section 2-3 of
`_research/ultimate-trail-status.md` wherever they disagree (see section 12, "Where the older notes were wrong").
Read-only research: no game run, no build, no tracked file edited.

## 0. Method, sources, how to read the citations

* The NRO `lua2cpp_trail.nro` was re-imported into a fresh headless Ghidra project (Ghidra 12.1.2, junction path
  without an apostrophe) and the whole side-special status closure (347 functions, 0x7100000000-0x7100036000) was
  decompiled and disassembled with `DumpSpec.java` (scratchpad; not committed). Outputs, all under
  `_build/tmp/sonic-spec/`:
  * `all_status.c` - raw decompilation of the closure;
  * `clean/<addr>.c` - the same, one file per function, declarations / destructors / lua-stack noise removed, blank
    lines removed, hash constants annotated with their ParamLabels names, work-id constants printed `K[0xNNNN]`
    (`K[x]` = `*(int*)(const_value_table + x)`);
  * `asm_<addr>.txt` - AArch64 listing, used to settle every branch whose sense mattered;
  * `registered.txt` - the (status kind, callback slot, wrapper address) table decoded from the two registration
    functions `0x7100004260` / `0x7100005910`; `acmd_compact.txt` - the ACMD rows; `ln.sh <addr> <regex>` finds a line.
* **Citation format:** `[28750:L96]` = `_build/tmp/sonic-spec/clean/7100028750.c` line 96. `[asm 2bd30 c278]` =
  `asm_710002bd30.txt` address `0x710002c278`. Function addresses are Ghidra VAs in the NRO (base `0x7100000000`).
  The older scan `_build/tmp/sonic-steering-scan.c` contains five of the same functions; mine are the same code with
  noise stripped.
* Tags: **CONFIRMED** = an operation / value is present in the decompilation or disassembly and its meaning follows
  from it; **INFERRED** = reading that goes beyond the literal code (names of engine constants, kinetic-type
  semantics); **UNKNOWN** = lives outside the NRO or needs data we do not have.
* A decompiler limitation to keep in mind: every `L2CValue::operator+/-/*` returns its result by hidden pointer, so
  the printed code shows the operands but not where the result went. I resolved each case by following which stack
  slot is read next and, where it mattered, by the listing. Branch senses that decide behaviour were re-checked in
  assembly (marked `[asm ...]`).
* **The const table is not on disk.** `K[...]` ids (status kinds, work ids, global_table slots, kinetic ids) are
  runtime values from the main executable. I give the offset and a role inferred from usage; names are mine.
* Motion hashes verified as `(len<<32)|crc32(name)`: `special_s_search 0x1017efc1d7`, `special_air_s_search
  0x14965a4e97`, `special_s_1 0xb9afea4ec`, `special_air_s_1 0xf6d6ca1db`, `special_s_2 0xb03f7f556`, `special_air_s_2
  0xff465f061`, `special_s_3 0xb74f0c5c0`, `special_air_s_3 0xf8362c0f7`, `special_s_end 0xdb8bd3614`,
  `special_air_s_end 0x1158d0953d`, `special_s_turn 0xe86240325`, `special_air_s_turn 0x12c476f6ea`,
  `special_s_turn_up 0x11b3447f8f`, `special_air_s_turn_up 0x15c5198b90`, `special_s_turn_down 0x1308d33e4b`,
  `special_air_s_turn_down 0x177f59708d`, `param_special_s 0xfea97fe73`. All recomputed locally; all match.
  (`special_s_start` = `0xf3c6351ed` / `special_air_s_start` = `0x1337fadc39` are **not referenced anywhere in the NRO**.)
* Constants read straight from the NRO rodata: `71004cbe18 = 90.0`, `71004cbc34 = 270.0`, `71004cbc74 = 360.0`,
  `71004cbd64 = 180.0`, `71004cbde4 = 0.01`.

## 1. The big picture (what the code actually is)

The move is **not** "start -> hover -> dash" repeated. It is four NRO statuses plus an entry status that is *not in
the NRO*:

```
 [exe-side entry: motion special_s_start, 15-frame clip; sets up the work values]   UNKNOWN (outside NRO)
        |
        v
  DASH (K[0xe4d8], count = 0)  --motion end--+--> END (K[0xe4e4])          when no follow-up input (or count >= 2)
        ^                                    |
        |                                    +--> SEARCH (K[0xe4dc]) when (stick >= 0.25) OR (special latched)
        |                                                |  ~9 frames, aim cursor, SEARCH hitbox active
        |                                                v
        +------------------ TURN (K[0xe4e0]) <-----------+   8-frame turn clip, picks up/down/level, flips facing
              (dash 2 and 3 only; count = 1, 2)
```

Registration (from `registered.txt`; slot `0x38`=PRE, `0x3c`=MAIN, `0x4c`=per-frame pose callback, `0x50`=END is
my reading of the contents; names of the statuses are mine):

| status id | my name | PRE | MAIN (wrapper -> body) / loop | 0x4c | 0x50 END |
|---|---|---|---|---|---|
| `K[0xe4d8]` | DASH ("attack") | `710002e520` | `7100018d70` -> `7100028750` / loop `710002bd30` | `7100014ae0` | `7100017260` |
| `K[0xe4dc]` | SEARCH (aim window) | `710002e900` | `7100018d80` / loop `7100025b40`, sub-callback `7100025a90` | `7100014c50` | `7100017500` |
| `K[0xe4e0]` | TURN | `710002ecd0` | `71000198a0` -> `71000238e0` / loop `7100024f40`, sub-callback `7100024ee0` | `7100014d20` | `7100017770` |
| `K[0xe4e4]` | END | `710002f0a0` | `71000198b0` / loop `7100022f70` | `7100014d50` | `7100017840` (no-op) |

The wrappers at `...18d70` and `...198a0` are three-instruction tail jumps (`mov x1,x0; mov x0,x8; b body`);
Ghidra names them as the body. Extra callbacks on DASH: slot `0x3078` = `7100007370` (mirror the stored aim angle
when facing flips: `a = 180 - a`, wrap into [0,360)) and slot `0x3084` = `71000077f0` (if `count > 0`, re-set the
dash energy's speed limit to (-1,-1)) [7370:L10-26, 77f0:L10-20] - the slot meanings (ON_CHANGE_LR / LEAVE_STOP) are INFERRED.

Work values, named by usage (**INFERRED names**, CONFIRMED uses). `W` = `WorkModule`:

| id | kind | role |
|---|---|---|
| `e640` | int | dash count = **dashes already completed** (0 during dash 1). `inc_int` in DASH-END [17260:L36]. Never written elsewhere in the NRO. |
| `e644` | int | read only in the speed helper (`0.98^e644`) [2b2d0:L38-52]. **No writer in the NRO** (byte search for `mov w,#0xe644` finds one site, the read). UNKNOWN. |
| `e648` | flag | "powered follow-up": set at each dash start to `is_flag(e654) && !is_flag(e660)` [28750:L41-60]; x1.15 speed [2b2d0:L67-76]; selects the stronger hitbox set in game_specials2/3. |
| `e64c` | flag | ground-correct selector in the dash-1 kinetic helper [2b880:L20-30]. Writer outside NRO. UNKNOWN. |
| `e650` | flag | "special latched" - **only writer in the NRO is the button check in the dash loop** [2bd30:L27-48] (and the exe may also set it, UNKNOWN). Cleared at every dash start [28750:L38]. |
| `e654` | flag | copy of `e650` taken at dash start [28750:L21-29]. |
| `e658` | flag | "dash started on ground / currently touching floor" [28750:L30]; updated in the dash loop for dashes 2/3 [2bd30:L384-395]. |
| `e65c` | flag | follow-up input window; **turned on at ACMD motion-frame 3, off at frame 13** of each dash (ACMD, see 5) and off at dash start. |
| `e660` | flag | "aimed with the stick since this SEARCH began" - on in `27700:L56-58` and `18d80:L142`, off at SEARCH start [18d80:L49] and in TURN when a target is used [238e0:L123]. |
| `e664` | int | locked target id, sentinel `0x50000000` = none. **Only written (to the sentinel) inside the NRO** [18d80:L45, 25b40:L256, 238e0, 28750]. The real writer is outside. |
| `e668` | float | aim angle in degrees [0,360), `-1` = none. |
| `e66c`,`e670`,`e690` | article id / article int / article status | lock/aim marker article (created outside the NRO). |
| `e674` | int | effect handle of the aim cursor (0 = none). |
| `e678` | int | consecutive "pressed into a surface" frame counter, limit param `0x1B949B05BC` = 35. |
| `e67c` | float | stick angle pre-sampled during dash 2 (see 3.4). |
| `e680` | int | SEARCH countdown, initial `search_frame` = 9; decremented by `7100025a90`. |
| `e684` | float | previous aim angle (for the body pose lerp). |
| `e688` | cliff-hang data id used before dash 3. `e68c` int: TURN cursor-lock countdown = `cursor_lock_frame` 7. `e694` float: previous lr. |
| `1744`/`1748` | flag/float | `22d80`: `on_flag(K[0x1744])`, `set_float(K[0x1748], cursor_offset_y(17) * scale)`, run in every status of the move. Role UNKNOWN (looks like an aim-reticle height offset consumed outside the NRO). |

Engine-ish ids (INFERRED): `K[0x58]` = SITUATION_KIND_GROUND, `K[0x2e4]` = SITUATION_KIND_AIR, global_table slot
`0x16` = SITUATION_KIND, `0x17` = PREV_SITUATION_KIND [asm 22f70 :30ac,30e0; asm 2bd30 ce68-cf1c], slot `0x8` = a boolean read
as `== false` (my guess: "in hitstop"), `K[0x498]` = the kinetic energy that carries the dash velocity ("stop"
energy), `K[0x3b4]` = gravity energy, `K[0x4a8]` = air-control energy, `K[0x4a0]` = air kinetic type, `K[0x410]` =
ground kinetic type, `K[0x434]` = ground-correct "air", `K[0x4b4]`/`K[0x414]` = ground-correct (cliff stop / plain).

## 2. Parameters (`param_special_s`[0], decoded `_build/tmp/sonic-steering-vl.xml` lines 633-689)

Every value was re-read from the XML; the *use* column is from this pass.

| param | value | used by | how |
|---|---|---|---|
| `attack_speed_x` | 3.2 | `2b2d0` | base dash speed, every dash |
| `attack_frame` | 12 | `28750:L517-529` | dash motion rate = `end_frame/12 + 0.01` -> **a dash lasts 12 frames** |
| `0x15530D2D10` | 0.92 | `2b2d0:L12-36` | speed x 0.92 per completed dash (`0.92^count`), only when count > 0 |
| `0x17DD304B6F` | 0.98 | `2b2d0:L38-52` | speed x 0.98 per `e644` |
| `0x1A41A10288` | 1.15 | `2b2d0:L67-76` | speed x 1.15 when `e648` (powered) |
| `attack_up_angle_min/max` | 40 / 140 | `28750:L426-448`, `238e0:L165-190` | **(a)** dash speed x `attack_up_speed_mul` 0.85 **only when there is no locked target**; **(b)** choose the `*_turn_up` clip |
| `attack_down_angle_min/max` | 220 / 320 | `238e0:L192-213` | choose the `*_turn_down` clip. **Nothing else.** |
| `attack_up_speed_mul` | 0.85 | `28750:L448` | above |
| `attack_num` | 3 | `2bd30:L56`, `28750`, `25b40` | dashes allowed = 3 (`count >= attack_num-1` ends the chain) |
| `search_frame` | 9 | `18d80:L15-26` | SEARCH countdown |
| `search_stick` | 0.25 | `27700:L19`, `18d80:L108`, `2bd30:L78` | stick-vector **length** dead zone |
| `search_inherit_speed` | 2 | `25270:L35` | speed cap on entering SEARCH |
| `search_brake_x` / `search_brake_air` | 0.24 / 0.34 | `25270:L64,95` | decel in SEARCH/TURN (ground / air) |
| `search_cursor_dist` / `search_cursor_offset_y` | 12 / 8 | `28280` | cursor placed `12*scale` from `pos_2d` along the aim angle, `+8*scale` up |
| `cursor_offset_y` | 17 | `22d80` | work float `K[0x1748]` (role UNKNOWN) |
| `cursor_lock_frame` | 7 | `238e0:L235-241` | TURN: `e68c` countdown; at 0 the marker article is switched to status `K[0xe690]` |
| `attack_turn_frame` | 4 | `15310` | frames over which the body "rot" joint lerps old aim -> new aim in TURN (**visual**) |
| `right_frame` | 4 | `14d80` | frames over which the "rot" joint un-rotates during END (**visual**) |
| `attack_hit_ground_angle` / `attack_hit_down_angle` | 65 / 55 | `2bd30:L189,197` | wall/ceiling vs floor head-on test thresholds (section 7) |
| `0x1B949B05BC` | 35 | `2bd30:L257,311` | head-on-contact frame limit -> END |
| `attack_check_down_y` | 15 | `28750:L168`, `25b40:L153` | x10 = **150**: length of a downward probe ray (floor check) |
| `attack_check_dead_range_x` | 5 | `28750:L238` | x10 = 50: distance to the blast-zone edge that triggers the "dead range" speed rule |
| `attack_dead_speed_mul` | **1.0** | `28750:L287,327` | multiplier of that rule: **a no-op in the shipped data** |
| `0x1719BF7EB5` | 10 | `28750:L150, L362-415` | NOT a speed factor: `10 + ceil(distance/speed)` is stored into the marker article (`ArticleModule::set_int(e66c, e670)`) as its lifetime in frames |
| `0x0DEB5675E2` | 20 | `24ab0:L6` | "near vertical" tolerance (deg) for the facing-flip rule |
| `end_frame_1/2/3` | 35 / 40 / 45 | `198b0:L14-35` | END motion rate -> END lasts exactly N frames (N by dash count 1 / 2 / 3+) |
| `end_brake_x` / `end_brake_x_air` | 0.12 / 0.35 | `223d0:L18,35` | x brake in END (ground / air) |
| `end_speed_y` | 1.5 | `223d0:L47-66` | air END: clamp of the gravity-energy y speed to [-1.5, +1.5] |
| `end_accel_y` | 0.08 | `223d0:L71-78` | air END: gravity accel set to -0.08 |
| `end_speed_x_mul_air` | 0.5 | `223d0:L99-107` | air END: stable speed of the air-control energy = `air_speed_x_stable * 0.5` |
| `attack_landing_frame` | 20 | `22f70:L38,72` | landing-lag float handed to the fall/landing statuses |
| `end_landing_fall_special_frame` | 20 | `22f70:L29` | motion-frame threshold: landing in END at motion frame >= 20 -> landing-special status |
| `0x1CB542ADC0` | 20 | **not used in the NRO** | UNKNOWN (probably the exe-side start/entry) |
| `start_*`, `search_angle` | - | **not used in the NRO** | the 12 `start_*` values (ground/air multiplier 0.5, brake 0.1/0.01, ...) are for the exe-side entry; `search_angle` = 0 unused |
| `turn_param_special_s` | [315,270,225,180] | **not used in the NRO** | see 3.5 |

## 3. Aiming (the part the port got wrong)

### 3.1 Who aims, and when

* **Dash 1 is not aimed at all.** The DASH status with `count == 0` takes the "else" of `if 0 < count`
  [28750:L66-83]: motion `special_s_1`/`special_air_s_1`, kinetic helper `b880`, then `ba70`:
  `set_speed(K[0x498], speed * lr, 0)`, `set_brake(0,0)`, `set_limit_speed(-1, 0)`, gravity accel 0 [ba70:L5-20],
  then `set_speed(K[0x3b4], 0)` [28750:L80]. Direction = **facing**, speed = `3.2 * (1.15 if e648)`. No stick, no
  target, no angle code is reachable for count 0. CONFIRMED. (And there is no SEARCH before dash 1: SEARCH is only
  entered from DASH-loop and from nowhere else in the NRO.)
* Dashes 2 and 3 (`count` = 1, 2) are aimed. Between every two dashes there is a SEARCH window then a TURN.

### 3.2 SEARCH (status `e4dc`), what happens frame by frame

Entry [18d80]: motion `special_s_search`/`special_air_s_search` (`inherit frame = false`) [L5-9]; kinetic setup
`222a0` [L11]; `25270(true)` [L13] (below); `e680 = search_frame (9)` [L15-26]; sub-callback `25a90` installed in a
global_table slot [L42] (decrements `e680` when called with a true argument [25a90:L8-12]); `e664 = 0x50000000`
(**target cleared at every SEARCH start**) [L45]; `e660 off` [L49]; `e684 = e668`, then `e668 = -1.0` [L52-67];
if `count == attack_num-1` (i.e. before the **last** dash) `select_cliff_hangdata(K[0xe688])` and
`set_cliff_check(K[0xb1cc])` [L72-90]; if a cursor effect already exists (`e674 != 0`): if `|stick| >= 0.25`
then `e668 = get_float(e67c)` and `on_flag(e660)` [L114-142] else kill the cursor effect [L121-127]. Then main = `25b40`.

`25270` (entry speed handling): reads the kinetic vector `(vx,vy)` of `K[0x498]`; **when called with `true` and
`|v| > search_inherit_speed (2.0)`, rescales v to length 2.0** [25270:L35-56]. Then: ground -> `set_brake(0.24, 0)`;
air -> if `search_brake_air` is zero `set_speed(0,0)` else `set_brake = (0.34/|v|) * (vx,vy)` i.e. a straight-line
deceleration of 0.34/frame [25270:L60-102]. (Ground 2.0 stops in ~8.3 frames, air in ~5.9.) CONFIRMED.

Loop `25b40` while `e680 != 0` [L10-18]:
* if the boolean global_table slot `0x8` is false (INFERRED: not in hitstop) **and `e664 == none`**: call
  `27700(handle=e674, floatId=e668)` [L55-64] - **the stick is sampled only when there is no locked target**.
  With a target the stick is ignored for aiming (the lock wins).
* if that slot is true and a cursor exists: only re-place the cursor from the stored angle [L18-48].
* then `14fd0(get_float(e684), 1.0)` (pose the "rot" joint) [L69-75], and on a ground<->air change re-select the
  search motion with `inherit frame = true`, redo `222a0` and `25270(false)` [L76-110].

`27700` (cursor + stick sampling) - read at **every frame of the window, once per frame**:
`stick = (get_stick_x, get_stick_y)` [L8-14]; `len = |stick|`; **if `search_stick (0.25) <= len`**: `angle =
deg(atan2(y, x))`, `+360` if negative -> full circle [0,360) [L39-52], `set_float(floatId, angle)`, `on_flag(e660)`
[L53-58]; **else if no cursor exists yet: return; else reuse the previously stored angle** [L26-33 region]. The cursor
effect (`0xe694f9d4f`) is created the first frame an angle is stored, placed at `pos + (cos*12, sin*12 + 8)*scale`
(`28280`), rotated `angle - 90` [L77-128]. CONFIRMED.

**There is no clamp, no quantisation, no 8-way snap, no ground restriction in the aim**: the angle is the raw
polar angle of the stick, continuous 0-360. The *last* frame inside the window with `|stick| >= 0.25` wins; letting
go keeps it.

Window end (`e680 == 0`) [25b40:L121-315]:
1. If `e650` (special latched) **and** situation is AIR **and** `count == attack_num-1` (the last dash is next):
   ledge assist [L121-265]. A probe ray of `attack_check_down_y*10 = 150` is cast straight down from `pos_2d`
   (`270f0` builds `(0,-150)`, rotated for non-normal gravity) [L153-190]. If it finds **no floor** (no line, or the
   line is not a floor) **and** `GroundModule::can_entry_cliff()`: `e668 = atan2(cliff.y' - pos.y, cliff.x - pos.x)`
   in degrees (`cliff.y' = max(cliff.y, pos.y)`), `clear_cliff_point`, `e664 = none`, `e660 off`, remove the marker
   article, `change_status(TURN, true)` [L205-270]. I.e. **the third dash is auto-aimed at a grabbable ledge when
   you are off-stage**. CONFIRMED mechanism; gameplay name is mine.
2. Otherwise: if `e664 != none` **or** `e668 >= 0` -> `change_status(TURN, true)` [L315]. If no target and
   `e668 < 0` (never deflected the stick): if `e650` latched -> `27580` (sets `e668 = 180` if lr = -1 else `0`: **straight
   ahead**) then `change_status(TURN, true)`; else `change_status(END, false)` [L278-315].

So with **neutral stick**: aim = forward (facing) if the special button was latched, otherwise the chain ends. With
**locked target**: aim = toward the target, stick ignored. With **stick**: aim = last stick angle. CONFIRMED.

### 3.3 TURN (status `e4e0`) - turn clip, facing, up/down clip

`238e0` [L10-260]: reads `e664`, `lr`; `e694 = lr`. 
* **Target present:** `tpos = FighterSpecializer_Trail::get_special_s_target_pos(e664)` (exe) -> 2D; `jpos` =
  `ModelModule::joint_global_position(param int64 0x187367db00 "trail_special_s_joint_id")` -> 2D; `d = tpos - jpos`;
  if `d` is the zero vector then `d = (lr, 0)`; `angle = deg(atan2(d.y,d.x))` (+360 if negative); `e668 = angle`;
  `e660 off` [L22-125]. 
* **No target:** `angle = e668` [L127-135].
* **Facing rule (both cases):** `24ab0(angle)` is true iff `|angle-90| <= 20` or `|angle-270| <= 20`
  (`0x0DEB5675E2 = 20`, constants 90/270 read from rodata) [24ab0:L6-20]. **If it is false (aim is NOT within 20 degrees
  of straight up/down) the new facing = sign of the aim's x component (`d.x` with a target, `cos(angle)` without),
  unchanged if x == 0; if it is true the facing is left unchanged.** [238e0:L93-160]. If new lr != old lr the exe call
  `FighterSpecializer_Trail::set_turn_special_s(accessor)` performs the flip [L227-232].
* **Clip choice:** `attack_up_angle_min(40) <= angle <= attack_up_angle_max(140)` -> `special_s_turn_up` /
  `special_air_s_turn_up`; else `attack_down_angle_min(220) <= angle <= attack_down_angle_max(320)` -> `*_turn_down`;
  else `special_s_turn` / `special_air_s_turn` [L165-232]. `inherit frame = false`. These ranges gate **only the
  turn animation** (and the 0.85 up multiplier at dash start); they are not aim limits. CONFIRMED.
* `e68c = cursor_lock_frame (7)`; `24d80(false)` [L235-252] ; sub-callback `24ee0` counts `e68c` down and at 0 does
  `ArticleModule::change_status_exist(e66c, e690)` [24d80:L8-24]. Main = `24f40`.
* TURN keeps the speed it inherited (it never calls `222a0`/`25270` on entry) so the SEARCH deceleration continues.

Loop `24f40` [L10-50]: when the turn motion ends (`MotionModule::is_end`) -> `change_status(DASH, false)`. Clip
lengths from our dump: `d01specialsstart2` / `...up` / `...down` = **8 frames** at rate 1 (no rate is set in TURN),
so TURN = 8 frames (if those clips are the turn clips; mapping clip <-> motion hash is by name, INFERRED). On a
ground<->air change it re-selects the turn motion with `inherit frame = true`, `222a0`, `25270(false)` [L58-90].
While turning, `15310` lerps the "rot" joint from `e684` to `e668` over `attack_turn_frame (4)` frames (visual).

### 3.4 Pre-sampling during dash 2

In the DASH loop, when `0 < count < attack_num-1` (that is, **dash 2 only**) and slot `0x8` is false, `27700(e674,
K[0xe67c])` runs every frame (cursor shown, stick angle stored in `e67c`, `e660` set) [2bd30:L407-471 region]. At the
next SEARCH start, if the stick is still >= 0.25 and the cursor exists, `e668 = e67c` [18d80:L114-142]. So the aim you
held during dash 2 carries into the aim window before dash 3. (There is no equivalent during dash 1.)

### 3.5 What `turn_param_special_s` [315, 270, 225, 180] is

Not referenced in the NRO (hash `0x144d3405f9` has no hit in the whole closure). **INFERRED:** a 4-entry table, and
`attack_turn_frame = 4`, `FighterSpecializer_Trail::set_turn_special_s` is the only exe call on a facing change -> most
likely a per-frame model-yaw sequence that turns the model 180 degrees over 4 frames when the aim flips Sora's facing.
It is **not** an aim quantisation table and not a ground restriction. To decide: disassemble `set_turn_special_s` in the
main executable.

### 3.6 Dash heading at DASH start (count 1 and 2) [28750:L84-513]

1. `situation <- AIR` (`set_situation(K[0x2e4])`), kinetic type `K[0x4a0]`, ground-correct `K[0x434]`,
   `GroundModule::set_passable_check(true)` [L87-98]; motion = `special_s_2` (count 1) or `special_s_3` (count 2),
   ground/air variant by "touching floor now" [`2afb0`, L1-45]. **Dashes 2 and 3 always leave the ground**, whatever
   the aim.
2. `speed = 2b2d0()` (section 5).
3. **Target present** (`e664 != none`; target position re-read live now): `d = tpos - jpos` as in TURN [L115-148].
   Last dash only (`count == attack_num-1`): the "dead range" rule [L150-330]: if no floor within 150 below Sora
   (probe ray) **and** the target's x is within `5*10 = 50` of the blast-zone edge in the facing direction (via
   `sv_camera_manager::dead_range`; special stage ids `K[0xaf00]`, `K[0xaee4]`, `K[0xfc8]` re-route the check) -> speed
   x `attack_dead_speed_mul` = **x1.0, so nothing happens**. If `d` is not zero: `v = d * (speed/|d|)` (**homing: the
   velocity points at the target's current position, speed unchanged**), marker lifetime `10 + ceil(|d|/speed)` stored in
   the article [L350-415]; if `d` is zero: `v = (speed*lr, 0)`. `e668 = deg(atan2(v.y,v.x))`. **The 0.85 up-speed multiplier is
   NOT applied with a target.**
4. **No target:** `angle = e668`; if `40 <= angle <= 140` then `speed *= 0.85`; `v = (cos(angle)*speed, sin(angle)*speed)`
   [L420-470]. (Neutral stick with latched special was already turned into `angle = 0/180` by `27580`.)
5. Facing: same `24ab0` rule as TURN; `if lr changed: PostureModule::set_lr; update_rot_y_lr` [L383-400, L470-500].
6. `set_speed(K[0x498], v.x, v.y)`, `set_brake(K[0x498], 0, 0)`, `set_limit_speed(K[0x498], -1, -1)`,
   **gravity accel `set_accel(K[0x3b4], 0)`** [L500-513]. Then motion rate `end_frame/attack_frame + 0.01` [L517-529].

`v` is in **world** coordinates (cos/sin of the absolute angle) - the stick x is raw `get_stick_x` (not lr-relative).
`e668` in degrees CCW from +x; `7370` mirrors it (`180 - a`) when facing changes mid-status.

## 4. Lock-on / targeting

* The only target-search artefact in our data is the ACMD `SEARCH` in `game_specialssearch` /
  `game_specialairssearch` (frame 0): `SEARCH(id 0, part 0, bone "top", size 50.0, x 0, y 4, z 0, x2 0, y2 4, z2 0, ...)`:
  a **sphere radius 50 at `top` + (0,4,0)**, active for the whole `special_s_search` motion (the clip loops, 21 frames,
  but the status leaves after ~9) [`acmd_compact.txt`; `_build/tmp/codex-nodrop-run/trail.acmd.json`]. Radius 50 = the
  port's `LOCK_RANGE` (numerically right).
* **Nothing in the NRO consumes the SEARCH hit.** `e664` is only ever *reset* in the NRO. The writer of the target id
  (and of the lock-on marker article `e66c`) is in the main executable (`FighterSpecializer_Trail`/search-hit handling).
  Consequently, **how the target is chosen among several (nearest? first hit? facing?), whether `search_angle` (0)
  filters, and the exact target point returned by `get_special_s_target_pos` (hit-box centre, a joint, + offset?) are
  UNKNOWN.** What is CONFIRMED: the target is **re-acquired at every SEARCH** (`e664 = none` at SEARCH start), a locked target
  **overrides the stick**, and the dash heading is computed from the target's **live** position at dash start
  (homing at launch only, not continuous in flight).
* `search_cursor_dist`/`search_cursor_offset_y`/`cursor_offset_y`: cursor geometry only (3.2, 2). `search_inherit_speed`/
  `search_brake_*`: SEARCH deceleration (3.2).

## 5. Dash velocity, duration, input windows

**Speed helper `2b2d0`:** `speed = 3.2`; `if count > 0: speed *= 0.92^count`; `if e644 > 0: speed *= 0.98^e644`
(inside the `count > 0` block); `if is_flag(e648): speed *= 1.15` [2b2d0:L5-76]. (Loop counts verified:
`iVar3 = count-1; do { speed *= m } while (++i < iVar3)` runs `count` times.)

| dash | count | base | x0.85 aimed 40-140 (no target) | x1.15 powered |
|---|---|---|---|---|
| 1 | 0 | 3.2 (never aimed) | n/a | 3.68 |
| 2 | 1 | 2.944 | 2.502 | 3.386 (2.877 aimed-up) |
| 3 | 2 | 2.708 | 2.302 | 3.115 (2.647 aimed-up) |

(`e644` unknown source: x0.98 each.) 

**Duration:** `MotionModule::set_rate(end_frame/12 + 0.01)` -> the dash motion ends after `attack_frame = 12` game
frames (clips are 13 frames; rate ~1.01-1.09) [28750:L517-529]. A dash ends **only** when its motion ends (12 frames),
or earlier by ledge-grab (`sub_transition_group_check_air_cliff` at loop top [2bd30:L7]) or hit/stop engine events; there is
no speed-based or contact-based end except the 35-frame contact rule (7).

**ACMD per dash (motion frames; game frame ~ motion frame / rate, ~ same):**
frame 3: three `ATTACK` spheres on bone `haver` (y = 2.5 r3.2, y = 6.5 r3.2, y = -3.0 r3.8) + `WorkModule::on_flag(0xe65c)` (**follow-up window opens**);
frame 11: `AttackModule::clear_all` (**hitboxes end**), `KineticModule::add_speed(-1,0,0)` (dash 1) / `(-0.5,0,0)` (dash 2, 3),
`notify_event_msc_cmd(0x2127e37c07, K[0x1ec0])` (**UNKNOWN**, exe event); frame 13: `off_flag(e65c)`. Same rows for air
variants (`game_specialairs1/2/3`). Hitbox data: dash 1: 5.2%, angle 72, kbg 10, bkb 85; dash 2: **3.0%**, angle 108, kbg 8, bkb 80
when `!is_flag(e648)`, **5.2%** same angle/kbg/bkb when `e648`; dash 3: **3.0%** angle 46 kbg 88 bkb 80 when `!e648`, **5.2%** angle 46 kbg 85 bkb 80 when
`e648` (the test is `is_flag(0xe648) == true` in the ACMD body, `game_specials2` `0x71000f6ee0`). hitlag 1.0, sdi 1.0, effect `collision_attr_cutup`.
`add_speed` is a plain `Vector3f(-1,0,0)` with no lr factor in the script; **whether the engine applies x relative to facing is UNKNOWN**
(it must, or a left-facing dash would speed up; also unknown whether it adds to the dash energy or to another).

**Gravity / collision during a dash:** gravity accel of `K[0x3b4]` forced to 0 [28750:L513, ba70:L17-20]. Collision: kinetic type `K[0x4a0]`
+ correct `K[0x434]` (air correct), `set_passable_check(true)` for dashes 2-3. For dash 1: ground kinetic `K[0x410]` + correct
`K[0x414]` or `K[0x4b4]` by `e64c`, or air kinetic if started in air [b880:L5-30]. Pass-through platforms: the passable check is **on**
for dashes 2-3 (INFERRED meaning: soft platforms do not stop the dash); for dash 1 it is whatever the exe left.

**Follow-up input (DASH loop `2bd30`):**
* every frame: if `!is_flag(e650)` and `is_flag(e65c)` (window, ACMD motion frame 3..13) and
  `ControlModule::check_button_on(K[0x1d4])` -> `on_flag(e650)` [L20-48]. `K[0x1d4]` is a CONTROL_PAD_BUTTON constant I cannot name from our
  data (INFERRED: the special button, "B again"). The latch survives to the end of the dash and into SEARCH/TURN until the next dash start clears it.
* at motion end [L51-126]: if `attack_num-1 (=2) <= count` -> **END**. Else read `|stick|`: if **`|stick| >= 0.25`** -> SEARCH
  (`change_status(K[0xe4dc], true)`; if `count == 0` first call `27580` = default aim straight ahead); if `|stick| < 0.25` -> SEARCH **only if
  `e650` is latched** (same `27580` for count 0), **else END** [asm 2bd30 c200-c2f0 confirm the sense: `search_stick <= len` false -> branch to the flag test at c404].
  **So the chain continues on stick deflection alone, on the special button alone, or both.** The stick is sampled once, on the last frame of the
  motion (not during the dash, no steering mid-flight).
* After the third dash (count 2) the chain always ends. Max dashes 3.

## 6. Ground / wall / ceiling / ledge contact (DASH loop, `not is_changing`) [2bd30:L130-405]

* `touch = GroundModule::get_touch_flag()`; `floor = (touch & K[0x6ac]) != 0`.
* If `touch == 0` (not touching anything): `e678 = 0`.
* If `touch != 0`:
  * `e658` true (dash began on the ground; or "touching floor" tracking for dashes 2/3): consider only side/ceiling touches
    `touch & (K[0x3b8]|K[0x548]|K[0x3bc])`; none -> `e678 = 0`; some and slot `0x8` false: if `e678 >= 35` -> **END**, else `e678 += 1`. No angle test.
  * `e658` false (airborne dash): pick surface: floor (`K[0x6ac]`) with threshold `attack_hit_down_angle = 55`, or a side/ceiling normal
    (priority `K[0x548]` > `K[0x3b8]` > `K[0x3bc]`) with threshold `attack_hit_ground_angle = 65`. `theta = deg(vec2_angle(velocity, touch_normal)) - 90`
    (90 read from rodata). If `theta > threshold` (the dash is pressed within 25 degrees / 35 degrees of head-on) -> the same `e678` counter (+1 per frame, END at 35); else `e678 = 0` [L215-250].
  * The dash is **not** stopped or bounced by this code; the surface is resolved by the engine's `correct` kind. Only a 35-frame run of head-on contact ends the chain
    (never within a 12-frame dash unless `e678` carries over from earlier frames; it is only reset by the branches above, and its initial value is set outside the NRO).
* Dash 1 only: when the situation changes (ground<->air, prev vs current) the motion is re-selected (`special_s_1`/`special_air_s_1`, `inherit frame = true`) and
  `b880(false)` + `ba70` re-apply **horizontal `3.2*lr`** velocity [L355-370, asm 2bd30 ce68-cf48 for the `prev/cur` tests].
* Dashes 2/3: when "touching floor" changes, only the **motion** switches ground/air (`2afb0`, `inherit frame = true`) and `e658` follows [L384-395]; the situation stays AIR.
* Ledge: `sub_transition_group_check_air_cliff()` at the top of the DASH loop and END loop [2bd30:L7, 22f70:L5]: grab during dashes and during air END. Before the last dash cliff
  checking is forced on with custom hang data (SEARCH start, count 2) [18d80:L72-90] and restored to `K[0x584]` at SEARCH end [17500:L40].
* Blast-zone self-preservation: the "dead range" rule (3.6) is neutralised by `attack_dead_speed_mul = 1.0`.

## 7. END (status `e4e4`) [198b0, 223d0, 22f70]

Entry: motion `special_s_end` / `special_air_s_end` (`inherit = false`); `222a0`; `223d0`; `e684 = e668`. Motion rate `end_frame/N + 0.01` with
`N = end_frame_1/2/3 = 35/40/45` for `count == 1 / 2 / otherwise` (count has been incremented by DASH-END, so after dashes 1/2/3: 35/40/45)
[198b0:L14-51]. Ground clip 56 frames, air clip 41 frames (our dump), so **the END motion plays in exactly 35/40/45 frames**
(unless `CancelModule::is_enable_cancel` earlier; the motion-list cancel frame for `special_s_end` is not in our dump).

`223d0`: `set_limit_speed(K[0x498], -1, 0)`; ground: `set_brake(0.12, 0)` and `clear_unable_energy(K[0x4a8])`; air: `set_brake(0.35, 0)`, gravity-energy y speed
clamped to +-1.5, `set_accel(K[0x3b4], -0.08)`, `set_limit_speed(K[0x3b4], -1)`, `reset_energy(K[0x4a8])`, `set_stable_speed(K[0x4a8], air_speed_x_stable*0.5)`, `enable_energy(K[0x4a8])`
[223d0:L10-110]. (The air-control energy is re-enabled with half the stable speed: Sora can drift a little.)

Loop `22f70`: air-cliff transition returns early; if cancel is enabled -> `sub_wait_ground_check_common` (ground) / `sub_air_check_fall_common` (air) [L8-18, L143-150];
else, **if Sora has just landed** (`PREV != GROUND && CUR == GROUND`) **and the END motion frame >= `end_landing_fall_special_frame` (20)**: set landing lag float `K[0x5e0] = attack_landing_frame (20)`
and `change_status(K[0x5d0])` (INFERRED = landing-special status) [L24-56]; at **motion end**: ground -> `K[0x698]` (INFERRED = wait); air -> set `K[0x5e0] = 20` and `change_status(K[0x3ac])`
(INFERRED = fall special: **helpless after an aerial finish**) [L66-97]; if the situation changes mid-END the end clip is re-selected with `inherit frame = true` + `222a0`/`223d0` [L100-140].

## 8. Hit-dependent behaviour (flags `0xe648/0xe650/0xe654/0xe65c/0xe660`)

* **Nothing in the NRO's status code reads whether a dash hit.** There is no `AttackModule::is_attack`, no hit callback in the closure.
* `e65c` (window) is set/cleared by ACMD (frames 3 / 13); `e650` by the button check; `e654 = e650`; `e660` by stick sampling; `e648 = e654 && !e660` at dash start.
  So **`e648` means "the follow-up was requested with the special button and NOT aimed with the stick (target lock counts as not stick)"**, not "the previous dash connected".
  Effects: speed x1.15 [2b2d0:L67-76]; dash 2/3 hitboxes 5.2% instead of 3.0% (ACMD). It is the "tap B without aiming = faster, stronger" mode.
* Whether a hit changes anything else (e.g. `e644`, the notify-event at frame 11) is UNKNOWN: both are written/consumed outside the NRO.

## 9. Frame timelines (game frames; `+-1` where the frame-update order is unknown)

Dash = 12 frames: hitboxes up at motion frame 3 (game ~3), down at motion frame 11 (game ~10-11), -1/-0.5 slow-down at the same frame, input window motion frames 3-13.
SEARCH = `search_frame` 9 (+-1), TURN = 8, END = 35/40/45. The exe-side start motion (clip 15 frames, rate unknown) precedes dash 1 and is UNKNOWN.

### (a) one dash on the ground, no target, no input after
```
 start (exe)   dash 1: f1-f12                                END: 35 frames (end_frame_1), ground brake 0.12
 ...           vx = 3.2*lr, vy = 0 (x1.15 if e648)           (speed after f11 = 2.2) 
               hitbox f3..f10 (5.2%, angle 72)
               follow-up window f3..f13 (button), stick sampled at the last dash frame
 distance dash ~ 3.2*10 + 2.2*2 = ~36.4 units; END slide ~ 2.2^2/(2*0.12) = ~20 units (INFERRED, assumes the dash velocity carries into END)
 total after start ~ 12 + 35 = 47 frames
```
### (b) three dashes with stick directions (stick held through the whole move; no target)
```
 dash 1  f0-12      straight, 3.2, hit f3-10
 SEARCH  f12-21     (9) decelerate from min(|v|,2.0): air 0.34/frame, ground 0.24/frame; stick sampled each frame; aim = last |stick|>=0.25 angle
 TURN    f21-29     (8) facing flips unless the aim is within 20 deg of vertical; up/down/level clip; marker article switches at +7
 dash 2  f29-41     speed 2.944 (x0.85 if 40..140 deg; x1.15 if powered), heading = aim angle, hit f32-39 (3.0% or 5.2%, angle 108)
 SEARCH  f41-50     (aim carried from dash-2 pre-sample if the stick is still held)
 TURN    f50-58
 dash 3  f58-70     speed 2.708 (...), hit f61-68 (3.0%/5.2%, angle 46); last-dash ledge assist/dead-range rules
 END     f70-115    45 frames; air -> helpless fall, landing lag 20
 first active hitbox f3; per-dash travel ~ speed*10 + (speed-1 or -0.5)*2: dash 2 ~ 34 (2.944), dash 3 ~ 31 (2.708) (aimed up x0.85: ~29 / ~27)
 total ~ 115 frames from dash 1 start
```
### (c) air use with a target in range
```
 dash 1 (air): horizontal 3.2*lr, ignores target
 SEARCH: target acquired by the exe-side SEARCH handler (radius 50 sphere, bone top +4y); e664 = id; stick ignored
 window ends -> TURN: angle = atan2(target - joint) ; clip up/down/level by that angle; lr = sign(dx) unless within 20 deg of vertical
 dash 2: live target position re-read at dash start; v = (target - joint) normalised * 2.944 (x1.15 if button-only and no stick); NO x0.85
 dash 3: same with 2.708; if no floor within 150 below and the target is near the blast zone: x attack_dead_speed_mul = x1.0 (nothing)
 off-stage + special latched + no target-ledge: the SEARCH-end ledge assist aims dash 3 at the ledge instead
```

## 10. Facing-reversal summary

* DASH 1: facing never changes.
* TURN and DASH 2/3 start: `lr := sign(aim.x)` **unless** the aim angle is within 20 degrees of 90/270, in which case lr is unchanged; the flip itself is done by the exe's `set_turn_special_s` (TURN) or
  `PostureModule::set_lr` + `update_rot_y_lr` (DASH start). Mid-status flips mirror `e668` (`180 - a`) via the slot-`0x3078` callback.

## 11. Divergences: current port (`ports/ir/tools/trail_specials_geno.py`) vs the real move

Ranked by how visible they are to a player.

| # | port (line) | real | visibility |
|---|---|---|---|
| 1 | **Dash 1 is steered / target-locked** (lock-on + `steer_words` at `search_frame` of `SStart`, lines 495-496; `SDash1` runs `steer_up_mul_test`, 513-527). | Dash 1 is **always straight along facing at 3.2** (count 0 path, [28750:L66-83]); no SEARCH, no stick, no target before dash 1. | Highest: the first thing a player does. |
| 2 | One 8-frame "hover" (`HOVER = 8`, line 86, `SStart2`) between dashes, with a lock/aim call at frame `attack_turn_frame` (4) (line 502-506). | Two phases: **SEARCH ~9 frames** (cursor, stick sampled every frame, decel from <=2.0, SEARCH hitbox) **then TURN 8 frames** (turn clip, facing flip) = ~17 frames. The aim is the **last** stick sample of the 9-frame window, not a single sample at a frame. | Very high: pacing of every combo. |
| 3 | Aim clamps: `MAX_LOCK_DEG = 40` (line 62), `STEER_MAX_UP/DOWN = 60` (72-73), `STICK_DEG = 25` (63). | **No clamp.** Full 0-360 polar angle (`atan2`), continuous. A target direction is also unclamped. 40/140 and 220/320 only pick the turn clip (and 0.85 speed for 40-140 without a target). | Very high: straight up / straight down dashes are possible. |
| 4 | Follow-up input: special pressed in anim frames 1..12 of the dash (lines 531-535); neutral stick ends the move. | Continue iff **stick >= 0.25 on the last dash frame** OR **special latched during window (motion frames 3-13)**; stick alone suffices. No input -> END right after the dash (no hover). | High. |
| 5 | No cursor, no 360 aim display, no marker. | Aim cursor effect (stick) + lock marker article (target). | Medium (visual). |
| 6 | Dash speed constant `3.2` for all dashes (line 513 area, `speed = S["attack_speed_x"]`). | `3.2 * 0.92^count` (2.944, 2.708) `* 0.98^e644` `* 1.15 if powered`; x0.85 only when no target. | Medium-high (reach). |
| 7 | "Hit-branch": boost + hitbox set chosen from `ATTACK_CONNECTED_PREV` (`--sonic-hit-branch`, lines 18-22, 507-523, `SONIC_DASH_ENHANCE_MUL`). | Boost and the 5.2% set depend on **`special latched && !stick-aimed`**, not on a hit. Dash-1 hit is irrelevant. | Medium-high; wrong trigger. |
| 8 | Dash length = clip `cancel_frame` (13). | **12 frames** (`attack_frame`), rate `end/12+0.01`; hitboxes ~f3-10, slow-down at ~f10. | Medium. |
| 9 | Dashes 2/3 lift off only "aimed up" (`V_MOVE_F1 > 0.05`, line ~524). | Dashes 2-3 are **always airborne** (`set_situation(AIR)`), also when aimed level/down. | Medium. |
| 10 | "never down on the ground" (STEER comment line 73). | No ground restriction on the aim at all; a grounded aim-down dash 2 goes airborne into the floor. | Medium. |
| 11 | END: IASA at `end_frame_N` inside the 56/41-frame clip (lines ~539-547). | END clip is **rate-scaled to exactly 35/40/45 frames** (`rate = end_frame/N + 0.01`); N counts dashes taken (1/2/3). `end_frame_N` is the length, not an IASA frame. | Medium. |
| 12 | Air END: `vy = +end_speed_y (1.5)`, forward x `end_speed_x_mul_air` (lines ~548-551), `landing_lag = end_landing_fall_special_frame`. | Air END: `brake 0.35`, **gravity y clamped to +-1.5**, **gravity accel -0.08**, air-control re-enabled with `stable = air_speed_x_stable*0.5`; helpless fall afterwards with `landing lag = attack_landing_frame (20)`; `end_landing_fall_special_frame` is only the **motion-frame threshold** for landing-in-END. | Medium. |
| 13 | No contact logic. | Head-on contact counter (65/55 deg tests, 35-frame limit), motion ground/air re-select (dash 1: also velocity reset), ledge grab during dashes/END. | Low-medium. |
| 14 | No last-dash ledge assist. | Off-stage + special latched: dash 3 is aimed at the grabbable ledge (probe 150 down, `can_entry_cliff`). | Low-medium (recovery use). |
| 15 | Facing: `STEER_TURN` (line 74) any stick behind turns. | `lr := sign(aim.x)` **except within 20 deg of straight up/down**. | Low-medium. |
| 16 | Lock-on happens in the Geno hook with range 50 sphere (`LOCK_RANGE = 50`, line 61). | Same radius (SEARCH sphere r50 at top+4y) but acquired **during SEARCH only**, cleared at every SEARCH start, position re-read at each dash start; stick ignored when locked. Range value is right. | Low. |
| 17 | Speed multipliers `start_*` applied at SStart (lines 480-483). | `start_*` params are unused in the NRO (exe-side entry, UNKNOWN); plausible but unverified. | Low. |

## 12. Where the older notes were wrong or incomplete

* `_research/ultimate-sonic-blade-steering.md` said `27700` "also moves/rotates an effect, so using this result as the actual dash heading is inferred" - **wrong framing**: `27700` *is* the cursor/stick sampler and writes `e668`, which the dash init reads as its heading (CONFIRMED chain 27700 -> `e668` -> 28750:L420).
* It listed the first dash as possibly steerable ("exact transition needs tracing"): **dash 1 is unsteerable and untargeted** (count 0 branch).
* It listed `0x1719BF7EB5 = 10` among "unlabeled flags/counters"; it is the **marker-article lifetime padding**, not a speed factor.
* `_research/ultimate-trail-status.md` section 3 called `e648` "previous dash connected" (plausible but unproved): it is **special-latched && !stick-aimed**; the NRO has no hit input to it.
* It said the sample frame is "undetermined": the stick is sampled **every frame of the 9-frame SEARCH window** (and once at the last dash frame for the continue decision, and every frame of dash 2 for pre-sampling).
* It said the dash code "examines ground touch flags ... exact outcome not resolved": resolved (section 6): no stop/bounce, only the head-on frame counter -> END at 35.
* "`attack_down_angle_min/max` ... gate?" -> they only choose the `turn_down` clip (and have no effect on speed).
* The statement "the 25 degree stick angle is not supported" stands (there is no 25-degree anything).

## 13. UNKNOWN / outside the NRO (best-supported reading, and what decides it)

1. **Entry status / the first dash trigger** (exe, `FIGHTER_STATUS_KIND_SPECIAL_S` for trail): motion `special_s_start` (clip 15 frames), its rate, when it hands over to DASH, initial values of `e648/e650/e660/e678/e644/e668/e664`. Reading: a plain start (`start_*` params: ground x0.5 / brake 0.1; air x0.5, brake 0.01, `speed_y_mul 0.1`) then DASH with count 0. A *latched* `e650` at dash 1 (e.g. B held through the start) would give a **powered dash 1** (1.15x), because `e648 = e654 && !e660`; unknown whether the exe presets it. Decide by: disassembling the exe's trail special-S status.
2. **The target selection** (who sets `e664`, which target when several, what `get_special_s_target_pos` returns, whether `search_angle` filters). Reading: the exe takes the SEARCH sphere's hit(s) (nearest or first), stores the object id, and `get_special_s_target_pos` returns a body-centre point. Decide by: `FighterSpecializer_Trail` + the search-hit callback.
3. **`e644`** (the 0.98 factor): no NRO writer; likely incremented by the exe on some event (hit?). Effect small (x0.98 per count).
4. **`notify_event_msc_cmd(0x2127e37c07, K[0x1ec0])` at frame 11 of each dash (and frame 10 of the air END)**: exe event; effect unknown (possibly the cursor/marker article's cleanup, or a camera hint).
5. **`KineticModule::add_speed(-1/-0.5, 0, 0)` semantics** (lr-relative? onto which energy?).
6. **`turn_param_special_s`** [315,270,225,180]: inferred as a 4-frame yaw sequence for the facing flip (3.5); the exe `set_turn_special_s` decides.
7. **Meaning of `K[0x1d4]`** (the follow-up button) and of status ids `K[0x5d0]`, `K[0x3ac]`, `K[0x698]`, `K[0x2e4]`, `K[0x58]`: my roles (special button, landing-special, fall-special, wait, air, ground) are inferred from structure and parameter names.
8. **Gravity during SEARCH/TURN.** The dash statuses explicitly zero gravity accel; SEARCH/TURN only switch to kinetic type `K[0x4a0]` and brake the `K[0x498]` energy. Two readings: (i) `K[0x4a0]` has no gravity (hover, as I remember the move in game: from general knowledge of the game, not from our data) - consistent with the aim window being a hover; (ii) gravity runs and only the dash cancels it. Decide by: the exe const table value of `K[0x4a0]` and the energy set of that kinetic type.
9. **Exact SEARCH length** (9 or 10 frames: depends on whether the countdown callback runs before or after the loop in a frame) and the START motion's game-frame length.
10. **`trail_special_s_joint_id`** (the aim origin joint): not in `trail/param/vl.prc`; probably in a common param. The origin is a body joint (not `top`), so the heading is body-centre to target.
11. The **motion-list cancel frames** for `special_s_end`/`special_air_s_end`/`..._turn` (not in our dump of the motion list): when `CancelModule::is_enable_cancel` becomes true during END.
12. `e64c` (stop-at-ledge for the grounded dash 1), `e678`'s initial value, the `0x1CB542ADC0` (20) parameter, and `22d80`'s `K[0x1744]/K[0x1748]` (aim-reticle height?).
13. Marker article creation/status (`K[0xe66c]`, status `K[0xe690]`): the NRO only sets its int and switches/removes it; its model/behaviour is in the weapon part of the NRO (not decompiled here) / exe.

## 14. Implementation checklist for the Geno rewrite (derived, not new facts)

1. State machine: START (exe-equivalent) -> DASH1 (straight, 12 frames) -> [continue? stick>=0.25 at last frame OR special latched in motion-frames 3-13] -> SEARCH(9) -> TURN(8) -> DASH2 -> same -> DASH3 -> END(45) ; END(35/40) when the chain stops after dash 1/2.
2. Keep one stored angle in degrees [0,360) (`e668`), `-1` = none; sample stick every SEARCH frame (and every dash-2 frame for `e67c`), update only when `|stick| >= 0.25`; target lock overrides; neutral+latched = straight ahead; neutral+not latched = END.
3. Dash velocity = `(cos a, sin a) * speed`, speed table in section 5, 0.85 only without a target, set once at dash start; slow-down at motion frame 11 (-1 / -0.5); gravity off during dashes.
4. Facing = sign(cos a) unless |a-90| <= 20 or |a-270| <= 20. Dashes 2/3 always airborne.
5. Powered flag at dash start = latched && !stickAimed (+ speed 1.15, damage 5.2 sets); not hit-based.
6. END length 35/40/45 rate-scaled; air: brake 0.35, y clamp +-1.5, gravity 0.08, helpless; ground brake 0.12.
