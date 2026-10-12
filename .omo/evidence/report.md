# Leftover branch disposition - 2026-10-11

Status: audit complete; LAND verified and committed. This dated report supersedes the rc3 unmerged-branch inventory for these refs.

Recovery audit complete after the owner reported a BSOD. The pre-crash CPU run stopped at frame 2806 without a completion marker or exit verdict; the checker rejects it, and it is excluded from passing evidence. All seven selected files and the saved EXE/map match their pre-crash hashes. Read and hashed 148,979 lane-written files (4,146,768,161 bytes), compared 136,396 copies with originals, and checked the structure/bounds of 3,501 binaries. No damaged source or build objects found. The one copy difference is intentional enabled-mod order (same four mods). Zero-length compiler temporary files also exist in the original baseline; other empty files are expected fixtures, markers, no-import tables and diagnostics. The all-zero zlib fixture matches its original. Two all-zero SQLite shared-memory files were stale transient state: copied database/WAL pairs both passed integrity_check after regenerating shared memory. Removed only those two owned transient files and the interrupted run's empty active-run marker. Both Git index locks and all Ninja locks are absent; Ninja log/dependency records parse completely. All 51 private reparse targets stay inside owned worktrees. Details: recovery-audit.json, recovery-file-manifest.json, recovery-verdict.json, recovery-cache-checks.json, recovery-locks.json and recovery-ninja.json. Validated objects were reused for the successful post-crash rebuild; no clean rebuild was needed. Test reruns are in progress.

Workspace: `worktrees/stalebr`, `ws/stale-branches`, base `7df47db9a50c5155de6d3115f95c1ff70bc85dae`. Game: `worktrees/stalebr-game`, `agent/stale-branches`, base `0a0c13111e3627068865596efb47de2ef32a862d`.

All 28 packet refs: 1 LAND, 27 RETIRE. RETIRE means the integrator can delete the listed branch after preserving anything they want; no branch was deleted or pushed. Other current lanes are outside this packet.

