# TBD roguelite — handoff to the next model

Updated 2026-09-30 after watched movement testing, the ascent spawn correction, and development-branch pushes.

## Assignment

**Scope update:** the user has authorized the new model to own the entire remaining 100/100 program. Read `FULL-100-100-MODEL-ASSIGNMENT.md` alongside this handoff; it supplies the milestone-by-milestone execution mandate through final content, polish and platform acceptance.

Continue the offline TBD roguelite toward the full completion and polish contract in `ROGUELITE-COMPLETION-PLAN.md`. Do not restart planning or rebuild already working systems. The next practical milestone is **one complete generated run through validated rooms, with combat, rewards and reliable save/resume**. This is an intermediate milestone, not permission to reduce the final scope to a demonstration.

Read this handoff first. The longer completion plan supplies the full requirements; this document supplies the latest facts and an execution order. Historical status paragraphs in other documents may be superseded by the evidence below.

## User decisions to preserve

- Offline only; networking is excluded.
- Entry: Load game → Main menu → **TBD** → custom mode. Decoupled from the post–Master Hand content.
- Melee movement, spacing, shields, DI, recovery and ring-outs remain the foundation.
- Recursive combat command tree: Left/Right/Down choose branches at each depth; Up goes back one level. Only a fresh Up press at the root taunts. Navigation remains real-time.
- Compact combat HUD replaces vanilla stock/percent when ownership is successfully acquired. Use the menu kit and useful, restrained toasts.
- Player and eligible opponents use the gene system. Enemy variety and capable CPU decisions matter, not just increased HP.
- Use our custom modular models and placement rules. Hide original FD geometry in actual room play.
- Connect genes, placements, equipment and upgrades to meaningful character/body/accessory regions and readable effects.
- Normal-speed testing only. The uncapped/turbo benchmark was cancelled.
- When automation is inconsistent, preserve evidence, note the uncertainty, and move on. Retest with the user watching. Do not repeatedly force a green result.
- Show actual in-game PNGs. No simulated game screenshots or interactive preview viewers. Leave requested PNG previews open when practical.
- Astra owns final new art unless the user explicitly delegates it elsewhere. Existing asset integration can continue.
- Cheap DeepSeek/OpenCode workers are authorized for isolated bulk work at ordinary effort. Root/coordinator reviews and lands changes. Never expose API keys.
- GitHub development pushes are authorized after review. **No release, release tag, or publishing step.**

## Workspace and isolation

Workspace: `/home/gd/melee_linux_test`.

| Purpose | Location / branch |
| --- | --- |
| Tools, docs, assets | `gdm`, branch `agent/linux-qt-launcher` |
| Native game and Lua | `gdm/melee/worktrees/linux`, branch `agent/linux` |
| Frozen user-model submission | `gdm/_build/model-tests/campaign-integration` and its nested game worktree |
| Frozen DeepSeek gene-world candidate | `gdm/_build/deepseek-worktrees/gene-world` and its nested game worktree |
| Current isolated native review profile | `gdm/_build/agents/roguelite-handoff-review` |

The roots contain substantial intentional uncommitted native, art and documentation work. **Do not reset, clean, stash everything, broadly stage, or overwrite it.** A clean GitHub checkout is not equivalent to the current tested local executable.

For a new implementation worker, create a separate wrapper worktree and nested game worktree from the current coordinating branch heads. Give the worker an explicit file allowlist. Do not reuse either frozen candidate lane. The nested game repository must be a real separate worktree, not a shared symlink into root.

Seed only needed, reviewed local dependencies/assets into that lane; record their original hashes in a seed manifest. Record deliberate local dependency changes separately. In particular, generated kit assets and the native seam APIs are not all committed. Do not silently treat an older seeded helper as newer than root. A worker can use a copy of the tested native binary in its own app profile for Lua checks, but must record that binary's hash and must not claim it was built from its own clean source.

Inspect current processes, console connectivity, Git status and worker reports before resuming anything. Process IDs, controller event numbers and sessions can change. Do not edit a lane whose writer is still active. Root owns integration and native acceptance; never run competing writers on `main.lua`.

## GitHub status

Verified remote branch heads at this handoff:

- `GurekamDhillon/gd-melee-workspace`, `agent/linux-qt-launcher`: `9369f60b7be11ad0685cc8784554bd941579a9df`.
- `GurekamDhillon/melee`, `agent/linux`: `5664a6db1cf2d096db8df0e3e58775d31dbed23e`.

These committed branches were pushed. Uncommitted local engine/art/docs work and frozen worker candidates were **not** pushed. No release or tag was created. Recheck remotes before subsequent pushes; do not force-push.

## What is implemented and validated

### Persistence and runtime integration

Safe persistence work includes atomic native data writes, A/B checkpoint handling, future-schema preservation and the TBD3 save/progress seam. Campaign and presentation integration is landed in game commit `fed9dbf94` and wrapper commit `a5fdad4`.

Root corrected defects found during independent review:

