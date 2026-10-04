# Acceptance session — 2026-10-01

Guided controller and visual acceptance of the consolidated build, run on the Windows PC with a
controller. This is **human observation**, deliberately kept separate from the automated results
below: a green suite cannot tell you whether damage feedback reads well or whether a menu is
usable with a D-pad.

Related: `INTEGRATION-2026-10-01.md` (integration ledger and its amendment).

**2026-10-02 amendment (see the final completed checks at the end):** the original build pin below describes the first controller session only. The working name is **SuperTime Envoy**. The controller observations and follow-up verification at the end supersede placeholder-label guidance below. A fresh follow-up build has uncommitted gameplay changes; it is not the original commit-only artifact.

## Build under test

Pin every observation to this tree. Anything else is a different result.

| Field | Value |
| --- | --- |
| Game repo | `GurekamDhillon/melee`, branch `integration/2026-10-01/roguelite-100-game` |
| Commit | `378d79b20` ("gw_script: dispatch on_enemy_hit at case 10 to match its producer") |
| Published | equals `pub/pc-port` at `378d79b20` |
| EXE | `_build/melee-pc.exe`, 10,400,256 bytes, built Oct 1 22:48 |
| Link map | `_build/melee-pc.map`, same timestamp (bridge fixpoint input) |
| Workspace | `gd-melee-workspace` `master` `d528d02` |

**The tree is not clean.** Two files in the game repo are uncommitted and are part of what you are
testing:

| File | Nature |
| --- | --- |
| `pc/platform/gw_script.c` | one-line test fix: `test_script_enemy_genes` now expects the natural enemy hit as event `10`, not `9` |
| `pc/platform/gw_mex_bridge.c` | **generated** by `build.sh`; never stage or commit it |

Also uncommitted in the workspace: `tools/port/build.sh`, `build_objects.py`, `test_build_speed.py`
(Windows source selection — `*_linux` shims were being handed to the Windows shim compiler).
Four unrelated `tools/slippi` files are yours and must stay untouched.

## Already established by automation — do not re-verify

| Result | Figure |
| --- | --- |
| Native tests, vanilla NTSC 1.02 | 216/216 |
| Native tests, ACE | 216/216 |
| Bridge fixpoint | passed |
| EXE ABI audit | clean |
| Launcher test suites | both passed |
| Launcher tabs | all four rendered |
| Roguelite pure/stub suite | 251 tests, 1 skipped |

These cover the harness. They say nothing about feel, readability or fun.

## Discs and mods

| Disc | File |
| --- | --- |
| Vanilla | `<GW_ISO_VANILLA file>` |
| Akaneia | `<GW_ISO_AKANEIA file>` |
| ACE | `<GW_ISO_ACE file>` |

Sora's effects run from the mod built at `_build/agents/alpha/sora` (`geno` plus
`geno.v6/v8/v9.slot.json`). Confirm which slot you are actually running before recording fidelity
notes — the versioned slot files are the easy thing to get wrong.

The roguelite is a script mod, not a disc mod: installed script ID `roguelite/main`. Once enabled it
adds a main-menu entry literally labelled **TBD** (a placeholder name, not a defect). From there:
**TBD → Start a run**. Expect that label; do not file it as a bug.

## Walkthrough

For each area: what to do, then what to judge. Record under Observations, never under the
automated table.

### 1. Roguelite movement, room transitions, platform traversal

Enter via **TBD → Start a run**. Judge:

- Does the fighter respond immediately to stick and buttons, or is there input lag you can feel?
- Walking off a ledge — does the drop read as deliberate, or as a bug?
- Room transitions: is it clear a transition happened? Is the seam between rooms visible as a
  pop, a loading stall, or a camera jump?
- Platform traversal: can you stand on every platform you expect to? Do you fall through any?
- Does the route advance on its own, or only when you reach something?

Note any seam where the floor visibly breaks. Stage-seam research recorded human reports of a
snag/pop at all three ascent joins (stairs→balcony, balcony→ramp, ramp→upper landing) — that is
exactly what this area is looking for.

### 2. Enemy combat, damage feedback, boss controls

- Land hits and watch for: hit flash, knockback, damage numbers, sound, controller rumble.
- Which of those are present? Which are missing? "No rumble" is a finding; "it felt wrong" is not.
- Enemies: do they approach, attack, and take damage? Do they die, and does anything acknowledge it?
- Boss: does it have distinct phases or only a health bar?

### 3. HUD, route map, inventory, reward menus — with the controller

