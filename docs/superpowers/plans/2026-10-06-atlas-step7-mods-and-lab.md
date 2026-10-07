# Atlas step 7: the mods list and the LAB: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) Replace `Settings > Mods` with an Atlas **MODS** screen: every installed mod, on or off for the next boot, what each one adds to the menus, its requirements, its conflicts and how to resolve them, the "applies at restart" note, and a door into a mod's own settings screen. (2) Redraw the **LAB's pause menu** (tabs PLAY, DISPLAY, DUMMY, STATES, TOOLS, DRILLS, EXIT) in Atlas, with the info panel, the move timeline and the mode strip as HUD descriptions, the states library as a paged list with a confirm dialog, and a `lab.pause` parent other mods can add entries under. The LAB stays offline only, every roadmap stage stays, and the dev overlays (hitbox draws, frame step, console, fly readout) keep their primitive drawing.

**Architecture:** The mods screen is host-native C: a pure model (`gw_ui_mods.c`) turns an `AtModsSrc` (a table of accessors over `gw_Mods_*` and the registry) into an `AtScreen` plus view, windows the list (256 mods against a 32-row record), and applies events; a thin door attaches it to the native Atlas door. The LAB is Lua: one mapper inside `lab.lua` (in its own function scope, no new main-chunk local) turns the existing `TABS` rows into a `gd.ui.screen` description; the legacy drawing stays as the fallback behind `lab ui off` until the owner has looked. A few engine additions the LAB needs (a stepper value, a world backdrop, WITH tags, tabs from Lua, `gd.ui.token`, `gd.ui.entries`) are built here only where the gate says earlier steps did not.

**Tech Stack:** C11 host code (standalone native tests through `tools/port/build.sh --native-test`), Lua 5.4 (the mapper, the stub tests, `lua` and `luac` on PATH), the step 1 harness (`atlas_check.h`, `atlas_fake.h`, `atlas_rec.h`) and the step 6 lint helpers (`atlas_lint.h`).

**Spec:** docs/superpowers/specs/2026-10-06-menu-reunification-design.md (13.7, with 7, 8, 9, 10). Form and harness: docs/superpowers/plans/2026-10-06-atlas-step1-components-and-envoy-bag.md. The LAB: `melee/pc/geno/mods/geno-lab/CLAUDE.md` and `melee/docs/geno.md` section 14.

**Status of the plan:** written 2026-10-06 against the step 1 code as merged (headers and `gw_script_ui.inc` read), `lab.lua` as it stands (5,290 lines), `gw_mods.h` and `gmfrontend_settings.inc`. Steps 2 to 5 are planned in parallel and **not built**: every dependency is in "Needs from earlier steps" and gated by Task 0. **What was checked when this was written (2026-10-06, offline, nothing built, no window):** the C of Tasks 1, 2, 3, 5 and 6 was extracted and syntax-checked (`clang -fsyntax-only`) against the step 1 headers (the engine edits of Task 5 applied to scratch copies of the real files, whose anchors matched); the Lua of Tasks 5g, 7, 8 and 9 was **run**: the mapper, the hooks, the stub changes and the new checks were applied to a scratch copy of `lab.lua` and `lab_stage_d_check.lua`, every old check still passes, every new one passes except the description-length lint (18 rows over 110 characters: the work list of Task 7 step 7), and `lab_locals.sh` reports 179 locals before and after. **Not checked:** the C native tests were not linked or run, the engine's binding code (5a, 5d to 5f) was not compiled with the Lua binding, and nothing was seen in the game.

## What the code says that the spec does not

