# Atlas step 5: settings and the remap editor: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw every Settings page (VIDEO, AUDIO, CONTROLS with its how-to and the remap editor, ONLINE, GAMEPLAY and, until step 7 replaces it, MODS) as tabs of one Atlas screen, add the retail Rumble, Screen Display and Erase Data rows to those pages, keep Language a native hand-off, and give the engine the value model these pages need and step 1 did not build (a slider `step`, live values, engine-owned choices, group headings, text rows, a confirm dialog fed by native code). The existing tables (`FrontendItem` arrays) and the existing capture state of the remap editor stay where they are; the Atlas screen is a **drawing and input layer over them**.

**Architecture:** (1) Engine additions in the step 1 record, pure C and testable with no game: value rows (`step`, options, readout, group, reason), the rule that applies a Left, Right or A to a row (`at_item_apply`, moved from `fe_change`), tabs (shared with step 4). (2) Lua parity for the same value model, as small as possible (`step`, `gd.ui.set_value`/`value`), so the LAB (step 7) and mods are not left behind. (3) The game-side adapter's table walker, extended: it turns a `FrontendScreen` into one tab of the Atlas screen each frame, evaluates `get`, `visible`, `enabled` and `format` on the game side and submits scalars and strings, and applies the events the host returns (`set`, `call`, tab, back). (4) The pages, one table test each through a **stub adapter** that needs no game. (5) The retail rows, with the erase calls split out of the retail screen's animation code. (6) The remap editor as an Atlas screen over the unchanged `Controls_*` API, with its capture freeze and its per-frame heartbeat preserved and pinned by tests.

**Tech Stack:** C11 host code (`tools/port/native_test.sh`), game-side C (PowerPC syntax check), Lua 5.4 (the stub and the binding contract), Python 3 (inventory and static guards).

**Spec:** `docs/superpowers/specs/2026-10-06-menu-reunification-design.md`, section 13.5 (this step), sections 4, 6.7, 7, 9 and 10. What exists: the step 1 plan `docs/superpowers/plans/2026-10-06-atlas-step1-components-and-envoy-bag.md`, `docs/scripting.md` "Atlas screens (`gd.ui`)" and its last line, "Not in step 1: tabs in the screen record, a slider `step`, a get/set API for values (values are data, re-registered), and mouse-wheel stepping of a value"; this plan builds the last three and shares the first with step 4 (`docs/superpowers/plans/2026-10-06-atlas-step4-select-screens.md`).

> **Nothing in this plan was compiled or run when it was written.** Code blocks are designs in code, read against the sources named; each test is written to fail first. Facts not read from source are marked **(unverified)** with the step that settles them.

## What this step needs from other steps (gates)

