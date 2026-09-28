# Menu-kit pieces: conventions and the next additions (2026-09-28)

How to add a piece to the kit without breaking the conventions. Sources of truth:
`menu/README.md` + `menu/CLAUDE.md` (art pipeline), `_research/frontend-menus.md` (the JSON
contract, widgets, motion), `pc/platform/gw_kit.h` (the script kit's native contract),
`src/melee/gm/gmfrontend_kit.inc` (the game-side toolkit), `docs/scripting.md` (the public
`gd.kit` table), `_build/ui/*.json` (the shipped layouts).

## Where each kind of piece lives

| piece kind | add it to | checks |
|---|---|---|
| art texture | `menu/pipeline/*.py` (HTML/CSS, one shear 0.25, flat colour, hard shadows; never traced from any game) | generator's own fit/overlap/safe-area/contrast checks; `png2gx.py --layout`; 1x/2x + manifest |
| layout/anchors/motion | a `*_layout.json` / `*_motion.json` beside the art; the game-side kit loads it once and builds a float model | keep `space: unsheared` vs screen-space convention (`fp_evaluate` applies motion before the shear) |
| game-side widget | `gmfrontend_kit.inc` (slots, `kw_names`), table rows need no drawing code | PowerPC syntax check through `gmfrontend.c`; `fe_menu_sweep.py` |
| script-facing call | native in `pc/platform/gw_kit.c` + wrapper in `gw_script.c` (`gs_kit_record` the drawn range) + a row in `docs/scripting.md` | `gw_kit_tests` (gw_kit.h) and the standalone contract tests |

Rules that already exist and apply to anything new: text never squashes (fit rule: step down a
role, then `…`); colour through tokens; the 640x480 virtual screen (today letterboxed into the
window — the wide-canvas/safe-area change is tracked separately); the kit's row/template metrics
are read from the layout JSON, not retyped.

## Next pieces (proposed, in order)

1. **`gd.kit.paragraph(x, y, w, text [, role [, colour [, opts]]]) -> lines, height`** — wrapped
   multi-line text at a fixed width; explicit `\n` is a hard break; a single word wider than `w`
   falls back to the fit rule; `shear` per line about its own baseline. Implemented 2026-09-28
   (`gw_kit.c: gw_Kit_DrawParagraph`); this is what the map editor's help and any body copy use.
   A matching `gd.kit.paragraph_measure(text, w [, role]) -> height` follows when a layout pass
   needs it (variable-height lists).
2. **Script widgets for value rows** (`gd.kit.choice` / `slider` / `toggle`) mirroring
   `widgets_layout.json`'s quads and state colours, so scripts stop hand-rolling arrows and
   tracks. The art and the colour/contrast tables already exist; only the script wrappers do
   not.
3. **A scrolling region convention for scripts**: `gd.kit.list` already takes `first` + `visible`
   (defaults 1 / 64); document the scroll pattern (clamp `first`, keep the selection one row from
   the edge as the frontend list does) instead of adding a new call, unless a motion-parity
   `scroll_step` is wanted.
4. **Dialog/toast parity**: `dialog_layout.json` and the toast motion exist game-side; a script
   toast (`gd.kit.toast(text, ok|danger)`) would let mods reuse it. Candidate, not scheduled.

## Rejected for now

- Native-side wrapping inside `gw_Kit_DrawText` (it would silently change every existing
  call's meaning; wrap is a new call).
- Squashing text to fit (violates the fit rule).
- New textures for the pieces above: the existing frame/row/glyph set covers them.
