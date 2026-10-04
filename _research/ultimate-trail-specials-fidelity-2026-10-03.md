# Sora (`trail`) port fidelity audit: neutral, up, down special and status-driven mechanics

Research dated 2026-10-03. Read-only: no tracked file edited, nothing built or run. Scope excludes the side special (Sonic Blade), which another agent specifies. This note supersedes none of `_research/ultimate-trail-status.md` or `_research/ultimate-trail-jab-chain.md`; it extends them (status decompiles that were "unresolved" there are traced further below) and corrects one inference of theirs (see 4.1).

Tags: **CONFIRMED** = present in the cited decompile / param / ACMD row. **INFERRED** = interpretation of confirmed operations (name, idiom, gameplay meaning). **UNKNOWN** = not derivable from our data. Statements from my general memory of Ultimate are labelled "from general knowledge of the game, not from our data" and are never used as evidence.

## 0. Method, sources and a hard limit

- NRO loaded fine. `lua2cpp_trail.nro` (6.1 MB) and `lua2cpp_common.nro` (8.4 MB) both import and decompile headlessly with the bundled Ghidra 12.1.2. Ghidra's launcher rejects project paths containing an apostrophe, so my projects live in the session scratchpad (a copy of `~/ghidra-projects/sora.gpr`, read-only, plus a fresh import of the common NRO with analysis); outputs were copied to `_build/tmp/trail-fidelity/` (`ghidra-status/` and `ghidra-status2/` raw trail decompiles, `ann/` and `ann2/` the same with Hash40 labels resolved from `ParamLabels.csv`/`motion-labels.txt`, `ghidra-common/` + `ann-common/` named decompiles of `L2CFighterCommon::status_*`, `show.py`/`show2.py` ACMD viewers, `common-prc.xml` = decoded `fighter/common/param/common.prc`).
- The previous project had almost no function boundaries defined (24 hand-picked status functions). I found function starts by scanning the status code range 0x7100000480-0x7100039860 for BL targets and ADRP+ADD pointers (288 functions) and decompiled them. Addresses below are Ghidra VAs in `lua2cpp_trail.nro` unless marked `common:`.
- **Hard limit on every decompile quote.** The decompiler drops the arguments of `L2CAgent::push_lua_stack` calls, so for `sv_kinetic_energy::set_speed/set_accel/set_brake/reset_energy/...` the structure, the param names read, and the order are recoverable but not which value feeds which slot. I only claim numeric wiring where it is visible (`get_jump_speed_y(distance, accel)`, `speed * lr`, `x * attack_mul` and similar).
- Status/work-flag identifiers are `const_value_table` offsets (`+0xe4fc`, `0xe610` ...). The table lives in the main executable, so those are positional IDs, not names. Names such as "N1START" are INFERRED from the motion hash the status plays.
- Status registration maps: `0x7100005910` registers statuses +0xe4f4..+0xe50c with (PRE, MAIN, END) triples; `0x7100004260` registers the special statuses +0xb8 (Special Hi: main `0x710001af70`, end `0x7100017ef0`), +0xc4 (Special S: main `0x7100018c40`), +0xd0 (Special LW: main `0x7100019d50`, end `0x7100017850`), +0xe4d8-+0xe4f0 (Sonic Blade and Counter sub-statuses), and Sora overrides of common statuses (0x19c AttackS3 end `0x71000181f0`, main `0x710001b4a0`; 0x238 JumpSquat `0x710001b700`; 0x25c JumpAerial `0x710001b830`; 0x338 AttackAir `0x710001b8b0`; 0x28ec WalkBrake `0x710001b2e0`; 0x4d4 AttackLw4; 0x138/0x86c/0x870 ItemSwingS4*; 0x39c GenesisGet; 0x280 Appeal). Common-status names for these are INFERRED from the calls they make.

---

## 1. Neutral special (Magic: Firaga / Blizzaga / Thundaga)

### 1.1 Real behaviour

**Statuses (CONFIRMED structure; names INFERRED from motion hashes):**

| status | pre / main / end | what main does |
|---|---|---|
| +0xe4fc N1START | `0x71000086d0` / `0x7100008ab0` / `0x7100008d80` | plays `special_n1_start` / `special_air_n1_start` (hash `0x108a69b021`/`0x140bdc3f61`); shifts to loop `0x7100012ca0`: each frame `sub_exec_special_start_common_kinetic_setting(param_special_n)`, on `MotionModule::is_end` -> `change_status(+0xe500)` |
| +0xe500 N1 | `0x7100008e30` / `0x7100009210` / `0x7100009350` | motion `special_n1`/`special_air_n1`; loop `0x7100012210` (below) |
| +0xe504 N1END | `0x7100009400` / `0x71000097e0` / `0x7100009920` | motion `special_n1_end`/`special_air_n1_end`; loop `0x7100011a00` |
| +0xe508 N2 | `0x7100009960` / `0x7100009d40` / `0x710000a190` | motion `special_n2`/`special_air_n2`; loop `0x7100011450` |
| +0xe50c N3 | `0x710000a1d0` / `0x710000a5b0` / `0x710000aa80` | motion `special_n3`/`special_air_n3`; loop `0x7100010b20` |

