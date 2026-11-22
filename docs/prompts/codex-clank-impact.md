# Codex packet J: clank impact frames, a deliberately over-the-top test of the new shader system (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `docs/scripting.md`, `docs/shaders.md`). Both trees are deliberately dirty: do NOT commit,
reset, stash, revert or reformat anything. Do NOT run `tools/port/build.sh` and do NOT launch the game. Keep every file
compilable at every save. Other Codex jobs may still be editing (fighter/stage shading in Aurora and its new files; contact
events in `gw_script*`/`pc/gameworld`; menus in `gm/gmfrontend*`): NEW files wherever possible; shared-file edits last, small,
after re-reading the file. Credit any outside technique or reference in the mod's README and `CREDITS.md`; consult, never copy.

## The owner's ask (verbatim)
"as a super basic test implementation of something, can we make two attacks that cancel each other (clanks) make crazy over
engineered anime impact frames during hitlag/stun?"

It is the first real consumer of packet G's work: read `_build/tmp/codex-shaders-report.md` and use ITS API (shaders as data,
full-screen passes `gd.post_*`) exactly as delivered; if something you need is missing there, report it instead of working
around it in the renderer.

## Build
1. **Engine: a clank event.** Find where the game resolves two hitboxes colliding and cancelling (the hitbox-versus-hitbox
   path in `melee/src/melee/ft/ftcoll.c` / `lb/lbcollision.c` that leads to `ftCo_MS_ReboundStop`/`ftCo_MS_Rebound`
   (`ft/kinds/ftCommon/ftCo_Rebound.c`), and the aerial case that only applies hitlag without a rebound; also fighter hitbox
   versus item/projectile hitbox). Add a script event `on_clank` (follow how the existing events such as `on_enemy_hit` are
   produced and dispatched in `gw_script.c`; mind the producer/dispatch case numbering, a past bug) carrying: both ports (or
   port + item), the world position of the contact (midpoint of the two hitboxes), each side's damage, whether a rebound
   follows, and the hitlag frames each side will take. Read-only: producing the event must not change the game's outcome.
   Headless test with the suite's fixtures.
2. **A sample mod `melee/pc/scripts/examples/clank_impact/`** (one folder, vanilla disc, offline; README) that on `on_clank`
   plays a short, timed, layered sequence for the duration of the clank's hitlag (optionally lengthened: a tunable
   `extra_freeze_frames`, default small, implemented with whatever existing offline freeze/hitlag API there is: check
   `docs/scripting.md`; if none exists, do not invent state changes: leave it at the natural hitlag and say so):
   - frame 1-2: full-screen "impact frame": the scene reduced to hard two-tone (luminance threshold) and colour-inverted,
     optionally with fighters as stark silhouettes (use depth; use object ids only if packet H's buffer exists, otherwise
     depth-edge), a white flash keyed to the contact point;
   - then: radial speed lines and a radial blur centred on the contact point projected to screen space, chromatic
     aberration that decays, a shockwave ring distortion expanding from the point, heavy contrast/saturation push, film
     grain, a brief letterbox, screen shake as a UV offset (visual only, not the game camera);
   - an easing envelope so it punches in and decays cleanly, never leaving a pass installed after it ends.
   Every parameter in one tuning table at the top (durations, intensities, colours, which layers are on), with three presets:
   `subtle`, `anime`, `absurd` (default `anime`); console commands `clank preset <name>`, `clank test` (fires the sequence at
   screen centre without a clank, so it can be seen and tuned without a second player), `clank off`.
   Scale intensity by the combined damage of the two attacks so jabs are small and smash-versus-smash is huge.
   Photosensitivity: a `flash_limit` option (default ON) that caps full-screen luminance change per frame and replaces the
   inverted white flash with a darker variant; state the numbers used.
3. WGSL for each layer as separate small pass files in the mod (`shaders/*.wgsl`), written against packet G's contract.
4. Offline tests for the Lua (sequence timing, envelope, cleanup when the match ends mid-sequence, presets, intensity
   scaling, that nothing is installed when no clank is active) with a stub `gd`; `luac -p` on every Lua file.

## Constraints
Visual only apart from the optional tunable extra freeze; never online; zero cost when no clank is active; a failed shader
compile disables that layer with one log line and the rest still play; state each pass's cost against the 120 fps target.

## Report
`_build/tmp/codex-clank-impact-report.md`: where the clank is detected (file:line) and each case covered or not (ground
rebound, aerial, projectile), the event's fields, the layers and their parameters, tests, what can only be judged on screen,
and an exact test plan for the integrator (`clank test`, then a real clank: which two attacks on which characters reliably
clank on Final Destination).

