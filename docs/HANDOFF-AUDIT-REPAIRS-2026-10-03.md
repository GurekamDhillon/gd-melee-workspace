# Project audit repair handoff

> **Later the same day:** everything after the audit repairs (missions, shaders, menus, engine batch 2, Envoy groundwork) is in `HANDOFF-2026-10-03-ENGINE-DAY.md`, which supersedes this file's "What is left".


**Resumed and re-verified later on 2026-10-03.** This is the current repair state and
supersedes earlier progress messages for this audit. The measured results of the resume are in
the repair ledger, [2026-10-03-audit-repairs.md](superpowers/plans/2026-10-03-audit-repairs.md),
under "2026-10-03 resume"; that section wins wherever the component notes below still say
"not run" or "not accepted". It does not supersede the gameplay requirements in
[ENVOY-PROBLEMS-2026-10-02.md](ENVOY-PROBLEMS-2026-10-02.md).

State in one paragraph: the integrated game build, bridge fixpoint, ABI audit and provenance
stamp pass; the native suite is 218/218 on the stamped exe (ACE disc); the launcher package
builds, deploys, passes its SDK-free smoke and the release guard on its real bytes; the native
spawn regression and the Envoy snapshot error state are repaired with red-then-green tests.
**SuperTime Envoy is not accepted and the owner now expects to rebuild it from scratch**; do not
finish it by patching. A mission layer was added to the kit map editor instead and completed its
sample mission in the real engine. Nothing was committed, published, pushed, or changed on a
live service.

## Preserve the workspace

Both repositories were already heavily dirty. Do not reset them or attribute the
whole Git diff to this repair pass. The repair baseline is saved under
`_build/audit-20261003/repair-baseline/`, including changed-file copies, patches and
status inventories for the workspace and game checkout.

- Workspace baseline HEAD: `d528d0281d76c4f674447af0288a734faa3572ae`.
- Game baseline HEAD: `378d79b20c46452cf43aec45c2d622471ed3a5e6`.
- The game checkout is `melee`; `GW_MELEE` selects an alternative.
- Repair ledger: [2026-10-03-audit-repairs.md](superpowers/plans/2026-10-03-audit-repairs.md).
- Local detailed evidence under `_build/audit-20261003/`:
  `repair-root-report.md`, `repair-ports-report.md`, `repair-envoy-report.md`, and
  `repair-release-report.md`.
- The baseline and evidence directories contain local build material. Do not
  stage `_build` or disc-derived/generated fighter content.

## Shared runtime and tooling

Root implemented these changes and observed the focused regressions fail before
repair and pass afterwards where indicated in the detailed report:

- `melee/pc/platform/gw_script.c`: refuse all Lua gameplay writes during online or
  rollback sessions, including manifests declaring `rollback_safe`. Those writes
  are not replayed; this closes the unsafe exception. Metadata/hash compatibility
  remains. `resume` uses the same permission gate. Public scripting docs and the
  native header/platform instructions match the policy.
- Geno hot reload: negative registry results report failure and retain paused old
  state; script reload errors no longer report success. Scheduling is LAB-only,
  and execution rechecks LAB/match eligibility before mutating the registry.
- `tools/port/native_test.sh`, `script_policy_fixture.py`, and
  `melee/pc/tests/script_policy_test.c`: an actual-source standalone permission
  and reload test, invoked through `build.sh --native-test script-policy`.
- ENet compilation uses content keys for compiler identity, flags, headers and
  source. Atomic replacement protects objects hardlinked from another lane.
- Game/shim content selection rebuilds objects missing a dependency record or
  key. `FileCache` shares reads only within a pass; it freshly hashes input bytes
  on each new pass. The previous size/mtime cache missed equal-length edits with
  restored timestamps. These two gaps were caught in cross-review before a full
  provenance-stamped build. Five added/updated regressions failed before repair;
  all 23 build-speed tests now pass. The legacy timestamp comparison command
  remains available separately.
- `build_provenance.py` and `build.sh`: bind game source content, commit, protocol,
  final EXE and map hashes. A pre/post source token rejects edits during the build;
  generated bridge files are omitted from the token but included in the final
  digest. Release packaging verifies the stamp. No current repair EXE has been
  stamped yet.
- `prune_runs.py` and `run.sh`: preserve live, unknown, unstamped and active-marker
  sandboxes; runner and pruner use the same atomic `.active-run` claim. A stale
  marker requires another run name or deliberate inspection, not blind removal.
- Crash sweep samples logic and presentation progress during its observation
  window and latches stalls over ten seconds. An early 600-frame burst followed
  by a freeze can no longer pass.
