# Sonic Blade steering in Ultimate (`trail`)

Research dated 2026-09-26. Primary sources are the extracted `fighter/trail/param/vl.prc`, decoded with `experiment/tooling/ultimate/apps/ParamXML/ParamXML-win-x64/ParamXML.exe` and `experiment/tooling/ultimate/references/ParamLabels.csv`; `experiment/tooling/ultimate/workspace/extracted/prebuilt/nro/release/lua2cpp_trail.nro` in the read-only Ghidra project `${GW_GHIDRA_PROJECTS}/sora.gpr`; and the ACMD dump `${GW_GHIDRA_PROJECTS}/sora_acmd/`. The temporary ParamXML output is `_build/tmp/sonic-steering-vl.xml`; the temporary Ghidra decompilation is `_build/tmp/sonic-steering-scan.c`. Addresses below are Ghidra virtual addresses in this NRO. **Confirmed from game data** means a value or operation appears in those files; **inferred** means its gameplay interpretation needs another control-flow pass. No gameplay measurement was made.

## Steering rules and limits

| Question | Finding | Source and confidence |
|---|---|---|
| When the stick is read | Status code reads both `ControlModule::get_stick_x` and `get_stick_y` in functions `0x7100018d80`, `0x7100027700`, and `0x710002bd30`. The latter is reached in the dash motion-end path before selecting another status. A new sample can therefore affect a follow-up dash. The exact game frame on which the attack heading is committed, and whether a held stick continuously changes velocity during an active dash, remain **undetermined**. The parameter file has `search_frame=9`, `attack_turn_frame=4`, `right_frame=4`, and `cursor_lock_frame=7`, but a parameter name alone does not assign a stick-read frame. | NRO `0x7100018d80` (decomp lines 167-190), `0x7100027700` (507-531), `0x710002bd30` (1683-1705); `vl.prc` decoded XML lines 651, 659-660, 683. Stick calls and values **confirmed**; timing interpretation **inferred/unknown**. |
| Stick conversion | At `0x7100027700`, the code forms `(stickX, stickY)`, compares its vector length with `search_stick=0.25`, and obtains an angle with `atan(stickY, stickX)` followed by radians-to-degrees conversion. A below-threshold path uses a saved angle. This is a polar stick direction, **not a linear function of Y alone**. This function also moves/rotates an effect, so using this result as the actual dash heading is **inferred**, while the vector threshold and angle calculation are **confirmed**. | NRO `0x7100027700` (decomp lines 507-603, 616-710); `vl.prc` lines 652-653. |
| Angle limits | `attack_up_angle_min=40 deg`, `attack_up_angle_max=140 deg`, `attack_down_angle_min=220 deg`, and `attack_down_angle_max=320 deg` are game data. In dash initialization, the **40 deg-140 deg test** gates the upward speed multiplier; this does **not** establish that the stick angle is clamped to 40 deg or 140 deg. No verified maximum stick-up/down angle or turn-rate limit can be given from this pass. | `vl.prc` lines 677-685; NRO `0x7100028750` (decomp lines 1354-1426). Values and upward-range test **confirmed**; any claim that they are steering clamps **unsupported**. |
| Aim across dashes; left/right | The dash initialization at `0x7100028750` gets either a target position or a stored angle, constructs a 2D heading, and calls `PostureModule::set_lr`/`update_rot_y_lr` when the selected horizontal sign differs from facing. The motion-end handler reads a fresh stick vector before a follow-up status. This supports **re-aiming each dash** and **reversing facing when the chosen aim points behind Sora**; the exact status transition and neutral-stick fallback need further tracing. | NRO `0x7100028750` (decomp lines 934-993, 1290-1455), `0x710002bd30` (1665-1760). Operations **confirmed**; gameplay summary **inferred**. |
| Dash velocity | `attack_speed_x=3.2` is the base scalar. The status helper at `0x710002b2d0` applies the unlabeled `0x15530D2D10=0.92` and `0x17DD304B6F=0.98` as repeated multipliers from internal counters, and `0x1A41A10288=1.15` when a flag is set. Dash initialization converts the selected angle with cosine/sine, scales both components by the result, and sets kinetic speed; it zeros brake/acceleration for that energy. If the heading is within 40 deg-140 deg, it multiplies the scalar by `attack_up_speed_mul=0.85` (base 3.2 becomes 2.72 before other multipliers). This is a directed velocity set at dash initialization, not evidence of continuous in-dash turning. | `vl.prc` lines 647, 661-663, 677-679; NRO `0x710002b2d0` (decomp lines 4191-4321), `0x7100028750` (1354-1493). Arithmetic **confirmed**; meanings of the unlabeled flags/counters **unknown**. |
| Ground/air and collisions | Startup parameters distinguish ground and air braking/control, while both startup horizontal speed multipliers are 0.5; there is one `attack_speed_x` scalar in `param_special_s[0]`. The active dash ACMD calls `KineticModule::add_speed(-1, 0, 0)` at frame 11 of dash 1, and `add_speed(-0.5, 0, 0)` at frame 11 of dashes 2 and 3, for both ground and air scripts. The dash status code changes kinetic/situation, enables pass-through checking, and examines ground touch flags, touch normals, and velocity. The exact landing and wall response is **not yet resolved** from these calls; a wall-stop or bounce rule should not be invented. | `vl.prc` lines 635-648; NRO `0x7100028750` (decomp lines 887-926, 1458-1493), `0x710002bd30` (1775-1889); ACMD `game_specials1/2/3` and `game_specialairs1/2/3`, `${GW_GHIDRA_PROJECTS}/sora_acmd/game/0x5b268858f__0xe0586388b.c`, `...__0xe9c8f6931.c`, `...__0xeeb8859a7.c` and their air equivalents. Values/calls **confirmed**; collision outcome **unknown**. |