This area is about **controller usability**, which is the one thing only you can test:

- Can you move a cursor in every menu using **only** the controller? D-pad and stick both?
- Is the selected item always obvious? Any menu where you cannot tell what is focused?
- Is any text clipped or overlapping at your TV's resolution? Note the resolution.
- Route map: readable? Can you open it mid-run without losing progress?
- Inventory and reward menus: can you equip/discard, and does the choice register visibly?
- Does anything require the mouse or keyboard? That is a finding.

### 4. Save and reload — probe the four known defects here

Two facts to carry: **the keyboard does not play** (0.1.5 made it hotkeys only — controllers play),
and legacy `TBD1` checkpoints default to Falco costume 0.

Do a save/reload cycle and record what actually persisted. Then specifically probe:

| # | Defect | What to do | What would confirm it |
| --- | --- | --- | --- |
| 1 | An earned or exported gene cannot be discarded durably — save validation still requires the historical exported gene to exist in the collection | Discard an earned/exported gene, save, reload | The discard reverts, or the gene is still demanded by validation |
| 2 | Legacy Restore spends an item when native healing refuses; return/readback and rollback ownership are not truthful | Use legacy Restore with no valid heal available | Item is consumed and nothing is restored |
| 3 | V2 Restore persists contradictory inventory and campaign supply counts instead of one transaction | Use V2 Restore, reload, compare inventory and supply counts | Counts disagree with each other after reload |
| 4 | Run history is appended after the durable finish save and can disappear on reload | Finish a run, reload, read run history | A finished run is missing from history |

**Keep all four open until fixed *and* verified.** A pass here means the defect did not reproduce,
not that it is closed — say which.

### 5. Sora's spells, specials, effect fidelity

Using the known working mod setup from `_build/agents/alpha/sora`. Record the slot version you ran.

- Each special: does it animate, hit, and knock back correctly?
- Spell effects: do they read on screen at your resolution? Note any that are invisible, clipped,
  or dropped frames.
- Fidelity is explicitly **open** work — there is no reference to compare against yet, so record
  what you see rather than judging it against an ideal. "Water projectiles look flat at 1080p" is
  useful; "effects are bad" is not.

## Observations

Separate from everything above. One row per observation.

| # | Area | What you did | What you saw | Repro | Severity |
| --- | --- | --- | --- | --- | --- |
| 1 | | | | | |

Severity: **blocker** (cannot play), **major** (feature wrong or unusable), **minor**
(works, reads badly), **nit** (cosmetic).

Note the run directory for anything you want a log from: `_build/runs/<name>/melee-pc.log`.
Read it — this repo's harness has under-reported before, and the log outranks the summary.

## Explicitly not part of this session

- The four defects above stay open until fixed and verified.
- Sora fidelity comparisons and the remaining showcase captures stay open.
- Nothing here closes room certification, controller traversal of unshipped rooms, or
  effects/region integration beyond what you actually observe.

## Controller findings and follow-up ? 2026-10-02

Human reports from `_build/runs/rogue-controller-20261001` are observations, not automated passes. Reproduction frequency and severity have not been independently assigned.

| Area | User observation/request | Follow-up status |
| --- | --- | --- |
| Platforms | Remove elevated-platform ledge grabs; preserve platform scale; raise platforms | Legacy platform widths retained, ledges disabled, tiers raised to 18/36; controller reachability pending |
| Room size | Approximately twice the space based on platform placement | Legacy width 130 to 260, authored doors/spawns/camera/blast margins updated; width interpretation is an assumption |
| Generation | No maze generation visible | Confirmed fixed legacy fallback: production v2 recipes uncertified; admission now diagnoses missing certified roles; no certification claimed |
| Menus | Labels, flow and controls confusing | Primary action focus, readable gene labels, contextual B handling, working-name native menu label updated; controller usability pending |
| Actors | CPU always present; wants maps without CPUs | Legacy collection/exploration use solo LAB with P2 absent; combat explicitly launches VS; generated v2 lifecycle still CPU-host |
| Effects | Custom map draws over shield and Falco laser; custom effects unseen | Cinder loads/attaches/emits; controlled geometry on/off comparison pending; renderer defect not yet established |

### Follow-up verification

