# Atlas step 2: the title, the main menu, Solo and the hubs: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to carry out this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw the game's front door (the title, MAIN MENU, SOLO, REGULAR MATCH, STADIUM, MULTI-MAN MELEE, VERSUS, SPECIAL MELEE, COLLECTION, the SETTINGS list, DATA, RECORDS, a new CREDITS screen) through Atlas behind `MELEE_ATLAS` (on by default, `MELEE_ATLAS=0` is the legacy fallback). Restructure the main menu as Solo, Versus, Online, Mods, Settings plus a More row. Add the entry registry and `mod.json` `menus`. Make Envoy the first mod entry (`SOLO > ENVOY`). Retire the `FA_TBD` tile mechanism as a versioned API removal. Build the scene policy table (RETAIL / OVERLAY / REPLACE).

**Architecture:** Step 1 built Atlas for Lua-owned screens only. Step 2 adds a third kind of owner, the **engine**: a native screen whose record is filled each frame by the game-side adapter (`GM/gmfrontend_atlas.inc`) through scalar shims (`Ui_*`, the unprefixed-shim convention). Its events go back through a host queue instead of to Lua handlers. The menu tree (`fm_menus[]`), the position protocol `(MenuKind, selection)`, `fm_confirm`/`fm_back`/`fm_do_pending` and the retail back-out are reused unchanged: Atlas only moves the cursor and calls those same functions. Three new pure-C units (tiles and display primaries in the existing parts and renderer; `gw_ui_registry.c`; `gw_ui_policy.c`) are tested without the game. One game-side line in `gm_801A4014` applies the scene policy.

**Tech stack:** C11 host code (`melee/pc/platform`, built by `tools/port/build.sh`), retargeted game C (`melee/src/melee/gm`, syntax-checked as PowerPC), Lua 5.4 (mods and offline tests; `lua` on PATH), Python 3 (one table test), `tools/port/native_test.sh`.

**Spec:** `docs/superpowers/specs/2026-10-06-menu-reunification-design.md`. Step 2 is section 13.2; the owner's decisions are in section 2; the scene policy is 6.8; the router is 6.4; the mod interface is section 8.
**Step 1, as merged (what this plan builds on):** `melee/pc/platform/gw_ui_*.{c,h}`, `gw_script_ui.inc`, `docs/scripting.md` "Atlas screens (`gd.ui`)", the step 1 plan `docs/superpowers/plans/2026-10-06-atlas-step1-components-and-envoy-bag.md`.

## Global Constraints

Values are copied from the spec and from step 1's code. If a task seems to need a different value, stop and ask the coordinator.

- **Canvas and arrangement:** 640x480 logical px, `w = 480 x aspect`, never under 640. Compact below 760, wide from 760, content at most 1140 wide and centred (`at_layout`, `gw_ui_layout.c`). Every test that draws runs at **640, 853 and 1140** wide.
- **Style rules that every new part must pass in its own test, not in review.** These are the three rules reviewers kept catching in step 1:
  1. **Chamfers.** Chamfers sit on two opposite corners only (top-left and bottom-right): 8 px on panes and modals, 5 px on rows, buttons, notes and tags, 3 px on cells. **Nothing is drawn inside a cut-away corner.** That includes focus ticks, numeral badges, tags and icons. Every new part's test calls `corners_clear(r, c)` (copied from `atlas_parts_test.c:304-316`).
  2. **Three focus cues at once.** The plate lifts 2 px, its front edge turns ember, and a tick (rows and tiles: 4 px at the left, below the chamfer) or four registration brackets (cells) appear. Every new focusable part's test counts all three. Selected adds jade and never moves.
  3. **Text never leaves its box and is never under 12 px.** Every text call goes through `at_fit` or `at_wrap` with the box width. Tests use `texts_legible()` and a `text_inside(rect)` check with the longest real string the screen can carry.
- **Ownership and lifetime are tested up front.** Each binding change has tests for: who may open, close, feed or replace a screen (engine, owning script, another script, the console); what happens when the owner unloads while its screen is on the stack or under another screen; what happens when the scene that opened a screen ends. **Test the real path:** a test that drives a screen as the developer console does not count as a test of a mod or of the engine (step 1 lesson: the console path hid a real bug). Console-only checks are labelled as such.
- **One stack.** Atlas has a single screen stack (`gs_ui_stack`, 8 deep). Only the top screen draws and takes input. A mod screen pushed from a menu entry sits above the native menu screen; the native menu does not draw or take input while it is covered.
- **Budgets:** one screen is at most 4,096 kit entries (it warns at 3,000) of the shared 16,384 (`KQ_MAX`). The target is 0.5 ms per frame for any screen, inside 8.3 ms (120 fps). A hub's estimate from the mockups is about 340 entries.
- **Online:** Atlas never masks the pad and never writes the simulation. Mod entries under `versus` and `online` are hidden while a netplay session exists unless `"online": true`. A mod entry is never shown over an online room. A screen's state is never an input to the simulation. No handler runs on a resimulated frame (`gs_may_run`).
- **Default is unchanged where the owner has not looked:** every scene policy except the title's is `RETAIL`. `MELEE_ATLAS=0` restores the legacy menus and the retail title exactly as they are today (same tree, same art, same `FA_TBD` behaviour is **not** kept: see Task 10).
- **No disc-derived data, ever,** in either repo. No screenshots as verification (the only exception is diagnosing how a visual looks). Every outside project, font or idea is credited by name and link in the same change.
- **Naming:** C `at_*`/`At*` (pure units), `gw_Ui_*` (host shims, called as `Ui_*` from game code), files `gw_ui_*`, Lua `gd.ui`. Screen ids of the built-in tree: `main`, `solo`, `solo.regular`, `solo.stadium`, `solo.multiman`, `versus`, `versus.special`, `more.collection`, `settings`, `more.data`, `more.records`, `more.credits`, `title`. Registry parent ids are the spec's: `main`, `solo`, `versus`, `online`, `mods`, `settings`, `more`, `settings.<page>`.
- **English only.**
- **Process rules (this machine):** no game, launcher or browser window while the owner is at the machine. The in-game task runs only when he is away, on the second monitor, with `MELEE_VOLUME=0`. Never kill processes by image name; stop only a PID you started. Build only through `tools/port/build.sh` in a private lane (`tools/port/agent_new.sh`); the native tests go through `build.sh --native-test` (the `nt` helper below). Use Git Bash on Windows.
- **Two repositories.** Game repo `melee/` (your worktree, branch `agent/atlas2`); workspace repo root (your worktree `worktrees/ws-atlas2`, branch `ws/atlas2`). Each commit step names the repo. Do not commit `gw_mex_bridge.c` churn.
- **The Envoy Lua suite runs from the game repo root:** `for f in pc/tests/envoy_*.lua; do lua "$f"; done` in `$GW_MELEE`. This is the same as `for f in melee/pc/tests/envoy_*.lua; do lua "$f"; done` from the workspace root of the main checkout. Running it from anywhere else fails on paths, which is not your bug.

## Decisions made before planning (the spec's open investigations, with evidence)

The spec left three questions open that step 2 depends on. Each was decided from source; each task that relies on one starts with a step that re-checks it on the current tree and gives both branches.

| # | Question | Answer from source | Evidence | Still unverified |
|---|---|---|---|---|
| D1 | Does the overlay draw over a frontend scene, and in what order? | **Yes, above everything the game draws, in the same frame.** The scene loop that runs every scene (title, `GS_FRONTEND`, `GS_MENU`, matches) calls `Script_Tick()` before the logic and `Script_PostRender()` after the GX render. `PostRender` completes the list (`gs_finish_draw`: `on_draw`, then `gs_ui_draw`, then `gw_Kit_SwapBanks`), and the shown bank is submitted through ImGui on every present, after the game frame. | `src/melee/gm/gmscene.c:821-825, 1124-1129`; `pc/platform/gw_script.c` `gs_finish_draw` (about :7604-7618, the swap at `gw_Kit_SwapBanks`); `pc/platform/shim_vi.c:1389-1397` (`gw_present_overlays`, "submit it through ImGui for every present, including GX replays") | How it looks: one frame of lag on a GX replay frame when uncapped, and whether the legacy frontend's own fade (`fm.fade`, game GX) shows through. Atlas draws an opaque ground (`gw_ui_render.c:221`), so the legacy screen underneath is covered. |
| D2 | Do script draw hooks and `gd.ui` run on menu scenes? | **Yes.** It is the same loop as D1; `gs_ui_tick()` is called from `gw_Script_Tick` and `gs_ui_draw()` from `gs_finish_draw` with no match gate. The Lua state is created even with `MELEE_SCRIPTS=0`, which only skips the scans. | `gw_script.c` `gw_Script_Tick` (`gs_ui_tick();` about :7674), `gs_finish_draw` (`gs_ui_draw();` about :7613), `gs_init` (`script: Lua 5.4 engine up` before `getenv("MELEE_SCRIPTS")`, about :7396-7403) | That `gw_Console_ScriptWidth()` reports the real canvas width on `GS_FRONTEND` (it is the same call the match uses). |
| D3 | Where is the title hook, and is it cheap? | **Cheap.** Every scene's `on_enter`/`on_frame` pair is resolved in exactly one place, `gm_801A4014` (`scene = gm_FindGameSceneHandler(kind)`, then `scene->on_enter`, then `gm_801A4D34(scene->on_frame, info)`). The title's next mode is decided by the retail `onExit` of `gm_Mode_Title_States` from the exit data the title's `on_frame` writes (START: `GM_MENU`; 600 frames idle: `GM_OPENING_MV`; the port's Y/B: `GM_DEBUG`). So an **OVERLAY** title (retail runs unchanged, Atlas draws an opaque display screen over it and takes no input) keeps the attract loop, START and the debug path with zero reproduction. `REPLACE` would have to rebuild the exit data, the music and `gm_PreloadTitleDemo`. | `src/melee/gm/gm_1A3F.c:158-200`; `gmtitle.c:258-300, 338-375`; `gmtitlemode.c:18-79`; `gmscdata.c:69-75` | That nothing retail shows through the opaque ground (the debug build-stamp text only draws on debug ROMs). |

**Consequence for the plan.** The title goes in step 2 as an **OVERLAY** (Task 12). `REPLACE` is built in the policy table and unit-tested, but it has no user until step 8 (results). This is a deviation from 13.2's "first used for the title"; the reason is D3, and it is listed in the self-review.

**Other facts the plan relies on (read from the merged code):**

