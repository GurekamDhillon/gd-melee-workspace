# Atlas step 3: Envoy's remaining screens, the in-match HUD, and the retail takeover capability: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Envoy's live screens (reward, swap, setup, pause and its confirm, results, the online reward pick) and its in-match HUD (build strip, opponent card, synergy toast, pickup note, the "collect the drives" and payout-hold banners, co-op strips) onto Atlas, and build the retail takeover capability (retail element registry and mask with one guard per draw site, the HUD zone description with keep-out rectangles, the pause description with the pause hooks and an unpause request). The capability is **off by default**: the element mask is empty and the Atlas pause takeover is switched off, so retail damage, stocks, timer and pause look exactly as today.

**Architecture:** Two new pure C units join the step 1 set: `gw_ui_retail.c` (element ids, the mask built from four sources, the pause state machine) and `gw_ui_hud.c` (zones inside the title-safe box, keep-out rectangles, stacking, per-zone caps). They draw only through `AtSink` and run in standalone native tests. New parts (offer card, port card, strip, banner, toast, link) join `gw_ui_parts.c`; a `cards` primary and grid `links` join the screen record. The game side gets one guard line per retail draw site and two pause notifications, all calling unprefixed shims that read the host mask. `gw_script_ui.inc` gains `gd.ui.hud`, `gd.ui.toast`, `gd.ui.retail_hide`, `gd.ui.retail`, `gd.ui.unpause`, `gd.ui.forget` and draws the HUD layer every frame under the screen stack. Envoy gets one description module per screen, attached to the existing run objects the way `atlas_bag.lua` attaches to `RunScreen`.

