# Codex packet D: the port's menus must not stretch in widescreen (2026-10-03)

Workspace `<workspace>`; the game is the separate checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/src/melee/gm/CLAUDE.md`, `melee/pc/platform/CLAUDE.md`, `menu/CLAUDE.md`, `docs/ART-BRIEF-menus.md`). Both trees are
deliberately dirty: do NOT commit, reset, stash, revert or reformat anything. Do NOT run `tools/port/build.sh` and do NOT launch
the game (the integrator builds and tests; another Codex job is finishing a small fix in `melee/pc/platform/gw_script_mission*`
and `gw_script_model_assets.inc`: do not touch those). Keep every file compilable at every save: the integrator may build while
you work, so write each edit complete.

## The owner's report and decision
"Im noticing some menus streched from their 4:3 asset size into widescreen now that we support it". Decision: the PROPER fix
(menus laid out on a wide canvas with the 4:3 layout centred and round things round), not the pillarbox stop-gap.

## Evidence (read it)
`_build/audit-20261003/menus-art/patches/03-kit-widescreen-stretch.md` (measurements, cause with file:line, the fix outline),
screenshots under `_build/audit-20261003/menus-art/shots/r4_43`, `r4_169`, `r4_219`, `_research/widescreen.md`,
`DEPENDENCIES.md` (who the widescreen mechanism is credited to: keep those credits intact and add to them if you draw on
anything else).
Cause in short: widescreen sets the presenter to stretch (`melee/pc/platform/shim_vi.c` ~1757), only perspective cameras are
widened (`melee/src/sysdolphin/baselib/cobj.c` ~1301), and every SisLib canvas is a fixed 640-wide ortho
(`melee/src/sysdolphin/baselib/sislib.c:532`), which is what the kit (`melee/src/melee/gm/gmfrontend*.c|inc`, `fe.canvas`) draws on.

## What to build
1. One source of truth for the view aspect, readable by game code through the shim boundary as a scalar (float as bit pattern,
   see `melee/CLAUDE.md`), following window resizes, returning 4:3 when widescreen is off.
2. The kit's canvas: when widescreen is on, the ortho spans 480*aspect wide with the authored 640 layout centred (left edge
   -(W-640)/2). Decide deliberately whether to change the SisLib canvas globally or only the kit's canvas: vanilla text drawn
   over native screens and the in-match HUD currently measure proportional and MUST NOT move or change; say in the report which
   you chose and why, listing every SisLib user you checked.
3. Everything full-bleed in the kit fills the wide canvas: backdrops/bands, fades and dims, the description strip and top chrome
   bars if they are meant to span the screen (follow the art brief), transitions that slide from off-screen (they must start
   beyond the real edge). No clear or black side gaps.
4. Mouse hit-testing (`gmfrontend_mouse.inc`) and any pointer-to-canvas mapping use the same offset and scale.
5. Lua overlays: `gd.safe_area` must report the same wide canvas; fix the LAB overlay's hard-coded 640
   (`_build/audit-20261003/menus-art/patches/04-lab-overlay-hardcoded-640.md`; `melee/pc/geno/mods/geno-lab/scripts/lab.lua`,
   then run `lua melee/pc/geno/tools/lab_stage_d_check.lua` as that mod's CLAUDE.md requires).
6. A "Widescreen" row in SETTINGS > VIDEO (it does not exist; the setting is only reachable by env/cfg), applied live and saved,
   using the existing settings machinery. Give the port's settings pages no new selection id that collides with existing ones
   (a collision between `SEL_1P_LAB` 0x42 and the AUDIO page hid AUDIO; that was just fixed in `gmfrontend_menus.inc:256`).
7. `README.md` says "Widescreen: not started" (~line 328): correct it to what is true after this change. Do not regenerate art.

## Rules
Root cause only; no per-screen fudge factors. Match the surrounding code style; port changes in upstream files stay under
`TARGET_PC`. Add a log line for the canvas width when it changes. Add headless tests where the suite has a pattern for it
(`melee/pc/platform/gw_test*.c`, `melee/pc/tests/`): the canvas maths (4:3, 16:9, 21:9, widescreen off), the mouse mapping
round-trip, the settings row persisting. Syntax-check game-side C as PowerPC where clang is available (command in
`melee/CLAUDE.md`); say if you could not.

## Report
`_build/tmp/codex-kit-widescreen-report.md`: what changed with file:line, the SisLib-users decision, every full-bleed element
you extended, tests added, what you could not verify without the game, and an exact on-screen test plan for the integrator
(which screens, at which window sizes, what to measure: a round element must measure 1.0 +/- 0.03 at 4:3, 16:9 and 21:9).
