# Geno Workbench: design (2026-10-09)

Approved in conversation with GD on 2026-10-09. Supersedes nothing.

## Goal

A character tool for Geno fighters, first used to finish imported fighters such as Goku XV2. It must:

- show a fighter exactly as the game does;
- let a person **or an agent (via MCP)** inspect and fix moves: hitbox limbs, clip choice, ground behaviour;
- write the fixes back to the fighter's source and reload it.

Scope v1 is "fix an imported fighter" (option a). The architecture must grow into a general Geno workbench (option c): attributes, states, combo routes, effects, stages, items.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Where the engine runs | The real game exe in a **workbench mode**, driven over a local socket | Fighter code is tied to global game state (gobj, HSD heap, archives, ft tables). The exe is one 32-bit monolith with a fixed-address bridge, so a linkable engine library is a large, risky refactor. The game process gives exact visuals with no drift. |
| Language/UI | **C++17 / Qt 6 Widgets inside the existing launcher** (`tools/release/launcher/qt`) | It already ships on Windows and Linux, has the Atlas look (`atlas.cpp`, `kit.cpp`), uses CMake and CTest, and already launches the game. **No Rust** (owner decision). |
| Command model | One registry of typed, undoable commands. UI, MCP, command palette and CLI are all clients of it | Anything the UI does an agent can do, and the other way round; history and review come for free. |
| MCP | First-class. Every command is an MCP tool. JSON-RPC over stdio (`gd-melee-launcher --mcp`), plus an optional localhost socket while the UI is open | Agents work headless or alongside the owner. |
| Animation authoring | Stays in Blender | Out of scope. |

## Architecture

```
gd-melee-launcher (Qt, C++17)
 |- launcher_core / launcher_ui        existing
 |- workbench_core  (no Qt Widgets; Qt Core/Network only)
 |    |- CommandRegistry   name -> {schema in/out, run, undo}
 |    |- History           undo/redo, author (human|agent), persisted
 |    |- GenoData          read/write fighter source (gameplay.json, moves/*.genoasm, clip map, fidelity ledger)
 |    |- EngineLink        spawn/connect/restart melee-pc --workbench; wb.* calls; JSON + PNG replies
 |    |- Checks            problems: wrong limb, below floor, duplicate clip, grounded clip on aerial, swing without hitbox
 |    |- McpServer         JSON-RPC; tools generated from the registry
 |- workbench_ui
      viewport (engine PNG + overlay toggles, orbit and preset cameras)
      timeline (frame step J/K/L, play, loop, speed; bars for hitbox active, IASA, landing lag)
      outliner (fighter > rows > hitboxes; bone tree)
      inspector (editable values of the selection)
      clip browser, fidelity panel, problems panel, history/review panel, Ctrl+P command palette
```

The launcher gets a **Creator** entry, behind a settings toggle at first.

### Game side: workbench mode (game repo)

- `MELEE_SCENE=mode=workbench` (or `--workbench`):
  - one fighter on an empty floor, no menus or match;
  - logic paused unless stepped;
  - Aurora offscreen frames (`begin_frame/end_frame(offscreen=true)`), with no window unless `MELEE_WB_VISIBLE=1`.
- The transport is the existing console socket (`MELEE_CONSOLE_PORT`; one line in, output then `>>> ok|error`). New Lua/C API `wb.*`:
  - `wb.load(mod_id, costume)`, `wb.row(n)`, `wb.frame(f)`, `wb.step(n)`;
  - `wb.frame_info()`: JSON with bones (world matrices), hitboxes (bone, offset, radius, world pos, active), hurtboxes, ECB, floor, lowest point;
  - `wb.render{camera, overlays, w, h}`: PNG bytes (base64, or a temp path);
  - `wb.reload()`: re-read the fighter's package without restarting.
- Generic for any Geno fighter. Compiled in, but inert unless the mode is set. Never active online, with no change to hashed or rollback state.

## v1 features and their commands

| Area | Commands |
|---|---|
| Open | `open_fighter`, `engine_status`, `engine_restart` |
| View | `render_view`, `set_camera`, `set_overlays` |
| Rows and frames | `list_rows`, `load_row`, `set_frame`, `play`, `frame_info` |
| Hitboxes | `list_hitboxes`, `edit_hitbox` (bone, offset, size, damage, angle, KB, frames), `suggest_hitbox_bone` (limb with the largest displacement and speed at the active frame) |
| Clips | `list_clips`, `preview_clip`, `assign_clip` (row, clip, range), `import_clip` (via the cross-skeleton retarget tool, `ports/ir/tools`) |
| Ground | `set_ground_mode` (hover / anchored / blend, per row, with entry and exit blend) |
| Checks | `run_checks` |
| Save | `save`, `rebuild`, `reload`, `undo`, `redo`, `history`, `propose`, `accept`, `reject` |

Not in v1: attribute, state, combo-route, effect and material editing; stages and items; animation authoring.

## Data safety

- The tool edits **source** only (for an XV2 port: `gameplay.json`, `moves/`, the clip map, the fidelity ledger), then runs the port's build. It never edits built output.
- Each save takes a snapshot first, and history persists.
- External changes are detected (mtime and hash) and offer reload or merge. No silent overwrite.
- Agent edits can come in as **proposals**. The owner accepts or rejects them in the review panel.
- No disc- or XV2-derived data is committed or bundled. MCP and the engine link bind to localhost only.

## Testing

- `workbench_core`: CTest unit tests (registry, undo, GenoData round-trip, checks) on synthetic fighters only.
- Game: a native or scripted test loads a sample fighter, steps frames, and compares `wb.frame_info` hitbox positions with the existing hitbox-position checker.
- MCP: a test client lists the tools, calls each one, and validates the schemas.
- Acceptance, with the owner watching:
  - via MCP only, fix three wrong-limb Goku hitboxes;
  - via MCP only, re-pick Goku's dair;
  - then both show correctly in a normal game run.

## Build order

1. Game workbench mode and `wb.*`.
2. `workbench_core`: registry, history, GenoData.
3. EngineLink, viewport and timeline.
4. Hitbox editing and checks.
5. Clip browser and `assign_clip`.
6. McpServer.
7. Ground modes.
