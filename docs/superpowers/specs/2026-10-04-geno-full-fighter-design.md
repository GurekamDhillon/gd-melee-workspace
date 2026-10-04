# Geno full-fighter design â€” 2026-10-04

**Design only, for owner review.** This proposal supersedes no implementation or gameplay acceptance record. Sources were inspected in the dirty working trees on 2026-10-04; no build, game launch, disc extraction or runtime test occurred. Citations are workspace-relative file:line anchors, not executable verification. Concurrent edits may move anchors.

The owner's direction: â€œbasically I think we need Geno to be able to express a full character instead of just what M-EX doesntâ€. Success means one fighter folder, data and optional Lua, playable on vanilla without MexTK, PPC code or an m-ex package. The private character port is the first customer, Ultimate ports the second, an original fighter the third. No private assets or machine/disc paths belong here.

**V** denotes verified by reading; **P** denotes a proposed contract; **I** denotes inference/estimate. All new schema/API examples below are P, not existing functionality.

## 1. Recommendation and alternatives

**P â€” Add a native fighter-definition backend inside Geno.** Compile data into engine-compatible descriptors; reuse Melee fighter objects, combat/collision and versioned common-state behavior. A definition owns its effective state graph even when most states inherit common algorithms. Keep `attach`, existing geno.json fields and stable .genoasm encodings; activate `define` in a new format version.

Alternative A generates m-ex packages internally: less initial work, but keeps table/PPC assumptions and does not achieve independent authorship. Alternative B implements a separate combat engine in Lua: flexible, but duplicates Melee and greatly expands rollback and compatibility work. Recommend the native middle path. Full-fighter expression does not imply Ultimate/Brawl global-mechanics parity.

**V â€” Current boundary:** `define` is skipped (`melee/pc/platform/geno_registry.c:1139`), and rejected by the author schema (`tools/geno/geno.schema.json:29`). Added states reuse installed subactions and named native callbacks (`melee/docs/geno.md:1597`, `:1619`, `:1655`). Those callbacks are not arbitrary fighter Lua.

## 2. Complete logical inventory and current ownership

Retail common C remains a supplier of common gameplay for every backend. â€œNoâ€ below means no complete Geno authoring surface was established by this reading. Several logical parts share a DAT. Unnamed struct fields must not be presented as a fully decoded format.

