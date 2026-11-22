# Packet J follow-up: three native failures after the integrator's build (2026-10-03)

Clean build (bridge fixpoint, ABI clean, provenance recorded). Native suite: 233 pass, 3 fail. Log:
`_build/runs/mission-integ-suite7/melee-pc.log` (lines ~365-375 and ~764-770); map `_build/melee-pc.map`.
Same rules (no commits/reset, no build, no game launch, keep files compilable). Another Codex job is editing
`pc/gameworld/script_fighter_bench.inc`, `gw_script_camera_params.inc`, docs: stay out of those.

1. `not ok 111 - script_clank_event`: `ACCESS_VIOLATION reading 0x00000020 at pc 0x10434694`, which the map resolves to
   `_gw_ScriptGame_ClankValue + 0x14`. A read at offset 0x20 from NULL: the game-side getter dereferences a null record or
   pointer when called from the headless test (no match, no fighters, or the event record not populated). Find whether the
   PRODUCT is unsafe (a script can call it with no clank active: that must return nil, never fault) or only the test's
   fixture; fix the product to be null-safe either way and make the test exercise the empty case explicitly.
2. `not ok 112 - script_presentation_timer`: `presentation APIs missing: function\nfunction\ntrue`. The console capture ends
   each printed value with a newline, so an exact `strcmp` against a string without the trailing newline fails although the
   APIs are present (the same test bug existed in `gw_script_shaders_tests.inc` and was fixed there with a trim helper,
   `t_shader_trim`). Fix the test the same way; check every `strcmp(out, ...)` in your new tests.
3. `not ok 158 - script_lab_events`: `event queue still armed with no hook defined`. This existing LAB test passed before your
   change (suite 232/234 with only two unrelated failures on the previous build), so adding the clank event changed event
   arming: the queue is armed when no script defines a hook. Find the cause (the new event's producer arming the queue
   unconditionally, an event id/case numbering collision in the dispatch table: a past bug in this area was `on_enemy_hit`
   dispatched at the wrong case, or the armed-mask not covering the new id) and fix it so the invariant holds: no hook
   defined = nothing armed = zero cost. Do not weaken the existing test.
Reply with each cause in two lines and file:line changed; update `_build/tmp/codex-clank-impact-report.md`.
