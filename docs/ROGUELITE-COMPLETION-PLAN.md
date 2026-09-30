# TBD roguelite completion and polish implementation plan

Planning handoff for Sol-6.1 and DeepSeek, authored by the coordinating agent on 2026-09-30. This document covers the complete offline TBD gamemode, its presentation, and its Windows/Linux delivery. It expands the earlier playable-slice plan into a finite completion contract. It is a plan, not evidence that the work is implemented.

Read this document start to finish before editing. Execute the numbered gates in order; use parallel workers only on the explicitly separable tasks. Keep a working build between gates. The coordinator owns integration and acceptance. A worker completing its patch does not establish completion of the corresponding game feature.

## 1. What 100 percent means

**Feature completion** means every required player-facing system below exists, survives its failure cases, and works together through complete runs on both supported operating systems. A preview, test double, hardcoded demonstration or debug-command-only feature does not qualify.

**Polish completion** means the implemented game passes the separate visual, audio, input, performance, usability and playtesting criteria in section 17. This is a finite quality bar for this version. It cannot honestly mean that no improvement will ever be possible. Human fun/readability evaluation remains a required gate; agents may prepare builds and evidence while the user is away, but must leave that gate pending until somebody actually plays and evaluates it.

Scope includes the offline roguelite, all currently offered stock fighter selections and costumes, the existing Qt launcher integration, Linux/Windows parity for this mode, and regression coverage for the offline base game/custom-content paths we touch. Networking is excluded. Public release tags, GitHub Releases and publication are not authorized. Finish a locally reviewable development package; repository pushes follow the user's existing authorization after integration and validation, without publishing a release.

The game must retain these user decisions:

- Launch through **Load game → Main menu → TBD**. Remain decoupled from the post–Master Hand sequence.
- Play like Melee: movement, spacing, shields, DI, combos, recovery, positioning and ring-outs remain central.
- Combine connected exploration/platforming with branching combat encounters and actual dungeon generation.
- Maintain a permanent genetic collection with breeding, plus run acquisition, upgrades, tradeoffs and fusion.
- Let enemies use the shared gene system, with varied enemy behaviors and clearly communicated buffs.
- Use the existing modular custom models and their authored placement rules. Keep original FD geometry out of the playable presentation; the current isolated host is allowed as internal infrastructure.
- Keep the recursive Kingdom Hearts-inspired command tree. Left/Right/Down select branches at every depth. Up returns one level; only a fresh Up press at the root taunts. Movement and combat controls remain available.
- Keep the combat HUD compact, including the replacement for vanilla stock/percentage display. Use the existing menu kit and restrained, useful notifications.
- Make genes visible on meaningful body/equipment regions, with a showy but readable combination of material treatments and particles.
- Validate normal gameplay at normal simulation speed. The debug fly attack cursor is a diagnostic tool, never evidence of ordinary combat balance or fighter mobility.

## 2. Baseline and source map

Workspace root: `/home/gd/melee_linux_test`.
Tools/documentation repository: `/home/gd/melee_linux_test/gdm`.
Native game checkout: `gdm/melee/worktrees/linux`.
Below, `runtime/` means `melee/worktrees/linux/pc/scripts/examples/roguelite/` relative to `gdm`.

Read these first:

| Source | Why it matters |
| --- | --- |
| `docs/EFFECTS-LAB-PLAN.md` | Confirmed design direction, systems research, AI audit and dungeon research. Historical status paragraphs are dated observations. |
| `tools/roguelite/README.md` | Current installed behavior, tooling, persistence and explicit validation limits. |
| `runtime/core.lua` | Gene resolution, ownership, runtime state, breeding/fusion and strict serialization. |
| `runtime/dungeon.lua` | Current fixed eight-node route and approximate movement screening. This is the generator to replace. |
| `runtime/rooms.lua` | Kit assembly, model caching, ownership and incremental preloading. |
| `runtime/main.lua` | Engine integration, room lifecycle, checkpoint envelope, encounter dispatch and input precedence. |
| `runtime/commands.lua`, `menus.lua`, `feedback.lua` | Existing command latches, menu transactions and compact feedback. |
| `runtime/bindings.lua`, `visuals.lua`, `roster.lua` | Reviewed geometry bindings and current roster/costume handling. |
| `runtime/enemy_genes.lua`, `technical_ai.lua` | Enemy charge/actions and narrow native technical assist. |
| `tools/roguelite/prepare.py` | Lexical module bundle and asset installation. Lua sandbox does not depend on `require`. |
| `tools/roguelite/test_*.py`, `live_acceptance.py` | Existing pure/runtime tests and explicit live fixtures. |
| `melee/worktrees/linux/pc/scripts/examples/bf_interior_room/README.md` | Authored module dimensions, origins, depth and collision contract. |
| `docs/scripting.md`, `_research/roguelite-ai-2026-09-30.md` | Actual native API contracts and AI candidates. |
| `docs/LINUX_PORT_STATUS.md`, `docs/LINUX_CONTINUOUS_CHECKS.md` | Build/package/launcher infrastructure and platform coverage limits. |

Current facts to preserve rather than reimplement:

- The current route has eight fixed room IDs. Seeds swap encounter assignments and offset some platforms; they do not change topology.
- Rooms now use full-size BF floor/wall/door modules, aligned to the kit grid. The main floor spans `[-65,65]`; doorway origins are currently `±52`.
- `gd.stage_isolate(true)` suppresses the supported host's original geometry/collision. Original camera/blast-zone constraints still matter. Loss of isolation must stop gameplay before checkpoint advancement.
- Loading six room models in a single Lua callback exceeded the 50 ms wall-clock budget. The runtime now loads one model per update, constructs the room later, and places fighters on another fresh update. Preserve this separation.
- Cinder, Rime, slot variants, Thermal Shock, shared enemy gene hosts, compact HUD, D-pad tree and collection/run transactions exist in prototype form.
- The native debug attack cursor follows a target and rearms real collision with fresh victim history/attack identity. It has native and live repeat-hit/cleanup evidence.
- The latest v10 baseline recorded 46 targeted native checks and 35 discovered roguelite tests, with additional standalone Lua suites. These are historical baseline results, not automatic passes for future changes.
- The current game can run through XWayland. Earlier package evidence also reports native Wayland startup. Verify the specific final artifact/backend; do not transfer one binary's result to another.

Known traps identified directly in the code:

1. `begin()` regenerates the dungeon from `run.world_seed`. Changing generation would move an existing saved run unless the resolved manifest is persisted/versioned.
2. `Core.new_run()` currently derives its default world seed from `profile.seed`; starting runs does not itself advance that profile seed. Successive runs can repeat unless another collection action changes it. Fix seed allocation deliberately.
3. `Rooms.plan()` whitelists eight room IDs. `setup_enemy()` identifies ReDead using the literal ID `approach`. The live driver contains the same fixed names. All must become data-driven together.
4. Two physical door positions cannot support a branching room with a return route. Real branching/backtracking requires templates with at least three distinct sockets.
5. Core validates exact fields, caps hosts/progress dictionaries at 32 and genes at 128. Its encoder only accepts numeric keys 1–16 and string values up to 256 bytes. Simply attaching a large manifest or 24-element array will fail.
6. Native enemy handles, model IDs and draw selectors are transient. Persist stable logical identities and resolve fresh native handles after loading.
7. Current encounter restart resets native actors. It does not restore exact fighter physics, enemy damage or partial champion progress.
8. A native Adventure enemy disappearing currently unlocks traversal. That behavior can incorrectly turn an escaped required enemy into a completed combat objective.
9. `rogue_state` currently emits `ready` twice with different meanings. Give new diagnostics unambiguous versioned fields such as `runtime_ready` and `ability_ready`.

