# Project terminology

Current naming reference, 2026-10-04. This file defines preferred prose across the project; it does not rename APIs or supersede dated gameplay acceptance. Existing code spellings remain valid until migrated. Sources are repository-relative and public-safe.

## Collisions and naming rules

| Ambiguous word | Use from now on | Stop using |
|---|---|---|
| Geno | the Geno engine on first use; Geno profile/state thereafter; Geno character for the unrelated public character | bare Geno when the meaning is unclear |
| Slot | fighter slot, roster slot, stage slot, drive slot, save slot; resident alias for a runtime fighter-kind mapping | bare slot; treating roster row, controller port and live fighter as synonyms |
| State | fighter action state; combat status; savestate; game state; save profile | state used for all five meanings |
| Item | retail item; Geno standalone item; article; drive loot or drive pickup | item meaning both equipped drive and native collision object |
| Armour | retail knockback armour; named armour type; resistance for percent/launch reduction | armoured implying super armour; directional armour called a type |
| Port | controller port; fighter adaptation for imported fighter work; PC port for the platform | bare port across these meanings |
| Mod | script mod or mod folder; modifier; m-ex content mod | mod as shorthand for a modifier in technical prose |
| Echo / afterimage / copy | gameplay echo; rendered afterimage; afterimage copy; modifier copies | echo for a picture; copy for an unspecified clone, sample or stack |
| Tag | move tag; player name tag | bare tag where player identity and combat filtering meet |
| Stage | level or arena for gameplay location; build phase; LAB roadmap milestone; stage slot for loaded resource | stage for build/LAB progress without a qualifier |
| Hook / effect / family | script hook, Geno state hook or Geno command hook; gameplay effect or visual effect; effect family or move family | unqualified cross-engine hook, effect or family |
| Profile / overlay / depth | Geno profile or save profile; subaction overlay or HUD overlay; progression depth or history/render depth | unqualified profile, overlay or depth across layers |

## Definitions

Entries without a status qualifier describe existing source concepts, not a claim that today's executable contains them. In flight, parked and proposed describe integration or implementation limits. Definitions refer to the implementation or owning reference, rather than listing every API spelling.

### Port and build

| Term | Definition and boundary | Where |
|---|---|---|
| Bridge | Generated guest-address-to-native-function lookup used by m-ex calls. A successful link does not prove the bridge matches the final map. | `tools/port/build.sh` |
| LAB | Offline inspection, drill, savestate and rewind environment for the game. It is not the retail run director or proof that a rule works in Classic. | `melee/docs/geno.md` |
| Provenance | Evidence identifying which source, assets and executable produced a result. Source inspection alone is not executable provenance. | `docs/HANDOFF.md` |
| Retarget | Translate PowerPC-compiled game code into native code while preserving guest memory conventions. It is not compiling the original game C directly as ordinary native C. | `melee/pc/tools/gwtool` |
| Run folder | Isolated directory containing one launch's copied executable, configuration and logs. Its executable can lag the main build. | `tools/port/run.sh` |
| Shim | Native implementation of a platform service or boundary adapter used by retargeted game code. Native code must respect the game's big-endian memory. | `melee/CLAUDE.md` |

### Modding

| Term | Definition and boundary | Where |
|---|---|---|
| Fighter slot | Live match position for a primary fighter, potentially with a secondary fighter object. It is not a roster catalogue entry. | `docs/scripting.md` |
| m-ex | Melee extension ecosystem and its data/code conventions, supported through the port's compatibility machinery. It is not the Geno engine or a Lua modifier. | `docs/MEX_PORT_STATUS.md` |
| Mod folder | Packaged script or content directory with metadata and resources loaded by the mod system. Use this phrase rather than bare mod when packaging is meant. | `docs/mods-packaging.md` |
| Resident alias | Bounded native fighter-kind identifier assigned to a loaded roster identity. It is not that identity's permanent catalogue key. | `melee/pc/platform/gw_roster_catalog.h` |
| Roster registry | Catalogue of stable fighter identities and their mapping to bounded resident aliases. Catalogue membership does not establish online admission. | `melee/pc/platform/gw_roster_catalog.h` |
| Roster slot | Entry or selectable identity in a roster, rather than a live match position. Qualify m-ex row numbers when those are meant. | `docs/MEX_PORT_STATUS.md` |

