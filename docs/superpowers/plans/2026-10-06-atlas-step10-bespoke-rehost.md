# Atlas step 10: the bespoke retail screens, re-hosted in Atlas chrome: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the retail Trophy Gallery, Collection (the trophy room) and Lottery scenes **unchanged** and draw Atlas chrome around them: trail, an explainer (name, one rule line, FROM), a counter, key hints, in the Atlas look, with the retail 3D showing through a transparent **window** in an opaque Atlas plate. The retail 2D pieces that sit inside the window are hidden one by one with the retail element mask; the retail renderer keeps drawing its own models from the player's disc at run time, and nothing is copied or stored. **Each screen has its own go or no-go** and any can be dropped without holding the others up. **Tournament** is undecided by the owner: it is planned as an optional, separately gated task (Task 9). **Not in this step, by the owner's word:** Movies, Staff Roll and Snapshots (they stay retail behind a hand-off, Task 10) and the vanilla Training panel (the LAB covers it).

**Architecture:** (1) Pure C additions to the step 3 / step 8 host: more retail element ids (toy panels, info panel, text), a per-scene mask table in the scene policy, a `frame` screen primary (`gw_ui_frame.c`: the window's rectangle on the arranged canvas, the plates around it, where each chrome slot goes and what is dropped), all tested without a game. (2) A generalised `OVERLAY` hook: today `gs_ui_overlay_try` knows only the title; a retail scene under `OVERLAY` now also gets a per-frame **game-side wrapper** around its own `on_frame` that submits the chrome view from readbacks, through the same shims the menu adapter uses. (3) Creation-time guards at each retail 2D site (a GX link callback swapped for a no-op, a text object's `hidden` flag): the mask is constant for the scene (the policy sets it before `on_enter`), no proc is ever skipped. (4) Per screen: readbacks, a chrome builder, the guard list, the window rectangle. (5) The retail text of the screens (names, descriptions) is read with step 8's decoder, only where step 8's gate said the English strings decode; otherwise the retail text objects stay visible (a partial mask) and Atlas draws only the frame.

**Tech Stack:** C11 host code through `tools/port/native_test.sh` (no game, no disc); game-side retargeted C checked with `clang --target=powerpc-unknown-eabi -fsyntax-only`; Python 3 guard scripts; the step 1 harness (`atlas_check.h`, `atlas_fake.h`, `atlas_rec.h`) and, if merged, step 6's `atlas_lint.h`.

**Spec:** `docs/superpowers/specs/2026-10-06-menu-reunification-design.md`, section 13.10 (this step), with 6.8 (the capability), 12 items 8 and 13, 14, 15, 16. Earlier plans this one builds on: step 3 (`docs/superpowers/plans/2026-10-06-atlas-step3-envoy-and-hud.md`, read on branch `agent/atlas3`), step 8 (`...-step8-retail-data-screens.md`, the text decoder and the adapter pattern), step 6 Task 0 (the gate script).

**Status of the plan:** written 2026-10-06 against the merged tree through step 2 and step 3 as built on `agent/atlas3` (head `d9b1b1647`: `gw_ui_retail.c/.h`, `gw_ui_retail_ids.h`, `gw_ui_hud.c`, the guards in `src/melee/if/*.c` and `gmpause.c`, `AT_PRIMARY_CARDS`, `persist`). Read for this plan: `ty/toy.c` (the Gallery: 6,842 lines, read at the scene entry, the text creation, the GX link sites and the pad polling), `ty/tydisplay.c` (the Collection, 2,525), `ty/tyfigupon.c` (the Lottery, 1,676), `gm/gmscdata.c`, `gm/gm_1A3F.c:150-260`, `gm/gmscene.c:790-810`, `gm/gmstaffroll.c` and `gmgover.c`/`gmdebugmode.c` (where Staff Roll is reached), `mn/mngallery.c`, `gw_runtime.c` (the scene launcher), `pc/docs/TROPHIES.md`. Steps 4 to 7 exist only as plans. **Nothing in this plan was compiled, run or seen**: every C block is unbuilt; every fact about what retail draws or where is read from source and marked "(unverified)" until the probe of Task 1 or a look settles it.

## Corrections to the spec, found in the code

1. **Opaque plates already hide retail 2D.** Atlas draws an opaque ground and opaque panes (`gw_ui_render.c:295`, step 2's finding D1), drawn **over** everything the game renders. So a framed scene needs no mask for the retail 2D pieces that sit **outside** the window: the plates cover them. The mask is needed only for retail 2D pieces **inside** the window (the trophy's name and description text, any frame or hint icon the camera draws over the model) and for text the owner wants Atlas to own. This makes the mask list shorter than 13.10 suggests and removes a class of "hidden element came back" bugs.
2. **The window must sit where retail draws the model, and where that is on a wide window is not known.** `gmfrontend.c:920-932` centres a 4:3 band for native menus; the port also has a `View` canvas (`gmscene.c:211` `View_SceneBegin`, `pc/tests/view_canvas_test.c`). How the toy scenes' camera maps onto a 16:9 or 21:9 window is **(unverified; settled by Task 1)**. Until it is, the plan places the hole at `window_x + (canvas_w - 640) / 2` (the 4:3 band centred), which is exactly right if retail pillarboxes and wrong if retail widens the view.
3. **Retail text is a glyph stream, not Unicode** (step 8, correction 2). Trophy names and descriptions are `SIS` strings (`SdToy.usd` `SIS_ToyData_E` in font slot 0, `SdToyExp.usd` `SIS_ToyDataExp_E` in slot 3, opened at `toy.c:6519-6526`; the text objects `x144` name, `x148` description, `x14C` and `x150` further lines, `toy.c:2900-3000`). Whether they decode is step 8's gate (Task 1 of that plan, `SdToy` probe). **Step 10 does not start its text-dependent parts before that answer exists.**
4. **Staff Roll has no menu entry in retail.** 13.10 says to "give it an entry under More > Credits". `GS_STAFFROLL` is reached from the game-over ending flow (`gmgover.c:34-39`) and from the debug mode (`gmdebugmode.c:250-256`), never from a menu. An entry in Credits would be a **new launch path** (a scene launch like `gw_runtime.c`'s `gw_sl_modes`), not a hand-off. Task 10 makes it an **owner decision**, default none.
5. **The three bespoke scenes run in `GM_MENU`'s sibling modes**, not in the frontend: the Collection hub's rows are `FA_MODE` rows to `GM_TOY_GALLERY`, `GM_TOY_LOTTERY`, `GM_TOY_COLLECTION` (`gmfrontend_menus.inc:214-218`) and back-out is the retail mode exit followed by `fm_position_for` (`gmfrontend_menus.inc:359-361`). The scene runs retail's own exit (`Toy_Scene_OnFrame` sees `TyModeState.x4` and calls `gm_801A4B60()`); step 10 never intercepts it.
6. **A framed screen must not draw while a netplay or rollback session is on**, because the retail mask is forced to 0 then (step 3: `at_retail_effective(.., online)`). Chrome over unhidden retail 2D would collide. The screens are menu-only and unreachable in a lobby, but the plan adds an explicit guard (Task 4) instead of relying on that.

## Global Constraints

Exact values come from the spec; if a task seems to need a different one, stop and ask the coordinator.

- **Canvas and layout:** 640x480 logical; compact below 760 wide, wide from 760; content at most 1140 wide, centred; margins 32; header top 22 (30 high, rule at 56), body 66 to 428, footer 434 (26 high); explainer presets narrow 160, normal 196, wide 256.
- **Text:** floor 12 px, roles and fit rule as step 1. A string that needed the ellipsis at 640 is logged once per screen id.
- **Shape and focus:** flat quads, chamfers top-left and bottom-right only, front edge 3 px, modal 6; focus is three cues at once. **A framed screen has no focus** (retail owns the pad): key hints are information, never clickable, and the screen records **no hit rectangles** (mouse is not supported on a framed screen in version 1, 13.10 item 5).
- **Retail untouched by default.** Every scene stays `RETAIL` and the mask empty until the owner says go for **that** screen. `MELEE_ATLAS=0` leaves all of it retail. `MELEE_ATLAS_SCENES=<kind>:overlay` (kinds 11, 12, 13 for Gallery, Lottery, Collection) turns one on for development. A flip is one table line per scene.
- **Presentation only, never a proc.** A guard replaces a render callback with a no-op or sets a text object's `hidden` flag **at creation**; it never skips a per-frame proc, never writes retail state, never changes a branch. With the mask empty the code path is the retail one (step 3's rule).
- **Online:** nothing hidden online (the effective mask is 0 while netplay or rollback is on) and **no framed screen draws then** (Task 4 guard). No file under `pc/platform/gw_ui_*` includes a netplay header.
- **No disc-derived data, ever.** Models, textures, text and animations are drawn by retail from the player's disc at run time. The only things committed are code, tests with **invented** trophy names and counts, and four numbers per screen (the window rectangle in the 640x480 logical canvas: where the retail camera frames its model: a screen position, not game content). Decoded text lives in a bounded buffer for the frame and is never logged or written (step 8's `check_no_disc_text.py` runs on this step's files too).
- **Mods work on vanilla.** The scenes run on the vanilla disc and on ACE (m-ex adds trophies; the counter and the readbacks use the retail getters, so they follow).
- **Credit outside assets.** Nothing outside this project is used. The spec's wording "preserve the original look" is satisfied by letting retail draw. If a task adopts anything outside, the same commit names it in `CREDITS.md`.
- **English only.** Authored strings are English; decoded retail strings are shown only if every glyph decodes (else the retail text object stays, or the authored fallback shows).
- **Per-screen go or no-go.** Each of Gallery, Collection, Lottery (and Tournament if asked) has a recorded decision in `docs/NEXT-SESSION.md` after its look: `go` (ship the policy row), `hold` (code kept, row off) or `drop` (code removed). No screen's row is added to the policy table by the code tasks; only by the decision.
- **Naming:** `at_*` host C, `gw_ui_*` files, `fad_*` and `fat_*` in game-side `.inc` files, shims `gw_Ui_*` (host) = `Ui_*` (game). English only.
- **Process rules (this machine):** reading, building and native tests only until Task 11. No game window while the owner is at the machine. Never terminate processes by image name; stop only a process you started, by PID. Build only through `tools/port/build.sh` in a private worktree made by `tools/port/agent_new.sh`; never raw clang for the game. Max 8 `melee-pc` in total; keep 2 GB free. Two repositories: game repo `melee/` (branch `pc-port`, your lane `agent/<name>`) and the workspace repo; each task says which gets the commit. `gw_mex_bridge.c` churn from `build.sh` is normal and is not committed by you.

## Needs from earlier steps (gated by Task 0)

Every name marked RECONCILE is assumed from a plan or read on a branch that is not merged; Task 0 greps for it and the engineer writes the real name into `tools/port/atlas_gate.py` and into the one wrapper that calls it.

