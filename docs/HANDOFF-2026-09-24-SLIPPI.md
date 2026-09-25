# Slippi replay-pair handoff — 2026-09-24

This supersedes the Slippi status in [HANDOFF-2026-09-24.md](HANDOFF-2026-09-24.md).
That document still owns the release baseline and unrelated backlog. No new
release was published for this experiment.

## Result

Two native GD clients completed the initial short replay and two unchanged
roughly 150-second recordings through public Slippi Direct matchmaking using
two distinct existing accounts. A third long recording was rejected at startup
for non-neutral initial processed controls. The service assigned
P1/P2; each client sourced only its own replay controls, with the other player's
controls delivered over Slippi ENet. This is an explicit diagnostic mode, not a
finished online menu or proof of interoperability with stock Slippi Dolphin.

The adapter baseline used game source `c1b08a92a` and was integrated as
`9ec3c7397`, preserving the independently published Discord documentation. Its full supported
build passed with all 18,827 bridge entries resolved, zero invalid ECX/EDX
prologues, and a bridge fixpoint. Compilation logs contained no error/FAIL.
The tested executable SHA-256 is
`688273ba0ff4c6288461fa8b51095ab0dbaf1c6ffbd9df73b494a2e681174c8b`.

## Evidence

Private artifacts remain under the Delta build's `runs/`; no replay or account
data belongs in Git. Paired runs used vanilla NTSC 1.02, visible windows, volume
3, and at least 8 GiB available RAM checked before each launch.

| Run | Evidence |
| --- | --- |
| `slippi-20260924-220311-cb42f7-{1,2}` | Local pair, clean exits, complete recordings and exact states/checksums. |
| `slippi-20260924-220354-7653e8-{1,2}` | Public Direct, two distinct reciprocal account tags, roles 2/1. All 1,026 frames (-123..902), 2,052 player-state records, processed inputs and finalized checksums match. Each sent/received 1,026 pads, read 1,024 local fixture inputs and zero remote fixture inputs. Rollbacks 16/120; desyncs zero. |
| `slippi-20260924-220451-39ac8e-{1,2}` | Local relay with 60 ms one-way delay and 2% configured packet loss. 126 packets dropped; complete input/state/checksum comparison passes with rollback required. |
| `slippi-20260924-221022-1ade6d-{1,2}` | Negative control: one P1 A press added at frame 45 only in client 1's fixture. Both clients agree exactly through frame 902; the source comparison rejects at frame 45 (buttons 0 to 256, action 14 to 44). |
| `slippi-20260924-222632-6b3d04-{1,2}` | Longer unchanged public Direct replay, Slippi 3.19.1 on vanilla stage 3: all 9,120 frames (-123..8996), 18,240 player-state records, processed inputs and finalized checksums agree exactly. Both source and executable hashes remained unchanged. |
| `slippi-20260924-222931-4063d5-{1,2}` | Second longer unchanged public Direct replay, Slippi 3.19.1 on vanilla stage 31: all 9,126 frames (-123..9002), 18,252 player-state records, processed inputs and finalized checksums agree exactly. Both source and executable hashes remained unchanged. |
| `slippi-20260924-223231-d9d036-{1,2}` | Third 3.19.1 replay was rejected before match start: P1 had non-neutral processed input at frame -123, inside the required neutral initial delay window. This was not a completed compatibility run; no replacement fixture was chosen or changed. Its source hash remained unchanged. |
| `parity-Game_*` (six configured console fixtures, historical) | All six ordinary replay cases previously passed, 7,344 frames total with exact post-state and RNG parity. GD later requested deletion of these six used `.slp` files, so this exact configured set cannot be rerun. |
| `slippi-offmode-ace-quoted` | Final integrated source: 185/185 tests, exit 0, FATAL 0. |

The stricter finalized verifier was rerun against both Direct and impaired-run
artifacts after review added exact processed-input comparison. Native local-input
checks also compare processed float bits and buttons during simulation.

All seven focused native test targets passed during implementation; the finalized
replay fixture target passed again after the shutdown fix. All 39 Python tooling
tests pass. Independent review's processed-input verification finding was fixed
and rechecked. Game integration and push are complete. Workspace tooling and this
handoff accompany the integration on workspace `master`. Long-lived development
lanes are retained; generated bridge churn is local build output.

The three longer attempts used the same tested executable SHA-256 listed above.
Their sanitized results are in ignored `_build/tmp/slippi-long-result-{1,2,3}.json`;
selection inspected 427 candidate recordings and found three about 150 seconds long.
The earlier one-time deletion of used Slippi recordings was at GD's request: 104
files were deleted, including the six paths from `parity.local.conf`; the cleanup
reported 4,396 remaining at that time. No source replay was modified by the
long-run tests.

