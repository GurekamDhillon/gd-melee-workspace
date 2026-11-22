# Codex packet: Envoy stage 5 mid-game resume, second pass (2026-10-08)

Same worktrees and rules as `docs/prompts/codex-envoy-s5-midgame-resume.md` (read it). Your first fix is committed as
game `d7d4d7938` ("a peer lost mid-match ends the match and returns to ONLINE PLAY"). The coordinator re-ran the set proof
with it (fresh ports 55150/55151): 11/12 checks PASS again, and progress: after the mid-match loss both saved records now
read `interrupted` (before your fix the survivor stayed frozen). But `CHECK FAIL C: resumed` still times out after 600 s:
the peers do not complete the resume after a MID-GAME loss (a between-games loss resumes fine; a fresh guest process
resumes fine).
New evidence: `E:\Projects\Melee Workspace\_build\agents\envoy-s5\np_s5\s5-opus-set2\` (host/guest logs of the reconnect
attempt, `driver-output.txt`). Find what happens after the survivor returns to ONLINE PLAY: does the host re-open the same
room, does the guest find it, does the saved-run handshake run, does it refuse (and why), or does the driver wait for the
wrong thing. Fix, add a test, report as before to `_build/tmp/codex-envoy-s5-midgame-report-2.md` with the re-run
command (ports 55160/55161).
