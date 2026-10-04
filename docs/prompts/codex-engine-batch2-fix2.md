# Packet F follow-up 2 (2026-10-03)
Round 2 in the game on the stamped build passed everything you fixed (floor call in Wait with no sink for Fox, Ice Climbers,
Zelda; 20 cycles none refused; stand/fight preserved across bench/call; run speed held; pan; range messages; per-entity
state; transform refusal; ownership). Same rules. One defect left, not a bench regression:
`gd.cpu_mode(port,"stand")` does not keep Zelda/Sheik idle: only the active half gets CPU kind 0; the dormant half keeps its
fighting kind, and a transform swaps that half in (control run with no bench: P2 walked and transformed within 120 frames).
Root cause: `melee/pc/gameworld/script_game.c` ~2644 `ScriptGame_CpuMode` initialises only the active primary. Apply the mode
to every entity of the slot (dormant transformation half, Nana), keep it across transforms, with a fixture. Sketch:
`_build/audit-20261003/batch2-verify/patches/04-cpu-mode-zelda-sheik-partner.diff` (needs the real partner accessor).
The integrator already added a `gw_log` line for console `wait` results (`gw_script_contacts_core.inc` ~160): leave it.
Reply with the cause in two lines and file:line.
