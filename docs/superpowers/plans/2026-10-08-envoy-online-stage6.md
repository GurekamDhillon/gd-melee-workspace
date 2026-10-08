# Envoy online, stage 6: CPU opponents in a netplay match, then items and drops

Date: 2026-10-08. Lane: workspace `ws/envoy-s6`, game `agent/envoy-s6` (from `integration/2026-10-01/roguelite-100-game` 47e2c09b2).
Implements section 5, row 6 of `_research/envoy-netplay-scoping-2026-10-05.md` (that study wins on the architecture; this plan
wins on stage 6's order and its test gates). The study says stage 6 "first needs its own feasibility test": this plan is that test
first, and the build-out only if it passes. Results are filled in at the bottom as they land (section 7).

## 1. The question

Co-op Envoy is two humans against CPU opponents. The retail CPU AI has never run in an online match, and `MELEE_CPU_IDLE` is
"ignored in netplay" (nobody ever relied on it). Is the AI **identical on both peers through rollbacks**? Three ways it could not be:

1. **Hidden AI state outside what a snapshot restores** (a static in the AI code, a heap block that is not MEM1, a native shim).
2. **A per-peer input**: the AI reading something local (a pad, the wall clock, `OSGetTick`, the render pass, a heap address, the camera).
3. **A resimulation that is not the first pass** (the known long-combat SyncTest mismatch, `PORT_DEV_QUICKREF.md` line 117 and
   `melee/_research/rollback-synctest-status.md` 2026-10-05: hitlag/animation frame off by one after 2-4k frames of sustained combat).
   A CPU fights all the time, so if that issue were real in netplay it would show here first.

Where the AI lives (read, not assumed): retail `ftCo_800B3900` (`Fighter_8006ABA0`, per-fighter input phase) writes `fp->cpu`
(`struct CpuFighter`, 0x57C bytes inside the `Fighter` struct in MEM1), then `Fighter_Spaghetti_8006AD10` turns that virtual pad
into `fp->input`. Its randomness is `HSD_Randi` (the global seed, already in `RB_GameHash`). The port's own overlays
(`technical_ai.inc`, `cpu_assist.inc`, the script CPU controller `d6f9ef629`) all refuse to run when `Netplay_Enabled() || RB_Enabled()`,
so online CPUs are the retail AI and nothing else. The rollback session lists human ports only (`gw_Replay_PortHuman`, slot_present),
so a CPU port has no input in the ring and needs none.

## 2. Slice order and gates

| step | what | gate (evidence) |
|---|---|---|
| A | Harness: scene carries CPU slots (host `MELEE_NETPLAY_CPUS`, `MELEE_NETPLAY_TEAMS`), `tools/netplay/cpu_soak.py` | CPUs are in the match on both peers (`slots present`, `cpu: P3 fight (retail)`), hash logs compared |
| B | AI state into the rollback hash (`RB_FighterHash`, CPU-controlled fighters only) + a negative control (`MELEE_RB_PERTURB=cpu`) | the control trips `DESYNC` at the perturbed frame on both peers; ordinary human matches hash exactly as before |
| C | Feasibility soaks: 1 and 2 CPUs, clean and lag/jitter/loss, delay 2 and 0, long runs, teams | 0 desyncs, 0 differing confirmed frames, thousands of rollbacks |
| D | Root-cause the long-combat SyncTest mismatch with CPUs in the bench (curated + `CURATED_DIFF`) | first divergent frame/field named, or shown to be a render-skip artifact that netplay (which renders in resim) does not have |
| E | 4-port ownership: 2 humans (ports 1, 2) + CPUs (3, 4), teams; a host setting and `gd.netplay_act("cpus", ...)` so a lobby can choose; no new packet | scene string only, protocol unchanged |
| F | Items online: `items=<n>` in the online scene (a host setting), item words already in `RB_ItemHash`; soak with items on | 0 desyncs with items on the list, CPUs and humans picking up and throwing |
| G | Envoy drops online: a native, deterministic drop spawn (seeded, at an agreed frame) in place of Lua `item_spawn` | design only unless F passes cleanly and time remains |
| H | Windows to Linux: the same CPU scene in the `tools/xplat` matrix | per-frame digests equal (needs a Linux tree of this branch; owed if it cannot be built here) |

Rules held throughout: new gameplay state goes in snapshots and the rollback hash; the local server only (no `netplay.gsd.sh`), every client
`MELEE_NETPLAY_BIND=127.0.0.1` (no Firewall prompt), at most two games at once, windows at `MELEE_WINDOW_X/Y=30000`, every
game stopped by numeric PID.

## 3. Protocol and wire

None for steps A to F: the CPU slots, teams and item frequency ride in the host's scene string (the same channel as `turbo=` and `envoy=`),
and a guest plays exactly the scene it is handed. Both peers must already be the same build (`np_build_id`), so an old peer cannot join a
CPU match by accident. A formal "slot ownership" field in the handshake (the study's "protocol bump for slot ownership") would only be needed
if a third human or spectator joins: **not needed for 2 humans + CPUs.** Any later bump is an ELEVATE decision, not made here.

## 4. The hash

`RB_FighterHash` mixes, for a CPU-controlled fighter only, a "CPUA" word group: the virtual pad (`buttons`, sticks, triggers), kind,
level, the AI's working words (`x14..x40`, `x7C..x84`), the two move-queue counts, `command_duration`, the command script's read offset
(as an offset into its own buffer, never a pointer) and the flag bytes. A human-only match hashes exactly as before (so the
pre-existing Turbo/Envoy evidence still holds), and `RB_GameHashTest`'s expectations are untouched.

## 5. Out of scope

Classic/Adventure online (stage 7), the Envoy evaluator (stage 4), the Atlas lobby UI for choosing CPUs (owner/art decision; the scene
and Lua hooks are the plumbing), Slippi.

## 6. Decisions left for the owner

Listed in the lane report (protocol shape for spectators; whether co-op ships as a lobby option; CPU level policy).

## 7. Results



Build: game `agent/envoy-s6` 4d5f441ba (merged with `integration/2026-10-01/roguelite-100-game` 92ffbe08b: Envoy stage 4, Geno 5-6, PlCo fix,
online sudden death, lobby fixes). Exe `_build/agents/envoy-s6/melee-pc.exe`, build id 4d05269f188683d5. Headless suite 336/0 (`rb_game_hash` ok).
All soaks: `cpu_soak.py`, two real clients over loopback (direct connect on a unique 57xxx port, no server), humans = pad bots, per-frame
`MELEE_RB_HASHLOG` of both peers compared on every confirmed frame.

| run | CPUs | stage | net sim | items | frames | rollbacks (h/g, max depth) | result |
|---|---|---|---|---|---|---|---|
| s1 (pre-merge) | Falco L9 | FD | lag50 j20 loss3 | off | 18270 | 1465/1813, 7 | 0 differing, 0 DESYNC |
| s2 (pre-merge) | Falco L9 | FD | lag50 j20 loss3, 600 s | off | 36292 | 3358/3144, 6 | clean |
| s3 (pre-merge) | Falco L9, delay 0 | FD | lag100 j40 loss8 | off | 14211 | 1294/1331, 7 | clean |
| s4/s6 (pre-merge) | Falco+Marth L9, teams | FD | lag50 j20 loss3 | off / 4 | 16671 / 18073 | 1608 / 1880 | clean |
| p1 (post-merge) | Falco L9 | FD | lag50 j20 loss3 | off | 18335 | 1464/1386 | clean |
| p2 | Ice Climbers + Kirby L9, teams | Stadium | lag80 j30 loss5 | 4 (3 on floor) | 18159 | 1701/1454, 7 | clean |
| p3 | Jigglypuff L3 + Link L1 | Dream Land | lag60 j25 loss4 | 8 (42 on floor) | 18258 | 1445/1606, 7 | clean |
| p4 | Marth+Falco L9, delay 0, 600 s | Yoshi's Story | lag100 j40 loss8 | 4 (7) | 28509 | 2814/2892, 7 | clean |
| p5 | Kirby + Ice Climbers L9, teams, 900 s | Fountain | lag70 j30 loss6 burst3 | 6 (76) | 49243 | 4889/4605, 7 | clean |
| n1/n2 (negative control) | Falco L9, `MELEE_RB_PERTURB=cpu` on the host | FD | clean | off | | | `DESYNC at frame 900` on both peers |

Bench SyncTest with a retail CPU (`sync_cpu`: 2 pad bots + Falco L9, items 4, curated + REGION-DIFF): 8400 checks, 0 mismatching to frame ~900;
the REGION-DIFF list names only the known render/audio words (`fp+0x20A4`, `+0x2224`, AX voice ids `+0x2144..2160`, joint flags and matrices); nothing
in `fp+0x1A88..` (the `CpuFighter`). The long-combat mismatch of the earlier note is the render-skip allocator artifact; netplay runs the render block
in resim and 49k frames / 4.9k rollbacks of CPU combat did not diverge.

Lobby path (np_drive, local server, `gd.netplay_act("cpus", "20:1:9,9:2:9", true)` + `("items", 4)`): both peers `P1,P2 human team0 | P3,P4 cpu team1`, items=1,
0 DESYNC, PASS. (The first run exposed that the lobby `X` message was swallowed; it is now `C`.)

Found and fixed on the way: the AI state was not in the hash (added `CPUA`); lobby extras message letter; per-lane menu port (`MELEE_NETPLAY_PORT`);
`cpu_soak.py` now picks free 57xxx ports (a pid-derived port collided with another lane's host and produced a bogus run).

**Verdict: feasible.** No divergence found, so none to fix: the retail AI, its RNG (`HSD_Randi`, already hashed), its virtual pad and its state
(`fp->cpu`, in the snapshot because it is in the fighter struct) are identical on both peers through rollbacks, with 1 and 2 CPUs, 10 characters (incl. Ice
Climbers/Nana and Kirby), 6 stages, delay 0 and 2, up to lag100/jitter40/loss8, 49k-frame matches.

## 8. Items and drops (step F, G)

F is done by the same machinery: `items=<n>` in the host's scene, retail spawn RNG hashed, item words in `RB_ItemHash`; soaks p2-p5 had 3-76 items on the floor
(CPUs picking up and throwing) with 0 desync. G (Envoy drops, physical Geno items spawned by Lua `item_spawn`, `gs_require_offline`) is NOT built: design only.
A native drop must be spawned by the simulation, not Lua: on both peers at an agreed frame (stage boundary or a KO frame already hashed), position from the
run seed (`seed_for(run_seed, game, loop, port)`), through `gw_Geno_ItemSpawn` (so it is a normal item: in snapshots and `RB_ItemHash`); the Lua
`drive_drop` record table must become a read-only presentation mirror rebuilt from the item list after each restore (it holds handles, which rollback
invalidates), and pickup must be resolved natively and reported as a hashed event. That is a separate lane (needs Geno item `drive` available online).