The N2 and N3 loops are identical in shape (`0x7100011450`, `0x7100010b20`): `CancelModule::is_enable_cancel` -> wait/fall transition checks (cancel allowed from the clip's `cancel_frame`, N2 63, N3 70 in `motion` rows); each frame `sub_exec_special_start_common_kinetic_setting(param_special_n)` + `sub_set_ground_correct_by_situation` + the air-hop helper `0x7100010fb0`; at `MotionModule::is_end` -> Wait (`+0x698`) on ground, Fall (`+0x458`) in air. CONFIRMED.

**Cycle order and when it advances.** `FighterSpecializer_Trail::change_magic` is imported (implementation in the main executable: UNKNOWN, see section 5). The five call sites are all in status END functions (CONFIRMED):

- `0x7100008d80` (END of N1START): `if (next_status != +0xe500) change_magic`
- `0x7100009350` (END of N1): `if (next_status != +0xe504) change_magic`
- `0x7100009920` (END of N1END): unconditional
- `0x710000a190` (END of N2): unconditional
- `0x710000aa80` (END of N3): `ArticleModule::remove_exist(0x52fc)` then unconditional

INFERRED (idiom, `this[200]` is read as the status being entered): the element advances when a cast status is *left*, whatever the reason, and Firaga's start/fire statuses skip the advance only while the repeat chain continues (N1START->N1, N1->N1END). So the advance is "end of the cast" rather than "at the moment of firing", and an interrupted N1START (hit before the fireball) also advances. Which element follows which is not in the NRO. From general knowledge of the game, not from our data: the cycle is Firaga, Blizzaga, Thundaga, repeat.

**Charge / hold behaviour (Firaga repeat).** N1 loop `0x7100012210` (CONFIRMED structure):
- While the motion is `special_n1`: ACMD raises work flag `0x52e0` at f0 and drops it at f14 (`game_specialn1`). While `0x52e0` is on, if the special-input command bit (`+0xd8c`) is set and `|stick_x| < common.special_stick_x` and `|stick_y| < common.special_stick_y` (decoded `common.prc`: **0.6 and 0.5**), it sets repeat flag `0x52e4`.
- At motion end: no repeat flag -> `change_status(+0xe504)` (N1END). Repeat flag -> clear both flags, switch to motion `special_n12` / `special_air_n12` (clip 31 frames, `FT_MOTION_RATE 0.5` from f0, `FT_START_ADJUST_MOTION_FRAME_REVISED 1` at f26: `game_specialn12`), and when `special_n12` ends it goes back to `special_n1` (which generates a new fireball at its f0).
- No fire-count limit is visible in this function. `magic_window_frame` = 10 (`param_special_n`, all three populated structs) is not read by any decompiled trail function (searched hash `0x12b266329e`): UNKNOWN where it is used.
- `trail_fire` has two hit scripts: `game_fly` (hitstun add 9/7/5 on its three damage stages) and `game_fly2` (add 1/-1/-3). The reduced variant is INFERRED to be for repeat shots; where the choice is made is UNKNOWN (weapon agent).

**Air behaviour (all three spells).** `FUN_7100010fb0` (called from the N1 loop and the N2/N3 loops), CONFIRMED structure: first time per cast in `SITUATION_AIR`, add speed via `sv_kinetic_energy::add_speed` using `param_special_n.hop_add_speed_x` (-0.3) times `PostureModule::lr` and `hop_add_speed_y` (1.0): a small hop back and up. Only index 0 (Firaga) has nonzero `hop_add_*`; indices 1 and 2 are 0 (`vl.prc` `param_special_n`), so the hop reads the same struct for all three spells (read at index 0 in the decompile: INFERRED).
Per-frame `sub_exec_special_start_common_kinetic_setting(param_special_n)` (`common:0x710005e510`, `..._inner 0x710005cc50`, `..._gravity_func 0x710005cd00`) and the start-time `common:0x710005b2f0` read these params: `start_speed_x_mul_ground/air`, `start_brake_x_ground/air`, `start_control_accel_x_mul_air`, `start_control_max_speed_x_mul_air`, `start_stop_y_frame_air`, `start_speed_y_air`, `start_speed_y_mul_air`, `start_speed_y_add_air`, `start_accel_y_mul_air`, `start_max_speed_y_mul_air`. Values for struct 0 (Firaga): 0.8 / 0.1 ground; air 0.9, brake 0.011, control accel 0.3, control max 0.6, stop_y 0, accel_y 0.95, max_speed_y 0.75, speed_y_air 0.8, speed_y_mul 0, speed_y_add 0. Struct 1 (Blizzaga) differs only in ground x mul 0.5; struct 2 (Thundaga) same as 1. Meaning (reduced air control, damped x speed, softened gravity during the cast) is INFERRED from the names; exact formulas are hidden by the stack-push limit.
Cast placement params (struct 0, Firaga): `fire_offset_x/y` 13.6 / 7.4; struct 1 (Blizzaga): `ice_offset_x/y` 7.6 / 6.8; both CONFIRMED values; their use by the weapon spawn is INFERRED.

**Firaga (fireball).**
- Timeline (CONFIRMED, `game_specialn1start`): clip `d00specialn1start` 18 frames, `FT_MOTION_RATE 0.8` f1-10, 1.0 after. A **zero-damage ATTACK** at f16: id 0, angle 361, kbg 100, fkb 55, bkb 0, size 2.8, capsule bone `top` (0,7.2,3.2)->(0,7.2,12.6), rehit 1 (a close-range sensor; its purpose is UNKNOWN). Then status N1, `game_specialn1` (clip 15 frames; `FT_MOTION_RATE 2` f1-6): `ArticleModule::generate_article(0xf3ec)` at f0 plus flags `0x52e0` (f0-14), `0xf3e8`, `0xf3f0`.
- Weapon (`trail_fire`, `game_fly` and `FUN_7100031cf0`, `FUN_7100032670`): life = `param_fire.life` **40**; speed = `param_fire.speed` **1.65** * `lr` set once via `sv_kinetic_energy::set_speed` (straight line). Hitboxes: f0 5.6%, f10 5.2%, f20 4.8%; angle 361, kbg 24/22/20, bkb 42/36/32, size 3.8, fire element, `ATK_SET_SHIELD_SETOFF_MUL2 1.05`, hitlag 1.0, reflectable and absorbable. Main loop: `life <= 0` -> `notify_event_msc_cmd(0x199c462b5d)` (remove); `sub_ground_module_is_touch_all_consider_speed` (terrain contact) or a hit flag (`+0xe6b4`) -> `change_status(+0xe6a8)` after a 2-frame `StopModule::set_other_stop`. So the fireball vanishes on terrain contact. Map-collision shape: rhombus half-width/up/down 1.6 (`map_collision_fire`).
- Cast end: `special_n1_end` clip 30 frames, `FT_MOTION_RATE 0.4` f0, 0.5 from f11, 1.0 from f15, `cancel_frame` 16.

**Blizzaga (ice).** CONFIRMED (`game_specialn2`, clip `d00specialn2` 63 frames, cancel 63): `FT_MOTION_RATE 0.5` f1-19, 1.0 f19-24, 1.25 f24-40, 1.0 f40-42, 0.8 f42+. Zero-damage ATTACK at f22 (id 0, angle 361, fkb 40, size 3.2, capsule (0,6.4,2.2)->(0,6.4,5.2), rehit 2). f24: `clear`, then **8 shards**: `ArticleModule::generate_article(0xf3f8)` at f24, 26, 28, 30, 32, 34, 36, 38 with angle floats (`WorkModule::set_float(.., 0xf3f4)`) 4, 16, -8, 24, -2, 12, -14, 0; flag `0xf3fc` at f24, flag `0xf400` at f38 (marks the last shard). Body hit at f40: id 0, 1.8% angle 42 kbg 64 bkb 52, size 3.2, capsule (0,6.4,2.2)->(0,6.4,6.4), rehit 0, cleared f42 (`collision_attr` of the body hit is not shown in my extract; see the ACMD row).
Shard (`trail_ice`, `game_fly`): speed `param_ice.speed` 3.6, `brake` 0.18, `stable_speed` 0.2; ATTACK f0 2.4% angle 70 kbg 12 bkb 92 size 2.0, f3 size 1.6 bkb 86, f6 bkb 74; ice element; `notify_event_msc_cmd(0x199c462b5d)` (the same removal event the fireball fires on expiry) at **f13**. Last shard (`0xc00a3e2ad`): 3.6% angle 80 kbg 100 fkb 82 size 2.8 (f0) -> fkb 68 size 2.4 (f5), hitstun add 8/6, same removal event at **f15**. Shard main (`FUN_71000357b0`): terrain contact -> removal (2-frame other-stop first). Blizzaga status flags the "freeze" as an element only (`collision_attr_ice`); freeze rules are engine-side: UNKNOWN.
Derived (arithmetic on confirmed numbers): a normal shard travels sum(3.6 - 0.18 k, k=0..12) = 32.8 units before its removal event at f13; the last shard sum(.., k=0..14) = 37.2 units at f15.

**Thundaga.** CONFIRMED (`game_specialn3`, clip `d00specialn3` 90 frames, cancel 70, no rate changes): at f26, f40, f54 (the f40/f54 are `wait [14]` after the previous): `WorkModule::set_int(idx 0,1,2, 0x52f4)` then `ArticleModule::generate_article(0x52fc)` (cloud); flag `0xf404` at f26; `off_flag 0xf3e8` at f60. Cloud placement relative to Sora is decided in the cloud weapon's own status script and its `trail_cloud` ACMD (`game_start`: only `frame 20`): UNKNOWN (the cloud weapon's status functions are not in the region I could resolve; see 5).
Bolt (`trail_thunder`; `FUN_71000376a0`, `FUN_7100036f60`, `FUN_7100039310`): `param_thunder.speed` **-3.8** (falls), `generate_frame` 3, `length` 90, `through_length` 45, `model_size` 50, `detach_frame` 20. The decompile scales the bolt joint's Y by (distance to the ground / `model_size`) clamped by `max(..)` with a sign flip flag, i.e. the model is a beam stretched to the floor; `FUN_71000383a0` detaches the `trail_thunder_bullet_top` effect at `detach_frame` 20. Hitboxes (`game_fall`): f1 5.2% angle 10 kbg 26 bkb 52 size 3.6 at (0,0.4,0); f5 angle 50 bkb 94 with a capsule (0,0.4,0)->(0,10.0,0). Third strike (`0xdbd48edf3`): angle 64 kbg 140 bkb 62 (stronger launch). Air variants (`game_fallair`): angle 344 bkb 48 then angle 68 bkb 98 (f0/f4). `game_landing` is a QUAKE only. Map collision rhombus 1.2.