| Repository / branch | Verdict | Evidence against starting integration | Commit |
|---|---|---|---|
| workspace: `ws/wb-attributes` | **RETIRE** | Only unique commit 58176d4 is patch-equivalent to integration 2e82210; commands_attributes.cpp is byte-identical. | `2e82210` |
| workspace: `ws/modsync-breakaway` | **RETIRE** | Only unique commit eb2c306 adds two lines enabling supervisor job breakaway. Repository search finds no consumer of GW_RUNS_BREAKAWAY. Abandon this unused ownership escape; keep supervised runs owned. | `none (abandoned)` |
| workspace: `ws/research-stage-builder` | **RETIRE** | Only unique commit e16476e is explicitly WIP. The note says loop-to-terrain/cliff classifier, collision layers, save format and sharing limits are owed; no tested implementation. Retire incomplete research from the integration queue; branch preserves it. | `none (incomplete WIP)` |
| workspace: `ws/luigi-ult-grab` | **RETIRE** | cbc24af records the owner-deprecated adaptation; owner packet says do not revive. The only permitted salvage, article show_model, belongs to the game and is already integrated by d2a2e78e6. | `cbc24af; game d2a2e78e6` |
| workspace: `ws/goku-mobility` | **RETIRE** | 65508c7 explicitly salvaged the bench/table/options without the gameplay.json stopgap. Four tooling files are byte-identical; remaining aerial_friction=0.0156 override was deliberately omitted. Preserve that choice. | `65508c7` |
| game: `agent/charlie_slippi` | **RETIRE** | Both unique SHAs are patch-equivalent to integrated ENet vendoring and Slippi Direct ticket matcher; current matcher has later validation. | `f225f9b9c; 02f193e65` |
| game: `agent/envoynet` | **RETIRE** | The old gw_modeval/MeEval evaluator is superseded by integrated native Envoy stage 4 (script_mods_core.h, simulation callbacks, rollback storage and hash); merging the old evaluator would duplicate the replaced architecture. | `f84fef537; 6c370ca99; ac9aa767a` |
| game: `agent/geno-workbench-data` | **RETIRE** | ScriptGame_WbPrepare and its workbench call already landed in ee3807daa. d7f41b045 also calls it before LAB preview changes motion; source restores Entry scale before clearing Entry callbacks. Original branch even has a malformed newline in OSReport. | `ee3807daa; d7f41b045` |
| game: `agent/loadscreen-hold` | **RETIRE** | WIP a024d9bad was superseded by the tested loading hold implementation, which freezes match/procs and waits on what is drawn, followed by rollback-clock and pipeline-prewarm fixes. | `159dd6fd8; d239f72f9; 57123723e` |
| game: `agent/luigi-ult-grab` | **RETIRE** | Owner deprecated the Luigi work. show_model commit e9342cc27 is patch-equivalent to integrated d2a2e78e6. Remaining grab/clips/accessory work is not revived. | `d2a2e78e6` |
| game: `agent/native-overlay` | **RETIRE** | DevText overlay commit 926831d8e is patch-equivalent to integrated 759341ebc, with later overlay corrections. The only unique remainder e51d908de labels its broad immediate-mode primitive changes UNPROVEN; retire that abandoned experiment. | `759341ebc; 9271219a1; 699a48b9b` |
| game: `agent/throw-banks-rollback` | **LAND** | Unique rewind/eviction/resident-bank Lua cases, input-free five-CPU SyncTest and dated rollback note remain useful. Squash merge excludes tracked .omo handoff and experimental pad-read diagnostic. Harden runner verdicts and prove on this lane. | game commit (agent/stale-branches HEAD) |
| game: `agent/xplat-hash` | **RETIRE** | 218ac4e8d is patch-equivalent to integrated 754fa3003 (merge 8ebfb7241). Hash implementation, detail dump, comparison tool and tests are byte-identical. Only additional commit is generated bridge churn, which must not be committed here. | `754fa3003; 8ebfb7241` |
| game: `codex/4sora-perf` | **RETIRE** | Tip 4c676892a is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `4c676892a (already ancestral)` |
| game: `codex/envoynet4` | **RETIRE** | Extends the obsolete MeEval evaluator/EV2 protocol experiment. Integrated Envoy stage 4 uses script_mods_core.h and existing native build agreement instead; its replacement is already in the integration base. | `f84fef537; 6c370ca99; ac9aa767a` |
| game: `codex/frame-arena` | **RETIRE** | Tip 6f582919f is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `6f582919f (already ancestral)` |
| game: `codex/gamemode-kit2` | **RETIRE** | Tip db95884f6 is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `db95884f6 (already ancestral)` |
| game: `codex/lua-tests` | **RETIRE** | Tip 85ff40ba4 is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `85ff40ba4 (already ancestral)` |
| game: `codex/map-editor` | **RETIRE** | Tip db95884f6 is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `db95884f6 (already ancestral)` |
| game: `codex/menu-migrate` | **RETIRE** | Tip db95884f6 is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `db95884f6 (already ancestral)` |
| game: `codex/menu-parametric` | **RETIRE** | Tip fd26f6927 is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `fd26f6927 (already ancestral)` |
| game: `codex/model-api` | **RETIRE** | WIP model API content landed as 62223b8f2; lighting/glow change is patch-equivalent to 3976206bf and authored model assets are identical. Current API separates spawned models from collision platforms: gd.stage_add_model attaches an existing floor via platform=handle. | `62223b8f2; 3976206bf` |
| game: `codex/model-gaps` | **RETIRE** | Tip 6f0753d8a is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `6f0753d8a (already ancestral)` |
| game: `codex/platform-model` | **RETIRE** | Platform model/light content landed as 62223b8f2/3976206bf. Interior room content landed in adapted form as 74e8f5e3d on the runtime model API (part-frame meshes, v1 collision sidecars, 41 parts). Do not regress to the branch's old model/platform coupling. | `62223b8f2; 3976206bf; 74e8f5e3d` |
| game: `codex/results-pools` | **RETIRE** | Tip fd26f6927 is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `fd26f6927 (already ancestral)` |
| game: `codex/slippi-fixes` | **RETIRE** | Tip 2f0c10430 is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `2f0c10430 (already ancestral)` |
| game: `codex/slippi-refresh` | **RETIRE** | Tip fd26f6927 is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `fd26f6927 (already ancestral)` |
| game: `codex/texupdate` | **RETIRE** | Tip 21adda748 is an ancestor of game integration base 0a0c13111 (merge-base --is-ancestor exit 0); log base..branch is empty. Already landed, nothing to merge. | `21adda748 (already ancestral)` |

## Method and review

Read-only `git log BASE..BRANCH`, `git diff BASE...BRANCH`, `git cherry BASE BRANCH`, per-file equality and integrated history. Raw inventory is `inventory.json`; full decisions are `dispositions.json`. An unmerged SHA is not proof that its content is absent.

The throw-bank squash conflict was only the branch's tracked `.omo/evidence/handoff.md`; retained the current base file and excluded it from the commit. Experimental `pc/platform/gw_script_pad.c` changes were also excluded. The tests initially masked game failures through shell pipelines; fixture tests demonstrated 14 failures and 2 passes before verdict hardening, then 16 passes. Invalid scripted SyncTest diagnostic mode was removed; case C explicitly overwrites Fox with Falcon before both restores.

Fresh read-only review confirmed the retirement choices and test-only scope, with two Important verdict findings, both fixed: immediate late mismatch detection and conditional eviction for three-arena CPU runs. Their regression fixtures failed first (2 failed/16 passed), then the runner and existing hash-detail checks passed (25 passed). No Critical or Minor findings.

The first real rewind run printed 4/4 while logging repeated teleport failures: fighters parked outside Final Destination's floor could die or enter respawn states. That run (`stalebr-tbr1`) is rejected as proof. The fixture reproducing this false positive failed first, then passed after the checker rejected setup failures; the Lua now parks fighters over the floor and aborts failed teleports. Final runner plus hash-detail checks: 26 passed (`runners-final.log`).

## Verification

