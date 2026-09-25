# Slippi two-client replay compatibility implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement independent tasks in separate long-lived lanes. Checkboxes track completion; each lane must build and test its change before integration.

**Goal:** Play one online `.slp` as P1 on one GD client and P2 on another, with the other player's input arriving through Slippi's Direct matchmaking and ENet peer protocol, and prove a complete matching game.

**Architecture:** Retain native replay parsing, rollback, snapshots and GD's current netplay service. Add a narrowly scoped Slippi adapter: replay-derived raw local pads, a Slippi ENet peer transport, Direct matchmaking, and a two-process verifier. The transport and fixture validator are independently testable before either client launches.

**Tech Stack:** C/C++ shims on Windows, ENet, Slippi SFML packet encoding and matchmaking JSON, Python 3 verification, existing `tools/port/build.sh` and replay parity tools.

**Spec:** `docs/superpowers/specs/2026-09-24-slippi-two-client-replay-design.md`

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

**Interfaces:** `int gw_Replay_SlippiFixtureInfo(GwSlippiFixtureInfo *out)` returns version, online flag, first/last frames, two human ports, seed and a copy of Game Start bytes without exposing the raw file. `int gw_Replay_SlippiPad(int port, int slp_frame, GwSlippiPad *out)` returns only the named port's eight-byte wire pad and rejects missing physical fields. `int gw_SlippiPad_ToRb(const GwSlippiPad *, GwRbInput *)` converts received bytes to native raw-pad input. `int gw_SlippiPad_RoundTrip(int port, int frame)` compares a decoded raw pad's processed result with recorded Pre-Frame input. Define `GwSlippiPad` as exactly eight unsigned bytes in wire order; document every byte from official source.

- [ ] Read the official `.slp` Pre-Frame offsets and official Slippi PAD serializer; record byte order, quantization and minimum event size in the new header with pinned source links.
- [ ] Write failing tests for a valid two-human online frame, missing physical fields, absent player input, truncated event, trigger 0/1/half-step, and game-frame to online-PAD-frame mapping (`-123` to online frame `1 + delay`). Run the focused test and capture its expected failure.
- [ ] Extend replay storage to retain physical buttons and L/R floats; implement the eight-byte encoder/decoder and fixture rejection. Use bounds checks before reading each optional field. Run focused tests to green.
- [ ] Run the six-case replay parity script and inspect failures; the new fields must not alter ordinary playback. Commit the lane change with the required footer.

### Task 2: Replay-backed local source for rollback (Alpha lane, after Task 1)

**Files:** Modify `melee/pc/platform/gw_rollback.c`, `gw_rollback.h`, `gw_replay.c`; focused tests in `melee/pc/tests/`.

**Interfaces:** `MELEE_SLIPPI_REPLAY_ROLE=1|2` activates this source only with the experimental Slippi mode. `gw_rb_submit_local_input` receives only the assigned port's decoded raw pad; the remote port's confirmation is exclusively `gw_rb_submit_remote_input`. Add counters `gw_rb_local_fixture_reads(port)` so the verifier can assert remote reads remain zero.

- [ ] Write a test in which role 1 requests P2 locally and assert refusal; also test role 2 and off-mode behavior. Run to see the expected failure.
- [ ] Change `rb_init` so experimental Slippi playback does not force `rb.src=live` and does not mirror the existing fake-network path. Seed the delay window with neutral pads and use the tested `.slp`/online frame mapping.
- [ ] Assert both roles use the same Game Start and seed and that only network delivery confirms the remote slot. Run focused rollback tests and replay parity to green. Commit.

### Task 3: Slippi ENet peer and packet codec (Beta lane)

**Files:** Create `melee/pc/platform/gw_slippi_wire.h/.c`, `gw_slippi_peer.h/.c` (or `.cpp` if required by ENet), focused codec tests, and dependency notice in `melee/pc/DEPENDENCIES.md`. Add shim objects to each lane's curated `_build/.../melee_link_objects.rsp` and the shared template at integration; add ENet library to the link list if linked separately.

**Interfaces:** `gw_slippi_peer_start(const GwSlippiPeerConfig *)`, `gw_slippi_peer_poll(int current_online_frame)`, `gw_slippi_peer_send_pad(int online_frame, const GwSlippiPad *, uint32_t checksum)`, `gw_slippi_peer_stats(GwSlippiPeerStats *)`, `gw_slippi_peer_close()`. `GwSlippiPeerConfig` contains local/remote address, assigned port, remote port, match ID and an explicit loopback/public mode; no credential fields. Receive path calls `gw_rb_submit_remote_input_e` only after validating packet length, player and frame.

- [ ] Pin official Dolphin's ENet channel and PAD/ACK/selections/preparation wire semantics; obtain a compatible ENet source/library with license and reproducible build instructions.
- [ ] Write failing codec vectors for PAD header/endian order, multiple newest-first eight-byte pads, ACK, bad size, bad index, stale epoch, out-of-window frame and bounded resend queue. Run focused tests to see expected failures.
- [ ] Implement codec and three-channel ENet peer, reliable control messages, unsequenced PAD/ACK, retransmission and checksum exchange. Run codec and two-process loopback peer tests to green; verify the second process receives non-neutral changing input and a bad packet is discarded. Commit.

