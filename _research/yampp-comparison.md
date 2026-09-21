# YAMPP vs our port: rollback and determinism design comparison

Written 2026-09-21. Read-only study of `github.com/sonsegajp/YAMPP` (shallow clone, Sept 2026 tree),
compared against our `pc-port` and the three rollback branches (`agent/snapcost`, `agent/rbsession`,
`agent/netcode`).

**Licence rule.** YAMPP has no top-level licence file (only `CREDITS.md` and `licenses/third-party`), so
its own code is not licensed to us. Nothing here is copied or structurally mirrored; everything is
paraphrase, and file paths in *their* repo are pointers for a human to read, not material to reuse. Every
recommendation in section 6 is written so it can be derived and implemented from first principles.

---

## 1. What YAMPP is, and how it differs from us

**Architecture (their `docs/architecture.md`, `native/`).** It is a *static recompilation* of Melee 1.02's
`main.dol`, not a decomp retarget. A Python pipeline (`native/recompiler/`: `ppc.py`, `emit.py`,
`discover.py`, `dol.py`, `dtk_symbols.py`; `scripts/regenerate_game.py`) turns the player's own DOL into
native C, generated locally (the committed tree contains only a 20 KB `native/games/gale01/game.py`, no
generated code). The decomp is used only for symbol names, struct layouts and behavioural reference. The
generated code runs against a **24 MiB guest address space plus a `Context` struct holding the PPC register
file**. `native/host/gxrt/` supplies the platform: HLE of SDK routines (`hle_gale01.c`, `hle_sdk_math.c`),
a cooperative host-thread scheduler standing in for GameCube OS threads (`hle_thread.c`), the GX command
FIFO translated to Aurora (`gx_translate.c`, `aurora_link.c`), audio, card, pads. `native/recompiler/oracle.py`
single-steps a function in Unicorn and diffs it against the generated code's own trace (their
correctness tool for the recompiler). Server side (`server/`): a Python lobby/relay with an optional UDP
datagram path. Also: Workshop editor, costume-pack registry, Lua VM, widescreen, an Akaneia importer.

**Ours.** The decomp is compiled to C, retargeted to i686 by `gwtool` (byte-swapping memory accesses so the
game sees big-endian guest memory), and *runs natively*: no register file, no host threads, one
game thread. A PPC interpreter exists only for m-ex code blobs. State = MEM1 (24 MB) + about 0.9 MB of
native globals.

**What that changes.**

| Consequence | YAMPP (recompiled PPC) | Ours (decomp -> native x86) |
|---|---|---|
| Floating point | Instruction-level emulation of Gekko FP (their notes mention signaling NaNs, paired singles in software), so console-exact arithmetic is the default | Compiler-emitted SSE; console exactness had to be *earned* (MSL trig, SDK `PSVECNormalize` sequence, fused multiply-add lowering in gwtool). Done, but cost a day of ULP hunting |
| Snapshot contents | Registers + 24 MiB RAM + ARAM + audio + device/DMA state + **scheduler continuations** | MEM1 + globals only. No registers, no threads |
| Native call stack | Not snapshottable. They had to re-express the scene loop as a callable "one frame step" that returns each frame; a restore is *refused* if the host scheduler changed since the snapshot | Not an issue: the scene loop is our own C, single thread; the loop already runs k frames per render |
| Speed | They needed matrix-transfer wrappers, FIFO fast paths, an entry-hook rework and an "overlap guest with renderer" handoff to approach 60 FPS; 4-player Akaneia around 55-59.7 | 60 fps in 4-player combat after our frame-tail fix; interpreter about 0.2% of game thread |
| Console replay | Not a stated goal; no `.slp` tooling seen | `.slp` playback/recording, first-divergence tooling, exact through thousands of frames |
| Cross-CPU determinism | Not claimed ("cross-CPU determinism" is listed as not established); they require *byte-identical executables* for play | Bit-identical on every SSE2 CPU by construction (fmuladd lowering, our own libm); still to be proven across machines |
| Mod scope | Rollback limited to stock fighters/stages plus verified costume packs; gameplay-changing content blocked "because its state is not snapshotted". A selective Akaneia route (fighters/stages/music) also passes their game-pair tests | m-ex runs through the same MEM1 snapshot, but rollback with m-ex state (interpreter registers, thunk tables) is untested |

