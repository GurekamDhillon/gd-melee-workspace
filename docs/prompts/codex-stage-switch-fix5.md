# Packet O follow-up 5: an engine hang at the end of a stage transition (2026-10-03)

Same rules (no commits/reset, no build, no game launch, keep files compilable). Found by the demo-catalogue lane and caught
by the new watchdog, twice, reproducibly.

When a script removes only its OWN post-process pass inside `on_stage_switch` (so the engine's transition cover stays
alive and the transition completes normally), the main thread deadlocks. The shipped stage-tour demo does not hang only
because it calls `gd.post_clear()` there, which destroys the engine's cover too and makes the engine log
`stage transition: cover update refused: post handle expired or belongs to another script` (12 times per run): that
refusal is hiding this hang.

Evidence: `_build/audit-20261003/demo-tour/hang-evidence/` and `_build/runs/dmt-i/` (`hang.txt`, `hang.dmp`,
`verdict.json` = HUNG code 86). `hang.txt`: the main thread is in `_gw_HSD_SynthPStreamStart+0x17`, `paused=2`,
`last_shim=DVDReadAsyncPrio`, `script=demo_stage_tour`, `callback=on_stage_switch`.

So: at the end of a transition, with a timed freeze (hitstop) still active, the switch starts the destination stage's
music stream; the stream start issues an asynchronous disc read and waits for it; the wait never completes because the
thing that would complete it does not run while the game is frozen/paused (or because it is being called from inside a
script callback on the game thread). This is the deadlock class `melee/CLAUDE.md` describes ("a game-side blocking spin
that calls no shim deadlocks: pump `wait_idle()` inside it") and the freeze makes it certain.

Find the exact wait (`HSD_SynthPStreamStart` and the async read completion path in the audio/DVD shims), and fix at the
root: music changes requested by a stage switch must be deferred to a point where the engine is not frozen and not inside
a script callback (queue the request and start the stream from the normal frame loop after the freeze ends), or the wait
must pump the completion; state which and why. Also make `gd.post_clear()` unable to destroy passes owned by the engine
or by other scripts (it should clear only the caller's), so a script cannot break a transition cover by accident; then
the refusal lines disappear for the right reason. Add a fixture that completes a transition with the cover alive under an
active timed freeze and asserts the main loop keeps ticking.

Report `_build/tmp/codex-stage-switch-fix5-report.md`: the cause in three lines, file:line, and how to reproduce the
before and after in the game (the tester's patched demo copy is under `_build/audit-20261003/demo-tour/fix/`).

## ADDED (owner, 2026-10-03): the standard for a switched-to stage is VANILLA, in full
The owner, after seeing that Fountain of Dreams was started with its reflection camera and particle bank skipped:
"ideallistically I want stages to look and feel like they are vanilla, aside from the transition mid-match".
So the target is not "the platforms work": it is that after the transition the stage is indistinguishable from having
started a normal match on it: everything the stage's own initialisation creates (reflections and their cameras, particle
banks and effects, background animation and its state machine, hazards, stage items, lighting and fog, sound and music,
camera behaviour, blast zones, spawn points), running the game's own code unmodified.
That rules out per-stage partial start-ups. Review what follow-up 4 added inside stage files (the guarded early-return
branch in `grIzumi_801CBE64` in `melee/src/melee/gr/grizumi.c`, and anything similar in `grstory.c` or others): the
direction is to run each stage's COMPLETE retail initialisation and teardown (your design B: one active native stage,
re-initialised behind the transition), and to make the engine able to host that, rather than to carve out the parts that
are safe to run beside another stage. Concretely:
- Make full teardown of the outgoing stage and full retail init of the incoming one work mid-match behind the transition
  (fighters benched and made safe first; everything that references stage objects cleared; the stage heap released and
  reused; the stage's particle bank, reflection camera and render passes created and destroyed with it), so no stage file
  needs a slot-specific branch. If something in a stage's init truly cannot run mid-match, say exactly what and why, and
  make that the thing to fix, not skip.
- Preloaded slots remain as cached file data for a hitch-free switch; only one stage is live at a time.
- Remove the slot-specific branches from stage files once the full path works; any change left in a decompiled stage file
  must be under the PC guard, minimal, and listed with its reason.
- Per legal stage, give a checklist against vanilla (visual and behavioural) and mark each line same / different / missing,
  so the tester can compare a switched-to stage with a normally started one side by side (same camera, screenshots and
  measured behaviour: Randall's lap time and puff, Shy Guy spawns, Whispy's wind strength and timing, Fountain's platform
  range and timing and its reflection, Stadium's transformation cycle, Battlefield's background cycle).
Do the hang fix above first (it blocks every switch with music), then this.
