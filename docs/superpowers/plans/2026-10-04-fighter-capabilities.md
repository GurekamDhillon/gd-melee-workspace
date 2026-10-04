# Fighter capabilities implementation plan

**Goal:** Implement the engine packet in `docs/prompts/codex-fighter-capabilities.md` without changing Envoy.

**Architecture:** Game-side include fragments in `script_game.c` keep simulation state in its already snapshotted MEM1 BSS. Scalar Lua wrappers enforce offline gameplay permission and fork the LAB timeline. Entity IDs 1â€“6 select primary fighters; 7â€“12 select their second entities, independently. Retail action decisions use read overlays, not asset mutations.

**Constraints:** No build, launch, commit, reset or bundle regeneration. Do not touch `ftcoll.c`. Shared-file changes happen last, after rereading. No machine/disc paths in public material. Approval to execute is supplied by the packet's parallel rules.

- [x] Add movement fixtures, then implement jump-count overlays and restriction decision hooks; bound multijump animation/impulse selection.
- [x] Add effect fixtures, then implement timed retail effects, armour and safe item granting; explicitly report any required foreign collision hook.
- [x] Add target fixtures, then implement deterministic nearest/radius queries and a bounded timed status value on any chosen entity.
- [x] Integrate scalar Lua wrappers, scene/unload cleanup, per-frame timers and suite registration in one minimal shared-file pass.
- [x] Add single-feature demos, API documentation, and a rewind-proof script that requires zero differing bytes.
- [x] Run syntax checks and available standalone checks; review changes and write `_build/tmp/codex-fighter-capabilities-report.md`, separating source evidence from pending runtime acceptance.

**Review focus:** Invalid/nonfinite inputs; independent Nana ownership; transformations/despawn; retail jump restoration; expiry/unload preserving unrelated retail effects; offline refusal; rewound timer/owner state; item failures leaving no spawned orphan.

Runtime acceptance and global stub/tour integration remain pending; see `_build/tmp/codex-fighter-capabilities-report.md`. Source tasks above are completed under the no-build/no-launch rule.
