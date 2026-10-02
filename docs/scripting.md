# Scripting GD's Melee (Lua) — the modding API

**Current as of 2026-09-27.** Checked against `gw_script.c` at game `4c676892a`; this
reference supersedes older API descriptions. The LAB API is public too (`gd.lab_api == 1`).

GD's Melee runs **Lua 5.4** scripts inside the game. A script can read the match (fighters,
positions, percents, action states), draw readouts over the game, add console commands, press
buttons, save and load states, and set up scenes. Training-mode features and other modders'
features are meant to be built on this. It is a public API: `gd.api_version` is **1**, and anything
that changes is listed under [Deprecations](#versioning-and-deprecations).

- Engine: `melee/pc/platform/gw_script.c` (+ `gw_script_pad.c`, `gw_console.cpp`, `gw_kit.c`,
  `pc/gameworld/script_game.c`). Lua itself is vendored at `melee/pc/third_party/lua-5.4.7` (MIT).
- Examples: `melee/pc/scripts/examples/` (shipped in releases as `scripts/examples/`, and compiled
  into the exe as `builtin:<name>`).

---

## Quick start

1. Create `scripts/hello.lua` next to `melee-pc.exe`:

   ```lua
   -- @name: Hello
   -- @version: 1.0.0
   function on_draw()
     gd.text(8, 8, "hello from Lua - frame " .. gd.frame(), 0xFFFFFFFF)
   end
   ```

2. Start the game. Every `scripts/*.lua` (and every `scripts/<id>/` with a `mod.json`) loads at boot.
3. Press **`** (the key left of 1) for the console. Type `reload hello` after editing the file.
   `= gd.player(1)` prints player 1's state. `help` lists the commands.

The examples are a good second step: in the console, `load builtin:state_overlay`,
`load builtin:tm_lite`, `load builtin:scene_setup` (then `fdtrain`).

---

## Where scripts come from

| place | what | manifest |
|---|---|---|
| `scripts/<name>.lua` (next to the exe, or `MELEE_SCRIPTS_DIR`) | a single-file script, loaded at boot | `-- @key: value` header lines |
| `scripts/<id>/mod.json` + `main.lua` | a script with a manifest, loaded at boot | `mod.json` |
| `mods/<id>/scripts/*.lua` | scripts inside a mod (below), loaded when that mod is mounting | the mod's `mod.json` |
| `scripts/examples/` | not loaded automatically; `load examples/<name>` | either |
| `builtin:<name>` | the examples, compiled in | either |
| `MELEE_SCRIPT=a;b;builtin:c` | extra scripts for a run (tests, agents) | either |
| `MELEE_PAD_SCRIPT=<file>.lua` | an input script (see [Input scripts](#input-scripts)), always "gameplay" | — |

`MELEE_SCRIPTS=0` turns boot loading off (console and `MELEE_SCRIPT` still work).

### Scripts as mods

A script is just another kind of mod in the mods folder (`docs/mods-packaging.md` is the layout):

```
mods/
  enabled.txt              the enabled set (absent = everything enabled)
  tm_lite/                 the folder name is the mod id
    mod.json               { "name": "TM-lite", "version": "1.0.0", "kind": "script", ... }
    scripts/main.lua       every scripts/*.lua runs; script ids are "tm_lite/main"
```

`"kind": "script"` means the mod carries only scripts. **Any** mod (a fighter, a stage, a misc mod)
may also ship a `scripts/` folder beside its `files/`; the scripts are never mounted as disc files.
The in-game mods menu and the mods browser handle script mods like any other: toggling the mod
toggles its scripts (at the next boot).

### The manifest

`mod.json` (a flat object) or, for a single file, header comments `-- @key: value` at the top:

| field | default | meaning |
|---|---|---|
| `name`, `version`, `author`, `description` | id, "", "", "" | shown in the console and the mods menu |
| `kind` | — | `"script"` for a scripts-only mod |
| `api_version` | 1 | the API the script was written for; a script asking for a newer one than the build has is refused with a message |
| `gameplay` | false | **true if the script changes the game** (see below) |
| `rollback_safe` | false | a gameplay script that promises to be deterministic under rollback (below) |
| `entry` | `main.lua` | for `scripts/<id>/` folders: the file to run |

Booleans may be written `true`/`false` or as strings (`"yes"`, `"true"`), so the file also parses
with the mods registry's strings-only reader.

---

## The sandbox

Scripts come from mods people download, so they run sandboxed:

- **Available:** the Lua base functions (`print`, `pairs`, `pcall`, `setmetatable`, ...), `string`,
  `table`, `math`, `utf8`, `coroutine`, and `gd`.
- **Not available:** `io`, `os`, `package`/`require`, `debug`, `dofile`, `loadfile`,
  `string.dump`, binary chunks (`load` takes text only). These libraries are not compiled into the
  exe at all. `collectgarbage` only answers `"count"`.
- **Files:** only the script's own data folder, through `gd.data_read` / `gd.data_write`
  (`scripts-data/<script id>/`, plain file names, 1 MB each).
- **Network:** none.
- **Isolation:** every script has its own globals and its own copies of the library tables; one
  script cannot see or break another. The string metatable is locked.
- **Budget:** each call into a script (a hook, a task step, a command) may run 2,000,000 Lua
  instructions or 50 ms, whichever comes first (`MELEE_SCRIPT_BUDGET`, `MELEE_SCRIPT_MS`). Over
  budget is an error. Total Lua memory is capped at 64 MB.
- **Errors** are reported per script in the console and the log, with the script, file, line and a
  traceback: `[tm_lite] on_tick: tm_lite:37: attempt to index a nil value`. The game carries on.
  A script that errors 20 times is switched off (`reload <id>` turns it back on).
- `math.random` is seeded with 0 at start-up, so a script using it is reproducible.

### Gameplay scripts, netplay and rollback

Anything that changes the game - `gd.input`, `gd.set_percent`, `gd.set_stocks`, savestates,
pause/step, `gd.scene_launch`, `gd.quit` - is refused unless the manifest says `"gameplay": true`.
Read-only scripts (overlays, loggers, readouts) can differ between two players online.

**The rule the engine implements:**

1. During a rollback session, **no script hook runs on a resimulated frame**. Hooks run once per
   real frame, at fixed points (below), so overlays and loggers never see a frame twice.
2. During a netplay/rollback session the gameplay writes are refused, **except** for scripts whose
   manifest also says `"rollback_safe": true`. That flag is a promise: the script derives
   everything it writes from game state each frame and keeps no Lua-side memory across frames
   (Lua state is not part of a savestate, so a script with counters would diverge on rollback).
   Savestates and pause are never available online.
3. Enabled scripts with both `gameplay` and `rollback_safe` are hashed by version and source
   into the netplay must-match set. Script ids label the diagnostic description. The console
   and offline-only scripts are excluded. An offline-only API stays unavailable online even
   when `rollback_safe` is true.

---

## Hooks

Define any of these as globals in your script; the engine calls them.

| hook | when | notes |
|---|---|---|
| `on_tick()` | each host script tick, before game logic | input polling (`gd.key_pressed`), UI state |
| `on_draw()` | after the game render; fallback at the next tick if no render hook ran | the only place `gd.text`/`gd.box`/... draw (the list is rebuilt every frame) |
| `on_frame_pre()` | at the start of every game-logic frame | before the fighters move |
| `on_frame()` | at the end of every game-logic frame | after the fighters moved; the frame-data point |
| `on_scene(kind, name, prev_kind)` | a scene started (also once when the script loads) | `name` like `"GS_TRAINING"` |
| `on_match_start()` | the first frame with fighters on stage | |
| `on_match_end()` | the match scene ended | |
| `on_savestate(slot)`, `on_loadstate(slot)` | after a savestate was taken / loaded | restore your own Lua state here |
| `on_unload()` | before the script is unloaded or reloaded | |

While the game is paused (`gd.pause`), `on_tick` and `on_draw` keep running; the frame hooks do not.
Engine events are queued and delivered after the logic frame, before `on_frame`:

| hook | arguments |
|---|---|
| `on_action_change(port, old, new, sub)` | action-state ids; `sub` identifies a subfighter |
| `on_hit(attacker, victim, info)` | attacker port or nil; victim port; `info.dealt`, optional `hitbox`, `item`, `attacker_sub`, `victim_sub`, and captured hitbox fields when available |
| `on_hitlag(port, entering, sub)` | entering/leaving hitlag |
| `on_land(port, motion, sub)` | landing action |
| `on_target_broken(handle, remaining)` | gameplay scripts only; scripted target broken |
| `on_all_targets_broken()` | gameplay scripts only; last scripted target broken |
| `on_enemy_defeated(event)` | gameplay scripts only; `{kind, handle}` |
| `on_enemy_hit(event)` | owning gameplay script; `{kind, handle, from, damage}` for a native direct primary-fighter hit on its Adventure enemy; `from` is a 1-based port |
| `on_boss_defeated(event)` | gameplay scripts only; `{kind, port, x, y}`; kind is `master_hand`, `crazy_hand`, or `fighter_<kind>` |
| `on_camera_complete(kind)` | owning script; `"move"` or `"path"` |
| `on_hot_reload(ok)` | completion of the LAB hot reload |

Use `gd.boss_hold` in the boss-defeat callback to delay progression for a scripted bonus,
then `gd.boss_release` to let the normal flow continue.

---

## API reference (`gd`, API 1)

Ports and players are numbered **1-4** (fighter slots 1-6 for `gd.player`).

### State

| function | returns |
|---|---|
| `gd.api_version` | `1` |
| `gd.frame()` | logic frames since boot |
| `gd.time()` | seconds (wall clock; for overlays, never for gameplay) |
| `gd.scene()` | `{kind, name, mode, mode_name, epoch}` - e.g. `name = "GS_TRAINING"`, `mode_name = "GM_TRAINING"`; `epoch` counts scene changes |
| `gd.match()` | `{active, frame, stage, netplay}` - `frame` counts from the first frame with fighters |
| `gd.players()` | a list of player tables for every fighter on stage |
| `gd.player(port)` | one player table, or `nil` |
| `gd.char_name(id)` | `"Fox"` etc. for a character id |
| `gd.pad(port)` | what the game read from that controller this frame: `{buttons, x, y, cx, cy, l, r, A=bool, B=..., START, L, R, Z, UP, DOWN, LEFT, RIGHT}` |
| `gd.paused()` | bool |
| `gd.perf([n])` | host diagnostics for up to `n` (default 120, 1-240) recent presented frames: `{fps, target (0 = uncapped; the sim stays 60 Hz), frames}`, oldest first. Each frame: `total_ms` (tick to tick, pacing included), `logic_ms` (game thread outside GX submission), `gx_ms` (`GXBegin` / `GXCallDisplayList`), `submit_ms` (`aurora_end_frame` enqueue), `worker_ms` (render-worker work incl. Present; asynchronous, overlaps the others, never add it to them), `draw_calls`, `vertices` (decoded GX vertices), `fx_particles`. `worker_ms` and `vertices` read 0 until the shared Aurora has the new counters. Sampling starts on a `gd.perf()` call or Video > Show FPS = Performance and stops about 120 frames after the last read; host-only, not in savestates or rollback, never for gameplay decisions. The LAB's DISPLAY > Performance (F4) panel and Show FPS 1 / 2 outside the LAB are drawn with the kit from it |
| `gd.script()` | this script's `{id, name, version, author, gameplay, rollback_safe}` |
| `gd.buttons` | the bit values: `gd.buttons.A == 0x100` ... |
| `gd.items()` | every live item (articles and projectiles too), in the engine's item-list order: `{id, kind, owner_port (1-6, 0 unowned), x, y, z, vx, vy, facing, frame_alive, state}`; Geno articles add `geno_kind` (zero-based article index) and `geno_profile`. `frame_alive` is exact for Geno articles; for other items it counts frames since the script engine first saw the item in this scene. `state` is the item's motion state |
| `gd.fx()` | every live Geno effect attachment (one row per package attachment, its emitters aggregated): `{package, owner_kind ("fighter"/"article"/"unknown"), owner_port, joint (-1 for an article), x, y, z (world origin), facing, live_particles, emitter_count, bbox}`; `bbox = {min={x,y,z}, max={x,y,z}}` over the particles' world positions, absent with no particles. A detached effect stays listed until its last particle dies |

A **player table**: `port`, `char` (character id), `char_name`, `kind` (internal fighter kind),
`costume`, `cpu` (bool), `x`, `y`, `vx`, `vy`, `percent`, `stocks`, `facing` (1 right / -1 left),
`action` (the action-state id), `action_frame` (frames since the action state began, from 0),
`anim_frame`, `airborne` (bool), `hitlag` (frames left).

### Drawing (call from `on_draw`)

Coordinates are a 640x480 virtual screen scaled to the window. Colours are `0xRRGGBBAA` numbers
(`gd.rgb(r, g, b [, a])` builds one) or `{r=, g=, b=, a=}`.

| function | |
|---|---|
| `gd.text(x, y, text [, color [, size]])` | `size` 1 = 13 px at 640x480 |
| `gd.box(x, y, w, h [, color])` | outline |
| `gd.fill(x, y, w, h [, color])` | filled (default translucent black) |
| `gd.line(x1, y1, x2, y2 [, color])` | |
| `gd.label(text)` | the run label: top-left caption and window title ("" clears) |

### Kit drawing (`gd.kit`, call from `on_draw`)

The port's own menus are drawn from the art pipeline's **kit** (`menu/` → `_build/ui`): the font
atlas and its text roles, the palette and section colours, the list row template, the 9-slice
frame, the icons. `gd.kit` draws the same kit over any scene — a match included — so a script's
UI looks like the menus. Same 640x480 screen as `gd.text`; kit and plain draws keep their call
order. It is drawing only (no game state is read or written, nothing touches the game's memory),
so every script may use it, online too.

It follows the kit's own rules: text is set from the font manifest (kerning, `?` for a missing
character, `hero`/`display` caps-only, the **fit rule** — too wide steps down to the next smaller
role of the same face, then truncates with `…`), glyphs are italicised by the kit's shear about
the baseline, and I4 / I8 / IA4 / IA8 textures are **masks**: RGB from the tint, alpha = texture
alpha × tint alpha. Other formats are modulated by the tint.

| function | |
|---|---|
| `gd.kit.available()` | `true`, or `false` and why (the kit's files were not found) |
| `gd.kit.text(x, y, text [, role [, color [, align [, opts]]]])` | `y` is the **baseline**. `role` (default `"body"`) is one of `gd.kit.roles`; `color` defaults to `"bone"`; `align` `"left"`/`"center"`/`"right"` of `x`; `opts` `{max_w =, shear =}` (`max_w` applies the fit rule; `shear` defaults to the kit's `gd.kit.shear`, 0 = upright). Returns the width |
| `gd.kit.measure(text [, role [, max_w]])` | width, line height, and the text as the fit rule would set it |
| `gd.kit.metrics(role)` | `{size, ascent, descent, cap, line}` at 1x |
| `gd.kit.image(name, x, y [, w [, h [, opts]]])` | any kit texture by file name (`"glyph_a"`, `"frame_edge_h"`, your mod's). Default size: its 1x size (the kit is authored at 2x) × `opts.scale`. `opts` `{tint =, scale =, flip_x =, flip_y =, shear =}`. Returns w, h, or `nil` when there is no such texture |
| `gd.kit.icon(name, x, y [, scale [, tint]])` | `ico_<name>` (`"lock"` → `ico_lock`), tinted `"bone"` unless its manifest or `tint` says otherwise |
| `gd.kit.panel(x, y, w, h [, style])` | a 9-slice panel. `style` `{prefix = "frame", piece =, tint =, fill =, shear =}`: pieces `<prefix>_corner_tl/_tr/_bl/_br`, `<prefix>_edge_h` (top; flipped vertically for the bottom), `<prefix>_edge_v` (left; flipped horizontally for the right) and an optional `<prefix>_fill` (stretched, tinted by `fill`). `piece` scales the frame (corner size in px; default the corner's 1x size, never more than half the panel). `fill` is a colour (default the Versus section's bg, a little translucent) or `false`. Missing pieces are skipped |
| `gd.kit.button(x, y, w, label [, state [, opts]])` | the kit's list row: `state` `true`/`"sel"` (gold face lifted off its gold_dk plate, ink label), `false`/`"ng"`, `"disabled"`. `opts` `{value =, h =, shear =, section =}` - `value` is drawn right-aligned. Returns the height |
| `gd.kit.list(x, y, w, items, selected [, opts])` | rows at the kit's pitch. `items` are strings or `{label =, value =, disabled =}`; `selected` is 1-based (0 = none). `opts` `{pitch =, h =, first =, visible =, shear =, section =}`. Returns the height used |
| `gd.kit.color(token)` | a colour token as `0xRRGGBBAA`, or `nil` |
| `gd.kit.texture(name)` | `{w, h, w1x, h1x, mask, tint}` or `nil` |
| `gd.kit.colors` | the palette (`ink`, `bone`, `muted`, `disabled`, `gold`, `gold_lt`, `gold_dk`, `danger`, `ok`), the sections (`gd.kit.colors.solo.face`, `.bg`, `.band`, `.face_hi` for `versus`, `solo`, `collection`, `options`, `data`) and the ports (`p1`..`p4`, `cpu`) |
| `gd.kit.roles`, `gd.kit.row`, `gd.kit.shear` | the text roles (smallest first); the row template `{h, pitch, label_x, label_base, lift}`; the kit's shear factor |

**Colour tokens** (anywhere a kit function takes a colour): `0xRRGGBBAA`, `{r=, g=, b=, a=}`, or a
string - a palette name (`"gold"`), `"@face"`/`"@bg"`/`"@band"`/`"@face_hi"` (Versus) or
`"<section>.<which>"` (`"solo.face"`), `"p1"`..`"p4"`/`"cpu"`, `"#rrggbb"`/`"#rrggbbaa"`, or a name
from the calling mod's palette (below).

**Your mod's own art.** A script mod can ship kit-format textures: `.gxtex` files made by
`melee/pc/tools/png2gx.py` (from 2x PNGs, as the kit's are) in a `ui/` folder beside its `scripts/`
(`mods/<id>/ui/`, or `scripts/<id>/ui/`). Texture lookups search the calling script's `ui/`
first, then `MELEE_MENUTEX_DIR`, `<exe>/ui` and `_build/ui`. So `gd.kit.icon("my_thing")` finds
`mods/<id>/ui/ico_my_thing.gxtex`, and `gd.kit.panel(x, y, w, h, {prefix = "my_frame"})` draws
the mod's `my_frame_corner_tl` ... `my_frame_fill`. Optional `ui/*_ui.json` manifests add:

```json
{
  "textures": [ { "name": "ico_my_thing", "size_1x": [16, 16], "tint": "accent" } ],
  "palette":  { "mine": { "accent": { "hex": "#38c9d9" } }, "warn": "#e5483b" }
}
```

`size_1x` is a texture's default draw size, `tint` its default tint (a token), and `palette`
names (flat, or grouped one level deep; `"#hex"` strings or `{hex}` / `{u32}` objects) become
colour tokens for that mod's scripts. Nothing else in the file is read.

The example `builtin:kit_hud` (`melee/pc/scripts/examples/kit_hud/`) puts a kit panel over the
match:

```lua
function on_draw()
  if not gd.kit.available() or not gd.match().active then return end
  local rows = {}
  for _, p in ipairs(gd.players()) do
    rows[#rows + 1] = { label = ("P%d  %s"):format(p.port, p.char_name),
                        value = ("%d%%"):format(math.floor(p.percent + 0.5)) }
  end
  local x, y, w = 16, 24, 236
  gd.kit.panel(x, y, w, 64 + #rows * gd.kit.row.pitch, { piece = 24 })
  gd.kit.icon("training", x + 14, y + 12, 0.25, "gold")
  gd.kit.text(x + 50, y + 34, "MATCH", "label")
  gd.kit.list(x + 12, y + 48, w - 24, rows, 1)
end
```

### Input

| function | |
|---|---|
| `gd.mouse()` | `x, y, buttons, wheel`: the pointer in the same 640x480 space as `gd.text` / `gd.kit` (-1000, -1000 when it is off the picture); `buttons` = 1 left + 2 right + 4 middle; `wheel` = notches this tick (+ up). Local UI input only: it never reaches the pads or a netplay peer. The kit's cursor shows during a match only while a script polls `gd.mouse()`, so poll it only while your menu is open. |
| `gd.key(name)`, `gd.key_pressed(name)` | the keyboard, only while the game window is focused, the console is closed and nothing is being typed (a name, a room code). The keyboard never drives the game, so every key is free for hotkeys. Names: `A`-`Z`, `0`-`9`, `F1`-`F12`, `KP0`-`KP9`, `SPACE`, `ENTER`, `TAB`, `ESCAPE`, `SHIFT`, `CTRL`, `ALT`, `LEFT`/`RIGHT`/`UP`/`DOWN`, `HOME`, `END`, `PAGEUP`, `PAGEDOWN`, `INSERT`, `DELETE`, `BACKSPACE` |
| `gd.input(port, spec [, frames])` | *gameplay.* Claim a controller from its first input. `spec` is `"A+B"`, a number (button bits), or `{buttons="A", x=, y=, cx=, cy=, l=, r=}` (sticks -127..127, triggers 0..255). The whole pad sample replaces the SDL controller, GameCube adapter, `MELEE_PAD_SCRIPT`, and `MELEE_PAD_LIVE`, even while focused. After `frames` completed logic frames (default 1), the claimed port stays connected and reports neutral input until released. Extra PADReads while paused do not consume the hold; `step n` consumes n completed logic frames. Rewind/rollback resimulation does not consume the live hold. Local diagnostic input, not rollback state. |
| `gd.release_pad(port)` | Release this script's or console session's claim early; the normal physical source resumes, or the port disconnects if none is present. A `gd.run` task also releases its claims when it ends; unloading, reloading, or disabling a script releases its claims. |
| `gd.release(port)` | Compatibility alias for `gd.release_pad(port)`. |
| `gd.press(port, buttons [, frames [, spec]])` | *in a task:* `gd.input` then wait that many frames |
| `gd.tilt(port, x, y [, frames])` | *in a task:* hold the stick |

### Tasks (scripts that wait)

| function | |
|---|---|
| `gd.run(fn)` | start `fn` as a task; it resumes once per logic frame |
| `gd.wait(n)` | *in a task:* wait `n` frames |
| `gd.wait_until(fn [, timeout])` | *in a task:* wait until `fn()` is true; `false` after `timeout` frames |

### Gameplay (need `"gameplay": true`)

| function | |
|---|---|
| `gd.set_percent(port, p)`, `gd.set_stocks(port, n)` | damage clamped to integer 0-999; stocks to 0-99; forks the rewind timeline |
| `gd.set_damage(port, n)` | offline; sets the same real fighter/player damage as `set_percent` (integer 0-999), keeping HUD, knockback and stamina HP in agreement. A boss at zero remaining HP still needs a hit to die |
| `gd.hit(port, {damage=, angle=, kbg=, bkb=, from=})` | offline; injects a normal-element hit through Melee's collision result and fighter hit processing. Required integer fields: damage 0-500, angle 0-361, kbg/bkb 0-1000. Optional `from` is a fighter slot; omitted means environment damage. Returns false for a missing fighter/source or refused damage, true after processing. Applies damage state, HP/percent and hitlag, not just a HUD edit; forks rewind |
| `gd.boss_hold([seconds])` | offline; hold the pending boss-defeat transition, default 60 seconds, range 1/60-600; timeout counts match logic frames. Returns whether accepted |
| `gd.boss_release()` | offline; release the boss-defeat hold; returns whether accepted |
| `gd.savestate([slot])`, `gd.loadstate([slot])` | slots 1-4, taken/loaded at the next frame boundary; a state from another scene is refused; never online |
| `gd.pause()`, `gd.resume()`, `gd.step([n])` | freeze the game logic; `step` runs `n` frames and stays paused |
| `gd.scene_launch(text or table)` | jump to a scene: `"mode=training;p1=fox;p2=falco/cpu;stage=fd"` or `{mode="training", p1="fox", ...}` (the `MELEE_SCENE` grammar, `_research/scene-launch.md`). It goes through the game's own soft reset, so it is safe from anywhere; returns the text |
| `gd.scene_clear()` | stop seeding scenes (the next VS/Training starts normally) |
| `gd.training_select(["kit" \| "native"])` | *(any script - menu routing only)* Training's character and stage select on the port's own kit screens or the native ones; returns the current choice and stays until changed. On the kit, Training keeps its rules: the player who entered picks, the CPU dummy's card picks the dummy, nothing else can be added. Also `select=kit` in the scene grammar (`gd.scene_launch{mode = "training", at = "css", select = "kit"}`, `MELEE_SCENE`), `MELEE_TRAINING_SELECT=kit` at start, and `gw_Frontend_SetTrainingSelect(1)` for native code |
| `gd.quit()` | close the game like the window's close button |
| `gd.fly(port [, mode])` | debug movement (noclip). With no mode it reads: `true` while that port's fighter flies. `mode` is `true` / `"on"`, `false` / `"off"` (drop into Fall there), `"place"` (land on the floor below) or `"toggle"`; returns the new state. Flying: stick moves it at the fly speed (A ×0.25, B ×4), no gravity, no stage collision or ledges, no blast-zone KO, no hurtboxes unless solid; the camera follows it past the stage's bounds. Offline only, every mode (melee `docs/geno.md` 14.17) |
| `gd.teleport(port, x, y)` | put the fighter exactly there. It keeps flying if it was; one on foot falls from there. Offline only |
| `gd.fly_speed([n])`, `gd.fly_solid([bool])` | the fly speed in units per frame at full stick (0.05-200, default 2), and whether hurtboxes stay on while flying (default off); each returns the current value. Offline only |
| `gd.fly_target(port, x, y)` | enables flight and moves toward a fixed world position at `fly_speed`, clamping the final step to avoid overshoot; holds that position once reached. Finite coordinates within ±10000. Offline debug control |
| `gd.fly_attack(port, on [, damage, radius])` | enables/disarms an actual native fighter hitbox while flying; enabling also starts flight. Defaults: 3 damage, radius 6; each is bounded to 1–30 (damage integer). Each non-hitlag physics frame rearms the capsule, clears both victim histories, and allocates a fresh attack instance. Fighter/item collision, shields, hitlag and invulnerability remain native. This is a debug attack, not a character's normal move animation |
| `gd.fly_state(port)` | reads `flying`, `targeting`, `attacking`, target `x/y`, `damage`, `radius`, and `pulses`. Inactive cursor fields are zero/false. Pulses count rearming attempts, not confirmed hits |
| `gd.fly_clear(port)` | disarms the cursor and clears its target while retaining ordinary stick-controlled flight. `gd.fly(port,false)` or F11 leaves flight and disarms it. New cursor controls are script-owned; unloading/disabling the owner clears them, and scene changes reset all cursors |

### Stage content (offline, gameplay mods)

A gameplay mod can add collision lines and breakable targets to the running stage: platforms and
walls for a custom map, or a Break-the-Targets course on a VS stage. These calls need a mod with
`"gameplay": true` in its manifest (a pad script counts). They work only in an active offline match.
The console and every netplay or rollback session are refused, even for a `rollback_safe` script.
Coordinates are world units, finite and within ±100000. Each write forks the LAB's rewind timeline.

| function | |
|---|---|
| `gd.stage_add_platform(x, y, width [, {passthrough=, ledges=, draw=}])` | a horizontal floor centred on `(x, y)`; returns a handle, or `nil, reason`; optional boolean `draw=false` hides its debug slab while preserving collision |
| `gd.stage_isolate([on])` | owning offline gameplay mod only: suppress the supported FD host's original scenery and collision, preserving added models/floors and native camera/blast zones. `true` acquires isolation; returns `false` for an unsupported stage and raises an error if another script owns it. `false` restores and returns `false`; no argument queries caller-owned isolation. First script error, unload, scene teardown or offline-boundary loss restores the original stage. Add your own floor before enabling; the console cannot own isolation |
| `gd.stage_add_model{file=, symbol='map_head', group=0, joint='root', x=0, y=0, z=0, scale=1, rot=0, platform=}` | Draw a JObj branch from a root-level stage or mounted mod `.dat` filename (5-30 bytes, no path separators or `..`) in the stage world pass (lit, fogged). `joint` is a group-local zero-based index, `JOBJ_<index>`, or `root`; `rot` is degrees about Z; `scale` is >0 and <=100, `group` 0-255, joint index 0-4095. Returns a model handle or `nil, reason`. `platform` attaches a `gd.stage_add_platform` floor: `gd.stage_move(model, x, y)` carries it and `gd.stage_remove(model)` removes both; an attached floor does not draw its slab. Each DAT is loaded once per scene into heap 0 and released at scene end; up to 8 DATs (8 MiB each) and 64 models. Branches with JObj instance references are refused. `gd.spawn_target` draws Mato's Target Test model (GrTMr.dat) |
| `gd.stage_add_line(x1, y1, x2, y2, kind [, opts])` | `kind`: `"floor"` (left to right), `"ceiling"` (right to left), `"right_wall"` (top to bottom) or `"left_wall"` (bottom to top); a wrong direction is an error. Floor options include `passthrough`, `ledges` and boolean `draw` |
| `gd.stage_move(handle, x, y)` | move a line midpoint or model to `(x, y)` (targets cannot be moved); returns whether it exists. A model carries its attached floor; a moved floor carries a standing fighter |
| `gd.stage_remove(handle)` | remove a line, target or model (a removed target raises no event); removing a model removes its attached floor; returns whether it existed |
| `gd.spawn_target(x, y)` | a target (Target Test's Mato item) held at `(x, y)`; returns a handle, or `nil, reason` |
| hook `on_target_broken(handle, remaining)` | after the frame a target was hit in |
| hook `on_all_targets_broken()` | after the last active scripted target breaks |

- **Floors.** `passthrough = true` makes a floor you can drop through (down on the stick) and land
  on from below. `ledges = true` makes both of its ends grabbable.
  `draw = false` hides only that floor's debug slab; absent or true draws it normally.
  A supplied nonboolean `draw` is an error. This does not hide runtime model meshes;
  `gd.stage_view(false)` hides the stage-content geometry more broadly.
- **Moving platforms.** A line moved during a frame carries whoever stands on it by the same amount
  (`mpGetSpeed`), exactly as the stage's own moving platforms do.
- **Handles.** Handles are never reused, even across a savestate load. A script that keeps handles
  across a load should check them before it moves or removes the objects.
- **Stage bounds.** The stage's camera bounds and blast zones do not change.
- **Looks.** Lines and targets are real geometry, drawn by the game in the stage's world pass.
  They show in screenshots, are fogged and depth-tested, and are blended at 120 fps.
  - Floors are slabs under the line: gold when solid, cyan when you can drop through.
  - A wall is a thin red bar, a ceiling a thin violet one.
  - A target uses the real Mato model loaded from `GrTMr.dat`.
  - `gd.stage_view([geometry [, overlay]])` turns the geometry off, or the old host-overlay debug
    strokes on (off by default); it returns both settings.
- **Limits.** Up to **200 lines** and **32 targets** at once.
  - **Lines:** each line takes one of mpLib's 256 collision joints, so a stage gets
    `min(200, 256 - its joints)`; inspect the actual stage reservation in the log.
  - **Targets:** the pool is 32. The next ceiling is the game's item limit for the category
    (`Item_804A0C64`, from ItCo's common data).
- **Example:** `melee/pc/scripts/examples/fd_stage_content/` adds 3 platforms (passthrough with
  ledges, passthrough, solid with ledges) and 10 targets to Final Destination. Copy it to
  `mods/fd_stage_content` beside the exe (the manifest entry is `scripts/main.lua`).

### Camera (offline, gameplay mods)

Camera writes need `"gameplay": true` (or the console) and are refused during netplay or rollback.
`gd.camera_get()` works in any script. It returns `{eye={x,y,z}, interest={x,y,z}, fov, roll,
mode}`, or `nil` before a match camera exists. Coordinates are world units, `fov` is degrees and
`roll` is radians.

| function | |
|---|---|
| `gd.camera_detach()` | take control at the current pose. The first write detaches by itself |
| `gd.camera_set{eye=, interest=, fov=, roll=}` | set any of the fields |
| `gd.camera_move{to={...}, frames=N, ease="linear"\|"in"\|"out"\|"inout"}` | tween the given fields over 1-6000 frames; calls `on_camera_complete("move")` |
| `gd.camera_path({{frame=0, eye={...}, interest={...}, fov=45}, ...})` | 2-64 keys starting at frame 0 with strictly rising frame numbers (up to 36000); calls `on_camera_complete("path")` |
| `gd.camera_follow(point \| gd.player(n) \| gd.items()[i] [, offset])` | track a point, a fighter or an item (`gd.items()` rows now carry `id`); the eye keeps its offset. If the target disappears, the last pose holds |
| `gd.camera_shake(intensity, frames)` | a deterministic decaying shake; nonnegative intensity and 0-6000 logic frames |
| `gd.camera_bounds(bool)` | `true` lifts the stage's camera clamps and extends the far plane; `false` restores the bounds policy |
| `gd.camera_attach([frames])` | blend back to the match camera (default 30 logic frames, range 0-6000; 0 is instant) |

- **Normal camera:** while detached, the normal camera keeps updating underneath, so attaching
  returns to it. The camera is also restored when the owning script unloads, when its `gd.run`
  task ends, and on a scene change.
- **Ownership:** only one script may own the camera. Another script's write is refused until it
  is released. Camera state is in snapshotted game memory; Lua bookkeeping is not.
- **Frame rate:** movement advances per game-logic frame; higher presentation rates interpolate.
- **Example:** `melee/pc/scripts/examples/camera_cinematic` (the console command `fdcine`).

### Adventure enemies (offline gameplay mods)

`gd.spawn_enemy(kind, x, y [, {facing = 1 | -1}])` returns a handle, or `nil, reason`. At most
32 script enemies can be alive at once.

- **Kinds:** `goomba`, `redead`, `octorok` (these three come from ItCo), and `koopa`,
  `like_like`, `polar_bear`. The last three load their Adventure stage's file on first use, and
  every item that file defines is registered too (Koopa's shell, for example).
- **Liveness:** `gd.enemy_alive(handle)` is a read-only query for a script-owned enemy.
  It returns false when the native pool entry is missing or inactive, including destruction
  without a stock defeat. It requires an active offline gameplay mod script; the console
  cannot call it. Handles are positive integers. A known handle owned by another script
  is refused. Querying does not queue a defeat event or change the game state.
- **Removing:** `gd.enemy_remove(handle)` returns whether the owned enemy was alive,
  and does not count as a defeat. Removing an already destroyed owned handle returns
  false and releases its ownership record. Known other-script handles are refused.
- **Defeats:** `on_enemy_defeated{kind=, handle=}` fires once, at the monster's stock defeat.
- **Native hits:** `on_enemy_hit{kind=, handle=, from=, damage=}` queues a direct
  primary-fighter hit for the owning script, including a killing blow whose actor
  retires before event delivery. `from` is a 1-based port. This event does not
  resolve generic projectile ownership or fire for scripted `gd.enemy_hurt`.
- **Rules:** these need a gameplay mod, in an active offline match; the console cannot call them.
- **Savestates:** enemies are saved with the match, but Lua tables are not. Rebuild your
  bookkeeping in `on_loadstate`. The current native ownership registry is scene-local;
  restoring an enemy after its ownership record was removed requires reconstruction
  and is not established by the liveness API. Scene changes clear ownership, and script
  unload/disable explicitly removes its remaining owned enemies without defeat events.

Koopa's shell transition is not the stock defeat path, so it does not emit an enemy-defeated
event at that transition. Explicit removal emits no defeat event and returns false for a missing handle.

Example: `melee/pc/scripts/examples/enemy_spawn_demo`.

Owned enemy combat helpers use the same offline gameplay restrictions and handle
ownership as the liveness API:

| function | result / action |
|---|---|
| `gd.enemy_state(handle)` | `nil` for a missing/retired actor, otherwise `{handle, alive, kind, state, damage, hits, attack_id, last_victim, received, last_attacker, last_damage, x, y, vx, vy, facing, vulnerable}`; `state` is the native item motion ID, victim/attacker are 1-based ports (0 when absent), counters describe contacts rather than ability charges |
| `gd.enemy_strike(handle, port, {damage=, angle=, kbg=, bkb=, reach=})` | boolean; an owned enemy's bounded damage/knockback attempt against a nearby fighter, using the native fighter damage path |
| `gd.enemy_hurt(handle, {from=port, damage=, angle=, kbg=, bkb=, reach=})` | boolean; a nearby primary fighter's bounded scripted damage attempt against the owned enemy, using its native hurt path |

All combat fields are required: integer damage 1-30, angle 0-361, kbg/bkb
0-1000, finite reach 1-30 world units. Native checks include actor liveness,
range, facing and applicable vulnerability/hitlag conditions; false means the
attempt was refused. A controller should spend its own charge only on acceptance
or restore it on refusal. Scripted enemy hurt is distinguished from natural
contacts, so these helpers do not themselves establish a recursive charge source.
The state table is an observation, not a persistent enemy snapshot.

### Menu and netplay state

| function | returns / action |
|---|---|
| `gd.menu()` | `{title, screen, cursor, item, native_menu, native_hovered}` for the current frontend/native menu |
| `gd.netplay()` | `{phase, status, code, host, rematch, random, lobby, me, game, turn, left, countdown, ck, color, players, stages, groups, cursor}`. `players[1]` is host, `[2]` guest (`ck, color, locked, ready`). Stage values: 0 free, 1/2 struck, 3 banned, 4 picked; groups: 0 starter, 1 counterpick. Stage cursor is 1-based |
| `gd.netplay_act(action, ...)` | `"char", ck, color`; `"stage", index` (1-based); `"ready", bool` (default true); `"code", text`. Uses the lobby's normal validation; returns local acceptance, not peer acknowledgement. Menu routing, no gameplay manifest required |

### LAB inspection and control

These are public API 1 functions, registered on `gd` alongside the rest; `gd.lab_api` is 1.
The game repo's `docs/geno.md` section 14 describes the detailed field tables and the LAB UI.
Reads work in ordinary scripts unless marked offline. Offline writes require `gameplay: true`
or the console, and remain refused during netplay/rollback even for `rollback_safe` scripts.

| function | meaning |
|---|---|
| `gd.debug_draw(port [, flags])` | read/set the fighter's develop-draw flags (low 8 bits); nil without the fighter; setting is offline |
| `gd.debug_stage([flags])` | read/set stage debug flags (low 5 bits); nil without a match camera; setting is offline |
| `gd.hitboxes(port [, all])` | active hitboxes; `all=true` includes all slots 0-4, enabled or not; nil without fighter |
| `gd.hurtboxes(port)` | capsules: `{id, bone, state, height, grabbable, ax, ay, az, bx, by, bz, radius}` |
| `gd.joints(port [, fresh])` | joint positions and projected coordinates: `{index, parent, valid, x, y, z, sx, sy, on}`; list index = joint index + 1. `fresh=true` updates matrices first and is offline-only; otherwise unused joints may have old matrices |
| `gd.dobjs(port)` | draw objects (`index, hidden, render, tobjs`) plus `models` part states and `costume` texture-animation transforms |
| `gd.project(x, y [, z])` | `screen_x, screen_y, visible, depth` in 640x480 coordinates; z defaults 0; nil without camera |
| `gd.attrs(port)` | fighter's named common attributes as `{name=value}` |
| `gd.motion_name(id [, port])` | action name; optional fighter selects its special/Geno table |
| `gd.motion_list(port)` | valid actions as `{id, name, group, anim_id, anim_name}`; groups `common`, `special`, `mex`, `geno` |
| `gd.timeline(port [, motion])` | script timeline for current/specified action: motion/animation ids and names, events, length and stop reason; current action also has `end_frame` |
| `gd.set_motion(port or {ports}, motion [, frame [, rate [, lift]]])` | offline; queue motion at next boundary, step to frame (default 1, clamped 1-600), then pause. Rate defaults 1, lift 0; lift raises grounded fighters for aerials. Returns true or false, reason. It changes motion directly; entry-specific setup may be absent |
| `gd.mirror_pad(from, to [, take])`, `gd.mirror_pad()` | offline; mirror ports 1-4 to a human destination; `take=true` also neutralises source. No args disables mirroring |
| `gd.lab_request([clear])` | whether the frontend/environment requested LAB; optional clear consumes request |
| `gd.lab_mode()` | whether LAB is the current mode, including its select screens |
| `gd.lab_leave([where])` | gameplay; leave LAB for `"css"` (default), `"sss"`, `"menu"` or `"restart"`; returns whether a LAB match was ended |
| `gd.lab_common()` | loaded common constants: L-cancel window/divisor, hitstun multiplier, knockback speed/decay, stick/tech/SDI thresholds, ASDI scale and stick dead zones |
| `gd.floor_below(x, y [, depth])` | first floor y within depth (default 200), or nil; active match only |
| `gd.set_shield(port, health)` | offline; set shield health (negative becomes 0), fork rewind |
| `gd.kb_preview(port, spec)` | offline; knockback/flight estimate without applying a hit. Spec: `attacker, damage=10, angle=45, kbg=100, bkb=0, wbk=0, percent, extra=90, x, y, dir, di`; omitted position/percent uses victim. DI: `"none"`, `"in"`, `"out"`, `"survival"`, or `{x,y}`. Returns kb, level, tumble, hitstun, angles, velocity, weight, zones, points and optional blast crossing. Preview does not simulate stage collisions |
| `gd.rollbacks([n])` | newest-first rollback diagnostics (default 120, max 600): total, list and optional first mismatch; read-only, online too |
| `gd.rollbacks_clear()` | clear host rollback diagnostics |
| `gd.lab_env(name)` | environment string `MELEE_LAB_<name>` or nil; no access to other environment families |
| `gd.lab_now([long])` | local time string `YYYYMMDD-HHMMSS`, or `YYYY-MM-DD HH:MM:SS` with true; labels only, not deterministic gameplay |
| `gd.lab_peek(address [, bytes])` | hex text of guest MEM1 bytes (default 16, clamped 1-64); nil outside MEM1; read-only diagnostic |

### Rewind, reload and persistent states

| function | meaning |
|---|---|
| `gd.history([frames [, interval]])` | inspect history depth, now/oldest/head, back/fwd, keys, memory/timings, replaying and busy. Setting depth/interval is offline; depth 0 stops recording |
| `gd.step_back([n])` | offline; request n frames back (default 1), pause; true or false, reason |
| `gd.rewind_to(frame)` | offline; request retained frame (forward too); stays paused; true or false, reason |
| `gd.rewind_live()` | offline; branch here, discard future logged input; true |
| `gd.rewind_test([frames [, keep_running]])` | offline exactness check: default 90 further frames, rewind/resimulate and compare state bytes. Unpauses to run; pauses after unless keep_running; true or false, reason |
| `gd.rewind_test_result()` | `{phase, pass, diff, diff_compared, text}`; pass present once available |
| `gd.hot_reload([seconds])` | offline; rewind (default 2 seconds), reload Geno data and LAB script, replay recorded input. Incompatible layout restarts match. Returns true, start frame or false, reason |
| `gd.hot_reload_status()` | `{phase, ok, text}`; phase 0 idle |
| `gd.state_save([name [, description]])` | offline; queue a persistent state for next boundary, return generated `.gdst` filename or false, reason |
| `gd.state_list()` | saved files with name, what, frame, time, saved, stage, fighters and compatibility `ok, why` |
| `gd.state_load(file)` | offline; validate build/disc/mods/Geno/match before queueing load; true or false, reason |
| `gd.state_delete(file)` | offline; delete a saved state; true or false, reason |
| `gd.state_rename(file, name)` | offline; change display name, retain filename; true or false, reason |
| `gd.state_gen()` | state-library change counter (refresh a UI list when it changes) |

State files live below the script's data folder in `states/`. Lua tables are not snapshotted:
use `on_loadstate` to restore script bookkeeping. Rewind and other gameplay writes can branch
history; a retained future is not guaranteed after a write.

### Console and files

| function | |
|---|---|
| `gd.log(...)` / `print(...)` | to the console and `melee-pc.log`, prefixed with the script id |
| `gd.command(name, fn [, help])` | add a console command; `fn(arg_string)` |
| `gd.data_read(name)`, `gd.data_write(name, text)` | the script's data folder |
| `gd.data_write_atomic(name, text)` | like `data_write`, but writes a temporary sibling file, checks the write/flush/close results, and only then replaces the target, returning `true`, or `false, why` on failure with the previous file intact. Atomic against a torn write (a reader sees the old or the new file, never a partial one); not a power-loss durability guarantee |
| `gd.screenshot([name])` | a PNG of the final frame into the data folder; returns `ok, path` (capture is queued for the next presented frame; it is not a synchronous file-write result) |

---

## Timing and turbo

Lua input durations count **completed logic frames**, not render ticks or PADReads.
`gd.input(1, {buttons="B", y=127}, 3)` holds that full sample for three logic frames even
when the game is paused and stepped one frame at a time. The claim then remains neutral.
Legacy `.txt` scripts and `MELEE_PAD_LIVE` retain their PADRead-based behaviour.

`MELEE_FPS=u` uncaps interpolated rendering while realtime logic remains 60 Hz.
`MELEE_TURBO=1` (or game `--turbo`) accelerates scripted/LAB batch logic on a virtual clock,
mutes audio, and defaults to presenting every eighth game frame. It requires `MELEE_PAD_SCRIPT`
or `MELEE_LAB_BATCH` and refuses netplay/Slippi/fake rollback. `MELEE_TURBO_RENDER=0` never
presents; hidden/minimised windows do not present. Unpresented match frames still run render
callbacks but skip display lists/skinning unless `MELEE_TURBO_DRAWS=1`. Wall-clock `gd.time`,
render-tick polling and `gd.perf` are not deterministic simulation clocks.

The workspace wrapper `run.sh --test` sets turbo by default, and `--realtime` clears it.
Headless engine tests have no paced frame driver and do not enter turbo simulation.
See [tools/port/README.md](../tools/port/README.md) for command placement.

## Input scripts

`MELEE_PAD_SCRIPT` used to take only fixed-frame text files (`<frames> <buttons_hex> [x y [l r]]`
per line). Those still work exactly as before. A `.lua` file instead runs as a gameplay script whose
tasks can wait on the game:

```lua
gd.run(function()
  gd.wait_until(function() return gd.scene().name == "GS_MEMCARD" end, 600)
  while gd.scene().name == "GS_MEMCARD" do
    gd.press(1, "A", 4)
    gd.wait(20)
  end
end)
```

(`examples/memcard_skip.lua`, the state-aware form of `_build/pad_card.txt`.) `MELEE_PAD_LIVE`
(a file re-read every frame) is unchanged.

---

## The console

- **In game:** **`** opens and closes it (Esc also closes). While it is open the keyboard types
  text and does not drive player 1. Up/Down recall history.
- **Local socket (for tools, tests and agents):** off by default. `MELEE_CONSOLE_PORT=51700` (or the
  launcher's option) listens on **127.0.0.1 only**. Send one command per line; the reply is the
  command's output lines followed by `>>> ok` or `>>> error`. Up to 4 clients; one command per
  client per rendered frame.

  ```
  python melee/pc/scripts/console.py 51700 "state" "savestate 1" "input 1 none 40 127 0" "step 30" "= gd.player(1).x" "loadstate 1"
  ```

Anything that is not a built-in runs as Lua in the console's own environment (it persists between
lines; the console may use the gameplay functions offline). `= expr` prints a value.

| command | |
|---|---|
| `help`, `api` | |
| `scripts` | loaded scripts, origin, gameplay flag, OFF if switched off |
| `load <name>` | `hello` (scripts/hello.lua), `examples/tm_lite`, `builtin:state_overlay`, a folder, or a full path |
| `unload <id>`, `reload [id]` | |
| `state` | scene, mode, match, and every fighter's position/percent/stocks/action |
| `items`, `fx` | one line per `gd.items()` / `gd.fx()` row (or a short empty-list line) |
| `frame`, `pause`, `resume`, `step [n]` | |
| `savestate [1-4]`, `loadstate [1-4]` | |
| `scene <MELEE_SCENE text>`, `scene clear` | |
| `input <port> <buttons\|0xhex\|none> [frames] [x y]` | e.g. `input 1 A 5`, `input 1 none 40 127 0` (walk right) |
| `shot [path]` | screenshot (see `gd.screenshot`) |
| `label <text>` | the run label |
| `fly [port] [on\|off\|place\|toggle]`, `noclip ...` | debug movement: toggle with no argument; `fly speed <n>`, `fly solid on\|off`, `fly port <n>` (the default port and F11's), `fly readout on\|off`. Offline only; **F11** toggles the fly port in any offline match |
| `fly target [port] x y`, `fly attack [port] on\|off [damage radius]`, `fly clear [port]` | fixed-position debug attack cursor. Example: `fly target 1 12 8`, then `fly attack 1 on 3 6`; `fly 1 off` ends it. The readout displays attack state and pulse count |
| `tp [port] <x> <y>` | teleport (offline only) |
| `pos [port]` | the fighter's position, also copied to the clipboard as `x y` |
| `echo <text>`, `clear`, `quit` | |
| *commands scripts added* | listed by `help` |

Console `input` claims a port from its first command, including gaps between commands. A connected socket client keeps its claim until `gd.release_pad(port)` or disconnect; the in-game console keeps it until `gd.release_pad(port)` or game exit. During a claim, a physical pad on that port is ignored and the port reports connected neutral input whenever no hold is active.

For automated tests the pattern is: start the game with `MELEE_CONSOLE_PORT` and `MELEE_SCENE`,
drive it over the socket, assert on `state` / `= gd.player(n)` output, `quit` at the end.

---

## Examples

| example | what it shows |
|---|---|
| `state_overlay.lua` | a frame-data readout (action state, frames in state, anim frame, percent, position, velocity, hitlag) for every fighter; F2 toggles. Read-only - works online |
| `tm_lite/` | TM-lite: F5/F6 and F7/F8 save/load states, F9 resets percent, D-pad Down + R/L on port 1, a `tm` console command. A gameplay script |
| `scene_setup/` | `fdtrain [percent]`: jumps into Training (Fox vs a Falco CPU on Final Destination) and sets both to the percent once the match is live - `scene_launch` + `gd.run` + `wait_until` |
| `memcard_skip.lua` | an input script that presses through the memory-card prompt by watching the scene |
| `kit_hud/` | a panel in the menus' own style over the match (`gd.kit`: 9-slice frame, kit fonts, list rows, an icon); F3 toggles, F4 moves the highlight; `kit_training` routes Training through the kit's select. Read-only - works online |

---

## Offline character-part inspection (2026-09-30 addition)

`gd.parts(port[, refresh])` returns the loaded fighter's zero-based DObj records:
owning joint, shared material IDs, triangle count, posed bounds/area, area-weighted
body-region influences, visibility-state membership, support flags, and currently
owned item geometry. The array also has `geometry_signature`, `measurement_space`
and `coverage_mode` metadata. Pass `true` to refresh after pose/model/equipment changes.

`gd.dobj_solid(port, index, colour)` changes one draw's live solid colour without
mutating its shared material. `gd.dobj_solid_off(port, index)` restores that draw;
`gd.parts_clear()` clears the calling script's overrides. Colours do not preserve
texture details or alpha cutouts. All these operations are offline only.
Colour calls targeting an expired snapshot entry return false; invalid indices
and override-capacity errors remain errors. Refresh the snapshot to inspect newly
spawned equipment rather than reusing its old numeric index.

`gd.parts_id(port[, inverted])` uses the current snapshot for isolated, opaque ID
rendering; `gd.parts_id_off()` exits it. Complementary frozen captures support
visible-coverage analysis. Other HSD geometry is suppressed during capture.

`gd.dobj_tint(port, index, colour)` instead multiplies the normal material's RGB
by the supplied colour. Texture detail, lighting and alpha cutouts remain intact;
the supplied alpha channel is ignored. This needs a spare TEV stage and unused
konst register: unsupported materials return false and retain their original
appearance. The same `dobj_solid_off` / `parts_clear` functions remove a tint.
It does not recompile or mutate shared source materials.

### Offline roguelite integration

`gd.input_mask(port, bits)` consumes only selected D-pad bits (left=1, right=2,
down=4, up=8); zero releases the mask. It preserves sticks, triggers, face buttons
and the controller's connection. One script owns a port's mask; conflicting
owners return false. `gd.pad(port, true)` reads buttons before this mask, allowing
edge detection without replacing the player's pad. Scene changes, script cleanup
and `gd.release_pad` release masks. A menu that consumes Up while backing to its
root must keep masking that hold until release, or the game can treat it as taunt.

`gd.impulse(port, {x=, y=})` adds bounded velocity during ordinary locomotion:
delta x ±4, y ±3; resulting x ±5, y ±4. Grounded impulses require y=0 and also
update ground velocity. Damage, capture, attacking, rebirth, special fall,
jump squat and hitlag states refuse the operation without changing velocity.
It returns a boolean and does not teleport, change actions or replenish jumps.

`gd.cpu_mode(port, "stand"|"fight")` reinitializes the existing native CPU mode,
preserving its level. It returns false for a missing, human or subfighter entity.
Stand retains physics and vulnerability. These are the game's existing modes;
this API does not install 20XX or another training hack's AI.

`gd.cpu_technical(port, skill [, seed])` opts a primary native Fox/Falco fight CPU
into an original input assist. Skill is integer 0-3 (0 disables), and seed is
integer 1-2147483647 (default 1). It returns acceptance as a boolean. Another
script's ownership, unsupported/missing actors, replay, netplay and rollback
refuse configuration. Ownership and policy state clear on scene changes and
script unload/disable; a replaced fighter requires configuration again.

The policy observes descending eligible aerials or damage-fly hitstun, native
floor collision and tech lockout, then inserts one delayed trigger pulse per
accepted opportunity. Landing-cancel uses an analog pulse; ground-tech uses a
digital pulse only during native hitstun. Skills 1/2/3 have 6/4/2-frame observation
delays and seeded 60/80/95% opportunity acceptance. These are policy settings,
not measured technique success rates. Pausing freezes the policy. Existing CPU
directions, attacks and recovery remain in place; it writes no physics, lag,
action state, hitstun, damage or stocks. It is not a complete fighting AI or an
upstream training-hack port.

`gd.cpu_technical(port)` reads the calling script's
`{enabled, skill, opportunities, lcancel_inputs, tech_inputs, missed_decisions,
last_event, reaction_frames, policy}`. Other owners appear disabled. Input
counters count attempts, not successful cancels/techs; `last_event` retains the
latest pulse type (0 initially, 1 for landing-cancel, 2 for ground-tech). The prototype's `rogue_ai`
command exposes these observations without configuring the CPU.

`gd.hud_visible([boolean])` queries or controls the native status HUD for an
offline gameplay script; the console is refused. Hiding requires an active
match and claims ownership, so another script cannot change it until released.
Passing true restores visibility and releases ownership. Scene changes and
script unload/disable also restore it. It does not hide script-drawn UI or change
fighter status; a mod that replaces the HUD must draw its own feedback.

When an active gameplay script has id `roguelite/main`, the native main menu
shows **TBD**. Choosing it sets `gd.tbd_request()`; pass `true` to consume the
request, then have the script launch its scene. The bundled prototype uses this
entry independently of Adventure and the Master Hand sequence.

`gd.hit` processes a synthetic damage result directly and currently does **not**
emit the collision-loop `on_hit` callback. Its action/hitlag transitions can still
emit their normal callbacks. Do not suppress the next ordinary hit as a proxy for
synthetic lineage: it may be an unrelated attack.

The mouse lab, API examples, interpretation limits and review workflow are in
[`tools/model_parts/README.md`](../tools/model_parts/README.md). Raw part indices
and inferred body regions are not universal names for garments or accessories.

## Versioning and deprecations

- `gd.api_version` is the API number; `api_version` in a manifest says what a script needs.
- Additions (new functions, new fields in returned tables) do not bump the version.
- A removal or a change of meaning bumps it; the old name then stays for one version, listed in
  `gd.deprecated[name] = "use X instead"` and in this document.
- **Deprecated in API 1:** nothing.

## What stays native

Rollback, snapshots and netcode; UCF/Slippi gameplay codes (scripts may toggle them one day, not
run them); the m-ex runtime hooks; render, audio and memory-card IO; hot-path traces (heap, DVD,
PPC bridge, `MELEE_WATCH` guard pages, `MELEE_LOG_MOTION`'s per-transition log). The fixed-frame
pad script and the scene grammar remain as shorthands over the same paths scripts use.
