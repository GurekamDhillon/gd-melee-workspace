# B4 — Product UI audit (read-only)

Lane: B4. Author: read-only audit agent. Date: 2026-09-30.
Scope: `melee/worktrees/linux/pc/scripts/examples/roguelite/` — `menus.lua`, `hud_layout.lua`,
`feedback.lua`, `onboarding.lua`, `commands.lua`, `roster.lua`, `runtime_presentation.lua`,
`main.lua`, `bindings.lua`, plus the bundler `tools/roguelite/prepare.py` and the tests
`tools/roguelite/test_menu_polish.py`, `tools/roguelite/test_presentation_runtime.py`,
`tools/roguelite/test_menus.py`, `tools/roguelite/test_commands.py`.
Specification: `docs/MENU-POLISH-CONTRACT.md`, `docs/ROGUELITE-ACCEPTANCE.md`.

**No build, no game run, no console (51701) connection, no test execution.** Nothing was modified,
staged or committed except this report. Frozen lanes under `_build/deepseek-worktrees/`,
`_build/sol-worktrees/`, `_build/model-tests/` were not touched.

Every claim below is from reading the source named at its line. Anything that needs a build, a
device or a human eye is marked **PENDING** and is not asserted.

---

## Summary

**The UI is a well-built, well-tested set of pure modules attached to a product that opens four
fewer doors than it has.** `menus.lua` renders nine distinct screens. `main.lua` can open five of
them. The other four — `map`, `onboarding`, `settings`, `ending` — are fully implemented, bounds-
tested, spoiler-tested, and unreachable; the contract that specifies them says so in its own words
(`docs/MENU-POLISH-CONTRACT.md:248-249`: "`main.lua` is not wired yet").

Three consequences that are visible to a player, in order:

1. **The reward screen has no way out.** `menus.lua:177-194` returns after emitting only the four
   reward cards — no `continue`, no `leave`. `Menus.update` honours `input.back` only when
   `s.section=='parents'` (`menus.lua:264`), so B does nothing here. The player reaches this screen
   from `main.lua:526` and `main.lua:586` and can leave it only by successfully claiming a reward.
2. **The tutorial cannot be skipped, replayed, or even seen as a screen.** `Presentation:skip` and
   `Presentation:revisit` (`runtime_presentation.lua:244-245`) have no caller anywhere in the
   product; the SKIP/ENABLE button lives on the unopened `onboarding` screen (`menus.lua:126`). The
   eight core steps (`onboarding.lua:16-33`) reach the player only as coalesced toasts, with no
   opt-out and nothing persisted.
3. **Six emitted control actions have no consumer at all**, and the player-visible result of
   activating one is the internal string `"Lifecycle action must be handled by main"`
   (`menus.lua:347` → `main.lua:801`).

What *is* genuinely finished and should not be reworked: the compact combat rail is compact and
informative (`hud_layout.lua:29,98-102` = 258x61 design units, ~4.1% of the 640x480 canvas;
`feedback.lua:246-261` carries percent, lives, item, and three charge/cooldown/READY segments);
there is **no** permanent large inventory panel anywhere in combat; reduced motion is read from a
real file (`main.lua:62,70`) and actually suppresses motion (`feedback.lua:177,209-214,260`); the
recursive D-pad grammar the tutorial teaches matches the tree the game installs
(`onboarding.lua:21-26` vs `commands.lua:176-187`); and genetics/fusion are taught only when the
feature actually succeeded (`onboarding.lua:91-96`, `main.lua:801,823-824`).

The three outstanding questions that need a device are unchanged from the contract's own list
(`docs/MENU-POLISH-CONTRACT.md:242-244`): HUD readability, menu feel and focus restoration after
scene exit, and real controller hotplug.

---

## 1. Screen reachability

`Menus.view` (`menus.lua:167`) dispatches four contexts to `view_extra` (`menus.lua:160-166`) and
handles the rest inline (`menus.lua:172-256`). `Roster` owns a fifth screen. Reachability is
decided by `pause_menu` (`main.lua:376`) and by `menu_context` (`main.lua:779-784`).

