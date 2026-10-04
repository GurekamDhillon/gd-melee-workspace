# Packet M follow-up: six-fighter matches after the first run in the game (2026-10-03)

Same rules (no commits/reset, no build, no game launch, keep files compilable; other Codex jobs are in `melee/pc/geno/`,
`pc/gameworld/script_stage_slots*`, `gw_script_items.inc`, the watchdog files). Verified in the game on the stamped build:
six fighters in LAB and direct VS, all visible, camera frames all six, every port API works on slots 5-6 (cpu_mode,
teleport, fighter_mod, bench/call, scripted input and release), KO and respawn, five different heavy characters admitted,
p5 human and CSS/Training routes refused cleanly, a wave of 12 through 3 slots by recycling, LAB restart, savestate and a
rewind test with 0 differing bytes. Evidence: `_build/audit-20261003/batch2-verify/` (`shots/`, `patches/`).
Fix, each with a test:
1. **The HUD shows only four percents with six fighters**: slots 5 and 6 have no percent or icon. Cause as traced by the
   tester: `melee/src/melee/gm/gm_1601.c:3691` sets `rules->x0_3 = 4` and the six-slot seeder
   (`gm/gmscenelaunch.h` ~219) never raises it; the HUD builder picks its layout from that value (`if/ifall.c:79`,
   `gm/gmvs.c` ~2330/2423/2445). Proposed diff `patches/05-six-slot-hud-count.diff`; the value may be rewritten at match
   start, so confirm where it must be set. Then check from the code that six percent groups fit the HUD anchors without
   overlap at 4:3 and wide aspects, and say what the tester should look at.
2. **The memory admission log prints the empty-budget numbers** (`files=0`, headroom equal to capacity): it is not an
   after-load measurement, so nothing is ever refused. Make the check use the real requests of the launch set and log the
   headroom after the fighter files are loaded; add a test where an oversized set is refused cleanly.
3. `p7=` is ignored silently: log a refusal. `gd.lab_leave("css"|"sss")` with six returns `true,false` with no reason:
   return and log the reason.
4. In team matches one duplicate (the fifth slot) is drawn paler than the others: establish from the code whether that is
   the game's own same-team duplicate shading (`gm_1B03.c` bumps the sub colour for same team + same character) and whether
   our launch passes through it; document what a six-slot team launch does to colours and add an option to force team
   costume colours for the enemy team if the game supports it for five members.
Report `_build/tmp/codex-six-slots-fix1-report.md`.
