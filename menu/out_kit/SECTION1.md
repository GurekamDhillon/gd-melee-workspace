# Section 1 delivery: kit primitives and font atlas

Rebuild everything, in this order:

```
python pipeline/kit.py && python pipeline/font_atlas.py && python pipeline/glyphs.py && python pipeline/kit_ui.py
```

Each script runs its own checks and exits non-zero if any fail. All of them pass at the time of this delivery.

## What's here

| Brief item | File | Notes |
|---|---|---|
| Palette, sections, ports, teams, type scale | `kit.json` | Colour-blindness and contrast results are under `checks` |
| 1. Font atlas | `font/font_manifest.json`, `font/{2x,1x}/font_<role>_latin_<n>.png` | 9 roles in two faces, I4, 928 KB at 2x in total. See "Fonts" below |
| 2. Button glyphs | `2x/glyph_{a,b,x,y,z,l,r,start,stick,cstick,dpad}.png` | Replace `glyph_a` and `glyph_b`. Also `glyph_check` for checkbox cells |
| 3. Chrome | `chrome_layout.json` | Header with title, breadcrumb, description strip, footer hint slots, per-section backdrop |
| 4. List template | `list_layout.json` | Row (normal, selected, disabled), divider, scroll track, value slot |
| 5. Widgets | `widgets_layout.json` | Toggle, choice, slider, stepper, checkbox cell; colours for all three states |
| 6. Dialog and toast | `dialog_layout.json` | 1–4 body lines, 1–3 buttons with a danger variant; the toast covers the description strip |
| 7. Cursor | `cursor_layout.json`, `2x/cursor_{ink,fill,detail}.png` | Hand split into masks; port number on a sheared badge set from the atlas |
| Motion | `kit_motion.json` | 18 events in the `hub_motion.json` format, plus sequences and hold-repeat |
| Textures | `manifest.json` | 24 textures, each with GX format and the reason for it |
| Previews | `preview/` | Composed from the JSON alone, with worst-case strings |

## Things the engine side needs to know

- **Template coordinates are unsheared.** Every vertex, glyph quads included, goes through `x' = x + (240 - y) * 0.25` as the last step, after layout and motion. That's what lets one row template be stamped at any y. `hub_layout.json` is still stored in screen space; it moves to this convention in section 2.
- **Colours in templates and motion are tokens.** `@face`, `@bg`, `@band` and `@face_hi` come from the current section in `kit.json`; `port:p1` and similar are port colours; anything else is a palette name. Motion values written as strings (`"60*dir"`, `"value/max"`) are expressions the player evaluates.
- **Text is set from `font_manifest.json` alone.** For each character, add `kerning[prev + ch]` if the pair is listed, place the glyph quad at pen + `offset`, then add `advance`. Advances and kerning come from the font tables, not PIL: PIL rounds advances to whole pixels (that drifted a 20-character name by about 4px at 1x) and applies no kerning. The kerning matches HarfBuzz on all 361 pairs I cross-checked.
- **Slots are sized in pixels, not characters.** Each text slot has a `max_width_1x`. If a string is wider, set it one role smaller in the same face; if it's still too wide, truncate with "…". Never squash it sideways. Character counts in the layouts are only a guide.
- **Italic is a shear, not a separate atlas.** The glyphs are upright; the screen shear italicises them, as the hub already does.
- **The large sizes are caps-only.** `hero` (44) and `display` (56) contain no lower case. The engine uppercases strings drawn in those roles.
- **Disc art never gets a texture from us.** Checkbox cells take a 64×56 slot, and the previews show it labelled "64×56".
- **Cursor rules.**
  - Draw order: ink mask offset by (1.5, 1.5) as the shadow, then ink, then the fill tinted per port, then detail.
  - Hotspot is (14, 4).
  - The cursor is never sheared.

## Memory at 2x, per composed screen (excluding disc art)

| Screen | KB |
|---|---:|
| List (rules, worst case) | 172 |
| List with dialog | 236 |
| List with toast | 172 |
| Widget sheets | 137 and 161 |
| Checkbox grid with cursors | 144.5 |

Every screen is well under the 1 MB budget. Most of the memory is the font: `title` + `body` + `row` + `caption` come to 160 KB. `hero` and `display` are 256 KB each, and only screens that use them load them.

## Answers to the open questions

**1. Rectangular or bouba as the base?** Rectangular. It's the only one with a finished motion spec, and the Sakurai reference depends on skewed edges and italic momentum, which bouba gives up. List rows, tables and grids are rectangular by nature, so a round base would fight every screen after the hub. Bouba stays an experiment in `out_hub_bouba/` and won't be mixed in.

