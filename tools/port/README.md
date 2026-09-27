# tools/port

Build and run the native Windows game from the workspace. `portlib.sh` resolves `GW_ROOT` from
these scripts and reads `.env`; `GW_MELEE` selects the game checkout, and `GW_BUILD_ROOT` selects
its objects, link response file, EXE, map and run sandboxes. The default game is `GW_ROOT/melee`.
A docs-only worktree need not contain it: set `GW_MELEE` explicitly when using another checkout.

## Commands (Git Bash)

```bash
bash tools/port/build.sh
bash tools/port/build.sh --tu src/melee/ft/ftdata.c --shim shim_dvd.c
bash tools/port/run.sh play --iso "C:/path/game.iso"
bash tools/port/run.sh --test tests --iso "C:/path/game.iso"
bash tools/port/run.sh --test --realtime tests-rt --iso "C:/path/game.iso"
MELEE_FPS=u bash tools/port/run.sh uncapped --iso "C:/path/game.iso"
MELEE_TURBO=1 MELEE_PAD_SCRIPT="C:/path/check.lua" bash tools/port/run.sh batch --iso "C:/path/game.iso"
```

Wrapper flags `--test` and `--realtime` go **before the sandbox name**. `--test` exports
`MELEE_TURBO=1`; `--realtime` exports 0. The headless test runner has no paced game-frame loop,
so its turbo request is informational, not an accelerated simulation. Normal windowed runs
remain realtime unless explicitly requested otherwise.

`build.sh` scans stale game TUs with `scan_stale_tus.py` (timestamps, including Geno headers),
rebuilds stale native shims, links, regenerates the bridge from that map, and rebuilds/relinks it
as needed until stable (at most four regeneration checks). It audits the final EXE's bridge ABI.
An unchanged trusted bridge avoids the extra link. Do not use raw clang for game TUs or bypass
the fixpoint. `GW_JOBS` is not supported in this revision; game-TU batches use `xargs -P 8`.

## Runtime switches

| Switch | Meaning |
|---|---|
| `MELEE_FPS=u` | uncapped interpolated presentation; realtime game logic remains 60 Hz |
| `MELEE_FPS=120` | cap interpolated presentation at 120; not a faster simulation |
| `MELEE_TURBO=1`, game `--turbo` | virtual-clock simulation without realtime pacing; requires `MELEE_PAD_SCRIPT` or `MELEE_LAB_BATCH`; refuses netplay, Slippi and fake rollback sessions |
| game `--realtime` | disables a turbo request; wrapper `--realtime` sets the environment to 0 |
| `MELEE_TURBO_RENDER=N` | present every Nth game frame (default 8, 0 never; range 0-10000); hidden/minimised windows do not present |
| `MELEE_TURBO_DRAWS=1` | keep display lists and skinning on unpresented turbo frames; normally suppressed while render callbacks still run |
| `MELEE_TURBO_HASHLOG=path` | per-live-match-frame snapshot hashes for parity diagnostics |
| `MELEE_TEST_SEED=integer` | fixed boot RNG seed for scripted comparisons |
| `MELEE_MODS_DIR=path` | parent containing mod folders; use a Windows path (`pwd -W` in Git Bash) |
| `GW_DAWN_CACHE_SEED=0` | disable copying an existing inactive run's compiled shader cache into a fresh sandbox |
| `GW_RUNS_KEEP=N` | retain the N most recently started stamped sandboxes (default 50); unstamped ones are not pruned |

Turbo mutes audio. Use realtime runs for controller, sound and presentation checks. Lua
`gd.input(..., frames)` counts completed logic frames even while stepping; text pad scripts
still consume one frame per PADRead. See [scripting.md](../../docs/scripting.md).

## Isolation and evidence

`run.sh` copies the EXE and map into `GW_BUILD_ROOT/runs/<name>/`, supplies runtime DLLs and
caches, and leaves the log there. Reusing a name replaces that sandbox's build: use distinct
names for concurrent runs. A live copy is not updated by a later build.

`agent_new.sh <name>` creates a game worktree and build root; `agent_rm.sh <name>` removes it
only when clean and retains the branch. Baseline objects are hardlinked: the local game-TU
writer must replace outputs rather than truncate shared files. Shared Aurora/Dawn/SDL libraries
are outside lane isolation. Read [HANDOFF.md section 6](../../docs/HANDOFF.md#6-traps) before parallel builds.

Read the run's log and crash logs as well as the test summary. Record EXE/game revision, disc,
mods, run directory and switches with any result. A successful older run is not a HEAD check.