## 3. Finite content target and design defaults

The following are **proposed implementation targets**, chosen to make this full-version plan executable. They are not claims that the user previously approved these exact counts or balance numbers. Implement them as data/configuration and record any evidence-driven change. Do not quietly reduce them to the old demonstration when work becomes difficult.

| Area | Full-version target |
| --- | --- |
| Run structure | One complete campaign-length run, initially tuned for roughly 20–35 minutes, with 12–18 generated rooms total and an 8–12-room mandatory route. Optional rooms need not all be visited. |
| Dungeon catalogue | At least 16 meaningfully different layouts: 5 traversal, 4 combat, 3 branch/connector, 2 rest/reward, 2 boss-capable. A palette swap or small translation does not count as another layout. Templates may host multiple encounters. |
| Topology | Variable room count and branch placement, optional branches with return paths, deliberate loops/shortcuts, discoveries and occasional optional locks. Mandatory completion requires no randomly acquired gene. |
| Themes | 3 coherent visual/encounter themes built around the existing kit. Distinction must include silhouette/detail/lighting composition, not only a recolour. |
| Genes | 12 mechanically distinct gene definitions across at least 6 readable families; each supports at least 2 mechanically distinct placements. Author and test a compatibility/reaction table rather than all possible pairs. |
| Build choices | At least 24 substantive reward definitions covering improvements, tradeoffs and behavior mutations; at least 6 supported cross-family reactions/synergies. Different numbers on the same reward count as tiers, not new behaviors. |
| Inventory/equipment | At least 6 consumable types and 8 equipment definitions with explicit ownership, slot rules and actual consequences. Equipment need not all introduce a new visible model. |
| Encounters | At least 6 enemy behavior archetypes, spanning fighter CPUs and native/custom non-fighters; at least 12 authored encounter compositions and 3 bosses with distinct phase/positioning demands. Extra HP alone is insufficient. |
| Progression | Complete collection management, breeding, inheritance previews, run fusion, difficulty progression and run history. No infinite collection or unbounded permanent stat inflation. |
| Roster | Every currently offered stock selection and costume works. Cover partners, transformation and owned accessories explicitly; do not present unverified visual coverage as complete. |
| Presentation | All functional screens, onboarding, settings, errors, run endings, event sounds, combat effects and room transitions share a finished visual/audio language. |
| Platforms | A reproducible Windows build and a portable Linux package launched through Qt, with the gameplay and controller evidence described below. |

Suggested family expansion order: stabilize Cinder/Rime first, then add a movement-oriented family, a defensive/impact family, a resource-conversion family and a mark/control family. These are design roles, not final names or permission to implement arbitrary speed multipliers. Write a one-page behavior specification before each family is coded.

Provisional economy rules retain the existing prototype's reversible policy: runs copy collection genes without consuming originals; failure discards run-only improvements; success allows one explicitly previewed inherited-base export; temporary modifiers and ordinary run stat upgrades are not inherited. Offer the player the export choice instead of silently selecting the first equipped slot. A full collection opens a replacement/discard decision instead of silently losing the reward. Breeding must expose costs/outcomes and avoid an unlimited free reroll loop. Keep these rules configurable and label them as defaults until human review.

Pause only in full collection/reward/rest/settings screens. Command navigation remains real-time. Add early command tutorials and configurable prepared branches without changing the user's recursive D-pad grammar. Keep full-scale seamless streaming, multiplayer, an arbitrary user-facing procedural editor and unrestricted mod-script importing outside this finite version.

## 4. Work rules for implementing agents

1. Before editing, inspect both repositories' status and any applicable `AGENTS.md`. The working tree contains substantial prior work. Never reset, clean or overwrite unrelated changes.
2. Record a baseline commit plus dirty-file snapshot/checksums and copy the test profile/checkpoint files to a development backup. Do not use the user's only collection for destructive save tests.
3. Preserve working code through narrow adaptations. Split modules only where the boundary below provides independent tests or ownership.
4. Read the real native function before assuming a Lua API exists. A prototype helper in this plan is a proposed interface until implemented and registered.
5. Pass explicit dependencies to pure modules, for example `Dungeon.new(Catalogue, RNG)`, rather than relying on globals created accidentally by bundle order. Update `prepare.py` and standalone test loaders together.
6. Every task handoff reports files, behavior changed, tests actually run, unresolved limitations and a reproducible live check. Say whether files are frozen before the coordinator builds.
7. A failing old test may reveal an important contract. Replace obsolete fixed-route assumptions with equivalent stronger invariants; never delete them simply to make discovery green.
8. Keep gameplay free of debug flight, direct percent manipulation and scripted fake victories. Such commands may be labelled fixtures in targeted tests, with separate natural-play evidence.
9. Only the coordinator builds/restarts the shared native game. Workers do not simultaneously drive port 51700 or overwrite an installed bundle.
10. Root/Astra owns final art direction and new art assets under the user's existing instruction. Sol/DeepSeek may implement asset loading, parameter binding and mechanical previews. Send art briefs with exact dimensions/anchors/states; use existing reviewed assets while waiting and keep the art acceptance item open.
11. Continue through implementation, integration and validation without routine permission questions. Stop for a real dependency or a product decision that cannot be resolved through the documented defaults; report exactly what remains rather than substituting a lesser feature.

## 5. Gate 0 — Baseline and acceptance ledger

Create `docs/ROGUELITE-ACCEPTANCE.md` when implementation begins. For each requirement record an ID, owner, dependencies, state, evidence artifact/command, revision and remaining limitation. States are `planned`, `implemented`, `automated-pass`, `live-pass`, `human-reviewed`, `blocked`. A feature can need several evidence types; a single status word must not erase a missing one.

Record the current working launch, save paths, CPU policy, supported model signatures, render backend and actual native build identity. Run the existing focused suites once. Capture a short baseline traversal and ordinary combat clip, including the compact HUD and command tree. Save the current fixed generator as a versioned legacy route implementation for migration tests.

Define severity: P0 crash/data loss; P1 softlock, broken controls, unreachable required objective or broken supported platform; P2 major readability, fairness or performance issue; P3 cosmetic defect. Full completion requires zero P0/P1. Full polish also requires zero unresolved P2; P3 issues must either be fixed or explicitly judged acceptable by human review.

**Exit:** baseline is reproducible, test saves are isolated and every later gate has checklist entries. No gameplay redesign is needed in this gate.

## 6. Gate 1 — Data contracts and safe persistence