| Fighter part and retail definition (V) | Supplier today | Geno today: exact fields or gap |
|---|---|---|
| Internal FighterKind, external CharacterKind, per-character arrays: `melee/src/melee/ft/forward.h:118`, `:181`; `melee/src/melee/ft/ftdata.c:147`, `:317`, `:349` | m-ex tables and port adapters | `attach` targets existing fighters (`melee/docs/geno.md:135`); `define` skipped (`geno_registry.c:1139`). No standalone constructor. |
| Main fighter archive: attributes, extended attributes, parts, animation descriptors, dynamics, camera, pickup offsets, SFX and other tables: `melee/src/melee/ft/types.h:871` | Retail/m-ex data, load callbacks (`melee/src/melee/ft/fighter.c:1049`) | `attributes`, `special_attributes` modify existing data (`melee/docs/geno.md:143`, `:1499`); not an archive constructor. |
| Common attributes: `melee/src/melee/ft/types.h:752` | DAT plus clone/native initialization | `attributes`, `jumps` (`melee/docs/geno.md:127`, `:232`); not every retail struct field. |
| Model, parts, skeleton and bone semantics: `melee/src/melee/ft/types.h:696`, `:875`, `:907` | Main/costume data and fighter setup | No fighter model/skeleton definition; conversion is outside Geno (`docs/learn/geno-fighters/06-attributes-animations-model.md:21`). |
| Hurtboxes and ECB: runtime fields `melee/src/melee/ft/types.h:1451`, `:1466`; hurt collision `melee/src/melee/ft/ftcoll.c:244` | Data plus retail/clone collision | LAB reads hurtboxes (`melee/docs/geno.md:409`); no full base hurtbox/ECB schema verified. Body/hurtbox script flags are partial support. Exact DAT-to-ECB mapping needs an extraction audit. |
| Animation banks, subactions, wait/paired thrown clips: `melee/src/melee/ft/types.h:862`, `:883`; loader/lookup `melee/src/melee/ft/ftdata.c:2169`, `:2307`, paired handling `:2254` | Retail/m-ex files | `subactions` overlays scripts; `motion_anims` remaps installed rows (`melee/docs/geno.md:1484`, `:2286`). No independent animation bank. |
| Common and fighter-specific states: animation/interrupt/physics/collision/camera callbacks, flags and move ids: `melee/src/melee/ft/types.h:989`, `:1014`; selection `melee/src/melee/ft/fighter.c:870`; Mario table `melee/src/melee/ft/kinds/ftMario/ftmario.c:20` | Retail C or interpreted m-ex PPC (`docs/MEX_PORT_STATUS.md:12`) | `states`: `name`, `behavior`, `subaction`, `like`, `flags`, `move_id`, `anim`, `iasa`, `phys`, `coll`, `next`, `land`, `landing_lag` (`melee/docs/geno.md:1619`). Added states, not complete common replacement. |
| Input and eight special entry functions: `melee/src/melee/ft/ftdata.c:421`, `:457`, `:565`, `:601`, `:673` | Clone/native or interpreted m-ex PPC | `specials.n/s/hi/lw/air_n/air_s/air_hi/air_lw` (`melee/docs/geno.md:1647`), native behaviors/data. No verified fighter Lua ABI. |
| Script timers, hitboxes, throw release, body/visibility, effects and sound: executor `melee/src/melee/ft/ftaction.c:349`; throw ops `tools/geno/reference.md:32` | Retail/m-ex words, Geno overlays | .genoasm vanilla commands plus Geno escapes (`tools/geno/README.md:30`, `:47`). Throw operations exist; full attachment/being-thrown asset ownership does not. |
| Articles/items, attributes and state tables: `melee/src/melee/it/types.h:86`, `:141`, update predicates `:407` | Retail/m-ex data/PPC; Geno native articles/items | `articles`, `model.file/symbol` (`melee/docs/geno.md:2054`, `:2079`, `:2088`); native `items/<name>/item.json` (`:2343`). Articles have no hurtbox (`:2184`); arbitrary article graphs/behavior still gaps. |
| Effects | Retail/m-ex banks; Geno runtime (`melee/docs/geno.md:2424`) | .gfx.json; article `fx`, fighter `fx_bindings` (`melee/docs/geno.md:2501`, `:2508`). Capability does not establish fidelity. |
| Sound/voice banks, announcer and victory audio | Retail SFX descriptor (`melee/src/melee/ft/types.h:900`); m-ex bank/announcer adapters (`melee/pc/platform/gw_mex_ftfunction_runtime.c:710`, `:803`, `:895`) | `sfx` plays installed ids (`tools/geno/README.md:51`); no complete named Geno fighter-bank registration verified. |
| Camera and results/victory models/poses/emblems | Retail camera data/zoom bone (`melee/src/melee/ft/types.h:895`, `:856`); results emblem (`melee/src/melee/gm/gmresult.c:1496`); m-ex metadata (`melee/pc/platform/gw_mex_ftfunction_runtime.c:1042`) | No complete presentation schema; `like` inherits camera callback (`melee/docs/geno.md:1624`). |
| CSS icon/portrait/name/announcer; stock icons | Retail/menu data and m-ex UI adapters (`melee/src/melee/mn/mncharsel.c:196`, `:1281`; `melee/src/melee/if/ifstock.c:44`) | No Geno-only selection entry verified. Native catalogue work is incomplete live integration, below. |
| Costumes, materials/texture animation, team colors | Costume structs/loader (`melee/src/melee/ft/types.h:975`, `:984`; `melee/src/melee/ft/ftdata.c:2081`, `:2110`), m-ex costume metadata (`gw_mex_ftfunction_runtime.c:1042`) | Reuse installed costumes; no standalone team/costume definition. |
| Kirby copy ability and hat | Retail archive table (`melee/src/melee/ft/kinds/ftKirby/ftkirbydata.c:48`); m-ex copy data and callback arrays (`melee/pc/platform/gw_mex_ftfunction_runtime.c:1220`, `:1232`) | No complete copy/hat declaration verified. Multi-jump does not supply it. |
| CPU AI tables, move decisions and recovery | Retail input command interpreter (`melee/src/melee/ft/ftcpuattack.c:52`); clone behavior. I: full per-kind AI-table audit remains | No complete Geno AI hints/planner surface verified; a CPU running does not prove it understands new moves. |
| Throws and being thrown, grab joints and paired clips | Runtime thrown hitbox (`melee/src/melee/ft/types.h:1463`), paired animation lookup (`melee/src/melee/ft/ftdata.c:2254`) | Throw words exist; independent grab/victim skeleton/animation mappings remain gaps. |
| Ledge, shield, landing, damage/death, item-use; water/swim policy where applicable | Common state selection (`melee/src/melee/ft/fighter.c:870`); item callbacks (`melee/src/melee/ft/ftdata.c:745`, `:889`, `:925`); Geno exits via Melee common logic (`melee/docs/geno.md:1605`) | Partial named callback inheritance, not every-state override contract. No established Geno swimming behavior claimed. |
| Trophies, progression and records | Trophy catalogue/list (`melee/src/melee/ty/tylist.c:116`, `:194`); character identity (`melee/src/melee/ft/forward.h:181`) | No Geno registration verified. Exact record storage/table census is unresolved and required before integration; do not infer new records work from roster support. |

