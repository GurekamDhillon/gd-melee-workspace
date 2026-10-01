# Full 100/100 assignment for the new model

Date: 2026-09-30. The user has authorized assigning the entire remaining offline TBD roguelite completion and polish effort to the new high-capability model, with ample usage. This is an execution assignment, not another request for a proposal.

## Copy this kickoff to the new model

> Read `docs/NEW-MODEL-ROGUELITE-HANDOFF.md`, this document, and `docs/ROGUELITE-COMPLETION-PLAN.md`. Take responsibility for the entire remaining 100/100 program. Establish an isolated integration workspace, preserve the current local changes and frozen submissions, then implement, integrate, test and document the remaining milestones. Do not stop at a first playable slice, one generated run, a helper module or passing stub tests. Keep a playable development build between milestones. Delegate bounded tasks where useful, but review and land them yourself. Carry independent work forward while human/hardware checks are pending. Do not fabricate those checks, publish a release, restart the cancelled turbo benchmark, or silently reduce the scope. Report concrete completion evidence and the remaining review queue.

The full completion plan is the detailed specification. The latest handoff is the current-state authority. This assignment defines how to execute the **rest** of that specification, including integration, content and polish.

## Ownership and startup

Act as the implementation coordinator. Own the complete outcome, including dependencies between native code, Lua, assets, launcher, saves and tests. Do not leave disconnected helper implementations as the final deliverable.

1. Recheck both root repos, remote heads, running native profiles and worker status. Read the handoff's dirty-worktree warning before editing.
2. Create an isolated integration branch/worktree in each repo. Record the source commits and hashes of any reviewed local files/assets seeded into it. Worker lanes are separate from the integration lane.
3. Preserve all frozen candidate worktrees. Independently review their output; import exact owned patches, not whole directory snapshots.
4. Establish a reproducible baseline for the integration lane. The latest root had 244 pure/stub tests passing and a tested native binary with 214/214 native checks, but much native/art work is still uncommitted. Inventory and reconcile that dependency before claiming a clean clone can build the tested mode.
5. Create `docs/ROGUELITE-100-100-LEDGER.md`: requirement, implementation location, owner, status, evidence, remaining defect/review. Use statuses such as missing, implemented, integration-tested, native-tested, human-reviewed and accepted. Track feature and polish acceptance separately.
6. Keep one writer per shared file/schema. Especially protect `main.lua`, `core.lua`, `prepare.py`, native script APIs and generated bridge code. Use exact-path commits and reviewable patches.

Do not request a model change or a fresh budget merely because the task is large. Use the available model for difficult integration/review. Cheap workers may handle bounded content, validators, migrations and tests; they are not substitutes for coordinator ownership.

## What is already accepted

Preserve the current save protection, reviewed campaign recovery, live legacy/v2 command tree, compact HUD and native ownership/seam fixes. Read their source and evidence before modifying them.

Latest movement result: Falco's stairs/balcony/ramp joins felt good to the user. The shared ascent spawn/left arrival was moved from -42 to -58.5, before the slope. Corrected native Jigglypuff/Kirby ascent and return all reached their targets without falling. Jigglypuff return still has an automated pop candidate, Bowser return is unresolved, and merge/drop checks remain incomplete. These are scoped results, not full recipe certification.

GitHub has the committed development branches; uncommitted native/assets/docs remain local. Never equate pushed Lua commits with a complete reproducible package.

## Milestone 1 — A trustworthy source/build baseline

This is necessary alongside continued gameplay work, not a weeks-long cleanup detour.

- Inventory the local native changes that the tested executable depends on: stage isolation, floor seams, ownership cleanup, model parts/FX, HUD, pad masking/debug attack cursor, technical AI and related bridge APIs.
- Separate validated implementation from generated bridge changes and unrelated experiments. Preserve backups; do not broadly stage a huge bridge diff just to silence Git status.
- Land coherent native patches with their focused checks and actual build/ABI validation. Confirm new includes/test files are tracked and a clean build discovers them.
- Include the authored asset pipeline inputs, allowed original assets and metadata needed to reproduce the kit/UI/effects. Never commit the disc or extracted retail assets. Do not indiscriminately add `_build/`.
- Establish the exact source-to-binary relationship. A copied local binary is useful for testing, but it is not clean-source build evidence.
- Update the ownership/evidence ledger and development branches after review. No release/tag.