- Recovery never resumes native gameplay while room cleanup/rollback is still owed.
- Exhausted objective saves resume settling, preserving finish/reward continuation exactly once.
- A refused final-KO result save keeps the distinct Retry Finish page; a healthy campaign cannot resurrect a zero-life run.
- Failed HUD restoration retains ownership for lifecycle retry; draw/layout failure attempts vanilla fallback.
- The loadout-derived command tree works in both legacy and v2 routes. Held-Up state, supply depletion/refund, placement/resume and the eight-step observed onboarding sequence have regressions.
- Native launch found a collection renderer nil-room access; fixed in `0eab9b9b4`, with regression `e00c463`.

Latest full root pure/stub discovery: **244 tests OK**, 17.373 seconds, recorded in `_build/deepseek-coordination/ascent-spawn-regressions.log`. This is not native gameplay evidence for every feature.

Production recipes remain uncertified. Consequently shipped new runs currently fall back to the legacy route. Live-v2 tests open admission only in throwaway fixtures. Do not claim that generated production runs are already enabled.

### Native floor seams and ownership

Explicit room-local `gd.stage_link` connects adjoining floor endpoints. Root's Lua room helper is committed; native seam/owner code still includes uncommitted files. The tested native build passed **214/214 native tests**, plus actual-source seam sanitizer checks.

Live owner probe verified cleanup after a deliberately throwing unload hook: one script's instance/collider was removed while another owner's shared-asset instance remained usable. This is ownership evidence, not full traversal certification. See `native-owner-live-probe.json`.

Do not remove the explicit linking, substitute global automatic welding, or join overlapping source/destination rooms. Keep ownership and failed-cleanup retry semantics.

### Human and native movement evidence

The user tested Falco with an 8BitDo Ultimate 2C physical controller:

- “Stairs are perfect, no pop or snap.”
- Balcony/ramp/upper-landing joins, up and back down: “feels good.”
- Earlier human tests also established Falco lower-door reachability and merge ground-level access. Later automated falls do not erase those observations.

The subsequent automated sweep produced setup refusals and falls. User identified a real spawn defect: Jigglypuff/Kirby spawned inside the stairs.

The shared ascent recipe originally placed the left arrival at x=-42, inside the slope spanning x=-52 to -26. Root moved **both the default spawn and left arrival to x=-58.5, y=0**, on the flat lead-in. This applies to every recipe using the shared ascent geometry. It is not a fighter-specific teleport workaround.

- Source: `5664a6db1`; regression: `9369f60`.
- Corrected native probes: **Jigglypuff ascent/return and Kirby ascent/return all arrived, without unexpected falls**.
- Both ascents and Kirby return had no classified seam-pop candidate.
- Jigglypuff return has a classifier candidate still needing watched review; it is not a confirmed human snag.
- Bowser's previous ascent arrived, but return/forks were inconclusive because placement refused.
- Merge's latest automated left-entry attempt fell; upper placement refused.
- All latest junction/drop placements refused. **There is no drop traversal pass.**

All recipes remain uncertified. These checks do not establish every fighter, equipment modifier, door transition or full room certificate.

## Immediate execution plan

1. **Finish room acceptance.** Recheck Jigglypuff return and Bowser return with the corrected spawn. Test both merge arrivals and actual drop-through/one-way behavior. Verify safe arrivals, floor clearance, camera/blast bounds and ordinary recovery. Broaden to the currently offered roster before calling a room fully certified.
2. **Fix any genuine layout/arrival defect at its source.** Keep spawn clearance, doorway socket anchors and actual collision distinct. Never change collision solely to make a preview look right. Keep documentation/recipe versions and saved-manifest compatibility consistent when geometry changes.
3. **Admit only reviewed recipes.** Define and record exactly what certification covers. Keep uncertified layouts out of production generation. Do not bulk-flip every `certified` flag or bypass admission to claim progress.
4. **Exercise real v2 runs.** Start through the product menu. Validate discovered maps, branches, returns, merges, pickups, opened-door policy, optional locks, combat/reward completion and safe travel transactions together. Complete one generated run; verify death and resume as well as success.
5. **Continue native gene integration in parallel.** Resolve the pending adapter review below. Prove complete Cinder/Rime and Thermal Shock loops with genuine native contacts, costs, interruption and counterplay before expanding families.
6. **Continue the remaining full-mode gates.** Encounters/AI/bosses; inventory/equipment/economy; region/accessory effects and audio; menu/onboarding/results polish; both-platform packaging and complete-run/soak acceptance.

Commit bounded changes after relevant checks. Keep the acceptance ledger current. A helper passing tests does not complete its gameplay gate.

## Pending gene-world adapter review: concrete engineering task

Accepted gene transaction helpers landed in game `f26863364`, wrapper `54bc740`. Spend revisions follow the exact runtime state object; mark restores are conditional. Do not weaken those ownership protections or refund an entire run snapshot.

The separate adapter candidate has completed three correction passes and is frozen for root review. It is **not landed or wired into production**. Read:

- `_build/deepseek-coordination/gene-world-report-3.md`.
- `_build/deepseek-coordination/gene-world-review-3.md`.
- Lane `AGENTS.md` and `GENE-WORLD-REVIEW-SEED.json`.