- Fresh executable built via `tools/port/build.sh`: 18,827 bridge entries resolve, zero audited bridge ECX/EDX violations.
- Native ACE regression: 216/216, `_build/runs/envoy-native-20261002/melee-pc.log`.
- Focused real Lua legacy scene-lifecycle test: actors actually destroyed/recreated, P2 absent outside combat, damage/run ID/seed/lives/loadout preserved, refused saves and cleanup prevent replacement.
- V2 runtime suite 33/33 after queued scene simulation; generated routes remain test-only certified fixtures.
- Full roguelite suite is undergoing fixture updates for the new scene lifecycle; do not claim full green until recorded here.

Opt-in render diagnostics install with `tools/roguelite/prepare.py --render-probe`. Backtick opens the Lua console. `envoy_map on` / `envoy_map off` toggles geometry while retaining collision; `envoy_fx_probe cinder` or `envoy_fx_probe rime` attaches an owned diagnostic effect without spending genes. Escape closes the console.

Open: real-controller traversal/reachability and menu usability, physical maze authoring and genuine recipe certification, safe generated-v2 solo scene handovers, rendering comparison/root cause, four previously documented roguelite defects, Sora fidelity/showcase work.

### Final verification and live camera feedback ? 2026-10-02

- Full real-Lua suite: **255 tests, OK, skipped=1**. Discovery now records the 12 persistence scenarios as one unittest rather than import-only side effects. Count is not a native acceptance percentage.
- Native ACE suite after falls API rebuild: **216/216**, `_build/runs/envoy-native-falls-20261002/melee-pc.log`.
- Native solo LAB counter regression: expected RED (missing `falls`) then GREEN (one real fall increments once while native stocks stay99), logs `envoy-falls-red-20261002` and `envoy-falls-green-20261002`.
- Controller build opened: `_build/runs/envoy-controller-20261002`, installed script `_build/acceptance/envoy-controller-20261002/mods/roguelite/scripts/main.lua`. Native log confirms script mounted; human reached combat room. This is uncommitted working-tree code.
- User reports camera frames Falco at bottom. Authored legacy camera moved down18: bottom=-18, top=54, same72-unit height. Full real-Lua suite repeated **255 OK, skipped=1**. Running interpreter keeps original bundle until next load; current-room console adjustment supplied. Computer Use helper unavailable (native pipe not found), so no live camera application claimed.
- Matched paused-frame render screenshots confirm custom geometry occludes shield and diagnostic Cinder. Falco laser sample inconclusive; no renderer fix claimed. Evidence: `_build/acceptance/envoy-render-20261002/scripts-data/roguelite_main/render_{shield,falco_laser,cinder}_map_{on,off}.png`. Native probe exited0 and released adapter.
- An exploratory coroutine native handover probe timed out on the paused collection menu; it is not passing evidence. The strict real-Lua handover fixture passes. Native controller feedback is still needed for complete scene-handover acceptance.


### Corrected scale and native maze findings - 2026-10-02

This amendment supersedes the earlier horizontal-width interpretation and renderer follow-up status above.

- User clarified 2x **each grid cell and authored stage geometry**, rather than twice the number of horizontal bays. New layouts use five 52-unit bays, grid26 and asset unit13; map-editor new placement/ghost/reset use uniform scale2 and grid13. Fighter mobility is unchanged. Resolved saved geometry is preserved.
- Historical dungeon_v1.lua restored to the exact historical generator bytes, independently pinned in the legacy regression. The earlier widened unversioned prototype has its own validator; resumed runs do not regenerate either layout.
- New default prototype uses seeded randomized DFS on a4x3 grid, two extra loops, reciprocal compass sockets and real wall/cap collision. The champion guards the sole exit. This is not room certification or completed controller acceptance.
- Full real-Lua suite after scaling/background policy:263 tests, OK, skipped=1. Native ACE suite after hidden-wall API fix and initial background policy:216/216, log _build/runs/envoy-native-render-20261002/melee-pc.log.
- Native hidden-wall regression: RED with the old floor-only flag check; GREEN after excluding only passthrough/ledge bits from wall/ceiling options. draw=false now works for non-floor colliders. Logs envoy-hidden-walls-red-20261002 and envoy-hidden-walls-green-20261002.
- Native maze probe loaded generator3,12cells,14collision handles, no P2 in exploration. Real pad movement stopped at the first wall at x=-54. It reached a champion combat scene, then FAILED while decoding a checkpoint: Lua2M-instruction/50ms callback budget exceeded. Complete handover/return/resume acceptance remains open. Log _build/runs/envoy-native-maze-20261002/melee-pc.log.
- Renderer attempts rejected: moving scenery backward in world Z misaligned perspective and still hid effects. Restored world Z0. Opt-in background viewport compression preserves projection, but native matched screenshots still show shield/Cinder hidden with mapON. Native getter confirms background=true; original viewport depth0..1. No visual fix claimed. Evidence _build/acceptance/envoy-render-after-20261002/scripts-data/roguelite_main.
- Current work: reduce checkpoint serialization/validation cost without changing saved bytes or weakening checks; measure rendered depths and audit actual Aurora depthStencil/pass order. Diagnostic forced depth writes are opt-in only and must not be treated as normal-play evidence.