| # | `ctx.menu` | Title | Rendered at | Opened by | Reachable? |
|---|---|---|---|---|---|
| 1 | `collection` | `GENE COLLECTION` (`menus.lua:174`), `BREED / INHERITED CHILD` (`menus.lua:205`) | `menus.lua:170-256`, `508-518` | `main.lua:38` (initial), `337`, `398`, `457`, `789`, `790`, `794`, `990`, `1024` | **yes** |
| 2 | `rest` | `REST / BUILD WORKBENCH` (`menus.lua:174`), `FUSION / RUN CHILD` (`menus.lua:205`) | same | `main.lua:587` (rest room), `989`, `1023` (Special→Loadout) | **yes** |
| 3 | `reward` | `ENCOUNTER REWARD` (`menus.lua:174`) | `menus.lua:485-506` | `main.lua:526`, `586` | **yes** |
| 4 | `error` | `CHECKPOINT UNAVAILABLE` (`menus.lua:173`) | `menus.lua:173` | `main.lua:337`, `396`, `476`, `482`, `571`, `581`, `593`, `600`, `604`, `610`, `629`, `638`, `664`, `679`, `691`, `875`, `891`, `901`, `932`, `940`, `1087` | **yes** |
| 5 | *(not a `ctx.menu`)* `fighter` | `CHOOSE FIGHTER / COSTUME` (`roster.lua:108`) | `roster.lua:105-115`, called `main.lua:1168` | `main.lua:788` from the collection's `CHANGE FIGHTER` | **yes** |
| 6 | `map` | `DISCOVERED MAP` (`menus.lua:91`) | `menus.lua:90-121`, `426-445` | nowhere — no `pause_menu('map')`, and `menu_context` never sets `ctx.map` | **NO** |
| 7 | `onboarding` | `TUTORIAL` (`menus.lua:123`) | `menus.lua:122-134`, `446-457` | nowhere — but `ctx.onboarding` **is** live (`main.lua:783`) | **NO** |
| 8 | `settings` | `SETTINGS` (`menus.lua:136`) | `menus.lua:135-151`, `458-466` | nowhere — but `ctx.settings` **is** live (`main.lua:783`) | **NO** |
| 9 | `ending` | `RUN COMPLETE` / `RUN ENDED` (`menus.lua:154`) | `menus.lua:152-159`, `467-473` | nowhere — `ctx.ending` is never constructed | **NO** |
| — | pseudo | `RUN UNAVAILABLE` (`menus.lua:172`) | `menus.lua:172` | fallback when `rest`/`reward` is opened with no active run | n/a |

Notes on the unreachable four:

* **Map.** The only real map source is `campaign:route_map()` (`main.lua:988`), and that call
  **toasts room/exit counts instead of opening the screen**. The installed command tree labels the
  leaf `Route` (`commands.lua:207`) and `docs/MENU-POLISH-CONTRACT.md:67` states "`route` opens the
  discovered map". The screen it should open is implemented, spoiler-tested
  (`tools/roguelite/test_menu_polish.py:257-271`) and inert.
* **Onboarding / Settings.** These are the *only* two screens whose declared context is genuinely
  wired (`main.lua:783`), which makes them the cheapest reachability wins in the report.
* **Ending.** The run result is real (`main.lua:398` → `Feedback.finish`, `feedback.lua:140-152`)
  but it is delivered as a 360-frame toast over the collection screen. The summary screen that was
  written for it is unreachable.

Dead screens are not dead *code*: `test_menu_polish.py` drives `M.draw` for all four
(`test_menu_polish.py:293-296`) against a bounds-checked stub. Their **static layout bounds are
proven**; their **use in play is not reachable at all**.

### Dead and no-op controls

| Action | Emitted | Consumer | Effect today |
|---|---|---|---|
| `discard` | `menus.lua:236-238` | none in `choose_menu` (`main.lua:787-794`) nor `Menus.apply` (`menus.lua:306-348`) | not even rendered: `menu_context` never sets `ctx.capacity` (`main.lua:779-784`). `Inventory.Collection.commit_discard` (`inventory.lua:567`) is not in the bundle (`prepare.py:34-39`; see report B3) |
| `setting` | `menus.lua:147` | none | falls to `menus.lua:347` → toast `"Lifecycle action must be handled by main"` |
| `map_close` | `menus.lua:93` | none | same |
| `onboarding_close` | `menus.lua:125` | none | same |
| `onboarding_skip` | `menus.lua:126` | none | same; also means `Presentation:skip` is never called |
| `settings_close` | `menus.lua:138` | none | same |
| `ending_continue` / `next_kind` | `menus.lua:157` | none | same |
| `Feedback.tell` | `feedback.lua:82-86` | never called | the priority-55 `tell` kind is unreachable; enemy tells are world-space `CASTING`/`READY` text instead (`main.lua:1174-1179`) |
| `Hud.command_expanded`, `Hud.avoids_center` | `hud_layout.lua:167-185` | never called | exported and tested (`test_menu_polish.py:167-168`) but the product never uses them |
| `F.new(opts).reduced` | `feedback.lua:34` | `Feedback.new()` is called with no args (`main.lua:46`) | dead field; `s.reduced` is always false, and draw uses `opts.reduced` instead (`feedback.lua:177`), so the two sources can disagree (P3, not user-visible today) |