| # | What step 10 needs | From | Name | Used by |
|---|---|---|---|---|
| N1 | The retail element ids, the mask with four sources, `gw_Ui_RetailHidden(id)`, effective 0 online | step 3 | **RECONCILE** (read on `agent/atlas3`): `AT_RE_*` in `gw_ui_retail_ids.h` (`AT_RE_COUNT = 9`), `AtRetail`, `AT_RS_POLICY`, `at_retail_set`, `at_retail_effective`, `gw_Ui_RetailHidden`, `gs_ui_retail` | Tasks 2, 4 |
| N2 | The retail guard pattern at a draw site (`Ui_RetailHidden(id)` read at the one site) | step 3 | **RECONCILE**: `src/melee/if/ifstatus.c:633` etc. on `agent/atlas3` | Tasks 5 to 7 |
| N3 | The scene policy table, `OVERLAY`, `Ui_ScenePolicy`, `gw_Ui_SceneBegin`/`SceneExit`, the engine slot | step 2 | built: `gw_ui_policy.c`, `gm_1A3F.c:190-205`, `gw_script_ui.inc:920-1000` | Tasks 2, 4 |
| N4 | The data-screen adapter pattern, `Ui_Row`, `Ui_Counter`, `Ui_Explain`, `Ui_Key`, `Ui_Commit` | steps 2, 8 | built (2): `Ui_Explain`, `Ui_Key`, `Ui_Commit`, `Ui_Begin`; **RECONCILE** (8): `Ui_Counter`, `gmfrontend_atlas_data.inc`, `fad_sis_text` | Tasks 4 to 7 |
| N5 | The retail text decoder and its gate result for `SdToy` and `SdToyExp` | step 8 | **RECONCILE**: `at_sis_decode`, the Task 1 probe outcome (GO / PARTIAL / NO-GO) | Tasks 5 to 7 |
| N6 | A screen primary with no list or tiles (a `display` screen exists: the title) and `input_feed` | steps 1, 2 | built: `AT_PRIMARY_DISPLAY`, `AtScreen.input_feed` (`gw_ui_screen.h`); step 3 adds `AT_PRIMARY_CARDS = 5`; **RECONCILE** the next free number for `AT_PRIMARY_FRAME` | Task 3 |
| N7 | The gate script | step 6 | **not on main**; Task 0 creates or extends it exactly as step 8 Task 0 does | Task 0 |
| N8 | Lint helpers for style rules | step 6 | **RECONCILE (soft)**: `atlas_lint.h` | Tasks 3, 5 |
| N9 | The wide-window mapping of retail 3D scenes | the `View` system | **(unverified; Task 1)**: `View_SceneBegin`, `view_canvas_test.c` | Tasks 3, 5 |

## Review Focus

