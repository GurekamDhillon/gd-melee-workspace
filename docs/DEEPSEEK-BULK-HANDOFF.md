# DeepSeek bulk implementation handoff — 2026-09-30

Read this first. It supersedes stale status/assignment wording in
`DEEPSEEK-NEXT-PASS.md`; keep that file's acceptance requirements and the full
`ROGUELITE-COMPLETION-PLAN.md`. The user prefers DeepSeek for bulk implementation
to control cost. Sol reviews/integrates and handles difficult defects; Astra
owns new art. Do not recreate completed foundation work.

Coordinator update: OpenCode is installed and its saved DeepSeek credential
passed an actual `AUTH_OK` request using `deepseek/deepseek-flash`. Root can
launch bounded workers directly with `opencode run`; no additional key or
custom API harness is needed. Keep credentials in OpenCode's existing store,
never in repository prompts/logs. Another OpenCode session has committed
`7fd8adc8d` (native atomic writer and initial test); inspect that patch rather
than duplicating the helper. Its failure coverage and native verification still
need review. Coordinate ownership before writing files another session uses.
The worker has since committed `c64741c28` (TBD3 main save seam and migration
helpers). Root review found acceptance gaps; read
[`PERSISTENCE-REVIEW-2026-09-30.md`](PERSISTENCE-REVIEW-2026-09-30.md) before
closing Batch 1 or proceeding with its current persistence assumptions.

Art presentation update: the user wants PNG previews, not interactive viewers.
Use stills/contact sheets for review; do not build or open more art viewers.
Prefer in-game PNG screenshots when readily available during implementation
or testing. Do not go out of the way solely for a screenshot; clearly label
art-reference previews when native captures are not readily available.

## Starting state

Read both reviewed work packets before editing:

- [Runtime checkpoint](SOL-RUNTIME-CHECKPOINT.md): adapter/route/progress pure
  seams, transactional traversal/pickups, saved resolved geometry and specs.
- [Room checkpoint](SOL-ROOMS-CHECKPOINT.md): recipe-v2 physical planning,
  collision/anchor/arrival helpers and incremental loading.
- [Art delivery](ASTRA-ART-DELIVERY.md): exported assets and browser references,
  native support still pending. Use approved existing art during integration.
- `ART-BRIEF-branch-rooms.md`, `ROGUELITE-ACCEPTANCE.md`, and the completion plan.

DeepSeek's finite-key and codec-collision fixes are already implemented with
regressions. The installer already contains all 21 BF models. Sol corrected a
real upper-door hole: upper arrival `(39,26)` now has solid floor. The separate
bottom opening spans `[-6.5,+6.5]`, with an actual drop trigger and separate safe
arrival. Slopes come from the kit sidecars, not flat invisible proxies.

**Live `main.lua` still uses v1 routes and TBD2 saves. All v2 room recipes remain
uncertified.** Module tests and exported art do not change that. Sol edits may
be uncommitted: inspect both repositories and preserve them and unrelated work.
No release/tag. Offline scope. No uncapped FPS experiment.

Working paths, relative to `/home/gd/melee_linux_test/gdm`:

```text
game:        melee/worktrees/linux
Lua modules: melee/worktrees/linux/pc/scripts/examples/roguelite
tests/tools: tools/roguelite
native test: _build/agents/linux/melee
ISO:        /home/gd/melee_linux_test/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso
```

## Batch 1 — safe persistence and legacy migration

This is the first bounded implementation assignment. Own checkpoint/main save
seams, the native data helper and their focused tests. Keep room/route APIs
stable; report a concrete contract defect before redesigning them.

1. Read `checkpoint.lua`, `progress.lua`, `route.lua`, legacy migration and
   existing save/load call sites. Preserve the frozen v1 generator for old runs.
   The new progress schema is 2; an incompatible older progress object is not
   interchangeable. Implement explicit migration only when enough information
   exists, otherwise preserve and explain the unsupported record.
2. Add a real `gd.data_write_atomic` helper if absent. `gw_script.c` currently
   writes data directly with `fopen("wb")`; ordinary success must not ignore a
   short write or close error. Reuse the sandboxed data-path/name contract and
   bound payloads. Write a temporary file in the same directory, check write/
   flush/close errors, and replace only after success. Check platform replace
   semantics for Linux and Windows. Distinguish atomic replacement from
   power-loss durability in the API documentation. Return a useful failure
   without destroying the previous valid file. Do not invent an unregistered
   Lua API or assume POSIX rename semantics on Windows.
3. Wire TBD3 A/B saves to this capability. Preserve a valid older checkpoint
   when the newest slot is corrupt, writing fails or the process is interrupted.
   Unknown future versions must not be silently replaced by a new run.
4. Persist the resolved manifest plus validated progress and collection/roster
   metadata. Keep selected fighter and active fighter distinct, including
   costume and partner/transform rules. Never regenerate a saved v2 manifest
   from a changed catalogue.
5. Add meaningful failure tests: failed replacement leaves old bytes intact;
   short/failed write reports failure; corrupt newest A/B falls back; reward/
   pickup save failure restores in-memory state; legacy resume remains valid;
   unknown version stays untouched. Use isolated fixtures, never the user's
   only collection. Run focused tests and required native build checks.
6. Contain malformed nested save data at the semantic loader boundary. The
   current pure validator can still throw on some shapes; use controlled
   refusal and adversarial tests. Close the remaining resource-history checks
   for pickup quantities and opened locks; do not assume a checksum establishes
   that a player could have earned the saved inventory.

