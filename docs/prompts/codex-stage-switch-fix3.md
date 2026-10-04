# Packet O follow-up 3: stage switching after its full verification run in the game (2026-10-03)

Same rules (no commits/reset, no build, no game launch, keep files compilable). You have just finished follow-up 2 (ledges,
dynamic stages, CPU mode across a switch): this list comes from a verification lane that ran your first build (exe of
16:03, before follow-up 2) for the whole native test plan. Evidence: `_build/audit-20261003/stage-switch/r2/<test>/`
(`probe.log`, `game.log`, screenshots; contact sheets `trans3/data/{wipe,flash,morph}_sheet.png`, `host_ps/data/ps_sheet.png`,
`ace3/data/ace_sheet.png`) and `_build/audit-20261003/stage-switch/patches/`. Check each item against your CURRENT source
first: some may already be fixed by follow-up 2; say which.

What passed: six legal stages fit (about 4.7 MB, 3.16 MB left; ten stages loaded before a clean refusal; the heap returns
after free and is stable across cycles); a switch costs 1.5-2.2 ms of logic with no hitch; the queue (timed, shuffle with a
seed, manual, events); hosts Battlefield, Yoshi's Story and Pokemon Stadium fully hidden and neutral, Brinstar refused
cleanly; about 100 of 124 scanned ACE m-ex stages load as static slots; fighters standing, airborne, mid-attack, shielding
and in hitstun keep their state and lose no stock; a fireball and a capsule survive; an off-stage fighter is placed on the
new edge; rewind is refused with a clear message; cleanup after a script error and a scene change.

Fix, in the order a player would hit them, each with a test:
1. **The game hangs when a switch happens while a fighter is hanging on a ledge** (3 of 4 launches). The log stops after
   `script stage: removed line handle=4`, before `stage switch: slot=... epoch=...` (`script_stage_slots.inc` ~466-468). A
   debugger attached to a hung process showed the main thread spinning in `gw_Script_Tick+0x1561` on a flag byte. So the
   native side is waiting for the game thread, which is stuck: most likely a game-side loop over collision lines or ledge
   ids that never terminates once the fighter's ledge line is removed (a `while` following prev/next links of a removed
   line, or the cliff-state code re-querying a ledge id that no longer exists), or a blocking spin that calls no shim (the
   deadlock class `melee/CLAUDE.md` warns about). Find it from the code: what a fighter in CliffCatch/CliffWait reads every
   frame, and what your removal leaves behind. A ledge-hanging fighter must be taken off the ledge into a defined state
   BEFORE any line is removed (the same for a fighter on a moving platform, grabbing, being thrown, or riding stage
   geometry). Add a fixture that removes lines under a fake ledge-hanging fighter and proves termination.
2. **`gd.stage_slot_load{models=...}` (a mission-folder level as a slot) crashes**: `gw_script_stage_mission.inc:44` calls
   `gs_model_options(L,-1,field)`, which pushes a string key so index -1 is the key and `lua_rawget` faults
   (`luaH_get <- lua_rawget <- gs_model_options <- l_stage_slot_load`). Use an absolute index
   (`patches/mission-slot-options-index.diff`). The missions-mod diff you delivered has CRLF endings and a stale context
   line and does not apply: re-issue it against the current mod (`patches/missions-stage-slot-helper.diff` is the tester's
   equivalent, syntax-checked only).
3. **Destination stages are the wrong size**: Battlefield measured 1.25x and Yoshi's Story 1.43x (platform heights 34/68
   against native 27.2/54.4; 33.5 against 23.45), and blast zones unscaled too (Battlefield KO at x=290 against native 230):
   the stage's own ground scale (`GroundParam` scale, 0.8 and 0.7 for those stages) was not applied to slot models,
   collision, blast zones, camera bounds and spawns. Your current source has a scale wrapper: confirm it covers ALL of
   those consistently and add a fixture comparing a slot's collision and blast zone with the native stage's own values.
4. **`place="ko"` does nothing to a fighter standing on a floor** (docs say Stage Morph's rule: fighters outside the new
   blast zone are KO'd; the code gates on already being outside or off a floor, ~427/459): make code and docs agree
   (`patches/place-ko-all-fighters.diff` is one reading; choose the rule deliberately and state it).
5. **LAB savestates fail silently while a slot session is active**: `gd.loadstate` after a switch returns true and does
   nothing; a save taken with live slots is silently not stored; `rewind_test` returns false with empty text. Refuse with a
   clear message and a log line in each case (or make it work), never report success.
6. **The wipe and flash transitions do not read as a wipe or a flash**: the tester saw the old stage frozen with the HUD
   still up, one black frame, then the new stage; the indicator text never appeared. Morph looks good (new terrain rising
   through the sinking old one). Make `wipe` a visible directional sweep and `flash` a visible flash-to-white and back,
   each with a duration parameter and a sensible default (about a second), covering or deliberately excluding the HUD
   (state which), using the post-process passes; make the pre-switch indicator actually draw.
7. **A slot of Final Destination shown on another host looks wrong**: a tighter camera and a red-vortex backdrop instead of
   FD's starfield (all backdrop groups load): find which background layer or effect is the host's own leaking through, or
   which of FD's is missing.
8. Music is reported per slot but nothing proves it changes: confirm from the code that the switch really changes the
   playing track, and log it.
9. `stage=dl` in the scene grammar selects Green Greens (id 13), not Dream Land: say what the right token is and document
   the legal-stage names for slots and scenes in one table.
Report `_build/tmp/codex-stage-switch-fix3-report.md`: per item, already fixed by follow-up 2 or fixed now, with file:line.
