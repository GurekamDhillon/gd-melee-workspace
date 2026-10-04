# Envoy depth power and pacing follow-up

Spec: docs/prompts/codex-envoy-balance-fix1.md (binding); EM4 structure retained, balance target superseded.

## Constraints and design
Both trees deliberately dirty; preserve all files. No commits, build.sh, game launch, reset/stash/revert. Source test/syntax compiles allowed. Bundle regenerated last. Packet inherits EM4 no design approval; existing integration checkouts retained. Skill-authorized task implementers and read-only reviewers use exact source baseline, not HEAD diffs.

Architectural change: one pure progression module owns validated depth/loop, effective depth, tier growth, 4/5/6 slot progression, multiple keystone allowance, difficulty/boss factors and stock-exchange model. Growth curve continues with depth/NG+ until numerical/game safety limits. Ratio contributions within each family stay additive; cross-family percent/launch/toughness/status interactions are intentional. Existing pool identities/chains remain. Native explicit percent-only fields gain safety bounds (percent .05..64, launch .05..4), final damage display 0..999, speed/jump safety bounds, finite values, event depth8/budget64 retained. Native rule capacity32 protects bounded runtime while allowing all30 pool IDs with aggregate slots. Legacy native damage fields retain .1..4.

Opponents consume a scalar strength, depth/loop and role only, never reference player mods. Seeded weighted independent same-pool search uses higher tiers/slots, multiple uniques/keystones and defensive/resistance/cleansing weighting at high strength. Validate exact rolled build strength and tracking band; fail visibly if outside reachable safety range. Threat preferably chains/statuses and toughness, modest final launch. Numeric hit/exchange table explicitly a documented formula/model, not live KO measurement. LAB depth command snapshotted and offline/replay gated; physical drops and bag capacity/UI share progression context.

## Review focus
- Deep duplicate uniques and multiple keystones must contribute rather than silently highest-tier dedupe.
- Six slot/menu/looks/drop rolls and checkpoint roots use the same depth context, with atomic refusal on malformed restores.
- Extreme finite/nan/infinite/depth inputs cannot overflow ratios, native rules, percent or chain budget.
- Default opponents see only strength and context, no build identity or mirror fallback; role factors scale target.
- Table and play recipe use real validated pool/build/engine paths, not an independent ideal curve.

## Tasks
- [x] 1 Core progression: progression module, schema tier resolution, budget/engine, drive loot/bag and pure foe roll. Write failing tests for tier/slot/keystone growth, monotonic curve, no mirror default, tracking band/defensive weights and extremes; run relevant pure suites. Report exact interfaces and actual table generation inputs. Own pure Lua modules/tests only.
- [x] 2 Native safety: widen percent-only bounds and family safety limits and rule capacity32, all dependent metadata/journal/helper tests. Red/green native C production tests plus native/PPC syntax. Preserve legacy multiplier bounds, separation timing and snapshotted state. Own native files/C tests only. Task1 and2 share documented fixed native contract; disjoint writes.
- [x] 3 LAB integration: depth n [loop], checkpoint context, drive roll/drop/slots/UI/multiplekeystones, foe difficulty/roles/nameplates. Depends on stable task1 interfaces. Red/green adapter/fullcombined generated-entry tests; preserve existing atomicity/cleanup. Own adapters/menu/drops/testfiles only; register new module root-owned.
- [x] 4 Integration: independent whole-source review, fix scoped findings, report 52 rows depth0..12 loops0..3 from actual seeded roll/build paths with strength ranges/opponents/exchanges, early/late deterministic play recipes, update PLAYTEST/README/API. Regenerate bundle last then fullLua/Python/native checks. Explicit rebuild and live acceptance pending.

## Ledger / preflight
Ruling: replace gameplay balance ceilings with numerical safety boundaries, keep depth/loop validated integers; cost: extremely large progression eventually saturates machine/game-safe outputs rather than literal mathematical infinity.
Ruling: widen native32 capacity rather than merging unrelated predicates; cost: native snapshot/journal layout changes and mandatory rebuild.
Ruling: player-independent scalar-targeted weighted foe rolls replace mirror fallback; cost: bounded search may visibly refuse unreachable requests rather than copy a player.
Ruling: table is an actual-build deterministic percent/launch exchange proxy, not actual KO timing; cost: DI, move choice and healing rhythms require owner tuning.

