# Envoy balance and opponents implementation plan

Goal: preserve visible modifier chains while limiting raw killing power and giving CPU opponents comparable builds.
Spec: `docs/prompts/codex-envoy-balance-and-opponents.md`, design sections 7 and 11 step 4.
Architecture: native percent-only damage path leaves launch inputs unchanged; one Lua budget module owns additive family composition, caps, strength and pool validation; seeded opponents use the same bag derivation/engine/display/checkpoint.

## Global constraints

Both checkouts are deliberately dirty; preserve all work. No commits, build.sh or game launch. No Classic integration. Source stays compilable; regenerate the bundle last. The packet explicitly overrides skill design/plan approval and commit/worktree handoffs. Execute reviewed tasks in the existing checkout.

## Review focus

- Simultaneous contacts against differently statused victims must not mutate shared capsules or contaminate launch inputs.
- Charged/staled attacks, projectiles and throws must separate percent and launch consistently; shield/clank priority changes must be explicit.
- Conditional native bonuses plus steady/status/implicit bonuses must share a family cap, rather than cap independently then multiply.
- Opponent edits while paused/replaying, invalid ports and controller ownership must refuse atomically and restore exactly.
- Clearing/restarting must retire CPU builds, nameplates, status effects and native rules, preserving unrelated P1 inventory.

## Tasks

- [x] Task 1: Native percent-only damage. Inspect ftcoll and throw paths, add explicit compatible hit-rule percent fields and snapshotted per-victim accounting where necessary. Red test unchanged launch with changed displayed percent, shield/clank/stale preservation, multi-victim contacts and journal/state roundtrip. Run standalone C tests and PPC syntax checks. Report exact native semantics and sourced formula/weight evidence in `_build/tmp/em4-native.md`. Review before task 2.
- [x] Task 2: Budget and pool. Create `scripts/mod_budget.lua`; modify schema, engine, pool, drive_loot and drive_bag. Declare each record/implicit family contributions and allowed costs; compose additive bonuses with shared caps, calculate worst-case build budgets and validate pool safety. Retune all 30 records and snapshot old/new table. Test family addition/caps, over-budget pool refusal, all records/tiers, chain preservation and representative four-slot Rare + unique launch target. Report `_build/tmp/em4-budget.md`. Review before task 3.
- [x] Task 3: Opponents and presentation. Create seeded pure `foe_roll.lua` and LAB `foe_lab.lua`; modify mod_lab, drive_menu and bundle module registration. Support foe roll strength/seed/CPU port, clear and stand/fight toggle, default player strength, nameplate and same shader treatments. Serialize foe seeds/builds/pending commands and preserve stock builds; clear on scene/unload. Test 1,000-roll mean tolerance, CPU -> player rules/chains, commands/cleanup/full checkpoint. Report `_build/tmp/em4-foes.md`. Review before task 4.
- [x] Task 4: Integration. Refresh docs/PLAYTEST and complete report `_build/tmp/codex-envoy-balance-and-opponents-report.md` with cause numbers, native semantics, caps, every old/new record and owner script. Independently review whole change. Finalize all editable source, regenerate bundle last, run complete Lua/Python checks and native syntax/standalone tests. Record live acceptance unrun and rebuild required.

## Contracts and rulings

Native API field names and exact percent timing are settled after collision-path inspection, before Lua integration; legacy scripting damage fields retain their contract. Family composition must join steady and conditional effects at contact, not introduce a second independent multiplier. Budget display and opponent strength consume the same data.

Ruling: keep explicit legacy damage scaling for existing scripting clients and use an explicit new percent-only mode for Envoy. Cost if wrong: maintaining two native behaviors increases API complexity; avoids silently changing unrelated scripts.
Ruling: use the existing dirty integration checkout rather than isolating/resetting either tree, as the packet requires. Cost if wrong: final diff includes earlier work, so review must use a recorded source baseline.

Ledger: task 1 dispatched to native implementer for collision inspection and tests. Implementation/review agents do not spawn subagents. Skill subagent-driven-development authorizes delegation; tasks run sequentially to avoid shared-interface conflicts. No commit-based review package is possible under the packet; changed-source packages and reports replace it.

Ledger: task1nativeimplementation complete with stable percent_damage/launch API; remaining native work is syntax/formula verification. Task2 dispatched on disjointLua source, after interface settlement; native review read-only underway. No simultaneous shared-file implementation.
Ruling: conservative launch budget test uses discrete no-DI FDcentre travel proxy, original retail percent flooring and real fighter weights, not a gameplay kill claim. Heavy/Pyre tier3 add7.5%/12%; Curse tier3 3.75% gives factor1.2398125. Cost if wrong: owner gameplay timing/DI may require further tuning; live game is prohibited here.
Ruling: family sums saturate at final family cap, consistent with bonuses ADD then one cap; validator rejects unsafe/undeclared per-record contributions and audits conservatively reachable capped extrema. Cost if wrong: owner may prefer rejecting overcap equipment rather than displaying saturation.

Task1 complete: read-only native review ACCEPT, standaloneproductioncore/state and formula fixtures +native/PPCsyntax passed. NoImportant/Critical findings. Quanttestisformulaonly.
Task2pureimplementation complete; family API stable; read-onlybudgetreview underway. Task3dispatched on adapter/newfoe modules; root registersmod_budget beforeengine andfoe modulesafterdrive factories.
Ruling: actualfour-slot witness uses validfixed depth10 rolled-record representations, not claims that labels401..404 reproducegenerator seeds. Cost if wrong: the owner cannot summon that exacttier3 witness via depth1 drive commands; report/playtest distinguishesnumericfixturefromliveplayrecipe.

Task2 complete: spec/qualityreview PASS afterfixround1 unsupportedlaunch_dealt fightervalue removedfromschema withredgreenrepro. Actualfourdrivewitnessvalidated, noImportant/Criticalremain. Aggregateprovenanceactorparameter added withnewregression; task3passesactor.
Ruling: defaultfoe targeting includes exactvalidatedplayerbuild as fallback candidate, even LABdebugbuilds; seededrandom candidates win when closer toseededtarget, impossibleexplicitstrengthsrefuse ratherthanclip. Cost if wrong: somehigh/unusualbuilds mirrorplayerandreduceopponentvariety; defaultbudgetcomparisonremainsusable.

Ruling: CPU foe and modifier queues mutually exclude conflicting pending edits. Cost: resume and commit one command type before issuing the other.
Ruling: timed foe nameplates replace the debug HUD. Cost: debug trace is hidden for four seconds while the opponent build is shown.
Ledger: final review original three Important findings and full-queue clear addressed. Narrow remaining malformed checkpoint aggregate bounds are being validated before publication; no early family clamping.

Ledger: narrow aggregate bounds correction accepted by final reviewer; all four Important findings and Minor cleared. Final bundle regenerated after source corrections. Fresh final verification: 323 Lua tests/37 suites;35 parsed modules <=400 lines;12 Python tests; native production/state/formula fixtures;7 PPC TUs+native platform syntax all pass. Broader catalogue has unrelated demo_fighter_air_jumps scenario coverage failure. No game build/launch/commits. Task4 complete; live acceptance explicitly remains integrator/owner work.
