# README artwork

Built by `python pipeline/readme.py` from `pipeline/readme_text.json`. To change a word, edit
that JSON and rebuild. Every image is original: HTML/CSS/SVG with the kit's palette and the
kit's OFL fonts (Source Sans 3), rendered by headless Chromium. There are no Nintendo, HAL or
Melee logos, lettering, characters, stages or screenshots, and nothing is traced from them.
The wordmark is typeset in Source Sans 3 Black and sheared at the kit's 14 degrees; it is
the placeholder project wordmark for section 6.

The snippets assume the images are copied to `docs/readme/` in the repo. Adjust the paths if
they go elsewhere. Nothing here has been placed in any README.

## Files

| File | Size | Pairing | Use |
|---|---|---|---|
| `banner_dark.png` | 1600x400 | dark (pair: `banner_light.png`) | hero banner, top of the README |
| `banner_dark@2x.png` | 3200x800 | dark (pair: `banner_light@2x.png`) | hero banner, top of the README |
| `feature_rollback_dark.png` | 800x400 | dark (pair: `feature_rollback_light.png`) | feature tile |
| `feature_hd_dark.png` | 800x400 | dark (pair: `feature_hd_light.png`) | feature tile |
| `feature_replays_dark.png` | 800x400 | dark (pair: `feature_replays_light.png`) | feature tile |
| `feature_mex_dark.png` | 800x400 | dark (pair: `feature_mex_light.png`) | feature tile |
| `feature_ucf_dark.png` | 800x400 | dark (pair: `feature_ucf_light.png`) | feature tile |
| `feature_determinism_dark.png` | 800x400 | dark (pair: `feature_determinism_light.png`) | feature tile |
| `banner_light.png` | 1600x400 | light (pair: `banner_dark.png`) | hero banner, top of the README |
| `banner_light@2x.png` | 3200x800 | light (pair: `banner_dark@2x.png`) | hero banner, top of the README |
| `feature_rollback_light.png` | 800x400 | light (pair: `feature_rollback_dark.png`) | feature tile |
| `feature_hd_light.png` | 800x400 | light (pair: `feature_hd_dark.png`) | feature tile |
| `feature_replays_light.png` | 800x400 | light (pair: `feature_replays_dark.png`) | feature tile |
| `feature_mex_light.png` | 800x400 | light (pair: `feature_mex_dark.png`) | feature tile |
| `feature_ucf_light.png` | 800x400 | light (pair: `feature_ucf_dark.png`) | feature tile |
| `feature_determinism_light.png` | 800x400 | light (pair: `feature_determinism_dark.png`) | feature tile |
| `social_preview.png` | 1280x640 | one file (GitHub shows it on neither theme) | repo Settings > Social preview (upload; not referenced in the README) |
| `divider.png` | 1600x32 | one file for both themes | section divider (transparent; reads on both themes) |

`@2x` banners are the same art at 3200x800 for sharp display on HiDPI screens. The feature
tiles are 800x400, drawn at 2x for a 400x200 display size.

## Hero banner (light/dark)

GitHub picks the source through `prefers-color-scheme`:

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/readme/banner_dark@2x.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/readme/banner_light@2x.png">
    <img alt="GD's Melee - A native PC port — rollback netplay, HD rendering, Slippi replays" src="docs/readme/banner_light@2x.png" width="800">
  </picture>
</p>
```

## Features

A two-column grid. Each tile is a `<picture>` so it follows the theme, and the tile's words
repeat in `alt` for screen readers:

```html
<table>
  <tr>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_rollback_dark.png">
      <img alt="Rollback netplay: Play a friend online: swap a code, connect, and rollback hides the lag." src="docs/readme/feature_rollback_light.png" width="400">
    </picture></td>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_hd_dark.png">
      <img alt="HD at any resolution: Native PC rendering at any window size, sharp at every scale." src="docs/readme/feature_hd_light.png" width="400">
    </picture></td>
  </tr>
  <tr>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_replays_dark.png">
      <img alt="Slippi replays: Frame-accurate playback of .slp replays, straight from the game." src="docs/readme/feature_replays_light.png" width="400">
    </picture></td>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_mex_dark.png">
      <img alt="m-ex mod support: Custom characters and stages from m-ex builds, loaded like the originals." src="docs/readme/feature_mex_light.png" width="400">
    </picture></td>
  </tr>
  <tr>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_ucf_dark.png">
      <img alt="UCF + tournament rules: Universal Controller Fix and tournament rule sets, built in." src="docs/readme/feature_ucf_light.png" width="400">
    </picture></td>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_determinism_dark.png">
      <img alt="Deterministic engine: Bit-exact simulation, checked frame by frame with SyncTest." src="docs/readme/feature_determinism_light.png" width="400">
    </picture></td>
  </tr>
</table>
```

## Divider

```html
<p align="center"><img alt="" src="docs/readme/divider.png" width="800"></p>
```

## Social preview

Upload `social_preview.png` (1280x640) under the repo's **Settings > General > Social
preview**. All of its text sits at least 64 px from the sides and 48 px from the top and
bottom, so crops don't cut it.

## Checks (all pass on every build)

- Every text box fits its text, measured in the page (titles one line, descriptions at most
  three balanced lines, the tagline one line).
- The wordmark, tagline and art cluster never overlap.
- The social card's text stays inside its safe area.
- Contrast is at least 4.5:1 for every text: tagline (bone on ink strip) 16.75:1; feature title (gold_lt on cobalt) 7.44:1; feature text (bone on cobalt) 8.95:1; wordmark tag (ink on gold) 10.35:1; wordmark name on dark bg 12.42:1; wordmark name on light bg 8.95:1.
