# menu/: the kit's art pipeline

Every texture the port's menus draw, and the README's art, is **generated** here: HTML/CSS/SVG in
`pipeline/*.py`, rendered by headless Chromium, converted to GX textures by
`melee/pc/tools/png2gx.py`, with a layout JSON beside each set. `README.md` has the build and the
per-texture table; `pipeline/readme.py`'s docstring the README-art rules.

## Provenance rule (the one that matters)

Nothing here may be traced, sampled, recoloured or referenced from Melee or any Nintendo asset.
The source of every pixel is in this repo, so the claim is auditable. Keep it that way: no
screenshots as references in the pipeline, no game fonts (the fonts are Source Sans 3 and
Hasklug, OFL).

## Layout

| dir | what |
|---|---|
| `pipeline/` | the generators: `build.py` (menu art), `hub*.py`, `lobby.py`, `online.py`, `loading.py`, `nav.py`, `kit.py` (palette, shear), `icons.py` (the `ico_*` bodies), `readme.py` + `readme_text.json` (README art), `build_brand.py` + `brand_text.json` (logos, badges) |
| `out_*/` | the rendered sets, one per generator; `out_kit/` is what the game reads as `ui/` (`kit.json`, `*_layout.json`, `kit_motion.json`, the font atlas) |
| `SourceSans3/`, `Hasklug/` | the fonts (OFL) |

The LAB's own art (`melee/pc/geno/mods/geno-lab/art/`) imports this pipeline by path and reads it
only.

## Working here

- Needs `playwright`, `pillow`, `numpy`, `scipy`. Without `playwright install`, point the launch at
  an existing Chromium (`executable_path`); a small wrapper that patches `BrowserType.launch`
  works and needs no repo change.
- Every generator checks its own output (text fits its box, no overlaps, contrast) and exits
  non-zero on failure; a build that prints no `checks ok` did not pass.
- The README shows the PNGs committed in `docs/readme/`; regenerating changes nothing until they
  are copied there. Compare before copying: a one-word change should move one tile.
- The kit's style is one shear (0.25), flat colour, hard shadows, cobalt faces, gold for emphasis
  (`kit.py`). New art follows it or it will not sit beside the rest.