**Acceptance:** the integrated source and allowed assets reproduce the executable/mod being tested; the native and pure baselines are independently green or have explicit, investigated failures. Missing generated assets are dependencies to fix, not tests to skip indefinitely.

## Milestone 2 — Physical catalogue and actual generated runs

- Resolve watched Jigglypuff return and Bowser return; verify both merge arrivals and drop-through/one-way behavior. Establish stable fixture placement without confusing native intro/respawn with geometry failure.
- Check spawn hull clearance against stairs, walls, floors and openings. The -58.5 fix must survive all shared ascent layouts, mirrors/entries and supported fighters. Keep actual doorway socket locations distinct from arrival positions.
- Cover the full offered roster and supported movement penalties, including large/small bodies, floaters, fast-fallers, swords, partners and transforms. Preserve native Melee movement; no teleport/fly certification.
- Finish the required room diversity and socket contracts. Version layout/collision changes and preserve supported saved manifests.
- Validate branching/merging/loops/shortcuts, directionality, keys, one-shot pickups, opened doors, mandatory objectives and safe return paths. Inspect structural diversity and fallback rate; generated palette changes are insufficient.
- Admit only physically accepted recipes. Complete the live v2 generation/route/map seam without using admission bypasses in normal play.
- Exercise source/destination lifetime, incremental preload, isolation, placement, save/commit/reveal, failure recovery, discovery and held-button latching. Revisit without duplicate rewards or enemy farming.
- Suspend/park unused fighter slots correctly. A standing Fox in every exploration room is not final behavior.

**Acceptance:** complete a generated route from product-menu entry, take and revisit a branch, use a merge/shortcut, save/relaunch/resume, lose lives and finish successfully. Then broaden the evidence to the catalogue, roster and varied seeds. The first complete run is a milestone, not the finished game.

## Milestone 3 — Native gene action integrity and full build mechanics

Start with the concrete adapter P1 in the latest handoff: contribution capacity must be reserved before provider mutation; repeated refunded actions cannot accumulate unbounded native tokens. Preserve ownership of issued tokens, original-run cleanup, strict acceptance and pre-spend identity checks.

- Correct native hit/strike acceptance for absorbed armor contact without breaking ordinary armor depletion/spill. Refusal must not conceal an irreversible mutation. Audit eligibility, shields, invulnerability and ownership in actual native code.
- Land and wire the reviewed adapter with honest per-host/per-direction capabilities. Unknown occlusion/eligibility remains unavailable; do not advertise unsupported behavior.
- Establish stable attack-instance/event provenance: direct hits, multihits, lingering hits, trades, projectiles, reflection, shield interactions, reactions and disappearing targets. Scripted damage is not fabricated natural-hit charge evidence.
- Implement startup, bounded effect/collision, recovery, interruption and targeted refunds shared by player and eligible enemy actions. Keep spend-state and mark revision ownership.
- Prove complete native Cinder/Rime/Thermal Shock loops under normal controller combat before expanding families.
- Expand the planned mechanically distinct families, placements, reward mutations and supported reactions. Give each a behavior specification, real counterplay, limits, visual/audio states and meaningful tradeoffs.
- Test reentrant callbacks, host/run replacement, room exit, death, scene reset, save failure and cleanup refusal. No stale marks, wrong-target effects or decorative substitutes for mechanics.

**Acceptance:** every offered gene/action/reaction has real native behavior, truthful command descriptions and demonstrated lifecycle/resource correctness. Catalogue counts alone do not pass this milestone.

## Milestone 4 — Encounters, bosses and capable opponents

- Finish data-driven encounter composition, stable actor IDs, gene assignment, reinforcement timing, completion policies and checkpoint state.
- Broaden native/custom non-fighters beyond demonstrations. Inspect original Adventure dependencies before adopting actors; give them movement, attacks, tells, vulnerability and fall/escape rules.
- Implement the planned distinct bosses/phases, recovery windows and positioning demands. Increased HP or repeated fighter stocks alone do not constitute distinct bosses.
- Revisit the 20XX/UnclePunch/training-hack AI audit. Use primary source/code evidence and current availability rather than assuming 20XX is best or directly portable.
- Compare candidate behavior to vanilla on the same seeds/layouts. Measure completed tech/L-cancel/recovery, spacing, punishment, approach/retreat and gene use, with difficulty/reaction-delay controls.
- Use legal observation and controller/action boundaries. No omniscient inputs, undeclared resources, teleport recovery or skipped lag.
- Preserve partial encounter/boss progress and rewards correctly across supported saves. Distinguish defeated, missing, unloaded and escaped actors.