- Fixed the live acceptance import-order NameError and effects/model-parts
  checkout/build roots. The final effects showcase/capture edits have not had a
  fresh test run; rerun their suites and review their Windows wrapper path.
- Fixed the native Slippi rollback fixture's missing scene callback. The real
  UDP relay stall regression now uses an explicit clock instead of a Windows
  sleep-timing assumption. Linux-only probes do not execute during Windows test
  discovery. Stale-scan comparison selects Git Bash instead of WSL's launcher.

## Fighter conversion and Geno

The ports agent implemented corrected motion-rate clocks, stable same-frame
command order, rejection of unknown ACMD predicates, payload-bound moveset audit
provenance, article hitbox slot allocation and rejection of unsupported nonzero
rehit. Article reflection applies the reflector speed multiplier to stored travel
velocity. Registry reload forces restart for article count/name/order or overlay
offset/length changes; malformed data still preserves old state.

Actual registry and article callback native fixtures passed in the parent process.
Permanent production tests were added, and `geno_game.c`/`geno_tests.c` passed PPC
syntax checks with existing typedef warnings. `GenoArtVars` moved to the shared
game state header without changing its layout.

The final frame-zero same-ID capsule-to-sphere replacement fix removes obsolete
samples instead of assigning end-frame zero, which means forever. Its regression
failed with five live entries before repair and passes with one afterwards. The
final IR suite ran 148 tests successfully with five skips; 14 repair regressions
passed. Existing installed Sora outputs
have **not** been regenerated; source fixes do not update those outputs. The
stricter installer intentionally rejects old or altered moveset provenance.

## Envoy and map editor

The Envoy agent implemented starter-state persistence, actionable storage-error
menus, idempotent dead-enemy cleanup, durable checkpoint recovery after savestate
loads, paginated pending rewards and explicit decline confirmation, editor
bounds/spawn restoration, and restored placement-ghost tracking. Ten focused
integrity regressions passed.

Native arena spawn editing now converts world coordinates to parent-local
coordinates and restores the original local transform. The changed native
function returns success/failure, and both native/Lua bridge call sites were
updated. **The standalone actual-source spawn fixture still needs updating and
running**; the old `arena_actual.c` asserts the original bug and is not a green
test for the repair.

Generation 5 is now the default via new `physical_campaign.lua`, with seven
physical rooms/eight nodes, encounters, rewards, rest and a champion finish;
generation 3/4 remain frozen for old saves. Root rejected the first geometry pass
because it reused a mirrored staircase layout. The replacement is syntactically
coherent and has three passing campaign tests, including 100 seeds and a bundled
lifecycle under engine doubles. It still needs independent geometry review,
collision/camera validation and real traversal. A door graph or mocked lifecycle
does not establish the user's requested spatial campaign.

The final broad Envoy suite ran 287 tests successfully with one skip; the existing
editor Lua test passed. Two concrete follow-ups remain beyond native acceptance:
the diversity test still checks pattern labels rather than structural topology,
and `on_loadstate` overwrites `load_data`'s error menu with `collection` when all
durable slots are invalid/future. Preserve that loader error state with a new
regression. Also exercise saved-v5 resume, the detour and failure/retry boundaries.

## Launcher and release

The release agent fixed random-match retries, room membership cleanup, bounded
queue behavior, enabled-list parsing/comment behavior and dependency cycles.
It added mandatory build provenance checks and package guards for essential
files, provenance and personal-path leakage. Public launcher claims now describe
the implemented local-mod flow; Remove is implemented and retained. README art
source and launcher feature images were changed from "Mods browser" to "Local mods".

The real Qt configure/build/CTest path passed. Deployment then exposed a series
of Windows issues: nested `vswhere` JSON handling, a CMake deploy path containing
spaces, PowerShell 5.1 treating native stderr warnings as terminating errors,
native exit-code propagation, and a blank `Process.ExitCode` despite version
output. The final package run has **not** been accepted.

There is a further concrete packaging blocker: official copied Qt DLLs are
Authenticode-signed and contain vendor personal build paths. The sanitizer
correctly refuses to alter signed images by default. Final source edits now use
an explicit copied-Qt-only signature removal/redaction path, clear the affected PE
checksum, disclose the change in `qt-build.txt`, capture native status separately,
and run bounded Python deployment smoke via `verify_launcher_runtime.py`. These
last integration edits have **not been rerun together**. SDK originals and
Microsoft CRT signatures must remain untouched. A successful CTest result is
not proof that sanitization, deployment smoke or the strict package guard passed.

## Recorded verification

