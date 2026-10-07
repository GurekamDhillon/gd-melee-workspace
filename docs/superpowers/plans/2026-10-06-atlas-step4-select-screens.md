# Atlas step 4: character select, stage select and Versus rules, one character select for every mode: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy kit's character select (CSS) and stage select (SSS), and the retail Versus rules screens, with Atlas screens, and make ONE Atlas character select serve every mode that has a `GS_CSS` state, driven by a per-mode **mode profile**. The CSS and SSS state machines are moved out of `gmfrontend_select.inc` into a pure C model that both the legacy drawing and the Atlas drawing read, so the two coexist on one set of rules until the legacy path is deleted.

**Architecture:** (1) A pure C **CSS model** (`gw_ui_css.c`: four ports, cursors, cards, picks, costumes, CPU levels, teams, the start blocker, the result) and an SSS model (`gw_ui_sss.c`), both host-testable with no game, parameterised by a **mode profile** (`gw_ui_css_profile.c`, keyed by the retail `CSSMatchType` that every mode already stores in `CSSData.match_type`). (2) Engine additions to the step 1 parts: tabs in the screen record, a band place for port cards and the matchup strip, per-port cursors, an auto-column grid, native cell storage beyond 12 cells, image cells for disc art, the port-card part. (3) A host-side **disc-art decoder** (copies pixels at once; never keeps a pointer into the disc archive). (4) A game-side adapter, `gmfrontend_atlas_select.inc`, that runs the model each frame with the game's pads and hands the Atlas host a view through scalar shims. (5) One entry point, `gmFrontend_AtlasSelect`, that the three existing entry functions become wrappers of; modes move in four groups with one line each in their state's `on_enter`.

**Tech Stack:** C11 host code built by `tools/port/build.sh` (clang, `i686-pc-windows-msvc`) and the standalone harness `tools/port/native_test.sh`; game-side C (retargeted decomp, syntax-checked as PowerPC); Python 3 for the audit script; Lua 5.4 only for the Lua-facing checks that must still pass.

**Spec:** `docs/superpowers/specs/2026-10-06-menu-reunification-design.md`, section 13.4 (this step), sections 4 to 10 for the style, parts, input and layout rules, 6.4 for the router. Step 1 plan (what exists): `docs/superpowers/plans/2026-10-06-atlas-step1-components-and-envoy-bag.md`.

> **Nothing in this plan was compiled or run when it was written.** Every code block is a design in code, checked by reading against the sources named; each task's tests are written to fail first and be made to pass by the engineer. Where a fact was not read from source it is marked **(unverified)** and a step says how to settle it.

## What this step needs from steps 2 and 3 (gates)

Steps 2 and 3 are planned in parallel and are not built. This plan asks for the following, by capability, not by file. **Task 0 checks each one by command; if a row fails, stop and report: do not build the dependent tasks on a guess.** Names marked `spec` are the spec's own (6.7); the step 2 plan fixes the final spelling, and the engineer replaces the name in the shim table of Task 9 if it differs.

| # | Needs | From | Why step 4 cannot do it alone | Tasks that wait for it |
|---|---|---|---|---|
| G1 | **The game-side door**: `GM/gmfrontend_atlas.inc` with the shim set `gw_Ui_*` (`spec`: `gw_Ui_ItemBegin`, `gw_Ui_Label`, `gw_Ui_Value`, `gw_Ui_Options`, `gw_Ui_PollEvent`), a frame protocol (begin, submit, poll, end) and the early branch in the frontend's per-frame function that calls `fa_frame()` | step 2 (U8) | CSS and SSS are scenes with their own state, not `FrontendScreen` tables, so step 4 adds its own shims **on top of** this door and its frame protocol, never beside it | 9, 10, 11 |
| G2 | **A host-owned native screen slot**: a screen record built by the adapter in place (not through Lua), with the **native owner** token the stack and `gd.ui` ownership rules recognise, closed on every scene exit | step 2 (U5, U8) | step 1's stack knows script owners only; a native screen with no owner rule is the "leaked top screen draws over the next scene" hole (Review Focus 7) | 9 |
| G3 | **Atlas draws during a `GS_FRONTEND` scene**, in front of the scene's fade, with its own fade quad, in the frame order step 2 proves; plus the switch `MELEE_ATLAS=0` that makes an Atlas screen fall back to the legacy drawing while both exist | step 2 (spec 6.1, section 18 first two items) | step 1 drew only inside a match; the CSS and SSS are frontend scenes | 9, 10 |
| G4 | **Canvas width for native scenes**: the host knows the window aspect when it draws; `gd.safe_area()`'s `w` is the same number the layout gets | step 1 (done) and step 2 | none new if G3 holds | 6 |
| G5 | **The hub flows that reach the CSS** keep their position protocol: Back from the CSS returns through the state's exit handler (`css->pending_scene_change = 2`), which step 2 must not change | step 2 | unchanged contract, checked by Task 10 tests | 10 |
| G6 | **Value rows** (slider `step`, live values, group headings, engine-owned choices) for the Versus rules pages | **step 5, Task 2** | MATCH SETUP is a table of stocks, time, ratio sliders; step 1's list has no `step` and takes values as data | 12 only |

**What step 5 needs from this plan:** Tasks 1 (the style checks), 4 (tabs, the band, native cell storage) and 5 (the `image` sink op, parts, tabs in the render) are step 5's gate G5. They are host-only and self-contained; build them first if step 5 is built first, and do not duplicate them there.

Step 3 gives step 4 nothing it must wait for. It gives the **element mask and `gd.ui.hud` keep-out zones**, which the CSS does not use; if step 3 renames `AtScreen` fields that Tasks 4 to 6 extend, the engineer follows the rename.

Order inside the step: Tasks 0 to 8 are host-only and testable without the game; 9 to 11 need G1 to G3; 12 needs G6; 13 is the owner's look; 14 retires the legacy path last.

## Global Constraints

Exact values come from the spec; if a task seems to need a different value, stop and ask the coordinator.

- **Canvas, text, depth, motion, budgets, online, naming, English only, process rules:** exactly as the step 1 plan's Global Constraints (copied by reference: that list is binding here). Restated where this step leans on them: text floor 12 px at 640x480 and the fit rule (step down one role of the same face, then ellipsis, never squash); chamfers on **two opposite corners only** (top-left and bottom-right: 8 px panes, 5 px rows and buttons, 3 px cells); focus is **three cues at once** (lift 2 px, ember front edge, tick for rows or four registration brackets for cells, tinted with the port's colour on a shared screen); ports are numeral plus shape plus colour (1 circle red, 2 square blue, 3 hexagon yellow, 4 diamond green, CPU hatched grey with the word CPU); one Atlas screen is at most 4,096 entries and warns at 3,000; **only one screen stack exists: only the top screen draws and takes input.**
- **Disc art is never stored or committed.** Icons (64x56) and portraits (136x188) are decoded in memory at run time from the player's own disc and are shown inside a generated frame with the two-letter abbreviation; where decoding is impossible the frame with the abbreviation and the words `DISC ART` is the shipped look (spec 4.8, section 12 item 8). No test fixture may contain disc bytes: the decoder tests use synthetic tiles built in the test.
- **The CSS contract does not change.** `CSSData` and `SSSData` are handed over exactly as today; the state's own exit handler (`gmVsMelee_ExitCss` and the per-mode ones) reads what it read before. The online lobby's pick keeps its logic and its protocol; this step changes how it is drawn only when the lobby's profile is switched on (Task 11, last).
- **`MELEE_NATIVE_CSS=1` and `MELEE_ATLAS=0` keep working** until Task 14 deletes the legacy path, which waits for the owner's look.
- **Two repositories.** Game repo `melee/` (branch `pc-port`; your worktree is `agent/atlas4`); workspace repo at the root (`tools/`, `docs/`, `menu/`). Each task says which one a commit goes to. Generated build output (`gw_mex_bridge.c`) churn is normal and is not committed by you.
- **Process rules (this machine):** no game, launcher or browser window while the owner is at the machine; the in-game task runs only when he is away, on the second monitor, `MELEE_VOLUME=0`, ACE disc for play tests. Never terminate processes by image name; stop only a process you started, by PID. Build only through `tools/port/build.sh` in a private worktree made by `tools/port/agent_new.sh`; never raw clang for the game (standalone native tests go through `nt`, below; PowerPC syntax checks use the exact command in `melee/CLAUDE.md`). Never print disc paths; never open `_build/local-assets/`. No screenshots as verification.

## Review Focus

The failure modes the spec and step 1's lessons imply, most likely to bite a player or the next reviewer. Each is pinned by a named check in the task that owns the code.

| # | What goes wrong | Pinned by |
|---|---|---|
| 1 | **A mode starts with the wrong fighter, costume, team, CPU level, stocks or nametag** (the CSSData contract; each mode reads a different slot). | Task 2 `profile_table_matches_modes`; Task 3 `finish_*`; Tasks 10a to 10d per-group `finish_leaves_mode_fields` |
| 2 | **The plan's own drawing breaks the style rules**: a chamfered corner drawn over, fewer than three focus cues, text outside its pane, a port told apart by colour alone, a disabled cell that is only dimmed. | Task 1 `atlas_style.h` and its self-test (the checks can fail); Tasks 5, 6, 8 call them on every new part and screen |
| 3 | **Ownership and lifetime**: a native screen left on the stack after a scene ends draws over the next scene; a disc-art texture outlives its archive; a copied screen record points at freed cell storage; a sink without an `image` op crashes. | Task 4 `ext_cells_never_copied` and a grep guard; Task 7 `decode_copies_pixels`; Task 9 `closed_on_every_exit`; Task 5 `sink_without_image_is_safe` |
| 4 | **Four ports on one screen**: a cursor on a port with no controller, two cursors on one cell, a CPU card focused by the wrong port, a port that leaves mid-screen. | Task 3 `ports_*`; Task 5 `two_cursors_one_cell` |
| 5 | **Rosters of 26, 29, 60 and 128 fighters and up to 256 stages**: more cells than the record holds, more rows than the room, a tab with zero entries, hit rectangles past the 96-entry limit, quads past the cap. | Task 4 `capacity`; Task 6 `rosters_at_three_widths`; Task 8 `stages_256` |
| 6 | **Disc art missing**: a Geno-defined fighter has no icon (`img == NULL`); an unsupported GX format; a TLUT of the wrong size; more art than texture slots. | Task 7 `decode_*`, `slot_pool_evicts`; Task 6 `placeholder_when_no_art` |
| 7 | **Back and Start semantics drift**: `B` twice to leave, Start blocked with a toast, Z leaves a port, A on an empty card adds a CPU: any of these changing silently. | Task 3 `legacy_rules_*` (each rule is one named check, read from `fs_css_port`) |
| 8 | **Wide and ultrawide windows and the mouse**: hit rectangles must follow the arranged rectangles; the mouse drives one port, as `fs_mouse_port()` does today; a pointer off the picture does nothing. | Task 6 `hits_follow_layout`; Task 9 `mouse_port` |
| 9 | **Tests that ran as the developer console hid a bug** (step 1: the console may drive any screen). Every ownership or permission check in this step is exercised as a **native owner and as a mod caller**, never only as the console. | Task 9 `owner_native_vs_mod`; Task 4 stub test with `caller=` set |
| 10 | **Online lobby regression** (a desync is the worst outcome in the project): the lobby's pick must behave as before, a fighter the opponent lacks stays unpickable, no host file includes the netplay headers. | Task 11 (profile `lobby`, gated on a two-client look); Task 3 `lobby_*`; guard grep in Task 4 |

---

## File structure

Game repo (`melee/`).

| File | Create/Modify | Responsibility |
|---|---|---|
| `pc/platform/gw_ui_css_profile.h/.c` | Create | the mode profile type and the table keyed by `CSSMatchType` (pure C, no game types) |
| `pc/platform/gw_ui_css.h/.c` | Create | the CSS model: ports, cursors, cards, pick, costume, CPU, teams, blocker, result; sfx and toast as returned bits |
| `pc/platform/gw_ui_sss.h/.c` | Create | the SSS model: stage list, tabs, cursor, pick, random, strike/ban cell states (drawing only) |
| `pc/platform/gw_ui_screen.h/.c` | Modify | tabs, band, per-port cursors, native cell storage (`ext`), image fields on cells and explainer, `AT_MAX_ITEMS` stays 32 here |
| `pc/platform/gw_ui_layout.h/.c` | Modify | `at_layout_band`, `at_layout_tabs`, `at_grid_cols` (auto columns) |
| `pc/platform/gw_ui_parts.h/.c` | Modify | the `image` sink op, `at_part_port_card`, `at_part_matchup`, bracket tint per port, image cell |
| `pc/platform/gw_ui_render.c` | Modify | draw tabs, the band, per-port brackets, image cells; cull to visible rows |
| `pc/platform/gw_kit.c`, `gw_kit.h` | Modify | `gw_Kit_TexAddHsd` (decode CI4, CI8, I4, IA4, I8, IA8, RGB565, RGB5A3, RGBA8, CMPR from game memory into a disc-art pool with eviction) |
| `pc/platform/gw_ui_native.c` (or the step 2 file that owns shims) | Modify | the `gw_Ui_Css*` and `gw_Ui_Sss*` shims (scalar arguments only) |
| `src/melee/gm/gmfrontend_select.inc` | Modify | `fs_*` rules call the model; the legacy drawing stays until Task 14 |
| `src/melee/gm/gmfrontend_atlas_select.inc` | Create | the adapter: roster and pads in, view out, `CSSData`/`SSSData` written at finish |
| `src/melee/gm/gmfrontend.c`, `gmfrontend.h` | Modify | `gmFrontend_AtlasSelect`; the three entry functions become wrappers |
| `src/melee/gm/gm{classic,adventure,allstar,event,homerun,multiman,...}.c` | Modify | one `TARGET_PC` line each in the CSS state's `on_enter` (Tasks 10b to 10d) |
| `pc/tests/atlas_style.h`, `atlas_style_test.c` | Create | the style checks and their self-test |
| `pc/tests/atlas_profile_test.c`, `atlas_css_test.c`, `atlas_sss_test.c`, `atlas_select_render_test.c`, `atlas_discart_test.c`, `atlas_select_adapter_test.c` | Create | one native test per unit |
| `pc/tests/atlas_fake.h`, `atlas_rec.h` | Modify | the `image` op in the recording sink |

Workspace repo (root).

| File | Create/Modify | Responsibility |
|---|---|---|
| `tools/port/css_states.py`, `tools/port/css_states_expected.json` | Create | the audit: every `GS_CSS` and `GS_SSS` state, its file, its enter data, its `match_type` source |
| `tools/port/native_test.sh` | Modify | cases `atlas-style`, `atlas-profile`, `atlas-css`, `atlas-sss`, `atlas-select-render`, `atlas-discart`, `atlas-select-adapter` |
| `docs/TERMINOLOGY.md`, `menu/CLAUDE.md`, `docs/superpowers/plans/` | Modify | the terms mode profile, port card, band, tab; the retirement list |

## Preflight (once, before Task 0; not a task)

- [ ] **Step 1: Read.** `CLAUDE.md` (root), `docs/NEXT-SESSION.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md`, spec sections 4 to 10 and 13.4, the step 1 plan's Global Constraints and Review Focus, `_research/menu-legacy-kit-inventory-2026-10-06.md` sections 1.1 and 1.2, and `melee/src/melee/gm/gmfrontend_select.inc` top to bottom (it is the oracle for Task 3).
- [ ] **Step 2: Private lane and shell.** Exactly as the step 1 plan's Preflight step 2, with the lane name `atlas4`:

```bash
export MAIN="<the workspace root: the directory that contains tools/ and _toolchains/>"
cd "$MAIN" && tools/port/agent_new.sh atlas4
git -C "$MAIN" worktree add worktrees/ws-atlas4 -b ws/atlas4
export WS="$MAIN/worktrees/ws-atlas4"; export GW_ROOT="$MAIN"
export GW_MELEE="$MAIN/worktrees/atlas4"; export GW_BUILD_ROOT="$MAIN/_build/agents/atlas4"   # as agent_new.sh printed them
nt() { GW_ROOT="$MAIN" GW_MELEE="$GW_MELEE" GW_BUILD_ROOT="$GW_BUILD_ROOT" bash "$WS/tools/port/native_test.sh" "$1"; }
ppc() { ( cd "$GW_MELEE" && "$MAIN/_toolchains/llvm/bin/clang.exe" -fsyntax-only -w -DTARGET_PC --target=powerpc-unknown-eabi -nostdinc -Isrc -Isrc/melee -Iinclude -Ilibs/dolphin/include -Ipc -Ipc/gameworld -Isrc/sysdolphin -Isrc/MSL "$1" ); }
```

`ppc FILE` is the PowerPC syntax check from `melee/CLAUDE.md` (the include list there is authoritative; copy it if it differs). If the shell refuses to run the compiler, say so in the report: **a syntax check that did not run is not a pass.**
- [ ] **Step 3: Baselines** (must still pass at the end):

```bash
cd "$GW_MELEE" && lua pc/tests/envoy_run_ux.lua | tail -1 && lua pc/tests/grid_inventory.lua | tail -1 && lua pc/tests/atlas_ui_stub_test.lua | tail -1
for t in tokens layout focus input screen stack parts render binding; do nt atlas-$t | tail -1; done
nt controls-remap | tail -1
```

Expected: every line ends in a pass (`PASS`, `0 failed`). Record the numbers.

---

### Task 0: Gate check and the audit of every CSS state

**Files:**
- Create (workspace repo): `tools/port/css_states.py`, `tools/port/css_states_expected.json`
- Modify (workspace repo): nothing else

**Interfaces:**
Consumes: the game sources under `$GW_MELEE/src/melee`.
Produces: `css_states.py --check` (exit 0 when the live grep equals the expected file) and `--table` (a Markdown table used by Task 2 and the retirement list).

- [ ] **Step 1: Check the gates G1 to G3 by command.** In `$GW_MELEE`:

```bash
test -f src/melee/gm/gmfrontend_atlas.inc && echo "G1 file ok" || echo "G1 MISSING: step 2 is not merged"
grep -n "gw_Ui_PollEvent" src/melee/gm/gmfrontend_atlas.inc pc/platform/*.c pc/platform/*.inc | head -3
grep -n "MELEE_ATLAS" src/melee/gm/*.c src/melee/gm/*.inc pc/platform/*.c | head -3
grep -n "AT_OWNER_NATIVE\|owner_native" pc/platform/gw_ui_stack.h pc/platform/gw_ui_screen.h pc/platform/gw_script_ui.inc | head -3
```

Expected: every line prints at least one hit. If any is empty, **stop**: write the missing gate and the grep that failed into the hand-off and do not start Task 9. Tasks 1 to 8 do not need the gates and may proceed.

- [ ] **Step 2: Write the audit script (failing first).** Create `tools/port/css_states.py`:

```python
"""Audit of every character-select and stage-select state in the game sources.

    python tools/port/css_states.py --check     # compare with css_states_expected.json
    python tools/port/css_states.py --table     # Markdown rows for the plan and the retirement list
    python tools/port/css_states.py --write     # rewrite the expected file (a reviewed change only)

A state is a GameModeState initialiser whose scene block starts with GS_CSS or GS_SSS. For each we record the file, the
enter-data symbol, and the CSSMatchType the mode stores (the first number passed as the second argument of gm_801B06B0,
or an assignment to match_type, or 'VS' when the state shares gmVsMelee_CssData).
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
EXPECTED = os.path.join(HERE, "css_states_expected.json")

SCENE = re.compile(r"\{\s*(GS_CSS|GS_SSS)\s*,\s*&?(\w+)\s*,", re.S)
MATCH = re.compile(r"gm_801B06B0\(\s*[^,]+,\s*(0x[0-9A-Fa-f]+|\d+)\s*[,U]")
ASSIGN = re.compile(r"match_type\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*;")


def scan():
    rows = []
    for name in sorted(os.listdir(GM)):
        if not name.endswith(".c") or name.startswith("gmfrontend"):
            continue
        path = os.path.join(GM, name)
        text = open(path, encoding="utf-8", errors="replace").read()
        if "GS_CSS" not in text and "GS_SSS" not in text:
            continue
        if name in ("gm_1A3F.c", "gmscdata.c"):          # a switch case and the scene table, not mode states
            continue
        found = SCENE.findall(text)
        if not found:
            continue
        mt = [int(m, 0) for m in MATCH.findall(text)] + [int(m, 0) for m in ASSIGN.findall(text)]
        for kind, sym in found:
            rows.append(dict(file=name, scene=kind, data=sym, match_types=sorted(set(mt))))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--table", action="store_true")
    g.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    rows = scan()
    if a.table:
        print("| file | scene | enter data | match_type(s) |\n|---|---|---|---|")
        for r in rows:
            print("| %s | %s | %s | %s |" % (r["file"], r["scene"], r["data"], ", ".join("0x%X" % m for m in r["match_types"]) or "VS family"))
        return 0
    if a.write:
        json.dump(rows, open(EXPECTED, "w"), indent=1, sort_keys=True)
        open(EXPECTED, "a").write("\n")
        print("wrote %d states" % len(rows))
        return 0
    want = json.load(open(EXPECTED))
    if rows != want:
        print("css_states: the game sources changed: %d states now, %d expected" % (len(rows), len(want)))
        return 1
    print("css_states: %d states match the expected file" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run it and read the result.**

```bash
cd "$WS" && GW_MELEE="$GW_MELEE" python tools/port/css_states.py --table
```

Expected: a table of every state. **Compare the count with the spec's "23 states in about 19 files".** A grep of the tree when this plan was written found **25 `GS_CSS` initialisers in 19 files** (11 single-state mode files, `gmmultiman.c` with 7, five VS-machinery special melees, `gmvsmode.c` and `gmtrainingmode.c`), and **one `GS_SSS` state in `gmvsmode.c` and one in `gmtrainingmode.c`**; `gmscdata.c:120` is the scene table and `gm_1A3F.c:91` a switch case, so neither is a state. If your count differs, the table you print is the truth: continue with it and put both numbers in the hand-off. Then write the expected file and make `--check` pass:

```bash
GW_MELEE="$GW_MELEE" python tools/port/css_states.py --write && GW_MELEE="$GW_MELEE" python tools/port/css_states.py --check
```

Expected: `css_states: N states match the expected file`.

- [ ] **Step 4: Read what the table cannot say** (record each answer in the task's commit message; each is a **(unverified)** until you do):
  1. `gm_801BA938(temp_r31, 1, 4, true)` in `gmevent.c` `onEnterCss` (when `x44 == 1`): does it restrict which fighters the retail CSS offers? If yes, the Event profile needs a roster filter (Task 2 field `roster_filter`); if no, Event is an ordinary one-player profile.
  2. `gm_801BEDA8` in `gmhanyucss.c` cycles `match_type` through 24 values on a CSS exit. Find out which scene uses it and whether any `GS_CSS` state in the table reaches it; if one does, the profile must carry "mode can change on exit".
  3. The one-player modes' exit handlers read `players[css->unk_0x0 - 1]` through `gm_801B0730`. Confirm for each file in the table that no handler reads another slot (`grep -n "gm_801B0730\|gm_801B07E8" src/melee/gm/*.c`).

- [ ] **Step 5: Commit.** Workspace repo: `tools/port/css_states.py`, `tools/port/css_states_expected.json`, message `atlas step 4: audit of every CSS and SSS state (the table the profiles are checked against)`, with the attribution lines of this session.

---

### Task 1: The style checks (so this plan's own code cannot break the style rules unseen)

Step 1's plan code repeatedly broke the style rules: chamfered corners drawn over, fewer than three focus cues, text overflowing. This task builds the checks first, **tests the checks themselves** (a check that cannot fail proves nothing), and every later part and screen test calls them.

**Files:**
- Create (game repo): `melee/pc/tests/atlas_style.h`, `melee/pc/tests/atlas_style_test.c`
- Modify (game repo): `melee/pc/tests/atlas_rec.h` (add the `image` op), `melee/pc/tests/atlas_fake.h` only if it needs nothing new
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-style`, die message)

**Interfaces:**
Consumes: `atlas_rec.h` (`REC`, `rec_sink`, `RecPoly`, `RecText`), `atlas_fake.h` (`fake_width`), `gw_ui_parts.h` (`at_plate`, `at_part_row`, `at_part_cell`).
Produces (all later tests rely on these exact names):

```c
int sty_poly_has(const RecPoly *p, float x, float y);            /* point in a convex quad, either winding */
unsigned sty_top_at(float x, float y);                           /* colour of the topmost opaque poly at a point, 0 when none */
int sty_chamfer(AtRect r, float c, unsigned under);              /* 0 ok; 1..4 = which corner broke the rule (4.1) */
typedef struct { float miny; int ember_polys; int polys; } StySig;
StySig sty_sig(int from_poly);                                    /* signature of the polys drawn since index from_poly */
int sty_focus_cues(StySig rest, StySig focused);                 /* 0..3: lift 2 px, ember edge, tick or brackets (4.6) */
int sty_text_inside(AtRect pane, int from_text);                 /* -1 ok, else the index of the first text outside the pane */
int sty_shapes_distinct(const int polys_per_port[4]);            /* 1 when no two ports share a shape signature (4.7) */
```

- [ ] **Step 1: Add the `image` op to the recording sink (a failing build first).** In `pc/tests/atlas_rec.h` add the struct and the recorder; the `AtSink` field itself arrives in Task 5, so for now compile against a local `#ifdef AT_SINK_HAS_IMAGE`:

```c
typedef struct { int tex; float x, y, w, h; unsigned rgba; } RecImage;
/* in Rec: */ RecImage im[64]; int ni;
static void rec_image(void *u, int tex, float x, float y, float w, float h, unsigned c)
{
    Rec *r = (Rec *) u;
    if (r->ni < 64) { RecImage *m = &r->im[r->ni++]; m->tex = tex; m->x = x; m->y = y; m->w = w; m->h = h; m->rgba = c; }
}
/* in rec_sink(): */ #ifdef AT_SINK_HAS_IMAGE
    s.image = rec_image;
#endif
```

- [ ] **Step 2: Write the failing self-test.** Create `pc/tests/atlas_style_test.c`:

```c
#include "atlas_check.h"
#include "atlas_fake.h"
#include "atlas_style.h"

static const AtTextOps OPS = { fake_width, NULL };

/* A correct chamfered plate: ground first, then at_plate (3 quads: face, the two chamfered ends, front edge). */
static void draw_plate(AtRect r, float c, int broken)
{
    AtSink s = rec_sink();
    at_poly_rect(&s, 0, 0, 640, 480, AT_C_GROUND);
    at_plate(&s, r, AT_C_PLATE2, AT_C_EDGE, 3.0f, c);
    if (broken) at_poly_rect(&s, r.x, r.y, 14, 14, AT_C_PLATE2);   /* a square drawn over the top-left chamfer: the bug step 1 had */
}

int main(void)
{
    AtRect r = { 100, 100, 120, 40 };
    StySig a, b;
    int i;
    /* the check passes a correct plate ... */
    draw_plate(r, 5.0f, 0);
    CHECK(sty_chamfer(r, 5.0f, AT_C_GROUND) == 0);
    /* ... and FAILS a plate with a square drawn over the cut (the check can fail) */
    draw_plate(r, 5.0f, 1);
    CHECK(sty_chamfer(r, 5.0f, AT_C_GROUND) == 1);
    /* a plate with all four corners square fails too (the other two corners must be filled, these two cut) */
    { AtSink s = rec_sink(); at_poly_rect(&s, 0, 0, 640, 480, AT_C_GROUND); at_poly_rect(&s, r.x, r.y, r.w, r.h, AT_C_PLATE2); }
    CHECK(sty_chamfer(r, 5.0f, AT_C_GROUND) == 1);

    /* focus cues: a row at rest and focused; the focused one must show lift, ember edge and a tick */
    { AtItem it; AtSink s; AtRect row = { 40, 100, 300, 34 };
      memset(&it, 0, sizeof it); snprintf(it.label, sizeof it.label, "%s", "Stocks");
      s = rec_sink(); at_part_row(&s, &OPS, row, &it, AT_ST_REST);  a = sty_sig(0);
      s = rec_sink(); at_part_row(&s, &OPS, row, &it, AT_ST_FOCUS); b = sty_sig(0);
      CHECK(sty_focus_cues(a, b) == 3);
      CHECK(sty_focus_cues(a, a) == 0); }                                  /* identical draws have no cue: the check can fail */
    /* a cell: the cues are lift, ember edge and four brackets */
    { AtCell c; AtSink s; AtRect cell = { 40, 100, 40, 40 };
      memset(&c, 0, sizeof c); c.model = AT_NO_MODEL; snprintf(c.name, sizeof c.name, "%s", "FOX");
      s = rec_sink(); at_part_cell(&s, &OPS, cell, &c, AT_ST_REST, AT_C_P1);  a = sty_sig(0);
      s = rec_sink(); at_part_cell(&s, &OPS, cell, &c, AT_ST_FOCUS, AT_C_P1); b = sty_sig(0);
      CHECK(sty_focus_cues(a, b) == 3); }

    /* text inside its pane: a long label in a narrow pane is caught */
    { AtSink s = rec_sink(); AtRect pane = { 10, 10, 60, 20 };
      at_text(&s, &OPS, AT_R_ROW16, "A very long label indeed", 12, 26, AT_C_IVORY, AT_ALIGN_LEFT, 0.0f);
      CHECK(sty_text_inside(pane, 0) == 0);                                /* unclipped, it overflows: index 0 is the offender */
      REC.nt = 0;
      at_text(&s, &OPS, AT_R_ROW16, "Fox", 12, 26, AT_C_IVORY, AT_ALIGN_LEFT, 0.0f);
      CHECK(sty_text_inside(pane, 0) == -1); }

    /* ports differ by shape: four different poly counts, and the same count for two ports is reported */
    { int ok[4] = { 3, 1, 3, 2 }, bad[4] = { 3, 1, 1, 2 };
      CHECK(sty_shapes_distinct(ok) == 0);                                  /* 3 appears twice: ports 1 and 3 */
      ok[2] = 4; CHECK(sty_shapes_distinct(ok) == 1);
      CHECK(sty_shapes_distinct(bad) == 0); }
    (void) i;
    ATLAS_DONE("atlas style");
}
```

Register it: in `tools/port/native_test.sh`, before the `*)` line,

```bash
atlas-style)
    sources=(pc/tests/atlas_style_test.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c) ;;
```

and append `, atlas-style` to the die message. Run `nt atlas-style`; expected: the compiler fails (`atlas_style.h` does not exist).

- [ ] **Step 3: Write the helper.** Create `pc/tests/atlas_style.h`:

```c
/* Checks of the Atlas style rules (spec 4.1 depth and chamfer, 4.6 focus, 4.3 text floor and fit, 4.7 ports) over a recorded draw.
 * Include after atlas_rec.h. A check returns 0 or -1 as documented per function; none of them is a substitute for the owner's look. */
#ifndef ATLAS_STYLE_H
#define ATLAS_STYLE_H
#include "atlas_rec.h"
#include "atlas_fake.h"
#include "../platform/gw_ui_tokens.h"

static int sty_poly_has(const RecPoly *p, float x, float y)
{
    int i, pos = 0, neg = 0;
    for (i = 0; i < 4; i++) {
        int j = (i + 1) % 4;
        float cr = (p->x[j] - p->x[i]) * (y - p->y[i]) - (p->y[j] - p->y[i]) * (x - p->x[i]);
        if (cr > 0.001f) pos = 1; else if (cr < -0.001f) neg = 1;
    }
    return !(pos && neg);
}

static unsigned sty_top_at(float x, float y)
{
    int i;
    for (i = REC.np - 1; i >= 0; i--)
        if ((REC.p[i].rgba & 0xFFu) >= 0x80u && sty_poly_has(&REC.p[i], x, y)) return REC.p[i].rgba;
    return 0u;
}

/* 4.1: a chamfered element is cut on the top-left and bottom-right corners only. The point a quarter of the chamfer in from each
 * cut corner must still show what is UNDER the element (`under`), and the point the same distance in from the other two corners
 * must show the element. 1 = top-left was drawn over, 2 = bottom-right, 3 = top-right is cut, 4 = bottom-left is cut. */
static int sty_chamfer(AtRect r, float c, unsigned under)
{
    float q = c * 0.25f;
    if (sty_top_at(r.x + q, r.y + q) != under) return 1;
    if (sty_top_at(r.x + r.w - q, r.y + r.h - q) != under) return 2;
    if (sty_top_at(r.x + r.w - q, r.y + q) == under) return 3;
    if (sty_top_at(r.x + q, r.y + r.h - q) == under) return 4;
    return 0;
}

typedef struct { float miny; int ember_polys; int polys; } StySig;
static StySig sty_sig(int from_poly)
{
    StySig s;
    int i, k;
    s.miny = 1.0e9f; s.ember_polys = 0; s.polys = REC.np - from_poly;
    for (i = from_poly; i < REC.np; i++) {
        if (REC.p[i].rgba == AT_C_EMBER) s.ember_polys++;
        for (k = 0; k < 4; k++) if (REC.p[i].y[k] < s.miny) s.miny = REC.p[i].y[k];
    }
    return s;
}

/* 4.6: three cues at once. The same part drawn at rest and focused: it is lifted by 2 px, the ember edge appears, and a tick or
 * four brackets add at least four polys. Returns how many of the three hold. */
static int sty_focus_cues(StySig rest, StySig focused)
{
    int n = 0;
    if (focused.miny <= rest.miny - 1.9f) n++;
    if (focused.ember_polys > rest.ember_polys) n++;
    if (focused.polys - rest.polys >= 1 && focused.ember_polys - rest.ember_polys >= 2) n++;   /* tick: one thin ember rect; brackets: eight */
    return n;
}

/* 4.3: every recorded text from index from_text on lies inside `pane` horizontally and has a legible role. -1 when all do,
 * else the index of the first offender (fake_width is half the role's size per character: a conservative stand-in). */
static int sty_text_inside(AtRect pane, int from_text)
{
    int i;
    for (i = from_text; i < REC.nt; i++) {
        float w = fake_width(NULL, REC.t[i].role, REC.t[i].s), left = REC.t[i].x;
        if (REC.t[i].align == AT_ALIGN_RIGHT) left -= w; else if (REC.t[i].align == AT_ALIGN_CENTER) left -= w * 0.5f;
        if (at_role_size(REC.t[i].role) < 12) return i;
        if (left < pane.x - 0.01f || left + w > pane.x + pane.w + 0.01f) return i;
    }
    return -1;
}

/* 4.7: colour is never the only signal. `polys_per_port` is how many polys each port's mark used: no two may be equal. 1 = distinct. */
static int sty_shapes_distinct(const int polys_per_port[4])
{
    int a, b;
    for (a = 0; a < 4; a++) for (b = a + 1; b < 4; b++) if (polys_per_port[a] == polys_per_port[b]) return 0;
    return 1;
}
#endif
```


- [ ] **Step 4: Run.** `nt atlas-style` then expected `atlas style: N checks, 0 failed`. If `sty_focus_cues(a, b) == 3` fails for the existing step 1 row or cell, **that is a finding about step 1's parts, not a test bug**: read `at_part_row`/`at_part_cell`, note which cue is missing, and report it to the coordinator before changing the part (a part that shows fewer than three cues breaks the focus rule, spec 4.6).
- [ ] **Step 5: Commit** (game repo: the tests and `atlas_rec.h`; workspace repo: `native_test.sh`), message `atlas step 4: style checks that can fail (chamfer, focus cues, text inside, port shapes)`.

---
### Task 2: The mode profile (the table every mode is checked against)

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_css_profile.h`, `melee/pc/platform/gw_ui_css_profile.c`, `melee/pc/tests/atlas_profile_test.c`
- Create (workspace repo): `tools/port/test_css_profiles.py`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-profile`)

**Interfaces:**
Consumes: the audit (Task 0), `CSSMatchType` in `src/melee/mn/types.h` (values 0x0 to 0x17).
Produces:

```c
enum { AT_MT_LOBBY = 0x40 };                 /* not a retail value: the online lobby's pick */
typedef struct {
    int match_type;          /* CSSMatchType, or AT_MT_LOBBY */
    int group;               /* migration group: 1 VS family, Training, LAB; 2 Classic, Adventure, All-Star; 3 Event; 4 Stadium; 5 lobby */
    int max_humans;          /* ports that may be human at once */
    int cpu_cards;           /* 1: a CPU can be added on the cards (VS family) */
    int teams_from_rules;    /* 1: team colours follow css->vs.start.rules.is_teams */
    int min_to_start;        /* fighters in before Start is accepted */
    int entering_port_only;  /* 1: only the port named by css->unk_0x0 plays (one-player modes) */
    int dummy_cpu;           /* 1: Training: the human plus a CPU dummy in the other of slots 0 and 1 */
    int has_sss;             /* 1: the mode has a stage select after the CSS */
    int online;              /* 1: the lobby's pick */
    int roster_filter;       /* 1: the mode restricts the fighters offered (settled for Event in Task 0 step 4) */
} AtCssProfile;
const AtCssProfile *at_css_profile(int match_type);   /* NULL when the value is not known: the caller keeps the retail screen */
int at_css_profile_count(void);
const AtCssProfile *at_css_profile_at(int i);
```

- [ ] **Step 1: Write the failing tests.** Create `pc/tests/atlas_profile_test.c`:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_css_profile.h"

