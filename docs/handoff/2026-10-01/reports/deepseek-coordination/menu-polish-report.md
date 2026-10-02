I'll start by inspecting the workspace, instructions, and the completion plan.

Let me read the rest of the plan and locate the runtime modules.

Now I understand the architecture. Let me set up my task list and start implementing the assigned modules.

Starting with `commands.lua` — additive loadout tree API while preserving the default tree and exported functions.

`commands.lua` done. Now the new `hud_layout.lua`.

`hud_layout.lua` verified. Now `onboarding.lua`.

Now the larger `menus.lua` additions — new screens and confirmations, gated so existing flows are untouched.

All modules updated. Now the wrapper test file.

Now debug the notification program directly:

Now let me wire the HUD layout into `feedback.draw` with an explicit availability gate, preserving the default path.

The map screen needs pagination for real 12–18 room dungeons and must draw its non-room controls. Let me fix that.

Gate 8 work is implemented and tested. Summary below.

## Frozen files (frozen; no further edits planned)

Game checkout `melee/worktrees/linux/pc/scripts/examples/roguelite/`:
- `commands.lua` (modified, +144) — default tree and `new/reset/view/update` unchanged; loadout API added
- `menus.lua` (modified, +171) — existing collection/rest/reward/error flows unchanged; new screens added
- `feedback.lua` (modified, +48) — existing priority/coalescing unchanged; `tutorial`/`tell`/layout gate added
- `hud_layout.lua` (new, 142)
- `onboarding.lua` (new, 133)

Workspace: `tools/roguelite/test_menu_polish.py` (new), `docs/MENU-POLISH-CONTRACT.md` (new). Untouched: `main.lua`, `prepare.py`, `core.lua`, `route_map.lua`, `runtime_*.lua`, all other workers' dirty files, and the seeded baselines.

## API (compatibility-preserving; full detail in the contract)
- `Commands.plan/install/loadout/assignments` build a tree from installed loadout + declared capacities only (3 slots, 2–3 presses, honest empty/blocked entries, validated prep assignments). `A`/`B` events now also carry `family`/`slot`.
- `Hud.layout/aspect/command_expanded/avoids_center` — pure geometry; `replace_vanilla` true only with `new_hud=true`; fallback anchors keep life/damage readable; 4:3/16:9 + high-DPI bounds; command panel avoids the center band.
- `Onboarding.observe/view/toast/set_room/skip/revisit` — D-pad grammar tutored in first rooms, lapses after, `view().pause` always false, genealogy/fusion only when declared.
- `Feedback.tutorial/tell` (coalescing, lifetimes, non-celebratory) and `Feedback.draw{s.layout=...}` gate.
- `Menus` new read-only screens `map/onboarding/settings/ending` via declared `ctx.map/onboarding/settings/ending/capacity`; mouse+controller focus; map paginates and never leaks hidden rooms/rewards; destructive discard needs a second press.

## Results
- `python3 -m unittest tools.roguelite.test_menu_polish -v` → **6/6 pass** (hierarchy, up-mask, root taunt, hold debounce, neutral/chord, open/close, loadout, layout bounds, mouse/controller focus, notification lifetimes, map spoilers, HUD fallback gate).
- Unchanged regressions `test_commands`, `test_menus`, `test_feedback`, `test_route_map` all pass.
- Full discovery: **120 tests, 4 errors, 6 skipped**. The 4 errors are pre-existing missing generated art/export assets (`menu/out_effects_study/manifest.json`, `menu/out_roguelite/*.coll.json`) in `test_runtime.py`, `test_certify_rooms.py`, `test_rooms.py`; none touches the owned files. Art generation is root/Astra-owned and was not run.
- `luac -p` clean on all five modules; `git diff --check` clean.

## Integration requirements (for the `main.lua`/`prepare.py` owner)
1. Call `Commands.loadout(state, run, {...})` after run start / loadout change; `Commands.reset` preserves the installed tree.
2. Build `Hud.layout{...}` and pass with a truthful `new_hud` into `Feedback.draw{s.layout=...}`.
3. Drive `Onboarding.observe` from existing event sites; route `Onboarding.toast` to `Feedback.tutorial`; never pause from onboarding.
4. Add pause-menu entries for `map/onboarding/settings/ending` and populate `ctx.map` from `RouteMap.build()` and `ctx.capacity` from the real collection count/max.

## Unavailable evidence (not claimed)
- No native compile/install/game/controller run or screenshot — root-owned, needs Windows/disc; HUD readability, focus restoration, and real hotplug remain human/native acceptance.
- No new raster art or interactive viewer; only existing `rogue_*` kit roles referenced.
- Until `main.lua` wires the hooks, the new screens/loadout tree are not reachable in the live game.
- No commits/staging performed.
