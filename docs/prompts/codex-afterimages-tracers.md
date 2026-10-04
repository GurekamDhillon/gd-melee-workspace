# Codex packet FX1: fighter afterimages and limb/weapon tracers (engine) (2026-10-04)

Workspace root is two levels above this file; game checkout `melee/`. Read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `docs/shaders.md`, `docs/scripting.md`, `docs/profiling.md`. Both trees are deliberately
dirty: no commits, no `tools/port/build.sh`, no game launch, keep every file compilable at every save. Do not stop for
design approval (the owner said "go, queue it on codex"); record your choices in the report. You have just finished
EM3 (loot and the full pool): build on that state; do not change how the modifier engine plays.

## Why
The owner: "There was a plan to add after images and tracers to characters, did we ever build that." It was planned
(`docs/EFFECTS-LAB-PLAN.md`, "expanded visual vocabulary": fighter afterimages, movement/weapon tracers and ribbons) and
never built; `docs/shaders.md` says "history afterimages ... are not implemented", and the Haste look in the Envoy
modifier display is only streaks on the fighter's own surface. The owner also asked "when do we get cooler effects on
everything?". These two capabilities are what a later look pass (done by an agent that can see the screen) will use,
so this packet builds the ENGINE capabilities, general and data-driven, plus correct first uses; it does not need to
make them beautiful.

## Build
1. **Afterimages (pose history).** For any fighter entity (six slots, sub-fighters, CPU opponents): keep a short ring of
   past poses and redraw the fighter at them as fading copies behind the live fighter.
   - Find the cheapest correct way in this renderer to draw a fighter again at an earlier pose: capturing the skinned
     joint matrices (and visibility, costume, model-part and held-item state) per logic frame and replaying the
     fighter's display lists with them, versus capturing the draw output, versus an off-screen accumulation. Say which
     you chose and why; it must look right through animation, turning, size changes and metal, and must never show a
     copy in the wrong costume or with a missing part.
   - Parameters per emitter: number of copies, spacing in frames, lifetime, fade curve, tint and blend (additive or
     alpha), a surface shader for the copies (reusing the surface shader system so a copy can be a flat silhouette, a
     gradient, or the fighter's own look), scale, whether copies are world-anchored (left behind) or follow, and a
     trigger mode (always, while moving faster than a speed, while a script flag is set).
   - API: `gd.afterimage_add(port, {...})` -> handle, `gd.afterimage_set`, `gd.afterimage_remove`, capacity stated;
     cleared on KO respawn only if the script says so, always on scene change and when the owning script unloads.
2. **Tracers (ribbons from moving points).** A ribbon generated each frame between a point's current and recent
   positions: anchors are a fighter joint by name or index (hand, foot, head, tail), a hitbox's centre while it is
   active (so a tracer follows the attacking limb without knowing the fighter), a held item, a sword tip (see the
   retail sword trail the script layer already exposes as a flag: learn from it, do not replace it), or a standalone
   item or projectile. Parameters: width and taper, length in frames, colour gradient along and across, a small library
   of ribbon shaders (solid, glow, fire, electric, frost, dark) with parameters, additive or alpha, sub-frame smoothing
   so a fast swing is a smooth arc rather than a polyline, depth behaviour consistent with the fixed custom-effects
   depth rules. API: `gd.tracer_add{port=, anchor=, ...}` -> handle, `gd.tracer_set`, `gd.tracer_remove`, plus
   "tracers on active hitboxes of this fighter, coloured by the hit's element" as a single call.
3. **Shared rules.** Deterministic and presentation-only: nothing here may affect simulation; state the snapshot story
   (history is either in the rewind journal or rebuilt, and a rewind must not leave stale copies or ribbons); correct
   under pause, frame advance, slow motion and hitlag (define what a copy does during hitlag); pipelines declared to
   `gd.warm` so nothing compiles in play; a frame budget measured with the profiler for the worst case (six fighters,
   each with afterimages and two tracers) against the 120 fps target, with hard caps and graceful degradation;
   an intensity setting and safe limits; offline and online both allowed since it is presentation-only, unless you find
   a reason it cannot be: say so.
4. **First uses, wired as data in the Envoy modifier display (`visual` records), no new art:** Haste = real afterimages
   while moving; Momentum = a tracer on the feet that brightens per stack; converted hits = a tracer on the active
   hitbox in the hit's element (fire arc on a converted smash, electric on Charged aerials); the Aerialist keystone (if
   it exists after EM3) = trails on air jumps; a big launch = afterimages on the launched fighter for the flight.
   Respect the readability rules of the spec (section 8b).
5. Catalogue demos (project rule): "afterimages" and "tracers", each showing the parameters live; tests in the suite
   pattern (capture and replay correctness of the pose ring, costume and part state, capacity, cleanup on unload and
   scene change, rewind leaves nothing stale, no simulation bytes change with the effects on).
   `docs/shaders.md` and `docs/scripting.md` updated.
Report `_build/tmp/codex-afterimages-tracers-report.md`: the approach chosen for redrawing a fighter and why, the APIs,
cost, whether Aurora must be rebuilt (and the carried patch), what is not possible, and a checklist for a tester who
can see the screen (what each first use should look like, and the commands to see it in the LAB).
