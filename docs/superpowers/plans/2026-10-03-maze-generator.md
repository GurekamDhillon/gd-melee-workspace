# Maze generator implementation plan

Spec: `docs/prompts/codex-maze-generator.md` (owner requested execution).
Goal: stitch authored chunks into a continuous, validated mission maze.
Architecture: pure Lua generator and independent checker; Python calls Lua rather
than duplicating generation. An in-memory file overlay uses the existing loader.
No commits, builds, game launches, C edits, Envoy edits or checkout cleanup.

- [x] Write failing Lua/Python contracts for deterministic output, injected RNG,
  1,000 seeds, directed traversal, sealing, overlaps, budgets and loader acceptance.
- [x] Add data-only chunk recipes, pure generation, serialization and checking.
- [x] Add Python materialization with explicit kit asset input, and a narrow loader
  overlay/console extension; regenerate only the missions entry.
- [x] Add Blender exit-marker collection/validation/export without changing assets.
- [x] Run focused existing suites, inspect ownership diff, document contract,
  starter table, limitations and native acceptance in the requested report.

Decisions: use explicit collision wall/floor/ceiling seals. Climb certificates
reference physical platforms at gaps <=24 (full hop measured about29); drop links
are directed. Main path length defaults to ceil(0.7*size). Reward dead ends use
existing message triggers as hooks, not an invented inventory system. Enemy budgets
are metadata and actual placements, capped at64 total and32 per wave.

Review focus: RNG bounds; mismatched slots; invalid/removed climb platforms;
retry/reroll during respawn; missing model assets and preservation of old mission.

Final ledger: fix3 prompt update requires130x104; old120x100 defaults superseded.
Reviewer findings corrected: preserve authored traversal/capability, include all
library models and glow, and stage the complete requested output before rename.
49 focused tests pass;32 Lua/19 Python syntax checks pass; current bundle and
fresh preview folder proof pass. Second review found no important issues.
No builds, game launches or commits. Native traversal remains for the owner.