1. **The spec's "the LAB's 6 modes" is stale.** `lab.lua` has ten display modes (clean, hitboxes, frames, stage, inspect, moves, launch, ab, training, combo). The DISPLAY tab shows one mode at a time (a "Display mode" row plus that mode's toggles), so the mapping is by row, not by mode count.
2. **Step 7 needs step 3, not only 1, 2 and 5.** The pause screen draws over the frozen world (step 1's renderer always paints an opaque ground), the info panel and the timeline need HUD parts, and the LAB's notices happen with no screen open while `gd.ui.note` needs one. All three are step 3's (`gd.ui.hud`, the pause description). Order: 1, 2, 3, 5, then 7.
3. **A choice row cannot carry the LAB's rows.** Step 1's choice reports a direction on left, right **and A**. Many LAB rows are "A does it, left and right change it" (Focus, Damage, Fly speed, History, Hot reload, Display mode). This plan adds a `stepper` value (left and right change, A accepts) unless step 5 already did.
4. **The record holds 32 rows, the mods folder holds 256, the states library any number.** `AT_MAX_ITEMS` is 32. The mods screen windows its list; the STATES tab pages its library.
5. **`gd.ui.note` needs an open screen.** The LAB's `say()` notices appear on the HUD with the menu closed, so they go through step 3's HUD note.
6. **The mods API has no conflicts accessor.** `gw_mods.h` exposes `Mods_Requires` but not the conflicts list the resolver already holds (`m->con[]`). Task 3 adds `gw_Mods_Conflicts`.
7. **Atlas has no icon set yet** (step 1 gap 2: the 36 line icons are not built). The `ico_lab_*` art stays in the mod for the dev overlays; the pause rows lose their icons in Atlas until the set exists. The retirement list shrinks accordingly (Task 12).

## Global Constraints

Exact values come from the spec; if a task seems to need a different one, stop and ask the coordinator.

- **Canvas, text, shape, focus, motion, budgets:** exactly as step 1's Global Constraints and step 6's: 640x480 logical, compact below 760 and wide from 760, 12 px text floor, the fit rule (step down one role, then ellipsis, never squash, nothing under 8 px of room), flat quads, chamfers top-left and bottom-right only (8 px panes, 5 px rows, buttons, notes and tags, 3 px cells), three focus cues at once, motion on the UI clock with Reduced Motion cutting every tween, 4,096 entries a screen (warn at 3,000), 512 triangles a model, 50 ms or 2,000,000 instructions a script call, 0.5 ms a frame target.
- **Mods (spec 8):** a mod adds entries, never replaces or hides a built-in one; at most 6 entries per mod per parent, 12 visible per parent in total, labels at most 18 characters at `cap20`; entries under `online` and `versus` are hidden while a session exists unless the entry says `"online": true`. The MODS screen **never runs a mod's code**; it reads `gw_Mods_*` and the registry and writes `mods/enabled.txt` for the next boot.
- **Online:** the MODS screen is presentation plus one local file write for the next boot; it is allowed in a session (the netplay handshake compares mounted sets, which cannot change until restart). The LAB is **offline only**: no Atlas LAB screen is opened when `gd.match().netplay` is true, `gd.ui` never masks the pad, no handler runs on a resimulated frame (`gs_may_run`), mouse and keyboard never reach the pads.
- **LAB rules (`geno-lab/CLAUDE.md`):** `lab.lua`'s main chunk is at Lua's 200-local limit, so **no new top-level `local`** (new code goes in a function scope and exports through an existing table, as `stage_e()` and `stage_d()` do); every mode, toggle, drill, savestate and A/B feature keeps working (the LAB roadmap's stages 0, A to E are not trimmed); `gd.player` and the game constants come from the engine, never typed in; a bug fixed from an in-game run gets a check in `lab_stage_d_check.lua`; and a LAB change has not run in the game unless a Windows agent ran it: the commit says so.
- **No disc-derived data, ever.** Fixtures are `mod.json` files only. No screenshots as verification. Credit any outside idea in the same change (none expected).
- **Naming:** `at_*` / `At*` in C, `gw_ui_*` files, Lua `gd.ui`, role names `a_*`; mod screen ids start with the mod id and a dot (`geno-lab.pause`), and a block, cell or item id is at most 23 characters. English only.
- **Process rules (this machine):** reading, building and tests only until Task 11. No game, launcher or browser window while the owner is at the machine. Never terminate processes by image name; stop only a process you started, by PID. Build only through `tools/port/build.sh` in a private worktree made by `tools/port/agent_new.sh`; never raw clang for the game. Max 8 `melee-pc` instances; keep 2 GB free. Two repositories: game repo `melee/` (branch `pc-port`) and the workspace repo (tools, docs, `CREDITS.md`); each task names the repo of each commit. `gw_mex_bridge.c` churn from `build.sh` is normal and is not committed by you.

## Needs from earlier steps (gated by Task 0)

Names in the last column are the spec's or this plan's assumed ones; Task 0 greps for each. **Hard** needs stop the tasks that use them; **soft** needs are built by Task 5 or 6 when the gate does not find them.

| # | Need | From | Name | Used by | Kind |
|---|---|---|---|---|---|
| N1 | The registry: entries by parent, the MOD tag, caps, manifest `menus` parsing; a way to ask "what does mod X add" | step 2 (U6) | `gw_ui_registry.h`, `at_registry_entries_of(mod_id, ...)` | Tasks 3, 5f | hard |
| N2 | A game menu item that opens an Atlas screen (`FA_ATLAS`), the native door that draws, ticks and hit-tests a screen with no script, and a way for the screen to hand back to the menu | step 2 | `FA_ATLAS`, `gw_ui_native_*` (the same six calls step 6 assumes, plus `gw_ui_native_pad`) | Tasks 3, 4 | hard |
| N3 | Tabs in the screen record: names, counts, the active tab, L and R paging, tab hit rectangles | step 5 | `AtScreen.n_tabs` | Tasks 1, 5d, 7 | hard |
| N4 | `gd.ui.hud` with zones, the `note{}` and `strip{}` parts, keep-out rectangles for the retail HUD | step 3 | `"hud"` in the binding | Tasks 6, 9 | hard |
| N5 | A screen over the world instead of the opaque ground (the pause description) | step 3 | `AtScreen.backdrop` | Tasks 5b, 7 | soft |
| N6 | A `stepper` value (left and right change, A accepts) | step 5 or here | `AT_VAL_STEPPER` | Tasks 5a, 7 | soft |
| N7 | Explainer WITH tags | step 3 or here | `AtExplainer.with_tag` | Tasks 5c, 7 | soft |
| N8 | `gd.ui.token(name)` | here | `"token"` in the binding | Tasks 5e, 12 | soft |
| N9 | `gd.ui.entries(parent)` and `gd.ui.activate(entry_id)` | step 2 or here | `"entries"` | Tasks 5f, 8 | soft |
| N10 | The tab syntax from Lua (`tabs`, `tab`, `on.tab`) | step 5 or here | `"tabs"` in `gw_ui_screen.c` | Task 5 | soft |

## Review Focus

The failure modes the spec implies that no happy-path test exercises, most likely to bite first. Each is pinned by a named test.

| # | What goes wrong | Pinned by |
|---|---|---|
| 1 | **A toggle changes more than the row says**: turning a mod off turns its dependents off, turning one on turns requirements on and conflicting mods off; a silent cascade leaves the player with a different set than the one shown. Or the save fails and the screen still says "Saved". | Task 1 `cascade_*`, `save_failure` (the note names the other mods; a failed save says so and the row still shows the pending truth) |
| 2 | **Focus lost or on the wrong mod** after a toggle, a resolve (the CONFLICTS tab shrinks under the cursor), a tab change, or with 256 mods (the 32-row window shifts). | Task 1 `window_walk`, `refocus_*` |
| 3 | **Text overflow**: a 63-character name, a 120-character description, `Mods_StatusText` ("conflicts with a-long-mod-id"), an "adds Solo > Envoy" line, and the counter plus the restart note against the key hints at 640. | Task 1 `long_strings_*` (rows linted through their hit rectangles), Task 7 `desc_lint` |
| 4 | **A LAB row loses a handler or fires twice**: a row with both `run` and `adjust` flips a toggle twice (once each), A on a stepper steps instead of running, a `run` that calls `menu_close()` runs against a screen that is already gone. | Task 7 checks 4 and 5 (`a toggle flips once`, `a stepper: right changes it, A runs it`) and 7 (`Resume closes cleanly`) |
| 5 | **Tests that pass only as the developer console**: the console may open any screen and bypasses ownership; step 1's own second fix round found a handler result judged against the wrong script. Every LAB and binding test here runs as the script `geno-lab` (`gs.cur` set, `Stub.new{ caller = 'geno-lab', owner_mod = 'geno-lab' }`), and a negative test registers a screen id without the prefix and expects the refusal. | Task 5 binding checks (`gs.cur = 1`), Task 7 check 2 (the owner is the script), Task 8 check 4 |
| 6 | **Focus lost after the LAB re-registers** (every action rebuilds the description): the focus must stay on the same row id, a tab change must restore that tab's last row, and a deleted state must leave the focus on a neighbour. | Task 7 check 6, Task 8 check 2 (the neighbour after a delete) |
| 7 | **The LAB reaches into a netplay session or lives past its script**: an Atlas LAB screen opened while `netplay` is true; a handler running after a hot reload or after `menu_leave`; the screen left open when the match ends. | Task 8 checks 6 to 8 (online, a new match, a reload), Task 7 check 8 (leaving) |
| 8 | **The pause leaks or fails to resume**: `menu_close` must resume only if the menu paused the game, and zero the inputs of all six ports; the Atlas path must keep exactly those effects. | Task 7 check 7 (resume once, six ports neutralised, paused stays paused) |
| 9 | **Style rule breaks in this plan's own C**: chamfers on the wrong corner, a hit-id colour with no second signal, readout text over its plate, a focus with fewer than three cues. | Task 6 lint checks (`atlas_lint.h`) |
| 10 | **A HUD panel on the retail HUD**: the info readout or the timeline overlapping the retail damage plates or the match timer at 4:3 and wide. | Task 6 step 5 (`keepouts`), Task 11 step 3.8 |

---

## File structure

Game repo (`melee/`).

| File | Create/Modify | Responsibility |
|---|---|---|
| `pc/platform/gw_ui_mods.h/.c` | Create | `AtModsSrc`, `AtModsState`, `at_mods_build`, `at_mods_event`, the detail screen, parent labels |
| `pc/platform/gw_ui_mods_native.c/.h` | Create | the real `AtModsSrc` over `gw_Mods_*` and the registry, the door |
| `pc/platform/gw_mods.c/.h` | Modify | `gw_Mods_Conflicts` |
| `pc/platform/gw_ui_hud_parts.h/.c` | Create | `at_part_readout`, `at_part_track` and their value-tree conversions |
| `pc/platform/gw_ui_screen.h/.c`, `gw_ui_parts.c`, `gw_ui_render.c` | Modify | `AT_VAL_STEPPER`, `backdrop`, WITH tags (only the ones the gate says are missing) |
| `pc/platform/gw_script_ui.inc` | Modify | stepper events, `tabs` from Lua, `gd.ui.token`, `gd.ui.entries`, `gd.ui.activate`, the HUD part kinds |
| `pc/tests/atlas_mods_test.c`, `atlas_hud_parts_test.c`, `fixtures/mods-atlas/` | Create | model tests, part tests, the fixture mods folder (`mod.json` only) |
| `pc/tests/atlas_ui_stub.lua`, `atlas_ui_stub_test.lua` | Modify | stepper, tabs, hud parts, token, entries in the stub, with tests |
| `pc/geno/mods/geno-lab/scripts/lab.lua` | Modify | the mapper (own function scope), the hooks in `menu_open`, `menu_close`, `menu_leave`, `on_match_start`, the `lab ui` command, the HUD conversions |
| `pc/geno/tools/lab_stage_d_check.lua` | Modify | the LAB Atlas checks (the harness already runs the whole script) |
| `src/melee/gm/gmfrontend_menus.inc`, `gmfrontend_settings.inc` | Modify | the Mods entry opens the Atlas screen; the Settings page is retired behind the switch |

Workspace repo (root).

| File | Create/Modify | Responsibility |
|---|---|---|
| `tools/port/atlas_gate.py` | Modify | step 7's requirements and soft needs |
| `tools/port/native_test.sh` | Modify | cases `atlas-mods`, `atlas-hud-parts` |
| `tools/port/lab_locals.sh` | Create | reports `lab.lua`'s main-chunk local count and compiles it |
| `docs/scripting.md`, `docs/mods-packaging.md`, `docs/TERMINOLOGY.md`, `melee/docs/geno.md`, `geno-lab/CLAUDE.md`, `docs/NEXT-SESSION.md` | Modify | the API, the manifest `menus` and `mods.self`, the LAB's new UI |

## Preflight (once, before Task 0; not a task)

- [ ] **Step 1: Read.** `CLAUDE.md` (root), `docs/NEXT-SESSION.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md`, `melee/pc/geno/mods/geno-lab/CLAUDE.md`, spec sections 6.5, 7, 8, 13.7, `docs/mods-packaging.md` section 4, `pc/platform/gw_mods.h`, `gmfrontend_settings.inc` from `FSP_MODS` to the end of the Mods block, and `lab.lua` from "LAB mode: the full-screen pause menu" to `lab_menu_draw`, `states_items`, `on_tick` and `on_draw`.
- [ ] **Step 2: A private lane and the shell** (names changed from step 1's):

```bash
export MAIN="<the workspace root: the directory that contains tools/ and _toolchains/>"
cd "$MAIN" && tools/port/agent_new.sh atlas7
git -C "$MAIN" worktree add worktrees/ws-atlas7 -b ws/atlas7
export WS="$MAIN/worktrees/ws-atlas7"; export GW_ROOT="$MAIN"
export GW_MELEE="$MAIN/worktrees/atlas7"; export GW_BUILD_ROOT="$MAIN/_build/agents/atlas7"   # as agent_new.sh printed them
nt() { GW_ROOT="$MAIN" GW_MELEE="$GW_MELEE" GW_BUILD_ROOT="$GW_BUILD_ROOT" bash "$WS/tools/port/native_test.sh" "$1"; }
```

- [ ] **Step 3: Baselines** (must still pass at the end):

```bash
for t in atlas-tokens atlas-layout atlas-focus atlas-input atlas-screen atlas-stack atlas-parts atlas-render atlas-binding; do nt $t | tail -1; done
cd "$GW_MELEE" && lua pc/tests/atlas_ui_stub_test.lua | tail -1
cd "$GW_MELEE" && lua pc/geno/tools/lab_stage_d_check.lua pc/geno/mods/geno-lab/scripts/lab.lua | tail -3
```

The step 1 notes say `lab_stage_d_check.lua` "fails from a checkout root on a path issue that is not yours"; if the last command fails that way, run it from `$GW_MELEE/pc/geno` with the paths relative to it and use that form everywhere below. Record whichever form passes and the number of `PASS` lines: the LAB checks must not lose one.
- [ ] **Step 4: Is step 6 merged?** Task 1's lint helpers (`pc/tests/atlas_lint.h`) and `tools/port/atlas_gate.py` come from step 6 (its Tasks 0 and 1; they depend only on step 1). If they are absent, do step 6's Tasks 0 and 1 first, verbatim.

---

### Task 0: The gate for step 7

**Files:**
- Modify (workspace repo): `tools/port/atlas_gate.py`

**Interfaces:**
Produces: `python tools/port/atlas_gate.py --step 7` exits 0 when every **hard** requirement is present; **soft** ones that are missing print `SOFT` and name the task that builds them.

Tasks 1 and 2 need only step 1 plus the lint helpers and may start at once. **Tasks 3, 4, 6, 7, 8 and 9 start only when the gate exits 0** (hard needs present). Task 5 builds exactly the soft items the gate lists.

- [ ] **Step 1: Teach the script soft requirements and fill step 7's table.** In `tools/port/atlas_gate.py` replace the line `    7: [],  # filled by the step 7 plan, Task 0` with:

```python
    7: [
        ("pc/platform/gw_ui_registry.h", r"at_registry", "step 2", "N1 the registry (entries by parent, manifests)"),
        ("src/melee/gm/gmfrontend_atlas.inc", r"FA_ATLAS", "step 2", "N2 a menu item that opens an Atlas screen"),
        ("pc/platform/gw_ui_screen.h", r"\bn_tabs\b", "step 5", "N3 tabs in the screen record"),
        ("pc/platform/gw_script_ui.inc", r'"hud"', "step 3", "N4 gd.ui.hud"),
        ("pc/platform/gw_ui_screen.h", r"\bbackdrop\b", "step 3", "N5 a screen over the world", "Task 5"),
        ("pc/platform/gw_ui_screen.h", r"AT_VAL_STEPPER", "step 5", "N6 the stepper value", "Task 5"),
        ("pc/platform/gw_ui_screen.h", r"with_tag", "step 3", "N7 explainer WITH tags", "Task 5"),
        ("pc/platform/gw_script_ui.inc", r'"token"', "this plan", "N8 gd.ui.token", "Task 5"),
        ("pc/platform/gw_script_ui.inc", r'"entries"', "step 2", "N9 gd.ui.entries and activate", "Task 5"),
        ("pc/platform/gw_ui_screen.c", r'"tabs"', "step 5", "N10 tabs from Lua", "Task 5"),
    ],
```

and replace the checking loop (`for rel, rx, owner, why in G[a.step]:` through the `print("MISSING ...")` and `missing += 1` lines) with:

```python
    for e in G[a.step]:
        rel, rx, owner, why = e[:4]
        soft = e[4] if len(e) > 4 else None
        path = os.path.join(root, rel)
        text = open(path, encoding="utf-8", errors="replace").read() if os.path.exists(path) else None
        if text is None or not re.search(rx, text):
            if soft:
                print("SOFT     %-46s %-8s %s (built by %s)" % (rel, owner, why, soft))
            else:
                print("MISSING  %-46s %-8s %s (%s)" % (rel, owner, why, rx))
                missing += 1
```

Step 6's four-element entries keep working (`e[4]` is read only when present).
- [ ] **Step 2: Run it and record the result.**

```bash
cd "$WS" && python tools/port/atlas_gate.py --step 7
```

Expected today: four `MISSING` lines (N1 to N4), up to six `SOFT` lines, `gate step 7: 4 missing`, exit 1: the gate can fail. When the earlier steps merge, reconcile any real name that differs (in this table and in the "Needs" table above, in the same commit). Re-run `--step 6` to prove the edit did not break it.
- [ ] **Step 3: Commit.** Workspace repo: `tools/port/atlas_gate.py`, message `tools: atlas_gate.py gains step 7's requirements and soft needs`.

---

### Task 1: The mods model: rows, tabs, windowing, toggles, conflicts

The MODS screen is a **pure model** over an accessor table. The real table (Task 3) reads `gw_Mods_*` and the registry; the tests use a fake with the same cascade rules as the real resolver, so everything below runs with no game and no mods folder.

**Files:**
- Create (game repo): `pc/platform/gw_ui_mods.h`, `pc/platform/gw_ui_mods.c`, `pc/tests/atlas_mods_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-mods`)

**Interfaces:**
Consumes: `AtScreen`, `AtView`, `AtEvent`, `at_list_scroll`, the parts through `at_render_ex`, `atlas_lint.h`; N3 for tabs (one wrapper, `set_tabs`, marked `RECONCILE`).
Produces: `AtModsSrc` (accessors, listed below), `AtModsState`, `at_mods_state_init`, `at_mods_build(src, state, screen, view, now_ms)`, `at_mods_event(src, state, event, now_ms, action)` returning an `AtModsAction` (`AT_MA_NONE`, `AT_MA_BACK`, `AT_MA_DETAIL` with the mod index, `AT_MA_SETTINGS` with a screen id), `at_mods_parent_label`, `at_mods_add_line`.

Behaviour the tests pin (each is a rule of the screen):
- The INSTALLED tab lists every mod in the API's order; the CONFLICTS tab lists mods whose boot status is `CONFLICT` or `MISSING_DEP`. Tab counts are shown (`INSTALLED 8`, `CONFLICTS 2`).
- A row is: name; sub line = kind word, then the pack, then `adds Solo > Envoy` when the registry says so, then a status word (`CONFLICT`, the status text for a missing dependency, `RESTART` when the next-boot state differs from the mounted one); a toggle value that shows the **next-boot** state; the jade `selected` bar when the mod is mounted **now**.
- A (and left and right) toggle the focused mod, save at once (as the legacy page did), and say what else changed ("Also turned off ace-wolf."). A failed save says so and the row still shows the pending state.
- X resolves a conflict row (turn the dropped mod off) or a missing dependency (turn it on, which turns its requirements on; when nothing changes, say which requirement is not installed).
- Y asks for the detail screen (Task 2). B goes back. L, R and Tab switch tabs; each tab keeps its own selection and scroll.
- While `restart_needed`, a persistent corner note says `Applies at restart`.
- The screen record holds at most `AT_MAX_ITEMS` rows; the model keeps a window of 32 around the visible rows and the view's focus and scroll are relative to it, so 256 mods behave like 8.

- [ ] **Step 1: Write the failing test.** Create `pc/tests/atlas_mods_test.c`:

```c
#include "atlas_lint.h"
#include "../platform/gw_ui_mods.h"
#include "../platform/gw_ui_render.h"

/* ---- a fake mods folder with the real resolver's cascade rules ---- */
#define FM_MAX 256
typedef struct { char id[40], name[64], kind[12], pack[12], desc[160], req[64], con[64], status_text[100], adds[3][64]; int status, enabled, active, nadds; char settings[40]; } FMod;
static FMod FM[FM_MAX];
static int fm_n, fm_restart, fm_save_calls, fm_save_result;

static int fm_find(const char *id) { int i; for (i = 0; i < fm_n; i++) if (strcmp(FM[i].id, id) == 0) return i; return -1; }
static int has_word(const char *list, const char *id)
{
    char buf[100], *p, *save = NULL;
    snprintf(buf, sizeof buf, "%s", list);
    for (p = strtok_s(buf, ",", &save); p != NULL; p = strtok_s(NULL, ",", &save)) if (strcmp(p, id) == 0) return 1;
    return 0;
}
static void fm_recompute_restart(void) { int i; fm_restart = 0; for (i = 0; i < fm_n; i++) if (FM[i].enabled != FM[i].active) fm_restart = 1; }
/* enabling turns requirements on and enabled conflicting mods off (either direction); disabling turns dependents off */
static int fm_set(void *u, int i, int on)
{
    int j, changed = 0;
    (void) u;
    if (i < 0 || i >= fm_n || FM[i].enabled == on) return 0;
    FM[i].enabled = on; changed++;
    for (j = 0; j < fm_n; j++) {
        if (j == i) continue;
        if (on && has_word(FM[i].req, FM[j].id) && !FM[j].enabled) { FM[j].enabled = 1; changed++; }
        if (on && FM[j].enabled && (has_word(FM[i].con, FM[j].id) || has_word(FM[j].con, FM[i].id))) { FM[j].enabled = 0; changed++; }
        if (!on && FM[j].enabled && has_word(FM[j].req, FM[i].id)) { FM[j].enabled = 0; changed++; }
    }
    fm_recompute_restart();
    return changed;
}
static int fm_count(void *u) { (void) u; return fm_n; }
#define FM_STR(field) static const char *fm_##field(void *u, int i) { (void) u; return FM[i].field; }
FM_STR(id) FM_STR(name) FM_STR(kind) FM_STR(pack) FM_STR(desc) FM_STR(status_text)
static const char *fm_version(void *u, int i) { (void) u; (void) i; return "1.0"; }
static const char *fm_requires(void *u, int i) { (void) u; return FM[i].req; }
static const char *fm_conflicts(void *u, int i) { (void) u; return FM[i].con; }
static int fm_status(void *u, int i) { (void) u; return FM[i].status; }
static int fm_enabled(void *u, int i) { (void) u; return FM[i].enabled; }
static int fm_active(void *u, int i) { (void) u; return FM[i].active; }
static int fm_save(void *u) { (void) u; fm_save_calls++; return fm_save_result; }
static int fm_restart_needed(void *u) { (void) u; return fm_restart; }
static int fm_adds(void *u, int i, char out[][AT_STR], int cap)
{
    int k;
    (void) u;
    for (k = 0; k < FM[i].nadds && k < cap; k++) snprintf(out[k], AT_STR, "%s", FM[i].adds[k]);
    return k < FM[i].nadds ? k : FM[i].nadds;
}
static int fm_settings(void *u, int i, char *sid, int cap, char *label, int lcap)
{
    (void) u;
    if (!FM[i].settings[0]) return 0;
    snprintf(sid, (size_t) cap, "%s", FM[i].settings); snprintf(label, (size_t) lcap, "%s settings", FM[i].name);
    return 1;
}
static AtModsSrc src(void)
{
    AtModsSrc s;
    memset(&s, 0, sizeof s);
    s.count = fm_count; s.id = fm_id; s.name = fm_name; s.version = fm_version; s.kind = fm_kind; s.pack = fm_pack; s.desc = fm_desc;
    s.requires = fm_requires; s.conflicts = fm_conflicts; s.status = fm_status; s.status_text = fm_status_text; s.enabled = fm_enabled;
    s.active = fm_active; s.set_enabled = fm_set; s.save = fm_save; s.restart_needed = fm_restart_needed; s.adds = fm_adds; s.settings = fm_settings;
    return s;
}
static void add(const char *id, const char *name, const char *kind, const char *req, const char *con, int status, int enabled, int active)
{
    FMod *m = &FM[fm_n++];
    memset(m, 0, sizeof *m);
    snprintf(m->id, sizeof m->id, "%s", id); snprintf(m->name, sizeof m->name, "%s", name); snprintf(m->kind, sizeof m->kind, "%s", kind);
    snprintf(m->req, sizeof m->req, "%s", req); snprintf(m->con, sizeof m->con, "%s", con);
    m->status = status; m->enabled = enabled; m->active = active;
    snprintf(m->desc, sizeof m->desc, "%s", "A mod.");
}
/* the eight-mod folder of the plan: a base, a fighter that needs it, a script with a Solo entry, two drive packs that conflict,
 * the LAB, a fighter whose base is not installed, and one that is simply off */
static void fixture(void)
{
    fm_n = 0; fm_save_calls = 0; fm_save_result = 0; fm_restart = 0;
    add("ace-base", "ACE Base", "base", "", "", AT_MOD_ACTIVE, 1, 1);
    add("ace-wolf", "ACE Wolf", "fighter", "ace-base", "", AT_MOD_ACTIVE, 1, 1);
    add("envoy", "Supertime Envoy", "script", "", "", AT_MOD_ACTIVE, 1, 1);
    snprintf(FM[2].adds[0], 64, "%s", "Solo > Envoy"); FM[2].nadds = 1; snprintf(FM[2].settings, sizeof FM[2].settings, "%s", "envoy.settings");
    add("envoy-drives", "Envoy Drives", "misc", "", "envoy-drives-sa2", AT_MOD_ACTIVE, 1, 1);
    add("envoy-drives-sa2", "Envoy Drives SA2", "misc", "", "envoy-drives", AT_MOD_CONFLICT, 1, 0);
    snprintf(FM[4].status_text, sizeof FM[4].status_text, "%s", "conflicts with envoy-drives");
    add("geno-lab", "Geno Lab", "script", "", "", AT_MOD_ACTIVE, 1, 1);
    snprintf(FM[5].adds[0], 64, "%s", "Solo > LAB"); FM[5].nadds = 1;
    add("orphan", "Orphan Fighter", "fighter", "missing-base", "", AT_MOD_MISSING_DEP, 1, 0);
    snprintf(FM[6].status_text, sizeof FM[6].status_text, "%s", "needs missing-base");
    add("sora", "Sora", "fighter", "", "", AT_MOD_OFF, 0, 0);
}
static void many(int n)
{
    int i;
    fm_n = 0; fm_save_calls = 0; fm_save_result = 0; fm_restart = 0;
    for (i = 0; i < n; i++) {
        char id[40], name[64];
        snprintf(id, sizeof id, "mod-%03d", i); snprintf(name, sizeof name, "Fighter Number %03d", i);
        add(id, name, "fighter", "", "", AT_MOD_ACTIVE, i % 3 != 0, i % 3 != 0);
    }
}

static AtModsState ST; static AtScreen SC; static AtView VW;
static AtEvent ev(int type, int a, int b) { AtEvent e; e.type = type; e.a = a; e.b = b; return e; }
static void build(const AtModsSrc *s) { CHECK(at_mods_build(s, &ST, &SC, &VW, 1000.0) == 1); }
static AtModsAction press(const AtModsSrc *s, AtEvent e) { AtModsAction a; at_mods_event(s, &ST, &e, 1000.0, &a); build(s); return a; }
static const char *focused_label(void) { return VW.focus.index >= 0 && VW.focus.index < SC.n_items ? SC.items[VW.focus.index].label : "(none)"; }

static void rows(void)
{
    AtModsSrc s = src();
    int i;
    fixture(); at_mods_state_init(&ST); memset(&VW, 0, sizeof VW); build(&s);
    CHECK(SC.n_items == 8 && SC.primary == AT_PRIMARY_LIST && SC.chapter == 4 && strcmp(SC.title, "MODS") == 0);
    CHECK(SC.n_tabs == 2 && SC.tab_count[0] == 8 && SC.tab_count[1] == 2);                     /* RECONCILE (step 5): the tab fields */
    CHECK(strcmp(SC.items[0].label, "ACE Base") == 0 && SC.items[0].vkind == AT_VAL_TOGGLE && SC.items[0].on == 1);
    CHECK(SC.items[7].on == 0 && !(SC.items[7].flags & AT_CELL_SELECTED));                      /* off: toggle off, not mounted */
    CHECK((SC.items[2].flags & AT_CELL_SELECTED) && strstr(SC.items[2].sub, "adds Solo > Envoy") != NULL);   /* mounted now: the jade bar */
    CHECK(strstr(SC.items[4].sub, "CONFLICT") != NULL && !(SC.items[4].flags & AT_CELL_SELECTED));            /* a word, not only a colour */
    CHECK(strstr(SC.items[6].sub, "needs missing-base") != NULL);
    CHECK(strstr(SC.items[0].sub, "Base") != NULL);
    for (i = 0; i < SC.n_items; i++) CHECK(strlen(SC.items[i].id) < AT_ID && SC.items[i].id[0] != '\0');
    CHECK(VW.focus.index == 0 && VW.scroll == 0);
    CHECK(strcmp(VW.counter, "1 / 8") == 0);
    CHECK(VW.note.text[0] == '\0');                                                             /* nothing to restart yet */
    /* the explainer follows the focus */
    CHECK(VW.ex.has && strcmp(VW.ex.title, "ACE Base") == 0 && strstr(VW.ex.from_text, "ace-base") != NULL);
    /* the keys: A names what it does to THIS mod, B backs out, Y asks for details */
    CHECK(strcmp(VW.key_label[0], "Turn off") == 0);
    press(&s, ev(AT_EV_MOVE, AT_DIR_DOWN, 0));
    CHECK(strcmp(focused_label(), "ACE Wolf") == 0 && strcmp(VW.counter, "2 / 8") == 0);
}

static void cascade(void)
{
    AtModsSrc s = src();
    AtModsAction a;
    fixture(); at_mods_state_init(&ST); memset(&VW, 0, sizeof VW); build(&s);
    /* turning the base off turns ace-wolf off with it, and the note says so; the file is saved once */
    a = press(&s, ev(AT_EV_ACCEPT, 0, 0));
    CHECK(a.kind == AT_MA_NONE && fm_save_calls == 1 && !FM[0].enabled && !FM[1].enabled);
    CHECK(strstr(VW.note.text, "ACE Wolf") != NULL && strstr(VW.note.text, "off") != NULL && VW.note.kind == AT_NOTE_OK);
    CHECK(SC.items[0].on == 0 && SC.items[1].on == 0);                                         /* the rows show the pending truth */
    CHECK(SC.items[0].flags & AT_CELL_SELECTED);                                               /* still mounted this boot */
    CHECK(strstr(SC.items[0].sub, "RESTART") != NULL && fm_restart == 1);
    /* the restart note is persistent and says what it is */
    CHECK(strcmp(VW.note.text, "Applies at restart") == 0 || strstr(VW.note.text, "ACE Wolf") != NULL);
    /* back on: the requirement comes with it */
    press(&s, ev(AT_EV_MOVE, AT_DIR_DOWN, 0));
    a = press(&s, ev(AT_EV_ACCEPT, 0, 0));                                                      /* ACE Wolf on: ace-base on too */
    CHECK(FM[1].enabled && FM[0].enabled && strstr(VW.note.text, "ACE Base") != NULL && strstr(VW.note.text, " on") != NULL);
    CHECK(fm_restart == 0);                                                                     /* the next-boot set equals the mounted one again */
    /* left and right toggle too (a toggle row flips on A, left or right) */
    press(&s, ev(AT_EV_MOVE, AT_DIR_RIGHT, 0));
    CHECK(!FM[1].enabled);
    /* a failed save is said, and the row still shows the pending state */
    fm_save_result = -1; fm_save_calls = 0;
    press(&s, ev(AT_EV_MOVE, AT_DIR_UP, 0));
    press(&s, ev(AT_EV_ACCEPT, 0, 0));
    CHECK(fm_save_calls == 1 && VW.note.kind == AT_NOTE_ERR && strstr(VW.note.text, "Could not save") != NULL);
    CHECK(SC.items[0].on == FM[0].enabled);
    /* turning a conflicting pack on turns the other off (either direction), and says which */
    fixture(); at_mods_state_init(&ST); build(&s);
    FM[4].status = AT_MOD_OFF; FM[4].enabled = 0; FM[3].enabled = 0; FM[3].status = AT_MOD_OFF; fm_recompute_restart();
    ST.sel[0] = 3; build(&s);
    press(&s, ev(AT_EV_ACCEPT, 0, 0));
    CHECK(FM[3].enabled && !FM[4].enabled);
    press(&s, ev(AT_EV_MOVE, AT_DIR_DOWN, 0));
    press(&s, ev(AT_EV_ACCEPT, 0, 0));
    CHECK(FM[4].enabled && !FM[3].enabled && strstr(VW.note.text, "Envoy Drives") != NULL);
}

static void conflicts(void)
{
    AtModsSrc s = src();
    AtModsAction a;
    fixture(); at_mods_state_init(&ST); memset(&VW, 0, sizeof VW); build(&s);
    press(&s, ev(AT_EV_PAGE, 1, 0));                                                            /* R: the CONFLICTS tab */
    CHECK(ST.tab == 1 && SC.n_items == 2 && strcmp(SC.items[0].label, "Envoy Drives SA2") == 0 && strcmp(SC.items[1].label, "Orphan Fighter") == 0);
    CHECK(VW.ex.has && strstr(VW.ex.kicker, "CONFLICT") != NULL);
    CHECK(strcmp(VW.counter, "1 / 2") == 0);
    /* X resolves the conflict: the dropped mod goes off, the tab shrinks, the focus lands on what is left */
    a = press(&s, ev(AT_EV_ALT, 'X', 0));
    CHECK(a.kind == AT_MA_NONE && !FM[4].enabled && fm_save_calls == 1);
    CHECK(SC.n_items == 2);                                                                     /* the boot status is still CONFLICT until the restart */
    /* statuses are boot facts; after a restart the row leaves the tab: simulate it and check the selection clamps */
    FM[4].status = AT_MOD_OFF; FM[6].status = AT_MOD_OFF; build(&s);
    CHECK(SC.n_items == 1 && (SC.items[0].flags & AT_CELL_DISABLED) && ST.sel[1] == 0);        /* both gone: the empty row, the selection clamped */
    FM[4].status = AT_MOD_CONFLICT; FM[6].status = AT_MOD_MISSING_DEP; ST.sel[1] = 1; build(&s);
    CHECK(strcmp(focused_label(), "Orphan Fighter") == 0);
    /* a missing dependency that is not installed cannot be fixed: the note says which one */
    a = press(&s, ev(AT_EV_ALT, 'X', 0));
    CHECK(VW.note.kind == AT_NOTE_ERR && strstr(VW.note.text, "missing-base") != NULL && strstr(VW.note.text, "not installed") != NULL);
    /* one that is installed but off is turned on by name */
    add("needs-sora", "Needs Sora", "fighter", "sora", "", AT_MOD_MISSING_DEP, 1, 0);
    build(&s);
    ST.sel[1] = 2; build(&s);
    CHECK(strcmp(focused_label(), "Needs Sora") == 0);
    press(&s, ev(AT_EV_ALT, 'X', 0));
    CHECK(FM[7].enabled == 1 && strstr(VW.note.text, "Sora") != NULL && VW.note.kind == AT_NOTE_OK);
    /* an empty tab says so instead of showing nothing, and A on it does nothing */
    FM[4].status = AT_MOD_OFF; FM[6].status = AT_MOD_OFF; FM[8].status = AT_MOD_OFF; ST.sel[1] = 0; build(&s);
    CHECK(SC.n_items == 1 && (SC.items[0].flags & AT_CELL_DISABLED) && strstr(SC.items[0].label, "No conflicts") != NULL);
    fm_save_calls = 0; press(&s, ev(AT_EV_ACCEPT, 0, 0)); CHECK(fm_save_calls == 0);
    /* each tab keeps its own selection */
    press(&s, ev(AT_EV_PAGE, -1, 0));
    CHECK(ST.tab == 0);
    ST.sel[0] = 5; build(&s); press(&s, ev(AT_EV_PAGE, 1, 0)); press(&s, ev(AT_EV_PAGE, -1, 0));
    CHECK(strcmp(focused_label(), "Geno Lab") == 0);
}

static void window_walk(void)
{
    AtModsSrc s = src();
    int k;
    many(256); at_mods_state_init(&ST); memset(&VW, 0, sizeof VW); build(&s);
    CHECK(SC.n_items <= AT_MAX_ITEMS && SC.tab_count[0] == 256);
    for (k = 1; k <= 255; k++) {                                                                /* down the whole folder */
        char want[64];
        press(&s, ev(AT_EV_MOVE, AT_DIR_DOWN, 0));
        snprintf(want, sizeof want, "Fighter Number %03d", k);
        CHECK(strcmp(focused_label(), want) == 0);
        CHECK(SC.n_items <= AT_MAX_ITEMS && VW.focus.index >= VW.scroll && VW.focus.index < VW.scroll + AT_MODS_VISIBLE);   /* the focus is on screen */
    }
    press(&s, ev(AT_EV_MOVE, AT_DIR_DOWN, 0));                                                  /* wraps to the top */
    CHECK(strcmp(focused_label(), "Fighter Number 000") == 0 && ST.sel[0] == 0);
    press(&s, ev(AT_EV_MOVE, AT_DIR_UP, 0));                                                    /* and back to the bottom */
    CHECK(strcmp(focused_label(), "Fighter Number 255") == 0);
    for (k = 254; k >= 0; k--) {
        char want[64];
        press(&s, ev(AT_EV_MOVE, AT_DIR_UP, 0));
        snprintf(want, sizeof want, "Fighter Number %03d", k);
        CHECK(strcmp(focused_label(), want) == 0);
    }
    /* a mouse hover reports a row of the WINDOW: it must land on that mod, not on the same index of the whole list */
    ST.sel[0] = 200; build(&s);
    press(&s, ev(AT_EV_FOCUS, 0, VW.focus.index + 2));
    CHECK(ST.sel[0] == 202 && strcmp(focused_label(), "Fighter Number 202") == 0);
    /* the wheel scrolls */
    press(&s, ev(AT_EV_SCROLL, -1, 0)); CHECK(ST.sel[0] == 201);
    /* toggling in the middle of 256 touches the right mod */
    press(&s, ev(AT_EV_ACCEPT, 0, 0));
    CHECK(FM[201].enabled == (201 % 3 != 0 ? 0 : 1));
    /* an empty folder: one disabled row and a hint, no crash, no action */
    fm_n = 0; at_mods_state_init(&ST); build(&s);
    CHECK(SC.n_items == 1 && (SC.items[0].flags & AT_CELL_DISABLED) && strstr(SC.items[0].label, "No mods") != NULL);
    press(&s, ev(AT_EV_ACCEPT, 0, 0)); press(&s, ev(AT_EV_ALT, 'Y', 0)); press(&s, ev(AT_EV_ALT, 'X', 0));
}

static void actions(void)
{
    AtModsSrc s = src();
    AtModsAction a;
    fixture(); at_mods_state_init(&ST); memset(&VW, 0, sizeof VW); build(&s);
    a = press(&s, ev(AT_EV_BACK, 0, 0)); CHECK(a.kind == AT_MA_BACK);
    ST.sel[0] = 2; build(&s);
    a = press(&s, ev(AT_EV_ALT, 'Y', 0)); CHECK(a.kind == AT_MA_DETAIL && a.arg == 2);
    a = press(&s, ev(AT_EV_START, 0, 0)); CHECK(a.kind == AT_MA_NONE);
}

/* every row's texts must sit inside its row rectangle, at three widths, with the worst strings the folder can hold */
static void long_strings(void)
{
    AtModsSrc s = src();
    static const float widths[3] = { 640.0f, 853.0f, 1140.0f };
    int w, i, j;
    fixture();
    memset(FM[0].name, 'W', 63); FM[0].name[63] = '\0';
    memset(FM[2].adds[0], 'A', 63); FM[2].adds[0][63] = '\0';
    memset(FM[4].status_text, 's', 99); FM[4].status_text[99] = '\0';
    memset(FM[1].desc, 'd', 159); FM[1].desc[159] = '\0';
    for (w = 0; w < 3; w++) {
        static AtHits hits; AtRenderInfo info; AtSink sk;
        at_mods_state_init(&ST); memset(&VW, 0, sizeof VW); build(&s);
        sk = rec_sink();
        at_render_ex(&SC, &VW, widths[w], 1000.0, 0, &FAKE, &sk, &hits, &info);
        CHECK(info.entries < 1500 && !info.capped);
        for (i = 0; i < hits.n; i++) {
            if (hits.h[i].kind != AT_HIT_CELL) continue;
            for (j = 0; j < REC.nt; j++) {
                float x0, x1, y0, y1;
                lint_text_box(&REC.t[j], &x0, &x1, &y0, &y1);
                if (REC.t[j].base < hits.h[i].r.y || REC.t[j].base > hits.h[i].r.y + hits.h[i].r.h) continue;
                if (x0 < hits.h[i].r.x - 0.5f) continue;                                         /* left of the row: the margin or the rail */
                if (x0 > hits.h[i].r.x + hits.h[i].r.w) continue;                                /* right of it: the explainer */
                CHECK(x1 <= hits.h[i].r.x + hits.h[i].r.w + 0.5f && at_role_size(REC.t[j].role) >= 12);
            }
        }
        press(&s, ev(AT_EV_PAGE, 1, 0)); press(&s, ev(AT_EV_PAGE, -1, 0));
    }
    /* the counter and the restart note against the key hints: the hints that do not fit are left off, never overlapped */
    FM[0].enabled = 0; fm_recompute_restart();
    build(&s);
    CHECK(VW.note.text[0] != '\0');
}

static void parents(void)
{
    char out[64];
    CHECK(strcmp(at_mods_parent_label("solo"), "Solo") == 0 && strcmp(at_mods_parent_label("versus"), "Versus") == 0);
    CHECK(strcmp(at_mods_parent_label("online"), "Online") == 0 && strcmp(at_mods_parent_label("lab.pause"), "LAB pause") == 0);
    CHECK(strcmp(at_mods_parent_label("settings.video"), "Settings > Video") == 0 && strcmp(at_mods_parent_label("pause"), "Pause") == 0);
    CHECK(strcmp(at_mods_parent_label("whatever"), "whatever") == 0);                           /* unknown: shown as given, never hidden */
    at_mods_add_line("solo", "Envoy", out, sizeof out);
    CHECK(strcmp(out, "Solo > Envoy") == 0);
}

int main(void)
{
    rows();
    cascade();
    conflicts();
    window_walk();
    actions();
    long_strings();
    parents();
    ATLAS_DONE("atlas mods");
}
```

Register in `tools/port/native_test.sh` (append `, atlas-mods` to the die message):

```bash
atlas-mods)
    sources=(pc/tests/atlas_mods_test.c pc/platform/gw_ui_mods.c pc/platform/gw_ui_render.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c) ;;
```

(Add `pc/platform/gw_ui_online_parts.c` and `gw_ui_room.c` to the list if step 6 is merged: `gw_ui_render.c` then references them. The test uses `strtok_s`, which the Windows toolchain provides.)

- [ ] **Step 2: Run to verify it fails.** `nt atlas-mods`. Expected: `fatal error: '../platform/gw_ui_mods.h' file not found`.
- [ ] **Step 3: Write the header.** Create `pc/platform/gw_ui_mods.h`:

```c
/* gw_ui_mods.h - the MODS screen as a pure model: an accessor table in, an AtScreen and view out, events applied. No game, no
 * mods folder, no Lua. The real accessors (gw_Mods_* and the registry) are in gw_ui_mods_native.c. */
#ifndef GW_UI_MODS_H
#define GW_UI_MODS_H
#include "gw_ui_input.h"
#include "gw_ui_parts.h"
#include "gw_ui_screen.h"
#ifdef __cplusplus
extern "C" {
#endif

#define AT_MODS_MAX 256                 /* GW_MODS_MAX in gw_mods.h */
#define AT_MODS_WINDOW AT_MAX_ITEMS     /* rows the record holds */
#define AT_MODS_VISIBLE 8               /* rows the list shows: (362 - 28) / 39 */
/* the same meaning as GW_MOD_*; the real accessor maps them, so no number is shared */
enum { AT_MOD_ACTIVE, AT_MOD_OFF, AT_MOD_MISSING_DEP, AT_MOD_CONFLICT };

typedef struct AtModsSrc {
    void *user;
    int (*count)(void *u);
    const char *(*id)(void *u, int i);
    const char *(*name)(void *u, int i);
    const char *(*version)(void *u, int i);
    const char *(*kind)(void *u, int i);
    const char *(*pack)(void *u, int i);
    const char *(*desc)(void *u, int i);
    const char *(*requires)(void *u, int i);        /* comma-separated ids */
    const char *(*conflicts)(void *u, int i);       /* comma-separated ids: the mod's own list */
    int (*status)(void *u, int i);                  /* AT_MOD_*, for this boot */
    const char *(*status_text)(void *u, int i);
    int (*enabled)(void *u, int i);                 /* for the next boot */
    int (*active)(void *u, int i);                  /* mounted this boot */
    int (*set_enabled)(void *u, int i, int on);     /* how many mods changed, cascades included */
    int (*save)(void *u);                           /* 0 ok */
    int (*restart_needed)(void *u);
    int (*adds)(void *u, int i, char out[][AT_STR], int cap);                             /* "Solo > Envoy" lines from the registry */
    int (*settings)(void *u, int i, char *screen_id, int cap, char *label, int lcap);     /* 1 when the mod has its own settings entry */
} AtModsSrc;

typedef struct {
    int tab;                         /* 0 installed, 1 conflicts */
    int sel[2], top[2];              /* per tab: the selected row and the first visible row, as indices into the tab's list */
    int list[2][AT_MODS_MAX], n[2];  /* mod indices per tab, rebuilt every build */
    int base;                        /* the first list row held in the record (the window) */
    char note[AT_STR]; int note_kind; double note_until;
} AtModsState;

enum { AT_MA_NONE, AT_MA_BACK, AT_MA_DETAIL, AT_MA_SETTINGS };
typedef struct { int kind, arg; char id[AT_ID * 2]; } AtModsAction;

void at_mods_state_init(AtModsState *st);
int at_mods_build(const AtModsSrc *s, AtModsState *st, AtScreen *sc, AtView *vw, double now_ms);
/* applies one event; fills *act; the caller rebuilds afterwards */
void at_mods_event(const AtModsSrc *s, AtModsState *st, const AtEvent *e, double now_ms, AtModsAction *act);
const char *at_mods_parent_label(const char *parent);                          /* "solo" -> "Solo"; unknown ids are returned as given */
void at_mods_add_line(const char *parent, const char *label, char *out, int cap);   /* "Solo > Envoy" */

#ifdef __cplusplus
}
#endif
#endif
```

- [ ] **Step 4: Write the implementation.** Create `pc/platform/gw_ui_mods.c`:

```c
#include "gw_ui_mods.h"
#include "gw_ui_tokens.h"
#include <stdio.h>
#include <string.h>

void at_mods_state_init(AtModsState *st) { memset(st, 0, sizeof *st); }

static const char *kind_word(const char *k)
{
    if (k == NULL) return "Content";
    if (strcmp(k, "base") == 0) return "Base";
    if (strcmp(k, "fighter") == 0) return "Fighter";
    if (strcmp(k, "stage") == 0) return "Stage";
    if (strcmp(k, "script") == 0) return "Script";
    return "Content";
}

const char *at_mods_parent_label(const char *p)
{
    static char buf[4][AT_STR];
    static int k;
    char *o;
    if (strcmp(p, "main") == 0) return "Main menu";
    if (strcmp(p, "solo") == 0) return "Solo";
    if (strcmp(p, "versus") == 0) return "Versus";
    if (strcmp(p, "online") == 0) return "Online";
    if (strcmp(p, "mods") == 0) return "Mods";
    if (strcmp(p, "settings") == 0) return "Settings";
    if (strcmp(p, "more") == 0) return "More";
    if (strcmp(p, "pause") == 0) return "Pause";
    if (strcmp(p, "lab.pause") == 0) return "LAB pause";
    if (strncmp(p, "settings.", 9) == 0) {
        o = buf[k++ & 3];
        snprintf(o, AT_STR, "Settings > %c%s", p[9] >= 'a' && p[9] <= 'z' ? p[9] - 32 : p[9], p + 10);
        return o;
    }
    return p;
}

void at_mods_add_line(const char *parent, const char *label, char *out, int cap)
{
    snprintf(out, (size_t) cap, "%s > %s", at_mods_parent_label(parent), label);
}

/* RECONCILE (step 5): the tab fields of the screen record. Assumed: sc->n_tabs, sc->tab_name[][], sc->tab_count[], vw->tab. */
static void set_tabs(AtScreen *sc, AtView *vw, int active, int n_installed, int n_conflicts)
{
    sc->n_tabs = 2;
    snprintf(sc->tab_name[0], sizeof sc->tab_name[0], "%s", "INSTALLED");
    snprintf(sc->tab_name[1], sizeof sc->tab_name[1], "%s", "CONFLICTS");
    sc->tab_count[0] = n_installed;
    sc->tab_count[1] = n_conflicts;
    vw->tab = active;
}

static void put_key(AtScreen *sc, AtView *vw, char btn, const char *label)
{
    int i = sc->n_keys;
    if (i >= AT_MAX_KEYS) return;
    sc->keys[i].btn = btn;
    snprintf(sc->keys[i].label, sizeof sc->keys[i].label, "%s", label);
    snprintf(vw->key_label[i], sizeof vw->key_label[i], "%s", label);
    vw->key_shown[i] = 1;
    sc->n_keys++;
}

static int word_in(const char *list, const char *id)
{
    size_t n = strlen(id);
    const char *p = list;
    while (p != NULL && *p) {
        const char *e = strchr(p, ',');
        size_t len = e ? (size_t) (e - p) : strlen(p);
        if (len == n && strncmp(p, id, n) == 0) return 1;
        p = e ? e + 1 : NULL;
    }
    return 0;
}

static void row_sub(const AtModsSrc *s, int m, char *out, int cap)
{
    char adds[2][AT_STR];
    int status = s->status(s->user, m), na = s->adds != NULL ? s->adds(s->user, m, adds, 1) : 0;
    const char *pack = s->pack(s->user, m), *st = s->status_text(s->user, m);
    snprintf(out, (size_t) cap, "%s", kind_word(s->kind(s->user, m)));
    if (pack != NULL && pack[0]) { size_t l = strlen(out); snprintf(out + l, (size_t) cap - l, " - %s", pack); }
    if (na > 0) { size_t l = strlen(out); snprintf(out + l, (size_t) cap - l, " - adds %s", adds[0]); }
    if (status == AT_MOD_CONFLICT) { size_t l = strlen(out); snprintf(out + l, (size_t) cap - l, " - CONFLICT"); }
    else if (status == AT_MOD_MISSING_DEP && st != NULL && st[0]) { size_t l = strlen(out); snprintf(out + l, (size_t) cap - l, " - %s", st); }
    else if (s->enabled(s->user, m) != s->active(s->user, m)) { size_t l = strlen(out); snprintf(out + l, (size_t) cap - l, " - RESTART"); }
}

int at_mods_build(const AtModsSrc *s, AtModsState *st, AtScreen *sc, AtView *vw, double now_ms)
{
    int i, t = st->tab, n = s->count(s->user), cur, last;
    const char *key_a = "Turn on";
    memset(sc, 0, sizeof *sc);
    memset(vw->key_label, 0, sizeof vw->key_label);
    memset(vw->key_shown, 0, sizeof vw->key_shown);
    memset(&vw->ex, 0, sizeof vw->ex);
    if (n > AT_MODS_MAX) n = AT_MODS_MAX;
    st->n[0] = st->n[1] = 0;
    for (i = 0; i < n; i++) {
        int stt = s->status(s->user, i);
        st->list[0][st->n[0]++] = i;
        if (stt == AT_MOD_CONFLICT || stt == AT_MOD_MISSING_DEP) st->list[1][st->n[1]++] = i;
    }
    for (i = 0; i < 2; i++) {
        if (st->sel[i] >= st->n[i]) st->sel[i] = st->n[i] - 1;
        if (st->sel[i] < 0) st->sel[i] = 0;
    }
    cur = st->sel[t];
    st->top[t] = at_list_scroll(cur, st->top[t], AT_MODS_VISIBLE, st->n[t] > 0 ? st->n[t] : 1);
    st->base = st->top[t] - 12;                                       /* the window: the visible rows and room either side */
    if (st->base > st->n[t] - AT_MODS_WINDOW) st->base = st->n[t] - AT_MODS_WINDOW;
    if (st->base < 0) st->base = 0;
    snprintf(sc->id, sizeof sc->id, "%s", "mods.list");
    snprintf(sc->title, sizeof sc->title, "%s", "MODS");
    sc->chapter = 4;                                                  /* IV Mods */
    sc->primary = AT_PRIMARY_LIST;
    sc->preset = AT_PRESET_WIDE;
    sc->input_feed = 1;                                               /* the model applies events itself (at_mods_event) */
    set_tabs(sc, vw, t, st->n[0], st->n[1]);
    if (st->n[t] == 0) {
        AtItem *it = &sc->items[sc->n_items++];
        memset(it, 0, sizeof *it);
        snprintf(it->id, sizeof it->id, "%s", "none");
        snprintf(it->label, sizeof it->label, "%s", t == 0 ? "No mods installed" : "No conflicts");
        snprintf(it->sub, sizeof it->sub, "%s", t == 0 ? "Put a mod folder in the mods folder, then restart." : "Every mod that is on can start.");
        it->flags = AT_CELL_DISABLED;
        vw->focus.block = 0; vw->focus.index = 0; vw->scroll = 0;
        snprintf(vw->counter, sizeof vw->counter, "%s", "0 / 0");
        put_key(sc, vw, 'B', "Back");
    } else {
        last = st->base + AT_MODS_WINDOW;
        if (last > st->n[t]) last = st->n[t];
        for (i = st->base; i < last; i++) {
            int m = st->list[t][i];
            AtItem *it = &sc->items[sc->n_items++];
            memset(it, 0, sizeof *it);
            snprintf(it->id, sizeof it->id, "m%d", m);
            snprintf(it->label, sizeof it->label, "%s", s->name(s->user, m));
            row_sub(s, m, it->sub, (int) sizeof it->sub);
            it->vkind = AT_VAL_TOGGLE;
            it->on = s->enabled(s->user, m) != 0;
            if (s->active(s->user, m)) it->flags |= AT_CELL_SELECTED;
        }
        vw->focus.block = 0;
        vw->focus.index = cur - st->base;
        vw->scroll = st->top[t] - st->base;
        snprintf(vw->counter, sizeof vw->counter, "%d / %d", cur + 1, st->n[t]);
        {
            int m = st->list[t][cur], status = s->status(s->user, m);
            const char *d = s->desc(s->user, m), *stx = s->status_text(s->user, m);
            key_a = s->enabled(s->user, m) ? "Turn off" : "Turn on";
            vw->ex.has = 1;
            snprintf(vw->ex.kicker, sizeof vw->ex.kicker, "%s", status == AT_MOD_CONFLICT ? "CONFLICT" : status == AT_MOD_MISSING_DEP ? "NEEDS A MOD" : kind_word(s->kind(s->user, m)));
            snprintf(vw->ex.title, sizeof vw->ex.title, "%s", s->name(s->user, m));
            snprintf(vw->ex.what, sizeof vw->ex.what, "%s", (status == AT_MOD_CONFLICT || status == AT_MOD_MISSING_DEP) && stx != NULL && stx[0] ? stx : d);
            snprintf(vw->ex.from_text, sizeof vw->ex.from_text, "%s %s", s->id(s->user, m), s->version(s->user, m)[0] ? s->version(s->user, m) : "");
        }
        put_key(sc, vw, 'A', key_a);
        put_key(sc, vw, 'B', "Back");
        put_key(sc, vw, 'Y', "Details");
        if (t == 1 || s->status(s->user, st->list[t][cur]) == AT_MOD_CONFLICT || s->status(s->user, st->list[t][cur]) == AT_MOD_MISSING_DEP) put_key(sc, vw, 'X', "Resolve");
    }
    /* the corner note: the last result while it lasts, else the standing restart note */
    if (now_ms < st->note_until && st->note[0]) {
        snprintf(vw->note.text, sizeof vw->note.text, "%s", st->note);
        vw->note.kind = st->note_kind;
        vw->note.from_ms = st->note_until - 3000.0;
        vw->note.until_ms = st->note_until;
    } else if (s->restart_needed(s->user)) {
        snprintf(vw->note.text, sizeof vw->note.text, "%s", "Applies at restart");
        vw->note.kind = AT_NOTE_INFO;
        vw->note.from_ms = now_ms;
        vw->note.until_ms = now_ms + 1000.0;
    } else {
        vw->note.text[0] = '\0';
    }
    return 1;
}

/* the mods that changed state between two snapshots, other than `except`, as "A, B and 2 more" */
static void changed_names(const AtModsSrc *s, const unsigned char *before, int n, int except, char *out, int cap)
{
    int i, k = 0, total = 0;
    out[0] = '\0';
    for (i = 0; i < n; i++) {
        if (i == except || (before[i] != 0) == (s->enabled(s->user, i) != 0)) continue;
        total++;
        if (k < 2) {
            size_t l = strlen(out);
            snprintf(out + l, (size_t) cap - l, "%s%s", k ? ", " : "", s->name(s->user, i));
            k++;
        }
    }
    if (total > 2) { size_t l = strlen(out); snprintf(out + l, (size_t) cap - l, " and %d more", total - 2); }
}

static void say(AtModsState *st, const char *text, int kind, double now_ms)
{
    snprintf(st->note, sizeof st->note, "%s", text);
    st->note_kind = kind;
    st->note_until = now_ms + 3000.0;
}

/* turn mod m on or off, save, and say what else moved */
static void toggle(const AtModsSrc *s, AtModsState *st, int m, int on, double now_ms)
{
    unsigned char before[AT_MODS_MAX];
    char others[AT_STR], text[AT_STR];
    int n = s->count(s->user), i, changed, saved;
    if (n > AT_MODS_MAX) n = AT_MODS_MAX;
    for (i = 0; i < n; i++) before[i] = (unsigned char) (s->enabled(s->user, i) != 0);
    changed = s->set_enabled(s->user, m, on);
    saved = changed > 0 ? s->save(s->user) : 0;
    if (changed <= 0) { say(st, "Nothing changed.", AT_NOTE_INFO, now_ms); return; }
    if (saved != 0) { say(st, "Could not save mods/enabled.txt. The change is not kept.", AT_NOTE_ERR, now_ms); return; }
    changed_names(s, before, n, m, others, (int) sizeof others);
    if (others[0]) {
        /* a cascade turns mods on (requirements) or off (dependents, conflicting mods): say which, from the first other mod that moved */
        int turned_on = 0;
        for (i = 0; i < n; i++) if (i != m && (before[i] != 0) != (s->enabled(s->user, i) != 0)) { turned_on = s->enabled(s->user, i) != 0; break; }
        snprintf(text, sizeof text, "Also turned %s: %s.", turned_on ? "on" : "off", others);
    } else {
        snprintf(text, sizeof text, "%s %s. Applies at restart.", s->name(s->user, m), on ? "on" : "off");
    }
    say(st, text, AT_NOTE_OK, now_ms);
}

/* A mod that needs a mod that is not mounting. Turn on every requirement that is in the folder and off; name the first one that is not
 * installed. (The resolver's own SetEnabled on a mod that is already on may report nothing, so each requirement is turned on itself.) */
static void resolve_missing(const AtModsSrc *s, AtModsState *st, int m, double now_ms)
{
    char need[AT_STR], gone[AT_STR], text[AT_STR + 40];
    const char *p;
    int n = s->count(s->user), turned = 0;
    gone[0] = '\0';
    snprintf(need, sizeof need, "%s", s->requires(s->user, m));
    for (p = need; p != NULL && *p; ) {
        char id[AT_STR];
        const char *e = strchr(p, ',');
        size_t len = e ? (size_t) (e - p) : strlen(p);
        int j, found = -1;
        if (len >= sizeof id) len = sizeof id - 1;
        memcpy(id, p, len);
        id[len] = '\0';
        for (j = 0; j < n && found < 0; j++) if (strcmp(s->id(s->user, j), id) == 0) found = j;
        if (found < 0) { if (!gone[0]) snprintf(gone, sizeof gone, "%s", id); }
        else if (!s->enabled(s->user, found)) { toggle(s, st, found, 1, now_ms); turned++; }
        p = e ? e + 1 : NULL;
    }
    if (turned == 0) {
        if (gone[0]) snprintf(text, sizeof text, "Nothing to turn on: %s is not installed.", gone);
        else snprintf(text, sizeof text, "%s", "Nothing to turn on: restart to apply.");
        say(st, text, AT_NOTE_ERR, now_ms);
    }
}

void at_mods_event(const AtModsSrc *s, AtModsState *st, const AtEvent *e, double now_ms, AtModsAction *act)
{
    int t = st->tab, n = st->n[t], m;
    memset(act, 0, sizeof *act);
    act->kind = AT_MA_NONE;
    if (e->type == AT_EV_PAGE) { st->tab = 1 - t; return; }                /* two tabs: L, R, Tab and Shift+Tab all switch */
    if (e->type == AT_EV_BACK) { act->kind = AT_MA_BACK; return; }
    if (n == 0) return;
    m = st->list[t][st->sel[t]];
    if (e->type == AT_EV_MOVE) {
        if (e->a == AT_DIR_UP) st->sel[t] = (st->sel[t] + n - 1) % n;
        else if (e->a == AT_DIR_DOWN) st->sel[t] = (st->sel[t] + 1) % n;
        else toggle(s, st, m, !s->enabled(s->user, m), now_ms);          /* left and right flip a toggle, as on A */
    } else if (e->type == AT_EV_SCROLL) {
        int v = st->sel[t] + (e->a > 0 ? 1 : -1);
        st->sel[t] = v < 0 ? 0 : v >= n ? n - 1 : v;
    } else if (e->type == AT_EV_FOCUS) {
        int v = st->base + e->b;                                         /* the event names a row of the WINDOW */
        if (v >= 0 && v < n) st->sel[t] = v;
    } else if (e->type == AT_EV_ACCEPT) {
        toggle(s, st, m, !s->enabled(s->user, m), now_ms);
    } else if (e->type == AT_EV_ALT && e->a == 'Y') {
        act->kind = AT_MA_DETAIL; act->arg = m;
    } else if (e->type == AT_EV_ALT && e->a == 'X') {
        int status = s->status(s->user, m);
        if (status == AT_MOD_CONFLICT) {
            toggle(s, st, m, 0, now_ms);
        } else if (status == AT_MOD_MISSING_DEP) {
            resolve_missing(s, st, m, now_ms);
        }
    }
}
```

Three behaviours the tests rely on: the cascade note says "on" or "off" from the first other mod that moved (a requirement turns on, a dependent turns off); a missing dependency that is not in the folder produces `Nothing to turn on: missing-base is not installed.`; and one that is in the folder but off is turned on by name, so the fix does not depend on how the resolver treats a mod that is already enabled.
- [ ] **Step 5: Run.** `nt atlas-mods`. Expected: `atlas mods: N checks, 0 failed` (about 2,400, mostly the 256-mod walk). Failures to expect and how to read them: `RECONCILE` field names for the tab record (fix `set_tabs` and the test's `SC.n_tabs` lines to step 5's real names, never the model's behaviour); the `conflicts` test's second `build` expects the tab to shrink only after a restart, because statuses are boot facts: if you "improve" the model to hide a resolved conflict at once, the real screen would lie about what is mounted.
- [ ] **Step 6: Commit.** Game repo: `pc/platform/gw_ui_mods.h/.c`, `pc/tests/atlas_mods_test.c`, message `atlas mods: the MODS screen as a pure model (rows, tabs, windowing, toggles with cascade notes, conflicts)`. Workspace repo: `tools/port/native_test.sh`, message `tools: atlas-mods native test`.

---

### Task 2: The mod detail screen and per-mod settings

Y on a mod opens its **detail**: what it requires, what it conflicts with (its own list **and** the mods that list it, since a conflict entry works in either direction), every entry it adds to the menus, and, when the mod registered one, a door into **its own settings screen**. Spec 14 rules out auto-generated settings pages: a mod's settings are a screen it registers (`gd.ui.screen`) and an entry in its `mod.json` whose parent is the new built-in `mods.self`, which the registry rewrites to `mods.<mod id>`. This screen only lists that entry and hands off; the mod owns the screen and its input, as every mod screen does.

**Files:**
- Modify (game repo): `pc/platform/gw_ui_mods.h`, `pc/platform/gw_ui_mods.c`, `pc/tests/atlas_mods_test.c`

**Interfaces:**
Consumes: the `AtModsSrc` of Task 1 (`requires`, `conflicts`, `adds`, `settings`).
Produces: `AtModsDetail { int mod, sel; }`, `at_mods_detail_build(src, detail, screen, view, now_ms)` and `at_mods_detail_event(src, detail, event, action)` (returns `AT_MA_BACK`, or `AT_MA_SETTINGS` with the entry id in `action.id`).

- [ ] **Step 1: Add the failing tests** to `pc/tests/atlas_mods_test.c` (before `main`; call `detail();` from `main` after `actions();`):

```c
static AtModsDetail DT;
static void dopen(const AtModsSrc *s, int mod) { memset(&DT, 0, sizeof DT); DT.mod = mod; CHECK(at_mods_detail_build(s, &DT, &SC, &VW, 1000.0) == 1); }
static AtModsAction dpress(const AtModsSrc *s, AtEvent e) { AtModsAction a; at_mods_detail_event(s, &DT, &e, &a); at_mods_detail_build(s, &DT, &SC, &VW, 1000.0); return a; }
static const char *sub_of(const char *label) { int i; for (i = 0; i < SC.n_items; i++) if (strcmp(SC.items[i].label, label) == 0) return SC.items[i].sub; return NULL; }

static void detail(void)
{
    AtModsSrc s = src();
    AtModsAction a;
    int i;
    fixture(); memset(&VW, 0, sizeof VW);
    /* a mod with an entry and its own settings screen */
    dopen(&s, 2);
    CHECK(strcmp(SC.id, "mods.detail") == 0 && strcmp(SC.title, "SUPERTIME ENVOY") == 0);
    CHECK(sub_of("Requires") != NULL && strcmp(sub_of("Requires"), "Nothing") == 0);
    CHECK(sub_of("Conflicts") != NULL && strcmp(sub_of("Conflicts"), "Nothing") == 0);
    CHECK(sub_of("Adds to the menus") != NULL && strcmp(sub_of("Adds to the menus"), "Solo > Envoy") == 0);
    CHECK(sub_of("Supertime Envoy settings") != NULL);                                          /* the mod's own settings entry */
    CHECK(VW.ex.has && strstr(VW.ex.what, "A mod.") != NULL);
    for (i = 0; i < SC.n_items; i++) CHECK(SC.items[i].vkind == AT_VAL_NONE);                   /* read-only rows: nothing to flip here */
    /* A on a plain row does nothing; A on the settings row hands off to the entry */
    a = dpress(&s, ev(AT_EV_ACCEPT, 0, 0)); CHECK(a.kind == AT_MA_NONE);
    for (i = 0; i < SC.n_items; i++) if (strstr(SC.items[i].label, "settings") != NULL) DT.sel = i;
    a = dpress(&s, ev(AT_EV_ACCEPT, 0, 0));
    CHECK(a.kind == AT_MA_SETTINGS && strcmp(a.id, "envoy.settings") == 0);
    a = dpress(&s, ev(AT_EV_BACK, 0, 0)); CHECK(a.kind == AT_MA_BACK);
    /* a conflict is listed from both sides, by name */
    dopen(&s, 3);
    CHECK(strstr(sub_of("Conflicts"), "Envoy Drives SA2") != NULL);
    dopen(&s, 4);
    CHECK(strcmp(sub_of("Conflicts"), "Envoy Drives") == 0);                               /* its own list names the other pack; the reverse scan finds the same one once */
    /* requirements by name where the mod is known, by id where it is not */
    dopen(&s, 6);
    CHECK(strstr(sub_of("Requires"), "missing-base") != NULL);
    dopen(&s, 1);
    CHECK(strstr(sub_of("Requires"), "ACE Base") != NULL);
    /* nothing to add, no settings entry: only the plain rows, and A and B are safe */
    dopen(&s, 7);
    CHECK(sub_of("Adds to the menus") == NULL && SC.n_items >= 3);
    a = dpress(&s, ev(AT_EV_ACCEPT, 0, 0)); CHECK(a.kind == AT_MA_NONE);
    a = dpress(&s, ev(AT_EV_MOVE, AT_DIR_DOWN, 0)); a = dpress(&s, ev(AT_EV_MOVE, AT_DIR_UP, 0)); CHECK(a.kind == AT_MA_NONE);
    /* the six-entry cap: six adds fit the record with everything else */
    fixture(); FM[2].nadds = 3; snprintf(FM[2].adds[1], 64, "%s", "Versus > Envoy Online"); snprintf(FM[2].adds[2], 64, "%s", "Online > Envoy Room");
    dopen(&s, 2); CHECK(SC.n_items <= AT_MAX_ITEMS);
    /* a long list and long names are cut by the fit rule inside their rows */
    fixture(); memset(FM[3].con, 'c', 63); FM[3].con[63] = '\0';
    dopen(&s, 3);
    {
        static AtHits hits; AtRenderInfo info; AtSink sk = rec_sink();
        at_render_ex(&SC, &VW, 640.0f, 1000.0, 0, &FAKE, &sk, &hits, &info);
        CHECK(info.entries < 1500 && !info.capped && hits.n >= 3);
    }
}
```

- [ ] **Step 2: Run to verify it fails.** `nt atlas-mods`. Expected: link errors for the new functions.
- [ ] **Step 3: Implement.** Append to `pc/platform/gw_ui_mods.h` (before `#ifdef __cplusplus` closes):

```c
/* the detail of one mod (Y on the list) */
typedef struct { int mod, sel; } AtModsDetail;
int at_mods_detail_build(const AtModsSrc *s, const AtModsDetail *d, AtScreen *sc, AtView *vw, double now_ms);
void at_mods_detail_event(const AtModsSrc *s, AtModsDetail *d, const AtEvent *e, AtModsAction *act);
```

Append to `pc/platform/gw_ui_mods.c`:

```c
/* ---- the detail screen ---- */
#include <ctype.h>

static void name_list(const AtModsSrc *s, const char *ids, char *out, int cap)
{
    const char *p = ids;
    int n = s->count(s->user);
    out[0] = '\0';
    while (p != NULL && *p) {
        char id[AT_STR];
        const char *e = strchr(p, ',');
        size_t len = e ? (size_t) (e - p) : strlen(p);
        int j, found = -1;
        size_t l = strlen(out);
        if (len >= sizeof id) len = sizeof id - 1;
        memcpy(id, p, len);
        id[len] = '\0';
        for (j = 0; j < n && found < 0; j++) if (strcmp(s->id(s->user, j), id) == 0) found = j;
        snprintf(out + l, (size_t) cap - l, "%s%s", l ? ", " : "", found >= 0 ? s->name(s->user, found) : id);
        p = e ? e + 1 : NULL;
    }
}

static void add_row(AtScreen *sc, const char *label, const char *sub)
{
    AtItem *it;
    if (sc->n_items >= AT_MAX_ITEMS) return;
    it = &sc->items[sc->n_items++];
    memset(it, 0, sizeof *it);
    snprintf(it->id, sizeof it->id, "d%d", sc->n_items);
    snprintf(it->label, sizeof it->label, "%s", label);
    snprintf(it->sub, sizeof it->sub, "%s", sub);
}

int at_mods_detail_build(const AtModsSrc *s, const AtModsDetail *d, AtScreen *sc, AtView *vw, double now_ms)
{
    int m = d->mod, n = s->count(s->user), j, na, i;
    char buf[AT_STR], mine[AT_STR], title[AT_STR], sid[AT_ID * 2], slabel[AT_STR], adds[6][AT_STR];
    const char *name, *others;
    (void) now_ms;
    memset(sc, 0, sizeof *sc);
    memset(vw->key_label, 0, sizeof vw->key_label);
    memset(vw->key_shown, 0, sizeof vw->key_shown);
    memset(&vw->ex, 0, sizeof vw->ex);
    vw->counter[0] = '\0';
    if (m < 0 || m >= n) return 0;
    name = s->name(s->user, m);
    for (i = 0; name[i] && i < AT_STR - 1; i++) title[i] = (char) toupper((unsigned char) name[i]);
    title[i] = '\0';
    snprintf(sc->id, sizeof sc->id, "%s", "mods.detail");
    snprintf(sc->title, sizeof sc->title, "%s", title);
    snprintf(sc->parent[0], sizeof sc->parent[0], "%s", "MODS");
    sc->n_parents = 1;
    sc->chapter = 4;
    sc->primary = AT_PRIMARY_LIST;
    sc->preset = AT_PRESET_WIDE;
    sc->input_feed = 1;
    snprintf(buf, sizeof buf, "%s%s%s", s->kind(s->user, m), s->pack(s->user, m)[0] ? " - " : "", s->pack(s->user, m));
    add_row(sc, "Folder", s->id(s->user, m));
    name_list(s, s->requires(s->user, m), mine, (int) sizeof mine);
    add_row(sc, "Requires", mine[0] ? mine : "Nothing");
    /* conflicts: this mod's own list, then every mod whose list names this one */
    name_list(s, s->conflicts(s->user, m), mine, (int) sizeof mine);
    for (j = 0; j < n; j++) {
        size_t l = strlen(mine);
        if (j == m) continue;
        others = s->conflicts(s->user, j);
        if (others != NULL && word_in(others, s->id(s->user, m)) && strstr(mine, s->name(s->user, j)) == NULL)
            snprintf(mine + l, sizeof mine - l, "%s%s", l ? ", " : "", s->name(s->user, j));
    }
    add_row(sc, "Conflicts", mine[0] ? mine : "Nothing");
    na = s->adds != NULL ? s->adds(s->user, m, adds, 6) : 0;
    for (i = 0; i < na; i++) add_row(sc, i == 0 ? "Adds to the menus" : "Also adds", adds[i]);
    if (s->settings != NULL && s->settings(s->user, m, sid, (int) sizeof sid, slabel, (int) sizeof slabel))
        add_row(sc, slabel, "Opens the mod's own settings screen.");
    vw->focus.block = 0;
    vw->focus.index = d->sel < sc->n_items ? d->sel : 0;
    vw->scroll = 0;
    vw->ex.has = 1;
    snprintf(vw->ex.kicker, sizeof vw->ex.kicker, "%s", buf);
    snprintf(vw->ex.title, sizeof vw->ex.title, "%s", name);
    snprintf(vw->ex.what, sizeof vw->ex.what, "%s", s->desc(s->user, m)[0] ? s->desc(s->user, m) : "No description.");
    snprintf(vw->ex.from_text, sizeof vw->ex.from_text, "%s", s->id(s->user, m));
    put_key(sc, vw, 'A', "Open");
    put_key(sc, vw, 'B', "Back");
    return 1;
}

void at_mods_detail_event(const AtModsSrc *s, AtModsDetail *d, const AtEvent *e, AtModsAction *act)
{
    AtScreen sc;
    AtView vw;
    char sid[AT_ID * 2], slabel[AT_STR];
    memset(act, 0, sizeof *act);
    memset(&vw, 0, sizeof vw);
    if (!at_mods_detail_build(s, d, &sc, &vw, 0.0)) { act->kind = AT_MA_BACK; return; }
    if (e->type == AT_EV_BACK) { act->kind = AT_MA_BACK; return; }
    if (e->type == AT_EV_MOVE && e->a == AT_DIR_UP) d->sel = (d->sel + sc.n_items - 1) % sc.n_items;
    else if (e->type == AT_EV_MOVE && e->a == AT_DIR_DOWN) d->sel = (d->sel + 1) % sc.n_items;
    else if (e->type == AT_EV_FOCUS && e->b >= 0 && e->b < sc.n_items) d->sel = e->b;
    else if (e->type == AT_EV_ACCEPT && d->sel >= 0 && d->sel < sc.n_items && s->settings != NULL &&
             strstr(sc.items[d->sel].label, "settings") != NULL &&
             s->settings(s->user, d->mod, sid, (int) sizeof sid, slabel, (int) sizeof slabel)) {
        act->kind = AT_MA_SETTINGS;
        snprintf(act->id, sizeof act->id, "%s", sid);
    }
}
```

The settings row is recognised by its label ending in `settings`, which is how the real accessor labels it (`"<name> settings"`); a mod whose own name contains the word does not matter, because `settings()` must also say yes for that mod.
- [ ] **Step 4: Run.** `nt atlas-mods`. Expected: `0 failed`.
- [ ] **Step 5: Commit.** Game repo: the three files, message `atlas mods: the detail screen (requirements, conflicts both ways, adds, a door to the mod's own settings)`.

---

### Task 3: The real accessors, `gw_Mods_Conflicts`, and the door

**Gate:** Task 0 exits 0 (N1 and N2). The six `gw_ui_native_*` calls are the same ones step 6 assumes; add `gw_ui_native_pad(unsigned *buttons, int *sx, int *sy)` to that list. Each is `RECONCILE` against step 2.

**Files:**
- Modify (game repo): `pc/platform/gw_mods.c`, `pc/platform/gw_mods.h`
- Create (game repo): `pc/platform/gw_ui_mods_native.h`, `pc/platform/gw_ui_mods_native.c`, `pc/tests/atlas_mods_door_test.c`, `pc/tests/fixtures/mods-atlas/*/mod.json`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-mods-door`)

- [ ] **Step 1: The conflicts accessor.** In `gw_mods.h`, next to `gw_Mods_Requires`: `const char *gw_Mods_Conflicts(int i);   /* comma-separated ids this mod lists as conflicts (its own list; a conflict also works from the other side), "" when none */`. In `gw_mods.c`, after `gw_Mods_Requires`:

```c
const char *gw_Mods_Conflicts(int i) {
    static char ring[4][GW_MODS_TEXT_MAX]; /* four calls stay valid at once: the screen asks a few rows at a time */
    static int next;
    gw_mod *m = mod_at(boot(), i);
    char *out = ring[next++ & 3];
    int j;
    size_t used = 0;
    out[0] = '\0';
    if (m == NULL) return out;
    for (j = 0; j < m->ncon; ++j) {
        int w = snprintf(out + used, GW_MODS_TEXT_MAX - used, "%s%s", j ? "," : "", m->con[j]);
        if (w < 0 || (size_t) w >= GW_MODS_TEXT_MAX - used) break;
        used += (size_t) w;
    }
    return out;
}
```

The real accessor is exercised against the real resolver in Step 7, through the fixture folder of Step 2.
- [ ] **Step 2: The fixture folder (no disc data, `mod.json` only).** Create `pc/tests/fixtures/mods-atlas/` with one folder per mod, each holding only a `mod.json`:

```
ace-base/mod.json         {"id":"ace-base","name":"ACE Base","version":"2.0","kind":"base","description":"The shared tables the ACE fighters need."}
ace-wolf/mod.json         {"id":"ace-wolf","name":"ACE Wolf","version":"2.0","kind":"fighter","pack":"ace","requires":["ace-base"],"description":"Wolf."}
envoy-a/mod.json          {"id":"envoy-a","name":"Envoy Drives","version":"1.0","kind":"misc","conflicts":["envoy-b"],"description":"Drive models."}
envoy-b/mod.json          {"id":"envoy-b","name":"Envoy Drives SA2","version":"1.0","kind":"misc","conflicts":["envoy-a"],"description":"The same drives."}
needs-ghost/mod.json      {"id":"needs-ghost","name":"Needs Ghost","version":"0.1","kind":"fighter","requires":["ghost-base"],"description":"Needs a mod that is not here."}
```

and a `enabled.txt` beside them listing `ace-base`, `ace-wolf`, `envoy-a`, `envoy-b`, `needs-ghost` (one id per line: the format `mods/enabled.txt` has today). With that set the resolver mounts `ace-base`, `ace-wolf`, `envoy-a`; `envoy-b` is `CONFLICT`; `needs-ghost` is `MISSING_DEP`. (The mods mount nothing: they have no `files/` folder.)
- [ ] **Step 3: Write the door's failing test.** Create `pc/tests/atlas_mods_door_test.c`. It stubs the native door and the pad, injects a **two-mod fake source** through `gw_Ui_ModsOpenWith`, and drives frames:

```c
#include "atlas_lint.h"
#include "../platform/gw_ui_mods_native.h"

static unsigned st_buttons; static int st_sx, st_sy;
static float st_mx = -1000.0f, st_my = -1000.0f; static int st_mb, st_wheel, st_attached;
static unsigned st_km; static double st_now = 1000.0;
void gw_ui_native_attach(const AtScreen *sc, AtView *vw, AtHits *hits) { (void) sc; (void) vw; (void) hits; st_attached++; }
void gw_ui_native_detach(const AtView *vw) { (void) vw; st_attached--; }
float gw_ui_native_canvas_w(void) { return 640.0f; }
double gw_ui_native_now_ms(void) { return st_now; }
void gw_ui_native_input(float *x, float *y, int *b, int *w, unsigned *k) { *x = st_mx; *y = st_my; *b = st_mb; *w = st_wheel; *k = st_km; }
void gw_ui_native_pad(unsigned *b, int *sx, int *sy) { *b = st_buttons; *sx = st_sx; *sy = st_sy; }
int gw_ui_native_enabled(void) { return 1; }

static int on[2] = { 1, 0 }, saves, settings_opened; static char opened[40];
static int c_count(void *u) { (void) u; return 2; }
static const char *c_id(void *u, int i) { (void) u; return i ? "b-mod" : "a-mod"; }
static const char *c_name(void *u, int i) { (void) u; return i ? "B Mod" : "A Mod"; }
static const char *c_empty(void *u, int i) { (void) u; (void) i; return ""; }
static int c_status(void *u, int i) { (void) u; return i ? AT_MOD_OFF : AT_MOD_ACTIVE; }
static int c_enabled(void *u, int i) { (void) u; return on[i]; }
static int c_active(void *u, int i) { (void) u; return !i; }
static int c_set(void *u, int i, int v) { (void) u; if (on[i] == v) return 0; on[i] = v; return 1; }
static int c_save(void *u) { (void) u; saves++; return 0; }
static int c_restart(void *u) { (void) u; return on[0] != 1 || on[1] != 0; }
static int c_adds(void *u, int i, char out[][AT_STR], int cap) { (void) u; (void) cap; if (i) return 0; snprintf(out[0], AT_STR, "Solo > A"); return 1; }
static int c_settings(void *u, int i, char *sid, int cap, char *lab, int lc) { (void) u; if (i) return 0; snprintf(sid, (size_t) cap, "a.settings"); snprintf(lab, (size_t) lc, "A Mod settings"); return 1; }
static AtModsSrc fake(void)
{
    AtModsSrc s; memset(&s, 0, sizeof s);
    s.count = c_count; s.id = c_id; s.name = c_name; s.version = c_empty; s.kind = c_empty; s.pack = c_empty; s.desc = c_empty;
    s.requires = c_empty; s.conflicts = c_empty; s.status = c_status; s.status_text = c_empty; s.enabled = c_enabled; s.active = c_active;
    s.set_enabled = c_set; s.save = c_save; s.restart_needed = c_restart; s.adds = c_adds; s.settings = c_settings;
    return s;
}

static void press_pad(unsigned b) { st_buttons = b; gw_Ui_ModsFrame(); st_buttons = 0; gw_Ui_ModsFrame(); }

int main(void)
{
    AtModsSrc s = fake();
    /* opening with A still held (the main menu's A brought us here) must not toggle the first mod */
    st_buttons = AT_PAD_A;
    gw_Ui_ModsOpenWith(&s);
    gw_Ui_ModsFrame(); gw_Ui_ModsFrame();
    CHECK(on[0] == 1 && saves == 0);
    st_buttons = 0; gw_Ui_ModsFrame();
    press_pad(AT_PAD_A);                                                       /* a fresh press toggles it */
    CHECK(on[0] == 0 && saves == 1);
    press_pad(AT_PAD_DOWN); press_pad(AT_PAD_A);                              /* down, A: the second mod */
    CHECK(on[1] == 1 && saves == 2);
    /* the keyboard and the mouse go the same way */
    st_km = AT_KEY_UP; gw_Ui_ModsFrame(); st_km = 0; gw_Ui_ModsFrame();
    st_km = AT_KEY_ENTER; gw_Ui_ModsFrame(); st_km = 0; gw_Ui_ModsFrame();
    CHECK(on[0] == 1);
    /* Y opens the detail, A on its settings row hands off, B comes back, B again leaves */
    press_pad(AT_PAD_Y);
    CHECK(gw_Ui_ModsMode() == 1);
    {
        int guard = 0;
        while (guard++ < 6 && settings_opened == 0) {
            press_pad(AT_PAD_DOWN);
            press_pad(AT_PAD_A);
            if (gw_Ui_ModsTakeSettings(opened, sizeof opened)) settings_opened = 1;
        }
    }
    CHECK(settings_opened == 1 && strcmp(opened, "a.settings") == 0);
    press_pad(AT_PAD_B); CHECK(gw_Ui_ModsMode() == 0);
    st_buttons = AT_PAD_B; CHECK(gw_Ui_ModsFrame() == AT_MA_BACK); st_buttons = 0; gw_Ui_ModsFrame();
    CHECK(gw_Ui_ModsClosedByBack() == 1);
    gw_Ui_ModsClose();
    CHECK(st_attached == 0);                                                  /* detached: nothing left drawing */
    gw_Ui_ModsClose();                                                         /* closing twice is harmless */
    CHECK(gw_Ui_ModsMode() == 0 && gw_Ui_ModsFrame() == 0);
    ATLAS_DONE("atlas mods door");
}
```

Register in `native_test.sh` (append `, atlas-mods-door`): `atlas-mods-door) sources=(pc/tests/atlas_mods_door_test.c pc/platform/gw_ui_mods_native.c pc/platform/gw_ui_mods.c pc/platform/gw_ui_render.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c) ;;` (plus the step 6 sources if merged), with `-DGW_UI_MODS_FAKE_ONLY` so the real accessor part of `gw_ui_mods_native.c` (which needs `gw_mods.c`) is left out of the test build.
- [ ] **Step 4: Run to verify it fails.** `nt atlas-mods-door`. Expected: `fatal error: '../platform/gw_ui_mods_native.h' file not found`.
- [ ] **Step 5: Write the door.** Create `pc/platform/gw_ui_mods_native.h`:

```c
/* gw_ui_mods_native.h - the MODS screen's door: pad, keyboard and mouse in, the model and its view out, drawn by the native
 * Atlas door. The real accessors read gw_Mods_* and the registry. */
#ifndef GW_UI_MODS_NATIVE_H
#define GW_UI_MODS_NATIVE_H
#include "gw_ui_mods.h"
#ifdef __cplusplus
extern "C" {
#endif
void gw_Ui_ModsOpen(void);                      /* the real source */
void gw_Ui_ModsOpenWith(const AtModsSrc *src);  /* tests */
int gw_Ui_ModsFrame(void);                      /* once a frame while open; returns AT_MA_BACK when the screen was left, else 0 */
void gw_Ui_ModsClose(void);
int gw_Ui_ModsMode(void);                       /* 0 the list, 1 a detail; -1 closed */
int gw_Ui_ModsTakeSettings(char *entry_id, int cap);   /* 1 once when the detail asked to open a mod's own settings; the caller activates it */
int gw_Ui_ModsClosedByBack(void);
/* RECONCILE (step 2): the native door */
extern void gw_ui_native_attach(const AtScreen *sc, AtView *vw, AtHits *hits);
extern void gw_ui_native_detach(const AtView *vw);
extern float gw_ui_native_canvas_w(void);
extern double gw_ui_native_now_ms(void);
extern void gw_ui_native_input(float *x, float *y, int *buttons, int *wheel, unsigned *key_mask);
extern void gw_ui_native_pad(unsigned *buttons, int *sx, int *sy);
extern int gw_ui_native_enabled(void);
#ifdef __cplusplus
}
#endif
#endif
```

Create `pc/platform/gw_ui_mods_native.c`:

```c
#include "gw_ui_mods_native.h"
#include <stdio.h>
#include <string.h>

static AtModsSrc g_src;
static AtModsState g_st;
static AtModsDetail g_dt;
static AtScreen g_sc;
static AtView g_vw;
static AtHits g_hits;
static AtPad g_pad;
static AtKeys g_keys;
static AtMouse g_mouse;
static int g_mode = -1, g_back, g_pending;
static char g_entry[AT_ID * 2];

void gw_Ui_ModsOpenWith(const AtModsSrc *src)
{
    unsigned b; int sx, sy;
    if (!gw_ui_native_enabled()) return;
    if (g_mode >= 0) gw_Ui_ModsClose();
    g_src = *src;
    at_mods_state_init(&g_st);
    memset(&g_dt, 0, sizeof g_dt);
    at_view_init(&g_vw);
    g_vw.opened_ms = gw_ui_native_now_ms();
    memset(&g_hits, 0, sizeof g_hits); memset(&g_mouse, 0, sizeof g_mouse); memset(&g_keys, 0, sizeof g_keys);
    gw_ui_native_pad(&b, &sx, &sy);
    memset(&g_pad, 0, sizeof g_pad);
    g_pad.prev = b;                        /* buttons held now do not fire: the A that opened this screen is still down */
    g_mode = 0; g_back = 0; g_pending = 0;
    gw_ui_native_attach(&g_sc, &g_vw, &g_hits);
    at_mods_build(&g_src, &g_st, &g_sc, &g_vw, gw_ui_native_now_ms());
}

static void rebuild(void)
{
    if (g_mode == 1) at_mods_detail_build(&g_src, &g_dt, &g_sc, &g_vw, gw_ui_native_now_ms());
    else at_mods_build(&g_src, &g_st, &g_sc, &g_vw, gw_ui_native_now_ms());
}

static void apply(const AtEvent *e)
{
    AtModsAction a;
    double now = gw_ui_native_now_ms();
    if (g_mode == 1) {
        at_mods_detail_event(&g_src, &g_dt, e, &a);
        if (a.kind == AT_MA_BACK) g_mode = 0;
        else if (a.kind == AT_MA_SETTINGS) { snprintf(g_entry, sizeof g_entry, "%s", a.id); g_pending = 1; }
    } else {
        at_mods_event(&g_src, &g_st, e, now, &a);
        if (a.kind == AT_MA_BACK) g_back = 1;
        else if (a.kind == AT_MA_DETAIL) { memset(&g_dt, 0, sizeof g_dt); g_dt.mod = a.arg; g_mode = 1; }
    }
    rebuild();
}

int gw_Ui_ModsFrame(void)
{
    float mx, my;
    int mb, wheel, sx, sy, n, i;
    unsigned km, pb;
    AtEvent ev[16];
    if (g_mode < 0) return 0;
    gw_ui_native_pad(&pb, &sx, &sy);
    n = at_pad_events(&g_pad, pb, sx, sy, gw_ui_native_now_ms(), ev, 16);
    for (i = 0; i < n && g_mode >= 0 && !g_back; i++) apply(&ev[i]);
    gw_ui_native_input(&mx, &my, &mb, &wheel, &km);
    n = at_key_events(&g_keys, km, gw_ui_native_now_ms(), ev, 16);
    for (i = 0; i < n && !g_back; i++) apply(&ev[i]);
    n = at_mouse_events(&g_mouse, mx, my, mb, wheel, &g_hits, ev, 16);
    for (i = 0; i < n && !g_back; i++) apply(&ev[i]);
    rebuild();
    return g_back ? AT_MA_BACK : 0;
}

void gw_Ui_ModsClose(void)
{
    if (g_mode >= 0) gw_ui_native_detach(&g_vw);
    g_mode = -1;
}

int gw_Ui_ModsMode(void) { return g_mode; }
int gw_Ui_ModsClosedByBack(void) { return g_back; }
int gw_Ui_ModsTakeSettings(char *entry_id, int cap)
{
    if (!g_pending) return 0;
    g_pending = 0;
    snprintf(entry_id, (size_t) cap, "%s", g_entry);
    return 1;
}

#ifndef GW_UI_MODS_FAKE_ONLY
/* ---- the real accessors: gw_Mods_* and the registry ---- */
#include "gw_mods.h"
/* RECONCILE (step 2): the registry. Assumed: at_registry_entries_of(mod_id, AtRegEntry *out, int cap) -> count, where an entry has
 * .id, .parent (already rewritten: "mods.self" is "mods.<mod id>"), .label; and at_registry_activate(entry_id). */
#include "gw_ui_registry.h"

static int r_count(void *u) { (void) u; return gw_Mods_Count(); }
#define R_STR(name, call) static const char *r_##name(void *u, int i) { (void) u; return call(i); }
R_STR(id, gw_Mods_Id) R_STR(name, gw_Mods_Name) R_STR(version, gw_Mods_Version) R_STR(kind, gw_Mods_Kind) R_STR(pack, gw_Mods_Pack)
R_STR(desc, gw_Mods_Description) R_STR(requires, gw_Mods_Requires) R_STR(conflicts, gw_Mods_Conflicts) R_STR(status_text, gw_Mods_StatusText)
static int r_status(void *u, int i)
{
    (void) u;
    switch (gw_Mods_Status(i)) {
    case GW_MOD_ACTIVE: return AT_MOD_ACTIVE;
    case GW_MOD_MISSING_DEP: return AT_MOD_MISSING_DEP;
    case GW_MOD_CONFLICT: return AT_MOD_CONFLICT;
    default: return AT_MOD_OFF;
    }
}
static int r_enabled(void *u, int i) { (void) u; return gw_Mods_IsEnabled(i); }
static int r_active(void *u, int i) { (void) u; return gw_Mods_IsActive(i); }
static int r_set(void *u, int i, int on) { (void) u; return gw_Mods_SetEnabled(i, on); }
static int r_save(void *u) { (void) u; return gw_Mods_Save(); }
static int r_restart(void *u) { (void) u; return gw_Mods_RestartNeeded(); }
static int r_adds(void *u, int i, char out[][AT_STR], int cap)
{
    AtRegEntry e[8];
    int n = at_registry_entries_of(gw_Mods_Id(i), e, 8), k, w = 0;
    (void) u;
    for (k = 0; k < n && w < cap; k++) {
        if (strncmp(e[k].parent, "mods.", 5) == 0) continue;              /* its own settings entry is not an addition to a menu */
        at_mods_add_line(e[k].parent, e[k].label, out[w++], AT_STR);
    }
    return w;
}
static int r_settings(void *u, int i, char *sid, int cap, char *label, int lcap)
{
    AtRegEntry e[8];
    int n = at_registry_entries_of(gw_Mods_Id(i), e, 8), k;
    (void) u;
    for (k = 0; k < n; k++) {
        if (strncmp(e[k].parent, "mods.", 5) != 0) continue;
        snprintf(sid, (size_t) cap, "%s", e[k].id);
        snprintf(label, (size_t) lcap, "%s settings", gw_Mods_Name(i));
        return 1;
    }
    return 0;
}

void gw_Ui_ModsOpen(void)
{
    AtModsSrc s;
    memset(&s, 0, sizeof s);
    s.count = r_count; s.id = r_id; s.name = r_name; s.version = r_version; s.kind = r_kind; s.pack = r_pack; s.desc = r_desc;
    s.requires = r_requires; s.conflicts = r_conflicts; s.status = r_status; s.status_text = r_status_text; s.enabled = r_enabled;
    s.active = r_active; s.set_enabled = r_set; s.save = r_save; s.restart_needed = r_restart; s.adds = r_adds; s.settings = r_settings;
    gw_Ui_ModsOpenWith(&s);
}
#endif
```

(The door has no netplay include and writes only through `gw_Mods_SetEnabled` and `gw_Mods_Save`. Opening a mod's own settings is the caller's job: it calls `at_registry_activate(entry_id)` after `gw_Ui_ModsTakeSettings`, so the mod's screen is pushed by the registry under the mod's ownership rules, never by this file.)
- [ ] **Step 6: Run.** `nt atlas-mods-door`, then `nt atlas-mods`. Expected: `0 failed` for both. The held-A check is the lesson from the binding's own docs ("a held A that opened it does not accept on it"); if it fails, the pad's `prev` was not seeded at open.
- [ ] **Step 7: The real accessors against the real resolver (in the exe, headless).** Add an in-engine test next to the other mods tests (`gw_mods.c`'s `gw_mods_tests_register` style, or `gw_ui_mods_native.c` under `#ifndef GW_UI_MODS_FAKE_ONLY`), named `mods_atlas_model`: with `MELEE_MODS_DIR` pointing at the fixture, build the model from `gw_Ui_ModsOpen`'s real source and assert: 5 mods; `envoy-b` is a `CONFLICT` row and appears in the CONFLICTS tab with `needs-ghost`; `ace-wolf`'s requirement shows `ACE Base`; toggling `ace-base` off through `at_mods_event` turns `ace-wolf` off (the real cascade) and writes `enabled.txt` into a **copy** of the fixture folder (copy it to the scratch folder first; never write into the repo). Run it with:

```bash
cd "$MAIN" && MELEE_MODS_DIR="<scratch copy of pc/tests/fixtures/mods-atlas>" tools/port/run.sh --test mods-atlas --iso "$GW_ISO_VANILLA"
```

How `run.sh --test` selects one test and whether it opens a window are **unverified**: read the quick reference first, and if it opens a window, run this only when the owner is away. Expected in the log: the test's PASS line and `gw: mods: <dir> - 5 mod(s)`.
- [ ] **Step 8: Commit.** Game repo: `gw_mods.c/.h`, the door files, the tests and the fixture, message `atlas mods: the real accessors (gw_Mods_Conflicts added), the door, a fixture folder`. Workspace repo: `tools/port/native_test.sh`, message `tools: atlas-mods-door native test`.

---

### Task 4: Open the Atlas MODS screen from the menus; retire the page behind the switch

**Gate:** Task 0 exits 0 and Task 3 is merged.

The legacy page caps the folder at **40 mods** (`FSM_MAX`, `gmfrontend_settings.inc`): a folder with more (an ACE split into one mod per fighter and stage is more) silently shows the first 40. The Atlas screen windows 256 (`GW_MODS_MAX`). Say so in the commit.

**Files:**
- Modify (game repo): `src/melee/gm/gmfrontend_menus.inc`, `src/melee/gm/gmfrontend_atlas.inc` (step 2's adapter: three lines), `src/melee/gm/gmfrontend_settings.inc` (nothing removed yet)

- [ ] **Step 1: The entry.** In `gmfrontend_menus.inc` (the `fm_settings` table, today `{ "MODS", "Turn mods on or off.", NULL, 0x45, FA_PAGE, 4 }`), make the row open the Atlas screen when Atlas is on and keep the legacy page when it is off:

```c
    { "MODS", "Turn mods on or off, see what each adds, resolve conflicts.", NULL, 0x45, FA_ATLAS, FA_ATLAS_MODS }, /* RECONCILE (step 2): its id for "mods.list" */
```

Step 2's top-level MODS entry on the main menu (spec 13.2: its destination is `Settings > Mods` until step 7) points at the same item, so there is one place to change. The legacy fallback is step 2's `MELEE_ATLAS=0` handling of `FA_ATLAS` (it falls back to the item's old `FA_PAGE` target): add `4` (the page) as that fallback.
- [ ] **Step 2: The dispatch.** In `gmfrontend_atlas.inc`, where step 2 dispatches an `FA_ATLAS` item to a host-native screen (RECONCILE: its function), add the mods case, three small pieces: open, per-frame, close.

```c
extern void Ui_ModsOpen(void);
extern int Ui_ModsFrame(void);
extern void Ui_ModsClose(void);
extern int Ui_ModsTakeSettings(char* entry_id, int cap);
extern void Ui_RegistryActivate(const char* entry_id); /* RECONCILE: step 2's shim for at_registry_activate */

/* on FA_ATLAS with the mods id: Ui_ModsOpen(); */
/* every frame while it is the open Atlas screen: */
static bool fa_mods_frame(void)
{
    char entry[48];
    int r = Ui_ModsFrame();
    if (Ui_ModsTakeSettings(entry, sizeof entry)) {
        Ui_RegistryActivate(entry); /* the registry opens the mod's screen under the mod's ownership, or runs its on_entry */
    }
    if (r != 0) {
        Ui_ModsClose();
        return true; /* B: leave through the same back the legacy page used (FE_DO_BACK to the menu that opened it) */
    }
    return false;
}
```

- [ ] **Step 3: Check without a window.**

```bash
cd "$GW_MELEE" && clang -fsyntax-only -w -DTARGET_PC --target=powerpc-unknown-eabi -nostdinc -Isrc -Isrc/melee -Iinclude -Ilibs/dolphin/include -Ipc -Ipc/gameworld -Isrc/sysdolphin -Isrc/MSL src/melee/gm/gmfrontend.c; echo "exit $?"
cd "$MAIN" && tools/port/build.sh
grep -a "mods.detail" "$GW_BUILD_ROOT/melee-pc.exe" | head -1
grep -a "Applies at restart" "$GW_BUILD_ROOT/melee-pc.exe" | head -1
```

Expected: `exit 0` (or the baseline you recorded), a linked exe, and both `grep -a` lines print. If the position table test from step 2 (`fe_menu_sweep.py`, [unverified: needs the disc?]) runs, it must still map `(MenuKind, 0x45)` to the same menu item as before.
- [ ] **Step 4: Commit.** Game repo, message `frontend: MODS opens the Atlas mods screen (the legacy page stays behind MELEE_ATLAS=0; it showed only the first 40 mods)`.

---

### Task 5: Engine additions the LAB needs (only what the gate says is missing)

Run `python tools/port/atlas_gate.py --step 7`. Every `SOFT` line it prints names a sub-step below; do those, skip the rest. **Sub-step 5g (the stub) comes first whichever others you do**: every test below that runs in Lua needs it. Each is test-first and small. **Every binding test in this task runs as a script, not as the developer console:** set `gs.cur = 1` (the stand-in's slot 1, mod id `envoy`) before registering, and put `gs.cur = -1` back after. Step 1's own second fix round found a handler result judged against the wrong script because the first tests ran as the console; a test that cannot fail for a script owner proves nothing about one.

**Files:**
- Modify (game repo): `pc/platform/gw_ui_screen.h/.c`, `gw_ui_parts.c`, `gw_ui_render.c`, `gw_script_ui.inc`, `pc/tests/atlas_screen_test.c`, `atlas_parts_test.c`, `atlas_render_test.c`, `atlas_binding_test.c`, `atlas_ui_stub.lua`, `atlas_ui_stub_test.lua`
- Modify (workspace repo): `menu/pipeline/atlas_tokens.py`, `menu/pipeline/test_atlas_tokens.py` (sub-step 5e only)

#### 5a. The `stepper` value (N6)

A row whose left and right change a value and whose A runs the row. Without it every LAB row that has both `adjust` and `run` loses one of them.

- [ ] **Step 1: Tests first.** In `atlas_screen_test.c`:

```c
    {   /* a stepper value converts, with its text */
        AtvArena a; AtScreen sc; char err[160]; int root, prim, items, it, val;
        atv_init(&a); root = atv_table(&a); atv_set(&a, root, "id", atv_str(&a, "t.one"));
        prim = atv_table(&a); atv_set(&a, prim, "kind", atv_str(&a, "list")); items = atv_table(&a);
        it = atv_table(&a); atv_set(&a, it, "id", atv_str(&a, "r1")); atv_set(&a, it, "label", atv_str(&a, "Row"));
        val = atv_table(&a); atv_set(&a, val, "kind", atv_str(&a, "stepper")); atv_set(&a, val, "text", atv_str(&a, "Stand"));
        atv_set(&a, it, "value", val); atv_push(&a, items, it); atv_set(&a, prim, "items", items); atv_set(&a, root, "primary", prim);
        CHECK(at_screen_from_val(&a, root, "t", &sc, err, sizeof err) == 1);
        CHECK(sc.items[0].vkind == AT_VAL_STEPPER && strcmp(sc.items[0].text, "Stand") == 0);
    }
```

In `atlas_parts_test.c` (a stepper draws exactly what a choice draws: the arrows and the text):

```c
    {
        AtRect r = { 32.0f, 100.0f, 300.0f, 34.0f };
        AtItem c = item("Mode", AT_VAL_CHOICE), st = item("Mode", AT_VAL_STEPPER);
        AtSink s; int np_choice, nt_choice;
        snprintf(c.text, sizeof c.text, "Stand"); snprintf(st.text, sizeof st.text, "Stand");
        s = rec_sink(); at_part_row(&s, &FAKE, r, &c, AT_ST_REST); np_choice = REC.np; nt_choice = REC.nt;
        s = rec_sink(); at_part_row(&s, &FAKE, r, &st, AT_ST_REST);
        CHECK(REC.np == np_choice && REC.nt == nt_choice && find_text("Stand") != NULL);
    }
```

In `atlas_binding_test.c`, next to the `on.change` checks (the same `LUA_IS` style), run **as a script**:

```c
    /* a stepper: left and right report their direction, A goes to on.accept and never to on.change */
    gs.cur = 1;
    LUA_IS("SQ={}; gd.ui.screen{id='envoy.step', primary={kind='list', items={{id='st',label='Focus',value={kind='stepper',text='P1'}},{id='tg',label='T',value={kind='toggle',on=false}}}}, "
           "on={change=function(id,v) SQ[#SQ+1]=id..'='..tostring(v) end, accept=function(c) SQ[#SQ+1]='accept '..c end}}; return gd.ui.open('envoy.step')", "true");
    LUA_IS("gd.ui.feed('envoy.step','right'); gd.ui.feed('envoy.step','left'); gd.ui.feed('envoy.step','accept'); return table.concat(SQ,',')", "st=1,st=-1,accept st");
    gs.cur = -1;
    LUA_IS("while gd.ui.state().top do gd.ui.close() end return 'clear'", "clear");
```

In `atlas_ui_stub_test.lua`, after the `ch=1,ch=-1,ch=1` check:

```lua
ui.screen(list1({ id = 'x.step', primary = { kind = 'list', items = { { id = 'st', label = 'S', value = { kind = 'stepper', text = 'a' } } } },
  on = { change = function(id, v) pl[#pl + 1] = id .. '=' .. tostring(v) end, accept = function(c) pl[#pl + 1] = 'accept ' .. c end } }))
ui.open('x.step'); pl = {}
ui.engine_row('x.step', 'right'); ui.engine_row('x.step', 'left'); ui.engine_press('x.step', 'accept')
check(table.concat(pl, ',') == 'st=1,st=-1,accept st', 'a stepper reports left and right, and A is an accept (got ' .. table.concat(pl, ',') .. ')')
```

- [ ] **Step 2: Run to verify they fail.** `nt atlas-screen`, `nt atlas-parts`, `nt atlas-binding`, `lua pc/tests/atlas_ui_stub_test.lua`. Expected: `AT_VAL_STEPPER` undeclared; the stub test fails on the unknown value kind.
- [ ] **Step 3: Implement.** `gw_ui_screen.h`: append `AT_VAL_STEPPER` at the end of the value enum (`enum { AT_VAL_NONE, AT_VAL_TOGGLE, AT_VAL_CHOICE, AT_VAL_SLIDER, AT_VAL_TEXT, AT_VAL_COUNTER, AT_VAL_STEPPER };`). `gw_ui_screen.c`, in the value-kind chain: `else if (strcmp(vk, "stepper") == 0) it->vkind = AT_VAL_STEPPER;` (the line after it reads `text` for every kind). `gw_ui_parts.c`, in `at_part_row`: `case AT_VAL_CHOICE: case AT_VAL_STEPPER: vw = part_choice(s, o, right, cy, it->text, focus); break;`. `gw_script_ui.inc`, in `gs_ui_value_event`: add `&& it->vkind != AT_VAL_STEPPER` to the kind test, and a branch after the choice one:

```c
    } else if (it->vkind == AT_VAL_STEPPER) {
        if (accept) return 0;                                     /* A runs the row (on.accept); only left and right change it */
        dir = left ? -1 : 1; val = dir;
    } else {
```

`atlas_ui_stub.lua`: the stepper's edits are in 5g.
- [ ] **Step 4: Run** the four commands again: `0 failed` / the stub's pass line.

#### 5b. A screen over the world (N5)

- [ ] **Step 1: Test first** in `atlas_render_test.c`:

```c
    {   /* backdrop = world: a translucent scrim instead of the opaque ground, ramping in on the UI clock; no end fade over the world */
        static AtScreen sc; static AtView vw; static AtHits hits; AtSink s;
        memset(&sc, 0, sizeof sc); memset(&vw, 0, sizeof vw);
        sc.primary = AT_PRIMARY_LIST; sc.preset = AT_PRESET_NONE; sc.n_items = 1; snprintf(sc.items[0].id, AT_ID, "a"); snprintf(sc.items[0].label, AT_STR, "A");
        sc.backdrop = AT_BD_WORLD; vw.opened_ms = 1000.0;
        s = rec_sink(); at_render(&sc, &vw, 640.0f, 1000.0, 0, &FAKE, &s, &hits);
        CHECK(REC.p[0].rgba == (AT_C_SCRIM & 0xFFFFFF00u));                       /* just opened: no scrim yet */
        s = rec_sink(); at_render(&sc, &vw, 640.0f, 1100.0, 0, &FAKE, &s, &hits);
        CHECK(REC.p[0].rgba == AT_C_SCRIM);                                       /* open: the full scrim, and never the ground */
        s = rec_sink(); at_render(&sc, &vw, 640.0f, 1000.0, 1, &FAKE, &s, &hits);
        CHECK(REC.p[0].rgba == AT_C_SCRIM);                                       /* Reduced Motion: a cut */
        sc.backdrop = AT_BD_GROUND; s = rec_sink(); at_render(&sc, &vw, 640.0f, 1100.0, 0, &FAKE, &s, &hits);
        CHECK(REC.p[0].rgba == AT_C_GROUND);                                      /* the default is unchanged */
    }
```

- [ ] **Step 2: Implement.** `gw_ui_screen.h`: `enum { AT_BD_GROUND, AT_BD_WORLD };` and `int backdrop;` in `AtScreen`. `gw_ui_screen.c`: `{ const char *b = atv_strv(a, atv_get(a, root, "backdrop"), "ground"); if (strcmp(b, "world") == 0) o->backdrop = AT_BD_WORLD; else if (strcmp(b, "ground") != 0) FAIL("gd.ui.screen: backdrop is \"ground\" or \"world\""); }`. `gw_ui_render.c`, replace the ground fill line in `at_render_ex` with:

```c
    if (sc->backdrop == AT_BD_WORLD) {
        AtTween wt;
        at_tween_start(&wt, v->opened_ms, 100.0, reduced);
        at_poly_rect(s, 0.0f, 0.0f, L.canvas.w, 480.0f, (AT_C_SCRIM & 0xFFFFFF00u) | (unsigned) ((float) (AT_C_SCRIM & 0xFFu) * at_tween_value(&wt, now) + 0.5f));
    } else {
        at_poly_rect(s, 0.0f, 0.0f, L.canvas.w, 480.0f, AT_C_GROUND);
    }
```

and guard the end fade: `if (sc->backdrop != AT_BD_WORLD && k > 0.004f) ...`. Stub: validate `d.backdrop` is nil, `'ground'` or `'world'` (a raise with the same message). Binding test (as a script): `gd.ui.screen{id='envoy.bd', backdrop='world', ...}` registers; `backdrop='sky'` raises `backdrop is`. Docs in Task 11.
- [ ] **Step 3: Run** `nt atlas-render`, `nt atlas-screen`, `nt atlas-binding`, the stub test: `0 failed`.

#### 5c. The explainer: WITH tags, and no empty media well (N7)

The LAB explainer has no model, so today's media well (96 px of an empty box) would waste a third of the pane; and its WITH is a short list of tags (the mode's keys), not models.

- [ ] **Step 1: Tests first** in `atlas_parts_test.c`:

```c
    {
        AtExplainer e; AtRect r = { 400.0f, 66.0f, 232.0f, 362.0f };
        AtSink s; int i;
        memset(&e, 0, sizeof e); e.media_model = e.media_ring = AT_NO_MODEL; e.has = 1;
        snprintf(e.kicker, sizeof e.kicker, "DUMMY"); snprintf(e.title, sizeof e.title, "BEHAVIOUR"); snprintf(e.what, sizeof e.what, "What the dummy does while you test.");
        snprintf(e.from_text, sizeof e.from_text, "Geno LAB");
        e.n_tags = 3; snprintf(e.with_tag[0], sizeof e.with_tag[0], "B Boxes"); snprintf(e.with_tag[1], sizeof e.with_tag[1], "L Labels"); snprintf(e.with_tag[2], sizeof e.with_tag[2], "D Data");
        s = rec_sink(); at_part_explainer(&s, &FAKE, r, &e);
        CHECK(find_text("WITH") != NULL && find_text("B Boxes") != NULL && find_text("D Data") != NULL && find_text("FROM") != NULL);
        CHECK(REC.nm == 0);
        for (i = 0; i < REC.nt; i++) CHECK(at_role_size(REC.t[i].role) >= 12);
        CHECK(lint_text_inside(r, 0) == 0);
        /* no media: the title starts at the top of the pane, not 106 px down */
        CHECK(find_text("DUMMY") != NULL && find_text("DUMMY")->base < r.y + 40.0f);
        /* with a model the well is still there and the title is below it (the bag is unchanged) */
        e.media_model = 3; s = rec_sink(); at_part_explainer(&s, &FAKE, r, &e);
        CHECK(REC.nm == 1 && find_text("DUMMY")->base > r.y + 106.0f);
        /* tags that do not fit are dropped, never overlapped */
        { AtRect small = { 400.0f, 66.0f, 232.0f, 200.0f }; e.media_model = AT_NO_MODEL; s = rec_sink(); at_part_explainer(&s, &FAKE, small, &e); CHECK(lint_text_inside(small, 0) == 0 && lint_text_overlaps() == 0); }
    }
```

(`atlas_parts_test.c` needs `#include "atlas_lint.h"`.) An existing parts test may assert the media well for a media-less explainer: that assertion described the old behaviour; update it with a comment.
- [ ] **Step 2: Implement.** `gw_ui_screen.h`, in `AtExplainer`: `int n_tags; char with_tag[AT_MAX_WITH][20];`. `gw_ui_screen.c`, in `at_explainer_from_val` after the `with` loop:

```c
    {
        int tags = atv_get(a, with, "tags"), nt = atv_len(a, tags), k;
        for (k = 0; k < nt && e->n_tags < AT_MAX_WITH; k++) {
            const char *tx = atv_strv(a, atv_at(a, tags, k + 1), "");
            if (tx[0]) snprintf(e->with_tag[e->n_tags++], sizeof e->with_tag[0], "%s", tx);
        }
    }
```

`gw_ui_parts.c`, in `at_part_explainer`, replace the media well block and the WITH block:

```c
    if (e->media_model != AT_NO_MODEL) {
        at_poly_rect(s, x, y, w, 96.0f, AT_C_GROUND2);                   /* the media well */
        s->model(s->user, e->media_model, e->media_ring, x + 8.0f, y + 4.0f, w - 16.0f, 88.0f, 1, 0);
        y += 106.0f;
    }
```

and for WITH:

```c
    if ((e->n_with > 0 || e->n_tags > 0) && y + 44.0f <= bottom) {
        float ty = y + 16.0f;
        at_text(s, o, AT_R_CAP12, "WITH", x, y + 11.0f, AT_C_DIM, AT_ALIGN_LEFT, 0.0f);
        for (i = 0; i < e->n_with; i++) {
            float cx = x + 26.0f * (float) i;
            at_poly_rect(s, cx, ty, 22.0f, 22.0f, AT_C_GROUND2);
            if (e->with_model[i] != AT_NO_MODEL) s->model(s->user, e->with_model[i], AT_NO_MODEL, cx + 1.0f, ty + 1.0f, 20.0f, 20.0f, 0, 0);
        }
        if (e->n_with > 0) ty += 26.0f;
        for (i = 0; i < e->n_tags && ty + 20.0f <= bottom - 44.0f; i++) {
            at_part_tag(s, o, x, ty, e->with_tag[i], AT_TAG_PLAIN, w);
            ty += 24.0f;
        }
        y = e->n_tags > 0 ? ty + 6.0f : y + 44.0f;
    }
```

(The `- 44.0f` keeps room for FROM.) Stub: `explainer.provide` results may carry `with = { tags = {...} }`; validate at most 4 tags, each a string.
- [ ] **Step 3: Run** `nt atlas-parts`, `nt atlas-render`, `nt atlas-screen`, the stub test, and the bag's own test (`lua pc/tests/envoy_atlas_bag.lua | tail -1`): `0 failed`.

#### 5d. Tabs from Lua (N10)

Step 5 puts tabs in the native record. A Lua screen needs the same: `tabs = { { name = "PLAY" }, ... }`, `tab = 3`, `on.tab(i)`. The engine moves the active tab on L, R, Tab, Shift+Tab (and a click on a tab, through step 5's tab hit rectangles: RECONCILE) and **tells the script**, which re-registers the content; it never decides what is on a tab.

- [ ] **Step 1: Tests first.** `atlas_screen_test.c` (the conversion, and the lifetime hole: a new Lua reference must be in the list the binding releases):

```c
    {
        AtvArena a; AtScreen sc; char err[160]; int root, prim, items, it, tabs, t1, t2, on;
        int refs[32], n, k, seen = 0;
        atv_init(&a); root = atv_table(&a); atv_set(&a, root, "id", atv_str(&a, "t.tabs"));
        prim = atv_table(&a); atv_set(&a, prim, "kind", atv_str(&a, "list")); items = atv_table(&a);
        it = atv_table(&a); atv_set(&a, it, "id", atv_str(&a, "r1")); atv_set(&a, it, "label", atv_str(&a, "Row")); atv_push(&a, items, it);
        atv_set(&a, prim, "items", items); atv_set(&a, root, "primary", prim);
        tabs = atv_table(&a); t1 = atv_table(&a); t2 = atv_table(&a);
        atv_set(&a, t1, "name", atv_str(&a, "PLAY")); atv_set(&a, t2, "name", atv_str(&a, "DISPLAY")); atv_set(&a, t2, "count", atv_num(&a, 4));
        atv_push(&a, tabs, t1); atv_push(&a, tabs, t2); atv_set(&a, root, "tabs", tabs); atv_set(&a, root, "tab", atv_num(&a, 2));
        on = atv_table(&a); atv_set(&a, on, "tab", atv_fn(&a, 41)); atv_set(&a, root, "on", on);
        CHECK(at_screen_from_val(&a, root, "t", &sc, err, sizeof err) == 1);
        CHECK(sc.n_tabs == 2 && strcmp(sc.tab_name[1], "DISPLAY") == 0 && sc.tab_count[1] == 4 && sc.tab_count[0] == -1 && sc.tab0 == 1);
        n = at_screen_fn_refs(&sc, refs, 32);
        for (k = 0; k < n; k++) seen += refs[k] == 41;
        CHECK(seen == 1);                                                      /* on.tab is released with the screen */
        atv_set(&a, root, "tabs", atv_table(&a));                              /* an empty tabs table is refused */
        CHECK(at_screen_from_val(&a, root, "t", &sc, err, sizeof err) == 0 && strstr(err, "tabs") != NULL);
    }
```

(RECONCILE: use step 5's field names for `n_tabs`, `tab_name`, `tab_count` and the view's active tab; `tab0` is this plan's: the tab the script asked for.) `atlas_binding_test.c`, as a script:

```c
    gs.cur = 1;
    LUA_IS("TB={}; gd.ui.screen{id='envoy.tabs', tabs={{name='ONE'},{name='TWO'},{name='THREE'}}, tab=2, primary={kind='list', items={{id='a',label='A'}}}, on={tab=function(i) TB[#TB+1]=i end}}; return gd.ui.open('envoy.tabs')", "true");
    LUA_IS("gd.ui.feed('envoy.tabs','r'); gd.ui.feed('envoy.tabs','r'); gd.ui.feed('envoy.tabs','l'); return table.concat(TB,',')", "3,1,3");
    LUA_HAS("return gd.ui.screen{id='envoy.t0', tabs={}, primary={kind='list', items={{id='a',label='A'}}}}", "tabs");
    LUA_HAS("local t={} for i=1,9 do t[i]={name='T'..i} end return gd.ui.screen{id='envoy.t9', tabs=t, primary={kind='list', items={{id='a',label='A'}}}}", "tabs");
    /* a screen without tabs: L and R still reach on.page, as before */
    LUA_IS("TB={}; gd.ui.screen{id='envoy.nt', primary={kind='list', items={{id='a',label='A'}}}, on={tab=function(i) TB[#TB+1]='tab' end, page=function(d) TB[#TB+1]='page'..d end}}; gd.ui.open('envoy.nt'); gd.ui.feed('envoy.nt','r'); return table.concat(TB,',')", "page1");
    gs.cur = -1;
    LUA_IS("while gd.ui.state().top do gd.ui.close() end return 'clear'", "clear");
```

`atlas_ui_stub_test.lua`: the stub registers `tabs`, rejects 0 or more than 8, calls `on.tab(i)` on L and R (wrapping) and `on.page` only when there are no tabs, and keeps `ui.tab(id)` readable.
- [ ] **Step 2: Implement.** `gw_ui_screen.h`: in `AtScreen` add `int fn_tab, tab0;` (the other tab fields are step 5's). `gw_ui_screen.c`: reset `o->fn_tab = -1;` with the other `-1`s (line with `o->fn_page = o->fn_start = -1`); read `o->fn_tab = get_fn(a, on, "tab");` after `fn_start`; convert `tabs` and `tab` (`AT_MAX_TABS` is step 5's cap, 8):

```c
    {
        int tabs = atv_get(a, root, "tabs"), nt, i;
        if (atv_kind(a, tabs) == ATV_TABLE) {
            nt = atv_len(a, tabs);
            if (nt < 1 || nt > AT_MAX_TABS) FAIL("gd.ui.screen: tabs is 1 to %d entries", AT_MAX_TABS);
            for (i = 0; i < nt; i++) {
                int tt = atv_at(a, tabs, i + 1);
                if (atv_kind(a, tt) != ATV_TABLE) FAIL("gd.ui.screen: tab %d is not a table", i + 1);
                get_str(a, tt, "name", o->tab_name[i], AT_ID, &o->warnings);
                o->tab_count[i] = get_int(a, tt, "count", -1);
            }
            o->n_tabs = nt;
            o->tab0 = get_int(a, root, "tab", 1) - 1;
            if (o->tab0 < 0) o->tab0 = 0;
            if (o->tab0 >= nt) o->tab0 = nt - 1;
        }
    }
```

and add `all[na++] = s->fn_tab;` to `at_screen_fn_refs` (the `all[16]` array has room: 14 entries). `gw_script_ui.inc`: in the reset at the top of `gs_ui_release` (the list ending `u->sc.fn_page = u->sc.fn_start = -1;`) add `= u->sc.fn_tab`; where a registered screen is installed (`l_ui_screen`, where focus is kept on replacement) set `u->view.tab = u->sc.tab0;`; and in `gs_ui_event`, at the top of the `AT_EV_PAGE` branch:

```c
        if (u->sc.n_tabs > 0) {                                        /* tabs: L, R, Tab and Shift+Tab move between them and tell the script */
            int nt = u->sc.n_tabs, t = (u->view.tab + (e->a < 0 ? -1 : 1) + nt) % nt;
            u->view.tab = t;
            u->explain_dirty = 1;
            if (u->sc.fn_tab >= 0 && gs_may_run(u->owner) && gs_ui_usable(u->owner)) {
                lua_State *L = gs.L;
                lua_rawgeti(L, LUA_REGISTRYINDEX, u->sc.fn_tab);
                if (lua_isfunction(L, -1)) {
                    lua_pushinteger(L, t + 1);
                    if (gs_pcall(u->owner, 1, 1, "ui") == 0) gs_ui_apply_result(owner);
                } else lua_pop(L, 1);
            }
            return;
        }
```

- [ ] **Step 3: Run** `nt atlas-screen`, `nt atlas-binding`, the stub test: `0 failed`.

#### 5e. `gd.ui.token(name)` (N8)

The LAB's remaining dev drawing must use Atlas colours, and the tokens must stay one source. The generator emits a name table and the binding reads it.

- [ ] **Step 1: Test first.** In `menu/pipeline/test_atlas_tokens.py` add to `Tokens`:

```python
    def test_names(self):
        n = T.names_text(self.tok)
        self.assertIn('{ "ember", 0xFF7A3DFFu },', n)
        self.assertIn('{ "scrim", 0x05070AB8u },', n)
        self.assertEqual(n.count("{ \""), len(self.tok["colours"]))
```

In `atlas_binding_test.c` (the colour of `ember` is `0xFF7A3DFF`, 4286201343 as a Lua integer), as a script:

```c
    gs.cur = 1;
    LUA_IS("return gd.ui.token('ember')", "4286201343");
    LUA_IS("return tostring(gd.ui.token('no-such-colour'))", "nil");
    LUA_HAS("return gd.ui.token(5, 6)", "");                                  /* a number is read as text: still a nil, not a crash */
    gs.cur = -1;
```

and in the stub test: `check(ui.token('ember') == 0xFF7A3DFF and ui.token('nope') == nil, 'the stub reads the tokens file')`.
- [ ] **Step 2: Implement.** `atlas_tokens.py`: add

```python
def names_text(tok):
    out = ["/* generated by menu/pipeline/atlas_tokens.py: do not edit */"]
    for name, v in sorted(tok["colours"].items()):
        out.append('{ "%s", 0x%08Xu },' % (name, v))
    return "\n".join(out) + "\n"
```

and in `main()` also write it next to the header: `open(os.path.join(os.path.dirname(a.header), "gw_ui_token_names.inc"), "w", encoding="utf-8", newline="\n").write(names_text(tok))`. Run `python menu/pipeline/atlas_tokens.py`. In `gw_script_ui.inc`:

```c
static const struct { const char *name; unsigned rgba; } gs_ui_tokens[] = {
#include "gw_ui_token_names.inc"
};
static int l_ui_token(lua_State *L)
{
    const char *n = luaL_checkstring(L, 1);
    size_t i;
    for (i = 0; i < sizeof gs_ui_tokens / sizeof gs_ui_tokens[0]; i++)
        if (strcmp(gs_ui_tokens[i].name, n) == 0) { lua_pushinteger(L, (lua_Integer) gs_ui_tokens[i].rgba); return 1; }
    lua_pushnil(L);
    return 1;
}
```

and `{"token", l_ui_token},` in `gs_ui_funcs`. The stub reads `menu/atlas/tokens.json` with a Lua pattern over its `colours` block (`"([%w-]+)": (%d+)`), found relative to `arg[0]` like its header limits.
- [ ] **Step 3: Run** `python menu/pipeline/test_atlas_tokens.py`, `nt atlas-binding`, the stub test.

#### 5f. `gd.ui.entries(parent)` and `gd.ui.activate(entry)` (N9)

Mods add entries under `lab.pause` (spec 8.1). The LAB must **read** them and **activate** one. Activation must stay the registry's act (it opens the owning mod's screen or runs its `on_entry`, under that mod's own permissions), and a mod may use these two calls only for a parent it owns: the registry's built-in table says `lab.pause` belongs to `geno-lab`. (This is a proposal beyond the spec: without the owner rule any mod could trigger another mod's entries by id.)

- [ ] **Step 1: Tests first**, in the binding test against stand-ins for the registry (`at_registry_visible`, `at_registry_activate`, `at_registry_owner`; RECONCILE: step 2's names), as a script that is **not** the owner and then as the owner:

```c
    gs.cur = 1;                                                               /* mod id "envoy": not the owner of lab.pause */
    LUA_HAS("return gd.ui.entries('lab.pause')", "not yours");
    LUA_HAS("return gd.ui.activate('x.entry')", "not yours");
    gs.cur = 2;                                                               /* slot 2 is the owner: set `snprintf(gs.s[2].id, sizeof gs.s[2].id, "geno-lab/main")` next to where the stand-in names its scripts */
    LUA_IS("local e = gd.ui.entries('lab.pause'); return #e .. ':' .. e[1].id .. ':' .. e[1].label .. ':' .. e[1].mod", "1:x.entry:Extra:somemod");
    LUA_IS("return tostring(gd.ui.activate('x.entry')) .. tostring(gd.ui.activate('x.gone'))", "truefalse");
    LUA_HAS("return gd.ui.entries('solo')", "not yours");                    /* only its own parents */
    gs.cur = -1;
```

and in the stub: `ui.entries(parent)` returns `ui._entries[parent]` (a test helper `ui.add_entry{ parent=, id=, label=, mod= }`), raises `not yours` unless `ui.owns[parent] == ui.owner_mod`, and `ui.activate(id)` records the call and returns whether the entry exists.
- [ ] **Step 2: Implement** `l_ui_entries` and `l_ui_activate` in `gw_script_ui.inc` over the registry (both check `at_registry_owner(parent) == the caller's mod id` and raise `gd.ui.entries: "<parent>" is not yours` otherwise; entries come back already filtered by the registry's visibility rules, including "hidden while a session exists"):

```c
static int l_ui_entries(lua_State *L)
{
    AtRegEntry e[24];
    const char *parent = luaL_checkstring(L, 1);
    int n, i;
    if (!gs_ui_owns_parent(parent)) return luaL_error(L, "gd.ui.entries: \"%s\" is not yours", parent);
    n = at_registry_visible(parent, e, 24);
    lua_createtable(L, n, 0);
    for (i = 0; i < n; i++) {
        lua_createtable(L, 0, 5);
        lua_pushstring(L, e[i].id); lua_setfield(L, -2, "id");
        lua_pushstring(L, e[i].label); lua_setfield(L, -2, "label");
        lua_pushstring(L, e[i].blurb); lua_setfield(L, -2, "blurb");
        lua_pushstring(L, e[i].mod); lua_setfield(L, -2, "mod");
        lua_pushstring(L, e[i].badge); lua_setfield(L, -2, "badge");
        lua_rawseti(L, -2, i + 1);
    }
    return 1;
}
static int l_ui_activate(lua_State *L)
{
    const char *id = luaL_checkstring(L, 1);
    if (!gs_ui_owns_entry_parent(id)) return luaL_error(L, "gd.ui.activate: \"%s\" is not yours", id);
    lua_pushboolean(L, at_registry_activate(id));
    return 1;
}
```

(`gs_ui_owns_parent` compares `at_registry_owner(parent)` with the calling script's mod id, as `gs_ui_usable` and the id-prefix rule already know it.) Register both in `gs_ui_funcs`. Add `lab.pause` to the registry's built-in parent table with owner `geno-lab` (RECONCILE: where step 2 keeps it) and a registry test that an entry whose manifest names parent `lab.pause` is accepted and counted against the 6-per-mod and 12-visible caps.
- [ ] **Step 3: Run** `nt atlas-binding`, the stub test, `nt atlas-registry` (step 2's test, if its case is named so).
- [ ] **Step 4: Commit** each sub-step as its own commit in the game repo (and the token generator in the workspace repo), messages `atlas ui: <the sub-step>`.


#### 5g. The stub (`pc/tests/atlas_ui_stub.lua`), once, for every sub-step above

The Lua checks of Tasks 7 to 9 run against the stub, so the stub gets the same contract as the engine for everything 5a to 5f add. **Do this sub-step first if you are doing any of the others, and keep it in step with them.** (The edits below were written and run against `lab.lua` and the checks of Tasks 7 to 9; they are the stub's side, not the engine's.) Each anchor is a line of the stub as it stands.

1. In `Stub.new`, the state table: `held = {}, _prev = {} }` becomes `held = {}, _prev = {}, _tab = {}, huds = {}, _entries = {}, owns = {} }`.
2. The value kinds. In `ui.screen`: `elseif k ~= 'toggle' and k ~= 'choice' and k ~= 'text' and k ~= 'counter' then` becomes `elseif k ~= 'toggle' and k ~= 'choice' and k ~= 'stepper' and k ~= 'text' and k ~= 'counter' then`. In `ui.engine_row`: add `and v.kind ~= 'stepper'` to the guard line (`(v.kind ~= 'toggle' and v.kind ~= 'choice' and v.kind ~= 'slider')`), and after the choice branch (`elseif v.kind == 'choice' then arg = (how == 'left') and -1 or 1`) add:

```lua
  elseif v.kind == 'stepper' then
   if how == 'accept' then return false end                         -- A runs the row (on.accept); only left and right change it
   arg = (how == 'left') and -1 or 1
```

3. Backdrop and tabs. In `ui.screen`, before `local port = d.port or 1`:

```lua
  if d.backdrop ~= nil and d.backdrop ~= 'ground' and d.backdrop ~= 'world' then fail('backdrop is "ground" or "world"') end
  if d.tabs ~= nil then
   if type(d.tabs) ~= 'table' or #d.tabs < 1 or #d.tabs > 8 then fail('tabs is 1 to 8 entries') end
   for i, tb in ipairs(d.tabs) do if type(tb) ~= 'table' then fail(('tab %d is not a table'):format(i)) end end
  end
```

and after `ui.screens[d.id] = d`: `if d.tabs then ui._tab[d.id] = math.max(1, math.min(#d.tabs, d.tab or 1)) end`. In `ui.engine_press`, replace `elseif kind == 'l' or kind == 'r' then` with:

```lua
  elseif kind == 'l' or kind == 'r' then
   if d.tabs then                                                    -- tabs: the engine moves the tab and tells the script
    local n = #d.tabs
    local tb = ((ui._tab[id] or 1) - 1 + (kind == 'l' and -1 or 1)) % n + 1
    ui._tab[id] = tb
    if on.tab then apply(on.tab(tb), ui._owner[id]) end
    if ui.screens[id] then ui.refresh(id) end
    return true
   end
```

(the old `if not on.page then return false end` and the rest of that branch follow unchanged).

4. Entries, the HUD and tokens. Before the comment line `-- ---- the engine's part ---` add:

```lua
 function ui.entries(parent)
  if ui.owns[parent] ~= ui.owner_mod then error(('gd.ui.entries: "%s" is not yours'):format(tostring(parent)), 2) end
  local out = {}
  for _, e in ipairs(ui._entries[parent] or {}) do out[#out + 1] = { id = e.id, label = e.label, blurb = e.blurb or '', mod = e.mod or '', badge = e.badge or '' } end
  return out
 end
 function ui.add_entry(e) ui._entries[e.parent] = ui._entries[e.parent] or {}; table.insert(ui._entries[e.parent], e) end
 function ui.activate(id)
  for parent, list in pairs(ui._entries) do
   for _, e in ipairs(list) do
    if e.id == id then
     if ui.owns[parent] ~= ui.owner_mod then error(('gd.ui.activate: "%s" is not yours'):format(tostring(id)), 2) end
     ui.activated = id
     return true
    end
   end
  end
  return false
 end
 local PARTS = { readout = true, track = true, strip = true, note = true }
 function ui.hud(d)
  if type(d) ~= 'table' or type(d.id) ~= 'string' then fail('hud: a table with an id') end
  if ui.owner_mod and not is_console() and d.id:sub(1, #ui.owner_mod + 1) ~= ui.owner_mod .. '.' then fail(('hud id "%s" must start with "%s."'):format(d.id, ui.owner_mod)) end
  for zname, parts in pairs(d.zones or {}) do
   for i, p in ipairs(parts) do
    if not PARTS[p.kind] then fail(('hud %s part %d: unknown kind "%s"'):format(zname, i, tostring(p.kind))) end
    if p.kind == 'readout' and #(p.rows or {}) > 16 then fail('a readout has at most 16 rows') end
    if p.kind == 'track' and (#(p.spans or {}) > 16 or #(p.marks or {}) > 24) then fail('a track has at most 16 spans and 24 marks') end
   end
  end
  ui.huds[d.id] = d
  return true
 end
 local tokens
 function ui.token(name)
  if not tokens then
   tokens = {}
   local here = (arg and arg[0] or ''):gsub('\\', '/'):gsub('[^/]*$', '')
   for _, p in ipairs({ here .. '../../../menu/atlas/tokens.json', 'menu/atlas/tokens.json' }) do
    local f = io.open(p)
    if f then
     local text = f:read('a'); f:close()
     for k, v in (text:match('"colours"%s*:%s*(%b{})') or ''):gmatch('"([%w%-]+)"%s*:%s*(%d+)') do tokens[k] = math.tointeger(tonumber(v)) end
     break
    end
   end
  end
  return tokens[name]
 end
```

(The HUD part names `strip` and `note` and their field shapes are step 3's, `RECONCILE`; the stub accepts them by name only. `ui.owns` is the registry's built-in parent-owner table in miniature: a test sets `ui.owns['lab.pause'] = 'geno-lab'`.)

5. The stub's own tests, in `atlas_ui_stub_test.lua`, before its last `local off = ...` line:

```lua
-- Atlas step 7: tabs, the world backdrop, entries, the HUD, tokens (the stub's side of Task 5)
do
  local s = Stub.new({ caller = 'geno-lab', owner_mod = 'geno-lab' })
  local one = { { id = 'a', label = 'A' } }
  local TB = {}
  s.screen({ id = 'geno-lab.t', backdrop = 'world', tabs = { { name = 'ONE' }, { name = 'TWO' }, { name = 'THREE' } }, tab = 2,
    primary = { kind = 'list', items = one }, on = { tab = function(i) TB[#TB + 1] = i end, page = function() TB[#TB + 1] = 'page' end } })
  s.open('geno-lab.t')
  s.engine_press('geno-lab.t', 'r'); s.engine_press('geno-lab.t', 'r'); s.engine_press('geno-lab.t', 'l')
  check(table.concat(TB, ',') == '3,1,3', 'L and R move the tab and tell on.tab, wrapping; on.page is not called when there are tabs (got ' .. table.concat(TB, ',') .. ')')
  raises(function() s.screen({ id = 'geno-lab.t0', tabs = {}, primary = { kind = 'list', items = one } }) end, 'tabs', 'tabs is 1 to 8 entries')
  local nine = {}
  for i = 1, 9 do nine[i] = { name = 'T' .. i } end
  raises(function() s.screen({ id = 'geno-lab.t9', tabs = nine, primary = { kind = 'list', items = one } }) end, 'tabs', 'nine tabs are refused')
  raises(function() s.screen({ id = 'geno-lab.bd', backdrop = 'sky', primary = { kind = 'list', items = one } }) end, 'backdrop', 'backdrop is ground or world')
  local NT = {}
  s.screen({ id = 'geno-lab.nt', primary = { kind = 'list', items = one }, on = { tab = function() NT[#NT + 1] = 'tab' end, page = function(d) NT[#NT + 1] = 'page' .. d end } })
  s.open('geno-lab.nt'); s.engine_press('geno-lab.nt', 'r')
  check(table.concat(NT, ',') == 'page1', 'a screen without tabs: R still reaches on.page (got ' .. table.concat(NT, ',') .. ')')
  s.owns['lab.pause'] = 'geno-lab'
  s.add_entry({ parent = 'lab.pause', id = 'x.entry', label = 'Extra', mod = 'x' })
  check(#s.entries('lab.pause') == 1 and s.entries('lab.pause')[1].mod == 'x' and s.entries('lab.pause')[1].blurb == '', 'entries(parent) lists what the registry holds for a parent the caller owns')
  raises(function() s.entries('solo') end, 'not yours', 'a parent the caller does not own')
  check(s.activate('x.entry') == true and s.activated == 'x.entry' and s.activate('nope') == false, 'activate runs the entry through the registry; an unknown id is false')
  local other = Stub.new({ caller = 'envoy', owner_mod = 'envoy' })
  other.owns['lab.pause'] = 'geno-lab'; other.add_entry({ parent = 'lab.pause', id = 'y.entry', label = 'Y', mod = 'y' })
  raises(function() other.activate('y.entry') end, 'not yours', 'another mod cannot activate an entry of a parent it does not own')
  check(s.hud({ id = 'geno-lab.hud', zones = { top_left = { { kind = 'readout', rows = {} } } } }) and s.huds['geno-lab.hud'] ~= nil, 'a hud registers')
  raises(function() s.hud({ id = 'other.hud', zones = {} }) end, 'must start with', 'a hud id carries the mod prefix')
  raises(function() s.hud({ id = 'geno-lab.hud', zones = { top_left = { { kind = 'blob' } } } }) end, 'unknown kind', 'an unknown part kind')
  local many = {}
  for i = 1, 17 do many[i] = { label = 'r', value = 'v' } end
  raises(function() s.hud({ id = 'geno-lab.hud', zones = { top_left = { { kind = 'readout', rows = many } } } }) end, 'at most 16 rows', 'a readout has at most 16 rows')
  check(s.token('ember') == 0xFF7A3DFF and s.token('nope') == nil, 'the stub reads the tokens file (ember is ' .. tostring(s.token('ember')) .. ')')
end
```

and the stepper check from 5a goes in the same file after the `ch=1,ch=-1,ch=1` check. Run `lua pc/tests/atlas_ui_stub_test.lua`: the baseline is 85 checks; with 5a and 5g it is 100, `0 failed`.

---

### Task 6: HUD parts: `readout` and `track`

The LAB's info panel and move timeline become descriptions of two new parts. They are drawn by the zones of step 3's `gd.ui.hud`; this task builds the parts, their tests and their value-tree conversion. **Gate:** Task 0 exits 0 (N4). The registration with step 3's part table is `RECONCILE`.

The three style lessons apply from the first line: plates have the chamfer on top-left and bottom-right only; every colour that means something also has a word, a number or a shape (a hit window's id is drawn as a number where it fits; each mark kind has its own shape); no text sits over its plate edge at 12 px. `atlas_lint.h` enforces them in the tests.

**Files:**
- Create (game repo): `pc/platform/gw_ui_hud_parts.h`, `pc/platform/gw_ui_hud_parts.c`, `pc/tests/atlas_hud_parts_test.c`
- Modify (game repo): `pc/platform/gw_script_ui.inc` (the registration, RECONCILE)
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-hud-parts`)

**Interfaces:**
Produces: `AtReadout`/`at_part_readout`/`at_readout_height`/`at_readout_from_val`; `AtTrack`/`at_part_track`/`at_track_height`/`at_track_from_val`. Lua shapes (the contract Task 10 and the stub use):

```lua
{ kind = "readout", title = "P1 FOX", cols = 1, rows = { { label = "Motion", value = "Wait f1", tone = "ok" }, ... } }   -- tone: nil, "ok", "warn", "bad"
{ kind = "track", title = "P1 FOX  Wait", right = "f 5 / 26   IASA 20", len = 26, now = 5, note = "f5-9 #0 9% a45",
  spans = { { from = 5, to = 9, id = 0 } }, marks = { { frame = 20, kind = "iasa" } } }      -- kind: iasa, invinc, gfx, sfx, vis
```

- [ ] **Step 1: Write the failing test.** Create `pc/tests/atlas_hud_parts_test.c`:

```c
#include "atlas_lint.h"
#include "../platform/gw_ui_hud_parts.h"

static AtReadout ro(int n, int cols)
{
    AtReadout d; int i;
    memset(&d, 0, sizeof d);
    snprintf(d.title, sizeof d.title, "%s", "P1 FOX");
    d.cols = cols; d.n = n;
    for (i = 0; i < n; i++) { snprintf(d.row[i].label, sizeof d.row[i].label, "Row %d", i); snprintf(d.row[i].value, sizeof d.row[i].value, "%d.%d", i, i); d.row[i].tone = i % 4; }
    return d;
}

static void readout(void)
{
    AtSink s;
    AtReadout d = ro(12, 2);
    AtRect r;
    r.x = 8.0f; r.y = 8.0f; r.w = 400.0f; r.h = at_readout_height(&d);
    s = rec_sink(); at_part_readout(&s, &FAKE, r, &d);
    CHECK(lint_plate_corners(r, 8.0f) == 0);                                        /* the E1 plate: 8 px chamfer, top-left and bottom-right */
    CHECK(lint_text_inside(r, 0) == 0 && lint_text_overlaps() == 0 && texts_legible());
    CHECK(find_text("P1 FOX") != NULL && find_text("Row 0") != NULL && find_text("Row 11") != NULL);
    CHECK(at_readout_height(&d) < 150.0f);                                          /* 12 rows in two columns: six lines */
    CHECK(count_color(AT_C_JADE) >= 1 && count_color(AT_C_SUN) >= 1 && count_color(AT_C_ROSE) >= 1);   /* tones: ok, warn, bad are told apart */
    /* a narrow plate falls back to one column and grows taller; nothing leaves it */
    {
        AtReadout one = d; one.cols = 1;
        r.w = 200.0f; r.h = at_readout_height(&one);
        s = rec_sink(); at_part_readout(&s, &FAKE, r, &d);
        CHECK(lint_text_inside(r, 0) == 0 && lint_text_overlaps() == 0);
    }
    /* the worst strings: a 39-character value and a 23-character label are cut by the fit rule inside their column */
    memset(d.row[3].value, 'v', 39); d.row[3].value[39] = '\0'; memset(d.row[3].label, 'l', 23); d.row[3].label[23] = '\0';
    r.w = 400.0f; r.h = at_readout_height(&d);
    s = rec_sink(); at_part_readout(&s, &FAKE, r, &d);
    CHECK(lint_text_inside(r, 0) == 0 && lint_text_overlaps() == 0);
    /* 16 rows is the cap, 0 rows is a title only */
    d = ro(16, 1); r.h = at_readout_height(&d); s = rec_sink(); at_part_readout(&s, &FAKE, r, &d); CHECK(lint_text_inside(r, 0) == 0);
    d = ro(0, 1); r.h = at_readout_height(&d); s = rec_sink(); at_part_readout(&s, &FAKE, r, &d); CHECK(find_text("P1 FOX") != NULL && lint_text_inside(r, 0) == 0);
}

static AtTrack tk(int len, int now)
{
    AtTrack t;
    memset(&t, 0, sizeof t);
    snprintf(t.title, sizeof t.title, "%s", "P1 FOX  AttackS3S"); snprintf(t.right, sizeof t.right, "%s", "f 5 / 26   IASA 20"); snprintf(t.note, sizeof t.note, "%s", "f5-9 #0 9% a45   f12-14 #1 7% a361");
    t.len = len; t.now = now;
    t.n_spans = 3; t.span[0].from = 5; t.span[0].to = 9; t.span[0].id = 0; t.span[1].from = 12; t.span[1].to = 14; t.span[1].id = 1; t.span[2].from = 20; t.span[2].to = 22; t.span[2].id = 7;
    t.n_marks = 5; t.mark[0].frame = 20; t.mark[0].kind = AT_MK_IASA; t.mark[1].frame = 3; t.mark[1].kind = AT_MK_INVINC; t.mark[2].frame = 6; t.mark[2].kind = AT_MK_GFX;
    t.mark[3].frame = 8; t.mark[3].kind = AT_MK_SFX; t.mark[4].frame = 10; t.mark[4].kind = AT_MK_VIS;
    return t;
}

static void track(void)
{
    AtSink s;
    AtTrack t = tk(26, 5);
    AtRect r;
    int i;
    r.x = 8.0f; r.y = 350.0f; r.w = 624.0f; r.h = at_track_height();
    s = rec_sink(); at_part_track(&s, &FAKE, r, &t);
    CHECK(lint_plate_corners(r, 8.0f) == 0);
    CHECK(lint_text_inside(r, 0) == 0 && lint_text_overlaps() == 0 && texts_legible());
    CHECK(find_text("P1 FOX  AttackS3S") != NULL && find_text("f 5 / 26   IASA 20") != NULL);
    /* a hit window is never colour alone: its id is a number over it when it fits (a 5 frame window at 624 px is wide) */
    CHECK(find_text("#0") != NULL && find_text("#1") != NULL);
    CHECK(count_color(AT_C_ROSE) >= 1 && count_color(AT_C_SUN) >= 1 && count_color(AT_C_JADE) >= 1);   /* ids 0, 1, and the IASA mark */
    /* each mark kind has its own shape: five kinds draw five distinct polygon footprints below the bar */
    {
        float seen[5]; int ns = 0, k;
        for (i = 0; i < REC.np; i++) {
            float w = poly_maxx(&REC.p[i]) - poly_minx(&REC.p[i]), h = poly_maxy(&REC.p[i]) - poly_miny(&REC.p[i]);
            if (poly_miny(&REC.p[i]) < r.y + 46.0f || poly_maxy(&REC.p[i]) > r.y + 64.0f || w > 12.0f) continue;
            for (k = 0; k < ns && !(fabsf(seen[k] - (w * 100.0f + h)) < 0.5f); k++) ;
            if (k == ns && ns < 5) seen[ns++] = w * 100.0f + h;
        }
        CHECK(ns >= 4);                                                              /* bar, square, two triangles and a disc or tick: at least four footprints */
    }
    /* the playhead is inside the bar for any 'now', also when 'now' is out of range or the move is one frame long */
    { int nows[5] = { 0, 1, 26, 99, -4 }, k;
      for (k = 0; k < 5; k++) { AtTrack u = tk(26, nows[k]); s = rec_sink(); at_part_track(&s, &FAKE, r, &u); CHECK(lint_text_inside(r, 0) == 0); } }
    { AtTrack u = tk(1, 1); s = rec_sink(); at_part_track(&s, &FAKE, r, &u); CHECK(lint_text_inside(r, 0) == 0); }          /* length 1: no division by zero */
    { AtTrack u = tk(0, 0); s = rec_sink(); at_part_track(&s, &FAKE, r, &u); CHECK(REC.np > 0); }                           /* length 0: drawn as 1 */
    /* a 600-frame move: windows are at least 2 px, and ids are dropped when they do not fit rather than overlapped */
    { AtTrack u = tk(600, 100); s = rec_sink(); at_part_track(&s, &FAKE, r, &u); CHECK(lint_text_inside(r, 0) == 0 && lint_text_overlaps() == 0); }
    /* spans and marks outside the move are clamped, never drawn outside the bar */
    { AtTrack u = tk(26, 5); u.span[0].from = -5; u.span[0].to = 900; u.mark[0].frame = 5000; s = rec_sink(); at_part_track(&s, &FAKE, r, &u);
      for (i = 0; i < REC.np; i++) CHECK(poly_minx(&REC.p[i]) >= r.x - 0.5f && poly_maxx(&REC.p[i]) <= r.x + r.w + 0.5f); }
    /* a narrow plate (a 4:3 corner): still inside */
    r.w = 300.0f; s = rec_sink(); at_part_track(&s, &FAKE, r, &t); CHECK(lint_text_inside(r, 0) == 0 && lint_text_overlaps() == 0);
}

int main(void)
{
    readout();
    track();
    ATLAS_DONE("atlas hud parts");
}
```

Register in `native_test.sh` (append `, atlas-hud-parts`): `atlas-hud-parts) sources=(pc/tests/atlas_hud_parts_test.c pc/platform/gw_ui_hud_parts.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_val.c) ;;`.
- [ ] **Step 2: Run to verify it fails.** `nt atlas-hud-parts`. Expected: `fatal error: '../platform/gw_ui_hud_parts.h' file not found`.
- [ ] **Step 3: Write the parts.** Create `pc/platform/gw_ui_hud_parts.h`:

```c
/* gw_ui_hud_parts.h - two HUD parts for read-only data: a readout (label and value rows) and a track (a move's timeline). Pure C. */
#ifndef GW_UI_HUD_PARTS_H
#define GW_UI_HUD_PARTS_H
#include "gw_ui_parts.h"
#include "gw_ui_val.h"
#ifdef __cplusplus
extern "C" {
#endif

#define AT_READ_ROWS 16
typedef struct { char label[24]; char value[40]; int tone; } AtReadRow;     /* tone: 0 plain, 1 ok (jade), 2 warn (sun), 3 bad (rose) */
typedef struct { char title[AT_STR]; int cols, n; AtReadRow row[AT_READ_ROWS]; } AtReadout;
float at_readout_height(const AtReadout *d);
void at_part_readout(const AtSink *s, const AtTextOps *o, AtRect r, const AtReadout *d);
int at_readout_from_val(const AtvArena *a, int t, AtReadout *out, char *err, int errcap);

#define AT_TRACK_SPANS 16
#define AT_TRACK_MARKS 24
enum { AT_MK_IASA, AT_MK_INVINC, AT_MK_GFX, AT_MK_SFX, AT_MK_VIS };
typedef struct { int from, to, id; } AtTrackSpan;
typedef struct { int frame, kind; } AtTrackMark;
typedef struct { char title[AT_STR], right[AT_STR], note[AT_STR]; int len, now, n_spans, n_marks; AtTrackSpan span[AT_TRACK_SPANS]; AtTrackMark mark[AT_TRACK_MARKS]; } AtTrack;
float at_track_height(void);
void at_part_track(const AtSink *s, const AtTextOps *o, AtRect r, const AtTrack *t);
int at_track_from_val(const AtvArena *a, int t, AtTrack *out, char *err, int errcap);

#ifdef __cplusplus
}
#endif
#endif
```

Create `pc/platform/gw_ui_hud_parts.c`:

```c
#include "gw_ui_hud_parts.h"
#include "gw_ui_tokens.h"
#include <stdio.h>
#include <string.h>

/* ---- the readout ---- */
static int eff_cols(const AtReadout *d, float w) { return d->cols >= 2 && w >= 380.0f ? 2 : 1; }

float at_readout_height(const AtReadout *d)
{
    int rows = d->n > 0 ? d->n : 0, cols = d->cols >= 2 ? 2 : 1;
    int per = (rows + cols - 1) / cols;
    return 36.0f + 16.0f * (float) per + 10.0f;
}

static unsigned tone_rgba(int tone)
{
    return tone == 1 ? AT_C_JADE : tone == 2 ? AT_C_SUN : tone == 3 ? AT_C_ROSE : AT_C_IVORY;
}

void at_part_readout(const AtSink *s, const AtTextOps *o, AtRect r, const AtReadout *d)
{
    int cols = eff_cols(d, r.w), per, i, n = d->n > AT_READ_ROWS ? AT_READ_ROWS : d->n;
    float cw;
    at_plate(s, r, AT_C_PLATE, AT_C_EDGE, 3.0f, (float) AT_PX_CH);
    at_text(s, o, AT_R_CAP12, d->title, r.x + 12.0f, r.y + 20.0f, AT_C_MUTED, AT_ALIGN_LEFT, r.w - 24.0f);
    per = (n + cols - 1) / cols;
    if (per < 1) per = 1;
    cw = (r.w - 24.0f) / (float) cols;
    for (i = 0; i < n; i++) {
        int c = i / per, k = i % per;
        float x = r.x + 12.0f + cw * (float) c, y = r.y + 36.0f + 16.0f * (float) k + 12.0f, gap = c + 1 < cols ? 12.0f : 0.0f;
        at_text(s, o, AT_R_BODY12, d->row[i].label, x, y, AT_C_MUTED, AT_ALIGN_LEFT, cw * 0.42f);
        at_text(s, o, AT_R_NUM12, d->row[i].value, x + cw - gap, y, tone_rgba(d->row[i].tone), AT_ALIGN_RIGHT, cw * 0.5f - gap);
    }
}

static int tone_of(const char *t) { return t == NULL ? 0 : strcmp(t, "ok") == 0 ? 1 : strcmp(t, "warn") == 0 ? 2 : strcmp(t, "bad") == 0 ? 3 : 0; }

int at_readout_from_val(const AtvArena *a, int t, AtReadout *out, char *err, int errcap)
{
    int rows, n, i;
    memset(out, 0, sizeof *out);
    if (atv_kind(a, t) != ATV_TABLE) { snprintf(err, (size_t) errcap, "%s", "gd.ui.hud: a readout is a table"); return 0; }
    snprintf(out->title, sizeof out->title, "%s", atv_strv(a, atv_get(a, t, "title"), ""));
    out->cols = (int) atv_numv(a, atv_get(a, t, "cols"), 1.0) >= 2 ? 2 : 1;
    rows = atv_get(a, t, "rows");
    n = atv_len(a, rows);
    if (n > AT_READ_ROWS) { snprintf(err, (size_t) errcap, "gd.ui.hud: a readout has at most %d rows", AT_READ_ROWS); return 0; }
    for (i = 0; i < n; i++) {
        int r = atv_at(a, rows, i + 1);
        if (atv_kind(a, r) != ATV_TABLE) { snprintf(err, (size_t) errcap, "gd.ui.hud: readout row %d is not a table", i + 1); return 0; }
        snprintf(out->row[i].label, sizeof out->row[i].label, "%s", atv_strv(a, atv_get(a, r, "label"), ""));
        snprintf(out->row[i].value, sizeof out->row[i].value, "%s", atv_strv(a, atv_get(a, r, "value"), ""));
        out->row[i].tone = tone_of(atv_strv(a, atv_get(a, r, "tone"), NULL));
    }
    out->n = n;
    return 1;
}

/* ---- the track ---- */
float at_track_height(void) { return 78.0f; }

static unsigned span_rgba(int id) { return id == 0 ? AT_C_ROSE : id == 1 ? AT_C_SUN : id == 2 ? AT_C_JADE : id == 3 ? AT_C_TEXT2 : AT_C_DIM; }
static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

static void tri_up(const AtSink *s, float cx, float y, float w, unsigned c)
{
    float x[4], yy[4];
    x[0] = cx - w * 0.5f; x[1] = cx + w * 0.5f; x[2] = cx; x[3] = cx;
    yy[0] = y + w; yy[1] = y + w; yy[2] = y; yy[3] = y;
    s->poly(s->user, x, yy, c);
}
static void tri_down(const AtSink *s, float cx, float y, float w, unsigned c)
{
    float x[4], yy[4];
    x[0] = cx - w * 0.5f; x[1] = cx + w * 0.5f; x[2] = cx; x[3] = cx;
    yy[0] = y; yy[1] = y; yy[2] = y + w; yy[3] = y + w;
    s->poly(s->user, x, yy, c);
}

void at_part_track(const AtSink *s, const AtTextOps *o, AtRect r, const AtTrack *t)
{
    int len = t->len < 1 ? 1 : t->len, i, now = clampi(t->now, 1, len);
    float x0 = r.x + 16.0f, w = r.w - 32.0f, sx = w / (float) len, by = r.y + 36.0f;
    at_plate(s, r, AT_C_PLATE, AT_C_EDGE, 3.0f, (float) AT_PX_CH);
    at_text(s, o, AT_R_CAP12, t->title, r.x + 12.0f, r.y + 18.0f, AT_C_IVORY, AT_ALIGN_LEFT, r.w * 0.55f);
    at_text(s, o, AT_R_NUM12, t->right, r.x + r.w - 12.0f, r.y + 18.0f, AT_C_MUTED, AT_ALIGN_RIGHT, r.w * 0.4f);
    at_poly_rect(s, x0, by, w, 8.0f, AT_C_GROUND2);                                  /* the well */
    for (i = 5; i <= len; i += 5) at_poly_rect(s, x0 + (float) (i - 1) * sx, by + 9.0f, 1.0f, i % 10 == 0 ? 4.0f : 2.0f, AT_C_LINE2);
    for (i = 0; i < t->n_spans && i < AT_TRACK_SPANS; i++) {
        int a = clampi(t->span[i].from, 1, len), b = clampi(t->span[i].to, 1, len);
        float sw = (float) (b - a + 1) * sx;
        if (sw < 2.0f) sw = 2.0f;
        if (x0 + (float) (a - 1) * sx + sw > x0 + w) sw = x0 + w - (x0 + (float) (a - 1) * sx);
        at_poly_rect(s, x0 + (float) (a - 1) * sx, by, sw, 8.0f, span_rgba(t->span[i].id));
        {   /* the id as a number over the window when its text fits: colour is not the only signal */
            char num[8];
            snprintf(num, sizeof num, "#%d", t->span[i].id);
            if (sw >= o->width(o->user, AT_R_NUM12, num) + 4.0f)
                at_text(s, o, AT_R_NUM12, num, x0 + (float) (a - 1) * sx + sw * 0.5f, by - 5.0f, span_rgba(t->span[i].id), AT_ALIGN_CENTER, 0.0f);
        }
    }
    for (i = 0; i < t->n_marks && i < AT_TRACK_MARKS; i++) {
        float mx = x0 + (float) (clampi(t->mark[i].frame, 1, len) - 1) * sx + sx * 0.5f, my = by + 14.0f;
        switch (t->mark[i].kind) {
        case AT_MK_IASA: at_poly_rect(s, mx - 1.5f, my, 3.0f, 10.0f, AT_C_JADE); break;          /* a bar */
        case AT_MK_INVINC: at_poly_rect(s, mx - 2.5f, my + 2.0f, 5.0f, 5.0f, AT_C_IVORY); break;   /* a square */
        case AT_MK_GFX: tri_up(s, mx, my + 1.0f, 7.0f, AT_C_SUN); break;                          /* a triangle up */
        case AT_MK_SFX: tri_down(s, mx, my + 1.0f, 7.0f, AT_C_ROSE); break;                       /* a triangle down */
        default: at_disc(s, mx, my + 5.0f, 3.0f, AT_C_MUTED); break;                              /* a disc */
        }
    }
    {   /* the playhead: a bar with a cap, inside the well whatever 'now' is */
        float px = x0 + (float) (now - 1) * sx + sx * 0.5f;
        at_poly_rect(s, px - 1.0f, by - 3.0f, 2.0f, 14.0f, AT_C_IVORY);
    }
    at_text(s, o, AT_R_BODY12, t->note, r.x + 12.0f, r.y + 72.0f, AT_C_MUTED, AT_ALIGN_LEFT, r.w - 24.0f);
}

static int kind_of(const char *k)
{
    return strcmp(k, "iasa") == 0 ? AT_MK_IASA : strcmp(k, "invinc") == 0 ? AT_MK_INVINC : strcmp(k, "gfx") == 0 ? AT_MK_GFX : strcmp(k, "sfx") == 0 ? AT_MK_SFX : AT_MK_VIS;
}

int at_track_from_val(const AtvArena *a, int t, AtTrack *out, char *err, int errcap)
{
    int spans, marks, n, i;
    memset(out, 0, sizeof *out);
    if (atv_kind(a, t) != ATV_TABLE) { snprintf(err, (size_t) errcap, "%s", "gd.ui.hud: a track is a table"); return 0; }
    snprintf(out->title, sizeof out->title, "%s", atv_strv(a, atv_get(a, t, "title"), ""));
    snprintf(out->right, sizeof out->right, "%s", atv_strv(a, atv_get(a, t, "right"), ""));
    snprintf(out->note, sizeof out->note, "%s", atv_strv(a, atv_get(a, t, "note"), ""));
    out->len = (int) atv_numv(a, atv_get(a, t, "len"), 1.0);
    out->now = (int) atv_numv(a, atv_get(a, t, "now"), 1.0);
    spans = atv_get(a, t, "spans"); n = atv_len(a, spans);
    for (i = 0; i < n && out->n_spans < AT_TRACK_SPANS; i++) {
        int sp = atv_at(a, spans, i + 1);
        out->span[out->n_spans].from = (int) atv_numv(a, atv_get(a, sp, "from"), 1.0);
        out->span[out->n_spans].to = (int) atv_numv(a, atv_get(a, sp, "to"), 1.0);
        out->span[out->n_spans].id = (int) atv_numv(a, atv_get(a, sp, "id"), 0.0);
        out->n_spans++;
    }
    marks = atv_get(a, t, "marks"); n = atv_len(a, marks);
    for (i = 0; i < n && out->n_marks < AT_TRACK_MARKS; i++) {
        int mk = atv_at(a, marks, i + 1);
        out->mark[out->n_marks].frame = (int) atv_numv(a, atv_get(a, mk, "frame"), 1.0);
        out->mark[out->n_marks].kind = kind_of(atv_strv(a, atv_get(a, mk, "kind"), "vis"));
        out->n_marks++;
    }
    return 1;
}
```

- [ ] **Step 4: Run.** `nt atlas-hud-parts`. Expected: `0 failed`. Likely first failures: a span id text overlapping the title (the id row is at `by - 5`, the title at `y + 18`: if `by - 5 < r.y + 24` they collide; the 78 px height and `by = r.y + 36` keep 13 px between them: if a real font's cap height changes that, move `by` down and the height up together); the narrow-plate case where the title and the right text share a line (`r.w * 0.55` and `0.4` leave 5 %: `lint_text_overlaps` proves it).
- [ ] **Step 5: The keep-out test (step 3's zones).** Add to the same test file, against step 3's zone geometry (RECONCILE: its names; the assertion is what matters): for widths 640, 853 and 1140, the rectangle a `readout` gets in zone `top_left` and a `track` in zone `bottom_center` must not intersect any retail keep-out rectangle (damage plates, stock icons, the match timer) that step 3 publishes, and must stay inside the title-safe box (32, 24 to 608, 456 at 640 wide):

```c
static int hit_rect(AtRect a, AtRect b) { return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h; }
static void keepouts(void)                                                      /* RECONCILE: at_hud_zone, at_hud_keepouts */
{
    static const float widths[3] = { 640.0f, 853.0f, 1140.0f };
    int k, i, n;
    for (k = 0; k < 3; k++) {
        AtRect ko[16], zr = at_hud_zone(AT_ZONE_TOP_LEFT, widths[k]), zt = at_hud_zone(AT_ZONE_BOTTOM_CENTER, widths[k]);
        n = at_hud_keepouts(widths[k], ko, 16);
        for (i = 0; i < n; i++) { CHECK(!hit_rect(zr, ko[i])); CHECK(!hit_rect(zt, ko[i])); }
        { AtReadout nine = ro(9, 1); CHECK(zt.h >= at_track_height() && zr.h >= at_readout_height(&nine)); }   /* the zones are big enough for the parts */
    }
}
```

If the zones are too small for a track at 4:3, the timeline moves to `top_center` or the track drops its note line: decide with the numbers, in this step, before Task 10.
- [ ] **Step 6: Register the parts with step 3's hud** (RECONCILE). In `gw_script_ui.inc`, where step 3 keeps its part table, add `readout` and `track`: for each, a name, the `from_val` function (`at_readout_from_val`, `at_track_from_val`), a height function (`at_readout_height` of the parsed value, `at_track_height`) and the draw function. The binding test (as a script) registers a hud with one of each and checks it draws (`gd.ui.state().quads` rises) and that a malformed part (rows not a table, 17 rows) raises with the messages above and registers nothing.
- [ ] **Step 7: Commit.** Game repo: `pc/platform/gw_ui_hud_parts.h/.c`, the test, the registration, message `atlas hud: readout and track parts (info panel and move timeline)`. Workspace repo: `tools/port/native_test.sh`, message `tools: atlas-hud-parts native test`.

---

### Task 7: The LAB pause menu as an Atlas screen

The legacy menu is `TABS` (PLAY, DISPLAY, DUMMY, STATES, TOOLS, DRILLS, EXIT), each tab a table of rows `{ label, icon, desc, value, run, adjust, toggle, key, delete, state_row, preview }`. The mapper turns **the same rows** into one `gd.ui.screen`, so no row is rewritten and the LAB's behaviour is the rows' behaviour. The legacy drawing stays as the fallback behind `lab ui off` (the default) until the owner has looked at the Atlas one.

How a row maps (the rule the tests pin):

| LAB row has | Atlas row | A | left and right |
|---|---|---|---|
| `toggle` | a toggle value, `on = toggle()` | `run` (else `adjust(1)`) once | the same, once |
| `adjust` (no toggle) | a **stepper** with `text = value()` | `run`, else `adjust(1)` | `adjust(dir)` |
| `value` only | a text value | `run` | nothing |
| neither | a plain row | `run` | nothing |
| `key` | the sub line `Match key F` | | |
| `desc` | the explainer's WHAT (a function is called when the focus moves) | | |
| `delete` (a library state) | | | Y asks in a dialog; A in the dialog deletes |
| `preview = "mode"` | WITH tags: the mode's keys | | |

**Files:**
- Modify (game repo): `pc/geno/mods/geno-lab/scripts/lab.lua`, `pc/geno/tools/lab_stage_d_check.lua`
- Create (workspace repo): `tools/port/lab_locals.sh`

**Gate:** Task 0 exits 0, Task 5 sub-steps 5a to 5d are merged (the stepper, the world backdrop, WITH tags and tabs from Lua), and `pc/tests/atlas_ui_stub.lua` supports them.

- [ ] **Step 1: The locals report (the 200-local limit).** Create `tools/port/lab_locals.sh`:

```bash
#!/usr/bin/env bash
# lab.lua's main chunk is at Lua's 200-local limit. This compiles it (a real overflow fails here) and reports how many locals
# the main function declares, so a change that adds one shows up before the harness refuses to load it.
#   tools/port/lab_locals.sh [path to lab.lua]
set -eu
F="${1:-melee/pc/geno/mods/geno-lab/scripts/lab.lua}"
luac -p "$F" && echo "luac -p: ok"
n=$(luac -l -l "$F" | awk '/^main /{f=1} f && /^locals \(/{gsub(/[^0-9]/,"",$2); print $2; exit}')
echo "main chunk locals declared: ${n:-unknown}"
```

Run it before any change and record the number (`chmod +x`, then `bash "$WS/tools/port/lab_locals.sh" "$GW_MELEE/pc/geno/mods/geno-lab/scripts/lab.lua"`). **The rule of this whole task: the number must not go up.** (It counts every local the function declares over its lifetime; the 200 limit is on locals active at once, so equal is the safe target and a drop is fine.)
- [ ] **Step 2: Write the failing checks.** Append to `pc/geno/tools/lab_stage_d_check.lua`, immediately before the line `for k in pairs(unknown) do u[#u + 1] = k end`. The block runs the LAB through the harness's own stub `gd` (which answers every unknown name with a no-op), so it replaces `gd.ui` with the real contract (`atlas_ui_stub.lua`) **owned by the script `geno-lab`**, never the console:

```lua
-- ---- the Atlas pause menu (docs/superpowers/plans/2026-10-06-atlas-step7-mods-and-lab.md) --------------------------------------
do
  local here = (arg and arg[0] or ""):gsub("\\", "/"):gsub("[^/]*$", "")
  local Stub = dofile(here .. "../../tests/atlas_ui_stub.lua")
  local ui = Stub.new{ caller = "geno-lab", owner_mod = "geno-lab", available = true }
  local SCREEN = "geno-lab.pause"
  local function upv(fn, name)
    for i = 1, 250 do local n, v = debug.getupvalue(fn, i) if not n then return nil end if n == name then return v end end
  end
  gd.ui = ui
  chunk()                                   -- a fresh LAB, loaded after gd.ui exists (the mapper reads it once, at load)
  env.on_match_start()
  local menu, TABS = upv(cmdfn, "menu"), upv(cmdfn, "TABS")
  local resumed, left = 0, nil
  gd.resume = function() resumed = resumed + 1 end
  gd.lab_leave = function(where) left = where end
  local function press(kind) return ui.engine_press(SCREEN, kind) end
  local function desc() return ui.screens[SCREEN] end
  local function rows() return desc().primary.items end
  local function row(label) for _, r in ipairs(rows()) do if r.label == label then return r end end end
  local function focus_on(label) local r = row(label); assert(r, "no row " .. label); ui.engine_focus(SCREEN, "list", r.id) end
  local function closed() return ui.state().depth == 0 end
  ui.owns["lab.pause"] = "geno-lab"                                 -- the registry's built-in owner table: lab.pause belongs to this mod

  -- 1. off by default: the legacy menu opens and no Atlas screen exists
  lab("menu")
  expect(menu.open and closed() and desc() == nil, "lab ui is off by default: the legacy menu opens and registers no screen")
  lab("menu close")
  -- 2. on: the pause menu is the Atlas screen, owned by the script, over the world, with every tab
  lab("ui on"); lab("menu")
  expect(ui.state().top == SCREEN and menu.open, "lab ui on: the pause menu is the Atlas screen")
  expect(ui._owner[SCREEN] == "geno-lab", "the screen is owned by the script geno-lab, not the console")
  local names, want = {}, {}
  for i, t in ipairs(desc().tabs) do names[i] = t.name end
  for i, t in ipairs(TABS) do want[i] = t.name end
  expect(table.concat(names, ",") == table.concat(want, ",") and want[#want - 1] == "DRILLS" and want[#want] == "EXIT", "every tab is there: " .. table.concat(names, ","))
  expect(desc().backdrop == "world" and desc().chapter == 1 and desc().trail.title == "PLAY" and desc().trail[1] == "LAB", "over the world, chapter I, LAB > PAUSE > PLAY")
  expect(not pcall(ui.screen, { id = "lab.pause", primary = { kind = "list", items = { { id = "a", label = "A" } } } }), "a screen id without the mod's prefix is refused for the script")
  -- 3. every row of every tab maps (count, unique ids, no row over the record's cap)
  for i, t in ipairs(TABS) do
    cmdfn("menu " .. t.name:lower())
    local legacy = #(type(t.items) == "function" and t.items() or t.items)
    local seen, ok = {}, true
    for _, r in ipairs(rows()) do if seen[r.id] or #r.id > 23 then ok = false end seen[r.id] = true end
    expect(ok and #rows() == math.min(legacy, 32) and #rows() >= 1, t.name .. ": " .. #rows() .. " rows for " .. legacy)
  end
  -- 4. a toggle flips once (run and adjust both flip it: calling both would undo it)
  cmdfn("menu display")
  local tr
  for _, r in ipairs(rows()) do if r.value and r.value.kind == "toggle" then tr = r break end end
  expect(tr ~= nil, "the DISPLAY tab has toggle rows")
  local before = tr.value.on
  focus_on(tr.label); press("accept")
  expect(row(tr.label).value.on ~= before, "a toggle flips on A")
  press("accept")
  expect(row(tr.label).value.on == before, "and flips back on the next A: once each, not twice")
  -- 5. a stepper: left and right change it, A runs it
  cmdfn("menu play")
  focus_on("Focus")
  local function focus_now() return tonumber(lab("status"):match("focus=(%d+)")) end
  local f0 = focus_now()
  ui.engine_row(SCREEN, "right")
  local f1 = focus_now()
  press("accept")
  local f2 = focus_now()
  expect(f1 ~= f0 and f2 ~= f1, "a stepper: right changes it, A runs it (focus " .. f0 .. ", " .. f1 .. ", " .. f2 .. ")")
  expect(row("Focus").value.kind == "stepper", "the Focus row is a stepper")
  -- 6. the focus stays on the row after every re-registration, and a tab change restores the tab's last row
  focus_on("Step +10"); press("accept")
  expect(ui.focus(SCREEN) == row("Step +10").id, "the focus stays on the same row after the screen is re-registered")
  press("r"); expect(menu.tab == 2 and desc().trail.title == "DISPLAY", "R: the next tab, the trail follows")
  press("l"); expect(menu.tab == 1 and ui.focus(SCREEN) == row("Step +10").id, "L: back, and the tab's last row has the focus again")
  -- 7. closing: the game resumes once, every port's input is neutralised, the screen is gone
  resumed = 0
  focus_on("Resume")
  local okc, errc = pcall(press, "accept")
  expect(okc and closed() and not menu.open, "Resume closes the menu and the screen (" .. tostring(errc) .. ")")
  expect(resumed == 1 and inputs[5] == 0 and inputs[6] == 0, "the game resumes once and all six ports' inputs are neutralised")
  gd.paused = function() return true end
  lab("menu"); resumed = 0
  press("back")
  expect(closed() and not menu.open and resumed == 0, "opened over a paused game: B closes the menu and leaves the game paused")
  press("back")                                                    -- a stray second B on a closed screen is harmless
  gd.paused = function() return false end
  -- 8. leaving the match closes the screen too
  lab("menu"); cmdfn("menu exit"); focus_on("Quit"); left = nil
  press("accept")
  expect(closed() and not menu.open and left == "menu", "EXIT > Quit leaves the match and closes the screen")
  -- 9. the explainer: WHAT is the row's description, and a mode row carries its keys as tags
  lab("menu"); cmdfn("menu display"); focus_on("Display mode")
  local ex = desc().explainer.provide(row("Display mode").id)
  expect(ex and ex.title == "Display mode" and #(ex.with and ex.with.tags or {}) >= 1 and ex.from.text == "Geno LAB", "the mode row explains itself and lists the mode's keys")
  lab("menu close")
  -- 10. the descriptions fit the explainer (the spec's one short rule: at most 110 characters; the engine cuts at 159)
  lab("menu")
  local long = {}
  for i, t in ipairs(TABS) do
    cmdfn("menu " .. t.name:lower())
    for _, r in ipairs(rows()) do
      local okp, e = pcall(desc().explainer.provide, r.id)
      if not okp then long[#long + 1] = t.name .. " / " .. r.label .. " (raised: " .. tostring(e) .. ")"
      elseif e and #e.what > 110 then long[#long + 1] = t.name .. " / " .. r.label .. " (" .. #e.what .. ")" end
    end
  end
  expect(#long == 0, "every row description is 110 characters or less; too long: " .. table.concat(long, "; "))
  lab("menu close"); lab("ui off")
-- (Tasks 8 and 9 add their checks above this closing end: one block, one preamble, no new file-scope local)
end
```

Two small additions to the harness's stub `gd`, because two descriptions read fields it does not have: in the `history = function() return { busy = false, ... } end` stub add `interval = 5, mb = 12.0`, and make sure `engine_focus` in `atlas_ui_stub.lua` calls `on.focus` (the mapper remembers each tab's row from it; if the stub's does not, add the call and a stub test for it).

- [ ] **Step 3: Run to verify it fails.**

```bash
cd "$GW_MELEE" && lua pc/geno/tools/lab_stage_d_check.lua pc/geno/mods/geno-lab/scripts/lab.lua | grep -E "FAIL|PASS" | tail -20
```

Expected: the old `PASS` lines still pass; the new block fails at `lab ui on` ("the pause menu is the Atlas screen") and everything after it (a `FAIL` per check, or a Lua error from `desc()` returning nil). That is the failing state.
- [ ] **Step 4: The hooks in the legacy code.** Five small edits, none adds a local, all are lines in `lab.lua`:

(a) The `menu` table (line `local menu = { open = false, tab = 1, ...`): add `ui = {}` to it (`..., slot = 1, target = 2, pct = 0, ui = {} }`).

(b) `menu_close`: after `menu.open = false` add `if menu.ui.close then menu.ui.close() end`. `menu_leave`: the same after its `menu.open = false`.

(c) `menu_open(port)`: as its last line add `if menu.ui.open then menu.ui.open(port) end`.

(d) `lab_menu_tick`: right after the `if not menu.open then ... return false end` block, add:

```lua
  if menu.ui.on and menu.ui.on() then return true end -- the Atlas screen reads the pad and the keys itself; the menu still owns the tick
```

(e) `on_draw`: change `if menu.open then lab_menu_draw() return end` to:

```lua
  if menu.open then
    if not (menu.ui.on and menu.ui.on()) then lab_menu_draw() end
    return
  end
```

and in `on_match_start` add `if menu.ui.close then menu.ui.close() end` after the line `menu.open, menu.reset_saved, menu.prev = false, false, {}`. In the console (`LE.console`): after the `elseif cmd == "menu" then` branch's tab loop (`for i, t in ipairs(TABS) do if t.name:lower() == rest:lower() then set_tab(i) end end`) add `if menu.ui.refresh then menu.ui.refresh() end`, and add a branch `elseif cmd == "ui" then if menu.ui.set then menu.ui.set(rest) else gd.log("lab ui: gd.ui is not available in this build") end`. In the help text of `lab help` add `lab ui on|off`.
- [ ] **Step 5: The mapper.** Immediately before `function on_tick()` add (this is one function scope; nothing in it is a top-level local):

```lua
-- ---- the Atlas pause menu ------------------------------------------------------------------------------------------------
-- docs/superpowers/plans/2026-10-06-atlas-step7-mods-and-lab.md. Off until `lab ui on`: the menu above is the fallback until the owner
-- has looked. No new top-level local: this scope holds its state and reaches the rest of the Lab through menu.ui.
;(function()
  local UI = type(gd.ui) == "table" and gd.ui or nil
  local SCREEN = "geno-lab.pause"
  local MAX_ROWS = 32 -- gw_ui_screen.h AT_MAX_ITEMS
  local on, opened = false, false
  local byid, shown, state_page = {}, {}, 1

  local function clip(s, n)
    s = tostring(s or "")
    if #s > n then return s:sub(1, n - 3) .. "..." end
    return s
  end
  local function row_id(tab, i) return "t" .. tab .. "r" .. i end

  -- the rows of one tab as a description, the legacy row for each id, and the legacy list that was shown
  local function rows_for(tab)
    local list = tab_items(tab)
    local fixed, states = {}, {}
    for _, it in ipairs(list) do
      if it.state_row then states[#states + 1] = it else fixed[#fixed + 1] = it end
    end
    local chosen = list
    local per = MAX_ROWS - #fixed - 1
    if #list > MAX_ROWS and (#states == 0 or per < 4) then -- no library to page (or no room for a page): the first rows, as the record allows
      chosen = {}
      for k = 1, MAX_ROWS do chosen[k] = list[k] end
      gd.log("Geno Lab: the " .. TABS[tab].name .. " tab has " .. #list .. " rows; the Atlas menu shows the first " .. MAX_ROWS)
    elseif #list > MAX_ROWS then -- the library can be any length; the record holds 32 rows: page it
      local pages = math.max(1, math.ceil(#states / per))
      state_page = math.max(1, math.min(state_page, pages))
      chosen = {}
      for _, it in ipairs(fixed) do chosen[#chosen + 1] = it end
      for k = (state_page - 1) * per + 1, math.min(#states, state_page * per) do chosen[#chosen + 1] = states[k] end
      chosen[#chosen + 1] = {
        label = "Library page", desc = "Left and right turn the page of the saved-state library.",
        value = function() return state_page .. " / " .. pages end,
        adjust = function(d) state_page = ((state_page - 1 + d) % pages) + 1 end,
      }
    end
    local rows, map = {}, {}
    for i, it in ipairs(chosen) do
      local id = row_id(tab, i)
      local row = { id = id, label = clip(it.label, 40) }
      if it.key then row.sub = "Match key " .. it.key end
      local val = it.value and it.value() or nil
      if it.toggle then row.value = { kind = "toggle", on = it.toggle() and true or false }
      elseif it.adjust then row.value = { kind = "stepper", text = clip(val or "", 20) }
      elseif val ~= nil then row.value = { kind = "text", text = clip(val, 20) } end
      rows[i], map[id] = row, it
    end
    return rows, map, chosen
  end

  local function explain(cell)
    local it = byid[cell]
    if not it then return nil end
    local d = it.desc
    if type(d) == "function" then d = d() end
    local ex = { kicker = TABS[menu.tab].name, title = clip(it.label, 24), what = clip(d or "", 159), from = { text = "Geno LAB" } }
    if it.preview == "mode" then
      local tags, md = {}, mode()
      for _, t in ipairs(md.t) do if #tags < 4 then tags[#tags + 1] = clip(t.k .. " " .. t.label, 19) end end
      for _, a in ipairs(md.a) do if #tags < 4 then tags[#tags + 1] = clip(a.k .. " " .. a.label, 19) end end
      ex.with = { tags = tags }
    end
    return ex
  end

  local register
  local function after() if menu.open and opened then register() end end -- the values and the explainer are data: rebuild them

  local function accept(cell)
    local it = byid[cell]
    if it == nil then return nil end
    if it.run then it.run() elseif it.adjust then it.adjust(1) end
    after()
    return nil
  end
  local function change(cell, v)
    local it = byid[cell]
    if it == nil then return nil end
    if it.toggle then
      if it.run then it.run() elseif it.adjust then it.adjust(1) end -- run and adjust both flip a toggle: only one is called
    elseif it.adjust then
      it.adjust(v)
    end
    after()
    return nil
  end
  local function back() menu_close() return nil end
  local function on_focus(cell)
    local i = tonumber(tostring(cell):match("r(%d+)$"))
    if i then menu.sel[menu.tab] = i end
  end
  local function on_tab(i)
    set_tab(i)
    register()
    UI.set_focus(SCREEN, "list", row_id(menu.tab, math.min(menu.sel[menu.tab] or 1, #shown)))
  end
  local function on_delete(cell)
    local it = byid[cell]
    if it == nil or it.state_row == nil then return nil end
    local row = it.state_row
    UI.dialog({
      title = "Delete state?", text = clip(row.name ~= "" and row.name or row.file, 60) .. " is removed from the library.",
      actions = { { "A", "Delete" }, { "B", "Keep" } },
      on = function(b) if b == "A" then lib_delete(row) after() end end,
    })
    return nil
  end

  register = function()
    local rows, map = rows_for(menu.tab)
    byid, shown = map, rows
    local names = {}
    for i, t in ipairs(TABS) do names[i] = { name = t.name } end
    UI.screen({
      id = SCREEN, chapter = 1, port = math.max(1, math.min(4, menu.port or 1)), backdrop = "world",
      trail = { "LAB", "PAUSE", title = TABS[menu.tab].name },
      tabs = names, tab = menu.tab,
      primary = { kind = "list", items = rows },
      explainer = { width = "wide", provide = explain },
      keys = {
        { "A", "Do it" }, { "B", "Resume" },
        { "Y", "Delete", when = function(c) local it = byid[c]; return it ~= nil and it.delete ~= nil end },
        { "L", "Page" }, { "R", "Page" }, { "START", "Resume" },
      },
      counter = function(c) local i = c and tonumber(c:match("r(%d+)$")) or 1 return i .. " / " .. #shown end,
      on = { accept = accept, back = back, start = back, change = change, tab = on_tab, focus = on_focus, alt = { Y = on_delete } },
    })
  end

  menu.ui.on = function() return opened end
  menu.ui.refresh = function() if opened then register() end end
  menu.ui.open = function(port)
    opened = false
    if not on or UI == nil or gd.match().netplay then return end -- the LAB is offline only: never an Atlas screen in a session
    local ok, why = UI.available()
    if not ok then gd.log("Geno Lab: the Atlas menu is not available (" .. tostring(why) .. "); using the old menu") return end
    state_page = 1
    opened = true
    local good, err = pcall(function()
      register()
      UI.open(SCREEN)
      UI.set_focus(SCREEN, "list", row_id(menu.tab, math.min(menu.sel[menu.tab] or 1, #shown)))
    end)
    if not good then
      opened = false
      gd.log("Geno Lab: the Atlas menu failed (" .. tostring(err) .. "); using the old menu")
    end
  end
  menu.ui.close = function()
    if opened then
      opened = false
      pcall(UI.close, SCREEN)
    end
  end
  menu.ui.set = function(word)
    if UI == nil then gd.log("lab ui: gd.ui is not available in this build") return end
    if word == "on" then on = true elseif word == "off" then on = false end
    gd.log("lab ui " .. (on and "on" or "off"))
  end
end)()
```

If a hook above names a Lab function that is declared **after** the mapper in the file (`mode`, `lib_delete`, `tab_items`, `set_tab` are all declared above `on_tick`; check with `luac -l`), move the mapper below that declaration, never the declaration.
- [ ] **Step 6: Run the checks.**

```bash
cd "$GW_MELEE" && lua pc/geno/tools/lab_stage_d_check.lua pc/geno/mods/geno-lab/scripts/lab.lua | grep -E "FAIL|PASS" | tail -30
bash "$WS/tools/port/lab_locals.sh" "$GW_MELEE/pc/geno/mods/geno-lab/scripts/lab.lua"
```

Expected: every old check still `PASS`; the new block `PASS` except the last one (the description lint), which lists the rows to shorten. The locals number equals the one you recorded.
- [ ] **Step 7: Shorten the descriptions the lint lists.** On 2026-10-06 `lab.lua` holds 71 string descriptions of which 14 are over 110 characters (2 over 159, which the engine would cut mid-sentence) and 11 description functions; run through the stubbed harness the check lists **18 rows** over the limit (the History, Hot reload, Save-to-library, Clean DI, Tech chase and Frame data export descriptions among them). The check prints each offender; rewrite each to one short rule that keeps its meaning. Two worked examples:
  - `"Every rollback as a bar (netplay, SyncTest, the fake network): how far, why, what it cost, and the first mismatch."` (114) becomes `"Every rollback as a bar: how far, why, what it cost, and the first mismatch."`.
  - `"On: the stick goes to the DI in two steps (just past the stick line, then full once the SDI ..."` (216) is two ideas: keep the first sentence in `desc` and move the rest to the `docs/geno.md` section that already describes it (14.13).
  Information that moves out of a description must still be somewhere the player can find it: say where in the commit message. Re-run Step 6 until the lint passes; the legacy menu shows the same shorter strings (that is intended: one text, two drawings).
- [ ] **Step 8: Commit.** Game repo: `pc/geno/mods/geno-lab/scripts/lab.lua`, `pc/geno/tools/lab_stage_d_check.lua`, message `geno-lab: the pause menu as an Atlas screen behind lab ui on (not run in the game; the legacy menu is unchanged and still the default)`. Workspace repo: `tools/port/lab_locals.sh`, message `tools: lab_locals.sh reports lab.lua's main-chunk locals`.

---

### Task 8: The LAB menu's edges: the library, other mods' tools, lifetime, ownership, online

Review Focus 5, 6, 7 and the states library. Tests first, in `lab_stage_d_check.lua`; the code they need follows.

**Files:**
- Modify (game repo): `pc/geno/mods/geno-lab/scripts/lab.lua`, `pc/geno/tools/lab_stage_d_check.lua`

**Gate:** Task 7 merged; Task 5f (`entries`, `activate`) merged for the mod-tools tab.

- [ ] **Step 1: Write the failing checks.** Insert these checks inside Task 7's block, directly above its closing `end` (the block's preamble defines `ui`, `SCREEN`, `upv`, `press`, `desc`, `rows`, `row`, `focus_on`, `closed`, `menu`, `TABS`, `resumed` and `left`; the harness file gets no new top-level local):

```lua
  -- ---- Task 8: the library, other mods' tools, lifetime, ownership, online ----

  lab("ui on")
  menu = upv(cmdfn, "menu")

  -- 1. the saved-state library is paged: 60 states do not fit a 32-row record
  local gen, lib_rows = 1, {}
  for i = 1, 60 do lib_rows[i] = { name = "State " .. i, file = "s" .. i, saved = "today", what = "Fox v Falco", ok = true, frame = i } end
  gd.state_gen = function() return gen end
  gd.state_list = function() return lib_rows end
  gd.state_delete = function(file)
    for i, r in ipairs(lib_rows) do if r.file == file then table.remove(lib_rows, i) gen = gen + 1 return true end end
    return false, "no such state"
  end
  lab("menu"); cmdfn("menu states")
  expect(#rows() <= 32 and row("Library page") ~= nil and row("Library page").value.text == "1 / 3", "STATES with 60 saved states: at most 32 rows and a page row reading 1 / 3")
  focus_on("Library page"); ui.engine_row(SCREEN, "right")
  expect(row("Library page").value.text == "2 / 3" and row("State 26") ~= nil and row("State 1") == nil, "right turns the page: the second page starts at state 26")
  ui.engine_row(SCREEN, "left"); ui.engine_row(SCREEN, "left")
  expect(row("Library page").value.text == "3 / 3", "and wraps round to the last page")
  ui.engine_row(SCREEN, "right")
  -- 2. delete: Y asks in a dialog, B keeps, A deletes, and the focus lands on a neighbour (never on nothing)
  focus_on("State 3")
  ui.engine_press(SCREEN, "y")
  expect(#ui.dialogs == 1 and ui.dialogs[1].actions[1][2] == "Delete", "Y on a saved state asks first, in a dialog")
  ui.dialogs[1].on("B")
  expect(#lib_rows == 60 and row("State 3") ~= nil, "B (Keep) deletes nothing")
  ui.engine_press(SCREEN, "y")
  ui.dialogs[#ui.dialogs].on("A")
  expect(#lib_rows == 59 and row("State 3") == nil, "A (Delete) removes it from the library")
  expect(ui.focus(SCREEN) ~= nil and (ui.focus(SCREEN) == row("State 4").id or ui.focus(SCREEN) == row("State 2").id), "the focus is on a neighbour after the delete")
  expect(ui.state().top == SCREEN, "the screen is still open")
  ui.engine_press(SCREEN, "y")                                       -- Y on a row that is not a saved state: nothing
  focus_on("Quick save"); local nd = #ui.dialogs; ui.engine_press(SCREEN, "y")
  expect(#ui.dialogs == nd, "Y on a row with no delete asks nothing")
  lab("menu close")

  -- 2b. an empty library is just the fixed rows
  lib_rows = {}; gen = gen + 1
  lab("menu"); cmdfn("menu states")
  expect(#rows() >= 4 and row("Library page") == nil, "no saved states: no page row")
  lab("menu close")

  -- 3. other mods' tools: entries under lab.pause appear as a tab, activating one is the registry's act
  lab("menu"); local n_tabs0 = #desc().tabs; lab("menu close")
  ui.add_entry({ parent = "lab.pause", id = "tools.extra", label = "Extra tool", blurb = "Does a thing.", mod = "tools" })
  lab("menu")
  local has_mods = false
  for _, t in ipairs(desc().tabs) do if t.name == "MODS" then has_mods = true end end
  expect(has_mods and #desc().tabs == n_tabs0 + 1, "an entry under lab.pause adds a MODS tab")
  cmdfn("menu mods"); focus_on("Extra tool"); press("accept")
  expect(ui.activated == "tools.extra", "A on the entry activates it through the registry")
  local e = desc().explainer.provide(row("Extra tool").id)
  expect(e and e.from.text == "tools", "the explainer's FROM names the mod that added it")
  lab("menu close")

  -- 4. ownership: the screen belongs to geno-lab; another script cannot touch it; the console bypass is not what the tests ran as
  lab("menu")
  expect(ui._owner[SCREEN] == "geno-lab" and ui.caller == "geno-lab", "these checks ran as the script geno-lab (not as the developer console)")
  lab("menu close")          -- another script touching this screen is the binding's rule, tested as a script in atlas_binding_test.c

  -- 5. the Atlas menu falls back when gd.ui is not available (fonts missing): the legacy menu opens instead
  ui.available_ok = false
  lab("menu")
  expect(menu.open and closed(), "gd.ui not available: the legacy menu opens and no screen is registered")
  lab("menu close"); ui.available_ok = true

  -- 6. offline only: online the menu does not open at all, and the Atlas path refuses even when called directly
  local real = gd.match
  gd.match = function() return { active = true, frame = now, netplay = true } end
  lab("menu")
  expect(not menu.open and closed(), "online: the LAB menu does not open")
  menu.ui.open(1)
  expect(closed(), "online: the Atlas path refuses to open")
  gd.match = real

  -- 7. a screen left open when the match ends is closed by on_match_start (a new match, a hot reload of the script)
  lab("menu")
  expect(ui.state().top == SCREEN, "open again")
  env.on_match_start()
  expect(closed() and not menu.open, "a new match closes a screen left open")
  -- 8. the script reloaded while a screen is registered: the new instance opens its own screen cleanly
  lab("menu"); chunk(); env.on_match_start()                        -- the reload re-registers the console command through gd.command
  lab("ui on"); lab("menu")
  expect(ui.state().top == SCREEN and #rows() >= 1, "after a reload the screen opens again from the new instance")
  lab("menu close"); lab("ui off")

```

(Checks 4 and 8 record what the stub can and cannot say: the stub does not release screens on a script unload, which is the engine's job and the binding test's.)
- [ ] **Step 2: Run to verify it fails.** Same command as Task 7 step 3. Expected: the library paging and the mod-tools checks fail (the first rows exist; the page row and the MODS tab do not yet).
- [ ] **Step 3: The mod-tools tab.** In the mapper's scope (Task 7 step 5), add before `menu.ui.on = ...`:

```lua
  -- other mods' tools: the entries registered under lab.pause become the rows of a MODS tab, added once when there are any
  local function mod_items()
    local out = {}
    local okl, list = pcall(UI.entries, "lab.pause")
    for _, e in ipairs(okl and list or {}) do
      local entry = e
      out[#out + 1] = {
        label = clip(entry.label, 40), desc = entry.blurb ~= "" and entry.blurb or "A tool added by another mod.", mod = entry.mod,
        run = function() UI.activate(entry.id) end,
      }
    end
    return out
  end
  local function ensure_mods_tab()
    if UI == nil or UI.entries == nil then return end
    for _, t in ipairs(TABS) do if t.name == "MODS" then return end end
    local okl, list = pcall(UI.entries, "lab.pause")
    if okl and #list > 0 then table.insert(TABS, #TABS, { name = "MODS", icon = "lab_modes", items = mod_items }) end
  end
```

call `ensure_mods_tab()` at the start of `menu.ui.open` (before `register()`), and in `explain` set `from = { text = it.mod or "Geno LAB" }`. A mod that registers its tool while the menu is open appears the next time it opens (the tab is added once; its rows are read each time).
- [ ] **Step 4: The library and delete** are already in the mapper (Task 7 step 5: `rows_for` pages, `on_delete` asks in a dialog). If a check in step 1 fails, the cause is almost always the focus after a re-register: `UI.set_focus` must be called with the id the **new** description has (the neighbour of the deleted row), so `after()` for a delete also does:

```lua
      on = function(b) if b == "A" then lib_delete(row) after(); UI.set_focus(SCREEN, "list", row_id(menu.tab, math.min(menu.sel[menu.tab] or 1, #shown))) end end,
```

- [ ] **Step 5: Run** the harness and `lab_locals.sh` as in Task 7 step 6. Expected: every check `PASS`, the locals number unchanged.
- [ ] **Step 6: Commit.** Game repo, message `geno-lab: the Atlas menu pages the saved-state library, asks before deleting, lists other mods' tools; lifetime, ownership and online checks (not run in the game)`.

---

### Task 9: The LAB HUD: info readout, move timeline, mode strip, notices

**Gate:** Task 0 exits 0 (N4, `gd.ui.hud`) and Task 6 is merged (the `readout` and `track` parts and their registration). The hud's shapes below are the contract of Task 6 and the assumed ones of step 3 (`strip`, `note`); every name outside Task 6 is `RECONCILE`. The checks run against the stub's hud, so a mismatch with step 3's real one fails loudly instead of silently drawing nothing.

What moves and what stays (spec 13.7): the **info panel** (`draw_info`, INSPECT's `I`), the **move timeline** (`draw_timeline`, FRAMES' `T`), the **mode strip** (`draw_strip`) and the **notices** (`say`, `draw_notice`) become descriptions. **Everything else keeps its primitive drawing** (hitboxes, skeleton, ECB, hit labels, the performance graph, the frame-advantage and move-card and input panels, the move browser, launch, A/B, the rollback strip, the help overlay, the event log, drill results): those are dev overlays, and the spec keeps them as they are. Their `panel()` helper loses its `lab_frame_*` art in Task 12 (retirement).

**Files:**
- Modify (game repo): `pc/geno/mods/geno-lab/scripts/lab.lua`, `pc/geno/tools/lab_stage_d_check.lua`

- [ ] **Step 1: Write the failing checks** (more checks in Task 7's block, above its closing `end`, after Task 8's). They drive the LAB in INSPECT and FRAMES with the stub hud and read what the LAB registered:

```lua
  -- ---- Task 9: the HUD ----

  lab("ui on")
  -- the harness's fake fighters carry only what the older checks read; the info readout reads the rest (the real game has them all)
  for i = 1, 2 do
    local q = P[i]
    for k, v in pairs({ anim_frame_f = 0, anim_rate = 1, vx = 0, vy = 0, kb_vx = 0, kb_vy = 0, jumps_max = 2, jumps_left = 2, walljumps_used = 0, ground_vel = 0,
                        hitlag = 0, hitstun = 0, kb_applied = 0, ledge_cooldown = 0, ecb_lock = 0, anim_name = "", intangible = 0, invincible = 0 }) do
      if q[k] == nil then q[k] = v end
    end
    q.ecb = q.ecb or { bottom = { y = 0 } }
  end
  local old_timeline = gd.timeline                                            -- the harness's timeline has no motion_name; the real one does
  gd.timeline = function(port, id) local tt = old_timeline(port, id); tt.motion_name = tt.motion_name or P[port].motion_name; return tt end
  local function hud() return ui.huds and ui.huds["geno-lab.hud"] end           -- RECONCILE: the stub's name for what gd.ui.hud last got
  local function zone(name) return hud() and hud().zones and hud().zones[name] or {} end
  local function part(zn, kind) for _, p in ipairs(zone(zn)) do if p.kind == kind then return p end end end
  local function tap(k) gd.key_pressed = function(x) return x == k end pcall(env.on_tick) gd.key_pressed = function() return false end end
  lab("mode inspect"); run(2)
  if not lab("status"):find("info=ON", 1, true) then tap("I") end
  pcall(env.on_tick)
  expect(hud() ~= nil, "in a LAB match the HUD is registered through gd.ui.hud")
  local info = part("top_left", "readout")
  expect(info ~= nil and #info.rows >= 9 and info.title:find("P1", 1, true) ~= nil, "INSPECT with I on: an info readout for the focused fighter")
  local labels = {}
  for _, r in ipairs(info.rows) do labels[r.label] = r.value end
  expect(labels["Motion"] ~= nil and labels["Position"] ~= nil and labels["Hitlag"] ~= nil and labels["Shield"] ~= nil, "the readout has the info panel's fields as label and value rows")
  for _, r in ipairs(info.rows) do expect(#r.label <= 23 and #r.value <= 39, "readout row fits its fields: " .. r.label) end
  local second = zone("top_left")[2]
  expect(second ~= nil and second.kind == "readout" and second.title:find("P2", 1, true) ~= nil, "a second readout for the other fighter")
  lab("mode frames"); run(2)
  if not lab("status"):find("timeline=ON", 1, true) then tap("T") end
  pcall(env.on_tick)
  local tl = part("bottom_center", "track")
  expect(tl ~= nil and tl.len >= 1 and tl.now >= 1 and tl.now <= tl.len, "FRAMES with T on: a timeline track for the focused fighter, the playhead inside the move")
  expect(type(tl.spans) == "table" and type(tl.marks) == "table" and tl.right:find("f ", 1, true) ~= nil, "windows, marks and the 'f n / len' text")
  local strip = part("bottom_left", "strip")
  expect(strip ~= nil and #strip.items >= 2, "the mode strip: the mode and its toggles")
  expect(strip.items[1].text == "FRAMES", "the first chip names the mode (a word, not a colour)")
  -- a notice is a corner note for its two seconds, then gone
  gd.time = function() return now / 60 end
  gd.hot_reload_status = function() return { text = "ok" } end
  env.on_hot_reload(true); pcall(env.on_tick)                       -- on_hot_reload calls say("Reloaded: ok")
  local note = part("top_right", "note")
  expect(note ~= nil and note.text == "Reloaded: ok" and note.note_kind == "ok", "say() shows a corner note")
  now = now + 600; pcall(env.on_tick)
  expect(part("top_right", "note") == nil, "and it is gone after its time")
  -- the menu open: the HUD is cleared (the pause screen is the only thing drawn)
  lab("menu"); pcall(env.on_tick)
  expect(#zone("top_left") == 0 and #zone("bottom_center") == 0, "with the pause menu open the HUD is empty")
  lab("menu close")
  -- hidden or off: nothing
  lab("hide"); pcall(env.on_tick)
  expect(#zone("top_left") == 0 and #zone("bottom_left") == 0, "Lab UI hidden: no HUD parts")
  lab("hide")
  -- online or outside a LAB match: no HUD
  local real = gd.match
  gd.match = function() return { active = true, frame = now, netplay = true } end
  pcall(env.on_tick)
  expect(#zone("top_left") == 0 and #zone("bottom_left") == 0, "online: the Lab draws no HUD")
  gd.match = real
  -- the budget: building the HUD every tick stays small
  local t0 = os.clock()
  for _ = 1, 200 do pcall(env.on_tick) end
  expect((os.clock() - t0) / 200 < 0.002, string.format("a HUD rebuild is under 2 ms of Lua (%.3f ms)", (os.clock() - t0) / 200 * 1000))
  gd.timeline = old_timeline
  lab("ui off"); lab("mode training")

```

- [ ] **Step 2: Run to verify it fails.** Expected: `hud() ~= nil` fails first (nothing registers a HUD).
- [ ] **Step 3: The HUD builder.** In the mapper's scope, add (after `mod_items`, before the `menu.ui.*` assignments):

```lua
  -- ---- the HUD (menu closed): info readouts, the timeline, the mode strip, a notice ----------------------------------------
  local HUD = "geno-lab.hud"
  local hud_was_empty = false
  local function tone(c) -- the Lab's own colours mean: gold = something is active, OK = good, DANGER = bad; map them to the readout's tones
    if c == GOLD then return "warn" elseif c == OK then return "ok" elseif c == DANGER then return "bad" end
    return nil
  end
  local function info_rows(p)
    local r = {}
    local function add(label, value, c) r[#r + 1] = { label = label, value = clip(value, 39), tone = tone(c) } end
    add("Motion", string.format("%s  f%d", p.motion_name, p.action_frame + 1))
    add("Action", string.format("%d  anim %s %.1f x%.2f", p.action, p.anim_name ~= "" and p.anim_name or "-", p.anim_frame_f, p.anim_rate))
    add("Position", string.format("%s %s  %s", f2(p.x), f2(p.y), p.airborne and "air" or "ground"))
    add("Velocity", string.format("%s %s", f2(p.vx), f2(p.vy)))
    add("Knockback v", string.format("%s %s", f2(p.kb_vx), f2(p.kb_vy)))
    add("Jumps", string.format("%d/%d  wj %d", p.jumps_left, p.jumps_max, p.walljumps_used))
    add("Ground vel", f2(p.ground_vel))
    add("Hitlag", string.format("%.0f", p.hitlag), p.in_hitlag and GOLD or nil)
    add("Hitstun", string.format("%.0f  kb %.1f", p.hitstun, p.kb_applied), p.in_hitstun and GOLD or nil)
    add("Intangible", string.format("%d  invinc %d", p.intangible, p.invincible), (p.intangible > 0 or p.invincible > 0) and OK or nil)
    add("Body", p.body_state, p.body_state ~= "normal" and OK or nil)
    add("Shield", string.format("%.1f", p.shield))
    add("IASA", p.iasa and "yes" or "no", p.iasa and OK or nil)
    add("Ledge cd", tostring(p.ledge_cooldown))
    add("ECB bottom", string.format("%s  lock %d", f2(p.ecb.bottom.y), p.ecb_lock))
    return r
  end
  local MARK_KIND = { iasa = "iasa", invinc = "invinc", gfx = "gfx", sfx = "sfx", vis = "vis" }
  local function track_of(p, is_focus)
    local c = timeline_of(p)
    if c == nil then return nil end
    local spans, marks, parts, iasa = {}, {}, {}, nil
    for _, hw in ipairs(c.windows) do
      if #spans < 16 then spans[#spans + 1] = { from = hw.from, to = hw.to, id = hw.id } end
      parts[#parts + 1] = string.format("f%d-%d #%d %d%% a%d", hw.from, hw.to, hw.id, hw.dmg, hw.angle)
    end
    for _, e in ipairs(c.marks) do
      if e.name == "iasa" then iasa = e.frame end
      local k = MARK_TEX[e.name] or (e.name:find("sfx") and "sfx")
      if k and MARK_KIND[k] and #marks < 24 then marks[#marks + 1] = { frame = e.frame, kind = MARK_KIND[k] } end
    end
    local len = math.max(c.len, 1)
    local now_f = math.floor(p.anim_frame_f + 1)
    return {
      kind = "track", title = clip(fighter_name(p.port) .. "  " .. tostring(c.tl.motion_name or "") .. (c.tl.conditional and " [conditional]" or ""), 63),
      right = string.format("f %d / %d%s", now_f, len, iasa and ("   IASA " .. iasa) or ""),
      len = len, now = math.max(1, math.min(len, now_f)), spans = spans, marks = marks, note = clip(table.concat(parts, "   "), 63),
    }
  end
  local function strip_of()
    local md, items = mode(), {}
    items[1] = { text = md.name, tone = gd.paused() and "warn" or "ok" }
    for _, t in ipairs(md.t) do items[#items + 1] = { text = t.k .. " " .. t.label, on = T(t.id) and true or false } end
    for _, a in ipairs(md.a) do items[#items + 1] = { text = a.k .. " " .. a.label, on = a.state and STATES[a.state]() or nil } end
    local h = gd.history()
    local right = string.format("f %d  %s", gd.match().frame, h.replaying and string.format("REPLAY +%s s", secs(h.fwd)) or string.format("rewind %s s", secs(h.back)))
    return { kind = "strip", items = items, right = right }
  end
  menu.ui.hud_tick = function()
    if UI == nil or UI.hud == nil or not on then return end
    local live = cfg.on and not cfg.hidden and not menu.open and gd.match().active and not gd.match().netplay
    if not live then
      if not hud_was_empty then UI.hud({ id = HUD, zones = {} }) hud_was_empty = true end
      return
    end
    hud_was_empty = false
    local list = gd.players()
    local z = { top_left = {}, bottom_center = {}, bottom_left = { strip_of() }, top_right = {} }
    local md = mode()
    if md.id == "inspect" and T("info") then
      for i, p in ipairs(focus_first(list, 2)) do
        z.top_left[i] = { kind = "readout", title = fighter_name(p.port), rows = info_rows(p), cols = 1 }
      end
    end
    if md.id == "frames" and T("timeline") then
      local a = gd.player(focus)
      if a then
        local t = track_of(a, true)
        if t then z.bottom_center[#z.bottom_center + 1] = t end
      end
    end
    if notice and gd.time() < notice_until then
      z.top_right[1] = { kind = "note", text = clip(notice[1], 63), note_kind = notice[2] == DANGER and "err" or "ok" }
    end
    UI.hud({ id = HUD, zones = z })
  end
  menu.ui.hud_on = function() return on and UI ~= nil and UI.hud ~= nil end
```

The note part's key for its colour is assumed `kind`; the table above uses `note_kind` only because `kind` is already the part's type: **reconcile this with step 3** (its `note{}` may take `tone`) and keep the stub test's `note.note_kind == "ok"` consistent with whichever name step 3 uses. `info_rows`, `track_of`, `strip_of` read only what the legacy `info_lines`, `draw_timeline` and `draw_strip` read (`p` fields, `timeline_of`, `mode()`, `T()`, `STATES`, `gd.history()`), so no number is typed in.
- [ ] **Step 4: Switch the legacy drawing off for these four things when the Atlas HUD is on.** (a) In `on_tick`, first line: `if menu.ui.hud_tick then local okh, errh = pcall(menu.ui.hud_tick) if not okh and not menu.ui.hud_failed then menu.ui.hud_failed = true gd.log("Geno Lab: the HUD failed: " .. tostring(errh)) end end` (a failing HUD must not stop the tick, and must not fail silently: it says so once). (b) In `on_draw`, `if id == "inspect" then if T("info") then draw_info(list) end` becomes `if T("info") and not (menu.ui.hud_on and menu.ui.hud_on()) then draw_info(list) end`. (c) In `draw_frames`, `if not T("timeline") then return end` becomes `if not T("timeline") or (menu.ui.hud_on and menu.ui.hud_on()) then return end` (the action chip and the rollback strip above it stay). (d) At the `draw_strip()` call and in `draw_notice()`: return at once when `menu.ui.hud_on and menu.ui.hud_on()`.
- [ ] **Step 5: Run** the harness and `lab_locals.sh`. Expected: every check `PASS`; locals unchanged. The budget check measures only the Lua side (the harness has no engine): the engine side is Task 11's `gd.ui.state().cost_ms`.
- [ ] **Step 6: Commit.** Game repo, message `geno-lab: the info panel, the move timeline, the mode strip and the notices as HUD descriptions behind lab ui on (not run in the game)`.

---

### Task 10: Documentation

**Files:**
- Modify (workspace repo): `docs/scripting.md`, `docs/mods-packaging.md`, `docs/TERMINOLOGY.md`, `docs/NEXT-SESSION.md`
- Modify (game repo): `docs/geno.md` (the file the workspace calls `melee/docs/geno.md`), `pc/geno/mods/geno-lab/CLAUDE.md`

- [ ] **Step 1: The scripting reference** (`docs/scripting.md`, the `gd.ui` section). Add, each in the style of the rows already there: the `stepper` value (`{ kind = "stepper", text }`: left and right call `on.change(id, -1 or 1)`, A calls `on.accept`; the engine does not change the text, re-register); `backdrop = "ground" | "world"` (world: a translucent scrim over the frozen game instead of the ground; the open ramp is the same; the end fade is skipped); the explainer's `with = { tags = { "B Boxes", ... } }` (at most 4, each at most 19 characters, drawn as tags under WITH; an explainer with no `media.model` has no media well); `tabs = { { name, count? }, ... }` with `tab` (1-based) and `on.tab(index)` (called on L, R, Tab and Shift+Tab; the script re-registers; the engine does not choose a tab's content; `on.page` is called only when the screen has no tabs); `gd.ui.token(name)` (a colour token as `0xRRGGBBAA`, or nil); `gd.ui.entries(parent)` and `gd.ui.activate(entry_id)` (only for a parent the caller owns; `lab.pause` belongs to the LAB; entries come back already filtered by the registry's visibility rules; `activate` is the registry opening the entry's screen or running its `on_entry` under its own mod); and the HUD parts `readout` and `track` with their field tables from Task 6 and their limits (16 rows, 16 spans, 24 marks, a row's label 23 and value 39 characters). Update the stub paragraph's "it is NOT the engine" list with what the stub now models (stepper, tabs, backdrop validation, tokens, entries) and what it still does not.
- [ ] **Step 2: The manifest** (`docs/mods-packaging.md`). Where it describes `Settings > Mods`, describe the Atlas MODS screen instead (INSTALLED and CONFLICTS tabs, A or left or right to toggle, X to resolve, Y for details, "Applies at restart", up to 256 mods; the old page showed only the first 40). In the manifest section, once step 2 has documented `menus`, add the two things step 7 owns: the built-in parent `mods.self`, which the registry rewrites to `mods.<the mod's id>`, puts an entry in that mod's detail screen (a mod's own settings are a screen it registers; the Mods screen only links to it), and the built-in parent `lab.pause`, which adds a row to the LAB's MODS tab (offline only). If step 2's document is not merged yet, add these as a short "Menu entries (step 7)" section and say so.
- [ ] **Step 3: The terms** (`docs/TERMINOLOGY.md`; check the file first, its rule). Add: **stepper** (a list value that changes with left and right and runs with A), **readout** and **track** (the two read-only HUD parts), **world backdrop**, **MODS screen** and **mod detail**, **lab.pause** and **mods.self** (the two built-in entry parents step 7 adds). Keep "Atlas" bare for the system.
- [ ] **Step 4: The LAB** (`docs/geno.md` section 14.9, the pause menu). Replace the description of the pause menu's drawing with the Atlas one: what is the same (`TABS`, the rows, the keys START and ESC to open, the freeze, the offline-only rule), what changed (tabs by L and R, Tab and Shift+Tab; **Q and E no longer change tabs in the Atlas menu** (letters stay free for hotkeys, spec 9); DELETE is Y; B resumes; a dialog before a state is deleted; the library is paged by 25), `lab ui on|off` and that off is the default until the owner has looked, and the HUD parts. Say what was verified and how: the Lua checks in `lab_stage_d_check.lua`, and **that the Atlas menu has not run in the game unless the in-game proof (Task 11) was done** (name the date and the exe when it was). In `geno-lab/CLAUDE.md` add to "How lab.lua is organised": the mapper lives in one function scope before `on_tick` and reaches the rest through `menu.ui`; no top-level local may be added; `tools/port/lab_locals.sh` reports the count; and to "Before committing": run `lab_locals.sh` and expect the number not to rise.
- [ ] **Step 5: The state** (`docs/NEXT-SESSION.md`). One dated line for step 7: built, behind which switch, what the owner must look at (Task 11), what is not retired (Task 12), the two spec corrections (the LAB has ten modes; step 7 needs step 3). Replace stale prose rather than appending an update.
- [ ] **Step 6: Commit.** Workspace repo: `docs/scripting.md`, `docs/mods-packaging.md`, `docs/TERMINOLOGY.md`, `docs/NEXT-SESSION.md`, message `docs: Atlas step 7 (stepper, tabs, backdrop, tokens, entries, HUD parts; the MODS screen; the LAB menu)`. Game repo: `docs/geno.md`, `pc/geno/mods/geno-lab/CLAUDE.md`, message `docs: the LAB pause menu in Atlas (geno.md 14.9, geno-lab CLAUDE.md)`.

---

### Task 11: The in-game proof (a checklist for a Windows agent or the owner)

**Nothing before this task proves a screen in the game.** Tasks 1 to 10 prove the model, the parts against a recording sink, the Lua contract against a stand-in, the LAB's rows through the harness, and that the exe contains the new code. They do not prove that the quads look right, that a real folder behaves, that the pause over a frozen match is readable, that the HUD stays off the retail HUD, or that the cost is acceptable.

**Who and when.** Only when the owner is away, or let him do it: a game window steals focus. Window on the **second monitor** (`MELEE_WINDOW_X` / `MELEE_WINDOW_Y`; ask the coordinator for the position), `MELEE_VOLUME=0`, never hidden or minimised. Stop the game by closing its window or by the PID you started; **never by image name**. At most 8 `melee-pc` in total, 2 GB free. Test with the **ACE** disc (the owner's standing rule) and once on vanilla. Use the **LAB**, not Training, with `cpus=idle`. No screenshots as proof (one is allowed to diagnose how something looks; the overlay is left out of `gd.screenshot`: use an OS window capture).

- [ ] **Step 1: Build in your private worktree and confirm the exe.**

```bash
tools/port/build.sh
for s in "mods.detail" "Applies at restart" "geno-lab.pause" "Delete state?" "Library page"; do grep -a "$s" "$GW_BUILD_ROOT/melee-pc.exe" | head -1; done
```

Expected: a linked exe and a line for each string (a stale exe prints nothing: root `CLAUDE.md` fact 1; the LAB's strings live in `lab.lua`, so check the mod folder instead for the last three: `grep -c "Library page" pc/geno/mods/geno-lab/scripts/lab.lua`).
- [ ] **Step 2: A real mods folder, and a big synthetic one (no disc data).** Make a scratch folder of 120 mods of nothing but `mod.json` files, so the windowing is seen with more than the old page's 40:

```bash
D="$MAIN/_build/runs/atlas7-mods"; mkdir -p "$D"
for i in $(seq -w 1 120); do mkdir -p "$D/mod-$i"; printf '{"id":"mod-%s","name":"Fighter Number %s","kind":"misc","description":"A fixture mod."}' "$i" "$i" > "$D/mod-$i/mod.json"; done
MELEE_VOLUME=0 MELEE_MODS_DIR="$D" tools/port/run.sh atlas7-proof --iso "$GW_ISO_VANILLA"
```

Main menu, Mods (or Settings, Mods). Look at, and write down yes or no for each:
  1. The MODS screen is the Atlas one (tabs `INSTALLED 120` and `CONFLICTS 0`, rows with a toggle, a sub line, the explainer, the counter `1 / 120`), not the old list.
  2. D-pad down walks all 120 without the focus ever leaving the screen or landing on a wrong mod; at the bottom it wraps; the wheel scrolls; hover focuses and a pointer at rest does not steal focus from the pad.
  3. A, left and right toggle the focused mod; the corner note says `Fighter Number 007 on. Applies at restart.`; the standing note `Applies at restart` stays; `mods/enabled.txt` in the folder changed. Restart the game with the same folder: the toggles are what you left.
  4. The old page is gone from Settings (or, with `MELEE_ATLAS=0`, is back and shows only 40).
  5. 4:3 (`MELEE_WINDOW_W=960 MELEE_WINDOW_H=720`), 640x480 and 16:9 (`1920 x 1080`): every string legible, nothing outside its row, the wide arrangement has the rail and a wider explainer.
  6. With your own mods folder (ACE and Envoy if you have them): a conflict shows the `CONFLICTS` tab with the pair; X on the dropped mod turns it off and says so; a mod with a missing requirement says `needs <id>`; Y opens the detail with Requires, Conflicts (both ways), `Adds to the menus` (`Solo > Envoy`) and, for Envoy, its own settings row if its manifest has one; A on that row opens the mod's screen; B comes back to the same row.
  7. Reduced Motion on (Settings): the screen opens as a cut.
- [ ] **Step 3: The LAB.** Launch the LAB, then use the console (backtick):

```bash
MELEE_VOLUME=0 MELEE_WINDOW_X=<x> MELEE_WINDOW_Y=<y> MELEE_SCENE="mode=lab;stage=fd;p1=fox/hu;p2=falco/cpu0;cpus=idle" tools/port/run.sh atlas7-lab --iso "$GW_ISO_VANILLA"
```

`lab ui on`, then START. Look at, and write down yes or no for each:
  1. The pause menu is the Atlas one **over the frozen fight** (the stage and fighters visible and dimmed; plates over them), tabs PLAY DISPLAY DUMMY STATES TOOLS DRILLS EXIT, the trail `LAB > PAUSE > PLAY`, key hints, counter `1 / n`. Held START does not close it at once.
  2. L and R (and Tab and Shift+Tab) change tabs; each tab remembers its row; hover and click work; the explainer shows the focused row's text in at most three lines and a `FROM Geno LAB` tag; DISPLAY's first row lists the mode's keys as tags.
  3. Rows behave as in the old menu: Resume resumes; Step +1 steps one frame; Focus changes with left and right **and** A; the DISPLAY toggles flip once per press; Damage steps with left and right and applies with A; Fly toggles; History and Hot reload step with left and right. Write down any row that does something different from the old menu (`lab ui off`, same row).
  4. STATES: Save to library, Quick save, Quick load, Reset positions. Save 30 states (A on `Save to library` 30 times) and see the `Library page 1 / 2` row; left and right turn the page; Y on a state asks in a dialog; B keeps it, A deletes it and the focus lands on a neighbour; A on a state loads it. Delete the test states afterwards.
  5. DRILLS: start a drill from the new menu; it starts and the menu closes. TOOLS: the frame-data export still starts. EXIT: Change fighters and Quit leave the LAB and close the screen.
  6. B and START resume; the game continues from the same frame; a press of START right after closing does not pause again by itself. ESC opens the menu on the keyboard.
  7. `lab ui off`: the old menu is back, byte for byte as before.
  8. **The HUD.** `lab mode inspect` with `I` on: the info readouts at the top left (two, focused fighter first) with the same fields as before; `lab mode frames` with `T` on: the timeline at the bottom with a hit window per window and the id numbers on them. At 4:3 and at 16:9: **neither overlaps the retail damage plates, the match timer or the stock icons** (write down any overlap with its position and the window size). The mode strip shows the mode and its toggles; a notice (`Quick save`) shows as a corner note and goes after about two seconds.
  9. Cost: with the pause open, then in FRAMES mode with the timeline, `= gd.ui.state().cost_ms` and `.cost_max_ms` and `.quads` (record them; the target is at most 0.5 ms and under 3,000 quads), and the FPS readout at `MELEE_FPS=120` (Settings > Video > Show FPS): it must hold 120.
  10. **Offline only:** there is no way to open a LAB match online; confirm the console line `lab menu` outside a LAB match answers `the LAB menu is for LAB matches` and registers no screen (`= gd.ui.state().depth` is 0).
  11. A mod's tool under `lab.pause`: drop a one-entry fixture mod whose `mod.json` has a `menus` entry with parent `lab.pause` into the mods folder (a `scripts/` file is not needed to see the row), restart, open the menu: a `MODS` tab with the row appears; A on it does what the entry says; the explainer's FROM names the mod.
- [ ] **Step 4: Capture and report.** Save `"$GW_BUILD_ROOT/runs/atlas7-proof/melee-pc.log"` and `.../atlas7-lab/melee-pc.log` lines with `ui:` and `mods:`, and any `Geno Lab:` or `[lab]` error; the numbers from step 3.9; a yes or no for every numbered item with one line for each no; say plainly which items were not run and why. The owner decides whether the look is accepted. **Do not do Task 12 in the same session.**

---

### Task 12: Retire the legacy pieces (a follow-up, after the owner's look)

Not part of the first pass, and not in the same session as Task 11. Spec 13.7 retires the LAB's own palette, `lab_frame_*`, the `ico_lab_*` art that Atlas icons replace, the chip and strip drawing, and `Settings > Mods`.

- [ ] **Step 1: The Settings page.** Delete the Mods page from `gmfrontend_settings.inc` (`FSM_MAX`, `fe_items_set_mods`, the `FSM_ROW` and `FSM_P` macro tables, `fsm_fill`, `fsm_fmt_state`, `fsm_toggle`, the `FSP_MODS` enum value and its table entry) and the `FA_PAGE` fallback row; remove the `page == FSP_MODS` call in `gmfrontend.c`. Run the PowerPC syntax check and the build. (About 100 lines, among them three function-pointer tables of 40 entries each, which is also the cap the Atlas screen lifts.)
- [ ] **Step 2: The LAB's legacy menu.** In `lab.lua` delete `lab_menu_draw`, `menu.hits`, `menu_hit`, the mouse block of `lab_menu_tick` and its key handling, `menu.t`, `menu.tab_t`, `menu.sel_t`, the tab wipe, and the `menu.ui` indirection where the Atlas path becomes the only one (keep the freeze, `ensure_history`, the input neutralising and `in_lab_match` in `menu_open` and `menu_close`). Make `lab ui` default on, then remove the switch. Remove the legacy menu's checks from `lab_stage_d_check.lua` (the wide-draw and footer checks name `lab_solid` and the footer text) and keep every other check.
- [ ] **Step 3: The HUD's legacy drawing.** Delete `draw_info`, the timeline half of `draw_frames`, `draw_strip` and `draw_notice` and their call sites once the HUD is the only path.
- [ ] **Step 4: The panel art and the palette.** `panel()` (the helper the dev overlays still call) loses its `lab_frame` 9-slice: draw it flat from `gd.ui.token` colours (plate, front edge): **square corners, because `gd.kit` has no polygon**; this is the spec's own fallback for plates, and the dev overlays are explicitly not held to the chamfer rule. Delete the `lab_frame_*` names from `PRELOAD_ICONS` (the list near `on_draw`), the generator code and pieces for `lab_frame_*` and `lab_chip_*` in `art/lab_art.py`, `art/lab_palette.py` (replace the palette constants at the top of `lab.lua` by `gd.ui.token(...)` values, in the same `local INK, BONE, ...` statements, adding no local), `art/lab_style.css` where nothing else reads it, and `ui/lab_frame_*.gxtex`, `ui/lab_chip_*.gxtex`. **Keep `ico_lab_*`**: Atlas has no icon set yet (step 1 gap 2), and the mode strip's key chips and the dev overlays still draw them; retire them in the step that builds the icon set.
- [ ] **Step 5: Verify** with the build, the nine native tests of step 1, `atlas-mods`, `atlas-mods-door`, `atlas-hud-parts`, the stub test, `lab_stage_d_check.lua`, `lab_locals.sh` (the number must have gone **down**), and Task 11's steps 2.1, 2.3, 3.1, 3.4 and 3.8 again. Commit in both repos.

---

## Self-review

**Spec coverage (13.7).**

| 13.7 item | Where |
|---|---|
| MODS (replacing `Settings > Mods`): installed, conflicts, applies at next start, one row per mod with kind and "adds" lines | Tasks 1 (rows, tabs, windowing, toggles, conflicts, the restart note, `adds` from the registry), 3 (real accessors), 4 (the entry), Task 12 step 1 (the page is deleted after the look) |
| Mods adding menu entries | `adds` lines come from the registry (Task 3 `r_adds`); entries under `lab.pause` become a LAB tab (Task 8); the registry itself is step 2's |
| Per-mod settings | Task 2: the `mods.self` parent, the detail row, the hand-off to the mod's own registered screen (spec 14: no generated pages) |
| Conflicts | Task 1 (the CONFLICTS tab, X to resolve, the cascade note), Task 2 (both directions), Task 3 (`gw_Mods_Conflicts`) |
| LAB pause tabs PLAY, DISPLAY, DUMMY, STATES, TOOLS, DRILLS, EXIT | Task 7 (the same `TABS` rows, one mapper) |
| The info panel, the move timeline, the states library (as descriptions), the mode strip as corner notes | Tasks 6 and 9 (readout, track, strip, note), 7 and 8 (the paged library with its dialog) |
| Dev overlays stay primitive `gd.kit` | Task 9 (the list of what stays) |
| Delivers: `lab.pause` parent; the 6 modes' toggles as list items with value widgets | Task 8 (the MODS tab), Task 7 (DISPLAY's toggles as toggle widgets; the mode count is ten, not six) |
| Retired: `lab_palette.py`, `lab_frame_*`, `ico_lab_*` that Atlas replaces, the chip and strip drawing, `Settings > Mods` | Task 12; **`ico_lab_*` is kept** until an icon set exists |
| Verified without the game: `lab_stage_d_check.lua` still passes; the Lua stub test of the LAB's descriptions; main-chunk local count under 200; the mods screen against a fixture folder including a conflict | Tasks 7 to 9 (the harness), `lab_locals.sh`, Task 1 (fake source with the real cascade rules), Task 3 step 7 (the fixture folder through the real resolver) |
| Must be seen: the LAB in a fight with the pause open, states saved and loaded, the info panel while paused; the mods list with a real folder and restart note; offline-only unchanged | Task 11 |

**Gaps and deviations the engineer and the coordinator should know about.**
1. **Q and E no longer change tabs in the Atlas LAB menu**, and DELETE is Y: the spec keeps letters free for hotkeys. The old menu keeps them behind `lab ui off`.
2. **Row icons are gone in the Atlas menu** (no icon set); the `ico_lab_*` files stay.
3. **The Atlas LAB menu is off by default** (`lab ui on` per session) until the owner has looked; it does not persist across a script reload.
4. **Rows are data, rebuilt on every action** (step 1's values are data: re-registering is the invalidation). A row whose value changes while the menu is open without an action (none today: the game is frozen) would not update.
5. **`lab.pause` and the owner rule for `gd.ui.entries` / `activate`** are this plan's proposals beyond the spec (without the rule any mod could trigger another's entries).
6. **The HUD refresh is a rebuild every script tick**, not a `get` the engine reads: step 1 has no live values for Lua. If the in-game cost is too high, the fix is step 3's native `port_card`-style readbacks, not a cache here.
7. **Explainer limits:** the spec's one short rule is 110 characters; the LAB had 14 string descriptions and some function descriptions over it. They are shortened (the information that moved is named in the commit).
8. **Names assumed from unbuilt steps:** the tab fields (step 5), the registry and the native door (step 2), the hud, its zones and its `strip` and `note` shapes (step 3). Each sits behind one wrapper or one stub field, and Task 0's gate fails until the real name is written in.
9. **The 40-mod cap of the old page** is a finding, not a goal: the Atlas screen holds 256 (`GW_MODS_MAX`) and warns nowhere about more because the registry cannot hold more.
10. **Mods screen online:** reachable and allowed; its only write is `enabled.txt` for the next boot. If the owner wants it hidden during a session, that is one line in step 2's registry rule.

**Placeholder scan.** No step defers a decision or refers to another task instead of showing its code. Where an unbuilt step's name is unknown the task says `RECONCILE`, shows code against an assumed name, and the gate fails until the real name is in. The second-monitor position is asked of the coordinator, as in steps 1 and 6. Line numbers into existing files are given as quoted text to find.

**Type and name consistency.** `AtModsSrc`, `AtModsState`, `AtModsAction`, `AtModsDetail` and the `AT_MOD_*` and `AT_MA_*` enums (Tasks 1 and 2) are used unchanged by the door (Task 3); `AT_VAL_STEPPER`, `AT_BD_WORLD`, `AtExplainer.n_tags/with_tag`, `AtScreen.fn_tab/tab0` (Task 5) by the mapper's description keys (`stepper`, `backdrop = "world"`, `with.tags`, `tabs`, `tab`, `on.tab`); `AtReadout` and `AtTrack` and their Lua tables (Task 6) by Task 9's builders; the screen id `geno-lab.pause` and the HUD id `geno-lab.hud` are the same in the mapper, the checks and the docs; `menu.ui.open/close/on/refresh/set/hud_tick/hud_on` are the names the hooks in Task 7 step 4 and the checks use.

**Review Focus pinned.** 1 (cascades, failed save): Task 1 `cascade`. 2 (focus and windowing): Task 1 `window_walk` and `conflicts`. 3 (overflow): Task 1 `long_strings`, Task 7 check 10. 4 (a row loses or doubles a handler): Task 7 checks 4 and 5. 5 (as the console): Task 5's `gs.cur = 1` binding checks, Task 8 check 4, and the stub owner. 6 (focus after re-register): Task 7 check 6, Task 8 check 2. 7 (online, reload, leave): Task 8 checks 6 to 8, Task 7 check 8. 8 (close effects): Task 7 check 7. 9 (style): Task 6 lint. 10 (HUD on the retail HUD): Task 6 step 5 and Task 11 step 3.8.

**Execution recommendation.** Tasks 1 and 2 are self-contained and pure: a fresh agent each with a review between. Tasks 3 and 4 touch retargeted game code and the build: one agent. Task 5 is six small independent sub-steps: one agent in order, each its own commit, skipping what the gate did not list. Task 6 is pure C with a clear test: a fresh agent. Tasks 7, 8 and 9 share `lab.lua` and one mental model of its upvalues and its 200-local limit: **one agent, in order**, running `lab_locals.sh` after every edit. Task 10 is small and can go to a fresh agent. Task 11 is for a Windows agent while the owner is away, or for him; Task 12 waits for his look.