### 1.2 Current port

Sources: `ports/ir/tools/trail_magic_geno.py`, generated `_build/audit-20261003/sora-regen/staged-magic/geno.json` (merged into `staged-install/geno.json`, states 0-5, articles 0-10).
- **Cycle**: LA int 0 (`SET_LA0`) set to the next element when the cast generates its spell: Firaga sets 1 at the spawn event (trail_magic_geno.py:369), Blizzaga sets 2 at its first shard time (:397), Thundaga sets 0 (:409). `specials.n` selects by `la_i:0` (geno.json `specials`). Selection works in the air via `air_n`.
- **Casts**: six Geno states (`Firaga`, `Blizzaga`, `Thundaga`, `*Air`), each a single state whose clip is a stand-in (see 1.3 row 1) with `phys: ground` or `air`, ending `CHG Wait` (:344-357). Firaga is one state for N1START+N1+N1END (73 game frames ground / 69 air, events at game f18 clear detector, f20 spawn). Timing uses the ACMD `FT_MOTION_RATE` segments (`game_time`, :111-124).
- **Firaga**: one fireball, article `Fire` lifetime 40, velocity (1.65, 0), spawn offset (13.6, 7.4) (:301), three hitbox stages (damage rounded 6/5/5, stun 9/7/5), model `GnTrailFire.dat`. The zero-damage detector is emitted as a fighter hitbox with HBFLAGS 7 (firaga_detector_events, :244-253). The repeat loop is **not ported** (:27, :278).
- **Blizzaga**: 8 shards at the ACMD frames with the ACMD angles, `ICE_LIFE = 30` (INFERRED, :53) with velocity 3.6, accel -0.18, min speed 0.2, spawn (7.6, 6.8); last shard is article `IceLast`; body hit at f40 emitted as a fighter hitbox; the f22 zero-damage hitbox is ported.
- **Thundaga**: three `Cloud` articles at `CLOUD_SPAWNS = [[15,32],[26,32],[37,32]]` (forward, up; INFERRED :54), `CLOUD_LIFE 30` (INFERRED), each spawning a `Bolt` child at frame `generate_frame` 3; `Bolt` article lifetime `round(90/3.8)` = 24, velocity (0,-3.8), `despawn: stage`.
- Physics: `phys: air` / `ground` default Melee physics. No `start_*`, `hop_add_*` or `control_*` param is read anywhere in `trail_magic_geno.py` (grep for `hop_add|start_speed|control_accel` returns nothing).

### 1.3 Divergences (neutral special)

| # | Real | Port | Player impact | Fix (size; new Geno capability?) |
|---|---|---|---|---|
| N1 | Casts play `d00specialn1start/n1/n1end`, `n2`, `n3` (and air clips); all 12 clips exist in `fighter/trail/motion/body/c00` | The six cast states sit on host rows 149-155 (ItemScope rows). `INSTALL.json` `conversion` entries map **`h12itemscope*`** clips to those rows: 149 `h12itemscopestart`, 150 `h12itemscoperapid`, 151 `h12itemscopefire`, 152 `h12itemscopeend`, 153 `h12itemscopeairstart`, 154 `h12itemscopeairrapid`, 155 `h12itemscopeairfire` (CONFIRMED in `INSTALL.json`). The `magic_geno` header says the stand-in is deliberate "until Sora's own clips exist" (trail_magic_geno.py:57). | Very high: Sora fires every spell with a ray-gun-holding pose; wrong timing against the hit events, wrong silhouette | M (add the 12 clips to a `--row-clips` map like the physical specials; re-time the three-part Firaga). No new engine |
| N2 | Air casts: hop (+1.0 y, -0.3 x*lr), damped x speed (0.9, brake 0.011), air control 0.3/0.6, gravity 0.95/max fall 0.75 (INFERRED meaning) | Plain Melee air physics, no hop | High (air magic is a mobility tool; port falls normally) | S-M (Geno `PUTF` at cast start, `air` phys variant; the specials generator already does this for Aerial Sweep/Counter). No new engine |
| N3 | Firaga repeat: re-press in N1 f0-14 with stick |x|<0.6, |y|<0.5 -> `special_n12` -> another fireball; `game_fly2` hitstun variant | One fireball | High (changes Firaga from a single shot to a barrage and its pressure) | M (CHG-on-press inside the Firaga state + loop; fireball article variant with `game_fly2` hitstun). No new engine; fire-count cap UNKNOWN |
| N4 | Ice shard removal event at f13 (normal) / f15 (last) of the weapon script; terrain contact removes it | `ICE_LIFE 30` (INFERRED); shard slides to ~39 units over 30 frames at <0.2 speed after f19 | Medium (shards linger and travel ~7 units farther) | S: set lifetime 13 / 15; add stage despawn like Bolt. No new engine |
| N5 | `change_magic` runs at status exit (and an N1START interrupted before the shot also advances) | Advance at the spawn event, Firaga after the shot, Blizzaga at first shard | Low-medium (differs when a cast is hit/cancelled; Blizzaga advances before the move finishes) | M; needs a state-exit hook (`on end/CHG`) if one exists, else keep at spawn: possibly new Geno capability |
| N6 | Thundaga cloud placement and bolt-to-floor beam | Fixed 15/26/37 forward x 32 up (INFERRED), falling 24-frame projectile | Medium-high (visible) but real values UNKNOWN | L until the cloud weapon status is read; no engine yet known |
| N7 | Fireball vanishes on terrain contact (`FUN_7100032670`) | `Fire` has no stage despawn (Bolt does) | Medium (fireball passes through walls/floors) | S: add `despawn.stage` to `Fire`. No new engine |
| N8 | Zero-damage sensors at Firaga f16 and Blizzaga f22 (purpose UNKNOWN) | Ported as HBFLAGS-7 hitboxes (done) | None known | n/a |
| N9 | Cancel at `cancel_frame` N2 63, N3 70; Firaga end 16 anim frames | Ported (IASA at those frames) | None | n/a |

---

## 2. Up special (Aerial Sweep)

### 2.1 Real behaviour

