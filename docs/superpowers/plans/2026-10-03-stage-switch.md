# Stage switching implementation plan

**Goal:** Implement packet O's offline static stage pool and deterministic queue.
**Spec:** `docs/prompts/codex-stage-switch.md`; Design A is already selected and authorized.
**Architecture:** New portable DAT validation/reader, game-side scene-owned slot records, small Lua bindings and a queue director. Keep the public slot API independent of static versus future behavioural slots.
**Tech stack:** C, Lua 5.4, synthetic host fixtures, Python read-only disc audit.

Constraints: no builds of the game, launches, commits, resets or formatting; preserve dirty work; shared files edited last. No disc-derived data in tracked files.

- [ ] Validate collision DAT structure, flags, indices and budgets with synthetic fixtures; audit six legal stage archives read-only and quantify heap headroom.
- [ ] Load hidden model groups and collision data into owned slots; reject full pools before allocating; free deterministically.
- [ ] Implement atomic logic-boundary collision/parameter switch, fighter contact reset and placement, conservative item policy and restoration.
- [ ] Bind Lua API, queue triggers, seeded ordering and lifecycle cleanup. Refuse snapshot operations that cannot preserve native director/cache lifetime.
- [ ] Add demo, missions integration diff, credits, scripting reference and source-linked report.
- [ ] Run standalone fixture tests, Lua tests and game/native syntax checks. Review malformed inputs, unload mid-transition, foreign handles, online refusal and failed destination activation. Record unverified native acceptance explicitly.