Doc drift worth knowing: `architecture.md` says confirmed hash mismatches "stop an inconsistent session";
`netplay.md` says a mismatch is recorded, shown on screen, and *never acted on*. The latter matches the
code (`native/host/gxrt/netplay.c`).

---

## 2. Rollback design, side by side

| Topic | YAMPP | Ours (branch) | Verdict / what to adopt |
|---|---|---|---|
| Rollback window | 8 frames, 9 snapshot slots, hard stop: never predict past it, simulation waits (`rollback.h`, `rollback.c`) | max 7 (env up to 12), stall when newest confirmed frame is too far behind (`agent/rbsession`) | Equivalent. Keep 7-8 as default |
| Snapshot content | Full copy of registers, 24 MiB RAM, ARAM, audio state, DMA/device state, scheduler checkpoint, virtual clock; ~24+ MB per slot (`netplay_rollback.inc`) | MEM1 + globals, ~26 MB per slot; excluded: audio, pad queue, video/GX shadow, card, movies, perf, rumble reset (`gw_snap.c`) | Same idea; ours smaller-surface. They also protect the GX cache / VI / draw-done regions across a restore because the GPU is external state, which mirrors our GX-shadow exclusion |
| Snapshot cost | Straight full copies; no dirty tracking; no per-frame cost published | Dirty-page write-watch on `agent/snapcost`: save 0.26 ms, load 0.31 ms, hash 0.26 ms (was 2.4/2.4) | **Ours ahead.** No change needed |
| Frames per replayed step | Each replayed frame re-saves its own snapshot, then runs the sim step only; **no render calls on replay**; the visible frame is presented once | Each resimulated frame runs logic **and the render calls minus the present** (1.2 ms/frame) because full-memory compare demanded it | **Open question** (section 7): their design skips render on replay and still passes curated-hash checks |
| Render->logic coupling | Fixed by recomputing the off-screen-damage eligibility natively before every sim step (they name the same three functions we found: fighter camera-box test, the magnifier draw callback, the off-screen flag consumer) | Computed by logic at end of each frame (`agent/rendcouple`, merged) | Same defect, same class of fix. Ours also removed the fighter-side flag written in the fighter draw callback |
| Input model | 8-byte input per port (buttons, 2 sticks, 2 triggers), per-frame history of *actual* vs *used*, conflicting re-delivery of a confirmed input rejected as an error | Per slot (port*2+follower) processed floats + raw stick bytes, 28 bytes (`GwRbInput`); rings of confirmed and used | Theirs is smaller on the wire; ours carries what UCF needs (see 6.3) |
| Prediction | Repeat the last actual (else last used) input; a future input never leaks backwards under reordering (tested) | Repeat last contiguous confirmed input | Same. Add their reordering test (6.2) |
| Input delay | Automatic: relay resolves one number 1-6 from both RTTs and sends it to both in the start message; frames before the delay are pre-seeded as known-empty input on every port; both peers must use the identical value | Fixed default 2, negotiated in the handshake config (`gw_net` ACCEPT carries it) | We agree on both-peers-identical; add auto-resolution (6.3) |
| Input sampling | Pads sampled on an input clock faster than the sim; per frame take the *union* of button edges, the peak of each trigger, and the newest stick position (`pad_latch.h`) so short taps and trigger crossings are not lost | Live pads not yet wired to the session | **Adopt** (6.2) |
| Time sync | GGPO-style frame advantage: each side measures how far behind the peer it thinks it is, sends it in every packet; only if both sides agree who is ahead does the ahead peer skip half the difference, in 2-5 frame steps, decided on ~half a second (30 frames) of averaged evidence; RTT = median of 8 samples; scene change forgets drift, keeps RTT (`timesync.h`, `tests/timesync_test.c`) | EMA (1/8) of frame advantage with a cooldown, tuned only against a simulator (`gw_net.c`) | Compare against their behavioural tests (6.3) |
| Transport | TCP/TLS stream to a relay for lobby *and* input, plus an optional UDP datagram path once packets are seen arriving; every input packet names its frames and repeats the previous few | Direct UDP peer-to-peer, redundant all-unacked inputs, handshake with hash checks (`gw_net.c`) | Different topology (relay vs direct). Their finding on stream head-of-line blocking supports our UDP choice |
| Desync detection | Curated hash: RNG seed + about 18 fields per fighter (action state, facing, position, velocities, ground speed, input state, percent...), published **only for confirmed frames**, carried in every input packet, compared over a 256-frame ring; mismatch dumps the full field set and inputs on both peers (`netplay.c`) | Whole-state hash (dirty-page incremental) planned as the peer checksum (`agent/snapcost`) | **Two-tier hash recommended** (6.1) |
| Desync response | Report and keep playing; "the players decide" | Not decided | Decide policy explicitly (6.3) |
| Determinism levers | Virtual clock advanced 675000 ticks per frame; deferred DMA/audio callbacks drained at the frame boundary; audio advances one fixed 60 Hz slice per sim frame | Same virtual-clock and boundary-drain design (`gw_wait_idle` fix); audio *excluded* from snapshots, SFX gated during resim | Same conclusions reached independently. Their audio treatment is stronger (6.1, 6.2) |
| Audio during resim | Sim-visible audio state is snapshotted and restored; replay does not submit audio to the speaker; playback queue capped (~83 ms stale-drop) | Suppress SFX starts during resim; dedupe/kill not done | Adopt fixed-slice audio + snapshot of sim-visible audio state (6.2) |
| Scenes / menus | **Everything is synchronized**: menus, CSS, SSS, loading, results share input via *epochs* (frame numbers restart at 0 each scene; hash labels are (epoch, frame) and must never repeat); scene exit waits for confirmed input | Match scene only | Big product feature; epochs are cheap to design in now (6.2, 6.3) |
| Match start | Host rules applied to both peers; session entry resets VS selections through the original initializer; saved name tags hidden so both CSS lists match | `StartMeleeData` blob + seed in the handshake (`match_blob`), entry via the replay module's path (not built) | Same approach |
| Disconnects | Opponent silence *holds* the match for up to 45 s and resumes from the same frame; lobby reconnect keeps the player's seat 40 s; an unrecoverable drop cancels the scene through the game's own mode-cancel path (a plain exit scores a tie and can start Sudden Death) | Silent-peer timeout only | Adopt (6.3) |
| Compatibility gate | Hash of the running executable, DOL, FST, every extracted game file (canonical order), the disc image; renderer DLL excluded but the reloadable game-core DLL included; **files held open with read-share only for the session**; aspect ratio is part of the identity (widescreen camera changes guest state); rechecked at Ready and Start; done in a helper process so UI stays live | exe + ISO + mods hashes in HELLO, refuse on mismatch | Adopt the details (6.3) |
| Test evidence | Real two-process game pair through an impairment relay: passes only if it reaches a match, fingerprints match, at least 20 confirmed hash samples match, real rollback corrections occurred, no faults; also a model test: rollback engine vs independent lockstep over 3,109 frames / 1,814 corrections (`scripts/check_netplay_local.py`, `native/host/gxrt/tests/rollback_test.c`) | Single-process fake-latency acceptance vs zero-latency playback (bit-identical trace) on `agent/rbsession`; standalone transport tests on simulated network | Add the two-process pair once the adapter exists (4.1) |
| Reported numbers | 8,000-frame runs at 80 +/- 20 ms, delay 2: ~89 matching hashes, 15-38 corrections per peer, 0 declined corrections in the latest run | k=1/3/7 SyncTest 0 mismatches over 2,600 rollbacks | Comparable order of evidence; theirs is over a real network stack |

