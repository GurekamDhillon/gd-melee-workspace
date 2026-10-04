# Codex packet K: easy controller remapping (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/src/melee/gm/CLAUDE.md`, `melee/pc/platform/CLAUDE.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md` (the controls section: it
says button remapping is not built and that Aurora's `PADSetButtonMapping` exists for SDL pads), `docs/ART-BRIEF-menus.md`,
`menu/CLAUDE.md`). Both trees are deliberately dirty: do NOT commit, reset, stash, revert or reformat anything. Do NOT run
`tools/port/build.sh`, do NOT launch the game. Keep every file compilable at every save. Other Codex jobs are editing
`melee/pc/platform/gw_fx*`, `gw_script*`, `melee/pc/gameworld/`, `melee/extern/aurora/`, shader files: stay out. The menu files
(`melee/src/melee/gm/gmfrontend*`) were just changed by a finished job (widescreen canvas, scroll cue, description fit rule):
read `_build/tmp/codex-kit-widescreen-report.md` and `..._fix1-report.md` and build on that state. Credit anything you draw on
in `CREDITS.md`; consult, never copy.

## The owner's ask (verbatim)
"make controls remapping easy for controllers"

## What "easy" must mean
A player with any supported controller (GameCube controller through the adapter, and SDL gamepads: Xbox, PlayStation, Switch
Pro, generic) can, from SETTINGS > CONTROLS with only that controller in hand, change what each physical input does, in
under a minute, without reading anything, and cannot lock themselves out.

## Build
1. **Model.** A per-controller mapping from physical inputs to the game's GameCube inputs (A, B, X, Y, Z, L, R, START, D-pad,
   control stick, C-stick, analog L/R), stored per device identity (adapter port for GC; SDL GUID/name for pads) with named
   profiles, in the existing settings file through the existing settings machinery (`melee/pc/platform/gw_settings.c`), applied
   in the pad shim (`melee/pc/platform/shim_pad.c` and the Aurora mapping it already uses). One physical input may drive
   several game inputs and several physical inputs may drive one (e.g. two jump buttons). Include the common competitive
   options as simple toggles on the same page: tap jump off (up on the stick does not jump), shield on a digital press at a
   chosen analog value (light/full), trigger analog off, swap sticks, C-stick as attacks stays the game's default (never make
   it a camera), per-stick dead zone (already exists: integrate, do not duplicate), and rumble if supported.
   State exactly which of these are implemented as input transforms in the shim versus needing game-side changes; game-side
   behaviour changes (tap jump) must be exact and offline/online-safe: mapping is applied to the local pad before the input
   enters the game/netplay pipeline, so both peers see ordinary GameCube inputs and nothing desyncs. Say why that holds.
2. **The remap screen (kit, same visual language as the other settings pages).** A picture or labelled list of the game's
   inputs; select one, "press the button you want" with a short timeout and a clear cancel; conflicts shown and resolved
   (swap by default, with an "also" option for duplicates); a live tester strip showing what the game receives as you press;
   Reset to default, per profile; choose which connected controller you are editing (by pressing a button on it); profiles:
   new, rename (existing name-entry or a simple list of preset names if text entry is not available), delete, assign to port.
   Safety: navigation of the menu itself always works with the device's default layout while the remap page is open, and
   START+B held for 2 seconds restores defaults for that controller anywhere in the menus. Everything fits the description
   strip (the fit rule exists) and works at 4:3, 16:9 and 21:9.
3. **Presets** shipped as data: default, and two or three well-known layouts as starting points (e.g. tap-jump-off with a
   shoulder jump; a "Xbox/PlayStation friendly" layout mapping face buttons sensibly), each one line of description.
4. **Keyboard** is out of scope unless the existing keyboard binding path makes it free; say what exists.
5. **Launcher**: do not edit the Qt launcher; report whether its strings/settings mention controls in a way that should
   follow (the launcher's strings are looked up by exact English text and have a checker).

## Tests and docs
Headless tests in the suite's pattern: mapping application (each transform, many-to-one, one-to-many), conflict resolution,
profile save/load round-trip and migration from a settings file without mappings, device identity fallback, the safety
restore, that a mapped pad produces identical netplay input bytes to a real GameCube pad producing the same intent. A short
player-facing section for the README/docs (where controls are documented today) and the agent notes updated
(`PORT_DEV_QUICKREF.md` no longer says remapping is not built).

## Report
`_build/tmp/codex-controls-remap-report.md`: design as built, file:line, what is shim-side versus game-side, settings schema,
tests, unverified items, and an on-screen test plan for the integrator and for the owner with a real controller in hand.