### Native lifecycle and matched-projectile amendment - 2026-10-02

This amendment supersedes the earlier renderer remedy and native maze failure status above; it does not certify controller traversal.

- Full real-Lua suite:265 tests, OK, skipped1, after single terminal transaction and byte-compatible codec/checksum optimizations. The finish-refusal fixture now rejects write2 (handover then finish), retains rollback/progress/single-export assertions, and asserts the exact write count.
- Native maze final2:PASS and exit0 in `_build/runs/envoy-native-maze-final2-20261002/melee-pc.log`. Real pad movement stopped at x=-54; exploration had no P2, combat retained percent37/id/seed/lives, rest returned to no P2, and terminal exit completed. The isolated fixture queues independent menu/travel actions on separate presentation callbacks; it is engine lifecycle evidence, not controller jump/seam certification.
- Latest build bridge fixpoint:18,827 entries resolve, zero ECX/EDX ABI violations. Temporary background camera/viewport diagnostics removed.
- Explicit opt-in background draw bucket fixes shield and Cinder overdraw without moving authored world Z or enabling diagnostic forced depth writes. Native paired captures show full room art plus shield and custom fire. Earlier viewport-only and camera-mode-only attempts were rejected.
- Corrected laser fixture now waits for the moving Falco projectile kind55, rather than counting its held blaster gun. Exact same projectile id1/age3/position/frame229 is visible mapOFF and hidden mapON. Laser overdraw therefore remains a confirmed renderer defect; work is continuing.
- Final review found reciprocal maze arrival side lost only across deferred solo/combat handovers; same-host travel is correct. Fix and cross-host socket regression are pending.


### Final completed automated checks and controller build - 2026-10-02

This is the latest amendment and supersedes the pending renderer and cross-host arrival claims above. Controller observations remain separate from automated evidence.

- Renderer fixed and visually verified with normal depth writes: full room art, Falco kind55 laser beam/muzzle flash, shield bubble and custom Cinder all remain visible. Exact projectile id1/age3/position/frame229 is identical across mapON/OFF captures. Backgrounds draw after refraction and before native fighters/items/effects. Compressed decorative depth requires scoped fog disable; all viewport and native fog parameters are restored before later draws. Host mixed/static/dynamic/nested-scope tests pass; temporary diagnostics removed.
- Exact final renderer proof: `_build/acceptance/envoy-render-after-20261002/verified-final-render/` contains six decoded PNGs, EXE, matching map, log and hashes. EXE SHA256: `07c659c479800a4c713ed07b0865b0f7ac4f7ac22fe06ed74241194ce8de565f`.
- Full real-Lua suite after reciprocal arrival fix:265 tests OK, skipped1. Cross-host North/South socket coordinates and ordinary Resume default spawn are explicitly checked.
- Final native ACE:216/216, `_build/runs/envoy-native-final-ace-20261002/melee-pc.log`; vanilla:216/216, `_build/runs/envoy-native-final-vanilla-20261002/melee-pc.log`. Both runners exit0/FATAL0.
- Final real native maze:PASS, exit0/FATAL0, `_build/runs/envoy-native-maze-sockets-20261002/melee-pc.log`. Real movement blocks at x=-54; all visited reciprocal arrivals assert exact XY including upper doorway y56. Solo-to-combat preserves37 percent/id/seed/lives; rest has no P2; exit completes successfully. The wall/camera screenshot is `_build/acceptance/envoy-native-maze-sockets-20261002/scripts-data/roguelite_main/maze_wall_camera.png`. This probe separates independent automated actions across callbacks and does not certify human jump traversal or menus.
- Fresh controller bundle: `_build/acceptance/envoy-maze-controller-20261002`; reopen via `launch.cmd`. Normal-speed visible window, real controller input, isolated new script-data folder; prior controller saves remain in their original folder. `build-pin.json` records exact EXE/map/bundle hashes and uncommitted tree status. Starts at the SuperTime Envoy collection; choose Start a run for the new maze. Existing saved geometry is preserved when resumed.