Do this before generating real runs. Introduce small pure modules where useful: `rng.lua`, `room_catalogue.lua`, `encounter_catalogue.lua`, `dungeon.lua`, `progression.lua` and `checkpoint.lua`. Leave native orchestration in `main.lua` or a narrowly extracted room controller. Avoid replacing the whole project architecture.

Use three distinct identities: template ID (authored layout), room instance ID (one occurrence in a run) and encounter/entity ID (persistent gameplay identity). A room's title or current native handle is none of these. All maps, rewards, enemy hosts and saves must use stable IDs.

Proposed resolved run manifest fields:

```text
schema_version, generator_version, catalogue_version
world_seed, stream_versions, start_room, final_room
rooms_by_id:
  instance_id, template_id, template_version, theme_id
  resolved module placements and collision recipe/version
  sockets_by_id, arrival points, resolved encounter/reward specification
edges_by_id:
  from_room, from_socket, to_room, to_socket
  direction, gate_rule, discovery_rule
generation_report:
  attempt_count, fallback_used, rejection_reasons, topology_signature
```

Progress is separate: current room and arrival socket, discovered/visited rooms, revealed edges, claimed rewards, encounter state, keys/unlocks, stable defeated-entity IDs, supplies, lives and bounded checkpoint state. Keep model handles, Lua closures, pointers and GPU/draw selectors out of both records.

Implementation order:

1. Define and validate schemas with finite values, unique IDs, bounded collections, strict versions and useful errors. Use ID-keyed maps plus explicit order lists; normalize decoded array keys consistently.
2. Extend the existing safe serializer or add a bounded data codec. The present numeric-key limit of 16 is inadequate for the proposed catalogue/manifest. Preserve duplicate-key detection, depth/node/byte limits and rejection of executable content. Never decode by `load()`/`loadstring()`.
3. Introduce a versioned checkpoint envelope, such as `TBD3`, containing profile, run, resolved manifest and roster metadata as one validated generation. Avoid unrelated writes to separate files that can become mismatched.
4. Keep A/B recovery; add checksums and an atomic temporary-write/rename mechanism if the existing native data API does not provide one. Verify native support first. Report durability limits honestly even after readback succeeds.
5. Migrate `TBD1/TBD2` using the frozen v1 generator and legacy fighter defaults. Preserve its exact graph, room IDs, progress and encounter policy; do not regenerate it with v2. Either support its recorded layout or perform an explicit validated migration. Unknown future versions remain preserved and explain why they cannot load.
6. Allocate different default world seeds using stable profile identity plus run serial or a persisted world RNG. The same explicit test seed must still reproduce the same manifest. Acquisition/fusion must not change world generation.
7. Save the resolved manifest, not just the seed. A cosmetic patch, added catalogue entry or generator change must not relocate a saved doorway. Version the placement/collision recipes and retain the versions needed by supported saves.
8. Stage transactions in copies: generate/validate a new run, apply collection changes and write the pair before committing in-memory ownership. A failed new run must not consume parents, unlocks, currency or a run counter repeatedly.

Use independent deterministic streams for topology, layout selection, encounters, rewards, genetics and cosmetics. Specify the integer algorithm and arithmetic so Lua/platform differences do not change results. Sort IDs before RNG-dependent selection. Cosmetic code must never consume a gameplay stream.

Legacy caveat: multiple earlier builds used unversioned `TBD2` generation. If a save contains only its seed, exact historical geometry cannot be recovered without the matching archived generator. Freeze the available legacy implementation, inspect known fixture provenance and document any safe layout migration. Do not promise byte-identical reconstruction of information the old format never stored.

Test old valid saves, newest-slot truncation, both slots invalid, short writes, missing assets/catalogue versions, unknown fields, oversized manifests, duplicate IDs, encoding round trips and interrupted migrations. Test resume after the generator's implementation has changed. Corruption recovery must not silently erase the collection.

**Exit:** a resolved variable-size test world round-trips; legacy saves reproduce their original route; failed writes preserve the preceding valid state.

## 7. Gate 2 — Real dungeon topology

Build the pure graph generator before touching native spawning. Its output must vary structurally across seeds.

Use the research's mission-graph approach: a required path with deliberately inserted branches and loops. A spanning tree can supply connectivity; choose additional edges according to play purpose. BSP/WFC are optional later tools only if measured room-packing or adjacency needs justify them. Do not implement a general WFC engine as a prerequisite.

Concrete algorithm:

1. Draw bounded room count, required-path length and pacing pattern from the topology stream. Reserve start, a safe early teaching space, at least one meaningful route choice, a rest opportunity, a boss approach, boss and completion room.
2. Allocate room-role instances before selecting art. Place combat, traversal, reward and rest roles with limits on consecutive hard fights and empty connectors.
3. Attach optional branches whose rewards justify the detour. Prefer short authored detours; cap consecutive unrewarded backtracking. An optional branch must return or rejoin safely.
4. Add selected loops/shortcuts while preserving mandatory progression. Distinguish a discovered shortcut from a required route. Never permit an early shortcut to bypass a required boss or consume the only key needed to finish.
5. Budget graph degree against available template sockets before selecting templates. A branching room with an entrance and two choices needs three distinct sockets. Degree-four rooms need four. Never map two destinations to one ambiguous door or duplicate a portal at the same coordinates.
6. Select compatible room templates by role, socket count/type, safe arrivals, theme, difficulty budget and measured mobility envelope. Avoid immediate repeats and limit repeated templates per run.
7. Bind every directed edge to concrete source/destination socket IDs. Bidirectional passage is represented and validated in both directions. Store actual arrival facing/position, not simply `x=-42` on every entry.
8. Resolve encounters and rewards from their own streams. Store those choices before runtime starts.
9. Validate topology, progression, sockets, movement and resource budgets. Use a bounded number of candidate attempts, initially 32. Persist reasons and attempt count.
10. If attempts fail, choose an explicitly versioned, already validated connected fallback. Mark it in diagnostics. Never claim the fallback demonstrates procedural diversity.

Start with deterministic optional locks and persistent keys. Do not require a random gene, consumable movement resource, advanced tech or rare proc on the mandatory path. For later optional gene gates, evaluate current capabilities and the return path; losing or swapping that gene cannot strand the player. Consumable-key puzzles require resource-aware search, not a Boolean `has_key` check.

Progression validation searches states such as `(room, socket, persistent unlocks, remaining consumable keys, completed mandatory objectives)`. Bound the state space; prefer a small explicit lock catalogue. Every reachable playable state needs a route to a safe checkpoint/finish under its authored one-way/drop rules. Graph connectivity alone does not prove this.

Property tests: at least 1,000 ordinary seeds plus targeted adversarial seeds, reproducibility, stream independence, path-to-finish, mandatory-objective ordering, return paths, socket degree, lock/key resource accounting, unique identities, bounded retries and failure cleanup. Measure topology signatures without IDs/themes/coordinates. Across the fixture seed set, require multiple room counts and at least 20 distinct structural signatures; small platform translations do not satisfy this gate. Log fallback rate and investigate if it exceeds 1% on the authored default catalogue.

