# Packet S follow-up 2: the catalogue after its first run in the game (2026-10-03)

Same rules (Lua/JSON/Markdown/Python only, no C, no build, no game, no commits). All 39 mods were run in the game on the
vanilla disc. 36 work (some subtle, some needing human eyes for overlays). Evidence and tested patches:
`_build/audit-20261003/demo-tour/` (`patches/`, `fix/` = the patched copies that ran, `hang-evidence/`, per-run folders).
Fix, each with a test in `tools/port/test_demo_mods.py` or a stub run:

1. **demo_gauntlet never starts as shipped and leaves P2 benched.** `setup()` builds the entry area, generates the maze and
   loads nine areas in ONE call; the bench is refused on the first frames (`unsafe action`), so `setup()` is retried from
   `on_frame`, where the per-call budget is 50 ms / 2,000,000 instructions: the log shows `on_frame: ran too long` at
   `area_load` (`demo_gauntlet:80`), then `demo_gauntlet:140: attempt to perform arithmetic on a nil value (upvalue
   started_at)` every frame, because `room=1` is set near line 61 but `started_at` only at the end of `setup()`. Stage the
   build in a task (`gd.run` with `gd.wait(1)` per cell), set state last, guard re-entry, and apply the camera outside the
   task (a camera claim made inside a task is released when the task ends). Also: it preloads a stage slot in `setup()` and
   later calls `gd.stage_hide(false)`, which refuses while any slot is loaded (`stage slots live: unload the owning script
   before restoring host geometry`): load the slot only after the arena is gone.
   `patches/demo-gauntlet-staged-setup-and-slot.diff` ran through to `Victory in 51.07s` in the game: use it as the basis.
   Then make the walk through the maze and the boss fight real (the tester teleported both) and state the intended route.
2. **demo_fly**: `gd.fly_target` unprotected at `fly/scripts/main.lua:38` errors when the key fires at match start
   (`that fighter's state cannot fly (dead, held, respawning)`): see `patches/demo-fly-pcall.diff`.
3. **demo_training_card** opens its list on death states, so the default selection puts P1 in `DeadRight`: see
   `patches/demo-training-card-start-at-jab.diff`; filter out states a player cannot sensibly enter.
4. **demo_stage_tour** calls `gd.post_clear()` inside `on_stage_switch` (`stage-tour/scripts/main.lua:39`), which destroys
   the engine's own live transition cover: 12 lines of `stage transition: cover update refused: post handle expired or
   belongs to another script` per run. Do NOT change it to remove only its own pass yet: the tester did, and the game then
   hangs in the engine (a separate engine fix is in progress). For now, defer the demo's look change until the `after`
   phase and never clear passes you do not own; when the engine fix lands, switch to removing only your own handles.
5. **The tour mounts `demo_gauntlet` and `demo_effects` at boot for the whole tour**, so the gauntlet retries its setup in
   every scene and benches P2 under every other demo, and is then loaded a second time (`bench refused ... owned by another
   script`). Each demo must be the only demo mod active while it is toured. A tour PASS must mean more than "loaded and a
   screenshot arrived": check each demo's documented keys through its state (the tester's `scenarios.py` and `drive.py`
   under the evidence folder do this per demo: fold that approach into `demo_tour.py`), and verify each screenshot decodes
   fully (two truncated PNGs passed a size check).
6. `demo_tour.py` still writes the disc path into `runner.log` and its copy of the game log, sets volume 3 (unattended tours
   must set `MELEE_VOLUME=0`), and sets no owner tag itself: confirm against the current file and fix what remains.
7. Weak demos: bloom and outline are barely visible (centre luma 71 to 73; edge strength 2.22 to 2.29): pick parameters
   that read clearly; the surface-fighter and parts tints are subtle: make them obvious; rewind: after save then load,
   `history.depth` is 0, so the snapshot step is unverified: make the demo prove it; six-slots: after recycle, slot 6 was
   still hidden.
8. Document in the catalogue README the API behaviours the run exposed: `gd.stage_hide(false)` refuses while any slot is
   loaded; a camera claim inside a task ends with the task; `gd.press` cannot be used outside a task; reading
   `gd.camera_params()` errors while another script owns them; `gd.fly_attack` accepted damage 40 although documented as
   1-30; `gd.scene_launch` stalls logic for about ten seconds.

Report `_build/tmp/codex-demo-mods-fix2-report.md`.
