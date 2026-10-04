# Packet B follow-up 8: mission clear, lost enemies, a death on load (2026-10-03)

Same rules (Lua/Python, your files, no build, no game, no commits). The staged install works in the game (15 logged steps,
player at 0%, CPU benched, three camera cuts in total, two blast writes).
1. **`mission clear` loops forever on a ReDead.** Under continuous `gd.fly_attack` the ReDead goes to a state with
   `vulnerable=false`, its damage counter climbs (3, 24 ... 638+) but it never dies, because being hit every frame
   re-applies hitlag and its death logic never runs; a real player kills it in about 437 frames with normal attacks, and
   PULSING the debug hitbox (on 28 frames, off 12) kills it in about 420. `commands.lua` ~64-76 has no per-target budget
   (only the wait for a controllable P1 times out), so the command restarts every 600 frames for ever; the owner watched it
   sit there. Give each target a budget and an escalation (pulse the attack; move the cursor; after the budget, log
   `clear: <kind> not defeated after N frames (state X, vulnerable=false)` and move on or fail the command), and open a
   script deadline around the whole clear (`gd.deadline`, guarded for absence). Evidence
   `_build/audit-20261003/envoy-verify2/patches/11-missions-clear-per-target-timeout.diff` (untested).
2. **Enemies are sometimes lost instead of defeated** (topi and polar bear launched off-stage after contact, logged as
   `lost ... (not a defeat)`, so they drop nothing): decide the rule for an enemy that leaves the level by itself (respawn
   it at its marker once, or count it as defeated if the player damaged it), implement it, and document it.
3. **A `mission: death` is logged immediately after `loaded <level>`**, before the first checkpoint, on a clean load with the
   player at 0% and standing on the level afterwards (`_build/runs/maze-smoke5/melee-pc.log`): find what registers as a KO
   during the hand-over (the player parked outside the blast zone while staging, the host stage being hidden under them)
   and remove it; a fresh load must log no death and must not count a fall.
4. After a fly-attack tour the first `gd.fly_target` console call errors and the second works: release the cursor cleanly
   when `clear` ends.
Regenerate the bundle. Report `_build/tmp/codex-mission-runtime-fix8-report.md`.