**Exit:** a graph inspector shows visibly different meaningful routes, and the same seed/version reproduces the same fully resolved result. Save/load preserves that result exactly.

## 8. Gate 3 — Room catalogue and physical playability

Replace the fixed-room whitelist with template contracts. Keep themes separate from role and geometry. A boss-capable template can host multiple bosses; a connector's actual topology must not depend on its display name.

Each template defines module placements, collision surfaces, socket transforms/types, safe arrivals, player/enemy/item spawn zones, camera policy, KO envelope, recovery space, supported mobility profiles and resource budgets. Distinguish decorative geometry from physical collision. Do not draw a staircase the fighter cannot stand on.

The BF kit rules are mandatory: 6.5 game units per metre, 13-unit structural grid, 26-unit wall/floor bays, 26-unit wall storeys, unit-scale doorway wall bays and their authored local depth. Replace solid wall bays with doors. Posts meet seams; beams meet storey tops. Optional door leaves share the doorway transform. Floor sidecars or explicit lines own collision exactly once; disable interior seam ledges and retain intended exterior ledges.

Initial catalogue construction order:

1. Prove a flat arena, a two-level traversal and a three-socket branch room using existing meshes.
2. Add a return connector and rest room, then run them as a connected reversible route in-engine before generating them.
3. Add stairs, a ramp, a drop-through opening and a balcony using the existing exported pieces. First inspect each sidecar and mirror/rotation policy. Runtime collision directions may forbid an otherwise valid visual transform.
4. Build alternate combat spacing, vertical traversal and four-socket connectors. Keep each inside a demonstrated camera/blast-zone envelope. If a room requires larger bounds, make the native bounds/respawn work a named dependency before admitting it.
5. Expand to the finite catalogue target. Count meaningfully different movement/combat demands, not art variants.

Measure representative movement profiles in the actual engine: short/heavy, floaty, fast-faller, multiple-jump, compact/tall body, sword/equipment and partner fighters. Eventually cover every offered fighter, transformations and the maximum supported movement penalties. Record standing/jumping clearance, platform rise/reach, drops, ledge grabs and recovery margins. Mandatory paths must work without advanced techniques or genetic bonuses; optional skill routes may demand them with clear expectations and safe returns.

Replace the current rise/gap-only screening with directed, obstacle-aware traversal checks. Floors, ceilings, walls, body clearance and approach/landing margins matter. A drop from A to B is not evidence of a jump from B to A. Use analytical checks for fast rejection and actual controller replays for catalogue certification. Debug flight can inspect surfaces but cannot certify mobility.

Maintain three independent tests: mesh/sidecar dimensions against authored metadata; generated placement/connection checks; native movement across seams and routes. A test that repeats the builder's constants is insufficient.

**Exit:** every admitted template has a native traversal/combat clip, a mobility contract, correct doors and actual collision. Unsupported transforms/templates fail before actors spawn.

## 9. Gate 4 — Runtime world lifecycle and exploration

Refactor fixed-name decisions in `main.lua`, `Rooms.plan()`, diagnostics and the live driver to use manifest/template/encounter fields. Remove `node.id=='approach'` and `arena_a/arena_b` assumptions from v2 paths. Keep explicit legacy handling isolated.

Implement a transition state machine with named phases: request → validate destination → preload → retire old room → construct collision/models → acquire/check isolation → place actors → commit checkpoint → reveal/activate. Keep the outgoing logical checkpoint until the new room is valid and saved. Once old geometry is retired, a failure may need to reconstruct the saved room; do not claim rollback while leaving an empty active scene.

Important details:

- Preflight asset/model/collision budgets and allocate incrementally. Never collapse preload, model creation, save serialization and visual rebinding into a single heavy hook.
- Latch held buttons across every phase. Loading must not turn a held Down into a second door activation or a held Up into taunt.
- Validate isolation during pending placement and active play. Script error, unsupported host or lost ownership pauses with a useful recovery path and preserves the last committed save.
- Resolve arrival from the destination socket. Check safe floor, body clearance, knockback/respawn restrictions and proximity to enemies before enabling combat. Preserve the existing bounded placement retry; count retry time meaningfully if the game is paused.
- Disable door activation during hitlag, damage/throw states, respawn or other unsafe control states. Require a deliberate fresh input and clear prompt. Getting knocked through a doorway never travels automatically.
- At command root, a usable nearby door consumes Down. Otherwise Down enters Special. Below root it always follows the tree. Resolve overlapping prompts deterministically and reject overlapping trigger volumes during template validation.
- Revisit cleared rooms without respawning rewards or required enemies. Track partial encounters by stable spawn ID, boss phase/remaining stock and policy-defined checkpoint state. Do not farm charges/items by reloading.
- Distinguish defeated, escaped, despawned, unloaded and missing enemies. Required enemies that escape need an authored fail/respawn/defeat rule. Remove the blanket 'no handle means cleared' assumption for combat objectives.
- Park, hide or safely suspend unused fighter slots so Fox does not stand in every exploration doorway, affect the camera, get charged on or die off-screen. Inspect existing native support; if adding a helper, test restoration on every exit. Merely setting CPU to stand is not a complete solution.
- Retire room-owned enemy genes, marks, emitters and references without losing persistent room progress. Longer runs cannot accumulate orphan hosts/genes until Core's 32/128 caps are exceeded.
- Add a compact discovered-room map accessible through the command menu and pauses. Show current room, known exits, revisitable rooms and relevant locks without revealing undiscovered rewards. Keep exploration physical.

**Exit:** complete a generated run, revisit an optional branch, use a shortcut, save/reload midway and finish. Repeat with fault injection during each transition phase. No duplicates, stranded player, FD reappearance or lost checkpoint is acceptable.

## 10. Gate 5 — Combat actions and genetic rules

Stabilize the action/event contract before expanding families. Distinguish fighter port, partner, item/article, Adventure actor, gene host and owner. Add stable move/attack instance identities and provenance for direct contact, projectile, shield interaction, reaction and scripted action damage.

Current action-state change IDs are not sufficient proof of correct multihit/projectile charging. Test a multi-hit move, a move that changes animation states, a lingering hitbox, simultaneous trade, projectile ownership, reflected attack, shield hit and a killing hit on a disappearing native actor. A reaction must not charge itself or recursively trigger forever. Define per-move versus per-target earning explicitly for each gene.

Implement a common resolved ability transaction: preflight → startup → active collision/effect → recovery → settled result. Player and enemy activations use the same costs, valid targets and interruption policy. Current immediate `gd.hit` calls do not by themselves provide dodgeable startup, obstruction or combat commitment. Where a gene promises an attack area, implement real or equivalently validated bounded collision with correct range, occlusion and hit history; visuals must match it.

For every gene/placement record: trigger, supported hosts, charge behavior, action, spend point, startup/recovery, cancellation/refund rules, hit/shield interactions, limits, affected logical regions, state visuals, audio, controller path and counterplay. Keep base traits, inherited traits, run upgrades, equipment contributions and timed modifiers separate. Resolve from sources once in a documented order; remove/expire contributions without numerical drift.