int main(void)
{
    int mt;
    /* every retail match type 0x0 to 0x17 has a profile; nothing else does except the lobby */
    for (mt = 0; mt <= 0x17; mt++) CHECK(at_css_profile(mt) != NULL);
    CHECK(at_css_profile(0x18) == NULL && at_css_profile(-1) == NULL && at_css_profile(0xFF) == NULL);  /* unknown: retail screen stays */
    CHECK(at_css_profile(AT_MT_LOBBY) != NULL && at_css_profile(AT_MT_LOBBY)->online == 1);

    /* VS family (0x0 to 0xA, shares gmVsMelee_CssData): four humans, CPU cards, teams from the rules, two fighters, a stage select */
    for (mt = 0; mt <= 0xA; mt++) {
        const AtCssProfile *p = at_css_profile(mt);
        CHECK(p->group == 1 && p->max_humans == 4 && p->cpu_cards == 1 && p->teams_from_rules == 1);
        CHECK(p->min_to_start == 2 && p->has_sss == 1 && p->entering_port_only == 0 && p->online == 0);
    }
    /* Classic, Adventure, All-Star (0xB to 0xD): one player, no CPU cards, one fighter, no stage select */
    for (mt = 0xB; mt <= 0xD; mt++) {
        const AtCssProfile *p = at_css_profile(mt);
        CHECK(p->group == 2 && p->max_humans == 1 && p->cpu_cards == 0 && p->min_to_start == 1);
        CHECK(p->entering_port_only == 1 && p->has_sss == 0 && p->teams_from_rules == 0);
    }
    CHECK(at_css_profile(0xE)->group == 3 && at_css_profile(0xE)->entering_port_only == 1);               /* Event */
    for (mt = 0xF; mt <= 0x16; mt++) {                                                                      /* Stadium */
        const AtCssProfile *p = at_css_profile(mt);
        CHECK(p->group == 4 && p->max_humans == 1 && p->has_sss == 0 && p->entering_port_only == 1);
    }
    /* Training: the human plus the CPU dummy, with a stage select; it is in group 1 because it already runs on the kit */
    { const AtCssProfile *p = at_css_profile(0x17);
      CHECK(p->group == 1 && p->dummy_cpu == 1 && p->max_humans == 1 && p->has_sss == 1 && p->cpu_cards == 0 && p->min_to_start == 2); }
    /* the lobby: one card, one fighter is enough, no CPU, no teams */
    { const AtCssProfile *p = at_css_profile(AT_MT_LOBBY);
      CHECK(p->group == 5 && p->max_humans == 1 && p->min_to_start == 1 && p->cpu_cards == 0 && p->teams_from_rules == 0); }
    ATLAS_DONE("atlas profile");
}
```

Create `tools/port/test_css_profiles.py`, which keeps the C table and the game's enum from drifting (the table is a copy of facts in two places otherwise):

```python
"""The mode profile table must cover exactly the retail CSSMatchType enum: python tools/port/test_css_profiles.py"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")


class Profiles(unittest.TestCase):
    def test_enum_equals_table(self):
        types = open(os.path.join(GAME, "src", "melee", "mn", "types.h"), encoding="utf-8", errors="replace").read()
        body = re.search(r"typedef enum CSSMatchType \{(.*?)\} CSSMatchType;", types, re.S).group(1)
        enum_vals = sorted(int(v, 0) for v in re.findall(r"=\s*(0x[0-9A-Fa-f]+|\d+)", body))
        table = open(os.path.join(GAME, "pc", "platform", "gw_ui_css_profile.c"), encoding="utf-8").read()
        rows = sorted(int(v, 0) for v in re.findall(r"^\s*\{\s*(0x[0-9A-Fa-f]+|\d+)\s*,", table, re.M) if int(v, 0) != 0x40)
        self.assertEqual(enum_vals, rows)


if __name__ == "__main__":
    unittest.main()
```

Register `atlas-profile) sources=(pc/tests/atlas_profile_test.c pc/platform/gw_ui_css_profile.c) ;;` in `native_test.sh` and extend the die message. Run `nt atlas-profile` and `python tools/port/test_css_profiles.py`; expected: both fail (no header; no table).

- [ ] **Step 2: Write the minimal implementation.** `gw_ui_css_profile.h` is the interface block above plus `#ifndef GW_UI_CSS_PROFILE_H` guards and `extern "C"`. `gw_ui_css_profile.c`:

```c
/* gw_ui_css_profile.c - what each mode's character select is allowed to do. Pure C, no game types.
 * Columns: match_type, group, max_humans, cpu_cards, teams_from_rules, min_to_start, entering_port_only, dummy_cpu, has_sss, online, roster_filter. */
#include "gw_ui_css_profile.h"

static const AtCssProfile T[] = {
    /* VS family: gmVsMelee_CssData; Camera, Stamina, Sudden Death, Giant, Tiny, Invisible, Fixed Camera, Single Button, Lightning, Slo-Mo */
    { 0x0, 1, 4, 1, 1, 2, 0, 0, 1, 0, 0 }, { 0x1, 1, 4, 1, 1, 2, 0, 0, 1, 0, 0 }, { 0x2, 1, 4, 1, 1, 2, 0, 0, 1, 0, 0 },
    { 0x3, 1, 4, 1, 1, 2, 0, 0, 1, 0, 0 }, { 0x4, 1, 4, 1, 1, 2, 0, 0, 1, 0, 0 }, { 0x5, 1, 4, 1, 1, 2, 0, 0, 1, 0, 0 },
    { 0x6, 1, 4, 1, 1, 2, 0, 0, 1, 0, 0 }, { 0x7, 1, 4, 1, 1, 2, 0, 0, 1, 0, 0 }, { 0x8, 1, 4, 1, 1, 2, 0, 0, 1, 0, 0 },
    { 0x9, 1, 4, 1, 1, 2, 0, 0, 1, 0, 0 }, { 0xA, 1, 4, 1, 1, 2, 0, 0, 1, 0, 0 },
    /* one-player: Classic, Adventure, All-Star */
    { 0xB, 2, 1, 0, 0, 1, 1, 0, 0, 0, 0 }, { 0xC, 2, 1, 0, 0, 1, 1, 0, 0, 0, 0 }, { 0xD, 2, 1, 0, 0, 1, 1, 0, 0, 0, 0 },
    /* Event */
    { 0xE, 3, 1, 0, 0, 1, 1, 0, 0, 0, 0 },
    /* Stadium: Target Test, Home-Run, Multi-Man 10 and 100, 3-Minute, 15-Minute, Endless, Cruel */
    { 0xF, 4, 1, 0, 0, 1, 1, 0, 0, 0, 0 }, { 0x10, 4, 1, 0, 0, 1, 1, 0, 0, 0, 0 }, { 0x11, 4, 1, 0, 0, 1, 1, 0, 0, 0, 0 },
    { 0x12, 4, 1, 0, 0, 1, 1, 0, 0, 0, 0 }, { 0x13, 4, 1, 0, 0, 1, 1, 0, 0, 0, 0 }, { 0x14, 4, 1, 0, 0, 1, 1, 0, 0, 0, 0 },
    { 0x15, 4, 1, 0, 0, 1, 1, 0, 0, 0, 0 }, { 0x16, 4, 1, 0, 0, 1, 1, 0, 0, 0, 0 },
    /* Training: the human plus the CPU dummy */
    { 0x17, 1, 1, 0, 0, 2, 0, 1, 1, 0, 0 },
    /* the online lobby's pick (profile 'lobby'; not a retail value) */
    { 0x40, 5, 1, 0, 0, 1, 0, 0, 0, 1, 0 },
};

const AtCssProfile *at_css_profile(int match_type)
{
    int i;
    for (i = 0; i < (int) (sizeof T / sizeof T[0]); i++) if (T[i].match_type == match_type) return &T[i];
    return 0;
}
int at_css_profile_count(void) { return (int) (sizeof T / sizeof T[0]); }
const AtCssProfile *at_css_profile_at(int i) { return i >= 0 && i < (int) (sizeof T / sizeof T[0]) ? &T[i] : 0; }
```

Training's `has_sss = 1`: its states are `0` CSS, `1` SSS, `2` the match (`gmtrainingmode.c`); the LAB uses the VS data through `gmFrontend_ModeSelect` and so takes profile `0x0` with its own trail name (the adapter, Task 9). **If Task 0 step 4.1 found that `gm_801BA938` restricts the roster for Event, set `roster_filter = 1` on row `0xE` and add the check `CHECK(at_css_profile(0xE)->roster_filter == 1)`; Task 10c implements the filter.**

- [ ] **Step 3: Run.** `nt atlas-profile` expected `atlas profile: 45 checks, 0 failed` (count follows the loops); `python tools/port/test_css_profiles.py` expected `OK`.
- [ ] **Step 4: Commit.** Game repo: the header, the table, the test. Workspace repo: `test_css_profiles.py`, `native_test.sh`. Message `atlas step 4: the mode profile table, checked against the retail enum`.

---

### Task 3: The CSS model, moved out of `gmfrontend_select.inc` into pure C

The legacy rules in `fs_css_port` (read in full for this plan) are the oracle. They are **moved, not rewritten**: each rule is one named check in the test, written from the code before the code is moved. The legacy game-side file then calls the model, so the legacy drawing and the Atlas drawing run on the same rules while both exist (`MELEE_ATLAS=0` is a real fallback).

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_css.h`, `melee/pc/platform/gw_ui_css.c`, `melee/pc/tests/atlas_css_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-css`)

**Interfaces:**
Consumes: `AtCssProfile` (Task 2).
Produces:

```c
#define AT_CSS_MAX_SLOTS 130          /* 128 fighters (FS_MAX_FIGHTERS) and the Random tile */
enum { AT_CSS_OFF, AT_CSS_HMN, AT_CSS_CPU };
enum { AT_CK_NONE = -1, AT_CK_RANDOM = -2 };
/* input bits for one port and one frame: held-with-repeat directions and edge-triggered buttons (the legacy FsIn.rep and .trig) */
enum { AT_CI_LEFT = 1, AT_CI_RIGHT = 2, AT_CI_UP = 4, AT_CI_DOWN = 8, AT_CI_A = 16, AT_CI_B = 32, AT_CI_X = 64, AT_CI_Y = 128,
       AT_CI_Z = 256, AT_CI_L = 512, AT_CI_R = 1024, AT_CI_START = 2048 };
typedef struct { unsigned trig, rep; } AtCssIn;
/* what one step did, for the caller to turn into sound, toast and scene end */
enum { AT_CE_MOVE = 1, AT_CE_FORWARD = 2, AT_CE_BACK = 4, AT_CE_TOAST = 8, AT_CE_FINISH_GO = 16, AT_CE_FINISH_BACK = 32 };
typedef struct { int kind, ck, costume, cpu_lv, team, cur, card, target; } AtCssPort;   /* cur: an index into the visible list; card -1 = on the grid */
typedef struct AtCssOps {
    void *user;
    int (*costumes)(void *u, int ck);              /* how many costumes the fighter has (fs_costumes), at least 1 */
    int (*random_ck)(void *u, const struct AtCss *c);   /* a fighter for the Random tile (fs_random_ck) */
    int (*zelda_swap)(void *u, int ck);            /* the other of the Zelda/Sheik pair when Sheik shares Zelda's tile, else -1 */
    int (*sheik_ok)(void *u);                      /* online: the opponent has Sheik */
} AtCssOps;
typedef struct AtCss {
    const AtCssProfile *prof;
    int online, teams;
    int n_slots, ck[AT_CSS_MAX_SLOTS]; unsigned char ok[AT_CSS_MAX_SLOTS], tab_of[AT_CSS_MAX_SLOTS];   /* tab_of: 1 retail, 2 added */
    int tab;                                        /* 0 = all */
    int vis[AT_CSS_MAX_SLOTS], n_vis, cols;         /* the visible list for the tab, and the grid's columns (set by the caller) */
    AtCssPort p[4];
    int train_h, train_c;                           /* Training: the human port and the dummy's slot */
    int done, back_until; char toast[80];
    const AtCssOps *ops;
} AtCss;
void at_css_open(AtCss *c, const AtCssProfile *prof, const AtCssOps *ops, int online, int teams);
void at_css_set_roster(AtCss *c, int n, const int *ck, const unsigned char *ok, const unsigned char *tab_of);   /* the Random tile is added */
void at_css_set_tab(AtCss *c, int tab);            /* rebuilds vis; every cursor goes to the nearest visible tile */
void at_css_set_cols(AtCss *c, int cols);
unsigned at_css_step(AtCss *c, int port, AtCssIn in, int frame);              /* one port, one frame: AT_CE_* bits */
const char *at_css_blocker(const AtCss *c, char *buf, int cap);               /* NULL when the match can start */
int at_css_free_costume(const AtCss *c, int port, int ck, int from, int dir); /* fs_free_costume */
int at_css_count_in(const AtCss *c);
unsigned at_css_mouse_bits(const AtCss *c, int port, int slot, int card, int moved, int click, int rclick, int wheel);   /* fs_mouse_css without the hit test */
```

- [ ] **Step 1: Write the failing test, one check per legacy rule.** Create `pc/tests/atlas_css_test.c`. The fake ops give every fighter 4 costumes; Zelda is ck 19 and Sheik 20 in the fake, shared only when the roster has no 20.

```c
#include "atlas_check.h"
#include "../platform/gw_ui_css.h"

static int f_costumes(void *u, int ck) { (void) u; (void) ck; return 4; }
static int f_random(void *u, const AtCss *c) { (void) u; return c->n_slots > 0 ? c->ck[0] : 0; }
static int f_swap(void *u, int ck) { (void) u; return ck == 19 ? 20 : ck == 20 ? 19 : -1; }
static int f_sheik_ok(void *u) { (void) u; return 1; }
static const AtCssOps OPS = { 0, f_costumes, f_random, f_swap, f_sheik_ok };

static void fresh(AtCss *c, int match_type, int online, int teams, int n)
{
    int ck[130], i; unsigned char ok[130], tb[130];
    for (i = 0; i < n; i++) { ck[i] = i; ok[i] = 1; tb[i] = i < 26 ? 1 : 2; }
    at_css_open(c, at_css_profile(match_type), &OPS, online, teams);
    at_css_set_roster(c, n, ck, ok, tb);
    at_css_set_cols(c, 8);
}
static unsigned press(AtCss *c, int port, unsigned trig, unsigned rep, int frame) { AtCssIn in; in.trig = trig; in.rep = rep; return at_css_step(c, port, in, frame); }

/* ports: P1 is a human from the start; another controller joins on A or START (fs_css_port) */
static void ports_join(void)
{
    AtCss c; fresh(&c, 0x0, 0, 0, 29);
    CHECK(c.p[0].kind == AT_CSS_HMN && c.p[1].kind == AT_CSS_OFF);
    CHECK((press(&c, 1, AT_CI_A, 0, 10) & AT_CE_FORWARD) != 0 && c.p[1].kind == AT_CSS_HMN && c.p[1].target == 1);
    CHECK(c.p[2].kind == AT_CSS_OFF); press(&c, 2, AT_CI_B, 0, 11); CHECK(c.p[2].kind == AT_CSS_OFF);   /* a stray B does not join */
}
/* A picks the tile under the cursor for the port its picks go to; B undoes the pick; a second B within 150 frames leaves */
static void legacy_rules_pick_undo_back(void)
{
    AtCss c; unsigned e; fresh(&c, 0x0, 0, 0, 29);
    c.p[0].cur = 4;
    e = press(&c, 0, AT_CI_A, 0, 20); CHECK((e & AT_CE_FORWARD) && c.p[0].ck == 4);
    e = press(&c, 0, AT_CI_B, 0, 21); CHECK((e & AT_CE_BACK) && c.p[0].ck == AT_CK_NONE);
    e = press(&c, 0, AT_CI_B, 0, 22); CHECK((e & AT_CE_TOAST) && !(e & AT_CE_FINISH_BACK) && strcmp(c.toast, "Press B again to go back.") == 0);
    e = press(&c, 0, AT_CI_B, 0, 100); CHECK(e & AT_CE_FINISH_BACK);                                    /* inside 150 frames */
    fresh(&c, 0x0, 0, 0, 29);
    press(&c, 0, AT_CI_B, 0, 22); e = press(&c, 0, AT_CI_B, 0, 22 + 151); CHECK(!(e & AT_CE_FINISH_BACK));   /* outside: only the toast again */
}
/* down off the grid goes to the cards (never online); a CPU is added with A on an empty card and its fighter is picked next */
static void legacy_rules_cards(void)
{
    AtCss c; fresh(&c, 0x0, 0, 0, 29);
    c.p[0].cur = 24;                                    /* the last row of a 29-tile grid of 8 columns */
    press(&c, 0, 0, AT_CI_DOWN, 30); CHECK(c.p[0].card == 24 % 8 * 4 / 8);                           /* col * 4 / cols */
    c.p[0].card = 1;
    press(&c, 0, AT_CI_A, 0, 31); CHECK(c.p[1].kind == AT_CSS_CPU && c.p[1].ck == AT_CK_RANDOM && c.p[0].target == 1 && c.p[0].card == -1);
    c.p[0].cur = 7; press(&c, 0, AT_CI_A, 0, 32); CHECK(c.p[1].ck == 7 && c.p[0].target == 0);      /* the CPU got it, picks are yours again */
    c.p[0].card = 1; press(&c, 0, AT_CI_Z, 0, 33); CHECK(c.p[1].kind == AT_CSS_OFF && c.p[1].ck == AT_CK_NONE);   /* Z removes a CPU */
    fresh(&c, 0x0, 1, 0, 29); c.p[0].cur = 24; press(&c, 0, 0, AT_CI_DOWN, 34); CHECK(c.p[0].card == -1);   /* online: wraps, no cards */
}
/* costumes: X forward, Y back, never one another port wears */
static void legacy_rules_costume(void)
{
    AtCss c; fresh(&c, 0x0, 0, 0, 29);
    c.p[1].kind = AT_CSS_HMN; c.p[1].ck = 4; c.p[1].costume = 1;
    c.p[0].cur = 4; press(&c, 0, AT_CI_A, 0, 40); CHECK(c.p[0].ck == 4 && c.p[0].costume == 0);
    press(&c, 0, AT_CI_X, 0, 41); CHECK(c.p[0].costume == 2);                                           /* 1 is taken by P2 */
    press(&c, 0, AT_CI_Y, 0, 42); CHECK(c.p[0].costume == 0);
}
/* Start: blocked with a reason until every human has a fighter and two fighters are in (one online) */
static void legacy_rules_start(void)
{
    AtCss c; char b[96]; unsigned e; fresh(&c, 0x0, 0, 0, 29);
    CHECK(at_css_blocker(&c, b, sizeof b) != NULL && strcmp(b, "P1: pick a fighter.") == 0);
    e = press(&c, 0, AT_CI_START, 0, 50); CHECK((e & AT_CE_TOAST) && !(e & AT_CE_FINISH_GO));
    c.p[0].ck = 3; CHECK(strcmp(at_css_blocker(&c, b, sizeof b), "Two fighters needed: pick one, or add a CPU below.") == 0);
    c.p[1].kind = AT_CSS_CPU; c.p[1].ck = 5; CHECK(at_css_blocker(&c, b, sizeof b) == NULL);
    e = press(&c, 0, AT_CI_START, 0, 51); CHECK(e & AT_CE_FINISH_GO);
}
/* the profiles: one player (Classic) has no CPU cards and starts with one fighter; Training has the dummy */
static void profile_rules(void)
{
    AtCss c; char b[96]; fresh(&c, 0xB, 0, 0, 29);
    c.p[0].ck = 3; CHECK(at_css_blocker(&c, b, sizeof b) == NULL);                                       /* min_to_start 1 */
    c.p[0].cur = 24; press(&c, 0, 0, AT_CI_DOWN, 60); CHECK(c.p[0].card == 0);                           /* col 0 would be card 0 anyway: use a right-hand column next */
    c.p[0].card = -1; c.p[0].cur = 23; press(&c, 0, 0, AT_CI_DOWN, 61); CHECK(c.p[0].card == 0);          /* col 7 would be card 3 in the VS family: one player has only its own */
    c.p[0].card = 1; press(&c, 0, AT_CI_A, 0, 62); CHECK(c.p[1].kind == AT_CSS_OFF);                      /* no CPU can be added */
    fresh(&c, 0x17, 0, 0, 29);
    CHECK(c.p[c.train_c].kind == AT_CSS_CPU && c.p[c.train_c].ck == AT_CK_RANDOM);
}
/* Zelda and Sheik share a tile: A on the tile again swaps them */
static void legacy_rules_zelda(void)
{
    AtCss c; fresh(&c, 0x0, 0, 0, 19 + 1);              /* ck 0..19: Zelda (19) present, Sheik (20) absent: they share */
    c.p[0].cur = 19; press(&c, 0, AT_CI_A, 0, 70); CHECK(c.p[0].ck == 19);
    press(&c, 0, AT_CI_A, 0, 71); CHECK(c.p[0].ck == 20);
    press(&c, 0, AT_CI_A, 0, 72); CHECK(c.p[0].ck == 19);
}
/* tabs: switching rebuilds the visible list; a tab with no tiles is not offered; the Random tile ends every tab */
static void tabs_visible(void)
{
    AtCss c; fresh(&c, 0x0, 0, 0, 29);
    CHECK(c.n_vis == 30);                               /* 29 and Random */
    at_css_set_tab(&c, 1); CHECK(c.n_vis == 27);        /* 26 retail and Random */
    at_css_set_tab(&c, 2); CHECK(c.n_vis == 4);         /* 3 added and Random */
    fresh(&c, 0x0, 0, 0, 26); at_css_set_tab(&c, 2); CHECK(c.n_vis == 1);   /* no added fighters: only Random; the caller hides the tab */
}
/* a port that loses its controller mid-screen: its cursor and card are dropped, nothing indexes past the list */
static void ports_leave(void)
{
    AtCss c; fresh(&c, 0x0, 0, 0, 29);
    c.p[2].kind = AT_CSS_HMN; c.p[2].cur = 29; at_css_set_tab(&c, 2);
    CHECK(c.p[2].cur >= 0 && c.p[2].cur < c.n_vis);
    press(&c, 2, 0, AT_CI_RIGHT, 80); CHECK(c.p[2].cur >= 0 && c.p[2].cur < c.n_vis);
}
/* the lobby profile: one card; nothing but port 1 plays; a fighter the opponent lacks cannot be picked */
static void lobby_rules(void)
{
    AtCss c; unsigned e; fresh(&c, AT_MT_LOBBY, 1, 0, 29);
    c.ok[5] = 0;
    c.p[0].cur = 5; e = press(&c, 0, AT_CI_A, 0, 90); CHECK((e & AT_CE_BACK) && c.p[0].ck == AT_CK_NONE && strstr(c.toast, "opponent") != NULL);
    CHECK((press(&c, 1, AT_CI_A, 0, 91) & AT_CE_FORWARD) == 0 && c.p[1].kind == AT_CSS_OFF);
}
int main(void)
{
    ports_join(); legacy_rules_pick_undo_back(); legacy_rules_cards(); legacy_rules_costume(); legacy_rules_start();
    profile_rules(); legacy_rules_zelda(); tabs_visible(); ports_leave(); lobby_rules();
    ATLAS_DONE("atlas css");
}
```

Two points the engineer must check against `fs_css_port` while making these pass, because the test was written from the code and not run: in `fs_css_port` the join rule triggers for any port whose `kind != FS_HMN` on A or START (so `START` joins too: add `CHECK` for it), and in the lobby (`fcs.online`) every other controller's presses are folded into port 0's input (`in.trig |= o.trig`): the model leaves that fold to the adapter (it ORs the other ports' bits before calling `at_css_step(c, 0, ...)`); `lobby_rules` above therefore expects port 1 to do nothing.

Register `atlas-css) sources=(pc/tests/atlas_css_test.c pc/platform/gw_ui_css.c pc/platform/gw_ui_css_profile.c) ;;`. Run `nt atlas-css`; expected: fails to compile (`gw_ui_css.h` missing).

- [ ] **Step 2: Write the model.** `gw_ui_css.h` is the interface block above with guards. `gw_ui_css.c` moves `fs_css_open`'s per-port setup (without the CSSData reads, which stay in the adapter), `fs_css_port`, `fs_css_blocker`, `fs_pick`, `fs_free_costume`, `fs_count_in`, `fs_mouse_css`'s decisions. The heart, from `fs_css_port` (the grid is now `vis[]` and `cols` instead of pages; every other line is the legacy rule):

```c
unsigned at_css_step(AtCss *c, int port, AtCssIn in, int frame)
{
    AtCssPort *s = &c->p[port];
    unsigned ev = 0;
    int cols = c->cols > 0 ? c->cols : 1, n = c->n_vis, cur;
    if (c->done || n <= 0) return 0;
    if (c->online && port != 0) return 0;                       /* the adapter folds the other controllers into port 0 */
    if (c->prof->dummy_cpu && port != c->train_h) return 0;     /* Training: the human's input only */
    if (s->kind != AT_CSS_HMN) {
        if (!c->online && c->prof->max_humans > 1 && (in.trig & (AT_CI_A | AT_CI_START))) { s->kind = AT_CSS_HMN; s->target = port; s->card = -1; ev |= AT_CE_FORWARD; }
        return ev;
    }
    if (s->cur < 0 || s->cur >= n) s->cur = 0;
    if (s->card < 0) {
        int row = s->cur / cols, col = s->cur % cols, last_row = (n - 1) / cols;
        if (in.rep & AT_CI_LEFT) col = col == 0 ? cols - 1 : col - 1;
        else if (in.rep & AT_CI_RIGHT) col = col == cols - 1 ? 0 : col + 1;
        else if (in.rep & AT_CI_UP) row = row == 0 ? last_row : row - 1;
        else if (in.rep & AT_CI_DOWN) {
            if (row + 1 > last_row || (row + 1) * cols + col >= n) {
                if (!c->online) { s->card = (c->prof->max_humans == 1 && !c->prof->cpu_cards && !c->prof->dummy_cpu) ? port : col * 4 / cols; return ev | AT_CE_MOVE; }   /* one player: only the own card exists */
                row = 0;
            } else row++;
        }
        if (row * cols + col >= n) { col = n - 1 - row * cols; if (col < 0) { row = 0; col = 0; } }
        cur = row * cols + col;
        if (cur != s->cur) ev |= AT_CE_MOVE;
        s->cur = cur;
        if (in.trig & AT_CI_A) ev |= at_css_pick(c, port, c->vis[s->cur]);
        else if (in.trig & (AT_CI_X | AT_CI_Y)) {
            AtCssPort *t = &c->p[s->target];
            if (t->ck >= 0) { int dir = (in.trig & AT_CI_X) ? 1 : -1; t->costume = at_css_free_costume(c, s->target, t->ck, t->costume + dir, dir); ev |= AT_CE_MOVE; }
        } else if (in.trig & AT_CI_B) {
            ev |= AT_CE_BACK;
            if (s->target != port) s->target = port;
            else if (s->ck != AT_CK_NONE) s->ck = AT_CK_NONE;
            else if (frame < c->back_until) ev |= AT_CE_FINISH_BACK;
            else { c->back_until = frame + 150; snprintf(c->toast, sizeof c->toast, "%s", "Press B again to go back."); ev |= AT_CE_TOAST; }
        }
    } else {
        /* on the cards: the legacy block, line for line (left/right cycle four cards, up returns to the bottom row under the card,
         * A adds or picks a CPU, X/Y step a CPU's level or your costume, Z removes a CPU or leaves, B returns to the grid) */
        ev |= at_css_card_step(c, port, in);
    }
    if ((in.trig & AT_CI_START) && !c->done) {
        char buf[96]; const char *why = at_css_blocker(c, buf, sizeof buf);
        if (why == NULL) { ev |= AT_CE_FORWARD | AT_CE_FINISH_GO; c->done = 1; }
        else { snprintf(c->toast, sizeof c->toast, "%s", why); ev |= AT_CE_BACK | AT_CE_TOAST; }
    }
    return ev;
}
```

In a one-player profile the legacy behaviour "down off the grid goes onto the cards" lands on the **own card only** (the other three cards do not exist there; `profile_rules` pins it). Write `at_css_pick` as `fs_pick` (including the Zelda/Sheik swap through `ops->zelda_swap`, and `AT_CE_BACK` plus the toast `"Your opponent doesn't have this fighter - pick another."` for an unavailable slot), `at_css_card_step` as the legacy `else` block with `fcs.training`/`fcs.online` replaced by the profile flags, `at_css_free_costume` as `fs_free_costume`, `at_css_blocker` as `fs_css_blocker` with `min_to_start` in place of `(fcs.online ? 1 : 2)`, and `at_css_open` as the port setup of `fs_css_open` (Training: human `train_h`, CPU dummy `train_c`, the dummy's fighter `AT_CK_RANDOM` when none).

- [ ] **Step 3: Run until every check passes.** `nt atlas-css`. Expected `atlas css: N checks, 0 failed`. When a legacy rule and a check disagree, **the legacy code wins** (it ships and was played): change the check, and note the correction in the commit message.
- [ ] **Step 4: Guard greps** (the model must stay pure, must not touch netplay, and its **headers must include no libc header**: game-side files include them and the PowerPC syntax check runs with `-nostdinc`):

```bash
cd "$GW_MELEE" && ! grep -n "netplay\|Netplay\|HSD_\|gm_\|#include <melee" pc/platform/gw_ui_css*.c pc/platform/gw_ui_css*.h && echo "model is pure"
! grep -n "#include <" pc/platform/gw_ui_css.h pc/platform/gw_ui_css_profile.h pc/platform/gw_ui_sss.h && echo "headers are libc-free"
```

Expected: both OK lines. (`snprintf` and `strlen` belong in the `.c` files only.)
- [ ] **Step 5: Commit.** Game repo: the model and its test. Workspace repo: `native_test.sh`. Message `atlas step 4: the CSS model in pure C, one test per legacy rule (moved from fs_css_port)`.

---

### Task 4: Screen record additions: tabs, a band, per-port cursors, native cell storage, image fields

Step 1's record has 12 cells per block, one focus, no tabs and no image on a cell. The CSS needs up to 129 tiles, the SSS up to 256, four cursors, tabs and a strip of port cards. This task adds them **without changing what the Lua door accepts** (12 cells per block stays the documented limit) and without a pointer that can outlive its storage.

**Files:**
- Modify (game repo): `melee/pc/platform/gw_ui_screen.h`, `gw_ui_screen.c`, `gw_ui_layout.h`, `gw_ui_layout.c`, `gw_ui_focus.h` (only if a cursor type is needed), `melee/pc/tests/atlas_screen_test.c`, `atlas_layout_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` if a test needs a source it did not link before

**Interfaces:**
Consumes: Task 1's style checks (not yet), step 1's `AtScreen`, `AtBlock`, `AtCell`, `AtView`, `AtLayout`.
Produces:

```c
/* gw_ui_screen.h */
#define AT_MAX_CELLS 12                 /* the Lua door's limit, unchanged (documented in scripting.md) */
#define AT_MAX_EXT_CELLS 256            /* a native grid block's capacity (stages: 256) */
#define AT_MAX_TABS 6
#define AT_MAX_CURSORS 4
typedef struct { char name[24]; int count; } AtTab;
typedef struct { char id[AT_ID]; char name[AT_STR]; int model, ring, tex; unsigned flags; int index, pips; char origin; unsigned rgba; char letter; char abbr[3]; } AtCell;   /* + tex, abbr */
enum { AT_CELL_BANNED = 64, AT_CELL_PICKED = 128, AT_CELL_UNSET = 256, AT_CELL_P1 = 512 };                                   /* strike marks: drawing only, step 6 sets them */
/* AtBlock gains: AtCell *ext; int ext_n;   (ext non-NULL: the cells live in adapter-owned storage and cells[] is unused) */
const AtCell *at_block_cell(const AtBlock *b, int i);   /* the ONE accessor: ext when set, else cells[] */
int at_block_count(const AtBlock *b);
/* AtScreen gains: */
AtTab tabs[AT_MAX_TABS]; int n_tabs;   /* 0 = none; the active tab is in AtView */
int band;                              /* AT_BAND_NONE, AT_BAND_CARDS, AT_BAND_MATCHUP */
typedef struct { int port, kind /* OFF HMN CPU */, ck_tex, cur; char name[AT_STR], sub[AT_STR]; unsigned flags; char abbr[3]; int cpu_lv, team; } AtPortCard;   /* flags: open, closed, ready, focus */
AtPortCard cards[4];
int grid_cols_auto;                    /* 1: the renderer picks the columns (at_grid_cols) */
/* AtView gains: */
struct { int active, block, index, card; } cursor[AT_MAX_CURSORS]; int tab; int progress /* 0..1000, the loading bar */;
/* AtExplainer gains: */ int media_tex; char media_abbr[3]; char stepper_label[16], stepper_text[24]; int stepper; char with_tag[AT_MAX_WITH][20]; int n_with_tag;
int at_screen_copy(AtScreen *dst, const AtScreen *src);   /* 1 copied; refuses (0) when any block has ext set: native screens are never copied */
void at_screen_clear_ext(AtScreen *s);
/* gw_ui_layout.h */
typedef struct { AtRect tabs, grid, band; } AtSplit;
void at_layout_split(const AtLayout *L, int has_tabs, int band, AtSplit *out);
int at_grid_cols(float width, float min_cell, float max_cell, float gap);
```

- [ ] **Step 1: Write the failing tests.** Add to `pc/tests/atlas_screen_test.c` (it already includes `gw_ui_screen.h`):

```c
static void ext_cells_never_copied(void)
{
    static AtScreen a, b; static AtCell pool[AT_MAX_EXT_CELLS];
    int i;
    memset(&a, 0, sizeof a); memset(pool, 0, sizeof pool);
    a.primary = AT_PRIMARY_GRID; a.n_blocks = 1; a.blocks[0].ext = pool; a.blocks[0].ext_n = 200;
    CHECK(at_block_count(&a.blocks[0]) == 200);
    CHECK(at_block_cell(&a.blocks[0], 199) == &pool[199] && at_block_cell(&a.blocks[0], 200) == NULL && at_block_cell(&a.blocks[0], -1) == NULL);
    CHECK(at_screen_copy(&b, &a) == 0);                             /* a native screen is never copied: the pointer would outlive the pool */
    at_screen_clear_ext(&a); CHECK(a.blocks[0].ext == NULL && at_block_count(&a.blocks[0]) == 0);
    a.blocks[0].n = 3; CHECK(at_screen_copy(&b, &a) == 1 && b.blocks[0].n == 3);  /* an inline screen copies */
    (void) i;
}
static void lua_door_unchanged(void)
{
    /* a Lua description with 13 cells in one block is still refused, with the old message (documented limit 12) */
    char err[160]; AtScreen s; AtvArena *ar = A;
    int sc = bag("x.big"), bk = atv_at(ar, atv_get(ar, atv_get(ar, sc, "primary"), "blocks"), 1), cells = atv_get(ar, bk, "cells"), i;
    for (i = 0; i < 13; i++) { char id[16]; snprintf(id, sizeof id, "c%d", i); atv_push(ar, cells, cell(id, "N", -1, 0, 0)); }
    CHECK(at_screen_from_val(ar, sc, "x", &s, err, sizeof err) == 0 && strstr(err, "12") != NULL);
}
static void tabs_and_cursors(void)
{
    AtView v; at_view_init(&v);
    CHECK(v.tab == 0 && v.cursor[0].active == 0 && v.cursor[3].active == 0 && v.progress == 0);
}
```

and in `atlas_layout_test.c`:

```c
static void split_and_cols(void)
{
    AtLayout L; AtSplit sp;
    at_layout(640.0f, AT_PRESET_NORMAL, &L);
    at_layout_split(&L, 1, 1 /* AT_BAND_CARDS */, &sp);
    CHECK(sp.tabs.h == 30.0f && sp.tabs.y == L.primary.y);
    CHECK(sp.band.h == 56.0f && sp.band.y + sp.band.h <= 428.0f + 0.01f);                  /* inside the body, above the keys */
    CHECK(sp.grid.y >= sp.tabs.y + sp.tabs.h && sp.grid.y + sp.grid.h <= sp.band.y - 12.0f + 0.01f);
    CHECK(sp.grid.x == L.primary.x && sp.grid.w == L.primary.w);
    at_layout_split(&L, 0, 0, &sp); CHECK(sp.tabs.h == 0.0f && sp.band.h == 0.0f && sp.grid.h == L.primary.h);
    /* columns: the cell size stays between min and max; wider windows give more columns, never bigger cells */
    CHECK(at_grid_cols(344.0f, 36.0f, 56.0f, 8.0f) == 8);                                     /* 640 wide, normal explainer: the mockup's 8 */
    CHECK(at_grid_cols(344.0f, 36.0f, 56.0f, 8.0f) <= at_grid_cols(700.0f, 36.0f, 56.0f, 8.0f));
    CHECK(at_grid_cols(10.0f, 36.0f, 56.0f, 8.0f) == 1);                                      /* never zero */
}
```

Add `split_and_cols();` to `main` of each. Run `nt atlas-screen` and `nt atlas-layout`; expected: compile errors (`ext`, `at_block_count`, `at_layout_split` missing).

- [ ] **Step 2: Implement.** In `gw_ui_screen.h` apply the interface block. Three rules of the implementation, each a past or likely bug:
  1. **One accessor.** Every read of `blocks[b].cells[i]` in `gw_ui_screen.c`, `gw_ui_focus` glue, `gw_ui_render.c` and `gw_script_ui.inc` becomes `at_block_cell(&sc->blocks[b], i)` and every `.n` read for a native-capable block becomes `at_block_count(...)`. `at_screen_focus_blocks` builds its `AtFocusBlock` array from `at_block_count`.
  2. **`at_screen_copy`** refuses when any `blocks[b].ext != NULL`. The binding's slot assignment (`gs->screens[i] = parsed` style code, found with `grep -n "memcpy\|= \*sc\|sizeof(AtScreen)\|sizeof \*" pc/platform/gw_script_ui.inc`) must use it, so a native screen cannot be copied by accident; Lua-converted screens never set `ext`.
  3. **`at_layout_split`**: tabs strip 30 high at the top of `L.primary` when `has_tabs`; the band (56 high for `AT_BAND_CARDS`, 40 for `AT_BAND_MATCHUP`) at the bottom of the body with a 12 px gap above it; the grid gets the rest. `at_grid_cols(width, min_cell, max_cell, gap)` returns `max(1, floor((width + gap) / (min_cell + gap)))` and then reduces the count while the resulting cell (`(width - (n-1)*gap)/n`) would exceed `max_cell`... **increase** the count instead until the cell is at most `max_cell` (a wider window gives more columns, never bigger cells).
- [ ] **Step 3: Guard greps.**

```bash
cd "$GW_MELEE" && ! grep -n "\.cells\[" pc/platform/gw_ui_render.c pc/platform/gw_ui_focus.c pc/platform/gw_script_ui.inc && echo "no direct cell reads outside the accessor"
grep -n "\.cells\[" pc/platform/gw_ui_screen.c
```

Expected: the first prints the OK line; the second lists only the accessor and the conversion that fills inline cells.
- [ ] **Step 4: Run.** `nt atlas-screen`, `nt atlas-layout`, `nt atlas-render`, `nt atlas-binding`, `lua pc/tests/atlas_ui_stub_test.lua | tail -1`. Expected: all pass, **including the unchanged step 1 tests** (the Lua door's 12-cell limit and every old check).
- [ ] **Step 5: Commit.** Game repo, message `atlas step 4: the screen record gains tabs, a band, four cursors, native cell storage and image fields; the Lua door is unchanged`.

---

### Task 5: Parts: the `image` op, the port card, the matchup strip, per-port brackets, tabs in the render

**Files:**
- Modify (game repo): `melee/pc/platform/gw_ui_parts.h`, `gw_ui_parts.c`, `gw_ui_render.c`, `melee/pc/tests/atlas_rec.h`, `atlas_parts_test.c`, `atlas_render_test.c`
- Modify (game repo, binding): `melee/pc/platform/gw_script_ui.inc` (the host sink gets `image`, or sets it to NULL)

**Interfaces:**
Consumes: Task 1 (`atlas_style.h`), Task 4 (`AtPortCard`, `AtTab`, `AtCell.tex`).
Produces:

```c
/* AtSink gains (a NULL op draws nothing; every constructor sets it or leaves it NULL, and callers go through at_sink_image) */
void (*image)(void *u, int tex, float x, float y, float w, float h, unsigned rgba);
void at_sink_image(const AtSink *s, int tex, float x, float y, float w, float h, unsigned rgba);
void at_part_port_card(const AtSink *s, const AtTextOps *o, AtRect r, const AtPortCard *c, int focus);
int  at_port_mark(const AtSink *s, float cx, float cy, float r, int port, unsigned rgba);   /* the shape: returns the polys used (circle 3, square 1, hexagon 3, diamond 2) */
void at_part_matchup(const AtSink *s, const AtTextOps *o, AtRect r, const AtPortCard *c, int n, int picker);
void at_cell_brackets(const AtSink *s, AtRect r, unsigned rgba, int slot, int of);        /* four registration brackets; slot/of offsets several ports on one cell */
/* at_part_cell: draws cell->tex as an image inside the cell when tex >= 0, else the name plate; abbr + flat frame + "DISC ART" word when neither */
```

- [ ] **Step 1: Write the failing tests** in `pc/tests/atlas_parts_test.c` (it includes `atlas_rec.h`; add `#define AT_SINK_HAS_IMAGE` before including it, and `#include "atlas_style.h"`):

```c
static const AtTextOps O = { fake_width, NULL };

static void sink_without_image_is_safe(void)
{
    AtSink s = rec_sink(); AtCell c; AtRect r = { 40, 100, 40, 40 };
    memset(&c, 0, sizeof c); c.model = AT_NO_MODEL; c.tex = 7; snprintf(c.abbr, sizeof c.abbr, "%s", "FO");
    s.image = NULL;                                                   /* a sink with no image op (the host sink before Task 11 sets one) */
    at_part_cell(&s, &O, r, &c, AT_ST_REST, AT_C_P1);                /* must not crash and must fall back to the abbreviation */
    CHECK(find_text("FO") != NULL);
}
static void image_cell(void)
{
    AtSink s = rec_sink(); AtCell c; AtRect r = { 40, 100, 40, 40 };
    memset(&c, 0, sizeof c); c.model = AT_NO_MODEL; c.tex = 7; snprintf(c.abbr, sizeof c.abbr, "%s", "FO");
    at_part_cell(&s, &O, r, &c, AT_ST_REST, AT_C_P1);
    CHECK(REC.ni == 1 && REC.im[0].tex == 7);
    CHECK(REC.im[0].x >= r.x && REC.im[0].y >= r.y && REC.im[0].x + REC.im[0].w <= r.x + r.w + 0.01f && REC.im[0].y + REC.im[0].h <= r.y + r.h + 0.01f);   /* inside the cell */
    c.tex = -1;                                                       /* no art: the frame, the abbreviation and the word */
    { AtSink s2 = rec_sink(); at_part_cell(&s2, &O, r, &c, AT_ST_REST, AT_C_P1); CHECK(REC.ni == 0 && find_text("FO") != NULL); }
}
static void cell_style(void)
{
    AtSink s; AtCell c; AtRect r = { 40, 100, 40, 40 }; StySig a, b;
    memset(&c, 0, sizeof c); c.model = AT_NO_MODEL; snprintf(c.abbr, sizeof c.abbr, "%s", "FO"); c.tex = -1;
    s = rec_sink(); at_poly_rect(&s, 0, 0, 640, 480, AT_C_PLATE); at_part_cell(&s, &O, r, &c, AT_ST_REST, AT_C_P1);
    CHECK(sty_chamfer(r, 3.0f, AT_C_PLATE) == 0);                    /* the cell's 3 px chamfers show the pane under it */
    CHECK(sty_text_inside(r, 0) == -1);
    s = rec_sink(); at_part_cell(&s, &O, r, &c, AT_ST_REST, AT_C_P1); a = sty_sig(0);
    s = rec_sink(); at_part_cell(&s, &O, r, &c, AT_ST_FOCUS, AT_C_P1); b = sty_sig(0);
    CHECK(sty_focus_cues(a, b) == 3);
    c.flags = AT_CELL_LOCKED; s = rec_sink(); at_part_cell(&s, &O, r, &c, AT_ST_DISABLED, AT_C_P1);
    CHECK(find_text("FO") != NULL && texts_legible());                /* disabled is hatched or worded, not only dimmed */
}
static void port_cards(void)
{
    AtSink s; AtPortCard pc[4]; AtRect r = { 32, 372, 140, 56 }; int n[4], p;
    memset(pc, 0, sizeof pc);
    for (p = 0; p < 4; p++) {
        pc[p].port = p; pc[p].kind = 1; snprintf(pc[p].name, sizeof pc[p].name, "%s", "SORA"); snprintf(pc[p].sub, sizeof pc[p].sub, "Costume 1");
        snprintf(pc[p].abbr, sizeof pc[p].abbr, "%s", "SO");
        s = rec_sink(); at_poly_rect(&s, 0, 0, 640, 480, AT_C_GROUND);
        { int before = REC.np; at_part_port_card(&s, &O, r, &pc[p], 0); n[p] = REC.np - before; }
        CHECK(sty_chamfer(r, 5.0f, AT_C_GROUND) == 0);
        CHECK(sty_text_inside(r, 0) == -1);
        CHECK(find_text("SORA") != NULL);
    }
    { int shape[4]; for (p = 0; p < 4; p++) { AtSink s2 = rec_sink(); shape[p] = at_port_mark(&s2, 50, 50, 12, p, AT_C_P1 + 0); } CHECK(sty_shapes_distinct(shape) == 1); }
    /* every port's numeral is drawn (colour is never the only signal) */
    { char want[2] = { 0, 0 }; for (p = 0; p < 4; p++) { AtSink s2 = rec_sink(); want[0] = (char) ('1' + p); at_part_port_card(&s2, &O, r, &pc[p], 0); CHECK(find_text(want) != NULL); } }
    /* CPU: the word CPU, the grey colour, and a cpu level */
    pc[1].kind = 2; pc[1].cpu_lv = 9; { AtSink s2 = rec_sink(); at_part_port_card(&s2, &O, r, &pc[1], 0); CHECK(find_text("CPU") != NULL); }
    /* an open slot and a closed one say so in words */
    pc[2].kind = 0; { AtSink s2 = rec_sink(); at_part_port_card(&s2, &O, r, &pc[2], 0); CHECK(find_text("OPEN") != NULL); }
}
static void two_cursors_one_cell(void)
{
    AtSink s = rec_sink(); AtRect r = { 40, 100, 40, 40 };
    at_cell_brackets(&s, r, AT_C_P1, 0, 2); at_cell_brackets(&s, r, AT_C_P2, 1, 2);
    CHECK(count_color(AT_C_P1) == 8 && count_color(AT_C_P2) == 8);          /* four brackets of two strokes each, per port */
    /* the two sets must not sit on top of each other: their bounding boxes differ */
    { float a = REC.p[0].x[0], b = REC.p[8].x[0]; CHECK(a != b); }
}
```

Add the matching calls to `main`. In `atlas_render_test.c` add the tab strip and band checks:

```c
static void tabs_and_band_render(void)
{
    /* a native-style screen: 29 cells in one block, 3 tabs, the cards band */
    static AtScreen sc; static AtView v; static AtCell pool[AT_MAX_EXT_CELLS]; AtSink s; AtHits hits; int i;
    memset(&sc, 0, sizeof sc); at_view_init(&v); memset(pool, 0, sizeof pool);
    sc.primary = AT_PRIMARY_GRID; sc.preset = AT_PRESET_NORMAL; sc.n_blocks = 1; sc.grid_cols_auto = 1; sc.band = AT_BAND_CARDS;
    sc.blocks[0].ext = pool; sc.blocks[0].ext_n = 29; sc.blocks[0].cols = 0;
    snprintf(sc.title, sizeof sc.title, "%s", "FIGHTERS");
    sc.n_tabs = 3; snprintf(sc.tabs[0].name, 24, "ALL"); sc.tabs[0].count = 29; snprintf(sc.tabs[1].name, 24, "RETAIL"); sc.tabs[1].count = 26; snprintf(sc.tabs[2].name, 24, "ADDED"); sc.tabs[2].count = 3;
    for (i = 0; i < 29; i++) { snprintf(pool[i].id, AT_ID, "f%d", i); pool[i].model = AT_NO_MODEL; pool[i].tex = -1; snprintf(pool[i].abbr, 3, "%c%c", 'A' + i % 26, 'A' + (i / 3) % 26); }
    for (i = 0; i < 4; i++) { sc.cards[i].port = i; sc.cards[i].kind = i == 0 ? 1 : 0; }
    s = rec_sink(); at_render(&sc, &v, 640.0f, 1000.0, 1, &O, &s, &hits);
    CHECK(find_text("ALL") != NULL && find_text("RETAIL") != NULL && find_text("ADDED") != NULL);
    CHECK(texts_legible());
    { int cells = 0; for (i = 0; i < hits.n; i++) cells += hits.h[i].kind == AT_HIT_CELL; CHECK(cells == 29); }   /* 29 fighters fit at 640 without scrolling (the mockup) */
    for (i = 0; i < hits.n; i++) if (hits.h[i].kind == AT_HIT_CELL) { CHECK(hits.h[i].r.y + hits.h[i].r.h <= 428.0f - 56.0f - 12.0f + 0.5f); }   /* above the band */
}
```

Run `nt atlas-parts` and `nt atlas-render`; expected: compile failures (`image`, `at_port_mark`, ...).

- [ ] **Step 2: Implement.**
  1. Add the `image` field to `AtSink` and `at_sink_image` (`if (s->image != NULL && tex >= 0) s->image(...)`). Update **every** `AtSink` constructor: the render's counting wrapper (`cs.image = cnt_image`, which counts one entry and forwards through `at_sink_image`), the host sink in `gw_script_ui.inc` (calls `gw_Kit_DrawImage`, or is left NULL until Task 7), and every test sink. `grep -n "AtSink" pc/platform pc/tests -r` lists them; an `AtSink s;` that is not fully initialised must be `memset` first.
  2. `at_part_cell`: when `c->tex >= 0` and the sink has an image op, draw the texture inside the cell's inner rect (keep aspect: icons are 64x56) and nothing else but the focus cues, the port tag and the index; otherwise draw the flat frame (`AT_C_PLATE2` face, 3 px edge, chamfers 3 on TL and BR), the abbreviation in `AT_R_CAP14` centred, and the word `DISC ART` in `AT_R_CAP12` only when the cell is at least 44 px wide (it does not fit under 12 px below that, and a smaller word would break the 12 px floor).
  3. `at_port_mark(port)`: circle for 0 (`at_disc`, 3 quads), square for 1 (1 quad), hexagon for 2 (3 quads: a rectangle and two triangles drawn as degenerate quads), diamond for 3 (2 quads). The shapes differ in poly count only if the numbers above are kept: the test `sty_shapes_distinct` depends on it; if the hexagon needs 3 quads and the circle 3, give the circle a fourth (an inner cut) rather than weaken the check.
  4. `at_part_port_card`: 56 high, 3 px top edge in the port colour, chamfers 5 on TL and BR, the mark and numeral at the left, the name in `AT_R_ROW16` and the sub line in `AT_R_BODY12`, all clipped with `max_w`; a CPU card is hatched grey (flat `AT_C_CPU` tone plus the word `CPU` in a tag, never colour alone); an open slot says `OPEN` and `Press A to join` is a hint line only when the card is focused and wide enough; a closed slot (online or Training) says `CLOSED`.
  5. `at_cell_brackets(r, rgba, slot, of)`: four L-shaped brackets (2 thin quads each = 8) inset by `2 + 3 * slot` px so `of` ports on one cell do not draw on top of each other.
  6. In `at_render_ex`: draw the tab strip with `at_part_tabs` (existing) from `sc->tabs`/`v->tab` when `sc->n_tabs > 0`; use `at_layout_split` for the grid and band rectangles; for a grid with `grid_cols_auto`, call `at_grid_cols(grid.w - 24, 36, 56, 8)` (the CSS) once per frame; draw `sc->cards` through `at_part_port_card` in four equal columns of the band, or the matchup strip; draw one bracket set per active cursor in its port colour; cull rows that are not visible (the step 1 pass already does; add the check below).
- [ ] **Step 3: Run.** `nt atlas-parts`, `nt atlas-render`, `nt atlas-binding`, and the step 1 baselines. Expected: pass. If `cell_style`'s `sty_focus_cues` is below 3 for the existing cell, read Task 1 step 4.
- [ ] **Step 4: Commit.** Game repo, message `atlas step 4: image cells, the port card, the matchup strip, per-port brackets, tabs and a band in the render`.

---
### Task 6: The CSS screen at three widths with real roster sizes

Composes tabs, grid, explainer, cards band and keys for the CSS from the model's view, and proves layout, budget and style **without the game**, with the rosters the spec names (26, 29, 60) plus the 128-fighter limit of `FS_MAX_FIGHTERS`.

**Files:**
- Create (game repo): `melee/pc/tests/atlas_select_render_test.c`
- Modify (game repo): `melee/pc/platform/gw_ui_render.c` (only what the test shows is missing)
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-select-render`)

**Interfaces:**
Consumes: Tasks 1, 4, 5 and the model's tab and port data (Task 3).
Produces: a helper in the test, `build_css_screen(AtScreen *sc, AtView *v, AtCell *pool, int n_fighters, int n_added, int ports_mask)`, that mirrors what the adapter submits (Task 9 uses the same field assignments; keep them in step).

- [ ] **Step 1: Write the failing tests.** Create `pc/tests/atlas_select_render_test.c`:

```c
#define AT_SINK_HAS_IMAGE
#include "atlas_check.h"
#include "atlas_fake.h"
#include "atlas_style.h"
#include "../platform/gw_ui_render.h"

static const AtTextOps O = { fake_width, NULL };
static AtScreen SC; static AtView V; static AtCell POOL[AT_MAX_EXT_CELLS]; static AtHits HITS;

static void build_css_screen(AtScreen *sc, AtView *v, AtCell *pool, int n, int n_added, int ports_mask)
{
    int i, p;
    memset(sc, 0, sizeof *sc); at_view_init(v); memset(pool, 0, sizeof(AtCell) * AT_MAX_EXT_CELLS);
    snprintf(sc->id, sizeof sc->id, "%s", "select.css"); snprintf(sc->title, sizeof sc->title, "%s", "FIGHTERS");
    snprintf(sc->parent[0], AT_STR, "%s", "VERSUS"); snprintf(sc->parent[1], AT_STR, "%s", "MELEE"); sc->n_parents = 2; sc->chapter = 2;
    sc->primary = AT_PRIMARY_GRID; sc->preset = AT_PRESET_NORMAL; sc->grid_cols_auto = 1; sc->band = AT_BAND_CARDS;
    sc->n_blocks = 1; sc->blocks[0].ext = pool; sc->blocks[0].ext_n = n; sc->blocks[0].cols = 0;
    sc->n_tabs = n_added > 0 ? 3 : 1;
    snprintf(sc->tabs[0].name, 24, "ALL"); sc->tabs[0].count = n;
    if (n_added > 0) { snprintf(sc->tabs[1].name, 24, "RETAIL"); sc->tabs[1].count = n - n_added; snprintf(sc->tabs[2].name, 24, "ADDED"); sc->tabs[2].count = n_added; }
    for (i = 0; i < n; i++) {
        AtCell *c = &pool[i];
        snprintf(c->id, AT_ID, "f%d", i); c->model = AT_NO_MODEL; c->tex = -1;
        c->abbr[0] = (char) ('A' + i % 26); c->abbr[1] = (char) ('A' + (i * 7) % 26);
        if (i >= n - n_added) c->origin = '+';
    }
    for (p = 0; p < 4; p++) {
        AtPortCard *k = &sc->cards[p];
        k->port = p; k->kind = (ports_mask >> p) & 1 ? 1 : 0;
        if (k->kind) { snprintf(k->name, AT_STR, "%s", "A FIGHTER WITH A LONG NAME"); snprintf(k->sub, AT_STR, "%s", "Costume 1"); snprintf(k->abbr, 3, "%s", "FO"); }
    }
    sc->keys[0].btn = 'A'; snprintf(sc->keys[0].label, AT_STR, "%s", "Pick"); sc->keys[1].btn = 'B'; snprintf(sc->keys[1].label, AT_STR, "%s", "Back");
    sc->keys[2].btn = 'X'; snprintf(sc->keys[2].label, AT_STR, "%s", "Costume"); sc->keys[3].btn = 'S'; snprintf(sc->keys[3].label, AT_STR, "%s", "Fight"); sc->n_keys = 4;
    snprintf(v->counter, AT_STR, "%d / %d", 1, n);
    v->ex.has = 1; snprintf(v->ex.kicker, AT_STR, "%s", "FIGHTER"); snprintf(v->ex.title, AT_STR, "%s", "A FIGHTER WITH A LONG NAME INDEED");
    snprintf(v->ex.what, AT_TEXT, "%s", "A rule line that is a little too long to fit on two lines at the narrow width, so it must be clamped.");
    snprintf(v->ex.stepper_label, 16, "%s", "COSTUME"); snprintf(v->ex.stepper_text, 24, "%s", "1 / 4"); v->ex.stepper = 1;
    v->cursor[0].active = 1; v->cursor[0].block = 0; v->cursor[0].index = 0; v->cursor[0].card = -1;
}

static void rosters_at_three_widths(void)
{
    static const int sizes[] = { 26, 29, 60, 129 }, widths[] = { 640, 853, 1140 };
    int si, wi;
    for (si = 0; si < 4; si++) for (wi = 0; wi < 3; wi++) {
        AtSink s; AtRenderInfo info; int i, cells = 0, n = sizes[si];
        build_css_screen(&SC, &V, POOL, n, n > 26 ? n - 26 : 0, 0x3);
        s = rec_sink();
        at_render_ex(&SC, &V, (float) widths[wi], 1000.0, 1, &O, &s, &HITS, &info);
        CHECK(info.capped == 0 && info.entries < AT_SCREEN_QUAD_WARN);                     /* the 129-tile worst case stays under 3,000 entries */
        CHECK(info.hits_dropped == 0);                                                       /* every visible tile is reachable by the mouse (AT_MAX_HITS 96) */
        CHECK(texts_legible());
        for (i = 0; i < HITS.n; i++) if (HITS.h[i].kind == AT_HIT_CELL) cells++;
        if (n == 26 || n == 29) CHECK(cells == n);                                          /* the vanilla and ACE-sized rosters fit without scrolling at every width */
        if (n >= 60) CHECK(cells < n && cells > 0);                                         /* the big ones scroll, and draw only the visible rows */
        /* no hit rectangle leaves the canvas, and none overlaps the band or the keys */
        for (i = 0; i < HITS.n; i++) {
            const AtHit *h = &HITS.h[i];
            CHECK(h->r.x >= -0.01f && h->r.x + h->r.w <= (float) widths[wi] + 0.01f && h->r.y >= 0.0f && h->r.y + h->r.h <= 480.0f + 0.01f);
        }
    }
}
static void hits_follow_layout(void)
{
    /* the same tile sits at a different x at 853 than at 640 (the arranged rectangle, not the authored one); a click on it maps to the same index */
    AtSink s; AtRect a, b; int i, ia = -1, ib = -1;
    build_css_screen(&SC, &V, POOL, 29, 3, 0x1);
    s = rec_sink(); at_render(&SC, &V, 640.0f, 1000.0, 1, &O, &s, &HITS);
    for (i = 0; i < HITS.n; i++) if (HITS.h[i].kind == AT_HIT_CELL && HITS.h[i].b == 5) { a = HITS.h[i].r; ia = i; }
    s = rec_sink(); at_render(&SC, &V, 1706.0f, 1000.0, 1, &O, &s, &HITS);
    for (i = 0; i < HITS.n; i++) if (HITS.h[i].kind == AT_HIT_CELL && HITS.h[i].b == 5) { b = HITS.h[i].r; ib = i; }
    CHECK(ia >= 0 && ib >= 0 && (a.x != b.x));
    CHECK(at_hit_test(&HITS, b.x + b.w * 0.5f, b.y + b.h * 0.5f) == ib);
    CHECK(at_hit_test(&HITS, -1000.0f, -1000.0f) == -1);                                    /* a pointer off the picture does nothing */
}
static void placeholder_when_no_art(void)
{
    AtSink s;
    build_css_screen(&SC, &V, POOL, 29, 0, 0x1);
    s = rec_sink(); at_render(&SC, &V, 640.0f, 1000.0, 1, &O, &s, &HITS);
    CHECK(REC.ni == 0);                                                                       /* no image drawn: every tile is the frame with its letters */
    CHECK(find_text("AA") != NULL || find_text("AH") != NULL);
}
static void style_of_the_screen(void)
{
    AtSink s; AtLayout L; AtSplit sp; int i;
    build_css_screen(&SC, &V, POOL, 29, 3, 0xF);
    s = rec_sink(); at_render(&SC, &V, 640.0f, 1000.0, 1, &O, &s, &HITS);
    at_layout(640.0f, AT_PRESET_NORMAL, &L); at_layout_split(&L, 1, AT_BAND_CARDS, &sp);
    CHECK(sty_chamfer(L.primary, 8.0f, AT_C_GROUND) == 0);                                  /* the pane's two cut corners show the ground */
    /* one primary plate and one supporting plate: everything else quiet (4.5): the number of E1 panes is two */
    { int panes = 0; for (i = 0; i < REC.np; i++) if (REC.p[i].rgba == AT_C_PLATE) panes++; CHECK(panes >= 2); }
    /* the four cards at the bottom do not collide with the keys */
    for (i = 0; i < HITS.n; i++) if (HITS.h[i].kind == AT_HIT_CELL) CHECK(HITS.h[i].r.y + HITS.h[i].r.h <= sp.band.y - 12.0f + 0.5f);
}
static void focus_on_a_cell_has_three_cues(void)
{
    AtSink s; StySig a, b;
    build_css_screen(&SC, &V, POOL, 29, 0, 0x1);
    V.cursor[0].active = 0; s = rec_sink(); at_render(&SC, &V, 640.0f, 1000.0, 1, &O, &s, &HITS); a = sty_sig(0);
    V.cursor[0].active = 1; s = rec_sink(); at_render(&SC, &V, 640.0f, 1000.0, 1, &O, &s, &HITS); b = sty_sig(0);
    CHECK(sty_focus_cues(a, b) == 3);
}
int main(void)
{
    rosters_at_three_widths(); hits_follow_layout(); placeholder_when_no_art(); style_of_the_screen(); focus_on_a_cell_has_three_cues();
    ATLAS_DONE("atlas select render");
}
```

If `style_of_the_screen`'s chamfer line fails with code 2, a later draw (the band or the keys) covers the pane's bottom-right corner: **that is the step 1 bug again**; fix the draw order, never the check.

Register `atlas-select-render) sources=(pc/tests/atlas_select_render_test.c pc/platform/gw_ui_render.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c) ;;`. Run `nt atlas-select-render`; expected: failures until the render handles ext cells, tabs, band, auto columns and the visible-row culling.

- [ ] **Step 2: Make it pass.** The work is in `gw_ui_render.c` and is the render half of Tasks 4 and 5; this task is where their combination is proved. Specific traps: `grid_pass` computes `rows` from `bk->n` (use `at_block_count`); the title row per block (`26 px`) is not drawn for a block with no title (the CSS has tabs instead: a block with an empty `title` takes no title row); `AT_MAX_HITS` is 96: at 1140 wide with 11 columns and 6 visible rows the grid alone is 66 hit rectangles plus 4 keys plus tabs and cards, so **raise `AT_MAX_HITS` to 192** and keep `hits_dropped` in the info (the test above fails if one is dropped).
- [ ] **Step 3: Run.** `nt atlas-select-render` and the baselines. Expected `0 failed`.
- [ ] **Step 4: Commit.** Game repo, message `atlas step 4: the CSS composed at three widths with 26, 29, 60 and 129 fighters; style checks on the screen`.

---

### Task 7: Disc art, decoded in memory (never stored)

**Files:**
- Modify (game repo): `melee/pc/platform/gw_kit.c`, `gw_kit.h`
- Create (game repo): `melee/pc/tests/atlas_discart_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-discart`); `CREDITS.md` if any outside source is consulted for CMPR

**Interfaces:**
Consumes: `kt_decode` (formats 0 to 6 and the palette formats), `KT_MAX`, `gw_Kit_TexAddGX`.
Produces:

```c
/* A GX texture read from game memory, decoded NOW into an RGBA8 copy owned by the kit: the caller's pointers are not kept.
 * `key` names it (an archive icon, a portrait and its costume); the same key returns the same slot. -1 when the format is not
 * decodable, the image is short, or the pool is full of slots used in the last two frames. */
int  gw_Kit_TexAddHsd(const char *key, int gx_fmt, const uint8_t *img, size_t img_size, int w, int h,
                      int tlut_fmt /* 0 IA8, 1 RGB565, 2 RGB5A3 */, const uint8_t *tlut, int tlut_n);
void gw_Kit_TexHsdFrame(int frame);         /* the host calls it once per frame: marks the use clock for eviction */
void gw_Kit_TexDropHsd(void);               /* scene exit: free the whole disc-art pool */
int  gw_Kit_TexHsdCount(void);
```

- [ ] **Step 1: Write the failing test** (host-only; synthetic tiles, **no disc bytes**). Create `pc/tests/atlas_discart_test.c`; the test includes `gw_kit.c` the way `gw_kit.c`'s own tests do (`gw_test_register`), or, if the file is not standalone-linkable, goes in the exe's test table (`gw_test_register("kit_discart", ...)` next to `kit_decode_formats` at `gw_kit.c:1774`) and is run by the exe's self-test command. Check which with `grep -n "gw_test_register\|GW_STANDALONE" pc/platform/gw_kit.c | head`; the checks are the same either way:

```c
static int test_kit_discart(void)
{
    uint8_t ci8[64], tl[8], img[32 * 4];
    int a, b, i, c;
    /* a CI8 tile: 8x4 texels, palette entries 0 and 1 (RGB5A3: opaque red, opaque blue) */
    for (i = 0; i < 32; i++) ci8[i] = (uint8_t) (i & 1);
    tl[0] = 0xFC; tl[1] = 0x00; tl[2] = 0x80; tl[3] = 0x1F;                       /* 1 11111 00000 00000 ; 1 00000 00000 11111 */
    a = gw_Kit_TexAddHsd("t:ci8", 9 /* CI8 */, ci8, 32, 8, 4, 2 /* tlut: RGB5A3 (0 IA8, 1 RGB565, 2 RGB5A3, as kt_tlut reads it) */, tl, 2);
    if (a < 0) { gw_test_fail("CI8 with an RGB5A3 palette did not decode"); return 1; }
    { const uint8_t *px = gw_Kit_TexPixels(a);
      if (px[0] != 255 || px[1] != 0 || px[2] != 0 || px[3] != 255) { gw_test_fail("texel 0 should be opaque red"); return 1; }
      if (px[4 + 2] != 255) { gw_test_fail("texel 1 should be blue"); return 1; } }
    /* the same key is the same slot; the caller's buffer may be freed or overwritten without changing the texture (the pixels were COPIED) */
    memset(ci8, 0xFF, sizeof ci8); memset(tl, 0, sizeof tl);
    b = gw_Kit_TexAddHsd("t:ci8", 9, ci8, 32, 8, 4, 2, tl, 2);
    if (b != a || gw_Kit_TexPixels(a)[0] != 255) { gw_test_fail("decode_copies_pixels: the kit kept the caller's buffer"); return 1; }
    /* short image, unknown format, bad size: -1, never a crash */
    if (gw_Kit_TexAddHsd("t:short", 9, ci8, 4, 8, 4, 2, tl, 2) != -1) { gw_test_fail("a short image was accepted"); return 1; }
    if (gw_Kit_TexAddHsd("t:fmt", 99, ci8, 32, 8, 4, 2, tl, 2) != -1) { gw_test_fail("an unknown format was accepted"); return 1; }
    if (gw_Kit_TexAddHsd("t:null", 9, NULL, 32, 8, 4, 2, tl, 2) != -1) { gw_test_fail("a NULL image was accepted"); return 1; }
    if (gw_Kit_TexAddHsd("t:ci8-no-lut", 9, ci8, 32, 8, 4, 2, NULL, 0) != -1) { gw_test_fail("a palette image without a palette was accepted"); return 1; }
    /* RGB5A3 and RGBA8 portrait-sized images: 136x188 (the retail portrait size) decode, and a full pool evicts only slots unused for two frames */
    for (c = 0; c < 400; c++) {
        char key[32]; static uint8_t big[136 * 188 * 4];
        gw_Kit_TexHsdFrame(c / 4);                                                  /* four decodes per frame */
        snprintf(key, sizeof key, "t:p%d", c);
        i = gw_Kit_TexAddHsd(key, 5, big, 136 * 192 * 2, 136, 188, 0, NULL, 0);
        if (i < 0 && c < 100) { gw_test_fail("slot_pool_evicts: the pool refused too early"); return 1; }
    }
    if (gw_Kit_TexHsdCount() > 192) { gw_test_fail("the pool grew past its cap"); return 1; }
    gw_Kit_TexDropHsd();
    if (gw_Kit_TexHsdCount() != 0) { gw_test_fail("TexDropHsd left slots behind"); return 1; }
    /* the model slots and file textures are untouched by the pool */
    return 0;
}
```

The RGB5A3 loop passes a size of `136 * 192 * 2` because GX tiles are 4x4: 188 rows round up to 192 (47 tile rows of 4). Register the test and run it; expected failure: `gw_Kit_TexAddHsd` undefined.

- [ ] **Step 2: Implement.**
  1. A separate pool: `KitTex.fmt = -7` for disc art, at most **192** slots (an icon is 64x56x4 = 14 KB, a portrait 136x188x4 = 102 KB: 192 mixed slots stay under about 10 MB worst case; **measure it and record the number** in the commit), `KT_MAX` raised from 384 to 576 (320 file + 64 model + 192 disc). Check what else is sized by `KT_MAX` or indexed by texture number: `grep -n "KT_MAX\|gw_Kit_TexCount\|TexPixels" pc/platform/*.c pc/platform/*.cpp pc/platform/*.inc` (the overlay's texture upload is **(unverified)**: if it uploads by index each frame it needs a dirty flag per slot; if it caches by index, an evicted-and-reused index shows the old image: then **never reuse an index**, grow the table and free the pixels only).
  2. **Eviction rule:** a slot may be reused only if it was not drawn or requested in the last two frames (the draw list is two-banked, so the frame in flight still names last frame's slots). A request for a key that exists returns its slot and marks it used. When no slot is free the call returns -1 and the caller draws the placeholder: a missing picture is acceptable, a wrong picture is not.
  3. **Formats:** use `kt_decode`'s existing cases for I4, I8, IA4, IA8, RGB565, RGB5A3, RGBA8, CI4, CI8; **CMPR** (format 14) is not read today (`kt_decode` returns NULL). The retail icons' and portraits' formats are **(unverified)**: first add a one-line log in the failure path (`ui: disc art format %d not decoded`, once per format) and let the in-game checklist (Task 13) report which formats occurred. Only if CMPR occurs, add it, written from the format's public description (two RGB565 endpoint colours and 2-bit indices per 4x4 block, four blocks per 8x8 tile) with its own synthetic test; **if any outside source is consulted for it, name it with a link in `CREDITS.md` in the same change** (the owner's credit rule), and do not copy code from a licence this project does not carry.
  4. **Nothing is written to disk.** `grep -n "fopen\|fwrite" ` over the new function must find nothing; the key is a string in memory only.
- [ ] **Step 3: Run.** The test passes (`kit_discart` in the exe's self-test list, run headless by the existing command in `melee/pc/docs/PORT_DEV_QUICKREF.md`, or by the standalone harness). Expected: no `gw_test_fail`.
- [ ] **Step 4: Commit.** Game repo, message `atlas step 4: disc art decoded in memory into a capped pool with two-frame eviction; nothing stored`.

---

### Task 8: The SSS model and the stage grid (drawing for strikes and bans only)

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_sss.h`, `gw_ui_sss.c`, `melee/pc/tests/atlas_sss_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-sss`)

**Interfaces:**
Consumes: Tasks 4 and 5 (cells, tabs, the matchup strip), the legacy rules in `fs_sss_open`, `fs_sss_frame`, `fs_random_stage`.
Produces:

```c
#define AT_SSS_MAX 256
typedef struct { int ext, type /* 1 icon, 2 icon with art, 3 random */, row; unsigned char ok, tab_of; } AtSssStage;   /* tab_of: 1 retail, 2 added, 3 tournament */
typedef struct AtSss {
    int n, tab, cur, cols, done, go, pick_ext;
    AtSssStage st[AT_SSS_MAX];
    int vis[AT_SSS_MAX], n_vis;
    int online;                                    /* the lobby uses the same grid; strikes are drawn through cell flags, never decided here */
} AtSss;
void at_sss_open(AtSss *s, int online);
void at_sss_set_stages(AtSss *s, int n, const AtSssStage *st);      /* the Random tile is kept last and appears once (Akaneia has two) */
void at_sss_set_tab(AtSss *s, int tab);
unsigned at_sss_step(AtSss *s, unsigned trig, unsigned rep, int random_pick);   /* AT_CE_* bits (the same bits as the CSS) */
int at_sss_pick_random(const AtSss *s, int r);       /* the r-th unlocked, non-random stage's ext (fs_random_stage with the dice injected) */
```

- [ ] **Step 1: Write the failing tests** (`pc/tests/atlas_sss_test.c`), one per legacy rule read from `fs_sss_frame`/`fs_sss_open`: the Random tile is last and unique; an `ok == 0` stage cannot be picked (a toast and `AT_CE_BACK`, as the legacy does for a locked stage); A on a stage sets `go` and `pick_ext`; START picks the hovered one; B goes back; `at_sss_pick_random` skips locked and random tiles and returns Battlefield's id `31` when nothing is unlocked; a **256-stage** list with tabs `1`/`2` has counts that sum correctly; focus survives a tab switch (the cursor goes to the nearest visible stage, never outside `vis`). Read `fs_sss_frame` (lines 1306 to 1410) and write each check from it before moving the code, exactly as Task 3.

```c
static void random_tile_last_and_unique(void)
{
    AtSss s; AtSssStage st[6]; int i;
    memset(st, 0, sizeof st);
    for (i = 0; i < 6; i++) { st[i].ext = 20 + i; st[i].type = 2; st[i].ok = 1; st[i].tab_of = 1; }
    st[2].type = 3; st[4].type = 3;                             /* two Random icons (an Akaneia layout) */
    at_sss_open(&s, 0); at_sss_set_stages(&s, 6, st);
    CHECK(s.n == 5 && s.st[4].type == 3 && s.st[4].ext == -1);   /* four stages and one Random, last */
    for (i = 0; i < 4; i++) CHECK(s.st[i].type != 3);
}
static void locked_stage_cannot_be_picked(void)
{
    AtSss s; AtSssStage st[3]; unsigned e;
    memset(st, 0, sizeof st);
    st[0].ext = 31; st[0].type = 2; st[0].ok = 1; st[0].tab_of = 1;
    st[1].ext = 32; st[1].type = 2; st[1].ok = 0; st[1].tab_of = 1;
    at_sss_open(&s, 0); at_sss_set_stages(&s, 2, st); s.cols = 8; s.cur = 1;
    e = at_sss_step(&s, AT_CI_A, 0, 0);
    CHECK((e & AT_CE_BACK) && !s.go);                              /* a locked stage: no pick */
    s.cur = 0; e = at_sss_step(&s, AT_CI_A, 0, 0); CHECK((e & AT_CE_FINISH_GO) && s.go && s.pick_ext == 31);
}
```

Register `atlas-sss) sources=(pc/tests/atlas_sss_test.c pc/platform/gw_ui_sss.c pc/platform/gw_ui_css.c pc/platform/gw_ui_css_profile.c) ;;` (it shares the `AT_CE_*` bits through `gw_ui_css.h`). Run; expected: fails to compile.

- [ ] **Step 2: Move the code** from `fs_sss_open`/`fs_sss_frame`/`fs_random_stage` into `gw_ui_sss.c` (pages become tabs and scrolling, exactly as Task 3 did for the CSS; the legacy page turn on L/R becomes a tab step). **Tabs:** `ALL`, `RETAIL`, `ADDED`; the `TOURNAMENT` tab of the mockup exists only where the online Stage List's legal six are known (`Netplay_StageMode`, `fso_stage_modes` "Competitive"); until the adapter supplies them (`tab_of == 3`) the tab is not offered. **Which stages are "added" is (unverified):** the legacy code knows `type` (1, 2, 3) and `ext`, not origin; the rule to try first is "an m-ex external id above the disc's retail count"; settle it by reading `mnStageSel_PcArtIcon` and `Mex_GrKindForExt` and put the rule in the test as a fixture.
- [ ] **Step 3: Strikes and bans are drawn, never decided.** The lobby (step 6) marks cells banned, picked or struck through `AT_CELL_BANNED`, `AT_CELL_PICKED`, `AT_CELL_P1`/`AT_CELL_UNSET` in the cell flags it submits. Add the drawing in `at_part_cell` (a banned cell is hatched or crossed **and** says `BAN` in `AT_R_CAP12`; a picked cell takes the ember ring; the port that struck it shows its numeral and shape) and a style test for each flag: text legible, inside the cell, not colour alone. **No decision logic is added**: `grep -n "strike\|ban" pc/platform/gw_ui_sss.c` must find only the flag names.
- [ ] **Step 4: Render test.** Add `stages_256` to `atlas_select_render_test.c`: 256 cells of `AT_PRESET_NORMAL` at 640 and 1140 stay under the entry cap, `hits_dropped == 0`, and a stage cell shows its **name plate** (`Peach's Castle`, wrapped over two lines at most in `AT_R_CAP12`, inside the cell) with the abbreviation above it as in the mockup.
- [ ] **Step 5: Run and commit.** `nt atlas-sss`, `nt atlas-select-render`; message `atlas step 4: the SSS model in pure C, the stage grid with tabs, strike and ban drawing (no decisions)`.

---
### Task 9: The host-side native screen and the game-side adapter (needs gates G1 to G3)

The game side cannot hand the host a function pointer or a struct: it submits **scalars and C strings** through shims, as `Settings_SetInt("envoy_online", v)` does today (`gmfrontend.c:554`). This task builds both ends: host functions that fill a **native-owned** `AtScreen` in place (testable with no game by calling them directly), and the game-side adapter `gmfrontend_atlas_select.inc` that runs the Task 3 and 8 models with the game's pads and submits the view each frame.

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_native_sel.c` (the host half; if step 2 already owns a native-shim file, this is a section of it), `melee/src/melee/gm/gmfrontend_atlas_select.inc`, `melee/pc/tests/atlas_select_adapter_test.c`
- Modify (game repo): `melee/src/melee/gm/gmfrontend.c` (include the new file; `gmFrontend_AtlasSelect`; scene exit), `gmfrontend.h`, `melee/pc/platform/gw_ui_stack.h/.c` only if G2's owner token is not yet in the stack
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-select-adapter`)

**Interfaces (the shim table; the host half implements, the game half calls; every argument is an int, a pointer to a NUL-terminated string, or an unsigned):**

```c
int  gw_Ui_SelOpen(int kind /* 0 css, 1 sss, 2 loading */, int match_type, const char *t0, const char *t1, const char *title);
                                       /* a handle >= 0, or -1 (roles missing, MELEE_ATLAS=0, stack full: the caller keeps the legacy drawing) */
void gw_Ui_SelTab(int h, int i, const char *name, int count, int active);
void gw_Ui_SelBeginCells(int h, int n);                        /* the block's cell count for this frame (<= AT_MAX_EXT_CELLS) */
void gw_Ui_SelCell(int h, int i, const char *id, const char *name, const char *abbr, int tex, unsigned flags, char origin);
void gw_Ui_SelCard(int h, int port, int kind, const char *name, const char *sub, const char *abbr, int tex, int cpu_lv, int team, unsigned flags);
void gw_Ui_SelCursor(int h, int port, int active, int cell, int card);
void gw_Ui_SelExplain(int h, const char *kicker, const char *title, const char *what, const char *abbr, int tex,
                      const char *stepper_label, const char *stepper_text, const char *from);
void gw_Ui_SelKeys(int h, const char *spec);                   /* "A:Pick,B:Back,X:Costume,S:Fight" (S = START); parsed once per change */
void gw_Ui_SelCounter(int h, const char *text);
void gw_Ui_SelNote(int h, const char *text, int kind);         /* the toast */
void gw_Ui_SelProgress(int h, int permille);                   /* loading */
int  gw_Ui_SelPoll(int h, int *kind, int *a, int *b);          /* 0 none; events: 1 cell hover/click (a = cell, b = clicks 0/1/2 for none/left/right), 2 card, 3 tab (a = tab), 4 key hint (a = button char), 5 wheel (a = +1/-1), 6 pointer moved */
int  gw_Ui_SelCols(int h);                                     /* the columns the layout chose (the model needs it to move on the grid) */
void gw_Ui_SelClose(int h);
int  gw_Ui_ArtDecode(const char *key, int gx_fmt, const void *img, int size, int w, int h, int tlut_fmt, const void *tlut, int tlut_n);   /* -> gw_Kit_TexAddHsd */
```

If step 2's shim set already has an equivalent for any row (for example a generic cell submit), use it and delete the duplicate row here; the rest of the task is unchanged.

- [ ] **Step 1: Write the failing host-side test.** `pc/tests/atlas_select_adapter_test.c` calls the shims exactly as the adapter will, against the real render and a fake kit (the same stand-ins `atlas_binding_test.c` uses for `gw_script.c` internals). Four checks matter more than the rest, each a past or likely hole:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_native_sel.h"      /* declares the gw_Ui_Sel* functions above and gw_Ui_SelTest_* helpers for the test */

static void filled_and_drawn(void)
{
    int h = gw_Ui_SelOpen(0, 0, "VERSUS", "MELEE", "FIGHTERS"), i;
    CHECK(h >= 0);
    gw_Ui_SelTab(h, 0, "ALL", 29, 1); gw_Ui_SelBeginCells(h, 29);
    for (i = 0; i < 29; i++) { char id[8]; snprintf(id, sizeof id, "f%d", i); gw_Ui_SelCell(h, i, id, "NAME", "NA", -1, 0u, 0); }
    gw_Ui_SelCursor(h, 0, 1, 3, -1);
    CHECK(gw_Ui_SelTest_Draw(h, 640.0f) > 0);                         /* it draws: returns the entry count */
    CHECK(gw_Ui_SelCols(h) >= 6 && gw_Ui_SelCols(h) <= 11);
    gw_Ui_SelClose(h);
}
/* Review Focus 3: a native screen left open must be closed on EVERY way a scene can end, or it draws over the next scene */
static void closed_on_every_exit(void)
{
    int h = gw_Ui_SelOpen(0, 0, "VERSUS", "MELEE", "FIGHTERS");
    CHECK(gw_Ui_SelTest_TopIsNative() == 1);
    gw_Ui_SelTest_SceneChanged();                                       /* the host's scene-change hook, called by the frontend scene's exit AND by the mode loop */
    CHECK(gw_Ui_SelTest_Depth() == 0);                                  /* closed without the adapter asking */
    CHECK(gw_Ui_SelPoll(h, &(int){0}, &(int){0}, &(int){0}) == 0);      /* and a stale handle is harmless, not a crash */
    gw_Ui_SelCell(h, 0, "x", "x", "xx", -1, 0u, 0);                     /* writes to a closed handle are ignored */
    CHECK(gw_Ui_SelOpen(0, 0, "A", "B", "C") >= 0);                     /* a second open after a close works */
    gw_Ui_SelClose(gw_Ui_SelTest_Handle());
    CHECK(gw_Ui_SelTest_Depth() == 0);
}
/* Review Focus 9: ownership checked as the native owner AND as a mod, never only as the developer console */
static void owner_native_vs_mod(void)
{
    int h = gw_Ui_SelOpen(0, 0, "VERSUS", "MELEE", "FIGHTERS");
    CHECK(gw_Ui_SelTest_ModClose("some.mod") == 0);                     /* a mod caller cannot close the native screen */
    CHECK(gw_Ui_SelTest_ModFeed("some.mod", "accept") == 0);            /* ... nor feed it an intent */
    CHECK(gw_Ui_SelTest_ModOpenOver("some.mod") == 0);                  /* ... nor push its own screen over it (no mod screen over a select) */
    CHECK(gw_Ui_SelTest_ConsoleClose() == 1);                           /* the developer console may (documented), and that is the only caller that may besides the owner */
    (void) h;
    gw_Ui_SelTest_SceneChanged();
}
static void mouse_port(void)
{
    int h = gw_Ui_SelOpen(0, 0, "VERSUS", "MELEE", "FIGHTERS"), i, k, a, b;
    gw_Ui_SelTab(h, 0, "ALL", 29, 1); gw_Ui_SelBeginCells(h, 29);
    for (i = 0; i < 29; i++) gw_Ui_SelCell(h, i, "f", "N", "NA", -1, 0u, 0);
    gw_Ui_SelTest_Draw(h, 640.0f);
    gw_Ui_SelTest_Mouse(h, gw_Ui_SelTest_CellCentreX(h, 5), gw_Ui_SelTest_CellCentreY(h, 5), 1);   /* left click on tile 5 */
    CHECK(gw_Ui_SelPoll(h, &k, &a, &b) == 1 && k == 1 && a == 5 && b == 1);
    gw_Ui_SelTest_Mouse(h, -1000.0f, -1000.0f, 0);                       /* off the picture: nothing */
    CHECK(gw_Ui_SelPoll(h, &k, &a, &b) == 0);
    gw_Ui_SelClose(h);
}
int main(void) { filled_and_drawn(); closed_on_every_exit(); owner_native_vs_mod(); mouse_port(); ATLAS_DONE("atlas select adapter"); }
```

`gw_Ui_SelTest_*` are small test-only accessors declared in `gw_ui_native_sel.h` under `#ifdef GW_UI_SEL_TEST` so the shipped exe does not export them. Register `atlas-select-adapter` with the render sources of Task 6 plus `pc/platform/gw_ui_native_sel.c`, `gw_ui_css.c`, `gw_ui_sss.c`, `gw_ui_css_profile.c`, and `flags=(-DGW_UI_SEL_TEST ...)` for that case (see how `native_test.sh` sets per-case flags; add one case-local line). Run `nt atlas-select-adapter`; expected: fails to compile.

- [ ] **Step 2: Write the host half** (`gw_ui_native_sel.c`). One static `AtScreen` plus a static `AtCell pool[AT_MAX_EXT_CELLS]` and `AtView`; the stack entry carries the **native owner** (G2). Rules, each pinned above:
  1. `gw_Ui_SelOpen` returns -1 when `MELEE_ATLAS=0`, when the Atlas roles are missing (`gd.ui.available()`'s check), or when a native screen is already open (only one: **the stack has one top**); otherwise it zeroes the record (`memset`, never reused state), sets `blocks[0].ext = pool`, pushes it with the native owner and returns a generation-tagged handle (`(gen << 8) | slot`) so a stale handle is recognised.
  2. Every `gw_Ui_Sel*` call checks the handle's generation first and **ignores** a stale one.
  3. `gw_Ui_SelBeginCells(h, n)` clamps `n` to `AT_MAX_EXT_CELLS` and rebuilds only when the adapter says the signature changed (the adapter calls `SelBeginCells` only then); cursors, toast and progress are cheap and written every frame.
  4. `gw_Ui_SelPoll` drains a small ring of events produced by the host's tick from `at_mouse_events` over the arranged hit rectangles (Task 4 hit kinds: cells, keys, plus new `AT_HIT_TAB` and `AT_HIT_CARD`; add them to `gw_ui_input.h` with their `at_mouse_events` handling and a test in `atlas_input_test.c`, **including the held-button priming rule of step 1**: a held A that opened the scene must not click on it).
  5. `gw_Ui_SelTest_SceneChanged()` is the real function `gw_Ui_SceneChanged()` that the **mode loop** calls on every mode or scene change and that the frontend scene's `OnExit` calls too; it closes every native-owned screen. It is called from both places so a forced scene change (a soft reset, `gd.scene_launch`, an error path) cannot leave the screen up.
  6. The host sink gets `image`: `gw_Kit_DrawImage(tex, ...)`.
- [ ] **Step 3: Run the host test** until it passes, then the old baselines. Expected: `atlas select adapter: N checks, 0 failed`.
- [ ] **Step 4: Write the game-side adapter.** `gmfrontend_atlas_select.inc`, included by `gmfrontend.c` after `gmfrontend_select.inc`. The adapter owns no rules: it reads pads, calls the models, submits the view, and writes `CSSData`/`SSSData` at the end exactly as `fs_css_finish`/`fs_sss_finish` do today (they stay; the adapter calls the same finish code after the model says `AT_CE_FINISH_GO` or `AT_CE_FINISH_BACK`). Skeleton, with the invariants in comments:

```c
/* gmfrontend_atlas_select.inc - the Atlas drawing of the CSS and SSS (included by gmfrontend.c, TARGET_PC only).
 * The rules are the models' (gw_ui_css.c, gw_ui_sss.c); this file reads pads, runs a step per port, submits the view and ends the
 * scene through the same finish code as the legacy screens. CSSData and SSSData are handed over exactly as before. */
extern int gw_Ui_SelOpen(int kind, int match_type, const char* t0, const char* t1, const char* title);
extern void gw_Ui_SelClose(int h);
/* ... the rest of the shim table ... */

static struct { int h; AtCss css; AtSss sss; int sig, art_frame; char toast[80]; int active; } fas;

static AtCssIn fas_in(int port)
{
    AtCssIn r;
    u64 t = gm_GetButtonsTriggered((u8) port), p = gm_801A36C0((u8) port);   /* the same sources fs_in reads: the legacy input is the oracle */
    r.trig = 0; r.rep = 0;
    if (t & PAD_BUTTON_A) r.trig |= AT_CI_A;   if (t & PAD_BUTTON_B) r.trig |= AT_CI_B;
    if (t & PAD_BUTTON_X) r.trig |= AT_CI_X;   if (t & PAD_BUTTON_Y) r.trig |= AT_CI_Y;
    if (t & PAD_TRIGGER_Z) r.trig |= AT_CI_Z;  if (t & PAD_TRIGGER_L) r.trig |= AT_CI_L;
    if (t & PAD_TRIGGER_R) r.trig |= AT_CI_R;  if (t & PAD_BUTTON_START) r.trig |= AT_CI_START;
    if (p & PAD_ANY_LEFT) r.rep |= AT_CI_LEFT;   if (p & PAD_ANY_RIGHT) r.rep |= AT_CI_RIGHT;
    if (p & PAD_ANY_UP) r.rep |= AT_CI_UP;       if (p & PAD_ANY_DOWN) r.rep |= AT_CI_DOWN;
    return r;
}

/* Open: called from gmFrontend_AtlasSelect's scene (the frontend scene's on_enter). Returns 1 when the Atlas screen is up. */
static int fas_open_css(CSSData* css, const char* t0, const char* t1)
{
    const AtCssProfile* prof = at_css_profile(css != NULL ? css->match_type : -1);
    if (prof == NULL) { return 0; }                              /* an unknown mode keeps the retail screen: never guess */
    fas.h = gw_Ui_SelOpen(0, css->match_type, t0, t1, "FIGHTERS");
    if (fas.h < 0) { return 0; }
    /* fs_css_open's CSSData reading stays in the legacy function: call it first so both drawings see the same start state, then
     * copy the ports into the model (kind, ck, costume, cpu_lv, team from css->vs.start.players[]) and the roster from fcs.ck[]. */
    fs_css_open(css);
    at_css_open(&fas.css, prof, &fas_ops, fcs.online, fcs.teams);
    /* ... at_css_set_roster(&fas.css, fcs.n, fcs.ck, ok, tab_of) ... */
    return 1;
}

static void fas_css_frame(void)
{
    int p, cols = gw_Ui_SelCols(fas.h);
    unsigned ev = 0;
    at_css_set_cols(&fas.css, cols);
    for (p = 0; p < 4 && !fas.css.done; p++) {
        AtCssIn in = fas_in(p);
        if (fas.css.online) {                                       /* the lobby folds every controller into port 0, as fs_css_port does */
            int q;
            if (p != 0) { continue; }
            for (q = 1; q < 4; q++) { AtCssIn o = fas_in(q); in.trig |= o.trig; in.rep |= o.rep; }
        }
        if (HSD_PadCopyStatus[p].err != 0 && fas.css.p[p].kind == AT_CSS_HMN && p != 0) { fas.css.p[p].kind = AT_CSS_OFF; }   /* a controller left */
        ev |= at_css_step(&fas.css, p, in, fe.frames);
    }
    if (ev & AT_CE_MOVE) sfxMove();
    if (ev & AT_CE_FORWARD) sfxForward();
    if (ev & AT_CE_BACK) sfxBack();
    if (ev & AT_CE_FINISH_GO) { fas_css_finish(1); }               /* fs_css_finish, fed from the model's ports */
    else if (ev & AT_CE_FINISH_BACK) { fas_css_finish(0); }
    fas_css_submit();                                              /* diffs a signature; cells only on change, cursors every frame */
}
```

`fas_css_submit` mirrors `fs_css_sig`/`fs_build_css`: when the signature changes it calls `gw_Ui_SelTab`, `gw_Ui_SelBeginCells` and one `gw_Ui_SelCell` per visible tile (icon texture through `gw_Ui_ArtDecode` **once per fighter and cached by key, `ck` plus the archive generation**, never per frame), `gw_Ui_SelCard` per port, `gw_Ui_SelExplain` for the tile under the leading cursor (portrait for the costume: key `ck:costume`); every frame it calls `gw_Ui_SelCursor` for each port. **The adapter never keeps an `HSD_ImageDesc*` or `HSD_Tlut*` across frames**: it passes them to `gw_Ui_ArtDecode` and drops them (the archive is closed by `fa_close` at scene exit). A `NULL` image (a Geno-defined fighter has no icon of its own: `fcs.icon[...].img == NULL`) submits `tex = -1` and the placeholder shows. Mouse: for each event from `gw_Ui_SelPoll` the adapter builds the pad bits with `at_css_mouse_bits(...)` for the mouse's port (the legacy `fs_mouse_port()` rule: the first human port; the human in Training; none online except the one card) and ORs them into that port's `AtCssIn`.

- [ ] **Boundary note.** The adapter above calls the pure models (`at_css_step`, `at_sss_step`) directly, because their headers are libc-free and the game-side file can include them. **If step 2's shim-boundary rule (spec 6.1, `melee/CLAUDE.md` "shim boundary") forbids game-side code from including host headers, put each model call behind a one-line shim** (`gw_Ui_CssStep(port, trig, rep, frame)` returning the `AT_CE_*` bits, with the model state held host-side in the native slot): the host tests are unchanged, and the adapter shrinks. Decide this in Task 0 step 1 by reading how `gmfrontend_atlas.inc` reaches the host.
- [ ] **Step 5: Hook the scene.** In `gmfrontend.c`: `gmFrontend_AtlasSelect(state, sss, name)` (declared in `gmfrontend.h`) replaces the **bodies** of `gmFrontend_SelectScene`, `gmFrontend_TrainingSelect` and `gmFrontend_ModeSelect`, which become one-line wrappers (so the three existing callers, and `geno_lab_mode.c`, are untouched); it does what they did (set `state->info.scene_kind = GS_FRONTEND`, record the CSS or SSS data pointer, `fe_sel_mode_pending`) and records `fe_sel_mt` (the profile key, remembered for the SSS, which has no `match_type` of its own). In the frontend scene's per-frame function add **one** early branch next to the one step 2 added: `if (fas.active) { fas_frame(); return; }`, and in `gm_Scene_Frontend_OnExit` call `gw_Ui_SceneChanged()` and clear `fas.active`. `MELEE_ATLAS=0` and a `-1` from `gw_Ui_SelOpen` leave `fas.active` at 0, so the legacy drawing runs: it reads the same model, so the fallback is a real screen, not a stub.
- [ ] **Step 6: PowerPC syntax check** (a syntax check that did not run is not a pass):

```bash
ppc src/melee/gm/gmfrontend.c && echo "gmfrontend.c: syntax ok"
```

Expected: `gmfrontend.c: syntax ok` (the `.inc` is included by it). Then `nt atlas-select-adapter` and the baselines again.
- [ ] **Step 7: Commit.** Game repo, message `atlas step 4: the native screen host half, the game-side adapter, one entry point for every select`.

---

### Task 10: Migrate the modes in four groups (one line each; the table test and the PowerPC check per group)

Each group is **one commit set and one look**. A group is done when its modes start a match from the Atlas CSS with the same `CSSData` the legacy path produced. Because the entry point is one function, "migrating a mode" is one `TARGET_PC` line in that mode's CSS `on_enter` (VS family already calls `gmFrontend_SelectScene`).

**Files (each group):** the mode files named below (game repo); `tools/port/css_states.py` (workspace repo; extend it **once**, in group 1, to record each state's `on_enter` and `on_exit` symbols: the regex becomes `\{\s*[\w-]+\s*,\s*\w+\s*,\s*\w+\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*\{\s*(GS_CSS|GS_SSS)` and the expected file is rewritten with `--write`).

**The line**, added after the mode's own `gm_801B06B0(...)` (so `css->match_type` is set when the adapter reads it):

```c
#if defined(TARGET_PC)
    extern void gmFrontend_AtlasSelect(struct GameModeState* state, int sss, const char* name);
    gmFrontend_AtlasSelect(scene, 0, NULL);
#endif
```

**What each group's tests are** (the same three, per group): (1) `atlas-profile` still passes with the group's `match_type` values; (2) a **finish test** in `atlas_css_test.c`, `finish_leaves_mode_fields_<group>`, which builds a `CSSData` the way the mode's `on_enter` does (the test copies `gm_801B06B0`'s assignments: stocks, nametag and the slot), runs the model to `FINISH_GO`, and checks that the **fields the mode's exit handler reads** (`gm_801B0730`'s outputs: `ckind`, `color`, `cpu_level`, `nametag`, `stocks` of the slot `unk_0x0 - 1`) are what the handler expects, **and that stocks and nametag are not touched**; (3) `ppc` on every edited file.

- [ ] **Task 10a: group 1, the VS family, Training and the LAB** (`gmvsmode.c`, `gmtrainingmode.c`, the five special-melee files `gmgiant.c gmtiny.c gmslomo.c gminvisible.c gmlightning.c`, `gmstamina.c`, `gmsupersudden.c`, `gmsinglebutton.c`, `gmfixedcamera.c`, `gmcameramode.c`; `pc/geno/geno_lab_mode.c` is already a caller). VS and Training already call a select function: their lines are unchanged (the wrapper does the rest). The special melees share `gmVsMelee_CssData`/`SssData` and have a `GS_CSS` state each whose `on_enter` fills `css->vs` from the VS data: add the line after that fill. Check, for each, which `on_enter` function the state names (the audit column) and that a stage select state follows. **Oracle for the finish test:** `fs_css_finish`'s writes (`slot_type`, `ckind`, `color`, `cpu_level`, `team` and the team colour functions `gm_801692BC`, `gm_80169290`, `gm_80169264`), which stay in the game-side finish code that the adapter calls: this group's finish test is therefore the **Task 3 model's result applied by the unchanged legacy writer**, and the check is that the writer is called with the model's ports and nothing else. **Training:** `fe_sel_training` behaviour (one human, the dummy in the other of slots 0 and 1) is the `dummy_cpu` profile; check `Training` and the LAB start with the same fighters as before.
- [ ] **Task 10b: group 2, Classic, Adventure, All-Star** (`gmclassic.c:1148`, `gmadventure.c:1366` area, `gmallstar.c:716` area: the `gm_801B06B0(css, 0xB|0xC|0xD, ...)` callers). One player; the exit handlers read the entering port's slot through `gm_801B0730`. **Check before writing the line:** what these modes' retail CSS did beyond picking a fighter that Atlas would drop (a CPU level? the costume? stocks?): read `mncharsel.c`'s `match_type` branches (`grep -n "match_type\|REG_CLASSIC\|unk_0x0" src/melee/mn/mncharsel.c`) and list every branch in the commit message; if the retail screen shows something Atlas lacks, **say so, do not silently drop it**. The back-out (`pending_scene_change == 2`) returns to `GM_MENU` in these handlers: the model's `FINISH_BACK` must set exactly that.
- [ ] **Task 10c: group 3, Event Match** (`gmevent.c:onEnterCss`, `x44 == 1` case settled in Task 0 step 4). If `gm_801BA938` restricts the roster, implement the filter (`roster_filter = 1`: the adapter marks the restricted fighters `ok = 0` with the cell flag `AT_CELL_DISABLED`, hatched or worded, never only dimmed) and test it with a synthetic restriction; if it does not, Event is group 2's twin and needs only the line. The event flow decides **whether** a CSS state is entered (a fixed-fighter event never enters it): do not touch that decision.
- [ ] **Task 10d: group 4, Stadium** (`gmhomerun.c:61`, `gmmultiman.c:256` and the six other `GS_CSS` states of that file, Target Test in `gmmultiman.c`/`gm_...` whichever file the audit names for `0xF`). **Check first:** `gmmultiman.c:455` and `:537` call `gm_801B06B0` outside an `on_enter` (a retry path that presets the CSS data with a known fighter): read both and decide whether they enter the CSS state; the line goes only in `on_enter` functions of states whose scene is `GS_CSS`, never in a helper that other paths call. Home-Run and Multi-Man pass `stocks = 1` and `nametag` through `gm_801B06B0`: the finish test asserts both survive.
- [ ] **Per group, after the commit:** `nt atlas-profile`, `nt atlas-css`, `python tools/port/css_states.py --check`, `ppc` on each edited file; **the in-game start of a match from each mode is for Task 13**, never claimed here.

Commit per group, game repo, message `atlas step 4: group N modes use the Atlas character select (<names>)`.

---

### Task 11: The loading screen and the lobby's pick (the lobby part is last and has its own gate)

**Files:** `melee/src/melee/gm/gmfrontend_online.inc` (the loading state reads), `gmfrontend_atlas_select.inc`, `melee/pc/tests/atlas_select_render_test.c`

- [ ] **Step 1: Loading ("GET READY").** The legacy screen (`fe_screen_loading`, `FL_LOAD`, `loading_layout.json`) shows who fights where and a warm-up bar, and holds until nothing is pending, with `FE_LOAD_MIN_FRAMES` 45, `FE_LOAD_SETTLE_FRAMES` 20 and `FE_LOAD_CEILING_FRAMES` 480 (`gmfrontend.c:622 to 648`). **The hold logic is not touched.** Add a render test first (`loading_screen`: two cards and the stage name inside the matchup strip, the bar's polys inside its track at 0, 500 and 1000 permille, the text legible at 640) and then the adapter function `fas_loading_frame()` that submits two to four `gw_Ui_SelCard`s from the preload cache's players, the stage name from `Netplay_StageNameExt`, and `gw_Ui_SelProgress` from the same counter the legacy bar uses. **Which counter that is, is (unverified)**: read `fl_*` in `gmfrontend_online.inc` for the loading drawing and reuse its variable; do not invent a new progress meter.
- [ ] **Step 2: The lobby's pick.** Add profile `AT_MT_LOBBY` use: `fas_open_css(NULL, ...)` is called by the lobby with `Frontend_OnlinePick() == 1`. **Gate: do not switch this on by default until two real clients have been looked at (Task 13 item 9).** Ship it behind `MELEE_ATLAS_LOBBY=1` until then. Guards: (a) `grep -rn "netplay\|Netplay" pc/platform/gw_ui_*.c pc/platform/gw_ui_*.h` finds **nothing** (the host files never include the netplay headers; the adapter, game side, calls `Netplay_FighterAvailable` as `fs_css_roster` does today); (b) the online profile never calls `input_mask`: `grep -n "input_mask\|input_chord" pc/platform/gw_ui_native_sel.c` finds nothing; (c) `lobby_rules` in `atlas_css_test.c` passes.
- [ ] **Step 3: Run, check, commit.** `nt atlas-select-render`, `nt atlas-css`, `ppc src/melee/gm/gmfrontend.c`. Message `atlas step 4: the Atlas loading screen; the lobby's pick behind MELEE_ATLAS_LOBBY`.

---

### Task 12: Match setup and the retail rules screens (gate G6: step 5, Task 2)

MATCH SETUP is a `FrontendScreen` table already (`fe_items_vs_setup`, 10 rows with stocks, time and ratio sliders), so it is drawn by step 2's table adapter; it needs **step 5's value rows** (slider `step`, group headings, engine-owned choices). If G6 is not in, **stop after Step 1**: the screens stay on the legacy rows, which still work.

- [ ] **Step 1: Audit the retail rules data** (read-only; the result decides the tables). In `$GW_MELEE`:

```bash
grep -n "GetGameRules\|gmMainLib_[A-Za-z0-9_]*(" src/melee/mn/mnmainrule.c | head -40
grep -n "GetGameRules\|gmMainLib_[A-Za-z0-9_]*(\|item\|Item" src/melee/mn/mnitemsw.c | head -40
grep -n "gmMainLib_[A-Za-z0-9_]*(\|stage\|Stage" src/melee/mn/mnstagesw.c | head -40
grep -n "GetGameRules\|rule_values" src/melee/mn/mnruleplus.c | head -20
```

Write what each screen reads and writes into a table in the commit message. Known from the tree when this plan was written: **Rules** edits `GameRules.mode`, `time_limit`, `handicap`, `damage_ratio`, `stage_sel`, `stock_count` (`mnmainrule.c:197-203`); **More Rules** edits `stock_time_limit`, `friendly_fire`, `pause`, `score_display` and `unk_xc` (the sudden-death penalty, `mnruleplus.c:145-149`); **Item Switch** (29 items and the cursor values `0x1F`, `0x20` that appear to be "all on" and "all off") and **Random Stage Switch** (a per-stage on/off set) store their data somewhere this plan did not find: **(unverified)**; do not build those two tables until the audit names the storage.
- [ ] **Step 2: Tables with a stub-adapter test.** For each screen a `FrontendItem` table and a native test through the same stub adapter step 5 builds (`atlas_settings_stub.h`): item counts, labels, min/max/step, `visible`/`enabled`, and **round trips** (`set` then `get` returns the value; a clamped value; a field written is the field the retail screen writes). **Values that were saved in retail and must not change meaning:** `damage_ratio` is stored as the retail value (the legacy `fe_get_ratio`/`fe_fmt_ratio` pair already converts it for MATCH SETUP: reuse them, do not re-derive).
- [ ] **Step 3: The position protocol.** `FeMenuItem` rows `RULES`/`MORE RULES`/`ITEM SWITCH`/`RANDOM STAGE SWITCH` change from `FA_NATIVE` to `FA_ATLAS` (step 2's action) one at a time; a table test (the legacy `fm_position_for` is the oracle, as step 2's) proves each `(MenuKind, selection)` still maps to the same item, and `gmFrontend_NativeReturn` for the screens still retail lands on the right row.
- [ ] **Step 4: PowerPC check and commit** (`ppc src/melee/gm/gmfrontend.c`), one commit per screen, message `atlas step 4: <screen> rebuilt as an Atlas table`.

---

### Task 13: The in-game proof (a checklist for a Windows agent or the owner; nothing before this proves a look)

**Who and when.** Only when the owner is away, or let him do it; a game window steals focus. Second monitor (ask the coordinator for the position), `MELEE_VOLUME=0`, **ACE disc** for play tests (`GW_ISO_ACE`; never print a disc path), never hidden or minimised, stop by PID. Use the LAB (`mode=lab`), not Training, for anything that is not a CSS check. No screenshots as proof (one allowed only to diagnose how something looks). Evidence is the log lines and yes/no per item.

- [ ] **Step 1: Build and confirm the exe has the new code** (root `CLAUDE.md` fact 1):

```bash
tools/port/build.sh
grep -a "ui: disc art format" "$GW_BUILD_ROOT/melee-pc.exe" | head -1
grep -a "character select - Atlas" "$GW_BUILD_ROOT/melee-pc.exe" | head -1     # use the exact log string your adapter prints on open
```

Both must print a line (a stale exe prints nothing).
- [ ] **Step 2: Per group, start a match from the Atlas CSS and say yes or no to each** (record `melee-pc.log` lines `frontend: character select -`):
  1. Group 1: Versus > Melee (4:3 window `MELEE_WINDOW_W=960 MELEE_WINDOW_H=720`, then 16:9 `1920 x 1080`, then once at `640 x 480`): tabs ALL / RETAIL / ADDED; tiles with disc art on the **vanilla** disc and with **ACE**; the placeholder letters where a Geno fighter has no icon; four ports (a second pad: A joins; Z on your card leaves); CPU added and its level changed; teams from the rules; costume X and Y; START blocked with the toast until two fighters are in; B twice leaves. Then each special melee, Camera Mode and Training and the LAB: **behaviour unchanged** (the same fighters, costumes, CPU dummy).
  2. Group 2: Classic, Adventure, All-Star: the fighter, costume and **stocks and nametag** reach the match (the HUD name tag is the check), Back returns to the menu.
  3. Group 3: an Event whose retail CSS appears; one that skips it still skips it.
  4. Group 4: Target Test, Home-Run, each Multi-Man mode.
  5. The stage select (VS and Training): ALL / RETAIL / ADDED, 4:3 and 16:9, custom stages from a mod, a locked stage cannot be picked on a fresh save (`MELEE_UNLOCK_ALL` unset), Random.
  6. Mouse: hover moves the leading port's cursor, a resting pointer does not steal it from a pad, click picks, right click backs, the wheel turns costumes over a card.
  7. **Frame cost** with the CSS up: `gd.ui.state().cost_ms`-style numbers for the native screen (the host logs them under `ui:`) at most 0.5 ms, entries under 3,000; the frame holds 120 fps with `MELEE_FPS=120`.
  8. **Reduced Motion** on: the fade is a cut.
  9. **Online** (only with a second client and the owner's consent; otherwise write "not run"): host and join by code, the lobby's pick with `MELEE_ATLAS_LOBBY=1` and with it off, a fighter the opponent lacks cannot be picked, strikes and bans still work (drawn by the legacy lobby), a full match, and the log shows no `input_mask` from Atlas code.
  10. **Leaks:** after every scene exit (a match start, Back, a forced `gd.scene_launch`) **nothing of the CSS stays on screen**, in the match, in the results and at the next menu.
  11. **Disc-art formats:** list the `ui: disc art format N not decoded` lines, if any: they say whether CMPR is needed (Task 7).
- [ ] **Step 3: Report** yes/no for every numbered item with one line per no, plainly stating which were not run and why. The owner decides whether the look is accepted.

---

### Task 14: Retire the legacy path (after the owner's look, and for the lobby after the two-client look)

**Not part of the same session as the look.** When the owner has accepted groups 1 to 4 and, separately, the lobby:

- [ ] **Step 1: Delete, in this order, each with its grep proving nothing else reads it:** `MELEE_NATIVE_CSS` and `Frontend_NativeSelect` (`gw_uigen.c:373`, `gmfrontend.c:776`: after this, `gmFrontend_AtlasSelect` never returns to the retail screen for a **known** profile; an unknown `match_type` still falls back, **keep that**); `Frontend_TrainingSelect` and `gd.training_select` (this is a **public API**: removing it is a version change under `docs/scripting.md` "Versioning": list it in `gd.deprecated` for one version first, do not delete it in the same change); the **drawing** half of `gmfrontend_select.inc` (`fs_build_css`, `fs_build_sss`, `fs_tile_rect`, `fs_card_rect` and the art-lending helpers `fs_art_tex`, `fs_drop_borrowed`), keeping the finish code the adapter calls; the unwired `out_nav` art for rules and grids (`list_rules`, `list_more_rules`, `grid_items`, `grid_stages` in `menu/pipeline/nav.py` and `menu/out_nav/`), after `menu/README.md` and the art table are updated; `MELEE_ATLAS_LOBBY`.
- [ ] **Step 2: Guards.** `grep -rn "fs_build_css\|fs_art_tex\|MELEE_NATIVE_CSS" melee/src melee/pc` finds nothing; `nt atlas-*`, `nt controls-remap`, the Lua baselines and `python tools/port/css_states.py --check` pass; `tools/port/fe_menu_sweep.py` if it runs without a disc **(unverified)**.
- [ ] **Step 3: Docs in the same change.** `docs/TERMINOLOGY.md`: add **mode profile** (what one mode's character select may do: players, CPU, teams, fixed fighter; a table keyed by `CSSMatchType`), **port card** (the 56 px card of one port: numeral, shape, colour, name; CPU hatched), **band** (the strip between the primary pane and the keys) and **native owner** (the host-side owner of a screen the game side builds); `menu/CLAUDE.md` (the layout table: the new files, and that disc art is decoded in memory and never stored); `docs/NEXT-SESSION.md` only if the coordinator asks. Nothing public mentions private branches or paths.
- [ ] **Step 4: Commit** (both repos), message `atlas step 4: retire the legacy character and stage select drawing`.

---

## Self-review

**Spec coverage (13.4).**

| 13.4 item | Where |
|---|---|
| Screens: CHARACTERS, STAGES, MATCH SETUP, LOADING, Rules, More Rules, Item Switch, Random Stage Switch | CSS: Tasks 3, 5, 6, 9; SSS: Task 8; loading: Task 11; MATCH SETUP and the retail rules: Task 12 (gated) |
| ONE character select for every mode, mode profile, modes migrate in groups | Task 2 (profile), Tasks 9 and 10 (one entry point, four groups: VS family with Training and LAB; Classic, Adventure, All-Star; Event; Stadium) |
| Disc-art cells (item 8), port cards, strike/ban-capable stage grid (drawing only), the profile mechanism, `CSSData`/`SSSData` unchanged | Tasks 7, 5, 8, 2, and the finish tests of Task 10 |
| Retired: retail CSS/SSS once the last mode moved, `MELEE_NATIVE_CSS`, `Frontend_NativeSelect`, `gmfrontend_select.inc` drawing, unwired `out_nav` art, `Frontend_TrainingSelect` | Task 14 (after the look; `gd.training_select` is public API and goes through `gd.deprecated`) |
| Verified without the game: layout tests with 26, 29, 60 fighters at three widths; focus tests (4 ports, token per port, CPU toggles); a table test of each mode's profile against the mode file | Task 6 (26, 29, 60 and 129), Task 3 (`ports_*`, cards, CPU), Tasks 0 and 2 (the audit and the table test) |
| Must be seen | Task 13 |

**Gaps, deviations and unverified items.**
1. **Pages become tabs and scrolling.** The legacy CSS and SSS turn pages with L and R; Atlas shows ALL / RETAIL / ADDED tabs and scrolls rows. This is the mockup's design and a **behaviour change** (the model keeps no page): the owner confirms at the look.
2. **The state count.** The spec says 23 `GS_CSS` states; a grep when this plan was written found 25 initialisers in 19 files (see Task 0). The audit script is the truth.
3. **Hatching is not built** (step 1 gap 1): disc-art frames and locked cells use a flat frame, the abbreviation and a word. The spec's own fallback.
4. **The 1P modes' retail CSS** may show things Atlas does not (a CPU level, stocks): Task 10b's first step lists them before the line is written; any loss is reported, not silent.
5. **Which stages are "added"**, the Item Switch and Random Stage Switch storage, the retail icon and portrait **GX formats** (CMPR), the overlay's handling of texture index reuse, whether `gw_Ui_SceneChanged` can be placed in the mode loop without touching more than the loop's one function, and the loading bar's counter: all **(unverified)**; each task that depends on one says how to settle it.
6. **Nothing in this plan was compiled or run.** The test code was written against the sources read and may need small corrections; where a legacy rule and a check disagree, the legacy code wins.
7. **Online:** the lobby's pick moves to Atlas only behind `MELEE_ATLAS_LOBBY` and only after a two-client look; strike and ban **decisions** are untouched (step 6).
8. **Mod screens over a select:** none are allowed (spec 8.4); Task 9's `owner_native_vs_mod` pins it.
9. The `gd.ui` Lua door and the documented 12-cell limit are **unchanged**; `docs/scripting.md` needs no edit in this step.

**Placeholder scan.** No step defers a decision without naming the unknown and the command or file that settles it; shim names that depend on step 2 are marked `spec` and replaceable in one table.

**Type and name consistency.** `AtCss`, `AtCssPort`, `AtCssIn`, `AT_CE_*`, `AT_CI_*`, `AT_CK_*` (Task 3) are used unchanged by Tasks 8, 9, 10; `AtSss` (Task 8) by Task 9; `AtTab`, `AtPortCard`, `AT_BAND_*`, `ext`/`ext_n`, `at_block_cell`, `at_layout_split`, `at_grid_cols` (Task 4) by Tasks 5, 6, 9; `at_part_port_card`, `at_port_mark`, `at_cell_brackets`, `AtSink.image` (Task 5) by Tasks 6 and 8; `gw_Kit_TexAddHsd` (Task 7) by Task 9's `gw_Ui_ArtDecode`; `sty_*` (Task 1) by Tasks 5, 6, 8.

**Review Focus pinned.** 1: Task 2, Task 3 `finish_*`, Task 10; 2: Task 1 and every later part and screen test; 3: Task 4 `ext_cells_never_copied`, Task 7 `decode_copies_pixels`, Task 9 `closed_on_every_exit`, Task 5 `sink_without_image_is_safe`; 4: Task 3 `ports_*`, Task 5 `two_cursors_one_cell`; 5: Task 4, Task 6 `rosters_at_three_widths`, Task 8 `stages_256`; 6: Task 7, Task 6 `placeholder_when_no_art`; 7: Task 3 `legacy_rules_*`; 8: Task 6 `hits_follow_layout`, Task 9 `mouse_port`; 9: Task 9 `owner_native_vs_mod`; 10: Task 11 guards and gate.

**Execution recommendation.** A fresh subagent per task with a review between tasks for Tasks 1 to 8 (self-contained, each ends in a test the reviewer can run); Tasks 9 and 11 by one agent in order (shared shim vocabulary); Task 10 one agent per group, each with the table test and `ppc` output shown in the report; Task 12 only after step 5's Task 2; Tasks 13 and 14 for a Windows agent or the owner, in that order, not in one session.
