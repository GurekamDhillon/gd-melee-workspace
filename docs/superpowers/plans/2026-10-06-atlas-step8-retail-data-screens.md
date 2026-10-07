# Atlas step 8: the retail screens rebuilt from data: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the retail screens whose content is *data the game already holds* as Atlas screens fed from that data: **Event Match** (the 51-event list and its detail), **Name Entry** (the tag list and a 4-cell tag editor), **Data > Sound Test**, **Data > Special Messages**, **Data > Records** (VS, Bonus, Misc) and the **Results** scene (a `REPLACE` stand-in, behind a switch until the owner has looked). Each screen is its own go or no-go; a screen that proves too costly is dropped without holding the others up. **Not in this step, by the owner's word:** Movies, Staff Roll and Snapshots (they stay retail behind a native hand-off), the vanilla Training panel (the LAB covers it), the opening movie and the memory-card prompt (video and a boot blocker). **The title** was taken by step 2 as an `OVERLAY`; step 8 only verifies it (Task 11).

**Architecture:** (1) A pure C decoder of the retail text stream (`gw_ui_retailtext.c`) so the screens whose words live on the disc can read them at run time and never store them; a **go or no-go gate** (Task 1) decides which text-dependent screens ship in full, in part, or not at all. (2) A pure C data model (`gw_ui_data.c`): a window over a long list, the formatters, and the turn of a row set into an Atlas list screen. (3) Per-screen pure models that take **scalars, not callbacks** (game-side C cannot hand the host a function pointer): Misc records, events, messages, rankings, the tag editor, the results card set. (4) One game-side adapter, `gmfrontend_atlas_data.inc`, that owns a cursor and a window per screen, gathers the scalars from the retail getters, submits rows through scalar shims and applies the host's events. It opens from the existing `FA_NATIVE` rows **without changing any table row** (the position protocol, `fm_position_for`, the `SEL_*` numbers and the retail back-out are untouched). (5) `REPLACE` for results through step 2's `gmFrontend_AtlasStandIn`.

**Tech Stack:** C11 host code built and tested through `tools/port/native_test.sh` (no game, no disc); game-side retargeted C checked with `clang --target=powerpc-unknown-eabi -fsyntax-only`; Python 3 for the guard scripts; the step 1 harness (`atlas_check.h`, `atlas_fake.h`, `atlas_rec.h`).

**Spec:** `docs/superpowers/specs/2026-10-06-menu-reunification-design.md`, section 13.8 (this step), with sections 2 (the owner's answers), 6.4, 6.7, 6.8, 10, 12 item 8, 14, 15. Form and harness: `docs/superpowers/plans/2026-10-06-atlas-step1-components-and-envoy-bag.md`. The gate script: `docs/superpowers/plans/2026-10-06-atlas-step6-online-room.md` Task 0.

**Status of the plan:** written 2026-10-06 against the game tree as merged through step 2 (`melee/src/melee/gm/gmfrontend_atlas.inc`, `melee/pc/platform/gw_ui_policy.c`, `gw_script_ui.inc`, `gm_1A3F.c:190-205`) and read in: `gmevent.c`, `mn/mnevent.c`, `gmresult.c`, `gmresultplayer.c`, `gmtitle.c`, `mn/mnname.c`, `mn/mnnamenew.c`, `mn/mnsoundtest.c`, `mn/mninfo.c`, `mn/mninfobonus.c`, `mn/mncount.c`, `mn/mndiagram*.c` (headers and public getters only), `gm_19EF.c` (game over), `gmscdata.c`, `mnmain.c:2763-2822` (`mn_PcOpenNative`), `gmfrontend_menus.inc`, `sysdolphin/baselib/hsd_3A64.c` and `hsd_3A76.c` (the text stream). Step 3 was read on its branch `agent/atlas3` (worktree `worktrees/atlas3`, head `d9b1b1647`); steps 4 to 7 exist only as plans. **Nothing in this plan was compiled, run or seen**: every C block is unbuilt, every game fact is from source, every item marked "(unverified)" names the task that settles it.

## Corrections to the spec and the brief, found in the code

1. **The title is done.** Step 2 built it as an `OVERLAY` (`gw_ui_policy.c`, `gs_ui_overlay_try`), not a `REPLACE`; 13.8's last row ("Title, if step 2 did not take it") is moot. Task 11 checks it and does nothing else.
2. **Retail text is not Unicode and not in the source.** Event names, special messages, sound names, record labels and trophy names are `SIS` byte streams (`HSD_SisLib_803A6368(text, sis_idx)`, tables `SIS_MenuData` in `SdMenu.usd`, `SIS_ResultData` in `SdRst.usd`, `SIS_ToyData_E` in `SdToy.usd`): opcodes plus 16-bit **glyph codes** into a font atlas (`hsd_3A76.c:652-860`). Only the glyphs of the default atlas have a reverse path (the two 0x240-byte tables `HSD_SisLib_8040C680` and `lbl_8040C8C0` map SJIS pairs to glyph codes, `hsd_3A64.c:205-212`); whether the English `.usd` strings use only those glyphs is **(unverified; settled by Task 1)**. This decides how much of Events, Messages, Sound Test and Bonus records can be shown with their real words. Our own labels (stat names, "EVENT 7") are authored, never copied; game content (event names, message bodies) is read from the disc at run time or not shown.
3. **The Event list shows all 51 events**, not a progress-gated subset: `mnEvent_8024CE74()` returns the **last page's first row** (a scroll bound that grows with unlocks), the confirm path stores `first_event + page` with no lock test (`mnevent.c:405-470`), and `gmMainLib_8015CEFC(slot)` is the *cleared* flag (it gates the row's icon only). What "locked" means for an event is **(unverified; Task 6 step 1)**.
4. **Mockup "Rematch / Back to fighters / Main menu" on Results is not a retail flow.** Retail results confirms per human player with START (`fn_80178050`, `x0_0`), then runs a 10 or 20 frame countdown and calls `gm_801A4B60()` (`gmresultplayer.c:972-1060, 1595-1606`); the mode's next state decides what follows. A rematch or a main-menu exit is a new feature (spec 14). Task 10 follows retail and lists the mockup's keys as an **owner decision**.
5. **Results has a 3D winner scene.** Retail builds fighter models, cameras and animations (`gm_Scene_Results_OnEnter`: `fn_8017A67C`, `fn_8017A318`, `gmResultLoadArchive`). The mockup (`13-results.html`) shows none: a hatched two-letter frame. `REPLACE` loses the 3D pose; keeping it needs the step 10 `view` window over an `OVERLAY`. Task 10 builds the data model once and flips the policy row; the owner chooses at the look.
6. **The Language row cannot go in step 8 and may never go.** It is removed "when the last retail text screen is gone" (spec 2, answer 5), but Movies, Staff Roll and Snapshots stay retail by the owner's decision and each draws retail text. Task 11 builds the inventory; the decision is the owner's (see "Owner decisions").

## Global Constraints

Exact values come from the spec; if a task seems to need a different one, stop and ask the coordinator.

- **Canvas and layout:** 640x480 logical; compact below 760 wide, wide from 760; content at most 1140 wide, centred; margins 32; header top 22 (30 high, rule at 56), body 66 to 428, footer 434 (26 high); explainer presets narrow 160, normal 196, wide 256.
- **Text:** floor 12 px. Roles `a_cap12/14/16/20`, `a_title`, `a_hero`, `a_display` (caps only), `a_body12/14`, `a_row16`, `a_num12/14/16`. Fit rule: step down one role of the same face, then ellipsis; never squash. A string that needed the ellipsis at 640 is logged once per screen id.
- **Shape and focus:** flat quads only; chamfer top-left and bottom-right only; front edge 3 px (modal 6). Focus is three cues at once: lift 2 px, ember front edge, tick (rows) or brackets (cells). Colour is never the only signal.
- **Budgets:** one screen at most 4,096 quad-list entries (warn at 3,000); the data lists hold at most `AT_DATA_ROWS` (32) rows in the host record and window the rest; target 0.5 ms per frame per screen; the retail text probe never runs per frame (once per screen open, cached).
- **Windowing owns the cursor.** On a windowed list the **adapter** moves focus (it knows the total) and the host is told the focus with `Ui_Commit`. The host's own up and down wrap is **not** used (it would wrap inside the window). A mouse hover or click arrives as a FOCUS event with a window-relative index; the adapter adds `first`.
- **Retail untouched by default.** `MELEE_ATLAS=0` leaves every screen retail. `MELEE_ATLAS_DATA=<list>` selects Atlas data screens (`events,name,sound,messages,bonus,misc,vsrec`; default: all of those); results is chosen only by the scene policy (`MELEE_ATLAS_SCENES=5:replace`, default off until the owner has looked). With a screen off, its `FA_NATIVE` row runs the retail screen exactly as today.
- **No disc-derived data, ever.** Retail text is decoded at run time into a bounded buffer and drawn; it is **never written to a file, a log, a test fixture or a commit** (logs carry counts only: characters, unknown glyphs). Test fixtures use invented words. Disc art (fighter icons on a results card) comes from step 4's run-time decode or the hatched frame; nothing is stored.
- **Online:** none of these screens exists in a netplay session (entries are menu-only; results of a netplay match keep `RETAIL` until the owner has looked at the offline one: the policy row is added with `netplay` excluded, Task 10). No file under `pc/platform/gw_ui_*` includes a netplay header.
- **Mods work on vanilla.** Nothing here reads m-ex tables for text; fighter names on cards come from the existing fighter-name lookup (`gw_Mex_FighterName`), which already serves vanilla and ACE.
- **Credit outside assets.** Nothing outside this project is used by step 8 (no new font, icon set or idea). If a task adopts one, the same commit adds it to `CREDITS.md` with a link.
- **English only** in code, docs and strings. The retail Language setting still picks `.usd` or `.dat`; Atlas draws Latin only, so a string with a non-Latin glyph falls back to the row's authored label.
- **Naming:** `at_*` / `At*` host C, `gw_ui_*` files, `fa_*` / `fad_*` in `gmfrontend_atlas_data.inc`, shims `gw_Ui_*` (host) = `Ui_*` (game). English only.
- **Process rules (this machine):** reading, building and native tests only until Task 12. No game, launcher or browser window while the owner is at the machine. Never terminate processes by image name; stop only a process you started, by PID. Build only through `tools/port/build.sh` in a private worktree made by `tools/port/agent_new.sh`; never raw clang for the game. Max 8 `melee-pc` instances in total; keep 2 GB free. Two repositories: game repo `melee/` (branch `pc-port`, your lane `agent/<name>`) and the workspace repo (tools, docs, `CREDITS.md`). `gw_mex_bridge.c` churn from `build.sh` is normal and is not committed by you.

## Needs from earlier steps (gated by Task 0)

Names in the last column that are not yet built are assumed; Task 0 greps for them and the engineer writes the real names into `tools/port/atlas_gate.py` and into the one wrapper that calls each (marked `RECONCILE`).

| # | What step 8 needs | From | Name (built = read on main; assumed = RECONCILE) | Used by |
|---|---|---|---|---|
| N1 | A native screen submitted each frame from game-side C, events back, a registry, an Atlas fade | step 2 | built: `fa_submit`, `fa_frame`, `fa_sync`, `Ui_Begin`, `Ui_Tile`, `Ui_Explain`, `Ui_Key`, `Ui_Commit`, `Ui_PollEvent`, `Ui_Intent`, `Ui_Close`, `Ui_ScenePolicy` | all game-side tasks |
| N2 | The scene hook that swaps a scene's `on_enter`/`on_frame` | step 2 | built: `gm_1A3F.c:190-205`, `gmFrontend_AtlasStandIn(u8 kind)` returns NULL today | Task 10 |
| N3 | A **list** primary on an engine screen with rows that carry a value text, a sub line and a tag | step 5 | assumed: `AT_PRIMARY_LIST` accepted by `gw_Ui_Begin`; step 5 `AtItem.vstep/group/reason` and the table walker. If step 5 is not merged, Task 3 builds the two shims it needs (`Ui_Row`, `Ui_Counter`) over the existing step 1 list renderer | Tasks 2, 3 |
| N4 | `AT_MAX_ITEMS` 64 and the windowing pattern | steps 5, 7 | assumed: `AT_MAX_ITEMS` 64 (today 32, `gw_ui_screen.h`); step 7's `at_mods_*` window. Task 2 builds its own window and uses `AT_DATA_ROWS = AT_MAX_ITEMS` | Task 2 |
| N5 | Tabs in the screen record (VS records: FIGHTERS and TAGS) | steps 4, 5 | assumed: `AtScreen.tabs`, `gw_Ui_SetTabs`. **Soft:** without tabs Task 8 shows one list and a stat selector on L and R | Task 8 |
| N6 | Disc-art decode for the fighter icon on a results card | step 4 | assumed: `gw_Kit_TexAddHsd`, the image cell. **Soft:** the hatched two-letter frame is the fallback and the mockup's own placeholder | Task 10 |
| N7 | Port card part | step 4 | assumed: `at_part_port_card`. **Soft:** Task 10 draws its own card from step 1 parts | Task 10 |
| N8 | Retail element mask and the pause/HUD takeover | step 3 | **not needed here** (step 8 hides nothing retail); read for naming only: `AT_RS_POLICY`, `gw_Ui_RetailHidden` are step 10's | Task 11 (inventory only) |
| N9 | The gate script and its `--step` switch | step 6 | **not on main** (created by step 6 Task 0). Task 0 creates it with the same layout if absent; the later merge takes the union of the two tables | Task 0 |

## Review Focus

The failure modes most likely to bite a player first. Each is pinned by a named test.

