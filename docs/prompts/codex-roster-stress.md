# Codex packet V: roster stress test, 100 cloned fighter slots, and lifting the roster limit (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `docs/MEX_PORT_STATUS.md`, `docs/mods-packaging.md`, `tools/mex_port/README.md`,
`_research/vanilla-single-folder-mods-2026-10-03.md`). Both trees are deliberately dirty: do NOT commit, reset, stash,
revert or reformat. Do NOT run `tools/port/build.sh`, do NOT launch the game. Keep every file compilable at every save.
Other Codex jobs are editing `melee/src/melee/gr/` and `pc/gameworld/script_stage_slots*` (stage switching): stay out of
those. HARD RULE: generated table files and cloned fighter files are derived from a mod disc: they are written ONLY under
`_build/local-assets/roster-stress/` (git-ignored), never into a tracked folder, and never committed. Never print or write
disc paths.

## The owner's ask (verbatim)
"can we add 100 sonics to the roster as their own character slots to test expanding well beyond the limits?"

The fighter to clone is the Sonic that ships on the ACE mod disc (an m-ex fighter). The purpose is a stress test of roster
capacity, not new content: 100 additional, independently selectable character slots that all use that fighter's files.

## What is true today (verify)
- The roster has 94 added fighter slots: `GW_MEX_SLOT_COUNT` (`melee/pc/platform/gw.h` ~241) and `FT_MEX_SLOT_COUNT`
  (`melee/src/melee/ft/forward.h`), because CharacterKind and FighterKind live in SIGNED bytes all over the game
  (`PlayerInitData`, match-end data, `ftMapping_list`, the character select), so ids stay <= 127; m-ex has the same bound.
  Character-select icons cap at 128 (`GW_MEX_CSS_ICON_MAX`, `CSS_ICON_MAX` in `melee/src/melee/mn/mncharsel.c`).
- ACE's table defines 65 fighter rows in total, so 100 more does not fit under 94 added slots.
- Geno supports 32 fighter profiles (found by a census today): a separate limit if the clones are Geno fighters.
- A tool already clones one m-ex table row for a new fighter (`ports/ir/tools/install_ultimate.py`: `mxdt_clone` and the
  table list in its `INSTALL.json`); `tools/mex_port/dump_mxdt.py` reads the table file.

## Build, in three phases, each useful alone
**Phase 1: the generator (Python, no engine change).** `tools/port/roster_stress.py`: given the ACE disc (path from `.env`,
never printed), a source fighter (default: ACE's Sonic, found by name in the table) and a count N, produce a self-contained
local mod folder under `_build/local-assets/roster-stress/<name>/` whose table file has N extra fighter rows cloned from
the source (every per-fighter table the row touches: fighter data, costumes, character-select icon and position, names,
announcer, results-screen data, CPU tables, effect and sound bank references, item lookups: enumerate them from the table
layout our reader already knows), each row independently selectable, with a distinguishable name ("Sonic 001"...) and, if
cheap, a tint or costume offset per clone so slots can be told apart on screen. Refuse cleanly, with the reason, when N
exceeds what the current engine admits, and say what the largest admissible N is. Tests against a synthetic table.
**Phase 2: fill to today's limit and find what breaks below it.** With N chosen to reach exactly the 94-slot cap: audit
from the code everything sized by roster count that would be stressed (character-select layout and paging for that many
icons, icon cap 128, table arrays, name/emblem/stock-icon tables on the results screen and HUD, random-select, the
netplay character field width, save data keyed by character, CPU tables, load times and memory per added row, Geno's 32
profiles) and list each as fine / will break / unknown with file:line. Write the integrator's test plan (launch on the ACE
disc with the stress mod, page through the select screen, pick the first, middle and last clone, start a match with six
different clones, results screen, random select).
**Phase 3: lift the limit so 100 clones fit (engine).** Decide and implement the smallest sound route to more than 127
character/fighter ids, from the code: (a) treat the id bytes as unsigned everywhere (0..254, "none" moved) across the
match data, results, mapping tables, character select and every comparison and "negative means none" test: a wide sweep
whose risk is one missed signed comparison; or (b) a native roster registry with wide ids that maps onto the game's
byte-sized ids only for the fighters actually loaded in a match (at most six), so mod-disc code that reads those
structures at fixed offsets is unaffected. State which you chose and why, what it does to m-ex compatibility (m-ex's own
fighter id type is a signed byte: rows past its bound cannot come from an m-ex table, so say how the extra rows are
supplied), to netplay (the character field on the wire, the roster hash both peers must agree on), to replays and save
data. Raise the icon cap and make the character select page or scroll. Raise Geno's profile cap to match. Every array
sized by the old constants is found by a mechanical audit (a script that lists them), not by memory. Headless tests in the
suite's pattern (id round-trips at 0, 127, 128, 200 and the "none" value; mapping-table bounds; select-screen paging).
If phase 3 is too large for one pass, deliver phases 1 and 2 complete and phase 3 as a concrete plan with the audit list
and the first slice implemented.

## Report
`_build/tmp/codex-roster-stress-report.md`: what each phase delivered, the audit table, the design decision for phase 3
with its compatibility consequences, the largest roster the engine admits after your changes and what bounds it next,
unverified items, and the integrator's native test plan.