## ADDED: the owner's reference for the look (this is the target; it overrides the layer list above where they differ)
The owner supplied a toy HLSL shader for "the kind of impact frame im looking for":
`docs/prompts/reference/owner-impact-frame.hlsl` (the owner's own text: use it freely). Port it to WGSL against packet G's
full-screen pass contract as the `anime` preset's main pass, keeping its five ideas and their order:
1. a shockwave ring that pushes pixels outward, with chromatic aberration on the scene sample;
2. the scene crushed to hard black below a luminance threshold, and INVERTED inside the ring early in the impact;
3. jagged procedural lightning streaks radiating from the impact centre (two layered seeds, sharpened to thin hard-edged
   bands, fading with distance and time), coloured from a streak colour to a hot core colour;
4. a dark, noisy ink-splatter blob at the epicentre that shrinks as the impact progresses;
5. composite: crushed scene, ink, then lightning added on top as emission.
Inputs map as: `_ImpactCenter` = the clank's world contact point projected to screen UV each frame; `_ImpactProgress` = 0..1
over the sequence; `_ShockwaveRadius` = animated from 0 outward by the envelope; `_Time`; `_LightningColor` and `_CoreColor`
as tunables (defaults vivid red and deep purple/gold as the comments suggest; optionally tinted per fighter or by damage).
Fix these while porting, and say so in the README (they are defects of a toy, not style choices):
- distances are computed in raw UV, so at 16:9 and 21:9 the ring and blob are ellipses: correct by the aspect ratio so they
  are round at every window shape;
- `atan2` has a seam at +/-pi, so the angle-based noise shows a hard line to the left of the centre: make the noise periodic
  in angle (sample noise on a circle, e.g. from `cos/sin(angle)`, or blend across the seam);
- WGSL forbids implicit-derivative `textureSample` in non-uniform control flow: sample before branching or use
  `textureSampleLevel`;
- the fixed 0.005 aberration offset and 0.1 ring width should scale with resolution/aspect and with the damage-based
  intensity;
- the inversion is a full-screen luminance flip: under `flash_limit` (default ON) keep the crushed blacks and the lightning
  but replace the inversion with a darker treatment and cap per-frame luminance change.
The other layers already listed (speed lines, grain, letterbox, UV shake, radial blur) become optional extras stacked on this
pass in the `absurd` preset; `subtle` is this pass at low intensity without inversion. `clank test` must show exactly this.

## ADDED LATER: the owner's second, better reference. THIS is the primary target; the HLSL above is the earlier sketch.
`docs/prompts/reference/owner-impact-frame-v3.html` (a WebGL page the owner supplied: "another example generation for
shaders"; the owner's own text, use it freely; open it in a browser to see it move: mouse moves the centre, click refires).
Its GLSL fragment shader (`FS`, about 270 lines) is the look to reproduce as the `anime` preset. Port it faithfully to WGSL
against packet G's full-screen pass contract, layer for layer:
- narrow violent pressure ring with radial + tangential displacement; short-lived directional RGB split along the radial;
- four-band poster thresholding of the scene (black / 0.32 / 0.72 / boosted);
- central black void with a jagged noisy perimeter that shrinks with progress;
- 18 blade-like radial shards (`spike`); 12 deterministic jagged polyline lightning bolts (`bolt`: 9 segments, white knife
  core + coloured sheath, manga-style intermittent cuts, forks on segments 2/5/7, flicker), red/magenta by angle;
- radial razor cracks gated to the ring; a broken, sectored shockwave ring plus a second inner ring; dark sheaths around bolts;
- an initial white 8-point star "frame tear" and inverted wedge cuts in the first frames; hard vignette, grain, final crush.
Its `scene()` function is only the demo's stand-in background: replace it with the real scene colour input (three samples for
the RGB split, taken before any branching). `u_center` = the clank's contact point projected to screen (GL's origin is
bottom-left, ours may be top-left: get the Y right); `u_progress` 0..1 over the sequence; `u_time` in seconds.
Fix while porting and note in the README:
- all distances use raw UV, so on a non-square screen everything is elliptical: do the geometry in aspect-corrected space
  (the demo only corrects inside `scene()`), so rings, void, star and bolts are round/isotropic at 4:3, 16:9 and 21:9;
- `atan` seam at +/-pi shows in `edgeNoise` (angle*13) and the angle-keyed colour pick: make them continuous around the circle;
- cost: per pixel this is ~108 segment distances for bolts plus forks, 18 shards, 14 cracks and 8 star spikes. Measure it at
  1080p and 4K against the 120 fps target; cull by radius/bounding region, and render the additive energy layers at half
  resolution if needed, keeping the knife-edge cores sharp. State the measured or estimated cost;
