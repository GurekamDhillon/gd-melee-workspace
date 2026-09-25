# GD's Melee brand kit

Built by `python pipeline/build_brand.py` (words in `pipeline/brand_text.json`). Every image
is generated from SVG/HTML in that script and rendered by headless Chromium; text is converted
to outlines, so the SVGs are self-contained. Nothing is traced, recoloured or sampled from any
Nintendo asset: no Nintendo logos, no character art, no trademarked marks.

Overview: `preview/brand_sheet.png`. Discord display-size check: `preview/discord_display_size.png`.

## Picks

- Discord server icon: `discord/server_icon_512.png`
- Discord server banner: `discord/server_banner_960x540.png`
- GitHub social preview: `social/github_social_game.png` (game), `social/github_social_port.png` (decomp/port fork)

## Palette

Same values as the in-game menu kit (`pipeline/kit.py`).

| Name | Hex | Use |
|---|---|---|
| Night | `#032568` | page background |
| Band | `#012d7b` | backdrop bands |
| Cobalt | `#1e3a8c` | faces, panels |
| Cobalt lt | `#2f55b8` | badges, accents |
| Lilac | `#9da2f8` | frames, rules |
| Gold | `#f0b429` | emphasis, tag, mark |
| Gold lt | `#ffd766` | highlight |
| Gold dk | `#a9761a` | icon on gold |
| Ink | `#0a0e18` | shadows, text on gold |
| Bone | `#f2efe4` | text on dark |
| P1 red | `#e5483b` | port / danger |
| P2 blue | `#2f7cf0` | port / link |

## Type

- **Source Sans 3 Black**: wordmark, headlines, chips. Uppercase, sheared 14 degrees.
- **Source Sans 3 Bold**: taglines, body, badge labels.
- **Hasklug Bold** (mono): frame counters, technical labels, hex codes.

