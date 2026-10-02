# Enemy-behaviors follow-up 4 report

Lane: frozen enemy-behaviors isolated wrapper/game lane. Owned files only:
`encounter_behaviors.lua`, `boss_behaviors.lua`, `test_enemy_behaviors.py`,
`docs/ENEMY-BEHAVIOR-CONTRACT.md`. No main/native/build/install/commit/art or
other lanes.

## Blockers fixed

1. **Visibility predicate exact-true.** `Behaviors:visibility` now grants
   visibility only when a configured `visible(agent, target, selfpose, frame)`
   returns exactly `true`. `false`, `nil`, a thrown error or any other value
   (`0`, `1`, strings, tables, functions) fails closed and is never an implicit
   yes. A thrown predicate is surfaced (`visible_error` counter/event). With no
   predicate configured, explicit observed-target semantics are unchanged.
   A tell started while visible is cancelled if visibility later returns `nil`
   (history is cleared, target not re-admitted, no ability request, no spend).

2. **Malformed observations refuse safely.** `sanitize_side` now always returns
   `(value, dropped)` (including `nil, 1` for non-table input), so
   `sanitize_obs` never raises. `sanitize_obs`:
   - refuses a missing / non-table / non-finite `self` with a reason;
   - drops non-table, id-less and non-finite-coordinate targets and counts them;
   - treats an omitted `targets` as an empty set;
   - returns a clean `{}` target list and never invents positions.
   The public `tick` path emits `observation_refused` for a malformed
   observation and clears `visible_now`, `hist` and `last_seen`, so a malformed
   frame cannot retain invisible history or drive a decision.

## New real-Core regressions (public `tick` / real modules)

- `test_visibility_predicate_requires_exact_true`: nil/other truthy predicate
  values produce no tell, no ability request, no visible target and no private
  history; exact `true` grants normal attack; `true -> nil` mid-tell cancels.
- `test_malformed_observations_refuse_safely`: direct `sanitize_obs` on
  missing/non-table/non-finite `self`, `false`/`nil`/id-less/non-finite targets,
  omitted targets; malformed frame via `tick` reports `observation_refused` and
  clears history; non-finite coordinates are never admitted.

All previous 30 tests (identity/action/LOS/gene/run/state binding, boss phases,
vulnerability, resume, defeat lifecycle, owner binding, callbacks, determinism,
cleanup) are preserved.

## Results (exact)

- `python3 -m unittest tools.roguelite.test_enemy_behaviors` -> **Ran 32 tests, OK**.
- Full `tools/roguelite` discovery -> **Ran 146 tests**, same **4 pre-existing
  errors** (missing generated art: `test_certify_rooms` x2, `test_rooms`,
  `test_runtime`) and 6 skips. No new regressions.
- Lexical-bundle smoke (`prepare.py`-style IIFE wrapping) loads and validates
  both modules against real Core/catalogues.
- `git status`: only the two new game modules changed; `main.lua` and other
  runtime modules remain untouched baseline. No non-ASCII.

## Remaining limits (native)

Native enemy/boss combat, rendered tells, Windows/Linux game and controller
runs, measured AI tech counts and human readability/feel remain unavailable
here. Runtime wiring of these modules into `main.lua`/`prepare.py` is still
pending root integration. No 20XX/UnclePunch or other external system is reused
or claimed. Frozen on completion.
