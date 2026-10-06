# Envoy gameplay UI audit (2026-10-05)

Question: what does Envoy draw on screen during a live match, which of it is debug or developer UI a player should not see, and what to hide.
Scope: reading and writing only. No game launched, nothing built, no game or mod file changed.

Labels used below: **[capture]** = I looked at the picture; **[code]** = I read it in source; **[log]** = a session log line; **[judgement]** = my opinion.
Paths are relative to the workspace. `E:` = `melee/pc/scripts/examples/envoy/scripts/`, `PL:` = `melee/pc/platform/`, `LAB:` = `melee/pc/geno/mods/geno-lab/scripts/lab.lua`.

## 0. Findings in five lines

1. The offender you most probably mean is not one thing. In an Envoy fight the loudest non-gameplay items are: the **small gold text under the top-left bar**, the **wide top-centre announcement panels (six seconds each, queued one after another)**, the **wide opponent panel across the top for four seconds**, and the **"+34% Depth 0" numbers in the top-left bar**. [capture + code]
2. The true developer overlays (Modifier LAB text box, LAB corner icon and bottom strip, FLY readout bar, hitbox/frames/launch overlays) appear **only in the LAB or when a fighter is flying**. A normal Envoy Classic run does not draw them. The one exception on record: the Modifier LAB text box was drawn over the top-left bar in an early capture; the code that hides it in runs was committed 12 minutes after that capture. [capture + commit times]
3. Every Envoy play script starts the run by **console command** (`envoy rules on`, `envoy classic`). In code the menu-started run has `rules=false`, which draws a **different, older "SuperTime Envoy" stat panel top-right** instead of the strip. So what you saw in play is the console-started HUD. [code]
4. The error toasts of the mod ("Build update refused: ...", "A keystone was removed: lower allowance") are sent through the same top-centre panel, **titled "Technique"**. [code]
5. The build strip is drawn on top of the retail results screen ("Special Bonus"), a capture-visible leak. [capture]

## 1. Every element that can be on screen in a live Envoy match

Columns: **For** = P (player information needed in a fight), B (better between stages / in the bag), D (developer or debug), R (retail game). **Switch** = whether something already hides it. **Rec** = KEEP / MOVE / SHRINK / HIDE (developer-only behind a switch) / REMOVE. Owner rulings of 2026-10-05 are applied and marked "ruled".

### 1a. Envoy rule-host run (console start: `envoy rules on`)

