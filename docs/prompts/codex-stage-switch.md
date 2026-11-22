# Codex packet O: seamless stage switching with a pool of stage slots and a queue (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `docs/scripting.md`, `docs/shaders.md`, `docs/HANDOFF-2026-10-03-ENGINE-DAY.md`). Both trees
are deliberately dirty: do NOT commit, reset, stash, revert or reformat. Do NOT run `tools/port/build.sh`, do NOT launch the
game. Keep every file compilable at every save. A profiler job (`docs/prompts/codex-profiler-bench.md`) starts at the same
time as you and instruments `gw_script*`, `gw_snap.c`, `gw_rollback.c` and game-side hot paths; an aspect-ratio job is in
`sysdolphin/baselib/cobj.c`, `shim_vi.c`, `gm/gmfrontend*`. Put your code in NEW files; touch shared files last, small, after
re-reading them. Credit: the design reference is Super Smash Bros. Ultimate's Stage Morph (Nintendo, Bandai Namco Studios,
Sora Ltd.; behaviour as described on SmashWiki, CC BY-SA 4.0): ideas only; record it in `CREDITS.md` if not already there.

## Read first
`_research/seamless-stage-switch-2026-10-03.md` (the feasibility study: every claim tagged, the load path, precedents such as
`Ground_TTMod_BuildCollData` in `gr/ground.c` ~690-806, what holds references to the stage, three designs, the Stage Morph
rule set, and an experiment that switched Final Destination -> Battlefield -> Yoshi's Story in one match with today's Lua
calls: probe and logs in `_build/audit-20261003/stage-switch/`, `_build/runs/stsw-2/`). Its findings are your starting point;
verify what you rely on.

## The owner's asks (verbatim)
"No loading screen switches between actual melee/ace/modded stages would be cool as well. ... loading screen -> Final
destination -> some kind of indicator during the fight -> screen flash, or shader effect, or screen wipe -> temp collision
across the entire screen so people cant fall off and die -> screen wipe back into gameplay -> we're on yoshi's now"
"Well can we have additional stage slots to pre-load more stages, and buffer changes into arbirary amounts of stages?"
Then: "go, queue it on codex".

## Build (design A from the note: the destination is models + collision held as data on a hidden host; shaped so design C,
pre-loaded stages with their own behaviour, can replace the inside later without changing the Lua API)

0. **Measure first, in code and report**: which game-side heap stage DAT models load into, its size, what one static stage
   costs (models, textures), and therefore how many stages fit at once; add a headroom counter. State the number for the
   legal stages. Everything below refuses cleanly, never crashes, when the pool is full.
1. **Stage slots.** `gd.stage_slot_load(spec) -> slot | nil, err` where spec is a vanilla stage name/kind, a disc stage file
   (vanilla or m-ex mod disc, static geometry), or a mission-folder level (the missions mod's levels: provide the hook the
   mod needs to register one as a slot; do not edit the mod, report the small change it needs as a diff);
   `gd.stage_slot_info(slot)` (memory, collision counts, bounds, spawns, blast zones, camera bounds, music id);
   `gd.stage_slot_free(slot)`; `gd.stage_slots()`. Loading may be spread over frames to avoid a hitch on a cold read (state
   the measured or estimated cold cost; the note measured 1.1-1.7 ms warm). Slots are data: no stage code runs for them.
2. **Collision from the stage file.** A native reader for a stage DAT's collision data (`coll_data`: vertices, lines with
   floor/ceiling/wall kinds, passthrough, ledge-grabbable flags, line groups/joints) that installs it as the active script
   collision when the slot becomes active, within the existing pool budgets (the note cites 768/1536/2048: confirm), with a
   clear refusal if a stage exceeds them. Nobody types collision by hand. Moving line groups are installed in their rest
   pose in this version; list which legal stages that misrepresents.
3. **Destination parameters.** Read and apply the destination's camera bounds, blast zones, spawn/respawn points, item spawn
   points and music from its data (`grGroundParam`, map markers) at the switch; restore the host's on unload.
4. **Host-agnostic hide.** `gd.stage_hide`/`stage_isolate` works on any host stage, not only Final Destination (models,
   collision, stage GObjs and callbacks that would otherwise keep acting: hazards must be neutralised, not merely hidden);
   list stages that cannot be hosts and why.
5. **`gd.stage_switch(slot, opts) -> ok | false, err`**, atomic, on a logic frame: optional indicator window before it;
   freeze with the timed hitstop; start the transition effect (a named built-in: `wipe`, `flash`, `morph` = new terrain
   rises through the old while both are visible, modelled on Stage Morph; or a mod-supplied `gd.post_*` shader); install a
   temporary full-width safety floor; deactivate the old slot and activate the new one (models, collision, parameters);
   place fighters by rule (`opts.place`: keep position if the new floor is under them, otherwise move to the nearest floor
   or a spawn point; `"ko"` to use Stage Morph's rule that fighters outside the new blast zone are KO'd; default = never KO);
   clear what each fighter carries from the old stage (floor and ledge line ids, ECB history, wall contacts) so nothing
   dereferences removed lines; despawn stage-bound items, carry held and portable items; projectiles in flight: choose and
   document; remove the safety floor; end the freeze; one LAB rewind fork for the whole switch. Bench/call may be used for
   placement (verified today: floor call arrives in Wait with no sink).
6. **A queue.** `gd.stage_queue{ {slot=, after=seconds | at_stocks= | on="event name", transition=, place=}, ... , loop=,
   shuffle=, seed= }`, `gd.stage_queue_next()`, `gd.stage_queue_clear()`; arbitrary length; triggers evaluated on logic
   frames; a script event `on_stage_switch` before and after; deterministic given the seed.
7. **Safety and scope.** Offline only in this version (refused under netplay/rollback like other stage writes; say what a
   native, snapshot-contained version would need). LAB savestate/rewind across a switch: make it correct or refuse a
   savestate load that crosses a switch with a clear message, and say which. Zero cost when unused. Everything restored on
   script unload, match end and scene change.
8. **A sample mod** `melee/pc/scripts/examples/stage_switch_demo/`: Final Destination -> Battlefield -> Yoshi's Story ->
   back, on a timer, with each of the three built-in transitions, console commands `stage next`, `stage queue`, `stage slots`.

## Tests and docs
Headless tests in the suite's pattern: the collision reader against fixture data (kinds, flags, budgets, refusal), slot
lifetime and the full-pool refusal, parameter apply/restore, the switch state machine (order of steps, fighter placement
rules with fake fighters, stale-reference clearing, item rules), the queue's triggers and determinism, cleanup on unload.
`docs/scripting.md` section "Stage slots and switching", with the limits stated plainly (static stages; no hazards; which
stages are misrepresented; offline).

## Report
`_build/tmp/codex-stage-switch-report.md`: how many stages fit and what bounds it, file:line for everything, per legal stage
what is right and what is missing, the fighter-state clearing list (the hardest part: be exhaustive, cite the fields), the
missions-mod diff, unverified items, and a native test plan (a round trip through three stages with fighters grounded,
airborne, hanging on a ledge, holding an item, mid-attack and in hitstun at the moment of the switch; what must be true
after each).
