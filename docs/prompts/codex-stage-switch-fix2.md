# Packet O follow-up 2: ledges are missing, and the owner needs switched-to stages to be DYNAMIC (2026-10-03)

Same rules (no commits/reset, no build, no game launch, keep every file compilable). The build is clean, stamped and passes
250/250 with your stage slots in it. Another Codex job is editing `melee/pc/geno/` and the LAB mod; a demo-mods job writes
Lua only. The owner watched the demo (Final Destination -> Battlefield -> Yoshi's Story cycling, all three transitions) on
the main monitor and said two things, verbatim:
1. "stages have no ledges in our transitions"
2. "We need stages to be dynamic"
A verification lane is also running your native test plan; its evidence so far is under
`_build/audit-20261003/stage-switch/r2/` (`coll*/`, `trans*/`, `state/`, `mem/`).

## Part 1: ledges (a defect; fix first)
After a switch no ledge can be grabbed on the destination stage. Your reader stores per line
`lo = (flags&1 ? LINE_FLAG_PLATFORM : 0) | (flags&2 ? LINE_FLAG_LEDGE : 0)` (`pc/gameworld/script_stage_slots.inc` ~262) from
`Script_StageSlotMissionInput(1,i,5)`, and installs with `4|platform?1|ledge?2` (~392). The game's ledge search reads
`lo_flags & LINE_FLAG_LEDGE` (`melee/src/melee/mp/mplib.c` ~3364, `LINE_FLAG_LEDGE` = 1<<9 in `mp/forward.h`). Find where
the flag is lost: the native reader's mapping of the DAT's own flag bits to your 1/2 scalars; the script-line install path
dropping the ledge bit (compare `script_game.c` ~785 `ml->lo_flags`); whether ledge grabbing also needs the line adjacency
(`prev/next`), the vertex ordering, the line's joint/group being marked, or bounding data that the script install does not
set; and whether your post-switch fighter clearing leaves `ledge_id`/skip fields in a state that blocks every grab. Prove
with a fixture built from Battlefield's and Yoshi's Story's real line data (ledge lines present with the flag, and the
ledge search returning them), and say what the tester should measure (a ledge grab on each side of each legal stage).

## Part 2: dynamic stages (the owner's requirement; phased, each phase usable)
Today a slot is static data: models in a rest pose and rest-pose collision; no stage code runs. The owner needs the
destination stage to behave like the real stage: Randall the cloud and the Shy Guys on Yoshi's Story, the Whispy wind on
Dream Land, Fountain of Dreams' moving platforms and reflections, Pokemon Stadium's transformations, animated backgrounds,
moving collision. Read the feasibility note `_research/seamless-stage-switch-2026-10-03.md` (designs B and C, the load path,
what holds references, `Ground_TTMod_BuildCollData` in `gr/ground.c` ~690-806) and the stage code itself
(`melee/src/melee/gr/ground.c`, `stage.c`, the per-stage `gr*.c` init/callback tables: how each map GObj is created, its
per-frame callback, how it moves collision joints, spawns stage items, and what global `stage_info` state it uses).
Design it so each phase adds real behaviour without redoing the previous one, and say honestly where a phase cannot be
done safely:
- **Phase A, animation**: stage models in a slot play their own joint, material and texture animations (backgrounds
  move, platforms animate), driven from the DAT's animation data the way the stage's own display code does.
- **Phase B, moving collision**: collision lines attached to animated joints follow them (the game's collision joints and
  their transform update: find the mechanism and reuse it for slot collision), so moving platforms carry fighters.
- **Phase C, the stage's own code**: run the destination stage's real initialisation and per-frame callbacks for a slot, so
  its behaviour is the game's own rather than a re-implementation. Establish what that requires: the stage module assumes
  one active stage (`stage_info`, the map GObj tables, the item and effect hooks, blast/camera data, the heap it allocates
  from). Choose between (i) a true in-match re-initialisation at the switch (tear down the current Ground and run the
  destination's normal init behind the transition, with fighters benched: design B) and (ii) context switching of the
  single-stage state between slots (design C); justify the choice from the code, with the memory and teardown facts. Deliver
  the legal stages first (Final Destination, Battlefield, Yoshi's Story, Dream Land, Fountain of Dreams, Pokemon Stadium),
  each listed with what now behaves like the original and what does not.
- **Hazards and stage items** spawned by stage code must be cleaned up at the next switch and must not leak into the
  following stage; stage-owned music and sound effects follow the active stage.
- m-ex stages from mod discs: their stage code is PowerPC guest code run through the m-ex layer; say what Phase C means for
  them and do what is contained.
- Keep the Lua API unchanged (`gd.stage_slot_load`, `gd.stage_switch`, the queue); add an option per slot
  (`dynamic=true|false`, default true where supported) and report per stage which level it reached.
- Offline in this packet; state precisely what a snapshot-contained, netplay-safe version needs (stage state inside the
  rollback snapshot) so it can be planned.
Tests: fixtures for animated-joint collision following its joint, slot teardown leaving no stage GObjs or items, the
single-stage state being restored exactly, plus what can only be judged on screen. Add a demo to the demo catalogue rule:
extend `melee/pc/scripts/examples/stage_switch_demo/` so it shows a dynamic stage (Yoshi's Story with Randall) once Phase C
reaches it.
Report `_build/tmp/codex-stage-switch-fix2-report.md`: the ledge cause in three lines; the Phase C design decision and why;
per legal stage a table of behaviours (works / static / missing); file:line; unverified items; and an on-screen test plan.
If Phase C proves too large for one pass, deliver Part 1 and Phases A and B complete and Phase C as a concrete, costed plan
with the first stage implemented as proof.

## ADDED (owner, watching the demo): "CPU is not standing still btw"
A CPU put in `gd.cpu_mode(port,"stand")` starts acting again after a stage switch (the same class of bug as bench/call and
respawn re-arming the AI, fixed earlier in `script_fighter_bench.inc` and `ScriptGame_CpuMode` for both halves of
Zelda/Sheik). The switch's fighter placement must preserve the script-selected CPU mode for every entity of every slot, and
a respawn after a switch must too. Add a fixture, and tell the tester to log a stood CPU's position across ten switches.
