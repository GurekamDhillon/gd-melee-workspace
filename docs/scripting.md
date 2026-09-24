# Scripting GD's Melee (Lua) — the modding API

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
3. Every loaded gameplay script is hashed (id, version and source) into
   `gw_Script_GameplayHash()` / `gw_Script_GameplayDescribe()` for the netplay must-match set:
   two players whose gameplay scripts differ do not match. (The handshake side is the netplay
   code's; the digest is ready for it.)

---

## Hooks

Define any of these as globals in your script; the engine calls them.

| hook | when | notes |
|---|---|---|
| `on_tick()` | once per rendered frame, before the game logic | input polling (`gd.key_pressed`), UI state |
| `on_draw()` | once per rendered frame, after `on_tick` | the only place `gd.text`/`gd.box`/... draw (the list is rebuilt every frame) |
| `on_frame_pre()` | at the start of every game-logic frame | before the fighters move |
| `on_frame()` | at the end of every game-logic frame | after the fighters moved; the frame-data point |
| `on_scene(kind, name, prev_kind)` | a scene started (also once when the script loads) | `name` like `"GS_TRAINING"` |
| `on_match_start()` | the first frame with fighters on stage | |
| `on_match_end()` | the match scene ended | |
| `on_savestate(slot)`, `on_loadstate(slot)` | after a savestate was taken / loaded | restore your own Lua state here |
| `on_unload()` | before the script is unloaded or reloaded | |

While the game is paused (`gd.pause`), `on_tick` and `on_draw` keep running; the frame hooks do not.
There is no `on_hit` in API 1 (it would need a hook inside the hit code; asked for later).

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
| `gd.script()` | this script's `{id, name, version, author, gameplay, rollback_safe}` |
| `gd.buttons` | the bit values: `gd.buttons.A == 0x100` ... |

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
| `gd.key(name)`, `gd.key_pressed(name)` | the keyboard, only while the game window is focused and the console is closed. Names: `A`-`Z`, `0`-`9`, `F1`-`F12`, `KP0`-`KP9`, `SPACE`, `ENTER`, `TAB`, `ESCAPE`, `SHIFT`, `CTRL`, `ALT`, `LEFT`/`RIGHT`/`UP`/`DOWN`, `HOME`, `END`, `PAGEUP`, `PAGEDOWN`, `INSERT`, `DELETE`, `BACKSPACE` |
| `gd.input(port, spec [, frames])` | *gameplay.* Override a controller for `frames` pad samples (default 1). `spec` is `"A+B"`, a number (bits) or `{buttons="A", x=, y=, cx=, cy=, l=, r=}` (sticks -127..127, triggers 0..255) |
| `gd.release(port)` | end an override early |
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
| `gd.set_percent(port, p)`, `gd.set_stocks(port, n)` | |
| `gd.savestate([slot])`, `gd.loadstate([slot])` | slots 1-4, taken/loaded at the next frame boundary; a state from another scene is refused; never online |
| `gd.pause()`, `gd.resume()`, `gd.step([n])` | freeze the game logic; `step` runs `n` frames and stays paused |
| `gd.scene_launch(text or table)` | jump to a scene: `"mode=training;p1=fox;p2=falco/cpu;stage=fd"` or `{mode="training", p1="fox", ...}` (the `MELEE_SCENE` grammar, `_research/scene-launch.md`). It goes through the game's own soft reset, so it is safe from anywhere; returns the text |
| `gd.scene_clear()` | stop seeding scenes (the next VS/Training starts normally) |
| `gd.training_select(["kit" \| "native"])` | *(any script - menu routing only)* Training's character and stage select on the port's own kit screens or the native ones; returns the current choice and stays until changed. On the kit, Training keeps its rules: the player who entered picks, the CPU dummy's card picks the dummy, nothing else can be added. Also `select=kit` in the scene grammar (`gd.scene_launch{mode = "training", at = "css", select = "kit"}`, `MELEE_SCENE`), `MELEE_TRAINING_SELECT=kit` at start, and `gw_Frontend_SetTrainingSelect(1)` for native code |
| `gd.quit()` | close the game like the window's close button |

### Console and files

| function | |
|---|---|
| `gd.log(...)` / `print(...)` | to the console and `melee-pc.log`, prefixed with the script id |
| `gd.command(name, fn [, help])` | add a console command; `fn(arg_string)` |
| `gd.data_read(name)`, `gd.data_write(name, text)` | the script's data folder |
| `gd.screenshot([name])` | a PNG of the final frame into the data folder; returns `ok, path` (reports "not available yet" until the renderer's capture lands) |

---

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
| `frame`, `pause`, `resume`, `step [n]` | |
| `savestate [1-4]`, `loadstate [1-4]` | |
| `scene <MELEE_SCENE text>`, `scene clear` | |
| `input <port> <buttons\|0xhex\|none> [frames] [x y]` | e.g. `input 1 A 5`, `input 1 none 40 127 0` (walk right) |
| `shot [path]` | screenshot (see `gd.screenshot`) |
| `label <text>` | the run label |
| `echo <text>`, `clear`, `quit` | |
| *commands scripts added* | listed by `help` |

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
