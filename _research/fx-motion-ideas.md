# FX motion: owner ideas and findings, 2026-10-07

From the owner's first on-screen look at the FX1 v2 demos (integration build, game `29fc8bf53`).
Afterimages: accepted ("looks good"). Tracers: work, but these are the asks.

## Tracers: not enough variation (owner)

"Not enough variation. More unique changes, more variable knobs and levers." Candidates, none built:

- **Colour over the trail's length**: multi-stop gradients (not just tint -> tail), hue cycling along
  the ribbon, a rainbow mode.
- **Colour over time**: pulse, flicker, a slow hue drift; tie it to speed or to the hit's damage.
- **Shape**: width that swells mid-trail (not only taper), a jagged/lightning edge, sparkle or dash
  breaks along the ribbon, a double ribbon (core plus glow halo as separate layers).
- **Per-shader params as live knobs**: `params={strength,frequency,core_width,motion_rate}` exists
  (0..10) but the demo never changes it; expose all four.
- **Blend and depth**: additive vs alpha vs screen per trail; an option to draw over the fighter.
- **Reactive**: trail flares on hit, colour from the hit element (already for hitbox mode), length
  from the move's speed.
- **More shaders** beyond solid/glow/fire/electric/frost/dark (smoke, water, shadow, holographic).

## Afterimages: per-copy colour (owner idea)

"Afterimages could change colour each image; they don't always need to be the same colour."
Today a copy gets `tint` and fades towards `tail`. Candidates:

- a palette per copy index (rainbow ghosts, alternating two colours);
- hue rotation by copy age;
- colour from state (the move's element, the fighter's costume, damage percent);
- per-copy scale or offset (a shrinking echo), per-copy surface (silhouette near, gradient far).

## Finding: weapon swings are not traced (owner)

"Tracers don't follow sword/weapon swings, but they do follow the fist holding the weapon."
Cause, as far as read: the tracers demo only offered `right_hand` and `active_hitboxes` (A). The API
also has `"held_item"`, `"sword_tip"` (reads the retail sword trail: Marth, Roy, Link, Young Link)
and `{item=serial}`, which the demo never used. Demo changed to cycle all four; to verify on screen.
Open question: whether `active_hitboxes` includes the held item's own hitboxes (a Beam Sword or Bat
swing) or only the fighter's. If only the fighter's, a weapon swing traces the fist; fix in the engine.