### Task 4: Slippi Direct matchmaking (Charlie lane)

**Files:** Create `melee/pc/platform/gw_slippi_match.h/.c` (or `.cpp`), a private-profile JSON loader, focused response/parser tests and dependency notice. No credential files belong in the worktree.

**Interfaces:** `gw_slippi_match_start(const char *user_json_path, const char *direct_code)`, `gw_slippi_match_poll(GwSlippiMatchAssignment *)`, `gw_slippi_match_close()`. `GwSlippiMatchAssignment` carries assigned P1/P2 port, peer public/LAN addresses and match ID. The separate peer match-selection handshake carries stage/rules/seed and agreed input delay. Error strings redact play key and token values.

- [ ] Pin official create-ticket/get-ticket packet schema and Direct search mode, then create sanitized fixture responses for tests. Do not hard-code a guessed current app version or print profile contents.
- [ ] Write failing tests for successful assignment, two distinct profiles, malformed JSON, missing key, expired key, rejected version, timeout, and no secret in logs. Run focused tests to see expected failures.
- [ ] Implement Launcher profile parsing and ENet matchmaking against `mm.slippi.gg:43113`; keep credentials in memory only. Run parser tests and a read-only authentication probe using the user's existing profile if reachable. Commit. If only one profile exists, mark paired public test pending without creating or modifying an account.

### Task 5: Native mode integration (integration lane, after Tasks 1–4)

**Files:** Modify `melee/pc/platform/gw_runtime.c`, `gw_replay.c`, `gw_rollback.c`, `gw_netplay.c` only at explicit integration hooks; create `gw_slippi_mode.c/.h`. Update `tools/port/build.sh` link inputs or curated response files as required, plus `melee/pc/DEPENDENCIES.md`.

**Interfaces:** `MELEE_SLIPPI_MODE=loopback|direct` gates all new behavior; loopback consumes explicit peer UDP ports, Direct consumes profile path and code. `gw_SlippiMode_Scene()` supplies the match scene; `gw_SlippiMode_Tick()` pumps the peer on the game thread; `gw_SlippiMode_MatchOver()` closes it. The mode logs role, peer identity, accepted fixture, confirmed frame and checksum without secrets.

- [ ] Write a failing headless boot test proving off-mode still takes GD's existing netplay path and invalid mode/fixture fails before launch.
- [ ] Wire mode initialization, scene selection, Game Start/seed, rollback lifecycle, local replay source and peer tick. Handle mismatch or match end with a nonzero diagnostic status. Run the focused boot test and a build; inspect the log for `error` and `FAIL`, bridge fixpoint, and missing shim objects.
- [ ] Run the six-case replay parity script and 185 ACE tests after integration. Commit only when they pass or a precisely isolated preexisting failure is documented.

### Task 6: Two-client acceptance runner (integration lane)

**Files:** Create `tools/slippi/two_client_replay.py`, `tools/slippi/compare_finalized.py`, and `tools/slippi/README.md`; private fixture/account paths supplied at runtime and ignored.

**Interfaces:** `two_client_replay.py --fixture <private.slp> --iso <vanilla.iso> --mode loopback|direct --user-a <user.json> --user-b <user.json> --code-a <code> --code-b <code>` emits a JSON result with `match_started`, `last_frame`, `received_remote_frames`, `remote_fixture_reads`, `checksums_equal`, `postframes_equal`, `rollbacks`, `first_divergence` and SLP output validation. The runner never prints credential values.

- [ ] Write failing verifier fixtures: identical title-screen logs, remote-fixture-read violation, all-neutral pads, missing final frame, mismatch and truncated output `.slp`; only a complete pair can pass.
- [ ] Implement two-process launcher with separate run/build roots, 8 GB free-RAM preflight, PID/path-tracked cleanup and timed exit. Compare both clients' finalized traces against each other and source for action, position, facing, damage and stocks; require complete Game Start/End event sequences in each output.
- [ ] Run loopback with one private online `.slp`; inject one altered P1 pad for a deterministic first divergence, then latency/loss to force rollback with identical final state. Save sanitized JSON logs in an ignored run directory and commit the runner.
- [ ] Run public Direct with two distinct existing Slippi profiles and the same fixture; record both peer identities, P1/P2 roles, packet counts, confirmed frames, complete result, and two readable `.slp` outputs. If a second profile or service acceptance is unavailable, report that exact acceptance blocker rather than call loopback success full compatibility.

### Task 7: Review and integration

**Files:** The game branch containing Tasks 1–6 and its build/link inputs; this plan's checkboxes.

- [ ] Have an independent agent review protocol conformance, credential handling, remote-only input guarantee and the verifier's false-green guards. Fix findings and rerun affected tests.
- [ ] Run clean build, replay parity, 185 ACE tests, and the paired run once after the final code change. Review changed files for fixtures, credentials, disc bytes and license notices.
- [ ] Merge the tested branch to `pc-port` and push only after the explicit acceptance evidence exists; report any unproven stock-Dolphin interoperability separately.
