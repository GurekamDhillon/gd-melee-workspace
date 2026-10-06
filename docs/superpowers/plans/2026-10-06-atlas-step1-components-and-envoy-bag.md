# Atlas step 1: components and the Envoy bag: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Atlas component set (parts, screen description, layout, focus, input, stack) as host-native C with a `gd.ui` Lua binding, and prove it by drawing the Envoy bag screen through it behind a switch, with the legacy bag kept as the fallback.

**Architecture:** Pure C units (`melee/pc/platform/gw_ui_*.c`) hold tokens, layout, text fit, focus, input events, the screen record, the stack and the parts; they draw only through a small `AtSink` interface, so they compile and run in standalone native tests with a recording sink and no game. A thin host adapter (`gw_script_ui.inc`, included by `gw_script.c`) turns a Lua table into the screen record, polls pad, mouse and keyboard, calls the Lua handlers, and sends the sink's output into the existing `gd.kit` quad list. The Envoy bag becomes a description built from the existing `run_screen.lua` cell data (`atlas_bag.lua`), switched on by a console command.

**Tech Stack:** C11 (host, built by `tools/port/build.sh` with the repo's clang for `i686-pc-windows-msvc`), Lua 5.4 (mod code and offline tests, `lua` on PATH), Python 3 with Pillow and fontTools (font and token generators), the existing `tools/port/native_test.sh` harness.

**Spec:** docs/superpowers/specs/2026-10-06-menu-reunification-design.md

## Global Constraints

Exact values are copied from the spec; if a task seems to need a different value, stop and ask the coordinator.

- **Canvas:** 640x480 logical px; width follows the window (`w = 480 x aspect`, never under 640). Compact arrangement for `w < 760`, wide for `w >= 760`; content at most 1140 wide, centred.
- **Text:** minimum 12 px at 640x480. Fit rule: too wide steps down one role of the same face, then truncates with an ellipsis; never squash. Atlas role set: `a_cap12 a_cap14 a_cap16 a_cap20` (Barlow Condensed SemiBold, tracked +0.10 em), `a_title 28`, `a_hero 44`, `a_display 64` (Barlow Condensed Bold; hero and display caps only), `a_body12 a_body14 a_row16` (Source Sans 3 Semibold), `a_num12 a_num14 a_num16` (Hasklug Medium).
- **Depth and shape:** flat quads only, no shadows, gradients or curves; E1 plate and E2 row or cell have a 3 px front edge, modal 6 px; chamfers on two opposite corners only (8 px panes and modal, 5 px rows, buttons, notes, tags, 3 px cells). Focus is three cues at once: lift 2 px, ember front edge, tick (rows) or four registration brackets (cells).
- **Motion on the UI clock (ms):** focus lift 80, tab 120, explainer swap 100, dialog 140, note 160 in and 3 s hold, turntable 12 s per turn at rest and 6 s in focus. A Reduced motion setting turns every tween into a cut.
- **Budgets:** the kit quad list is 16,384 per frame (`KQ_MAX`, `gw_kit.c:1155`) shared with every script draw; one Atlas screen is capped at 4,096 entries and warns at 3,000. Model cells: at most 512 triangles per model. Script time: 50 ms or 2,000,000 instructions per call. Target at most 0.5 ms per frame for any Atlas screen, inside the 120 fps frame of about 8.3 ms.
- **Online:** `gd.ui` is presentation only and allowed online. `gd.input_mask` and `gd.input_chord` stay refused online (`gw_script.c:838-844, 1893-1900`); Atlas never masks the pad itself in step 1. No script hook runs on a resimulated frame. Mouse and keyboard input never reach the pads or the netplay stream. A screen's state is never an input to the simulation.
- **No disc-derived data, ever,** in either repo. No screenshots as verification (the only exception: diagnosing how a visual looks). Every outside tool, font or idea is named with a link in the same change (Barlow Condensed: Jeremy Tribby, https://github.com/jpt/barlow, SIL OFL 1.1).
- **Naming:** C identifiers `at_*` / `At*`, files `gw_ui_*`, Lua `gd.ui`, role names `a_*`. "Atlas" means this system; the engine's "font atlas" and "texture atlas" keep their qualifier. "Legacy menu kit" means everything the port draws for menus today.
- **English only** in code, docs and strings.
- **Process rules (this machine):** no game, launcher or browser window is launched while the owner is at the machine (a window steals focus); the in-game task runs only when he is away, on the second monitor, `MELEE_VOLUME=0`. Never terminate processes by image name (no `taskkill /IM`, no `pkill melee`): stop only a process you started, by its PID. Build only through `tools/port/build.sh`, in a private worktree made by `tools/port/agent_new.sh`; never raw clang for the game (the standalone native tests go through `build.sh --native-test`, which the `nt` helper in the Preflight wraps). Windows only; Git Bash.
- **Two repositories.** The game repo is `melee/` (branch `pc-port`; your worktree is a branch `agent/<name>` of it); the workspace repo is the root (tools, docs, `menu/`, `CREDITS.md`). Each task says which one a commit goes to. Generated build output (`gw_mex_bridge.c`) churn is normal and is not committed by you.

## Review Focus

The failure modes the spec implies that no ordinary happy-path test exercises, most likely to bite a player first. Each is pinned by a named test in the task that owns the code.

| # | What goes wrong for the player | Pinned by |
|---|---|---|
| 1 | **Focus is lost or lands on nothing after the bag changes** (merge, discard, equip: the cell list shrinks or reorders while a cell has focus). | Task 5 `refocus_*` checks (`at_screen_refocus`); Task 14 Lua test `focus survives merge and discard` |
| 2 | **Long real strings at 640x480**: a long drive name or a three-rule explainer overflows the narrow 160 px pane or drops under 12 px. | Task 2 `fit_*` and `wrap_*` checks; Task 9 render test `long strings stay inside the panes at 640` |
| 3 | **Empty, locked and disabled cells**: A on a locked slot or an empty slot must not crash, must not act as a drive, and a disabled row must not fire its handler; they must still take focus. | Task 5 `accept_semantics`; Task 13 Lua tests `locked and empty cells have no drive actions` |
| 4 | **Wide and ultrawide windows and the mouse**: hit rectangles must follow the arranged (not the authored) rectangles at 853 and 1706 wide, a pointer resting still must not steal focus from the pad, and a pointer off the picture (-1000) must do nothing. | Task 4 `mouse_*` checks; Task 9 `hits follow the layout at three widths` |
| 5 | **Online**: the screen must still draw and take mouse and keyboard in a netplay session, Atlas code must never call `input_mask`, and nothing may run on a resimulated frame. | Task 13 Lua test `netplay: described, never masked`; Task 11 binding test (handlers do not run when `gs_may_run` says no) and its guard greps; Task 18 check in a real room |

---

## File structure

Game repo (`melee/`), all host-native C unless noted. One responsibility per file.

| File | Create/Modify | Responsibility |
|---|---|---|
| `pc/platform/gw_ui_tokens.h` | Create (generated) | colours, sizes, timings as `AT_C_*`, `AT_PX_*`, `AT_MS_*` macros; never hand-edited |
| `pc/platform/gw_ui_layout.h/.c` | Create | `AtRect`, the role table, text fit and wrap over an injected width function, the four-place layout for compact and wide, list scrolling |
| `pc/platform/gw_ui_focus.h/.c` | Create | focus movement on blocks of cells (the legacy rule), held-direction repeat |
| `pc/platform/gw_ui_input.h/.c` | Create | pad, keyboard and mouse into one event type; hit list type |
| `pc/platform/gw_ui_val.h/.c` | Create | a tiny value tree (`AtvArena`) so the Lua-to-screen conversion is testable without Lua |
| `pc/platform/gw_ui_screen.h/.c` | Create | `AtScreen`, `AtView`, conversion from the value tree, validation, focus helpers, refocus |
| `pc/platform/gw_ui_stack.h/.c` | Create | screen stack and the tween |
| `pc/platform/gw_ui_parts.h/.c` | Create | every part, drawn through `AtSink` |
| `pc/platform/gw_ui_render.h/.c` | Create | composes one screen from its parts and records hit rectangles |
| `pc/platform/gw_kit.c`, `gw_kit.h` | Modify | `gw_Kit_DrawPoly4`, tracking, more roles and kerning room |
| `pc/platform/gw_script_ui.inc` | Create | the `gd.ui` Lua binding, the host sink, the tick and draw passes |
| `pc/platform/gw_script.c` | Modify | include the binding, register `gd.ui`, call its tick and draw, isolate the table |
| `pc/tests/atlas_check.h`, `atlas_fake.h` | Create | test macros, a fake width function, a recording sink |
| `pc/tests/atlas_*_test.c` | Create | one native test per unit (tokens, layout, focus, input, screen, stack, parts, render) and one for the Lua binding (`atlas_binding_test.c`, which includes `gw_script_ui.inc` against stand-ins and a real Lua state) |
| `pc/tests/atlas_ui_stub.lua`, `atlas_ui_stub_test.lua` | Create | an offline `gd.ui` stand-in with the same contract, and its own test |
| `pc/tests/envoy_atlas_bag.lua` | Create | offline tests of the Envoy description |
| `pc/tests/envoy_run_ux.lua` | Modify | load the new module; one integration check on the real `RunScreen` |
| `pc/scripts/examples/envoy/scripts/atlas_bag.lua` | Create | the bag as a `gd.ui` description plus the attach glue |
| `pc/scripts/examples/envoy/scripts/run_screen.lua` | Modify | two hook lines (attach on open, detach on close) |
| `pc/scripts/examples/envoy/scripts/run_host.lua` | Modify | the `uxatlas` console command |
| `pc/scripts/examples/envoy/scripts/main.lua` | Regenerate | by `tools/port/envoy_bundle.py` |
| `pc/scripts/examples/demos/atlas-screen/` | Create | a single-feature demo mod (a list, a grid, a note, a dialog) |

Workspace repo (root).

| File | Create/Modify | Responsibility |
|---|---|---|
| `menu/pipeline/atlas_tokens.py`, `test_atlas_tokens.py` | Create | tokens from the concept's `tokens.css` to JSON and the C header |
| `menu/atlas/tokens.json` | Create (generated) | the one token file every consumer reads |
| `menu/pipeline/kit.py`, `font_atlas.py` | Modify | the Atlas role set, faces and checks |
| `menu/pipeline/test_atlas_fonts.py` | Create | pipeline checks, including sync with the C role table and loader limits |
| `menu/Barlow/` | Create | the two Barlow Condensed files and the OFL text |
| `menu/out_kit/font/*` | Regenerate | `font_a_*` pages and the merged manifest |
| `tools/port/native_test.sh` | Modify | the nine `atlas-*` native test cases |
| `tools/port/envoy_bundle.py` | Modify | add `atlas_bag` to `ENVOY_MODULES` |
| `tools/release/licenses/BarlowCondensed-OFL-1.1.txt`, `THIRD-PARTY-NOTICES.txt` | Create/Modify | the font ships, so its licence ships |
| `CREDITS.md`, `docs/scripting.md`, `docs/TERMINOLOGY.md`, `menu/CLAUDE.md` | Modify | credit, the `gd.ui` reference, the terms |

## Preflight (once, before Task 1; not a task)

- [ ] **Step 1: Read the three files that explain the rules.** `CLAUDE.md` (root), `docs/NEXT-SESSION.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md`, and the spec sections 4 to 8 and 13.1.
- [ ] **Step 2: Make a private lane and fix the shell.** The main workspace checkout (call it `MAIN`; it is the directory that holds `_toolchains/`, `_build/` and `.env`) is where the toolchain lives. You edit the game repo in your own worktree and the workspace repo in your own worktree of it, and run the tools from `MAIN` (or through the helper below). In Git Bash:

```bash
export MAIN="<the workspace root: the directory that contains tools/ and _toolchains/>"
cd "$MAIN" && tools/port/agent_new.sh atlas1
git -C "$MAIN" worktree add worktrees/ws-atlas1 -b ws/atlas1
```

`agent_new.sh` prints `worktree  .../worktrees/atlas1`, `root      .../_build/agents/atlas1`, a hardlink count, and the `export` lines to use (`GW_MELEE`, `GW_BUILD_ROOT`). Then, in every new shell:

```bash
export MAIN="<as above>"; export WS="$MAIN/worktrees/ws-atlas1"; export GW_ROOT="$MAIN"
export GW_MELEE="$MAIN/worktrees/atlas1"; export GW_BUILD_ROOT="$MAIN/_build/agents/atlas1"     # as agent_new.sh printed them
nt() { GW_ROOT="$MAIN" GW_MELEE="$GW_MELEE" GW_BUILD_ROOT="$GW_BUILD_ROOT" bash "$WS/tools/port/native_test.sh" "$1"; }
```

`nt NAME` is `tools/port/build.sh --native-test NAME` but runs YOUR copy of `native_test.sh` (the one you edit in `$WS`), compiled with the shared toolchain against your game worktree; plain `build.sh --native-test` would run the main checkout's copy and never see your new test cases. Where each command runs: workspace-repo commands (`python menu/pipeline/...`, `python tools/port/envoy_bundle.py`, doc edits, workspace commits) in `$WS`; game-repo commands (`lua pc/tests/...`, game commits) in `$GW_MELEE`; full builds and runs (`tools/port/build.sh`, `tools/port/run.sh`) in `$MAIN` with the exports above. The game repo worktree is on branch `agent/atlas1`, the workspace one on `ws/atlas1`; "workspace repo" and "game repo" in every commit step mean those two.
- [ ] **Step 3: Record the baselines** (they must still pass at the end):

```bash
cd "$GW_MELEE" && lua pc/tests/envoy_run_ux.lua | tail -1
cd "$GW_MELEE" && lua pc/tests/grid_inventory.lua | tail -1
nt view-canvas | tail -2
```

Expected: `PASS 56 tests`, `717 checks, 0 failed`, and `view canvas aspect/centering/mouse round-trip passed`. (`lua pc/geno/tools/lab_stage_d_check.lua` fails from a checkout root on a path issue that is not yours; ignore it.)
- [ ] **Step 4: What step 1 does NOT depend on.** The spec lists three unverified items (overlay over a frontend scene, script draw hooks on menu scenes, font page loading). Step 1 draws only inside a match, where `gd.kit` already draws over the world, so the first two are not needed here (they gate step 2). The third was read in source: font pages load lazily per role (`KfRole.tex[] = -2` until first draw, `gw_kit.c:1235-1238`), so unused roles cost nothing; Task 15 changes the two hard limits that would break a bigger manifest.

---

### Task 1: Tokens from one source

**Files:**
- Create (workspace repo): `menu/pipeline/atlas_tokens.py`, `menu/pipeline/test_atlas_tokens.py`, `menu/atlas/tokens.json` (generated)
- Create (game repo): `melee/pc/platform/gw_ui_tokens.h` (generated), `melee/pc/tests/atlas_check.h`, `melee/pc/tests/atlas_tokens_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case list near line 19-59 and the die message at line 61)

**Interfaces:**
Consumes: `menu/concepts/reunification-2026-10-06/c-atlas/tokens.css` `:root` custom properties.
Produces: macros `AT_C_<NAME>` (uint32 `0xRRGGBBAAu`), `AT_PX_<NAME>` (int), `AT_MS_<NAME>` (int; the leading `m-` of the CSS name dropped), and `atlas_check.h` with `CHECK`, `CHECK_NEAR`, `CHECK_STR`, `ATLAS_DONE(name)` used by every later test.

- [ ] **Step 1: Write the failing tests.** Create `menu/pipeline/test_atlas_tokens.py`:

```python
"""Tests for atlas_tokens.py: python menu/pipeline/test_atlas_tokens.py"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import atlas_tokens as T  # noqa: E402


class Tokens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok = T.parse(open(T.SRC, encoding="utf-8").read())

    def test_colours(self):
        c = self.tok["colours"]
        self.assertEqual(c["ember"], 0xFF7A3DFF)
        self.assertEqual(c["jade"], 0x4FD6AAFF)
        self.assertEqual(c["plate"], 0x1A1F29FF)
        self.assertEqual(c["scrim"], 0x05070AB8)  # rgba(5,7,10,.72)
        self.assertEqual(c["p4"], 0x42D68BFF)

    def test_sizes(self):
        p = self.tok["px"]
        self.assertEqual([p["t-cap"], p["t-body"], p["t-row"], p["t-label"], p["t-title"], p["t-hero"], p["t-display"]],
                         [12, 14, 16, 20, 28, 44, 64])
        self.assertEqual([p["ch"], p["ch-s"], p["ch-xs"]], [8, 5, 3])
        self.assertEqual([p["s1"], p["s2"], p["s3"], p["s4"], p["s5"]], [4, 8, 12, 16, 24])

    def test_motion(self):
        m = self.tok["ms"]
        self.assertEqual([m["m-focus"], m["m-tab"], m["m-pane"], m["m-modal"], m["m-note"], m["m-turn"]],
                         [80, 120, 100, 140, 160, 12000])

    def test_header_text(self):
        h = T.header_text(self.tok)
        self.assertIn("#define AT_C_EMBER 0xFF7A3DFFu", h)
        self.assertIn("#define AT_PX_T_CAP 12", h)
        self.assertIn("#define AT_MS_FOCUS 80", h)
        self.assertIn("generated by menu/pipeline/atlas_tokens.py", h)


if __name__ == "__main__":
    unittest.main()
```

Create `melee/pc/tests/atlas_check.h`:

```c
/* Tiny check macros shared by the atlas-* native tests (no framework, no game). */
#ifndef ATLAS_CHECK_H
#define ATLAS_CHECK_H
#include <math.h>
#include <stdio.h>
#include <string.h>

static int at_t_fails, at_t_count;
#define CHECK(cond) do { at_t_count++; if (!(cond)) { at_t_fails++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); } } while (0)
#define CHECK_NEAR(a, b) do { double _a = (a), _b = (b); at_t_count++; if (fabs(_a - _b) > 0.01) { at_t_fails++; printf("FAIL %s:%d: %s = %g, want %g\n", __FILE__, __LINE__, #a, _a, _b); } } while (0)
#define CHECK_STR(a, b) do { const char *_a = (a), *_b = (b); at_t_count++; if (strcmp(_a, _b) != 0) { at_t_fails++; printf("FAIL %s:%d: \"%s\", want \"%s\"\n", __FILE__, __LINE__, _a, _b); } } while (0)
#define ATLAS_DONE(name) do { printf("%s: %d checks, %d failed\n", name, at_t_count, at_t_fails); return at_t_fails ? 1 : 0; } while (0)
#endif
```

Create `melee/pc/tests/atlas_tokens_test.c`:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_tokens.h"

int main(void)
{
    CHECK(AT_C_EMBER == 0xFF7A3DFFu);
    CHECK(AT_C_JADE == 0x4FD6AAFFu);
    CHECK(AT_C_GROUND == 0x0D1015FFu);
    CHECK(AT_C_SCRIM == 0x05070AB8u);
    CHECK(AT_PX_T_CAP == 12 && AT_PX_T_DISPLAY == 64);
    CHECK(AT_PX_CH == 8 && AT_PX_CH_S == 5 && AT_PX_CH_XS == 3);
    CHECK(AT_PX_S1 == 4 && AT_PX_S5 == 24);
    CHECK(AT_MS_FOCUS == 80 && AT_MS_MODAL == 140 && AT_MS_TURN == 12000);
    ATLAS_DONE("atlas tokens");
}
```

Register the native test. In `tools/port/native_test.sh`, add before the `*)` line:

```bash
atlas-tokens)
    sources=(pc/tests/atlas_tokens_test.c) ;;
```

and extend the die message on the `*)` line by appending `, atlas-tokens` inside the parentheses.

- [ ] **Step 2: Run them to verify they fail.**

```bash
python menu/pipeline/test_atlas_tokens.py
```

Expected: `ModuleNotFoundError: No module named 'atlas_tokens'`.

```bash
nt atlas-tokens
```

Expected: the test file exists, so the failure comes from the compiler: `fatal error: '../platform/gw_ui_tokens.h' file not found`.

- [ ] **Step 3: Write the minimal implementation.** Create `menu/pipeline/atlas_tokens.py`:

```python
"""Atlas tokens: one source, three consumers.

    python menu/pipeline/atlas_tokens.py [--header PATH]

Reads the :root custom properties of the chosen concept's tokens.css
(menu/concepts/reunification-2026-10-06/c-atlas/tokens.css) and writes
  menu/atlas/tokens.json                  every consumer's data (launcher, tools)
  melee/pc/platform/gw_ui_tokens.h        the C header the host includes (AT_C_*, AT_PX_*, AT_MS_*)
Colours are 0xRRGGBBAA. Nothing here is hand-edited downstream.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # menu/
SRC = os.path.join(ROOT, "concepts", "reunification-2026-10-06", "c-atlas", "tokens.css")
OUT_JSON = os.path.join(ROOT, "atlas", "tokens.json")
DEFAULT_HEADER = os.path.join(os.path.dirname(ROOT), "melee", "pc", "platform", "gw_ui_tokens.h")

VAR = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);")
HEX = re.compile(r"^#([0-9a-fA-F]{6})$")
RGBA = re.compile(r"^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)$")
PX = re.compile(r"^(\d+)px$")
MS = re.compile(r"^(\d+)ms$")


def parse(css_text):
    root = re.search(r":root\s*\{(.*?)\n\}", css_text, re.S).group(1)
    colours, px, ms = {}, {}, {}
    for name, raw in VAR.findall(root):
        raw = raw.strip()
        m = HEX.match(raw)
        if m:
            colours[name] = (int(m.group(1), 16) << 8) | 0xFF
            continue
        m = RGBA.match(raw)
        if m:
            r, g, b = (int(m.group(i)) for i in (1, 2, 3))
            colours[name] = (r << 24) | (g << 16) | (b << 8) | round(float(m.group(4)) * 255)
            continue
        m = PX.match(raw)
        if m:
            px[name] = int(m.group(1))
            continue
        m = MS.match(raw)
        if m:
            ms[name] = int(m.group(1))
    return dict(colours=colours, px=px, ms=ms)


def cname(prefix, name):
    return "AT_%s_%s" % (prefix, name.upper().replace("-", "_"))


def header_text(tok):
    out = ["/* generated by menu/pipeline/atlas_tokens.py from the Atlas tokens.css: do not edit */",
           "#ifndef GW_UI_TOKENS_H", "#define GW_UI_TOKENS_H", ""]
    for name, v in tok["colours"].items():
        out.append("#define %s 0x%08Xu" % (cname("C", name), v))
    out.append("")
    for name, v in tok["px"].items():
        out.append("#define %s %d" % (cname("PX", name), v))
    out.append("")
    for name, v in tok["ms"].items():
        out.append("#define %s %d" % (cname("MS", name[2:] if name.startswith("m-") else name), v))
    out += ["", "#endif", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--header", default=DEFAULT_HEADER)
    a = ap.parse_args(argv)
    tok = parse(open(SRC, encoding="utf-8").read())
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dict(source=os.path.relpath(SRC, ROOT).replace("\\", "/"), **tok), fh, indent=1, sort_keys=True)
        fh.write("\n")
    with open(a.header, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(header_text(tok))
    print("tokens: %d colours, %d sizes, %d timings -> %s, %s"
          % (len(tok["colours"]), len(tok["px"]), len(tok["ms"]), OUT_JSON, a.header))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Generate both outputs. The header goes into the game worktree:

```bash
python menu/pipeline/atlas_tokens.py --header "$GW_MELEE/pc/platform/gw_ui_tokens.h"
```

Expected: `tokens: 30 colours, 15 sizes, 6 timings -> .../menu/atlas/tokens.json, .../gw_ui_tokens.h` (counted on the current `tokens.css`: 30 colour tokens, 7 type sizes + 5 spacing steps + 3 chamfers, 6 motion times; if the concept's file has changed the counts follow it, and the next step must still pass).

- [ ] **Step 4: Run the tests.**

```bash
python menu/pipeline/test_atlas_tokens.py
```

Expected: `Ran 4 tests in 0.0Xs` and `OK`.

```bash
nt atlas-tokens
```

Expected: `native test  atlas-tokens` then `atlas tokens: 8 checks, 0 failed`.

- [ ] **Step 5: Commit.** Game repo (`$GW_MELEE`):

```bash
git -C "$GW_MELEE" add pc/platform/gw_ui_tokens.h pc/tests/atlas_check.h pc/tests/atlas_tokens_test.c
git -C "$GW_MELEE" commit -m "atlas: generated token header and the shared native-test macros

Not built into the exe; checked by the atlas-tokens native test.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UppNBzq7g5LUc45dFioUHp"
```

Workspace repo (`worktrees/ws-atlas1`; the same files `menu/pipeline/atlas_tokens.py`, `test_atlas_tokens.py`, `menu/atlas/tokens.json`, `tools/port/native_test.sh`):

```bash
git add menu/pipeline/atlas_tokens.py menu/pipeline/test_atlas_tokens.py menu/atlas/tokens.json tools/port/native_test.sh
git commit -m "atlas: tokens generator, JSON and the atlas-tokens native test case

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UppNBzq7g5LUc45dFioUHp"
```

---

### Task 2: Roles, text fit, wrap and the four-place layout

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_layout.h`, `melee/pc/platform/gw_ui_layout.c`, `melee/pc/tests/atlas_fake.h`, `melee/pc/tests/atlas_layout_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (add case `atlas-layout`)

**Interfaces:**
Consumes: `atlas_check.h` (Task 1).
Produces (all later tasks rely on these exact names):

```c
typedef struct { float x, y, w, h; } AtRect;
typedef enum { AT_R_CAP12, AT_R_CAP14, AT_R_CAP16, AT_R_CAP20, AT_R_TITLE, AT_R_HERO, AT_R_DISPLAY,
               AT_R_BODY12, AT_R_BODY14, AT_R_ROW16, AT_R_NUM12, AT_R_NUM14, AT_R_NUM16, AT_R_COUNT } AtRole;
typedef struct { const char *name; int size; int face; int caps_only; int tracked; int smaller; } AtRoleInfo;
const AtRoleInfo *at_role(int role);
int at_role_size(int role);
int at_role_by_name(const char *name);
typedef struct AtTextOps { float (*width)(void *user, int role, const char *s); void *user; } AtTextOps;
int at_fit(const AtTextOps *ops, int role, const char *s, float max_w, char *out, int cap);
int at_wrap(const AtTextOps *ops, int role, const char *s, float max_w, int max_lines, char lines[][96], int *clamped);
enum { AT_PRESET_NARROW, AT_PRESET_NORMAL, AT_PRESET_WIDE, AT_PRESET_NONE };
typedef struct { int wide; AtRect canvas, header, trail, chapter, rule, body, primary, explainer, keys, rail; float content_x, content_w; } AtLayout;
void at_layout(float canvas_w, int preset, AtLayout *out);
int at_list_scroll(int focus, int scroll, int visible, int n);
```

- [ ] **Step 1: Write the failing test.** Create `melee/pc/tests/atlas_fake.h` (shared fakes; later tasks extend it):

```c
/* Fakes for the atlas-* native tests: a fixed-width text measure and (added in Task 7) a recording sink. */
#ifndef ATLAS_FAKE_H
#define ATLAS_FAKE_H
#include <string.h>
#include "../platform/gw_ui_layout.h"

/* every UTF-8 character is half the role's size wide */
static float fake_width(void *u, int role, const char *s)
{
    int n = 0;
    (void) u;
    for (; *s; s++) if (((unsigned char) *s & 0xC0) != 0x80) n++;
    return 0.5f * (float) at_role_size(role) * (float) n;
}
static const AtTextOps FAKE = { fake_width, 0 };
#endif
```

Create `melee/pc/tests/atlas_layout_test.c`:

```c
#include "atlas_check.h"
#include "atlas_fake.h"

static void roles(void)
{
    int r;
    for (r = 0; r < AT_R_COUNT; r++) {
        const AtRoleInfo *i = at_role(r);
        CHECK(i->size >= 12);                                   /* the floor at 640x480 */
        if (i->smaller >= 0) {
            CHECK(at_role(i->smaller)->face == i->face);        /* the fit rule never changes face */
            CHECK(at_role(i->smaller)->size < i->size);
        }
    }
    CHECK(at_role_by_name("a_cap12") == AT_R_CAP12);
    CHECK(at_role_by_name("a_num16") == AT_R_NUM16);
    CHECK(at_role_by_name("body") == -1);                       /* legacy names are not Atlas roles */
    CHECK(at_role(AT_R_CAP12)->tracked == 1 && at_role(AT_R_TITLE)->tracked == 0);
    CHECK(at_role(AT_R_HERO)->caps_only == 1 && at_role(AT_R_DISPLAY)->caps_only == 1);
}

static void fit(void)
{
    char out[160];
    int r;
    r = at_fit(&FAKE, AT_R_ROW16, "Hello world", 200.0f, out, sizeof out);
    CHECK(r == AT_R_ROW16); CHECK_STR(out, "Hello world");
    r = at_fit(&FAKE, AT_R_ROW16, "Hello world", 80.0f, out, sizeof out);   /* 88 wide at 16: one role down */
    CHECK(r == AT_R_BODY14); CHECK_STR(out, "Hello world");
    r = at_fit(&FAKE, AT_R_ROW16, "Hello world", 60.0f, out, sizeof out);   /* 66 at 12 is still too wide: truncate */
    CHECK(r == AT_R_BODY12); CHECK_STR(out, "Hello wor\xE2\x80\xA6");
    r = at_fit(&FAKE, AT_R_BODY12, "Hello", 0.0f, out, sizeof out);         /* no limit: unchanged */
    CHECK(r == AT_R_BODY12); CHECK_STR(out, "Hello");
    r = at_fit(&FAKE, AT_R_BODY12, "Wide", 1.0f, out, sizeof out);          /* never below one character */
    CHECK_STR(out, "W\xE2\x80\xA6");
}

static void wrap(void)
{
    char lines[6][96];
    int clamped = 0, n;
    n = at_wrap(&FAKE, AT_R_BODY14, "Your hits set the target Burning for 3 s.", 136.0f, 4, lines, &clamped);
    CHECK(n == 3 && !clamped);
    CHECK_STR(lines[0], "Your hits set the"); CHECK_STR(lines[1], "target Burning for"); CHECK_STR(lines[2], "3 s.");
    n = at_wrap(&FAKE, AT_R_BODY14, "one\ntwo", 136.0f, 4, lines, &clamped);        /* hard breaks */
    CHECK(n == 2); CHECK_STR(lines[0], "one"); CHECK_STR(lines[1], "two");
    n = at_wrap(&FAKE, AT_R_BODY14, "aaa bbb ccc ddd eee fff ggg hhh iii jjj kkk lll mmm nnn ooo ppp", 60.0f, 2, lines, &clamped);
    CHECK(n == 2 && clamped);                                                        /* clamped lines end in an ellipsis */
    CHECK(strstr(lines[1], "\xE2\x80\xA6") != NULL);
    CHECK(fake_width(0, AT_R_BODY14, lines[1]) <= 60.0f);
    n = at_wrap(&FAKE, AT_R_BODY14, "Supercalifragilisticexpialidocious", 60.0f, 3, lines, &clamped);  /* one overlong word */
    CHECK(n == 1 && fake_width(0, AT_R_BODY14, lines[0]) <= 60.0f);
}

static void layout(void)
{
    AtLayout L;
    at_layout(640.0f, AT_PRESET_NORMAL, &L);
    CHECK(!L.wide);
    CHECK_NEAR(L.primary.x, 32); CHECK_NEAR(L.primary.y, 66); CHECK_NEAR(L.primary.w, 368); CHECK_NEAR(L.primary.h, 362);
    CHECK_NEAR(L.explainer.x, 412); CHECK_NEAR(L.explainer.w, 196);
    CHECK_NEAR(L.header.y, 22); CHECK_NEAR(L.header.h, 30); CHECK_NEAR(L.rule.y, 56);
    CHECK_NEAR(L.keys.y, 434); CHECK_NEAR(L.keys.h, 26);
    CHECK_NEAR(L.chapter.x, 608 - 112); CHECK_NEAR(L.chapter.w, 112); CHECK_NEAR(L.rail.w, 0);
    at_layout(640.0f, AT_PRESET_NARROW, &L);                                          /* the bag: 160 explainer */
    CHECK_NEAR(L.explainer.x, 448); CHECK_NEAR(L.explainer.w, 160); CHECK_NEAR(L.primary.w, 404);
    at_layout(640.0f, AT_PRESET_WIDE, &L);
    CHECK_NEAR(L.explainer.w, 256); CHECK_NEAR(L.primary.w, 640 - 64 - 256 - 12);
    at_layout(640.0f, AT_PRESET_NONE, &L);
    CHECK_NEAR(L.explainer.w, 0); CHECK_NEAR(L.primary.w, 576);
    at_layout(500.0f, AT_PRESET_NORMAL, &L);                                          /* never under 640 */
    CHECK_NEAR(L.canvas.w, 640);
    at_layout(853.3333f, AT_PRESET_NORMAL, &L);                                       /* 16:9: the wide arrangement */
    CHECK(L.wide);
    CHECK_NEAR(L.rail.x, 32); CHECK_NEAR(L.rail.w, 104); CHECK_NEAR(L.chapter.w, 0);
    CHECK_NEAR(L.primary.x, 32 + 104 + 12);
    CHECK_NEAR(L.explainer.w, 196 + 75);                                              /* + round((853.33 - 640) * 0.35) */
    CHECK_NEAR(L.explainer.x + L.explainer.w, 853.3333f - 32);
    at_layout(759.0f, AT_PRESET_NORMAL, &L); CHECK(!L.wide);
    at_layout(760.0f, AT_PRESET_NORMAL, &L); CHECK(L.wide);
    at_layout(1706.6667f, AT_PRESET_NORMAL, &L);                                      /* ultrawide: content capped and centred */
    CHECK_NEAR(L.content_w, 1140); CHECK_NEAR(L.content_x, (1706.6667f - 1140) / 2);
    CHECK_NEAR(L.rail.x, L.content_x + 32);
    CHECK_NEAR(L.explainer.x + L.explainer.w, L.content_x + 1140 - 32);
}

static void scroll(void)
{
    CHECK(at_list_scroll(0, 0, 5, 12) == 0);
    CHECK(at_list_scroll(5, 0, 5, 12) == 1);      /* the focus row stays inside the window */
    CHECK(at_list_scroll(11, 0, 5, 12) == 7);
    CHECK(at_list_scroll(2, 7, 5, 12) == 2);
    CHECK(at_list_scroll(3, 9, 5, 4) == 0);       /* never scrolls past the end */
}

int main(void)
{
    roles(); fit(); wrap(); layout(); scroll();
    ATLAS_DONE("atlas layout");
}
```

Register in `tools/port/native_test.sh` (before the `*)` line) and add `, atlas-layout` to the die message:

```bash
atlas-layout)
    sources=(pc/tests/atlas_layout_test.c pc/platform/gw_ui_layout.c) ;;
```

- [ ] **Step 2: Run it to verify it fails.**

```bash
nt atlas-layout
```

Expected: `error: native test source missing: pc/platform/gw_ui_layout.c`.

- [ ] **Step 3: Write the minimal implementation.** Create `melee/pc/platform/gw_ui_layout.h`:

```c
/* gw_ui_layout.h - Atlas: rectangles, the text-role table, text fit and wrap, and the four-place layout.
 * Pure C: no game, no Lua, no renderer. Text is measured through AtTextOps, so the same code runs against
 * the real font (gw_script_ui.inc) and a fixed-width fake (pc/tests/atlas_fake.h). */
#ifndef GW_UI_LAYOUT_H
#define GW_UI_LAYOUT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct { float x, y, w, h; } AtRect;

/* The Atlas text roles. The names are the keys of the font manifest (menu/pipeline/kit.py ATLAS_TYPE_SCALE). */
typedef enum {
    AT_R_CAP12, AT_R_CAP14, AT_R_CAP16, AT_R_CAP20, AT_R_TITLE, AT_R_HERO, AT_R_DISPLAY,
    AT_R_BODY12, AT_R_BODY14, AT_R_ROW16, AT_R_NUM12, AT_R_NUM14, AT_R_NUM16, AT_R_COUNT
} AtRole;

typedef struct {
    const char *name;
    int size;      /* px at 640x480; never under 12 */
    int face;      /* 0 condensed, 1 sans, 2 numerals: the fit rule steps down inside one face */
    int caps_only;
    int tracked;   /* the adapter adds +0.10 em letter-spacing */
    int smaller;   /* the next role down in the same face, or -1 */
} AtRoleInfo;

const AtRoleInfo *at_role(int role);
int at_role_size(int role);
int at_role_by_name(const char *name); /* -1 when it is not an Atlas role */

typedef struct AtTextOps {
    float (*width)(void *user, int role, const char *s); /* px at 1x, tracking included */
    void *user;
} AtTextOps;

/* The fit rule: too wide -> the next smaller role of the same face -> truncate with an ellipsis (UTF-8
 * U+2026). `out` receives the text; returns the role it fits in. max_w <= 0 means no limit. */
int at_fit(const AtTextOps *ops, int role, const char *s, float max_w, char *out, int cap);

/* Word wrap to max_w: breaks at spaces and '\n'. At most max_lines lines of 95 bytes; a clamped block ends its
 * last line with an ellipsis and sets *clamped. Returns the line count. */
int at_wrap(const AtTextOps *ops, int role, const char *s, float max_w, int max_lines, char lines[][96], int *clamped);

enum { AT_PRESET_NARROW, AT_PRESET_NORMAL, AT_PRESET_WIDE, AT_PRESET_NONE };

typedef struct {
    int wide;
    AtRect canvas, header, trail, chapter, rule, body, primary, explainer, keys, rail;
    float content_x, content_w;
} AtLayout;

/* The four places for a canvas width (>= 640) and an explainer preset. Compact below 760, wide from 760;
 * content at most 1140 wide and centred; 32 px margins inside it. */
void at_layout(float canvas_w, int preset, AtLayout *out);

/* The first visible row of a scrolling list that keeps `focus` inside a window of `visible` rows. */
int at_list_scroll(int focus, int scroll, int visible, int n);

#ifdef __cplusplus
}
#endif
#endif
```

Create `melee/pc/platform/gw_ui_layout.c`:

```c
#include "gw_ui_layout.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

static const AtRoleInfo roles[AT_R_COUNT] = {
    { "a_cap12", 12, 0, 0, 1, -1 },        { "a_cap14", 14, 0, 0, 1, AT_R_CAP12 },
    { "a_cap16", 16, 0, 0, 1, AT_R_CAP14 }, { "a_cap20", 20, 0, 0, 1, AT_R_CAP16 },
    { "a_title", 28, 0, 0, 0, AT_R_CAP20 }, { "a_hero", 44, 0, 1, 0, AT_R_TITLE },
    { "a_display", 64, 0, 1, 0, AT_R_HERO },
    { "a_body12", 12, 1, 0, 0, -1 },       { "a_body14", 14, 1, 0, 0, AT_R_BODY12 },
    { "a_row16", 16, 1, 0, 0, AT_R_BODY14 },
    { "a_num12", 12, 2, 0, 0, -1 },        { "a_num14", 14, 2, 0, 0, AT_R_NUM12 },
    { "a_num16", 16, 2, 0, 0, AT_R_NUM14 },
};

const AtRoleInfo *at_role(int role) { return &roles[role >= 0 && role < AT_R_COUNT ? role : AT_R_BODY14]; }
int at_role_size(int role) { return at_role(role)->size; }
int at_role_by_name(const char *name)
{
    int i;
    for (i = 0; name != NULL && i < AT_R_COUNT; i++) if (strcmp(roles[i].name, name) == 0) return i;
    return -1;
}

static int prev_char(const char *s, int n) /* byte length of s[0..n) minus its last UTF-8 character */
{
    n--;
    while (n > 0 && ((unsigned char) s[n] & 0xC0) == 0x80) n--;
    return n;
}

/* Truncate with an ellipsis inside ONE role (the role is not changed). */
static void truncate_in(const AtTextOps *ops, int role, const char *s, float max_w, char *out, int cap)
{
    int n;
    snprintf(out, (size_t) cap, "%s", s);
    n = (int) strlen(out);
    while (n > 1 && ops->width(ops->user, role, out) > max_w) {
        n = prev_char(s, n);
        if (n < 1) n = 1;
        if (n + 4 > cap) n = cap - 4;
        memcpy(out, s, (size_t) n);
        memcpy(out + n, "\xE2\x80\xA6", 4); /* the ellipsis and the terminating NUL */
    }
}

int at_fit(const AtTextOps *ops, int role, const char *s, float max_w, char *out, int cap)
{
    snprintf(out, (size_t) cap, "%s", s);
    if (max_w <= 0.0f) return role;
    while (ops->width(ops->user, role, out) > max_w && at_role(role)->smaller >= 0) role = at_role(role)->smaller;
    truncate_in(ops, role, s, max_w, out, cap);
    return role;
}

static int push_line(char lines[][96], int *n, int max_lines, const char *text, int *clamped)
{
    if (*n >= max_lines) { *clamped = 1; return 0; }
    snprintf(lines[*n], 96, "%s", text);
    (*n)++;
    return 1;
}

int at_wrap(const AtTextOps *ops, int role, const char *s, float max_w, int max_lines, char lines[][96], int *clamped)
{
    char cur[96] = "", word[96], cand[200], fit[96];
    int n = 0, cl = 0;
    const char *p = s;
    while (*p != '\0' && !cl) {
        int k = 0;
        if (*p == '\n') {
            if (!push_line(lines, &n, max_lines, cur, &cl)) break;
            cur[0] = '\0';
            p++;
            continue;
        }
        if (*p == ' ') { p++; continue; }
        while (p[k] != '\0' && p[k] != ' ' && p[k] != '\n' && k < 95) { word[k] = p[k]; k++; }
        word[k] = '\0';
        p += k;
        snprintf(cand, sizeof cand, "%s%s%s", cur, cur[0] ? " " : "", word);
        if (ops->width(ops->user, role, cand) <= max_w || max_w <= 0.0f) {
            snprintf(cur, sizeof cur, "%s", cand);
        } else {
            if (cur[0] != '\0' && !push_line(lines, &n, max_lines, cur, &cl)) break;
            truncate_in(ops, role, word, max_w, fit, sizeof fit);   /* an overlong single word is cut, in the same role */
            snprintf(cur, sizeof cur, "%s", fit);
        }
    }
    if (!cl && (cur[0] != '\0' || n == 0)) push_line(lines, &n, max_lines, cur, &cl);
    if (cl && n > 0) {                                          /* the last allowed line says it was cut */
        char tmp[96];
        snprintf(tmp, sizeof tmp, "%.90s\xE2\x80\xA6", lines[n - 1]);
        truncate_in(ops, role, tmp, max_w, lines[n - 1], 96);
    }
    if (clamped) *clamped = cl;
    return n;
}

void at_layout(float canvas_w, int preset, AtLayout *o)
{
    static const float base[3] = { 160.0f, 196.0f, 256.0f };
    float w = canvas_w < 640.0f ? 640.0f : canvas_w, cw, cx, L, R, px, ew = 0.0f;
    memset(o, 0, sizeof *o);
    o->wide = w >= 760.0f;
    cw = w < 1140.0f ? w : 1140.0f;
    cx = (w - cw) * 0.5f;
    L = cx + 32.0f;
    R = cx + cw - 32.0f;
    o->canvas = (AtRect){ 0.0f, 0.0f, w, 480.0f };
    o->content_x = cx;
    o->content_w = cw;
    o->header = (AtRect){ L, 22.0f, R - L, 30.0f };
    o->trail = (AtRect){ L, 22.0f, R - L - (o->wide ? 0.0f : 124.0f), 30.0f };
    o->rule = (AtRect){ L, 56.0f, R - L, 1.0f };
    o->body = (AtRect){ L, 66.0f, R - L, 362.0f };
    o->keys = (AtRect){ L, 434.0f, R - L, 26.0f };
    if (o->wide) o->rail = (AtRect){ L, 66.0f, 104.0f, 362.0f };
    else o->chapter = (AtRect){ R - 112.0f, 26.0f, 112.0f, 20.0f };
    px = L + (o->wide ? 116.0f : 0.0f);
    if (preset >= AT_PRESET_NARROW && preset <= AT_PRESET_WIDE) {
        ew = base[preset];
        if (o->wide) ew += (float) floor((cw - 640.0f) * 0.35f + 0.5f);
    }
    o->explainer = (AtRect){ ew > 0.0f ? R - ew : R, 66.0f, ew, 362.0f };
    o->primary = (AtRect){ px, 66.0f, (ew > 0.0f ? R - ew - 12.0f : R) - px, 362.0f };
}

int at_list_scroll(int focus, int scroll, int visible, int n)
{
    if (visible < 1) visible = 1;
    if (focus < scroll) scroll = focus;
    if (focus >= scroll + visible) scroll = focus - visible + 1;
    if (scroll > n - visible) scroll = n - visible;
    return scroll < 0 ? 0 : scroll;
}
```

- [ ] **Step 4: Run the tests.**

```bash
nt atlas-layout
```

Expected: `native test  atlas-layout` then `atlas layout: 99 checks, 0 failed`. If a CHECK fails, fix the code, not the expectation, unless the expectation contradicts the spec numbers in Global Constraints.

- [ ] **Step 5: Commit.** Game repo: `git -C "$GW_MELEE" add pc/platform/gw_ui_layout.h pc/platform/gw_ui_layout.c pc/tests/atlas_fake.h pc/tests/atlas_layout_test.c`, message `atlas: role table, text fit and wrap, four-place layout (compact and wide)` with the two trailer lines used in Task 1. Workspace repo: `git add tools/port/native_test.sh`, message `atlas: atlas-layout native test case` with the trailers.

### Task 3: Focus movement and held-direction repeat

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_focus.h`, `melee/pc/platform/gw_ui_focus.c`, `melee/pc/tests/atlas_focus_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-focus`)

**Interfaces:**
Consumes: `atlas_check.h`.
Produces:

```c
typedef struct { int col0, row0, cols, n; const unsigned char *exists; } AtFocusBlock;
typedef struct { int block, index; } AtFocusPos;
enum { AT_DIR_LEFT = 1, AT_DIR_RIGHT = 2, AT_DIR_UP = 3, AT_DIR_DOWN = 4 };
AtFocusPos at_focus_first(const AtFocusBlock *b, int nb);                       /* {-1,-1} when nothing can be focused */
AtFocusPos at_focus_move(const AtFocusBlock *b, int nb, AtFocusPos cur, int dir, int wrap);
typedef struct { int dir; double down_ms, last_ms; } AtRepeat;
int at_repeat_step(AtRepeat *r, int held_dir, double now_ms);                   /* the direction to fire now, or 0 */
```

The rule is the legacy grid's, copied exactly so the proven behaviour carries over: the nearest focusable cell strictly in the pressed direction, scored `distance along the direction + 2 x sideways offset`; with nothing that way, wrap to the far side keeping the row (left, right) or column (up, down), scored `position + 4 x sideways offset` (source: `melee/pc/scripts/examples/demos/grid-inventory/scripts/grid.lua:258-290`). A cell sits at `x = col0 + index % cols`, `y = row0 + index / cols`. `exists[i] == 0` is a hole: skipped and never focusable. Empty and locked cells EXIST (they are focusable; the legacy view says so too).

- [ ] **Step 1: Write the failing test.** Create `melee/pc/tests/atlas_focus_test.c`. It ports the legacy scenario in `melee/pc/tests/grid_inventory.lua:26-62` (blocks A, B, K, with a hole), zero-based:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_focus.h"

static AtFocusPos P(int b, int i) { AtFocusPos p; p.block = b; p.index = i; return p; }
static int is(AtFocusPos p, int b, int i) { return p.block == b && p.index == i; }

static void legacy_scenario(void)
{
    static const unsigned char a_exists[6] = { 1, 1, 1, 1, 0, 1 };      /* a5 is a hole */
    AtFocusBlock bl[3] = {
        { 0, 0, 3, 6, a_exists },   /* A: 3 columns, rows 0..1 */
        { 3, 0, 2, 4, NULL },       /* B: right of A, 2 columns; b3 is an EMPTY cell and focusable */
        { 0, 2, 3, 2, NULL },       /* K: row 2, two cells of three columns */
    };
    AtFocusPos f = at_focus_first(bl, 3);
    CHECK(is(f, 0, 0));
    f = at_focus_move(bl, 3, f, AT_DIR_RIGHT, 1); CHECK(is(f, 0, 1));
    f = at_focus_move(bl, 3, f, AT_DIR_RIGHT, 1); f = at_focus_move(bl, 3, f, AT_DIR_RIGHT, 1);
    CHECK(is(f, 1, 0));                                                 /* right crosses into B, same row */
    f = at_focus_move(bl, 3, f, AT_DIR_RIGHT, 1); CHECK(is(f, 1, 1));
    f = at_focus_move(bl, 3, f, AT_DIR_RIGHT, 1); CHECK(is(f, 0, 0));   /* the end of the row wraps to the first cell, same row */
    f = at_focus_move(bl, 3, f, AT_DIR_RIGHT, 1); f = at_focus_move(bl, 3, f, AT_DIR_RIGHT, 1);
    CHECK(is(f, 0, 2));
    f = at_focus_move(bl, 3, f, AT_DIR_DOWN, 1); CHECK(is(f, 0, 5));    /* down inside a block */
    f = at_focus_move(bl, 3, f, AT_DIR_DOWN, 1); CHECK(is(f, 2, 1));    /* down leaves the block, nearest column (k2 is under a3) */
    f = at_focus_move(bl, 3, f, AT_DIR_LEFT, 1); CHECK(is(f, 2, 0));
    f = at_focus_move(bl, 3, f, AT_DIR_LEFT, 1); CHECK(is(f, 2, 1));    /* wraps to the last existing cell of the row */
    f = at_focus_move(bl, 3, f, AT_DIR_DOWN, 1); CHECK(is(f, 0, 1));    /* bottom wraps to the top, same column */
    f = at_focus_move(bl, 3, f, AT_DIR_UP, 1);   CHECK(is(f, 2, 1));    /* top wraps to the bottom, same column */
    f = at_focus_move(bl, 3, P(0, 3), AT_DIR_RIGHT, 1); CHECK(is(f, 0, 5));   /* right skips the hole at a5 */
    f = at_focus_move(bl, 3, f, AT_DIR_LEFT, 1);        CHECK(is(f, 0, 3));   /* and left skips it back */
    f = at_focus_move(bl, 3, P(0, 5), AT_DIR_UP, 1);    CHECK(is(f, 0, 2));
    f = at_focus_move(bl, 3, P(0, 3), AT_DIR_DOWN, 1);  CHECK(is(f, 2, 0));   /* down from the last row crosses to K */
    f = at_focus_move(bl, 3, P(1, 2), AT_DIR_LEFT, 1);  CHECK(f.block >= 0);  /* the empty cell b3 holds focus and moves */
}

static void edges(void)
{
    AtFocusBlock one[1] = { { 0, 0, 3, 3, NULL } };
    AtFocusBlock solo[1] = { { 0, 0, 1, 1, NULL } };
    AtFocusBlock none[1] = { { 0, 0, 2, 0, NULL } };
    AtFocusPos f = P(0, 0);
    f = at_focus_move(one, 1, f, AT_DIR_LEFT, 0); CHECK(is(f, 0, 0));           /* wrap = 0 stops at the edge */
    f = at_focus_move(one, 1, P(0, 2), AT_DIR_RIGHT, 0); CHECK(is(f, 0, 2));
    f = at_focus_move(solo, 1, P(0, 0), AT_DIR_RIGHT, 1); CHECK(is(f, 0, 0));   /* a single cell never loops onto itself */
    f = at_focus_move(solo, 1, P(0, 0), AT_DIR_DOWN, 1);  CHECK(is(f, 0, 0));
    f = at_focus_first(none, 1); CHECK(f.block == -1 && f.index == -1);         /* an empty block has no focus */
    f = at_focus_move(one, 1, P(-1, -1), AT_DIR_DOWN, 1); CHECK(is(f, 0, 0));   /* an invalid position falls to the first cell */
    f = at_focus_move(one, 1, P(0, 9), AT_DIR_DOWN, 1);   CHECK(is(f, 0, 0));
}

static void bag_shape(void)
{
    /* the Envoy bag: equipped 6 / bag 4 / keystones 3, one block per row, all from column 0 */
    AtFocusBlock bl[3] = { { 0, 0, 6, 6, NULL }, { 0, 1, 4, 4, NULL }, { 0, 2, 6, 3, NULL } };
    AtFocusPos f;
    f = at_focus_move(bl, 3, P(0, 5), AT_DIR_DOWN, 1);  CHECK(is(f, 1, 3));     /* slot 6 is over bag cell 4, the nearest */
    f = at_focus_move(bl, 3, P(1, 3), AT_DIR_RIGHT, 1);
    /* inherited legacy behaviour, pinned on purpose: with nothing further right in its own row the focus goes to the
       nearest cell to the right in ANOTHER row (equipped slot 5) rather than wrapping within the row */
    CHECK(is(f, 0, 4));
    f = at_focus_move(bl, 3, P(2, 2), AT_DIR_DOWN, 1);  CHECK(is(f, 0, 2));     /* bottom wraps to the top, same column */
}

static void repeat(void)
{
    AtRepeat r = { 0, 0, 0 };
    CHECK(at_repeat_step(&r, AT_DIR_LEFT, 0.0) == AT_DIR_LEFT);                 /* the first press fires at once */
    CHECK(at_repeat_step(&r, AT_DIR_LEFT, 100.0) == 0);
    CHECK(at_repeat_step(&r, AT_DIR_LEFT, 299.0) == 0);
    CHECK(at_repeat_step(&r, AT_DIR_LEFT, 300.0) == AT_DIR_LEFT);               /* 300 ms delay, then every 80 ms */
    CHECK(at_repeat_step(&r, AT_DIR_LEFT, 379.0) == 0);
    CHECK(at_repeat_step(&r, AT_DIR_LEFT, 380.0) == AT_DIR_LEFT);
    CHECK(at_repeat_step(&r, 0, 400.0) == 0);                                   /* release resets */
    CHECK(at_repeat_step(&r, AT_DIR_RIGHT, 500.0) == AT_DIR_RIGHT);
    CHECK(at_repeat_step(&r, AT_DIR_UP, 510.0) == AT_DIR_UP);                   /* a new direction fires at once */
}

int main(void)
{
    legacy_scenario(); edges(); bag_shape(); repeat();
    ATLAS_DONE("atlas focus");
}
```

Register in `native_test.sh`: `atlas-focus) sources=(pc/tests/atlas_focus_test.c pc/platform/gw_ui_focus.c) ;;` and add `, atlas-focus` to the die message.

- [ ] **Step 2: Run it to verify it fails.**

```bash
nt atlas-focus
```

Expected: `error: native test source missing: pc/platform/gw_ui_focus.c`.

- [ ] **Step 3: Write the minimal implementation.** Create `melee/pc/platform/gw_ui_focus.h`:

```c
/* gw_ui_focus.h - Atlas focus movement on blocks of cells, and held-direction repeat. Pure C. */
#ifndef GW_UI_FOCUS_H
#define GW_UI_FOCUS_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct { int col0, row0, cols, n; const unsigned char *exists; } AtFocusBlock; /* exists NULL = every cell exists */
typedef struct { int block, index; } AtFocusPos;
enum { AT_DIR_LEFT = 1, AT_DIR_RIGHT = 2, AT_DIR_UP = 3, AT_DIR_DOWN = 4 };

AtFocusPos at_focus_first(const AtFocusBlock *b, int nb);
AtFocusPos at_focus_move(const AtFocusBlock *b, int nb, AtFocusPos cur, int dir, int wrap);

typedef struct { int dir; double down_ms, last_ms; } AtRepeat;
int at_repeat_step(AtRepeat *r, int held_dir, double now_ms);

#ifdef __cplusplus
}
#endif
#endif
```

Create `melee/pc/platform/gw_ui_focus.c`:

```c
#include "gw_ui_focus.h"

#include <math.h>
#include <stddef.h>

static int cx_of(const AtFocusBlock *b, int i) { return b->col0 + i % b->cols; }
static int cy_of(const AtFocusBlock *b, int i) { return b->row0 + i / b->cols; }
static int present(const AtFocusBlock *b, int i) { return b->exists == NULL || b->exists[i]; }

AtFocusPos at_focus_first(const AtFocusBlock *bl, int nb)
{
    int b, i;
    AtFocusPos none = { -1, -1 };
    for (b = 0; b < nb; b++)
        for (i = 0; i < bl[b].n; i++)
            if (present(&bl[b], i)) { AtFocusPos p = { b, i }; return p; }
    return none;
}

AtFocusPos at_focus_move(const AtFocusBlock *bl, int nb, AtFocusPos cur, int dir, int wrap)
{
    int fx, fy, b, i, have = 0, pass;
    double best = 0.0;
    AtFocusPos out = cur;
    if (cur.block < 0 || cur.block >= nb || cur.index < 0 || cur.index >= bl[cur.block].n || !present(&bl[cur.block], cur.index))
        return at_focus_first(bl, nb);
    fx = cx_of(&bl[cur.block], cur.index);
    fy = cy_of(&bl[cur.block], cur.index);
    for (pass = 0; pass < 2 && !have; pass++) {
        if (pass == 1 && !wrap) break;
        for (b = 0; b < nb; b++) {
            for (i = 0; i < bl[b].n; i++) {
                int dx, dy, horizontal = (dir == AT_DIR_LEFT || dir == AT_DIR_RIGHT);
                double prim, perp, s;
                if (!present(&bl[b], i) || (b == cur.block && i == cur.index)) continue;
                dx = cx_of(&bl[b], i) - fx;
                dy = cy_of(&bl[b], i) - fy;
                perp = fabs((double) (horizontal ? dy : dx));
                if (pass == 0) {
                    prim = dir == AT_DIR_RIGHT ? dx : dir == AT_DIR_LEFT ? -dx : dir == AT_DIR_DOWN ? dy : -dy;
                    if (prim <= 0.01) continue;
                    s = prim + 2.0 * perp;
                } else {
                    int ax = cx_of(&bl[b], i), ay = cy_of(&bl[b], i);
                    prim = dir == AT_DIR_RIGHT ? ax : dir == AT_DIR_LEFT ? -ax : dir == AT_DIR_DOWN ? ay : -ay;
                    s = prim + 4.0 * perp;
                }
                if (!have || s < best) { best = s; out.block = b; out.index = i; have = 1; }
            }
        }
    }
    return out;
}

int at_repeat_step(AtRepeat *r, int held, double now)
{
    if (held == 0) { r->dir = 0; return 0; }
    if (held != r->dir) { r->dir = held; r->down_ms = now; r->last_ms = now; return held; }
    if (now - r->down_ms >= 300.0 && now - r->last_ms >= 80.0) { r->last_ms = now; return held; }
    return 0;
}
```

- [ ] **Step 4: Run the tests.**

```bash
nt atlas-focus
```

Expected: `atlas focus: 36 checks, 0 failed`. If the `bag_shape` right-move check fails, do not "fix" it by changing the rule; read the scoring above (strict direction first: from bag cell 4 at x=3,y=1 the candidates with x>3 are equipped cells 4 and 5 at y=0 and keystone cells none; nearest is equipped 4) and fix the test arithmetic.

- [ ] **Step 5: Commit.** Game repo: add the three files, message `atlas: focus movement (the legacy grid rule, ported) and held-direction repeat`. Workspace repo: `tools/port/native_test.sh`, message `atlas: atlas-focus native test case`. (Trailers as in Task 1.)

---

### Task 4: Input events from pad, keyboard and mouse

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_input.h`, `melee/pc/platform/gw_ui_input.c`, `melee/pc/tests/atlas_input_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-input`)

**Interfaces:**
Consumes: `AtFocusPos`, `AtRepeat`, `at_repeat_step`, `AT_DIR_*` (Task 3); `AtRect` (Task 2).
Produces:

```c
enum { AT_EV_NONE, AT_EV_MOVE, AT_EV_FOCUS, AT_EV_ACCEPT, AT_EV_BACK, AT_EV_ALT, AT_EV_PAGE, AT_EV_SCROLL, AT_EV_START };
typedef struct { int type, a, b; } AtEvent;      /* MOVE a=dir; FOCUS a=block b=index; ALT a='X'|'Y'|'Z'; PAGE a=-1|+1; SCROLL a=-1|+1 */
enum { AT_HIT_CELL = 1, AT_HIT_KEY = 2, AT_HIT_DIALOG = 3 };
typedef struct { AtRect r; int kind, a, b; } AtHit;  /* CELL a=block b=index; KEY and DIALOG a=button char 'A'.. ('S' = START) */
#define AT_MAX_HITS 96
typedef struct { AtHit h[AT_MAX_HITS]; int n; } AtHits;
enum { AT_PAD_LEFT = 0x0001, AT_PAD_RIGHT = 0x0002, AT_PAD_DOWN = 0x0004, AT_PAD_UP = 0x0008, AT_PAD_Z = 0x0010, AT_PAD_R = 0x0020,
       AT_PAD_L = 0x0040, AT_PAD_A = 0x0100, AT_PAD_B = 0x0200, AT_PAD_X = 0x0400, AT_PAD_Y = 0x0800, AT_PAD_START = 0x1000 };
enum { AT_KEY_UP = 1, AT_KEY_DOWN = 2, AT_KEY_LEFT = 4, AT_KEY_RIGHT = 8, AT_KEY_ENTER = 16, AT_KEY_ESC = 32, AT_KEY_TAB = 64, AT_KEY_SHIFT = 128 };
typedef struct { unsigned prev; AtRepeat rep; } AtPad;
typedef struct { unsigned prev; AtRepeat rep; } AtKeys;
typedef struct { int valid; float x, y; int buttons; } AtMouse;
int at_pad_events(AtPad *p, unsigned buttons, int sx, int sy, double now_ms, AtEvent *out, int cap);
int at_key_events(AtKeys *k, unsigned mask, double now_ms, AtEvent *out, int cap);
int at_mouse_events(AtMouse *m, float x, float y, int buttons, int wheel, const AtHits *hits, AtEvent *out, int cap);
int at_hit_test(const AtHits *hits, float x, float y);
```

The pad bit layout is the game's (the same bits `gd.input_mask` accepts: D-pad 0x000F, START 0x1000, `gw_script.c:1893-1900`, and `envoy/scripts/menu_input.lua:28`). The stick threshold is 60 on the -127..127 scale (`menu_input.lua:36-37`); up and down win over left and right.

- [ ] **Step 1: Write the failing test.** Create `melee/pc/tests/atlas_input_test.c`:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_input.h"

static AtEvent ev[8];

static void pad(void)
{
    AtPad p; int n;
    memset(&p, 0, sizeof p);
    n = at_pad_events(&p, AT_PAD_A, 0, 0, 0.0, ev, 8);
    CHECK(n == 1 && ev[0].type == AT_EV_ACCEPT);
    n = at_pad_events(&p, AT_PAD_A, 0, 0, 16.0, ev, 8); CHECK(n == 0);              /* held: no repeat for buttons */
    n = at_pad_events(&p, 0, 0, 0, 32.0, ev, 8); CHECK(n == 0);
    n = at_pad_events(&p, AT_PAD_B | AT_PAD_X, 0, 0, 48.0, ev, 8);
    CHECK(n == 2 && ev[0].type == AT_EV_BACK && ev[1].type == AT_EV_ALT && ev[1].a == 'X');
    n = at_pad_events(&p, 0, 0, 0, 64.0, ev, 8);
    n = at_pad_events(&p, AT_PAD_L, 0, 0, 80.0, ev, 8); CHECK(n == 1 && ev[0].type == AT_EV_PAGE && ev[0].a == -1);
    n = at_pad_events(&p, AT_PAD_R | AT_PAD_L, 0, 0, 96.0, ev, 8); CHECK(n == 1 && ev[0].type == AT_EV_PAGE && ev[0].a == 1);
    n = at_pad_events(&p, 0, 0, 0, 112.0, ev, 8);
    n = at_pad_events(&p, AT_PAD_START, 0, 0, 128.0, ev, 8); CHECK(n == 1 && ev[0].type == AT_EV_START);
    n = at_pad_events(&p, 0, 0, 0, 144.0, ev, 8);
    n = at_pad_events(&p, 0, 0, 100, 160.0, ev, 8);                                /* stick up past 60 */
    CHECK(n == 1 && ev[0].type == AT_EV_MOVE && ev[0].a == AT_DIR_UP);
    n = at_pad_events(&p, 0, 0, 100, 200.0, ev, 8); CHECK(n == 0);
    n = at_pad_events(&p, 0, 0, 100, 460.0, ev, 8); CHECK(n == 1 && ev[0].a == AT_DIR_UP);   /* repeat after 300 ms */
    n = at_pad_events(&p, 0, 59, 0, 480.0, ev, 8); CHECK(n == 0);                  /* under the threshold: nothing */
    n = at_pad_events(&p, AT_PAD_LEFT | AT_PAD_UP, 0, 0, 500.0, ev, 8);
    CHECK(n == 1 && ev[0].a == AT_DIR_UP);                                         /* up beats left */
    n = at_pad_events(&p, AT_PAD_RIGHT, 0, 0, 520.0, ev, 8); CHECK(n == 1 && ev[0].a == AT_DIR_RIGHT);
    n = at_pad_events(&p, 0, -80, 0, 540.0, ev, 8); CHECK(n == 1 && ev[0].a == AT_DIR_LEFT);
}

static void keys(void)
{
    AtKeys k; int n;
    memset(&k, 0, sizeof k);
    n = at_key_events(&k, AT_KEY_ENTER, 0.0, ev, 8); CHECK(n == 1 && ev[0].type == AT_EV_ACCEPT);
    n = at_key_events(&k, AT_KEY_ENTER, 10.0, ev, 8); CHECK(n == 0);
    n = at_key_events(&k, AT_KEY_ESC, 20.0, ev, 8); CHECK(n == 1 && ev[0].type == AT_EV_BACK);
    n = at_key_events(&k, 0, 30.0, ev, 8);
    n = at_key_events(&k, AT_KEY_TAB, 40.0, ev, 8); CHECK(n == 1 && ev[0].type == AT_EV_PAGE && ev[0].a == 1);
    n = at_key_events(&k, 0, 50.0, ev, 8);
    n = at_key_events(&k, AT_KEY_TAB | AT_KEY_SHIFT, 60.0, ev, 8); CHECK(n == 1 && ev[0].type == AT_EV_PAGE && ev[0].a == -1);
    n = at_key_events(&k, 0, 70.0, ev, 8);
    n = at_key_events(&k, AT_KEY_DOWN, 80.0, ev, 8); CHECK(n == 1 && ev[0].type == AT_EV_MOVE && ev[0].a == AT_DIR_DOWN);
    n = at_key_events(&k, AT_KEY_DOWN, 400.0, ev, 8); CHECK(n == 1 && ev[0].a == AT_DIR_DOWN);   /* repeats like the pad */
}

static AtHits hits_fixture(void)
{
    AtHits h; memset(&h, 0, sizeof h);
    h.h[0].r = (AtRect){ 100, 100, 50, 50 }; h.h[0].kind = AT_HIT_CELL; h.h[0].a = 0; h.h[0].b = 0;
    h.h[1].r = (AtRect){ 200, 100, 50, 50 }; h.h[1].kind = AT_HIT_CELL; h.h[1].a = 0; h.h[1].b = 1;
    h.h[2].r = (AtRect){ 40, 440, 90, 20 };  h.h[2].kind = AT_HIT_KEY;  h.h[2].a = 'X';
    h.h[3].r = (AtRect){ 700, 440, 90, 20 }; h.h[3].kind = AT_HIT_KEY;  h.h[3].a = 'B';   /* a wide-window position */
    h.n = 4;
    return h;
}

static void mouse(void)
{
    AtHits h = hits_fixture();
    AtMouse m; int n;
    memset(&m, 0, sizeof m);
    n = at_mouse_events(&m, 120, 120, 0, 0, &h, ev, 8); CHECK(n == 0);              /* the first sample never focuses */
    n = at_mouse_events(&m, 120, 120, 0, 0, &h, ev, 8); CHECK(n == 0);              /* a pointer resting still does nothing */
    n = at_mouse_events(&m, 220, 120, 0, 0, &h, ev, 8);
    CHECK(n == 1 && ev[0].type == AT_EV_FOCUS && ev[0].a == 0 && ev[0].b == 1);     /* moving onto a cell focuses it */
    n = at_mouse_events(&m, 221, 120, 0, 0, &h, ev, 8); CHECK(n == 1 && ev[0].b == 1);
    n = at_mouse_events(&m, 221, 120, 1, 0, &h, ev, 8);
    CHECK(n == 2 && ev[0].type == AT_EV_FOCUS && ev[1].type == AT_EV_ACCEPT);       /* left click: focus then accept */
    n = at_mouse_events(&m, 221, 120, 1, 0, &h, ev, 8); CHECK(n == 0);              /* held: once */
    n = at_mouse_events(&m, 221, 120, 3, 0, &h, ev, 8); CHECK(n == 1 && ev[0].type == AT_EV_BACK);   /* right button down: back */
    n = at_mouse_events(&m, 221, 300, 0, 0, &h, ev, 8); CHECK(n == 0);              /* moving over nothing: no event */
    n = at_mouse_events(&m, 60, 450, 1, 0, &h, ev, 8);
    CHECK(n == 1 && ev[0].type == AT_EV_ALT && ev[0].a == 'X');                     /* a key hint is a button */
    n = at_mouse_events(&m, 60, 450, 0, 0, &h, ev, 8);
    n = at_mouse_events(&m, 740, 450, 1, 0, &h, ev, 8);
    CHECK(n == 1 && ev[0].type == AT_EV_BACK);                                      /* hit rectangles work beyond x = 640 */
    n = at_mouse_events(&m, 740, 450, 0, 0, &h, ev, 8);
    n = at_mouse_events(&m, 740, 450, 0, 3, &h, ev, 8); CHECK(n == 1 && ev[0].type == AT_EV_SCROLL && ev[0].a == -1);
    n = at_mouse_events(&m, 740, 450, 0, -2, &h, ev, 8); CHECK(n == 1 && ev[0].a == 1);
    n = at_mouse_events(&m, -1000, -1000, 1, 0, &h, ev, 8); CHECK(n == 0);         /* off the picture: nothing, ever */
    n = at_mouse_events(&m, -1000, -1000, 0, 5, &h, ev, 8); CHECK(n == 0);
    n = at_mouse_events(&m, 120, 120, 1, 0, &h, ev, 8);                              /* re-entering with the button held is not a click */
    CHECK(n == 0);
    CHECK(at_hit_test(&h, 120, 120) == 0 && at_hit_test(&h, 5, 5) == -1);
}

int main(void)
{
    pad(); keys(); mouse();
    ATLAS_DONE("atlas input");
}
```

Register: `atlas-input) sources=(pc/tests/atlas_input_test.c pc/platform/gw_ui_input.c pc/platform/gw_ui_focus.c) ;;` and add `, atlas-input` to the die message.

- [ ] **Step 2: Run it to verify it fails.**

```bash
nt atlas-input
```

Expected: `error: native test source missing: pc/platform/gw_ui_input.c`.

- [ ] **Step 3: Write the minimal implementation.** Create `melee/pc/platform/gw_ui_input.h`:

```c
/* gw_ui_input.h - Atlas input: pad, keyboard and mouse become one event type; hit rectangles. Pure C. */
#ifndef GW_UI_INPUT_H
#define GW_UI_INPUT_H
#include "gw_ui_focus.h"
#include "gw_ui_layout.h"
#ifdef __cplusplus
extern "C" {
#endif

enum { AT_EV_NONE, AT_EV_MOVE, AT_EV_FOCUS, AT_EV_ACCEPT, AT_EV_BACK, AT_EV_ALT, AT_EV_PAGE, AT_EV_SCROLL, AT_EV_START };
typedef struct { int type, a, b; } AtEvent;   /* MOVE a=dir; FOCUS a=block b=index; ALT a='X'|'Y'|'Z'; PAGE a=-1|+1; SCROLL a=-1|+1 */

enum { AT_HIT_CELL = 1, AT_HIT_KEY = 2, AT_HIT_DIALOG = 3 };
typedef struct { AtRect r; int kind, a, b; } AtHit;   /* CELL a=block b=index; KEY and DIALOG a=button char ('A'.., 'S' = START) */
#define AT_MAX_HITS 96
typedef struct { AtHit h[AT_MAX_HITS]; int n; } AtHits;

enum { AT_PAD_LEFT = 0x0001, AT_PAD_RIGHT = 0x0002, AT_PAD_DOWN = 0x0004, AT_PAD_UP = 0x0008, AT_PAD_Z = 0x0010, AT_PAD_R = 0x0020,
       AT_PAD_L = 0x0040, AT_PAD_A = 0x0100, AT_PAD_B = 0x0200, AT_PAD_X = 0x0400, AT_PAD_Y = 0x0800, AT_PAD_START = 0x1000 };
enum { AT_KEY_UP = 1, AT_KEY_DOWN = 2, AT_KEY_LEFT = 4, AT_KEY_RIGHT = 8, AT_KEY_ENTER = 16, AT_KEY_ESC = 32, AT_KEY_TAB = 64, AT_KEY_SHIFT = 128 };

typedef struct { unsigned prev; AtRepeat rep; } AtPad;
typedef struct { unsigned prev; AtRepeat rep; } AtKeys;
typedef struct { int valid; float x, y; int buttons; } AtMouse;

/* Each returns how many events it wrote to out (at most cap). */
int at_pad_events(AtPad *p, unsigned buttons, int sx, int sy, double now_ms, AtEvent *out, int cap);
int at_key_events(AtKeys *k, unsigned mask, double now_ms, AtEvent *out, int cap);
int at_mouse_events(AtMouse *m, float x, float y, int buttons, int wheel, const AtHits *hits, AtEvent *out, int cap);
int at_hit_test(const AtHits *hits, float x, float y);   /* the topmost (latest) hit rectangle under the point, or -1 */

#ifdef __cplusplus
}
#endif
#endif
```

Create `melee/pc/platform/gw_ui_input.c`:

```c
#include "gw_ui_input.h"

#include <stddef.h>

#define EMIT(T, A, B) do { if (n < cap) { out[n].type = (T); out[n].a = (A); out[n].b = (B); n++; } } while (0)

static int dir_from(unsigned held_up, unsigned held_down, unsigned held_left, unsigned held_right)
{
    if (held_up) return AT_DIR_UP;
    if (held_down) return AT_DIR_DOWN;
    if (held_left) return AT_DIR_LEFT;
    if (held_right) return AT_DIR_RIGHT;
    return 0;
}

int at_pad_events(AtPad *p, unsigned b, int sx, int sy, double now, AtEvent *out, int cap)
{
    unsigned edge = b & ~p->prev;
    int n = 0, d;
    if (edge & AT_PAD_A) EMIT(AT_EV_ACCEPT, 0, 0);
    if (edge & AT_PAD_B) EMIT(AT_EV_BACK, 0, 0);
    if (edge & AT_PAD_X) EMIT(AT_EV_ALT, 'X', 0);
    if (edge & AT_PAD_Y) EMIT(AT_EV_ALT, 'Y', 0);
    if (edge & AT_PAD_Z) EMIT(AT_EV_ALT, 'Z', 0);
    if (edge & AT_PAD_L) EMIT(AT_EV_PAGE, -1, 0);
    else if (edge & AT_PAD_R) EMIT(AT_EV_PAGE, 1, 0);
    if (edge & AT_PAD_START) EMIT(AT_EV_START, 0, 0);
    d = dir_from((b & AT_PAD_UP) || sy > 60, (b & AT_PAD_DOWN) || sy < -60, (b & AT_PAD_LEFT) || sx < -60, (b & AT_PAD_RIGHT) || sx > 60);
    d = at_repeat_step(&p->rep, d, now);
    if (d) EMIT(AT_EV_MOVE, d, 0);
    p->prev = b;
    return n;
}

int at_key_events(AtKeys *k, unsigned m, double now, AtEvent *out, int cap)
{
    unsigned edge = m & ~k->prev;
    int n = 0, d;
    if (edge & AT_KEY_ENTER) EMIT(AT_EV_ACCEPT, 0, 0);
    if (edge & AT_KEY_ESC) EMIT(AT_EV_BACK, 0, 0);
    if (edge & AT_KEY_TAB) EMIT(AT_EV_PAGE, (m & AT_KEY_SHIFT) ? -1 : 1, 0);
    d = dir_from(m & AT_KEY_UP, m & AT_KEY_DOWN, m & AT_KEY_LEFT, m & AT_KEY_RIGHT);
    d = at_repeat_step(&k->rep, d, now);
    if (d) EMIT(AT_EV_MOVE, d, 0);
    k->prev = m;
    return n;
}

int at_hit_test(const AtHits *h, float x, float y)
{
    int i;
    for (i = h->n - 1; i >= 0; i--) {                       /* the latest drawn is the topmost */
        const AtRect *r = &h->h[i].r;
        if (x >= r->x && x < r->x + r->w && y >= r->y && y < r->y + r->h) return i;
    }
    return -1;
}

static void press_button(int ch, AtEvent *out, int cap, int *np)
{
    int n = *np;
    if (ch == 'A') EMIT(AT_EV_ACCEPT, 0, 0);
    else if (ch == 'B') EMIT(AT_EV_BACK, 0, 0);
    else if (ch == 'X' || ch == 'Y' || ch == 'Z') EMIT(AT_EV_ALT, ch, 0);
    else if (ch == 'L') EMIT(AT_EV_PAGE, -1, 0);
    else if (ch == 'R') EMIT(AT_EV_PAGE, 1, 0);
    else if (ch == 'S') EMIT(AT_EV_START, 0, 0);
    *np = n;
}

int at_mouse_events(AtMouse *m, float x, float y, int buttons, int wheel, const AtHits *hits, AtEvent *out, int cap)
{
    int n = 0, hit, moved, left, right;
    if (x < 0.0f || y < 0.0f) {                              /* off the picture (-1000): never an event */
        m->valid = 0;
        m->buttons = buttons;
        return 0;
    }
    moved = m->valid && (x != m->x || y != m->y);
    left = (buttons & 1) && !(m->buttons & 1) && m->valid;
    right = (buttons & 2) && !(m->buttons & 2) && m->valid;
    hit = at_hit_test(hits, x, y);
    if (moved && hit >= 0 && hits->h[hit].kind == AT_HIT_CELL) EMIT(AT_EV_FOCUS, hits->h[hit].a, hits->h[hit].b);
    if (left && hit >= 0) {
        const AtHit *h = &hits->h[hit];
        if (h->kind == AT_HIT_CELL) {
            if (!moved) EMIT(AT_EV_FOCUS, h->a, h->b);
            EMIT(AT_EV_ACCEPT, 0, 0);
        } else {
            press_button(h->a, out, cap, &n);
        }
    }
    if (right) EMIT(AT_EV_BACK, 0, 0);
    if (wheel != 0) EMIT(AT_EV_SCROLL, wheel > 0 ? -1 : 1, 0);
    m->valid = 1;
    m->x = x;
    m->y = y;
    m->buttons = buttons;
    return n;
}
```

Note the test sequence the code must satisfy: in the "left click" step the pointer did not move (221,120 twice), so `moved` is false and the code emits FOCUS then ACCEPT (two events); in the step at (221,120) with buttons 1 right after a move step, `moved` was already consumed. In the "re-entering with the button held" case `valid` is 0 on re-entry so `left` is false.

- [ ] **Step 4: Run the tests.**

```bash
nt atlas-input
```

Expected: `atlas input: 37 checks, 0 failed`.

- [ ] **Step 5: Commit.** Game repo: `pc/platform/gw_ui_input.h`, `gw_ui_input.c`, `pc/tests/atlas_input_test.c`, message `atlas: pad, keyboard and mouse into one event type; hit testing`. Workspace repo: `tools/port/native_test.sh`, message `atlas: atlas-input native test case`.

---

### Task 5: The screen record, conversion from a value tree, validation and refocus

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_val.h`, `gw_ui_val.c`, `gw_ui_screen.h`, `gw_ui_screen.c`, `melee/pc/tests/atlas_screen_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-screen`)

**Interfaces:**
Consumes: `AtFocusBlock`, `AtFocusPos`, `at_focus_first` (Task 3).
Produces:

```c
/* gw_ui_val.h */
#define ATV_MAX_NODES 2048
#define ATV_MAX_ENTRIES 4096
#define ATV_POOL 49152
typedef enum { ATV_NIL, ATV_BOOL, ATV_NUM, ATV_STR, ATV_TABLE, ATV_FN } AtvKind;
typedef struct { unsigned char kind, b; int fn; double num; int str; int first, last, narr; } AtvNode;
typedef struct { int key, val, next; } AtvEntry;           /* key: pool offset of the name, -1 for an array entry */
typedef struct { AtvNode node[ATV_MAX_NODES]; AtvEntry ent[ATV_MAX_ENTRIES]; char pool[ATV_POOL]; int nn, ne, np, overflow; } AtvArena;
void atv_init(AtvArena *a);
int atv_bool(AtvArena *a, int b);  int atv_num(AtvArena *a, double d);  int atv_str(AtvArena *a, const char *s);
int atv_fn(AtvArena *a, int ref);  int atv_table(AtvArena *a);                   /* node index, -1 on overflow */
int atv_set(AtvArena *a, int t, const char *key, int v);  int atv_push(AtvArena *a, int t, int v);
int atv_get(const AtvArena *a, int t, const char *key);   int atv_at(const AtvArena *a, int t, int i1);  int atv_len(const AtvArena *a, int t);
int atv_kind(const AtvArena *a, int n);  double atv_numv(const AtvArena *a, int n, double def);
const char *atv_strv(const AtvArena *a, int n, const char *def);  int atv_boolv(const AtvArena *a, int n, int def);  int atv_fnv(const AtvArena *a, int n);

/* gw_ui_screen.h */
#define AT_MAX_BLOCKS 6
#define AT_MAX_CELLS 12
#define AT_MAX_ITEMS 32
#define AT_MAX_KEYS 6
#define AT_MAX_WITH 4
#define AT_ID 24
#define AT_STR 64
#define AT_TEXT 160
#define AT_NO_MODEL (-1)
enum { AT_PRIMARY_LIST = 1, AT_PRIMARY_GRID = 2 };
enum { AT_CELL_LOCKED = 1, AT_CELL_EMPTY = 2, AT_CELL_MERGE = 4, AT_CELL_NEW = 8, AT_CELL_SELECTED = 16, AT_CELL_DISABLED = 32 };
enum { AT_VAL_NONE, AT_VAL_TOGGLE, AT_VAL_CHOICE, AT_VAL_SLIDER, AT_VAL_TEXT, AT_VAL_COUNTER };
typedef struct { char id[AT_ID]; char name[AT_STR]; int model, ring; unsigned flags; int index, pips; char origin; unsigned rgba; char letter; } AtCell;
typedef struct { char id[AT_ID]; char title[AT_STR]; char count[24]; char note[AT_STR]; int cols, n, stones; AtCell cells[AT_MAX_CELLS]; } AtBlock;
typedef struct { char id[AT_ID]; char label[AT_STR]; char sub[AT_STR]; unsigned flags; int vkind, on; char text[AT_STR]; int vmin, vmax, vval; } AtItem;
typedef struct { char btn; char label[AT_STR]; int fn_label, fn_when; } AtKey;
typedef struct { int has; char label[24]; int model_a, model_b, model_out; char text[AT_STR]; } AtFooter;
typedef struct { int has; int media_model, media_ring; char kicker[AT_STR], title[AT_STR], what[AT_TEXT]; int n_with, with_model[AT_MAX_WITH]; char from_text[AT_STR]; int warn; } AtExplainer;
typedef struct { char id[AT_ID * 2]; char title[AT_STR]; char parent[3][AT_STR]; int n_parents; int primary, preset, chapter; AtBlock blocks[AT_MAX_BLOCKS]; int n_blocks; AtItem items[AT_MAX_ITEMS]; int n_items;
                 AtFooter footer; AtKey keys[AT_MAX_KEYS]; int n_keys; char counter[AT_STR]; int fn_counter, input_feed, port;
                 int fn_provide, fn_accept, fn_back, fn_alt[3], fn_focus, fn_change, fn_open, fn_close; int warnings; } AtScreen;
typedef struct { char text[AT_STR]; int kind; double from_ms, until_ms; } AtNote;
typedef struct { int open; char title[AT_STR]; char body[AT_TEXT]; int n; char btn[2]; char label[2][24]; int focus; double from_ms; } AtDialog;
typedef struct { AtFocusPos focus; int scroll; AtExplainer ex; char key_label[AT_MAX_KEYS][AT_STR]; unsigned char key_shown[AT_MAX_KEYS];
                 char counter[AT_STR]; AtNote note; AtDialog dialog; double opened_ms; unsigned port_rgba; } AtView;
int at_screen_from_val(const AtvArena *a, int root, const char *owner_mod, AtScreen *out, char *err, int errcap);   /* 1 ok, 0 error text in err */
int at_explainer_from_val(const AtvArena *a, int t, AtExplainer *out, char *err, int errcap);
int at_screen_fn_refs(const AtScreen *s, int *out, int cap);
void at_view_init(AtView *v);
int at_screen_focus_blocks(const AtScreen *s, AtFocusBlock *fb);                       /* returns the block count */
const char *at_screen_block_id(const AtScreen *s, int block);
const char *at_screen_cell_id(const AtScreen *s, AtFocusPos p);                        /* NULL when invalid */
AtFocusPos at_screen_refocus(const AtScreen *s, const char *block_id, const char *cell_id, AtFocusPos old);
int at_cell_accepts(const AtScreen *s, AtFocusPos p);
int at_screen_wants_pad(const AtScreen *s);
```

- [ ] **Step 1: Write the failing test.** Create `melee/pc/tests/atlas_screen_test.c`:

```c
#include <stdlib.h>
#include "atlas_check.h"
#include "../platform/gw_ui_screen.h"

static AtvArena *A;
static int S(int t, const char *k, const char *v) { return atv_set(A, t, k, atv_str(A, v)); }
static int N(int t, const char *k, double v) { return atv_set(A, t, k, atv_num(A, v)); }
static int B(int t, const char *k, int v) { return atv_set(A, t, k, atv_bool(A, v)); }

static int cell(const char *id, const char *name, int model, int locked, int empty)
{
    int c = atv_table(A), f;
    S(c, "id", id); S(c, "name", name);
    if (model >= 0) N(c, "model", model);
    f = atv_table(A);
    if (locked) B(f, "locked", 1);
    if (empty) B(f, "empty", 1);
    atv_set(A, c, "flags", f);
    return c;
}

static int block(const char *id, const char *title, int cols, int stones)
{
    int b = atv_table(A), cells = atv_table(A);
    S(b, "id", id); S(b, "title", title); N(b, "cols", cols);
    if (stones) S(b, "kind", "stones");
    atv_set(A, b, "cells", cells);
    return b;
}

static int key(const char *btn, const char *label, int fn)
{
    int k = atv_table(A);
    atv_push(A, k, atv_str(A, btn));
    atv_push(A, k, fn >= 0 ? atv_fn(A, fn) : atv_str(A, label));
    return k;
}

/* the Envoy bag, as the Lua description would arrive */
static int bag(const char *id)
{
    int root = atv_table(A), trail = atv_table(A), prim = atv_table(A), blocks = atv_table(A), b, cells, i, ex = atv_table(A), keys = atv_table(A), on = atv_table(A), alt = atv_table(A);
    char buf[24];
    S(root, "id", id);
    S(trail, "title", "YOUR DRIVES"); atv_push(A, trail, atv_str(A, "SOLO")); atv_push(A, trail, atv_str(A, "ENVOY")); atv_set(A, root, "trail", trail);
    S(prim, "kind", "grid");
    b = block("eq", "EQUIPPED", 6, 0); cells = atv_get(A, b, "cells"); S(b, "count", "5 / 6");
    for (i = 0; i < 6; i++) { snprintf(buf, sizeof buf, "eq:%d", i + 1); atv_push(A, cells, i == 5 ? cell(buf, "Locked slot", -1, 1, 0) : cell(buf, "Drive", 100 + i, 0, 0)); }
    atv_push(A, blocks, b);
    b = block("bag", "BAG", 4, 0); cells = atv_get(A, b, "cells");
    for (i = 0; i < 4; i++) { snprintf(buf, sizeof buf, "bag:%d", i + 1); atv_push(A, cells, i == 3 ? cell(buf, "Empty slot", -1, 0, 1) : cell(buf, "Drive", 110 + i, 0, 0)); }
    atv_push(A, blocks, b);
    b = block("key", "KEYSTONE", 6, 1); cells = atv_get(A, b, "cells"); S(b, "note", "One held");
    for (i = 0; i < 3; i++) { snprintf(buf, sizeof buf, "key:%d", i + 1); atv_push(A, cells, cell(buf, "Keystone", -1, 0, 0)); }
    atv_push(A, blocks, b);
    atv_set(A, prim, "blocks", blocks); atv_set(A, root, "primary", prim);
    S(ex, "width", "narrow"); atv_set(A, ex, "provide", atv_fn(A, 7)); atv_set(A, root, "explainer", ex);
    atv_push(A, keys, key("A", 0, 11)); atv_push(A, keys, key("X", "Discard", -1)); atv_push(A, keys, key("Y", "More", -1)); atv_push(A, keys, key("B", "Close", -1));
    atv_set(A, root, "keys", keys);
    atv_set(A, on, "accept", atv_fn(A, 21)); atv_set(A, on, "back", atv_fn(A, 22)); atv_set(A, alt, "X", atv_fn(A, 23)); atv_set(A, on, "alt", alt);
    atv_set(A, on, "focus", atv_fn(A, 24)); atv_set(A, root, "on", on);
    S(root, "input", "feed"); N(root, "port", 2);
    return root;
}

static void parse_bag(void)
{
    static AtScreen sc;
    char err[160];
    int refs[24], n;
    CHECK(at_screen_from_val(A, bag("envoy.bag"), "envoy", &sc, err, sizeof err));
    CHECK_STR(sc.id, "envoy.bag"); CHECK_STR(sc.title, "YOUR DRIVES");
    CHECK(sc.n_parents == 2); CHECK_STR(sc.parent[0], "SOLO"); CHECK_STR(sc.parent[1], "ENVOY");
    CHECK(sc.primary == AT_PRIMARY_GRID && sc.n_blocks == 3 && sc.preset == AT_PRESET_NARROW);
    CHECK(sc.blocks[0].n == 6 && sc.blocks[1].n == 4 && sc.blocks[2].n == 3);
    CHECK(sc.blocks[2].stones == 1 && sc.blocks[0].stones == 0);
    CHECK_STR(sc.blocks[0].count, "5 / 6"); CHECK_STR(sc.blocks[2].note, "One held");
    CHECK(sc.blocks[0].cells[5].flags & AT_CELL_LOCKED); CHECK(sc.blocks[1].cells[3].flags & AT_CELL_EMPTY);
    CHECK(sc.blocks[0].cells[0].model == 100 && sc.blocks[0].cells[5].model == AT_NO_MODEL);
    CHECK(sc.n_keys == 4 && sc.keys[0].btn == 'A' && sc.keys[0].fn_label == 11 && sc.keys[1].btn == 'X');
    CHECK_STR(sc.keys[1].label, "Discard");
    CHECK(sc.fn_provide == 7 && sc.fn_accept == 21 && sc.fn_back == 22 && sc.fn_alt[0] == 23 && sc.fn_alt[1] == -1 && sc.fn_focus == 24 && sc.fn_change == -1);
    CHECK(sc.input_feed == 1 && sc.port == 2);
    CHECK(!at_screen_wants_pad(&sc));                                  /* feed: the engine must not poll the pad as well */
    n = at_screen_fn_refs(&sc, refs, 24);
    CHECK(n == 6);                                                      /* provide, accept, back, alt X, focus, key A's label */
}

static void errors(void)
{
    static AtScreen sc;
    char err[160];
    int root, prim, blocks, b;
    root = atv_table(A);
    CHECK(!at_screen_from_val(A, root, NULL, &sc, err, sizeof err)); CHECK(strstr(err, "id") != NULL);
    CHECK(!at_screen_from_val(A, atv_str(A, "x"), NULL, &sc, err, sizeof err));
    CHECK(!at_screen_from_val(A, bag("other.bag"), "envoy", &sc, err, sizeof err));        /* a mod's ids start with its own id */
    CHECK(strstr(err, "envoy.") != NULL);
    root = atv_table(A); S(root, "id", "m.x"); prim = atv_table(A); S(prim, "kind", "tiles"); atv_set(A, root, "primary", prim);
    CHECK(!at_screen_from_val(A, root, NULL, &sc, err, sizeof err)); CHECK(strstr(err, "tiles") != NULL);
    root = atv_table(A); S(root, "id", "m.x"); prim = atv_table(A); S(prim, "kind", "grid"); blocks = atv_table(A);
    for (b = 0; b < 7; b++) atv_push(A, blocks, block("b", "B", 2, 0));
    atv_set(A, prim, "blocks", blocks); atv_set(A, root, "primary", prim);
    CHECK(!at_screen_from_val(A, root, NULL, &sc, err, sizeof err)); CHECK(strstr(err, "blocks") != NULL);
    root = atv_table(A); S(root, "id", "m.x"); prim = atv_table(A); S(prim, "kind", "grid"); blocks = atv_table(A);
    b = block("b", "B", 2, 0); atv_push(A, atv_get(A, b, "cells"), cell("c", "one", -1, 0, 0)); atv_push(A, atv_get(A, b, "cells"), cell("c", "two", -1, 0, 0));
    atv_push(A, blocks, b); atv_set(A, prim, "blocks", blocks); atv_set(A, root, "primary", prim);
    CHECK(!at_screen_from_val(A, root, NULL, &sc, err, sizeof err)); CHECK(strstr(err, "duplicate") != NULL);
    root = bag("m.bag"); { int k = atv_get(A, root, "keys"); atv_push(A, k, key("Q", "Nope", -1)); }
    CHECK(!at_screen_from_val(A, root, NULL, &sc, err, sizeof err)); CHECK(strstr(err, "button") != NULL);
    root = atv_table(A); S(root, "id", "m.x"); prim = atv_table(A); S(prim, "kind", "grid"); blocks = atv_table(A);
    b = block("b", "B", 20, 0);                                                              /* more columns than cells per block */
    atv_push(A, blocks, b); atv_set(A, prim, "blocks", blocks); atv_set(A, root, "primary", prim);
    CHECK(!at_screen_from_val(A, root, NULL, &sc, err, sizeof err)); CHECK(strstr(err, "cols") != NULL);
}

static void list_screen(void)
{
    static AtScreen sc;
    char err[160];
    int root = atv_table(A), prim = atv_table(A), items = atv_table(A), it, v;
    S(root, "id", "demo.list"); S(prim, "kind", "list");
    it = atv_table(A); S(it, "id", "sync"); S(it, "label", "Sync"); v = atv_table(A); S(v, "kind", "toggle"); B(v, "on", 1); atv_set(A, it, "value", v); atv_push(A, items, it);
    it = atv_table(A); S(it, "id", "vol"); S(it, "label", "Volume"); v = atv_table(A); S(v, "kind", "slider"); N(v, "min", 0); N(v, "max", 100); N(v, "value", 30); atv_set(A, it, "value", v); atv_push(A, items, it);
    it = atv_table(A); S(it, "id", "off"); S(it, "label", "Closed"); B(it, "disabled", 1); atv_push(A, items, it);
    atv_set(A, prim, "items", items); atv_set(A, root, "primary", prim);
    CHECK(at_screen_from_val(A, root, "demo", &sc, err, sizeof err));
    CHECK(sc.primary == AT_PRIMARY_LIST && sc.n_items == 3 && sc.preset == AT_PRESET_NONE);
    CHECK(sc.items[0].vkind == AT_VAL_TOGGLE && sc.items[0].on == 1);
    CHECK(sc.items[1].vkind == AT_VAL_SLIDER && sc.items[1].vmax == 100 && sc.items[1].vval == 30);
    CHECK(sc.items[2].flags & AT_CELL_DISABLED);
}

static void explainer(void)
{
    AtExplainer e;
    char err[160], big[400];
    int t = atv_table(A), with = atv_table(A), from = atv_table(A), media = atv_table(A);
    S(t, "kicker", "BAG CELL 1"); S(t, "title", "KINDLING"); S(t, "what", "Your hits set the target Burning for 3 s.");
    N(media, "model", 5); N(media, "ring", 6); atv_set(A, t, "media", media);
    atv_push(A, with, atv_num(A, 8)); atv_push(A, with, atv_num(A, 9)); atv_set(A, t, "with", with);
    S(from, "text", "Depth 0, Fire"); atv_set(A, t, "from", from);
    CHECK(at_explainer_from_val(A, t, &e, err, sizeof err));
    CHECK(e.has && e.media_model == 5 && e.media_ring == 6 && e.n_with == 2 && e.with_model[1] == 9 && e.warn == 0);
    CHECK_STR(e.title, "KINDLING"); CHECK_STR(e.from_text, "Depth 0, Fire");
    memset(big, 'a', sizeof big - 1); big[sizeof big - 1] = '\0';
    t = atv_table(A); S(t, "title", "T"); S(t, "what", big);
    CHECK(at_explainer_from_val(A, t, &e, err, sizeof err));
    CHECK(strlen(e.what) == AT_TEXT - 1 && e.warn == 1);                /* clamped, and said so */
    CHECK(at_explainer_from_val(A, -1, &e, err, sizeof err) && e.has == 0);   /* nothing to explain: the pane is empty */
}

static AtFocusPos P(int b, int i) { AtFocusPos p; p.block = b; p.index = i; return p; }

static void refocus(void)
{
    static AtScreen sc;
    char err[160];
    AtFocusBlock fb[AT_MAX_BLOCKS];
    AtFocusPos p;
    CHECK(at_screen_from_val(A, bag("envoy.bag"), "envoy", &sc, err, sizeof err));
    CHECK(at_screen_focus_blocks(&sc, fb) == 3);
    CHECK(fb[0].row0 == 0 && fb[1].row0 == 1 && fb[2].row0 == 2 && fb[1].cols == 4);
    CHECK_STR(at_screen_cell_id(&sc, P(1, 2)), "bag:3"); CHECK_STR(at_screen_block_id(&sc, 1), "bag");
    CHECK(at_screen_cell_id(&sc, P(1, 9)) == NULL && at_screen_cell_id(&sc, P(-1, 0)) == NULL);
    p = at_screen_refocus(&sc, "bag", "bag:3", P(1, 2)); CHECK(p.block == 1 && p.index == 2);        /* the same cell stays */
    sc.blocks[1].n = 3;                                                                              /* a discard shrank the bag */
    p = at_screen_refocus(&sc, "bag", "bag:4", P(1, 3));
    CHECK(p.block == 1 && p.index == 2);                                                              /* the gone cell: the same block, clamped */
    sc.blocks[1].n = 0;                                                                               /* the whole block went */
    p = at_screen_refocus(&sc, "bag", "bag:1", P(1, 0));
    CHECK(p.block == 0 && p.index == 0);                                                              /* never "nothing" while a cell exists */
    p = at_screen_refocus(&sc, NULL, NULL, P(-1, -1)); CHECK(p.block == 0 && p.index == 0);
    sc.blocks[0].n = 0; sc.blocks[2].n = 0;
    p = at_screen_refocus(&sc, "eq", "eq:1", P(0, 0)); CHECK(p.block == -1 && p.index == -1);          /* truly empty */
}

static void accept_semantics(void)
{
    static AtScreen sc, ls;
    char err[160];
    int root = atv_table(A), prim = atv_table(A), items = atv_table(A), it;
    CHECK(at_screen_from_val(A, bag("envoy.bag"), "envoy", &sc, err, sizeof err));
    CHECK(at_cell_accepts(&sc, P(0, 5)));                              /* a LOCKED slot still reaches the handler (it says what it is) */
    CHECK(at_cell_accepts(&sc, P(1, 3)));                              /* an EMPTY slot too */
    CHECK(!at_cell_accepts(&sc, P(7, 0)));                             /* a position that is not there accepts nothing */
    S(root, "id", "demo.list"); S(prim, "kind", "list");
    it = atv_table(A); S(it, "id", "a"); S(it, "label", "A"); atv_push(A, items, it);
    it = atv_table(A); S(it, "id", "b"); S(it, "label", "B"); B(it, "disabled", 1); atv_push(A, items, it);
    atv_set(A, prim, "items", items); atv_set(A, root, "primary", prim);
    CHECK(at_screen_from_val(A, root, NULL, &ls, err, sizeof err));
    CHECK(at_cell_accepts(&ls, P(0, 0)));
    CHECK(!at_cell_accepts(&ls, P(0, 1)));                             /* a DISABLED row is focusable but never fires */
    CHECK(at_screen_wants_pad(&ls));                                   /* default: the engine polls the pad */
}

int main(void)
{
    A = (AtvArena *) malloc(sizeof *A);
    atv_init(A); parse_bag();
    atv_init(A); errors();
    atv_init(A); list_screen();
    atv_init(A); explainer();
    atv_init(A); refocus();
    atv_init(A); accept_semantics();
    free(A);
    ATLAS_DONE("atlas screen");
}
```

Register: `atlas-screen) sources=(pc/tests/atlas_screen_test.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c) ;;` and add `, atlas-screen` to the die message.

- [ ] **Step 2: Run it to verify it fails.**

```bash
nt atlas-screen
```

Expected: `error: native test source missing: pc/platform/gw_ui_screen.c`.

- [ ] **Step 3: Write the minimal implementation.** Create `melee/pc/platform/gw_ui_val.h`:

```c
/* gw_ui_val.h - a tiny value tree, so the Lua-to-screen conversion is testable without Lua. Pure C. */
#ifndef GW_UI_VAL_H
#define GW_UI_VAL_H
#ifdef __cplusplus
extern "C" {
#endif

#define ATV_MAX_NODES 2048
#define ATV_MAX_ENTRIES 4096
#define ATV_POOL 49152

typedef enum { ATV_NIL, ATV_BOOL, ATV_NUM, ATV_STR, ATV_TABLE, ATV_FN } AtvKind;
typedef struct { unsigned char kind, b; int fn; double num; int str; int first, last, narr; } AtvNode;
typedef struct { int key, val, next; } AtvEntry;   /* key: pool offset of the name, -1 for an array entry */
typedef struct { AtvNode node[ATV_MAX_NODES]; AtvEntry ent[ATV_MAX_ENTRIES]; char pool[ATV_POOL]; int nn, ne, np, overflow; } AtvArena;

void atv_init(AtvArena *a);
/* constructors return the node index, or -1 when the arena is full (then a->overflow is set) */
int atv_bool(AtvArena *a, int b);
int atv_num(AtvArena *a, double d);
int atv_str(AtvArena *a, const char *s);
int atv_fn(AtvArena *a, int ref);
int atv_table(AtvArena *a);
int atv_set(AtvArena *a, int t, const char *key, int v);   /* t[key] = v; returns the entry or -1 */
int atv_push(AtvArena *a, int t, int v);                   /* append to t's array part */
/* readers: -1 / defaults for anything that is not there or has another kind */
int atv_get(const AtvArena *a, int t, const char *key);
int atv_at(const AtvArena *a, int t, int i1);              /* the i-th array entry, 1-based */
int atv_len(const AtvArena *a, int t);                     /* the number of array entries */
int atv_kind(const AtvArena *a, int n);
double atv_numv(const AtvArena *a, int n, double def);
const char *atv_strv(const AtvArena *a, int n, const char *def);
int atv_boolv(const AtvArena *a, int n, int def);
int atv_fnv(const AtvArena *a, int n);                     /* the registry reference, or -1 */

#ifdef __cplusplus
}
#endif
#endif
```

Create `melee/pc/platform/gw_ui_val.c`:

```c
#include "gw_ui_val.h"

#include <stdio.h>
#include <string.h>

void atv_init(AtvArena *a) { a->nn = a->ne = a->np = a->overflow = 0; }

static int node_new(AtvArena *a, int kind)
{
    AtvNode *n;
    if (a->nn >= ATV_MAX_NODES) { a->overflow = 1; return -1; }
    n = &a->node[a->nn];
    memset(n, 0, sizeof *n);
    n->kind = (unsigned char) kind;
    n->first = n->last = -1;
    n->fn = -1;
    return a->nn++;
}

static int pool_put(AtvArena *a, const char *s)
{
    int len = (int) strlen(s) + 1, at = a->np;
    if (a->np + len > ATV_POOL) { a->overflow = 1; return -1; }
    memcpy(a->pool + at, s, (size_t) len);
    a->np += len;
    return at;
}

int atv_bool(AtvArena *a, int b) { int n = node_new(a, ATV_BOOL); if (n >= 0) a->node[n].b = (unsigned char) (b != 0); return n; }
int atv_num(AtvArena *a, double d) { int n = node_new(a, ATV_NUM); if (n >= 0) a->node[n].num = d; return n; }
int atv_fn(AtvArena *a, int ref) { int n = node_new(a, ATV_FN); if (n >= 0) a->node[n].fn = ref; return n; }
int atv_table(AtvArena *a) { return node_new(a, ATV_TABLE); }
int atv_str(AtvArena *a, const char *s)
{
    int n = node_new(a, ATV_STR), p;
    if (n < 0) return -1;
    p = pool_put(a, s);
    if (p < 0) return -1;
    a->node[n].str = p;
    return n;
}

static int entry_add(AtvArena *a, int t, int key, int v)
{
    AtvEntry *e;
    AtvNode *tn;
    if (t < 0 || t >= a->nn || a->node[t].kind != ATV_TABLE || v < 0) return -1;
    if (a->ne >= ATV_MAX_ENTRIES) { a->overflow = 1; return -1; }
    e = &a->ent[a->ne];
    e->key = key; e->val = v; e->next = -1;
    tn = &a->node[t];
    if (tn->last >= 0) a->ent[tn->last].next = a->ne; else tn->first = a->ne;
    tn->last = a->ne;
    if (key < 0) tn->narr++;
    return a->ne++;
}

int atv_set(AtvArena *a, int t, const char *key, int v)
{
    int k = pool_put(a, key);
    return k < 0 ? -1 : entry_add(a, t, k, v);
}
int atv_push(AtvArena *a, int t, int v) { return entry_add(a, t, -1, v); }

int atv_get(const AtvArena *a, int t, const char *key)
{
    int e;
    if (t < 0 || t >= a->nn || a->node[t].kind != ATV_TABLE) return -1;
    for (e = a->node[t].first; e >= 0; e = a->ent[e].next)
        if (a->ent[e].key >= 0 && strcmp(a->pool + a->ent[e].key, key) == 0) return a->ent[e].val;
    return -1;
}

int atv_at(const AtvArena *a, int t, int i1)
{
    int e, k = 0;
    if (t < 0 || t >= a->nn || a->node[t].kind != ATV_TABLE) return -1;
    for (e = a->node[t].first; e >= 0; e = a->ent[e].next)
        if (a->ent[e].key < 0 && ++k == i1) return a->ent[e].val;
    return -1;
}

int atv_len(const AtvArena *a, int t) { return (t >= 0 && t < a->nn && a->node[t].kind == ATV_TABLE) ? a->node[t].narr : 0; }
int atv_kind(const AtvArena *a, int n) { return (n >= 0 && n < a->nn) ? a->node[n].kind : ATV_NIL; }
double atv_numv(const AtvArena *a, int n, double def) { return atv_kind(a, n) == ATV_NUM ? a->node[n].num : def; }
const char *atv_strv(const AtvArena *a, int n, const char *def) { return atv_kind(a, n) == ATV_STR ? a->pool + a->node[n].str : def; }
int atv_boolv(const AtvArena *a, int n, int def) { return atv_kind(a, n) == ATV_BOOL ? a->node[n].b : def; }
int atv_fnv(const AtvArena *a, int n) { return atv_kind(a, n) == ATV_FN ? a->node[n].fn : -1; }
```

Create `melee/pc/platform/gw_ui_screen.h`:

```c
/* gw_ui_screen.h - the Atlas screen record, its dynamic view, conversion from a value tree, validation, focus helpers. Pure C. */
#ifndef GW_UI_SCREEN_H
#define GW_UI_SCREEN_H
#include "gw_ui_focus.h"
#include "gw_ui_layout.h"
#include "gw_ui_val.h"
#ifdef __cplusplus
extern "C" {
#endif

#define AT_MAX_BLOCKS 6
#define AT_MAX_CELLS 12
#define AT_MAX_ITEMS 32
#define AT_MAX_KEYS 6
#define AT_MAX_WITH 4
#define AT_ID 24
#define AT_STR 64
#define AT_TEXT 160
#define AT_NO_MODEL (-1)

enum { AT_PRIMARY_LIST = 1, AT_PRIMARY_GRID = 2 };
enum { AT_CELL_LOCKED = 1, AT_CELL_EMPTY = 2, AT_CELL_MERGE = 4, AT_CELL_NEW = 8, AT_CELL_SELECTED = 16, AT_CELL_DISABLED = 32 };
enum { AT_VAL_NONE, AT_VAL_TOGGLE, AT_VAL_CHOICE, AT_VAL_SLIDER, AT_VAL_TEXT, AT_VAL_COUNTER };

typedef struct { char id[AT_ID]; char name[AT_STR]; int model, ring; unsigned flags; int index, pips; char origin; unsigned rgba; char letter; } AtCell;
typedef struct { char id[AT_ID]; char title[AT_STR]; char count[24]; char note[AT_STR]; int cols, n, stones; AtCell cells[AT_MAX_CELLS]; } AtBlock;
typedef struct { char id[AT_ID]; char label[AT_STR]; char sub[AT_STR]; unsigned flags; int vkind, on; char text[AT_STR]; int vmin, vmax, vval; } AtItem;
typedef struct { char btn; char label[AT_STR]; int fn_label, fn_when; } AtKey;
typedef struct { int has; char label[24]; int model_a, model_b, model_out; char text[AT_STR]; } AtFooter;
typedef struct { int has; int media_model, media_ring; char kicker[AT_STR], title[AT_STR], what[AT_TEXT]; int n_with, with_model[AT_MAX_WITH]; char from_text[AT_STR]; int warn; } AtExplainer;

typedef struct {
    char id[AT_ID * 2];
    char title[AT_STR];
    char parent[3][AT_STR]; int n_parents;
    int primary, preset, chapter;
    AtBlock blocks[AT_MAX_BLOCKS]; int n_blocks;
    AtItem items[AT_MAX_ITEMS]; int n_items;
    AtFooter footer;
    AtKey keys[AT_MAX_KEYS]; int n_keys;
    char counter[AT_STR]; int fn_counter;
    int input_feed, port;
    int fn_provide, fn_accept, fn_back, fn_alt[3], fn_focus, fn_change, fn_open, fn_close;
    int warnings;
} AtScreen;

typedef struct { char text[AT_STR]; int kind; double from_ms, until_ms; } AtNote;
typedef struct { int open; char title[AT_STR]; char body[AT_TEXT]; int n; char btn[2]; char label[2][24]; int focus; double from_ms; } AtDialog;
typedef struct {
    AtFocusPos focus; int scroll; AtExplainer ex;
    char key_label[AT_MAX_KEYS][AT_STR]; unsigned char key_shown[AT_MAX_KEYS];
    char counter[AT_STR]; AtNote note; AtDialog dialog; double opened_ms; unsigned port_rgba;
} AtView;

/* 1 ok; 0 with the reason in err. owner_mod: the mod id every screen id must start with (NULL or "" for none). */
int at_screen_from_val(const AtvArena *a, int root, const char *owner_mod, AtScreen *out, char *err, int errcap);
int at_explainer_from_val(const AtvArena *a, int t, AtExplainer *out, char *err, int errcap);   /* t = -1: an empty explainer */
int at_screen_fn_refs(const AtScreen *s, int *out, int cap);                                    /* every Lua reference the screen holds */
void at_view_init(AtView *v);
int at_screen_focus_blocks(const AtScreen *s, AtFocusBlock *fb);                                /* returns the block count */
const char *at_screen_block_id(const AtScreen *s, int block);
const char *at_screen_cell_id(const AtScreen *s, AtFocusPos p);                                 /* NULL when invalid */
AtFocusPos at_screen_refocus(const AtScreen *s, const char *block_id, const char *cell_id, AtFocusPos old);
int at_cell_accepts(const AtScreen *s, AtFocusPos p);                                           /* 0 for a disabled or missing cell */
int at_screen_wants_pad(const AtScreen *s);                                                     /* 0 when the script feeds its own pad input */

#ifdef __cplusplus
}
#endif
#endif
```

Create `melee/pc/platform/gw_ui_screen.c`:

```c
#include "gw_ui_screen.h"

#include <stdio.h>
#include <string.h>

#define FAIL(...) do { snprintf(err, (size_t) errcap, __VA_ARGS__); return 0; } while (0)

/* ---- small readers; a string cut to its field counts as a warning ---------------------------------- */
static void get_str(const AtvArena *a, int t, const char *k, char *dst, int cap, int *warn)
{
    int n = atv_get(a, t, k);
    const char *s;
    if (atv_kind(a, n) != ATV_STR) return;
    s = atv_strv(a, n, "");
    if ((int) strlen(s) >= cap && warn) (*warn)++;
    snprintf(dst, (size_t) cap, "%s", s);
}
static int get_int(const AtvArena *a, int t, const char *k, int def) { return (int) atv_numv(a, atv_get(a, t, k), def); }
static int get_fn(const AtvArena *a, int t, const char *k) { return atv_fnv(a, atv_get(a, t, k)); }
static int flag(const AtvArena *a, int f, const char *k, unsigned bit) { return atv_boolv(a, atv_get(a, f, k), 0) ? (int) bit : 0; }

static unsigned read_flags(const AtvArena *a, int f)
{
    if (atv_kind(a, f) != ATV_TABLE) return 0;
    return (unsigned) (flag(a, f, "locked", AT_CELL_LOCKED) | flag(a, f, "empty", AT_CELL_EMPTY) | flag(a, f, "merge", AT_CELL_MERGE) |
                       flag(a, f, "new", AT_CELL_NEW) | flag(a, f, "selected", AT_CELL_SELECTED) | flag(a, f, "disabled", AT_CELL_DISABLED));
}

static int button_char(const char *s)
{
    if (strcmp(s, "START") == 0) return 'S';
    if (s[0] != '\0' && s[1] == '\0' && strchr("ABXYZLR", s[0]) != NULL) return s[0];
    return 0;
}

void at_view_init(AtView *v)
{
    memset(v, 0, sizeof *v);
    v->focus.block = v->focus.index = -1;
}

int at_screen_from_val(const AtvArena *a, int root, const char *owner, AtScreen *o, char *err, int errcap)
{
    int prim, blocks, items, i, j, k, ex, keys, on, alt, nb, nc, n;
    const char *kind, *id, *w;
    memset(o, 0, sizeof *o);
    o->fn_provide = o->fn_accept = o->fn_back = o->fn_focus = o->fn_change = o->fn_open = o->fn_close = o->fn_counter = -1;
    o->fn_alt[0] = o->fn_alt[1] = o->fn_alt[2] = -1;
    o->preset = AT_PRESET_NONE;
    o->port = 1;
    if (atv_kind(a, root) != ATV_TABLE) FAIL("gd.ui.screen: a screen description is a table");
    id = atv_strv(a, atv_get(a, root, "id"), "");
    if (id[0] == '\0') FAIL("gd.ui.screen: the description has no id");
    if (owner != NULL && owner[0] != '\0') {
        size_t ol = strlen(owner);
        if (strncmp(id, owner, ol) != 0 || id[ol] != '.') FAIL("gd.ui.screen: id \"%s\" must start with \"%s.\"", id, owner);
    }
    if (strlen(id) >= sizeof o->id) FAIL("gd.ui.screen: id \"%s\" is too long (47 characters at most)", id);
    snprintf(o->id, sizeof o->id, "%s", id);
    snprintf(o->title, sizeof o->title, "%s", id);
    get_str(a, atv_get(a, root, "trail"), "title", o->title, AT_STR, &o->warnings);
    {
        int tr = atv_get(a, root, "trail"), pn = atv_len(a, tr), pi;           /* the trail's array part: the parents ("SOLO", "ENVOY") */
        for (pi = 0; pi < pn && o->n_parents < 3; pi++) {
            const char *ps = atv_strv(a, atv_at(a, tr, pi + 1), "");
            if (ps[0] != '\0') snprintf(o->parent[o->n_parents++], AT_STR, "%s", ps);
        }
    }
    o->chapter = get_int(a, root, "chapter", 0);
    if (o->chapter < 0 || o->chapter > 5) FAIL("gd.ui.screen: chapter is 0 to 5");

    prim = atv_get(a, root, "primary");
    if (atv_kind(a, prim) != ATV_TABLE) FAIL("gd.ui.screen: \"%s\" has no primary", id);
    kind = atv_strv(a, atv_get(a, prim, "kind"), "");
    if (strcmp(kind, "grid") == 0) o->primary = AT_PRIMARY_GRID;
    else if (strcmp(kind, "list") == 0) o->primary = AT_PRIMARY_LIST;
    else FAIL("gd.ui.screen: primary kind \"%s\" is not supported here (grid or list)", kind);

    if (o->primary == AT_PRIMARY_GRID) {
        blocks = atv_get(a, prim, "blocks");
        nb = atv_len(a, blocks);
        if (nb < 1 || nb > AT_MAX_BLOCKS) FAIL("gd.ui.screen: a grid needs 1 to %d blocks (it has %d)", AT_MAX_BLOCKS, nb);
        o->n_blocks = nb;
        for (i = 0; i < nb; i++) {
            int bn = atv_at(a, blocks, i + 1), cells;
            AtBlock *b = &o->blocks[i];
            if (atv_kind(a, bn) != ATV_TABLE) FAIL("gd.ui.screen: block %d is not a table", i + 1);
            get_str(a, bn, "id", b->id, AT_ID, &o->warnings);
            if (b->id[0] == '\0') FAIL("gd.ui.screen: block %d has no id", i + 1);
            get_str(a, bn, "title", b->title, AT_STR, &o->warnings);
            get_str(a, bn, "count", b->count, 24, &o->warnings);
            get_str(a, bn, "note", b->note, AT_STR, &o->warnings);
            b->cols = get_int(a, bn, "cols", 1);
            if (b->cols < 1 || b->cols > AT_MAX_CELLS) FAIL("gd.ui.screen: block \"%s\": cols is 1 to %d", b->id, AT_MAX_CELLS);
            b->stones = strcmp(atv_strv(a, atv_get(a, bn, "kind"), ""), "stones") == 0;
            cells = atv_get(a, bn, "cells");
            nc = atv_len(a, cells);
            if (nc > AT_MAX_CELLS) FAIL("gd.ui.screen: block \"%s\" has %d cells (%d at most)", b->id, nc, AT_MAX_CELLS);
            if (b->cols > nc && nc > 0 && b->cols > AT_MAX_CELLS) FAIL("gd.ui.screen: block \"%s\": cols is larger than the cell limit", b->id);
            b->n = nc;
            for (j = 0; j < nc; j++) {
                int cn = atv_at(a, cells, j + 1), media;
                AtCell *c = &b->cells[j];
                const char *og;
                if (atv_kind(a, cn) != ATV_TABLE) FAIL("gd.ui.screen: block \"%s\" cell %d is not a table", b->id, j + 1);
                get_str(a, cn, "id", c->id, AT_ID, &o->warnings);
                if (c->id[0] == '\0') FAIL("gd.ui.screen: block \"%s\" cell %d has no id", b->id, j + 1);
                for (k = 0; k < i; k++) { int q; for (q = 0; q < o->blocks[k].n; q++) if (strcmp(o->blocks[k].cells[q].id, c->id) == 0) FAIL("gd.ui.screen: duplicate cell id \"%s\"", c->id); }
                for (k = 0; k < j; k++) if (strcmp(b->cells[k].id, c->id) == 0) FAIL("gd.ui.screen: duplicate cell id \"%s\"", c->id);
                get_str(a, cn, "name", c->name, AT_STR, &o->warnings);
                c->model = get_int(a, cn, "model", AT_NO_MODEL);
                c->ring = get_int(a, cn, "ring", AT_NO_MODEL);
                c->index = get_int(a, cn, "index", 0);
                c->pips = get_int(a, cn, "pips", 0);
                if (c->pips < 0) c->pips = 0;
                if (c->pips > 4) c->pips = 4;
                og = atv_strv(a, atv_get(a, cn, "origin"), "");
                c->origin = og[0] == 'G' || og[0] == '+' ? og[0] : 0;
                c->rgba = (unsigned) atv_numv(a, atv_get(a, cn, "color"), 0);
                w = atv_strv(a, atv_get(a, cn, "letter"), "");
                c->letter = w[0];
                c->flags = read_flags(a, atv_get(a, cn, "flags"));
                (void) media;
            }
        }
        {
            int ft = atv_get(a, prim, "footer");
            if (atv_kind(a, ft) == ATV_TABLE) {
                o->footer.has = 1;
                get_str(a, ft, "label", o->footer.label, 24, &o->warnings);
                o->footer.model_a = get_int(a, ft, "a", AT_NO_MODEL);
                o->footer.model_b = get_int(a, ft, "b", AT_NO_MODEL);
                o->footer.model_out = get_int(a, ft, "out", AT_NO_MODEL);
                get_str(a, ft, "text", o->footer.text, AT_STR, &o->warnings);
            }
        }
    } else {
        items = atv_get(a, prim, "items");
        n = atv_len(a, items);
        if (n < 1 || n > AT_MAX_ITEMS) FAIL("gd.ui.screen: a list needs 1 to %d items (it has %d)", AT_MAX_ITEMS, n);
        o->n_items = n;
        for (i = 0; i < n; i++) {
            int in = atv_at(a, items, i + 1), vt;
            AtItem *it = &o->items[i];
            const char *vk;
            if (atv_kind(a, in) != ATV_TABLE) FAIL("gd.ui.screen: item %d is not a table", i + 1);
            get_str(a, in, "id", it->id, AT_ID, &o->warnings);
            if (it->id[0] == '\0') FAIL("gd.ui.screen: item %d has no id", i + 1);
            for (k = 0; k < i; k++) if (strcmp(o->items[k].id, it->id) == 0) FAIL("gd.ui.screen: duplicate item id \"%s\"", it->id);
            get_str(a, in, "label", it->label, AT_STR, &o->warnings);
            get_str(a, in, "sub", it->sub, AT_STR, &o->warnings);
            if (atv_boolv(a, atv_get(a, in, "disabled"), 0)) it->flags |= AT_CELL_DISABLED;
            if (atv_boolv(a, atv_get(a, in, "selected"), 0)) it->flags |= AT_CELL_SELECTED;
            vt = atv_get(a, in, "value");
            if (atv_kind(a, vt) == ATV_TABLE) {
                vk = atv_strv(a, atv_get(a, vt, "kind"), "");
                if (strcmp(vk, "toggle") == 0) { it->vkind = AT_VAL_TOGGLE; it->on = atv_boolv(a, atv_get(a, vt, "on"), 0); }
                else if (strcmp(vk, "choice") == 0) it->vkind = AT_VAL_CHOICE;
                else if (strcmp(vk, "slider") == 0) { it->vkind = AT_VAL_SLIDER; it->vmin = get_int(a, vt, "min", 0); it->vmax = get_int(a, vt, "max", 100); it->vval = get_int(a, vt, "value", 0); }
                else if (strcmp(vk, "text") == 0) it->vkind = AT_VAL_TEXT;
                else if (strcmp(vk, "counter") == 0) it->vkind = AT_VAL_COUNTER;
                else FAIL("gd.ui.screen: item \"%s\": unknown value kind \"%s\"", it->id, vk);
                get_str(a, vt, "text", it->text, AT_STR, &o->warnings);
            }
        }
    }

    ex = atv_get(a, root, "explainer");
    if (atv_kind(a, ex) == ATV_STR) {
        if (strcmp(atv_strv(a, ex, ""), "none") != 0) FAIL("gd.ui.screen: explainer must be a table or \"none\"");
    } else if (atv_kind(a, ex) == ATV_TABLE) {
        w = atv_strv(a, atv_get(a, ex, "width"), "normal");
        if (strcmp(w, "narrow") == 0) o->preset = AT_PRESET_NARROW;
        else if (strcmp(w, "normal") == 0) o->preset = AT_PRESET_NORMAL;
        else if (strcmp(w, "wide") == 0) o->preset = AT_PRESET_WIDE;
        else FAIL("gd.ui.screen: explainer width \"%s\" is narrow, normal or wide", w);
        o->fn_provide = get_fn(a, ex, "provide");
    }

    keys = atv_get(a, root, "keys");
    n = atv_len(a, keys);
    if (n > AT_MAX_KEYS) FAIL("gd.ui.screen: at most %d key hints (%d given)", AT_MAX_KEYS, n);
    o->n_keys = n;
    for (i = 0; i < n; i++) {
        int kn = atv_at(a, keys, i + 1), bn, ln;
        AtKey *key = &o->keys[i];
        const char *bs;
        int ch;
        if (atv_kind(a, kn) != ATV_TABLE) FAIL("gd.ui.screen: key hint %d is not a table", i + 1);
        bn = atv_get(a, kn, "btn"); if (bn < 0) bn = atv_at(a, kn, 1);
        ln = atv_get(a, kn, "label"); if (ln < 0) ln = atv_at(a, kn, 2);
        bs = atv_strv(a, bn, "");
        ch = button_char(bs);
        if (ch == 0) FAIL("gd.ui.screen: key hint %d: unknown button \"%s\" (A B X Y Z L R START)", i + 1, bs);
        key->btn = (char) ch;
        key->fn_label = atv_fnv(a, ln);
        key->fn_when = get_fn(a, kn, "when");
        if (atv_kind(a, ln) == ATV_STR) snprintf(key->label, sizeof key->label, "%s", atv_strv(a, ln, ""));
    }

    {
        int cn = atv_get(a, root, "counter");
        if (atv_kind(a, cn) == ATV_STR) snprintf(o->counter, sizeof o->counter, "%s", atv_strv(a, cn, ""));
        else o->fn_counter = atv_fnv(a, cn);
    }
    o->input_feed = strcmp(atv_strv(a, atv_get(a, root, "input"), "engine"), "feed") == 0;
    o->port = get_int(a, root, "port", 1);
    if (o->port < 1 || o->port > 4) FAIL("gd.ui.screen: port is 1 to 4");

    on = atv_get(a, root, "on");
    if (atv_kind(a, on) == ATV_TABLE) {
        o->fn_accept = get_fn(a, on, "accept");
        o->fn_back = get_fn(a, on, "back");
        o->fn_focus = get_fn(a, on, "focus");
        o->fn_change = get_fn(a, on, "change");
        o->fn_open = get_fn(a, on, "open");
        o->fn_close = get_fn(a, on, "close");
        alt = atv_get(a, on, "alt");
        o->fn_alt[0] = get_fn(a, alt, "X");
        o->fn_alt[1] = get_fn(a, alt, "Y");
        o->fn_alt[2] = get_fn(a, alt, "Z");
    }
    return 1;
}

int at_explainer_from_val(const AtvArena *a, int t, AtExplainer *e, char *err, int errcap)
{
    int media, with, from, i, n;
    memset(e, 0, sizeof *e);
    e->media_model = e->media_ring = AT_NO_MODEL;
    (void) err; (void) errcap;
    if (atv_kind(a, t) != ATV_TABLE) return 1;
    e->has = 1;
    get_str(a, t, "kicker", e->kicker, AT_STR, &e->warn);
    get_str(a, t, "title", e->title, AT_STR, &e->warn);
    get_str(a, t, "what", e->what, AT_TEXT, &e->warn);
    media = atv_get(a, t, "media");
    if (atv_kind(a, media) == ATV_TABLE) {
        e->media_model = get_int(a, media, "model", AT_NO_MODEL);
        e->media_ring = get_int(a, media, "ring", AT_NO_MODEL);
    }
    with = atv_get(a, t, "with");
    n = atv_len(a, with);
    for (i = 0; i < n && e->n_with < AT_MAX_WITH; i++) {
        int w = atv_at(a, with, i + 1);
        e->with_model[e->n_with++] = atv_kind(a, w) == ATV_TABLE ? get_int(a, w, "model", AT_NO_MODEL) : (int) atv_numv(a, w, AT_NO_MODEL);
    }
    from = atv_get(a, t, "from");
    if (atv_kind(a, from) == ATV_TABLE) get_str(a, from, "text", e->from_text, AT_STR, &e->warn);
    return 1;
}

int at_screen_fn_refs(const AtScreen *s, int *out, int cap)
{
    int n = 0, i;
    int all[16];
    int na = 0;
    all[na++] = s->fn_provide; all[na++] = s->fn_accept; all[na++] = s->fn_back; all[na++] = s->fn_focus;
    all[na++] = s->fn_change; all[na++] = s->fn_open; all[na++] = s->fn_close; all[na++] = s->fn_counter;
    all[na++] = s->fn_alt[0]; all[na++] = s->fn_alt[1]; all[na++] = s->fn_alt[2];
    for (i = 0; i < na; i++) if (all[i] >= 0 && n < cap) out[n++] = all[i];
    for (i = 0; i < s->n_keys; i++) {
        if (s->keys[i].fn_label >= 0 && n < cap) out[n++] = s->keys[i].fn_label;
        if (s->keys[i].fn_when >= 0 && n < cap) out[n++] = s->keys[i].fn_when;
    }
    return n;
}

int at_screen_focus_blocks(const AtScreen *s, AtFocusBlock *fb)
{
    int b, row = 0;
    if (s->primary == AT_PRIMARY_LIST) {
        fb[0].col0 = 0; fb[0].row0 = 0; fb[0].cols = 1; fb[0].n = s->n_items; fb[0].exists = NULL;
        return 1;
    }
    for (b = 0; b < s->n_blocks; b++) {
        fb[b].col0 = 0; fb[b].row0 = row; fb[b].cols = s->blocks[b].cols > 0 ? s->blocks[b].cols : 1;
        fb[b].n = s->blocks[b].n; fb[b].exists = NULL;
        row += (fb[b].n + fb[b].cols - 1) / fb[b].cols;
    }
    return s->n_blocks;
}

const char *at_screen_block_id(const AtScreen *s, int block)
{
    if (s->primary == AT_PRIMARY_LIST) return block == 0 ? "list" : NULL;
    return (block >= 0 && block < s->n_blocks) ? s->blocks[block].id : NULL;
}

const char *at_screen_cell_id(const AtScreen *s, AtFocusPos p)
{
    if (s->primary == AT_PRIMARY_LIST) return (p.block == 0 && p.index >= 0 && p.index < s->n_items) ? s->items[p.index].id : NULL;
    if (p.block < 0 || p.block >= s->n_blocks || p.index < 0 || p.index >= s->blocks[p.block].n) return NULL;
    return s->blocks[p.block].cells[p.index].id;
}

AtFocusPos at_screen_refocus(const AtScreen *s, const char *block_id, const char *cell_id, AtFocusPos old)
{
    AtFocusBlock fb[AT_MAX_BLOCKS];
    int nb = at_screen_focus_blocks(s, fb), b, i;
    AtFocusPos p = { -1, -1 };
    if (s->primary == AT_PRIMARY_LIST) {
        for (i = 0; cell_id != NULL && i < s->n_items; i++) if (strcmp(s->items[i].id, cell_id) == 0) { p.block = 0; p.index = i; return p; }
        if (s->n_items > 0) { p.block = 0; p.index = old.index < 0 ? 0 : (old.index >= s->n_items ? s->n_items - 1 : old.index); }
        return p;
    }
    for (b = 0; block_id != NULL && cell_id != NULL && b < s->n_blocks; b++) {
        if (strcmp(s->blocks[b].id, block_id) != 0) continue;
        for (i = 0; i < s->blocks[b].n; i++) if (strcmp(s->blocks[b].cells[i].id, cell_id) == 0) { p.block = b; p.index = i; return p; }
    }
    for (b = 0; block_id != NULL && b < s->n_blocks; b++) {          /* the cell is gone: the same block, the same place, clamped */
        if (strcmp(s->blocks[b].id, block_id) != 0 || s->blocks[b].n < 1) continue;
        p.block = b;
        p.index = old.index < 0 ? 0 : (old.index >= s->blocks[b].n ? s->blocks[b].n - 1 : old.index);
        return p;
    }
    return at_focus_first(fb, nb);
}

int at_cell_accepts(const AtScreen *s, AtFocusPos p)
{
    if (at_screen_cell_id(s, p) == NULL) return 0;
    if (s->primary == AT_PRIMARY_LIST) return !(s->items[p.index].flags & AT_CELL_DISABLED);
    return !(s->blocks[p.block].cells[p.index].flags & AT_CELL_DISABLED);
}

int at_screen_wants_pad(const AtScreen *s) { return !s->input_feed; }
```

- [ ] **Step 4: Run the tests.**

```bash
nt atlas-screen
```

Expected: `atlas screen: 66 checks, 0 failed`. Likely first-run compile issues are typos in the test's `bag()` builder; the checks themselves encode the contract above, so fix code or builder, not the contract. One check to read carefully: the 13-cell-block error test relies on `cols = 20` exceeding `AT_MAX_CELLS` (12) and the message containing `cols`.

- [ ] **Step 5: Commit.** Game repo: the five new source files and the test, message `atlas: screen record, value tree, conversion, validation, refocus`. Workspace repo: `tools/port/native_test.sh`, message `atlas: atlas-screen native test case`.

---

### Task 6: The screen stack and the tween

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_stack.h`, `gw_ui_stack.c`, `melee/pc/tests/atlas_stack_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-stack`)

**Interfaces:**
Consumes: `AtFocusPos` (Task 3).
Produces:

```c
#define AT_STACK_MAX 8
typedef struct { int screen; AtFocusPos focus; int scroll; } AtStackEntry;
typedef struct { AtStackEntry e[AT_STACK_MAX]; int n; } AtStack;
int at_stack_push(AtStack *s, int screen);        /* 1 pushed; 0 when full or already on top */
int at_stack_pop(AtStack *s);                      /* the popped screen, -1 when empty */
int at_stack_remove(AtStack *s, int screen);       /* 1 removed (anywhere in the stack) */
int at_stack_top(const AtStack *s);                /* the top screen, -1 when empty */
AtStackEntry *at_stack_top_entry(AtStack *s);      /* NULL when empty; the caller saves focus and scroll here */
typedef struct { double t0, dur; } AtTween;
void at_tween_start(AtTween *t, double now_ms, double dur_ms, int reduced);   /* reduced: a cut */
float at_tween_value(const AtTween *t, double now_ms);                        /* 0..1, ease-out cubic; 1 when dur <= 0 */
```

- [ ] **Step 1: Write the failing test.** Create `melee/pc/tests/atlas_stack_test.c`:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_stack.h"

int main(void)
{
    AtStack s; AtTween t; int i;
    memset(&s, 0, sizeof s);
    CHECK(at_stack_top(&s) == -1 && at_stack_pop(&s) == -1 && at_stack_top_entry(&s) == NULL);
    CHECK(at_stack_push(&s, 3) == 1 && at_stack_top(&s) == 3);
    CHECK(at_stack_push(&s, 3) == 0);                                   /* pushing the screen already on top does nothing */
    at_stack_top_entry(&s)->focus.block = 1; at_stack_top_entry(&s)->focus.index = 2; at_stack_top_entry(&s)->scroll = 4;
    CHECK(at_stack_push(&s, 5) == 1 && at_stack_top(&s) == 5);
    CHECK(at_stack_pop(&s) == 5 && at_stack_top(&s) == 3);
    CHECK(at_stack_top_entry(&s)->focus.block == 1 && at_stack_top_entry(&s)->focus.index == 2 && at_stack_top_entry(&s)->scroll == 4);   /* focus is remembered */
    at_stack_push(&s, 6); at_stack_push(&s, 7);
    CHECK(at_stack_remove(&s, 6) == 1 && s.n == 2 && at_stack_top(&s) == 7);   /* removal from the middle keeps the order */
    CHECK(at_stack_remove(&s, 99) == 0);
    for (i = 10; i < 20; i++) at_stack_push(&s, i);
    CHECK(s.n == AT_STACK_MAX);                                         /* full: a push is refused, nothing is lost */
    CHECK(at_stack_push(&s, 50) == 0 && at_stack_top(&s) == 15);   /* 3 and 7, then 10 to 15, fill the eight places */

    at_tween_start(&t, 1000.0, 100.0, 0);
    CHECK_NEAR(at_tween_value(&t, 1000.0), 0.0);
    CHECK_NEAR(at_tween_value(&t, 1050.0), 0.875);                      /* ease-out cubic: 1 - (1 - 0.5)^3 */
    CHECK_NEAR(at_tween_value(&t, 1100.0), 1.0);
    CHECK_NEAR(at_tween_value(&t, 5000.0), 1.0);
    CHECK_NEAR(at_tween_value(&t, 900.0), 0.0);                         /* before the start: not started */
    at_tween_start(&t, 1000.0, 100.0, 1);                               /* Reduced motion: an immediate cut */
    CHECK_NEAR(at_tween_value(&t, 1000.0), 1.0);
    at_tween_start(&t, 1000.0, 0.0, 0);
    CHECK_NEAR(at_tween_value(&t, 1000.0), 1.0);
    ATLAS_DONE("atlas stack");
}
```

Register: `atlas-stack) sources=(pc/tests/atlas_stack_test.c pc/platform/gw_ui_stack.c) ;;` and add `, atlas-stack` to the die message.

- [ ] **Step 2: Run it to verify it fails.**

```bash
nt atlas-stack
```

Expected: `error: native test source missing: pc/platform/gw_ui_stack.c`.

- [ ] **Step 3: Write the minimal implementation.** Create `melee/pc/platform/gw_ui_stack.h`:

```c
/* gw_ui_stack.h - the Atlas screen stack and the tween. Pure C. */
#ifndef GW_UI_STACK_H
#define GW_UI_STACK_H
#include "gw_ui_focus.h"
#ifdef __cplusplus
extern "C" {
#endif

#define AT_STACK_MAX 8
typedef struct { int screen; AtFocusPos focus; int scroll; } AtStackEntry;
typedef struct { AtStackEntry e[AT_STACK_MAX]; int n; } AtStack;

int at_stack_push(AtStack *s, int screen);        /* 1 pushed; 0 when full or already on top */
int at_stack_pop(AtStack *s);                      /* the popped screen, -1 when empty */
int at_stack_remove(AtStack *s, int screen);       /* 1 removed (from anywhere in the stack) */
int at_stack_top(const AtStack *s);                /* the top screen, -1 when empty */
AtStackEntry *at_stack_top_entry(AtStack *s);      /* NULL when empty; the caller saves focus and scroll here */

typedef struct { double t0, dur; } AtTween;
void at_tween_start(AtTween *t, double now_ms, double dur_ms, int reduced);   /* reduced: a cut */
float at_tween_value(const AtTween *t, double now_ms);                        /* 0..1, ease-out cubic; 1 when dur <= 0 */

#ifdef __cplusplus
}
#endif
#endif
```

Create `melee/pc/platform/gw_ui_stack.c`:

```c
#include "gw_ui_stack.h"

#include <stddef.h>

int at_stack_push(AtStack *s, int screen)
{
    if (s->n >= AT_STACK_MAX || (s->n > 0 && s->e[s->n - 1].screen == screen)) return 0;
    s->e[s->n].screen = screen;
    s->e[s->n].focus.block = s->e[s->n].focus.index = -1;
    s->e[s->n].scroll = 0;
    s->n++;
    return 1;
}

int at_stack_pop(AtStack *s) { return s->n > 0 ? s->e[--s->n].screen : -1; }

int at_stack_remove(AtStack *s, int screen)
{
    int i, j;
    for (i = 0; i < s->n; i++) {
        if (s->e[i].screen != screen) continue;
        for (j = i; j + 1 < s->n; j++) s->e[j] = s->e[j + 1];
        s->n--;
        return 1;
    }
    return 0;
}

int at_stack_top(const AtStack *s) { return s->n > 0 ? s->e[s->n - 1].screen : -1; }
AtStackEntry *at_stack_top_entry(AtStack *s) { return s->n > 0 ? &s->e[s->n - 1] : NULL; }

void at_tween_start(AtTween *t, double now, double dur, int reduced)
{
    t->t0 = now;
    t->dur = reduced ? 0.0 : dur;
}

float at_tween_value(const AtTween *t, double now)
{
    double p;
    if (t->dur <= 0.0) return 1.0f;
    p = (now - t->t0) / t->dur;
    if (p <= 0.0) return 0.0f;
    if (p >= 1.0) return 1.0f;
    return (float) (1.0 - (1.0 - p) * (1.0 - p) * (1.0 - p));
}
```

- [ ] **Step 4: Run the tests.**

```bash
nt atlas-stack
```

Expected: `atlas stack: 17 checks, 0 failed`.

- [ ] **Step 5: Commit.** Game repo: `pc/platform/gw_ui_stack.h`, `gw_ui_stack.c`, `pc/tests/atlas_stack_test.c`, message `atlas: screen stack and the tween`. Workspace repo: `tools/port/native_test.sh`, message `atlas: atlas-stack native test case`.

### Task 7: Parts, first half: plates, rows, value widgets, tabs, tags (against a recording sink)

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_parts.h`, `melee/pc/platform/gw_ui_parts.c`, `melee/pc/tests/atlas_rec.h`, `melee/pc/tests/atlas_parts_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-parts`)

**Interfaces:**
Consumes: `AtRect`, `AtTextOps`, `at_fit`, `at_role_size` (Task 2); `AtItem`, `AtCell`, `AtExplainer`, `AtFooter`, `AtDialog`, `AT_CELL_*`, `AT_VAL_*`, `AT_NO_MODEL` (Task 5); `gw_ui_tokens.h` (Task 1).
Produces (the header is complete now; Task 8 implements the second half of it):

```c
typedef struct AtSink {
    void *user;
    void (*poly)(void *u, const float x[4], const float y[4], unsigned rgba);                 /* a flat convex quad */
    void (*text)(void *u, float x, float base, const char *s, int role, unsigned rgba, int align, float max_w);
    void (*model)(void *u, int model, int ring, float x, float y, float w, float h, int focused, int dim);
} AtSink;
enum { AT_ALIGN_LEFT = 0, AT_ALIGN_CENTER = 1, AT_ALIGN_RIGHT = 2 };                         /* the same numbers as GW_KIT_ALIGN_* */
enum { AT_ST_REST, AT_ST_FOCUS, AT_ST_PRESS, AT_ST_DISABLED, AT_ST_SELECTED };
enum { AT_TAG_PLAIN, AT_TAG_JADE, AT_TAG_EMBER, AT_TAG_SUN, AT_TAG_ROSE };
enum { AT_NOTE_OK, AT_NOTE_WARN, AT_NOTE_ERR, AT_NOTE_INFO };
void  at_poly_rect(const AtSink *s, float x, float y, float w, float h, unsigned rgba);
void  at_disc(const AtSink *s, float cx, float cy, float r, unsigned rgba);                    /* an octagon, three quads */
int   at_plate_polys(AtRect r, float edge, float chamfer, float px[3][4], float py[3][4]);     /* the geometry, for tests: 3 quads */
void  at_plate(const AtSink *s, AtRect r, unsigned face, unsigned edge_rgba, float edge, float chamfer);
void  at_text(const AtSink *s, const AtTextOps *o, int role, const char *str, float x, float base, unsigned rgba, int align, float max_w);
void  at_part_row(const AtSink *s, const AtTextOps *o, AtRect r, const AtItem *it, int state);
void  at_part_tabs(const AtSink *s, const AtTextOps *o, AtRect r, const char *const *names, const int *counts, int n, int active, int focus_tab);
float at_part_tag(const AtSink *s, const AtTextOps *o, float x, float y, const char *text, int tone, float max_w);   /* returns its width */
/* Task 8: */
void  at_part_cell(const AtSink *s, const AtTextOps *o, AtRect r, const AtCell *c, int state, unsigned focus_rgba);
void  at_part_stone(const AtSink *s, const AtTextOps *o, AtRect r, const AtCell *c, int state, unsigned focus_rgba);
float at_part_hint(const AtSink *s, const AtTextOps *o, float x, float base, char btn, const char *label);        /* returns its advance */
float at_part_trail(const AtSink *s, const AtTextOps *o, AtRect r, const char *const *items, int n);
void  at_part_chapter(const AtSink *s, const AtTextOps *o, AtRect r, int active);
void  at_part_rail(const AtSink *s, const AtTextOps *o, AtRect r, int active);
void  at_part_explainer(const AtSink *s, const AtTextOps *o, AtRect r, const AtExplainer *e);
void  at_part_footer(const AtSink *s, const AtTextOps *o, AtRect r, const AtFooter *f);
void  at_part_note(const AtSink *s, const AtTextOps *o, AtRect r, const char *text, int kind, float remaining);   /* remaining 0..1 */
int   at_part_dialog(const AtSink *s, const AtTextOps *o, float canvas_w, const AtDialog *d, float rise, AtRect btn[2]);
```

Plate geometry (the spec's plate): a chamfer `c` on the top-left and bottom-right corners, a front edge `e` at the bottom; three convex quads (two for the face, one for the edge). Face: `(c,0) (w,0) (w,h-c) (w-c+e,h-e)` and `(c,0) (w-c+e,h-e) (0,h-e) (0,c)`; edge: `(0,h-e) (w-c+e,h-e) (w-c,h) (0,h)`. Their areas add up to `w*h - c*c`.

- [ ] **Step 1: Write the failing test.** Create `melee/pc/tests/atlas_rec.h` (the recording sink; Task 8 and 9 reuse it):

```c
/* A recording AtSink: every poly, text and model call is kept for the test to read. */
#ifndef ATLAS_REC_H
#define ATLAS_REC_H
#include <math.h>
#include <string.h>
#include "../platform/gw_ui_parts.h"

#define REC_POLYS 4096
typedef struct { float x[4], y[4]; unsigned rgba; } RecPoly;
typedef struct { float x, base; char s[160]; int role; unsigned rgba; int align; } RecText;
typedef struct { int model, ring; float x, y, w, h; int focused, dim; } RecModel;
typedef struct { RecPoly p[REC_POLYS]; int np; RecText t[512]; int nt; RecModel m[64]; int nm; } Rec;
static Rec REC;

static void rec_poly(void *u, const float x[4], const float y[4], unsigned c)
{
    Rec *r = (Rec *) u;
    if (r->np < REC_POLYS) { memcpy(r->p[r->np].x, x, sizeof r->p[0].x); memcpy(r->p[r->np].y, y, sizeof r->p[0].y); r->p[r->np].rgba = c; r->np++; }
}
static void rec_text(void *u, float x, float base, const char *s, int role, unsigned c, int align, float max_w)
{
    Rec *r = (Rec *) u;
    (void) max_w;
    if (r->nt < 512) { RecText *t = &r->t[r->nt++]; t->x = x; t->base = base; snprintf(t->s, sizeof t->s, "%s", s); t->role = role; t->rgba = c; t->align = align; }
}
static void rec_model(void *u, int model, int ring, float x, float y, float w, float h, int focused, int dim)
{
    Rec *r = (Rec *) u;
    if (r->nm < 64) { RecModel *m = &r->m[r->nm++]; m->model = model; m->ring = ring; m->x = x; m->y = y; m->w = w; m->h = h; m->focused = focused; m->dim = dim; }
}
static AtSink rec_sink(void)
{
    AtSink s;
    memset(&REC, 0, sizeof REC);
    s.user = &REC; s.poly = rec_poly; s.text = rec_text; s.model = rec_model;
    return s;
}
static float poly_area(const RecPoly *p)
{
    float a = 0.0f; int i;
    for (i = 0; i < 4; i++) { int j = (i + 1) % 4; a += p->x[i] * p->y[j] - p->x[j] * p->y[i]; }
    return (float) fabs(a) * 0.5f;
}
static float poly_minx(const RecPoly *p) { float m = p->x[0]; int i; for (i = 1; i < 4; i++) if (p->x[i] < m) m = p->x[i]; return m; }
static float poly_maxx(const RecPoly *p) { float m = p->x[0]; int i; for (i = 1; i < 4; i++) if (p->x[i] > m) m = p->x[i]; return m; }
static float poly_miny(const RecPoly *p) { float m = p->y[0]; int i; for (i = 1; i < 4; i++) if (p->y[i] < m) m = p->y[i]; return m; }
static float poly_maxy(const RecPoly *p) { float m = p->y[0]; int i; for (i = 1; i < 4; i++) if (p->y[i] > m) m = p->y[i]; return m; }
static int count_color(unsigned rgba) { int i, n = 0; for (i = 0; i < REC.np; i++) if (REC.p[i].rgba == rgba) n++; return n; }
static const RecText *find_text(const char *s) { int i; for (i = 0; i < REC.nt; i++) if (strcmp(REC.t[i].s, s) == 0) return &REC.t[i]; return NULL; }
static int texts_legible(void) { int i; for (i = 0; i < REC.nt; i++) if (at_role_size(REC.t[i].role) < 12) return 0; return 1; }
#endif
```

Create `melee/pc/tests/atlas_parts_test.c`:

```c
#include "atlas_check.h"
#include "atlas_fake.h"
#include "atlas_rec.h"
#include "../platform/gw_ui_tokens.h"

static void plates(void)
{
    float px[3][4], py[3][4];
    int i, k;
    float total = 0.0f, edge_h;
    AtRect r = { 10.0f, 20.0f, 100.0f, 40.0f };
    CHECK(at_plate_polys(r, 3.0f, 8.0f, px, py) == 3);
    for (i = 0; i < 3; i++) { RecPoly p; for (k = 0; k < 4; k++) { p.x[k] = px[i][k]; p.y[k] = py[i][k]; } total += poly_area(&p); }
    CHECK_NEAR(total, 100.0f * 40.0f - 8.0f * 8.0f);                      /* the silhouette: a rectangle less two chamfer triangles */
    { RecPoly p; for (k = 0; k < 4; k++) { p.x[k] = px[2][k]; p.y[k] = py[2][k]; } edge_h = poly_maxy(&p) - poly_miny(&p); }
    CHECK_NEAR(edge_h, 3.0f);                                              /* the front edge is exactly its thickness */
    CHECK(at_plate_polys(r, 9.0f, 8.0f, px, py) == 3);                     /* an edge never outgrows the chamfer */
    { AtSink s = rec_sink(); at_plate(&s, r, AT_C_PLATE, AT_C_EDGE, 3.0f, 8.0f); CHECK(REC.np == 3); CHECK(REC.p[2].rgba == AT_C_EDGE && REC.p[0].rgba == AT_C_PLATE); }
    { AtSink s = rec_sink(); at_plate(&s, r, AT_C_PLATE, AT_C_EDGE, 6.0f, 8.0f); CHECK_NEAR(poly_maxy(&REC.p[2]) - poly_miny(&REC.p[2]), 6.0f); }   /* modal */
}

static AtItem item(const char *label, int vkind)
{
    AtItem it; memset(&it, 0, sizeof it);
    snprintf(it.label, sizeof it.label, "%s", label); it.vkind = vkind;
    return it;
}

static void rows(void)
{
    AtRect r = { 32.0f, 100.0f, 300.0f, 34.0f };
    AtItem it = item("Window", AT_VAL_NONE);
    AtSink s = rec_sink();
    int i; float top;
    at_part_row(&s, &FAKE, r, &it, AT_ST_REST);
    CHECK(count_color(AT_C_EMBER) == 0 && count_color(AT_C_LIFT) == 0);    /* rest: no focus cues */
    CHECK(REC.nt == 1 && REC.t[0].rgba == AT_C_TEXT2 && REC.t[0].role == AT_R_ROW16);
    CHECK(texts_legible());
    s = rec_sink();
    at_part_row(&s, &FAKE, r, &it, AT_ST_FOCUS);
    top = 1e9f; for (i = 0; i < REC.np; i++) if (poly_miny(&REC.p[i]) < top) top = poly_miny(&REC.p[i]);
    CHECK_NEAR(top, 98.0f);                                                /* lifted 2 px */
    CHECK(count_color(AT_C_LIFT) == 2 && count_color(AT_C_EMBER) == 2);    /* face, ember edge and the ember tick: three cues */
    CHECK(REC.t[0].rgba == AT_C_IVORY);
    s = rec_sink();
    at_part_row(&s, &FAKE, r, &it, AT_ST_PRESS);
    top = 1e9f; for (i = 0; i < REC.np; i++) if (poly_miny(&REC.p[i]) < top) top = poly_miny(&REC.p[i]);
    CHECK_NEAR(top, 101.0f); CHECK(count_color(AT_C_EMBER_D) >= 2);        /* pressed: drops 1 px, darker edge */
    s = rec_sink(); it.flags = AT_CELL_DISABLED;
    at_part_row(&s, &FAKE, r, &it, AT_ST_REST);
    CHECK(REC.t[0].rgba == AT_C_DIM && count_color(AT_C_EMBER) == 0);
    s = rec_sink(); it.flags = AT_CELL_SELECTED;
    at_part_row(&s, &FAKE, r, &it, AT_ST_REST);
    CHECK(count_color(AT_C_JADE) == 1);                                    /* selected: the jade bar */
}

static void values(void)
{
    AtRect r = { 32.0f, 100.0f, 300.0f, 34.0f };
    AtItem t = item("Sync", AT_VAL_TOGGLE), c = item("Mode", AT_VAL_CHOICE), sl = item("Vol", AT_VAL_SLIDER), tx = item("Code", AT_VAL_TEXT);
    AtSink s;
    t.on = 1;
    s = rec_sink(); at_part_row(&s, &FAKE, r, &t, AT_ST_REST);
    CHECK(find_text("OFF") != NULL && find_text("ON") != NULL && count_color(AT_C_JADE) == 1);   /* the lit half is jade and says ON */
    CHECK(find_text("ON")->rgba == AT_C_INK && find_text("OFF")->rgba == AT_C_DIM);
    t.on = 0; s = rec_sink(); at_part_row(&s, &FAKE, r, &t, AT_ST_REST);
    CHECK(count_color(AT_C_JADE) == 0 && find_text("OFF")->rgba == AT_C_IVORY);
    snprintf(c.text, sizeof c.text, "Window");
    s = rec_sink(); at_part_row(&s, &FAKE, r, &c, AT_ST_FOCUS);
    CHECK(find_text("Window") != NULL);
    CHECK(count_color(AT_C_EMBER) >= 4);                                   /* the arrows light up in focus */
    sl.vmin = 0; sl.vmax = 100; sl.vval = 50;
    s = rec_sink(); at_part_row(&s, &FAKE, r, &sl, AT_ST_REST);
    CHECK(REC.np >= 12);                                                   /* ticks */
    snprintf(tx.text, sizeof tx.text, "ABC-123");
    s = rec_sink(); at_part_row(&s, &FAKE, r, &tx, AT_ST_REST);
    CHECK(find_text("ABC-123") != NULL && find_text("ABC-123")->role == AT_R_NUM14 && find_text("ABC-123")->align == AT_ALIGN_RIGHT);
    CHECK_NEAR(find_text("ABC-123")->x, 32.0f + 300.0f - 12.0f);          /* right aligned, 12 px from the edge */
}

static void tabs_and_tags(void)
{
    AtRect r = { 32.0f, 70.0f, 300.0f, 30.0f };
    static const char *const names[3] = { "VIDEO", "AUDIO", "CONTROLS" };
    static const int counts[3] = { 5, 3, 12 };
    AtSink s = rec_sink();
    float w;
    at_part_tabs(&s, &FAKE, r, names, counts, 3, 1, -1);
    CHECK(find_text("VIDEO") && find_text("AUDIO") && find_text("CONTROLS") && find_text("12"));
    CHECK(find_text("AUDIO")->rgba == AT_C_IVORY && find_text("VIDEO")->rgba == AT_C_MUTED);     /* the active tab is the bright one */
    CHECK(texts_legible());
    s = rec_sink();
    w = at_part_tag(&s, &FAKE, 40.0f, 200.0f, "GENO", AT_TAG_JADE, 0.0f);
    CHECK_NEAR(w, fake_width(0, AT_R_CAP12, "GENO") + 16.0f);
    CHECK(count_color(AT_C_JADE_D) >= 1 && find_text("GENO")->rgba == AT_C_IVORY);
    s = rec_sink();
    w = at_part_tag(&s, &FAKE, 40.0f, 200.0f, "A VERY LONG ORIGIN TAG TEXT", AT_TAG_PLAIN, 60.0f);
    CHECK(w <= 60.0f + 0.01f);                                             /* a tag never outgrows its slot */
}

int main(void)
{
    plates(); rows(); values(); tabs_and_tags();
    ATLAS_DONE("atlas parts");
}
```

Register: `atlas-parts) sources=(pc/tests/atlas_parts_test.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c) ;;` and add `, atlas-parts` to the die message.

- [ ] **Step 2: Run it to verify it fails.**

```bash
nt atlas-parts
```

Expected: `error: native test source missing: pc/platform/gw_ui_parts.c`.

- [ ] **Step 3: Write the minimal implementation.** Create `melee/pc/platform/gw_ui_parts.h`:

```c
/* gw_ui_parts.h - the Atlas parts, drawn only through AtSink. Pure C. */
#ifndef GW_UI_PARTS_H
#define GW_UI_PARTS_H
#include "gw_ui_layout.h"
#include "gw_ui_screen.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct AtSink {
    void *user;
    void (*poly)(void *u, const float x[4], const float y[4], unsigned rgba);                 /* a flat convex quad */
    void (*text)(void *u, float x, float base, const char *s, int role, unsigned rgba, int align, float max_w);
    void (*model)(void *u, int model, int ring, float x, float y, float w, float h, int focused, int dim);
} AtSink;

enum { AT_ALIGN_LEFT = 0, AT_ALIGN_CENTER = 1, AT_ALIGN_RIGHT = 2 };   /* the same numbers as GW_KIT_ALIGN_* */
enum { AT_ST_REST, AT_ST_FOCUS, AT_ST_PRESS, AT_ST_DISABLED, AT_ST_SELECTED };
enum { AT_TAG_PLAIN, AT_TAG_JADE, AT_TAG_EMBER, AT_TAG_SUN, AT_TAG_ROSE };
enum { AT_NOTE_OK, AT_NOTE_WARN, AT_NOTE_ERR, AT_NOTE_INFO };

void  at_poly_rect(const AtSink *s, float x, float y, float w, float h, unsigned rgba);
void  at_disc(const AtSink *s, float cx, float cy, float r, unsigned rgba);                    /* an octagon, three quads */
int   at_plate_polys(AtRect r, float edge, float chamfer, float px[3][4], float py[3][4]);     /* the geometry, for tests: 3 quads */
void  at_plate(const AtSink *s, AtRect r, unsigned face, unsigned edge_rgba, float edge, float chamfer);
void  at_text(const AtSink *s, const AtTextOps *o, int role, const char *str, float x, float base, unsigned rgba, int align, float max_w);

void  at_part_row(const AtSink *s, const AtTextOps *o, AtRect r, const AtItem *it, int state);
void  at_part_tabs(const AtSink *s, const AtTextOps *o, AtRect r, const char *const *names, const int *counts, int n, int active, int focus_tab);
float at_part_tag(const AtSink *s, const AtTextOps *o, float x, float y, const char *text, int tone, float max_w);   /* returns its width */
void  at_part_cell(const AtSink *s, const AtTextOps *o, AtRect r, const AtCell *c, int state, unsigned focus_rgba);
void  at_part_stone(const AtSink *s, const AtTextOps *o, AtRect r, const AtCell *c, int state, unsigned focus_rgba);
float at_part_hint(const AtSink *s, const AtTextOps *o, float x, float base, char btn, const char *label);        /* returns its advance */
float at_part_trail(const AtSink *s, const AtTextOps *o, AtRect r, const char *const *items, int n);              /* returns the end x */
void  at_part_chapter(const AtSink *s, const AtTextOps *o, AtRect r, int active);
void  at_part_rail(const AtSink *s, const AtTextOps *o, AtRect r, int active);
void  at_part_explainer(const AtSink *s, const AtTextOps *o, AtRect r, const AtExplainer *e);
void  at_part_footer(const AtSink *s, const AtTextOps *o, AtRect r, const AtFooter *f);
void  at_part_note(const AtSink *s, const AtTextOps *o, AtRect r, const char *text, int kind, float remaining);   /* remaining 0..1 */
int   at_part_dialog(const AtSink *s, const AtTextOps *o, float canvas_w, const AtDialog *d, float rise, AtRect btn[2]);

#ifdef __cplusplus
}
#endif
#endif
```

Create `melee/pc/platform/gw_ui_parts.c` with the first half (Task 8 appends the rest to the same file):

```c
/* gw_ui_parts.c - the Atlas parts, drawn only through AtSink. Geometry follows the spec's style section
 * (tokens from gw_ui_tokens.h). Chamfers are two opposite corners; no curves; the circle is an octagon. */
#include "gw_ui_parts.h"
#include "gw_ui_tokens.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

/* tag tones that tokens.css does not carry (ATLAS/kit.css .tag.sun and .tag.rose backgrounds) */
#define AT_C_SUN_D 0x5E4A14FFu
#define AT_C_ROSE_D 0x5A1C30FFu

static void poly4(const AtSink *s, float x0, float y0, float x1, float y1, float x2, float y2, float x3, float y3, unsigned c)
{
    float px[4], py[4];
    px[0] = x0; px[1] = x1; px[2] = x2; px[3] = x3;
    py[0] = y0; py[1] = y1; py[2] = y2; py[3] = y3;
    s->poly(s->user, px, py, c);
}

void at_poly_rect(const AtSink *s, float x, float y, float w, float h, unsigned c)
{
    if ((c & 0xFFu) == 0 || w <= 0.0f || h <= 0.0f) return;
    poly4(s, x, y, x + w, y, x + w, y + h, x, y + h, c);
}

static void tri(const AtSink *s, float x0, float y0, float x1, float y1, float x2, float y2, unsigned c)
{
    poly4(s, x0, y0, x1, y1, x2, y2, x2, y2, c);
}

void at_disc(const AtSink *s, float cx, float cy, float r, unsigned c)
{
    float px[8], py[8];
    int k;
    for (k = 0; k < 8; k++) {
        double a = (22.5 + 45.0 * k) * 3.14159265358979 / 180.0;
        px[k] = cx + r * (float) cos(a);
        py[k] = cy + r * (float) sin(a);
    }
    poly4(s, px[0], py[0], px[1], py[1], px[2], py[2], px[3], py[3], c);
    poly4(s, px[0], py[0], px[3], py[3], px[4], py[4], px[5], py[5], c);
    poly4(s, px[0], py[0], px[5], py[5], px[6], py[6], px[7], py[7], c);
}

int at_plate_polys(AtRect r, float e, float c, float px[3][4], float py[3][4])
{
    float x = r.x, y = r.y, w = r.w, h = r.h;
    if (c < e) c = e;
    px[0][0] = x + c;         py[0][0] = y;
    px[0][1] = x + w;         py[0][1] = y;
    px[0][2] = x + w;         py[0][2] = y + h - c;
    px[0][3] = x + w - c + e; py[0][3] = y + h - e;
    px[1][0] = x + c;         py[1][0] = y;
    px[1][1] = x + w - c + e; py[1][1] = y + h - e;
    px[1][2] = x;             py[1][2] = y + h - e;
    px[1][3] = x;             py[1][3] = y + c;
    px[2][0] = x;             py[2][0] = y + h - e;
    px[2][1] = x + w - c + e; py[2][1] = y + h - e;
    px[2][2] = x + w - c;     py[2][2] = y + h;
    px[2][3] = x;             py[2][3] = y + h;
    return 3;
}

void at_plate(const AtSink *s, AtRect r, unsigned face, unsigned edge_rgba, float e, float c)
{
    float px[3][4], py[3][4];
    int i;
    at_plate_polys(r, e, c, px, py);
    for (i = 0; i < 3; i++) s->poly(s->user, px[i], py[i], i < 2 ? face : edge_rgba);
}

void at_text(const AtSink *s, const AtTextOps *o, int role, const char *str, float x, float base, unsigned rgba, int align, float max_w)
{
    char buf[200];
    int r;
    if (str == NULL || str[0] == '\0') return;
    r = at_fit(o, role, str, max_w, buf, sizeof buf);
    s->text(s->user, x, base, buf, r, rgba, align, 0.0f);
}

static float mid_base(float top, float h, int role) { return top + h * 0.5f + (float) at_role_size(role) * 0.35f; }
static float twidth(const AtTextOps *o, int role, const char *s) { return o->width(o->user, role, s); }

/* ---- small glyphs, all straight lines ------------------------------------------------------------- */
static void glyph_plus(const AtSink *s, float cx, float cy, float len, float th, unsigned c)
{
    at_poly_rect(s, cx - len * 0.5f, cy - th * 0.5f, len, th, c);
    at_poly_rect(s, cx - th * 0.5f, cy - len * 0.5f, th, len, c);
}
static void glyph_lock(const AtSink *s, float cx, float cy, unsigned c)
{
    at_poly_rect(s, cx - 6.0f, cy - 1.0f, 12.0f, 9.0f, c);               /* body */
    at_poly_rect(s, cx - 4.0f, cy - 7.0f, 2.0f, 6.0f, c);                /* shackle */
    at_poly_rect(s, cx + 2.0f, cy - 7.0f, 2.0f, 6.0f, c);
    at_poly_rect(s, cx - 4.0f, cy - 8.0f, 8.0f, 2.0f, c);
}
static void outline(const AtSink *s, AtRect r, float th, unsigned c)
{
    at_poly_rect(s, r.x, r.y, r.w, th, c);
    at_poly_rect(s, r.x, r.y + r.h - th, r.w, th, c);
    at_poly_rect(s, r.x, r.y + th, th, r.h - 2.0f * th, c);
    at_poly_rect(s, r.x + r.w - th, r.y + th, th, r.h - 2.0f * th, c);
}
static void brackets(const AtSink *s, AtRect r, unsigned c)             /* four registration brackets, 4 px outside the cell */
{
    float x0 = r.x - 4.0f, y0 = r.y - 4.0f, x1 = r.x + r.w + 4.0f, y1 = r.y + r.h + 4.0f;
    at_poly_rect(s, x0, y0, 9.0f, 2.0f, c);        at_poly_rect(s, x0, y0, 2.0f, 9.0f, c);
    at_poly_rect(s, x1 - 9.0f, y0, 9.0f, 2.0f, c); at_poly_rect(s, x1 - 2.0f, y0, 2.0f, 9.0f, c);
    at_poly_rect(s, x0, y1 - 2.0f, 9.0f, 2.0f, c); at_poly_rect(s, x0, y1 - 9.0f, 2.0f, 9.0f, c);
    at_poly_rect(s, x1 - 9.0f, y1 - 2.0f, 9.0f, 2.0f, c); at_poly_rect(s, x1 - 2.0f, y1 - 9.0f, 2.0f, 9.0f, c);
}

/* ---- value widgets: each draws ending at `right` and returns the width it used ---------------------- */
static float part_toggle(const AtSink *s, const AtTextOps *o, float right, float cy, int on)
{
    float w = 36.0f, h = 22.0f, x = right - 2.0f * w, y = cy - h * 0.5f;
    at_poly_rect(s, x, y, w, h, on ? AT_C_GROUND : AT_C_LINE2);
    at_poly_rect(s, x + w, y, w, h, on ? AT_C_JADE : AT_C_GROUND);
    at_text(s, o, AT_R_CAP12, "OFF", x + w * 0.5f, mid_base(y, h, AT_R_CAP12), on ? AT_C_DIM : AT_C_IVORY, AT_ALIGN_CENTER, 0.0f);
    at_text(s, o, AT_R_CAP12, "ON", x + w * 1.5f, mid_base(y, h, AT_R_CAP12), on ? AT_C_INK : AT_C_DIM, AT_ALIGN_CENTER, 0.0f);
    return 2.0f * w;
}

static float part_choice(const AtSink *s, const AtTextOps *o, float right, float cy, const char *text, int focus)
{
    float tw = twidth(o, AT_R_ROW16, text), mid = tw < 44.0f ? 44.0f : tw, total = 16.0f + 6.0f + mid + 6.0f + 16.0f, x = right - total;
    unsigned bg = focus ? AT_C_EMBER : AT_C_GROUND, fg = focus ? AT_C_INK : AT_C_MUTED;
    at_poly_rect(s, x, cy - 9.0f, 16.0f, 18.0f, bg);
    tri(s, x + 11.0f, cy - 4.0f, x + 5.0f, cy, x + 11.0f, cy + 4.0f, fg);
    at_text(s, o, AT_R_ROW16, text, x + 22.0f + mid * 0.5f, mid_base(cy - 9.0f, 18.0f, AT_R_ROW16), AT_C_IVORY, AT_ALIGN_CENTER, mid);
    at_poly_rect(s, right - 16.0f, cy - 9.0f, 16.0f, 18.0f, bg);
    tri(s, right - 11.0f, cy - 4.0f, right - 5.0f, cy, right - 11.0f, cy + 4.0f, fg);
    return total;
}

static float part_slider(const AtSink *s, float right, float cy, int vmin, int vmax, int vval, int focus)
{
    int i, k = vmax > vmin ? (vval - vmin) * 10 / (vmax - vmin) : 0;
    float x = right - 70.0f;
    if (k < 0) k = 0;
    if (k > 9) k = 9;
    for (i = 0; i < 10; i++) {
        float tx = x + 7.0f * (float) i;
        if (i == k) at_poly_rect(s, tx, cy - 10.0f, 6.0f, 20.0f, focus ? AT_C_EMBER : AT_C_IVORY);
        else at_poly_rect(s, tx, cy - (i < k ? 6.0f : 5.0f), 5.0f, i < k ? 12.0f : 10.0f, i < k ? AT_C_TEXT2 : AT_C_GROUND);
    }
    return 70.0f;
}

void at_part_row(const AtSink *s, const AtTextOps *o, AtRect r, const AtItem *it, int state)
{
    unsigned face = AT_C_PLATE2, edge = AT_C_EDGE2, txt = AT_C_TEXT2, val = AT_C_MUTED;
    float e = 3.0f, y = r.y, right, cy, vw = 0.0f, lx;
    int disabled = state == AT_ST_DISABLED || (it->flags & AT_CELL_DISABLED), focus = state == AT_ST_FOCUS && !disabled;
    AtRect pr;
    if (disabled) { face = AT_C_PLATE; txt = AT_C_DIM; val = AT_C_DIM; }
    else if (focus) { face = AT_C_LIFT; edge = AT_C_EMBER; txt = AT_C_IVORY; val = AT_C_IVORY; y -= 2.0f; }
    else if (state == AT_ST_PRESS) { face = AT_C_PLATE; edge = AT_C_EMBER_D; txt = AT_C_IVORY; e = 1.0f; y += 1.0f; }
    pr.x = r.x; pr.y = y; pr.w = r.w; pr.h = r.h;
    at_plate(s, pr, face, edge, e, (float) AT_PX_CH_S);
    if (focus) at_poly_rect(s, r.x, y, 4.0f, r.h - e, AT_C_EMBER);
    if (state == AT_ST_PRESS) at_poly_rect(s, r.x, y, 4.0f, r.h - e, AT_C_EMBER_D);
    if (it->flags & AT_CELL_SELECTED) at_poly_rect(s, r.x + r.w - 4.0f, y, 4.0f, r.h - e, AT_C_JADE);
    right = r.x + r.w - 12.0f - ((it->flags & AT_CELL_SELECTED) ? 6.0f : 0.0f);
    cy = y + (r.h - e) * 0.5f;
    switch (it->vkind) {
    case AT_VAL_TOGGLE: vw = part_toggle(s, o, right, cy, it->on); break;
    case AT_VAL_CHOICE: vw = part_choice(s, o, right, cy, it->text, focus); break;
    case AT_VAL_SLIDER: vw = part_slider(s, right, cy, it->vmin, it->vmax, it->vval, focus); break;
    case AT_VAL_TEXT:
    case AT_VAL_COUNTER:
        at_text(s, o, AT_R_NUM14, it->text, right, mid_base(y, r.h - e, AT_R_NUM14), val, AT_ALIGN_RIGHT, 0.0f);
        vw = twidth(o, AT_R_NUM14, it->text);
        break;
    default: break;
    }
    lx = r.x + 12.0f;
    if (it->sub[0] != '\0') {
        at_text(s, o, AT_R_ROW16, it->label, lx, y + 15.0f, txt, AT_ALIGN_LEFT, right - lx - vw - 8.0f);
        at_text(s, o, AT_R_BODY12, it->sub, lx, y + r.h - e - 4.0f, AT_C_MUTED, AT_ALIGN_LEFT, right - lx - vw - 8.0f);
    } else {
        at_text(s, o, AT_R_ROW16, it->label, lx, mid_base(y, r.h - e, AT_R_ROW16), txt, AT_ALIGN_LEFT, right - lx - vw - 8.0f);
    }
}

void at_part_tabs(const AtSink *s, const AtTextOps *o, AtRect r, const char *const *names, const int *counts, int n, int active, int focus_tab)
{
    float x = r.x, bottom = r.y + r.h;
    int i;
    for (i = 0; i < n; i++) {
        char num[16];
        float tw = twidth(o, AT_R_CAP16, names[i]), cw = 0.0f, w, h = i == active ? 30.0f : 26.0f, y = bottom - h;
        snprintf(num, sizeof num, "%d", counts != NULL ? counts[i] : 0);
        if (counts != NULL) cw = twidth(o, AT_R_NUM12, num) + 6.0f;
        w = tw + cw + 28.0f;
        at_poly_rect(s, x, y, w, h, i == active ? AT_C_PLATE : AT_C_GROUND2);
        at_text(s, o, AT_R_CAP16, names[i], x + 14.0f, mid_base(y, h, AT_R_CAP16), i == active ? AT_C_IVORY : AT_C_MUTED, AT_ALIGN_LEFT, 0.0f);
        if (counts != NULL) at_text(s, o, AT_R_NUM12, num, x + 14.0f + tw + 6.0f, mid_base(y, h, AT_R_NUM12), i == active ? AT_C_EMBER : AT_C_DIM, AT_ALIGN_LEFT, 0.0f);
        if (i == focus_tab) at_poly_rect(s, x, y, w, 2.0f, AT_C_EMBER);
        x += w + 2.0f;
    }
}

float at_part_tag(const AtSink *s, const AtTextOps *o, float x, float y, const char *text, int tone, float max_w)
{
    unsigned face = AT_C_GROUND, ink = AT_C_TEXT2;
    AtRect r;
    float tw = twidth(o, AT_R_CAP12, text), w = tw + 16.0f;
    if (tone == AT_TAG_JADE) { face = AT_C_JADE_D; ink = AT_C_IVORY; }
    else if (tone == AT_TAG_EMBER) { face = AT_C_EMBER; ink = AT_C_INK; }
    else if (tone == AT_TAG_SUN) { face = AT_C_SUN_D; ink = AT_C_SUN; }
    else if (tone == AT_TAG_ROSE) { face = AT_C_ROSE_D; ink = 0xFFB3C9FFu; }
    if (max_w > 0.0f && w > max_w) w = max_w;
    r.x = x; r.y = y; r.w = w; r.h = 20.0f;
    at_plate(s, r, face, face, 0.0f, (float) AT_PX_CH_S);
    at_text(s, o, AT_R_CAP12, text, x + 8.0f, mid_base(y, 20.0f, AT_R_CAP12), ink, AT_ALIGN_LEFT, w - 16.0f);
    return w;
}

/* <<< Task 8 appends the second half of the parts here >>> */
```

- [ ] **Step 4: Run the tests.** The second-half functions are declared in the header but not yet defined; that is fine because nothing calls them yet.

```bash
nt atlas-parts
```

Expected: `atlas parts: 31 checks, 0 failed`. Read each failing CHECK against the geometry paragraph; the row checks count polys by colour (a focused row has exactly two LIFT quads, the face's two halves, and two EMBER quads: the edge strip and the tick).

- [ ] **Step 5: Commit.** Game repo: `pc/platform/gw_ui_parts.h`, `gw_ui_parts.c`, `pc/tests/atlas_rec.h`, `pc/tests/atlas_parts_test.c`, message `atlas: parts, first half: plate, row, toggle, choice, slider, tabs, tag`. Workspace repo: `tools/port/native_test.sh`, message `atlas: atlas-parts native test case`.

---

### Task 8: Parts, second half: cells, stones, key hints, trail, chapter rail, explainer, footer, note, dialog

**Files:**
- Modify (game repo): `melee/pc/platform/gw_ui_parts.c` (replace the `<<< Task 8 ... >>>` marker comment with the code below), `melee/pc/tests/atlas_parts_test.c` (add the tests and call them from `main`)

**Interfaces:**
Consumes: everything Task 7 produced.
Produces: the definitions of the Task 8 functions declared in `gw_ui_parts.h` (signatures in Task 7).

- [ ] **Step 1: Write the failing tests.** Add to `melee/pc/tests/atlas_parts_test.c`, above `main`:

```c
static AtCell mk_cell(const char *name, int model, unsigned flags)
{
    AtCell c; memset(&c, 0, sizeof c);
    snprintf(c.id, sizeof c.id, "c"); snprintf(c.name, sizeof c.name, "%s", name);
    c.model = model; c.ring = AT_NO_MODEL; c.flags = flags;
    return c;
}

static void cells(void)
{
    AtRect r = { 100.0f, 100.0f, 56.0f, 56.0f };
    AtCell c = mk_cell("Kindling", 7, 0);
    AtSink s = rec_sink();
    int rest;
    c.ring = 9;
    at_part_cell(&s, &FAKE, r, &c, AT_ST_REST, 0);
    CHECK(REC.nm == 1 && REC.m[0].model == 7 && REC.m[0].ring == 9 && REC.m[0].focused == 0 && REC.m[0].dim == 0);
    CHECK(REC.m[0].x >= r.x && REC.m[0].x + REC.m[0].w <= r.x + r.w && REC.m[0].y >= r.y && REC.m[0].y + REC.m[0].h <= r.y + r.h);   /* the model stays inside the cell */
    rest = count_color(AT_C_EMBER);
    CHECK(rest == 0 && find_text("Kindling") == NULL);                      /* a cell with a model shows only the model */
    s = rec_sink();
    at_part_cell(&s, &FAKE, r, &c, AT_ST_FOCUS, 0);
    CHECK(REC.m[0].focused == 1);
    CHECK(count_color(AT_C_EMBER) >= 9);                                    /* the ember edge and eight bracket strips */
    s = rec_sink();
    at_part_cell(&s, &FAKE, r, &c, AT_ST_FOCUS, AT_C_P2);
    CHECK(count_color(AT_C_P2) == 8);                                       /* brackets take the focusing port's colour */
    c = mk_cell("Locked slot", AT_NO_MODEL, AT_CELL_LOCKED);
    s = rec_sink(); at_part_cell(&s, &FAKE, r, &c, AT_ST_REST, 0);
    CHECK(REC.nm == 0 && count_color(AT_C_DIM) >= 4);                       /* the lock glyph, no model, no name */
    c = mk_cell("Empty slot", AT_NO_MODEL, AT_CELL_EMPTY);
    s = rec_sink(); at_part_cell(&s, &FAKE, r, &c, AT_ST_REST, 0);
    CHECK(REC.nm == 0 && count_color(AT_C_LINE) == 4 && count_color(AT_C_LINE2) == 2);   /* an outline and a plus, no plate */
    c = mk_cell("Cell", 7, AT_CELL_MERGE);
    s = rec_sink(); at_part_cell(&s, &FAKE, r, &c, AT_ST_REST, 0);
    CHECK(find_text("+ MERGE") != NULL && count_color(AT_C_JADE) >= 1);
    c = mk_cell("Cell", 7, 0); c.pips = 3; c.origin = 'G'; c.index = 2;
    s = rec_sink(); at_part_cell(&s, &FAKE, r, &c, AT_ST_REST, 0);
    CHECK(find_text("G") != NULL && find_text("2") != NULL && count_color(AT_C_JADE) == 3 + 1 /* pips + origin mark */);
    c = mk_cell("Mr. Game & Watch", AT_NO_MODEL, 0);                        /* no model: the name, fitted into the cell */
    s = rec_sink(); at_part_cell(&s, &FAKE, r, &c, AT_ST_REST, 0);
    CHECK(REC.nt == 1 && REC.t[0].role == AT_R_BODY12 && REC.t[0].align == AT_ALIGN_CENTER);
    CHECK(texts_legible());
    c = mk_cell("Stone", AT_NO_MODEL, 0); c.letter = 'P'; c.rgba = 0xB872F0FFu;
    { AtRect sr = { 100.0f, 100.0f, 34.0f, 38.0f };
      s = rec_sink(); at_part_stone(&s, &FAKE, sr, &c, AT_ST_REST, 0);
      CHECK(find_text("P") != NULL && count_color(0xB872F0FFu) == 1);
      c.flags = AT_CELL_EMPTY; s = rec_sink(); at_part_stone(&s, &FAKE, sr, &c, AT_ST_REST, 0); CHECK(find_text("P") == NULL);
      c.flags = AT_CELL_LOCKED; s = rec_sink(); at_part_stone(&s, &FAKE, sr, &c, AT_ST_REST, 0); CHECK(count_color(AT_C_DIM) >= 4); }
}

static void hints_and_chrome(void)
{
    AtSink s = rec_sink();
    float adv;
    static const char *const trail3[3] = { "SOLO", "ENVOY", "YOUR DRIVES" };
    AtRect tr = { 32.0f, 22.0f, 480.0f, 30.0f };
    adv = at_part_hint(&s, &FAKE, 40.0f, 450.0f, 'A', "Merge into slot 1");
    CHECK(REC.np == 3 && REC.p[0].rgba == AT_C_PAD_A);                      /* the octagon disc */
    CHECK(find_text("Merge into slot 1") != NULL && find_text("A") != NULL);
    CHECK(adv > fake_width(0, AT_R_BODY14, "Merge into slot 1") + 18.0f);
    s = rec_sink(); at_part_hint(&s, &FAKE, 40.0f, 450.0f, 'B', "Close"); CHECK(REC.p[0].rgba == AT_C_PAD_B);
    s = rec_sink(); at_part_hint(&s, &FAKE, 40.0f, 450.0f, 'Z', "Bag"); CHECK(REC.p[0].rgba == AT_C_PAD_Z);
    s = rec_sink(); at_part_hint(&s, &FAKE, 40.0f, 450.0f, 'S', "Fight"); CHECK(find_text("START") != NULL);
    s = rec_sink(); at_part_hint(&s, &FAKE, 40.0f, 450.0f, 'M', "Move"); CHECK(REC.np == 2);   /* the d-pad cross */

    s = rec_sink();
    at_part_trail(&s, &FAKE, tr, trail3, 3);
    CHECK(find_text("YOUR DRIVES")->role == AT_R_CAP20 && find_text("YOUR DRIVES")->rgba == AT_C_IVORY);   /* here: bright and large */
    CHECK(find_text("SOLO")->role == AT_R_CAP16 && find_text("SOLO")->rgba == AT_C_MUTED);
    CHECK(count_color(AT_C_EMBER) >= 1);                                    /* the mark */
    s = rec_sink();
    tr.w = 150.0f;                                                          /* too narrow: the earliest parents drop out */
    at_part_trail(&s, &FAKE, tr, trail3, 3);
    CHECK(find_text("YOUR DRIVES") != NULL && find_text("SOLO") == NULL);
    s = rec_sink();
    at_part_chapter(&s, &FAKE, (AtRect){ 496.0f, 26.0f, 112.0f, 20.0f }, 2);
    CHECK(find_text("I") && find_text("II") && find_text("III") && find_text("IV") && find_text("V"));
    CHECK(count_color(AT_C_EMBER) == 1 && find_text("II")->rgba == AT_C_INK);
    s = rec_sink();
    at_part_rail(&s, &FAKE, (AtRect){ 32.0f, 66.0f, 104.0f, 362.0f }, 2);
    CHECK(find_text("SOLO") && find_text("VERSUS") && find_text("SETTINGS") && find_text("VERSUS")->rgba == AT_C_IVORY);
}

static void explainer_note_dialog(void)
{
    AtRect pane = { 448.0f, 66.0f, 160.0f, 362.0f };
    AtExplainer e;
    AtSink s;
    int i;
    memset(&e, 0, sizeof e);
    e.has = 1; e.media_model = 5; e.media_ring = 6;
    snprintf(e.kicker, sizeof e.kicker, "BAG CELL 1"); snprintf(e.title, sizeof e.title, "KINDLING");
    snprintf(e.what, sizeof e.what, "Your hits set the target Burning for 3 s.");
    e.n_with = 2; e.with_model[0] = 8; e.with_model[1] = 9; snprintf(e.from_text, sizeof e.from_text, "Depth 0, Fire");
    s = rec_sink();
    at_part_explainer(&s, &FAKE, pane, &e);
    CHECK(find_text("BAG CELL 1")->role == AT_R_CAP14 && find_text("BAG CELL 1")->rgba == AT_C_JADE);   /* WHAT: kicker, title, one rule */
    CHECK(find_text("KINDLING")->role == AT_R_TITLE);
    CHECK(find_text("target Burning for") != NULL);                         /* wrapped inside the 136 px inner width */
    CHECK(find_text("WITH") != NULL && find_text("FROM") != NULL && find_text("Depth 0, Fire") != NULL);
    CHECK(REC.nm == 3);                                                     /* the big media model and two WITH cells */
    for (i = 0; i < REC.nt; i++) CHECK(REC.t[i].base <= pane.y + pane.h && REC.t[i].x >= pane.x);
    CHECK(texts_legible());
    {                                                                       /* a long unbroken rule: clamped, still inside the pane */
        char big[400];
        memset(big, 'x', 150); big[150] = '\0';
        for (i = 0; i < 40; i++) strcat(big, " word");
        snprintf(e.what, sizeof e.what, "%s", big);
    }
    s = rec_sink(); at_part_explainer(&s, &FAKE, pane, &e);
    for (i = 0; i < REC.nt; i++) CHECK(REC.t[i].base <= pane.y + pane.h - 12.0f + 0.01f);
    e.has = 0; s = rec_sink(); at_part_explainer(&s, &FAKE, pane, &e);
    CHECK(REC.np == 3 && REC.nt == 0);                                      /* nothing to explain: an empty plate */

    s = rec_sink();
    at_part_note(&s, &FAKE, (AtRect){ 300.0f, 22.0f, 300.0f, 30.0f }, "Merged! Kindling got stronger.", AT_NOTE_OK, 0.5f);
    CHECK(count_color(AT_C_JADE) >= 2 && find_text("Merged! Kindling got stronger.")->role == AT_R_BODY14);   /* icon square and the timer line */
    s = rec_sink();
    at_part_note(&s, &FAKE, (AtRect){ 300.0f, 22.0f, 200.0f, 30.0f }, "Careful", AT_NOTE_WARN, 1.0f);
    CHECK(count_color(AT_C_SUN) >= 1);

    { AtDialog d; AtRect b[2]; int n;
      memset(&d, 0, sizeof d);
      d.open = 1; snprintf(d.title, sizeof d.title, "DISCARD DRIVE?"); snprintf(d.body, sizeof d.body, "This drive is gone for good.");
      d.n = 2; d.btn[0] = 'A'; snprintf(d.label[0], 24, "Discard"); d.btn[1] = 'B'; snprintf(d.label[1], 24, "Cancel"); d.focus = 1;
      s = rec_sink();
      n = at_part_dialog(&s, &FAKE, 640.0f, &d, 0.0f, b);
      CHECK(n == 2);
      CHECK(REC.p[0].rgba == AT_C_SCRIM && poly_minx(&REC.p[0]) == 0.0f && poly_maxx(&REC.p[0]) == 640.0f && poly_maxy(&REC.p[0]) == 480.0f);   /* the scrim covers the canvas */
      CHECK(find_text("DISCARD DRIVE?") != NULL && find_text("Discard") != NULL && find_text("Cancel") != NULL);
      CHECK(b[0].x >= 150.0f && b[1].x + b[1].w <= 640.0f - 150.0f && b[0].x + b[0].w <= b[1].x);   /* buttons inside the 332 px plate, not overlapping */
      s = rec_sink(); n = at_part_dialog(&s, &FAKE, 1706.0f, &d, 0.0f, b);
      CHECK(b[0].x > 600.0f && b[1].x + b[1].w < 1100.0f);                   /* centred on a wide canvas */
    }
}
```

and in `main`, call `cells(); hints_and_chrome(); explainer_note_dialog();` before `ATLAS_DONE`.

- [ ] **Step 2: Run to verify it fails.**

```bash
nt atlas-parts
```

Expected: a linker failure naming the missing parts: `lld-link: error: undefined symbol: _at_part_cell` (and the others).

- [ ] **Step 3: Write the minimal implementation.** In `melee/pc/platform/gw_ui_parts.c` replace the line `/* <<< Task 8 appends the second half of the parts here >>> */` with:

```c
void at_part_cell(const AtSink *s, const AtTextOps *o, AtRect r, const AtCell *c, int state, unsigned focus_rgba)
{
    int focus = state == AT_ST_FOCUS, has_model = c->model != AT_NO_MODEL;
    float y = focus ? r.y - 2.0f : r.y;
    AtRect pr;
    pr.x = r.x; pr.y = y; pr.w = r.w; pr.h = r.h;
    if (c->flags & AT_CELL_EMPTY) {
        outline(s, pr, 1.0f, AT_C_LINE);
        glyph_plus(s, r.x + r.w * 0.5f, y + r.h * 0.5f, 14.0f, 2.0f, AT_C_LINE2);
    } else {
        unsigned face = (c->flags & AT_CELL_LOCKED) ? AT_C_PLATE : (focus ? AT_C_LIFT : (has_model ? AT_C_GROUND2 : AT_C_PLATE2));
        at_plate(s, pr, face, focus ? AT_C_EMBER : AT_C_EDGE2, 3.0f, (float) AT_PX_CH_XS);
        if (c->flags & AT_CELL_LOCKED) {
            glyph_lock(s, r.x + r.w * 0.5f, y + r.h * 0.5f, AT_C_DIM);
        } else if (has_model) {
            at_poly_rect(s, r.x + r.w * 0.18f, y + r.h * 0.77f, r.w * 0.64f, r.h * 0.12f, 0x00000073u);   /* the floor shadow */
            s->model(s->user, c->model, c->ring, r.x + 3.0f, y + 3.0f, r.w - 6.0f, r.h - 8.0f, focus, (c->flags & AT_CELL_DISABLED) ? 1 : 0);
        } else {
            at_text(s, o, AT_R_BODY12, c->name, r.x + r.w * 0.5f, y + r.h - 8.0f, AT_C_IVORY, AT_ALIGN_CENTER, r.w - 6.0f);
        }
        if (c->index > 0) {
            char num[12];
            snprintf(num, sizeof num, "%d", c->index);
            at_text(s, o, AT_R_NUM12, num, r.x + 4.0f, y + 13.0f, AT_C_DIM, AT_ALIGN_LEFT, 0.0f);
        }
        if (c->origin != 0) {
            char one[2];
            one[0] = c->origin; one[1] = '\0';
            at_poly_rect(s, r.x + r.w - 14.0f, y, 14.0f, 14.0f, c->origin == 'G' ? AT_C_JADE : AT_C_SUN);
            at_text(s, o, AT_R_CAP12, one, r.x + r.w - 7.0f, y + 11.0f, AT_C_INK, AT_ALIGN_CENTER, 0.0f);
        } else if (c->flags & AT_CELL_NEW) {
            at_poly_rect(s, r.x + r.w - 9.0f, y + 3.0f, 6.0f, 6.0f, AT_C_EMBER_D);
        }
        if (c->pips > 0) {
            int p;
            for (p = 0; p < c->pips; p++) at_poly_rect(s, r.x + r.w - 20.0f - 7.0f * (float) (c->pips - 1 - p), y + r.h - 12.0f, 5.0f, 5.0f, AT_C_JADE);
        }
        if (c->flags & (AT_CELL_MERGE | AT_CELL_SELECTED)) outline(s, pr, 2.0f, AT_C_JADE);
        if (c->flags & AT_CELL_MERGE) {
            at_poly_rect(s, r.x, y + r.h - 18.0f, r.w, 15.0f, AT_C_JADE);
            at_text(s, o, AT_R_CAP12, "+ MERGE", r.x + r.w * 0.5f, y + r.h - 7.0f, AT_C_INK, AT_ALIGN_CENTER, r.w - 4.0f);
        }
    }
    if (focus) brackets(s, pr, focus_rgba != 0 ? focus_rgba : AT_C_EMBER);
}

void at_part_stone(const AtSink *s, const AtTextOps *o, AtRect r, const AtCell *c, int state, unsigned focus_rgba)
{
    int focus = state == AT_ST_FOCUS;
    float y = focus ? r.y - 2.0f : r.y;
    AtRect pr;
    unsigned face = c->rgba != 0 ? c->rgba : AT_C_LINE2;
    char one[2];
    pr.x = r.x; pr.y = y; pr.w = r.w; pr.h = r.h;
    if (c->flags & AT_CELL_EMPTY) face = AT_C_GROUND;
    else if (c->flags & AT_CELL_LOCKED) face = AT_C_PLATE;
    poly4(s, r.x + r.w * 0.2f, y, r.x + r.w * 0.8f, y, r.x + r.w, y + r.h, r.x, y + r.h, face);     /* the arch stone */
    if (c->flags & AT_CELL_EMPTY) glyph_plus(s, r.x + r.w * 0.5f, y + r.h * 0.6f, 12.0f, 2.0f, AT_C_LINE2);
    else if (c->flags & AT_CELL_LOCKED) glyph_lock(s, r.x + r.w * 0.5f, y + r.h * 0.6f, AT_C_DIM);
    else if (c->letter != 0) {
        one[0] = c->letter; one[1] = '\0';
        at_text(s, o, AT_R_CAP20, one, r.x + r.w * 0.5f, y + r.h - 9.0f, AT_C_INK, AT_ALIGN_CENTER, 0.0f);
    }
    if (focus) brackets(s, pr, focus_rgba != 0 ? focus_rgba : AT_C_EMBER);
}

float at_part_hint(const AtSink *s, const AtTextOps *o, float x, float base, char btn, const char *label)
{
    float cy = base - 5.0f, gw = 18.0f, lw;
    char one[2];
    one[0] = btn; one[1] = '\0';
    if (btn == 'A' || btn == 'B' || btn == 'X' || btn == 'Y') {
        at_disc(s, x + 9.0f, cy, 9.0f, btn == 'A' ? AT_C_PAD_A : btn == 'B' ? AT_C_PAD_B : AT_C_PAD_X);
        at_text(s, o, AT_R_CAP12, one, x + 9.0f, mid_base(cy - 9.0f, 18.0f, AT_R_CAP12), btn == 'B' ? AT_C_IVORY : AT_C_INK, AT_ALIGN_CENTER, 0.0f);
    } else if (btn == 'Z') {
        gw = 20.0f;
        at_poly_rect(s, x, cy - 9.0f, gw, 18.0f, AT_C_PAD_Z);
        at_text(s, o, AT_R_CAP12, one, x + gw * 0.5f, mid_base(cy - 9.0f, 18.0f, AT_R_CAP12), AT_C_IVORY, AT_ALIGN_CENTER, 0.0f);
    } else if (btn == 'L' || btn == 'R') {
        gw = 22.0f;
        at_poly_rect(s, x, cy - 8.0f, gw, 16.0f, AT_C_MUTED);
        at_text(s, o, AT_R_CAP12, one, x + gw * 0.5f, mid_base(cy - 8.0f, 16.0f, AT_R_CAP12), AT_C_INK, AT_ALIGN_CENTER, 0.0f);
    } else if (btn == 'S') {
        gw = twidth(o, AT_R_CAP12, "START") + 14.0f;
        at_poly_rect(s, x, cy - 8.0f, gw, 16.0f, AT_C_MUTED);
        at_text(s, o, AT_R_CAP12, "START", x + gw * 0.5f, mid_base(cy - 8.0f, 16.0f, AT_R_CAP12), AT_C_INK, AT_ALIGN_CENTER, 0.0f);
    } else {                                                             /* 'M': the d-pad cross, for "Move" */
        at_poly_rect(s, x, cy - 3.0f, 18.0f, 6.0f, AT_C_TEXT2);
        at_poly_rect(s, x + 6.0f, cy - 9.0f, 6.0f, 18.0f, AT_C_TEXT2);
    }
    at_text(s, o, AT_R_BODY14, label, x + gw + 6.0f, base, AT_C_TEXT2, AT_ALIGN_LEFT, 0.0f);
    lw = twidth(o, AT_R_BODY14, label);
    return gw + 6.0f + lw + 18.0f;
}

float at_part_trail(const AtSink *s, const AtTextOps *o, AtRect r, const char *const *items, int n)
{
    float x = r.x, cy = r.y + r.h * 0.5f, sep = 18.0f, total = 0.0f, base = cy + 7.0f;
    int i, first = 0;
    poly4(s, x + 11.0f, cy - 11.0f, x + 22.0f, cy, x + 11.0f, cy + 11.0f, x, cy, AT_C_EMBER);        /* the mark: a diamond ring */
    poly4(s, x + 11.0f, cy - 6.0f, x + 17.0f, cy, x + 11.0f, cy + 6.0f, x + 5.0f, cy, AT_C_GROUND);
    x += 34.0f;
    for (i = 0; i < n; i++) total += twidth(o, i == n - 1 ? AT_R_CAP20 : AT_R_CAP16, items[i]) + (i > 0 ? sep : 0.0f);
    while (total > r.w - 34.0f && first < n - 1) {                       /* too wide: the earliest parents drop out */
        total -= twidth(o, AT_R_CAP16, items[first]) + (first + 1 < n ? sep : 0.0f);
        first++;
    }
    if (first > 0) {
        at_text(s, o, AT_R_CAP16, "\xE2\x80\xA6", x, base, AT_C_DIM, AT_ALIGN_LEFT, 0.0f);
        x += twidth(o, AT_R_CAP16, "\xE2\x80\xA6") + sep;
    }
    for (i = first; i < n; i++) {
        int here = i == n - 1, role = here ? AT_R_CAP20 : AT_R_CAP16;
        at_text(s, o, role, items[i], x, base, here ? AT_C_IVORY : AT_C_MUTED, AT_ALIGN_LEFT, r.x + r.w - x);
        x += twidth(o, role, items[i]);
        if (!here) {
            at_text(s, o, AT_R_CAP14, ">", x + sep * 0.5f, base, AT_C_DIM, AT_ALIGN_CENTER, 0.0f);
            x += sep;
        }
    }
    return x;
}

static const char *const ROMAN[5] = { "I", "II", "III", "IV", "V" };
static const char *const CHAPTER_NAME[5] = { "SOLO", "VERSUS", "ONLINE", "MODS", "SETTINGS" };

void at_part_chapter(const AtSink *s, const AtTextOps *o, AtRect r, int active)
{
    int i;
    for (i = 0; i < 5; i++) {
        float x = r.x + 23.0f * (float) i;
        int on = active == i + 1;
        at_poly_rect(s, x, r.y, 20.0f, 20.0f, on ? AT_C_EMBER : AT_C_GROUND2);
        at_text(s, o, AT_R_CAP12, ROMAN[i], x + 10.0f, mid_base(r.y, 20.0f, AT_R_CAP12), on ? AT_C_INK : AT_C_DIM, AT_ALIGN_CENTER, 0.0f);
    }
}

void at_part_rail(const AtSink *s, const AtTextOps *o, AtRect r, int active)
{
    int i;
    for (i = 0; i < 5; i++) {
        AtRect row;
        int on = active == i + 1;
        row.x = r.x; row.y = r.y + 34.0f * (float) i; row.w = r.w; row.h = 30.0f;
        if (on) at_plate(s, row, AT_C_PLATE, AT_C_EDGE, 3.0f, (float) AT_PX_CH_S);
        at_poly_rect(s, row.x + 8.0f, row.y + 5.0f, 20.0f, 20.0f, on ? AT_C_EMBER : AT_C_GROUND2);
        at_text(s, o, AT_R_CAP12, ROMAN[i], row.x + 18.0f, mid_base(row.y + 5.0f, 20.0f, AT_R_CAP12), on ? AT_C_INK : AT_C_DIM, AT_ALIGN_CENTER, 0.0f);
        at_text(s, o, AT_R_CAP14, CHAPTER_NAME[i], row.x + 36.0f, mid_base(row.y, 28.0f, AT_R_CAP14), on ? AT_C_IVORY : AT_C_DIM, AT_ALIGN_LEFT, r.w - 40.0f);
    }
}

void at_part_explainer(const AtSink *s, const AtTextOps *o, AtRect r, const AtExplainer *e)
{
    float x = r.x + 12.0f, w = r.w - 24.0f, y = r.y + 12.0f, bottom = r.y + r.h - 12.0f;
    char lines[5][96];
    int n, i, clamped = 0;
    at_plate(s, r, AT_C_PLATE, AT_C_EDGE, 3.0f, (float) AT_PX_CH);
    if (!e->has) return;
    at_poly_rect(s, x, y, w, 96.0f, AT_C_GROUND2);                       /* the media well */
    if (e->media_model != AT_NO_MODEL) s->model(s->user, e->media_model, e->media_ring, x + 8.0f, y + 4.0f, w - 16.0f, 88.0f, 1, 0);
    y += 106.0f;
    at_text(s, o, AT_R_CAP14, e->kicker, x, y + 11.0f, AT_C_JADE, AT_ALIGN_LEFT, w);
    y += 18.0f;
    at_text(s, o, AT_R_TITLE, e->title, x, y + 24.0f, AT_C_IVORY, AT_ALIGN_LEFT, w);
    y += 36.0f;
    n = at_wrap(o, AT_R_BODY14, e->what, w, 4, lines, &clamped);
    for (i = 0; i < n && y + 18.0f <= bottom; i++) {
        at_text(s, o, AT_R_BODY14, lines[i], x, y + 13.0f, AT_C_IVORY, AT_ALIGN_LEFT, 0.0f);
        y += 18.0f;
    }
    y += 8.0f;
    if (e->n_with > 0 && y + 44.0f <= bottom) {                          /* a label, then its content under it, so a narrow pane still fits */
        at_text(s, o, AT_R_CAP12, "WITH", x, y + 11.0f, AT_C_DIM, AT_ALIGN_LEFT, 0.0f);
        for (i = 0; i < e->n_with; i++) {
            float cx = x + 26.0f * (float) i;
            at_poly_rect(s, cx, y + 16.0f, 22.0f, 22.0f, AT_C_GROUND2);
            if (e->with_model[i] != AT_NO_MODEL) s->model(s->user, e->with_model[i], AT_NO_MODEL, cx + 1.0f, y + 17.0f, 20.0f, 20.0f, 0, 0);
        }
        y += 44.0f;
    }
    if (e->from_text[0] != '\0' && y + 40.0f <= bottom) {
        at_text(s, o, AT_R_CAP12, "FROM", x, y + 11.0f, AT_C_DIM, AT_ALIGN_LEFT, 0.0f);
        at_part_tag(s, o, x, y + 16.0f, e->from_text, AT_TAG_JADE, w);
    }
}

void at_part_footer(const AtSink *s, const AtTextOps *o, AtRect r, const AtFooter *f)
{
    float x = r.x + 14.0f, cy = r.y + r.h * 0.5f, mx;
    at_plate(s, r, AT_C_PLATE2, AT_C_EDGE2, 3.0f, (float) AT_PX_CH_S);
    at_text(s, o, AT_R_CAP14, f->label, x, mid_base(r.y, r.h - 3.0f, AT_R_CAP14), AT_C_MUTED, AT_ALIGN_LEFT, 76.0f);
    mx = x + 88.0f;
    if (f->model_a != AT_NO_MODEL) s->model(s->user, f->model_a, AT_NO_MODEL, mx, cy - 14.0f, 28.0f, 28.0f, 0, 0);
    glyph_plus(s, mx + 40.0f, cy, 8.0f, 2.0f, AT_C_MUTED);
    if (f->model_b != AT_NO_MODEL) s->model(s->user, f->model_b, AT_NO_MODEL, mx + 52.0f, cy - 14.0f, 28.0f, 28.0f, 1, 0);
    tri(s, mx + 90.0f, cy - 5.0f, mx + 100.0f, cy, mx + 90.0f, cy + 5.0f, AT_C_JADE);
    if (f->model_out != AT_NO_MODEL) s->model(s->user, f->model_out, AT_NO_MODEL, mx + 106.0f, cy - 14.0f, 28.0f, 28.0f, 0, 0);
    at_text(s, o, AT_R_BODY14, f->text, mx + 146.0f, mid_base(r.y, r.h - 3.0f, AT_R_BODY14), AT_C_TEXT2, AT_ALIGN_LEFT, r.x + r.w - mx - 146.0f - 10.0f);
}

void at_part_note(const AtSink *s, const AtTextOps *o, AtRect r, const char *text, int kind, float remaining)
{
    unsigned tone = kind == AT_NOTE_OK ? AT_C_JADE : kind == AT_NOTE_WARN ? AT_C_SUN : kind == AT_NOTE_ERR ? AT_C_ROSE : AT_C_LINE2;
    AtRect ic;
    at_plate(s, r, AT_C_PLATE, AT_C_EDGE, 3.0f, (float) AT_PX_CH_S);
    ic.x = r.x; ic.y = r.y; ic.w = 30.0f; ic.h = r.h - 3.0f;
    at_poly_rect(s, ic.x, ic.y, ic.w, ic.h, tone);
    glyph_plus(s, ic.x + 15.0f, ic.y + ic.h * 0.5f, 10.0f, 2.0f, AT_C_INK);
    at_text(s, o, AT_R_BODY14, text, r.x + 38.0f, mid_base(r.y, r.h - 3.0f, AT_R_BODY14), AT_C_IVORY, AT_ALIGN_LEFT, r.w - 46.0f);
    if (remaining < 0.0f) remaining = 0.0f;
    if (remaining > 1.0f) remaining = 1.0f;
    at_poly_rect(s, r.x, r.y + r.h - 5.0f, (r.w - 8.0f) * remaining, 2.0f, tone);                      /* the timer rule drains */
}

int at_part_dialog(const AtSink *s, const AtTextOps *o, float canvas_w, const AtDialog *d, float rise, AtRect btn[2])
{
    float w = 332.0f, pad = 16.0f, x, y, h, bx, by;
    char lines[5][96];
    int n, i, clamped = 0, nb = d->n > 2 ? 2 : d->n;
    at_poly_rect(s, 0.0f, 0.0f, canvas_w, 480.0f, AT_C_SCRIM);
    n = at_wrap(o, AT_R_BODY14, d->body, w - 2.0f * pad, 4, lines, &clamped);
    h = 14.0f + 24.0f + 6.0f + 18.0f * (float) n + 14.0f + 34.0f + 16.0f;
    x = (canvas_w - w) * 0.5f;
    y = (480.0f - h) * 0.5f + rise;
    {
        AtRect pr;
        pr.x = x; pr.y = y; pr.w = w; pr.h = h;
        at_plate(s, pr, AT_C_PLATE, AT_C_EDGE, 6.0f, (float) AT_PX_CH);
    }
    at_text(s, o, AT_R_CAP20, d->title, x + pad, y + 34.0f, AT_C_IVORY, AT_ALIGN_LEFT, w - 2.0f * pad);
    for (i = 0; i < n; i++) at_text(s, o, AT_R_BODY14, lines[i], x + pad, y + 57.0f + 18.0f * (float) i, AT_C_TEXT2, AT_ALIGN_LEFT, 0.0f);
    by = y + h - 16.0f - 34.0f;
    bx = x + w - pad;
    for (i = nb - 1; i >= 0; i--) {
        float tw = twidth(o, AT_R_CAP16, d->label[i]), bw = tw + 18.0f + 22.0f + 18.0f;
        int f = d->focus == i;
        AtRect br;
        bx -= bw;
        br.x = bx; br.y = by; br.w = bw; br.h = 34.0f;
        at_plate(s, br, f ? AT_C_EMBER : AT_C_PLATE2, f ? AT_C_EMBER_D : AT_C_EDGE2, 3.0f, (float) AT_PX_CH_S);
        at_disc(s, br.x + 18.0f, by + 15.0f, 7.0f, d->btn[i] == 'A' ? AT_C_PAD_A : d->btn[i] == 'B' ? AT_C_PAD_B : AT_C_PAD_X);
        at_text(s, o, AT_R_CAP16, d->label[i], br.x + 18.0f + 14.0f + 8.0f, mid_base(by, 31.0f, AT_R_CAP16), f ? AT_C_INK : AT_C_TEXT2, AT_ALIGN_LEFT, 0.0f);
        btn[i] = br;
        bx -= 8.0f;
    }
    return nb;
}
```

- [ ] **Step 4: Run the tests.**

```bash
nt atlas-parts
```

Expected: `atlas parts: 90 checks, 0 failed`. Two checks are order-sensitive and worth knowing when one fails: in the `Locked slot` test `count_color(AT_C_DIM) >= 4` counts the four lock rectangles (body, two shackle legs, top bar); in the `Empty slot` test the outline is exactly four `AT_C_LINE` rectangles and the plus exactly two `AT_C_LINE2` rectangles.

- [ ] **Step 5: Commit.** Game repo: `pc/platform/gw_ui_parts.c`, `pc/tests/atlas_parts_test.c`, message `atlas: parts, second half: cells, stones, key hints, trail, rail, explainer, footer, note, dialog`.

---

### Task 9: The screen renderer, hit rectangles and the budget

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_render.h`, `melee/pc/platform/gw_ui_render.c`, `melee/pc/tests/atlas_render_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-render`)

**Interfaces:**
Consumes: `at_layout`, `AtLayout`, `at_list_scroll` (Task 2); `AtScreen`, `AtView`, `AtBlock`, `AtCell` (Task 5); `AtHits`, `AtHit`, `AT_HIT_*`, `AT_MAX_HITS` (Task 4); every part (Tasks 7, 8); `AtTween`, `at_tween_start`, `at_tween_value` (Task 6).
Produces:

```c
#define AT_SCREEN_QUAD_CAP 4096
#define AT_SCREEN_QUAD_WARN 3000
void at_render(const AtScreen *sc, const AtView *v, float canvas_w, double now_ms, int reduced,
               const AtTextOps *o, const AtSink *s, AtHits *hits);
```

`at_render` draws, in order: ground, header (mark, trail, chapter dots or rail, rule), the primary plate with its blocks or rows, the explainer, the key hints and counter, the corner note, the dialog, and the open fade; it records one hit rectangle per cell or row (kind `AT_HIT_CELL`, `a` = block, `b` = index) and one per key hint (kind `AT_HIT_KEY`, `a` = the button char) and per dialog button. A grid's cell edge is `min(56, floor((inner_w - (maxcols-1)*8) / maxcols))`, at least 24; blocks are stacked with a 26 px header each; stone blocks use fixed 34x38 stones.

- [ ] **Step 1: Write the failing test.** Create `melee/pc/tests/atlas_render_test.c`:

```c
#include <stdlib.h>
#include "atlas_check.h"
#include "atlas_fake.h"
#include "atlas_rec.h"
#include "../platform/gw_ui_render.h"
#include "../platform/gw_ui_tokens.h"

static AtScreen SC;
static AtView V;
static AtHits HITS;

static void put_cell(AtBlock *b, const char *prefix, int i, const char *name, int model, unsigned flags)
{
    AtCell *c = &b->cells[b->n++];
    memset(c, 0, sizeof *c);
    snprintf(c->id, sizeof c->id, "%s:%d", prefix, i + 1);
    snprintf(c->name, sizeof c->name, "%s", name);
    c->model = model; c->ring = model >= 0 ? model + 50 : AT_NO_MODEL; c->flags = flags; c->index = i + 1;
}

static void bag_fixture(void)
{
    int i;
    AtBlock *b;
    memset(&SC, 0, sizeof SC);
    at_view_init(&V);
    snprintf(SC.id, sizeof SC.id, "envoy.bag"); snprintf(SC.title, sizeof SC.title, "YOUR DRIVES");
    snprintf(SC.parent[0], AT_STR, "SOLO"); snprintf(SC.parent[1], AT_STR, "ENVOY"); SC.n_parents = 2;
    SC.primary = AT_PRIMARY_GRID; SC.preset = AT_PRESET_NARROW; SC.chapter = 1; SC.n_blocks = 3;
    b = &SC.blocks[0]; snprintf(b->id, AT_ID, "eq"); snprintf(b->title, AT_STR, "EQUIPPED"); snprintf(b->count, 24, "5 / 6"); b->cols = 6;
    for (i = 0; i < 6; i++) put_cell(b, "eq", i, "Drive", i == 5 ? -1 : 100 + i, i == 5 ? AT_CELL_LOCKED : 0);
    b = &SC.blocks[1]; snprintf(b->id, AT_ID, "bag"); snprintf(b->title, AT_STR, "BAG"); snprintf(b->count, 24, "3 / 4"); b->cols = 4;
    for (i = 0; i < 4; i++) put_cell(b, "bag", i, "Drive", i == 3 ? -1 : 110 + i, i == 3 ? AT_CELL_EMPTY : (i == 0 ? AT_CELL_MERGE : 0));
    b = &SC.blocks[2]; snprintf(b->id, AT_ID, "key"); snprintf(b->title, AT_STR, "KEYSTONE"); snprintf(b->note, AT_STR, "One held"); b->cols = 6; b->stones = 1;
    for (i = 0; i < 3; i++) { put_cell(b, "key", i, "Keystone", -1, i == 2 ? AT_CELL_LOCKED : (i == 1 ? AT_CELL_EMPTY : 0)); b->cells[i].letter = 'P'; b->cells[i].rgba = 0xB872F0FFu; }
    SC.footer.has = 1; snprintf(SC.footer.label, 24, "IF YOU MERGE"); SC.footer.model_a = 1; SC.footer.model_b = 2; SC.footer.model_out = 3;
    snprintf(SC.footer.text, AT_STR, "Slot 1 Kindling gets stronger.");
    SC.n_keys = 4;
    SC.keys[0].btn = 'A'; snprintf(SC.keys[0].label, AT_STR, "Merge into slot 1"); V.key_shown[0] = 1; snprintf(V.key_label[0], AT_STR, "Merge into slot 1");
    SC.keys[1].btn = 'X'; V.key_shown[1] = 1; snprintf(V.key_label[1], AT_STR, "Discard");
    SC.keys[2].btn = 'Y'; V.key_shown[2] = 1; snprintf(V.key_label[2], AT_STR, "More");
    SC.keys[3].btn = 'B'; V.key_shown[3] = 1; snprintf(V.key_label[3], AT_STR, "Close");
    snprintf(V.counter, AT_STR, "Bag 1 / 4");
    V.ex.has = 1; V.ex.media_model = 100; V.ex.media_ring = 150; snprintf(V.ex.kicker, AT_STR, "BAG CELL 1"); snprintf(V.ex.title, AT_STR, "KINDLING");
    snprintf(V.ex.what, AT_TEXT, "Your hits set the target Burning for 3 s."); V.ex.n_with = 2; V.ex.with_model[0] = 101; V.ex.with_model[1] = 102;
    snprintf(V.ex.from_text, AT_STR, "Depth 0, Fire");
    V.focus.block = 1; V.focus.index = 0; V.opened_ms = 0.0;
}

static int estimate_quads(void)           /* a glyph is a quad; a model about 150 triangles (the drives are 24 to 146) */
{
    int i, n = REC.np;
    for (i = 0; i < REC.nt; i++) n += (int) strlen(REC.t[i].s);
    return n + REC.nm * 150;
}

static void budget_and_legibility(void)
{
    AtSink s = rec_sink();
    int i;
    bag_fixture();
    at_render(&SC, &V, 640.0f, 10000.0, 0, &FAKE, &s, &HITS);
    CHECK(REC.np > 60 && REC.np < 400);                                     /* the parts of one screen: well under the cap */
    CHECK(estimate_quads() <= AT_SCREEN_QUAD_WARN);                         /* typical bag, models included, under the warning line */
    CHECK(texts_legible());                                                  /* no text under 12 px, anywhere */
    for (i = 0; i < REC.nt; i++) CHECK(REC.t[i].x >= 0.0f && REC.t[i].x <= 640.0f && REC.t[i].base >= 0.0f && REC.t[i].base <= 480.0f);
    CHECK(REC.p[0].rgba == AT_C_GROUND && poly_maxx(&REC.p[0]) == 640.0f);   /* the ground comes first */
    CHECK(find_text("YOUR DRIVES") != NULL && find_text("SOLO") != NULL && find_text("ENVOY") != NULL);
    CHECK(find_text("EQUIPPED") && find_text("BAG") && find_text("KEYSTONE") && find_text("5 / 6") && find_text("One held"));
    CHECK(find_text("Bag 1 / 4")->align == AT_ALIGN_RIGHT && find_text("Close") && find_text("Move"));
    CHECK(find_text("IF YOU MERGE") != NULL && find_text("KINDLING") != NULL);
    CHECK(REC.nm >= 12 && REC.nm <= 20);                                     /* nine bodies, the merge preview and the explainer */
}

static void focus_cues(void)
{
    AtSink s = rec_sink();
    int with, without;
    bag_fixture();
    V.focus.block = -1; V.focus.index = -1;
    at_render(&SC, &V, 640.0f, 10000.0, 0, &FAKE, &s, &HITS);
    without = count_color(AT_C_EMBER);
    s = rec_sink(); bag_fixture();
    at_render(&SC, &V, 640.0f, 10000.0, 0, &FAKE, &s, &HITS);
    with = count_color(AT_C_EMBER);
    CHECK(with - without >= 9);                                              /* the ember edge and the eight bracket strips */
}

static void long_strings(void)
{
    AtSink s = rec_sink();
    AtLayout L;
    int i;
    bag_fixture();
    snprintf(V.ex.title, AT_STR, "BURNING RED DRIVE OF THE MAGNIFICENT UPDRAFT AND ALL");
    snprintf(V.ex.what, AT_TEXT, "Aerial hits set the target Burning for 3 s. Burning targets take 10 percent more damage. Your jumps are refunded.");
    snprintf(V.ex.from_text, AT_STR, "Depth 12, Fire, Updraft, Reprisal, Echoes");
    snprintf(SC.blocks[0].title, AT_STR, "EQUIPPED DRIVES WITH A VERY LONG TITLE");
    at_render(&SC, &V, 640.0f, 10000.0, 0, &FAKE, &s, &HITS);
    at_layout(640.0f, AT_PRESET_NARROW, &L);
    CHECK(texts_legible());
    for (i = 0; i < REC.nt; i++) {
        const RecText *t = &REC.t[i];
        float w = fake_width(0, t->role, t->s);
        if (t->x >= L.explainer.x && t->base > L.explainer.y && t->base < L.explainer.y + L.explainer.h && t->align == AT_ALIGN_LEFT) {
            CHECK(t->x + w <= L.explainer.x + L.explainer.w - 12.0f + 0.01f);   /* inside the 160 px pane, 12 px padding */
            CHECK(t->base <= L.explainer.y + L.explainer.h - 12.0f + 0.01f);
        }
    }
}

static void hits_at_widths(void)
{
    static const float widths[3] = { 640.0f, 853.3333f, 1706.6667f };
    int w, i, j, cells, keys;
    for (w = 0; w < 3; w++) {
        AtSink s = rec_sink();
        AtLayout L;
        bag_fixture();
        at_render(&SC, &V, widths[w], 10000.0, 0, &FAKE, &s, &HITS);
        at_layout(widths[w], AT_PRESET_NARROW, &L);
        cells = keys = 0;
        for (i = 0; i < HITS.n; i++) {
            const AtHit *h = &HITS.h[i];
            if (h->kind == AT_HIT_CELL) {
                cells++;
                CHECK(h->r.x >= L.primary.x && h->r.x + h->r.w <= L.primary.x + L.primary.w && h->r.y >= L.primary.y && h->r.y + h->r.h <= L.primary.y + L.primary.h);
                CHECK(at_hit_test(&HITS, h->r.x + h->r.w * 0.5f, h->r.y + h->r.h * 0.5f) == i);   /* the centre of a cell hits that cell */
                for (j = i + 1; j < HITS.n; j++) if (HITS.h[j].kind == AT_HIT_CELL) {
                    const AtRect *a = &h->r, *b = &HITS.h[j].r;
                    CHECK(a->x + a->w <= b->x || b->x + b->w <= a->x || a->y + a->h <= b->y || b->y + b->h <= a->y);   /* cells never overlap */
                }
            } else if (h->kind == AT_HIT_KEY) {
                keys++;
                CHECK(h->r.y >= L.keys.y - 4.0f && h->r.y + h->r.h <= L.keys.y + L.keys.h + 4.0f && h->r.x + h->r.w <= L.keys.x + L.keys.w);
            }
        }
        CHECK(cells == 13 && keys == 4);
        CHECK(L.wide == (widths[w] >= 760.0f));
        if (L.wide) CHECK(find_text("VERSUS") != NULL);                     /* the rail (with chapter names) replaces the chapter dots */
        else CHECK(find_text("VERSUS") == NULL && find_text("V") != NULL);
    }
}

static void list_screen(void)
{
    AtSink s = rec_sink();
    int i;
    memset(&SC, 0, sizeof SC); at_view_init(&V);
    snprintf(SC.id, sizeof SC.id, "demo.list"); snprintf(SC.title, sizeof SC.title, "VIDEO");
    SC.primary = AT_PRIMARY_LIST; SC.preset = AT_PRESET_NORMAL; SC.n_items = 12;
    for (i = 0; i < 12; i++) { snprintf(SC.items[i].id, AT_ID, "i%d", i); snprintf(SC.items[i].label, AT_STR, "Row %d", i); }
    SC.items[2].flags = AT_CELL_DISABLED;
    V.focus.block = 0; V.focus.index = 7; V.scroll = 3;
    at_render(&SC, &V, 640.0f, 10000.0, 0, &FAKE, &s, &HITS);
    CHECK(find_text("Row 3") != NULL && find_text("Row 2") == NULL);       /* the window starts at the scroll offset */
    CHECK(HITS.n >= 5 && HITS.n < 12);                                       /* only visible rows are targets */
    CHECK(find_text("Row 7") != NULL && find_text("Row 7")->rgba == AT_C_IVORY);   /* the focused row is bright */
}

static void overlays_and_fade(void)
{
    AtSink s = rec_sink();
    int n_rest;
    bag_fixture();
    at_render(&SC, &V, 640.0f, 10000.0, 0, &FAKE, &s, &HITS);
    n_rest = REC.np;
    CHECK(count_color(AT_C_SCRIM) == 0);
    s = rec_sink(); bag_fixture();
    snprintf(V.note.text, AT_STR, "Merged! Kindling got stronger."); V.note.kind = AT_NOTE_OK; V.note.from_ms = 10000.0; V.note.until_ms = 13000.0;
    at_render(&SC, &V, 640.0f, 11000.0, 0, &FAKE, &s, &HITS);
    CHECK(find_text("Merged! Kindling got stronger.") != NULL && REC.np > n_rest);
    s = rec_sink(); bag_fixture();
    snprintf(V.note.text, AT_STR, "old"); V.note.until_ms = 5000.0;
    at_render(&SC, &V, 640.0f, 11000.0, 0, &FAKE, &s, &HITS);
    CHECK(find_text("old") == NULL);                                         /* an expired note is not drawn */
    s = rec_sink(); bag_fixture();
    V.dialog.open = 1; V.dialog.n = 2; snprintf(V.dialog.title, AT_STR, "DISCARD?"); snprintf(V.dialog.body, AT_TEXT, "Gone for good.");
    V.dialog.btn[0] = 'A'; snprintf(V.dialog.label[0], 24, "Discard"); V.dialog.btn[1] = 'B'; snprintf(V.dialog.label[1], 24, "Cancel");
    at_render(&SC, &V, 640.0f, 11000.0, 0, &FAKE, &s, &HITS);
    CHECK(count_color(AT_C_SCRIM) == 1 && find_text("DISCARD?") != NULL);
    { int d = 0, i; for (i = 0; i < HITS.n; i++) if (HITS.h[i].kind == AT_HIT_DIALOG) d++; CHECK(d == 2); }
    s = rec_sink(); bag_fixture(); V.opened_ms = 10000.0;                    /* opening: the fade starts opaque and is gone after 100 ms */
    at_render(&SC, &V, 640.0f, 10000.0, 0, &FAKE, &s, &HITS);
    CHECK(REC.p[REC.np - 1].rgba == ((AT_C_GROUND & 0xFFFFFF00u) | 255u));
    s = rec_sink(); bag_fixture(); V.opened_ms = 10000.0;
    at_render(&SC, &V, 640.0f, 10200.0, 0, &FAKE, &s, &HITS);
    CHECK(REC.p[REC.np - 1].rgba != ((AT_C_GROUND & 0xFFFFFF00u) | 255u));                 /* after 100 ms the fade quad is gone (the last quad is a key hint's) */
    s = rec_sink(); bag_fixture(); V.opened_ms = 10000.0;
    at_render(&SC, &V, 640.0f, 10000.0, 1, &FAKE, &s, &HITS);               /* Reduced motion: no fade at all */
    CHECK(REC.p[REC.np - 1].rgba != ((AT_C_GROUND & 0xFFFFFF00u) | 255u));
}

int main(void)
{
    budget_and_legibility(); focus_cues(); long_strings(); hits_at_widths(); list_screen(); overlays_and_fade();
    ATLAS_DONE("atlas render");
}
```

Register: `atlas-render) sources=(pc/tests/atlas_render_test.c pc/platform/gw_ui_render.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c) ;;` and add `, atlas-render` to the die message.

- [ ] **Step 2: Run it to verify it fails.**

```bash
nt atlas-render
```

Expected: `error: native test source missing: pc/platform/gw_ui_render.c`.

- [ ] **Step 3: Write the minimal implementation.** Create `melee/pc/platform/gw_ui_render.h`:

```c
/* gw_ui_render.h - compose one Atlas screen from its parts. Pure C: draws only through AtSink. */
#ifndef GW_UI_RENDER_H
#define GW_UI_RENDER_H
#include "gw_ui_input.h"
#include "gw_ui_parts.h"
#include "gw_ui_screen.h"
#ifdef __cplusplus
extern "C" {
#endif

#define AT_SCREEN_QUAD_CAP 4096   /* one screen's entries in the kit quad list: the cap */
#define AT_SCREEN_QUAD_WARN 3000  /* and the line the host logs a warning at */

/* Draws the screen for a canvas of width canvas_w at time now_ms (the UI clock). `reduced` turns the open fade
 * into a cut. Fills `hits` with the rectangles the mouse can reach (cells or rows, key hints, dialog buttons). */
void at_render(const AtScreen *sc, const AtView *v, float canvas_w, double now_ms, int reduced,
               const AtTextOps *o, const AtSink *s, AtHits *hits);

#ifdef __cplusplus
}
#endif
#endif
```

Create `melee/pc/platform/gw_ui_render.c`:

```c
#include "gw_ui_render.h"
#include "gw_ui_stack.h"
#include "gw_ui_tokens.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

static void hit_add(AtHits *h, AtRect r, int kind, int a, int b)
{
    if (h->n >= AT_MAX_HITS) return;
    h->h[h->n].r = r; h->h[h->n].kind = kind; h->h[h->n].a = a; h->h[h->n].b = b;
    h->n++;
}

static void draw_header(const AtScreen *sc, const AtLayout *L, const AtTextOps *o, const AtSink *s)
{
    const char *items[4];
    int n = 0, i;
    for (i = 0; i < sc->n_parents && n < 3; i++) items[n++] = sc->parent[i];
    items[n++] = sc->title;
    at_part_trail(s, o, L->trail, items, n);
    if (L->wide) at_part_rail(s, o, L->rail, sc->chapter);
    else at_part_chapter(s, o, L->chapter, sc->chapter);
    at_poly_rect(s, L->rule.x, L->rule.y, L->rule.w, 1.0f, AT_C_LINE);
}

static void draw_grid(const AtScreen *sc, const AtView *v, const AtLayout *L, const AtTextOps *o, const AtSink *s, AtHits *hits)
{
    float x0 = L->primary.x + 12.0f, y = L->primary.y + 12.0f, iw = L->primary.w - 24.0f, gap = 8.0f, cell;
    int b, i, maxc = 1;
    for (b = 0; b < sc->n_blocks; b++) if (!sc->blocks[b].stones && sc->blocks[b].cols > maxc) maxc = sc->blocks[b].cols;
    cell = (float) floor((iw - (float) (maxc - 1) * gap) / (float) maxc);
    if (cell > 56.0f) cell = 56.0f;
    if (cell < 24.0f) cell = 24.0f;
    for (b = 0; b < sc->n_blocks; b++) {
        const AtBlock *bk = &sc->blocks[b];
        int rows = (bk->n + bk->cols - 1) / bk->cols;
        float cw = bk->stones ? 34.0f : cell, ch = bk->stones ? 38.0f : cell, tw, cnw;
        if (rows < 1) rows = 1;
        tw = o->width(o->user, AT_R_CAP14, bk->title);
        cnw = bk->count[0] ? o->width(o->user, AT_R_NUM12, bk->count) : 0.0f;
        at_text(s, o, AT_R_CAP14, bk->title, x0, y + 14.0f, AT_C_MUTED, AT_ALIGN_LEFT, iw - cnw - 16.0f);
        if (bk->count[0]) at_text(s, o, AT_R_NUM12, bk->count, x0 + iw, y + 14.0f, AT_C_DIM, AT_ALIGN_RIGHT, 0.0f);
        if (x0 + tw + 10.0f < x0 + iw - cnw - 10.0f) at_poly_rect(s, x0 + tw + 10.0f, y + 9.0f, iw - tw - cnw - 20.0f, 1.0f, AT_C_LINE);
        y += 26.0f;
        for (i = 0; i < bk->n; i++) {
            AtRect r;
            int st = (v->focus.block == b && v->focus.index == i) ? AT_ST_FOCUS : AT_ST_REST;
            r.x = x0 + (float) (i % bk->cols) * (cw + gap);
            r.y = y + (float) (i / bk->cols) * (ch + gap);
            r.w = cw; r.h = ch;
            if (bk->stones) at_part_stone(s, o, r, &bk->cells[i], st, v->port_rgba);
            else at_part_cell(s, o, r, &bk->cells[i], st, v->port_rgba);
            hit_add(hits, r, AT_HIT_CELL, b, i);
        }
        if (bk->stones && bk->note[0]) at_text(s, o, AT_R_BODY14, bk->note, x0 + (float) bk->n * (cw + gap) + 8.0f, y + 24.0f, AT_C_TEXT2, AT_ALIGN_LEFT, iw - (float) bk->n * (cw + gap) - 8.0f);
        y += (float) rows * (ch + gap) - gap + 12.0f;
    }
    if (sc->footer.has) {
        AtRect f;
        f.x = x0; f.y = L->primary.y + L->primary.h - 12.0f - 48.0f; f.w = iw; f.h = 48.0f;
        at_part_footer(s, o, f, &sc->footer);
    }
}

static void draw_list(const AtScreen *sc, const AtView *v, const AtLayout *L, const AtTextOps *o, const AtSink *s, AtHits *hits)
{
    float x0 = L->primary.x + 12.0f, y0 = L->primary.y + 14.0f, iw = L->primary.w - 24.0f;
    int visible = (int) floor((L->primary.h - 28.0f) / 39.0f), first = v->scroll < 0 ? 0 : v->scroll, i;   /* the host keeps v->scroll valid */
    for (i = first; i < sc->n_items && i < first + visible; i++) {
        AtRect r;
        r.x = x0; r.y = y0 + (float) (i - first) * 39.0f; r.w = iw; r.h = 34.0f;
        at_part_row(s, o, r, &sc->items[i], (v->focus.index == i) ? AT_ST_FOCUS : AT_ST_REST);
        hit_add(hits, r, AT_HIT_CELL, 0, i);
    }
}

static void draw_keys(const AtScreen *sc, const AtView *v, const AtLayout *L, const AtTextOps *o, const AtSink *s, AtHits *hits)
{
    float x = L->keys.x, base = L->keys.y + 18.0f, adv;
    int i;
    adv = at_part_hint(s, o, x, base, 'M', "Move");
    x += adv;
    for (i = 0; i < sc->n_keys; i++) {
        AtRect r;
        if (!v->key_shown[i] || v->key_label[i][0] == '\0') continue;
        adv = at_part_hint(s, o, x, base, sc->keys[i].btn, v->key_label[i]);
        r.x = x; r.y = base - 16.0f; r.w = adv - 18.0f; r.h = 22.0f;
        hit_add(hits, r, AT_HIT_KEY, sc->keys[i].btn, 0);
        x += adv;
    }
    if (v->counter[0]) at_text(s, o, AT_R_NUM16, v->counter, L->keys.x + L->keys.w, base, AT_C_DIM, AT_ALIGN_RIGHT, 0.0f);
}

void at_render(const AtScreen *sc, const AtView *v, float canvas_w, double now, int reduced,
               const AtTextOps *o, const AtSink *s, AtHits *hits)
{
    AtLayout L;
    AtTween open;
    float k;
    hits->n = 0;
    at_layout(canvas_w, sc->preset, &L);
    at_poly_rect(s, 0.0f, 0.0f, L.canvas.w, 480.0f, AT_C_GROUND);
    draw_header(sc, &L, o, s);
    at_plate(s, L.primary, AT_C_PLATE, AT_C_EDGE, 3.0f, (float) AT_PX_CH);
    if (sc->primary == AT_PRIMARY_GRID) draw_grid(sc, v, &L, o, s, hits);
    else draw_list(sc, v, &L, o, s, hits);
    if (sc->preset != AT_PRESET_NONE) at_part_explainer(s, o, L.explainer, &v->ex);
    draw_keys(sc, v, &L, o, s, hits);
    if (v->note.text[0] != '\0' && now < v->note.until_ms) {
        AtRect r;
        float w = o->width(o->user, AT_R_BODY14, v->note.text) + 54.0f, right = L.wide ? L.header.x + L.header.w : L.chapter.x - 12.0f;
        if (w > 300.0f) w = 300.0f;
        r.x = right - w; r.y = 22.0f; r.w = w; r.h = 30.0f;
        at_part_note(s, o, r, v->note.text, v->note.kind, v->note.until_ms > v->note.from_ms ? (float) ((v->note.until_ms - now) / (v->note.until_ms - v->note.from_ms)) : 0.0f);
    }
    if (v->dialog.open) {
        AtRect b[2];
        AtTween rise;
        int n, i;
        at_tween_start(&rise, v->dialog.from_ms, 140.0, reduced);
        n = at_part_dialog(s, o, L.canvas.w, &v->dialog, 6.0f * (1.0f - at_tween_value(&rise, now)), b);
        for (i = 0; i < n; i++) hit_add(hits, b[i], AT_HIT_DIALOG, v->dialog.btn[i], 0);
    }
    at_tween_start(&open, v->opened_ms, 100.0, reduced);
    k = 1.0f - at_tween_value(&open, now);                               /* the screen fades in from the ground colour */
    if (k > 0.004f) at_poly_rect(s, 0.0f, 0.0f, L.canvas.w, 480.0f, (AT_C_GROUND & 0xFFFFFF00u) | (unsigned) (k * 255.0f + 0.5f));
}
```

`draw_list` draws from `v->scroll`: the host keeps it valid (Task 11 updates it with `at_list_scroll` after every focus change). The `list_screen` test sets `V.scroll = 3` with focus 7 and 5 visible rows (362-28 = 334 / 39 = 8 rows visible: rows 3 to 10), so row 7 is on screen and row 2 is not.

- [ ] **Step 4: Run the tests.**

```bash
nt atlas-render
```

Expected: `atlas render: 420 checks, 0 failed`. If `budget_and_legibility` reports `REC.nm` out of range, count the model calls the fixture should produce: equipped 5 (the locked cell draws none), bag 3, the explainer 1 media plus 2 with, the footer 3 = 14. If the `list_screen` window check fails, remember `visible = floor((362 - 28) / 39) = 8`.

- [ ] **Step 5: Commit.** Game repo: `pc/platform/gw_ui_render.h`, `gw_ui_render.c`, `pc/tests/atlas_render_test.c`, message `atlas: screen renderer, hit rectangles, quad budget checks`. Workspace repo: `tools/port/native_test.sh`, message `atlas: atlas-render native test case`.

### Task 10: Kit additions: a four-corner flat quad, letter-spacing, room for the Atlas fonts

**Files:**
- Modify (game repo): `melee/pc/platform/gw_kit.h` (declarations near the draw calls, after line 134), `melee/pc/platform/gw_kit.c` (lines 288 and 292, the `kf` struct near line 330, `kf_width_raw` near line 628, `gw_Kit_DrawText` near line 1250, `gw_Kit_DrawFlat` near line 1323, the test block near line 1595)

**Interfaces:**
Consumes: the existing kit (`GwKitQuad`, `kq`/`nkq`, `kf`).
Produces:

```c
int  gw_Kit_DrawPoly4(const float x[4], const float y[4], uint32_t rgba);   /* one flat quad with these corners (top-left, top-right, bottom-right, bottom-left); 1 when added, 0 when full or transparent */
void gw_Kit_SetTracking(float px);                                           /* letter-spacing in px added after every glyph by TextWidth, Fit, DrawText and DrawParagraph; 0 = off (the default) */
```

and two raised limits: `KF_ROLES` 24 (was 12) and `KF_MAX_KERN` 32000 (was 16000). Why: the manifest will hold the 10 legacy roles plus 13 Atlas roles (23); the legacy roles carry 6,364 kerning pairs [measured in `menu/out_kit/font/font_manifest.json`] and the 13 Atlas roles add 7,065 [measured by running the generator], 13,429 together: under the old 16,000, but the loader silently stops reading pairs past the limit (`gw_kit.c:419`), so one more face would lose kerning with no error. The roles array is the hard one: 12 would drop the Atlas roles from the 13th on.

- [ ] **Step 1: Write the failing test.** This one runs inside the exe (the kit is host code that links Windows and the renderer, so it has no standalone harness; its tests are registered with `gw_test_register`). In `melee/pc/platform/gw_kit.c`, above `void gw_kit_tests_register(void)` add:

```c
static int test_kit_poly4_and_tracking(void) {
    const float px[4] = {10.0f, 50.0f, 50.0f, 10.0f}, py[4] = {20.0f, 20.0f, 60.0f, 60.0f};
    int role, n;
    float w0, w1;
    if (!gw_Kit_Available()) {
        return 0;
    }
    gw_Kit_BeginFrame();
    n = gw_Kit_DrawPoly4(px, py, 0xFF7A3DFFu);
    if (n != 1 || gw_Kit_QuadCount() != 1 || gw_Kit_QuadAt(0)->tex != -1 || gw_Kit_QuadAt(0)->x[2] != 50.0f ||
        gw_Kit_QuadAt(0)->y[2] != 60.0f || gw_Kit_QuadAt(0)->rgba != 0xFF7A3DFFu) {
        gw_test_fail("DrawPoly4 did not append one flat quad with its corners (%d, %d quads)", n, gw_Kit_QuadCount());
        return 1;
    }
    if (gw_Kit_DrawPoly4(px, py, 0x00000000u) != 0 || gw_Kit_QuadCount() != 1) {
        gw_test_fail("a fully transparent poly was drawn");
        return 1;
    }
    role = gw_Kit_Role("body");
    if (role < 0) {
        role = 0;
    }
    gw_Kit_SetTracking(0.0f);
    w0 = gw_Kit_TextWidth(role, "ABC");
    gw_Kit_SetTracking(2.0f);
    w1 = gw_Kit_TextWidth(role, "ABC");
    gw_Kit_SetTracking(0.0f);
    if (fabsf((w1 - w0) - 6.0f) > 0.01f) {
        gw_test_fail("tracking of 2 px over three glyphs should add 6 px (it added %.2f)", w1 - w0);
        return 1;
    }
    {
        const GwKitQuad *a, *b;
        float gap0, gap1;
        gw_Kit_BeginFrame();
        gw_Kit_DrawText(0, 100, "II", role, 0xFFFFFFFFu, GW_KIT_ALIGN_LEFT, 0, 0, NULL);
        a = gw_Kit_QuadAt(0);
        b = gw_Kit_QuadAt(1);
        if (a == NULL || b == NULL) {
            gw_test_fail("two glyphs drew no quads");
            return 1;
        }
        gap0 = b->x[0] - a->x[0];
        gw_Kit_SetTracking(3.0f);
        gw_Kit_BeginFrame();
        gw_Kit_DrawText(0, 100, "II", role, 0xFFFFFFFFu, GW_KIT_ALIGN_LEFT, 0, 0, NULL);
        a = gw_Kit_QuadAt(0);
        b = gw_Kit_QuadAt(1);
        gap1 = b->x[0] - a->x[0];
        gw_Kit_SetTracking(0.0f);
        if (fabsf((gap1 - gap0) - 3.0f) > 0.01f) {
            gw_test_fail("drawing with tracking 3 moved the second glyph by %.2f, not 3", gap1 - gap0);
            return 1;
        }
    }
    gw_Kit_BeginFrame();
    return 0;
}
```

and add `gw_test_register("kit_poly4_and_tracking", test_kit_poly4_and_tracking);` as the last line of `gw_kit_tests_register`.

- [ ] **Step 2: Run it to verify it fails.** Build the shim (this does the link and the bridge fixpoint; it takes a few minutes):

```bash
tools/port/build.sh --shim gw_kit.c
```

Expected failure: `error: call to undeclared function 'gw_Kit_DrawPoly4'` (and one for `gw_Kit_SetTracking`).

- [ ] **Step 3: Write the minimal implementation.**
  1. `gw_kit.h`: after the `gw_Kit_DrawFlat` declaration add

```c
/* One flat quad with four arbitrary corners (top-left, top-right, bottom-right, bottom-left): the Atlas plates
 * and glyphs are built from these. Returns 1 when added, 0 when the list is full or the colour is transparent. */
int gw_Kit_DrawPoly4(const float x[4], const float y[4], uint32_t rgba);
/* Letter-spacing in px added after every glyph by gw_Kit_TextWidth, gw_Kit_Fit, gw_Kit_DrawText and the paragraph
 * (0 = none, the default). A caller sets it around its own text and resets it to 0. */
void gw_Kit_SetTracking(float px);
```

  2. `gw_kit.c`: change `#define KF_ROLES 12` to `#define KF_ROLES 24 /* the 10 legacy roles and the 13 Atlas roles, with room */`; change `#define KF_MAX_KERN 16000` to `#define KF_MAX_KERN 32000 /* the legacy roles carry 6,364 pairs, the Atlas ones about as many again; the loader stops silently past this */`.
  3. `gw_kit.c`: directly after the line `} kf;` that closes the `static struct { ... } kf;` add `static float kf_track; /* letter-spacing in px after every glyph (gw_Kit_SetTracking) */`.
  4. `gw_kit.c`, function `kf_width_raw`: change `x += kf_kern(r, prev, c) + r->g[c].adv;` to `x += kf_kern(r, prev, c) + r->g[c].adv + kf_track;`.
  5. `gw_kit.c`, function `gw_Kit_DrawText`: in the glyph loop change the last statement `pen += g->adv;` to `pen += g->adv + kf_track;`. (Run `grep -n "pen += g->adv" melee/pc/platform/gw_kit.c` first: it must match exactly once, inside `gw_Kit_DrawText`; if it matches more, change only the one in `gw_Kit_DrawText`.)
  6. `gw_kit.c`, directly after `gw_Kit_DrawFlat` add:

```c
int gw_Kit_DrawPoly4(const float x[4], const float y[4], uint32_t rgba) {
    GwKitQuad *q;
    int k;
    if (nkq >= KQ_MAX || (rgba & 0xFF) == 0) return 0;
    q = &kq[nkq++];
    for (k = 0; k < 4; k++) {
        q->x[k] = x[k];
        q->y[k] = y[k];
        q->u[k] = 0.0f;
        q->v[k] = 0.0f;
    }
    q->rgba = rgba;
    q->tex = -1;
    q->flags = 0;
    return 1;
}

void gw_Kit_SetTracking(float px) { kf_track = px; }
```

- [ ] **Step 4: Run the tests.** Build, then run only the kit tests headless (no window; `main.c:308-330` returns before any window is created [unverified: if you see a window, close it by its PID and tell the coordinator]):

```bash
tools/port/build.sh --shim gw_kit.c
MELEE_TEST_FILTER=kit_ tools/port/run.sh --test atlas-kit --iso "$GW_ISO_VANILLA"
grep -a "TESTS" "$GW_BUILD_ROOT/runs/atlas-kit/melee-pc.log" | tail -8
```

Expected in the log: `kit_poly4_and_tracking` among the passing tests and a final line with `failures=0` (the other four `kit_*` tests pass too; they were passing before). If `GW_ISO_VANILLA` is empty the run cannot start: that is the owner's disc, set in `.env`; do not look for one yourself, ask the coordinator.

- [ ] **Step 5: Commit.** Game repo: `git -C "$GW_MELEE" add pc/platform/gw_kit.h pc/platform/gw_kit.c`, message `kit: gw_Kit_DrawPoly4, letter-spacing, room for 24 roles and 32,000 kerning pairs

The loader stops reading kerning pairs silently past KF_MAX_KERN; the legacy manifest has 6,364 pairs and the Atlas roles add 7,065. Tested in the exe (kit_poly4_and_tracking); not played.` with the two trailers.

---

### Task 11: The `gd.ui` Lua binding, the host sink, the tick and the draw pass

**Files:**
- Create (game repo): `melee/pc/platform/gw_script_ui.inc`
- Modify (game repo): `melee/pc/platform/gw_script.c` (include after line 6258; call sites at lines 6788, 6844, 6946-6955, 7597-7602, 7660), `melee/src/melee/gm/gmfrontend_settings.inc` (one row at line 189-200)
- Create (game repo): `melee/pc/tests/atlas_binding_test.c` (a host-side test of the binding: no game needed)
- Modify (workspace repo): `tools/port/linux_shims.txt` (eight lines), `tools/port/native_test.sh` (case `atlas-binding`)

**Interfaces:**
Consumes: everything in Tasks 1 to 9 and Task 10; from `gw_script.c`: `gs` (the state), `gs_pcall(script, nargs, nres, what)` (0 ok, -1 error with the results discarded), `gs_may_run(script)`, `gs_cur_script()`, `gs_kit_record(first, added)`, `gs_kit_optnum`, `gs_now_ms()`, `gs_ui_clock`, `gs_sm_emit(asset, &GsmParams, clip, &why)`, `gs_stage_models[]`, `gs_stage_nmodels`, `gw_ScriptGame_ModelRefOwned`, `gw_Script_StageResourceOwner`, `gw_script_pad_state`, `gw_script_pad_raw_buttons`, `gw_Mouse_ScriptRead`, `gw_Console_ScriptWidth`, `gw_Settings_Int`, `gs_prof_setfuncs`.
Produces (Lua API, exactly these names; section 7 of the spec describes the fields):

| call | does |
|---|---|
| `gd.ui.available()` | `true`, or `false, why` (the kit or the Atlas font roles are missing) |
| `gd.ui.screen(desc)` | register or replace the screen `desc.id` (the focus stays on the same cell id when it still exists); raises a Lua error with the validation message when the description is wrong |
| `gd.ui.open(id)` / `gd.ui.close([id])` | push a screen / remove it (or the top one); `on.open` and `on.close` run |
| `gd.ui.feed(id, intent)` | an intent from the script: `"up" "down" "left" "right" "accept" "back" "x" "y" "z"`; returns true when it was applied |
| `gd.ui.focus(id)` | `cell_id, block_id` of the focus, or nil |
| `gd.ui.set_focus(id, block_id, cell_id)` | true when that cell exists |
| `gd.ui.note{text=, kind="ok"|"warn"|"err"|"info", seconds=}` | a corner note on the top screen |
| `gd.ui.dialog{title=, text=, actions={{"A","Discard"},{"B","Cancel"}}, on=function(button) end}` | a dialog on the top screen; `on` gets the button letter |
| `gd.ui.state()` | `{depth, top, canvas_w, wide, quads, cost_ms, cost_max_ms, roles_ok}` for tests and the in-game checklist |

Handlers in `desc.on` get `(cell_id, block_id)`. Key label and `when` functions, the explainer provider and the counter function get the same two arguments and are called when focus changes or the screen is re-registered; they must be pure and cheap.

- [ ] **Step 1: Write the failing tests.** Two. The first needs no game: `gw_script_ui.inc` is included by a test program against stand-ins for the few `gw_script.c` internals it uses (the script table, `gs_pcall`, the kit's draw calls, with a switch that makes `gs_may_run` say no), and driven through a real Lua 5.4 state built from the repo's `pc/third_party/lua-5.4.7`. It checks conversion, focus by id, the legacy focus rule, handlers, disabled and locked cells, ownership, unload, that nothing runs when `gs_may_run` says no, and that a frame draws quads. Create `melee/pc/tests/atlas_binding_test.c`:

```c
/* Host-side test of the gd.ui binding: gw_script_ui.inc is included here, against stand-ins for the few gw_script.c
 * internals it uses (the script table, gs_pcall, the kit's draw calls), and driven through a real Lua 5.4 state.
 * No game, no renderer, no window. */
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include "gw_kit.h"
#include "gw_screen_model.h"
#include "atlas_check.h"

typedef struct { char id[64]; int used, disabled, gameplay; } GsScript;
static struct { lua_State *L; int cur, console; GsScript s[8]; unsigned char key_now[256]; } gs;
static int g_may_run = 1, g_quads, g_models;
static double g_now = 1000.0;

void gw_log(const char *fmt, ...) { (void) fmt; }
static int gs_may_run(int i) { (void) i; return g_may_run; }
static int gs_pcall(int script, int nargs, int nres, const char *what)
{
    (void) script; (void) what;
    if (lua_pcall(gs.L, nargs, nres, 0) != LUA_OK) { lua_pop(gs.L, 1); return -1; }
    return 0;
}
static const GsScript *gs_cur_script(void) { return &gs.s[gs.cur]; }
static double gs_now_ms(void) { return g_now; }
static double gs_ui_clock;
static struct { int token; } gs_stage_models[4];
static int gs_stage_nmodels;
int gw_ScriptGame_ModelRefOwned(int a, int b, int c, int d) { (void) a; (void) b; (void) c; (void) d; return 0; }
int gw_Script_StageResourceOwner(void) { return 0; }
static int gs_sm_emit(int asset, const GsmParams *p, int clip, const char **why) { (void) asset; (void) p; (void) clip; (void) why; g_models++; return 0; }
void gw_script_pad_state(int ch, unsigned *b, int *sx, int *sy, int *cx, int *cy, int *tl, int *tr) { (void) ch; *b = 0; *sx = *sy = *cx = *cy = *tl = *tr = 0; }
unsigned gw_script_pad_raw_buttons(int ch) { (void) ch; return 0; }
void gw_Mouse_ScriptRead(float *x, float *y, int *buttons, float *wheel) { *x = -1000.0f; *y = -1000.0f; *buttons = 0; *wheel = 0.0f; }
float gw_Console_ScriptWidth(void) { return 640.0f; }
int gw_Settings_Int(const char *k, int d) { (void) k; return d; }
static void gs_prof_setfuncs(lua_State *L, const luaL_Reg *funcs, const char *prefix) { (void) prefix; luaL_setfuncs(L, funcs, 0); }
static int gs_kit_record(int first, int added) { (void) first; return added; }
static double gs_kit_optnum(lua_State *L, int t, const char *k, double def)
{
    double v = def;
    if (!lua_istable(L, t)) return def;
    lua_getfield(L, t, k);
    if (lua_isnumber(L, -1)) v = lua_tonumber(L, -1);
    lua_pop(L, 1);
    return v;
}
int gw_Kit_Available(void) { return 1; }
const char *gw_Kit_Why(void) { return ""; }
int gw_Kit_Role(const char *name) { return name != NULL && name[0] == 'a' && name[1] == '_' ? 3 : -1; }
float gw_Kit_TextWidth(int role, const char *s) { (void) role; return 6.0f * (float) strlen(s); }
int gw_Kit_DrawText(float x, float y, const char *s, int role, uint32_t rgba, int align, float max_w, float shear, float *out_w)
{
    (void) x; (void) y; (void) role; (void) rgba; (void) align; (void) max_w; (void) shear;
    if (out_w) *out_w = 0.0f;
    g_quads += (int) strlen(s);
    return (int) strlen(s);
}
int gw_Kit_DrawPoly4(const float x[4], const float y[4], uint32_t rgba) { (void) x; (void) y; (void) rgba; g_quads++; return 1; }
void gw_Kit_SetTracking(float px) { (void) px; }
int gw_Kit_QuadCount(void) { return g_quads; }
int gw_Kit_QuadRoom(void) { return 16000; }

#include "gw_script_ui.inc"

/* run Lua; the result is the last value as text, or "ERR ..." */
static const char *lua(const char *code)
{
    static char buf[512];
    lua_State *L = gs.L;
    int top = lua_gettop(L);
    buf[0] = '\0';
    if (luaL_dostring(L, code) != LUA_OK) snprintf(buf, sizeof buf, "ERR %s", lua_tostring(L, -1));
    else if (lua_gettop(L) > top) snprintf(buf, sizeof buf, "%s", luaL_tolstring(L, -1, NULL));
    lua_settop(L, top);
    return buf;
}
#define LUA_IS(code, want) CHECK_STR(lua(code), want)
#define LUA_HAS(code, part) do { const char *_r = lua(code); at_t_count++; if (strstr(_r, part) == NULL) { at_t_fails++; printf("FAIL %s:%d: %s -> \"%s\" lacks \"%s\"\n", __FILE__, __LINE__, code, _r, part); } } while (0)

int main(void)
{
    lua_State *L = luaL_newstate();
    gs.L = L; gs.cur = 0; gs.console = 0;
    snprintf(gs.s[0].id, sizeof gs.s[0].id, "console");
    snprintf(gs.s[1].id, sizeof gs.s[1].id, "envoy/main");
    luaL_openlibs(L);
    lua_newtable(L); gs_push_ui(L); lua_setfield(L, -2, "ui"); lua_setglobal(L, "gd");

    LUA_IS("return tostring((gd.ui.available()))", "true");
    /* a list: register, open, move focus by feed, a bad description, a note, a dialog */
    LUA_IS("return gd.ui.screen{id='t.list', primary={kind='list', items={{id='one',label='One'},{id='two',label='Two'},{id='three',label='Three',disabled=true}}}, explainer='none', keys={{'A','Pick'},{'B','Back'}}}", "true");
    LUA_IS("return gd.ui.open('t.list')", "true");
    LUA_IS("return gd.ui.state().top", "t.list");
    LUA_IS("return (gd.ui.focus('t.list'))", "one");
    LUA_IS("return gd.ui.feed('t.list','down')", "true");
    LUA_IS("return (gd.ui.focus('t.list'))", "two");
    LUA_HAS("return gd.ui.screen{id='t.bad', primary={kind='tiles'}}", "not supported");
    LUA_HAS("return gd.ui.feed('t.list','sideways')", "unknown intent");
    LUA_IS("return gd.ui.note{text='hi', kind='ok'}", "true");
    LUA_IS("return gd.ui.dialog{title='T', text='body', actions={{'A','Yes'},{'B','No'}}, on=function(b) DIALOG=b end}", "true");
    LUA_IS("gd.ui.feed('t.list','down'); return tostring(DIALOG)", "nil");          /* a dialog takes every event: focus did not move */
    LUA_IS("return (gd.ui.focus('t.list'))", "two");
    LUA_IS("gd.ui.feed('t.list','accept'); return DIALOG", "A");
    LUA_IS("gd.ui.close('t.list'); return tostring(gd.ui.state().top)", "nil");

    /* a grid: handlers, the provider, key functions, the legacy focus rule, disabled and locked cells */
    LUA_IS("LOG={}; return gd.ui.screen{id='t.grid', trail={'SOLO', title='BAG'}, primary={kind='grid', blocks={"
           "{id='eq', title='EQUIPPED', cols=3, cells={{id='eq:1',name='a'},{id='eq:2',name='b'},{id='eq:3',name='c',flags={locked=true}}}},"
           "{id='bag', title='BAG', cols=2, cells={{id='bag:1',name='x'},{id='bag:2',name='y',flags={disabled=true}}}}}},"
           "explainer={width='narrow', provide=function(c,b) return {kicker=b, title=c, what='rule '..c} end},"
           "keys={{'A', function(c) return c=='eq:1' and 'First' or nil end}, {'B','Close'}}, counter=function(c) return 'at '..c end, input='feed',"
           "on={focus=function(c,b) LOG[#LOG+1]='focus '..c end, accept=function(c,b) LOG[#LOG+1]='accept '..c end,"
           "back=function() LOG[#LOG+1]='back'; return {pop=true} end}}", "true");
    LUA_IS("gd.ui.open('t.grid'); return gd.ui.state().top", "t.grid");
    LUA_IS("gd.ui.feed('t.grid','right'); return (gd.ui.focus('t.grid'))", "eq:2");
    LUA_IS("gd.ui.feed('t.grid','accept'); return table.concat(LOG,',')", "focus eq:2,accept eq:2");
    LUA_IS("gd.ui.feed('t.grid','down'); return (gd.ui.focus('t.grid'))", "bag:2");
    LUA_IS("gd.ui.feed('t.grid','accept'); return table.concat(LOG,',')", "focus eq:2,accept eq:2,focus bag:2");   /* a disabled cell takes focus and never fires */
    LUA_IS("gd.ui.feed('t.grid','right'); return (gd.ui.focus('t.grid'))", "eq:3");                              /* the inherited legacy rule: the nearest cell to the right, in another row */
    LUA_IS("gd.ui.feed('t.grid','accept'); return LOG[#LOG]", "accept eq:3");                                    /* a locked cell still reaches its handler */
    LUA_IS("gd.ui.set_focus('t.grid','bag','bag:1'); return (gd.ui.focus('t.grid'))", "bag:1");
    LUA_IS("return tostring(gd.ui.set_focus('t.grid','bag','nope'))", "false");
    LUA_IS("gd.ui.screen{id='t.grid', primary={kind='grid', blocks={{id='eq', cols=3, cells={{id='eq:1'}}},{id='bag', cols=2, cells={{id='bag:1'}}}}}}; return (gd.ui.focus('t.grid'))", "bag:1");
    LUA_IS("gd.ui.screen{id='t.grid', primary={kind='grid', blocks={{id='eq', cols=3, cells={{id='eq:1'},{id='eq:2'}}}}}}; return (gd.ui.focus('t.grid'))", "eq:1");   /* the focused block is gone: the first cell */
    /* a re-registration from inside a handler keeps working */
    LUA_IS("N=0; gd.ui.screen{id='t.re', primary={kind='list', items={{id='a',label='A'},{id='b',label='B'}}},"
           "on={focus=function(c) N=N+1; gd.ui.screen{id='t.re', primary={kind='list', items={{id='a',label='A'},{id='b',label='B'}}}, on={}} end}}; gd.ui.open('t.re'); gd.ui.feed('t.re','down'); return N..(gd.ui.focus('t.re'))", "1b");
    /* a Lua error inside a handler is contained */
    LUA_IS("gd.ui.screen{id='t.err', primary={kind='list', items={{id='a',label='A'}}}, on={accept=function() error('boom') end}}; gd.ui.open('t.err'); gd.ui.feed('t.err','accept'); return 'alive'", "alive");

    /* a mod's screens carry its id; another script cannot replace them */
    gs.cur = 1;
    LUA_HAS("return gd.ui.screen{id='other.x', primary={kind='list', items={{id='a',label='A'}}}}", "must start with \"envoy.\"");
    LUA_IS("return gd.ui.screen{id='envoy.bag', primary={kind='list', items={{id='a',label='A'}}}}", "true");
    gs.cur = 2; snprintf(gs.s[2].id, sizeof gs.s[2].id, "envoy/second");
    LUA_HAS("return gd.ui.screen{id='envoy.bag', primary={kind='list', items={{id='a',label='A'}}}}", "belongs to another script");
    gs.cur = 1;
    LUA_IS("gd.ui.open('envoy.bag'); return gd.ui.state().top", "envoy.bag");
    gs_ui_release(1);                                                                /* the script unloads: its screens and the stack entry go */
    LUA_IS("return tostring(gd.ui.state().top)", "t.err");
    gs.cur = 0;

    /* nothing runs on a resimulated frame: handlers are not called while gs_may_run says no */
    LUA_IS("LOG={}; gd.ui.screen{id='t.rs', primary={kind='list', items={{id='a',label='A'}}}, on={accept=function() LOG[#LOG+1]='accept' end}}; gd.ui.open('t.rs'); return #LOG", "0");
    g_may_run = 0;
    LUA_IS("gd.ui.feed('t.rs','accept'); return #LOG", "0");
    g_may_run = 1;
    LUA_IS("gd.ui.feed('t.rs','accept'); return #LOG", "1");

    /* the tick and the draw pass: input polling is quiet with no pad and the pointer off the picture; a frame draws quads */
    gs_ui_tick();
    gs_ui_draw();
    CHECK(g_quads > 20);
    LUA_IS("return tostring(gd.ui.state().quads > 20)", "true");
    LUA_IS("return tostring(gd.ui.state().roles_ok)", "true");
    ATLAS_DONE("atlas binding");
}
```

Register the case in `tools/port/native_test.sh` (before the `*)` line; add `, atlas-binding` to the die message):

```bash
atlas-binding)
    sources=(pc/tests/atlas_binding_test.c pc/platform/gw_ui_render.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c)
    for lua_file in lapi lauxlib lbaselib lcode lcorolib lctype ldblib ldebug ldo ldump lfunc lgc linit liolib llex lmathlib lmem loadlib lobject lopcodes loslib lparser lstate lstring lstrlib ltable ltablib ltm lundump lutf8lib lvm lzio; do
        sources+=("pc/third_party/lua-5.4.7/src/$lua_file.c")
    done
    flags=(-std=gnu11 -w -ffunction-sections -I "$GW_MELEE/pc/platform" -I "$GW_MELEE/pc/third_party/lua-5.4.7/src") ;;
```

The second is an in-exe test of the same calls through the real script engine (the same pattern as `test_script_lab_draw_pass`, `gw_script.c:10437-10458`), for the final integration. In `gw_script.c`, above the line `#include "gw_script_deadline_tests.inc"` (line 9467) is the tests region; add this function there, after `t_exec`'s definition (line 9465), and register it next to `gw_test_register("script_kit_isolated", ...)` (line 11021) as `gw_test_register("script_ui_binding", test_script_ui_binding);`:

```c
/* gd.ui: register, open, move focus by feed, reject a bad description, close */
static int test_script_ui_binding(void) {
    char out[512];
    if (!gw_Kit_Available()) {
        return 0;
    }
    t_exec("= gd.ui.screen{id='uitest.a', primary={kind='list', items={{id='one',label='One'},{id='two',label='Two'}}}, "
           "explainer='none', keys={{'A','Pick'},{'B','Back'}}}", out, sizeof out);
    t_exec("= gd.ui.open('uitest.a')", out, sizeof out);
    t_exec("= gd.ui.state().top", out, sizeof out);
    if (strstr(out, "uitest.a") == NULL) {
        gw_test_fail("gd.ui.state().top is not the opened screen: %s", out);
        return 1;
    }
    t_exec("= (gd.ui.focus('uitest.a'))", out, sizeof out);
    if (strstr(out, "one") == NULL) {
        gw_test_fail("the first item does not start with focus: %s", out);
        return 1;
    }
    t_exec("= gd.ui.feed('uitest.a', 'down')", out, sizeof out);
    t_exec("= (gd.ui.focus('uitest.a'))", out, sizeof out);
    if (strstr(out, "two") == NULL) {
        gw_test_fail("feeding 'down' did not move focus to the second item: %s", out);
        return 1;
    }
    t_exec("= gd.ui.screen{id='uitest.bad', primary={kind='tiles'}}", out, sizeof out);
    if (strstr(out, "not supported") == NULL) {
        gw_test_fail("a bad description was not refused with its message: %s", out);
        return 1;
    }
    t_exec("= gd.ui.close('uitest.a')", out, sizeof out);
    t_exec("= gd.ui.state().top", out, sizeof out);
    if (strstr(out, "uitest.a") != NULL) {
        gw_test_fail("the closed screen is still the top: %s", out);
        return 1;
    }
    return 0;
}
```

- [ ] **Step 2: Run the first to verify it fails.**

```bash
nt atlas-binding
```

Expected: `fatal error: 'gw_script_ui.inc' file not found` (Task 10 must be done first: the test includes the real `gw_kit.h`, which must declare `gw_Kit_DrawPoly4` and `gw_Kit_SetTracking`).

- [ ] **Step 3: Write the implementation.** Create `melee/pc/platform/gw_script_ui.inc`:

```c
/* gw_script_ui.inc - gd.ui: Atlas screens for scripts (docs/scripting.md "gd.ui"; the design is
 * docs/superpowers/specs/2026-10-06-menu-reunification-design.md).
 *
 * Included by gw_script.c after gs_prof_setfuncs is declared. The pure Atlas units (gw_ui_*.c) own layout, focus,
 * input events and the parts; this file is the adapter: Lua table -> screen record, pad/keyboard/mouse -> events,
 * events -> Lua handlers, the sink -> the gd.kit quad list.
 *
 * ONLINE. A screen is presentation: it draws and takes local input, nothing here writes the simulation. The pad is
 * never masked from here (gd.input_mask stays the mod's call, refused online). Handlers do not run on a resimulated
 * frame (gs_may_run). Mouse and keyboard stay local, as gd.mouse and gd.key do. */
#include "gw_ui_render.h"
#include "gw_ui_stack.h"

extern int gw_Settings_Int(const char *key, int dflt); /* gw_settings.c:138; the Reduced Motion row writes "reduced_motion" */

#define GS_UI_SLOTS 8

typedef struct {
    int used, owner, explain_dirty, dialog_fn, warned;
    AtScreen sc;
    AtView view;
    AtHits hits;
    AtPad pad;
    AtKeys keys;
    AtMouse mouse;
} GsUiSlot;

static GsUiSlot gs_ui_slot[GS_UI_SLOTS];
static AtStack gs_ui_stack;
static AtvArena gs_ui_arena;
static AtScreen gs_ui_scratch;
static int gs_ui_role_idx[AT_R_COUNT];
static int gs_ui_roles_state; /* 0 not tried, 1 every Atlas role found, -1 missing */
static struct { double sum, max; int frames, quads; float canvas_w; } gs_ui_stat;

/* ---- fonts: the Atlas roles by name, resolved once ------------------------------------------------ */
static int gs_ui_roles_ok(void) {
    int r;
    if (gs_ui_roles_state != 0) return gs_ui_roles_state > 0;
    gs_ui_roles_state = -1;
    if (!gw_Kit_Available()) return 0;
    for (r = 0; r < AT_R_COUNT; r++) {
        gs_ui_role_idx[r] = gw_Kit_Role(at_role(r)->name);
        if (gs_ui_role_idx[r] < 0) {
            gw_log("ui: the font manifest has no Atlas role \"%s\" (rebuild the kit fonts: menu/pipeline/font_atlas.py)", at_role(r)->name);
            return 0;
        }
    }
    gs_ui_roles_state = 1;
    gw_log("ui: Atlas text roles found (%d)", AT_R_COUNT);
    return 1;
}

static float gs_ui_width(void *u, int role, const char *s) {
    float w;
    (void) u;
    gw_Kit_SetTracking(at_role(role)->tracked ? 0.10f * (float) at_role(role)->size : 0.0f);
    w = gw_Kit_TextWidth(gs_ui_role_idx[role], s);
    gw_Kit_SetTracking(0.0f);
    return w;
}

static void gs_ui_poly(void *u, const float x[4], const float y[4], unsigned rgba) {
    (void) u;
    gw_Kit_DrawPoly4(x, y, rgba);
}

static void gs_ui_text(void *u, float x, float base, const char *s, int role, unsigned rgba, int align, float max_w) {
    (void) u;
    (void) max_w;
    gw_Kit_SetTracking(at_role(role)->tracked ? 0.10f * (float) at_role(role)->size : 0.0f);
    gw_Kit_DrawText(x, base, s, gs_ui_role_idx[role], rgba, align, 0.0f, 0.0f, NULL);
    gw_Kit_SetTracking(0.0f);
}

/* a model handle (a gd.model_load token) to its asset slot, or -1 when it is stale: a cell then draws nothing */
static int gs_ui_model_asset(int token) {
    int i;
    for (i = 0; i < gs_stage_nmodels; ++i)
        if (gs_stage_models[i].token == token && gw_ScriptGame_ModelRefOwned(i, token, gw_Script_StageResourceOwner(), 0)) return i;
    return -1;
}

static void gs_ui_model_draw(void *u, int model, int ring, float x, float y, float w, float h, int focused, int dim) {
    GsmParams p;
    const char *why = "";
    int a;
    (void) u;
    memset(&p, 0, sizeof p);
    p.x = x; p.y = y; p.w = w; p.h = h;
    p.yaw = 18.0f; p.pitch = 12.0f;                             /* the bag's pose (envoy run_screen.lua S.model_opts) */
    p.spin = (focused && !gw_Settings_Int("reduced_motion", 0)) ? 120.0f : 0.0f;
    p.clock = (float) gs_ui_clock;
    p.margin = 0.02f; p.dim = dim ? 0.35f : 1.0f; p.alpha = 1.0f; p.tint = 0xFFFFFFFFu; p.cull = 0;
    if (ring >= 0 && (a = gs_ui_model_asset(ring)) >= 0) (void) gs_sm_emit(a, &p, 1, &why);   /* the rarity ring first: it passes behind the body */
    if (model >= 0 && (a = gs_ui_model_asset(model)) >= 0) (void) gs_sm_emit(a, &p, 1, &why);
}

/* ---- Lua table -> the value tree; functions become registry references ------------------------------ */
static int gs_ui_copy(lua_State *L, int idx, int depth) {
    int t;
    idx = lua_absindex(L, idx);
    t = lua_type(L, idx);
    if (depth > 8) return -1;
    if (t == LUA_TBOOLEAN) return atv_bool(&gs_ui_arena, lua_toboolean(L, idx));
    if (t == LUA_TNUMBER) return atv_num(&gs_ui_arena, lua_tonumber(L, idx));
    if (t == LUA_TSTRING) return atv_str(&gs_ui_arena, lua_tostring(L, idx));
    if (t == LUA_TFUNCTION) {
        int ref, n;
        lua_pushvalue(L, idx);
        ref = luaL_ref(L, LUA_REGISTRYINDEX);
        n = atv_fn(&gs_ui_arena, ref);
        if (n < 0) luaL_unref(L, LUA_REGISTRYINDEX, ref);
        return n;
    }
    if (t == LUA_TTABLE) {
        int n = atv_table(&gs_ui_arena), len = (int) lua_rawlen(L, idx), i;
        if (n < 0) return -1;
        for (i = 1; i <= len; i++) {
            int v;
            lua_rawgeti(L, idx, i);
            v = gs_ui_copy(L, -1, depth + 1);
            lua_pop(L, 1);
            if (v >= 0) atv_push(&gs_ui_arena, n, v);
        }
        lua_pushnil(L);
        while (lua_next(L, idx)) {
            if (lua_type(L, -2) == LUA_TSTRING) {
                int v = gs_ui_copy(L, -1, depth + 1);
                if (v >= 0) atv_set(&gs_ui_arena, n, lua_tostring(L, -2), v);
            }
            lua_pop(L, 1);
        }
        return n;
    }
    return -1;
}

static void gs_ui_unref_arena_except(lua_State *L, const int *keep, int nkeep) {
    int i, k;
    for (i = 0; i < gs_ui_arena.nn; i++) {
        int ref, kept = 0;
        if (gs_ui_arena.node[i].kind != ATV_FN) continue;
        ref = gs_ui_arena.node[i].fn;
        for (k = 0; k < nkeep; k++) if (keep[k] == ref) kept = 1;
        if (!kept) luaL_unref(L, LUA_REGISTRYINDEX, ref);
    }
}

static void gs_ui_unref_screen(lua_State *L, const AtScreen *s) {
    int refs[40], n = at_screen_fn_refs(s, refs, 40), i;
    for (i = 0; i < n; i++) luaL_unref(L, LUA_REGISTRYINDEX, refs[i]);
}

static int gs_ui_find(const char *id) {
    int i;
    for (i = 0; i < GS_UI_SLOTS; i++) if (gs_ui_slot[i].used && strcmp(gs_ui_slot[i].sc.id, id) == 0) return i;
    return -1;
}

/* the mod id of the running script (the part of "envoy/main" before the slash); NULL for the console */
static const char *gs_ui_owner_mod(char *buf, int cap) {
    const GsScript *s = gs_cur_script();
    char *slash;
    if (s == NULL || gs.cur == gs.console) return NULL;
    snprintf(buf, (size_t) cap, "%s", s->id);
    slash = strchr(buf, '/');
    if (slash != NULL) *slash = '\0';
    return buf;
}

/* ---- calling back into Lua ------------------------------------------------------------------------- */
/* Call a stored function with (cell id, block id). Returns 1 when it ran; nres results are then on the stack. */
static int gs_ui_call(int slot, int ref, const char *a, const char *b, int nres) {
    lua_State *L = gs.L;
    int owner = gs_ui_slot[slot].owner;
    if (ref < 0 || !gs_may_run(owner)) return 0;
    lua_rawgeti(L, LUA_REGISTRYINDEX, ref);
    if (!lua_isfunction(L, -1)) { lua_pop(L, 1); return 0; }
    lua_pushstring(L, a != NULL ? a : "");
    lua_pushstring(L, b != NULL ? b : "");
    return gs_pcall(owner, 2, nres, "ui") == 0;
}

static void gs_ui_close_screen(int slot);
static int gs_ui_open_screen(int slot);

/* a handler may return {pop = true} or {push = "screen id"} */
static void gs_ui_apply_result(void) {
    lua_State *L = gs.L;
    if (lua_istable(L, -1)) {
        lua_getfield(L, -1, "pop");
        if (lua_toboolean(L, -1) && at_stack_top(&gs_ui_stack) >= 0) gs_ui_close_screen(at_stack_top(&gs_ui_stack));
        lua_pop(L, 1);
        lua_getfield(L, -1, "push");
        if (lua_type(L, -1) == LUA_TSTRING) {
            int s = gs_ui_find(lua_tostring(L, -1));
            if (s >= 0) gs_ui_open_screen(s);
        }
        lua_pop(L, 1);
    }
    lua_pop(L, 1);
}

/* re-run the explainer provider, the key label and `when` functions and the counter for the focused cell */
static void gs_ui_refresh_view(int slot) {
    GsUiSlot *u = &gs_ui_slot[slot];
    lua_State *L = gs.L;
    const char *cid = at_screen_cell_id(&u->sc, u->view.focus), *bid = at_screen_block_id(&u->sc, u->view.focus.block);
    char err[96], cell[AT_ID], block[AT_ID];
    int i;
    u->explain_dirty = 0;
    snprintf(cell, sizeof cell, "%s", cid != NULL ? cid : "");     /* a handler may re-register the screen and move these */
    snprintf(block, sizeof block, "%s", bid != NULL ? bid : "");
    cid = cell[0] ? cell : NULL;
    bid = block[0] ? block : NULL;
    if (u->sc.fn_provide >= 0 && cid != NULL && gs_ui_call(slot, u->sc.fn_provide, cid, bid, 1)) {
        int n;
        atv_init(&gs_ui_arena);
        n = gs_ui_copy(L, -1, 0);
        at_explainer_from_val(&gs_ui_arena, n, &u->view.ex, err, sizeof err);
        gs_ui_unref_arena_except(L, NULL, 0);
        lua_pop(L, 1);
        if (u->view.ex.warn) gw_log("ui: %s: an explainer string was cut to its field", u->sc.id);
    } else {
        atv_init(&gs_ui_arena);
        at_explainer_from_val(&gs_ui_arena, -1, &u->view.ex, err, sizeof err);
    }
    for (i = 0; i < u->sc.n_keys; i++) {
        AtKey *k = &u->sc.keys[i];
        int show = 1;
        snprintf(u->view.key_label[i], AT_STR, "%s", k->label);
        if (k->fn_when >= 0) {
            show = 0;
            if (gs_ui_call(slot, k->fn_when, cid, bid, 1)) { show = lua_toboolean(L, -1); lua_pop(L, 1); }
        }
        if (show && k->fn_label >= 0) {
            show = 0;
            if (gs_ui_call(slot, k->fn_label, cid, bid, 1)) {
                if (lua_type(L, -1) == LUA_TSTRING) { snprintf(u->view.key_label[i], AT_STR, "%s", lua_tostring(L, -1)); show = 1; }
                lua_pop(L, 1);
            }
        }
        u->view.key_shown[i] = (unsigned char) (show && u->view.key_label[i][0] != '\0');
    }
    if (u->sc.fn_counter >= 0) {
        u->view.counter[0] = '\0';
        if (gs_ui_call(slot, u->sc.fn_counter, cid, bid, 1)) {
            if (lua_type(L, -1) == LUA_TSTRING) snprintf(u->view.counter, AT_STR, "%s", lua_tostring(L, -1));
            lua_pop(L, 1);
        }
    } else {
        snprintf(u->view.counter, AT_STR, "%s", u->sc.counter);
    }
}

/* ---- stack operations --------------------------------------------------------------------------------- */
static int gs_ui_open_screen(int slot) {
    GsUiSlot *u = &gs_ui_slot[slot];
    AtStackEntry *top;
    if (!at_stack_push(&gs_ui_stack, slot)) return 0;
    top = at_stack_top_entry(&gs_ui_stack);
    if (top != NULL && top->focus.block >= 0 && u->view.focus.block < 0) u->view.focus = top->focus;
    u->view.opened_ms = gs_now_ms();
    u->view.port_rgba = 0;
    u->explain_dirty = 1;
    memset(&u->pad, 0, sizeof u->pad);
    memset(&u->keys, 0, sizeof u->keys);
    memset(&u->mouse, 0, sizeof u->mouse);
    gw_log("ui: screen %s open (%d blocks, %d items)", u->sc.id, u->sc.n_blocks, u->sc.n_items);
    if (u->sc.fn_open >= 0 && gs_ui_call(slot, u->sc.fn_open, "", "", 1)) gs_ui_apply_result();
    return 1;
}

static void gs_ui_close_screen(int slot) {
    GsUiSlot *u = &gs_ui_slot[slot];
    AtStackEntry *top = at_stack_top_entry(&gs_ui_stack);
    if (top != NULL && top->screen == slot) { top->focus = u->view.focus; top->scroll = u->view.scroll; }
    if (!at_stack_remove(&gs_ui_stack, slot)) return;
    if (u->sc.fn_close >= 0 && gs_ui_call(slot, u->sc.fn_close, "", "", 1)) lua_pop(gs.L, 1);
    gw_log("ui: screen %s closed", u->sc.id);
}

/* a script unloaded: its screens and their references go */
static void gs_ui_release(int script) {
    int i;
    for (i = 0; i < GS_UI_SLOTS; i++) {
        GsUiSlot *u = &gs_ui_slot[i];
        if (!u->used || u->owner != script) continue;
        at_stack_remove(&gs_ui_stack, i);
        gs_ui_unref_screen(gs.L, &u->sc);
        if (u->dialog_fn >= 0) luaL_unref(gs.L, LUA_REGISTRYINDEX, u->dialog_fn);
        memset(u, 0, sizeof *u);
    }
}

/* ---- events ----------------------------------------------------------------------------------------- */
static void gs_ui_dialog_press(int slot, int btn) {
    GsUiSlot *u = &gs_ui_slot[slot];
    lua_State *L = gs.L;
    int i, hit = 0;
    for (i = 0; i < u->view.dialog.n; i++) if (u->view.dialog.btn[i] == btn) hit = 1;
    if (!hit) return;
    u->view.dialog.open = 0;
    if (u->dialog_fn >= 0 && gs_may_run(u->owner)) {
        char one[2];
        one[0] = (char) btn; one[1] = '\0';
        lua_rawgeti(L, LUA_REGISTRYINDEX, u->dialog_fn);
        if (lua_isfunction(L, -1)) { lua_pushstring(L, one); (void) gs_pcall(u->owner, 1, 0, "ui:dialog"); } else lua_pop(L, 1);
    }
}

static void gs_ui_event(int slot, const AtEvent *e) {
    GsUiSlot *u = &gs_ui_slot[slot];
    AtFocusBlock fb[AT_MAX_BLOCKS];
    AtFocusPos before = u->view.focus;
    const char *cid, *bid;
    char cell[AT_ID], block[AT_ID];
    int nb, alt;
    if (u->view.dialog.open) {                                    /* a dialog takes every event until it is answered */
        if (e->type == AT_EV_ACCEPT) gs_ui_dialog_press(slot, 'A');
        else if (e->type == AT_EV_BACK) gs_ui_dialog_press(slot, 'B');
        else if (e->type == AT_EV_ALT) gs_ui_dialog_press(slot, e->a);
        return;
    }
    nb = at_screen_focus_blocks(&u->sc, fb);
    if (e->type == AT_EV_MOVE) u->view.focus = at_focus_move(fb, nb, u->view.focus, e->a, 1);
    else if (e->type == AT_EV_SCROLL && u->sc.primary == AT_PRIMARY_LIST) u->view.focus = at_focus_move(fb, nb, u->view.focus, e->a < 0 ? AT_DIR_UP : AT_DIR_DOWN, 0);
    else if (e->type == AT_EV_FOCUS) {
        AtFocusPos p;
        p.block = e->a; p.index = e->b;
        if (at_screen_cell_id(&u->sc, p) != NULL) u->view.focus = p;
    }
    if (u->sc.primary == AT_PRIMARY_LIST && u->view.focus.index >= 0) {
        int visible = (int) ((362.0f - 28.0f) / 39.0f);
        u->view.scroll = at_list_scroll(u->view.focus.index, u->view.scroll, visible, u->sc.n_items);
    }
    cid = at_screen_cell_id(&u->sc, u->view.focus);
    bid = at_screen_block_id(&u->sc, u->view.focus.block);
    snprintf(cell, sizeof cell, "%s", cid != NULL ? cid : "");
    snprintf(block, sizeof block, "%s", bid != NULL ? bid : "");
    cid = cell[0] ? cell : NULL;
    bid = block[0] ? block : NULL;
    if (u->view.focus.block != before.block || u->view.focus.index != before.index) {
        u->explain_dirty = 1;
        if (u->sc.fn_focus >= 0 && cid != NULL && gs_ui_call(slot, u->sc.fn_focus, cid, bid, 1)) lua_pop(gs.L, 1);
        return;
    }
    if (e->type == AT_EV_ACCEPT) {
        if (u->sc.fn_accept >= 0 && cid != NULL && at_cell_accepts(&u->sc, u->view.focus) && gs_ui_call(slot, u->sc.fn_accept, cid, bid, 1)) gs_ui_apply_result();
    } else if (e->type == AT_EV_BACK) {
        if (u->sc.fn_back >= 0 && gs_ui_call(slot, u->sc.fn_back, cid, bid, 1)) gs_ui_apply_result();
    } else if (e->type == AT_EV_ALT) {
        alt = e->a == 'X' ? 0 : e->a == 'Y' ? 1 : 2;
        if (u->sc.fn_alt[alt] >= 0 && gs_ui_call(slot, u->sc.fn_alt[alt], cid, bid, 1)) gs_ui_apply_result();
    }
}

/* once per script tick, before on_tick: the top screen's input, then its explainer refresh */
static void gs_ui_tick(void) {
    int top = at_stack_top(&gs_ui_stack), n, i;
    AtEvent ev[16];
    double now = gs_now_ms();
    GsUiSlot *u;
    if (top < 0) return;
    u = &gs_ui_slot[top];
    if (!u->used) { at_stack_remove(&gs_ui_stack, top); return; }
    if (!gs_may_run(u->owner)) return;
    if (at_screen_wants_pad(&u->sc)) {
        unsigned b;
        int sx, sy, cx, cy, tl, tr;
        gw_script_pad_state(u->sc.port - 1, &b, &sx, &sy, &cx, &cy, &tl, &tr);
        b = gw_script_pad_raw_buttons(u->sc.port - 1);
        n = at_pad_events(&u->pad, b, sx, sy, now, ev, 16);
        for (i = 0; i < n && at_stack_top(&gs_ui_stack) == top; i++) gs_ui_event(top, &ev[i]);
    }
    if (at_stack_top(&gs_ui_stack) != top) return;
    {
        unsigned m = 0;
        if (gs.key_now[VK_UP]) m |= AT_KEY_UP;
        if (gs.key_now[VK_DOWN]) m |= AT_KEY_DOWN;
        if (gs.key_now[VK_LEFT]) m |= AT_KEY_LEFT;
        if (gs.key_now[VK_RIGHT]) m |= AT_KEY_RIGHT;
        if (gs.key_now[VK_RETURN]) m |= AT_KEY_ENTER;
        if (gs.key_now[VK_ESCAPE]) m |= AT_KEY_ESC;
        if (gs.key_now[VK_TAB]) m |= AT_KEY_TAB;
        if (gs.key_now[VK_SHIFT]) m |= AT_KEY_SHIFT;
        n = at_key_events(&u->keys, m, now, ev, 16);
        for (i = 0; i < n && at_stack_top(&gs_ui_stack) == top; i++) gs_ui_event(top, &ev[i]);
    }
    if (at_stack_top(&gs_ui_stack) != top) return;
    {
        float x, y, wheel;
        int buttons;
        gw_Mouse_ScriptRead(&x, &y, &buttons, &wheel);
        n = at_mouse_events(&u->mouse, x, y, buttons, (int) wheel, &u->hits, ev, 16);
        for (i = 0; i < n && at_stack_top(&gs_ui_stack) == top; i++) gs_ui_event(top, &ev[i]);
    }
    if (at_stack_top(&gs_ui_stack) == top && u->explain_dirty) gs_ui_refresh_view(top);
}

/* the draw pass: called from gs_finish_draw after the scripts' on_draw hooks */
static void gs_ui_draw(void) {
    int top = at_stack_top(&gs_ui_stack), first, old, quads;
    LARGE_INTEGER t0, t1, fq;
    AtTextOps ops;
    AtSink sink;
    GsUiSlot *u;
    double ms;
    if (top < 0 || !gs_ui_roles_ok()) return;
    u = &gs_ui_slot[top];
    if (!u->used) return;
    if (gw_Kit_QuadRoom() < AT_SCREEN_QUAD_CAP) {
        if (!u->warned) { u->warned = 1; gw_log("ui: %s not drawn: only %d quads left this frame", u->sc.id, gw_Kit_QuadRoom()); }
        return;
    }
    old = gs.cur;
    gs.cur = u->owner;
    QueryPerformanceCounter(&t0);
    ops.width = gs_ui_width; ops.user = NULL;
    sink.user = NULL; sink.poly = gs_ui_poly; sink.text = gs_ui_text; sink.model = gs_ui_model_draw;
    first = gw_Kit_QuadCount();
    gs_ui_stat.canvas_w = gw_Console_ScriptWidth();
    at_render(&u->sc, &u->view, gs_ui_stat.canvas_w, gs_now_ms(), gw_Settings_Int("reduced_motion", 0) != 0, &ops, &sink, &u->hits);
    quads = gw_Kit_QuadCount() - first;
    gs_kit_record(first, quads);
    QueryPerformanceCounter(&t1);
    QueryPerformanceFrequency(&fq);
    ms = 1000.0 * (double) (t1.QuadPart - t0.QuadPart) / (double) fq.QuadPart;
    gs_ui_stat.quads = quads;
    gs_ui_stat.sum += ms; gs_ui_stat.frames++;
    if (ms > gs_ui_stat.max) gs_ui_stat.max = ms;
    if (quads > AT_SCREEN_QUAD_WARN && !u->warned) { u->warned = 1; gw_log("ui: %s drew %d quads (warning line %d, cap %d)", u->sc.id, quads, AT_SCREEN_QUAD_WARN, AT_SCREEN_QUAD_CAP); }
    gs.cur = old;
}

/* ---- the Lua functions -------------------------------------------------------------------------------- */
static int l_ui_available(lua_State *L) {
    int ok = gs_ui_roles_ok();
    lua_pushboolean(L, ok);
    lua_pushstring(L, ok ? "" : (gw_Kit_Available() ? "the Atlas text roles are missing from the font manifest" : gw_Kit_Why()));
    return 2;
}

static int l_ui_screen(lua_State *L) {
    char err[200], owner[64];
    int root, slot, nkeep, keep[40], replace = 0;
    GsUiSlot *u;
    AtFocusPos old;
    char old_block[AT_ID], old_cell[AT_ID];
    luaL_checktype(L, 1, LUA_TTABLE);
    atv_init(&gs_ui_arena);
    root = gs_ui_copy(L, 1, 0);
    if (root < 0 || gs_ui_arena.overflow) {
        gs_ui_unref_arena_except(L, NULL, 0);
        return luaL_error(L, "gd.ui.screen: the description is too large or nested too deeply");
    }
    if (!at_screen_from_val(&gs_ui_arena, root, gs_ui_owner_mod(owner, sizeof owner), &gs_ui_scratch, err, sizeof err)) {
        gs_ui_unref_arena_except(L, NULL, 0);
        return luaL_error(L, "%s", err);
    }
    nkeep = at_screen_fn_refs(&gs_ui_scratch, keep, 40);
    gs_ui_unref_arena_except(L, keep, nkeep);                     /* every reference the screen does not keep goes */
    slot = gs_ui_find(gs_ui_scratch.id);
    if (slot < 0) {
        int i;
        for (i = 0; i < GS_UI_SLOTS; i++) if (!gs_ui_slot[i].used) { slot = i; break; }
        if (slot < 0) {
            gs_ui_unref_screen(L, &gs_ui_scratch);
            return luaL_error(L, "gd.ui.screen: too many screens (%d)", GS_UI_SLOTS);
        }
    }
    u = &gs_ui_slot[slot];
    if (u->used) {
        if (u->owner != gs.cur) { gs_ui_unref_screen(L, &gs_ui_scratch); return luaL_error(L, "gd.ui.screen: \"%s\" belongs to another script", u->sc.id); }
        replace = 1;
        old = u->view.focus;
        snprintf(old_block, sizeof old_block, "%s", at_screen_block_id(&u->sc, old.block) != NULL ? at_screen_block_id(&u->sc, old.block) : "");
        snprintf(old_cell, sizeof old_cell, "%s", at_screen_cell_id(&u->sc, old) != NULL ? at_screen_cell_id(&u->sc, old) : "");
        gs_ui_unref_screen(L, &u->sc);
    } else {
        memset(u, 0, sizeof *u);
        at_view_init(&u->view);
        u->dialog_fn = -1;
    }
    u->sc = gs_ui_scratch;
    u->used = 1;
    u->owner = gs.cur;
    if (replace) u->view.focus = at_screen_refocus(&u->sc, old_block[0] ? old_block : NULL, old_cell[0] ? old_cell : NULL, old);
    else { AtFocusBlock fb[AT_MAX_BLOCKS]; u->view.focus = at_focus_first(fb, at_screen_focus_blocks(&u->sc, fb)); }
    u->explain_dirty = 1;
    lua_pushboolean(L, 1);
    return 1;
}

static int gs_ui_slot_arg(lua_State *L, int idx) {
    int s = gs_ui_find(luaL_checkstring(L, idx));
    if (s < 0) luaL_error(L, "gd.ui: no screen \"%s\"", lua_tostring(L, idx));
    return s;
}

static int l_ui_open(lua_State *L) { lua_pushboolean(L, gs_ui_open_screen(gs_ui_slot_arg(L, 1))); return 1; }

static int l_ui_close(lua_State *L) {
    int s = lua_isstring(L, 1) ? gs_ui_slot_arg(L, 1) : at_stack_top(&gs_ui_stack);
    if (s >= 0) gs_ui_close_screen(s);
    lua_pushboolean(L, s >= 0);
    return 1;
}

static int l_ui_feed(lua_State *L) {
    int s = gs_ui_slot_arg(L, 1);
    const char *k = luaL_checkstring(L, 2);
    AtEvent e;
    memset(&e, 0, sizeof e);
    if (strcmp(k, "up") == 0) { e.type = AT_EV_MOVE; e.a = AT_DIR_UP; }
    else if (strcmp(k, "down") == 0) { e.type = AT_EV_MOVE; e.a = AT_DIR_DOWN; }
    else if (strcmp(k, "left") == 0) { e.type = AT_EV_MOVE; e.a = AT_DIR_LEFT; }
    else if (strcmp(k, "right") == 0) { e.type = AT_EV_MOVE; e.a = AT_DIR_RIGHT; }
    else if (strcmp(k, "accept") == 0) e.type = AT_EV_ACCEPT;
    else if (strcmp(k, "back") == 0) e.type = AT_EV_BACK;
    else if (strcmp(k, "x") == 0 || strcmp(k, "y") == 0 || strcmp(k, "z") == 0) { e.type = AT_EV_ALT; e.a = k[0] - 'a' + 'A'; }
    else return luaL_error(L, "gd.ui.feed: unknown intent \"%s\" (up down left right accept back x y z)", k);
    gs_ui_event(s, &e);
    if (gs_ui_slot[s].used && gs_ui_slot[s].explain_dirty) gs_ui_refresh_view(s);
    lua_pushboolean(L, 1);
    return 1;
}

static int l_ui_focus(lua_State *L) {
    int s = gs_ui_slot_arg(L, 1);
    const GsUiSlot *u = &gs_ui_slot[s];
    const char *c = at_screen_cell_id(&u->sc, u->view.focus), *b = at_screen_block_id(&u->sc, u->view.focus.block);
    if (c == NULL) { lua_pushnil(L); return 1; }
    lua_pushstring(L, c);
    lua_pushstring(L, b != NULL ? b : "");
    return 2;
}

static int l_ui_set_focus(lua_State *L) {
    int s = gs_ui_slot_arg(L, 1);
    GsUiSlot *u = &gs_ui_slot[s];
    AtFocusPos p = at_screen_refocus(&u->sc, luaL_checkstring(L, 2), luaL_checkstring(L, 3), u->view.focus);
    const char *c = at_screen_cell_id(&u->sc, p);
    int ok = c != NULL && strcmp(c, lua_tostring(L, 3)) == 0;
    if (ok) { u->view.focus = p; u->explain_dirty = 1; }
    lua_pushboolean(L, ok);
    return 1;
}

static int l_ui_note(lua_State *L) {
    int top = at_stack_top(&gs_ui_stack);
    GsUiSlot *u;
    const char *kind;
    double secs;
    luaL_checktype(L, 1, LUA_TTABLE);
    if (top < 0) { lua_pushboolean(L, 0); return 1; }
    u = &gs_ui_slot[top];
    lua_getfield(L, 1, "text");
    snprintf(u->view.note.text, AT_STR, "%s", luaL_optstring(L, -1, ""));
    lua_pop(L, 1);
    lua_getfield(L, 1, "kind");
    kind = luaL_optstring(L, -1, "info");
    u->view.note.kind = strcmp(kind, "ok") == 0 ? AT_NOTE_OK : strcmp(kind, "warn") == 0 ? AT_NOTE_WARN : strcmp(kind, "err") == 0 ? AT_NOTE_ERR : AT_NOTE_INFO;
    lua_pop(L, 1);
    secs = gs_kit_optnum(L, 1, "seconds", 3.0);
    if (secs < 0.5) secs = 0.5;
    if (secs > 15.0) secs = 15.0;
    u->view.note.from_ms = gs_now_ms();
    u->view.note.until_ms = u->view.note.from_ms + secs * 1000.0;
    lua_pushboolean(L, 1);
    return 1;
}

static int gs_ui_btn_char(const char *s) { return (s != NULL && s[0] != '\0' && strchr("ABXYZ", s[0]) != NULL) ? s[0] : 'A'; }

static int l_ui_dialog(lua_State *L) {
    int top = at_stack_top(&gs_ui_stack), i, n;
    GsUiSlot *u;
    luaL_checktype(L, 1, LUA_TTABLE);
    if (top < 0) { lua_pushboolean(L, 0); return 1; }
    u = &gs_ui_slot[top];
    if (u->dialog_fn >= 0) { luaL_unref(L, LUA_REGISTRYINDEX, u->dialog_fn); u->dialog_fn = -1; }
    memset(&u->view.dialog, 0, sizeof u->view.dialog);
    lua_getfield(L, 1, "title");
    snprintf(u->view.dialog.title, AT_STR, "%s", luaL_optstring(L, -1, ""));
    lua_pop(L, 1);
    lua_getfield(L, 1, "text");
    snprintf(u->view.dialog.body, AT_TEXT, "%s", luaL_optstring(L, -1, ""));
    lua_pop(L, 1);
    lua_getfield(L, 1, "actions");
    n = lua_istable(L, -1) ? (int) lua_rawlen(L, -1) : 0;
    if (n > 2) n = 2;
    for (i = 1; i <= n; i++) {
        lua_rawgeti(L, -1, i);
        if (lua_istable(L, -1)) {
            lua_rawgeti(L, -1, 1);
            u->view.dialog.btn[i - 1] = (char) gs_ui_btn_char(luaL_optstring(L, -1, "A"));
            lua_pop(L, 1);
            lua_rawgeti(L, -1, 2);
            snprintf(u->view.dialog.label[i - 1], 24, "%s", luaL_optstring(L, -1, ""));
            lua_pop(L, 1);
        }
        lua_pop(L, 1);
    }
    lua_pop(L, 1);
    lua_getfield(L, 1, "on");
    if (lua_isfunction(L, -1)) u->dialog_fn = luaL_ref(L, LUA_REGISTRYINDEX); else lua_pop(L, 1);
    u->view.dialog.n = n;
    u->view.dialog.focus = 0;
    u->view.dialog.from_ms = gs_now_ms();
    u->view.dialog.open = n > 0;
    lua_pushboolean(L, n > 0);
    return 1;
}

static int l_ui_state(lua_State *L) {
    int top = at_stack_top(&gs_ui_stack);
    AtLayout lay;
    lua_newtable(L);
    lua_pushinteger(L, gs_ui_stack.n); lua_setfield(L, -2, "depth");
    if (top >= 0) { lua_pushstring(L, gs_ui_slot[top].sc.id); lua_setfield(L, -2, "top"); }
    lua_pushnumber(L, gs_ui_stat.canvas_w); lua_setfield(L, -2, "canvas_w");
    at_layout(gs_ui_stat.canvas_w > 0.0f ? gs_ui_stat.canvas_w : 640.0f, AT_PRESET_NORMAL, &lay);
    lua_pushboolean(L, lay.wide); lua_setfield(L, -2, "wide");
    lua_pushinteger(L, gs_ui_stat.quads); lua_setfield(L, -2, "quads");
    lua_pushnumber(L, gs_ui_stat.frames > 0 ? gs_ui_stat.sum / (double) gs_ui_stat.frames : 0.0); lua_setfield(L, -2, "cost_ms");
    lua_pushnumber(L, gs_ui_stat.max); lua_setfield(L, -2, "cost_max_ms");
    lua_pushboolean(L, gs_ui_roles_state > 0); lua_setfield(L, -2, "roles_ok");
    return 1;
}

static const luaL_Reg gs_ui_funcs[] = {
    {"available", l_ui_available}, {"screen", l_ui_screen}, {"open", l_ui_open}, {"close", l_ui_close},
    {"feed", l_ui_feed}, {"focus", l_ui_focus}, {"set_focus", l_ui_set_focus}, {"note", l_ui_note},
    {"dialog", l_ui_dialog}, {"state", l_ui_state}, {NULL, NULL}};

static void gs_push_ui(lua_State *L) {
    lua_newtable(L);
    gs_prof_setfuncs(L, gs_ui_funcs, "gd.ui");
}
```

Then edit `gw_script.c` (verify each line number with `grep -n` first; they drift):
  1. Directly after the line `static void gs_prof_setfuncs(lua_State *L, const luaL_Reg *funcs, const char *prefix);` (about line 6258) add `#include "gw_script_ui.inc"`.
  2. In `gs_finish_draw` (about line 7597), after `gs_hook_all("on_draw", 0, 0, 0);` add `gs_ui_draw();`.
  3. In `gw_Script_Tick` (about line 7660), immediately before `gs_hook_all("on_tick", 0, 0, 0);` add `gs_ui_tick();`.
  4. After `gs_push_kit(L);` / `lua_setfield(L, -2, "kit");` (about line 6787) add `gs_push_ui(L);` and `lua_setfield(L, -2, "ui");`.
  5. In the private-copy block (about line 6843), directly after the four lines for `"kit"` (`lua_getfield(L, -1, "kit"); gs_copy_deep(L, -1, 3); lua_setfield(L, -3, "kit"); lua_pop(L, 1);`) add the same four lines with `"ui"` and depth `2`.
  6. In `gs_unload` (about line 6946), after `gs_contact_release(i);` add `gs_ui_release(i);`.

Add the Reduced motion row. In `melee/src/melee/gm/gmfrontend_settings.inc`, above `static const FrontendItem fe_items_set_video[]` add:

```c
static int fsv_get_reduced(void) { return Settings_Int("reduced_motion", 0) != 0; }
static void fsv_set_reduced(int v) { Settings_SetInt("reduced_motion", v); }
```

and append to the end of `fe_items_set_video[]` (after the `Show FPS` entry):

```c
    { FE_TOGGLE, 0, "Reduced Motion", "Menus cut instead of fading, and models stop turning. Applies to the new menus.",
      fsv_get_reduced, fsv_set_reduced, 0, 1, 1 },
```

Add to `tools/port/linux_shims.txt` (workspace repo), in alphabetical position among the `gw_*` lines: `gw_ui_focus.c`, `gw_ui_input.c`, `gw_ui_layout.c`, `gw_ui_parts.c`, `gw_ui_render.c`, `gw_ui_screen.c`, `gw_ui_stack.c`, `gw_ui_val.c`.

- [ ] **Step 4: Run the tests.** First the host-side one, which needs no game:

```bash
nt atlas-binding
```

Expected: `atlas binding: 40 checks, 0 failed` (about a minute: it compiles Lua). Then the build and the in-exe check:

```bash
tools/port/build.sh --shim gw_script.c --tu src/melee/gm/gmfrontend.c
MELEE_TEST_FILTER=script_ui_binding tools/port/run.sh --test atlas-ui --iso "$GW_ISO_VANILLA"
grep -a "TESTS" "$GW_BUILD_ROOT/runs/atlas-ui/melee-pc.log" | tail -5
```

Expected: the build links with the bridge fixpoint message (`gmfrontend.c` is the translation unit that includes `gmfrontend_settings.inc`; the PowerPC syntax check from the root `CLAUDE.md` is an acceptable extra), then the log shows `script_ui_binding` passing and `failures=0`. If the Atlas fonts are not built yet, `gw_Kit_Available()` can still be true while `gs_ui_roles_ok()` is false (Task 15 adds the roles): `gd.ui.screen` still registers (it needs no fonts), the test passes, and `gd.ui.available()` returns false, which is the intended fallback.

Then the guard checks that pin Review Focus 5 (online):

```bash
grep -c "gs_may_run" "$GW_MELEE/pc/platform/gw_script_ui.inc"        # at least 2
grep -c "input_mask\|pad_mask\|input_chord" "$GW_MELEE/pc/platform/gw_script_ui.inc"   # exactly 0 (the engine never masks the pad)
```

Expected: a number of 2 or more, then `0`.

- [ ] **Step 5: Commit.** Game repo: `git -C "$GW_MELEE" add pc/platform/gw_script_ui.inc pc/platform/gw_script.c src/melee/gm/gmfrontend_settings.inc pc/tests/atlas_binding_test.c`, message `gd.ui: the Atlas screen binding, the host sink, the tick and draw passes; a Reduced Motion setting

Built and unit-tested in the exe; not played. gd.ui is presentation only: no input masking, no hooks on resimulated frames.` with the trailers. Workspace repo: `git add tools/port/linux_shims.txt tools/port/native_test.sh`, message `atlas: the atlas-binding native test case; the gw_ui_* units in the Linux shim list`.

### Task 12: An offline `gd.ui` stand-in with the same contract

**Files:**
- Create (game repo): `melee/pc/tests/atlas_ui_stub.lua`, `melee/pc/tests/atlas_ui_stub_test.lua`

**Interfaces:**
Consumes: `melee/pc/platform/gw_ui_screen.h` (read as text for the limits `AT_MAX_BLOCKS`, `AT_MAX_CELLS`, `AT_MAX_ITEMS`, `AT_MAX_KEYS`).
Produces: `Stub.new(opts)` returning a table that answers every `gd.ui` function of Task 11 (`available screen open close feed focus set_focus note dialog state`) and records what happened, plus the engine's part for tests: `ui.engine_focus(id, block, cell)`, `ui.engine_press(id, 'accept'|'back'|'x'|'y'|'z')`, `ui.refresh(id)`, and the readable fields `ui.screens[id]`, `ui.views[id]` (`{explainer=, keys={{btn,label}...}, counter=}`), `ui.stack`, `ui.fed`, `ui.notes`, `ui.dialogs`, `ui.refreshed` (a count of registrations). `Stub.limits` is `{blocks=6, cells=12, items=32, keys=6, with=4}` as read from the C header. It validates like `at_screen_from_val` (Task 5) and re-focuses by cell id like `at_screen_refocus`; the C side is the authority, the stub is the same contract for offline Lua tests (the limits cannot drift because they are read from the header).

- [ ] **Step 1: Write the failing test.** Create `melee/pc/tests/atlas_ui_stub_test.lua`:

```lua
-- cd "$GW_MELEE" && lua pc/tests/atlas_ui_stub_test.lua   (it also runs from a directory that holds melee/)
local prefix = io.open('pc/tests/atlas_ui_stub.lua') and '' or 'melee/'
local Stub = dofile(prefix .. 'pc/tests/atlas_ui_stub.lua')
local fails, count = 0, 0
local function check(cond, msg) count = count + 1; if not cond then fails = fails + 1; print('FAIL: ' .. msg) end end
local function raises(f, part, msg) local ok, e = pcall(f); check(not ok and tostring(e):find(part, 1, true), msg .. ' (got ' .. tostring(e) .. ')') end

local L = Stub.limits
check(L.blocks == 6 and L.cells == 12 and L.items == 32 and L.keys == 6, 'limits are read from gw_ui_screen.h')

local function cell(id, extra) local c = { id = id, name = id }; for k, v in pairs(extra or {}) do c[k] = v end; return c end
local function grid(id, bags)
  return { id = id, primary = { kind = 'grid', blocks = {
    { id = 'eq', title = 'EQUIPPED', cols = 6, cells = { cell('eq:1'), cell('eq:2'), cell('eq:3', { flags = { locked = true } }) } },
    { id = 'bag', title = 'BAG', cols = 4, cells = bags or { cell('bag:1'), cell('bag:2'), cell('bag:3') } } } },
    keys = { { 'A', 'Pick' }, { 'B', 'Close' } } }
end

local ui = Stub.new()
check(ui.available() == true, 'available')
raises(function() ui.screen({}) end, 'no id', 'an id is required')
raises(function() ui.screen({ id = 'x.a', primary = { kind = 'tiles' } }) end, 'not supported', 'only grid and list')
raises(function() ui.screen({ id = 'x.a', primary = { kind = 'grid', blocks = {} } }) end, 'blocks', 'a grid needs blocks')
raises(function() ui.screen({ id = 'x.a', primary = { kind = 'grid', blocks = { { id = 'b', cols = 2, cells = { cell('c'), cell('c') } } } } }) end, 'duplicate', 'cell ids are unique')
raises(function() ui.screen({ id = 'x.a', primary = { kind = 'grid', blocks = { { id = 'b', cols = 20, cells = {} } } } }) end, 'cols', 'cols is bounded')
local d = grid('x.a'); d.keys[#d.keys + 1] = { 'Q', 'No' }
raises(function() ui.screen(d) end, 'button', 'key buttons are checked')
local seven = { id = 'x.a', primary = { kind = 'grid', blocks = {} } }
for i = 1, 7 do seven.primary.blocks[i] = { id = 'b' .. i, cols = 1, cells = {} } end
raises(function() ui.screen(seven) end, 'blocks', 'at most six blocks')

check(ui.screen(grid('x.a')), 'a good grid registers')
local c, b = ui.focus('x.a'); check(c == 'eq:1' and b == 'eq', 'focus starts on the first cell')
ui.open('x.a'); check(ui.state().top == 'x.a' and ui.state().depth == 1, 'open pushes')

-- focus is kept by id across a re-registration; a gone cell clamps to the same block; a gone block falls to the first cell
ui.set_focus('x.a', 'bag', 'bag:3')
ui.screen(grid('x.a')); c = ui.focus('x.a'); check(c == 'bag:3', 'same id: same cell')
ui.screen(grid('x.a', { cell('bag:1'), cell('bag:2') })); c = ui.focus('x.a'); check(c == 'bag:2', 'gone: clamped to the same block, got ' .. tostring(c))
local g2 = grid('x.a'); table.remove(g2.primary.blocks, 2); ui.screen(g2); c = ui.focus('x.a'); check(c == 'eq:1', 'block gone: the first cell, got ' .. tostring(c))

-- the engine's part: on.focus, the provider and key/counter functions, dispatch, disabled cells
local log = {}
local e = grid('x.b')
e.explainer = { width = 'narrow', provide = function(cid, bid) return { title = cid .. '@' .. bid } end }
e.keys = { { 'A', function(cid) return cid == 'eq:1' and 'First' or 'Other' end }, { 'X', 'Hidden', when = function(cid) return cid ~= 'eq:1' end }, { 'B', 'Close' } }
e.counter = function(cid) return 'at ' .. cid end
e.primary.blocks[1].cells[2].flags = { disabled = true }
e.on = { focus = function(cid, bid) log[#log + 1] = 'focus ' .. cid .. ' ' .. bid end, accept = function(cid, bid) log[#log + 1] = 'accept ' .. cid; return nil end,
         back = function() log[#log + 1] = 'back' end, alt = { X = function(cid) log[#log + 1] = 'x ' .. cid end } }
ui.screen(e)
local v = ui.refresh('x.b')
check(v.explainer.title == 'eq:1@eq' and v.counter == 'at eq:1', 'provider and counter get the focused ids')
check(#v.keys == 2 and v.keys[1][2] == 'First' and v.keys[2][1] == 'B', 'a key whose when() is false is hidden')
ui.engine_focus('x.b', 'bag', 'bag:2')
check(log[1] == 'focus bag:2 bag' and ui.views['x.b'].keys[1][2] == 'Other' and #ui.views['x.b'].keys == 3, 'engine_focus runs on.focus then refreshes the view')
check(ui.engine_press('x.b', 'accept') and log[2] == 'accept bag:2', 'accept reaches the handler with the cell id')
ui.engine_focus('x.b', 'eq', 'eq:2')
check(not ui.engine_press('x.b', 'accept'), 'a disabled cell is focusable but never fires'); check(#log == 3, 'and nothing was logged for it')
check(ui.engine_press('x.b', 'x') and log[4] == 'x eq:2', 'alt X reaches its handler'); check(ui.engine_press('x.b', 'back'), 'back')
check(not ui.engine_press('x.b', 'y'), 'no handler: nothing')
ui.feed('x.b', 'down'); check(ui.fed[1][1] == 'x.b' and ui.fed[1][2] == 'down', 'feed is recorded')
ui.note({ text = 'hi' }); ui.dialog({ title = 'T' }); check(#ui.notes == 1 and #ui.dialogs == 1, 'notes and dialogs are recorded')
ui.close('x.a'); check(ui.state().depth == 0, 'close removes the screen')
local off = Stub.new({ available = false }); check(select(1, off.available()) == false, 'an unavailable stub says so')
print(('atlas ui stub: %d checks, %d failed'):format(count, fails))
os.exit(fails == 0 and 0 or 1)
```

- [ ] **Step 2: Run it to verify it fails.**

```bash
cd "$GW_MELEE" && lua pc/tests/atlas_ui_stub_test.lua
```

Expected: `cannot open pc/tests/atlas_ui_stub.lua` (the test finds the stub relative to the game checkout, so run it from there: your lane's `$GW_MELEE`, not the workspace root).

- [ ] **Step 3: Write the minimal implementation.** Create `melee/pc/tests/atlas_ui_stub.lua`:

```lua
-- A gd.ui stand-in for offline tests (Atlas step 1). It enforces the contract of gw_ui_screen.c (the limits are read from
-- that header so the two cannot drift) and plays the engine's part where a test needs it: focus by cell id, on.focus, the
-- explainer / key label / counter refresh, and accept / back / alt dispatch.
local Stub = {}

local function read_limits()
 local here = (arg and arg[0] or ''):gsub('\\', '/'):gsub('[^/]*$', '')
 for _, p in ipairs({ here .. '../platform/gw_ui_screen.h', 'pc/platform/gw_ui_screen.h', 'melee/pc/platform/gw_ui_screen.h' }) do
  local f = io.open(p)
  if f then
   local text = f:read('a'); f:close()
   local L = {}
   for name, v in text:gmatch('#define%s+AT_MAX_(%u+)%s+(%d+)') do L[name:lower()] = tonumber(v) end
   return L
  end
 end
 error('gw_ui_screen.h not found')
end
Stub.limits = read_limits()
local BUTTONS = { A = true, B = true, X = true, Y = true, Z = true, L = true, R = true, START = true }

local function disabled(c) return (c.flags and c.flags.disabled) or c.disabled end

function Stub.new(opts)
 opts = opts or {}
 local L = Stub.limits
 local ui = { screens = {}, stack = {}, views = {}, fed = {}, notes = {}, dialogs = {}, refreshed = 0, _f = {}, available_ok = opts.available ~= false }
 local function fail(msg) error('gd.ui.screen: ' .. msg, 3) end

 -- every focusable cell in focus order: { block =, id =, cell =, index = (1-based within its block) }
 local function flat(d)
  local out, p = {}, d.primary
  if p.kind == 'grid' then
   for _, b in ipairs(p.blocks) do for i, c in ipairs(b.cells or {}) do out[#out + 1] = { block = b.id, id = c.id, cell = c, index = i } end end
  else
   for i, it in ipairs(p.items) do out[#out + 1] = { block = 'list', id = it.id, cell = it, index = i } end
  end
  return out
 end

 function ui.available() return ui.available_ok, ui.available_ok and '' or 'stub: unavailable' end

 function ui.screen(d)
  if type(d) ~= 'table' then fail('a screen description is a table') end
  if type(d.id) ~= 'string' or d.id == '' then fail('the description has no id') end
  local p = d.primary
  if type(p) ~= 'table' then fail('"' .. d.id .. '" has no primary') end
  local seen = {}
  if p.kind == 'grid' then
   local n = #(p.blocks or {})
   if n < 1 or n > L.blocks then fail(('a grid needs 1 to %d blocks (it has %d)'):format(L.blocks, n)) end
   for _, b in ipairs(p.blocks) do
    if type(b.id) ~= 'string' or b.id == '' then fail('a block has no id') end
    if (b.cols or 1) < 1 or (b.cols or 1) > L.cells then fail('block "' .. b.id .. '": cols is 1 to ' .. L.cells) end
    if #(b.cells or {}) > L.cells then fail(('block "%s" has %d cells (%d at most)'):format(b.id, #b.cells, L.cells)) end
    for _, c in ipairs(b.cells or {}) do
     if type(c.id) ~= 'string' or c.id == '' then fail('a cell has no id') end
     if seen[c.id] then fail('duplicate cell id "' .. c.id .. '"') end
     seen[c.id] = true
    end
   end
  elseif p.kind == 'list' then
   local n = #(p.items or {})
   if n < 1 or n > L.items then fail(('a list needs 1 to %d items (it has %d)'):format(L.items, n)) end
   for _, it in ipairs(p.items) do
    if type(it.id) ~= 'string' or it.id == '' then fail('an item has no id') end
    if seen[it.id] then fail('duplicate item id "' .. it.id .. '"') end
    seen[it.id] = true
   end
  else
   fail(('primary kind "%s" is not supported here (grid or list)'):format(tostring(p.kind)))
  end
  if d.keys and #d.keys > L.keys then fail(('at most %d key hints (%d given)'):format(L.keys, #d.keys)) end
  for i, k in ipairs(d.keys or {}) do
   local b = k[1] or k.btn
   if not BUTTONS[b] then fail(('key hint %d: unknown button "%s" (A B X Y Z L R START)'):format(i, tostring(b))) end
  end
  local old = ui.screens[d.id] and ui._f[d.id]
  ui.screens[d.id] = d
  ui.refreshed = ui.refreshed + 1
  local all, pick = flat(d), nil
  if old then
   for _, e in ipairs(all) do if e.block == old.block and e.id == old.cell then pick = e end end
   if not pick then   -- gone: the same block, the same place clamped (at_screen_refocus)
    local inblock = {}
    for _, e in ipairs(all) do if e.block == old.block then inblock[#inblock + 1] = e end end
    if #inblock > 0 then pick = inblock[math.min(old.index or 1, #inblock)] end
   end
  end
  pick = pick or all[1]
  ui._f[d.id] = pick and { block = pick.block, cell = pick.id, index = pick.index } or nil
  return true
 end

 function ui.open(id) assert(ui.screens[id], 'gd.ui: no screen "' .. tostring(id) .. '"'); ui.stack[#ui.stack + 1] = id; ui.refresh(id); return true end
 function ui.close(id)
  id = id or ui.stack[#ui.stack]
  for i = #ui.stack, 1, -1 do if ui.stack[i] == id then table.remove(ui.stack, i) end end
  return id ~= nil
 end
 function ui.feed(id, intent) assert(ui.screens[id], 'gd.ui: no screen "' .. tostring(id) .. '"'); ui.fed[#ui.fed + 1] = { id, intent }; return true end
 function ui.focus(id)
  assert(ui.screens[id], 'gd.ui: no screen "' .. tostring(id) .. '"')
  local f = ui._f[id]
  if not f then return nil end
  return f.cell, f.block
 end
 function ui.set_focus(id, block, cell)
  assert(ui.screens[id], 'gd.ui: no screen "' .. tostring(id) .. '"')
  for _, e in ipairs(flat(ui.screens[id])) do
   if e.block == block and e.id == cell then ui._f[id] = { block = block, cell = cell, index = e.index }; return true end
  end
  return false
 end
 function ui.note(t) ui.notes[#ui.notes + 1] = t; return #ui.stack > 0 end
 function ui.dialog(t) ui.dialogs[#ui.dialogs + 1] = t; return #ui.stack > 0 end
 function ui.state() return { depth = #ui.stack, top = ui.stack[#ui.stack], roles_ok = ui.available_ok } end

 -- ---- the engine's part -------------------------------------------------------------------------------------
 function ui.refresh(id)
  local d, f = ui.screens[id], ui._f[id]
  local cell, block = f and f.cell, f and f.block
  local v = { keys = {} }
  local ex = d.explainer
  if type(ex) == 'table' and type(ex.provide) == 'function' and cell then v.explainer = ex.provide(cell, block) end
  for _, k in ipairs(d.keys or {}) do
   local label = k[2] or k.label
   if type(label) == 'function' then label = label(cell, block) end
   local show = true
   if type(k.when) == 'function' then show = k.when(cell, block) and true or false end
   if show and type(label) == 'string' and label ~= '' then v.keys[#v.keys + 1] = { k[1] or k.btn, label } end
  end
  local c = d.counter
  if type(c) == 'function' then v.counter = c(cell, block) else v.counter = c end
  ui.views[id] = v
  return v
 end

 function ui.engine_focus(id, block, cell)
  local f = ui._f[id]
  if f and f.block == block and f.cell == cell then return false end
  assert(ui.set_focus(id, block, cell), 'no cell ' .. block .. ':' .. cell)
  local on = ui.screens[id].on or {}
  if on.focus then on.focus(cell, block) end      -- the handler may re-register the screen: the refresh below reads the newest one
  ui.refresh(id)
  return true
 end

 function ui.engine_press(id, kind)
  local d, f = ui.screens[id], ui._f[id]
  local on = d.on or {}
  local fn
  if kind == 'accept' then fn = on.accept elseif kind == 'back' then fn = on.back
  elseif kind == 'x' or kind == 'y' or kind == 'z' then fn = on.alt and on.alt[kind:upper()] end
  if kind == 'accept' and f then
   for _, e in ipairs(flat(d)) do if e.block == f.block and e.id == f.cell and disabled(e.cell) then return false end end
  end
  if not fn then return false end
  local r = fn(f and f.cell, f and f.block)
  if ui.screens[id] then ui.refresh(id) end
  return true, r
 end

 return ui
end

return Stub
```

- [ ] **Step 4: Run the tests.**

```bash
cd "$GW_MELEE" && lua pc/tests/atlas_ui_stub_test.lua
```

Expected: `atlas ui stub: 28 checks, 0 failed`.

- [ ] **Step 5: Commit.** Game repo: `pc/tests/atlas_ui_stub.lua`, `pc/tests/atlas_ui_stub_test.lua`, message `atlas: an offline gd.ui stand-in with the C contract's limits and the engine's part`.

---

### Task 13: The Envoy bag as a description (`atlas_bag.lua`)

**Files:**
- Create (game repo): `melee/pc/scripts/examples/envoy/scripts/atlas_bag.lua`, `melee/pc/tests/envoy_atlas_bag.lua`

**Interfaces:**
Consumes: `gd.ui` (Task 11) or the stub (Task 12); from a `RunScreen` instance `S` (`envoy/scripts/run_screen.lua`): `S.g`, `S.mode` (`'bag'`), `S.layout` (`'main'`), `S.active`, `S.confirm`, `S.blocks` (array of `{id, title, cols, rows, cells}`; a cell is `{name, colour, rarity, pips, flags={...}, icon, lines, actions={A,X,Y}, ref, empty}`, `run_screen.lua:61-128`), `S.host:bag():capacity()`, `S.host.seat`, `S.host:plan_take(record, from)`, `S.host:merge_text(plan)`, `S:detail_lines(cell)`, `S:mark_target(cell)`, `S:model_desc(colour, rarity)`, `S:press(action)`, `S:refresh()`, `S:notify(text)`.
Produces:

```lua
local A = D.atlas_bag            -- the module (run_screen.lua reaches it as D.atlas_bag)
A.set(on)                        -- the switch; default off
A.enabled(g) -> boolean          -- on, g.ui exists and g.ui.available() is true
A.attach(S) -> boolean           -- bag mode only; registers 'envoy.bag', opens it, takes over draw/focus/press; false leaves the legacy screen
A.detach(S)                      -- restores the legacy methods and closes the Atlas screen
A.describe(S, self) -> table     -- the gd.ui description
```

Behaviour contract (each line is tested below): ids are positional (`eq:3`, `bag:2`, `key:1`); `'EQUIPPED 5/6'` becomes title `EQUIPPED` and count `5 / 6`; the keystone block is `kind='stones'` with the note `One held`; directions go to the engine (`g.ui.feed`), A/B/X/Y go to the legacy `S:press`, so every rule (merge, equip, discard asks twice, close) stays in `run_screen.lua`; the key hints are the legacy `cell.actions` plus `B Close`; the explainer is the legacy `detail_lines` (first line = the drive's full name, then one line per rule up to the first blank line); a locked or empty cell explains itself and offers only `B`; when `S.layout` leaves `'main'` (the swap screen, still legacy in step 1) the screen detaches and the legacy grid draws; Atlas code never touches the pad mask.

- [ ] **Step 1: Write the failing test.** Create `melee/pc/tests/envoy_atlas_bag.lua`:

```lua
-- Offline tests of the Envoy bag as a gd.ui description:  cd melee && lua pc/tests/envoy_atlas_bag.lua
local prefix = io.open('pc/tests/atlas_ui_stub.lua') and '' or 'melee/'
local Stub = dofile(prefix .. 'pc/tests/atlas_ui_stub.lua')
local T = dofile(prefix .. 'pc/tests/envoy_testlib.lua')
local A = assert(loadfile(T.root .. 'atlas_bag.lua'))()({})
local ID = 'envoy.bag'

local function drive(i, extra)
  local c = { name = 'Drive ' .. i, colour = 'red', pips = 2, flags = {}, icon = { kind = 'model', asset = 100 + i, ring = 150 },
    lines = { 'Magic drive: Burning Red Drive ' .. i, 'Aerial hits set Burning for 3 s.', 'Burning targets take more damage.', '', 'Goes into slot 2.' },
    actions = { A = 'Equip', X = false, Y = 'Discard' }, ref = { kind = 'bag', where = 'bag', index = i, record = { colour = 'red' } } }
  for k, v in pairs(extra or {}) do c[k] = v end
  return c
end
local function blocks()
  local eq = {}
  for i = 1, 5 do eq[i] = drive(i, { ref = { kind = 'eq', where = 'equipped', index = i, record = {} }, actions = { A = 'To bag', X = 'To bag' } }) end
  eq[6] = { name = 'Locked slot', colour = 'grey', flags = { 'locked' }, lines = { 'Slot 6 unlocks at depth 5.' }, ref = { kind = 'locked', index = 6 }, actions = {} }
  local bag = { drive(1, { flags = { 'merge' } }), drive(2), drive(3),
    { empty = true, name = 'Empty slot', lines = { 'Empty bag place.' }, ref = { kind = 'bag', where = 'bag', index = 4, empty = true }, actions = {} } }
  local key = { { name = 'Pyromancer', colour = 'purple', pips = 0, icon = { kind = 'letter', letter = 'P', colour = 0xB872F0FF },
    lines = { 'Keystone rule line.', '', 'Purple keystone.' }, ref = { kind = 'key', id = 'pyro' }, actions = {} } }
  return { { id = 'eq', title = 'EQUIPPED 5/6', cols = 6, rows = 1, cells = eq }, { id = 'bag', title = 'BAG 3/4', cols = 4, rows = 1, cells = bag },
           { id = 'key', title = 'KEYSTONES 1/3', cols = 6, rows = 1, cells = key } }
end

-- a RunScreen look-alike: a class table, so that detaching can fall back to the "legacy" methods
local Class = {}
function Class:refresh() self.log.refreshes = self.log.refreshes + 1 end
function Class:press(a) self.log.pressed[#self.log.pressed + 1] = a; if a == 'accept' then local _, ref = self:focused(); self.log.accepted = ref end end
function Class:draw() self.log.drew = true end
function Class:focused() return nil end
function Class:sync() end
function Class:notify(t) self.log.notices[#self.log.notices + 1] = t end
function Class:mark_target(c) self.log.marked[#self.log.marked + 1] = c.name end
function Class:detail_lines(c) return c.lines or { c.name } end
function Class:model_desc() return { kind = 'model', asset = 900 } end
local function fake(opts)
  opts = opts or {}
  local ui = Stub.new({ available = opts.available })
  local g = { ui = ui, match = function() return { active = true, netplay = opts.netplay or false } end,
    input_mask = function() error('Atlas must never mask the pad') end, input_chord = function() error('Atlas must never chord the pad') end }
  local log = { pressed = {}, marked = {}, notices = {}, refreshes = 0 }
  local S = setmetatable({ g = g, mode = 'bag', layout = 'main', active = true, log = log, blocks = blocks(),
    host = { seat = opts.seat, bag = function() return { capacity = function() return 4 end } end, plan_take = function() return { action = 'equip' } end } },
    { __index = Class })
  return S, ui, log, g
end

T.test('the switch: off by default, and any missing piece leaves the legacy screen', function()
  local S = fake(); A.set(false); assert(not A.enabled(S.g))
  A.set(true); assert(A.enabled(S.g))
  local S2 = fake({ available = false }); assert(not A.enabled(S2.g))
  S2.g.ui = nil; assert(not A.enabled(S2.g))
  assert(A.attach(S2) == false, 'attach refuses without gd.ui')
  A.set(false)
end)

T.test('describe: three blocks, positional ids, counts split, stones, flags and models', function()
  local S, ui = fake(); A.set(true); assert(A.attach(S))
  local d = ui.screens[ID]
  assert(d and d.primary.kind == 'grid' and #d.primary.blocks == 3)
  local eq, bag, key = d.primary.blocks[1], d.primary.blocks[2], d.primary.blocks[3]
  assert(eq.title == 'EQUIPPED' and eq.count == '5 / 6' and eq.cols == 6 and #eq.cells == 6, 'equipped block')
  assert(bag.title == 'BAG' and bag.count == '3 / 4' and #bag.cells == 4, 'bag block')
  assert(key.kind == 'stones' and key.note == 'One held' and key.count == '1 / 3', 'keystone block')
  assert(eq.cells[1].id == 'eq:1' and eq.cells[1].index == 1 and eq.cells[1].model == 101 and eq.cells[1].ring == 150, 'a drive cell: id, slot, model, ring')
  assert(eq.cells[6].flags.locked and bag.cells[4].flags.empty and bag.cells[1].flags.merge, 'locked, empty and merge flags')
  assert(key.cells[1].letter == 'P' and key.cells[1].color == 0xB872F0FF and key.cells[1].index == nil, 'a keystone: letter and colour, no slot number')
  assert(d.trail[1] == 'SOLO' and d.trail[2] == 'ENVOY' and d.trail.title == 'YOUR DRIVES' and d.chapter == 1)
  assert(d.input == 'feed' and d.explainer.width == 'narrow' and d.port == 1)
  assert(ui.stack[#ui.stack] == ID, 'attach opened the screen')
  A.set(false)
end)

T.test('co-op: the seat port is the screen port', function()
  local S, ui = fake({ seat = { port = 2 } }); A.set(true); assert(A.attach(S)); assert(ui.screens[ID].port == 2); A.set(false)
end)

T.test('focus: on.focus marks the merge target, re-registers, and the provider explains the real lines', function()
  local S, ui, log = fake(); A.set(true); A.attach(S)
  local before = ui.refreshed
  ui.engine_focus(ID, 'bag', 'bag:2')
  assert(log.marked[#log.marked] == 'Drive 2', 'the legacy mark_target ran for the focused cell')
  assert(ui.refreshed > before, 'the description was re-registered (merge flags may have changed)')
  local v = ui.views[ID]
  assert(v.explainer.kicker == 'BAG CELL 2' and v.explainer.title == 'Drive 2', v.explainer.kicker)
  assert(v.explainer.what == 'Aerial hits set Burning for 3 s.\nBurning targets take more damage.', v.explainer.what)
  assert(v.explainer.media.model == 102 and v.explainer.media.ring == 150 and v.explainer.from.text:find('Magic drive', 1, true))
  local btn = {}; for _, k in ipairs(v.keys) do btn[k[1]] = k[2] end
  assert(btn.A == 'Equip' and btn.Y == 'Discard' and btn.B == 'Close' and btn.X == nil, 'hints are the legacy actions plus Close; a false action is hidden')
  assert(v.counter == 'Bag 2 / 4', tostring(v.counter))
  A.set(false)
end)

T.test('locked and empty cells have no drive actions and still explain themselves', function()
  local S, ui, log = fake(); A.set(true); A.attach(S)
  ui.engine_focus(ID, 'eq', 'eq:6')
  local v = ui.views[ID]
  assert(v.explainer.title == 'Locked slot' and v.explainer.what == 'Slot 6 unlocks at depth 5.' and v.explainer.media == nil and v.explainer.from == nil)
  assert(#v.keys == 1 and v.keys[1][1] == 'B', 'only Close is offered')
  assert(ui.engine_press(ID, 'accept'), 'A reaches the handler ...')
  assert(log.accepted and log.accepted.kind == 'locked', '... on the locked ref, where the legacy accept does nothing')
  ui.engine_focus(ID, 'bag', 'bag:4')
  local v2 = ui.views[ID]
  assert(v2.explainer.what == 'Empty bag place.' and #v2.keys == 1 and v2.counter == 'Bag 4 / 4')
  A.set(false)
end)

T.test('A, B, X and Y reach the legacy handlers; directions go to the engine and never to the legacy view', function()
  local S, ui, log = fake(); A.set(true); A.attach(S)
  ui.engine_focus(ID, 'bag', 'bag:1')
  S:press('down'); S:press('left')
  assert(#ui.fed == 2 and ui.fed[1][2] == 'down' and ui.fed[2][2] == 'left')
  assert(#log.pressed == 0, 'directions never reach the legacy press')
  ui.engine_press(ID, 'accept'); ui.engine_press(ID, 'back'); ui.engine_press(ID, 'x'); ui.engine_press(ID, 'y')
  assert(table.concat(log.pressed, ',') == 'accept,back,x,y', table.concat(log.pressed, ','))
  local c = S:focused(); assert(c and c.name == 'Drive 1', 'the focused cell is the engine focus')
  A.set(false)
end)

T.test('focus survives merge and discard: the same cell, else the same place, else the first cell', function()
  local S, ui = fake(); A.set(true); A.attach(S)
  ui.engine_focus(ID, 'bag', 'bag:3')
  S.blocks = blocks(); S.blocks[2].cells[3] = { empty = true, name = 'Empty slot', lines = { 'Empty bag place.' }, ref = { kind = 'bag', where = 'bag', index = 3, empty = true }, actions = {} }
  S:refresh()                                                   -- the legacy refresh rebuilt S.blocks: the wrapper re-registers
  local c, b = ui.focus(ID)
  assert(c == 'bag:3' and b == 'bag', 'positional ids keep the focus on the same place')
  S.blocks = blocks(); S.blocks[2].cells[4] = nil; S.blocks[2].cells[3] = nil
  S:refresh(); c = ui.focus(ID)
  assert(c == 'bag:2', 'the cell is gone: clamped to the last cell of the same block, got ' .. tostring(c))
  S.blocks = blocks(); table.remove(S.blocks, 2)
  S:refresh(); c = ui.focus(ID)
  assert(c == 'eq:1', 'the block is gone: the first cell, got ' .. tostring(c))
  A.set(false)
end)

T.test('a notice becomes a corner note', function()
  local S, ui, log = fake(); A.set(true); A.attach(S)
  S:notify('Merged! Drive got stronger.')
  assert(log.notices[1] == 'Merged! Drive got stronger.' and ui.notes[1].text == 'Merged! Drive got stronger.')
  A.set(false)
end)

T.test('netplay: described, never masked, and the legacy input is untouched', function()
  local S, ui = fake({ netplay = true }); A.set(true); assert(A.enabled(S.g))
  A.attach(S); ui.engine_focus(ID, 'bag', 'bag:1'); ui.engine_press(ID, 'accept'); S:press('down'); S:refresh()
  assert(ui.screens[ID], 'g.input_mask and g.input_chord raise when called: getting here proves they were not')
  A.set(false)
end)

T.test('the swap layout hands the screen back to the legacy grid; close detaches', function()
  local S, ui, log = fake(); A.set(true); A.attach(S)
  assert(rawget(S, 'draw') and rawget(S, 'press') and S.atlas)
  S.layout = 'swap'; S:refresh()
  assert(S.atlas == nil and rawget(S, 'draw') == nil and rawget(S, 'press') == nil and rawget(S, 'focused') == nil, 'legacy methods are back')
  assert(#ui.stack == 0, 'the Atlas screen is closed')
  S.layout = 'main'; assert(A.attach(S)); A.detach(S)
  assert(S.atlas == nil and #ui.stack == 0)
  S.mode = 'reward'; assert(A.attach(S) == false, 'only the bag is described in step 1')
  A.set(false)
end)

T.test('a description the engine refuses falls back to the legacy screen', function()
  local S, ui = fake(); A.set(true)
  S.blocks[1].cells[2].name = nil
  local real = ui.screen
  ui.screen = function() error('gd.ui.screen: refused') end
  assert(A.attach(S) == false and S.atlas == nil and rawget(S, 'draw') == nil, 'attach failed cleanly')
  ui.screen = real; A.set(false)
end)

T.done()
```

- [ ] **Step 2: Run it to verify it fails.**

```bash
cd "$GW_MELEE" && lua pc/tests/envoy_atlas_bag.lua
```

Expected: `lua: cannot open pc/scripts/examples/envoy/scripts/atlas_bag.lua` (from `assert(loadfile(...))`: `attempt to call a nil value`).

- [ ] **Step 3: Write the minimal implementation.** Create `melee/pc/scripts/examples/envoy/scripts/atlas_bag.lua`:

```lua
-- The Envoy bag as a gd.ui description (Atlas step 1; spec section 13.1). It reads the cell data run_screen.lua already builds
-- (S.blocks: blocks of cells with name, icon, flags, actions, ref and detail lines) and describes it; the engine lays it out,
-- moves focus, reads mouse and keyboard and draws the key hints. The pad stays with run_screen's own input (menu_input.lua hides
-- the D-pad and START from the game and does not mask online), so the screen is input = 'feed': directions are fed to the
-- engine, A/B/X/Y run the legacy handlers. Off by default (A.set, console `uxatlas on`). Anything it cannot describe (the swap
-- layout, no gd.ui, no Atlas fonts) leaves the legacy grid screen in charge.
return function(D)
 local A={setting={on=false}}
 local ID='envoy.bag'
 local KICKER={eq='EQUIPPED SLOT',bag='BAG CELL',key='KEYSTONE',offer='OFFERED',koffer='KEYSTONE OFFER'}
 local DIRS={up=true,down=true,left=true,right=true}

 function A.set(on) A.setting.on=on and true or false end

 function A.enabled(g)
  if not A.setting.on or type(g.ui)~='table' or type(g.ui.available)~='function' then return false end
  return (g.ui.available()) and true or false
 end

 -- 'EQUIPPED 5/6' -> 'EQUIPPED', '5 / 6'
 local function split_title(t)
  local name,a,b=tostring(t):match('^(.-)%s+(%d+)/(%d+)$')
  if name then return name,a..' / '..b end
  return tostring(t),nil
 end

 local function cell_desc(block_id,i,c)
  local d={id=block_id..':'..i,name=c.name or '',flags={},pips=c.pips or 0}
  if block_id=='eq' or block_id=='bag' then d.index=i end
  if c.empty then d.flags.empty=true end
  for _,f in ipairs(c.flags or {}) do if f=='locked' or f=='merge' or f=='new' then d.flags[f]=true end end
  local ic=c.icon
  if type(ic)=='table' then
   if ic.kind=='model' then d.model=ic.asset;d.ring=ic.ring
   elseif ic.kind=='letter' then d.letter=ic.letter;d.color=ic.colour end
  end
  return d
 end

 -- IF YOU MERGE: the focused drive, the drive it merges into and the result (only when the legacy plan says merge)
 function A.footer(S,c)
  local ref=c and c.ref
  if not ref or not ref.record or (ref.kind~='bag' and ref.kind~='offer') then return nil end
  local ok,res=pcall(function()
   local plan=S.host:plan_take(ref.record,ref.kind=='bag' and {where='bag',index=ref.index} or nil)
   if plan.action~='merge' then return nil end
   local target
   for _,b in ipairs(S.blocks) do for _,t in ipairs(b.cells) do
    if t.ref and t.ref.where==plan.loc.where and t.ref.index==plan.loc.index and not t.empty then target=t end
   end end
   local out=S:model_desc(plan.merged.colour,plan.merged.rarity)
   local name=S.host:merge_text(plan)
   return {label='IF YOU MERGE',a=c.icon and c.icon.asset,b=target and target.icon and target.icon.asset,out=out and out.asset,text=(name or 'It')..' gets stronger.'}
  end)
  return ok and res or nil
 end

 -- what the explainer shows for one cell: the legacy detail lines, split into the drive's name line, its rule lines, and the rest
 function A.explainer(self,cid,bid)
  local S=self.S;local c=self.cells[cid]
  if not c then return nil end
  local lines=c.lines or S:detail_lines(c)
  local idx=cid:match(':(%d+)$')
  local ex={kicker=(KICKER[bid] or bid:upper())..(bid~='key' and idx and (' '..idx) or ''),title=c.name or ''}
  if c.empty or (c.ref and c.ref.kind=='locked') then ex.what=lines[1] or '';return ex end
  local rules,blank={},false
  for i=2,#lines do local l=lines[i];if l=='' then blank=true elseif not blank then rules[#rules+1]=l end end
  ex.what=table.concat(rules,'\n')
  if type(c.icon)=='table' and c.icon.kind=='model' then ex.media={model=c.icon.asset,ring=c.icon.ring} end
  if lines[1] then ex.from={text=lines[1]} end
  return ex
 end

 function A.describe(S,self)
  local cells,blocks={}, {}
  for _,b in ipairs(S.blocks) do
   local name,count=split_title(b.title or b.id)
   local bd={id=b.id,title=name,count=count,cols=math.max(1,math.min(b.cols or 1,12)),cells={}}
   if b.id=='key' or b.id=='koffer' then bd.kind='stones' end
   if b.id=='key' then bd.note=(#b.cells==1) and 'One held' or (#b.cells..' held') end
   for i=1,#b.cells do
    local c=b.cells[i]
    if c then local d=cell_desc(b.id,i,c);bd.cells[#bd.cells+1]=d;cells[d.id]=c end
   end
   blocks[#blocks+1]=bd
  end
  self.cells=cells
  local ok,fid=pcall(S.g.ui.focus,ID)
  local focus=ok and fid and cells[fid] or nil
  local function action(btn) return function(cid) local c=self.cells[cid];return c and c.actions and c.actions[btn] or nil end end
  return {
   id=ID,trail={'SOLO','ENVOY',title='YOUR DRIVES'},chapter=1,
   primary={kind='grid',blocks=blocks,footer=A.footer(S,focus)},
   explainer={width='narrow',provide=function(cid,bid) return A.explainer(self,cid,bid) end},
   keys={{'A',action('A')},{'X',action('X')},{'Y',action('Y')},{'B','Close'}},
   counter=function(cid)
    local c=self.cells[cid];local r=c and c.ref
    if r and r.where=='bag' then return ('Bag %d / %d'):format(r.index,S.host:bag():capacity()) end
    if r and r.where=='equipped' then return ('Slot %d / 6'):format(r.index) end
   end,
   input='feed',port=(S.host and S.host.seat and S.host.seat.port) or 1,
   on=self.on}
 end

 function A.register(self)
  local S=self.S
  local ok,err=pcall(function() S.g.ui.screen(A.describe(S,self)) end)
  if not ok then
   if S.host and S.host.log then S.host:log('atlas bag: '..tostring(err)) end
   A.detach(S);return false
  end
  self.blocks_ref=S.blocks
  return true
 end

 function A.attach(S)
  if S.mode~='bag' or S.layout~='main' or not A.enabled(S.g) then return false end
  local g=S.g
  local self={S=S,cells={}}
  S.atlas=self
  local orig_press,orig_refresh,orig_notify=S.press,S.refresh,S.notify
  local function focused_cell()
   local ok,cid=pcall(g.ui.focus,ID)
   return ok and cid and self.cells[cid] or nil
  end
  self.on={
   accept=function() S:press('accept') end,
   back=function() S:press('back') end,
   alt={X=function() S:press('x') end,Y=function() S:press('y') end},
   focus=function(cid)
    local c=self.cells[cid];S.confirm=nil
    if c then
     S:mark_target(c)
     if not c.detail_done then c.lines=S:detail_lines(c);c.detail_done=true end
    end
    A.register(self)
   end}
  S.draw=function() end
  S.sync=function() end
  S.focused=function() local c=focused_cell();return c,c and c.ref end
  S.press=function(inst,action)
   if not inst.active then return end
   if DIRS[action] then inst.confirm=nil;g.ui.feed(ID,action);inst:refresh();return end
   return orig_press(inst,action)
  end
  S.refresh=function(inst)
   orig_refresh(inst)
   if inst.layout~='main' or inst.mode~='bag' then A.detach(inst);return end
   if inst.blocks~=self.blocks_ref then A.register(self) end
  end
  S.notify=function(inst,text) orig_notify(inst,text);pcall(g.ui.note,{text=text,kind='info',seconds=4}) end
  if not A.register(self) then return false end
  g.ui.open(ID)
  return true
 end

 function A.detach(S)
  if not S.atlas then return end
  S.atlas=nil
  for _,k in ipairs({'draw','focused','sync','press','refresh','notify'}) do S[k]=nil end
  if S.g and S.g.ui then pcall(S.g.ui.close,ID) end
 end

 return A
end
```

- [ ] **Step 4: Run the tests.**

```bash
cd "$GW_MELEE" && lua pc/tests/envoy_atlas_bag.lua
```

Expected: `PASS 11 tests`. If `focus survives merge and discard` fails, remember the stub's rule: by id first, then the same block clamped to the old index, then the first cell; ids here are positional.

- [ ] **Step 5: Commit.** Game repo: `pc/scripts/examples/envoy/scripts/atlas_bag.lua`, `pc/tests/envoy_atlas_bag.lua`, message `envoy: the bag as a gd.ui description (atlas_bag.lua), behind a switch, with offline tests`.

---

### Task 14: Wire the Atlas bag into `RunScreen`, the bundle and the console

**Files:**
- Modify (game repo): `melee/pc/scripts/examples/envoy/scripts/run_screen.lua` (the two hooks, near lines 316-335), `melee/pc/scripts/examples/envoy/scripts/run_host.lua` (one command near line 98), `melee/pc/tests/envoy_run_ux.lua` (module list near line 22; one new test before `T.done()`), `melee/pc/scripts/examples/envoy/scripts/main.lua` (regenerated)
- Modify (workspace repo): `tools/port/envoy_bundle.py` (the module list at line 29; `GW_MELEE` support at lines 13-17 and 40)

**Interfaces:**
Consumes: `D.atlas_bag.enabled/attach/detach/set` (Task 13); the stub (Task 12).
Produces: the console command `uxatlas [on|off]` (takes effect the next time the bag opens); the bundle includes the module; the hook lines.

- [ ] **Step 1: Write the failing test.** In `melee/pc/tests/envoy_run_ux.lua`, change the module-loading list at line 22 from `...,'mod_lab','run_screen','run_hud','run_host'}` to `...,'mod_lab','run_screen','atlas_bag','run_hud','run_host'}`, and add this test immediately before the final `T.done()`:

```lua
T.test('the Atlas bag over the real RunScreen: described, focus by id, A merges through the legacy handler, B closes both',function()
 local Stub=dofile((io.open('pc/tests/atlas_ui_stub.lua') and '' or 'melee/')..'pc/tests/atlas_ui_stub.lua')
 local s,g,mods,host=start_run();stage(host)
 local ui=Stub.new();g.ui=ui;D.atlas_bag.set(true)
 local m=mergeable(host);give(host,m);host.screen:open('bag')
 assert(host.screen.atlas,'the Atlas bag attached');local d=ui.screens['envoy.bag']
 assert(d and #d.primary.blocks>=3,'equipped, bag and keystone blocks described');assert(ui.stack[#ui.stack]=='envoy.bag')
 ui.engine_focus('envoy.bag','bag','bag:1')
 local v=ui.views['envoy.bag'];local keys={};for _,k in ipairs(v.keys) do keys[k[1]]=k[2] end
 assert(keys.A=='Merge','the legacy label for A is the Atlas key hint: '..tostring(keys.A));assert(v.explainer and v.explainer.title~='')
 local before=count_drives(host);assert(ui.engine_press('envoy.bag','accept'));assert(count_drives(host)==before-1,'A merged through the legacy handler')
 assert(ui.engine_press('envoy.bag','back'));assert(not host.screen.active and #ui.stack==0 and host.screen.atlas==nil,'B closed the bag and the Atlas screen')
 D.atlas_bag.set(false)
 local s2,g2,m2,h2=start_run();stage(h2);g2.ui=Stub.new();give(h2,mergeable(h2));h2.screen:open('bag')
 assert(h2.screen.atlas==nil,'switched off, the legacy bag opens untouched');h2.screen:press('back')
end)
```

- [ ] **Step 2: Run it to verify it fails.**

```bash
cd "$GW_MELEE" && lua pc/tests/envoy_run_ux.lua 2>&1 | tail -4
```

Expected: the new test fails with `the Atlas bag attached` (the hook is not in `run_screen.lua` yet); the other 56 pass.

- [ ] **Step 3: Write the minimal implementation.**
  1. `run_screen.lua`, in `function S:open(mode)`: after the line ` self:refresh()` (the one right after the `owns_pause` line, before ` if self.view then self.view:set_countdown(...)`), add one line: `  if mode=='bag' and D.atlas_bag and D.atlas_bag.enabled(self.g) then D.atlas_bag.attach(self) end`. In `function S:close()`, add as its first line: `  if self.atlas then D.atlas_bag.detach(self) end`. (Find them with `grep -n "self:refresh()" run_screen.lua` and `grep -n "function S:close" run_screen.lua`. The file's style is a one-space indent for `function` lines and two spaces inside them: the lines above are written with their two-space indent. Both hooks were run against the real `RunScreen` and the 56 existing `envoy_run_ux.lua` tests: the suite passed 57 with the new test.)
  2. `run_host.lua`, directly after the `uxbag` command (line 98) add:

```lua
  g.command('uxatlas',function(a) if D.atlas_bag then D.atlas_bag.set(a~='off');g.log('uxatlas: the bag screen draws through gd.ui '..((a=='off') and 'off' or 'on')..' (from the next time the bag opens)') end;return true end,'draw the bag screen through the Atlas parts (gd.ui): uxatlas [on|off]')
```

  3. `tools/port/envoy_bundle.py` (workspace repo). First make it honour a lane's game checkout: add `import os` to the imports; after `ROOT = Path(__file__).resolve().parents[2]` add `MELEE = Path(os.environ.get('GW_MELEE') or ROOT / 'melee')`; replace `ROOT / 'melee/pc/scripts/examples/missions/scripts'` with `MELEE / 'pc/scripts/examples/missions/scripts'`, `ROOT / 'melee/pc/scripts/examples/envoy/scripts'` with `MELEE / 'pc/scripts/examples/envoy/scripts'`, `ROOT / 'melee/pc/scripts/examples/demos/grid-inventory/scripts/grid.lua'` with `MELEE / 'pc/scripts/examples/demos/grid-inventory/scripts/grid.lua'`, and `(ROOT / 'melee/pc/scripts/lib/pickup_juice.lua')` with `(MELEE / 'pc/scripts/lib/pickup_juice.lua')`. Leave `ROOT/'tools/port/missions_bundle.py'` as it is. Then in `ENVOY_MODULES` change `'grid', 'run_screen', 'run_hud'` to `'grid', 'run_screen', 'atlas_bag', 'run_hud'`.
  4. Regenerate the bundle into your game worktree and check it:

```bash
GW_MELEE="$GW_MELEE" python tools/port/envoy_bundle.py
GW_MELEE="$GW_MELEE" python tools/port/envoy_bundle.py --check; echo "exit=$?"
```

Expected: no output from the first, `exit=0` from the second. Before this change `--check` also exited 0 on the main checkout, so the bundle diff you commit contains only the new module and nothing else; confirm with `git -C "$GW_MELEE" diff --stat pc/scripts/examples/envoy/scripts/main.lua` (a single changed line plus the one-line addition).

- [ ] **Step 4: Run the tests.**

```bash
cd "$GW_MELEE" && lua pc/tests/envoy_run_ux.lua | tail -1
cd "$GW_MELEE" && lua pc/tests/envoy_atlas_bag.lua | tail -1
cd "$GW_MELEE" && lua pc/tests/grid_inventory.lua | tail -1
cd "$GW_MELEE" && for f in envoy_menu envoy_hud envoy_run envoy_main envoy_integration; do lua pc/tests/$f.lua | tail -1; done
```

Expected: `PASS 57 tests`, `PASS 11 tests`, `717 checks, 0 failed`, and `PASS n tests` for each of the five neighbours (their counts are whatever they were before this task; none may fail). If one of the neighbours cannot run from there, run it the way its own first comment line says.

- [ ] **Step 5: Commit.** Game repo: `pc/scripts/examples/envoy/scripts/run_screen.lua`, `run_host.lua`, `main.lua`, `pc/tests/envoy_run_ux.lua`, message `envoy: the bag opens through gd.ui behind uxatlas; the legacy bag stays the default and the fallback`. Workspace repo: `tools/port/envoy_bundle.py`, message `envoy bundle: honour GW_MELEE; include atlas_bag`.

---

### Task 15: The Atlas font pages (the pipeline, the licence, the credit)

**Files:**
- Create (workspace repo): `menu/Barlow/BarlowCondensed-SemiBold.ttf`, `menu/Barlow/BarlowCondensed-Bold.ttf`, `menu/Barlow/OFL.txt` (copied from the concept's `fonts/`), `menu/pipeline/test_atlas_fonts.py`, `tools/release/licenses/BarlowCondensed-OFL-1.1.txt`
- Modify (workspace repo): `menu/pipeline/kit.py` (the `FONTS` dict near line 96; a new list after `TYPE_SCALE` near line 130), `menu/pipeline/font_atlas.py` (`build_role` near line 168; `main` near lines 337-390 and 395), `tools/release/THIRD-PARTY-NOTICES.txt` (line 65), `CREDITS.md` (after line 156)
- Regenerate (workspace repo): `menu/out_kit/font/*` (new `font_a_*` pages, the merged `font_manifest.json`, the specimen) and `menu/out_kit/manifest.json`
- Modify (game repo): `melee/pc/platform/gw_kit.c` (one in-exe test)

**Interfaces:**
Consumes: the role names in `gw_ui_layout.c` (Task 2): `a_cap12 a_cap14 a_cap16 a_cap20 a_title a_hero a_display a_body12 a_body14 a_row16 a_num12 a_num14 a_num16`.
Produces: those 13 roles in `font_manifest.json` (faces `acond`, `asans`, `anum`), the pages `font_<role>_latin_0.png`, the licence in the package. The 10 legacy roles are unchanged.

- [ ] **Step 1: Write the failing test.** Create `menu/pipeline/test_atlas_fonts.py`:

```python
"""Pipeline checks for the Atlas font roles:  python menu/pipeline/test_atlas_fonts.py
Regenerates menu/out_kit/font (deterministic) and reads the result, the C role table and the loader limits."""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402

MENU = os.path.dirname(HERE)
REPO = os.path.dirname(MENU)
GAME = os.environ.get("GW_MELEE") or os.path.join(REPO, "melee")
LEGACY = ["caption", "body", "row", "label", "title", "heading", "hero", "display", "tag", "code"]
FACE_GROUP = {"acond": 0, "asans": 1, "anum": 2}


class AtlasFonts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import font_atlas
        assert font_atlas.main() == 0, "font_atlas.py checks failed"
        path = os.path.join(MENU, "out_kit", "font", "font_manifest.json")
        cls.m = json.load(open(path, encoding="utf-8"))
        cls.roles = cls.m["roles"]

    def test_atlas_roles_present_and_legacy_intact(self):
        for name in [s["role"] for s in kit.ATLAS_TYPE_SCALE]:
            self.assertIn(name, self.roles)
        for name in LEGACY:
            self.assertIn(name, self.roles)
        self.assertEqual(len(kit.ATLAS_TYPE_SCALE), 13)

    def test_floor_and_faces(self):
        for spec in kit.ATLAS_TYPE_SCALE:
            r = self.roles[spec["role"]]
            self.assertGreaterEqual(r["size"], 12, spec["role"])
            self.assertIn(r["face"], FACE_GROUP)
            self.assertNotIn(r["face"], ("sans", "mono"), "Atlas roles must not share a face tag with the legacy roles: the loader's fit rule steps down inside one face")

    def test_printable_ascii_everywhere(self):
        for spec in kit.ATLAS_TYPE_SCALE:
            if spec["charset"] == "caps":
                continue
            glyphs = self.roles[spec["role"]]["glyphs"]
            for ch in kit.ASCII:
                self.assertIn(ch, glyphs, "%s lacks %r" % (spec["role"], ch))
            self.assertIn("\u2026", glyphs, "%s lacks the ellipsis the fit rule truncates with" % spec["role"])

    def test_tabular_digits_where_declared(self):
        for spec in kit.ATLAS_TYPE_SCALE:
            if spec.get("tabular", True):
                g = self.roles[spec["role"]]["glyphs"]
                self.assertEqual(len({g[d]["advance"] for d in "0123456789"}), 1, spec["role"])
        for name in ("a_num12", "a_num14", "a_num16"):
            self.assertTrue(self.roles[name]["monospaced"])

    def test_sync_with_the_c_role_table(self):
        text = open(os.path.join(GAME, "pc", "platform", "gw_ui_layout.c"), encoding="utf-8").read()
        rows = re.findall(r'\{\s*"(a_\w+)",\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(-?\w+)\s*\}', text)
        self.assertEqual(len(rows), 13)
        for (name, size, face, caps, _tracked, _smaller), spec in zip(rows, kit.ATLAS_TYPE_SCALE):
            self.assertEqual(name, spec["role"])
            self.assertEqual(int(size), spec["size"], name)
            self.assertEqual(int(face), FACE_GROUP[spec["face"]], name)
            self.assertEqual(int(caps), 1 if spec["charset"] == "caps" else 0, name)

    def test_loader_limits_hold(self):
        text = open(os.path.join(GAME, "pc", "platform", "gw_kit.c"), encoding="utf-8").read()
        roles_cap = int(re.search(r"#define KF_ROLES (\d+)", text).group(1))
        kern_cap = int(re.search(r"#define KF_MAX_KERN (\d+)", text).group(1))
        self.assertLessEqual(len(self.roles), roles_cap)
        total = sum(len(r["kerning"]) for r in self.roles.values())
        self.assertLessEqual(total, kern_cap, "the loader silently drops kerning pairs past KF_MAX_KERN (%d pairs here)" % total)

    def test_licence_and_files_ship(self):
        for f in ("BarlowCondensed-SemiBold.ttf", "BarlowCondensed-Bold.ttf", "OFL.txt"):
            self.assertTrue(os.path.exists(os.path.join(MENU, "Barlow", f)), f)
        self.assertTrue(os.path.exists(os.path.join(REPO, "tools", "release", "licenses", "BarlowCondensed-OFL-1.1.txt")))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails.**

```bash
python menu/pipeline/test_atlas_fonts.py 2>&1 | tail -6
```

Expected: `AttributeError: module 'kit' has no attribute 'ATLAS_TYPE_SCALE'`.

- [ ] **Step 3: Write the minimal implementation.**
  1. Copy the font files and the licence (the concept already carries them; Barlow Condensed is by Jeremy Tribby, SIL OFL 1.1):

```bash
mkdir -p menu/Barlow tools/release/licenses
cp menu/concepts/reunification-2026-10-06/c-atlas/fonts/BarlowCondensed-SemiBold.ttf menu/concepts/reunification-2026-10-06/c-atlas/fonts/BarlowCondensed-Bold.ttf menu/concepts/reunification-2026-10-06/c-atlas/fonts/OFL.txt menu/Barlow/
cp menu/Barlow/OFL.txt tools/release/licenses/BarlowCondensed-OFL-1.1.txt
```

  2. `menu/pipeline/kit.py`: in the `FONTS` dict add three entries after `"mono"`:

```python
    # Atlas (menu re-unification, 2026-10-06). Separate face tags from the legacy "sans"/"mono": the engine's fit rule steps
    # down inside one face, so the Atlas roles must not share a tag with the legacy roles of the same size.
    "asans": dict(name="Source Sans 3", licence="SIL OFL 1.1", dir="SourceSans3",
                  files={"semibold": "SourceSans3-Semibold.otf"}),
    "acond": dict(name="Barlow Condensed (Jeremy Tribby)", licence="SIL OFL 1.1", dir="Barlow", licence_file="OFL.txt",
                  files={"semibold": "BarlowCondensed-SemiBold.ttf", "bold": "BarlowCondensed-Bold.ttf"}),
    "anum": dict(name="Hasklug Nerd Font (Hasklig)", licence="SIL OFL 1.1", dir="Hasklug",
                 files={"medium": "HasklugNerdFont-Medium.otf"}),
```

  and after the closing `]` of `TYPE_SCALE` add:

```python
# The Atlas role set (spec section 4.3). Names are the keys of the manifest and of gw_ui_layout.c's role table.
ATLAS_TYPE_SCALE = [
    dict(role="a_cap12", size=12, face="acond", weight="semibold", charset="full", tabular=False, use="Atlas: tags, toggle words (tracked caps)"),
    dict(role="a_cap14", size=14, face="acond", weight="semibold", charset="full", tabular=False, use="Atlas: plate headings, rail, key glyph letters"),
    dict(role="a_cap16", size=16, face="acond", weight="semibold", charset="full", tabular=False, use="Atlas: tabs, trail, buttons"),
    dict(role="a_cap20", size=20, face="acond", weight="semibold", charset="full", tabular=False, use="Atlas: the trail's current screen, dialog titles, stones"),
    dict(role="a_title", size=28, face="acond", weight="bold", charset="full", tabular=False, use="Atlas: explainer and screen titles"),
    dict(role="a_hero", size=44, face="acond", weight="bold", charset="caps", tabular=False, use="Atlas: title screen, results (caps only)"),
    dict(role="a_display", size=64, face="acond", weight="bold", charset="caps", tabular=False, use="Atlas: big numerals (caps only)"),
    dict(role="a_body12", size=12, face="asans", weight="semibold", charset="full", use="Atlas: captions"),
    dict(role="a_body14", size=14, face="asans", weight="semibold", charset="full", use="Atlas: rule text, hints"),
    dict(role="a_row16", size=16, face="asans", weight="semibold", charset="full", use="Atlas: list rows, choices"),
    dict(role="a_num12", size=12, face="anum", weight="medium", charset="full", use="Atlas: counters"),
    dict(role="a_num14", size=14, face="anum", weight="medium", charset="full", use="Atlas: values"),
    dict(role="a_num16", size=16, face="anum", weight="medium", charset="full", use="Atlas: footer counters"),
]
```

  3. `menu/pipeline/font_atlas.py`, `build_role`: replace `mono = spec["face"] == "mono"` with `mono = spec["face"] in ("mono", "anum")`; after the line `tables = font_tables(path, chars)` add:

```python
    missing_ascii = [c for c in kit.ASCII if c not in tables["adv"]]
    if missing_ascii:
        raise SystemExit("%s: %s lacks printable ASCII %r" % (spec["role"], path, missing_ascii))
    dropped = [c for c in chars if c != STAR and c not in tables["adv"]]   # extras the face does not have (arrows...): the engine sets '?'
    chars = [c for c in chars if c not in dropped]
```

  and add `dropped=dropped,` to the `dict(...)` that `build_role` returns (next to `use=spec["use"]`).
  4. `font_atlas.py`, `main`: change `for spec in kit.TYPE_SCALE:` to `for spec in kit.TYPE_SCALE + kit.ATLAS_TYPE_SCALE:`; in the checks change `missing = [c for c in kit.charset(spec["charset"]) if c not in role["glyphs"]]` to `missing = [c for c in kit.charset(spec["charset"]) if c not in role["glyphs"] and c not in role["dropped"]]`; change `if len(digits) != 1:` to `if spec.get("tabular", True) and len(digits) != 1:`; in the `fonts=` entry of `manifest` change `"%s, %s (see %s/LICENSE.md)" % (v["name"], v["licence"], v["dir"])` to `"%s, %s (see %s/%s)" % (v["name"], v["licence"], v["dir"], v.get("licence_file", "LICENSE.md"))`.
  5. Regenerate, and refresh the texture list the converter reads:

```bash
python menu/pipeline/font_atlas.py | tail -12
python menu/pipeline/kit_ui.py | tail -3
git status --short menu/out_kit | head -40
```

Expected: the font report lists 23 roles (the 13 new ones `a_cap12` ... `a_num16`, 7,065 kerning pairs between them, about 7.3 MB once decoded to RGBA8 by the host, from the page sizes it prints) and ends `font checks ok`; `kit_ui.py` (headless Chromium, no window) finishes; `git status` shows NEW `font_a_*` PNGs under `menu/out_kit/font/1x` and `2x`, a MODIFIED `font_manifest.json`, `manifest.json` and the specimen, and **no modified legacy `font_<legacy role>_latin_0.png`** (if a legacy page changed, stop: the generator is not deterministic here, tell the coordinator).
  6. Deploy to your lane's private UI directory (the loader searches `<exe>/../../ui` before the shared `_build/ui`, so this touches nobody else, `gw_kit.c:264-290`), then add the in-exe check. Run from the workspace root:

```bash
mkdir -p "$GW_BUILD_ROOT/ui" && cp -r "$GW_ROOT/_build/ui/." "$GW_BUILD_ROOT/ui/"
python "$GW_MELEE/pc/tools/png2gx.py" --manifest "$WS/menu/out_kit/manifest.json" --outdir "$GW_BUILD_ROOT/ui" --res 2x
cp "$WS/menu/out_kit/font/font_manifest.json" "$GW_BUILD_ROOT/ui/"
ls "$GW_BUILD_ROOT/ui" | grep -c "font_a_"
```

Expected: the converter prints one line per texture; the last command prints 13 or more (one page per role, more for the caps roles). If `png2gx.py` cannot find the PNGs, read `convert_manifest` in `$GW_MELEE/pc/tools/png2gx.py` for the base directory it resolves `file_2x` against and run it from there.
  In `melee/pc/platform/gw_kit.c` add above `gw_kit_tests_register` and register as `kit_atlas_roles`:

```c
static int test_kit_atlas_roles(void) {
    static const char *const names[] = {"a_cap12", "a_cap14", "a_cap16", "a_cap20", "a_title", "a_hero", "a_display",
                                        "a_body12", "a_body14", "a_row16", "a_num12", "a_num14", "a_num16"};
    int i, found = 0;
    if (!gw_Kit_Available()) {
        return 0;
    }
    for (i = 0; i < 13; i++) {
        if (gw_Kit_Role(names[i]) >= 0) found++;
    }
    if (found == 0) {
        return 0; /* this lane's ui/ has no Atlas fonts yet: nothing to check */
    }
    if (found != 13) {
        gw_test_fail("only %d of the 13 Atlas text roles are in the font manifest", found);
        return 1;
    }
    for (i = 0; i < 13; i++) {
        float size = 0.0f;
        int role = gw_Kit_Role(names[i]);
        gw_Kit_RoleMetrics(role, &size, NULL, NULL, NULL, NULL);
        if (size < 12.0f || gw_Kit_TextWidth(role, "Aa 123") <= 0.0f) {
            gw_test_fail("Atlas role %s: size %.1f, no width", names[i], size);
            return 1;
        }
    }
    return 0;
}
```

- [ ] **Step 4: Run the tests.**

```bash
python menu/pipeline/test_atlas_fonts.py 2>&1 | tail -4
python menu/pipeline/test_atlas_tokens.py 2>&1 | tail -2
tools/port/build.sh --shim gw_kit.c
MELEE_TEST_FILTER=kit_ tools/port/run.sh --test atlas-kit --iso "$GW_ISO_VANILLA"
grep -a "TESTS" "$GW_BUILD_ROOT/runs/atlas-kit/melee-pc.log" | tail -8
```

Expected: `Ran 7 tests ... OK`, `OK`, and in the log `kit_atlas_roles` passing with `failures=0`. The log also says `kit: scripts' kit - 23 text roles, NNNN kerning pairs`; NNNN must be the manifest's total (the Python test pinned it under 32,000).
Then credits and the licence entry: append to `CREDITS.md` after line 156:

```
- Atlas menu system, step 1 (2026-10-06): the game's font atlas now carries [Barlow Condensed](https://github.com/jpt/barlow) by Jeremy Tribby (SIL OFL 1.1; files in `menu/Barlow/`, the licence in `tools/release/licenses/BarlowCondensed-OFL-1.1.txt` and so in the release's `LICENSES/`), for the new menus' caps labels and titles, beside Source Sans 3 (Adobe) and Hasklug (Nerd Fonts), both SIL OFL 1.1. The Atlas design is this project's own; nothing is traced from Nintendo or HAL work.
```

and in `tools/release/THIRD-PARTY-NOTICES.txt`, after the `Hasklug Nerd Font (Hasklig) ........... SIL OFL 1.1  Hasklug-OFL-1.1.txt` line (line 65) add:

```
      Barlow Condensed (Jeremy Tribby) ...... SIL OFL 1.1  BarlowCondensed-OFL-1.1.txt
```

Then check the release guard still passes (about 40 s): `python tools/release/test_release_guard.py 2>&1 | tail -3`, expecting `OK`. If it reports the new licence file as unknown, add `BarlowCondensed-OFL-1.1.txt` to the allowlist the failing assertion names, in the same commit.

- [ ] **Step 5: Commit.** Workspace repo: `menu/Barlow/`, `menu/pipeline/kit.py`, `font_atlas.py`, `test_atlas_fonts.py`, `menu/out_kit/font/`, `menu/out_kit/manifest.json`, `menu/out_kit/preview/font_specimen_2x.png`, `tools/release/licenses/BarlowCondensed-OFL-1.1.txt`, `tools/release/THIRD-PARTY-NOTICES.txt`, `CREDITS.md`, message `atlas: the Atlas font roles (Barlow Condensed, Source Sans 3 Semibold, Hasklug Medium), their licence and credit

Thirteen additive roles under their own face tags; the ten legacy roles are unchanged. Barlow Condensed: Jeremy Tribby, SIL OFL 1.1, https://github.com/jpt/barlow` with the trailers. Game repo: `pc/platform/gw_kit.c`, message `kit: an in-exe check that the Atlas text roles load`.

---

### Task 16: A single-feature demo mod for `gd.ui`

**Files:**
- Create (game repo): `melee/pc/scripts/examples/demos/atlas-screen/mod.json`, `melee/pc/scripts/examples/demos/atlas-screen/scripts/main.lua`, `melee/pc/scripts/examples/demos/atlas-screen/README.md`
- Modify (game repo): `melee/pc/scripts/examples/demos/catalogue.json` (one row), `melee/pc/scripts/examples/demos/README.md` (one table row near line 127)

**Interfaces:**
Consumes: `gd.ui` (Task 11).
Produces: the mod `demo_atlas_screen` (screen ids start with `demo_atlas_screen.`): F7 opens or closes it; two screens, a list with every value widget and a grid with cells, an explainer and key hints; used to look at the engine before involving Envoy (Task 18, step 3).

- [ ] **Step 1: Write the failing check.** The repo's demo validator (`tools/port/test_demo_mods.py`) reads the demos of the checkout it lives in, so it sees your demo only after your game branch is merged; until then the checks are the Lua syntax check and the catalogue row parsing. Run the first now:

```bash
cd "$GW_MELEE" && luac -p pc/scripts/examples/demos/atlas-screen/scripts/main.lua
```

Expected now: `luac: cannot open pc/scripts/examples/demos/atlas-screen/scripts/main.lua`. For reference, the validator already fails on `main` for other demos (`python tools/port/test_demo_mods.py 2>&1 | tail -3` in `$MAIN` ends with `FAIL: 95 catalogue entries; 212 Lua files`); the goal is that, once merged, no line mentions `demo_atlas_screen`.

- [ ] **Step 2: Create the mod.** `mod.json`:

```json
{
  "id": "demo_atlas_screen",
  "name": "Atlas screens (gd.ui)",
  "version": "0.1.0",
  "kind": "script",
  "api_version": 1,
  "gameplay": false,
  "rollback_safe": false,
  "entry": "scripts/main.lua"
}
```

`scripts/main.lua` (under 150 lines, the validator's limit for a new demo entry):

```lua
-- Atlas screens (gd.ui): a list with every value widget, and a grid with cells, an explainer and key hints.
-- F7 opens or closes it. A changes the row, X shows a corner note, Y a dialog, B closes, TAB or pad L switches screens.
-- Mouse: hover focuses, left click is A, right click is B, the wheel scrolls. Presentation only: it works online.
local ui = gd.ui
local MODES = { 'Window', 'Borderless', 'Full' }
local state = { sync = true, mode = 1, vol = 40, shown = 'list' }
local LIST, GRID = 'demo_atlas_screen.list', 'demo_atlas_screen.grid'

local function change(cid)
  if cid == 'sync' then state.sync = not state.sync
  elseif cid == 'mode' then state.mode = state.mode % #MODES + 1
  elseif cid == 'vol' then state.vol = (state.vol + 20) % 120 end
end

local function list_desc()
  return { id = LIST, trail = { 'SOLO', title = 'ATLAS DEMO' }, chapter = 1,
    primary = { kind = 'list', items = {
      { id = 'sync', label = 'Sync', value = { kind = 'toggle', on = state.sync } },
      { id = 'mode', label = 'Mode', sub = 'A steps the choice', value = { kind = 'choice', text = MODES[state.mode] } },
      { id = 'vol', label = 'Volume', value = { kind = 'slider', min = 0, max = 100, value = math.min(state.vol, 100) } },
      { id = 'code', label = 'Code', value = { kind = 'text', text = 'ABC-123' } },
      { id = 'closed', label = 'Closed', disabled = true } } },
    explainer = { width = 'normal', provide = function(cid)
      return { kicker = 'ROW', title = cid:upper(), what = 'Press A to change it, X for a note, Y for a dialog.', from = { text = 'Atlas demo' } } end },
    keys = { { 'A', 'Change' }, { 'X', 'Note' }, { 'Y', 'Dialog' }, { 'B', 'Close' } },
    counter = function(cid) return cid end,
    on = {
      accept = function(cid) change(cid); ui.screen(list_desc()) end,
      back = function() return { pop = true } end,
      alt = {
        X = function() ui.note{ text = 'A note from the demo', kind = 'ok', seconds = 3 } end,
        Y = function() ui.dialog{ title = 'DIALOG', text = 'This is the dialog part. A confirms, B cancels.',
          actions = { { 'A', 'Fine' }, { 'B', 'Cancel' } }, on = function(b) gd.log('demo_atlas_screen: dialog ' .. b) end } end } } }
end

local NAMES = { 'Fox', 'Falco', 'Marth', 'Sheik', 'Peach', 'Jigglypuff' }
local function grid_desc()
  local a, b = {}, {}
  for i, n in ipairs(NAMES) do a[i] = { id = 'a:' .. i, name = n, index = i, origin = i == 6 and 'G' or nil, pips = i % 4, flags = { new = i == 2 } } end
  a[4].flags = { locked = true }
  for i = 1, 3 do b[i] = { id = 'b:' .. i, name = 'Cell ' .. i, flags = { empty = i == 3, merge = i == 1 } } end
  return { id = GRID, trail = { 'VERSUS', 'MELEE', title = 'FIGHTERS' }, chapter = 2,
    primary = { kind = 'grid', blocks = {
      { id = 'a', title = 'ROSTER', count = '6 / 6', cols = 6, cells = a },
      { id = 'b', title = 'SPARE', cols = 4, cells = b } } },
    explainer = { width = 'narrow', provide = function(cid, bid)
      return { kicker = bid:upper(), title = cid:upper(), what = 'A cell shows only its name or model. The rule shows here, for the focus.', from = { text = 'Demo data' } } end },
    keys = { { 'A', 'Pick' }, { 'B', 'Close' } },
    on = { accept = function(cid) ui.note{ text = 'Picked ' .. cid, kind = 'info' } end, back = function() return { pop = true } end } }
end

local function top() return ui.state().top end
function on_tick()
  if not ui.available() then return end
  if gd.key_pressed('F7') then
    if top() then ui.close() else ui.screen(list_desc()); ui.open(LIST); state.shown = 'list' end
  end
  if gd.key_pressed('TAB') and top() then
    ui.close()
    if state.shown == 'list' then ui.screen(grid_desc()); ui.open(GRID); state.shown = 'grid'
    else ui.screen(list_desc()); ui.open(LIST); state.shown = 'list' end
  end
end
```

`README.md`: three short paragraphs: what it shows (`gd.ui`: list with toggle, choice, slider, text and a disabled row; a grid with locked, empty, merge and new cells, origin marks and pips; the explainer; key hints; corner note; dialog), how to launch (`MELEE_SCENE="mode=lab;stage=fd;p1=fox/hu;p2=falco/cpu0;cpus=idle"`, then the console `load <absolute path of this folder>`; F7), and the note `No disc-derived art; every pixel is a part drawn by the engine. Needs the Atlas font roles in ui/ (menu/pipeline/font_atlas.py); without them gd.ui.available() is false and the demo does nothing.`

Add the catalogue row (the file is a JSON list, 2-space indent; append before the final `]` with a text edit and keep the indentation), exactly:

```json
  {
    "id": "demo_atlas_screen",
    "path": "demos/atlas-screen",
    "title": "Atlas screens (gd.ui)",
    "api": "gd.ui (screens, key hints, corner note, dialog)",
    "category": "demo",
    "new": true,
    "in_game": false,
    "controls": "F7 opens and closes; D-pad or arrows move; A change; X note; Y dialog; B close; TAB or pad L switch list and grid; mouse hover, click, right click, wheel",
    "setup": []
  }
```

and the README index row in `demos/README.md` (after the `demo_console_socket` row at line 127):

```
| [`demo_atlas_screen`](atlas-screen) | Atlas screens (gd.ui) | gd.ui (screens, key hints, corner note, dialog) | F7 opens and closes; A change; X note; Y dialog; TAB switches list and grid | No (not played yet) |
```

- [ ] **Step 3: Run the checks.**

```bash
cd "$GW_MELEE" && luac -p pc/scripts/examples/demos/atlas-screen/scripts/main.lua && echo syntax-ok
cd "$GW_MELEE" && python -c "import json;rows=json.load(open('pc/scripts/examples/demos/catalogue.json',encoding='utf-8'));r=[x for x in rows if x['id']=='demo_atlas_screen'];print(len(rows),len(r),r[0]['path'])"
cd "$GW_MELEE" && wc -l pc/scripts/examples/demos/atlas-screen/scripts/main.lua
cd "$GW_MELEE" && grep -c "demo_atlas_screen" pc/scripts/examples/demos/README.md
```

Expected: `syntax-ok`; `96 1 demos/atlas-screen`; a line count under 150 (the validator's limit for a new demo entry); `1`. After the merge, `python tools/port/test_demo_mods.py 2>&1 | grep -c demo_atlas_screen` in the merged checkout must print `0`. (The validator's call scanner ignores `gd.ui.*` method calls; it does not know the `gs_ui_funcs` table. That is a known limit, not a failure of this task.)

- [ ] **Step 4: Commit.** Game repo: the four files and the two edits, message `demos: demo_atlas_screen, a single-feature demo of gd.ui (a list, a grid, a note, a dialog)`.

---

### Task 17: Documentation: `gd.ui`, the terms, the pipeline note

**Files:**
- Modify (workspace repo): `docs/scripting.md` (a new section before `### Comms callouts (offline)`, line 445), `docs/TERMINOLOGY.md` (a new subsection before `### Scripting`), `menu/CLAUDE.md` (the layout table)

**Interfaces:**
Consumes: the API and behaviour of Tasks 11 to 16.
Produces: the public reference for `gd.ui`; the two terms.

- [ ] **Step 1: Write the failing check.** Docs are checked by text: the names in the docs must be the names the C binding registers.

```bash
cd "$GW_ROOT"
for n in available screen open close feed focus set_focus note dialog state; do grep -c "gd.ui.$n" docs/scripting.md | tr '\n' ' '; done; echo
grep -c "legacy menu kit" docs/TERMINOLOGY.md
```

Expected now: `0 0 0 0 0 0 0 0 0 0` then `0`.

- [ ] **Step 2: Write the docs.** In `docs/scripting.md`, insert before the line `### Comms callouts (offline)`:

````markdown
### Atlas screens (`gd.ui`)

`gd.ui` draws screens in the new menu style (Atlas) from a **description**: the script says what goes in four fixed places
(trail, primary, explainer, keys) and the engine does the layout (4:3 and wide), focus movement, mouse and keyboard input, the
key hints and the motion. It is presentation only: it reads no game state, writes none, and is allowed online. It never masks
the pad (`gd.input_mask` stays yours, and stays refused online). Handlers do not run on a resimulated frame. It needs the Atlas
text roles in the kit's font manifest; `gd.ui.available()` says whether they are there. Design:
`docs/superpowers/specs/2026-10-06-menu-reunification-design.md`.

| function | |
|---|---|
| `gd.ui.available()` | `true`, or `false` and why |
| `gd.ui.screen(desc)` | register or replace the screen `desc.id` (must start with your mod's id and a dot). A replacement keeps the focus on the same cell id, else on the same place in the same block, else on the first cell. Raises a Lua error with the reason when the description is wrong |
| `gd.ui.open(id)`, `gd.ui.close([id])` | push a screen onto the stack, or remove it (the top one by default); `on.open` / `on.close` run |
| `gd.ui.feed(id, intent)` | an intent from your own input: `"up" "down" "left" "right" "accept" "back" "x" "y" "z"` |
| `gd.ui.focus(id)` | `cell_id, block_id`, or nil |
| `gd.ui.set_focus(id, block_id, cell_id)` | true when that cell exists |
| `gd.ui.note{text=, kind="ok"\|"warn"\|"err"\|"info", seconds=}` | a corner note on the top screen (0.5 to 15 s) |
| `gd.ui.dialog{title=, text=, actions={{"A","Discard"},{"B","Cancel"}}, on=function(button) end}` | a dialog on the top screen (one or two actions) |
| `gd.ui.state()` | `{depth, top, canvas_w, wide, quads, cost_ms, cost_max_ms, roles_ok}` |

A description:

- `id`; `trail = { "SOLO", "ENVOY", title = "YOUR DRIVES" }` (the array part are the parents, at most three); `chapter` 0 to 5.
- `primary = { kind = "grid", blocks = {...}, footer = {...} }` or `{ kind = "list", items = {...} }`.
  A **block** is `{ id, title, count?, note?, cols (1 to 12), kind? = "stones", cells = {...} }` (at most 6 blocks, 12 cells each). A **cell** is
  `{ id, name?, model?, ring?, index?, pips? (0-4), origin? = "G"|"+", color? (0xRRGGBBAA, for stones), letter?, flags = { locked, empty, merge, new, selected, disabled } }`;
  `model` and `ring` are `gd.model_load` handles. A cell shows only a model or a name. A **list item** is `{ id, label, sub?, disabled?, selected?, value? }` with
  `value = { kind = "toggle", on }`, `{ kind = "choice", text }`, `{ kind = "slider", min, max, value }`, `{ kind = "text", text }` or `{ kind = "counter", text }` (at most 32 items;
  values are data: register the screen again when they change). `footer = { label, a, b, out, text }` is a merge-preview strip.
- `explainer = { width = "narrow"|"normal"|"wide", provide = function(cell_id, block_id) -> { kicker, title, what, media = {model, ring}, with = {models}, from = { text } } end }`,
  or `"none"` (the default). `what` is one short rule (it is cut to 159 characters and 4 lines).
- `keys = { { "A", "Label" }, { "X", function(cell_id, block_id) return "Label" or nil end, when = function(...) end }, ... }`: at most 6 of `A B X Y Z L R START`; a function label
  that returns nothing hides the hint. `counter = "text"` or a function. `input = "engine"` (the default: the engine reads the pad of `port`) or `"feed"` (you feed directions
  and handle the buttons yourself, which is what a screen needs when it masks the pad itself).
- `on = { accept, back, alt = { X, Y, Z }, focus, open, close }`: functions called with `(cell_id, block_id)`. A handler may return `{ pop = true }` or `{ push = "id" }`.
  A disabled cell takes focus but never reaches `accept`. Key label, `when`, counter and provider functions must be pure and cheap: they run when focus changes.

Input: pad (D-pad or stick, A B X Y Z L R START), keyboard (arrows, Enter, Escape, Tab) and mouse (hover focuses, left click is A, right click is B, the wheel scrolls
a list, key hints are buttons); mouse and keyboard are local UI input and never reach the pads. The setting **Reduced Motion** (Settings > Video, key `reduced_motion`)
turns the fades and turntables into cuts.

Budget: one screen draws at most 4,096 entries of the kit's 16,384-quad list (a warning is logged at 3,000); a model cell is at most 512 triangles.
Demo: `demos/atlas-screen`. A real use: the Envoy bag (`envoy/scripts/atlas_bag.lua`, console `uxatlas on`).

````

In `docs/TERMINOLOGY.md`, insert before the `### Scripting` heading a new subsection:

```markdown
### Menus

| Term | Definition and boundary | Where |
|---|---|---|
| Legacy menu kit | Everything the port draws or wraps for menus before the Atlas re-unification: the native frontend (`gmfrontend*`), the old `gd.kit` panel, button and list, the `menu/out_*` art sets, the Envoy and LAB screen code, the launcher's own kit copy, and the retail screens until each is replaced. Removed piece by piece as screens move to Atlas. | `docs/superpowers/specs/2026-10-06-menu-reunification-design.md` |
| Atlas | The new menu system and its style: the parts (plate, row, tab strip, toggle, choice, slider, cell, model cell, explainer, dialog, note, key hints, trail), the screen description, the layout and focus rules, and `gd.ui`. Not the font atlas or a texture atlas, which keep their qualifier. | `melee/pc/platform/gw_ui_*`, `docs/scripting.md` |
```

In `menu/CLAUDE.md`, replace the row ``| `SourceSans3/`, `Hasklug/` | the fonts (OFL) |`` with:

```markdown
| `SourceSans3/`, `Hasklug/`, `Barlow/` | the fonts (OFL); `Barlow/` (Barlow Condensed, Jeremy Tribby) is the Atlas family |
| `atlas/` | `tokens.json`, generated by `pipeline/atlas_tokens.py` from the chosen concept's `tokens.css`; the C header `gw_ui_tokens.h` in the game repo comes from the same run |
```

and add a line under "Working here": `- The Atlas role set is `ATLAS_TYPE_SCALE` in `pipeline/kit.py`; `pipeline/test_atlas_fonts.py` regenerates the font pages and checks them against the C role table and the loader's limits.`

- [ ] **Step 3: Run the check.**

```bash
cd "$GW_ROOT"
for n in available screen open close feed focus set_focus note dialog state; do grep -c "gd.ui.$n" docs/scripting.md | tr '\n' ' '; done; echo
grep -c "Legacy menu kit" docs/TERMINOLOGY.md
```

Expected: ten counts of 1 or more, then `1`.

- [ ] **Step 4: Commit.** Workspace repo: `docs/scripting.md`, `docs/TERMINOLOGY.md`, `menu/CLAUDE.md`, message `docs: gd.ui reference; the terms legacy menu kit and Atlas; the Atlas pipeline note`.

---

### Task 18: The in-game proof (a checklist for a Windows agent or the owner)

**Nothing before this task proves the screen in the game.** Tasks 1 to 17 prove layout, focus, input events, the screen record, the parts against a recording sink, the Lua contract against a stand-in, and (in the exe, headless) the kit additions and the binding's basic calls. They do not prove that the quads look right, that the overlay draws where expected, that a real model cell fits, that a real drive's text reads, or that the frame cost is acceptable. Those are looked at here.

**Who and when.** Run this only when the owner is away from the machine, or let him do it: a game window steals focus. Window on the **second monitor** (set `MELEE_WINDOW_X` and `MELEE_WINDOW_Y` to that monitor's position; the position is not recorded in the repo, so ask the coordinator for it; never place the window on the main monitor while he is at the machine), `MELEE_VOLUME=0`, never hidden, never minimised. Stop the game by closing its window or by the PID you started; never by image name. Use the LAB (`mode=lab`), not Training, with `cpus=idle` for CPUs you do not script. No screenshots as proof; a screenshot is allowed only to diagnose how something looks, and `gd.screenshot` leaves the overlay out (use an OS window capture).

**Files:** none changed here. Evidence goes into `docs/superpowers/plans/` only as a short result note if the coordinator asks; otherwise report in the hand-off.

- [ ] **Step 1: Build in your private worktree and confirm the exe has the new code.**

```bash
tools/port/build.sh
grep -a "ui: Atlas text roles found" "$GW_BUILD_ROOT/melee-pc.exe" | head -1
grep -a "gd.ui.screen: the description is too large" "$GW_BUILD_ROOT/melee-pc.exe" | head -1
```

Expected: the build ends with the bridge fixpoint message and a linked exe; both `grep -a` commands print a line (a stale exe prints nothing: root `CLAUDE.md` fact 1). Make sure the lane's `ui/` holds the Atlas fonts (Task 15, step 3.6) and that the run uses a distinct sandbox name.

- [ ] **Step 2: Launch the LAB with the demo mod, before involving Envoy.**

```bash
MELEE_VOLUME=0 MELEE_WINDOW_X=<second monitor x> MELEE_WINDOW_Y=<second monitor y> \
MELEE_SCENE="mode=lab;stage=fd;p1=fox/hu;p2=falco/cpu0;cpus=idle" \
tools/port/run.sh atlas-proof --iso "$GW_ISO_VANILLA"
```

In the game's console (backtick): `load examples/demos/atlas-screen` (or the absolute path of `melee/pc/scripts/examples/demos/atlas-screen`), then press F7. Look at, and write down yes or no for each:
  1. The list screen draws with the Atlas look (dark ground, plates with a front edge, ember focus) and the text is Barlow Condensed caps for labels and Source Sans for rows: **not** the old cobalt/gold kit.
  2. D-pad or arrows move the focus; the focused row lifts and its edge turns ember; the disabled row takes focus and A does nothing; the toggle says ON or OFF; the slider moves; the key hints at the bottom match the screen.
  3. Mouse: hovering a row focuses it, a resting pointer does not steal focus from the pad, left click acts like A, right click like B, the wheel scrolls. TAB switches to the grid screen; the focus brackets draw around a focused cell; locked and empty cells look different from filled ones.
  4. `X` shows a corner note; `Y` shows a dialog over a darkened scrim; A or B answers it (the log line `demo_atlas_screen: dialog A`).
  5. In the console, `= gd.ui.state().quads` and `= gd.ui.state().cost_ms`: record both (the list is a few hundred quads; the cost target is at most 0.5 ms).
  6. Reduced Motion: turn it on in Settings > Video (a title-screen trip), reopen: the fade is a cut.

- [ ] **Step 3: The Envoy bag.** Mount the drive models (`mods/envoy_drives`, folder from `melee/pc/scripts/examples/envoy_drives`; see its README) so the cells show models. In the console: `load examples/envoy`, `envoy rules on`, `envoy start classic fox depth=6 loop=0 build=7`, `drive grant rare 11` (the PLAYTEST.md top lines are the reference if a command differs), then `uxatlas on`, then `uxbag` (or Z+START in a fight). Look at, and write down yes or no for each:
  1. The bag opens as the Atlas bag: trail `SOLO > ENVOY > YOUR DRIVES`, three blocks (EQUIPPED n / 6, BAG n / 4, KEYSTONE), drive models in the cells with their rarity rings, the keystone as an arch stone with its letter, the locked slot with a lock, an empty place with a plus.
  2. Focus: D-pad moves between cells and blocks (up and down jump between blocks); the focused cell lifts with ember edge and four brackets; mouse hover moves it too.
  3. The explainer for a **real drive**: kicker (`BAG CELL 1`), the drive's short name as the title, its rule lines (one line per modifier), a FROM tag with the full drive name; the model large in the media well, turning. Is it readable at a glance? Three modifiers on one drive show three lines: say whether that is acceptable (the spec's "one short rule per piece").
  4. A **merge**: focus a bag drive that matches an equipped one: the equipped cell shows `+ MERGE` and a jade ring, the footer strip `IF YOU MERGE` shows the pair and the result, the key hint says `A Merge`; press A: "Merged" appears as a corner note and the bag redraws with the focus on the same place.
  5. X (to bag) on an equipped drive, Y twice (discard asks twice through the legacy note), B closes: the game resumes and START does not also pause.
  6. **4:3 and wide.** Run the same at a 4:3 window (`MELEE_WINDOW_W=960 MELEE_WINDOW_H=720`) and at 16:9 (`1920 x 1080`): the wide arrangement shows the chapter rail at the left and a wider explainer; nothing new appears. Run once at 640x480 (`MELEE_WINDOW_W=640 MELEE_WINDOW_H=480`): every string is legible (12 px at the smallest) and nothing runs outside its pane; a drive with a long name truncates with an ellipsis instead of overflowing.
  7. **Frame cost.** With the bag open, `= gd.ui.state().cost_ms` and `.cost_max_ms` and `.quads` (record them), and the existing `uxcost` (script cost of the run screens): the Atlas bag must be at most 0.5 ms average and under 3,000 quads. The frame itself must hold 120 fps: run with `MELEE_FPS=120` and watch the FPS readout (Settings > Video > Show FPS).
  8. **Fallbacks.** `uxatlas off`, reopen the bag: the legacy grid draws exactly as before. With `uxatlas on` open the swap layout (give drives until the bag is full and one more is picked up): the Atlas screen hands over to the legacy swap grid and back.
  9. **Online** (only if a second client and the owner's consent exist; otherwise write "not run"): in a netplay room with Envoy online on, open the bag: it draws, mouse and keyboard work, the match is not paused and the pad is not masked, and neither client desyncs. The log must show no `input_mask` call from Atlas code (`grep -a "input_mask" melee-pc.log` shows only the legacy Envoy lines).

- [ ] **Step 4: Capture and report.** Save from the run folder `"$GW_BUILD_ROOT/runs/atlas-proof/melee-pc.log"` the lines containing `ui:` (screen opens and closes, quad warnings, role messages) and any `[envoy]` error lines; the numbers from steps 2.5 and 3.7; a yes or no for every numbered item above with one line of detail for each no. State plainly in the report which items were not run and why. The owner decides whether the look is accepted.

- [ ] **Step 5: After the owner's look (a follow-up, not part of this plan).** If he accepts the Atlas bag: delete `envoy/scripts/drive_menu.lua` (the older bag UI) and its bundle entry, drop the bag's use of the embedded `D.grid` once reward and swap move (step 3 of the migration), remove the `uxatlas` switch and make the Atlas bag the default. Do not do this in the same session as the proof.

---

## Self-review

**Spec coverage (section 13.1, step 1).**

| 13.1 item | Where |
|---|---|
| U1 additions (tracking, hatch, chamfer helper, graticule, key glyphs and icons) | tracking and a poly quad: Task 10. Chamfer: Tasks 7 and 10. Hatch, graticule, icon set: **not built** (gaps 1 and 2) |
| U2 all parts | Tasks 7 and 8 (plate, row, tabs, toggle, choice, slider, tag, cell, stone, hint, trail, chapter and rail, explainer, footer, note, dialog) |
| U3 screen and layout | Tasks 2 (layout, fit, wrap), 5 (record, validation, refocus), 9 (composition, hits, budget) |
| U4 focus and input (pad, mouse, keyboard) | Tasks 3 and 4; used by the bag for mouse and keyboard, pad through `feed` (gap 4) |
| U5 stack (fade, modal, online non-modal) | Task 6 (stack, tween), Task 9 (fade, dialog rise), Task 11 (tick, draw); the bag is non-modal online because it never masks (Task 13 test) |
| `gd.ui.screen`, `invalidate`, `note`, `dialog` | Task 11; there is no `invalidate`: re-registering is the invalidation, documented in Task 17 |
| `menu/atlas/tokens.json` and its generator | Task 1 |
| Reduced Motion setting | Task 11 (setting row, key `reduced_motion`), honoured in Tasks 6, 9, 11 |
| `docs/TERMINOLOGY.md`, `docs/scripting.md`, `CREDITS.md`, the OFL text in the package | Tasks 17 and 15 |
| The Envoy bag as the Atlas bag | Tasks 13 and 14 |
| Retired: `drive_menu.lua`, the bag's use of `D.grid` | **Deliberately not in this plan**: the legacy bag is kept as the default and the fallback until the owner has looked (Task 18, step 5) |
| Verified without the game: layout tests at three widths, the Lua stub test, equivalence of focus movement with `grid_inventory.lua`, quad and triangle budget with 16 drive models | Tasks 2, 3 (the legacy scenario ported case by case), 9 (13 cells and 14 model calls, and the long-string and three-width tests), 12, 13 |
| Must be seen in game | Task 18 |

**Gaps and deviations the engineer and the coordinator should know about.**
1. The **hatch** and **graticule** textures (spec engine work items 3 and 5) are not built: disabled and locked things use flat dim fills plus a glyph, the ground is flat. These are the spec's own fallbacks.
2. The **36 line icons** and the Atlas pad-glyph art are not built: step 1 draws every glyph from quads (plus, lock, d-pad cross, octagon discs, triangles). The bag needs none of the textures.
3. The `list` primary's value widgets take **data**, not a `get` function read every frame (spec 7.1): a script re-registers when a value changes. Frame-live values arrive with the native adapter in step 2.
4. The Envoy bag uses `input = 'feed'`: its pad input and the D-pad and START masking stay in `menu_input.lua`; the engine's own pad path (Task 4) is built and tested but unused by the bag. Moving the masking into the engine is a follow-up.
5. The discard confirmation still uses the legacy "press Y again" notice (now shown as a corner note); the dialog part and `gd.ui.dialog` exist, are tested natively and by the demo, but the bag does not use them yet.
6. The explainer's **WITH** row is not populated by the bag (no data in `run_screen.lua` for it); a drive with several modifiers shows one line each, which may exceed the spec's "one short rule": the owner decides at the look.
7. The wide **rail** shows the chapter but is inert (no focus on it in step 1).
8. `menu/atlas/tokens.json` is generated and committed but only the C header consumes it in step 1; the launcher consumes it in step 9.
9. The `uxatlas` command name and the `reduced_motion` settings key are this plan's choices.
10. `gw_script_ui.inc` is tested host-side against stand-ins for the `gw_script.c` internals (Task 11, 40 checks through a real Lua state), in the exe (one test), through the Lua stub tests (which mirror its contract), the guard greps, and Task 18; the stand-ins mean the real `gs_pcall` budget, the real kit drawing and the real model path are only exercised in the exe.

**Placeholder scan.** No step defers a decision, refers to another task instead of repeating its code, or describes an action without showing it; every code step shows its code. Three places name an unknown by design and say what to read: the second-monitor position (ask the coordinator), `convert_manifest`'s base directory in `png2gx.py`, and whether `run.sh --test` shows a window. Line numbers into existing files are given with a `grep` to find the line, because they drift.

**Type and name consistency.** `AtRect`, `AtRole`, `AtTextOps` (Task 2) are used unchanged by Tasks 5, 7, 8, 9, 11. `AtFocusBlock`, `AtFocusPos`, `AtRepeat` (Task 3) are used by Tasks 4, 5, 6, 9, 11. `AtEvent`, `AtHit`, `AtHits`, `AT_HIT_*`, `AtPad`, `AtKeys`, `AtMouse` (Task 4) by Tasks 9 and 11. `AtScreen`, `AtView`, `AtCell`, `AtBlock`, `AtItem`, `AtKey`, `AtFooter`, `AtExplainer`, `AtNote`, `AtDialog` (Task 5, with `AtScreen.parent[]` and `AtDialog.from_ms` included in the listing) by Tasks 7, 8, 9, 11. `AtSink` and `AT_ALIGN_*`, `AT_ST_*`, `AT_TAG_*`, `AT_NOTE_*` (Task 7) by Tasks 8, 9, 11. `AT_SCREEN_QUAD_CAP/WARN` (Task 9) by Task 11. The gd.ui function names in Task 11's table are the ones the stub (Task 12), `atlas_bag.lua` (Task 13), the demo (Task 16) and the docs (Task 17) use. Role names `a_*` are identical in Task 2's table, Task 15's `ATLAS_TYPE_SCALE` and the in-exe test, and Task 15 checks the first two against each other.

**Review Focus pinned.** 1 (focus after a rebuild): Task 5 `refocus`, Task 12 stub, Task 13 `focus survives merge and discard`. 2 (long strings at 640): Task 2 `fit`/`wrap`, Task 8 explainer clamp, Task 9 `long_strings`. 3 (empty, locked, disabled): Task 5 `accept_semantics`, Task 12 stub, Task 13 `locked and empty cells...`. 4 (wide and mouse): Task 4 `mouse`, Task 9 `hits_at_widths`. 5 (online): Task 13 `netplay`, Task 11 step 4 greps, Task 18 step 3.9.

**Execution recommendation.** Use a fresh subagent per task with a review between tasks (superpowers:subagent-driven-development) for Tasks 1 to 10, which are self-contained, mechanical and each end in a test the reviewer can run; do Tasks 11 to 15 in one session by one agent (or two in order), because the binding, the stub, `atlas_bag.lua` and the `RunScreen` wiring share names and one mental model, and a fresh agent per task would have to rediscover `gw_script.c`; Task 16 and 17 are small and can go to a fresh agent; Task 18 is for a Windows agent while the owner is away, or for him.