Latest remaining P1: **contribution capacity is checked after provider mutation**. With max capacity 1, repeated refused guard actions can allocate and retain three native tokens while refunding charge; the action engine sees no accepted contributions. This permits unbounded retained ownership.

Required correction: reserve/check capacity before calling the provider, and refuse before spend where possible. Handle concurrent/reentrant callbacks. Preserve ownership of every token already issued, including refused actions. Keep original-run cleanup identity and exact-true provider acceptance. Regression must use actual Core/actions/adapter with stateful live-token accounting, not just compare table counts.

Previous token cleanup, replacement-run identity, unknown eligibility and custom movement preflight findings were independently verified fixed in pass 3. Preserve them. Candidate focused tests pass, but full lane discovery has **three missing generated-asset/sidecar errors**; it is not a green full suite.

Native hit contract is separately unresolved: `ftColl_80076640` can chip armor and return false. Native scripted hit/strike wrappers must distinguish pre-acceptance refusal from accepted armor contact before callers safely refund based on false. See `native-hit-refusal-audit.md`. Preserve ordinary armor chipping/spill behavior and do not fabricate collision callbacks. Adapter requires an explicit confirmed native-contract opt-in; do not enable it merely to get tests green.

## Testing and evidence discipline

Run pure/stub tests from `gdm`:

```sh
python -m unittest discover -s tools/roguelite -p 'test_*.py'
```

Relevant tools: `prepare.py`, `certify_rooms.py`, `live_acceptance.py`, and the native console client `melee/worktrees/linux/pc/scripts/console.py`.

Current native profile uses console port **51701**, paced 60 Hz and turbo off. Confirm that the running executable is the expected one before controlling it. The disc is local and must never enter Git or artifacts. Avoid changing the user's real saves or shared app profile.

The certification fixture has custom room geometry but **does not perform door transitions**. Reaching its doorway tests movement only. Actual runtime door use needs separate testing.

Pause during fixture construction and initial placement so removal of host geometry cannot kill the fighter before testing begins. Then resume ordinary native physics for traversal. Fixture teleports are setup, never reachability evidence. Release scripted pad ownership before user control. Do not let an idle CPU attack the test fighter.

Focus loss can throttle the game severely. Check actual logic timing; a configured target of 60 alone is insufficient. Discard the prior unfocused approximately 5-Hz attempt. Never use turbo to mask this.

The root native `shot` capture omitted script UI in the latest check. The actual desktop game-window PNG showed the compact HUD, onboarding and ability tree correctly. Use a window capture when UI evidence is needed; do not substitute a mockup.

Evidence directory: `gdm/_build/deepseek-coordination/`. Useful files:

| Evidence | Scope |
| --- | --- |
| `ascent_spawn_corrected-summary.json` | Corrected Jigglypuff/Kirby ascent and return |
| `branch_remaining-summary.json` | Earlier Bowser/small-fighter sweep; spawn defect supersedes applicable ascent failures |
| `merge_drop-summary.json` | Inconclusive/failing merge/drop attempts |
| `handoff-native-evidence.json` | Native HUD/menu smoke-test scope and limitations |
| `native-previews-clean/handoff_window.png` | Actual desktop capture of in-game custom room, rail and command tree |
| `native-owner-live-probe.json` | Live owner fallback cleanup |
| `model-handoff-review.md` | Independent review and root disposition of frozen user-model submission |

Some JSONL logs contain multiple interrupted run starts. Use their matching final summaries; do not combine an old pass with a newer refusal to manufacture completion.

## Remaining full completion/polish scope

Follow Gates 0–12 in the completion plan. In particular, do not omit:

- Materially different generated topology, certified room catalogue, discovered map, branches/returns/shortcuts and transactional exploration.
- Full gene/reward/synergy content, shared player/enemy rules, event provenance and genuine native combat behavior.
- Varied non-fighters and fighter CPUs, capable AI, distinct boss phases and readable counterplay.
- Consumables, equipment, collection/breeding/inheritance/fusion/export and bounded economy/history.
- Every advertised character/costume, partner/transformation and accessory visual binding.
- Persistent region shaders, afterimages, trails/tracers, halos and other agreed effects beyond bursts, with clear priority/budgets and matching mechanics.
- Audio, camera, room framing, transitions, loading/error states, complete results and usable compact menus.
- Reproducible Windows/Linux/Qt delivery, display/input/controller checks, save migrations, offline regressions and long-session resource/performance checks.
- Complete natural-control runs and human judgments of fun/readability. Existing content-count targets are provisional design targets, not evidence that those counts already exist.

Do not invent a completion percentage. Report accepted gates, working-but-unvalidated systems, active defects and pending human/hardware evidence separately.

## First response expected from the new model

Inspect current state, establish isolated ownership, and report the next bounded task being executed. Continue work rather than asking the user to approve an abstract plan again. Preserve the latest human findings and spawn fix. Do not call the mode finished after a helper, screenshot or fixture passes.
