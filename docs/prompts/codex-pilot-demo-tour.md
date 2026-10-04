# Codex pilot: run the demo tour in the real game and report (2026-10-03)

This is a PILOT. Until now you wrote code and never ran the game; the owner doubts game-running suits you ("I think its
really bad at that tbh, but if you can coax it into doing it properly sure"). For this one job your sandbox is open so you
CAN launch the game. The pilot succeeds only if you follow the procedure exactly and your report is trustworthy. If
anything is unclear or a tool misbehaves, STOP and report what happened; do not improvise around it.

Workspace `<workspace>`. Read `CLAUDE.md`, `tools/port/README.md` (the agent launch pattern added
today), `_build/tmp/codex-hung-game-detection-report.md`, `_build/tmp/codex-demo-mods-report.md`,
`melee/pc/scripts/examples/demos/README.md`.

## Hard rules
- Do NOT edit any tracked file. Do NOT build (`tools/port/build.sh` is forbidden). Do NOT commit, reset, stash or revert.
  You may write only under `_build/audit-20261003/demo-tour/`.
- Launch the game ONLY through `tools/port/demo_tour.py` (which uses `tools/port/run.sh`) with an owner tag
  `MELEE_RUN_OWNER=codex-demo-tour`. Never start `melee-pc.exe` directly. Never hide or minimise the window (the game stalls).
- Second monitor only: `MELEE_WINDOW_X=-1080 MELEE_WINDOW_Y=-360`, window width <= 1080 (use 1024x576). The owner is using
  the main monitor.
- The disc image path comes from `.env` (`GW_ISO_VANILLA`): load it into the environment, never print it, never write it
  into any file you create (check your output files for it before finishing).
- At most ONE game instance from you at a time. Before each launch run `python tools/port/runs.py status`: if 8 games are
  running or available memory is under 2 GB, wait.
- Never end a process you did not start. End your own only through `python tools/port/runs.py reap --owner codex-demo-tour`.
- Every launch has a time limit. When you finish, `python tools/port/runs.py status --owner codex-demo-tour` must show
  nothing; paste its output in the report.
- CPU opponents must be idle: `cpu0` is not idle in this game; the tour or each demo must call `gd.cpu_mode(port,"stand")`.
  If the tour does not do it, report that as a defect; do not edit the tour.
- Report only what you observed. For every demo give the evidence: the log lines and the screenshot file you looked at.
  If you did not look at a screenshot, say so. Never infer a pass from the absence of an error.

## Task
1. Run the tour over the whole catalogue on the vanilla disc with the current `_build/melee-pc.exe` (built 17:36, native
   suite 256/256). In batches if the tour supports it, so one hang does not lose everything.
2. For each of the 36 demos and 3 showcases record: loaded without script errors (quote the load line); did something
   visible (describe what the screenshot shows in one sentence, having opened it); any `error`, `refused` or `ran too long`
   lines (quote them); unloaded cleanly.
3. Classify each: WORKS, LOADS BUT SHOWS NOTHING, SCRIPT ERROR, ENGINE REFUSAL, HANG/CRASH (with the run verdict from the
   launcher), NOT RUN (why).
4. For each failure give the cause if it is evident from the log and the demo source (file:line), and a proposed fix as a
   diff under `_build/audit-20261003/demo-tour/patches/` (do not apply it).
5. Also report honestly on the tooling itself: did `demo_tour.py`, `run.sh` owner tags, `runs.py status|wait|reap`, the
   heartbeat and the verdict line work as their reports claim? Quote what they printed.

## Report
`_build/audit-20261003/demo-tour/REPORT.md`: the table, the failures with evidence, the tooling findings, the final
`runs.py status` output, and a list of anything you were unsure about.
