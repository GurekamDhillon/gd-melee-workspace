# Atlas step 6: the online room: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redraw the online screens (ONLINE PLAY rows, JOIN ROOM, WAITING ROOM, LOBBY) in Atlas. **Drawing only.** The room and lobby state machines stay in `gmfrontend_online.inc`, the netplay protocol is not touched, and the pad path into those state machines stays byte-for-byte the one that exists today. Mouse and keyboard become the same menu bits a pad press already produces, and never reach the pads or the netplay stream.

**Architecture:** Pure C units in the host (`gw_ui_online_parts.c`, `gw_ui_room.c`) turn a plain-data `AtRoomView` (filled once a frame by the game-side adapter from the `Netplay_*` readbacks the legacy screens already call) into an `AtScreen` plus one composite primary (code plate, player cards, rules pane, stage tiles, status strip, countdown, coin flip) drawn through the step 1 `AtSink`. No file under `pc/platform/gw_ui_*` includes a netplay header or calls a netplay function. The adapter in `gmfrontend_atlas_online.inc` is the only place that reads netplay state and the only place that turns an Atlas event into the existing `MenuInput_*` bit. A grep guard script pins both.

**Tech Stack:** C11 host code built through `tools/port/build.sh --native-test`, game-side retargeted C checked with `clang --target=powerpc-unknown-eabi -fsyntax-only`, Python 3 for two small checkers, the step 1 harness (`atlas_check.h`, `atlas_fake.h`, `atlas_rec.h`). No Lua in this step.

**Spec:** docs/superpowers/specs/2026-10-06-menu-reunification-design.md (13.6, with 4, 6.7, 8.4, 9, 10, 11). Step 1 plan for the form and the harness: docs/superpowers/plans/2026-10-06-atlas-step1-components-and-envoy-bag.md.

**Status of the plan:** written 2026-10-06 against the step 1 code as merged (headers read: `gw_ui_screen.h`, `gw_ui_parts.h`, `gw_ui_render.h`, `gw_ui_layout.h`, `gw_ui_input.h`, `gw_ui_stack.h`) and the legacy online code as it stands (`gmfrontend.c`, `gmfrontend_online.inc`, `gw_netplay.c`). Steps 2 to 5 are planned in parallel and **not built**: everything this plan takes from them is in "Needs from earlier steps" and is gated by Task 0. **What was checked when this was written (2026-10-06, offline, nothing built, no window):** the C of Tasks 1 to 7 was extracted and syntax-checked (`clang -fsyntax-only`) against the step 1 headers, with the stub of step 4's port card standing in; the game-side adapter and every edit of Tasks 7 and 8 were syntax-checked as PowerPC inside a copy of `gmfrontend.c` (which found one missing forward declaration, now in Task 8); `check_atlas_online.sh` was run against the unmodified legacy files plus the adapter (all seven guards pass, and guard 1 fails when it should). **Not checked:** the native tests were not linked or run (their expected counts are approximate), and nothing was seen in the game.

## Two corrections to the spec, found in the code

1. **Random Opponent is not a placeholder.** 13.6 says to hide or remove the "Random Opponent (soon)" row. In the code it is a working path (`fe_ol_random`, `Netplay_RandomBegin`, `Netplay_RandomStatus`, the FINDING OPPONENT waiting room). Only a comment in `gmfrontend_online.inc` still says "(soon)". This plan **keeps the row and the search screen**; removing a working feature is not a drawing change. The owner can still ask for it hidden.
2. **Step 6 needs step 5, not only 1, 2 and 4.** The ONLINE PLAY screen is a `FrontendItem` table with choice, slider and action rows (Stage List, Turbo, Envoy, Stocks, Time Limit, Input Delay with formatters). Drawing it through the adapter needs step 5's value rows (toggle, choice, slider with `format`). 13.6 lists the dependencies as 1, 2, 4. Order: 1, 2, 4, 5, then 6.

## Global Constraints

Exact values come from the spec; if a task seems to need a different one, stop and ask the coordinator.

- **Canvas and layout:** 640x480 logical; compact below 760 wide, wide from 760; content at most 1140 wide, centred; margins 32; header top 22 (30 high, rule at 56), body 66 to 428, footer 434 (26 high); explainer presets narrow 160, normal 196, wide 256.
- **Text:** floor 12 px. Roles `a_cap12/14/16/20`, `a_title`, `a_hero`, `a_display` (caps only), `a_body12/14`, `a_row16`, `a_num12/14/16`. Fit rule: step down one role of the same face, then truncate with an ellipsis; never squash; text with under 8 px of room is not drawn. The room code uses `display` (the spec has no separate `code` role; see "What is unverified").
- **Shape and focus:** flat quads only; chamfer on top-left and bottom-right only (8 px panes, 5 px rows, buttons, notes, tags, 3 px cells); front edge 3 px (modal 6). Focus is three cues at once: lift 2 px, ember front edge, a tick (rows) or four registration brackets (cells). Colour is never the only signal: states have a word or a shape as well. Disabled is dim text plus a word (the hatch texture is not built; spec fallback).
- **Motion on the UI clock:** focus lift 80 ms, dialog 140, note 160 in and 3 s hold. Reduced Motion turns every tween into a cut. Logic timers (the countdown, the coin flip, the 45-frame "found" beat, the B-twice-to-leave window) stay on **game frames**, owned by the existing state machine; Atlas only reads how many are left.
- **Budgets:** one Atlas screen at most 4,096 quad-list entries (warn at 3,000); the lobby with 32 stage tiles must stay under 1,200 entries at 1140 wide. Per-frame cost target 0.5 ms. Screen record limits from step 1 apply (`AT_MAX_CELLS` 12 per block, `AT_MAX_ITEMS` 32); the room composite pages its stage tiles by those macros, never by a copied number.
- **Online (the point of this step):** presentation only. Nothing in `pc/platform/gw_ui_*` includes a netplay header or calls a `Netplay_*` function. Atlas never masks a pad, never calls `gd.input_mask` or `input_chord`, never adds a call that writes netplay state. The pad bits that reach the lobby state machine are the same ones as today. Mouse and keyboard never reach the pads or the netplay stream. A screen's state is never an input to the simulation. No mod screen is pushed over a room screen (8.4).
- **No disc-derived data, ever.** Fighter icons shown in cards come from the existing runtime capture (`Frontend_CaptureCharIcon`, drawn from game memory, never stored) or, where step 4's disc-art cell is not ready, the hatched-frame stand-in with the two-letter abbreviation. No screenshots as verification (exception: diagnosing how a visual looks). Credit any outside idea or asset in the same change (none is expected here).
- **Naming:** `at_*` / `At*` in C, files `gw_ui_*` on the host, `fa_*` in the game-side adapter (`gmfrontend_atlas_online.inc`), shims `gw_Ui_Room*`. English only.
- **Process rules (this machine):** reading, building and native tests only until Task 10. No game, launcher or browser window while the owner is at the machine (a window steals focus). Never terminate processes by image name; stop only a process you started, by PID. Build only through `tools/port/build.sh` in a private worktree made by `tools/port/agent_new.sh`; never raw clang for the game. Max 8 `melee-pc` instances in total; keep 2 GB free. Two repositories: game repo `melee/` (branch `pc-port`, your lane `agent/<name>`) and the workspace repo (tools, docs, `CREDITS.md`); each task says which gets the commit. `gw_mex_bridge.c` churn from `build.sh` is normal and is not committed by you.

## Needs from earlier steps (gated by Task 0)

The names in the last column are the spec's names or this plan's assumed ones; Task 0 greps for them and the engineer writes the real names into the table in `tools/port/atlas_gate.py` and into the one wrapper in `gw_ui_room.c` that calls each (marked `RECONCILE`).

| # | What step 6 needs | From | Spec name or assumed name | Used by |
|---|---|---|---|---|
| N1 | A screen submitted from game-side C, drawn, ticked and hit-tested **without a script** and in frontend scenes (the step 1 binding is script-slot only; spec 18 lists "script hooks run during frontend scenes" as unverified) | step 2 (U5, U8) | `GM/gmfrontend_atlas.inc`, `fa_submit`, `fa_frame`, `gw_Ui_PollEvent`, `FrontendScreen.atlas` | Tasks 7, 8 |
| N2 | An Atlas fade quad for native scenes (the game's own fade does not cover host-drawn quads, 6.1 (b)) | step 2 | an `at_fade` call or the stack's own | Task 8 |
| N3 | The registry: entries by parent `online`, the MOD tag, hidden while a session exists unless `"online": true` | step 2 (U6) | `at_registry_entries(parent, ...)` | Task 8 |
| N4 | Value rows through the adapter: `FE_CHOICE`, `FE_SLIDER`, `FE_TOGGLE` with `get`, `set` and `format` | step 5 | `fa_submit` item kinds | Task 8 |
| N5 | A port card part (numeral plus shape plus colour, name, sub line, tag) and its link to a fighter icon cell | step 4 | `at_part_portcard`, `AtPortCard` | Task 5 |
| N6 | Stage cells that can show struck, banned and picked | step 4 | cell flags and tag | Task 5 (the room composite draws its own tags, so this is soft: see Task 5) |
| N7 | The one character select with an online (lobby) profile: one local port, blind pick, locked | step 4 | mode profile `online` | Task 8 (soft: `fe_np_pick_char` opens whatever CSS is current) |
| N8 | The native mouse source (hits and wheel) for game-side screens | step 2 | `fms` replaced by the adapter's events | Tasks 6, 8 |

## Review Focus

The failure modes most likely to bite first. Each is pinned by a named test.

| # | What goes wrong | Pinned by |
|---|---|---|
| 1 | **Presentation reaches the netplay stream or desyncs a lobby**: a draw-side change alters what A, START, B or a stage click does; mouse or keyboard produces a different call than the pad would. | Task 6 `intents` (the same job three ways, hover alone, a resting and an off-picture pointer); `tools/port/check_atlas_online.sh` guards 1 to 6 (no netplay in the host files, a read-only allow-list in the adapter, the intent-to-bit table, the untouched pad term) |
| 2 | **Focus on nothing after the room changes under it**: the stage list arrives late (a guest waits for it), shrinks (a stage struck), or the phase changes to RECONNECTING while the cursor is on a tile; a page turns while the cursor is on the last page. | Task 4 `cursor` and `grid` (every list size from 0 to 32, every column count), Task 5 `render` (focus only on my own stage turn, never while reconnecting) |
| 3 | **A stale view**: the screen is left (leave, peer left, match start) and the next frame still draws the old room, or the draw reads a view that was freed. | Task 5 `render` (a NULL view draws nothing and chrome only), Task 7 `lifetime` (End clears the view, calls after End are refused, a copy not a pointer) |
| 4 | **Text overflow**: a 15-character player name, a `Netplay_MenuStatus` server sentence, a 96-character instruction, a stage name such as "Princess Peach's Castle" or an m-ex stage "Stage 147" at 640 wide and at 1140. | Task 5 `render` (the 4,320-view fixture at 640, 853 and 1140, linted for text inside the primary and no overlap), Task 8 step 6 (the rows' help strings) |
| 5 | **Style rule breaks in this plan's own code**: a chamfer on the wrong corner, a focus with fewer than three cues, a card tag wider than its plate. | Task 1 lint helpers, used by every part and composite test |
| 6 | **Tests that pass only as the developer**: the room screens are native, so there is no console to hide behind, but the same trap exists as "tests that only run with a good connection". Every room test runs the offline and the no-link (`ping -1`) and the reconnecting views. | Task 4 `fill` and Task 5 `render` (every kind, phase, side, link state, rule set and list size of the fixture) |
| 7 | **The Envoy reward pick while the lobby waits** (`Netplay_LobbyInfo(13)`): the lobby must keep today's input behaviour; this step must not add suppression or take focus from the Envoy script. | Task 6 `intents` (the reward-open block: same intents and keys with it open or closed); Task 10 step 9 |
| 8 | **Link meter flicker**: a ping hovering on a threshold changes the bar count every frame. | Task 2 `bars` (the 100-reading flicker check), Task 7 `ping` |
| 9 | **The blind pick leaks**: in game 1 the opponent's fighter must stay hidden ("Locked in") until both have locked. A new drawing path that reads the opponent's fighter for its card shows it early. | `check_atlas_online.sh` guard 7 (the one `Netplay_FighterName` call sits after the legacy `fl_card_portrait` test); Task 10 step 4 |

---

## File structure

Game repo (`melee/`).

| File | Create/Modify | Responsibility |
|---|---|---|
| `pc/platform/gw_ui_online_parts.h/.c` | Create | `at_link_bars`, `at_part_link`, `at_part_code`, `at_part_code_slot_rect` |
| `pc/platform/gw_ui_room.h/.c` | Create | `AtRoomView`, `at_room_screen`, stage paging, the composite render, hit rectangles, `AtRoomIntent` and the event mapping |
| `pc/platform/gw_ui_screen.h` | Modify | `AT_PRIMARY_ROOM`, `AtView.room` (a borrowed pointer) |
| `pc/platform/gw_ui_render.c` | Modify | one branch: a room primary calls `at_room_render` |
| `pc/platform/gw_ui_room_native.c` | Create | the `gw_Ui_Room*` shims and the singleton view (the only door the game side uses) |
| `pc/tests/atlas_lint.h`, `atlas_lint_test.c` | Create | style-rule checks over a recorded sink, and their own fixtures |
| `pc/tests/atlas_online_parts_test.c`, `atlas_room_test.c` | Create | the parts, the view, the composite, the intent stream |
| `src/melee/gm/gmfrontend_atlas_online.inc` | Create | the adapter: view submission, event to `MenuInput_*`, the Atlas branches of the room frames |
| `src/melee/gm/gmfrontend_online.inc`, `gmfrontend.c` | Modify | a few `if (fa_room_active())` branches; `.atlas` on the four screens |

Workspace repo (root).

| File | Create/Modify | Responsibility |
|---|---|---|
| `tools/port/atlas_gate.py` | Create | the Task 0 gate (also used by step 7: it takes `--step`) |
| `tools/port/check_atlas_online.sh` | Create | the netplay-isolation guards (greps) |
| `tools/port/check_atlas_online_text.py`, `test_check_atlas_online_text.py` | Create | lint of the online rows' help strings against the explainer limit |
| `tools/port/native_test.sh` | Modify | cases `atlas-lint`, `atlas-online-parts`, `atlas-room` |
| `tools/port/README.md`, `docs/NEXT-SESSION.md` | Modify | the checks and the state |

## Preflight (once, before Task 0; not a task)

- [ ] **Step 1: Read.** `CLAUDE.md` (root), `docs/NEXT-SESSION.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md`, the spec sections 4, 6, 8.4, 9, 13.6, the step 1 plan's Preflight and Task 11 (the binding), `melee/src/melee/gm/gmfrontend_online.inc` from its header comment to `fl_frame_lobby`, `gmfrontend.c` lines 280 to 330 and 500 to 650, `pc/platform/gw_netplay.c` from `gw_Netplay_LobbyPhase` to `gw_Netplay_LobbyReady`.
- [ ] **Step 2: A private lane and the shell** (same as step 1; names changed):

```bash
export MAIN="<the workspace root: the directory that contains tools/ and _toolchains/>"
cd "$MAIN" && tools/port/agent_new.sh atlas6
git -C "$MAIN" worktree add worktrees/ws-atlas6 -b ws/atlas6
export WS="$MAIN/worktrees/ws-atlas6"; export GW_ROOT="$MAIN"
export GW_MELEE="$MAIN/worktrees/atlas6"; export GW_BUILD_ROOT="$MAIN/_build/agents/atlas6"   # as agent_new.sh printed them
nt() { GW_ROOT="$MAIN" GW_MELEE="$GW_MELEE" GW_BUILD_ROOT="$GW_BUILD_ROOT" bash "$WS/tools/port/native_test.sh" "$1"; }
```

`nt NAME` runs YOUR copy of `native_test.sh` against your game worktree. Workspace commands run in `$WS`, game commands in `$GW_MELEE`, builds in `$MAIN` with the exports above.
- [ ] **Step 3: Baselines** (must still pass at the end):

```bash
for t in atlas-tokens atlas-layout atlas-focus atlas-input atlas-screen atlas-stack atlas-parts atlas-render atlas-binding; do nt $t | tail -1; done
cd "$GW_MELEE" && lua pc/tests/atlas_ui_stub_test.lua | tail -1
```

Expected: every line ends `N checks, 0 failed` (or the stub test's own pass line).

---

### Task 0: The gate: what earlier steps must have delivered

**Files:**
- Create (workspace repo): `tools/port/atlas_gate.py`

**Interfaces:**
Consumes: the game checkout (`GW_MELEE`). Produces: exit status 0 when every `--step 6` requirement is present; otherwise a list of what is missing and which earlier step owes it. Step 7's plan uses the same script with `--step 7`.

Tasks 1 to 4 need only step 1 and may start before the gate passes. **Tasks 5 to 9 start only when `python tools/port/atlas_gate.py --step 6` exits 0**, except where a task says "soft".

- [ ] **Step 1: Write the script.**

```python
"""Gate: has every earlier Atlas step delivered what this step needs?

    python tools/port/atlas_gate.py --step 6 [--melee PATH]

Each requirement is (file under the game checkout, regex, owner, why). A missing one is printed and the exit status is 1.
When a name differs from the one written here, the earlier step's real name goes into this table AND into the plan's
"Needs" table in the same commit; do not weaken a regex to make the gate pass.
"""
import argparse
import os
import re
import sys

G = {
    6: [
        ("src/melee/gm/gmfrontend_atlas.inc", r"\bfa_submit\b", "step 2", "N1 the game-side adapter submits a screen"),
        ("src/melee/gm/gmfrontend_atlas.inc", r"gw_Ui_PollEvent", "step 2", "N1/N8 events come back to the game side"),
        ("src/melee/gm/gmfrontend.c", r"\batlas\b", "step 2", "N1 FrontendScreen has an atlas field"),
        ("pc/platform/gw_ui_registry.h", r"at_registry", "step 2", "N3 the registry"),
        ("pc/platform/gw_ui_parts.h", r"at_part_portcard", "step 4", "N5 the port card part"),
        ("src/melee/gm/gmfrontend_atlas.inc", r"\bFE_CHOICE\b|\bFE_SLIDER\b", "step 5", "N4 value rows through the adapter"),
    ],
    7: [],  # filled by the step 7 plan, Task 0
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, required=True)
    ap.add_argument("--melee", default=os.environ.get("GW_MELEE", ""))
    a = ap.parse_args(argv)
    root = a.melee
    if not root or not os.path.isdir(root):
        print("gate: set GW_MELEE or pass --melee")
        return 2
    missing = 0
    for rel, rx, owner, why in G[a.step]:
        path = os.path.join(root, rel)
        text = open(path, encoding="utf-8", errors="replace").read() if os.path.exists(path) else None
        if text is None or not re.search(rx, text):
            print("MISSING  %-46s %-8s %s (%s)" % (rel, owner, why, rx))
            missing += 1
    print("gate step %d: %d missing" % (a.step, missing))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it before starting and record the result.**

```bash
cd "$WS" && python tools/port/atlas_gate.py --step 6
```

Expected today (steps 2 to 5 unbuilt): six `MISSING` lines and `gate step 6: 6 missing`, exit 1. That is correct: it proves the gate can fail. When the earlier steps merge, the engineer reconciles names (see the header of the script), and the exit becomes 0.
- [ ] **Step 3: Commit.** Workspace repo: `tools/port/atlas_gate.py`, message `tools: atlas_gate.py, the check that earlier Atlas steps delivered what a later one needs`.

---

### Task 1: Style-rule lint helpers (the lesson from step 1, built first)

Step 1's review found style breaks in its own code: chamfers on the wrong corner, focus with fewer than three cues, text running out of its plate. Every composite in this plan is tested with these helpers, so a violation fails a test instead of reaching the owner's eye.

**Files:**
- Create (game repo): `pc/tests/atlas_lint.h`, `pc/tests/atlas_lint_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-lint`)

**Interfaces:**
Consumes: `atlas_check.h`, `atlas_fake.h`, `atlas_rec.h`, `gw_ui_parts.h`. Produces (static functions in a header, used by Tasks 2, 3, 5 and by step 7): `lint_covered(x, y)`, `lint_plate_corners(AtRect r, float chamfer)`, `lint_text_inside(AtRect r, int from)`, `lint_text_overlaps()`, `lint_focus_row(AtRect rest)`, `lint_focus_cell(AtRect rest, unsigned focus_rgba)`. Each returns the number of violations (0 = clean).

- [ ] **Step 1: Write the failing test.** Create `pc/tests/atlas_lint_test.c`:

```c
#include "atlas_lint.h"
#include "../platform/gw_ui_tokens.h"

/* a plate with the WRONG chamfer (top-right and bottom-left cut), built from three convex bands */
static void bad_plate(const AtSink *s, AtRect r, float c, unsigned rgba)
{
    float xa[4] = { r.x, r.x + r.w - c, r.x + r.w, r.x },               ya[4] = { r.y, r.y, r.y + c, r.y + c };
    float xb[4] = { r.x, r.x + r.w, r.x + r.w, r.x },                   yb[4] = { r.y + c, r.y + c, r.y + r.h - c, r.y + r.h - c };
    float xc[4] = { r.x, r.x + r.w, r.x + r.w, r.x + c },               yc[4] = { r.y + r.h - c, r.y + r.h - c, r.y + r.h, r.y + r.h };
    s->poly(s->user, xa, ya, rgba);
    s->poly(s->user, xb, yb, rgba);
    s->poly(s->user, xc, yc, rgba);
}

int main(void)
{
    AtRect r = { 40.0f, 60.0f, 120.0f, 34.0f };
    AtSink s;

    /* the real plate passes: TL and BR cut, TR and BL square */
    s = rec_sink(); at_plate(&s, r, AT_C_PLATE2, AT_C_EDGE2, 3.0f, 5.0f);
    CHECK(lint_plate_corners(r, 5.0f) == 0);
    /* a hand-made TR/BL chamfer fails on all four corners */
    s = rec_sink(); bad_plate(&s, r, 8.0f, AT_C_PLATE2);
    CHECK(lint_plate_corners(r, 8.0f) == 4);
    /* a chamfer of 2 px or less is not probed (a 1 px inset cannot tell it from square) */
    s = rec_sink(); at_poly_rect(&s, r.x, r.y, r.w, r.h, AT_C_PLATE2);
    CHECK(lint_plate_corners(r, 2.0f) == 0);

    /* text inside / overlapping, with the fake width (half the role size per character) */
    s = rec_sink();
    at_text(&s, &FAKE, AT_R_ROW16, "Short", 50.0f, 80.0f, AT_C_IVORY, AT_ALIGN_LEFT, 0.0f);
    CHECK(lint_text_inside(r, 0) == 0);
    at_text(&s, &FAKE, AT_R_ROW16, "This label is far too long for its plate", 50.0f, 80.0f, AT_C_IVORY, AT_ALIGN_LEFT, 0.0f);
    CHECK(lint_text_inside(r, 0) == 1);                     /* the second text runs out */
    s = rec_sink();
    at_text(&s, &FAKE, AT_R_ROW16, "AAAAAAAA", 50.0f, 80.0f, AT_C_IVORY, AT_ALIGN_LEFT, 0.0f);
    at_text(&s, &FAKE, AT_R_ROW16, "BBBBBBBB", 80.0f, 82.0f, AT_C_IVORY, AT_ALIGN_LEFT, 0.0f);
    CHECK(lint_text_overlaps() == 1);
    s = rec_sink();
    at_text(&s, &FAKE, AT_R_ROW16, "AAAA", 50.0f, 80.0f, AT_C_IVORY, AT_ALIGN_LEFT, 0.0f);
    at_text(&s, &FAKE, AT_R_ROW16, "BBBB", 120.0f, 80.0f, AT_C_IVORY, AT_ALIGN_LEFT, 0.0f);
    CHECK(lint_text_overlaps() == 0);

    /* focus cues: a row at rest has none, a focused row has all three, a half-focused one fails */
    {
        AtItem it; memset(&it, 0, sizeof it); snprintf(it.label, sizeof it.label, "Row");
        s = rec_sink(); at_part_row(&s, &FAKE, r, &it, AT_ST_FOCUS);
        CHECK(lint_focus_row(r) == 0);
        s = rec_sink(); at_part_row(&s, &FAKE, r, &it, AT_ST_REST);
        CHECK(lint_focus_row(r) == 3);                      /* no lift, no ember edge, no tick */
        s = rec_sink(); at_plate(&s, r, AT_C_LIFT, AT_C_EMBER, 3.0f, 5.0f);   /* edge and face but no lift and no tick */
        CHECK(lint_focus_row(r) == 2);
    }
    {
        AtCell c; memset(&c, 0, sizeof c); c.model = AT_NO_MODEL; snprintf(c.name, sizeof c.name, "Cell");
        AtRect cr = { 100.0f, 200.0f, 48.0f, 48.0f };
        s = rec_sink(); at_part_cell(&s, &FAKE, cr, &c, AT_ST_FOCUS, AT_C_EMBER);
        CHECK(lint_focus_cell(cr, AT_C_EMBER) == 0);
        s = rec_sink(); at_part_cell(&s, &FAKE, cr, &c, AT_ST_REST, AT_C_EMBER);
        CHECK(lint_focus_cell(cr, AT_C_EMBER) == 3);
    }
    ATLAS_DONE("atlas lint");
}
```

Register the case in `tools/port/native_test.sh` before the `*)` line (and append `, atlas-lint` to the die message):

```bash
atlas-lint)
    sources=(pc/tests/atlas_lint_test.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c) ;;
```

- [ ] **Step 2: Run to verify it fails.**

```bash
nt atlas-lint
```

Expected: `fatal error: 'atlas_lint.h' file not found`.

- [ ] **Step 3: Write the implementation.** Create `pc/tests/atlas_lint.h`:

```c
/* Style-rule checks over a recorded sink (atlas_rec.h), used by every Atlas screen test. Each returns the number of
 * violations. The rules are the spec's: 4.1 chamfers (top-left and bottom-right only), 4.6 focus (three cues at once),
 * 10 text (12 px floor, nothing outside its plate, nothing on top of other text). Include once per test. */
#ifndef ATLAS_LINT_H
#define ATLAS_LINT_H
#include "atlas_check.h"
#include "atlas_fake.h"
#include "atlas_rec.h"
#include "../platform/gw_ui_tokens.h"

/* is the point inside a recorded convex quad (either winding; a triangle has a repeated vertex) */
static int lint_in_poly(const RecPoly *p, float x, float y)
{
    int i, pos = 0, neg = 0;
    for (i = 0; i < 4; i++) {
        int j = (i + 1) % 4;
        float cr = (p->x[j] - p->x[i]) * (y - p->y[i]) - (p->y[j] - p->y[i]) * (x - p->x[i]);
        if (cr > 0.001f) pos++; else if (cr < -0.001f) neg++;
    }
    return pos == 0 || neg == 0;
}

static int lint_covered(float x, float y)
{
    int i;
    for (i = 0; i < REC.np; i++) if (lint_in_poly(&REC.p[i], x, y)) return 1;
    return 0;
}

/* The chamfer rule. A plate of rectangle r with chamfer c > 2 px leaves the pixel just inside its top-left and its
 * bottom-right corner empty and the other two covered. (Probing the silhouette, not the polygons, because a plate is
 * several convex quads and their inner diagonals say nothing about the corners.) Probe ONE plate on a fresh sink. */
static int lint_plate_corners(AtRect r, float c)
{
    int bad = 0;
    if (c <= 2.0f) return 0;
    if (lint_covered(r.x + 1.0f, r.y + 1.0f)) bad++;                    /* top-left must be cut */
    if (lint_covered(r.x + r.w - 1.0f, r.y + r.h - 1.0f)) bad++;        /* bottom-right must be cut */
    if (!lint_covered(r.x + r.w - 1.0f, r.y + 1.0f)) bad++;             /* top-right must be square */
    if (!lint_covered(r.x + 1.0f, r.y + r.h - 1.0f)) bad++;             /* bottom-left must be square */
    return bad;
}

static void lint_text_box(const RecText *t, float *x0, float *x1, float *y0, float *y1)
{
    float w = FAKE.width(FAKE.user, t->role, t->s), sz = (float) at_role_size(t->role);
    *x0 = t->align == AT_ALIGN_LEFT ? t->x : t->align == AT_ALIGN_CENTER ? t->x - w * 0.5f : t->x - w;
    *x1 = *x0 + w;
    *y0 = t->base - sz * 0.8f;
    *y1 = t->base + sz * 0.2f;
}

/* texts [from, REC.nt) must lie inside r, and be at least 12 px */
static int lint_text_inside(AtRect r, int from)
{
    int i, bad = 0;
    for (i = from; i < REC.nt; i++) {
        float x0, x1, y0, y1;
        lint_text_box(&REC.t[i], &x0, &x1, &y0, &y1);
        if (at_role_size(REC.t[i].role) < 12) { bad++; continue; }
        if (x0 < r.x - 0.5f || x1 > r.x + r.w + 0.5f || y0 < r.y - 0.5f || y1 > r.y + r.h + 0.5f) bad++;
    }
    return bad;
}

/* no two texts overlap by more than 1 px in both axes (overflow into a neighbour) */
static int lint_text_overlaps(void)
{
    int i, j, bad = 0;
    for (i = 0; i < REC.nt; i++) for (j = i + 1; j < REC.nt; j++) {
        float a0, a1, b0, b1, c0, c1, d0, d1;
        lint_text_box(&REC.t[i], &a0, &a1, &b0, &b1);
        lint_text_box(&REC.t[j], &c0, &c1, &d0, &d1);
        if (a0 < c1 - 1.0f && c0 < a1 - 1.0f && b0 < d1 - 1.0f && d0 < b1 - 1.0f) bad++;
    }
    return bad;
}

static float lint_top(void)
{
    float top = 1e9f; int i;
    for (i = 0; i < REC.np; i++) if (poly_miny(&REC.p[i]) < top) top = poly_miny(&REC.p[i]);
    return top;
}

/* A focused row: lifted 2 px, an ember front edge, an ember tick (two ember polys), the lift face. Returns the number
 * of the three cues missing. `rest` is the rectangle the row has at rest. */
static int lint_focus_row(AtRect rest)
{
    int bad = 0;
    if (lint_top() > rest.y - 1.5f) bad++;                       /* the lift */
    if (count_color(AT_C_EMBER) < 1) bad++;                      /* the edge */
    if (count_color(AT_C_EMBER) < 2) bad++;                      /* the tick (edge plus tick = two) */
    return bad;
}

/* A focused cell: lifted 2 px, ember front edge, and four registration brackets (at least four small polys of the
 * focus colour: a bracket is two thin strips). */
static int lint_focus_cell(AtRect rest, unsigned focus_rgba)
{
    int i, bad = 0, small = 0;
    if (lint_top() > rest.y - 1.5f) bad++;
    if (count_color(AT_C_EMBER) < 1) bad++;
    for (i = 0; i < REC.np; i++)
        if (REC.p[i].rgba == focus_rgba && poly_maxx(&REC.p[i]) - poly_minx(&REC.p[i]) <= 14.0f &&
            poly_maxy(&REC.p[i]) - poly_miny(&REC.p[i]) <= 14.0f) small++;
    if (small < 4) bad++;
    return bad;
}
#endif
```

- [ ] **Step 3b: Reconcile against the real parts.** The two focus counts assume what `at_part_row` and `at_part_cell` draw today (ember edge plus an ember tick for a row; brackets for a cell). If the test shows a count different from the one above, read the part (`gw_ui_parts.c`) and the existing `atlas_parts_test.c` and fix the lint's expectation to match the part, never the part to match the lint. The lint's job is to fail when a later part loses a cue.

- [ ] **Step 4: Run the test.**

```bash
nt atlas-lint
```

Expected: `atlas lint: 12 checks, 0 failed` (the count may change if the reconcile above adds a check; it must end `0 failed`).

- [ ] **Step 5: Commit.** Game repo: `pc/tests/atlas_lint.h`, `pc/tests/atlas_lint_test.c`, message `atlas tests: style-rule lint helpers (chamfer corners, focus cues, text overflow)`. Workspace repo: `tools/port/native_test.sh`, message `tools: atlas-lint native test`.

---

### Task 2: The link meter (connection quality, with hysteresis)

The room shows connection quality. `Netplay_Ping()` returns the round trip in ms, or -1 with no link. A meter that redraws a different bar count every frame while the ping hovers on a threshold is the flicker in Review Focus 8, so the bar count has memory.

**Files:**
- Create (game repo): `pc/platform/gw_ui_online_parts.h`, `pc/platform/gw_ui_online_parts.c`, `pc/tests/atlas_online_parts_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-online-parts`)

**Interfaces:**
Consumes: `AtSink`, `AtTextOps`, `at_text`, `at_poly_rect` (step 1), `AT_C_*` (tokens).
Produces: `int at_link_bars(int ms, int prev_bars)` (0 to 4; `ms < 0` is 0; the caller keeps the result as the next `prev_bars`), `AtLinkInfo at_link_info(int bars)`, `float at_part_link(sink, ops, x, base, bars, ms, with_word)` (returns its advance).

The thresholds are this plan's proposal and are **unmeasured against play** (4 bars up to 50 ms, 3 up to 90, 2 up to 140, 1 above; a move to a worse count needs 8 ms past the line, to a better one 8 ms inside it). The words are GOOD (4, 3), FAIR (2), POOR (1), NO LINK (0): the bars and the word say the same thing, so colour is never the only signal.

- [ ] **Step 1: Write the failing test.** Create `pc/tests/atlas_online_parts_test.c`:

```c
#include "atlas_lint.h"
#include "../platform/gw_ui_online_parts.h"

static void bars(void)
{
    int i, b, changes;
    CHECK(at_link_bars(-1, 3) == 0);                    /* no link */
    CHECK(at_link_bars(20, 0) == 4 && at_link_bars(50, 0) == 4 && at_link_bars(51, 0) == 3);   /* first reading: the raw bar count */
    CHECK(at_link_bars(90, 0) == 3 && at_link_bars(91, 0) == 2 && at_link_bars(140, 0) == 2 && at_link_bars(141, 0) == 1);
    CHECK(at_link_bars(55, 4) == 4 && at_link_bars(58, 4) == 4 && at_link_bars(59, 4) == 3);   /* worse: 8 ms past the line */
    CHECK(at_link_bars(45, 3) == 3 && at_link_bars(42, 3) == 4);                               /* better: 8 ms inside it */
    CHECK(at_link_bars(500, 4) == 1);                                                          /* several steps in one reading */
    CHECK(at_link_bars(5, 1) == 4);
    /* flicker: a ping alternating across each line changes the count at most once in 100 readings */
    {
        static const int line[3] = { 50, 90, 140 };
        for (i = 0; i < 3; i++) {
            int k;
            b = 0; changes = 0;
            for (k = 0; k < 100; k++) {
                int nb = at_link_bars(line[i] + (k & 1 ? 3 : -3), b);
                if (b != 0 && nb != b) changes++;
                b = nb;
            }
            CHECK(changes <= 1);
        }
    }
}

static void part(void)
{
    AtSink s;
    AtRect box = { 20.0f, 10.0f, 150.0f, 20.0f };
    float adv;
    int b;
    for (b = 0; b <= 4; b++) {
        AtLinkInfo li = at_link_info(b);
        s = rec_sink();
        adv = at_part_link(&s, &FAKE, box.x, box.y + 16.0f, b, b ? 40 : -1, 1);
        CHECK(li.bars == b && li.word != NULL && find_text(li.word) != NULL);       /* a word for every count */
        CHECK(count_color(b ? li.rgba : AT_C_LINE) >= (b ? b : 4));                  /* the lit bars (or four empty ones) */
        CHECK(adv > 18.0f && adv <= box.w);                                          /* bars are 18 px wide, the rest fits the box */
        CHECK(lint_text_inside(box, 0) == 0 && lint_text_overlaps() == 0);
        CHECK(b == 0 ? find_text("40 ms") == NULL : find_text("40 ms") != NULL);     /* no number with no link */
    }
    s = rec_sink();
    adv = at_part_link(&s, &FAKE, 0.0f, 16.0f, 3, 61, 0);
    CHECK_NEAR(adv, 18.0f);                                                          /* without the word: just the bars */
    CHECK(REC.nt == 0);
}

int main(void)
{
    bars();
    part();
    ATLAS_DONE("atlas online parts");
}
```

Register in `tools/port/native_test.sh` (and append `, atlas-online-parts` to the die message):

```bash
atlas-online-parts)
    sources=(pc/tests/atlas_online_parts_test.c pc/platform/gw_ui_online_parts.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c) ;;