| # | Name a player would use | Looks like / where | Drawn at | Shows when | For | Switch | Rec and reason |
|---|---|---|---|---|---|---|---|
| 1 | Build bar | Dark strip top-left, 26 px high: one small square per drive slot (fill = colour, edge = rarity), then `+34%`, `Depth 0` (also `NG+1`, `3 drive(s) waiting`), then one lettered cell per keystone (six, then `+n`) | `E:run_hud.lua:52-82` (model 9-27) | Whole fight, always | P (squares, keystone cells), B (strength %, depth) | none | **SHRINK**: keep squares and keystone letters; move `+N%` and `Depth` to the bag [judgement]. Seen: `envoy-synergy-fx/shots/r2_fight_a.png`, `envoy-look/shots/after/strip_6slot_7key.png` |
| 2 | Gold text under the build bar | Small italic gold text just below the bar, about 2 s | `E:run_hud.lua:77`; trigger list below | On many events: slot changed/emptied, keystone chosen/removed, merged, "Build ready", "+ drive", "Drive waiting", "Collect the drives (N s)", "Out of bounds: a stock is lost", and **every modifier fire** (`Hd:watch`, `run_hud.lua:39-46`: shows "<modifier name>!" or "Modifier!") | mostly D / B | none | **REMOVE** all but the out-of-bounds line (which becomes a corner toast). Most echo something already shown. Triggers: `run_host.lua:152,161,185,186,230,325,335,568,576,579,659,666,670,741,838`. Seen: `envoy-fx/shots/g_hold_0.png` ("Collect the drives (29 s)" while the banner below says the same), `envoy-fx/shots/g3_near_0.png`, `envoy-look/shots/after/c_crit.png` ("Build ready"); log: `FLASH Keystone: Phase Dash`, `FLASH Iron Resolve!` |
| 3 | Bar flash tint | The bar's background turns amber and the `%` turns gold for 1.5 s alongside #2 | `E:run_hud.lua:60-61,71` | same as #2 | D | none | **REMOVE** with #2 |
| 4 | Announcement panel | Wide panel top-centre (560 px max), 6 s, **one at a time, the rest queue**; lines wrapped; archetype emblem tile on the left for synergy | `E:run_hud.lua:83-108`, 6 s = `announce_frames=360` (line 5) | Starter drive + starting keystone (`run_host.lua:405-421`); slot / keystone allowance / drive tier / NG+ milestones (`run_host.lua:370-380,473`); synergy "X assembled" (`synergy_fx.lua:184-188`); "Technique" and error toasts (see #5) | B mostly; synergy P | `synergy fx announce` layer flag exists in tuning (`mod_tuning.lua:64`) but nothing reads it | **MOVE / SHRINK**: milestones to the between-stage screen; synergy ruled "smaller, top corner toast"; starter panel keep once per run, shorter. At stage start three panels queue for 18 s (log frame 126075: "Fifth slot unlocked", "Keystone allowance: 2", "Drive tier 2"). Seen: `envoy-synergy-fx/shots/r2_burn_p1.png` (covers the match timer and the P1/CP tags) |
| 5 | "Technique" panel (mod messages) | Same panel, gold title "Technique" | `E:run_host.lua:46` sends every mod toast with the title "Technique" | Once per run: "Technique rule fired: ... Techniques show as a coloured afterimage ..." (`mod_lab.lua:693-695`), and the error texts `mod_lab.lua:460,469,479,579,820-823` ("Build update delayed: retrying", "refused", "A drive moved to the bag: fewer slots", "A keystone was removed: lower allowance") | teaching line B; errors D | none | **HIDE** the error texts (log only, developer switch); **MOVE** the teaching line to the bag/first-time hint. Log shows it queued behind crit and synergy panels |
| 6 | "Critical hit x1.7" pop-up | Same top-centre panel (#4), titled "Technique", second line "Critical hit x1.7" (log: `hud toast: Critical hit x1.7`) | `E:earned_fx.lua:146-149` | A strong crit (strength >= .75) | D/P | none | **REMOVE** (ruled: "meh, it can go") |
| 7 | Pickup card | Panel bottom-centre, 2.5 s: "A drive dropped!", "Picked up: ...", "Merged!", "Bag full: ..." | `E:run_hud.lua:109-116`; triggers `run_host.lua:230,563,572,575,578` | Each drop / pickup / merge | P (pickup), B (merge) | none | **SHRINK**: drop "A drive dropped!" (the floor effect says it), make pickup a one-line corner toast, merge to the bag (ruled direction: stop inventory spam) |
| 8 | "Collect the drives" banner | Gold-edged strip 300 px wide centre-top, directly under the match timer, with `N s` once the foes are out | `E:run_host.lua:619-629` | Stage end hold while a drive is on the floor | P | `end_hold` tuning flag (`run_host.lua:27`) | **KEEP**, shift down so it does not cover the timer. Seen: `envoy-fx/shots/g_hold_0.png` (covers the timer digits) |
| 9 | Drive arrow | Bobbing gold triangle over the nearest floor drive; if off screen an edge box with arrow and the word "Drive" | `E:run_host.lua:630-646` | Same hold | P | none | **KEEP**. Seen: `envoy-fx/shots/g3_near_0.png` (left edge) |
| 10 | Opponent panel | Full-width dark panel across the top (y +42), 3 lines of the opponent's modifiers plus `(opponent strength 1.4)` and its archetype tag at the right; shown 4 s per opponent, rotating | `E:foe_lab.lua:108-127`; archetype tag `synergy_fx.lua:259-266` | After each opponent's roll, stage start; waits while a panel (#4) is up | P (what the foe carries) but too wide | `synergy fx nameplate off` hides only the tag | **SHRINK** to a small top-right card, or MOVE to the get-ready moment; the strength number is D. Covers timer and P1/CP in `envoy-synergy-fx/shots/r2_plate.png` |
| 11 | Synergy pill | Small dark pill right of the build bar: emblems of assembled archetypes, and a counter `x5` that climbs while a chain fires then fades | `E:synergy_fx.lua:236-252` | Whenever an archetype is assembled or a chain is live | P | `synergy fx hud off` | **KEEP** (small) [judgement]. Seen: `r2_burn_p1.png` (two flame emblems + `x5`) |
| 12 | Link flash | Curved glowing line from attacker to target in the archetype colour, with an emblem popping over the target | `E:synergy_fx.lua:204-234` | A chain fires | P | `synergy fx chain off`, `intensity` | **KEEP** (ruled "awesome"). Seen faintly in `r2_burn_p1.png` (orange link dot above Mario) |
| 13 | Crit impact frames | Whole-screen post pass at the contact point: radial streaks, blur, colour fringes; length and strength scale with crit strength, light crits get a "crisp accent" | `E:earned_fx.lua:69-84` (`play`), look table 14-20 | Every crit (min strength .12) | effect, not UI | `critfx off` / `critfx intensity` (`mod_lab.lua:16,189`) | **NOT RULED**. Heavy at high strength: `envoy-look/shots/after/c_crit.png` shows the whole frame streaked. See question Q7 |
| 14 | Crit tracer | Glow trail on the attacker's active hitboxes for 24 frames | `E:earned_fx.lua:117-135` | A crit | effect | `critfx off` | **KEEP** (tracer = "this hit carries something", presentation language) |
| 15 | Earned afterimage | Coloured afterimage on a fighter while an earned status lasts | `E:earned_fx.lua` (header 1-8), `visual.lua` | While the status lasts | effect | `critfx off` | **KEEP** (approved language) |
| 16 | Fighter tints | Surface treatment of equipped drives, statuses and the assembled-archetype motif | `E:visual.lua`, `synergy_fx.lua:85`; shader `shaders/modifiers_surface.wgsl` | While equipped | effect | `synergy fx surface off` | **KEEP** (ruled: overlapping tints are fine). Seen: `envoy-fx/shots/statuses_final.png` |
| 17 | Floor drive effects | Beam, glow, sparkle, pool, ember crown etc. on a dropped drive | `fx/DriveLoot_*`, `items/drive` | While a drive is on the floor | effect | none | **KEEP** (ruled). Seen: `envoy-fx/shots/drop_gb_0.png` |
| 18 | Co-op strips | Each seat's bar, panel and card on its own side, with a `P1` / `P2` colour tab | `E:run_hud.lua:47-51,62`; `coop.lua:344-348` | Co-op run | P | same as above | Same recommendations as #1 to #7 |
| 19 | Bar over the results screen | The build bar stays drawn on top of the retail "Special Bonus" results screen | `E:run_host.lua:871-879` draws while the match flag is active | After the match ends | none | none | **FIX** (hide when the results screen is up) [judgement]. Seen: `envoy-fx/shots/g3_after_ko.png` |
| 20 | Bag / pause screen | Full grid screen (Z+START), pauses the game | `E:run_screen.lua` | On demand | B | n/a | Between-stage content; not "during gameplay" unless opened. Not audited further |

### 1b. Developer text of the mod that can still appear

| # | Name | Looks like / where | Drawn at | Shows when | For | Switch | Rec |
|---|---|---|---|---|---|---|---|
| 21 | Modifier LAB text box | Dark box top-left, 420 px: "Modifier LAB / ready", `P1: Frosted, Hit and Run, Lingering`, `Last chain:`, `Envoy foe P2` | `E:mod_display.lua:184-202`, called `mod_lab.lua:797` | Only if the mod is enabled and **not** in a rule-host or co-op run | D | `mod box off` (`mod_lab.lua:178-179`); hidden when hosted (`mod_lab.lua:95,797`) | **HIDE** (already hidden in runs). Seen overlapping the build bar in `envoy-join/shots/strip_169_a.png` (taken 01:45; the hiding commit `857266985` is dated 01:57 [commit times]) |
| 22 | Drive LAB card | Panel top, a card line | `E:drive_lab.lua:219-221` | LAB route only | D | none | **HIDE** (developer) |
| 23 | Online reward box | 340x190 plain debug-font box at screen coordinates 150,110: "ENVOY REWARD - game N - n s left", cursor list, "Up/Down choose, A takes it" | `E:mod_lab.lua:754-767` | Netplay reward between stages | B | none | **MOVE** to the kit reward screen (it uses the plain font) [judgement] |
| 24 | Companion stat panel (rule-less route) | Top-right 280x155: "SuperTime Envoy / Classic NG+0", Power / Speed / Guard / Jump with level, grade, progress bars, `LEVEL UP!`, "White drives found" | `E:hud.lua:23-51`, called `retail_app.lua:309` | A retail run with `rules` off, which is the code default (`classic.lua:31`; set on only by `retail_app.lua:111,155`) | P in its own mode | `envoy rules on` replaces it | **ASK** (Q11): it is a different mode's HUD |
| 25 | Companion tag panel and labels | Top-left panel 4 s with the foes' leading stat, plus a label over each opponent; "GUARD" bubble over the player; `<>` pickup glyphs | `E:retail_app.lua:311-329`, `hud.lua:52-57` | Rules-off route | P/D | hidden when the rule host runs (`retail_app.lua:311`) | Same as #24 |

### 1c. Engine and LAB overlays

| # | Name | Looks like / where | Drawn at | Shows when | For | Switch | Rec |
|---|---|---|---|---|---|---|---|
| 26 | FLY readout | Dark panel bottom-left, 300 px: `FLY P1  x -200.0  y 60.0  speed 2.00  attack off  #0`, one line per flying port | `PL:gw_console.cpp:538-567`, text built `PL:gw_script.c:2468-2492` | Offline match, a fighter in debug flight (F11 or `fly`) | D | `fly readout off` (`gw_script.c:2412-2415`); off in netplay/rollback | **HIDE BY DEFAULT**, behind the developer switch. Seen: `frozen-k/shots/flame1.png` |
| 27 | LAB corner icon | Small amber (paused) or teal chip with a bracket icon, bottom-left, 24x18 | `LAB:1224-1232` | LAB scene, mode CLEAN | D | `lab mode`, TAB, `H` hides all | **HIDE**; LAB-only. Seen: `frozen-k/shots/fan1.png` (amber), `flame1.png` (teal) |
| 28 | LAB bottom strip | Full-width bar at y 456: mode name, key chips, toggles, `f 1234 rewind 3.2 s`, "mode TAB", "help F3", `PAUSED` | `LAB:1233-1273` | LAB scene, any mode except CLEAN. **Default mode is HITBOXES** (`cfg.mode = 2`, `LAB:229`) | D | `lab mode clean`, `H`, `always` setting | LAB-only; fine in the LAB |
| 29 | LAB overlays by mode | Hit/hurtboxes, hitbox labels and data, ECB, swept boxes, frames timeline, stage collision, skeleton, info panel, event log, launch arc and knockback "check real hits" lines, A/B ghosts, input display, frame advantage, combo DI fan | `LAB:5097-5136` and the mode tables `LAB:56-216` | LAB scene only (`cfg.on = cfg.always or gd.lab_request()`, `LAB:261`) | D | mode keys | LAB-only. Not in an Envoy retail run unless `always` is saved [judgement: check the saved LAB settings] |
| 30 | LAB notice and help panels | Centre-bottom notice (y 420), F3 help panel, F4 perf panel | `LAB:1215-1222, 1275-, draw_perf` | On request | D | F3, F4 | LAB-only |
| 31 | Show FPS / Performance graph | Kit panel with frame rate or a frame-time graph | `PL:shim_vi.c:1374-1388`; setting at `src/melee/gm/gmfrontend_settings.inc:187-199` | Setting "Show FPS": default Off; suppressed inside a LAB match | P option | Settings screen | **KEEP** as a player option, off by default. Not seen in any capture |
| 32 | F9 panel, toast, run label | F9: frame count, files, scene string, pad state. Toast (2.5 s): "controllers recalibrated", Slippi lost reason. Run label: only while the F9 panel is open | `PL:gw_overlay.cpp:391-470,531`; `src/melee/gm/gmscene.c:716-718` | F9 pressed; toasts on their events | D | `MELEE_OVERLAY=0` (`gw_overlay.cpp:76-82`) | **HIDE** (already F9-gated). The run label also sets the window title "Melee PC - build / sf-a2" (visible in every capture's title bar, not in the game picture) |
| 33 | Console | Dark drop-down over the top of the screen | `PL:gw_console.cpp` (backtick key) | Backtick; log shows it opened once in `frozen-j/.../envoy-play` | D | backtick, ESC | **HIDE** (already key-gated) |
| 34 | Mouse cursor | Kit cursor | `PL:gw_console.cpp:497-520` | Only after the mouse moves | R/D | none | Fine |
| 35 | "Connect a controller" panel | Centre panel, "The keyboard is for hotkeys only." | `PL:gw_console.cpp:462` | No controller connected | P | none | **KEEP** for players; in the captures it appeared because the agent runs had no pad (see section 3). Seen: `envoy-fx/shots/h_start.png`, `envoy-synergy-fx/shots/r1_burn_assembled.png` |
| 36 | Watchdog, netplay stats, profiler | No on-screen text found; they log (`prof:` lines) or exit. Ping shows in the online lobby UI only | grep of `PL:gw_console.cpp`, `gw_overlay.cpp`, `gw_netplay.c` | n/a | D | n/a | Nothing to hide |

### 1d. Retail game (not ours)

| # | Name | Looks like / where | Rec |
|---|---|---|---|
| 37 | Percent and stock icons | Bottom: big `0%`, the fighter's stock heads above | R: leave |
| 38 | Match timer | Centre top `04:21 04` | R: leave (our banners must not cover it: #4, #8, #10) |
| 39 | `P1` / `CP` name tags | Arrow tags over fighters | R: leave |
| 40 | Off-screen magnifier bubble | Round bubble with the fighter's face and an arrow at the screen edge when the fighter is off screen. Seen: `frozen-k/shots/flame1.png` (top-left, Mario flying), `envoy-fx/shots/echo_1.png` (right, Fox) | R: retail behaviour, leave |
| 41 | Retail results screen | "Special Bonus", score. Seen: `envoy-fx/shots/g3_after_ko.png` | R: leave (but see #19) |
| 42 | Retail develop-mode displays | None are drawn in this build: the port's only DevText boxes are the loading screen and the F9 panel (`src/melee/gm/gmscene.c`) | none |

## 2. The same list, grouped the way you would see it

### 2a. Probably what you mean by "debug UI", most likely first

| Rank | What you would point at | Where on screen | Capture to look at | Rec |
|---|---|---|---|---|
| 1 | Small gold text under the top-left bar ("Build ready", "Collect the drives (29 s)", "Iron Resolve!") | Just under the bar | `envoy-fx/shots/g_hold_0.png`, `g3_near_0.png`, `drop_gb_0.png` | REMOVE (#2) |
| 2 | The numbers `+34%` and `Depth 0` in the bar | Top-left bar, right of the squares | `envoy-synergy-fx/shots/r2_fight_a.png` | MOVE to bag (#1) |
| 3 | Wide opponent panel with `(opponent strength 1.4)` and modifier lines | Across the whole top, covers the timer | `envoy-synergy-fx/shots/r2_plate.png` | SHRINK / MOVE (#10) |
| 4 | Wide announcement panels (Fifth slot unlocked, Keystone allowance, Drive tier, Technique text), stacked in time for up to 18 s | Top-centre | `envoy-synergy-fx/shots/r2_burn_p1.png`; log frame 126075 | MOVE (#4) |
| 5 | Error/teaching text in the same panel titled "Technique" ("Build update refused", "Technique rule fired: ...") | Top-centre | log `uxdump: hud toast: Technique` | HIDE errors (#5) |
| 6 | Bottom-left bar "FLY P1 x y speed attack off #0" | Bottom-left | `frozen-k/shots/flame1.png` | HIDE BY DEFAULT (#26) |
| 7 | Small teal/amber corner icon and, in other modes, the long bottom bar with key chips | Bottom-left / bottom | `frozen-k/shots/fan1.png`, `flame1.png` | LAB-only (#27, #28) |
| 8 | "Modifier LAB" text box (ids, last chain) | Top-left over the bar | `envoy-join/shots/strip_169_a.png` | Hidden in runs already (#21) |
| 9 | Hitbox / hurtbox, labels, timelines | Over the fighters, bottom | none of the Envoy captures; LAB only | LAB-only (#29) |
| 10 | The strip left on the retail results screen | Top-left over "Special Bonus" | `envoy-fx/shots/g3_after_ko.png` | FIX (#19) |

### 2b. Real information, but too much during a fight

| What | Where | Why | Rec |
|---|---|---|---|
| Drive-collection duplicate (#2 + #8 + #9: three signals for one message) | Top-left, centre, floor | Same message three times | Keep banner + arrow, drop text |
| Pickup card "A drive dropped!" then "Picked up" then "Merged!" | Bottom-centre | Inventory spam | One line toast; merge to bag |
| Opponent panel (#10) | Across the top | Covers the timer and tags | Small card |
| Crit impact frames (#13) | Whole screen | Not ruled; very heavy when strong | Q7 |
| Synergy pill counter (#11) | Next to the bar | Small; probably fine | Keep |

### 2c. Keep

Link flashes (#12), crit tracer (#14), earned afterimage (#15), fighter tints (#16), floor-drive effects (#17), "Collect the drives" banner (#8, moved) and drive arrow (#9), synergy pill (#11), the bar's squares and keystone cells (#1), Show FPS as a player setting (#31), "Connect a controller" (#35), all retail HUD (#37-41).

## 3. What came from how the sessions were launched

| Item | Appears because of | What a normal player's launch shows |
|---|---|---|
| Build bar, strip flashes, banners, plate, synergy pill (#1-#18) | `envoy rules on` + `envoy classic [fighter]` sent to the console port by every play script (`frozen-k/play-crit.sh`, `play-falco*.sh`, `envoy-synergy-fx/play.sh`: `cmd.py 51997 "envoy rules on" "envoy classic ..."`). The run host is only on that way: code default `rules=false` (`E:classic.lua:31`; set true at `retail_app.lua:111` for the command and `:155` for developer starts) | Starting from the Envoy menu draws the older companion panel (#24-#25) instead of the bar [code]. Which of the two you intend players to see is Q11 |
| Modifier LAB box (#21) | An early run before the hide-in-run commit (`857266985`, Oct 5 01:57); capture `strip_169_a.png` is 01:45 | Hidden in a rule-host or co-op run [code] |
| FLY readout, LAB icon and strip, hitbox overlays (#26-#30) | `play-fd.sh` mounts the geno-lab mod (`mods-lab/enabled.txt`: geno-lab) and sets `MELEE_SCENE="mode=lab;..."` for effect work; Envoy play scripts mount only `envoy` + `envoy_drives` (`frozen-k/mods/enabled.txt`) | No LAB overlays outside a LAB scene (`cfg.on` needs `gd.lab_request()`), no FLY bar unless a fighter flies. Unknown: whether your own mods folder (`_build/runs_gd/mods-all` lists geno-lab) has a saved LAB `always` setting; check once |
| "Connect a controller" (#35) | Unattended agent runs with no pad (`run.sh --test` sets `MELEE_UNATTENDED=1`, `MELEE_PAD_IGNORE_ADAPTER=1`) | Only if no controller is plugged in |
| Run label in the window title | `run.sh` sets `MELEE_RUN_LABEL="$lane / $name"` (`tools/port/run.sh:106`) | Plain "Melee PC" title; label never in the picture except with F9 open |
| Console open in the log | A tester opened it (`MELEE_CONSOLE_PORT=51997` only opens the command port; the overlay needs backtick) | Closed |
| Window size, widescreen | `run.sh` sets 1920x1080, scale 3, widescreen 1 | Player settings |

## 4. Proposal: one switch

**Name:** "Developer overlays" (setting `dev_ui`, default **off**).
**Turn on:** Settings screen entry (Advanced), console `devui on|off|status`, environment `MELEE_DEVUI=1` (wins over the setting). Persisted like the other settings (`gw_Settings_Int("dev_ui")`).

**Covers (when off, none of these draw):**

| Element | How |
|---|---|
| FLY readout (#26) | Engine gate: draw only if `dev_ui` or a LAB match; `fly readout` stays as a finer control |
| Modifier LAB box (#21), Drive LAB card (#22) | Mod checks `gd.dev_ui()` |
| Error toasts (#5 errors: "Build update refused", "A keystone was removed") | Mod sends to the log only; player-relevant ones (a drive moved to the bag) get plain wording through the new corner toast |
| Strip flashes and modifier-fire flash (#2, #3) | Mod: draw only with `dev_ui` |
| Strength % and Depth in the bar, "(opponent strength n)" in the plate (#1, #10) | Mod: shown only with `dev_ui` (they stay in the bag) |
| LAB corner icon and bottom strip (#27, #28) | LAB mod: in the LAB, mode CLEAN shows nothing unless `dev_ui`; default mode becomes CLEAN (`LAB:229`) |
| Console, F9 panel, run label | Already key-gated; unchanged. F9 and backtick keep working |
| Strip over the retail results screen (#19) | Plain bug fix, not behind the switch |

**Not covered (player options, stay under their own settings):** Show FPS (#31), retail HUD, link flashes, tracers, tints, drive effects, "Connect a controller".

**Where implemented (spec, no code):**
- Engine: `PL:gw_settings.c` key and env override; a `gd.dev_ui()` Lua function in `PL:gw_script.c`; the `devui` console command; the gate in `PL:gw_script.c:2473` (`gs_fly_text_update`).
- LAB mod: `LAB` reads `gd.dev_ui()` in `draw_strip` / default `cfg.mode`; hitbox, frames and launch overlays are the LAB's purpose and stay as they are inside a LAB scene.
- Envoy mod: `E:run_hud.lua` (flash list, strength/depth text), `E:foe_lab.lua` (strength figure), `E:mod_display.lua` / `E:drive_lab.lua` (boxes), `E:run_host.lua:46` (route mod toasts by kind: teaching, error, player).
- Agent runs set `MELEE_DEVUI=1` in `tools/port/run.sh` so probes keep their overlays.

## 5. Questions for you (taste decides)

| # | Plain-language question | Suggested answer |
|---|---|---|
| Q1 | The top-left bar shows four little squares, then `+34%` and `Depth 0`, then a lettered box. Keep the squares and the letter box, and drop the percent and depth (they are in your bag)? | Yes |
| Q2 | The small gold words under that bar ("Build ready", "Keystone: Iron Resolve", "Collect the drives (22 s)"): remove all of them except "Out of bounds"? | Yes, remove |
| Q3 | The wide panel at the top-centre that says "Fifth slot unlocked / Keystone allowance / Drive tier / New Game+": show those on the between-stage screen instead, and keep only the synergy message, as a small card in a top corner? | Yes |
| Q4 | The wide dark panel across the top for four seconds at the start of each fight, listing the opponent's modifiers and "(opponent strength 1.4)": make it a small card in the top-right, or put it on the "get ready" moment? | Small top-right card, no strength number |
| Q5 | The card at the bottom-centre when a drive drops ("A drive dropped!") and when you pick one up: drop the "dropped" card and show pickup as a one-line note in a corner? | Yes |
| Q6 | The orange emblem box with "x5" beside the top-left bar (assembled synergies and chain counter): keep? | Keep |
| Q7 | The full-screen streaks and blur on a crit: keep it for strong crits only and use just the glow trail for small ones? You only ruled on the text pop-up | Strong crits only |
| Q8 | The "Collect the drives 29 s" banner under the timer covers the timer digits: keep it, moved lower? | Keep, moved |
| Q9 | The bottom-left bar "FLY P1 x ... y ... speed ..." and the small corner icon in LAB scenes: show them only when a developer switch is on? | Yes (LAB shows them when its own mode asks) |
| Q10 | One developer switch for all of the above (section 4), off by default, on for agent test runs? | Yes |
| Q11 | A run started from the Envoy menu (not the console) shows an older panel top-right ("SuperTime Envoy | Classic ... Power Speed Guard Jump"). Which of the two HUDs should a player get from the menu? | The new bar; the old panel is for the stat-companion mode only [judgement; this needs your call] |

## 6. What I did not do or could not confirm

- No live check: nothing was launched. Captures are earlier lanes' stills; no capture shows the Envoy run with the geno-lab mod mounted, so the "LAB overlays appear in a normal run" case is only known from code (`cfg.on` and `gd.lab_request()`).
- The saved LAB settings of your own folder (`always`, `perf`, `mode`) were not read.
- `E:hud.lua`'s pickup glyph function is called from the legacy app route only (`app.lua:128`).
- Companion-route captures were not found; #24-#25 are code only.
