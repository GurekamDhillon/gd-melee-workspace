# Goku alpha media pipeline

Videos, stills, overlays, combo cards, the download zip and the Discord post for the Goku test build. Tooling only: every
output lands under `_build/goku-media` (git-ignored). **Goku is never committed or put on GitHub**: no package, renders,
videos or screenshots in a commit.

| step | command | output |
|---|---|---|
| capture (video + audio passes) | `python tools/media/goku/build_media.py capture [--exe E] [--mods M] [--only kame,ground,flight,ki]` | `<script>/frames/*.png`, `<script>_audio/audio.wav`, `marks.txt` |
| check the passes agree | `build_media.py verify` | state sequences, worst frame offset, per-clip audio shift |
| hero render (Blender Workbench) | `blender -b _build/goku-xv2/author-source/goku.blend --python tools/media/goku/hero_render.py -- OUT.png --action KameFull --frame 20 --side 1 --azimuth -38 --elev 6 --size 1400x1750` | transparent PNG |
| overlays (title, lower-thirds, controls, end, costumes) | `python tools/media/goku/atlas_overlay.py --hero HERO.png --costumes css-goku-p1-panels.png --presentation _build/goku-art/presentation` | `overlays/*.png` |
| combo cards from `combo.json` | `python tools/media/goku/combo_cards.py [--combo PATH]` | `cards/card_1..4_*.png`, `cheat_sheet.png` |
| clips, stills, GIFs, reel | `build_media.py clips`, `stills`, `gifs`, `reel` | `clips/*.mp4`, `stills/*.png`, `gifs/*.gif`, `reel/*.mp4` |
| download zip | `python tools/media/goku/make_goku_zip.py` | `package/GokuAlpha-test.zip` |
| Discord post | `python tools/discord/post_goku_test.py` (dry run) / `--post --zip-link URL` | none until `--post` |

## How the capture works (what was tried)

* `gd.screenshot` is the only per-frame capture (GX-only: the game's own HUD and ki bar, no host overlay). Its PNG writer is a
  worker thread that lags and, when overrun, kills the game (fail-fast) or hangs it.
* Realtime with screenshots every logic tick loses and doubles frames (catch-up ticks). `MELEE_TURBO=1` renders only some frames
  (black frames with particles). Neither is usable.
* **Stepped capture** (what `cap.lua` does): while a clip records the logic is paused and `on_tick` steps one frame every
  `CFG.pace` (3) presented frames; each `CAP.wait(1)` resumes after exactly one step and shoots it. Frame-exact at any load.
  One game at a time (two at once can still overrun the writer); `build_media.py capture` retries a failed script.
* Sound: `MELEE_AUDIO_DUMP` only exists in a realtime run (turbo has no output device), so the same Lua runs again in realtime
  without shots. Input timing in that pass is replayed from the video pass (`CAP.when` logs `WT seq frame`), because input edges
  are one or two logic frames different between a paused step and realtime. wav time = (game clock ms - 2000) / 1000 (measured
  with `gd.play_sound` at known frames). Each clip's audio is shifted by the frame offset of P1's first non-Wait motion.
* Captures are 4:3 (1920x1440) in the current build (`MELEE_WIDESCREEN=1` corrupts screenshots), composed 1440x1080 over a
  darkened blurred copy of the frame.
* The LAB starts in CLEAN display (a throwaway copy of the mods folder with `lab.lua` mode 1), muted to the speakers
  (`MELEE_VOLUME=0`; the dump is full scale), window off screen, own build root `_build/agents/gokumedia`.

## Files

`capture_run.py` one LAB run; `lua/cap.lua` + `lua/clips_*.lua` the scripted clips; `shots.json` the single source for
lower-thirds, controls card, install steps, reel order, stills; `atlas_style.py` tokens, fonts, controller glyphs, Chromium
renderer (the readme.py / announce_chart.py approach); `combo_cards.py` route cards read from combo.json.