```

- [ ] **Step 2: Run to verify it fails.** `nt atlas-online-parts`. Expected: `fatal error: '../platform/gw_ui_online_parts.h' file not found`.
- [ ] **Step 3: Write the implementation.** Create `pc/platform/gw_ui_online_parts.h`:

```c
/* gw_ui_online_parts.h - Atlas parts the online screens need: the link meter and the room-code field. Pure C. */
#ifndef GW_UI_ONLINE_PARTS_H
#define GW_UI_ONLINE_PARTS_H
#include "gw_ui_parts.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct { int bars; const char *word; unsigned rgba; } AtLinkInfo;
int at_link_bars(int ms, int prev_bars);   /* 0..4; ms < 0 = no link; prev_bars (0 = none yet) gives the 8 ms dead band */
AtLinkInfo at_link_info(int bars);
float at_part_link(const AtSink *s, const AtTextOps *o, float x, float base, int bars, int ms, int with_word);

typedef struct { char c[4]; int slot; int invalid; } AtCodeView;   /* c[i] == 0: an empty slot */
#define AT_CODE_BAND 18.0f                                          /* the strip above and below the active slot: step up / down */
AtRect at_code_slot_rect(AtRect field, int i);                      /* four slots, centred; at most 64 x 84 */
/* what is under the point: 0 nothing, 1 a slot (*arg = its index), 2 the active slot's up strip, 3 its down strip */
int at_code_hit(AtRect field, int active, float px, float py, int *arg);
void at_part_code(const AtSink *s, const AtTextOps *o, AtRect field, const AtCodeView *v);

#ifdef __cplusplus
}
#endif
#endif
```

Create `pc/platform/gw_ui_online_parts.c` (the link meter now; the code field is appended in Task 3):

```c
#include "gw_ui_online_parts.h"
#include "gw_ui_tokens.h"
#include <ctype.h>
#include <stdio.h>
#include <string.h>

/* bars b holds up to this many ms (4: 50, 3: 90, 2: 140; 1 has no upper line) */
static int limit_ms(int bars) { return bars == 4 ? 50 : bars == 3 ? 90 : bars == 2 ? 140 : 1000000; }

int at_link_bars(int ms, int prev)
{
    int b = prev;
    if (ms < 0) return 0;
    if (b < 1 || b > 4) b = ms <= 50 ? 4 : ms <= 90 ? 3 : ms <= 140 ? 2 : 1;   /* the first reading has no memory */
    while (b > 1 && ms > limit_ms(b) + 8) b--;
    while (b < 4 && ms <= limit_ms(b + 1) - 8) b++;
    return b;
}

AtLinkInfo at_link_info(int bars)
{
    AtLinkInfo i;
    if (bars < 0 || bars > 4) bars = 0;
    i.bars = bars;
    switch (bars) {
    case 4: case 3: i.word = "GOOD"; i.rgba = AT_C_JADE; break;
    case 2: i.word = "FAIR"; i.rgba = AT_C_SUN; break;
    case 1: i.word = "POOR"; i.rgba = AT_C_ROSE; break;
    default: i.word = "NO LINK"; i.rgba = AT_C_DIM; break;
    }
    return i;
}

float at_part_link(const AtSink *s, const AtTextOps *o, float x, float base, int bars, int ms, int with_word)
{
    AtLinkInfo li = at_link_info(bars);
    float bx = x, w;
    int i;
    for (i = 0; i < 4; i++) {
        float h = 5.0f + 3.0f * (float) i;
        at_poly_rect(s, bx, base - h, 3.0f, h, i < li.bars ? li.rgba : AT_C_LINE);
        bx += 5.0f;
    }
    w = bx - x - 2.0f;                                                   /* 4 bars of 3 px with 2 px gaps: 18 px */
    if (with_word) {
        at_text(s, o, AT_R_CAP12, li.word, x + w + 6.0f, base, li.bars ? AT_C_IVORY : AT_C_MUTED, AT_ALIGN_LEFT, 0.0f);
        w += 6.0f + o->width(o->user, AT_R_CAP12, li.word);
        if (ms >= 0 && li.bars > 0) {
            char num[16];
            snprintf(num, sizeof num, "%d ms", ms);
            at_text(s, o, AT_R_NUM12, num, x + w + 8.0f, base, AT_C_MUTED, AT_ALIGN_LEFT, 0.0f);
            w += 8.0f + o->width(o->user, AT_R_NUM12, num);
        }
    }
    return w;
}
```

- [ ] **Step 4: Run.** `nt atlas-online-parts`. Expected: `atlas online parts: 47 checks, 0 failed` (the count is approximate; it must end `0 failed`). If the `adv > 18.0f` check fails for `b == 0`, the word is wider than nothing: with the word the advance is 18 + 6 + the word width, so it holds; a failure means the word is not drawn.
- [ ] **Step 5: Commit.** Game repo: the three new files, message `atlas online: the link meter part with hysteresis`. Workspace repo: `tools/port/native_test.sh`, message `tools: atlas-online-parts native test`.

---

### Task 3: The room-code field

JOIN ROOM is four slots. Up and down change a letter, left and right move between slots, Y pastes, A joins; typed letters still arrive through `Netplay_CodeKeys` on the game side. The field draws the slots and answers "what is under the pointer"; it never edits the code (the netplay layer owns it).

**Files:**
- Modify (game repo): `pc/platform/gw_ui_online_parts.c` (append), `pc/tests/atlas_online_parts_test.c`

**Interfaces:**
Consumes: `AtCodeView`, `at_plate`, `at_text` (roles `AT_R_DISPLAY`, `AT_R_NUM16`). Produces: `at_code_slot_rect`, `at_code_hit`, `at_part_code` as declared in Task 2.

Rules this part must obey, each pinned below: the active slot has all three focus cues (lift 2, ember front edge, four registration brackets) plus the up and down chevrons; the other slots are 3 px-chamfer cells; an invalid code is shown with rose edges AND by the caller's word (the field itself carries no word, so the screen must: Task 5 draws "NOT FOUND" under it); the glyph is upper-case (the `display` role is caps only); a narrow field shrinks its slots and the fit rule steps the glyph down a role rather than overflowing.

- [ ] **Step 1: Add the failing tests** to `pc/tests/atlas_online_parts_test.c` (before `main`, and call `code();` from `main`):

```c
static AtCodeView cv(const char *chars, int slot, int invalid)
{
    AtCodeView v; int i;
    memset(&v, 0, sizeof v);
    for (i = 0; i < 4 && chars[i]; i++) v.c[i] = chars[i];
    v.slot = slot; v.invalid = invalid;
    return v;
}

static void code(void)
{
    AtRect f = { 100.0f, 120.0f, 300.0f, 120.0f };
    AtSink s;
    AtCodeView v;
    int i, arg = -1;
    /* geometry: four slots inside the field, centred, never wider than 64 x 84, no overlap */
    for (i = 0; i < 4; i++) {
        AtRect r = at_code_slot_rect(f, i);
        CHECK(r.w <= 64.0f && r.h <= 84.0f && r.x >= f.x && r.x + r.w <= f.x + f.w && r.y >= f.y + AT_CODE_BAND - 0.1f);
        if (i > 0) { AtRect p = at_code_slot_rect(f, i - 1); CHECK(r.x >= p.x + p.w + 11.0f); }
    }
    /* the active slot: three cues (lift, ember edge, brackets) and chevrons */
    v = cv("AB", 2, 0);
    s = rec_sink(); at_part_code(&s, &FAKE, f, &v);
    CHECK(lint_focus_cell(at_code_slot_rect(f, 2), AT_C_EMBER) == 0);
    CHECK(find_text("A") != NULL && find_text("B") != NULL && REC.nt == 4);          /* A, B and two dashes */
    CHECK(count_color(AT_C_MUTED) >= 2);                                             /* the chevrons */
    /* the other slots keep the chamfer rule (probe one on a fresh sink: the active slot's brackets are outside it) */
    v = cv("ABCD", 0, 0);
    s = rec_sink(); at_part_code(&s, &FAKE, f, &v);
    CHECK(find_text("D") != NULL);
    {
        AtSink s2 = rec_sink(); AtCodeView solo = cv("ABCD", 9, 0);                  /* slot 9: nothing active */
        at_part_code(&s2, &FAKE, f, &solo);
        for (i = 0; i < 4; i++) CHECK(lint_plate_corners(at_code_slot_rect(f, i), 3.0f) == 0);
        CHECK(count_color(AT_C_EMBER) == 0);                                         /* no focus anywhere: no ember */
    }
    /* lower case is shown in capitals (the role is caps only) */
    v = cv("abcd", 0, 0);
    s = rec_sink(); at_part_code(&s, &FAKE, f, &v);
    CHECK(find_text("A") != NULL && find_text("a") == NULL);
    /* invalid: rose edges on the three non-active slots, the active one stays ember */
    v = cv("ABCD", 1, 1);
    s = rec_sink(); at_part_code(&s, &FAKE, f, &v);
    CHECK(count_color(AT_C_ROSE) == 3 && count_color(AT_C_EMBER) >= 1);
    /* the widest glyph in a normal field, a narrow one and a very narrow one: every text inside its slot, 12 px or more */
    {
        static const float widths[3] = { 300.0f, 200.0f, 150.0f };
        int k;
        for (k = 0; k < 3; k++) {
            AtRect nf = { 50.0f, 100.0f, widths[k], 120.0f };
            v = cv("WWWW", 0, 0);
            s = rec_sink(); at_part_code(&s, &FAKE, nf, &v);
            CHECK(texts_legible());
            for (i = 0; i < 4; i++) {                                                /* glyph i belongs to slot i (drawn in order) */
                RecText t = REC.t[i];
                AtRect slot = at_code_slot_rect(nf, i);
                float w = FAKE.width(FAKE.user, t.role, t.s);
                CHECK(t.x - w * 0.5f >= slot.x - 0.5f && t.x + w * 0.5f <= slot.x + slot.w + 0.5f);
            }
        }
    }
    /* hit testing: a slot, the active slot's strips, nothing elsewhere, nothing outside the field */
    {
        AtRect r1 = at_code_slot_rect(f, 1);
        CHECK(at_code_hit(f, 1, r1.x + 5.0f, r1.y + 5.0f, &arg) == 1 && arg == 1);
        CHECK(at_code_hit(f, 1, r1.x + 5.0f, r1.y - 5.0f, &arg) == 2);
        CHECK(at_code_hit(f, 1, r1.x + 5.0f, r1.y + r1.h + 5.0f, &arg) == 3);
        CHECK(at_code_hit(f, 0, r1.x + 5.0f, r1.y - 5.0f, &arg) == 0);               /* a strip of a slot that is not active */
        CHECK(at_code_hit(f, 1, -1000.0f, -1000.0f, &arg) == 0);                     /* a pointer off the picture */
        CHECK(at_code_hit(f, 1, r1.x + r1.w + 4.0f, r1.y + 5.0f, &arg) == 0);       /* in the gap between slots */
    }
}
```

- [ ] **Step 2: Run to verify it fails.** `nt atlas-online-parts`. Expected: link errors for `at_code_slot_rect`, `at_code_hit`, `at_part_code`.
- [ ] **Step 3: Write the implementation.** Append to `pc/platform/gw_ui_online_parts.c`:

```c
/* ---- the room-code field ------------------------------------------------------------------------- */

AtRect at_code_slot_rect(AtRect f, int i)
{
    float gap = 12.0f, sw = (f.w - 3.0f * gap) / 4.0f, sh = f.h - 2.0f * AT_CODE_BAND;
    AtRect r;
    if (sw > 64.0f) sw = 64.0f;
    if (sw < 8.0f) sw = 8.0f;
    if (sh > 84.0f) sh = 84.0f;
    r.w = sw;
    r.h = sh;
    r.x = f.x + (f.w - (4.0f * sw + 3.0f * gap)) * 0.5f + (float) i * (sw + gap);
    r.y = f.y + (f.h - sh) * 0.5f;
    return r;
}

int at_code_hit(AtRect f, int active, float px, float py, int *arg)
{
    int i;
    for (i = 0; i < 4; i++) {
        AtRect r = at_code_slot_rect(f, i);
        if (px < r.x || px >= r.x + r.w) continue;
        if (py >= r.y && py < r.y + r.h) { *arg = i; return 1; }
        if (i == active && py >= r.y - AT_CODE_BAND && py < r.y) return 2;
        if (i == active && py >= r.y + r.h && py < r.y + r.h + AT_CODE_BAND) return 3;
    }
    return 0;
}

/* one registration bracket: two 2 px strips meeting in the corner (x, y); sx and sy are +1 or -1, the way it points inward */
static void bracket(const AtSink *s, float x, float y, float sx, float sy, unsigned c)
{
    at_poly_rect(s, sx > 0.0f ? x : x - 10.0f, sy > 0.0f ? y : y - 2.0f, 10.0f, 2.0f, c);
    at_poly_rect(s, sx > 0.0f ? x : x - 2.0f, sy > 0.0f ? y : y - 10.0f, 2.0f, 10.0f, c);
}

static void chevron(const AtSink *s, float cx, float y, int up, unsigned c)
{
    float x[4] = { cx - 7.0f, cx + 7.0f, cx, cx };
    float ya = up ? y + 8.0f : y, yb = up ? y : y + 8.0f;
    float yy[4];
    yy[0] = ya; yy[1] = ya; yy[2] = yb; yy[3] = yb;
    s->poly(s->user, x, yy, c);
}

void at_part_code(const AtSink *s, const AtTextOps *o, AtRect f, const AtCodeView *v)
{
    int i;
    for (i = 0; i < 4; i++) {
        AtRect r = at_code_slot_rect(f, i), pr;
        int active = i == v->slot;
        float y = active ? r.y - 2.0f : r.y, cx = r.x + r.w * 0.5f;
        unsigned face = active ? AT_C_LIFT : AT_C_PLATE2;
        unsigned edge = active ? AT_C_EMBER : v->invalid ? AT_C_ROSE : AT_C_EDGE2;
        pr.x = r.x; pr.y = y; pr.w = r.w; pr.h = r.h;
        at_plate(s, pr, face, edge, 3.0f, (float) AT_PX_CH_XS);
        if (v->c[i] != '\0') {
            char one[2];
            one[0] = (char) toupper((unsigned char) v->c[i]);
            one[1] = '\0';
            at_text(s, o, AT_R_DISPLAY, one, cx, y + r.h * 0.5f + 22.0f, AT_C_IVORY, AT_ALIGN_CENTER, r.w - 8.0f);
        } else {
            at_text(s, o, AT_R_NUM16, "-", cx, y + r.h * 0.5f + 6.0f, AT_C_DIM, AT_ALIGN_CENTER, 0.0f);
        }
        if (active) {
            bracket(s, r.x - 3.0f, y - 3.0f, 1.0f, 1.0f, AT_C_EMBER);
            bracket(s, r.x + r.w + 3.0f, y - 3.0f, -1.0f, 1.0f, AT_C_EMBER);
            bracket(s, r.x - 3.0f, y + r.h + 3.0f, 1.0f, -1.0f, AT_C_EMBER);
            bracket(s, r.x + r.w + 3.0f, y + r.h + 3.0f, -1.0f, -1.0f, AT_C_EMBER);
            chevron(s, cx, r.y - 14.0f, 1, AT_C_MUTED);
            chevron(s, cx, r.y + r.h + 6.0f, 0, AT_C_MUTED);
        }
    }
}
```

- [ ] **Step 4: Run.** `nt atlas-online-parts`. Expected: `0 failed`. Two things to look at if a check fails: (a) `lint_plate_corners` on a slot whose plate was lifted by 2 (it must be probed in the no-active case, as written); (b) the narrow-field glyph check, which holds only because `at_text` passes `r.w - 8` to the fit rule: if a slot is narrower than 28 px the role steps down to `a_title`, then `a_hero` is never reached because the fit rule only steps down.
- [ ] **Step 5: Commit.** Game repo: `pc/platform/gw_ui_online_parts.c`, `pc/tests/atlas_online_parts_test.c`, message `atlas online: the room-code field part (slots, brackets, chevrons, hit test)`.

---

### Task 4: The room view, the stage-grid model and the screen builder

**This is where "drawing only" is easiest to break.** The legacy lobby moves its cursor with `fl_step_row`, which compares the **rectangles** `fl_grid_layout` computes in the retired layout's pixel space (`flg.r[i]`). If Atlas drew its tiles somewhere else, the cursor would move through a grid the player cannot see. So the grid becomes one pure function, `at_room_grid`, that gives every stage a `(col, row, page)` and every group a header, and **both** the drawing and the legacy cursor code read it: the adapter fills `flg` from it (Task 7). The cursor algorithms (`fl_step_row`, `fl_step_open`, `fl_step_page`) are not edited; only their input geometry is. Nothing netplay-visible changes: `fl.cur` is a local cursor and `Netplay_LobbyStageAct(index)` still gets an index.

**Files:**
- Create (game repo): `pc/platform/gw_ui_room.h`, `pc/platform/gw_ui_room.c`, `pc/tests/atlas_room_fixture.h`, `pc/tests/atlas_room_test.c`
- Modify (game repo): `pc/platform/gw_ui_screen.h` (`AT_PRIMARY_ROOM`, `AtView.room`)
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-room`)

