# Codex packet I: contact events, polling, wait-until and a debug overlay (2026-10-03)

Workspace `<workspace>`; the game is the separate checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `melee/pc/geno/CLAUDE.md`, `docs/scripting.md`). Both trees are deliberately dirty: do NOT
commit, reset, stash, revert or reformat anything. Do NOT run `tools/port/build.sh` and do NOT launch the game. Keep every file
compilable at every save. Other Codex jobs are editing: two shader jobs (`gw_fx_render.cpp`, `gw_fx.c`, Aurora, new shader
files), a menu job (`gm/gmfrontend*`, `sysdolphin/`). Engine batch 2 (camera params, fighter mods, bench) has just finished in
`gw_script*`, `pc/gameworld/script_*`: build on its result (`_build/tmp/codex-engine-batch2-report.md`), in NEW files where
possible; shared-file edits last, small, after re-reading the file.

## The owner's idea (verbatim, abridged)
"our agents could benefit from logging that mentions X character collided/stood on/ran on/dropped through/jumped through
custom_stage_obj_id ..., with specific offsets on where the fighter was on each thing ... Also the state the fighter was in as
it travelled across/through (or where it didn't) ... maybe let the agent poll for it instead and build a loop around it ... or
create a poll loop til xyz coords + state is achieved." Approved design below; the owner also wants the on-screen debug overlay.

## Foundation that exists
`gd.player(port)` has `on_floor, floor_y, floor_passthrough, wall, ceiling, ledge` (packet A:
`_build/tmp/codex-mission-engine-report.md`, game side `pc/gameworld/script_game.c` ~1755 contact/floor helpers). Scripted
model instances own their collision lines (`gd.model_spawn`, `SCRIPT_MESH_LINES`, the per-instance line arrays); the missions
mod (`melee/pc/scripts/examples/missions/`) places parts from `level.lua` where each part has a name from the Blender scene.

## Build
1. **Identity.** Map a collision line id to its owner: scripted instance handle + line index within the mesh, or "host stage".
   Let scripts attach a label to an instance (`gd.model_label(handle, "Floor_4m.003")` or a field at spawn); the missions mod
   is NOT yours to edit: report the one-line change it needs to pass the level's part names, as a diff in your report.
2. **`gd.contacts(port)`** -> the current picture: for each of floor, left wall, right wall, ceiling, ledge: nil or
   `{owner=handle|"stage", label=, part=, line=, kind=, passthrough=, x0,y0,x1,y1 (the line's world ends), offset= (units along
   the surface from its left/lower end to the contact point), t= (0..1), normal=}`, plus the fighter's `x,y,vx,vy,facing,
   state` (action state NAME via the existing motion-name table, and id), `state_frame`, `jumps_left`, `airborne`.
3. **Events**, emitted only on change, into a ring buffer (capacity stated, oldest dropped, a dropped counter): `land`,
   `leave` (with reason: jumped, ran_off_left/right, dropped_through, knocked), `wall_touch`/`wall_release`, `ceiling_hit`,
   `pass_up_through`, `drop_through`, `ledge_grab`/`ledge_release`, `state_change` (optional, off by default: it is noisy),
   `ko`, `respawn`. Each carries frame, port, the owner/label/line/offset fields above and the fighter fields.
   `gd.contact_events(since_seq)` -> array + next seq; `gd.contact_trace(true|false|{file=, state_changes=})` also appends
   each event as one JSON line to a file in the script data dir (size-capped, rotated once).
4. **Wait-until**, usable from Lua as a non-blocking watcher (the engine calls scripts per frame; nothing may block):
   `gd.wait_until{port=, x=, y=, radius=, state=, on=label_or_handle, airborne=, timeout=}` -> handle;
   `gd.wait_status(handle)` -> `{done=, ok=, frames=, reason=}` where a failure reason is a plain sentence built from the last
   events, e.g. `stopped at wall "Wall_Solid.014" (left side) at x=41.2 after 212 frames`, `fell through "Floor_4m.003"`,
   `never left the ground`, `timeout 600 frames; last on "Ramp.002" offset 3.1`. Console commands for agents:
   `contacts <port>`, `trace on|off`, `trace last [n]` (the last n events as plain sentences), `wait ...` printing the one
   result line when it resolves.
5. **Debug overlay** (owner-approved): a toggle (`gd.contact_overlay(true)`, console `contacts overlay on|off`, and a key or
   LAB menu entry if the LAB has a natural place: do not edit `lab.lua` if it is contested, report the hook instead) drawing
   one compact line per human fighter near the bottom of the safe area (`gd.safe_area`, never a hard-coded 640): e.g.
   `P1 Wait  on Floor_4m.003  2.1 from left (0.32)   wall: -   ceil: -`, and optionally a small marker at the contact point and
   the owning line highlighted. Off by default; zero cost when off.
6. Read-only and offline-safe: nothing here changes game state; say why it is rollback-neutral (derived each frame from
   state, buffer not in the snapshot: state that savestate/rewind therefore clears the buffer and bumps the sequence).

## Tests and docs
Headless tests in the suite's pattern (fake fighter + fake lines): owner mapping, offsets on flat/sloped/vertical lines, each
event's trigger and that steady contact emits nothing, leave reasons, ring overflow, wait-until success and each failure
sentence, overlay text formatting. `docs/scripting.md` section "Contacts and traces" written for an agent that must drive a
fighter through a level: include a worked loop.

## Report
`_build/tmp/codex-contact-events-report.md`: signatures, file:line, the event schema, buffer sizes and cost, the missions-mod
diff, unverified assumptions, and a native test plan (Lua/console snippets and expected lines).
