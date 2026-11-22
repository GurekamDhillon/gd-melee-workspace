# FX1 follow-up implementation plan

> Execute inline using executing-plans and TDD. Packet approval overrides additional design gates; no commits, builds of the game or game launch.

**Goal:** Complete the source-level FX1 audit against the already integrated engine and its newer visual-language policy.

**Architecture:** Retain current whole-pose Aurora capture/held-item assembly and procedural ribbons. Public bindings use existing owner-scoped motion registry; Lua parsing must reject malformed selectors before registry calls. Preserve earned-state/crit first uses unless the owner answers otherwise.

**Tech stack:** native C/Lua, C++ standalone history fixture, PPC/native libclang checks.

**Spec:** docs/prompts/codex-afterimages-tracers.md; later current earned visual contract in docs/scripting.md and earned_fx.lua.

## Constraints and review focus

No game build/launch or commits. Preserve unrelated work. No gameplay changes. No claim of measured120fps, real rewind parity, shader execution or correct pixels from standalone fixtures. Test explicit port disagreement, embedded-NUL enums/joints, limits, ownership and default earned triggers. Existing CPU/sub/held/custom material acceptance remains a runtime requirement.

## Tasks

- [x] Audit current renderer, fix1 report and earned first uses; reconcile documentation with current limits/ABI/material fallback.
- [x] Add standalone fixture for actual Lua motion bindings; witness port and NUL rejection regressions RED, repair parsing and verify GREEN. Run C++ history fixture.
- [x] Run motion source audits, demos, affected native/PPC/C++ syntax and existing Envoy suites. Fresh independent review; fix important integer-narrowing finding RED/GREEN and add nested-name coverage in one wave.
- [x] Update original requested report with current source evidence and explicit unrun profiling/game acceptance.

## Ledger

Ruling: existing later code reserves afterimages for technique-earned windows and crit-hit tracers; asked the owner which visual policy to use. Preserve current policy pending clarification. Cost if wrong: first-use data must be retuned; gameplay remains unchanged.
Ruling: game launch/build prohibition prevents the required worst-case profiling and simulation/GPU acceptance; prepare commands/checklist and report incomplete acceptance honestly. No source test substitutes for it.

Final review: integer-narrowing finding fixed RED/GREEN; nested-joint coverage added; fixture default/ownership evidence explicitly limited; current report supersedes historical first-use/material/limit claims. No minors deferred. Standalone parser/history PASS, five source audits/two demo checks PASS, affected syntax PASS.599 Envoy tests/62 suites pass; helper then refuses the existing oversized mod_engine module (no Envoy changes). Carried patch refreshed and reverse check PASS; generated space-prefixed blank context preserved.