---

## 3. Problems they hit that we will hit

Each item: what went wrong, their documented cure (paraphrased), our status.

1. **Off-screen damage read a flag only produced while drawing.** Replay skipped the draw, so the 1% tick
   landed late by the number of replayed frames. Cure: recompute eligibility and the camera projection
   natively before each sim step. *Ours: fixed (rendcouple).* Lesson to keep: after a restore, any
   "derived once per rendered frame" value must be recomputed, not carried.
2. **Two machines never tick at the same rate** (60.000 vs 59.94 Hz); half a hertz is 30 frames a minute,
   past any window. Cure: symmetric frame-advantage correction where the ahead peer gives back *half*,
   both peers must agree who is ahead, corrections one frame at a time in steady state. *Ours: transport
   has an EMA scheme; not validated with two different-rate clocks.*
3. **A stream transport freezes on one lost packet, then bursts rollbacks.** Cure: input on datagrams;
   every packet names its frames and repeats the last few. *Ours: UDP by design.*
4. **Their public relay could not carry the datagram path.** The web proxy cannot forward UDP and the
   host firewall drops the port, so production advertises "no datagram port" and everyone uses the
   stream. Lesson: any relay needs an open UDP port from day one.
5. **Short taps and light trigger presses vanished** when the pad was sampled once per frame or merged into
   older samples; air-dodge triggers on a pad that only reports 75% range were unreachable. Cure: latch
   edges and trigger peaks between frames, keep sticks as latest position; shape the trigger so a click is
   reachable. *Ours: not yet wired for live pads.*
