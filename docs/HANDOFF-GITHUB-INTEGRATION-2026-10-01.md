# GitHub integration handoff for the next model

Prepared 2026-10-01 for this Windows workspace. This document supersedes the earlier chat's branch inventory for integration planning. It does not supersede the architecture and safety rules in `AGENTS.md`, `docs/HANDOFF.md`, or the upstream acceptance ledger.

## User request and scope

The user wants outstanding GitHub work consolidated into the active main branches so they can start new work. The term is **repository integration**, **branch consolidation**, or **bringing main up to date**. A pull alone is insufficient because the changes are on feature and recovery branches.

The user's latest instruction was: **“Also dont actually do it, get a doc ready fora different model to do it?”** This session therefore stopped implementation/integration and prepared this handoff. No branches were merged, no commits were made, and nothing was pushed or published. Fetches and an isolated graphics worktree were created before the handoff request.

For the next model, the intended deliverable is an integrated, verified Windows working baseline in both repositories, preserving local work and accounting for every incoming branch. This is not an instruction to finish the entire roguelite 100/100 program or publish a release. Keep unfinished feature acceptance explicit. The next model should proceed when the user assigns it this handoff; this document records intent rather than granting an independent background task.

## The two repositories and current local state

Root: `<workspace>`.

| Repository | Active target | Local HEAD | GitHub remote | Published main HEAD |
| --- | --- | --- | --- | --- |
| Workspace, tooling, assets and docs | `master` | `52b91aa` | `origin-ws`, GurekamDhillon/gd-melee-workspace | `1ae7f03` |
| Game, native code and Lua | `melee`, branch `pc-port` | `28c528018` | `pub`, GurekamDhillon/melee | `1f5b36baf` |

Workspace local `master` contains all of `origin-ws/master` and is 42 commits ahead. Game local `pc-port` contains all of `pub/pc-port` and is 50 commits ahead. These local commits must survive integration. The game also has remote `origin` pointing to doldecomp/melee; do not confuse upstream decomp `master` with the port's target `pc-port`.

The workspace has pre-existing modified files:

- `tools/slippi/compare_finalized.py`
- `tools/slippi/test_compare_finalized.py`
- `tools/slippi/test_two_client_replay.py`
- `tools/slippi/two_client_replay.py`

It also has existing untracked build/run directories, `_research/tm/`, `tools/discord/`, `menu/out_discord_pins/`, `menu/out_discord_refresh/`, `ports/kirby-ultimate/animations/manifest.json`, and `set_function`. Preserve these. The parent game checkout was clean at the last inspection. There are many existing game worktrees; do not infer ownership or completion from their names. Read their current status before using one.

Do not use broad `git add .`, `git clean`, hard reset, or checkout-overwrite operations. Back up the exact tracked diffs before integration and preserve untracked material separately as needed. Stage only reviewed authored files; never disc-derived assets, generated bridges, binaries, caches or downloaded SDKs.

## Incoming work and authoritative starting points

The latest fetch discovered the October 1 cross-machine snapshots. Begin with the primary pair:

| Repository | Primary incoming branch | Observed HEAD | Commits absent from local target |
| --- | --- | --- | ---: |
| Workspace | `origin-ws/handoff/2026-10-01/roguelite-100-integration` | `1da9335` | 79 |
| Game | `pub/handoff/2026-10-01/roguelite-100-game` | `3062566f5` | 47 |

Both primary branches diverge from local targets: local-only counts remain 42 workspace and 50 game. A reset or replacement checkout would lose local work. Merge into an integration branch based on the local target, then reconcile and verify.

Read these **from the incoming workspace ref**, since the active root does not contain them yet:

```powershell
git show origin-ws/handoff/2026-10-01/roguelite-100-integration:docs/handoff/2026-10-01/README.md
git show origin-ws/handoff/2026-10-01/roguelite-100-integration:docs/handoff/2026-10-01/SNAPSHOTS.json
git show origin-ws/handoff/2026-10-01/roguelite-100-integration:docs/ROGUELITE-100-100-LEDGER.md
git show origin-ws/handoff/2026-10-01/roguelite-100-integration:docs/handoff/2026-10-01/reports/coordination/100-100/ROOT-REVIEW-NEW-WORK-2026-10-01.md
```