Before adding more genes, demonstrate complete Cinder/Rime loops and Thermal Shock with native contacts and natural controller play. Then add families one at a time, with at least two distinct placements and one useful build decision each. Each new family must fit both player and eligible enemy contracts. Validate lower and upper caps as well as normal balance values.

Author mutually exclusive effects, dominance rules and reaction precedence. Limit one dominant persistent surface treatment per region, but preserve information for secondary effects through accents. Gameplay limits and visual budgets are separate. Particle culling must never suppress a hit or shorten a status.

**Exit:** the finite gene/reward/synergy catalogue is playable, describes real mechanics accurately and has native evidence for every behavior category. Unsupported item/projectile interactions are either implemented or removed from the offered definitions; they cannot remain hidden partial behavior.

## 11. Gate 6 — Enemies, bosses and capable fighter AI

Use encounter data for composition, positions, activation regions, genes, modifiers, objectives, reinforcement timing and completion policy. Include pressure, zoning, defense, aerial/recovery, mixed-target and elite encounters. Difficulty uses decisions and combinations as well as bounded stats. Prevent off-screen unavoidable attacks and simultaneous overlapping tells with no response window.

A fighter AI task is not complete because level 9 is selected or an L-cancel input was attempted. Start from the existing native technical assist and the recorded 20XX/UnclePunch/TM-CE/SmashBot/Slippi-AI audit. Recheck original source and applicable reuse/model terms before adopting code or weights. Choose one integration strategy after a short runnable comparison; do not glue several incompatible policies together or assume patched PPC code runs natively.

Create one observation → decision → legal controller-input/ability-action boundary. Compare vanilla and candidate policies on identical seeds and layouts. Measure actual completed L-cancels/techs, recovery success, approach/retreat decisions, spacing, shield punishment, ledge behavior, reaction delay and gene use. Report opportunity/input/success counters separately. Technical execution must be paired with understandable difficulty levels and readable counterplay.

Broaden from Fox/Falco to every fighter archetype actually used by encounter data. Test on custom room collision, not just stock stages. Native AI may assume stock navigation; supply bounded room-aware target/recovery guidance where needed without teleporting or skipping lag. AI cannot inspect unobservable player inputs or grant itself undeclared charge, invulnerability or reactions.

Non-fighter enemies need authored movement, targeting, ledge/fall rules, gene tells and attack recovery. The existing Goomba/ReDead wrappers are starting points. Add other native enemies only after inspecting their dependencies on original Adventure stage data. Supply original custom controllers/models when necessary; a spawn API alone is insufficient.

Bosses must have distinct phases, attack selection, vulnerability/recovery windows, positioning demands and gene expression. A boss may be a fighter-based champion or another supported native/custom actor. Give each a phase transition that is mechanically meaningful; no unavoidable cinematic damage. Record phase/remaining-stock state at supported checkpoints and prevent reward duplication on reload.

**Exit:** the encounter/boss content target is met, fighter AI demonstrably improves on the baseline in measured behaviors, and full natural encounters remain fair at the intended difficulty. External integration claims must name the actual reused system and limitations.

## 12. Gate 7 — Inventory, collection and progression economy

Complete real inventory ownership and item actions; the existing Restore leaf is only one consumable. Specify capacity, stacking, acquisition, cooldown, use restrictions and room-transition behavior. Reject unavailable actions before spending items. Add equipment records with stable slot ownership and reversible contributions to gene resolution.

Distinguish a gameplay equipment record from a sword already built into a fighter model. Marth's sword, Link's shield/scabbard and temporary articles need separate semantic bindings; equipping a stat item must not delete the fighter's native weapon. If physical held items are supported, define drop, pickup, destruction, reflection and owner changes explicitly.

Finish collection sorting/filtering, gene inspection, ancestry, comparison, breeding, locked inheritance, fusion previews, selling/discarding/replacement, capacity handling and run history. All destructive transactions require an accurate preview and a deliberate in-game confirmation. These confirmations are product UX, not requests for agent-development permission.

Define one bounded permanent economy: acquisition sources, breeding costs, unlock progression, duplicate handling and difficulty rewards. Simulate it to catch unbounded power/currency loops, then playtest it. Permanent progress should broaden choices and allow selected inherited improvements while caps preserve meaningful difficulty. Do not silently turn the agreed permanent genetic system into unlocks only.

Preselect reward offers when the encounter is created or first legitimately completed, and persist them before selection. Reopening/reloading does not reroll offers. Prevent an enemy-owned gene entering inventory or export. Verify fusion does not leave an equipped reference to a consumed parent.

**Exit:** a fresh profile and an established profile can complete success/failure loops, acquire/breed/fuse/equip/use/export/discard content and resume safely, including full-capacity and failed-save cases.

## 13. Gate 8 — Commands, menus and onboarding

Expand the current command tree from installed loadout/inventory capabilities. Do not make the player browse every catalogue item during combat. Keep three choices per node and a stable, learnable direction pattern. Aim for frequently used actions in two or three presses from root; allow prepared assignments between encounters. Show cost/readiness and a short reason for a blocked action.

Preserve neutral-separated input, Up's release latch, chord handling and all ordinary combat inputs. Test controller disconnect/reconnect, remapping, keyboard emulation, mouse focus, pause, respawn, transformation and scene transition. Reconnection must not consume a held button as an immediate destructive selection.

Replace permanently disabled placeholders such as Route or a manual Thermal Shock leaf with working interactions or clear explanatory entries. The route action opens the discovered map. An automatic reaction should explain its prerequisites rather than pretend to be a castable command.

Finish collection, new-run setup, roster, build, inventory, breeding, fusion, reward, rest, discovered map, pause/settings, death, victory/export and save-error recovery screens. Reuse menu-kit layout/components and the existing single source of resolved stats. Actual fighter/model previews must identify when they are schematic; final equipment/region previews should show the relevant supported fighter where feasible.

Centralize player-facing strings, formatting and units. Finish the launcher's already offered English/Spanish error coverage; any language offered inside TBD must cover tutorials, item/gene descriptions and recovery messages as well as button labels. Do not add a language selector for unfinished translations. Test long labels, text scale, contrast, color-independent states and keyboard/controller focus. Keep diagnostics separate from translated product text.

Add an early teach-and-try sequence: move/fight normally, earn one charge, navigate a branch, back out with Up, cast once, recognize an enemy tell, use a door and accept a reward. Experienced players can skip/revisit tutorials. Explain genealogy and fusion only when those features first become useful.

HUD and toast rules: compact damage/lives/resources, clear ready/cooldown states, no permanent large inventory panel in combat, no toast for every hit/charge tick. Prioritize critical errors and encounter tells; coalesce repetitive upgrades. Keep faces, fighters, ledges and enemy windups visible. Safe-area and UI-scale settings must work at 4:3 and widescreen sizes.

**Exit:** a new player can complete the first loop without console commands or unexplained placeholders. Every screen works with controller and mouse; focus, back and destructive-action behavior are consistent.

## 14. Gate 9 — Character regions, equipment and visual spectacle

