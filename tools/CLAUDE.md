# tools/: how the game is built, run, tested, packaged and shipped

Each subdirectory has a README that is its reference. This file says which tool to reach for and
the rules that cross them.

| dir | reach for it when | reference |
|---|---|---|
| `port/` | building (`build.sh`), running (`run.sh`), a second agent (`agent_new.sh`), a fresh machine (`bootstrap.sh`), profiling (`prof_report.py`) | `port/README.md`; script headers; `melee/pc/docs/PORT_DEV_QUICKREF.md` |
| `release/` | a public release, the launcher, the user README, the crash upload server | `release/README.md`; notes in `release/notes/<version>.md`, the version in `release/VERSION` |
| `netplay/` | the matchmaking server, the friends zip (`make_package.ps1`), `HOW TO PLAY ONLINE.txt` | `netplay/server/README.md` |
| `sweep/` | which stages and fighters crash on each disc (`crash_sweep.py --plan` first) | its docstring |
| `replay/` | `.slp` playback, parity against the GameCube (`replay_compare.py`, `first_div.py`) | `replay/README.md` |
| `mex_port/` | reading m-ex's data and patches, the bridge signatures, the ABI audits | `mex_port/README.md` (the attribution rule is there: consult m-ex, never copy it) |
| `mods_browser/` | the mod index format the launcher reads | `gdmelee-mods.schema.json` |
| `blender/` | Target Test stage round-trips | `blender/README.md` |
| `geno/artist/` | an original fighter from Blender to a playable `base: "none"` define: starter, validator, importer, one-command build | `geno/artist/README.md`; rules in `docs/geno-artist-spec.md` |
| `skins/` | making, importing or linting a skin mod (costume packs), a synthetic test pack, a one-window screenshot of a scene | `skins/README.md`; format in `docs/mods-packaging.md` 4b |
| `gc_extract.py` | assets out of a disc, locally only | |

## Rules

- **Jev (TypeSafe System One), v2:** parse run facts in code first, ask the model only narrow questions. `jev/runparse.py RUN_DIR`
  (PASS/FAIL, timeout, setup/harness signatures, faults; no key, no model), `jev/triage_run.py` (runparse, then a narrow
  confidence-gated Choice on a crash signature only), `jev/coverage.py BRIEF REPORT` (done/owed/unaddressed per requirement),
  `jev/check_claims.py`. Always read the `band`: `human` means do not trust it; thresholds in `jev/confidence.py` are uncalibrated
  defaults. `--offline` stubs are fixtures, not Jev. Details and how lanes call them: `jev/README.md`.

- **Scripts, not raw commands.** `build.sh` exists for the bridge fixpoint; `run.sh` for the
  sandbox per run. A raw clang or a bare exe run repeats the mistakes those scripts encode.
- **Everything is relative to `GW_ROOT`** (`port/portlib.sh`), with the disc images from `.env`.
  `build.sh` builds Aurora inside `GW_BUILD_ROOT`; the old bootstrap batch uses
  the explicit `GW_AURORA_ROOT` junction (see `move_workspace.md`).
- **Two agents, two build roots** (`GW_BUILD_ROOT`). Test runs (`--test`) parallelise; gameplay
  runs share audio and the screen. Baseline game objects are hardlinked by `agent_new.sh`;
  check the local output writer before treating build roots as isolated. Aurora outputs
  and copied dependency sources are private to the build root.
- **Timing:** `run.sh --test` requests turbo; `--realtime` (before the sandbox name) clears it.
  Headless tests have no paced frame loop. `MELEE_FPS=u` uncaps presentation; `MELEE_TURBO=1`
  accelerates scripted/LAB batch logic. `GW_JOBS` sets compile jobs; stale objects are chosen by content hash (tools/port/README.md).
- **Disk hygiene (E: filled to 0 once).** `run.sh` prunes its build root's `runs/` (newest `MELEE_RUNS_KEEP`=40
  kept, exe copies stripped past the newest 10, running games never touched); `run.sh`, `build.sh` and
  `crash_sweep.py` refuse below `MELEE_MIN_FREE_GB`=20 free unless `--allow-low-disk`. At lane end run
  `python tools/port/agent_slim.py <name> --yes` (or `agent_rm.sh`) and `git worktree remove` merged
  worktrees. `python tools/port/disk_report.py` shows what is big and what to clean (deletes nothing).
  Details: `tools/port/README.md` "Disk hygiene".
- `MELEE_MODS_DIR` is the parent of mod folders; pass Windows paths (`pwd -W`), not `/c/...`.
- **Read the log, not the harness.** A run's `melee-pc.log` and `crashlogs/` are in its sandbox
  under `_build/runs/<name>/` (or the sweep's `runs/`); the harness's summary has under-reported
  before.
- **The release guard is `check_release.ps1`**: nothing disc-derived ships. `publish.ps1` also
  refuses an exe older than the melee commit, or a commit not on the public remotes.
- The portable launcher is in `release/launcher/qt/`; keep English/Spanish labels together.
  It is drawn in the Atlas style from `menu/atlas/tokens.json`, Barlow Condensed and Source Sans 3, all
  Qt resources (`kit.qrc`). Build scripts run its CTest suite. Its `t()` pairs are checked by
  `release/launcher/check_qt_strings.py`; `check_strings.py` and `Lang.cs` are the C# reference launcher's.
  The old C# UI/string table remains a reference for deferred online features.
- PowerShell build scripts target Windows. `port/ci_linux.sh` and `check_linux.ps1` cover Linux
  and Windows/WSL checks; actual engine validation needs local discs.