**V â€” Limits:** 32 profiles, 48 added states, 16 articles (`melee/pc/geno/geno.h:250`, `:266`, `:357`); article ranges depend on profile count (`:361`), registry overlay slots have another bound (`melee/pc/platform/geno_registry.c:444`). Changing one constant is insufficient.

**I â€” Inventory qualification:** this is a complete logical ownership inventory, not a byte-perfect decoding of every ftData field, CPU table or persistence index. Before shipping, generate a table/loader census and resolve every read for the native backend. Unknown fields require investigation or a documented versioned common preset, never silent donor PPC fallback.

## 3. Target package and schema (P)

Introduce `geno: 6` with explicit `requires` capabilities, including `fighter_definition: 1` and `fighter_lua: 1`. Exactly one of `attach` or `define` per entry. Preserve v1â€“5 interpretation and public escape encodings. Older engines must refuse unsupported definitions clearly. Validate transactionally before registration, never expose a half-loaded fighter.

```text
hero/
  mod.json
  geno.json
  fighter/states.json        # optional referenced definition data
  moves/*.genoasm            # author source
  moves/*.words              # portable compiled scripts
  logic/*.lua
  models/*.dat               # authored HSD, or use retail references
  animations/*.dat
  fx/*/*.gfx.json
  sounds/*.wav
  ui/*.png
  copy/                     # optional hat/clips/scripts
  author/*.blend            # source only, excluded from runtime manifest
  manifest.runtime.json     # complete hashed dependency list
```

Schema sketch, deliberately partial rather than a claimed bootable example:

```json
{
  "geno": 6,
  "fighters": [{
    "define": {"key": "example.hero", "name": "Hero", "common": "melee.common.v1"},
    "attribute_base": {"retail": "mario", "component": "attributes"},
    "attributes": {"gravity": 0.09},
    "model": {"retail": "mario", "costume": 0},
    "skeleton": {"retail": "mario"},
    "animations": {"Wait": {"retail": "mario", "clip": "Wait"}},
    "states": [{"name": "Wait", "inherit": "common:Wait", "clip": "Wait"}],
    "moves": {"jab": {"script": "moves/jab.words"}},
    "specials": {"n": "state:Shoot"},
    "logic": {"module": "logic/hero.lua", "state_layout": {"charge": "i32"}},
    "copy": {"policy": "none"},
    "ai": {"preset": "melee.generic.v1"}
  }]
}
```