The [upstream handoff](https://github.com/GurekamDhillon/gd-melee-workspace/blob/1da9335607fe8f931a5b1f7a07f9d6f2261e2541/docs/handoff/2026-10-01/README.md) explicitly says the snapshot branches contain overlapping copied baselines and unreviewed agent changes. Treat them as recovery/reference branches, **not a queue to merge wholesale**. Reconcile unique changes against the primary integration pair and its newer review findings. The root snapshot may contain useful source absent from the reviewed pair, but may also carry an older or incompatible variant.

Additional priority refs:

| Repository | Ref | HEAD | Commits not in primary integration |
| --- | --- | --- | ---: |
| Workspace | `origin-ws/release/linux-0.1.8` | `a30d155` | 5 |
| Workspace | `origin-ws/handoff/2026-10-01/linux-qt-launcher` | `c2f5332` | 1 |
| Workspace | `origin-ws/handoff/2026-10-01/model-test-campaign-20260930` | `6d465c1` | 1 |
| Workspace | `origin-ws/handoff/2026-10-01/gene-world-capacity-20260930` | `089fa74` | 1 |
| Game | `pub/handoff/2026-10-01/linux` | `15c459c50` | 1 |
| Game | `pub/handoff/2026-10-01/model-test-campaign-20260930` | `08a292bd5` | 1 |
| Game | `pub/handoff/2026-10-01/gene-world-capacity-20260930` | `42d92ea6b` | 1 |
| Game | `pub/handoff/2026-10-01/sol-native-owner-cleanup-20260930` | `0b227162a` | 1 |
| Game | `pub/handoff/2026-10-01/vk-concepts-kit-20261001` | `55b110dd3` | 2 |
| Game | `pub/handoff/2026-10-01/archived-linux-compat-20260922` | `0ab62f440` | 1 |

Each repository also has recovery snapshots named `handoff/2026-10-01/deepseek-...` for certification, encounters, enemy behaviors, gene actions, gene world, integration, inventory, layouts, menu polish, physical traversal, rewards and stage seams. The complete local fetch inventory, full commit IDs, divergence counts, and commits absent from the primary pair are in **`HANDOFF-GITHUB-INTEGRATION-2026-10-01-branches.json`**, adjacent to this document. Counts are commit ancestry counts, not proof of unique or acceptable code. Re-fetch and recompute them before merging if GitHub has moved.

The older `origin-ws/agent/linux-qt-launcher` (`6b94b78`, 65 commits absent locally) and `pub/agent/linux` (`5664a6db1`, 40 absent locally) are ancestors of the primary integration pair. Do not import them a second time. The old Claude refs are already contained in the local targets. The archived Linux compatibility snapshot needs inspection for equivalence; do not assume its different commit ID means its old WIP should override the newer port.

## What the new work contains

The primary pair adds the Linux port and Qt launcher plus a large roguelite implementation: procedural topology, room recipes and traversal, persistence, inventory/equipment, gene actions/world adapter, enemy/boss behaviors, route map, responsive HUD, menus and onboarding. Newer integration commits include native stage seams/isolation/ownership, model parts and effects tools, authored art generators and runtime art, gene-world adapter hooks, discard/deferred-export changes, inventory ownership and equipment/run-history wiring, and regression suites.

The VK concept-kit branch adds authored Blender material, greymasks and renders. The upstream handoff says these are **not exported to the engine yet**. Preserve source provenance and do not claim in-game availability.

The `release/linux-0.1.8` branch is a separate Linux public-test baseline. Its five additional commits prepare the release and fix portable runtime loading, SDL Wayland build enforcement, and i686 X11 runtime bundling. Review/import those fixes as appropriate without replacing newer Windows release metadata or pretending the release includes unfinished roguelite content. No implicit release/tag/publication.

## Known defects that must remain visible

The latest October 1 upstream review supersedes older “R2 closed” or broad completion claims. It records:

1. An actually earned/exported gene cannot be discarded durably: save validation still requires the historical exported gene to exist in the collection.
2. Legacy Restore spends an item when native healing refuses; return/readback and rollback ownership are not handled truthfully.
3. V2 Restore persists contradictory inventory and campaign supply counts instead of one transaction.
4. Run history is appended after the durable finish save and can disappear on reload.

Pending-export menus also need bounded pagination and decline confirmation. Some regression tests bypass actual menus or contain an always-true assertion. Art dependency reproducibility is incomplete. Preserve and assess the real review findings; do not erase them by adopting older worker variants.

The upstream latest review reports 251 pure/stub tests with one skipped; earlier Linux native evidence is 214/214. These are historical, source-specific results. They do not validate the merged Windows baseline. Room certification, controller traversal, enemy/boss controls, effects/region integration, audio/camera and other feature milestones remain open. Integration readiness does not mean 100/100 product completion.

## Partial graphics preflight work from this session

Before the user requested a handoff, a feature was started in an isolated workspace:

- Branch: `codex/linux-graphics`.
- Path: `worktrees/linux-graphics` under the root.
- Base/HEAD: `a30d155`, tracking `origin-ws/release/linux-0.1.8`.
- Changes are **uncommitted**, not on GitHub, and not in root `master`.

Purpose approved by the user: detect usable **32-bit Vulkan drivers** before the Linux game starts; list GPUs; support selection for mixed AMD/NVIDIA systems; explain missing dependencies by distro; retain actionable graphics startup errors. Installation stays user-controlled.

User logs are `<home>\Downloads\melee-pc.log`, `launcher-process.log`, and `crash-20261001-123023-full.log`. They show the Linux 0.1.8 game failing Vulkan adapter enumeration (“No supported adapters”), then EGL display creation, then SDL renderer initialization. The user reports a GTX 1080 Ti and RX 7900 XTX; distro/version and the exact driver setup were not confirmed. Missing/incompatible 32-bit drivers is a hypothesis, not a proven root cause. Keyboard Compose warnings and missing Target Test mods are not the fatal failure shown.

Worktree changes include:

- New `tools/release/launcher/qt/graphics.h`, `graphics.cpp`, `graphics_tests.cpp`: report parsing, selection environment, distro help, startup log classification, and tests.
- Existing `launcher_core.cpp`, `window.cpp`, `window.h`, `CMakeLists.txt`: asynchronous preflight, timeout and logs, diagnostics/GPU controls, graphics-specific game errors, selection propagation and test wiring.
- New `tools/port/graphics_probe.c`, `build_graphics_probe.sh`: standalone i686 Vulkan loader/device/graphics-queue/swapchain check, with JSON output; no Qt or disc required.
- `tools/release/build_launcher.sh`, `tools/port/package_linux.py`: build and package the helper, verify ELF32, retain existing glibc auditing.
- `tools/release/build_launcher.ps1`: optional generator parameter because this machine has VS 18/2026, while the script defaults to VS 17/2022.
- `.github/workflows/launcher-qt.yml`: 32-bit test dependencies and intended helper integration-test call.
- New `tools/release/test_graphics_wsl.sh`: session-specific Linux verification wrapper copying the source to `/tmp/gd-linux-graphics-test` because CMake RCC/Ninja mishandles the apostrophe in the Windows root path.

**Incomplete and must be reviewed before landing:**

- The CI step references `tools/port/test_graphics_probe.py`, which has **not been written**. Do not merge the CI change as-is.
- The C helper has not yet been compiled/run. Missing-loader, no-device, device-creation failure, healthy-driver and wrong-architecture checks remain to be implemented/run.
- The final Linux UI compiled and both Qt test targets passed, but no UI render/manual preflight flow was inspected. English-only detailed graphics strings need a localization decision; labels have Spanish translations.
- Native Windows verification failed before compilation due to duplicated case-insensitive environment keys in MSBuild (`MSB6001`, Hashtable duplicate key). CMake's “No CMAKE_CXX_COMPILER” headline is secondary. Normalize child environment keys without changing global machine settings, then retry the Windows build.
- Startup fallback, helper absence, timeout, ignored GPU selection, environment propagation, missing devices, stale saved GPU choices and packaging need end-to-end checks. A successful helper probe does not prove Dawn renderer compatibility or presentation.
- GPU selection uses Mesa `DRI_PRIME`/device-select and NVIDIA Optimus variables. It re-probes to verify isolation before claiming success. Review behavior with inherited explicit ICD selections and multiple same-vendor devices; the current report identifies vendor/device pairs rather than individual PCI addresses.
- Direct CLI `launch-melee` preflight has not been wired. Decide/document whether this feature is launcher-only or should cover direct launch too.

Verification already performed for this WIP:

- Existing Linux launcher baseline passed before production edits.
- Four new behavior tests were observed failing against placeholders, then passing with the implementation.
- Latest WSL Qt build: both `launcher_core` and `launcher_graphics` CTest targets passed (Debian 13, Qt 6.8.2). Build and full test logs are in `/tmp/gd-linux-graphics-test/build`; only the existing launcher result was copied to the worktree `_build/graphics-test/launcher-tests.txt`.
- No Windows launcher test, game build, game run, helper test, release package, or GPU hardware test passed in this session.

Workspace-local downloaded tools, excluded from staging: `_build/graphics-build-tools` (aqtinstall/CMake/Ninja), `_build/qt-sdk/6.8.3/msvc2022_64`. Build output is `_build/launcher-qt-windows`. Debian WSL has Qt/CMake and multilib Vulkan development/runtime test dependencies installed with approval. Those WSL results are not Windows results or Ubuntu 22.04 portability evidence.

Windows retry should use the repo's `tools/release/build_launcher.ps1`, the downloaded QtRoot, and `-Generator 'Visual Studio 18 2026'`. Add workspace-local `_build/graphics-build-tools/cmake/data/bin` to the child PATH. The system execution policy requires an appropriate process-local script invocation (the previous attempt used `powershell -NoProfile -ExecutionPolicy Bypass -File ...`). Do not change global execution policy.

## Recommended integration sequence

1. Read `AGENTS.md`, `docs/NEXT-SESSION.md`, `docs/HANDOFF.md` sections 6–7, and per-directory guidance. Re-inspect local statuses, remote refs and all proposed branch differences. Preserve local Slippi work and this WIP first.
2. Create separate integration workspaces based on the **local** `master` and `pc-port` tips. Use separate build roots/run directories, explicit `GW_MELEE`, and the repo's build/run scripts. Do not repoint or reuse an old lane blindly.
3. Merge the primary incoming workspace/game pair coherently. Resolve native/Lua/tooling conflicts with source review; avoid wholesale ours/theirs for `gw_script.c`, adapters, ownership hooks, or room/persistence code. Keep gene-world adapter and compatible action hooks together. Regenerate the bridge from the final Windows map through `build.sh`.
4. Compare every recovery snapshot with the primary pair and merged local baseline. Import unique, appropriate changes; preserve duplicate, obsolete or unreviewed recovery material with an explicit disposition. Account for all refs rather than deleting or merging all snapshots indiscriminately. Review root snapshots and VK source/assets separately.
5. Bring across the five Linux release fixes with appropriate release metadata handling. Finish/review the graphics WIP in its branch or transplant its reviewed source changes into the consolidated launcher. Keep Linux and Windows requirements distinct.
6. Repair build/test paths as needed: some roguelite tooling hardcodes `melee/worktrees/linux`. Set `GW_MELEE` where supported and fix/configure actual-source test paths instead of accidentally testing a different checkout. The upstream handoff proposes a nested game worktree for fresh checkouts; this machine already has a separate parent game repo and many lanes, so adapt deliberately.
7. Run the integrated pure/stub suites, relevant native actual-source checks, Qt launcher tests/builds, and **Windows** game build/bridge ABI/headless tests. Use the scripts documented in each incoming tool README, not guessed commands. Inspect failing run logs. Verify changed runtime menus/rooms in the game where required and record any hardware/certification gaps.
8. Audit staged source/art for disc-derived data and generated output. Record final commit IDs and validation. Advance local `master`/`pc-port` to the reviewed integrated commits, restoring preserved user work. Do not push/tag/release unless separately requested. Leave a clear ledger of any branch content not accepted and why; do not claim “everything caught up” if unique required work was silently omitted.

The suite command recorded upstream is `python -m unittest discover -s tools/roguelite -p 'test_*.py'`, but verify its source-checkout assumptions before treating its result as evidence. Build and run Windows gameplay using `tools/port/build.sh` and `tools/port/run.sh`, with the correct game/build roots and local disc configuration. Neither a historical green log nor a stale copied EXE validates the new main.

## Suggested prompt to assign the next model

> Read `docs/HANDOFF-GITHUB-INTEGRATION-2026-10-01.md` and its branch inventory. Bring the reviewed GitHub work and local commits together into workspace master and game pc-port, preserving all current local work. Account for every recovery snapshot without blindly merging copied or unreviewed variants. Finish and verify the partial graphics-preflight work, use the Windows build path for the Windows baseline, and report the remaining roguelite defects honestly. Do not publish a release or discard user changes. The desired outcome is an integrated, verified baseline ready for new work.
