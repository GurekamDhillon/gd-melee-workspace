# Active coordinated implementation — 2026-09-30

User closed the previous OpenCode session and authorized standard-effort
DeepSeek workers in as many isolated worktrees as useful. Root owns reviews,
landing, shared native builds, installed profiles and game runs. No release.

| Worker | Location | Owned output | State |
| --- | --- | --- | --- |
| Persistence | Main checkouts | main/checkpoint persistence, bundler, focused tests | Landed persistence seam; atomic-only refusal regression reviewed |
| Physical | `_build/deepseek-worktrees/physical` | `runtime_rooms.lua`, `test_physical_runtime.py` | Reviewed; focused tests green, integration pending |
| Encounters | `_build/deepseek-worktrees/encounters` | `runtime_encounters.lua`, `test_encounter_runtime.py` | Reviewed; focused tests green, integration pending |
| Certification | `_build/deepseek-worktrees/certification` | isolated certification script/mod and CLI/tests | Reviewed harness; root native probes uncovered scene/timing/output fixes |
| Rewards | `_build/deepseek-worktrees/rewards` | `runtime_rewards.lua`, `test_reward_runtime.py` | Reviewed; focused tests green, integration pending |

| Live integration | `_build/deepseek-worktrees/integration` | `main.lua`, optional `runtime_campaign.lua`, bundler, new v2 integration tests | First output reviewed; corrective pass active on reproduced pause/stock/encounter/save/rollback defects |

Each isolated lane has separate wrapper and game Git worktrees on an
`agent/deepseek-<task>-20260930` branch. Frozen Sol module/test changes were
copied in as baseline, not as newly owned work. Only copy/land each worker's
owned outputs after it stops editing; never indiscriminately commit its baseline
dirty changes. Review interfaces and dependency order before wiring main.

Task prompts and JSON event logs are in `_build/deepseek-coordination/`.
All workers use `deepseek/deepseek-flash` with default effort, `--pure`, and
bounded coding tasks. Root's direct API authentication test passed. Credentials
remain in the existing OpenCode store. See `DEEPSEEK-COORDINATION.md`.

Root completed native path-check follow-up `05d2f429a`, built the Linux binary
with bridge/ABI checks, and passed the 34/34 native scripting group, including
long-path refusal preserving old data. Root has not claimed the full new mode
is installed/live. Production recipes remain uncertified.

Next integration order: persistence acceptance → physical/encounter/reward module
review → live route creation/entry/doors/progress wiring → isolated native
certification harness runs → admitted generated-run acceptance. Then continue
later content/menu/FX/platform/polish gates from the full plan. Human feel and
unavailable hardware stay pending; they do not block independent engineering.

Only actual in-game PNG captures may be shown or left open for the user.
Do not reopen art-reference/mockup galleries, create interactive viewers, or
run the cancelled uncapped/turbo experiment.

Review update: helpers plus existing module/runtime suites passed 111 named tests on root (before later harness refinements). Physical 10/10, encounters 8/8, rewards 11/11 focused cases passed. Native room probe is not certified: a probe logging error released stage isolation after construction; corrected binding and successful-build regression now pass, native rerun underway; original FD visibility makes captures diagnostic only. Harness now waits through Ready/Go, retains partial cleanup ownership, parses multi-argument Lua commands correctly, uses absolute PNG paths and bounded trace pages. Do not admit recipes or claim generated runs playable from this evidence.

Additional user-authorized standard-effort lanes started: `gene-actions` (bounded startup/active/recovery and authored behavior contracts), `layouts` (distinct collision/kit layouts, uncertified), `enemy-behaviors` (observable AI and distinct boss controllers), `menu-polish` (recursive D-pad grammar, compact HUD/onboarding/toasts), `inventory` (bounded item/equipment/economy services). They own disjoint files, do not edit main/bundler, and cannot build/install/drive the game. Root reviews and integrates; data-only/prototype work is not shipping completion. New final art remains Astra-owned.