Workspace Python tools: 479 passed, 6 skipped, 183 subtests passed (`pytest-tools.log`). Launcher: configuration and Release build succeeded; offscreen CTest passed all 48 tests (`launcher-ctest.log`). Private game build succeeded: bridge fixed point after 2 links, all 18,830 functions resolved, 0 ABI failures; source provenance verified. Headless suite: TESTS pass=397 fail=0 total=397, exit 0 (`stalebr-native`). One-arena and three-arena rewind each passed cases A/B/C/D, DONE 4/4, and the checker, exit 0 (`stalebr-tbr1-good`, `stalebr-tbr3-good`). Their complete case/pose-hash traces are identical (`throw-budget-comparison.json`). Observed log events: 23 loads/21 evictions with one arena; 10 loads/0 evictions with three. These counts include replayed loads, not unique logical events. Pending: the input-free CPU SyncTest.

The deterministic generic run parser labels the headless suite `pass` and the two rewind runs `clean_no_verdict`, because it does not recognize TBR lines. `check_throw_banks.py` provides their complete case verdicts; generic parser facts still establish exit 0, loaded expected mods and no fault evidence. Native-suite define-refused messages are deliberate invalid-input tests, with the enclosing 397/0 suite result. Initial CPU attempt `stalebr-cpu1` was explicitly reaped through the verified lane owner and sandbox selectors (exit 125), because the chosen 300-second timeout was too short for 3,000 frames of 12-frame re-simulation; it is excluded. Replacement `stalebr-cpu1-good` uses the runner's 1,500-second timeout.

Evidence logs live beside this report; each actual game log is in `../build/game/runs/<name>/melee-pc.log`, with `exit.json` and `run.json`. Build roots are `.omo/build/launcher` and `.omo/build/game`. Private build inputs/objects are copies, not hardlinks. Shared `_build/ax86m` is not used; dependency source cache is read from shared `_build/ax86/_deps` and copied before CMake.

Build setup supplied the two existing generated font includes via a private `stalebr-game/.omo/build/inputs` directory and local ignored `build/` junction; these generated inputs are not committed. Native runtime DLLs were copied from the installed x86 MSVC CRT into the private build. No installer or package deployment was run.

## Reproduction and scope

Dot-source `lane-env.ps1` in PowerShell. It selects both owned worktrees and private outputs, puts temporary files under `.omo/build/tmp`, and sets the game's offscreen coordinates, volume 0, turbo, loopback bind, deterministic seed and owner. All runs are serial. The launcher uses `QT_QPA_PLATFORM=offscreen`.

```powershell
python -m pytest tools/port tools/jev tools/release -q --basetemp .omo/build/pytest-tools -p no:cacheprovider
python -m pytest ../stalebr-game/pc/tests/test_throw_banks_runners.py ../stalebr-game/pc/tests/test_compare_rb_hash_detail.py -q --basetemp .omo/build/pytest-runners -p no:cacheprovider
cmake -S tools/release/launcher/qt -B .omo/build/launcher -G "Visual Studio 18 2026" -A x64 -DCMAKE_PREFIX_PATH=E:/Projects/Qt/6.8.3/msvc2022_64 -DBUILD_TESTING=ON -DLAUNCHER_DEPLOY_QT=OFF
cmake --build .omo/build/launcher --config Release --parallel 4
ctest --test-dir .omo/build/launcher -C Release --output-on-failure
bash tools/port/build.sh
# Use an empty private mods directory for the native suite.
$env:MELEE_MODS_DIR = "$env:GW_BUILD_ROOT/empty-mods"
bash tools/port/run.sh --test --max-seconds 300 stalebr-native
$env:MELEE_MODS_DIR = "$env:GW_BUILD_ROOT/mods"
$env:MELEE_THROW_BANKS = '1'
bash ../stalebr-game/pc/tests/run_throw_banks_rewind.sh stalebr-tbr1-good
$env:MELEE_THROW_BANKS = '3'
bash ../stalebr-game/pc/tests/run_throw_banks_rewind.sh stalebr-tbr3-good
$env:TBR_TIMEOUT = '1500'
bash ../stalebr-game/pc/tests/run_throw_banks_cpu_synctest.sh stalebr-cpu1-good 3000 1
```

The CPU proof uses one arena; the three-arena budget has real rewind coverage and runner fixtures. The packet's single-process restriction precludes a fresh two-client netplay check. No fresh cross-platform run or visual judgment is claimed. The only selected changes are the rollback note, two Lua scenarios, two shell runners, a verdict checker and its fixtures. No game runtime code, generated bridge, disc-derived assets or `.omo` files are selected. All workspace leftovers are already represented or retired, so the workspace branch needs no source commit; the requested report remains in ignored `.omo/evidence`.


## Final CPU proof (2026-10-11, after BSOD recovery)

`run_throw_banks_cpu_synctest.sh stalebr-cpu1-final 3000 1`: loads 26, evictions 13, curated hash 37200 compared 0 mismatching, `TBC DONE frames=3000`, `throw banks: cpu PASS`, exit 0 (`final-cpu1.log`). One-arena and three-arena rewind 4/4 each (`recovery-rewind1/3.log`). Branches are listed for deletion by the integrator; none deleted.