Handled correctly, for contrast: `inspect`/`page`/`parents`/`back`/`map_inspect` inside
`M.update` (`menus.lua:299-304`), `retry_finish`/`choose_fighter`/`fighter_*`/`start`/`resume`/
`continue`/`leave` in `choose_menu` (`main.lua:787-794`), and `starter`/`lock`/`breed`/`fuse`/
`place`/`unequip`/`reward` in `Menus.apply` (`menus.lua:312-346`).

---

## 2. Navigation: controller, mouse, keyboard

### Held buttons

* **Combat command tree — correct and deliberate.** Edges only, `previous==0` required
  (`commands.lua:70`), chords neutralised (`commands.lua:62-67`), Up masked until release
  (`commands.lua:91-92`), and `C.install` preserves `previous`/`up_latched` across a rebuild
  (`commands.lua:229`) with the live word passed in from `main.lua:81,973,1010`. This is the part
  of the input stack that is finished.
* **Menus — edges only, no auto-repeat.** `main.lua:959` and `999` pass edges; `menus.lua:258`
  documents it. Consequence: crossing the workbench from the gene list to `START A RUN` /
  `RESUME SAVED RUN` (`menus.lua:227-228`, up to ten controls away) costs one press per step with
  no repeat. **P2, usability.**
* **v2 reward overlay — commits on an already-held A.** `open_v2_reward` is entered from
  `main.lua:965` on the tick `campaign.reward_room` becomes set; `handle_v2_reward`
  (`main.lua:508-518`) then tests `edge(b,gd.buttons.A)` on the very next tick with no latched
  previous word of its own. An A held for any other purpose commits reward `ui.focus` immediately.
  Every other input path in `main.lua` latches `buttons`; this one does not. **P2, fairness bug —
  statically identified; PENDING in-game reproduction.**
* **Stale latch on pause.** `pause_menu` calls `Commands.reset(command_state,buttons)`
  (`main.lua:376`), but `buttons` is only assigned at the *end* of `on_tick`
  (`main.lua:962,992,1002,1028`), so it holds the previous tick's word. Compare `main.lua:973,1010`,
  which correctly pass the fresh `b`. **P3.**

### Chords

Combat refuses a diagonal (`commands.lua:62-67`). Menus do not: `menus.lua:265` and `roster.lua:81`
collapse a chord to right/down priority and navigate. The same physical input is a no-op in a room
and a focus move in a menu. **P3, inconsistency.**

### B / back

* `menus.lua:264` handles `input.back` **only** for `s.section=='parents'`. On collection, rest and
  reward it does nothing — while the legend the same file draws at `menus.lua:520` reads
  `D-PAD: FOCUS   A: SELECT   B: BACK   /   MOUSE: CLICK`.
* `roster.lua:78` *does* honour B. So the two menu systems disagree.
* This is the only plausible exit from the reward screen (see Summary) and the advertised exit from
  the workbench. **P1/P2.**

### Focus

* `Menus.reset` always clears `s.focus` (`menus.lua:70`) and `focused()` treats
  `v.controls[1]` as focused when `s.focus` is nil (`menus.lua:425,512`). Every `pause_menu`
  therefore lands focus on the first control.
* On the reward screen the first control is reward card 1 (`menus.lua:181-187`), so a single A
  press on entering claims it with no navigation. **P2.**
* Horizontal focus has **no** wrap: the fallback at `menus.lua:274` handles only `dy`
  (`dy<0 → #controls`, `dy>0 → 1`); a left/right press at the row edge changes nothing, while up/down
  wraps. `rogue_menu` advertises `wrap=` without qualifying the axis (`main.lua:1290`). **P2.**