### Geno engine

| Term | Definition and boundary | Where |
|---|---|---|
| .genoasm | Text authoring format for Geno move-script commands compiled into script words. It is not a Lua script. | `tools/geno` |
| Article | Fighter-owned projectile or other spawned object defined by the Geno engine and executed through native Item machinery. Ownership does not make every article a projectile. | `melee/pc/geno/geno_game_articles.inc` |
| Attach | Add a Geno profile to an existing retail or m-ex fighter, retaining its host foundation. It is not a new independent fighter definition. | `melee/pc/platform/geno_registry.c` |
| Define | Declare a fighter foundation through the Geno engine rather than merely attaching extensions. Slice 1 is in flight and narrowly admits native Mario/common behavior; full fighter authoring is not accepted. | `melee/pc/platform/geno_define_registry.inc` |
| Fighter action state | Current fighter behavior state, including animation, interrupt, physics and collision callbacks. It is not a timed combat status. | `melee/pc/geno/geno.h` |
| Geno engine | This project's fighter-extension engine for attributes, states, move scripts, articles and overlays. It is unrelated to the public mod character with the same name. | `melee/docs/geno.md` |
| Geno standalone item | Native item defined independently of a fighter-owned article, with its own behavior and lifetime. It is not drive loot merely because it can be collected. | `melee/pc/geno/geno_game_items.inc` |
| Move script | Ordered commands executed during a fighter move, including Geno escape commands. It is not a modifier rule evaluated from a gameplay event. | `melee/pc/geno/geno.h` |
| Overlay | Geno replacement or extension of an existing subaction's script data. Say HUD overlay for interface graphics. | `melee/pc/platform/geno_registry.c` |
| Profile | Loaded Geno definition and its immutable configuration. Say save profile for persistent player progress. | `melee/pc/platform/geno_registry.c` |

### Menus

