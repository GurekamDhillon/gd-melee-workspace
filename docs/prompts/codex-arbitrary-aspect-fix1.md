# Packet D follow-up 4: arbitrary aspect after the first run in the game (2026-10-03)

Same rules. Verified on the stamped build: a shield bubble measures round (0.976-0.978 by the tester's mask method) at
4:3, 16:9, 2.25:1 and in the letterboxed narrow window; black bars with the logged rectangle outside the supported range
and with widescreen off; 16:9 matches the previous build; the magnifier bubble is round; live resize logs one line per
change; kit character select centred at 2.25:1. Evidence: `_build/audit-20261003/batch2-verify/shots/` (`asp-*`, `cullD-225.png`,
`diff_169.png`).
1. **A black wedge covers part of the stage floor at some window shapes only**: black pixels in the floor band are
   0.02-0.03% at aspect 1.333, 1.5, 1.778 and 2.25, but 18-21% at 1.6, 1.707 and 1.901 (windows 1024x640, 960x600,
   1024x600, 1080x568), deterministic across reruns. Screenshot `shots/asp-1610/asp_a.png` (Final Destination, fixed
   camera z=80 fov 30). Not root-caused; the tester suspects the live projection (`sysdolphin/baselib/cobj.c` ~495) or stage
   frustum/portal culling using a stale or table-driven aspect that only has entries near the classic values. Find it:
   what differs for those aspects (a lookup or branch keyed on aspect; a clip plane or scissor computed from the 4:3 or
   16:9 constants; a stage background layer drawn with its own camera that was not widened; a depth/near-plane issue), fix
   it for every aspect in the supported range, and add a test over a dense sweep of aspects (4:3 to 32:9 in small steps)
   for whatever quantity was wrong.
2. HUD at wide aspects is a centred authored block with empty space on both sides (your stated policy): keep, but make the
   six-fighter HUD (another job is enabling six percent groups) fit that block.
3. Not yet checked by anyone: native Rules and Name Entry at wide windows, and the Widescreen row toggle with the new
   presenter: re-read your own paths for those and list anything you now doubt.
Report `_build/tmp/codex-arbitrary-aspect-fix1-report.md` with the cause of item 1 in three lines.

## ADDED LATER (integrator review, 2026-10-03): keep port changes in decomp files under the PC guard
`melee/src/melee/gr/grizumi.c` ~783: `HSD_CObjSetAspect(dst, HSD_CObjGetAspect(src))` was changed in place to
`HSD_CObjGetAuthoredAspect(src)`. That file is upstream decompiled code: project rule (`melee/CLAUDE.md`, Conventions) is
that port additions in such files stay under `#if defined(TARGET_PC)` with the original line kept for other targets.
Audit EVERY change your aspect work made in files under `melee/src/` (not `melee/pc/`): list them, and put each under the
guard with the original preserved. Reply with the list.
