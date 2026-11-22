# Parallel packet P4: small known defects (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md` (read it first). You own only the files each item names; nothing in the
Envoy mod, the hit rules, the stage slots or the renderer's new afterimage/tracer files.

1. **A black wedge on the stage floor at some window aspect ratios** (seen around 1.6, 1.7 and 1.9; fine at 4:3, 16:9
   and 2.25:1). Evidence and a candidate cause: `_build/tmp/codex-arbitrary-aspect-fix1-report.md` and
   `_build/audit-20261003/` (search for "wedge"). Find the real cause in the arbitrary-aspect code (projection,
   scissor, viewport or the widescreen culling margins) and fix it for every aspect from 1.0 to 3.6, with a test that
   computes the visible frustum against the culling bounds across that range.
2. **Slot 6 is hidden after a recycle**: `gd.fighter_recycle` on the sixth fighter slot leaves it invisible
   (`melee/pc/gameworld/script_six_slots.inc`, `script_fighter_bench.inc`). Find and fix; add the fixture.
3. **The demo catalogue is missing the zones demo** (`demo_zones: mod missing from catalogue`, reported by several jobs):
   add it properly in `melee/pc/scripts/examples/demos/` and make catalogue validation pass; check every other
   capability added on 2026-10-03/04 has its single-feature demo listed (zones, warm, hit rules, 1P hooks, fighter
   mods, items, contacts) and report any that do not, without writing demos for another job's unfinished capability.
4. **Tap-jump-off**: write the netplay-safe DESIGN only (no code): how a per-player "tap jump off" control option can
   exist without desyncing rollback (input is remapped before it enters the simulation and both sides agree, versus a
   simulation flag in the match settings), which the port's controls model (`gw_controls_model.h`) supports today, and
   what to build. Put it in `_research/tap-jump-netplay-safe-2026-10-04.md`.
5. **Log hygiene**: `run.sh`, `demo_tour.py` and the harness wrote the disc path into logs, plan files and `run.json`
   earlier (a fix was sent in the hung-game-detection follow-up): verify from the code that no launcher or tool writes
   a disc path anywhere now, add a test that scans a simulated run folder, and list anything still leaking.
Tests for each code item; report `_build/tmp/codex-small-defects-report.md`.
