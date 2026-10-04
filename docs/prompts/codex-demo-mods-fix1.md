# Packet S follow-up: the tour runner is not safe to run as written (2026-10-03)

Same rules (Lua/JSON/Markdown/Python only, no C, no build, no game launch, no commits). A pilot agent inspected
`tools/port/demo_tour.py` before launching and stopped, correctly. Its findings and a proposed diff (which no longer applies
to the current file) are in `_build/audit-20261003/demo-tour/REPORT.md` and
`_build/audit-20261003/demo-tour/patches/demo-tour-preflight.diff`. A second lane is running the catalogue by hand meanwhile.
Fix `tools/port/demo_tour.py`, with tests in `tools/port/test_demo_mods.py`:
1. It writes the resolved disc image path into `plan.json` (the launch command, ~line 136/150) and into `runner.log`. The
   disc path must never be written or printed anywhere: redact it (`<disc>`) in every file and line the tool produces, and
   add a test that scans the tool's outputs for the configured path in both slash forms.
2. It launches with `p2=marth/cpu0` and never makes the CPU idle. `cpu0` is NOT idle in this game: the tour must put every
   CPU in `gd.cpu_mode(port,"stand")` a couple of frames after match start and re-assert it after each demo loads (and after
   respawns/stage switches), unless a demo's catalogue entry says it needs an acting CPU; log proof per demo.
3. It overrides the window size to 1066x600 whatever the caller asked for: honour `MELEE_WINDOW_W/H` when set, default
   1024x576, keep the second-monitor position and the width limit.
4. No overall time limit or unattended policy: use the launcher's new `--max-seconds`, owner tag (`MELEE_RUN_OWNER`) and
   verdict line (`_build/tmp/codex-hung-game-detection-report.md`), per demo and for the whole tour, and record each
   demo's verdict.
5. It writes under the build root's `runs/` as well as its output folder: document what it writes where; make the output
   folder the only place results go.
Also add to the catalogue README the rule that each demo which needs an idle opponent sets it itself.
Reply with file:line changed.
