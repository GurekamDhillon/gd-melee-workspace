# Geno key reference (generated; do not edit)

Regenerate with `python -m tools.geno.schema`.
Use the adjacent minimal geno.json/mod.json pair as a starting point. Engine source wins.

Every nested key is listed below. Defaults describe absence; inherited data needs your disc.

| Key | Type / meaning | Engine default | Limits / reference |
|---|---|---|---|
| geno | integer: Format version | 8 | minimum=1; maximum=8; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters | array: Ordered entries | absent | maxItems=65535; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].attach | string: Vanilla name/alias or existing fighter .dat file |  | maxLength=31; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].define | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].define.key | string: See choice encodings | absent | pattern=^[a-z0-9][a-z0-9_.-]{0,38}$; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].define.name | string: See choice encodings | absent | maxLength=47; pattern=^[ -~]+$; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].define.base | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].define.common | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].define.resources | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].common_states | array: Ordered entries | absent | maxItems=64; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].common_states[].motion | integer: Native motion row | 0 | minimum=0; maximum=350; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].common_states[].like | integer: Inherited motion row | 0 | minimum=0; maximum=350; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].common_states[].subaction | integer: Installed retail animation row | 0 | minimum=0; maximum=1023; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].common_states[].flags | integer: Motion flags | 0 | minimum=0; maximum=2147483647; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].common_states[].move_id | integer: Stale move id | 0 | minimum=0; maximum=255; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].common_states[].move_tag | string: Declared move tag |  | enum=['jab', 'dash_attack', 'tilt', 'smash', 'aerial', 'grab', 'throw', 'special', 'projectile']; geno.md §22; melee/pc/platform/geno_registry.c |
| fighters[].common_states[].anim | string: Callback override |  | enum=['like', 'next', 'loop', 'hold', 'glide.start', 'glide', 'tornado', 'drill', 'drill.end', 'glide.after', 'cape']; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].common_states[].iasa | string: Callback override |  | enum=['like', 'interrupt', 'none', 'glide']; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].common_states[].phys | string: Callback override |  | enum=['like', 'cape', 'none', 'air', 'air_nodrift', 'air_drift', 'brake', 'ground', 'auto', 'anim_motion', 'glide.start', 'glide', 'glide.attack', 'glide.end', 'tornado', 'drill', 'drill.end', 'drill.start']; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].common_states[].coll | string: Callback override |  | enum=['like', 'cape', 'cape.after', 'none', 'air', 'air_noledge', 'ground', 'ground_stop', 'both', 'anim_motion', 'glide', 'drill', 'drill.start']; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].name | string: Log display name | target Pl file | maxLength=63; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes | object: Named settings | absent | maxProperties=128; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].attributes.walk_accel_mul | number: Common attribute walk_accel_mul | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.walk_accel_base | number: Common attribute walk_accel_base | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.walk_max_vel | number: Common attribute walk_max_vel | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.slow_walk_max | number: Common attribute slow_walk_max | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.mid_walk_point | number: Common attribute mid_walk_point | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.fast_walk_min | number: Common attribute fast_walk_min | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.ground_friction | number: Common attribute ground_friction | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.dash_initial_velocity | number: Common attribute dash_initial_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.dash_accel_mul | number: Common attribute dash_accel_mul | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.dash_accel_base | number: Common attribute dash_accel_base | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.dash_max_velocity | number: Common attribute dash_max_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.run_animation_scaling | number: Common attribute run_animation_scaling | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.max_run_brake_frames | number: Common attribute max_run_brake_frames | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.ground_max_horizontal_velocity | number: Common attribute ground_max_horizontal_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.jump_startup_time | number: Common attribute jump_startup_time | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.jump_h_initial_velocity | number: Common attribute jump_h_initial_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.jump_v_initial_velocity | number: Common attribute jump_v_initial_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.ground_to_air_jump_momentum_multiplier | number: Common attribute ground_to_air_jump_momentum_multiplier | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.jump_h_max_velocity | number: Common attribute jump_h_max_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.hop_v_initial_velocity | number: Common attribute hop_v_initial_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.air_jump_v_multiplier | number: Common attribute air_jump_v_multiplier | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.air_jump_h_multiplier | number: Common attribute air_jump_h_multiplier | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.max_jumps | integer: Common attribute max_jumps | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.gravity | number: Common attribute gravity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.terminal_velocity | number: Common attribute terminal_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.air_drift_stick_mul | number: Common attribute air_drift_stick_mul | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.aerial_drift_base | number: Common attribute aerial_drift_base | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.air_drift_max | number: Common attribute air_drift_max | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.aerial_friction | number: Common attribute aerial_friction | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.fast_fall_velocity | number: Common attribute fast_fall_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.air_max_horizontal_velocity | number: Common attribute air_max_horizontal_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.jab_2_input_window | number: Common attribute jab_2_input_window | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.jab_3_input_window | number: Common attribute jab_3_input_window | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.standing_turn_frames | number: Common attribute standing_turn_frames | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.weight | number: Common attribute weight | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.model_scaling | number: Common attribute model_scaling | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.initial_shield_size | number: Common attribute initial_shield_size | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.shield_break_initial_velocity | number: Common attribute shield_break_initial_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.rapid_jab_window | integer: Common attribute rapid_jab_window | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.clank_animation_length | number: Common attribute clank_animation_length | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.hit_spark_variant | integer: Common attribute hit_spark_variant | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.ledge_jump_horizontal_velocity | number: Common attribute ledge_jump_horizontal_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.ledge_jump_vertical_velocity | number: Common attribute ledge_jump_vertical_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.item_throw_velocity_multiplier | number: Common attribute item_throw_velocity_multiplier | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.heavy_throw_velocity_multiplier | number: Common attribute heavy_throw_velocity_multiplier | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.specials_ground_speed_retention | number: Common attribute specials_ground_speed_retention | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.kirby_b_star_damage | number: Common attribute kirby_b_star_damage | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.normal_landing_lag | number: Common attribute normal_landing_lag | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.landingairn_lag | number: Common attribute landingairn_lag | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.landingairf_lag | number: Common attribute landingairf_lag | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.landingairb_lag | number: Common attribute landingairb_lag | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.landingairhi_lag | number: Common attribute landingairhi_lag | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.landingairlw_lag | number: Common attribute landingairlw_lag | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.name_tag_height | number: Common attribute name_tag_height | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.passivewall_vel_x | number: Common attribute passivewall_vel_x | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.wall_jump_horizontal_velocity | number: Common attribute wall_jump_horizontal_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.wall_jump_vertical_velocity | number: Common attribute wall_jump_vertical_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.passiveceil_vel_x | number: Common attribute passiveceil_vel_x | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.trophy_scale | number: Common attribute trophy_scale | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.screw_attack_launch_velocity | number: Common attribute screw_attack_launch_velocity | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.wall_jump_min_approach_speed | number: Common attribute wall_jump_min_approach_speed | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.damageice_ice_size | number: Common attribute damageice_ice_size | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.damageicejump_vel_y | number: Common attribute damageicejump_vel_y | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.damageicejump_vel_x_mult | number: Common attribute damageicejump_vel_x_mult | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.respawn_platform_scale | number: Common attribute respawn_platform_scale | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.warp_star_hitbox_scale | number: Common attribute warp_star_hitbox_scale | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].attributes.camera_zoom_target_bone | integer: Common attribute camera_zoom_target_bone | disc value | ; geno.md §7; melee/pc/platform/geno_registry.c |
| fighters[].jumps | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].jumps.max | integer: Total jumps including ground jump | disc value | minimum=1; maximum=250; geno.md §10; melee/pc/platform/geno_registry.c |
| fighters[].jumps.air_vy | array: Ordered entries | absent | maxItems=16; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].hooks | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].hooks.on_init | array: Ordered entries | absent | maxItems=8; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].hooks.on_frame | array: Ordered entries | absent | maxItems=8; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].hooks.on_action | array: Ordered entries | absent | maxItems=8; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].hooks.on_land | array: Ordered entries | absent | maxItems=8; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].hooks.on_hit | array: Ordered entries | absent | maxItems=8; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].states | array: Ordered entries | absent | maxItems=48; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].states[].name | string: State target name |  | maxLength=31; geno.md §16.1; melee/pc/platform/geno_registry.c |
| fighters[].states[].behavior | string: Callback bundle |  | enum=['geno.air', 'geno.ground', 'geno.anim_motion', 'geno.glide.start', 'geno.glide', 'geno.glide.attack', 'geno.glide.landing', 'geno.glide.end', 'geno.tornado', 'geno.drill', 'geno.drill.end', 'geno.cape', 'geno.cape.attack', 'geno.cape.end', 'geno.drill.start']; geno.md §16.2; melee/pc/platform/geno_registry.c |
| fighters[].states[].subaction | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].states[].like | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].states[].flags | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].states[].move_id | integer: Move id for staling | from like / behavior | minimum=0; maximum=255; geno.md §16.1; melee/pc/platform/geno_registry.c |
| fighters[].states[].next | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].states[].land | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].states[].landing_lag | number: Landing lag | 0 | ; geno.md §16.1; melee/pc/platform/geno_registry.c |
| fighters[].states[].ledge | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].states[].liftoff | ['boolean', 'number']: Enable when nonzero | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].states[].origin | ['boolean', 'number']: Enable when nonzero | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].states[].move_tag | string: Declared move tag |  | enum=['jab', 'dash_attack', 'tilt', 'smash', 'aerial', 'grab', 'throw', 'special', 'projectile']; geno.md §22; melee/pc/platform/geno_registry.c |
| fighters[].states[].gravity | number: Root-motion gravity multiplier | 0 | ; geno.md §17; melee/pc/platform/geno_registry.c |
| fighters[].states[].facing | string: Lock root-motion travel to entry facing |  | enum=['entry']; geno.md §17; melee/pc/platform/geno_registry.c |
| fighters[].states[].counter | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].states[].counter.from | integer: First counter action frame | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].states[].counter.to | integer: Last counter action frame | 2147483647 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].states[].counter.target | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].states[].counter.negate | ['boolean', 'number']: Enable when nonzero | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].states[].anim | string: Override anim callback | behavior callback | enum=['like', 'next', 'loop', 'hold', 'glide.start', 'glide', 'tornado', 'drill', 'drill.end', 'glide.after', 'cape']; geno.md §16.2; melee/pc/platform/geno_registry.c |
| fighters[].states[].iasa | string: Override iasa callback | behavior callback | enum=['like', 'interrupt', 'none', 'glide']; geno.md §16.2; melee/pc/platform/geno_registry.c |
| fighters[].states[].phys | string: Override phys callback | behavior callback | enum=['like', 'cape', 'none', 'air', 'air_nodrift', 'air_drift', 'brake', 'ground', 'auto', 'anim_motion', 'glide.start', 'glide', 'glide.attack', 'glide.end', 'tornado', 'drill', 'drill.end', 'drill.start']; geno.md §16.2; melee/pc/platform/geno_registry.c |
| fighters[].states[].coll | string: Override coll callback | behavior callback | enum=['like', 'cape', 'cape.after', 'none', 'air', 'air_noledge', 'ground', 'ground_stop', 'both', 'anim_motion', 'glide', 'drill', 'drill.start']; geno.md §16.2; melee/pc/platform/geno_registry.c |
| fighters[].articles | array: Ordered entries | absent | maxItems=16; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].name | string: Article name |  | maxLength=31; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].model | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].model.file | string: Model archive path |  | maxLength=63; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].model.symbol | string: Model joint public symbol; absent uses first *_joint |  | maxLength=63; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].lifetime | number: Lifetime in logic frames | 60 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].velocity | array: Ordered entries | absent | maxItems=2; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].spawn | array: Ordered entries | absent | maxItems=2; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].scale | number: Model scale | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].spin | number: Model spin in degrees per frame | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].max_live | integer: Live article limit | 4 | minimum=1; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].homing | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].homing.turn | number: turn | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].homing.range | number: range | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].homing.delay | number: delay | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].despawn | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].despawn.hit | ['boolean', 'number']: Enable when nonzero | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].despawn.shield | ['boolean', 'number']: Enable when nonzero | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].despawn.stage | ['boolean', 'number']: Enable when nonzero | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].despawn.clank | ['boolean', 'number']: Enable when nonzero | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].spins | array: Ordered entries | absent | maxItems=4; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].spins[].joint | integer: Model joint index | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].spins[].z | number: Joint spin radians per frame | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].bone | integer: Spawn joint; -1 = position | -1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].effect | integer: Melee effect id | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].fx | string: Effect package name |  | ; geno.md §20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].spawn_sound | string: Name from the fighter's sounds table played at spawn |  | maxLength=31; geno.md §22.2; melee/pc/platform/geno_registry.c |
| fighters[].articles[].end_sound | string: Name from the fighter's sounds table played when the article goes |  | maxLength=31; geno.md §22.2; melee/pc/platform/geno_registry.c |
| fighters[].articles[].effects | array: Ordered entries | absent | maxItems=8; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].effects[].id | integer: Effect id | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].effects[].frame | integer: Attach life frame | 0 | minimum=0; maximum=65535; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].effects[].joint | integer: Model joint | 0 | minimum=0; maximum=255; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].effects[].count | integer: Consecutive effect count | 1 | minimum=1; maximum=256; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].spawns | array: Ordered entries | absent | maxItems=4; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes | array: Ordered entries | absent | maxItems=8; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].damage | number: Damage percent | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].size | number: Hitbox radius | 3 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].offset | array: Ordered entries | absent | maxItems=3; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].angle | integer: Launch angle | 361 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].kbg | integer: Knockback growth | 100 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].wkb | integer: Weight-set knockback | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].bkb | integer: Base knockback | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].element | integer: Hit element | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].shield_damage | integer: Shield damage | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].stun | integer: Extra hitstun | 0 | minimum=0; maximum=255; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].sfx_severity | integer: Hit sound severity | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].sfx_kind | integer: Hit sound kind | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].start | integer: First active life frame | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].end | integer: Last active life frame; 0 = lifetime | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].slot | integer: Live hitbox slot | entry index modulo 4 | minimum=0; maximum=3; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].hits | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].hits.ground | ['boolean', 'number']: Enable when nonzero | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].hits.air | ['boolean', 'number']: Enable when nonzero | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].hits.reflect | ['boolean', 'number']: Enable when nonzero | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].hits.absorb | ['boolean', 'number']: Enable when nonzero | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].hitboxes[].hits.counter | ['boolean', 'number']: Enable when nonzero | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].children | array: Ordered entries | absent | maxItems=2; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].children[].article | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].articles[].children[].frame | integer: First spawn frame | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].children[].every | integer: Repeat interval; 0 = once | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].children[].count | integer: Spawn count | 1 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].children[].spawn | integer: Spawn variant | 0 | minimum=0; maximum=3; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].gravity | number: gravity | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].max_fall | number: max fall | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].accel | number: accel | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].max_speed | number: max speed | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].min_speed | number: min speed | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].articles[].angle | number: angle | 0 | ; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].subactions | array: Ordered entries | absent | maxItems=64; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].subactions[].index | integer: Subaction row to replace | 0 | minimum=0; maximum=1023; geno.md §15.5; melee/pc/platform/geno_registry.c |
| fighters[].subactions[].words | array: Ordered entries | absent | maxItems=16383; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].subactions[].file | string: Whitespace word file relative to mod root |  | ; geno.md §15.5; melee/pc/platform/geno_registry.c |
| fighters[].subactions[].move_tag | string: Declared move tag |  | enum=['jab', 'dash_attack', 'tilt', 'smash', 'aerial', 'grab', 'throw', 'special', 'projectile']; geno.md §22; melee/pc/platform/geno_registry.c |
| fighters[].special_attributes | array: Ordered entries | absent | maxItems=64; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].special_attributes[].index | integer: Special attribute word index | 0 | minimum=0; maximum=264; geno.md §15.5; melee/pc/platform/geno_registry.c |
| fighters[].special_attributes[].offset | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].special_attributes[].float | number: Float override | 0 | ; geno.md §15.5; melee/pc/platform/geno_registry.c |
| fighters[].special_attributes[].int | integer: Integer override | 0 | minimum=-2147483648; maximum=2147483647; geno.md §15.5; melee/pc/platform/geno_registry.c |
| fighters[].moves | object: Authoring sugar for defines (move names: lowercase letters, digits, hyphens): expands to a subactions overlay plus a common_states row at export/check; the engine reads no such key | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].on_land | array: Ordered entries | absent | maxItems=16; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].on_land[].from | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].on_land[].to | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].on_land[].keep_frame | boolean: Keep current animation frame | False | ; geno.md §15.5; melee/pc/platform/geno_registry.c |
| fighters[].motion_anims | array: Ordered entries | absent | maxItems=8; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].motion_anims[].motion | integer: Common motion id | 0 | minimum=0; maximum=1023; geno.md §19.12; melee/pc/platform/geno_registry.c |
| fighters[].motion_anims[].subaction | integer: Animation row | 0 | minimum=0; maximum=1023; geno.md §19.12; melee/pc/platform/geno_registry.c |
| fighters[].specials | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.n | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.n.select | string: Integer bank selector |  | pattern=^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].specials.n.targets | array: Ordered entries | absent | maxItems=4; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.s | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.s.select | string: Integer bank selector |  | pattern=^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].specials.s.targets | array: Ordered entries | absent | maxItems=4; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.hi | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.hi.select | string: Integer bank selector |  | pattern=^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].specials.hi.targets | array: Ordered entries | absent | maxItems=4; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.lw | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.lw.select | string: Integer bank selector |  | pattern=^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].specials.lw.targets | array: Ordered entries | absent | maxItems=4; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_n | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_n.select | string: Integer bank selector |  | pattern=^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_n.targets | array: Ordered entries | absent | maxItems=4; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_s | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_s.select | string: Integer bank selector |  | pattern=^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_s.targets | array: Ordered entries | absent | maxItems=4; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_hi | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_hi.select | string: Integer bank selector |  | pattern=^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_hi.targets | array: Ordered entries | absent | maxItems=4; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_lw | choice: See choice encodings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_lw.select | string: Integer bank selector |  | pattern=^(la_i\|ra_i):(?:[0-9]\|[1-5][0-9]\|6[0-3])$; geno.md §19; melee/pc/platform/geno_registry.c |
| fighters[].specials.air_lw.targets | array: Ordered entries | absent | maxItems=4; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].fx_bindings | string: Effect bindings JSON relative path |  | ; geno.md §20; melee/pc/platform/geno_registry.c |
| fighters[].sounds | array: Ordered entries | absent | maxItems=16; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].sounds[].name | string: Sound name an article refers to |  | maxLength=31; geno.md §22.2; melee/pc/platform/geno_registry.c |
| fighters[].sounds[].retail_sfx | integer: Engine sound id (ft_PlaySFX's) | 0 | minimum=1; maximum=999999; geno.md §22.2; melee/pc/platform/geno_registry.c |
| fighters[].sounds[].volume | integer: Volume 0..127 | 127 | minimum=0; maximum=127; geno.md §22.2; melee/pc/platform/geno_registry.c |
| fighters[].glide | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].glide.angle_max | ['number', 'boolean']: Behavior parameter angle_max | 80.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.angle_min | ['number', 'boolean']: Behavior parameter angle_min | -70.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.start_vy | ['number', 'boolean']: Behavior parameter start_vy | 0.75 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.start_gravity | ['number', 'boolean']: Behavior parameter start_gravity | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.start_vx | ['number', 'boolean']: Behavior parameter start_vx | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.speed | ['number', 'boolean']: Behavior parameter speed | 1.7 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.speed_accel | ['number', 'boolean']: Behavior parameter speed_accel | 0.04 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.max_speed | ['number', 'boolean']: Behavior parameter max_speed | 2.2 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.stall_speed | ['number', 'boolean']: Behavior parameter stall_speed | 0.7 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.sink_accel | ['number', 'boolean']: Behavior parameter sink_accel | 0.03 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.max_sink | ['number', 'boolean']: Behavior parameter max_sink | 0.6 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.recover_angle | ['number', 'boolean']: Behavior parameter recover_angle | 15.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.dive_angle | ['number', 'boolean']: Behavior parameter dive_angle | -25.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.dive_bonus | ['number', 'boolean']: Behavior parameter dive_bonus | 0.03 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w14 | ['number', 'boolean']: Behavior parameter w14 | 0.15 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.deadzone | ['number', 'boolean']: Behavior parameter deadzone | 0.25 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.pitch_up | ['number', 'boolean']: Behavior parameter pitch_up | 0.55 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.pitch_down | ['number', 'boolean']: Behavior parameter pitch_down | 0.75 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.max_pitch_rate | ['number', 'boolean']: Behavior parameter max_pitch_rate | 7.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.stall_pitch | ['number', 'boolean']: Behavior parameter stall_pitch | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.wing_node | ['number', 'boolean']: Behavior parameter wing_node | 44.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w21 | ['number', 'boolean']: Behavior parameter w21 | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.hold_frames | ['number', 'boolean']: Behavior parameter hold_frames | 16.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.from_ground_jump | ['number', 'boolean']: Behavior parameter from_ground_jump | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.end_helpless | ['number', 'boolean']: Behavior parameter end_helpless | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.landing_lag | ['number', 'boolean']: Behavior parameter landing_lag | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.entry | ['number', 'boolean']: Behavior parameter entry | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.max_frames | ['number', 'boolean']: Behavior parameter max_frames | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.pose_center | ['number', 'boolean']: Behavior parameter pose_center | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.end_buttons | ['number', 'boolean']: Behavior parameter end_buttons | 14 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.script_entry_helpless | ['number', 'boolean']: Behavior parameter script_entry_helpless | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w00 | ['number', 'boolean']: Behavior parameter w00 | 80.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w01 | ['number', 'boolean']: Behavior parameter w01 | -70.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w02 | ['number', 'boolean']: Behavior parameter w02 | 0.75 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w03 | ['number', 'boolean']: Behavior parameter w03 | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w04 | ['number', 'boolean']: Behavior parameter w04 | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w05 | ['number', 'boolean']: Behavior parameter w05 | 1.7 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w06 | ['number', 'boolean']: Behavior parameter w06 | 0.04 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w07 | ['number', 'boolean']: Behavior parameter w07 | 2.2 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w08 | ['number', 'boolean']: Behavior parameter w08 | 0.7 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w09 | ['number', 'boolean']: Behavior parameter w09 | 0.03 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w10 | ['number', 'boolean']: Behavior parameter w10 | 0.6 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w11 | ['number', 'boolean']: Behavior parameter w11 | 15.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w12 | ['number', 'boolean']: Behavior parameter w12 | -25.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w13 | ['number', 'boolean']: Behavior parameter w13 | 0.03 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w15 | ['number', 'boolean']: Behavior parameter w15 | 0.25 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w16 | ['number', 'boolean']: Behavior parameter w16 | 0.55 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w17 | ['number', 'boolean']: Behavior parameter w17 | 0.75 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w18 | ['number', 'boolean']: Behavior parameter w18 | 7.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w19 | ['number', 'boolean']: Behavior parameter w19 | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].glide.w20 | ['number', 'boolean']: Behavior parameter w20 | 44.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].tornado.entry_vy | ['number', 'boolean']: Behavior parameter entry_vy | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.entry_vx_mul | ['number', 'boolean']: Behavior parameter entry_vx_mul | 0.7 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.start_rate | ['number', 'boolean']: Behavior parameter start_rate | 80.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.ground_accel | ['number', 'boolean']: Behavior parameter ground_accel | 0.12 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.ground_speed | ['number', 'boolean']: Behavior parameter ground_speed | 2.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.air_accel | ['number', 'boolean']: Behavior parameter air_accel | 0.1 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.air_speed | ['number', 'boolean']: Behavior parameter air_speed | 1.7 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.brake | ['number', 'boolean']: Behavior parameter brake | 0.008 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.gravity | ['number', 'boolean']: Behavior parameter gravity | -0.08 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.max_fall | ['number', 'boolean']: Behavior parameter max_fall | 0.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.tap_vy | ['number', 'boolean']: Behavior parameter tap_vy | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.tap_cooldown | ['number', 'boolean']: Behavior parameter tap_cooldown | 10.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.max_rise | ['number', 'boolean']: Behavior parameter max_rise | 1.4 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.tap_rate | ['number', 'boolean']: Behavior parameter tap_rate | 16.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.max_rate | ['number', 'boolean']: Behavior parameter max_rate | 80.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.rate_decay | ['number', 'boolean']: Behavior parameter rate_decay | 1.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.spin_frames | ['number', 'boolean']: Behavior parameter spin_frames | 70.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.late_decay | ['number', 'boolean']: Behavior parameter late_decay | 2.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.end_rate | ['number', 'boolean']: Behavior parameter end_rate | 10.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w19 | ['number', 'boolean']: Behavior parameter w19 | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.max_speed | ['number', 'boolean']: Behavior parameter max_speed | 2.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.end_helpless | ['number', 'boolean']: Behavior parameter end_helpless | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.spin_anim | ['number', 'boolean']: Behavior parameter spin_anim | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.spin_period | ['number', 'boolean']: Behavior parameter spin_period | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w00 | ['number', 'boolean']: Behavior parameter w00 | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w01 | ['number', 'boolean']: Behavior parameter w01 | 0.7 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w02 | ['number', 'boolean']: Behavior parameter w02 | 80.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w03 | ['number', 'boolean']: Behavior parameter w03 | 0.12 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w04 | ['number', 'boolean']: Behavior parameter w04 | 2.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w05 | ['number', 'boolean']: Behavior parameter w05 | 0.1 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w06 | ['number', 'boolean']: Behavior parameter w06 | 1.7 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w07 | ['number', 'boolean']: Behavior parameter w07 | 0.008 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w08 | ['number', 'boolean']: Behavior parameter w08 | -0.08 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w09 | ['number', 'boolean']: Behavior parameter w09 | 0.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w10 | ['number', 'boolean']: Behavior parameter w10 | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w11 | ['number', 'boolean']: Behavior parameter w11 | 10.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w12 | ['number', 'boolean']: Behavior parameter w12 | 1.4 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w13 | ['number', 'boolean']: Behavior parameter w13 | 16.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w14 | ['number', 'boolean']: Behavior parameter w14 | 80.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w15 | ['number', 'boolean']: Behavior parameter w15 | 1.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w16 | ['number', 'boolean']: Behavior parameter w16 | 70.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w17 | ['number', 'boolean']: Behavior parameter w17 | 2.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].tornado.w18 | ['number', 'boolean']: Behavior parameter w18 | 10.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].drill.start_vx_mul | ['number', 'boolean']: Behavior parameter start_vx_mul | 0.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.start_vy | ['number', 'boolean']: Behavior parameter start_vy | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.start_gravity | ['number', 'boolean']: Behavior parameter start_gravity | -0.08 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.steer | ['number', 'boolean']: Behavior parameter steer | 3.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.end_frames | ['number', 'boolean']: Behavior parameter end_frames | 10.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.w05 | ['number', 'boolean']: Behavior parameter w05 | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.speed | ['number', 'boolean']: Behavior parameter speed | 2.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.angle_max | ['number', 'boolean']: Behavior parameter angle_max | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.bounce | ['number', 'boolean']: Behavior parameter bounce | 0.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.pop_vx | ['number', 'boolean']: Behavior parameter pop_vx | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.pop_vy | ['number', 'boolean']: Behavior parameter pop_vy | 2.1 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.end_helpless | ['number', 'boolean']: Behavior parameter end_helpless | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.pitch_model | ['number', 'boolean']: Behavior parameter pitch_model | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.w00 | ['number', 'boolean']: Behavior parameter w00 | 0.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.w01 | ['number', 'boolean']: Behavior parameter w01 | 1.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.w02 | ['number', 'boolean']: Behavior parameter w02 | -0.08 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.w03 | ['number', 'boolean']: Behavior parameter w03 | 3.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].drill.w04 | ['number', 'boolean']: Behavior parameter w04 | 10.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape | object: Named settings | absent | ; geno.md §§7,15–20; melee/pc/platform/geno_registry.c |
| fighters[].cape.keep_vx | ['number', 'boolean']: Behavior parameter keep_vx | 0.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.keep_vy | ['number', 'boolean']: Behavior parameter keep_vy | 0.4 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.steer_accel_x | ['number', 'boolean']: Behavior parameter steer_accel_x | 0.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.steer_max_x | ['number', 'boolean']: Behavior parameter steer_max_x | 2.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.steer_accel_y | ['number', 'boolean']: Behavior parameter steer_accel_y | 0.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.steer_max_y | ['number', 'boolean']: Behavior parameter steer_max_y | 2.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.steer_frame | ['number', 'boolean']: Behavior parameter steer_frame | 12.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.decide_frame | ['number', 'boolean']: Behavior parameter decide_frame | 26.0 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.neutral_x | ['number', 'boolean']: Behavior parameter neutral_x | 0.3 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.attack_buttons | ['number', 'boolean']: Behavior parameter attack_buttons | 3 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.w00 | ['number', 'boolean']: Behavior parameter w00 | 0.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.w01 | ['number', 'boolean']: Behavior parameter w01 | 0.4 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.w02 | ['number', 'boolean']: Behavior parameter w02 | 0.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.w03 | ['number', 'boolean']: Behavior parameter w03 | 2.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.w04 | ['number', 'boolean']: Behavior parameter w04 | 0.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |
| fighters[].cape.w05 | ['number', 'boolean']: Behavior parameter w05 | 2.5 | ; geno.md §16.4; melee/pc/geno/geno_game_v2.inc:geno_params |

