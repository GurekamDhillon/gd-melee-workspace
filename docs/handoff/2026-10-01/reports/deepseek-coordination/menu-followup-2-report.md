Review follow-up 2 has real geometry defects. Let me first reproduce the dpi2 overlap, then redesign the responsive HUD.

Now update `feedback.lua` to consume the responsive layout, stack the opponent, keep one-line compact notifications, and use inward shadows.

Now the held-Up contract in `commands.lua` — preserve the latch across a tree rebuild instead of fabricating a taunt.

Now update the contract doc for the responsive HUD and held-Up contract.

All residual blockers from follow-up 2 are fixed and regression-tested.

## Reproduced then fixed
1. **dpi2 rail/opponent overlap** — `Hud.layout` no longer caps the rail at `0.62*safe.w` while content scales at full dpi. Each component gets its own clamped scale (`content_scale`, `note_scale`, `compact_scale`) so scaled content always fits its box. At 640×480 dpi2 the rail is now `516` wide (was `362`), the third charge bar stays inside it, and `layout.opponent` is placed right of the rail or stacked fully above it — verified disjoint, e.g. rail `28,334,516,122` vs opponent `28,232,264,78`.
2. **Actual draw bounds** — `Feedback.surface` and fallback anchors now inset their shadows, so every `gd.fill` lies strictly inside its declared rect. The wrapper records real fill/text coordinates and asserts each lies in its owned rail/opponent/notification rect, rail and opponent are disjoint, the third bar is inside the rail, at 640×480 dpi1/dpi2 and 854×480 dpi1/dpi2 — not merely `rail==layout`.
3. **Compact notification spill** — the workbench strip now draws a single line positioned so baseline + caption height fits the strip (`compact_notification`, `compact_scale`); the two-line `ny+30` detail is reserved for the normal notification, whose `note_h` is sized for two lines.
4. **Held-Up across rebuild** — `Commands.install` returns the cursor to root but **preserves** `previous`/`up_latched` (clears only `chord`). Rebuilding while Up is held no longer emits a synthetic taunt; an optional `buttons` arg syncs the exact held word. Regression: press-Up-hold → rebuild → same Up emits no event/mask 15 → release → fresh Up taunts.

## Frozen files (owned only)
`commands.lua`, `feedback.lua`, `menus.lua` (modified), `hud_layout.lua`, `onboarding.lua`; workspace `tools/roguelite/test_menu_polish.py`, `docs/MENU-POLISH-CONTRACT.md`. No `main.lua`/bundler/build/native/game/art/commit changes.

## Results
- `test_menu_polish` 6/6; focused `commands`/`menus`/`feedback`/`route_map`/`menu_polish` 14/14 pass.
- Full discovery: 120 tests, 4 errors (unchanged pre-existing missing generated art assets), 6 skipped.
- `luac -p` clean on all five modules; `git diff --check` clean.

## Remaining
Main hooks are still pending: `main.lua` must build/pass `Hud.layout`, call `Feedback.draw{s.layout=...}`, `Commands.loadout`, and `Onboarding.observe`. Native UI acceptance and screenshots remain unverified until root integration.