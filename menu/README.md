# Placeholder menu art — pipeline bring-up

**This is placeholder, not shipping art.** Its job is to exercise the path
`PNG → GX texture → HSD scene → scene proc` end to end, so we learn the real
constraints (element split, POT padding, which format each piece wants) before
a human artist cuts anything. The written spec still goes to the artist
unchanged.

**Provenance:** every pixel is generated from the HTML/CSS in `pipeline/`.
Nothing is traced, recoloured, referenced or sampled from Melee or any other
Nintendo asset. The source is in the repo, so the provenance is auditable
rather than asserted.

## Build

```
python pipeline/build.py
```

Needs `playwright` (+ `playwright install chromium`), `pillow`, `numpy`.
HTML + CSS → headless Chromium → PNG-32, straight (non-premultiplied) alpha,
sRGB-tagged. Rebuilds `out/` from scratch every run.

## What's here

| file | @2x | @1x | format | why |
|---|---|---|---|---|
| `panel_bg` | 1024×512 | 512×256 | CI8 (RGB5A3 TLUT) | measured 74 colours — exact, at half of RGB5A3 |
| `btn_play_ng` / `_hover` / `_press` / `_disabled` | 512×128 | 256×64 | RGBA8 | carries text |
| `cursor_hand` | 64×64 | 32×32 | RGBA8 | tiny; needs clean alpha on a stepped silhouette |
| `frame_corner_tl/tr/bl/br` | 128×128 | 64×64 | RGB5A3 | 9-slice, no text |
| `frame_edge_h` | 128×32 | 64×16 | RGB5A3 | tiles/stretches on X |
| `frame_edge_v` | 32×128 | 16×64 | RGB5A3 | tiles/stretches on Y |

```
out/2x/     authoring res — this is the deliverable set
out/1x/     640×480 native, for comparison / if 2x is deferred
out/ora/    layered source, one .ora per element (Krita, GIMP, Photopea;
            Photopea re-saves as .psd if someone downstream needs one)
out/preview/  composed mockups — reference only, do NOT ship these
out/manifest.json  per-file sizes, format recommendation + rationale, layers
```

Every size is a power of two, hence also a multiple of 4, and ≤1024 in both
axes. Nothing needs padding and nothing needs tiling except the frame, which
is 9-sliced by design.

## Decisions worth arguing with

- **The frame is 6 pieces, not one texture.** A full-screen frame at 2× is
  1280×960, over the 1024 limit. 9-slicing is the answer that survives the
  limit *and* makes the frame resolution-independent. The four corners are
  emitted separately rather than relying on mirrored UVs — collapse them to
  one texture if the UV flip is cheaper on your side.
- **Disabled is desaturated, not alpha-faded.** RGB5A3 has 15 alpha levels;
  a 50%-opacity greyed-out button bands visibly. The disabled state is fully
  opaque steel instead.
- **The four button states are frames 0–3 of one `HSD_A_T_TIMG` track.**
  `press` is offset +8,+8 *inside* its own canvas rather than being a smaller
  texture, so all four share one quad, one UV rect and one material. A state
  change is `animateJoint(joint, TOBJ_MASK, state)` — no new code path, the
  same mechanism the CSS portraits already use.
- **No soft shadows, glows or smooth gradients anywhere.** The "shadow" is a
  solid ink shape at a hard offset and the shading is hard-stop stripes. This
  is what survives CMPR and CI8's 256 colours intact.
- **Cursor hotspot is (14,4) @1x / (28,8) @2x** — tip of the index finger.

## Quantisation, measured

`python pipeline/quantise_check.py` simulates RGB5A3 and CI8 on the built
PNGs and writes `out/quantise/` (quantised result plus an 8×-amplified diff).
It is a format simulation, not a converter — it exists so the art can be
fixed while fixing it is still cheap.

`panel_bg` was the risk, because of the diagonal hatch. It survives:

```
panel_bg -> RGB5A3   max delta 8/255   mean 1.51   117 -> 74 colours
hatch                luma separation 10.85 -> 8.00, no banding
```

The hatch is a hard-stop overlay, so quantisation moves both tones by about
the same amount and the stripes stay separated. There was nothing smooth in
there to band in the first place — that was the point of the palette call.

The useful surprise: **`panel_bg` is only 74 distinct colours** once RGB5A3
has done its thing. A CI8 index with an RGB5A3 palette reproduces it exactly
— byte-identical output at 512 KB instead of 1 MB @2x. Recommended, at the
cost of one TLUT slot; fall back to RGB5A3 if TLUT slots are scarcer than
texture memory. The art is unaffected either way.

Per-element colour counts after an RGB5A3 quantise:

| element | colours | CI8? |
|---|---|---|
| `panel_bg` | 74 | yes — 1 MB → 512 KB |
| `btn_play_ng` / `_press` / `_disabled` | 172 / 193 / 119 | fits, but see below |
| `btn_play_hover` | 258 | **no** — two colours over the limit |
| `cursor_hand` | 26 | yes, saves 4 KB |
| `frame_corner_*` | 5 | yes, saves 16 KB each |

The buttons stay RGBA8 regardless: they carry text, and mixing formats across
frames of one TexAnim track is not worth it to save 64 KB. The frame pieces
stay RGB5A3 — 16 KB is not worth a TLUT slot.