## Runtime limits

| Constant | Value | Source |
|---|---|---|
| GENO_VARS_PER_BANK | 64 | melee/pc/geno/geno.h:47 |
| GENO_SPECIAL_WORDS | 265 | melee/pc/geno/geno.h:137 |
| GENO_MAX_CHECKS | 8 | melee/pc/geno/geno.h:180 |
| GENO_CHECK_CONDS | 3 | melee/pc/geno/geno.h:181 |
| GENO_MAX_REHIT | 4 | melee/pc/geno/geno.h:182 |
| GENO_EV_MAX_HOOKS | 8 | melee/pc/geno/geno.h:247 |
| GENO_MAX_ATTRS | 128 | melee/pc/geno/geno.h:251 |
| GENO_MAX_JUMP_VY | 16 | melee/pc/geno/geno.h:252 |
| GENO_MAX_PROFILES | 65535 | melee/pc/geno/geno.h:253 |
| GENO_MAX_SPECIAL | 64 | melee/pc/geno/geno.h:254 |
| GENO_MAX_ONLAND | 16 | melee/pc/geno/geno.h:255 |
| GENO_MAX_MOTION_ANIM | 8 | melee/pc/geno/geno.h:256 |
| GENO_MAX_OVERLAYS | 64 | melee/pc/geno/geno.h:257 |
| GENO_POOL_WORDS | 16384 | melee/pc/geno/geno.h:258 |
| GENO_MAX_STATES | 48 | melee/pc/geno/geno.h:269 |
| GENO_ART_KIND_BASE | 4096 | melee/pc/geno/geno.h:354 |
| GENO_MAX_ARTICLES | 16 | melee/pc/geno/geno.h:354 |
| GENO_ART_PER_RANGE | 8 | melee/pc/geno/geno.h:361 |
| GENO_ART_EXTRA_BASE | 131072 | melee/pc/geno/geno.h:366 |
| GENO_MAX_SOUNDS | 16 | melee/pc/geno/geno.h:374 |
| GENO_ART_HITBOXES | 4 | melee/pc/geno/geno.h:375 |
| GENO_ART_HIT_ENTRIES | 8 | melee/pc/geno/geno.h:376 |
| GENO_ART_SPAWNS | 4 | melee/pc/geno/geno.h:378 |
| GENO_ART_CHILDREN | 2 | melee/pc/geno/geno.h:379 |
| GENO_SP_SELECT | 4 | melee/pc/geno/geno.h:478 |
| JDOC_NODES | 4096 | melee/pc/platform/geno_registry.c:72 |
| JDOC_ARENA | 65536 | melee/pc/platform/geno_registry.c:73 |
| GN_MAX_SLOTS | 256 | melee/pc/platform/geno_registry.c:457 |
| JSON_DEPTH | 32 | melee/pc/platform/geno_registry.c:jd_value |
| JSON_FILE_BYTES | 1048576 | melee/pc/platform/geno_registry.c:gn_read_file |

