# Slippi two-client replay compatibility implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement independent tasks in separate long-lived lanes. Checkboxes track completion; each lane must build and test its change before integration.

**Goal:** Play one online `.slp` as P1 on one GD client and P2 on another, with the other player's input arriving through Slippi's Direct matchmaking and ENet peer protocol, and prove a complete matching game.

**Architecture:** Retain native replay parsing, rollback, snapshots and GD's current netplay service. Add a narrowly scoped Slippi adapter: replay-derived raw local pads, a Slippi ENet peer transport, Direct matchmaking, and a two-process verifier. The transport and fixture validator are independently testable before either client launches.

**Tech Stack:** C/C++ shims on Windows, ENet, Slippi SFML packet encoding and matchmaking JSON, Python 3 verification, existing `tools/port/build.sh` and replay parity tools.

**Spec:** `docs/superpowers/specs/2026-09-24-slippi-two-client-replay-design.md`

**Implementation status (2026-09-24):** Native fixture, PAD, rollback, wire, peer,
matchmaking and mode tests pass through `build.sh`; the runner has 39 Python tests.
The Direct pair `slippi-20260924-220354-7653e8-{1,2}` completed fixture frames
-123..902 with 2,052 player records, exact processed inputs/post-frame state and
matching hashes. Each client sent and received 1,026 applied PAD frames, read
1,024 local fixture pads and zero remote fixture pads; roles were server-assigned
P2/P1, with 16/120 rollbacks and zero desyncs. A 60 ms, 2% loss loopback run
`slippi-20260924-220451-39ac8e` passed with 126 dropped relay packets. These
GD/GD results do not establish compatibility with stock Slippi Dolphin. The
final six ordinary console replay parity cases passed on the current Delta
build (1,026, 1,118, 1,149, 1,232, 1,270 and 1,549 frames), with exact
post-frame state and RNG. The live input negative control passed: the altered P1
A press caused the first input and action divergence at frame 45, while both
clients agreed through frame 902. The final ACE suite passed 185/185. Tested game
source is `c1b08a92a`; `pc-port` also preserves the current Discord documentation.

## Global Constraints

- The final acceptance uses a vanilla NTSC 1.02 disc, two distinct existing Slippi Launcher accounts, and one private online `.slp` recorded on Slippi 3.17 or later.
- Existing GD netplay remains default; the Slippi path is explicit and experimental. No disc, `.slp`, token, Nintendo asset, match report or replay upload is committed or sent.
- New `pc/` code is GPL-2.0-or-later; ENet and adapted upstream code need precise license and origin notices. Build with `tools/port/build.sh`, not raw clang.
- Before each game launch verify at least 8 GB free RAM. Use `MELEE_VOLUME=3`, visible windows, no screenshots; stop only PIDs started by the run after confirming executable paths.
- Preserve six console replay parity cases and the 185-test ACE suite. Agent build/log verification does not replace GD's visual/controller test.
- Commit messages end with `Co-Authored-By: OpenAI Codex <noreply@openai.com>`; integrate only after tests. The user already authorized Git/GitHub operations.

## Review Focus

- A truncated or pre-3.17 `.slp` must fail fixture validation before any peer connection; Task 1 owns the test.
- Physical trigger floats at boundaries 0, 1 and between byte steps must quantize deterministically; Task 1 owns the test.
- PAD packets with wrong length, player index or frame order must not enter rollback; Task 3 owns the test.
- A valid account with an expired play key or rejected app version must report a sanitized error and exit; Task 4 owns the test.
- Both clients reading both players locally, a title-screen-only run, or all-neutral inputs must fail the verifier; Task 6 owns the test.

---

### Task 1: Replay fixture and raw pad conversion (Alpha lane)

**Files:** Modify `melee/pc/platform/gw_replay.c` and `melee/pc/platform/gw_rollback.h`; create `melee/pc/platform/gw_slippi_pad.h`, `melee/pc/platform/gw_slippi_pad.c`, and `melee/pc/tests/slippi_pad_test.c` (test runner location may follow current test harness). Update the game worktree's build response file if a new shim object is needed.

**Interfaces:** `int gw_Replay_SlippiFixtureInfo(GwSlippiFixtureInfo *out)` returns version, online flag, first/last frames, two human ports, seed and a copy of Game Start bytes without exposing the raw file. `int gw_Replay_SlippiPad(int port, int slp_frame, GwSlippiPad *out)` returns only the named port's eight-byte wire pad and rejects missing physical fields. `int gw_SlippiPad_ToRb(const GwSlippiPad *, GwRbInput *)` converts received bytes to native raw-pad input. Define `GwSlippiPad` as exactly eight unsigned bytes in wire order; document every byte from official source. Stateful processed-input equivalence must be checked through the running game's PAD pipeline during integration; a host-only conversion helper cannot certify it.

