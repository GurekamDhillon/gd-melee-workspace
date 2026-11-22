# Codex packet P: standalone Geno items, with the Chaos Drive as the first one (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `melee/pc/geno/CLAUDE.md`, `melee/docs/geno.md` (articles: ~2140), `docs/scripting.md`).
Both trees are deliberately dirty: do NOT commit, reset, stash, revert or reformat. Do NOT run `tools/port/build.sh`, do NOT
launch the game. Keep every file compilable at every save. A profiler job and a stage-switch job have just finished in
`gw_script*`, `pc/gameworld/`, `gw_snap.c`, `gw_rollback.c`: read `_build/tmp/codex-profiler-bench-report.md` and
`_build/tmp/codex-stage-switch-report.md`, build on that state, new files where possible, shared-file edits last and small.
HARD RULE: no game-derived data in either repository. The converted Sonic Adventure 2 drive models live outside the repos
in `_build/local-assets/mods/envoy_drives_sa2/` (git-ignored): never copy them into tracked folders, never embed them.
Credit (Sonic Adventure 2: Sega / Sonic Team; tools as listed in that mod's README) is recorded there and in `CREDITS.md`.

## The owner's expectation (verbatim)
"The chaos drives are going to become a M-EX/Geno item right?"
Today the drive is a script pickup (Lua list + `gd.model_spawn` instances): it works (5 of 5 pickups fired in the game), but
it is outside the game's item system, so it has no stage physics, is not in the rollback snapshot, and is offline-only.
A feasibility pass (`_build/audit-20261003/drive-assets/`: its final report is summarised below; `patches/` has the Lua
integration for the script pickup) found: there is NO data-only route. m-ex custom items are PowerPC guest code plus
`MxDt.dat` tables that the vanilla disc does not have; Geno articles are real, snapshotted items but fighter-owned,
projectile-only, single-state, with no floor rest, no touch trigger and no pickup callback (`geno.md` ~2142-2146); Lua has
`gd.items()` read-only and no item spawn besides `gd.spawn_target`. So this is engine work: a Geno-style NATIVE item range,
not the m-ex route (which cannot work on the vanilla disc). Verify these findings before relying on them.

## Build: standalone Geno items (a general capability; the drive is its first user)
1. **A native item kind range for standalone Geno items**, beside `GENO_ART_KIND_BASE` (`melee/pc/geno/geno.h`), dispatched
   in `Item_80267978` (`melee/src/melee/it/item.c` ~549) to a native descriptor and logic table built the way
   `geno_art_build` does (`melee/pc/geno/geno_game_articles.inc`). Numbering must never collide with vanilla, character,
   Pokemon, stage or m-ex custom kinds (>= 237): state the reserved range and why it is safe on mod discs too.
2. **Defined by data**: an item is described in a mod folder (`items/<name>/item.json`, loadable on the vanilla disc from one
   mod folder, same path-containment rules as mission files): physics (gravity, terminal velocity, bounce, friction, floor
   rest, whether it uses stage collision including script/mission collision), lifetime and blink-before-despawn, collection
   rule (`touch` = collected by overlap with a fighter, with a radius and which ports/teams may collect; `grab` = normal
   pickup with A; `none`), whether it can be held/thrown (reuse an existing grounded item's hold/throw states if that comes
   cheaply: say which vanilla item's procs you reused), hurtbox/hitbox none by default, item-cap policy (`hold_kind` choice
   in `Item_802674AC`: state whether these count against the item cap and why), a small per-item payload of script-visible
   values (e.g. colour, amount), and its visual.
3. **Visual without a DAT writer**: draw the item with script model instances bound to the item (a `.gxmesh` asset with its
   material sidecar from a mod folder, positioned from the item's joint/position every frame natively, with spin about the
   vertical axis done properly: instance rotation is Z-only today, so add full 3-axis rotation to scripted model instances
   if that is contained, since a pickup that only squashes in width does not read as spinning), plus optional bob, pulse on
   collect and glow. The binding must follow the item through rollback re-simulation (visual only: no state). An HSD `.dat`
   model path (as Geno articles use) may be accepted too if present, but must not be required.
4. **Lua**: `gd.item_define(path)` / automatic registration from mod folders; `gd.item_spawn(name, x, y, {vx=, vy=, payload})`
   -> handle (gameplay write: refused online for now through the usual gate, forks the LAB timeline; say what full netplay
   support would need now that the item itself is in the snapshot); `gd.items()` rows for these kinds with name and payload;
   `gd.item_despawn(handle)`; events `on_item_collect{item=, name=, port=, x=, y=, payload=}` and `on_item_expire{...}`,
   queued like `on_target_broken`, with the armed-only-when-hooked rule (a past regression: the event queue stayed armed with
   no hook defined; the LAB events test guards it: do not weaken it).
5. **The Chaos Drive as an item**: `melee/pc/scripts/examples/envoy/items/drive/item.json` (data only, tracked: no game data in
   it) with touch collection, floor rest on mission collision, a short pop-up arc on spawn, lifetime with blink, payload
   colour. Its model is looked up by name in the optional asset mod (`envoy_drives_sa2`: `models/drive_<colour>.gxmesh` and
   `drive_glass.gxmesh`), with a plain built-in fallback visual when that mod is absent (a tinted primitive; no art).
   The Envoy mod is tracked Lua that other jobs have been changing: do NOT edit it; deliver the change to `drives.lua` /
   `app.lua` as a diff under `_build/tmp/` that switches drops from the script pickup to `gd.item_spawn("drive", ...)` and
   credits the stat from `on_item_collect`, keeping the script pickup as the fallback when the engine lacks item support.
6. Rollback and LAB: items are in the game's item state, so savestates/rewind restore them; prove with a fixture that a
   spawned item survives a snapshot round trip and that the bound visual follows.
Tests in the suite's pattern (kind dispatch, definition parsing and refusals, physics rest on a fake floor, touch collect
exactly once, expiry, payload, events, the cap policy, cleanup on unload/match end). `melee/docs/geno.md` gets a section for
standalone items with stable numbering (do not change existing section numbers); `docs/scripting.md` gets the Lua API.
Report `_build/tmp/codex-geno-items-report.md`: file:line, the reserved range, what was reused from vanilla items, the cap
policy, unverified items, and a native test plan (spawn five colours, let them fall onto a mission level's floor and a
pass-through platform, collect, expire, 30 on screen, a LAB savestate with items in flight).