| # | What goes wrong | Pinned by |
|---|---|---|
| 1 | **The cursor and the window disagree**: focus on row 50 of 51 with the window on the first nine; a wheel or hover event mapped with the wrong base; the host wraps inside the window. | Task 2 `window_*` checks; Task 3 `test_fe_atlas_data.py` (no `MOVE` forwarded for data screens) |
| 2 | **Back lands on the wrong item**: B from Records, Sound Test or Name Entry must return to the same `FeMenu` row the player came from (the legacy native screens return through `mn_80229894` to `(kind, sel)`). | Task 3 `test_fe_atlas_data.py` (every screen's parent `(MenuKind, SEL_*)` against `mn_PcOpenNative`) |
| 3 | **Disc text leaks**: a decoded event name reaches a log, a fixture or a file. | Task 1 `check_no_disc_text.py` (greps the new files for `OSReport`/`gw_log` calls that pass a decoded buffer) |
| 4 | **A glyph that does not decode** shows as garbage or an empty row. | Task 1 `decode_*` checks (unknown glyph becomes `?` and is counted), Task 5 `row_*` (the authored label wins) |
| 5 | **Empty and edge data**: no events cleared, zero tags, 120 tags (full list), no messages unlocked, a record with no fighters played, a 99-hour time. | Task 4 `misc_clamp`, Task 5 `event_*`, Task 6 `messages_*`, Task 8 `rank_*`, Task 9 `name_*` |
| 6 | **A screen that changes the save by looking at it**: Sound Test, Records, Messages write nothing; Name Entry writes only on confirm; Events write the selection only when the player starts one. | Task 3 guard `fad_readonly` (an allow-list of game calls per screen) |
| 7 | **Results leaves the match half-closed**: `fn_801701AC` (the results exit) not run, the music not stopped, the mode's next state wrong. | Task 10 step 1 (the side-effect table), `test_fe_atlas_results.py` |
| 8 | **Replacing results loses a per-player confirm**: one human confirms and the scene leaves for all (or never leaves when a player disconnects: `err != 0` counts as confirmed in retail). | Task 10 `confirm_*` checks |
| 9 | **Style rule breaks in this plan's own code** (chamfer corner, focus cues, text outside its plate). | the step 6 `atlas_lint.h` helpers if merged (RECONCILE), else the step 3 helpers in `atlas_rec.h` |

---

## File structure

Game repo (`melee/`).

| File | Create/Modify | Responsibility |
|---|---|---|
| `pc/platform/gw_ui_retailtext.h/.c` | Create | the SIS stream decoder (pure; takes the two lookup tables as arguments) and the SJIS subset to UTF-8 |
| `pc/platform/gw_ui_data.h/.c` | Create | window, formatters, `AtDataView` to an Atlas list screen |
| `pc/platform/gw_ui_data_models.h/.c` | Create | the per-screen scalar models: misc rows, event row, message order, rank sort, stat formatting |
| `pc/platform/gw_ui_name.h/.c` | Create | the tag editor model (4 cells, a glyph set, cursor, validation order) |
| `pc/platform/gw_ui_results.h/.c` | Create | the results card set from a `MatchEnd` summary, per-player confirm, the exit rule |
| `pc/platform/gw_script_ui.inc` | Modify | the shims `gw_Ui_Row*`, `gw_Ui_Counter`, `gw_Ui_SisDecode`, `gw_Ui_ResBegin`/`ResPlayer`/`ResCommit` |
| `src/melee/gm/gmfrontend_atlas_data.inc` | Create | the adapter: `fad_*` (screens table, cursor, window, text helper, per-screen row sources) and the results stand-in |
| `src/melee/gm/gmfrontend.c`, `gmfrontend_menus.inc`, `gmfrontend_atlas.inc` | Modify | include the new `.inc`; `fm_confirm` hook before the `FA_NATIVE` case; `fa_frame`/`fa_sync` early branch; `gmFrontend_AtlasStandIn` returns the results pair |
| `src/melee/gm/gmresult.c` | Modify | nothing unless Task 10 step 1 finds a retail side effect that must be exposed (then one `TARGET_PC` accessor) |
| `pc/tests/atlas_retailtext_test.c`, `atlas_data_test.c`, `atlas_models_test.c`, `atlas_name_test.c`, `atlas_results_test.c` | Create | one native test per unit |

Workspace repo (root).

| File | Create/Modify | Responsibility |
|---|---|---|
| `tools/port/atlas_gate.py` | Create or modify | `--step 8` (and the layout step 6 defined) |
| `tools/port/test_fe_atlas_data.py` | Create | static guards on the adapter and the entry hook (Review Focus 1, 2, 6) |
| `tools/port/check_no_disc_text.py` | Create | Review Focus 3 |
| `tools/port/test_fe_atlas_results.py` | Create | the stand-in's exit and side-effect list (Review Focus 7) |
| `tools/port/retail_screens.py`, `retail_screens_expected.json` | Create | the inventory of retail screens left (the Language row question) |
| `tools/port/native_test.sh` | Modify | cases `atlas-retailtext`, `atlas-data`, `atlas-models`, `atlas-name`, `atlas-results` |
| `docs/TERMINOLOGY.md`, `menu/CLAUDE.md`, `docs/NEXT-SESSION.md`, `docs/scripting.md` (only if a shim becomes a `gd.ui` call: it does not) | Modify | the terms (data screen, retail text), the retirement list, the state |

## Preflight (once, before Task 0; not a task)

- [ ] **Step 1: Read.** `CLAUDE.md` (root), `docs/NEXT-SESSION.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md`, the spec sections 2, 6.4, 6.7, 6.8, 13.8, 13.10 (for what step 10 will reuse), `melee/src/melee/gm/gmfrontend_atlas.inc` whole, `gmfrontend_menus.inc` lines 100-300 and 1313-1420, `gm_1A3F.c` lines 150-210, `mn/mnmain.c` lines 2763-2822, `pc/platform/gw_ui_policy.c`, `gw_script_ui.inc` lines 700-1010.
- [ ] **Step 2: A private lane and the shell** (same as step 1; names changed):

```bash
export MAIN="<the workspace root: the directory that contains tools/ and _toolchains/>"
cd "$MAIN" && tools/port/agent_new.sh atlas8
git -C "$MAIN" worktree add worktrees/ws-atlas8 -b ws/atlas8
export WS="$MAIN/worktrees/ws-atlas8"; export GW_ROOT="$MAIN"
export GW_MELEE="$MAIN/worktrees/atlas8"; export GW_BUILD_ROOT="$MAIN/_build/agents/atlas8"   # as agent_new.sh printed them
nt() { GW_ROOT="$MAIN" GW_MELEE="$GW_MELEE" GW_BUILD_ROOT="$GW_BUILD_ROOT" bash "$WS/tools/port/native_test.sh" "$1"; }
```

- [ ] **Step 3: Baselines** (must still pass at the end): every `atlas-*` case the merged steps added, for example `for t in atlas-tokens atlas-layout atlas-focus atlas-input atlas-screen atlas-stack atlas-parts atlas-render atlas-tiles atlas-registry atlas-policy; do nt $t | tail -1; done` and `lua pc/tests/atlas_ui_stub_test.lua | tail -1`. Expected: each ends `N checks, 0 failed`.
- [ ] **Step 4: Which steps are merged.** `git -C "$GW_MELEE" log --oneline -20` and run `python "$WS/tools/port/atlas_gate.py" --step 8` once Task 0 exists. Tasks 1 to 3 need only step 2 and may start before steps 4, 5 and 7 merge.

---

### Task 0: The gate and the retail inventory

**Files:** Create or modify (workspace repo) `tools/port/atlas_gate.py`; create `tools/port/retail_screens.py` and `retail_screens_expected.json`.

**Interfaces:** `python tools/port/atlas_gate.py --step 8 [--melee PATH]` exits 0 when every hard requirement is present, prints `SOFT` lines for the soft ones (they never fail the exit), and names the owner step.

- [ ] **Step 1: Write the table.** If `tools/port/atlas_gate.py` does not exist, create it exactly as step 6 Task 0 does (same `main`, same exit rules) and add this entry; if it exists, add this entry to `G` and a `SOFT` list beside it:

```python
    8: [
        ("src/melee/gm/gmfrontend_atlas.inc", r"\bfa_submit\b", "step 2", "N1 the adapter submits a screen each frame"),
        ("src/melee/gm/gmfrontend_atlas.inc", r"gmFrontend_AtlasStandIn", "step 2", "N2 the REPLACE hook"),
        ("src/melee/gm/gm_1A3F.c", r"Ui_ScenePolicy", "step 2", "N2 the scene table hook"),
        ("pc/platform/gw_ui_policy.c", r"AT_POLICY_REPLACE", "step 2", "N2 the policy table"),
    ],
```

and, in the same file, `SOFT = { 8: [ ("pc/platform/gw_ui_item.h", r"at_item_apply", "step 5", "N3 value rows"), ("pc/platform/gw_ui_screen.h", r"\btabs\b", "steps 4,5", "N5 tabs"), ("pc/platform/gw_kit.h", r"gw_Kit_TexAddHsd", "step 4", "N6 disc-art decode"), ("pc/platform/gw_ui_parts.h", r"at_part_port_card", "step 4", "N7 port card") ] }`. In `main`, after the hard loop, print `SOFT   <file> <owner> <why>` for each soft entry whose regex is absent (no exit change).

- [ ] **Step 2: Run it and record.** `python tools/port/atlas_gate.py --step 8` today (steps 2 merged; 4, 5, 7 not): exit 0, four `SOFT` lines. That is correct. If a hard line is MISSING the step 2 names changed: reconcile the table, do not weaken a regex.
- [ ] **Step 3: The inventory script.** `tools/port/retail_screens.py` reads `mn/mnmain.c` `mn_PcOpenNative` and `gmscdata.c` and prints, for each native screen entry point, whether an Atlas screen replaces it (a `fad_screens[]` row or a policy row) or it stays retail, as JSON:

```python
"""Which retail screens are still retail: python tools/port/retail_screens.py [--melee PATH] [--json]"""
import json, os, re, sys

def entries(text):
    body = text[text.index("static void mn_PcOpenNative"):]
    body = body[:body.index("not a native screen")]
    out = []
    for km in re.finditer(r"case (MENU_KIND_\w+):(.*?)(?=case MENU_KIND_|\Z)", body, re.S):
        kind, seg = km.group(1), km.group(2)
        for m in re.finditer(r"(?:case (SEL_\w+):|if \(sel == (SEL_\w+)\)\s*\{?)(.*?)return;", seg, re.S):
            calls = re.findall(r"\b(\w+)\(", m.group(3))
            out.append((kind, m.group(1) or m.group(2), calls[-1] if calls else "?"))
    return out

def main(argv):
    root = os.environ.get("GW_MELEE", "")
    melee = next((argv[i + 1] for i, a in enumerate(argv) if a == "--melee"), root)
    mn = open(os.path.join(melee, "src/melee/mn/mnmain.c"), encoding="utf-8", errors="replace").read()
    atl = os.path.join(melee, "src/melee/gm/gmfrontend_atlas_data.inc")
    covered = open(atl, encoding="utf-8").read() if os.path.exists(atl) else ""
    rows = [{"kind": k, "sel": s, "retail_fn": f, "atlas": bool(re.search(r"\b" + re.escape(s) + r"\b", covered))} for k, s, f in entries(mn)]
    print(json.dumps(rows, indent=1) if "--json" in argv else "\n".join("%-20s %-22s %-28s %s" % (r["kind"], r["sel"], r["retail_fn"], "ATLAS" if r["atlas"] else "retail") for r in rows))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Run it: it lists the 15 entry points of `mn_PcOpenNative` (Event, Rules, Name Entry, Rumble, Sound, Display, Language, Erase, Snapshots, Movies, Sound Test, Special Messages, the three Records) all `retail` today (it was run against the merged tree while writing this plan and printed exactly these 15). Save that output as `tools/port/retail_screens_expected.json` (it is the starting inventory the owner's Language-row question reads: step 5 owns Rumble, Display, Language, Erase and Rules; step 4 owns Rules; this step the rest; Movies and Snapshots stay).

- [ ] **Step 4: Commit (workspace repo).** `tools: atlas_gate.py step 8 table, retail_screens.py (the inventory of screens still retail)`.

---

### Task 1: The retail text decoder and the text gate

The decision this task makes is the most important in the step: **which screens can show the disc's own words.** Everything else in step 8 is independent of it.

**Files:**
- Create (game repo): `pc/platform/gw_ui_retailtext.h/.c`, `pc/tests/atlas_retailtext_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-retailtext`), create `tools/port/check_no_disc_text.py`

**Interfaces:**
Produces `at_sis_decode(...)` and `at_sjis_to_utf8(...)`; consumes nothing. The game side passes the retail tables as arguments, so the host never links the game's data.

- [ ] **Step 1: Write the failing test** `pc/tests/atlas_retailtext_test.c`. The tables here are **invented**: a 4-pair lookup with the SJIS codes the retail encoder itself uses (`HSD_SisLib_803A67EC`, `hsd_3A64.c:137-219`: digits `0x82 (c+0x1F)`, capitals `0x82 (c+0x1F)`, lower case `0x82 (c+0x20)`, space `0x8140`):

```c
#include "atlas_check.h"
#include "../platform/gw_ui_retailtext.h"

/* invented glyph codes for "A", "b", "7" and the space; SJIS pairs as the retail encoder writes them */
static const unsigned char GLYPH[8] = { 0x20, 0x41, 0x20, 0x62, 0x20, 0x37, 0x20, 0x00 };
static const unsigned char SJIS[8]  = { 0x82, 0x60, 0x82, 0x82, 0x82, 0x56, 0x81, 0x40 };

int main(void)
{
    char out[64]; AtSisStats st;
    /* opcode 10 (+4 operand bytes) then glyphs then the end opcode, as the encoder lays a line out */
    const unsigned char s1[] = { 10, 0, 0, 0, 0, 0x20, 0x41, 0x20, 0x62, 0x20, 0x00, 0x20, 0x37, 0 };
    CHECK(at_sis_decode(GLYPH, SJIS, 4, s1, out, sizeof out, &st) == 4);
    CHECK_STR(out, "Ab 7");
    CHECK(st.chars == 4 && st.unknown == 0 && st.controls == 1 && st.bad == 0);

    /* an unknown glyph becomes '?' and is counted; the text still comes out */
    { const unsigned char s[] = { 0x20, 0x41, 0x2F, 0xFF, 0x20, 0x62, 0 };
      CHECK(at_sis_decode(GLYPH, SJIS, 4, s, out, sizeof out, &st) == 3);
      CHECK_STR(out, "A?b"); CHECK(st.unknown == 1); }

    /* newline (opcode 3) becomes a newline; colour (12, +3) and scale (14, +4) are skipped */
    { const unsigned char s[] = { 12, 255, 0, 0, 0x20, 0x41, 3, 14, 1, 0, 1, 0, 0x20, 0x62, 0 };
      CHECK(at_sis_decode(GLYPH, SJIS, 4, s, out, sizeof out, &st) == 3);
      CHECK_STR(out, "A\nb"); CHECK(st.controls == 3); }

    /* a jump (8, 9) is not followed: the walk stops and says so; an unknown opcode stops it and says so */
    { const unsigned char j[] = { 0x20, 0x41, 8, 0, 0, 0, 0, 0 };
      CHECK(at_sis_decode(GLYPH, SJIS, 4, j, out, sizeof out, &st) == 1); CHECK(st.jumps == 1);
      { const unsigned char u[] = { 0x20, 0x41, 29, 0x20, 0x62, 0 };
        CHECK(at_sis_decode(GLYPH, SJIS, 4, u, out, sizeof out, &st) == 1); CHECK(st.bad == 1); } }

    /* output never overruns: a 3-byte buffer holds 2 characters and a terminator */
    { char tiny[3]; const unsigned char s[] = { 0x20, 0x41, 0x20, 0x62, 0x20, 0x37, 0 };
      CHECK(at_sis_decode(GLYPH, SJIS, 4, s, tiny, sizeof tiny, &st) == 2); CHECK_STR(tiny, "Ab"); }

    /* the SJIS subset the retail encoder itself emits */
    { char u[5];
      CHECK(at_sjis_to_utf8(0x82, 0x4F, u) == 1 && u[0] == '0');   /* digits: 0x82, c + 0x1F */
      CHECK(at_sjis_to_utf8(0x82, 0x60, u) == 1 && u[0] == 'A');   /* capitals */
      CHECK(at_sjis_to_utf8(0x82, 0x81, u) == 1 && u[0] == 'a');   /* lower case: c + 0x20 */
      CHECK(at_sjis_to_utf8(0x81, 0x40, u) == 1 && u[0] == ' ');
      CHECK(at_sjis_to_utf8(0x81, 0x46, u) == 1 && u[0] == ':');
      CHECK(at_sjis_to_utf8(0x81, 0x7C, u) == 1 && u[0] == '-');
      CHECK(at_sjis_to_utf8(0x83, 0x41, u) == 0);                  /* kana: not in the Latin subset */ }
    ATLAS_DONE("atlas retailtext");
}
```

Register `atlas-retailtext)` with `sources=(pc/tests/atlas_retailtext_test.c pc/platform/gw_ui_retailtext.c)`.

- [ ] **Step 2: Run to see it fail** (`nt atlas-retailtext`: the header is missing).
- [ ] **Step 3: Implement.** `gw_ui_retailtext.h`:

```c
/* gw_ui_retailtext.h - decode a retail SIS string (opcodes plus 16-bit glyph codes) to UTF-8, using the font's own SJIS lookup run in reverse. Pure C. */
#ifndef GW_UI_RETAILTEXT_H
#define GW_UI_RETAILTEXT_H
#ifdef __cplusplus
extern "C" {
#endif
typedef struct { int chars, unknown, controls, jumps, bad; } AtSisStats;
/* lut_glyph[2k..2k+1] is the glyph code of lut_sjis[2k..2k+1] (the pair of HSD_SisLib_8040C680 and lbl_8040C8C0, npairs of them).
 * Returns the characters written (a newline counts); out is always terminated. Never reads past a terminating 0 opcode, a jump or an
 * unknown opcode; at most 1024 stream bytes are walked. */
int at_sis_decode(const unsigned char *lut_glyph, const unsigned char *lut_sjis, int npairs, const unsigned char *s, char *out, int cap, AtSisStats *st);
/* the Latin subset: 1 and out[0] set for ASCII; 0 when the code is outside it (kana, kanji) */
int at_sjis_to_utf8(unsigned hi, unsigned lo, char out[5]);
#ifdef __cplusplus
}
#endif
#endif
```

`gw_ui_retailtext.c`:

```c
#include "gw_ui_retailtext.h"
#include <string.h>