Counts below are the last completed results, not claims of end-to-end acceptance.
Check agent reports for final handoff additions.

| Check | Result |
|---|---|
| `tools/port` Python discovery | 42 tests OK, 5 Linux-only skips |
| Build-speed subset | 23 passed, including both cross-review fixes |
| `tools/slippi` | 49 passed |
| `tools/replay` | 7 passed |
| `tools/sweep` | 4 passed |
| Effects and model-parts prepare suites | 4 and 11 passed; later capture/showcase edits not rerun |
| Native wrapper targets | 9 passed: slippi-pad, fixture, rb, mode, wire, peer, match, window-drag, script-policy |
| Final IR suite and repair subset | 148 tests OK, 5 skips; 14 repair regressions passed |
| Kirby converter and animation suites | 46 and 9 passed |
| Actual registry/article callback fixtures | Both passed in parent |
| Qt launcher core tests | Parent 12/12 passed; CTest 2/2 passed during deployment build |
| Matchmaking server | Agent reported 14/14 passed |
| Release guard and sanitizer | Agent reported 9 guard tests and 5 sanitizer tests passed; final integrated packaging edits not rerun |
| Final Envoy suite and focused tests | 287 tests OK, 1 skip; integrity 10 and campaign 3 passed |
| Existing editor Lua fixture | Passed |
| Both repositories `git diff --check` | Passed at handoff, line-ending notices only |

A read-only game content scan at handoff completed in 17.35 seconds and selected
three stale translation units: `pc/gameworld/script_game.c`, `pc/geno/geno_game.c`
and `pc/geno/geno_tests.c`. This was not a compile. Shims and final linking are
still outstanding. No game or compiler process was running in the parent inventory.

## What is left

The ledger's two "2026-10-03" sections hold the measured results; this list is what remains.

1. **Envoy**: a design conversation with the owner before any rewrite; do not patch the current
   campaign. The mission layer in the kit map editor is the candidate foundation.
2. **Sora** (combined mod: `_build/audit-20261003/sora-final/mods`, recipe `regen.sh` there): the
   owner's play test of feel and looks. Still unported: nair/fair hits 2-3 (design in
   `_build/audit-20261003/sora-normals/aerial-chain-design.md`), the jab hit-confirm rule, the
   Sonic Blade aim cursor and lock marker (needs an effect attached to another fighter), ledge
   grabs during a dash, Thundaga cloud placement, counter lunge scaling and rebound, the
   four-slot hitbox drops. `melee/docs/geno.md` 19.8 (the magic table) is stale. Loss entries
   with `approved_by: null` await the owner's review. The working baseline mod was not replaced.
3. **Mission layer**: nothing visual was judged (overlay, HUD, banner); the real mouse was not
   driven; `complete`/`fail` triggers and three enemy kinds are stub-tested only. Engine wishes:
   a Koopa kicked into its shell reports as removed, and rebirth always uses the platform.
4. **Release**: the bundle passes the guard non-strict. A publishable build needs both trees
   committed and `-Strict`.
5. Both trees are still uncommitted.

Useful local commands from the workspace PowerShell prompt:

```powershell
$env:GW_JOBS = '4'
& 'C:/Program Files/Git/bin/bash.exe' tools/port/build.sh
python tools/port/build_provenance.py --melee melee --build _build --verify
python -m unittest discover -s tools/port -p 'test_*.py'
python -m unittest discover -s tools/roguelite -p 'test_*.py'
python -m unittest discover -s ports/ir/tools -p 'test_*.py'
python tools/roguelite/prepare.py --app-dir _build/audit-20261003/envoy-acceptance --enable --demo
```

The Envoy preparation command is a next step, not a recorded completed install.
Set both `MELEE_MODS_DIR` and `MELEE_SCRIPT_DATA_DIR` to that isolated app directory
when launching it through `run.sh --realtime <new-name>`.

For the launcher use the known local tools, then inspect the complete output:

```powershell
& './tools/release/build_launcher.ps1' `
  -Out '_build/audit-20261003/further-release/repaired-package/GD Melee.exe' `
  -BuildDir '_build/audit-20261003/further-release/qt-package-build' `
  -QtRoot 'E:/Projects/Qt/6.8.3/msvc2022_64' `
  -CMake 'E:/Projects/gdm-build-tools/cmake/data/bin/cmake.exe'
```

The machine uses Visual Studio 18 2026. Qt tests and their child process require
the matching Qt bin and latest VS x64 CRT on PATH; the deployed smoke deliberately
removes SDK/toolset PATH entries to test the package itself. Logs and intermediate
package files are under `_build/audit-20261003/further-release/`.
