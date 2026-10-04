# Packet D follow-up 3: arbitrary aspect ratios, with black bars as the fallback (2026-10-03)

Same rules as your earlier packets (no commits/reset, no build, no game launch, keep every file compilable). Another Codex job
is editing `melee/pc/platform/gw_runtime.c` and `melee/src/melee/gm/gmscenelaunch.h` (six-slot matches), and a profiler job
will follow it in `gw_script*`, `gw_snap.c`, `gw_rollback.c`: stay out of those. Credits for the widescreen mechanism are in
`DEPENDENCIES.md` and `_research/widescreen.md`: keep them intact.

## The owner's report (verbatim)
"we also need to renable blackbars when a window cant be set to a "real" aspect ratio, or we need arbitrary aspect ratio
support."

## What is true today (verify)
- The 3D cameras are widened by a FIXED factor: `melee/src/sysdolphin/baselib/cobj.c` ~1301 scales the perspective aspect by
  320/219, which is exactly 16:9, whatever the window is.
- With widescreen on, the presenter stretches the frame to the window: `melee/pc/platform/shim_vi.c` ~1794
  `AuroraSetViewportPolicy(ws ? AURORA_VIEWPORT_STRETCH : AURORA_VIEWPORT_FIT)`.
- So at any wide window that is not 16:9 (21:9, 16:10, 3:2, a freely resized window) the 3D scene and HUD are stretched or
  squashed, while your kit menus are correct because they use the real view aspect (`gw_View_Aspect`, `shim_vi.c` ~65).
  The earlier on-screen checks measured the menus at 4:3, 16:9 and ~2.25:1 and they were round; the 3D scene was only judged
  at 16:9.

## Build: arbitrary aspect support first, bars only where it cannot apply
1. One source of truth: the real view aspect you already added. The perspective widening uses it (Hor+: vertical field of
   view unchanged, horizontal follows the window), replacing the fixed 320/219, for every camera the fixed factor applied
   to. Keep the 73:60 pixel-aspect handling exactly as correct as it is at 16:9 today (derive the general formula; at 16:9
   it must reduce to the current numbers bit-for-bit or within float error, and a test proves that).
2. Everything that assumed 4:3 or 16:9 follows the same aspect: culling/frustum tests (objects must not pop at the sides at
   21:9), the in-match HUD (it is currently left-anchored and not re-anchored to the wide frame: decide per the art brief
   whether percent/stock groups keep their 4:3 block centred or spread to the wide frame, and do one consistently, stating
   which), the pause camera, screen-space effects and full-screen quads (fades, flashes, the transition wipes), 2D
   world-to-screen projections used by scripts (`gd.project`, `gd.world_to_screen`), the off-screen magnifier bubbles and
   player arrows, camera bounds maths that convert world to screen, blast-zone independent, stage backgrounds/skyboxes that
   may reveal their edges when the view is wider than they were built for (list which stages show an edge at 21:9 from the
   code or data if you can tell, otherwise list it as an on-screen check).
3. Supported range and the fallback bars: support every aspect from 4:3 up to a stated maximum (propose 32:9; justify from
   what breaks first: culling, backgrounds, HUD). Outside the range, and for any screen that cannot widen (the vanilla
   native menus: Rules, Name Entry, Event Match and the other screens that pass their own camera, pre-rendered movies, the
   title sequence), present at the nearest supported aspect CENTRED WITH BLACK BARS (pillarbox or letterbox), never
   stretched: narrower than 4:3 letterboxes a 4:3 frame; wider than the maximum pillarboxes the maximum. This means the
   presenter policy is no longer "stretch when widescreen": compute the target rectangle from the scene's supported aspect
   and present it centred with bars cleared to black. Widescreen OFF keeps a 4:3 frame with pillarbox bars, as today.
4. Live: resizing the window, toggling fullscreen and toggling the Widescreen row update the 3D aspect, the kit canvas and
   the bars on the same frame, with one log line per change (aspect, target rectangle, bars).
5. Screenshots and `gd.screenshot` capture the game frame without the bars and report its size; scripts can read the
   aspect and the safe area (`gd.safe_area` already exists: make it agree).
6. A SETTINGS > VIDEO option only if needed: "Aspect: Auto / 4:3 / 16:9 / 21:9" (Auto = follow the window); do not add it
   if Auto plus the Widescreen row covers it: say which you chose and why.
Tests in the suite's pattern: the aspect-to-projection maths at 4:3, 16:10, 16:9, 21:9, 32:9 and beyond the range; the
presenter rectangle and bar sizes for a table of window sizes (including narrower than 4:3 and an odd free-resize size);
the 16:9 result identical to today's. Report `_build/tmp/codex-arbitrary-aspect-report.md` with file:line, the supported
range and why, the HUD decision, every screen that falls back to bars, and an on-screen test plan (window sizes; what to
measure: a round world-space object such as a shield bubble or Pokeball must measure 1.0 +/- 0.03 at each aspect).