The checker expands common behavior and verifies all required bindings; a clone-template command fills complete moves, clips, attachment and presentation defaults. Bare Wait plus an undefined Shoot fails. Existing state keys retain their meanings; v6 adds symbolic targets and independent animation/script binding. Legacy numeric `geno:N` remains for attachments; standalone scripts compile named local relocations, not guest addresses.

### Identity, attributes and assets

Identity is `(mod_id, fighter_key)` plus content/version, display/localized name, series/emblem, select visibility and unlock default. Numeric catalogue ids are transient; the author never chooses a resident byte id. Transform partners/companion fighters are explicit dependencies counted at admission.

Attributes cover the complete common struct through named typed fields, units and ranges. A retail preset may supply defaults by reference, followed by independent effective overrides. New special parameters are typed named data, not offsets into clone memory. Keep `special_attributes` for old attachment profiles.

Skeleton data declares hierarchy/bind pose, root and translation/rotation roles, feet, hand/item sockets, grab/victim anchor, camera and shield/reflect/absorb origins. Named bones resolve to validated indices. Hurt capsules declare endpoints/radius/posture/grabbability; ECB declares probes and animation-sampling/lock policy. Enforce current engine capacities until explicitly expanded. Costume variants share gameplay skeleton/hurtboxes by default; gameplay changes are a distinct hashed fighter variant.

Accept authored HSD DAT models/banks and symbolic retail HSD references. Accept GXMS for rigid accessories/articles. **Recommend Blender/glTF 2.0 input compiled offline to HSD skeleton, skin and animations** as the primary original-art path. V: the stage mesh exporter packs position/UV/normal, no skin joints/weights (`tools/blender/gd_mission/mesh.py:31`, `:41`); current fighterbuild uses mesh JSON and a template DAT (`ports/ir/tools/fighterbuild/Program.cs:61`, `:88`). P: extend fighterbuild with a clean authored template generator so no retail template is shipped. Skinned GXMS would require a new runtime contract and is a later alternative.

Importer must bake constraints/drivers, normalize weights, use deterministic joint/triangle ordering, convert axes/units/bind matrices/root motion and interpolation, and validate supported materials/palettes/memory. Unsupported morphs/materials/constraints are rejected or explicitly baked with a loss report. No automatic retargeting promise. LAB previews posed skeletons, sockets and collision, not just static meshes.

Named animations reference package bank/symbol or `{retail, clip}`, with rate, loop, root-motion policy and blend/interpolation. Clips are independent of scripts. Required common clips may deliberately alias compatible clips with warnings; incompatible grabbed/thrown/ledge anchors cannot silently pass. Results clips are separately scoped.

Costumes declare model/material/texture variants and per-costume portrait/stock art; red/blue/green teams use explicit costume maps or declared tint fallbacks. Results define victory/defeat poses, framing, emblem and victory music. Missing optional art uses initials/generic presentation; missing announcer uses a generic call. These defaults let slice 1 play through results before custom UI work.

### Every state, with common behavior inherited

Resolve all engine common states through `melee.common.v1`: idle/walk/dash/run/turn/crouch, jumps/fall/fastfall, attacks and landings, shields/rolls/dodges, ledges, grabs/throws/victim states, damage/hitlag/hitstun/tech/down/getup, death/rebirth, taunts and supported item states. Package owns effective clips/scripts/attributes; preset owns native algorithms/input arbitration. Water interaction requires an explicit supported common policy; do not invent an existing swimming implementation.

Each state may override `enter`, `anim`, `iasa`, `phys`, `coll`, `camera`, `exit`, flags/stale id, clip/script, and transitions on animation end, ground/air edge, landing or hit. Phase is a versioned native/common behavior, declarative checks, or sandbox Lua function. Missing phases inherit the named common state; explicit `none` disables one. Define input intent priority explicitly. Engine forced damage/grab/death transitions remain authoritative: omitting a callback cannot grant immunity.

All transitions, including calls from damage/ledge/item code, resolve through the fighter's effective dispatcher. V: current added Geno row lookup is scoped to 0x400+ (`melee/docs/geno.md:1601`). P: expanding only that lookup is insufficient. Retain native common motion semantics for range checks; custom states use package handles and centralized conversion. Generate coverage proving every common state resolves correctly and never falls into accidental donor behavior. Clone templates may explicitly select supported native retail special adapters, but never PPC pointers. Unsupported donor behavior causes template generation to fail clearly.

