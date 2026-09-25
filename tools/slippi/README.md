# Experimental Slippi replay pair

This diagnostic runs one online replay through two native clients. Each client
reads its assigned player's raw controls; the other player's controls arrive over
Slippi's ENet peer protocol. `direct` additionally uses Slippi Direct matchmaking
with two existing accounts. A passing GD/GD pair does not establish compatibility
with an unmodified Slippi Dolphin opponent.

Build the selected game lane with `tools/port/build.sh` first. On Windows, with
Python and `psutil` installed:

```text
python tools/slippi/two_client_replay.py --fixture <private.slp> --iso <vanilla-1.02.iso> --game-root <game-checkout> --build-root <lane-build> --mode loopback
python tools/slippi/two_client_replay.py --fixture <private.slp> --iso <vanilla-1.02.iso> --game-root <game-checkout> --build-root <lane-build> --mode direct --user-a <account-a/user.json> --user-b <account-b/user.json>
```

For a loopback impairment run, add `--latency-ms 60 --loss-percent 2
--require-rollback`. A local UDP relay delays each direction and drops packets
with a repeatable random seed; its packet counters appear in the result. These
options are refused for public Direct matchmaking.

For an input negative control, add `--negative-control` in loopback mode. The
runner changes one P1 A press in a private copy of the fixture, supplies that
copy only to the P1 client, and requires both clients to agree on the changed
result while the original fixture shows a first gameplay divergence at or after
the changed input. This option can be combined with `--require-rollback`.

The fixture must contain a complete modern online match (Slippi replay format
3.17 or later), human ports 1 and 2, vanilla characters/stage, and recoverable
physical controller fields. Input delay defaults to two frames; recorded processed
controls must be neutral during that initial window. Slippi clears opening PADs;
its separately recorded physical fields may contain first-frame controller noise.
Applied replay frame -123 is online PAD frame 1. Recorded analog
triggers are normalized by 140; original raw trigger values above that clamp
cannot be recovered, but the canonical bytes have the same processed effect.

Accounts can alternatively come from a private, untracked Python module named by
`--accounts-helper`; its `profiles()` returns two Launcher `user.json` dictionaries
in memory. The runner forwards only the five game profile fields through stdin.
It never writes a credential file, submits a match report, or uploads a replay.
Keep all account files, recordings and discs outside version control.

Each run has distinct directories under the lane's `runs/`. `state.csv`,
`hashes.csv`, `match.slp`, and `evidence.json` are verified after both games exit.
The result directory contains `result.json`. Game windows are visible, volume is
3, and at least 8 GiB available physical memory is required before each launch.
Cleanup targets only descendants with recorded executable paths and creation
times. No screenshots are used.

Acceptance requires the complete finalized frame sequence to agree with the
fixture, every recorded processed Pre-Frame input for both ports to match the
fixture exactly, equal gameplay checksums, changing remote inputs, zero remote
fixture reads, and a completed handshake/match. Direct additionally checks the two
requested accounts against reciprocal identifiers salted for this run. These
identifiers are diagnostics, not client attestation. Missing or incomplete
evidence fails verification.

The standalone checker can rerun artifact validation:

```text
python tools/slippi/compare_finalized.py <private.slp> <client-1-run> <client-2-run> --mode direct
python -m unittest discover -s tools/slippi -p "test_*.py"
```

The game reads `MELEE_SLIPPI_MODE=loopback|direct`,
`MELEE_SLIPPI_REPLAY_ROLE=1|2` (Direct adopts its assigned port),
`MELEE_SLIPPI_DELAY=1..7`, the local/remote UDP port settings, and an evidence
output path. The runner supplies these settings and existing replay/trace/hash
settings consistently. Ordinary launches with no Slippi mode use the existing
GD netplay and replay paths.

Native unit tests run through the same supported build wrapper:
`build.sh --native-test slippi-pad`, `slippi-fixture`, `slippi-rb`,
`slippi-wire`, `slippi-peer`, `slippi-match`, and `slippi-mode`.
ENet's pinned source and license are documented in the game checkout's
`pc/DEPENDENCIES.md`.
