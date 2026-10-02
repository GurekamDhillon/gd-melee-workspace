# New-model task: finish campaign acceptance and wire the compact command UI

Work only in this directory:
`/home/gd/melee_linux_test/gdm/_build/model-tests/campaign-integration`

The game checkout is nested at `melee/worktrees/linux`. These are two independent
Git worktrees on `agent/model-test-campaign-20260930`; neither is the coordinator's
working checkout. No other agent will write to this lane. The previous DeepSeek
campaign session is terminal and retired; do not resume it. Do not edit its lane,
the coordinator root, or another worker's files.

Read `docs/ROGUELITE-COMPLETION-PLAN.md`, this handoff, and the frozen evidence
`docs/MODEL-TEST-integration-followup-5-report.md`. The full goal is offline TBD
roguelite completion/polish. This task is a bounded part of it, not permission to
redefine completion as a slice or claim all gates done.

## Starting state

Coordinator copied reviewed root modules/tests/generated assets, then the frozen
DeepSeek campaign fifth pass. `MODEL-TEST-SEED.json` records initial source hashes.
`MODEL-TEST-BASELINE.log` records the combined baseline run in THIS lane. Inspect
its result before changing anything; a historical green report isn't proof.
Do not commit the seeded dirty files as your own changes. Use the seed manifest
and your exact owned-file list to describe your patch.

Safe persistence and room/encounter/reward/inventory/equipment services are landed.
Compact commands/menus/feedback/HUD layout/onboarding are landed as helpers but
not fully wired into main. The campaign fifth pass has 27 focused tests; final
coordinator review remains pending. Preserve the production certification gate:
all recipes remain uncertified. Tests may grant admission ONLY in isolated test
copies, never in the checked-in production table.

The coordinator's Linux native cleanup build passed 213/213 tests plus bridge/ABI
checks. Its owner-cleanup patch is in root working files and NOT part of this
lane's native HEAD. You must not rebuild/install/launch the game; root handles
that seam and native integration. The user is currently testing a separate
profile with a Bluetooth 8BitDo controller. Do not touch its console/pad/windows.

Physical watched evidence: Falco reached the branch lower door, and the user
confirmed the merge room accessible. User reported snag/pop at all slope joins.
A Sol worker is implementing explicit native floor links. Do not remove the
certification gate to manufacture a working generated route while this is open.

## Your file ownership

Game:
- `pc/scripts/examples/roguelite/main.lua`
- `pc/scripts/examples/roguelite/runtime_campaign.lua`
- optionally NEW `pc/scripts/examples/roguelite/runtime_presentation.lua`

Wrapper:
- `tools/roguelite/prepare.py`
- `tools/roguelite/test_v2_runtime.py`
- optionally NEW `tools/roguelite/test_presentation_runtime.py`
- NEW `docs/MODEL-TEST-RESULT.md`

Read other files freely inside this lane, but report required helper changes
instead of modifying Core, codecs, recipes, inventory, enemies, gene-actions,
native source, or generated art. Root coordinates those writers. No new art.

## Phase A: verify and finish the campaign's real ownership contract

Inspect the fifth pass against the prior review in
`docs/MODEL-TEST-integration-review-3.md`; some defects are now fixed. Reproduce
current behavior before proposing edits. Native `gd.player` returns a fresh
snapshot table, not an alias. `gd.teleport` and several setters return nil on
success, but false/throws must still be handled where applicable. Never invent
undocumented native APIs.

These invariants must hold together:

1. Pause BEFORE building destination colliders/placing fighters, stay paused until
   source rollback or destination settling and cleanup genuinely completes. One
   bounded phase per tick; ordinary combat ticks don't run in dual-room phases.
2. Keep refused collider/model/effect cleanup ownership. No reset(true) except a
   confirmed native scene teardown. An effect-pending heal rollback cannot be
   thrown away by teardown/drop_pending/new-run retirement or unload claims.
3. Successful new-run promotion may not unpause/build its room while an old owner
   remains; retirement retries bounded, retains ownership on exhaustion.
4. Old campaigns retain their old run/route identity forever. Their teardown must
   not remove a new run's coincidentally named gene/host or flush old progress to
   a new checkpoint.