The ACMD scripts contain hitboxes, a 50-unit `SEARCH` sphere (`game_specialssearch` at `0x71000e0310`, air variant at `0x71000e05e0`), and the frame-11 speed changes. They do **not** contain the stick-to-velocity calculation. The NRO does contain status logic: its status agent factory is `lua2cpp::create_agent_fighter_status_script_trail` at `0x7100000480`, whose fighter branch installs the status vtable at `0x71005db0a0`; the status setup is reached through vtable method `0x7100004260`. The directly relevant functions identified here are `0x7100018d80`, `0x7100027700`, `0x7100028750`, `0x710002b2d0`, and `0x710002bd30`. `FighterSpecializer_Trail::get_special_s_target_pos` and `set_turn_special_s` are **external imports** at `0x71004af9b0` and `0x71004af9f0`; their implementations are not in this NRO. Sources: NRO status factory decomp `_build/tmp/sonic-steering-status-factory.c`, vtable/reference dump `_build/tmp/sonic-steering-refs.txt`, status decomp `_build/tmp/sonic-steering-scan.c`, and `${GW_GHIDRA_PROJECTS}/sora_acmd/index.tsv` lines 161-169.

## Parameters

All rows below are `param_special_s` **struct index 0** in `fighter/trail/param/vl.prc` (decoded XML lines 633-689). The label hashes come from `references/ParamLabels.csv`. Raw hashes have no label there; they are retained as hashes. This is the complete struct so the unlabeled factors and collision/end parameters are available to the implementer without treating their guessed purpose as fact. Values and hashes are **confirmed from game data**; the names are community hash labels, not a proof of runtime use.