| # | What goes wrong for a player | Pinned by |
|---|---|---|
| 1 | **A guard hides more than intended, or a hidden element's state stops updating** (a missing number, a stuck animation, a trophy that cannot be rotated). | Task 2 `mask_*` and `policy_mask_*`; Task 5 `test_toy_guards.py` (guards only at `GObj_SetupGXLink` sites and text `hidden` flags; none inside a proc); Task 11 per-bit look |
| 2 | **The window is not where the model is**: the trophy half under an Atlas plate, or a hole showing the retail 2D frame. | Task 3 `hole_*` (the mapping at three widths); Task 4 `MELEE_ATLAS_FRAME_OUTLINE` and Task 11 steps 3 to 5 at 4:3 and 16:9 |
| 3 | **Chrome and window collide**: the explainer or the keys drawn over the model. | Task 3 `slots_*` (a slot that would intersect the hole is moved or dropped, never silently overlapped; an overlapping card is flagged) |
| 4 | **The framed screen steals or blocks input**: Atlas reads the pad while retail does, or a mouse click on a hint acts. | Task 3 `no_hits`; Task 4 `test_overlay_hook.py` (no `Ui_Intent`, `input_feed = 1`) |
| 5 | **Retail exit or back-out changes**: the wrapper swallows `on_frame`, the exit never fires, the Collection hub lands on the wrong row. | Task 4 `test_overlay_hook.py` (the inner `on_frame` is called first, every frame, unconditionally); Task 11 step 6 |
| 6 | **Disc text leaks or garbage shows**: a decoded trophy name in a log; a half-decoded description on screen. | `check_no_disc_text.py`; Task 5 `row_*` (a name with an unknown glyph is not shown) |
| 7 | **Trophy edge cases**: zero trophies, all owned, an m-ex trophy past the retail count, the last index, the empty Collection shelf. | Task 5 `gallery_*`, Task 6 `collection_*`, Task 7 `lottery_*` (counts 0, 1, 293 (retail's count is `TY_TROPHY_COUNT`; read it), 300) |
| 8 | **The Lottery popup or a coin drop is covered or hidden**: the one scene piece that must stay retail (it shows the real trophy model). | Task 7 (no guard on the popup objects, a grep) and Task 11 step 5 |
| 9 | **A framed screen draws online** or with a forced-empty mask over unhidden retail 2D. | Task 4 `online_no_frame` |
| 10 | **A skipped screen gets an Atlas treatment by accident** (Movies, Snapshots, Staff Roll: a policy row, a mask bit). | Task 10 `skipped_stay_retail` (the policy for their kinds is RETAIL, with no mask, even with `atlas_on`) |

---

## File structure

Game repo (`melee/`).

| File | Create/Modify | Responsibility |
|---|---|---|
| `pc/platform/gw_ui_retail_ids.h`, `gw_ui_retail.c` | Modify (step 3's files) | the toy and lottery element ids and names |
| `pc/platform/gw_ui_policy.h/.c` | Modify | a per-scene mask table and screen ids for the bespoke scenes; `at_policy_mask`; the screen id lookup for a non-default OVERLAY |
| `pc/platform/gw_ui_frame.h/.c` | Create | the window on the arranged canvas, the plates around it, the chrome slots (pure) |
| `pc/platform/gw_ui_screen.h`, `gw_ui_render.c`, `gw_ui_parts.c` | Modify | `AT_PRIMARY_FRAME`, `AtScreen.frame`, the render branch (no ground, plates, chrome, no hits) |
| `pc/platform/gw_script_ui.inc` | Modify | `gw_Ui_FrameBegin`, the generalised overlay (`gs_ui_overlay_try` no longer names "title"), the policy mask set at scene begin and cleared at exit |
| `src/melee/gm/gm_1A3F.c` | Modify | the OVERLAY `on_frame` wrapper (under `TARGET_PC`) |
| `src/melee/gm/gmfrontend_atlas_toy.inc` | Create | readbacks, the three chrome builders, the guard helpers, the window constants |
| `src/melee/ty/toy.c`, `tydisplay.c`, `tyfigupon.c` | Modify | the creation-site guards (one line each, `TARGET_PC`), the readback accessors if a static must be exposed |
| `pc/tests/atlas_frame_test.c`; additions to `atlas_retail_test.c`, `atlas_policy_test.c`, `atlas_render_test.c` | Create/Modify | the unit tests |

Workspace repo (root).

| File | Create/Modify | Responsibility |
|---|---|---|
| `tools/port/atlas_gate.py` | Modify | `--step 10` |
| `tools/port/test_overlay_hook.py`, `test_toy_guards.py` | Create | static guards (Review Focus 1, 4, 5, 8) |
| `tools/port/retail_screens.py` (step 8) | Modify | the three bespoke scenes and the three skipped ones in the inventory |
| `tools/port/native_test.sh` | Modify | case `atlas-frame`; `atlas-retail`, `atlas-policy`, `atlas-render` gain sources if needed |
| `docs/NEXT-SESSION.md`, `docs/TERMINOLOGY.md`, `menu/CLAUDE.md`, `docs/scripting.md` (only if Task 8 changes `gd.ui`: it does not) | Modify | decisions, the terms (frame, window, retail text), the retirement list |

## Preflight (once, before Task 0; not a task)

- [ ] **Step 1: Read.** `CLAUDE.md` (root), `docs/NEXT-SESSION.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md`, `melee/pc/docs/TROPHIES.md` whole (the scenes' history: the Lottery's entry fault is fixed; the scenes load their archives by name), the spec sections 6.8 and 13.10, step 3's plan Tasks 3, 4 and 6 and step 8's Task 1 and Task 3, `ty/toy.c` lines 1429-1495 (the pad polling), 2400-2500 and 2896-3000 (panels and text), 5760-5790 (the viewer), 6421-6575 (the scene pair), `tydisplay.c` 1801-2010, `tyfigupon.c` 1533-1676, `gm_1A3F.c` 150-260, `gmscene.c` 790-810.
- [ ] **Step 2: A private lane and the shell** (same as step 1; names changed):

```bash
export MAIN="<the workspace root: the directory that contains tools/ and _toolchains/>"
cd "$MAIN" && tools/port/agent_new.sh atlas10
git -C "$MAIN" worktree add worktrees/ws-atlas10 -b ws/atlas10
export WS="$MAIN/worktrees/ws-atlas10"; export GW_ROOT="$MAIN"
export GW_MELEE="$MAIN/worktrees/atlas10"; export GW_BUILD_ROOT="$MAIN/_build/agents/atlas10"   # as agent_new.sh printed them
nt() { GW_ROOT="$MAIN" GW_MELEE="$GW_MELEE" GW_BUILD_ROOT="$GW_BUILD_ROOT" bash "$WS/tools/port/native_test.sh" "$1"; }
```

- [ ] **Step 3: Baselines** (must still pass at the end): every merged `atlas-*` case, including `atlas-retail`, `atlas-hud`, `atlas-policy` (step 3 adds the first two) and `lua pc/tests/atlas_ui_stub_test.lua`, `python tools/port/check_no_disc_text.py`, `python -m unittest tools/port/test_fe_atlas_data.py` (step 8). Expected: each ends `N checks, 0 failed` or its own pass line.
- [ ] **Step 4: Which steps are merged.** Steps 1, 2 are on the integration branch; step 3 is on `agent/atlas3` until it merges; step 8 is a plan until it merges. **Task 0's gate says what is missing; Tasks 2 and 3 need only steps 2 and 3; Tasks 5 to 7 need step 8's decoder only for their text parts.**

---

### Task 0: The gate

**Files:** modify (workspace repo) `tools/port/atlas_gate.py`.

- [ ] **Step 1: Add the entry.** To the `G` table (created by step 6 Task 0 or step 8 Task 0; create it with the same layout if absent):

```python
    10: [
        ("pc/platform/gw_ui_retail_ids.h", r"AT_RE_COUNT", "step 3", "N1 the retail element ids"),
        ("pc/platform/gw_ui_retail.h", r"AT_RS_POLICY", "step 3", "N1 the scene-policy source of the mask"),
        ("pc/platform/gw_ui_retail.h", r"at_retail_effective", "step 3", "N1 effective mask (0 online)"),
        ("src/melee/if/iftime.c", r"Ui_RetailHidden", "step 3", "N2 the guard pattern"),
        ("pc/platform/gw_ui_policy.c", r"AT_POLICY_OVERLAY", "step 2", "N3 OVERLAY"),
        ("src/melee/gm/gm_1A3F.c", r"Ui_ScenePolicy", "step 2", "N3 the scene hook"),
        ("pc/platform/gw_ui_screen.h", r"AT_PRIMARY_DISPLAY", "step 2", "N6 a primary-less screen"),
    ],
```

and a `SOFT` entry: `10: [ ("src/melee/gm/gmfrontend_atlas_data.inc", r"fad_sis_text", "step 8", "N5 the text decoder"), ("pc/platform/gw_ui_retailtext.h", r"at_sis_decode", "step 8", "N5"), ("pc/tests/atlas_lint.h", r"lint_", "step 6", "N8 style lint") ]`.
- [ ] **Step 2: Run it.** `python tools/port/atlas_gate.py --step 10` against a checkout that has **step 3 merged**: exit 0. Against today's main (step 3 unmerged): the first four lines MISSING, exit 1: correct. The names step 3 built differ from this table in no place **read on `agent/atlas3`** (`gw_ui_retail.h` there declares `AT_RS_POLICY`, `at_retail_effective`, `AtRetail`); if a name changed at merge, reconcile the table and the wrappers, never the regex.
- [ ] **Step 3: Commit (workspace repo).** `tools: atlas_gate.py step 10 table`.

---

### Task 1: The probe and the decision record (before any chrome is drawn)

The three scenes are 12,000 lines of retail code this plan read at its seams only. Everything below depends on facts only a run shows. This task builds a read-only probe and records, per screen, GO, PARTIAL, NO-GO and the owner's go or no-go.

**Files:**
- Create (game repo): the probe in `src/melee/gm/gmfrontend_atlas_toy.inc` (the first block of that file)
- Modify (workspace repo): `docs/NEXT-SESSION.md` (the decision table)

- [ ] **Step 1: Write the probe** (a game-side function behind `MELEE_ATLAS_TOYPROBE=1`, called once per scene entry from the wrapper of Task 4; until Task 4 it is called from `Toy_Scene_OnEnter`'s end under `TARGET_PC`). It logs **numbers only**:

```c
/* MELEE_ATLAS_TOYPROBE=1: numbers about a bespoke scene, never text. */
static void fat_probe(u8 kind)
{
    HSD_CObj* cobj = HSD_CObjGetCurrent();   /* the scene's main camera when called from its on_frame */
    OSReport("frontend: toyprobe kind %d: trophies %d selected %d selid %d count %d coins %d\n", kind, (int) *gmMainLib_GetTrophyCount(),
             (int) *TOY_SEL, (int) *TOY_SELID, (int) *TOY_COUNT, (int) (gm_801623D8() / 10u));
    if (cobj != NULL) {
        float l, t, w, h;
        HSD_CObjGetViewport(cobj, &l, &t, &w, &h);   /* RECONCILE: the viewport getter the port has; units are the retail 640x480 canvas */
        OSReport("frontend: toyprobe kind %d: viewport %.1f %.1f %.1f %.1f, window %dx%d\n", kind, l, t, w, h, Ui_CanvasW(), 480);
    }
    OSReport("frontend: toyprobe kind %d: gxlink objects", kind);
    { int link; for (link = 0x30; link < 0x40; link++) OSReport(" %02X:%d", link, fat_count_gxlink(link)); }
    OSReport("\n");
}
```

`fat_count_gxlink(link)` walks the GObj GX link list for that link number (the structure `gobjgxlink.c` keeps: `gx_link_heads[link]`; read it) and counts objects; the log shows how many GObjs retail has at each of the links the scene creates (`0x32 TyMnBg`, `0x33` panel, `0x38 TyMnInfo`, `0x39` the viewer, `0x3C` labels in the Gallery, `toy.c`). The probe also logs, for step 8's text gate, the decode counts for `SdToy.usd`/`SIS_ToyData_E` (ids `Toy_803063D4(id, 2, 0x128)` for the first 20 trophies) and `SdToyExp.usd` (`0x374`, `0x37A`, `0x380`): characters and unknown glyphs only.
- [ ] **Step 2: The run (a Windows agent while the owner is away; `MELEE_VOLUME=0`; second monitor; one game):** with the probe, enter each scene once at 640x480, 960x720 and 1920x1080 (`MELEE_WINDOW_W/H`), through the Collection hub (`MAIN > COLLECTION`, the three rows), vanilla and ACE. Record in the decision table: (a) the viewport the camera uses at each size (**N9**: does 16:9 widen the view or pillarbox it?); (b) the GX link counts; (c) the trophy and coin readbacks make sense (selected index within count, coins non-negative); (d) the decode result for the toy text; (e) which GObjs lie **inside** the area the 3D occupies (compare the 3D bounds with the link counts by drawing the Task 4 outline over a candidate window).
- [ ] **Step 3: The decision table** in `docs/NEXT-SESSION.md` (one row per screen; this plan fills the columns it can; the run fills the rest; the owner writes the last two):

| Screen | Text | Window known | Inside-window 2D found | Cost | Agent verdict | Owner: go / hold / drop |
|---|---|---|---|---|---|---|
| Gallery | GO / PARTIAL / NO-GO | at 4:3 / at 16:9 | the GX links | S/M/L | | |
| Collection | | | | | | |
| Lottery | | | | | | |
| Tournament (optional) | n/a | n/a | n/a | L | not started | |

  A screen whose row says **NO-GO text** is still a go for a **text-less frame** (the window and the plates with the authored lines: `TROPHY n / total`, the series from numbers) if the owner wants it; the retail text objects then stay visible inside the window (partial mask).
- [ ] **Step 4: Commit.** Game repo: the probe. Workspace repo: the decision table skeleton. `atlas: the toy scene probe (numbers only) and the decision record for step 10`.

---

### Task 2: The element ids, the policy masks (pure)

**Files:**
- Modify (game repo): `pc/platform/gw_ui_retail_ids.h`, `gw_ui_retail.c` (step 3's), `gw_ui_policy.h/.c`, `pc/tests/atlas_retail_test.c`, `pc/tests/atlas_policy_test.c`

**Interfaces:** Consumes step 3's `AtRetail`, `at_retail_name`, `at_retail_script_allowed`, `at_retail_effective`; step 2's `at_policy_for`. Produces the new ids, `at_policy_mask(kind, atlas_on, env, text_ok)`, `at_policy_screen_for(kind)`.

- [ ] **Step 1: Write the failing tests.** Append to `atlas_retail_test.c` (RECONCILE the helper names if step 3's file differs):

```c
    /* step 10: the bespoke scenes' ids: toy panels, the info panel, text, the lottery's panel and text; policy-only */
    { unsigned toy = (1u << AT_RE_TOY_PANEL) | (1u << AT_RE_TOY_INFO) | (1u << AT_RE_TOY_TEXT) | (1u << AT_RE_LOT_PANEL) | (1u << AT_RE_LOT_TEXT);
      AtRetail r; memset(&r, 0, sizeof r);
      CHECK(AT_RE_COUNT <= 32);
      CHECK_STR(at_retail_name(AT_RE_TOY_PANEL), "toy.panel"); CHECK_STR(at_retail_name(AT_RE_TOY_INFO), "toy.info");
      CHECK_STR(at_retail_name(AT_RE_TOY_TEXT), "toy.text"); CHECK_STR(at_retail_name(AT_RE_LOT_PANEL), "lot.panel"); CHECK_STR(at_retail_name(AT_RE_LOT_TEXT), "lot.text");
      CHECK((at_retail_script_allowed() & toy) == 0);                       /* a mod may never hide a bespoke scene's element */
      at_retail_set(&r, AT_RS_POLICY, toy);
      CHECK(at_retail_hidden(&r, AT_RE_TOY_PANEL, 0) && at_retail_hidden(&r, AT_RE_LOT_TEXT, 0));
      CHECK(!at_retail_hidden(&r, AT_RE_HUD_DAMAGE, 0));                    /* nothing else moved */
      CHECK(!at_retail_hidden(&r, AT_RE_TOY_PANEL, 1));                     /* online: shown, always */
      { unsigned m = 0; char err[64]; CHECK(at_retail_parse("toy.panel,lot.text", &m, err, sizeof err) == 0 /* RECONCILE: step 3's success convention */ && m == ((1u << AT_RE_TOY_PANEL) | (1u << AT_RE_LOT_TEXT))); } }
```

and to `atlas_policy_test.c`:

```c
    /* step 10: every scene is RETAIL by default; an env override turns one on; the mask follows only an OVERLAY */
    CHECK(at_policy_for(11, 1, NULL) == AT_POLICY_RETAIL);                   /* GS_TOY_GALLERY */
    CHECK(at_policy_for(11, 1, "11:overlay") == AT_POLICY_OVERLAY);
    CHECK(at_policy_mask(11, 1, NULL, 1) == 0);                              /* retail: no mask */
    CHECK(at_policy_mask(11, 0, "11:overlay", 1) == 0);                      /* MELEE_ATLAS=0 beats everything */
    CHECK(at_policy_mask(11, 1, "11:overlay", 1) == ((1u << AT_RE_TOY_PANEL) | (1u << AT_RE_TOY_INFO) | (1u << AT_RE_TOY_TEXT)));
    CHECK(at_policy_mask(11, 1, "11:overlay", 0) == ((1u << AT_RE_TOY_PANEL) | (1u << AT_RE_TOY_INFO)));   /* text not decodable: the retail text stays */
    CHECK(at_policy_mask(12, 1, "12:overlay", 1) == ((1u << AT_RE_LOT_PANEL) | (1u << AT_RE_LOT_TEXT)));    /* GS_TOY_LOTTERY */
    CHECK(at_policy_mask(13, 1, "13:overlay", 1) != 0);                                                     /* GS_TOY_COLLECTION */
    CHECK(at_policy_mask(0, 1, NULL, 1) == 0);                                                              /* the title: an overlay with no mask */
    CHECK_STR(at_policy_screen_for(11), "toy.gallery"); CHECK_STR(at_policy_screen_for(12), "toy.lottery"); CHECK_STR(at_policy_screen_for(13), "toy.collection");
    CHECK(at_policy_screen_for(5) == NULL);                                                                  /* results: step 8's REPLACE, no chrome id */
    /* the owner-skipped scenes never get a mask or a chrome id, whatever the override says about their policy */
    { int skipped[] = { 0x1C /* GS_MOVIE_OPENING */, 0x1D, 0x1E, 0x1F, 0x2B /* GS_STAFFROLL */, 0x2A /* GS_MEMCARD */ }; int i;
      for (i = 0; i < 6; i++) { CHECK(at_policy_mask(skipped[i], 1, NULL, 1) == 0); CHECK(at_policy_screen_for(skipped[i]) == NULL); } }
```

(`GS_TOY_GALLERY` is `0x0B` = 11, `GS_TOY_LOTTERY` `0x0C` = 12, `GS_TOY_COLLECTION` `0x0D` = 13 in `gm/forward.h:100-102`; the game side asserts them with `_Static_assert` next to step 2's title one, Task 4 step 4.)
- [ ] **Step 2: Run to see them fail** (`nt atlas-retail`, `nt atlas-policy`).
- [ ] **Step 3: The ids.** In `gw_ui_retail_ids.h` (step 3), before `AT_RE_COUNT`: `AT_RE_TOY_PANEL = 9, AT_RE_TOY_INFO = 10, AT_RE_TOY_TEXT = 11, AT_RE_LOT_PANEL = 12, AT_RE_LOT_TEXT = 13, AT_RE_COUNT = 14` and comments naming the retail pieces: `TOY_PANEL`: the 2D panel GObjs at GX links `0x33` and `0x3C` (`toy.c:2488`, `2423`); `TOY_INFO`: the info SObj `TyMnInfo` at link `0x38` (`toy.c:2585`); `TOY_TEXT`: the name, description and series `HSD_Text` objects (`display->x144..x150`, `toy.c:2900-3000`); `LOT_PANEL`, `LOT_TEXT`: the Lottery's equivalents (read in Task 7). **The ids are the candidate list; Task 1 step 2(e) and the per-screen tasks prune or extend it, and the tests above change with it.** In `gw_ui_retail.c` add the five names to the name table; `at_retail_script_allowed()` stays "everything but `hud.timer` **and the toy and lot ids**": clear those bits in its return.
- [ ] **Step 4: The policy.** In `gw_ui_policy.h` add:

```c
/* the retail 2D pieces a bespoke scene hides while Atlas frames it (retail element ids, gw_ui_retail_ids.h), and the chrome screen's id */
unsigned at_policy_mask(int scene_kind, int atlas_on, const char *env_override, int text_ok);
const char *at_policy_screen_for(int scene_kind);   /* the overlay screen id for a scene that has one (default row or not), else NULL */
```

and in `gw_ui_policy.c` (step 2's `ROWS[]` stays the **defaults**; a second table says what each bespoke scene would hide and call itself if an OVERLAY is chosen):

```c
#include "gw_ui_retail_ids.h"
#define AT_SCENE_TOY_GALLERY 11
#define AT_SCENE_TOY_LOTTERY 12
#define AT_SCENE_TOY_COLLECTION 13
static const struct { int kind; unsigned mask; unsigned text_bits; const char *screen; } BESPOKE[] = {
    { AT_SCENE_TOY_GALLERY,    (1u << AT_RE_TOY_PANEL) | (1u << AT_RE_TOY_INFO) | (1u << AT_RE_TOY_TEXT), 1u << AT_RE_TOY_TEXT, "toy.gallery" },
    { AT_SCENE_TOY_LOTTERY,    (1u << AT_RE_LOT_PANEL) | (1u << AT_RE_LOT_TEXT),                         1u << AT_RE_LOT_TEXT, "toy.lottery" },
    { AT_SCENE_TOY_COLLECTION, (1u << AT_RE_TOY_PANEL) | (1u << AT_RE_TOY_INFO) | (1u << AT_RE_TOY_TEXT), 1u << AT_RE_TOY_TEXT, "toy.collection" },
};
unsigned at_policy_mask(int kind, int atlas_on, const char *env, int text_ok)
{
    size_t i;
    if (at_policy_for(kind, atlas_on, env) != AT_POLICY_OVERLAY) return 0;
    for (i = 0; i < sizeof BESPOKE / sizeof BESPOKE[0]; i++)
        if (BESPOKE[i].kind == kind) return text_ok ? BESPOKE[i].mask : BESPOKE[i].mask & ~BESPOKE[i].text_bits;
    return 0;
}
const char *at_policy_screen_for(int kind)
{
    size_t i;
    for (i = 0; i < sizeof BESPOKE / sizeof BESPOKE[0]; i++) if (BESPOKE[i].kind == kind) return BESPOKE[i].screen;
    return at_policy_screen(kind);   /* the title's "title" */
}
```

(The title's `at_policy_screen(0)` is `"title"`; the test `at_policy_screen_for(5) == NULL` holds because results is not in `ROWS`.)
- [ ] **Step 5: Run to pass.** `nt atlas-retail`, `nt atlas-policy`; and `atlas-hud` / `atlas-binding` (they include step 3's ids): all still pass. The three scene rows are **not** in `ROWS[]`: no default changed.
- [ ] **Step 6: Commit (game repo).** `atlas: retail element ids for the bespoke scenes and a per-scene mask table (policy only, nothing on by default)`.

---

### Task 3: The `frame` screen: window, plates, chrome slots (pure)

**Files:**
- Create (game repo): `pc/platform/gw_ui_frame.h/.c`, `pc/tests/atlas_frame_test.c`
- Modify (game repo): `pc/platform/gw_ui_screen.h` (`AT_PRIMARY_FRAME`, `AtScreen.frame`), `gw_ui_render.c` (the branch), `pc/tests/atlas_render_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-frame`)

**Interfaces:** `AtFrameRect` (the window, in the 640x480 retail canvas), `at_frame_hole`, `at_frame_plates`, `at_frame_slots`. `AtScreen` gains `frame` (the window) and `AT_PRIMARY_FRAME`.

- [ ] **Step 1: Write the failing tests** `pc/tests/atlas_frame_test.c`:

```c
#include "atlas_check.h"
#include "atlas_fake.h"
#include "../platform/gw_ui_frame.h"

static float area(AtRect r) { return r.w > 0 && r.h > 0 ? r.w * r.h : 0.0f; }
static int overlaps(AtRect a, AtRect b) { return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h && area(a) > 0 && area(b) > 0; }

int main(void)
{
    AtLayout L; AtFrameRect win = { 200, 90, 240, 260 }; AtRect hole, pl[4]; int n, i, j; float sum;
    static const float widths[3] = { 640.0f, 853.0f, 1140.0f };
    for (i = 0; i < 3; i++) {
        at_layout(widths[i], AT_PRESET_NORMAL, &L);
        hole = at_frame_hole(&L, win);
        CHECK_NEAR(hole.x, 200.0f + (widths[i] - 640.0f) * 0.5f);          /* the 4:3 band centred (assumption of correction 2) */
        CHECK_NEAR(hole.y, 90.0f); CHECK_NEAR(hole.w, 240.0f); CHECK_NEAR(hole.h, 260.0f);
        n = at_frame_plates(&L, win, pl);
        CHECK(n == 4);
        sum = 0.0f;
        for (j = 0; j < n; j++) { sum += area(pl[j]); CHECK(!overlaps(pl[j], hole)); }
        CHECK_NEAR(sum, widths[i] * 480.0f - hole.w * hole.h);             /* plates plus the hole are exactly the canvas */
        for (j = 1; j < n; j++) { int k; for (k = 0; k < j; k++) CHECK(!overlaps(pl[j], pl[k])); }
    }
    /* a window touching the left edge gives no left plate; a full-canvas window gives none at all */
    at_layout(640.0f, AT_PRESET_NORMAL, &L);
    { AtFrameRect w2 = { 0, 90, 300, 260 }; CHECK(at_frame_plates(&L, w2, pl) == 3); }
    { AtFrameRect w3 = { 0, 0, 640, 480 }; CHECK(at_frame_plates(&L, w3, pl) == 0); }

    /* chrome slots: trail and keys at the top and bottom plates, the explainer in the wider side plate; nothing silently overlaps the hole */
    { AtFrameSlots s; AtFrameRect w4 = { 40, 70, 330, 350 };               /* the window left of centre: the right plate is wide */
      at_layout(640.0f, AT_PRESET_NORMAL, &L); at_frame_slots(&L, w4, 160.0f, &s);
      hole = at_frame_hole(&L, w4);
      CHECK(!s.explainer_overlaps && s.have_explainer && s.explainer.x >= hole.x + hole.w && s.explainer.w >= 160.0f);
      CHECK(s.have_trail && !overlaps(s.trail, hole));
      CHECK(s.have_keys && !overlaps(s.keys, hole)); }
    { AtFrameSlots s; AtFrameRect w5 = { 120, 60, 400, 380 };              /* wide window: no side plate fits the explainer; keys would hit the hole */
      at_layout(640.0f, AT_PRESET_NORMAL, &L); at_frame_slots(&L, w5, 160.0f, &s);
      hole = at_frame_hole(&L, w5);
      CHECK(s.explainer_overlaps && s.have_explainer);                       /* a card over the hole's corner, and it says so */
      CHECK(!s.have_keys);                                                   /* a slot that would sit on the model is dropped, not overlapped */ }
    { AtFrameSlots s; AtFrameRect w6 = { 0, 0, 640, 480 };
      at_layout(640.0f, AT_PRESET_NORMAL, &L); at_frame_slots(&L, w6, 160.0f, &s);
      CHECK(!s.have_trail && !s.have_keys && s.explainer_overlaps); }        /* a full-canvas window: only the overlap card can exist */
    /* at 16:9 the side plates grow: the explainer that overlapped at 640 fits */
    { AtFrameSlots s; AtFrameRect w7 = { 120, 60, 400, 380 };
      at_layout(1140.0f, AT_PRESET_NORMAL, &L); at_frame_slots(&L, w7, 160.0f, &s);
      CHECK(!s.explainer_overlaps && s.have_explainer); }
    ATLAS_DONE("atlas frame");
}
```

Register `atlas-frame)` with `sources=(pc/tests/atlas_frame_test.c pc/platform/gw_ui_frame.c pc/platform/gw_ui_layout.c)`.
- [ ] **Step 2: Run to see them fail** (`nt atlas-frame`: the header is missing).
- [ ] **Step 3: Implement.** `gw_ui_frame.h`:

```c
/* gw_ui_frame.h - a framed screen: Atlas chrome around a window onto a retail scene. Pure C. */
#ifndef GW_UI_FRAME_H
#define GW_UI_FRAME_H
#include "gw_ui_layout.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct { float x, y, w, h; } AtFrameRect;               /* the window in the 640x480 retail canvas: where retail's camera frames its model */
typedef struct { AtRect trail, explainer, keys; int have_trail, have_explainer, have_keys, explainer_overlaps; } AtFrameSlots;

/* The window on the arranged canvas. ASSUMPTION (correction 2, settled by Task 1): the retail 640x480 picture is a 4:3 band centred in a wider canvas. */
AtRect at_frame_hole(const AtLayout *L, AtFrameRect win);
/* The opaque plates around the hole: top, bottom, left, right in that order, only those with room. Returns the count; together with the hole they tile the canvas exactly. */
int at_frame_plates(const AtLayout *L, AtFrameRect win, AtRect out[4]);
/* Where each chrome slot goes. A slot that would intersect the hole is dropped (trail, keys) or becomes a card over the hole's corner (explainer) and says so. */
void at_frame_slots(const AtLayout *L, AtFrameRect win, float explainer_w, AtFrameSlots *out);
#ifdef __cplusplus
}
#endif
#endif
```

`gw_ui_frame.c`:

```c
#include "gw_ui_frame.h"
#include <string.h>

AtRect at_frame_hole(const AtLayout *L, AtFrameRect w)
{
    AtRect r;
    float band = L->canvas.w > 640.0f ? (L->canvas.w - 640.0f) * 0.5f : 0.0f;
    r.x = w.x + band; r.y = w.y; r.w = w.w; r.h = w.h;
    return r;
}

int at_frame_plates(const AtLayout *L, AtFrameRect win, AtRect out[4])
{
    AtRect h = at_frame_hole(L, win), c; int n = 0;
    c.x = 0.0f; c.y = 0.0f; c.w = L->canvas.w; c.h = 480.0f;
    {   AtRect top = { 0.0f, 0.0f, c.w, h.y };                         if (top.h > 0.5f) out[n++] = top; }
    {   AtRect bot = { 0.0f, h.y + h.h, c.w, 480.0f - (h.y + h.h) };   if (bot.h > 0.5f) out[n++] = bot; }
    {   AtRect lef = { 0.0f, h.y, h.x, h.h };                          if (lef.w > 0.5f) out[n++] = lef; }
    {   AtRect rig = { h.x + h.w, h.y, c.w - (h.x + h.w), h.h };       if (rig.w > 0.5f) out[n++] = rig; }
    return n;
}

static int hits(AtRect a, AtRect b) { return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h; }

void at_frame_slots(const AtLayout *L, AtFrameRect win, float ew, AtFrameSlots *s)
{
    AtRect h = at_frame_hole(L, win);
    float left_w = h.x, right_w = L->canvas.w - (h.x + h.w);
    memset(s, 0, sizeof *s);
    s->trail = L->header;                 /* the retail-independent places of step 1's layout */
    s->keys = L->keys;
    s->have_trail = !hits(s->trail, h);
    s->have_keys = !hits(s->keys, h);
    /* the explainer: the wider side plate if it holds the preset, else a card over the hole's bottom-right corner */
    if (right_w >= left_w && right_w >= ew + 16.0f) {
        s->explainer.x = h.x + h.w + 8.0f; s->explainer.w = right_w - 16.0f > ew ? ew : right_w - 16.0f; s->have_explainer = 1;
    } else if (left_w >= ew + 16.0f) {
        s->explainer.x = 8.0f; s->explainer.w = ew; s->have_explainer = 1;
    } else {
        s->explainer.w = ew; s->explainer.x = h.x + h.w - ew - 8.0f; s->explainer_overlaps = 1; s->have_explainer = 1;
    }
    s->explainer.y = s->explainer_overlaps ? h.y + h.h - 150.0f - 8.0f : (h.y > L->body.y ? h.y : L->body.y);
    s->explainer.h = 150.0f;
}
```

(The numbers 150 and 8 are placeholders of the card's height and gap that Task 5 replaces with the explainer part's measured height; `atlas_frame_test.c` pins only the structure. Check the tests by hand against this code: the `w4` case: hole.x = 40, hole.w = 330 -> right plate `640 - 370 = 270 >= 176` -> explainer on the right (ok); the top plate height 70, the `L->header` rect (y 22, h 30) lies in it (ok), the keys rect at y 434..460 vs hole bottom 420 (ok) no hit. The `w5` case: hole 120..520 x 60..440: keys at 434..460 hit the hole (440 > 434) -> dropped (ok); left_w 120, right_w 120, both < 176 -> overlap card (ok). The full-canvas case: header and keys hit the hole -> dropped (ok), explainer overlap (ok). The 1140 case: band 250; hole.x = 370, hole.w = 400, right plate `1140 - 770 = 370 >= 176` (ok).)
- [ ] **Step 4: The screen record and the render branch.** In `gw_ui_screen.h`: `AT_PRIMARY_FRAME` (RECONCILE the next free number: step 3 has `AT_PRIMARY_CARDS = 5`; steps 4 and 5 may take 6 and 7) and in `AtScreen`: `int has_frame; float frame_x, frame_y, frame_w, frame_h;` (the window). In `gw_ui_render.c` before the ground fill (line ~295): `if (sc->primary == AT_PRIMARY_FRAME) { render_frame(...); return; }` where `render_frame` draws **no ground**, draws each plate from `at_frame_plates` as an E1 pane in `AT_C_PLATE` with the 3 px front edge and 8 px chamfer on the corners that border the screen's own edge **only on the outside** (a plate's chamfer must not cut into the hole: keep the hole's side square), then the trail, the explainer (the existing `at_part_explainer`) and the keys (`at_part_hint`) in their slots, and **records no hits** (`hits->n = 0`). Add to `atlas_render_test.c`:

```c
    /* a framed screen: no ground quad, plates outside the hole only, no hit rectangles, nothing inside the hole */
    { AtScreen sc; AtView v; AtHits hits; AtSink s = rec_sink(); AtLayout L; AtRect hole;
      memset(&sc, 0, sizeof sc); at_view_init(&v);
      sc.primary = AT_PRIMARY_FRAME; sc.has_frame = 1; sc.frame_x = 200; sc.frame_y = 90; sc.frame_w = 240; sc.frame_h = 260;
      snprintf(sc.id, sizeof sc.id, "toy.test"); snprintf(sc.title, sizeof sc.title, "GALLERY");
      sc.n_keys = 1; sc.keys[0].btn = 'B'; snprintf(sc.keys[0].label, AT_STR, "Back");
      at_layout(853.0f, AT_PRESET_NORMAL, &L); hole = at_frame_hole(&L, (AtFrameRect) { 200, 90, 240, 260 });
      memset(&hits, 0, sizeof hits);
      at_render(&sc, &v, 853.0f, 10000.0, 1, &FAKE, &s, &hits);
      CHECK(hits.n == 0);
      CHECK(count_color(AT_C_GROUND) == 0);                                  /* no ground: the retail scene shows through the hole and the retail band beside it is covered by plates */
      { int i; for (i = 0; i < REC.np; i++) { AtRect q = { poly_minx(&REC.p[i]), poly_miny(&REC.p[i]), poly_maxx(&REC.p[i]) - poly_minx(&REC.p[i]), poly_maxy(&REC.p[i]) - poly_miny(&REC.p[i]) };
          CHECK(!(q.x < hole.x + hole.w - 0.5f && hole.x < q.x + q.w - 0.5f && q.y < hole.y + hole.h - 0.5f && hole.y < q.y + q.h - 0.5f)); } }   /* not one quad inside the hole */
      CHECK(texts_legible()); }
```

(`rec_sink`, `REC`, `count_color`, `poly_*`, `texts_legible` are in `atlas_rec.h`; the helpers `at_layout` and `at_frame_hole` need `gw_ui_frame.c` and `gw_ui_layout.c` added to the `atlas-render` sources in `native_test.sh`. If step 6's lint helpers are merged, also run `lint_chamfers` on the plates; RECONCILE their signature.)
- [ ] **Step 5: Run to pass.** `nt atlas-frame`, `nt atlas-render`, and every other `atlas-*` case (the new primary must not change a list or tiles screen).
- [ ] **Step 6: Commit.** Game repo: the unit, the screen field, the render branch, the tests. Workspace repo: `native_test.sh`. `atlas: the frame screen (a window onto a retail scene, plates around it, chrome slots that never silently overlap it)`.

---

### Task 4: The overlay hook, the policy wiring and the online guard

**Files:**
- Modify (game repo): `src/melee/gm/gm_1A3F.c`, `pc/platform/gw_script_ui.inc`, `src/melee/gm/gmfrontend_atlas.inc` (the stand-in neighbour for `_Static_assert`s), create the shim part of `gmfrontend_atlas_toy.inc`
- Create (workspace repo): `tools/port/test_overlay_hook.py`

**Interfaces:** Produces `Fad_OverlayWrap(kind, inner)` (game side), `gw_Ui_FrameBegin(id, title, x, y, w, h)` (host), the scene-begin mask wiring (host).

- [ ] **Step 1: Write the static guard first** `tools/port/test_overlay_hook.py`:

```python
"""Static guards on the OVERLAY hook for bespoke scenes. python -m unittest tools/port/test_overlay_hook.py"""
import os, re, unittest
ROOT = os.environ.get("GW_MELEE", "")
def read(rel): return open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()

class Hook(unittest.TestCase):
    def test_inner_on_frame_runs_first_and_always(self):
        t = read("src/melee/gm/gmfrontend_atlas_toy.inc")
        body = t[t.index("static void fat_overlay_frame"):]; body = body[:body.index("\n}\n")]
        self.assertLess(body.index("fat_inner"), body.index("fat_submit"), "the retail on_frame must run before the chrome is submitted")
        self.assertNotRegex(body, r"if\s*\(.*\)\s*return\s*;\s*\n\s*fat_inner", "an early return would skip the retail frame")
    def test_no_pad_and_no_hits(self):
        t = read("src/melee/gm/gmfrontend_atlas_toy.inc")
        self.assertNotIn("Ui_Intent", t); self.assertNotIn("Ui_PollEvent", t)
        self.assertIn("input_feed", read("pc/platform/gw_script_ui.inc"))
    def test_wrapper_only_under_overlay_and_target_pc(self):
        g = read("src/melee/gm/gm_1A3F.c")
        i = g.index("Fad_OverlayWrap"); window = g[max(0, i - 300):i + 200]
        self.assertIn("TARGET_PC", g[:i][-1500:]); self.assertRegex(window, r"AT_POLICY_OVERLAY|== 1")
    def test_online_guard(self):
        t = read("src/melee/gm/gmfrontend_atlas_toy.inc")
        self.assertIn("Ui_NetplayActive", t)
    def test_policy_before_enter(self):
        s = read("src/melee/gm/gmscene.c"); g = read("src/melee/gm/gm_1A3F.c")
        self.assertLess(g.index("gm_801A4B88(info)"), g.index("scene->on_enter(info->enter_data)"))   # SceneBegin (gmscene.c:805) runs in gm_801A4B88, before on_enter
        self.assertIn("Script_SceneBegin", s)
if __name__ == "__main__":
    unittest.main()
```

(Fails until the wrapper and the file exist: expected. The last test pins the ordering the guard approach relies on: the policy mask is set in `Script_SceneBegin`, called from `gmscene.c:805` inside `gm_801A4B88`, which runs **before** `scene->on_enter`, so creation-time guards see the final mask. **(unverified)** that `gm_801A4B88` is the caller of that block: Step 2 confirms it by reading `gmscene.c:790-810`.)
- [ ] **Step 2: Confirm the ordering** by reading `gmscene.c:790-810` and `gm_801A4B88`; if the mask would be set after `on_enter`, move the set into `gm_1A3F.c` right after the policy test and say so in the commit message.
- [ ] **Step 3: The host.** In `gw_script_ui.inc`:
  1. `gw_Ui_SceneBegin(kind)` (step 2's): after `gs_ui_overlay_kind = ...` add `{ unsigned m = at_policy_mask(kind, atlas_env_on(), getenv("MELEE_ATLAS_SCENES"), gs_ui_text_ok(kind)); at_retail_set(&gs_ui_retail, AT_RS_POLICY, m); }` (RECONCILE with step 3's `gs_ui_retail`; `gs_ui_text_ok` reads the step 8 gate result per source: default **0** until step 8 has recorded GO for that source). `gw_Ui_SceneExit(prev)`: `at_retail_set(&gs_ui_retail, AT_RS_POLICY, 0)`.
  2. `gs_ui_overlay_try`: it hard-codes `strcmp(screen, "title")`. Change it to a small table `{ "title", build_title }` and leave bespoke scenes **out of it**: their screens are submitted each frame by the game-side wrapper through `gw_Ui_Begin`/`gw_Ui_FrameBegin`, not pushed once.
  3. `gw_Ui_FrameBegin(id, title, x, y, w, h)`: like `gw_Ui_Begin` but `primary = AT_PRIMARY_FRAME`, `has_frame = 1`, the window, `input_feed = 1` (Atlas reads no pad: retail does).
- [ ] **Step 4: The game side.** In `gm_1A3F.c`, in the `TARGET_PC` block step 2 added (after the `REPLACE` branch):

```c
        {
            extern void (*Fad_OverlayWrap(u8 kind, void (*inner)(void)))(void);
            if (Ui_ScenePolicy(kind) == 1 /* AT_POLICY_OVERLAY */) {
                overlay_frame = Fad_OverlayWrap(kind, scene->on_frame);   /* returns inner itself for a scene that has no chrome */
            }
        }
```

with `void (*overlay_frame)(void) = NULL;` declared with the other locals (under `TARGET_PC`) and the later call `gm_801A4D34(scene->on_frame, info);` becoming, under `TARGET_PC`, `gm_801A4D34(overlay_frame != NULL ? overlay_frame : scene->on_frame, info);`. In `gmfrontend_atlas_toy.inc`:

```c
_Static_assert(GS_TOY_GALLERY == 11 && GS_TOY_LOTTERY == 12 && GS_TOY_COLLECTION == 13, "gw_ui_policy.c AT_SCENE_TOY_* must be these kinds");

static void (*fat_inner)(void);
static u8 fat_kind;
static int fat_online_noted;

/* every frame of the scene: retail first (its own pad polling, logic and exit), then the chrome from readbacks */
static void fat_overlay_frame(void)
{
    if (fat_inner != NULL) {
        fat_inner();
    }
    if (Ui_NetplayActive()) {              /* the mask is 0 online: chrome over unhidden retail 2D would collide */
        if (!fat_online_noted) {
            OSReport("frontend: framed scene %d not drawn: a session is on\n", fat_kind);
            fat_online_noted = 1;
        }
        return;
    }
    fat_submit(fat_kind);
}

void (*Fad_OverlayWrap(u8 kind, void (*inner)(void)))(void)
{
    if (kind != GS_TOY_GALLERY && kind != GS_TOY_LOTTERY && kind != GS_TOY_COLLECTION) {
        return inner;
    }
    fat_inner = inner;
    fat_kind = kind;
    fat_online_noted = 0;
    return fat_overlay_frame;
}
```

`fat_submit(kind)` is filled by Tasks 5 to 7; until then it is `static void fat_submit(u8 kind) { (void) kind; }` so the wrapper links and the guard test passes. Include `gmfrontend_atlas_toy.inc` from `gmfrontend.c` after `gmfrontend_atlas_data.inc`; add `Ui_Counter` etc. externs there.
- [ ] **Step 5: The outline (development aid, no screenshot).** `MELEE_ATLAS_FRAME_OUTLINE=1` makes the frame screen draw the hole's border (4 thin ember quads) so the window can be compared with where retail puts the model **by looking**, and `MELEE_ATLAS_FRAME_WIN=x,y,w,h` overrides the window rectangle for tuning (the committed constants of Tasks 5 to 7 come from this). Both are read once in `gw_Ui_FrameBegin`. Add a test to `atlas_render_test.c`: with the outline flag set the frame screen has exactly eight more thin polys and still none inside the hole... (the outline is on the border: allow polys that **touch** but do not enter the hole by more than 1 px).
- [ ] **Step 6: Run** `python -m unittest tools/port/test_overlay_hook.py` (all pass once Step 4 is done), PowerPC syntax check of `gm_1A3F.c` and `gmfrontend.c` (the form step 2 and step 6 used), `nt atlas-render`, `nt atlas-policy`, `nt atlas-retail`.
- [ ] **Step 7: Commit.** Game repo: `atlas: OVERLAY for bespoke scenes (a per-frame wrapper after the retail on_frame, the policy mask set at scene begin and cleared at exit, no chrome online)`; workspace repo: the guard.

---

### Task 5: The Trophy Gallery (go or no-go on its own)

**Files:**
- Modify (game repo): `src/melee/gm/gmfrontend_atlas_toy.inc` (readbacks, builder, window constant, guard helpers), `src/melee/ty/toy.c` (the creation-site guards), `pc/platform/gw_ui_frame.c` and `gw_ui_data_models.c` (a pure chrome model `at_toy_chrome`), `pc/tests/atlas_models_test.c` (or a new `atlas_toy_test.c`)
- Create (workspace repo): `tools/port/test_toy_guards.py`

Retail facts read: the scene is `GS_TOY_GALLERY` (11): `Toy_Scene_OnEnter` (`toy.c:6421`) sets up the SIS tables (font slot 0 `SdToy`, slot 3 `SdToyExp`, `toy.c:6513-6526`), allocates the scene's data, runs `Toy_80310324` (the build-up: archives `TyMnView`, `TyMnBg`, `TyMnInfo`, `TyDatai`, `TyStand`, `TyLight`) and the music; `Toy_Scene_OnFrame` (`toy.c:6568`) leaves when `TyModeState.x4 != 0` (`gm_801A4B60()`). Pad: polled directly (`HSD_PadCopyStatus`, `toy.c:1429-1491`). State: the selection `*TOY_SEL` (`s16`), its id `*TOY_SELID`, the count `*TOY_COUNT` (the owned count in 1P and the lottery, else `*gmMainLib_GetTrophyCount()`, `toy.c:6470-6480`). Text: name from `Toy_803063D4(id, 2, 0x128)` (slot 0), description `Toy_803063D4(id, 2, 0x374)` (slot 3), two more lines `(id, 0x128, 0x37A)` and `(id, 0x24E, 0x380)` (slot 3) (`toy.c:2936-3000`). The text objects are created once and re-pointed per trophy (`HSD_SisLib_803A6368`).

- [ ] **Step 1: The pure chrome model, failing test first** (`atlas_toy_test.c`, case `atlas-toy`, sources `gw_ui_data_models.c`, `gw_ui_data.c`, `gw_ui_screen.c`, `gw_ui_val.c`, `gw_ui_focus.c`):

```c
#include "atlas_check.h"
#include "../platform/gw_ui_data_models.h"

int main(void)
{
    AtToyChrome c; char b[64];
    /* the counter and the authored fallbacks when no retail text could be decoded */
    at_toy_chrome(&c, 6, 293, "", "", "");
    CHECK_STR(c.counter, "7 / 293"); CHECK_STR(c.title, "TROPHY 7"); CHECK(c.what[0] == '\0'); CHECK(c.from[0] == '\0');
    /* decoded text wins, clipped to the explainer's limits (title 64, what 110) */
    at_toy_chrome(&c, 0, 1, "Invented Trophy", "A short invented description.", "Invented series");
    CHECK_STR(c.title, "Invented Trophy"); CHECK_STR(c.what, "A short invented description."); CHECK_STR(c.from, "Invented series"); CHECK_STR(c.counter, "1 / 1");
    { char longd[200]; int i; for (i = 0; i < 199; i++) longd[i] = 'a' + i % 26; longd[199] = 0;
      at_toy_chrome(&c, 0, 5, "T", longd, ""); CHECK(strlen(c.what) <= 110); }
    /* the edges: nothing owned, the index past the count (an m-ex trophy), a negative index */
    at_toy_chrome(&c, 0, 0, "", "", "");   CHECK_STR(c.counter, "");  CHECK_STR(c.title, "NO TROPHIES YET");
    at_toy_chrome(&c, 299, 293, "", "", ""); CHECK_STR(c.counter, "293 / 293");                               /* clamped to the last */
    at_toy_chrome(&c, -3, 293, "", "", "");  CHECK_STR(c.counter, "1 / 293");
    /* only the first sentence of a description is the rule line */
    at_toy_chrome(&c, 0, 3, "T", "First sentence. Second sentence here.", ""); CHECK_STR(c.what, "First sentence.");
    (void) b;
    ATLAS_DONE("atlas toy");
}
```

- [ ] **Step 2: Implement** `AtToyChrome { char title[64], what[112], from[64], counter[24]; }` and `at_toy_chrome(c, index, count, name, desc, series)` in `gw_ui_data_models.c`: index clamped to `[0, count-1]`; count 0 gives the title `NO TROPHIES YET` and an empty counter; an empty name gives `TROPHY n`; the rule line is the first sentence of `desc` (up to and including the first `.`, `!` or `?` followed by a space or the end) clipped to 110 characters with an ellipsis; `from` is the series text clipped to 63.
- [ ] **Step 3: The readbacks and the builder** (game side, `gmfrontend_atlas_toy.inc`):

```c
/* the Gallery's chrome: the window is where TyMnView frames the trophy at 640x480 (numbers measured with MELEE_ATLAS_FRAME_OUTLINE, Task 4 step 5; unverified until then) */
static const float FAT_GALLERY_WIN[4] = { 0.0f, 0.0f, 0.0f, 0.0f };   /* x y w h: REPLACE with the measured rectangle; zero means "do not draw" and the probe says so */

static void fat_gallery_submit(void)
{
    char name[64], desc[160], series[64];
    int id = (int) *TOY_SELID, idx = (int) *TOY_SEL, count = (int) *TOY_COUNT;
    name[0] = desc[0] = series[0] = '\0';
    if (FAT_GALLERY_WIN[2] <= 0.0f) {
        return;                                       /* the window is unmeasured: draw nothing rather than guess */
    }
    if (fat_text_ok) {                                /* step 8's gate for SdToy and SdToyExp */
        fat_sis_text2("SdToy", "SIS_ToyData_E", Toy_803063D4(id, 2, 0x128), name, sizeof name);
        fat_sis_text2("SdToyExp", "SIS_ToyDataExp_E", Toy_803063D4(id, 2, 0x374), desc, sizeof desc);
        fat_sis_text2("SdToyExp", "SIS_ToyDataExp_E", Toy_803063D4(id, 0x128, 0x37A), series, sizeof series);
    }
    Ui_FrameBegin("toy.gallery", "GALLERY", FAT_GALLERY_WIN[0], FAT_GALLERY_WIN[1], FAT_GALLERY_WIN[2], FAT_GALLERY_WIN[3]);
    Ui_Trail("MAIN MENU");
    Ui_Trail("COLLECTION");
    Ui_ToyChrome(idx, count, name, desc, series);     /* the host builds AtToyChrome and fills the explainer and the counter */
    Ui_Key('B', "Back");                              /* retail's own keys are read from its scene: Step 1 below */
    Ui_Commit(-1, -1);
}
```

`fat_sis_text2(archive, symbol, sis, out, cap)` is step 8's `fad_sis_text` generalised to the archive name and symbol (add a `static` cache per archive; use the saved-language `.usd`/`.dat` rule as `toy.c:6519` does; return 0 and an empty buffer when any glyph is unknown). `Ui_ToyChrome` is a host shim that calls `at_toy_chrome` and then `gw_Ui_Explain` and `gw_Ui_Counter`. `fat_text_ok` is set on scene entry from the gate (`Ui_TextOk(kind)`).
- [ ] **Step 4: Read the retail keys and fix `Ui_Key`.** The Gallery's inputs are read directly from `HSD_PadCopyStatus` (`toy.c:1429-1491`); read what A, B, X, Y, the sticks and L/R do (rotate, zoom, previous/next series, back) and list **exactly those** as key hints. The hints are information only. Write them into the commit message; no hint for something retail does not do.
- [ ] **Step 5: The guards, creation-time, one line each** (`toy.c`; `TARGET_PC`; pattern from step 3, RECONCILE the helper name):

```c
#if defined(TARGET_PC)
extern int Ui_RetailHidden(int id);
static GObj_RenderFunc Toy_GuardRender(int id, GObj_RenderFunc cb)
{
    extern void Toy_NoRender(HSD_GObj*, int);   /* defined in toy.c: an empty render callback with the right signature */
    return Ui_RetailHidden(id) ? (GObj_RenderFunc) Toy_NoRender : cb;
}
#endif
```

applied at the **creation** sites **only for the pieces Task 1 found inside the window**: candidates `toy.c:2423` (`tg->x0`, link `0x3C`, `HSD_GObj_JObjCallback`), `toy.c:2488` (`td->gobj`, link `0x33`), `toy.c:2586` (`data->x0C`, link `0x38`, `HSD_SObjLib_803A49E0`: the info panel) as `GObj_SetupGXLink(td->gobj, Toy_GuardRender(AT_RE_TOY_PANEL, HSD_GObj_JObjCallback), 0x33, 0)`; for the text objects, after creating each of `display->x144`, `x148`, `x14C`, `x150` (`toy.c:2910-2990`): `if (Ui_RetailHidden(AT_RE_TOY_TEXT)) { display->x144->hidden = 1; }`. **Do not** touch the viewer's render (`_Toy_80312050`, link `0x39`), the stand, the lights or `TyMnBg` (`0x32`): they are the retail 3D and its backdrop. A render guard replaces the callback pointer only; the proc, the animation and the object's state are exactly retail's.
- [ ] **Step 6: The guard test** `tools/port/test_toy_guards.py`: for `toy.c`, `tydisplay.c`, `tyfigupon.c` every line that mentions `Ui_RetailHidden` or `Toy_GuardRender` is (a) under `TARGET_PC`, (b) inside a creation statement (`GObj_SetupGXLink`, `HSD_SisLib_803A5ACC` neighbour) and **not inside a function whose name ends in `Proc`/is set up by `HSD_GObj_SetupProc`**; no `Ui_RetailHidden` appears within a proc body (the proc list is found by the `HSD_GObj_SetupProc(` calls in the same file); the Lottery's popup creation sites (named in Task 7) have **no** guard.
- [ ] **Step 7: Run** `nt atlas-toy`, `python -m unittest tools/port/test_toy_guards.py tools/port/test_overlay_hook.py`, `python tools/port/check_no_disc_text.py`, the PowerPC syntax check of `toy.c` and `gmfrontend.c`.
- [ ] **Step 8: Commit.** `atlas: Trophy Gallery chrome (readbacks, a chrome model, creation-time guards for the pieces inside the window); the window constant is unmeasured and draws nothing until Task 11 sets it`.

---

### Task 6: The Collection (the trophy room)

**Files:** modify `gmfrontend_atlas_toy.inc`, `tydisplay.c`, `atlas_toy_test.c`; extend `test_toy_guards.py`.

Retail facts: `GS_TOY_COLLECTION` (13): `tyDisplay_Scene_OnEnter` (`tydisplay.c:1801`) builds the room from `TyMnDisp` and the per-series trophy archives (`Mycc`, `Map`, `Seri`, `Etc`, `Poke`, `Item` sets, `tydisplay.c:1255-1260, 1861-1883`), pad via `Toy_80305C44()`/`Toy_80305B88()` (button state), camera and cursor in `TyDspConfig` (`cfg->x20/x24` stick values); exit like the Gallery (`tydisplay.c:1993`, `state->x4`). **Where the cursor's trophy id lives is not read: (unverified).**

- [ ] **Step 1: Find the cursor's trophy.** Read `tydisplay.c` 1500-1700 (the cursor and selection code, `TyDspGrid`, `grid->sort[]`, `Toy_803087F4`) and `Toy_8030xxxx` helpers; write down in the commit message the expression for "the trophy under the cursor" (an index into `grid->sort[].key`, or `*TOY_SELID`). **If there is none** (the cursor is only a camera position), the Collection chrome shows the series and counts only (`SHELF n`, total trophies) and no per-trophy explainer: say so.
- [ ] **Step 2: The builder and the window.** A second constant `FAT_COLLECTION_WIN` (measured, Task 11), the chrome from `at_toy_chrome` with the cursor's trophy if found, else the authored `COLLECTION` and `n trophies`. **The retail room fills the screen** (spec): expect the window to be large and the explainer to be the overlap card (Task 3 handles it and flags it). If the measured window leaves no plate room, **this screen's decision is probably drop**: the outcome is recorded, not forced.
- [ ] **Step 3: Guards** for the pieces inside the window (candidates: `tydisplay.c:1671` `ptr->gobj4` link `0x3C`, `2205` link `0x3C`): same pattern, `AT_RE_TOY_PANEL`; no guard on the room, the shelves, the camera or the models.
- [ ] **Step 4: Tests** in `atlas_toy_test.c`: the empty shelf (count 0), one trophy, the cursor past the count, and the chrome with no per-trophy text; extend the guard test to `tydisplay.c`.
- [ ] **Step 5: Commit.** `atlas: Collection chrome (cursor readback found in Step 1, the room's own camera and shelves untouched)`.

---

### Task 7: The Lottery (the dispenser)

**Files:** modify `gmfrontend_atlas_toy.inc`, `tyfigupon.c`, `atlas_toy_test.c`; extend `test_toy_guards.py`.

Retail facts: `GS_TOY_LOTTERY` (12): `tyFigupon_Scene_OnEnter` (`tyfigupon.c:1533`), the machine from `TyMnFigp` and `ToyFigurePonCoin_Top_joint` (the coin model), the coin balance `gm_801623D8() / 10u` (`tyfigupon.c:594`), the text objects `data->x14` (set from `Toy_80308328(arg0)` and index `0x13C`, `tyfigupon.c:842, 1485`), the pull logic and the popup "a new trophy" (kept retail: it shows the real trophy model), `tyFigupon_Scene_OnFrame` leaves on its own state (`tyfigupon.c:1668-1676`). The Lottery's entry fault is fixed (`TROPHIES.md` sections 1 to 3). **What "chance" the spec mentions is not found in the code read: (unverified).**

- [ ] **Step 1: Read** `tyfigupon.c` 560-760 (the coin drop and `tyFigupon_FinishCoinDrop`), 842-940 (the cursor and pad), 1285-1300, 1485, 1533-1676: list (a) the text objects retail shows (coins, prompts) and which are the **popup**, (b) the GX links of the machine, the coins and the popup (the popup must have **no** guard), (c) the keys retail accepts, (d) any "chance" or price value. Write them in the commit message.
- [ ] **Step 2: The chrome:** the coin count (`gm_801623D8() / 10u`, an authored label `COINS`), the trail `COLLECTION > LOTTERY`, the key hints from (c), an explainer whose WHAT is an authored line about the coin cost **only if** (d) found a price (else none: no invented numbers). Window constant `FAT_LOTTERY_WIN` (measured; the machine, framed).
- [ ] **Step 3: Guards** (`AT_RE_LOT_PANEL`, `AT_RE_LOT_TEXT`): only the coin readout and prompts found in (a) that are **not** part of the popup; the guard test lists the popup's creation sites by line text and asserts no guard on them.
- [ ] **Step 4: Tests** in `atlas_toy_test.c`: coins 0, 1, 99, 100 (the readout formatting through `at_fmt_count`), and a no-price chrome.
- [ ] **Step 5: Commit.** `atlas: Lottery chrome (the coin balance and keys; the popup and the machine stay retail)`.

---

### Task 8: Movies, Staff Roll and Snapshots: stay retail behind a hand-off

**Files:** tests only; `tools/port/retail_screens.py` expected file; no new product code unless Step 2's owner decision says so.

- [ ] **Step 1: Prove they stay retail.** `pc/tests/atlas_policy_test.c` already asserts (Task 2) that no mask or chrome id exists for the opening, movie, memory-card and Staff Roll kinds. Add the **entry** side: a static check (`tools/port/test_fe_atlas_data.py` in step 8 already pins that `fad_screens[]` has no row for `SEL_DATA_SNAP` and `SEL_DATA_ARCHIVES`: add the assertion `not in` for both if it is not there) so Movies and Snapshots keep running through `FA_NATIVE` and `mn_PcOpenNative` exactly as today, and the back-out returns through `gmFrontend_NativeReturn` to the DATA hub row.
- [ ] **Step 2: Staff Roll (an owner decision, default none).** Correction 4: retail has no menu entry for it. The options for the owner: (a) **none** (default: it plays after a 1P ending, as retail); (b) an entry under `More > Credits` that launches it through the scene launcher (`gw_sl_modes`-style launch of `GS_STAFFROLL`, then returns to the menu): a **new feature** and a new launch path to write and test, size S; (c) the same plus a corner key hint from Atlas. If (a): nothing to build. If (b) or (c): this step adds `Ui_OpenCredits`'s sibling `Ui_LaunchStaffRoll` and a Credits row, with the scene's retail exit returning to the main menu; the scene's own on_enter reads `GmStRoll.dat` etc. unchanged.
- [ ] **Step 3: Update `retail_screens_expected.json`** (step 8) with `"stays": true` for Movies, Snapshots and Staff Roll and a `"decision"` field for each (`owner, 2026-10-06: skip`).
- [ ] **Step 4: Commit.** `tests: the owner-skipped screens stay retail (policy and entry guards); Staff Roll's entry is an owner decision`.

---

### Task 9 (optional, separately gated): Tournament

**Gate:** the owner says yes (he has not: "undecided"), **and** step 8 has merged, **and** Tasks 3 to 5 have had their look. Until all three, this task does not start. It is recorded as **L** in the spec and the order is setup first (M), bracket framed after.

**What is known:** `GS_TOU_SETUP` (0x24, "selections and settings"), `GS_TOU_BRACKET` (0x25, "Match Type"), `GS_TOU_ALT` (0x26, winner out / loser out), `gmscdata.c:316-330`; the code is `gmtou_0.c` (2,922 lines), `gmtou_1.c` (2,462), `gmtou_2.c` (1,211), `gmtoulib.c` (2,608), `gmtoumode.c` (234); text from `SIS_TournamentData` (`gmtou_0.c:2905`, the file name from `fn_8018F5F0()`); the archive `TmBox.dat`; the entry is `VS > TOURNAMENT`, an `FA_MODE` to `GM_TOURNAMENT` (`gmfrontend_menus.inc:164-165, 186`). Name tags and the `MatchEnd` of the current tournament match are in `struct gm_...` with `x48` "current tournament match results" (`gm/types.h:1069`). **Everything else is unread: (unverified).**

- [ ] **Step 1: Read** `gmtoumode.c`, `gmtoulib.h` and the three scene `OnEnter` functions and write, in `docs/NEXT-SESSION.md`, the table the spec lacks: the setup's data structures (the player list, the byes, the match order, the options), how a result feeds back (the `x48` `MatchEnd` path), which parts are **list-and-settings** (Atlas-able as a list screen like step 5's pages or step 8's data screens) and which are **bracket drawing** (retail 2D and 3D), and the size per part. **No code before this table exists and the owner has seen it.**
- [ ] **Step 2: Setup (M).** If the setup is a list of choices over a fixed-size structure, model it as a pure `AtTouSetup` (the fields from Step 1; a test with invented values for every option, the full 64-player case, and the validation retail does before it starts) and an adapter in the step 8 style (own cursor, shims, `FA_MODE` entry). The retail scene `GS_TOU_SETUP` becomes `REPLACE` only if the setup's outputs are simple to reproduce (the structure it writes for the bracket scene); otherwise `OVERLAY` with the frame.
- [ ] **Step 3: Bracket (L).** The framed pattern of Tasks 3 to 5 for `GS_TOU_BRACKET` and `GS_TOU_ALT`, window from the same outline procedure, readbacks from Step 1's table, guards for the 2D labels inside the window; the retail text (`SIS_TournamentData`) through step 8's decoder or left visible.
- [ ] **Step 4: Decision.** After a look: go, hold or drop, in the decision table.
- [ ] **Step 5: Commit** per sub-step. If the owner says no: write "Tournament: not re-hosted (owner, <date>)" in `docs/NEXT-SESSION.md` and stop.

---

### Task 10: The Language row, and the decision it needs

**Files:** none unless the owner decides to remove it.

The spec (2, answer 5): "The retail Language row stays a native hand-off until the retail text screens are gone, then is removed." The state after steps 8 and 10: the retail **text** screens still running are **Movies, Snapshots and Staff Roll** (skipped by the owner), the text objects the framed scenes keep visible under a NO-GO or PARTIAL text outcome, Tournament if not re-hosted, the opening movie's subtitles if any, and the memory-card prompt.

- [ ] **Step 1: Run the inventory.** `python tools/port/retail_screens.py` and the decision table: list every retail screen that still draws text in the saved language.
- [ ] **Step 2: Write the finding** to `docs/NEXT-SESSION.md`: while any of them remains, "the last retail text screen" does not exist; the Language row (English or Japanese: it sets `.usd` or `.dat` through `lbLang_IsSavedLanguageJP()` for **every** retail text archive) cannot be removed without choosing the language for those screens. **Owner decision needed** (Owner decisions): keep the row (default), or remove it and **fix the language to the disc's own** for the skipped screens.
- [ ] **Step 3: Only if he chooses removal.** Remove the `LANGUAGE` row from `fm_settings` and from step 5's settings page, the `SEL_SETTINGS_LANG` case from `mn_PcOpenNative`, and leave `mnLanguage.c` and the saved setting untouched (the setting still decides `.usd` or `.dat`; a player who saved Japanese keeps it). Tests: the settings inventory (`tools/port/settings_inventory.py`, step 5) loses exactly one row; `retail_screens.py` shows `SEL_SETTINGS_LANG` retired.
- [ ] **Step 4: Commit** the finding (and the removal only if chosen).

---

### Task 11: Documentation, the in-game proof and the retirement list

**Files (workspace repo):** `docs/TERMINOLOGY.md` (**frame**, **window**, **chrome**, **retail text** if not added by step 8), `menu/CLAUDE.md` (the retirement list below), `docs/NEXT-SESSION.md` (the state, the per-screen decisions). No `docs/scripting.md` change: nothing here is a `gd.ui` API. **No demo mod:** the house rule gives each new *capability* a single-feature demo; step 10 adds none a mod can use (the mask bits for these scenes are policy-only, `at_retail_script_allowed` excludes them, and `frame` is not exposed to Lua).

**What the owner's look retires (nothing is deleted before it, and only per accepted screen):** the retail 2D pieces stay on the disc and in the game, hidden by the mask where they sat inside the window; once a screen has shipped (row in the policy table, owner's go), its retail text and hint objects inside the window are never drawn. Nothing of the disc is copied; nothing disc-derived is committed. No file under `menu/` is retired by this step (the legacy menu art is step 9's Task 11).

- [ ] **Step 1: Build and confirm the exe** (no window): `tools/port/build.sh` in `$MAIN` with the lane exports; `grep -a "framed scene" "$GW_BUILD_ROOT/melee-pc.exe" | head -1` and `grep -a "toyprobe" ...` print a line.
- [ ] **Step 2: The window measurement (a Windows agent while the owner is away; second monitor; `MELEE_VOLUME=0`; vanilla first, ACE second).** For each scene: enter it through its real path (`MAIN > COLLECTION > GALLERY` etc.); run with `MELEE_ATLAS_SCENES=<kind>:overlay MELEE_ATLAS_FRAME_OUTLINE=1 MELEE_ATLAS_FRAME_WIN=x,y,w,h`, adjusting `x,y,w,h` until the outline hugs where the retail model is at **640x480 (4:3)**; write the four numbers into the `FAT_*_WIN` constants; repeat at 960x720 and **1920x1080** to see whether the same numbers work (correction 2): if the 16:9 retail view is wider than the 4:3 band, write that down and **stop**: the mapping in `at_frame_hole` needs the `View` system's real transform before the screen can ship wide.
- [ ] **Step 3: Per-bit look** (each guard alone, offline): `MELEE_ATLAS_RETAIL=toy.panel`, then `toy.info`, then `toy.text`, then `lot.panel`, `lot.text` (the environment source of step 3's mask works for any id): exactly that retail piece disappears and nothing else; the trophy still rotates and zooms with the stick, the series still changes, the coins still drop. With a netplay or rollback-enabled run (a LAB SyncTest is enough to enable rollback): nothing hidden, and the log says `framed scene N not drawn`.
- [ ] **Step 4: Each screen (the owner, or an agent while he is away), with the policy on:** `MELEE_ATLAS_SCENES=11:overlay` (Gallery), `12:overlay` (Lottery), `13:overlay` (Collection) one at a time, on the vanilla disc **and** ACE (m-ex trophies): (1) the retail 3D unchanged inside the window (same model, same lights, same rotation as `MELEE_ATLAS_SCENES=<kind>:retail`); (2) the hidden retail pieces gone and **nothing else missing**; (3) trail, explainer, counter and key hints correct and inside their plates; (4) the explainer's text is the right trophy's (a trophy you know); a trophy whose name does not decode shows the authored fallback, never a half name; (5) the hints match what retail's pad does; (6) at 4:3, 16:9 and 21:9, no chrome over the model and the window where the model is; (7) first and last trophy, zero owned (a fresh save), all owned.
- [ ] **Step 5: The Lottery's popup** (the scene piece that must stay retail): pull once (coins needed: `unlock all` gives them): the popup and the trophy model show completely, with the Atlas chrome behind or beside, nothing hiding them.
- [ ] **Step 6: Exit and return.** B leaves each scene through retail's own exit; the COLLECTION hub shows with the cursor on the row you came from (`fm_position_for`), in Atlas and in `MELEE_ATLAS=0`.
- [ ] **Step 7: Frame cost and Reduced Motion:** `MELEE_FPS=120`: each framed scene holds 120 fps (record the readout; the chrome is a few hundred quads); Reduced Motion on: the chrome's open fade is a cut.
- [ ] **Step 8: The fallback:** `MELEE_ATLAS=0` and `MELEE_ATLAS_SCENES=<kind>:retail`: each scene is exactly retail.
- [ ] **Step 9: Capture and report.** Per run folder `"$GW_BUILD_ROOT/runs/<name>/melee-pc.log"`, the lines with `frontend:`, `toyprobe` and `ui:`; a yes or no for every numbered item and one line for each no; say plainly which items were not run. The owner records **go, hold or drop** for each screen in `docs/NEXT-SESSION.md`; **only a go adds the policy row** (`ROWS[]` in `gw_ui_policy.c`, one line) and the owner's per-screen decision is the only thing that does.
- [ ] **Step 10: Commit (both repos).** `docs: step 10 terms, decisions and the retirement list`; after a go, one more commit per screen: `atlas: <screen> framed by default (owner's go, <date>)`.

---

## Self-review

**Spec coverage (13.10).**

| 13.10 item | Where |
|---|---|
| The frame pattern: OVERLAY, retail runs unchanged, retail pad polling untouched, nothing injected | Tasks 3, 4 (the wrapper runs retail first; no `Ui_Intent`; `input_feed`) |
| The retail 2D pieces hidden one by one with the mask (`JOBJ_HIDDEN`) | Tasks 2, 5 to 7 (render-callback and text-`hidden` guards at creation; correction 1: only the pieces inside the window) |
| Atlas chrome: trail, explainer, counter, key hints; a transparent window in an opaque plate (the `view` part) | Task 3 |
| Readback shims (trophy index, series counter, cursor, coin count) | Tasks 5 to 7 (`TOY_SEL`, `TOY_SELID`, `TOY_COUNT`, `gm_801623D8() / 10`; the Collection cursor found in Task 6 step 1) |
| Retail strings decoded to the Atlas charset or left visible (a partial mask) | Task 1 (the gate), Tasks 2 and 4 (`text_ok` in the mask), Task 5 |
| Mouse not supported on a framed screen in version 1; hints show the pad only | Task 3 (no hits), Global Constraints |
| Trophy Gallery first; Collection after; Lottery with the popup kept | Tasks 5, 6, 7 |
| Movies (a list calling retail playback), Staff Roll, Snapshots | **Owner: skipped.** Task 8 proves they stay retail; Staff Roll's entry is an owner decision (correction 4) |
| Tournament, last, only if played | Task 9 (optional, separately gated, unread beyond the scene table) |
| Training panel | **Owner: skipped.** Nothing built; the LAB covers it |
| Each screen is one commit set and one look; per-screen go or no-go | Task 1 (the record), Task 11 step 9, Global Constraints |
| Retired per screen: the retail 2D stays on the disc, hidden by the mask once shipped | Task 11 retirement paragraph |
| The Language row goes when the last retail text screen is gone | Task 10 (cannot, while the skipped screens remain; an owner decision) |
| Verified without the game: mask and policy tests, layout tests of each chrome at three widths with sample data, PowerPC syntax checks of every guard | Tasks 2, 3, 5 to 7 |

**Deviations from the spec, named.** (1) The mask hides only what is **inside** the window (opaque plates cover the rest): correction 1. (2) Guards swap a render callback or set a text `hidden` flag **at creation** rather than set `JOBJ_HIDDEN` on trees: the mask is constant for the scene (policy), nothing in retail's logic reads it, and one mechanism covers JObj, SObj and text objects. (3) Staff Roll's Credits entry is not a hand-off (correction 4). (4) The window rectangles are committed numbers measured with a debug outline, not derived from the retail camera.

**Unverified items and where each is settled.**

| Item | Settled by |
|---|---|
| How a 16:9 or 21:9 window maps the retail toy camera (widens or pillarboxes) | Task 1 step 2(a), Task 11 step 2 |
| The viewport getter name and the GX link list structure the probe uses | Task 1 step 1 (read `gobjgxlink.c`, `cobj.h`) |
| Which retail GObjs and text objects lie inside each window | Task 1 step 2(e), Task 11 step 2 and 3 |
| That the policy mask is set before `scene->on_enter` (via `Script_SceneBegin` in `gm_801A4B88`) | Task 4 step 2 |
| That the English `SdToy`/`SdToyExp` strings decode | step 8 Task 1 (probe), recorded in Task 1 here |
| The keys the Gallery, Collection and Lottery accept | Tasks 5 step 4, 6 step 1, 7 step 1 |
| Where the Collection's cursor trophy lives; whether it has one | Task 6 step 1 |
| What a Lottery "chance" or price is, if anything | Task 7 step 1 |
| `AT_PRIMARY_FRAME`'s number and step 3's final names (`AT_RS_POLICY`, `gs_ui_retail`, the id enum) | Task 0 gate; Tasks 2, 3, 4 RECONCILE notes |
| The Tournament data structures, result path and what is list versus bracket | Task 9 step 1 |
| Whether retail rendering of these scenes tolerates a hidden callback (no assumption in later passes, such as a GX state reset done by the callback) | Task 11 step 3 (the per-bit look) |
| The trophy count constant (`TY_TROPHY_COUNT`) and m-ex's extra trophies | Task 5 tests use invented counts; Task 11 step 4 on ACE |

**Owner decisions needed.** (1) **Language row**: keep it while Movies, Staff Roll and Snapshots stay retail (default), or remove it and fix their language to the disc's (Task 10). (2) **Staff Roll**: no entry (default), an entry under More > Credits that launches the scene (a new launch path), or that plus a corner hint (Task 8). (3) **Tournament**: yes or no (Task 9; default no, undecided). (4) **Per screen**, after its look: go, hold or drop for the Gallery, the Collection and the Lottery (Task 11 step 9). (5) If a screen's text does not decode: ship its frame without the disc's words, or drop it (Task 1).

**Placeholder scan.** Where the plan could not read a fact it says "(unverified)" and names the step that reads it; the window constants are an explicit zero-means-do-not-draw placeholder that Task 11 replaces with measurements (`FAT_*_WIN`: the code refuses to draw rather than guess). Two numbers in `at_frame_slots` (the card height 150 and the 8 px gap) are stated as placeholders for the explainer part's measured height.

**Type and name consistency.** `AtFrameRect`, `AtFrameSlots`, `at_frame_hole/plates/slots` (Task 3) are used by the render branch and the tests; `at_policy_mask`, `at_policy_screen_for` (Task 2) by `gw_Ui_SceneBegin` (Task 4); `AtToyChrome` and `at_toy_chrome` (Task 5) by Tasks 6 and 7; `Fad_OverlayWrap`, `fat_inner`, `fat_kind`, `fat_overlay_frame`, `fat_submit` (Task 4) are the names `test_overlay_hook.py` parses; the element ids `AT_RE_TOY_PANEL`, `AT_RE_TOY_INFO`, `AT_RE_TOY_TEXT`, `AT_RE_LOT_PANEL`, `AT_RE_LOT_TEXT` (Task 2) are used unchanged by the guards of Tasks 5 to 7 and by `MELEE_ATLAS_RETAIL`; shims `gw_Ui_*` (host) equal `Ui_*` (game) apart from the prefix.

**Execution recommendation.** Tasks 0 to 3 are self-contained: one fresh agent each in order, with a review between (Tasks 2 and 3 can start as soon as step 3 is merged; Task 2 needs only the ids and the mask). Task 4 touches retargeted game code and the scene loop: one agent, the coordinator reviews the guard output and the PowerPC check before the build. Task 1 (the probe and its run) should happen **before** Tasks 5 to 7 are written beyond their pure parts: it decides which of them are worth doing. Tasks 5, 6 and 7 are independent once Task 4 is in and can go to separate agents (merge Gallery first: it proves the pattern). Task 9 waits for the owner. Task 11 is for a Windows agent while the owner is away, or for him.