### Move scripts, articles and resource names

Keep hitbox/throw/timer words and stable Geno escapes. Add high-level move data compiled into the same scripts: frame/tick events, hitboxes/grabs/throw release, body flags, rates, named FX/SFX and transitions. Specify animation-frame versus logic-tick timers, never render-frame timers. Named bones/states/resources relocate at load; reject raw callback/call addresses. Throws declare attachment, paired victim clips and release frame as well as damage/angle/growth.

Articles gain named local kinds, owned attributes/model/clips, state phases, optional hurtboxes, hitboxes, lifetime, reflect/absorb/clank/team/owner policy, spawn/despawn/child scripts and snapshotted serial handles. Native items cover pickup/drop interactions. Use bounded per-match/per-owner pools; prohibit unlimited recursive generation and specify deterministic exhaustion behavior.

FX references existing .gfx.json packages or symbolic retail effects. Audio maps names to authored PCM WAV converted offline to the mixer's supported representation, or symbolic retail bank entries. Voice/announcer/victory have named roles and deterministic selection. Named fighter audio registration is engine work, not something today's `sfx` already supplies. Effects/audio never decide collision or damage.

Kirby copy policy is `ability`, `retail` or explicit `none`. A supplied ability owns copied state graph, Kirby clip/bone mapping, parameters/articles/FX/audio and hat/socket. Source identity and copy state survive rollback and reset on loss. Missing copy gives no ability, never an unrelated donor row. AI hints cover intent/range/startup/recovery, charge/projectile conditions, recovery geometry and ground/air eligibility; generic AI turns them into legal inputs. Optional bounded Lua planner uses the same deterministic domain. Records persist under stable keys; optional authored trophy/text registers in a separate catalogue. Missing trophy produces none; do not extend fixed retail saves by indexing custom kinds into them.

## 4. Deterministic fighter Lua, rollback and netplay (P)

Create a dedicated fighter Lua domain with no unrestricted `gd`. V: general scripting uses one native Lua state with script environments (`melee/pc/platform/gw_script.c:5`); a `rollback_safe` flag does not prove arbitrary heap snapshot support. Existing Geno requires mutable state in game memory and no host RNG/time (`melee/docs/geno.md:79`).

Recommend stateless module functions over a declared typed `ctx.state` block in snapshotted game memory. No persistent mutable globals/upvalues, arbitrary tables as stored state, coroutines or native pointer userdata. Freeze module/library tables and reject mutable closures; validate enforcement feasibility before enabling online Lua. Recreate ephemeral context each callback. Compile source with a pinned Lua build, reject foreign bytecode. Expose deterministic integer/f32 operations and a fixed math subset; forbid host-dependent transcendental gameplay operations. RNG is only a snapshotted stream with defined draw order.

API: read-only `ctx.input` (latched sticks/buttons/intents), `ctx.self`, bounded `ctx.query` (results ordered by stable serial), typed `ctx.state`; commands `transition`, `velocity`, `attribute`, `hitbox`, `grab`, `throw_release`, `article_spawn/despawn`, `fx`, `sound`. Handles are generation-checked. Commands apply at defined phase boundaries; no direct foreign memory writes. Specify entry, animation/script, interrupt, physics, collision, queued hit/land and presentation order against actual engine ordering. Version any divergence. Entry/exit occur exactly once per transition, including resimulation.

Initial proposed ceilings: 10,000 VM instructions per phase, 50,000 per fighter/tick including owned articles; 64 KiB temporary allocation/invocation; 4 KiB typed persistent fighter state, 1 KiB/article; 64 commands/invocation. These require measurement. No filesystem/network/OS/clock, dynamic module loading, console eval, debug/io/package libraries or randomseed. No wall-time gameplay cutoff. Budget overflow is a deterministic match fault on the same tick for both peers, not a behavior fallback. Host watchdogs may terminate/diagnose but cannot alter gameplay.

