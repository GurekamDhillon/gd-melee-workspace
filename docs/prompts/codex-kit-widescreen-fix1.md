# Packet D follow-up: widescreen menus, after the integrator's on-screen check (2026-10-03)

Your widescreen change is built (clean build, 227/227) and verified on screen: round elements measure 1.02-1.03 at 4:3, 16:9
and 21:9; native screens and the HUD are pixel-identical; the VIDEO row toggles live and persists. Good. Same rules as before
(no commits/reset, no build, no game launch, keep files compilable; another Codex job is working in `melee/pc/platform/gw_script*`,
`melee/pc/gameworld/`, `melee/src/melee/cm/`, `melee/pc/geno/`: stay out of those). Evidence and proposed patches:
`_build/audit-20261003/menus-art/patches/05-*.diff`, `06-*.md`, `07-*.md`; screenshots `_build/audit-20261003/menus-art/shots/f_a169`,
`f_a219`, `f_b219`, `f2_long.png`, `crop_strip169.png`.

Fix, root cause each:
1. A stranded teal accent bar mid-strip in the description strip on list-type pages in wide modes (VIDEO, CONTROLS, ONLINE
   PLAY, MATCH SETUP). The widening at `gmfrontend_player.inc` ~1826-1850 grows quads by id (`desc_strip`, `footer_strip`,
   `desc_strip_*`, `header_rule`, `band_*`); this quad has another id (probably built in `gmfrontend_kitlist.inc`). Find it and
   anchor it to the strip's real right end. Prefer making "anchored to the canvas edge" a property of the quad rather than a
   growing list of names.
2. Full-bleed chrome does not reach the real edges at 16:9/21:9: description and footer strips start ~4% in from the left and
   stop ~7% short on the right (hubs) or uneven (lists: description reaches, footer stops ~8% short); the header rule extends
   only to the right. Decide from `docs/ART-BRIEF-menus.md` what each is meant to do and make left and right consistent on every
   screen type. State the rule you implemented.
3. Mods help text still cuts mid-word with no ellipsis: `fsm_help[FSM_MAX][FE_STR]` (`gmfrontend_settings.inc:454`, `FE_STR` 80
   in `gmfrontend.c:230`), and `help_str`/`label_str`/`value_str` (`gmfrontend.c:644-646`) share the limit. Make every
   description path let the fit rule (ellipsis) do the cutting; audit every `FE_STR` buffer that can hold a description.
4. Owner decision: widescreen defaults to ON when the window (or desktop) is wider than 4:3, unless the user has saved a
   choice. An explicit saved `widescreen=0` must be respected. `tools/port/run.sh` currently forces `MELEE_WIDESCREEN=1`: leave
   run.sh alone, but say in the report whether it is still needed.
5. A scroll cue on kit lists that have more rows than fit (SETTINGS has a hidden tenth row, ERASE DATA; Special Melee and
   Multi-Man also scroll). The brief asks for one; use existing kit art if there is a suitable piece (18 unused textures are
   listed in the audit, do not invent art), otherwise a plain drawn indicator in the kit's style.
6. Log the canvas width on every change including back to 640 (only the widescreen-on line was seen).
Tests where the suite has a pattern. Report: `_build/tmp/codex-kit-widescreen-fix1-report.md` with file:line, the edge rule,
and an on-screen test plan.