- loops must have constant bounds (WGSL is fine with that); no `#define`, use `const`;
- `flash_limit` (default ON): keep everything except the white star flash and the inverted wedges, which get the darker
  capped variant.
Timing: the demo runs 1.18 s. A clank's hitlag is only a few frames. Default behaviour: start on the clank, hold the first
"frame tear" beat during the real hitlag, and let the remaining sequence play out over resumed gameplay (visual only), with
total length scaled by combined damage between about 0.35 s (jab vs jab) and 1.2 s (smash vs smash). The optional
`extra_freeze_frames` tunable (offline) extends the freeze instead; keep it default small/zero.

## FINAL SCOPE (owner, 2026-10-03): "this is just an experiment we will not continue to use in the game anywhere, just show it off to me"
This overrides everything above where they conflict. It is a throwaway demo, so cut it down:
- NO engine changes at all. Drop the `on_clank` engine event. Detect a clank in Lua: two fighters entering the rebound
  states (`ftCo_MS_ReboundStop` 237 / `ftCo_MS_Rebound` 238; confirm the ids and how `gd.player` exposes the action state)
  on the same frame or within a frame of each other; impact centre = midpoint between the two fighters (use hitbox positions
  from `gd.hitboxes` if that is easy, otherwise fighter positions at chest height), projected to screen with the existing
  camera API. Aerial and projectile clanks are out of scope; say so in the README.
- Put it OUTSIDE the shipped examples: `experiment/clank_impact/` in the workspace repo (one mod folder: `mod.json`,
  `scripts/main.lua`, `shaders/impact.wgsl`, `README.md` saying it is a throwaway demo and crediting the owner's reference).
  Nothing in `melee/` is edited. No `CREDITS.md` or `docs/` changes.
- One look only: the v3 reference, ported faithfully, with the porting fixes listed above (aspect, seam, scene input, Y
  origin, constant loops). No presets, no damage scaling tables beyond one intensity scalar.
- Timing for the demo: FREEZE the game for the sequence so it reads like the reference (use the existing offline
  freeze/pause/frame-step API from `docs/scripting.md`; if there is none usable from Lua, fall back to playing the sequence
  over live gameplay and say so). Sequence length 1.18 s as in the reference, one tunable at the top of the file.
- Flash limiter: keep it as a single toggle at the top, default OFF (the owner wants their reference shown as written, on
  their own screen); one console command `clank flash_limit on` turns it on.
- Console: `clank test` fires it at screen centre with no clank needed; `clank off` disables the mod's effect.
- Tests: only a small stub test of the detection and of cleanup when the match ends mid-sequence, plus `luac -p`.
- Still required: never crash on a shader compile failure (log one line, do nothing), remove the pass when the sequence
  ends, and state the measured or estimated per-frame cost.
Report as before, short, with the exact steps to show it: which two characters and attacks clank reliably on Final
Destination, and the `clank test` command.

## CORRECTION TO "FINAL SCOPE" (owner, 2026-10-03): "woah I still want the engine changes and features and capabilities, this example wont be developed further so dont ask me to make any decisions about it"
The integrator over-cut. The EXAMPLE is throwaway; the ENGINE capabilities it exercises are wanted and permanent. So:
- RESTORE section 1 in full: the engine `on_clank` script event (ground rebound, aerial clank with hitlag only, fighter
  hitbox versus item/projectile hitbox), with both ports or port + item, the world contact point (midpoint of the two
  colliding hitboxes), each side's damage, whether a rebound follows, hitlag frames; read-only; headless test; documented in
  `docs/scripting.md`. Credit entries where due.
- ADD whatever general capability the example needs and the engine lacks, as real, documented, tested API rather than
  example-local hacks, and list each in the report. Expected: world-to-screen projection for a point usable as a shader
  parameter each frame (`gd.world_to_screen(x,y,z)` if nothing equivalent exists); an offline visual freeze/hitstop request
  from Lua with a duration (`gd.hitstop(frames)` or the existing equivalent), refused online; a per-pass time/progress
  parameter convention for `gd.post_*`; pass lifetime helpers (auto-remove after N frames). If packet G's full-screen pass
  system is missing something a real effect needs (half-resolution layers, multiple inputs, ordering), extend it properly
  and coordinate in `docs/shaders.md`.
- The example mod itself stays as scoped in "FINAL SCOPE": one look (the v3 reference), in `experiment/clank_impact/`,
  freeze for the 1.18 s sequence, flash limiter toggle default OFF, `clank test`, minimal tests; but it now uses the engine
  `on_clank` event (with the Lua rebound-state detection kept only as a fallback if the event is unavailable).
- Make every remaining choice about the example yourself and note it in the README. Do not leave questions for the owner.