**Interfaces:**
Consumes: `AtScreen`, `AtView`, `AtCodeView`, step 1 limits (`AT_MAX_KEYS`, `AT_STR`).
Produces: `AtRoomView` (plain data, the only thing the game side fills), `AtGrid` and `at_room_grid`, `at_room_pick_cols`, `at_room_cursor_fix`, `at_room_fill` (the screen record and the dynamic view, including the toast as a corner note, from a room view). The enums `AT_ROOM_*`, `AT_PH_*`, `AT_STAGE_*` are Atlas's own numbers; the adapter never shares them: it sends phases, stage states and settings **by name** through the shims (Task 7), so there is no numeric coupling to keep in step.

- [ ] **Step 1: Write the failing tests.** Create `pc/tests/atlas_room_fixture.h` (shared by Tasks 4, 5 and 6):

```c
/* A deterministic space of room views: every screen kind, every lobby phase, host and guest, link states, rules, list sizes. */
#ifndef ATLAS_ROOM_FIXTURE_H
#define ATLAS_ROOM_FIXTURE_H
#include <stdio.h>
#include <string.h>
#include "../platform/gw_ui_room.h"
#include "../platform/gw_ui_render.h"

static const char *const FX_STAGES[] = { "Battlefield", "Final Destination", "Yoshi's Story", "Dream Land", "Fountain of Dreams",
    "Pokemon Stadium", "Princess Peach's Castle", "Stage 147", "Kongo Jungle", "Great Bay", "Brinstar Depths", "Mushroom Kingdom II" };
static const char *const FX_NAMES[] = { "GD", "Opponent", "WWWWWWWWWWWWWWW", "a b c d e f g" };   /* 15 wide characters and spaces */
static const int FX_LISTS[] = { 0, 5, 6, 12, 32 };
static const int FX_PINGS[] = { -1, 20, 95, 260 };
#define FX_COUNT (3 * 9 * 2 * 2 * 4 * 5 * 2)   /* kinds x phases x host x reconnecting x pings x lists x rules */

static void fx_view(int idx, AtRoomView *v)
{
    int kind = 1 + idx % 3, phase = (idx / 3) % 9, host = (idx / 27) % 2, recon = (idx / 54) % 2, ping = (idx / 108) % 4,
        list = (idx / 432) % 5, rules = (idx / 2160) % 2, i;
    char code[8];
    memset(v, 0, sizeof *v);
    v->kind = kind; v->phase = phase; v->host = host; v->me = host ? 0 : 1; v->reconnecting = recon;
    v->ping_ms = FX_PINGS[ping]; v->rules_known = rules ? 1 : host;
    v->turbo = rules; v->envoy = rules; v->stage_all = rules; v->stocks = 4; v->minutes = 8; v->delay = 2;
    snprintf(code, sizeof code, "%s", "ABCD"); memcpy(v->code, code, 5);
    for (i = 0; i < 2; i++) {
        snprintf(v->pl[i].name, sizeof v->pl[i].name, "%s", FX_NAMES[(idx + i) % 4]);
        snprintf(v->pl[i].fighter, sizeof v->pl[i].fighter, "%s", i ? "Captain Falcon" : "Fox");
        v->pl[i].present = i == 0 || kind != AT_ROOM_WAIT || (idx & 1);
        v->pl[i].locked = phase > AT_PH_CHAR_BLIND; v->pl[i].ready = phase == AT_PH_GO || (phase == AT_PH_READY && i == 0);
    }
    v->game = 2; v->pl[0].score = 1; v->pl[1].score = 0; v->turn = 0; v->left = 2;
    v->countdown_s = phase == AT_PH_READY ? 3 : 0; v->coin_on = phase == AT_PH_STRIKE;
    v->my_stage_turn = (phase == AT_PH_STRIKE || phase == AT_PH_BAN || phase == AT_PH_PICK) && v->me == v->turn;
    v->can_pick = phase == AT_PH_CHAR_BLIND || phase == AT_PH_CHAR_WINNER || phase == AT_PH_CHAR_LOSER;
    v->can_ready = phase == AT_PH_READY; v->ready_mine = v->pl[v->me].ready;
    snprintf(v->phase_title, sizeof v->phase_title, "%s", "STAGE STRIKING");
    snprintf(v->instruction, sizeof v->instruction, "%s", "Strike 2 stages: move, then press A. It stays hidden till both lock.");
    snprintf(v->status, sizeof v->status, "%s", "Connected to the matchmaking server, waiting for the other player to join your room.");
    v->code_in.c[0] = 'A'; v->code_in.c[1] = 'B'; v->code_in.slot = idx % 4; v->code_in.invalid = idx % 5 == 0;
    snprintf(v->code_msg, sizeof v->code_msg, "%s", v->code_in.invalid ? "No room with that code." : "");
    v->code_msg_bad = v->code_in.invalid;
    {
        int group[AT_ROOM_STAGES];
        v->n_stages = FX_LISTS[list];
        for (i = 0; i < v->n_stages; i++) {
            snprintf(v->st[i].name, sizeof v->st[i].name, "%s", FX_STAGES[i % 12]);
            group[i] = i >= 5 ? 1 : 0; v->st[i].starter = group[i] == 0; v->st[i].open = i % 4 != 3;
            v->st[i].state = i % 4 == 3 ? AT_STAGE_BANNED : AT_STAGE_FREE;
        }
        at_room_grid(group, v->n_stages, at_room_pick_cols(v->n_stages, v->n_stages > 5, idx & 4), 3, &v->grid);
    }
    v->cursor = v->n_stages > 1 ? 1 : 0;
}
#endif
```

Create `pc/tests/atlas_room_test.c`:

```c
#include "atlas_lint.h"
#include "atlas_room_fixture.h"

static void grid(void)
{
    AtGrid g;
    int i, n, cols, group[AT_ROOM_STAGES];
    /* five ungrouped stages: three columns, two rows, one page, no headers */
    memset(group, 0, sizeof group);
    at_room_grid(group, 5, 3, 3, &g);
    CHECK(g.pages == 1 && g.nhead == 0 && g.n == 5);
    CHECK(g.cell[0].col == 0 && g.cell[0].row == 0 && g.cell[2].col == 2 && g.cell[3].col == 0 && g.cell[3].row == 1);
    /* four starters and two counterpicks: a header over each group, the counterpicks start a new row */
    for (i = 0; i < 6; i++) group[i] = i >= 4;
    at_room_grid(group, 6, 4, 3, &g);
    CHECK(g.nhead == 2 && g.head[0].group == 0 && g.head[0].count == 4 && g.head[1].group == 1 && g.head[1].row == 1 && g.head[1].count == 2);
    CHECK(g.cell[4].row == 1 && g.cell[4].col == 0 && g.cell[5].col == 1);
    /* all stages: 5 starters, 27 counterpicks, six columns, three rows a page: the group's header comes back on page 2 */
    for (i = 0; i < 32; i++) group[i] = i >= 5;
    at_room_grid(group, 32, 6, 3, &g);
    CHECK(g.pages == 2);
    {
        int heads_p1 = 0;
        for (i = 0; i < g.nhead; i++) if (g.head[i].page == 1 && g.head[i].group == 1 && g.head[i].row == 0) heads_p1++;
        CHECK(heads_p1 == 1);
    }
    /* invariants over every list size and column count: unique cells, inside the grid, pages in order, every head valid */
    for (n = 0; n <= AT_ROOM_STAGES; n++) for (cols = 1; cols <= 8; cols++) {
        int split, ok = 1, lastp = 0;
        for (split = 0; split <= n; split += (n > 6 ? 5 : 1)) {
            for (i = 0; i < n; i++) group[i] = i >= split;
            at_room_grid(group, n, cols, 3, &g);
            ok = g.n == n;
            for (i = 0; i < n && ok; i++) {
                int j;
                if (g.cell[i].col < 0 || g.cell[i].col >= cols || g.cell[i].row < 0 || g.cell[i].row >= 3 || g.cell[i].page < lastp) ok = 0;
                lastp = g.cell[i].page;
                for (j = 0; j < i; j++)
                    if (g.cell[j].col == g.cell[i].col && g.cell[j].row == g.cell[i].row && g.cell[j].page == g.cell[i].page) ok = 0;
            }
            for (i = 0; i < g.nhead; i++) if (g.head[i].page >= g.pages || g.head[i].row >= 3) ok = 0;
            lastp = 0;
            CHECK(ok && (n == 0 ? g.pages == 1 : g.pages >= 1));
        }
    }
    /* the column count: three for a short ungrouped list, four compact or six wide for the rest */
    CHECK(at_room_pick_cols(5, 0, 0) == 3 && at_room_pick_cols(6, 0, 1) == 3 && at_room_pick_cols(6, 1, 0) == 4 && at_room_pick_cols(32, 1, 1) == 6);
}

static void cursor(void)
{
    AtRoomView v;
    int i;
    memset(&v, 0, sizeof v);
    CHECK(at_room_cursor_fix(&v) == -1);                       /* no list yet (a guest waits for it): no cursor */
    v.n_stages = 3; v.cursor = 7;
    for (i = 0; i < 3; i++) v.st[i].open = 1;
    CHECK(at_room_cursor_fix(&v) == 0);                        /* past the end: the first open stage */
    v.cursor = -4; CHECK(at_room_cursor_fix(&v) == 0);
    v.st[0].open = 0; v.cursor = 9; CHECK(at_room_cursor_fix(&v) == 1);
    v.cursor = 2; CHECK(at_room_cursor_fix(&v) == 2);          /* a valid cursor is left alone, open or not */
    v.st[0].open = v.st[1].open = v.st[2].open = 0; v.cursor = 9; CHECK(at_room_cursor_fix(&v) == -1);   /* nothing open */
    v.n_stages = 0; v.cursor = 0; CHECK(at_room_cursor_fix(&v) == -1);   /* the list shrank under the cursor */
}

static void fill(void)
{
    static AtScreen sc;
    static AtView vw;
    static AtRoomView rv;
    int idx;
    for (idx = 0; idx < FX_COUNT; idx += 7) {                     /* every seventh view of the space: all kinds, phases, sides */
        int i, ok;
        fx_view(idx, &rv);
        memset(&vw, 0, sizeof vw);
        ok = at_room_fill(&rv, &sc, &vw, 1000.0);
        CHECK(ok);
        CHECK(sc.primary == AT_PRIMARY_ROOM && vw.room == &rv);
        CHECK(sc.n_keys >= 1 && sc.n_keys <= AT_MAX_KEYS && sc.title[0] != '\0' && sc.chapter == 3);
        for (i = 0; i < sc.n_keys; i++) CHECK(vw.key_shown[i] && vw.key_label[i][0] != '\0');
        CHECK(sc.preset == (rv.kind == AT_ROOM_LOBBY ? AT_PRESET_NORMAL : AT_PRESET_NONE));
        if (rv.kind == AT_ROOM_LOBBY) CHECK(vw.ex.has && vw.ex.what[0] != '\0' && strcmp(vw.ex.what, rv.instruction) == 0);
    }
    /* the keys name what A does now, and B asks twice before leaving */
    fx_view(0, &rv); rv.kind = AT_ROOM_LOBBY; rv.phase = AT_PH_READY; rv.can_ready = 1; rv.can_pick = 0; rv.leave_armed = 0; rv.countdown_s = 0;
    at_room_fill(&rv, &sc, &vw, 1000.0);
    CHECK(strcmp(vw.key_label[0], "Ready") == 0);
    { int b; for (b = 0; b < sc.n_keys; b++) if (sc.keys[b].btn == 'B') CHECK(strcmp(vw.key_label[b], "Leave") == 0); }
    rv.leave_armed = 1; at_room_fill(&rv, &sc, &vw, 1000.0);
    { int b; for (b = 0; b < sc.n_keys; b++) if (sc.keys[b].btn == 'B') CHECK(strcmp(vw.key_label[b], "Leave now") == 0); }
    rv.leave_armed = 0; rv.countdown_s = 3; rv.ready_mine = 1; at_room_fill(&rv, &sc, &vw, 1000.0);
    { int b; for (b = 0; b < sc.n_keys; b++) if (sc.keys[b].btn == 'B') CHECK(strcmp(vw.key_label[b], "Cancel") == 0); }   /* B in the count takes the ready back */
    /* a toast is a corner note while it is set, and gone when it is not */
    rv.kind = AT_ROOM_LOBBY; snprintf(rv.toast, sizeof rv.toast, "Press B again to leave the room."); rv.toast_bad = 1;
    at_room_fill(&rv, &sc, &vw, 1000.0);
    CHECK(strcmp(vw.note.text, rv.toast) == 0 && vw.note.kind == AT_NOTE_ERR && vw.note.until_ms > 1000.0);
    rv.toast[0] = '\0'; at_room_fill(&rv, &sc, &vw, 1000.0); CHECK(vw.note.text[0] == '\0');
    /* an unknown kind fills nothing and says so */
    rv.kind = 0; CHECK(at_room_fill(&rv, &sc, &vw, 1000.0) == 0);
}

int main(void)
{
    grid();
    cursor();
    fill();
    ATLAS_DONE("atlas room");
}
```

Register in `tools/port/native_test.sh` (append `, atlas-room` to the die message):

```bash
atlas-room)
    sources=(pc/tests/atlas_room_test.c pc/platform/gw_ui_room.c pc/platform/gw_ui_online_parts.c pc/platform/gw_ui_render.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c) ;;
```

- [ ] **Step 2: Run to verify it fails.** `nt atlas-room`. Expected: `fatal error: '../platform/gw_ui_room.h' file not found`.
- [ ] **Step 3: Extend the screen header.** In `pc/platform/gw_ui_screen.h`, change the primary enum and add the borrowed pointer:

```c
enum { AT_PRIMARY_LIST = 1, AT_PRIMARY_GRID = 2, AT_PRIMARY_ROOM = 3 };   /* ROOM: native only, drawn by gw_ui_room.c; Lua cannot ask for it */
```

and, inside `AtView` (after `port_rgba`), `const struct AtRoomView *room;   /* borrowed: set by the adapter every frame, NULL when the screen is released */`. Add `struct AtRoomView;` above the typedef. `at_view_init` must set it to NULL (it memsets; check). `at_screen_from_val` already refuses a primary kind it does not know: add the check `{ kind = "room" }` raises (a test in `atlas_screen_test.c`, the existing one for unknown kinds, gets one more line).
- [ ] **Step 4: Write the room header and the model.** Create `pc/platform/gw_ui_room.h`:

```c
/* gw_ui_room.h - the online room screens (code entry, waiting room, lobby): a plain-data view, the stage-grid model,
 * the screen builder, the composite render and the input mapping. Pure C. It never includes a netplay header and never
 * calls a netplay function: the game-side adapter (gmfrontend_atlas_online.inc) fills AtRoomView from the readbacks the
 * legacy screens already used and applies the AtRoomIntents it gets back. */
#ifndef GW_UI_ROOM_H
#define GW_UI_ROOM_H
#include "gw_ui_input.h"
#include "gw_ui_online_parts.h"
#include "gw_ui_screen.h"
#ifdef __cplusplus
extern "C" {
#endif

#define AT_ROOM_STAGES 32      /* the lobby's stage list cap (LB_MAX_UI_STAGES in gmfrontend.c; the adapter asserts they match) */
#define AT_ROOM_NAME 40        /* the legacy buffers: stage names 40, fighter names 24, player names 18 */
#define AT_ROOM_TEXT 96
enum { AT_ROOM_CODE = 1, AT_ROOM_WAIT = 2, AT_ROOM_LOBBY = 3 };
enum { AT_PH_OFF, AT_PH_CHAR_BLIND, AT_PH_STRIKE, AT_PH_BAN, AT_PH_PICK, AT_PH_CHAR_WINNER, AT_PH_CHAR_LOSER, AT_PH_READY, AT_PH_GO };
enum { AT_STAGE_FREE, AT_STAGE_STRUCK_P1, AT_STAGE_STRUCK_P2, AT_STAGE_BANNED, AT_STAGE_PICKED };

/* ---- the stage grid: one model for drawing AND for the legacy cursor code ---- */
typedef struct { int col, row, page; } AtGridCell;
typedef struct { int page, row, group, count; } AtGridHead;     /* a group's label strip sits above `row` of `page` */
typedef struct { int cols, rows, pages, n, nhead; AtGridCell cell[AT_ROOM_STAGES]; AtGridHead head[16]; } AtGrid;
/* group[i] is 0 for a starter, 1 for a counterpick (starters first, as the netplay list is). Rows of `cols`; a group starts a
 * new row; `rows` rows to a page; when the list is grouped each group's header is drawn again at the top of a page it
 * continues on. */
void at_room_grid(const int *group, int n, int cols, int rows, AtGrid *g);
int at_room_pick_cols(int n, int grouped, int wide);            /* 3 for a short ungrouped list; else 4 compact, 6 wide */

typedef struct { char name[AT_ROOM_NAME]; int state, starter, open; } AtRoomStage;
typedef struct { char name[AT_ROOM_NAME], fighter[AT_ROOM_NAME]; int present, locked, ready, score; } AtRoomPlayer;

typedef struct AtRoomView {
    int kind;                                         /* AT_ROOM_* */
    /* the room */
    char code[8];
    int host, random_search, random_secs, found;      /* found: the opponent is in (the short beat before the lobby opens) */
    int rules_known, turbo, envoy, stage_all, stocks, minutes, delay;
    char status[AT_ROOM_TEXT];
    int ping_ms, link_bars;                           /* ping -1: no link; link_bars is the meter's memory, kept by the host shim */
    int copied;                                       /* the code was just copied */
    AtRoomPlayer pl[2]; int me;                       /* 0 host, 1 guest */
    /* code entry */
    AtCodeView code_in; char code_msg[AT_ROOM_TEXT]; int code_msg_bad;
    /* lobby */
    int phase, game, turn, left, first, countdown_s, coin_on, reward_open, reward_left_s;
    int reconnecting, leave_armed, my_stage_turn, can_pick, can_ready, ready_mine;
    char phase_title[24], instruction[AT_ROOM_TEXT];
    int n_stages, cursor; AtRoomStage st[AT_ROOM_STAGES]; AtGrid grid;
    char toast[AT_ROOM_TEXT]; int toast_bad;
} AtRoomView;

/* The cursor to show: the view's own when it is a real stage, else the first open stage, else -1 (no list, nothing open). */
int at_room_cursor_fix(const AtRoomView *v);
/* Fill the screen record and the dynamic part of the view (keys, counter, explainer, the toast as a corner note) from a room view. 1 ok; 0 for an unknown kind. */
int at_room_fill(const AtRoomView *rv, AtScreen *sc, AtView *vw, double now_ms);

#ifdef __cplusplus
}
#endif
#endif
```

(The fixture uses `v->rules_known`; it is declared above. Intents, the composite render and hits are added to this header by Tasks 5 and 6.)

Create `pc/platform/gw_ui_room.c`:

```c
#include "gw_ui_room.h"
#include "gw_ui_tokens.h"
#include <stdio.h>
#include <string.h>

/* ---- the grid ---- */
void at_room_grid(const int *group, int n, int cols, int rows, AtGrid *g)
{
    int i, page = 0, row = 0, col = 0, grp = -1, has0 = 0, has1 = 0, grouped, need_head = 0, c0 = 0, c1 = 0;
    memset(g, 0, sizeof *g);
    if (cols < 1) cols = 1;
    if (cols > 8) cols = 8;
    if (rows < 1) rows = 1;
    if (n > AT_ROOM_STAGES) n = AT_ROOM_STAGES;
    if (n < 0) n = 0;
    for (i = 0; i < n; i++) { if (group[i]) { has1 = 1; c1++; } else { has0 = 1; c0++; } }
    grouped = has0 && has1;
    g->cols = cols; g->rows = rows; g->n = n; g->pages = 1;
    for (i = 0; i < n; i++) {
        int gi = group[i] ? 1 : 0, new_group = grouped && gi != grp, new_row = i > 0 && (new_group || col >= cols);
        if (new_row) { row++; col = 0; }
        if (row >= rows) { page++; row = 0; col = 0; need_head = grouped; }
        if ((new_group || need_head) && g->nhead < (int) (sizeof g->head / sizeof g->head[0])) {
            AtGridHead *h = &g->head[g->nhead++];
            h->page = page; h->row = row; h->group = gi; h->count = gi ? c1 : c0;
        }
        need_head = 0;
        g->cell[i].col = col; g->cell[i].row = row; g->cell[i].page = page;
        col++;
        grp = gi;
    }
    g->pages = page + 1;
}

int at_room_pick_cols(int n, int grouped, int wide)
{
    if (n <= 6 && !grouped) return 3;
    return wide ? 6 : 4;
}

int at_room_cursor_fix(const AtRoomView *v)
{
    int i;
    if (v->n_stages <= 0) return -1;
    if (v->cursor >= 0 && v->cursor < v->n_stages) return v->cursor;
    for (i = 0; i < v->n_stages; i++) if (v->st[i].open) return i;
    return -1;
}

/* ---- the screen record ---- */
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

static const char *a_label(const AtRoomView *v)
{
    if (v->can_pick) return "Pick";
    if (v->my_stage_turn) return v->phase == AT_PH_BAN ? "Ban" : v->phase == AT_PH_PICK ? "Pick stage" : "Strike";
    if (v->can_ready) return v->ready_mine ? NULL : "Ready";    /* A only readies: START takes it back (the legacy rule) */
    return NULL;
}

int at_room_fill(const AtRoomView *rv, AtScreen *sc, AtView *vw, double now_ms)
{
    char title[AT_STR];
    const char *a;
    memset(sc, 0, sizeof *sc);
    memset(vw->key_label, 0, sizeof vw->key_label);
    memset(vw->key_shown, 0, sizeof vw->key_shown);
    vw->counter[0] = '\0';
    memset(&vw->ex, 0, sizeof vw->ex);
    vw->room = rv;
    if (rv->toast[0]) {                                                /* the game side owns a toast's duration: it is drawn while it is set */
        snprintf(vw->note.text, sizeof vw->note.text, "%s", rv->toast);
        vw->note.kind = rv->toast_bad ? AT_NOTE_ERR : AT_NOTE_INFO;
        vw->note.from_ms = now_ms;
        vw->note.until_ms = now_ms + 1000.0;
    } else {
        vw->note.text[0] = '\0';
    }
    sc->chapter = 3;                                                   /* III Online */
    sc->primary = AT_PRIMARY_ROOM;
    sc->preset = AT_PRESET_NONE;
    sc->input_feed = 1;                                                /* the game side owns the pad (the legacy bits); Atlas reads none */
    snprintf(sc->parent[0], sizeof sc->parent[0], "%s", "ONLINE");
    sc->n_parents = 1;
    switch (rv->kind) {
    case AT_ROOM_CODE:
        snprintf(sc->id, sizeof sc->id, "%s", "online.code");
        snprintf(sc->title, sizeof sc->title, "%s", "JOIN ROOM");
        put_key(sc, vw, 'A', "Join");
        put_key(sc, vw, 'Y', "Paste");
        put_key(sc, vw, 'B', "Back");
        return 1;
    case AT_ROOM_WAIT:
        snprintf(sc->id, sizeof sc->id, "%s", "online.wait");
        snprintf(title, sizeof title, "%s", rv->random_search ? "FINDING OPPONENT" : rv->host ? "WAITING ROOM" : "JOINING ROOM");
        snprintf(sc->title, sizeof sc->title, "%s", title);
        if (rv->host && !rv->random_search) put_key(sc, vw, 'X', "Copy code");
        put_key(sc, vw, 'B', rv->random_search ? "Stop" : rv->host ? "Close room" : "Cancel");
        return 1;
    case AT_ROOM_LOBBY:
        snprintf(sc->id, sizeof sc->id, "%s", "online.lobby");
        snprintf(sc->title, sizeof sc->title, "%s", rv->phase_title[0] ? rv->phase_title : "LOBBY");
        sc->preset = AT_PRESET_NORMAL;
        a = a_label(rv);
        if (a != NULL) put_key(sc, vw, 'A', a);
        if (rv->can_ready) put_key(sc, vw, 'S', rv->ready_mine ? "Unready" : "Ready");
        put_key(sc, vw, 'B', rv->countdown_s > 0 && rv->ready_mine ? "Cancel" : rv->leave_armed ? "Leave now" : "Leave");
        put_key(sc, vw, 'X', "Copy code");
        if (rv->grid.pages > 1 && rv->my_stage_turn) { put_key(sc, vw, 'L', "Page"); put_key(sc, vw, 'R', "Page"); }
        snprintf(vw->counter, sizeof vw->counter, "Game %d   %d - %d", rv->game, rv->pl[0].score, rv->pl[1].score);
        vw->ex.has = 1;
        snprintf(vw->ex.kicker, sizeof vw->ex.kicker, "%s", rv->phase_title);
        snprintf(vw->ex.title, sizeof vw->ex.title, "ROOM %s", rv->code);
        snprintf(vw->ex.what, sizeof vw->ex.what, "%s", rv->instruction);
        snprintf(vw->ex.from_text, sizeof vw->ex.from_text, "%s", rv->turbo && rv->envoy ? "Host sets: Turbo, Envoy" : rv->turbo ? "Host sets: Turbo" : rv->envoy ? "Host sets: Envoy" : "Host sets: standard rules");
        return 1;
    default:
        return 0;
    }
}
```

