# tools/: how the game is built, run, tested, packaged and shipped

Each subdirectory has a README that is its reference. This file says which tool to reach for and
the rules that cross them.

| dir | reach for it when | reference |
|---|---|---|
| `port/` | building (`build.sh`), running (`run.sh`), a second agent (`agent_new.sh`), a fresh machine (`bootstrap.sh`), profiling (`prof_report.py`) | the header comment of each script; `melee/pc/docs/PORT_DEV_QUICKREF.md` |
| `release/` | a public release, the launcher, the user README, the crash upload server | `release/README.md`; notes in `release/notes/<version>.md`, the version in `release/VERSION` |
| `netplay/` | the matchmaking server, the friends zip (`make_package.ps1`), `HOW TO PLAY ONLINE.txt` | `netplay/server/README.md` |
| `sweep/` | which stages and fighters crash on each disc (`crash_sweep.py --plan` first) | its docstring |
| `replay/` | `.slp` playback, parity against the GameCube (`replay_compare.py`, `first_div.py`) | `replay/README.md` |
| `mex_port/` | reading m-ex's data and patches, the bridge signatures, the ABI audits | `mex_port/README.md` (the attribution rule is there: consult m-ex, never copy it) |
| `mods_browser/` | the mod index format the launcher reads | `gdmelee-mods.schema.json` |
| `blender/` | Target Test stage round-trips | `blender/README.md` |
| `gc_extract.py` | assets out of a disc, locally only | |

## Rules

- **Scripts, not raw commands.** `build.sh` exists for the bridge fixpoint; `run.sh` for the
  sandbox per run. A raw clang or a bare exe run repeats the mistakes those scripts encode.
- **Everything is relative to `GW_ROOT`** (`port/portlib.sh`), with the disc images from `.env`.
  Nothing hard-codes `C:\gdm`.
- **Two agents, two build roots** (`GW_BUILD_ROOT`). Test runs (`--test`) parallelise; gameplay
  runs share one audio device and one screen, so keep those serial or use the sweep's tiling.
- **Read the log, not the harness.** A run's `melee-pc.log` and `crashlogs/` are in its sandbox
  under `_build/runs/<name>/` (or the sweep's `runs/`); the harness's summary has under-reported
  before.
- **The release guard is `check_release.ps1`**: nothing disc-derived ships. `publish.ps1` also
  refuses an exe older than the melee commit, or a commit not on the public remotes.
- The launcher is one C# file; strings are keyed by their English text, so edit `GDMeleeLauncher.cs`
  and `Lang.cs` together and run `release/launcher/check_strings.py`.
- PowerShell scripts are Windows-only; the Python and bash ones run anywhere, but anything that
  starts the game needs Windows and a disc.
