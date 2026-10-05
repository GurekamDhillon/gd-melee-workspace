# Geno full fighter: build brief for slice 2, and the road through slice 8 (2026-10-05)

**Status: approved to build.** The owner approved slices 2 onward on 2026-10-05. This document is the brief an engine
lane executes; it needs no further planning round. It builds on `docs/superpowers/specs/2026-10-04-geno-full-fighter-design.md`
(the design) and supersedes that document's section 8 for ORDER only (see "Decisions taken", D1). Written read-only: nothing
was built, launched or committed while writing it, so every statement about code is a reading, not a run.

Tags: **[R]** read from source (path:line; paths are relative to the game checkout `melee/` unless they begin `tools/`,
`docs/`, `_research/`, `_build/`), **[I]** inferred, **[U]** unverified, needs a test. Line numbers move; re-grep before editing.

## The two milestones the owner cares about

"We need Geno to be able to express a full character instead of just what M-EX doesn't."

| milestone | first slice that reaches it | what is true afterwards |
|---|---|---|
| A fighter whose BEHAVIOUR is not its donor's | **Slice 2** (own move set) | A define with its own normals, its own grab and throws, at least one special of its own design, its own attributes and its own move tags. Still wears the donor's model and clips. |
| A fighter that no longer wears the donor's MODEL AND ANIMATIONS | **Slice 4** (own model, skeleton, clips) | Authored art and clips, no donor clip bank, no donor skeleton. Needs slice 3's named-resource resolver first. |

Slice 2 is a behaviour milestone only: after it a define is still a Mario clone in look, and it is still loaded through the
Mario preset ([R] `pc/platform/geno_define_registry.inc:151`, `return p >= 0 ? 0 : -1; /* native Mario only in slice 1 */`).
Slice 4 introduces the generic preset (`base: "none"`) that finally frees a define from the Mario tables.

## Roadmap at a glance

| slice | name | ends playable as | size (I, engineer-weeks) |
|---|---|---|---|
| 1 | retail-reference clone | BUILT. Vanilla Hero, Mario donor, one changed jab and walk speed | done |
| **2** | **own move set** | **Vanilla Striker: a second fixture visibly unlike Mario in how it fights** | 3-5 |
| 3 | own articles, FX, sounds, named resources | Striker throws its own projectile, plays its own sound, with the resolver that later slices reuse | 4-6 |
| 4 | own model, skeleton, clips, hurtboxes | an original-art fighter on the generic preset; donor model and clips gone | 5-8 |
| 5 | fighter Lua | a typed-state charge or counter special written as a Lua callback | 4-6 |
| 6 | presentation and integration | CSS, stock icon, results, announcer, costumes, Kirby copy, CPU AI hints, records | 4-7 |
| 7 | online identity and rollback certification | a Geno define fighter in a real two-client online match | 3-5 |
| 8 | customer migrations | Sora (`ultimate-trail`) and other ports move onto the format, one at a time | 2-5 per fighter |

Estimates are unmeasured planning figures (the design's own caveat applies).

## Decisions taken

Where the design asked the owner a question, or this plan needed a call, it is decided here with the reason and what would
reverse it. Reverse only on the stated condition.

| # | Decision | Reason | Reversed if |
|---|---|---|---|
| D1 | Order: 2 move set, 3 articles/FX/audio/resolver, 4 model/skeleton/clips, 5 Lua, 6 presentation, 7 online, 8 migrations. This splits the design's slice 2 in two and puts art (the owner's milestone) before Lua. | The design itself says Lua comes after declarative play ("Initial play uses native declarative behavior before Lua is added", spec line 190) and that customer need may reorder 2/3. Slice 1's own script VM (CHG checks, variables, IF) already expresses a lot [R `pc/geno/geno.h:28-80`], so Lua is not the next blocker; the donor's model is. | A customer move cannot be written with the opcodes and states of slices 2-3: swap 4 and 5. |
| D2 | Defines stay offline-only until slice 7. Slices 2-6 add every new gameplay state to snapshot-covered memory and to the rollback hash as they go, so slice 7 is certification, not retrofit. | Online is refused today at three places [R `src/melee/ft/ftdata.c` GenoDefine_Load assert, `pc/geno/geno_define_data.inc:91`; `pc/platform/gw_runtime.c:1836`; `docs/geno.md` section 22]. `_research/envoy-netplay-scoping-2026-10-05.md` section 6 rule 7: "every new native modifier state added without a hash word creates silent desyncs". | The owner wants early two-client tests: pull task S2-7 forward, it already exists. |
| D3 | The donor stays Mario through slice 3. Other retail donors are not added. | The define loader copies Mario-typed structs [R `geno_define_data.inc:25-36,92-107`: `ftMario_DatAttrs`, `GenoDefine_MarioBaseline`, `ftMr_MS_SelfCount`], and every selection, audio and costume path maps a define to CK 8 [R `src/melee/gm/gm_1601.c:754,4410`; `src/melee/lb/lbaudio_ax.c:1756`; `src/melee/mn/mncharsel.c:6524`]. A second donor multiplies all of that for no gain; slice 4's generic preset removes the need. | A customer insists on a Marth- or Fox-shaped base before slice 4. |
| D4 | Slice 2 changes the file format only additively: `"geno": 7` (and `GENO_VERSION` 7) marks a define file that uses the widened attribute list, `special_attributes` or `fx_bindings`. v6 files, including the Hero, keep loading unchanged. | Today a newer file read by an older engine is "read for what it knows" [R `pc/platform/geno_registry.c:1303-1305`], which would silently drop new attributes; a version bump makes the mismatch visible. The content id hashes the whole entry [R `geno_registry.c` `gn_hash_node`], so ids of v6 entries do not change. | Never needs reversing; if the lane finds the bump breaks existing ids, hash v7 fields only. |
| D5 | Articles remain refused for defines in slice 2; the second fixture's specials use no projectile. | Articles need a per-define kind range and a model-region decision (slice 3). The refusal list is [R `geno_define_registry.inc:9-11`: articles, fx_bindings, special_attributes]; slice 2 lifts only the last two. | Striker's design needs a projectile to read as "not Mario": it should not, see S2-6. |
| D6 | A define's declared move tag WINS over the tag derived from the motion id, for defined kinds only. | Today the motion-id tag wins and a declared tag is consulted only when it is 0 [R `pc/gameworld/script_hit_context.inc:45,52`], so a define that rebinds its forward tilt to a smash-like script still reports `tilt`. Scoping to defines keeps every retail and attach fighter byte-identical. | The roguelike's modifier lane objects (it reads tags by motion): then give the fixture's moves the motion-derived tag and declare only for states 0x400+. |
| D7 | The Mario-specific rows (motion 341..350) are never deleted; they become unreachable once the eight special entries are bound to Geno states. | Deleting rows changes the table geometry the Mario preset copies [R `geno_define_data.inc:107`, `ftMr_MS_SelfCount` at `src/melee/ft/kinds/ftMario/forward.h:44`]. Unreachable is enough for slice 2; slice 4's generic preset removes them. | n/a |
| D8 | Rollback hash: fold a digest of `GenoState` for defined kinds only into `RB_GameHash`, in slice 2. | `RB_GameHash` hashes seed, motion, position, velocity, percent, facing and the interrupt-window word, nothing from Geno [R `src/melee/ft/fighter.c:3967-3990`]; `GenoState` (variables, change checks, move vars) is snapshotted but not hashed [R `pc/geno/geno_state.h:1-8`]. For a define whose behaviour is all script variables, divergence would be invisible until it moves a body. Defined kinds only means no existing hash changes. | The hash cost shows in the 8.3 ms budget (it will not; it is bytes per fighter per frame). |
| D9 | The authoring convenience `moves` (a per-move block that expands to a `subactions` overlay plus a `common_states` row) lives in `tools/geno` and compiles to the existing keys. The engine reads no new key for it. | Keeps the engine surface small and the stable encodings untouched; one place to evolve the sugar. | n/a |
| D10 | Fixture 2's working name is "Vanilla Striker", key `vanilla-striker`. | A name is needed to write tests; names are the owner's taste (see open questions). | Owner renames: a grep-and-replace of one folder and its tests. |
| D11 | Retail code that switches on `fp->kind` treats a define as an unknown fighter and takes the default arm. That is accepted in slice 2 and documented, not patched. Sites listed in S2-5. | Patching retail switches to know about defines is slice 6 (AI) work; for slice 2 the default arms are harmless for a ground-and-air fighter [I]. | A default arm is found to misbehave in the S2-9 sweep: fix that site only. |

