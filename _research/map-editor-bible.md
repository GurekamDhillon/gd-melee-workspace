# The Map Editor Bible

**Status:** living document. Every change to the map editor cites this file. If a change cannot cite a
section here, either the change is wrong or this file needs a new section first.
**Owner:** GD (workspace) · **Author of record:** the agent session of 2026-09-28 (research lanes L1-L6,
E1-E2; Jev ranking; see §12).
**Scope:** the in-game map editor of the Melee PC port (`pc/scripts/examples/map_editor/`), its
controls, its UI, its data model, and its roadmap.

Read with:
- `_research/menu-kit-pieces.md` — the kit piece conventions this bible assumes (panels, rows, text
  roles, the paragraph widget).
- `_research/map-editing.md` — the stage data survey (map_head / coll_data / general points).
- `_research/widescreen.md` — the safe-area/widescreen plan; the editor's layout depends on it.
- `docs/scripting.md` — the public script API this editor is written against.

---

## §0 How to use this bible

### 0.1 The rule

**Every design decision in the editor names its justification here.** The three justification kinds:

| kind | example |
|---|---|
| a principle | "snap is on by default (§2 P13) because snapping is faster *and* more precise" |
| a pattern | "the palette is a fuzzy-filtered, recency-ordered list (§5.3)" |
| a data fact | "the layout file stores no spawn points (§6.6), so spawns are phase P2" |

If you cannot name one of the three, you are inventing. Stop and add a section to this bible first.

### 0.2 Verification rules (carried from the 2026-09-28 session)

1. **Lua-only changes reload**: copy `main.lua` into the staged lane, `reload map_editor/main` on the
   console port, then `map on` (retry — `gd.fly` refuses while P1 is dead/held/respawning).
2. **Native changes rebuild** (`build.sh`) and need a fresh run; the staged lane is a copy.
3. **Vision is a witness, not a judge.** `python3 /tmp/opencode/see.py <png> "<prompt>"` (or the inline
   DeepSeek-vision call) describes the capture; the model has claimed "no dim veil" when the pixel
   measurement proved a 0.34–0.42 brightness ratio (a 66% veil). Measure before you believe.
   `_build/capture_now.ps1 -TimestampsSec 0 -OutDir <dir>` is the capture convention (PrintWindow);
   the game's own `shot` does not include the overlay.
4. **A capture is not acceptance.** Acceptance is §0.3.

### 0.3 The acceptance tests (what "the menu is not shit" means)

1. **Stranger test** — someone who has never seen the editor can place a floor, select it, move it, and
   save, *without being told which keys to press* (on-screen affordances suffice).
2. **Two-minute test** — a person who knows Blender/Unreal/Unity finds the equivalent binding for
   move/rotate/scale/snap/undo in under two minutes (muscle-memory parity, §2 P6).
3. **Trust test** — after any operation the editor says what happened (§5.9), and nothing is lost
   without a way back (§2 P24, P25).

### 0.4 The artifact trail

- Findings + Jev ranking: `_build/agents/batcha/bible-findings.tsv`, `rank_chunks.md`, `rank_chunks.json`.
- Research lane reports: `_build/agents/batcha/` (session outputs kept in the tool-output store).
- Captures: `_build/agents/batcha/ui-cap*/now00.png`.

---

## §1 Product definition

### 1.1 Who this editor is for

| persona | wants | must not be blocked by |
|---|---|---|
| **Builder (casual)** | assemble a playable room in minutes; save it; play it | keybind memorisation, jargon, invisible state |
| **Competitive / hacker** | move spawns, shrink/extend camera and blast bounds, verify quickly | the editor refusing because it only edits "parts" |
| **Modder** | ship a map inside a mod, with its models, reproducibly | hidden scale/units assumptions, silent save failures |

### 1.2 Goals

- Assemble, edit, and persist a stage from kit parts, inside a live match, with a controller or a mouse.
- Make the authoring loop *tight*: edit → play the change in seconds, never via a rebuild (§2 P29).
- Make every operation legible: what will happen (preview), what happened (status/toast), how to undo.
- Own the gap the Melee tooling ecosystem left: **no maintained Melee tool edits collision, spawns and
  camera visually** (the BrawlBox role). Stage 1 of that gap is parts + spawns/bounds browsing.

### 1.3 Non-goals (for now, and why)

- **Unlimited worlds / streaming.** The engine has 64 areas and an instance pool of 256 (§6.5); the
  editor is an assembly tool, and pretending otherwise produced the "large map" side-quest. Revisit
  only if a map needs it.
- **Editing the host stage's native `coll_data`.** The editor appends scripted collision lines; it does
  not rewrite `Gr*.dat`. That is a different, higher-risk feature (round-trip + budget enforcement).
- **Rollback/online maps.** The manifest is deliberately not rollback-safe.

### 1.4 Success criteria

The three tests in §0.3 plus: a saved layout reloads byte-identical (§6.6), and the editor never
exceeds a documented engine limit without saying so first (§5.9, §6.5).

---

## §2 Principles

Nineteen principles, each with its source and its consequence for this editor. Ordered by the Jev
ranking's emphasis bands (§12).

### A. The core loop and the tool

**P1 — Immediate visual feedback is the single most critical editor property.** If you must
rebuild/relaunch to see a change, nobody iterates in the editor; every other principle serves this one.
*Source: Flukz devlog, "Level Editors in Games" (2026).* → The editor draws over the live match and
applies edits to live instances on the next tick; no save/restart loop.

**P2 — Keep the designers in the zone: count the cost of every action.** Storm measured the same brush
primitive at 2 clicks + 1 drag + 1 key in Hammer vs 2 clicks + 1 drag + 3 typed values + 2 keys in
Unreal; across 10,000 brushes that is ~30,000 actions and roughly a third of the time. *Source:
Robin-Yann Storm, "Keeping Level Designers in the Zone Through Level Editor Design", GDC 2016.* → Every
tool must be one gesture + one confirm; the action menu must never be the *only* path to a common edit.

**P3 — Blame the tool, not the user.** If a builder repeatedly does the wrong thing, the tool is at
fault. *Source: Storm, GDC 2016 (transcript).* → Repeated misplacements mean the preview/snap is wrong,
not that the user is clumsy; fix the affordance.

**P4 — Cut features to keep the editor usable.** Deliberately dropping advanced features (Zucconi
skipped elliptical orbits, comets, destructible planets in the 0RBITALIS editor) is what keeps an
editor intuitive; unused complexity is a cost, not a feature. *Source: Alan Zucconi, "The UGC Dilemma:
post-mortem of a level editor" (2015).* → §1.3 is a feature list we defend on purpose.

### B. Controls and manipulation

**P5 — Edit in the medium you are designing for.** Duske shipped TrenchBroom with only a 3D view for
years because 2D orthographic views force designers to think in 2D; the editor should default to the
view the player sees. *Source: Kristian Duske, ModDB interview (2018).* → the editor is
first-person/camera-space by default; orthographic/2D views are a later precision aid, not the default.

**P6 — Match existing muscle memory where you can, and teach where you cannot.** A person arrives with
Unreal/Unity/Maya *or* Blender habits. The reserved keys (§4.1) break both canonical clusters, so the
editor must (a) pick the least-surprising substitutions and (b) show the mapping on screen (HUD hint +
F1 help). *Source: L1/L5 cross-editor analysis; Blender default keymap; Unity hotkeys.* → §4.3.

**P7 — Direct manipulation beats indirection, but keep a gizmo for rotation.** TrenchBroom avoids
handles where possible (drag geometry as if with your hands) and keeps a handle for rotation because
it is the exception. *Source: Duske, ModDB interview.* → dragging geometry directly is the primary
verb; the rotate handle is the accepted exception.

**P8 — Snapping beats no snapping on precision *and* speed; make it default.** Oh Snap measured ~40%
improvement over no snapping; Snap-and-go 138% (1D) / 231% (2D) faster alignment. *Sources: Oh Snap
(UBC 2011), Snap-and-go (CHI 2005).* → snap on by default; `G` toggles; `Ctrl` is momentary snap.

