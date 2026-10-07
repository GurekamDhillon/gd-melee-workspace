# Script command reference (generated)

Regenerate: `python -m tools.geno.schema`.
Source: melee/src/melee/ft/ftaction.c; melee/pc/geno/geno_game.c and geno_game_v2.inc; melee/pc/platform/gw_script.c.

## Vanilla commands

Fields are encoded integers. Word 0 excludes the opcode's high six bits.

| Opcode | Name | Total words | Named fields (bit width; signed if marked) |
|---|---|---|---|
| 0 | end | 1 | `w0.value` (26) |
| 1 | wait | 1 | `w0.value` (26) |
| 2 | wait_until | 1 | `w0.value` (26) |
| 3 | loop | 1 | `w0.value` (26) |
| 4 | loop_end | 1 | positional/raw form |
| 5 | call | 2 | positional/raw form |
| 6 | return | 1 | positional/raw form |
| 7 | goto | 2 | positional/raw form |
| 8 | wait_anim | 1 | positional/raw form |
| 9 | bg_flash | 1 | `w0.param_1` (8), `w0.param_2` (18) |
| 10 | gfx | 5 | `w0.boneId` (8), `w0.useCommonBoneIDs` (1), `w0.destroyOnStateChange` (1), `w0.useUnkBone` (1), `w0.unk1` (15), `w1.gfxID` (16), `w1.unkFloat` (16), `w2.offsetZ` (16 signed), `w2.offsetY` (16 signed), `w3.offsetX` (16 signed), `w3.rangeZ` (16), `w4.rangeY` (16), `w4.rangeX` (16) |
| 11 | hitbox | 5 | `w0.id` (3), `w0.hit_group` (3), `w0.only_hit_grabbed` (1), `w0.bone` (8), `w0.use_common_bone_ids` (1), `w0.damage` (10), `w1.size` (16), `w1.z_offset` (16 signed), `w2.y_offset` (16 signed), `w2.x_offset` (16 signed), `w3.angle` (9), `w3.knockback_growth` (9), `w3.weight_set_knockback` (9), `w3.item_hit_interaction` (1), `w3.ignore_thrown_fighters` (1), `w3.ignore_fighter_scale` (1), `w3.clank` (1), `w3.rebound` (1), `w4.base_knockback` (9), `w4.element` (5), `w4.shield_damage` (8 signed), `w4.hit_sfx_severity` (3), `w4.hit_sfx_kind` (5), `w4.hit_grounded` (1), `w4.hit_aerial` (1) |
| 12 | hitbox_damage | 1 | `w0.idx` (3), `w0.value` (23) |
| 13 | hitbox_size | 1 | `w0.idx` (3), `w0.value` (23) |
| 14 | hitbox_flags | 1 | `w0.idx` (24), `w0.type` (1), `w0.value` (1) |
| 15 | hitbox_remove | 1 | `w0.hit_idx` (26) |
| 16 | hitboxes_clear | 1 | positional/raw form |
| 17 | sfx | 3 | `w0.behavior` (8), `w0.unknown` (18), `w1.sfx_id` (32), `w2.padding` (16), `w2.volume` (8), `w2.panning` (8) |
| 18 | smash_sfx | 1 | positional/raw form |
| 19 | cmd_var | 1 | `w0.idx` (2), `w0.value` (24) |
| 20 | throw_flag | 1 | `w0.hit_idx` (26) |
| 21 | throw_flag_b1 | 1 | positional/raw form |
| 22 | throw_flag_b2 | 1 | positional/raw form |
| 23 | iasa | 1 | positional/raw form |
| 24 | throw_flag_b0 | 1 | positional/raw form |
| 25 | air_state | 1 | `w0.state` (26) |
| 26 | body_state | 1 | `w0.state` (26) |
| 27 | hurtboxes_state | 1 | `w0.state` (26) |
| 28 | hurtbox_state | 1 | `w0.bone_idx` (8), `w0.state` (18) |
| 29 | jab_combo | 1 | `w0.disabled` (26) |
| 30 | jab_rapid | 1 | `w0.state` (26) |
| 31 | model_state | 1 | `w0.idx` (7 signed), `w0.value` (19 signed) |
| 32 | models_revert | 1 | positional/raw form |
| 33 | models_remove | 1 | positional/raw form |
| 34 | throw | 3 | `w0.idx` (3), `w0.damage` (23), `w1.unk0` (9), `w1.hit_x24` (9), `w1.hit_x28` (9), `w2.hit_x2C` (9), `w2.element` (4), `w2.sfx_severity` (3), `w2.sfx_kind` (4) |
| 35 | item_visibility | 1 | `w0.value` (26) |
| 36 | article_visibility | 1 | `w0.value` (26) |
| 37 | visibility | 1 | `w0.value` (26) |
| 38 | random_sfx | 7 | `w0.volume` (8), `w0.panning` (8), `w0.behavior` (4), `w0.random_range` (6), `w1.sfx_id` (32) |
| 39 | pitch_sfx | 4 | `w0.sfx_base` (10), `w0.x2_b0_7` (8), `w0.pitch_select` (8), `w1.sfx_id` (32), `w2.x0_b0_15` (16), `w2.x2_b0_15` (16), `w3.x0_b0_15` (16), `w3.x2_b0_7` (8), `w3.x3_b0_7` (8) |
| 40 | tex_anim | 1 | `w0.b` (1), `w0.idx` (7 signed), `w0.idx2` (7 signed), `w0.frame` (11 signed) |
| 41 | part_anim | 1 | `w0.unk1` (7 signed), `w0.unk2` (7 signed), `w0.unk3` (12) |
| 42 | parasol | 1 | `w0.unk1` (13), `w0.unk2` (13) |
| 43 | rumble | 1 | `w0.unk1` (1), `w0.unk2` (12), `w0.unk3` (13) |
| 44 | rumble_stop | 1 | `w0.unk1` (26) |
| 45 | color_anim | 1 | `w0.unk1` (2), `w0.unk2` (10), `w0.unk3` (14) |
| 46 | color_overlay | 1 | `w0.unk1` (8), `w0.unk2` (18) |
| 47 | color_overlay_off | 1 | `w0.unk1` (8) |
| 48 | flag_221E | 1 | `w0.unk1` (26) |
| 49 | sword_trail | 1 | `w0.unk3` (1 signed), `w0.unk4` (25 signed) |
| 50 | anim_part | 1 | `w0.unk1` (26 signed) |
| 51 | self_damage | 1 | `w0.damage_amount` (26 signed) |
| 52 | continuation | 1 | `w0.unk1` (26) |
| 53 | flag_2225 | 1 | `w0.unk1` (26) |
| 54 | footstep_fx | 3 | `w0.boneId` (8), `w0.use_alt_bone` (1), `w0.x1_b7` (1), `w0.x2_b0_7` (8), `w0.x3_b0_7` (8), `w1.sfx_id` (32), `w2.padding` (16), `w2.volume` (8), `w2.panning` (8) |
| 55 | landing_fx | 3 | `w0.x0_b6_7` (2), `w0.x1_b0_7` (8), `w0.x2_b0_7` (8), `w0.x3_b0_7` (8), `w1.sfx_id` (32), `w2.padding` (16), `w2.volume` (8), `w2.panning` (8) |
| 56 | smash_charge | 2 | `w0.charge_frames` (10), `w0.charge_rate` (16), `w1.color_anim` (8), `w1.x1_b0_23` (24) |
| 57 | unk_57 | 1 | `w0.unk1` (1), `w0.unk2` (8) |
| 58 | wind | 4 | `w0.x0_b6_17` (18), `w0.bone` (8), `w1.timer` (16 signed), `w1.x` (16 signed), `w2.y` (16 signed), `w2.mag` (16 signed), `w3.angle` (16 signed), `w3.decay` (16 signed) |

