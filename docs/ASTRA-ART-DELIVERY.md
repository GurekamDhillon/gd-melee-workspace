# Astra art delivery — 2026-09-30

The first expansion pack is available at
[`menu/out_roguelite_expansion/index.html`](../menu/out_roguelite_expansion/index.html).
It was opened locally for review. This is an interactive art reference using
an original abstract figure, not footage of a fighter or a native integration.

## Delivered

- 76 manifest entries: 17 reused shared glyphs and 59 expansion entries.
  Editable SVG, straight-alpha PNG and native GX textures share stable names.
- Shape-coded door/socket/map markers, compact command-tree chrome, charge and
  cooldown masks, equipment/reward icons and five enemy-tell symbols.
- Six family treatments: Cinder, Rime, Gale, Aegis, Flux and Sigil, with body/
  equipment placement previews and dormant/charging/ready/activation/recovery.
- Continuous trails, orbitals, segmented halos, material fields and reference
  afterimages. Weapon-history ribbons and fighter ghosts still need native code.
- Five founder compositions, ten authored pair blends and six reaction motion
  references; preview playback, scrub, blend and quality controls.
- Three theme directions and reward, fusion, victory, failure, transition and
  enemy-tell layouts. Displayed reward values are examples, not new mechanics.
- Compact HUD in 4:3 and 16:9 with recursive mouse/D-pad controls: Left/Right/
  Down descend, Up returns to parent, Up at root represents taunt.

Sources: `menu/pipeline/roguelite_expansion.py` and
`roguelite_expansion_review.{html,css,js}`. Existing packs remain unchanged.
`manifest.json` describes exports, hashes, anchors and blend/wrap assumptions;
`direction.json` describes motion, attachments and quality/budget contracts;
`layout.json` describes layout, socket and gene/tell associations.

## Review links

- [Compact combat comparison](../menu/out_roguelite_expansion/preview/combat-sheet.png)
- [Six families](../menu/out_roguelite_expansion/preview/family-sheet.png)
- [Cinder/Rime states](../menu/out_roguelite_expansion/preview/state-sheet.png)
- [Five founders](../menu/out_roguelite_expansion/preview/founder-sheet.png)
- [Ten blends at five weights](../menu/out_roguelite_expansion/preview/blend-sheet.png)
- [Reactions](../menu/out_roguelite_expansion/preview/reaction-sheet.png)
- [World and reward presentation](../menu/out_roguelite_expansion/preview/world-sheet.png)
- [Continuous motion reference](../menu/out_roguelite_expansion/preview/continuous-motion.gif)

## Validation and budgets

Run from `gdm`:

```sh
_build/roguelite-art-venv/bin/python menu/pipeline/roguelite_expansion.py
_build/roguelite-art-venv/bin/python menu/pipeline/roguelite_expansion_check.py
```

The build uses Pillow, rsvg-convert and the existing native `png2gx.py`.
The review checker uses Playwright and installed Chromium. The existing local
venv now has both Pillow and Playwright. Source Sans 3 includes its OFL license.

`validation.json` records passing export/hash/dimension/reference checks and
GX alpha round trips (maximum IA4 error 8/255; RGBA8 exact). Browser checks
cover actual tree navigation, aspect ratios, states, founders, ten blends at
five weights, sampled exact endpoints, reactions, presentation screens,
reduced/color controls and document overflow. No browser errors were recorded.

Exported UI subset: **805,952 bytes**. Full authored GX library: **6,165,248
bytes**. The 4 MiB resident FX budget is a runtime selection budget, not a claim
that the entire library fits in 4 MiB. Full-library budget is 8 MiB. Native
allocation, timing and overdraw measurements remain pending.

## Still required before calling the art finished

1. Review on real fighters, weapons/accessories and simultaneous opponents at
   native gameplay scale. Browser figures cannot validate model selectors,
   surface masks, pose history, depth handling or native blend modes.
2. Capture a real integrated branch room. Only the earlier corridor capture
   was available for this pass. Review door markers at actual upper/drop
   sockets; the review background is illustrative geometry.
3. Reconcile each visual reaction with implemented gameplay semantics. Founder
   reaction names describe art combinations; they are not automatically the
   mechanical gene-reaction catalogue. Tell masks must follow actual attack
   timing/range; decorative halos must not imply unimplemented protection.
4. Implement and measure native ribbons, afterimages and surfaces against the
   contracts. Select bounded resident sets, clear history across teleports,
   room changes and fighter replacement, and preserve reduced-FX settings.
5. Obtain user visual/feel review, including readable color alternatives and
   reduced motion. Automated screenshots do not certify accessibility or polish.

No gameplay, physical-room or completion/polish acceptance gate is closed by
these browser previews. This pack supplies assets and concrete direction for
integration and the next art iteration.