- The stack's slots are Lua-owned only (`GsUiSlot.owner` is a script index). `gs_ui_tick` releases a slot whose owner is not `gs_ui_usable` (`gw_script_ui.inc:529`). **An engine owner must be exempted, or the main menu would be released on its first tick.** Task 5 pins this.
- `AtScreen.primary` has only `AT_PRIMARY_LIST` and `AT_PRIMARY_GRID` (`gw_ui_screen.h:21`). The hubs need the spec's `tiles` primary, and the title needs a display screen with no primary. Tasks 1 and 2 add them.
- `mod.json` is parsed by a strings-only reader that skips nested objects inside arrays (`gw_mods.c:240-270`, `json_skip_value`). `menus` needs an array-of-flat-objects reader (Task 4).
- The `FA_TBD` chain: `fm_main[0]` (`gmfrontend_menus.inc:70`), `fm_visible` (:249-251), `fm_confirm` case `FA_TBD` and `fm_do_pending` case 7 (:1222-1226), `gw_Script_TbdAvailable`/`TbdRequest` (`gw_script.c` about :7704-7713), `l_tbd_request` (about :4095), its registration (about :6570), the only consumer `pc/scripts/examples/roguelite/main.lua:1250`. `GW_SCRIPT_API_VERSION` is 1 (`gw_script.h:41`); `gd.deprecated` exists (`gw_script.c` about :6757).
- The LAB is already in SOLO as `FA_MODE GM_LAB`, shown when `Script_LabAvailable()` and asking `Script_LabRequest()` (`gmfrontend_menus.inc:92-93, 255-260, 1262-1268`). `gd.lab_request` itself is also used by `MELEE_LAB=1` and `geno_lab_mode.c:129, 230`, so it stays.
- `tools/port/fe_menu_sweep.py` boots the game with a disc (`--disc vanilla`, pad scripts through `_build/selftest.ps1`). **It does not run without the disc** (this settles the spec's "[unverified]" in 13.2). It is used in Task 13 only.

## Review Focus

The failure modes a happy-path test does not catch, most likely to hurt a player first. Each is pinned by a named test in the task that owns the code.

| # | What goes wrong for the player | Pinned by |
|---|---|---|
| 1 | **The main menu disappears or freezes.** The engine-owned screen is released by the script-lifetime code (`gs_ui_release`, the `gs_ui_usable` check), or a mod screen left on the stack covers it after its script unloads, or a screen pushed in the menu is still on the stack in the match. | Task 5 `engine_slot_survives_tick`, `engine_slot_not_released_by_script_unload`, `uncover_primes_engine_screen`, `scene_exit_closes_scene_screens`; Task 6 `entry_screen_closed_on_scene_exit` |
| 2 | **Coming back lands on the wrong item.** After a retail screen (Rules, Name Entry, Event), a match or a settings page, the cursor must land where the legacy menus land. | Task 8 `test_fe_atlas_positions.py` (every `fm_position_for` row is a visible item of an Atlas menu); Task 8 `cursor_is_the_legacy_cursor` (the adapter never keeps its own cursor) |
| 3 | **Double input or no input.** A press acts twice (Atlas plus the legacy `fm_scene_frame` path), a held A from the previous screen fires on the next one, or the menu ignores the pad because the port that pressed was not port 1. | Task 5 `native_intents_are_primed`; Task 8 step 4 (the legacy input path is skipped by construction; grep check); Task 5 `intents_from_any_port` |
| 4 | **A mod breaks the menu.** A mod registers 20 entries, an unknown parent, an id outside its namespace or a 40-character label; a disabled mod still shows; an online-unsafe entry shows in a netplay session. | Task 3 `caps`, `unknown_parent`, `disabled_mod_adds_nothing`, `online_hidden`, `label_cap`; Task 4 `menus_parse_rejects` |
| 5 | **Text and chamfer breakage at 640 wide.** The longest blurb ("Video, audio, controls, online, mods and the game's options."), a mod label at 18 characters, `MULTI-MAN MELEE` in a two-column tile, the More row at 640. | Task 1 `tiles_at_three_widths`, `tile_chamfers_clear`, `tile_three_cues`, `more_row_fits_640`; Task 2 `title_fits` |

---

## File structure

Game repo (`melee/`).

| File | Create/Modify | Responsibility |
|---|---|---|
| `pc/platform/gw_ui_screen.h/.c` | Modify | `AT_PRIMARY_TILES`, `AT_PRIMARY_DISPLAY`; `AtItem.icon`, `.tag`, `.badge`, `.numeral`; `AtScreen.more[]` (the More strip), `AtScreen.hero`; `AtExplainer.with_text[]`; focus blocks for tiles |
| `pc/platform/gw_ui_parts.h/.c` | Modify | `at_part_tile`, `at_part_more`, `at_part_numeral`, `at_part_title` |
| `pc/platform/gw_ui_render.c` | Modify | `draw_tiles`, `draw_display`; the tiles and More hit rectangles |
| `pc/platform/gw_ui_registry.h/.c` | Create | U6: entries by parent, ordering, caps, visibility, online rule |
| `pc/platform/gw_ui_menus_json.h/.c` | Create | the `mod.json` `menus` array reader (pure; used by `gw_mods.c`) |
| `pc/platform/gw_ui_policy.h/.c` | Create | the scene policy table and its environment overrides (pure) |
| `pc/platform/gw_mods.c`, `gw_mods.h` | Modify | read `menus` into each mod; `gw_Mods_MenuCount`, `gw_Mods_MenuField`, `gw_Mods_MenuSummary` |
| `pc/platform/gw_script_ui.inc` | Modify | engine-owned slots, the native intent and event queue, the `gw_Ui_*` shims, scene tags, `gd.ui.entry`, the `on_entry` hook, registry boot |
| `pc/platform/gw_script.c`, `gw_script.h` | Modify | remove `TbdAvailable`/`TbdRequest`; `gd.tbd_request` becomes a deprecated stub; API 2; the scene-begin call into the binding |
| `src/melee/gm/gmfrontend_atlas.inc` | Create | U8: `fa_on`, `fa_submit`, `fa_frame`, `fa_scene_policy`, the title overlay |
| `src/melee/gm/gmfrontend_menus.inc` | Modify | the Atlas tree (`fm_main_atlas`, More), ids per menu, `FA_ENTRY`, `FA_CREDITS`; the `FA_TBD` removal; the early `fa_frame` branch in `fm_scene_frame` |
| `src/melee/gm/gmfrontend.c` | Modify | include `gmfrontend_atlas.inc` |
| `src/melee/gm/gm_1A3F.c` | Modify | one `TARGET_PC` line: the scene policy around `scene->on_enter`/`on_frame` |
| `src/melee/gm/gmfrontend_settings.inc` | Modify | the Mods page row says what a mod adds ("adds Solo > Envoy") |
| `pc/tests/atlas_tiles_test.c` | Create | tiles, More strip, display screen at three widths |
| `pc/tests/atlas_registry_test.c` | Create | registry and `menus` parsing |
| `pc/tests/atlas_policy_test.c` | Create | the policy table |
| `pc/tests/atlas_binding_test.c` | Modify | engine-owned slots, the event queue, lifetimes, entries |
| `pc/tests/atlas_ui_stub.lua`, `atlas_ui_stub_test.lua` | Modify | `entry`, `on_entry` in the stand-in |
| `pc/tests/envoy_atlas_entry.lua` | Create | Envoy's entry and `on_entry` offline |
| `pc/scripts/examples/envoy/mod.json` | Modify | `menus` |
| `pc/scripts/examples/envoy/scripts/run_host.lua` (or the file that defines the hooks; see Task 11) | Modify | `on_entry` |
| `pc/scripts/examples/envoy/scripts/main.lua` | Regenerate | `tools/port/envoy_bundle.py` |
| `pc/scripts/examples/roguelite/main.lua` | Modify | drop the `gd.tbd_request` line |

Workspace repo (root).

| File | Create/Modify | Responsibility |
|---|---|---|
| `tools/port/native_test.sh` | Modify | `atlas-tiles`, `atlas-registry`, `atlas-policy` cases; `atlas-binding` gains the new sources |
| `tools/port/test_fe_atlas_positions.py` | Create | the position-protocol table test (parses `gmfrontend_menus.inc`) |
| `docs/scripting.md` | Modify | `gd.ui.entry`, `on_entry`, manifest `menus`, API 2 and the `tbd_request` deprecation |
| `docs/TERMINOLOGY.md` | Modify | **engine screen**, **scene policy** |
| `melee/src/melee/gm/CLAUDE.md` is in the game repo | Modify (game repo) | one paragraph: `FM_ATLAS`, `MELEE_ATLAS`, the adapter |
| `CREDITS.md` | Check only | the Credits screen lists what `CREDITS.md` lists; no new outside work enters in this step |

## Preflight (once, before Task 1; not a task)

- [ ] **Step 1: Read.** Root `CLAUDE.md`, `docs/NEXT-SESSION.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md`, the spec sections 2, 4.5-4.10, 6.4, 6.7, 6.8, 7.1, 8, 9 and 13.2, the `gd.ui` section of `docs/scripting.md`, and `gw_script_ui.inc` from top to bottom (808 lines). The binding is the code you change most.
- [ ] **Step 2: Make a private lane** (same as step 1's Preflight, step 2, with the name `atlas2`):

```bash
export MAIN="<the workspace root: the directory that contains tools/ and _toolchains/>"
cd "$MAIN" && tools/port/agent_new.sh atlas2
git -C "$MAIN" worktree add worktrees/ws-atlas2 -b ws/atlas2
# then in every new shell:
export MAIN="<as above>"; export WS="$MAIN/worktrees/ws-atlas2"; export GW_ROOT="$MAIN"
export GW_MELEE="$MAIN/worktrees/atlas2"; export GW_BUILD_ROOT="$MAIN/_build/agents/atlas2"   # as agent_new.sh printed
nt() { GW_ROOT="$MAIN" GW_MELEE="$GW_MELEE" GW_BUILD_ROOT="$GW_BUILD_ROOT" bash "$WS/tools/port/native_test.sh" "$1"; }
ppc() { "$MAIN/_toolchains/llvm/bin/clang" --target=powerpc-unknown-eabi -fsyntax-only -DTARGET_PC -I "$GW_MELEE/src" -I "$GW_MELEE/src/melee" -I "$GW_MELEE/include" "$@"; }
```

`ppc FILE.c` is the PowerPC syntax check from root `CLAUDE.md` ("What a cloud or headless agent cannot do here"). If your toolchain's clang lives elsewhere, `ls "$MAIN/_toolchains"` and adjust the path once; the include list is the one `build.sh` uses for game TUs (`grep -n "\-I" "$WS/tools/port/build.sh" | head`).
- [ ] **Step 3: Record the baselines** (they must still pass at the end):

```bash
for t in atlas-tokens atlas-layout atlas-focus atlas-input atlas-screen atlas-stack atlas-parts atlas-render atlas-binding view-canvas; do nt $t | tail -1; done
cd "$GW_MELEE" && lua pc/tests/atlas_ui_stub_test.lua | tail -1
cd "$GW_MELEE" && for f in pc/tests/envoy_*.lua; do lua "$f" | tail -1; done
cd "$GW_MELEE" && ppc src/melee/gm/gmfrontend.c && echo ppc-frontend-ok
```

Write the numbers into your task notes. Expected: every `atlas-*` test prints `0 failed`; `envoy_*` print their PASS lines; `ppc-frontend-ok`. If the frontend PowerPC check already fails on `main`, record the error text: later tasks compare against it, not against zero.

---

### Task 1: The tiles primary and the More strip (hubs and the main menu)

**Files:**
- Modify: `melee/pc/platform/gw_ui_screen.h`, `gw_ui_screen.c`, `gw_ui_parts.h`, `gw_ui_parts.c`, `gw_ui_render.c`
- Create: `melee/pc/tests/atlas_tiles_test.c`
- Modify (workspace): `tools/port/native_test.sh` (new case `atlas-tiles`; add it to the `gw_die` list)

**Interfaces:**
Consumes: `AtLayout`, `at_fit`, `at_plate`, `at_poly_rect`, `at_part_tag`, `AT_C_*`, `AT_PX_CH_S` (5 px), `AT_PX_CH` (8 px).
Produces:
```c
enum { AT_PRIMARY_LIST = 1, AT_PRIMARY_GRID = 2, AT_PRIMARY_TILES = 3, AT_PRIMARY_DISPLAY = 4 };
#define AT_MAX_MORE 4
/* AtItem gains: */ char icon[AT_ID]; char tag[16]; char badge[8]; char numeral[6];   /* numeral: "I".."V" on the main menu */
/* AtScreen gains: */ int tile_cols;                 /* 1 (main menu: big rows) or 2 (hubs); 0 = by count: <= 3 items -> 1, else 2 */
                      AtItem more[AT_MAX_MORE]; int n_more;   /* the small More row under the tiles */
/* AtExplainer gains: */ char with_text[AT_MAX_WITH][24]; int n_with_text;   /* tags such as "Melee", "Rules" */
void at_part_tile(const AtSink *s, const AtTextOps *o, AtRect r, const AtItem *it, int state, int big);
void at_part_more(const AtSink *s, const AtTextOps *o, AtRect r, const AtItem *items, int n, int focus);   /* focus -1: none */
/* tiles focus blocks: block 0 = the tiles (cols = tile_cols), block 1 = the More row (cols = n_more) */
```

- [ ] **Step 1: Re-read the merged geometry.** `grep -n "draw_list\|draw_grid\|362.0f\|39.0f" "$GW_MELEE/pc/platform/gw_ui_render.c" "$GW_MELEE/pc/platform/gw_script_ui.inc"`. The list row pitch (39) and the primary height (362) are hard-coded in two places today (`gw_script_ui.inc:476` copies them). Do not add a third copy: add `int at_tiles_geometry(const AtScreen*, const AtLayout*, AtRect *tiles, int cap, AtRect *more, int more_cap)` to `gw_ui_render.h`. Both the renderer and the hit and scroll code use it.

- [ ] **Step 2: Write the failing test** `melee/pc/tests/atlas_tiles_test.c`:

```c
/* atlas-tiles: the tiles primary (hubs, main menu), the More strip and the display screen. No game. */
#include "atlas_check.h"
#include "atlas_fake.h"
#include "atlas_rec.h"
#include "../platform/gw_ui_render.h"
#include "../platform/gw_ui_tokens.h"

static AtScreen SC; static AtView V; static AtHits H;
static const float WIDTHS[3] = { 640.0f, 853.0f, 1140.0f };

/* copied from atlas_parts_test.c:304-316: no vertex inside the top-left or bottom-right cut-away */
static int corners_clear(AtRect r, float c)
{
    int i, k;
    for (i = 0; i < REC.np; i++) for (k = 0; k < 4; k++) {
        float dx = REC.p[i].x[k] - r.x, dy = REC.p[i].y[k] - r.y, ex = r.x + r.w - REC.p[i].x[k], ey = r.y + r.h - REC.p[i].y[k];
        if (dx >= -0.01f && dy >= -0.01f && dx + dy < c - 0.01f) return 0;
        if (ex >= -0.01f && ey >= -0.01f && ex + ey < c - 0.01f) return 0;
    }
    return 1;
}
static int text_inside(AtRect r)
{
    int i;
    for (i = 0; i < REC.nt; i++) {
        const RecText *t = &REC.t[i];
        float w = fake_width(0, t->role, t->s);
        float l = t->align == AT_ALIGN_RIGHT ? t->x - w : t->align == AT_ALIGN_CENTER ? t->x - w * 0.5f : t->x;
        if (l < r.x - 0.5f || l + w > r.x + r.w + 0.5f) return 0;
    }
    return 1;
}
static void item(AtItem *it, const char *id, const char *label, const char *sub, const char *tag)
{
    memset(it, 0, sizeof *it);
    snprintf(it->id, sizeof it->id, "%s", id); snprintf(it->label, sizeof it->label, "%s", label);
    snprintf(it->sub, sizeof it->sub, "%s", sub); snprintf(it->tag, sizeof it->tag, "%s", tag);
}
static void solo_fixture(void)       /* the longest real SOLO hub: 7 tiles (Envoy is a mod tile) */
{
    static const char *L[7] = { "REGULAR MATCH", "EVENT MATCH", "STADIUM", "TRAINING", "LAB", "ENVOY", "MULTI-MAN MELEE" };
    int i;
    memset(&SC, 0, sizeof SC); at_view_init(&V);
    snprintf(SC.id, sizeof SC.id, "solo"); snprintf(SC.title, sizeof SC.title, "SOLO");
    SC.primary = AT_PRIMARY_TILES; SC.tile_cols = 2; SC.preset = AT_PRESET_NORMAL; SC.chapter = 1;
    for (i = 0; i < 7; i++) item(&SC.items[i], L[i], L[i], "", i >= 4 && i <= 5 ? "MOD" : "");
    SC.n_items = 7;
    V.focus.block = 0; V.focus.index = 5;
}
static void main_fixture(void)       /* five big rows with numerals, then More */
{
    static const char *L[5] = { "SOLO", "VERSUS", "ONLINE", "MODS", "SETTINGS" }, *N[5] = { "I", "II", "III", "IV", "V" };
    static const char *M[3] = { "COLLECTION", "DATA", "CREDITS" };
    int i;
    memset(&SC, 0, sizeof SC); at_view_init(&V);
    snprintf(SC.id, sizeof SC.id, "main"); snprintf(SC.title, sizeof SC.title, "MAIN MENU");
    SC.primary = AT_PRIMARY_TILES; SC.tile_cols = 1; SC.preset = AT_PRESET_NORMAL;
    for (i = 0; i < 5; i++) { item(&SC.items[i], L[i], L[i], "", ""); snprintf(SC.items[i].numeral, 6, "%s", N[i]); }
    SC.n_items = 5;
    for (i = 0; i < 3; i++) item(&SC.more[i], M[i], M[i], "", "");
    SC.n_more = 3;
    V.focus.block = 0; V.focus.index = 1;
}

static void tiles_at_three_widths(void)
{
    int w;
    for (w = 0; w < 3; w++) {
        AtSink s = rec_sink();
        AtRect t[16], m[4];
        AtLayout L;
        int n, i;
        solo_fixture();
        at_layout(WIDTHS[w], SC.preset, &L);
        at_render(&SC, &V, WIDTHS[w], 1e6, 0, &FAKE, &s, &H);
        CHECK(texts_legible());
        n = at_tiles_geometry(&SC, &L, t, 16, m, 4);
        CHECK(n == 7);
        for (i = 0; i < n; i++) {                                   /* inside primary, no overlap */
            int j;
            CHECK(t[i].x >= L.primary.x - 0.01f && t[i].x + t[i].w <= L.primary.x + L.primary.w + 0.01f);
            CHECK(t[i].y >= L.primary.y - 0.01f && t[i].y + t[i].h <= L.primary.y + L.primary.h + 0.01f);
            for (j = 0; j < i; j++) CHECK(t[i].x + t[i].w <= t[j].x + 0.01f || t[j].x + t[j].w <= t[i].x + 0.01f ||
                                          t[i].y + t[i].h <= t[j].y + 0.01f || t[j].y + t[j].h <= t[i].y + 0.01f);
        }
        for (i = 0; i < H.n; i++) if (H.h[i].kind == AT_HIT_CELL && H.h[i].a == 0) {   /* hits are the arranged rectangles */
            CHECK_NEAR(H.h[i].r.x, t[H.h[i].b].x); CHECK_NEAR(H.h[i].r.w, t[H.h[i].b].w);
        }
    }
}

static void tile_chamfers_clear(void)
{
    AtItem it; AtRect r = { 40.0f, 60.0f, 250.0f, 62.0f };
    int st;
    item(&it, "lab", "LAB", "", "MOD");
    for (st = AT_ST_REST; st <= AT_ST_SELECTED; st++) {
        AtSink s = rec_sink();
        at_part_tile(&s, &FAKE, r, &it, st, 0);
        CHECK(corners_clear(r, (float) AT_PX_CH_S));                 /* the tag, the tick and the lift stay out of the corners */
        CHECK(text_inside(r));
    }
    snprintf(it.numeral, 6, "III");
    { AtSink s = rec_sink(); at_part_tile(&s, &FAKE, r, &it, AT_ST_FOCUS, 1); CHECK(corners_clear(r, (float) AT_PX_CH_S)); }
}

static void tile_three_cues(void)
{
    AtItem it; AtRect r = { 40.0f, 60.0f, 250.0f, 62.0f };
    AtSink s;
    float rest_top, focus_top;
    item(&it, "stadium", "STADIUM", "", "");
    s = rec_sink(); at_part_tile(&s, &FAKE, r, &it, AT_ST_REST, 0);
    CHECK(count_color(AT_C_EMBER) == 0);
    rest_top = poly_miny(&REC.p[0]);
    s = rec_sink(); at_part_tile(&s, &FAKE, r, &it, AT_ST_FOCUS, 0);
    focus_top = poly_miny(&REC.p[0]);
    CHECK_NEAR(rest_top - focus_top, 2.0f);                          /* cue 1: lift 2 px */
    CHECK(count_color(AT_C_EMBER) >= 2);                             /* cue 2: the front edge; cue 3: the 4 px tick */
    {
        int i, tick = 0;
        for (i = 0; i < REC.np; i++) if (REC.p[i].rgba == AT_C_EMBER && poly_maxx(&REC.p[i]) - poly_minx(&REC.p[i]) <= 4.01f &&
                                         poly_minx(&REC.p[i]) <= r.x + 0.01f) tick = 1;
        CHECK(tick);
    }
    s = rec_sink(); at_part_tile(&s, &FAKE, r, &it, AT_ST_SELECTED, 0);
    CHECK(count_color(AT_C_JADE) >= 1);
    CHECK_NEAR(poly_miny(&REC.p[0]), rest_top);                      /* selected never moves */
}

static void long_strings_fit(void)
{
    int w;
    for (w = 0; w < 3; w++) {
        AtSink s;
        AtLayout L;
        AtRect t[16], m[4];
        solo_fixture();
        snprintf(SC.items[6].label, AT_STR, "%s", "ABCDEFGHIJKLMNOPQR");   /* a mod label at the 18-character cap */
        at_layout(WIDTHS[w], SC.preset, &L);
        at_tiles_geometry(&SC, &L, t, 16, m, 4);
        s = rec_sink();
        at_part_tile(&s, &FAKE, t[6], &SC.items[6], AT_ST_FOCUS, 0);
        CHECK(text_inside(t[6]));
        CHECK(texts_legible());
    }
}

static void more_row_fits_640(void)
{
    AtSink s = rec_sink();
    AtLayout L;
    AtRect t[8], m[4];
    int i;
    main_fixture();
    at_layout(640.0f, SC.preset, &L);
    CHECK(at_tiles_geometry(&SC, &L, t, 8, m, 4) == 5);
    for (i = 0; i < 3; i++) {
        CHECK(m[i].y >= t[4].y + t[4].h - 0.01f);                       /* the More row is below the five rows */
        CHECK(m[i].y + m[i].h <= L.primary.y + L.primary.h + 0.01f);
    }
    at_part_more(&s, &FAKE, m[0], SC.more, 3, 1);
    CHECK(texts_legible());
    V.focus.block = 1; V.focus.index = 2;
    s = rec_sink(); at_render(&SC, &V, 640.0f, 1e6, 0, &FAKE, &s, &H);
    CHECK(find_text("CREDITS") != NULL);
}

static void focus_moves_between_tiles_and_more(void)
{
    AtFocusBlock fb[AT_MAX_BLOCKS];
    int nb;
    AtFocusPos p;
    main_fixture();
    nb = at_screen_focus_blocks(&SC, fb);
    CHECK(nb == 2);
    p.block = 0; p.index = 4;                                        /* SETTINGS, the last big row */
    p = at_focus_move(fb, nb, p, AT_DIR_DOWN, 1);
    CHECK(p.block == 1);                                             /* down from the last row enters More */
    p = at_focus_move(fb, nb, p, AT_DIR_RIGHT, 1);
    CHECK(p.block == 1 && p.index == 1);
    p = at_focus_move(fb, nb, p, AT_DIR_UP, 1);
    CHECK(p.block == 0);
    solo_fixture();
    nb = at_screen_focus_blocks(&SC, fb);
    p.block = 0; p.index = 0;
    p = at_focus_move(fb, nb, p, AT_DIR_RIGHT, 1);
    CHECK(p.index == 1);                                              /* two columns */
}

static void budget(void)
{
    AtSink s = rec_sink();
    AtRenderInfo info;
    solo_fixture();
    at_render_ex(&SC, &V, 1140.0f, 1e6, 0, &FAKE, &s, &H, &info);
    CHECK(info.entries < AT_SCREEN_QUAD_WARN);
    CHECK(info.capped == 0);
}

int main(void)
{
    tiles_at_three_widths(); tile_chamfers_clear(); tile_three_cues(); long_strings_fit();
    more_row_fits_640(); focus_moves_between_tiles_and_more(); budget();
    ATLAS_DONE("atlas-tiles");
}
```

Add to `tools/port/native_test.sh`, next to `atlas-render`:

```bash
atlas-tiles)
    sources=(pc/tests/atlas_tiles_test.c pc/platform/gw_ui_render.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c) ;;
```

and add `atlas-tiles` to the `gw_die` list of names.

- [ ] **Step 3: Run it and see it fail.** `nt atlas-tiles`. Expected: a compile error naming `AT_PRIMARY_TILES`, `tile_cols`, `at_part_tile` or `at_tiles_geometry`.

- [ ] **Step 4: Implement.**
  1. `gw_ui_screen.h`: the enum and fields above. `at_view_init` is unchanged. In `at_screen_focus_blocks`, for `AT_PRIMARY_TILES` return block 0 with `cols = tile_cols ? tile_cols : (n_items <= 3 ? 1 : 2)` and `n = n_items`, plus block 1 (`cols = n_more`, `n = n_more`) when `n_more > 0`. `at_screen_cell_id` returns `items[i].id` or `more[i].id`. `at_cell_accepts` is 0 for `AT_CELL_DISABLED` in either block.
  2. `at_screen_from_val` (the Lua door) accepts `primary = { kind = "tiles", cols = 1|2, items = {...}, more = {...} }`. An item reads `icon`, `tag`, `numeral` (at most 5 bytes) and `badge`. Unknown kinds keep raising the same message. Add three checks to `atlas_screen_test.c`: a valid tiles description; `cols = 3` is rejected ("tiles: cols must be 1 or 2"); more than 4 `more` items are rejected.
  3. `gw_ui_parts.c`, `at_part_tile(s, o, r, it, state, big)`:
     - Face: `at_plate(s, rr, face, edge, 3, AT_PX_CH_S)`, with `rr` lifted by 2 px when focused or pressed. The face is `AT_C_LIFT` when focused, else `AT_C_PLATE`. The edge is `AT_C_EMBER` when focused, else `AT_C_EDGE`.
     - Tick: `at_poly_rect(s, rr.x, rr.y + AT_PX_CH_S, 4, rr.h - 2 * AT_PX_CH_S, AT_C_EMBER)`. It starts below the top-left chamfer and ends above the bottom-right chamfer's row, so it never enters a corner.
     - Numeral badge (`big` rows): a 30x30 plate with a 5 px chamfer at `rr.x + 14`, centred vertically. It is ember-filled with `AT_C_INK` text when focused, else ground-filled with `AT_C_MUTED`.
     - Label: `a_title` (28) when `big`, else `a_cap20`. It is fitted to the width left after the badge, the tag and 14 px padding, so the fit rule steps down then truncates.
     - Tag: `at_part_tag(..., AT_TAG_JADE)` for `"MOD"`, right-aligned at `rr.x + rr.w - 10 - AT_PX_CH_S`, so it stays clear of the bottom-right chamfer.
     - Selected: a jade 3 px bar on the bottom edge, inset by the chamfer on both ends. No lift.
     - Disabled: a dim face, `AT_C_DIM` text, and the label suffixed by nothing (the reason goes in the explainer).
  4. `at_part_more(s, o, r, items, n, focus)` draws one quiet row: a 1 px `AT_C_LINE` outline as four thin rects that skip both chamfers, the word `MORE` in `a_cap12` muted, then the n labels as `a_cap14` text buttons. The focused one gets all three cues: it lifts 2, an ember underline as its front edge, and a 4 px ember tick at its left. Each label is fitted to `(r.w - 70) / n - 8`.
  5. `gw_ui_render.c`: `at_tiles_geometry`:
     - `big` rows (cols 1) are 56 px tall with a 6 px gap.
     - Hub tiles are 62 px tall with a 6 px vertical and 8 px horizontal gap, in `cols` columns across `L.primary` less 12 px padding.
     - The More row is 34 px tall, 6 px below the last row.
     - When the rows do not fit the height, the tile height shrinks to a 44 px minimum, then the grid scrolls by whole rows with the focus (reuse `at_list_scroll` on row indices).
     - Return the tile count.
     - `draw_tiles` draws each tile with its state and records `AT_HIT_CELL` hits (block 0 or 1, index). The `at_render_ex` dispatch gains `else if (sc->primary == AT_PRIMARY_TILES) draw_tiles(...)`.
  6. `gw_script_ui.inc:476`: replace the copied `362/39` list constants with a call into the renderer's geometry for lists (`at_list_visible(&L)`; add it next to `at_tiles_geometry`). Do the same for the tiles scroll.

- [ ] **Step 5: Run the new test, the old ones and the step-1 suites.**

```bash
nt atlas-tiles | tail -1          # atlas-tiles: N checks, 0 failed
for t in atlas-screen atlas-parts atlas-render atlas-binding; do nt $t | tail -1; done   # unchanged counts + the new screen checks, 0 failed
```

- [ ] **Step 6: Commit (game repo, then workspace repo).**

```bash
cd "$GW_MELEE" && git add pc/platform/gw_ui_screen.h pc/platform/gw_ui_screen.c pc/platform/gw_ui_parts.h pc/platform/gw_ui_parts.c pc/platform/gw_ui_render.h pc/platform/gw_ui_render.c pc/platform/gw_script_ui.inc pc/tests/atlas_tiles_test.c pc/tests/atlas_screen_test.c && git commit -m "atlas step 2: the tiles primary and the More strip (chamfers, three cues, fit at three widths)"
cd "$WS" && git add tools/port/native_test.sh && git commit -m "native_test: atlas-tiles"
```

---

### Task 2: The display screen (the title's face)

**Files:**
- Modify: `gw_ui_screen.h/.c`, `gw_ui_parts.h/.c`, `gw_ui_render.c`, `melee/pc/tests/atlas_tiles_test.c`

**Interfaces:**
Produces: `AT_PRIMARY_DISPLAY`, `AtScreen.hero[AT_STR]` (the wordmark), `AtScreen.prompt[AT_STR]` (the prompt under it), `AtScreen.foot_left[24]`, `AtScreen.foot_right[AT_STR]`; `void at_part_title(const AtSink*, const AtTextOps*, const AtLayout*, const AtScreen*, double now_ms, int reduced)`. A display screen has no focus blocks, records **no hit rectangles** and has no explainer. Its `keys` may hold one hint (START).

- [ ] **Step 1: Write the failing test.** Append to `atlas_tiles_test.c` and call `title_fits(); title_has_no_hits();` from `main`:

```c
static void title_fixture(void)
{
    memset(&SC, 0, sizeof SC); at_view_init(&V);
    snprintf(SC.id, sizeof SC.id, "title");
    SC.primary = AT_PRIMARY_DISPLAY; SC.preset = AT_PRESET_NONE;
    snprintf(SC.hero, AT_STR, "GD'S MELEE"); snprintf(SC.prompt, AT_STR, "PRESS START");
    snprintf(SC.foot_left, 24, "v0.1.7"); snprintf(SC.foot_right, AT_STR, "Original menu art");
}
static void title_fits(void)
{
    int w;
    for (w = 0; w < 3; w++) {
        AtSink s = rec_sink();
        AtLayout L;
        const RecText *h, *p;
        title_fixture();
        at_layout(WIDTHS[w], AT_PRESET_NONE, &L);
        at_render(&SC, &V, WIDTHS[w], 1e6, 0, &FAKE, &s, &H);
        h = find_text("GD'S MELEE"); p = find_text("PRESS START");
        CHECK(h != NULL && p != NULL);
        CHECK(h != NULL && at_role_size(h->role) >= 44);                 /* hero or display */
        CHECK(texts_legible());
        CHECK(text_inside(L.canvas));
        CHECK(h != NULL && p != NULL && p->base > h->base);
    }
}
static void title_has_no_hits(void)
{
    AtSink s = rec_sink();
    AtFocusBlock fb[AT_MAX_BLOCKS];
    title_fixture();
    at_render(&SC, &V, 853.0f, 1e6, 0, &FAKE, &s, &H);
    CHECK(H.n == 0);                                                     /* the mouse cannot act on the title */
    CHECK(at_screen_focus_blocks(&SC, fb) == 0);
    CHECK(at_screen_wants_pad(&SC) == 0);                                /* the title never reads the pad: retail does */
}
```

- [ ] **Step 2: Run it.** `nt atlas-tiles`. Expected: compile errors for `AT_PRIMARY_DISPLAY`, `hero`, `prompt`.

- [ ] **Step 3: Implement.** `at_part_title`:
  - The ground is opaque (the renderer already draws it).
  - The wordmark is `a_display` (64), centred, baseline at y 208, fitted to `L.content_w - 64`; at 640 it steps down to `a_hero` if needed.
  - Two 70x2 ember rules flank `PC PORT` (`a_cap16`, muted), baseline 240.
  - The prompt is a focused-style button plate: chamfer 5, lifted, ember edge, START glyph via `at_part_hint` and label `a_cap16`, centred at y 330. It pulses its edge alpha 0.6 to 1.0 over 1,200 ms on the UI clock; under `reduced` it does not pulse.
  - The foot texts are `a_num12` muted at left 32 and `a_body12` dim at right 32, baseline 456.
  - No hits.
  - `at_screen_wants_pad` returns 0 for `AT_PRIMARY_DISPLAY`.
  - The chamfer rule applies to the prompt plate: add `CHECK(corners_clear(prompt_rect, AT_PX_CH_S))`, using the rectangle `at_part_title` writes to an optional out-parameter (`AtRect *prompt_out`; pass NULL from the renderer).

- [ ] **Step 4: Run.** `nt atlas-tiles | tail -1` gives 0 failed. `nt atlas-render | tail -1` is unchanged.

- [ ] **Step 5: Commit (game repo).** `git commit -am "atlas step 2: the display screen (title face): wordmark, prompt, no hits, no pad"`

---

### Task 3: The entry registry (U6)

**Files:**
- Create: `melee/pc/platform/gw_ui_registry.h`, `gw_ui_registry.c`, `melee/pc/tests/atlas_registry_test.c`
- Modify (workspace): `tools/port/native_test.sh` (`atlas-registry`)

**Interfaces:**
```c
#define AT_REG_MAX 96
#define AT_REG_PER_MOD_PARENT 6
#define AT_REG_VISIBLE_PER_PARENT 12
#define AT_REG_LABEL_MAX 18
enum { AT_ENTRY_OPENS = 1, AT_ENTRY_SCRIPT = 2, AT_ENTRY_NATIVE = 3 };
typedef struct {
    char id[AT_ID * 2], parent[AT_ID], mod[AT_ID], label[AT_REG_LABEL_MAX + 1], blurb[AT_TEXT], icon[AT_ID], after[AT_ID * 2],
         opens[AT_ID * 2], badge[8];
    int action, online, visible, builtin, native_arg;  /* native_arg: what the adapter runs for AT_ENTRY_NATIVE */
} AtEntry;
typedef struct { AtEntry e[AT_REG_MAX]; int n; char log[4][96]; int nlog; } AtRegistry;
void at_reg_init(AtRegistry *r);
int  at_reg_is_parent(const char *id);                              /* the built-in nodes, section 8.1 */
/* 1 added; 0 refused, with one line in r->log. mod "" = a built-in entry. */
int  at_reg_add(AtRegistry *r, const AtEntry *e);
int  at_reg_set(AtRegistry *r, const char *mod, const char *id, int visible, const char *badge);   /* gd.ui.entry */
void at_reg_drop_mod(AtRegistry *r, const char *mod);                /* a mod switched off or unloaded */
/* the visible children of parent in order (builtins first in their own order, then mods by `after`, then by id);
 * netplay != 0 hides entries without `online` under versus and online. Returns the count (<= cap). */
int  at_reg_children(const AtRegistry *r, const char *parent, int netplay, const AtEntry **out, int cap);
```

- [ ] **Step 1: Write the failing test** `atlas_registry_test.c`:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_registry.h"

static AtEntry E(const char *mod, const char *id, const char *parent, const char *label, const char *after, int online)
{
    AtEntry e; memset(&e, 0, sizeof e);
    snprintf(e.mod, sizeof e.mod, "%s", mod); snprintf(e.id, sizeof e.id, "%s", id); snprintf(e.parent, sizeof e.parent, "%s", parent);
    snprintf(e.label, sizeof e.label, "%s", label); snprintf(e.after, sizeof e.after, "%s", after);
    e.action = AT_ENTRY_OPENS; e.online = online; e.visible = 1; e.builtin = mod[0] == '\0';
    return e;
}
static void order(void)
{
    AtRegistry r; const AtEntry *c[16]; int n;
    AtEntry b1 = E("", "training", "solo", "TRAINING", "", 0), b2 = E("", "lab", "solo", "LAB", "", 0);
    AtEntry m1 = E("envoy", "envoy", "solo", "ENVOY", "training", 0);
    at_reg_init(&r);
    CHECK(at_reg_add(&r, &b1) && at_reg_add(&r, &b2) && at_reg_add(&r, &m1));
    n = at_reg_children(&r, "solo", 0, c, 16);
    CHECK(n == 3);
    CHECK_STR(c[0]->id, "training"); CHECK_STR(c[1]->id, "envoy"); CHECK_STR(c[2]->id, "lab");   /* after = training */
}
static void caps(void)
{
    AtRegistry r; char id[32]; int i, added = 0; const AtEntry *c[32];
    at_reg_init(&r);
    for (i = 0; i < 9; i++) { AtEntry e; snprintf(id, sizeof id, "big.e%d", i); e = E("big", id, "solo", "X", "", 0); added += at_reg_add(&r, &e); }
    CHECK(added == AT_REG_PER_MOD_PARENT);                              /* 6 per mod per parent */
    CHECK(r.nlog >= 1);
    for (i = 0; i < 10; i++) { AtEntry e; snprintf(id, sizeof id, "m%d.e", i); { char mod[8]; snprintf(mod, sizeof mod, "m%d", i); e = E(mod, id, "solo", "Y", "", 0); at_reg_add(&r, &e); } }
    CHECK(at_reg_children(&r, "solo", 0, c, 32) == AT_REG_VISIBLE_PER_PARENT);   /* 12 visible: the rest are not listed */
}
static void unknown_parent(void)
{
    AtRegistry r; AtEntry e = E("envoy", "envoy", "nowhere", "ENVOY", "", 0);
    at_reg_init(&r);
    CHECK(at_reg_add(&r, &e) == 0);
    CHECK(r.nlog == 1 && strstr(r.log[0], "nowhere") != NULL);
}
static void namespace_rule(void)
{
    AtRegistry r; AtEntry ok = E("envoy", "envoy.daily", "solo", "DAILY", "", 0), bad = E("envoy", "lab", "solo", "LAB", "", 0),
                          own = E("envoy", "envoy", "solo", "ENVOY", "", 0);
    at_reg_init(&r);
    CHECK(at_reg_add(&r, &ok) == 1);
    CHECK(at_reg_add(&r, &own) == 1);                                   /* the mod's own id is allowed */
    CHECK(at_reg_add(&r, &bad) == 0);                                   /* another name is not */
}
static void label_cap(void)
{
    AtRegistry r; AtEntry e = E("envoy", "envoy", "solo", "", "", 0);
    at_reg_init(&r);
    snprintf(e.label, sizeof e.label, "%s", "ABCDEFGHIJKLMNOPQRSTUV");      /* snprintf already cuts at 18 */
    CHECK(strlen(e.label) == AT_REG_LABEL_MAX);
    CHECK(at_reg_add(&r, &e) == 1);
}
static void disabled_mod_adds_nothing(void)
{
    AtRegistry r; const AtEntry *c[8]; AtEntry e = E("envoy", "envoy", "solo", "ENVOY", "", 0);
    at_reg_init(&r); at_reg_add(&r, &e);
    at_reg_drop_mod(&r, "envoy");
    CHECK(at_reg_children(&r, "solo", 0, c, 8) == 0);
}
static void online_hidden(void)
{
    AtRegistry r; const AtEntry *c[8];
    AtEntry a = E("m", "m.safe", "versus", "SAFE", "", 1), b = E("m", "m.local", "versus", "LOCAL", "", 0), s = E("m", "m.solo", "solo", "SOLO", "", 0);
    at_reg_init(&r); at_reg_add(&r, &a); at_reg_add(&r, &b); at_reg_add(&r, &s);
    CHECK(at_reg_children(&r, "versus", 1, c, 8) == 1 && strcmp(c[0]->id, "m.safe") == 0);
    CHECK(at_reg_children(&r, "versus", 0, c, 8) == 2);
    CHECK(at_reg_children(&r, "solo", 1, c, 8) == 1);                    /* the rule is versus and online only */
}
static void set_visibility(void)
{
    AtRegistry r; const AtEntry *c[8]; AtEntry e = E("envoy", "envoy", "solo", "ENVOY", "", 0);
    at_reg_init(&r); at_reg_add(&r, &e);
    CHECK(at_reg_set(&r, "envoy", "envoy", 0, NULL) == 1);
    CHECK(at_reg_children(&r, "solo", 0, c, 8) == 0);
    CHECK(at_reg_set(&r, "other", "envoy", 1, NULL) == 0);              /* only the owner may change it */
    CHECK(at_reg_set(&r, "envoy", "envoy", 1, "NEW") == 1);
    CHECK(at_reg_children(&r, "solo", 0, c, 8) == 1 && strcmp(c[0]->badge, "NEW") == 0);
}
static void duplicate_id(void)
{
    AtRegistry r; AtEntry e = E("envoy", "envoy", "solo", "ENVOY", "", 0);
    at_reg_init(&r);
    CHECK(at_reg_add(&r, &e) == 1);
    CHECK(at_reg_add(&r, &e) == 0);
}
int main(void)
{
    order(); caps(); unknown_parent(); namespace_rule(); label_cap(); disabled_mod_adds_nothing(); online_hidden(); set_visibility(); duplicate_id();
    ATLAS_DONE("atlas-registry");
}
```

`native_test.sh`:

```bash
atlas-registry)
    sources=(pc/tests/atlas_registry_test.c pc/platform/gw_ui_registry.c pc/platform/gw_ui_menus_json.c) ;;
```

(`gw_ui_menus_json.c` arrives in Task 4. Until then, create it as an empty translation unit with only its header include, so this case links.)

- [ ] **Step 2: Run it and see it fail** (`nt atlas-registry`: the header is missing).
- [ ] **Step 3: Implement** `gw_ui_registry.c`:
  - The built-in parents are `main solo versus online mods settings more` and any `settings.<page>`. `pause` and `lab.pause` are refused with "parent not available until a later step".
  - `at_reg_add` refuses, with one log line each: an unknown parent; a duplicate id; a mod id that is neither `<mod>` nor `<mod>.<x>`; the seventh entry of one mod under one parent. A refused entry adds nothing.
  - `at_reg_children` takes the built-ins first, in insertion order. Each mod entry is then placed right after its `after` sibling when that sibling exists, else at the end, ties by id. It filters out `!visible` entries and (with `netplay`) entries without `online` under `versus` or `online`, and stops at 12.
  - The log keeps the first 4 lines; the host prints them.
- [ ] **Step 4: Run.** `nt atlas-registry | tail -1` gives 0 failed.
- [ ] **Step 5: Commit** (game repo: registry, header, test, the placeholder `gw_ui_menus_json.c`; workspace: `native_test.sh`).

---

### Task 4: `mod.json` `menus`

**Files:**
- Create: `melee/pc/platform/gw_ui_menus_json.h`, `gw_ui_menus_json.c`
- Modify: `melee/pc/platform/gw_mods.c`, `gw_mods.h`, `melee/pc/tests/atlas_registry_test.c`

**Interfaces:**
```c
/* gw_ui_menus_json.h: reads the "menus" array of a mod.json text into AtEntry records (mod filled in). Pure. */
int at_menus_parse(const char *json, const char *mod, AtEntry *out, int cap, char *err, int errcap);   /* the count; -1 on a syntax error */
/* gw_mods.h, all ints and const char*, callable from game code without the gw_ prefix */
int gw_Mods_MenuCount(int i);                                   /* entries this mod's mod.json declares (0 when inactive) */
const char *gw_Mods_MenuField(int i, int k, const char *field); /* "id" "parent" "label" "blurb" "icon" "after" "opens" "action" "online" */
const char *gw_Mods_MenuSummary(int i);                         /* "adds Solo > Envoy" or "" */
```

The manifest shape is the spec's (8.1):

```json
"menus": [
  { "id": "envoy", "parent": "solo", "label": "ENVOY", "blurb": "Explore, fight and evolve your build.",
    "icon": "ico_envoy", "after": "training", "action": "script", "online": false }
]
```

`action` is `"script"` (the mod's `on_entry(id)` runs) or absent with `opens` naming a `gd.ui` screen. `online` takes `true`/`false` or the strings, as the strings-only reader allows.

- [ ] **Step 1: Write the failing tests.** Append to `atlas_registry_test.c` (and call them from `main`):

```c
#include "../platform/gw_ui_menus_json.h"
static void menus_parse_ok(void)
{
    AtEntry e[4]; char err[96];
    const char *j = "{ \"id\": \"envoy\", \"kind\": \"script\", \"menus\": [ { \"id\": \"envoy\", \"parent\": \"solo\", \"label\": \"ENVOY\","
                    " \"blurb\": \"Explore, fight and evolve your build.\", \"after\": \"training\", \"action\": \"script\", \"online\": false } ],"
                    " \"gameplay\": true }";
    CHECK(at_menus_parse(j, "envoy", e, 4, err, sizeof err) == 1);
    CHECK_STR(e[0].id, "envoy"); CHECK_STR(e[0].parent, "solo"); CHECK_STR(e[0].mod, "envoy");
    CHECK(e[0].action == AT_ENTRY_SCRIPT); CHECK(e[0].online == 0); CHECK(e[0].visible == 1);
}
static void menus_parse_rejects(void)
{
    AtEntry e[4]; char err[96];
    CHECK(at_menus_parse("{ \"menus\": [ { \"id\": \"x\", \"parent\": \"solo\" } ] }", "m", e, 4, err, sizeof err) == 0);    /* no label: skipped */
    CHECK(at_menus_parse("{ \"menus\": [ { \"id\": \"m.a\", \"parent\": \"solo\", \"label\": \"A\", \"opens\": \"m.s\" } ] }", "m", e, 4, err, sizeof err) == 1);
    CHECK(e[0].action == AT_ENTRY_OPENS);
    CHECK(at_menus_parse("{ \"menus\": [ { \"id\": \"m.a\", \"parent\": \"solo\", \"label\": \"A\" } ] }", "m", e, 4, err, sizeof err) == 0);   /* neither opens nor action */
    CHECK(at_menus_parse("{ \"menus\": [ { \"id\": ", "m", e, 4, err, sizeof err) == -1);
    CHECK(at_menus_parse("{ \"name\": \"no menus\" }", "m", e, 4, err, sizeof err) == 0);
    CHECK(at_menus_parse("{ \"menus\": [ {\"id\":\"m.a\",\"parent\":\"solo\",\"label\":\"A\",\"action\":\"script\",\"nested\":{\"x\":[1,2]}} ] }", "m", e, 4, err, sizeof err) == 1);
}
```

Then add a **real-file** check: parse `pc/scripts/examples/envoy/mod.json` from disk after Task 11 adds its `menus`. Until then this check expects 0 entries. Task 11 flips it to 1. The test is run from the game repo root:

```c
static void envoy_manifest(void)
{
    FILE *f = fopen("pc/scripts/examples/envoy/mod.json", "rb"); char buf[4096]; size_t n; AtEntry e[4]; char err[96];
    CHECK(f != NULL);
    if (f == NULL) return;
    n = fread(buf, 1, sizeof buf - 1, f); fclose(f); buf[n] = '\0';
    CHECK(at_menus_parse(buf, "envoy", e, 4, err, sizeof err) == ENVOY_MENUS_EXPECTED);
}
#ifndef ENVOY_MENUS_EXPECTED
#define ENVOY_MENUS_EXPECTED 0
#endif
```

(Place the `#define` above the function. `native_test.sh` runs the test binary from `$GW_MELEE`; confirm with `grep -n "cd \"\$GW_MELEE\"\|pushd" "$WS/tools/port/native_test.sh"`. If it runs elsewhere, pass the path through an environment variable `ATLAS_GAME_ROOT` that the case sets.)

- [ ] **Step 2: Run, fail** (`nt atlas-registry`).
- [ ] **Step 3: Implement** `at_menus_parse` as a small dedicated reader:
  - It scans the top level for the key `"menus"` and skips every other value with a balanced skipper that handles nested arrays, objects and strings with escapes.
  - Inside `menus`, each element is a flat object read as strings or booleans. Nested values inside an element are skipped.
  - An element without `id`, `parent` or `label`, or without `opens` and `action`, is skipped and logged into `err`.
  - Then wire it into `gw_mods.c`: after `mod_parse_json` succeeds, call `at_menus_parse(text, m->id, ...)` into a per-mod array (at most 6 entries; `GW_MODS_MAX` mods times 6 entries is about 220 KB, so allocate per mod with `malloc` only when the count is non-zero).
  - `gw_Mods_MenuSummary` builds `adds Solo > Envoy` from the first entry, using a parent display-name table: solo Solo, versus Versus, online Online, mods Mods, settings Settings, more More.
  - An inactive mod returns 0 and `""`. This is the "disabled mod adds nothing" rule at the source.
- [ ] **Step 4: Run.** `nt atlas-registry | tail -1` gives 0 failed. Also confirm the host build compiles: `tools/port/build.sh` from `$MAIN` with the lane exports (a full build; it is the only way `gw_mods.c` is compiled). Then `grep -a "adds %s > %s\|adds Solo" "$GW_BUILD_ROOT/melee-pc.exe" | head -1` prints a line.
- [ ] **Step 5: Commit (game repo).** `git commit -m "mods: mod.json menus (an array of flat objects) and the summary line"`

---

### Task 5: Engine-owned screens in the binding, the intent queue and the `Ui_*` shims

**This task closes the ownership and lifetime holes before any menu uses them.**

**Files:**
- Modify: `melee/pc/platform/gw_script_ui.inc`, `melee/pc/tests/atlas_binding_test.c`

**Interfaces:**
```c
#define GS_UI_ENGINE (-2)        /* GsUiSlot.owner for a native screen */
/* GsUiSlot gains: int scene;   the scene kind that was current when it was pushed (-1 = any) */
/* host shims; game code declares them WITHOUT the gw_ prefix (gmfrontend_menus.inc:250 is the pattern) */
int  gw_Ui_Ready(void);                                    /* roles ok and MELEE_ATLAS != 0 */
int  gw_Ui_Begin(const char *id, int primary, int chapter, const char *title);   /* starts a scratch record; 0 if not ready */
void gw_Ui_Trail(const char *parent);                      /* at most 3 */
void gw_Ui_Tile(const char *id, const char *label, const char *tag, const char *numeral, int flags);
void gw_Ui_More(const char *id, const char *label);
void gw_Ui_Explain(const char *kicker, const char *title, const char *what);
void gw_Ui_ExplainWith(const char *tag);
void gw_Ui_Key(int button, const char *label);             /* 'A' 'B' 'X' 'Y' 'Z' 'L' 'R' 'S' */
void gw_Ui_Display(const char *hero, const char *prompt, const char *foot_left, const char *foot_right);
int  gw_Ui_Commit(int focus_block, int focus_index);       /* replace the engine slot for that id if changed; push it if absent; 1 if it is the top */
void gw_Ui_Intent(int type, int a);                        /* AT_EV_MOVE / ACCEPT / BACK / ALT / PAGE from the game's own menu input */
int  gw_Ui_PollEvent(int *type, int *block, int *index);   /* the engine screen's events: FOCUS, ACCEPT, BACK, ALT, ENTRY */
void gw_Ui_Close(const char *id);
int  gw_Ui_TopIsEngine(const char *id);                    /* 1 when that engine screen is the top (it alone takes input) */
void gw_Ui_SceneExit(int scene_kind);                      /* closes every slot pushed during that scene (engine and mod) */
```

The rules this task implements:

| Who | register / replace | open | close | feed | focus readback |
|---|---|---|---|---|---|
| engine (`gw_Ui_*`) | its own ids only (ids without a dot, or `more.*`, `solo.*`, `versus.*`, `title`) | yes | yes | `gw_Ui_Intent` | yes |
| a mod script | its `<mod>.*` ids only; an engine id raises `belongs to the engine` | its own; an engine id raises | its own | its own | its own |
| the console | **not** engine ids (raises `belongs to the engine`) | its own and mods' (as step 1) | as step 1 | as step 1 | any |

- [ ] **Step 1: Re-check D2 on the current tree.**

```bash
cd "$GW_MELEE"; grep -an "gs_ui_tick();\|gs_ui_draw();" pc/platform/gw_script.c | tr -d '\000'
grep -n "Script_Tick();\|Script_PostRender();" src/melee/gm/gmscene.c
```

Expected: one `gs_ui_tick();` inside `gw_Script_Tick`, one `gs_ui_draw();` inside `gs_finish_draw`, and the two calls in the scene loop of `gmscene.c`.
  - **If they are there:** continue.
  - **If either is now gated** (for example `if (gs.match_active)`): do not move the gate. Add an `|| gs_ui_has_engine_top()` condition at that gate, and add a test in step 2 that the engine screen ticks with `match_active = 0`.

- [ ] **Step 2: Write the failing tests.** `atlas_binding_test.c` already includes `gw_script_ui.inc` against stand-ins and a real Lua state (read its top 120 lines first for the stand-in names: `gs`, `gs_may_run`, `gs_pcall`, the kit stubs, `gw_Mouse_ScriptRead`). Add these functions and call them from `main`. **Each test drives the screen the way its real owner does**: the engine through `gw_Ui_*`, a mod through a script slot set as `gs.cur = <mod script index>`. The console is used only in `console_cannot_touch_engine`.

```c
static int engine_menu(const char *id, int n)
{
    int i;
    char tid[16];
    if (!gw_Ui_Begin(id, AT_PRIMARY_TILES, 0, "MAIN MENU")) return 0;
    for (i = 0; i < n; i++) { snprintf(tid, sizeof tid, "t%d", i); gw_Ui_Tile(tid, tid, "", "", 0); }
    gw_Ui_Key('A', "Open"); gw_Ui_Key('B', "Title");
    return gw_Ui_Commit(0, 0);
}
static void engine_slot_survives_tick(void)
{
    reset_ui();                                   /* the existing helper that clears slots and the stack; add it if absent */
    CHECK(engine_menu("main", 5) == 1);
    for (int f = 0; f < 10; f++) gs_ui_tick();
    CHECK(gw_Ui_TopIsEngine("main") == 1);        /* the gs_ui_usable() check must not release an engine slot */
}
static void engine_slot_not_released_by_script_unload(void)
{
    reset_ui();
    engine_menu("main", 5);
    fake_script(3, "envoy");                       /* a mod script in slot 3 */
    gs.cur = 3; CHECK(t_lua("gd.ui.screen{ id='envoy.setup', primary={kind='list', items={{id='a', label='A'}}}, on={back=function() return {pop=true} end} }; return gd.ui.open('envoy.setup')"));
    CHECK(gw_Ui_TopIsEngine("main") == 0);
    gs_ui_release(3);                              /* the script unloads while its screen covers the menu */
    CHECK(gw_Ui_TopIsEngine("main") == 1);
    gs_ui_release(GS_UI_ENGINE);                   /* a release keyed by the engine id does nothing */
    CHECK(gw_Ui_TopIsEngine("main") == 1);
}
static void uncover_primes_engine_screen(void)
{
    int t, b, i;
    reset_ui();
    engine_menu("main", 5);
    fake_script(3, "envoy");
    gs.cur = 3; t_lua("gd.ui.screen{ id='envoy.s', primary={kind='list', items={{id='a', label='A'}}}, on={back=function() return {pop=true} end} }; gd.ui.open('envoy.s')");
    fake_pad_hold(1, AT_PAD_B);                   /* B held: it closes envoy.s ... */
    gs_ui_tick();
    gs_ui_tick();
    CHECK(gw_Ui_TopIsEngine("main") == 1);
    while (gw_Ui_PollEvent(&t, &b, &i)) CHECK(t != AT_EV_BACK);   /* ... and the same held B must not back out of the main menu */
}
static void native_intents_are_primed(void)
{
    int t, b, i, accepts = 0;
    reset_ui();
    gw_Ui_Intent(AT_EV_ACCEPT, 0);                /* an intent before the screen exists is dropped */
    engine_menu("main", 5);
    while (gw_Ui_PollEvent(&t, &b, &i)) if (t == AT_EV_ACCEPT) accepts++;
    CHECK(accepts == 0);
    gw_Ui_Intent(AT_EV_MOVE, AT_DIR_DOWN);
    CHECK(gw_Ui_PollEvent(&t, &b, &i) == 1 && t == AT_EV_FOCUS && b == 0 && i == 1);
    gw_Ui_Intent(AT_EV_ACCEPT, 0);
    CHECK(gw_Ui_PollEvent(&t, &b, &i) == 1 && t == AT_EV_ACCEPT && i == 1);
}
static void intents_from_any_port(void)
{
    /* the engine screen does not read a port: the game feeds the merged menu input of all ports */
    reset_ui();
    engine_menu("main", 5);
    CHECK(gs_ui_slot[gs_ui_find("main")].sc.input_feed == 1);
}
static void engine_screen_covered_takes_no_intent(void)
{
    int t, b, i;
    reset_ui();
    engine_menu("main", 5);
    fake_script(3, "envoy");
    gs.cur = 3; t_lua("gd.ui.screen{ id='envoy.s', primary={kind='list', items={{id='a', label='A'}}} }; gd.ui.open('envoy.s')");
    gw_Ui_Intent(AT_EV_ACCEPT, 0);
    CHECK(gw_Ui_PollEvent(&t, &b, &i) == 0);
}
static void scene_exit_closes_scene_screens(void)
{
    reset_ui();
    gs.scene_kind = 1;                             /* GS_FRONTEND's kind in the stand-in */
    engine_menu("main", 5);
    fake_script(3, "envoy");
    gs.cur = 3; t_lua("gd.ui.screen{ id='envoy.s', primary={kind='list', items={{id='a', label='A'}}} }; gd.ui.open('envoy.s')");
    gw_Ui_SceneExit(1);
    CHECK(gs_ui_stack.n == 0);                     /* neither the menu nor the mod screen reaches the next scene */
    gs.scene_kind = 2;
    gs.cur = 3; t_lua("gd.ui.open('envoy.s')");     /* the bag pattern: opened inside a match */
    gw_Ui_SceneExit(1);                            /* another scene's exit leaves it alone */
    CHECK(gs_ui_stack.n == 1);
}
static void console_cannot_touch_engine(void)    /* console-only check: labelled */
{
    reset_ui();
    engine_menu("main", 5);
    gs.cur = gs.console;
    CHECK(!t_lua("gd.ui.close('main')"));
    CHECK(strstr(t_lua_err(), "belongs to the engine") != NULL);
    CHECK(!t_lua("gd.ui.screen{ id='main', primary={kind='list', items={{id='a', label='A'}}} }"));
}
static void mod_cannot_take_engine_id(void)
{
    reset_ui();
    engine_menu("main", 5);
    fake_script(3, "envoy");
    gs.cur = 3;
    CHECK(!t_lua("gd.ui.screen{ id='main', primary={kind='list', items={{id='a', label='A'}}} }"));
}
static void commit_without_change_does_not_rebuild(void)
{
    int before;
    reset_ui();
    engine_menu("main", 5);
    before = gs_ui_slot[gs_ui_find("main")].rebuilds;   /* add `rebuilds` to GsUiSlot */
    engine_menu("main", 5);
    CHECK(gs_ui_slot[gs_ui_find("main")].rebuilds == before);
    engine_menu("main", 4);
    CHECK(gs_ui_slot[gs_ui_find("main")].rebuilds == before + 1);
}
static void eight_slots_with_engine(void)
{
    /* the engine's screens count against the 8 slots: the front door uses at most 2 at once (menu, title) */
    reset_ui();
    engine_menu("main", 5);
    CHECK(gs_ui_engine_slots() <= 2);
}
```

`fake_script`, `fake_pad_hold`, `t_lua` and `t_lua_err` may already exist under other names in `atlas_binding_test.c`. Use the existing ones and add only what is missing. Add the new sources the binding needs (`gw_ui_registry.c`, `gw_ui_menus_json.c`, `gw_ui_policy.c` once Task 7 lands) to the `atlas-binding` case in `native_test.sh`.

- [ ] **Step 3: Run, fail.** `nt atlas-binding`: the `gw_Ui_*` functions are missing.
- [ ] **Step 4: Implement** in `gw_script_ui.inc`:
  1. `gs_ui_usable(owner)` returns 1 for `GS_UI_ENGINE`. `gs_ui_release(script)` returns at once for `script < 0`. `gs_ui_tick`'s `if (!gs_ui_usable(u->owner)) { gs_ui_release(...) }` is skipped for the engine owner. `gs_may_run` still gates engine screens on resimulated frames; a menu never resimulates, but the rule is uniform.
  2. Engine slots: `gw_Ui_Begin` fills `gs_ui_scratch` directly (no Lua, no value tree), with `input_feed = 1` and `owner = GS_UI_ENGINE`. `gw_Ui_Commit` finds or allocates the slot for the id. It `memcmp`s the scratch against the slot's record; only on a difference does it copy, run `at_screen_refocus` on the same id and increment `rebuilds`. If the slot is not on the stack, it pushes it (`gs_ui_open_screen`, which primes). It records `scene = gs.scene_kind`. It returns `at_stack_top(...) == slot`. The engine never has Lua refs, so `gs_ui_unref_screen` is not called for it.
  3. The event queue: `static struct { int type, block, index; } gs_ui_q[16]; int gs_ui_qn;` For an engine slot, `gs_ui_event` does not call Lua. FOCUS changes are applied to the view, then queued as `AT_EV_FOCUS`. ACCEPT (only when `at_cell_accepts`), BACK, ALT and PAGE are queued with the focused block and index. `gw_Ui_PollEvent` pops in order. Keyboard and mouse events for an engine top screen go through the same path from `gs_ui_tick`.
  4. `gw_Ui_Intent` builds one `AtEvent` and runs `gs_ui_event` immediately, but only when the engine screen is the top. It is dropped otherwise, and dropped for the first frame after the screen became the top (the prime rule: a press that opened it must not act on it). Track that frame with `u->primed_ms`; an intent within the same UI tick as `gs_ui_open_screen` is dropped.
  5. Ownership guards: `l_ui_screen`, `gs_ui_slot_arg` (used by `open`, `close(id)`, `feed`, `focus`, `set_focus`) raise `gd.ui: screen "<id>" belongs to the engine` when the slot's owner is `GS_UI_ENGINE`, for every caller including the console. `gs_ui_may_touch` keeps its step-1 meaning for script slots.
  6. Scene tags: `gw_Ui_SceneExit(kind)` removes (without calling Lua `on.close` for engine slots; with it for script slots, through `gs_ui_close_screen`) every stack entry whose slot `scene == kind`. Call it from the binding's scene hook: `Script_SceneBegin` already runs per scene (`gmscene.c:803-805`). In it, call `gw_Ui_SceneExit(previous kind)` before recording the new kind. Find `gs.scene_kind` being set: `grep -an "scene_kind = " pc/platform/gw_script.c | tr -d '\000'`.
  7. `gw_Ui_Ready()` returns `gs_ui_roles_ok() && atlas_env_on()`, where `atlas_env_on` reads `MELEE_ATLAS` once (absent or anything but `"0"` means on).
- [ ] **Step 5: Run.** `nt atlas-binding | tail -1` gives 0 failed, with the step-1 checks still passing. Then:

```bash
cd "$GW_MELEE" && grep -n "gs_ui_release(u->owner)" pc/platform/gw_script_ui.inc     # still present, now behind the engine exemption
grep -n "input_mask" pc/platform/gw_script_ui.inc                                     # nothing: Atlas never masks
```

- [ ] **Step 6: Commit (game repo; workspace for `native_test.sh`).** `git commit -m "gd.ui: engine-owned screens (native menus): intents, an event queue, scene tags; ownership guards"`

---

### Task 6: Entries at run time: boot, `gd.ui.entry`, `on_entry`, and the stand-in

**Files:**
- Modify: `melee/pc/platform/gw_script_ui.inc`, `melee/pc/tests/atlas_binding_test.c`, `melee/pc/tests/atlas_ui_stub.lua`, `melee/pc/tests/atlas_ui_stub_test.lua`

**Interfaces:**
```c
static AtRegistry gs_ui_reg;                      /* filled at boot from active mods' manifests and the built-ins */
int  gw_Ui_EntryCount(const char *parent);        /* visible children (netplay rule applied) */
const char *gw_Ui_EntryField(const char *parent, int k, const char *field);   /* "id" "label" "blurb" "tag" ("MOD" for a mod entry) "badge" */
int  gw_Ui_EntryActivate(const char *parent, int k);  /* 1 handled (a screen pushed or on_entry ran); 0 refused (logged) */
```
Lua: `gd.ui.entry(id, { visible = bool, badge = "NEW" | nil })` returns `true` when the caller's mod owns that entry. A mod script may define `function on_entry(id) ... end`; it runs when one of its entries with `"action": "script"` is chosen. Its result may be `{ push = "<mod>.<screen>" }`.

- [ ] **Step 1: Write the failing tests** in `atlas_binding_test.c`. These run as the mod (real path), not the console.

```c
static void entry_opens_pushes_mod_screen(void)
{
    reset_ui(); reg_boot_with("{\"menus\":[{\"id\":\"envoy\",\"parent\":\"solo\",\"label\":\"ENVOY\",\"opens\":\"envoy.setup\"}]}", "envoy");
    engine_menu("solo", 6);
    fake_script(3, "envoy");
    gs.cur = 3; t_lua("gd.ui.screen{ id='envoy.setup', primary={kind='list', items={{id='a', label='A'}}} }");
    gs.cur = -1;                                         /* activation comes from the engine, not from a script */
    CHECK(gw_Ui_EntryCount("solo") == 1);
    CHECK(gw_Ui_EntryActivate("solo", 0) == 1);
    CHECK(strcmp(gs_ui_slot[at_stack_top(&gs_ui_stack)].sc.id, "envoy.setup") == 0);
    CHECK(gs_ui_slot[at_stack_top(&gs_ui_stack)].owner == 3);   /* the screen keeps its owner: its handlers run as envoy */
}
static void entry_script_runs_on_entry_as_the_mod(void)
{
    reset_ui(); reg_boot_with("{\"menus\":[{\"id\":\"envoy\",\"parent\":\"solo\",\"label\":\"ENVOY\",\"action\":\"script\"}]}", "envoy");
    fake_script(3, "envoy");
    gs.cur = 3; t_lua("function on_entry(id) gd.log('entry '..id..' as '..tostring(gd.script_id and gd.script_id() or '?')); ENTRY_SEEN = id end");
    gs.cur = -1;
    CHECK(gw_Ui_EntryActivate("solo", 0) == 1);
    gs.cur = 3; CHECK(t_lua("return ENTRY_SEEN == 'envoy'"));
    CHECK(last_pcall_owner() == 3);                         /* called through gs_pcall(owner = the mod), not the console */
}
static void entry_missing_screen_refused(void)
{
    reset_ui(); reg_boot_with("{\"menus\":[{\"id\":\"envoy\",\"parent\":\"solo\",\"label\":\"ENVOY\",\"opens\":\"envoy.nope\"}]}", "envoy");
    CHECK(gw_Ui_EntryActivate("solo", 0) == 0);
}
static void entry_from_other_script_cannot_hide(void)
{
    reset_ui(); reg_boot_with("{\"menus\":[{\"id\":\"envoy\",\"parent\":\"solo\",\"label\":\"ENVOY\",\"action\":\"script\"}]}", "envoy");
    fake_script(4, "other");
    gs.cur = 4; CHECK(t_lua("return gd.ui.entry('envoy', {visible=false}) == false"));
    fake_script(3, "envoy");
    gs.cur = 3; CHECK(t_lua("return gd.ui.entry('envoy', {visible=false}) == true"));
    CHECK(gw_Ui_EntryCount("solo") == 0);
}
static void entry_hidden_in_netplay(void)
{
    reset_ui(); reg_boot_with("{\"menus\":[{\"id\":\"m.v\",\"parent\":\"versus\",\"label\":\"V\",\"action\":\"script\"}]}", "m");
    fake_netplay(1);
    CHECK(gw_Ui_EntryCount("versus") == 0);
    CHECK(gw_Ui_EntryActivate("versus", 0) == 0);
    fake_netplay(0);
}
static void entry_screen_closed_on_scene_exit(void)
{
    reset_ui(); reg_boot_with("{\"menus\":[{\"id\":\"envoy\",\"parent\":\"solo\",\"label\":\"ENVOY\",\"opens\":\"envoy.setup\"}]}", "envoy");
    gs.scene_kind = 1; engine_menu("solo", 6);
    fake_script(3, "envoy");
    gs.cur = 3; t_lua("gd.ui.screen{ id='envoy.setup', primary={kind='list', items={{id='a', label='A'}}} }");
    gs.cur = -1; gw_Ui_EntryActivate("solo", 0);
    gw_Ui_SceneExit(1);
    CHECK(gs_ui_stack.n == 0);
}
static void entry_mod_unloaded(void)
{
    reset_ui(); reg_boot_with("{\"menus\":[{\"id\":\"envoy\",\"parent\":\"solo\",\"label\":\"ENVOY\",\"action\":\"script\"}]}", "envoy");
    fake_script(3, "envoy");
    gs_ui_release(3); fake_script_off(3);
    CHECK(gw_Ui_EntryActivate("solo", 0) == 0);          /* no owner to run on_entry: refused, logged, no crash */
}
```

`reg_boot_with(json, mod)` is a test helper that calls `at_reg_init`, `at_menus_parse` and `at_reg_add`. The real boot (step 3) reads `gw_Mods_*`. `last_pcall_owner()` is a stand-in counter set by the test's `gs_pcall` stand-in; add it if missing.

Stand-in (`atlas_ui_stub.lua`) additions, with tests in `atlas_ui_stub_test.lua`:
  - `Stub:entry(id, t)`: owner check by `owner_mod`.
  - `Stub:engine_activate(id)`: plays the engine's part; it calls the stub-held `on_entry` or pushes `opens`.
  - `Stub:register_entry{ id, parent, label, opens | action, online }`: validates like `at_menus_parse` (label, id namespace, parent in the built-in list).
  - The docs line "It is NOT the engine" gains: "no registry caps or ordering".

- [ ] **Step 2: Run, fail** (`nt atlas-binding`; `lua pc/tests/atlas_ui_stub_test.lua` from `$GW_MELEE`).
- [ ] **Step 3: Implement.**
  - Boot: on the first `gs_ui_tick`, fill `gs_ui_reg` once. The built-ins come from the adapter (Task 8 registers them through `gw_Ui_EntryBuiltin(parent, id, label, native_arg)`; until then the registry has only mods). Then, for every active mod `i`, `gw_Mods_MenuField(i, k, ...)` gives the entries, each passed to `at_reg_add`, and `r.log` lines go to `gw_log("ui: registry: %s")`.
  - A mod that becomes disabled or unloaded at run time: `gs_ui_release` also calls `at_reg_drop_mod(&gs_ui_reg, <its mod id>)`.
  - `gw_Ui_EntryActivate`:
    - It refuses in netplay for non-online entries.
    - For `AT_ENTRY_OPENS` it finds the slot by id. It refuses when the slot is not the entry's mod's, or the owner is not usable. Otherwise it calls `gs_ui_open_screen`.
    - For `AT_ENTRY_SCRIPT` it finds the mod's script index (the first used, enabled script whose id starts with `<mod>/`, the way `gw_Script_LabAvailable` matches `geno-lab/`). Then it calls `on_entry(id)` through `gs_get_hook` and `gs_pcall(owner, 1, 1, "on_entry")`, so the budget and the owner are the mod's. It applies a `{push=}` result with `gs_ui_apply_result(owner)`.
    - Every refusal logs one line.
  - `gd.ui.entry` is added to `gs_ui_funcs`.
- [ ] **Step 4: Run** both suites; 0 failed. `cd "$GW_MELEE" && lua pc/tests/atlas_ui_stub_test.lua | tail -1`.
- [ ] **Step 5: Commit (game repo).** `git commit -m "gd.ui: the entry registry at run time: manifest entries, gd.ui.entry, on_entry as the owning mod, netplay rule"`

---

### Task 7: The scene policy table (RETAIL, OVERLAY, REPLACE)

**Files:**
- Create: `melee/pc/platform/gw_ui_policy.h`, `gw_ui_policy.c`, `melee/pc/tests/atlas_policy_test.c`
- Modify: `melee/src/melee/gm/gm_1A3F.c` (one `TARGET_PC` block), `melee/pc/platform/gw_script_ui.inc` (the shim), workspace `tools/port/native_test.sh` (`atlas-policy`)

**Interfaces:**
```c
enum { AT_POLICY_RETAIL = 0, AT_POLICY_OVERLAY = 1, AT_POLICY_REPLACE = 2 };
typedef struct { int scene_kind; int policy; const char *screen; } AtPolicyRow;
/* the default table: { GS_TITLE, OVERLAY, "title" } only; every other scene RETAIL */
int at_policy_for(int scene_kind, int atlas_on, const char *env_override);   /* env: "MELEE_ATLAS_SCENES" e.g. "0:retail,40:replace" */
const char *at_policy_screen(int scene_kind);
int gw_Ui_ScenePolicy(int scene_kind);        /* the shim the game calls as Ui_ScenePolicy */
```
Game side (in `gm_801A4014`):
```c
#if defined(TARGET_PC)
    {
        extern int Ui_ScenePolicy(int);
        extern GameScene* gmFrontend_AtlasStandIn(u8 kind);      /* gmfrontend_atlas.inc */
        if (Ui_ScenePolicy(kind) == 2 /* AT_POLICY_REPLACE */) {
            GameScene* stand_in = gmFrontend_AtlasStandIn(kind);
            if (stand_in != NULL) scene = stand_in;              /* NULL: no stand-in for that scene, stay retail */
        }
    }
#endif
```
OVERLAY needs no game-side change at this hook: the retail pair runs, and the adapter pushes the overlay's engine screen from `Script_SceneBegin`'s kind (Task 12).

- [ ] **Step 1: Re-check D3.**

```bash
cd "$GW_MELEE" && sed -n 158,200p src/melee/gm/gm_1A3F.c
grep -rn "scene->on_enter\|->on_frame" src/melee/gm/*.c | grep -v "^src/melee/gm/gm_1A3F.c"
```

Expected: `scene = (GameScene*) ((uintptr_t) gm_FindGameSceneHandler(kind) | (zero = 0));`, then `scene->on_enter(...)`, then `gm_801A4D34(scene->on_frame, info)`, and no other caller of a scene's pair.
  - **If so:** the hook goes right after the `scene = ...` line and before `gm_801A4BD4()`. Keep the `| (zero = 0)` line untouched; its comment explains a register-allocation constraint for the matching build. The `TARGET_PC` block is outside matching.
  - **If another caller exists:** put the same block there too, and list both lines in the commit message.
- [ ] **Step 2: Write the failing test** `atlas_policy_test.c`:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_policy.h"
#define GS_TITLE_K 0      /* the scene kinds as numbers: read them from gm/types.h with grep, do not guess */
int main(void)
{
    CHECK(at_policy_for(GS_TITLE_K, 1, NULL) == AT_POLICY_OVERLAY);
    CHECK(at_policy_for(GS_TITLE_K, 0, NULL) == AT_POLICY_RETAIL);           /* MELEE_ATLAS=0: everything retail */
    CHECK(at_policy_for(5, 1, NULL) == AT_POLICY_RETAIL);                    /* any other scene: retail by default */
    CHECK(at_policy_for(GS_TITLE_K, 1, "0:retail") == AT_POLICY_RETAIL);     /* the override wins */
    CHECK(at_policy_for(40, 1, "0:retail,40:replace") == AT_POLICY_REPLACE);
    CHECK(at_policy_for(40, 1, "40:bogus") == AT_POLICY_RETAIL);             /* a bad word is ignored */
    CHECK(at_policy_for(40, 1, "nonsense") == AT_POLICY_RETAIL);
    CHECK(at_policy_screen(GS_TITLE_K) != NULL && strcmp(at_policy_screen(GS_TITLE_K), "title") == 0);
    CHECK(at_policy_screen(5) == NULL);
    ATLAS_DONE("atlas-policy");
}
```

Get the real `GS_TITLE` value first: `grep -n "GS_TITLE\b" "$GW_MELEE/src/melee/gm/types.h"`. If it is an enum without an explicit value, count from the enum start, or compile a two-line PowerPC file that prints nothing but has `_Static_assert(GS_TITLE == 0, "")`, and adjust until it passes. Write the number into the test with a comment naming the enum line.

- [ ] **Step 3: Run, fail; implement; run.** `nt atlas-policy | tail -1` gives 0 failed. Implement `gw_Ui_ScenePolicy` in the binding as `at_policy_for(kind, atlas_env_on(), getenv("MELEE_ATLAS_SCENES"))`, read once per scene. Implement `gmFrontend_AtlasStandIn` in `gmfrontend_atlas.inc` (Task 8 creates the file) returning NULL for every kind in step 2. **REPLACE has no user in this step** (decision D3); the stand-in table is the step-8 extension point.
- [ ] **Step 4: PowerPC syntax check** of the game file: `ppc "$GW_MELEE/src/melee/gm/gm_1A3F.c" && echo ok`.
- [ ] **Step 5: Commit** (game repo; workspace `native_test.sh`). `git commit -m "atlas: the scene policy table (retail by default, the title overlay, replace built for step 8)"`

---

### Task 8: The game-side adapter for the menu tree (`FM_ATLAS`)

**Files:**
- Create: `melee/src/melee/gm/gmfrontend_atlas.inc`, workspace `tools/port/test_fe_atlas_positions.py`
- Modify: `melee/src/melee/gm/gmfrontend.c` (the include), `gmfrontend_menus.inc` (the screen id per menu, the early branch)

**Interfaces:**
```c
/* gmfrontend_menus.inc: FeMenu gains `const char* atlas_id;` ("main", "solo", ...). */
static bool fa_on(const FeMenu* m);            /* Ui_Ready() && m->atlas_id != NULL */
static void fa_submit(const FeMenu* m);        /* fm.vis[] -> Ui_Tile; registry children -> Ui_Tile with tag "MOD"; keys; explainer */
static void fa_frame(void);                    /* early in fm_scene_frame; returns true when Atlas handled the frame */
```

How the adapter keeps the legacy semantics: **the adapter never keeps its own cursor.** Atlas focus events set `fm.cursor` through `fm_go(index)` (the legacy cursor setter), and ACCEPT and BACK call `fm_confirm()` and `fm_back()`. So `fm_do_pending`, `fm_mirror_flow`, `fm_position_for`, the native back-out and the `FMF_PORT` port all behave exactly as today. A registry entry is a tile after the menu's own items. It has no `fm.vis[]` slot; its ACCEPT goes to `Ui_EntryActivate(parent, k)`.

- [ ] **Step 1: Investigation: the legacy frame's side effects that must still run.** Read `fm_scene_frame` (`gmfrontend_menus.inc:1418-1485`) and list what runs even when no input arrives: `fm.fading_out`/`fm.fade`, `fm.demo`, `fp.frame++`, `fm.leave_at`/`fm_do_pending`, `fm_first_boot`, the L+R+START return to main (`mn_8022F218`), `fm_mirror_flow`, `fp_evaluate`, `fm_clip_rows`, `fm_texts_update`.
  - **Branch A (expected):** the Atlas branch replaces only the block inside `else if (fm.leave_at == 0 && !fm.fading_out && fm.frames >= fm.ready_at && fm.nvis > 0)`, which reads the pad and mouse. Everything before and after still runs, so fades, pending actions, first boot, `fm_mirror_flow` (which `gd.menu()` reads) and L+R+START keep working. `fp_evaluate` and `fm_texts_update` keep animating the legacy texts under Atlas's opaque ground, which costs a little CPU and is invisible. To stop the legacy texts drawing at all, call `fm_texts_destroy()` once on Atlas open and guard `fm_texts_update` with `if (!fa_on(fm.menu))`. Pin it in step 4.
  - **Branch B:** if a legacy GObj draws above the overlay (it cannot per D1, but check the log in Task 13), hide the frontend's text canvas under Atlas with the existing `fm_texts_destroy`/`fm_close` pair on open, and re-create it on `MELEE_ATLAS=0`.
- [ ] **Step 2: Write the position-protocol test (failing).** `tools/port/test_fe_atlas_positions.py`:

```python
"""Every (MenuKind, selection) the legacy router can produce lands on a visible item of an Atlas menu.
Run from the workspace root:  python tools/port/test_fe_atlas_positions.py [--game <path to melee>]"""
import os, re, sys, unittest

GAME = os.environ.get("GW_MELEE") or os.path.join(os.path.dirname(__file__), "..", "..", "melee")
SRC = os.path.join(GAME, "src", "melee", "gm", "gmfrontend_menus.inc")

def read():
    with open(SRC, encoding="utf-8") as f:
        return f.read()

def menus(text):
    """fm_menus[] rows: kind, items array name, atlas id (the new last field)."""
    body = text[text.index("static const FeMenu fm_menus[]"):]
    body = body[:body.index("};")]
    rows = re.findall(r"\{\s*(MENU_KIND_\w+),.*?\"([A-Z .\-]+)\",\s*(\w+),\s*FM_N\(\w+\)\s*(?:,\s*(\"[a-z.]+\"|NULL))?\s*\}", body, re.S)
    return {k: (arr, (aid or "NULL").strip('"')) for k, _title, arr, aid in rows}

def items(text, arr):
    m = re.search(r"static const FeMenuItem %s\[\] = \{(.*?)\n\};" % re.escape(arr), text, re.S)
    return re.findall(r"\{\s*\"[^\"]*\",\s*\"[^\"]*\",\s*(?:\"\w+\"|NULL),\s*(\w+)", m.group(1)) if m else []

def positions(text):
    body = text[text.index("static void fm_position_for"):]
    body = body[:body.index("int i;")]
    return re.findall(r"\{\s*GM_\w+,\s*(MENU_KIND_\w+),\s*(\w+)\s*\}", body)

class Positions(unittest.TestCase):
    def test_every_position_is_an_atlas_item(self):
        t = read(); ms = menus(t)
        missing = []
        for kind, sel in positions(t):
            if kind == "MENU_KIND_EVENT":
                continue                               # the Event list stays a retail screen (spec 13.2)
            self.assertIn(kind, ms, "%s has no menu" % kind)
            arr, aid = ms[kind]
            self.assertNotEqual(aid, "NULL", "%s is not an Atlas menu" % kind)
            sels = items(t, arr)
            if sel != "0" and sel not in sels:
                missing.append((kind, sel))
        self.assertEqual(missing, [])

    def test_atlas_ids_unique(self):
        ids = [aid for _arr, aid in menus(read()).values() if aid != "NULL"]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_tbd_left(self):
        t = read()
        for word in ("FA_TBD", "SEL_MAIN_TBD", "Script_Tbd"):
            self.assertNotIn(word, t)

if __name__ == "__main__":
    unittest.main()
```

Run it: `cd "$WS" && GW_MELEE="$GW_MELEE" python tools/port/test_fe_atlas_positions.py`. Expected now: `test_every_position_is_an_atlas_item` fails (no atlas ids yet), and `test_no_tbd_left` fails (Task 10 fixes that one; mark it `@unittest.expectedFailure` until Task 10 and remove the decorator there).
- [ ] **Step 3: Implement.**
  1. Add `const char* atlas_id` as the last `FeMenu` field and fill it for every row of `fm_menus[]` (MAIN `"main"`, 1P `"solo"`, REG `"solo.regular"`, STADIUM `"solo.stadium"`, MULTI_VS `"solo.multiman"`, VS `"versus"`, SPECIAL `"versus.special"`, TOY `"more.collection"`, SETTINGS `"settings"`, DATA `"more.data"`, RECORDS `"more.records"`). Positional initialisers keep the existing rows valid; add the field at the end of each row.
  2. `gmfrontend_atlas.inc`, included by `gmfrontend.c` right after `gmfrontend_menus.inc` (find the include line with `grep -n "#include \"gmfrontend_menus.inc\"" src/melee/gm/gmfrontend.c`):

```c
/* gmfrontend_atlas.inc - the Atlas adapter for the menu tree (spec 6.4, 6.7; plan 2026-10-06-atlas-step2).
 * The tree, the cursor, confirm, back and every pending action stay the legacy ones; this file only
 * describes the current FeMenu to the host each frame and turns the host's events into fm_go/fm_confirm/fm_back. */
extern int Ui_Ready(void);
extern int Ui_Begin(const char* id, int primary, int chapter, const char* title);
extern void Ui_Trail(const char* parent);
extern void Ui_Tile(const char* id, const char* label, const char* tag, const char* numeral, int flags);
extern void Ui_More(const char* id, const char* label);
extern void Ui_Explain(const char* kicker, const char* title, const char* what);
extern void Ui_ExplainWith(const char* tag);
extern void Ui_Key(int button, const char* label);
extern int Ui_Commit(int focus_block, int focus_index);
extern void Ui_Intent(int type, int a);
extern int Ui_PollEvent(int* type, int* block, int* index);
extern void Ui_Close(const char* id);
extern int Ui_EntryCount(const char* parent);
extern const char* Ui_EntryField(const char* parent, int k, const char* field);
extern int Ui_EntryActivate(const char* parent, int k);

enum { FA_PRIMARY_TILES = 3 };                     /* AT_PRIMARY_TILES (gw_ui_screen.h) */
enum { FA_EV_MOVE = 1, FA_EV_FOCUS = 2, FA_EV_ACCEPT = 3, FA_EV_BACK = 4, FA_EV_ALT = 5 };   /* AT_EV_* (gw_ui_input.h) */
enum { FA_DIR_LEFT = 0, FA_DIR_RIGHT = 1, FA_DIR_UP = 2, FA_DIR_DOWN = 3 };                  /* AT_DIR_*: confirm with grep */

static const char* fa_parent_of(const FeMenu* m) { return m->atlas_id; }   /* the registry parent is the screen id */

static bool fa_on(const FeMenu* m)
{
    return m != NULL && m->atlas_id != NULL && Ui_Ready() != 0;
}

static void fa_submit(const FeMenu* m)
{
    int i, n = Ui_EntryCount(fa_parent_of(m));
    const FeMenuItem* f = &m->items[fm.vis[fm.cursor]];
    Ui_Begin(m->atlas_id, FA_PRIMARY_TILES, fa_chapter_of(m), m->title);
    fa_trail(m);                                    /* parents from back_kind, at most 3 */
    for (i = 0; i < fm.nvis; i++) {
        const FeMenuItem* it = &m->items[fm.vis[i]];
        Ui_Tile(fa_item_id(m, it), it->label, fa_item_tag(m, it), m->kind == MENU_KIND_MAIN ? fa_numeral(i) : "", 0);
    }
    for (i = 0; i < n; i++) {
        Ui_Tile(Ui_EntryField(fa_parent_of(m), i, "id"), Ui_EntryField(fa_parent_of(m), i, "label"), "MOD", "", 0);
    }
    if (m->kind == MENU_KIND_MAIN) {
        Ui_More("collection", "COLLECTION"); Ui_More("data", "DATA"); Ui_More("credits", "CREDITS");
    }
    if (fa.focus_block == 0 && fa.focus_index < fm.nvis) {
        Ui_Explain(fa_kicker(m), f->label, f->desc);
    } else if (fa.focus_block == 0) {
        int k = fa.focus_index - fm.nvis;
        Ui_Explain("MOD", Ui_EntryField(fa_parent_of(m), k, "label"), Ui_EntryField(fa_parent_of(m), k, "blurb"));
    }
    Ui_Key('A', "Open");
    Ui_Key('B', m->kind == MENU_KIND_MAIN ? "Title" : "Back");
    Ui_Commit(fa.focus_block, fa.focus_index);
}

/* returns true when Atlas handled this frame's input (the legacy input block is skipped) */
static bool fa_frame(u32 in)
{
    int type, block, index;
    if (!fa_on(fm.menu)) {
        return false;
    }
    if (in & MenuInput_Up) Ui_Intent(FA_EV_MOVE, FA_DIR_UP);
    if (in & MenuInput_Down) Ui_Intent(FA_EV_MOVE, FA_DIR_DOWN);
    if (in & MenuInput_Left) Ui_Intent(FA_EV_MOVE, FA_DIR_LEFT);
    if (in & MenuInput_Right) Ui_Intent(FA_EV_MOVE, FA_DIR_RIGHT);
    if (in & MenuInput_Confirm) Ui_Intent(FA_EV_ACCEPT, 0);
    if (in & MenuInput_Back) Ui_Intent(FA_EV_BACK, 0);
    while (Ui_PollEvent(&type, &block, &index)) {
        if (type == FA_EV_FOCUS) {
            fa.focus_block = block; fa.focus_index = index;
            if (block == 0 && index < fm.nvis) fm_go(index);           /* the legacy cursor is the truth */
        } else if (type == FA_EV_ACCEPT) {
            if (block == 0 && index < fm.nvis) { fm_go(index); fm_confirm(); }
            else if (block == 0) { sfxForward(); Ui_EntryActivate(fa_parent_of(fm.menu), index - fm.nvis); }
            else fa_more(index);                                        /* Collection, Data, Credits */
            break;                                                      /* one action per frame, as the legacy path */
        } else if (type == FA_EV_BACK) {
            fm_back();
            break;
        }
    }
    fa_submit(fm.menu);
    return true;
}
```

  Write the helpers named above (`fa_chapter_of`: main 0, solo-side 1, versus-side 2, online 3, mods 4, settings 5, more-side 0; `fa_trail`; `fa_item_id` (a lower-case slug of the label, unique per menu); `fa_item_tag` (`"MOD"` for `SEL_1P_LAB`); `fa_numeral`; `fa_kicker` ("CHAPTER I" ... for the main menu, the parent title otherwise); `fa_more` (Task 9); a `static struct { int focus_block, focus_index; } fa;` reset in `fm_open` to `(0, fm.cursor)`).
  3. In `fm_scene_frame`, the pad block becomes:

```c
    } else if (fm.leave_at == 0 && !fm.fading_out && fm.frames >= fm.ready_at && fm.nvis > 0) {
        in = mn_80229624(4) | fms_menu_bits();
#if defined(TARGET_PC)
        if (mn_8022F218() && fm.menu->kind != MENU_KIND_MAIN) {
            /* L+R+START stays first, exactly as the legacy branch below */
        } else if (fa_frame(in)) {
            goto fm_after_input;
        }
#endif
        ... the legacy block unchanged ...
    }
