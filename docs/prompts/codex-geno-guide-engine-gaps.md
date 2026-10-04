# Codex packet R: three Geno engine gaps found by a learner working through the new course (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/geno/CLAUDE.md`, `melee/pc/geno/mods/geno-lab/CLAUDE.md`, `melee/docs/geno.md`). Both trees are deliberately dirty:
do NOT commit, reset, stash, revert or reformat. Do NOT run `tools/port/build.sh`, do NOT launch the game. Keep every file
compilable. The current build is clean, stamped and passes 250/250. Another Codex job is writing Python author tools under
`tools/geno/` and may add files under `docs/learn/geno-fighters/`: stay out of both. Contracts in `melee/pc/geno/CLAUDE.md`
hold: numbers in reference sections 15-19 never change; new behaviour gets new ids; deterministic and rollback-safe.

A course for human beginners (`docs/learn/geno-fighters/`) was tested step by step in the game (vanilla disc, Kirby, the
tutorial mod at `_build/audit-20261003/geno-guide/mods/tutorial-kirby/`; drivers and log in that evidence folder, run
`_build/runs/ggd-p1a/melee-pc.log`). Three engine gaps stopped or misled the learner. Fix each at the root, with a test in
`melee/pc/geno/geno_tests.c` (name `geno_<what>`) or the LAB checker (`melee/pc/geno/tools/lab_stage_d_check.lua`: run it
after any `lab.lua` change), and update the reference where it promised something untrue.

1. **`jumps.max` above the fighter's own count does not take effect.** With `"jumps": {"max": 9}` on Kirby the log says
   `air jump N of 8` but Kirby chains at most 5 air jumps (`jumps_used` reaches 6) and the promised
   `(beyond Melee's multi-jump table)` line never appears. `melee/docs/geno.md` section 10 promises `max` works. Find what
   caps it (Kirby's own multi-jump states and their table, `ftKb` jump code, the count Geno writes versus the one the
   multi-jump states read) and make the declared maximum real for multi-jump fighters and for ordinary double-jumpers, or,
   if a real limit exists in the game data, make the registry refuse or clamp with a clear log line and document the limit.
2. **The LAB cannot decode a Geno state's script.** `lab events`, `gd.timeline`, `lab card` and the frame-data export show 0
   events for a state whose script comes from a `geno.json` overlay or a Geno state, so an author cannot check their own
   move's hitbox frames, IASA frame or commands; the same tools decode vanilla moves fine (`lab events` after
   `lab play Attack11` prints the jab). Make the decoder read the effective script (overlay words and Geno state scripts,
   including the opcode-59 escape sub-commands, shown by name) wherever it reads a vanilla one, natively and in `lab.lua`,
   so every LAB view that works for a vanilla move works for a Geno one.
3. **Hot reload does not re-apply a state's callbacks or its `iasa` setting.** Changing a state's `"iasa"` (and by the same
   path its phys/coll/anim callbacks and behaviours) in `geno.json` and reloading (`F8` / `lab reload`) reports success but
   the old behaviour stays until a new match. Reference section 14.10 defines what is a "layout change" (restarts the match)
   versus a live change: either apply these live, or classify them as a layout change so the match restarts and the log says
   why; never report a reload that silently did not apply. Also: the default `iasa` of `none` while the script contains an
   IASA command is a silent trap: log one warning line at load naming the state.
Also correct in `melee/docs/geno.md` what this exposed and what the course author listed in
`docs/learn/geno-fighters/10-known-gaps.md` (read its "source contradictions" list): Brawl Kirby is no longer a customer
(the tree's Geno fighters are Halberd, Ultimate Kirby and Sora); "v3" is used for two different things; cited demo mods and
test counts that are not in the repository; the header date. Do not renumber sections.
Report `_build/tmp/codex-geno-guide-engine-gaps-report.md`: cause of each in a few lines, file:line, tests, and an in-game
re-test plan using the tutorial mod.
