# Packet C follow-up 2: exporter (2026-10-03)

Round 2 in the game passed everything the exporter produces. Same rules as before (Python only, your files, no game, no
commits). Two additions:
1. Every placed part in `level.lua` and chunk level files carries its Blender object name as `name` (sanitised, unique within
   the mission; duplicates get a suffix) so the runtime can label instances for contact traces (`Wall1`, `PassPlatform`...).
   Today all walls of one kind are indistinguishable in traces. Validate uniqueness and length.
2. Camera authoring per section 8 of `docs/superpowers/specs/2026-10-03-mission-folders-and-large-levels-design.md`: a level
   custom property set and a per-chunk override (on the `gd_chunk` rectangle) written into the level file as
   `camera = {mode="follow"|"chunk"|"shaft", window={w,h}, min_dist=, fov=}`; omitted when not set (the runtime has defaults).
   Validate the mode and ranges; add the panel fields plainly.
Tests updated; report `_build/tmp/codex-mission-blender-fix2-report.md`.
