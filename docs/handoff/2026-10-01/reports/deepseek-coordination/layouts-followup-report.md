I'll address the review defects systematically. Let me re-inspect the current code sections I need to change.

Now I'll replace the entire directed-screen and signature section:

Now I'll correct the documentation to remove the overclaims and reflect the fixes.

Let me strengthen the test to catch the interior-seam ledge regression directly.

Corrective review addressed. Stopped editing; all changes are in the isolated lane.

## Fixes

**1. `combat_flank` interior seam ledges** — `room_recipes.lua` adds `seam_platform` (one-way, `ledges=false`) and uses it for both walkway bays (every edge meets a ramp at ±26 or the other bay at 0). Reviewed four recipes and `ASCENT_MODULES` remain byte-for-byte unchanged. `test_room_layouts.py` now derives all platform/floor/ramp seam edges and requires `ledges=false` on any shared edge; I verified it fails on the pre-fix geometry and passes after.

**2. Mobility screen** — `screen` now seeds **only the actual arrival surface** (`spawn`, or `opts.entry`), never every floor; requires **every required surface, every non-drop anchor and every drop edge** reachable; and refuses non-finite geometry (NaN/inf) via `geometry_finite` plus finite checks in `can_traverse`/`traversal_surfaces`. New negative regressions all refuse: `shortcut_zero`, `crossing_zero`, `raised_unreachable` (platform y=60), `nan_platform_y`, `inf_line`, `entry_off_surface`.

**3. Honest geometry diversity** — replaced the metadata signature with `geometry_signature`: movement geometry only (floor span, openings, platforms, slopes, module placements), ignoring camera/spawn/arrivals/socket names/shape/theme and normalised by translation. `audit()` now reports **16 geometry-distinct of 29 templates** (the old "19" was a signature count). `branch_y`/`rejoin_merge` alias honestly as the same ascent surface.

**4. Theme contracts** — `topology.lua::add_room` honors `template.theme or assigned`; routes still validate. `test_topology.py` asserts across 100 seeds: **327 themed rooms, 0 mismatches** (was 218). `topology.lua`/`test_topology.py` are flagged as this lane's per the review for root to review separately.

**5. Corrected claims** — `docs/ROOM-LAYOUT-EXPANSION.md` now states every new layout keeps the full ground route with optional raised ledges (no mandatory elevation), and that the three themes are composition/encounter contracts over one BF atlas, **not** visually distinct art.

## Frozen files
Game worktree: `room_catalogue.lua`, `room_recipes.lua`, `rooms.lua`, `topology.lua`. Wrapper: `tools/roguelite/test_room_layouts.py` (new), `tools/roguelite/test_topology.py`, `docs/ROOM-LAYOUT-EXPANSION.md`. `main.lua`, `prepare.py` and the seeded dirty baselines were not touched.

## Evidence
`test_room_layouts` 5/5; `test_room_recipes` (29 templates, uncertified); `test_catalogue`; `test_rooms` 13/13; `test_topology` (1000 seeds, 647 signatures, theme contracts); `test_route`, `test_adapter`, `test_progression`, `test_checkpoint`, `test_dungeon`, `test_legacy`, `test_route_map`, `test_integration_edges`, and physical/encounter/reward suites all pass. Discovery remains 120 tests with the same 6 pre-existing unrelated errors.

## Remaining limits
No recipe is certified; no native build/run/screenshot/replay exists in this lane. Themes are not distinct art. Ledge grabs, body clearance, knockback, camera/blast bounds and real fighter mobility still require root's normal-speed native replays.