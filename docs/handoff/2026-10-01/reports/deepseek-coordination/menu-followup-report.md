I'll work through the nine review defects, fixing owned files only. Let me start with the simpler ones and re-read the current state.

Now replace the rail block with a layout-scaled version:

Now fix the assignment injection defect in `commands.lua`:

Now fix the menu confirmation identity binding:

Now update the wrapper tests with adversarial cases for each defect.

Now the docs wording fix and review notes:

All nine review defects are fixed in the seven owned files, with adversarial real-module tests added.

## Fixed (defect → change)
1. **Onboarding cast hint** (`onboarding.lua`) — now "Left / Right / Down on the final branch casts the ability"; no longer says press A. Test asserts no "press a" and presence of the D-pad text.
2. **Stale discard confirmation** (`menus.lua`) — `M.new`/`M.reset` carry `pending`+`gen`; prompts are bound to action id/slot + menu/section + generation. Reset, selection change, page change, section change and map selection invalidate it. Adversarial test: prompt g1 → select g2 → click discard re-prompts (not discards g2); two fresh presses needed; reset also invalidates.
3. **Fallback opponent nil label** (`feedback.lua`) — uses `enemy.label or 'OPPONENT'`.
4. **Partial assignments** (`commands.lua`) — `assignment` reconciles a partial map into a permutation of the allowed set, filling missing directions in stable order; unknown/repeated values and unknown direction keys are refused. Tests cover `abilities.left='guard'` and `root.left='special'` yielding all nodes exactly once.
5. **`Commands.install(state,nil)` mid-branch** (`commands.lua`) — both install and restore now reset cursor to root and clear `previous`/`up_latched`/`chord` before `C.view`. Tested from `node='abilities'`.
6. **HUD draw ignores layout** (`feedback.lua`) — with a layout, rail/notification boxes come from `layout.rail`/`layout.notification` and all metrics scale by `layout.scale`; fallback also scales. Test records real `gd.fill` coords and asserts the rail box equals `layout.rail` (h=122 at dpi 2, not 61), the notification equals `layout.notification`, and it sits inside the declared safe area. Compact rail draws only when `replace_vanilla=true`.
7. **Supplies 0** (`commands.lua`) — declared `items.restore=0` or `supplies=0` yields blocked "No supplies", never enabled "Restore x0"; declared counts validated.
8. **Legacy API compatibility** — default tree, no-layout draw path, and all existing functions/fields preserved; `test_commands`, `test_menus`, `test_feedback`, `test_route_map` pass unchanged.
9. **Docs** (`MENU-POLISH-CONTRACT.md`) — native checks now stated as pending/root-exclusive and human-unverified, not a Windows/disc constraint; plus a review-follow-up section.

## Frozen files (unchanged list)
Game: `commands.lua`, `feedback.lua`, `menus.lua` (modified), `hud_layout.lua`, `onboarding.lua` (new). Workspace: `tools/roguelite/test_menu_polish.py`, `docs/MENU-POLISH-CONTRACT.md`. `main.lua`/`prepare.py`/bundler/art untouched.

## Results
- `test_menu_polish` 6/6; focused set (`commands`, `menus`, `feedback`, `route_map`, `menu_polish`) 14/14 pass.
- Full discovery: 120 tests, 4 errors, 6 skipped — the same pre-existing missing generated art assets (`menu/out_effects_study`, `menu/out_roguelite`), no owned file involved.
- `luac -p` clean; `git diff --check` clean. No commits/builds/installs.

Ship main hooks still pending: `main.lua` must call `Commands.loadout`, pass a truthful `Hud.layout`/`new_hud` into `Feedback.draw`, drive `Onboarding.observe`, and open the new screens. Native and human acceptance remain unverified.
