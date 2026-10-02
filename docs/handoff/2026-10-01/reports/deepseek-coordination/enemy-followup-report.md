Now I'll rewrite the tests to cover the review items against the real modules.

All 21 Lua tests pass; only the doc test fails because the contract needs the new sections. Let me update the doc.

All 22 pass. Final verification: lexical bundling smoke, no forbidden-file changes, and broader suite.

All corrective review P1s are addressed and verified. Summary:

**Changes (still only the four owned files)**
- `encounter_behaviors.lua`
  - Observable-only history: `visibility()` + `record_history()` store only previously visible poses; reveal reaction now starts at first reveal.
  - Fail-closed callbacks: thrown `visible`/`permission`/`actions.available` are treated as denied and surfaced.
  - Eligibility: `alive==false` / `hitlag>0` never request and abort an advertised tell.
  - Tell retention: advertises and reuses exact `target`/`slot`/`move_id`; cancels instead of reselecting.
  - Generation-safe ownership: pending purged on remove; `move_id` = `<id>#<gen>:<slot>:<serial>`; stale confirm refused.
  - Explicit `permission` callback; refused/failed submit leaves no pending and is surfaced.
  - Boss combat anchor movement; `capability` grounded/aerial on move/recover; `placement` height now upward.
  - `adapter_contract` documents logical losses/measured hits and `enemy_state.received` vs `hits`.
- `boss_behaviors.lua`
  - Delayed visible phase inputs; resume requires controller match and preserves `phase_frames`/`completed`/`rewarded`; latest measured `kos`/`hits` synced.
  - `on_recovery` opens after a successful attack or aborted tell (Glacier fixed).
  - Real `defeat()` completion lifecycle (sync before remove).
  - Addon bound to `run_id` + `generation`; encode/decode validated.
- `test_enemy_behaviors.py`: 22 real-module tests, including controller-mechanics, occlusion/reveal, eligibility, retention, generation purge, fail-closed callbacks, anchor movement, defeat/resume lifecycles and binding.
- `docs/ENEMY-BEHAVIOR-CONTRACT.md`: updated contract.

**Evidence**
- `python3 -m unittest tools.roguelite.test_enemy_behaviors -v` → **22/22 OK**.
- Lexical-bundle load/validate smoke OK.
- Full `tools/roguelite` discovery: 136 tests, only the 4 pre-existing missing-art errors (`test_certify_rooms`, `test_rooms`, `test_runtime`) remain.
- `git status` confirms only the two new game modules and the two new workspace files; `main.lua` and other runtime modules are untouched baseline.

**Remaining limits**
Native enemy combat, rendered tells, game/controller runs, measured AI tech counts and human readability/feel remain unavailable here; runtime native wiring into `main.lua`/`prepare.py` is still pending. No external system (20XX/UnclePunch) is reused or claimed.