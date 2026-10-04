# Rules for jobs running in parallel (2026-10-04)

Several Codex jobs are editing this workspace AT THE SAME TIME, at the owner's request. Every parallel packet includes
these rules by reference.

- Workspace root is two levels above this file; game checkout `melee/`. Read `CLAUDE.md`, `melee/CLAUDE.md`, and the
  per-directory `CLAUDE.md` of whatever you touch.
- Both trees are deliberately dirty. Do NOT commit, reset, stash, revert, checkout or reformat. Do NOT run
  `tools/port/build.sh`. Do NOT launch the game. Keep every file compilable at every save.
- **Stay in your lane.** Your packet names the files and directories you own. Put new code in NEW files. Do not edit
  another job's files; if you need something there, write the request in your report instead.
- **Shared files** (`melee/pc/platform/gw_script.c` registration tables and includes, `melee/pc/gameworld/script_game.c`
  includes and frame hooks, `_build/melee_link_objects.rsp`, `docs/scripting.md`, `docs/shaders.md`, the demo catalogue):
  touch them LAST, once, with the smallest possible edit, re-reading the file immediately before you write, and never
  rewrite or reorder what is already there. If the file changed under you, re-read and re-apply; never overwrite.
- Do NOT regenerate the Envoy or missions bundles (`tools/port/envoy_bundle.py`, `missions_bundle.py`) and do not edit
  anything under `melee/pc/scripts/examples/envoy/` unless your packet says the Envoy mod is yours: the integrator
  regenerates bundles after all jobs finish.
- Other jobs running now: Envoy balance and opponents (owns the Envoy mod and the hit rules in `ftcoll.c` /
  `script_hit_rules*`); afterimages and tracers (rendering, new files); fighter capabilities (fighter values and
  restrictions); stage teardown (`melee/src/melee/gr/`, `pc/gameworld/script_stage_slot*`); roster registry
  (m-ex slot tables); small defects (aspect wedge, slot 6, demo catalogue).
- Do not stop to ask for design approval: the owner approved running these. Record your choices, and anything you could
  not do, in your report. Never fake a capability.
- Nothing you add may leak a disc path or a machine path into logs, docs or tests.
