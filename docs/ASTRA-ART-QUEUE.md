# Astra art queue — TBD roguelite

User presentation preference: **PNG previews only**. Show stills/contact sheets
directly in chat. Do not create or open further interactive viewers for art
review. The existing viewer is a historical artifact, not the delivery format
for future batches.
Prefer in-game PNG screenshots when readily available during normal work.
Do not add substantial setup or integration work just to capture a preview;
otherwise use clearly labeled art-reference PNGs.
Leave selected PNG previews open in the desktop image viewer for the user's
return, and add useful in-game captures as they become available. Avoid taking
over a native acceptance run merely to arrange preview windows.

Execution update, 2026-09-30: the user authorized the Astra art pass. A first
reusable art pack and interactive motion/layout review are now delivered in
`menu/out_roguelite_expansion/`. See [delivery and remaining work](ASTRA-ART-DELIVERY.md).
Asset/browser validation passes; native integration and human visual approval
remain pending. This does not close the full art/polish queue.

Astra owns new final art and direction. DeepSeek owns bulk runtime support and
asset ingestion, with Sol reviewing and integrating. Coordinate shared files
and builds. The requirements below remain the acceptance brief.

Companions: `DEEPSEEK-NEXT-PASS.md`, `ART-BRIEF-branch-rooms.md` and Gate 9 of
`ROGUELITE-COMPLETION-PLAN.md`.

## Existing assets to reuse first

- `menu/out_roguelite/room-kit/` already has stairs, ramps, balconies, doorway
  walls, floor openings and trim, with mesh/collision metadata. The immediate
  branch-room milestone primarily needs installation, placement reconciliation
  and native collision/traversal verification, not a fresh room kit.
- `menu/out_roguelite/manifest.json` already lists Cinder/Rime, command and
  body-role icons and other UI assets. Audit coverage before replacing them.
- `menu/out_effects_study/manifest.json` already supplies 16 original masks and
  fields, including rings, tapered streaks, fire and ice shapes. Reuse these for
  runtime prototypes. The 13 native recipes are not 13 finished gene families.

## Priority 1 — Readable dungeon and compact command UI

Review a real integrated branch-room capture before drawing replacements.
Provide original socket/route markers for upper/lower paths, locked/open doors,
return paths and unexplored destinations where the existing kit lacks readable
signals. They must suit the authored 10.4 × 16.9 game-unit doorway opening and
26-unit storey without changing collision. Directions must read through shape,
position and motion as well as color. Keep camera views and fighter silhouettes
clear; do not solve every route with a large floating panel.

Extend the current menu kit for the compact D-pad tree, breadcrumbs, charge
segments, cooldown/ready/refusal states, item/equipment choices, small map marks
and short toasts. Reuse current icons/chrome where good. Show combat at 4:3 and
widescreen with the menu closed and open; keep damage/lives legible and most of
the screen available for gameplay. Labels remain runtime text.

## Priority 2 — Continuous build identity

Author a coordinated set of trail/ribbon masks, segmented halos, orbiting
shapes and persistent material accents for reviewed body/equipment roles.
Begin with one coherent Cinder and one Rime treatment across dormant, charging,
ready, activation and recovery, then extend to the remaining families.
Supply shape/motion differences, not only palette swaps. Each composition
should explain what a player can do and which region carries the gene.

Full-model afterimages need native pose/draw-history support from DeepSeek.
Astra can specify tint, opacity decay, spacing, silhouette readability and
quality levels; do not present a static sprite as implemented fighter ghosts.
Likewise, model-surface patterns need masks/material support and reviewed
selectors, and real weapon ribbons need attachment history. Agree these
contracts before multiplying art variants.

## Priority 3 — Finish the catalogue and world presentation

Complete visual compositions for Thunder Crown, Astral Vortex and Comet
Crescent, founder blends and reactions in the full plan. Extend family,
equipment, reward and boss-tell icon coverage against implemented definitions.
Develop theme/background depth, hazard and encounter tells, transitions,
reward/fusion presentation and run-end screens. Boss danger and hit range must
match mechanics; ornament cannot masquerade as a damaging field or shield.

## Delivery contract

Deliver each batch as reusable source assets plus stable names, manifest,
dimensions, anchors, alpha/blend/wrap assumptions, motion/state specification
and native memory/overdraw budget where applicable. Follow the existing
pipeline's format and source conventions. Avoid baked UI words; use tintable
mask assets where appropriate. Keep provenance original.

Show the user assets as they finish, distinguishing an art preview from native
rendered evidence. Review motion at gameplay distance, simultaneous opposing
builds, reduced FX, and color-vision/readability cases. Supply close-up and
gameplay-distance previews; leave native correctness/certification to tested
integration. Root/coordinator lands reviewed batches with DeepSeek.

This queue must not block unrelated implementation: DeepSeek can install the
existing kit, fix save/generation defects and complete the generated-run loop
while Astra develops new presentation assets.

Screenshot preference clarification: show/open actual in-game screenshots only. Do not present simulated screenshots or menu mockup sheets as screenshot previews. Root closed the reference gallery and opened native clean room captures. Existing art references remain files, not desktop presentation.