6. **Audio delay, gaps and duplicate sound.** Cure: fixed 60 Hz slice per sim frame, snapshot the
   simulated audio state, never submit audio during replay, cap and flush the playback queue on scene
   change. *Ours: gated SFX only; music and abandoned-timeline sounds open.*
7. **Results/unlock screens reused an old epoch** and the second match's stage cursor did not move on
   replay. Cure: online results branch defers local unlock/prize checks; scene driver refuses entry
   without a fresh epoch; test fails on any reused (epoch, frame) hash label.
8. **A disconnect scored a tie / launched Sudden Death.** Cure: cancel via the game's own mode-change
   path.
9. **Exit-time hang** under stall tests (cooperative shutdown checkpoints).
10. **A correction becomes impossible** (snapshot aged out, scheduler changed). Cure: *decline* it and keep
    playing the prediction; count and log the declines. *Ours: stall-before-overrun exists; a declined
    path should exist for the "snapshot missing" case.*
11. **Costume/pack ordering must be identical across peers**; per-peer differences in name tags, saved
    rules, aspect ratio all leak into simulation. Cure: canonical ordering by hash, temporary VS
    selections restored afterward, aspect locked per session. *Ours: UCF/Slippi code toggles, PAL,
    game speed belong in the same identity.*
12. **Wrongly claiming a test passed.** They now require proof the impairment was exercised (relay logs
    injected latency; test fails if no rollback happened). *Ours: SyncTest overflow bug proved we needed
    a heartbeat; same principle.*

---

## 4. Things they do that we do not (ranked value / cost)

1. **Two-process game-pair harness with an impairment relay** and machine-checkable pass criteria (matches
   reached, N confirmed hash samples, real corrections, no faults). High value, medium cost. Blocked on
   the adapter between `gw_net` and `gw_rollback`.
2. **Input latch for live pads** (button edges, trigger peaks, latest stick). High value for feel, low
   cost.
3. **Curated gameplay hash on the wire + full-field dump on mismatch** with a 256-frame ring. High value,
   low cost.
4. **Epochs for scene transitions** (menu/CSS/SSS/results synchronized, scene exit waits for confirmed
   input). High product value, medium-high cost; cheap to *design in now* by numbering frames per scene.
5. **Auto input delay from measured RTT**, resolved once and sent to both peers. Medium value, low cost.
6. **Interruption handling**: hold-and-resume, seat reservation, cancel-scene path. Medium, medium.
7. **Compatibility fingerprint hardening** (file locking, domain-separated combined digest, settings that
   change the sim in the identity, off-thread hashing, recheck at Ready and Start). Medium, low-medium.
8. **Pure-logic model test of the rollback core** against an independent lockstep reference under late,
   duplicated and reordered inputs across history wraps. Medium value, low cost.
9. **A standing "practice opponent" bot** that speaks the protocol and feeds deterministic inputs so a
   single machine can measure real network behaviour (`server/netplay_input_bot.py`). Low cost once a
   relay/lobby exists.
10. **Lobby/relay/room browser/server tests.** High product value, high cost; out of scope for now.
11. **Overlap guest simulation with renderer processing** (immutable frame handoff): 54.4 -> 60.0 FPS on
    their side. We already hold 60, so not needed.

---

## 5. Things we do that they do not (as far as their repo and docs show)

- **Full-state SyncTest** (byte compare of all memory every frame after k-deep rollbacks) with attribution
  of every differing byte to a map symbol or heap offset. Their checks compare a small curated hash, so
  heap/pool divergence that does not (yet) touch those fields is invisible to them.
- **Console-exact validation**: `.slp` playback, self-recording round trip, first-divergence tooling,
  per-field and velocity comparison, run-to-run determinism diffs down to RNG draw callers.
