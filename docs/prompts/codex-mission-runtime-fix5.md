# Packet B follow-up 5: the integrator's smoke test of fix4 in the game (2026-10-03)

Same rules (Lua/Python, your files, no build, no game, no commits). The integrator regenerated the bundle from your fix4
sources, built a play copy (repo scripts + the tester's exported levels) and ran `mission play maze` in the LAB on the
vanilla disc, Mario standing still at the start. Log: `_build/runs/maze-smoke1/melee-pc.log` lines ~975-1300; screenshot
`_build/audit-20261003/maze-play/data/console/maze_smoke.png`; the play copy is `_build/audit-20261003/maze-play/mods/`.

1. **The instant camera cut fires continuously.** With the player standing still, the log repeats, about every 8 frames
   (60 times in ~8 seconds):
   ```
   script [missions/main] camera attach (0 frames)
   script camera params: owner=9 mask=959 min=252.6 max=252.6 yaw=0 pitch=0
   script arena-hooks: blast bounds -197.111 582.889 312 -208
   script [missions/main] camera detached
   script [missions/main] camera set
   script [missions/main] camera attach (0 frames)
   script camera params: ...
   script arena-hooks: blast bounds -197.11 582.89 312 -208
   ```
   The blast rectangle alternates between two nearly equal values, so two pieces of state disagree by a rounding step and
   each "corrects" the other: most likely the far-respawn cut condition is satisfied by the clamped origin (the origin is
   clamped away from the player at the level's left end, so "player further than a window from the origin" or "origin not
   where the follow rule wants it" stays true), or the cut's detach/attach itself moves the origin and re-triggers it. Find
   the loop and remove it at the root: the cut must fire once per respawn event (edge-triggered on the respawn, not
   level-triggered on distance), must not fire when the origin is merely clamped, and re-applying camera params and blast
   bounds must be idempotent (no setter call and no log line when the value is unchanged within a tolerance).
   Add a test that runs 600 frames with a stationary player at a clamped level end and asserts zero cuts and zero setter
   calls after the first frame, and one that respawns far away and asserts exactly one cut.
2. **The player has 33% right after `mission play`**, having done nothing. Something damages P1 during load. Candidates: the
   CPU acting before its bench takes (`mission: CPU 2 benched` is logged during load, but the first attempt can be refused
   and retried), the host stage being hidden under the fighters, or a fall. Make play start clean: bench (or at least
   stand + intangible) CPUs before anything else can happen, place P1 on the level before the host stage is hidden, and
   reset P1's percent to its pre-load value if the mission does not define a starting percent. Say which cause it was if you
   can determine it from the code; otherwise list what the tester should log.
3. **Void is visible left of the level's outer edge** at the maze start (screenshot: the floor strip begins about 15% in from
   the left of the frame and the area left of it is empty). Re-check the edge clamp with item 1 fixed: at the left end the
   visible left edge must equal the level's outer rectangle (or the level must be centred if narrower than the view). If
   the exported level's outer rectangle itself extends left of the first floor (a margin authored by the exporter), say so:
   then it is the level data, not the clamp.
Regenerate the bundle. Reply with the cause of item 1 in three lines, file:line, and the tests added;
`_build/tmp/codex-mission-runtime-fix5-report.md`.