Deliver this batch as a reviewable patch with actual evidence, then continue
Batch 2 if no other agent has taken its files. Do not widen this batch into new
content, graphics features or a second persistence architecture.

## Batch 2 — connect the existing modules to gameplay

The bulk work is `main.lua` orchestration, not another collection of schemas.
Follow exact signatures in the Sol checkpoint documents and current code.

1. New run: generator → validated resolved manifest → adapter → progress.
   Handle refusal with a useful toast/menu message; do not hide failure behind
   a silently substituted fixed route. Resume uses saved resolved data.
2. Drive load/build/place/encounter/clear/reward/transition phases explicitly.
   Use per-node `Rooms.preload_step`, respect hook budgets and allocation
   failures, and clean owned models/lines/actors on exit or rollback.
3. Build floor segments, platforms and slopes returned by `Rooms.collision`.
   `gd.stage_add_line` already exists; inspect its actual contract. Translate
   local coordinates once. Preserve empty-stage/off-FD isolation.
4. Replace fixed left/right door logic with every node socket. Use the source
   anchor for the trigger and the destination socket's arrival for spawn.
   Support top, bottom, forks, merges, allowed returns and one-way drops.
   A bottom trigger must detect actual downward passage below the floor;
   a broad proximity test can wrongly activate while the fighter stands above.
5. Commit traversal and finite pickups transactionally through `Route.travel`
   and `Route.collect`. Keep Core's gameplay state synchronized with progress,
   including visited/revealed state, opened locks, claims, encounter KOs and
   reward completion. A failed room load or save must not spend a key twice,
   grant a second reward or strand a run in half-transitioned state.
6. Resolve encounter/reward specs from the manifest. Admit only mechanics that
   are implemented. An enemy leaving the camera or disappearing is not proof
   of defeat. Display truthful choices, short toasts and compact HUD feedback.
7. Preserve the user's recursive D-pad tree: Left/Right/Down choose branches;
   Up returns to parent, and only taunts at root. Test native entry/exit restores
   ordinary play and that combat input does not leak while navigating.

Use stubs for focused transaction/state-machine regressions, then test the real
installed bundle. Do not claim the stub proves native geometry or combat.

## Batch 3 — native admission and generated-run acceptance

Create an isolated certification harness that can inspect an uncertified
recipe without bypassing production admission. Natural movement uses ordinary
controller input at normal speed; teleport/debug flight is inspection only.
Record the build, template/recipe/assets and mobility contract with each clip.

Cover every admitted socket and both merge entries, side and upper returns,
one-way drops, short/heavy/floaty/fast-faller/multijump movement, seam contact,
combat/recovery, camera and blast bounds. Start with branch/merge/cross layouts
to expose the physical integration risks. Correct geometry before certifying;
do not flip all flags or reduce the mode to its old linear route.

Then enter through the native TBD button and run distinct seeds through
branching, backtracking, locks, encounter clear, rewards, failure, victory and
resume of the exact same route. Include allocation refusal, interrupted
transition, corrupt newest A/B, legacy resume and failed reward save. Save
durable logs/clips in a build-identified acceptance directory.

Existing native test triage by root used the current binary with
`MELEE_MODS=0 MELEE_SCRIPTS=0`: pad pair 2/2, lab-events 1/1, then full `script_`
group **33/33 passed**. The three failures from the earlier installed-script run
are not established engine regressions or proven fixed; compare the actual
test environments if they recur. Never dismiss a failure as pre-existing
without evidence. These results do not test your forthcoming native edits.

## Later cheap bulk work, after the generated-run gate

Use the completion plan's dependency order. Good bounded packets include
implemented reward/item catalogues against stable APIs, encounter composition
and schedules, menu screens built from the existing kit, asset ingestion with
bounded resident sets, and deterministic content/transaction tests. Each needs
actual player-visible behavior and validation, not just data definitions.

Keep model history/render hooks, cross-platform atomicity and native lifecycle
changes small enough for Sol review. Astra supplies new final art; browser
afterimages, ribbons and surface patterns are not already implemented engine
features. Do not multiply cosmetic variants while the underlying feature is
missing. Continue independent engineering when an art review is pending.

## Coordination and evidence

One owner at a time for the shared native build/game. Check that earlier agents
have frozen their work before taking the same files. Commit only owned reviewed
files; preserve the working collection and unrelated dirty work. Use the
existing completion plan's build/install commands and actual current APIs.

Both Sol workers have frozen their implementation. Root's final combined
discovery after both patches passed **37 named tests**, plus the separately
printed module suites, in 7.277 seconds. Evidence:
`_build/sol-runtime-backup/combined-tests.log`. Owned tracked diffs pass
`git diff --check`. Changes are local and have not been installed into the game;
there is no new native gameplay acceptance claim.

After each batch report changed files, behavior now live, exact commands and
results, evidence paths and remaining limitations. The Python suite includes
import-executed suites as well as named unittest cases; report both honestly.
Continue available work, but never label human polish, Windows/hardware
acceptance or physical rooms passed without the corresponding evidence.

## Message to give DeepSeek

> Read `gdm/docs/DEEPSEEK-BULK-HANDOFF.md` and both linked Sol checkpoint docs.
> Continue the existing implementation, starting with Batch 1 safe persistence,
> then live integration and native certification. Preserve the current dirty
> work and all completed foundation fixes. Own the bulk code in bounded,
> tested patches; Sol will review/integrate and Astra owns new art. Do not stop
> at another contract-only pass, bypass certification, overwrite unsupported
> saves, resume the cancelled FPS experiment or publish a release. Report actual
> live behavior and test evidence separately from pending acceptance.
