# One-system surfacing catalogue — 2026-10-04

```text
 SOURCES                     OBSERVATIONS                 EXECUTION
 drive / opponent roll ----+ retail collision -----------+ native hit rules
 fighter attach / define --+ Geno init/action/land/hit ---+ Geno commands/articles
 stage / item definition --+ zone/contact/item/1P --------+ Lua modifier evaluator
                           |                             |
                           +----- PROPOSED SPINE ---------+
                           | entity + source identity    |
                           | typed events + common tags  |
                           | status / stack authority    |
                           | effect descriptors/executors|
                           | checkpoint + lifecycle      |
                           +--------------+--------------+
                                          |
                           surface = equipment/status
                           afterimage = earned timed state
                           tracer = carried hit property
                                          |
                   LAB / Classic / Adventure / stage slots
                   share adapters; retain retail engines/renderer
```

Ten most valuable missing connections, in order:

1. LAB modifier rules → Classic/Adventure director, using the same pool.
2. Lua status instances → native hit predicates and timed channels, with one lifetime authority.
3. Geno fighter data → the existing rule/effect vocabulary, as character abilities without loot.
4. Geno/item/echo move identity → common hit tags, preserving original and effective elements.
5. Port/sub/serial/handle identities → one entity-and-source reference.
6. Capability/armour writes -> the checkpoint output executor, following the existing echo operation.
7. Existing zone/contact observations → modifier events; armour/skill observations when their packets finish.
8. Committed status/source/hit state → surface, earned-afterimage and tracer bindings.
9. Item/article/echo ownership → shared source attribution, including CPUs and KO credit.
10. Stage/respawn/NG+ boundaries → explicit retain/rebuild/expire policy.

## Evidence boundary

This dated catalogue supersedes undated inventory claims for the sources inspected here. It does not supersede gameplay acceptance reports. **Verified by reading** means a registration, producer, executor or lifecycle path was inspected. **Inferred** means a proposed adapter, expected composition or a negative finding within this scope. No build, game launch, commit, bundle regeneration or executable test was performed. Both trees were already dirty and parallel packets were changing source.

Status **played** requires named historical run evidence. **Built/unseen** below means an existing source implementation whose current executable/build provenance was not established; it does not assert that today's source was compiled. **In flight** covers current echo, armour and define packets, even where implementation files exist. **Parked** is the mission/campaign direction. **Missing** is an absent shared adapter. Snapshot **BSS/heap** means source places mutable state in snapshot-selected game regions, not a zero-difference replay proof. **Journal** means explicit Lua exports plus replayed outputs. **Presentation** means caches/derived state outside authoritative simulation.

The audit enumerates production script dispatch strings, exact gd registration tables, literal Script_GameEvent producer sites, finite Envoy/Geno vocabulary, native systems and run/world/LAB integration. Arbitrary user names, shader bodies, model labels, custom state names and mod IDs are open namespaces. Their possible values cannot be finitely enumerated. The appended inventories preserve actual exported words rather than treating every C identifier as a gameplay noun.

Snapshot region selection: `melee/pc/platform/gw_snap.c:210`. The Lua VM is not replayed; the output journal is separate: `melee/pc/platform/gw_script_sim_state.inc:1`.

## In-flight packets

| Packet | Observed source | Status and boundary |
|---|---|---|
| Echo EM5 + fix1 | `melee/pc/gameworld/script_echo_core.h:3`; `melee/pc/platform/gw_script_echo.inc:1`; `melee/pc/scripts/examples/envoy/scripts/mod_echo.lua:1` | In flight. 12 entities, 61 history records/entity, 8 rules/entity, four recorded hitboxes. Native capsule/history and Lua source adapters exist; shared includes/registration/journal/collision acceptance must be integrated. |
| Armour P2b | `melee/pc/gameworld/script_fighter_caps_effects.inc:22`; `melee/pc/platform/gw_script_fighter_caps.inc:96` | In flight. Both legacy `fighter_armour` and typed/windowed `fighter_armor` are now registered; on_armor dispatch exists. Geno/Envoy integration remains a report request and runtime acceptance is pending. |
| Geno define GF1 | `melee/pc/platform/geno_define_registry.inc:4`; `melee/pc/geno/geno.h:16` | In flight. v6 parser/dynamic profile work exists. Parser admits Mario/common v1/retail references only, and explicitly refuses articles, fx_bindings and special_attributes in this slice. No stock-match/mixed-match acceptance inferred. |

Packets read: `docs/prompts/codex-echo-hitboxes.md:1`, `docs/prompts/codex-echo-hitboxes-fix1.md:1`, `docs/prompts/codex-armour-types.md:1`, `docs/prompts/codex-geno-define-slice1.md:1`. Reports for these three active jobs were absent when initially searched; the closing inventory rechecks their presence. Prior capabilities, afterimages and roster reports were read as integration evidence, not current-game acceptance.

Latest owner direction supersedes the first echo brief: **no always-on afterimages; an afterimage is the sign of an earned expiring status**. The initial source allows echo records without a status gate and includes unconditional armed records. Fix1 remains in flight; do not claim the earned-state constraint is enforced end to end.

## 1. Parts list

The call-level appendix gives one row per registered capability. These tables describe the systems those calls expose.

### Observations and native gameplay

| Capability | What it is / source | Status | Deterministic / snapshot | Offline-only? |
|---|---|---|---|---|
| Retail fighter events | Action/hit/hitlag/land/KO/stock and successful action signals; `melee/pc/platform/gw_script.c:8306` | Built/unseen | Deterministic observations; host queue is not simulation authority | Observer admission follows script policy |
| Clank | Deduplicated pair, resolved rebound/hitlag snapshot; `melee/pc/platform/gw_script_clank.inc:10` | Built/unseen | Host observation of game outcome | Observer, no mutation |
| Zones | Named regions and enter/exit/none/some membership; `melee/pc/platform/gw_script_zones.inc:21` | Built/unseen | Game BSS; Lua dispatch suppressed in replay | Yes dispatch |
| Contacts/waits | Floor/wall/ceiling/ledge pictures, polling ring and wait predicates; `melee/pc/platform/gw_script_contacts.inc:1` | Built/unseen | Host diagnostic ring, not rewind authority | Read observations; mutation separately gated |
| Hit rules | 32 creation/contact rules/entity, status masks, incoming/outgoing percent and launch; `melee/pc/platform/gw_script_hit_rules.inc:2` | Built/unseen | Pure native evaluator, game BSS and journal | Gameplay gate |
| Fighter modifiers | 11 ratio overlays preserving retail baseline; `melee/pc/gameworld/script_fighter_mod.inc:4` | Built/unseen | Six port roots in BSS; journal replay | Yes |
| Fighter capabilities | Air-jump count and shield/dodge/run/grab/special restrictions; `melee/pc/gameworld/script_fighter_caps_movement.inc:2` | Built/unseen | Independent 12 entity BSS overlays; absent from current capability journal | Yes writes |
| Protection/size | Timed intangible/invincible/metal/size; `melee/pc/gameworld/script_fighter_caps_effects.inc:17` | Built/unseen | BSS/retail heap; overlap ownership incomplete | Yes |
| Baseline threshold armour | Strict-below selected-hit damage or computed KB suppresses ordinary flinch; `melee/pc/gameworld/script_fighter_caps_effects.inc:28` | Built/unseen | BSS, no journal operation | Yes |
| Armour type extension | Subtractive/threshold/super/count/pool/directional/window/break observer; `docs/prompts/codex-armour-types.md:1` | In flight | Requested exactness, not yet proven | Requested offline effect |
| Timed numeric channels | Four expiring numbers/entity, no automatic Shock effect; `melee/pc/gameworld/script_fighter_caps_target.inc:52` | Built/unseen | Game BSS, no journal operation | Yes writes |
| Opponent targeting | Nearest/radius candidates, stable ties and exclusion; `melee/pc/gameworld/script_fighter_caps_target.inc:33` | Built/unseen | Read game entities | Read-only |
| Held-item grant | Safe portable retail kinds; refuses unsafe states/hands/data; `melee/pc/gameworld/script_fighter_caps_effects.inc:210` | Built/unseen | Retail RNG/heap, no grant journal | Yes |
| Gameplay history/echo | Delayed world capsules with owner and separate hit memory; `melee/pc/gameworld/script_echo.inc:152` | In flight | Game BSS intention; live exactness pending | Gameplay gate intended |

### Presentation

| Capability | What it is / source | Status | Deterministic / snapshot | Offline-only? |
|---|---|---|---|---|
| Surface shaders | One program per port/stage, 16 params; `melee/pc/platform/gw_script_surface.inc:5` | Built/unseen | Presentation selection, rebind from state | Visual API |
| Afterimages | Captured skinned draws outside MEM1; `melee/pc/platform/gw_fx_motion.cpp:1` | Built/unseen | Restore clears/refills history, never gameplay | Visual API |
| Tracers | Joint/hitbox/item/held-item ribbons; `melee/pc/platform/gw_script_motion.inc:45` | Built/unseen | Presentation history | Visual API |
| Post passes | Ordered world/final shaders with optional duration/progress; `melee/pc/platform/gw_script_shaders.inc:112` | Built/unseen | Presentation timers/cache | Visual API |
| Lights | Script lighting parameters; `melee/pc/platform/gw_script_shaders.inc:191` | Built/unseen | Output, not status authority | Visual API |
| FX | Fighter/article/world packages and attachment/control; gd registration appendix | Played historical Sora; current source unseen | Gameplay article state separate from emitter/render state | Caller policy |
| Sound | Existing sound-ID playback; gd registration appendix | Built/unseen | Output, avoid duplicate replay sound | Caller policy |
| Warmup | Declared resource/pipeline traversal and readiness; gd registration appendix | Built/unseen | Cache work; can branch LAB history | Offline traversal policy |

### Lua rules and loot

| Capability | What it is / source | Status | Deterministic / snapshot | Offline-only? |
|---|---|---|---|---|
| Modifier evaluator | Sorted rules, bounded chain queue, statuses/stacks/origin; `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:1` | Built/unseen | Frame order + export/import | LAB adapter yes |
| Schema | Tags/triggers/conditions/effects/visual validation; `melee/pc/scripts/examples/envoy/scripts/mod_schema.lua:5` | Built/unseen; echo edits in flight | Immutable definitions | Adapter yes |
| Pool/budget | Authored records, additive families and numeric safety; `melee/pc/scripts/examples/envoy/scripts/mod_pool.lua:11`; `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:4` | Built/unseen; echo family in flight | Pure derivation | Yes |
| Progression | Effective depth = depth + 13*loop, growing tiers/slots; `melee/pc/scripts/examples/envoy/scripts/mod_progression.lua:14` | Built/unseen | Explicit checkpointed context | Yes |
| Drive loot/bag | Colour implicit, affixes/rarity, bag/equipment build; drive_loot/drive_bag source inventories below | Built/unseen | Seeded rolls and serialized roots | Yes |
| Physical drops | Native payload points into Lua rolled ledger; `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:18` | Built/unseen | Item heap plus Lua checkpoint | Yes |
| Same-pool CPUs | Independent seeded foe build and LAB nameplate; foe_roll/foe_lab source inventories below | Built/unseen | Checkpointed adapter roots, primary ports | Yes LAB |
| Visual adapter | Status/equipment params and chain pulse; `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:75` | Built/unseen | Lua metadata checkpoint; renderer derived | Yes adapter |

### Geno engine

| Capability | What it is / source | Status | Deterministic / snapshot | Offline-only? |
|---|---|---|---|---|
| Attach profiles | Attributes/hooks/overlays added to retail/m-ex fighter; `melee/pc/platform/geno_registry.c:1157` | Played historical Sora; current source unseen | GenoState/game heap + immutable profile identity | Existing simulation path; no define online promise |
| State graph | 48 named states, anim/iasa/phys/coll callbacks; `melee/pc/geno/geno.h:266` | Built/unseen | Game state, move vars | Existing simulation path |
| Move scripts | Escape opcode 59, vars/conditions/change checks; `melee/pc/geno/geno.h:38` | Built/unseen | Game BSS/heap and game RNG | Existing simulation path |
| Hit flags/writes | HBDMG/HBSTUN/HBFLAGS/rehit/autolink; `melee/pc/geno/geno.h:68` | Built/unseen | Hit-side game fields | Existing simulation path |
| Articles | 16 projectiles/profile, homing/children/hitboxes/FX; `melee/pc/geno/geno_game_articles.inc:1` | Played historical Firaga; current source unseen | Native Item heap; renderer separate | Existing simulation path |
| Standalone items | Native definitions/behaviour/pickup/expiry; `melee/pc/geno/geno_game_items.inc:1` | Built/unseen | Game heap/BSS, immutable registry | Script spawn offline |
| Define GF1 | Native Mario donor/common behaviour references; `melee/pc/platform/geno_define_registry.inc:4` | In flight | Boot-stable aliases, dynamic game profile allocations | Offline pending full admission |

### Run, world, roster and LAB

| Capability | What it is / source | Status | Deterministic / snapshot | Offline-only? |
|---|---|---|---|---|
| 1P hooks/hold | Classic/Adventure lifecycle and bounded barrier; `melee/pc/platform/gw_script_1p.inc:54` | Built/unseen | Host run/barrier state is not a generic game checkpoint | Yes |
| Retail Envoy/NG+ | Companion-stat templates/reward/evolution/save loop; `melee/pc/scripts/examples/envoy/scripts/classic.lua:77` | Built/unseen | Saved profile; separate Lua director state | Yes |
| Mission/campaign | Waves/checkpoints/objectives/triggers; `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:1` | Parked | Own Lua runtime, no shared modifier checkpoint | Yes |
| Stage slots/switch | Preload/queue/switch with carry/teardown; `melee/pc/platform/gw_script_stage_slots.inc:253` | Built/unseen | Game data + host epoch; incompatible saves refused | Yes |
| Stage geometry | Lines/platforms/models/spawns/bounds/collision groups; gd appendix | Built/unseen; older editor played evidence | Mixed game geometry/host assets | Yes mutation |
| Six slots/bench | Six primaries, secondary objects and bench/call; gd appendix | Built/unseen | Retail/game overlays | Yes writes |
| Roster registry | Wide stable catalogue, bounded resident aliases; `melee/pc/platform/gw_roster_catalog.h:1` | Built/unseen; define adapter in flight | Host immutable identity; admission integration incomplete | Wide/define online pending |
| LAB saves/rewind | Snapshot memory, pad replay, explicit Lua output journal; `melee/pc/platform/gw_script_sim_state.inc:1` | Built/unseen | Lua VM never replayed | Offline LAB |
| LAB drills/debug | Timeline/motion/CPU/input/hitbox/KB tools; gd appendix | Built/unseen | Per-tool state, not a run ledger | Writes gated |
| Shared spine | Common source/status/effect/event/visual contract | Missing | Proposal only | Preserve current offline admission |

Historical played evidence: named Sora `sora-fx-cap2` and `sora-showcase` runs in `docs/NEXT-SESSION.md` (“RESOLVED” and showcase paragraphs). This establishes the earlier installed attach/article/FX path, not today's packets or current bundle. No unrelated source/stub result was promoted to played-build status.

## 2. Vocabulary: semantic facts before the exhaustive ledger

The appended finite-vocabulary tables retain every exported Envoy set, Geno command/value/condition/hook/behaviour/flag/article field and schema enum. Each entry identifies producer, consumer and boundary. Counts deduplicate spelling, not semantics.

Verified by reading:

- Move tags: jab, tilt, smash, aerial, special, grab, throw, projectile, dash_attack; unknown/any are real sentinels. `grounded`/`airborne` are hit-time situation tags. `script_hit_family_move` deliberately returns unknown for Geno or unsupported extension states (`melee/pc/gameworld/script_hit_context.inc:19`). Ordinary item context is move 0, not reliably projectile (`:32`). A fighter's current action is not an article's move identity.
- Ordinary rule elements: normal/fire/electric/ice/darkness. Retail hitbox inspection exposes more element names; those are not all legal conversions. Creation matches **original** element, contact rules operate in their own phase. Split/fractional conversion is rejected by native rule parser.
- Named statuses: burn/chill/curse/haste/guarded/momentum. Adjective tags burning/chilled/cursed/hasted are aliases, not separate stores. Native bits mirror only presence. `shock` is a look and `shocked` an accepted tag, but Shock is not an accepted timed Lua status; bit 2 is skipped (`melee/pc/scripts/examples/envoy/scripts/mod_schema.lua:7`–`:9`). Electric damage, Shock gameplay and electric tracer style are distinct concepts.
- `status_applied`, `status_removed`, `stacks_changed`, `interval` are Lua-produced events. They have no native/Geno subscriber. `equip` is mostly passive compilation, not an automatically emitted event. `stage_start` is admitted by schema but the current retail hook wiring does not deliver it to the modifier evaluator.
- `damage`, `healing`, `unique`, `keystone` are accepted tags/labels. Direct percent damage/heal does not automatically emit a tagged attack or heal event. Burn damage is not a physical hit and must not inherit hitlag by naming convention.
- Native `fighter_status` bitmask, Lua named statuses and four `fighter_timed_status` numeric channels are independent mechanisms. The latter is a marker, not automatic next-hit Shock stun (`melee/pc/gameworld/script_fighter_caps_target.inc:52`).
- `knockback_taken` maps to budget `launch_taken`; creation damage, contact percent_damage, final launch and direct percent writes are distinct phases. `armoured` pool modifier reduces percent; Guarded reduces percent/launch; retail armour subtracts KB; threshold armour suppresses ordinary reaction. Geno FLINCHLESS is hit-side; armour is target-side.
- Schema admits shield_max/fall_speed/weight/shield_regen, while budget families omit those keys. Several creation change fields are likewise schema-valid but budget-refused (`melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:6`, `:29`). Schema validity alone is not executability.
- Specific aerial selectors nair/fair/bair/uair/dair exist in echo wrapper; general modifier tags only say aerial, and the inspected Lua echo move set includes nair but not the other four (`melee/pc/platform/gw_script_echo.inc:21`; `melee/pc/scripts/examples/envoy/scripts/mod_echo.lua:3`).
- Three channels are a semantic policy, not current renderer types: surface = equipped/status; afterimage = earned expiring status; tracer = carried hit property. Native renderer options remain free-standing (always/moving/flag; solid/glow/fire/electric/frost/dark). The shared binding is missing.
- `on_hit` is ambiguous across namespaces: Geno is hit **taken before damage reaction**, Lua script is a post-frame collision observation. `on_land`, modifier landing, contact floor enter and zone enter occur near each other but are not equivalent.
- `on_boss_defeated` and `on_1p_boss_defeated` can describe the same defeat in different envelopes. Stock-lost hook plus falls/stocks polling already requires deduplication. `on_action_signal` is an internal stage queue signal; Lua dispatch chooses a concrete jump/grab/etc hook.
- Entity kinds are not interchangeable IDs: fighter/sub-fighter are physical participants; CPU opponent is a controller/team role; projectile is an attack role; Geno article is usually a native Item; echo is a capsule extension; stage object and zone are world entities. Capabilities use 1..6/7..12, hit rules use port+sub, echo/zone internals interleave primary/sub, loot uses six port roots, items use serials.
- Native drive payload has colour/amount, not a complete rolled build. Native item colour set has five names and no purple (`melee/pc/platform/gw_script_items.inc:29`); Lua purple loot uses ledger/visual mapping. Do not unify this by silently interpreting amount as damage or rules.

## 3. Connection matrix

The generated pair matrix below inventories every pair among renderer, modifiers, native hit rules, fighter ratios, capabilities/armour, Geno, items, echoes, zones/contacts, 1P, stage/world, roster/slots and LAB. **C** is existing transport; **A** is a proposed adapter using existing primitives (inference); **S** means keep execution/storage separate while optionally sharing descriptors. A connected pair is not a claim of complete interoperability or acceptance.

### Directional reach and persistence

Y = existing source connection; A = missing adapter; F = in flight; — = inapplicable. Geno means the fighter's own data, not a Lua mod externally controlling it.

| System | Modifier trigger / cause | Geno own data trigger / cause | CPU / item / article / echo | Three-channel visual | Stage / respawn / rewind / NG+ |
|---|---|---|---|---|---|
| Hit rules | Y hit tags; Y conversion/percent/launch | A declare shared rule; Y own hitbox commands | CPU Y; owned item Y with ordinary-element restrictions; echo F | Surface Y through Lua, semantic tracer A | Same live fighter likely retained; Lua clears statuses/rederives build on stock; BSS+journal; retail run reinstall A |
| Fighter ratios | Read indirect; Y budget-mapped values | Y base attrs, A shared temporary source | CPU Y; not item attributes | Surface Y | Live carry then scene release; build reapply; journal; old stat NG+ Y/new pool A |
| Capabilities/protection | A triggers/effect schema/budget/journal | A generic setter hooks | 12 fighter entities Y; items can affect but do not carry fighter restrictions | Retail metal/size Y; shared binding A | Live bindings; respawn attribution varies; BSS captured but Lua write replay A; template extension A |
| Armour | on_armor F; modifier effect A | Geno integration F/deferred | CPU baseline Y; armour belongs to target, not attacking item | Guarded flash A | Named-type/window lifecycle F; baseline BSS; journal and NG+ A |
| Echoes | F hit path/echo effect | A character rule source | 12 entities intended; chosen carrier is capsule extension | Age alignment/armed flash F | History reset/carry policy F; snapshot exactness F; run adapter A |
| Zones/contacts | A schema route; APIs already exist | A membership condition/event | Zones primary/sub Y; contacts primary-only; item/article/echo membership A | Debug overlay Y, common status binding A | Zone exits/release at switch; membership recompute; zone BSS/contact host ring; NG+ reinstall A |
| Items/drives | Y collection/expiry; drive adapter Y/generic spawn effect A | Article spawn Y/standalone rule source A | CPU collects Y; loot bag adapter primarily P1; item payload only colour/amount | Pickup FX Y, semantic hit tracer A | Scene teardown/ledger policy; item heap+Lua export, arbitrary spawn replay A; old Classic drops Y/new rolled bag A |
| Geno move/state/article | Hit taken/dealt observed; custom state tags A; modifier article/state effect A | Y graph/scripts/hooks/articles/FX | CPU normal fighter path Y; own articles Y; echo source A | fx_bindings Y, common channel binding A | Live state carry; INIT resets on spawn; game heap/BSS with immutable profile identity; run source reinstall A |
| Surface/post/light/FX | Appearance is not trigger; surface/post output Y, generic light/FX effect A | FX Y/shared status binding A | Per-port CPUs Y; independent sub surface A; article/world FX Y | Surface Y; earned/tracer policy A/F | Scene release/rebind; derived on restore; no gameplay state; NG+ rebuild |
| Classic/Adventure | stage_start modifier mapping A; no mod-engine run-control effect | Character should not own run director | Old stat CPU templates and drops Y | Old tint/HUD Y | Host barrier/profile separate from simulation journal; saved stats/evolution NG+ Y/rolled build A |
| Mission/stage slots | A stage/zone bridge; external stage APIs Y | No need for character stage director | Retail fighters/items native lifetimes | World shaders Y | Own carry/teardown; spawn policy; epoch compatibility; mission parked |
| LAB/roster | Debug commands/observations Y | Define identity F | Six slots Y; inspect articles/items; echoes F | Debug Y | Snapshot compatibility refuses identity/epoch mismatch; LAB is not run save ledger |

Lifecycle evidence: `melee/pc/gameworld/script_game.c:211`–`:217` releases scene roots; `melee/pc/platform/gw_script_stage_slots.inc:255` releases zones on switch; `mod_engine.lua` stock-lost branch and `mod_lab.lua` observed-life resets clear transients; `melee/pc/platform/gw_fx_motion.cpp:1` clears/refills presentation on restore. Stage-slot epoch rejection is in gw_script.c load/rewind paths. NG+ profile carry is `classic.lua` completion/save path. Retention of overlays on the same live fighter is an inference, not a tested universal guarantee.

## 4. Ranked seams