- [ ] **Step 5: Run.** `nt atlas-room`. Expected: `atlas room: 0 failed` (the count is large, about 2,000 checks, because `fill` walks the space). `FX_COUNT` is 3 x 9 x 2 x 2 x 4 x 5 x 2 = 4,320 views; the loop takes every seventh. If `at_room_grid`'s invariant check fails for some `(n, cols, split)`, print the three numbers and fix the algorithm, not the check.
- [ ] **Step 6: Re-run the neighbours** (the header change touches step 1 code): `for t in atlas-screen atlas-render atlas-binding; do nt $t | tail -1; done`. Expected: `0 failed` each.
- [ ] **Step 7: Commit.** Game repo: `pc/platform/gw_ui_room.h/.c`, `pc/platform/gw_ui_screen.h`, `pc/tests/atlas_room_fixture.h`, `pc/tests/atlas_room_test.c`, message `atlas online: the room view, the stage-grid model and the screen builder`. Workspace repo: `tools/port/native_test.sh`, message `tools: atlas-room native test`.

---

### Task 5: The composite render: code entry, waiting room, lobby

**Gate:** `python tools/port/atlas_gate.py --step 6` exits 0 (this task needs N5, the port card part). The two uses of it are one wrapper, `room_card`, marked `RECONCILE`.