## 1. Where slice 1 actually stands (read from source)

### 1.1 What a `define` is today

A define is a `fighters[]` entry with `"define": {key, name, base, common, resources}` in a `geno: 6` file. All five strings are
required, `base` must be `"mario"`, `common` must be `"melee.common.v1"`, `resources` must be `"retail:mario"` [R
`pc/platform/geno_define_registry.inc:4-25`]. The parser refuses an entry that also has `attach`, `articles`, `fx_bindings` or
`special_attributes` (line 9-11) and `common_states` over 64 rows (line 50). It accepts and then runs the SAME v1/v2/v5
parsing an attach entry gets, because `gn_add_fighter` calls `gn_add_v2`, `gn_add_v5` and `gn_add_v1` for both [R
`pc/platform/geno_registry.c:1198-1260`]. So a define can ALREADY carry: `attributes`, `jumps`, `hooks`, `states` (Geno states,
motion 0x400+n), `specials`, `motion_anims`, `subactions` overlays, `on_land`, `common_states`, and `move_tag` declarations.
What slice 1 added is the loader that makes that a standalone kind.

Loading [R `pc/geno/geno_define_data.inc`]:
- Kind: each define gets an unused resident alias, CK 127 downward to 34 (so FighterKind 126 for the first), occupied m-ex
  slots skipped; refusal with a log on exhaustion [R `geno_define_registry.inc:97-123`; `docs/geno.md` section 22].
- `GenoDefine_InitKinds` copies Mario's ~40 per-kind callback tables (OnLoad, OnDeath, eight special entries, item
  pickup/drop, knockback, demo callbacks...) into the new kind (lines 52-72), sets the costume list to Mario's count (77),
  binds CK to kind (79).
- `GenoDefine_Load` (line 86) copies Mario's `ftData` root, common attributes, `ext_attr`, animation descriptors and the
  per-kind common motion table (341 rows) and Mario's 10 specific rows into per-kind copies, rewrites each animation row's
  owner kind id (97-103), then `GenoGame_DefineApplyRows` applies `common_states` (rows 0..350) [R
  `geno_define_rows.inc:6-37`: `like`, `subaction`, `flags`, `move_id`, and the `anim/iasa/phys/coll` callbacks by registered name].
- Spawn: `GenoDefine_BindFighter` points the fighter at its own two row tables (line 116).
- No PowerPC: an entry probe counts interpreter attempts per kind and refuses them [R `geno_define_registry.inc:194-216`,
  `geno_define_data.inc:127`]; the log says `interpreter attempts 0`.
- Memory: profile storage grows dynamically, descriptors and per-profile rows come from a 2 MiB static, snapshot-covered
  arena [R `pc/geno/geno_profile_storage.h:5`; `docs/geno.md` section 22].

### 1.2 Ownership table

"Own" = the define package can change it today. "Donor" = inherited from the Mario preset or from retail common code, and the
package cannot change it. "No" = impossible today. The right-hand column is the slice that closes it.