#if defined(TARGET_PC)
fm_after_input:
#endif
```

  (If a `goto` is unwelcome in that file's style, restructure as `if (!fa_frame(in)) { legacy }`, with the L+R+START check moved above both. Pick one and keep the legacy block byte-identical otherwise.)

  Mouse: under Atlas the legacy `fm_mouse_slot` and `fms.click` handling is skipped; the host's mouse path drives the engine screen. `fms_menu_bits()` still contributes keyboard bits only if it does not duplicate the host's keyboard. Investigate: `grep -n "fms_menu_bits" -A20 src/melee/gm/gmfrontend_mouse.inc`.
  - **If it maps keys to MenuInput:** pass `in & ~fms_menu_bits()` into `fa_frame` (the host already reads arrows, Enter and Escape for the top screen). Otherwise a key press acts twice.
  - **If it is mouse only:** pass `in` unchanged.
  - Add a one-line comment saying which branch was taken.
  4. On `fm_close()` (leaving a menu for another menu), call `Ui_Close(prev atlas_id)`. On `fm_scene_exit`, call nothing: `Ui_SceneExit` from the scene hook closes the engine screens.
  5. Built-in entries: in `fm_scene_enter`, register nothing yet. The LAB stays a menu item (Task 10 decides its tag).
- [ ] **Step 4: Checks.**

```bash
cd "$WS" && GW_MELEE="$GW_MELEE" python tools/port/test_fe_atlas_positions.py      # positions: OK (tbd: expected failure until Task 10)
ppc "$GW_MELEE/src/melee/gm/gmfrontend.c" && echo ppc-frontend-ok
grep -n "fm_go(index)" "$GW_MELEE/src/melee/gm/gmfrontend_atlas.inc"                   # the cursor is the legacy one (cursor_is_the_legacy_cursor)
grep -c "fm.cursor =" "$GW_MELEE/src/melee/gm/gmfrontend_atlas.inc"                     # 0: the adapter never writes the cursor itself
```

- [ ] **Step 5: Commit (game repo, then workspace).** `git commit -m "frontend: the Atlas adapter for the menu tree (the legacy cursor, confirm and back; registry entries as MOD tiles)"`

---

### Task 9: The new main menu, the More row and the Credits screen

**Files:**
- Modify: `gmfrontend_menus.inc`, `gmfrontend_atlas.inc`, `gw_script_ui.inc` (the host-native Credits description)
- Test: `atlas_binding_test.c` (credits), `test_fe_atlas_positions.py` (new rows)

**The structure (spec 13.2, owner's decision in section 2):**

| Main (Atlas) | Action | Legacy equivalent kept for `MELEE_ATLAS=0` |
|---|---|---|
| I SOLO | `FA_SUB MENU_KIND_1P` | same |
| II VERSUS | `FA_SUB MENU_KIND_VS` (VS no longer lists ONLINE) | VS still lists ONLINE |
| III ONLINE | `FA_ONLINE` (the old Online rows until step 6) | under VS |
| IV MODS | `FA_PAGE 4` (the old Settings > Mods page until step 7) | under Settings |
| V SETTINGS | `FA_SUB MENU_KIND_SETTINGS` | same |
| More: COLLECTION | `FA_SUB MENU_KIND_TOY` | main item |
| More: DATA | `FA_SUB MENU_KIND_DATA` | main item |
| More: CREDITS | push the host screen `more.credits` | none |

Two trees exist while `MELEE_ATLAS=0` is supported: `fm_main` (legacy, unchanged except Task 10's TBD removal) and `fm_main_atlas` (five items; More is drawn by the adapter, not an `FeMenuItem`). `fm_find(MENU_KIND_MAIN)` returns the Atlas row when `Ui_Ready()`. The same split applies to `fm_vs` / `fm_vs_atlas` (without ONLINE). New selections for the new main items: `SEL_MAIN_ONLINE 0x44` and `SEL_MAIN_MODS 0x45` (non-vanilla, like `SEL_VS_ONLINE 0x40`; check with `grep -n "0x4[0-9]" gmfrontend_menus.inc` that neither is taken in `MENU_KIND_MAIN`).

- [ ] **Step 1: Investigation: back-outs that name the old places.** `fm_back_to_online_item` returns to `MENU_KIND_VS, SEL_VS_ONLINE` (`gmfrontend_menus.inc:313-321`). `fm_back_kind`/`fm_back_sel` return from a settings page to the Settings list (`:305-312`). The first boot sends to SETTINGS > CONTROLS (`:1169-1182`).
  - **Under Atlas:** leaving Online must land on MAIN > ONLINE (`MENU_KIND_MAIN, SEL_MAIN_ONLINE`). Leaving the Mods page entered from main must land on MAIN > MODS; record the origin in a `fa.page_from_main` flag set by the Atlas main's MODS confirm. The first boot is unchanged (it still opens CONTROLS, a legacy page until step 5).
  - **Under `MELEE_ATLAS=0`:** every back-out is unchanged.
  - Write both as `if (Ui_Ready()) ... else ...` at those two sites.
- [ ] **Step 2: Failing tests.**
  - In `test_fe_atlas_positions.py`, add `test_main_atlas_shape`: `fm_main_atlas` lists exactly `SEL_MAIN_1P, SEL_MAIN_VS, SEL_MAIN_ONLINE, SEL_MAIN_MODS, SEL_MAIN_SETTINGS` in that order, and `fm_vs_atlas` has no `SEL_VS_ONLINE`.
  - Add `test_online_back_lands_on_main`: the source contains `SEL_MAIN_ONLINE` inside `fm_position_for`.
  - In `atlas_binding_test.c`, add `credits_screen`. `gw_Ui_OpenCredits()` pushes `more.credits`, an engine list. Every item has a non-empty `sub`. The list renders at 640 with `texts_legible()` and with every text inside the primary rectangle. B pops it. While it is on top, `gw_Ui_TopIsEngine("main") == 0`, and after B it is 1 again with no BACK event left in the main menu's queue.
- [ ] **Step 3: Implement.**
  - `fm_main_atlas`, `fm_vs_atlas` and `SEL_MAIN_ONLINE` / `SEL_MAIN_MODS` in the confirm switch: they reuse `FA_ONLINE` and `FA_PAGE` with `arg` 4. Add the `fm_position_for` rows: `{ GM_VS from online, MENU_KIND_MAIN, SEL_MAIN_ONLINE }` through the existing `fm_back_to_online_item` path.
  - `fa_more(index)`: 0 opens COLLECTION and 1 opens DATA, both via the existing `FA_SUB` path (`fm.pend_kind = 1; fm.pend_a = MENU_KIND_TOY or MENU_KIND_DATA; fm.leave_at = fp.frame + 1;`); 2 calls `Ui_OpenCredits()`.
  - Credits (host, `gw_script_ui.inc`): a static table from `CREDITS.md`'s sections. Read the file and copy each outside project's name and its link or licence line into `{ id, label, sub }`. Use the Atlas fonts, m-ex (akaneia), Slippi, Lua, Aurora, decomp (doldecomp/melee) and every other project `CREDITS.md` names. Nothing is invented here; if `CREDITS.md` lacks a link, the `sub` says "see CREDITS.md". It is an engine list (`AT_PRIMARY_LIST`, explainer `normal` with the item's `sub` as `what`); B pops it. Rows past 32 items are cut at the limit with a final row "and more: CREDITS.md". Check the count: `grep -c "^- \|^| " "$MAIN/CREDITS.md"`.
- [ ] **Step 4: Run** both tests, `ppc` the frontend, and `nt atlas-binding`.
- [ ] **Step 5: Commit (game repo, then workspace).** `git commit -m "frontend: the Atlas main menu (Solo, Versus, Online, Mods, Settings; More: Collection, Data, Credits) and the Credits screen"`

---

### Task 10: Retire the `FA_TBD` tile (a versioned API removal) and settle the LAB entry

**Files:**
- Modify: `gmfrontend_menus.inc`, `gw_script.c`, `gw_script.h`, `pc/scripts/examples/roguelite/main.lua`, workspace `docs/scripting.md`, `tools/port/test_fe_atlas_positions.py` (drop the expected-failure mark)

**The removal, by the Versioning rule (`docs/scripting.md` "Versioning and deprecations"):** removing a function bumps the API, and the old name stays for one version, listed in `gd.deprecated`. So:
- `GW_SCRIPT_API_VERSION` becomes **2**.
- `gd.tbd_request` stays for API 2 as a stub that always returns `false`, and `gd.deprecated.tbd_request = "use mod.json menus and on_entry (docs/scripting.md, Atlas entries)"`. It is removed in API 3.
- `gw_Script_TbdAvailable`, `gw_Script_TbdRequest`, `gs.tbd_request`, `FA_TBD`, `SEL_MAIN_TBD`, the `fm_main[0]` row, the `fm_visible` branch, the `fm_confirm` case and `fm_do_pending` case 7 are deleted. They apply under both `MELEE_ATLAS` values: the legacy main menu loses the SUPERTIME ENVOY tile too, because Envoy now appears under Solo through the registry in both arrangements. Task 11 makes the legacy SOLO hub show registry entries as well; if that proves too costly, see Task 11 step 1, branch B.

- [ ] **Step 1: Investigation: who else calls the TBD path.**

```bash
cd "$GW_MELEE" && grep -rn "tbd_request\|TbdAvailable\|TbdRequest\|SEL_MAIN_TBD\|FA_TBD" --include=*.c --include=*.inc --include=*.h --include=*.lua --include=*.cpp . | grep -v "^./_build"
cd "$MAIN" && grep -rn "tbd_request\|SUPERTIME ENVOY" docs tools menu --include=*.md --include=*.py --include=*.json | head
```

Expected: only the places listed above, `roguelite/main.lua:1250`, and docs.
  - **If `menu/` or `tools/` also reference the tile** (for example the hub layout JSON naming a fifth main slot): remove the tile from that data too, and say so in the commit.
  - **If a mod outside the repo is known to call it:** keep the stub (it is kept anyway) and mention the mod in the release notes for the next version.
- [ ] **Step 2: Investigation: roguelite.** `pc/scripts/examples/roguelite` has no `mod.json`; its id is `roguelite/main`, and line 1250 launches its run when the tile asked. Look for a console command that launches it: `grep -n "add_command\|gd.command\|function.*on_command" pc/scripts/examples/roguelite/main.lua pc/scripts/examples/roguelite/commands.lua | head`.
  - **If a launch command exists:** delete line 1250 and add one comment line saying the main-menu tile was removed in API 2 and naming the command.
  - **If none exists:** replace line 1250 with a guard `if gd.api_version < 2 and gd.tbd_request(true) then launch();return end`, so it still works on an older build, and add a launch command next to the existing ones that calls `launch()`. The roguelite example is superseded by Envoy (the spec's 13.2 "migrate or remove it"); this keeps it working without a tile.
- [ ] **Step 3: Tests first.** In `gw_script.c`'s in-exe self-test block (the one around `gd.lab_request read/clear`, about :10266), add a check that `= gd.api_version, gd.tbd_request(true), gd.deprecated.tbd_request ~= nil` returns `2, false, true`. Remove the expected-failure decorator from `test_no_tbd_left` in `test_fe_atlas_positions.py`. Both fail now.
- [ ] **Step 4: Implement** the removal as listed. Settle the LAB: it stays a menu item of SOLO (`FA_MODE GM_LAB` with `Script_LabRequest()` and `Script_LabAvailable()` visibility, unchanged). Under Atlas its tile carries the tag `"MOD"` (`fa_item_tag`), the "built-in entry owned by its mod" of 13.2. `gd.lab_request` stays (it is not menu-only: `MELEE_LAB=1` and `geno_lab_mode.c:129, 230` use it). The spec's "moved to the entry's `on_entry`" is **not** done. The reason: a Lua `on_entry` cannot enter `GM_LAB` without a new gameplay API, and the native action already does exactly that. This is listed as a deviation.
- [ ] **Step 5: Run.** `python tools/port/test_fe_atlas_positions.py` (all OK), `ppc` the frontend, then a full `tools/port/build.sh` and its in-exe test run (find the command with `grep -n "\-\-test" "$WS/tools/port/README.md" | head -3`; it is the headless one, no window). Then `grep -a "use mod.json menus and on_entry" "$GW_BUILD_ROOT/melee-pc.exe" | head -1`.
- [ ] **Step 6: Docs.** In `docs/scripting.md` "Versioning and deprecations", replace "Deprecated in API 1: nothing." with "**Deprecated in API 2:** `gd.tbd_request` (always `false`; use `mod.json` `menus` with `action = "script"` and `on_entry`). Removed in API 3." Remove `gd.tbd_request` from the API table, or mark it deprecated there with the same sentence.
- [ ] **Step 7: Commit** (game repo: code and roguelite; workspace: docs and the test). `git commit -m "script API 2: the main-menu TBD tile is gone (gd.tbd_request deprecated, always false); entries replace it"`

---

### Task 11: Envoy's entry: `SOLO > ENVOY`

**Files:**
- Modify: `pc/scripts/examples/envoy/mod.json`; the Envoy file that defines script hooks (find it in step 1); `pc/scripts/examples/envoy/scripts/main.lua` (regenerated); `pc/tests/atlas_registry_test.c` (`ENVOY_MENUS_EXPECTED 1`); `gmfrontend_menus.inc` (legacy SOLO lists registry entries)
- Create: `pc/tests/envoy_atlas_entry.lua`

- [ ] **Step 1: Investigation: can Envoy's menu open over the frontend scene?** Envoy's setup and menu are today opened by the console (`envoy menu`, `app.lua:143-148`). `A:command('menu')` asserts only that the match is not netplay (`self.g.match()` may be nil on `GS_FRONTEND`). It sets `self.visible = true` and `self.menu:show('title')`, and its drawing uses `gd.kit`, which runs on menu scenes (D2). What is not known: whether the Envoy menu's own input (`menu_input.lua`) reads the pad on `GS_FRONTEND` while the frontend also reads it (double input), and whether a run start from that menu (`run:start()`, which launches an offline LAB scene, `MENUS.md:140`) works from `GS_FRONTEND`.
  - **Branch A (prefer):** `on_entry('envoy')` pushes a small Atlas screen `envoy.entry`, a list with START CLASSIC, START ADVENTURE, ENVOY MENU and BACK. Its handlers call the existing commands (`app:command('start')` with the mode set, or `app:command('menu')` for the full legacy menu). Pushing an Atlas screen covers the native menu. Atlas input belongs to the top screen, and the frontend adapter takes no input while covered (Task 5 `engine_screen_covered_takes_no_intent`), so there is no double input for this screen. **ENVOY MENU (legacy)** pops the Atlas screen first and then calls `app:command('menu')`. While the legacy Envoy menu is visible the frontend must not take input either. Add `gd.ui.hold_menu(true/false)`, a host flag `gs_ui_menu_held` that makes `gw_Ui_TopIsEngine` return 0 and drops intents; Envoy sets it while `self.visible` is true on `GS_FRONTEND`. Test it in `atlas_binding_test.c` as `held_menu_takes_no_intent`, driven as the mod.
  - **Branch B (if Branch A's run start does not work from `GS_FRONTEND`, found in Task 13):** `on_entry` launches the same offline scene the console path launches. Envoy's own setup then appears in that scene, as `envoy menu` does today from a match. This needs no new code beyond calling the existing start path. Record the branch taken in the Envoy README's first lines.
  - This plan implements Branch A. Branch B is the fallback the in-game task decides.
- [ ] **Step 2: Find where Envoy defines hooks.** `cd "$GW_MELEE" && grep -n "^function on_\|_G.on_\|on_tick *=\|function on_scene" pc/scripts/examples/envoy/scripts/*.lua | grep -v main.lua | head`. Put `on_entry` in that same file (the bundle regenerates `main.lua` from the modules: `tools/port/envoy_bundle.py`).
- [ ] **Step 3: Write the failing offline test** `pc/tests/envoy_atlas_entry.lua` (run from `$GW_MELEE`, the Envoy suite's root):

```lua
-- envoy_atlas_entry.lua: Envoy's main-menu entry, offline (lua pc/tests/envoy_atlas_entry.lua from the game repo root)
local Stub = dofile("pc/tests/atlas_ui_stub.lua")
local pass, fail = 0, 0
local function check(c, what) if c then pass = pass + 1 else fail = fail + 1; print("FAIL " .. what) end end

local f = assert(io.open("pc/scripts/examples/envoy/mod.json", "rb")); local manifest = f:read("a"); f:close()
check(manifest:find('"menus"', 1, true) ~= nil, "mod.json has menus")
check(manifest:find('"parent": "solo"', 1, true) ~= nil, "under solo")
check(manifest:find('"action": "script"', 1, true) ~= nil, "a script action")
check(manifest:find('"online": false', 1, true) ~= nil, "offline only")

local ui = Stub.new{ caller = "envoy", owner_mod = "envoy", available = true }
local env = dofile("pc/tests/envoy_test_env.lua")          -- the suite's existing loader; use the one envoy_run_ux.lua uses
local app = env.app{ gd_ui = ui }
check(type(env.hooks.on_entry) == "function", "on_entry defined")
local r = env.hooks.on_entry("envoy")
check(type(r) == "table" and r.push == "envoy.entry", "on_entry pushes envoy.entry")
check(ui:registered("envoy.entry"), "envoy.entry registered")
local s = ui:screen_of("envoy.entry")
check(s.primary.kind == "list" and #s.primary.items == 4, "four rows")
check(s.on and type(s.on.back) == "function", "B closes (on.back given)")
for _, it in ipairs(s.primary.items) do check(#it.label <= 18, "label fits: " .. it.label) end
check(env.hooks.on_entry("other") == nil, "another id is not Envoy's")
env.set_netplay(true)
check(env.hooks.on_entry("envoy") == nil, "nothing in netplay")
print(("PASS %d tests"):format(pass)); if fail > 0 then os.exit(1) end
```

  Read `pc/tests/envoy_run_ux.lua`'s first 60 lines for the real loader and stub names. Replace `envoy_test_env.lua`, `env.app`, `env.hooks` and `env.set_netplay` with what that file uses; do not create a second loader if one exists.
- [ ] **Step 4: Run, fail.** `cd "$GW_MELEE" && lua pc/tests/envoy_atlas_entry.lua`.
- [ ] **Step 5: Implement.**
  - Add `mod.json` `"menus": [ { "id": "envoy", "parent": "solo", "label": "ENVOY", "blurb": "Explore, fight and evolve your build.", "after": "training", "action": "script", "online": false } ]`.
  - Add `on_entry(id)`: it returns nil unless `id == "envoy"` and the session is not netplay. It registers `envoy.entry` (four rows; `trail = { "SOLO", title = "ENVOY" }`; explainer `normal` with one short rule per row) and returns `{ push = "envoy.entry" }`.
  - Add `gd.ui.hold_menu` to the binding, the stub and the docs.
  - Run `python tools/port/envoy_bundle.py` (from `$WS`, with `GW_MELEE` set as its README says) to regenerate `main.lua`.
  - Legacy SOLO (`MELEE_ATLAS=0`): `fm_open` appends the registry's `solo` children as extra `FA_ENTRY` items after the native ones (a small static `FeMenuItem` buffer filled from `Ui_EntryField`; `act = FA_ENTRY`, `arg = k`). `fm_confirm` sends them to `Ui_EntryActivate`. If the legacy hub's slot layout (`hub_layout.json`) cannot take an eighth tile, **Branch B**: the legacy SOLO hub shows no mod entries, and under `MELEE_ATLAS=0` Envoy is reached by `envoy menu` only. Say so in the README and the release notes.
  - Flip `ENVOY_MENUS_EXPECTED` to 1 in `atlas_registry_test.c`.
- [ ] **Step 6: Run** the Envoy suite **from the game repo root**, plus the native and stub tests:

```bash
cd "$GW_MELEE" && for f in pc/tests/envoy_*.lua; do lua "$f" | tail -1; done
nt atlas-registry | tail -1; nt atlas-binding | tail -1
cd "$GW_MELEE" && lua pc/tests/atlas_ui_stub_test.lua | tail -1
```

- [ ] **Step 7: Commit** (game repo: Envoy, tests, the bundle output, the frontend; workspace: none). `git commit -m "envoy: the SOLO > ENVOY entry (mod.json menus, on_entry, envoy.entry); legacy SOLO lists registry entries"`

---

### Task 12: The title as an Atlas overlay

**Files:**
- Modify: `gmfrontend_atlas.inc` (the title submit), `gw_script_ui.inc` (scene-begin push of policy screens), `gw_script.c` (the call from `Script_SceneBegin`)

**How it works.** At scene begin, if `Ui_ScenePolicy(kind) == OVERLAY` and `at_policy_screen(kind)` is `"title"`, the host itself builds the engine display screen (Task 2) and pushes it with `scene = kind`. No game-side per-frame code is needed: the screen has no input and the retail `on_frame` keeps START, the 600-frame attract timer and the port's Y/B debug path. At scene exit `Ui_SceneExit` pops it. `MELEE_ATLAS=0` or `MELEE_ATLAS_SCENES=<title kind>:retail` gives the retail title.

- [ ] **Step 1: Investigation: is the title entered before the Lua state and the font roles are ready?** The first scene after boot may be the title or the opening movie. `gs_ui_roles_ok()` loads the font pages on first use.
  - **If roles are not ready at the title's first frame** (check `gw_Ui_Ready()` on each tick until true, not only at scene begin): push on the first tick where it is true, provided the scene is still the title. The retail title shows for those frames, which is acceptable.
  - **If the roles are missing entirely** (`ui/` without the Atlas pages): the title stays retail and one log line says why. This is the same rule as `gd.ui.available()`.
  - Test both in `atlas_binding_test.c` as `title_waits_for_roles` and `title_without_roles_stays_retail`.
- [ ] **Step 2: Failing tests** in `atlas_binding_test.c`:
  - `title_pushed_on_scene_begin` (policy OVERLAY: the stack top is `title`, engine-owned, `AT_PRIMARY_DISPLAY`).
  - `title_takes_no_input`: feed `gw_Ui_Intent(AT_EV_ACCEPT)` and move the fake mouse with a click; no event is queued and the stack is unchanged.
  - `title_popped_on_scene_exit`.
  - `title_retail_when_off` (`MELEE_ATLAS=0` in the stand-in environment: nothing pushed).
  - `title_version_text`: the foot-left text is the release version string. Find it with `grep -rn "GW_VERSION\|gw_Version" "$GW_MELEE/pc/platform/*.h" | head -3`; if no version symbol exists in the host, leave `foot_left` empty and say so.
- [ ] **Step 3: Implement**, then run `nt atlas-binding`.
- [ ] **Step 4: Commit (game repo).** `git commit -m "atlas: the title as an overlay display screen (retail title logic unchanged; MELEE_ATLAS=0 keeps the retail face)"`

---

### Task 13: The Mods page says what a mod adds; docs and terms

**Files:**
- Modify: `gmfrontend_settings.inc` (the Mods page row), workspace `docs/scripting.md`, `docs/TERMINOLOGY.md`, game repo `src/melee/gm/CLAUDE.md`

- [ ] **Step 1: The Mods page row.** Find the row builder: `grep -n "Mods_Name\|Mods_Description" "$GW_MELEE/src/melee/gm/gmfrontend_settings.inc"`. Where a row shows a mod's description, show `Mods_MenuSummary(i)` when it is not empty ("adds Solo > Envoy"), followed by the description. Run the PowerPC check: `ppc "$GW_MELEE/src/melee/gm/gmfrontend.c"`.
- [ ] **Step 2: `docs/scripting.md`.**
  - The manifest table gains a `menus` row (the shape from Task 4, the caps 6 per mod per parent and 12 visible per parent, labels at most 18 characters, parents `main solo versus online mods settings more settings.<page>`, unknown parents ignored with one log line, a disabled mod adds nothing).
  - The `gd.ui` table gains `gd.ui.entry(id, {visible=, badge=})` and `gd.ui.hold_menu(on)`.
  - The Hooks section gains `on_entry(id)`.
  - The `gd.ui` intro says engine screens exist (the native menus), that a script may not register, open, close or feed an engine id, and that a screen opened by an entry is closed when the scene that opened it ends.
  - Update "Not in step 1" accordingly.
- [ ] **Step 3: `docs/TERMINOLOGY.md`.** Add **engine screen** (an Atlas screen owned by native code: the menus, the title, Credits) and **scene policy** (RETAIL, OVERLAY, REPLACE per scene kind, spec 6.8). Check the file's own rule first: `head -30 "$WS/docs/TERMINOLOGY.md"`.
- [ ] **Step 4: `melee/src/melee/gm/CLAUDE.md`.** Add one paragraph: `FeMenu.atlas_id`, `gmfrontend_atlas.inc`, the rule that the adapter never owns the cursor, `MELEE_ATLAS=0`, `MELEE_ATLAS_SCENES`.
- [ ] **Step 5: Commit** (game repo: settings row and CLAUDE.md; workspace: docs).

---

### Task 14: The in-game look (a checklist for a Windows agent while the owner is away, or for the owner)

**Nothing before this task proves the front door in the game.** Tasks 1 to 13 prove layout, focus, ownership, the registry, the policy table, the position protocol by table, and the PowerPC syntax of game-side edits. They do not prove how it looks, that the overlay sits over the frontend and the title as D1 says, that input acts once, or the frame cost.

**Who and when.** Only when the owner is away, or by him. Second monitor (ask the coordinator for its position), `MELEE_VOLUME=0`, never hidden. Stop only your own PID. No screenshots as proof. The ACE disc is the default for play tests (memory "Test with ACE"); the vanilla disc is needed for `fe_menu_sweep.py --disc vanilla`.

- [ ] **Step 1: Build and confirm the exe is new.**

```bash
tools/port/build.sh
grep -a "belongs to the engine" "$GW_BUILD_ROOT/melee-pc.exe" | head -1
grep -a "frontend: the Atlas\|ui: registry:" "$GW_BUILD_ROOT/melee-pc.exe" | head -2
```

- [ ] **Step 2: Boot to the title** (`tools/port/run.sh atlas2-look --iso "$GW_ISO_ACE"` with the window variables; no `MELEE_SCENE`, so it boots normally). Write yes or no for each:
  1. The title is the Atlas face (wordmark, PC PORT, PRESS START), not the retail logo.
  2. START goes to the Atlas main menu.
  3. Waiting 10 seconds plays the retail attract movie as before.
  4. Y or B still opens the debug menu.
- [ ] **Step 3: The walk.** Title > Main > Solo > Envoy > (the `envoy.entry` screen) > B > B > B back to the title. Then:
  1. Each hub (Main, Solo, Regular Match, Stadium, Multi-Man, Versus, Special Melee, Collection, Settings, Data, Records, Credits) at 4:3 (`MELEE_WINDOW_W=960 MELEE_WINDOW_H=720`) and 16:9 (`1920 x 1080`). Every focused tile shows all three cues. No text runs out of a tile. Chamfers are clean.
  2. Each press acts once: A on SOLO opens SOLO once; one D-pad press moves one tile; keyboard arrows and Enter act once.
  3. The mouse: hover focuses, a click opens, a right click backs, and a still pointer does not steal focus.
  4. A retail screen and back: VERSUS > RULES, then B lands on RULES. SOLO > EVENT MATCH, then back lands on EVENT MATCH. A Training match, then quit lands on TRAINING.
  5. L+R+START from a submenu returns to the main menu.
  6. ONLINE from the main menu opens the old Online rows; B lands on MAIN > ONLINE. MODS opens the old Mods page; B lands on MAIN > MODS, and the Envoy row says "adds Solo > Envoy".
  7. **Envoy.** SOLO shows ENVOY with a MOD tag after TRAINING. A opens `envoy.entry`. START CLASSIC starts a run. If it does not, write down the log lines and take Task 11's Branch B. ENVOY MENU opens the legacy Envoy menu, and the frontend does not react to the pad while it is open.
  8. **First boot.** With a fresh `userdata` sandbox, the first boot goes to SETTINGS > CONTROLS as before.
  9. `MELEE_ATLAS=0`: the legacy menus and the retail title exactly as before, minus the SUPERTIME ENVOY tile, with ENVOY under SOLO (or not, if Task 11 took Branch B).
  10. Frame cost on the main menu: `= gd.ui.state().cost_ms`, `.cost_max_ms`, `.quads` from the console. The target is at most 0.5 ms and under 3,000 quads.
- [ ] **Step 4: The sweep** (vanilla disc, unattended, owner away): `python tools/port/fe_menu_sweep.py --disc vanilla --exe-dir "$GW_BUILD_ROOT"`. Read the failing runs' logs before calling anything an artifact (root `CLAUDE.md` fact 3). The sweep's navigation model assumes "every menu opens on its first visible item" and Down steps through items. Under Atlas, a two-column hub moves Down by a row, not by an item. **Investigate before running:**
  - **If the sweep sends only Down presses:** run it with `MELEE_ATLAS=0` (it then tests the legacy tree, including the new back-outs), and file a follow-up to teach it Atlas's two-column moves.
  - **If it can be told the column count:** run it under Atlas too.
- [ ] **Step 5: Report** a yes or no for every item with one line per no, the numbers from 3.10, the sweep's summary, and the branches taken in Tasks 8, 11 and 12. The owner decides whether the look is accepted.
- [ ] **Step 6: After the owner's look (a follow-up, not this plan).**
  - Retire the `FM_HUB`/`FM_LIST` drawing and the art sets `out_hub`, `out_hub_bouba`, the hub and list parts of `out_nav`, `hub_layout.json` and `list_layout.json`.
  - Drop `fm_main` and `fm_vs` in favour of the Atlas trees.
  - Remove `MELEE_ATLAS=0` for these screens.
  - Do not do this in the same session as the look.

---

## Self-review

**Spec coverage (13.2).**

| 13.2 item | Where |
|---|---|
| Title (`gmtitle.c`, Press Start) | Tasks 2, 7, 12; OVERLAY by decision D3 |
| MAIN MENU, SOLO, REGULAR MATCH, STADIUM, MULTI-MAN, VERSUS, SPECIAL MELEE, COLLECTION, SETTINGS (list), DATA, RECORDS | Tasks 1, 8 (all tree menus get an `atlas_id`), 9 |
| First-boot onboarding | Task 9 step 1 (unchanged route), Task 14 step 3.8 |
| A new Credits screen | Task 9 |
| Main is Solo, Versus, Online, Mods, Settings plus More; Online and Mods top level; VERSUS keeps Melee, Tournament, Special Melee, Rules, Name Entry | Task 9 |
| The registry (U6) and manifest `menus` | Tasks 3, 4, 6 |
| U8 adapter for `FM_ATLAS` | Task 8 (as `FeMenu.atlas_id`, the spec's `FM_ATLAS` style in effect) |
| Scene policy with OVERLAY and REPLACE | Task 7 (table, hook, REPLACE extension point), Task 12 (OVERLAY's first user) |
| Envoy's entry replacing the tile | Tasks 10, 11 |
| The LAB as a built-in entry owned by its mod | Task 10 step 4 (a MOD-tagged native item; see deviation 3) |
| Retired: `FA_TBD`, `SEL_MAIN_TBD`, `Script_Tbd*`, `gd.tbd_request` (versioned), roguelite's use | Task 10 |
| Retired: hub and list drawing and art | **After the owner's look** (Task 14 step 6), as step 1 did with the legacy bag |
| Verified without the game: hubs as descriptions at three widths; position-protocol table test; registry tests; `fe_menu_sweep.py` | Tasks 1, 2 (three widths), 8 (positions), 3, 4, 6 (registry); the sweep needs the disc (fact above) and runs in Task 14 |
| Must be seen | Task 14 |

**Deviations and gaps the coordinator should know about.**
1. **REPLACE has no user in step 2.** The title is an OVERLAY because it keeps retail's exit logic, the attract loop and the debug path for free (D3). REPLACE is built, unit-tested and hooked, and gets its first user in step 8.
2. **`FM_ATLAS` is expressed as `FeMenu.atlas_id`** (non-NULL means Atlas draws it when `Ui_Ready()`), not as a third `style` value. It needs no change to the `FM_HUB`/`FM_LIST` drawing, and it carries the screen id the registry needs.
3. **The LAB's menu path does not move to `on_entry`.** A Lua handler cannot enter `GM_LAB` without a new gameplay API; the native item already does it. It is MOD-tagged in Atlas.
4. **Icons.** Step 1 built no Atlas icon set (its gap 2). Hub tiles show labels, numerals and tags, no icons. The mockups show line icons; the icon set (spec engine item 6) is not in this plan. Its fallback ("reuse legacy masks tinted") was not taken, because it would keep `out_hub` alive.
5. **Envoy's entry opens a small Atlas screen in front of the legacy Envoy menu** (Branch A). Envoy's own screens become Atlas in step 3.
6. **The legacy SOLO hub may not show mod entries** (Task 11 Branch B) if its fixed slot layout cannot take them. In that case the Envoy entry under `MELEE_ATLAS=0` is the console only.
7. **One frame of latency is avoided** by running native intents immediately (`gw_Ui_Intent`); mouse and keyboard still go through the script tick, so a click acts on the next logic frame. This is unmeasured.
8. **`gd.ui.hold_menu`** is new API surface that this plan introduces for the legacy Envoy menu over the frontend. It is temporary: step 3 retires it when Envoy's menus are Atlas.

**Unverified after this plan (needs the game):** how the overlay looks over the title and the frontend (D1), including any GX-replay frame lag; whether Envoy's run start works from `GS_FRONTEND` (Task 11); double input through `fms_menu_bits` (Task 8 step 3); the frame cost; `fe_menu_sweep.py` against Atlas's two-column moves.

**Placeholder scan.** Where a value depends on the current tree (the `GS_TITLE` number, the AT_DIR values, the Envoy test loader, the clang path, the version symbol), the step names the `grep` that finds it and what to do in each case; no step asks the engineer to invent a value. Line numbers are given with a `grep` to re-find them, because they drift.

**Type and name consistency.** `AT_PRIMARY_TILES`/`AT_PRIMARY_DISPLAY`, `AtItem.icon/tag/badge/numeral`, `AtScreen.tile_cols/more/n_more/hero/prompt/foot_*`, `AtExplainer.with_text` (Tasks 1-2) are used by Tasks 5, 8, 9, 12. `AtEntry`, `AtRegistry`, `AT_ENTRY_*` (Task 3) are used by Tasks 4 and 6. `GS_UI_ENGINE`, `gw_Ui_*` (Task 5) are declared game-side as `Ui_*` in Task 8's listing; the names match one to one. The policy enum values (Task 7) are the numbers the game-side hook compares (`2` for REPLACE, commented).

**Review Focus pinned.** 1: Task 5 (four tests), Task 6 `entry_screen_closed_on_scene_exit`. 2: Task 8 positions test and the `fm_go` grep. 3: Task 5 `native_intents_are_primed`, `engine_screen_covered_takes_no_intent`, `intents_from_any_port`; Task 8 step 3 keyboard branch. 4: Tasks 3, 4, 6. 5: Tasks 1 and 2.

**Execution recommendation.** Give Tasks 1-4 and 7 each to a fresh subagent, with a review between them: they are pure C, each with a test the reviewer can run. Do Tasks 5, 6, 8, 9 and 12 in one session by one agent, because they share the binding's internals and the adapter's mental model. Tasks 10, 11 and 13 can each be one agent after Task 9. Task 14 is for a Windows agent while the owner is away, or for him.