- **Dirty-page snapshots** (10x cheaper) and a measured resimulation cost.
- **Determinism proven with the pin removed**: unpinned runs and concurrent runs bit-identical; render
  couplings hunted with an audit for RNG draws during render.
- **Slippi gameplay code coverage** (UCF 0.73/0.84, neutral spawns, stage codes) for accuracy against real
  tournament data. They do not claim console accuracy.
- **A correct reading of Slippi's desync handling.** Their docs state Slippi does not detect desyncs. Our
  verified read of `slippi-ssbm-asm` (`StartEngineLoop.asm`, checksum walk over the player blocks,
  exchanged checksums, on-screen "DESYNC DETECTED") shows it does.
- **Cross-machine float determinism by construction** (no dependence on the host libm or FMA hardware).

---

## 6. Concrete recommendations for our three branches

All of these can be derived and implemented without their code.

### 6.1 `agent/snapcost` (snapshots, hashing, resim cost)

1. **Two hashes.** Keep the whole-state dirty-page hash for SyncTest (`gw_snap_hash`). Add a separate
   **gameplay hash** for the wire: RNG seed plus, per fighter slot, the fields that determine future
   behaviour (action state, facing, position, velocity terms, ground speed, damage, held/pressed input
   state, hitlag/timers that gate behaviour; derive the list from Slippi's checksum and from what
   `first_div.py` already compares). Reason: two real peers legitimately differ in render-owned bytes
   (particle display, matrix caches, pool layout) and would false-positive on a whole-memory hash.
   Publish only for *confirmed* frames, and only up to the earliest frame still marked dirty.
2. **Test skipping render on resim, guarded by an env switch.** Their peers replay logic only and still
   agree on the curated hash over hundreds of checkpoints; our render-in-resim requirement came from a
   full-memory compare. Run SyncTest with the *gameplay hash only* and resim-without-render over the whole
   replay at k=1/3/7, then over a soak on an item/effect-heavy stage. If clean, resim drops from about
   1.2 ms to about 0.35 ms per frame (a 7-deep rollback from about 9 ms to about 3 ms). Keep
   render-in-resim as the safe default until it passes. Watch for allocation-dependent behaviour
   (pool exhaustion, address-dependent code paths) that a curated hash cannot see; add a check that pool
   occupancy after resim stays within bounds.
3. **Audio in the snapshot.** Prefer advancing the sim-visible audio state by one fixed slice per logic
   frame and snapshotting just that state (voice handles, instance ids, "is playing"), while never
   submitting audio from replayed frames. This removes the audio->logic determinism hazard rather than
   masking it.
4. **Restore hygiene list.** After a load, re-derive or protect everything external to the sim: GX state
   shadow, VI/XFB ownership, draw-done state (you already exclude these); add a self-check that fails
   loudly if a load is attempted while a deferred device callback is pending.
5. **Expose `gw_snap_gameplay_hash(frame)`** next to `gw_snap_frame_hash` with a small documented header
   comment, so the session layer and transport call one function.

### 6.2 `agent/rbsession` (session layer)

1. **Input latch for live pads**: at every raw pad sample between logic frames, OR in newly-pressed buttons,
   keep the maximum of each analog trigger, and keep the newest stick; consume once per logic frame and
   restart the peak from empty. Confirm our raw pad queue does not merge a fast tap away when it is full
   (the research doc notes the queue merges buttons into its oldest entry when full).
2. **Immutable confirmed inputs**: a second, *different* confirmed input for the same (slot, frame) is a
   protocol/desync error, not an overwrite; identical redelivery is harmless. Add tests for: duplicate,
   reordered, and a future input never appearing as a prediction for an earlier frame.
3. **Known-empty frames before the delay** on every slot, and the same delay on both peers (negotiated in
   the handshake, never measured independently).
4. **Declined-correction path**: if a rollback target snapshot is missing, do not abort; keep the
   prediction on screen, count and log it, continue.
5. **Publish only confirmed state**: gate the checksum sent to the peer on `min(confirmed, first-dirty)`.
6. **Epochs**: number frames per scene and label every trace/hash row as (epoch, frame). Fail tests on a
   reused label. Design `gw_rb_*` so a scene change resets frame numbering and the time-sync history
   (keep RTT).
7. **Scene-end deferral**: hold the match end until all remote inputs for the final frames are confirmed;
   on an aborted match cancel through the game's mode-change path (not the normal end-of-match path).