**Acceptance:** the encounter/boss target is implemented, opponents show measured improvements on custom geometry, and human natural combat confirms readable/fair counterplay.

## Milestone 5 — Inventory, equipment and the permanent economy

- Finish actual consumable ownership/actions, stacking/capacity/cooldowns and truthful pre-use refusal. Restore is the beginning, not a full inventory.
- Implement equipment slots and reversible stat/behavior contributions. Distinguish equipped gameplay items from a character's built-in weapon/accessory and transient articles.
- Complete collection inspection, comparisons, ancestry, sorting/filtering, breeding, inheritance locks/previews, fusion, replacement/discard and run history.
- Persist reward offers before choice; reload cannot reroll them. Handle full capacity and refused saves without silent loss, repeated export or dangling equipped parents.
- Offer an explicit victory export choice. Clearly separate inherited/base properties from run-only upgrades and temporary modifiers.
- Simulate acquisition/costs/unlocks and established-profile power, then tune through actual play. Keep choices meaningful without infinite permanent stat inflation.

**Acceptance:** fresh and established profiles can acquire, equip, consume, breed, fuse, export, fail and resume across full-capacity/error cases. Every advertised item has actual consequences.

## Milestone 6 — Complete product UI and readable feedback

- Preserve the recursive Left/Right/Down tree and Up release latch. Build leaves from actual equipped capabilities/inventory, with cost/readiness and useful disabled reasons.
- Finish route-map and prepared-branch interactions. Replace dead placeholders with working features or truthful explanations; automatic reactions are not fake cast buttons.
- Finish every collection/setup/roster/build/inventory/breeding/fusion/reward/rest/map/settings/death/victory/export/error screen using the menu kit.
- Make controller, mouse and keyboard navigation consistent. Test held buttons, chords, hotplug, reconnect, pause, respawn and transformations.
- Finish teach-and-try onboarding, skip/revisit and contextual genetics/fusion explanation. Test a new player without console assistance.
- Keep the combat rail/toasts compact and informative. Do not restore a large permanent inventory panel. Test real combat readability at 4:3/widescreen and available UI scales.
- Centralize user-facing text/units and complete only languages actually offered. Keep raw handles and diagnostics outside product flows.

**Acceptance:** all functional screens/actions are usable, truthful and readable, with native HUD ownership restored on every exit/failure path. Static layout bounds are necessary but not sufficient.

## Milestone 7 — Region genetics, effects and the full spectacle

This milestone includes the original effects-lab commitments, not only Cinder/Rime wrappers. Read `EFFECTS-LAB-PLAN.md`, the expanded visual vocabulary in the completion plan, and the art queue/delivery documents.

- Separate anatomy/equipment semantics, draw/material selectors and skeleton attachments. Bind every offered fighter/costume using reviewed fingerprints; do not copy raw draw ordinals blindly.
- Cover faces/cutouts, action-dependent geometry, built-in weapons/shields/scabbards, temporary articles, partners and transformations. No invisible fighters or leaked material overrides.
- Map family/placement/stats to quiet dormant/charging/ready states and earned activation/reaction/recovery events. Discrete charges and actual duration/range must match what the player sees.
- Integrate persistent region accents, attachment halos, actual motion/weapon tracers and trails. Implement afterimages and advanced material patterns only with genuine native support; cheap silhouettes must be named accurately.
- Complete founder recipes, ten unordered pair blends, trait controls, deterministic Breed/Mutate/Lock/Save/Compare and saved recipe/version behavior described by the existing plan. Interpolating arbitrary emitter fields is not a convincing blend.
- Deliver the full labelled catalogue sweep across phases, parts and accessories. The prior purple/cyan demo is not the sweep.
- Enforce lifecycle and per-region dominance, history/attachment/emitter/overdraw budgets, quality levels and reduced flash/motion settings. Keep enemy tells legible with opposing builds active.
- Coordinate final asset authorship with Astra under the user's standing preference. Continue renderer/plumbing/content work independently while specific art review is pending.

**Acceptance:** every advertised visual technique and binding works during real motion/combat and cleans up correctly. Provide actual native PNGs for visual review and recorded motion evidence where timing matters; no interactive external preview viewer or simulated gameplay image.

## Milestone 8 — World composition, audio and production feel