Snapshots cover typed fighter/article state, pending commands/events, RNG, grab/copy relationships, pool generations/cursors and resident map. Immutable descriptors stay fixed during a match and are identified by hash. No native pointer is serialized. Sound/FX events have `(tick, owner serial, ordinal)` identities for resim suppression/reconstruction; cosmetic RNG cannot feed gameplay. No online reload.

SHA-256 identity covers canonical runtime manifest, schema/compiler/behavior versions, effective definitions, compiled words, Lua source, runtime model/clip/audio/FX/UI bytes and dependency edges. Exclude author-only files and host paths; normalize relative names/case, reject traversal/collisions. Retail references resolve against agreed edition and actual component fingerprints; hash dependencies without shipping their bytes. Peers agree on engine build, rules, stable fighter keys, package hashes and resident map before play; replays retain the same identities and refuse incompatible playback. Hash is content identity, not provenance/authenticity or sandbox proof.

## 5. Coexistence, registry, capacity and migration

**V:** `_build/tmp/codex-roster-registry-report.md:6` explicitly says live 100-extra-fighter support is incomplete. Its format/identity section begins at `:59`; delivered source-bound manifests/alias planning/codecs are not authored Geno admission. No live mutable map or new wire format is claimed there.

**P:** catalogue entries have `retail`, `mex` or `geno` backend, stable identity, presentation and dependency keys. Existing m-ex and attachment dispatch remains; native Geno descriptors never invoke the m-ex interpreter. Add source-independent Geno registration, not fabricated MxDt rows. Complete frontend, initialization, admission, snapshot, netplay/replay and persistence integration before calling it playable. Attachments may target stable keys; initially allow one gameplay profile per fighter and reject ambiguous compositions.

Map selected wide keys transactionally to resident aliases before match loading. Count transforms/companions and copy dependencies; refuse alias exhaustion. A fully occupied legacy m-ex disc may leave no room for extra native residents. Catalogue coexistence is not unlimited simultaneous kinds. Later widen engine indices or create a separate native resident range after a table audit; never pass wide ids through byte APIs. Version save/replay/netplay maps.

Replace static profile-indexed tables with allocated immutable definitions and snapshot-managed active rows. Decouple article kinds from profile arithmetic; audit masks, 48-state/overlay-slot limits, shared allocators, scalar bridge APIs and reload layout. Keep explicit admitted memory/pool limits. Removing 32 alone is unsafe; active resident kinds remain independently bounded.

Migration reads a locally installed m-ex+Geno fighter, emits a new definition and loss report; it does not automatically decompile PPC. Lift data/scripts/assets, name references, preserve encodings and replace metadata. Strip MxDt/PlCo/menu overlays and raw callbacks. Extracted assets remain local; distributable output contains authored assets and retail references. Every unsupported callback becomes a manual native/data/Lua rewrite task and blocks parity claims.

| Port | Conversion and material risks |
|---|---|
| Sora | Preserve skeleton/clips, converted move scripts, Geno specials and FX bindings; replace host callbacks, registration/UI/audio metadata and clone-file dependency. V: host selection and conversion-loss checks exist (`ports/README.md:37`, `:48`). I: unmapped host item/throw/special behaviors may be lost until rewritten. |
| Ultimate Kirby | Preserve assets/normals and supported overrides; explicitly implement inhale/capture/copy/hat, paired clips and remaining specials. V: current pipeline is not full fighter-code translation (`ports/README.md:12`), proof-of-life is narrower (`:66`). Migration is not automatic parity. |
| Meta Knight | Preserve Geno specials/glide/root-motion and scripts; replace m-ex model/animation/sound/UI registration. V: current Halberd is m-ex plus Geno (`ports/README.md:11`). I: remaining callbacks/host assumptions need local inspection before claiming no loss. |

Gain independent slots, portable authored folders, named resources and complete ownership. Lose reliance on opaque PPC or accidental donor behavior; this becomes explicit rewrite cost. Compare old/new on identical inputs: effective attributes, states/clips, movement, hitboxes/damage, article lifetimes, FX/SFX events and rollback hashes. Every difference needs repair or accepted loss; install success is not acceptance.

