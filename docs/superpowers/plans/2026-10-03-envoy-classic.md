# Envoy retail 1P implementation plan

Spec: docs/prompts/codex-envoy-classic.md (approved execution packet).

Constraints: Preserve both dirty trees. No commits, resets, stashes, builds or game launches. Engine handoff marker exists. Research before C edits; reread touched C files. Offline only. Existing missions are parked and retained.

- [x] Task 1: Map retail Classic/Adventure; add guarded mode awareness, queued lifecycle hooks, bounded interstage hold, spawn modifiers and loop/start controls. Document engine contract in _build/tmp/codex-envoy-classic-engine.md. Syntax and offline fixture checks; no native execution claims.
- [x] Task 2: Integrate a separate retail-run adapter into Envoy. Seed opponent distributions around companion level totals, team scaling, per-stage reward choices, final evolution and NG+; settle age/records on game over. Guard old engines. Keep existing mission modules untouched. Add stub flow tests including two loops, failure, 1000 seeded rolls and cleanup.
- [x] Task 3: Update API documentation, single-capability catalogue demos and Envoy playtest/menu/native plan. Regenerate bundle last and run existing offline regression checks.
- [x] Task 4: Review combined implementation and produce _build/tmp/codex-envoy-classic-report.md with retail file:line map, policy decisions, checks and remaining native/owner acceptance.

Review focus: retried stages produce identical opponents; a disabled/broken script cannot hold retail indefinitely; no script records reach retail card records; entity replacement in wireframe teams does not leak modifiers; save failure cannot duplicate final evolution or aging.

Ruling: Execute in the supplied dirty workspace, no isolation/commits or design approval, as explicitly required by the packet. Use a dedicated engine worker followed by integration and review; no concurrent implementers.
