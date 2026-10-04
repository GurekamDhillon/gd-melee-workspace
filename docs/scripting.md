# Scripting GD's Melee (Lua) — the modding API

## Zones

**2026-10-03 source addition:** native non-physical trigger volumes. Syntax checks
and the demo's Lua stub check have passed; native suite, rewind and in-game
acceptance are pending. Zones do not add collision lines or physical geometry.

```lua
local room = gd.zone_add{
  name="west-room", label="West room", kind="room",
  x0=-120, y0=-20, x1=-12, y1=90, tags={"interior"}
}
local door = gd.zone_add{
  name="door", kind="transition", x0=-12, y0=-20, x1=12, y1=90
}
gd.zone_set(room, {label="West chamber"})
local inside = gd.zones_at(1)
local wait = gd.wait_until{port=1, zone="west-room", timeout=180}
-- gd.wait_status(wait) reports success or names the current zones on timeout.
```

| Call | Result |
|---|---|
| `gd.zone_add{...}` | Positive handle; errors on invalid data or exhausted capacity |
| `gd.zone_set(handle, patch)` | Same handle after atomic validation and replacement |
| `gd.zone_remove(handle)` | `true`; only the owning script can remove it |
| `gd.zones()` | All live definitions, ordered by kind, ascending area, then handle |
| `gd.zones_at(port [, sub])` | Cached memberships for port 1–6; `sub=0` primary (default), `sub=1` sub-fighter |
| `gd.zone_members(handle)` | `{port, sub, entity, x, y, frames}` records for the zone |
| `gd.point_zones(x, y)` | Definitions containing a finite gameplay-plane point |

Definitions require a unique live `name` (1–80 bytes). `label` defaults to the name,
`kind` defaults to `"trigger"` and accepts arbitrary text (1–31 bytes), and `tags`
is an optional dense array of up to eight strings (1–31 bytes each). Choose either
all four rectangle coordinates, with `x0<x1` and `y0<y1`, or
`points={{x,y},...}` with 3–16 vertices of a strictly convex polygon. Both winding
directions are accepted; repeated or collinear vertices, self-intersections,
non-finite values and coordinates beyond ±49000 are refused. Capacity is 64 live
zones; a removed slot becomes available after its terminal membership pass.
No strings are silently truncated. A rectangle update supplies all four bounds;
other fields can be patched independently. Unknown definition keys are errors.

Optional `model=handle` binds local geometry to a scripted model instance's x/y
translation. Rotation and scale are not inherited. `model=0` detaches the binding;
removing the model removes the zone on the next logic pass. Returned definitions
include `handle`, `owner`, `name`, `label`, `kind`, `tags`, local `points`, `area`,
and cached `offset_x`/`offset_y`; memberships also contain `frames` and `seconds`
(frames/60). A newly entered membership has one completed residence frame.

Membership uses each fighter's `cur_pos.x/y` origin, the same point used for
retail blast-zone checks. It does not use the animation-dependent ECB centre.
All six owners and their sub-fighters are sampled separately. Dead and benched
fighters are absent; respawn/call starts membership again. `entity` identifies a
sampled lifetime, while `port` identifies its owner. Reads never advance time.
Positions and bindings are sampled once at the end of each logic frame. A
teleport compares its endpoints; a zone crossed entirely between samples does
not produce a synthetic intermediate visit.

Rectangles use `[x0,x1) × [y0,y1)`: left/bottom included, right/top excluded.
Polygons normalize counterclockwise winding; downward-directed edges and
rightward horizontal edges are included, opposite edges excluded. An unchanged
point on a boundary retains the same answer without movement-direction heuristics
or hysteresis. A camera can read `gd.zones_at` to distinguish room, transition and
outside membership explicitly.

Define any of these hooks to opt into its queued transitions:

```lua
function on_zone_enter(e) gd.log("entered", e.label, e.port, e.entity) end
function on_zone_exit(e) gd.log("left", e.label, e.port, e.entity) end
function on_zone_none(e) gd.log("outside every zone", e.port) end
function on_zone_some(e) gd.log("inside at least one zone", e.port) end
```

Payloads contain `zone` (handle), `name`, `label`, `kind`, `port`, `sub`, `entity`,
`x`, `y`, and `from` (prior membership handles). None/some have no individual zone
(`zone=0`, empty name/label/kind). Exit precedes enter for each entity; none/some
only report a change between nonempty and empty membership, including first entry.
Removing a zone or fighter emits terminal exits; owner unload, scene teardown and
stage-slot switching retire zones before destination hooks create new ones.
Cleanup preserves labels for exit payloads. Teardown callbacks cannot add or update
zone definitions. Hook arming is independent of membership calculation and does
not arm the ordinary engine event queue. Silent rewind/rollback frames compute
membership but never deliver Lua callbacks.

`gd.contacts(port)` and contact-event pictures include `zones` as cached
`{handle, frames}` records and `zone_names` as display text. Contact JSON traces
include those same fields; the contact overlay displays zone names. A watcher
with `zone="name"` waits for that primary fighter's named membership and names the
current zones, or "outside every zone", on timeout. Profiling exposes `zones`
for the membership pass.

Definitions, handles, current membership, residence counters and transition state
live in the snapshot-covered game-side scripting TU. They are restored rather
than reconstructed from Lua globals. Native Lua event-delivery copies are
observers only. A native monotonic allocation watermark prevents cached Lua zone
handles from aliasing newly created zones after a restore; it only influences an
explicit definition write, never a membership pass. Zone writes use the existing offline gameplay gate and fork the
rewind timeline; reads remain available. Online gameplay use would require shared
zone schema/content, deterministic replayable definition writes on both peers,
and rollback-safe consumers; the current Lua mutation gate grants no online writes.
Optional item membership is not implemented. Geno zone data schema version 1 is
reserved, with this definition shape; there is no Geno stage-zone loader yet.

See `examples/demos/zones` for the two-room/doorway demo and
`pc/tests/zones_rewind.lua` for the live zero-difference rewind fixture. Neither
fixture's presence establishes native execution or visual acceptance.

**Current as of 2026-09-28.** Comms callouts (`gd.comm`, `gd.comm_state`, `gd.comm_clear`,
`gd.play_sound`) were verified at game `d6b067d25`; the rest of the reference was checked against
`gw_script.c` at `4c676892a`. This reference supersedes older API descriptions. The LAB API is
public too (`gd.lab_api == 1`).

**Engine batch 2 additions (2026-10-03):** camera parameters, passive fighter modifiers and
reserve fighters below have source and headless-suite fixtures. The native audit confirmed the
basic APIs; follow-up floor-call/CPU fixes and entity inspection still need native re-testing.

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
| `rollback_safe` | false | legacy compatibility metadata; does not permit online gameplay writes |
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
2. During a netplay/rollback session **all Lua gameplay writes are refused**, including scripts
   whose manifest says `"rollback_safe": true`. Hooks are skipped during resimulation and the
   engine does not replay their mutations, so the flag cannot guarantee determinism. Gameplay
   scripts remain supported offline; read-only overlays and loggers remain available online.
3. Enabled scripts with both `gameplay` and `rollback_safe` are hashed by version and source
   into the netplay must-match set. Script ids label the diagnostic description. The console
   and offline-only scripts are excluded. This historical handshake set is retained for
   compatibility; matching it does not grant online write permission.

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
| `on_clank(event)` | read-only hitbox cancellation observation; `{port_a, port_b?, item?, item_kind?, x,y,z, damage_a,damage_b, cancel_a,cancel_b, rebound,rebound_a,rebound_b, hitlag_a,hitlag_b}`; queued at collision and delivered after the frame |
| `on_boss_defeated(event)` | gameplay scripts only; `{kind, port, x, y}`; kind is `master_hand`, `crazy_hand`, or `fighter_<kind>` |
| `on_camera_complete(kind)` | owning script; `"move"` or `"path"` |
| `on_hot_reload(ok)` | completion of the LAB hot reload |

Use `gd.boss_hold` in the boss-defeat callback to delay progression for a scripted bonus,
then `gd.boss_release` to let the normal flow continue.

---

## API reference (`gd`, API 1)

Fighter slots are numbered **1-6**. Physical controller ports remain **1-4**; `gd.input`, `gd.pad` and `gd.release` also support script-driven CPU slots 5-6 in offline matches.

### State

| function | returns |
|---|---|
| `gd.api_version` | `1` |
| `gd.frame()` | logic frames since boot |
| `gd.time()` | seconds (wall clock; for overlays, never for gameplay) |
| `gd.scene()` | `{kind, name, mode, mode_name, epoch}` - e.g. `name = "GS_TRAINING"`, `mode_name = "GM_TRAINING"`; `epoch` counts scene changes |
| `gd.match()` | `{active, frame, stage, netplay}` - `frame` counts from the first frame with fighters |
| `gd.players()` | a list of player tables for every fighter on stage |
| `gd.player(port)` | one player table, or `nil`; `falls` is the main fighter death count for this match, including time-mode/LAB deaths without stock loss |
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

Traversal reads also include `on_floor` (current grounded floor contact), `floor_y` (the supporting
collision segment's height at the ECB bottom x, or nil without a valid supporting floor),
`floor_passthrough` (standing on a drop-through floor), `wall` (-1 left, 1 right, 0 neither;
left wins if touching both), `ceiling` (current ceiling contact), `ledge` (CliffCatch or CliffWait,
not merely a nearby grabbable edge), and `jumps_left` (nonnegative maximum minus jumps used).
Contact fields describe the latest collision update; read them from `on_frame` after physics.

### Drawing (call from `on_draw`)

Coordinates are a 640x480 virtual screen scaled to the window: the height is always 480 and the
width grows with the window's aspect (a 16:9 window is about 853 wide), so the overlay uses the
whole picture instead of a centred 4:3 band. Read `gd.safe_area()` and lay wide layouts out
against it; 640 stays the origin and the minimum. Colours are `0xRRGGBBAA` numbers
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
| `gd.kit.paragraph(x, y, w, text [, role [, colour [, opts]]])` | wrapped multi-line text: breaks at spaces (and `\n`) to lines no wider than `w`, drawn from baseline `y` at the role's line height. A single overlong word goes through the fit rule. `opts` `{shear =}` (default the kit's shear). Returns the lines drawn and the block's height. The kit's pieces and how to add one: `_research/menu-kit-pieces.md` |
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

### Comms callouts (offline)

A Corneria-style comm window: a panel slides in at the screen edge with a portrait, a speaker name
and a subtitle, holds, then slides out. Calls queue behind the current one (up to 16), and the
window draws over any scene - a match included. It is drawing only, with its own tick state in Lua
(no game memory), so savestates and rewinds cannot desync it; it is refused during netplay/rollback.
It uses `gd.kit` when the kit is available and plain draws otherwise, and keeps clear of the
widescreen safe area when available.

