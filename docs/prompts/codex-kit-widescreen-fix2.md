# Packet D follow-up 2: two small menu items after the on-screen check (2026-10-03)

Your follow-up passed on screen (accent bar, edges 0%/0%, ellipses, default, scroll cue, logging). Same rules. A controller
remapping page was added to SETTINGS > CONTROLS by another finished job (`_build/tmp/codex-controls-remap-report.md`): build
on that state, do not disturb it. Evidence: `_build/audit-20261003/menus-art/patches/08-howto-breadcrumb.md`,
`09-description-width-on-wide-canvas.md`, shots `l_sk17.png`, `l_k17/howto_row5.png`, `i_sf14w.png`.
1. Description text keeps its 4:3 width on the wide strip: the text slot is still `max_width_1x` = 474
   (`gmfrontend_kit.inc` ~403), so long lines get an ellipsis while ~40% of the strip is empty. Let the fit width follow the
   canvas (keeping the authored left margin and a matching right margin).
2. "How to Play Online" shows the MATCH SETUP breadcrumb and a "Select / Change / Back" footer on read-only rows, and B goes
   to the SETTINGS list instead of CONTROLS: `fe_screen_howto_online` (`gmfrontend_settings.inc` ~339) is not recognised by
   `fe_is_settings()`.
3. Kit character select and stage select at wide aspects show the sheared section band on the left only: make it symmetric
   or extend it, following the brief.
Report: `_build/tmp/codex-kit-widescreen-fix2-report.md`.