The three screens are one primary each, drawn in the primary rectangle the step 1 layout gives (`AtLayout.primary`), through the same `AtSink`. The chrome (ground, trail, chapter, key hints, the lobby's explainer, notes, dialogs, the open fade) stays `at_render_ex`'s; only the primary is new. Layout, per screen (all values in logical px at 640x480, scaled by the layout's width; inner padding 12):

| Screen | Primary | Preset |
|---|---|---|
| JOIN ROOM | label `ROOM CODE` (cap12), the code field 330 x 120 centred (Task 3), the instruction line (body14, muted), one message line: a rose `FAILED` tag plus text for a bad code, plain muted text for a notice | none |
| WAITING ROOM (host, guest, or Random) | left 58 %: the code plate 110 high (label, the code in `display`, a sub line, a COPY button on the host), two player cards 56 high, the connection strip 40 high (status text, the link meter), a LEAVE button 44 high at the bottom. Right: ROOM RULES (read-only rows, `HOST SETS` at the right of the heading), or "Set by the host" for a guest who has not seen them | none |
| LOBBY | two player cards side by side 56 high, a turn or coin line 24 high, the stage tiles (group headers 18 high, rows of `at_room_grid`), an action plate 40 high at the bottom while there is an action (READY, PICK A FIGHTER), the countdown plate over the tiles | normal (the standard explainer: kicker, `ROOM ABCD`, the instruction as WHAT, `Host sets: ...` as FROM) |

Rules this composite must obey, each pinned in Step 1 below: every text inside its plate at 640, 853 and 1140 wide, no two texts overlapping, 12 px floor; chamfers top-left and bottom-right only; focus (a stage tile) has three cues and exists only on the player's own stage turn and never while reconnecting; ember appears only for focus and the one action (the READY plate, YOUR TURN); every state has a word (`STRUCK P1`, `BANNED`, `PICKED`, `NOT YET`, `RECONNECTING`, `READY`); hit rectangles stay inside the primary and fit `AT_MAX_HITS`; with no view the chrome still draws and nothing else does.

**Files:**
- Modify (game repo): `pc/platform/gw_ui_room.h` (the render, hit and intent declarations), `pc/platform/gw_ui_room.c`, `pc/platform/gw_ui_input.h` (`AT_HIT_ROOM`), `pc/platform/gw_ui_render.c` (one branch), `pc/tests/atlas_room_test.c`

**Interfaces:**
Consumes: `AtLayout`, `at_part_cell`, `at_part_tag`, `at_part_row`, `at_part_hint`, `at_part_link`, `at_part_code`, `at_plate`, `at_text`, and step 4's port card (`RECONCILE`).
Produces: `int at_room_render(const AtRoomView *, const AtLayout *, const AtTextOps *, const AtSink *, AtHits *, double now_ms)` (returns how many hit rectangles did not fit) and the hit codes `AT_RH_*` carried in `AtHit` with kind `AT_HIT_ROOM`.

- [ ] **Step 1: Add the failing tests** to `pc/tests/atlas_room_test.c` (before `main`; call `render();` from `main` after `fill();`):

```c
/* the primary of one view at one width, drawn straight into a fresh recording sink */
static AtHits RH;
static AtLayout draw_room(const AtRoomView *rv, float w)
{
    AtLayout L;
    AtSink s = rec_sink();
    at_layout(w, rv->kind == AT_ROOM_LOBBY ? AT_PRESET_NORMAL : AT_PRESET_NONE, &L);
    memset(&RH, 0, sizeof RH);
    CHECK(at_room_render(rv, &L, &FAKE, &s, &RH, 0.0) == 0);                 /* no hit rectangle dropped */
    return L;
}

static void render(void)
{
    static AtRoomView rv;
    static const float widths[3] = { 640.0f, 853.0f, 1140.0f };
    int idx, k, i;
    for (idx = 0; idx < FX_COUNT; idx += 5) for (k = 0; k < 3; k++) {
        AtLayout L;
        fx_view(idx, &rv);
        L = draw_room(&rv, widths[k]);
        CHECK(lint_text_inside(L.primary, 0) == 0);                          /* every text inside the primary, 12 px or more */
        CHECK(lint_text_overlaps() == 0);                                    /* and none on top of another */
        CHECK(RH.n <= AT_MAX_HITS);
        for (i = 0; i < RH.n; i++) {
            CHECK(RH.h[i].kind == AT_HIT_ROOM);
            CHECK(RH.h[i].r.x >= L.primary.x - 0.5f && RH.h[i].r.x + RH.h[i].r.w <= L.primary.x + L.primary.w + 0.5f);
            CHECK(RH.h[i].r.y >= L.primary.y - 8.0f && RH.h[i].r.y + RH.h[i].r.h <= L.primary.y + L.primary.h + 0.5f);   /* 8: a code strip above its slot */
        }
    }

    /* the lobby, my stage turn: the focused tile has three cues, the others none; the chamfer rule holds on a resting tile */
    fx_view(0, &rv); rv.kind = AT_ROOM_LOBBY; rv.phase = AT_PH_STRIKE; rv.me = 1; rv.host = 0; rv.turn = 1; rv.my_stage_turn = 1;
    rv.n_stages = 6; rv.cursor = 2; rv.reconnecting = 0;
    { int g[AT_ROOM_STAGES], j; for (j = 0; j < 6; j++) { g[j] = 0; rv.st[j].open = 1; rv.st[j].state = AT_STAGE_FREE; rv.st[j].starter = 1; }
      at_room_grid(g, 6, 3, 3, &rv.grid); }
    draw_room(&rv, 640.0f);
    {
        int found = 0, stage_hits = 0;
        for (i = 0; i < RH.n; i++) if (RH.h[i].a == AT_RH_STAGE) {
            stage_hits++;
            if (RH.h[i].b == 2) { AtRect r = RH.h[i].r; found = 1; CHECK(lint_focus_cell(r, AT_C_P2) == 0); }   /* the guest's colour (me == 1) */
        }
        CHECK(found && stage_hits == 6);
        for (i = 0; i < RH.n; i++) if (RH.h[i].a == AT_RH_STAGE && RH.h[i].b != 2) CHECK(lint_plate_corners(RH.h[i].r, 3.0f) == 0);
    }
    /* not my turn, or reconnecting: no focus anywhere, and no ember (the action plate is only in the ready phase) */
    rv.my_stage_turn = 0; draw_room(&rv, 640.0f); CHECK(count_color(AT_C_EMBER) == 0);
    rv.my_stage_turn = 1; rv.reconnecting = 1; draw_room(&rv, 640.0f); CHECK(count_color(AT_C_EMBER) == 0 && find_text("RECONNECTING") != NULL);
    rv.reconnecting = 0;
    /* states have words: struck, banned, picked, not yet */
    rv.st[0].state = AT_STAGE_STRUCK_P1; rv.st[1].state = AT_STAGE_BANNED; rv.st[3].state = AT_STAGE_PICKED; rv.st[4].open = 0;
    draw_room(&rv, 640.0f);
    CHECK(find_text("P1 STRUCK") && find_text("BANNED") && find_text("PICKED") && find_text("NOT YET"));
    rv.phase = AT_PH_READY; draw_room(&rv, 640.0f); CHECK(find_text("OUT") != NULL);          /* decided: the free ones say OUT */
    rv.phase = AT_PH_STRIKE;
    /* the ready phase: the one ember plate says READY, and after readying it is jade and says so */
    rv.phase = AT_PH_READY; rv.my_stage_turn = 0; rv.can_ready = 1; rv.ready_mine = 0; rv.countdown_s = 0;
    draw_room(&rv, 640.0f); CHECK(count_color(AT_C_EMBER) >= 1 && find_text("READY") != NULL);
    rv.ready_mine = 1; draw_room(&rv, 640.0f); CHECK(count_color(AT_C_EMBER) == 0 && find_text("READY - WAITING") != NULL);
    /* the countdown plate */
    rv.countdown_s = 3; draw_room(&rv, 640.0f); CHECK(find_text("3") != NULL && find_text("B CANCEL") != NULL);

    /* the code screen: slots hit, strips for the active slot, an invalid code says FAILED as well as showing rose */
    fx_view(0, &rv); rv.kind = AT_ROOM_CODE; rv.code_in.slot = 1; rv.code_in.invalid = 1; snprintf(rv.code_msg, sizeof rv.code_msg, "No room with that code."); rv.code_msg_bad = 1;
    draw_room(&rv, 640.0f);
    { int slots = 0, up = 0, down = 0; for (i = 0; i < RH.n; i++) { slots += RH.h[i].a == AT_RH_CODE_SLOT; up += RH.h[i].a == AT_RH_CODE_UP; down += RH.h[i].a == AT_RH_CODE_DOWN; }
      CHECK(slots == 4 && up == 1 && down == 1); }
    CHECK(find_text("FAILED") != NULL && count_color(AT_C_ROSE) >= 3);

    /* the waiting room: the host can copy, the guest cannot; Random shows a clock, not a code */
    fx_view(0, &rv); rv.kind = AT_ROOM_WAIT; rv.host = 1; rv.random_search = 0; draw_room(&rv, 640.0f);
    { int copy = 0; for (i = 0; i < RH.n; i++) copy += RH.h[i].a == AT_RH_COPY; CHECK(copy == 1); }
    rv.host = 0; draw_room(&rv, 640.0f);
    { int copy = 0; for (i = 0; i < RH.n; i++) copy += RH.h[i].a == AT_RH_COPY; CHECK(copy == 0); }
    rv.random_search = 1; rv.random_secs = 72; draw_room(&rv, 640.0f); CHECK(find_text("1:12") != NULL && find_text("ABCD") == NULL);
    /* a guest who has not seen the rules is told so instead of seeing zeros */
    rv.random_search = 0; rv.rules_known = 0; draw_room(&rv, 640.0f); CHECK(find_text("Set by the host.") != NULL);

    /* the life of the view: no room, no drawing (the chrome is the renderer's); a view cleared after the screen is left */
    {
        AtSink s = rec_sink(); AtLayout L; AtHits h;
        at_layout(640.0f, AT_PRESET_NONE, &L); h.n = 0;
        CHECK(at_room_render(NULL, &L, &FAKE, &s, &h, 0.0) == 0 && REC.np == 0 && REC.nt == 0 && h.n == 0);
    }
    /* the whole screen through the real renderer: under the quad cap with 32 stages at the widest width, chrome and room both drawn */
    {
        static AtScreen sc; static AtView vw; static AtHits hits; AtRenderInfo info; AtSink s;
        fx_view(0, &rv); rv.kind = AT_ROOM_LOBBY; rv.phase = AT_PH_STRIKE; rv.n_stages = 32; rv.my_stage_turn = 1; rv.cursor = 7;
        { int g[AT_ROOM_STAGES], j; for (j = 0; j < 32; j++) { g[j] = j >= 5; rv.st[j].open = 1; } at_room_grid(g, 32, 6, 3, &rv.grid); }
        memset(&vw, 0, sizeof vw); at_room_fill(&rv, &sc, &vw, 1000.0);
        s = rec_sink();
        at_render_ex(&sc, &vw, 1140.0f, 1000.0, 0, &FAKE, &s, &hits, &info);
        CHECK(info.entries < 1200 && !info.capped && info.hits_dropped == 0);
        CHECK(find_text("ROOM ABCD") != NULL && find_text("STAGE STRIKING") != NULL);                  /* the explainer, from the chrome */
        vw.room = NULL; s = rec_sink();
        at_render_ex(&sc, &vw, 640.0f, 1000.0, 0, &FAKE, &s, &hits, &info);
        CHECK(find_text("BANNED") == NULL && hits.n == 0);                                              /* chrome only, nothing dangling */
    }
}
```

Two checks lean on strings the implementation below chooses (`READY - WAITING`, `B CANCEL`, `Set by the host.`, `P1 STRUCK`); keep them identical in both places.

- [ ] **Step 2: Run to verify it fails.** `nt atlas-room`. Expected: a compile error (`at_room_render` undeclared).
- [ ] **Step 3: Declarations.** In `pc/platform/gw_ui_input.h` extend the hit enum: `enum { AT_HIT_CELL = 1, AT_HIT_KEY = 2, AT_HIT_DIALOG = 3, AT_HIT_ROOM = 4 };` (the generic `at_mouse_events` never sees a room hit: room screens use the mouse function of Task 6; add one line to its comment saying so). In `pc/platform/gw_ui_room.h`, before the closing `#ifdef __cplusplus`:

```c
/* hit codes carried in AtHit.a (kind AT_HIT_ROOM); AtHit.b is the stage index or code slot */
enum { AT_RH_STAGE = 1, AT_RH_ACTION, AT_RH_LEAVE, AT_RH_COPY, AT_RH_CODE_SLOT, AT_RH_CODE_UP, AT_RH_CODE_DOWN };
/* Draws the primary of a room screen into L->primary and records hit rectangles (hits may be NULL: nothing is recorded).
 * A NULL view draws nothing. Returns how many hit rectangles did not fit in AtHits. */
int at_room_render(const AtRoomView *v, const AtLayout *L, const AtTextOps *o, const AtSink *s, AtHits *hits, double now_ms);
```

- [ ] **Step 4: The renderer branch.** In `pc/platform/gw_ui_render.c`, in `at_render_ex`, replace the two lines that choose the primary:

```c
    if (sc->primary == AT_PRIMARY_ROOM) hc.dropped += at_room_render(v->room, &L, o, s, hc.hits, now);
    else if (sc->primary == AT_PRIMARY_GRID) draw_grid(sc, v, &L, o, s, &hc);
    else draw_list(sc, v, &L, o, s, &hc);
```

and add `#include "gw_ui_room.h"` at the top. (`hc.hits` is NULL while a dialog is open, which `at_room_render` honours.) Add `pc/platform/gw_ui_room.c` and `gw_ui_online_parts.c` to the `atlas-render` and `atlas-binding` source lists in `native_test.sh`: `render.c` now references them.
- [ ] **Step 5: The implementation.** Append to `pc/platform/gw_ui_room.c`:

```c
/* ---- the composite render ------------------------------------------------------------------------ */
static AtRect rc(float x, float y, float w, float h) { AtRect r; r.x = x; r.y = y; r.w = w; r.h = h; return r; }
static void e2(const AtSink *s, AtRect r) { at_plate(s, r, AT_C_PLATE2, AT_C_EDGE2, 3.0f, (float) AT_PX_CH_S); }
static unsigned port_rgba(int who) { return who == 0 ? AT_C_P1 : AT_C_P2; }

static void hit_add(AtHits *h, AtRect r, int a, int b, int *dropped)
{
    if (h == NULL) return;
    if (h->n >= AT_MAX_HITS) { (*dropped)++; return; }
    h->h[h->n].r = r; h->h[h->n].kind = AT_HIT_ROOM; h->h[h->n].a = a; h->h[h->n].b = b;
    h->n++;
}

/* a button: a 5 px chamfer plate with the key glyph and a label */
static void button(const AtSink *s, const AtTextOps *o, AtRect r, unsigned face, unsigned edge, char btn, const char *label)
{
    at_plate(s, r, face, edge, 3.0f, (float) AT_PX_CH_S);
    at_part_hint(s, o, r.x + 12.0f, r.y + r.h * 0.5f + 5.0f, btn, label);
}

/* RECONCILE (step 4): the port card. Assumed: AtPortCard { int port (1..4); char name[], sub[], tag[]; int tag_tone; int dim; }
 * and at_part_portcard(sink, ops, rect, card, state). Everything else in this file calls only this wrapper. */
static void room_card(const AtSink *s, const AtTextOps *o, AtRect r, const AtRoomPlayer *p, int who, int is_me, const char *tag, int tone)
{
    AtPortCard c;
    memset(&c, 0, sizeof c);
    c.port = who + 1;
    if (p->present) snprintf(c.name, sizeof c.name, "%s", p->name[0] ? p->name : is_me ? "You" : "Opponent");
    else snprintf(c.name, sizeof c.name, "%s", "Waiting...");
    snprintf(c.sub, sizeof c.sub, "%s", p->present ? p->fighter : "");
    snprintf(c.tag, sizeof c.tag, "%s", tag);
    c.tag_tone = tone;
    c.dim = !p->present;
    at_part_portcard(s, o, r, &c, 0);
}

static const char *player_tag(const AtRoomView *v, int who, int *tone)
{
    const AtRoomPlayer *p = &v->pl[who];
    *tone = AT_TAG_PLAIN;
    if (v->reconnecting) { *tone = AT_TAG_SUN; return "RECONNECTING"; }
    if (!p->present) return "WAITING";
    if (p->ready) { *tone = AT_TAG_JADE; return "READY"; }
    if (v->kind == AT_ROOM_WAIT) return who == 0 ? "HOST" : "JOINED";
    if (p->locked) { *tone = AT_TAG_JADE; return "LOCKED IN"; }
    return v->phase == AT_PH_CHAR_BLIND || v->phase == AT_PH_CHAR_WINNER || v->phase == AT_PH_CHAR_LOSER ? "CHOOSING" : "";
}

static int render_code(const AtRoomView *v, const AtLayout *L, const AtTextOps *o, const AtSink *s, AtHits *h)
{
    AtRect P = L->primary, f;
    float fw = P.w - 48.0f, y;
    const char *msg = v->code_msg;
    int dropped = 0, i, bad = v->code_msg_bad;
    if (fw > 330.0f) fw = 330.0f;
    f = rc(P.x + (P.w - fw) * 0.5f, P.y + 54.0f, fw, 120.0f);
    at_text(s, o, AT_R_CAP12, "ROOM CODE", f.x, f.y + 4.0f, AT_C_MUTED, AT_ALIGN_LEFT, 0.0f);
    at_part_code(s, o, f, &v->code_in);
    for (i = 0; i < 4; i++) hit_add(h, at_code_slot_rect(f, i), AT_RH_CODE_SLOT, i, &dropped);
    {
        AtRect a = at_code_slot_rect(f, v->code_in.slot < 0 ? 0 : v->code_in.slot > 3 ? 3 : v->code_in.slot);
        hit_add(h, rc(a.x, a.y - AT_CODE_BAND, a.w, AT_CODE_BAND), AT_RH_CODE_UP, 0, &dropped);
        hit_add(h, rc(a.x, a.y + a.h, a.w, AT_CODE_BAND), AT_RH_CODE_DOWN, 0, &dropped);
    }
    y = f.y + f.h + 26.0f;
    at_text(s, o, AT_R_BODY14, "Up and down change a letter, left and right move between slots.", P.x + P.w * 0.5f, y, AT_C_MUTED, AT_ALIGN_CENTER, P.w - 48.0f);
    if (msg[0]) {
        float x = f.x, tw = 0.0f;
        if (bad) tw = at_part_tag(s, o, x, y + 16.0f, "FAILED", AT_TAG_ROSE, 0.0f) + 8.0f;
        at_text(s, o, AT_R_BODY14, msg, x + tw, y + 31.0f, bad ? AT_C_IVORY : AT_C_MUTED, AT_ALIGN_LEFT, f.w - tw);
    }
    return dropped;
}

static const char *stage_list_name(const AtRoomView *v) { return v->stage_all ? "All stages" : "Competitive"; }

static int render_wait(const AtRoomView *v, const AtLayout *L, const AtTextOps *o, const AtSink *s, AtHits *h)
{
    AtRect P = L->primary, plate, strip, leave, rules;
    float pad = 12.0f, lw = (P.w - 3.0f * pad) * 0.58f, rx = P.x + pad + lw + pad, y = P.y + pad;
    int dropped = 0, i, tone;
    const char *tag;
    char line[AT_ROOM_TEXT];
    plate = rc(P.x + pad, y, lw, 110.0f);
    e2(s, plate);
    at_text(s, o, AT_R_CAP12, v->random_search ? "SEARCHING" : v->host ? "ROOM CODE" : "JOINING ROOM", plate.x + 14.0f, plate.y + 22.0f, AT_C_MUTED, AT_ALIGN_LEFT, plate.w - 28.0f);
    if (v->random_search) {
        char t[16];
        snprintf(t, sizeof t, "%d:%02d", v->random_secs / 60, v->random_secs % 60);
        at_text(s, o, AT_R_HERO, t, plate.x + 14.0f, plate.y + 70.0f, AT_C_IVORY, AT_ALIGN_LEFT, plate.w - 28.0f);
    } else {
        at_text(s, o, AT_R_DISPLAY, v->code, plate.x + 14.0f, plate.y + 74.0f, AT_C_IVORY, AT_ALIGN_LEFT, plate.w - 28.0f - (v->host ? 100.0f : 0.0f));
    }
    at_text(s, o, AT_R_BODY14, v->random_search ? "Looking for another player." : v->host ? "Share it to invite a friend." : "The host sees you as soon as you are in.",
            plate.x + 14.0f, plate.y + 98.0f, AT_C_MUTED, AT_ALIGN_LEFT, plate.w - (v->host && !v->random_search ? 130.0f : 28.0f));
    if (v->host && !v->random_search) {
        AtRect cb = rc(plate.x + plate.w - 14.0f - 104.0f, plate.y + plate.h - 14.0f - 28.0f, 104.0f, 28.0f);
        button(s, o, cb, AT_C_PLATE, AT_C_EDGE, 'X', v->copied ? "Copied" : "Copy");
        hit_add(h, cb, AT_RH_COPY, 0, &dropped);
    }
    y = plate.y + plate.h + 8.0f;
    for (i = 0; i < 2; i++) {
        AtRect c = rc(P.x + pad, y, lw, 56.0f);
        tag = player_tag(v, i, &tone);
        room_card(s, o, c, &v->pl[i], i, i == v->me, tag, tone);
        y += 64.0f;
    }
    strip = rc(P.x + pad, y, lw, 40.0f);
    e2(s, strip);
    {
        int bars = v->ping_ms < 0 ? 0 : v->link_bars;
        float meter_w = 150.0f;                                                      /* the meter is at most 18 + 6 + the word + 8 + the number: under 150 at 640 */
        snprintf(line, sizeof line, "%s", v->status[0] ? v->status : "Connecting...");
        at_text(s, o, AT_R_BODY14, line, strip.x + 14.0f, strip.y + 25.0f, AT_C_TEXT2, AT_ALIGN_LEFT, strip.w - 28.0f - meter_w);
        at_part_link(s, o, strip.x + strip.w - 14.0f - meter_w, strip.y + 27.0f, bars, v->ping_ms, 1);
    }
    leave = rc(P.x + pad, P.y + P.h - pad - 44.0f, 190.0f, 44.0f);
    button(s, o, leave, AT_C_PLATE, AT_C_EDGE, 'B', v->random_search ? "Stop" : v->host ? "Close room" : "Cancel");
    hit_add(h, leave, AT_RH_LEAVE, 0, &dropped);
    rules = rc(rx, P.y + pad, P.x + P.w - pad - rx, P.h - 2.0f * pad);
    at_text(s, o, AT_R_CAP12, "ROOM RULES", rules.x + 4.0f, rules.y + 14.0f, AT_C_MUTED, AT_ALIGN_LEFT, rules.w * 0.5f);
    at_text(s, o, AT_R_CAP12, "HOST SETS", rules.x + rules.w - 4.0f, rules.y + 14.0f, AT_C_DIM, AT_ALIGN_RIGHT, rules.w * 0.5f);
    if (!v->rules_known) {
        at_text(s, o, AT_R_BODY14, "Set by the host.", rules.x + 4.0f, rules.y + 44.0f, AT_C_MUTED, AT_ALIGN_LEFT, rules.w - 8.0f);
        at_text(s, o, AT_R_BODY12, "You see the rules in the lobby.", rules.x + 4.0f, rules.y + 62.0f, AT_C_DIM, AT_ALIGN_LEFT, rules.w - 8.0f);
    } else {
        char val[6][24];
        static const char *const names[6] = { "Stage list", "Turbo", "Envoy", "Stocks", "Time limit", "Input delay" };
        snprintf(val[0], 24, "%s", stage_list_name(v));
        snprintf(val[1], 24, "%s", v->turbo ? "On" : "Off");
        snprintf(val[2], 24, "%s", v->envoy ? "On" : "Off");
        snprintf(val[3], 24, "%d", v->stocks);
        snprintf(val[4], 24, "%d min", v->minutes);
        snprintf(val[5], 24, "%d frames", v->delay);
        for (i = 0; i < 6; i++) {
            AtItem it;
            memset(&it, 0, sizeof it);
            snprintf(it.label, sizeof it.label, "%s", names[i]);
            it.vkind = AT_VAL_TEXT;
            snprintf(it.text, sizeof it.text, "%s", val[i]);
            at_part_row(s, o, rc(rules.x, rules.y + 26.0f + (float) i * 39.0f, rules.w, 34.0f), &it, AT_ST_REST);   /* read-only: never focused */
        }
    }
    return dropped;
}

static int render_lobby(const AtRoomView *v, const AtLayout *L, const AtTextOps *o, const AtSink *s, AtHits *h)
{
    AtRect P = L->primary;
    float pad = 12.0f, cw = (P.w - 2.0f * pad - 8.0f) * 0.5f, y = P.y + pad, gx = P.x + pad, gw = P.w - 2.0f * pad, gy, gh, th, ay;
    int dropped = 0, i, k, tone, cur = at_room_cursor_fix(v), page = 0, rows_used = 1, nh = 0, has_action;
    int deciding = v->phase == AT_PH_STRIKE || v->phase == AT_PH_BAN || v->phase == AT_PH_PICK;   /* tiles can be acted on only now */
    const AtGrid *g = &v->grid;
    char buf[48];
    for (i = 0; i < 2; i++) {
        const char *tag = player_tag(v, i, &tone);
        room_card(s, o, rc(P.x + pad + (float) i * (cw + 8.0f), y, cw, 56.0f), &v->pl[i], i, i == v->me, tag, tone);
    }
    y += 64.0f;
    /* the coin flip, or whose turn it is */
    if (v->coin_on) {
        snprintf(buf, sizeof buf, "COIN FLIP: P%d STRIKES FIRST", v->first + 1);
        at_part_tag(s, o, gx, y, buf, AT_TAG_SUN, gw * 0.6f);
    } else if ((v->phase == AT_PH_STRIKE || v->phase == AT_PH_BAN || v->phase == AT_PH_PICK) && !v->reconnecting) {
        if (v->my_stage_turn) at_part_tag(s, o, gx, y, "YOUR TURN", AT_TAG_EMBER, gw * 0.4f);
        else { snprintf(buf, sizeof buf, "P%d'S TURN", v->turn + 1); at_part_tag(s, o, gx, y, buf, AT_TAG_PLAIN, gw * 0.4f); }
    }
    if (g->pages > 1) {
        if (cur >= 0 && cur < g->n) page = g->cell[cur].page;
        snprintf(buf, sizeof buf, "PAGE %d / %d", page + 1, g->pages);
        at_text(s, o, AT_R_CAP12, buf, gx + gw, y + 14.0f, AT_C_MUTED, AT_ALIGN_RIGHT, gw * 0.4f);
    }
    y += 30.0f;
    has_action = (v->can_ready || v->can_pick) && !v->reconnecting;
    ay = P.y + P.h - pad - 40.0f;
    gy = y;
    gh = (has_action ? ay - 8.0f : P.y + P.h - pad) - gy;
    for (k = 0; k < g->nhead; k++) if (g->head[k].page == page) nh++;
    for (i = 0; i < g->n; i++) if (g->cell[i].page == page && g->cell[i].row + 1 > rows_used) rows_used = g->cell[i].row + 1;
    th = (gh - 6.0f * (float) rows_used - 18.0f * (float) nh) / (float) rows_used;
    if (th > 64.0f) th = 64.0f;
    if (th < 30.0f) th = 30.0f;
    for (k = 0, i = 0; k < g->nhead; k++) {
        const AtGridHead *hd = &g->head[k];
        if (hd->page != page) continue;
        at_text(s, o, AT_R_CAP12, hd->group ? "COUNTERPICKS" : "STARTERS", gx, gy + (float) hd->row * (th + 6.0f) + 18.0f * (float) i + 13.0f, AT_C_MUTED, AT_ALIGN_LEFT, gw * 0.6f);
        at_poly_rect(s, gx, gy + (float) hd->row * (th + 6.0f) + 18.0f * (float) i + 16.0f, gw, 1.0f, AT_C_LINE);
        i++;
    }
    for (i = 0; i < g->n && i < v->n_stages; i++) {
        const AtGridCell *c = &g->cell[i];
        const AtRoomStage *st = &v->st[i];
        AtCell cell;
        AtRect r;
        int heads_above = 0, focus, dim, stt;
        float tw = (gw - 6.0f * (float) (g->cols - 1)) / (float) g->cols, ty;
        const char *word = NULL;
        unsigned wtone = AT_C_MUTED;
        if (c->page != page) continue;
        for (k = 0; k < g->nhead; k++) if (g->head[k].page == page && g->head[k].row <= c->row) heads_above++;
        r = rc(gx + (float) c->col * (tw + 6.0f), gy + (float) c->row * (th + 6.0f) + 18.0f * (float) heads_above, tw, th);
        focus = i == cur && v->my_stage_turn && !v->reconnecting;
        dim = v->reconnecting || !deciding || st->state != AT_STAGE_FREE || !st->open;
        stt = focus ? AT_ST_FOCUS : dim ? AT_ST_DISABLED : AT_ST_REST;
        memset(&cell, 0, sizeof cell);
        cell.model = AT_NO_MODEL;
        snprintf(cell.name, sizeof cell.name, "%s", st->name);
        if (st->state == AT_STAGE_PICKED) cell.flags |= AT_CELL_SELECTED;
        at_part_cell(s, o, r, &cell, stt, port_rgba(v->me));
        if (st->state == AT_STAGE_STRUCK_P1) word = "P1 STRUCK";
        else if (st->state == AT_STAGE_STRUCK_P2) word = "P2 STRUCK";
        else if (st->state == AT_STAGE_BANNED) word = "BANNED";
        else if (st->state == AT_STAGE_PICKED) { word = "PICKED"; wtone = AT_C_JADE; }
        else if (!st->open && deciding) word = "NOT YET";
        else if (!deciding && !v->reconnecting) word = "OUT";                       /* decided: the others are out (a word, not only a dim) */
        ty = focus ? r.y - 2.0f : r.y;
        if (word != NULL) at_text(s, o, AT_R_CAP12, word, r.x + 4.0f, ty + 13.0f, wtone, AT_ALIGN_LEFT, r.w - 8.0f);
        hit_add(h, r, AT_RH_STAGE, i, &dropped);
    }
    if (has_action) {
        AtRect a = rc(gx, ay, gw, 40.0f);
        if (v->can_pick) {
            at_plate(s, a, AT_C_EMBER, AT_C_EMBER_D, 3.0f, (float) AT_PX_CH_S);
            at_text(s, o, AT_R_CAP20, "PICK A FIGHTER", a.x + a.w * 0.5f, a.y + 27.0f, AT_C_INK, AT_ALIGN_CENTER, a.w - 24.0f);
            hit_add(h, a, AT_RH_ACTION, 0, &dropped);
        } else if (!v->ready_mine) {
            at_plate(s, a, AT_C_EMBER, AT_C_EMBER_D, 3.0f, (float) AT_PX_CH_S);
            at_text(s, o, AT_R_CAP20, "READY", a.x + a.w * 0.5f, a.y + 27.0f, AT_C_INK, AT_ALIGN_CENTER, a.w - 24.0f);
            hit_add(h, a, AT_RH_ACTION, 0, &dropped);
        } else {
            at_plate(s, a, AT_C_PLATE2, AT_C_JADE, 3.0f, (float) AT_PX_CH_S);
            at_text(s, o, AT_R_CAP20, "READY - WAITING", a.x + a.w * 0.5f, a.y + 27.0f, AT_C_JADE, AT_ALIGN_CENTER, a.w - 24.0f);
        }
    }
    if (v->countdown_s > 0) {
        AtRect c = rc(P.x + P.w * 0.5f - 80.0f, P.y + P.h * 0.5f - 60.0f, 160.0f, 120.0f);
        at_plate(s, c, AT_C_PLATE, AT_C_EDGE, 3.0f, (float) AT_PX_CH);
        snprintf(buf, sizeof buf, "%d", v->countdown_s);
        at_text(s, o, AT_R_DISPLAY, buf, c.x + c.w * 0.5f, c.y + 72.0f, AT_C_IVORY, AT_ALIGN_CENTER, c.w - 16.0f);
        if (v->ready_mine) at_text(s, o, AT_R_CAP12, "B CANCEL", c.x + c.w * 0.5f, c.y + 104.0f, AT_C_DIM, AT_ALIGN_CENTER, c.w - 16.0f);
    }
    return dropped;
}

int at_room_render(const AtRoomView *v, const AtLayout *L, const AtTextOps *o, const AtSink *s, AtHits *hits, double now_ms)
{
    (void) now_ms;
    if (v == NULL) return 0;
    switch (v->kind) {
    case AT_ROOM_CODE: return render_code(v, L, o, s, hits);
    case AT_ROOM_WAIT: return render_wait(v, L, o, s, hits);
    case AT_ROOM_LOBBY: return render_lobby(v, L, o, s, hits);
    default: return 0;
    }
}
```

- [ ] **Step 6: Run.** `nt atlas-room`, then `for t in atlas-render atlas-binding atlas-input atlas-parts; do nt $t | tail -1; done`. Expected: `0 failed` everywhere. Likely first failures and what they mean: a `lint_text_inside` failure on a card is the step 4 card part's own fit (fix there, and add the failing name to its test); an overlap between a card name and its tag at 640 means the wrapper's `r` is too narrow for both (the lobby cards are `(P.w - 32) / 2`, about 168 px at 640 with the normal explainer): the card part must give the tag its width first and fit the name into the rest.
- [ ] **Step 7: Commit.** Game repo: the files above, message `atlas online: the composite render for the code entry, the waiting room and the lobby`.

---

### Task 6: Intents: pad stays legacy; keyboard and mouse become the same menu bits

This is the task that proves "nothing presentation may touch the netplay stream". The design that makes it provable:

1. **The pad path is not translated at all.** `fl_frame` already builds `in = mn_80229624(4) | fms_menu_bits()`: the retail pad read, then the old mouse bits. Atlas replaces only the second term. The first (the pad) is untouched, so every pad press reaches the lobby state machine exactly as today.
2. **Keyboard and mouse produce `AtRoomIntent`s**; the adapter turns each into the **same `MenuInput_*` bit** the equivalent pad press has (Task 7), or into a local cursor move (`fl.cur`, `Netplay_CodeMove`), which are things the legacy mouse code already did.
3. **Hover alone never produces an accept-class intent**; a pointer at rest never produces anything; a pointer off the picture never produces anything.

One deliberate narrowing, said plainly: the legacy lobby treats a left click **anywhere** (except the footer) when it is not your stage turn as A (it readies you, or opens the fighter pick). Atlas makes that click act only on the **action plate** (READY, PICK A FIGHTER). A stray click that readies you is a netplay-visible action caused by an ambiguous input; the plate is the visible target. Mouse only, local UI only, and trivially reverted if the owner wants it back.

**Files:**
- Modify (game repo): `pc/platform/gw_ui_room.h`, `pc/platform/gw_ui_room.c`, `pc/tests/atlas_room_test.c`
- Create (workspace repo): `tools/port/check_atlas_online.sh`
- Modify (workspace repo): `tools/port/README.md`

**Interfaces:**
Consumes: `at_key_events` and `AtKeys` (step 1 input), `at_hit_test`, `AtHits`, the room view and hit codes.
Produces: `AtRoomIntent`, `at_room_key_intents`, `at_room_mouse_intents`, `at_room_intent_name` (for logs and tests). Intent kinds: `AT_RI_UP, DOWN, LEFT, RIGHT, ACCEPT, BACK, START, COPY, PASTE, PAGE_L, PAGE_R, STAGE_AT (arg = stage index), CODE_SLOT (arg = slot)`.

- [ ] **Step 1: Write the failing tests.** Add to `pc/tests/atlas_room_test.c` (before `main`; call `intents();` from `main`):

```c
/* A reference model of what the legacy lobby does with each intent (fl_frame_lobby), used only to compare streams.
 * It returns the NETPLAY-VISIBLE actions: the things that call into the protocol. Cursor moves and arming B are local. */
typedef struct { char act[24]; int arg; } NetAct;
typedef struct { const AtRoomView *v; int cursor, armed; NetAct out[16]; int n; } Model;
static void emit(Model *m, const char *a, int arg) { if (m->n < 16) { snprintf(m->out[m->n].act, 24, "%s", a); m->out[m->n].arg = arg; m->n++; } }
static void consume(Model *m, AtRoomIntent in)
{
    const AtRoomView *v = m->v;
    switch (in.kind) {
    case AT_RI_STAGE_AT: m->cursor = in.arg; break;
    case AT_RI_RIGHT: m->cursor = (m->cursor + 1) % v->n_stages; break;
    case AT_RI_LEFT: m->cursor = (m->cursor + v->n_stages - 1) % v->n_stages; break;
    case AT_RI_ACCEPT:
        if (v->can_ready && !v->ready_mine) emit(m, "READY", 1);
        else if (v->can_pick) emit(m, "PICK_CHAR", 0);
        else if (v->my_stage_turn) emit(m, "STAGE_ACT", m->cursor);
        break;
    case AT_RI_START: if (v->can_ready) emit(m, "READY", !v->ready_mine); break;
    case AT_RI_BACK:
        if (v->countdown_s > 0 && v->ready_mine) emit(m, "READY", 0);
        else if (m->armed) emit(m, "LEAVE", 0);
        else m->armed = 1;
        break;
    default: break;
    }
}
static int same(const Model *a, const Model *b)
{
    int i;
    if (a->n != b->n) return 0;
    for (i = 0; i < a->n; i++) if (strcmp(a->out[i].act, b->out[i].act) != 0 || a->out[i].arg != b->out[i].arg) return 0;
    return 1;
}

static int mouse_step(const AtRoomView *v, AtMouse *m, float x, float y, int buttons, int wheel, AtRoomIntent *out, int cap)
{
    return at_room_mouse_intents(v, m, x, y, buttons, wheel, &RH, out, cap);
}

static void intents(void)
{
    static AtRoomView rv;
    AtRoomIntent in[8];
    AtMouse m; AtKeys k;
    Model pad, mouse, kbd;
    int i, n, tile3 = -1, action = -1;
    memset(&m, 0, sizeof m); memset(&k, 0, sizeof k);

    /* a lobby on my stage turn with six open stages; the pointer targets are the recorded hit rectangles */
    fx_view(0, &rv); rv.kind = AT_ROOM_LOBBY; rv.phase = AT_PH_STRIKE; rv.me = 1; rv.host = 0; rv.turn = 1; rv.my_stage_turn = 1; rv.n_stages = 6; rv.cursor = 1;
    { int g[AT_ROOM_STAGES], j; for (j = 0; j < 6; j++) { g[j] = 0; rv.st[j].open = 1; rv.st[j].state = AT_STAGE_FREE; } at_room_grid(g, 6, 3, 3, &rv.grid); }
    draw_room(&rv, 640.0f);
    for (i = 0; i < RH.n; i++) if (RH.h[i].a == AT_RH_STAGE && RH.h[i].b == 3) tile3 = i;
    CHECK(tile3 >= 0);
    {
        float tx = RH.h[tile3].r.x + 5.0f, ty = RH.h[tile3].r.y + 5.0f;
        /* the same job three ways: strike stage 3 */
        memset(&pad, 0, sizeof pad); pad.v = &rv; pad.cursor = 1;
        { AtRoomIntent a = { AT_RI_RIGHT, 0 }, b = { AT_RI_RIGHT, 0 }, c = { AT_RI_ACCEPT, 0 }; consume(&pad, a); consume(&pad, b); consume(&pad, c); }   /* pad: right, right, A */
        memset(&mouse, 0, sizeof mouse); mouse.v = &rv; mouse.cursor = 1;
        n = mouse_step(&rv, &m, 400.0f, 300.0f, 0, 0, in, 8);                      /* the pointer arrives somewhere: nothing */
        for (i = 0; i < n; i++) consume(&mouse, in[i]);
        n = mouse_step(&rv, &m, tx, ty, 0, 0, in, 8);                              /* hover over tile 3 */
        CHECK(n == 1 && in[0].kind == AT_RI_STAGE_AT && in[0].arg == 3);           /* hover moves the cursor... */
        for (i = 0; i < n; i++) consume(&mouse, in[i]);
        CHECK(mouse.n == 0);                                                       /* ...and does nothing netplay-visible */
        n = mouse_step(&rv, &m, tx, ty, 1, 0, in, 8);                              /* left click */
        CHECK(n == 2 && in[0].kind == AT_RI_STAGE_AT && in[1].kind == AT_RI_ACCEPT);
        for (i = 0; i < n; i++) consume(&mouse, in[i]);
        memset(&kbd, 0, sizeof kbd); kbd.v = &rv; kbd.cursor = 1;
        n = at_room_key_intents(&k, AT_KEY_RIGHT, 0.0, in, 8); for (i = 0; i < n; i++) consume(&kbd, in[i]);
        n = at_room_key_intents(&k, 0, 10.0, in, 8);
        n = at_room_key_intents(&k, AT_KEY_RIGHT, 20.0, in, 8); for (i = 0; i < n; i++) consume(&kbd, in[i]);
        n = at_room_key_intents(&k, AT_KEY_RIGHT | AT_KEY_ENTER, 30.0, in, 8); for (i = 0; i < n; i++) consume(&kbd, in[i]);
        CHECK(pad.n == 1 && strcmp(pad.out[0].act, "STAGE_ACT") == 0 && pad.out[0].arg == 3);
        CHECK(same(&pad, &mouse));                                                 /* pad, mouse and keyboard: one netplay-visible action */
        CHECK(kbd.n == 1 && strcmp(kbd.out[0].act, "STAGE_ACT") == 0);
    }
    /* hover alone: 100 pointer moves over every rectangle with no button, nothing netplay-visible; a resting pointer is silent */
    {
        Model hv; int steps;
        memset(&hv, 0, sizeof hv); hv.v = &rv; hv.cursor = 1; memset(&m, 0, sizeof m);
        for (steps = 0; steps < 100; steps++) {
            const AtHit *h = &RH.h[steps % RH.n];
            n = mouse_step(&rv, &m, h->r.x + 3.0f + (float) (steps % 3), h->r.y + 3.0f, 0, 0, in, 8);
            for (i = 0; i < n; i++) consume(&hv, in[i]);
        }
        CHECK(hv.n == 0);
        n = mouse_step(&rv, &m, 123.0f, 45.0f, 0, 0, in, 8); n = mouse_step(&rv, &m, 123.0f, 45.0f, 0, 0, in, 8); CHECK(n == 0);   /* resting: silent */
        n = mouse_step(&rv, &m, -1000.0f, -1000.0f, 1, 0, in, 8); CHECK(n == 0);                                                   /* off the picture: silent */
        n = mouse_step(&rv, &m, tx_of(tile3), ty_of(tile3), 0, 0, in, 8);                                                          /* back on, no click yet */
        CHECK(n <= 1);
    }
    /* the ready phase: a click on the action plate readies (as A does), a click elsewhere does nothing, START and A agree */
    rv.my_stage_turn = 0; rv.phase = AT_PH_READY; rv.can_ready = 1; rv.ready_mine = 0; draw_room(&rv, 640.0f);
    for (i = 0; i < RH.n; i++) if (RH.h[i].a == AT_RH_ACTION) action = i;
    CHECK(action >= 0);
    memset(&m, 0, sizeof m);
    mouse_step(&rv, &m, RH.h[action].r.x + 4.0f, RH.h[action].r.y + 4.0f, 0, 0, in, 8);
    n = mouse_step(&rv, &m, RH.h[action].r.x + 4.0f, RH.h[action].r.y + 4.0f, 1, 0, in, 8);
    CHECK(n == 1 && in[0].kind == AT_RI_ACCEPT);
    mouse_step(&rv, &m, 3.0f, 3.0f, 0, 0, in, 8);
    n = mouse_step(&rv, &m, 3.0f, 3.0f, 1, 0, in, 8); CHECK(n == 0);                                    /* a click on nothing */
    n = mouse_step(&rv, &m, 3.0f, 3.0f, 2, 0, in, 8); CHECK(n == 1 && in[0].kind == AT_RI_BACK);       /* right click: back */

    /* the Envoy reward pick open does not change one intent or one key (the lobby keeps today's input behaviour) */
    {
        AtRoomIntent a[8], b[8]; int na, nb; AtMouse m1, m2;
        memset(&m1, 0, sizeof m1); memset(&m2, 0, sizeof m2);
        rv.reward_open = 0; draw_room(&rv, 640.0f);
        mouse_step(&rv, &m1, RH.h[action].r.x + 4.0f, RH.h[action].r.y + 4.0f, 0, 0, a, 8);
        na = mouse_step(&rv, &m1, RH.h[action].r.x + 4.0f, RH.h[action].r.y + 4.0f, 1, 0, a, 8);
        rv.reward_open = 1; rv.reward_left_s = 20; draw_room(&rv, 640.0f);
        mouse_step(&rv, &m2, RH.h[action].r.x + 4.0f, RH.h[action].r.y + 4.0f, 0, 0, b, 8);
        nb = mouse_step(&rv, &m2, RH.h[action].r.x + 4.0f, RH.h[action].r.y + 4.0f, 1, 0, b, 8);
        CHECK(na == nb && (na == 0 || a[0].kind == b[0].kind));
    }
    /* B twice leaves, the same for the pad and for a click on the B key hint (the chrome records that hit rectangle: add one by hand) */
    {
        Model mb, pb;
        AtRoomIntent back = { AT_RI_BACK, 0 };
        AtHit key; int hb;
        memset(&key, 0, sizeof key); key.r.x = 200.0f; key.r.y = 440.0f; key.r.w = 80.0f; key.r.h = 22.0f; key.kind = AT_HIT_KEY; key.a = 'B';
        hb = RH.n; RH.h[RH.n++] = key;
        memset(&mb, 0, sizeof mb); mb.v = &rv; memset(&pb, 0, sizeof pb); pb.v = &rv;
        rv.countdown_s = 0;
        consume(&pb, back); consume(&pb, back);
        memset(&m, 0, sizeof m);
        for (i = 0; i < 2; i++) {
            mouse_step(&rv, &m, RH.h[hb].r.x + 4.0f, RH.h[hb].r.y + 4.0f, 0, 0, in, 8);
            n = mouse_step(&rv, &m, RH.h[hb].r.x + 4.0f, RH.h[hb].r.y + 4.0f, 1, 0, in, 8);
            CHECK(n == 1 && in[0].kind == AT_RI_BACK);
            consume(&mb, in[0]);
        }
        CHECK(same(&pb, &mb) && pb.n == 1 && strcmp(pb.out[0].act, "LEAVE") == 0);
        RH.n--;
    }
    /* the code screen: wheel steps the letter, a click on the active slot's strip steps it, a click on another slot moves there */
    fx_view(0, &rv); rv.kind = AT_ROOM_CODE; rv.code_in.slot = 1; draw_room(&rv, 640.0f);
    memset(&m, 0, sizeof m);
    mouse_step(&rv, &m, 300.0f, 200.0f, 0, 0, in, 8);
    n = mouse_step(&rv, &m, 300.0f, 200.0f, 0, 1, in, 8); CHECK(n == 1 && in[0].kind == AT_RI_UP);
    n = mouse_step(&rv, &m, 300.0f, 200.0f, 0, -1, in, 8); CHECK(n == 1 && in[0].kind == AT_RI_DOWN);
    /* the lobby on my stage turn: the wheel turns the page (L before R) */
    rv.kind = AT_ROOM_LOBBY; rv.my_stage_turn = 1; rv.phase = AT_PH_BAN; draw_room(&rv, 640.0f);
    n = mouse_step(&rv, &m, 300.0f, 200.0f, 0, 1, in, 8); CHECK(n == 1 && in[0].kind == AT_RI_PAGE_L);
    n = mouse_step(&rv, &m, 300.0f, 200.0f, 0, -1, in, 8); CHECK(n == 1 && in[0].kind == AT_RI_PAGE_R);
    /* keyboard: arrows move, Enter accepts, Escape goes back, Tab and Shift+Tab page; typed letters are not here at all */
    memset(&k, 0, sizeof k);
    n = at_room_key_intents(&k, AT_KEY_UP, 0.0, in, 8); CHECK(n == 1 && in[0].kind == AT_RI_UP);
    at_room_key_intents(&k, 0, 10.0, in, 8);
    n = at_room_key_intents(&k, AT_KEY_ESC, 20.0, in, 8); CHECK(n == 1 && in[0].kind == AT_RI_BACK);
    at_room_key_intents(&k, 0, 30.0, in, 8);
    n = at_room_key_intents(&k, AT_KEY_TAB, 40.0, in, 8); CHECK(n == 1 && in[0].kind == AT_RI_PAGE_R);
    at_room_key_intents(&k, 0, 50.0, in, 8);
    n = at_room_key_intents(&k, AT_KEY_TAB | AT_KEY_SHIFT, 60.0, in, 8); CHECK(n == 1 && in[0].kind == AT_RI_PAGE_L);
}
```

(`tx_of` and `ty_of` in the hover block are two one-line helpers: `static float tx_of(int hit) { return RH.h[hit].r.x + 5.0f; }` and the same for y. Add them above `intents`. `mouse_step` reads `RH` as drawn by the last `draw_room`. The lobby has no LEAVE button: leaving is the B key hint, whose hit rectangle the chrome records, so the B-twice check adds one by hand.)

- [ ] **Step 2: Run to verify it fails.** `nt atlas-room`. Expected: compile errors for `AtRoomIntent` and the two functions.
- [ ] **Step 3: Implement.** In `pc/platform/gw_ui_room.h` (before the closing `#ifdef __cplusplus`):

```c
/* Input for the room screens. The PAD is not here: the game side reads its own pad bits, exactly as before. Keyboard and
 * mouse become intents, and the adapter turns each intent into the menu bit the equivalent pad press has. */
enum { AT_RI_NONE, AT_RI_UP, AT_RI_DOWN, AT_RI_LEFT, AT_RI_RIGHT, AT_RI_ACCEPT, AT_RI_BACK, AT_RI_START, AT_RI_COPY, AT_RI_PASTE,
       AT_RI_PAGE_L, AT_RI_PAGE_R, AT_RI_STAGE_AT, AT_RI_CODE_SLOT };
typedef struct { int kind, arg; } AtRoomIntent;
int at_room_key_intents(AtKeys *k, unsigned mask, double now_ms, AtRoomIntent *out, int cap);
int at_room_mouse_intents(const AtRoomView *v, AtMouse *m, float x, float y, int buttons, int wheel, const AtHits *hits, AtRoomIntent *out, int cap);
const char *at_room_intent_name(int kind);
```

Append to `pc/platform/gw_ui_room.c`:

```c
/* ---- input ---------------------------------------------------------------------------------------- */
#define PUT(K, A) do { if (n < cap) { out[n].kind = (K); out[n].arg = (A); n++; } } while (0)

int at_room_key_intents(AtKeys *k, unsigned mask, double now_ms, AtRoomIntent *out, int cap)
{
    AtEvent ev[8];
    int ne = at_key_events(k, mask, now_ms, ev, 8), i, n = 0;
    for (i = 0; i < ne; i++) {
        switch (ev[i].type) {
        case AT_EV_MOVE: PUT(ev[i].a == AT_DIR_UP ? AT_RI_UP : ev[i].a == AT_DIR_DOWN ? AT_RI_DOWN : ev[i].a == AT_DIR_LEFT ? AT_RI_LEFT : AT_RI_RIGHT, 0); break;
        case AT_EV_ACCEPT: PUT(AT_RI_ACCEPT, 0); break;
        case AT_EV_BACK: PUT(AT_RI_BACK, 0); break;
        case AT_EV_PAGE: PUT(ev[i].a < 0 ? AT_RI_PAGE_L : AT_RI_PAGE_R, 0); break;
        default: break;
        }
    }
    return n;
}

static int button_intent(int c)
{
    switch (c) {
    case 'A': return AT_RI_ACCEPT;
    case 'B': return AT_RI_BACK;
    case 'X': return AT_RI_COPY;
    case 'Y': return AT_RI_PASTE;
    case 'S': return AT_RI_START;
    case 'L': return AT_RI_PAGE_L;
    case 'R': return AT_RI_PAGE_R;
    default: return AT_RI_NONE;
    }
}

int at_room_mouse_intents(const AtRoomView *v, AtMouse *m, float x, float y, int buttons, int wheel, const AtHits *hits, AtRoomIntent *out, int cap)
{
    int n = 0, hit, moved, left, right;
    if (x < 0.0f || y < 0.0f) {                              /* off the picture (-1000): never an intent */
        m->valid = 0;
        m->buttons = buttons;
        return 0;
    }
    moved = m->valid && (x != m->x || y != m->y);            /* a pointer at rest never acts */
    left = (buttons & 1) && !(m->buttons & 1) && m->valid;
    right = (buttons & 2) && !(m->buttons & 2) && m->valid;
    hit = at_hit_test(hits, x, y);
    if (hit >= 0 && moved && hits->h[hit].kind == AT_HIT_ROOM && hits->h[hit].a == AT_RH_STAGE && v->my_stage_turn &&
        hits->h[hit].b >= 0 && hits->h[hit].b < v->n_stages && v->st[hits->h[hit].b].open)
        PUT(AT_RI_STAGE_AT, hits->h[hit].b);                  /* hover moves the cursor onto an open stage, nothing more */
    if (left && hit >= 0) {
        const AtHit *h = &hits->h[hit];
        if (h->kind == AT_HIT_KEY) {
            int b = button_intent(h->a);
            if (b != AT_RI_NONE) PUT(b, 0);
        } else if (h->kind == AT_HIT_ROOM) {
            switch (h->a) {
            case AT_RH_STAGE: PUT(AT_RI_STAGE_AT, h->b); PUT(AT_RI_ACCEPT, 0); break;   /* as the legacy click: cursor there, then confirm */
            case AT_RH_ACTION: PUT(AT_RI_ACCEPT, 0); break;
            case AT_RH_LEAVE: PUT(AT_RI_BACK, 0); break;
            case AT_RH_COPY: PUT(AT_RI_COPY, 0); break;
            case AT_RH_CODE_SLOT: PUT(AT_RI_CODE_SLOT, h->b); break;
            case AT_RH_CODE_UP: PUT(AT_RI_UP, 0); break;
            case AT_RH_CODE_DOWN: PUT(AT_RI_DOWN, 0); break;
            default: break;
            }
        }
    }
    if (right) PUT(AT_RI_BACK, 0);
    if (wheel != 0) {
        if (v->kind == AT_ROOM_CODE) PUT(wheel > 0 ? AT_RI_UP : AT_RI_DOWN, 0);
        else if (v->kind == AT_ROOM_LOBBY && v->my_stage_turn) PUT(wheel > 0 ? AT_RI_PAGE_L : AT_RI_PAGE_R, 0);
    }
    m->valid = 1; m->x = x; m->y = y; m->buttons = buttons;
    return n;
}
#undef PUT

const char *at_room_intent_name(int kind)
{
    static const char *const names[] = { "none", "up", "down", "left", "right", "accept", "back", "start", "copy", "paste", "page_l", "page_r", "stage_at", "code_slot" };
    return kind >= 0 && kind < (int) (sizeof names / sizeof names[0]) ? names[kind] : "?";
}
```

- [ ] **Step 4: Run.** `nt atlas-room`. Expected: `0 failed`. If the "same job three ways" check fails on `mouse.n` after hover, a hover emitted an accept-class intent: that is the exact bug this task exists to catch, so fix the function, never the model.
- [ ] **Step 5: The isolation guard.** Create `tools/port/check_atlas_online.sh`:

```bash
#!/usr/bin/env bash
# Atlas online isolation guards (step 6). Textual by design: they say what the files may contain, and fail loudly.
#   tools/port/check_atlas_online.sh [GAME_CHECKOUT]     (default: $GW_MELEE, else <root>/melee)
set -u
G="${1:-${GW_MELEE:-$(cd "$(dirname "$0")/../.." && pwd)/melee}}"
fail=0
bad() { echo "FAIL: $*"; fail=1; }

# 1. No host file of the Atlas UI includes a netplay header or names a netplay function.
hits=$(grep -n -E '#include[[:space:]]*[<"][^>"]*netplay|\bNetplay_[A-Za-z]|\bgw_Netplay_' "$G"/pc/platform/gw_ui_*.c "$G"/pc/platform/gw_ui_*.h "$G"/pc/platform/gw_script_ui.inc 2>/dev/null || true)
if [ -n "$hits" ]; then
    echo "$hits"
    bad "a host Atlas file touches netplay (lines above)"
fi

# 2. The game-side adapter only READS netplay state: every Netplay_ name in it is in the read allow-list. All writes stay in
#    gmfrontend_online.inc, where the state machine is.
ADAPTER="$G/src/melee/gm/gmfrontend_atlas_online.inc"
READS="LobbyInfo LobbyPlayer LobbyMe LobbyPhase LobbySeq LobbyStage LobbyStageExt LobbyStageGroup LobbyStageOpen LobbyStageName IsHost RoomCode Ping PlayerName FighterName MenuStatus Turbo Envoy StageMode TurboPref EnvoyPref RandomStatus RandomSeconds CodeChar CodeSlot CodeComplete PeerLeft RematchPending"
if [ -f "$ADAPTER" ]; then
    for name in $(grep -o -E 'Netplay_[A-Za-z]+' "$ADAPTER" | sort -u | sed 's/^Netplay_//'); do
        case " $READS " in *" $name "*) ;; *) bad "the adapter calls Netplay_$name, which is not a read (writes belong in gmfrontend_online.inc)";; esac
    done
fi

# 3. The adapter introduces no Netplay call the legacy lobby did not already make.
LEGACY="$G/src/melee/gm/gmfrontend_online.inc"
if [ -f "$ADAPTER" ] && [ -f "$LEGACY" ]; then
    for name in $(grep -o -E 'Netplay_[A-Za-z]+' "$ADAPTER" | sort -u); do
        grep -q "$name" "$LEGACY" || grep -q "$name" "$G/src/melee/gm/gmfrontend.c" || bad "$name is new: the adapter must not add a netplay call"
    done
fi

# 4. The intent to menu-bit table. Intents cross the shim BY NAME (at_room_intent_name), and each name maps to one MenuInput bit,
#    on one line, once.
if [ -f "$ADAPTER" ]; then
    for pair in "up:MenuInput_Up" "down:MenuInput_Down" "left:MenuInput_Left" "right:MenuInput_Right"                 "accept:MenuInput_Confirm" "back:MenuInput_Back" "start:MenuInput_StartButton" "copy:MenuInput_XButton"                 "paste:MenuInput_YButton" "page_l:MenuInput_LTrigger" "page_r:MenuInput_RTrigger"; do
        k="${pair%%:*}"; b="${pair##*:}"
        n=$(grep -c -E "strcmp\(n, \"$k\"\) == 0\).*$b" "$ADAPTER")
        [ "$n" = 1 ] || bad "intent \"$k\" must map to $b exactly once in the adapter (found $n)"
    done
    # 5. The pad term of the menu input is the legacy read, untouched.
    grep -q 'mn_80229624(4) | ' "$G/src/melee/gm/gmfrontend_online.inc" || bad "fl_frame no longer ORs the retail pad read (mn_80229624(4)) with the mouse bits"
    # 7. The opponent's blind pick never reaches the host view: the one Netplay_FighterName call sits inside fa_room_fighter, after
    #    the same fl_card_portrait test the legacy card used to decide what to show.
    [ "$(grep -c 'Netplay_FighterName' "$ADAPTER")" = 1 ] || bad "Netplay_FighterName must be called exactly once in the adapter, inside fa_room_fighter"
    awk '/static .*fa_room_fighter/ {f=1} f && /fl_card_portrait/ {ok=1} f && /Netplay_FighterName/ {exit !ok}' "$ADAPTER" || bad "fa_room_fighter reads the fighter before asking fl_card_portrait (the blind pick would leak)"
fi

# 6. No mask and no mod hook from the Atlas online files.
hits=$(grep -n -E 'input_mask|input_chord|gs_require_offline' "$G"/pc/platform/gw_ui_room*.c "$G"/pc/platform/gw_ui_room*.h "$ADAPTER" 2>/dev/null || true)
if [ -n "$hits" ]; then
    echo "$hits"
    bad "an Atlas online file mentions the input mask"
fi

[ "$fail" = 0 ] && echo "check_atlas_online: ok"
exit "$fail"
```

Run it now (the adapter does not exist yet, so only guards 1 and 6 run and pass):

```bash
chmod +x "$WS/tools/port/check_atlas_online.sh" && bash "$WS/tools/port/check_atlas_online.sh" "$GW_MELEE"
```

Expected: `check_atlas_online: ok`. Prove guard 1 can fail: `echo '#include "gw_netplay.h"' >> "$GW_MELEE/pc/platform/gw_ui_room.h"`, rerun (expected: `FAIL: a host Atlas file touches netplay` and exit 1), then remove that line with `git -C "$GW_MELEE" checkout -p` or by editing it out, and rerun to see `ok` again. Add a line to `tools/port/README.md` under the tests section naming the script and what it pins.
- [ ] **Step 6: Commit.** Game repo: `pc/platform/gw_ui_room.h/.c`, `pc/tests/atlas_room_test.c`, message `atlas online: keyboard and mouse intents for the room screens, pad path left as it was`. Workspace repo: `tools/port/check_atlas_online.sh`, `tools/port/README.md`, message `tools: check_atlas_online.sh, the netplay-isolation guards for the Atlas online screens`.

---

### Task 7: The host door and the game-side adapter

The host keeps one room view. The game side fills it **by name**, through scalar shims, once a frame, and gets back **intent names**. Nothing numeric is shared between the two sides (phases, stage states, settings keys and intents all cross as strings), so a renumbered enum cannot silently mislead a lobby. The shim file reads no netplay state. The adapter reads netplay state only through the read-only allow-list of Task 6 and decides what may be shown with the **legacy predicates** (`fl_phase`, `fl_my_stage_turn`, `fl_can_pick_char`, `fl_reconnecting`, `fl_card_portrait`, `fl_stage_open`, `fl_instruction`, `fl_phase_title`), never with a second copy of their rules.

**Information that must not leak.** In game 1 the characters are picked blind: the opponent's card says "Locked in" until both have locked. The legacy card decides that with `fl_card_portrait`. The adapter's one call to `Netplay_FighterName` sits inside `fa_room_fighter`, after the same test, so the opponent's pick never even reaches the host view. Guard 7 of `check_atlas_online.sh` pins it.

**Gate:** Task 0 exits 0 (the door names below are `RECONCILE` against step 2).

**Files:**
- Create (game repo): `pc/platform/gw_ui_room_native.h`, `pc/platform/gw_ui_room_native.c`, `pc/tests/atlas_room_native_test.c`, `src/melee/gm/gmfrontend_atlas_online.inc`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-room-native`)

**Interfaces:**
Consumes: step 2's native door, assumed as `gw_ui_native_attach(sc, vw, hits)`, `gw_ui_native_detach(vw)`, `gw_ui_native_canvas_w()`, `gw_ui_native_now_ms()`, `gw_ui_native_input(x, y, buttons, wheel, key_mask)`, `gw_ui_native_enabled()` (`MELEE_ATLAS` on and the Atlas fonts available). Produces the shims below. The game side declares them without the `gw_` prefix (the repo's convention, `src/melee/gm/CLAUDE.md`).

| Shim (host name) | Does |
|---|---|
| `gw_Ui_RoomOn()` | 1 when Atlas room screens are enabled this run |
| `gw_Ui_RoomBegin("code" or "wait" or "lobby")` | attach that screen (a fresh view and a fresh open fade when the kind changes; nothing when it is already that kind) |
| `gw_Ui_RoomEnd()` | detach, clear the view and the intent queue |
| `gw_Ui_RoomSetInt(key, v)`, `gw_Ui_RoomSetStr(key, s)` | set a field by name; 1 when the key is known, 0 (ignored) otherwise or when no room is attached; strings are copied and cut to the field |
| `gw_Ui_RoomPlayer(who, present, locked, ready, score)`, `gw_Ui_RoomPlayerName(who, name, fighter)` | the two cards |
| `gw_Ui_RoomStageCount(n)`, `gw_Ui_RoomStage(i, name, state, starter, open)` | the stage list (cut at `AT_ROOM_STAGES`); `state` is `"free"`, `"p1"`, `"p2"`, `"banned"` or `"picked"` |
| `gw_Ui_RoomGridFor(n, starters)`, `gw_Ui_RoomGridCell(i, &col, &row, &page)` | the one grid model, for the legacy cursor code; returns the page count / 1 when the cell exists |
| `gw_Ui_RoomFrame()` | once a frame: read local keyboard and mouse, queue intents, rebuild the screen record |
| `gw_Ui_RoomPollName(out, cap, &arg)` | pop one intent name (`"up"`, `"accept"`, `"stage_at"` ...); 0 when none |

- [ ] **Step 1: Write the failing host test.** Create `pc/tests/atlas_room_native_test.c`:

```c
#include "atlas_lint.h"
#include "atlas_room_fixture.h"
#include "../platform/gw_ui_room_native.h"

/* stand-ins for step 2's native door */
static int st_attached, st_detached, st_enabled = 1;
static float st_w = 640.0f, st_mx = -1000.0f, st_my = -1000.0f;
static int st_mb, st_wheel;
static unsigned st_km;
static double st_now = 1000.0;
void gw_ui_native_attach(const AtScreen *sc, AtView *vw, AtHits *hits) { (void) sc; (void) vw; (void) hits; st_attached++; }
void gw_ui_native_detach(const AtView *vw) { (void) vw; st_detached++; }
float gw_ui_native_canvas_w(void) { return st_w; }
double gw_ui_native_now_ms(void) { return st_now; }
void gw_ui_native_input(float *x, float *y, int *b, int *w, unsigned *k) { *x = st_mx; *y = st_my; *b = st_mb; *w = st_wheel; *k = st_km; }
int gw_ui_native_enabled(void) { return st_enabled; }

static void lifetime(void)
{
    char got[16];
    int arg = -1, i;
    const AtRoomView *v;
    gw_Ui_RoomBegin("lobby");
    CHECK(st_attached == 1);
    CHECK(gw_Ui_RoomSetStr("code", "WXYZ") == 1 && gw_Ui_RoomSetInt("host", 1) == 1);
    CHECK(gw_Ui_RoomSetInt("no_such_key", 1) == 0 && gw_Ui_RoomSetStr("no_such_key", "x") == 0);   /* unknown: refused, no effect */
    v = gw_Ui_RoomDebugView();
    CHECK(strcmp(v->code, "WXYZ") == 0 && v->host == 1);
    gw_Ui_RoomBegin("lobby");                                              /* the same kind again: nothing restarts */
    CHECK(st_attached == 1 && strcmp(gw_Ui_RoomDebugView()->code, "WXYZ") == 0);
    gw_Ui_RoomBegin("wait");                                               /* another kind: a fresh view */
    CHECK(st_attached == 1 && gw_Ui_RoomDebugView()->code[0] == '\0' && gw_Ui_RoomDebugView()->kind == AT_ROOM_WAIT);   /* the door keeps its slot */
    gw_Ui_RoomSetStr("code", "ABCD");
    gw_Ui_RoomEnd();                                                       /* the screen is left */
    CHECK(st_detached >= 1 && gw_Ui_RoomDebugView()->kind == 0 && gw_Ui_RoomDebugView()->code[0] == '\0');
    CHECK(gw_Ui_RoomSetInt("host", 1) == 0 && gw_Ui_RoomSetStr("code", "ZZZZ") == 0);   /* after End nothing is accepted */
    gw_Ui_RoomFrame();                                                     /* and a frame with no room is harmless */
    CHECK(gw_Ui_RoomPollName(got, sizeof got, &arg) == 0);
    gw_Ui_RoomEnd();                                                       /* End twice is harmless */
    gw_Ui_RoomBegin("lobby");
    CHECK(gw_Ui_RoomDebugView()->code[0] == '\0');                         /* nothing of the last room survives */
    gw_Ui_RoomEnd();
    for (i = 0; i < 2; i++) { st_enabled = 0; gw_Ui_RoomBegin("lobby"); CHECK(gw_Ui_RoomOn() == 0 && gw_Ui_RoomDebugView()->kind == 0); st_enabled = 1; }
    CHECK(gw_Ui_RoomOn() == 1);
    gw_Ui_RoomBegin("nonsense");                                           /* an unknown kind attaches nothing */
    CHECK(gw_Ui_RoomDebugView()->kind == 0);
}

static void copies(void)
{
    char buf[400], name[8];
    int i;
    gw_Ui_RoomBegin("wait");
    snprintf(name, sizeof name, "%s", "ABCD"); gw_Ui_RoomSetStr("code", name); name[0] = 'Z';
    CHECK(strcmp(gw_Ui_RoomDebugView()->code, "ABCD") == 0);               /* a copy, not a pointer into the game's buffer */
    for (i = 0; i < 399; i++) buf[i] = 'x';
    buf[399] = '\0';
    gw_Ui_RoomSetStr("status", buf);
    CHECK(strlen(gw_Ui_RoomDebugView()->status) == AT_ROOM_TEXT - 1);      /* cut to the field, still terminated */
    gw_Ui_RoomSetStr("status", NULL);
    CHECK(gw_Ui_RoomDebugView()->status[0] == '\0');                       /* NULL is empty */
    gw_Ui_RoomSetStr("phase", "strike");
    CHECK(gw_Ui_RoomDebugView()->phase == AT_PH_STRIKE);
    gw_Ui_RoomSetStr("phase", "nonsense");
    CHECK(gw_Ui_RoomDebugView()->phase == AT_PH_OFF);
    gw_Ui_RoomPlayerName(1, "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW", "Locked in");
    CHECK(strlen(gw_Ui_RoomDebugView()->pl[1].name) == AT_ROOM_NAME - 1 && strcmp(gw_Ui_RoomDebugView()->pl[1].fighter, "Locked in") == 0);
    gw_Ui_RoomPlayerName(5, "x", "y"); gw_Ui_RoomPlayer(-1, 1, 1, 1, 1);   /* out of range: ignored */
    gw_Ui_RoomEnd();
}

static void ping(void)
{
    int k, changes = 0, last = -1;
    gw_Ui_RoomBegin("wait");
    gw_Ui_RoomSetInt("ping", 20);
    CHECK(gw_Ui_RoomDebugView()->link_bars == 4 && gw_Ui_RoomDebugView()->ping_ms == 20);
    for (k = 0; k < 100; k++) {
        gw_Ui_RoomSetInt("ping", 90 + (k & 1 ? 3 : -3));                   /* hovering on a line */
        if (last >= 0 && gw_Ui_RoomDebugView()->link_bars != last) changes++;
        last = gw_Ui_RoomDebugView()->link_bars;
    }
    CHECK(changes <= 1);
    gw_Ui_RoomSetInt("ping", -1);
    CHECK(gw_Ui_RoomDebugView()->link_bars == 0 && gw_Ui_RoomDebugView()->ping_ms == -1);
    gw_Ui_RoomEnd();
}

static void grid(void)
{
    int i, col, row, page, pages, cols;
    AtGrid g;
    int group[AT_ROOM_STAGES];
    gw_Ui_RoomBegin("lobby");
    gw_Ui_RoomStageCount(40);
    CHECK(gw_Ui_RoomDebugView()->n_stages == AT_ROOM_STAGES);              /* cut at the list cap */
    gw_Ui_RoomStage(31, "Last", "banned", 0, 1); gw_Ui_RoomStage(32, "Past the end", "free", 0, 1);   /* the second is ignored */
    CHECK(strcmp(gw_Ui_RoomDebugView()->st[31].name, "Last") == 0 && gw_Ui_RoomDebugView()->st[31].state == AT_STAGE_BANNED);
    st_w = 640.0f;
    pages = gw_Ui_RoomGridFor(32, 5);
    cols = at_room_pick_cols(32, 1, 0);
    for (i = 0; i < 32; i++) group[i] = i >= 5;
    at_room_grid(group, 32, cols, 3, &g);
    CHECK(pages == g.pages);
    for (i = 0; i < 32; i++) {
        CHECK(gw_Ui_RoomGridCell(i, &col, &row, &page) == 1 && col == g.cell[i].col && row == g.cell[i].row && page == g.cell[i].page);
    }
    CHECK(gw_Ui_RoomGridCell(-1, &col, &row, &page) == 0 && gw_Ui_RoomGridCell(32, &col, &row, &page) == 0);
    st_w = 1140.0f;                                                        /* wide: six columns, so fewer pages */
    CHECK(gw_Ui_RoomGridFor(32, 5) <= pages && gw_Ui_RoomDebugView()->grid.cols == 6);
    st_w = 640.0f;
    gw_Ui_RoomEnd();
}

static void intents(void)
{
    char name[16];
    int arg = -9, i, n;
    AtSink s;
    gw_Ui_RoomBegin("lobby");
    gw_Ui_RoomSetInt("my_stage_turn", 1); gw_Ui_RoomSetStr("phase", "strike"); gw_Ui_RoomSetInt("me", 1);
    gw_Ui_RoomStageCount(6);
    for (i = 0; i < 6; i++) gw_Ui_RoomStage(i, "Stage", "free", 1, 1);
    gw_Ui_RoomGridFor(6, 6);
    gw_Ui_RoomSetInt("cursor", 1);
    gw_Ui_RoomFrame();
    s = rec_sink();                                                        /* the door's job, done here: draw to learn the hit rectangles */
    at_render_ex(gw_Ui_RoomDebugScreen(), gw_Ui_RoomDebugView_vw(), 640.0f, st_now, 0, &FAKE, &s, gw_Ui_RoomDebugHits(), NULL);
    CHECK(gw_Ui_RoomDebugHits()->n > 0 && gw_Ui_RoomDebugScreen()->primary == AT_PRIMARY_ROOM && gw_Ui_RoomDebugView_vw()->room == gw_Ui_RoomDebugView());
    st_km = AT_KEY_RIGHT; gw_Ui_RoomFrame(); st_km = 0;
    CHECK(gw_Ui_RoomPollName(name, sizeof name, &arg) == 1 && strcmp(name, "right") == 0);
    CHECK(gw_Ui_RoomPollName(name, sizeof name, &arg) == 0);
    /* a click on a tile: stage_at then accept, in order; the pointer arrives first (a first sample never clicks) */
    {
        const AtHit *t = NULL; AtHits *h = gw_Ui_RoomDebugHits();
        for (i = 0; i < h->n; i++) if (h->h[i].kind == AT_HIT_ROOM && h->h[i].a == AT_RH_STAGE && h->h[i].b == 3) t = &h->h[i];
        CHECK(t != NULL);
        st_mx = t->r.x + 4.0f; st_my = t->r.y + 4.0f; st_mb = 0; gw_Ui_RoomFrame();
        CHECK(gw_Ui_RoomPollName(name, sizeof name, &arg) == 0);           /* first sample: nothing */
        st_mb = 1; gw_Ui_RoomFrame(); st_mb = 0;
        CHECK(gw_Ui_RoomPollName(name, sizeof name, &arg) == 1 && strcmp(name, "stage_at") == 0 && arg == 3);
        CHECK(gw_Ui_RoomPollName(name, sizeof name, &arg) == 1 && strcmp(name, "accept") == 0);
        gw_Ui_RoomFrame();
    }
    /* the queue is bounded: a held-down storm of presses keeps 16 and drops the rest, never overruns */
    for (n = 0; n < 40; n++) { st_km = (n & 1) ? 0 : AT_KEY_ENTER; gw_Ui_RoomFrame(); }
    st_km = 0;
    for (n = 0; gw_Ui_RoomPollName(name, sizeof name, &arg); n++) CHECK(strcmp(name, "accept") == 0);
    CHECK(n == 16);
    st_mx = st_my = -1000.0f;
    gw_Ui_RoomEnd();
}

int main(void)
{
    lifetime();
    copies();
    ping();
    grid();
    intents();
    ATLAS_DONE("atlas room native");
}
```

(The debug accessors `gw_Ui_RoomDebugView`, `gw_Ui_RoomDebugView_vw` (the `AtView`), `gw_Ui_RoomDebugScreen` and `gw_Ui_RoomDebugHits` are part of the host file; they exist for tests and for the door's own use of the screen record.)

Register in `tools/port/native_test.sh` (append `, atlas-room-native` to the die message):

```bash
atlas-room-native)
    sources=(pc/tests/atlas_room_native_test.c pc/platform/gw_ui_room_native.c pc/platform/gw_ui_room.c pc/platform/gw_ui_online_parts.c pc/platform/gw_ui_render.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c) ;;
```

- [ ] **Step 2: Run to verify it fails.** `nt atlas-room-native`. Expected: `fatal error: '../platform/gw_ui_room_native.h' file not found`.
- [ ] **Step 3: Write the host door.** Create `pc/platform/gw_ui_room_native.h`:

```c
/* gw_ui_room_native.h - the shims the game side uses to fill, draw and poll the online room screens. Scalars and
 * strings only, all by name; no netplay header. The game side declares these without the gw_ prefix. */
#ifndef GW_UI_ROOM_NATIVE_H
#define GW_UI_ROOM_NATIVE_H
#include "gw_ui_room.h"
#ifdef __cplusplus
extern "C" {
#endif
int gw_Ui_RoomOn(void);
void gw_Ui_RoomBegin(const char *kind);
void gw_Ui_RoomEnd(void);
int gw_Ui_RoomSetInt(const char *key, int v);
int gw_Ui_RoomSetStr(const char *key, const char *s);
void gw_Ui_RoomPlayer(int who, int present, int locked, int ready, int score);
void gw_Ui_RoomPlayerName(int who, const char *name, const char *fighter);
void gw_Ui_RoomStageCount(int n);
void gw_Ui_RoomStage(int i, const char *name, const char *state, int starter, int open);
int gw_Ui_RoomGridFor(int n, int starters);
int gw_Ui_RoomGridCell(int i, int *col, int *row, int *page);
void gw_Ui_RoomFrame(void);
int gw_Ui_RoomPollName(char *out, int cap, int *arg);
/* for tests and for the door */
const AtRoomView *gw_Ui_RoomDebugView(void);
AtView *gw_Ui_RoomDebugView_vw(void);
const AtScreen *gw_Ui_RoomDebugScreen(void);
AtHits *gw_Ui_RoomDebugHits(void);
/* RECONCILE (step 2): the door this file leans on */
extern void gw_ui_native_attach(const AtScreen *sc, AtView *vw, AtHits *hits);
extern void gw_ui_native_detach(const AtView *vw);
extern float gw_ui_native_canvas_w(void);
extern double gw_ui_native_now_ms(void);
extern void gw_ui_native_input(float *x, float *y, int *buttons, int *wheel, unsigned *key_mask);
extern int gw_ui_native_enabled(void);
#ifdef __cplusplus
}
#endif
#endif
```

Create `pc/platform/gw_ui_room_native.c`:

```c
#include "gw_ui_room_native.h"
#include <stddef.h>
#include <stdio.h>
#include <string.h>

static AtRoomView g_rv;
static AtScreen g_sc;
static AtView g_vw;
static AtHits g_hits;
static AtMouse g_mouse;
static AtKeys g_keys;
static AtRoomIntent g_q[16];
static int g_qn, g_on;

typedef struct { const char *key; size_t off; } IntKey;
typedef struct { const char *key; size_t off, size; } StrKey;
#define IK(k, f) { k, offsetof(AtRoomView, f) }
#define SK(k, f) { k, offsetof(AtRoomView, f), sizeof(((AtRoomView *) 0)->f) }
static const IntKey INTS[] = {
    IK("host", host), IK("random", random_search), IK("random_secs", random_secs), IK("found", found), IK("rules_known", rules_known),
    IK("turbo", turbo), IK("envoy", envoy), IK("stage_all", stage_all), IK("stocks", stocks), IK("minutes", minutes), IK("delay", delay),
    IK("copied", copied), IK("me", me), IK("game", game), IK("turn", turn), IK("left", left), IK("first", first), IK("countdown", countdown_s),
    IK("coin", coin_on), IK("reward_open", reward_open), IK("reward_left", reward_left_s), IK("reconnecting", reconnecting),
    IK("leave_armed", leave_armed), IK("my_stage_turn", my_stage_turn), IK("can_pick", can_pick), IK("can_ready", can_ready),
    IK("ready_mine", ready_mine), IK("cursor", cursor), IK("code_invalid", code_in.invalid), IK("code_slot", code_in.slot),
    IK("code_msg_bad", code_msg_bad), IK("toast_bad", toast_bad),
};
static const StrKey STRS[] = {
    SK("code", code), SK("status", status), SK("phase_title", phase_title), SK("instruction", instruction), SK("code_msg", code_msg), SK("toast", toast),
};

int gw_Ui_RoomOn(void) { return gw_ui_native_enabled() != 0; }

static int kind_of(const char *k)
{
    if (k == NULL) return 0;
    return strcmp(k, "code") == 0 ? AT_ROOM_CODE : strcmp(k, "wait") == 0 ? AT_ROOM_WAIT : strcmp(k, "lobby") == 0 ? AT_ROOM_LOBBY : 0;
}

void gw_Ui_RoomBegin(const char *kind)
{
    int k = kind_of(kind);
    if (!gw_Ui_RoomOn() || k == 0) return;
    if (g_on && g_rv.kind == k) return;
    memset(&g_rv, 0, sizeof g_rv);
    g_rv.kind = k;
    g_rv.ping_ms = -1;
    at_view_init(&g_vw);
    g_vw.opened_ms = gw_ui_native_now_ms();                    /* a new screen fades in */
    memset(&g_mouse, 0, sizeof g_mouse);
    memset(&g_keys, 0, sizeof g_keys);
    g_qn = 0;
    if (!g_on) gw_ui_native_attach(&g_sc, &g_vw, &g_hits);
    g_on = 1;
    at_room_fill(&g_rv, &g_sc, &g_vw, gw_ui_native_now_ms());
}

void gw_Ui_RoomEnd(void)
{
    if (g_on) gw_ui_native_detach(&g_vw);
    g_on = 0;
    g_vw.room = NULL;                                          /* the view the door might still hold points nowhere */
    memset(&g_rv, 0, sizeof g_rv);
    memset(&g_hits, 0, sizeof g_hits);
    g_qn = 0;
}

int gw_Ui_RoomSetInt(const char *key, int v)
{
    size_t i;
    if (!g_on || key == NULL) return 0;
    if (strcmp(key, "ping") == 0) { g_rv.link_bars = at_link_bars(v, g_rv.link_bars); g_rv.ping_ms = v; return 1; }
    for (i = 0; i < sizeof INTS / sizeof INTS[0]; i++)
        if (strcmp(INTS[i].key, key) == 0) { *(int *) ((char *) &g_rv + INTS[i].off) = v; return 1; }
    return 0;
}

int gw_Ui_RoomSetStr(const char *key, const char *s)
{
    size_t i;
    if (!g_on || key == NULL) return 0;
    if (s == NULL) s = "";
    if (strcmp(key, "phase") == 0) {
        static const char *const names[] = { "off", "char_blind", "strike", "ban", "pick", "char_winner", "char_loser", "ready", "go" };
        int p;
        g_rv.phase = AT_PH_OFF;
        for (p = 0; p < 9; p++) if (strcmp(s, names[p]) == 0) g_rv.phase = p;
        return 1;
    }
    for (i = 0; i < sizeof STRS / sizeof STRS[0]; i++)
        if (strcmp(STRS[i].key, key) == 0) { snprintf((char *) &g_rv + STRS[i].off, STRS[i].size, "%s", s); return 1; }
    return 0;
}

void gw_Ui_RoomPlayer(int who, int present, int locked, int ready, int score)
{
    if (!g_on || who < 0 || who > 1) return;
    g_rv.pl[who].present = present != 0; g_rv.pl[who].locked = locked != 0; g_rv.pl[who].ready = ready != 0; g_rv.pl[who].score = score;
}

void gw_Ui_RoomPlayerName(int who, const char *name, const char *fighter)
{
    if (!g_on || who < 0 || who > 1) return;
    snprintf(g_rv.pl[who].name, sizeof g_rv.pl[who].name, "%s", name != NULL ? name : "");
    snprintf(g_rv.pl[who].fighter, sizeof g_rv.pl[who].fighter, "%s", fighter != NULL ? fighter : "");
}

void gw_Ui_RoomStageCount(int n)
{
    if (!g_on) return;
    g_rv.n_stages = n < 0 ? 0 : n > AT_ROOM_STAGES ? AT_ROOM_STAGES : n;
}

void gw_Ui_RoomStage(int i, const char *name, const char *state, int starter, int open)
{
    static const char *const names[] = { "free", "p1", "p2", "banned", "picked" };
    int s;
    AtRoomStage *st;
    if (!g_on || i < 0 || i >= g_rv.n_stages) return;
    st = &g_rv.st[i];
    snprintf(st->name, sizeof st->name, "%s", name != NULL ? name : "");
    st->state = AT_STAGE_FREE;
    for (s = 0; s < 5; s++) if (state != NULL && strcmp(state, names[s]) == 0) st->state = s;
    st->starter = starter != 0; st->open = open != 0;
}

int gw_Ui_RoomGridFor(int n, int starters)
{
    int group[AT_ROOM_STAGES], i, wide = gw_ui_native_canvas_w() >= 760.0f;
    if (n < 0) n = 0;
    if (n > AT_ROOM_STAGES) n = AT_ROOM_STAGES;
    for (i = 0; i < n; i++) group[i] = i >= starters;
    at_room_grid(group, n, at_room_pick_cols(n, starters > 0 && starters < n, wide), 3, &g_rv.grid);
    return g_rv.grid.pages;
}

int gw_Ui_RoomGridCell(int i, int *col, int *row, int *page)
{
    if (!g_on || i < 0 || i >= g_rv.grid.n) return 0;
    *col = g_rv.grid.cell[i].col; *row = g_rv.grid.cell[i].row; *page = g_rv.grid.cell[i].page;
    return 1;
}

static void queue(const AtRoomIntent *in, int n)
{
    int i;
    for (i = 0; i < n; i++) if (g_qn < 16) g_q[g_qn++] = in[i];         /* full: the newest are dropped */
}

void gw_Ui_RoomFrame(void)
{
    float mx, my;
    int mb, wheel, n;
    unsigned km;
    AtRoomIntent in[16];
    if (!g_on) return;
    gw_ui_native_input(&mx, &my, &mb, &wheel, &km);
    n = at_room_key_intents(&g_keys, km, gw_ui_native_now_ms(), in, 16);
    queue(in, n);
    n = at_room_mouse_intents(&g_rv, &g_mouse, mx, my, mb, wheel, &g_hits, in, 16);
    queue(in, n);
    at_room_fill(&g_rv, &g_sc, &g_vw, gw_ui_native_now_ms());
}

int gw_Ui_RoomPollName(char *out, int cap, int *arg)
{
    int i;
    if (!g_on || g_qn == 0 || cap < 2) return 0;
    snprintf(out, (size_t) cap, "%s", at_room_intent_name(g_q[0].kind));
    *arg = g_q[0].arg;
    for (i = 1; i < g_qn; i++) g_q[i - 1] = g_q[i];
    g_qn--;
    return 1;
}

const AtRoomView *gw_Ui_RoomDebugView(void) { return &g_rv; }
AtView *gw_Ui_RoomDebugView_vw(void) { return &g_vw; }
const AtScreen *gw_Ui_RoomDebugScreen(void) { return &g_sc; }
AtHits *gw_Ui_RoomDebugHits(void) { return &g_hits; }
```

Two details the test pins that are easy to get wrong: `gw_Ui_RoomBegin` for an unknown kind attaches nothing (so a typo cannot leave a half-built screen on the stack), and `gw_Ui_RoomEnd` clears `g_vw.room` **before** the door can draw again (the stale-view hole).
- [ ] **Step 4: Run.** `nt atlas-room-native`. Expected: `0 failed`. If the grid check `<= pages` fails at 1140 wide, the pick-cols rule is not widening (see `at_room_pick_cols`). If the queue check is not exactly 16, the key repeat is eating presses: the test alternates ENTER with 0 so each press is an edge.
- [ ] **Step 5: Write the game-side adapter.** Create `src/melee/gm/gmfrontend_atlas_online.inc`:

```c
/* gmfrontend_atlas_online.inc - included by gmfrontend.c (TARGET_PC only) after gmfrontend_online.inc.
 *
 * The Atlas drawing of the online room screens (docs/superpowers/plans/2026-10-06-atlas-step6-online-room.md). DRAWING ONLY.
 * Every rule about what a screen shows or accepts is still a gmfrontend_online.inc predicate (fl_phase, fl_my_stage_turn,
 * fl_can_pick_char, fl_reconnecting, fl_card_portrait, fl_stage_open, fl_instruction, fl_phase_title): this file asks them and
 * copies the answers into the host's room view by name. It READS netplay state (Netplay_* calls below are the read-only set that
 * tools/port/check_atlas_online.sh allows); every write stays in gmfrontend_online.inc. Pad input is not touched: fl_frame ORs the
 * retail pad read with fa_room_bits() where it used to OR fms_menu_bits(), and fa_room_bits() turns the mouse and keyboard
 * intents into the same MenuInput_ bits a pad press has. */

extern int Ui_RoomOn(void);
extern void Ui_RoomBegin(const char* kind);
extern void Ui_RoomEnd(void);
extern int Ui_RoomSetInt(const char* key, int v);
extern int Ui_RoomSetStr(const char* key, const char* s);
extern void Ui_RoomPlayer(int who, int present, int locked, int ready, int score);
extern void Ui_RoomPlayerName(int who, const char* name, const char* fighter);
extern void Ui_RoomStageCount(int n);
extern void Ui_RoomStage(int i, const char* name, const char* state, int starter, int open);
extern int Ui_RoomGridFor(int n, int starters);
extern int Ui_RoomGridCell(int i, int* col, int* row, int* page);
extern void Ui_RoomFrame(void);
extern int Ui_RoomPollName(char* out, int cap, int* arg);

static bool fa_room_on(void) { return Ui_RoomOn() != 0; }

static void fa_room_begin(int art)
{
    Ui_RoomBegin(art == FL_CODE ? "code" : art == FL_WAIT ? "wait" : "lobby");
}

static const char* fa_phase_name(int p)
{
    switch (p) {
    case LBP_CHAR_BLIND: return "char_blind";
    case LBP_STRIKE: return "strike";
    case LBP_BAN: return "ban";
    case LBP_PICK: return "pick";
    case LBP_CHAR_WINNER: return "char_winner";
    case LBP_CHAR_LOSER: return "char_loser";
    case LBP_READY: return "ready";
    case LBP_GO: return "go";
    default: return "off";
    }
}

static const char* fa_stage_state(int s)
{
    switch (s) {
    case LBS_P1: return "p1";
    case LBS_P2: return "p2";
    case LBS_BANNED: return "banned";
    case LBS_PICKED: return "picked";
    default: return "free";
    }
}

/* The grid model for the cursor code: the legacy cursor functions (fl_step_row, fl_step_open, fl_step_page) are unchanged and
 * read flg; under Atlas flg comes from the same function that draws the tiles. A tile is a 80 x 80 box on a 100 px pitch, so
 * "the nearest row that way" means the nearest row of the grid on screen. */
static void fa_room_grid(int n, int starters)
{
    int i, col, row, page;
    flg.kind = FL_GRID_FLOW;
    flg.pages = Ui_RoomGridFor(n, starters);
    flg.nhead = 0;
    for (i = 0; i < n; i++) {
        if (!Ui_RoomGridCell(i, &col, &row, &page)) {
            continue;
        }
        flg.page[i] = page;
        flg.r[i][0] = (float) (col * 100);
        flg.r[i][1] = (float) (row * 100);
        flg.r[i][2] = flg.r[i][0] + 80.0F;
        flg.r[i][3] = flg.r[i][1] + 80.0F;
    }
}

/* What a card may say about a fighter. The legacy card decided with fl_card_portrait; so does this. The opponent's blind pick
 * is never read here until it is "shown" (check_atlas_online.sh guard 7). */
static void fa_room_fighter(int w, char* out, int cap)
{
    const char* pt = fl_card_portrait(w);
    if (strcmp(pt, "shown") != 0) {
        sprintf(out, "%s", strcmp(pt, "hidden") == 0 ? "Locked in" : "Choosing...");
        return;
    }
    Netplay_FighterName(fl_ck(w), out, cap);
}

static void fa_room_players(bool lobby)
{
    char nm[FE_STR], fi[FE_STR];
    int w, me = Netplay_LobbyMe(), found = fe_np_phase == FE_NP_LOBBY || fe_np_phase == FE_NP_CONNECTED;
    for (w = 0; w < 2; w++) {
        Netplay_PlayerName(w, nm, 18);
        fi[0] = '\0';
        if (lobby) {
            fa_room_fighter(w, fi, 24);
        }
        Ui_RoomPlayerName(w, nm, fi);
        Ui_RoomPlayer(w, w == me || found, Netplay_LobbyPlayer(w, 2) != 0, Netplay_LobbyPlayer(w, 3) != 0, Netplay_LobbyInfo(2 + w));
    }
}

static void fa_room_common(void)
{
    char b[FE_STR];
    const char* t = fl_toast_now();
    Netplay_RoomCode(b, sizeof b);
    Ui_RoomSetStr("code", b);
    Ui_RoomSetInt("host", Netplay_IsHost() != 0);
    Ui_RoomSetInt("me", Netplay_LobbyMe());
    Ui_RoomSetInt("ping", Netplay_Ping());
    Netplay_MenuStatus(b, FE_STR);
    Ui_RoomSetStr("status", b);
    Ui_RoomSetInt("turbo", Netplay_IsHost() && fe_np_phase != FE_NP_LOBBY ? Netplay_TurboPref() != 0 : Netplay_Turbo() != 0);
    Ui_RoomSetInt("envoy", Netplay_IsHost() && fe_np_phase != FE_NP_LOBBY ? Netplay_EnvoyPref() != 0 : Netplay_Envoy() != 0);
    Ui_RoomSetInt("stage_all", Netplay_StageMode() != 0);
    Ui_RoomSetInt("stocks", fe_np_stocks);
    Ui_RoomSetInt("minutes", fe_np_minutes);
    Ui_RoomSetInt("delay", fe_np_delay);
    Ui_RoomSetInt("rules_known", Netplay_IsHost() != 0); /* a guest sees the rules in the lobby, not before */
    Ui_RoomSetStr("toast", t != NULL ? t : "");
    Ui_RoomSetInt("toast_bad", fl.toast_bad);
    Ui_RoomSetInt("reconnecting", fl_reconnecting());
}

static void fa_room_submit(void)
{
    char b[FE_STR];
    int i, n, s = 0;
    fa_room_begin(fl.art);
    fa_room_common();
    if (fl.art == FL_CODE) {
        for (i = 0; i < 4; i++) {
            b[i] = (char) Netplay_CodeChar(i);
        }
        b[4] = '\0';
        Ui_RoomSetStr("code_chars", b);
        Ui_RoomSetInt("code_slot", Netplay_CodeSlot());
        Ui_RoomSetInt("code_invalid", fl.invalid);
        Ui_RoomSetStr("code_msg", fl.code_msg);
        Ui_RoomSetInt("code_msg_bad", fl.code_msg_bad);
    } else if (fl.art == FL_WAIT) {
        fa_room_players(false);
        Ui_RoomSetInt("random", Netplay_RandomStatus() == 1);
        Ui_RoomSetInt("random_secs", Netplay_RandomSeconds());
        Ui_RoomSetInt("copied", fl.frames < fl.copied_until);
        Ui_RoomSetInt("found", fe_np_phase == FE_NP_LOBBY);
    } else if (fl.art == FL_LOBBY) {
        int p = fl_phase(), me = Netplay_LobbyMe();
        fa_room_players(true);
        fl_grid_layout(); /* under Atlas: the host's grid model; also sets flg.n and flg.starters */
        n = flg.n;
        s = flg.starters;
        Ui_RoomSetStr("phase", fa_phase_name(p));
        Ui_RoomSetStr("phase_title", fl_phase_title());
        fl_instruction(b);
        Ui_RoomSetStr("instruction", b);
        Ui_RoomSetInt("game", Netplay_LobbyInfo(0));
        Ui_RoomSetInt("turn", Netplay_LobbyInfo(4));
        Ui_RoomSetInt("left", Netplay_LobbyInfo(5));
        Ui_RoomSetInt("first", Netplay_LobbyInfo(6));
        Ui_RoomSetInt("countdown", Netplay_LobbyInfo(8));
        Ui_RoomSetInt("coin", fl.frames < fl.coin_until);
        Ui_RoomSetInt("reward_open", Netplay_LobbyInfo(13) != 0);
        Ui_RoomSetInt("reward_left", (Netplay_LobbyInfo(14) + 59) / 60);
        Ui_RoomSetInt("leave_armed", fl.frames < fl.leave_until);
        Ui_RoomSetInt("my_stage_turn", fl_my_stage_turn());
        Ui_RoomSetInt("can_pick", fl_can_pick_char());
        Ui_RoomSetInt("can_ready", p == LBP_READY);
        Ui_RoomSetInt("ready_mine", Netplay_LobbyPlayer(me, 3) != 0);
        Ui_RoomSetInt("cursor", fl.cur);
        Ui_RoomStageCount(n);
        for (i = 0; i < n && i < LB_MAX_UI_STAGES; i++) {
            Ui_RoomStage(i, fl_stage_name(i), fa_stage_state(Netplay_LobbyStage(i)), Netplay_LobbyStageGroup(i) == 0, fl_stage_open(i));
        }
        Ui_RoomGridFor(n, s);
    }
    Ui_RoomFrame();
}

/* Mouse and keyboard intents become the bits a pad press has, or a local cursor move the legacy mouse code already made. The
 * pad itself never comes through here. One line per intent, so check_atlas_online.sh can read the table. */
static u32 fa_room_bits(void)
{
    char n[16];
    int arg;
    u32 bits = 0;
    while (Ui_RoomPollName(n, sizeof n, &arg)) {
        if (strcmp(n, "up") == 0) bits |= MenuInput_Up;
        else if (strcmp(n, "down") == 0) bits |= MenuInput_Down;
        else if (strcmp(n, "left") == 0) bits |= MenuInput_Left;
        else if (strcmp(n, "right") == 0) bits |= MenuInput_Right;
        else if (strcmp(n, "accept") == 0) bits |= MenuInput_Confirm;
        else if (strcmp(n, "back") == 0) bits |= MenuInput_Back;
        else if (strcmp(n, "start") == 0) bits |= MenuInput_StartButton;
        else if (strcmp(n, "copy") == 0) bits |= MenuInput_XButton;
        else if (strcmp(n, "paste") == 0) bits |= MenuInput_YButton;
        else if (strcmp(n, "page_l") == 0) bits |= MenuInput_LTrigger;
        else if (strcmp(n, "page_r") == 0) bits |= MenuInput_RTrigger;
        else if (strcmp(n, "stage_at") == 0) {
            if (fl.art == FL_LOBBY && fl_my_stage_turn() && arg >= 0 && arg < Netplay_LobbyInfo(9)) {
                fl.cur = arg; /* the legacy mouse set the cursor the same way, then confirmed */
            }
        } else if (strcmp(n, "code_slot") == 0) {
            if (fl.art == FL_CODE) {
                fa_code_slot_req = arg; /* acted on in fl_frame_code, where the legacy arrows move the slot: the adapter writes nothing */
            }
        }
    }
    return bits;
}
```

(`fl.toast_bad`, `fl.invalid`, `fl.code_msg`, `fl.copied_until`, `fl.coin_until`, `fl.leave_until`, `fl.cur` exist in the legacy state struct. `fa_code_slot_req` is declared in `gmfrontend_online.inc` (Task 8 step 1): the request is consumed by the same function that moves the slot for an arrow key, so every `Netplay_CodeMove` call stays in the file the guard allows to write.)
- [ ] **Step 6: Syntax-check the adapter with the retargeted rules.** The adapter is only compiled through `gmfrontend.c` (Task 8 includes it). Run the baseline first so a pre-existing diagnostic is not blamed on you:

```bash
cd "$GW_MELEE" && clang -fsyntax-only -w -DTARGET_PC --target=powerpc-unknown-eabi -nostdinc -Isrc -Isrc/melee -Iinclude -Ilibs/dolphin/include -Ipc -Ipc/gameworld -Isrc/sysdolphin -Isrc/MSL src/melee/gm/gmfrontend.c; echo "exit $?"
```

Record the result. The adapter is not included yet, so this only measures the baseline: if it is not `exit 0`, copy the first diagnostics into your notes so Task 8 is not blamed for them. The real check is Task 8, Step 5.
- [ ] **Step 7: Commit.** Game repo: the four new files, message `atlas online: the host door (shims, queue, grid) and the game-side adapter`. Workspace repo: `tools/port/native_test.sh`, message `tools: atlas-room-native native test`.

---

### Task 8: Wire the three room screens and the ONLINE PLAY rows

**Gate:** Task 0 exits 0 and Task 7 is merged.

Each edit below is small and says what the legacy line was; the legacy behaviour under `MELEE_ATLAS=0` (so `fa_room_on()` false) is identical to today's.

**Files:**
- Modify (game repo): `src/melee/gm/gmfrontend_online.inc`, `src/melee/gm/gmfrontend.c`
- Create (workspace repo): `tools/port/check_atlas_online_text.py`, `tools/port/test_check_atlas_online_text.py`

- [ ] **Step 1: Forward declarations and the include.** In `gmfrontend_online.inc`, after the existing forward declarations (the block ending `static void fs_drop_borrowed(void);`), add:

```c
/* the Atlas drawing of these screens (gmfrontend_atlas_online.inc, included after this file) */
static bool fa_room_on(void);
static void fa_room_begin(int art);
static void fa_room_submit(void);
static u32 fa_room_bits(void);
static void fa_room_grid(int n, int starters);
extern void Ui_RoomEnd(void); /* fl_open and fl_exit call it before the adapter's own externs are seen */
static int fa_code_slot_req = -1; /* a mouse click on a code slot, for fl_frame_code to act on */
```

In `fl_frame_code`, directly after the `before[4] = Netplay_CodeSlot();` line, add:

```c
    if (fa_code_slot_req >= 0) { /* Atlas: a click on a slot moves there, one step at a time, as the arrows do */
        int d = fa_code_slot_req - Netplay_CodeSlot();
        fa_code_slot_req = -1;
        while (d != 0 && Netplay_CodeMove(d > 0 ? 1 : -1)) {
            d += d > 0 ? -1 : 1;
        }
    }
```

In `gmfrontend.c`, where `gmfrontend_online.inc` is included, add on the next line `#include "gmfrontend_atlas_online.inc"`. (The adapter uses `flg`, `fl_*` and `fe_np_*`, so it must come after `gmfrontend_online.inc`; the forward declarations let the online file call it first.)
- [ ] **Step 2: The grid.** In `fl_grid_layout`, directly after `flg.starters = s; c = n - s;`, add:

```c
    if (fa_room_on()) {
        fa_room_grid(n, s); /* Atlas: the host's grid model, so the cursor moves through the grid that is drawn */
        return;
    }
```

- [ ] **Step 3: Input and the per-frame submission.** In `fl_frame`, change the input line from `in = mn_80229624(4) | fms_menu_bits();` to:

```c
        in = mn_80229624(4) | (fa_room_on() ? fa_room_bits() : fms_menu_bits()); /* the pad: the retail read, as ever; the mouse (and Atlas keyboard): bits */
```

and, after the `if (fe.screen == NULL || fe.screen->art != fl.art || fe.leaving != 0) { return; }` block, before the signature block, add:

```c
    if (fa_room_on() && (fl.art == FL_CODE || fl.art == FL_WAIT || fl.art == FL_LOBBY)) {
        fa_room_submit(); /* Atlas: one view a frame, no model to rebuild */
        return;
    }
```

In `fl_frame_lobby`, wrap the two legacy mouse blocks so they do not also run (Atlas delivers the same actions as bits and as `fl.cur`): change `if (fms.click && !fms_over_footer() && !fl_my_stage_turn()) {` to `if (!fa_room_on() && fms.click && !fms_over_footer() && !fl_my_stage_turn()) {`, and wrap the block that begins `{ /* the mouse: pointing at an open stage moves there ...` with `if (!fa_room_on())`. (That is the deliberate narrowing of Task 6: a click on empty space no longer readies you.)
- [ ] **Step 4: Open, leave, and the leaving frames.** At the end of `fl_open(int art)` add:

```c
    if (art == FL_CODE || art == FL_WAIT || art == FL_LOBBY) {
        if (fa_room_on()) {
            fa_room_begin(art);
        }
    } else {
        Ui_RoomEnd(); /* the loading screen, the character and stage select, and leaving: no Atlas room is attached */
    }
```

and at the top of `fl_exit` add `Ui_RoomEnd();`. In `gmfrontend.c`, in the leaving branch of the frame function (`if (fe.screen->art != 0) { fp.frame++; fp_evaluate(fp.frame); return; }`), guard the model with the new state: `if (fe.screen->art != 0) { if (!fa_room_on()) { fp.frame++; fp_evaluate(fp.frame); } return; }` (under Atlas no frontend model was built, so there is nothing to evaluate). **The fade-out:** the legacy fade is drawn by the game under the host's quads, so on leaving the Atlas screen would stay fully visible until the scene changes. Hand the fade to the door (RECONCILE, N2): while `fe.leaving`, call the door's fade with `(float) fe.fade / FE_FADE_FRAMES` from `fa_room_submit` (add one `Ui_RoomSetInt("fade_out", ...)` line and the door's matching handling; if step 2's door already fades native screens on scene exit, this line is not needed).
- [ ] **Step 5: Syntax-check and guard.**

```bash
cd "$GW_MELEE" && clang -fsyntax-only -w -DTARGET_PC --target=powerpc-unknown-eabi -nostdinc -Isrc -Isrc/melee -Iinclude -Ilibs/dolphin/include -Ipc -Ipc/gameworld -Isrc/sysdolphin -Isrc/MSL src/melee/gm/gmfrontend.c; echo "exit $?"
bash "$WS/tools/port/check_atlas_online.sh" "$GW_MELEE"
```

Expected: `exit 0`, then `check_atlas_online: ok` (all seven guards now run, because the adapter exists). A syntax error naming an `fl_*` or `fe_np_*` identifier means the include came before its definition. Prove guard 7 can fail: temporarily move the `Netplay_FighterName` line above the `fl_card_portrait` line in `fa_room_fighter`, rerun (expected: `FAIL: fa_room_fighter reads the fighter before asking fl_card_portrait`), put it back.
- [ ] **Step 6: The ONLINE PLAY rows.** `fe_screen_online` is a `FrontendItem` table, so step 5's adapter draws it once the screen carries step 2's Atlas flag (RECONCILE: set whatever field step 2 added to `FrontendScreen`, as the `SETTINGS > ONLINE` page did in step 5). Two things are this step's: (a) every row's help string becomes the explainer's WHAT, which wraps at the preset width, so the strings must be short enough; (b) the bad-notice path (`fe_ol_notice(text, true)`) shows as a corner note in `err` colour (and, when the text is longer than 60 characters, as a dialog titled by its cause) through step 2's note shim (RECONCILE: its name; one line in `fe_ol_notice`).

First the lint, test-first. Create `tools/port/test_check_atlas_online_text.py`:

```python
"""python tools/port/test_check_atlas_online_text.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_atlas_online_text as C  # noqa: E402

TABLE = '''static const FrontendItem fe_items_online[] = {
    { FE_ACTION, FE_DO_CALL, "Host a Room", "Open a room and get a code.", NULL, NULL },
    { FE_CHOICE, 0, "A Label That Is Far Too Long", "Short.", fe_get, fe_set },
    { FE_CHOICE, 0, "Envoy", "Rooms you host: a best-of set where each player fights with an Envoy build and picks a reward between games.", fe_get, fe_set },
};
'''


class Lint(unittest.TestCase):
    def test_pairs(self):
        self.assertEqual([p[0] for p in C.pairs(TABLE)], ["Host a Room", "A Label That Is Far Too Long", "Envoy"])

    def test_findings(self):
        f = C.lint(C.pairs(TABLE))
        self.assertEqual(len(f), 2)
        self.assertIn("A Label That Is Far Too Long", f[0])     # the label is over 18 characters
        self.assertIn("Envoy", f[1])                              # the help wraps to more than 3 lines at 33 characters

    def test_wrap(self):
        self.assertEqual(C.wrap_lines("one two three"), 1)
        self.assertEqual(C.wrap_lines("x" * 40), 2)               # a word longer than a line is broken, never squashed

    def test_the_real_table_is_clean(self):
        path = os.environ.get("GW_MELEE_GM", "")
        if path and os.path.exists(path):
            self.assertEqual(C.lint(C.pairs(C.table_text(open(path, encoding="utf-8").read()))), [])


if __name__ == "__main__":
    unittest.main()
```

Create `tools/port/check_atlas_online_text.py`:

```python
"""Lint the ONLINE PLAY rows' strings against what the Atlas explainer and row can show.

    python tools/port/check_atlas_online_text.py [path to gmfrontend.c]

A label must fit a list row beside a value widget (at most 18 characters). A help string is the explainer's WHAT: it must wrap
to at most 3 lines at 33 characters a line (the wide preset's 232 px at 7 px a character, the fake width the tests use; the real
font is a little narrower, so this is conservative). Step 1's explainer would clamp a longer one with an ellipsis, which is the
failure this catches before the owner sees it.
"""
import re
import sys

MAX_LABEL = 18
MAX_LINES = 3
LINE = 33


def table_text(src):
    a = src.index("static const FrontendItem fe_items_online[] = {")
    return src[a:src.index("};", a)]


def pairs(text):
    q = re.findall(r'"((?:[^"\\]|\\.)*)"', text)
    return [(q[i], q[i + 1]) for i in range(0, len(q) - 1, 2)]


def wrap_lines(s):
    lines, cur = 0, ""
    for word in s.split():
        while len(word) > LINE:
            if cur:
                lines, cur = lines + 1, ""
            lines, word = lines + 1, word[LINE:]
        if cur and len(cur) + 1 + len(word) > LINE:
            lines, cur = lines + 1, word
        else:
            cur = (cur + " " + word).strip()
    return lines + (1 if cur else 0)


def lint(ps):
    out = []
    for label, help_ in ps:
        if len(label) > MAX_LABEL:
            out.append('label "%s" is %d characters (at most %d)' % (label, len(label), MAX_LABEL))
        if wrap_lines(help_) > MAX_LINES:
            out.append('help of "%s" wraps to %d lines at %d characters (at most %d)' % (label, wrap_lines(help_), LINE, MAX_LINES))
    return out


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "melee/src/melee/gm/gmfrontend.c"
    findings = lint(pairs(table_text(open(path, encoding="utf-8").read())))
    for f in findings:
        print("FAIL:", f)
    print("check_atlas_online_text: %d finding(s)" % len(findings))
    sys.exit(1 if findings else 0)
```

Run `python tools/port/test_check_atlas_online_text.py` (expected: `OK`), then the real table:

```bash
cd "$WS" && python tools/port/check_atlas_online_text.py "$GW_MELEE/src/melee/gm/gmfrontend.c"
```

Expected with the strings as they are on 2026-10-06: findings for the longer helps (the Envoy help is 108 characters, about 4 lines at 33). Shorten each reported string in `fe_items_online` until the checker reports `0 finding(s)`, keeping the meaning: for example Envoy becomes `"Rooms you host: a best-of set. Each player fights with an Envoy build and picks a reward."`, Stage List `"Rooms you host: the legal six, or every stage you both have."`, Input Delay `"Frames of delay in rooms you host. 2 suits most connections."`. The same strings appear in `fe_items_set_online` (`gmfrontend_settings.inc`): change both so the two screens agree.

Then the registry rows (N3): after step 2's registry exists, entries registered under parent `online` appear below the built-in rows with the MOD tag, **hidden while a session exists unless the entry says `"online": true`** (8.4). Step 2 owns the registry and that rule; this step's only job is that the ONLINE PLAY screen passes parent `online` when it asks. Nothing registers under it today, so with no such mod the screen is unchanged: say so in the commit.
- [ ] **Step 7: Build and prove the exe has the new code.**

```bash
cd "$MAIN" && tools/port/build.sh
grep -a "online.lobby" "$GW_BUILD_ROOT/melee-pc.exe" | head -1
grep -a "Locked in" "$GW_BUILD_ROOT/melee-pc.exe" | head -1
```

Expected: the build ends with the bridge fixpoint message and a linked exe (churn in `gw_mex_bridge.c` is normal and not committed); both `grep -a` lines print (a stale exe prints nothing: root `CLAUDE.md` fact 1). The shims are new `gw_Ui_Room*` externs: the audit step of `build.sh` must pass; if it names a missing symbol, the shim file is not in the host source list (`build.sh` reads the translation units from its own list: add `gw_ui_room.c`, `gw_ui_online_parts.c` and `gw_ui_room_native.c` where `gw_ui_render.c` is listed).
- [ ] **Step 8: Re-run everything that does not need a window.**

```bash
for t in atlas-tokens atlas-layout atlas-focus atlas-input atlas-screen atlas-stack atlas-parts atlas-render atlas-binding atlas-lint atlas-online-parts atlas-room atlas-room-native; do nt $t | tail -1; done
bash "$WS/tools/port/check_atlas_online.sh" "$GW_MELEE"; python "$WS/tools/port/check_atlas_online_text.py" "$GW_MELEE/src/melee/gm/gmfrontend.c"
```

Expected: every test line ends `0 failed`; `check_atlas_online: ok`; `check_atlas_online_text: 0 finding(s)`.
- [ ] **Step 9: Commit.** Game repo: `gmfrontend_online.inc`, `gmfrontend.c`, `gmfrontend_settings.inc`, message `frontend: the online room screens draw through Atlas (MELEE_ATLAS=0 keeps the legacy drawing); pad path unchanged`. Workspace repo: the two Python files, message `tools: lint of the online rows' strings against the Atlas explainer`.

---

### Task 9: Documentation

**Files:**
- Modify (game repo): `src/melee/gm/CLAUDE.md`
- Modify (workspace repo): `docs/NEXT-SESSION.md`, `tools/port/README.md` (the checks, if not already added in Task 6)

- [ ] **Step 1: The game-side map.** In the table of `src/melee/gm/CLAUDE.md`, add the row `| gmfrontend_atlas_online.inc | the Atlas drawing of the room screens: copies legacy predicates into the host's room view by name, turns mouse and keyboard intents into the same MenuInput bits; reads netplay state, writes none (tools/port/check_atlas_online.sh) |` and under Rules: `- A change to what the online screens show goes in the adapter or in pc/platform/gw_ui_room.c; a change to what they do goes in gmfrontend_online.inc and the netplay layer, never in the adapter. Run tools/port/check_atlas_online.sh after touching either.`
- [ ] **Step 2: The state.** In `docs/NEXT-SESSION.md`, in the section that lists what the migration has built, add one dated line for step 6: built, what the owner must look at (Task 10), what is retired (nothing yet: Task 11), the two spec corrections (Random Opponent is working; step 5 is a dependency). Replace stale prose rather than appending an "update".
- [ ] **Step 3: Commit.** Game repo: `docs: gm CLAUDE.md names the Atlas online adapter and its rules`. Workspace repo: `docs: NEXT-SESSION notes Atlas step 6`.

---

### Task 10: The in-game proof (a checklist for a Windows agent or the owner)

**Nothing before this task proves a lobby in the game.** Tasks 1 to 9 prove the parts and the composites against a recording sink, the intent stream against a model, the shim lifetime, the isolation by grep, and that the exe contains the new code. They do not prove that two real clients still agree, that the quads look right, that the cost is acceptable or that a dropped connection still behaves.

**Who and when.** Only when the owner is away, or let him do it: two game windows steal focus. Both windows on the **second monitor** (`MELEE_WINDOW_X` / `MELEE_WINDOW_Y`; ask the coordinator for the position), `MELEE_VOLUME=0`, never hidden or minimised. Test with the **ACE** disc and ACE fighters (the owner's standing rule), and once on vanilla. Stop a client by closing its window or by the PID you started; **never by image name**. At most 8 `melee-pc` in total; keep 2 GB free. No screenshots as proof (one is allowed to diagnose how something looks; the overlay is left out of `gd.screenshot`, use an OS window capture). Two local clients: `_build/netplay_local.ps1` (read its header for the host and guest switches; it points the mods folder at `_build/nomods` unless told otherwise, so pass the ACE mod folder to both).

- [ ] **Step 1: Confirm the exe.** `grep -a "online.lobby" "$GW_BUILD_ROOT/melee-pc.exe"` and `grep -a "Locked in" ...` print a line.
- [ ] **Step 2: ONLINE PLAY.** From the main menu: Online. Look at, and write down yes or no for: every row is there (Host a Room, Join a Room, **Random Opponent**, Stage List, Turbo, Envoy, Stocks, Time Limit, Input Delay); a choice row steps with left and right and says its value in words; a slider moves; the explainer shows the row's help in at most three lines; Join a Room with no server file shows the corner note; B goes back.
- [ ] **Step 3: Host and join by code.** Client A hosts: WAITING ROOM shows the code large in `display`, the `COPY` button works with X and with a click (paste it somewhere to check), the guest card says WAITING. Client B: Join a Room: type the code (keyboard), then clear it and paste with Y; use the mouse on the slots and the up and down strips; a wrong code shows rose edges **and** the word FAILED and returns to the field; the right code joins. Both cards fill; the link meter shows bars, a word and a number; the number is plausible (same machine: a few ms).
- [ ] **Step 4: The lobby, game 1 (the blind pick).** Both players press A to pick. **While only one has locked, the other player's card on your screen must say `Locked in` and not the fighter's name.** Write down what each window showed at each moment (this is the information-leak check). When both lock, both names appear.
- [ ] **Step 5: Strikes.** The coin flip tag appears for the strike phase; the player whose turn it is sees `YOUR TURN` in ember, the other sees `P1'S TURN` or `P2'S TURN` in plain; **focus appears on the tiles only for the player whose turn it is** and never while reconnecting. Strike a stage three ways in three games: pad (D-pad then A), mouse (hover, click), keyboard (arrows, Enter): the other client sees the same result each time (`P1 STRUCK` on the same tile). Hovering without a click changes nothing on the other client. The three-cue focus (lift, ember edge, four brackets in your port colour) is on the tile under the cursor. Hover a tile that is not open: the cursor does not go there; click it: a note says it is out.
- [ ] **Step 6: Counterpicks and paging.** Set Stage List to All Stages on the host (with ACE: many stages). The grid shows group headers (`STARTERS`, `COUNTERPICKS`), pages with `PAGE n / m`, L and R and Tab and the wheel turn the page, and the cursor always lands on a tile that is drawn. Look at it at 4:3 and at 16:9 (below).
- [ ] **Step 7: Ready and the count.** In the ready phase the ember `READY` plate is clickable and A and START ready you; START again takes it back; a click anywhere else does **not** ready you (the deliberate narrowing). During the count the plate shows the numeral and `B CANCEL`; B takes the ready back on your side only. B in the lobby asks twice: the first B shows the note and the key hint reads `Leave now`; the second leaves.
- [ ] **Step 8: A full match and the return.** Play the match. Back in the lobby both cards say RECONNECTING for a moment and then recover; game 2's flow (winner bans two, loser picks, then characters) draws correctly and the score reads `Game 2   1 - 0`.
- [ ] **Step 9: Envoy online.** Host with Envoy on: the explainer FROM says `Host sets: Envoy`; when the reward pick opens the instruction line says so with the seconds left; **the lobby accepts the same input as before** (the Envoy script's own pick UI is step 3's; if step 3 is not merged the legacy pick draws). Write down any key the lobby took that it should not have.
- [ ] **Step 10: A dropped connection.** Close the guest's window (by the window or the PID you started) mid-lobby. The host returns to the waiting room with the same code and a note; start a new guest and join the same code. Then close the **host** mid-lobby: the guest goes back to ONLINE PLAY with the room-closed notice.
- [ ] **Step 11: A mod screen open during a rollback match.** Offline, with the Atlas demo mod's screen open (`examples/demos/atlas-screen`, F7), run the curated SyncTest (`MELEE_SYNCTEST_BENCH=1 MELEE_SYNCTEST=12 MELEE_SYNCTEST_CURATED=1`, the proof the quick reference names): 0 mismatches. Then in a real room with Envoy online open the Envoy bag (step 1's) during the match: the match is not paused and the pad is not masked, neither client desyncs (compare the two logs for `desync` lines).
- [ ] **Step 12: Widths, motion, cost.** Repeat Steps 2 to 7 at `MELEE_WINDOW_W=640 MELEE_WINDOW_H=480` (every string legible, nothing outside its plate, a 15-character name truncates with an ellipsis), at 960x720 (4:3) and at 1920x1080 (the wide arrangement). Turn on Reduced Motion (Settings): the open fade is a cut. Frame cost with `MELEE_FPS=120` and the FPS readout: the lobby must hold 120 fps on the host machine; record the readout. (Step 2's door should expose the native screens' quad and time counters; record them if it does.)
- [ ] **Step 13: The fallback.** `MELEE_ATLAS=0` on both clients: every online screen is the legacy one and still works end to end.
- [ ] **Step 14: Capture and report.** Save from each run folder `"$GW_BUILD_ROOT/runs/<name>/melee-pc.log"` the lines with `frontend:`, `ui:` and `netplay:` and any error; a yes or no for every numbered item above with one line for each no; say plainly which items were not run and why (a second machine, a real internet link, a real 150 ms ping were probably not available). The owner decides whether the look is accepted. **Do not do Task 11 in the same session.**

---

### Task 11: Retire the legacy drawing (a follow-up, not part of this plan's first pass)

Only after the owner has looked and accepted (Task 10), and not in the same session. The retirement list is the spec's: the room layout JSON and `gmfrontend_online.inc` drawing (`out_lobby`, `out_online`, the `fl_*` draw paths).

- [ ] **Step 1: Remove the drawing from `gmfrontend_online.inc`:** `fl_build_wait`, `fl_build_code`, `fl_build_lobby`, `fl_build`, `fl_el`, `FlEl`, `fl_lookup`, `fl_val`, `fl_colour`, `fl_when`, `fl_offset`, `fl_lifts`, `fl_subst`, `fl_special_quad`, `fl_slot_text`, `fl_axis_state`, `fl_play*`, `fl_grid_draw`, `fl_grid_head`, the signature code (`fl_signature`, `fl_sig_*`), the status strip, and the model upkeep in `fl_frame` / `fl_frame_anim` / `fl_exit` for the three screens. **Keep** the state machines, `fl_instruction`, `fl_phase_title`, `fl_card_portrait`, `fl_stage_name`, the cursor functions and the toast helpers: the adapter calls them. The loading screen (`FL_LOAD`) and the CSS and SSS still use the model until step 4 removes them; do not remove `fl_build_load` or `fp_*`.
- [ ] **Step 2: Remove the art:** `menu/out_lobby/` (the `waiting_room_`, `code_entry_` and `lobby_` layouts, their motion files and 1x/2x PNGs, `LOBBY.md`), `menu/out_online/` (the status strip), `menu/pipeline/lobby.py` and `online.py` and their tests; the entries for them in `out_kit/kit.json` and in the release packaging (search `tools/release/` for `out_lobby` and `out_online` first; the loading art `out_loading` stays until step 4). Fix the stale "(soon)" comment in the header of `gmfrontend_online.inc`.
- [ ] **Step 3: Remove the switch** `MELEE_ATLAS=0`'s effect on these screens once the owner says the legacy path is not wanted as a fallback (spec 6.4 keeps it only while both exist).
- [ ] **Step 4: Verify.** The build, the nine native tests above, `check_atlas_online.sh` (update guard 5, which reads the legacy pad line), and Task 10 steps 2, 3, 5 and 7 again. Commit in both repos.

---

## Self-review

**Spec coverage (13.6).**

| 13.6 item | Where |
|---|---|
| ONLINE PLAY rows (Host, Join, Random placeholder, Stage List, Turbo, Envoy, Stocks, Time Limit, Input Delay) | Task 8 step 6 (through step 5's adapter; strings linted); Random kept, see the two corrections |
| JOIN ROOM (code entry) | Tasks 3, 5, 6, 7, 8 |
| WAITING ROOM | Tasks 5, 7, 8 (host, guest and Random's FINDING OPPONENT) |
| LOBBY (strikes, bans, picks, ready, countdown, coin flip) | Tasks 4, 5, 6, 7, 8 (the character pick opens the existing CSS: `fe_np_pick_char` is untouched) |
| Code entry part | Task 3 (`display` role: the spec has no `code` role) |
| Port cards with ping and the link meter | Task 5 (card via step 4), Task 2 (meter with hysteresis) |
| The dialogs | Used for one thing only: a long bad notice at the landing screen (Task 8 step 6). The step 1 dialog part is otherwise unused; nothing in the netplay flow waits for a button |
| The netplay layer is not touched | Task 6 (guards 1 to 7), Task 7 (reads only), Review Focus 1 |
| Retired: room layout JSON, `gmfrontend_online.inc` drawing, `out_lobby`, `out_online`, `fl_*` draw paths; the "Random Opponent (soon)" row | **Not retired in this pass** (Task 11 is a follow-up after the owner's look); the Random row is kept (a working feature) |
| Verified without the game: layout tests of every lobby state with sample data | Tasks 4 and 5 (the 4,320-view fixture at three widths) |
| The intent stream is identical for pad and mouse | Task 6 (`intents`): the pad path is untouched, so the identity is between the legacy bits and the translated ones, plus the model comparison for the three ways to strike a stage |
| No host file in `PL/gw_ui_*` includes the netplay headers | `check_atlas_online.sh` guard 1 |
| Must be seen: two real clients, strikes, ready, countdown, a full match; a rollback session with a mod screen open; a dropped connection | Task 10 steps 3 to 11 |

**Gaps and deviations the engineer and the coordinator should know about.**
1. **Pad input is not translated, on purpose.** The spec's wording (U4 takes intents from the pad) would route the pad through Atlas. For the lobby that adds a path where none is needed and a chance to change what a button does. The pad term stays the retail read.
2. **A click anywhere no longer readies you** (Task 6). Mouse-only, local, reversible.
3. **Cursor geometry now comes from the host's grid model** (Task 4). The cursor algorithms are unchanged; their input rectangles are not the retired layout's pixels. This is the one place the drawing and the cursor logic meet, so it has its own test and its own look (Task 10 step 6).
4. **Room rules are read-only** in the room. The mockup shows steppers; editing rules in the room needs a protocol, which is out of scope (spec 14). They are shown as rows that are never focused.
5. **No hatch, no model for stages.** A disabled or decided tile is dim plus a word (`STRUCK`, `BANNED`, `OUT`, `NOT YET`); stage tiles show names only (no stage art is captured today, as before).
6. **The mockup's "Server reachable" indicator is not built:** the code only knows a server is configured (`Netplay_MenuHasServer`), not that it is reachable. The link meter is the peer link only.
7. **The Turbo "private-lobby toggle"** is an engine lane that is not built (the memory note says the packet is written). This step draws the Turbo row and tag from `Netplay_Turbo` and `Netplay_TurboPref`, as the legacy screens do; when the engine lane changes those readbacks the adapter changes, not the composite.
8. **The Envoy reward pick in the lobby** is drawn by the Envoy script today and by step 3's reward screen later. The spec (8.4) says no mod screen is pushed over a room screen; the legacy behaviour is that the lobby waits while a script draws. This plan keeps the legacy input behaviour (Task 6 test) and leaves the arbitration to step 3; look at it in Task 10 step 9.
9. **Link thresholds** (50, 90, 140 ms, 8 ms dead band) and the words are this plan's proposal, not measured.
10. **Names assumed from step 4** (`AtPortCard`, `at_part_portcard`) and from step 2 (the native door, the note shim, the fade) are guesses at unbuilt code. Each is behind one wrapper and Task 0's gate.

**Placeholder scan.** No step defers a decision or refers to another task instead of showing its code. Where an unbuilt step's name is unknown, the task says `RECONCILE`, shows the code against an assumed name, and the gate fails until the real name is written in. The second-monitor position is asked of the coordinator, as in step 1. Line numbers into existing files are given as quoted text to find (the lines drift).

**Type and name consistency.** `AtRoomView`, `AtRoomPlayer`, `AtRoomStage`, `AtGrid`, `AtGridCell`, `AtGridHead` (Task 4) are used unchanged by Tasks 5, 6, 7; `AtCodeView` and `AT_CODE_BAND` (Task 2's header, Task 3) by Tasks 4, 5; `AT_RH_*` and `AT_HIT_ROOM` (Task 5) by Task 6 and the host door; `AtRoomIntent`, `AT_RI_*` and `at_room_intent_name` (Task 6) by Task 7, and the intent **names** `up down left right accept back start copy paste page_l page_r stage_at code_slot` are the ones the adapter's table and guard 4 read. Shim names `gw_Ui_Room*` (host) and `Ui_Room*` (game) are identical apart from the prefix. `at_room_fill(rv, sc, vw, now_ms)` has four arguments everywhere it is called.

**Review Focus pinned.** 1 (netplay stream): Task 6 `intents` and the guards. 2 (focus on nothing): Task 4 `cursor` and `grid`, Task 5 render checks. 3 (stale view): Task 7 `lifetime`, Task 5 the NULL-view check. 4 (overflow): Task 5 `render` and `lint_text_inside` / `lint_text_overlaps`, Task 8 step 6 text lint. 5 (style breaks): Task 1 and every test that includes it. 6 (tests that pass only in the good case): the fixture covers no link, reconnecting, guest and host, empty and full lists. 7 (Envoy reward): Task 6 `reward_open` check, Task 10 step 9. 8 (flicker): Task 2 and Task 7 `ping`. 9 (blind-pick leak, found while writing Task 7): guard 7 and Task 10 step 4.

**Execution recommendation.** Tasks 0 to 3 are self-contained and can go to fresh agents one at a time with a review between. Task 4 and 5 and 6 share the room view and one mental model: one agent in order. Tasks 7 and 8 touch retargeted game code and the exe build: one agent, and the coordinator reviews the guard output before the build. Task 10 is for a Windows agent while the owner is away, or for him. Task 11 waits for his look.
