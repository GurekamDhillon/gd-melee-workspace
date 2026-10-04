# No-hitch engine implementation plan

Spec: docs/prompts/codex-no-hitch-engine.md (approved packet, 2026-10-03).
Goal: move compilation and chunk preparation ahead of room entry and stage launch behind loading.
Constraints: preserve dirty trees; no game build/run, commits or mission/Envoy Lua edits. Aurora changes carried in _build/patches/aurora-gd-no-hitch-v1.patch.

- [ ] A/C: production fixtures for pipeline capture, readiness, and draw skip policy; add bounded warm capture handles, snapshot-independent diagnostic progress, current-layout core readiness, persisted coverage and shared immutable seed import. Owner root, Aurora/main/script glue.
- [ ] B: fixtures for prepared area identity, collision/model gating and deferred retirement; implement snapshot-owned activation state and budgeted reclamation. Owner streaming lane, gameworld and mp collision.
- [ ] D: parser and loading-order fixtures; add scene mission/maze and mod autostart metadata, covered launch callback and explicit ready handshake. Owner launch lane, runtime/mods/gmscene; root script glue.
- [ ] E: overflow/context fixtures; admission control for tiny trace events, aggregate excess identities, frame/time log prefix; expose cheap perf query. Owner profiling lane; root script glue.
- [ ] Integrate registrations; add one-feature warm demo, seed sweep driver/tool inputs, scripting/profiling documentation.
- [ ] Verify focused fixtures and syntax, review combined changes; report signatures, patch, rebuild requirement, exact native acceptance targets with unmeasured values distinguished.

Review focus: stale handles after scene transition; unknown model/item/fighter requests; concurrent sandbox writers; compile failures that never become ready; rewind across prepared/active/retired areas.
