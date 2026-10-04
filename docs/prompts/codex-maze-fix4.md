# Maze generator follow-up 4: pluggable layout algorithms (2026-10-03)

Same rules as your earlier follow-ups (missions mod and `tools/maze/`, Lua/Python only, no C, no build, no game launch,
no commits); build on your follow-up 2 and 3 state; regenerate the missions bundle last.

The owner asked whether one generator covers every knob or whether other maze algorithms are worth implementing, and
approved this plan ("lgtm").

1. **Make the layout step pluggable.** Split the generator into: a LAYOUT algorithm that proposes a room graph (cells,
   connections, which are one-way), and the shared back end that everything already depends on: template selection,
   the reachability and clearance checker (gravity: up costs jumps, drops may be one-way, headroom rules), zones, enemy
   budgets, goal placement, the 1,000-seed proof and the maze-ness summary. An algorithm is a small module with one
   interface; the checker may reject or repair a proposal (state the repair rules) and the algorithm never bypasses it.
   The current "route first, then branches" generator becomes the first module, with unchanged output for existing seeds
   (prove it with a fixture).
2. **Add three:**
   - **Recursive backtracker**: long winding corridors, few branches, deep dead ends.
   - **Braid pass**: a knob (0..1) usable on ANY algorithm that removes dead ends by adding loops, so there are several
     routes and enemies can approach from two sides.
   - **Lock and key on the room graph**: one or more sealed exits on the main route, each opened by a key placed in a
     region the player can reach before that door (prove the ordering: no key behind its own lock, no soft lock, also
     with one-way drops); the player sees the sealed door before finding the key where the layout allows. Use the
     mission runtime's existing triggers/items for the key and the sealed-exit state; report anything missing as a
     request rather than faking it.
   Also give Wilson's algorithm a short assessment (unbiased by construction: would it replace the east-bias tuning?) and
   implement it only if it is small once the interface exists.
3. **Per-region algorithms in a maze world**: each region of `mission world` picks its algorithm and knobs (seeded, or
   named in the command), so one region is winding, one braided, one lock-and-key; keys may open a connector to another
   region, with the world-level proof extended to cover it.
4. Commands: `mission maze <seed> [size] [algo] [braid]`, `mission world <seed> ... ` with per-region overrides, and the
   ASCII map showing locks, keys and one-way edges. The maze-ness summary reports per algorithm so they can be compared.
Not now: cellular caves and wave function collapse (say in one paragraph what each would need).
Tests for each algorithm (determinism per seed, solvability over 1,000 seeds, clearance, the lock ordering proof);
report `_build/tmp/codex-maze-fix4-report.md` with the interface, the comparison table, and what a tester should walk.