## Geno escape subcommands

| Name | Id |
|---|---|
| NOP | 0 |
| SET | 1 |
| ADD | 2 |
| SUB | 3 |
| MUL | 4 |
| SETBIT | 5 |
| CLRBIT | 6 |
| DIV | 7 |
| GET | 8 |
| PUT | 9 |
| RAND | 10 |
| IF | 16 |
| SKIP | 17 |
| IFV | 18 |
| ORIG | 19 |
| CALL | 32 |
| CHG | 48 |
| CHGAND | 49 |
| CHGCLR | 50 |
| REHIT | 56 |
| HBDMG | 58 |
| LINK | 57 |
| HBSTUN | 59 |
| HBFLAGS | 60 |

## Engine values

| Name | Id |
|---|---|
| AIR | 0 |
| FACING | 1 |
| VEL_X | 2 |
| VEL_Y | 3 |
| GROUND_VEL | 4 |
| FWD_VEL | 5 |
| KB_VEL_X | 6 |
| KB_VEL_Y | 7 |
| STICK_X | 8 |
| STICK_Y | 9 |
| STICK_FWD | 10 |
| CSTICK_X | 11 |
| CSTICK_Y | 12 |
| ANIM_FRAME | 13 |
| ACTION_FRAME | 14 |
| MOTION | 15 |
| PERCENT | 16 |
| JUMPS_USED | 17 |
| JUMPS_MAX | 18 |
| BUTTONS_HELD | 19 |
| BUTTONS_PRESSED | 20 |
| POS_X | 21 |
| POS_Y | 22 |
| CMD_VAR0 | 23 |
| CMD_VAR3 | 26 |
| ANIM_RATE | 27 |
| FAST_FALL | 28 |
| TRIGGER | 29 |
| GENO_STATE | 30 |
| MOVE_F0 | 32 |
| MOVE_F7 | 39 |
| MOVE_I0 | 40 |
| MOVE_I7 | 47 |
| LEDGE | 48 |
| HIDDEN | 49 |
| TRANSN_FWD | 50 |
| TRANSN_UP | 51 |
| MOTION_GRAVITY | 52 |
| HIT_DAMAGE | 53 |
| HIT_PORT | 54 |
| HIT_COUNTER | 55 |
| HIT_COUNT | 56 |
| ARTICLES | 57 |
| ATTACK_CONNECTED | 59 |
| ATTACK_CONNECTED_PREV | 60 |
| STICK_LEN | 61 |
| FALL_LIMIT | 62 |
| SPECIAL_F | 4096 |
| SPECIAL_I | 8192 |
| MOVE_F1 | 33 |
| MOVE_F2 | 34 |
| MOVE_F3 | 35 |
| MOVE_F4 | 36 |
| MOVE_F5 | 37 |
| MOVE_F6 | 38 |
| MOVE_I1 | 41 |
| MOVE_I2 | 42 |
| MOVE_I3 | 43 |
| MOVE_I4 | 44 |
| MOVE_I5 | 45 |
| MOVE_I6 | 46 |
| CMD_VAR1 | 24 |
| CMD_VAR2 | 25 |