/* operand bytes after each opcode, read from the stream interpreter (HSD_SisLib_803A84BC, hsd_3A76.c:652-870): 5 delay u16, 6 two u16,
 * 7 line origin two s16, 8/9 jump pointer, 10 scale two s16, 12 colour rgb, 14 size two u16; the rest take none. 27..31: not seen. */
static const signed char OPERANDS[32] = {
    0, 0, 0, 0, 0, 2, 4, 4, 4, 4, 4, 0, 3, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1, -1
};

int at_sjis_to_utf8(unsigned hi, unsigned lo, char out[5])
{
    int c = 0;
    if (hi == 0x82 && lo >= 0x4F && lo <= 0x58) c = '0' + (int) (lo - 0x4F);
    else if (hi == 0x82 && lo >= 0x60 && lo <= 0x79) c = 'A' + (int) (lo - 0x60);
    else if (hi == 0x82 && lo >= 0x81 && lo <= 0x9A) c = 'a' + (int) (lo - 0x81);
    else if (hi == 0x81) {
        switch (lo) {
        case 0x40: c = ' '; break;  case 0x43: c = ','; break;  case 0x44: c = '.'; break;  case 0x46: c = ':'; break;
        case 0x66: c = '\''; break; case 0x68: c = '"'; break;  case 0x7C: c = '-'; break;
        default: break;          /* more punctuation is added when the Task 1 probe lists it as an unknown glyph */
        }
    }
    if (c == 0) { out[0] = '\0'; return 0; }
    out[0] = (char) c; out[1] = '\0';
    return 1;
}

int at_sis_decode(const unsigned char *lg, const unsigned char *ls, int npairs, const unsigned char *s, char *out, int cap, AtSisStats *st)
{
    AtSisStats z; int i = 0, n = 0, steps = 0;
    memset(&z, 0, sizeof z);
    if (cap <= 0) return 0;
    out[0] = '\0';
    while (steps++ < 1024) {
        unsigned op = s[i];
        if (op >= 0x20) {
            unsigned g = ((unsigned) s[i] << 8) | s[i + 1];
            char u[5]; int k, ok = 0;
            i += 2;
            for (k = 0; k < npairs; k++)
                if ((((unsigned) lg[2 * k] << 8) | lg[2 * k + 1]) == g) { ok = at_sjis_to_utf8(ls[2 * k], ls[2 * k + 1], u); break; }
            if (!ok) { u[0] = '?'; u[1] = '\0'; z.unknown++; }
            z.chars++;
            if (n + 1 < cap) { out[n++] = u[0]; out[n] = '\0'; }
            continue;
        }
        if (op == 0) break;
        if (op == 8 || op == 9) { z.jumps++; break; }
        if (OPERANDS[op] < 0) { z.bad++; break; }
        if (op == 3 && n + 1 < cap) { out[n++] = '\n'; out[n] = '\0'; z.chars++; }
        i += 1 + OPERANDS[op];
        z.controls++;
    }
    if (st) *st = z;
    return n;
}
```

(Check against the test: `s1` = opcode 10 + 4 operand bytes, then four glyphs including the invented space glyph `0x2000`; the opcode-3 case counts both a control and a character: in the test `controls == 3` is colour + newline + scale, so the newline must count as a control as well. It does: `z.controls++` runs for opcode 3 after the newline is written.) The glyph byte order (`hi` byte first) and the glyph range are the retail encoder's own (`data[out_idx++] = HSD_SisLib_8040C680[lut*2]; ...[lut*2+1]`); the in-game round trip of Step 5 confirms them.

- [ ] **Step 4: Run to pass.** `nt atlas-retailtext | tail -1` prints `atlas retailtext: 25 checks, 0 failed` (count approximate).
- [ ] **Step 5: The game-side helper and the round trip.** In `src/melee/gm/gmfrontend_atlas_data.inc` (created here; Task 3 adds the rest) write the helper **under `TARGET_PC`** and call the self-check once from `fa_scene_enter` of the Data screens (Task 3):

```c
/* Retail text: open the SIS table the retail screen would (SdMenu.usd / SIS_MenuData in the saved language), decode one string at
 * run time into the caller's buffer. The archive handle is kept for the scene; nothing is stored, nothing is logged but counts. */
static HSD_Archive* fad_sis_arc;
static SIS** fad_sis_tab;
extern int Ui_SisDecode(const u8* glyph, const u8* sjis, int npairs, const u8* sis, char* out, int cap, int* stats5);

static bool fad_sis_open(void)
{
    if (fad_sis_tab != NULL) {
        return true;
    }
    fad_sis_arc = HSD_SisLib_803A945C(lbLang_IsSavedLanguageJP() ? "SdMenu.dat" : "SdMenu.usd");
    if (fad_sis_arc == NULL) {
        return false;
    }
    fad_sis_tab = (SIS**) HSD_ArchiveGetPublicAddress(fad_sis_arc, "SIS_MenuData");
    return fad_sis_tab != NULL;
}

/* 1 when decoded with no unknown glyph; 0 when partly or not decodable (out still holds what came out) */
static int fad_sis_text(int sis_idx, char* out, int cap)
{
    int st[5];
    out[0] = '\0';
    if (!fad_sis_open() || fad_sis_tab[sis_idx] == NULL) {
        return 0;
    }
    Ui_SisDecode(HSD_SisLib_8040C680, lbl_8040C8C0, 0x120, (const u8*) fad_sis_tab[sis_idx], out, cap, st);
    return st[1] == 0 && st[4] == 0 && out[0] != '\0';
}

/* the self-check that needs no disc text: encode a known string with the retail encoder, decode it back */
static void fad_sis_selfcheck(void)
{
    static const char probe[] = "Ab 09:.-";
    u8 buf[0x100];
    char back[32];
    int st[5];
    HSD_SisLib_803A67EC(buf, (u8*) probe);
    Ui_SisDecode(HSD_SisLib_8040C680, lbl_8040C8C0, 0x120, buf, back, sizeof back, st);
    OSReport("frontend: sis round trip %s (chars %d, unknown %d, bad %d)\n", strcmp(back, probe) == 0 ? "ok" : "FAILED", st[0], st[1], st[4]);
}
```

Add the host shim in `gw_script_ui.inc`: `int gw_Ui_SisDecode(const unsigned char *g, const unsigned char *j, int n, const unsigned char *s, char *out, int cap, int *st5) { AtSisStats st; int r = at_sis_decode(g, j, n, s, out, cap, &st); if (st5) { st5[0] = st.chars; st5[1] = st.unknown; st5[2] = st.controls; st5[3] = st.jumps; st5[4] = st.bad; } return r; }`. (`0x120` is `ARRAY_SIZE(HSD_SisLib_FontAtlas)`: use the macro if the `.inc` can see it, else a `_Static_assert` on `sizeof(HSD_SisLib_8040C680) == 0x240`.)
- [ ] **Step 6: The disc-text guard.** `tools/port/check_no_disc_text.py`: fail when a line in `gmfrontend_atlas_data.inc` or `gw_ui_data*.c` passes a buffer that `fad_sis_text` filled to `OSReport`, `gw_log`, `printf`, `fprintf` or `fwrite`:

```python
"""python tools/port/check_no_disc_text.py [--melee PATH]: decoded retail text must never reach a log or a file."""
import os, re, sys
FILES = ["src/melee/gm/gmfrontend_atlas_data.inc", "pc/platform/gw_ui_data.c", "pc/platform/gw_ui_data_models.c", "pc/platform/gw_ui_name.c", "pc/platform/gw_ui_results.c"]
SINKS = re.compile(r"\b(OSReport|gw_log|printf|fprintf|fwrite|fputs|puts)\s*\(")
TEXTY = re.compile(r"\b(name|desc|msg|text|label|buf|txt)\w*\b|%s")
def main():
    root = os.environ.get("GW_MELEE", "")
    root = sys.argv[sys.argv.index("--melee") + 1] if "--melee" in sys.argv else root
    bad = 0
    for rel in FILES:
        p = os.path.join(root, rel)
        if not os.path.exists(p): continue
        for n, line in enumerate(open(p, encoding="utf-8").read().splitlines(), 1):
            if SINKS.search(line) and "%s" in line and "OK-NOTEXT" not in line and rel.endswith(("inc", "c")) and TEXTY.search(line.split("(", 1)[1]):
                print("%s:%d: a log call formats a string: %s" % (rel, n, line.strip())); bad += 1
    print("check_no_disc_text: %d problem(s)" % bad)
    return 1 if bad else 0