Keep anatomy/equipment semantics, draw/material surfaces and skeleton anchors as separate data layers. Use the existing measured reports to propose bindings, then review the visible geometry. The largest mesh is not necessarily the useful part; a blade, shield, glove, boot, hat, tail or detached article may be more important than the torso.

For every offered fighter/costume, bind logical striking, guard/core, traversal and appropriate focus/equipment roles using asset fingerprints and reviewed selectors. Cover action-dependent geometry, alternate weapons/accessories, transformation, respawn and partner actors. Define whether partners share mechanical resources and how that shared state is expressed visually. Do not copy raw draw ordinals between costumes.

Where one draw combines regions, author a mask or use an approved attachment/whole-surface accent. Never claim shader selection can isolate geometry for which no mask/selector exists. Preserve base texture, normals/shading and alpha/cutouts; protect faces and key silhouette detail. Fix invisibility or leaked overrides before adding new effects.

Author dormant, charging, ready, activation, reaction and recovery states for each family. Connect visual parameters to effective stats: discrete capacity segments, intensity/density for potency within a cap, actual status duration and true hit range. Put high-energy compositions on earned events and leave quiet periods. Include distinct motion/shape cues so color is not the only signal.

### Expanded visual vocabulary — beyond bursts

Design addition: the user explicitly wants afterimages, tracers, halos and related continuous effects. This is planning only; adding this section does not start implementation. The installed showcase is weighted toward point-emitted particles and explosions. Build identity should also be readable while moving, charging and fighting normally, with bursts reserved for appropriate events.

| Treatment | Intended appearance and gameplay use | Implementation boundary |
|---|---|---|
| Fighter afterimages | Fading ghost poses on a dash, dodge or earned movement activation; express Traversal identity without hiding the live fighter. | A full fighter ghost needs bounded historical pose/draw snapshots and a separate render pass/material. Joint particles or flat silhouettes are cheaper alternatives, but must be labelled accurately. Do not assume an existing particle emitter can reproduce the animated fighter. |
| Tracers and ribbons | Lines following fists, feet, blades, projectiles or motion paths; curved ribbons for wind wakes and energy trails. | Sample actual post-animation attachment transforms into bounded history. For blades, track both endpoints and construct a strip; reject teleport/respawn discontinuities. Trails must follow the accessory's lifecycle and must not imply a larger hitbox. |
| Halos and segmented rings | Rings behind the head, around wrists, under boots or around equipment; rotate/pulse quietly and show discrete stored charges. | Reuse reviewed joint attachments and authored sprites/meshes where sufficient. Orient them deliberately in world, joint or camera space. Drive segment count from actual charge capacity/current state, not a decorative approximation. |
| Orbitals and continuous fields | Circling shards, shields or miniature moons; sustained wind envelopes, heat auras, gravity lenses and shield membranes. | Authored orbits can use deterministic attachment-local transforms; genuine forces/interactions need separate mechanics. Distortion needs suitable background contrast and motion evidence. Never make a cosmetic orbital appear to block damage unless it actually does. |
| Persistent surface treatments | Frosted boots, metallic feathers, glowing seams, flowing arm patterns and spreading cracks; show gene placement and charge/recovery. | Existing texture-preserving part tint is a foundation. Animated patterns require reviewed material support and masks/selectors. Preserve texture detail, cutouts, shading, faces and equipment ownership. |
| Silhouette attachments | Spectral wings, energy claws, blade extensions or shoulder mantles that identify a build at gameplay distance. | Reuse or author appropriate attached geometry and review every advertised fighter/costume/accessory binding. Extra geometry grants no mechanical slot or attack reach by itself. |
| Contact and world traces | Footprints, landing ripples, weapon-floor sparks, frost on platforms or electric links between targets. | Resolve real contact/target positions; expire owned traces and clear them on room exit. Surface spreading and stage-bound decals need actual support. Keep cosmetic traces distinguishable from damaging terrain. |
| Combat/UI connections | Directional slash accents, brief parry punctuation, or a charge travelling from a body region to its HUD icon. | Use actual action/resource events; prevent duplicate triggers. Keep camera/screen effects restrained and preserve important tells at reduced FX settings. |

Start with persistent region accents, attachment-based halos and genuine movement/weapon trails; treat full-model afterimages and animated material patterns as explicit renderer work rather than promised existing features. Prototype one representative of each technique before multiplying recipes across founders. Inspect the native capabilities first and record which implementations are existing, newly added or still planned.

Compose each gene as a small, coherent visual sequence. Example: an ice Traversal gene has quiet frost on equipped boots, a thin skating trail during relevant movement, a contact ripple on a qualifying landing, and a finite shatter burst on activation. More real stored charges may add halo segments; higher movement potency may lengthen a trail within a readability cap; a weapon gene may change tracer shape. Cosmetic density, trail length and brightness do not change collision, grant mechanics or exaggerate effective range. Do not place every treatment on every gene or play every layer continuously.

**Acceptance for this vocabulary:** provide normal-speed, gameplay-distance motion clips and close-up inspection for each advertised technique, including simultaneous opposing builds. Static PNGs and emission counters cannot establish afterimage timing, ribbon continuity or heat distortion. Test camera motion, hitlag, pause/resume, facing changes, fast attacks, teleports, respawn, equipment replacement/destruction, partners/transforms and room exit. Bound snapshot/history lengths, attachment counts and overdraw; use distance/quality reduction while retaining mechanical information. Afterimages must remain distinguishable from the live fighter and opponents, disappear promptly, and respect reduced flashes/motion options. Verify render-state restoration, alpha/depth order and cleanup; no ghost fighters, stale trails, false shields or persistent material overrides may survive their owner.

Complete the earlier effects-lab commitments as part of this work, not just the in-game Cinder/Rime wrappers: Solar Eruption, Glacial Shatter, Thunder Crown, Astral Vortex and Comet Crescent; all ten unordered founder-pair blends; meaningful Palette/Energy/Turbulence/Cohesion/Rhythm/Persistence/Structure controls; and reproducible Breed/Mutate/Lock/Save/Compare operations. Give each founder real charge, release and decay phases. Author semantic layer correspondences and a convincing midpoint for each pair; interpolating arbitrary emitter fields is insufficient. Compare endpoints and at least 25/50/75% mixtures, extreme traits and multiple simultaneous instances. Preserve saved recipe/asset versions so an update does not silently change a favorite. Keep visual ancestry separate from mechanical gene ownership, with an explicit mapping between them.

Complete the authored interaction vocabulary—Thermal Shock, plasma surge, charged crystals, fire cyclone, orbital shard storm and infused comet effects—where mapped into the finite gameplay catalogue. Cosmetic blends do not automatically create a gameplay reaction. Implement every advertised interaction's order, timing, consumption and cooldown through the action system. Multi-founder appearance blends must share a bounded budget and use reviewed compositions; do not promise arbitrary novel behavior from mixing sliders. Genuine orbital forces, dynamic lightning branches or weapon trails require actual native support if advertised; label supported authored animation techniques accurately.

