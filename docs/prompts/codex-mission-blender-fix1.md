# Packet C follow-up: exporter and kit collision after the first in-game runs (2026-10-03)

18 game runs on the vanilla disc. Evidence: `_build/audit-20261003/mission-verify/` (`logs/`, `patches/`, `work/`, `kit/`).
Same rules as before (Python only, your files only, no build, no game, no commits). The integrator has ALREADY applied
`patches/03a`, `03b`, `04`, `05`; after that `python -m unittest tools/blender/test_gd_mission.py` has 3 failures: bring the
tests in line with the measured truth below (do not revert the patches).

Measured in the game:
1. Wall winding was inverted: `solid_outline` (`export_kit.py` ~65-73) put `right_wall` on a block's left edge and `left_wall`
   on its right edge; fighters walked into walls and stopped at the far face from inside. With the kinds swapped and endpoints
   reversed (patch 05) walls stop fighters from outside on both sides and `gd.player().wall` reports the correct side. Doorway
   and window jambs had the same inversion: check every wall-type line in the kit against this rule and state the rule.
2. Floor undersides broke pass-through platforms (a hop under Floor_4m stopped at y=39 with `ceiling=1` instead of reaching
   61.5 and landing on top). Patch 05 removed the underside ceilings from Floor_4m, Floor_2m, Balcony, Floor_Opening. A floor
   therefore no longer acts as a room's ceiling: add an explicit way to author a solid ceiling (a kit part or a per-instance
   property `gd_solid=true` that emits the underside for that instance only), validated and documented.
3. The doorway is a sealed pocket in 2D: solid blocks on both sides up to y=26 and a lintel; a fighter cannot walk through.
   A side-view game needs a doorway that is passable along X: redefine the doorway (and window) collision for the side view
   (no jamb walls in the gameplay plane; lintel as ceiling above head height only if the opening is taller than a fighter;
   state the clearance you assumed, using fighter heights from the game data referenced in the notes), and document how a
   door that blocks until opened is authored (a separate blocker marker), without implementing door logic.
4. Content-hash mesh names were 64 bytes; the engine allows 48-character basenames (patch 03a/03b shortened them: confirm
   collision resistance is still adequate and the validator enforces 48).
5. `MAX_LINES` raised to 64 to match the engine (patch 04): make the validator message name the limit.
6. Reload cost: each chunk folder gets its own copy of the kit's colour and glow atlases (11.2 MB per copy) and every export
   rewrites them, so the engine pins a new asset generation each time and its 64 MiB budget is gone by the third export.
   Write ONE shared atlas per mission (in `models/`), reference it from chunks, and never rewrite a file whose content is
   unchanged (compare content hash; keep the old file and its modification time). Add a validator estimate of the mission's
   pinned asset memory with a warning near the budget.
Report: `_build/tmp/codex-mission-blender-fix1-report.md` (what changed with file:line, the wall/ceiling/doorway rules as
implemented with a per-part line table, tests, and exactly what the integrator should re-measure in the game).