| # | Needs | From | Tasks that wait for it |
|---|---|---|---|
| G1 | **The game-side door**: `GM/gmfrontend_atlas.inc` with the table walker `fa_submit(const FrontendScreen*)` and `fa_apply`, the shim set `gw_Ui_*` (`spec` 6.7: `gw_Ui_ItemBegin(kind, id)`, `gw_Ui_Label`, `gw_Ui_Value`, `gw_Ui_Options`, `gw_Ui_PollEvent(&item, &arg)`), the frame protocol (begin, submit, poll, end), and the early branch in `gm_Scene_Frontend_OnFrame` | step 2 (U8) | 5 to 10 |
| G2 | **A native-owned screen slot** with the native owner token, closed on every scene exit (step 4's Task 9 builds the same thing for the select screens; whichever lands first owns it, the other reuses it) | step 2 (U5) or step 4 Task 9 | 5 |
| G3 | **Atlas draws in `GS_FRONTEND` scenes**, in front of the scene's fade, and the `MELEE_ATLAS=0` fallback to the legacy kit list | step 2 (spec 6.1) | 5 to 10 |
| G4 | **The `FM_ATLAS` tree and the position protocol**: the SETTINGS node, `fe_settings_from_menus(page)`, `fm_back_kind`/`fm_back_sel`, the `fm_position_for` oracle table | step 2 | 9 |
| G5 | **Tabs in the screen record**, the tab strip in the render, the `AT_HIT_TAB` mouse hits and the style checks (`atlas_style.h`) | **step 4, Tasks 1, 4 and 5** | 4 onward |
| G6 | The step 1 pieces as built (the list primary, the dialog part, `gd.ui` and its stub) | step 1 (done) | all |

Step 3 gives step 5 nothing it waits for. **Task 0 checks each gate by command. If G5 is absent, do step 4's Tasks 1, 4 and 5 first (they are host-only and self-contained), or stop and report; do not copy them into this step.**

## Global Constraints

- **Binding by reference:** the Global Constraints and Review Focus of the step 1 plan and of the step 4 plan (canvas and layout, the 12 px floor and the fit rule, flat quads, chamfers on two opposite corners only, three focus cues at once, motion on the UI clock, budgets, online rules, naming, English only, process rules for this machine, **only one screen stack exists: only the top screen draws and takes input**).
- **Every change applies at once and persists, as today.** A settings row's `set` is called when the value changes, exactly like `fe_change`; nothing is deferred to a "Save" step; environment variables still win over saved values (`gmfrontend_settings.inc` header).
- **The tables stay the source of truth.** No page is rewritten as new data: a page is the same `FrontendItem` array, shown by Atlas. A table row is added or edited only where this plan says so, with the reason.
- **The remap editor's capture state stays in `gmfrontend_controls.inc` and `Controls_*`** (spec 13.5). Atlas freezes its own input during a capture and never reads the pad for anything but the cancel chord.
- **No new features.** The mockup's sample rows that the code does not have (Window mode, Performance record, Reset page, the controller diagram, "Replace" mode) are not built (spec section 14): hints and rows exist only where a function exists.
- **Disc and settings data:** no disc-derived data is committed; erase code paths are tested with **fake callbacks only**: no test, script or step in this plan touches a real save.
- **Two repositories** and the process rules of step 4 (lane `atlas5`, worktree `ws-atlas5`, `nt`, `ppc`, no windows while the owner is present, never print disc paths, never open `_build/local-assets/`, no screenshots as verification).

## Review Focus

| # | What goes wrong | Pinned by |
|---|---|---|
| 1 | **The plan's own drawing breaks the style rules** (chamfers drawn over, fewer than three focus cues, text outside its pane, a toggle that is only a colour, a disabled row only dimmed). | Task 2 and Task 6 call `atlas_style.h` (step 4 Task 1) on every new row kind and every page |
| 2 | **A value changes meaning on the way through**: a slider moves by the wrong step (Main Dead Zone `-1..50` step 1 against the Lua rule `(max-min)/20`), a choice does not wrap, A on a slider does not step, a hidden row keeps focus. | Task 2 `apply_*` (one check per legacy `fe_change` rule); Task 6 `round_trips` |
| 3 | **The capture freeze and the heartbeat**: `Controls_Menu` must be called every frame while the editor is open or a capture is cancelled by the runtime within 100 ms; the bind press must not also act as `A`; the release must be swallowed; START+B must cancel. | Task 8 `capture_timeline`; Task 1 `test_menu_heartbeat.py` |
| 4 | **Text entry swallowed by the screen**: Enter or Escape typed into the Player Name row must not also accept or go back. | Task 5 `freeze_swallows_everything` |
| 5 | **Focus lost or on nothing** after a value shows or hides rows, after a tab switch, after the mods list changes. | Task 5 `refocus_by_id`, `tab_focus_is_per_tab`; Task 6 `visible_rows_change` |
| 6 | **Erase Data**: a confirm that defaults to Yes, a handler that fires on Cancel, categories mixed up, the retail animation code called without its screen (a NULL user-data crash). | Task 7 `erase_cancel_calls_nothing`, `erase_plan_order`; the split of `mndatadel.c` |
| 7 | **Tests that ran as the developer console hid a bug** (step 1). Every ownership or permission check here runs as the native owner and as a mod caller, and the Lua value API runs as a mod. | Task 3 stub and binding tests with `caller=` set; Task 5 `owner_native_vs_mod` |
| 8 | **Return paths**: coming back from the retail Language screen lands on the GAME tab at Language; first boot opens the CONTROLS tab; Back from a tab returns to the right main-menu item; the MODS destination still works. | Task 9 position table test |
| 9 | **A page overflows a record limit**: MODS has up to 40 toggles (the list holds 32), a 512-character mod help line, 20 remap rows. | Task 2 `capacity`; Task 6 `mods_41_rows`, `help_clamped` |

---

## File structure

Game repo (`melee/`).

| File | Create/Modify | Responsibility |
|---|---|---|
| `pc/platform/gw_ui_item.h/.c` | Create | the value rule: `at_item_apply`, `at_item_text`, with **no libc include in the header** (game-side files include it, and the PowerPC check runs with `-nostdinc`) |
| `pc/platform/gw_ui_screen.h/.c` | Modify | `AtItem` gains `vstep`, options, `group`, `reason`, `iflags`; `AT_MAX_ITEMS` 64 |
| `pc/platform/gw_ui_render.c`, `gw_ui_parts.c` | Modify | group headings, readout rows, the slider with steps, the option text, reason on a disabled row |
| `pc/platform/gw_script_ui.inc` | Modify | `step`, `options`, `gd.ui.set_value`, `gd.ui.value` |
| `pc/platform/gw_ui_native_set.c` (or the step 2 shim file) | Create/Modify | the settings shims over the native screen slot |
| `src/melee/gm/gmfrontend_atlas.inc` (step 2's) | Modify | table walker: tabs, readouts, text entry swallow, freeze, notes, dialogs |
| `src/melee/gm/gmfrontend_atlas_set.inc` | Create | the settings pages as tabs, the retail rows, the remap editor layer |
| `src/melee/gm/gmfrontend_settings.inc`, `gmfrontend_controls.inc`, `gmfrontend.c` | Modify | `off_reason` field, the new rows, the Atlas branch's ordering guard |
| `src/melee/mn/mndatadel.c`, `mndatadel.h` | Modify | the erase calls split from the retail animation (`mnDataDel_Erase(category)`) |
| `pc/tests/atlas_items_test.c`, `atlas_settings_stub.h`, `atlas_settings_test.c`, `atlas_erase_test.c`, `atlas_remap_test.c` | Create | the native tests |
| `pc/tests/atlas_ui_stub.lua`, `atlas_ui_stub_test.lua`, `atlas_binding_test.c`, `atlas_screen_test.c`, `atlas_render_test.c` | Modify | the value model on every layer |
| `pc/scripts/examples/demos/atlas-screen/` | Modify | the demo shows a stepped slider and `set_value` |

Workspace repo (root).

| File | Create/Modify | Responsibility |
|---|---|---|
| `tools/port/settings_inventory.py`, `settings_inventory_expected.json` | Create | every `FrontendItem` table, its rows and kinds: the table the pages are checked against |
| `tools/port/test_menu_heartbeat.py` | Create | static guards: `Controls_Menu` is called once per frame before the Atlas branch; the menu-major list; the 100 ms window |
| `tools/port/native_test.sh` | Modify | cases `atlas-items`, `atlas-settings`, `atlas-erase`, `atlas-remap` |
| `docs/scripting.md`, `docs/TERMINOLOGY.md`, `menu/CLAUDE.md` | Modify | the value API, the terms, the retirement list |

## Preflight (once, before Task 0; not a task)

- [ ] **Step 1: Read.** `CLAUDE.md`, `docs/NEXT-SESSION.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md`, spec sections 4 to 10 and 13.5, the step 1 and step 4 plans' Global Constraints, `docs/superpowers/plans/2026-10-03-controls-remap.md` (what the remap work did and left unverified), and in the game: `gmfrontend_settings.inc`, `gmfrontend_controls.inc`, `gmfrontend.c` lines 100 to 135 (the table types), 1810 to 1850 (`fe_change`) and 1960 to 2120 (`gm_Scene_Frontend_OnFrame`).
- [ ] **Step 2: Private lane and shell,** as step 4's Preflight with `atlas5`:

```bash
export MAIN="<the workspace root: the directory that contains tools/ and _toolchains/>"
cd "$MAIN" && tools/port/agent_new.sh atlas5
git -C "$MAIN" worktree add worktrees/ws-atlas5 -b ws/atlas5
export WS="$MAIN/worktrees/ws-atlas5"; export GW_ROOT="$MAIN"
export GW_MELEE="$MAIN/worktrees/atlas5"; export GW_BUILD_ROOT="$MAIN/_build/agents/atlas5"   # as agent_new.sh printed them
nt() { GW_ROOT="$MAIN" GW_MELEE="$GW_MELEE" GW_BUILD_ROOT="$GW_BUILD_ROOT" bash "$WS/tools/port/native_test.sh" "$1"; }
ppc() { ( cd "$GW_MELEE" && "$MAIN/_toolchains/llvm/bin/clang.exe" -fsyntax-only -w -DTARGET_PC --target=powerpc-unknown-eabi -nostdinc -Isrc -Isrc/melee -Iinclude -Ilibs/dolphin/include -Ipc -Ipc/gameworld -Isrc/sysdolphin -Isrc/MSL "$1" ); }
```

If the compiler cannot be run, say so: **a syntax check that did not run is not a pass.**
- [ ] **Step 3: Baselines** (must still pass at the end):

```bash
cd "$GW_MELEE" && lua pc/tests/envoy_run_ux.lua | tail -1 && lua pc/tests/grid_inventory.lua | tail -1 && lua pc/tests/atlas_ui_stub_test.lua | tail -1
for t in tokens layout focus input screen stack parts render binding; do nt atlas-$t | tail -1; done
nt controls-remap | tail -1
```

---

### Task 0: Gate check and the inventory of every settings table

**Files:**
- Create (workspace repo): `tools/port/settings_inventory.py`, `tools/port/settings_inventory_expected.json`

- [ ] **Step 1: Gates by command.** In `$GW_MELEE`:

```bash
test -f src/melee/gm/gmfrontend_atlas.inc && echo "G1 file ok" || echo "G1 MISSING (step 2 not merged)"
grep -n "fa_submit\|gw_Ui_PollEvent" src/melee/gm/gmfrontend_atlas.inc | head -3
grep -n "MELEE_ATLAS" src/melee/gm/*.c src/melee/gm/*.inc pc/platform/*.c | head -3
test -f pc/tests/atlas_style.h && echo "G5 style helper ok" || echo "G5 MISSING: step 4 Task 1"
grep -n "AtTab\|n_tabs" pc/platform/gw_ui_screen.h | head -2 || echo "G5 MISSING: step 4 Task 4"
grep -n "AT_HIT_TAB" pc/platform/gw_ui_input.h | head -1
```

Every line must print a hit. A missing G1 to G4 stops Tasks 5 onward; a missing G5 sends you to step 4's Tasks 1, 4, 5 first. Tasks 1 to 3 need none of them.
- [ ] **Step 2: The inventory script (failing first).** Create `tools/port/settings_inventory.py`:

```python
"""Inventory of every FrontendItem table the Atlas settings pages are checked against.

    python tools/port/settings_inventory.py --check | --table | --write
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")
GM = os.path.join(GAME, "src", "melee", "gm")
EXPECTED = os.path.join(HERE, "settings_inventory_expected.json")
FILES = ("gmfrontend_settings.inc", "gmfrontend_controls.inc", "gmfrontend.c")
TABLE = re.compile(r"static const FrontendItem (\w+)\[\] = \{(.*?)\n\};", re.S)
ROW = re.compile(r"^\s*\{\s*FE_(ACTION|CHOICE|SLIDER|TOGGLE)\s*,", re.M)


def scan():
    out = {}
    for name in FILES:
        text = open(os.path.join(GM, name), encoding="utf-8", errors="replace").read()
        for m in TABLE.finditer(text):
            kinds = ROW.findall(m.group(2))
            out[m.group(1)] = dict(file=name, rows=len(kinds), kinds={k: kinds.count(k) for k in sorted(set(kinds))})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--table", action="store_true")
    g.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    now = scan()
    if a.table:
        for k, v in now.items():
            print("| %s | %s | %d | %s |" % (k, v["file"], v["rows"], v["kinds"]))
        return 0
    if a.write:
        json.dump(now, open(EXPECTED, "w"), indent=1, sort_keys=True)
        open(EXPECTED, "a").write("\n")
        print("wrote %d tables" % len(now))
        return 0
    if now != json.load(open(EXPECTED)):
        print("settings_inventory: a settings table changed; read the diff, update the plan's page tests, then --write")
        return 1
    print("settings_inventory: %d tables match" % len(now))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run, read, write the expected file.**

```bash
cd "$WS" && GW_MELEE="$GW_MELEE" python tools/port/settings_inventory.py --table
```

Expected when this plan was written (`fe_items_set_video 6`, `fe_items_set_audio 3`, `fe_items_howto_online 6`, `fe_items_set_controls 12`, `fe_items_set_online 6`, `fe_items_set_gameplay 10`, `fe_items_remap 20`, `fe_items_vs_setup 10`, `fe_items_online 9`; the MODS table is filled at run time, 1 header row plus up to 40 toggles). If your numbers differ, the table you print is the truth and every count in Tasks 6 and 8 follows it. Then `--write` and `--check` (`settings_inventory: 9 tables match`).
- [ ] **Step 4: Commit** (workspace repo): `tools/port/settings_inventory.py`, `settings_inventory_expected.json`, message `atlas step 5: inventory of every settings table`, with the session's attribution lines.

---

### Task 1: What the menus read (pre or post remap) and the heartbeat, pinned by a static test

The spec leaves it **(unverified)** whether menus read the pad before or after the Controls remap (section 9). This task settles it from the source and pins the two facts the Atlas settings and the remap editor depend on.

**Files:**
- Create (workspace repo): `tools/port/test_menu_heartbeat.py`

- [ ] **Step 1: Read, and write what you find into the commit message.** From `melee/pc/platform/gw_controls_runtime.inc` (`ctl_poll`) as read when this plan was written:
  1. `int menu = major == 0 || major == 1 || major == 8 || major == 9 || major == 0x0B || major == 0x0C || major == 0x0D || major == 0x2E;`: the **original** layout is used only in these game modes (0x2E is `GM_FRONTEND`, `GM_COUNT + 1`; 1 is `GM_MENU`). **`GM_VS` (2), `GM_CLASSIC` (3), `GM_ADVENTURE` (4), `GM_ALLSTAR` (5) and `GM_TRAINING` (0x1C) are not in the list**, so a character select that runs inside one of those modes reads the **remapped** pad, while a settings page in `GM_FRONTEND` reads the original. Identify what 8, 9, 0x0B, 0x0C and 0x0D are from `src/melee/gm/forward.h` and write it down.
  2. `int editor = major == 0x2E && (int)(ctl_menu_until - GetTickCount()) > 0 && ctl_editor;` and `gw_Controls_Menu(editor)` sets `ctl_menu_until = GetTickCount() + 100`: the editor flag **expires 100 ms after the last call**; `ctl_capture` is cancelled with result 4 when `!editor` (`ctl_poll`). So `Controls_Menu(port)` is a **heartbeat**: it must run every frame while the editor is open.
  3. `gm_Scene_Frontend_OnFrame` begins with `Controls_Menu(fe.screen == &fe_screen_remap ? fcr_port : -1);` (gmfrontend.c, the first statement), **before** any branch. The Atlas branch added by step 2 must therefore come **after** that line, and the Atlas remap editor must keep `fe.screen == &fe_screen_remap` true while it is open (the table stays the screen; Atlas only draws it).
  4. **Consequence for key hints (spec 9):** hints keep the logical glyphs; in `GM_FRONTEND` the glyph is also the physical button (original layout); in a CSS that runs inside `GM_VS` and friends the physical binding may differ after a remap. Step 5 draws no hint for the physical button in those modes and says so in `docs/scripting.md`'s "not built" list. Record as a finding for the owner: **a player with a remapped profile sees menus follow the remap in the CSS but not in the hubs and settings** (a property of the existing runtime, not introduced here).
- [ ] **Step 2: Write the static test (failing first).** `tools/port/test_menu_heartbeat.py`:

```python
"""Static guards for the Controls heartbeat and the menu-major list: python tools/port/test_menu_heartbeat.py"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")


def read(*p):
    return open(os.path.join(GAME, *p), encoding="utf-8", errors="replace").read()


class Heartbeat(unittest.TestCase):
    def test_menu_majors_unchanged(self):
        rt = read("pc", "platform", "gw_controls_runtime.inc")
        m = re.search(r"int menu = (.*?);", rt, re.S).group(1)
        majors = sorted(int(x, 0) for x in re.findall(r"major == (0x[0-9A-Fa-f]+|\d+)", m))
        self.assertEqual(majors, [0, 1, 8, 9, 0x0B, 0x0C, 0x0D, 0x2E])

    def test_window_is_100ms(self):
        rt = read("pc", "platform", "gw_controls_runtime.inc")
        self.assertIn("ctl_menu_until = GetTickCount() + 100;", rt)

    def test_heartbeat_runs_once_before_any_branch(self):
        src = read("src", "melee", "gm", "gmfrontend.c")
        body = src[src.index("void gm_Scene_Frontend_OnFrame(void)"):]
        body = body[:body.index("\nvoid gm_Scene_Frontend_OnExit")]
        beats = [m.start() for m in re.finditer(r"Controls_Menu\(", body)]
        self.assertEqual(len(beats), 1, "exactly one heartbeat call per frame")
        for needle in ("fa_frame(", "fas_frame(", "fas.active", "fk_frame("):
            i = body.find(needle)
            if i >= 0:
                self.assertLess(beats[0], i, "the heartbeat must come before %s" % needle)

    def test_remap_screen_stays_the_table(self):
        src = read("src", "melee", "gm", "gmfrontend.c")
        self.assertIn("fe.screen == &fe_screen_remap ? fcr_port : -1", src)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run.** `python tools/port/test_menu_heartbeat.py`; expected `OK` (4 tests) on the tree as it is now. It is a guard: it fails the moment a later task moves the heartbeat below the Atlas branch or changes the remap screen's identity.
- [ ] **Step 4: Commit** (workspace repo), message `atlas step 5: static guards for the Controls heartbeat and the menu-major list`.

---

### Task 2: The value model in the engine (`step`, options, readouts, group headings, reasons)

Step 1's list takes values as data and moves a slider by `max(1, (max - min) / 20)`. The native tables need the legacy rules exactly, and they need more rows than 32. This task adds the model and moves the **legacy rule** (`fe_change`) into a pure function, so one rule serves tables and Lua.

**Files:**
- Modify (game repo): `melee/pc/platform/gw_ui_screen.h`, `gw_ui_screen.c`, `gw_ui_parts.c`, `gw_ui_render.c`, `melee/pc/tests/atlas_screen_test.c`, `atlas_render_test.c`
- Create (game repo): `melee/pc/platform/gw_ui_item.h`, `gw_ui_item.c`, `melee/pc/tests/atlas_items_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-items`)

**Interfaces:**
Consumes: step 1's `AtItem`, `AT_VAL_*`; `atlas_style.h` (step 4 Task 1).
Produces:

```c
/* gw_ui_screen.h */
#define AT_MAX_ITEMS 64                 /* was 32: the MODS page has up to 41 rows, the remap inputs 22 */
#define AT_MAX_OPTS 8
enum { AT_ITEM_A_STEPS = 1, AT_ITEM_RO = 2, AT_ITEM_DANGER = 4 };   /* A steps a slider (+1) like the legacy rule; a readout; a confirm-worthy action */
/* AtItem gains: */ int vstep; int n_opts; char opt[AT_MAX_OPTS][24]; char group[24]; char reason[40]; unsigned iflags;
/* gw_ui_item.h: NO libc include (game-side files include it; the PowerPC check runs with -nostdinc). The value kinds are plain ints
 * equal to AT_VAL_* (a static assert in gw_ui_screen.c keeps the two in step). */
/* The legacy fe_change rule, pure. dir -1 or +1. Returns 1 when the value changed (the caller then calls set), 0 when not (a slider at an end),
 * and writes the new value to *v. Toggle flips; slider adds dir * (step > 0 ? step : 1) and CLAMPS; choice WRAPS over min..max. */
int at_item_apply(int vkind, int vmin, int vmax, int vstep, int cur, int dir, int *v);
/* Which text a row shows for a value: toggle ON/OFF, option i of `opts` (n entries of 24 chars), a slider's number, else `text`. */
void at_item_text(int vkind, int value, int vmin, const char (*opts)[24], int n_opts, const char *text, char *out, int cap);
```

- [ ] **Step 1: Write the failing tests.** `pc/tests/atlas_items_test.c`: one check per legacy rule of `fe_change` (read from `gmfrontend.c:1815-1845`), using values from the real tables:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_screen.h"
#include "../platform/gw_ui_item.h"

static int app(int kind, int mn, int mx, int st, int cur, int dir, int *out) { return at_item_apply(kind, mn, mx, st, cur, dir, out); }

static void apply_choice_wraps(void)
{
    int v;
    CHECK(app(AT_VAL_CHOICE, 0, 5, 1, 5, +1, &v) == 1 && v == 0);          /* Render Scale: 4x wraps to Auto */
    CHECK(app(AT_VAL_CHOICE, 0, 5, 1, 0, -1, &v) == 1 && v == 5);
    CHECK(app(AT_VAL_CHOICE, -1, 4, 1, 4, +1, &v) == 1 && v == -1);       /* Items: min is -1 (the legacy "Off" slot): the wrap uses min..max, not 0..n */
    CHECK(app(AT_VAL_CHOICE, 0, 1, 1, 0, +1, &v) == 1 && v == 1);
}
static void apply_slider_clamps_and_steps(void)
{
    int v;
    CHECK(app(AT_VAL_SLIDER, 0, 100, 5, 95, +1, &v) == 1 && v == 100);     /* Master Volume, step 5 */
    CHECK(app(AT_VAL_SLIDER, 0, 100, 5, 100, +1, &v) == 0 && v == 100);    /* held at an end: unchanged, the caller bumps */
    CHECK(app(AT_VAL_SLIDER, -100, 100, 5, -98, -1, &v) == 1 && v == -100);/* Music / Effects: -98 - 5 clamps to -100 */
    CHECK(app(AT_VAL_SLIDER, -1, 50, 1, -1, -1, &v) == 0);                 /* Main Dead Zone: step 1 across -1..50 (the Lua rule would be 2) */
    CHECK(app(AT_VAL_SLIDER, -1, 50, 1, -1, +1, &v) == 1 && v == 0);
    CHECK(app(AT_VAL_SLIDER, 0, 40, 2, 38, +1, &v) == 1 && v == 40);       /* Stick Dead Zone, step 2 */
    CHECK(app(AT_VAL_SLIDER, 1, 99, 0, 1, +1, &v) == 1 && v == 2);         /* step 0 or less is 1 (legacy: it->step > 0 ? it->step : 1) */
    CHECK(app(AT_VAL_SLIDER, 5, 20, 1, 20, +1, &v) == 0);                  /* Damage Ratio */
}
static void apply_toggle(void)
{
    int v;
    CHECK(app(AT_VAL_TOGGLE, 0, 1, 1, 0, +1, &v) == 1 && v == 1);
    CHECK(app(AT_VAL_TOGGLE, 0, 1, 1, 1, -1, &v) == 1 && v == 0);          /* left and right both flip */
}
static void apply_rejects_readouts(void)
{
    int v = 7;
    CHECK(app(AT_VAL_TEXT, 0, 0, 0, 0, +1, &v) == 0 && v == 7);
    CHECK(app(AT_VAL_COUNTER, 0, 0, 0, 0, +1, &v) == 0 && v == 7);
    CHECK(app(AT_VAL_NONE, 0, 0, 0, 0, +1, &v) == 0);
    CHECK(app(AT_VAL_SLIDER, 5, 5, 1, 5, +1, &v) == 0);                    /* max == min: no range, no change, no divide by zero */
    CHECK(app(AT_VAL_CHOICE, 3, 2, 1, 3, +1, &v) == 0);                    /* an inverted range is refused, not wrapped through a negative n */
}
static void text_of_values(void)
{
    AtItem it; char o[40];
    memset(&it, 0, sizeof it);
    it.vkind = AT_VAL_CHOICE; it.vmin = 0; it.vmax = 2; it.n_opts = 3;
    snprintf(it.opt[0], 24, "%s", "Off"); snprintf(it.opt[1], 24, "%s", "FPS"); snprintf(it.opt[2], 24, "%s", "Performance");
    at_item_text(it.vkind, 1, it.vmin, (const char (*)[24]) it.opt, it.n_opts, it.text, o, sizeof o); CHECK_STR(o, "FPS");
    at_item_text(it.vkind, 7, it.vmin, (const char (*)[24]) it.opt, it.n_opts, it.text, o, sizeof o); CHECK_STR(o, "");   /* out of range: empty, never a read past the options */
    it.vkind = AT_VAL_TOGGLE; at_item_text(it.vkind, 1, 0, NULL, 0, it.text, o, sizeof o); CHECK_STR(o, "ON");
    at_item_text(it.vkind, 0, 0, NULL, 0, it.text, o, sizeof o); CHECK_STR(o, "OFF");
    it.vkind = AT_VAL_SLIDER; at_item_text(it.vkind, 45, 0, NULL, 0, it.text, o, sizeof o); CHECK_STR(o, "45");
    it.vkind = AT_VAL_TEXT; snprintf(it.text, AT_STR, "%s", "Port 1: Nothing connected"); at_item_text(it.vkind, 0, 0, NULL, 0, it.text, o, sizeof o); CHECK_STR(o, "Port 1: Nothing connected");
}
static void capacity(void)
{
    CHECK(AT_MAX_ITEMS >= 64 && AT_MAX_OPTS >= 6);                          /* Render Scale has 6 options, the MODS page 41 rows */
}
int main(void) { apply_choice_wraps(); apply_slider_clamps_and_steps(); apply_toggle(); apply_rejects_readouts(); text_of_values(); capacity(); ATLAS_DONE("atlas items"); }
```

In `atlas_render_test.c` add (with `atlas_style.h`): `value_rows_style`: a list with a toggle, a stepped slider, a choice with options, a readout, a disabled row with a `reason`, and two group headings; for each row kind the checks are `sty_chamfer(row, 5.0f, parent)`, `sty_text_inside(row, from)` at 640 and at 853, `sty_focus_cues(rest, focused) == 3`, and for the disabled row **both** a non-colour signal (its `reason` text or the word `LOCKED`/`NOT NOW`, found with `find_text`) and `texts_legible()`. The toggle must draw the words `ON` and `OFF` (colour is never the only signal) and the slider a track whose lit fraction equals `(v - min) / (max - min)` within 1 px (assert on the lit poly's width). A group heading is not focusable: `at_screen_focus_blocks` skips it (add to `atlas_screen_test.c`: `refocus_skips_headings`), and Up from the first row after a heading wraps to the last row, never onto the heading.

Register `atlas-items) sources=(pc/tests/atlas_items_test.c pc/platform/gw_ui_item.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_layout.c) ;;` and run `nt atlas-items`; expected: compile errors (no `at_item_apply`).

- [ ] **Step 2: Implement** `at_item_apply` and `at_item_text` in `gw_ui_item.c` (the apply rule is the legacy one, line for line, plus the two refusals the tests pin), the new fields, `AT_MAX_ITEMS 64` (check `grep -n "AT_MAX_ITEMS" -r pc` for every array it sizes: the focus block arrays, `at_screen_from_val`'s validation message, the stub's copy of the limit in `atlas_ui_stub.lua` which reads it from the header, and `scripting.md`'s "32 items"), group headings in `draw_list` (a heading draws when `group[0] != 0` and differs from the previous row's; it takes 22 px and no hit rectangle) and `reason` under the label of a disabled row (`AT_R_BODY12`, clipped). **The Lua door keeps its documented limits unless Task 3 says otherwise**: the converter still refuses more than 32 items from a script (`AT_MAX_ITEMS_LUA 32`), so the limit that changes is the native one.
Every `native_test.sh` case that links `gw_ui_screen.c` (`atlas-screen`, `atlas-render`, `atlas-binding`, and step 4's `atlas-select-render`, `atlas-select-adapter`) now also needs `pc/platform/gw_ui_item.c` in its `sources=` line: add it to each, or those cases fail to link.
- [ ] **Step 3: Run** `nt atlas-items`, `nt atlas-screen`, `nt atlas-render`, `nt atlas-binding`, the baselines. Expected: all pass, including the unchanged step 1 tests.
- [ ] **Step 4: Commit** (game repo; workspace repo for `native_test.sh`), message `atlas step 5: the value model in the engine: step, options, readouts, headings, reasons; the legacy change rule as a pure function`.

---

### Task 3: Lua parity: `step`, `gd.ui.set_value`, `gd.ui.value` (small, tested as a mod, never only as the console)

The LAB (step 7) and any mod need the same value model. This is the smallest API that gives it; it is **additive** (no existing call changes).

**Files:**
- Modify (game repo): `melee/pc/platform/gw_script_ui.inc`, `melee/pc/platform/gw_ui_screen.c` (conversion of `step` and `options`), `melee/pc/tests/atlas_ui_stub.lua`, `atlas_ui_stub_test.lua`, `atlas_binding_test.c`, `melee/pc/scripts/examples/demos/atlas-screen/` (the demo)
- Modify (workspace repo): `docs/scripting.md`

**Interfaces (the contract, to appear in the docs):**
- A slider value takes `step` (integer, at least 1, default `max(1, (max - min) / 20)` as today); a choice value takes `options = { "Off", "FPS", "Performance" }` (at most 8, each cut at 23 characters), `min` 0 and `max = #options - 1` implied; with `options` the **engine** owns the choice (it wraps, updates the text, and calls `on.change(item_id, index)`); without `options` the old behaviour (direction passed) is unchanged.
- `gd.ui.set_value(screen_id, item_id, v)`: sets a toggle (boolean), slider (integer, clamped) or choice (index) value in place, **without re-registering and without moving the focus**; a text or counter row takes a string. Returns `true` when the row exists, is of the right kind and the value was accepted. Raises on an unknown screen (as every `gd.ui` call), and on a screen that belongs to another script (`gd.ui: screen "id" belongs to another script`); returns `false` for an unknown item or a wrong-typed value.
- `gd.ui.value(screen_id, item_id)`: the current value (boolean, integer or string), or `nil` for an unknown item. Same ownership rule.
- **No per-frame Lua `get`** (the spec's `get` read every frame would cost a Lua call per row per frame inside the 50 ms budget): a script calls `set_value` when its own state changes. Native tables get live values from the adapter.

- [ ] **Step 1: Write the failing tests, as a mod caller.** In `atlas_ui_stub_test.lua` add (the stub is built with `Stub.new{ caller = "demo.mod", owner_mod = "demo" }`: **not the console**):

```lua
local S = Stub.new{ caller = "demo.mod", owner_mod = "demo", available = true }
S.ui.screen{ id = "demo.set", trail = { title = "T" }, primary = { kind = "list", items = {
  { id = "vol", label = "Volume", value = { kind = "slider", min = -1, max = 50, step = 1, value = 3 } },
  { id = "fps", label = "FPS", value = { kind = "choice", options = { "Off", "FPS", "Perf" }, value = 0 } },
  { id = "on",  label = "On",  value = { kind = "toggle", on = false } },
  { id = "who", label = "Who", value = { kind = "text", text = "P1" } } } },
  keys = { { "B", "Back" } }, on = { back = function() return { pop = true } end } }
-- the new API as the owner
check(S.ui.value("demo.set", "vol") == 3, "value reads the slider")
check(S.ui.set_value("demo.set", "vol", 99) == true and S.ui.value("demo.set", "vol") == 50, "set_value clamps a slider")
check(S.ui.set_value("demo.set", "vol", "x") == false, "a wrong-typed value is refused, not coerced")
check(S.ui.set_value("demo.set", "fps", 2) == true and S.ui.value("demo.set", "fps") == 2, "a choice takes an index")
check(S.ui.set_value("demo.set", "fps", 3) == false, "an index past the options is refused")
check(S.ui.set_value("demo.set", "on", true) == true and S.ui.value("demo.set", "on") == true, "toggle")
check(S.ui.set_value("demo.set", "who", "P2") == true and S.ui.value("demo.set", "who") == "P2", "text row")
check(S.ui.set_value("demo.set", "nope", 1) == false and S.ui.value("demo.set", "nope") == nil, "unknown item")
-- ownership: ANOTHER script's screen is refused for a mod caller (the console is the only exception).
-- If the stub cannot share screens between two callers, add `shared` (a table of screens) to Stub.new with its own check first.
local T = Stub.new{ caller = "other.mod", owner_mod = "other", available = true, shared = S }
local ok, err = pcall(function() return T.ui.set_value("demo.set", "vol", 1) end)
check(not ok and tostring(err):find("belongs to another script"), "set_value on another script's screen raises")
ok, err = pcall(function() return T.ui.value("demo.set", "vol") end)
check(not ok and tostring(err):find("belongs to another script"), "value on another script's screen raises")
-- step: engine rule through engine_press
S.engine_focus("demo.set", "vol"); S.engine_press("demo.set", "right")
check(S.ui.value("demo.set", "vol") == 50, "already at max 50: a step right clamps and says nothing")
S.engine_press("demo.set", "left")
check(S.ui.value("demo.set", "vol") == 49, "a slider with step 1 moves by 1, not by (max - min) / 20 = 2")
```

and the matching C checks in `atlas_binding_test.c` with a **non-console caller** (`gs.cur` set to a script slot, not the console): `set_value` on an own screen returns true and does not call `on.change`; on another script's screen raises the documented message; `value` agrees; with `options` the engine wraps through `on.change(item_id, index)`. Run `lua pc/tests/atlas_ui_stub_test.lua` and `nt atlas-binding`; expected: failures (`set_value` missing).

- [ ] **Step 2: Implement** in the binding: `step` and `options` in the value conversion (`at_screen_from_val`: validate `step >= 1` and `options` count 1 to 8, strings cut at 23, `min`/`max` for a choice derived), the engine's wrap for an options choice via `at_item_apply`, `set_value` and `value` as host-side writes into the screen record's item (never a re-registration), under the **same owner check every `gd.ui` call uses** (reuse the helper that raises `belongs to another script`; do not write a second check). Mirror the same rules in `atlas_ui_stub.lua`, reading the limits from the C headers as the stub already does for the others.
- [ ] **Step 3: Docs.** `docs/scripting.md`: add the two calls to the `gd.ui` table, the `step` and `options` fields to "A description", replace the last sentence ("Not in step 1: ...") by what is still not built (per-frame `get`, mouse-wheel stepping unless Task 5 adds it), and bump the list limit text only for native screens. Public docs never mention private branches or paths.
- [ ] **Step 4: Demo.** `demos/atlas-screen` gains a stepped slider and a choice with options, and a note that shows `gd.ui.value` after a change; its README line lists the new calls.
- [ ] **Step 5: Run** the stub test, `nt atlas-binding`, `luac -p` on the demo, the baselines. Expected: pass. **Commit** (game repo, workspace repo for the docs), message `atlas step 5: gd.ui step, options, set_value and value (additive; tested as a mod caller)`.

---
### Task 4: The table walker: one `FrontendScreen` becomes the rows of one tab (header-only, tested with fake shims)

The pages are tables of function pointers that live on the game side. The walker evaluates them there (`get`, `visible`, `enabled`, `format`) and submits **scalars and strings** to the host; it applies the host's events with the legacy rules. To test it without the game, its logic lives in a header that needs only the table types and the shim prototypes.

**Files:**
- Create (game repo): `melee/src/melee/gm/gmfrontend_items.h` (the table types, moved out of `gmfrontend.c`), `melee/src/melee/gm/gmfrontend_atlas_table.h` (the walker), `melee/pc/tests/atlas_settings_stub.h` (fake shims and a recording host), `melee/pc/tests/atlas_walker_test.c`
- Modify (game repo): `melee/src/melee/gm/gmfrontend.c` (replace lines 100 to 134, the toolkit's data types, by `#include "gmfrontend_items.h"`; add the field `const char* off_reason;` **at the end** of `FrontendItem`, so every positional initialiser stays valid and the field defaults to NULL), `gmfrontend_atlas.inc` (include the walker)
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-walker`)

**Interfaces:**
Consumes: step 2's frame protocol (G1), Task 2's `at_item_apply` through the shim below.
Produces:

```c
/* gmfrontend_items.h: no libc, no game headers (u8 is unsigned char in the game too) */
typedef enum FrontendItemKind { FE_ACTION, FE_CHOICE, FE_SLIDER, FE_TOGGLE } FrontendItemKind;
typedef enum FrontendAction { FE_DO_CONTINUE, FE_DO_BACK, FE_DO_CALL } FrontendAction;
typedef struct FrontendItem {
    unsigned char kind, action; const char *label, *help;
    int (*get)(void); void (*set)(int); int min, max, step;
    const char *const *options; void (*format)(int value, char *out);
    int (*visible)(void); void (*call)(void); int (*enabled)(void);
    const char *off_reason;                 /* new: shown under a disabled row ("Connect a controller to this port first.") */
} FrontendItem;
typedef struct FrontendScreen { const char *title, *subtitle; const FrontendItem *items; int n_items; int art; } FrontendScreen;

/* gmfrontend_atlas_table.h */
#define FAS_MAX 64
typedef struct { int n, idx[FAS_MAX]; } FasVis;                 /* the visible rows: slot -> table index */
enum { FAS_EV_CHANGE = 1, FAS_EV_ACCEPT = 2, FAS_EV_BACK = 3, FAS_EV_TAB = 4 };
enum { FAS_FX_MOVE = 1, FAS_FX_BACK = 2, FAS_FX_FORWARD = 4, FAS_FX_REBUILD = 8, FAS_FX_CONTINUE = 16, FAS_FX_LEAVE = 32, FAS_FX_BUMP = 64 };
static void fas_visible(const FrontendScreen *s, FasVis *v);
static void fas_table_submit(int h, const FrontendScreen *s, const FasVis *v);                       /* values, text, flags, per frame */
static unsigned fas_table_event(const FrontendScreen *s, const FasVis *v, int slot, int ev, int arg); /* the legacy rules; returns FAS_FX_* */
/* host shims the walker calls */
extern void gw_Ui_SetRows(int h, int n);
extern void gw_Ui_SetRow(int h, int slot, const char *id, const char *label, const char *help, int vkind, int vmin, int vmax, int vstep,
                         int value, const char *text, unsigned flags, const char *reason);
extern void gw_Ui_SetRowOpt(int h, int slot, int k, const char *text);
extern int  gw_Ui_ItemApply(int vkind, int vmin, int vmax, int vstep, int cur, int dir, int *out);   /* = at_item_apply */
```

- [ ] **Step 1: Write the failing tests** (`pc/tests/atlas_walker_test.c`). Each check is a branch of the legacy code, named for its source line; the fake items use local functions with counters.

```c
#include "atlas_check.h"
#include "../../src/melee/gm/gmfrontend_items.h"
#include "atlas_settings_stub.h"                 /* fake gw_Ui_* that record rows, options and apply calls into REC_ROWS */
#include "../../src/melee/gm/gmfrontend_atlas_table.h"

static int g_val, g_sets, g_calls, g_en = 1, g_vis = 1; static int g_last;
static int get_v(void) { return g_val; }
static void set_v(int v) { g_val = v; g_sets++; g_last = v; }
static void call_it(void) { g_calls++; }
static int en(void) { return g_en; }
static int vis(void) { return g_vis; }
static void fmt_pct(int v, char *o) { o[0] = (char) ('0' + v / 10); o[1] = (char) ('0' + v % 10); o[2] = '%'; o[3] = 0; }
static const char *const OPTS[] = { "Off", "FPS", "Performance" };

static const FrontendItem T[] = {
    /* 0 */ { FE_TOGGLE, 0, "VSync", "Wait for the display.", get_v, set_v, 0, 1, 1 },
    /* 1 */ { FE_SLIDER, 0, "Master Volume", "Everything.", get_v, set_v, 0, 100, 5, NULL, fmt_pct },
    /* 2 */ { FE_CHOICE, 0, "Show FPS", "Readout.", get_v, set_v, 0, 2, 1, OPTS },
    /* 3 */ { FE_SLIDER, 0, "Port 1", "Live.", get_v, NULL, 0, 0, 0, NULL, fmt_pct },                       /* a readout: a slider with no set */
    /* 4 */ { FE_ACTION, FE_DO_CALL, "Recalibrate", "Adapter.", NULL, NULL, 0, 0, 0, NULL, fmt_pct, NULL, call_it },
    /* 5 */ { FE_ACTION, FE_DO_CALL, "Bind", "Capture.", NULL, NULL, 0, 0, 0, NULL, NULL, NULL, call_it, en, "Connect a controller first." },
    /* 6 */ { FE_SLIDER, 0, "Stick Dead Zone", "SDL only.", get_v, set_v, 0, 40, 2, NULL, NULL, vis },
    /* 7 */ { FE_ACTION, FE_DO_CONTINUE, "Continue", "On." },
    /* 8 */ { FE_ACTION, FE_DO_BACK, "Done", "Back." },
};
static const FrontendScreen S = { "SETTINGS", "VIDEO", T, 9, 0 };

static void visible_and_ids(void)
{
    FasVis v;
    g_vis = 0; fas_visible(&S, &v);
    CHECK(v.n == 8 && v.idx[6] == 7);                                  /* row 6 hidden: slots shift, table indices stay */
    fas_table_submit(1, &S, &v);
    CHECK(REC_ROWS.n == 8 && strcmp(REC_ROWS.r[6].id, "i7") == 0);     /* ids are TABLE indices: stable when rows show or hide (focus refocuses by id) */
    g_vis = 1; fas_visible(&S, &v); CHECK(v.n == 9);
}
static void kinds_and_text(void)
{
    FasVis v; g_val = 45; fas_visible(&S, &v); fas_table_submit(1, &S, &v);
    CHECK(REC_ROWS.r[0].vkind == STUB_TOGGLE && REC_ROWS.r[0].value == 1);                                                /* any non-zero is on */
    CHECK(REC_ROWS.r[1].vkind == STUB_SLIDER && REC_ROWS.r[1].vmax == 100 && REC_ROWS.r[1].vstep == 5 && strcmp(REC_ROWS.r[1].text, "45%") == 0);
    CHECK(REC_ROWS.r[2].vkind == STUB_CHOICE && REC_ROWS.r[2].n_opts == 3 && strcmp(REC_ROWS.r[2].opt[1], "FPS") == 0);
    CHECK(REC_ROWS.r[3].vkind == STUB_TEXT && (REC_ROWS.r[3].flags & STUB_RO) && strcmp(REC_ROWS.r[3].text, "45%") == 0);   /* set == NULL: a readout (the kit's FKW_READOUT rule) */
    CHECK(REC_ROWS.r[4].vkind == STUB_TEXT && strcmp(REC_ROWS.r[4].text, "00%") == 0);                                    /* an action with a status */
    CHECK(REC_ROWS.r[7].vkind == STUB_NONE);                                                                               /* an action without one */
    CHECK((REC_ROWS.r[5].flags & STUB_DISABLED) == 0 && g_en == 1);
    g_en = 0; fas_table_submit(1, &S, &v);
    CHECK((REC_ROWS.r[5].flags & STUB_DISABLED) && strcmp(REC_ROWS.r[5].reason, "Connect a controller first.") == 0);       /* disabled has words, not only a dim */
    g_en = 1;
}
static void legacy_change(void)                                          /* fe_change, gmfrontend.c:1815 */
{
    FasVis v; unsigned fx; fas_visible(&S, &v);
    g_val = 95; g_sets = 0; fx = fas_table_event(&S, &v, 1, FAS_EV_CHANGE, +1);
    CHECK(g_last == 100 && g_sets == 1 && (fx & FAS_FX_MOVE) && (fx & FAS_FX_REBUILD));                                 /* step 5, clamps at 100 */
    g_sets = 0; fx = fas_table_event(&S, &v, 1, FAS_EV_CHANGE, +1);
    CHECK(g_sets == 0 || g_last == 100);                                                                                   /* held at the end ... */
    CHECK(fx & FAS_FX_BUMP);                                                                                               /* ... the kit's "can't go further" */
    g_val = 2; g_sets = 0; fas_table_event(&S, &v, 2, FAS_EV_CHANGE, +1); CHECK(g_last == 0);                              /* a choice wraps */
    g_val = 0; fas_table_event(&S, &v, 0, FAS_EV_CHANGE, -1); CHECK(g_last == 1);                                          /* a toggle flips from either direction */
    g_sets = 0; fas_table_event(&S, &v, 3, FAS_EV_CHANGE, +1); CHECK(g_sets == 0);                                         /* a readout never changes */
}
static void legacy_accept(void)                                          /* gm_Scene_Frontend_OnFrame, the Confirm branch (gmfrontend.c:2062) */
{
    FasVis v; unsigned fx; fas_visible(&S, &v);
    g_calls = 0; fx = fas_table_event(&S, &v, 4, FAS_EV_ACCEPT, 0);
    CHECK(g_calls == 1 && (fx & FAS_FX_FORWARD) && (fx & FAS_FX_REBUILD));                                                 /* FE_DO_CALL: call, rebuild */
    g_en = 0; g_calls = 0; fx = fas_table_event(&S, &v, 5, FAS_EV_ACCEPT, 0);
    CHECK(g_calls == 0 && (fx & FAS_FX_BACK) && (fx & FAS_FX_BUMP));                                                       /* a disabled row: no call, back sound, bump */
    g_en = 1;
    fx = fas_table_event(&S, &v, 7, FAS_EV_ACCEPT, 0); CHECK((fx & FAS_FX_CONTINUE) && (fx & FAS_FX_FORWARD));
    fx = fas_table_event(&S, &v, 8, FAS_EV_ACCEPT, 0); CHECK((fx & FAS_FX_LEAVE) && (fx & FAS_FX_BACK));
    g_val = 10; g_sets = 0; fas_table_event(&S, &v, 1, FAS_EV_ACCEPT, 0); CHECK(g_last == 15);                              /* A on a slider steps +1 step: the legacy rule */
    fas_table_event(&S, &v, 0, FAS_EV_ACCEPT, 0); CHECK(g_sets == 2);                                                      /* A on a toggle flips */
    CHECK(fas_table_event(&S, &v, 99, FAS_EV_ACCEPT, 0) == 0 && fas_table_event(&S, &v, -1, FAS_EV_CHANGE, 1) == 0);       /* a stale or bad slot does nothing */
}
static void big_table(void)
{
    static FrontendItem M[41]; static FrontendScreen MS; FasVis v; int i;
    memset(M, 0, sizeof M); M[0].kind = FE_SLIDER; M[0].label = "Mods"; M[0].get = get_v; M[0].format = fmt_pct;
    for (i = 1; i < 41; i++) { M[i].kind = FE_TOGGLE; M[i].label = "mod"; M[i].get = get_v; M[i].set = set_v; M[i].max = 1; M[i].step = 1; }
    MS.items = M; MS.n_items = 41; fas_visible(&MS, &v); CHECK(v.n == 41);
    fas_table_submit(1, &MS, &v); CHECK(REC_ROWS.n == 41);                                                                 /* the MODS page fits (FAS_MAX 64, AT_MAX_ITEMS 64) */
}
int main(void) { visible_and_ids(); kinds_and_text(); legacy_change(); legacy_accept(); big_table(); ATLAS_DONE("atlas walker"); }
```

`atlas_settings_stub.h` defines the `STUB_*` constants equal to `AT_VAL_*`, `REC_ROWS` (up to 64 rows with `id`, `label`, `help` cut to 159, `vkind`, `vmin`, `vmax`, `vstep`, `value`, `text`, `flags`, `reason`, `opt[8][24]`, `n_opts`), and implements `gw_Ui_SetRows`, `gw_Ui_SetRow`, `gw_Ui_SetRowOpt` (clamping slots to 64 and **ignoring** a slot past `SetRows`' count) and `gw_Ui_ItemApply` (a call into `at_item_apply`, so the test links `gw_ui_item.c`).

Register `atlas-walker) sources=(pc/tests/atlas_walker_test.c pc/platform/gw_ui_item.c) ;;`. Run `nt atlas-walker`; expected: compile errors (the headers do not exist).

- [ ] **Step 2: Move the types and write the walker.** `gmfrontend_items.h` is the interface block; in `gmfrontend.c` delete the moved definitions (lines 100 to 134) and include the header. Check that `FrontendRule` (not moved) still compiles. The walker:

```c
static void fas_visible(const FrontendScreen *s, FasVis *v)
{
    int i;
    v->n = 0;
    for (i = 0; i < s->n_items && v->n < FAS_MAX; i++)
        if (s->items[i].visible == 0 || s->items[i].visible()) v->idx[v->n++] = i;
}

static int fas_vkind(const FrontendItem *it)
{
    switch (it->kind) {
    case FE_TOGGLE: return 1;                                           /* AT_VAL_TOGGLE */
    case FE_CHOICE: return 2;                                           /* AT_VAL_CHOICE */
    case FE_SLIDER: return it->set != 0 ? 3 : 4;                        /* a slider with no set is a readout: AT_VAL_TEXT (the kit's FKW_READOUT rule) */
    default:        return it->format != 0 ? 4 : 0;                     /* an action with a status shows it; else no value */
    }
}

static void fas_table_submit(int h, const FrontendScreen *s, const FasVis *v)
{
    int slot, k;
    gw_Ui_SetRows(h, v->n);
    for (slot = 0; slot < v->n; slot++) {
        const FrontendItem *it = &s->items[v->idx[slot]];
        char id[12], text[80]; unsigned flags = 0; int value = it->get != 0 ? it->get() : 0, vk = fas_vkind(it);
        const char *reason = "";
        id[0] = 'i'; { int n = v->idx[slot], d = 0; char t[8]; if (n == 0) t[d++] = '0'; while (n > 0 && d < 7) { t[d++] = (char) ('0' + n % 10); n /= 10; } for (k = 0; k < d; k++) id[1 + k] = t[d - 1 - k]; id[1 + d] = 0; }
        text[0] = 0;
        if (it->format != 0 && (vk == 3 || vk == 4 || (vk == 2 && it->options == 0))) it->format(value, text);
        if (vk == 4) flags |= 2;                                        /* AT_ITEM_RO */
        if (it->kind == FE_SLIDER && it->set != 0) flags |= 1;          /* AT_ITEM_A_STEPS: A steps a slider, as the legacy Confirm branch does */
        if (it->enabled != 0 && !it->enabled()) { flags |= 8; if (it->off_reason != 0) reason = it->off_reason; }   /* 8: disabled */
        gw_Ui_SetRow(h, slot, id, it->label, it->help != 0 ? it->help : "", vk, it->min, it->max, it->step, vk == 1 ? value != 0 : value, text, flags, reason);
        if (vk == 2 && it->options != 0)
            for (k = 0; k <= it->max - it->min && k < 8; k++) gw_Ui_SetRowOpt(h, slot, k, it->options[k]);
    }
}
```

(`flags` 1, 2, 8 are `AT_ITEM_A_STEPS`, `AT_ITEM_RO` and a new `AT_ITEM_DISABLED = 8` in `gw_ui_screen.h`; the header cannot include the host header, so the numbers are written here and **asserted equal** in `gw_ui_native_set.c`: `_Static_assert(AT_ITEM_A_STEPS == 1 && AT_ITEM_RO == 2 && AT_ITEM_DISABLED == 8, "walker flag numbers")`.) Then `fas_table_event`, which is `fe_change` and the Confirm and Back branches of `gm_Scene_Frontend_OnFrame`, moved: `FAS_EV_CHANGE` does `get`/`set` null checks, applies `gw_Ui_ItemApply(vkind, min, max, step, get(), dir, &v)`, returns `FAS_FX_BUMP` when the apply says unchanged for a slider, otherwise calls `set(v)` and returns `FAS_FX_MOVE | FAS_FX_REBUILD`; `FAS_EV_ACCEPT` is the Confirm branch (disabled: `FAS_FX_BACK | FAS_FX_BUMP`, no call; `FE_ACTION`: `FE_DO_CALL` calls and returns `FAS_FX_FORWARD | FAS_FX_REBUILD`, `FE_DO_CONTINUE` returns `FAS_FX_FORWARD | FAS_FX_CONTINUE`, else `FAS_FX_BACK | FAS_FX_LEAVE`; a non-action with `call` calls it; otherwise a change of +1); `FAS_EV_BACK` returns `FAS_FX_BACK | FAS_FX_LEAVE`: the **caller** (the screen's own code, Task 8 for the remap editor and the how-to page) decides what Back means for those two, exactly as the legacy Back branch does (`fcr_back`, the controls help page, else leave).

- [ ] **Step 3: Run until it passes.** Then `ppc src/melee/gm/gmfrontend.c` (the moved types must still compile for PowerPC) and the baselines. Expected `atlas walker: N checks, 0 failed`.
- [ ] **Step 4: Commit** (game repo, workspace repo for `native_test.sh`), message `atlas step 5: the table walker (legacy change and confirm rules, readouts, reasons) as a header tested without the game; off_reason field`.

---

### Task 5: Tabs over pages, per-tab focus, the freeze, and ownership (host half; needs G5)

**Files:**
- Modify (game repo): `melee/pc/platform/gw_ui_native_sel.c` (or step 2's native-shim file; the settings shims live beside the select shims and use the same native slot), `gw_ui_input.c`, `gw_ui_screen.c` (item flag `AT_ITEM_DISABLED`), `melee/pc/tests/atlas_select_adapter_test.c` or a new `atlas_settings_host_test.c`
- Modify (workspace repo): `tools/port/native_test.sh`

**Interfaces:**
Produces (shims, host half):

```c
int  gw_Ui_SetOpen(int match_page /* the settings page index */, const char *t0, const char *title);   /* the native settings screen; handle or -1 */
void gw_Ui_SetTabs(int h, int n, const char *names /* "VIDEO,AUDIO,CONTROLS,ONLINE,GAME,MODS" */, int active);
void gw_Ui_SetFocus(int h, const char *item_id);                      /* put the focus on an item by id (after a rebuild or a tab switch) */
void gw_Ui_SetExplain(int h, const char *kicker, const char *title, const char *what, const char *now, const char *from);
void gw_Ui_SetKeys(int h, const char *spec);
void gw_Ui_SetNote(int h, const char *text, int kind);
void gw_Ui_SetDialog(int h, const char *title, const char *text, const char *a_label, const char *b_label, int default_button);
int  gw_Ui_SetDialogAnswer(int h);                                    /* 0 pending, 1 A, 2 B (taken once) */
void gw_Ui_Freeze(int h, int on);                                     /* drop every event: text entry and remap capture */
int  gw_Ui_PollEvent(int h, int *item_slot, int *arg);                /* FAS_EV_*; item_slot = the slot (-1 for tab or back) */
```

- [ ] **Step 1: Write the failing host tests** (the real render and input, fake kit, as in step 4 Task 9). The ones that matter:

```c
static void tab_focus_is_per_tab(void)                                /* Review Focus 5 */
{
    int h = open_settings(0); build_rows(h, 6); gw_Ui_SetFocus(h, "i3");
    CHECK(strcmp(focused_id(h), "i3") == 0);
    switch_tab(h, 1); build_rows(h, 3);                                /* AUDIO has 3 rows; the adapter submits them */
    CHECK(strcmp(focused_id(h), "i0") == 0);                           /* a fresh tab starts on its first row */
    switch_tab(h, 0); build_rows(h, 6);
    CHECK(strcmp(focused_id(h), "i3") == 0);                           /* the adapter remembers per tab and refocuses by id */
}
static void refocus_by_id(void)
{
    int h = open_settings(0); build_rows(h, 6); gw_Ui_SetFocus(h, "i4");
    hide_row(h, 4);                                                    /* a value hid the focused row */
    CHECK(strcmp(focused_id(h), "i5") == 0);                           /* the next visible row, never nothing and never a stale index */
    hide_row(h, 5); hide_row(h, 3); hide_row(h, 2); hide_row(h, 1); hide_row(h, 0);
    CHECK(focused_id(h)[0] == 0 || strcmp(focused_id(h), "i0") != 0);  /* rows gone: no focus, no crash, an explainer for nothing is empty */
}
static void freeze_swallows_everything(void)                          /* Review Focus 4 */
{
    int h = open_settings(2), s, a;
    build_rows(h, 12);
    gw_Ui_Freeze(h, 1);
    test_key(AT_KEY_ENTER); test_key(AT_KEY_ESC); test_pad(AT_PAD_A | AT_PAD_B); test_click(h, 100, 100);
    CHECK(gw_Ui_PollEvent(h, &s, &a) == 0);                            /* nothing reaches the adapter while a name is being typed */
    gw_Ui_Freeze(h, 0);
    test_tick(h, 0);                                                   /* Enter and A are STILL HELD from the frame the edit ended */
    CHECK(gw_Ui_PollEvent(h, &s, &a) == 0);                            /* a held button after a freeze primes from the held state: it does not accept */
    test_release_all(); test_pad(AT_PAD_A); test_tick(h, 20);
    CHECK(gw_Ui_PollEvent(h, &s, &a) == FAS_EV_ACCEPT);                /* a fresh press does */
}
static void dialog_defaults_to_cancel(void)                           /* Review Focus 6 */
{
    int h = open_settings(5);
    gw_Ui_SetDialog(h, "ERASE DATA", "This cannot be undone.", "Erase", "Cancel", 2 /* the B button */);
    CHECK(gw_Ui_SetDialogAnswer(h) == 0);
    test_pad(AT_PAD_A); test_tick(h, 0); test_release_all();           /* a stray A held from before: must not answer */
    CHECK(gw_Ui_SetDialogAnswer(h) == 0);
    test_pad(AT_PAD_A); test_tick(h, 30);
    CHECK(gw_Ui_SetDialogAnswer(h) == 1);                              /* a fresh A answers Erase only when A was pressed on purpose */
    gw_Ui_SetDialog(h, "ERASE DATA", "x", "Erase", "Cancel", 2); test_release_all(); test_pad(AT_PAD_B); test_tick(h, 60);
    CHECK(gw_Ui_SetDialogAnswer(h) == 2);                              /* B is Cancel, and the dialog closes */
}
static void owner_native_vs_mod(void)                                 /* Review Focus 7 */
{
    int h = open_settings(0);
    CHECK(mod_close("some.mod") == 0 && mod_feed("some.mod", "accept") == 0 && mod_open_over("some.mod") == 0);
    CHECK(console_close() == 1);
    gw_Ui_SceneChanged(); CHECK(depth() == 0);                         /* closed on every scene exit (the step 4 rule) */
    (void) h;
}
```

`open_settings`, `build_rows`, `focused_id`, `hide_row`, `switch_tab`, `test_*` are small helpers in the test file over the host functions and the test accessors (`#ifdef GW_UI_SEL_TEST`). The dialog's default focus is the **Cancel** button in every dialog the adapter opens for a destructive action (`default_button = 2`): the part draws the focused button with the three cues, and the pad's A answers the **focused** button, B always answers Cancel. Register the case with the render sources and the native-slot file; run it; expected: fails (no shims).

- [ ] **Step 2: Implement.** The settings shims fill the same native slot as the select shims (one native screen at a time: **only one stack exists**). Rules: `gw_Ui_SetTabs` fills `sc->tabs` and `v->tab`; L and R (and Tab and Shift+Tab, and a click on a tab) produce `FAS_EV_TAB` with the target tab (wrapping), and the host **does not** switch the displayed tab itself: the adapter submits the new rows, then the host shows them (otherwise one frame of the old rows under the new tab); `gw_Ui_SetFocus` finds the item by id, else the first row; `gw_Ui_Freeze(h, on)` drops all events and, on release, **primes** the pad, key and mouse states from what is held at that instant (step 1's rule for a screen that becomes the top one: reuse its function); a frozen screen still draws. The dialog part is step 1's, opened by `gw_Ui_SetDialog` with the focused button, and `at_part_dialog` must show the focused button with three cues (add a check with `sty_focus_cues`).
- [ ] **Step 3: Run, commit.** Host tests, the baselines. Message `atlas step 5: tabs over pages with per-tab focus, the freeze with held-button priming, a Cancel-first dialog, ownership as native and as mod`.

---

### Task 6: The pages, from the real tables' shapes (descriptors generated from the source)

The pages are checked **without the game** by generating, from the real `FrontendItem` tables, a header of descriptors (kind, label, help length, range, step, option count, which pointers are present), and running the walker and the engine over them with fake getters. The real getters and setters are proved in the game (Task 10).

**Files:**
- Create (workspace repo): `tools/port/settings_descriptors.py`
- Create (game repo): `melee/pc/tests/atlas_settings_tables.inc` (generated, committed, `--check`ed), `melee/pc/tests/atlas_settings_test.c`
- Modify (game repo): `gmfrontend_settings.inc` (`off_reason` strings on the six `fcr_ready` rows in `gmfrontend_controls.inc`, nothing else here), `gmfrontend_atlas_set.inc` (create: the page-to-tab mapping)
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-settings`)

**Interfaces:**
Produces `atlas_settings_tables.inc`: for each table, `static const StubItem tbl_<name>[] = { { kind, "label", help_len, min, max, step, n_opts, has_get, has_set, has_format, has_visible, has_enabled, has_call, action }, ... };` and `static const StubTable all_tables[] = { { "fe_items_set_video", tbl_fe_items_set_video, 6 }, ... }`.

- [ ] **Step 1: The generator (failing first).** `tools/port/settings_descriptors.py` parses each table in `gmfrontend_settings.inc`, `gmfrontend_controls.inc` and `gmfrontend.c` with a small top-level-comma splitter (strings may hold commas; adjacent string literals concatenate), resolves `options` names to the count of strings in their `static const char* const` array, and writes the `.inc`; `--check` fails when the committed file differs. Positional fields are `kind, action, label, help, get, set, min, max, step, options, format, visible, call, enabled, off_reason`; omitted trailing fields are NULL or 0.

```python
"""Generate pc/tests/atlas_settings_tables.inc from the FrontendItem tables: python tools/port/settings_descriptors.py --write|--check"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")
GM = os.path.join(GAME, "src", "melee", "gm")
OUT = os.path.join(GAME, "pc", "tests", "atlas_settings_tables.inc")
FILES = ("gmfrontend_settings.inc", "gmfrontend_controls.inc", "gmfrontend.c")
TABLE = re.compile(r"static const FrontendItem (\w+)\[\] = \{(.*?)\n\};", re.S)
STRARR = re.compile(r"static const char\* const (\w+)\[\] = \{(.*?)\};", re.S)
FIELDS = ("kind", "action", "label", "help", "get", "set", "min", "max", "step", "options", "format", "visible", "call", "enabled", "off_reason")


def split_top(s):
    out, depth, cur, q = [], 0, [], False
    i = 0
    while i < len(s):
        c = s[i]
        if q:
            cur.append(c)
            if c == "\\":
                i += 1
                cur.append(s[i])
            elif c == '"':
                q = False
        elif c == '"':
            q = True
            cur.append(c)
        elif c in "({":
            depth += 1
            cur.append(c)
        elif c in ")}":
            depth -= 1
            cur.append(c)
        elif c == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        i += 1
    tail = "".join(cur).strip()
    if tail:
        out.append(tail)
    return out


def strlen_of(lit):
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', lit)
    return len("".join(parts))


def rows(body, arrays):
    out = []
    depth, start, items = 0, None, []
    for i, c in enumerate(body):
        if c == "{":
            if depth == 0:
                start = i + 1
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start is not None:
                items.append(body[start:i])
    for it in items:
        f = split_top(it)
        if not f or not f[0].startswith("FE_"):
            continue
        f += ["0"] * (len(FIELDS) - len(f))
        d = dict(zip(FIELDS, f))
        n_opts = 0
        if re.match(r"\w+$", d["options"]) and d["options"] in arrays:
            n_opts = arrays[d["options"]]
        out.append("    { %s, %d, %d, %s, %s, %s, %d, %d, %d, %d, %d, %d, %d, %d, %d }," % (
            d["kind"], 1 if d["action"] == "FE_DO_CALL" else 0, strlen_of(d["help"]), d["min"], d["max"], d["step"] or "0", n_opts,
            d["get"] not in ("0", "NULL"), d["set"] not in ("0", "NULL"), d["format"] not in ("0", "NULL"),
            d["visible"] not in ("0", "NULL"), d["enabled"] not in ("0", "NULL"), d["call"] not in ("0", "NULL"),
            1 if d["action"] == "FE_DO_CONTINUE" else 2 if d["action"] == "FE_DO_BACK" else 0))
    return out


def build():
    lines = ["/* generated by tools/port/settings_descriptors.py from the FrontendItem tables: do not edit */"]
    names = []
    for name in FILES:
        text = open(os.path.join(GM, name), encoding="utf-8", errors="replace").read()
        arrays = {m.group(1): len(re.findall(r'"', m.group(2))) // 2 for m in STRARR.finditer(text)}
        for m in TABLE.finditer(text):
            r = rows(m.group(2), arrays)
            lines.append("static const StubItem tbl_%s[] = {" % m.group(1))
            lines += r
            lines.append("};")
            names.append((m.group(1), len(r)))
    lines.append("static const StubTable all_tables[] = {")
    for n, c in names:
        lines.append('    { "%s", tbl_%s, %d },' % (n, n, c))
    lines.append("};")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    text = build()
    if a.write:
        open(OUT, "w", encoding="utf-8", newline="\n").write(text)
        print("wrote", OUT)
        return 0
    if open(OUT, encoding="utf-8").read() != text:
        print("settings_descriptors: out of date; run --write and review the diff")
        return 1
    print("settings_descriptors: up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run it once with `--write` and read the generated file against the sources: a row whose `help_len` is 0, or an unresolved `n_opts` for a choice with `options`, is a parser fault, not data.

- [ ] **Step 2: Write the failing page tests** (`pc/tests/atlas_settings_test.c`; it includes `atlas_settings_stub.h`, `atlas_style.h` and the generated `.inc`). One group of checks per page, from the counts of Task 0:

```c
static const StubTable *tbl(const char *n) { int i; for (i = 0; i < (int) (sizeof all_tables / sizeof all_tables[0]); i++) if (strcmp(all_tables[i].name, n) == 0) return &all_tables[i]; return NULL; }
static void page_counts(void)
{
    CHECK(tbl("fe_items_set_video")->n == 6 && tbl("fe_items_set_audio")->n == 3 && tbl("fe_items_set_controls")->n == 12);
    CHECK(tbl("fe_items_set_online")->n == 6 && tbl("fe_items_set_gameplay")->n == 10 && tbl("fe_items_remap")->n == 20 && tbl("fe_items_howto_online")->n == 6);
}
/* every text drawn on a row stays inside that row's rectangle: for each text whose baseline lies in a row, its right edge is inside the row */
static int texts_in_rows(const AtHits *h)
{
    int i, k;
    for (i = 0; i < REC.nt; i++) for (k = 0; k < h->n; k++) {
        const AtRect *r = &h->h[k].r;
        float w = fake_width(NULL, REC.t[i].role, REC.t[i].s), left = REC.t[i].x - (REC.t[i].align == AT_ALIGN_RIGHT ? w : REC.t[i].align == AT_ALIGN_CENTER ? w * 0.5f : 0.0f);
        if (REC.t[i].base > r->y + 2.0f && REC.t[i].base < r->y + r->h && left >= r->x - 0.01f && left < r->x + r->w && left + w > r->x + r->w + 0.01f) return i;
    }
    return -1;
}
static void every_row_is_drawable(void)                  /* per page, at 640 and 853: the style checks on every row kind the page contains */
{
    int t, w;
    for (t = 0; t < ntables(); t++) for (w = 0; w < 2; w++) {
        AtSink s; AtRect canvas = { 0.0f, 0.0f, w ? 853.0f : 640.0f, 480.0f };
        build_screen_from_descriptors(&SC, &V, &all_tables[t]);                  /* what the walker would submit, with fake values and the real help lengths */
        s = rec_sink(); at_render(&SC, &V, canvas.w, 1000.0, 1, &O, &s, &HITS);
        CHECK(texts_legible());
        CHECK(sty_text_inside(canvas, 0) == -1);                                  /* nothing leaves the canvas */
        CHECK(texts_in_rows(&HITS) == -1);                                        /* nothing runs out of its row: a label, a value and a reason fit or are cut */
    }
}
static void round_trips(void)                            /* Review Focus 2: min, max, step and wrap per row, through the same rule the walker uses */
{
    int t, i;
    for (t = 0; t < ntables(); t++) for (i = 0; i < all_tables[t].n; i++) {
        const StubItem *it = &all_tables[t].rows[i];
        int v;
        if (it->kind == FE_SLIDER && it->has_set) {
            CHECK(it->max > it->min);                                           /* a settable slider has a range */
            CHECK(at_item_apply(AT_VAL_SLIDER, it->min, it->max, it->step, it->max, +1, &v) == 0);       /* held at the top */
            CHECK(at_item_apply(AT_VAL_SLIDER, it->min, it->max, it->step, it->min, +1, &v) == 1 && v > it->min);
        }
        if (it->kind == FE_CHOICE) CHECK(it->n_opts == 0 || it->n_opts == it->max - it->min + 1);          /* the option strings cover the range */
        if (it->kind == FE_CHOICE && it->n_opts > 0) CHECK(it->n_opts <= AT_MAX_OPTS);
        CHECK(it->help_len > 0);                                                                           /* every row explains itself (the explainer's WHAT) */
    }
}
static void help_clamped(void)                           /* Review Focus 9: a 512-character mod help line is clamped with an ellipsis, not an overflow */
{
    int h = open_settings(5); char long_help[600]; AtSink s;
    memset(long_help, 'x', sizeof long_help - 1); long_help[599] = 0;
    gw_Ui_SetExplain(h, "MODS", "A MOD", long_help, "ON", "");
    CHECK(strlen(test_explainer_what(h)) <= 159 && strstr(test_explainer_what(h), "â¦") != NULL);
    s = rec_sink(); at_render(test_screen(h), test_view(h), 640.0f, 1000.0, 1, &O, &s, &HITS);
    CHECK(texts_legible());
    { int i, seen = 0; AtRect ex = test_explainer_rect(640.0f);
      for (i = 0; i < REC.nt; i++) if (strncmp(REC.t[i].s, "xxx", 3) == 0) {          /* the lines of the clamped rule text */
          float w = fake_width(NULL, REC.t[i].role, REC.t[i].s); seen++;
          CHECK(REC.t[i].x >= ex.x - 0.01f && REC.t[i].x + w <= ex.x + ex.w + 0.01f); }
      CHECK(seen >= 1 && seen <= 4); }                                              /* wrapped to at most 4 lines, all inside the explainer */
}
static void visible_rows_change(void)                    /* Review Focus 5: the Stick Dead Zone row (fsc_any_sdl) shows and hides; focus follows by id */
{
    int h = open_settings(2); submit_with_visible(h, "fe_items_set_controls", 1); gw_Ui_SetFocus(h, "i6");
    submit_with_visible(h, "fe_items_set_controls", 0);
    CHECK(strcmp(focused_id(h), "i7") == 0);
}
static void mods_41_rows(void) { CHECK(rows_in_record_for(41) == 41); }
```

`test_screen`, `test_view` and `test_explainer_rect` are accessors in `atlas_settings_stub.h` over the host slot and `at_layout` (`GW_UI_SEL_TEST` only). Register `atlas-settings` with `gw_ui_item.c` and the render sources. Run it; expected: failures.

- [ ] **Step 3: Make it pass.** Explainer for a settings row (the same in every page): `kicker` the tab's name (`VIDEO`), `title` the row's label upper-cased by the explainer part, `what` the row's `help` clamped to 159 characters, `now` the formatted value (`NOW 200%`), `from` empty; **no media well** (the controller diagram and the render-scale sketch of the mockup are not built, section 14); `Y` has no hint (no reset-page function exists). Tabs: `VIDEO, AUDIO, CONTROLS, ONLINE, GAME, MODS` for `FSP_VIDEO` to `FSP_GAMEPLAY` and the MODS table (`GAME` is the short name of GAMEPLAY, as in the mockup); the how-to page and the remap editor are **screens of their own** under CONTROLS (Task 8). Mods rows: `fsm_fill()` runs when the MODS tab opens (it does today in `fe_settings_from_menus`) and the mods' `help` (up to 512 characters) is clamped by the explainer. The six rows of `fe_items_remap` that use `fcr_ready` get `off_reason` `"Connect a controller to this port first."`; `fsc_any_sdl`'s row stays hidden when no SDL pad is present (no reason needed).
- [ ] **Step 4: Run** `python tools/port/settings_descriptors.py --check`, `python tools/port/settings_inventory.py --check`, `nt atlas-settings`, `nt atlas-walker`, `ppc src/melee/gm/gmfrontend.c`. Expected: all pass.
- [ ] **Step 5: Commit** (both repos), message `atlas step 5: the settings pages checked from the real tables' shapes; the off_reason strings`.

---

### Task 7: The retail rows: Rumble, Screen Display, Erase Data (and Language stays a hand-off)

**Files:**
- Modify (game repo): `melee/src/melee/mn/mndatadel.c`, `mndatadel.h` (split the erase calls from the animation), `melee/src/melee/gm/gmfrontend_settings.inc` (the new rows), `gmfrontend_atlas_set.inc`, `gmfrontend_menus.inc` (the four `FA_NATIVE` rows leave `fm_settings`; Language becomes a row in GAME that does the hand-off)
- Create (game repo): `melee/pc/tests/atlas_erase_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-erase`)

**What is known and what is not, from the sources read for this plan:**
- **Rumble.** The retail screen reads `GetRumbleSettingOfPort(port)` (the saved card data) and writes `gmMainLib_SetRumbleEnabled(port, on)` (`mnvibration.c:466-492`, `gmmain_lib.c:984-991`). The getter reads `save_data.x1CB0.rumble_enabled[port]` and the setter writes `GetGamePrefs()->rumble_enabled[port]`: **whether those are the same bytes is (unverified)**; Step 1 below settles it. The port also has a per-controller **Rumble** toggle in the remap options (`Controls_Option(5)`): the two must be told apart in words (decision for the owner, below).
- **Screen Display.** The retail screen flips `deflicker` with `gmMainLib_8015F588(x)` and stores it with `gmMainLib_8015F4F4(cursor)` then `lbCardGame_SaveChanges()` (`mndeflicker.c:54-70`); `gmMainLib_8015F588` calls `HSD_VISetConfigure(mode)`. **Whether the PC port honours the interlace and deflicker mode is (unverified)** (`pc/platform/shim_vi.c:2259 gw_VIConfigure`).
- **Erase Data.** `mndatadel.c` holds six erase operations (the five `case` arms of the cursor switch at lines 440 to 535, and `mnDataDel_8024EA6C` for "everything" with a language restore and a deflicker reset). **Every one of them also animates the retail screen's JObjs through `mnDataDel_804D6C68->user_data`**, which is NULL when that screen is not up: **calling `mnDataDel_8024E940()` or `mnDataDel_8024EA6C()` from Atlas would dereference NULL.** What each category clears, and what the retail text calls it, is **(unverified)**.
- **Language.** Stays the native hand-off: the same `pend_kind 3` request the `FA_NATIVE` row uses today (`fm.native_req`, `fm.native_kind = MENU_KIND_SETTINGS`, `fm.native_sel = SEL_SETTINGS_LANG`), return position `{ GM_MENU, MENU_KIND_SETTINGS, SEL_SETTINGS_LANG }` in `fm_position_for` (`gmfrontend_menus.inc`).

- [ ] **Step 1: Settle the unknowns by reading (no code yet), and put each answer in the commit message.**

```bash
cd "$GW_MELEE"
grep -n "rumble_enabled" src/melee/gm/*.h src/melee/gm/gmmain_lib.c src/melee/mn/*.c | head -20
grep -n "GetGamePrefs\|GetCardData" src/melee/gm/gmmain_lib.c | head -10
grep -n "deflicker\|IntDf\|vfilter" pc/platform/shim_vi.c | head -20
sed -n 430,540p src/melee/mn/mndatadel.c
```

Decide and record: (a) are `GetGamePrefs()->rumble_enabled` and `GetCardData()->save_data.x1CB0.rumble_enabled` the same storage, and does the PC rumble backend consult either; (b) does `shim_vi.c` act on the deflicker mode (if **not**, the Screen Display row **is not shown**: a row that does nothing is a lie, and the spec's "no new features" cuts both ways; say so in the report); (c) for each of the six erase operations, the exact ordered list of state-changing calls with the animation lines removed, and a name for the category from what it clears (**name a category only if the calls make it certain; otherwise label it "Data set N" and flag it to the owner**).
- [ ] **Step 2: Split `mndatadel.c` (failing test first).** The test, `pc/tests/atlas_erase_test.c`, cannot link the game file, so it tests the **plan table** the adapter will run, with fake callbacks, and a second check (below) binds the table to the split functions:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_erase.h"      /* a pure table: the ordered call ids of each category, libc-free, shared with the game side */

static int LOG[32], NLOG;
static void rec(int id) { if (NLOG < 32) LOG[NLOG++] = id; }

static void erase_plan_order(void)                                   /* ids are the names in gw_ui_erase.h, filled from Step 1's record */
{
    int c;
    CHECK(at_erase_categories() == 6);
    for (c = 0; c < at_erase_categories(); c++) {
        int n = at_erase_calls(c), k;
        CHECK(n >= 2);
        CHECK(at_erase_call(c, n - 1) == AT_ER_SAVE);                /* every category ends by saving the card exactly once */
        for (k = 0; k < n - 1; k++) CHECK(at_erase_call(c, k) != AT_ER_SAVE);
    }
}
static void erase_cancel_calls_nothing(void)                         /* Review Focus 6 */
{
    int c;
    for (c = 0; c < at_erase_categories(); c++) {
        NLOG = 0;
        CHECK(at_erase_run(c, 0 /* cancelled */, rec) == 0 && NLOG == 0);
    }
    NLOG = 0; CHECK(at_erase_run(-1, 1, rec) == 0 && NLOG == 0);     /* a bad category does nothing */
    CHECK(at_erase_run(99, 1, rec) == 0 && NLOG == 0);
}
static void erase_confirmed_runs_the_plan_once(void)
{
    int c, k;
    for (c = 0; c < at_erase_categories(); c++) {
        NLOG = 0;
        CHECK(at_erase_run(c, 1, rec) == at_erase_calls(c) && NLOG == at_erase_calls(c));
        for (k = 0; k < NLOG; k++) CHECK(LOG[k] == at_erase_call(c, k));
    }
}
int main(void) { erase_plan_order(); erase_cancel_calls_nothing(); erase_confirmed_runs_the_plan_once(); ATLAS_DONE("atlas erase"); }
```

`gw_ui_erase.h/.c` hold the table (an enum `AT_ER_*` of the retail calls observed: for example `AT_ER_8016505C`, `AT_ER_F464`, `AT_ER_801729EC`, `AT_ER_SAVE` = `lbCardGame_SaveChanges`, `AT_ER_DB80`, and so on, one id per distinct function, in the order Step 1 recorded) and `at_erase_run(category, confirmed, rec)`, which calls `rec(id)` for each call **only when `confirmed`** and returns the count. On the game side `mndatadel.c` gains `void mnDataDel_RunCall(int id)` (a `switch` over the ids calling the real functions) and `mnDataDel_Erase(int category)` (`at_erase_run(category, 1, mnDataDel_RunCall)`); **the retail screen's own handlers are changed to call the same function after their animation**, so the retail screen and Atlas run one list. Syntax-check: `ppc src/melee/mn/mndatadel.c` and `ppc src/melee/gm/gmfrontend.c`.
- [ ] **Step 3: The rows.** Rumble: under a `RUMBLE` group in CONTROLS, four toggles `Rumble, Port N` (visible only while that port has a controller: `HSD_PadCopyStatus[p].err == 0`), `get` `GetRumbleSettingOfPort(p)`, `set` `gmMainLib_SetRumbleEnabled(p, v)` plus `lbCardGame_SaveChanges()` **only if Step 1 shows the retail screen saves on exit** (it saves through the card write path; match it exactly), help `"Send rumble to this port during matches."`. Screen Display: a toggle `Flicker Filter` in VIDEO (only if Step 1 says the port honours it), `get` `gmMainLib_8015F4E8()`, `set` as the retail screen. Erase Data: an action row `Erase Data...` in GAME (group `DATA`, `AT_ITEM_DANGER`) that opens the **Erase submenu**, six action rows named from Step 1, each opening the dialog `gw_Ui_SetDialog(h, "ERASE <NAME>", "This cannot be undone.", "Erase", "Cancel", 2)`; the adapter runs `mnDataDel_Erase(category)` **only when `gw_Ui_SetDialogAnswer` returns 1**, then shows a `gw_Ui_SetNote(h, "Erased.", ok)`. Language: a row `Language` in GAME with value text `English` or `Japanese` (`lbLang_GetSavedLanguage()`: **which value means which is (unverified)**; read `mnlanguage.c:174` and `lbLang_IsSavedLanguageUS`), whose action does the existing hand-off. The four `FA_NATIVE` rows leave `fm_settings` (`gmfrontend_menus.inc:180-183`).
- [ ] **Step 4: The duplicate rumble, as a recorded owner decision (do not decide it silently).** The remap options have `Rumble` (this controller profile) and the retail row is per game port. Recommendation for the coordinator to put to the owner: keep both, label them `Rumble (this profile)` in the remap options and `Rumble, Port N` in CONTROLS, and say in each row's help which one it is. Until he answers, ship the labels as recommended.
- [ ] **Step 5: Run** `nt atlas-erase`, `nt atlas-settings` (counts change: update `settings_inventory_expected.json` and the page counts **in the same commit**, with the reason), the PowerPC checks. **Commit** (both repos), message `atlas step 5: Rumble, Screen Display and Erase Data as settings rows; the erase calls split from the retail animation; Language stays a hand-off`.

---

### Task 8: The remap editor as an Atlas screen over the unchanged `Controls_*` API

**Files:**
- Create (game repo): `melee/pc/tests/atlas_remap_test.c`, `melee/pc/tests/atlas_controls_fake.h` (a fake `Controls_*` model with a scripted clock)
- Modify (game repo): `melee/src/melee/gm/gmfrontend_atlas_set.inc` (the remap layer), `gmfrontend_controls.inc` (only: the screen's table stays; `fcr_frame` is called from the Atlas branch exactly as from the legacy one)
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-remap`)

**The screen.** Three tabs over the **same** table `fe_items_remap` (20 rows), presented by Atlas as:
- **INPUTS**: the controller rows (`Controller`, `Pick Controller`) and **one row per game input** (the 22 names in `fcr_targets`: `A`, `B`, `X`, `Y`, `Z`, `START`, `L click`, ..., `Analog R`). The row's value is `Controls_Binding(target, ...)`; **A** on a row = `fcr_target = row; Controls_Capture(fcr_target, fcr_also)`; **X** toggles `fcr_also` (Swap or Also, shown as two tags in the explainer: the mockup's `REPLACE` is not built, the code has two modes). Replaces the three rows `Game Input`, `Bind Input`, `Conflicts` (a presentation change over the same state: `fcr_target`, `fcr_also` are what they were).
- **PROFILE**: `Profile`, `New Profile`, `Rename Profile`, `Delete Profile`, `Preset`, `Assign to Port`, `Reset to Default`.
- **OPTIONS**: `Swap Sticks`, `Trigger Analog Off`, `Digital Shield`, `Main Dead Zone`, `C-stick Dead Zone`, `Rumble (this profile)`.
The explainer shows the live tester (`Controls_Tester`, the old `Game Receives` row) and the last result message (the legacy `messages[]` strings, now notes). `Done`/B returns to CONTROLS (`fcr_back`). The trail is `SETTINGS > CONTROLS > REMAP`. **Binding text is cached:** `Controls_Binding` is called for the 22 rows only when `Controls_Result()`, `Controls_Profile()`, `Controls_Port()` or the pad identity changes, and at most every 30 frames otherwise, never 22 times a frame.

- [ ] **Step 1: Write the failing test: the capture timeline, against a fake `Controls_*` with a scripted clock.** The legacy timeline (from `fcr_frame`, `ctl_poll`, `gw_Controls_Capture`) that the Atlas layer must reproduce:

```c
#include "atlas_check.h"
#include "atlas_controls_fake.h"       /* Controls_Menu/Capture/Cancel/Capturing/Result/Held/Binding... recording calls; a frame counter; a 100 ms heartbeat window */
#include "../../src/melee/gm/gmfrontend_atlas_remap.h"   /* the pure part of the layer: fas_remap_frame(), no game types */

static void heartbeat_every_frame(void)                               /* Review Focus 3 */
{
    int f;
    fake_reset(); remap_open(0);
    for (f = 0; f < 600; f++) { fake_tick(16); remap_frame(); CHECK(fake_editor_active()); }     /* ten seconds open: the editor flag never lapses */
    CHECK(fake_calls_menu() == 600 + 1);                                                          /* once per frame (the scene's own heartbeat), plus the open */
}
static void capture_timeline(void)
{
    remap_open(0); fake_pad_held(0);
    remap_press_a_on_row(5);                                           /* A on the START row */
    CHECK(fake_capturing() == 1 && fake_target() == 5);
    CHECK(remap_input_frozen() == 1);                                  /* the host reads nothing while capturing: the press that binds is not an accept */
    fake_tick(1000); fake_physical_press(7); remap_frame();            /* the player presses a new input */
    CHECK(fake_result() == 2 /* saved */ && fake_capturing() == 0);
    CHECK(remap_input_frozen() == 1);                                  /* STILL frozen: the legacy fcr_wait_release holds until the input is released */
    fake_physical_release(7); fake_tick(16); remap_frame();
    CHECK(remap_input_frozen() == 0);                                  /* released: input returns, primed from the held state (no stray accept) */
}
static void timeout_and_cancel(void)
{
    remap_open(0); remap_press_a_on_row(2);
    fake_tick(8001); remap_frame();                                    /* 8 second timeout (the legacy message "Timed out; not changed.") */
    CHECK(fake_capturing() == 0 && fake_result() == 3 && remap_message_is("Timed out; not changed."));
    remap_press_a_on_row(2); fake_chord_start_b(); remap_frame();      /* START+B on the ORIGINAL layout cancels: read natively, never through the host */
    CHECK(fake_capturing() == 0 && fake_result() == 4 && remap_message_is("Cancelled; not changed."));
}
static void messages_are_notes(void)
{
    int r;
    static const char *want[] = { "Original layout navigates; START+B restores.", "Press and release an input. START+B cancels. 8 seconds.", "Saved.",
        "Timed out; not changed.", "Cancelled; not changed.", "Defaults restored.", "Profile copied.", "All four profile slots are full.",
        "Conflict: bindings swapped.", "Conflict: both bindings kept.", "Could not save. Check settings storage; this change may be temporary." };
    for (r = 0; r < 11; r++) CHECK(strcmp(remap_message_for(r), want[r]) == 0);                   /* every legacy message survives, word for word, as a note */
    CHECK(remap_message_for(11) != NULL && remap_message_for(-1) != NULL);                         /* out of range: the default line, never a read past the array */
}
static void disconnect_mid_capture(void)
{
    remap_open(0); remap_press_a_on_row(1); fake_unplug(0); fake_tick(16); remap_frame();
    CHECK(fake_capturing() == 0 && remap_input_frozen() == 0);         /* ctl_poll cancels with result 4 when the device goes: input must not stay frozen forever */
}
static void bindings_cached(void)
{
    int before;
    remap_open(0); remap_frame(); before = fake_calls_binding();
    remap_frame(); remap_frame(); remap_frame();
    CHECK(fake_calls_binding() == before);                              /* nothing changed: no 22 calls per frame */
    fake_set_result(2); remap_frame(); CHECK(fake_calls_binding() == before + 22);
}
int main(void) { heartbeat_every_frame(); capture_timeline(); timeout_and_cancel(); messages_are_notes(); disconnect_mid_capture(); bindings_cached(); ATLAS_DONE("atlas remap"); }
```

`gmfrontend_atlas_remap.h` holds the **pure part** of the layer (`remap_frame`'s decisions: freeze while `Controls_Capturing() || wait_release`, result to message to note, the cache rule, the START+B check through an injected `pad_value(port, 0) & 0x1200`), with the `Controls_*` calls as extern prototypes the fake satisfies, exactly as Task 4's walker does for `gw_Ui_*`. Register `atlas-remap` with the fake. Run it; expected: compile errors.

- [ ] **Step 2: Implement** the layer: `fas_remap_frame()` is `fcr_frame()` moved, calling `gw_Ui_Freeze(h, frozen)` each frame and `gw_Ui_SetNote(h, message, kind)` instead of `fe_ol_notice`; the Atlas branch of `gm_Scene_Frontend_OnFrame` calls it **before** the host's events are polled, and while it returns true (the legacy "ordinary navigation is frozen") the branch **does not poll** events. The rows' events: `FAS_EV_ACCEPT` on an input row calls `fcr_target = row; fcr_bind()`; on the other rows the walker. **`fe.screen` stays `&fe_screen_remap`** (Task 1's static test fails otherwise), and the host's native screen id is `settings.remap`.
- [ ] **Step 3: Guard.** `python tools/port/test_menu_heartbeat.py` still passes; add one more static check there: `fas_remap_frame` is referenced only from the Atlas branch placed after the heartbeat. Run `nt atlas-remap`, `nt controls-remap` (unchanged, must still pass), `ppc src/melee/gm/gmfrontend.c`.
- [ ] **Step 4: Commit** (both repos), message `atlas step 5: the remap editor as an Atlas screen over Controls_*: capture freeze, release wait, heartbeat and the START+B cancel pinned by a timeline test`.

---
### Task 9: Key hints per row kind (logical glyphs) and a synthetic remap profile

Spec 9: hints are generated, drawn as glyph plus label; when a remap moves a logical button to another physical one, **the hint keeps the logical glyph**. Task 1 settled which game modes read the original layout; this task makes the hints follow the focused row and pins the glyph rule.

**Files:**
- Modify (game repo): `melee/src/melee/gm/gmfrontend_atlas_set.inc` (hint strings per focused row), `melee/pc/tests/atlas_settings_test.c`, `atlas_remap_test.c`

- [ ] **Step 1: Write the failing tests.**

```c
/* hints are a function of the focused row's kind; the labels are true to what the legacy rule does (A steps a slider or flips a toggle) */
static void hint_strings(void)
{
    char o[96];
    fas_hints_for(STUB_TOGGLE, 0 /* enabled */, 1 /* tabs */, o, sizeof o); CHECK_STR(o, "A:Change,L:Page,B:Back");
    fas_hints_for(STUB_SLIDER, 0, 1, o, sizeof o);                         CHECK_STR(o, "A:Change,L:Page,B:Back");
    fas_hints_for(STUB_CHOICE, 0, 1, o, sizeof o);                         CHECK_STR(o, "A:Change,L:Page,B:Back");
    fas_hints_for(STUB_NONE, 0, 1, o, sizeof o);                           CHECK_STR(o, "A:Select,L:Page,B:Back");     /* an action */
    fas_hints_for(STUB_TEXT, 0, 1, o, sizeof o);                           CHECK_STR(o, "L:Page,B:Back");               /* a readout: nothing to press A for */
    fas_hints_for(STUB_NONE, 1 /* disabled */, 1, o, sizeof o);            CHECK_STR(o, "L:Page,B:Back");               /* a disabled row offers no A */
    fas_hints_for(STUB_NONE, 0, 0 /* no tabs: the how-to page */, o, sizeof o); CHECK_STR(o, "A:Select,B:Back");
}
static void hints_fit_at_640(void)                         /* "a hint that does not fit is left off, with every one after it": nothing important may be lost at 640 */
{
    static const char *sets[] = { "A:Change,L:Page,B:Back", "A:Rebind,X:Swap,Y:Presets,B:Back", "A:Select,L:Page,B:Back" };
    int i;
    for (i = 0; i < 3; i++) {
        AtSink s = rec_sink(); int shown = 0, n = 0; const char *p;
        build_screen_with_hints(&SC, &V, sets[i]);
        at_render(&SC, &V, 640.0f, 1000.0, 1, &O, &s, &HITS);
        for (p = sets[i]; *p; p++) n += *p == ':';
        { int k; for (k = 0; k < HITS.n; k++) shown += HITS.h[k].kind == AT_HIT_KEY; }
        CHECK(shown == n);                                                                               /* every hint of the set is drawn and clickable at 640 */
        CHECK(texts_legible());
    }
}
static void hints_keep_the_logical_glyph(void)             /* spec 9: after a remap the hint still says A and B, in the A and B colours */
{
    AtSink s = rec_sink();
    fake_profile_swaps_a_and_b();                           /* a synthetic profile: logical A is physical B and the reverse */
    build_screen_with_hints(&SC, &V, "A:Rebind,B:Back");
    at_render(&SC, &V, 640.0f, 1000.0, 1, &O, &s, &HITS);
    CHECK(find_text("A") != NULL && find_text("B") != NULL);
    CHECK(count_color(AT_C_PAD_A) > 0 && count_color(AT_C_PAD_B) > 0);                                  /* the glyph colours are the logical buttons' */
    CHECK(find_text("Rebind") != NULL && find_text("Back") != NULL);
}
```

`fas_hints_for(vkind, disabled, tabs, out, cap)` is a pure function in the walker header (it builds the string `gw_Ui_SetKeys` takes); add it there with the tests. Run `nt atlas-walker`, `nt atlas-settings`; expected: failures first.

- [ ] **Step 2: Implement** `fas_hints_for`, and call `gw_Ui_SetKeys` from the adapter **only when the focused row's kind or disabled state changes** (not every frame). Where the keyboard or the mouse was last used, step 1's hint switching is not built (spec 9, [image kit-4]); say so in `docs/scripting.md` and do not fake it.
- [ ] **Step 3: Run, commit** (game repo), message `atlas step 5: key hints per row kind; the logical glyph rule pinned with a synthetic remap profile`.

---

### Task 10: Entry, return and position: first boot, Language, Back, Mods (needs G4)

**Files:**
- Modify (game repo): `melee/src/melee/gm/gmfrontend.c` (`fe_settings_from_menus`), `gmfrontend_menus.inc` (the SETTINGS node and its position rows), `gmfrontend_atlas_set.inc`
- Create (workspace repo): `tools/port/test_settings_positions.py`

**The design.** The SETTINGS list node (`fm_settings`) is replaced, as the tabs replace it: the main menu's SETTINGS entry (an `FA_PAGE` with page `0`, as the list's rows were) opens the tabbed Atlas screen at VIDEO through the existing `fe_settings_from_menus(page)`. Entry points and what each must do:

| Entry | Today | After step 5 |
|---|---|---|
| Main menu SETTINGS | the list, then a page | the tabbed screen at VIDEO (`fe_settings_from_menus(0)`) |
| Main menu MODS (step 2) | `Settings > Mods` page | the tabbed screen at MODS (`fe_settings_from_menus(FSP_MODS)`); step 7 later retires it |
| First boot (`fm_first_boot`, `pend_kind 6`, `pend_a 2`) | CONTROLS page once | the tabbed screen at CONTROLS, once, with the how-to row reachable |
| Back from any tab | the SETTINGS list on item `0x41 + page` (`fm_back_kind`, `fm_back_sel`) | the main menu, on SETTINGS (set `fm_back_*` to the main-menu item the entry came from) |
| Language row (GAME tab) | `FA_NATIVE` hand-off, return `{ GM_MENU, MENU_KIND_SETTINGS, SEL_SETTINGS_LANG }` | the same hand-off request (`fm.pend_kind = 3`, kind `MENU_KIND_SETTINGS`, sel `SEL_SETTINGS_LANG`); the **return** reopens the tabbed screen at GAME with the focus on the Language row |
| How-to page, remap editor | their own screens; Back to CONTROLS | unchanged (Task 8) |

- [ ] **Step 1: Write the failing static and table tests.** `tools/port/test_settings_positions.py` pins the rows that must survive and the new return rule by reading the source (the position table is data in `gmfrontend_menus.inc`):

```python
"""Settings entry and return positions: python tools/port/test_settings_positions.py"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")


def read(n):
    return open(os.path.join(GAME, "src", "melee", "gm", n), encoding="utf-8", errors="replace").read()


class Positions(unittest.TestCase):
    def test_language_return_row_survives(self):
        self.assertIn("{ GM_MENU, MENU_KIND_SETTINGS, SEL_SETTINGS_LANG }", read("gmfrontend_menus.inc"))

    def test_first_boot_opens_controls(self):
        m = read("gmfrontend_menus.inc")
        self.assertRegex(m, r"first boot -> SETTINGS > CONTROLS")
        self.assertRegex(m, r"fm\.pend_a = 2;")

    def test_retail_rows_left_the_list(self):
        m = read("gmfrontend_menus.inc")
        for name in ("RUMBLE", "SCREEN DISPLAY", "ERASE DATA"):
            self.assertNotIn('{ "%s",' % name, m)

    def test_language_is_a_row_that_hands_off(self):
        s = read("gmfrontend_atlas_set.inc")
        self.assertIn("SEL_SETTINGS_LANG", s)
        self.assertRegex(s, r"pend_kind\s*=\s*3")

    def test_every_page_enters_through_one_function(self):
        g = read("gmfrontend.c")
        self.assertEqual(len(re.findall(r"static void fe_settings_from_menus\(int page\)\s*\{", g)), 1)


if __name__ == "__main__":
    unittest.main()
```

Plus a native table test through step 2's position oracle (`fm_position_for` as the legacy table): for each of the five entries above, a case in the oracle's own test file (step 2 builds it; add the rows) with the expected `(MenuKind, selection)` or tab and focus id. **If step 2's oracle is not present, write the five cases as comments in the commit and mark the task unverified in the report: do not invent the oracle.** Run the python test; expected: fails (rows still in the list).
- [ ] **Step 2: Implement.** `fe_settings_from_menus(page)` selects the tab (`gw_Ui_SetTabs(h, 6, "VIDEO,AUDIO,CONTROLS,ONLINE,GAME,MODS", page)`), sets `fe.screen = &fe_screen_settings[page]` **on every tab change** (so `fe_is_settings(fe.screen)`, the notice rule and the heartbeat's screen test keep working), calls `fsm_fill()` when the MODS tab opens, `fe_settings_apply_online()` as before, and remembers the focused item id per tab (`fas_tab_focus[6]`). The Language return: in `gmFrontend_NativeReturn`, a `(MENU_KIND_SETTINGS, SEL_SETTINGS_LANG)` return opens the screen at GAME and sets `fas_pending_focus` to the Language row's id; the first submit applies it through `gw_Ui_SetFocus`. Delete the four retail rows and the `fm_settings` node from the tree **only after** the step 2 oracle accepts the new entries.
- [ ] **Step 3: Run** the two python tests, `python tools/port/test_menu_heartbeat.py`, `ppc src/melee/gm/gmfrontend.c`, `python tools/port/fe_menu_sweep.py` **if it runs without a disc (unverified)**.
- [ ] **Step 4: Commit** (both repos), message `atlas step 5: settings entry, first boot, Language return and Back through the tabbed screen`.

---

### Task 11: The in-game proof (a checklist for a Windows agent or the owner; nothing before this proves a look)

**Who and when.** Only when the owner is away, or let him do it. Second monitor (ask the coordinator for the position), `MELEE_VOLUME=0`, never hidden or minimised, stop by PID, never by image name. A **real pad** is needed for the capture items: a run without one writes "not run" for them. No screenshots as proof (one allowed only to diagnose how something looks). **Erase Data: use a copy of the settings and memory-card data made for this test (`MELEE_PROFILE` or the lane's own `userdata`, never the owner's); say which in the report.**

- [ ] **Step 1: Build and confirm the exe has the code** (root `CLAUDE.md` fact 1):

```bash
tools/port/build.sh
grep -a "frontend: Atlas settings" "$GW_BUILD_ROOT/melee-pc.exe" | head -1     # the exact log string your adapter prints on open
grep -a "Press and release an input. START+B cancels. 8 seconds." "$GW_BUILD_ROOT/melee-pc.exe" | head -1
```

Both must print a line (a stale exe prints nothing).
- [ ] **Step 2: Launch and say yes or no to each** (a 4:3 window `MELEE_WINDOW_W=960 MELEE_WINDOW_H=720`, then 16:9 `1920 x 1080`, then once at `640 x 480`; `tools/port/run.sh atlas5-proof` with a scene that reaches the menus, ACE disc for anything that plays):
  1. **Every tab** (VIDEO, AUDIO, CONTROLS, ONLINE, GAME, MODS): the rows and values read as the legacy page did; L and R switch tabs; the tab strip never shows a tab with nothing in it; the explainer shows the row's help and its current value; text is legible at 640 and nothing runs outside a row.
  2. **Change a value and see it applied**: Render Scale, Frame Rate, VSync, Show FPS, Reduced Motion, Master Volume (steps of 5), Music/Effects (steps of 5 across -100 to 100), Output, an Online Input Delay, a Gameplay stock count. Each takes effect at once and **survives a restart** (the lane's `settings.cfg`).
  3. **Value rules**: a choice wraps at both ends; a slider stops at both ends (the "can't go further" bump); A on a toggle flips, A on a slider steps +1 step; Main Dead Zone moves by 1.
  4. **Text rows**: Player Name and Server: A starts the edit; typing works; **Enter ends it and does not also reopen it; Escape cancels and does not also leave the screen**; a pad can also edit (up and down cycle, left and right move).
  5. **Focus**: change a value that shows or hides rows (Stick Dead Zone appears with an SDL pad): the focus stays put or moves to the next row, never to nothing; switch tabs and come back: the focus is where you left it.
  6. **Mouse**: hover focuses a row, a click acts as A, the wheel steps a hovered value or scrolls, right click is B, a click on a tab switches it, key hints are clickable; a resting pointer does not steal focus from the pad.
  7. **The remap editor (a real pad)**: open it (CONTROLS > Remap); pick the controller; A on an input row starts a capture and the row says to press an input; **press a new input: it is saved, and the A you pressed to start does not also bind or accept**; hold the new input: navigation stays frozen until you release; `START+B` on the original layout cancels a capture; 8 seconds of nothing times out with the legacy message; a swapped binding and an "also" binding both work (X toggles the mode); profiles: new, rename, delete, preset, assign; the options page; the live tester shows what the game receives; **hold START+B for 2 seconds anywhere in the menus: defaults restore** (the legacy chord); unplug the pad mid-capture: the screen is not stuck frozen.
  8. **Hints after a remap**: with a profile that moves A, the hints still say A and B (logical); say in the report what the CSS in Versus does with that profile (Task 1 finding: the CSS reads the remapped pad).
  9. **Rumble**: the four port toggles (only ports with a controller); a change is felt in a match, and persists. **Screen Display**: present only if Task 7 said the port honours it. **Language**: the row hands off to the retail screen and **returns to the GAME tab on the Language row**. **Erase Data**: the dialog opens with Cancel focused; B and Cancel change nothing (check a record before and after); Erase with a fresh A clears **only** the named category; "Erased." appears.
  10. **First boot**: delete `onboarded` from the lane's `settings.cfg`, start: the CONTROLS tab opens once.
  11. **Online**: with a second client and the owner's consent, open Settings in a room: it draws, mouse and keyboard work, nothing is masked, no desync; otherwise write "not run".
  12. **Cost**: the host's `ui:` log lines for entries and `cost_ms` with the MODS tab (the largest page) up: at most 0.5 ms, under 3,000 entries; 120 fps holds with `MELEE_FPS=120`. **Reduced Motion** on: tab changes and the fade are cuts.
  13. **Leaks**: leave Settings by Back, by a Language hand-off, by a forced scene change: nothing of the screen stays up in the next scene.
- [ ] **Step 3: Report** yes or no for each item with a line per no, and say plainly which were not run and why. The owner decides whether the look is accepted.

---

### Task 12: Retire the legacy settings drawing (after the owner's look; not in the same session)

- [ ] **Step 1: Delete, each with a grep proving nothing else reads it.** `gmfrontend_kitlist.inc` row drawing for settings screens (the file stays while the online rows screen, `fe_items_online`, and any list not yet moved still use it: **step 6 retires the rest**; delete only what a grep shows is unreferenced: `grep -n "fk_" melee/src/melee/gm/*.c melee/src/melee/gm/*.inc`), `widgets_layout.json` and `list_layout.json` **only if** the online rows no longer use them (they are the legacy kit's widget art; step 6 may be the last reader: if so, move this bullet to step 6's list and say so), the legacy widget art in `menu/out_kit` that Atlas replaces (`menu/pipeline/build.py` outputs for the toggle, slider, choice and their glyph pieces; update `menu/README.md`'s texture table in the same change), the `fm_settings` node and its `FA_NATIVE` rows (already removed in Task 10).
- [ ] **Step 2: Guards.** `grep -rn "fe_items_set_\|fe_screen_settings" melee/src` still finds the tables (they are the source of truth and stay); `nt atlas-*`, `nt controls-remap`, the Lua baselines, `python tools/port/settings_inventory.py --check`, `python tools/port/settings_descriptors.py --check`, `python tools/port/test_menu_heartbeat.py`, `python tools/port/test_settings_positions.py` pass.
- [ ] **Step 3: Docs in the same change.** `docs/TERMINOLOGY.md`: **value row** (a list row that carries a value: toggle, choice, slider, readout), **readout** (a row that only shows a value), **table walker** (the game-side code that turns a `FrontendScreen` into rows), **freeze** (an input hold during text entry or a capture). `docs/scripting.md`: the value API (Task 3) and the updated "not built" list (per-frame `get`, device-switching hints, mouse-wheel stepping of a Lua value). `menu/CLAUDE.md`: the retirement. Nothing public names a private branch or path.
- [ ] **Step 4: Commit** (both repos), message `atlas step 5: retire the legacy settings drawing and widget art`.

---

## Self-review

**Spec coverage (13.5).**

| 13.5 item | Where |
|---|---|
| Pages VIDEO, AUDIO, CONTROLS (+ remap editor, how-to), ONLINE, GAMEPLAY, the Reduced motion row | Tasks 4, 5, 6 (pages as tabs), 8 (remap), Task 6 step 3 (how-to stays a screen; Reduced Motion is the existing VIDEO row) |
| Retail rows Rumble, Screen Display, Erase Data | Task 7 (Rumble and Erase; Screen Display only if the port honours it) |
| Language stays a native hand-off | Task 7 step 3 and Task 10 (return to the GAME tab) |
| Tab strip over pages, toggle, choice, slider as tables through the adapter | Task 5 (tabs, from step 4's record), Task 2 (value rows), Task 4 (the walker) |
| The remap editor's capture state stays in `gmfrontend_controls.inc` and `Controls_*`; hints per section 9 | Task 8 (layer only), Task 9 |
| Retired: kitlist row drawing, `widgets_layout.json`, `list_layout.json`, the legacy widget art | Task 12 (conditional on step 6, stated) |
| Verified without the game: every page as a table through a stub adapter; `controls_remap_test.c` still passes; hint tests with a synthetic profile | Tasks 4 and 6 (walker and generated descriptors), baselines in every task, Task 9 |
| Must be seen: each page, a change applied, the capture flow with a real pad, hints after a remap, Erase's confirm | Task 11 |
| Needs added to the engine: slider `step`, a get/set value API | Task 2 (the rule, the model), Task 3 (`step`, `set_value`, `value` for Lua); native tables get live values from the walker, every frame |

**What step 5 added that step 1 did not have (the answer to "what must step 5 add").** (1) a slider **`step`** (`AtItem.vstep`), (2) engine-owned **choice options** (`opt[]`), (3) a **value write and read** API without re-registering (`gd.ui.set_value`, `gd.ui.value`; native tables are live through the walker), (4) **readout rows**, **group headings**, **disabled reasons**, (5) **64 rows** per list, (6) the legacy change rule as one pure function used by tables and Lua, (7) **tabs** (built once, in step 4 Task 4, used here), (8) the **freeze** with held-button priming, (9) a **Cancel-first dialog** fed by native code.

**Gaps, deviations and unverified items.**
1. **Screen Display** is shown only if the port honours the deflicker mode; **Rumble** storage (one byte or two) and whether the PC backend reads it, the **erase categories** (what each clears and what to call it), the retail **language values**, **which tab the 4:3 and wide layouts** need, and whether **`fe_menu_sweep.py`** runs without a disc are **(unverified)**; each task that depends on one says how to settle it.
2. **Menus follow the remap in the CSS but not in hubs and settings** (Task 1): an existing property, reported not changed.
3. **Mockup rows that do not exist in the code** (Window mode, Performance record, Reset page, the controller diagram, a Replace mode) are not built; the remap editor shows **Swap and Also** only.
4. **The Rumble duplicate** (per-port retail setting and per-profile option) is an owner decision recorded in Task 7 step 4; the recommended labels ship meanwhile.
5. **No per-frame Lua `get`** (a Lua call per row per frame inside the 50 ms budget): Lua screens call `set_value`. The spec's `get` is met for native tables only.
6. **Nothing here was compiled or run.** Where a legacy rule and a check disagree, the legacy code wins and the check changes with a note in the commit.
7. **Step 6 and `fe_items_online`:** the VERSUS > ONLINE rows screen still uses the legacy list drawing; Task 12 deletes only what is unreferenced.

**Placeholder scan.** Every unknown is named with the command or file that settles it; shim names that depend on step 2 are marked `spec` and replaceable in one table.

**Type and name consistency.** `AtItem` additions and `at_item_apply`, `at_item_text` (Task 2) are used unchanged by Tasks 3, 4, 6; `FasVis`, `FAS_EV_*`, `FAS_FX_*`, `fas_table_submit`, `fas_table_event` (Task 4) by Tasks 5, 6, 8, 9; the `gw_Ui_Set*` shims (Tasks 4, 5) by 7, 8, 10; `AtTab` and `AT_HIT_TAB` come from step 4 Tasks 4 and 5 (gate G5); `FrontendItem.off_reason` (Task 4) by Tasks 6 and 7.

**Review Focus pinned.** 1: Task 2 and Task 6 with the style checks; 2: Task 2 `apply_*`, Task 6 `round_trips`, Task 4 `legacy_*`; 3: Task 8 and Task 1; 4: Task 5 `freeze_swallows_everything`; 5: Task 5 `tab_focus_is_per_tab`, `refocus_by_id`, Task 6 `visible_rows_change`; 6: Task 7 `erase_*`, Task 5 `dialog_defaults_to_cancel`; 7: Task 3, Task 5 `owner_native_vs_mod`; 8: Task 10; 9: Task 2 `capacity`, Task 6 `mods_41_rows`, `help_clamped`.

**Execution recommendation.** A fresh subagent per task with a review between tasks for Tasks 1 to 4 (self-contained, each ends in a test the reviewer can run); Tasks 5 to 8 and 10 by one agent in order (they share the shim vocabulary and the adapter); Task 9 can go to a fresh agent; Task 7's reading steps first, as a separate pass whose written answers the coordinator reads before any code; Tasks 11 and 12 for a Windows agent or the owner, in that order, not in one session. **Build step 4's Tasks 1, 4 and 5 before Task 5 of this plan.**