Finish the effects-lab UI and a full labelled showcase: founder/preset selection, layer isolation, play/replay/loop/stop, pause/step, mouse sliders, deterministic replay, parent/child comparison and saved favorites. Walk through the entire implemented catalogue, body/equipment attachments and all phases at close and normal cameras. Distinguish a source-art preview from native rendered evidence and a planned founder from an implemented one. This tour is a required deliverable; the earlier single purple/cyan demo is not sufficient.

Use stable lifecycle ownership for attached emitters, glows, trails and item effects. Resolve transforms after the fighter animation/physics update. A real weapon trail needs sampled movement/attachment history, not a stationary particle masquerading as a trail. Test equip/drop/destroy, scene exit, shader disable, graphics reset, transformation and script error.

Finish low/medium/high FX settings, reduced flashes and reduced camera shake. All retain readiness, warning and damage information. Provide an art review contact sheet and gameplay-distance clips for each family, reaction, upgrade, boss phase and theme. Existing purple/cyan demonstrations do not count as a complete effect catalogue.

**Exit:** every advertised binding and effect is visible, readable and correctly owned during real play; no invisible fighters, wrong accessories, false attack radius or persistent overrides remain.

## 15. Gate 10 — Audio, world presentation and production polish

Create an audio event map for menu focus/confirm/back/refusal, door use, pickups, charge ready, gene startup/release/recovery, reaction, enemy tell, reward, fusion, boss phase, death and run completion. Use original or appropriately usable assets and record their provenance. Add variation and concurrency limits so repeated hits do not become an undifferentiated wall of sound.

Keep combat-critical tells audible over music and spectacle. Add separate music/effects/UI controls and mute behavior; test focus loss, audio-device changes and cold-load underruns. Human listening is required; an active audio voice counter proves only that a voice exists.

Finish coherent room framing, background depth, theme transitions, doorway prompts, lighting/material contrast and readable hazard boundaries. The final camera must follow gameplay and recovery without exposing host-stage remnants or being dragged around by unused CPUs. Validate bounds and respawn together. Do not change gameplay collision merely to accommodate a screenshot.

Use a short masked transition/loading treatment while room resources change, then reveal only after the player can act. Never flash FD or half-built geometry. Check scene fades, shader warmup, first-use sounds, pause/resume and restoring the base game's HUD/camera after leaving TBD.

Give victory, failure and extraction complete results: outcome, notable build changes, collection consequences, chosen export and next action. Remove developer-only names, raw handles and diagnostic counters from player-facing UI. Keep diagnostics accessible separately.

**Exit:** every player-facing state has final visuals, audio and interaction; no debug placeholder remains in normal play. Human review signs off gameplay-distance readability and audio mix.

## 16. Gate 11 — Platform parity, performance and delivery

Follow the existing Linux/Qt build infrastructure. Build native changes on both Windows and Linux; run bridge/ABI checks for the exact executable being tested. The launcher is already Qt—finish its integration and verify it rather than creating another launcher.

Required platform matrix:

- Windows: actual launcher, installed mod, controller gameplay, saves, Unicode/spaced paths, process cleanup and a complete run.
- Linux portable baseline: verify the packaged runtime under the documented Ubuntu baseline, relocated installation, writable user data separate from installation and complete gameplay.
- Linux display paths: actual native Wayland and X11/XWayland, with the renderer and backend recorded. Test mouse, focus, fullscreen/windowed changes, resizing, gamepad ownership and clean exit. Forcing an unavailable backend and seeing an abort is a failed check, not a reason to label the XWayland result native.
- Physical GameCube adapter and SDL controllers: hotplug, four ports, calibration/deadzones, rumble, focus handoff, disconnect/reconnect and exit. Keep the neutral virtual controller helper from claiming the user's active port. Hardware unavailable means that gate remains pending.
- Offline regression: vanilla modes plus representative supported custom content such as the existing Akaneia/ACE fixtures wherever touched. Launcher/disc/mod settings and the original game's HUD/input must restore after TBD.

Use hosted CI for pure tests, schemas, asset metadata and Qt. Use the trusted disc-backed runner/WSL workflow for the game. Do not add discs or extracted retail assets to repositories/artifacts. A skipped or unavailable runner is not a pass. The user should be able to develop on Windows and receive a real Linux check without opening the laptop.

Set reference hardware and graphics settings before performance acceptance. Proposed targets: normal 60 Hz game logic, no growing audio underruns, no visible combat stalls, warmed CPU/GPU frame-time p95 below 13.5 ms and p99 within a 16.67 ms budget on the agreed reference configuration. Measure useful work separately from deliberate present/sleep time. Loading can have a longer wall-clock duration behind its loading state, but must not freeze input/error handling or trip Lua budgets.

Profile the worst supported combination of actors, equipped effects, room detail and UI. Reserve resources for gameplay tells before optional particles. Respect the existing 128 model-instance pool and collision capacities, including other owners; catalogue limits must include temporary gates/effects. Do not increase native pools before measuring and auditing the consequences.

The user cancelled the uncapped ceiling benchmark. Do not restart it as part of this plan. Retain normal-speed performance acceptance and profiling of actual roguelite workloads described above.

Run at least a 60-minute normal-speed soak with repeated transitions and a scripted longer lifecycle test where appropriate. Track model/texture/emitter/enemy/host counts, memory, load latency and input ownership across hundreds of room changes. Loading/culling failures must not corrupt saves or mechanics.

Finish deterministic asset builds, catalogue versions/hashes, incremental invalidation and a local relocatable package. Verify startup through Qt on a clean user profile and an upgraded profile. Keep local development artifacts separate from any future publishing step.

**Exit:** supported platform/input paths have evidence from the final artifact, CI reflects real failures, the local package is reproducible, and offline regressions pass.

## 17. Gate 12 — Full playtesting and the final polish pass

Run complete natural-control playthroughs. Automated fixtures are useful for reaching states, but the final evidence must include players earning charge, surviving traversal, beating encounters and making build decisions at normal speed.

Minimum review matrix for this finite version:

- At least 12 complete runs spanning the three themes, distinct topologies/builds, all boss archetypes, success/failure and both supported operating systems.
- Catalogue traversal certification for every offered fighter and admitted movement-penalty profile, plus focused costumes/equipment/partner/transformation rendering checks.
- First-session review by someone unfamiliar with the mode and skilled-Melee review of movement, AI, counterplay and genetic decision-making. Record feedback separately rather than averaging it into a fictitious objective fun score.
- Resume tests before/after rewards, fusion, doors, partial encounters, boss phases and extraction; verify no rerolls, duplicated items or repeated exports.
- A long-run collection/economy simulation and actual established-profile play. Check that new players can progress and experienced collections cannot trivialize every decision.

Feature completion checklist:

1. Main-menu entry and return work without debug commands.
2. Seeds generate materially different connected dungeons, with certified rooms, discoveries, branches, returns and shortcuts.
3. Movement, objectives and progression cannot strand the player under supported conditions.
4. The full agreed content target is implemented or an explicitly reviewed revised target replaces it.
5. Player/enemy genes, inventory, equipment, breeding, fusion and export obey one consistent ownership/economy model.
6. Fighter AI, non-fighters and bosses have demonstrated intended behavior.
7. All screens, command actions, roster entries and advertised visual bindings work.
8. Save migration/recovery and room lifecycle failures preserve valid progress.
9. Windows/Linux/controller/package acceptance and touched offline regressions pass.

