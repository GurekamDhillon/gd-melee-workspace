# Slippi replay-pair handoff — 2026-09-24

This supersedes the Slippi status in [HANDOFF-2026-09-24.md](HANDOFF-2026-09-24.md).
That document still owns the release baseline and unrelated backlog. No new
release was published for this experiment.

## Result

Two native GD clients completed one private online replay through public Slippi
Direct matchmaking using two distinct existing accounts. The service assigned
P1/P2; each client sourced only its own replay controls, with the other player's
controls delivered over Slippi ENet. This is an explicit diagnostic mode, not a
finished online menu or proof of interoperability with stock Slippi Dolphin.

The tested game source is `c1b08a92a`; published `pc-port` is `9ec3c7397`, which also
preserves the independently published Discord documentation. Its full supported
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
| `parity-Game_*` (six configured console fixtures) | All six ordinary replay cases pass, 7,344 frames total with exact post-state and RNG parity. |
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
