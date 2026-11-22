# Codex packet Q: tools for people who write Geno fighters (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/geno/CLAUDE.md`, `melee/docs/geno.md` in full, `tools/CLAUDE.md`). Both trees are deliberately dirty: do NOT
commit, reset, stash, revert or reformat. Python and data only: do NOT edit C, do NOT run `tools/port/build.sh`, do NOT launch
the game. No game-derived data may be written into either repository: tools that read the user's own disc write their
output to a path the user gives, outside tracked folders by default, and say so. Credit anything you draw on in
`CREDITS.md`; consult, never copy.

## Why
A course for human beginners now exists: `docs/learn/geno-fighters/` (read `README.md`, packets `00`-`03`, and
`10-known-gaps.md`, whose ranked list of missing tools is this packet's brief). A learner-lane is working through it in the
game right now and may edit those files: do NOT edit anything under `docs/learn/geno-fighters/` except to ADD the new files
named below; report text changes you recommend as a list. Today an author hand-encodes move scripts as raw 32-bit words,
gets no error for a mistyped key in `geno.json` (unknown keys are silently ignored), and finds mistakes only by launching
the game and reading the log. The owner approved building the four tools below.

The engine is the specification: `melee/pc/platform/geno_registry.c` (what `geno.json` keys exist, their types, limits and
defaults, the `geno:` log lines, the 27 `attach` names in the `gn_vanilla` table), `melee/pc/geno/geno.h` (ids, limits),
`geno_game.c` and its `.inc` files (the script escape opcode 59 and its sub-commands, values, conditions, hooks, callbacks),
`melee/docs/geno.md` sections 7-9 and 15-20 (stable encodings). The existing encoder is `ports/ir/tools/acmd_to_ftcmd.py`
(and the generators beside it); the decoder side exists in the LAB (`lab events`) and `melee/pc/geno/tools/`. Where code and
reference disagree, the code wins and you list the disagreement.

## Build, under `tools/geno/` (a small package with one job per module, plus `tools/geno/README.md`)
1. **`geno_check`**: `python -m tools.geno.check <mod folder or geno.json>` validates as the engine would, without the game:
   JSON syntax with line and column; every key against the schema the registry really accepts (unknown key = error with the
   nearest valid key suggested; wrong type; out-of-range index; limits such as the state and article caps, overlay word
   lengths, table sizes: take each limit from the code and cite it); references that must resolve (files beside the mod,
   state names, subaction rows, animation names where checkable without disc data, `attach` names, hooks, callbacks,
   values); script words decode cleanly (item 2); `mod.json` fields; and a refusal list for files that look disc-derived
   (whole game archives) with the reason. Exit code non-zero on error; `--json` output for editors. Derive the schema from
   the registry source mechanically where you can (a generator script with a test that fails when the registry gains a key
   the schema lacks), so it cannot drift silently.
2. **A script assembler and disassembler**: a small, documented text form for fighter scripts covering the vanilla command
   set Geno fighters use (hitboxes, timers, loops, flags, graphics and sound calls, IASA and the rest: enumerate from the
   existing encoder and the game's command table in `melee/src/melee/ft/ftaction.c` / `ftcmd`) AND every Geno escape
   sub-command, value, condition and call, with symbolic names instead of numbers. `asm` turns text into the word arrays
   `geno.json` takes; `disasm` turns words back into the same text; round-trip is exact (property test over the encoder's
   outputs and over every script in the tree's Geno fixtures and generated fighters). Errors name the line. Reuse the
   existing encoder's logic rather than forking it (import it; if it must be refactored to be importable, do that without
   changing its output: prove with its existing tests).
3. **`geno_export`**: reads an existing fighter's move scripts FROM THE USER'S OWN DISC IMAGE (path from the `.env`
   variables or `--iso`; never printed, never written into a tracked folder) and writes them as the editable text form, so
   a person can change one number in a stock move and put the result in an overlay. Say exactly which fighters and data it
   can read with the readers already in the tree (`tools/`, `ports/ir/tools/`, `tools/mex_port/`), and stop cleanly where
   it cannot. Output carries a header saying it is derived from the user's disc and must not be shared.
4. **A commented template and a schema**: `docs/learn/geno-fighters/template/geno.json.md` (every key with a one-line
   explanation, type, default, limit and the reference section, generated from the same schema as item 1, with a test that
   it is regenerated when the schema changes) and a machine-readable JSON Schema file (`tools/geno/geno.schema.json`) that
   editors can use for completion and inline errors; a minimal valid `geno.json` and `mod.json` pair as files.
5. **A starter mod as data only** under `docs/learn/geno-fighters/starter/`: the smallest folder that the validator passes
   and that the course's packet 1 describes (an overlay on a vanilla fighter that changes something visible), written in
   the text form from item 2 with a build step that assembles it; no game data. The learner-lane is producing a tested
   tutorial mod under `_build/audit-20261003/geno-guide/mods/`: if it exists when you get here, base the starter on it and
   say so; otherwise base it on packet 1 and flag it as not yet run in the game.
Tests (pytest or unittest, matching the repo's existing Python tests): schema coverage against the registry, every
validator rule with a failing example, assembler round-trips, the export tool against a stub reader, template generation.

## Report
`_build/tmp/codex-geno-author-tools-report.md`: what each tool does with examples of its output, every limit and where in
the code it comes from, disagreements found between the reference and the code, the text changes you recommend to the
course so it teaches the text form and the validator instead of hand-encoded words, what could not be done, and what must be
checked in the game.
