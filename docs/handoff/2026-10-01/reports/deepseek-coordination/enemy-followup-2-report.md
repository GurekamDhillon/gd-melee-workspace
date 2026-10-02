The second review identifies residual P1s. Let me read the current modules and fix them systematically.

All 26 pass. Now update the contract doc for the new guarantees.

All residual review P1s are fixed and proven. Final report:

**Changes (only the four owned files)**

`encounter_behaviors.lua`
- **Stale-history fix**: `record_history` clears a target's history immediately on line-of-sight failure and forgets absent targets; `select_target` requires a currently-observable target (`visible_now`); `delayed_pose` has a bounded `memory` window (120 frames). A target visible through frame 10 and occluded since 11 is never attacked at 197, and a mid-tell LOS loss aborts the tell.
- **Exact-true callback protocol**: configured `permission`/`actions.available`/`actions.submit` must return exactly `true`; `false`, `nil` or a throw is denied/refused/failed, surfaced, and leaves no confirmable pending.
- **Tell gene/run binding**: the tell advertises and re-checks the exact equipped gene instance and run identity at release; a charged gene swap cancels with `reason='gene_changed'` and spends nothing.
- Attack-phase tracking (`startup/active/recovery`).

`boss_behaviors.lua`
- **Movement is not recovery**: `on_recovery` opens only on a real `ability` request or an aborted tell; movement/patrol never does, and the window is bounded and expires.
- **Completed bosses inert**: a resumed `completed` boss emits one `retired` event and never requests/moves/attacks; phase time and completion are preserved.
- **Owner-bound addon**: added `owner_key(profile_id, run_id)` and a required `owner` field; `ctx = {owner, run_id, generation}` is checked (owner first) in sync/eligible/claim, so two profiles both containing `run1` cannot accept each other's rewards.

`docs/ENEMY-BEHAVIOR-CONTRACT.md` updated for all of the above.

**Evidence**
- `python3 -m unittest tools.roguelite.test_enemy_behaviors -v` → **26/26 OK**, including new real-Core cases: visibility loss after acquisition, LOS failure with existing history, movement-vs-recovery vulnerability, real-attack vulnerability expiry, completed-resume inertness, charged gene replacement, nil/false callback seams, and distinct profiles sharing `run1`.
- Lexical-bundle load/validate smoke OK.
- Full `tools/roguelite` discovery: 140 tests, same 4 pre-existing missing-art errors only; no new regressions.
- `git status` confirms only the two new game modules changed; `main.lua` and other modules remain untouched baseline.

**Remaining limits:** native combat, rendered tells, game/controller runs, measured AI tech counts and human feel remain unavailable here; runtime native wiring into `main.lua`/`prepare.py` is still pending. No 20XX/UnclePunch or other external system is reused or claimed.