## ADDED (owner, 2026-10-03): one item surface for scripts, whichever layer defined the item
The owner pointed out that the m-ex layer is always in the engine. Precisely: it is always compiled in, and it becomes
active when an `MxDt.dat` resolves through the file layer (`gw_mex_ftfunction_runtime.c` ~392: safe when absent, as on the
vanilla disc; a mod folder can supply one). m-ex custom items (kinds >= 237) are table rows in that file plus PowerPC guest
code. Standalone Geno items are the native route and stay the design here, but the two must not be separate worlds:
- `gd.items()`, `gd.item_spawn`, `gd.item_despawn`, `on_item_collect` / `on_item_expire` cover m-ex custom items too whenever
  the m-ex layer is active (spawn by m-ex kind id or name; report which layer an item belongs to), and vanilla items by
  kind where spawning them is safe; state exactly what is supported for each of the three families and what is refused.
- Say in the report what finishing m-ex item support would take (the incomplete itFunction loader noted by the panic near
  `gw_mex_ftfunction_runtime.c:1808`), as a separate, sized item; do not do it in this packet.

## ADDED: three small engine gaps found by Envoy's first run in the game (do these too; each is S, with a test)
1. `gd.data_read` returns nil for a missing file and for an unreadable one alike (`gw_script.c` ~2615): add
   `gd.data_exists(name)` and make `data_read` return `nil, "missing"` versus `nil, "<error>"` without breaking callers that
   only test the first value.
2. A Koopa that is knocked into its shell never produces `on_enemy_defeated` (the mission layer logs it defeated; scripts
   listening for the engine event get nothing). Find the enemy-defeat producer and make every kind's defeat, including the
   shell transition, emit exactly one event; say what "defeated" means per kind.
3. Read-back for script-owned fighter state: `gd.fighter_mod(port)` with no table returns the active multipliers (or nil),
   and a query for active per-draw tints on a port (count and whether any are set), so a test can prove a clean restore.