5. Current campaign must coherently follow current menu/reward/restore commits:
   the real Menus.place/fuse output replaces a run table, and the next lose_life
   save must retain that loadout. Audit all run= and restore assignments. A failed
   initial save restores the exact previous references/profile/fighter/campaign.
6. Persist newest coherent progress; no stale pending save after newer successful
   travel/reward/item commit, no free heal or resurrected supplies/lives/rewards.
   Terminal storage failure must expose an actual recoverable path, not strand
   a pending record in an undriven phase. Refusals never overwrite future saves.
7. Engine stock baseline stays99; one observed native loss counts one logical
   life/KO. Untouched champion may not auto-clear, and repeated combat waves must
   work. Combat doors remain objective-gated; no disappear=defeated shortcut.

Use real bundled-main/Core/Menus and the real runtime helpers in tests. Don't
patch a method to just return true and then call that an integration proof. Add
regressions only for actual defects; don't replace meaningful assertions to make
new behavior pass. Existing 27 focused campaign tests and legacy persistence must
stay green. No speculative redesign if the fifth pass already satisfies a case.

## Phase B: wire the already reviewed compact UI into the live runtime

Read commands.lua, menus.lua, feedback.lua, hud_layout.lua and onboarding.lua.
Implement their actual main hooks, for both live-v2 and legacy-v1 where useful:

- Bundle `Hud`/`Onboarding` (and presentation helper if used) before main. Keep
  all earlier runtime module names/order compatible; no generated code missing
  from installed bundle. Do not accidentally drop the reviewed inventory modules
  from future integration plans; inventory persistence is a separate task.
- Build/pass Hud.layout to Feedback.draw. Verify the engine's logical UI
  coordinate system; OS screenshot resolution is not automatically UI coordinates.
  Use documented size APIs or the existing640x480 virtual canvas. Do not invent
  gd.viewport or pixel-DPI APIs. A large window should not enlarge HUD coverage.
- Enable the compact custom life/percent/ability rail intentionally and restore
  vanilla HUD ownership on leave/unload/error. Native gd.hud_visible(false) can
  legitimately return false as the new state; don't treat it as failed mutation.
- Preserve the recursive D-pad tree. Left/right/down fork; Up goes to the parent,
  and only a fresh Up at root taunts. Rebuild loadout trees without resetting a
  held-Up edge. Do not add A-confirm navigation or pause ordinary combat.
- Rebuild command loadout after gene placements/changes/resume/current-run commit.
  Show actual ability names/readiness/cost, disabled Restore when supplies0, real
  refusal reasons and no options that execute unsupported mechanics.
- Preserve cleared-door proximity/input routing versus the root Down item branch;
  test that one press cannot both spend a consumable and travel. Approved
  collection context remains rest-only. Do not quietly add an anywhere safe exit.
- Feed truthful Onboarding.observe events from real movement, charge, command,
  cast, tell, door and reward paths; don't complete tutorial steps by construction
  or show teaching for unimplemented genealogy/fusion features. Surface tutorial
  hints through the existing toast system without covering normal enemy tells.
- Honor existing reduced-motion setting if present, avoid noisy repeated toasts,
  and keep UI input/render failures from corrupting run/save state.

Do not wire new unreviewed enemy/gene prototypes or invent playable inventory
items just to populate menus. Core currently offers Cinder/Rime; new families
still await native bindings. This task should finish meaningful live UI hooks,
not pretend the entire content target exists.

## Tests and report

Run in this worktree:
```
python3 -m unittest discover -s tools/roguelite -p 'test_*.py'
```
Run focused files while iterating, then the full suite once final edits stabilize.
Record exact commands and counts; import-time module suites aren't named methods.
Test real draw coordinates/ownership, actual input edges, main state transitions,
and bundle/installer behavior, including meaningful failure cases.

Native playtesting is root-owned. If automated results are difficult/inconsistent,
record the exact setup, expected/observed result and proposed watched retest, then
move to independent work. Reproducible data-loss/ownership bugs still need fixing.
Do not flip certificates or lower acceptance to make tests green.

Write `docs/MODEL-TEST-RESULT.md`: exact files/changes, baseline vs final test
results, residual issues, documented native needs and root's integration steps.
Provide a compact patch/diff against your seed, then STOP editing for root review.
No commits/pushes/releases, no turbo/uncapped test, no root/shared mutations.
