# Stage lifecycle follow-up 1: the owner played ten switches (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md` (other jobs are still running: the afterimage fix owns the motion and
Aurora motion files). You own what your packet P3 named. No build, no game launch, no commits.

The integrator built your P3 work and smoke-tested six switches (FD, Battlefield, Yoshi's Story, round twice: each
logged `stage switch: complete retail visit`, music changed, no crash or hang). The owner then played ten switches on
the main monitor (`_build/runs/stage-play1/melee-pc.log`) and said, verbatim: "Stage switching feels great, but there
is some different lighting/shading on characters. Also seems like characters get teleported to "safe positions"
occasionally, but its too often."

So the lifecycle is right. Two things are not vanilla:

1. **Fighter lighting/shading differs after a switch.** In a normal match on a stage the fighters are lit by that
   stage's own light set-up (the stage's LObjs / ambient / the per-stage light and colour data the fighter draw uses,
   plus any stage fog colour that tints them). After a switch the fighters look lit differently from a normal match on
   the destination stage. Find every piece of lighting state a fighter's draw depends on (the lights bound when
   fighters render, the fighter light gobj and how each stage configures it, ambient colour, the colour overlays and
   the stage-supplied values the fighter material path reads, fog) and where retail sets each at match start for a
   stage; then make a switch leave ALL of it exactly as a fresh match on the destination would, and nothing left over
   from the source stage or from the transition's cover/flash/morph. Watch for: the lights captured or created before
   the stage's init and never rebuilt; the transition post pass leaving a tint; the fighter's own cached light state.
   Add a fixture that compares the full lighting state after a switch with the state after a fresh match start on the
   same stage, field by field, for every supported stage, and list the fields in the report.
2. **Fighters are moved to "safe positions" too often.** The carry rule teleports whenever a grounded fighter has no
   new floor or a fighter is outside the new bounds. The owner wants a switch to feel continuous. New rule, in order:
   - An AIRBORNE fighter keeps its exact position, velocity and state: never moved, unless it is outside the new blast
     zones, and then it is clamped just inside the nearest boundary rather than sent to a spawn point.
   - A GROUNDED fighter stays at its X and is placed on the destination's floor at that X if there is one within a
     generous vertical range (state it; the main floors of the supported stages differ in height and shape, so "the
     floor directly above or below within the stage's height" should count), keeping its action; this is a small
     vertical correction, not a teleport, and it must not play a landing or a respawn.
   - If there is no floor under that X (off the edge of the new stage), the fighter simply becomes airborne where it is
     and falls or recovers as it would have walking off an edge. No teleport.
   - On a platform that does not exist on the new stage: treated as grounded-with-no-floor above: fall.
   - Ledge hangers: already detached; they follow the airborne rule.
   - Only when a position is genuinely unusable (inside solid geometry with no way out, or outside the blast zones by
     more than the clamp can fix) use a spawn point, and log it with the reason so it is rare and explainable.
   Log one line per fighter per switch saying which rule applied. A fixture runs each rule for each pair of supported
   stages and asserts that the spawn-point fallback is not used for any position that is in open air or over floor.
3. The same play log has `stage switch: fighter is captured, thrown, dead or respawning; retry later` once: confirm the
   queued switch really is retried by itself shortly after and not dropped, and that the demo's loop does not stall on it.
4. Add Dream Land and Fountain of Dreams to the demo's rotation (five stages), each transition used at least once.
Tests for each; report `_build/tmp/codex-stage-teardown-fix1-report.md`: the lighting fields and where retail sets
them, the carry table, and a side-by-side checklist the owner can use (what to compare on each stage).