## Windows title-bar movement

The fix is committed as `1cf87fe4b` and pushed to `pub/pc-port`.

The follow-up window fix consumes the native primary caption click before
Windows enters its modal move loop, activates that exact Aurora HWND, and moves
it from the normal frame tick. Simulation and Slippi polling remain on their
existing thread. It does not call game code recursively from a Windows callback.

The baseline held-drag probe blocked all eight console frame queries for 4.86
seconds (`window-drag-baseline-224058`). The fixed standalone probe answered all
eight queries while held, at about 60 logic frames/s. The final build also passed
caption double-click maximize/restore and dragging from maximized
(`window-drag-controls-225437`), plus ACE 185/185 with zero FATAL entries
(`window-drag-ace-225332`). The focused native coordinate regression passes.

Final public Direct run `slippi-20260924-225506-3ab1bc-{1,2}` passed all 9,120
frames and 18,240 player-state records with exact processed inputs, post-states
and finalized checksums. The original source replay hash was unchanged. During
that run both clients moved 105 by 28 pixels while their physical mouse button
remained held and their frames advanced across all eight samples. Client 2 was
deliberately inactive before its caption click and correctly activated and moved.
The full proof is in that run's private `-result/window-drag-proof.json`.

The final window executable SHA-256 is
`03fd499c9757d16897dc5b10486fae4829c1e4776a25d32bb21aa20de7fd242b`.
Its supported build passes the 18,827-entry bridge fixpoint and has no
error/FAIL in the completed build log. Review corrected swapped-button message
handling and the initial inactive-window activation issue before this build.

Scope: primary-button title-bar movement, including drag from maximized.
Border/corner resizing and system-menu Move/Size still use Windows modal
handling. This custom caption path does not reproduce native edge Snap previews.
Swapped-button mapping is source-reviewed; system mouse settings were not changed
for a live swapped-button test. GD still owns subjective movement/desktop feel.
The controller-enabled ACE Fox/Fox check was left open for GD in
`window-drag-gd-230104` (console port 52479); its held-drag probe also passed.

## Implementation and traps

- `gw_slippi_mode.c` gates the experiment. With no mode, existing GD netplay and
  ordinary replay paths stay active. The mode rejects conflicting input/resync
  sources; fixture validation precedes peer setup.
- Replay frame -123 maps to online PAD frame 1, independent of input delay. Initial
  applied controls must be neutral; first-frame physical controller noise is
  normal in official recordings and must not cause rejection.
- Physical trigger normalization uses 140, with canonical reconstruction above
  the clamp. Gameplay checks validate the resulting processed controls.
- Only received remote truth confirms remote frames. Resimulation replaces
  speculative recording events; only finalized frames reach output artifacts.
- Public Direct obtains account/version information from existing Launcher
  profiles. The private local helper keeps refreshed tokens/profile data in
  memory and sends only required game fields over stdin. No match reports,
  ranked/unranked searches, replay uploads or account changes are performed.
- Same-WAN peers use the supplied LAN address, following official Dolphin.
- The peer receive window covers rollback capacity; an earlier +7 window could
  discard bundles containing useful older inputs and stall delayed clients.
- CRT `exit()` ran recorder finalization but then returned 127 through unsafe
  graphics teardown. The finite diagnostic now closes/checks recording explicitly,
  flushes files and uses `_exit()`, matching existing parity behavior.
- The runner checks process ownership and creation times, cleans up only its own
  executable copies, and rejects incomplete artifacts and nonzero exits.
- Pass spaced disc paths through the runner's environment quoting. A PowerShell
  nested Bash command previously truncated the ACE path and produced a misleading
  184/185 test result; the correctly quoted prior run passed 185/185.

Usage and focused tests: [tools/slippi/README.md](../tools/slippi/README.md).
Design and implementation checklist live under `docs/superpowers/`.

## Remaining scope

Stock Dolphin interoperability, interactive controller play through this adapter,
online menu integration, ranked/unranked, spectating, client attestation and larger
cross-machine/WAN coverage have not been established by this work. No upstream
GitHub thread was posted. The three earlier VPS reports, Spanish text and unrelated
feature backlog remain untouched.

The third long replay exposed a narrower fixture limit: non-neutral processed
controls in the initial delay window are rejected before peer setup. Two other
long recordings passed; this third recording does not count as a pass.
