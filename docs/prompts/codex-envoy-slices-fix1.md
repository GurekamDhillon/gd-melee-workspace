# Packet E2 follow-up 2: after slices 2-4, a run cannot start in the game (2026-10-03)

Same rules (Lua/Python/JSON/Markdown only, your mod and tests, no C, no build, no game launch, no commits). You have just
merged the drive polish; build on that state and regenerate the bundle last.

Integrator smoke test on a clean STAMPED build (native suite 255/256, the one failure is an unrelated test), vanilla disc,
fresh copy of the repo Envoy mod plus the local drive asset mod, fresh profile. Log:
`_build/runs/envoy-smoke2/melee-pc.log` (lines ~421 and ~894-970). Before your slices, on the previous build, a full run
could be started, played and won by the owner.

1. **`envoy start` now fails every time, on the first run and the second.** Sequence in the log:
   ```
   envoy: slices 2-4 loaded; growth, garden and seeded campaigns ...
   envoy: run 1 started
   envoy: boss benched
   mission: maze 569824651 8 waiting for controllable P1 (600-frame limit)
   mission: refused missions/loader.lua:36: cannot list models: path must start with missions/ and contain no traversal, drive or backslash
   envoy: mission request refused or timed out
   mission: stopped envoy fail
   envoy: settled run=1 result=fail one-write
   ```
   The run's first room is now a generated maze (`mission maze <seed> 8`). The loader's catalogue step
   (`missions/scripts/loader.lua` ~31-36: it first looks the folder up in `L.generated` by name prefix, and otherwise calls
   `gd.mod_list(folder..'models/')`) falls through to the file listing with a folder path that is not under `missions/`,
   so the engine's path check refuses it. Either the generated maze is registered under a name that does not match the
   prefix test, or its chunks reference a model folder outside `missions/`, or the starter chunk set has no models in the
   Envoy mod at all (the generator's starter chunks are DATA built from kit piece names and need their models exported by
   the kit: a maze-generator bring-up lane is doing exactly that in its own copy right now, evidence will be under
   `_build/audit-20261003/maze-gen/`). Find the real cause from the code. Requirements:
   - A run must start on a fresh install with NO extra assets: if generated mazes need models that the mod does not ship,
     the campaign falls back to hand-authored rooms that work with what is present, and says so once in the log; a maze
     room is used only when its chunk models resolve. Never let a missing optional piece fail the whole run.
   - A refused room must not settle the run as a FAIL against the player's record: a run that could not start is not a
     run (no age tick, no record entry), and the menu must say why in plain words.
   - Add an offline test that starts a run through the real loader path with a stub that enforces the engine's path rule
     (`missions/` prefix, no traversal, no backslash, no drive), for both the maze room and the authored rooms.
2. **Drive models are reported unavailable although the asset mod is mounted**:
   `envoy: drive models unavailable (model source missing or unreadable: ...\mods\envoy_drives_sa2\models\dri...`. The asset
   mod contains `drive_red|green|blue|yellow|white|purple.gxmesh` with `.coll.json` and `.material.json` sidecars,
   `drive_glass.gxmesh`, `drive_atlas.gxtex`, `drive_atlas.glow.gxtex`, `drive_glass_atlas.gxtex`,
   `drive_glass_atlas.glow.gxtex`. Find which file name the mod asks for that is not there (the polish may have changed the
   expected names or added one), make the lookup tolerant (use what exists, log exactly which file was not found, once),
   and list in your reply any file the integrator must add to the local asset mod.
3. After a failed start the hub must be usable again immediately (the smoke test could issue `envoy start` again and got
   the same refusal, which is right, but confirm nothing is left benched, paused, tinted or modified).
Reply with the cause of item 1 in three lines, file:line, tests; `_build/tmp/codex-envoy-slices-fix1-report.md`.

## ADDED: the cause of item 1 is now known (maze bring-up lane, verified in the game)
`missions/scripts/maze_commands.lua:21` calls `D.loader.catalogue(r.g,'models/')`; catalogue appends `models/` and
`gd.mod_list` only accepts `missions/...`, so it must be `'missions/'`. Separately the maze kit must sit at
`missions/models/` (the generator's `--prepare-mod` wrote it to the mod-root `models/`). ANOTHER Codex job (the maze
generator's thread) is fixing both in the missions mod and `tools/maze/generate.py` right now: do NOT edit missions files;
wait for `_build/tmp/codex-maze-fix1-last.txt` to exist before regenerating the Envoy bundle. Your work is the Envoy side:
the fallback to authored rooms when the maze kit (`D.maze_set.part` in the catalogue) is absent from the installed mod,
a not-started run not being recorded, the path-rule test, and item 2.