| Term | Definition and boundary | Where |
|---|---|---|
| Legacy menu kit | The owner's name for the current menu stuff: everything the port draws or wraps for menus before the Atlas re-unification: the native frontend (`gmfrontend*`), the old `gd.kit` panel, button and list, the `menu/out_*` art sets, the Envoy and LAB screen code, the launcher's own kit copy, and the retail screens until each is replaced. Removed piece by piece as screens move to Atlas. | `docs/superpowers/specs/2026-10-06-menu-reunification-design.md` |
| Atlas | The new menu system and its style: the parts (plate, row, tab strip, toggle, choice, slider, cell, model cell, explainer, dialog, note, key hints, trail), the screen description, the layout and focus rules, and `gd.ui` (code names: `gw_ui_*`, the `at_` functions, `gd.ui`). Not the font atlas or a texture atlas, which keep their qualifier. | `melee/pc/platform/gw_ui_*`, `docs/scripting.md` |
| Engine screen | An Atlas screen owned by native code, not by a script: the title, the main menu and its hubs, Credits. The game side describes it each frame through the `Ui_*` shims and polls its events; a script (and the console) may not open, close, feed or replace one. The opposite is a mod screen, registered by `gd.ui.screen`. | `pc/platform/gw_script_ui.inc`, `src/melee/gm/gmfrontend_atlas.inc` |
| Mode profile | What one mode's character select may do: how many humans, whether CPUs can be added, teams from the rules, the fighters needed to start, whether only the entering port plays (the one-player modes), the Training dummy, whether a stage select follows, whether it is the online lobby's pick. A table keyed by the retail `CSSMatchType` (plus the lobby), checked against the enum by `tools/port/test_css_profiles.py`. | `melee/pc/platform/gw_ui_css_profile.c` |
| Port card | The 56 px card of one controller port in the character select's band: a 3 px top edge in the port's colour, the port's shape and numeral, the fighter's name and a line under it; a CPU says CPU and its level, an open slot OPEN, a closed one CLOSED. | `melee/pc/platform/gw_ui_parts.c`, spec 4.7 |
| Band | The strip between the primary pane and the key hints: the four port cards, or the matchup strip (the fighters and VS) of the loading screen. | `melee/pc/platform/gw_ui_layout.c` (`at_layout_split`) |
| Select screen (native) | The character select, stage select and loading screen when Atlas draws them: a screen record whose cells live in storage the game-side adapter owns (up to 256), opened and closed through a handle, never copied. The rules are the host's models (`gw_ui_css.c`, `gw_ui_sss.c`); the adapter reads the pads and the host's mouse events and ends the scene through the legacy writers. Disc art on its tiles is decoded in memory and never stored. | `melee/pc/platform/gw_script_ui_sel.inc`, `melee/src/melee/gm/gmfrontend_atlas_select.inc` |
| Value row | A list row that carries a value: a toggle, a choice, a slider or a readout. A choice may hold its options and a slider its step; the engine applies a left, right or A to it with one rule (`at_item_apply`, the legacy `fe_change`), and a script reads and writes it with `gd.ui.value` and `gd.ui.set_value`. | `melee/pc/platform/gw_ui_item.c`, `docs/scripting.md` |
| Readout | A value row that only shows a value and never changes it: a live text such as what a controller port reads, or a number the game formats. It takes no A. | `melee/src/melee/gm/gmfrontend_atlas_table.h` |
| Table walker | The game-side code that turns a settings-style `FrontendScreen` (a table of get and set pairs) into the rows of one Atlas tab each frame, evaluating `get`, `visible`, `enabled` and `format` on the game side, and applies the host's events with the legacy rules. The pages stay tables; the walker is a header tested without the game. | `melee/src/melee/gm/gmfrontend_atlas_table.h`, `gmfrontend_atlas_set.inc` |
| Freeze | An input hold on the settings screen while a name is typed or a controller capture runs: the host drops every event, and when it ends it primes the keys and the mouse from what is held at that instant, so a key that was down when the edit ended does not also accept or go back. | `melee/pc/platform/gw_script_ui_set.inc` (`gw_Ui_Freeze`) |
| Settings screen (native) | The Atlas drawing of SETTINGS: six tabs (VIDEO, AUDIO, CONTROLS, ONLINE, GAME, MODS) over the game's tables, and the remap editor, the how-to page, the erase screen and the Rules screens as screens of their own. One engine-owned slot filled in place through the `Ui_Set*` shims; the pad is the game's (intents), the keyboard and the mouse the host's. | `melee/pc/platform/gw_script_ui_set.inc`, `melee/src/melee/gm/gmfrontend_atlas_set.inc` |
| Stepper | A list value that changes with left and right (`on.change` gets the direction) and runs with A (`on.accept`); the script owns its text. Not a choice (A changes a choice) and not a slider. | `gw_ui_screen.h` `AT_VAL_STEPPER`, `docs/scripting.md` |
| Readout, track, chips | The three read-only HUD parts: label and value rows (a fighter's info), a move's timeline with hit windows and marks, and a strip of chips (a mode and its toggles). | `melee/pc/platform/gw_ui_hud_parts.h` |
| World backdrop | A screen's `backdrop = "world"`: a translucent scrim over the frozen game instead of the opaque ground. | `gw_ui_render.c` |
| MODS screen, mod detail | The Atlas screen that replaces Settings > Mods (INSTALLED and CONFLICTS tabs, toggles for the next boot) and the screen one mod's Y opens (requires, conflicts, what it adds, its own settings). Not the Settings MODS tab, which stays until the owner has looked. | `melee/pc/platform/gw_ui_mods.c`, `gw_script_ui_mods.inc` |
| `lab.pause`, `mods.self` | The two built-in entry parents Atlas step 7 adds: `lab.pause` (a row in the LAB's MODS tab, offline only) and `mods.self` (an entry in the mod's own detail screen; the registry files it under `mods.<id>`). Only the mod that draws a parent may read or activate its entries (`gd.ui.entries`, `gd.ui.activate`). | `gw_ui_registry.c` `at_reg_owner` |
| Framed screen, window, chrome | A **framed screen** is an Atlas screen (`AT_PRIMARY_FRAME`) drawn around a retail scene that runs unchanged: opaque plates in the ground colour around a **window** (a rectangle of the 640x480 retail canvas where retail's 3D shows through; nothing of Atlas is drawn inside it), with the **chrome** (trail, explainer, counter, key hints) on the plates. It has no focus, no events and no hit rectangles, because retail owns the pad. Used for the Trophy Gallery, Lottery and Collection. | `pc/platform/gw_ui_frame.c`, `gw_script_ui_toy.inc`, `src/melee/gm/gmfrontend_atlas_toy.inc` |
| Retail text | A string the retail game draws from the player's disc, stored as a glyph stream (`SIS` archives such as `SdToy.usd`), not as Unicode. Atlas shows it only after decoding every glyph in memory (step 8's decoder, `at_sis_decode`); a string with an unknown glyph is not shown, and where nothing decodes the retail text object stays visible. Never logged, never written. | `docs/superpowers/plans/2026-10-06-atlas-step10-bespoke-rehost.md` |
| Scene policy | How Atlas relates to one scene kind: RETAIL (the game's own scene), OVERLAY (the retail scene runs unchanged and Atlas draws an engine screen over it, as the title) or REPLACE (Atlas stands in for the scene's enter and frame pair; built, no user yet). Retail everywhere except the title, and `MELEE_ATLAS=0` makes everything retail. | `pc/platform/gw_ui_policy.c`, spec 6.8 |
| HUD zone | One of the six places (`top_left top_center top_right bottom_left bottom_center bottom_right`) inside the title-safe box where a script's HUD parts (`gd.ui.hud`) go. The engine stacks the parts in a zone (at most four) and keeps them clear of the retail HUD. Not a stage zone (`gd.zones`) and not a screen's four places (trail, primary, explainer, keys). | `gw_ui_hud.c`, `docs/scripting.md` "The HUD layer" |
| Keep-out rectangle | A rectangle of the retail HUD (the damage plates and stocks, the match timer) that the Atlas HUD layer will not place a part over; one is dropped from the list when its retail element is hidden. Estimates until measured in the game. | `at_hud_retail_keepouts`, `atlas keepout on` |
| Retail pause takeover | Atlas showing a script's pause screen (`gd.ui.pause_screen`) when the retail pause starts, with `gd.ui.unpause` asking retail's own unpause routine to run. Off by default (`MELEE_ATLAS_PAUSE=1`); offline only. Not Envoy's own START pause, which is a legacy-menu route. The retail element mask (`gd.ui.retail_hide`, `MELEE_ATLAS_RETAIL`) is the same capability's other half. | `gw_script_ui.inc`, `gmvs.c` |

### Scripting

| Term | Definition and boundary | Where |
|---|---|---|
| Checkpoint output journal | Recorded, validated Lua gameplay outputs replayed during simulation reconstruction. It does not replay the Lua VM itself. | `melee/pc/platform/gw_script_sim_state.inc` |
| Event | Observation of an occurrence with payload and timing; a hook delivers it to a subscriber. Different existing queues and phases are not yet one shared bus. | `docs/scripting.md` |
| Gameplay write | API operation that changes authoritative simulation, such as percent or hit rules. A shader parameter change is a presentation write. | `docs/scripting.md` |
| gd | Lua namespace exposing the port's scripting API; gd.kit exposes interface drawing helpers. It is not the modifier evaluator. | `docs/scripting.md` |
| Hook | Named callback entry point such as on_hit that receives an engine observation. Geno move-command hooks and state hooks are separate namespaces and must be qualified. | `docs/scripting.md` |
| Offline gate | Admission check restricting an operation to supported offline execution. An API being registered does not imply online-safe use. | `melee/pc/platform/gw_script.c` |
| Warmup | Prepare declared resources or pipelines before use through the warm APIs. It is cache preparation, not a gameplay status or a readiness guarantee for undeclared assets. | `melee/pc/platform/gw_script_warm.inc` |

### Game layer

| Term | Definition and boundary | Where |
|---|---|---|
| Bag | Persistent collection of rolled drives and equipment selections. It is not a list of currently active status stacks. | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua` |
| Budget | Bounded aggregate allowance for a modifier effect family. Renderer budgets and power budgets are separate constraints. | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua` |
| Depth | Progression index within a run loop; effective depth adds 13 times the loop count. It is not rendering depth or echo history depth. | `melee/pc/scripts/examples/envoy/scripts/mod_progression.lua` |
| Drive | Equipable loot object carrying a color implicit and rolled or fixed modifier records. Its physical pickup representation is not the equipped rule set. | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua` |
| Drive slot | Equipment position for a drive. It is not a controller port or fighter slot. | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua` |
| Effect family | Budget category aggregating related modifier outputs. Say move family for attack classification such as aerial or smash. | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua` |
| Implicit | Built-in color-associated contribution on a drive, separate from its affixes. It is not an unlisted accidental effect. | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua` |
| Keystone | Special modifier record kind with progression-limited capacity. It is distinct from a unique drive and a normal affix. | `melee/pc/scripts/examples/envoy/scripts/mod_schema.lua` |
| Loop | Completed-cycle count used with depth to continue progression. It is not a Lua iteration or the render loop. | `melee/pc/scripts/examples/envoy/scripts/mod_progression.lua` |
| Modifier | Authored rule or passive contribution evaluated and compiled into gameplay outputs. Use script mod for a package and fighter modifier for the native ratio API. | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua` |
| New Game+ | Continuation after run completion carrying designated saved progress into a new cycle. The older retail stat loop exists; shared rolled-build integration is not established. | `melee/pc/scripts/examples/envoy/scripts/classic.lua` |
| Prefix | Normal affix record placed in a drive's prefix category. It is not a generated C symbol prefix. | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua` |
| Rarity | Loot or record category governing composition, distinct from numerical strength tier. Record kinds and physical drive rarity are related but not interchangeable fields. | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua` |
| Suffix | Normal affix record placed in a drive's suffix category. It is not the second half of every modifier rule. | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua` |
| Tier | Numerical strength level used to resolve a record's values. It is not rarity, and repeated copies may retain separate tiers. | `melee/pc/scripts/examples/envoy/scripts/mod_schema.lua` |
| Unique | Authored special modifier/drive identity with fixed composition or color metadata. The word does not promise only one instance can exist. | `melee/pc/scripts/examples/envoy/scripts/mod_schema.lua` |

### Combat

| Term | Definition and boundary | Where |
|---|---|---|
| Armour | Target-side knockback or reaction protection; qualify the named type. Percent resistance and invincibility are different mechanics. Typed armour is in flight for integration and runtime acceptance. | `melee/pc/gameworld/script_fighter_caps_armor_core.h` |
| Condition | Predicate that must hold for a rule to execute after its trigger. A condition observes state; it does not cause an effect. | `melee/pc/scripts/examples/envoy/scripts/mod_schema.lua` |
| Conversion | Creation-phase replacement of an eligible hitbox's element, matching its original element. It is not fractional damage splitting or a named-status application. | `melee/pc/platform/gw_script_hit_rules.inc` |
| Damage-pool armour | Named damage_pool type consuming a finite damage allowance; equal or crossing damage breaks through unless another protection absorbs. It preserves percent damage and hitlag. In flight. | `melee/pc/gameworld/script_fighter_caps_armor_core.h` |
| Damage-threshold armour | Named damage_threshold type suppressing eligible ordinary reaction strictly below a per-hit damage threshold. It is not a cumulative damage pool. In flight. | `melee/pc/gameworld/script_fighter_caps_armor_core.h` |
| Directional armour filter | Front/back/any eligibility filter applied to an armour type. It is not a seventh armour type. In flight. | `melee/pc/gameworld/script_fighter_caps_armor_core.h` |
| Echo | Delayed gameplay replay of recorded hit capsules with separate collision memory and owner attribution. It is not a rendered afterimage or another live fighter. In flight. | `melee/pc/gameworld/script_echo.inc` |
| Effect | Requested gameplay output of a rule, such as a ratio, hit rule or status application. Say visual effect or FX package when rendering is meant. | `melee/pc/scripts/examples/envoy/scripts/mod_schema.lua` |
| Element | Hitbox damage-property classification such as normal, fire, electric, ice or darkness. A fire element does not automatically apply Burn; inspection names exceed legal conversion names. | `melee/pc/gameworld/script_hit_context.inc` |
| Hit rule | Native creation/contact policy modifying an eligible hit's properties, percent damage or launch. It is not every rule in the Lua modifier engine. | `melee/pc/platform/gw_script_hit_rules.inc` |
| Hit-count armour | Named hit_count type absorbing a finite count of eligible contacts; the final counted hit is absorbed and breaks the protection. It is not a rehit timer. In flight. | `melee/pc/gameworld/script_fighter_caps_armor_core.h` |
| Knockback armour | Named knockback type subtracting knockback before the retail floor; it does not promise no flinch. Retail knockback armour remains a separately qualified baseline mechanic. In flight. | `melee/pc/gameworld/script_fighter_caps_armor_core.h` |
| Knockback-threshold armour | Named knockback_threshold type suppressing eligible ordinary reaction strictly below resulting knockback. It is not subtractive knockback armour. In flight. | `melee/pc/gameworld/script_fighter_caps_armor_core.h` |
| Move tag | Attack or situation classification used by rules, such as aerial, projectile or airborne. It is not a player name tag; extension moves are not all classified today. | `melee/pc/gameworld/script_hit_context.inc` |
| Resistance | Reduction in percent damage or launch through ratios/rules. The current armoured loot label describes resistance rather than a named armour type. | `melee/pc/scripts/examples/envoy/scripts/mod_pool.lua` |
| Skill event | Observation of a successful gameplay technique used to earn temporary state. It must come from the actual decision/result, not a guessed button press; shared skill wiring remains in flight. | `docs/prompts/codex-echo-hitboxes-fix1.md` |
| Stack | Multiplicity or accumulated amount of a named status or modifier; qualify status stack versus modifier copies. It is not a C call stack. | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua` |
| Status | Named combat state with lifetime and optional stacks: burn, chill, curse, haste, guarded or momentum. Native presence bits and numeric timed channels are separate mechanisms; shock is not an implemented named timed status. | `melee/pc/scripts/examples/envoy/scripts/mod_schema.lua` |
| Super armour | Named super type suppressing eligible ordinary reaction while active. It does not remove percent damage or hitlag, or cover every throw/special reaction path. In flight. | `melee/pc/gameworld/script_fighter_caps_armor_core.h` |
| Trigger | Occurrence or schedule that initiates rule evaluation, such as a hit event or interval. Conditions further filter it. | `melee/pc/scripts/examples/envoy/scripts/mod_schema.lua` |

### Visuals

| Term | Definition and boundary | Where |
|---|---|---|
| Afterimage | Rendered historical fighter picture signaling an earned status while it lasts. It never supplies collision itself; this binding policy is not yet enforced across all current adapters. | `melee/pc/platform/gw_fx_motion.cpp` |
| Afterimage copy | One historical rendered sample with age, opacity and optional treatment. It is neither a fighter clone nor a gameplay echo. | `melee/pc/platform/gw_script_echo_visual.inc` |
| FX package | Authored visual-effect resources attached to a fighter/article or placed in the world. It is not a modifier effect descriptor. | `docs/shaders.md` |
| Post pass | Ordered shader applied to a world or final rendered image. It is outside the three entity/hit channels and is not a status store. | `melee/pc/platform/gw_script_shaders.inc` |
| Surface treatment | Appearance bound to equipped properties or current status on the entity itself. The current surface API binds per port; independent secondary-fighter binding is not established. | `melee/pc/platform/gw_script_surface.inc` |
| Three channels | Semantic visual contract: surface means equipped/status on you; afterimage means earned status while it lasts; tracer means this hit carries a property. The shared binding is proposed/in flight, not three authoritative gameplay stores. | `docs/superpowers/specs/2026-10-04-one-system-catalogue.md` |
| Tracer | Rendered ribbon signaling a property carried by a hit. Existing joint/item ribbon APIs do not automatically establish the hit-property binding. | `melee/pc/platform/gw_script_motion.inc` |

### Stages and persistence

| Term | Definition and boundary | Where |
|---|---|---|
| Chunk | Authored portion of physical level geometry or a level layout. It is not necessarily a separately loaded stage slot; qualify snapshot chunk for memory blocks. | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua` |
| Game state | Authoritative simulation data determining future gameplay. Renderer caches and a persistent save profile are different state domains. | `melee/pc/platform/gw_snap.c` |
| Lifecycle | Creation, retention, reset and teardown policy across spawn, respawn, switch and scene exit. A shared policy across all rule sources is proposed rather than complete. | `docs/superpowers/specs/2026-10-04-one-system-catalogue.md` |
| Mission | Scripted objective/wave/checkpoint runtime for authored levels. The campaign direction is parked; it is not the active LAB modifier host. | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua` |
| Save slot | Named storage position for a saved profile or LAB state; qualify the storage system. It is not a live fighter slot. | `melee/docs/geno.md` |
| Savestate | Captured simulation image used to restore a compatible execution point. It is not a fighter action state or ordinary progression save. | `melee/pc/platform/gw_snap.c` |
| Stage slot | Preloaded native stage resource position used by the stage-switch system. It is not a fighter/roster/equipment slot. | `melee/pc/platform/gw_script_stage_slots.inc` |
| Stage switch | Transition to another loaded stage with explicit carry and teardown. Retaining the same fighter does not guarantee every status or resource survives. | `melee/pc/platform/gw_script_stage_slots.inc` |
| Zone | Named spatial region with membership observations such as enter and exit. A zone is not collision geometry or automatically a modifier trigger. | `melee/pc/platform/gw_script_zones.inc` |

### People and process

| Term | Definition and boundary | Where |
|---|---|---|
| Codex packet | Scoped task document naming requirements, allowed files and acceptance/report obligations. A packet is not evidence that its implementation passed. | `docs/prompts/codex-parallel-rules.md` |
| Integrator | Role responsible for joining lanes, regenerating shared bundles and checking the assembled executable. It is a responsibility, not a particular person or model. | `docs/prompts/codex-parallel-rules.md` |
| Lane | Explicit file/task ownership boundary during concurrent work. Shared source must not be overwritten by another lane's broader rewrite. | `docs/prompts/codex-parallel-rules.md` |
| Owner | Person setting the project's gameplay direction and accepting its behavior. An agent's implementation claim does not replace owner acceptance. | `docs/prompts/codex-system-catalog.md` |
| Stamped build | Executable with recorded source/build provenance tied to a test result. A copied filename alone is not a reliable stamp. | `docs/HANDOFF.md` |
| Verified in game | Behavior observed in an identified executable/run with relevant acceptance evidence. Syntax checks, stubs and source reading must be described separately. | `docs/NEXT-SESSION.md` |
| Written | Present in source or documentation, without an implied build or gameplay test. Use built, source-checked and verified in game only for their corresponding evidence. | `docs/superpowers/specs/2026-10-04-one-system-catalogue.md` |

## Adding a term

Check this file and the source vocabulary before inventing a name. Give each unqualified word one meaning; use an explicit qualifier when an established word must serve another layer. Add or correct its entry in the same change, including its source and any proposed, in-flight or parked status. A near-duplicate is a terminology bug: reconcile it or document why the mechanics differ. Preserve API, save and content compatibility when a later code rename occurs.

## Proposed code renames, for a later change

These are migration proposals only. No code, identifier, schema or saved record is renamed by this document. Status aliases become a common predicate namespace only after a shared contract exists.

| Current name | Proposed name | Where | Reason / migration boundary |
|---|---|---|---|
| knockback_taken (modifier value key) | launch_taken | melee/pc/scripts/examples/envoy/scripts/mod_schema.lua; mod_budget.lua | Budget family already says launch_taken; rename only this value-key alias, not unrelated native knockback fields. |
| fighter_armor / on_armor / armor authoring field | fighter_armour_types / on_armour / armour | melee/pc/platform/gw_script_fighter_caps_armor.inc; gw_script.c; Geno authoring contract | British spelling in prose; explicit types name distinguishes the legacy fighter_armour API. Preserve compatibility aliases and serialized versioning. |
| armoured (resistance record label) | damage_resistant | melee/pc/scripts/examples/envoy/scripts/mod_pool.lua | Semantic correction: percent resistance is not reaction armour. Preserve persistent record IDs or migrate them explicitly. |
| fighter_status (native presence mask) | fighter_status_mask | melee/pc/platform/gw_script_hit_rules.inc; gw_script.c | Clarifies projection of named statuses versus the Lua lifetime/stack store. |
| fighter_timed_status (numeric channels) | fighter_timed_marker | melee/pc/platform/gw_script_fighter_caps.inc | Independent numeric marker is not a named combat status; do not merge mechanics merely by renaming. |
| burning / chilled / cursed / hasted tag aliases | status:burn / status:chill / status:curse / status:haste | melee/pc/scripts/examples/envoy/scripts/mod_schema.lua; mod_engine.lua | Proposed qualified predicate spelling resolves adjective/noun aliases; it is not accepted schema syntax today. |