Still open for human acceptance: jump reachability/platform seams, camera comfort, controller menus, enemy/HUD/effect presentation. Room recipes remain uncertified. The four prior durable-discard/Restore/run-history defects and Sora fidelity/showcase work remain open; this is not a 100/100 acceptance claim. No commits or pushes were made in this follow-up.


### Durable discard and Restore transaction fixes - 2026-10-02

This amendment supersedes the four-defects-open statement above for the automated paths listed here. It does not claim controller acceptance or close Sora work.

- Core now permits discarding an earned/exported gene while retaining its finish record: the record clears the live `export` pointer and stores a validated `discarded_export` ID. History migration carries that earned ID forward even though the gene is gone from collection. Regressions cover discard, snapshot/reload and legacy-history migration; existing pre-discard finish records remain valid.
- Both v2 and shipped legacy Restore handlers check native setter refusal and verify the exact post-heal readback. Inventory, the Core supply mirror and v2 route progress commit together. A refused save triggers exact-percent rollback; if native rollback is refused, the game pauses, retains the rollback callback and blocks input until recovery succeeds.
- Finish history is staged before the single terminal checkpoint write. Save refusal restores the pre-finish profile/run snapshot, so retry appends exactly once. History capacity migrates from the old default64 to512 to match Core's finish ledger, preserving existing entries.
- Regressions cover native refusal on legacy Restore, retained and retried native rollback, v2 route/run/inventory checkpoint agreement, and durable run-history inclusion in the finish checkpoint.
- Full real-Lua suite: **266 tests, OK, skipped1** (WSL real Lua5.4). This is stub/integration evidence, not in-game controller verification.
- Refreshed and relaunched the isolated controller bundle after the user confirmed the prior game was closed. Loader log `_build/runs/envoy-savefix-controller-20261002/melee-pc.log` confirms the updated `roguelite/main.lua` mounted; the existing isolated script-data and checkpoint files were preserved. Pin: `_build/acceptance/envoy-maze-controller-20261002/build-pin.json`. This is startup evidence only; no controller input test is claimed.

No commits or pushes were made. Human controller acceptance, room recipe certification and Sora fidelity/showcase remain open.


## Amendment 2026-10-02: physical traversal and widescreen controller refresh

This amendment supersedes the small door-cell layout as the default for new runs. Existing saved generator-3 rooms retain their resolved manifests on Resume. Generator 4 is a physical traversal prototype with continuous 832-unit ground, upper fork/rejoin and an elevated side branch; it currently has no encounters and is not a complete maze campaign. It remains `certified=false`.

Collection/reward menus and the stock fighter picker now use `gd.safe_area()` for shared drawing and pointer coordinates. Free collection breeding/trait-lock controls are removed; Core tools retain their breeding API. Menu previews clone trusted live tables without repeated serialization, preserving runtime aliases. Core decoding uses bounded string chunks. Physical wall artwork alone is translated onto its collision plane; decorative artwork and saved geometry are unchanged. The new local camera follows P1; cleanup restores the native camera.

Native feedback exposed two history defects: the numeric encoder capped indexes at 16, and reloaded history arrays retained string keys, causing duplicate keys on the next append. Both are covered by actual Core/RunHistory round-trip, append-after-reload tests. Discard/save failures retain their detailed refusal reason. Persistence fixtures now exercise confirmed gene discard rather than removed trait-lock buttons, retaining byte-preservation and rollback assertions.

Verification: 274 tests, OK (skipped=1), real Lua. Native `_build/runs/envoy-physical-native-20261002/melee-pc.log` reports 48 models/24 colliders, P2 absent, continuous walk from -390 to 392.365, upper cap at y=130.0001, camera follow and terminal durable success. `_build/runs/envoy-reward-native-20261002/melee-pc.log` passed solo/combat reward/door handovers and completion without the earlier callback-budget/isolation failure. The executable remains SHA256 `07c659c479800a4c713ed07b0865b0f7ac4f7ac22fe06ed74241194ce8de565f`; these changes are Lua/bundle updates.

Controller package: `_build/acceptance/envoy-physical-controller-20261002/launch.cmd`; exact bundle hash and source heads are in `build-pin.json`. The prior controller package and its saves remain available. User observations are distinct from automated evidence: actual jump comfort/all-fighter traversal, camera after respawn, visible effect interactions and full campaign design remain open. Native screenshots confirm floor support and fighter framing; they do not certify the overlay menu appearance or human traversal. No commits or pushes.