sys.exit(main())
```

A log line that prints an authored string (a screen id) adds `/* OK-NOTEXT */`. Run it on the files as they stand: exit 0.
- [ ] **Step 7: Commit.** Game repo: `gw_ui_retailtext.h/.c`, test, the helper block; workspace repo: `native_test.sh`, `check_no_disc_text.py`. Messages: `atlas: retail text decoder (SIS stream to UTF-8, the font's SJIS table in reverse), counts only` and `tools: atlas-retailtext test case, check_no_disc_text.py`.
- [ ] **Step 8: The gate decision (a Windows agent, while the owner is away; part of Task 12 if no agent is available earlier).** Build, run with `MELEE_ATLAS_TEXTPROBE=1` (Task 3 reads it in `fad_open`): the log must print `frontend: sis round trip ok`. Then for each text source the adapter lists (`SdMenu.usd`: event names `0x154 + 2*k` for the 51 events, the 66 message bodies via `un_802FE3F8(id, 0x4BD, &idx, NULL)`, the 30 misc labels `0xC9`..`0xE6`, the bonus labels from `0xA5`; `SdRst.usd`: the result labels; and for step 10 `SdToy.usd` `SIS_ToyData_E`) it logs **only** `frontend: sis probe <source>: <n> strings, <c> chars, <u> unknown glyphs`. Decide per source by `u / c`:
  - **GO** (0 unknown): the screen shows the disc's words.
  - **PARTIAL** (under 2 percent unknown, only punctuation): add the missing punctuation to `at_sjis_to_utf8` (one line each, read from the probe's list of unknown glyph codes, which are font indices, not text) and re-run.
  - **NO-GO** (the English strings use glyphs outside the default atlas, so there is no reverse table): the source's screens ship **without the disc's words** (rows carry the authored label and the value only; Events show "EVENT 7" and the record; Special Messages and Sound Test stay retail), and step 10's trophy chrome keeps the retail text objects visible (the partial mask of 13.10 item 4). Record the result in `docs/NEXT-SESSION.md` and in the table in Task 12.
  The result is **(unverified until this step runs)**; every task below states what it does under each outcome.

---

### Task 2: The data model: window, formatters, rows to a list screen

**Files:**
- Create (game repo): `pc/platform/gw_ui_data.h/.c`, `pc/tests/atlas_data_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (case `atlas-data`)

**Interfaces:**
Consumes `AtScreen`, `AtItem`, `AT_VAL_TEXT`, `AT_PRIMARY_LIST`, `AT_MAX_ITEMS` (`gw_ui_screen.h`). Produces `AtDataView`, `at_data_first`, `at_data_counter`, `at_fmt_count`, `at_fmt_hm`, `at_fmt_frames`, `at_data_screen`.

- [ ] **Step 1: Write the failing test** `pc/tests/atlas_data_test.c`:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_data.h"

int main(void)
{
    char b[32]; AtDataView v; AtScreen sc; int i;
    /* the window keeps focus in view, slides by one, clamps, and survives a short list */
    CHECK(at_data_first(51, 9, 0, 0) == 0);
    CHECK(at_data_first(51, 9, 8, 0) == 0);        /* the last visible row: no slide */
    CHECK(at_data_first(51, 9, 9, 0) == 1);        /* one past it: slide by one */
    CHECK(at_data_first(51, 9, 50, 0) == 42);      /* the end: the last full page */
    CHECK(at_data_first(51, 9, 3, 42) == 3);       /* a jump back up */
    CHECK(at_data_first(5, 9, 4, 3) == 0);         /* a list shorter than a page never scrolls */
    CHECK(at_data_first(0, 9, 0, 7) == 0);
    CHECK(at_data_first(51, 9, -1, 20) == 20 || at_data_first(51, 9, -1, 20) == 0);   /* a bad focus does not crash and stays in range */
    for (i = 0; i < 51; i++) { int f = at_data_first(51, 9, i, (i * 7) % 43); CHECK(f >= 0 && f <= 42 && i >= f && i < f + 9); }

    at_data_counter(b, sizeof b, 2, 51); CHECK_STR(b, "3 / 51");
    at_data_counter(b, sizeof b, 0, 0);  CHECK_STR(b, "");

    at_fmt_count(b, sizeof b, 0);        CHECK_STR(b, "0");
    at_fmt_count(b, sizeof b, 999);      CHECK_STR(b, "999");
    at_fmt_count(b, sizeof b, 1000);     CHECK_STR(b, "1,000");
    at_fmt_count(b, sizeof b, 1234567);  CHECK_STR(b, "1,234,567");
    at_fmt_hm(b, sizeof b, 0);           CHECK_STR(b, "0:00");
    at_fmt_hm(b, sizeof b, 3900);        CHECK_STR(b, "1:05");           /* seconds in, hours:minutes out, as mnCount_CreateRow does */
    at_fmt_hm(b, sizeof b, 359940);      CHECK_STR(b, "99:59");
    at_fmt_frames(b, sizeof b, 3615);    CHECK_STR(b, "01:00 25");       /* the Event record rule: minutes, seconds, 99*(t%60)/59 */
    at_fmt_frames(b, sizeof b, 0);       CHECK_STR(b, "00:00 00");

    /* a view of 3 rows in a total of 51, window at 10: the screen has 3 items, the counter says 12 / 51 for focus 11 */
    memset(&v, 0, sizeof v);
    snprintf(v.id, sizeof v.id, "data.test"); snprintf(v.title, sizeof v.title, "TEST");
    v.total = 51; v.first = 10; v.n = 3; v.focus = 11;
    snprintf(v.row[0].label, AT_STR, "EVENT 11"); snprintf(v.row[0].value, AT_STR, "01:00 25"); v.row[0].flags = AT_DR_DONE;
    snprintf(v.row[1].label, AT_STR, "EVENT 12"); snprintf(v.row[1].value, AT_STR, "--");
    snprintf(v.row[2].label, AT_STR, "EVENT 13"); snprintf(v.row[2].sub, AT_STR, "sub");
    CHECK(at_data_screen(&v, &sc) == 1);
    CHECK(sc.primary == AT_PRIMARY_LIST && sc.n_items == 3);
    CHECK_STR(sc.items[0].label, "EVENT 11"); CHECK(sc.items[0].vkind == AT_VAL_TEXT); CHECK_STR(sc.items[0].text, "01:00 25");
    CHECK_STR(sc.items[0].tag, "CLEARED"); CHECK_STR(sc.items[1].tag, ""); CHECK_STR(sc.items[2].sub, "sub");
    CHECK_STR(sc.counter, "12 / 51");
    v.n = AT_MAX_ITEMS + 1; CHECK(at_data_screen(&v, &sc) == 0);   /* over the record: refused, never truncated silently */
    ATLAS_DONE("atlas data");
}
```

Register `atlas-data)` with `sources=(pc/tests/atlas_data_test.c pc/platform/gw_ui_data.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c)`.

- [ ] **Step 2: Run to see it fail.**
- [ ] **Step 3: Implement.** `gw_ui_data.h`:

```c
/* gw_ui_data.h - a long data list as an Atlas list screen: a window over the rows, formatters, rows to items. Pure C. */
#ifndef GW_UI_DATA_H
#define GW_UI_DATA_H
#include "gw_ui_screen.h"
#ifdef __cplusplus
extern "C" {
#endif
#define AT_DATA_ROWS AT_MAX_ITEMS   /* RECONCILE: step 5 raises AT_MAX_ITEMS to 64; this follows it */
enum { AT_DR_DONE = 1, AT_DR_LOCKED = 2, AT_DR_NEW = 4 };
typedef struct { char label[AT_STR], value[AT_STR], sub[AT_STR]; unsigned flags; } AtDataRow;
typedef struct {
    char id[AT_ID * 2], title[AT_STR];
    int total, first, n, focus;            /* total rows; the window's first row; rows below; the focused row (absolute) */
    AtDataRow row[AT_DATA_ROWS];
} AtDataView;

int  at_data_first(int total, int per, int focus, int first);
void at_data_counter(char *out, int cap, int focus, int total);          /* "3 / 51"; empty for an empty list */
void at_fmt_count(char *out, int cap, unsigned v);                        /* 1,234,567 */
void at_fmt_hm(char *out, int cap, unsigned seconds);                     /* H:MM, hours not capped at 24 */
void at_fmt_frames(char *out, int cap, unsigned frames);                  /* MM:SS CC from 60 fps frames (the retail Event record rule) */
int  at_data_screen(const AtDataView *v, AtScreen *sc);                   /* 1 filled; 0 when the window does not fit the record */
#ifdef __cplusplus
}
#endif
#endif
```

`gw_ui_data.c`:

```c
#include "gw_ui_data.h"
#include <stdio.h>
#include <string.h>

int at_data_first(int total, int per, int focus, int first)
{
    int max_first = total > per ? total - per : 0;
    if (focus < 0) focus = 0;
    if (focus >= total) focus = total > 0 ? total - 1 : 0;
    if (focus < first) first = focus;
    else if (focus >= first + per) first = focus - per + 1;
    if (first > max_first) first = max_first;
    if (first < 0) first = 0;
    return first;
}

void at_data_counter(char *out, int cap, int focus, int total)
{
    if (total <= 0) { snprintf(out, (size_t) cap, "%s", ""); return; }
    snprintf(out, (size_t) cap, "%d / %d", focus + 1, total);
}

void at_fmt_count(char *out, int cap, unsigned v)
{
    char d[16]; int n = snprintf(d, sizeof d, "%u", v), i, o = 0;
    for (i = 0; i < n && o + 2 < cap; i++) {
        if (i > 0 && (n - i) % 3 == 0) out[o++] = ',';
        out[o++] = d[i];
    }
    out[o] = '\0';
}

void at_fmt_hm(char *out, int cap, unsigned seconds) { snprintf(out, (size_t) cap, "%u:%02u", seconds / 3600u, seconds / 60u % 60u); }

void at_fmt_frames(char *out, int cap, unsigned t)
{
    snprintf(out, (size_t) cap, "%02u:%02u %02u", t / 3600u % 60u, t / 60u % 60u, (unsigned) (99.0 * (double) (t % 60u) / 59.0));
}

int at_data_screen(const AtDataView *v, AtScreen *sc)
{
    int i;
    if (v->n < 0 || v->n > AT_MAX_ITEMS) return 0;
    memset(sc, 0, sizeof *sc);
    snprintf(sc->id, sizeof sc->id, "%s", v->id);
    snprintf(sc->title, sizeof sc->title, "%s", v->title);
    sc->primary = AT_PRIMARY_LIST;
    sc->n_items = v->n;
    for (i = 0; i < v->n; i++) {
        AtItem *it = &sc->items[i];
        snprintf(it->id, sizeof it->id, "r%d", v->first + i);
        snprintf(it->label, sizeof it->label, "%s", v->row[i].label);
        snprintf(it->sub, sizeof it->sub, "%s", v->row[i].sub);
        it->vkind = AT_VAL_TEXT;
        snprintf(it->text, sizeof it->text, "%s", v->row[i].value);
        snprintf(it->tag, sizeof it->tag, "%s", (v->row[i].flags & AT_DR_DONE) ? "CLEARED" : (v->row[i].flags & AT_DR_LOCKED) ? "LOCKED" : (v->row[i].flags & AT_DR_NEW) ? "NEW" : "");
    }
    at_data_counter(sc->counter, (int) sizeof sc->counter, v->focus, v->total);
    return 1;
}
```

(`at_fmt_frames`: 3615 -> `3615/3600%60 = 1`, `3615/60%60 = 60%60 = 0`, `99*15/59 = 25.17 -> 25`: `"01:00 25"`. `at_data_first(.., -1, 20)` clamps focus to 0 so the result is 0; the test accepts either value.)
- [ ] **Step 4: Run to pass.** `nt atlas-data | tail -1`: `atlas data: 52 checks, 0 failed` (count approximate).
- [ ] **Step 5: Commit.** Game repo: `gw_ui_data.h/.c`, test. Workspace repo: `native_test.sh`. `atlas: the data model (a window over a long list, formatters, rows to a list screen)`.

---

### Task 3: The adapter, the entry hook and the guards

**Files:**
- Create (game repo): `src/melee/gm/gmfrontend_atlas_data.inc` (extends the Task 1 helper)
- Modify (game repo): `pc/platform/gw_script_ui.inc` (the row shims), `src/melee/gm/gmfrontend.c` (include), `src/melee/gm/gmfrontend_menus.inc` (`fm_confirm` hook), `src/melee/gm/gmfrontend_atlas.inc` (`fa_frame`, `fa_sync`)
- Create (workspace repo): `tools/port/test_fe_atlas_data.py`

**Interfaces:**
Consumes step 2's shims and `fm`, `fe`, `fm_back`. Produces the shims `Ui_Row(label, value, sub, flags)` (appends one item to the pending screen), `Ui_Counter(text)` (the right-hand footer text, built by the adapter), the adapter, and the table `fad_screens[]`.

**Gate:** `atlas_gate.py --step 8` exits 0 (step 2). N3 is soft: if step 5's item shims exist, `Ui_Row` is a wrapper over them (the one `RECONCILE` wrapper); if not, it appends to the step 1 list record directly.

- [ ] **Step 1: Write the static guards first** `tools/port/test_fe_atlas_data.py` (they fail until the adapter exists, which is the point):

```python
"""Static guards on the Atlas data adapter. python -m unittest tools/port/test_fe_atlas_data.py"""
import os, re, unittest

ROOT = os.environ.get("GW_MELEE", "")
def read(rel): return open(os.path.join(ROOT, rel), encoding="utf-8").read()

class Adapter(unittest.TestCase):
    def setUp(self): self.t = read("src/melee/gm/gmfrontend_atlas_data.inc")

    def test_no_move_forwarded_for_data_screens(self):
        body = self.t[self.t.index("static bool fad_frame"):]
        body = body[:body.index("\n}\n")]
        self.assertNotRegex(body, r"Ui_Intent\(\s*FA_EV_MOVE", "the adapter owns the cursor: a MOVE intent would wrap inside the window")

    def test_back_returns_to_the_parent_item(self):
        # every screen names the (MenuKind, SEL) its native entry used, and it matches mn_PcOpenNative
        mn = read("src/melee/mn/mnmain.c")
        native = mn[mn.index("static void mn_PcOpenNative"):mn.index("not a native screen")]
        for kind, sel in re.findall(r"\{\s*FD_\w+\s*,\s*\"[\w.]+\"\s*,\s*\"[^\"]*\"\s*,\s*(MENU_KIND_\w+)\s*,\s*(SEL_\w+)", self.t):
            self.assertIn(sel, native, "%s %s is not a native entry point" % (kind, sel))

    def test_screens_are_read_only_unless_listed(self):
        writers = re.findall(r"\b(gmMainLib_\w*(?:Set|Write|Save)\w*|lbCardGame_SaveChanges|DeleteName|CreateNameAtIndex|WriteCharactersForNameAtIndex|gm_801BEB74)\s*\(", self.t)
        allowed = {"gm_801BEB74", "DeleteName", "CreateNameAtIndex", "WriteCharactersForNameAtIndex"}
        self.assertTrue(set(writers) <= allowed, "unexpected writers: %s" % sorted(set(writers) - allowed))

    def test_native_row_untouched(self):
        m = read("src/melee/gm/gmfrontend_menus.inc")
        self.assertIn("fad_open_for(", m)       # the hook sits in fm_confirm
        self.assertEqual(len(re.findall(r"FA_ATLAS", m)), 0, "no table row changes: FA_NATIVE stays")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Write the adapter skeleton.** `gmfrontend_atlas_data.inc` (after the Task 1 helper):

```c
/* gmfrontend_atlas_data.inc - the Atlas data screens (spec 13.8): Event Match, Name Entry, Sound Test, Special Messages, Records.
 * Each is opened from the FA_NATIVE row that opens its retail screen today: fm_confirm asks fad_open_for(kind, sel) first and, when a
 * data screen takes it, the frontend scene stays loaded (no scene change), the menu keeps its cursor, and B returns to it. So the position
 * protocol (MenuKind, selection), the SEL_* numbers and gmFrontend_NativeReturn are untouched. MELEE_ATLAS=0 or a screen left out of
 * MELEE_ATLAS_DATA leaves the retail screen exactly as it is. THE ADAPTER OWNS THE CURSOR AND THE WINDOW of a data screen (the host's
 * wrap would wrap inside the window): it forwards no MOVE intent and tells the host the focus with Ui_Commit. */

extern int Ui_Row(const char* label, const char* value, const char* sub, int flags);
extern void Ui_Counter(const char* text);
extern int Ui_DataRows(void);
extern const char* Ui_EnvData(void);
extern int Ui_NetplayActive(void);
extern int Ui_DataFirst(int total, int per, int focus, int first);
enum { FD_NONE, FD_EVENTS, FD_NAME, FD_SOUND, FD_MESSAGES, FD_BONUS, FD_MISC, FD_VSREC, FD_COUNT };
enum { FAD_PAGE = 9 }; /* rows the pane shows: the host's at_list_visible decides; 9 is the 640x480 figure used until Ui_Window reports it */

typedef struct {
    int id;
    const char* atlas_id;
    const char* title;
    u8 kind, sel;                /* the (MenuKind, SEL_*) the retail entry is, and where B returns */
    int (*total)(void);
    void (*row)(int i, int focused);  /* calls Ui_Row once for row i; focused: also fills the explainer through Ui_Explain */
    bool (*accept)(int i);       /* A on row i; true when it left the scene */
    const char* enable_name;     /* the word in MELEE_ATLAS_DATA */
} FadScreen;

static struct {
    int id, focus, first, total;
    bool env_read;
    u32 enabled; /* bit per FD_* from MELEE_ATLAS_DATA */
} fad;

static const FadScreen* fad_find(int id);   /* defined after the per-screen sources below */
static const FadScreen* fad_for(u8 kind, u8 sel);

static void fad_read_env(void)
{
    const char* e;
    int i;
    if (fad.env_read) {
        return;
    }
    fad.env_read = true;
    e = Ui_EnvData(); /* the string of MELEE_ATLAS_DATA, "" when unset */
    for (i = 1; i < FD_COUNT; i++) {
        const FadScreen* s = fad_find(i);
        if (s != NULL && (e[0] == '\0' || strstr(e, "all") != NULL || strstr(e, s->enable_name) != NULL) && strstr(e, "none") == NULL) {
            fad.enabled |= 1u << i;
        }
    }
}

/* fm_confirm calls this before it runs an FA_NATIVE row: true when a data screen took the row */
static bool fad_open_for(u8 kind, u8 sel)
{
    const FadScreen* s;
    if (!Ui_Ready() || Ui_NetplayActive()) {
        return false;
    }
    fad_read_env();
    s = fad_for(kind, sel);
    if (s == NULL || !(fad.enabled & (1u << s->id))) {
        return false;
    }
    fad.id = s->id;
    fad.focus = 0;
    fad.first = 0;
    fad.total = s->total();
    OSReport("frontend: Atlas data screen %s\n", s->atlas_id); /* OK-NOTEXT */
    return true;
}

static void fad_close(void)
{
    const FadScreen* s = fad_find(fad.id);
    if (s != NULL) {
        Ui_Close(s->atlas_id);
    }
    fad.id = FD_NONE;
}

/* every frame the screen is up: input first (the host's events and the game's menu pad), then the view */
static bool fad_frame(u32 pad)
{
    const FadScreen* s = fad_find(fad.id);
    int type, block, index;
    if (s == NULL) {
        return false;
    }
    fad.total = s->total();
    if (fad.total > 0) {
        if (pad & MenuInput_Up) {
            fad.focus = fad.focus > 0 ? fad.focus - 1 : fad.total - 1; /* up and down wrap over the whole list, not the window */
        }
        if (pad & MenuInput_Down) {
            fad.focus = fad.focus < fad.total - 1 ? fad.focus + 1 : 0;
        }
    }
    if (pad & MenuInput_Confirm) {
        Ui_Intent(FA_EV_ACCEPT, 0);
    }
    if (pad & MenuInput_Back) {
        Ui_Intent(FA_EV_BACK, 0);
    }
    while (Ui_PollEvent(&type, &block, &index)) {
        if (type == FA_EV_FOCUS && index >= 0) {
            fad.focus = fad.first + index; /* a hover or a click: the window-relative index plus the window start */
        } else if (type == FA_EV_ACCEPT) {
            if (fad.total > 0 && s->accept != NULL && s->accept(fad.focus)) {
                fad_close();
                return true;
            }
        } else if (type == FA_EV_BACK) {
            sfxBack();
            fad_close();
            return true;
        }
    }
    if (fad.focus >= fad.total) {
        fad.focus = fad.total > 0 ? fad.total - 1 : 0;
    }
    fad.first = Ui_DataFirst(fad.total, FAD_PAGE, fad.focus, fad.first); /* host at_data_first */
    return true;
}

static void fad_submit(void)
{
    const FadScreen* s = fad_find(fad.id);
    char ctr[24];
    int i;
    if (s == NULL || !Ui_Begin(s->atlas_id, FA_PRIMARY_LIST, 0, s->title)) {
        return;
    }
    if (fad.total > 0) {
        snprintf(ctr, sizeof ctr, "%d / %d", fad.focus + 1, fad.total);
        Ui_Counter(ctr);
    }
    for (i = fad.first; i < fad.total && i < fad.first + Ui_DataRows(); i++) {
        s->row(i, i == fad.focus);
    }
    Ui_Key('A', "Select");
    Ui_Key('B', "Back");
    Ui_Commit(0, fad.focus - fad.first);
}
```

(`Ui_DataRows()` returns `AT_DATA_ROWS`; `Ui_EnvData`, `Ui_NetplayActive` and `Ui_DataFirst` are one-line host shims, written in the next step. `FA_PRIMARY_LIST = 1` is `AT_PRIMARY_LIST`, next to step 2's `FA_PRIMARY_TILES`; `FA_EV_*` are step 2's.)
- [ ] **Step 3: The host shims.** In `gw_script_ui.inc` (RECONCILE: if step 5 merged, make `gw_Ui_Row` call its item shim):

```c
/* the data screens' rows: appended to the screen gw_Ui_Begin opened (an engine slot, one at a time) */
int gw_Ui_Row(const char *label, const char *value, const char *sub, int flags) {
    GsUiSlot *u = gs_ui_pending_engine();                 /* the slot gw_Ui_Begin filled; NULL when none is open */
    AtItem *it;
    if (u == NULL || u->sc.n_items >= AT_MAX_ITEMS) return 0;
    it = &u->sc.items[u->sc.n_items++];
    memset(it, 0, sizeof *it);
    snprintf(it->id, sizeof it->id, "r%d", u->sc.n_items - 1);
    snprintf(it->label, sizeof it->label, "%s", label ? label : "");
    snprintf(it->sub, sizeof it->sub, "%s", sub ? sub : "");
    it->vkind = AT_VAL_TEXT;
    snprintf(it->text, sizeof it->text, "%s", value ? value : "");
    snprintf(it->tag, sizeof it->tag, "%s", (flags & AT_DR_DONE) ? "CLEARED" : (flags & AT_DR_LOCKED) ? "LOCKED" : (flags & AT_DR_NEW) ? "NEW" : "");
    return 1;
}
void gw_Ui_Counter(const char *text) { GsUiSlot *u = gs_ui_pending_engine(); if (u) snprintf(u->sc.counter, sizeof u->sc.counter, "%s", text ? text : ""); }
int gw_Ui_DataRows(void) { return AT_DATA_ROWS; }
const char *gw_Ui_EnvData(void) { const char *e = getenv("MELEE_ATLAS_DATA"); return e ? e : ""; }
int gw_Ui_NetplayActive(void) { return gs_ui_online(); }          /* the same test step 3 uses for the retail mask */
int gw_Ui_DataFirst(int total, int per, int focus, int first) { return at_data_first(total, per, focus, first); }
```

`gs_ui_pending_engine` is the accessor step 2's `gw_Ui_Tile` uses to reach the slot (name RECONCILE: read `gw_Ui_Tile` at `gw_script_ui.inc:770` and use whatever it uses). The counter is built on the game side because the adapter owns `focus`; `at_data_counter` stays the tested host formatter for any caller that has both numbers.
- [ ] **Step 4: The entry hook and the frame branches.**
  1. `gmfrontend.c`: `#include "gmfrontend_atlas_data.inc"` right after the include of `gmfrontend_atlas.inc` (the `.inc` uses `fm`, `fa_*` and the shims declared there).
  2. `gmfrontend_menus.inc` `fm_confirm`, immediately before `switch (it->act)` (after the Sound Test stop calls, which the retail screen's first two calls need only when the retail screen opens: move the existing `if (it->act == FA_NATIVE && m->kind == MENU_KIND_DATA && it->sel == SEL_DATA_SOUND)` block **below** the new hook so the audio is not stopped twice; the Atlas Sound Test stops them itself in Task 7):

```c
#if defined(TARGET_PC)
    if (it->act == FA_NATIVE && fad_open_for(m->kind, it->sel)) {
        return;
    }
#endif
```

  3. `gmfrontend_atlas.inc` `fa_frame`: first lines: `if (fad.id != FD_NONE) { fat.handled = true; return fad_frame(pad); }`; `fa_sync`: `if (fad.id != FD_NONE) { fad_submit(); return; }` placed after the `fa_on` test and before the menu's own `fa_submit`; and when `fad.id != FD_NONE` the menu's `Ui_Close(fat.shown)` must run once (the data screen replaces the menu's host screen): `if (fad.id != FD_NONE && fat.shown != NULL) { Ui_Close(fat.shown); fat.shown = NULL; }`. On `fad_close` the next `fa_sync` re-submits the menu and the legacy cursor is where it was.
  4. The `SOLO > EVENT MATCH` row is `FA_NATIVE` with `(MENU_KIND_1P, SEL_1P_EVENT)`: its retail screen is opened by `mn_PcOpenNative` with `MENU_KIND_1P`, so the table in Step 5's `fad_for` lists the Event screen under `(MENU_KIND_1P, SEL_1P_EVENT)`.
- [ ] **Step 5: The screens table skeleton** at the end of `gmfrontend_atlas_data.inc` (the rows are filled by Tasks 4 to 9; commit with only Misc once Task 4 lands):

```c
static const FadScreen fad_screens[] = {
    /* id         atlas id          title                kind              sel                 total  row  accept  env word  */
    { FD_MISC,    "data.misc",      "MISC. RECORDS",     MENU_KIND_RECORDS, SEL_RECORDS_MISC,   fad_misc_total, fad_misc_row, NULL, "misc" },
};
static const FadScreen* fad_find(int id) { int i; for (i = 0; i < (int) (sizeof fad_screens / sizeof fad_screens[0]); i++) if (fad_screens[i].id == id) return &fad_screens[i]; return NULL; }
static const FadScreen* fad_for(u8 kind, u8 sel) { int i; for (i = 0; i < (int) (sizeof fad_screens / sizeof fad_screens[0]); i++) if (fad_screens[i].kind == kind && fad_screens[i].sel == sel) return &fad_screens[i]; return NULL; }
```

The guard `test_back_returns_to_the_parent_item` parses these rows (`FD_*`, quoted ids, the `(MENU_KIND_*, SEL_*)` pair) against `mn_PcOpenNative`.
- [ ] **Step 6: Run the guards and the syntax check.** `python -m unittest tools/port/test_fe_atlas_data.py` (needs the adapter's `fad_frame` and the Misc row from Task 4: run again then); PowerPC syntax check of `gmfrontend.c` with the new include: `clang --target=powerpc-unknown-eabi -fsyntax-only -DTARGET_PC ...` using the flags `tools/port/build.sh` prints for a game TU (the form step 6 Task 8 used; the extern declarations above are the only host symbols the file needs).
- [ ] **Step 7: Commit.** Game repo: the `.inc`, the shims, the three small edits: `atlas: the data adapter (owns the cursor and the window, opens from the FA_NATIVE rows, B returns to the menu item)`. Workspace repo: the guard test.

---

### Task 4: Misc Records (the first screen: no retail text needed)

`mnCount_GetRowValue_Number(int row)` and `mnCount_GetRowValue_Character(row)` are public and the 30 rows are the `mnCount_row` enum (`mncount.h:28-59`); the five time rows are `POWER_TIME`, `PLAY_TIME`, `SINGLEPLAYER_TIME`, `VS_PLAY_TIME`, `COMBINED_VS_PLAY_TIME` in seconds, shown `H:MM` (`mncount.c:550-556`), and the ten fighter rows (`LONGEST_TIME` to `DISASTER_MASTER`) show a fighter name or an empty mark (`SELKIND_COUNT`). The labels are the retail SIS ids `0xC9..0xE6` (`mnCount_sis_idx`); **this screen uses its own authored labels** and so does not depend on Task 1.

**Files:**
- Create/modify (game repo): `pc/platform/gw_ui_data_models.h/.c`, `pc/tests/atlas_models_test.c`; the Misc source in `gmfrontend_atlas_data.inc`
- Modify (workspace repo): `native_test.sh` (case `atlas-models`)

**Interfaces:** `AtMiscRow at_misc_row(int row)` (label and kind), `void at_misc_fill(int row, unsigned value, const char *fighter, AtDataRow *out)`.

- [ ] **Step 1: Write the failing test** `pc/tests/atlas_models_test.c` (this file grows in Tasks 5, 6 and 8):

```c
#include "atlas_check.h"
#include "../platform/gw_ui_data_models.h"

int main(void)
{
    AtDataRow r; int i;
    CHECK(AT_MISC_ROWS == 30);
    /* every row has an authored label under the row width and a kind; the five time rows and ten fighter rows are where mncount.h puts them */
    for (i = 0; i < AT_MISC_ROWS; i++) { CHECK(at_misc_row(i).label[0] != 0); CHECK(strlen(at_misc_row(i).label) <= 28); }
    CHECK(at_misc_row(1).kind == AT_MK_TIME && at_misc_row(2).kind == AT_MK_TIME && at_misc_row(3).kind == AT_MK_TIME && at_misc_row(4).kind == AT_MK_TIME && at_misc_row(5).kind == AT_MK_TIME);
    CHECK(at_misc_row(0).kind == AT_MK_COUNT && at_misc_row(6).kind == AT_MK_COUNT);
    for (i = 20; i < 30; i++) CHECK(at_misc_row(i).kind == AT_MK_FIGHTER);

    at_misc_fill(14, 1234567u, "", &r);  CHECK_STR(r.value, "1,234,567");            /* KO total */
    at_misc_fill(2, 3900u, "", &r);      CHECK_STR(r.value, "1:05");                  /* play time */
    at_misc_fill(2, 359999999u, "", &r); CHECK_STR(r.value, "99999:59");              /* the retail clamp (3599999940 s) is the getter's, not ours */
    at_misc_fill(20, 0, "Fox", &r);      CHECK_STR(r.value, "Fox");
    at_misc_fill(20, 0, "", &r);         CHECK_STR(r.value, "--");                    /* nobody yet: SELKIND_COUNT */
    ATLAS_DONE("atlas models");
}
```

- [ ] **Step 2: Implement** `gw_ui_data_models.h`:

```c
/* gw_ui_data_models.h - the per-screen scalar models of the data screens. Pure C; every input is a number or a string, never a callback. */
#ifndef GW_UI_DATA_MODELS_H
#define GW_UI_DATA_MODELS_H
#include "gw_ui_data.h"
#ifdef __cplusplus
extern "C" {
#endif
#define AT_MISC_ROWS 30   /* mnCount_row, mncount.h:28-59: POWER_COUNT .. DISASTER_MASTER */
enum { AT_MK_COUNT, AT_MK_TIME, AT_MK_FIGHTER };
typedef struct { char label[32]; int kind; } AtMiscRow;
AtMiscRow at_misc_row(int row);
void at_misc_fill(int row, unsigned value, const char *fighter, AtDataRow *out);   /* fighter: "" when the getter says nobody */
#ifdef __cplusplus
}
#endif
#endif
```

`gw_ui_data_models.c` (Misc part): the label table is **ours**, in the enum's order:

```c
#include "gw_ui_data_models.h"
#include <stdio.h>
#include <string.h>

static const char *const MISC_LABEL[AT_MISC_ROWS] = {
    "Times switched on", "Time switched on", "Time played", "Single-player time", "VS time", "Combined VS time",
    "VS matches", "Time matches", "Stock matches", "Coin matches", "Bonus matches", "VS contestants",
    "Match resets", "Damage dealt", "KOs", "Self-destructs", "Fighters available", "Stages available",
    "Trophies", "Name tags",
    "Longest fighter time", "Second longest fighter time", "Shortest fighter time", "Most KOs per fall", "Fewest KOs per fall",
    "Most hits taken", "Fewest hits taken", "KO leader", "Fall leader", "Self-destruct leader"
};
AtMiscRow at_misc_row(int row)
{
    AtMiscRow r; memset(&r, 0, sizeof r);
    if (row < 0 || row >= AT_MISC_ROWS) return r;
    snprintf(r.label, sizeof r.label, "%s", MISC_LABEL[row]);
    r.kind = (row >= 1 && row <= 5) ? AT_MK_TIME : (row >= 20) ? AT_MK_FIGHTER : AT_MK_COUNT;
    return r;
}
void at_misc_fill(int row, unsigned value, const char *fighter, AtDataRow *out)
{
    AtMiscRow m = at_misc_row(row);
    memset(out, 0, sizeof *out);
    snprintf(out->label, AT_STR, "%s", m.label);
    if (m.kind == AT_MK_TIME) at_fmt_hm(out->value, AT_STR, value);
    else if (m.kind == AT_MK_FIGHTER) snprintf(out->value, AT_STR, "%s", (fighter && fighter[0]) ? fighter : "--");
    else at_fmt_count(out->value, AT_STR, value);
}
```

The labels for rows 22 to 29 describe the retail getters as read (`mnCount_GetSmashChamp` etc.: what exactly "Smash Champ" ranks is **(unverified)**; Task 4 step 5 reads `mncount.c:203-224` and rewrites the five labels that are guesses: "Most KOs per fall" to "Fewest hits taken" are placeholders and the task must not ship them as they stand). Register `atlas-models)` with `sources=(pc/tests/atlas_models_test.c pc/platform/gw_ui_data_models.c pc/platform/gw_ui_data.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c)`.
- [ ] **Step 3: Run to pass** (`nt atlas-models`).
- [ ] **Step 4: The game-side source.** Extend the adapter (before `fad_screens`):

```c
extern void Ui_RowMisc(int row, unsigned value, const char* fighter);   /* the host formats it: at_misc_fill, then gw_Ui_Row */

static int fad_misc_total(void)
{
    return 30; /* mnCount_row */
}

static void fad_misc_row(int i, int focused)
{
    char name[24];
    unsigned v = 0;
    name[0] = '\0';
    if (i >= LONGEST_TIME) {
        SelectableCharacterKind k = mnCount_GetRowValue_Character((mnCount_row) i);
        if (k != SELKIND_COUNT) {
            Frontend_FighterName(gm_SelKindToCKind(k), name, sizeof name); /* the port's own fighter-name lookup (RECONCILE: the name the lobby uses, gmfrontend_online.inc) */
        }
    } else {
        v = mnCount_GetRowValue_Number(i);
    }
    Ui_RowMisc(i, v, name);
    if (focused) {
        Ui_Explain("MISC. RECORDS", Ui_MiscLabel(i), "Counted from your save, as the retail screen does.");
    }
}
```

`Ui_RowMisc` and `Ui_MiscLabel` are two more host shims (`gw_Ui_RowMisc` fills `AtDataRow` through `at_misc_fill` and calls `gw_Ui_Row`; `gw_Ui_MiscLabel(i)` returns `at_misc_row(i).label`). The `mnCount_*` getters are the retail ones, called as `mncount.c` calls them; include `<melee/mn/mncount.h>` in the `.inc`'s includes in `gmfrontend.c`.
- [ ] **Step 5: Read the five guessed labels' getters** (`mncount.c:203-224`, `mnCount_8025092C`) and replace the labels of rows 23 to 29 with what each ranks, in plain words. Re-run `nt atlas-models`.
- [ ] **Step 6: Commit.** `atlas: Misc records (the 30 retail getters, our own labels, no retail text)`.

---

### Task 5: Event Match

**Files:**
- Modify (game repo): `pc/platform/gw_ui_data_models.h/.c` (event row), `pc/tests/atlas_models_test.c`, the events source in `gmfrontend_atlas_data.inc`, a `fad_screens[]` row.
- Read first: `mn/mnevent.c` 42-102, 185-334, 405-470, 627-733; `gmevent.c` 2321-2418.

**Interfaces:** `void at_event_row(int slot, int cleared, int timed, unsigned best, const char *name, AtDataRow *out)`.

Facts read: 51 events (`0x33`), keyed by **slot** (`gm_801BEB74(slot)` stores the selection in the save, `gm_801BEB80()` reads it back, `gm_801BEBA8(slot)` maps a slot to the name's SIS number `((n * 2) & 0x1FE) + 0x154`), a cleared flag `gmMainLib_8015CEFC(slot)`, a best record `gmMainLib_8015CF5C(gm_801BEBC0(slot))`, and a "timed" flag `gm_801BEB8C(...)` (`evinit->x1_0`): timed events show `MM:SS CC` (`mnEvent_8024D5B0`), the others a plain count. Starting an event is `gm_801BEB74(slot); gm_801677E8(port); mn_80229860(GM_EVENT)` (`mnEvent_8024D864`), which the frontend does as `fm.pend_kind = 2; fm.pend_a = GM_EVENT`.

- [ ] **Step 1: Read, then write down three things** in the task's commit message (they are **(unverified)** until read): (a) what `gmMainLib_8015CEFC` gates (the icon only, per `mnEvent_8024D15C`); (b) where the description text comes from (`mnEvent_ShowSelected` and the `desc_text` object are not in the plan's reading: the SIS number or the `evbonus` data); (c) which slot the first entry focuses (`mnEvent_8024E838(0, true)`, and `mnEvent_8024CE74()`'s progress start). If (b) is not a SIS string the explainer's WHAT shows the authored line "Event N" and the record only.
- [ ] **Step 2: Add the failing checks** to `atlas_models_test.c`:

```c
    /* events: authored fallback label, the record by kind, the cleared mark, names clipped to the row */
    at_event_row(6, 1, 1, 3615u, "", &r);       CHECK_STR(r.label, "EVENT 7");  CHECK_STR(r.value, "01:00 25"); CHECK(r.flags & AT_DR_DONE);
    at_event_row(6, 0, 1, 0u, "", &r);          CHECK_STR(r.value, "--:-- --"); CHECK(!(r.flags & AT_DR_DONE));    /* timed, never cleared: retail shows fullwidth dashes in the MM:SS CC shape */
    at_event_row(0, 1, 0, 12u, "", &r);         CHECK_STR(r.value, "12");                                          /* a count event */
    at_event_row(0, 0, 0, 0u, "", &r);          CHECK_STR(r.value, "--");
    at_event_row(2, 0, 1, 0u, "Invented Name", &r); CHECK_STR(r.label, "Invented Name"); CHECK_STR(r.sub, "EVENT 3");
    at_event_row(2, 0, 1, 0u, "A very very very very long event name that cannot fit a row at all", &r); CHECK(strlen(r.label) <= AT_STR - 1);
    at_event_row(50, 0, 0, 0u, "", &r);         CHECK_STR(r.label, "EVENT 51");
```

- [ ] **Step 3: Implement** (`gw_ui_data_models.c`):

```c
void at_event_row(int slot, int cleared, int timed, unsigned best, const char *name, AtDataRow *out)
{
    memset(out, 0, sizeof *out);
    snprintf(out->sub, AT_STR, "EVENT %d", slot + 1);
    if (name && name[0]) snprintf(out->label, AT_STR, "%s", name); else snprintf(out->label, AT_STR, "EVENT %d", slot + 1);
    if (cleared) {
        out->flags |= AT_DR_DONE;
        if (timed) at_fmt_frames(out->value, AT_STR, best); else snprintf(out->value, AT_STR, "%u", best);
    } else {
        snprintf(out->value, AT_STR, "%s", timed ? "--:-- --" : "--");
    }
}
```

(When the name equals the fallback the sub line repeats it; the explainer shows the better one: the adapter passes `name == ""` when the decode gate is NO-GO.)
- [ ] **Step 4: The source.** In the adapter:

```c
extern void Ui_RowEvent(int slot, int cleared, int timed, unsigned best, const char* name);

static int fad_ev_total(void)
{
    return 0x33;
}

static void fad_ev_row(int i, int focused)
{
    char name[48];
    int timed = gm_801BEB8C((u8) gm_801BEBC0((u8) i)) & 0xFF; /* mnevent.c:5B0 does the same lookup */
    int cleared = gmMainLib_8015CEFC(i) != 0;
    unsigned best = gmMainLib_8015CF5C((s32) gm_801BEBC0((u8) i));
    name[0] = '\0';
    if (fad_text_ok) {
        fad_sis_text(((gm_801BEBA8((u8) i) * 2) & 0x1FE) + 0x154, name, sizeof name); /* the retail name's SIS number, mnevent.c:24D15C */
    }
    Ui_RowEvent(i, cleared, timed, best, name);
    if (focused) {
        Ui_Explain("EVENT MATCH", name[0] ? name : "EVENT", "Pick an event and press A to start it.");
    }
}

static bool fad_ev_accept(int i)
{
    gm_801BEB74((u8) i);                      /* the saved selection, as mnEvent_8024D864 writes it */
    gm_801677E8((s8) mn_802295AC());          /* the port that pressed A */
    sfxForward();
    fm.pend_kind = 2;                         /* FA_MODE path: leave the scene for the mode */
    fm.pend_a = GM_EVENT;
    fm.leave_at = fp.frame + 1;
    return true;
}
```

`fad_text_ok` is set once per open from the Task 1 gate (`GO` or `PARTIAL`); with NO-GO it is false and the row carries "EVENT N" only. Add the row `{ FD_EVENTS, "data.events", "EVENT MATCH", MENU_KIND_1P, SEL_1P_EVENT, fad_ev_total, fad_ev_row, fad_ev_accept, "events" }`, and on opening set `fad.focus` to the saved selection (`gm_801BEB80()`) when the player returns from an event, 0 on first entry (read in Step 1(c)): add `fad_events_start()` called from `fad_open_for` when `s->id == FD_EVENTS`.
- [ ] **Step 5: Edge checks** that need the game (Task 12): an unplayed save, a save with every event cleared, the 51st row, returning from an event lands on the same row.
- [ ] **Step 6: Commit.** `atlas: Event Match (51 events, cleared mark, the retail record rule, the retail start sequence)`.

---

### Task 6: Special Messages and Bonus Records (retail text screens)

These two need the Task 1 gate. Under **NO-GO** neither ships in Atlas (their `FA_NATIVE` rows keep running the retail screens, `fad_screens[]` has no row for them), and this task ends at Step 1.

**Files:** `pc/platform/gw_ui_data_models.h/.c` (message order), `pc/tests/atlas_models_test.c`, adapter sources and rows.

Read: `mn/mninfo.c` 54-150, 195-262, 272-300 and `mn/mninfobonus.c` whole. Facts: **66** special messages (`0x42`); unlocked per `mnInfo_80251A08(id)` (id `0x3E` never, `0x34` not in the US language, `0x35` not in the JP language, else `gmMainLib_8015D94C(id)`); sorted by the date `*gmMainLib_8015D804(id)` (descending: the newest first is **(unverified)**; `mnInfo_80251AFC` sorts the index array `mnInfo_804A0968[0x48]`, read it); the body text is the SIS string `un_802FE3F8(id, 0x4BD, &idx, NULL)` and the date is formatted with `date_format`/`time_format` from `MnInfoDataLayout`. Bonus records: `gm_8016F120(j)` unlocked per bonus (count **(unverified)**), the label is the SIS id from `0xA5`.

- [ ] **Step 1: Read the sort and the bonus loop** and state in the commit message: the sort order, the number of bonus entries, the date format fields. Under NO-GO stop here.
- [ ] **Step 2: Failing checks** (`atlas_models_test.c`): the visible message order from invented inputs (ids 3, 7, 9 unlocked with dates 30, 10, 20): `at_msg_order(unlocked[], date[], n, out[])` returns `[3, 9, 7]` for newest first, stable for equal dates, and skips locked ids; `at_msg_row` formats a date `"2026-10-06"` from seconds since the retail epoch only if Step 1 found the epoch; otherwise the row shows the message's number only ("MESSAGE 12", unverified date format is not guessed):

```c
    { int un[6] = { 0, 1, 0, 1, 1, 0 }; unsigned dt[6] = { 0, 30, 0, 10, 20, 0 }; int ord[6]; int n = at_msg_order(un, dt, 6, ord);
      CHECK(n == 3 && ord[0] == 1 && ord[1] == 4 && ord[2] == 3);
      un[2] = 1; dt[2] = 20; n = at_msg_order(un, dt, 6, ord); CHECK(n == 4 && ord[1] == 2 && ord[2] == 4); }   /* stable: equal dates keep the lower id first */
    { int un0[3] = { 0, 0, 0 }; unsigned d0[3] = { 0, 0, 0 }; int o0[3]; CHECK(at_msg_order(un0, d0, 3, o0) == 0); }
```

- [ ] **Step 3: Implement** `at_msg_order` (a stable insertion sort descending by date, skipping locked) in `gw_ui_data_models.c`; the game-side source builds the `unlocked[]`/`date[]` arrays once on open (66 calls), then `fad_msg_row(i)` shows `MESSAGE n` plus the date, and the explainer's WHAT is the decoded body (`fad_sis_text`, clamped to the 160-char explainer limit; the lint logs once per id when it clips). A message with `unknown > 0` glyphs shows `Message n` and "This message cannot be shown here yet." (an authored line): never a half message.
- [ ] **Step 4: Bonus records** the same way: rows from `gm_8016F120(j)` with the decoded label (or "BONUS n"), a `DONE` mark.
- [ ] **Step 5: Commit.** `atlas: Special Messages and Bonus Records (retail text through the decoder; the gate's outcome in the message)`.

---

### Task 7: Sound Test

Under a NO-GO text outcome the **names** are not shown but the screen can still ship as a numbered list (`SOUND 1 ... N`); say so to the owner at the look (it is the one screen that works without the disc's words).

**Files:** adapter source and row; a small model in `gw_ui_data_models.c` only if a list needs ordering.

Read first (`mn/mnsoundtest.c` 128-480, `mn/mnsound.c`): the track table (`data_2[text_ids[...]].text_id` SIS numbers, `data_3[idx]` the sound ids), how play, stop and next work (`lbAudioAx_80023694` stops effects, `lbAudioAx_800236DC` stops music, `lbAudioAx_80023968(id)` plays), the volume reads (`gm_801601C4(gmMainLib_8015ED74())`, `gm_80160244(...)`), and the retail screen's three groups if any **(unverified)**.

- [ ] **Step 1: Write down** the list structure (groups, counts, how a row maps to a sound id) and that the screen **writes no save value** (volumes are read, not set here: the retail test sets the live level from the saved setting, `mnSoundTest_8024A790`).
- [ ] **Step 2: The source.** A row per sound; A plays it (and A on the playing row stops it); B stops everything the retail screen stops on exit (`lbAudioAx_80023694(); lbAudioAx_800236DC();` and restores the menu music: `lbAudioAx_80023F28(gmMainLib_8015ECB0())` as `mnmain.c` does on entry) then closes. The first two stop calls the retail entry makes (`gmfrontend_menus.inc:1369`) move into this screen's open. The row `{ FD_SOUND, "data.sound", "SOUND TEST", MENU_KIND_DATA, SEL_DATA_SOUND, ... }`; because `fm_confirm` has `FMF_NOSFX` on this row, the screen plays no menu sound on open.
- [ ] **Step 3: Failing check** (`atlas_models_test.c`): a pure `at_sound_toggle(int playing, int row)` returns the action (`PLAY row`, `STOP`, or `PLAY other` when another row plays); six assertions over play, stop, switch.
- [ ] **Step 4: Commit.** `atlas: Sound Test (a list, A plays, B stops and restores the menu music)`.

---

### Task 8: VS Records

The largest of the Records screens (`mndiagram.c` 2,955 lines, `mndiagram2.c`, `mndiagram3.c`): two modes (by fighter, by name tag), many stat types, a ranked detail view. This task rebuilds the **ranking** (the data), not the retail's per-entry animated diagram.

**Files:** `pc/platform/gw_ui_data_models.c` (rank sort and stat formatting), `pc/tests/atlas_models_test.c`, adapter source and row.

Read first: `mndiagram2.h` (the stat type predicates `mnDiagram2_IsTimeStat/IsDistanceStat/IsPercentageStat/IsIconOnlyStat`, `mnDiagram2_GetStatValue(is_name_mode, stat_type, idx)`, `mnDiagram2_GetRankedFighter(stat, rank)`, `mnDiagram2_GetRankedName(stat, rank)`), `mndiagram.h` (`mnDiagram_FormatTime`, `mnDiagram_ConvertDistanceForDisplay`, `mnDiagram_IsDistanceOverflow`, `mnDiagram_GetFighterByIndex`, `mnDiagram_GetNameByIndex`, `mnDiagram_CountUnlockedFighters`). **(unverified):** the number of stat types and what each means (read `mndiagram2.c` `PopulateStatRows`), whether `mnDiagram2_GetRanked*` is already sorted or needs `mnDiagram_SortFightersByKOs`, and the units of a distance stat.

- [ ] **Step 1: Read and write down** the stat type list (index, kind, unit) as a table in the commit message; label each stat in our own words.
- [ ] **Step 2: Failing checks:**

```c
    /* ranking: a stable descending sort of (index, value) pairs, ties by the lower index, zero-value entries dropped */
    { unsigned val[6] = { 5, 0, 9, 5, 0, 7 }; int ord[6]; int n = at_rank(val, 6, ord);
      CHECK(n == 4 && ord[0] == 2 && ord[1] == 5 && ord[2] == 0 && ord[3] == 3); }
    { unsigned z[3] = { 0, 0, 0 }; int o[3]; CHECK(at_rank(z, 3, o) == 0); }
    /* a stat's text by kind: count, time (frames: MM:SS CC), percent, distance with the retail overflow mark */
    at_stat_text(AT_STAT_COUNT, 1500u, 0, &r);      CHECK_STR(r.value, "1,500");
    at_stat_text(AT_STAT_TIME, 3615u, 0, &r);       CHECK_STR(r.value, "01:00 25");
    at_stat_text(AT_STAT_PERCENT, 87u, 0, &r);      CHECK_STR(r.value, "87%");
    at_stat_text(AT_STAT_DISTANCE, 123456u, 1, &r); CHECK(strstr(r.value, "+") != NULL);          /* overflow: a plus mark instead of a wrong number */
```

- [ ] **Step 3: Implement** `at_rank` (stable, descending, drops zero values) and `at_stat_text` (the four kinds; the distance conversion and its overflow predicate are called **game-side** with the retail functions and the host receives the converted number and the overflow flag).
- [ ] **Step 4: The source.** Tabs FIGHTERS and TAGS when N5 is available (`Ui_Tab(name, active)` RECONCILE: step 5's tab shim), else one list and **L and R** change the stat (the adapter reads `MenuInput_*` for the shoulders as step 2's `fa_frame` does for the others, or the host's PAGE event); A on a row opens the entry's own detail (the explainer shows the entry's top three stats); tag names are SJIS in the save (`namedata[8]`): decode with `at_sjis_to_utf8` pair by pair, a non-Latin tag shows `TAG n`.
- [ ] **Step 5: Commit.** `atlas: VS Records (rankings by fighter and by tag, our stat labels, retail getters)`.

---

### Task 9: Name Entry

The riskiest screen of the step. `Versus > Name Entry` opens `mnName_8023AC40()` (the list: `GetNameCount`, `GetNameText(slot)`, `IsNameListFull`, `DeleteName`, `CreateNameAtIndex`, 120 tags, `mnname.c:157-351`) and then `mnNameNew` (the editor): **4 cells**, each a 2-byte SJIS glyph held in a 3-byte slot of `mnNameNew_CurrentNameText[0x10]`, a key map and glyph tables with variants (`mnNameNew_KeyMap`, `mnNameNew_GlyphTable`: kana rows with voiced and small variants, `mnnamenew.c:141-169`), written with `WriteCharactersForNameAtIndex(index, port)` (`CopyCurrentNameToNametag` copies up to 8 bytes into `NameTagData.namedata[8]`). Checks before confirm: `NameContainsOnlySpaces()`, `IsNameUnique`, `IsNameNotAllowed` **(unverified order; read `mnNameNew_MainInput` 949-1262 first)**. The same editor is also entered from the character select (`mnNameNew_EnterFromMnCharSel`): that entry is **step 4's** and is not touched here.

**Files:** create `pc/platform/gw_ui_name.h/.c`, `pc/tests/atlas_name_test.c`; adapter source and row; `native_test.sh` (case `atlas-name`).

**Interfaces:** `AtName` (4 cells, cursor, glyph page, message), `at_name_init`, `at_name_key(AtName*, event)`, `at_name_valid(const AtName*, taken[], n)`, `at_name_bytes(const AtName*, unsigned char out[9])`.

- [ ] **Step 1: Read, then record** in the commit message: the confirm validation order; the glyph set the **English** retail editor offers (the table is in source: `mnNameNew_GlyphTable.lower_glyphs/upper_glyphs`, and which of them are Latin); whether Latin letters are full-width SJIS (`0x82xx`) in the tag bytes; what B does on an empty cell. Name Entry is a go only if the English glyph set is Latin and small enough for a 4-column glyph grid; if the editor is kana-first in the English game, **drop the editor** and ship the list only (view, delete with a confirm dialog) with the editor left retail.
- [ ] **Step 2: Failing test** `pc/tests/atlas_name_test.c`:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_name.h"

int main(void)
{
    AtName n; unsigned char b[9]; int taken_none = 0;
    at_name_init(&n);
    CHECK(n.len == 0 && n.cursor == 0);
    CHECK(!at_name_valid(&n, NULL, 0));                         /* all spaces: refused (NameContainsOnlySpaces) */
    at_name_put(&n, 0x82, 0x60);                                /* A */
    at_name_put(&n, 0x82, 0x81);                                /* a */
    CHECK(n.len == 2 && n.cursor == 2);
    CHECK(at_name_valid(&n, NULL, 0));
    at_name_bytes(&n, b);
    CHECK(b[0] == 0x82 && b[1] == 0x60 && b[2] == 0x82 && b[3] == 0x81 && b[4] == 0);                /* NUL-terminated pairs, as namedata[8] holds them */
    at_name_put(&n, 0x82, 0x4F); at_name_put(&n, 0x82, 0x50);
    CHECK(n.len == 4);
    at_name_put(&n, 0x82, 0x51);                                /* a fifth glyph: refused, nothing changes */
    CHECK(n.len == 4 && n.cursor == 4);
    at_name_bytes(&n, b); CHECK(b[8] == 0);
    at_name_back(&n); CHECK(n.len == 3 && n.cursor == 3);
    at_name_back(&n); at_name_back(&n); at_name_back(&n); at_name_back(&n);
    CHECK(n.len == 0 && n.cursor == 0);                         /* back on empty: stays empty (the caller leaves the editor) */
    { unsigned char other[8] = { 0x82, 0x60, 0x82, 0x81, 0, 0, 0, 0 };
      at_name_put(&n, 0x82, 0x60); at_name_put(&n, 0x82, 0x81);
      CHECK(!at_name_valid(&n, (const unsigned char (*)[8]) other, 1)); }                             /* a name that exists: refused (IsNameUnique) */
    (void) taken_none;
    ATLAS_DONE("atlas name");
}
```

- [ ] **Step 3: Implement** `gw_ui_name.c` (pure; the glyph set, the forbidden list and the unique check are **inputs**, the host never contains retail tables):

```c
typedef struct { unsigned char hi[4], lo[4]; int len, cursor; } AtName;
void at_name_init(AtName *n) { memset(n, 0, sizeof *n); }
int  at_name_put(AtName *n, unsigned hi, unsigned lo) { if (n->len >= 4) return 0; n->hi[n->len] = (unsigned char) hi; n->lo[n->len] = (unsigned char) lo; n->len++; n->cursor = n->len; return 1; }
void at_name_back(AtName *n) { if (n->len > 0) { n->len--; n->cursor = n->len; } }
static int is_space(unsigned hi, unsigned lo) { return hi == 0x81 && lo == 0x40; }
int  at_name_valid(const AtName *n, const unsigned char (*taken)[8], int ntaken)
{
    int i, all_space = 1, t;
    for (i = 0; i < n->len; i++) if (!is_space(n->hi[i], n->lo[i])) all_space = 0;
    if (n->len == 0 || all_space) return 0;
    for (t = 0; t < ntaken; t++) {
        int same = 1;
        for (i = 0; i < 4; i++) { unsigned h = i < n->len ? n->hi[i] : 0, l = i < n->len ? n->lo[i] : 0; if (taken[t][i * 2] != h || taken[t][i * 2 + 1] != l) same = 0; }
        if (same) return 0;
    }
    return 1;
}
void at_name_bytes(const AtName *n, unsigned char out[9]) { int i; memset(out, 0, 9); for (i = 0; i < n->len; i++) { out[i * 2] = n->hi[i]; out[i * 2 + 1] = n->lo[i]; } }
```

(The test's `at_name_back` after four glyphs loops to empty; the `taken` array layout is the eight bytes of `namedata`.) The `IsNameNotAllowed` check stays **game-side** (it needs the retail list): the adapter calls it before `at_name_valid` and shows the authored line "That name is not allowed." The glyph set the grid shows comes from the game side through the shim `Ui_NameGlyph(row, col, hi, lo)` reading the retail table under the language rule found in Step 1.
- [ ] **Step 4: The adapter.** Two sub-screens inside `FD_NAME`: the **list** (rows `GetNameText(slot)` decoded with SJIS pairs, `NEW TAG` first when `!IsNameListFull()`, A edits or creates, **Y** deletes with a confirm dialog through `Ui_Dialog` RECONCILE (step 1's `gd.ui.dialog` part as a shim; if the dialog shim is not there the delete is refused with a note "Delete is in the retail screen for now" and the row stays; this is the one behaviour the plan allows to degrade) and the **editor** (the 4 cells and a glyph grid; A puts, B backs, START confirms when valid). Confirm writes with `CreateNameAtIndex` (a new tag) then `WriteCharactersForNameAtIndex(slot, port)` then `mnName_SortNames`-equivalent ordering exactly as the retail confirm path does (read it in Step 1; do not invent a different order). Only these three calls write (the guard allow-list names them).
- [ ] **Step 5: Commit.** `atlas: Name Entry (the tag list and a 4-cell editor over the retail validation and writes; the English glyph set found in the source)`. If Step 1 says drop the editor, the commit message says so and only the list ships.

---

### Task 10: Results (a `REPLACE` stand-in, off until the owner has looked)

**Files:**
- Create (game repo): `pc/platform/gw_ui_results.h/.c`, `pc/tests/atlas_results_test.c`
- Modify (game repo): `src/melee/gm/gmfrontend_atlas_data.inc` (the stand-in), `src/melee/gm/gmfrontend_atlas.inc` (`gmFrontend_AtlasStandIn`), `pc/platform/gw_script_ui.inc` (the `Ui_Res*` shims)
- Create (workspace repo): `tools/port/test_fe_atlas_results.py`; modify `native_test.sh` (case `atlas-results`)

**Interfaces:** `AtResults` (outcome, teams, up to 4 `AtResPlayer`), `at_results_build`, `at_results_confirm(AtResults*, port, kind)`, `at_results_done(const AtResults*)`, `at_results_screen`.

Facts read: the scene receives `ResultsMatchInfo` with a `MatchEnd` (`gmresult.c:1755`); `MatchEnd` has `outcome`, `match_kind`, `is_teams`, `winners[]`, `team_standings[]`, `player_standings[4]` with `pkind` (0 human, 1 CPU, 2 .., 3 none: `fn_801795D4` skips 3), `ckind`, `ftkind`, `stocks`, `self_destructs`, `percent`, `kills[4]`, `score`, `is_big_loser`, `team`; per-human confirm is START (`fn_80178050`: `HSD_PadCopyStatus[k].trigger & PAD_BUTTON_START`, or `err != 0`), when every human has confirmed the scene counts `x3` (0x14 frames when all four slots are non-human-less, else 0x0A) and calls `gm_801A4B60()`; a cancelled match (`gm_WasMatchCanceled(outcome)`) uses 2 pages and leaves on any human START at once (`fn_801791E4`). **(unverified):** what `kills[4]`, `percent` and `x9` mean per field (read the callers `fn_80174B4C` and `fn_80175240`), which side effects the retail scene performs that other code relies on, and what `fn_801701AC` clears.

- [ ] **Step 1: The side-effect table (read-only, before any code).** Walk `gm_Scene_Results_OnEnter` and its procs (`fn_80179350` and what it calls) and write a table in the task's commit message with every call classified **presentation** (the stand-in drops it), **audio** (the stand-in repeats it: the victory theme `lbAudioAx_80023F28(fn_80160400(ckind))`, the announcer `fn_80168E54`, the cancelled-match sounds `0x148`, `0xC350`) or **state** (the stand-in repeats it; candidates: `lb_80014574(slot, 3, 0x20, 0)` which looks like a rumble, `un_802FF1B4`, `gm_SetDbPauseFlag(0)`, `un_802FF128` the KO tally effect, `fn_801701AC` in the exit). **Any call classified state or unknown stops the task until understood.** `test_fe_atlas_results.py` reads this list from the stand-in's comments and checks that every name in it appears in the stand-in.
- [ ] **Step 2: Write the failing test** `pc/tests/atlas_results_test.c`:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_results.h"

int main(void)
{
    AtResults r; AtResInput in; int i;
    memset(&in, 0, sizeof in);
    in.outcome = 2; in.is_teams = 0;                                   /* elimination, free for all */
    for (i = 0; i < 4; i++) in.p[i].pkind = 3;                         /* none */
    in.p[0].pkind = 0; in.p[0].ckind = 1; in.p[0].stocks = 2; in.p[0].kos = 4; in.p[0].falls = 1; in.p[0].percent = 87; in.p[0].winner = 1;
    in.p[1].pkind = 1; in.p[1].ckind = 2; in.p[1].stocks = 0; in.p[1].kos = 1; in.p[1].falls = 4; in.p[1].percent = 130;
    at_results_build(&r, &in);
    CHECK(r.n == 2 && r.players[0].port == 0 && r.players[1].port == 1);          /* none-ports are skipped */
    CHECK(r.players[0].place == 1 && r.players[1].place == 2 && r.players[0].winner);
    CHECK(!r.canceled && r.humans == 1);
    CHECK(!at_results_done(&r));
    at_results_confirm(&r, 1, AT_RC_START);                                        /* a CPU port cannot confirm */
    CHECK(!at_results_done(&r));
    at_results_confirm(&r, 0, AT_RC_START);
    CHECK(at_results_done(&r) == 1 && r.exit_frames == 10);                        /* any human present: the 0x0A countdown (fn_80178050) */
    /* four players, all human: every one must confirm; the countdown is still 0x0A */
    memset(&in, 0, sizeof in); in.outcome = 2;
    for (i = 0; i < 4; i++) { in.p[i].pkind = 0; in.p[i].ckind = i; in.p[i].kos = i; }
    at_results_build(&r, &in);
    CHECK(r.humans == 4);
    at_results_confirm(&r, 0, AT_RC_START); at_results_confirm(&r, 1, AT_RC_START); at_results_confirm(&r, 2, AT_RC_START);
    CHECK(!at_results_done(&r));
    at_results_confirm(&r, 3, AT_RC_ERR);                                          /* a disconnected pad counts as confirmed, as retail does (err != 0) */
    CHECK(at_results_done(&r) == 1 && r.exit_frames == 10);
    /* no human at all (four CPUs): nobody has to confirm, the countdown is 0x14 */
    memset(&in, 0, sizeof in); in.outcome = 2;
    for (i = 0; i < 4; i++) in.p[i].pkind = 1;
    at_results_build(&r, &in);
    CHECK(r.humans == 0 && at_results_done(&r) == 1 && r.exit_frames == 20);
    /* a cancelled match: any human START leaves at once */
    memset(&in, 0, sizeof in); in.outcome = 4; in.canceled = 1; in.p[0].pkind = 0; in.p[1].pkind = 0; in.p[2].pkind = 3; in.p[3].pkind = 3;
    at_results_build(&r, &in);
    CHECK(r.canceled);
    at_results_confirm(&r, 1, AT_RC_START);
    CHECK(at_results_done(&r) == 1 && r.exit_frames == 0);
    /* teams: place by team; a tie shares the place */
    memset(&in, 0, sizeof in); in.outcome = 3; in.is_teams = 1;
    for (i = 0; i < 4; i++) { in.p[i].pkind = 0; in.p[i].team = i < 2 ? 0 : 1; in.p[i].winner = i < 2; }
    at_results_build(&r, &in);
    CHECK(r.players[0].place == 1 && r.players[1].place == 1 && r.players[2].place == 2);
    ATLAS_DONE("atlas results");
}
```

Register `atlas-results)` with `sources=(pc/tests/atlas_results_test.c pc/platform/gw_ui_results.c pc/platform/gw_ui_data.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c)`.
- [ ] **Step 3: Implement** `gw_ui_results.h/.c` (pure; inputs are plain numbers):

```c
typedef struct { int pkind, ckind, stocks, kos, falls, percent, team, winner; } AtResPlayerIn;
typedef struct { int outcome, is_teams, canceled; AtResPlayerIn p[4]; } AtResInput;
typedef struct { int port, pkind, ckind, stocks, kos, falls, percent, team, winner, place, confirmed; } AtResPlayer;
typedef struct { AtResPlayer players[4]; int n, humans, canceled, exit_frames, done; } AtResults;
enum { AT_RC_START = 1, AT_RC_ERR = 2 };
```

`at_results_build` skips `pkind == 3`, counts `humans` (`pkind == 0`), and orders `place`: free for all, `winner` first, then more stocks, then lower percent, ties share a place; teams: the winning team is place 1, the others 2 (the retail winner rule is `is_big_loser` and `team_standings`, **(unverified)** until Step 1 reads `fn_80175240`; the test pins the shape, Step 1 may change the rule). `exit_frames` follows `fn_80178050:991-1001`: **20** (`0x14`) when no slot is human (`lbl_804D3FC8` stays 1 only when no `player_standings[j].pkind == 0`), else **10** (`0x0A`); a canceled match leaves at once (0). In retail `pkind == 0` is **human** (`case 0: fn_80174B4C(...)` in the same function; `Gm_PKind_Human` in `fn_801791E4`), `1` is CPU, `3` an empty slot. `at_results_confirm(r, port, kind)` ignores a CPU or empty port, marks `confirmed`, and sets `done` when every human is confirmed (a canceled match: when any human is; no human at all: `done` at build). `at_results_screen(const AtResults*, AtScreen*)` builds the card list: one row per player (`P1`, fighter name, `4 KOs  1 fall  87%`), the winner first, `WINNER` in the trail. The countdown's polarity was found while writing the test; a reader who "corrects" it to the opposite should read `fn_80178050` first.
- [ ] **Step 4: The shims and the stand-in.** Shims `Ui_ResBegin(outcome, is_teams, canceled)`, `Ui_ResPlayer(port, pkind, ckind, stocks, kos, falls, percent, team, winner)`, `Ui_ResCommit()` (the host builds `AtResults` with `at_results_build`, draws it), `Ui_ResConfirm(port, kind)`, `Ui_ResDone()`. In `gmfrontend_atlas_data.inc`:

```c
static void far_enter(void* arg)
{
    ResultsMatchInfo* mi = arg;
    int i;
    /* the side-effect table of Task 10 step 1, as code: audio and state only, in the retail order */
    Ui_ResBegin(mi->match_end.outcome, mi->match_end.is_teams, gm_WasMatchCanceled(mi->match_end.outcome));
    for (i = 0; i < 4; i++) {
        const MatchPlayerData* p = &mi->match_end.player_standings[i];
        Ui_ResPlayer(i, p->pkind, p->ckind, p->stocks, fad_ko_total(p), p->self_destructs, p->percent, p->team, fad_is_winner(&mi->match_end, i));
    }
    Ui_ResCommit();
    /* RECONCILE with Step 1's table: the victory theme, the announcer, the rumble, the KO tally */
}

static void far_frame(void)
{
    int i;
    for (i = 0; i < 4; i++) {
        if (HSD_PadCopyStatus[i].err != 0) {
            Ui_ResConfirm(i, 2);
        } else if (HSD_PadCopyStatus[i].trigger & PAD_BUTTON_START) {
            Ui_ResConfirm(i, 1);
        }
    }
    if (Ui_ResDone() >= 0) {         /* frames to wait after the last confirm; -1 while someone has not */
        if (far_wait++ >= Ui_ResDone()) {
            gm_801A4B60();           /* the retail exit: the mode's next state decides */
        }
    }
}

static void far_exit(void* unused)
{
    Ui_Close("results");
    fn_801701AC();                   /* what gm_Scene_Results_OnExit does */
}

static GameScene fad_results_scene = { GS_RESULTS, far_frame, far_enter, far_exit, NULL };
```

and `gmFrontend_AtlasStandIn(u8 kind)` becomes `return kind == GS_RESULTS ? &fad_results_scene : NULL;` (with the `_Static_assert(GS_RESULTS == 5, ...)` beside step 2's title one, and `AT_SCENE_RESULTS` in `gw_ui_policy.c`). **No policy row is added yet:** the stand-in is reached only with `MELEE_ATLAS_SCENES=5:replace`. At acceptance (Task 12 and the owner's look) a policy row `{ 5, AT_POLICY_REPLACE, "results" }` is added, with a netplay exclusion in `gw_Ui_ScenePolicy` (`gs_ui_online()` returns RETAIL for kind 5). The field names of `GameScene` (`kind, on_frame, on_enter, on_exit`) follow `gmscdata.c:72-76`; the stand-in's `on_exit` receives `info->exit_data` as retail's does.
- [ ] **Step 5: `test_fe_atlas_results.py`** reads the Step 1 list (a comment block `/* RESULTS SIDE EFFECTS: <name> <class> ... */` above `far_enter`) and checks that each `audio` and `state` name occurs in `gmfrontend_atlas_data.inc`, that `far_exit` calls `fn_801701AC`, that `far_frame` reads `err` and `PAD_BUTTON_START` for each of four ports, and that no `Ui_Intent` is used (results takes START per port, not the merged menu input).
- [ ] **Step 6: Commit.** `atlas: Results stand-in (REPLACE, off by default; per-human confirm, the retail exit; side effects listed)`.

---

### Task 11: The title check, Game Over and the Language inventory

**Files:** none created except a note in `docs/NEXT-SESSION.md`; reads only.

- [ ] **Step 1: The title.** `grep -n '"title"' pc/platform/gw_ui_policy.c` shows the `OVERLAY` row; `python tools/port/atlas_gate.py --step 8` already requires `AT_POLICY_REPLACE` and the hook; confirm `gmtitle.c` is unchanged by step 8 (`git diff --stat` shows nothing in `gmtitle.c`). The title's look is step 2's checklist.
- [ ] **Step 2: Game Over (`GS_GAMEOVER`, `gm_Scene_GOver_OnEnter`, `gm_19EF.c:654-700`).** It is a 3D animated scene (a `GObj` model from `fn_8019F9C4(ckind)`, `SdIntro.dat` text, a score) whose enter data (`DebugGameOverData`: `x0`, `x8`, `x15`, `x16`, `x18`, `ckind`, `slot`) has **unnamed fields**. **Decision recorded: no-go for step 8** (not a list or a card until the fields are named); it is a candidate for step 10's frame pattern. Write the sentence into `docs/NEXT-SESSION.md`.
- [ ] **Step 3: "1P intermission and bonus summaries" (13.8's row).** Trace which retail scenes a Classic, Adventure and All-Star run visits (`MELEE_LOG=scene`, the scene trace the game already prints): `GS_INTRO_NORMAL`, `GS_INTRO_EASY`, `GS_REGEND_TOYFALL`, `GS_REGEND_CONGRATS` (a THP movie: `gm_1A9B.c`), `GS_PRIZE_INTERFACE`, `GS_GAMEOVER`. Which of them is "a list or a card" is **(unverified)**; the expected answer is none beyond results: the rest are video or 3D. List them in the table of Task 12 as `stays retail`, each with the reason, and say that nothing is built for them.
- [ ] **Step 4: The Language inventory.** Run `python tools/port/retail_screens.py` after Tasks 4 to 10: it shows which native entry points are now `ATLAS`. Add to `retail_screens_expected.json` the three owner-skipped screens (`SEL_DATA_SNAP`, `SEL_DATA_ARCHIVES`, and the Staff Roll scene `GS_STAFFROLL`) with `"stays": true`. **The decision for the owner (see "Owner decisions"):** while those three stay retail, "the last retail text screen" is never gone, so the Language row would stay forever. The plan removes nothing.
- [ ] **Step 5: Commit (workspace repo).** `docs: step 8 decisions recorded (title done by step 2, Game Over no-go, the Language inventory)`.

---

### Task 12: Documentation, the in-game proof and the retirement list

**Files (workspace repo):** `docs/TERMINOLOGY.md` (**data screen**, **retail text**), `menu/CLAUDE.md` (the retirement list below), `docs/NEXT-SESSION.md` (the state and the gate outcome), the step 8 row of `docs/superpowers/plans/` if an index exists. No `docs/scripting.md` change: the shims are not a `gd.ui` API.

**What the owner's look retires (nothing is deleted before it):** per accepted screen, the `FA_NATIVE` row stays as the fallback until the owner says the legacy path is not wanted; then (a separate follow-up, like step 6's Task 11) the screen's case in `mn_PcOpenNative` and the retail screen's menu-entry glue are removed, never the retail scene code or the disc's archives; the legacy `out_nav` pieces for the Event list, if any are wired, are removed with it (the spec's row says art exists; **(unverified)** which files: `grep -rn "event" menu/out_nav/*.json` first).

- [ ] **Step 1: Build and confirm the exe** (no window): `tools/port/build.sh` in `$MAIN` with the lane exports; `grep -a "Atlas data screen" "$GW_BUILD_ROOT/melee-pc.exe" | head -1` and `grep -a "sis round trip" ...` each print a line.
- [ ] **Step 2: In-game checklist (a Windows agent while the owner is away, second monitor, `MELEE_VOLUME=0`, ACE disc by default, vanilla for every item marked V; one game at a time; no screenshots as verification, a screenshot only to diagnose how something looks).**
  1. `frontend: sis round trip ok` in the log at the first Data screen. The text probe (`MELEE_ATLAS_TEXTPROBE=1`) prints counts per source; record GO, PARTIAL or NO-GO per source in `docs/NEXT-SESSION.md`. No disc text in any log (`python tools/port/check_no_disc_text.py` on the repo, and `grep` the run's `melee-pc.log` for a known event name: none).
  2. **Misc Records** (V): MAIN > DATA > RECORDS > MISC. RECORDS opens the Atlas list, 30 rows, the first five times read `H:MM`, B returns to the RECORDS hub on the MISC row. `MELEE_ATLAS_DATA=none`: the retail screen opens and behaves as before.
  3. **Event Match** (V): SOLO > EVENT MATCH lists 51 rows; focus moves with the stick across the whole list (wrap from the last row to the first); the mouse wheel scrolls; A on an event starts the retail event (the match loads, the event's rules apply); back from the event lands on the list at that row. Compare cleared marks and records against the retail list once (`MELEE_ATLAS_DATA=none`).
  4. **Special Messages, Bonus Records** (V; only when the gate allows): the unlocked set and order match the retail screen's; a message that cannot decode says so.
  5. **Sound Test** (V): A plays a row, A again stops it, another row switches; B stops all sound and the menu music returns; the Settings volumes are unchanged afterwards.
  6. **VS Records** (V): after a few played matches the ranking shows the played fighter; a fresh save shows an empty-state line, not a crash.
  7. **Name Entry** (V): create a tag, see it in VS > RULES tag pickers and on the character select (retail); delete it; a tag that exists is refused; the full list (120) shows no `NEW TAG` row. If the editor was dropped, the retail editor still opens from the list's A.
  8. **Results** (`MELEE_ATLAS_SCENES=5:replace`): a 2 player stock match, a 4 player match, a team match, a match with a CPU, a quit from the pause (cancelled): each shows the right winner and numbers; each human's START confirms that player; the exit lands where the retail exit does (the CSS in Versus); the victory music plays and stops; the next match starts normally (nothing stale from the stand-in). Compare against retail once (`MELEE_ATLAS_SCENES=5:retail`). **Results after a netplay match stays retail** (the policy excludes it): confirm.
  9. Every screen at 640x480, 960x720 (4:3) and 1920x1080 (wide); focus by pad and by mouse; the key hints; Reduced Motion on: cuts, no tweens.
  10. Frame cost: `MELEE_FPS=120`: each screen holds 120 fps; record the readout.
  11. `MELEE_ATLAS=0`: every screen above is retail and works.
- [ ] **Step 3: Capture and report.** Per run folder `"$GW_BUILD_ROOT/runs/<name>/melee-pc.log"`, the lines with `frontend:` and `ui:`; a yes or no for every numbered item and one line for each no; say plainly which items were not run. The owner decides whether each look is accepted; **a screen that proves too costly is dropped here** (its row removed from `fad_screens[]`, one line in `docs/NEXT-SESSION.md`).
- [ ] **Step 4: Commit (both repos).** `docs: step 8 terms, the retirement list, the state`.

---

## Self-review

**Spec coverage (13.8).**

| 13.8 item | Where |
|---|---|
| Event Match list and detail (`gmevent.c`) | Task 5 (list and the retail start; the detail is the explainer: its description text is gated by Task 1 and **(unverified)** until Task 5 step 1) |
| Name Entry | Task 9 (list and editor; the editor is droppable) |
| Sound Test, Special Messages | Tasks 7, 6 |
| VS, Bonus, Misc Records | Tasks 8, 6, 4 |
| Results (`gmresult.c`, `gmresultplayer.c`), `REPLACE` or `OVERLAY` | Task 10 (`REPLACE`; the `OVERLAY` with a window is step 10's `view` part if the owner wants the 3D winner) |
| Game Over, 1P intermission and bonus summaries | Task 11 (no-go with reasons; nothing is a list or a card until the fields are named) |
| Title, if step 2 did not take it | Task 11 step 1 (step 2 took it) |
| Stays: the opening movie and the memory-card prompt | not touched; Movies, Snapshots and Staff Roll (the owner's skips) are in the Task 11 inventory |
| Retired: retail text and layouts drop out of use; nothing of the disc is deleted or copied | Task 12 retirement list; Global Constraints (disc text never stored) |
| The Language row goes when the last retail text screen is gone | **Not done**; Task 11 step 4 and the owner decision below |
| Verified without the game: a table test per screen against a recorded sample | Tasks 2, 4, 5, 6, 8, 9, 10 (invented fixtures: a recorded sample of game data would be disc-derived, so the "recorded sample" of the spec is replaced by invented data of the same shape) |
| Must be seen: each screen by its real path, results after a real match and a netplay match, a name entry round trip | Task 12 step 2 |

**Deviations from the spec, all named.** (1) The entry hook leaves `FA_NATIVE` rows in place instead of switching them to `FA_ATLAS` (6.4 item 3): a per-screen fallback and zero table edits. (2) Results is `REPLACE` without the 3D winner and with retail's exits, not the mockup's three keys (Correction 4, 5). (3) The adapter owns the cursor on windowed lists (the host's wrap is not used). (4) "A recorded sample of the game data" is replaced by invented fixtures (no disc-derived data in the repo). (5) The Language row is not removed.

**Unverified items and where each is settled.**

| Item | Settled by |
|---|---|
| The English `.usd` strings decode with the default atlas' reverse table; glyph byte order | Task 1 steps 5 and 8 (the round trip and the probe) |
| Which archive and symbol hold each text source in `GS_FRONTEND` (`SdMenu.usd`/`SIS_MenuData` is what `mnmain.c:3019` loads in the menu scene) | Task 1 step 8 |
| What "locked" means for an event; the description's source; the first-entry focus | Task 5 step 1 |
| The message sort order, the bonus count, the date format | Task 6 step 1 |
| The sound list structure and groups | Task 7 step 1 |
| The VS stat types, units and whether the retail ranking is pre-sorted | Task 8 step 1 |
| The editor's validation order; the English glyph set; whether tag letters are full-width | Task 9 step 1 |
| The results side effects, the meaning of `kills[4]`/`percent`/`x9`, the winner and place rules | Task 10 step 1 |
| `AtScreen.tabs`, `Ui_Dialog`, the item shims, the disc-art decode and port card names (steps 4, 5) | the gate (`SOFT` lines) once those steps merge |
| Whether the host overlay's list primary is accepted by `gw_Ui_Begin` for an engine slot | Task 3 step 6 and Task 12 step 2 (a look) |
| The `out_nav` files the Event list retires | Task 12 retirement note |
| That nothing else reads the results scene's statics (`lbl_8046DBE8`) after the scene | Task 10 step 1 |

**Owner decisions needed** (also in the report that accompanied this plan): (1) the Language row: Movies, Staff Roll and Snapshots stay retail and draw retail text, so the row can never be "removed when the last retail text screen is gone"; options are keep it (the default of this plan), or remove it and let those three follow the disc's default language; (2) Results: `REPLACE` (no 3D winner) or an `OVERLAY` with a window over the retail winner scene (step 10 machinery); and whether Rematch and Main menu on the results screen are wanted (new features, spec 14); (3) Name Entry's editor if the English set is kana-first: list only, or drop the screen; (4) a NO-GO text outcome: accept screens without the disc's words (Events as numbered rows), or leave them retail.

**Placeholder scan.** Every task that depends on a fact the plan could not read says "(unverified)" and names the step that reads it; no step defers a decision it could make. Where an unbuilt step's name is unknown the plan says `RECONCILE`, shows the code against an assumed name and relies on the gate. Two places in the code blocks are **intentional corrections to read before coding**: Task 4 step 5 (five label guesses) and Task 10 step 3 (the countdown's polarity, found while writing the test): both say so in place.

**Type and name consistency.** `AtDataRow`/`AtDataView`/`AT_DR_*`/`AT_DATA_ROWS` (Task 2) are used by Tasks 4 to 9; `at_misc_row`, `at_misc_fill`, `at_event_row`, `at_msg_order`, `at_rank`, `at_stat_text` live in `gw_ui_data_models.c`; `AtName` functions (Task 9) and `AtResults` functions (Task 10) are in their own units; shims `gw_Ui_*` (host) match `Ui_*` (game) apart from the prefix; `FD_*` ids and `fad_screens[]` rows are the ones `test_fe_atlas_data.py` parses. `FA_EV_*` and `FA_PRIMARY_*` are step 2's constants.

**Execution recommendation.** Tasks 0 to 2 are self-contained: one fresh agent each, a review between. Task 3 touches retargeted game code and the frame order of the frontend: one agent, the coordinator reviews the guard output and the PowerPC syntax check before the build. Tasks 4 to 9 are independent of each other once Task 3 is in: they can go to separate agents on separate branches (merge in the order 4, 5, 6, 7, 8, 9). Task 1 step 8 (the text gate) is the one that decides Tasks 5 to 8 and 6: run it as early as a Windows agent and the owner's absence allow, and before Task 6. Task 10 is the most expensive and the least urgent: after the others and after the owner has seen one screen. Task 12 is for a Windows agent while the owner is away, or for him.