Live integration review (Sol): combined root suite123 named cases green, but new native-correct snapshot stubs reproduce false boss KOs, absent pause, old encounter ownership preventing a second fight, stale save retries/free heals, missing active retries, refused native heals consuming supplies, rollback ownership lost and invalid unload teardown assumptions. Not landed or installed. DeepSeek corrective pass is active. Supplemental review is saved in `_build/deepseek-coordination/integration-review-addendum.md`; check these against its next output before landing.

User clarified screenshots must be actual in-game captures ONLY. Removed the mockup/reference-sheet gallery from desktop; `roguelite-game-captures` transient user service opens native Falco branch-room PNGs from `native-previews-clean`. Do not reopen art-sheet/mockup/simulated UI galleries. PNGs and screenshot claims must come from the running engine.

Coordinator update: certification harness followup landed (`66e7818` wrapper,
`24b164c5f` game), 62 focused tests green. Native branch_y v7 arrived on three
segments; lower fork attempt fell and return has a seam-pop review candidate;
no certification. A normal-speed rejoin_merge Falco probe is now running.
Integration second correction, inventory second correction, enemy fairness/boss
correction and layout mobility/theme correction have confirmed live OpenCode
processes in their isolated lanes. Gene/menu frozen followups are undergoing
Sol review. Root reproduced inventory plan tampering (heal999 and zero-spend
output accepted); do not integrate its first correction. See current audit in
ROGUELITE-ACCEPTANCE.md, which supersedes historical baseline status.

Later review update: inventory second correction landed (game `1be259f18`,
wrapper `05be7a1`), root 16/16 plus original adversarial probe green. Still a
pure service, not in-game inventory. Integration second correction (19 tests)
and layout correction returned; independent review pending. Gene/menu second
corrections and enemy first correction remain active. Native merge probe v1
failed setup timeout, v2 is running with a longer bounded Ready/Go startup wait.
Native script unload currently lacks per-script ownership for stage/model
resources; a native seam is required, not a fabricated reset(true).

## New-model handoff / campaign writer retired

User requested work to test a new model in an isolated area. DeepSeek campaign
session `ses_f0bc253ceffeVyPhAOtkZu7w9j` is terminal after corrective pass5;
no process remained when handoff was created. Do NOT resume that writer or
start another main/campaign/UI integration writer during this reservation.

New external-model lane: `_build/model-tests/campaign-integration`, wrapper and
nested game worktrees on `agent/model-test-campaign-20260930`. Task:
`MODEL-TEST-TASK.md` — verify campaign acceptance, then wire compact HUD,
loadout command tree and truthful onboarding. Reviewed assets are copied;
no shared asset symlink writes. Initial sourcehashes in MODEL-TEST-SEED.json.
Coordinator-ran baseline199namedtests OK (1skipped), import-level suites green.
User will supply/run the model; creation of a lane is not evidence it is running.
Root/Sol continue native seams, cleanup and separate combat/helper reviews.
Root must not overwrite the reserved lane or copy live output until it freezes.


## Coordination update after new-model reservation

- Campaign integration remains reserved for the user's new model. No replacement
  DeepSeek campaign writer has been started.
- Gene actions corrective pass 5 is running in the existing isolated gene-actions
  lane, session `ses_f0bb67b3affe04vwHUrcZ4TZdx`, process handle 12007. It addresses
  revision-registry saturation: refusal must precede mark mutation and charge
  spending, while tracked targets remain usable. Prompt and log are in
  `_build/deepseek-coordination/gene-actions-followup-5.*`.
- Enemy corrective pass 3 is terminal. Its 30-case report claims exact run/gene/
  state identity binding. Sol runtime is independently reviewing it before landing.
- Sol rooms is finishing an isolated native stage-link patch in
  `_build/sol-worktrees/stage-seams`. Actual-source floor-follow and island tests
  passed; final review and seed-relative patch are pending. Root owns Lua callers.
- Watched merge accessibility is recorded; the user-reported ascent snag remains
  an open defect. No native recipe certification has been granted.