**Parameters (CONFIRMED, `param_special_hi` struct 0):** `start_speed_x_mul_ground` 0.5, `start_brake_x_ground` 0.1, `start_speed_x_mul_air` 0.4, `start_brake_x_air` 0.01, `start_control_accel_x_mul_air` 0.8, `start_control_max_speed_x_mul_air` 0.6, `start_accel_y_mul_air` 0.7, `start_max_speed_y_mul_air` 0.9, `start_speed_y_air` 0, `start_speed_y_mul_air` 0.1, `jump_distance` **55**, `jump_distance_mul` **0.8**, `jump_accel_y` **0.04**, `jump_accel_x_add` 0.12, `jump_speed_x_mul` 0.6, `fall_accel_x_mul` 0.04, `fall_max_speed_x` 0.8, `fall_special_accel_x_mul` 1.0, `fall_special_max_speed_x_mul` 0.9, `landing_frame` **21**. Structs 1-3 are all zero.

**Start (`0x710001af70`, CONFIRMED):** `sub_change_motion_by_situation(special_hi, special_air_hi)`; `sub_set_special_start_common_kinetic_setting(param_special_hi)`; stores `landing_frame` (21) into work float `+0x5e0`; `enable_transition_term(+0xc0)`; `GroundModule::select_cliff_hangdata(+0xe5fc)`; shifts to loop `0x710001cd10`. End (`0x7100017ef0`): re-selects default cliff data (`+0x584`) and, if the next status is `+0x3ac` (special fall), writes `fall_special_accel_x_mul`/`fall_special_max_speed_x_mul` into work floats `+0x2398/+0x239c`. The vl.prc `cliff_hang_data` list has 3 entries: [0] and [2] the normal box (16,22.5)/(-9.6,8.5), [1] (100,100)/(-100,-100) (a 200x200 box). Which index `+0xe5fc` selects is UNKNOWN (the Sonic Blade search uses a different constant, `+0xe688`, at `0x7100018d80`).

