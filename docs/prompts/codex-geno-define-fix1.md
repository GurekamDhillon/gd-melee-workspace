# GF1 follow-up 1: slice 1 broke 33 existing Geno suite tests (2026-10-04)

Same rules as GF1 (`docs/prompts/codex-geno-define-slice1.md`): no commits, no `tools/port/build.sh`, no game launch;
your files only. No other job is editing the engine right now.

The integrator built your slice 1 together with the echo and armour work: it compiles, links, and the build recorded
provenance. The native suite then went from 280/280 to **252 pass, 33 fail of 285**
(`_build/runs/mission-integ-suite38/melee-pc.log`). Every failure but one is an EXISTING Geno test, with the same
signature:
```
geno: fighter PlKb.dat (PlKb.dat) -> kind 4: id ..., 1 subaction overlay(s), 1 Geno state(s) ...
geno: kind 4 player 5 reset (profile 0)
geno: kind 4 player 5 subaction 3 script replaced by overlay slot 0
heap: EXHAUSTED on 4 bytes after 0 allocs 0 frees, live 0 KB, top repeat 0 bytes x0
assertion "adr" failed
not ok 192 - geno_lab_effective_timeline
```
Failing: geno_lab_effective_timeline, geno_multijump, geno_multijump_script_gate, geno_jump_limits,
geno_effective_script_range, geno_iasa_script_validation, geno_state_savestate, geno_v1_values, geno_v1_change_action,
geno_v1_ground_edge, geno_v1_rehit, geno_v1_autolink, geno_v1_special_attrs, geno_v1_overlay, geno_v1_inert,
geno_v2_states, geno_v2_change_to_state, geno_v2_glide_entry, geno_v2_glide, geno_v2_specials, geno_v3_anim_motion,
geno_v3_hidden_glide, geno_v3_many_states, geno_v3_cape, geno_v3_drill, geno_lab_stale_fighter, geno_v4_drill_pose,
geno_v4_tornado_spin, geno_v5_registry, geno_v5_on_hit, geno_v51, geno_v52_lockon; and your own
geno_define_repeated_install (its last log lines are five repeats of `geno: fighter PlMr.dat (PlMr.dat) -> kind 0 ...`).

What the signature says: in the headless suite there is no game heap ("after 0 allocs 0 frees, live 0 KB"), and
something on the `attach` path that previously used static storage now asks the GAME heap for 4 bytes right after a
subaction overlay is installed. The likeliest cause is the dynamic-profile change (the 32-profile cap removed): a
per-fighter or per-profile table that used to be a fixed array is now allocated with the game's allocator. Find the
exact allocation from the code (do not guess), and fix the cause so that:
- existing `attach` fighters behave byte-for-byte as before slice 1 in every suite test (those tests are the contract);
- dynamic storage does not depend on a live game heap when none exists, and is covered by the LAB snapshot when it does
  (state how: a snapshot-covered native arena, a static pool with a refusal at exhaustion, or game memory reserved at
  match start), without reintroducing a small hard cap silently;
- nothing in the `attach` path allocates per frame or per action.
Also fix `geno_define_repeated_install`, and re-read your slice for any other place where `define` work changed
behaviour for fighters that do not use it (the catalogue's rule: a fighter with no definition is untouched).
Before you finish, reason through each of the 33 tests against your fix and say which you are confident pass and why;
you cannot run the suite, so be explicit about what the integrator should expect.
Report `_build/tmp/codex-geno-define-fix1-report.md`: the allocation, file:line, the fix, and the expected suite result.
