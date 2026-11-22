# Packet B follow-up 2: mission runtime after the second in-game round, plus the camera (2026-10-03)

Round 2 on the vanilla disc passed walls, pass-through, solid ceilings, the doorway, 11 reloads, chunk windows, names and
limits. Evidence: `_build/audit-20261003/mission-verify/r2/` (`logs/`, `work/`). Same rules (Lua/Python only, your files only,
no build, no game, no commits). Fix at the root, with tests:
1. `mission clear` dies when P1 is respawning: `commands.lua:108` asserts `gd.fly_attack`, which is refused for a fighter that
   is dead/held/respawning; the command is never retried and the mission cannot complete (1 of 10 completion runs failed this
   way: log `lost goomba (not a defeat) | wave 2 of 2 | death | refused missions/commands.lua:108: fly_attack: that fighter's
   state cannot fly`). Commands that need a controllable fighter must wait and retry until it is ready (bounded), never assert.
2. `mission play` / `mission reload` right after match start or during a respawn are refused with an obscure teleport error
   (`runtime.lua:57: gd.teleport: that fighter's state cannot fly (dead, held, respawning)`). Same treatment: wait for a ready
   fighter, with a clear log line if it times out.
3. One chunk-border flip at the x=130 border inside the claimed dead band (`chunk spawn c1 (player=132.4) | unload c2 | spawn
   c0 (128.0) | load c2 | spawn c1 (132.2)`); probably the fighter being knocked back across. Check the hysteresis really
   applies to both directions at every border; add a test that crosses and re-crosses within the band.
4. A CPU opponent re-arms its AI after every respawn (the stage is hidden, so a CPU falls, dies and comes back acting). The
   runtime owns the level, so give missions a rule for non-player fighters: by default keep every CPU port in
   `gd.cpu_mode(port,"stand")`, re-applied after respawn, and park them on the level (the chunk spawn) rather than letting
   them fall; a mission may opt a port into "fight". Document it.
5. Labels: pass each part's instance name from the level file to `gd.model_label` (the exporter is being changed to write
   `name`/`label` per part: Blender object names such as `Wall1`), falling back to the part type.
6. **Camera (the owner's complaint: "camera wasn't great").** The engine now has `gd.camera_params` (verified in the game:
   `min_dist`, `fov`, `fixed_zoom`, zero `yaw_gain`/`pitch_gain` remove the skew; `gd.camera_params(nil)` restores; see
   `docs/scripting.md` and `_build/tmp/codex-engine-batch2-report.md`). Implement section 8 of
   `docs/superpowers/specs/2026-10-03-mission-folders-and-large-levels-design.md` from the evidence in
   `_research/camera-for-large-levels-2026-10-03.md`: a camera module that (a) moves the stage origin to follow the player with
   a 10-unit leash, clamped to the level ends (`gd.stage_set_origin`, `gd.stage_set_camera_bounds`); (b) per level and per
   chunk camera settings from the level file (`camera = {mode="follow"|"chunk"|"shaft", window={w,h}, min_dist=, fov=, ...}`),
   defaults: follow mode, window about 250x180, yaw/pitch gains 0; chunk mode = window is the chunk rectangle plus a margin,
   origin eases to the chunk centre over 30-60 frames on crossing, `min_dist` chosen so the view is not wider than the room;
   shaft mode = origin x fixed, y follows, window 150x180; (c) everything restored on `mission stop`/unload. Never touch the
   C-stick. State the numbers you chose and why; the owner judges it by eye afterwards.
Regenerate `scripts/main.lua` with the bundler. Report: `_build/tmp/codex-mission-runtime-fix2-report.md`.