* Focus is never restored across menu round trips. The contract lists "focus restoration after scene
  exit" as human-unverified (`docs/MENU-POLISH-CONTRACT.md:242-244`). **PENDING.**
* Because navigation is purely geometric (`menus.lua:266-274`), one D-pad press from a gene row
  jumps to `PLACE / ASSAULT` (`menus.lua:248`) rather than staying in the list — the nearest control
  by `along + cross*3` is two rows down and one column over. **P3.**

### Mouse

Uniform and correct on both screens: a click inside a rect focuses and activates in the same event
(`menus.lua:277-281`, `roster.lua:92-94`), with a real edge on button 1 (`main.lua:959,999`). One
caveat: the test stub asserts `x + max_w <= 640` for text but performs **no y assertion**
(`test_menu_polish.py:284`), so text baselines near the canvas bottom are not bounds-proven — see §6.

### Hotplug / reconnect

`main.lua:858` is the only pad read: `local pad=gd.pad(1,true);local b=pad and pad.buttons or 0`.
A `nil` pad is indistinguishable from "no buttons held", so both `Commands` (`commands.lua:58,70`)
and the menu edge detector (`main.lua:959`) read a disconnect as a full release followed by a fresh
press. Reconnecting while holding Down at the command root can travel or execute immediately
(`main.lua:970-975`, `commands.lua:75-85`). There is no on-screen disconnect notice and no
statement that port 1 is assumed. **P2 — static analysis; PENDING hardware confirmation.**

### Pause

`pause_menu` = `gd.pause()` + `gd.input_mask(1,15)` (`main.lua:376`); `unpause` restores
(`main.lua:377`). `on_frame` freezes on `menu or reward_ui` (`main.lua:1078`) while `on_tick` keeps
routing input to the menu, which is correct. Two rough edges:

* v2 has a second pause owner, `v2_set_paused` (`main.lua:421-429`), which calls `unpause()`, and
  `v2_recovered()` (`main.lua:450-460`) can `pause_menu('collection')` *after* the menu input block
  for that tick has already run (`main.lua:949-962`). One tick of input is routed to the old screen.
  **P3.**
* The collection screen opened from combat (`main.lua:990,1024`) has no route back to the live
  room: `leave` and `continue` are rest-only (`menus.lua:253-254`), B is inert, and the only exits
  are `START A RUN`, `RESUME SAVED RUN` (`menus.lua:227-228`) and the fighter screen
  (`main.lua:789-790`). Not a softlock — `RESUME SAVED RUN` re-enters the same run — but an
  unlabelled, non-obvious escape from a frozen fight. **P2.**

### Respawn

`complete_entry` (`main.lua:559-590`) is honest: it refuses to fake placement, keeps simulating,
retries for 600 ticks, then fails into `error` with a retained checkpoint (`main.lua:567-573`).
Input is masked during `pending_entry` (`main.lua:904`) so no menu can be entered mid-respawn. Stock
loss routes to `finish` → `pause_menu('collection')` (`main.lua:1103,1134` → `398`), where the run
summary the player expects is only a toast, because `ending` is unreachable.

---

## 3. Onboarding

| Question | Answer | Evidence |
|---|---|---|
| Teaches the real recursive D-pad grammar? | **yes** | `onboarding.lua:21-26` describes L/R/D opening a branch, Up returning one level, and L/R/D on the *final* branch auto-casting. That is exactly the installed tree: root forks three (`commands.lua:177-184`), `ABILITIES` children are leaves at depth 2 (`commands.lua:186-187`), and a leaf press executes (`commands.lua:81-84`). It correctly does **not** tell the player to press A (which is the attack). |
| Never pauses combat? | **yes** | `onboarding.lua:6`, `view().pause` hardcoded false (`onboarding.lua:116`); `menus.lua:129-130` asserts `v.no_pause` in the view itself. |
| Genetics/fusion only when the feature exists? | **yes** | `onboarding.lua:91-96` requires `event.available==true`; `main.lua:801` returns early on a refused `Menus.apply`, and only `main.lua:823-824` observes, with `available=result.ok==true`. |
| Early grammar steps lapse late in a route? | **yes** | `onboarding.lua:73-76,101-103`; window `first_rooms=3` (`onboarding.lua:40`) because `main.lua:69-71` passes no `tutorial` opts; room index from the real node depth (`main.lua:90,595,910`). |
| Skip supported? | **NO** | `Presentation:skip` (`runtime_presentation.lua:244`) has no caller. The only control is `menus.lua:126` on the unopened screen, and its action has no handler. Nothing is persisted. |
| Revisit supported? | **NO** | `Presentation:revisit` (`runtime_presentation.lua:245`) has no caller; same dead `onboarding` screen. |
| Reachable as a screen, or only as toasts? | **toasts only** | `Onboarding.toast` → `Presentation:toast` → `Feedback.tutorial` (`runtime_presentation.lua:161-163,175-181`; `feedback.lua:76-81`) → the notification strip. `STEP i / n` progress (`menus.lua:449`) is never shown. |

