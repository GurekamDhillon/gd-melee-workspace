# Engine notes: Melee (melee.gc, melee.mex, melee.gdport)

## Engine ids
| id | meaning |
|---|---|
| `melee.gc` | retail SSBM NTSC 1.02 (GALE01) on GameCube hardware; addresses are retail and resolve through `melee/config/GALE01/symbols.txt` |
| `melee.mex` | the m-ex framework's semantics (registration in MxDt.dat, Arch_FighterFunc slots, relative id rules, API block 0x803D7058..) |
| `melee.gdport` | GD's Melee PC port: decomp compiled native, content PPC code interpreted, m-ex behaviour reimplemented |

## Index spaces
| space | what | stability |
|---|---|---|
| `melee.retail.character_kind` / `melee.retail.fighter_kind` | decomp CharacterKind / FighterKind for the 26/33 retail fighters; motion flags' low 6 bits hold a fighter_kind | stable |
| `melee.mex.internal` | MxDt internal id (pl_file, costume_file, anim, fighter_function, item_lookup, kirby_*, effect_index) | stable per disc |
| `melee.mex.external` | MxDt external/CSS id (names, costume_info, ssm_files, results, victory, announcer, insignia, end files, trophies) | stable per disc |
| `melee.mex.css_icon` | index in the MxDt CSS icon table | stable per disc |
| `melee.gdport.mex_slot` | dense index of present m-ex fighters | install_relative |
| `melee.gdport.fighter_kind` / `melee.gdport.character_kind` | 0x21 + slot / 0x22 + slot | install_relative |
| `melee.action_state` | MotionState id (common 0-340, content 341+ = x18) | stable |
| `melee.subaction_id` | row in ftData->xC (motion/"action" table: clip + ftcmd script) | stable |
| `melee.demo_motion_id` | row in ftData->x14 (results/intro/ending/ViWait) | stable |
| `melee.kirby_copy_subaction_id` | row in a Kirby copy file's ftcmd table | stable |
| `melee.item_kind` | global ItemKind (m-ex custom kinds >= 237) | stable per disc |
| `melee.effect_bank` / `melee.ssm_bank` | MxDt effect row / SSM row | stable per disc |
| `melee.sfx_id` / `melee.gfx_id` | ids as used by scripts (relative 5000+ or absolute) | see relative_id_rules |
| `melee.costume_id`, `melee.trophy_id`, `melee.bgm_id`, `melee.emblem_id` | as named | stable per disc |

## Extension blocks (`engine` keyed by engine id)
- Hitbox (`melee.gc`): `hit_sfx_raw` ("kind/level" as decoded), `flags5` (raw 5-bit field; bits 4..0 = hits_items, ignore_thrown, ignore_scale, clank, rebound - bit order inferred from the jab/SpecialNSpin decodes).
- Model (`melee.gc`): `render_modes`, `tobj_flags` histograms.
- Framework (`integration.frameworks[].engine_detail`): free-form.

## Script language `melee.ftcmd`
Opcode = top 6 bits of the first word; 0-9 generic lbCommand set, 10-58 dispatched through
`ftAction_803C06E8[op-10]` with word lengths from `ftAction_803C0870` (`melee/src/melee/ft/ftaction.c`).
AsyncWait n = wait until frame n; SyncWait n = wait n frames. Distances are raw/256. Mnemonics without a
canonical op become `engine.<lowercased name>` (e.g. `engine.ft_8008a1b8`, `engine.throw_flag_b3`).