**Loop (`0x710001cd10`, CONFIRMED structure):**
1. `sub_transition_group_check_air_cliff()` -> ledge grab enters the cliff status immediately.
2. Each frame: `sub_exec_special_start_common_kinetic_setting(param_special_hi)` (the damped start phase).
3. ACMD flag `0xe610` raised at animation f7 (`game_specialhi`; `FT_MOTION_RATE 2` over f4-6): on seeing it the loop clears it, sets `0xe604`, switches ground correct / kinetic type, and in the air-or-ground **launches the rise**: `jump_distance` (times `jump_distance_mul` **only when the situation is AIR**) and `jump_accel_y` -> `KineticUtility::get_jump_speed_y(distance, accel)` -> vertical energy `reset_energy` / `set_speed` / `set_limit_speed` to that speed and `set_accel(-jump_accel_y)` (the `operator-` of the accel is visible). Horizontal energy is reset to zero with `air_speed_x_stable * jump_speed_x_mul` (0.96 * 0.6 = 0.576) as the speed cap and `jump_accel_x_add` (0.12) added to accel (INFERRED wiring).
4. Work flag `0xe60c` (set outside the NRO's visible code: UNKNOWN who raises it): clears it, then sets x accel mul / max from `fall_accel_x_mul` (0.04) and `fall_max_speed_x` (0.8).
5. **Cancel window.** ACMD raises flag `0xe600` at f48 and drops it at f70 (`game_specialhi`). While it is on, if `WorkModule::is_enable_transition_term(+0xc0)` and `sub_transition_term_id_cont_disguise` pass, the loop does `change_status(+0xc4)`. `+0xc4` is the status whose main is `0x7100018c40` = the Special **S** status (it loads `param_special_s` and `special_s_start`). So Sora can cancel Aerial Sweep into the side special during animation f48-70 (the exact input guard inside the transition term is UNKNOWN). CONFIRMED structure; consistent with, from general knowledge of the game, not from our data, Sora being able to follow Aerial Sweep with Sonic Blade.
6. `0xe608` flag and ground contact -> `change_status(+0x5d0)` (landing, with the 21-frame lag stored at +0x5e0). At motion end: ground -> +0x5d0, air -> `+0x3ac` (special fall).

**Hit structure (CONFIRMED, `game_specialhi` / `game_specialairhi` identical, clip `d02specialhi` 79 frames; `FT_MOTION_RATE 2` f4-6 and f75-79):**
- f7: ids 0,1 (3.8%, angle 86/88, fkb 116/82 set_weight true, size 4.2, points (0,4.2/12.6,7.6)); f8: ids 2,3 at z 16.8, ids 4,5 are capsules z 7.6->16.8 at y 4.2 / 12.6; clear_all f10. Angles 86-110, `collision_attr_cutup`, hitlag 0.3.
- f15 (2.1%, size 2.4, behind Sora z -6.6/-12.2, angles 80-108, six hitboxes), f18 (2.1%, size 2.8, front, six), f22 (2.1% behind), f25 (2.1% front), f29 (2.1%, behind, angles 125-150 fkb 110-150: the up-and-back sweep), each lasting three frames and cleared (f18, f21, f25, f28, f32).
- f39-42: five hitboxes 4.6%, angle 62, **kbg 176, bkb 44** (`set_weight false`), bone `haver` at (0,0,0),(0,4.6,0),(0,9.2,0) size 3.6, plus bone `top` capsule (0,7.4,8.4)->(0,9.6,8.4) size 5.2 and (0,12.6,15.6)->(0,14.8,15.6) size 4.8; hitlag 1.0. Max total if all hits connect: 3.8 + 5*2.1 + 4.6 = 18.9%.
- `notify_event_msc_cmd(0x2127e37c07, 0x1ec0)` at f21 (a camera/effect event; meaning UNKNOWN).

### 2.2 Current port

`trail_specials_geno.py:562-588` (states `Hi`, `HiAir`; generated in `staged-install/geno.json` states 13-14): `phys air_drift`, `coll anim_motion`, `ledge front`, `landing_lag 21`; at f0 multiplies ground velocity by `start_speed_x_mul_ground` and Y by `start_speed_y_mul_air`; at the rise frame (`g0` = game frame of the 0xe610 flag) sets `V_AIR` and multiplies x velocity by `jump_speed_x_mul`, then per frame `PUTF V_VEL_Y, v0 - a*(f-g0)` with `v0 = sqrt(2*a*dist)`, `dist = 55` (x0.8 air), `a = 0.04` (INFERRED profile, :573-580; the header lists it as INFERRED). Hitboxes follow the ACMD through `hit_events`. At the end `CHG(MS_FALLSPECIAL)`. 

### 2.3 Divergences (up special)

| # | Real | Port | Impact | Fix |
|---|---|---|---|---|
| U1 | Cancel into Special S (Sonic Blade) in anim f48-70 | None: runs to the end, then helpless fall | High for recovery play (the largest functional gap of this move) | M: a `CHG` on special press during the window (target `geno:SStart`); the window frames convert through the FT_MOTION_RATE table. No new engine if `CHG PRESSED` accepts the Special button as in the Sonic hit branch; the stick-side guard UNKNOWN |
| U2 | 6 hitboxes per hit; Melee has 4 slots. ids 4-5 (the connecting capsules) dropped at every one of the 7 hit frames; final hit drops `top` capsule id 3 (size 5.2) and id 4 (size 4.8) and replaces id 2 (conversion_losses: "four Melee hitbox slots") | Hit frames keep ids 0-3 only | Medium (tip/upper reach of the finisher; gaps between the point spheres: 9.2 spacing vs 4.2 radius leaves ~0.8 unit gaps) | S-M: repack with the position check; a real fix needs more hitbox slots: possible new engine capability |
| U3 | Rise speed from `get_jump_speed_y` then accel -0.04; vertical limit = v0 | Same shape (v0 = sqrt(2*a*dist) INFERRED; a for the 44-unit air case) | Low (formula unverified, shape matches) | S: verify `get_jump_speed_y` (main exe) in game |
| U4 | Start phase: x damped 0.5/0.4, brake, **gravity 0.7x and max fall 0.9x** (air), control 0.8/0.6, y speed 0.1x | Only the two multiplies at f0; no gravity change, no control change; air drift is plain `air_drift` | Low-medium (feel of the 7 pre-rise frames) | S |
| U5 | Rise-phase x: speed cap 0.96*0.6, accel add 0.12 | `V_VEL_X *= 0.6` once, normal drift thereafter | Low-medium (steering during the rise) | S-M |
| U6 | Special fall afterwards uses `fall_special_accel_x_mul` 1.0 / `fall_special_max_speed_x_mul` 0.9 | Melee special-fall (Geno `MS_FALLSPECIAL`) defaults | Low | S |
| U7 | Landing 21 frames via status +0x5d0 | `landing_lag 21` (done) | None | n/a |
| U8 | Ledge-grab box chosen by `select_cliff_hangdata` (index UNKNOWN, one entry is a 200x200 box) | `ledge: front` | Unknown (could be large) | UNKNOWN |
| U9 | `0xe60c` after-hit control (accel 0.04, max 0.8): set elsewhere | Not ported | Unknown | UNKNOWN |

---

## 3. Down special (Counter Attack)

### 3.1 Real behaviour

**Parameters (CONFIRMED, `param_special_lw` struct 0):** `start_speed_x_mul_ground` 0.5, `start_brake_x_ground` 0.05, `start_speed_x_mul_air` 0.4, `start_brake_x_air` 0.01, `start_control_accel_x_mul_air` 0.1, `..._max_speed_x_mul_air` 0.5, `start_accel_y_mul_air` 0.7, `start_max_speed_y_mul_air` 0.7, `start_speed_y_mul_air` 0.4, `start_speed_y_add_air` 0.1, `control_accel_x_mul` 0.7, `control_max_speed_x_mul` 0.7, `hitstop_frame_direct` 6, `hitstop_frame` 4, `reflect_angle` 145, `shake_min/max/mul` 1/25/1.5, `ground_frame` 14, `air_frame` 10, `rebound_start_ground` 25, `rebound_frame_ground` 1, `rebound_start_air` 30, `rebound_frame_air` 1, `rebound_speed_y` 0.02, `rebound_speed_y_max` 0.3, `target_speed_x` 0.9, `target_speed_y` 1.9, `speed_x` **0.45**, `speed_y` **1.1**, `attack_mul` **1.5**, `attack_min` **9**, `attack_max` **30**, `attack_max_for_enemy` 30, `rebound_distance_min/max` 0.9 / 4.3, `rebound_speed_mul_f_min/max` 0.1 / 2.3, `rebound_speed_mul_b_min/max` 1.1 / 0.1, `rebound_attack_start_frame` 4, `rebound_height` 1.9, `rebound_approach` 0.6, `shield_parts_no` top, `shield_size` 4, shield offsets (0,2,7)-(0,16.1,7.1), `shield_attack_mul` 1.4, `shield_speed_mul` 1.8, `shield_life_mul` 0.5, `shield_limit` 80, `motion_rate` 1.

**Window / trigger (CONFIRMED, previous note + `0x7100021240`, `0x71000210a0`):** start status plays `special_lw_start` / `special_air_lw_start`; ACMD (`game_speciallwstart`): intangible `xlu` f7-9 (motion row), flag `0xe61c` raised at f8 and lowered at f26, `enable_fix_jostle_area(9,3)` at f7 and `(4,4)` at f24, `cancel_frame` 52. The start callback toggles `ShieldModule` and `ReflectorModule` from `0xe618/0xe61c`. So the active window is anim f8-26. The shield/reflector parameters (`shield_*`) indicate the window both counters melee and reflects projectiles with a damage x1.4 / speed x1.8 / life x0.5 (INFERRED from names; "does it reflect" is not stated by any code I read). The branch that picks the attack status after a hit is `+0xe4ec` (when flag `0xe630` is true) or `+0xe4f0` (false); what raises `0xe628` and the producer of the counter event live outside the NRO (UNKNOWN). 

**Counter attack status (`0x710001af60` init, `0x710001f9c0` main; CONFIRMED):**
- Motion `special_lw_attack` / `special_air_lw_attack`. If the status was entered via `+0xe4f0` (not `+0xe4ec`) the animation is synced to frame `rebound_attack_start_frame` (4) at start.
- **Damage formula** (visible arithmetic): `d = stored_hit_damage * attack_mul`; `if d < attack_min then d = attack_min`; `max = attack_max_for_enemy` if a flag is set else `attack_max`; `if max < d then d = max` (both 30). The result is stored to a work float and `AttackModule::set_power` is applied to every active attack part each frame while a work float `<=` condition holds (`0x710001f9c0`). Net: **countered damage x1.5, clamped to 9..30**.
- **Distance-scaled lunge**: if the target object `is_active`, `dmin = rebound_distance_min*10 = 9`, `dmax = rebound_distance_max*10 = 43`, if `dmin < dmax`: `clamp(|target.pos_x - self.pos_x|, 9, 43)` -> `lerp(rebound_speed_mul_f_min 0.1, rebound_speed_mul_f_max 2.3, (clamped-9)/(43-9))` -> `sv_kinetic_energy::set_speed_mul` on the kinetic energy that carries the animation Trans movement. If flag `0xe630` is true the multiplier is `dmin / clip's total Trans z` (`MotionModule::trans_tra_end_frame`) instead (INFERRED meaning). The `rebound_speed_mul_b_*` pair (1.1 -> 0.1) is read for the other direction (`0x710001a370`-family; the visible lerp is the f pair).
- **Air**: when `0xe63c` (ACMD raises it at f7 of `game_speciallw`) is seen while in the air: `set_speed(-speed_x * lr, speed_y)` = (-0.45*lr, +1.1), then `mul_x_accel_mul(control_accel_x_mul 0.7)` and `mul_x_speed_max(control_max_speed_x_mul 0.7)`; kinetic energy switched to `+0x550` type. CONFIRMED structure; sign INFERRED from the visible `operator-`.
- **Direction/turning**: `special_lw_turn`/`special_air_lw_turn` motions (7-frame clips) are played by `0x7100019e80` (`se_trail_special_l01_counter01/02` sounds); the facing logic that decides when the turn clip is used is in the start/main callbacks (not fully traced: UNKNOWN).
- **Rebound** (`0x710001a370` init, `0x7100020620` main): motion `special_lw_rebound`/`special_air_lw_rebound` (clip intangible f1-30, QUAKE 0x1978 at f2); reads `rebound_height` 1.9 / `rebound_approach` 0.6 (init) and `rebound_speed_y` 0.02 / `rebound_speed_y_max` 0.3 (main); at motion end requests `+0xe4f0` (CONFIRMED, previous note). What enters rebound is UNKNOWN.
- **ACMD attack** (`game_speciallw`, clip `d03speciallw` `move: true`, xlu f1-12, cancel 32): f7 ids 0-3: 9.0%, angle 361, kbg 67, bkb 74, hitbox sizes 3.2 (ids 0-2 on bone `haver` at y 0/4.6/9.2) and size **9.0** (id 3, `top` (0,4.0,11.5)); `set_force_reaction` all four; flag `0xe63c` f7; id 3 re-asserted f10, f11; `clear_all` f12.

### 3.2 Current port

`trail_specials_geno.py:590-690` (states `LwStart`, `LwStartAir`, `LwAttack*`, optional `LwAttackBack*`): counter window `{"from": 9, "to": 26, ... "negate": true}` (flag on+1 .. off), intangible per the motion list, IASA at `cancel_frame`, ground start multiplies by `start_speed_x_mul_ground`, air by `start_speed_x_mul_air`/`start_speed_y_mul_air`+`add`; attack states: lock-on hook turns Sora to the nearest opponent; ground lunge = the clip's Trans z per frame; air `vy = speed_y (1.1)` at f0; counter damage `HIT_DAMAGE * 1.5` clamped 9..30 via `HBDMG` (:649-660); the backward variant (`counter_backward`, default ON) plays the reversed clip; the rebound states exist only with `--counter-rebound` (default OFF, "unreachable", :675-690); `phys air_nodrift`/`coll air`, `phys none`/`coll both`.

### 3.3 Divergences (down special)

| # | Real | Port | Impact | Fix |
|---|---|---|---|---|
| D1 | Lunge scaled 0.1x-2.3x by distance to the attacker (9-43 units) | Fixed clip travel | High (counter attacks hit near or far attackers with the same lunge; Ultimate home-in) | M; needs the lock-on target distance exposed to a script (a var like `LOCK_DIST`): possible new Geno capability |
| D2 | Counter hit pushes Sora (-0.45 lr, +1.1) at f7 in the air and re-enables air control x0.7 | `vy = 1.1` at f0 only, no x recoil, `air_nodrift` | Medium | S-M |
| D3 | Rebound state, reflector window: unreachable / unknown | Rebound states off by default | Medium (counter vs strong attacker/projectile) | L (trigger UNKNOWN) |
| D4 | Counters melee; `shield_*` params imply reflect x1.4 dmg / x1.8 speed (INFERRED) | Counter window turns any hit (incl. projectiles) into the attack state; no reflection | Medium for projectile matchups | M; reflected-projectile scaling is new engine capability |
| D5 | Hit 3 (size 9.0, the large front hitbox) dropped (four slots) | Ids 0-2 kept | Low-medium (counter attack reach) | S |
| D6 | Intangibility f7-9 start, f1-12 attack | Ported | None | n/a |
| D7 | Damage 1.5x, 9..30 | Ported | None (matches, CONFIRMED) | n/a |
| D8 | `hitstop_frame_direct/hitstop_frame` 6/4, `shake_*`, camera | Melee hitlag rules | Low | S |

---

## 4. Status-driven normals and mechanics

### 4.1 Jab chain and forward tilt (`common:status_Attack_Main`, `status_AttackS3_Main_param`)

Previous note's data stand (clips, ACMD flags f20/f22 and f16/f18, `fighter_param_table[76]`: `attack_combo_max` 3, `combo_attack_12_end` 38, `combo_attack_13_end` 36, `attack100_type` False, `attack_100_enable_cnt` 0). New from `common:0x7100079c70` (`status_Attack_Main_button`, button const `+0x268`):
- With `attack100_type == False` (Sora), the jab continues only if (CONFIRMED structure): `AttackModule::is_infliction_status(0x7f)` (the attack **connected**) AND work flag `+0x73c` AND `ControlModule::check_button_on` (the attack button is **held**, not necessarily newly pressed) AND `ComboModule::count < attack_combo_max` AND work flag `+0x720` (the ACMD flag raised at f20/f16) AND ground -> `change_status(+0x1c4)` (the Attack status again, ComboModule increments).
- Else (no hit): `is_enable_transition_term(+0x1bc)` AND `+0x73c` AND work int `+0x70c >= attack_100_enable_cnt` (0) AND ground -> the same status. The two ACMD flags (`+0x720` at f20 and `+0x72c` at f22) map to the hit and no-hit routes (INFERRED, order of the flags in each jab script).
- Correction to the earlier jab note: its "`ENABLE_COMBO`/`ENABLE_NO_HIT_COMBO`" guess is plausible, but the continuation requires the *hit* result for the first route and holds the button; the port inherits Melee's "A pressed during a window" jab.
- `status_AttackS3_Main_param` (`common:0x7100082d00`, Sora main `0x710001ca60` passes const `+0xe528`): follow-up when `ComboModule::count < s3_combo_max` (3) AND flag `+0x710` AND flag `+0x720` -> `attack_s3_mtrans_param` (the continuation handler, not traced). `+0x710` is read by the `game_attacks3` ACMD to choose the 7.2% or 5.2% branch; who sets it is UNKNOWN (not in `status_AttackS3Common`). End: `status_end_AttackS3` + `ComboModule::clear_setting` (`0x71000181f0`).

Port: Melee's native jab chain (A pressed in the jab window), Attack13 row populated (INSTALL `moveset_rows` 48), `S3Combo2/3` Geno states using a fresh A press (`trail_specials_geno.py:694-722`, `combo_chain_check(.., 29, 44)`/`(18, 40)`). The jab input windows (`co_attrs.jab_2/3_input_window`) are Melee's, not Ultimate's 38/36.
Divergence: **J1** jab 2 and 3 need a hit-confirm or the later no-hit flag and a held button in Ultimate; Melee's jab continues on a press, hit or whiff. Medium. Fix M (jab as a Geno state or `jab_*_input_window` override; hit-confirm needs `ATTACK_CONNECTED` var which exists). **J2** `+0x710` gating for the S3 follow-up not understood: the port gives stage 2 whenever the A-press check at f29-44 passes. Low-medium, UNKNOWN.

### 4.2 Aerial chains (nair and fair): Sora has custom statuses and the port drops stages 2 and 3

CONFIRMED (`0x7100007d50` main of +0xe4f4, `0x7100008400` main of +0xe4f8 [triples (7970,7d50,7ff0) and (8020,8400,86a0) in `0x7100005910`], `0x7100016120` landing, `0x71000144f0`, `0x7100013fe0`; `param_private`): Sora overrides the aerial statuses for **neutral and forward air**. Each main runs `common:status_AttackAir_Main_common`, and `0x71000141a0` (nair) / `0x7100013360` (fair) continue the chain when `ComboModule::count < attack_air_n_combo_max` (3) / `attack_air_f_combo_max` (3) and the work flags `+0xe53c` (combo input accepted) and `+0xe540` (the ACMD raises `0xe540` at f23 in `game_attackairn`, `0xe54c` at f16) are set: `0x7100013fe0` clears the attack and re-arms, `ComboModule::set`, and `0x71000144f0` selects the motion by the combo count: 1 -> `attack_air_n`, 2 -> `attack_air_n2`, 3 -> `attack_air_n3` (fair: `attack_air_f`/`f2`/`f3`). A work int `+0xe538` (written by Sora's JumpSquat main `0x710001b700` and by the Jump end `0x7100018500`; value hidden) must be `>= 2` for flag `+0xe53c` to be set at the start (`0x7100007d50`): **the chain is gated by a jump-state counter (INFERRED: full hop / double jump versus short hop)**.
- Chain data (ACMD, anim frames): nair1 `game_attackairn` clip `c05attackairn` hits f8-14 3.8% (angles shift 74..128, bkb 66..84 growing), flag 0xe54c f16, 0xe540 f23, cancel 42; nair2 `game_attackairn2` clip `c05attackairn2`, `FT_MOTION_RATE 0.8` f0-14, 3.5% f6-12, cancel 37; nair3 `game_attackairn3` clip `c05attackairn3` 6.8% angle 68 kbg 88 bkb 68 f9-14, cancel 42. Fair1 `game_attackairf` 4.8% f8-14, flags 0xe56c f14 / 0xe560 f21, cancel 42; **fair2 reuses clip `c05attackairn2`** (4.0% angles 48-92) and **fair3 reuses `c05attackairn3`** (6.8% angle 52 kbg 88 bkb 68).
- Parameters: `param_private.combo_attack_ari_n2_end` 42, `..._n3_end` 36, `..._f2_end` 42, `..._f3_end` 36; `attack_air_n/n2/f/f2_hit_speed_y` 1.0 (the hop on hit), `attack_air_hit_speed_x_mul` 0.35, `accel_x_mul` 0.75, `speed_max_x_mul` 0.65; per-stage landing: `landing_attack_air_frame_n/f/b/hi/lw` 9/12/11/10/28 (`fighter_param_table[76]`) and `param_private` 0x1B5041CFB5=10 (n2, by elimination), 0x1B2746FF23=11 (n3), 0x1B989845BD=13 (f2), 0x1BEF9F752B=14 (f3) with per-stage landing motions `landing_air_n/n2/n3/f/f2/f3` (`0x7100016120`).
- Port: the installed moveset has only `AttackAirN` (row 68), `AttackAirF` (69), `AttackAirB`, `AttackAirHi`, `AttackAirLw` (INSTALL `moveset_rows`). There are no Melee rows or Geno states for nair2/3 and fair2/3: `grep AttackAirN2` in `ports/ir/tools` finds nothing. The stage 2/3 scripts exist in the ACMD (`game_attackairn2/3/f2/f3`) and clips exist but are never installed.
- **A1 (very high)**: Sora's three-hit nair and fair strings (the character's bread-and-butter) are one hit in the port. Fix M-L: Geno states modelled on `S3Combo2/3` (they already have the machinery: `CHG` on fresh A at the flagged frames, `clip anim next`), plus per-stage landing lag. No new engine needed (aerial `geno.air` states exist). The `+0xe538` gate is UNKNOWN and needs a decision (see 5).
- **A2**: Sora's `AttackAirLw` (dair) vertical motion is dropped: ACMD `game_attackairlw` has `suspend_energy` f1, `SET_SPEED_EX(0, 1.2)` f2, `SET_SPEED_EX(0, -3.2)` f14, `resume_energy` f40 (conversion_losses). The port's dair has none of the rise-then-dive. Medium-high. Fix S-M: `PUTF V_VEL_Y` events in the dair row (gravity suspend needs a phys mode: possible new capability).

### 4.3 Air mobility, jump, movement attributes

- Ultimate Sora (`fighter_param_table[76]`, CONFIRMED): `jump_count_max` 2, `jump_y` 30, `jump_aerial_y` 40, `mini_jump_y` 17.2, `jump_squat_frame` 3, `jump_speed_x_max` 1.2, `air_accel_y` 0.064, `air_speed_y_stable` 1.44, `dive_speed_y` 2.304, `air_speed_x_stable` 0.96, `walk_speed_max` 0.82, `dash_speed` 1.78, `run_speed_max` 1.58, `weight` 85, `shield_radius` 11.6, `landing_frame` 3 (light 1, heavy 5), `landing_attack_air_frame_*` above, `special_s_brake` 0.2.
- `_build/tmp/ir/attr_calibration.json` holds a fitted Melee attribute set for `trail` (`port` block: gravity 0.07314, terminal 1.81512, fast fall 2.33142, walk max 0.78063, dash 1.3497, jump squat 3, landing lags N/F/B/Hi/Lw 18/24/22/20/56, weight 85). **Nothing consumes it**: no reference in `install_ultimate.py` or `build_melee_fighter.py` (grep), `INSTALL.json` has no attribute section, and the generated `geno.json` fighter object has no `attributes` key (keys: `attach name states specials subactions articles`). INFERRED consequence: the installed Sora keeps the cloned host's (Marth's) Melee attributes (walk/run/jump/fall/weight/landing lag/shield size/jab windows). Not verified in game.
- Sora overrides: JumpAerial main sets `MotionModule::set_trans_move_speed_no_scale(<bool>)` then `status_JumpAerial` (`0x710001b830`); JumpSquat main stores `+0xe538`; Walk and WalkBrake use `walk_*_item` motions when an item is held; AttackLw4 and the item-swing smash statuses have thin wrappers. The decompile gives no Sora-specific double-jump height beyond the table above.