| function | |
|---|---|
| `gd.comm{who=, text=, seconds=, sound=, portrait=, side=}` | show a callout. `who` is `"fox"`, `"falco"`, `"peppy"`, `"slippy"` or `"custom"` (default; picks the name and colours); `text` is the subtitle; `seconds` is the hold time (default 3); `sound` is a game sound id played when the window appears (see `gd.play_sound`); `portrait` is a `gd.kit.image` texture name (the colour block with the speaker's initial is the fallback); `side` is `"left"` (default) or `"right"`. Returns how many callouts are live or queued, or `false` when the queue is full |
| `gd.comm_clear()` | drop the current callout and the queue |
| `gd.comm_state()` | `{shown, queued, who, text, t, slide}` - for tests and mods (`t` is frames in the current callout, `slide` 0-1) |
| `gd.play_sound(id [, {volume=127, pitch=0}])` | play an existing game sound id (what the decomp passes to `lbAudioAx_800237A8`), centre pan; returns the AX voice handle, or a negative handle if playback failed. `volume` is an integer 0..127; `pitch` is an integer -1200..1200 cents (100 cents = one semitone). Omitting options retains full volume and unchanged pitch. Offline only |

The console command `comm <who> "text" [sound id]` is the same call, e.g. `comm fox "incoming"`.

The pickup-juice demo uses vanilla coin pickup 170, star pickup 250, and box
break 246 as regular pickup, rare pickup, and drop candidates. These ids are
identified from their game call sites; their mix and suitability need an in-game
audition. No additional audio assets are loaded.

`gd.fx_world(package,x,y,z [,scale=1,seed=1])` starts a registered effect
package at a fixed world position without a fighter joint. It returns a positive
script-owned handle, or 0 when the package is missing or the emitter pool is
full. Coordinates must be finite and within +/-100000, scale within (0,100],
and seed an integer 0..2147483647. `gd.fx_move(handle,x,y,z)` moves that world
anchor, returning false for ended, foreign or fighter-attached handles. Particles
with `follow:"srt"` or `follow:"translate"` move with it; `follow:"none"`
particles stay where they were born, leaving a trail. Both calls are offline
only and use the existing snapshotted FX state. `gd.fx_end(handle,0)` immediately
removes its emitters and particles; a positive fade duration permits a bounded
tail. Script unload already removes owned effects. These new calls have syntax
and fixture coverage; their native fixtures have not yet been executed.

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
| `gd.set_percent(port, p)`, `gd.set_stocks(port, n)` | damage clamped to integer 0-999; stocks to 0-99; forks the rewind timeline. A LAB match has no stocks (infinite respawn), so `gd.set_stocks` changes nothing a script can rely on there: count `gd.player(port).falls` instead |
| `gd.set_damage(port, n)` | offline; sets the same real fighter/player damage as `set_percent` (integer 0-999), keeping HUD, knockback and stamina HP in agreement. A boss at zero remaining HP still needs a hit to die |
| `gd.hit(port, {damage=, angle=, kbg=, bkb=, from=})` | offline; injects a normal-element hit through Melee's collision result and fighter hit processing. Required integer fields: damage 0-500, angle 0-361, kbg/bkb 0-1000. Optional `from` is a fighter slot; omitted means environment damage. Returns false for a missing fighter/source or refused damage, true after processing. Applies damage state, HP/percent and hitlag, not just a HUD edit; forks rewind |
| `gd.boss_hold([seconds])` | offline; hold the pending boss-defeat transition, default 60 seconds, range 1/60-600; timeout counts match logic frames. Returns whether accepted |
| `gd.boss_release()` | offline; release the boss-defeat hold; returns whether accepted |
| `gd.savestate([slot])`, `gd.loadstate([slot])` | slots 1-4, taken/loaded at the next frame boundary; a state from another scene is refused; never online |
| `gd.pause()`, `gd.resume()`, `gd.step([n])` | freeze the game logic; `step` runs `n` frames and stays paused |
| `gd.hitstop(frames)` | offline gameplay; freeze logic for `frames/60` wall-clock seconds (integer 1..36000), returning bool; replaces this owner's timed request. Presentation hooks/rendering continue; manual pause/step state stays intact |
| `gd.hitstop_cancel()` | offline gameplay; cancel only the calling owner's timed freeze; bool |
| `gd.scene_launch(text or table)` | jump to a scene: `"mode=training;p1=fox;p2=falco/cpu;stage=fd"` or `{mode="training", p1="fox", ...}` (the `MELEE_SCENE` grammar, `_research/scene-launch.md`). It goes through the game's own soft reset, so it is safe from anywhere; returns the text |
| `gd.scene_clear()` | stop seeding scenes (the next VS/Training starts normally) |
| `gd.training_select(["kit" \| "native"])` | *(any script - menu routing only)* Training's character and stage select on the port's own kit screens or the native ones; returns the current choice and stays until changed. On the kit, Training keeps its rules: the player who entered picks, the CPU dummy's card picks the dummy, nothing else can be added. Also `select=kit` in the scene grammar (`gd.scene_launch{mode = "training", at = "css", select = "kit"}`, `MELEE_SCENE`), `MELEE_TRAINING_SELECT=kit` at start, and `gw_Frontend_SetTrainingSelect(1)` for native code |
| `gd.quit()` | close the game like the window's close button |
| `gd.fly(port [, mode])` | debug movement (noclip). With no mode it reads: `true` while that port's fighter flies. `mode` is `true` / `"on"`, `false` / `"off"` (drop into Fall there), `"place"` (land on the floor below) or `"toggle"`; returns the new state. Flying: stick moves it at the fly speed (A ×0.25, B ×4), no gravity, no stage collision or ledges, no blast-zone KO, no hurtboxes unless solid; the camera follows it past the stage's bounds. Offline only, every mode (melee `docs/geno.md` 14.17) |
| `gd.teleport(port, x, y)` | put the fighter exactly there. It keeps flying if it was; one on foot falls from there. Offline only |
| `gd.fighter_mod(port, table_or_nil)` | replace that script's passive multipliers for port 1-6; omitted fields become 1.0, `nil` clears. Offline active matches only; returns true on success |
| `gd.fighter_bench(port)` | freeze and hide a reserve, including its partner/dormant transformation half; returns true or `false, reason`. Offline active matches only |
| `gd.fighter_call(port, x, y [, {facing=1, intangible_frames=0}])` | release the calling script's reserve at a new position; returns true or `false, reason` |
| `gd.fighter_benched(port)` | returns ownership boolean plus per-entity state tables; false outside a match |
| `gd.hold_hitbox(port, on [, {action=, frame=}])` | with debug fly on: the fighter stays in an attack state (`"nair"` default, `"fair"` `"bair"` `"uair"` `"dair"` `"jab"` or a motion state id) frozen at the first frame a hitbox is live (or `frame`); the hitbox stays on, attacker hitlag is cancelled and the hit list is cleared every 8 frames so the same target is hit again. `gd.hold_hitbox(port)` returns `on, rehit_intervals`. Console: `hold [port] on\|off`. Offline only |
| `gd.fly_speed([n])`, `gd.fly_solid([bool])` | the fly speed in units per frame at full stick (0.05-200, default 2), and whether hurtboxes stay on while flying (default off); each returns the current value. Offline only |
| `gd.fly_target(port, x, y)` | enables flight and moves toward a fixed world position at `fly_speed`, clamping the final step to avoid overshoot; holds that position once reached. Finite coordinates within ±49000. Offline debug control |
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
| `gd.stage_hide(on)` | boolean required; wrapper over `stage_isolate` for **Final Destination only**. Hides both host scenery and collision on `true`, restores both on `false`; returns `true` on successful hide or restoration, or `false, err` if host isolation is unavailable. Same owner, unload/match-end restoration and offline restrictions; ownership/type errors raise Lua errors. `stage_isolate` retains its existing return semantics |
| `gd.stage_add_model{file=, symbol='map_head', group=0, joint='root', x=0, y=0, z=0, scale=1, rot=0, platform=}` | Draw a JObj branch from a root-level stage or mounted mod `.dat` filename (5-30 bytes, no path separators or `..`), or a contained `missions/.../*.dat` path in the calling mod, in the stage world pass (lit, fogged). `joint` is a group-local zero-based index, `JOBJ_<index>`, or `root`; `rot` is degrees about Z; `scale` is >0 and <=100, `group` 0-255, joint index 0-4095. Returns a model handle or `nil, reason`. `platform` attaches a `gd.stage_add_platform` floor: `gd.stage_move(model, x, y)` carries it and `gd.stage_remove(model)` removes both; an attached floor does not draw its slab. Each DAT generation is loaded once per scene into heap 0 and released at scene end; up to 8 DATs (8 MiB each) and 64 models. Branches with JObj instance references are refused. `gd.spawn_target` draws Mato's Target Test model (GrTMr.dat) |
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
- **Limits.** Up to **768 scripted collision lines**, **256 GXMS instances**, **128 scene-pinned
  GXMS assets** (also bounded by a **64 MiB native mesh/atlas budget**), and **128 targets** at once.
  - **Lines:** each owns two vertices and one joint. Reservation is
    `min(768, (2048 - host_vertices) / 2, 1536 - host_lines, 1024 - host_joints)` with integer division;
    inspect the actual stage reservation in the log. A single model sidecar may contain up to
    **64 lines**, within **16 KiB**; a spawn also needs that many free reserved lines.
  - **Targets:** the pool is 128. The next ceiling is the game's item limit for the category
    (`Item_804A0C64`, from ItCo's common data).
- **Example:** `melee/pc/scripts/examples/fd_stage_content/` adds 3 platforms (passthrough with
  ledges, passthrough, solid with ledges) and 10 targets to Final Destination. Copy it to
  `mods/fd_stage_content` beside the exe (the manifest entry is `scripts/main.lua`).

#### Mission model paths and reloads

`gd.model_load(path)` accepts `missions/<name>/models/<mesh>` (optional `.gxmesh` suffix), relative
to the calling mod's root even when the script entry is nested. The existing plain basename lookup
under `models/` and mounted `mod-id/path/to/mesh` form remain supported. The `model` option on
`gd.stage_add_platform` / `gd.stage_add_line` accepts the same mission path. Mission mesh names use
at most 48 letters, digits, `_` or `-`; each sidecar's atlas and optional glow remain beside it.

| function | result |
|---|---|
| `gd.model_load(path)` | retained asset handle; a changed mesh, collision sidecar, atlas or optional glow at the same path creates a new asset generation |
| `gd.model_spawn(asset [, options])` | new instance handle, or `nil, reason`; options include transform, visibility, tint, `collision=false`, and `floor_flags` |
| `gd.model_despawn(instance)` | whether the instance was removed; retained load handles and scene-pinned asset bytes survive |
| `gd.model_release(asset)` | releases one caller-owned load reference; no return value; bytes remain pinned until scene reset |
| `gd.model_get(instance)` | instance table, or nil |
| `gd.model_instances()` | array of live instance tables |

Asset identity uses the resolved path plus size/modification-time stamps for **all four source
files**, including optional file presence. An unchanged generation reuses its asset and atlas;
an old instance keeps its old bytes after a re-export. This is a metadata stamp, so an exporter
must preserve a change in size or modification time. Bytes are freed at scene reset, not on the
last despawn. When 128 generations or the 64 MiB budget are exhausted, restart the match.
Savestate/rewind behavior with reloaded assets is unverified and outside this reload contract.

`gd.stage_add_model{file="missions/<name>/models/stage.dat", ...}` also accepts a contained
mission path. Mission DATs are read directly from the calling mod, transported into the game heap,
and cached by final path plus size/modification time. Root-level disc/mod DAT filenames retain
their existing behavior. The separate DAT limits remain 8 scene-pinned archives (8 MiB each) and
64 JObj model instances; valid DAT structure and available game heap are still required.

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

- **Kinds:** `goomba`, `redead`, `octorok`, `topi` (these four come from ItCo), and `koopa`,
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
| `gd.project(x, y [, z])` | `screen_x, screen_y, visible, depth` in the overlay canvas coordinates above (x can exceed 640 on a wide window); z defaults 0; nil without camera |
| `gd.safe_area()` | `{x=0, y=0, w, h=480, right=w, bottom=480}`: the overlay canvas; `w` follows the window aspect. Lay panels out against this. |
| `gd.stage_set_spawn(slot, x, y)` | offline: move a spawn point; slots 0–3 are player starts, 4–7 the respawns, 127–146 the item spawns (owner-guarded, forks the rewind timeline, restored by `gd.stage_restore_bounds()`). |
| `gd.stage_spawn(slot)` | `x, y, z` of that spawn point as authored. |
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
| `gd.hot_reload([seconds])` | offline LAB match only; rewind (default 2 seconds), reload Geno data and LAB script, replay recorded input. Incompatible layout restarts match; malformed data is refused with previous data retained. Returns true, start frame or false, reason |
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
| `gd.mod_read(path)` | read-only Windows mission text from the calling mod: string, or `nil, err`; at most 1 MiB |
| `gd.mod_list(dir)` | sorted array of `{name=string, dir=bool}`, or `nil, err` for an unavailable/non-directory path; `missions/` lists the mission root |
| `gd.mod_stamp(path)` | integer size/modification-time stamp for a contained file of at most 1 MiB, or nil; intended for polling |
| `gd.data_write_atomic(name, text)` | like `data_write`, but writes a temporary sibling file, checks the write/flush/close results, and only then replaces the target, returning `true`, or `false, why` on failure with the previous file intact. Atomic against a torn write (a reader sees the old or the new file, never a partial one); not a power-loss durability guarantee |
| `gd.screenshot([name])` | a PNG of the final frame into the data folder; returns `ok, path` (capture is queued for the next presented frame; it is not a synchronous file-write result) |

Mission paths must start with `missions/` and use forward slashes. Absolute paths, drive letters,
backslashes, `..` anywhere, empty components, embedded NUL, Windows wildcard/device separators,
and components ending in a dot or space are refused. Final opened paths must remain inside the
mod folder, including after resolving junctions/reparse points. Nested entries use the mounted
mod root (or the nearest ancestor `mod.json` for a standalone mod). The console has no owning
mod and cannot use these reads. They add no write access and require no online service or disc.
On non-Windows hosts mission reads fail closed; existing data-folder and model APIs remain available.

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
| `comm <who> "text" [sound id]` | a comm callout (`gd.comm{...}`) |
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
preserving each entity's level. It initializes the active and dormant transformation
halves together, so stand/fight survives Zelda/Sheik swaps; Nana also receives the
retail initializer, which retains her special partner CPU kind. A benched pair
saves the latest selection for both entities. It returns false for a missing or
human slot, or a subfighter presented as the primary.
Stand emits no autonomous inputs: it bypasses retail recovery/character AI and
clears pending commands, including timed Zelda/Sheik transformations. Nana is
also quiet despite her special CPU kind. Physics and vulnerability remain active.
The selected mode is persisted in the player slot so first-frame initialization,
respawn and transformation use it. Explicit scripted virtual-pad control is still
an input override. Fight uses the game's existing AI;
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


### Camera parameters (engine batch 2)

`gd.camera_params(values)` returns the previous values for all ten keys. A table updates only its named fields; an empty table does nothing. `gd.camera_params(nil)` restores the stage baseline. This requires an offline active match and has one script owner. Unknown keys, non-finite values, conflicting aliases and `min_dist > max_depth` are errors; validation is atomic.

| Keys | Accepted range |
|---|---|
| `min_dist`, `max_depth` | 1..49000 |
| `fov`, `tilt` | 1..89 degrees |
| `fixed_zoom`, `track_smooth`, `track_ratio`, `yaw_gain`, `pitch_gain` | 0..10 |
| `pan` | -180..180 degrees |

The decompilation's `cam_vertical_tilt` field actually feeds the standard camera FOV. Consequently `tilt` is an alias for `fov`; specifying both requires equal values. It is not an independent camera rotation. `pan` is the stage's vertical pitch offset in degrees, despite the historical name; it changes the eye/interest Y offset, not horizontal yaw. The accepted key remains `pan`. The standard camera FOV hook reads the override after its retail target calculation. C-stick paths and the 1P-mode gate are unchanged. The verified vanilla LAB stage defaults for `yaw_gain` and `pitch_gain` are both 0.05; values come from the loaded stage, so other stages can differ. Set `yaw_gain=0, pitch_gain=0` to remove origin-distance skew. Per-frame `stage_set_origin` and `stage_set_camera_bounds` calls no longer fork the LAB timeline or emit per-call logs; acquiring arena tracking logs once. Blast-bound writes retain their existing behavior.

```lua
local previous = gd.camera_params{min_dist=100, max_depth=1800,
    fov=45, yaw_gain=0, pitch_gain=0}
gd.camera_params(nil)
```

### Passive fighter modifiers (engine batch 2)

`gd.fighter_mod(port, values)` replaces that script's complete set and returns true. Ports are 1..6. Keys are `damage_dealt`, `damage_taken`, `run_speed`, `air_speed`, `shield_max`, `jump_height`, `air_jump_height`, and `knockback_taken`; omitted keys become 1. Finite numbers are clamped to 0.1..4. Ground `jump_height` covers full jumps and short hops. `air_jump_height` independently covers ordinary double jumps, multi-jump impulse tables (after Geno), and animation-driven double jumps. Ballistic launch velocity is multiplied by the square root of the requested height ratio; achieved height is approximate because gravity and discrete frames still follow retail logic. Animation-driven vertical displacement uses the ratio directly. `knockback_taken` scales the final capped collision knockback; 0.8 means 20% less launch impulse. These are live read overlays over the attributes the jump code reads, without DAT mutation; clearing/replacement/owner release preserves item and Geno edits. Expanded values remain in the existing snapshotted game BSS. Unknown fields and another script's ownership are errors. `gd.fighter_mod(port, nil)` clears the set. Writes require an offline active match.

Attack/defense multipliers overlay the retail player ratio getters for knockback. Actual damage percent also needs separate hooks: dealt damage is scaled on fighter/item collision and direct grab/throw/script hit routes; taken damage is scaled once at the central damage application. Owned thrown bodies and items credit their live fighter owner. Modified damage is capped at 500; unmodified damage retains retail behavior. Generic grounded acceleration and speed limits use `run_speed`; generic aerial drift limits use `air_speed`. Lowering `air_speed` does not immediately rewrite existing horizontal velocity. Retail state-specific drift/deceleration callbacks work toward the scaled limit; momentum may remain above it for several frames, and existing retail clamp paths still clamp where they normally do. There is no new setter-time clamp. Character-specific special-move velocities retain their own behavior. Shield capacity reads scale the shared baseline without editing it; current shield health is clamped immediately when capacity decreases and is never refilled by clearing a modifier.

Fighter attribute bytes and player baseline ratios remain untouched. Reads use the current baseline, including ported/Geno edits, so sets survive respawn and character changes without stacking. Clearing restores baseline calculations; it does not undo already inflicted damage or refill shield health. Ownership and values live in game BSS captured by LAB snapshots.

```lua
gd.fighter_mod(2, {damage_dealt=1.5, damage_taken=0.75,
    run_speed=1.2, air_speed=1.1, shield_max=1.5})
gd.fighter_mod(2, nil)
```

### Reserve fighters (engine batch 2)

`gd.fighter_bench(port)` returns true or `false, reason`. `gd.fighter_call(port, x, y, options)` returns the same; options are `facing` (-1 or 1) and `intangible_frames` (integer 0..600). Coordinates must be finite and within +/-49000. `gd.fighter_benched(port)` returns `boolean, entities`: the existing first result queries any script's ownership, returning false outside a match. The second result is an array of two state tables for the current primary and partner/dormant half, even when not benched. Each has `entity_index` (0 or 1) and `present`. Present entities also expose numeric `kind`, `action`, `cpu_kind`, `x`, `y`, `refusal_code`, and boolean `airborne`, `frozen`, `invisible`, `intangible`, `camera_excluded`, `dormant`, `benched`. `refusal_code` is the current individual safety result (0 safe, 1 missing camera, 2 boss, 3 dead/sleep/respawn, 4 capture/throw/carry, 5 hitlag/external freeze, 6 transformation, 7 unsupported action/item); pair/ownership checks can additionally refuse the write. Missing entities expose only index and `present=false`. This read-only query does not fork the timeline. Writes require an offline active match; online writes error before changing ownership.

A benched fighter is frozen, hidden, intangible, CPU-disabled and excluded from camera framing. Flags are reasserted before AI/physics and in the stage frame hook. Benching enters clean Wait on the ground or Fall in the air. Calling clears velocities, acceleration, nudge, fastfall, button/stick/trigger state and input timers; it probes a floor within 0.5 units of the requested height, enters the retail grounded Wait state (action 14 with Wait callbacks) immediately when found, otherwise airborne Fall at the requested coordinates, collapses collision history, unlocks ECB and reseeds the camera. Use a floor-height target to call onto a platform; distant floors are not snapped to.

Refusals cover missing fighter/camera, bosses, dead/sleep/respawn states, grabbing/grabbed/thrown/shouldered states, hitlag or externally frozen fighters, active transformations, unsupported action states, held items, another owner's reserve, calling an unbenched port, and changed entity identity. Supported entry actions are Wait through FallAerialB, plus teeter states. Invalid arguments error at the Lua boundary. Both player entities are checked before mutation: Nana is handled with her leader; a genuine dormant Zelda/Sheik half stays dormant and frozen while moving with the active half. Unknown secondary entities are refused.

The full CPU controller is saved, so restoring a kind cannot leave the disabled controller's stale AI state behind. Calling `gd.cpu_mode` while benched replaces the saved controller with the latest initialized selection and keeps the reserve inert; call/unload restores that selection. Saved flags, controllers and entity identities live in snapshotted game BSS. Script unload, match end and scene change release ownership, restoring original flags only on still-live matching entities. Camera parameter baselines and modifier sets have the same cleanup lifecycle. The batch-2 native audit confirmed camera/modifier behavior, reserve stock protection, air calls and several refusals. The follow-up corrects floor Wait entry and CPU controller restoration; its floor-cycle, partner/transform inspection and rewind re-tests remain for the integrator. Source fixtures are not a game run.

```lua
local ok, reason = gd.fighter_bench(2)
if ok then
    assert(gd.fighter_benched(2))
    local called, why = gd.fighter_call(2, 0, 0,
        {facing=-1, intangible_frames=60})
    print(called, why)
else print(reason) end
```

## Fighter and original-stage surface shaders (packet H, 2026-10-03)

`gd.fighter_shader(port, "shaders/name.wgsl", {params={...}})` and
`gd.stage_shader("shaders/name.wgsl", {params={...}})` select visual-only WGSL
surface functions. Ports are 1..6; at most 16 finite parameter floats are accepted.
Pass `nil` instead of the path to clear the calling script's selection. Returns
`true` or `nil, diagnostic`; paths are contained in the calling mod folder.
Another script cannot overwrite your selection. Unload, script disablement and
scene transitions clear selections. Requires the Aurora GD surface carried patch
and a fresh build. See [shaders.md](shaders.md) for inputs, normal-buffer limits,
cache/performance costs and the sample mod. `gd.perf()` adds cumulative
`surface_load_calls`, cumulative `surface_fifo_commands`, and `surface_selections`.


## Contacts and traces

**Source addition, 2026-10-03:** syntax checked; native-suite, link and gameplay acceptance are
pending. These APIs inspect primary fighters on ports 1..6. Sampling begins when a contact API,
watcher or overlay is first used, and runs after completed logic frames, before `on_frame`.

| Call | Result |
|---|---|
| `gd.model_label(instance, "Floor_4m.003")` | `true`; diagnostic name for an instance owned by this script's resource token. Printable text, at most 80 bytes; 1024 labelled handles per scene. Retired handles retain their names for same-scene rewind. |
| `gd.contacts(port)` | Current contact picture, or `nil` when the primary fighter is absent. |
| `gd.contact_events([since_seq])` | `events, next_seq, dropped`; pass `next_seq` back on the next poll. Omit the cursor or use 0 to read all retained events. |
| `gd.contact_trace(true)` | Append events to this script's data file `contacts.jsonl`. |
| `gd.contact_trace{file="route.jsonl", state_changes=true}` | Choose a relative script-data path and opt into action-state events. One script owns the file tracer at a time. |
| `gd.contact_trace(false)` | Close the calling script's tracer and turn state-change events off. |
| `gd.wait_until{port=1, x=41.2, y=8, radius=1, state="Wait", on="Floor_4m.003", airborne=false, timeout=600}` | Watcher handle; no input, teleport, pause or blocking loop. All supplied conditions must match. |
| `gd.wait_status(handle)` | `{done, ok, frames, reason}`, or `nil, reason` for a stale/other-script handle. |
| `gd.contact_overlay(true)` | Show human fighters' compact contact text, highlighted surfaces and contact markers. `false` hides it. Off by default. |

A picture has `x,y,vx,vy,facing,state,state_id,state_frame,jumps_left,airborne`.
`state` uses the fighter's existing action-name table, including named Geno actions; `state_id`
is the numeric action. `state_frame` counts logic frames in that action, as in `gd.player`.
`floor,left_wall,right_wall,ceiling,ledge` are each absent (`nil`) or a surface:

```lua
{owner=instance_handle_or_line_handle_or_"stage", label="Floor_4m.003",
 part=0, line=123, kind="floor", passthrough=true,
 x0=-10, y0=8, x1=10, y1=8, offset=6, t=0.3, normal={x=0,y=1}}
```

`line` is the current map collision index; `part` is the zero-based mesh line index (`-1` for
host-stage and standalone scripted lines). A model's instance handle owns its lines; a standalone
scripted line owns itself; original-stage lines have owner `"stage"`. Empty labels mean no name
was attached. Wall sides describe the fighter's left/right, rather than the wall's normal.
Endpoints are ordered from left to right, or bottom to top for a vertical segment. `offset`
is distance along the segment from that end; `t` is its clamped fraction. Ledge contacts use the
latched floor line and its facing-selected endpoint. Coordinates and offsets are world units.

The 512-event ring drops its oldest record when full; `dropped` counts overflow since the last
scene/load/rewind reset. Records contain `seq,frame,port,event,reason`, the fighter fields above,
and `contact` (the full surface or `nil`). Lua records also copy surface fields to the top level.
`frame` is the match logic frame. Events are `land`, `leave`, `wall_touch`, `wall_release`,
`ceiling_hit`, `pass_up_through`, `drop_through`, `ledge_grab`, `ledge_release`, `ko`, `respawn`,
and optional `state_change`. Steady contacts emit nothing. Initial sampling reports existing
contacts as acquisitions. Changing floor lines emits leave/land even on adjoining surfaces.

Leave reasons are `jumped`, `ran_off_left`, `ran_off_right`, `dropped_through`, `knocked`, or
`lost_contact` when the read-only sample cannot classify the transition. `pass_up_through`
means the airborne fighter's ECB bottom swept upward across a pass-through line. It records the
crossing point, including crossings without a final contact flag. This is geometry observation,
not a claim that an input succeeded. Moving surfaces and fighter-specific actions need native
acceptance. Traces use one escaped JSON record per event, capped at 1 MiB per file; `.1` holds
one previous rotation. File errors stop tracing and log a diagnostic. Trace-off still allows
ring polling and watchers.

Watchers default to port 1, radius 1, timeout 600 logic frames. Coordinates must be finite and
within +/-49000; radius is 0..49000; timeout is 1..360000. `state` accepts a name or nonnegative
id; `on` accepts a floor owner handle or exact label. A supplied x alone tests horizontal distance;
x+y tests circular distance. Unknown fields and empty conditions are errors. Already satisfied
conditions resolve at zero frames. Paused presentation ticks do not advance waits. There are
64 slots shared across scripts; a script may reuse its completed slots when full, invalidating
the previous handle. Active waits are never evicted; unloading releases that script's slots.

A timeout explains observations, for example `stopped at wall "Wall_Solid.014" (left side) at
x=41.2 after 212 frames`, `fell through "Floor_4m.003"`, `never left the ground`, or
`timeout 600 frames; last on "Ramp.002" offset 3.1`. These are diagnostic descriptions, not proof
of causation. Match/scene changes and state loads/rewinds cancel pending waits with a reason.

A traversal controller should issue short inputs and poll once per logic frame. This worked
loop assumes an existing labelled platform near `(41.2,8)` and an offline gameplay script
(`-- @gameplay: true`):

```lua
-- @gameplay: true
local cursor, watcher, finished = 0, nil, false
local target_x, target_y = 41.2, 8

function on_match_start()
  cursor, finished = 0, false
  gd.contact_trace{file="route.jsonl"} -- state changes stay off
  watcher = gd.wait_until{port=1, x=target_x, y=target_y, radius=1,
    state="Wait", on="Floor_4m.003", airborne=false, timeout=600}
end

function on_frame()
  if finished or not watcher then return end
  local events
  events, cursor = gd.contact_events(cursor)
  for _, e in ipairs(events) do
    if e.port == 1 then
      gd.log(e.event .. " " .. (e.label or "-") .. " at " .. e.x .. "," .. e.y)
    end
  end
  local result = gd.wait_status(watcher)
  if not result then finished = true; gd.release_pad(1); return end
  if result.done then
    gd.release_pad(1)
    gd.log((result.ok and "reached target: " or "route failed: ") .. result.reason)
    finished = true
    return
  end
  local c = gd.contacts(1)
  if c then
    local dx = target_x - c.x
    gd.input(1, {x=math.abs(dx)>0.75 and (dx>0 and 60 or -60) or 0}, 1)
  end
end

function on_loadstate() -- Lua control variables are not simulation snapshots
  finished, watcher = true, nil
  gd.release_pad(1)
end
function on_match_end() finished = true; watcher = nil end
function on_unload() gd.contact_trace(false) end
```

For an airborne target, add a jump input when the live picture shows the named launch floor,
then wait for the intended airborne coordinates/state. Poll the events to distinguish a wall
stop, an upward platform crossing and an unintended drop; do not spin in a Lua `while` loop.

Console equivalents are `contacts 1`, `contacts overlay on|off`, `trace on|off`, `trace last 20`,
and `wait port=1 x=41.2 y=8 radius=1 state=Wait on=Floor_4m.003 airborne=false timeout=600`.
Console wait values use `key=value` tokens; labels containing spaces use the Lua API instead.
A console wait prints one result line when it resolves.

Contact reads never call collision probes or alter fighters, pads, camera or line caches.
Observer history, labels, trace files, watcher progress and overlay state are native diagnostics,
excluded from simulation snapshots and hashes. Rollback replay frames do not append events or
advance watchers. Savestate load/rewind clears the ring and previous picture, bumps the monotonic
sequence, and cancels active waits; retained same-scene labels remain attached to their nonreused
handles. This keeps diagnostics rollback-neutral; gameplay inputs in the example still use the
normal offline permission checks. Disabled overlay drawing returns immediately without reads or
allocations. The observer itself remains inactive until first use.

## Custom shaders, post passes and model materials

These APIs change native visual state only and remain available online. See
[the shader author guide](shaders.md) for WGSL bodies, bindings, examples,
containment, hot reload and performance costs. The sample mod is
`melee/pc/geno/mods/shader-demo/`.

| API | Contract |
|---|---|
| `gd.shader_load(path, opts)` | Handle or `nil,error`; opts: `kind="post"` (default) or `"effect"`, optional `vertex`, named `params` |
| `gd.shader_set(handle, params)` | Atomically update declared floats/vec4s; `true` or `nil,error` |
| `gd.shader_status(handle)` | `{valid,error}` or `nil,error`; also polls for edits |
| `gd.fx_shader(package, emitter, handle_or_nil)` | Override a named effect emitter's appearance; nil restores its package shader |
| `gd.post_add(path_or_shader_handle, opts)` | Post handle or `nil,error`; opts: `order`, `stage="world"|"final"`, `half`, `params`, `duration_frames`, `clock` |
| `gd.post_set(handle, {params=...})` | Update a pass's independent parameter values |
| `gd.post_remove(handle)` | Boolean; only the owning script can remove it |
| `gd.post_clear()` | Clear this script's passes; engine transition covers and other scripts' passes survive |
| `gd.light_set{dir={x,y,z}, color={r,g,b}, ambient={r,g,b}}` | Set the custom model key light; nonzero direction, nonnegative colours |

Paths are relative to the calling mod; console paths start with a mounted mod ID.
Parameters declare at most 16 named finite floats or four-float arrays. Every WGSL
parameter occupies a `vec4f` slot: read scalar values with `.x`. Updates cannot
change names or types. Handles expire on unload and scene/match end.

`world` runs after world/effects/near translucent models and before the retail
HUD; `final` runs after the retail HUD and before host overlays. Passes preserve
scene depth and EFB alpha. No separate pre-effects insertion point is exposed.
`gd.perf().shaders` reports cumulative compilation/cache/error, draw/pass/resolve,
skip, pixel, upload-byte and CPU recording counters; it does not measure GPU time.

`gd.model_load` opts into custom rendering when a matching `.material.json`
exists next to its `.gxmesh`. Built-ins are `lit`, `unlit`, `glass`, or supply a
WGSL fragment body. Models without a material keep the GX path. Glass needs its
existing collision sidecar's `alpha=1` to retain far/near translucent sorting;
the sample provides an authored opacity/tint material template. See the author
guide before adding material sidecars to exported kit parts.


### Clank observation and timed presentation

`gd.clank_event == true` advertises `on_clank`. Both ports are 1-based;
`port_b` is absent for a fighter/item clash, where `item` is an unsigned
same-frame object identity and `item_kind` is the engine item kind. The item
identity is **not** a mutable `gd.item_*` handle. `x,y,z` are the midpoint of
the colliding hitbox world centres; damage fields preserve their float damage.
`cancel_a/b` reflect the engine damage-gap test for each side. Damage-imbalanced
clashes can cancel only one side. Repeated contacts for the same entity pair in
one logic frame yield the first contact once.

`rebound_a/b` and `hitlag_a/b` read each still-live object's final state at the
frame boundary, after ordinary engine collision processing and callbacks. A
projectile destroyed by its clank callback has zero remaining hitlag. Hitlag
also reflects other collisions that frame; these fields report actual remaining
engine state, not a newly calculated per-contact duration. Rebound is the OR of
the per-fighter ReboundStop/Rebound state flags. Producing the event writes no
game state, and resimulated frames produce no duplicate Lua events.

Grounded fighter/fighter clanks and grounded/aerial fighter/item clanks are
observed. The vanilla fighter/fighter collision gate requires both fighters on
the ground: this API does not create an aerial fighter/fighter cancellation rule.
A fighter/item clash in the air can apply hitlag with `rebound=false`. Inert
hitbox touches, shield hits, reflects, absorbs and item/item clashes are separate
paths and do not produce this event. With no `on_clank` subscriber the producer
returns immediately.

For a shader centre, existing `gd.project(x,y,z)` returns top-left script
coordinates; divide x by `gd.safe_area().w` and y by 480 to obtain post UVs.
No additional camera write or projection API is necessary.

`gd.hitstop` is a host logic-iteration gate, not a write to fighter hitlag or
rollback memory. Its duration is nominal **60 Hz presentation time**, including
while paused, rather than stopped logic frames or monitor refreshes. Separate
owners' requests coexist; cancelling/expiry never resumes another request or a
manual pause. Match/scene end, unload, script disable and online entry release
requests; netplay, rollback and resimulation do not honor this gate. Calling it
requires `gameplay=true` (or console), an offline active match and valid frames.
`on_tick`, drawing and console remain live. On scene restart manual pause follows
its pre-existing reset behavior.

`gd.post_add(...,{duration_frames=N,clock=true,params={elapsed=0,progress=0,...}})`
removes that owned pass automatically after N/60 wall-clock seconds, even if its
Lua hook errors. `clock=true` additionally updates **declared scalar** `elapsed`
(seconds since creation) and `progress` (0..1) at each presentation tick. Declare
both scalar names; wrong/missing types fail atomically and remove the attempted
pass. `clock` requires a duration; omit it for a timed pass whose parameters Lua
updates. Duration is integer 1..36000, or omitted/0 for an indefinite pass.
Manual remove/clear, scene cleanup and unload retire timer records too.

The non-shipped `experiment/clank_impact` folder demonstrates these capabilities
with GD's own v3 impact shader. Its freeze is offline-only; the shader APIs remain
local visual APIs under their existing permissions.

## Six-fighter direct matches (source update 2026-10-03)

**Fix1 source update (2026-10-03):** `p7=` is logged and refuses the complete launch. With six fighters, `gd.lab_leave("css"|"sss")` returns `false, reason` and logs that reason; use `"menu"` or `"restart"`. A refused leave preserves pause state.

Team launches normally keep the requested/default costume (`/colorN`) and run Melee's same-team, same-character duplicate tint assignment. Five identical teammates can therefore have shades 0 through 4; shading does not select their physical controller. Add `teams=1;enemy_team_colors=1` to force each active fighter on a team different from P1's team to its CSS team costume (team0 red, team1 blue, team2 green) and shade zero. This overrides enemy `/colorN`, preloads the chosen costume, and supports five enemies sharing one costume without a fifth nonzero tint. P1's team retains ordinary duplicate shading.

Admission now plans the actual match preload requests before any fighter load, independently of the previous screen's heap policy. `six-slot planned` lines give deduplicated request counts and byte budgets; `six-slot after-load` lines give allocator free bytes after the complete preload queue finishes. They are distinct measurements. Main-heap runtime peaks still need live testing.

The tester verified the original six-slot build's camera, port APIs, KO/respawn, recycling, restart, savestates and rewind (zero differing bytes) in `_build/audit-20261003/batch2-verify/`. Fix1's HUD, admission, refusal and colour changes have syntax checks and added regression fixtures; they have not been built or run. See `_build/tmp/codex-six-slots-fix1-report.md` for acceptance steps.


`MELEE_SCENE` and `gd.scene_launch` accept `p1` through `p6` for **direct VS or LAB matches**. Slots 5-6 default to CPUs and refuse human/demo types. Physical controllers remain four. Six-slot CSS, SSS and Training routes are refused; VS finishes return to menus, and LAB permits restart or exit to menus. Use `/team0` for the player and `/team1` for each enemy with `teams=1`.

```lua
gd.scene_launch{mode="lab", stage="fd", teams=1,
  p1="fox/hu/team0", p2="marth/cpu0/team1", p3="marth/cpu0/team1",
  p4="marth/cpu0/team1", p5="marth/cpu0/team1", p6="marth/cpu0/team1"}
gd.input(6, {buttons="A", x=-80}, 10)
gd.release(6)
```

Fighter APIs use slots 1-6: `player`, `players`, CPU modes, modifiers, bench/call/benched, shaders, teleport, hit and contacts. `input`, `press`, `pad` and `release` now also support slots 5-6 through CPU input records. Holds count logic frames; a claimed slot stays neutral until released. `pad(5/6)` reports the most recently sampled CPU input; its optional physical/raw selector has no separate meaning there. `mirror_pad` and `input_mask` remain physical-controller APIs for ports 1-4. LAB panel targets cycle the fighters actually present; menu navigation still polls four controllers.

`gd.fighter_recycle(port, {x=, y=, facing=1, intangible_frames=0, character=})` returns `true` or `false, reason`. The optional character is an explicit CharacterKind (`gd.player(port).char`). Recycle requires a CPU that has completed its KO and is in Sleep/Rebirth/RebirthWait. Use an infinite time/LAB match: stock elimination can destroy the entity before a script can recycle it. Retail respawn reset refreshes the retained fighter, damage becomes zero, and floor/camera/input placement uses the reserve call path. Paired fighters, transforms, bosses and character changes are currently refused. For a different enemy character, call another fighter slot seeded with that character at match start.

`preload=fox/marth` reserves up to **two** additional costume-zero characters in the eight-entry launch cache. This preloads files only; it does **not** enable character-changing recycle. Six-slot launches and extra preloads check deduplicated file sizes, alignment and archive/allocator overhead against the file heaps, retain 1 MiB admission headroom in each fighter heap, and require 4 MiB free in the main heap. Refusals and headroom are logged. These conservative floors are not measured runtime peak guarantees for arbitrary mod assets or stages.

The snapshot header already describes six fighters. Virtual input records and sampled values live in snapshotted game memory, and LAB input logs include the two extra slots for replay. The initial source pass did not build or run the game. The subsequent tester results and outstanding Fix1 acceptance are distinguished above; six-way HUD spacing remains pending visual verification.


## Stage slots and switching

Offline stage slots (Packet O; fix4 source update, 2026-10-03). The owner watched the fix2/fix3 six-stage queue tour; fix4 native-controller changes still need executable acceptance. Slots retain DAT models, collision, markers and parameters. The six legal DATs default to scoped animation/moving collision; Yoshi's Story and Fountain additionally run owned native controllers. Arbitrary destination hazards remain unsupported. `gd.stage_slot_load("battlefield")` returns `slot` or `nil, err`; names `fd`, `bf`, `ys`, `dl`, `fod`, `ps` and vanilla kind numbers are accepted. `{file="GrNBa.dat",music_id=...}` selects a root disc DAT. `gd.stage_slot_info(slot)` exposes bytes, model bytes, collision counts, camera/blast bounds, marker-indexed spawns, music and heap free/capacity/headroom. `gd.stage_slots()` lists owned slots. `gd.stage_slot_free(slot)` refuses active or transitioning slots. Handles belong to the loading script and scene.

There are 16 slot records, 64 model groups per slot, a 512 KiB heap reserve, and the existing script collision budget (normally 768 lines, 1536 vertices); switches reserve one safety line. Allocation and collision availability can limit the count below 16. DAT reads are synchronous. Preload before play: the pre-fix2 tester measured about 4.7 MiB for six legal static slots; current animation allocations require a fresh heap measurement. Arbitrary archives are subject to bounded validation and cannot be assumed safe or compatible.

`gd.stage_switch(slot,{transition="wipe",indicator=1,duration_frames=60,place="keep"})` requests an owned timed freeze and one atomic collision/parameter replacement. Built-ins are `wipe`, `flash`, `morph`; an integer post shader handle selects a custom cover. Default duration is 60 presentation frames (one second). Wipe sweeps left-to-right across the old scene, then uncovers the new scene left-to-right; flash fades to white and back. Both use the final post-process pass and cover the retail HUD, while the host/console overlay stays above the cover. The indicator is queried directly on each rendered frame, including frozen logic. Indicator uses logic seconds; presentation duration uses 60 Hz time while logic is frozen. Morph offsets DAT meshes visually; collision switches once at midpoint. The initial host is hidden rather than morphed. Mission meshes currently switch visibility without morphing. Custom shaders receive no automatic progress uniform.

Fix5 source repair defers destination/restoration music until the normal native
loop has returned from script hooks and both timed freeze and explicit pause
have ended. A later switch/unload replaces or cancels a pending request; scene
end clears it. `gd.post_clear()` leaves director-created built-in/custom covers
alive until the director removes them. The PC stream-start busy wait also pumps
deferred DVD/AR completions. These changes have standalone fixture evidence;
they have not been accepted in a rebuilt executable.

The owner's fix5 target is complete vanilla initialization and teardown with
one live stage and file-only caches. The current partial paths below do **not**
meet that target. The hosting audit and concrete remaining work are in
[_research/stage-switch-full-retail-lifecycle-2026-10-03.md](../_research/stage-switch-full-retail-lifecycle-2026-10-03.md).

Default placement retains a usable position, otherwise moves to the nearest floor without KO. `place="ko"` moves only fighters outside the new blast zone below it, including grounded fighters; fighters inside the zone keep a usable position, and those without a usable floor move to the nearest floor without KO; retail KO occurs after logic resumes. Captured, thrown, dead and respawning fighters refuse the switch. Ledge action entry into Fall and all floor, wall, ceiling, ledge and ECB contact clearing happen before any old collision line is removed. Captures/throws are refused before writes. Common portable items and projectiles survive with reset collision references; item kinds at or above `Old_Kuri` are deleted (this conservative policy also removes summons). Fighters with unusual transformation/bench state still need native testing.

`gd.stage_queue{{slot=bf,after=10,transition="wipe"},{slot=ys,on="next_room",transition="flash"},loop=true,shuffle=true,seed=42}` accepts arbitrarily many entries subject to memory. Each entry uses exactly one of `after` (seconds since queue start/previous completed switch), `at_stocks` (total stocks <= threshold), or `on` (event name). `gd.stage_queue_event(name)` signals a custom event; dispatched game events also signal queues. `gd.stage_queue_next()` forces the next entry; `gd.stage_queue_clear()` clears future entries. A pending transition must finish before replacing its queue. Seeded shuffle and loop order are deterministic. All scripts receive `on_stage_switch{phase="before"|"after",from=...,slot=...}`; recursive switch requests are refused. Captured/dead/respawning preflight refusals retry without consuming the entry; other preflight failures stop the queue.

Only the six legal retail stages are accepted as hosts. Original host stage procs, collision and wind are gated; owned Yoshi/Fountain procs and their destination shadow checks run while active. Other stages and arbitrary m-ex hosts require a hazard audit. FD/BF retain their authored topology; Yoshi runs Randall and Shy Guy callbacks; Fountain runs random platform heights with submerged/absent collision disabled, omitting reflections and water effects. Dream Land omits Whispy/clouds; Stadium selects its initial arena, omitting transformations and screen animation. These fix4 source paths supersede the earlier animation-only limitations for Yoshi/Fountain; full visual equivalence is not yet accepted.

Mission registration uses `gd.stage_slot_load{models={{asset=asset,x=...,y=...,scale=...}},camera={left=...,right=...,top=...,bottom=...},blast={...},spawns={[0]={x=...,y=...}},music_id=...}`. Generated GXMS collision sidecars supply geometry; static full levels only. Release the slot before asset references. The missions-mod registration diff is in `_build/tmp/codex-stage-switch-missions.diff`; the mod itself is unchanged.

Netplay, rollback and replay are refused. Savestate loads/rewind/history/hot-reload resimulation are refused while slots are live, and memory snapshots from a different slot epoch are refused. Native queues and model caches are outside snapshots. Unload/match end/scene change reclaim slots and restore host markers, camera, blast bounds, parameters, music and isolation. See `pc/scripts/examples/stage_switch_demo/` for the FD -> BF -> YS -> FD timer demo and `stage next`, `stage queue`, `stage slots` commands.



Legal stage names differ between the slot API's internal kinds and the scene launcher's SSS indices. Use these tokens:

| Stage | Slot name | Slot kind | Scene `stage=` | Scene SSS index |
|---|---|---:|---|---:|
| Final Destination | `fd` / `final_destination` | 37 | `fd` / `finaldestination` | 32 |
| Battlefield | `bf` / `battlefield` | 36 | `bf` / `battlefield` | 31 |
| Yoshi's Story | `ys` / `yoshis_story` | 10 | `ys` / `yoshistory` | 8 |
| Dream Land 64 | `dl` / `dream_land` | 28 | `dreamland64` / `oldpupupu` | 28 |
| Fountain of Dreams | `fod` / `fountain_of_dreams` | 12 | `fod` / `fountain` | 2 |
| Pokemon Stadium | `ps` / `pokemon_stadium` | 16 | `ps` / `pstadium` | 3 |

The scene aliases `dl` and `dreamland` select Green Greens (SSS 17, internal kind 13), retained for compatibility. Use `stage=dreamland64` for Dream Land.

While any stage slots are loaded, `gd.savestate`, `gd.loadstate`, `gd.state_save`, `gd.state_load`, `gd.rewind_test` and `gd.hot_reload` return `false, reason` and log a refusal before scheduling work. Pending state requests are also logged and cleared if slots are loaded before their frame boundary. Slot/cache epochs continue to protect older snapshots after unloading.

All DAT model, collision, camera/blast markers and spawn markers use the destination ground scale (BF 0.8, YS 0.7). FD reproduces its starting backdrop clip selection and its near/far camera planes; its full retail backdrop cycle remains unsupported. A switch logs requested/current music ids and whether the retail HPS helper restarted playback.

## Standalone items and model rotation (source update 2026-10-03)

Native Geno items let a mod define stage pickups independently of a fighter or
m-ex item table. They use real game item state, with gravity, stage/script mission
collision, floor rest, touch collection, expiry, a small colour/amount payload,
and optional GXMS visuals. Definitions register from `items/<name>/item.json` at
mod boot; format and reserved kind range are in `melee/docs/geno.md` section 19.13.
`grab`, holding and throwing standalone definitions are currently refused.
There is a hard cap of 128 live native standalone items. Collision uses swept
points against floors, walls and ceilings, plus moving-floor carry; floor/platform rest is owner-verified on the stamped build; wall/ceiling and
moving-floor carry still need native acceptance. Full netplay still requires definition
fingerprints and replicated deterministic spawn/despawn inputs.

General definition fields `visual.hover`, `visual.height`, and `visual.tilt`
default to zero. Hover lifts only the visual and pickup volume; the stage
collision point stays at the floor anchor. Height is the unscaled model height.
The pickup volume is a vertical capsule from that anchor to
`anchor + max(0, hover + bob*sin(age*bob_speed*pi/180) + height*scale)`;
its radius is `radius*scale`. A fighter underneath or jumping through it can
collect it. `spin` and `bob_speed` are degrees per logic frame: 6 and 3 give
360 degrees/second and a two-second bob at 60 logic FPS. Rotation turns the
tilted long axis around Y (`Ry(spin)*Rx(tilt)`) so symmetric models read clearly.
Hover follows the existing floor carry and does not prevent falling off edges.
These additions are source-checked; moving-platform and visual acceptance
require a later native run.

Standalone Geno rows from `gd.items()` also expose `visual_y`, `rotation`
(degrees), `tilt` (degrees), `scale`, `visible`, and native `age` (logic frames).
The ordinary `x,y,z` remain the physics anchor. These read-only values let
presentation follow the rendered pickup without simulating a second trajectory.

```lua
local handle, err = gd.item_spawn("drive", 10, 30,
  {vx=0, vy=2, payload={colour="blue", amount=20}})
function on_item_collect(e)
  if e.name == "drive" and e.port == 1 then
    -- Award e.payload.colour / e.payload.amount once for e.item.
  end
end
function on_item_expire(e)
  -- e.reason is "expired" for lifetime expiry, "destroyed" for other destruction.
end
```

`gd.item_define("items/drive/item.json")` loads a contained mod-relative definition;
`gd.item_spawn(name,x,y,options)` returns a handle or `nil,reason`;
vanilla aliases `"vanilla:<kind>"` are accepted as well as numeric kinds.
Refusals distinguish unsupported kind, unsafe kind, uninitialized descriptor,
pool full, item cap reached, and reserved-range conflict. Visuals preload one
colour/part per engine tick outside the Lua budget. A freshly registered
or scene-reset definition may return `nil,"item visuals still preparing; retry
next frame"`; retry after a later frame. Optional-art failures complete with the
built-in fallback. Spawn never loads assets. If the creating callback errors or
runs over its budget, newly created items from that callback are removed without
terminal reward events. Successful callbacks and yielded tasks retain items.
`gd.item_despawn(handle)` removes a live item. Spawn/despawn are gameplay writes:
refused online and fork the LAB timeline. Native item state can be restored with
the game's snapshots; drawing follows the restored item rather than storing an
independent Lua pickup list. Collection and expiry hooks are queued only when
hooked. By default they report standalone Geno items only. A script can opt in
with `gd.item_events{vanilla=true, mex=true}`; `gd.item_events{}` disables both
families, and `gd.item_events()` reads the current filter. Filters are per script
and take effect immediately. Vanilla opt-in covers common kinds 0..34, not
fighter articles/projectiles or stage enemies. Geno fighter articles never enter
these hooks. m-ex opt-in covers admitted custom kinds outside Geno reservations. Script rewards remain offline-only and must guard duplicate/unrelated
handles themselves. The owner verified baseline floor/platform rest, fallback spin, exactly-once
collection, expiry, 60 items and snapshot/rewind on the stamped build (fix1 packet).
The material/preload/filter/CPU/blink corrections still require native retesting;
this source update did not build or launch the game.

One item surface covers three families, with explicit admission limits:

| Family | Spawn selector | Support and refusal |
|---|---|---|
| Standalone Geno | definition name or reserved kind 4608-4671 | Defined native pickup state, colour/amount payload and collect/expiry events; undefined kinds refused. |
| Vanilla | integer kind from Capsule through Poke Ball (`It_Kind_M_Ball`) | Ordinary common items only, using loaded retail descriptors; later fighter/Pokemon/stage kinds and uninitialized/unsafe kinds refused. |
| m-ex | integer custom kind or alias `"mex:<kind>"` | Only an active, resolved descriptor and logic row; missing/incomplete rows refused. No m-ex display-name table is available, so the numeric alias is the supported name. |

`gd.items()` adds `layer` (`geno`, `geno_article`, `mex`, `vanilla`) and a native
name, m-ex alias `mex:<kind>`, or vanilla alias `vanilla:<kind>` where available. Script-spawned items expose their
owned handle; only standalone Geno rows have a payload. Vanilla and m-ex rows
and events omit payload, and their spawn options refuse it. Despawn is restricted to handles owned by the calling
script; arbitrary existing retail/m-ex objects have no script ownership. Unified
collection events cover known common consumable paths, touch collection of stars
and mushrooms, and held-item pickup paths, including items not spawned by Lua.
Their existing behavior is retained. Untracked-family events identify the item
by engine serial; script-spawned handles use a separate namespace starting at
`0x40000000`. Do not assume every event item ID is an owned despawn handle.
General destruction emits `on_item_expire` with `reason="destroyed"`; native
lifetime completion uses `reason="expired"`, and collection uses
`reason="collected"`. Terminal guards suppress a second event after collection. Fighter
Geno articles remain their existing fighter-owned route and cannot be spawned
through the standalone API. The m-ex itFunction loader remains incomplete;
this API does not implement the missing guest-code loader. Admission checks validate
the descriptor/table structure, not arbitrary guest-code safety.

Model options now include `rot_x` and `rot_y` in degrees (-360..360). Existing `rot`
is still Z rotation. Transform order is scale, X, Y, then Z; static batched vertices,
normal transforms, dynamic replay matrices and alpha depth sorting agree.
`gd.model_get`/`gd.model_instances` return all three fields. Instances with collision
lines refuse nonzero X/Y rotations atomically; use `collision=false` for visual
models that spin in three dimensions.

## Data and fighter-state readback (source update 2026-10-03)

`gd.data_exists(name)` returns `true` or `false`, or `nil,error` when the existence
check fails. It uses the same per-script data namespace and name validation as
`data_read`. A directory can exist even though reading it as a file fails.
`gd.data_read(name)` returns bytes or `nil,"missing"` for an absent file, and
`nil,error` for unreadable, oversized or failed reads. Callers that only inspect
the first return value remain compatible; invalid names still raise errors.

`gd.fighter_mod(port)` queries the active overlay as a table containing
`damage_dealt`, `damage_taken`, `run_speed`, `air_speed`, `shield_max`, `jump_height`, `air_jump_height` and `knockback_taken`, or `nil`
when none is active. The query is read-only across script owners. Explicit
`gd.fighter_mod(port,nil)` clears an owned overlay; table writes keep their
existing offline gate and ownership rules.

`gd.dobj_tints(port)` returns `{count=N,any=boolean}` for registered per-draw tint
overlays assigned to that fighter slot across script owners. This excludes flat
colours and ID rendering. It counts registered overlays; rendering can suppress
an overlay for an unsupported material or pass. Clear/unload/destruction removes
registrations, so the query can verify restoration without changing part caches.

`on_enemy_defeated` reports stock enemy defeat, including a Koopa's conversion to
a shell (even if shell allocation fails and the original enemy is removed).
A snapshotted terminal guard emits one terminal event per enemy lifetime.
Scripted removal, fallout, lifetime expiry or general destruction without stock
defeat remains `on_enemy_removed`; it does not fabricate a reward.

`gd.cpu_mode(port,"stand")` / `"fight"` now persists the choice in the player slot
used by first-frame initialization, rebirth and resets. The CPU entity pair and
bench overlay are updated together; invalid/non-CPU/not-present ports return false.
The drive visual defaults to bob amplitude 0.6. Blink-before-expiry hides four of
every eight logic frames, and logs one `geno item: blink start` line per item;
the guard is snapshot-owned, so rewind restores its lifecycle state.


### Dynamic stage slots (2026-10-03 fix4 source update)

This update supersedes the static-only playback and rest-pose descriptions above.
The six legal retail DATs default to dynamic animation/collision. Use
`gd.stage_slot_load{kind="yoshis_story",dynamic=false}` for an explicitly static
slot, or `dynamic=true` to require support. Mission meshes and other DATs remain
static; explicitly requesting dynamic playback for them refuses.
`stage_slot_info` now reports `dynamic`, `dynamic_phase` (0 static, 2 DAT animation
and moving collision, 3 owned native Yoshi/Fountain controllers), and
`callback_proof` (the audited FD group-0 callback path).
Phase 2 does not mean the complete stage module runs.

Loaded groups use the destination scale and retail clip-zero joint/material/
texture animation setup. Playback pauses while a slot is inactive. Original
DAT joint bindings and native StageData bindings drive the reserved lines through
retail collision transforms, including previous positions for platform carry.
Placement uses the installed world vertices. Ledge checks retain original DAT
joint identity for wall occlusion, despite one reserved backend joint per line.
These source paths need on-screen acceptance for each stage.

Yoshi's Story now runs retail initialization, Randall collision/puffs and the
Shy Guy controller. Fountain uses two independent retail platform controllers;
submerged or absent platforms have disabled collision. Stage-created objects,
items and particles are torn down on exit; another visit resets the controllers.
Both use the engine RNG. Fountain reflections/water effects, Whispy wind/apples,
Stadium transformations and FD's background state machine remain omitted.
Existing demos use these source paths without a Lua API change. Fix4 has
standalone controller/lifecycle evidence; executable and visual acceptance,
including all-six-slots native heap measurements, remain pending.

Fighter placement/unload preserves the entire per-entity CPU controller across
Fall entry. The existing player-slot CPU choice continues to drive respawn;
verify a stood CPU and both transformation/partner entities across ten switches.
The report and on-screen acceptance plan are in
`_build/tmp/codex-stage-switch-fix2-report.md`.

## Preparing room content, warming materials and launching missions (source update 2026-10-03)

This section supersedes earlier area-unload descriptions that imply immediate physical
frees. These APIs are verified against current source and compiler syntax checks;
native rendering, rewind and frame-time acceptance still require a rebuilt executable.
Area construction, `warm`, `item_kinds` and `launch_ready` require an active offline
match and a mod manifest with `"gameplay": true`; the console cannot construct areas
or declare warm jobs. Script gameplay writes remain refused during netplay/rollback.

### Prepare an area before entering it

| Call | Result |
|---|---|
| `gd.area_prepare(name, builder)` | Positive integer handle for an inactive preparation. |
| `gd.area_prepare(name)` | Existing prepared/active preparation handle; a new name requires a builder. |
| `gd.area_activate(handle)` | `true` for an owned prepared/already active handle; `false` for missing, foreign or unloading handles. |
| `gd.area_status(handle)` | `"missing"`, `"prepared"`, `"active"` or `"unloading"`. |
| `gd.area_loaded(name)` | Whether this script's named area is active. |
| `gd.area_load(name, builder)` | Builds an active area, or activates a preparation without rerunning its builder; `false` for an already active or still unloading name. |
| `gd.area_unload(name)` | `true` when the name exists; hides its content immediately and schedules resource retirement. |

Names are 1�47 bytes without NUL. Handles belong to the script generation; positive
32-bit handle arguments are required. Name-only preparation returns `nil` for an
unloading name or an area created by ordinary `area_load` without a preparation handle.
Repeated preparation of an existing prepared/active name returns its original handle
without calling another builder.

```lua
local room = gd.area_prepare('next-room', function()
    gd.stage_add_line(500, 100, 600, 100, 'floor')
    -- gd.model_spawn(loaded_model, transform) can prepare GXMS instances here.
end)
-- The reserved floor and models are absent from collision queries and drawing.
assert(gd.area_status(room) == 'prepared')
-- Later, after material warming and before crossing the doorway:
assert(gd.area_activate(room))
```

Builders are synchronous: call preparation early, and keep each builder small. They
cannot nest, yield or unload areas. A builder error retires its partial content and
propagates the Lua error. Prepared builders support collision lines and GXMS model
instances; retail target/enemy spawning and legacy stage DAT model GObjs are refused.
Spawn enemies after activation, following their separate material warm declaration.
Explicit `stage_link` floor seams must remain within one area slot: independently
activated areas cannot share a cached floor chain. Standalone lines belong to area 0.

Line/model edits inside an area builder share one collision-island batch. Activation
changes the area gate without walking its line/model records. Unload immediately
removes collision, draws and public model handles, then retires at most two
line/instance records per logic frame, with collision lines retired before their
instances. Wait for `area_status(handle) == 'missing'` before relying on reclaimed
capacity or reusing that name. The pools remain 64 areas, 256 instances and up to
768 scripted lines. Ordinary `area_load` still supports targets; those retail item
GObjs are removed synchronously on unload, outside the deferred geometry budget.
`stage_stats` excludes unloading records and counts prepared resources as reserved;
`visible_instances` respects the area gate.

Area membership, activation and the deferred cursor are snapshot state. Savestates
can restore prepared, active or unloading content, and deterministic cleanup resumes
from its restored cursor. Immutable model assets stay pinned for the scene. Lua
builders are not replayed by history: save stable states outside a builder and run
`gd.rewind_test` for the mission's existing replay path. Preparation/activation are
source mechanisms, not a measured guarantee that every room takes less than 4 ms.

### Declare materials before their first visible draw

`gd.warm{enemies={...}, items={...}, models={...}, fighters={...}} -> handle` queues
material discovery and background pipeline compilation. All four lists are optional;
unknown top-level keys are refused. There are at most 16 outstanding handles and
128 listed objects per declaration.

* `enemies`: names accepted by `spawn_enemy`: `goomba`, `koopa`, `redead`, `like_like`,
  `octorok`, `polar_bear`, `topi`.
* `items`: numeric kinds, `"vanilla:<kind>"`, `"mex:<kind>"`, or an active Geno item
  name. m-ex kinds must already be registered; Geno definitions must be active.
* `models`: handles returned by `gd.model_load`, retained by this script. Load assets
  before declaring them; a warm declaration does not accept model filenames.
* `fighters`: loaded player ports **1�6**, such as `{1, 2}`. These are entity slots,
  not fighter names or CharacterKind values. An absent entity fails discovery.

```lua
local materials = gd.warm{
    enemies = {'goomba', 'koopa'},
    fighters = {1},
}
-- Poll from on_tick, including while the launch loading hold is active.
local done, why = gd.warm_done(materials)
if done then
    gd.warm_release(materials)
elseif why then
    gd.log(why)
end
```

`gd.warm_done(handle) -> done, error_or_nil` is `false,nil` while pending,
`true,nil` when complete, or `false,"warm material discovery failed"` on failure.
`gd.warm_status(handle)` returns `{objects, prepared, pending, done, failed}`:
`objects` counts requested descriptors, `prepared` counts completed descriptor
captures, and `pending` combines descriptors not yet captured with pending captured
pipelines (`-1` on failure). It is not a percentage. Poll per tick rather than spinning.
One descriptor is traversed across all warm jobs per tick; discovery can still perform
CPU work and temporary model allocation, but it creates no enemy/item AI or visible
object. Successful completion covers the material variants discovered by those
current descriptors; later costume/material/content changes may need a new declaration.

`gd.warm_release(handle)` releases the job handle, with no return value. Release
completed or failed jobs to reclaim the 16-job pool. Releasing a pending declaration
removes its readiness tracking; it does not establish that compilation completed.
Jobs are scene-scoped and owned by the script generation; stale/foreign handles raise
an error. Scene changes and script retirement clear them. Warm progress is diagnostic
native state, not rewind simulation state, and does not advance during resimulation.
The single-feature [Warm demo](../melee/pc/scripts/examples/demos/warm/scripts/main.lua)
declares all seven enemy descriptors before spawning its first Goomba.

`gd.item_kinds() -> array` lists currently registered/readable item descriptors as
`{kind=number, name=string, spawnable=boolean}`. Names use `vanilla:<kind>` or
`mex:<kind>` for stock/m-ex descriptors, and the definition name for Geno items.
`spawnable=false` descriptors can still be useful to warm: readable materials do
not imply that the public item-spawn API accepts that kind. This list reflects the
current scene/mod registrations, not every item that could exist in another install.

### Keep loading covered until a mission director is ready

Scene launch accepts `mission=<folder>` or `maze=<seed>,<size>`, for example:

```text
MELEE_SCENE=mission=first-room;p1=fox;stage=fd
MELEE_SCENE=maze=7,12;p1=fox;stage=fd
```

A mission folder identifier uses only letters, digits, `-` and `_` (1�127 bytes).
Maze seed is 0�2147483647 and size is 1�1024. The latest mission/maze selector wins.
The selector routes to an offline training host and holds loading while a Lua
mission director stages content; the engine does not generate or read the mission
layout itself. An active mod can supply a scene-grammar string in `mod.json`, such
as `"autostart": "maze=7,12;p1=fox;stage=fd"`. Autostart is considered only when no
scene was already configured; the first valid active declaration is selected.

`gd.launch_request() -> {mission, seed, size, mod, pending}` reads the request.
`mission`/`mod` are strings (empty when absent), and `seed`/`size` are numbers.
For mod autostart, `mod` identifies its selected mod; explicit scene configuration
has no selected mod filter.

The engine initializes the host and loaded fighters, grants the active-match API,
and delivers `on_match_start` before `on_launch(request)`. It then invokes exactly
one enabled gameplay script's `on_launch`; mod autostart restricts candidates to the
selected mod. Zero or multiple candidates leave loading held and log the refusal.
`on_launch` is delivered once per request. Retiring its owner allows a replacement
hook to receive the pending request. Tick hooks continue while loading is held:
retain the request and retry stage/CPU operations from `on_tick` when they report
an unsafe/not-ready entity. Do not expect logic-frame waits to advance during staging,
and do not depend on the engine repeatedly calling `on_launch` after a hook error.

The director calls `gd.launch_ready() -> boolean` only after its level is staged,
prepared areas are activated where required, and its declared materials are ready.
Only the selected owner may call it. It returns `false` while any of that owner's
unreleased warm jobs are pending or failed; `true` clears the script staging hold.
The loading screen's other pipeline readiness conditions still apply. `launch_ready`
does not itself activate areas or verify a mission layout.

`gd.launch_cancel([reason])` clears/consumes the pending launch and logs the reason,
with no return value. Once an owner is selected, only it may cancel; before selection,
an authorized offline gameplay script or console may cancel. Cancellation does not
unload staged content or release warm handles. A scene transition cancels pending
staging. The director should cancel on a terminal load/warm error rather than leave
an unfinishable request held.

## Retail Classic and Adventure (1P)

Source addition, 2026-10-03. Offline gameplay mods only. These APIs use the retail
mode tables, opponents, handicaps, AI levels, bonus stages, continues and Adventure
cutscenes. Native play/controller acceptance remains pending; source syntax and
single-feature Lua stubs are checked.

| Call | Contract |
|---|---|
| `gd.start_1p{mode="classic", fighter="mario", difficulty=2, stocks=3, loop=true}` | Queues a safe scene reset. Mode is `classic` or `adventure`; fighter is an installed scene-selector name or explicit kind token, without player-option suffixes. Difficulty 0..4 (Normal 2), stocks 1..99. Returns `true`, or `false, reason`; an existing or pending 1P run cannot be replaced, including by its owner. Requires a manifest-backed gameplay mod. |
| `gd.mode_1p()` | Snapshot table below, or nil outside the tracked offline retail run. |
| `gd.hold_1p([ticks=1800])` | Claims the current interstage barrier from its clear/complete/game-over callback. Returns boolean. One claim per barrier, clamped to 1..1800 host ticks; cannot renew its deadline. |
| `gd.release_1p()` | Releases this script's hold; returns false if absent or another script owns it. |
| `gd.loop_1p(enabled)` | Owner-only New Game+ switch; returns boolean. A run adopted by `spawn_1p` from a manually entered retail mode cannot enable looping, because it has no original launch settings. |
| `gd.end_1p()` | Owner-only, idempotent cleanup. Cancels a pending initial launch, or safely resets an active run to the menu. Templates, tints and holds are released; record protection remains until retail teardown. Returns boolean. |
| `gd.spawn_1p(port, options)` | Apply a template to the current main entity and each replacement in that port before its first logic frame. Options: the existing `damage_dealt`, `damage_taken`, `run_speed`, `air_speed`, `shield_max`, `jump_height`, `air_jump_height`, `knockback_taken` multipliers (finite, clamped 0.1..4), plus optional `tint=0xRRGGBBAA`. Returns boolean. `nil` clears this script's template/modifier/tint even after match end. A template adopts an otherwise manual retail run into record-protected script ownership. |

Each hook receives one snapshot: `{mode, stage_index, stage_kind, loop, player_port,
held, final, opponents}`. `mode` is a string; `stage_index` is the zero-based retail
**battle ordinal**, including Classic bonus stages and Adventure's separate fights
within a stage block. Retries keep that ordinal. `stage_kind` is `battle`, `team`,
`giant`, `metal`, `bonus` or `boss`, from the existing retail flags; these tags do
not change match rules. `loop` begins at zero. Player entity port is 1. `opponents`
contains only present enemy CPU main entities, excluding allies, with
`{port, char, kind, entity}`; `char` is CharacterKind, `kind` is FighterKind, and
`entity` is a monotonically changing spawn generation. Do not use that generation
as a retry seed. Physical controller ports remain separate from fighter entity ports.

- `on_1p_stage_start(e)` runs after initial entities exist, before their first
  logic frame. Existing `on_match_start` still runs first.
- `on_1p_spawn(e)` adds `port` and `entity`; it notifies after a new main entity
  exists. Native templates already applied before its first logic frame. Notification
  does not request a new template; calling `spawn_1p` never synthesizes a spawn event.
- `on_1p_stage_clear(e)` runs when retail accepts a clear, including bonus-stage
  exits. Failed battles and continued/retried attempts do not produce a clear.
- `on_1p_boss_defeated(e)` adds `boss_kind` and `port`: Master/Crazy Hand use their
  native HP/death detection; Adventure Bowser/Giga Bowser use accepted final-block
  battle clears. These events do not override Crazy Hand or Giga Bowser conditions.
- `on_1p_complete(e)` is the definitive completion event, with `final=true`.
  Classic final clear and completion share a barrier and deadline. Adventure can
  reach completion after a retained cutscene; its distinct completion barrier permits
  a fresh bounded hold. Bowser clear cannot promise completion before the Giga decision.
- `on_1p_game_over(e)` runs when a continue is declined or retail exits through
  its no-contest/retry cancellation path. Explicit script scene replacement also
  signals termination; `end_1p` is cleanup and does not recursively signal its owner.

The barrier freezes the old scene after its exit decision, before next-scene preload.
No retail GObj, AI, clock or input logic advances. Drawing, `on_tick`, `on_draw` and
fresh `gd.pad` reads continue, so A/B/START cannot leak through to retail while held.
Use those tick hooks for panels, not logic-frame waits. Unload/disable releases the
owner's hold and ends its scripted run. Deadline expiry releases the flow; an expired
completion hold disables looping so uncommitted progression cannot auto-start NG+.

Templates multiply the retail ratios instead of rewriting the fighter attributes.
Giant size, metal armour, team size and CPU level therefore remain retail values.
They are per replacement **main entity in a port**, not independent persistent
controllers for multiple entities sharing a port: Ice Climbers' follower shares the
port's stat modifiers; the template tint is applied to the main entity. Wireframe
replacements reuse their port's deterministic template; their predecessor's overlay
is cleared before applying it. New stages and terminal exits clear templates/tints.
No jump-height field is added by this capability.

Scripted runs write **no Classic/Adventure score, clear/difficulty/stock, target-test,
play-time, coin or trophy progression records through the retail 1P exit paths**, and
skip their card-save dispatch. Continue choices and stock reset behavior remain;
scripted continues do not debit the memory card's coin count. Completion skips the
retail trophy/congratulations/credits majors to avoid unlocking trophies or inflating
card records; the script may show its own short congratulations. New Game+ starts
from stage zero with the original fighter, difficulty and stock setting. A standalone
`scene_launch` Classic/Adventure without script templates keeps normal retail records
and ending behavior. Companion growth and saving belong to the mod.

Snapshot/rewind/state-file imports are refused while this orchestration is active:
the native lifecycle/hold/loop state is not snapshot-owned. No native snapshot resume
is promised. Modifiers and spawn templates themselves live in game memory.

Single-capability catalogue demos: `demo_1p_awareness`, `demo_1p_hold`,
`demo_1p_spawn`, `demo_1p_loop` under `pc/scripts/examples/demos/`. Native suite
fixture: `script_1p`; offline demo stub: `pc/tests/onep_demo_test.lua`.


## Surface parameter updates (EM1, 2026-10-04)

`gd.fighter_shader_set(port, {params={...}})` updates the calling script's existing
fighter surface selection, retaining its program. The complete array replaces the
previous 16 floats (omitted tail slots become zero). Returns `true` or `nil,error`
if no owned selection exists. Invalid ports, non-finite values or more than 16
values raise argument errors. Updates perform no file reads, shader registration
or compilation. The independent catalogue entry is
`melee/pc/scripts/examples/surface-shaders/scripts/parameter-update.lua`.

Select your surface program before `gd.warm{fighters={1,2}}`. Fighter warm jobs now
capture actual GX material variants under that selected program for both loaded
primary and sub-fighter joints. Poll `gd.warm_done` before enabling play. This is
coverage of current loaded materials; future costumes, metal materials or other
uncaptured GX configurations can still compile. Selection follows player port,
including CPU and sub-fighter draw callbacks, and survives costume/metal/size
changes within the scene. Lifecycle cleanup clears it. Script-owned visual state
is not a rewind snapshot; rebuild selection and parameters from restored Lua
state. Use logic-time uniforms for deterministic animation, since surface `s.time`
is host time. No Aurora renderer source or ABI change is required for these APIs.


### EM1 gameplay observations and live value overlays (2026-10-04 source additions)

These additions have syntax checks and native-suite source fixtures. They have not
been linked or executed in the game. `gd.fighter_mod` also accepts `fall_speed`,
`weight`, and `shield_regen`, each a finite multiplier clamped to 0.1..4 and
returned by its getter. Fall speed scales the terminal velocity in the common
fall callback, preserving gravity and character-specific fall callbacks. Weight
scales the live weight input of collision-knockback formulas and the ordinary
explicit-weight route; fixed-weight throw behavior still uses its
retail weight-selection rule. Shield regeneration scales the central idle shield
health increment. All three are read overlays in the existing snapshot-owned
modifier set. Replacement resets unspecified keys to one; clear/unload restores
live baseline calculations. No attributes or DAT tables are edited. The same
port-owned overlay applies to primary/subfighters and CPUs. Existing modifiers
survive respawn by design; a rules module must explicitly clear its own statuses
and modifier set on its lifecycle boundaries. See demos/modifier-fall-speed,
demos/modifier-weight, demos/modifier-shield-regen.

Collision-origin `on_hit(attacker, victim, info)` adds `context_valid`,
`move_tag`, `element_tag`, numeric `element`, `attacker_action`,
`attacker_grounded` (absent for no owner), `victim_grounded`,
`attacker_damage` and `victim_damage`. Damage fields are the current percent at
collision, before the eventual central percent application; `dealt` is the
collision's scaled damage. Context is captured through scalar arguments at the
collision site, never reconstructed from deferred fighter state. Synthetic
`gd.hit`/enemy observer paths may have `context_valid=false`; consumers must check
it. Elements map normal=0, fire=1, electric=2, ice=5, darkness=13; other retail
elements remain numeric and have `element_tag="unknown"`.

Common action states classify jab (including rapid jabs), dash_attack, tilt,
smash, aerial, grab and throw. The same common ranges apply to retail fighter
families, clones and Geno fighters while they use those states. Family-specific
states are `unknown`: an index beyond the common range is not automatically a
special. Item hits remain `unknown` instead of claiming every item is a projectile.
Thrown-body hits attribute the owner when available. Family-specific normal
attacks, special throws, Geno custom states and lingering hitboxes after their
owner changes state need an explicit future move-metadata contract. Direct throw
percent routes do not currently emit `on_hit`; this addition does not invent them.
See demos/hit-context. `on_hit` remains a queued observer after collision result
application; returning a table cannot patch damage, element, knockback or hitstop.

| Hook | Payload and exact source |
|---|---|
| `on_ko(attacker_or_nil, victim)` | Retail death accounting; self/environment attribution is nil; primary lifetimes only |
| `on_stock_lost(port, stocks_remaining)` | After the same death accounting; LAB unlimited respawn still reports falls; delivered after on_ko |
| `on_jump(port, action, sub)` | Entry to common JumpF/JumpB |
| `on_air_jump(port, action, sub)` | Entry to common JumpAerialF/JumpAerialB; family-specific multijump states excluded |
| `on_ledge_grab(port, action, sub)` | Entry to common CliffCatch |
| `on_grab(port, action, sub)` | Successful common CatchPull/CatchDashPull; grab attempts excluded |
| `on_throw(port, action, sub)` | Entry to common ThrowF/B/Hi/Lw; family-specific throws excluded |
| `on_taunt(port, action, sub)` | Entry to common AppealSR/AppealSL; family-specific taunts excluded |
| `on_shield_hit(port, action, sub)` | Actual accepted fighter/item shield collision, including repeated contacts during shield stun |
| `on_perfect_shield(port, action, sub)` | Accepted fighter shield collision with retail powershield flag x221C_b2; reflected items take a separate unimplemented observer route |

All hooks are opt-in queued observations delivered after the logic frame, before
on_frame, and suppressed during silent resimulation. They do not change retail
behavior. Common transition signals fire only when old and new states differ;
a repeated same-state motion restart is not another transition. `on_land` remains
the existing grounded-commit event. Each new hook has one demos/event-* catalogue
example. Gameplay effects still require offline script authorization.

## Simulation checkpoints (EM1, 2026-10-04)

Source addition; isolated native/game helper fixtures and syntax checks pass.
Integrated `gd.rewind_test` with active modifiers is an integrator check.

`gd.sim_supported == true` advertises the offline checkpoint API.
`gd.sim_commit(blob, operations)` accepts an opaque string up to 16384 bytes and
at most 24 dense-array operations. A gameplay mod may commit once inside its
`on_frame` in an offline active match. Console calls, tasks, other hooks, online
sessions and explicit replay-time calls are refused. Validate/allocate everything
before any gameplay writes. Eight loaded generations may own checkpoints.
The sparse native journal has a 128 MiB budget; exhaustion refuses the commit.

Supported operations:

- `{op='fighter_mod', port=1, values={run_speed=1.2}}`: replaces the script's
  complete fighter overlay. Omitted values default to 1; all supplied values
  must be finite and within 0.1..4. Keys are `damage_dealt`, `damage_taken`,
  `run_speed`, `air_speed`, `shield_max`, `jump_height`, `air_jump_height`,
  `knockback_taken`, `fall_speed`, `weight`, `shield_regen`. A nil `values`
  clears the overlay. Ownership conflicts refuse the whole commit.
- `{op='damage', port=2, value=18}`: sets real fighter/HUD percent, 0..999.
  Fractions truncate exactly as `gd.set_damage` does. Healing is an absolute
  lower damage value computed by the rule engine.

`gd.sim_read()` returns the calling script's checkpoint or nil. Its opaque bytes
live in game BSS already covered by the snapshot; Lua globals do not. Serialize
all deterministic rule state (seed, statuses, stacks, timers, pending events and
equipped modifiers) and import it in `on_loadstate`. Never deserialize by
executing the string as Lua. `gd.sim_replaying()` is true during both silent
history frames and the last history frame, whose ordinary Lua hooks still run:
return immediately from rule evaluation then. `on_loadstate` must still import.
The journal replays the stored absolute writes/checkpoint at their original
post-frame boundary without evaluating Lua or forking history. The last replay
frame is covered too. New live writes after a seek fork future history.

This contract covers only outputs submitted through `sim_commit`; other Lua
writes, hit mutation, spawned actors and arbitrary native presentation are not
made replayable by storing a blob. The script owns its schema, bounded serializer
and restoration. Reload/unload/disable invalidates old history, clears storage,
and existing fighter ownership teardown clears its overlays. Scene teardown
clears checkpoints and the journal. Old saved load generations cannot alias a
new script in the same slot. Demo: `demo_sim_checkpoint` in the feature catalogue.

`gd.sim_clear()` immediately clears the calling gameplay mod's fighter overlays
and checkpoint, including while the LAB is paused. It is offline-only and refuses
explicit calls during history resimulation. Like other manual gameplay edits it
forks future history and forces a checkpoint at the next boundary. It does not
reset damage already dealt/healed; reset pure Lua rule state in the same command.
Earlier snapshots still own their earlier blob; importing nil on load must reset
the script's rule state. This manual edit differs from timed cleanup operations,
which belong in `sim_commit` so history can replay them.

### EM1 collision context and LAB modifier adapter

Hit payload `context_valid` identifies the captured collision fields. When true,
`move_tag`, `element_tag`, `attacker_damage`, `victim_damage`,
`attacker_grounded` (only if a fighter owner is known), and `victim_grounded`
describe collision-time state. Unknown move/element names remain unclassified:
item contacts do not automatically mean `projectile`. An unknown attacker may
still produce a valid victim hit-taken event; no fighter attacker is fabricated.
The Lua adapter preserves these percent/ground values in `self_context` and
`target_context`; stocks are sampled from `gd.player` at hook dispatch, because
collision-time stock capture is not provided.

The Envoy `mod_lab` module remains dormant until explicit `mod add <id> [port]`
in an offline active LAB match. `mod list`, `mod trace` and
`mod intensity <0..1>` expose its data/look; `mod clear` clears the entire debug
build immediately, including while paused. Partial clear is intentionally not
exposed. Classic/Adventure and an active Envoy run/director refuse activation.
Hooks queue pure events; one live `on_frame` samples players, drains rules and
commits all outputs. Hit percentages/ground flags are used only with valid native
capture. Shader warmup completes before queued equipment activates. Host ticks
poll paused visual restoration without advancing rule timers or game outputs.
All rule/adapter roots, pending equipment, owner slots and lifecycle observations
are serialized; a missing blob retires stale numeric-slot overlays from old saves.
Checkpoint failure disables debug evaluation and clears native/pure/visual state.
KO/respawn clears temporary statuses/stacks/events; equipment, steady values and
native hit rules persist and are re-derived; a neutral shader
selection may be reused as a cache while an opponent remains loaded. Scene change
recreates the visual adapter, because shader handles are scene-owned.


`gd.post_ready(handle)` returns a boolean for an owned post pass. It is false
until that exact pass successfully records and resolves using its current shader
program; an expired or foreign handle returns `nil,error`. This is render-only
readiness, not proof of GPU execution, visual correctness, or every future target
configuration. A successful body reload replaces its program and clears effective
readiness until the new program records. Use a zero-strength or identity pass
while loading, then retire it after readiness. The independent catalogue demo is
`demos/post-ready`; `demos/surface-params` separately demonstrates per-frame
fighter uniforms without shader loads. Source/native fixture checked; game
acceptance remains pending.


### Native hit rules (EM2)

Offline gameplay scripts declare rules ahead of combat; Lua never runs during collision.
`gd.hit_rule_add(port, rule[, sub])` returns a handle; `gd.hit_rule_remove(handle)`
removes its owned copies. `gd.hit_rules(port[, sub])` returns an array with
`owner` and `status_bits`. `gd.hit_rules_clear(port[, sub])` retains statuses.
`gd.fighter_status(port[, bits[, sub]])` reads/sets the 31-bit mask (nil bits
for a selected partner read). Boolean sub selects primary(false)/partner(true).
Omitted writes mirror both; omitted reads select primary. Each of the twelve
entities has an independent eight-rule table/mask. CPU slots participate.
Ownership covers rules and statuses. Unload/scene clear them; KO only if scripted.

Example: `gd.hit_rule_add(1,{id=101,match={move='smash',element='normal'},
change={element='fire',damage=1.2}})`. Move tags: any, unknown, jab, dash_attack,
tilt, smash, aerial, special, grab, throw, projectile (owned items). Optional
grounded and original element filters are frozen at creation. Allowed original
and converted elements: normal, fire, electric, ice, darkness. Every other
original is immune, including Sleep, Catch, Inert and Lipstick. Creation changes
permit element, damage, knockback_growth, knockback_base, shield_damage, hitstun.
Contact rules use match.status_bits (all requested bits) or match.incoming=true,
and permit only damage/knockback_taken. Incoming rules belong to the victim.
Original element matches even after conversion. Missing metadata permits incoming
ordinary-element rules with unknown move/grounding; outgoing owner is not inferred.

Insertion order is fixed, last element setter wins. Multipliers individually
and running products are clamped to 0.1..4 after each rule. Shield delta -100..100,
stun 0..120 logic frames; changed damage capped500, growth/base1000, shield
result -100..100. Unchanged retail fields retain original values. Unknown fields
and fraction requests are refused: conversion changes the whole hit, with no
second damage component. Creation values stay latched for a capsule; clear affects
future creation and current contact rules, not an already launched projectile.
Per-victim contact scalars do not mutate a shared capsule. Metadata capacity1024;
exhaustion logs once and refuses new creation changes.

Electric uses retail hitlag; Fire uses fire reaction/thaw; Ice freezes only when
retail thresholds qualify; Darkness has its own visual effect. Original sound
kind/severity remain, so conversion alone does not change the attack sound.
Creation damage affects clanks/shields/stale-adjusted damage. Contact-only damage
does not affect clank priority. Staling still adds one queue entry. Stun uses
the existing Geno largest-contact-bonus channel.

Live checkpoint scripts must use absolute journal outputs:
`gd.sim_commit(blob,{{op='hit_rules',port=1,rules={...},status_bits=1,sub=false}})`.
Omitted sub mirrors both. Direct setters branch history and must not be used
per-frame for replay. Tables/masks/handles/metadata live in snapshotted game BSS;
native replay applies journal outputs. on_hit provides parallel hit_rule_ids and
hit_rule_owners arrays of actual changes. Compare owner AND ID before naming
a modifier. Creation IDs stay latched; contact IDs describe the victim's hit.

Retail playable family special states, clones and Kirby copied specials are mapped.
Unmapped character-specific normals/taunts, bosses/wireframes/Sandbag and custom
m-ex/Geno extended states return unknown. Anonymous environmental and synthetic
paths outside audited contact are excluded. Detailed site census, retail effects
and integrator acceptance: _build/tmp/codex-hit-rules-report.md. Source/isolated
helper tests do not establish live LAB rewind exactness.


EM3 LAB drive commands: drive give|drop [common|magic|rare|unique] [seed], and bag.
Z+START opens the controller-only four-slot/twelve-drive bag; A selects/equips,
B closes, Left/Right pages detail text. Keystones are separate, never rolled.
Bag edits and native rule/overlay outputs join the modifier sim_commit blob.
Highest tier per duplicate ID contributes once; base implicits multiply with caps.
Purple status_duration is Lua-only and never a native fighter_mod field. Manual
physical drops use the existing item_spawn timeline branch outside on_frame,
with compact owned-handle records checkpointed next frame. Default inventory
is fresh per scene/run; drive_lab.tuning.persist controls retention. These are
offline LAB diagnostics, with no opponent rolls or Classic loot integration.
See Envoy PLAYTEST.md for physical drop/checkpoint boundaries and acceptance.


Envoy EM4 native hit-rule fields (2026-10-04; source-tested, rebuild required).
`change.percent_damage` and `change.launch` are neutral-at-1 ratios for ordinary
attacks. They support unconditional, status-conditioned and incoming matches.
Each side adds matching ratio-minus-one contributions and caps once: percent
0.6..1.6, launch 0.6..1.3. The two sides remain separate families.
`gd.hit_rules(port).percent_only == true` identifies the updated engine.

Percent-only damage scales the accepted, already-staled damage at its commit,
after current-frame launch selection. It leaves original hitbox damage, shield
damage, clank priority, hitlag inputs and staling unchanged; the on-screen
percent/HP changes and later hits see the real accumulated percent. Special
nonordinary elements, phantom hits and zero-damage detector contacts are
excluded. Launch scales the final retail knockback scalar. Legacy `damage`,
`knockback_growth`, `knockback_base` and fighter-modifier damage fields keep their
existing behavior. New rule fields and pending percent deltas are snapshotted
game state and included in the native simulation journal. Old native snapshots
and journals must not be reused after upgrading this binary. Live collision
and LAB rewind acceptance remain required.


## Fighter capabilities (2026-10-04 source pass)

These calls extend passive fighter modifiers. Writes require an active offline match and a gameplay script (or console), and fork the LAB rewind timeline. Each selector is an **entity**: 1?6 are the primary fighters of ports 1?6; 7?12 are their secondary entities (Nana or a second form). Missing entities refuse effect/item/status writes. CPU control does not change permissions. Each native record has a script owner; competing scripts receive false. Read calls do not claim ownership. No native pointer crosses the Lua boundary.

| Call | Contract |
|---|---|
| `gd.fighter_caps(entity)` | Owned override table or nil, plus a second return containing this live entity's retail air-jump count (nil if missing). Useful for relative bonuses. |
| `gd.fighter_caps(entity, options)` | Replace overrides; returns boolean. `air_jumps=0..8` sets air jumps; omitted uses retail. `shield`, `air_dodge`, `run`, `grab`, `specials` are boolean restriction flags: **true forbids**. Unknown keys/types refuse. |
| `gd.fighter_caps(entity, nil)` | Clear this owner's movement overrides. |
| `gd.fighter_armour(entity)` | `{damage, knockback}` thresholds, or nil. |
| `gd.fighter_armour(entity, {damage=n, knockback=n})` | Each threshold 0?1000; zero disables that test. Strictly below either enabled threshold suppresses the ordinary retail damage reaction, while percent damage remains. Nil clears. |
| `gd.fighter_effect(entity, kind)` | `{value, frames}` or nil. |
| `gd.fighter_effect(entity, kind, value, frames)` | `kind` is `intangible`, `invincible`, `metal`, or `size`. Duration 0?3600 logic frames; zero clears that owner's kind. Use value 1 for enabled non-size kinds (accepted range 0?1); size is an absolute scale 0.25?4. Effects expire automatically. |
| `gd.give_item(entity, kind)` | Retail numeric kind ID or `"random"`; boolean result. Empty hands, neutral Wait/Fall/Jump states, enabled match items, spawn cap, portable kind and actual pickup eligibility required. Random is weighted from enabled portable kinds. Failure destroys any newly spawned orphan. |
| `gd.nearest_opponent(entity[, exclude_entity])` | Entity ID or nil; optional exclusion supports chaining to a different victim. |
| `gd.opponents_in_radius(entity, radius[, exclude_entity])` | Ascending entity IDs, radius 0?100000 world units inclusive. No line-of-sight check. Same-port entities and teammates in team matches are excluded, as are dead/entry/benched entities. Equal nearest distances choose the lower ID. |
| `gd.fighter_timed_status(entity, channel)` | `{value, frames}` or nil. |
| `gd.fighter_timed_status(entity, channel, value, frames)` | Four independent channels (1?4), finite value ?100000?100000, duration 0?3600 logic frames. Replaces a channel owned by this script; zero frames clears. Generic event-carried values, with no built-in hitlag/hitstun mutation. |

`fighter_timed_status` is separate from the hit-rule API `gd.fighter_status(port, bits, sub)`. The latter stores a bitmask; timed values do not automatically change it or install hit rules.

Air-jump overrides retain retail landing/ledge/hit counter resets and exhaustion writes. The initial ground jump is counted internally, so an override of five means five **air** jumps. Kirby/Puff repeat bounded retail multi-jump motion/impulse rows; the penultimate script is reused while extra jumps remain, since Kirby's final script has no next-jump gate. Movement claims apply to the entity selector through respawn/transformation; other timed values bind to the current fighter object and retire when it is replaced.

Restrictions gate entries into GuardOn/powershield, EscapeAir, Dash/Run/TurnRun, Catch/CatchDash/AirCatch and the shared ground/air SpecialN/S/Hi/Lw decisions. An action already underway finishes its normal callbacks; input is not latched or rewritten. Item throws remain available with grab forbidden. Forced state changes and character-specific internal special continuations are not filtered. CPU decision checks share the jump-limit overlay; live CPU lockup acceptance remains pending.

Armour uses the existing `ftCo_8008EC90` no-reaction branch after retail commits percent and calculates knockback. Damage thresholds compare the individual scaled damage of the hit selected by retail to determine the reaction, rather than the sum of damage from simultaneous contacts. Percent still keeps that full sum. Knockback thresholds compare the result **after** crouch, ice, charge, scale, Yoshi/Bowser and metal modifiers. It does not intercept special damage-reaction modes, grabs/throws, or state-specific callbacks. Existing retail armour is left intact.

Timed hurt protection uses retail counters/setters and colour animation. Cleanup ages the original counter using observed retail decrements (including hitlag pauses), restores it when still attributable to the script and preserves a longer newer counter. The shared counter cannot distinguish a new equal/shorter retail timer; exact independent overlap ownership requires a follow-up setter hook in the collision owner's files. Metal refuses an already-metal fighter and uses retail material/attribute setup and teardown. Size restores the saved scale only while the current scale equals its applied value. New retail effects with the same value are likewise not distinguishable. Use these timed effects in controlled offline scenarios until that overlap hook and runtime acceptance are complete.

Give-at-stage-start uses the existing event hook rather than a persistent native queue:

```lua
function on_match_start()
  if not gd.give_item(1, "random") then gd.log("stage-start item grant refused") end
end
```

A director may retry on a later neutral frame, once per stage, if entry animation initially refuses. The allowed portable kinds are Bob-omb, Mr. Saturn, Bat, Beam Sword, Green/Red Shell, Ray Gun, Freezie, Motion-Sensor Bomb, Super Scope, Star Rod, Lip's Stick, Fan, Fire Flower and Pok? Ball. Heavy items, consumables and character articles are refused. A successful grant becomes an ordinary retail held item; script unload does not confiscate it.

All timers, ownership and entity bindings live in the already snapshotted `script_game.c` BSS. Scene teardown and native script-unload fallback release overrides and timed effects even if Lua cleanup throws. The `script_fighter_caps` headless suite fixture covers game-side helpers and Lua validation. Six single-feature examples are indexed in the demo catalogue. The separate `fighter-targeting/scripts/rewind-proof.lua` fixture requires timer expiry followed by `pass == true` and `diff == 0`; **it has not been executed**. This packet did not build or launch the game, and source/stub checks do not establish gameplay or rewind acceptance.


Envoy EM4 LAB opponent commands: `foe roll [strength] [seed] [port]`,
`foe clear`, `foe list`, `foe fight [port]`, and `foe stand [port]`.
Default rolls target the player build strength. CPU modifier edits and foe
rolls must commit separately; timed opponent nameplates temporarily replace
the debug HUD. These commands are offline LAB tools, not Classic integration.


## Fighter afterimages and point tracers (FX1 source; runtime acceptance pending)

`gd.afterimage_add(port, options)` and `gd.tracer_add(options)` return an owner-scoped
handle or `nil, reason`. `gd.afterimage_set(handle, partial_options)` and
`gd.tracer_set` return true or `nil, reason`; the corresponding `_remove(handle)`
returns true. Foreign/stale handles and malformed options raise Lua errors. Port
and `sub` are immutable. These APIs have no gameplay gate or simulation writes.

Afterimage options: `copies=1..6`, `spacing=1..8`, `lifetime=2..31` logic frames,
`fade=0.25..4` exponent, `tint={r,g,b,a}`, `tail={r,g,b,a}`,
`blend="alpha"|"additive"`, `surface="own"|"silhouette"|"gradient"`,
`scale=0.25..2`, `follow=false`, `trigger="always"|"moving"|"flag"`,
`speed=0..100`, `flag=false`, `clear_on_respawn=false`, `sub=false`,
`intensity=0..1`, and `offset={x,y,z}` (each -100..100). One emitter per port/sub;
12 total. A port's primary and sub-fighter must share surface and blend.

Tracer options additionally include `port=1..6`,
`anchor="right_hand"|"left_hand"|"right_foot"|"left_foot"|"head"`,
an explicit joint index 0..254 (tail/custom skeleton), `{joint=...}`,
`{hitbox=0..4}`, `"held_item"`, `"sword_tip"`, or `{item=serial}`.
Sword tips read the existing retail trail; they do not enable it. `gd.tracer_hitboxes(port,
options)` makes one handle for all active hitboxes and selects colour/shader from
the actual hit element. `anchor="active_hitboxes"` is equivalent. Limit 64 handles.
`width=0.05..8`, `taper=0..4`, `length=2..31`, `smoothing=1..8`, `depth=true`,
`shader="solid"|"glow"|"fire"|"electric"|"frost"|"dark"`,
`edge={r,g,b,amount}`, and `params={strength,frequency,core_width,motion_rate}`
(0..10; strength clamps to 1). Colours use 0..1 components. `tail` fades along
the ribbon; `edge` blends across it. Catmull-Rom smoothing creates intermediate
geometry without adding simulation samples.

Declare emitters before `gd.warm{fighters={1,2}, tracers=true}` and poll
`gd.warm_done`; cold/unsupported historical draws are skipped. New surface/blend,
costume or material configurations need another warm pass. `gd.motion_intensity(0..1)`
sets the global multiplier (initial 0.65). `gd.motion_stats()` exposes active counts,
cumulative poses/copy_draws/skipped/ribbon_vertices/resets, not GPU timings.

Histories are native presentation state, cleared and rebuilt on restore/resimulation,
scene change, unload, and entity/costume replacement. Pause/interpolated presents
do not add samples. Hitlag suppresses new pose samples; existing copies age in
logic frames. Ribbons sample once per logic frame, so a frozen anchor degenerates
and fades naturally. KO clearing is opt-in unless the entity changes. APIs are
available online, but online/rollback visual correctness is unverified; `gd.warm`
remains an offline diagnostic.

Aurora must be rebuilt with `_build/patches/aurora-gd-motion-v1.patch`. Held-item
afterimages, fog-range materials and mutable EFB-copy textures are skipped whole.
Arbitrary custom copy WGSL is not exposed. Demos: `demos/afterimages`, `demos/tracers`.
See `_build/tmp/codex-afterimages-tracers-report.md` for caps and unrun acceptance.


### Envoy progression follow-up (2026-10-04)

New hit-rule percent_damage and launch coefficients accept finite signed -1e9..1e9, encoded as 1 + additive raw delta. Sum all matching contributions before final physical caps: outgoing percent .05..64, incoming percent .15..64, launch .05..4. Legacy damage/growth/base/knockback_taken inputs remain .1..4. Tables support32 rules; progression=true identifies the new native capability, while percent_only remains. Provenance retains96 IDs (historical creation plus current attacker/defender). This changes native snapshot/journal layout and requires a rebuild.

Envoy LAB depth <n> [loop] controls future drive/opponent rolls, unlocks4/5/6 slots and1/2/3 keys, and preserves physical drive tiers and existing CPU builds. Selected player keys follow the dial. Invalid downshifts refuse atomically. Opponents use scalar strength and shared weighted rolls; optional foe role is normal, boss or finalboss. See Envoy PLAYTEST.md for exact early/late FD commands.


### Typed fighter armour (2026-10-04 source pass)

`gd.fighter_armor(entity)` returns an array in type order; `entity`1-6 primary,
7-12 secondary. Set one type with `gd.fighter_armor(entity, options)`;
`nil` clears this script's types, `{type='hit_count',clear=true}` clears one.
Writes require an offline active match and gameplay permission; false means
missing fighter or another owner. The older `gd.fighter_armour` remains available.

```lua
gd.fighter_armor(1,{type='damage_threshold',value=8,frames=120})
gd.fighter_armor(1,{type='hit_count',value=3,state=14,from=0,to=20,direction='front'})
function on_armor(e)
  gd.log(e.type..' absorbed='..tostring(e.absorbed)..' broke='..tostring(e.broke))
end
```

Types in evaluation order: `knockback` subtracts value after retail armour and
before its minimum floor; `damage_threshold` absorbs selected-hit damage strictly
below value; `knockback_threshold` absorbs resulting knockback strictly below
value; `super` absorbs ordinary reactions; `hit_count` absorbs N hits, including
the breaking Nth; `damage_pool` absorbs below remaining damage, with equal/crossing
hit breaking through. All eligible types evaluate and both budgets consume even
when another type protects. Threshold equality reacts. Subtraction alone reports
absorbed=false because it promises reduction, not no flinch.

Options: positive value<=1000 (hit_count integer1-255; super defaults1), frames0
persistent or1-36000 logic frames, state-1 any or exact0-65535, inclusive from/to
animation bounds(-1 unbounded or0-100000), direction any/front/back. Read rows:
type,value,remaining,frames,state,from,to,direction,enabled. Disabled broken rows
remain readable until clear/expiry. State gates do not refill budgets on re-entry.

`on_armor(e)` receives port1-6, entity1-12, subfighter boolean, type, absorbed,
broke, selected damage and resulting knockback. One event per eligible type per
selected reaction; copied scalars dispatch after frame, suppressed during resim.
Percent and retail hitlag for both fighters remain. Absorption prevents new launch
and hitstun; existing counters and blastzone deaths remain. Grabs/throws/captures
and ice, sleep, bury, Disable paralysis, Cape and Leadead preserve retail reaction
and do not consume typed budgets. Electric keeps ordinary armour and electric
hitlag. No grab immunity is added. CPUs use the same hooks.

[Armour types demo](../melee/pc/scripts/examples/demos/armor-types/README.md) uses
scripted P2 collision hits; physical attack and native rewind acceptance remain
pending. Authoritative armour records live in game snapshot memory. Geno
per-move integration is proposed separately for the schema owner.


### Fighter gameplay history and echoes (EM5, 2026-10-04 source pass)

`gd.fighter_history_depth()` returns61; `gd.fighter_history(port,age,sub=false)` reads ages0..60 or returns nil before capture. Reads are ungated. Records expose resolved world endpoints/radius and damage/angle/knockback/element for active fighter capsules, state/action-frame/position/facing/grounding and identity/source ownership, including the thrown-body capsule. Six ports and their explicit partners are independent. This game-memory history is separate from presentation pose history.

`gd.echo_add(port,{delay=1..60,sub=false,match={move='nair',element='normal',airborne=true},damage=.4,knockback=1,once_per_move=true})` returns an owned handle; `gd.echo_remove(handle)` removes it. `gd.echoes(port,sub=false)` reads rows and owner/capacity/journal metadata. Eight rules per fighter entity; gameplay writes require the existing offline permission/branch rules. Normal fighter capsules replay at historical world positions, retaining true historical source credit; live hit and each echo have independent target memory. Default once_per_move consumes a target per historical move. False preserves the original per-hitbox/group incarnation semantics. Owner hitlag/rebound is suppressed, while normal target reactions/team/shield/clank and stale-credit paths remain. Articles and projectile hitboxes are not recorded by this fighter carrier.

Deterministic on_frame publication uses `gd.sim_commit(blob,{{op='echoes',port=1,sub=false,rules={...}}})`. This absolute replacement preserves unchanged handles/target memory; empty rules clears the entity. Native canonicalization and duplicate-entity/handle preflight occur before journal allocation or mutation. Use direct echo_add/remove for explicit branched edits, not replayed on_frame state. `gd.echo_supported` identifies the rebuilt capability.

`gd.echo_afterimage(port,{copies=3,spacing=4,echoes={{copy=1,match={move='nair'},damage=.4},{copy=2,match={move='nair'},damage=.4}},visual={...},sub=false})` returns emitter and echo handle array. Delay is always copy index times spacing; conflicting overrides refuse. `presentation_only=true` creates pictures only for rules already published through the journal. Multiple filters may occupy one copy. Existing motion options remain in visual; copies1..12, spacing1..8 and oldest age below60 preserve the current renderer lifetime bound. Standalone collision delay60 is supported; a joint age60 picture needs renderer work.

`gd.afterimage_copy(emitter,index)` reads copy age/armed/element/contact-flash/brightness/tint; `gd.afterimage_copy_set(emitter,index,{brightness=.8,tint={1,.5,.2,1}})` changes owner-scoped unarmed styling. Ordinary afterimage_add emitters are addressable too. These are presentation reads/updates, without gameplay gates. Armed style data is implemented; the renderer integration is explicitly pending in the afterimage lane. Its game-thread snapshot must be copied into the GX FIFO payload, never read game BSS from the render thread.

Envoy LAB: `echo add <delay> [move] [scale]`, `echo clear`. Manual commands publish collision-only rules; the joint demo supplies the matching three pictures. Source fixtures/syntax checks do not establish live shield/clank, rendered alignment or actual LAB zero-byte rewind. Rebuild normal affected translation units and run owner acceptance.