Polish completion checklist:

1. No visual placeholders, model/door seams, host geometry flashes, texture corruption, missing bindings or leaked effects in normal play.
2. Attacks, effects, enemy tells, doors and HUD remain legible at gameplay distance and reduced-FX settings.
3. Command paths, menus, focus, back behavior and onboarding are understandable and consistent.
4. Final sounds/music/UI feedback are mixed, varied and informative, including quiet and high-intensity moments.
5. Camera, fades, room loading, pause/resume, death and extraction are smooth and coherent.
6. Combat timing, rewards, difficulty, run length and permanent progression have been tuned through documented playtest iterations.
7. Reference performance, memory/lifecycle stability and controller behavior meet the accepted targets.
8. Errors explain recovery actions without exposing engine internals or losing data.
9. Fresh install, upgrade, complete run, save/resume and return to the base game feel finished.
10. No P0/P1/P2 issue remains; any accepted minor imperfection has explicit human review.

Do not declare 100% polish from test counts or screenshot approval alone. If the user is asleep, finish the automated/native work and prepare a review build with a short prescribed route through outstanding human/hardware checks. Record those checks as pending.

## 18. Integration order and worker assignments

Use at most the available worker slots. The following are roles, not a request to start them during this planning turn.

| Wave | Independent worker tasks | Coordinator work and merge gate |
| --- | --- | --- |
| A | Persistence/schema worker; pure topology/catalogue-contract worker; optional read-only AI audit worker | Baseline, schema agreement, common fixtures and exact module interfaces. Merge Gate 1 before runtime uses new manifests. |
| B | Topology generation; room templates/mobility; save migration tests | Own runtime adapter and input/transition changes. Land a complete generated route with safe revisit/save/load before expanding effects. |
| C | Gene/action core; encounter/AI policies; inventory/economy | Freeze event/action interfaces first. Integrate one complete behavior at a time and run real combat checks. |
| D | Menus/onboarding; region/FX plumbing; platform/performance | Root authors/reviews art and coordinates asset ingestion. Keep the playable build stable. |
| E | Focused bugs from playtesting, assigned by file ownership | Final evidence, package, human review and completion ledger. |

Sol-6.1 High is appropriate for schema/runtime integration, native collision/action changes and cross-system review. DeepSeek can own bounded pure generators, content definitions, catalogue validators or tests once their contracts are frozen. These are assignment suggestions; do not label an agent's output correct based on model identity. Every change passes the same review and native evidence requirements.

One writer owns `main.lua`, `core.lua`, `prepare.py` and each shared schema at a time. A worker needing another owner's change sends a concrete interface request and continues independent work. No overlapping edits disguised as separate subtasks. Use separate worktrees when that simplifies review, and integrate only after the worker supplies its patch and test evidence.

Suggested independently reviewable patch sequence:

1. Baseline ledger and frozen v1 save fixtures.
2. Bounded codec/checkpoint v3 and migration, without changing current run behavior.
3. Catalogue/socket schema and deterministic RNG streams.
4. Pure variable topology and progression validator.
5. Certified initial three-socket templates and return connections.
6. Runtime manifest adapter, transition state machine and discovered map.
7. Generated full-run acceptance and save/revisit fixes.
8. Event provenance/action lifecycle and Cinder/Rime hardening.
9. Encounter controller and measured AI improvements.
10. Inventory/equipment and collection/economy completion.
11. Expanded content in small playable batches.
12. Full roster/equipment visuals, final UI/art/audio and accessibility.
13. Platform/performance/package fixes and final playtest iterations.

Milestones are integration gates, not stopping points. A worker should not declare the overall task complete at patch 6 because a generated room can be shown.

## 19. Commands and evidence discipline

Run from `gdm`; use the user's existing local disc path rather than acquiring game content.

```sh
python3 -m unittest discover -s tools/roguelite -p 'test_*.py' -v
bash tools/port/build_linux.sh
env MELEE_MODS=0 MELEE_TEST_FILTER=script_ _build/agents/linux/melee --test --iso /path/to/melee.iso
env MELEE_MODS=0 MELEE_TEST_FILTER=geno_fly _build/agents/linux/melee --test --iso /path/to/melee.iso
env MELEE_MODS=0 MELEE_TEST_FILTER=scene_ _build/agents/linux/melee --test --iso /path/to/melee.iso
env MELEE_MODS=0 MELEE_TEST_FILTER=fx_ _build/agents/linux/melee --test --iso /path/to/melee.iso
```

These are baseline entry points, not the complete new test specification. Add focused tests for new behavior and execute the appropriate Windows/portable Linux workflows. New pure-only changes do not require rebuilding untouched native code.

Close the running game before installation:

```sh
python3 tools/roguelite/prepare.py --app-dir _build/agents/linux --enable
env MELEE_CONSOLE_PORT=51700 MELEE_TURBO=0 MELEE_FPS=60 \
  _build/agents/linux/melee --realtime --iso /path/to/melee.iso
```

Normal acceptance enters through the native TBD button. `--demo` is useful for review but does not prove the main-menu path. Update `live_acceptance.py` to query versioned room/socket/encounter diagnostics instead of assuming literal IDs or door coordinates. Ensure read-only inspection never mutates the run or claims controller ownership.

Store durable evidence under a build-identified acceptance directory, with seed, manifest/catalogue versions, OS/backend, test type, result and limitations. Historical `/tmp` logs are useful while working but insufficient as the only final record. Keep copyrighted disc contents, private user data and credentials out of committed artifacts.

Report progress as named gates and verified requirements. If percentages are requested, publish the agreed denominator/weights and distinguish implemented from verified. Never infer 90% completion merely because most source files exist, or 100% polish because automated checks pass.

## 20. Copyable instruction for the implementing agent

> Execute `docs/ROGUELITE-COMPLETION-PLAN.md` through its full offline completion scope. First inspect both repositories and preserve existing dirty work. Create the acceptance ledger and frozen legacy-save fixtures, then implement the data/persistence contracts, actual dungeon generation, certified room catalogue and safe runtime integration before expanding content. Follow the later gates for genetics/actions, enemies/AI/bosses, inventory/progression, command menus, roster/equipment visuals, art/audio, platform parity and polish. Treat the listed content numbers as explicit proposed delivery targets, not evidence of prior approval or current implementation. Record any necessary changes and their reasons. Reuse the current kit and native APIs; verify capabilities before inventing helpers. Keep the recursive D-pad controls, compact HUD, offline-only scope and no-release instruction. Root coordinates shared builds and final art. Run real native/controller checks in addition to pure tests; label debug fixtures. Do not stop at another vertical slice or substitute a fixed graph for generation. Preserve pending hardware/human acceptance honestly and prepare a concrete review build when those are the only remaining gates.
