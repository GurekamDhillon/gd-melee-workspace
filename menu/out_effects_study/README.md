# Fire / Ice — Asset Study 01

Sixteen original source textures for review before effect integration.
Open `index.html` for side-by-side dark/light previews and size, opacity and tint
controls. `preview/contact-sheet.png` shows the complete set, including 32 px
readability thumbnails. The preview colours are suggestions, not baked into masks.

## Contents

- Three flame silhouettes: lance, hook and fork.
- Three faceted ice silhouettes: needle, cleaver and chip.
- A branching frost fragment.
- Clean and fractured rings, a release flash and a tapered streak.
- An angular ember, smoke billow and steam wisp.
- Seamless scalar noise and a curl vector field.

`rgba/` contains sixteen 256×256 RGBA8 PNGs. Fourteen have white RGB and straight
alpha, including fully transparent pixels; tint them at runtime. `svg/` contains
their editable vector/filter sources. The two opaque data maps are generated
analytically with a fixed seed. `manifest.json` records intended roles, anchors,
wrapping, export formats, sampling notes and content hashes.

The current effect offset shader reads R and A. For the R/G curl source use
texture swizzle `rgbg`, which routes G to A. For scalar noise `rrrr` supplies the
same scalar to both axes. Use linear data sampling and keep an offset sampler
out of the effect's opacity sampler list. These are integration instructions;
the assets have not been installed in any runtime recipe.

The shards are 2D sprites. Actual three-dimensional shard and shell meshes are
a separate authoring task. Flat previews do not represent finished effects,
particle motion, emission, additive blending or distortion in the game.

## Rebuild in the repository

```sh
python3 menu/pipeline/effects_assets.py
```

Requires NumPy, `rsvg-convert`, and ImageMagick. SVGs are rasterised at 512 px and
downsampled to 256 px; checks reject empty masks, clipped canvas edges and loss
of alpha precision. Two consecutive builds produced identical texture hashes.
All artwork comes from the SVG paths/filters and analytic fields in that script;
no game artwork was used as a reference or input.

The interactive preview embeds Source Sans 3 from the menu kit. Its licence is
included in `font-LICENSE.md`.
