# Packet B follow-up 7: staged install never commits in the game (2026-10-03)

Same rules (Lua/Python, your files, no build, no game, no commits). Integrator smoke test of fix6 on the stamped build
(native suite 250/250), LAB, vanilla disc, the tester's 8-chunk maze (play copy `_build/audit-20261003/maze-play/mods/`,
scripts copied from the repo after regenerating the bundle). Log: `_build/runs/maze-smoke4/melee-pc.log`.

What improved: at match start P1 is at 0% and the CPU is benched from the first frames (one early refusal is logged:
`script reserve: bench refused port=2 reason=grabbed, grabbing, carried or thrown`, then it takes).

What fails: `mission play maze` answers `mission: staging maze` and never finishes. Sixteen seconds later P1 is still
standing on Final Destination at (-60, 0), action 14; no `loaded maze` line; no `refused` line; no "ran too long". During
that time the log shows `script mission: stage_hide false accepted` at least eight times, 21 `blast bounds` writes and 20
`script camera params` writes, and zero camera cuts. So the staged transaction is looping: it appears to roll back (or
re-run a restore step) repeatedly instead of advancing or reporting a refusal.
Find the cause from the code and that log: a step whose completion condition is never true in the real engine (a stub in
your tests returns immediately where the engine needs frames: model loads that report ready later, `gd.fighter_bench`
refused while the fighter is in an unsafe state, `gd.stage_hide` semantics, a wait for a fighter state that the frozen or
benched fighter never reaches), a step that restores bounds/camera/stage visibility on every frame while waiting, or the
staging state being reset by the per-frame tick. Requirements:
- every wait in the staged path has a bounded timeout and ends in a logged refusal naming the step and the condition
  (`mission: refused staging step <name>: <condition> not met after N frames`), never a silent loop;
- no setter is called on a frame where nothing changed (the repeated `stage_hide false`, blast and camera writes are
  themselves a defect: idempotent, change-only writes);
- log one line per completed staging step (step name, frame count), so the next smoke test shows exactly where it stops;
- make your stub model the engine's real asynchrony for each engine call you wait on (read the C for what each returns
  while not ready), and add a test that reproduces this stall with such a stub before fixing it.
Regenerate the bundle. Reply with the cause in three lines and file:line; `_build/tmp/codex-mission-runtime-fix7-report.md`.