**2. How do sections read as different places while staying one system?** Each section gets three cues, and nothing else changes:
- **Colour:** a face hue per section. Backdrop, band and icon colours are derived from it at fixed lightness steps in Lab. The closest pair under normal vision is ΔE 14.6.
- **Band rhythm:** each section has its own pattern of backdrop bands (Versus two, Solo one wide, Collection three thin on the right, Options none, Data four).
- **Breadcrumb icon:** the section's hub icon sits at the root of the breadcrumb.

Gold selection, ink structure and bone text are identical everywhere. Colour alone isn't enough for red-green colour-blind players: Collection violet and Versus cobalt fall to ΔE 4.8–5.5. An optimiser can push that to 12.6, but only by making the sections grey and brown, so the band rhythm and icon carry the difference instead. `preview/sections_strip.png` shows all five sections.

**3. The smallest type size at 1x?** 12px (`caption`, cap height about 8px, Source Sans 3 Bold), for badges, divider labels and footnotes. Sentences and footer hints use 14px (`body`). The 1x previews show 12px Bold reading cleanly on the dark faces. I haven't tested anything below 12, and nothing in the kit needs it.

## Fonts

The name-width problem is settled by using two faces from one family, both under the SIL OFL 1.1:
- **Source Sans 3 sets almost everything:** names, labels, sentences and numbers. It's the proportional sibling of Source Code Pro, which Hasklug is built on, so the two faces share letter shapes and weights. Its Japanese and Chinese companion, Source Han Sans, is also OFL, which suits the second-script pages later. The files are in `SourceSans3/`, with the licence, downloaded from Adobe's official 3.052R release.
- **Hasklug stays only in the `tag` role (20px, fully monospaced),** for name tags and the name-entry field. There, fixed-width cells keep the caret and the plate still while letters change.
- **Numbers use Source Sans too,** which is different from what was proposed. Its default figures are already tabular (every digit is 540 units wide in Black), and the build checks that in every role. So a separate monospaced number face would only cost extra atlases.

| Role | Size | Face | Glyphs | Kern pairs | Page | KB |
|---|---:|---|---:|---:|---|---:|
| caption | 12 | Sans Bold | 105 | 966 | 256×256 | 32 |
| body | 14 | Sans Bold | 105 | 966 | 256×256 | 32 |
| row | 16 | Sans Black | 105 | 937 | 256×256 | 32 |
| label | 20 | Sans Black | 105 | 937 | 512×256 | 64 |
| title | 24 | Sans Black | 105 | 937 | 512×256 | 64 |
| heading | 32 | Sans Black | 105 | 937 | 512×512 | 128 |
| hero | 44 | Sans Black, caps | 79 | 342 | 1024×512 | 256 |
| display | 56 | Sans Black, caps | 79 | 342 | 1024×512 | 256 |
| tag | 20 | Hasklug Black, mono | 105 | 0 | 512×256 | 64 |

## Port colours

| | Colour | Label text | Contrast |
|---|---|---|---:|
| P1 | `#e5483b` red | ink | 4.89 |
| P2 | `#2f7cf0` blue | ink | 4.83 |
| P3 | `#f4d23a` yellow | ink | 12.97 |
| P4 | `#27b88a` green | ink | 7.63 |
| CPU | `#7e8490` grey | ink | 5.13 |

Teams use red = P1, blue = P2 and green = P4. The closest pair under each simulation:

| Vision | Closest pair | ΔE00 |
|---|---|---:|
| Normal | P2 / CPU | 19.5 |
| Deuteranopia | P4 / CPU | 17.4 |
| Protanopia | P2 / CPU | 20.8 |
| Tritanopia | P2 / P4 | 15.2 |

Every port-coloured element also carries its number, so colour is never the only cue.

The one real conflict is P3 yellow against the selection gold: ΔE 4.9 under deuteranopia. Port colours are never used to show selection. Selection is gold plus the lift and plate, and the number and plate carry the difference.

## Known gaps, to fix in the section noted

- **Section 2:** the hub's labels are still baked textures, set in Arial Black. That breaks the no-baked-text rule, and Arial Black is licensed less clearly than Hasklug (SIL OFL). The hub moves to atlas text and gains the fifth tile, Data.
- **Section 2:** there's no `ico_data` icon yet, so the Data section's breadcrumb has no icon.
- **Section 3:** the player panel's name plate is sized by the fit rule. The longest vanilla name, "Mr. Game & Watch", is 110.5px at `body` against a 136px portrait. Longer m-ex names step down to `caption`, then truncate.
