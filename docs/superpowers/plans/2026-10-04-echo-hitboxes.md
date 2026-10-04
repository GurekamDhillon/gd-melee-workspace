# Echo hitboxes implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. No commits or game builds: packet restriction wins.

**Goal:** Historical fighter hitboxes replay through native collision with matching afterimages and declarative Envoy upgrades.
**Architecture:** Snapshot-covered history and echo capsule state; native Lua API/journal adapter; pure Envoy echo family and shared display helper.
**Tech Stack:** PPC game C, native C/C++ and Lua5.4.
**Spec:** docs/superpowers/specs/2026-10-04-echo-hitboxes-design.md

## Global constraints
No commit/reset/stash/revert/checkout/build/game launch. No roster/fighter-definition edits. New code in script_echo*/gw_script_echo*; only owned Envoy and hit-rule code modified. Root alone applies minimal shared-file hooks/registration/docs/catalogue last, re-reading immediately before mutation. Preserve existing API compatibility and gameplay gates; never hand native pointers into game memory.

## Review focus
History must record after world capsules resolve but before hit memory changes; age60 wraps correctly. Sub-fighters and respawn identity must not alias. Rule cleanup and script ownership must survive snapshot restore and unload. Echo target memory must distinguish live move and delay copies, but prevent every-frame repeat. Native replay mutations must journal deterministically; presentation must never affect collision.

## Tasks
- [x] 1 Native game history/carrier. Create script_echo.h/script_echo.c and focused tests; own ftcoll.c/hit-rule hooks only as needed. Establish exact scalar boundary interface. Write failing tests for ring wrap/ages, recorded-position timing, capsule identity, owner/team immunity, shield/clank/once/cleanup, snapshot byte equality. Implement and run production standalone tests + PPC syntax. Provide root exact deferred hook snippets and costs; no shared script_game.c writes.
- [ ] 2 Native API/journal and aligned presentation. Depends on task1 scalar signatures; create gw_script_echo* implementations/tests, reuse existing gs_sim conventions. Inspect/render afterimage API and add bounded copy-addressing/armed tint/flash support where packet authorizes; do not overwrite ongoing afterimage lane. Establish joint description helper and ownership/gates. Write parser/journal/determinism tests before implementing. Provide root registration/include/reset snippets, do not write gw_script.c.
- [x] 3 Envoy echo family/records/LAB. Create echo module(s) and tests; modify owned schema/budget/engine/pool/display/adapters. Consume gd.echo_* and aligned helper stable description. Add tiered first/second/third aerial echo suffix, live-damage-cost unique and keystone; owner's neutral-air copies1/2 description; shared vocabulary/strength budget/CPU. Test tier/extrema/once metadata, adapter journal/checkpoint/cleanup with stub APIs. No bundle generation until root final.
- [x] 4 Root integration/review/docs/demo. Apply shared hooks last from actual current sources, catalogue demo in new echo files, native object list entries if necessary. Review each task's source/spec and final whole-source separately; fix findings with scoped regressions. Regenerate Envoy last; full Lua/tools tests, affected PPC/native syntax/standalone tests and exact snapshot fixture. Report source limitations and live acceptance pending.

## Ledger
Ruling: distinct capsule list in normal traversal preferred over scripted direct damage or Geno articles; preserves team/shield collision without roster dependencies, costs added collision hooks and bounded snapshot storage. Native implementer may refine based on actual traversal evidence and must report unsupported behavior.
Ruling: twelve entity history rings with age0..60 support sub-fighters and all afterimage delays; costs bounded game-memory storage (measured after concrete layout).
Ruling: echo no owner hitlag is intended; echo is separate stale/credit hit with own target memory; implementation must prove ownership does not accidentally feed rebound/hitlag back into live owner.
Ruling: three disjoint implementers coordinate fixed interfaces; root applies all shared mutations last. Exact dirty-source baselines replace commit review ranges under packet restrictions.

Final source review PASS after one correction wave: PC damage/tip logs548 rows (42,240 added PPC bytes), stale descriptor sweep with80 create/remove regression, and current generated-entry capability fixture/old-engine refusal. Final368 Lua/42 suites and12 Python tests PASS; native fixtures/PPC/native syntax PASS. Task1 marks source/standalone proof, not live engine/LAB proof. Task2 remains partial: API/journal/copy inspection/style seam implemented and tested, but existing renderer is owned elsewhere; concrete FIFO integration patch and new render helper supplied without applying it. Actual shield/clank, on-screen tint/flash, owner-hitlag and real LAB rewind acceptance remain pending. Report: _build/tmp/codex-echo-hitboxes-report.md. Bundle regenerated after assembled source review and correction source freeze; narrow correction acceptance then confirmed without further source changes.
