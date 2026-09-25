# Slippi two-client replay compatibility design

## Purpose and acceptance

Prove a native GD's Melee match can run across two separate clients using Slippi's online peer protocol. One saved, vanilla, two-human online `.slp` is the input fixture: client A owns P1's recorded controls and client B owns P2's. Each client receives the other player's controls over the network and simulates both fighters. The fixture is a diagnostic input source, not a new public replay-watch mode.

The final acceptance run uses Slippi Direct matchmaking with two distinct Slippi Launcher accounts, then Slippi's ENet peer connection. A loopback ENet pair is an earlier integration gate, not the final claim. The fixture must be a modern online recording with physical buttons, L/R trigger values, and all four raw stick bytes (Slippi 3.17 or later); both players must be ordinary human ports 1 and 2 on a vanilla-compatible stage. The runner rejects unsuitable fixtures with a reason. The fixture and disc remain private and ignored by Git.

Success requires all of the following, from both process logs and machine-readable traces:

1. Both clients complete matchmaking and the Slippi peer handshake; the accepted peer identity and assigned P1/P2 roles are logged without credentials.
2. Both reach the same VS match, advance from frame -123 through the fixture's final frame, and receive changing remote inputs over ENet. Reading the remote port's input directly from the local `.slp` is prohibited and counted as a test failure.
3. Every finalized post-frame record for both fighters agrees between clients and with the fixture for action, position, facing, damage, and stocks; absent frames or players fail. Finalized gameplay checksums agree. The run reports packets, acknowledgements, confirmed frames, rollbacks, and first divergence.
4. A negative control changes one local input and produces a deterministic first divergence. Latency/loss injection produces rollback while preserving the original result. A title-screen-only or all-neutral run cannot pass.
5. Each client writes a readable `.slp` of the resulting match. The outputs are checked for a complete Game Start / frame / Game End sequence and compared against the source's finalized gameplay fields. We do not claim byte-for-byte identity of metadata or speculative frames.

This test proves GD-client-to-GD-client compatibility with Slippi's matchmaking and peer wire path. Compatibility with an unmodified Slippi Dolphin opponent requires a separate follow-up match and is not claimed from two identical clients alone.

## Existing implementation to retain

`melee/pc/platform/gw_replay.c` parses and records `.slp` events; `gw_rollback.c` owns prediction, snapshots and finalized gameplay state; `gw_netplay.c` and `gw_net.c` provide GD's existing custom online service. Keep that existing service as the default. Put the Slippi path behind an explicit experimental launch setting and a C-facing adapter. Do not port Dolphin's EXI device or savestate system: our native game already has the corresponding hooks.

The present replay parser stores processed fighter inputs and optional UCF stick bytes, but discards physical buttons and L/R trigger values. The present netplay path transmits 11-byte raw `PADStatus`, forces live-pad sampling, and cannot arm while an `.slp` is active. The new mode must explicitly bridge those boundaries. It must never rely on two clients independently reading both players from the fixture.

## Network and match design

Use Slippi's ENet peer wire format: three channels; reliable control traffic; unsequenced PAD (channel 1) and ACK (channel 2). Serialize SFML-style packets with network-order integers and length-prefixed strings. Implement the necessary two-player messages: PAD (`0x80`), ACK (`0x81`), match selections (`0x82`), connection selection (`0x83`), and match-preparation steps (`0x85`); handle or explicitly reject other message types. PAD has a 14-byte header and eight bytes per input, newest first. Maintain a bounded unacknowledged input queue and resend until ACKed. Adapt decoded remote pads into `gw_rb_submit_remote_input`, and obtain finalized checksums through `gw_rb_checksum`; preserve the existing seven-frame rollback bound.

For replay-driven runs, parse physical buttons, floating-point L/R trigger values and raw stick bytes from the fixture. Quantize the trigger values into Slippi's eight-byte PAD representation with an explicit, tested rule. Round-trip each fixture pad through the same PAD decoding and native pad-processing path used by Slippi online before accepting the fixture. Define and test a single mapping from `.slp` frame indices (beginning at -123) to Slippi online PAD frame indices (beginning at 1 after the configured input delay); do not conflate the two counters. Both peers use the fixture's Game Start data and synchronized initial RNG seed. Only the assigned local port contributes input; the other port must arrive from ENet. For online recordings, the existing per-frame online seed rule applies. Reject a fixture if raw-to-processed input does not match its recorded Pre-Frame values, rather than silently sending processed values in a non-Slippi packet.

Support two connection modes sharing one peer adapter. Loopback mode takes two explicit local ports and fabricated match assignment for deterministic tests; it makes no public report/upload. Public Direct mode connects to `mm.slippi.gg:43113`, sends Slippi's `create-ticket` request with the user's existing Launcher `user.json` credentials and a Direct connect code, then consumes the assigned peer addresses and match details. The accounts are never created, modified, logged or copied into build artifacts. Require two distinct user profiles for the two-client test. Report server version/auth errors clearly; do not fake a newer app version to bypass a rejection. No replay upload, match report, Ranked, Unranked, Teams, or stock-Dolphin compatibility claim is part of this slice.

## Verification and operating constraints

Use source-level packet vectors and a local ENet peer test before launching the game. Build through `tools/port/build.sh`; inspect the log for shim failures and confirm the bridge fixpoint. Keep the six console replay parity cases and the 185-test ACE suite green. The Slippi run uses a vanilla NTSC 1.02 disc because its gameplay data must agree with Slippi, while normal project smoke tests continue to use ACE. Game runs use `MELEE_VOLUME=3`, visible windows, no screenshots, and at least 8 GB free physical memory before each launch. Only two `melee-pc` processes run during a short paired sweep, with separate run/build roots; stop only the PIDs this test started, after checking their executable paths. GD judges visual/controller feel; agents report logs and numbers.

The networking code belongs under `melee/pc/` (GPL-2.0-or-later). ENet and any adapted code retain their licenses and precise upstream attribution in source headers and dependency notices. Do not commit a replay fixture, disc bytes, Slippi credentials, or Nintendo assets.

## Source basis and limits

- [Project Slippi's `.slp` specification](https://github.com/project-slippi/slippi-wiki/blob/71c6a395f841ff67f75ab4c0084fd1d6ee22c2db/SPEC.md) defines the replay fields, not the peer protocol.
- [Project Slippi's Dolphin peer client](https://github.com/project-slippi/dolphin/blob/41a7a3a110ed52999486ae1901c8fbb9a63d4f13/Source/Core/Core/Slippi/SlippiNetplay.cpp) and [matchmaking client](https://github.com/project-slippi/dolphin/blob/41a7a3a110ed52999486ae1901c8fbb9a63d4f13/Source/Core/Core/Slippi/SlippiMatchmaking.cpp) define the wire path; the server implementation is not public here.
- [Melee Unlocked's native port](https://github.com/Hero88go/melee-unlocked/blob/4d1aa844e918ca67277fa63d84063577bfc35715/port/runtime/hle/slippi_net.cpp) is a GPL-2.0-or-later adaptation and test reference. Its [two-process runner](https://github.com/Hero88go/melee-unlocked/blob/4d1aa844e918ca67277fa63d84063577bfc35715/tools/online_pair.py) does not itself assert replay parity or a completed match.
- [999sian/melee-pc](https://github.com/999sian/melee-pc) uses a different, custom netplay protocol. Its confirmed-frame recording and acceptance methodology are references, not Slippi wire code.