So: the tutorial's *content* is accurate and honest; its *delivery* is a fixed eight-toast
sequence with no opt-out and no progress display.

---

## 4. Combat rail, inventory panel, reduced motion

**Rail — compact and informative: yes.** Design box 258x61 (`hud_layout.lua:29`, placed at
`hud_layout.lua:98-102`) on a 640x480 canvas ≈ 4.1% of the screen. Contents: percent, `LIVES`,
`ITEM`, and per-slot icon + charge/cost or cooldown-seconds or `READY` + charge ratio bar + ready
bar (`feedback.lua:246-261`). The opponent block is placed right of the rail, or stacked fully
above it, and the code de-overlaps it against the rail (`hud_layout.lua:145-159`) so it can never
cover a charge bar. When the compact rail is not actually installed, only minimal life/damage
anchors draw and the native cluster is left readable (`feedback.lua:219-236`, gated on
`layout.replace_vanilla`, `hud_layout.lua:93`). This is the finished part of the HUD.

**Permanent large inventory panel: none.** The gene list exists only inside paused workbenches
(`menus.lua:195-199`), and `presentation:draw` is called with `hud=not menu` (`main.lua:1191`) so
the rail is suppressed behind any menu. `Menus.draw` does fill the whole 640x480
(`menus.lua:476-477`), but only while the engine is paused by `pause_menu` (`main.lua:376`). The
v2 reward overlay (`main.lua:1157-1164`) occupies (40,60)-(520,280); the rail (14,407,258,61) and
the notification (196,10,418,46) do not intersect it, and the overlay returns before the tell and
exit labels are drawn.

**Reduced motion — honored from a real setting: yes.** `gd.data_read('config.txt')`
(`main.lua:62`) → `reduced_motion=true` (`main.lua:70`) → `Presentation.reduced`
(`runtime_presentation.lua:42`) → `Feedback.draw` opts (`runtime_presentation.lua:140`) → ready
pulse suppressed (`feedback.lua:260`), confetti suppressed and the progress bar pinned
(`feedback.lua:209-214`), `F.view` pulse zeroed (`feedback.lua:159`). Honest reporting is
asserted in `test_presentation_runtime.py:638`. **Gap:** it is not reachable or toggleable in game
(the settings screen is unopened and the `setting` action is unhandled), and the game never writes
it back — only one declared item exists (`runtime_presentation.lua:288-291`).

**One real layout collision.** While any menu is open, `Feedback` draws the compact strip at
`layout.compact_notification` = (28, 63, 588, 23) at dpi 1 (`hud_layout.lua:113-117`;
`feedback.lua:187-195`) — the same vertical band as the workbench's scope line at y=78 and its
divider at y=87 (`menus.lua:480-481`). And `main.lua:780` always passes `ctx.notice`, so
`menus.lua:480` suppresses the scope line whenever *any* notice is queued. The workbench's
orientation text ("RUN COPIES / UPGRADES END WITH THIS RUN", `menus.lua:175`) therefore appears and
disappears with the toast queue. **P2.**

---

## 5. Text centralization and leakage

**Not centralized.** There is no strings/i18n module in the bundle (`prepare.py:34-39`). Literals
are inline in `menus.lua:7-9,61-66,93,125-126,138,174-176,191,222-228,234,248-254,428-443,449-455,
462-464,470-471,492-493,506,520-530`, `feedback.lua:129-149`, `commands.lua:15-21,106,156-207`,
`roster.lua:68-69,109,113-114`, `onboarding.lua:16-33`, `main.lua:217,275,338-339,399,485,
494-556,570,580,588,614,626,916,947,975,987,1021-1022,1134,1136`. Only `onboarding.lua:16-33` is a
table that could be enumerated and translated. **P3.**