**Tech Stack:** C11 (host, built by `tools/port/build.sh` with the repo's clang for `i686-pc-windows-msvc`), PowerPC-retargeted game C (syntax-checked with `clang --target=powerpc-unknown-eabi -fsyntax-only`), Lua 5.4 (`lua` on PATH), the existing `tools/port/native_test.sh` harness and `tools/port/envoy_bundle.py`.

**Spec:** `docs/superpowers/specs/2026-10-06-menu-reunification-design.md` (step 3 is 13.3; the capability is 6.8; the owner's decisions are section 2). **Step 1 plan (form and the code this builds on):** `docs/superpowers/plans/2026-10-06-atlas-step1-components-and-envoy-bag.md`.

## Global Constraints

Exact values come from the spec or from the step 1 code as merged. If a task seems to need a different value, stop and ask the coordinator.

- **Everything from step 1's Global Constraints still holds** (canvas, text roles and the 12 px floor, the fit rule, depth and shape, motion on the UI clock, budgets, naming, English only, no disc-derived data, no screenshots as proof, process rules, two repositories). Read them once in the step 1 plan; they are not repeated in full here.
- **The style rules every new part is tested against (the three things reviewers caught most in step 1):**
  1. **Chamfers are never drawn over.** No polygon vertex of anything a part draws may lie inside the cut-away triangle of a chamfered corner (8 px panes and modal, 5 px rows, buttons, notes, tags, toasts, banners, port cards, 3 px cells and offer cards' tags). The test helper is `corners_clear(rect, chamfer)` (it exists in `pc/tests/atlas_parts_test.c`; Task 2 moves it to `atlas_rec.h` so every test can use it).
  2. **Focus is three cues at once.** Anything that takes focus (offer cards, rows, cells, dialog buttons) shows the 2 px lift, the ember front edge, and a tick (rows) or four registration brackets (cells, cards), all at once; at rest it shows none of them. HUD parts **never** take focus and never show a focus cue.
  3. **Text never leaves its box.** Every string a part draws is measured with the same function that draws it, fitted with `at_fit` (one role down, then an ellipsis) or wrapped with `at_wrap` (explainer up to 3 lines, dialogs up to 4, toasts 1 title line plus 1 rule line, banners 1 line), and every test checks `text_left >= box.x` and `text_right <= box.x + box.w` at 640, 853 and 1140 wide with the longest real Envoy strings (Task 2 adds `texts_inside(rect)` to `atlas_rec.h`).
- **Envoy rulings (bind every Envoy task):** one short rule per piece on screen (a piece with more rules pages them with Z / L / R, as the bag does); each piece has a distinct visual identity (drive colour fill plus rarity ring, keystone arch stone with its letter, synergy emblem colour); the synergy notice is a **small top-corner toast**, never a banner; **link flashes stay** (the world-space chain flashes in `synergy_fx.lua` are not HUD and are not touched); **the crit HUD pop-up goes** (no HUD text for a crit, ever); a **quiet match HUD** (at most one banner, one toast per corner, three opponent cards, one pickup note; nothing else flashes); **press A to collect drives** (the collect banner carries the A glyph); **the end-of-stage payout hold** keeps its banner and its leave progress.
- **Retail takeover is off by default.** The element mask is empty unless an environment variable, a console command, a script (offline) or a scene policy sets it; the Atlas pause takeover is off unless `MELEE_ATLAS_PAUSE=1` or the setting `atlas_pause` is on. With both off, every guard's code path is the retail one.
- **Netplay safety (normative for the HUD and the guards):** the HUD is presentation only: its record changes only from script hooks (which never run on a resimulated frame, `gs_may_run`, `gw_script.c:786`), its draw never calls Lua, its timings are on the UI clock (wall time), and it draws online. A guard never skips a proc, only a render callback or a panel's visibility, so no simulation state changes. The mask's effective value is **0 while netplay or rollback is enabled** (the same rule as `gd.hud_visible`, `gw_Script_StatusHUDVisible`, `gw_script.c:464`). `gd.ui.retail_hide` and `gd.ui.unpause` are refused online. The Atlas pause takeover never runs in a netplay match.
- **Ownership and lifetime (the engine-side holes step 1 reviews found):** every HUD, toast, mask bit and screen belongs to the script that set it; another script cannot change it (`belongs to another script`); an unload, a disable or a scene change releases all of it, in the same function that releases the script's screens (`gs_ui_release`); every Lua reference the engine holds is unref'd on replace and on release. The tests for these run **as a mod script on the real path** (see the next rule), never as the console.
- **Test the real path.** Step 1's console-driven tests hid a bug. Every binding test in this plan calls `gd.ui.*` as a mod script (`gs.cur` set to a script slot whose id is `envoy/main`, not `gs.console`) and drives handlers through `gs_ui_tick` (where `gs.cur` is -1, as in the exe). A check that only passes as the console is not a pass.
- **One screen stack** exists (step 1; `docs/scripting.md` "gd.ui"). Step 3 does not add per-port stacks; see "Local co-op and the single stack" below for where it matters and the recommendation.

## Review Focus

| # | What goes wrong for the player | Pinned by |
|---|---|---|
| 1 | **The HUD covers the retail percent or the timer** at 4:3 or wide (the build strip under a damage plate, an opponent card over the clock). | Task 6 `keepout_*` checks at 640, 853, 1140; Task 16 Lua test `hud stays clear of the retail HUD`; Task 21 step 4 |
| 2 | **A retail element stays hidden after the script that hid it is gone** (an unload, a crash, a scene change) or is hidden online. | Task 3 `sources_and_online`; Task 7 binding test `released on unload, on scene change, ignored online` (run as a mod script) |
| 3 | **The pause never ends**: the Atlas pause's Resume does not unpause retail, or an unpause request leaks into a later pause or a netplay match. | Task 3 `pause_*`; Task 4 PowerPC check of the unpause shim; Task 8 binding test `unpause is one-shot, offline, only while paused`; Task 21 step 6 |
| 4 | **The reward countdown or a stage end eats the player's pick**: the countdown takes an offer while the player is mid-confirm, or the screen closes with the drive unresolved. | Task 10 Lua tests `countdown takes the first offer, never discards` and `closing resolves every offer` |
| 5 | **A noisy match**: two banners, a toast queue that grows, the crit pop-up back, a flash every hit. | Task 6 `caps_*`; Task 16 Lua tests `quiet HUD caps`, `no crit text`, `link flashes still fire` |
| 6 | **Ran out of screen slots**: Envoy registers more screens than the 8 slots and a late screen raises mid-run. | Task 1 `forget frees a slot` and the slot count test; Task 17 Lua test `envoy registers at most N screens` |

---

## Dependencies on step 2 (planned in parallel, not built)

| Step 3 needs | What step 2 builds | What this plan does |
|---|---|---|
| The Envoy entry `solo > ENVOY` that `opens` `envoy.setup` (spec 8.1, 13.2) | the registry (U6) and manifest `menus` parsing | **Waits** for that one line. Task 12 builds `envoy.setup` and opens it from Envoy's existing route (the app's `setup` screen, `envoy` console). Task 12 step 6 adds the `menus` line to `envoy/mod.json` only if step 2's parser is merged; otherwise it is left as a named follow-up |
| The trail's parents ("SOLO > ENVOY") from the entry that opened the screen | the registry and the stack's parent chain | **Minimal piece included**: every Envoy description sets `parents = {"SOLO", "ENVOY"}` itself (the step 1 record already has `AtScreen.parent[3]`). When step 2 lands, the entry's parents win and these lines are deleted |
| The **scene policy** table (`RETAIL` / `OVERLAY` / `REPLACE`, spec 6.8 part 1) | step 2 builds it for the title | **Not needed by step 3**: the HUD and the pause live inside a match, not a scene swap. Step 3 builds the element mask with a `policy` source slot (`AT_RS_POLICY`) and the setter `gw_Ui_RetailSetSource(AT_RS_POLICY, mask)`; step 2's `OVERLAY` entries call it. Whichever step merges second wires the two (one call). If step 2 has already merged its own mask stub, Task 3 replaces it and keeps its call sites |
| Mods registering entries under parent `pause` (spec 8.1 "later `pause` (step 3)") | the registry's parent list | **Minimal piece included**: the pause screen's entries come from its own description (Task 8, Task 13). Adding `pause` to the registry's parent list is one line in step 2's table; it is a follow-up named in Task 8, done only once U6 exists |
| `MELEE_ATLAS=0` fallback | step 2's router switch | Not used. Envoy keeps its own switch (`envoy ui legacy`) until the owner's look (Task 18) |

## Local co-op and the single stack

Only the top screen of the one stack draws and takes input. Where step 3 is affected:

- **Reward and swap in co-op:** not affected. `coop.lua` already serialises them (`screen_owner`, `coop.lua:301-307`: one seat's screen at a time, the other strip stays out of the way). The Atlas versions keep that rule; the screen's `port` field tints the focus brackets with the seat's colour.
- **The bag in co-op:** affected. Each seat has its own bag id (`envoy.bag`, `envoy.bag.pN`, `atlas_bag.lua:20`), but if seat 2 opens its bag while seat 1's is up, seat 2's covers seat 1's and seat 1 loses input. Task 17 adds the rule: a seat's bag does not open while another seat's Envoy screen is on top; that seat gets a toast in its own corner ("Player 1 has a screen open").
- **The pause:** not affected (one pauser at a time; retail has the same rule).
- **The HUD:** not affected. The HUD is not on the stack: every seat's strip draws in its own zone at once.

**Recommendation:** do not build per-port stacks. Keep one stack with "one seat's screen at a time" for Envoy, and give character select (step 4) several focus tokens inside **one** screen (the spec's "CSS and lobby keep one token per port", section 9), which is what CSS needs. Revisit only if a real case needs two independent full screens at once (split-screen co-op menus); no current design has one. The owner has not decided; this plan works either way because every Envoy screen already carries its seat's port.

---

## File structure

Game repo (`melee/`).

| File | Create/Modify | Responsibility |
|---|---|---|
| `pc/platform/gw_ui_retail_ids.h` | Create | the retail element ids only (an enum, no types), included by host and game side |
| `pc/platform/gw_ui_retail.h/.c` | Create | names and parsing of element ids, the mask from four sources, the online rule, the pause state machine and the one-shot unpause request |
| `pc/platform/gw_ui_hud.h/.c` | Create | the HUD record, zones in the title-safe box, keep-out rectangles, stacking and caps, the HUD render through `AtSink` |
| `pc/platform/gw_ui_parts.h/.c` | Modify | parts: `at_part_offer` (offer card), `at_part_port_card`, `at_part_strip`, `at_part_banner`, `at_part_toast`, `at_part_link` |
| `pc/platform/gw_ui_screen.h/.c` | Modify | the `cards` primary (`AT_PRIMARY_CARDS`), grid `links`, `kind = "pause"`, the countdown field |
| `pc/platform/gw_ui_render.c` | Modify | lay out and draw `cards`, draw grid links under the cells, the countdown in the trail's right end |
| `pc/platform/gw_script_ui.inc` | Modify | `gd.ui.hud`, `hud_clear`, `toast`, `retail_hide`, `retail`, `unpause`, `forget`; the HUD draw pass; the retail pause notification; 16 slots |
| `pc/platform/gw_script.c` | Modify | call the HUD draw before `gs_ui_draw`; release HUD and mask with the script; the console command `atlas` |
| `src/melee/if/ifstatus.c`, `ifstock.c`, `iftime.c`, `ifnametag.c`, `ifmagnify.c`, `ifcoget.c`, `ifprize.c`, `ifhazard.c` | Modify | one guard line per render callback (`Ui_RetailHidden(id)`) under `TARGET_PC` |
| `src/melee/gm/gmpause.c`, `gm/gmvs.c` | Modify | the pause panel guard; the pause on/off notifications; the unpause request read |
| `pc/tests/atlas_rec.h` | Modify | `corners_clear`, `texts_inside`, `focus_cues_at` shared helpers |
| `pc/tests/atlas_retail_test.c`, `atlas_hud_test.c` | Create | native tests of the two new units |
| `pc/tests/atlas_parts_test.c`, `atlas_screen_test.c`, `atlas_render_test.c`, `atlas_binding_test.c` | Modify | the new parts, `cards`, `links`, the binding additions on the real path |
| `pc/tests/atlas_ui_stub.lua`, `atlas_ui_stub_test.lua` | Modify | the stand-in follows every new `gd.ui` call |
| `pc/tests/envoy_atlas_screens.lua`, `envoy_atlas_hud.lua` | Create | offline tests of the Envoy descriptions and the HUD |
| `pc/scripts/examples/envoy/scripts/atlas_kit.lua` | Create | shared helpers for Envoy descriptions (ids per seat, parents, rule paging, log_once), moved out of `atlas_bag.lua` |
| `.../envoy/scripts/atlas_reward.lua`, `atlas_swap.lua`, `atlas_setup.lua`, `atlas_pause.lua`, `atlas_results.lua`, `atlas_netpick.lua`, `atlas_hud.lua` | Create | one description per screen, and the HUD |
| `.../envoy/scripts/atlas_bag.lua` | Modify | uses `atlas_kit.lua`; the swap layout is handed to `atlas_swap.lua` instead of the legacy grid |
| `.../envoy/scripts/run_screen.lua`, `run_hud.lua`, `run_host.lua`, `retail_app.lua`, `mod_lab.lua`, `coop.lua`, `foe_lab.lua` | Modify | attach points (two lines each), then the retirement in Task 18 |
| `.../envoy/scripts/main.lua` | Regenerate | by `tools/port/envoy_bundle.py` |
| `.../envoy/MENUS.md` | Modify | the Atlas contract replaces the grid contract at the top |
| `pc/scripts/examples/demos/atlas-hud/`, `atlas-pause/` | Create | single-feature demo mods (HUD zones and keep-outs with the mask; the pause takeover) |

Workspace repo (root).

| File | Create/Modify | Responsibility |
|---|---|---|
| `tools/port/native_test.sh` | Modify | `atlas-retail`, `atlas-hud`; new sources for `atlas-parts`, `atlas-render`, `atlas-binding` |
| `tools/port/envoy_bundle.py` | Modify | the new modules in `ENVOY_MODULES`; `grid` and the legacy menu modules removed in Task 18 |
| `docs/scripting.md`, `docs/TERMINOLOGY.md` | Modify | the new `gd.ui` calls; `HUD zone`, `keep-out rectangle`, `retail pause takeover` |

## Preflight (once, before Task 1; not a task)

- [ ] **Step 1: Read.** Root `CLAUDE.md`, `docs/NEXT-SESSION.md`, `melee/CLAUDE.md` ("The shim boundary"), `melee/pc/docs/PORT_DEV_QUICKREF.md`, spec sections 2, 4.5-4.9, 6.8, 7, 8.4, 13.3, the step 1 plan's Global Constraints and Task 11, `docs/scripting.md` "Atlas screens (`gd.ui`)" and `gd.hud_visible`, and `envoy/MENUS.md` top section.
- [ ] **Step 2: Make a private lane** exactly as the step 1 plan's Preflight step 2, with the name `atlas3` (`tools/port/agent_new.sh atlas3`; workspace worktree `worktrees/ws-atlas3` on `ws/atlas3`), and define `MAIN`, `WS`, `GW_MELEE`, `GW_BUILD_ROOT` and the `nt` helper the same way.
- [ ] **Step 3: Record the baselines** (all must still pass at the end):

```bash
cd "$GW_MELEE" && for t in envoy_run_ux envoy_atlas_bag atlas_ui_stub_test envoy_hud envoy_coop envoy_online; do printf '%s: ' $t; lua pc/tests/$t.lua | tail -1; done
for t in atlas-tokens atlas-layout atlas-focus atlas-input atlas-screen atlas-stack atlas-parts atlas-render atlas-binding; do nt $t | tail -1; done
cd "$WS" && python tools/port/envoy_bundle.py --check
```

Write the numbers down; later tasks say "the baseline count plus N".
- [ ] **Step 4: Check two states the plan assumes, and stop if either is false.** (a) Step 1's Atlas bag has had the owner's look and is accepted (ask the coordinator; `atlas_bag.lua` still has `A.setting.on=false`, so the switch is still `uxatlas`). If it has not, Tasks 1-9 can proceed, Tasks 10-18 wait. (b) Whether step 2 has merged anything (`git -C "$GW_MELEE" log --oneline -20 -- pc/platform/gw_ui_registry.c src/melee/gm/gmfrontend_atlas.inc`): if it has, apply the "Dependencies on step 2" table's merge notes.
- [ ] **Step 5: What step 3 does NOT depend on.** The overlay's ordering against frontend scenes (spec 6.1, unverified) is a step 2 question: every step 3 screen and the HUD draw inside a match, where `gd.kit` already draws over the world and the retail HUD (`hud.lua`, `run_hud.lua` do today). The Envoy setup screen draws where Envoy's menus draw today (in a match or the LAB scene the app runs in), so it inherits their proven path.

---

### Task 1: Room for Envoy's screens: 16 slots and `gd.ui.forget`

Envoy will hold up to nine screens (bag, bag.p2, reward, keystone, swap, setup, pause, results, the online pick). Step 1 has 8 slots and `close` does not free one (`docs/scripting.md` "gd.ui", `GS_UI_SLOTS 8`).

**Files:**
- Modify (game repo): `melee/pc/platform/gw_script_ui.inc` (`GS_UI_SLOTS`, a new `l_ui_forget`, the function table at `gs_ui_funcs[]`), `melee/pc/tests/atlas_binding_test.c`, `melee/pc/tests/atlas_ui_stub.lua`, `melee/pc/tests/atlas_ui_stub_test.lua`

**Interfaces:**
Produces: `GS_UI_SLOTS 16`; `gd.ui.forget(id)` -> `true` (the screen is closed if on the stack, its Lua references are released, its slot is free); raises `gd.ui: no screen "id"` for an unknown id and `gd.ui.screen: "id" belongs to another script` for another script's.

- [ ] **Step 1: Write the failing binding test, on the real path.** Append to `atlas_binding_test.c` a case that loads its Lua as script slot 0 with id `envoy/main` (the existing helper that sets `gs.cur = 0` and `gs.s[0].id`; grep `envoy/main` in the file for it; if it only has a console helper, add `run_as_script(int slot, const char *lua)` that sets `gs.cur = slot`, runs, and restores `gs.cur = -1`):

```c
static void forget_frees_a_slot(void)
{
    int i;
    char lua[256];
    for (i = 0; i < 16; i++) {                                /* 16 screens fit */
        snprintf(lua, sizeof lua, "assert(gd.ui.screen{id='envoy.s%d', trail={title='T'}, primary={kind='list', items={{id='a', label='A'}}}})", i);
        CHECK(run_as_script(0, lua) == 0);
    }
    CHECK(run_as_script(0, "assert(not pcall(gd.ui.screen, {id='envoy.s16', trail={title='T'}, primary={kind='list', items={{id='a', label='A'}}}}))") == 0);
    CHECK(run_as_script(0, "assert(gd.ui.open('envoy.s3')); assert(gd.ui.forget('envoy.s3')); assert(gd.ui.state().depth == 0)") == 0);
    CHECK(run_as_script(0, "assert(gd.ui.screen{id='envoy.s16', trail={title='T'}, primary={kind='list', items={{id='a', label='A'}}}})") == 0);
    CHECK(run_as_script(1, "assert(not pcall(gd.ui.forget, 'envoy.s0'))") == 0);   /* another script: refused */
    CHECK(run_as_script(0, "assert(not pcall(gd.ui.forget, 'envoy.nope'))") == 0);
    CHECK(lua_refs_held() == refs_for_screens(16));           /* no leaked registry references */
}
```

`lua_refs_held()` counts live references: add it as a test helper that walks `gs_ui_slot[]` and sums `at_screen_fn_refs`; `refs_for_screens(n)` is what n list screens with no handlers hold (0 refs each plus none), so the check is `== 0` here; write it so a handler-bearing variant can be added.
- [ ] **Step 2: Run it and see it fail.** `nt atlas-binding | tail -3`. Expected: FAIL lines for the 16-screen loop (slot 9 raises) and for `gd.ui.forget` (nil).
- [ ] **Step 3: Implement.** In `gw_script_ui.inc`: `#define GS_UI_SLOTS 16`. Add:

```c
/* gd.ui.forget(id): close it if it is on the stack, release every Lua reference it holds, free its slot. */
static int l_ui_forget(lua_State *L) {
    int slot = gs_ui_slot_arg(L, 1);                       /* raises for an unknown id or another script's (gs_ui_may_touch) */
    GsUiSlot *u = &gs_ui_slot[slot];
    while (at_stack_remove(&gs_ui_stack, slot)) {}          /* a duplicate entry may exist (open pushes again) */
    if (u->dialog_fn >= 0) { luaL_unref(L, LUA_REGISTRYINDEX, u->dialog_fn); u->dialog_fn = -1; }
    gs_ui_unref_screen(L, &u->sc);
    memset(u, 0, sizeof *u);
    u->dialog_fn = -1;
    if (at_stack_top(&gs_ui_stack) >= 0) gs_ui_prime(at_stack_top(&gs_ui_stack));
    lua_pushboolean(L, 1);
    return 1;
}
```

Run `on.close` first when the screen was on top (call the existing `gs_ui_close_screen(slot)` before the loop when `at_stack_top == slot`). Check that `gs_ui_slot_arg` enforces `gs_ui_may_touch`; if it does not, add the check and the message `gd.ui.screen: "%s" belongs to another script`. Add `{"forget", l_ui_forget}` to `gs_ui_funcs[]`.
- [ ] **Step 4: The stand-in follows.** In `atlas_ui_stub.lua` set the slot cap to 16 (it reads no slot cap today: add `Stub.slots = 16` and enforce it in `Stub.screen`), add `Stub.forget(id)` with the same errors, and a test in `atlas_ui_stub_test.lua`: 16 fit, the 17th raises, forget frees one, another owner is refused.
- [ ] **Step 5: Run.** `nt atlas-binding | tail -1` -> `0 failed`; `lua pc/tests/atlas_ui_stub_test.lua | tail -1` -> PASS.
- [ ] **Step 6: Commit (game repo).** `git add pc/platform/gw_script_ui.inc pc/tests/atlas_binding_test.c pc/tests/atlas_ui_stub.lua pc/tests/atlas_ui_stub_test.lua && git commit -m "gd.ui: 16 screen slots and gd.ui.forget (closes, releases references, frees the slot)"`

---

### Task 2: Shared style checks in the test helpers

Every later test uses the same three style checks; step 1 had them only inside `atlas_parts_test.c`.

**Files:**
- Modify (game repo): `melee/pc/tests/atlas_rec.h`, `melee/pc/tests/atlas_parts_test.c` (use the shared copies; delete the local `corners_clear`, `text_left`, `text_right`)

**Interfaces:**
Produces in `atlas_rec.h` (all read `REC` and use the fake width from `atlas_fake.h`, which `atlas_rec.h` now includes):
`int corners_clear(AtRect r, float c)`; `int texts_inside(AtRect r)` (every recorded text inside r, with its fitted width); `int focus_cues_at(AtRect r, int is_cell)` (returns the number of cues found for a part drawn at r: lift, ember edge, tick or 4 brackets, so a test writes `CHECK(focus_cues_at(r, 1) == 3)`); `int no_focus_cues(void)` (no `AT_C_EMBER` and no `AT_C_LIFT` anywhere).

- [ ] **Step 1: Move and add.** Move `corners_clear`, `text_left`, `text_right` from `atlas_parts_test.c` (they start under the comment "round 2: the chamfer rule") into `atlas_rec.h` unchanged. Add:

```c
static int texts_inside(AtRect r)
{
    int i;
    for (i = 0; i < REC.nt; i++)
        if (text_left(&REC.t[i]) < r.x - 0.01f || text_right(&REC.t[i]) > r.x + r.w + 0.01f) {
            printf("  text \"%s\" leaves its box [%g, %g]\n", REC.t[i].s, r.x, r.x + r.w);
            return 0;
        }
    return 1;
}
/* Count the focus cues of a part drawn at r: 1 for a lifted face (any AT_C_LIFT poly whose top is r.y - 2),
 * 1 for an ember front edge (an AT_C_EMBER poly along the bottom edge), 1 for a tick (rows: an ember poly at the left
 * edge, 4 px wide) or for brackets (cells: 8 ember or port-coloured strips outside r). */
static int focus_cues_at(AtRect r, int is_cell)
{
    int i, lift = 0, edge = 0, tick = 0, br = 0;
    for (i = 0; i < REC.np; i++) {
        const RecPoly *p = &REC.p[i];
        if (p->rgba == AT_C_LIFT && fabsf(poly_miny(p) - (r.y - 2.0f)) < 0.6f) lift = 1;
        if (p->rgba == AT_C_EMBER && poly_maxy(p) >= r.y + r.h - 2.01f && poly_maxx(p) - poly_minx(p) > r.w * 0.5f) edge = 1;
        if (!is_cell && p->rgba == AT_C_EMBER && poly_maxx(p) - poly_minx(p) <= 4.01f && poly_minx(p) <= r.x + 0.01f) tick = 1;
        if (is_cell && (poly_minx(p) < r.x - 0.01f || poly_maxx(p) > r.x + r.w + 0.01f) && p->rgba != AT_C_LIFT) br++;
    }
    return lift + edge + (is_cell ? (br >= 8) : tick);
}
static int no_focus_cues(void) { return count_color(AT_C_EMBER) == 0 && count_color(AT_C_LIFT) == 0; }
```

Before relying on `focus_cues_at`, prove it on the step 1 parts: in `atlas_parts_test.c` add `CHECK(focus_cues_at(r, 0) == 3)` for a focused row and `CHECK(focus_cues_at(cell_r, 1) == 3)` for a focused cell, and `CHECK(no_focus_cues())` at rest. If the lift's top or the edge's position in the merged parts differ from these numbers, adjust the helper to the merged geometry (read `at_part_row` and `at_part_cell`), never the parts.
- [ ] **Step 2: Run.** `nt atlas-parts | tail -1` and `nt atlas-render | tail -1`: the baseline count plus the new checks, `0 failed`.
- [ ] **Step 3: Commit (game repo).** `git commit -am "atlas tests: corners_clear, texts_inside, focus_cues_at shared in atlas_rec.h"`

---

### Task 3: The retail element registry, the mask and the pause state machine (pure C)

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_retail_ids.h`, `gw_ui_retail.h`, `gw_ui_retail.c`, `melee/pc/tests/atlas_retail_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (a case `atlas-retail` and its name in the die message)

**Interfaces:**
Produces:

```c
/* gw_ui_retail_ids.h - retail element ids (spec 6.8). An enum only: included by host C and by game-side TUs under TARGET_PC. */
#ifndef GW_UI_RETAIL_IDS_H
#define GW_UI_RETAIL_IDS_H
enum {
    AT_RE_HUD_DAMAGE = 0,   /* the percent plates: ifStatus_802F5DE0 / ifStatus_802F5E50 */
    AT_RE_HUD_STOCK = 1,    /* stock icons: fn_802F9680, fn_802F94E0, fn_802F95E8, fn_802F9548, fn_802F9598 */
    AT_RE_HUD_TIMER = 2,    /* match timer and countdown: iftime.c GXLink sites */
    AT_RE_HUD_NAMETAG = 3, AT_RE_HUD_MAGNIFY = 4, AT_RE_HUD_COIN = 5, AT_RE_HUD_PRIZE = 6, AT_RE_HUD_HAZARD = 7,
    AT_RE_PAUSE_PANEL = 8,  /* the GmPause panel (gm_801A0FEC) */
    AT_RE_COUNT = 9
};
#endif
```

```c
/* gw_ui_retail.h - which retail elements Atlas hides, and the retail pause as Atlas sees it. Pure C. */
enum { AT_RS_ENV, AT_RS_CONSOLE, AT_RS_SCRIPT, AT_RS_POLICY, AT_RS_COUNT };
typedef struct { unsigned src[AT_RS_COUNT]; int script_owner; } AtRetail;     /* script_owner: script slot + 1, 0 none */
const char *at_retail_name(int id);                   /* "hud.damage" ... "pause.panel"; NULL out of range */
int at_retail_parse(const char *list, unsigned *mask, char *err, int cap); /* "hud.damage,hud.stock" or "all" or "" */
unsigned at_retail_script_allowed(void);              /* what a mod may hide: everything but hud.timer */
void at_retail_set(AtRetail *r, int source, unsigned mask);
unsigned at_retail_effective(const AtRetail *r, int online);   /* the OR of the sources; 0 when online */
int at_retail_hidden(const AtRetail *r, int id, int online);
void at_retail_release_script(AtRetail *r, int owner);         /* the script source clears when its owner goes */

typedef struct { int paused, pauser, takeover, unpause_req; } AtPause;
void at_pause_on(AtPause *p, int pauser, int takeover_wanted, int online);   /* takeover only offline */
void at_pause_off(AtPause *p);                                               /* clears any request too */
int  at_pause_request_unpause(AtPause *p, int online);                       /* 1 accepted: paused, offline, none pending */
int  at_pause_take_unpause(AtPause *p);                                      /* the pauser once, else -1 */
```

- [ ] **Step 1: Write the failing test** `melee/pc/tests/atlas_retail_test.c`:

```c
#include "atlas_check.h"
#include "../platform/gw_ui_retail.h"

static void names_and_parse(void)
{
    unsigned m = 0; char err[96];
    CHECK_STR(at_retail_name(AT_RE_HUD_DAMAGE), "hud.damage");
    CHECK_STR(at_retail_name(AT_RE_PAUSE_PANEL), "pause.panel");
    CHECK(at_retail_name(AT_RE_COUNT) == NULL);
    CHECK(at_retail_parse("hud.damage, hud.stock", &m, err, sizeof err) && m == ((1u << AT_RE_HUD_DAMAGE) | (1u << AT_RE_HUD_STOCK)));
    CHECK(at_retail_parse("", &m, err, sizeof err) && m == 0);
    CHECK(at_retail_parse("all", &m, err, sizeof err) && m == (1u << AT_RE_COUNT) - 1);
    CHECK(!at_retail_parse("hud.damage,hud.bogus", &m, err, sizeof err) && strstr(err, "hud.bogus") != NULL);
    CHECK((at_retail_script_allowed() & (1u << AT_RE_HUD_TIMER)) == 0);   /* a mod never hides the match clock */
}
static void sources_and_online(void)
{
    AtRetail r; memset(&r, 0, sizeof r);
    CHECK(at_retail_effective(&r, 0) == 0);                                 /* empty by default */
    at_retail_set(&r, AT_RS_ENV, 1u << AT_RE_HUD_DAMAGE);
    at_retail_set(&r, AT_RS_SCRIPT, 1u << AT_RE_HUD_STOCK); r.script_owner = 3;
    CHECK(at_retail_hidden(&r, AT_RE_HUD_DAMAGE, 0) && at_retail_hidden(&r, AT_RE_HUD_STOCK, 0));
    CHECK(!at_retail_hidden(&r, AT_RE_HUD_TIMER, 0));
    CHECK(at_retail_effective(&r, 1) == 0 && !at_retail_hidden(&r, AT_RE_HUD_DAMAGE, 1));   /* online: nothing hidden */
    at_retail_release_script(&r, 2);                                        /* not the owner: no change */
    CHECK(at_retail_hidden(&r, AT_RE_HUD_STOCK, 0));
    at_retail_release_script(&r, 3);
    CHECK(!at_retail_hidden(&r, AT_RE_HUD_STOCK, 0) && r.script_owner == 0 && at_retail_hidden(&r, AT_RE_HUD_DAMAGE, 0));
    CHECK(!at_retail_hidden(&r, -1, 0) && !at_retail_hidden(&r, AT_RE_COUNT, 0));             /* out of range: never hidden */
}
static void pause_machine(void)
{
    AtPause p; memset(&p, 0, sizeof p); p.pauser = -1;
    CHECK(!at_pause_request_unpause(&p, 0));                               /* not paused: refused */
    at_pause_on(&p, 2, 1, 0);
    CHECK(p.paused && p.pauser == 2 && p.takeover);
    CHECK(at_pause_take_unpause(&p) == -1);                                /* nothing requested */
    CHECK(at_pause_request_unpause(&p, 0) && !at_pause_request_unpause(&p, 0));   /* one pending at most */
    CHECK(at_pause_take_unpause(&p) == 2 && at_pause_take_unpause(&p) == -1);     /* one-shot */
    at_pause_off(&p);
    CHECK(!p.paused && p.pauser == -1 && !p.takeover && !p.unpause_req);
    at_pause_on(&p, 1, 1, 1);                                              /* online: never a takeover, never an unpause request */
    CHECK(p.paused && !p.takeover && !at_pause_request_unpause(&p, 1));
    at_pause_on(&p, 0, 0, 0);                                              /* takeover not wanted (the default) */
    CHECK(!p.takeover);
    at_pause_on(&p, 1, 1, 0); CHECK(at_pause_request_unpause(&p, 0)); at_pause_off(&p);
    at_pause_on(&p, 1, 1, 0); CHECK(at_pause_take_unpause(&p) == -1);     /* a request never leaks into the next pause */
}
int main(void) { names_and_parse(); sources_and_online(); pause_machine(); ATLAS_DONE("atlas-retail"); }
```

Add to `native_test.sh` after the `atlas-binding` case:

```bash
atlas-retail)
    sources=(pc/tests/atlas_retail_test.c pc/platform/gw_ui_retail.c) ;;
```

and `atlas-retail` to the die message's list.
- [ ] **Step 2: Run it and see it fail.** `nt atlas-retail` -> a compile error (no `gw_ui_retail.h`).
- [ ] **Step 3: Implement** `gw_ui_retail.c`:

```c
/* gw_ui_retail.c - the retail element mask and the retail pause, as Atlas sees them (spec 6.8). Pure C. */
#include "gw_ui_retail.h"
#include <stdio.h>
#include <string.h>

static const char *const NAMES[AT_RE_COUNT] = { "hud.damage", "hud.stock", "hud.timer", "hud.nametag", "hud.magnify",
                                                "hud.coin", "hud.prize", "hud.hazard", "pause.panel" };
const char *at_retail_name(int id) { return (id >= 0 && id < AT_RE_COUNT) ? NAMES[id] : NULL; }

int at_retail_parse(const char *list, unsigned *mask, char *err, int cap)
{
    char word[32]; int n = 0, i; unsigned m = 0; const char *p = list ? list : "";
    for (;;) {
        char c = *p;
        if (c == ',' || c == ' ' || c == '\0') {
            if (n > 0) {
                word[n] = '\0';
                if (strcmp(word, "all") == 0) m = (1u << AT_RE_COUNT) - 1;
                else {
                    for (i = 0; i < AT_RE_COUNT && strcmp(word, NAMES[i]) != 0; i++) {}
                    if (i == AT_RE_COUNT) { snprintf(err, (size_t) cap, "unknown retail element \"%s\"", word); return 0; }
                    m |= 1u << i;
                }
                n = 0;
            }
            if (c == '\0') break;
        } else if (n < (int) sizeof word - 1) word[n++] = c;
        p++;
    }
    *mask = m;
    return 1;
}
unsigned at_retail_script_allowed(void) { return ((1u << AT_RE_COUNT) - 1) & ~(1u << AT_RE_HUD_TIMER); }
void at_retail_set(AtRetail *r, int source, unsigned mask) { if (source >= 0 && source < AT_RS_COUNT) r->src[source] = mask & ((1u << AT_RE_COUNT) - 1); }
unsigned at_retail_effective(const AtRetail *r, int online)
{
    unsigned m = 0; int i;
    if (online) return 0;
    for (i = 0; i < AT_RS_COUNT; i++) m |= r->src[i];
    return m;
}
int at_retail_hidden(const AtRetail *r, int id, int online) { return id >= 0 && id < AT_RE_COUNT && (at_retail_effective(r, online) >> id & 1u); }
void at_retail_release_script(AtRetail *r, int owner) { if (owner > 0 && r->script_owner == owner) { r->src[AT_RS_SCRIPT] = 0; r->script_owner = 0; } }

void at_pause_on(AtPause *p, int pauser, int takeover_wanted, int online)
{ p->paused = 1; p->pauser = pauser; p->takeover = takeover_wanted && !online; p->unpause_req = 0; }
void at_pause_off(AtPause *p) { p->paused = 0; p->pauser = -1; p->takeover = 0; p->unpause_req = 0; }
int at_pause_request_unpause(AtPause *p, int online)
{ if (!p->paused || online || p->unpause_req) return 0; p->unpause_req = 1; return 1; }
int at_pause_take_unpause(AtPause *p)
{ if (!p->paused || !p->unpause_req) return -1; p->unpause_req = 0; return p->pauser; }
```

and `gw_ui_retail.h` with the declarations from Interfaces (include `gw_ui_retail_ids.h`; the usual `extern "C"` guards as in `gw_ui_stack.h`).
- [ ] **Step 4: Run.** `nt atlas-retail | tail -1` -> `atlas-retail: N checks, 0 failed`.
- [ ] **Step 5: Commit.** Game repo: `git add pc/platform/gw_ui_retail* pc/tests/atlas_retail_test.c && git commit -m "atlas: retail element ids, the mask from four sources (empty by default, nothing online), the retail pause state"`. Workspace repo: `git commit -am "native_test: atlas-retail"`.

---

### Task 4: The guards and the pause notifications in the game side

One line per draw site, under `TARGET_PC`, calling unprefixed shims (`melee/CLAUDE.md` "The shim boundary": game code calls `X`, the host defines `gw_X`). The existing `Script_StatusHUDVisible` guard (`ifstatus.c:635, 657`; `ifstock.c:497-561`) is kept: the new check is ANDed after it.

**Files:**
- Modify (game repo): `src/melee/if/ifstatus.c`, `ifstock.c`, `iftime.c`, `ifnametag.c`, `ifmagnify.c`, `ifcoget.c`, `ifprize.c`, `ifhazard.c`, `src/melee/gm/gmpause.c`, `src/melee/gm/gmvs.c`
- Modify (game repo): `melee/pc/platform/gw_script_ui.inc` (the four shims' host definitions)

**Interfaces:**
Consumes: `AtRetail`, `AtPause` (Task 3).
Produces (host, `gw_` prefixed; game side calls them unprefixed):
`int gw_Ui_RetailHidden(int id)` (reads `at_retail_hidden(&gs_ui_retail, id, online)` with `online = gw_RB_Enabled() || gw_Netplay_Enabled()`), `void gw_Ui_RetailPause(int pauser, int on)`, `int gw_Ui_TakeUnpause(void)` (`at_pause_take_unpause`, -1 when none).

- [ ] **Step 1: Find the include form and every site.** How a game TU includes a `pc/platform` header: `grep -rn '#include .*platform/' src/melee | head -3` (use the same form for `gw_ui_retail_ids.h`; if no game TU does, write the numeric id with a comment naming the enum, e.g. `Ui_RetailHidden(0 /* AT_RE_HUD_DAMAGE */)`, and add a static assert in `atlas_retail_test.c` that pins the numbers). The sites: `grep -n "GObj_SetupGXLink\|JObjCallback" src/melee/if/ifnametag.c src/melee/if/ifmagnify.c src/melee/if/ifcoget.c src/melee/if/ifprize.c src/melee/if/ifhazard.c src/melee/if/iftime.c`. Write the list (file, line, callback) into the commit message. A file whose render goes through the generic `HSD_GObj_JObjCallback` gets a guarded wrapper (step 3).
- [ ] **Step 2: Damage and stocks.** In each guarded callback, extend the existing `TARGET_PC` block:

```c
#if defined(TARGET_PC)
    extern int Script_StatusHUDVisible(void);
    extern int Ui_RetailHidden(int id);
    if (!Script_StatusHUDVisible() || Ui_RetailHidden(AT_RE_HUD_DAMAGE)) return;
#endif
```

(`AT_RE_HUD_STOCK` in the five `ifstock.c` callbacks.) The procs `ifStatus_802F5B48` and `ifStatus_802F4EDC` are **not** touched.
- [ ] **Step 3: Timer and the generic callbacks.** `iftime.c:214, 258` pass `HSD_GObj_JObjCallback`. Add above `ifTime_UpdateCountdown`:

```c
#if defined(TARGET_PC)
static void ifTime_RenderGuarded(HSD_GObj* gobj, int pass)
{
    extern int Ui_RetailHidden(int id);
    if (Ui_RetailHidden(AT_RE_HUD_TIMER)) return;
    HSD_GObj_JObjCallback(gobj, pass);
}
#define IFTIME_RENDER ifTime_RenderGuarded
#else
#define IFTIME_RENDER HSD_GObj_JObjCallback
#endif
```

and use `IFTIME_RENDER` at the two `GObj_SetupGXLink` calls. Match the callback's real parameter types to `HSD_GObj_JObjCallback`'s declaration (`grep -rn "void HSD_GObj_JObjCallback" src`). Do the same, with a file-local wrapper, for name tags, magnify, coin, prize and hazard.
- [ ] **Step 4: The pause panel and the pause notifications.** In `gmpause.c` `gm_801A0FEC`, at the top:

```c
#if defined(TARGET_PC)
    { extern int Ui_RetailHidden(int id); if (Ui_RetailHidden(AT_RE_PAUSE_PANEL)) flag = 0; }   /* flag 0 hides the background itself */
#endif
```

In `gmvs.c` `gm_DoPauseChecksAndRoutine`, after `arg0->state.pauser = pauser;` (inside the existing `TARGET_PC` area or a new one): `{ extern void Ui_RetailPause(int pauser, int on); Ui_RetailPause(pauser, 1); }`. In `gm_DoUnpauseChecksAndRoutine`, after `gm_801A10FC(i);`: `Ui_RetailPause(i, 0);`. In `fn_8016CF4C` (match end from a pause, `gmvs.c:1351`), after `gm_801A10FC(slot);`: `Ui_RetailPause(slot, 0);`. Do **not** hook `gmcamera.c:270, 307`: those hide and re-show the panel around the pause camera while the game stays paused.

In `gm_GetPlayerPressingUnpause`, before the pad loop:

```c
#if defined(TARGET_PC)
    { extern int Ui_TakeUnpause(void); int req = Ui_TakeUnpause(); if (req >= 0) return req; }   /* the Atlas pause's Resume: offline only */
#endif
```

The request returns the pauser, so `i == arg0->state.pauser` holds and the retail unpause routine runs unchanged (audio, HUD, camera, the 10-frame unpause timer).
- [ ] **Step 5: The host shims.** In `gw_script_ui.inc` add `static AtRetail gs_ui_retail; static AtPause gs_ui_pause = {0, -1, 0, 0};` and:

```c
static int gs_ui_online(void) { return gw_RB_Enabled() || gw_Netplay_Enabled(); }
int gw_Ui_RetailHidden(int id) { return at_retail_hidden(&gs_ui_retail, id, gs_ui_online()); }
void gw_Ui_RetailPause(int pauser, int on) {
    if (on) at_pause_on(&gs_ui_pause, pauser, gs_ui_pause_wanted(), gs_ui_online());
    else at_pause_off(&gs_ui_pause);
    gs_ui_pause_changed = 1;                     /* the tick pushes or pops the pause screen (Task 8) */
}
int gw_Ui_TakeUnpause(void) { return gs_ui_online() ? -1 : at_pause_take_unpause(&gs_ui_pause); }
```

`gs_ui_pause_wanted()` returns `gw_Settings_Int("atlas_pause", 0) || env MELEE_ATLAS_PAUSE == "1"` (read the env once at first use). Add `gw_ui_retail.c` to the host sources the same way step 1 added `gw_ui_*.c` (grep `gw_ui_stack.c` in `tools/port/build.sh` or its source list; if the build globs `pc/platform/*.c`, nothing to add). Read `MELEE_ATLAS_RETAIL` once at the first `gw_Ui_RetailHidden` call into `AT_RS_ENV` (log `ui: retail elements hidden by MELEE_ATLAS_RETAIL: <names>` once, or the parse error).
- [ ] **Step 6: Syntax-check every touched game file as PowerPC.** From `$GW_MELEE`:

```bash
for f in src/melee/if/ifstatus.c src/melee/if/ifstock.c src/melee/if/iftime.c src/melee/if/ifnametag.c src/melee/if/ifmagnify.c \
         src/melee/if/ifcoget.c src/melee/if/ifprize.c src/melee/if/ifhazard.c src/melee/gm/gmpause.c src/melee/gm/gmvs.c; do
  clang --target=powerpc-unknown-eabi -fsyntax-only -DTARGET_PC -Isrc -Isrc/melee -Iinclude -Ipc "$f" && echo "ok $f"
done
```

The include flags must match what `build.sh` passes for game TUs: read them from `tools/port/build.sh` (grep `powerpc`) and use those. Expected: `ok` for all ten. Also with `TARGET_PC` undefined (drop `-DTARGET_PC`): the retail build is untouched.
- [ ] **Step 7: Guard greps (both must print nothing).**

```bash
grep -n "Ui_RetailHidden" src/melee/if/ifstatus.c | grep -v "Script_StatusHUDVisible() ||"   # every damage guard keeps the old check first
grep -rn "Ui_Retail\|Ui_TakeUnpause" src/melee | grep -v "extern\|TARGET_PC" | grep -v "if (\|Ui_RetailPause(\|req = Ui_TakeUnpause\|flag = 0\|return;" 
```

- [ ] **Step 8: Build and confirm in the exe** (no window): `tools/port/build.sh` in `$MAIN` with the lane exports, then `grep -a "retail elements hidden by MELEE_ATLAS_RETAIL" "$GW_BUILD_ROOT/melee-pc.exe" | head -1` prints a line.
- [ ] **Step 9: Commit (game repo).** `git commit -am "retail takeover: one guard per HUD draw site and the pause panel, pause on/off notifications, the unpause request (all inert with the mask empty)"`

---

### Task 5: New parts: offer card, port card, strip, banner, toast, link

**Files:**
- Modify (game repo): `melee/pc/platform/gw_ui_parts.h`, `gw_ui_parts.c`, `melee/pc/tests/atlas_parts_test.c`

**Interfaces:**

```c
typedef struct { int model, ring; char name[AT_STR]; char rule[AT_TEXT]; char tag[24]; int tag_tone; unsigned rgba; char letter; } AtOffer;
void  at_part_offer(const AtSink *s, const AtTextOps *o, AtRect r, const AtOffer *c, int state, unsigned focus_rgba);
      /* an offer card: model well (or a keystone stone with its letter when model < 0 and letter != 0), name (a_cap16),
       * one rule (a_body12, at most 2 lines), a bottom tag. 5 px chamfers; focus: lift, ember edge, four brackets */
typedef struct { int port; char name[AT_STR]; int percent, stocks, cpu; } AtPortCard;
void  at_part_port_card(const AtSink *s, const AtTextOps *o, AtRect r, const AtPortCard *c);   /* 3 px top edge in the port colour */
typedef struct { int n_pips; unsigned pip_fill[8], pip_ring[8]; int n_keys; char key_letter[8]; unsigned key_rgba[8]; char wait[24]; } AtStrip;
void  at_part_strip(const AtSink *s, const AtTextOps *o, AtRect r, const AtStrip *st);          /* slot pips, keystone stones, "n waiting" */
void  at_part_banner(const AtSink *s, const AtTextOps *o, AtRect r, char btn, const char *text, float progress);  /* progress <0: none */
void  at_part_toast(const AtSink *s, const AtTextOps *o, AtRect r, unsigned emblem_rgba, const char *title, const char *rule, float remaining);
void  at_part_link(const AtSink *s, float x0, float y0, float x1, float y1, float th, unsigned rgba);  /* a flat quad along a segment */
float at_part_offer_min_h(void);  /* the smallest card that keeps the 12 px floor: model 48 + name + 2 rule lines + tag */
```

Sizes: offer card 5 px chamfer, 3 px front edge; port card 5 px; strip has no plate (pips 12x12 squares with a 2 px rarity ring, keystones 14x16 arch stones, 4 px gaps); banner 5 px chamfer, 34 px tall, the glyph drawn with `at_part_hint`; toast 5 px chamfer, 22 px emblem square, title `a_cap14`, rule `a_body12` one line, the drain rule along the bottom (the step 1 note's timer rule); link 2 px thick.

- [ ] **Step 1: Write the failing tests** (append to `atlas_parts_test.c`; `r` values chosen so 640 is tight):

```c
static AtOffer offer_fixture(void)
{
    AtOffer c; memset(&c, 0, sizeof c);
    c.model = 7; c.ring = 9; c.rgba = 0xF07474FFu;
    snprintf(c.name, sizeof c.name, "%s", "Lingering Burning Red Drive of the Long Name");
    snprintf(c.rule, sizeof c.rule, "%s", "Aerial hits set Burning for 3 s and Burning targets take 12% more damage from you.");
    snprintf(c.tag, sizeof c.tag, "%s", "+ MERGE");
    return c;
}
static void offer_card_style(void)
{
    AtSink s = rec_sink(); AtOffer c = offer_fixture();
    AtRect r = { 40.0f, 120.0f, 168.0f, 196.0f };                    /* three cards across the 640 primary */
    REC.np = REC.nt = REC.nm = 0;
    at_part_offer(&s, &FAKE_OPS, r, &c, AT_ST_REST, AT_C_P1);
    CHECK(no_focus_cues());
    CHECK(corners_clear(r, 5.0f));
    CHECK(texts_inside((AtRect){ r.x + 8.0f, r.y, r.w - 16.0f, r.h }));
    CHECK(texts_legible());
    CHECK(REC.nm == 1);                                               /* the model, once */
    REC.np = REC.nt = REC.nm = 0;
    at_part_offer(&s, &FAKE_OPS, r, &c, AT_ST_FOCUS, AT_C_P2);
    CHECK(focus_cues_at(r, 1) == 3);
    CHECK(count_color(AT_C_P2) == 8);                                 /* brackets take the seat's colour */
    c.model = -1; c.letter = 'P';                                     /* a keystone offer: an arch stone with its letter */
    REC.np = REC.nt = REC.nm = 0;
    at_part_offer(&s, &FAKE_OPS, r, &c, AT_ST_REST, AT_C_P1);
    CHECK(REC.nm == 0 && find_text("P") != NULL && corners_clear(r, 5.0f));
}
static void hud_parts_never_focus(void)
{
    AtSink s = rec_sink(); AtPortCard pc = { 2, "FALCO", 147, 3, 0 }; AtStrip st; int i;
    AtRect r = { 420.0f, 16.0f, 188.0f, 44.0f };
    memset(&st, 0, sizeof st); st.n_pips = 6; st.n_keys = 7;
    for (i = 0; i < 6; i++) { st.pip_fill[i] = 0xF07474FFu; st.pip_ring[i] = AT_C_SUN; }
    for (i = 0; i < 7; i++) { st.key_letter[i] = (char) ('A' + i); st.key_rgba[i] = 0xB872F0FFu; }
    snprintf(st.wait, sizeof st.wait, "%s", "2 waiting");
    REC.np = REC.nt = 0; at_part_port_card(&s, &FAKE_OPS, r, &pc);
    CHECK(no_focus_cues() && corners_clear(r, 5.0f) && texts_inside(r) && count_color(AT_C_P2) >= 1);
    REC.np = REC.nt = 0; at_part_strip(&s, &FAKE_OPS, (AtRect){ 24.0f, 16.0f, 240.0f, 20.0f }, &st);
    CHECK(no_focus_cues() && texts_inside((AtRect){ 24.0f, 16.0f, 240.0f, 20.0f }));
    CHECK(find_text("+1") != NULL);                                    /* six stones, then +n */
    REC.np = REC.nt = 0; at_part_banner(&s, &FAKE_OPS, (AtRect){ 170.0f, 150.0f, 300.0f, 34.0f }, 'A', "Collect the drives", -1.0f);
    CHECK(no_focus_cues() && corners_clear((AtRect){ 170.0f, 150.0f, 300.0f, 34.0f }, 5.0f) && texts_inside((AtRect){ 170.0f, 150.0f, 300.0f, 34.0f }));
    CHECK(count_color(AT_C_PAD_A) >= 1);                               /* the A glyph: press A to collect */
    REC.np = REC.nt = 0; at_part_toast(&s, &FAKE_OPS, (AtRect){ 400.0f, 16.0f, 216.0f, 44.0f }, 0xB872F0FFu,
                                       "SKYWARD ASSEMBLED", "Your aerials gain Haste for 2 s and chain Burning onward.", 0.5f);
    CHECK(no_focus_cues() && corners_clear((AtRect){ 400.0f, 16.0f, 216.0f, 44.0f }, 5.0f) && texts_inside((AtRect){ 400.0f, 16.0f, 216.0f, 44.0f }));
    CHECK(REC.nt == 2);                                                /* one title, one rule line: never more */
}
static void link_is_flat(void)
{
    AtSink s = rec_sink();
    REC.np = 0; at_part_link(&s, 10.0f, 10.0f, 110.0f, 60.0f, 2.0f, AT_C_JADE);
    CHECK(REC.np == 1 && REC.p[0].rgba == AT_C_JADE);
    REC.np = 0; at_part_link(&s, 10.0f, 10.0f, 10.0f, 10.0f, 2.0f, AT_C_JADE);
    CHECK(REC.np == 0);                                                /* a zero-length link draws nothing */
}
```

Call the three from `main`. (`FAKE_OPS` is the fixed-width text ops step 1's tests use; use the name `atlas_fake.h` gives it.)
- [ ] **Step 2: Run and see it fail.** `nt atlas-parts` -> undefined `at_part_offer` (compile error).
- [ ] **Step 3: Implement** the six parts in `gw_ui_parts.c`, built from the existing helpers (`at_plate`, `fit_text`, `at_wrap`, `brackets`, `glyph_*`, `at_part_hint`, `at_part_stone`'s arch geometry). The rules the tests pin, written as the implementation's comments:
  - Every plate is `at_plate(s, r, face, edge, 3, 5)`; nothing else may place a vertex in the cut corners, so tags and emblems are inset by the chamfer (`x >= r.x + 5` on the top-left, `x + w <= r.x + r.w - 5` on the bottom-right rows).
  - Text is drawn only through `fit_text` (single line) or `at_wrap` into at most the stated lines, with `max_w` = the box's inner width.
  - `at_part_offer` focus: `face = AT_C_LIFT`, `r.y - 2`, edge `AT_C_EMBER`, `brackets(s, r, focus_rgba)`; rest: `AT_C_PLATE`, edge `AT_C_EDGE`; disabled: `AT_C_PLATE2` and the name in `AT_C_DIM`.
  - `at_part_strip` draws at most six stones, then the text `+n` (`a_num12`) for the rest; pips are squares (identity: fill = drive colour, ring = rarity), keystones are arch stones with a letter (identity differs by shape, not only colour).
  - `at_part_toast` draws the emblem square, the title (`a_cap14`), one rule line (`a_body12`, fitted, never wrapped), and the drain rule (`remaining` of the width) inside the bottom edge.
  - `at_part_link` is one quad: the segment's normal times `th / 2` on both sides.
- [ ] **Step 4: Run.** `nt atlas-parts | tail -1` -> `0 failed`.
- [ ] **Step 5: Commit (game repo).** `git commit -am "atlas parts: offer card, port card, build strip, banner, toast, link (chamfers clear, three cues on the card, no cue on HUD parts, text inside)"`

---

### Task 6: The HUD zones, keep-outs, stacking and caps (pure C)

**Files:**
- Create (game repo): `melee/pc/platform/gw_ui_hud.h`, `gw_ui_hud.c`, `melee/pc/tests/atlas_hud_test.c`
- Modify (workspace repo): `tools/port/native_test.sh` (`atlas-hud`)

**Interfaces:**

```c
/* gw_ui_hud.h - the in-match HUD layer (spec 6.8 part 3). Pure C. Never takes focus, never records a hit. */
enum { AT_Z_TOP_LEFT, AT_Z_TOP_CENTER, AT_Z_TOP_RIGHT, AT_Z_BOTTOM_LEFT, AT_Z_BOTTOM_CENTER, AT_Z_BOTTOM_RIGHT, AT_Z_COUNT };
enum { AT_HP_PORT_CARD = 1, AT_HP_TIMER, AT_HP_NOTE, AT_HP_STRIP, AT_HP_BANNER, AT_HP_TOAST, AT_HP_CARD };
#define AT_HUD_PER_ZONE 4
#define AT_HUD_KEEPOUTS 12
#define AT_HUD_QUAD_CAP 768
typedef struct {
    int kind; AtPortCard port; AtStrip strip;
    char text[AT_STR]; char rule[AT_TEXT]; char btn; float progress; unsigned rgba;
    char lines[3][AT_STR]; int n_lines;          /* AT_HP_CARD: the opponent card: a title and up to 3 short lines */
    int seconds;                                  /* AT_HP_TIMER */
    double from_ms, until_ms;                     /* AT_HP_TOAST / AT_HP_NOTE: shown on the UI clock; 0 = always */
} AtHudPart;
typedef struct { char id[AT_ID * 2]; int owner; AtHudPart z[AT_Z_COUNT][AT_HUD_PER_ZONE]; int n[AT_Z_COUNT]; } AtHud;
typedef struct { AtRect r[AT_HUD_KEEPOUTS]; int n; } AtKeepOut;
typedef struct { AtRect rect[AT_Z_COUNT][AT_HUD_PER_ZONE]; int shown[AT_Z_COUNT][AT_HUD_PER_ZONE]; int dropped; } AtHudLayout;

AtRect at_hud_safe(float canvas_w);                              /* the title-safe box: content area, 16 px top and bottom */
void   at_hud_retail_keepouts(float canvas_w, unsigned visible_mask, AtKeepOut *k);   /* the retail HUD's rectangles that are still visible */
int    at_hud_cap_ok(const AtHud *h, char *why, int cap);       /* the quiet-HUD caps */
void   at_hud_layout(const AtHud *h, float canvas_w, const AtKeepOut *k, double now_ms, const AtTextOps *o, AtHudLayout *out);
void   at_hud_render(const AtHud *h, const AtHudLayout *l, double now_ms, int reduced, const AtTextOps *o, const AtSink *s, int *entries);
```

**The quiet-HUD caps** (`at_hud_cap_ok`; spec 4.5 and the Envoy rulings): at most one `BANNER` in the whole HUD, and only in `TOP_CENTER`; at most one `TOAST` per zone (a new toast replaces the old one in the binding, never queues); at most three `CARD`s; at most one `NOTE`; `TOAST` only in a top zone. A HUD that breaks a cap is refused whole with the reason.

**Keep-outs [estimate; measured in Task 21 step 4]:** the retail HUD is drawn in the 4:3 band centred on the canvas (`ox = (canvas_w - 640) / 2`). Damage plates: `{ox + 40, 372, 560, 96}` (four plates across the bottom; one rectangle); stocks sit above the plates inside the same rectangle; timer: `{ox + 248, 16, 144, 52}`. `at_hud_retail_keepouts` adds each rectangle only when its element is visible (not in the mask), so a hidden element frees its space. If Task 21 measures different numbers, change these constants and the test's expected values together.

**Stacking:** top zones stack downward from the safe box's top, bottom zones upward from its bottom, 8 px apart; left zones are left-aligned, right zones right-aligned, centre zones centred. A part whose rectangle meets a keep-out moves past it (down in a top zone, up in a bottom zone, keeping its alignment); a part that would leave the safe box or cross the canvas's middle line (`y = 240`) is not shown and counted in `dropped`. A toast or note past `until_ms` is not shown and takes no space.

- [ ] **Step 1: Write the failing test** `atlas_hud_test.c`:

```c
#include "atlas_check.h"
#include "atlas_fake.h"
#include "atlas_rec.h"
#include "../platform/gw_ui_hud.h"

static const float WIDTHS[3] = { 640.0f, 853.0f, 1140.0f };
static int meets(AtRect a, AtRect b) { return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h; }
static AtHud envoy_fixture(void)                   /* what Envoy's HUD holds at its busiest legal moment */
{
    AtHud h; int i; memset(&h, 0, sizeof h);
    snprintf(h.id, sizeof h.id, "%s", "envoy.hud");
    h.z[AT_Z_TOP_LEFT][0].kind = AT_HP_STRIP; h.z[AT_Z_TOP_LEFT][0].strip.n_pips = 6; h.z[AT_Z_TOP_LEFT][0].strip.n_keys = 3; h.n[AT_Z_TOP_LEFT] = 1;
    h.z[AT_Z_TOP_RIGHT][0].kind = AT_HP_TOAST; snprintf(h.z[AT_Z_TOP_RIGHT][0].text, AT_STR, "SKYWARD ASSEMBLED");
    snprintf(h.z[AT_Z_TOP_RIGHT][0].rule, AT_TEXT, "Your aerials gain Haste for 2 s."); h.z[AT_Z_TOP_RIGHT][0].until_ms = 5000.0;
    for (i = 1; i <= 3; i++) { h.z[AT_Z_TOP_RIGHT][i].kind = AT_HP_CARD; snprintf(h.z[AT_Z_TOP_RIGHT][i].text, AT_STR, "MARTH  CPU %d", i);
        snprintf(h.z[AT_Z_TOP_RIGHT][i].lines[0], AT_STR, "Pyromancer: All your attacks become fire."); h.z[AT_Z_TOP_RIGHT][i].n_lines = 1; }
    h.n[AT_Z_TOP_RIGHT] = 4;
    h.z[AT_Z_TOP_CENTER][0].kind = AT_HP_BANNER; h.z[AT_Z_TOP_CENTER][0].btn = 'A'; h.z[AT_Z_TOP_CENTER][0].progress = -1.0f;
    snprintf(h.z[AT_Z_TOP_CENTER][0].text, AT_STR, "Collect the drives"); h.n[AT_Z_TOP_CENTER] = 1;
    h.z[AT_Z_BOTTOM_LEFT][0].kind = AT_HP_NOTE; snprintf(h.z[AT_Z_BOTTOM_LEFT][0].text, AT_STR, "Merged: Lingering got stronger");
    h.z[AT_Z_BOTTOM_LEFT][0].until_ms = 5000.0; h.n[AT_Z_BOTTOM_LEFT] = 1;
    return h;
}
static void keepout_and_safe(void)
{
    int w, z, i, k;
    for (w = 0; w < 3; w++) {
        AtHud h = envoy_fixture(); AtKeepOut ko; AtHudLayout l; AtRect safe = at_hud_safe(WIDTHS[w]);
        at_hud_retail_keepouts(WIDTHS[w], 0xFFFFFFFFu, &ko);                   /* every retail element visible */
        CHECK(ko.n == 2);
        at_hud_layout(&h, WIDTHS[w], &ko, 1000.0, &FAKE_OPS, &l);
        for (z = 0; z < AT_Z_COUNT; z++) for (i = 0; i < h.n[z]; i++) {
            AtRect r = l.rect[z][i];
            if (!l.shown[z][i]) continue;
            CHECK(r.x >= safe.x - 0.01f && r.x + r.w <= safe.x + safe.w + 0.01f && r.y >= safe.y - 0.01f && r.y + r.h <= safe.y + safe.h + 0.01f);
            for (k = 0; k < ko.n; k++) CHECK(!meets(r, ko.r[k]));            /* never over the retail percent or the timer */
        }
        CHECK(l.shown[AT_Z_TOP_CENTER][0]);                                    /* the banner moved below the timer, not dropped */
        CHECK(l.rect[AT_Z_TOP_CENTER][0].y >= ko.r[1].y + ko.r[1].h);
    }
}
static void hidden_element_frees_space(void)
{
    AtKeepOut ko;
    at_hud_retail_keepouts(640.0f, ~(1u << AT_RE_HUD_TIMER), &ko);            /* the timer is masked */
    CHECK(ko.n == 1);
}
static void caps(void)
{
    AtHud h = envoy_fixture(); char why[96];
    CHECK(at_hud_cap_ok(&h, why, sizeof why));
    h.z[AT_Z_TOP_LEFT][1].kind = AT_HP_BANNER; h.n[AT_Z_TOP_LEFT] = 2;
    CHECK(!at_hud_cap_ok(&h, why, sizeof why) && strstr(why, "banner") != NULL);
    h = envoy_fixture(); h.z[AT_Z_BOTTOM_RIGHT][0].kind = AT_HP_TOAST; h.n[AT_Z_BOTTOM_RIGHT] = 1;
    CHECK(!at_hud_cap_ok(&h, why, sizeof why));                                /* a toast lives in a top corner */
    h = envoy_fixture(); h.z[AT_Z_TOP_LEFT][1].kind = AT_HP_CARD; h.n[AT_Z_TOP_LEFT] = 2;
    CHECK(!at_hud_cap_ok(&h, why, sizeof why) && strstr(why, "three") != NULL);   /* a fourth opponent card */
}
static void expiry_and_render_style(void)
{
    int w;
    for (w = 0; w < 3; w++) {
        AtHud h = envoy_fixture(); AtKeepOut ko; AtHudLayout l; AtSink s = rec_sink(); int entries = 0;
        at_hud_retail_keepouts(WIDTHS[w], 0xFFFFFFFFu, &ko);
        at_hud_layout(&h, WIDTHS[w], &ko, 6000.0, &FAKE_OPS, &l);              /* past the toast's and the note's until_ms */
        CHECK(!l.shown[AT_Z_TOP_RIGHT][0] && !l.shown[AT_Z_BOTTOM_LEFT][0]);
        CHECK(l.rect[AT_Z_TOP_RIGHT][1].y <= at_hud_safe(WIDTHS[w]).y + 0.01f);   /* the cards move up into the free space */
        REC.np = REC.nt = REC.nm = 0;
        at_hud_render(&h, &l, 6000.0, 0, &FAKE_OPS, &s, &entries);
        CHECK(no_focus_cues() && texts_legible() && entries <= AT_HUD_QUAD_CAP);
    }
}
int main(void) { keepout_and_safe(); hidden_element_frees_space(); caps(); expiry_and_render_style(); ATLAS_DONE("atlas-hud"); }
```

`native_test.sh`:

```bash
atlas-hud)
    sources=(pc/tests/atlas_hud_test.c pc/platform/gw_ui_hud.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c) ;;
```

- [ ] **Step 2: Run and see it fail** (`nt atlas-hud`: no header).
- [ ] **Step 3: Implement** `gw_ui_hud.c`: `at_hud_safe` from `at_layout(canvas_w, AT_PRESET_NONE, &L)` (`x = L.content_x + 16`, `w = L.content_w - 32`, `y = 16`, `h = 448`); part sizes (strip 20 tall, toast 44, card `26 + 17 x lines`, banner 34 and 300 wide or the safe width, note 24, port card 44 x 188, timer 28 x 96); the stacking rule above; `at_hud_render` calls the Task 5 parts through a counting wrapper that stops forwarding at `AT_HUD_QUAD_CAP` (copy the step 1 renderer's wrapper pattern: grep `capped` in `gw_ui_render.c`). Toast and note fade in over `AT_MS_NOTE` (a cut when `reduced`); the drain rule is `(until_ms - now) / (until_ms - from_ms)`.
- [ ] **Step 4: Run.** `nt atlas-hud | tail -1` -> `0 failed`; `nt atlas-parts | tail -1` still `0 failed`.
- [ ] **Step 5: Commit.** Game repo: `git add pc/platform/gw_ui_hud.* pc/tests/atlas_hud_test.c && git commit -m "atlas: the HUD layer: zones in the title-safe box, retail keep-outs, stacking, quiet-HUD caps, expiry"`. Workspace repo: `git commit -am "native_test: atlas-hud"`.

---

### Task 7: `gd.ui.hud`, `gd.ui.toast`, `gd.ui.retail_hide`, `gd.ui.retail` and the HUD draw pass

**Files:**
- Modify (game repo): `melee/pc/platform/gw_script_ui.inc`, `melee/pc/platform/gw_script.c` (the draw call, the release, the scene-change release, the console command), `melee/pc/tests/atlas_binding_test.c`, `atlas_ui_stub.lua`, `atlas_ui_stub_test.lua`

**Interfaces:**
Lua (all presentation; the first four allowed online):
- `gd.ui.hud{ id = "mod.hud", zones = { top_left = { {kind="strip", pips={{fill=, ring=}...}, keys={{letter=, rgba=}...}, wait=} }, top_center = { {kind="banner", text=, button="A", progress=} }, top_right = { {kind="card", title=, lines={...}} }, bottom_left = {...} } }` registers or replaces the caller's HUD (one per script; the id must start with the mod id). Kinds: `strip`, `banner`, `card`, `note` (`text`, `seconds`), `port_card` (`port`; percent, stocks and name are read by the host at draw time), `timer` (`seconds`). Raises with the cap reason (`gd.ui.hud: ...`) when `at_hud_cap_ok` refuses it.
- `gd.ui.hud_clear([id])`.
- `gd.ui.toast{ zone = "top_left" | "top_right", title =, text =, rgba =, seconds = }` puts a toast in the caller's HUD (replacing that zone's toast; 0.5 to 15 s, 4 by default). Independent of the screen stack (step 1's `note` stays a screen note).
- `gd.ui.retail_hide{ "hud.damage", ... }` (offline, a gameplay mod script, an active match; ids from `at_retail_script_allowed`) claims the script source; `gd.ui.retail_hide{}` releases it. Raises `gd.ui.retail_hide: online` online, `... belongs to another script`, `... hud.timer may not be hidden by a mod`.
- `gd.ui.retail()` -> `{ hidden = {"hud.damage", ...}, paused = bool, pauser = n|nil, takeover = bool }`.
Host: `gs_ui_hud_draw()` called from `gs_finish_draw` **before** `gs_ui_draw()` (the HUD sits under any screen); `gs_ui_release(script)` also clears that script's HUD and `at_retail_release_script`; the existing scene-change path that restores `gd.hud_visible` also clears the script source and every HUD's toasts and notes. Console: `atlas retail <ids|clear>` (source `AT_RS_CONSOLE`), `atlas hud` (logs every HUD's parts and their arranged rectangles), `atlas keepout on|off` (draws the keep-out rectangles as 1 px rose outlines, for Task 21).

- [ ] **Step 1: Write the failing binding tests, on the real path** (as script 0, `envoy/main`, and through `gs_ui_tick`):

```c
static void hud_basics(void)
{
    CHECK(run_as_script(0,
        "assert(gd.ui.hud{id='envoy.hud', zones={top_left={{kind='strip', pips={{fill=0xF07474FF, ring=0xF2C14EFF}}, keys={{letter='P', rgba=0xB872F0FF}}}},"
        " top_center={{kind='banner', text='Collect the drives', button='A'}}}})") == 0);
    CHECK(run_as_script(0, "assert(not pcall(gd.ui.hud, {id='other.hud', zones={}}))") == 0);          /* id must start with the mod */
    CHECK(run_as_script(0, "assert(not pcall(gd.ui.hud, {id='envoy.hud', zones={top_left={{kind='banner', text='x'}}, top_center={{kind='banner', text='y'}}}}))") == 0);
    g_quads = 0; gs_ui_hud_draw();
    CHECK(g_quads > 0);                                                       /* drawn with no screen open */
    g_may_run = 0; g_quads = 0; gs_ui_hud_draw();                             /* a resimulated frame: the draw needs no Lua and still draws */
    CHECK(g_quads > 0); g_may_run = 1;
    CHECK(run_as_script(0, "assert(gd.ui.toast{zone='top_right', title='SKYWARD ASSEMBLED', text='Aerials gain Haste.'})") == 0);
    CHECK(run_as_script(0, "assert(gd.ui.toast{zone='top_right', title='SECOND', text='Replaces the first.'})") == 0);
    CHECK(hud_toasts_in_zone(0, AT_Z_TOP_RIGHT) == 1);
    CHECK(run_as_script(0, "assert(not pcall(gd.ui.toast, {zone='bottom_left', title='x', text='y'}))") == 0);
}
static void retail_mask_ownership(void)
{
    g_match_active = 1; g_online = 0;
    CHECK(run_as_script(0, "assert(gd.ui.retail_hide{'hud.damage'}); local r=gd.ui.retail(); assert(r.hidden[1]=='hud.damage')") == 0);
    CHECK(gw_Ui_RetailHidden(AT_RE_HUD_DAMAGE));
    CHECK(run_as_script(1, "assert(not pcall(gd.ui.retail_hide, {'hud.stock'}))") == 0);                   /* another script */
    CHECK(run_as_script(0, "assert(not pcall(gd.ui.retail_hide, {'hud.timer'}))") == 0);                   /* never the clock */
    g_online = 1; CHECK(!gw_Ui_RetailHidden(AT_RE_HUD_DAMAGE));                                         /* online: shown */
    CHECK(run_as_script(0, "assert(not pcall(gd.ui.retail_hide, {'hud.damage'}))") == 0); g_online = 0;
    gs_ui_release(0);                                                                                   /* unload */
    CHECK(!gw_Ui_RetailHidden(AT_RE_HUD_DAMAGE) && hud_count() == 0);
    CHECK(run_as_script(0, "assert(gd.ui.retail_hide{'hud.stock'})") == 0);
    gs_ui_scene_changed();                                                                              /* a scene change releases it too */
    CHECK(!gw_Ui_RetailHidden(AT_RE_HUD_STOCK));
    g_match_active = 0;
    CHECK(run_as_script(0, "assert(not pcall(gd.ui.retail_hide, {'hud.stock'}))") == 0);               /* no match: refused */
}
static void console_is_not_the_test(void)
{
    /* the same calls as the console must not be the only passing path: the console has no mod id, so a console hud is refused */
    CHECK(run_as_console("assert(not pcall(gd.ui.hud, {id='envoy.hud', zones={}}))") == 0);
}
```

The stand-ins this needs in the test file: `g_match_active`, `g_online` (feeding `gs.match_active`, `gw_RB_Enabled`, `gw_Netplay_Enabled`), `gs_ui_scene_changed()` (the function the binding exposes for `gw_script.c`'s scene path), `hud_toasts_in_zone`, `hud_count` (read the binding's HUD table).
- [ ] **Step 2: Run and see it fail.**
- [ ] **Step 3: Implement** in `gw_script_ui.inc`: `static AtHud gs_ui_hud[4];` (one per script, at most 4 scripts with a HUD; a fifth raises `gd.ui.hud: too many HUDs (4)`), the converter from the Lua table to `AtHud` (raw reads, as step 1's `gs_ui_copy`; strings cut to their fields; colours as integers), `l_ui_hud`, `l_ui_hud_clear`, `l_ui_toast` (sets `from_ms = gs_now_ms()`, `until_ms`), `l_ui_retail_hide` (checks in this order: online, console or no gameplay script, no match, another owner, an id not allowed; then `at_retail_set(&gs_ui_retail, AT_RS_SCRIPT, m)` and `script_owner = gs.cur + 1`, or 0 for `{}`), `l_ui_retail`. The draw:

```c
/* the HUD layer: every script's HUD, under the screen stack, every rendered frame. Never calls Lua. */
static void gs_ui_hud_draw(void) {
    int i, entries;
    double now = gs_now_ms();
    float w;
    AtKeepOut ko; AtHudLayout l; AtTextOps ops; AtSink sink;
    if (!gs_ui_roles_ok() || !gs.match_active) return;
    w = gw_Console_ScriptWidth();
    at_hud_retail_keepouts(w, ~at_retail_effective(&gs_ui_retail, gs_ui_online()), &ko);
    ops.width = gs_ui_width; ops.user = NULL;
    sink.user = NULL; sink.poly = gs_ui_poly; sink.text = gs_ui_text; sink.model = gs_ui_model_draw;
    for (i = 0; i < 4; i++) {
        AtHud *h = &gs_ui_hud[i];
        if (h->owner <= 0 || !gs_ui_usable(h->owner - 1)) continue;
        if (gw_Kit_QuadRoom() < AT_HUD_QUAD_CAP) { gs_ui_hud_warn_once(h, "not drawn: the kit quad list is nearly full"); continue; }
        gs_ui_hud_fill_ports(h);              /* port_card: percent, stocks, name from the fighter readbacks gd.player uses */
        at_hud_layout(h, w, &ko, now, &ops, &l);
        if (l.dropped) gs_ui_hud_warn_once(h, "a part did not fit and is not shown");
        entries = 0;
        at_hud_render(h, &l, now, gs_ui_reduced, &ops, &sink, &entries);
    }
    gw_Kit_SetTracking(0.0f);
}
```

`gs_ui_hud_fill_ports` uses the same calls `l_player` uses (`gw_ScriptGame_FighterF(slot, SF_PERCENT)`, `gw_ScriptGame_FighterI(slot, SI_STOCKS)`; grep `"percent"` in `gw_script.c:1417`) and skips a port with no fighter. In `gw_script.c`: call `gs_ui_hud_draw()` on the line before `gs_ui_draw()` in `gs_finish_draw` (`gw_script.c:7613`); call `gs_ui_scene_changed()` where the scene change restores `gs_hud_owner` (grep `gs_hud_release_owner` and the scene hook that clears it); `gs_ui_release` clears the script's HUD and calls `at_retail_release_script`. Register the console command `atlas` with the three subcommands.
- [ ] **Step 4: The stand-in follows.** `atlas_ui_stub.lua`: `Stub.hud`, `Stub.hud_clear`, `Stub.toast`, `Stub.retail_hide`, `Stub.retail` with the same refusals and caps (`Stub.hud_caps` mirrors `at_hud_cap_ok`: one banner and only top_center, one toast per top zone, three cards, one note); `Stub.netplay = true` makes `retail_hide` raise. Tests in `atlas_ui_stub_test.lua` for each refusal.
- [ ] **Step 5: Guard greps (nothing printed).** `grep -n "gs_ui_call\|lua_" melee/pc/platform/gw_script_ui.inc | sed -n '/gs_ui_hud_draw/,/^}/p'` (the HUD draw calls no Lua); `grep -n "input_mask\|input_chord" melee/pc/platform/gw_script_ui.inc`.
- [ ] **Step 6: Run.** `nt atlas-binding | tail -1`, `lua pc/tests/atlas_ui_stub_test.lua | tail -1`.
- [ ] **Step 7: Commit (game repo).** `git commit -am "gd.ui.hud, toast, retail_hide, retail: the HUD layer under the stack, owned and released with the script, nothing hidden online"`

---

### Task 8: The pause description and the pause takeover (off by default)

**Files:**
- Modify (game repo): `melee/pc/platform/gw_ui_screen.c` (`kind = "pause"`), `gw_script_ui.inc` (the takeover in `gs_ui_tick`, `gd.ui.unpause`, `gd.ui.pause_screen`), `atlas_binding_test.c`, `atlas_screen_test.c`, the stub and its test

**Interfaces:**
- A description may say `kind = "pause"` (a `list` primary only; `gd.ui.screen` raises otherwise). A pause screen is offline-only: `gd.ui.open` of a pause screen online returns `false`.
- `gd.ui.pause_screen(id | nil)`: the caller's screen to push when a retail pause starts **and** the takeover is on (`AtPause.takeover`). One per script; the latest call wins; `nil` clears. When the retail pause starts with a takeover wanted, the tick pushes the most recently named pause screen whose owner is usable, with `port = pauser + 1`; when it ends, the tick pops it. With the takeover off nothing is pushed: retail's pause shows as today.
- `gd.ui.unpause()` -> `true` when the request was accepted (`at_pause_request_unpause`): paused, offline, none pending. The pause screen's Resume row calls it; the game side takes it on its next unpause check (Task 4).
- Follow-up (step 2 dependency): when U6 exists, entries registered under parent `pause` are appended to the pushed pause screen's rows. Not built here.

- [ ] **Step 1: Write the failing tests.** `atlas_screen_test.c`: a `kind="pause"` with a grid primary is refused with `gd.ui.screen: a pause screen has a list primary`; with a list it converts and `AtScreen.pause == 1`. `atlas_binding_test.c` (real path):

```c
static void pause_takeover(void)
{
    CHECK(run_as_script(0, "assert(gd.ui.screen{id='envoy.pause', kind='pause', trail={title='PAUSED'}, primary={kind='list', items="
                           "{{id='resume', label='Resume'}}}, on={accept=function(c) if c=='resume' then gd.ui.unpause() end end}});"
                           "gd.ui.pause_screen('envoy.pause')") == 0);
    g_pause_wanted = 0; gw_Ui_RetailPause(1, 1); gs_ui_tick();
    CHECK(at_stack_top(&gs_ui_stack) < 0);                                    /* takeover off (the default): nothing pushed */
    gw_Ui_RetailPause(1, 0); gs_ui_tick();
    g_pause_wanted = 1; gw_Ui_RetailPause(1, 1); gs_ui_tick();
    CHECK(at_stack_top(&gs_ui_stack) == screen_slot("envoy.pause") && gs_ui_slot[screen_slot("envoy.pause")].sc.port == 2);
    g_pad = AT_PAD_A; gs_ui_tick(); g_pad = 0; gs_ui_tick();                 /* the pauser presses A on Resume */
    CHECK(gw_Ui_TakeUnpause() == 1 && gw_Ui_TakeUnpause() == -1);            /* one-shot */
    gw_Ui_RetailPause(1, 0); gs_ui_tick();
    CHECK(at_stack_top(&gs_ui_stack) < 0);                                    /* popped when retail unpaused */
    g_online = 1; gw_Ui_RetailPause(1, 1); gs_ui_tick();
    CHECK(at_stack_top(&gs_ui_stack) < 0 && gw_Ui_TakeUnpause() == -1);      /* never online */
    gw_Ui_RetailPause(1, 0); g_online = 0; g_pause_wanted = 0;
    CHECK(run_as_script(0, "assert(gd.ui.unpause() == false)") == 0);         /* not paused */
}
```

`g_pad` feeds `gw_script_pad_raw_buttons` for the pauser's channel: check that the binding reads the pad of `sc.port` (step 1 reads `u->sc.port`; if the stand-in ignores the channel, make it honour it so this test proves the right port is read).
- [ ] **Step 2: Run and see it fail.**
- [ ] **Step 3: Implement.** `AtScreen` gains `int pause;` (set from `kind`). At the very start of `gs_ui_tick`, before its `if (top < 0) return;` (with an empty stack the push must still happen) and before the `gs_may_run` check (a push is presentation; the screen's handlers still never run on a resimulated frame):

```c
if (gs_ui_pause_changed) {
    gs_ui_pause_changed = 0;
    if (gs_ui_pause.paused && gs_ui_pause.takeover && gs_ui_pause_slot >= 0 && gs_ui_slot[gs_ui_pause_slot].used
        && gs_ui_usable(gs_ui_slot[gs_ui_pause_slot].owner)) {
        gs_ui_slot[gs_ui_pause_slot].sc.port = gs_ui_pause.pauser + 1;
        gs_ui_open_screen(gs_ui_pause_slot);
        gs_ui_pause_pushed = gs_ui_pause_slot;
    } else if (!gs_ui_pause.paused && gs_ui_pause_pushed >= 0) {
        if (at_stack_top(&gs_ui_stack) == gs_ui_pause_pushed) gs_ui_close_screen(gs_ui_pause_pushed);
        else at_stack_remove(&gs_ui_stack, gs_ui_pause_pushed);
        gs_ui_pause_pushed = -1;
    }
}
```

`l_ui_pause_screen` stores the slot (only the caller's own screen with `pause == 1`), `l_ui_unpause` returns `at_pause_request_unpause(&gs_ui_pause, gs_ui_online())`. `gs_ui_release` clears `gs_ui_pause_slot` and `gs_ui_pause_pushed` when they belong to the released script. `l_ui_open` of a pause screen online returns `false`.
- [ ] **Step 4: Stub follows** (`Stub.pause_screen`, `Stub.unpause`, `Stub.retail_pause(port, on)` as the test driver).
- [ ] **Step 5: Run.** `nt atlas-screen`, `nt atlas-binding`, the stub test.
- [ ] **Step 6: Commit (game repo).** `git commit -am "gd.ui pause screens: kind=pause, pushed on a retail pause only when the takeover is on, Resume through a one-shot unpause request; never online"`

---

### Task 9: The `cards` primary, grid links and the countdown

**Files:**
- Modify (game repo): `gw_ui_screen.h/.c`, `gw_ui_render.c`, `atlas_screen_test.c`, `atlas_render_test.c`, the stub and its test

**Interfaces:**
- `primary = { kind = "cards", cards = { {id, model?, ring?, letter?, rgba?, name, rule, tag?, tag_tone?, disabled?}, ... } }`: 1 to `AT_MAX_CARDS 4` cards in one row; focus moves left and right (wraps); A accepts the focused card. A card's `rule` is **one** rule (the Envoy ruling); the explainer still shows WHAT/WITH/FROM for the focused card.
- On a `grid`: `links = { {a = "eq:2", b = "bag:1", rgba = 0x...}, ... }` (at most `AT_MAX_LINKS 16`): drawn as `at_part_link` between the two cells' centres **before** the cells (so cells cover the line's ends), 2 px. A link naming a missing cell is skipped and logged once at registration.
- `countdown = seconds` on any screen: shown at the trail's right end as `0:45` (`a_num14`) and turns `AT_C_ROSE` under 10 s. The script updates it by re-registering once a second (the screen stays O(1) per frame).
Record: `AtScreen` gains `AtOffer cards[AT_MAX_CARDS]; int n_cards; struct { char a[AT_ID], b[AT_ID]; unsigned rgba; } links[AT_MAX_LINKS]; int n_links; int countdown;` and `AT_PRIMARY_CARDS = 3`.

- [ ] **Step 1: Failing tests.** `atlas_screen_test.c`: a five-card description is refused (`gd.ui.screen: at most 4 cards`); focus on cards moves right and wraps; A on a disabled card does not accept (`at_cell_accepts`). `atlas_render_test.c` at 640, 853, 1140 with the longest real strings (use `offer_fixture` names: three drive cards and a keystone card):

```c
static void cards_screen(void)
{
    int w;
    for (w = 0; w < 3; w++) {
        AtHits hits; AtRenderInfo info; AtSink s = rec_sink(); AtLayout L;
        cards_fixture();                                          /* three drive offers, focus on card 2, countdown 8 */
        REC.np = REC.nt = REC.nm = 0;
        at_render_ex(&SC, &VIEW, WIDTHS[w], 1000.0, 0, &FAKE_OPS, &s, &hits, &info);
        at_layout(WIDTHS[w], SC.preset, &L);
        CHECK(texts_legible() && !info.capped && info.entries < AT_SCREEN_QUAD_WARN);
        CHECK(texts_inside(L.canvas));
        CHECK(hits_count(AT_HIT_CELL) == 3);                       /* each card is clickable */
        CHECK(card_rects_inside(L.primary));                       /* three cards fit the primary at 640 */
        CHECK(find_text("0:08") != NULL && find_text_color("0:08") == AT_C_ROSE);
        CHECK(focus_cues_at(card_rect(1), 1) == 3);
    }
}
static void links_under_cells(void)
{
    AtHits hits; AtSink s = rec_sink();
    bag_fixture(); add_link("eq:1", "bag:2", AT_C_JADE);
    REC.np = 0;
    at_render(&SC, &VIEW, 640.0f, 1000.0, 0, &FAKE_OPS, &s, &hits);
    CHECK(first_index_of(AT_C_JADE) < first_cell_plate_index());   /* drawn before the cells */
}
```

(`cards_fixture`, `card_rect`, `card_rects_inside`, `hits_count`, `find_text_color`, `add_link`, `first_index_of`, `first_cell_plate_index` are small helpers in the test file next to step 1's `bag_fixture`.)
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement** the converter (cards: required `id`, `name`, `rule`; one block named `"cards"` for focus purposes so `gd.ui.focus` returns `card_id, "cards"`), `at_screen_focus_blocks` returns one block of `n_cards` with `cols = n_cards`, the render branch (cards share the primary width: `card_w = min(200, (primary.w - 12 x (n - 1)) / n)`, height `max(at_part_offer_min_h(), primary.h - 24)`, centred), the links pass, the countdown in the trail.
- [ ] **Step 4: Stub follows** (cards conversion and limits; links validation; countdown).
- [ ] **Step 5: Run** `nt atlas-screen`, `nt atlas-render`, `nt atlas-parts`, the stub test.
- [ ] **Step 6: Commit (game repo).** `git commit -am "gd.ui: cards primary (one rule per card), grid links drawn under the cells, the countdown"`

---

### Task 10: Envoy shared description helpers and the reward screen

**Files:**
- Create: `envoy/scripts/atlas_kit.lua`, `envoy/scripts/atlas_reward.lua`, `melee/pc/tests/envoy_atlas_screens.lua`
- Modify: `envoy/scripts/atlas_bag.lua` (use `atlas_kit`), `envoy/scripts/run_screen.lua` (attach in `S:open` for `mode=='reward'`, detach in `S:close`), `tools/port/envoy_bundle.py` (`atlas_kit`, `atlas_reward` before `run_screen` in `ENVOY_MODULES`)

**Interfaces:**
`atlas_kit.lua` returns `K` with `K.id(base, S)` (seat suffix as `atlas_bag.lua` `A.id_for`), `K.parents()` -> `{"SOLO","ENVOY"}` (deleted when step 2's entry supplies them), `K.log_once(S, text)`, `K.rules(lines)` and `K.page(state, cid, n, dir)` (the bag's one-rule paging, moved verbatim from `atlas_bag.lua`), `K.enabled(g)` (gd.ui present and available, and not `envoy ui legacy`).
`atlas_reward.lua` returns `R` with `R.describe(S, self)`, `R.attach(S)`, `R.detach(S)`: the reward screen (`envoy.reward`, or `envoy.keystone` when the offers are keystones) is a `cards` primary built from `S.host.offers` / `S.host.key_offers` (the same records `run_screen.lua` `S:build_main` reads), the explainer WHAT (the card's focused rule, paged with Z / L / R), WITH (what it merges into or the slot it goes to: the existing `S:plan_line`), FROM (the drive's family tag); keys `A Take`, `X To bag` (only when the bag has room), `Z More` (only when the card has more than one rule), `B Skip` / `Continue`; the countdown from `S:seconds_left()`; the trail title `STAGE CLEAR` and, when present, the milestone line as the counter (`S.host.milestone_line`). The swap layout is not handled here (Task 11).

- [ ] **Step 1: Write the failing tests** `envoy_atlas_screens.lua` (Stub plus the real `RunScreen` with a host fixture, as `envoy_run_ux.lua` builds one; reuse its fixture builder through `envoy_testlib.lua`):

```lua
-- Offline tests of Envoy's Atlas screens:  cd melee && lua pc/tests/envoy_atlas_screens.lua
local prefix = io.open('pc/tests/atlas_ui_stub.lua') and '' or 'melee/'
local Stub = dofile(prefix .. 'pc/tests/atlas_ui_stub.lua')
local T = dofile(prefix .. 'pc/tests/envoy_testlib.lua')
local run = T.runner('envoy_atlas_screens')

run('reward is a cards screen with one rule per card', function()
  local g = Stub.new{ mod = 'envoy' }; local S = T.run_screen(g, { offers = 3 })
  S:open('reward')
  local d = Stub.top(g)
  assert(d.id == 'envoy.reward' and d.primary.kind == 'cards' and #d.primary.cards == 3)
  for _, c in ipairs(d.primary.cards) do assert(not c.rule:find('\n') and #c.rule <= 159, 'one short rule: ' .. c.rule) end
  assert(d.parents[1] == 'SOLO' and d.parents[2] == 'ENVOY')
  assert(Stub.key_label(g, 'A') == 'Take' and Stub.key_label(g, 'B') == 'Skip')
end)

run('countdown takes the first offer, never discards', function()
  local g = Stub.new{ mod = 'envoy' }; local S = T.run_screen(g, { offers = 3, bag_full = true, free_slot = false })
  S:open('reward'); T.advance_seconds(S, 46)
  local h = S.host
  assert(#h.offers == 0 and h.last_outcome ~= 'discard', 'the first offer was kept: ' .. tostring(h.last_outcome))
  assert(Stub.top(g) == nil or Stub.top(g).id ~= 'envoy.reward')
end)

run('closing resolves every offer', function()
  local g = Stub.new{ mod = 'envoy' }; local S = T.run_screen(g, { offers = 3 })
  S:open('reward'); Stub.press(g, 'B'); Stub.press(g, 'B')        -- skip asks, a second B skips
  assert(#S.host.offers == 0 and S.host.skipped == 3)
end)

run('Z pages the rules of a card with several', function()
  local g = Stub.new{ mod = 'envoy' }; local S = T.run_screen(g, { offers = 1, rules_per_offer = 3 })
  S:open('reward')
  assert(Stub.explainer(g).kicker:find('RULE 1 OF 3'))
  Stub.press(g, 'Z'); assert(Stub.explainer(g).kicker:find('RULE 2 OF 3'))
end)

run('keystone offers are stones with a letter', function()
  local g = Stub.new{ mod = 'envoy' }; local S = T.run_screen(g, { key_offers = 3 })
  S:open('reward')
  local d = Stub.top(g)
  assert(d.id == 'envoy.keystone')
  for _, c in ipairs(d.primary.cards) do assert(c.model == nil and #c.letter == 1) end
end)

run('a seat tints its focus', function()
  local g = Stub.new{ mod = 'envoy' }; local S = T.run_screen(g, { offers = 3, seat = 2 })
  S:open('reward'); assert(Stub.top(g).port == 2 and Stub.top(g).id == 'envoy.reward.p2')
end)

run('netplay: described, never masked', function()
  local g = Stub.new{ mod = 'envoy', netplay = true }; local S = T.run_screen(g, { offers = 3 })
  S:open('reward'); assert(Stub.top(g).id == 'envoy.reward' and g.mask_calls == 0)
end)

run:done()
```

Add any missing fixture options (`bag_full`, `free_slot`, `rules_per_offer`, `seat`, `key_offers`) to `envoy_testlib.lua` next to the existing run-screen fixture; `T.advance_seconds` drives `S:seconds_left()` through the fixture's clock.
- [ ] **Step 2: Run and see it fail.** `cd "$GW_MELEE" && lua pc/tests/envoy_atlas_screens.lua | tail -3`.
- [ ] **Step 3: Implement** `atlas_kit.lua` (move the helpers out of `atlas_bag.lua` unchanged; `atlas_bag.lua` then calls `K.*`; run `lua pc/tests/envoy_atlas_bag.lua` to prove the move changed nothing) and `atlas_reward.lua` following `atlas_bag.lua`'s attach pattern: wrap `S.press`, `S.refresh`, `S.notify` (notes go to `gd.ui.note` on the reward screen), feed directions with `g.ui.feed`, run A/X/B through the legacy `S:press` so every outcome (merge, equip, bag, choose, countdown) stays the run's tested logic. On `refresh`, if `S.layout == 'swap'` hand over to `atlas_swap.lua` (Task 11) instead of detaching to the legacy grid. Re-register once a second for the countdown (compare `math.ceil(S:seconds_left())` with the last value).
- [ ] **Step 4: Wire.** `run_screen.lua` `S:open`: after the existing `atlas_bag` line, `if mode=='reward' and D.atlas_reward and D.atlas_kit.enabled(self.g) then D.atlas_reward.attach(self) end`; `S:close`: `if self.atlas_reward then D.atlas_reward.detach(self) end`. Add both modules to `ENVOY_MODULES`, then `python tools/port/envoy_bundle.py` (in `$WS`, writing into `$GW_MELEE`'s `main.lua`; check the script's `--melee` or `GW_MELEE` handling first).
- [ ] **Step 5: Run.** `lua pc/tests/envoy_atlas_screens.lua`, `lua pc/tests/envoy_atlas_bag.lua`, `lua pc/tests/envoy_run_ux.lua` (baseline count), `python tools/port/envoy_bundle.py --check`.
- [ ] **Step 6: Commit.** Game repo: `git add pc/scripts/examples/envoy/scripts/atlas_kit.lua pc/scripts/examples/envoy/scripts/atlas_reward.lua pc/scripts/examples/envoy/scripts/atlas_bag.lua pc/scripts/examples/envoy/scripts/run_screen.lua pc/scripts/examples/envoy/scripts/main.lua pc/tests/envoy_atlas_screens.lua pc/tests/envoy_testlib.lua && git commit -m "envoy atlas: the reward screen as cards (one rule per card, countdown, keystone stones), shared helpers"`. Workspace repo: `git commit -am "envoy_bundle: atlas_kit, atlas_reward"`.

---

### Task 11: The swap screen ("BAG FULL" / "SWAP")

**Files:**
- Create: `envoy/scripts/atlas_swap.lua`
- Modify: `atlas_bag.lua` and `atlas_reward.lua` (hand the swap layout here), `envoy_atlas_screens.lua`, `envoy_bundle.py`

**Interfaces:** `W.attach(S)`, `W.detach(S)`: `envoy.swap` (seat-suffixed), a `grid` built from `S:build_swap()` (the incoming drive is the footer `AtFooter`: `label = "INCOMING"`, `model_a` = its model; the six equipped and four bag cells are the targets); the explainer says what A does to the focused target (the legacy `S:detail_lines` "Replaces ...; it goes to your bag" or "it is gone"); keys `A Replace`, `B Leave it` (from `decide`) or `B Back`; grid `links` from `synergy_fx` (`D.synergy_fx.current:grid_links(...)`; read its `m.links` model, `synergy_fx.lua:294-304`, and map `a.k`/`b.k` to cell ids) so link marks keep their place now that the grid is native.

- [ ] **Step 1: Failing tests** (append to `envoy_atlas_screens.lua`): `swap opens from a full bag and returns focus` (gain a drive into a full bag with no free slot -> top is `envoy.swap`; B returns to the bag or reward screen with the focus where it was: the legacy `back_focus` rule); `B twice leaves the drive behind and logs it`; `the explainer names the outcome before A` (the focused equipped cell's explainer contains "goes to your bag" when the bag has room, "is gone" when not); `links: synergy marks are grid links` (a fixture with two linked pieces gives one `links` entry naming both cells).
- [ ] **Step 2: Run, see them fail. Step 3: Implement** (the attach pattern again; `S.refresh` on `layout ~= 'swap'` returns to the screen that handed over). **Step 4: Run** the three Envoy suites and the bundle check. **Step 5: Commit** (`envoy atlas: the swap screen; synergy link marks as grid links`).

---

### Task 12: The setup screen

**Files:**
- Create: `envoy/scripts/atlas_setup.lua`
- Modify: `envoy/scripts/retail_app.lua` (attach where the app shows `setup`), `envoy_atlas_screens.lua`, `envoy_bundle.py`; `envoy/mod.json` only per step 6

**Interfaces:** `envoy.setup`, a `list`: `Begin` (label `Begin Classic as Fox`, built from `menu.run_type` and `menu.fighter`), `Mode` (choice: Classic, Adventure, and Co-op only when `c.coop_available`), `Fighter` (choice over the app's fighter list, including listed Geno fighters with their labels), `Difficulty` (choice 1..5 or the app's range; read `C.tuning.retail`), `Stocks` (choice 1..5); explainer per row (one rule: "Classic: twelve retail stages, a drive pick every third." etc., taken from the existing notices); keys `A Begin` on Begin, `Left/Right Change` on a choice, `B Back`. On `change` it writes `menu.run_type`, `menu.fighter`, `menu.difficulty`, `menu.stocks` (the same fields the legacy setup rows set) and re-registers; `accept` on Begin calls the app's existing start path (`self:start_retail(...)` or `start_coop`), so refusals keep their notices (shown as a screen note).

- [ ] **Step 1: Failing tests:** `setup lists the live choices only` (no Companion, Records or garden rows: parked); `changing a choice writes the menu field` (Mode -> Adventure sets `menu.run_type`); `Begin starts through the app's start path` (a stubbed `start_retail` records its arguments); `a refused start shows the reason as a note and stays`; `co-op appears only when available`.
- [ ] **Step 2: Run, see them fail. Step 3: Implement.** Attach in `retail_app.lua` wherever it calls `self.menu:show('setup')` (four places, `retail_app.lua:18, 92, 102` and the refusals): one helper `self:show_setup()` that shows the legacy setup when `D.atlas_kit.enabled` is false and opens `envoy.setup` otherwise.
- [ ] **Step 4: Run** the suites and the bundle check.
- [ ] **Step 5: Commit** (`envoy atlas: the setup screen (live choices only)`).
- [ ] **Step 6: Step 2 dependency.** If step 2's manifest `menus` parser is merged (`grep -n '"menus"' "$GW_MELEE/pc/platform/gw_mods.c"` or wherever step 2 put it), add to `envoy/mod.json`: `"menus": [{ "id": "envoy", "parent": "solo", "label": "ENVOY", "blurb": "Explore, fight and evolve your build.", "after": "training", "opens": "envoy.setup", "online": false }]` and a test that the registry lists it; delete `K.parents()`'s use in `atlas_setup.lua`. If not merged, write in the hand-off: "Envoy's `menus` line waits for step 2's parser".

---

### Task 13: Pause, confirm and quit

**Files:**
- Create: `envoy/scripts/atlas_pause.lua`
- Modify: `envoy/scripts/retail_app.lua` / `app.lua` (where the app shows `pause`, `confirm`, `quit`), `envoy_atlas_screens.lua`, `envoy_bundle.py`

**Interfaces:** `envoy.pause`, `kind = "pause"`, a `list`: `Resume`, `Bag` (opens the bag screen; only in a rules-on run), `Controls`, `Quit run`; explainer one line per row; keys `A Select`, `B Resume`. **Lifecycle unchanged:** Envoy's own START route opens it and the app's `sync_pause` keeps owning `gd.pause`/`gd.resume` (`app.lua:224-231`); Resume runs the app's `resume` effect. `Controls` opens a `gd.ui.dialog` listing Envoy's buttons in one line each (`Z + START  Bag`, `A  Collect a drive`, `Hold Z + Down  Leave the stage`). `Quit run` opens a `gd.ui.dialog` ("Quit the run? Your build is lost." `A Quit`, `B Keep playing`) whose `A` runs the app's existing abandon effect. The script also calls `gd.ui.pause_screen('envoy.pause')`, so when the owner turns the takeover on (`MELEE_ATLAS_PAUSE=1`) a retail pause in an Envoy run shows this list; with the takeover off (default), a retail pause looks as today.

- [ ] **Step 1: Failing tests:** `pause lists Resume, Bag, Controls, Quit run` (Bag absent when rules are off); `B resumes through the app's resume effect`; `Quit asks once in a dialog; A abandons, B returns`; `pause_screen is named` (`Stub.pause_target(g) == 'envoy.pause'`); `online: the pause screen is never opened` (Stub `netplay = true`: `S:open` returns false and the legacy no-pause path runs, as today: Envoy does not pause online).
- [ ] **Step 2: Run, see them fail. Step 3: Implement** (attach where `menu:show('pause')`, `show('confirm')` and `show('quit')` are called: `retail_app.lua:189`, `menu.lua:46` via the app's effect handler). **Step 4: Run. Step 5: Commit** (`envoy atlas: pause list, controls and quit dialogs; named as the pause takeover's screen`).

Note for the hand-off: how Envoy's START pause and the retail pause interact today (whether `gd.pause` stops `gm_DoPauseChecksAndRoutine` from seeing START) is **unverified**; Task 21 step 6 checks it with the takeover off and on.

---

### Task 14: Results

**Files:** Create `envoy/scripts/atlas_results.lua`; modify `retail_app.lua` (where `self.menu:results(...)` is called: `retail_app.lua:198, 241, 296`), `envoy_atlas_screens.lua`, `envoy_bundle.py`.

**Interfaces:** `envoy.results`, a `list` of read-only text rows built from `self.retail.results` (outcome, stages cleared, the build's final drives as one row each with their one rule in the explainer), counter `NG+n` when looping; keys `A Continue` / `B Leave`. **The retail results rule is kept:** while the retail results scene is up (`self.results_up`), START belongs to the game and this screen does not open (`retail_app.lua:201-204`); it opens after.

**Interlude** (the campaign's between-room screen, `app.lua:105`) belongs to the parked campaign flow: it is **not ported** (the parked-screens decision, spec 13.3) and loses its wiring in Task 18.

- [ ] **Step 1: Failing tests:** `results show after the retail results, never over them`; `each final drive is one row with one rule`; `A continues to NG+ when looping, B leaves Envoy` (the app's existing effects). **Step 2-5:** run, implement, run, commit (`envoy atlas: results`).

---

### Task 15: The online reward pick

**Files:** Create `envoy/scripts/atlas_netpick.lua`; modify `envoy/scripts/mod_lab.lua` (`L:net_sync`, `L:net_draw`, `mod_lab.lua:740-770`), `envoy_atlas_screens.lua`, `envoy_bundle.py`.

**Interfaces:** `envoy.netpick`, a `cards` primary of the three offers plus a fourth card `Keep my build` (`letter = "K"`), the countdown from `env.left / 60`, the trail `ENVOY REWARD  GAME n`. Input stays `feed` from `menu_input` (which never masks online, `menu_input.lua:7-9`); A runs `g.netplay_act('rpick', index)`, B `('rpick', 3)`; the auto-pick test hook (`envoynet auto`) still works. The screen is non-modal (it never calls `gd.pause` or a mask). It closes when `env.picks[seat] >= 0` or `env.open` ends.

- [ ] **Step 1: Failing tests** (Stub `netplay = true`): `the pick is four cards with the countdown`; `A sends rpick with the card index, B sends 3`; `never masked, never paused` (`g.mask_calls == 0 and g.pause_calls == 0`); `closes when the pick is in`. **Step 2-5:** run, implement (`L:net_draw` returns early when the Atlas screen is up; the legacy box stays for `envoy ui legacy`), run (also `lua pc/tests/envoy_online.lua`), commit (`envoy atlas: the online reward pick as cards, non-modal`).

---

### Task 16: Envoy's HUD on `gd.ui.hud`

**Files:**
- Create: `envoy/scripts/atlas_hud.lua`, `melee/pc/tests/envoy_atlas_hud.lua`
- Modify: `envoy/scripts/run_hud.lua` (when Atlas is enabled, `Hd:draw()` returns early and `Hd:frame()`/`announce`/`corner`/`show_card` also feed `atlas_hud`), `envoy/scripts/run_host.lua` (`H:draw_hold`: the banner text moves to the HUD; the floor arrow over the nearest drive stays as world-space `gd.kit` drawing), `envoy/scripts/foe_lab.lua` (`F:draw_cards` feeds HUD cards), `envoy/scripts/coop.lua` (each seat's strip in its own top corner), `envoy_bundle.py`

**Interfaces:** `atlas_hud.lua` returns `U` with `U.sync(host)` (rebuilds the description only when `Hd:model()`'s key, the toast, the cards or the banner change: never per frame) and `U.clear(host)`. What it describes (one HUD per Envoy script, id `envoy.hud`):
- `top_left` (seat 1) / `top_right` (seat 2 in co-op): the strip (`pips` from `Hd:model().pips`, `keys` letters and family colours, `wait` = `n waiting` only while drives wait). No strength figure, no depth text (developer only, as today).
- `top_right`: the synergy toast through `gd.ui.toast{ zone = 'top_right', title = '<ARCHETYPE> ASSEMBLED', text = <its one-line blurb>, rgba = <emblem colour>, seconds = 4 }` (from `Hd:corner`); below it, the opponent cards (at most three: `title` = fighter name, `lines` = keystone name and its one rule; no strength).
- `top_center`: one banner at most: `Collect the drives` with `button = 'A'` while `H.holding_end and H.hold_banner`; during the payout, the same banner with the text `Hold Z + Down to leave` and `progress = leave_w:progress()`.
- `bottom_left`: the pickup note (one line: `Merged: Lingering got stronger`, `Drive to slot 2`, `Bag full: choose a drive`), 4 s.
- The out-of-bounds notice (`Hd:flash(text, true)`) becomes a `note`.
- **Gone:** the starter announcement's centred panel: the starter drive and keystone are shown once as a toast in the seat's top corner (title `RUN START`, text the drive's one rule); the crit pop-up has no path at all (there is no HUD part for a crit; the test pins it); developer flashes stay developer-only through `Hd.dev_ui()` and draw with the legacy code.
- **Stays:** the world-space link flashes and emblem pops (`synergy_fx.lua` `F:chain_fired`, `:204-230`) and the floor arrow; they are not HUD.

- [ ] **Step 1: Failing tests** `envoy_atlas_hud.lua`:

```lua
local prefix = io.open('pc/tests/atlas_ui_stub.lua') and '' or 'melee/'
local Stub = dofile(prefix .. 'pc/tests/atlas_ui_stub.lua')
local T = dofile(prefix .. 'pc/tests/envoy_testlib.lua')
local run = T.runner('envoy_atlas_hud')

run('quiet HUD caps hold at the busiest moment', function()
  local g = Stub.new{ mod = 'envoy' }; local h = T.run_host(g, { foes = 5, holding = true })
  h.hud:corner({ { text = 'Skyward assembled' } }, 'skyward'); h.hud:show_card('Merged!', { 'Lingering got stronger' })
  T.tick(h, 1)
  local d = Stub.hud(g, 'envoy.hud')
  assert(Stub.hud_caps_ok(d))                                     -- one banner, one toast per corner, three cards, one note
  assert(#Stub.hud_parts(d, 'card') == 3)
end)

run('the collect banner carries the A glyph; the payout banner its progress', function()
  local g = Stub.new{ mod = 'envoy' }; local h = T.run_host(g, { holding = true })
  T.tick(h, 1); local b = Stub.hud_parts(Stub.hud(g, 'envoy.hud'), 'banner')[1]
  assert(b.text == 'Collect the drives' and b.button == 'A')
  h.paying = true; T.tick(h, 1); b = Stub.hud_parts(Stub.hud(g, 'envoy.hud'), 'banner')[1]
  assert(b.text:find('leave') and type(b.progress) == 'number')
end)

run('no crit text, ever', function()
  local g = Stub.new{ mod = 'envoy' }; local h = T.run_host(g, {})
  T.crit(h, { multiplier = 1.5 }); T.tick(h, 30)
  for _, p in ipairs(Stub.hud_all_text(g)) do assert(not p:lower():find('crit'), p) end
end)

run('link flashes still fire', function()
  local g = Stub.new{ mod = 'envoy' }; local h = T.run_host(g, { synergy = true })
  T.chain(h); assert(#h.mods.synergy_fx.flashes >= 1)             -- world-space, untouched by the HUD move
end)

run('the synergy notice is a small top-corner toast', function()
  local g = Stub.new{ mod = 'envoy' }; local h = T.run_host(g, {})
  h.hud:corner({ { text = 'Skyward assembled' }, { text = 'Your aerials gain Haste.' } }, 'skyward'); T.tick(h, 1)
  local t = Stub.toast(g, 'top_right'); assert(t and t.title:find('ASSEMBLED') and not t.text:find('\n'))
  assert(#Stub.hud_parts(Stub.hud(g, 'envoy.hud'), 'banner') == 0)
end)

run('co-op seats use their own corners', function()
  local g = Stub.new{ mod = 'envoy' }; local c = T.coop(g)
  T.tick(c, 1); local d = Stub.hud(g, 'envoy.hud')
  assert(#Stub.hud_parts_in(d, 'top_left', 'strip') == 1 and #Stub.hud_parts_in(d, 'top_right', 'strip') == 1)
end)

run('hud stays clear of the retail HUD', function()     -- the description only uses zones; the engine places them (Task 6 pins geometry)
  local g = Stub.new{ mod = 'envoy' }; local h = T.run_host(g, {})
  T.tick(h, 1); for _, z in ipairs(Stub.hud_zones(Stub.hud(g, 'envoy.hud'))) do assert(z ~= 'bottom_center') end
end)

run('rebuilt only on change', function()
  local g = Stub.new{ mod = 'envoy' }; local h = T.run_host(g, {})
  T.tick(h, 1); local n = g.hud_calls; T.tick(h, 120); assert(g.hud_calls == n)
end)

run('netplay: the HUD draws, nothing is hidden', function()
  local g = Stub.new{ mod = 'envoy', netplay = true }; local h = T.run_host(g, {})
  T.tick(h, 1); assert(Stub.hud(g, 'envoy.hud') ~= nil and g.retail_hide_calls == 0)
end)

run:done()
```

Fixture helpers (`T.run_host`, `T.tick`, `T.crit`, `T.chain`, `T.coop`) extend `envoy_testlib.lua`; build them from what `envoy_hud.lua`, `envoy_synergy_fx.lua` and `envoy_coop.lua` already construct.
- [ ] **Step 2: Run and see it fail.**
- [ ] **Step 3: Implement** `atlas_hud.lua` and the hooks. Envoy never calls `gd.ui.retail_hide` (step 3's first users hide nothing retail).
- [ ] **Step 4: Run** `envoy_atlas_hud.lua`, `envoy_hud.lua`, `envoy_synergy_fx.lua`, `envoy_coop.lua`, `envoy_run_ux.lua` (baselines), the bundle check.
- [ ] **Step 5: Commit** (`envoy atlas: the match HUD on gd.ui.hud: strip, synergy toast, opponent cards, collect and payout banners, pickup note; no crit text; link flashes untouched`).

---

### Task 17: One seat's screen at a time, and the screen count

**Files:** Modify `atlas_kit.lua`, `atlas_bag.lua`; `envoy_atlas_screens.lua`.

**Interfaces:** `K.may_open(S)` -> `false, 'Player N has a screen open'` when the stack's top is another seat's Envoy screen (`gd.ui.state().top` ends in `.pN` for another N, or is the unsuffixed id while this seat is not port 1); the bag's attach then shows `gd.ui.toast{ zone = <the seat's corner>, title = 'BAG', text = 'Player N has a screen open' }` and does not open. `K.forget_all(g)` on run end forgets every Envoy screen id (Task 1's `forget`).

- [ ] **Step 1: Failing tests:** `seat 2's bag waits while seat 1's reward is up`; `envoy registers at most nine screens and frees them at run end` (count `Stub.screens(g)` after a co-op run that opened every screen: at most 9 live; after the run ends: 0).
- [ ] **Step 2-5:** run, implement, run, commit (`envoy atlas: one seat's screen at a time; screens forgotten at run end`).

---

### Task 18: Make Atlas Envoy's default, then retire the legacy screens (after the owner's look)

**This task is in two parts. Part A runs now; Part B runs only after the owner has looked (Task 21) and said yes, in a later session.**

**Part A (now).**
- [ ] **Step 1:** `atlas_kit.lua` `K.enabled` defaults to on; the console `envoy ui legacy on|off` switches every Envoy screen and the HUD back to the legacy code for the look (replacing `uxatlas`, which becomes an alias that logs "use envoy ui legacy"). Test: `legacy switch restores the grid` in `envoy_atlas_screens.lua`. Commit.

**Part B (after the look; a separate commit per bullet, each followed by every Envoy suite and the bundle check).**
- [ ] Remove `run_screen.lua`'s grid use (`S:new_view`, `S:icon`, `S:sync`, `S:draw`), `grid` from `ENVOY_MODULES` and the embedded `D.grid` with its `embed.py` flow (grep `embed.py` and `D.grid` in `tools/port/envoy_bundle.py` and the envoy scripts). The grid demo `demos/grid-inventory` stays only if it is moved to `gd.ui` (a separate request; otherwise leave it untouched as a demo).
- [ ] Remove `drive_menu.lua` (step 1's deferred retirement) and its bundle entry, after replacing `foe_lab.lua`'s use of `D.drive_menu.wrap` (`foe_lab.lua:131`) with `at_wrap` through the HUD card (Task 16 already does) or `gd.kit` text fit.
- [ ] `menu.lua`, `menu_draw.lua`: remove the replaced screens (`setup`, `pause`, `confirm`, `quit`, `reward`, `results`) and the **parked screens' wiring** (`title`, `profile`, `hub`, `fighter`, `companion`, `records`, `interlude`): their rows, their draw code and the app's `show(...)` calls. **Keep their logic** (`companion.lua`, `hub.lua`, `campaign.lua`, `save.lua`, records in `save.lua`, the app's run and garden code) and their console diagnostics (`envoy hub`, `menudump`, `dump`, `status`, `reset-profile confirm`) where they do not need a screen. `menu_input.lua` stays (it is the screens' pad reader).
- [ ] `hud.lua`: remove the duplicate companion panel and tag panel (audit #24, #25); keep `H.stat_view` if `classic.lua` or a test uses it (grep).
- [ ] The Modifier LAB text box and the Drive LAB card stay developer-only behind `envoy devui` (no change; check `Hd.dev_ui()` gates both).
- [ ] `envoy/MENUS.md`: replace the grid contract at the top with the Atlas contract (each screen, its keys, the HUD zones), and mark the parked contract "parked: logic kept, no screens".

---

### Task 19: Demo mods: `atlas-hud` and `atlas-pause`

**Files:** Create `melee/pc/scripts/examples/demos/atlas-hud/` (`mod.json`, `main.lua`, `README.md`) and `demos/atlas-pause/` (same). Follow `demos/atlas-screen/` (step 1) for form.

- `atlas-hud`: one HUD with a port card per human port, a timer, a strip, a banner and a toast on F7; F8 cycles `gd.ui.retail_hide` through `{}`, `{'hud.damage'}`, `{'hud.stock'}`, `{'hud.damage','hud.stock'}` and logs each; the README says what each step should look like and that online nothing is hidden.
- `atlas-pause`: registers `kind="pause"` with Resume and a Log row, names it with `gd.ui.pause_screen`; the README says to run with `MELEE_ATLAS_PAUSE=1` and what changes; without it, nothing does.
- [ ] **Step 1:** `luac -p` both `main.lua` files. **Step 2:** a stub test each (`lua pc/tests/atlas_ui_stub_test.lua` loads them through the stub, as step 1 did for `atlas-screen`, if that pattern exists; else a three-line loader in the stub test). **Step 3:** Commit (`demos: atlas-hud (zones, keep-outs, the mask) and atlas-pause (the takeover)`).

---

### Task 20: Documentation

**Files:** `docs/scripting.md` (workspace repo): in "Atlas screens (`gd.ui`)", add rows for `forget`, `hud`, `hud_clear`, `toast`, `retail_hide`, `retail`, `pause_screen`, `unpause`, the `cards` primary, `links`, `countdown`, `kind="pause"`; change "8 screens" to 16; a short "HUD layer" paragraph (zones, keep-outs, caps, online, under the stack); a "Retail takeover" paragraph (element ids, sources, empty by default, nothing hidden online, `MELEE_ATLAS_RETAIL`, `MELEE_ATLAS_PAUSE`, the `atlas` console command), and the relation to `gd.hud_visible` (both apply; either hides). `docs/TERMINOLOGY.md`: **HUD zone**, **keep-out rectangle**, **retail pause takeover**. `envoy/MENUS.md` per Task 18.
- [ ] Commit each repo's docs separately.

---

### Task 21: The in-game proof (a checklist for a Windows agent or the owner)

**Nothing before this task proves the screens or the HUD in the game.** The same rules as step 1's Task 18: only when the owner is away (or by him); second monitor (`MELEE_WINDOW_X`/`Y` from the coordinator); `MELEE_VOLUME=0`; never hidden; stop only your own PID; LAB scenes (`mode=lab`), never Training; no screenshots as proof; ACE disc and ACE fighters by default for play tests (the owner's rule), the vanilla disc where a step says so.

- [ ] **Step 1: Build and confirm the exe.** `tools/port/build.sh`; `grep -a "retail elements hidden by MELEE_ATLAS_RETAIL" "$GW_BUILD_ROOT/melee-pc.exe" | head -1` and `grep -a "gd.ui.hud: too many HUDs" "$GW_BUILD_ROOT/melee-pc.exe" | head -1` both print a line.
- [ ] **Step 2: Empty mask looks as before.** A LAB match with no mods: damage, stocks, timer and the pause panel look as before (compare with a run of the main checkout's exe if in doubt). Yes or no.
- [ ] **Step 3: Each bit hides exactly its element.** For each of `hud.damage`, `hud.stock`, `hud.timer`, `pause.panel` (and name tags with `nametag` on): run with `MELEE_ATLAS_RETAIL=<id>`; exactly that element is gone and nothing else; the game keeps running (percent still changes: `= gd.player(1).percent`). Then `atlas retail clear` in the console: it is back. A netplay or rollback-enabled run with the same variable: nothing is hidden.
- [ ] **Step 4: Keep-outs measured.** `load examples/demos/atlas-hud`, `atlas keepout on`, F7: at 4:3 (`960x720`) and 16:9 (`1920x1080`), do the rose keep-out outlines cover the retail damage plates and timer with a small margin? If not, write down the rectangles that do (in 640x480 canvas units: `atlas hud` logs the canvas width) for Task 6's constants. The port cards, strip, banner and toast never overlap the retail HUD.
- [ ] **Step 5: Envoy, a full Classic run** (`load examples/envoy`, `envoy rules on`, start from the Atlas setup screen): the setup screen; the HUD strip, the synergy toast in the top-right corner, opponent cards (at most three, clear of the timer), the pickup note, `Collect the drives` with the A glyph and A collects; the payout hold banner with its leave progress; the reward cards with the countdown (let one run out: the first offer is kept); a swap (fill the bag); the bag (Z+START); results. At 4:3 and 16:9; once at 640x480 for text fit. Yes or no for each, one line for each no. `= gd.ui.state().cost_ms` with the HUD alone and with the reward screen open (target at most 0.5 ms; record the numbers).
- [ ] **Step 6: Pause.** In an Envoy run with the takeover off: START shows what it showed before step 3 (record whether Envoy's list and the retail panel both appear: this answers the open question in Task 13). With `MELEE_ATLAS_PAUSE=1`: START shows the Atlas pause list with the retail panel still visible (nothing hidden), the pausing port drives it, Resume unpauses, B resumes, Quit asks. Then `MELEE_ATLAS_PAUSE=1 MELEE_ATLAS_RETAIL=pause.panel`: only the Atlas list shows. Then `load examples/demos/atlas-pause` in a plain LAB match: the same with the demo's list.
- [ ] **Step 7: Co-op** (`envoy coop`): each seat's strip in its own corner; one seat's reward at a time; seat 2's bag waits with a toast while seat 1's screen is up.
- [ ] **Step 8: Online** (only with a second client and the owner's consent; else "not run"): the reward pick between games is the Atlas cards and is non-modal; the HUD draws in a netplay match; nothing retail is hidden; no desync; `grep -a "input_mask" melee-pc.log` shows no Atlas line.
- [ ] **Step 9: Report** the yes/no list, the numbers, the keep-out measurements and the pause answer. The owner decides on the look (Task 18 Part B waits for it) and, separately, whether to turn on any retail takeover.

---

## Self-review

**Spec coverage (13.3 and 6.8).**

| Item | Where |
|---|---|
| Reward screen, cards primary, countdown | Tasks 9, 10 |
| Swap ("BAG FULL") | Task 11 |
| Setup | Task 12 (entry under Solo waits for step 2) |
| Pause / confirm / quit | Tasks 8, 13 |
| Interlude / Results (the live ones) | Results: Task 14. Interlude belongs to the parked campaign: not ported, wiring removed in Task 18 |
| Online reward box | Task 15 |
| HUD: build strip, opponent card, notes reduced, collect banner, synergy notice as a small top-corner toast, co-op strips | Tasks 5, 6, 7, 16 |
| Generic builders in the engine, assets in the mod | Tasks 5, 9 (cards, links, strip, banner, toast are engine parts; models, colours, letters and text come from Envoy) |
| Retired: run_screen grid and D.grid/embed.py, replaced menu screens, duplicate hud panels; dev LAB boxes stay dev-only | Task 18 Part B (after the look) |
| Parked screens not ported, wiring removed, logic kept | Task 18 Part B |
| Element registry, mask, guards (damage, stocks, timer, name tags, pause panel) | Tasks 3, 4 (plus magnify, coin, prize, hazard) |
| `gd.ui.hud` with keep-outs | Tasks 6, 7 |
| Pause description and on/off hooks; `gw_Ui_RequestUnpause` | Tasks 3, 4, 8 (the shim is `Ui_TakeUnpause` on the game side, fed by `gd.ui.unpause`) |
| Off by default; first users hide nothing retail | Global Constraints; Task 16 (Envoy never calls `retail_hide`); Task 13 (takeover off unless switched on) |
| Verified without the game: Lua stub tests per screen, cap tests, corner-note layout at three widths with retail keep-outs | Tasks 6, 10-17; the stub follows every binding change (Tasks 1, 7, 8, 9) |
| Must be seen | Task 21 |

**Style rules built into tests (the step 1 lessons).** Chamfers: `corners_clear` on every new plate (Tasks 5, 6). Three cues: `focus_cues_at == 3` on cards (Tasks 5, 9) and `no_focus_cues` on every HUD part (Tasks 5, 6). Text: `texts_inside` and `texts_legible` at three widths with the longest real strings (Tasks 5, 6, 9). Ownership and lifetime: Tasks 1, 7, 8 on the real path, plus a console-only negative check (Task 7 `console_is_not_the_test`).

**Gaps and deviations.**
1. Keep-out rectangles are estimates until Task 21 step 4 measures them; the constants and the test move together.
2. The registry parent `pause` and the Envoy `menus` entry wait for step 2 (named in the dependency table).
3. The Atlas pause can take over only the VS-style pause (`gmvs.c`); other modes that pause through their own controller are not hooked (grep found the two VS sites and the camera pair only). The 1P modes run the same `gm_DoPauseChecksAndRoutine` [unverified for every 1P mode].
4. `gd.hud_visible` is not merged into the mask; both apply (documented in Task 20). A later cleanup can make it a script source of the mask.
5. The port card's percent and stocks are read host-side at draw time with the same readbacks as `gd.player`; whether those reads are valid in every scene the draw runs in is checked only in Task 21.
6. Per-port stacks are not built (recommendation above).

**Type and name consistency.** `AtRetail`, `AtPause`, `AT_RE_*`, `AT_RS_*` (Task 3) are used by Tasks 4, 6, 7, 8. `AtOffer`, `AtPortCard`, `AtStrip` and the part functions (Task 5) by Tasks 6 and 9. `AtHud`, `AtHudPart`, `AtKeepOut`, `AtHudLayout`, `AT_Z_*`, `AT_HP_*` (Task 6) by Task 7. `AT_PRIMARY_CARDS`, `AT_MAX_CARDS`, `AT_MAX_LINKS` (Task 9) by Tasks 10, 11, 15. Lua names: `gd.ui.forget`, `hud`, `hud_clear`, `toast`, `retail_hide`, `retail`, `pause_screen`, `unpause` are the same in the binding, the stub, the Envoy modules, the demos and the docs. Game-side shims `Ui_RetailHidden`, `Ui_RetailPause`, `Ui_TakeUnpause` map to the host's `gw_` definitions.

**Placeholder scan.** Where an existing helper's exact name could not be confirmed from the merged code (`run_as_script` in the binding test, the fixture builders in `envoy_testlib.lua`, the PowerPC include flags, the include form for a `pc/platform` header in a game TU), the step says what to grep and what to add if it is missing.

**Execution recommendation.** Tasks 1-9 are engine work, each ending in a native or stub test: a fresh subagent per task with a review between (superpowers:subagent-driven-development), Task 4 by an agent that has read `melee/CLAUDE.md`'s shim section. Tasks 10-17 share `atlas_kit.lua`, the run-screen fixture and one mental model of Envoy's app: one agent in order. Tasks 19-20 are small. Task 21 is for a Windows agent while the owner is away, or for him. Task 18 Part B is a later session.
