# Packet E1 follow-up 2: Envoy slice 1 after its first run in the game (2026-10-03)

Same rules (Lua/Python only, your mod and tests, no C, no build, no game launch, no commits). Evidence:
`_build/audit-20261003/envoy-verify/` (`patches/01..04`, the tester's isolated copy `mods/envoy` with its fixes and test hooks,
`shots/`, logs `_build/runs/env-ev1..13/melee-pc.log`). The mission runtime changed again (camera fix4/fix5, CPU bench
policy): read `_build/tmp/codex-mission-runtime-fix5-report.md` if present (else fix4) and re-bundle last.

First run result, on the vanilla disc: with one blocker patched the whole loop works end to end (menus by scripted pad,
level loads, boss benched, drives drop and are collected once, levels rise, boss called and fights, exactly one win written,
profile survives a restart, native stat ratios match your tuning table at levels 1/22/50/90 and return to exact base after
win, abandon, quit, fail and unload; plain, coloured, two-tone and shiny companions tint the fighter and survive a KO).

Fix, in the order they block a real player, each with a test:
1. **A fresh install cannot start**: `save.lua` ~86-89 treats a nil `gd.data_read` as an error, but the engine returns nil for
   a missing file. Apply the intent of `patches/01-save-missing-profile.diff` (verified in the tester's copy): no profile =
   start a default in-memory profile; the first settle creates the file atomically. Keep the corrupt-file refusal. An engine
   job is adding a way to tell "missing" from "unreadable" (`gd.data_exists` or a distinct second return): use it when
   present, guard for its absence. Drop the README instruction to run an initialiser first.
2. **Enabling the mod pauses every offline match behind the Envoy title menu** (`app.lua` ~179 `sync_pause`, `visible` starts
   nil): the menu must be closed by default and open only through `envoy menu` or the mode's own entry point; a match the
   player started for another reason must be untouched (no pause, no D-pad mask).
3. **Soft-lock on an error or corrupt profile**: the profile screen's only entry is disabled, B returns to title, title has no
   exit, the game stays paused. Every screen must have a way out that unpauses, and an error state must offer "Close".
4. **Confirm screens open on "Confirm"** after the first use (focus memory applies to them): quit and abandon confirms must
   always open on the safe default, as `MENUS.md` says.
5. **The menu launches `mode='training'` with `falco/cpu`**: use the LAB (`mode=lab`), with the opponent handled by the
   runtime's CPU policy (standing rule: tests and owner windows use the LAB, never training).
6. **State carries between runs**: the benched boss arrives pre-damaged (it kept 56-116%) and P1's percent carried into the
   next run (39% at the start of run 2). Reset both at run start and when the boss is called; say whether a benched fighter
   can take damage from real hitboxes (the engine bench is intangible: the tester only saw it from `fly_attack`).
7. **Koopa never drops a drive**: its shell transition emits no `on_enemy_defeated`, though the mission logs "defeated
   koopa". Award drives from the mission's own defeat signal so every kind the mission counts as defeated drops.
8. **Goomba and redead never drop in the sample level**: they walk off the ledges and are counted as lost. Redesign
   `missions/path` with walls or edge-safe placement so all seven kinds can be defeated; the idle player also takes ~24% and
   can be knocked off at spawn: give the start room a safe pocket.
9. **Test hooks**: add `envoy menudump` (current screen, entries, focus, disabled flags) and `envoy dump` (run, companion,
   modifiers applied, tint state) as supported console commands; the tester had to add them to drive the menus.
10. Cosmetic: the `tuning ... shield=` log prints `%.1f` (0.02 shows as 0.0); `envoy status` shows a stale room after a run;
    Records shows only "Last result".
11. **Drive models** (optional asset mod, game-derived, kept outside the repos): integrate the tested module and diffs from
    `_build/audit-20261003/drive-assets/patches/` (`src/drive_models.lua`, `app.lua.diff`, `envoy_bundle.py.diff`): when the
    mod `envoy_drives_sa2` is present its models draw the drives (two instances per drive, bob, blink before expiry, pulse on
    collect); when absent the current glyph is used. No game data enters the Envoy mod. An engine job will later add real
    standalone items (`gd.item_spawn`, `on_item_collect`): keep the pickup logic behind one small interface so it can switch.
Report: `_build/tmp/codex-envoy-slice1-fix2-report.md`.
