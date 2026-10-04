# Engine batch 2 implementation plan

**Goal:** Implement the three ordered parts of `docs/prompts/codex-engine-batch2.md`.
**Architecture:** Snapshot-owned game-side state, scalar native/Lua interfaces, existing offline write gates. Keep includes focused by feature; preserve both dirty trees.
**Authorization:** The user requested execution of the packet and its referenced designs. Execute inline. No commits, resets, builds, game launches, frontend, sysdolphin or mod edits.

- [x] Camera: write native-suite boundary tests and fake-stage fixture first; expose partial parameter updates/restoration, standard-camera FOV hook, lifecycle cleanup; remove continuous origin/camera-bounds log and timeline forks. Document ranges.
- [x] Modifiers: write fake-fighter attribute-byte/replacement/clear tests first; use vanilla attack/defense ratio getters and movement/shield read hooks rather than mutating attributes. State and ownership in snapshotted game BSS. Document mechanisms and limits.
- [x] Reserves: write fake-fighter freeze/restoration/refusal tests first; validate both player entities atomically, preserve control/hide flags, clear motion/input/velocity and reseed collision/camera on call, reassert before game updates. Audit six-slot launch, HUD and LAB capacities; report if enabling is not contained.
- [x] Verify changed C syntax and diff hygiene without building or launching; report unrun native-suite tests explicitly. Produce `_build/tmp/codex-engine-batch2-report.md` with exact integrator commands and credits.

Review focus: partial updates must not overwrite other camera fields; online calls must stop before ownership changes; modifier reads must preserve Geno edits; reserve ownership must cover dormant halves without awakening them; unload and snapshots must preserve lifecycle state.

Ruling: Write tests first but defer suite execution to the integrator, as the packet explicitly forbids building and launching the game. Syntax checks and standalone fixtures are allowed; they do not establish full native acceptance.
