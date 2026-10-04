# Afterimages follow-up 1: no pose is ever captured in the game (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md` (read it again: other jobs are running). You own the afterimage and
tracer files (`melee/pc/platform/gw_fx_motion.cpp`, `gw_motion*`, `melee/extern/aurora/lib/gx/motion_capture.hpp`,
`include/aurora/motion.hpp`, the carried Aurora patch, `pc/gameworld/script_motion*`, the two demos). No build, no game
launch, no commits. The integrator will rebuild Aurora and the game and test.

The owner looked at both demos: "Im seeing tracers, but im not sure im seeing after images at all". Tracers work.
Afterimages draw nothing. The integrator built and probed it (stamped-equivalent build, vanilla disc, LAB, Fox on FD,
the afterimages demo, intensity 1, trigger always, six copies):

1. FIXED by the integrator, keep it: `pc/gameworld/script_motion_draw.h` compared the current camera with
   `cm_804D6464`. Camera creation (`src/melee/cm/camera.c` ~4318-4326) makes TWO cobjs from the same descriptor: one is
   attached to the camera gobj and is the one current while fighters draw; `cm_804D6464` is a separate copy. The test
   was always false, so `MotionFighterBegin` was never called (`poses=0, skipped=0`). It now compares with a new
   `Camera_PCMainCObj()` (camera.c, TARGET_PC). Check the tracer world-draw path and any other place for the same
   assumption.
2. NOT fixed, yours: with that gate open, capture begins every frame and `aurora::gx::motion::end()` returns no pose
   every time. Probe output (the integrator left three rate-limited `motion: probe ...` log lines in
   `gw_fx_motion.cpp`; keep or replace them with proper counters):
   ```
   motion: probe begin replaying=0 trigger=1 hitlag=0 intensity=0.65 latest=-1 frame=949 copies=6
   motion: probe end pose=0 draws=-1 bytes=-1
   gd.motion_stats(): skipped=5307 poses=0 copy_draws=0 afterimages=1   (after ~30 s, warm-up long finished)
   ```
   `motion_capture.hpp` marks a capture failed for: no pipeline for the motion variant ("no compilation requested in
   play", ~53), arena copy failure (~56), a pinned copy-texture (~63), an index array not cached (~80), palette (~81),
   fog range enabled (~82), more than 2048 draws or over the byte budget (~85). One of these is true for an ordinary
   fighter on Final Destination every frame. Find which by reasoning from the code, and make it diagnosable in one run:
   - Count each failure reason separately and expose the counts in `gd.motion_stats()` (and one log line the first time
     each reason occurs, naming the reason and the fighter), so the next probe names the cause outright.
   - Then fix the likely causes rather than only reporting: the demo calls `gd.warm{fighters={1}}` and waits for
     `gd.warm_done` before raising intensity: confirm that warm-up really builds the MOTION variant pipelines for that
     fighter's materials (the fighter draws through a surface program path: `SurfaceBegin(port)` wraps the draw in
     `ftdrawcommon.c`; a pipeline keyed on the surface program or blend that warm-up did not request would fail every
     draw); fog on a stage is common, so "reject the pose when fog range is enabled" would disable afterimages on many
     stages: handle fog properly (capture the LUT, or draw copies without fog) instead of rejecting; same for the
     palette and copy-texture cases where a correct fallback exists (a silhouette copy needs no textures at all:
     `surface="silhouette"` should be capturable whenever geometry is).
3. Defaults were invisible to the owner ("I cant really tell the difference between different settings ... they need
   to be exagerated"). The integrator rewrote both demos with extreme defaults and wider key ranges: keep that; raise
   the hard caps where they limit a clearly visible effect (copies 6 -> 12, lifetime 31 -> 60, tracer width and length)
   if the budget allows, and say what you changed.
4. Held items: an afterimage of a fighter holding an item currently clears the history and skips. Retain the held item's
   draws as part of the same pose so the copy is whole.
Tests for the failure counters and each fallback. Report `_build/tmp/codex-afterimages-fix1-report.md`: the cause you
believe is the one, the counters added, what the integrator must rebuild (Aurora and the patch), and exactly what a
probe should print when it works.