- [x] Read the official `.slp` Pre-Frame offsets and official Slippi PAD serializer; record byte order, quantization and minimum event size in the new header with pinned source links.
- [x] Write failing tests for a valid two-human online frame, missing physical fields, absent player input, truncated event, trigger 0/1/half-step, and applied game-frame to online-PAD-frame mapping (`-123` to online frame `1`, independent of delay). Run the focused test and capture its expected failure.
- [x] Extend replay storage to retain physical buttons and L/R floats; implement the eight-byte encoder/decoder and fixture rejection. Use bounds checks before reading each optional field. Run focused tests to green.
- [x] Run the six-case ordinary replay parity script after integration. All six
  cases passed with exact post-frame state and RNG on the current Delta build;
  the Alpha implementation is committed.

### Task 2: Replay-backed local source for rollback (Alpha lane, after Task 1)

**Files:** Modify `melee/pc/platform/gw_rollback.c`, `gw_rollback.h`, `gw_replay.c`; focused tests in `melee/pc/tests/`.

**Interfaces:** `gw_rb_slippi_configure(local_port, delay, peer_tick)` selects the
local source after fixture validation. `gw_rb_slippi_local_pad(online_frame, out)`
exposes sampled local raw truth; `gw_rb_slippi_receive(epoch, remote_port,
online_frame, pad)` accepts and confirms only checked peer delivery. The mode
calls `gw_rb_slippi_finalized()` after the last simulation to flush trace and
recording, and reads `gw_rb_local_fixture_reads(port)` for source evidence.
`MELEE_SLIPPI_REPLAY_ROLE=1|2` selects the role in loopback; Direct uses the
server-assigned role. Initial delay frames use canonical neutral PADs after
checking both ports' recorded processed controls, since separately recorded
physical startup fields can contain noise.

- [x] Test role 1 refusal of P2 remote input as local, role 2 source isolation,
  off-mode refusal, and startup physical noise with neutral processed input.
- [x] Give the experimental mode its own rollback source, seed local neutral
  PADs for the initial delay, and retain -123 to online PAD frame 1 mapping.
- [x] Test that remote initial PADs remain unconfirmed until peer delivery,
  malformed/duplicate deliveries are refused, and both roles read only their
  assigned local fixture controls. Direct pair evidence confirms common fixture
  Game Start/seed behavior; focused rollback and fixture tests pass. The final
  six-case ordinary replay parity run passed and is recorded in Task 1/5.

### Task 3: Slippi ENet peer and packet codec (Beta lane)

**Files:** Create `melee/pc/platform/gw_slippi_wire.h/.c`, `gw_slippi_peer.h/.c` (or `.cpp` if required by ENet), focused codec tests, and dependency notice in `melee/pc/DEPENDENCIES.md`. Add shim objects to each lane's curated `_build/.../melee_link_objects.rsp` and the shared template at integration; add ENet library to the link list if linked separately.

**Interfaces:** `gw_slippi_peer_start(const GwSlippiPeerConfig *)`,
`gw_slippi_peer_poll(peer, current_online_frame)`,
`gw_slippi_peer_send_pad(peer, online_frame, pad_bytes, checksum_frame, checksum)`,
`gw_slippi_peer_stats(peer, out)`, and `gw_slippi_peer_close(peer)`.
`GwSlippiPeerConfig` carries addresses, assigned port indices, match ID,
loopback/public mode and callbacks, with no credentials. The mode's remote-PAD
callback calls `gw_rb_slippi_receive`; the peer ACKs only a stored or identical
duplicate pad after wire and frame validation.

- [x] Pin official Dolphin wire semantics; vendor ENet with its license and
  reproducible `build.sh` link inputs.
- [x] Test PAD header/endian order, newest-first pads, ACK, bad size/index,
  out-of-window and noncontiguous frames, bounded resend queue and rollback's
  epoch/refusal guard. These checks span wire, peer and rollback tests.
- [x] Implement three-channel ENet transport, control messages, unsequenced
  PAD/ACK, retransmission and checksums. Native wire and two-process peer tests
  pass, including changing non-neutral input and malformed-packet refusal.

### Task 4: Slippi Direct matchmaking (Charlie lane)

**Files:** Create `melee/pc/platform/gw_slippi_match.h/.c` and
`gw_slippi_match_json.c`, with focused response/parser tests and dependency
notice. No credential files belong in the worktree.

**Interfaces:** `gw_slippi_match_start(user_json_path, direct_code)` or
`gw_slippi_match_start_profile(profile, direct_code)` for in-memory profiles,
`gw_slippi_match_poll(out)`, `gw_slippi_match_close()` and sanitized
`gw_slippi_match_error()`. Assignment carries P1/P2 ports, peer public/LAN
addresses, match ID, UDP port and private UID fingerprints. The separate peer
selection handshake checks stage, character and seed; the native mode uses its
configured input delay. Errors redact play keys and tokens.