1. **Main run does not run the new rules.** Verified: `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:16` requires LAB and active offline match; source main constructs it with active retail/run/mission blocked. `melee/pc/scripts/examples/envoy/scripts/classic.lua:92` installs companion-stat templates. New rolled loot/foe engine is a LAB island. Inferred fix: one run host adapter unlocks existing player/CPU/loot/NG+ combinations.
2. **Three status authorities.** Verified: `melee/pc/scripts/examples/envoy/scripts/mod_schema.lua:7`–`:9` named statuses/mirror bits, `melee/pc/gameworld/script_fighter_caps_target.inc:52` numeric channels. Names/stacks/origin/expiry are absent from bitmask. Inferred fix: derive masks/looks/native predicates from one committed semantic store.
3. **Geno abilities cannot use loot language.** Verified: Geno hook table has init/frame/action/land/hit and native calls, no shared rule/status source API (`melee/pc/geno/geno.h:218`, `:235`). Loot cannot cause arbitrary Geno state/article commands either. Inferred fix: character data becomes another rule source; keep move executor native.
4. **Tags incomplete at collision.** Verified: `melee/pc/gameworld/script_hit_context.inc:19` excludes Geno/nonretail special families; item path selects move 0. Inferred fix: source descriptors carry declared move tags, original/effective elements, not guessed owner action.
5. **Entity/source identity mismatch.** Verified: `melee/pc/platform/gw_script_fighter_caps.inc:17`, `gw_script_hit_rules.inc` sub selector, `melee/pc/gameworld/script_echo_core.h:3`, Lua six-port roots. Inferred fix: normalize refs with generation; separate owner/controller/source from entity kind.
6. **New setters lack replay transaction.** Verified: `melee/pc/platform/gw_script_sim_state.inc:146` operation parser now admits fighter_mod/damage/hit_rules/echoes, while capabilities/typed armour still lack operations. BSS coverage does not replay later Lua setters from a keyframe. Inferred fix: admit existing new effects only after journal/replay parity.
7. **Visual semantics partially shared.** Verified: mod_display packs looks in one surface program; motion options are independent; surface binds port (`melee/pc/platform/gw_script_surface.inc:74`). Inferred fix: state/source/hit binding, entity-aware sub selection, presentation remains separate.
8. **Loaded bundle behind source.** Verified: generated main.lua embeds earlier adapter/pool and lacks newer echo module wiring; editable mod_lab source has echo integration. Inferred fix: integrator regenerates after shared includes/registration/journal are complete. This audit does not regenerate.
9. **Queues/phases/clocks differ.** Verified: GsEvent frame-post batch, Lua chain queue, zone batch, contact ring, stage signals, Geno pre-reaction hook, 1P flags, presentation ticks. Inferred fix: shared typed envelope/order contract, not a Lua callback inside collision.
10. **CPU parity stops at port roots.** Verified: mod_lab action ignores sub; 1P template refuses sub (`melee/pc/gameworld/script_1p.inc:44`). Capabilities independently support 12 entities. Inferred fix: evaluator keyed by entity/role; stage replacement installs before first logic frame.
11. **Schema is broader than budget/executor.** Verified: mod_schema accepts value/change fields budget rejects (`melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:6`, `:29`). Inferred fix: one registry provides schema, bounds/family and executor metadata.
12. **Spawning does not imply carrying rules.** Verified: article.spawn, item_spawn, give_item, spawn_enemy, model_spawn, spawn_1p and echo capsule paths have different semantics. Inferred fix: common source/descriptor attribution; retain appropriate native allocators/collision paths.
13. **Persistence is accidental.** Verified: same-fighter carry, zone teardown, scene root clear, epoch refusal and old stat NG+ are distinct policies. Inferred fix: explicit persistent build/transient combat/scene resource classifications.
14. **Armour names blur mechanics.** Verified: percent resistance in armoured/Guarded, retail subtractive KB, ordinary threshold no-flinch, hit-side Geno FLINCHLESS. Inferred fix: honest distinct effect types and visuals; do not market resistance as super armour.
15. **Wide/native identity is not full online admission.** Verified: roster report lists snapshot/wire/replay/record integration requests; define parser uses boot-stable aliases (`melee/pc/platform/geno_define_registry.inc:41`). Inferred fix: immutable source identity and offline admission until full contracts pass.
16. **Earned afterimages not yet enforced.** Verified: `mod_schema.lua` allows omitted echo status, `melee/pc/scripts/examples/envoy/scripts/mod_echo.lua:43` initial records can be ungated; fix1 demands retail skill decisions. Inferred fix: integrate this packet's actual producer/dispatcher/status lifetime, not input guesses.
17. **Direct percent damage is not a hit.** Verified: mod_engine sustain damage aggregates percent deltas, no normal collision/hitlag/automatic hit event. Inferred fix: distinct direct-damage/heal descriptors with provenance; do not manufacture attacks.
18. **Power and rendering budgets are independent.** Verified: mod_budget echo family cap vs `melee/pc/platform/gw_fx_motion.cpp:39` renderer limits. Inferred fix: retain independent renderer budget; derive looks/counts without changing simulation.

## 5. Smallest spine: dependency order

S1 follow-up (2026-10-04) supersedes the original identity/bundle gap for the
following source changes only. Historical inventories and fingerprints below
remain the audit's closing capture, not the current EXE.

| Step | Current status | Evidence / remaining acceptance |
|---|---|---|
| 1 | Source implemented and reviewed: scalar entity/source refs, compatibility adapters, queued event envelope foundation, LAB binding checks | Production standalone identity/codec/adapter/event fixtures pass; 516-byte reference-state replay has zero differences. PPC/native syntax and369 Lua tests pass. Real EXE queue/rewind and owner acceptance pending. Sources are caller-authored provenance; loader wiring remains step6. |
| 2 | Built, suite 286/286 (2026-10-04, Claude): `sim_commit` journal admits `fighter_caps`, `fighter_effect`, `fighter_armour`, `fighter_armor`, `timed_status` (same bounds as the `gd.*` setters, replay calls the same native setters); `mod_registry.lua` is the one effect/operation descriptor list schema and budget read; journal commits allocate only their ops (the old full array exhausted the 128 MB budget after ~30 s) | Headless test: parse/refusal per op and movement replay zero-difference. Effect, armour and timer replay equality needs a live fighter: not yet checked in a LAB rewind. |
| 3 | Built (Lua, suite unaffected): `mod_status.lua` is the single status declaration (bits, tags, budget, fighter values, order); schema, engine, synergy, display and budget read it; the `armoured` loot is labelled `Damage resistant` (id kept: persisted) | All existing Envoy Lua tests pass unchanged; `envoy_status.lua` pins the old numbers. Native numeric timed channels stay private. |
| 4 | Partly built: item/article hits declare move tag `projectile`; original and effective element both reach `on_hit` (`original_element_tag`, `element_converted`); zone (`world`) and 1P (`run`) signals join the `on_event` envelope | Declared move tags for Geno-fighter and m-ex-fighter moves are NOT done (no declaration source exists in their data); armour/skill producers and the contact ring are not in the envelope. |
| 5 | Built and driven in the game (sandbox, vanilla disc): `envoy rules on` then `envoy classic` installs the pool, bag, slots, opponent rolls and looks through the same host as the LAB (`run_host.lua`); the old companion-stat route is the default | Verified: starter drive equipped, opponent rolled with nameplate and fighter mod applied, stage clear -> reward drive -> stage 1 (depth 1) with three more rolls, game over and `envoy stop` clear the bag. Not verified: visual looks, the owner's own play, NG+, Adventure, bosses. |

Codex stopped after step 1; Claude continued with steps 2 to 5 (see `_build/audit-20261003/spine/PROGRESS.md`).
Envoy bundle regeneration is the final source operation of the pass. Report:
`_build/tmp/codex-spine-steps-1-5-report.md`; scoped review:
`_build/tmp/spine-step1-review.md`. No held technique/crit feature was built.


Keep retail collision/physics, Geno move/state executor, Item allocation, stage teardown and renderer. Unify their **contracts**. These steps only join existing capabilities; in-flight armour/skill/define work is not a new feature smuggled into this proposal.

| Order | Small change | Existing systems change | Playable boundary and evidence required |
|---|---|---|---|
| 1 | Scalar/versioned entity and source refs; frame/sequence/phase/cause in event envelope | Normalize capabilities, hit rules, echo/zone, Lua port roots and item serials; roster/Geno provide immutable keys | Compatibility adapters preserve old APIs. Stale-generation refs refuse; primary/Nana/item/transform identity fixtures agree. |
| 2 | One descriptor registry and validated aggregate replay executor for existing effects | Schema/budget/compiler share fields/phase/bounds; extend sim_commit for implemented capabilities/timers/echoes after integration; stable handles recorded before replay | Old operations remain accepted. Snapshot+replay zero-diff for each new admitted operation before rules use it. Never rerun Lua during pad resimulation. |
| 3 | One named status/stack authority | Start with current Lua semantics/export as authority, derive hit masks/native expiry predicates/looks. Numeric channels remain private until explicitly mapped | Existing Burn/Chill/Curse/Haste/Guarded/Momentum results unchanged. Verify refresh/extend/expire/stock reset and CPU/sub parity; no new Shock feature promised. |
| 4 | Complete tagged adapters for existing observations | Preserve Geno pre-reaction vs script post-frame phases. Normalize action/clank/item/zone/contact/1P; declared move/article tags and cause IDs | Old hook listeners receive old signatures. One canonical moment, exact original/effective tags, no replay callbacks. Armour/skill enters only once producer/dispatcher are ready. |
| 5 | Reusable rule host outside LAB-only guard | Extract mod_lab host; LAB stays debug adapter. Classic/Adventure installs same pool/foe rolls/bag at existing lifecycle boundaries | Gate adapter while old stat route remains playable. Same build gives same outputs in LAB and one retail stage; no campaign redesign. |
| 6 | Geno character definition becomes another source | Loader validates immutable existing-rule records; init/action publishes facts; attribute baseline combines with temporary output. Native commands remain native | Character-origin and loot-origin copies of an existing rule behave alike. No-rule retail/m-ex/attach baseline unchanged; define remains offline. |
| 7 | Derive surface/earned-afterimage/tracer bindings from committed state | mod_display uses binding registry; echo and picture share ages; tracer uses effective hit properties; post/light/FX/sound remain optional outputs | Renderer never writes gameplay. Restore rebuilds; no status = no afterimage; expiry/KO cleanup, armed alignment and prepared shaders verified. |
| 8 | Shared boundary retention/teardown contract | Persistent build/bag/run source vs transient statuses/history/target memory vs scene resources. Stage and 1P retain their own machines | Switch→respawn→rewind→NG+ has no orphan/stale/duplicate drop/RNG drift; incompatible identity/epoch refuses before partial restore. |

Steps 1–5 unlock the broadest combinations: honest identity, executable/checkpointed effects, common statuses, tagged observations, then main-run use. Do not postpone replay until the end. “Could connect cheaply” means an existing producer/executor is available for an adapter, not that ordering/ownership/snapshot work is free.

## 6. Source appendices

The following mechanically enumerated tables provide exact hooks/payloads, producers, registrations, finite vocabulary and pair mechanisms. Source fingerprints are read-time evidence, not executable provenance. No disc assets or private machine/disc paths are included.

### 6A. Closing capture and parallel integration changes

During this audit the parallel jobs registered fighter_history/depth, echo_add/remove/echoes, echo_afterimage, afterimage copy queries/updates, fighter_armor and on_armor. The sim journal now admits an echoes operation and stable-handle preparation. Named armour source also replaced the earlier threshold-only implementation. These are VERIFIED SOURCE connections, still IN FLIGHT for runtime/build acceptance. For echo/armour, interpret the earlier status tables as in-flight runtime evidence, with these newly observed source connections; the generic capability/armour journal and Geno/Lua status adapters remain missing. No technique-event acceptance or bundle regeneration is inferred. on_floor is a player field, not a callback.

### 6B. Complete hook / internal signal inventory