## Attach names and aliases

`mario` (PlMr.dat), `fox` (PlFx.dat), `captain` (PlCa.dat), `falcon` (PlCa.dat), `donkey` (PlDk.dat), `dk` (PlDk.dat), `kirby` (PlKb.dat), `koopa` (PlKp.dat), `bowser` (PlKp.dat), `link` (PlLk.dat), `seak` (PlSk.dat), `sheik` (PlSk.dat), `ness` (PlNs.dat), `peach` (PlPe.dat), `popo` (PlPp.dat), `nana` (PlNn.dat), `pikachu` (PlPk.dat), `samus` (PlSs.dat), `yoshi` (PlYs.dat), `purin` (PlPr.dat), `jigglypuff` (PlPr.dat), `mewtwo` (PlMt.dat), `luigi` (PlLg.dat), `mars` (PlMs.dat), `marth` (PlMs.dat), `zelda` (PlZd.dat), `clink` (PlCl.dat), `younglink` (PlCl.dat), `drmario` (PlDr.dat), `falco` (PlFc.dat), `pichu` (PlPc.dat), `gamewatch` (PlGw.dat), `gnw` (PlGw.dat), `ganon` (PlGn.dat), `ganondorf` (PlGn.dat), `emblem` (PlFe.dat), `roy` (PlFe.dat)