**Divergences:** **M1 (high)** movement/landing/attributes are the host's (INFERRED); fix S-M (apply `attr_calibration.json` `port` through Geno `attributes`, which `geno.md` section 4 already supports); no new engine. **M2** the nair/fair `+0xe538` jump-state gate is not modelled (low until A1 is done).

### 4.4 Other non-special statuses of interest

`+0x4d4` AttackLw4 and `+0x138/+0x86c/+0x870` ItemSwingS4* are thin wrappers; `+0x39c` GenesisGet and `+0x280` Appeal custom entry only. No Sora-specific mechanic found in them (low-confidence: bodies not read beyond the first lines).

---

## 5. Divergence table across the kit (ranked by how noticeable a player finds it)

Rank / area / real vs port / size / new engine?

| # | Area | Divergence | Size | New Geno engine capability? |
|---|---|---|---|---|
| 1 | Magic casts | Ray-gun (`h12itemscope*`) clips on all six cast states instead of `d00specialn*` (N1) | M | No |
| 2 | Nair/Fair | Hits 2 and 3 of both aerial chains do not exist (A1) | M-L | No (clone of `S3Combo` pattern) |
| 3 | Movement | Host (Marth) Melee attributes: walk/run/jump/fall/landing lag (M1, INFERRED) | S-M | No (`attributes`) |
| 4 | Firaga | One fireball; no repeat loop, no `game_fly2` variant (N3) | M | No |
| 5 | Magic (air) | No air hop / start-kinetic damping (N2) | S-M | No |
| 6 | Up special | No cancel into Special S in f48-70 (U1) | M | Probably no |
| 7 | Counter | Lunge not scaled by distance (D1) | M | Likely yes (target distance var) |
| 8 | Thundaga | Cloud/bolt placement invented (N6) | L | Unknown |
| 9 | Blizzaga | Shard life 30 vs 13/15, no terrain despawn (N4); Firaga no terrain despawn (N7) | S | No |
| 10 | Counter | Air recoil (-0.45, 1.1 at f7) and control x0.7 missing (D2) | S-M | No |
| 11 | Counter | Rebound / reflect / projectile scaling absent (D3, D4) | L | Yes (reflect scaling) |
| 12 | Up special | 4-slot hitbox limit drops capsules and the finisher's tip (U2) | S-M | Possibly yes (slots) |
| 13 | Jab | Press-based Melee jab versus held-button + hit-confirm Ultimate (J1) | M | No |
| 14 | Dair | Rise-then-dive velocity events dropped (A2) | S-M | Maybe (gravity suspend) |
| 15 | Magic cycle | Advance at spawn, not at status end (N5) | M | Maybe (exit hook) |