| Name or raw hash | Hash | Value |
|---|---|---:|
| `start_speed_x_mul_ground` | `0x18820c6279` | 0.5 |
| `start_brake_x_ground` | `0x14c6661aec` | 0.1 |
| `start_speed_x_mul_air` | `0x15be2ab29a` | 0.5 |
| `start_brake_x_air` | `0x1130d6fe7d` | 0.01 |
| `start_control_accel_x_mul_air` | `0x1ddb814820` | 0.5 |
| `start_control_max_speed_x_mul_air` | `0x216611cef6` | 0.5 |
| `start_stop_y_frame_air` | `0x1608994192` | 0 |
| `start_accel_y_mul_air` | `0x154540af28` | 1 |
| `start_max_speed_y_mul_air` | `0x1900b3b5b6` | 1 |
| `start_speed_y_air` | `0x11882a5471` | 0 |
| `start_speed_y_mul_air` | `0x15a951a6d9` | 0.1 |
| `start_speed_y_add_air` | `0x15960b5652` | 0 |
| `attack_speed_x` | `0x0ec379508b` | 3.2 |
| `attack_frame` | `0x0c6bb4b9c9` | 12 |
| `attack_hit_ground_angle` | `0x1735e7956a` | 65 |
| `attack_hit_down_angle` | `0x15db4a5e9f` | 55 |
| `search_frame` | `0x0c81cdff24` | 9 |
| `search_stick` | `0x0c7b8ee93b` | 0.25 |
| `search_angle` | `0x0c34b486e0` | 0 |
| `search_cursor_offset_y` | `0x16ee6fe522` | 8 |
| `search_cursor_dist` | `0x12145d2880` | 12 |
| `search_inherit_speed` | `0x14c6deb55d` | 2 |
| `search_brake_x` | `0x0e2fea5e43` | 0.24 |
| `search_brake_air` | `0x100f9d0521` | 0.34 |
| `attack_turn_frame` | `0x1154de6755` | 4 |
| `right_frame` | `0x0b4d12a7cd` | 4 |
| `0x1A41A10288` | `0x1A41A10288` | 1.15 |
| `0x15530D2D10` | `0x15530D2D10` | 0.92 |
| `0x17DD304B6F` | `0x17DD304B6F` | 0.98 |
| `0x1719BF7EB5` | `0x1719BF7EB5` | 10 |
| `attack_num` | `0x0aa5d51ffa` | 3 |
| `end_brake_x` | `0x0b37f4e030` | 0.12 |
| `end_speed_y` | `0x0bd80f5d13` | 1.5 |
| `end_brake_x_air` | `0x0f60af08b6` | 0.35 |
| `end_speed_x_mul_air` | `0x133bb947b4` | 0.5 |
| `end_accel_y` | `0x0b2c5f04d9` | 0.08 |
| `attack_landing_frame` | `0x1417ed5a1b` | 20 |
| `0x1CB542ADC0` | `0x1CB542ADC0` | 20 |
| `end_frame_1` | `0x0be9d062cb` | 35 |
| `end_frame_2` | `0x0b70d93371` | 40 |
| `end_frame_3` | `0x0b07de03e7` | 45 |
| `0x1B949B05BC` | `0x1B949B05BC` | 35 |
| `attack_up_angle_min` | `0x13b363dc08` | 40 |
| `attack_up_angle_max` | `0x138f6ee351` | 140 |
| `attack_up_speed_mul` | `0x13ddedc0c6` | 0.85 |
| `attack_check_down_y` | `0x130dd4d94a` | 15 |
| `attack_check_dead_range_x` | `0x190b863464` | 5 |
| `attack_dead_speed_mul` | `0x15ec0d15a1` | 1 |
| `cursor_lock_frame` | `0x116f193347` | 7 |
| `attack_down_angle_min` | `0x15b9567fd1` | 220 |
| `attack_down_angle_max` | `0x15855b4088` | 320 |
| `0x0DEB5675E2` | `0x0DEB5675E2` | 20 |
| `end_landing_fall_special_frame` | `0x1e514eeee4` | 20 |
| `cursor_offset_y` | `0x0f35d3204c` | 17 |

The adjacent `turn_param_special_s` list (`0x144d3405f9`, XML lines 859-864) is `[315, 270, 225, 180]`. Its use in steering was **not established**. The other three `param_special_s` struct entries are zero-filled and were not treated as alternate settings for the active move.

## Current port and unresolved work

`ports/ir/tools/trail_specials_geno.py` lines 56-59 defines an **inferred** 50-unit lock range, 40 deg lock clamp, 25 deg stick angle, and 8-frame hover. Lines 246-306 call lock-on at `search_frame` during startup and `attack_turn_frame` during the hover, then set velocity from the stored aim vector using `attack_speed_x` and apply `attack_up_speed_mul` for upward motion. The 25 deg stick angle is not supported by the game parameter data or the status code inspected here. Its 40 deg clamp must not be equated with the game's `attack_up_angle_min=40 deg`: the latter was observed as an upward-speed range test. The port's dash states otherwise fix the aim for each dash and use its own Geno physics.

Still unknown: the exact input-sampling frame relative to each animation, whether any active-dash callback continuously updates the angle, the full neutral-stick reuse rule, the role of the unlabeled speed factors and angle/collision parameters, and the exact landing/wall transition. The unresolved pieces require a targeted control-flow pass of the status handlers and the external `FighterSpecializer_Trail` implementation in the game's main module. The ACMD dump cannot answer them because it only registers animation commands. No angle clamp, turn-rate, collision bounce, or wall-stop number should be copied from the port's inferred constants as an Ultimate fact.

### For the implementer

Provide the Melee-side state with the current analog `(stickX, stickY)` and its magnitude at the chosen sampling frame, a saved heading for neutral-stick fallback, an optional lock-on target position, facing, dash index and relevant hit/target flags, ground/air and wall/ground contact normal, and a way to set **one directed 2D velocity** `(speed*cos(angle), speed*sin(angle))` when a dash starts. The game-derived baseline is `speed=3.2`, the confirmed upward-heading multiplier is `0.85` for 40 deg-140 deg, and the ACMD frame-11 `add_speed` X inputs are `-1`/`-0.5`; other factors and the exact sample frame need the additional status trace before claiming parity.