8. **Audio**: adopt 6.1.3; until then, at least drop stale sounds from the abandoned timeline.
9. **Stall behaviour**: when stalled, re-request missing input and resend recent history, but never widen
   the prediction window.
10. **Model test**: add a headless test that runs the session core against an independent lockstep
    reference under late/duplicated/reordered inputs across many history wraps (no game, no renderer).

### 6.3 `agent/netcode` (transport)

1. **Time-sync behaviour tests.** Confirm (and if missing add) exactly these properties in the virtual-time
   test bench: two peers on different clock rates (about 60.3 vs 59.8 Hz) stay within about 2 frames over
   60 simulated seconds; only the faster peer ever corrects; never both at once; a steady link is never
   corrected; a scene change forgets drift but keeps RTT; one retransmitted packet cannot move the RTT
   estimate. Consider the symmetric "both agree who is ahead, give back half, 2-5 frame steps, decide on a
   30-frame average" scheme if the EMA scheme fails any of these.
2. **Per-packet frame advantage** in the header so both sides can compare measurements.
3. **Wire payload budget.** At 28 bytes per slot the redundancy window shrinks to about 17 frames for two
   slots. A raw pad is 8-9 bytes. Sending post-calibration raw analog bytes and letting each peer run the
   game's own deadzone/UCF processing quarters the payload and matches how Slippi does it, but *requires
   identical calibration*: the port's per-machine adapter calibration must be normalised before it goes on
   the wire. Decide with the session author; keep the negotiated per-slot size.
4. **Auto input delay**: measure RTT during the handshake, resolve one delay (about one frame per 16 ms of
   one-way latency plus margin, clamped to 1-6; their published sample points: ~8 ms RTT -> 1, ~100 ms ->
   3, ~400 ms -> 6), send it in START to both peers, keep a manual override.
5. **Desync policy**: choose explicitly. Recommended: report on-screen and in the log on both peers with a
   full-field dump of the mismatching confirmed frame (keep a ring of 256 frames of field snapshots), keep
   playing, let a caller stop the session if it wants.
6. **Interruptions**: hold the match instead of ending it when the peer goes quiet (their grace is 45 s),
   resume from the same frame; a permanent loss cancels the scene through the game's mode-change path.
7. **Identity hardening**: domain-separate the combined digest with a version tag; include every setting
   that changes simulation (UCF/Slippi code set, PAL, game speed, aspect if any camera state is
   simulation-visible, mod content hashes) and exclude renderer libraries; open hashed files with
   read-only sharing for the session so they cannot change underneath; hash off the game thread; recheck
   at Ready and Start.
8. **Relay reality check (for later)**: if a relay is ever built, it needs an open UDP port on the host;
   a stream fallback creates the head-of-line stalls above. Direct P2P plus hole punching avoids the
   problem for two players.
9. **Impaired two-process test** once the adapter lands: pass criteria (match reached, at least 20
   confirmed hash samples equal, at least one real correction, zero faults, and evidence in the proxy log
   that impairment was applied).

---

## 7. Open questions

1. **Is skip-render-on-replay actually safe?** Their peers do it and match on a curated hash; our full
   memory compare says the render pass moves object pools. Whether the pool/cache differences ever reach
   gameplay is unproven either way. Answer with the experiment in 6.1.2 (curated-hash SyncTest, long soak).
2. **Does our whole-memory hash ever match across two real machines?** Probably not (render-owned bytes),
   which is why the two-tier hash matters. Worth measuring before choosing the wire checksum.
3. **How slow are their per-frame full snapshots?** They publish rendering FPS but no snapshot or replay
   cost. Not needed for our decisions.
4. **Rollback with m-ex/Akaneia content on our side.** Interpreter registers and thunk tables live outside
   MEM1; do they need snapshotting, or are they always idle at frame boundaries (`gw_ppc_depth == 0`)?
   SyncTest so far ran stock fighters only.
5. **Cross-CPU determinism.** Ours should hold by construction; nobody (them included) has demonstrated
   it across two different CPUs. A two-machine run is the real test.
6. **Their exact hashed field list and per-frame cost** are implementation details we deliberately did
   not copy; derive ours from Slippi's published checksum and from the fields `first_div.py` tracks.
7. **Licence.** Absent a licence, do not reuse their code. If specific pieces are wanted, the route is to
   ask the author for permission or a licence statement; for the ideas above no permission is needed.
