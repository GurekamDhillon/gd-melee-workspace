# SuperTime Envoy slice 1 implementation plan

**Goal:** implement packet E1 against the approved Envoy design with offline evidence.
**Spec:** `docs/superpowers/specs/2026-10-03-supertime-envoy-design.md` and `docs/prompts/codex-envoy-slice1.md`.
**Architecture:** pure genetics/companion rules; injected persistence and drop randomness;
run coordinator using an unchanged bundled mission runtime; HUD and application glue.
**Tech stack:** Lua 5.4 and a deterministic Python bundler.

User authorization is to execute this packet now in the existing dirty checkouts.
No commits, worktree changes, C edits, builds, game launches, or old Envoy reuse.
Only the new Envoy folder, new tests, new bundler, this plan and requested report are owned.

## Tasks and interfaces

- [x] Genetics: `new`, `validate`, `blend`, `express`; paired grade/cosmetic alleles.
  Write/run `envoy_genetics.lua` RED, implement `genetics.lua`, run GREEN.
- [x] Companion: `new`, `validate`, `feed`, `effects`; one tuning table with caps.
  Write/run `envoy_companion.lua` RED, implement `companion.lua`, run GREEN.
- [x] Drives: `new`, `track`, `defeat`, `tick`, `clear`; native defeat-only pickups.
  Write/run `envoy_drives.lua` RED, implement `drives.lua`, run GREEN.
- [x] Save: `new_profile`, `validate`, `encode`, `decode`, `open`, `commit`;
  deterministic strict text schema, atomic replacement, corrupt-file lockout.
  Write/run `envoy_save.lua` RED, implement `save.lua`, run GREEN.
- [x] Run: `new`, `start`, `frame`, `finish`; mission runtime `command/frame/current/stop`.
  Write/run `envoy_run.lua` RED, implement `run.lua`, run GREEN.
- [x] HUD: `draw`, `pickups`; safe-area stat panel and world-projected drive glyphs.
  Write/run `envoy_hud.lua` RED, implement `hud.lua`, run GREEN.
- [x] App/entry: console dispatch, lifecycle and real runtime composition.
  Write/run `envoy_main.lua` RED, implement `app.lua`, bundler and data folders, run GREEN.
- [x] Run all new tests and existing missions/map suites; parse every new Lua file.
- [x] Review integration/persistence edges and document exact engine registrations,
  missing capabilities, save/tuning schema and native probe commands in the report.

## Review focus

Corrupt/read-refused profiles must never be overwritten; failed settlements retain pending
progress and lock out another run; duplicate/end/unload events cannot double-settle;
missing CPU is not a victory; failed mission transitions cannot lose collected drives.
Native event ownership and last-position sampling must exclude removals/other scripts.

## Progress

All implementation tasks complete with RED→GREEN evidence, including real generated-entry
integration. Required regressions and Lua syntax checks pass. See
`_build/tmp/codex-envoy-slice1-report.md` for test counts, native limitations and probe steps.

Ruling: reuse the approved design and execute the user's packet in the existing dirty
checkout; no new approval, commits or isolation changes. Cost: no commit-based rollback
for this work; only new owned files were written.

Ruling: missing fighter modifiers are calculated/logged but not applied. Exact death
position and bench/unbench are engine requests. Cost: full native gameplay acceptance
is blocked pending those engine capabilities; Reach works in the script model.

Ruling: white drives are banked without grade changes, honoring slice 1's explicit
no-grade-changing scope. Cost: whites have no immediate growth benefit until a later slice.

Final review: independent read-only reviewer found an Important ambiguous-nil data-read
overwrite risk. Fixed with failing save tests first, then fail-closed runtime reads plus
a tested exclusive-create offline initializer. No other Critical/Important findings.
Cost: fresh profiles require offline initialization until the engine distinguishes missing
files from read errors. Native gameplay/rendering and OS durability remain unverified.