- Finish coherent themes, background depth, room lighting, doorway prompts, hazards and gameplay camera/bounds. Hide unused actors and host-stage remnants reliably.
- Mask incremental loading/room transitions until safe activation. No FD flash, half-built room or warmup hitch exposed as normal presentation.
- Implement the complete audio event map with usable original/provenanced assets, variation, priority and concurrency limits. Combat tells must survive busy music/effects.
- Finish separate audio controls, focus/device change behavior and first-use loading. Counters prove playback activity, not a good mix; prepare human listening review.
- Finish death/victory/extraction summaries, build consequences, export and next action. Product UI must explain recovery without exposing engine internals.
- Tune encounter pacing, detour value, difficulty, run length and economy. Record iterations and human observations rather than claiming fun from simulation alone.

**Acceptance:** every normal state has finished presentation, informative sound, smooth transitions and reviewed gameplay-distance readability.

## Milestone 9 — Both-platform acceptance, packaging and stability

- Build the final source on Windows and Linux. Verify bridge/ABI and exact artifacts; preserve existing Qt launcher rather than replacing it again.
- Test installed/relocated and upgraded profiles, Unicode/spaced paths, writable user data, launch/exit, complete runs and save/resume.
- Verify native Wayland and X11/XWayland with backend evidence, mouse/focus/fullscreen/resize and controllers. A failed unavailable backend is not a native Wayland pass.
- Test SDL and GameCube adapter input/hotplug/rumble/multiple ports when hardware is available. Do not let virtual pad helpers claim the user's active port.
- Preserve Windows-driven Linux checks through CI/trusted disc-backed runner workflows. No disc data in public repos or artifacts; skipped runners remain pending.
- Profile worst supported actors/effects/UI at normal speed. Agree/reference hardware settings and frame-time targets; do not resurrect uncapped benchmarking.
- Run the planned normal-speed soak and repeated-transition lifecycle checks. Track resources, memory, input ownership, loading and audio stability.
- Check touched vanilla/offline custom content and restoration of the base game's HUD, camera, input and settings.

**Acceptance:** reproducible local packages and complete gameplay evidence on both platforms, required inputs/displays, stable resources and honest CI. No public release is part of this assignment.

## Milestone 10 — Full completion and final polish acceptance

Use the completion plan's full playtest matrix: varied topology/themes/builds/bosses, success/failure, both operating systems, all offered fighters, save points and an established collection. Obtain first-session and skilled-Melee review as distinct evidence.

Work through all feature and polish checklists. Resolve P0/P1/P2 issues; minor accepted imperfections require explicit human review. Ensure advertised content is implemented, not still a diagnostic command or disabled placeholder. Do not label a missing requirement as optional after implementation becomes difficult.

Prepare a short, ordered user review route with the exact build, controller actions and judgments needed. Keep unavailable hardware/human evidence pending and continue independent fixes. Never self-certify subjective feel or silently assume missing approval.

**Acceptance:** every required feature and quality gate has evidence, no material defect remains, and human/platform checks are actually complete. Only then call the mode 100/100. Until then report specific gate status rather than invented percentages.

## Working cadence and completion behavior

- Keep the playable integration build stable. Land bounded patches with relevant tests before dependent content expansion.
- Maintain one acceptance ledger rather than scattered conflicting completion claims. Record test provenance: real native, stub, property test, fixture, scripted controller or human controller.
- Carry save/load/failure/cleanup checks across every new system, not just at the beginning and end.
- Make routine engineering choices autonomously within the agreed scope. Ask only for missing design choices that materially affect the result or required human/hardware judgment.
- When one lane blocks, preserve its evidence and progress on independent work. Do not keep trying fixture placement indefinitely.
- Commit and push reviewed work on development branches. Keep unvalidated candidates isolated, and report anything still local. Never publish a release/tag.
- A green checkpoint is where to land a patch, not where to stop the whole assignment. Continue to the next milestone while authorized work remains.

## Final deliverables

1. Integrated source and reproducible original-asset pipeline, with reviewed development commits pushed in both repositories.
2. Local Windows/Linux review packages and complete-mode launch/exit behavior through Qt.
3. Completed finite content catalogue and correctly integrated mechanics/presentation.
4. Evidence-linked feature/polish ledger, fault/regression/soak reports and human/hardware results.
5. Actual in-game PNG showcase and motion evidence for the full effects/bindings catalogue.
6. Final known-issues list and truthful acceptance report. Pending required evidence means the full assignment is not complete.