| Area of a fighter | Own today | Donor today | Impossible today | Closed by |
|---|---|---|---|---|
| Identity: key, display name, content id | Yes: key, name, id hash over the entry and overlay words [R `geno_registry.c:1262-1285`; `geno_define_registry.inc:19-34`] | Resident id is boot-assigned, not the author's | | 2 keeps; wide ids 6 |
| Roster, CSS icon, portrait, nameplate, results pose, announcer, stock icon | Name only | All of it is Mario's: selection, costume count, audio bank, CSP all map CK to CK 8 [R `gm_1601.c:754,4410`; `lbaudio_ax.c:1756`; `mncharsel.c:6524`; `gmfrontend_select.inc:334`]. The spike saw the Mario stock icon and Mario's red plate [R `_build/audit-20261003/geno-envoy/PROGRESS.md` item 6] | A custom icon, portrait or announcer | 6 |
| Attributes (common struct) | 40 named fields, one table [R `pc/geno/geno_game.c:888-937`]. `ftCo_DatAttrs` has about 80 members [R `src/melee/ft/types.h:752-819`] | The rest, including every landing-lag field (`normal_landing_lag` is read at `ftCo_Landing.c:127`), dodge, shield, ledge and damage fields [I: absent from the table] | | **2** (S2-2) |
| Special attributes (the fighter's own parameter block) | Not for a define (refused). The loader already gives each kind its own `ext_attr` copy [R `geno_define_data.inc:95`], so it is safe to admit [I] | Mario's block | | **2** (S2-3) |
| Common states (stand, walk, dash, jumps, shield, rolls, ledge, damage, etc.) | Rows 0..340 can be rebound: animation row, flags, move id, four callbacks by registered name, `like` [R `geno_define_rows.inc`] | The algorithms (versioned `melee.common.v1`), input arbitration, and every callback name outside the registered list | New callbacks | 2 uses what exists; 5 adds Lua phases |
| Grounded attacks (jab, dash attack, tilts, smashes) | Script words via overlays, and the row binding (`common_states.subaction`). A jab is proven (Hero). Hitbox, timer, GFX/SFX/throw words and Geno escapes are available | Mario's animation CLIP for any row: only the 303 installed rows can be chosen [R `geno_define_registry.inc:73-85`: subaction 0..302] | A clip that Mario does not have | 2 (scripts), 4 (clips) |
| Aerials and landings | Same mechanism. Landing lag lives in attributes (`landing_*`), which are not exposed | Landing lag values | | **2** (S2-2) |
| Specials with their own states | Geno states (`states`, behaviours `geno.air/ground/anim_motion/glide/tornado/drill/cape`) bound by `specials` for all eight entries [R `docs/geno.md` 16.1-16.2; the eight sites ask `Geno_SpecialEnter` first: `src/melee/ft/kinds/ftCommon/ftCo_Attack100.c:61,100,139,165`, `ftCo_SpecialAir.c:29`, `pc/geno/geno_game_v2.inc:1075`]. Not exercised by any define test or fixture [R: Hero uses none; `geno_define_tests.inc` has none] | The eight unbound entries run Mario's native special code, inherited by `GD_INHERIT(ftData_SpecialN)...` [R `geno_define_data.inc:55-58`] | A generic charge or projectile behaviour | 2 proves; 5 for Lua |
| Articles and projectiles | No (refused) | Mario's fireball, spawned by native code that checks the base kind [R `src/melee/ft/kinds/ftMario/ftmariospecialn.c:124`: `Geno_DefineBaseKind(fp->kind) == Ft_Kind_Mario`] | Own article kinds, owned attributes | 3 |
| Grabs and throws | Scripts of the throw subactions (same overlay route); throw words exist [R `tools/geno/reference.md`] | Grab joints, victim skeleton and paired thrown clips (the loader preserves the generic victim author id, `geno_define_data.inc:100-103`) | Own victim animations | 2 scripts, 4 clips |
| Animations and their source | `motion_anims`, `subactions`, rate [R `docs/geno.md` 15.5] | The clip bank is Mario's (`PlMrAJ.dat` loads for kind 126 [R spike item 4]) | An own bank | **4** |
| Model, materials, costumes | No | Mario's, costume count 8 [R `geno_define_data.inc:77`] | An own model | **4**; costumes 6 |
| Hurtboxes, ECB | No (reads exist in the LAB [R `docs/geno.md` 14.3]) | Mario's | Own capsules/ECB | 4 |
| Sounds and voice | `sfx` words play installed ids | Mario's bank and voice | Own named sounds | 3 (sounds), 6 (voice, announcer) |
| Effects | `fx_bindings` exist for attach; refused for define [R `geno_define_registry.inc:10`] | Mario's effect bank | | **2** admits bindings, 3 adds fighter-owned banks |
| AI behaviour | No hints | Retail CPU tables by kind; a define takes default arms of every `fp->kind` switch, e.g. recovery [R `src/melee/ft/ftcpuattack.c:1106`] | Own AI hints | 6 |
| Item interactions | Pickup/drop callbacks inherited (`ftData_OnItemPickup...` in the copied table [R `geno_define_data.inc:58-60`]) | Mario's | Own hold animations | 6 |
| Kirby copy and hat | No | Kirby's hat tables are indexed by retail kind (`src/melee/ft/kinds/ftKirby/ftkirby.c:3371`, `:3932`, `ftkirbyspecialmario.c:38`); a define is not a hat source [I: no define entry] | A copy ability | 6 |
| 1P modes: intro, target test, credits | Classic cleared to credits by the spike with the Hero [R spike items 4, 6]; the intro copy has 16 subaction rows and the overlay is now skipped quietly [R `geno_game.c:592-601`] | Intro/results models (Mario) | Own intro/results | 6 |
| Online | Refused [R D2 sites] | | | 7 |

### 1.3 The Hero, as shipped [R `pc/geno/mods/vanilla-hero/geno.json`]

One define, one attribute (`walk_max_vel` 1.8), one overlay (subaction 46, a 12% root-bone jab), no states, no specials, no
tags. The spike [R `_build/audit-20261003/geno-envoy/PROGRESS.md`] played a whole Classic run and a roguelike Envoy run with it
(0 asserts), measured it at Mario's frame cost (frame_work 5.13 vs 4.87 ms, +0.26, noise level), and listed what is untested:
only a Mario donor; tags inherited from the donor; an L-cancel timing miss on neutral air; intro-scene overlay refusal (since
quieted); name readback (since fixed). Not seen: any state or special on a define, looks, a non-Mario donor.

### 1.4 Facts that shape slice 2

1. A define is today a Mario clone plus the attach machinery; "own states" are reachable with no new engine concept [R 1.1].
2. Ten retail sites switch on `fp->kind`; for a define they take the default arm. Read: `ftCo_800C70D0.c:28`, `ftCo_800C7178.c:28`,
   `ftcpuattack.c:1106,1446`, `ftCo_0A01.c:4487`, `ftCo_Landing.c:49` (resets Mario's tornado/cape flags on landing: skipped for a
   define, harmless unless the define runs Mario's special rows), `ftkirby.c:3371,3932`, `player.c:52` [R].
3. The tag rule (D6) and the missing landing-lag attributes (S2-2) explain two gaps the spike hit: tags carried by the donor,
   and a CPU L-cancel macro that is timed from `co_attrs` the author cannot set [R `pc/platform/gw_script_cpu_ctl.inc:305-322`
   lists `landing_*` among the macro attributes; the geno table lacks them] [I that this explains the miss; S2-9 checks].
4. GenoState (variables, checks, move vars) is snapshotted game memory and unhashed (D8).
5. The suite stood at 296/296 at the 2026-10-05 handoff [R `docs/HANDOFF-2026-10-05.md`].

## 2. Slice 2: own move set

### 2.1 Scope

A define that fights unlike its donor, with every ground and air normal, a grab and throws, and the full set of eight special
entries bound to its own states, written by an author in one folder, on the vanilla disc, still wearing Mario's model and
clips.

**In slice 2:** complete attribute surface; `special_attributes` and `fx_bindings` admitted for defines; own scripts for
jab(s), dash attack, three tilts, three smashes, five aerials and their landings, grab, pummel, four throws; four grounded and
four aerial specials bound to Geno states built from existing behaviours and the script VM; declared move tags that win for
defines; a rollback-hash word; the second fixture and its demo; authoring tools (check report, preview table, `moves` sugar).

**Out of slice 2:** articles and projectiles (3); named resources, own sounds (3); any model, clip, skeleton, hurtbox change (4);
Lua (5); CSS, stock icon, results, announcer, costumes, Kirby copy, AI hints, records (6); online (7); any other donor (D3);
migrating Sora (8, but see 2.6); ledge attacks, get-up attacks, taunts, edge cases of item holding (they inherit; touched only if
the sweep S2-9 finds them broken).

### 2.2 Entry condition

Game checkout at a build where `geno_define_*` tests pass (the suite 296/296 of 2026-10-05 or later), the Hero loads (log
`native define kind 126 loaded ... interpreter attempts 0`), and the engine slot is free. Verify before task 1:
`grep -a "native define kind" _build/melee-pc.exe` (fact 1 of the workspace notes: verify the exe, not the source).

### 2.3 Tasks, in order

Each task: files, native tests, in-game acceptance, determinism, risk. Test registration pattern: the registry half of a test
goes in `pc/platform/geno_define_tests.inc` (included at `pc/platform/geno_registry.c:2235`, registered near `:2240`); the game
half goes in `pc/geno/geno_define_snapshot_tests.inc` (included at `pc/geno/geno_tests.c:3412`, registered in
`GenoTestRegisterAll` at `:3413`). Python tests go in `tools/geno/test_define.py` and `test_native_define.py`.

#### S2-1 Baseline probe and a second fixture skeleton (no engine change)

- Files: new folder `pc/geno/mods/vanilla-striker/` (`mod.json`, `geno.json` with only the define header, `README.md`); copy of the
  Hero's layout; `tools/geno/new.py` already creates one (`python -m tools.geno.new vanilla-striker --name "Vanilla Striker"
  --base mario --output ...`), use it.
- Tests: `python -m tools.geno.check` on both fixtures passes. No native test.
- Acceptance: the unmodified Striker loads beside the Hero in one LAB match (`mode=lab;p1=geno:vanilla-hero;p2=geno:vanilla-striker`)
  with two distinct kinds (126 and 125, or the log's pair), both `interpreter attempts 0`, and the log shows two definitions.
  This proves two defines coexist, which no test or run has shown [I: the spike used one].
- Determinism: nothing new. Risk: low. Exposes alias-order or arena issues with two defines early.

#### S2-2 The attribute surface

- Files: `pc/geno/geno_game.c` (the `geno_attrs[]` table, lines 888-937: append entries for the remaining scalar members of
  `ftCo_DatAttrs`, `src/melee/ft/types.h:752-819`: all landing-lag fields, the normal/aerial landing lags, dodge and roll
  speeds, shield fields, ledge fields, damage and knockback fields that are scalars); `pc/geno/geno.h:248` (`GENO_MAX_ATTRS` 48
  counts entries per profile, raise to 128; check `gn_profile` arrays sized by it); `tools/geno/schema.py` and the generated
  `tools/geno/geno.schema.json` (`python -m tools.geno.schema`, then `--check`); `docs/learn/geno-fighters/template/geno.json.md`.
- Order rule: APPEND only. Parsed profiles store the table index [R `geno_registry.c` `attr_index`], and the id hashes the JSON
  text, not the index, so appending changes no existing id [I: confirm in the test].
- Tests: extend `geno_attr_table` (`pc/geno/geno_tests.c:3421`) to assert every table entry's offset is inside the struct and the
  original 40 names keep their indices; new `geno_define_attrs_v7` (registry half): a v7 define with 60 attributes parses, an
  unknown name is refused with the name in the log (a define is strict; attach stays lenient).
- Acceptance: Striker sets a landing lag for nair and a shield size; read back with `gd.cpu_attrs(port)` and the LAB's
  attribute readout; a CPU `lcancel` macro on Striker's nair now reports `lcancel` with the author's lag (this closes the
  spike's timing miss if the cause was the donor's lag [I]).
- Determinism: attributes are written into `fp->co_attrs` at spawn and re-apply [R `docs/geno.md` 15.5 text], inside the fighter,
  which the snapshot covers. No new global state. Risk: low; the one trap is the profile arrays sized by 48.

#### S2-3 Admit `special_attributes` and `fx_bindings` for defines; version 7

- Files: `pc/platform/geno_define_registry.inc` (line 9: accept `version == 6 || version == 7`; remove `special_attributes`
  and `fx_bindings` from the refusal; keep `articles`); `pc/geno/geno.h:16` (`GENO_VERSION` 7); `pc/platform/geno_registry.c`
  (nothing else: the shared parsers already run); `tools/geno/define.py`, `check.py`, `schema.py` (a v7 define may use the two keys;
  v6 may not, with the message "needs geno: 7").
- Why safe: each define kind owns an `ext_attr` copy and the special attributes are written into it [R `geno_define_data.inc:95`;
  `geno_game.c:960-985`]; fx bindings are keyed by profile and state, not by Mario [I: confirm in the test].
- Tests: `geno_define_v7_parse`: v7 define with both keys parses, the same entry as v6 is refused, the Hero's id is unchanged
  (compare the hex id to a literal captured from the current engine; store the literal in the test); a define with `articles`
  is still refused.
- Acceptance: Striker overrides one special attribute word that Mario's fireball-free neutral does not read, and one `fx_bindings`
  file binds a retail-installed effect to Striker's jab; the effect plays only for the Striker (LAB `lab events`).
- Determinism: special words live in the fighter's attribute buffer (snapshot); fx bindings are presentation. Risk: low.

#### S2-4 Own move tags win for defines (D6)

- Files: `pc/gameworld/script_hit_context.inc` (function `script_hit_family_move`, lines 36-72: for a profile that is a define
  (`Geno_DefineBaseKind(fp->kind) >= 0`), consult `Geno_CommonMoveTag` / `Geno_StateMoveTag` / overlay tag BEFORE the motion-id
  tag at line 45; retail, m-ex and attach fighters take the old path unchanged).
- Tests: extend `test_geno_move_tags` (`pc/platform/geno_define_tests.inc`): a define row `motion 53` (a tilt) declared
  `smash` reports smash through the registry accessor; add a game-half test `geno_define_hit_tag` driving
  `script_hit_family_move` (the existing hit-context tests in `pc/platform/gw_script_gameplay_events_tests.inc` are the template)
  proving an attach Kirby and a retail Mario are unchanged by the edit.
- Acceptance: LAB, Striker's forward tilt declared `smash` with a hit-rule on `smash` (the roguelike's `g.hit_rules` harness,
  `pc/tests/envoy_hit_rules.lua` is the model): the rule fires on the tilt; the same rule does not fire on a Mario tilt.
- Determinism: tags are read-only data from the registry. Risk: low. Compatibility: this is the layer of section 4.

#### S2-5 Overlay and state budgets, and the donor-site review

- Files: `pc/geno/geno.h:252-255` (`GENO_MAX_OVERLAYS` 64 per profile, `GENO_POOL_WORDS` 16384 words for ALL profiles, 64 KB; a
  full move set is about 25 overlays of 40-150 words, so a define can reach ~4k words; two such defines plus Sora's and MK's
  profiles may not fit [I: measure]); `pc/platform/geno_registry.c` (`GN_MAX_SLOTS` 256 at `:453`); `pc/geno/geno_game_v2.inc`
  (`GENO_MAX_STATES` 48 per profile: Striker needs about 12-16).
- Work: (a) raise `GENO_POOL_WORDS` to 65536 (256 KB) only if the measured need exceeds 60% of 16384; the pool is a game global and
  the snapshot grows with it [R `docs/geno.md` 15.7 "The overlay pool ... game globals"], so state the snapshot cost in the log;
  (b) add one boot log line `geno: define budgets: overlays N/64, pool W/POOL, states S/48, arena B/2097152` per define;
  (c) write the donor-site list (fact 2 of 1.4) into `docs/geno.md` section 22 as "known default arms".
- Tests: `geno_define_overlay_budget`: a define with 40 overlays and a 1500-word pool parses; 65 overlays is refused with the
  message naming the limit; a second define loaded afterwards still gets its slots.
- Acceptance: boot log with both fixtures shows the budget lines and no refusal. Determinism: pool contents are written once,
  idempotent. Risk: medium (snapshot size grows if the pool grows; check the rewind history memory).

#### S2-6 Striker's move set (content)

The fixture is what proves the milestone; it is content, written with the tools of S2-8, so do S2-6 and S2-8 together.

Design of "Vanilla Striker" (a rushdown fighter, deliberately unlike Mario in speed, frame data and specials). Everything below
uses only mechanisms that exist, stated so the lane can check feasibility, not a promise of feel [I]:

| slot | design | mechanism |
|---|---|---|
| attributes | fast dash, high run speed, light weight, low gravity, two air jumps, short landing lags | S2-2 attributes; `jumps.max` |
| jab | a 3-hit jab chain with its own windows | overlays on the three jab subactions + `jab_2_input_window`, `jab_3_input_window` attributes [R `geno_game.c:926-927` are in the table] |
| dash attack | a long lunge that carries momentum | overlay + `PUT FWD_VEL` |
| tilts, smashes | own damage, angles, hitbox shapes, timings; one smash with `REHIT` multi-hit | overlays with `hitbox`, `REHIT`, `HBDMG` words |
| aerials | five aerials, one an autolink (`LINK`) drag-down, with landing lags from S2-2 | overlays + attributes |
| grab, throws | own pummel damage and throw damage/angles; one throw is a combo starter | throw words (`throw_hitbox`) in the throw subactions |
| neutral special | a charge: hold B, release to dash-strike; charge length in `MOVE_I0` | Geno states `geno.ground`/`geno.air` + `CHG` checks on `HELD`/`NOT` + counter in move variables |
| side special | a lunge using root motion | `geno.anim_motion` state |
| up special | a vertical rise with a steering window | `geno.air` + `PUT VEL_Y`, `GET STICK_X` |
| down special | a counter: hit during the window = counter-strike | counter windows (`docs/geno.md` 19.4) via the existing `on_hit` machinery |
| tags | every row declared; specials `special`, counter declared | S2-4 |

- Files: `pc/geno/mods/vanilla-striker/geno.json`, `moves/*.genoasm`, `moves/*.words` (built by the assembler, committed like
  the Hero's), `README.md`; `melee/pc/scripts/examples/demos/geno-define-striker/` (a pad-driven demo, pattern of the existing
  `geno-define` demo's `scripts/main.lua`).
- Tests: `python -m tools.geno.check pc/geno/mods/vanilla-striker` clean; a native test `geno_define_specials` (game half) that
  builds the Striker's state table headlessly and checks, for each of the eight `Geno_SpecialEnter` calls, that the target
  state is entered and Mario's native special code is not (the `geno_v2_specials` test at `pc/geno/geno_tests.c:1312-1316` is the
  template); the interpreter-attempt counter stays 0.
- Acceptance (in game, LAB, vanilla disc): `gd.player(1).motion` after each input equals the expected 0x400+n for all eight
  specials; readback of frame data per move (`gd.timeline`) differs from Mario's jab/tilt/smash tables for at least 20 of the 24
  rows; the neutral special charges and releases; the counter reflects a hit. Not acceptable: any special that falls back to
  Mario's code (log line `interpreter attempts` > 0, or a Mario fireball spawns).
- Determinism: scripts only use game RNG (`RAND`, not drawn in fast-forward [R `docs/geno.md` 15.7]) and fighter-local variables.
  No host time. Risk: medium (feel; the donor's clip dictates timing visually, and the first wait of a script is read as frame
  N-2 [R `docs/geno.md` "Frame-counting convention"]).

#### S2-7 Rollback hash word and snapshot proof (D8)

- Files: `src/melee/ft/fighter.c` (`RB_GameHash`, lines 3967-3990, add one `ftRb_Mix` of `GenoDefine_StateDigest(fp)` which returns
  0 for every kind that is not a define); `pc/geno/geno_define_data.inc` (the digest function: FNV over `la_i`, `ra_i`, `la_f`
  bits, `ra_f`, `move_i`, `move_f`, `checks`, `action_time`, `hold_*`, `hit_*`, `atk_connected*`, `stun_bonus` of the fighter's
  `GenoState` block; exclude the diagnostics counters `hook_calls`, `resets`, `changes`, `state_entries`, `art_spawned`,
  `counters`, which are not simulation inputs [I: confirm none feeds a decision]); declare in `pc/geno/geno_define_game.h`.
- Tests: `geno_define_state_hash` (game half): digest is 0 for a non-define; changes when `move_i[0]` changes; unchanged by
  a diagnostics-only change; equal after `snap_save`/mutate/`snap_load` (the pattern of `test_geno_define_snapshot`,
  `geno_define_snapshot_tests.inc:6-34`); the retail `RB_GameHash` for a match with no define is bit-identical before and after
  (record a hash from the old build in the test as a literal).
- Acceptance: with `MELEE_SYNCTEST_CURATED=1` (`docs/HANDOFF-2026-10-05.md`, the bench note) a 60-second Striker vs Hero CPU
  match shows no curated mismatch; `gd.rewind_test` with the Striker mid-charge restores the charge counter. Note the known
  open item: the bench SyncTest mismatches after long sustained combat with or without Turbo, unexplained, not caused by this
  [R handoff]; compare against a Mario-vs-Mario control run before blaming the digest.
- Risk: medium: the hash is shared by all netplay; the "defined kinds only" guard is the whole safety, so review it first.

#### S2-8 Author tooling for a move-set author

- Files: `tools/geno/define.py`, `check.py`, `new.py`, `export.py`, new `tools/geno/report.py`, `tools/geno/test_define.py`.
- (a) **Validation with good messages**: `check` reports the unresolved: a `common_states` motion out of 0..350, a `subaction` out
  of 0..302, a Geno state with a script containing IASA but callback none (the engine warns once at load [R `docs/geno.md` 16.2]:
  make it an error offline), a state never targeted by any special, `next`, `land` or CHG (unreachable), a special entry unbound
  (it runs Mario's code: warn "binds to donor"), a tag with a typo, an overlay with absolute pointers. Each error carries the JSON
  path and source line (the existing format [R `tools/geno/README.md`]).
- (b) **Effective-graph report**: `python -m tools.geno.report mods/vanilla-striker` prints the 351 motion rows with `own`,
  `inherited` or `donor-special (unreachable)` and the eight special entries with their bound state or `DONOR`. This is the
  ownership table of section 1.2 generated from a package, and the checkable definition of "not donor-dependent" for slice 2:
  zero `DONOR` entries and every common attack row `own`.
- (c) **Preview without the game**: the same command with `--frames` prints, per overlay, hitbox start and end frames, damage,
  angle, size and IASA frame, computed from the assembled words with the readout convention (hitbox live from action frame N-2).
  Preview of motion in game remains the LAB.
- (d) **`moves` sugar** (D9): `"moves": {"ftilt": {"motion": 53, "words": "moves/ftilt.words", "tag": "tilt"}}` expands at export to the
  overlay and the `common_states` row; hand-written keys still work. The exported `geno.json` contains only engine keys.
- (e) `new.py` gains `--template striker-skeleton` that emits the Striker's header and empty move stubs.
- Tests: `tools.geno.test_define` gains cases for each error; golden-file test for `report` on the Hero (expected: jab row `own`,
  walk attribute set, 350 rows inherited, 8 specials `DONOR`) and on the Striker (8 specials bound).
- Acceptance: an author who has only the README runs `new`, edits one move, `check`, `report` and sees the row flip to `own`
  (the owner can follow this in 10 minutes). Determinism: tools only. Risk: low.

#### S2-9 Compatibility sweep, performance and regression

- Files: tests only: new `pc/tests/geno_define_modifiers.lua` (patterned on `pc/tests/envoy_hit_rules.lua`), a note in
  `docs/learn/geno-fighters/10-known-gaps.md`.
- The sweep (in game, LAB, Striker as P1 and as P2): (1) modifier layer: move tags on every row, `g.hit_rules`, a crit
  (`gd.crit` with `tags`), armour (`fighter_armour`), a timed status, skill events (`short_hop`, `wavedash`, `lcancel`
  with the S2-2 lags) [R `docs/scripting.md`, spike items 3, 7, 9]; (2) `gd.cpu_assist` / script CPU macros timed from
  `gd.cpu_attrs` on the Striker; (3) stage switching: five retail stages, the same loop the stage lane used, with the Striker in
  the match; (4) six slots: Striker, Hero, Mario, a retail fighter, an m-ex fighter, an attach fighter in one six-player match;
  (5) savestate and rewind: save mid-neutral-special, run 3 s, load, the charge counter, motion and position match (the LAB's
  state library); (6) Classic to the credits with the Striker, plus an Envoy rule-host stage (the spike's runs, repeated);
  (7) the vanilla-disc rule: `grep` the package for any file other than text, `.words`, and `.json` (the exporter already
  refuses archives).
- Performance: profiler zones over about 900 frames, both CPUs level 7, frame_work and logic for Striker vs Mario (the spike's
  method [R spike item 8]). Gate: mean under the 8.3 ms target and within 0.5 ms of the Mario control; digest cost line.
- Regression: the full native suite; expected 296 + the new tests below; the existing 33 geno tests that slice 1's fix1 restored must
  still pass [R `docs/prompts/codex-geno-define-fix1.md`].
- Risk: the sweep is where default arms (fact 2) show up; fix the single site, do not widen.

#### S2-10 Docs and handoff

- Files: `docs/geno.md` section 22 (what a define can now do; known default arms; the budgets), `docs/learn/geno-fighters/11-defined-fighter.md`
  (turn the stub into a real lesson: a define with its own move set, tested), `tools/geno/README.md`, `docs/NEXT-SESSION.md` pointer,
  `docs/learn/geno-fighters/10-known-gaps.md` (rank what remains). Credit: the PSA-to-Geno cheat sheet conventions are Brawl's
  (already credited in `docs/geno.md` 15.6); no new outside source in this slice.

### 2.4 Native tests added (expected suite)

`geno_define_attrs_v7`, `geno_define_v7_parse`, `geno_define_hit_tag`, `geno_define_overlay_budget`, `geno_define_specials`,
`geno_define_state_hash`, plus the extended `geno_attr_table` and `test_geno_move_tags`: **six new registered tests, so the suite
goes from 296 to 302** (give or take tests other lanes add; count the delta, not the total). Python: new cases in `test_define.py`
and `test_native_define.py`, one `report` golden file.

### 2.5 Acceptance for the whole slice

**Owner's play script (10 minutes, LAB, vanilla disc):**
1. Launch `mode=lab` with P1 `geno:vanilla-striker` (human) against P2 `mario` (cpu0 set with `gd.cpu_mode(port,"stand")`).
2. Run the Striker's eight special inputs. Each does something Mario cannot (a charge, a lunge, a counter...). No fireball, no
   cape, no tornado appears. The log shows `interpreter attempts 0`.
3. Press every normal; read frame data (`gd.timeline`) beside Mario's: visibly different damage and timing.
4. Switch P2 to the Hero: two defines in one match.
5. Save a state mid-charge, advance, load: the charge resumes.
6. Run `python -m tools.geno.report` on the Striker: zero `DONOR` entries.
7. Play one Classic stage with the Striker.

**A reviewer should try to break:** (a) a define whose special points at a state with no `iasa` callback; (b) 65 overlays, 49
states, an attribute name that does not exist; (c) two defines binding the same alias after a hot reload (reload with a define
is refused today [R `docs/geno.md` 22]; keep that); (d) the Striker's counter hit by a multi-hit while a `REHIT` timer runs;
(e) a Striker landing during a Geno state on a platform (the `geno.air` and `both` collisions);
(f) the Striker grabbed during its charge (the grabbed state must leave the Geno state without leaving `ra_i` stale: the RA
bank resets on action change, LA and `move_*` do not [R `geno_state.h:32,66`]); (g) Kirby inhaling the Striker (a define is not
a hat source: must not crash, expected: no copy [I]); (h) the six-slot match with the Striker in slot 6; (i) the digest
changing for a non-define kind.

### 2.6 Migration of the existing ported fighters (what a later proof costs)

Sora (`ultimate-trail`) is an m-ex slot plus a Geno profile (`attach`), with Geno specials, effect bindings, articles and a
translated move set [R `ports/README.md:9-12`; `docs/MEX_PORT_STATUS.md`]. What slice 2 gives it: attributes and landing lags in
the same table, the report tool as a conversion-loss dashboard. What it cannot yet use: its articles (slice 3), its own skeleton
and clips (slice 4), its UI, voice and costumes (6). So moving ONE Sora move onto a define in slice 2 is possible only as an
experiment: take one grounded normal's overlay words out of its profile and bind them to the Striker (a Mario-body host) to
prove the words are portable, not to ship it. Cost: a day of lane time; gain: the first evidence that the IR output is
define-compatible. Do it at the end of S2-9 only if time remains; the real migration is slice 8.

## 3. Slices 3 to 8 (lighter grain; each starts from the previous slice's exit)

### Slice 3: own articles, FX, sounds, named resources

- **Scope:** defines may declare `articles` (the v5 article machinery) with per-define kind ranges; fighter-owned effect banks;
  named sound registration; the resolver for `{retail: ..., component: ...}` references that every later slice uses.
- **Entry condition:** slice 2 accepted; defines coexist; hash word exists; budgets logged.
- **Tasks:** S3-1 resolver and manifest (`{retail:"mario", clip:"..."}`, `{retail_sound:...}`, content/edition check, hard error on a
  missing reference, no donor fallback); S3-2 lift the article refusal for defines and replace profile-arithmetic article kinds
  with a per-definition allocation (`GENO_ART_KIND`, `GENO_ART_EXTRA_BASE` start at profile 32 [R `geno.h:361-370`]; the Mario
  fireball path at `ftmariospecialn.c:124` must not fire for a define); S3-3 model region sizing for N defines (1 MiB bump
  reserved only when a mod defines articles [R `docs/geno.md` 19.1]); S3-4 own sounds: WAV to the mixer's representation offline,
  named events `(tick, owner, ordinal)` for rollback suppression; S3-5 article state words into the arena, digest and snapshot
  (pool cursor, generation); S3-6 Striker gains a projectile and a sound; S3-7 tooling (`check` resolves every reference;
  `report` lists resources); S3-8 sweep (reflect, absorb, clank, despawn, stage switching with live articles, savestate
  across spawn and hit).
- **Acceptance:** Striker's neutral special becomes a charged projectile with its own sound; reflect/absorb/despawn read back;
  rollback across a spawn and a hit gives equal state; peer-visible refusal is slice 7. Suite +about 8.
- **Risk:** the 16 articles per profile and the 2 MiB arena [R]; peer determinism of audio events.

### Slice 4: own model, skeleton, clips, hurtboxes (the donor's model and animations go)

- **Scope:** the generic preset `base: "none"` (no Mario rows, no Mario callback tables beyond named common ones); an animation
  bank that is the package's; skeleton roles and sockets; hurtboxes and ECB; Blender/glTF compiled offline to HSD (design
  question 2, accepted in direction): extend `ports/ir/tools/fighterbuild` with a clean authored template generator [R design
  section 3; `ports/ir/tools/fighterbuild/Program.cs:61,88` per the design].
- **Entry condition:** slice 3 resolver in place; the digest and budgets cover all gameplay state; the owner has an original model
  and clip set to test with (the owner's or a Blender lane's; no third-party assets in the repo).
- **Tasks:** S4-1 generic preset and loader (removes `ftMario_DatAttrs`/baseline dependencies, `geno_define_data.inc:25-36`);
  S4-2 independent animation bank and subaction table (the 303-row limit goes; `geno_define_registry.inc:73-85` bound becomes the
  package's row count); S4-3 skeleton, bone roles, sockets, grab anchor; S4-4 hurtbox and ECB schema and checker; S4-5 importer
  (axes, bind pose, weights, deterministic ordering, loss report); S4-6 paired grab/victim clips and ledge/item anchors; S4-7 LAB
  preview of poses, sockets and collision; S4-8 a no-donor fixture ("Vanilla Original" working name) that plays every common state.
- **Acceptance:** the fixture fights through a full stock match on the vanilla disc with the log showing no donor clip bank load
  (`PlMrAJ.dat` absent from the loaded-file log for this kind) and no Mario model; owner QA of poses and collisions; memory bounds.
  Suite +about 10.
- **Risk:** the largest in the project: the skinned-model path and every place that indexes by CK or retail kind (CSS, results).

### Slice 5: fighter Lua

- **Scope:** the dedicated deterministic Lua domain (design section 4): stateless module functions, typed `ctx.state` in
  snapshotted memory, bounded commands, pinned math, no `gd`.
- **Entry condition:** slice 4 accepted; a list of the moves that slices 2-3 could not express (from `10-known-gaps.md`).
- **Tasks:** S5-1 sandbox and enforcement feasibility (frozen module tables, mutable-closure rejection; the design lists this as an
  acceptance blocker, spec line 210); S5-2 typed state block and snapshot/hash coverage; S5-3 command queue and phase order;
  S5-4 budgets with deterministic overflow fault; S5-5 `check` for Lua; S5-6 rewrite Striker's charge special as Lua and compare
  frame by frame to the declarative version; S5-7 LAB faults and budgets display.
- **Acceptance:** identical inputs give identical states and hashes between the declarative and the Lua version of the same move;
  resim never double-fires a command; overflow is a tick-exact fault. **Risk:** the closure/global enforcement.

### Slice 6: presentation and integration

- **Scope:** custom CSS icon, portrait, nameplate, stock icon, results pose and emblem, announcer and voice; costumes and team
  colours; Kirby copy policy (`none`, `retail` or `ability`); AI hints and the default arms of the `fp->kind` switches; item hold
  animations; records and optional trophies under stable keys; residual identity widening (wide resident indices, design
  section 5).
- **Entry:** slice 4 (art) accepted; slice 5 optional. **Tasks:** S6-1 selection entry independent of CK 8; S6-2 results/emblem;
  S6-3 costumes and teams; S6-4 voice, announcer, victory audio; S6-5 Kirby copy; S6-6 AI hints and recovery; S6-7 records;
  S6-8 resident-index census and widening plan; S6-9 sweep with 1P modes (intro, target test, credits).
- **Acceptance:** full versus and Classic with CSS, results and team costumes, CPU recovery, Kirby copy and loss, records without
  corrupting retail saves. **Risk:** every retail table indexed by character kind.

### Slice 7: online identity and rollback certification

- **Scope:** lift the three online refusals only after: package content hash (design section 4, SHA-256 identity) in the
  handshake and replays; the resident map agreed and snapshotted; the Lua and arena contracts in the hash; two-client loopback
  and an internet soak.
- **Entry:** slices 2-6 complete and every gameplay word hashed. **Tasks:** S7-1 manifest hash and handshake (protocol bump, the
  Turbo pattern [R `_research/envoy-netplay-scoping-2026-10-05.md` section 8]); S7-2 resident map in the match setup and replay
  header; S7-3 peer-mismatch refusal tests; S7-4 resimulation proof with a define under real rollback (not only
  `gd.rewind_test`, which proves snapshot restore only [R scoping section 7]); S7-5 retire the offline-only asserts; S7-6 soak:
  repeated 10-minute two-client runs, zero desyncs. **Acceptance:** a Striker-vs-retail online match plays; a mismatched build is
  refused at the handshake. **Risk:** unexplained SyncTest float differences noted in the handoff.

### Slice 8: customer migrations

- **Scope:** move existing ports onto the format, one fighter per pass, with a loss report each: Sora (`ultimate-trail`) first as the
  in-repo port; then Ultimate Kirby and Meta Knight. The order and timing of any private customer's own port are the owner's call
  and are not described here.
- **Entry:** slices 3-6 (Sora needs articles, own clips, UI); slice 5 if a move needs Lua. **Tasks per fighter:** convert the
  profile (`attach` to `define`), drop the m-ex slot dependency, compare old and new on identical inputs (attributes, states,
  clips, movement, hitboxes, article lifetimes, FX/SFX events, rollback hashes), repair or accept each difference. **Acceptance:**
  the folder boots on vanilla without m-ex or PowerPC; scripted comparison plus owner play. **Risk:** unmapped host behaviours.

## 4. Compatibility checks with what exists

| Area | Check in slice 2 | Where |
|---|---|---|
| Roguelike modifier layer | tags (D6), hit rules on the fixture's own hitboxes, statuses, crits (`gd.crit` with tags), armour, timed status, skill events, as in the spike's items 3, 7, 9 [R] | S2-4, S2-9 |
| `gd.cpu_assist` and CPU macros timed from attributes | macros read `gd.cpu_attrs` [R `gw_script_cpu_ctl.inc:305-322`]; S2-2 makes the landing lags the author's | S2-2, S2-9 |
| Stage switching | the Striker in the 200-seed switch loop | S2-9 |
| Six slots and the wide roster registry | six distinct kinds in one match, with aliases 127 downward [R `docs/geno.md` 22]; at most 94 definitions, fewer with m-ex installed; the wide registry (`gw_roster_catalog.h`: ids 128+, "native") is unrelated live-wise [R `_build/tmp/codex-roster-registry-report.md:6` per the design] | S2-1, S2-9 |
| Savestates and rewind | state library save/load mid-special; digest equality | S2-7, S2-9 |
| Vanilla disc, one folder | exporter refuses archives; package has text only; no disc paths in README, tests or logs | S2-9 |
| Performance | Hero cost = Mario's within noise (+0.26 ms) [R spike]; slice 2 gate: Striker within 0.5 ms of the Mario control, mean under 8.3 ms | S2-9 |
| Netplay readiness | every new state in game memory, a hash word (D8), no host time, no per-peer input in rules [R scoping section 6 rules 4, 7, 8]; Lua stays out until slice 5 | all tasks |
| Existing attach fighters | each edit is gated on "is a define" (D6, D8) or appends (S2-2); the full suite is the contract [R `docs/prompts/codex-geno-define-fix1.md`] | S2-9 |

## 5. Questions that genuinely need the owner

Everything else is decided in the table above.

1. **Names** (taste): the second fixture's display name ("Vanilla Striker" is a placeholder), the generic-preset fixture of slice 4
   ("Vanilla Original"), and whether the demos ship in the public catalogue. Recommendation: keep placeholders until slice 4.
2. **Original art** (his or a lane's): slice 4 needs an original model and clip set. Who makes the first one, and the budget in
   polygons and clips? Recommendation: a small neutral humanoid made in Blender by a modelling lane (modelling stays with Claude
   lanes), no third-party assets.
3. **Anything touching the private port**: when its engine requests are scheduled against slices 3-6 is his call. This plan does
   not read or describe it.
4. **Feel sign-off** on the Striker's moves: the owner decides whether the rushdown design reads as "not Mario"; slice 2's
   acceptance is mechanical plus his 10-minute play.

## 6. Evidence limits

Read: the design; the slice-1 packets and fix packet; `pc/geno/*` and `pc/platform/geno_registry.c`, `geno_define_registry.inc`,
`geno_define_tests.inc`; `docs/geno.md` sections 15-22; `ports/README.md`; the spike progress; the netplay scoping study; the
2026-10-05 handoff; retail sites by grep. Not read in full: `geno_game_articles.inc`, `geno_game_items.inc`, `docs/scripting.md`
beyond the handoff's summary of it, `docs/MEX_PORT_STATUS.md` beyond the Geno lines, `gw_roster_catalog.h` beyond its header.
Not run: everything (no build, no suite, no launch). Credit: GGPO (Tony Cannon, ggpo.net) is the rollback vocabulary of the
netplay study this plan follows; Brawl's PSA conventions are credited in `docs/geno.md` 15.6; Khronos glTF 2.0 and Blender are the
named inputs of slice 4.