**Raw handles in product text.** A gene's only identity anywhere is its id `g1..gN`:

* gene list label `menus.lua:197` → the player reads `g7 / RIME`
* stat panel `menus.lua:382,386-387`, parents preview `menus.lua:423`
* mannequin slot labels `menus.lua:406`
* every placement/unequip/fuse/breed/starter message and toast `menus.lua:313,317,320,323,326,331,340`
* page header count `menus.lua:509`
* v2 reward overlay `main.lua:1161` — `(option.kind or 'gene')..' '..tostring(option.id or '')`

`C.definitions[g.kind].name` exists and is used in the stat panel (`menus.lua:381`) but not as the
list identity. **P2.**

**Internal diagnostics in product flows.** `Menus.apply`'s fallback is the developer string
`'Lifecycle action must be handled by main'` (`menus.lua:347`), reached by `main.lua:801` for every
unhandled kind in the table in §1. Also `main.lua:604` (`'Room construction failed: '..why`),
`main.lua:556` (enemy-controller reason), `main.lua:987`/`1022` (`use_supply` reason). By contrast
the `rogue_*` console diagnostics are correctly `gd.log`-only (`main.lua:1243-1292`), and
`bindings.coverage`'s measurement text (`bindings.lua:11-15`) is surfaced deliberately as the roster
subtitle (`roster.lua:70,109`) — that is the right kind of detail for that screen.

---

## 6. Ranked gaps

### 6a. Static layout bounds **proven** (no build needed)

* Rail / opponent / notification / compact strip / fallback rect ownership, rail-opponent
  disjointness, third bar inside the rail, compact line inside its strip, at 640x480 dpi1/dpi2 and
  854x480 dpi1/dpi2 (`hud_layout.lua:100-160`; claimed in `docs/MENU-POLISH-CONTRACT.md:219-223`;
  exercised against recorded real `gd.fill`/`gd.kit.text` coordinates in
  `test_presentation_runtime.py:385-407`).
* Button and icon fills for all nine screens asserted inside 640x480 by a bounds stub
  (`test_menu_polish.py:280-296`).
* Map spoiler boundary against a real `RouteMap.build` (`test_menu_polish.py:257-271`).
* Destructive-confirm identity/generation invalidation (`menus.lua:291-298`;
  `test_menu_polish.py:201-228`).
* Loadout honesty: empty slots blocked, zero supplies blocked, no catalogue enumeration
  (`commands.lua:151-161,189-204`; `test_presentation_runtime.py:268-331`).
* Held-Up across rebuild, no fabricated root taunt (`commands.lua:220-232`;
  `test_presentation_runtime.py:736-800`).
* Fresh collection renders before any room or run exists (`test_presentation_runtime.py:672-690`).

### 6b. Ranked gap list

