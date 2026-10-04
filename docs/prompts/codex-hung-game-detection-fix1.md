# Packet T follow-up: the launcher tooling after its first real use (2026-10-03)

Same rules (no commits/reset, no build, no game launch, keep files compilable). What worked in the game: the heartbeat file
(about once a second; during a real hang it read `state: main-loop-stalled`, `main_age_seconds 38`, with the script callback
named), the interactive watchdog (`gw: watchdog: HUNG ...`, `hang.txt`, game left alive), the unattended watchdog (exit
after about 10 s, `verdict.json` HUNG code 86, `launcher final reason=HUNG code=86`), and `runs.py wait` (OK rc 0, HUNG
rc 1). It caught a real engine hang today. Evidence: `_build/audit-20261003/demo-tour/` (`hang-evidence/`,
`patches/runs-inventory-tolerance.diff`).

Fix, each with a test:

1. **`runs.py` cannot attribute live games**: they show `owner=untracked state=unknown`, and `status --owner X`,
   `reap --owner X` and `reap --sandbox NAME` print nothing and exit 0. Cause: `inventory()` (about line 121) requires an
   exact match of the process creation time; `live_processes()` takes it from CIM `CreationDate.ToFileTimeUtc()`
   (microsecond resolution) while `run.json` holds the 100 ns FILETIME (for example 134355479274178404 against
   134355479274178400), so they match only when the last digit is 0. Match within 1 ms. `terminate_verified` compares the
   same two values exactly and needs the same tolerance, or `reap` will fail with "process identity changed" once matching
   works. A reap that matches nothing must say so and exit non-zero.
2. **`run.json` in each run folder contains the disc image path** (the launch command), and `run.sh` prints a
   `disc image ...` line into every harness log. The disc path is never written or printed: redact it (`<disc>`) everywhere
   the launcher and the tools write, and add a test that scans a fake run folder for the configured path in both slash
   forms and the JSON-escaped form.
3. `run.sh` printed once, at its line 93, an `Aborted` message from the `grep -qiF` that checks the live process list
   against the sandbox path: find and fix the fragile pipeline.
4. Unattended runs must default to `MELEE_VOLUME=0` (interactive runs keep 3): `run.sh` line 126 defaults everything to 3.
5. `watchdog: intentionally-paused` is logged on every pause: rate-limit it (once per pause, plus a summary).
6. `gd.scene_launch` shows as `logic-not-advancing logic_age=10.0`: either mark a scene change as an expected, named state
   in the heartbeat or explain why logic really stops for ten seconds.
7. The GameCube adapter: `gc adapter: reclaim - adapter busy (error 5)` appears in runs with `MELEE_PAD_IGNORE_ADAPTER=1`,
   and test windows keep the owner's adapter away from the window the owner is playing in. Read
   `melee/pc/platform/gc_adapter.c` and `shim_pad.c`: with the ignore flag set the game must not open the adapter device at
   all; an unattended run (`MELEE_UNATTENDED=1`) must never hold it; and a focused interactive window should win it from
   unfocused ones.

Report `_build/tmp/codex-hung-game-detection-fix1-report.md`.
