# Geno define slice 1 implementation plan

Goal: implement the approved GF1 native Mario-reference definition, preserving attachments and m-ex. Spec: `docs/superpowers/specs/2026-10-04-geno-full-fighter-design.md`, slice 1 only.

Execution: native in this shared checkout as required by the packet. No commits/worktree operations, game builds or launches. New implementation units use Geno-specific files; other jobs' m-ex roster/interpreter and collision/render/stage files remain untouched. Shared includes/catalogue are edited last and minimally. Runtime acceptance requires an integrator rebuild and tester.

Architecture: definitions allocate stable boot-time resident aliases from unused legacy space, refusing exhaustion. A source-independent catalogue uses the roster catalogue identity primitives. A native Mario adapter copies independent effective descriptors/common and specific state rows; inherited retail resources remain references. Keep aliases fixed for the process, avoiding mutable host match remapping in slice 1. Offline only. Profiles grow by allocation; preserve historical article ids and use a separate namespace for extra profiles.

## Review focus

- Definition must not override retail Mario or a populated m-ex row.
- Reusing a loaded retail archive must not mutate Mario's animation flags/scripts.
- Additional profiles must not renumber existing article kinds or escape m-ex classification.
- Definition reload must not leave a changed alias/descriptor behind a saved snapshot.
- Unsupported donors/versions/schema/resources must refuse explicitly.

## Tasks

- [x] 1. Author format: failing generator/check/export tests; implement `tools/geno/define.py`, `new.py`, schema/check/export integration, Hero source-only fixture. Test unsupported donors, attach/define conflict, invalid version, provenance/path refusal and authored move round-trip.
- [x] 2. Native definition registry: failing standalone catalogue/alias tests; implement `geno_define.h` and registry include, strict Mario/common preset parsing, boot alias allocation, resource reference metadata and offline/hash APIs. Test mixed occupied slots, duplicate identity, deterministic alias assignment and exhaustion without mutation.
- [x] 3. Dynamic profiles: test profile 31/32 and legacy article ids; grow native registry ownership safely through reload/tests; replace game profile-indexed fixed descriptors with snapshotted lazy allocations; add disjoint extra article kinds while preserving legacy ids.
- [x] 4. Native game backend: independent retail-referenced ftData/animation/costume/common/special state descriptors; native load/callback adapters and every-state overrides; snapshot-visible identity and interpreter-use diagnostics. Verify syntax and suite registration; full stock tests deferred to tester by explicit prohibition.
- [x] 5. Selection/presentation/offline integration: append Geno definitions to existing frontend with referenced art and names, source costume/stock/results fallbacks, refuse online use, source-name scene selector, catalogue demo. Keep m-ex enumeration untouched.
- [x] 6. Validation/handoff: run author and standalone tests, syntax checks for changed native/game units; fresh review; update reference/guide/report with files/lines, limitations, shared edits, later private-port requests and tester script. No executable acceptance claims.

Each implementation task follows failing test → implementation → passing focused test. The ledger is `_build/tmp/codex-geno-define-slice1-progress.md`; forbidden commits/builds are replaced by source verification records.

Source tasks and permitted checks completed; playable acceptance remains pending the integrator rebuild and runtime tester. Results/review/verification are in the progress ledger and slice-1 report. No commits or executable checks performed.