| # | Sev | Gap | Player-visible impact | Evidence |
|---|---|---|---|---|
| 1 | **P1** | Reward screen has no exit control and B is inert there | A room-clear reward modal can only be left by successfully claiming. If every card is blocked (no placed gene and `Core.acquire` refusing), the run cannot continue. | `menus.lua:177-194`, `menus.lua:264`; entered at `main.lua:526,586` |
| 2 | **P1** | Four of nine screens unreachable; their controls have no consumer; the map command leaf does not open the map | The map, the tutorial screen, settings and the run summary are all invisible. `Special→Route` toasts counts instead of showing the route, contradicting the tree label and the contract. | `main.lua:779-784`, `main.lua:988`; `commands.lua:207`; `MENU-POLISH-CONTRACT.md:67,248-249` |
| 3 | **P1** | Tutorial skip/revisit unreachable and unpersisted | An experienced player cannot silence eight tutorial toasts and cannot replay them. | `runtime_presentation.lua:244-245`; `menus.lua:126`; `onboarding.lua:16-33` |
| 4 | **P2** | `discard` is dead and never rendered | At a full collection the promised "discard or replace" path does not exist; breeding will simply refuse (`menus.lua:191` text vs no control). | `menus.lua:236-238`; `main.lua:779-784`; `inventory.lua:567` not bundled (`prepare.py:34-39`) |
| 5 | **P2** | B is inert in collection/rest/reward while the legend advertises it; `Roster` disagrees | The advertised back control does nothing on the three main screens. | `menus.lua:264` vs `menus.lua:520`; `roster.lua:78` |
| 6 | **P2** | No route back to a live room from the collection screen opened mid-combat | A frozen fight is exited only via an unlabelled `RESUME SAVED RUN` or by abandoning to a new run. | `main.lua:990,1024`; `menus.lua:227-228,253-254` |
| 7 | **P2** | v2 reward overlay commits on an A that was already held | A reward can be spent by a button held for another purpose. | `main.lua:965` → `main.lua:508-518` |
| 8 | **P2** | `setting` action unhandled; settings screen unopened; value never persisted | Reduced motion is a config-file-only feature the player cannot reach. | `menus.lua:147`; `main.lua:62,70`; `runtime_presentation.lua:288-291` |
| 9 | **P2** | Run outcome delivered as a toast, not the written summary screen | No persistent record of what a run exported or lost. | `main.lua:398`; `feedback.lua:140-152`; `menus.lua:152-159` |
| 10 | **P2** | Workbench orientation line appears/disappears with the toast queue | The "RUN COPIES / UPGRADES END WITH THIS RUN" line — the key orientation cue in the build screen — flickers. | `main.lua:780`; `menus.lua:480-481,175`; `hud_layout.lua:113-117`; `feedback.lua:187-195` |
| 11 | **P2** | Raw gene ids are the only identity in product text | The player reasons about `g7`, not about Cinder or Rime individuals. | `menus.lua:197,313,317,320,323,326,331,340,382,406,423,509`; `main.lua:1161` |
| 12 | **P2** | `"Lifecycle action must be handled by main"` reaches the player | Developer text on screen for six control kinds. | `menus.lua:347` → `main.lua:801` |
| 13 | **P2** | Reconnect is indistinguishable from release-then-press | Reconnecting while holding Down at the command root can travel or execute immediately. | `main.lua:858`; `commands.lua:58,70` |
| 14 | **P2** | Focus starts on a spending control; horizontal focus does not wrap; no auto-repeat | Entering the reward screen arms card 1; the left/right edges of every row are dead; a held direction moves focus once. | `menus.lua:425,274`; `menus.lua:181-187`; `main.lua:959` |
| 15 | **P2** | `Feedback.tell` unreachable; tells are world-space text | The contract's priority-55 notice that must sit below `clear` never appears; no priority protection for tells at all. | `feedback.lua:82-86`; `main.lua:1174-1179`; `MENU-POLISH-CONTRACT.md:121` |
| 16 | **P3** | Text not centralized | Any wording change is a multi-file edit. | see §5 list |
| 17 | **P3** | `Menus.view` recomputed twice per frame, each control cloning the whole run | On the reward screen ≈ 12 `snapshot`+`restore` round trips per frame (`copy` = `menus.lua:12`). | `main.lua:961,1168`; `menus.lua:182,245` |
| 18 | **P3** | Chord policy differs between combat and menus | Same input: ignored in a room, navigates in a menu. | `commands.lua:62-67` vs `menus.lua:265`, `roster.lua:81` |
| 19 | **P3** | `pause_menu` latches the previous tick's button word | A direction pressed on the menu-opening tick is not latched. | `main.lua:376` vs `main.lua:973,1010` |
| 20 | **P3** | `Hud.command_expanded` / `Hud.avoids_center` never used | Dead geometry helpers; `layout.command` is computed every frame and drawn by nobody. | `hud_layout.lua:136-137,167-185` |
| 21 | **P3** | `F.new().reduced` dead; two reduced sources can disagree | No visible effect today (draw uses `opts.reduced`); latent divergence. | `feedback.lua:34` vs `feedback.lua:177` |

### 6c. Requires a build or a human (not claimed here)

| Item | Why static evidence is insufficient |
|---|---|
| HUD readability, contrast, and whether the `y=474` (`menus.lua:520`) / `y=478` (`roster.lua:114`) control-legend baselines clip against the 480 canvas bottom | The text stub checks `x + max_w <= 640` but asserts **nothing about y** (`test_menu_polish.py:284`); button/icon fills are the only y-bounded things. Needs kit caption metrics + a screenshot. **PENDING** |
| `gd.hud_visible` really hides the vanilla stock/percent cluster, so `replace_vanilla` is truthful | Registered as `l_hud_visible` at `gw_script.c:5496`, table entry `5660`; the effect behind it was not exercised here. **PENDING** |
| Whether the all-blocked reward screen (gap 1) is reachable in a real run | Requires a run with no placed gene and a refusing `Core.acquire`. **PENDING** |
| Controller hotplug / reconnect mid-hold (gap 13) | Needs a physical pad. **PENDING** |
| Menu feel, focus restoration after scene exit, held-button feel | Listed as human-unverified by the owning contract (`MENU-POLISH-CONTRACT.md:242-244`). **PENDING** |
| Anything on the live v2 campaign path | `docs/ROGUELITE-ACCEPTANCE.md:53-56`: "Live v2 campaign output is **not accepted or installed**." **PENDING** |