**P9 — Snapping must not create dead zones.** Traditional snapping makes positions *near* the snap line
unreachable unless you toggle it off; the fix is mode-free snapping (Snap-and-go / Oh Snap) or modifier
override. *Sources: Snap-and-go (CHI 2005); Oh Snap (UBC 2011).* → `Ctrl` (hold) disables snap for the
gesture; the tool must allow near-snap placement.

**P10 — Snap to the perceived centre, not the bounding box.** For asymmetric shapes the centroid is
measurably closer to user intent (shape-dependent snapping). *Source: Heo et al. (KAIST), shape
dependent snapping.* → selection/frames use the part origin and the part's own notion of centre; do not
invent a bbox centre for asymmetric parts.

**P11 — No single camera metaphor wins; offer both.** Ware & Osborne found scene-in-hand best for
manipulating an object and flying best for navigating interiors; there is no universal winner. *Source:
Ware & Osborne, I3D 1990.* → the editor keeps the fly camera (navigation) and frames/orbits around the
selection (manipulation, §4.4).

**P12 — Scale camera speed with depth, and map velocity non-linearly.** Users hold constant velocity
relative to local scale; depth-modulated flying and cubic velocity mapping give fine control and fast
travel in one gesture. *Sources: Ware & Fleet (I3D 1997); Ware & Osborne (1990).* → `gd.fly_speed`
already exists; the editor exposes a speed control and uses Shift=fast; add depth awareness when the
camera system is next touched.

