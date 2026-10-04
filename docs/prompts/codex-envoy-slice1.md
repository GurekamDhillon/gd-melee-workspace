# Codex packet E1: Supertime Envoy, slice 1 (2026-10-03)

Workspace `<workspace>`; the game is the separate checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`).
Both trees are deliberately dirty: do NOT commit, reset, stash, revert or reformat anything. Lua and Python only: do NOT edit C,
do NOT run `tools/port/build.sh`, do NOT launch the game. Other Codex jobs are working in `melee/pc/platform/`,
`melee/src/melee/gm/`, `melee/src/sysdolphin/` and `melee/pc/geno/mods/geno-lab/`: stay out of them.

## Read first
- The approved design: `docs/superpowers/specs/2026-10-03-supertime-envoy-design.md` (the owner said "lgtm"; sections 4, 5,
  8, 9, 10, 11 and 12 bind you; its section 13 proposals are accepted as written).
- The mission runtime you build ON TOP OF and must not fork or edit: `melee/pc/scripts/examples/missions/` (README, scripts,
  `tools/port/missions_bundle.py` if present, tests `melee/pc/tests/missions_*.lua`), its report
  `_build/tmp/codex-mission-runtime-report.md`, and the engine report `_build/tmp/codex-mission-engine-report.md`.
- `docs/scripting.md` (enemies, items/pickups, damage and speed modifiers, HUD text and `gd.kit`, `gd.safe_area`, persistence
  of script data: check every name against the registration tables in `melee/pc/platform/gw_script.c`; if a capability the
  slice needs does not exist, do NOT fake it: list it in the report as an engine request and build the rest).
- Why the old one failed: `docs/ENVOY-PROBLEMS-2026-10-02.md`. The old code is `tools/roguelite/`: do not reuse or edit it.
- Research and credit: `_research/chao-genetics-for-envoy-2026-10-03.md`; `CREDITS.md` (add nothing copied; rules are
  re-implemented from the description, crediting the sources in the mod's README).

## Slice 1 (what the owner can do at the end)
One run: one hand-built level and a boss room, enemies drop drives, a HUD panel shows the companion's four stats filling, and
stat levels change the fighter. No hub, no evolution, no grades-changing, no breeding yet, but the data model must already be
the full one (two alleles per trait, grades E-S, points/levels, age, type) so later slices add behaviour, not migrations.

## Build
New mod `melee/pc/scripts/examples/envoy/` (one folder, works on the vanilla disc; `mod.json`, `scripts/`, `README.md`,
`missions/` with a sample run's level folders described as data: models stay empty with a README line, as the missions sample
does). Small modules, one job each, none over ~400 lines, each with offline tests against a stub `gd` (pattern:
`melee/pc/tests/missions_*.lua`), tests written before the code:
1. `genetics.lua`: pure. DNA with two alleles per trait (four stat grades, colour, two-tone, shiny), blending (one random
   allele from each parent, no mutation), expression (grades: higher allele 70%), with an injected random source so tests are
   deterministic. Not used by slice 1's gameplay, but complete and tested.
2. `companion.lua`: pure. Stats Power/Speed/Guard/Reach: points, level = points/100, grade multiplies points gained, caps;
   the fighter effect per level as small capped numbers kept in ONE tuning table; age and type fields present.
3. `drives.lua`: drop on enemy defeat (each of the seven enemy kinds maps mostly to one colour, table-driven, with an
   injected random source), a pickup that sits a few seconds and is collected by touch within a radius that Reach widens,
   rare white drive; picked-up points are kept if the run fails.
4. `run.lua`: a run is a list of mission folders ending in a boss room; flow between them through the mission runtime's own
   API/commands; run end (win, fail, quit) settles the companion exactly once.
5. `save.lua`: one profile file, written as a complete replacement (write temp, rename), versioned, refuses and reports a
   corrupt file without overwriting it; every settling action is one write.
6. `hud.lua`: the four stat bars and level numbers, laid out with `gd.safe_area` (never a hard-coded 640).
7. `main.lua` glue and console commands for testing: `envoy start`, `envoy stop`, `envoy give <colour> <n>`,
   `envoy status`, `envoy reset-profile` (asks for the word `confirm` as an argument).
The boss in slice 1: use what the engine has today for a fighter opponent in the LAB/mission (a CPU fighter present from match
start, held until the boss room if the API allows, otherwise present throughout) and say exactly which calls you used and
what is missing for the bench-until-needed behaviour.

## Acceptance (offline)
`lua` on every new test file passes; `luac -p` on every Lua file; the missions and map editor suites still pass untouched
(`lua pc/tests/missions_*.lua`, `lua pc/tests/map_mission_test.lua`, `lua pc/tests/map_editor_test.lua` from `melee/`).

## Report
`_build/tmp/codex-envoy-slice1-report.md`: modules with one line each, the save schema, the tuning table, every engine call
relied on with the registration line you checked, engine requests (missing capabilities), test names and counts, and a native
test plan for the integrator (console commands and the log lines that prove each feature). Do not claim it works in the game.