## For whoever writes the converter

Two things that will silently ruin correct art:

- **Do not apply an sRGB→linear transform.** The PNGs are sRGB-tagged because
  that is what they are, but GX samples texels raw. A converter that colour-
  manages on the way in will wash everything out, and it will look like an art
  problem rather than a pipeline one.
- **The GX texture must carry straight alpha.** The 2×→1× resize
  premultiplies internally and un-premultiplies before writing, so the PNGs on
  disk are straight. Anything that re-premultiplies will fringe in RGB5A3.

## Not in this pass

No animation sequences — the minimal set is static, and the transitions for
the loading screen / trophy-get popup belong in the scene proc as joint and
material animation, not as textures. When we do need them: **hover in over 6 frames (100 ms), press
in over 3 frames (50 ms), press release over 4 frames (67 ms)** at 60 fps,
delivered as `btn_play_hover_000.png` … `_005.png`. That's 6 × 512×128 RGBA8
= 1.5 MB at 2× for one button's hover alone, which is the argument for doing
hover as a vertex-colour or UV-scroll effect on the static texture rather
than as per-frame art.

## Two gotchas the pipeline hit, so they don't get re-hit by hand

1. **Downscaling straight alpha directly produces dark halos.** Chromium
   leaves RGB at 0,0,0 in fully transparent pixels, and a filter pulls that
   black into every edge texel. `build.py` premultiplies → resizes →
   un-premultiplies. Any 2×→1× step downstream must do the same.
2. **Layer isolation uses `opacity`, not `visibility`.** A descendant with
   `visibility:visible` overrides a hidden parent, which silently leaked the
   hover chevron into every other layer of the hover and press states. It
   rendered fine in the flat PNG and wrong in the `.ora`, which is exactly
   the kind of divergence that isn't noticed until someone opens the source.

---

# Hub main menu prototype — geometry, not texture

```
python pipeline/hub.py        # writes out_hub/ (separate from out/, which build.py wipes)
```

A hub-and-spoke main menu: one hero bucket (VERSUS) takes the full height,
three secondaries step down in size (SOLO 144 → COLLECTION 110 → OPTIONS 82
px tall @1x). The point of it is the build, not the look: **the whole screen
is 15 flat-colour quads and 13 textured quads**, and every texture is a white
alpha mask tinted by material colour.

| | memory @2x |
|---|---|
| this approach — 13 masks, I4 | **138 KB** |
| baked, per tile, ng + sel, RGB5A3 | 6,144 KB (and still no header/footer) |
| baked, 4 full screens, RGB5A3 | 9,600 KB (and each over the 1024 limit) |

## The source of truth is `out_hub/hub_layout.json`

Every quad with explicit vertices in 640×480 space, its colour, and for
textured quads the texture name and normalised UV rect. Per-tile state rules
are in the file. The previews in `out_hub/preview/` are drawn *from that JSON
alone*, with the textures pre-quantised to I4, so they are what the engine
would draw if it follows the file. `hub_wireframe_2x.png` shows the quads:
magenta flat, green textured, gold dashed title-safe.

This is also the layered source for the hub: every element is already its
own quad, so there is nothing to re-split.

## How it works

- **One shear for the whole screen**: `x' = x + (240 − y) × 0.25`, about 14°.
  Layout is authored as plain rectangles, then sheared. Every edge leans the
  same way and every gutter is parallel.
- **Italics for free.** Labels are rendered upright. The sheared quad
  italicises them. The same texture would work upright elsewhere.
- **Textured quads must be parallelograms.** A parallelogram maps a texture
  exactly with two triangles because the map is affine. A trapezoid kinks the
  texture along the diagonal. `hub.py` checks every textured quad.
- **Gutters are the backplate.** One ink quad sits behind the cluster; the
  8px gaps between tiles are that quad showing through. No outline geometry.
- **Selection adds no texture.** The face, icon and label change material
  colour and translate by (−5, −5). A darker plate quad appears at the rest
  position, which gives a hard-edged extrusion with no shadow. The selected
  tile draws on top. The footer description is the only per-selection
  visibility change.
- **Checks on every build:** textured quads are parallelograms; everything
  except the two decor bands stays inside title-safe, *including* after the
  selection offset; labels don't overlap icons or spill out of their tiles;
  every texture is power-of-two and ≤1024.

## For the scene proc

- **I4 needs a specific TEV setup.** GX expands I4 to the same intensity in
  all four channels. TEV must take RGB from the material colour and only
  alpha from the texture. If RGB also comes from the texture, every
  anti-aliased edge gets darkened twice. If that setup is awkward, use IA4
  (8bpp), which is the fallback listed in the JSON.
- The shear is baked into the vertices, so there's no special transform.
  Joint translate for the selection offset, material colour animation for the
  tint.
- UVs are normalised, so the 1× and 2× textures drop in unchanged.

## Provenance

The layout, pictograms (clashing chevrons, bullseye, gem on pedestal, gear)
and copy are original and generated from `pipeline/hub_layout.py` and
`pipeline/hub.py`. What's borrowed is the principles: size hierarchy, a
single shear angle, flat colour, broad-to-specific buckets. No layout or
asset is taken from any shipped game.