## 6. Vanilla disc, one folder (P)

All non-retail runtime dependencies live in the folder. No absolute paths, lane dependencies or incidental mounted files. Explicit package dependencies are allowed, but default export bundles authored dependencies for self-contained sharing. No disc-derived DAT/PlCo/MxDt/menu/texture/animation/audio bytes ship.

Typed references include `{retail: "mario", component: "model", costume: 0}`, `{retail: "mario", clip: "Attack11"}`, `{retail_effect: "hit.normal"}` and `{retail_sound: {bank: "mario", entry: "jump"}}`. A versioned resolver maps logical names to the user's disc and checks revision/content. Missing/wrong assets refuse admission, not substitute another fighter. Package owns states/moves while using referenced visuals. Manifest records provenance; checker flags archive overlays/generated extracted assets for review. Hash matching alone cannot establish ownership/provenance.

## 7. Tooling and the human author (P)

Extend existing check/asm/disasm/export/schema tools. V: current commands and portable pointer restrictions are documented (`tools/geno/README.md:7`, `:61`). Checker validates complete graph/common coverage, symbols, bone roles, clips, capsules/ECB, grab pairs, resource budgets, Lua contract, provenance and admission; errors include JSON/source locations. Retain v5 schema support. Assembler adds symbolic relocations, not changed escape ids; exporter emits manifest, words and deterministic conversion/loss reports.

Proposed command: `python -m tools.geno.new hero --base mario --output mods/hero`. Generate a complete playable native clone using retail references, no copied disc data/PPC. Start with an explicitly supported Mario behavior preset; fail for unsupported donors rather than promise every fighter. Author changes attributes, then a normal, specials/articles and own art. Blender add-on exports armature/skins/clips/sockets/capsules/ECB and validation overlays; glTF CLI supports other tools. Runtime HSD conversion requires no extracted template.

LAB shows identity, effective inheritance, named bones, sources, phase budgets and faults. Scalar/script edits with unchanged layout reload atomically at a paused offline boundary, clear history and restart current action. Skeleton/state layout/article pools/callbacks/identity/assets restart match; old history must never reference freed descriptors. V: today's reload already distinguishes layout and file changes (`melee/docs/geno.md:710`, `:715`, `:721`). P: extend that transaction to complete definitions; prohibit online reload.

Guide packets become: 0 ownership/coexistence; 1 generate/play vanilla clone; 2 effective states/clips; 3 first move/throw; 4 attributes/phase overrides; 5 article/FX/audio; 6 Blender/skeleton/animations/costumes; 7 LAB/rollback; 8 provenance/export; 9 port migrations/loss reports; 10 gaps/budgets. Keep legacy attach lessons clearly available. Guide edits belong to later implementation, outside this packet.

## 8. Build order: every slice ends playable

**I:** ranges are engineer-weeks for one experienced implementer, excluding asset creation/owner testing. They are unmeasured planning estimates, not delivery commitments. Table/registry unknowns create substantial variance.