## 6. What the conversion DROPPED (from `conversion_losses.json` 2560 rows, `INSTALL.json`, `staged-*/conversion_losses.json`)

All but 195 rows are the *approved* Melee-rule drops ("Ultimate-specific mechanic, Melee rules apply", `approved_by: coordinator per GD rule 2026-09-26`), so they are by design, not bugs, but they do change feel. Grouped and ranked by play/visual effect:

1. **Hitbox slot overflow (94 + 12 + 4 rows)**: `game_specialhi/airhi` ids 4-5 at every frame and 3 of 5 final hits (see U2); `game_speciallw` id 3 (size 9.0); `game_attacks4`, `game_attacklw4` (6 each), `game_attackhi3/lw3` (3), `game_attack12`, `game_attacks32/33` (2-3). High for the up special, medium elsewhere.
2. **Velocity/physics commands**: `SET_SPEED_EX`, `KineticModule::suspend_energy/resume_energy`, `KineticModule::change_kinetic` in `game_attackairlw` (dair rise/dive, A2), `game_specialairn1end`, `game_specialairn3` (change_kinetic 0x430): Medium-high.
3. **Work-flag commands that status code reads** (`on_flag/off_flag` of `0xe54c`, `0xe540`, `0xe56c`, `0xe560` (aerial combo flags), `0xe610/0xe600` (up special rise/cancel window), `0xe61c` (counter window, handled by the Geno `counter` window), `0xe63c` (counter air recoil trigger), `0x52e0` (Firaga repeat window), `0xf3e8/0xf3f0/0xf3fc/0xf400/0xf404` (magic): Medium-high, because they are the *inputs* of the status machine the port replaces.
4. **Animation rows played as fallback or stand-ins**: 12 host rows with no matching Ultimate clip are replaced by `a00wait1` (`DownSpotU`, `FuraSleepEnd/Loop/Start`, `ItemBlind`, `ItemParasolFall/Open`, `ItemScrewAir/Damage`, `SpecialAirNLoop`, `SpecialAirS4S`, `SpecialNLoop`); plus the six magic rows 149-155 using `h12itemscope*` (this audit). High for the magic rows, low for the rest.
5. **Model visibility / texture animation**: 25 `modelvis_dropped`, 65 `texanim_dropped` (eye/mouth/face pattern swaps `trail_Blink*`, `trail_Mouth_*`, `trail_Eye*`, `trail_Hot`, sword `trail_sword` show/hide); 49 "visibility state after Goto" and 26 host-ModelVis-script approximations (rows 29444 etc.): Medium visual (faces do not animate; keyblade show/hide approximate).
6. **Effects/hit properties**: `ATTACK` arguments `setoff_kind`, `lr_check`, `hitbits`, `collision_part`, `sound_level/attr`, `region`, `hitlag`, `sdi`, `set_weight`, `direct` (hundreds; Melee rules), `ATK_SET_SHIELD_SETOFF_MUL2` (58), `set_no_finish_camera` (72), `set_no_damage_fly_smoke_all` (16): Low-medium for feel (hitlag 0.3 on the up special's multihits: Melee uses default hitlag, so the sweep sticks and lets more of it connect differently), low otherwise. 3 rows: effect `collision_attr_magic` approximated in Melee.
7. **Rounding**: article damage rounds to integers (Firaga 5.6/5.2/4.8 -> 6/5/5, Blizzaga shard 2.4 -> 2, last shard 3.6 -> 4, thunder 5.2 -> 5, blizzaga body 1.8 -> ?, throw damage 3 rows): Low.
8. **Pending engine features**: `GrabModule::set_rebound` (4 rows), `FT_CATCH_STOP`, `ATTACK_ABS`/`ATK_HIT_ABS` (the throw-hit absorb), `FighterCutInManager::set_throw_finish_zoom_rate`, `AttackModule::set_attack_height_all`: Low-medium (grab/throw feel).
9. **Host physics drives the root on 13 rows** ("animation root travel"): the clip's Trans travel is stripped on those rows (`root_travel_stripped` list in `INSTALL.json`, e.g. `a01walkfast` z 35.8, `a02run` 59.1), replaced by Melee physics: movement distances of walk/run/dash come from Melee attributes (see 4.3): Medium.
10. **Host bone dynamics** (3 dropped), `unmatched ... replaced by a#wait#`.

## 7. UNKNOWN (outside the NRO or beyond my traces), stated plainly

1. **Cycle order and exact change_magic semantics**: `FighterSpecializer_Trail::change_magic` is imported from the main executable; the order Firaga -> Blizzaga -> Thundaga is not in our data (only call sites). Also unknown: how the Special-N press chooses N1START/N2/N3 (the Special N status is not overridden in this NRO; the selection occurs elsewhere).
2. **Weapon-agent behaviour**: the cloud (`trail_cloud`) status and its placement of the three clouds and bolts, the ice shard's initial angle/offset use of `+0xf3f4`, shard-versus-shard behaviour, freeze rules, and `game_fly` vs `game_fly2` selection. Only `trail_fire` (`0x7100031cf0`, `0x7100032670`), the ice shard main (`0x71000357b0`), and parts of `trail_thunder` (`0x71000376a0`, `0x7100036f60`, `0x71000383a0`, `0x7100039310`) were read.
3. **Counter trigger and rebound**: what raises flags `0xe628/0xe630`, which hit event enters `+0xe4ec`/`+0xe4f0`, whether and how projectiles are reflected, rebound entry and exit conditions: the producer is in `ReflectorModule`/`ShieldModule`/main-exe code.
4. **Up special**: what raises `0xe60c`; which `cliff_hang_data` index `+0xe5fc` selects; the exact guard of the 0xe600-window transition term into Special S; `KineticUtility::get_jump_speed_y` (main exe) numerical definition; the camera/effect event `0x2127e37c07`.
5. **Jab/ftilt**: who sets work flag `+0x710` and `+0x73c`; the continuation handler `attack_s3_mtrans_param` (read only by name); the exact frame of the combo-input comparison; the `+0xe538` jump counter gate of the aerial chains.
6. **Common functions**: the exact formulas of `sub_set_special_start_common_kinetic_setting` (the param names are confirmed; the stack-push loss hides how each is applied).
7. **Parameters outside `vl.prc`**: Sora-specific `common.prc` entries other than the ones read (`special_stick_x/y` read: 0.6/0.5).
8. **Anything that needs a running game**: all timing statements are static (game-frame conversion of anim frames through the ACMD `FT_MOTION_RATE` segments); nothing was observed on screen.

## 8. Reference: where the evidence lives

- Param decode: `_build/tmp/sonic-steering-vl.xml` (`param_special_n` line 387, `param_fire` 541, `param_ice` 559, `param_thunder` 581, `param_special_hi` 865, `param_special_lw` 963, `param_private` 368); `_build/tmp/trail-jab-fighter-param.xml` index 76; `_build/tmp/trail-fidelity/common-prc.xml` (`special_stick_x` 195, `special_stick_y` 196).
- ACMD: `_build/tmp/codex-nodrop-run/trail.acmd.json` rows named in the text (`python _build/tmp/trail-fidelity/show.py trail <script>` prints one).
- Decompiles: `_build/tmp/trail-fidelity/ann/<addr>.c` (annotated trail), `.../ann-common/<addr>.c` (named common functions); status registration maps by function: 7100005910 (+0xe4f4..0xe50c), 7100004260 (the Sora overrides).
- Port: `ports/ir/tools/trail_magic_geno.py`, `trail_specials_geno.py`, `acmd_to_ftcmd.py`; generated `_build/audit-20261003/sora-regen/{staged-magic,staged-specials,staged-install}/geno.json`, `staged-install/INSTALL.json` (`conversion`, `animations`, `moveset_rows`), `staged-install/conversion_losses.json`.
- Engine semantics: `melee/docs/geno.md` (sections 4 `attributes`, 19.4 counter windows, `HBDMG` 0x3A).