| Hook/signal | Payload / phase | Evidence |
|---|---|---|
| on_action_change | (port,old,new,sub) | `melee/pc/platform/gw_script.c:7225`, `melee/pc/platform/gw_script.c:8323` |
| on_action_signal | Internal stage queue signal; Lua event16 maps to concrete action hook | `melee/pc/platform/gw_script.c:8326` |
| on_air_jump | (port,motion,sub); action decision / shield collision | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8339` |
| on_all_targets_broken | () | `melee/pc/platform/gw_script.c:8324` |
| on_armor | {port,entity,subfighter,type,absorbed,broke,damage,knockback}; queued observer, native reaction synchronous | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8326` |
| on_boss_defeated | {kind,port,x,y} | `melee/pc/platform/gw_script.c:7256`, `melee/pc/platform/gw_script.c:8325` |
| on_camera_complete | (job result integer) | `melee/pc/platform/gw_script.c:8570`, `melee/pc/platform/gw_script.c:8572` |
| on_clank | {port_a,port_b?,item?,item_kind?,x/y/z,damage_a/b,cancel_a/b,rebound_a/b,rebound,hitlag_a/b} | `melee/pc/platform/gw_script.c:7245`, `melee/pc/platform/gw_script.c:8325` |
| on_deadline | (name,frames_waited); host diagnostics not rewound | `melee/pc/platform/gw_script_deadline.inc:65`, `melee/pc/platform/gw_script_deadline.inc:67` |
| on_draw | () render completion | `melee/pc/platform/gw_script.c:7329` |
| on_enemy_defeated | {kind,handle,reason=defeated} | `melee/pc/platform/gw_script.c:8325` |
| on_enemy_hit | {handle,from,damage,reaction=false} | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8325` |
| on_enemy_removed | {kind,handle,reason=explicit_remove/item_destroyed} | `melee/pc/platform/gw_script.c:8325` |
| on_frame | () after logic/events, checkpoint boundary | `melee/pc/platform/gw_script.c:8584` |
| on_frame_pre | () before logic | `melee/pc/platform/gw_script.c:8134` |
| on_grab | (port,motion,sub); action decision / shield collision | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8339` |
| on_hit | (attacker or nil,victim,info): dealt,hitbox?,context_valid,hit_rule_ids/owners,move_tag,element_tag,element,attacker_action,attacker/victim_grounded,attacker/victim_damage,item,source_enemy?,reaction,attacker_sub,victim_sub; optional group,bone,damage,angle,kbg,bkb,wbk,element_name,shield_damage,radius,x/y/z,px/py/pz,hit_air/ground | `melee/pc/platform/gw_script.c:7225`, `melee/pc/platform/gw_script.c:8323` |
| on_hitlag | (port,entering,sub) | `melee/pc/platform/gw_script.c:7225`, `melee/pc/platform/gw_script.c:8323` |
| on_hot_reload | (ok) | `melee/pc/platform/gw_script.c:7895`, `melee/pc/platform/gw_script.c:7930` |
| on_item_collect | {item,kind,layer,reason,name,port?,x,y,payload?={colour,amount}} | `melee/pc/platform/gw_script.c:7241`, `melee/pc/platform/gw_script.c:8326` |
| on_item_expire | same item envelope; expired/destroyed, optional collector | `melee/pc/platform/gw_script.c:7242`, `melee/pc/platform/gw_script.c:8326` |
| on_jump | (port,motion,sub); action decision / shield collision | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8339` |
| on_ko | (attacker or nil,victim) | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8326` |
| on_land | (port,motion,sub) | `melee/pc/platform/gw_script.c:7225`, `melee/pc/platform/gw_script.c:8323` |
| on_launch | {mission,seed,size,mod,pending} | `melee/pc/platform/gw_script_launch.inc:87`, `melee/pc/platform/gw_script_launch.inc:89` |
| on_ledge_grab | (port,motion,sub); action decision / shield collision | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8339` |
| on_loadstate | (slot):0 history,1..8 slots,9 library | `melee/pc/platform/gw_script.c:8015`, `melee/pc/platform/gw_script.c:8057` |
| on_match_end | () | `melee/pc/platform/gw_script.c:7186` |
| on_match_start | () | `melee/pc/platform/gw_script_1p.inc:133`, `melee/pc/platform/gw_script_launch.inc:71` |
| on_perfect_shield | (port,motion,sub); action decision / shield collision | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8339` |
| on_savestate | (slot) | `melee/pc/platform/gw_script.c:7997` |
| on_scene | (major,minor[,serial]); catchup 2 args, scene change 3 | `melee/pc/platform/gw_script.c:7213`, `melee/pc/platform/gw_script.c:7217` |
| on_shield_hit | (port,motion,sub); action decision / shield collision | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8339` |
| on_stage_switch | {phase=before/after,from,slot} | `melee/pc/platform/gw_script_stage_slots.inc:257`, `melee/pc/platform/gw_script_stage_slots.inc:259` |
| on_stock_lost | (port,stocks) | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8326` |
| on_target_broken | (handle,remaining) | `melee/pc/platform/gw_script.c:8324` |
| on_taunt | (port,motion,sub); action decision / shield collision | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8339` |
| on_throw | (port,motion,sub); action decision / shield collision | `melee/pc/platform/gw_script.c:7226`, `melee/pc/platform/gw_script.c:8339` |
| on_tick | () presentation/host tick | `melee/pc/platform/gw_script.c:7389` |
| on_unload | () | `melee/pc/platform/gw_script.c:6683`, `melee/pc/platform/gw_script.c:6684` |
| on_zone_enter | {zone,name,label,kind,port,entity,sub,x,y,from=[previous zone handles]}; offline | `melee/pc/platform/gw_script_zones.inc:21` |
| on_zone_exit | {zone,name,label,kind,port,entity,sub,x,y,from=[previous zone handles]}; offline | `melee/pc/platform/gw_script_zones.inc:21` |
| on_zone_none | {zone,name,label,kind,port,entity,sub,x,y,from=[previous zone handles]}; offline | `melee/pc/platform/gw_script_zones.inc:21` |
| on_zone_some | {zone,name,label,kind,port,entity,sub,x,y,from=[previous zone handles]}; offline | `melee/pc/platform/gw_script_zones.inc:21` |

### 6C. Every literal Script_GameEvent producer

| Producer | Actual call / ABI |
|---|---|
| `melee/src/melee/ft/fighter.c:1172` | Script_GameEvent(1 /* LAB_EV_ACTION */, fp->player_id, fp->motion_id, msid, |
| `melee/src/melee/ft/fighter.c:3431` | Script_GameEvent(3 /* LAB_EV_HITLAG */, fp->player_id, 1, fp->is_sub_fighter, 0); |
| `melee/src/melee/ft/fighter.c:3465` | Script_GameEvent(3 /* LAB_EV_HITLAG */, fp->player_id, 0, |
| `melee/src/melee/ft/fighter.c:3487` | Script_GameEvent(3 /* LAB_EV_HITLAG */, fp->player_id, 0, fp->is_sub_fighter, 0); |
| `melee/src/melee/ft/ft_0D31.c:173` | Script_GameEvent(14,attacker,fp->player_id,0,0); |
| `melee/src/melee/ft/ft_0D31.c:174` | Script_GameEvent(15,fp->player_id,Player_GetStocks(fp->player_id),0,0); |
| `melee/src/melee/ft/ftcoll.c:483` | Script_GameEvent(16,fp1->player_id,fp1->motion_id,7,fp1->is_sub_fighter); |
| `melee/src/melee/ft/ftcoll.c:484` | if (fp1->x221C_b2) Script_GameEvent(16,fp1->player_id,fp1->motion_id,8,fp1->is_sub_fighter); |
| `melee/src/melee/ft/ftcoll.c:777` | Script_GameEvent(2 /* LAB_EV_HIT */, fp0->player_id, fp1->player_id, |
| `melee/src/melee/ft/ftcoll.c:930` | Script_GameEvent(16,fp->player_id,fp->motion_id,7,fp->is_sub_fighter); |
| `melee/src/melee/ft/ftcoll.c:1457` | else Script_GameEvent(2 /* LAB_EV_HIT */, owner, fp->player_id, flags, bits.i); |
| `melee/src/melee/ft/ftcommon.c:648` | Script_GameEvent(4 /* LAB_EV_LAND */, fp->player_id, fp->motion_id, |
| `melee/src/melee/gm/gm_17C0.c:114` | Script_GameEvent(LAB_EV_BOSS_DEFEATED, fp->kind, port, x.i, y.i); |
| `melee/pc/gameworld/script_hit_rules.inc:220` | Script_GameEvent(2,attacker->player_id,victim->player_id,255 / (attacker->is_sub_fighter?256:0) / (victim->is_sub_fighter?512:0),bits.i); |

Other typed producers: Script_Clank (script_clank_observe.inc), ItemEvent (geno_game_items.inc ? gw_script_items.inc), TargetBroken/EnemyDefeated/EnemyRemoved/EnemyHit (script_game.c), OnePStage/Clear/Complete/Spawn (retail gm and script_1p.inc), Script_ArmorEvent (new armour adapter). Typed packet dispatch above is the consumer. No input-guess skill event is counted.

### 6D. Every gd registration, grouped by what it reads or changes

Aliases have separate rows. Guard column only shows direct wrapper checks; delegated policy can be stricter. Registration is not netplay admission or journal proof.

#### World / stages / observations

| Call | Capability | Implementation | Registration | Direct guard/branch |
|---|---|---|---|---|
| gd.deadline | Read/control deadline | `melee/pc/platform/gw_script_deadline.inc:20` | `melee/pc/platform/gw_script.c:6233` | Delegated/no direct listed guard |
| gd.deadline_done | Read/control deadline done | `melee/pc/platform/gw_script_deadline.inc:39` | `melee/pc/platform/gw_script.c:6233` | Delegated/no direct listed guard |
| gd.stage_slot_load | Read/control stage slot load | `melee/pc/platform/gw_script_stage_slots.inc:112` | `melee/pc/platform/gw_script.c:6234` | stage, fork history |
| gd.stage_slot_info | Read/control stage slot info | `melee/pc/platform/gw_script_stage_slots.inc:82` | `melee/pc/platform/gw_script.c:6234` | Delegated/no direct listed guard |
| gd.stage_slot_free | Read/control stage slot free | `melee/pc/platform/gw_script_stage_slots.inc:149` | `melee/pc/platform/gw_script.c:6235` | stage, fork history |
| gd.stage_slots | Read/control stage slots | `melee/pc/platform/gw_script_stage_slots.inc:88` | `melee/pc/platform/gw_script.c:6235` | Delegated/no direct listed guard |
| gd.stage_switch | Read/control stage switch | `melee/pc/platform/gw_script_stage_slots.inc:196` | `melee/pc/platform/gw_script.c:6236` | stage |
| gd.stage_queue | Read/control stage queue | `melee/pc/platform/gw_script_stage_slots.inc:209` | `melee/pc/platform/gw_script.c:6236` | stage |
| gd.stage_queue_next | Read/control stage queue next | `melee/pc/platform/gw_script_stage_slots.inc:240` | `melee/pc/platform/gw_script.c:6237` | stage |
| gd.stage_queue_clear | Read/control stage queue clear | `melee/pc/platform/gw_script_stage_slots.inc:204` | `melee/pc/platform/gw_script.c:6237` | stage |
| gd.stage_queue_event | Read/control stage queue event | `melee/pc/platform/gw_script_stage_slots.inc:246` | `melee/pc/platform/gw_script.c:6238` | stage |
| gd.zone_add | Read/control zone add | `melee/pc/platform/gw_script_zones.inc:110` | `melee/pc/platform/gw_script.c:6243` | Delegated/no direct listed guard |
| gd.zone_set | Read/control zone set | `melee/pc/platform/gw_script_zones.inc:111` | `melee/pc/platform/gw_script.c:6243` | Delegated/no direct listed guard |
| gd.zone_remove | Read/control zone remove | `melee/pc/platform/gw_script_zones.inc:112` | `melee/pc/platform/gw_script.c:6243` | offline, fork history |
| gd.zones | Read/control zones | `melee/pc/platform/gw_script_zones.inc:129` | `melee/pc/platform/gw_script.c:6244` | Delegated/no direct listed guard |
| gd.zones_at | Read/control zones at | `melee/pc/platform/gw_script_zones.inc:133` | `melee/pc/platform/gw_script.c:6244` | Delegated/no direct listed guard |
| gd.zone_members | Read/control zone members | `melee/pc/platform/gw_script_zones.inc:136` | `melee/pc/platform/gw_script.c:6245` | Delegated/no direct listed guard |
| gd.point_zones | Read/control point zones | `melee/pc/platform/gw_script_zones.inc:130` | `melee/pc/platform/gw_script.c:6245` | Delegated/no direct listed guard |
| gd.model_label | Read/control model label | `melee/pc/platform/gw_script_contacts.inc:113` | `melee/pc/platform/gw_script.c:6246` | Delegated/no direct listed guard |
| gd.contacts | Read/control contacts | `melee/pc/platform/gw_script_contacts.inc:73` | `melee/pc/platform/gw_script.c:6246` | Delegated/no direct listed guard |
| gd.contact_events | Read/control contact events | `melee/pc/platform/gw_script_contacts.inc:86` | `melee/pc/platform/gw_script.c:6247` | Delegated/no direct listed guard |
| gd.contact_trace | Read/control contact trace | `melee/pc/platform/gw_script_contacts.inc:180` | `melee/pc/platform/gw_script.c:6247` | Delegated/no direct listed guard |
| gd.wait_until | Read/control wait until | `melee/pc/platform/gw_script_contacts.inc:203` | `melee/pc/platform/gw_script.c:6248` | Delegated/no direct listed guard |
| gd.wait_status | Read/control wait status | `melee/pc/platform/gw_script_contacts.inc:243` | `melee/pc/platform/gw_script.c:6248` | Delegated/no direct listed guard |
| gd.contact_overlay | Read/control contact overlay | `melee/pc/platform/gw_script_contacts.inc:200` | `melee/pc/platform/gw_script.c:6249` | Delegated/no direct listed guard |
| gd.camera_get | Read/control camera get | `melee/pc/platform/gw_script.c:928` | `melee/pc/platform/gw_script.c:6261` | Delegated/no direct listed guard |
| gd.camera_detach | Read/control camera detach | `melee/pc/platform/gw_script.c:945` | `melee/pc/platform/gw_script.c:6261` | Delegated/no direct listed guard |
| gd.camera_attach | Read/control camera attach | `melee/pc/platform/gw_script.c:946` | `melee/pc/platform/gw_script.c:6262` | offline, fork history |
| gd.camera_set | Read/control camera set | `melee/pc/platform/gw_script.c:958` | `melee/pc/platform/gw_script.c:6262` | Delegated/no direct listed guard |
| gd.camera_move | Read/control camera move | `melee/pc/platform/gw_script.c:966` | `melee/pc/platform/gw_script.c:6263` | Delegated/no direct listed guard |
| gd.camera_path | Read/control camera path | `melee/pc/platform/gw_script.c:988` | `melee/pc/platform/gw_script.c:6263` | Delegated/no direct listed guard |
| gd.camera_follow | Read/control camera follow | `melee/pc/platform/gw_script.c:1015` | `melee/pc/platform/gw_script.c:6264` | Delegated/no direct listed guard |
| gd.camera_shake | Read/control camera shake | `melee/pc/platform/gw_script.c:1039` | `melee/pc/platform/gw_script.c:6264` | Delegated/no direct listed guard |
| gd.camera_bounds | Read/control camera bounds | `melee/pc/platform/gw_script.c:1049` | `melee/pc/platform/gw_script.c:6265` | Delegated/no direct listed guard |
| gd.stage_add_platform | Read/control stage add platform | `melee/pc/platform/gw_script.c:5759` | `melee/pc/platform/gw_script.c:6312` | stage, fork history |
| gd.stage_add_line | Read/control stage add line | `melee/pc/platform/gw_script.c:5732` | `melee/pc/platform/gw_script.c:6312` | stage, fork history |
| gd.stage_add_model | Read/control stage add model | `melee/pc/platform/gw_script.c:5337` | `melee/pc/platform/gw_script.c:6313` | stage, fork history |
| gd.stage_set_origin | Read/control stage set origin | `melee/pc/platform/gw_script_arena.inc:41` | `melee/pc/platform/gw_script.c:6315` | Delegated/no direct listed guard |
| gd.camera_params | Read/control camera params | `melee/pc/platform/gw_script_camera_params.inc:6` | `melee/pc/platform/gw_script.c:6316` | offline, fork history |
| gd.stage_set_spawn | Read/control stage set spawn | `melee/pc/platform/gw_script_arena.inc:21` | `melee/pc/platform/gw_script.c:6342` | fork history |
| gd.stage_spawn | Read/control stage spawn | `melee/pc/platform/gw_script_arena.inc:32` | `melee/pc/platform/gw_script.c:6342` | Delegated/no direct listed guard |
| gd.stage_set_camera_bounds | Read/control stage set camera bounds | `melee/pc/platform/gw_script_arena.inc:65` | `melee/pc/platform/gw_script.c:6343` | Delegated/no direct listed guard |
| gd.stage_set_blast_bounds | Read/control stage set blast bounds | `melee/pc/platform/gw_script_arena.inc:66` | `melee/pc/platform/gw_script.c:6344` | Delegated/no direct listed guard |
| gd.stage_restore_bounds | Read/control stage restore bounds | `melee/pc/platform/gw_script_arena.inc:67` | `melee/pc/platform/gw_script.c:6345` | fork history |
| gd.stage_bounds | Merge of three gd.stage_bounds: largemap (set/restore + camera/blast), arena-hooks (origin, frames) and model-gaps (main_floor, surface_top). Reads keep every field. | `melee/pc/platform/gw_script.c:6200` | `melee/pc/platform/gw_script.c:6345` | Delegated/no direct listed guard |
| gd.stage_collision_group | Read/control stage collision group | `melee/pc/platform/gw_script_arena.inc:103` | `melee/pc/platform/gw_script.c:6346` | stage, fork history |
| gd.stage_collision_groups | Read/control stage collision groups | `melee/pc/platform/gw_script_arena.inc:92` | `melee/pc/platform/gw_script.c:6347` | Delegated/no direct listed guard |
| gd.model_load | Read/control model load | `melee/pc/platform/gw_script_model_api.inc:70` | `melee/pc/platform/gw_script.c:6348` | stage, fork history |
| gd.model_release | Read/control model release | `melee/pc/platform/gw_script_model_api.inc:83` | `melee/pc/platform/gw_script.c:6349` | stage, fork history |
| gd.model_spawn | Read/control model spawn | `melee/pc/platform/gw_script_model_api.inc:92` | `melee/pc/platform/gw_script.c:6350` | stage, fork history |
| gd.model_move | Read/control model move | `melee/pc/platform/gw_script_model_api.inc:153` | `melee/pc/platform/gw_script.c:6351` | Delegated/no direct listed guard |
| gd.model_set | Read/control model set | `melee/pc/platform/gw_script_model_api.inc:154` | `melee/pc/platform/gw_script.c:6352` | Delegated/no direct listed guard |
| gd.model_despawn | Read/control model despawn | `melee/pc/platform/gw_script_model_api.inc:155` | `melee/pc/platform/gw_script.c:6353` | stage, fork history |
| gd.model_get | Read/control model get | `melee/pc/platform/gw_script_model_api.inc:180` | `melee/pc/platform/gw_script.c:6354` | Delegated/no direct listed guard |
| gd.model_instances | Read/control model instances | `melee/pc/platform/gw_script_model_api.inc:190` | `melee/pc/platform/gw_script.c:6355` | Delegated/no direct listed guard |
| gd.area_load | Read/control area load | `melee/pc/platform/gw_script_largemap.inc:70` | `melee/pc/platform/gw_script.c:6357` | fork history |
| gd.area_unload | Read/control area unload | `melee/pc/platform/gw_script_largemap.inc:145` | `melee/pc/platform/gw_script.c:6357` | fork history |
| gd.area_prepare | Read/control area prepare | `melee/pc/platform/gw_script_largemap.inc:92` | `melee/pc/platform/gw_script.c:6358` | fork history |
| gd.area_activate | Read/control area activate | `melee/pc/platform/gw_script_largemap.inc:119` | `melee/pc/platform/gw_script.c:6358` | stage, fork history |
| gd.area_status | Read/control area status | `melee/pc/platform/gw_script_largemap.inc:132` | `melee/pc/platform/gw_script.c:6358` | stage |
| gd.launch_ready | Read/control launch ready | `melee/pc/platform/gw_script_launch.inc:28` | `melee/pc/platform/gw_script.c:6361` | stage |
| gd.launch_request | Read/control launch request | `melee/pc/platform/gw_script_launch.inc:27` | `melee/pc/platform/gw_script.c:6361` | Delegated/no direct listed guard |
| gd.launch_cancel | Read/control launch cancel | `melee/pc/platform/gw_script_launch.inc:40` | `melee/pc/platform/gw_script.c:6361` | offline |
| gd.area_loaded | Read/control area loaded | `melee/pc/platform/gw_script_largemap.inc:60` | `melee/pc/platform/gw_script.c:6362` | Delegated/no direct listed guard |
| gd.stage_stats | Read/control stage stats | `melee/pc/platform/gw_script_largemap.inc:156` | `melee/pc/platform/gw_script.c:6362` | stage |
| gd.stage_remove | Read/control stage remove | `melee/pc/platform/gw_script.c:5777` | `melee/pc/platform/gw_script.c:6363` | stage, fork history |
| gd.stage_move | Read/control stage move | `melee/pc/platform/gw_script.c:5789` | `melee/pc/platform/gw_script.c:6363` | stage, fork history |
| gd.stage_link | Read/control stage link | `melee/pc/platform/gw_script.c:5804` | `melee/pc/platform/gw_script.c:6364` | stage, fork history |
| gd.stage_isolate | Read/control stage isolate | `melee/pc/platform/gw_script_stage_isolation.inc:2` | `melee/pc/platform/gw_script.c:6364` | stage, fork history |
| gd.stage_hide | Read/control stage hide | `melee/pc/platform/gw_script_stage_isolation.inc:36` | `melee/pc/platform/gw_script.c:6365` | stage |
| gd.spawn_target | Read/control spawn target | `melee/pc/platform/gw_script.c:5836` | `melee/pc/platform/gw_script.c:6366` | stage, fork history |
| gd.stage_view | gd.stage_view([geometry [, overlay]]) -> geometry, overlay: the in-game shapes (on by default) * and the host-overlay debug strokes (off by default). Cosmetic: any script, not gameplay state. | `melee/pc/platform/gw_script.c:5825` | `melee/pc/platform/gw_script.c:6366` | Delegated/no direct listed guard |
| gd.spawn_enemy | Read/control spawn enemy | `melee/pc/platform/gw_script.c:5853` | `melee/pc/platform/gw_script.c:6367` | stage, fork history |
| gd.enemy_remove | Read/control enemy remove | `melee/pc/platform/gw_script.c:5888` | `melee/pc/platform/gw_script.c:6367` | stage, fork history |
| gd.enemy_status | Read/control enemy status | `melee/pc/platform/gw_script.c:5985` | `melee/pc/platform/gw_script.c:6368` | stage |
| gd.enemy_alive | Read/control enemy alive | `melee/pc/platform/gw_script.c:5902` | `melee/pc/platform/gw_script.c:6368` | stage |
| gd.enemy_state | Read/control enemy state | `melee/pc/platform/gw_script.c:5919` | `melee/pc/platform/gw_script.c:6369` | Delegated/no direct listed guard |
| gd.enemy_strike | Read/control enemy strike | `melee/pc/platform/gw_script.c:5962` | `melee/pc/platform/gw_script.c:6369` | Delegated/no direct listed guard |
| gd.enemy_hurt | Read/control enemy hurt | `melee/pc/platform/gw_script.c:5963` | `melee/pc/platform/gw_script.c:6369` | Delegated/no direct listed guard |
| gd.hud_visible | Read/control hud visible | `melee/pc/platform/gw_script.c:5965` | `melee/pc/platform/gw_script.c:6370` | offline |

#### Rendering / effects / warmup

| Call | Capability | Implementation | Registration | Direct guard/branch |
|---|---|---|---|---|
| gd.shader_load | Read/control shader load | `melee/pc/platform/gw_script_shaders.inc:90` | `melee/pc/platform/gw_script.c:6239` | Delegated/no direct listed guard |
| gd.shader_set | Read/control shader set | `melee/pc/platform/gw_script_shaders.inc:98` | `melee/pc/platform/gw_script.c:6239` | Delegated/no direct listed guard |
| gd.shader_status | Read/control shader status | `melee/pc/platform/gw_script_shaders.inc:105` | `melee/pc/platform/gw_script.c:6239` | Delegated/no direct listed guard |
| gd.post_add | Read/control post add | `melee/pc/platform/gw_script_shaders.inc:112` | `melee/pc/platform/gw_script.c:6240` | Delegated/no direct listed guard |
| gd.post_set | Read/control post set | `melee/pc/platform/gw_script_shaders.inc:151` | `melee/pc/platform/gw_script.c:6240` | Delegated/no direct listed guard |
| gd.post_remove | Read/control post remove | `melee/pc/platform/gw_script_shaders.inc:160` | `melee/pc/platform/gw_script.c:6240` | Delegated/no direct listed guard |
| gd.post_clear | Read/control post clear | `melee/pc/platform/gw_script_shaders.inc:165` | `melee/pc/platform/gw_script.c:6240` | Delegated/no direct listed guard |
| gd.post_ready | Read/control post ready | `melee/pc/platform/gw_script_shaders.inc:215` | `melee/pc/platform/gw_script.c:6241` | Delegated/no direct listed guard |
| gd.fx_shader | Read/control fx shader | `melee/pc/platform/gw_script_shaders.inc:172` | `melee/pc/platform/gw_script.c:6242` | Delegated/no direct listed guard |
| gd.light_set | Read/control light set | `melee/pc/platform/gw_script_shaders.inc:191` | `melee/pc/platform/gw_script.c:6242` | Delegated/no direct listed guard |
| gd.echo_afterimage | Read/control echo afterimage | `melee/pc/platform/gw_script_echo_visual.inc:53` | `melee/pc/platform/gw_script.c:6252` | gameplay, fork history |
| gd.afterimage_copy | Read/control afterimage copy | `melee/pc/platform/gw_script_echo_visual.inc:45` | `melee/pc/platform/gw_script.c:6252` | Delegated/no direct listed guard |
| gd.afterimage_copy_set | Read/control afterimage copy set | `melee/pc/platform/gw_script_echo_visual.inc:34` | `melee/pc/platform/gw_script.c:6252` | Delegated/no direct listed guard |
| gd.afterimage_add | Read/control afterimage add | `melee/pc/platform/gw_script_motion.inc:86` | `melee/pc/platform/gw_script.c:6253` | Delegated/no direct listed guard |
| gd.afterimage_set | Read/control afterimage set | `melee/pc/platform/gw_script_motion.inc:115` | `melee/pc/platform/gw_script.c:6253` | Delegated/no direct listed guard |
| gd.afterimage_remove | Read/control afterimage remove | `melee/pc/platform/gw_script_motion.inc:118` | `melee/pc/platform/gw_script.c:6253` | Delegated/no direct listed guard |
| gd.tracer_add | Read/control tracer add | `melee/pc/platform/gw_script_motion.inc:93` | `melee/pc/platform/gw_script.c:6254` | Delegated/no direct listed guard |
| gd.tracer_set | Read/control tracer set | `melee/pc/platform/gw_script_motion.inc:116` | `melee/pc/platform/gw_script.c:6254` | Delegated/no direct listed guard |
| gd.tracer_remove | Read/control tracer remove | `melee/pc/platform/gw_script_motion.inc:119` | `melee/pc/platform/gw_script.c:6254` | Delegated/no direct listed guard |
| gd.tracer_hitboxes | Read/control tracer hitboxes | `melee/pc/platform/gw_script_motion.inc:98` | `melee/pc/platform/gw_script.c:6255` | Delegated/no direct listed guard |
| gd.motion_intensity | Read/control motion intensity | `melee/pc/platform/gw_script_motion.inc:120` | `melee/pc/platform/gw_script.c:6255` | Delegated/no direct listed guard |
| gd.motion_stats | Read/control motion stats | `melee/pc/platform/gw_script_motion.inc:121` | `melee/pc/platform/gw_script.c:6255` | Delegated/no direct listed guard |
| gd.fighter_shader | Read/control fighter shader | `melee/pc/platform/gw_script_surface.inc:74` | `melee/pc/platform/gw_script.c:6256` | surface ownership |
| gd.fighter_shader_set | Read/control fighter shader set | `melee/pc/platform/gw_script_surface.inc:83` | `melee/pc/platform/gw_script.c:6257` | Delegated/no direct listed guard |
| gd.stage_shader | Read/control stage shader | `melee/pc/platform/gw_script_surface.inc:80` | `melee/pc/platform/gw_script.c:6258` | surface ownership |
| gd.fx | Read/control fx | `melee/pc/platform/gw_script.c:1551` | `melee/pc/platform/gw_script.c:6260` | Delegated/no direct listed guard |
| gd.dobjs | gd.dobjs(port) -> the fighter's draw list, read-only: { models = {state per model-part model}, * costume = {{frame, tu, tv, su, sv} per costume texture-anim TObj}, {index, hidden, render, tobjs = * {{id, src, flags, tu, tv, su, sv | `melee/pc/platform/gw_script.c:3129` | `melee/pc/platform/gw_script.c:6288` | Delegated/no direct listed guard |
| gd.dobj_solid | Read/control dobj solid | `melee/pc/platform/gw_script.c:3171` | `melee/pc/platform/gw_script.c:6289` | offline, fork history |
| gd.dobj_solid_off | Read/control dobj solid off | `melee/pc/platform/gw_script.c:3191` | `melee/pc/platform/gw_script.c:6289` | offline, fork history |
| gd.dobj_tint | Read/control dobj tint | `melee/pc/platform/gw_script.c:3209` | `melee/pc/platform/gw_script.c:6290` | offline, fork history |
| gd.parts | Read/control parts | `melee/pc/platform/gw_script.c:3222` | `melee/pc/platform/gw_script.c:6291` | offline |
| gd.parts_id | Read/control parts id | `melee/pc/platform/gw_script.c:3261` | `melee/pc/platform/gw_script.c:6291` | offline, fork history |
| gd.parts_id_off | Read/control parts id off | `melee/pc/platform/gw_script.c:3268` | `melee/pc/platform/gw_script.c:6291` | offline |
| gd.parts_clear | Read/control parts clear | `melee/pc/platform/gw_script.c:3275` | `melee/pc/platform/gw_script.c:6291` | offline |
| gd.fx_attach | Read/control fx attach | `melee/pc/platform/gw_script.c:3278` | `melee/pc/platform/gw_script.c:6292` | offline, fork history |
| gd.fx_stop | Read/control fx stop | `melee/pc/platform/gw_script.c:3291` | `melee/pc/platform/gw_script.c:6292` | offline |
| gd.fx_play | Read/control fx play | `melee/pc/platform/gw_script.c:3296` | `melee/pc/platform/gw_script.c:6293` | offline, fork history |
| gd.fx_control | Read/control fx control | `melee/pc/platform/gw_script.c:3342` | `melee/pc/platform/gw_script.c:6293` | offline, fork history |
| gd.fx_end | Read/control fx end | `melee/pc/platform/gw_script.c:3356` | `melee/pc/platform/gw_script.c:6293` | offline, fork history |
| gd.fx_instance | Read/control fx instance | `melee/pc/platform/gw_script.c:3362` | `melee/pc/platform/gw_script.c:6293` | Delegated/no direct listed guard |
| gd.fx_world | Read/control fx world | `melee/pc/platform/gw_script.c:3325` | `melee/pc/platform/gw_script.c:6294` | offline, fork history |
| gd.fx_move | Read/control fx move | `melee/pc/platform/gw_script.c:3337` | `melee/pc/platform/gw_script.c:6294` | offline, fork history |
| gd.dobj_tints | Read/control dobj tints | `melee/pc/platform/gw_script_tint_query.inc:2` | `melee/pc/platform/gw_script.c:6337` | Delegated/no direct listed guard |
| gd.warm | Read/control warm | `melee/pc/platform/gw_script_warm.inc:75` | `melee/pc/platform/gw_script.c:6359` | stage |
| gd.warm_done | Read/control warm done | `melee/pc/platform/gw_script_warm.inc:64` | `melee/pc/platform/gw_script.c:6359` | Delegated/no direct listed guard |
| gd.warm_status | Read/control warm status | `melee/pc/platform/gw_script_warm.inc:69` | `melee/pc/platform/gw_script.c:6359` | Delegated/no direct listed guard |
| gd.warm_release | Read/control warm release | `melee/pc/platform/gw_script_warm.inc:123` | `melee/pc/platform/gw_script.c:6359` | Delegated/no direct listed guard |

#### Fighter / collision / items / sound

| Call | Capability | Implementation | Registration | Direct guard/branch |
|---|---|---|---|---|
| gd.fighter_history | Read/control fighter history | `melee/pc/platform/gw_script_echo.inc:88` | `melee/pc/platform/gw_script.c:6250` | Delegated/no direct listed guard |
| gd.fighter_history_depth | Read/control fighter history depth | `melee/pc/platform/gw_script_echo.inc:86` | `melee/pc/platform/gw_script.c:6250` | Delegated/no direct listed guard |
| gd.echo_add | Read/control echo add | `melee/pc/platform/gw_script_echo.inc:75` | `melee/pc/platform/gw_script.c:6251` | gameplay, fork history |
| gd.echo_remove | Read/control echo remove | `melee/pc/platform/gw_script_echo.inc:82` | `melee/pc/platform/gw_script.c:6251` | gameplay, fork history |
| gd.echoes | Read/control echoes | `melee/pc/platform/gw_script_echo.inc:108` | `melee/pc/platform/gw_script.c:6251` | Delegated/no direct listed guard |
| gd.fighter_recycle | Read/control fighter recycle | `melee/pc/platform/gw_script_six_slots.inc:5` | `melee/pc/platform/gw_script.c:6260` | offline, fork history |
| gd.items | Read/control items | `melee/pc/platform/gw_script.c:1521` | `melee/pc/platform/gw_script.c:6260` | Delegated/no direct listed guard |
| gd.hitstop | Read/control hitstop | `melee/pc/platform/gw_script_presentation.inc:9` | `melee/pc/platform/gw_script.c:6270` | offline |
| gd.hitstop_cancel | Read/control hitstop cancel | `melee/pc/platform/gw_script_presentation.inc:27` | `melee/pc/platform/gw_script.c:6270` | offline |
| gd.set_percent | Read/control set percent | `melee/pc/platform/gw_script.c:1808` | `melee/pc/platform/gw_script.c:6271` | gameplay, fork history |
| gd.set_damage | gd.set_damage(port, n): the fighter's real damage (fp->dmg.x1830_percent) and the player's * damage slot together (Player_SetHUDDamage -> ftLib_800870F0), so the HUD, knockback and a stamina * boss's remaining HP (Player_GetRemain | `melee/pc/platform/gw_script.c:1822` | `melee/pc/platform/gw_script.c:6271` | gameplay, offline, fork history |
| gd.hit | gd.hit(port or {enemy=handle}, {damage, angle, kbg, bkb, from?}): feed a hit to Melee's collision * damage result and fighter hit processing. All inputs are integers to keep it repeatable. | `melee/pc/platform/gw_script.c:1839` | `melee/pc/platform/gw_script.c:6272` | offline, stage, fork history |
| gd.impulse | Read/control impulse | `melee/pc/platform/gw_script.c:1887` | `melee/pc/platform/gw_script.c:6272` | offline, fork history |
| gd.cpu_mode | Read/control cpu mode | `melee/pc/platform/gw_script.c:1870` | `melee/pc/platform/gw_script.c:6272` | offline, fork history |
| gd.cpu_technical | Read/control cpu technical | `melee/pc/platform/gw_script_cpu.inc:2` | `melee/pc/platform/gw_script.c:6272` | offline, fork history |
| gd.cpu_assist | Per-entity technique assist on top of the retail AI's pad: L-cancel, tech (+direction), perfect shield, wavedash, fast fall, seeded probabilities, counters (`melee/src/melee/ft/cpu_assist.inc`) | `melee/pc/platform/gw_script_cpu.inc:48` | `melee/pc/platform/gw_script.c:6478` | offline, game BSS (snapshot-covered) |
| gd.set_stocks | Read/control set stocks | `melee/pc/platform/gw_script.c:1901` | `melee/pc/platform/gw_script.c:6272` | gameplay, fork history |
| gd.play_sound | Read/control play sound | `melee/pc/platform/gw_script.c:2054` | `melee/pc/platform/gw_script.c:6273` | Delegated/no direct listed guard |
| gd.hold_hitbox | Read/control hold hitbox | `melee/pc/platform/gw_script.c:2016` | `melee/pc/platform/gw_script.c:6273` | offline |
| gd.fly | Read/control fly | `melee/pc/platform/gw_script.c:1970` | `melee/pc/platform/gw_script.c:6274` | offline |
| gd.teleport | Read/control teleport | `melee/pc/platform/gw_script.c:2064` | `melee/pc/platform/gw_script.c:6274` | offline, fork history |
| gd.fly_speed | gd.fly_speed([units per frame]) -> the speed; gd.fly_solid([bool]) -> hurtboxes kept | `melee/pc/platform/gw_script.c:2077` | `melee/pc/platform/gw_script.c:6274` | offline, fork history |
| gd.fly_solid | gd.fly_speed([units per frame]) -> the speed; gd.fly_solid([bool]) -> hurtboxes kept | `melee/pc/platform/gw_script.c:2087` | `melee/pc/platform/gw_script.c:6274` | offline, fork history |
| gd.fly_target | Read/control fly target | `melee/pc/platform/gw_script_fly_attack.inc:53` | `melee/pc/platform/gw_script.c:6275` | offline |
| gd.fly_attack | Read/control fly attack | `melee/pc/platform/gw_script_fly_attack.inc:63` | `melee/pc/platform/gw_script.c:6275` | offline |
| gd.fly_clear | Read/control fly clear | `melee/pc/platform/gw_script_fly_attack.inc:78` | `melee/pc/platform/gw_script.c:6275` | offline, fork history |
| gd.fly_state | Read/control fly state | `melee/pc/platform/gw_script_fly_attack.inc:86` | `melee/pc/platform/gw_script.c:6275` | Delegated/no direct listed guard |
| gd.set_shield | gd.set_shield(port, health): the dummy's infinite shield. Gameplay, offline; forks the timeline like gd.set_percent. | `melee/pc/platform/gw_script.c:5235` | `melee/pc/platform/gw_script.c:6311` | offline, fork history |
| gd.fighter_mod | Read/control fighter mod | `melee/pc/platform/gw_script_fighter_mod.inc:6` | `melee/pc/platform/gw_script.c:6324` | offline, fork history |
| gd.fighter_caps | Read/control fighter caps | `melee/pc/platform/gw_script_fighter_caps.inc:40` | `melee/pc/platform/gw_script.c:6325` | fork history, offline capability helper |
| gd.fighter_effect | Read/control fighter effect | `melee/pc/platform/gw_script_fighter_caps.inc:78` | `melee/pc/platform/gw_script.c:6325` | fork history, offline capability helper |
| gd.fighter_armour | Read/control fighter armour | `melee/pc/platform/gw_script_fighter_caps.inc:96` | `melee/pc/platform/gw_script.c:6326` | fork history, offline capability helper |
| gd.fighter_armor | Read/control fighter armor | `melee/pc/platform/gw_script_fighter_caps_armor.inc:26` | `melee/pc/platform/gw_script.c:6327` | fork history, offline capability helper |
| gd.give_item | Read/control give item | `melee/pc/platform/gw_script_fighter_caps.inc:122` | `melee/pc/platform/gw_script.c:6327` | fork history, offline capability helper |
| gd.nearest_opponent | Read/control nearest opponent | `melee/pc/platform/gw_script_fighter_caps.inc:135` | `melee/pc/platform/gw_script.c:6328` | Delegated/no direct listed guard |
| gd.opponents_in_radius | Read/control opponents in radius | `melee/pc/platform/gw_script_fighter_caps.inc:142` | `melee/pc/platform/gw_script.c:6328` | Delegated/no direct listed guard |
| gd.fighter_timed_status | Read/control fighter timed status | `melee/pc/platform/gw_script_fighter_caps.inc:153` | `melee/pc/platform/gw_script.c:6329` | fork history, offline capability helper |
| gd.hit_rule_add | Read/control hit rule add | `melee/pc/platform/gw_script_hit_rules.inc:88` | `melee/pc/platform/gw_script.c:6330` | gameplay, fork history |
| gd.hit_rule_remove | Read/control hit rule remove | `melee/pc/platform/gw_script_hit_rules.inc:105` | `melee/pc/platform/gw_script.c:6330` | gameplay, fork history |
| gd.hit_rules | Read/control hit rules | `melee/pc/platform/gw_script_hit_rules.inc:129` | `melee/pc/platform/gw_script.c:6331` | Delegated/no direct listed guard |
| gd.hit_rules_clear | Read/control hit rules clear | `melee/pc/platform/gw_script_hit_rules.inc:114` | `melee/pc/platform/gw_script.c:6331` | gameplay, fork history |
| gd.fighter_status | Read/control fighter status | `melee/pc/platform/gw_script_hit_rules.inc:120` | `melee/pc/platform/gw_script.c:6332` | gameplay, fork history |
| gd.item_define | Read/control item define | `melee/pc/platform/gw_script_items.inc:77` | `melee/pc/platform/gw_script.c:6338` | offline |
| gd.item_events | Read/control item events | `melee/pc/platform/gw_script_items.inc:120` | `melee/pc/platform/gw_script.c:6338` | Delegated/no direct listed guard |
| gd.item_spawn | Read/control item spawn | `melee/pc/platform/gw_script_items.inc:198` | `melee/pc/platform/gw_script.c:6338` | offline, fork history |
| gd.item_despawn | Read/control item despawn | `melee/pc/platform/gw_script_items.inc:251` | `melee/pc/platform/gw_script.c:6338` | offline, fork history |
| gd.fighter_bench | Read/control fighter bench | `melee/pc/platform/gw_script_fighter_bench.inc:42` | `melee/pc/platform/gw_script.c:6339` | offline, fork history |
| gd.fighter_call | Read/control fighter call | `melee/pc/platform/gw_script_fighter_bench.inc:50` | `melee/pc/platform/gw_script.c:6340` | offline, fork history |
| gd.fighter_benched | Read/control fighter benched | `melee/pc/platform/gw_script_fighter_bench.inc:20` | `melee/pc/platform/gw_script.c:6341` | Delegated/no direct listed guard |
| gd.item_kinds | Read/control item kinds | `melee/pc/platform/gw_script_warm.inc:173` | `melee/pc/platform/gw_script.c:6360` | stage |

#### Host / diagnostics / data / control

| Call | Capability | Implementation | Registration | Direct guard/branch |
|---|---|---|---|---|
| gd.log | Read/control log | `melee/pc/platform/gw_script.c:1318` | `melee/pc/platform/gw_script.c:6259` | Delegated/no direct listed guard |
| gd.frame | Read/control frame | `melee/pc/platform/gw_script.c:1335` | `melee/pc/platform/gw_script.c:6259` | Delegated/no direct listed guard |
| gd.time | Read/control time | `melee/pc/platform/gw_script.c:1340` | `melee/pc/platform/gw_script.c:6259` | Delegated/no direct listed guard |
| gd.perf | Read/control perf | `melee/pc/platform/gw_script.c:6052` | `melee/pc/platform/gw_script.c:6259` | Delegated/no direct listed guard |
| gd.prof | Read/control prof | `melee/pc/platform/gw_script.c:6135` | `melee/pc/platform/gw_script.c:6259` | Delegated/no direct listed guard |
| gd.scene | Read/control scene | `melee/pc/platform/gw_script.c:1345` | `melee/pc/platform/gw_script.c:6259` | Delegated/no direct listed guard |
| gd.match | Read/control match | `melee/pc/platform/gw_script.c:1467` | `melee/pc/platform/gw_script.c:6259` | Delegated/no direct listed guard |
| gd.players | Read/control players | `melee/pc/platform/gw_script.c:1476` | `melee/pc/platform/gw_script.c:6260` | Delegated/no direct listed guard |
| gd.player | Read/control player | `melee/pc/platform/gw_script.c:1576` | `melee/pc/platform/gw_script.c:6260` | Delegated/no direct listed guard |
| gd.char_name | Read/control char name | `melee/pc/platform/gw_script.c:1586` | `melee/pc/platform/gw_script.c:6266` | Delegated/no direct listed guard |
| gd.scene_launch | gd.scene_launch("mode=training;p1=fox") or gd.scene_launch{mode="training", p1="fox"} | `melee/pc/platform/gw_script.c:2299` | `melee/pc/platform/gw_script.c:6278` | gameplay |
| gd.scene_clear | Read/control scene clear | `melee/pc/platform/gw_script.c:2355` | `melee/pc/platform/gw_script.c:6278` | Delegated/no direct listed guard |
| gd.command | Read/control command | `melee/pc/platform/gw_script.c:2581` | `melee/pc/platform/gw_script.c:6280` | Delegated/no direct listed guard |
| gd.run | Read/control run | `melee/pc/platform/gw_script.c:2608` | `melee/pc/platform/gw_script.c:6280` | Delegated/no direct listed guard |
| gd.data_read | Read/control data read | `melee/pc/platform/gw_script_data_read.inc:9` | `melee/pc/platform/gw_script.c:6281` | Delegated/no direct listed guard |
| gd.data_exists | Read/control data exists | `melee/pc/platform/gw_script_data_read.inc:2` | `melee/pc/platform/gw_script.c:6281` | Delegated/no direct listed guard |
| gd.data_write | Read/control data write | `melee/pc/platform/gw_script.c:2753` | `melee/pc/platform/gw_script.c:6281` | Delegated/no direct listed guard |
| gd.data_write_atomic | gd.data_write_atomic(name, text) -> true  /  false, why * Writes a sibling temporary file, checks every write/flush/close result, then * replaces the target. A failure leaves the previous file untouched. This is * atomic against a t | `melee/pc/platform/gw_script.c:2784` | `melee/pc/platform/gw_script.c:6281` | Delegated/no direct listed guard |
| gd.script | Read/control script | `melee/pc/platform/gw_script.c:2836` | `melee/pc/platform/gw_script.c:6281` | Delegated/no direct listed guard |
| gd.mod_read | Read/control mod read | `melee/pc/platform/gw_script_mission.inc:269` | `melee/pc/platform/gw_script.c:6282` | Delegated/no direct listed guard |
| gd.mod_list | Read/control mod list | `melee/pc/platform/gw_script_mission.inc:270` | `melee/pc/platform/gw_script.c:6282` | Delegated/no direct listed guard |
| gd.mod_stamp | Read/control mod stamp | `melee/pc/platform/gw_script_mission.inc:271` | `melee/pc/platform/gw_script.c:6282` | Delegated/no direct listed guard |
| gd.screenshot | gd.screenshot(name): into the script's data folder (a bare file name, .png added) | `melee/pc/platform/gw_script.c:2454` | `melee/pc/platform/gw_script.c:6284` | Delegated/no direct listed guard |
| gd.quit | gd.quit(): close the game window the way the user would (gameplay scripts and the console) | `melee/pc/platform/gw_script.c:2481` | `melee/pc/platform/gw_script.c:6284` | gameplay |
| gd.menu | gd.menu() -> {frontend = {title, screen, cursor, item} (the port's own menus: gmfrontend.c), * native = {menu, hovered} (Melee's menu tree)}. Which one is live follows gd.scene(). | `melee/pc/platform/gw_script.c:1384` | `melee/pc/platform/gw_script.c:6285` | Delegated/no direct listed guard |
| gd.netplay | gd.netplay() -> the connection and the lobby, read-only (stages, groups, the screen's cursor). | `melee/pc/platform/gw_script.c:1401` | `melee/pc/platform/gw_script.c:6285` | Delegated/no direct listed guard |
| gd.netplay_act | gd.netplay_act("char", ck, color)  /  ("stage", i) (1-based: strike, ban or pick, whichever the * lobby is in)  /  ("ready", on)  /  ("code", "ABCD") (the join code). Lobby actions go through the * same rules as a player's (the host val | `melee/pc/platform/gw_script.c:1448` | `melee/pc/platform/gw_script.c:6285` | Delegated/no direct listed guard |
| gd.floor_below | gd.floor_below(x, y [, depth]) -> the y of the first floor line under (x, y) within `depth` units (default 200), or nil. Read-only (mpCheckFloor), in a match only. Stage D's dummy. | `melee/pc/platform/gw_script.c:5216` | `melee/pc/platform/gw_script.c:6311` | Delegated/no direct listed guard |

#### Input

| Call | Capability | Implementation | Registration | Direct guard/branch |
|---|---|---|---|---|
| gd.pad | Read/control pad | `melee/pc/platform/gw_script.c:1708` | `melee/pc/platform/gw_script.c:6266` | Delegated/no direct listed guard |
| gd.input | gd.input(port, spec, frames): spec = "A+B"  /  {buttons="A", x=, y=, cx=, cy=, l=, r=} | `melee/pc/platform/gw_script.c:1658` | `melee/pc/platform/gw_script.c:6267` | gameplay, fork history |
| gd.release | Read/control release | `melee/pc/platform/gw_script.c:1688` | `melee/pc/platform/gw_script.c:6267` | offline, fork history |
| gd.release_pad | Read/control release pad | `melee/pc/platform/gw_script.c:1688` | `melee/pc/platform/gw_script.c:6267` | offline, fork history |
| gd.key | Read/control key | `melee/pc/platform/gw_script.c:2535` | `melee/pc/platform/gw_script.c:6279` | Delegated/no direct listed guard |
| gd.key_pressed | Read/control key pressed | `melee/pc/platform/gw_script.c:2540` | `melee/pc/platform/gw_script.c:6280` | Delegated/no direct listed guard |
| gd.mouse | Read/control mouse | `melee/pc/platform/gw_script.c:2553` | `melee/pc/platform/gw_script.c:6280` | Delegated/no direct listed guard |
| gd.mirror_pad | gd.mirror_pad(from, to) / gd.mirror_pad(): port `to` gets exactly what port `from` sends (for comparing two fighters under the same inputs; `to` must be a human slot). Offline, gameplay. | `melee/pc/platform/gw_script.c:3857` | `melee/pc/platform/gw_script.c:6303` | offline |

#### LAB / snapshot / inspection

| Call | Capability | Implementation | Registration | Direct guard/branch |
|---|---|---|---|---|
| gd.savestate | Read/control savestate | `melee/pc/platform/gw_script.c:1755` | `melee/pc/platform/gw_script.c:6268` | gameplay |
| gd.loadstate | Read/control loadstate | `melee/pc/platform/gw_script.c:1767` | `melee/pc/platform/gw_script.c:6269` | gameplay |
| gd.pause | Read/control pause | `melee/pc/platform/gw_script.c:1785` | `melee/pc/platform/gw_script.c:6269` | gameplay |
| gd.resume | Read/control resume | `melee/pc/platform/gw_script.c:1790` | `melee/pc/platform/gw_script.c:6269` | gameplay |
| gd.step | Read/control step | `melee/pc/platform/gw_script.c:1796` | `melee/pc/platform/gw_script.c:6269` | gameplay |
| gd.paused | Read/control paused | `melee/pc/platform/gw_script.c:1803` | `melee/pc/platform/gw_script.c:6271` | Delegated/no direct listed guard |
| gd.debug_draw | gd.debug_draw(port) -> flags; gd.debug_draw(port, flags) -> previous flags (offline, gameplay) | `melee/pc/platform/gw_script.c:2893` | `melee/pc/platform/gw_script.c:6287` | offline |
| gd.debug_stage | gd.debug_stage() -> flags; gd.debug_stage(flags) -> the flags now set (offline, gameplay) | `melee/pc/platform/gw_script.c:2911` | `melee/pc/platform/gw_script.c:6287` | offline |
| gd.hitboxes | gd.hitboxes(port [, all]) -> the hitboxes that are on (all = every slot 0-4, on or off) | `melee/pc/platform/gw_script.c:2932` | `melee/pc/platform/gw_script.c:6287` | Delegated/no direct listed guard |
| gd.hurtboxes | gd.hurtboxes(port) -> {{id, bone, state, height, grabbable, ax, ay, az, bx, by, bz, radius}} | `melee/pc/platform/gw_script.c:2952` | `melee/pc/platform/gw_script.c:6288` | Delegated/no direct listed guard |
| gd.joints | gd.joints(port [, fresh]) -> {{index, parent, x, y, z, sx, sy, on}, ...}; list position = * index + 1. fresh = true brings every joint's matrix up to date first (ScriptGame_JointsSetup); * without it a joint nothing used this fram | `melee/pc/platform/gw_script.c:3080` | `melee/pc/platform/gw_script.c:6288` | Delegated/no direct listed guard |
| gd.attrs | Read/control attrs | `melee/pc/platform/gw_script.c:3369` | `melee/pc/platform/gw_script.c:6295` | Delegated/no direct listed guard |
| gd.motion_name | gd.motion_name(id [, port]) -> the action state's name (the port picks the fighter's table) | `melee/pc/platform/gw_script.c:3386` | `melee/pc/platform/gw_script.c:6297` | Delegated/no direct listed guard |
| gd.history | gd.history([frames [, interval]]) -> {depth, seconds, back, fwd, now, head, oldest, keys, mb, delta_mb, key_ms, last_ms, last_load_ms, last_frames, replaying, busy, ...}: with frames, keep that many frames of rewind (0 = off, at m | `melee/pc/platform/gw_script.c:3955` | `melee/pc/platform/gw_script.c:6297` | offline |
| gd.step_back | gd.step_back([n]) -> true  /  false, why: go back n frames and stay paused. Offline, gameplay. The newest keyframe at or before the target is loaded and the frames after it re-simulated on the logged inputs (silently, in one tick). | `melee/pc/platform/gw_script.c:4010` | `melee/pc/platform/gw_script.c:6297` | offline |
| gd.rewind_to | gd.rewind_to(frame) -> true  /  false, why: any frame from gd.history().oldest to .head (forward too, while the log still has the frames after "now"). Offline, gameplay; stays paused. | `melee/pc/platform/gw_script.c:4024` | `melee/pc/platform/gw_script.c:6298` | offline |
| gd.rewind_live | gd.rewind_live() -> true: stop replaying the log here; the pads play from this frame on (the logged frames after it are dropped). Offline, gameplay. | `melee/pc/platform/gw_script.c:4038` | `melee/pc/platform/gw_script.c:6298` | offline, fork history |
| gd.rewind_test | gd.rewind_test([frames [, keep_running]]) -> true  /  false, why: the exactness self-test. Copies the whole state at the next frame, runs `frames` more (default 90), rewinds to the copied frame through the keyframes and the input lo | `melee/pc/platform/gw_script.c:4051` | `melee/pc/platform/gw_script.c:6298` | offline |
| gd.rewind_test_result | gd.rewind_test_result() -> {phase (0 = done), pass (true/false/nil), diff, diff_compared, text} | `melee/pc/platform/gw_script.c:4076` | `melee/pc/platform/gw_script.c:6299` | Delegated/no direct listed guard |
| gd.hot_reload | gd.hot_reload([seconds]) -> true, start  /  false, why: save where you are, rewind `seconds` (default 2) through the history, reload the fighters' geno.json (attributes, parameters, states, subaction overlays and their words files)  | `melee/pc/platform/gw_script.c:4095` | `melee/pc/platform/gw_script.c:6299` | offline |
| gd.hot_reload_status | gd.hot_reload_status() -> {phase (0 = idle), ok, text} | `melee/pc/platform/gw_script.c:4151` | `melee/pc/platform/gw_script.c:6300` | Delegated/no direct listed guard |
| gd.state_save | gd.state_save([name [, what]]) -> file  /  false, why: the whole state to a new file in the Lab's library, at the next frame boundary (at once when paused). Offline, gameplay. | `melee/pc/platform/gw_script.c:4362` | `melee/pc/platform/gw_script.c:6300` | offline |
| gd.state_list | gd.state_list() -> {{file, name, what, frame, time, saved, stage, fighters = {{port, char, costume, cpu}}, ok, why}, ...}, newest first. `ok` false = it would be refused now, `why` says why. gd.state_gen() changes whenever the lib | `melee/pc/platform/gw_script.c:4401` | `melee/pc/platform/gw_script.c:6301` | Delegated/no direct listed guard |
| gd.state_load | gd.state_load(file) -> true  /  false, why: checked now (build, disc, mods, Geno data, and that this match is the state's match); loaded whole at the next frame boundary. Offline, gameplay. | `melee/pc/platform/gw_script.c:4476` | `melee/pc/platform/gw_script.c:6301` | offline |
| gd.state_delete | gd.state_delete(file) -> true  /  false, why | `melee/pc/platform/gw_script.c:4502` | `melee/pc/platform/gw_script.c:6301` | offline |
| gd.state_rename | gd.state_rename(file, name) -> true  /  false, why | `melee/pc/platform/gw_script.c:4521` | `melee/pc/platform/gw_script.c:6302` | offline |
| gd.state_gen | Read/control state gen | `melee/pc/platform/gw_script.c:4469` | `melee/pc/platform/gw_script.c:6302` | Delegated/no direct listed guard |
| gd.lab_peek | gd.lab_peek(addr [, n]) -> hex string: n (<= 64) raw bytes of MEM1 at addr, as memory holds them (game memory is big-endian). Read-only, for the Lab's debugging. | `melee/pc/platform/gw_script.c:4133` | `melee/pc/platform/gw_script.c:6302` | Delegated/no direct listed guard |
| gd.timeline | gd.timeline(port [, motion]) -> {motion, motion_name, anim_id, anim_name, end_frame, length, events = {{frame, op, name, words, ...decoded fields}}, truncated} The script of the fighter's current action, or of `motion` (its row in | `melee/pc/platform/gw_script.c:3658` | `melee/pc/platform/gw_script.c:6303` | Delegated/no direct listed guard |
| gd.set_motion | Read/control set motion | `melee/pc/platform/gw_script.c:3810` | `melee/pc/platform/gw_script.c:6303` | offline |
| gd.lab_request | gd.lab_request([clear]) -> true when the frontend's LAB entry (or MELEE_LAB=1) asked for the Lab this session; `clear` resets it | `melee/pc/platform/gw_script.c:3877` | `melee/pc/platform/gw_script.c:6304` | Delegated/no direct listed guard |
| gd.lab_mode | gd.lab_mode() -> true while LAB is the running game mode (its match, its select screens) | `melee/pc/platform/gw_script.c:3896` | `melee/pc/platform/gw_script.c:6304` | Delegated/no direct listed guard |
| gd.lab_leave | gd.lab_leave("css"  /  "sss"  /  "menu"  /  "restart") -> true when a LAB match was ended (a no contest): back to LAB's character select, its stage select, or the menus. Offline only (the match's own end). | `melee/pc/platform/gw_script.c:3913` | `melee/pc/platform/gw_script.c:6304` | gameplay |
| gd.tbd_request | Read/control tbd request | `melee/pc/platform/gw_script.c:3884` | `melee/pc/platform/gw_script.c:6305` | Delegated/no direct listed guard |
| gd.input_mask | Read/control input mask | `melee/pc/platform/gw_script.c:1739` | `melee/pc/platform/gw_script.c:6305` | offline |
| gd.training_select | gd.training_select(["kit"  /  "native"]) -> the current choice. Training's character and * stage select on the port's kit screens or the native ones; stays until changed. Menu routing * only - the match and its rules are Training's  | `melee/pc/platform/gw_script.c:2340` | `melee/pc/platform/gw_script.c:6306` | Delegated/no direct listed guard |
| gd.motion_list | gd.motion_list(port) -> {{id, name, group ("common"  /  "special"  /  "mex"  /  "geno"), anim_id, anim_name}, ...}: every action state the fighter has a row for, in id order. "mex" = a special past the decomp's table (the m-ex MoveLogic | `melee/pc/platform/gw_script.c:3763` | `melee/pc/platform/gw_script.c:6308` | Delegated/no direct listed guard |
| gd.kb_preview | Read/control kb preview | `melee/pc/platform/gw_script.c:4960` | `melee/pc/platform/gw_script.c:6308` | offline |
| gd.rollbacks | gd.rollbacks([n]) -> {total, list = {{frame, first, depth, cause (port; 0 = SyncTest's own), kind ("synctest"  /  "fake"  /  "netplay"), mismatch, ms}, ...} newest first (n, default 120), mismatch = {frame, count, where, va, was, now} | `melee/pc/platform/gw_script.c:5130` | `melee/pc/platform/gw_script.c:6308` | Delegated/no direct listed guard |
| gd.rollbacks_clear | Read/control rollbacks clear | `melee/pc/platform/gw_script.c:5166` | `melee/pc/platform/gw_script.c:6309` | Delegated/no direct listed guard |
| gd.lab_env | gd.lab_env(name) -> the value of the environment variable MELEE_LAB_<name>, or nil (only that family: the Lab's launch switches, e.g. MELEE_LAB_BATCH for the headless frame-data export) | `melee/pc/platform/gw_script.c:5246` | `melee/pc/platform/gw_script.c:6309` | Delegated/no direct listed guard |
| gd.lab_now | gd.lab_now([long]) -> the local time, "20260924-153000" (a version tag) or, with long, "2026-09-24 15:30:00" (the sandbox has no os.date) | `melee/pc/platform/gw_script.c:5174` | `melee/pc/platform/gw_script.c:6309` | Delegated/no direct listed guard |
| gd.lab_common | gd.lab_common() -> the PlCo constants the Lab's training readouts use (stage D), as loaded: lcancel_window (an L-cancel needs player.lr_age below it at landing), lcancel_div (the landing lag is divided by it), hitstun_mul, kb_spee | `melee/pc/platform/gw_script.c:5192` | `melee/pc/platform/gw_script.c:6311` | Delegated/no direct listed guard |
| gd.sim_commit | Read/control sim commit | `melee/pc/platform/gw_script_sim_state.inc:119` | `melee/pc/platform/gw_script.c:6333` | offline, fork history |
| gd.sim_clear | Read/control sim clear | `melee/pc/platform/gw_script_sim_state.inc:54` | `melee/pc/platform/gw_script.c:6334` | offline, fork history |
| gd.sim_read | Read/control sim read | `melee/pc/platform/gw_script_sim_state.inc:110` | `melee/pc/platform/gw_script.c:6335` | Delegated/no direct listed guard |
| gd.sim_replaying | Read/control sim replaying | `melee/pc/platform/gw_script_sim_state.inc:27` | `melee/pc/platform/gw_script.c:6336` | Delegated/no direct listed guard |

#### Run / 1P / storage

| Call | Capability | Implementation | Registration | Direct guard/branch |
|---|---|---|---|---|
| gd.boss_hold | Read/control boss hold | `melee/pc/platform/gw_script.c:1058` | `melee/pc/platform/gw_script.c:6276` | offline, fork history |
| gd.boss_release | Read/control boss release | `melee/pc/platform/gw_script.c:1069` | `melee/pc/platform/gw_script.c:6276` | offline, fork history |
| gd.mode_blob | gd.mode_blob([bytes]): nil if absent; "" clears. Snapshot state is keyed by * source+id hash, so script load order cannot expose another script's data. | `melee/pc/platform/gw_script_mode.inc:76` | `melee/pc/platform/gw_script.c:6277` | offline, fork history |
| gd.campaign_storage | Read/control campaign storage | `melee/pc/platform/gw_script_campaign.inc:4` | `melee/pc/platform/gw_script.c:6283` | offline |
| gd.mode_1p | Read/control mode 1p | `melee/pc/platform/gw_script_1p.inc:188` | `melee/pc/platform/gw_script.c:6317` | Delegated/no direct listed guard |
| gd.start_1p | Read/control start 1p | `melee/pc/platform/gw_script_1p.inc:214` | `melee/pc/platform/gw_script.c:6318` | Delegated/no direct listed guard |
| gd.end_1p | Read/control end 1p | `melee/pc/platform/gw_script_1p.inc:316` | `melee/pc/platform/gw_script.c:6319` | Delegated/no direct listed guard |
| gd.hold_1p | Read/control hold 1p | `melee/pc/platform/gw_script_1p.inc:192` | `melee/pc/platform/gw_script.c:6320` | offline |
| gd.release_1p | Read/control release 1p | `melee/pc/platform/gw_script_1p.inc:201` | `melee/pc/platform/gw_script.c:6321` | offline |
| gd.loop_1p | Read/control loop 1p | `melee/pc/platform/gw_script_1p.inc:205` | `melee/pc/platform/gw_script.c:6322` | offline |
| gd.spawn_1p | Read/control spawn 1p | `melee/pc/platform/gw_script_1p.inc:242` | `melee/pc/platform/gw_script.c:6323` | offline, fork history |

#### UI / layout / draw

| Call | Capability | Implementation | Registration | Direct guard/branch |
|---|---|---|---|---|
| gd.text | Read/control text | `melee/pc/platform/gw_script.c:2391` | `melee/pc/platform/gw_script.c:6278` | Delegated/no direct listed guard |
| gd.box | Read/control box | `melee/pc/platform/gw_script.c:2489` | `melee/pc/platform/gw_script.c:6279` | Delegated/no direct listed guard |
| gd.fill | Read/control fill | `melee/pc/platform/gw_script.c:2490` | `melee/pc/platform/gw_script.c:6279` | Delegated/no direct listed guard |
| gd.line | Read/control line | `melee/pc/platform/gw_script.c:2491` | `melee/pc/platform/gw_script.c:6279` | Delegated/no direct listed guard |
| gd.rgb | Read/control rgb | `melee/pc/platform/gw_script.c:2427` | `melee/pc/platform/gw_script.c:6284` | Delegated/no direct listed guard |
| gd.label | Read/control label | `melee/pc/platform/gw_script.c:2437` | `melee/pc/platform/gw_script.c:6284` | Delegated/no direct listed guard |
| gd.project | gd.project(x, y [, z]) -> sx, sy, visible, depth (nil when there is no match camera) | `melee/pc/platform/gw_script.c:3047` | `melee/pc/platform/gw_script.c:6295` | Delegated/no direct listed guard |
| gd.safe_area | gd.safe_area() -> {x, y, w, h, right, bottom}: the overlay canvas in script units. Height is * always 480; the width follows the window's aspect, so wide layouts lay out against this. | `melee/pc/platform/gw_script.c:3065` | `melee/pc/platform/gw_script.c:6296` | Delegated/no direct listed guard |
| gd.kit.available | Read/control available | `melee/pc/platform/gw_script.c:4635` | `melee/pc/platform/gw_script.c:5997` | Delegated/no direct listed guard |
| gd.kit.text | Read/control text | `melee/pc/platform/gw_script.c:4642` | `melee/pc/platform/gw_script.c:5997` | Delegated/no direct listed guard |
| gd.kit.measure | Read/control measure | `melee/pc/platform/gw_script.c:4680` | `melee/pc/platform/gw_script.c:5997` | Delegated/no direct listed guard |
| gd.kit.paragraph | Read/control paragraph | `melee/pc/platform/gw_script.c:4660` | `melee/pc/platform/gw_script.c:5998` | Delegated/no direct listed guard |
| gd.kit.metrics | Read/control metrics | `melee/pc/platform/gw_script.c:4702` | `melee/pc/platform/gw_script.c:5998` | Delegated/no direct listed guard |
| gd.kit.texture | Read/control texture | `melee/pc/platform/gw_script.c:4718` | `melee/pc/platform/gw_script.c:5998` | Delegated/no direct listed guard |
| gd.kit.image | Read/control image | `melee/pc/platform/gw_script.c:4763` | `melee/pc/platform/gw_script.c:5999` | Delegated/no direct listed guard |
| gd.kit.icon | Read/control icon | `melee/pc/platform/gw_script.c:4771` | `melee/pc/platform/gw_script.c:6000` | Delegated/no direct listed guard |
| gd.kit.panel | Read/control panel | `melee/pc/platform/gw_script.c:4788` | `melee/pc/platform/gw_script.c:6000` | Delegated/no direct listed guard |
| gd.kit.button | Read/control button | `melee/pc/platform/gw_script.c:4837` | `melee/pc/platform/gw_script.c:6000` | Delegated/no direct listed guard |
| gd.kit.list | Read/control list | `melee/pc/platform/gw_script.c:4859` | `melee/pc/platform/gw_script.c:6000` | Delegated/no direct listed guard |
| gd.kit.color | Read/control color | `melee/pc/platform/gw_script.c:4899` | `melee/pc/platform/gw_script.c:6001` | Delegated/no direct listed guard |

#### Lua helpers / admission flags

| Name | Source | Meaning |
|---|---|---|
| gd.wait | `melee/pc/platform/gw_script.c:6377` | Coroutine/input or dialogue presentation helper |
| gd.wait_until | `melee/pc/platform/gw_script.c:6379` | Coroutine/input or dialogue presentation helper |
| gd.press | `melee/pc/platform/gw_script.c:6388` | Coroutine/input or dialogue presentation helper |
| gd.tilt | `melee/pc/platform/gw_script.c:6395` | Coroutine/input or dialogue presentation helper |
| gd.comm | `melee/pc/platform/gw_script_comm.inc:18` | Coroutine/input or dialogue presentation helper |
| gd.comm_clear | `melee/pc/platform/gw_script_comm.inc:32` | Coroutine/input or dialogue presentation helper |
| gd.comm_state | `melee/pc/platform/gw_script_comm.inc:37` | Coroutine/input or dialogue presentation helper |
| gd.comm_draw | `melee/pc/platform/gw_script_comm.inc:51` | Coroutine/input or dialogue presentation helper |
| gd.sim_supported | gw_script.c base environment | Boolean capability flag, not a call; wait_until overlaps native helper |

#### New armour/echo source integration anchors

| Executor / integration | Evidence |
|---|---|
| static int l_fighter_armor(lua_State* L) | `melee/pc/platform/gw_script_fighter_caps_armor.inc:26` |
| void gw_Script_ArmorEvent(int entity,int type,int absorbed,int broke,int damage_bits,int kb_bits) | `melee/pc/platform/gw_script_fighter_caps_armor.inc:85` |
| int ScriptGame_ArmorSet(int entity,int owner,int type,int value_bits,int frames, | `melee/pc/gameworld/script_fighter_caps_armor.inc:40` |
| int ScriptGame_ArmorRead(int entity,int type,int field) | `melee/pc/gameworld/script_fighter_caps_armor.inc:55` |
| int ScriptGame_ArmorClear(int entity,int owner,int type) | `melee/pc/gameworld/script_fighter_caps_armor.inc:77` |
| void ScriptGame_ArmorRelease(int owner) | `melee/pc/gameworld/script_fighter_caps_armor.inc:92` |
| void ScriptGame_ArmorFrame(void) | `melee/pc/gameworld/script_fighter_caps_armor.inc:104` |
| void ScriptGame_ArmorResetReaction(Fighter* fp) | `melee/pc/gameworld/script_fighter_caps_armor.inc:118` |
| int ScriptGame_ArmorReact(Fighter* fp) | `melee/pc/gameworld/script_fighter_caps_armor.inc:133` |
| int ScriptGame_ArmorAbsorbed(Fighter* fp) | `melee/pc/gameworld/script_fighter_caps_armor.inc:159` |
| int gw_Script_EchoInput(int at) { return gs_echo_input && at>=0 && at<GS_ECHO_MAX*GS_ECHO_FIELDS ? gs_echo_input[at] : 0; } | `melee/pc/platform/gw_script_echo.inc:16` |
| static int l_echo_add(lua_State *L) { | `melee/pc/platform/gw_script_echo.inc:75` |
| static int l_echo_remove(lua_State *L) { | `melee/pc/platform/gw_script_echo.inc:82` |
| static int l_fighter_history_depth(lua_State *L){lua_pushinteger(L,gw_ScriptGame_FighterHistoryDepth());return 1;} | `melee/pc/platform/gw_script_echo.inc:86` |
| static int l_fighter_history(lua_State *L) { | `melee/pc/platform/gw_script_echo.inc:88` |
| static int l_echoes(lua_State *L) { | `melee/pc/platform/gw_script_echo.inc:108` |
| int gw_EchoCopyStyle(int port,int sub,int copy,int field) { | `melee/pc/platform/gw_script_echo_visual.inc:19` |
| static int l_afterimage_copy_set(lua_State *L) { | `melee/pc/platform/gw_script_echo_visual.inc:34` |
| static int l_afterimage_copy(lua_State *L) { | `melee/pc/platform/gw_script_echo_visual.inc:45` |
| static int l_echo_afterimage(lua_State *L) { | `melee/pc/platform/gw_script_echo_visual.inc:53` |
| int ScriptGame_FighterHistoryDepth(void) {return ECHO_DEPTH;} | `melee/pc/gameworld/script_echo.inc:30` |
| int ScriptGame_FighterHistoryRead(int entity,int age,int hit,int field) { | `melee/pc/gameworld/script_echo.inc:31` |
| int ScriptGame_EchoOwner(int entity) { | `melee/pc/gameworld/script_echo.inc:54` |
| int ScriptGame_EchoNextHandle(void) {return script_echo.next_handle==0x7fffffff ? 0 : script_echo.next_handle+1;} | `melee/pc/gameworld/script_echo.inc:59` |
| int ScriptGame_EchoRead(int entity,int index,int field) { | `melee/pc/gameworld/script_echo.inc:60` |
| int ScriptGame_EchoReplace(int entity,int owner,int count) { | `melee/pc/gameworld/script_echo.inc:75` |
| int ScriptGame_EchoAddWithHandle(int entity,int owner,int delay,int move,int match_element,int airborne, | `melee/pc/gameworld/script_echo.inc:95` |
| int ScriptGame_EchoAdd(int entity,int owner,int delay,int move,int match_element,int airborne, | `melee/pc/gameworld/script_echo.inc:110` |
| int ScriptGame_EchoRemove(int handle,int owner) { | `melee/pc/gameworld/script_echo.inc:114` |
| void ScriptGame_EchoClear(int owner) { | `melee/pc/gameworld/script_echo.inc:120` |
| void ScriptGame_EchoReset(void) {ScriptGame_EchoClear(0);memset(&script_echo,0,sizeof script_echo);} | `melee/pc/gameworld/script_echo.inc:124` |
| void ScriptGame_EchoFrame(void) { | `melee/pc/gameworld/script_echo.inc:125` |
| void ScriptGame_EchoCapture(Fighter* fp) { | `melee/pc/gameworld/script_echo.inc:150` |
| void ScriptGame_EchoPrepare(void) { | `melee/pc/gameworld/script_echo.inc:232` |
| int ScriptGame_EchoCapsuleCount(Fighter* fp) { | `melee/pc/gameworld/script_echo.inc:236` |
| int ScriptGame_EchoIsCapsule(HitCapsule* hit) { | `melee/pc/gameworld/script_echo.inc:245` |
| int ScriptGame_EchoHitIndex(Fighter* fp,HitCapsule* hit) { | `melee/pc/gameworld/script_echo.inc:254` |
| void ScriptGame_EchoConnected(HitCapsule* hit,Fighter* victim) { | `melee/pc/gameworld/script_echo.inc:258` |
| int ScriptGame_EchoSameGroup(HitCapsule* a,HitCapsule* b) { | `melee/pc/gameworld/script_echo.inc:267` |
| int ScriptGame_EchoBlocked(HitCapsule* hit,Fighter* victim) { | `melee/pc/gameworld/script_echo.inc:271` |
| int ScriptGame_EchoState(int entity,int handle,int field) { | `melee/pc/gameworld/script_echo.inc:277` |
| int ScriptGame_EchoReportContext(Fighter* attacker,Fighter* victim,HitCapsule* hit) { | `melee/pc/gameworld/script_echo.inc:284` |
| int ScriptGame_EchoCredit(Fighter* attacker,Fighter* victim,HitCapsule* hit,float damage) { | `melee/pc/gameworld/script_echo.inc:295` |
| int ScriptGame_EchoSourceX(HitCapsule* hit,int fallback) { | `melee/pc/gameworld/script_echo.inc:307` |
| static int l_sim_replaying(lua_State *L) { lua_pushboolean(L,gs_sim_replay_mode); return 1; } | `melee/pc/platform/gw_script_sim_state.inc:27` |
| int gw_Script_SimByte(int at) { | `melee/pc/platform/gw_script_sim_state.inc:31` |
| static int l_sim_clear(lua_State *L) { | `melee/pc/platform/gw_script_sim_state.inc:54` |
|         if(o->kind==1) { | `melee/pc/platform/gw_script_sim_state.inc:75` |
|         } else if(o->kind==3) gs_hr_apply_targets(o->slot,o->enabled,c->script+1,&o->hit_rules); | `melee/pc/platform/gw_script_sim_state.inc:86` |
|         else if(o->kind==4) gs_echo_apply(o->slot*2+o->enabled,c->script+1,&o->echoes); | `melee/pc/platform/gw_script_sim_state.inc:87` |
| static int l_sim_read(lua_State *L) { | `melee/pc/platform/gw_script_sim_state.inc:110` |
| static int l_sim_commit(lua_State *L) { | `melee/pc/platform/gw_script_sim_state.inc:119` |
|         o->kind=!strcmp(name,"fighter_mod") ? 1 : !strcmp(name,"damage") ? 2 : !strcmp(name,"hit_rules") ? 3 : !strcmp(name,"echoes") ? 4 : 0; lua_pop(L,1); | `melee/pc/platform/gw_script_sim_state.inc:138` |
|         if(!o->kind) return luaL_error(L,"sim_commit unsupported operation"); | `melee/pc/platform/gw_script_sim_state.inc:139` |
|         if(o->kind==1) { | `melee/pc/platform/gw_script_sim_state.inc:140` |
|         } else if(o->kind==3) { | `melee/pc/platform/gw_script_sim_state.inc:157` |
|         } else if(o->kind==4) { | `melee/pc/platform/gw_script_sim_state.inc:160` |

### 6E. Complete finite Envoy/native/visual/entity term ledger

| Term | Namespace(s) | Produces | Consumes | Alias / orphan / gap | Evidence |
|---|---|---|---|---|---|
| additive | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| aerial | tag, hit_move | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| afterimage | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| air_dodge | native/visual/entity/loot | Capabilities/retail | Gates/timers/physics | No shared modifier/Geno descriptor or journal | `melee/pc/platform/gw_script_fighter_caps.inc:78` |
| air_jump | event | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| air_jump_height | value | Value/implicit/status budget | fighter_mod or native percent/launch rules | Temporary ratio != Geno baseline | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:6` |
| air_jumps | native/visual/entity/loot | Capabilities/retail | Gates/timers/physics | No shared modifier/Geno descriptor or journal | `melee/pc/platform/gw_script_fighter_caps.inc:78` |
| air_speed | value | Value/implicit/status budget | fighter_mod or native percent/launch rules | Temporary ratio != Geno baseline | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:6` |
| airborne | tag, condition | Player/event/status/recent context | E:matches | No common native/Geno predicate | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:65` |
| alpha | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| always | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| any | hit_move, native/visual/entity/loot | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| article | native/visual/entity/loot | Retail/Geno/world spawn/history | System-specific selectors | CPU/projectile are roles; IDs incompatible | `melee/pc/platform/gw_script_fighter_caps.inc:17` |
| back | native/visual/entity/loot | Native typed armour declaration | ScriptArmorCore / ordinary reaction | Six types; direction is a filter, not seventh type; Geno and modifier adapters absent | `melee/pc/platform/gw_script_fighter_caps_armor.inc:7` |
| bair | native/visual/entity/loot | Retail aerial action selector | Echo matcher | Not general tags; Lua echo precise set only nair | `melee/pc/platform/gw_script_echo.inc:17` |
| battle | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| blue | native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| bonus | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| boss | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| burn | status | Lua application/expiry, native_rules mask | Budget/predicates/display/native presence bits | Adjective alias; native mask lacks stacks/expiry/origin | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:164` |
| burning | tag | Lua application/expiry, native_rules mask | Budget/predicates/display/native presence bits | Adjective alias; native mask lacks stacks/expiry/origin | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:164` |
| chill | status | Lua application/expiry, native_rules mask | Budget/predicates/display/native presence bits | Adjective alias; native mask lacks stacks/expiry/origin | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:164` |
| chilled | tag | Lua application/expiry, native_rules mask | Budget/predicates/display/native presence bits | Adjective alias; native mask lacks stacks/expiry/origin | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:164` |
| clank | event, family | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| clank_damage | effect | Pool effects | apply / values / native_rules / mod_echo | No Geno shared effect source; phase-specific executor | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:101` |
| cleanse | family | Effect/status/implicit delta | Caps/foe strength/pool audit | Safety family != tag; Lua-local | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:4` |
| common | native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| conversion | family | Effect/status/implicit delta | Caps/foe strength/pool audit | Safety family != tag; Lua-local | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:4` |
| convert | effect | Pool effects | apply / values / native_rules / mod_echo | No Geno shared effect source; phase-specific executor | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:101` |
| cpu_opponent | native/visual/entity/loot | Retail/Geno/world spawn/history | System-specific selectors | CPU/projectile are roles; IDs incompatible | `melee/pc/platform/gw_script_fighter_caps.inc:17` |
| curse | status | Lua application/expiry, native_rules mask | Budget/predicates/display/native presence bits | Adjective alias; native mask lacks stacks/expiry/origin | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:164` |
| curse_dealt | family | Effect/status/implicit delta | Caps/foe strength/pool audit | Safety family != tag; Lua-local | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:4` |
| cursed | tag | Lua application/expiry, native_rules mask | Budget/predicates/display/native presence bits | Adjective alias; native mask lacks stacks/expiry/origin | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:164` |
| dair | native/visual/entity/loot | Retail aerial action selector | Echo matcher | Not general tags; Lua echo precise set only nair | `melee/pc/platform/gw_script_echo.inc:17` |
| damage | tag, effect | Pool effects | apply / values / native_rules / mod_echo | No Geno shared effect source; phase-specific executor | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:101` |
| damage_dealt | value, family | Effect/status/implicit delta | Caps/foe strength/pool audit | Safety family != tag; Lua-local | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:4` |
| damage_pool | native/visual/entity/loot | Native typed armour declaration | ScriptArmorCore / ordinary reaction | Six types; direction is a filter, not seventh type; Geno and modifier adapters absent | `melee/pc/platform/gw_script_fighter_caps_armor.inc:7` |
| damage_taken | value, family | Effect/status/implicit delta | Caps/foe strength/pool audit | Safety family != tag; Lua-local | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:4` |
| damage_threshold | native/visual/entity/loot | Native typed armour declaration | ScriptArmorCore / ordinary reaction | Six types; direction is a filter, not seventh type; Geno and modifier adapters absent | `melee/pc/platform/gw_script_fighter_caps_armor.inc:7` |
| dark | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| darkness | tag, element | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| dash_attack | tag, hit_move | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| directional | native/visual/entity/loot | Native typed armour declaration | ScriptArmorCore / ordinary reaction | Six types; direction is a filter, not seventh type; Geno and modifier adapters absent | `melee/pc/platform/gw_script_fighter_caps_armor.inc:7` |
| echo | effect, family, native/visual/entity/loot | Pool effects | apply / values / native_rules / mod_echo | No Geno shared effect source; phase-specific executor | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:101` |
| electric | tag, element, native/visual/entity/loot | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| emit | effect | Pool effects | apply / values / native_rules / mod_echo | No Geno shared effect source; phase-specific executor | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:101` |
| equip | event | Passive declaration / 1P stage envelope | E:matches/recent, no Geno subscriber | equip passively compiled; stage_start lacks modifier route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| extend | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| fair | native/visual/entity/loot | Retail aerial action selector | Echo matcher | Not general tags; Lua echo precise set only nair | `melee/pc/platform/gw_script_echo.inc:17` |
| fall_speed | value | Value/implicit/status budget | fighter_mod or native percent/launch rules | Budget omits this schema key | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:6` |
| fighter | native/visual/entity/loot | Retail/Geno/world spawn/history | System-specific selectors | CPU/projectile are roles; IDs incompatible | `melee/pc/platform/gw_script_fighter_caps.inc:17` |
| final | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| fire | tag, element, native/visual/entity/loot | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| flag | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| front | native/visual/entity/loot | Native typed armour declaration | ScriptArmorCore / ordinary reaction | Six types; direction is a filter, not seventh type; Geno and modifier adapters absent | `melee/pc/platform/gw_script_fighter_caps_armor.inc:7` |
| frost | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| fx | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| giant | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| glow | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| grab | tag, event, hit_move, native/visual/entity/loot | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| gradient | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| green | native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| grounded | tag, condition | Player/event/status/recent context | E:matches | No common native/Geno predicate | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:65` |
| guarded | tag, status | Lua application/expiry, native_rules mask | Budget/predicates/display/native presence bits | Adjective alias; native mask lacks stacks/expiry/origin | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:164` |
| haste | status | Lua application/expiry, native_rules mask | Budget/predicates/display/native presence bits | Adjective alias; native mask lacks stacks/expiry/origin | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:164` |
| hasted | tag | Lua application/expiry, native_rules mask | Budget/predicates/display/native presence bits | Adjective alias; native mask lacks stacks/expiry/origin | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:164` |
| heal | effect | Pool effects | apply / values / native_rules / mod_echo | No Geno shared effect source; phase-specific executor | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:101` |
| healing | tag | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| hit_count | native/visual/entity/loot | Native typed armour declaration | ScriptArmorCore / ordinary reaction | Six types; direction is a filter, not seventh type; Geno and modifier adapters absent | `melee/pc/platform/gw_script_fighter_caps_armor.inc:7` |
| hit_dealt | event | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| hit_taken | event | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| ice | tag, element | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| intangible | native/visual/entity/loot | Capabilities/retail | Gates/timers/physics | No shared modifier/Geno descriptor or journal | `melee/pc/platform/gw_script_fighter_caps.inc:78` |
| interval | event | Lua status/timer/emit | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| invincible | native/visual/entity/loot | Capabilities/retail | Gates/timers/physics | No shared modifier/Geno descriptor or journal | `melee/pc/platform/gw_script_fighter_caps.inc:78` |
| item | native/visual/entity/loot | Retail/Geno/world spawn/history | System-specific selectors | CPU/projectile are roles; IDs incompatible | `melee/pc/platform/gw_script_fighter_caps.inc:17` |
| item_pickup | event | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| jab | tag, hit_move | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| jump | event, family | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| jump_height | value | Value/implicit/status budget | fighter_mod or native percent/launch rules | Temporary ratio != Geno baseline | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:6` |
| keep | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| keystone | tag, native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| knockback | native/visual/entity/loot | Native typed armour declaration | ScriptArmorCore / ordinary reaction | Six types; direction is a filter, not seventh type; Geno and modifier adapters absent | `melee/pc/platform/gw_script_fighter_caps_armor.inc:7` |
| knockback_taken | value | Value/implicit/status budget | fighter_mod or native percent/launch rules | Temporary ratio != Geno baseline | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:6` |
| knockback_threshold | native/visual/entity/loot | Native typed armour declaration | ScriptArmorCore / ordinary reaction | Six types; direction is a filter, not seventh type; Geno and modifier adapters absent | `melee/pc/platform/gw_script_fighter_caps_armor.inc:7` |
| ko_dealt | event | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| landing | event | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| last_stock | condition | Player/event/status/recent context | E:matches | No common native/Geno predicate | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:65` |
| launch_dealt | family | Effect/status/implicit delta | Caps/foe strength/pool audit | Safety family != tag; Lua-local | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:4` |
| launch_taken | family | Effect/status/implicit delta | Caps/foe strength/pool audit | Safety family != tag; Lua-local | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:4` |
| ledge_grab | event | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| light | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| magic | native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| metal | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| momentum | tag, status, family | Lua application/expiry, native_rules mask | Budget/predicates/display/native presence bits | Adjective alias; native mask lacks stacks/expiry/origin | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:164` |
| moving | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| nair | native/visual/entity/loot | Retail aerial action selector | Echo matcher | Not general tags; Lua echo precise set only nair | `melee/pc/platform/gw_script_echo.inc:17` |
| normal | tag, element | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| own | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| perfect_shield | event | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| post | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| prefix | native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| projectile | tag, hit_move, native/visual/entity/loot | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| purple | native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| rare | native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| recently | condition | Player/event/status/recent context | E:matches | No common native/Geno predicate | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:65` |
| red | native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| refresh | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| remove_status | effect | Pool effects | apply / values / native_rules / mod_echo | No Geno shared effect source; phase-specific executor | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:101` |
| run | native/visual/entity/loot | Capabilities/retail | Gates/timers/physics | No shared modifier/Geno descriptor or journal | `melee/pc/platform/gw_script_fighter_caps.inc:78` |
| run_speed | value | Value/implicit/status budget | fighter_mod or native percent/launch rules | Temporary ratio != Geno baseline | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:6` |
| self_damage_above | condition | Player/event/status/recent context | E:matches | No common native/Geno predicate | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:65` |
| self_damage_below | condition | Player/event/status/recent context | E:matches | No common native/Geno predicate | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:65` |
| self_status | condition | Player/event/status/recent context | E:matches | No common native/Geno predicate | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:65` |
| shield_hit | event | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| shield_max | value | Value/implicit/status budget | fighter_mod or native percent/launch rules | Budget omits this schema key | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:6` |
| shield_regen | value | Value/implicit/status budget | fighter_mod or native percent/launch rules | Budget omits this schema key | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:6` |
| shock | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| shocked | tag | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| silhouette | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| size | native/visual/entity/loot | Capabilities/retail | Gates/timers/physics | No shared modifier/Geno descriptor or journal | `melee/pc/platform/gw_script_fighter_caps.inc:78` |
| smash | tag, hit_move | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| solid | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| special | tag, hit_move | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| specials | native/visual/entity/loot | Capabilities/retail | Gates/timers/physics | No shared modifier/Geno descriptor or journal | `melee/pc/platform/gw_script_fighter_caps.inc:78` |
| speed | family | Effect/status/implicit delta | Caps/foe strength/pool audit | Safety family != tag; Lua-local | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:4` |
| stacks | effect | Pool effects | apply / values / native_rules / mod_echo | No Geno shared effect source; phase-specific executor | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:101` |
| stacks_changed | event | Lua status/timer/emit | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| stage_kind | condition | Player/event/status/recent context | E:matches | No common native/Geno predicate | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:65` |
| stage_object | native/visual/entity/loot | Retail/Geno/world spawn/history | System-specific selectors | CPU/projectile are roles; IDs incompatible | `melee/pc/platform/gw_script_fighter_caps.inc:17` |
| stage_start | event | Passive declaration / 1P stage envelope | E:matches/recent, no Geno subscriber | equip passively compiled; stage_start lacks modifier route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| status | condition, effect | Pool effects | apply / values / native_rules / mod_echo | No Geno shared effect source; phase-specific executor | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:101` |
| status_applied | event | Lua status/timer/emit | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| status_duration | value, family | Effect/status/implicit delta | Caps/foe strength/pool audit | Safety family != tag; Lua-local | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:4` |
| status_removed | event | Lua status/timer/emit | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| stock_lost | event | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| sub_fighter | native/visual/entity/loot | Retail/Geno/world spawn/history | System-specific selectors | CPU/projectile are roles; IDs incompatible | `melee/pc/platform/gw_script_fighter_caps.inc:17` |
| suffix | native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| super | native/visual/entity/loot | Native typed armour declaration | ScriptArmorCore / ordinary reaction | Six types; direction is a filter, not seventh type; Geno and modifier adapters absent | `melee/pc/platform/gw_script_fighter_caps_armor.inc:7` |
| surface | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| sustain | family | Effect/status/implicit delta | Caps/foe strength/pool audit | Safety family != tag; Lua-local | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:4` |
| tag | condition | Player/event/status/recent context | E:matches | No common native/Geno predicate | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:65` |
| target_damage_above | condition | Player/event/status/recent context | E:matches | No common native/Geno predicate | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:65` |
| target_status | condition | Player/event/status/recent context | E:matches | No common native/Geno predicate | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:65` |
| taunt | event | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| team | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| throw | tag, event, hit_move | Script hook ? mod_lab | E:matches/recent, no Geno subscriber | Primary-port LAB route | `melee/pc/scripts/examples/envoy/scripts/mod_lab.lua:103`, `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:38` |
| tilt | tag, hit_move | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| tracer | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| uair | native/visual/entity/loot | Retail aerial action selector | Echo matcher | Not general tags; Lua echo precise set only nair | `melee/pc/platform/gw_script_echo.inc:17` |
| unique | tag, native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| unknown | hit_move | Retail context/creation conversion | Native predicates/Lua tag match | Geno/m-ex special unknown; item projectile incomplete | `melee/pc/gameworld/script_hit_context.inc:16` |
| value | effect | Pool effects | apply / values / native_rules / mod_echo | No Geno shared effect source; phase-specific executor | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:101` |
| versus-status | effect | Pool effects | apply / values / native_rules / mod_echo | No Geno shared effect source; phase-specific executor | `melee/pc/scripts/examples/envoy/scripts/mod_engine.lua:101` |
| weight | value | Value/implicit/status budget | fighter_mod or native percent/launch rules | Budget omits this schema key | `melee/pc/scripts/examples/envoy/scripts/mod_budget.lua:6` |
| white | native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| world | native/visual/entity/loot | Look/options/stage flags | Renderer/display/local schema | Local semantics; Shock look != Shock status | `melee/pc/platform/gw_script_motion.inc:45`, `melee/pc/scripts/examples/envoy/scripts/mod_display.lua:4` |
| yellow | native/visual/entity/loot | Loot/pool | Roll/naming/bag/display | Native payload lacks purple; ledger owns full rule record | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:1`, `melee/pc/platform/gw_script_items.inc:29` |
| zone | native/visual/entity/loot | Retail/Geno/world spawn/history | System-specific selectors | CPU/projectile are roles; IDs incompatible | `melee/pc/platform/gw_script_fighter_caps.inc:17` |

### 6F. Every Geno exported gameplay symbol

Profile/subaction definitions PRODUCE these typed words; Geno command/state/article executors CONSUME them. No implicit Lua modifier subscription. COUNT/MAX/sizing sentinels excluded; numbered register ranges use endpoint symbols. Each engine symbol keeps its namespace even where the meaning overlaps a Lua term.

| Term | Meaning / producer ? consumer | Evidence |
|---|---|---|
| GENO_SUB_NOP | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:48` |
| GENO_SUB_SET | A = B | `melee/pc/geno/geno.h:49` |
| GENO_SUB_ADD | A += B | `melee/pc/geno/geno.h:50` |
| GENO_SUB_SUB | A -= B | `melee/pc/geno/geno.h:51` |
| GENO_SUB_MUL | A *= B | `melee/pc/geno/geno.h:52` |
| GENO_SUB_SETBIT | A  / = 1 << B   (int vars) | `melee/pc/geno/geno.h:53` |
| GENO_SUB_CLRBIT | A &= ~(1 << B) | `melee/pc/geno/geno.h:54` |
| GENO_SUB_DIV | v1: A /= B (B == 0: unchanged) | `melee/pc/geno/geno.h:55` |
| GENO_SUB_GET | v1: A = engine value word1 (GENO_VAL_*) | `melee/pc/geno/geno.h:56` |
| GENO_SUB_PUT | v1: engine value word1 = B (word2; [7] B is a var) | `melee/pc/geno/geno.h:57` |
| GENO_SUB_RAND | v1: A = game-RNG random in [0, B) | `melee/pc/geno/geno.h:58` |
| GENO_SUB_IF | if !(A cmp B) skip word2 words | `melee/pc/geno/geno.h:59` |
| GENO_SUB_SKIP | skip word1 words (the jump over an else branch) | `melee/pc/geno/geno.h:60` |
| GENO_SUB_IFV | v1: if !(value word1 cmp B word2) skip word3 words | `melee/pc/geno/geno.h:61` |
| GENO_SUB_ORIG | v1: continue with the overlaid subaction's original script | `melee/pc/geno/geno.h:62` |
| GENO_SUB_CALL | call native hook word1 with argument word2 | `melee/pc/geno/geno.h:63` |
| GENO_SUB_CHG | v1: register a change-action check (word1 target, word2/3 args) | `melee/pc/geno/geno.h:64` |
| GENO_SUB_CHGAND | v1: AND another condition onto the last CHG (word1/2 args) | `melee/pc/geno/geno.h:65` |
| GENO_SUB_CHGCLR | v1: drop every change-action check of this action | `melee/pc/geno/geno.h:66` |
| GENO_SUB_REHIT | v1: [15:8] hitbox mask; word1 = rehit every N frames (0 = off) | `melee/pc/geno/geno.h:67` |
| GENO_SUB_HBDMG | v5.3: [15:8] hitbox mask, [7] B is a var; word1 = damage (float) | `melee/pc/geno/geno.h:68` |
| GENO_SUB_LINK | v1: [15:8] hitbox mask; word1 = autolink mode (GENO_LINK_*) | `melee/pc/geno/geno.h:69` |
| GENO_SUB_HBSTUN | v5.5: [15:8] hitbox mask, [7] B is a var; word1 = extra hitstun frames (int) | `melee/pc/geno/geno.h:70` |
| GENO_SUB_HBFLAGS | v5.5: [15:8] hitbox mask, [7] B is a var; word1 = GENO_HBF_* contact flags | `melee/pc/geno/geno.h:71` |
| GENO_VAL_AIR | i W: 1 airborne; writing 1 on the ground = become airborne | `melee/pc/geno/geno.h:76` |
| GENO_VAL_FACING | f W: +1 / -1; writing 0 turns around | `melee/pc/geno/geno.h:77` |
| GENO_VAL_VEL_X | f W: self_vel.x | `melee/pc/geno/geno.h:78` |
| GENO_VAL_VEL_Y | f W: self_vel.y | `melee/pc/geno/geno.h:79` |
| GENO_VAL_GROUND_VEL | f W: gr_vel | `melee/pc/geno/geno.h:80` |
| GENO_VAL_FWD_VEL | f W: self_vel.x * facing | `melee/pc/geno/geno.h:81` |
| GENO_VAL_KB_VEL_X | f | `melee/pc/geno/geno.h:82` |
| GENO_VAL_KB_VEL_Y | f | `melee/pc/geno/geno.h:83` |
| GENO_VAL_STICK_X | f | `melee/pc/geno/geno.h:84` |
| GENO_VAL_STICK_Y | f | `melee/pc/geno/geno.h:85` |
| GENO_VAL_STICK_FWD | f: stick x * facing | `melee/pc/geno/geno.h:86` |
| GENO_VAL_CSTICK_X | f | `melee/pc/geno/geno.h:87` |
| GENO_VAL_CSTICK_Y | f | `melee/pc/geno/geno.h:88` |
| GENO_VAL_ANIM_FRAME | f | `melee/pc/geno/geno.h:89` |
| GENO_VAL_ACTION_FRAME | i: frames in this action (1 on its first frame) | `melee/pc/geno/geno.h:90` |
| GENO_VAL_MOTION | i: motion (action state) id | `melee/pc/geno/geno.h:91` |
| GENO_VAL_PERCENT | f | `melee/pc/geno/geno.h:92` |
| GENO_VAL_JUMPS_USED | i W | `melee/pc/geno/geno.h:93` |
| GENO_VAL_BUTTONS_HELD | i: GENO_BTN_* mask | `melee/pc/geno/geno.h:95` |
| GENO_VAL_BUTTONS_PRESSED | i: GENO_BTN_* mask, this frame | `melee/pc/geno/geno.h:96` |
| GENO_VAL_POS_X | f | `melee/pc/geno/geno.h:97` |
| GENO_VAL_POS_Y | f | `melee/pc/geno/geno.h:98` |
| GENO_VAL_CMD_VAR0 | i W: fp->cmd_vars[0..3] = 0x17..0x1A | `melee/pc/geno/geno.h:99` |
| GENO_VAL_CMD_VAR3 | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:100` |
| GENO_VAL_ANIM_RATE | f W (v5.2): animation + script rate (ftAnim_8006F0FC) | `melee/pc/geno/geno.h:101` |
| GENO_VAL_FAST_FALL | i | `melee/pc/geno/geno.h:102` |
| GENO_VAL_TRIGGER | f: analog shield trigger | `melee/pc/geno/geno.h:103` |
| GENO_VAL_GENO_STATE | i: the Geno state the fighter is in (index), -1 when none | `melee/pc/geno/geno.h:105` |
| GENO_VAL_MOVE_F0 | f W: 0x20..0x27 behaviour floats (glide angle/speed, ...) | `melee/pc/geno/geno.h:106` |
| GENO_VAL_MOVE_F7 | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:107` |
| GENO_VAL_MOVE_I0 | i W: 0x28..0x2F behaviour ints (timers, counters) | `melee/pc/geno/geno.h:108` |
| GENO_VAL_MOVE_I7 | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:109` |
| GENO_VAL_LEDGE | i W: this action's ledge grab (PSA Allow/Disallow Ledgegrab): | `melee/pc/geno/geno.h:111` |
| GENO_VAL_HIDDEN | i W: 1 = the whole fighter is not drawn (model, shadow; | `melee/pc/geno/geno.h:113` |
| GENO_VAL_TRANSN_FWD | f: this frame's root motion (TransN), forward | `melee/pc/geno/geno.h:115` |
| GENO_VAL_TRANSN_UP | f: this frame's root motion (TransN), up | `melee/pc/geno/geno.h:116` |
| GENO_VAL_MOTION_GRAVITY | f W: this action's root-motion gravity multiplier (PSA | `melee/pc/geno/geno.h:117` |
| GENO_VAL_HIT_DAMAGE | f: damage of the last hit taken (before a counter negated it) | `melee/pc/geno/geno.h:120` |
| GENO_VAL_HIT_PORT | i: the attacker's port (0-5) of the last hit, -1 unknown | `melee/pc/geno/geno.h:121` |
| GENO_VAL_HIT_COUNTER | i: 1 when the last hit landed in a counter window | `melee/pc/geno/geno.h:122` |
| GENO_VAL_ARTICLES | i: this fighter's Geno articles alive now | `melee/pc/geno/geno.h:124` |
| GENO_VAL_ATTACK_CONNECTED | i W (v5.3): a hitbox of this fighter hit a fighter in this | `melee/pc/geno/geno.h:125` |
| GENO_VAL_ATTACK_CONNECTED_PREV | i (v5.3): ATTACK_CONNECTED as the previous action ended | `melee/pc/geno/geno.h:127` |
| GENO_VAL_STICK_LEN | f (v5.4): the stick vector's length, the test Ultimate's status code makes | `melee/pc/geno/geno.h:128` |
| GENO_VAL_FALL_LIMIT | f W (v5.4): this action's fall-speed limit in place of terminal velocity; 0 = the fighter's | `melee/pc/geno/geno.h:129` |
| GENO_VAL_SPECIAL_F | + word index: fp->dat_attrs word as float | `melee/pc/geno/geno.h:131` |
| GENO_VAL_SPECIAL_I | + word index: fp->dat_attrs word as int | `melee/pc/geno/geno.h:132` |
| GENO_BTN_ATTACK | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:137` |
| GENO_BTN_SPECIAL | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:138` |
| GENO_BTN_JUMP | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:139` |
| GENO_BTN_SHIELD | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:140` |
| GENO_BTN_GRAB | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:141` |
| GENO_BTN_TAUNT | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:142` |
| GENO_COND_ALWAYS | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:147` |
| GENO_COND_ANIM_END | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:148` |
| GENO_COND_GROUND | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:149` |
| GENO_COND_AIR | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:150` |
| GENO_COND_PRESSED | arg1 GENO_BTN_* mask | `melee/pc/geno/geno.h:151` |
| GENO_COND_HELD | arg1 GENO_BTN_* mask | `melee/pc/geno/geno.h:152` |
| GENO_COND_BIT | arg1 var ref, arg2 bit | `melee/pc/geno/geno.h:153` |
| GENO_COND_VAR | arg1 var ref A, cmp, arg2 B | `melee/pc/geno/geno.h:154` |
| GENO_COND_FRAME | animation frame >= arg1 | `melee/pc/geno/geno.h:155` |
| GENO_COND_VALUE | arg1 GENO_VAL_*, cmp, arg2 B | `melee/pc/geno/geno.h:156` |
| GENO_TGT_MOTION | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:166` |
| GENO_TGT_SPECIAL | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:167` |
| GENO_TGT_GENO | a Geno state (v2): id = index in the profile's "states" list | `melee/pc/geno/geno.h:168` |
| GENO_TGT_AUTO | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:170` |
| GENO_TGT_HELPLESS | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:171` |
| GENO_TGT_STAY | v3 "stay" ("land": landing only grounds; the state goes on) | `melee/pc/geno/geno.h:172` |
| GENO_TGT_RAW | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:173` |
| GENO_TGT_KEEP_FRAME | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:174` |
| GENO_HBF_NO_HITLAG | no hitlag for the victim or the attacker | `melee/pc/geno/geno.h:181` |
| GENO_HBF_FLINCHLESS | the damage lands; no knockback, no damage state | `melee/pc/geno/geno.h:182` |
| GENO_HBF_ZERO_DAMAGE | the hit adds no damage (a detector / sensor hit) | `melee/pc/geno/geno.h:183` |
| GENO_HBF_FORCE_REACTION | the victim reacts even when its state would not (no_kb) | `melee/pc/geno/geno.h:184` |
| GENO_LINK_OFF | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:187` |
| GENO_LINK_DIRECTION | launch along the attacker's momentum, Melee knockback | `melee/pc/geno/geno.h:188` |
| GENO_LINK_SPEED | ... and at least the attacker's speed | `melee/pc/geno/geno.h:189` |
| GENO_CMP_EQ | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:193` |
| GENO_CMP_NE | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:194` |
| GENO_CMP_LT | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:195` |
| GENO_CMP_LE | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:196` |
| GENO_CMP_GT | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:197` |
| GENO_CMP_GE | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:198` |
| GENO_CMP_BIT | A & (1 << B) | `melee/pc/geno/geno.h:199` |
| GENO_CMP_NOBIT | !(A & (1 << B)) | `melee/pc/geno/geno.h:200` |
| GENO_HOOK_NONE | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:219` |
| GENO_HOOK_LOG | "geno.log": log arg and the first LA vars (debugging) | `melee/pc/geno/geno.h:220` |
| GENO_HOOK_JUMPS_REFILL | "geno.jumps.refill": give back arg air jumps (0 = all) | `melee/pc/geno/geno.h:221` |
| GENO_HOOK_JUMPS_TO_VAR | "geno.jumps.to_var": LA int var[arg] = air jumps left | `melee/pc/geno/geno.h:222` |
| GENO_HOOK_COUNT_FRAMES | "geno.count_frames": LA int var[arg] += 1 | `melee/pc/geno/geno.h:223` |
| GENO_HOOK_ARTICLE_SPAWN | v5 "geno.article.spawn": spawn the profile's article arg | `melee/pc/geno/geno.h:224` |
| GENO_HOOK_LOCKON | v5.2 "geno.lockon": aim at the nearest other fighter -> MOVE_F0/F1/I0 | `melee/pc/geno/geno.h:225` |
| GENO_HOOK_AIM_STICK | v5.3 "geno.aim_stick": heading from the stick's polar angle -> MOVE_F0/F1 | `melee/pc/geno/geno.h:226` |
| GENO_HOOK_DASH_SEARCH | v5.4 "geno.dash.search": one frame of an aim window -> MOVE_I0/I1 target, MOVE_F2/F3/I2 stick | `melee/pc/geno/geno.h:227` |
| GENO_HOOK_DASH_AIM | v5.4 "geno.dash.aim": the window's result -> MOVE_F0/F1 world heading, MOVE_I3 up/down, facing | `melee/pc/geno/geno.h:228` |
| GENO_HOOK_BRAKE | v5.4 "geno.brake": clamp, then decelerate the fighter's own velocity along itself | `melee/pc/geno/geno.h:229` |
| GENO_EV_INIT | spawn and respawn, after the state block is reset | `melee/pc/geno/geno.h:236` |
| GENO_EV_FRAME | every frame, after the m-ex onFrame dispatch | `melee/pc/geno/geno.h:237` |
| GENO_EV_ACTION | action state change, after the RA banks are cleared | `melee/pc/geno/geno.h:238` |
| GENO_EV_LAND | v1: the moment of landing (inside the collision callback) | `melee/pc/geno/geno.h:239` |
| GENO_EV_HIT | v5: the fighter was hit (Fighter_ProcessHit, before the damage reaction); | `melee/pc/geno/geno.h:240` |
| GENO_EV_MAX_HOOKS | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:244` |
| GENO_CB_ANIM | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:270` |
| GENO_CB_IASA | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:270` |
| GENO_CB_PHYS | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:270` |
| GENO_CB_COLL | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:270` |
| GENO_CB_LIKE | "like": the like-motion's own callback for that slot | `melee/pc/geno/geno.h:271` |
| GENO_BHV_NONE | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:275` |
| GENO_BHV_AIR | "geno.air": aerial state, gravity + drift, anim end -> next | `melee/pc/geno/geno.h:276` |
| GENO_BHV_GROUND | "geno.ground": grounded state, friction, anim end -> next | `melee/pc/geno/geno.h:277` |
| GENO_BHV_ANIM_MOTION | v3 "geno.anim_motion": moved by the clip's root motion (TransN), | `melee/pc/geno/geno.h:278` |
| GENO_BHV_GLIDE_START | "geno.glide.start" | `melee/pc/geno/geno.h:280` |
| GENO_BHV_GLIDE | "geno.glide" | `melee/pc/geno/geno.h:281` |
| GENO_BHV_GLIDE_ATTACK | "geno.glide.attack" | `melee/pc/geno/geno.h:282` |
| GENO_BHV_GLIDE_LANDING | "geno.glide.landing" | `melee/pc/geno/geno.h:283` |
| GENO_BHV_GLIDE_END | "geno.glide.end" | `melee/pc/geno/geno.h:284` |
| GENO_BHV_TORNADO | "geno.tornado": Mach Tornado (tap B to rise, drift, multi-hit) | `melee/pc/geno/geno.h:285` |
| GENO_BHV_DRILL | "geno.drill": Drill Rush (steered dash, bounce on hit / wall) | `melee/pc/geno/geno.h:286` |
| GENO_BHV_DRILL_END | "geno.drill.end": the flip after the rush | `melee/pc/geno/geno.h:287` |
| GENO_BHV_DRILL_START | "geno.drill.start": the wind-up before the rush (optional) | `melee/pc/geno/geno.h:288` |
| GENO_BHV_CAPE | v3 "geno.cape": Dimensional Cape start + vanish (stick-steered) | `melee/pc/geno/geno.h:289` |
| GENO_BHV_CAPE_ATTACK | v3 "geno.cape.attack": a reappear with the slash (root motion); | `melee/pc/geno/geno.h:290` |
| GENO_BHV_CAPE_END | v3 "geno.cape.end": the reappear without the slash; 2 in order: | `melee/pc/geno/geno.h:292` |
| GENO_P_GLIDE_W0 | glide.w00..w21: Brawl's Misc Glide block, 0x00..0x15 | `melee/pc/geno/geno.h:302` |
| GENO_P_GLIDE_HOLD | glide.hold_frames: jump held this long in an air jump | `melee/pc/geno/geno.h:303` |
| GENO_P_GLIDE_FROM_JUMP | glide.from_ground_jump: 1 = the ground jump counts too | `melee/pc/geno/geno.h:304` |
| GENO_P_GLIDE_END_HELPLESS | glide.end_helpless: 1 = GlideEnd -> FallSpecial | `melee/pc/geno/geno.h:305` |
| GENO_P_GLIDE_LANDING_LAG | glide.landing_lag: GlideAttack's landing lag (frames) | `melee/pc/geno/geno.h:306` |
| GENO_P_GLIDE_ENTRY | glide.entry: 0 = no jump-hold entry (scripts only) | `melee/pc/geno/geno.h:307` |
| GENO_P_GLIDE_MAX_FRAMES | glide.max_frames: a time limit (0 = none, as Brawl) | `melee/pc/geno/geno.h:308` |
| GENO_P_GLIDE_POSE | glide.pose_center: pose frame = this - angle (0 = off) | `melee/pc/geno/geno.h:309` |
| GENO_P_GLIDE_END_BUTTONS | glide.end_buttons: GENO_BTN_* mask that ends the glide | `melee/pc/geno/geno.h:310` |
| GENO_P_TORNADO_W0 | tornado.w00..w19: Brawl paramSpecialN, 0x20..0x33 | `melee/pc/geno/geno.h:311` |
| GENO_P_TORNADO_MAX_SPEED | tornado.max_speed: hard horizontal cap (Brawl 2.5) | `melee/pc/geno/geno.h:312` |
| GENO_P_TORNADO_END_HELPLESS | tornado.end_helpless: air end -> FallSpecial | `melee/pc/geno/geno.h:313` |
| GENO_P_TORNADO_SPIN_ANIM | v4 tornado.spin_anim: the spin clip plays at spin_anim x the | `melee/pc/geno/geno.h:314` |
| GENO_P_TORNADO_SPIN_PERIOD | v4 tornado.spin_period: the clip loops at this frame (MK 360: | `melee/pc/geno/geno.h:317` |
| GENO_P_DRILL_W0 | drill.w00..w05: Brawl paramSpecialS, 0x40..0x45 | `melee/pc/geno/geno.h:319` |
| GENO_P_DRILL_SPEED | drill.speed: travel speed when the clip has no root motion | `melee/pc/geno/geno.h:320` |
| GENO_P_DRILL_BOUNCE | drill.bounce: 1 wall  /  2 hit  /  4 shield -> DrillEnd at once | `melee/pc/geno/geno.h:322` |
| GENO_P_DRILL_POP_VX | drill.pop_vx: DrillEnd's backward pop (Brawl 1.0) | `melee/pc/geno/geno.h:323` |
| GENO_P_DRILL_POP_VY | drill.pop_vy: DrillEnd's upward pop (Brawl 2.1) | `melee/pc/geno/geno.h:324` |
| GENO_P_DRILL_END_HELPLESS | drill.end_helpless: 1 = FallSpecial unless it hit | `melee/pc/geno/geno.h:325` |
| GENO_P_DRILL_PITCH_MODEL | v4 drill.pitch_model: 1 = the model (TopN) turns with the | `melee/pc/geno/geno.h:326` |
| GENO_P_GLIDE_SCRIPT_HELPLESS | glide.script_entry_helpless: a Glide entered straight | `melee/pc/geno/geno.h:330` |
| GENO_P_CAPE_W0 | cape.w00..w05: Brawl paramSpecialLw (ids 4021-4026), 0x58..0x5D | `melee/pc/geno/geno.h:333` |
| GENO_P_CAPE_STEER_FRAME | cape.steer_frame: the vanish (stick steering) starts (12) | `melee/pc/geno/geno.h:334` |
| GENO_P_CAPE_DECIDE_FRAME | cape.decide_frame: the reappear is chosen (26) | `melee/pc/geno/geno.h:335` |
| GENO_P_CAPE_NEUTRAL_X | cape.neutral_x:  / stick x /  below it = the neutral reappear | `melee/pc/geno/geno.h:336` |
| GENO_P_CAPE_BUTTONS | cape.attack_buttons: GENO_BTN mask held = the slash (B  /  A) | `melee/pc/geno/geno.h:337` |
| GENO_AP_LIFETIME | frames alive (the article despawns after it); 0 = 60 | `melee/pc/geno/geno.h:379` |
| GENO_AP_VEL_FWD | initial velocity along the facing | `melee/pc/geno/geno.h:380` |
| GENO_AP_VEL_UP | initial velocity up | `melee/pc/geno/geno.h:381` |
| GENO_AP_GRAVITY | vy -= gravity every frame | `melee/pc/geno/geno.h:382` |
| GENO_AP_MAX_FALL | vy >= -max_fall (0 = no cap) | `melee/pc/geno/geno.h:383` |
| GENO_AP_ACCEL | speed += accel every frame, along the travel direction | `melee/pc/geno/geno.h:384` |
| GENO_AP_MAX_SPEED |  / v /  cap (0 = none) | `melee/pc/geno/geno.h:385` |
| GENO_AP_HOMING_TURN | degrees a frame the travel turns toward the nearest opponent | `melee/pc/geno/geno.h:386` |
| GENO_AP_HOMING_RANGE | only opponents nearer than this (0 = any distance) | `melee/pc/geno/geno.h:387` |
| GENO_AP_HOMING_DELAY | frames before the homing starts | `melee/pc/geno/geno.h:388` |
| GENO_AP_SPAWN_FWD | spawn offset from the fighter's position, along the facing | `melee/pc/geno/geno.h:389` |
| GENO_AP_SPAWN_UP | spawn offset, up | `melee/pc/geno/geno.h:390` |
| GENO_AP_SCALE | model scale (0 = 1) | `melee/pc/geno/geno.h:391` |
| GENO_AP_DESPAWN | int: GENO_ART_DESPAWN_* mask (default hit  /  shield  /  stage) | `melee/pc/geno/geno.h:392` |
| GENO_AP_SPIN | model spin, degrees a frame about the travel axis (visual only) | `melee/pc/geno/geno.h:393` |
| GENO_AP_MAX_LIVE | int: at most this many of this article per fighter (0 = 4) | `melee/pc/geno/geno.h:394` |
| GENO_AP_MIN_SPEED | a negative accel (a brake) stops at this speed | `melee/pc/geno/geno.h:396` |
| GENO_AP_BONE | int: spawn at this fighter part (bone) + the offset; -1 = position | `melee/pc/geno/geno.h:397` |
| GENO_AP_EFFECT | int: Melee effect id attached to the article at spawn (efAsync), 0 none | `melee/pc/geno/geno.h:398` |
| GENO_AP_SPAWN_N | int: number of "spawns" variants | `melee/pc/geno/geno.h:399` |
| GENO_AP_SPAWN_V | 20..27: variant v's [forward, up] = 20 + 2v, 21 + 2v | `melee/pc/geno/geno.h:400` |
| GENO_AP_CHILD | 28..37: child c: article 28+5c, frame +1, every +2, count +3, | `melee/pc/geno/geno.h:401` |
| GENO_AP_ANGLE | degrees the initial velocity is turned (up, in the facing), added to | `melee/pc/geno/geno.h:403` |
| GENO_AP_FX | v5.4 int: "fx" - Geno effect package (docs/geno.md 20) + 1, attached to the | `melee/pc/geno/geno.h:405` |
| GENO_AP_EFFECTS | v5.2 40..47: "effects" - up to 8 effect ids attached at spawn | `melee/pc/geno/geno.h:407` |
| GENO_AP_EFFECT_AT | v5.3 48..55: effect e's [15:0] article frame it attaches at (0 = spawn), | `melee/pc/geno/geno.h:410` |
| GENO_AP_SPINS | v5.3 56..63: "spins" - 4 x (joint index, radians a frame about its Z, float bits): | `melee/pc/geno/geno.h:414` |
| GENO_ART_DESPAWN_HIT | its hitbox hit a fighter / item | `melee/pc/geno/geno.h:419` |
| GENO_ART_DESPAWN_SHIELD | it hit a shield | `melee/pc/geno/geno.h:420` |
| GENO_ART_DESPAWN_STAGE | it touched the stage (a wall, floor or ceiling on its path) | `melee/pc/geno/geno.h:421` |
| GENO_ART_DESPAWN_CLANK | it clanked with another hitbox | `melee/pc/geno/geno.h:422` |
| GENO_AH_DAMAGE | float | `melee/pc/geno/geno.h:427` |
| GENO_AH_SIZE | float (radius) | `melee/pc/geno/geno.h:428` |
| GENO_AH_OFF_X | float: offset from the article's root joint | `melee/pc/geno/geno.h:429` |
| GENO_AH_OFF_Y | float | `melee/pc/geno/geno.h:430` |
| GENO_AH_OFF_Z | float | `melee/pc/geno/geno.h:431` |
| GENO_AH_ANGLE | Melee angle (361 = Sakurai) | `melee/pc/geno/geno.h:432` |
| GENO_AH_KBG | knockback growth | `melee/pc/geno/geno.h:433` |
| GENO_AH_WKB | weight-set knockback | `melee/pc/geno/geno.h:434` |
| GENO_AH_BKB | base knockback | `melee/pc/geno/geno.h:435` |
| GENO_AH_ELEMENT | HitElement: 0 normal, 1 fire, 2 electric, 3 slash, 4 coin, 5 ice ... | `melee/pc/geno/geno.h:436` |
| GENO_AH_SHIELD_DAMAGE | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:437` |
| GENO_AH_SFX_SEVERITY | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:438` |
| GENO_AH_SFX_KIND | Typed definition/script word ? native interpreter/state/article executor. | `melee/pc/geno/geno.h:439` |
| GENO_AH_START | first active frame of the article's life (1-based) | `melee/pc/geno/geno.h:440` |
| GENO_AH_END | last active frame (0 = the whole lifetime) | `melee/pc/geno/geno.h:441` |
| GENO_AH_FLAGS | GENO_AHF_* (default: all but none) | `melee/pc/geno/geno.h:442` |
| GENO_AH_SLOT | v5.1: Melee hitbox slot 0-3 (default: the entry's index mod 4) | `melee/pc/geno/geno.h:443` |
| GENO_AH_STUN | v5.5: extra hitstun frames a hit gives (int; HBSTUN for articles) | `melee/pc/geno/geno.h:444` |
| GENO_AHF_GROUND | hits grounded fighters | `melee/pc/geno/geno.h:447` |
| GENO_AHF_AIR | hits airborne fighters | `melee/pc/geno/geno.h:448` |
| GENO_AHF_REFLECT | can be reflected | `melee/pc/geno/geno.h:449` |
| GENO_AHF_ABSORB | can be absorbed | `melee/pc/geno/geno.h:450` |
| GENO_AHF_COUNTER | can be countered (Marth's / Geno's counter windows, shields) | `melee/pc/geno/geno.h:451` |

### 6G. Geno authoring schema literal enums

Authoring tooling PRODUCES; loader/callback validation CONSUMES. This is the attach authoring vocabulary as well as in-flight define fields; define admits a narrower slice. Arbitrary state/model/source names remain open namespaces.

| Literal | Schema context | Evidence |
|---|---|---|
| air | /fighters/items/common_states/items/phys, /fighters/items/common_states/items/coll | `tools/geno/geno.schema.json:151` |
| air_drift | /fighters/items/common_states/items/phys, /fighters/items/states/items/phys | `tools/geno/geno.schema.json:153` |
| air_nodrift | /fighters/items/common_states/items/phys, /fighters/items/states/items/phys | `tools/geno/geno.schema.json:152` |
| air_noledge | /fighters/items/common_states/items/coll, /fighters/items/states/items/coll | `tools/geno/geno.schema.json:180` |
| anim_motion | /fighters/items/common_states/items/phys, /fighters/items/common_states/items/coll | `tools/geno/geno.schema.json:157` |
| auto | /fighters/items/common_states/items/phys, /fighters/items/states/items/phys | `tools/geno/geno.schema.json:156` |
| both | /fighters/items/common_states/items/coll, /fighters/items/states/items/ledge/anyOf/0 | `tools/geno/geno.schema.json:183` |
| brake | /fighters/items/common_states/items/phys, /fighters/items/states/items/phys | `tools/geno/geno.schema.json:154` |
| cape | /fighters/items/common_states/items/anim, /fighters/items/common_states/items/phys | `tools/geno/geno.schema.json:125` |
| cape.after | /fighters/items/common_states/items/coll, /fighters/items/states/items/coll | `tools/geno/geno.schema.json:177` |
| drill | /fighters/items/common_states/items/anim, /fighters/items/common_states/items/phys | `tools/geno/geno.schema.json:122` |
| drill.end | /fighters/items/common_states/items/anim, /fighters/items/common_states/items/phys | `tools/geno/geno.schema.json:123` |
| drill.start | /fighters/items/common_states/items/phys, /fighters/items/common_states/items/coll | `tools/geno/geno.schema.json:165` |
| entry | /fighters/items/states/items/facing | `tools/geno/geno.schema.json:780` |
| front | /fighters/items/states/items/ledge/anyOf/0 | `tools/geno/geno.schema.json:735` |
| geno.air | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:600` |
| geno.anim_motion | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:602` |
| geno.cape | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:611` |
| geno.cape.attack | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:612` |
| geno.cape.end | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:613` |
| geno.drill | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:609` |
| geno.drill.end | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:610` |
| geno.drill.start | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:614` |
| geno.glide | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:604` |
| geno.glide.attack | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:605` |
| geno.glide.end | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:607` |
| geno.glide.landing | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:606` |
| geno.glide.start | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:603` |
| geno.ground | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:601` |
| geno.tornado | /fighters/items/states/items/behavior | `tools/geno/geno.schema.json:608` |
| glide | /fighters/items/common_states/items/anim, /fighters/items/common_states/items/iasa | `tools/geno/geno.schema.json:120` |
| glide.after | /fighters/items/common_states/items/anim, /fighters/items/states/items/anim | `tools/geno/geno.schema.json:124` |
| glide.attack | /fighters/items/common_states/items/phys, /fighters/items/states/items/phys | `tools/geno/geno.schema.json:160` |
| glide.end | /fighters/items/common_states/items/phys, /fighters/items/states/items/phys | `tools/geno/geno.schema.json:161` |
| glide.start | /fighters/items/common_states/items/anim, /fighters/items/common_states/items/phys | `tools/geno/geno.schema.json:119` |
| ground | /fighters/items/common_states/items/phys, /fighters/items/common_states/items/coll | `tools/geno/geno.schema.json:155` |
| ground_stop | /fighters/items/common_states/items/coll, /fighters/items/states/items/coll | `tools/geno/geno.schema.json:182` |
| hold | /fighters/items/common_states/items/anim, /fighters/items/states/items/anim | `tools/geno/geno.schema.json:118` |
| interrupt | /fighters/items/common_states/items/iasa, /fighters/items/states/items/iasa | `tools/geno/geno.schema.json:136` |
| like | /fighters/items/common_states/items/anim, /fighters/items/common_states/items/iasa | `tools/geno/geno.schema.json:72` |
| loop | /fighters/items/common_states/items/anim, /fighters/items/states/items/anim | `tools/geno/geno.schema.json:117` |
| next | /fighters/items/common_states/items/anim, /fighters/items/states/items/anim | `tools/geno/geno.schema.json:116` |
| none | /fighters/items/common_states/items/iasa, /fighters/items/common_states/items/phys | `tools/geno/geno.schema.json:137` |
| tornado | /fighters/items/common_states/items/anim, /fighters/items/common_states/items/phys | `tools/geno/geno.schema.json:121` |

### 6H. Retail element inspection and parser field inventories

| Element name | Produces ? consumes | Gap | Evidence |
|---|---|---|---|
| normal | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| fire | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| electric | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| slash | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| coin | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| ice | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| nap | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| sleep | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| catch | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| ground | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| cape | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| inert | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| disable | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| dark | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| scball | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| lipstick | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |
| leadead | Retail numeric element ? hitbox/hit inspection | Not automatically legal ordinary rule conversion or modifier tag | `melee/pc/platform/gw_script.c:8271` |

| Parser namespace | Fields/literal enums | Evidence |
|---|---|---|
| gs_hr_moves | unknown, jab, dash_attack, tilt, smash, aerial, grab, throw, special, projectile | `melee/pc/platform/gw_script_hit_rules.inc:13` |
| top | id, match, change | `melee/pc/platform/gw_script_hit_rules.inc:33` |
| match | move, grounded, element, status_bits, incoming | `melee/pc/platform/gw_script_hit_rules.inc:34` |
| change | element, damage, knockback_growth, knockback_base, shield_damage, hitstun, knockback_taken, percent_damage, launch | `melee/pc/platform/gw_script_hit_rules.inc:35` |
| mult | damage, knockback_growth, knockback_base, knockback_taken, percent_damage, launch | `melee/pc/platform/gw_script_hit_rules.inc:36` |
| keys | damage, knockback_growth, knockback_base, knockback_taken, percent_damage, launch | `melee/pc/platform/gw_script_hit_rules.inc:133` |
| names | left_hand, right_hand, left_foot, right_foot, head | `melee/pc/platform/gw_script_motion.inc:39` |
| keys | port, sub, anchor, copies, spacing, lifetime, length, smoothing, blend, trigger, flag, follow, clear_on_respawn, surface, shader, depth, speed, scale, fade, width, taper, intensity, params, offset, tint, tail, edge | `melee/pc/platform/gw_script_motion.inc:47` |
| blends | alpha, additive | `melee/pc/platform/gw_script_motion.inc:48` |
| shaders | solid, glow, fire, electric, frost, dark | `melee/pc/platform/gw_script_motion.inc:49` |
| akeys | joint, hitbox, item | `melee/pc/platform/gw_script_motion.inc:67` |
| gs_item_colours | red, green, blue, yellow, white | `melee/pc/platform/gw_script_items.inc:29` |
| keys | vanilla, mex | `melee/pc/platform/gw_script_items.inc:121` |
| option_keys | vx, vy, payload | `melee/pc/platform/gw_script_items.inc:199` |
| payload_keys | colour, amount | `melee/pc/platform/gw_script_items.inc:200` |
| keys | shield, air_dodge, run, grab, specials | `melee/pc/platform/gw_script_fighter_caps.inc:42` |
| kinds | intangible, invincible, metal, size | `melee/pc/platform/gw_script_fighter_caps.inc:80` |
| gs_armor_types | knockback, damage_threshold, knockback_threshold, super, hit_count, damage_pool | `melee/pc/platform/gw_script_fighter_caps_armor.inc:7` |
| names | any, front, back | `melee/pc/platform/gw_script_fighter_caps_armor.inc:67` |
| gs_zone_hooks | on_zone_enter, on_zone_exit, on_zone_none, on_zone_some | `melee/pc/platform/gw_script_zones.inc:21` |
| coords | x0, y0, x1, y1 | `melee/pc/platform/gw_script_zones.inc:72` |

### 6I. Additional Lua module executor/lifecycle anchors

| Producer/consumer/executor | Evidence |
|---|---|
|  function L.new(pool,config) | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:9` |
|  function L:roll(seed,depth,forced,loop) | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:25` |
|  function L:validate(r) | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:57` |
|  function L:name(r) | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:79` |
|  function L:tooltip(r) | `melee/pc/scripts/examples/envoy/scripts/drive_loot.lua:85` |
|  function B.new(loot,config) | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:6` |
|  function B:slots(context) return self.config.slots or D.mod_progression.slots(context or self.context) end | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:9` |
|  function B:set_context(context) | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:10` |
|  function B:derive(state) | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:13` |
|  function B:validate(s) | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:30` |
|  function B:snapshot() return copy({items=self.items,equipped=self.equipped,keystone=self.keystone,keystones=self.keystones,context=self.context}) end | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:40` |
|  function B:publish(s) | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:41` |
|  function B:restore(s) return self:publish(copy(s)) end | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:49` |
|  function B:give(r) | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:50` |
|  function B:equip(i,slot) | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:55` |
|  function B:unequip(slot) | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:60` |
|  function B:discard(i) if not index(i,#self.items) then return false,'invalid index' end;table.remove(self.items,i);return true end | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:65` |
|  function B:choose_keystone(id) | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:66` |
|  function B:new_run() if self.config.persist then return true end;return self:publish({items={},equipped={}}) end | `melee/pc/scripts/examples/envoy/scripts/drive_bag.lua:74` |
|  function R.core_colour(record) | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:5` |
|  function R.new(g) | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:12` |
|  function R:count() local n=0;for _ in pairs(self.records) do n=n+1 end;return n end | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:17` |
|  function R:spawn(record) | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:18` |
|  function R:visual(h,record,x,y) | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:26` |
|  function R:pickup(e,bag) | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:31` |
|  function R:expire(e) | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:37` |
|  function R:snapshot() return {next_id=self.next_id,records=self.records} end | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:41` |
|  function R:validate(s) | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:42` |
|  function R:restore(s) | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:54` |
|  function R:clear() | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:61` |
|  function R:retry_retired() | `melee/pc/scripts/examples/envoy/scripts/drive_drop.lua:67` |
|  function V.new(g,lab) | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:5` |
|  function V:combined(mods,lab) | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:16` |
|  function V:view() | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:32` |
|  function V:reserved() return math.max(#self.bag.items,#self:view().items)+self.drops:count() end | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:37` |
|  function V:queue(op,a,b) | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:38` |
|  function V:command(arg) | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:46` |
|  function V:apply() | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:62` |
|  function V:budget_lines() | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:73` |
|  function V:delta(index,slot) | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:80` |
|  function V:pickup(e) | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:95` |
|  function V:snapshot() return {bag=self.bag:snapshot(),drops=self.drops:snapshot(),pending=self.pending,seed=self.seed} end | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:99` |
|  function V:validate(s,lab) | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:100` |
|  function V:publish(s) | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:120` |
|  function V:restore(s) self:publish(self:validate(s)) | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:124` |
|  function V:clear() | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:126` |
|  function V:has_build() return next(self.bag.equipped)~=nil or self.bag.keystone~=nil or #(self.bag.keystones or {})>0 end | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:130` |
|  function V:tick() | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:131` |
|  function V:frame() self.drops.juice:tick();if self.card_left then self.card_left=self.card_left-1;if self.card_left<=0 then self.card=nil;self.card_left=nil end end end | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:138` |
|  function V:draw() | `melee/pc/scripts/examples/envoy/scripts/drive_lab.lua:139` |
|  function R.new(pool) | `melee/pc/scripts/examples/envoy/scripts/foe_roll.lua:9` |
|  function R:weights(strength) | `melee/pc/scripts/examples/envoy/scripts/foe_roll.lua:14` |
|  function R:construct(rand,context,strength,full) | `melee/pc/scripts/examples/envoy/scripts/foe_roll.lua:18` |
|  function R:evaluate(build,port) | `melee/pc/scripts/examples/envoy/scripts/foe_roll.lua:29` |
|  function R:sample(seed,context) | `melee/pc/scripts/examples/envoy/scripts/foe_roll.lua:35` |
|  function R:exchange(player,foe) | `melee/pc/scripts/examples/envoy/scripts/foe_roll.lua:41` |
|  function R:validate(r) | `melee/pc/scripts/examples/envoy/scripts/foe_roll.lua:68` |
|  function R:roll(strength,seed,stage,port,context,role) | `melee/pc/scripts/examples/envoy/scripts/foe_roll.lua:80` |
|  function F.new(g,lab) | `melee/pc/scripts/examples/envoy/scripts/foe_lab.lua:5` |
|  function F:cpu(p) | `melee/pc/scripts/examples/envoy/scripts/foe_lab.lua:10` |
|  function F:command(arg) | `melee/pc/scripts/examples/envoy/scripts/foe_lab.lua:14` |
|  function F:retire() | `melee/pc/scripts/examples/envoy/scripts/foe_lab.lua:39` |
|  function F:apply() | `melee/pc/scripts/examples/envoy/scripts/foe_lab.lua:49` |
|  function F:frame() for p,label in pairs(self.labels) do label.left=label.left-1;if label.left<=0 then self.labels[p]=nil end end end | `melee/pc/scripts/examples/envoy/scripts/foe_lab.lua:64` |
|  function F:draw() | `melee/pc/scripts/examples/envoy/scripts/foe_lab.lua:65` |
|  function F:snapshot() return clone{seed=self.seed,stage=self.stage,builds=self.builds,pending=self.pending,labels=self.labels} end | `melee/pc/scripts/examples/envoy/scripts/foe_lab.lua:76` |
|  function F:validate(s) | `melee/pc/scripts/examples/envoy/scripts/foe_lab.lua:77` |
|  function F:restore(s) s=self:validate(s);self.seed=s.seed;self.stage=s.stage;self.builds=s.builds;self.pending=s.pending;self.labels=s.labels end | `melee/pc/scripts/examples/envoy/scripts/foe_lab.lua:86` |
|  function F:reset() self.builds={};self.pending={};self.labels={};self.seed=104729;self.stage=0 end | `melee/pc/scripts/examples/envoy/scripts/foe_lab.lua:87` |
|  function X.description(e) | `melee/pc/scripts/examples/envoy/scripts/mod_echo.lua:5` |
|  function X.resolve(e,m,tier) | `melee/pc/scripts/examples/envoy/scripts/mod_echo.lua:18` |
|  function X.engine(engine,p) | `melee/pc/scripts/examples/envoy/scripts/mod_echo.lua:23` |
|  function X.records() | `melee/pc/scripts/examples/envoy/scripts/mod_echo.lua:44` |
|  function A.new(host)return setmetatable({host=host,manual={},owned={},visual={}},A)end | `melee/pc/scripts/examples/envoy/scripts/mod_echo_lab.lua:5` |
|  function A:capable() | `melee/pc/scripts/examples/envoy/scripts/mod_echo_lab.lua:6` |
|  function A:reset() | `melee/pc/scripts/examples/envoy/scripts/mod_echo_lab.lua:9` |
|  function A:command(arg) | `melee/pc/scripts/examples/envoy/scripts/mod_echo_lab.lua:13` |
|  function A:snapshot()return {manual=clone(self.manual),owned=clone(self.owned)}end | `melee/pc/scripts/examples/envoy/scripts/mod_echo_lab.lua:31` |
|  function A:validate(s) | `melee/pc/scripts/examples/envoy/scripts/mod_echo_lab.lua:32` |
|  function A:restore(s) | `melee/pc/scripts/examples/envoy/scripts/mod_echo_lab.lua:40` |
|  function A:ops(ops,players,lost) | `melee/pc/scripts/examples/envoy/scripts/mod_echo_lab.lua:43` |
|  function A:present(players) | `melee/pc/scripts/examples/envoy/scripts/mod_echo_lab.lua:56` |
|  function A:active()return next(self.manual)~=nil or next(self.owned)~=nil end | `melee/pc/scripts/examples/envoy/scripts/mod_echo_lab.lua:71` |
|  function R.roll(c,seed,stage,loop,port,count) | `melee/pc/scripts/examples/envoy/scripts/classic.lua:12` |
|  function R.new(g,profile,commit) | `melee/pc/scripts/examples/envoy/scripts/classic.lua:28` |
|  function R:available() | `melee/pc/scripts/examples/envoy/scripts/classic.lua:31` |
|  function R:save() | `melee/pc/scripts/examples/envoy/scripts/classic.lua:37` |
|  function R:start(mode,fighter,difficulty,stocks,seed) | `melee/pc/scripts/examples/envoy/scripts/classic.lua:41` |
|  function R:clear_mods() | `melee/pc/scripts/examples/envoy/scripts/classic.lua:64` |
|  function R:clear_items() | `melee/pc/scripts/examples/envoy/scripts/classic.lua:70` |
|  function R:stage_start(e) | `melee/pc/scripts/examples/envoy/scripts/classic.lua:77` |
|  function R:spawn(e) | `melee/pc/scripts/examples/envoy/scripts/classic.lua:102` |
|  function R:boss_defeated() if self.active then self.boss=true end end | `melee/pc/scripts/examples/envoy/scripts/classic.lua:108` |
|  function R:stage_clear(e) | `melee/pc/scripts/examples/envoy/scripts/classic.lua:109` |
|  function R:offer_reward(stage,loop,final) | `melee/pc/scripts/examples/envoy/scripts/classic.lua:118` |
|  function R:pick(index) | `melee/pc/scripts/examples/envoy/scripts/classic.lua:128` |
|  function R:acknowledge() | `melee/pc/scripts/examples/envoy/scripts/classic.lua:142` |
|  function R:complete(e) | `melee/pc/scripts/examples/envoy/scripts/classic.lua:148` |
|  function R:retry_save() | `melee/pc/scripts/examples/envoy/scripts/classic.lua:171` |
|  function R:finish(reason) | `melee/pc/scripts/examples/envoy/scripts/classic.lua:175` |
|  function R:game_over() return self:finish('fail') end | `melee/pc/scripts/examples/envoy/scripts/classic.lua:191` |
|  function R:tick() | `melee/pc/scripts/examples/envoy/scripts/classic.lua:192` |
|  function R:item_collect(e) | `melee/pc/scripts/examples/envoy/scripts/classic.lua:206` |
|  function R:physical_tick() | `melee/pc/scripts/examples/envoy/scripts/classic.lua:212` |
|  function R:frame() | `melee/pc/scripts/examples/envoy/scripts/classic.lua:229` |
|  function M.extend(A) | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:4` |
|   function A.new(...) | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:6` |
|   function A:companion() | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:11` |
|   function A:context() | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:14` |
|   function A:start_retail(mode,fighter,difficulty,stocks,seed) | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:20` |
|   function A:command(arg) | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:35` |
|   function A:retail_event(name,e) | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:55` |
|   function A:sync_pause() | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:64` |
|   function A:menu_effect(e) | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:73` |
|   function A:launch(kind,fighter) | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:106` |
|   function A:frame() | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:110` |
|   function A:tick() | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:120` |
|   function A:draw() | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:141` |
|   function A:stop(reason) | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:169` |
|   function A:match_start() if self.retail.active or self.retail.pending then self.models:unload();return end;return old.match_start(self) end | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:178` |
|   function A:match_end() if self.retail.active or self.retail.pending then self.models:unload();self.recolour:clear();return end;return old.match_end(self) end | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:179` |
|   function A:unload() self:stop('quit');return old.unload(self) end | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:180` |
|   function A:enter_hub() | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:181` |
|   function A:item_collect(e) | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:189` |
|   function A:item_expire(e) | `melee/pc/scripts/examples/envoy/scripts/retail_app.lua:193` |

### 6J. All system pairs: matrix and exact mechanisms

R renderer; M modifiers; H hit rules; F fighter ratios; K capabilities/armour; G Geno; I items/drives; E echoes; Z zones/contacts; P 1P; T stage/world; O roster/slots; L LAB. C is source transport (including explicitly in-flight additions); A proposed adapter; S separate execution/storage by design. Direction and lifecycle limits remain in ?3.

| System | R | M | H | F | K | G | I | E | Z | P | T | O | L |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R | ? | C | A | A | A | C | C | C | C | C | C | C | S |
| M | C | ? | C | C | A | A | C | C | A | A | A | A | C |
| H | A | C | ? | C | A | C | C | C | A | A | S | C | C |
| F | A | C | C | ? | A | C | S | C | A | C | C | C | C |
| K | A | A | A | A | ? | A | C | C | A | A | C | C | A |
| G | C | A | C | C | A | ? | C | A | A | C | C | C | C |
| I | C | C | C | S | C | C | ? | S | A | C | C | C | C |
| E | C | C | C | C | C | A | S | ? | A | A | C | C | C |
| Z | C | A | A | A | A | A | A | A | ? | A | C | C | C |
| P | C | A | A | C | A | C | C | A | A | ? | S | C | A |
| T | C | A | S | C | C | C | C | C | C | S | ? | C | C |
| O | C | A | C | C | C | C | C | C | C | C | C | ? | A |
| L | S | C | C | C | A | C | C | C | C | A | C | A | ? |

| Pair | Status | How / why |
|---|---|---|
| R ? M | C | mod_display surface params and chain post |
| R ? H | A | bind effective hit result to tracer |
| R ? F | A | derive ratio/status look |
| R ? K | A | common armour/protection binding |
| R ? G | C | fx_bindings and article effects |
| R ? I | C | native item models and pickup FX |
| R ? E | C | new echo_afterimage/copy style shares ages and armed state; runtime in flight |
| R ? Z | C | contact debug overlay |
| R ? P | C | old retail tint/HUD |
| R ? T | C | stage shader/model/post |
| R ? O | C | fighter port draw routing |
| R ? L | S | clear/refill/rebind presentation, never simulation authority |
| M ? H | C | native_rules?journal hit_rules |
| M ? F | C | budget values?journal fighter_mod |
| M ? K | A | missing schema/budget/armour-capability journal adapter |
| M ? G | A | missing character rule-source adapter |
| M ? I | C | payload?ledger?bag?build |
| M ? E | C | source mod_echo/mod_echo_lab plus echoes journal; generated bundle still behind |
| M ? Z | A | map hooks/poll ring into bounded modifier queue |
| M ? P | A | LAB-only guard and separate Classic director |
| M ? T | A | stage-kind/switch boundary adapter |
| M ? O | A | normalize secondary and source identity |
| M ? L | C | export/import plus sim_commit |
| H ? F | C | both feed retail percent/launch at distinct phases |
| H ? K | A | common status/armour reaction contract |
| H ? G | C | ordinary Geno hitboxes pass collision; tags incomplete |
| H ? I | C | owned item hit rules, ordinary elements only |
| H ? E | C | new normal capsule collision and hit-context routing, in-flight acceptance |
| H ? Z | A | zone predicate via compiled context/status |
| H ? P | A | install same hit rules before replacement CPU logic |
| H ? T | S | rule evaluator independent from stage loader |
| H ? O | C | 12 target entities through sub selector |
| H ? L | C | game BSS and output journal |
| F ? K | A | shared descriptor with distinct ratio/action executors |
| F ? G | C | Geno baseline attrs and effective overlay reads |
| F ? I | S | fighter ratios do not become item attributes |
| F ? E | C | owner percent/launch collision path present; scaling acceptance in flight |
| F ? Z | A | membership rule derives overlay |
| F ? P | C | spawn_1p templates |
| F ? T | C | live fighter carry, scene clear |
| F ? O | C | six port modifier roots |
| F ? L | C | snapshot and fighter_mod journal |
| K ? G | A | deferred Geno armour/setter schema integration |
| K ? I | C | give_item retail pickup path |
| K ? E | C | echo collision targets ordinary damage reaction including armour |
| K ? Z | A | zone-triggered setter requires journal operation |
| K ? P | A | replacement CPU capability/armour templates absent |
| K ? T | C | live fighter binding, scene release |
| K ? O | C | 1..12 independent primary/secondary entities |
| K ? L | A | BSS capture present, Lua setter replay absent |
| G ? I | C | articles are Items; standalone native item backend |
| G ? E | A | character-owned echo rules/history declaration missing |
| G ? Z | A | no Geno membership condition/event |
| G ? P | C | retail callbacks run, shared modifier source absent |
| G ? T | C | retail carry/land/collision callbacks |
| G ? O | C | attach registry, define admission in flight |
| G ? L | C | GenoState/profile game heap; immutable identity required |
| I ? E | S | echo is capsule extension, not another item allocator |
| I ? Z | A | zone membership currently fighters only |
| I ? P | C | old Classic physical stat-drive drops |
| I ? T | C | native scene item teardown; universal carry absent |
| I ? O | C | owner port/item serial, common source ref absent |
| I ? L | C | native heap and Lua ledger; arbitrary spawn replay incomplete |
| E ? Z | A | history locations can query regions but shared predicate absent |
| E ? P | A | no Classic echo modifier host |
| E ? T | C | new scene reset/death history clearing; carry semantics acceptance pending |
| E ? O | C | 12-entity ring and port/sub adapter, in-flight runtime |
| E ? L | C | echoes journal and stable handles now integrated in source; real rewind proof pending |
| Z ? P | A | existing observations lack main-run rule consumers |
| Z ? T | C | zone release on stage switch; contacts inspect geometry identity |
| Z ? O | C | zone port/sub versus primary-only contacts |
| Z ? L | C | zone BSS, host contact ring deliberately separate |
| P ? T | S | retail scene progression and arbitrary stage director retain different machines |
| P ? O | C | primary opponents with spawn generations |
| P ? L | A | host hold/profile outside generic game journal |
| T ? O | C | live carry of primary/secondary fighter objects |
| T ? L | C | stage epoch refuses incompatible snapshot |
| O ? L | A | wide save/online identity incomplete; define boot mapping in flight |

C source evidence: mod_lab.lua frame publication; classic.lua stage_start templates; gw_script_sim_state.inc executor; gw_script_echo_visual.inc age/style binding; ftcoll.c COLL_CAPSULE macros and ScriptGame_EchoReportContext; ftCo_Damage.c ScriptGame_ArmorReact; geno_game_articles.inc native Items; script_stage_slot_carry.inc retained Fighters; gw_script_zones.inc switch release; script_contacts.inc primary observations. Exact declarations are cited in the appendices. A/S cells are architectural inference, not measured engineering estimates.

### 6K. New armour source facts and report

The P2b report appeared during this audit and was read: `_build/tmp/codex-armour-types-report.md:1`. It supersedes the early threshold-only inventory for typed armour, while retaining the independent British-spelling legacy API. Verified by source: six typed slots; direction is any/front/back filter; fixed type order; equality reacts; finite budgets consume even under another protecting type. Hit-count absorbs its last hit then breaks; damage-pool equal/crossing hit breaks through unless another type absorbs. Knockback type subtracts before floor and does not promise no flinch. `on_armor` uses **subfighter**, not `sub`. Frames=0 is persistent configuration, not an earned timed afterimage. State/animation gates do not refill budget. Ordinary selected reaction scope excludes capture/throw/alternate modes; special retail element exclusions retain their mechanics. All this remains SOURCE evidence, no played acceptance.

Geno encoding request is explicit in the report: canonical armor array rows and proposed 32-byte versioned BE row; loader/state entry owns a separate namespace, clears/reinstalls and refills on re-entry. Envoy modifier records are proposals, not accepted schema. Runtime fixture/rewind are unexecuted; stub/syntax checks do not establish integration. Source: `melee/pc/gameworld/script_fighter_caps_armor_core.h:44`, `melee/pc/gameworld/script_fighter_caps_armor.inc:133`, `melee/pc/platform/gw_script_fighter_caps_armor.inc:1`.

## 7. Counts and closing limits

| Inventory | Count |
|---|---|
| callable_script_hooks | 43 |
| internal_stage_signals | 1 |
| GameEvent_producer_sites | 14 |
| native_gd_calls | 278 |
| gd_kit_calls | 12 |
| Lua_helpers | 8 |
| shared_finite_terms | 159 |
| Geno_symbols | 229 |
| Geno_schema_enum_strings | 44 |
| deduplicated_vocabulary_terms | 485 |
| system_pairs | 78 |
| ranked_seams | 18 |
| unification_steps | 8 |

Counts: registrations are exact name/function pairs with aliases; Lua helpers separate and wait_until overlaps a native registration. Hooks exclude tests/player fields; on_action_signal is internal. Vocabulary union is exact spelling across finite shared terms, Geno gameplay symbols, schema literal enums, retail inspection elements and hooks; structural parser property names and arbitrary user IDs are excluded. Counts are not distinct mechanics or proven combinations.

| Active report | Availability |
|---|---|
| _build/tmp/codex-echo-hitboxes-report.md | absent at closing capture |
| _build/tmp/codex-echo-hitboxes-fix1-report.md | absent at closing capture |
| _build/tmp/codex-armour-types-report.md | present and read |
| _build/tmp/codex-geno-define-slice1-report.md | absent at closing capture |

Source SHA256 prefixes at closing capture, not EXE provenance:

| Source | SHA256 prefix |
|---|---|
| melee/pc/platform/gw_script.c | 0c1915ab1d936f75 |
| melee/pc/platform/gw_script_sim_state.inc | 0de60b213257134b |
| melee/pc/gameworld/script_hit_context.inc | 02a752713ff244e8 |
| melee/pc/gameworld/script_echo.inc | 2a47da6283312f35 |
| melee/pc/gameworld/script_fighter_caps_armor.inc | 97f1042d2f6d5f23 |
| melee/pc/platform/geno_define_registry.inc | 56eeb4123079a74b |
| melee/pc/geno/geno.h | b9f3f61066cd5d04 |
| melee/pc/scripts/examples/envoy/scripts/mod_schema.lua | 9a98d4092366d7a3 |
| melee/pc/scripts/examples/envoy/scripts/mod_engine.lua | 591ccd36064516e9 |
| melee/pc/scripts/examples/envoy/scripts/mod_pool.lua | 11aff766c585fc9c |
| melee/pc/scripts/examples/envoy/scripts/mod_display.lua | 3df1d47867122c60 |
| melee/pc/scripts/examples/envoy/scripts/mod_lab.lua | fc60ff9918365683 |
| melee/pc/scripts/examples/envoy/scripts/main.lua | 8e83a3c91f206739 |
| tools/geno/geno.schema.json | ac351702d885ae62 |

Unverified: current EXE/bridge inclusion, real zero-byte rewind, gameplay CPU/sub parity, complete retail rolled-loot loop, earned skill telemetry, six-fighter rendering cost, define stock/mixed match/online admission. Integrator must finish shared integration and bundle regeneration after packets finish, then build/bridge audit and real runtime acceptance. This audit writes only the catalogue and report.

### 6L. Geno authoring names behind the exported symbols

These literal names supplement the exported constant inventory in 6F. They are not added to the 485-term count, which counts the explicitly delimited finite inventories above. Custom state/article/overlay IDs remain open-ended author input. The authoring tools produce these names; native Geno tables consume them. They do not automatically become Envoy modifier predicates or effect descriptors.

| Namespace | Authoring name | Producer / consumer | Source |
|---|---|---|---|
| hooks | `geno.log` | `tools/geno/source.py:39` extractor / `geno_hooks` native table | `melee/pc/geno/geno_game.c:490` |
| hooks | `geno.jumps.refill` | `tools/geno/source.py:39` extractor / `geno_hooks` native table | `melee/pc/geno/geno_game.c:491` |
| hooks | `geno.jumps.to_var` | `tools/geno/source.py:39` extractor / `geno_hooks` native table | `melee/pc/geno/geno_game.c:492` |
| hooks | `geno.count_frames` | `tools/geno/source.py:39` extractor / `geno_hooks` native table | `melee/pc/geno/geno_game.c:493` |
| hooks | `geno.article.spawn` | `tools/geno/source.py:39` extractor / `geno_hooks` native table | `melee/pc/geno/geno_game.c:494` |
| hooks | `geno.lockon` | `tools/geno/source.py:39` extractor / `geno_hooks` native table | `melee/pc/geno/geno_game.c:164` |
| hooks | `geno.aim_stick` | `tools/geno/source.py:39` extractor / `geno_hooks` native table | `melee/pc/geno/geno_game.c:195` |
| hooks | `geno.dash.search` | `tools/geno/source.py:39` extractor / `geno_hooks` native table | `melee/pc/geno/geno_game.c:497` |
| hooks | `geno.dash.aim` | `tools/geno/source.py:39` extractor / `geno_hooks` native table | `melee/pc/geno/geno_game.c:498` |
| hooks | `geno.brake` | `tools/geno/source.py:39` extractor / `geno_hooks` native table | `melee/pc/geno/geno_game.c:499` |
| attrs | `walk_accel_mul` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:883` |
| attrs | `walk_accel_base` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:884` |
| attrs | `walk_max_vel` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:885` |
| attrs | `slow_walk_max` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:886` |
| attrs | `mid_walk_point` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:887` |
| attrs | `fast_walk_min` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:888` |
| attrs | `ground_friction` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:889` |
| attrs | `dash_initial_velocity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:890` |
| attrs | `dash_accel_mul` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:891` |
| attrs | `dash_accel_base` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:892` |
| attrs | `dash_max_velocity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:893` |
| attrs | `run_animation_scaling` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:894` |
| attrs | `max_run_brake_frames` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:895` |
| attrs | `ground_max_horizontal_velocity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:896` |
| attrs | `jump_startup_time` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:897` |
| attrs | `jump_h_initial_velocity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:898` |
| attrs | `jump_v_initial_velocity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:899` |
| attrs | `ground_to_air_jump_momentum_multiplier` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:900` |
| attrs | `jump_h_max_velocity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:901` |
| attrs | `hop_v_initial_velocity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:902` |
| attrs | `air_jump_v_multiplier` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:903` |
| attrs | `air_jump_h_multiplier` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:904` |
| attrs | `max_jumps` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:905` |
| attrs | `gravity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:906` |
| attrs | `terminal_velocity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:907` |
| attrs | `air_drift_stick_mul` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:908` |
| attrs | `aerial_drift_base` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:909` |
| attrs | `air_drift_max` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:910` |
| attrs | `aerial_friction` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:911` |
| attrs | `fast_fall_velocity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:912` |
| attrs | `air_max_horizontal_velocity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:913` |
| attrs | `jab_2_input_window` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:914` |
| attrs | `jab_3_input_window` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:915` |
| attrs | `standing_turn_frames` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:916` |
| attrs | `weight` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:917` |
| attrs | `model_scaling` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:918` |
| attrs | `initial_shield_size` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:919` |
| attrs | `shield_break_initial_velocity` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:920` |
| attrs | `rapid_jab_window` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:921` |
| attrs | `clank_animation_length` | `tools/geno/source.py:39` extractor / `geno_attrs` native table | `melee/pc/geno/geno_game.c:922` |
| behaviors | `geno.air` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:964` |
| behaviors | `geno.ground` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:967` |
| behaviors | `geno.anim_motion` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:970` |
| behaviors | `geno.glide.start` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:973` |
| behaviors | `geno.glide` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:976` |
| behaviors | `geno.glide.attack` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:979` |
| behaviors | `geno.glide.landing` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:982` |
| behaviors | `geno.glide.end` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:985` |
| behaviors | `geno.tornado` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:988` |
| behaviors | `geno.drill` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:991` |
| behaviors | `geno.drill.end` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:994` |
| behaviors | `geno.cape` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:997` |
| behaviors | `geno.cape.attack` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:1000` |
| behaviors | `geno.cape.end` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:1003` |
| behaviors | `geno.drill.start` | `tools/geno/source.py:39` extractor / `geno_bhvs` native table | `melee/pc/geno/geno_game_v2.inc:1006` |
| callbacks | `anim.like` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:7` |
| callbacks | `anim.next` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:490` |
| callbacks | `anim.loop` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:526` |
| callbacks | `anim.hold` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:914` |
| callbacks | `anim.glide.start` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:915` |
| callbacks | `anim.glide` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:55` |
| callbacks | `anim.tornado` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:88` |
| callbacks | `anim.drill` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:114` |
| callbacks | `anim.drill.end` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:919` |
| callbacks | `anim.glide.after` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:920` |
| callbacks | `anim.cape` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:130` |
| callbacks | `iasa.like` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:7` |
| callbacks | `iasa.interrupt` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:426` |
| callbacks | `iasa.none` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:926` |
| callbacks | `iasa.glide` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:55` |
| callbacks | `phys.like` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:7` |
| callbacks | `phys.cape` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:130` |
| callbacks | `phys.none` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:926` |
| callbacks | `phys.air` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:645` |
| callbacks | `phys.air_nodrift` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:930` |
| callbacks | `phys.air_drift` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:553` |
| callbacks | `phys.brake` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:95` |
| callbacks | `phys.ground` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:658` |
| callbacks | `phys.auto` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:603` |
| callbacks | `phys.anim_motion` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:935` |
| callbacks | `phys.glide.start` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:915` |
| callbacks | `phys.glide` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:55` |
| callbacks | `phys.glide.attack` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:938` |
| callbacks | `phys.glide.end` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:939` |
| callbacks | `phys.tornado` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:88` |
| callbacks | `phys.drill` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:114` |
| callbacks | `phys.drill.end` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:919` |
| callbacks | `phys.drill.start` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:943` |
| callbacks | `coll.like` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:7` |
| callbacks | `coll.cape` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:130` |
| callbacks | `coll.cape.after` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:925` |
| callbacks | `coll.none` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:926` |
| callbacks | `coll.air` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:645` |
| callbacks | `coll.air_noledge` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:652` |
| callbacks | `coll.ground` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:658` |
| callbacks | `coll.ground_stop` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:664` |
| callbacks | `coll.both` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:683` |
| callbacks | `coll.anim_motion` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:935` |
| callbacks | `coll.glide` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:55` |
| callbacks | `coll.drill` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:114` |
| callbacks | `coll.drill.start` | `tools/geno/source.py:39` extractor / `geno_cbs` native table | `melee/pc/geno/geno_game_v2.inc:943` |
| params | `glide.angle_max` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:55` |
| params | `glide.angle_min` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:56` |
| params | `glide.start_vy` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:57` |
| params | `glide.start_gravity` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:58` |
| params | `glide.start_vx` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:59` |
| params | `glide.speed` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:60` |
| params | `glide.speed_accel` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:61` |
| params | `glide.max_speed` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:62` |
| params | `glide.stall_speed` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:63` |
| params | `glide.sink_accel` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:64` |
| params | `glide.max_sink` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:65` |
| params | `glide.recover_angle` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:66` |
| params | `glide.dive_angle` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:67` |
| params | `glide.dive_bonus` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:68` |
| params | `glide.deadzone` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:70` |
| params | `glide.pitch_up` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:71` |
| params | `glide.pitch_down` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:72` |
| params | `glide.max_pitch_rate` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:73` |
| params | `glide.stall_pitch` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:74` |
| params | `glide.wing_node` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:75` |
| params | `glide.hold_frames` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:77` |
| params | `glide.from_ground_jump` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:78` |
| params | `glide.end_helpless` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:79` |
| params | `glide.landing_lag` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:80` |
| params | `glide.entry` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:81` |
| params | `glide.max_frames` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:82` |
| params | `glide.pose_center` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:83` |
| params | `glide.end_buttons` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:84` |
| params | `glide.script_entry_helpless` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:127` |
| params | `tornado.entry_vy` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:88` |
| params | `tornado.entry_vx_mul` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:89` |
| params | `tornado.start_rate` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:90` |
| params | `tornado.ground_accel` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:91` |
| params | `tornado.ground_speed` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:92` |
| params | `tornado.air_accel` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:93` |
| params | `tornado.air_speed` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:94` |
| params | `tornado.brake` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:95` |
| params | `tornado.gravity` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:96` |
| params | `tornado.max_fall` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:97` |
| params | `tornado.tap_vy` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:98` |
| params | `tornado.tap_cooldown` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:99` |
| params | `tornado.max_rise` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:100` |
| params | `tornado.tap_rate` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:101` |
| params | `tornado.max_rate` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:102` |
| params | `tornado.rate_decay` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:103` |
| params | `tornado.spin_frames` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:104` |
| params | `tornado.late_decay` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:105` |
| params | `tornado.end_rate` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:106` |
| params | `tornado.max_speed` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:108` |
| params | `tornado.end_helpless` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:109` |
| params | `tornado.spin_anim` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:110` |
| params | `tornado.spin_period` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:111` |
| params | `drill.start_vx_mul` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:114` |
| params | `drill.start_vy` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:115` |
| params | `drill.start_gravity` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:116` |
| params | `drill.steer` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:117` |
| params | `drill.end_frames` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:118` |
| params | `drill.speed` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:120` |
| params | `drill.angle_max` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:121` |
| params | `drill.bounce` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:122` |
| params | `drill.pop_vx` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:123` |
| params | `drill.pop_vy` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:124` |
| params | `drill.end_helpless` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:125` |
| params | `drill.pitch_model` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:126` |
| params | `cape.keep_vx` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:130` |
| params | `cape.keep_vy` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:131` |
| params | `cape.steer_accel_x` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:132` |
| params | `cape.steer_max_x` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:133` |
| params | `cape.steer_accel_y` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:134` |
| params | `cape.steer_max_y` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:135` |
| params | `cape.steer_frame` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:136` |
| params | `cape.decide_frame` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:137` |
| params | `cape.neutral_x` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:138` |
| params | `cape.attack_buttons` | `tools/geno/source.py:39` extractor / `geno_params` native table | `melee/pc/geno/geno_game_v2.inc:139` |

Named attributes are base fighter authoring fields, not a source-keyed temporary stack. Callback names select native adapters; `like` means donor inheritance rather than a callable effect. Parameter aliases `wNN` expose raw words and remain confined to the native behavior family. Hook names are move-script commands, distinct from both Lua `on_*` observations and Geno state-hook dispatch.

LAB documentation context: `melee/docs/geno.md:611` describes delta rewind and `melee/docs/geno.md:656` records prior exactness results. Those are historical acceptance evidence, not proof that the current in-flight echo/armour/define additions are included in the EXE or rewind image.