## Change-action conditions

| Name | Id |
|---|---|
| ALWAYS | 0 |
| ANIM_END | 1 |
| GROUND | 2 |
| AIR | 3 |
| PRESSED | 4 |
| HELD | 5 |
| BIT | 6 |
| VAR | 7 |
| FRAME | 8 |
| VALUE | 9 |

## Comparisons

| Name | Id |
|---|---|
| EQ | 0 |
| NE | 1 |
| LT | 2 |
| LE | 3 |
| GT | 4 |
| GE | 5 |
| BIT | 6 |
| NOBIT | 7 |

## Hooks

| Name | Id |
|---|---|
| geno.log | 1 |
| geno.jumps.refill | 2 |
| geno.jumps.to_var | 3 |
| geno.count_frames | 4 |
| geno.article.spawn | 5 |
| geno.lockon | 6 |
| geno.aim_stick | 7 |
| geno.dash.search | 8 |
| geno.dash.aim | 9 |
| geno.brake | 10 |

## Writable values

`AIR`, `ANIM_RATE`, `ATTACK_CONNECTED`, `CMD_VAR0`, `CMD_VAR1`, `CMD_VAR2`, `CMD_VAR3`, `FACING`, `FALL_LIMIT`, `FWD_VEL`, `GROUND_VEL`, `HIDDEN`, `JUMPS_USED`, `LEDGE`, `MOTION_GRAVITY`, `MOVE_F0`, `MOVE_F1`, `MOVE_F2`, `MOVE_F3`, `MOVE_F4`, `MOVE_F5`, `MOVE_F6`, `MOVE_F7`, `MOVE_I0`, `MOVE_I1`, `MOVE_I2`, `MOVE_I3`, `MOVE_I4`, `MOVE_I5`, `MOVE_I6`, `MOVE_I7`, `VEL_X`, `VEL_Y`

## Integer engine values

`ACTION_FRAME`, `AIR`, `ARTICLES`, `ATTACK_CONNECTED`, `ATTACK_CONNECTED_PREV`, `BUTTONS_HELD`, `BUTTONS_PRESSED`, `CMD_VAR0`, `CMD_VAR1`, `CMD_VAR2`, `CMD_VAR3`, `FAST_FALL`, `GENO_STATE`, `HIDDEN`, `HIT_COUNT`, `HIT_COUNTER`, `HIT_PORT`, `JUMPS_MAX`, `JUMPS_USED`, `LEDGE`, `MOTION`, `MOVE_I0`, `MOVE_I1`, `MOVE_I2`, `MOVE_I3`, `MOVE_I4`, `MOVE_I5`, `MOVE_I6`, `MOVE_I7`

SPECIAL_I:index is integer and SPECIAL_F:index is floating point. Both are read-only.

## GENO_BTN_

| Name | Bits |
|---|---|
| ATTACK | 0x1 |
| SPECIAL | 0x2 |
| JUMP | 0x4 |
| SHIELD | 0x8 |
| GRAB | 0x10 |
| TAUNT | 0x20 |

## GENO_HBF_

| Name | Bits |
|---|---|
| NO_HITLAG | 0x1 |
| FLINCHLESS | 0x2 |
| ZERO_DAMAGE | 0x4 |
| FORCE_REACTION | 0x8 |

## GENO_LINK_

| Name | Bits |
|---|---|
| OFF | 0x0 |
| DIRECTION | 0x1 |
| SPEED | 0x2 |

## Callback names by slot

- anim: `like`, `next`, `loop`, `lua`, `hold`, `glide.start`, `glide`, `tornado`, `drill`, `drill.end`, `glide.after`, `cape`
- iasa: `like`, `interrupt`, `none`, `glide`
- phys: `like`, `cape`, `none`, `air`, `air_nodrift`, `air_drift`, `brake`, `ground`, `auto`, `anim_motion`, `glide.start`, `glide`, `glide.attack`, `glide.end`, `tornado`, `drill`, `drill.end`, `drill.start`
- coll: `like`, `cape`, `cape.after`, `none`, `air`, `air_noledge`, `ground`, `ground_stop`, `both`, `anim_motion`, `glide`, `drill`, `drill.start`