**P13 — Camera collision is correctness.** An orbit that lets the camera clip through geometry
disorients (SHOCam's contribution). *Source: SHOCam, 2015.* → blocking geometry must stop the camera's
descent into floors when the editor next touches the camera; until then, frame-on-selection is the
escape hatch.

### C. Safety, discovery and honesty

**P14 — Error prevention beats error messages.** Distinguish slips (fix with constraints/defaults) from
mistakes (fix by removing memory burdens and supporting undo/confirmation). *Source: Nielsen, 10
Usability Heuristics, #5.* → destructive actions are guarded by confirmation *and* undo (§5.6, §5.9).

**P15 — Confirmation only for serious, irreversible actions, with specific text and no default "yes".**
Overused confirmations become noise; restate the concrete consequence. *Source: NN/g, "Confirmation
Dialogs Can Prevent User Errors" (2018).* → confirmations for Delete/Clear only, and the message names
the object and the count.

**P16 — Undo is a user intention, not a system command.** Support backward *and* forward recovery
(history traces, soft delete), and treat undo as the thing that makes experimentation safe. *Source:
Abowd & Dix, "Giving Undo Attention" (1992); Nielsen heuristic #3.* → every mutation is undoable and
named (§5.6); §9's status bar shows the last action.

**P17 — Undo is named and grouped; a drag is one step.** Unity records per-object deltas, splits groups
on mouse-down and names every group; Blender adds an Undo History list. *Sources: Unity Undo API;
Blender Undo & Redo manual.* → the editor's clone-snapshot history already coalesces by operation; the
status bar must name the last action ("Undo Move") and the action menu must expose the history.

**P18 — Progressive disclosure: show few, disclose on demand, cap at two levels, split by frequency.**
Hidden features need a labelled path back or they become "discoverability debt". *Sources: Nielsen,
"Progressive Disclosure"; Microsoft progressive-disclosure guidance.* → the panel shows tools + the
current task's rows; advanced ops live behind the action menu (`F2`/RMB) and the Help page, and both are
visible entry points.

**P19 — Immediate feedback, honest save, tight loop.** A save that silently drops changes is the worst
failure mode in the community's own history (the coll_data "PRESS SAVE" all-caps warning). *Sources:
TDRR stage-import guide (2020); Flukz devlog.* → save verifies read-back (§6.6) and reports the byte
count; nothing is silent.

**P20 — Label everything; vanilla Melee data is unlabelled.** Historically modders found node meaning by
trial and error, changing a value and reloading in Dolphin; naming points and collision groups is the
single most-demanded feature. *Source: SmashBoards stage-hacking thread.* → §6.2's point table is the
naming scheme, and the editor's property grid must show a point's *name* ("P1 spawn"), never a raw type
id.

**P21 — Previews must equal what the commit produces.** Tiled: "previews mean that when you click/commit,
that's what you'll get"; a preview that diverges is worse than none. *Source: Tiled issue #3890.* →
ghost/placement previews are phase P1 (§5.8) and must be validated before they ship.

**P22 — Show severity properly: transient toasts for confirmation, a status bar for state, a panel for
errors.** Never auto-dismiss errors. *Sources: imgui-notify; Dear ImGui demo console.* → §5.9.

**P23 — Selection follows a modifier matrix: Shift=add, Ctrl=toggle/subtract, marquee=box.** Local vs
world space is offered only where meaningful (not for scale). *Sources: Tiled editing; Dear ImGui
multi-select; ImGuizmo README.* → §5.4.

**P24 — Name and group every mutation; make selection reversible.** (Folded into P16/P17; kept as the
checklist item for code review.)

### D. What the audience expects (Smash-specific)

**P25 — Own the gap the Melee ecosystem left.** No maintained Melee tool does visual collision + spawn +
camera editing (BrawlBox does it for Brawl; HSDRaw Viewer is the closest Melee analogue). *Sources: L3
tool survey; `_research/map-editing.md` §5.* → the editor's phase P2 is spawns/camera/blast, because
that is the unmet demand.

**P26 — Match the BrawlBox mental model for spawns and bounds.** Modders expect named `StgPosition`
bones for player/rebirth spawns and `CamLimit`/`Dead` boxes; the Melee equivalent is typed general
points (ids 0–7, 127–146, 148–152). *Source: BrawlBox/Project-M workflows (KC-MM).* → §6.2.

**P27 — Distance from the two classic failure modes:** *collision ≠ model* (moving a platform's visual
does not move static collision) and *nothing is labelled*. *Sources: stage-hacking thread; pain-point
list §6.7.* → the editor draws the collision overlay with the model and names groups.

---

## §3 Canonical controls (the evidence base)

Condensed from L1 (official docs). This is the reference the scheme in §4 is derived from; it is not
the scheme.

### 3.1 Per-editor navigation

| editor | orbit | pan | zoom | fly | frame |
|---|---|---|---|---|---|
| **Unreal** | Alt+LMB | Alt+MMB | Alt+RMB / wheel | RMB + WASD/QE | `F` |
| **Unity** | Alt+LMB | MMB | wheel / Alt+RMB | RMB + WASD/QE, Shift fast | `F` (Shift+F locks) |
| **Godot** | MMB | Shift+MMB | wheel | RMB + WASD/QE, Shift fast / Alt slow | `F` (`O` origin) |
| **Blender** | MMB | Shift+MMB | wheel / Ctrl+MMB | Shift+F (walk/fly) | Numpad `.` (Home = all) |
| **Hammer (S1)** | Space+LMB drag | Space+RMB drag | wheel / +- / 1-9 | `Z` then WASD | PgUp/PgDn cameras |
| **TrenchBroom** | Alt+RMB (community) | MMB | wheel (with RMB) | **RMB look + WASD/QX up-down** | Ctrl+U |
| **Tiled** | — (2D) | MMB / Space | Ctrl+wheel / `Ctrl±` | — | `Ctrl+/` |
| **Radiant** | RMB drag | RMB drag (2D) | wheel | arrows + look keys | `END` |

### 3.2 Per-editor tool keys and modifiers

| editor | move | rotate | scale | select | local/world | precision | snap (hold) | pivot |
|---|---|---|---|---|---|---|---|---|
| **Unreal** | W | E | R | Q (view) | Ctrl+` | — | — | Alt+End |
| **Unity** | W | E | R | Q | Shift (screen) | — | Ctrl/Cmd | Z (pivot) / X |
| **Godot** | W | E | R | Q | T | — | Ctrl | — |
| **Blender** | G | R | S | B (box) / C (circle) | orientation menu | **Shift** | **Ctrl** | `.` pie |
| **Maya** | W | E | R | Q | — | — | — | — |
| **Tiled** | (brush B) | — | — | R (rect) / W (wand) | — | — | Ctrl | — |
| **Radiant** | W | R | (q=resize) | — | — | — | — | — |

### 3.3 The consensus and the two divergences

- **Consensus:** RMB-look + WASD fly (Unreal/Unity/Godot/TrenchBroom); wheel zoom; Shift=fast/finer;
  Ctrl=snap; `F` = frame (Unreal/Unity/Godot); RGB axis mapping; a plane-lock on the gizmo.
- **Divergence 1 — tool letters:** Unity/Unreal/Maya use **W E R**; Blender uses **G R S**. They agree
  on `E` for rotate and nothing else.
- **Divergence 2 — precision polarity:** Blender/Unity use Ctrl = *snap/coarser*; Dear ImGui uses
  Ctrl = *finer* (1/10). **Decision: follow Blender/Unity** (§4.5) — Ctrl = snap, Shift = finer.
- **`R` is the most contested key in 3D tooling** (rotate in Blender/Radiant/TrenchBroom; scale in
  Unreal/Unity/Maya). Our editor already gives `R` to discrete rotate, siding with Blender/Radiant.

---

## §4 The control scheme

### 4.1 Reserved keys (fixed; the scheme must route around them)

| binding | action | why fixed |
|---|---|---|
| `W A S D` | fly | the fly camera is the port's debug flight, already shipped and taught |
| `F1`–`F6` | scene toggles | existing port hotkeys (help, menu, overlay, …) |
| `Tab` | menu | existing kit menu key |
| `X` `Y` | select / move chords | existing editor chords (pad muscle memory) |
| `R` `L` | discrete rotate ± | existing rotate pair; `R` therefore cannot be scale |

Consequences (from L5): move cannot be `W`; scale cannot be `S` (fly) or `R` (rotate); `F3` (Blender
search) is inside `F1–F6`; `X`/`Y` axis-lock is unavailable. Therefore **move = `G`, scale = `C`,
continuous rotate = `E`, search = `Space`, axis-lock = arrow keys.**

### 4.2 The three candidate schemes (L5)

| | (i) Blender-like modal | (ii) Maya-like immediate | **(iii) Hybrid (recommended)** |
|---|---|---|---|
| model | press key → drag → LMB confirm / Esc cancel | always-on gizmo, switch tools, click handles | immediate by default; **hold** a transform key = one-shot modal |
| best for | keyboard-first precision users | mouse-first users; **gamepad** | everyone; one key set |
| move/rotate/scale | `G` / `E` / `C` | `G` / `E` / `C` | `G` / `E` / `C` |
| cost | loses Blender's literal `R`/`S` | non-mnemonic `G`/`C` | must document tap-vs-hold |

### 4.3 The recommended scheme (hybrid) — authoritative key table

| key | action |
|---|---|
| `Q` | select tool |
| `G` | move — tap = switch tool; **hold+drag = modal move** |
| `E` | rotate — tap = switch; hold+drag = modal (snaps to 15° when snap on) |
| `C` | scale — tap = switch; hold+drag = modal |
| `1`–`5` | tool shortcuts (place, select, move, rotate, scale) |
| `F` | **frame selection** (sets the orbit pivot, §4.4) |
| `V` (hold) | vertex/nearest-point snap |
| `Shift` (hold) | precision / slow fly |
| `Ctrl` (hold) | snap to grid while dragging; toggles snap when tapped with `G`? **No — `G` alone toggles snap** |
| `End` | snap selection to floor (`y` = nearest collision below) |
| `↑ ↓ ← →` | during a modal transform: lock to X / Y / Z world axes |
| Numpad `1 3 7 5 0 .` | front / right / top view, ortho toggle, camera view, frame (optional, §4.6) |
| `Space` | command palette / search (replaces `F3`) |
| `Z` | pivot mode toggle (origin / median) |
| `M` | move selection to cursor (existing) |
| `I` | place at cursor (existing Insert, kept) |
| `Del` | delete (confirm, §5.6) |
| `Ctrl+Z` / `Ctrl+Y` | undo / redo (named, §5.6) |
| `Ctrl+D` | duplicate at cursor (existing) |
| `Ctrl+S` / `Ctrl+O` | save / load (save verifies, §6.6) |
| `F1` / `H` | help (existing) |
| `F4` | palette filter: type a name, Enter done, ESC clears (`map filter <text>` scripts/tests) |
| `F2` / RMB | action menu (existing) |
| `F3` | collision overlay (existing) |
| `F6` | start / exit editor (existing) |
| `PgUp`/`PgDn`, wheel | depth (existing) |
| `C` conflict note | `C` was "move constraint free/X/Y". That moves to **`Shift+↑/↓`** or the action menu; document it. |

### 4.4 Camera and framing

- **Fly** (navigation): `WASD` + `Shift` fast, existing port flight. Speed is shown in the status bar
  and adjustable (`gd.fly_speed`).
- **Frame** (manipulation): `F` projects the selection and sets the orbit pivot; the port's fly camera
  then looks at the selection (implement as a camera-interest override). Rationale: §2 P11 — focus is
  the bridge into orbiting; Unreal explicitly couples `F` to tumbling around the selection.
- **Depth cue**: the status bar shows `z` and the grid; the cursor cross shows the snapped origin
  (§9.2). Camera collision (§2 P13) is deferred but noted.

### 4.5 Modifier polarity (decided)

| modifier | meaning | rationale |
|---|---|---|
| `Shift` (hold) | precision: 1/4 grid step; slower fly; finer rotate | Blender/Unity convention; also Godot's "slow" |
| `Ctrl` (hold) | snap hard to the grid (ignore sub-steps) | Blender/Unity convention |
| `Ctrl` tap on `G` | *(no)* — `G` **toggles** snap, because a toggle is what the current editor teaches | keep one toggle, one modifier |

Document this explicitly in F1 help: *"Ctrl = snap, Shift = fine (Blender/Unity polarity; ImGui-style
Ctrl=finer is deliberately not used)."*

### 4.6 Widescreen and view presets

The editor draws in the overlay's 640×480 space (§6.4). Numpad view presets are optional and cost
nothing to skip on tenkeyless keyboards; the fly camera covers the need. Revisit after the safe-area
work (`_research/widescreen.md`).

### 4.7 Gamepad scheme (from L2/L5, Forge as the model)

| pad | action | keyboard parallel |
|---|---|---|
| Left stick | fly | `WASD` |
| Right stick | look / orbit | RMB drag |
| `LT` (hold) | **move gizmo / modal move** | `G` hold |
| `RT` (hold) | **rotate gizmo** | `E` hold |
| `LT+RT` | **scale gizmo** (Halo Infinite's chord) | `C` hold |
| `LB` (hold) | snap | `Ctrl` hold |
| `RB` (hold) | precision / slow | `Shift` hold |
| `A` | place / grab | `I` / LMB |
| `X` | select nearest | `Tab` |
| `Y` | move to cursor | `M` |
| `B` | duplicate | `Ctrl+D` |
| D-pad `←`/`→` | rotate ±15° | `R` / `L` |
| D-pad `↑`/`↓` | depth step | `PgUp`/`PgDn` |
| `↑` D-pad (hold) | play/edit toggle | `F6` |
| `Start` | action menu (radial, pad-native) | `F2` |
| `Back` | help | `F1` |

Rules (from L2's lessons): hold-to-modify (not toggles) for snap/precision so cross-input muscle memory
matches; the radial/action menu is the pad's object browser; keep a bounded palette (hotbar-like);
face-button `X`/`Y` are a different namespace from keyboard `X`/`Y` — say "button X" in the help.

---

## §5 Interaction patterns (what to build, and why)

Each pattern names its source (L4 unless noted) and this editor's status. **P0 = this pass; P1/P2/P3 =
§8 roadmap.**

### 5.1 Input routing — the single choke point

**Rule:** one place decides whether the editor or the game consumes input, and the UI gets first
refusal (Dear ImGui's `WantCaptureMouse`/`WantCaptureKeyboard` pattern; always forward, then filter).
**Our situation:** the port's keyboard is hotkeys-only and `gd.key`/`gd.key_pressed` are polled only
while the window is focused, the console is closed and nothing is being typed; `gd.pad(1)` reads what
the game read. **P0:** the editor already gates on `editing`; make the gate explicit in one function and
document that while editing the *keyboard* drives the editor while the *pad* still plays (by design —
do not override pads for a UI, §4.7 uses them read-only).

### 5.2 Scrub fields (numbers you drag)

**Pattern:** drag the label to scrub, click the box to type; a drag deadzone so a click still types;
`Esc` during a drag reverts to the start value; Ctrl/Shift modify the step (Blender fields; Unity
`FieldMouseDragger`/`DragNumberValue`). **Polarity:** Blender/Unity = Ctrl coarser, Shift finer (§4.5);
document it.
**Done 2026-09-28:** inspector `x/y/z/rot/scale` rows scrub on drag (3px deadzone, `Shift` quarters the
step, `Ctrl` hard-snaps) and open **typed entry** on a plain click (digits, `.`, `-`, Backspace, Enter
applies one undo step, ESC cancels). `map set <field> <value>` mirrors it for scripts and tests.
`gd.key` gained the OEM names (`PERIOD`, `MINUS`, `PLUS`, `COMMA`, `SLASH`, `SEMICOLON`, `GRAVE`,
`LBRACKET`, `RBRACKET`, `BACKSLASH`, `QUOTE`).
**Remaining:** a native `gd.kit.field` widget (the Lua row is sufficient today).

### 5.3 Palette browsing and search

**Pattern:** a *bounded* selection surface (Minecraft's 9-slot hotbar; SMM2's radial wheel) plus fuzzy
search that **filters** but does not reorder — VS Code orders its palette by recency and category
because unstable ordering is unlearnable (L4). **Our situation:** 21 parts in a linear Up/Down list, no
search, no recents. **P1:** fuzzy filter, "recent" section pinned at top, category grouping
(floor/wall/trim/glass/stair), and the pad gets a radial (LB/RB category, stick pick).

### 5.4 Multi-select

**Pattern:** Shift = add, Ctrl = toggle/subtract, marquee = box select (Tiled), with the ImGui
multi-select semantics (box-select needs spacing to aim at empty space; `ClearOnClickVoid` decides
whether clicking the void clears). Local vs world only where meaningful — ImGuizmo hides it for scale.
**Our situation:** single selection only; pick is nearest-origin (§7.4). **P2:** box select + grouped
transform (the model API supports per-instance `set`; a multi-drag must be one undo step, §5.6).

### 5.5 Duplicate / copy / paste / arrays

**Pattern:** duplicate is *immediate + enter move mode* (Blender `Shift+D`), linked duplication is a
separate verb (`Alt+D`), per-field value copy/paste is `Ctrl+C/V`, and a repeat/array count is the
power-user form of duplicate. **Done 2026-09-28:** `map duplicate <n>` (and the "Duplicate x4 at cursor" action row) copies the
selection **N times** spaced one grid step along X as **one undo step**; `Ctrl+D` stays a single
duplicate at the cursor. **Remaining:** enter move mode after a duplicate, and a small copy stack for
part settings.

### 5.6 Undo / redo

**Pattern:** named, grouped, coalesced (Unity: per-object deltas, groups split on mouse-down,
`SetCurrentGroupName`; Blender: Undo History list). **Our situation:** 64 clone-snapshot steps, unnamed,
no history UI; a failed op never advances history (§7.7 — already correct). **Done 2026-09-28:** every
mutation is **named** through `acted()`/`name_undo()` (`undo_names` tracks the stack), the status bar
shows the last action, and `map log on` opens an **Action Log** overlay listing the last named steps —
**click a row to step back** (`map history <n>` does the same from a script). **Done:** the Action Log also lists the **redo branch** (rows prefixed `redo:`, click one to step
forward); `map redo <n>` mirrors `map history <n>` for scripts. The undo stack now snapshots the
**whole document** (`{parts, bounds, spawns}`) and `history` re-applies the live stage effects on
restore, so bounds and spawn edits are undoable like part edits; savestates carry bounds/spawns beside
parts. **Remaining:** a per-part copy stack (§5.5).

### 5.7 Property grid

**Pattern:** data-driven, foldout sections, reset-to-default per field, per-field copy/paste (Dear ImGui
property editor demo; Unity Inspector revert; Blender Ctrl+C/V). **Our situation:** no inspector at all
— the selected part is only a cyan square. **Done 2026-09-28:** a right-hand SELECTION panel shows
`part`, `x/y/z`, `rot`, `scale`, `collision`, `floor_flags`; the numeric rows scrub and type (§5.2),
`collision`/`floor flags` click to change. **Remaining:** `layer`/`tint`, and moving the `New …`
defaults from the action menu into a "New parts" section here.

### 5.8 Ghost previews and validation

**Pattern:** the ghost is translucent *real geometry* (not a bbox), tinted green/red by validity
(`0x22c55e`/`0xef4444`), `depthWrite`/raycast off, and **always visible** while the tool is armed
(Tiled issue #3890; pascalorg ghost-materials). **Rule:** preview == commit; validate before shipping.
**Our situation:** place shows only the cursor cross. **P1:** a ghost instance following the snapped
cursor (the model API can spawn a temporary instance with `alpha`, then despawn it on place/cancel —
free, since the pool is 256 and the editor caps at 128).

### 5.9 Status, toasts, errors

**Pattern:** transient toasts for confirmation (severity: success/warning/error/info; **never
auto-dismiss errors**), a persistent status bar for mode/selection, a console panel for stackable
errors (imgui-notify; ImGui demo console). **Our situation:** one status string in the bottom bar, no
severity, no toasts, and errors are printed into the same line as the mode text. **P0:** split the
bottom bar into `mode | hint | state` and give errors their own persistent line/colour (`danger` from
the kit palette). **P1:** toasts at the top-right for save/load/duplicate; errors stay until dismissed.

### 5.10 Help

**Pattern:** a searchable command/help surface; the two-layer model (exposed ops vs all ops, Blender
F3). **Our situation:** the P0 help overlay is a single-column, scrollable, opaque, dimmed modal
(verified: no bleed-through; proportional scrollbar). **Done 2026-09-28:** `Space` opens a **live action
search** — type to filter every action, Up/Down to pick, Enter runs the highlighted one, ESC closes;
`map search [text]` opens it from a script and `map run <text>` runs the best match. F1 remains the
keybind reference. **Remaining:** search the help *rows* too, and a palette-driven search.

### 5.11 Discoverability of the scheme

The reserved-key conflict (§4.1) means the scheme is *unusual*, so the editor must teach it: the bottom
bar's hint line names the current tool's primary gesture and its modifier, and F1 shows the full table
with the `G/E/C` substitutions called out. (§2 P6.)

### 5.12 On-object gizmos (the primary manipulation path)

**Principle:** direct manipulation first (§2 P7) — the selected part carries its own handles rather than
requiring a modal key. **Done 2026-09-28:** the selection draws **red = move X**, **green = move Y**,
**cyan = scale** (uniform), and a **gold rotation ring**, all in screen space from the projected axes
(so they follow the camera and widescreen). Pressing a handle starts the *same* modal transform the keys
use (`modal_begin(mode, ax, 'mouse')`); the pointer drives it, release commits, a drag is one undo step.
Panels take precedence over handles (a press is tested against the panels first), and the handles only
exist while a part is selected.
**Remaining:** a hover highlight + cursor change over a handle, per-axis scale tips, and rotation
out-of-plane (the ring is the in-plane rotate the engine supports).

---

## §6 The data model

### 6.1 What a map is in this port

A flat, versioned **parts list** with absolute transforms, saved as a sandboxed Lua data file.

```lua
return {version=1, units=6.5, parts={
  {part="bf_floor_4m", x=0, y=40, z=0, rot=0, collision=true, floor_flags=2},
  -- scale / scale_x / scale_y / scale_z are written only when != 1
}}
```

| fact | detail |
|---|---|
| version | must equal 1 |
| units | must equal 6.5 (kit metres); a mismatch is the "re-export" error |
| parts | dense list, `#parts <= MAX_PARTS` (editor cap 128; engine 256 — §6.5) |
| coordinates | `x,y` = the fighter plane; `z` = **visual depth only** (never collision) |
| rot | degrees, −360..360; per-model, not collision |
| collision | boolean; per-part sidecar collision lines (XY, z=0) |
| floor_flags | 0..3; bit 1 = drop-through, bit 2 = ledges |
| file | `scripts-data/map_editor_main/<name>.lua`, ≤ 1 MB, `.bak` kept |

**Absent by design (phase P2+):** stage id, spawns, camera/bounds, tint/layer/visible/alpha, custom
collision geometry, model assets (only the *name* is saved — the recipient ships matching models).

### 6.2 What a Melee stage is (the model we are growing into)

A stage is **two coordinated graphs**:

1. **`map_head`** — model groups (JObj/DObj/PObj), animations, fog/light lists, **general points**
   (typed JObjs), splines, and the `GrJoint` links that bind collision groups to JObjs (moving
   collision). 
2. **`coll_data`** — the 2D collision graph: vertices, **directed** lines (floor/ceiling/left/right
   wall), line ranges, and collision joints.

Editing one never edits the other: **moving a platform's visual does not move its static collision**
(the community's #1 confusion, §6.7). Our port's runtime model API sidesteps this by *attaching*
collision lines to instances (they move together) — a deliberate improvement over the vanilla model,
and the reason the editor should say "collision follows this part" in the property grid.

### 6.3 General points — the naming scheme (§2 P20/P26)

| ids | meaning | editor name (P2) |
|---|---|---|
| 0–3 | player starts | `P1 spawn`, … |
| 4–7 | respawns | `P1 respawn`, … |
| 127–146 | item spawns | `item spawn` |
| 148–150 (`0x94–0x96`) | camera configuration | `camera` |
| 151–152 (`0x97–0x98`) | blast bounds | `blast` |
| 199+ | target-test targets | `target` |
| 252+ | bumpers | `bumper` |

Vanilla data is unlabelled; naming is the feature. In Melee these are JObjs inside `map_head`; the
Brawl equivalent (`StgPosition` bones, `Player0-3E/N`, `Rebirth0-3E/N`, `CamLimit0N/1N`, `Dead0N/1N`)
is the mental model modders already have (§2 P26).

**Editable since 2026-09-28:** `gd.stage_set_spawn(slot, x, y)` moves a **start** (0–3) or **respawn**
(4–7) point by writing the point JObj's translate (the same value `Ground_801C2D24` reads at spawn),
owner-guarded and restored by `gd.stage_restore_bounds()`; `gd.stage_spawn(slot)` reads it back. The map
editor exposes it as `map spawn <0-7> [x y]`. **Verified live:** moving slot 4 to `x=-100` made P1
respawn at `x=-100` after a KO. **Spawns are saved in layout v2** (`spawn={[slot]={x=…,y=…}, …}`) and
re-applied on load — the move/save/move-away/load cycle was verified live.

### 6.4 The stage filenames (and the corrections)

| file | stage |
|---|---|
| `GrNBa.dat` | Battlefield |
| `GrNLa.dat` | Final Destination |
| `GrNPo.dat` | Push-On (Multi-Man Melee arena) |
| `GrNKr/NSr/NZr/NBr/NFg` | Adventure routes (Mushroom Kingdom, Underground Maze, Brinstar escape, Big Blue, Figure Get) |
| `GrSt/Cs/Rc/Kg/Gd/Gb/Sh/Ze/Kr/Yt/Iz/Gr/Cn/Ve/Ps1-4/Pu/Mc/Bb/Ot/Fs/Im/I1/I2/Fz/Op/Oy/Ok/He` | the VS/tournament + single-player stages (Yoshi's Story, Peach's Castle, … Pokémon Stadium's four transformations, … All-Star Rest) |
| `GrT*.dat` | per-character Target Test |

**Corrections:** `GrNCP` and `GrGround` **do not exist**. Collision is `coll_data`; stage parameters
are the `grGroundParam` symbol (a `GroundParam` struct, whose `0x4C` byte is the fixed-camera flag);
`ground.c` is the loader module. Do not repeat the folklore names.

### 6.5 Limits (with the doc-vs-code discrepancies — verify in the exe)

| limit | code | docs/editor say | note |
|---|---|---|---|
| model instances | **256** (`SCRIPT_MESH_INSTANCES`) | 128 (`MAX_PARTS` / README) | editor self-limits below the engine ceiling |
| scene-pinned assets | 32 (`SCRIPT_MESH_ASSETS`) | 32 | asset cache; 64 MiB budget |
| collision lines / sidecar | 32 (`SCRIPT_MESH_LINES`) | 32 | per model |
| total scripted collision lines | **768** (`SCRIPT_STAGE_LINES`, largemap) | "up to 200" | the 200 figure is the legacy `stage_add_line` pool |
| mpLib collision | 2048 verts / 1536 lines / 256 joints | "256 joints" | base joints are counted against |
| areas | 64 | not used | streaming; out of scope |
| undo | 64 | 64 | clone snapshots |
| coords | ±100000 | ±100000 | |
| scale | 0.001..100 (negative mirrors) | UI clamps 0.25..4 | |
| layer | −8..8 | not exposed | |
| data file | ≤ 1 MB | ≤ 1 MB | |

Per the workspace's own trap #1, treat every row as "verify against the built exe" before quoting it in
a release note.

### 6.6 Save / load

- `save(name)` → serialize → `gd.data_write` (keeps `<name>.bak`) → **read-back verification**: the
  written text is re-read and compared; a mismatch is an error (§2 P19). The status reports the result.
- `load_map(name)` → `gd.data_read` → `load(text, '@name', 't', {})` with an **empty environment** (no
  `gd`, no `io`, no globals) → `validate()` (schema, palette membership, ranges, units) → `apply()`.
- `map play <file>` sets the session autoload; it is **not** persisted across relaunch (by design).
- **Layout v2 (done 2026-09-28):** when the map carries stage bounds, `serialize` writes `version=2`
  plus `camera={left,right,top,bottom}` and/or `blast={...}`; `validate` still accepts v1 and checks v2
  bounds (`left < right`, `bottom < top`). Loading v2 applies them through `gd.stage_set_camera_bounds`
  / `gd.stage_set_blast_bounds`, and says so if the stage refuses. `map bounds` reports the live bounds,
  `bounds capture` stores them, `bounds restore` clears them, `bounds camera|blast l r t b` sets the
  live stage and the document; the overlay draws the camera rect green and the blast rect red (clamped
  to the canvas). **Spawns** ride the same version: `spawn={[slot]={x=…,y=…}, …}` for every moved
  start/respawn, validated (slots 0–7) and re-applied through `gd.stage_set_spawn` on load.

### 6.7 Community pain points (what our editor must not repeat)

1. The `+0x20` offset confusion → our file format is plain Lua; no offsets.
2. **Collision ≠ model** → our instances carry their collision; the property grid says so.
3. **Nothing is labelled** → §6.3 names every point; the overlay labels groups.
4. **Silent save failures** → read-back verification + a loud save toast.
5. **Tool rot and fragmentation** → the editor is in-tree and tested (contract test + in-game captures).
6. **Bounds by trial and error** → P2 draws camera/blast rects with a preview.
7. **Crash-prone imports** → we only spawn validated kit assets; no bone-count coupling.
8. **Walkoffs everywhere** → P2 can warn when a blast bound sits inside a wall.
9. **Ledge/flag subtlety** → `floor_flags` are named in the UI (drop-through / ledges), not bits.
10. **Tool copy/paste mismatch** → our layouts are self-describing and version-checked.

### 6.8 What cannot persist today (the roadmap's raw input)

Stage id/binding · items/enemies · model binaries · authored collision geometry · tint/layer/
visible/alpha · Z-depth collision · undo history and UI state · pad handles ·
cross-mod sharing · rollback safety · streaming worlds · asset-bundle self-validation (units/scale).
(Camera/blast bounds and **start/respawn points** left this list on 2026-09-28 — both are editable and
persisted in layout v2; item/enemy spawns still have no editor.)

---

## §7 Current editor audit (as of the readability pass, commit `104db2739`)

### 7.1 Inventory

- **Tools (5):** place, select, move, rotate, scale.
- **Palette (21):** the `bf_*` kit parts (floors, walls, trims, glass, stairs, ramps, posts).
- **Actions (33):** place/select/move/duplicate/delete, undo/redo, save/load, overlay, grid cycle,
  new-part defaults, tools, scale/mirror/reset, constraint, snap, help.
- **Keys:** F6/F1/H/F2/F3/F7/F8, Z, arrows, PgUp/PgDn, Insert, Del, Tab, Enter, Esc, M/R/T/C/G/X/Y, 1-5,
  WASD (fly), Ctrl+{D,Z,Y,S,O}, Shift+{X,Y}; plus pad edges via `gd.pad(1)`.
- **Panels:** top bar (title/tool/part/file), left panel (TOOL + PART/ACTIONS + Help rows), right
  SELECTION inspector (name, x/y/z/rot/scale, collision, floor flags), bottom bar (hint + state +
  last-action/error), all on an opaque backdrop; help modal (single column, 12 rows, scrollbar, dim
  backdrop). Every panel is laid out against `gd.safe_area()`, so the bars span the whole window at any
  aspect and the inspector hugs the right edge.
- **Gizmos:** the selection carries red/green move handles, a cyan scale handle and a gold rotate ring
  (§5.12), drawn from `gd.project`; the world cursor cross and the part outlines use the same projection.
- **Undo:** 64 clone snapshots; failed ops do not advance history; selection re-validated after apply.
- **Picking:** no raycast — nearest part origin in XYZ (including the selected depth plane); screen→world
  via a **plane homography** solved from four projected samples, cached per (camera interest, depth,
  eye) — widescreen-correct without assuming camera constants.

### 7.2 What is already right (keep it)

- Opaque panels + dimmed modal + scrollbar (this pass; verified).
- Read-back-verified save with `.bak`.
- History that refuses to record failed operations.
- Screen→world by homography (the only widescreen-safe approach available to Lua here).
- The console command surface (`map …`) mirroring every action — the automation/test bed.

### 7.3 Defects found in captures (fix in P0/P1)

| # | defect | fix | phase |
|---|---|---|---|
| D1 | Part rows showed meaningless index numbers as their "value" | the property grid (§5.7) or remove the value column | **fixed P1**: palette rows show names (recents `*`), values live in the inspector |
| D2 | `New …` action rows mutate new-part defaults invisibly | move to a "New parts" section of the panel showing the actual values | **partial P1**: the inspector shows the selected part's real values; the New… rows remain |
| D3 | Errors share the status line with mode text | dedicated error line/colour (§5.9) | **fixed P0** |
| D4 | No feedback on the last undoable action | "last action" in the status bar (§5.6) | **fixed P0** |
| D5 | The native FLY readout draws over the modal's bottom-left corner | raise the modal 8px and/or shrink; noted as a port-UI z-order issue | open |
| D6 | Selection is a bare cyan square; no part identity | selection panel + ghost of what is selected | **fixed P1** (SELECTION panel; ghost still open) |
| D7 | Rotation/mirror semantics are hidden in the README, not the UI | per-tool hint line + help row (§4.3) | **fixed P0/P1** (per-tool hints) |
| D8 | No spawn/camera/bounds at all | phase P2 (§6.2/6.3) | open (P2) |

### 7.4 Rules the code already encodes (do not break)

- Collision follows owned instances; mirroring an instance that owns collision goes through
  despawn/respawn (the engine rejects in-place axis-sign flips); scale fields are written only when
  ≠ 1 so v1 files stay valid.
- Z moves the visual only; the fighter plane is XY.
- `map save` is allowed outside a match (recovery); every other op requires an active offline match.

---

## §8 Roadmap

Each phase has acceptance criteria; a phase is not "done" until the criteria pass **and** the change
cites this bible.

### P0 — Controls + honesty (this pass)

**Done 2026-09-28** (game `f637fc46f`, verified on screen): hybrid `G/E/C` hold-to-transform with tap-to-switch,
`F` frame, `Shift`/`Ctrl` polarity, `Z` snap, `Shift+C` constraint, last-action + persistent error lines,
help updated. Contract tests cover modal move/undo, ESC revert, axis lock, frame, snap, fine step.

### P1 — Make it a tool people want to use

**Done 2026-09-28** (this session, verified on screen): palette **filter + recents + typed `F4` mode**
(`map filter <text>` for scripts/tests; matches are pinned-recent-first; `*` marks recent rows), the
**SELECTION inspector** (right panel: name, x/y/z/rot/scale; drag to scrub, click to type; click
`collision`/`floor flags` to edit), **on-object gizmo handles** (§5.12), **toasts** for
save/load/duplicate/clear, and the error/last-action split. The overlay also fills the widescreen frame
via `gd.safe_area` (§4.6).
**Remaining:** a native `gd.kit.field` widget, a ghost hover highlight, and
palette *search ranking* (filter + category headers + recents are done: the list groups under gold
`floor`/`wall`/`trim`/`glass`/`corner`/`door`/`balcony` headers, 5 parts per page).

### P2 — Own the ecosystem gap (spawns, camera, bounds)

**Done 2026-09-28:** layout **v2** persists camera/blast bounds (v1 still reads), `map bounds
capture|restore|camera l r t b|blast l r t b` edits them, and the overlay draws the camera rect green /
blast rect red. Contract tests cover capture → v2 serialize → load-applies → round-trip and v1
compatibility. **Player start/respawn editing landed too:** `gd.stage_set_spawn(slot, x, y)` +
`gd.stage_spawn(slot)` (native, JObj translate; arena-owned and restorable) with the editor's
`map spawn <0-7> [x y]` op — verified live by moving P1's respawn to `x=-100` and respawning there.
**Remaining:** write spawns into the layout (v2), a drag-a-rect bounds UI, spawn/bounds handles, and
the walkoff warning (§6.7 #8); item/enemy spawns still have no editor.

- Read, display, name, edit and persist: player respawns (ids 0–7) — the scripted-platform API already
  exists for spawn points; camera bounds and blast bounds via `gd.stage_set_camera_bounds` /
  `stage_set_blast_bounds` / `stage_restore_bounds`; wire them into the layout file as a **version 2**
  schema (bump `version`, keep v1 readable).
- Draw camera/blast rects in the overlay with a preview; warn when a blast bound sits inside a wall
  (§6.7 #8).
- **Acceptance:** a builder can shrink a stage's camera to a room and save/reload it; the layout
  round-trips; validation rejects camera `l>=r` or `b>=t`.

### P3 — Multi-select, polish, scale

- Box select + grouped transforms (one undo step) (§5.4); duplicate ×N (§5.5).
- Widescreen/safe-area layout (§4.6, `_research/widescreen.md`) and camera collision (§2 P13).
- Optional orthographic/top view for alignment (P5 says default to 3D; add ortho as a precision aid).
- **Acceptance:** a 200-part room is still editable at 60 fps; the editor respects `gd.safe_area`.

---

## §9 UI specification (640×480 space, pre-safe-area)

Current layout (P0, verified on screen): top bar `8,10,624,30`; left panel `8,44,246,338`; bottom bar
`8,386,624,44`; help modal `40,24,560,432` (move to `40,16` per D5). All panels sit on an opaque
backdrop (`0x0E1218FF`); the help modal additionally dims the frame (`0x000000A8`) and boxes itself.

```
 0                                                         640
  ┌─────────────────────────────────────────────────────────┐ 10
  │ MAP EDITOR   tool: move [x]      part: floor_4m  *room.lua│ 30   top bar
  ├──────────────┬──────────────────────────────────────────┤ 44
  │ TOOL         │                                          │
  │ 1 place      │            (3D view + ghost)             │
  │ 2 select  ◀  │                                          │
  │ 3 move       │        ✛ cursor cross (snapped)          │
  │ 4 rotate     │                                          │
  │ 5 scale      │                                          │
  │ ── PART ──   │                                          │  P1: right inspector
  │  floor_4m ◀  │                                          │      388,44,244,338
  │  wall_solid  │                                          │
  │  …           │                                          │
  │ ── Help (F1) │                                          │
  ├──────────────┴──────────────────────────────────────────┤ 386
  │ hint: drag to move · Ctrl snap · Shift fine             │ 404  status/hint
  │ XYZ 12.00 0.00 6.00 | grid 0.5 | snap on | parts 14/128  │ 418  state
  │ ✖ error: rotate refused (collision owner)               │ 432  error line (P0)
  └─────────────────────────────────────────────────────────┘ 434
  Toasts (P1): top-right, 2 max, errors persist until dismissed.
```

Rules:
- **Left panel** = tools + the current task's list (palette when place, actions otherwise) + Help.
- **Right panel (P1)** = inspector; appears only when something is selected, otherwise shows the
  "New parts" defaults.
- **Bottom bar** = one line per job: hint (what the tool does), state (numbers), error (persistent).
- **Modal help** = single column, 12 rows visible, proportional scrollbar, dim backdrop, opaque panel.
- **Cursor** = gold cross at the snapped origin; selected part = cyan square + axis hints; ghost (P1) =
  translucent model, green/red tint.
- Never draw text on a translucent surface (§2 P19's practical form; the kit panel fill is translucent).

---

## §10 Implementation appendix (verified API surface)

Citations are `file:line` at the 2026-09-28 checkout; `gw_script.c` = `pc/platform/gw_script.c`.

### 10.1 `gd.kit.*` (all drawing-only; 640×480; safe online)

| call | returns | notes |
|---|---|---|
| `gd.kit.available()` | `bool, why` | guard every kit use; else hard error |
| `gd.kit.text(x, baseline_y, text[, role[, colour[, align[, opts]]]])` | width | `y` = **baseline**; `opts {max_w, shear}`; fit rule on `max_w` |
| `gd.kit.paragraph(x, top_y, w, text[, role[, colour[, opts]]])` | lines, height | wraps at spaces; `\n` hard break; overlong word falls back to the fit rule |
| `gd.kit.measure(text[, role[, max_w]])` | width, height, fitted | ellipsis byte 0x01 shown as `~` |
| `gd.kit.metrics(role)` | sizes | 1× px |
| `gd.kit.texture(name)` / `image(name,x,y[,w[,h[,opts]]])` | info / w,h | `opts {tint, scale, flip_x, flip_y, shear}` |
| `gd.kit.icon(name,x,y[,scale[,tint]])` | w,h | resolves `ico_<name>` |
| `gd.kit.panel(x,y,w,h[,{prefix,piece,tint,fill,shear}])` | — | 9-slice; `fill` defaults `@bg` α 0xE0 (**translucent** — back it or pass an opaque fill) |
| `gd.kit.button(x,y,w,label[,state[,opts]])` | height | `state`: `true/"sel"`, `false/"ng"`, `"disabled"`; `opts {value,h,shear,section}` |
| `gd.kit.list(x,y,w,items,selected[,opts])` | height | `opts {pitch,h,first,visible,shear,section}` |
| `gd.kit.color(token)` | rgba or nil | unlike other colour args, returns nil on unknown |

Data: `gd.kit.colors` (palette + sections + ports), `gd.kit.roles` (1-based, smallest first),
`gd.kit.row` (h/pitch/label_x/label_base/lift), `gd.kit.shear`.

### 10.2 Text roles (smallest first)

`caption` (12/15) · `body` (14/18) · `row` (16/20) · `label` (20/25) · `title` (24/30) · `heading`
(32/40) · `hero` (44/55, caps) · `display` (56/70, caps) · `tag` (20/25, mono) · `code` (16/20, mono).
`bone` is a **colour**, not a role. Hero/display uppercase input; code maps unknown chars to `?`.
The fit rule steps down to the next smaller role **of the same face**, then ellipsises.

### 10.3 Colours and pieces

Tokens: `0xRRGGBBAA`, `{r,g,b,a}`, `#rrggbb[aa]`, `@face/@bg/@band/@face_hi` (Versus only),
`<section>.<which>`, `p1..p4`/`cpu`/`port:pN`, or a palette name. Palette: `ink bone muted disabled gold
gold_lt gold_dk danger ok`. Sections: versus solo collection options data (each face/bg/band/face_hi).
Panel pieces are **named textures** (no numeric ids): `<prefix>_corner_tl/_tr/_bl/_br`, `_edge_h`,
`_edge_v`, `_fill`; icons `ico_*`; glyphs `glyph_*`; mod `ui/` overrides the kit.

### 10.4 Input

| call | semantics |
|---|---|
| `gd.mouse()` → x,y,buttons,wheel | 640×480; `-1000` off-picture; buttons 1=L,2=R,4=M; **polling it shows the cursor — only while editing** |
| `gd.key(name)` / `gd.key_pressed(name)` | A-Z 0-9 F1-F12 KP0-9 SPACE ENTER TAB ESCAPE BACKSPACE SHIFT CTRL ALT arrows HOME END PGUP PGDN INSERT DELETE |
| `gd.pad(port)` | `{buttons,x,y,cx,cy,l,r,A..Z}` — what the game read |
| `gd.buttons` | A=0x100 B=0x200 X=0x400 Y=0x800 START=0x1000 L=0x40 R=0x20 Z=0x10 UP=8 DOWN=4 LEFT=1 RIGHT=2 (12 names only) |
| `gd.input/gd.press/gd.tilt` | gameplay pad override (offline only) |

### 10.5 Plain draws

`gd.text(x,y,text[,colour[,size]])` (size 1 = 13 px) · `gd.box` (outline) · `gd.fill` (default
`0x000000A0`) · `gd.line` · `gd.label(text)` · `gd.rgb(r,g,b[,a])` · `gd.project(x,y[,z])` →
`screen_x, screen_y, visible, depth` (nil before a match). Plain draws take int/table colours only.

### 10.6 Console and geometry APIs

- `gd.command(name, fn[, help])` registers a console command (the `map …` surface).
- **There is no `gd.map` table and no `l_map_*`.** Geometry editing is:
  - `gd.stage_add_platform(x,y,w[,{passthrough,ledges}])`, `gd.stage_add_line(x1,y1,x2,y2,kind[,opts])`
    (kind = floor/ceiling/right_wall/left_wall, direction-checked), `gd.stage_add_model{...}`,
    `gd.stage_move(handle,x,y)`, `gd.stage_remove(handle)`, `gd.spawn_target(x,y)`,
    `gd.stage_view([geometry[,overlay]])`, `gd.stage_bounds()`.
  - `gd.stage_set_origin/camera_bounds/blast_bounds/restore_bounds`, `stage_collision_group(s)`
    (`gw_script_arena.inc`).
  - `gd.model_load/spawn/set/move/despawn/release/get/instances` — the runtime meshes this editor uses.
  - `gd.area_load/unload/loaded`, `gd.stage_stats()` (`gw_script_largemap.inc`).
- All are offline + `"gameplay": true`; every write forks the rewind timeline; handles are never reused.

---

## §11 Decisions log

| # | decision | basis |
|---|---|---|
| D-a | Control scheme = **hybrid** (immediate default, hold = modal) | §4.2/P6; L5 recommendation |
| D-b | Move=`G`, rotate=`E`, scale=`C`; `R` stays discrete rotate | §4.1/P6; the reserved-key conflict |
| D-c | `Ctrl` = snap, `Shift` = fine (Blender/Unity polarity, not ImGui's) | §4.5 |
| D-d | `F` = frame (sets the orbit pivot) | §2 P11/P6 |
| D-e | Snap **on by default**; `G` toggles; `Ctrl` is momentary | §2 P8/P9 |
| D-f | Panels are opaque-backed; kit fills are never trusted as opaque | §2 P19; verified defect |
| D-g | Help = single column, 12 rows, scrollbar, dim backdrop | verified fix + §5.10 |
| D-h | Editor keeps its 128-part cap until the engine ceiling (256) is verified in the exe | §6.5 |
| D-i | The inspector is a new right panel; `New …` action rows become fields | §5.7; D1/D2 |
| D-j | Pads are **read-only** for the UI (no override) | §5.1; offline-only manifest |
| D-k | Save is read-back verified; errors are persistent and specific | §2 P15/P19 |
| D-l | Layout stays `version=1` until spawns/camera land (then v2, v1 still readable) | §6.8 |

**Open questions for GD (do not guess):**

| # | question |
|---|---|
| O1 | Confirm the hybrid scheme (or choose Blender-modal / Maya-immediate) — §4.2. |
| O2 | Should the part cap rise to the engine's 256 once the exe is verified? (§6.5, D-h.) |
| O3 | Spawn/camera/bounds: edit the *native* stage (P2 as written) or script-only overlays that a map can ship? The native route needs a round-trip + budget story. |
| O4 | Orthographic/top view: wanted, or is the fly camera enough? (§8 P3.) |
| O5 | Gamepad palette: radial wheel (Forge-like) or the same list? (§5.3.) |
| O6 | Expose `tint`/`layer`/`visible`/`alpha` in v2, or keep the part set minimal? (§6.8.) |
| O7 | Widescreen safe-area timing — the editor layout should switch to `gd.safe_area` when it lands (§4.6). |
| O8 | Is per-part **custom collision** (drawing lines) in scope at all, or is the sidecar the contract? (§1.3.) |

---

## §12 Sources and the Jev ranking

### 12.1 The emphasis ranking (why the sections are ordered as they are)

33 findings were scored with Jev (`tools/jev/rank_chunks.py`, one `noul` per finding, one call, 7,505
tokens in / 669 out): *"Does this finding materially inform or change the plan for the goal?"* Both
distractors scored 0.03; the design findings 0.64–0.95. Ranked (top 12):

| noul | finding | where |
|---|---|---|
| 0.95 | reserved-key conflict (`W/R/S` break both canonical clusters) | §4.1 |
| 0.95 | unlabelled nodes are the historical pain | §2 P20, §6.3 |
| 0.95 | silent save failures | §2 P19, §6.6 |
| 0.95 | a stage is two graphs (`map_head` + `coll_data`) | §6.2 |
| 0.95 | general points carry spawns/camera/blast | §6.3 |
| 0.94 | snapping is faster *and* more precise | §2 P8 |
| 0.94 | snapping dead zones | §2 P9 |
| 0.94 | hybrid modal/immediate | §4.2 |
| 0.94 | camera metaphor is task-dependent | §2 P11 |
| 0.94 | BrawlBox is the expected baseline | §2 P26 |
| 0.93 | undo named and grouped | §2 P17 |
| 0.93 | opaque panels | §2 P19, §5.10 |

Artifacts: `_build/agents/batcha/bible-findings.tsv`, `rank_chunks.md`, `rank_chunks.json`.

### 12.2 Sources

- **L1 (canonical controls):** Unreal 4.27 LDQuickStart + Viewport Basics; Unity SceneViewNavigation +
  hotkeys + PositioningGameObjects; Godot introduction_to_3d + default_key_mapping; Blender navigation
  / viewpoint / snapping / projections; Hammer 3.4 3D View + Hotkey Reference (Source 2 page
  bot-gated — unverified); TrenchBroom manual; Tiled keyboard shortcuts; NetRadiant/Q3Radiant.
- **L2 (gamepad/in-game editors):** Halopedia H3/Reach/MCC/HINF control schemes + Forge + H5G:Forge;
  ForgeWiki interface (Infinite trigger chords + snap ladders); Nintendo Life (Oshino) + Time
  (Miyamoto/Tezuka) for Mario Maker; SmashWiki + Nintendo Wii U manual + IGN/Game8 for the Smash stage
  builders; LBP Wiki Controls; Indreams/TAPgiles/Dreamskool for Dreams; minecraft.net controls +
  minecraft.wiki controller page; create.roblox.com parts/cross-platform/DragDetector; Far Cry Arcade
  Steam guide + editor.farcry.info; Bethesda SnapMap wiki + Steam hotkeys.
- **L3 (Melee stage ecosystem):** decomp `gr/types.h`, `mp/types.h`, `gr/forward.h`, `ground.c`,
  `grdatfiles.c` + doldecomp.github.io/melee; SmashBoards (DAT format 292603, Stage Hacking 328552,
  Crazy Hand 389500, DTW 373777, Melee Toolkit 334274, Smash Forge 447380, TDRR imports 506145, stage
  collision 278556); GitHub (Crazy-Hand-Project, DRGN-DRC, Ploaj/HSDLib, bsv798/gcrebuilder,
  jam1garner/Smash-Forge, akaneia/m-ex); KC-MM; workspace `_research/map-editing.md`.
- **L4 (interaction patterns):** Dear ImGui `imgui.h`/`imgui_widgets.cpp`/`docs/FAQ.md`/`imgui_demo.cpp`
  @`aa01814`; ImGuizmo @`18cef5e`; VS Code `fuzzyScorer.ts`/`filters.ts`/`commandsQuickAccess.ts`;
  Blender fields/undo/duplicate/array/keymap; Unity `FieldMouseDragger`/`DragNumberValue`@`61f92bd`/
  Undo API; Tiled shortcuts + issue #3890; imgui-notify; pascalorg `ghost-materials.ts`.
- **L5 (hotkey canon):** the same official shortcut docs, merged; §4.2/§4.3 are its direct product.
- **L6 (principles):** Duske ModDB interview + TrenchBroom manual; Storm GDC 2016 ("Keeping Level
  Designers in the Zone") + "Don't Fear the Hammer" (Game Developer); Oshino/Miyamoto (Nintendo Life,
  Time); Ware & Osborne (I3D 1990) + Ware & Fleet (I3D 1997) + SHOCam (2015); Oh Snap (UBC 2011) +
  Snap-and-go (CHI 2005) + shape-dependent snapping (KAIST); Nielsen (progressive disclosure, 10
  heuristics, confirmation dialogs, user control) + Microsoft progressive-disclosure guidance; Abowd &
  Dix, "Giving Undo Attention" (1992); Zucconi 0RBITALIS postmortem; Flukz devlog; Simplified Media
  browser-editor guide; Callum Nottage postmortem.
- **E1/E2 (our port):** `gw_kit.h/.c`, `gw_script.c`, `gw_script_pad.c`,
  `gw_script_model_api.inc`, `gw_script_lane*.inc`/`gw_script_largemap.inc`,
  `gw_script_arena.inc`, `pc/gameworld/script_model.{h,inc}`, `script_game.c`, `docs/scripting.md`,
  `_build/ui/font_manifest.json`, `_build/ui/kit.json`, `_research/menu-kit-pieces.md`.

### 12.3 Verification status of this document

- Every API row in §10 is read from source at the cited checkout and cross-checked against
  `_build/ui/*.json` and the shipped `.gxtex` set; **none of it has been run** in this session except
  the P0 readability items (which were verified on screen).
- The limits in §6.5 are source-read; the workspace's trap #1 applies: verify in the exe before
  quoting.

---

## §13 The one-paragraph summary

The editor is an in-match, first-person assembly tool for the port's kit parts. Its unusual constraint —
`W`, `R`, `S`, `Tab`, `X`, `Y` and `F1`–`F6` are already taken — breaks both the Unity/Unreal/Maya and
Blender control clusters, so the scheme is a deliberate hybrid: **immediate mode with an always-on
gizmo, `G`/`E`/`C` for move/rotate/scale, hold-to-go-modal, `F` to frame, `Ctrl` to snap, `Shift` to
fine.** It must be legible (opaque panels, single-column help, status/error separation), safe (named
grouped undo, read-back-verified save, confirmations only for deletion), and honest (previews equal
commits, limits announced before they bite). Its growth path is the gap the Melee ecosystem left:
**named spawns, camera bounds and blast zones, editable and persisted in a v2 layout** — the BrawlBox
role, which no maintained Melee tool fills. Every future change cites a section here; if it cannot, the
bible is updated first.