---

## 7. Proposed implementation order

Each step is small, independently reviewable, and unblocks the next. Steps 1-3 are pure `main.lua`
wiring against modules that already exist and are already tested.

1. **Give `Menus.update` a real B.** Honour `input.back` in the main section too — at minimum on the
   `reward` screen (a `continue` action, guarded the same way `room_clear` already is at
   `main.lua:520-528`), and on `rest` as a no-op-because-already-paused. Removes gap 1 and the
   legend lie in gap 5. Add the "no enabled control" case to the reward screen explicitly rather
   than relying on a card being available.
2. **Wire the two screens whose context already exists.** Add `map` and `settings` to
   `menu_context` (`main.lua:779-784`) plus pause-menu entries via `Menus.reset`
   (`main.lua:376`). For `settings`, add a `setting` branch to `Menus.apply` (`menus.lua:306-348`)
   that persists `reduced_motion` into the same `config.txt` it is read from — that closes gaps 8
   and 12 in one change and gives the setting a real, reachable owner.
3. **Point `Special→Route` at the map.** `main.lua:988` already has the real map; replace the count
   toast with `pause_menu('map')` after populating `ctx.map`. Add `map_close` handling in
   `choose_menu`. Closes the largest part of gap 2.
4. **Wire tutorial skip/revisit.** Handle `onboarding_skip` in `choose_menu` → `Presentation:skip`,
   add a pause-menu `onboarding` entry that also calls `Presentation:revisit`, and persist both in
   the profile so a returning player is not re-taught. Closes gap 3 and completes gap 2.
5. **Replace the internal fallback string.** `menus.lua:347` should return an honest, player-facing
   refusal; `main.lua:801` should never be able to show developer text. Then either implement
   `discard` (via the unbundled `Inventory.Collection.commit_discard`, see report B3) or remove the
   control and the `capacity_note` that promises it (`menus.lua:191`). Closes gaps 4 and 12.
6. **Give the run a summary screen.** Build `ctx.ending` from the real `Feedback.finish` result at
   `main.lua:398` and route `ending_continue` back to the collection. Closes gap 9.
7. **Fix navigation consistency.** Latch a previous button word for `reward_ui` (`main.lua:508-518`,
   gap 7); add horizontal wrap or an explicit edge-stop indicator (`menus.lua:274`, gap 14); add
   auto-repeat after a held threshold; add a route-back control to the collection screen
   (`menus.lua:220-240`, gap 6); pass the live `b` into `pause_menu`'s `Commands.reset`
   (`main.lua:376`, gap 19).
8. **Give genes readable names.** Thread a display name through the gene list, stat panel,
   mannequin, messages and the v2 reward overlay (`menus.lua:197,313-340,382,406,423,509`;
   `main.lua:1161`), falling back to the id only in `gd.log`. Closes gap 11.
9. **Move the workbench's orientation line out of the notification band.** Either draw the scope
   line unconditionally (`menus.lua:480`) or shift `compact_notification` below the divider
   (`hud_layout.lua:115`). Closes gap 10.
10. **Text centralization last.** Introduce a strings table consumed by `menus.lua`, `feedback.lua`,
    `roster.lua` and `main.lua`, seeded from `onboarding.lua:16-33`. Do it after steps 1-9 so the
    wording is already settled. Closes gap 16.
11. **Cleanup, no player impact.** Delete or wire `Hud.command_expanded` / `Hud.avoids_center` and
    `F.new().reduced`; cache `Menus.view` once per frame instead of twice (`main.lua:961,1168`);
    unify the chord policy. Gaps 17, 18, 20, 21.

Steps 1-6 are the ones that make the difference between "the UI modules exist" and "the UI exists
in the game". All six are wiring, not new design, and each is verifiable by a stub-level test of
the same shape as `test_presentation_runtime.py:585-626` (drive `on_tick` and assert the menu and
the action, no engine).