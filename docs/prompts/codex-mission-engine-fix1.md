# Packet A: one native failure after the integrator's build (2026-10-03)

The build passed (bridge fixpoint, ABI 18827/18827, provenance). Native suite: 225 pass, 1 fail.
`script_mission_paths`, `_stage_hide`, `_limits`, `_archive`, `_lifetime`, `_player` pass.

FAIL: `not ok 110 - script_mission_reload`, message `script_mission_reload at 256`
(`melee/pc/platform/gw_script_mission_tests.inc:256`, the final check after filling the cache:
`gs_stage_nmodels == 128` and `open_model('a')==d` and the overflow call failing with an error containing
both `cache full` and `restart the match`). The log shows parts loaded up to `part_120` and then
`script model: scene assets released (128)`; no line in the log contains "cache full".
Log: `_build/runs/mission-integ-suite/melee-pc.log` lines ~370-505.

Find the root cause (is the product wrong: the error text or the reuse of an unchanged asset when full; or is the test wrong),
fix the right side, same file ownership and rules as before (no build, no game launch, no commits). Reply with the cause in
three lines and the file:line changed.