The one shear everywhere is skewX(-14.036deg) (the kit's S = 0.25). Shadows are hard ink
offsets (about 5% of the type size), never blurred.

## Logo

- **Wordmark** (primary): the GD'S plate over MELEE.
- **Monogram**: GD on the chamfered gold tile. Below 32 px use `icons/app_icon_small.svg`
  (unsheared, maximised letters).
- **Horizontal lockup**: monogram + one-line wordmark. **Stacked lockup**: monogram over the wordmark.
- Variants: `dark` (for dark backgrounds), `light` (for light backgrounds), `white` and `black`
  (one colour, plate letters knocked out, no shadow).

**Clear space**: x on every side, where x is the height of the GD'S plate.
**Minimum size**: wordmark 120 px wide (25 mm in print); monogram 24 px; 16 px only with the small mark.

**Do**: use the supplied files; keep the gold plate and ink shadow; use the white/black versions on photos.
**Don't**: recolour, stretch, rotate or unshear the mark, add outlines/glows/gradients, set the
wordmark in another font, or combine it with any Nintendo mark or character art.

## Files

| File | Size | Use |
|---|---|---|
| `logo/wordmark_dark.svg` | vector | wordmark logo, on dark backgrounds |
| `logo/wordmark_dark.png` | 1928x760 | wordmark logo @2x, on dark backgrounds |
| `logo/wordmark_light.svg` | vector | wordmark logo, on light backgrounds |
| `logo/wordmark_light.png` | 1928x760 | wordmark logo @2x, on light backgrounds |
| `logo/wordmark_white.svg` | vector | wordmark logo, one colour, white, on photos/dark |
| `logo/wordmark_white.png` | 1974x760 | wordmark logo @2x, one colour, white, on photos/dark |
| `logo/wordmark_black.svg` | vector | wordmark logo, one colour, black, print/light |
| `logo/wordmark_black.png` | 1974x760 | wordmark logo @2x, one colour, black, print/light |
| `logo/monogram_dark.svg` | vector | monogram logo, on dark backgrounds |
| `logo/monogram_dark.png` | 1000x760 | monogram logo @2x, on dark backgrounds |
| `logo/monogram_light.svg` | vector | monogram logo, on light backgrounds |
| `logo/monogram_light.png` | 1000x760 | monogram logo @2x, on light backgrounds |
| `logo/monogram_white.svg` | vector | monogram logo, one colour, white, on photos/dark |
| `logo/monogram_white.png` | 1018x760 | monogram logo @2x, one colour, white, on photos/dark |
| `logo/monogram_black.svg` | vector | monogram logo, one colour, black, print/light |
| `logo/monogram_black.png` | 1018x760 | monogram logo @2x, one colour, black, print/light |
| `logo/horizontal_dark.svg` | vector | horizontal logo, on dark backgrounds |
| `logo/horizontal_dark.png` | 3358x560 | horizontal logo @2x, on dark backgrounds |
| `logo/horizontal_light.svg` | vector | horizontal logo, on light backgrounds |
| `logo/horizontal_light.png` | 3358x560 | horizontal logo @2x, on light backgrounds |
| `logo/horizontal_white.svg` | vector | horizontal logo, one colour, white, on photos/dark |
| `logo/horizontal_white.png` | 3530x560 | horizontal logo @2x, one colour, white, on photos/dark |
| `logo/horizontal_black.svg` | vector | horizontal logo, one colour, black, print/light |
| `logo/horizontal_black.png` | 3530x560 | horizontal logo @2x, one colour, black, print/light |
| `logo/stacked_dark.svg` | vector | stacked logo, on dark backgrounds |
| `logo/stacked_dark.png` | 1960x1392 | stacked logo @2x, on dark backgrounds |
| `logo/stacked_light.svg` | vector | stacked logo, on light backgrounds |
| `logo/stacked_light.png` | 1960x1392 | stacked logo @2x, on light backgrounds |
| `logo/stacked_white.svg` | vector | stacked logo, one colour, white, on photos/dark |
| `logo/stacked_white.png` | 1960x1376 | stacked logo @2x, one colour, white, on photos/dark |
| `logo/stacked_black.svg` | vector | stacked logo, one colour, black, print/light |
| `logo/stacked_black.png` | 1960x1376 | stacked logo @2x, one colour, black, print/light |
| `keyart/keyart.svg` | vector | title card source (vector) |
| `keyart/keyart_1080p.png` | 1920x1080 | title card / key art 1920x1080 |
| `keyart/keyart_4k.png` | 3840x2160 | title card / key art 3840x2160 |
| `keyart/keyart_clean.svg` | vector | clean plate source |
| `keyart/keyart_clean_1080p.png` | 1920x1080 | clean plate, no text, 1920x1080 |
| `keyart/keyart_clean_4k.png` | 3840x2160 | clean plate, no text, 3840x2160 |
| `discord/server_icon.svg` | vector | Discord server icon source |
| `discord/server_icon_512.png` | 512x512 | Discord server icon (upload; Discord crops to a circle) |
| `discord/server_banner.svg` | vector | Discord server banner source |
| `discord/server_banner_960x540.png` | 960x540 | Discord server banner (Boost level 2) |
| `discord/invite_splash_1920x1080.png` | 1920x1080 | Discord invite splash (Boost level 1) |
| `discord/emoji/rollback.svg` | vector | emoji source :rollback: |
| `discord/emoji/rollback.png` | 128x128 | Discord emoji / role icon :gdm_rollback: |
| `discord/emoji/replays.svg` | vector | emoji source :replays: |
| `discord/emoji/replays.png` | 128x128 | Discord emoji / role icon :gdm_replays: |
| `discord/emoji/mods.svg` | vector | emoji source :mods: |
| `discord/emoji/mods.png` | 128x128 | Discord emoji / role icon :gdm_mods: |
| `discord/emoji/lobby.svg` | vector | emoji source :lobby: |
| `discord/emoji/lobby.png` | 128x128 | Discord emoji / role icon :gdm_lobby: |
| `discord/emoji/strikes.svg` | vector | emoji source :strikes: |
| `discord/emoji/strikes.png` | 128x128 | Discord emoji / role icon :gdm_strikes: |
| `discord/emoji/bugs.svg` | vector | emoji source :bugs: |
| `discord/emoji/bugs.png` | 128x128 | Discord emoji / role icon :gdm_bugs: |
| `discord/emoji/announcements.svg` | vector | emoji source :announcements: |
| `discord/emoji/announcements.png` | 128x128 | Discord emoji / role icon :gdm_announcements: |
| `discord/emoji/netplay.svg` | vector | emoji source :netplay: |
| `discord/emoji/netplay.png` | 128x128 | Discord emoji / role icon :gdm_netplay: |
| `discord/emoji/win.svg` | vector | emoji source :win: |
| `discord/emoji/win.png` | 128x128 | Discord emoji / role icon :gdm_win: |
| `discord/emoji/gg.svg` | vector | emoji source :gg: |
| `discord/emoji/gg.png` | 128x128 | Discord emoji / role icon :gdm_gg: |
| `social/github_social_game.png` | 1280x640 | GitHub social preview, game repo |
| `social/github_social_port.png` | 1280x640 | GitHub social preview, decomp/port fork repo |
| `social/x_header_1500x500.png` | 1500x500 | Twitter/X header |
| `social/post_square_1080x1080.png` | 1080x1080 | post template with placeholder headline |
| `social/post_square_1080x1080_blank.png` | 1080x1080 | post template, empty headline slot (type over it) |
| `social/post_portrait_1080x1350.png` | 1080x1350 | post template with placeholder headline |
| `social/post_portrait_1080x1350_blank.png` | 1080x1350 | post template, empty headline slot (type over it) |
| `social/youtube_thumb_1280x720.png` | 1280x720 | YouTube thumbnail template with placeholder headline |
| `social/youtube_thumb_1280x720_blank.png` | 1280x720 | YouTube thumbnail template, no headline |
| `badges/rollback.svg` | vector | README badge: NETPLAY ROLLBACK |
| `badges/rollback@2x.png` | 410x56 | README badge PNG fallback |
| `badges/windows.svg` | vector | README badge: PLATFORM WINDOWS X64 |
| `badges/windows@2x.png` | 482x56 | README badge PNG fallback |
| `badges/version.svg` | vector | README badge: RELEASE V0.1.6 |
| `badges/version@2x.png` | 354x56 | README badge PNG fallback |
| `badges/mex.svg` | vector | README badge: MODS M-EX COMPATIBLE |
| `badges/mex@2x.png` | 474x56 | README badge PNG fallback |
| `badges/slippi.svg` | vector | README badge: REPLAYS SLIPPI |
| `badges/slippi@2x.png` | 358x56 | README badge PNG fallback |
| `badges/discord.svg` | vector | README badge: COMMUNITY JOIN DISCORD |
| `badges/discord@2x.png` | 506x56 | README badge PNG fallback |
| `badges/download_windows.svg` | vector | Download for Windows button (release page / README) |
| `badges/download_windows.png` | 640x150 | Download button 640x150 |
| `badges/download_windows@2x.png` | 1280x300 | Download button 1280x300 |
| `icons/app_icon_1024.png` | 1024x1024 | app icon master (transparent) |
| `icons/app_icon.svg` | vector | app icon source (full mark) |
| `icons/app_icon_small.svg` | vector | app icon source for 16-32 px |
| `icons/gds_melee.ico` | 16-256 | Windows icon for melee-pc.exe and the launcher |
| `icons/favicon/favicon.ico` | 16/32/48 | site favicon |
| `icons/favicon/favicon.svg` | vector | site favicon (SVG, modern browsers) |
| `icons/favicon/favicon-16.png` | 16x16 | favicon PNG |
| `icons/favicon/favicon-32.png` | 32x32 | favicon PNG |
| `icons/favicon/apple-touch-icon.png` | 180x180 | iOS home-screen icon (opaque) |
| `icons/favicon/icon-192.png` | 192x192 | Android / PWA icon (opaque) |
| `icons/favicon/icon-512.png` | 512x512 | Android / PWA icon, maskable-safe |
| `icons/favicon/site.webmanifest` | vector | web manifest for the favicon set |
| `preview/discord_display_size.png` | 1200x560 | check sheet: Discord assets at their real display sizes (not for upload) |
| `preview/brand_sheet.png` | 2400x2000 | brand sheet overview |