| Slice | P: engine and tooling work | P: playable acceptance | I: size |
|---|---|---|---|
| 1: retail-reference native clone | Source-independent roster registration; minimal selection/results defaults; admission/resident mapping; attributes/descriptors; every-state dispatcher; native donor adapters/script bindings; dynamic profiles; snapshot/hash foundation; new/check/export template | Vanilla Hero selected beside retail/m-ex; full stocks, all normals/specials/grab/throw/shield/ledge/item/death/rebirth. Changed owned move/attribute. No Hero MxDt/PPC calls. Coverage and save/restore/repeated-input hashes. | 5â€“8 weeks |
| 2: own articles/FX/audio and Lua | Named audio/resources, article graphs/hurtboxes/pools, typed-state sandbox, queues/RNG/handles, resim presentation and real netplay/replay identity integration | Hero custom projectile/sound and charge/counter Lua special; reflect/absorb/despawn; rollback across spawn/hit; peer mismatch refusal. | 4â€“7 weeks |
| 3: own model/skeleton/clips | Clean-template HSD generator; Blender/glTF; semantic roles/independent banks; skin/pose audits; hurtboxes/ECB and paired clips | Original-art Hero performs full combat/common states with correct sockets/grab/victim/ledge/item behavior; owner pose/collision QA and memory checks. | 4â€“7 weeks |
| 4: full presentation/integration | Custom CSS/stock/name/announcer, costumes/teams/results, Kirby copy/hat, AI hints/planner, stable records/optional trophies; residual identity widening | Full versus/results; team costumes, CPU recovery, Kirby copy/loss and native saved records without retail corruption. | 4â€“7 weeks |
| 5: customer migrations | Private fighter first, then Sora/Kirby/Meta Knight; conversion reports/manual rewrites, guides and parity scenarios | Each folder boots vanilla without m-ex/PPC; scripted comparison plus owner gameplay/visual acceptance per fighter. | 2â€“5 weeks/fighter; Kirby/capture may take more |

Slice 1 owns all resolved states by definition/inheritance, not custom algorithms for every common state. Minimal selection/results comes first; slice 4 custom art cannot excuse earlier crash/unselectability. Customer need may reorder slices 2/3. Online use waits for full admission/snapshot/Lua contracts. Initial play uses native declarative behavior before Lua is added.

Validation plan: malformed schema/assets/relocations, graph coverage, mixed backends and exhaustion refusal; deterministic replays; save-modify-restore across state/grab/copy/article edges; identical rollback hashes; peer/replay mismatch; transactional offline reload; memory bounds/fuzzing. Owner accepts controller feel, art/audio and port parity separately. None of these executable checks was run for this design.

## 9. Owner questions and recommendations (P)

1. **Should Geno own complete definitions inheriting Melee common behavior, or be a separate combat engine?** Recommend native definitions within Melee. This is the principal architecture decision.
2. **Should Blender/glTF compile to HSD or should skinned GXMS be introduced now?** Recommend offline HSD with a clean authored template; keep GXMS for rigid pieces initially.
3. **Should Lua retain arbitrary VM state or use typed snapshotted fields with stateless functions?** Recommend constrained typed state; arbitrary heaps/coroutines require a larger snapshot project.
4. **Is alias-limited mixed-backend admission acceptable initially?** Recommend honest refusal at exhaustion, then wide resident indices after a complete census.
5. **Which fixture drives the first slice?** Recommend a Mario-reference clone with an authored move, then private-port migration. This separates constructor correctness from unknown port behavior.
6. **How strict are missing resources/conversion losses?** Recommend optional presentation defaults, hard gameplay/skeleton/reference errors, and explicit accepted migration losses; no silent donor PPC.
7. **Must every fighter author Kirby/AI/trophy content?** Recommend generic AI, explicit no-copy and no trophy defaults. Complete format expresses them without making custom content mandatory for first play.
8. **What online platform scope is required?** Recommend same engine build and pinned math/Lua initially; cross-platform deterministic behavior needs dedicated tests.
9. **Approve the whole project or slice 1 first?** Recommend direction plus slice 1 first, with separate plans/acceptance for subsequent slices. This is a substantial engine project, not a small schema change.

## 10. Evidence limits and handoff

Read prompt/rules, workspace/game/Geno notes, learning ownership/gap/model packets, Geno reference/schema/tools, registry parser/caps, retail fighter structs/loading/dispatch, Mario state table, Kirby copy table, item structs, CPU command interpreter, CSS/stock/results/trophy surfaces, m-ex audio/copy adapters, roster report, ports overview, stage mesh exporter and HSD fighterbuild entry path. Anchors above substantiate current-state claims; proposals and estimates are labeled. No external importer or new capability is claimed to exist.

Before shipping, resolve unnamed ftData fields, exact CPU/record tables, common-transition bypasses, retail resolver symbols and Lua closure enforcement. These are discovery prerequisites and acceptance blockers. Only this spec and `_build/tmp/codex-geno-full-fighter-design-report.md` are owned by P7.