- [x] Pin create-ticket/get-ticket schema and Direct search mode; use the
  profile's `latestVersion` and sanitized synthetic responses.
- [x] Native parser tests cover assignment, distinct profiles, malformed JSON,
  missing key, expired-key and rejected-version responses, timeout boundaries
  and secret redaction.
- [x] Implement Launcher profile parsing and ENet matchmaking against
  `mm.slippi.gg:43113`, with credentials in memory. The paired Direct run used
  two existing accounts and received reciprocal server-assigned P1/P2 roles.

### Task 5: Native mode integration (integration lane, after Tasks 1–4)

**Files:** `melee/pc/platform/gw_runtime.c`, `gw_replay.c`,
`gw_rollback.c`, new `gw_slippi_mode.c/.h` and
`gw_slippi_mode_config.h`, plus `tools/port/build.sh` link inputs and
`melee/pc/DEPENDENCIES.md`. The ordinary `gw_netplay.c` service is unchanged.

**Interfaces:** `MELEE_SLIPPI_MODE=loopback|direct` gates all new behavior;
loopback consumes explicit peer UDP ports, while Direct consumes a profile path
or in-memory profile and connect code. `gw_SlippiMode_Scene()` supplies the
match scene and `gw_SlippiMode_Tick(online_frame)` pumps ENet on the game thread.
After final confirmation, the mode finalizes the recorder and evidence and exits
with a diagnostic status. It records role, redacted peer identity, confirmed
frame and checksums without logging credentials.

- [x] Test off-mode gating and invalid/conflicting Slippi configuration before
  network initialization. The native mode test covers configuration; fixture
  rejection is covered by fixture and rollback tests.
- [x] Wire scene selection, Game Start/seed, rollback lifecycle, local fixture
  source and peer tick. Native mode and integration tests pass; the Delta full
  build log is clean and bridge regeneration reaches its fixpoint. Mismatches
  and incomplete matches exit nonzero.
- [x] Run the six-case ordinary replay parity script after integration; all
  six cases passed on the current Delta build with exact post-frame state and RNG.
- [x] Run the final 185 ACE tests after integration: 185/185, exit 0, FATAL 0.

### Task 6: Two-client acceptance runner (integration lane)

**Files:** Create `tools/slippi/two_client_replay.py`, `tools/slippi/compare_finalized.py`, and `tools/slippi/README.md`; private fixture/account paths supplied at runtime and ignored.

**Interfaces:** `two_client_replay.py --fixture <private.slp> --iso
<vanilla.iso> --game-root <checkout> --build-root <lane-build> --mode
loopback|direct`; Direct also takes `--user-a`/`--user-b` or
`--accounts-helper`. Loopback accepts `--latency-ms`, `--loss-percent`,
`--require-rollback` and `--negative-control`. The runner writes `result.json`
with handshake, complete frame/input/post-state, checksum, rollback and first
divergence results without printing credentials. `compare_finalized.py` checks
every processed Pre-Frame control and exact frame/player shape as well as final
post-frame traces and hashes.

- [x] Verifier tests reject identical title-screen evidence, remote fixture
  reads, all-neutral controls, missing/extra final rows, processed-input or
  checksum mismatch, truncated/malformed output `.slp` and reused artifacts.
  Mutation and first-divergence logic has unit tests and a passing live control.
- [x] Implement two-process launch with separate run directories, 8 GB RAM
  preflight, PID/path-scoped cleanup and timed exit. Require complete Game
  Start/End, processed Pre-Frames, post-frame traces and hashes.
- [x] Run the live altered-P1-input negative control. The separate 60 ms,
  2% loss loopback run passed with rollback and identical final artifacts;
  run `slippi-20260924-221022-1ade6d` rejects the original at the altered input's
  frame 45 while both clients agree on the complete changed match.
- [x] Run public Direct with two distinct existing profiles and the same
  fixture. The paired run completed both server-assigned roles, full frame
  range, reciprocal account tags, packet counts and readable `.slp` outputs.
  Stock-Dolphin interoperability remains unproven.

### Task 7: Review and integration

**Files:** The game branch containing Tasks 1–6 and its build/link inputs; this plan's checkboxes.

- [x] Have an independent agent review protocol conformance, credential handling, remote-only input guarantee and the verifier's false-green guards. Fix findings and rerun affected tests.
- [x] Run the supported full build, replay parity, 185 ACE tests, and the paired run after the final game code change. Review changed files for fixtures, credentials, disc bytes and license notices. The final integration adds only Discord documentation to the tested game source.
- [x] Merge the tested branch to `pc-port` and push after the explicit acceptance evidence exists: `9ec3c7397`, including the independently published Discord documentation. Stock-Dolphin interoperability is explicitly unverified.