| Pair/task | Contract check | Result |
|---|---|---|
|1/2|Lua emits signed raw +/-1e9; native final percent/launch caps once, 32 capacity|fixed shared contract|
|1/3|progression, slots/keys, roll context and strength used by LAB|stable interface implemented; mixed-copy tiers retained|
|1/4|table actual seeded pool builds vs reported curve|generate after pure interfaces settle|
|2/3|capability/version tells oldEXE to rebuild|task2 specifies field to task3|
|3/4|checkpoint/draw integration before bundle|root bundle last|
|1|growth vs safety invariants tests|consistent|
|2|legacy unaffected vs new fields widened|consistent|
|3|depth changes vs existing equipment|must preserve valid equipment on context change|
|4|no launch vs hits table|model labelled not gameplay evidence|

Stable contract: mod_progression before schema; context={depth,loop}; effective=depth+13*loop; tier=1+floor(effective/5); slots4/5/6 and keys1/2/3 at effective5/10; normal difficulty1+.003*effective, boss x1.15/finalboss x1.3. Core owns testlib loader. Native owns gw_script.c event-metadata96 expansion (historical creation plus current attacker/defender).
Ruling: chosen keystones retune to the current context tier as system choices, while physical drive tiers remain fixed in their rolled records. Cost: changing LAB depth changes chosen key potency immediately; returning to early depth can refuse excess slots/keys atomically.

Ledger: task2nativeimplementation done, five fresh nativefixture/syntax checks pass; read-only task2review running. Core stable interfaces accepted; task3adapter inprogress. Pool grows from30to32 with shared Armoured/Cleansing records. Target Curse is explicitly offensive rather than wearer vulnerability; utilitystrength uses bounded actual outputs.
Task2 fix round1: retain historical capsule + current attacker + defender rule provenance. Ruling event metadata96=3*32 (not64), bounded; cost additional event-array bytes, avoids dropping incoming rule ancestry after replacement. Pacing table exposed one-hit/lopsided cases; core is refining shared defensive construction rather than declaring target accepted.

Task2 complete: spec+quality PASS after scoped96-metadata fix; no remainingImportant. RetainnewactualnativeAPI+eventcontext fixtures; latergame rebuild mandatory. Nativeeventarrays grow147456 bytesvsinitial24 baseline; 32-rule simjournalcommit50716 bytes bounded128MiB.
Task1 fix round1: preserve per-copy unique tiers; no early ratio/aggregate saturation; stock model original-element predicates. Ruling: new percent/launch fields carry signed finite additive coefficients (1+rawdelta) within ±1e9; final physical output caps once (outpercent .05..64, takenpercent .15..64, launch .05..4), legacy inputs .1..4. Cost: wider explicit API semantics and native rebuild; avoids nonlinear stacking mistakes. Task3 fix round1 validates actual queued foe?debug?bag restore before publication. Existing CPU rolls retain own context/tiers until reroll; player selected keys follow dial.

Final source freeze: core6 review regressions and latest52x4 table ratios .8045..1.1944; LAB progression14/mod37/drive15 plus freshly assembled scratch integration17 pass; independent final whole-source review running. Native six fresh standalone/syntax checks pass. Python12 preliminary had only expected stale generated bundle failure; rerun after final regeneration. No EXE build/launch/commit.

Final acceptance: independent whole-source spec/quality PASS with explicit acceptance of three core, joint LAB checkpoint and mixed-tier adapter corrections; no remainingImportant. Bundle regeneratedLAST aftersourcefreeze;350Lua/40suites,36moduleparse+size,12Python, bundlecheck, sixnativefixture/syntaxcommandsPASS. Dirty integration trees retained, no commits/build/launch. Source taskcomplete; live rebuild/owneracceptancepending perpacket. Report _build/tmp/codex-envoy-balance-fix1-report.md.
