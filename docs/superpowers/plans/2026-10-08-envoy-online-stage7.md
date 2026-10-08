# Envoy online, stage 7: Classic / Adventure runs online

**Date:** 2026-10-08. Branches: workspace `ws/envoy-stage7`, game `agent/envoy7` (both from the 2026-10-08 integration heads, workspace `ea760c8`, game `47e2c09b2`).
**Supersedes:** nothing. It fills the last row of the staged plan in `_research/envoy-netplay-scoping-2026-10-05.md` section 5 (stage 7, "Classic/Adventure online (only if still wanted)"), which the owner has now asked for ("envoy online doesn't do the classic/adventure mode stuff at all").
**Depends on** stage 4 (triggered drives in a match), stage 5 (co-op run state, resume) and stage 6 (CPUs online), which three other leads are building in parallel. This document is written so that stage 7 can start now and meet them at named seams (section 9).

Tags as in the scoping study: **[R]** read from source (file and function given), **[I]** inferred, **[U]** unverified, needs a test, **[T]** measured by the spike of section 8.

---

## 0. The answer in ten lines

1. Online today is a 1v1 Versus set. After each game the session is closed, the room is kept open on the server, both players come back to the lobby and reconnect to the same room (`gw_Netplay_MatchOver`, `gw_Netplay_Rejoin`) [R `gw_netplay.c`]. So the port **already runs one fresh, agreed rollback session per game**.
2. **A rollback session cannot span a scene change, and must not try.** Snapshots are MEM1 plus game BSS [R `gw_snap.c` header]; a scene change reloads heaps and archives and tears down render and audio state that the snapshot does not own. A rollback window is therefore bounded by its scene: frame -123 is the earliest frame any rollback can reach (`rb.opened = 0` at every VS scene, `gw_RB_SceneBegin`) [R]. Each stage is a hard barrier.
3. The rollback layer is already scene-aware in the right way: every scene bumps an **epoch**, inputs and hashes carry it, and a peer that enters the next scene first has its inputs held back (`early[]`) [R `gw_rollback.c`, `gw_rollback.h` EPOCHS]. What is missing is the transport side: `gw_net` has no way to go from RUNNING back to ACCEPTED, so a new stage means a new connection (the server round trip) today.
4. **Do not run the retail 1P state machine under netplay.** Retail Classic/Adventure is single-player in its data (`UnkAllstarData` holds one `ckind`, one colour, one stock count) and its stage selection reads each machine's save (`gm_IsCKindUnlocked`) and the global RNG (`HSD_Randi` in `gmClassic_InitMatchupOrder`) [R `gmclassic.c`]. Two humans do not fit it. Recommended architecture **R2**: a *run director* that plays the stages as ordinary agreed Versus-shaped scenes (`GS_VS`), exactly the shape of the offline co-op Envoy already has, with the 1P tables read as DATA for stage, opponents, flags and difficulty.
5. In both retail modes **every stage is a `GS_VS` scene** (Classic: `GS_INTRO_EASY`, `GS_VS` pairs; Adventure: `GS_INTRO_NORMAL` or a `GS_CUTSCENE_*`, then `GS_VS`) [R `gmclassic.c`, `gmadventure.c` state tables]. Intros, cutscenes, the continue screen and the ending are non-VS scenes. R2 replaces all of them with a **director interstitial** (the Envoy reward/bag screen in the frontend), so the only scenes that exist online are `GS_VS` stages and the frontend between them.
6. What the peers must agree on at each boundary is small: the **run record** (seed, stage index, loop, scores, flags, the chosen stage), a 64-bit digest of it, and from stage 5 the two players' builds. A stage's scene string names the record's digest; the guest recomputes it before loading anything and refuses on a difference. The spike builds exactly this (`gw_netrun.h`, `RN1|...|digest`).
7. **Spike result (section 8): two real clients walked stage 1 -> stage 2 -> stage 3 over loopback, a fresh agreed session each, the run record identical on both sides, 0 hash mismatches over every compared frame (no sim and with lag 40, jitter 10, loss 2), and a wrong record is refused before the stage loads.** The reconnect between stages costs 5.4 s through the server; a timed-out tie sends today's sets into an unsynchronised sudden death (a stage must contain no scene change).
8. Hazards that would silently desync a naive port, all avoidable in R2: the global RNG at mode entry, save-dependent unlock checks, wall-clock holds (`hold_ms`), host-only 1P state (`gs_1p`) outside the snapshot, scripts that refuse to run online (`gs_1p_offline`).
9. Not provable here and flagged owed: CPU AI exactness (stage 6), boss fights (Master Hand, Crazy Hand, Giga Bowser) under rollback, bonus stages (target test, platforms, race), Windows-Linux determinism of any new state, and how any of it looks.
10. Protocol: the spike needs no protocol bump (it rides the lobby channel and the scene string). Production needs a mode word (Envoy mode word V2 or a protocol 6) and, if the server round trip per stage is to go away, a transport re-arm packet. Both are **elevated decisions** (section 10).

---

## 1. What exists, from the code

### 1a. The 1P layer today (offline)

`pc/platform/gw_script_1p.inc` [R] is a host-side hook layer on top of the retail 1P modes:

- state: one static `gs_1p` struct (`mode` 3 = Classic, 4 = Adventure, `stage`, `flags`, `player`, `loops`, hold/barrier fields, `launch` text for New Game+). It is **host state, not in the snapshot**.
- gate: `gs_1p_offline()` is `!gw_RB_Enabled() && !gw_Netplay_Enabled() && !gw_Snap_Resimulating()`; every hook (`OnePStage`, `OnePClear`, `OnePGameOver`, `OnePComplete`) returns at once online, and `gs_1p_tick` clears the barrier and hold when not offline. Every Lua call (`start_1p`, `hold_1p`, `release_1p`, `loop_1p`, `spawn_1p`) is `gs_require_offline`.
- the **interstage hold** is a wall-clock window (`gs_1p_hold_clock`, 60 Hz units of `gs_now_ms`, default 1800 units, ceiling 7200) that keeps the old retail scene frozen while a script shows its reward screen, then `gm_OnePInterstage` pumps input, scripts and drawing with no retail frame (`gmscene.c`, `gm_onep_interstage`). Wall-clock time is per-peer: it cannot be a shared decision.
- the Envoy retail director (`pc/scripts/examples/envoy/scripts/classic.lua`, "Retail director only") sits on those hooks: per-stage rolls from `rng(seed, stage, loop, port)`, spawn modifiers on opponents, rewards at stage clear, New Game+ through `loop_1p`. `R:start` refuses outright when `match.netplay`.

### 1b. The scene tables

Classic (`gm_Mode_Classic_States`, `gmclassic.c`) [R]: CSS (state 112), then pairs `GS_INTRO_EASY` + `GS_VS` at states 0/1, 8/9, 16/17 ... 80/81 (eleven stages), then `GS_COMING_SOON` (104, the end) and `GS_GAMEOVER` (105, continue). Enter handler `gmClassic_801B3A34` builds `StartMeleeData` for the stage; exit handler `gmClassic_801B3B40` records the stage result (`gm_804908A0[idx]` 1 = won, 2 = failed) and, for the bonus stage rows, the best time. The stage list (`gmClassic_803DDEC8`) is data: per row a flags byte (0 battle, 2 metal, 4 giant, 8 and 0x10 team/ally rows, 0x20 the boss row, 0x80 bonus rows 1, 2, 3 = targets, platforms, race), a CPU level, a stage and up to three enemy kinds.

Adventure (`gmadventure.c`) [R]: the same `GS_VS` stages with `GS_INTRO_NORMAL` or one of nine `GS_CUTSCENE_*` scenes (Luigi, Brinstar, planet explosion, three Kirbys, giant Kirby, Star Fox, F-Zero, Metal Mario, Bowser toy, Giga Bowser transformation and defeat) interleaved, `GS_GAMEOVER`, `GS_COMING_SOON`, CSS.

What the stage is: **every fight is `GS_VS` (scene kind 2)**. That matters, because the rollback layer's definition of a match is `scene_kind == 2` (`gw_RB_SceneBegin`: `rb.in_match = scene_kind == 2`, and a non-VS scene after a live net match calls `gw_Netplay_MatchOver`) [R]. So the stages themselves are scenes the session layer already knows how to arm, whatever mode started them. The non-VS scenes are the problem, and R2 deletes them from the online flow.

### 1c. The online path today

`np_build_scene` produces `mode=vs;at=match;p1=../hu;p2=../hu;stage=..;match=stock;stocks;minutes;items=off;pause=0` plus `turbo=` and `envoy=` tokens [R `gw_netplay.c`]. The lobby (`lb`) is a host-arbitrated state machine; its messages (`A`, `S`, `L`, `E`, `W`, `V`, `X`, `G`, `N`) travel on the reliable lobby channel (200 bytes a message); the match starts with `G <seed> <scene>` and the guest checks the Envoy word against the scene token before loading. When the scene ends: `gmVsMelee_ExitResults` calls `Netplay_GameResult` (score and game number) and `Frontend_BackToOnline`, `gw_Netplay_MatchOver` closes the session but keeps the room (`np_keep_room`, keepalives), and `gw_Netplay_Rejoin` re-enters (the guest keeps asking for the room for up to 30 s).

---

## 2. Architecture: R1 or R2

**R1, the retail 1P state machine under netplay (rejected).** Needs: a second human in `UnkAllstarData` and every stage's `StartMeleeData` (the structs are single-player), the retail intro/cutscene/continue/ending scenes to run in lockstep on two machines (each is its own scene with its own loader and audio, none has ever been driven by two peers), the stage selection to stop reading `gmMainLib` unlock bits and `HSD_Randi` per peer, the 1P results and save writes (clear times, unlocks, `gmMainLib_8015EDBC` writes) to stop touching two different memory cards, and `gs_1p` to move into the snapshot and the hash. Estimated large and brittle, and the outcome (a retail single-player mode with a second pad) is not what the Envoy co-op design describes.

**R2, a run director over `GS_VS` stages (recommended).** The Envoy offline co-op (`envoy/COOP.md`) is already "a sequence of Versus team stages" launched with `gd.scene_launch`, the run ending each stage itself, rewards on a frontend-style screen between. R2 is that, with the launch done by the netplay layer instead of a script:

- the **plan** of a stage is a pure function of (run seed, stage index, loop, mode): stage, opponent kinds, flags, CPU level. The 1P tables are the data source (read-only, indexed by plan), the selection logic is reimplemented over an agreed seed and an *agreed unlock mask* (the intersection of what both players have, like the lobby's stage list from `gw_mexid.c`), never `HSD_Randi` and never the local save.
- the **scene** of a stage is `mode=vs;...` built by the host exactly as `np_build_scene` does, extended (stage 6) with CPU slots and teams.
- the **boundary** is the lobby channel: `G <seed> <scene>` already is "the next session's agreed start", and the lobby tick already keeps the connection alive between sessions.
- **retail scenes** (intro, cutscene, continue, ending) do not run. The director interstitial shows what they showed (opponent preview, story beat as text, continue, ending summary) on the frontend scene, where the reward screen already lives.

What R2 gives up: retail cutscenes and the retail continue screen online, and the retail save side effects (unlocks, trophies, clear times). Those are the owner's call (section 10, decision 2); the offline Classic/Adventure and the Envoy retail director are untouched.

---

## 3. Boundary by boundary: what must be agreed

| boundary | what happens | must be agreed by both peers | how |
|---|---|---|---|
| run start | host opens a room with the run preference on | mode word, run seed, the stage list (identity tokens), characters, rules (stocks, time, handicap), starter builds (stage 5) | handshake mode word (production) / lobby `R` message (spike); `L` chunks; `E`/`W` words for Envoy |
| stage N -> interstitial | the stage's sim reaches its end frame; the scene exits to the frontend | the **end frame and the outcome** (who won, stocks, time) before either side leaves | stage-end barrier (section 5); today the results screen plays this role |
| interstitial | rewards, bag, opponent preview, continue prompt | each player's choice (an index into an offer both can compute), a countdown counted in lobby ticks, the default on timeout | the Stage 3 reward phase (`RPICK`, `env_left`) generalised; host validates, both apply |
| interstitial -> stage N+1 | the host builds the scene and sends `G` | the **run record digest** (stage index, loop, scores, flags, chosen stage), the builds' word, the seed | `run=` token in the scene, guest recomputes and refuses on a difference (built in the spike) |
| stage N+1 load | both load, then the hold-start handshake releases frame -123 together | nothing new: `gw_net_release`, start time agreed by the transport | existing |
| boss stage | an ordinary stage whose opponents are boss kinds | the same record; the boss's behaviour is retail native code on snapshotted memory, hashed through the RNG seed and positions | stage 6 feasibility |
| game over | all of the team out of stocks (or the director's rule) | that the run is over, the final record | `flags` bit in the record, host announces, both go to the summary |
| continue | optional retry of the failed stage | whether it is allowed (a run-level token in the record), the count | record field; owner decision |
| run complete / New Game+ | last stage of a pass | `loop+1`, the carried builds | record field, as offline `loop_1p` |
| disconnect, mid-stage | the stage is forfeit (rollback cannot recover a missing peer) | nothing; both clients keep the last boundary's record | stage 5 resume |
| disconnect, at a boundary | resume from the last record | digests compared, one record adopted | stage 5 |

---

## 4. Snapshots and rollback across stage transitions

Question asked: can a rollback session span a scene change, or does each stage start a fresh agreed session?

**Answer: each stage is a fresh agreed session, and that is the only safe shape.** Reasons, from code:

1. A snapshot slot is MEM1 as shared pages plus the game's BSS symbols (`gw_snap.c`). A stage change reloads stage and fighter archives into the heaps, rebuilds GObjs and display lists, reloads audio banks, and re-registers render resources that live outside MEM1. Restoring an older MEM1 over a different scene's heaps while the renderer, audio and archive caches hold the new scene's native state is not a coherent state. [I, but the existing code agrees: the slot ring is reset per scene.]
2. `gw_RB_SceneBegin` already treats every scene as a new epoch and resets the ring (`rb.opened = 0`, `rb.newest`, `hring`, `conf_slot`) [R]. A rollback below frame -123 cannot be requested.
3. Rollback inside a stage is unaffected by anything in the director: the director writes nothing during a stage (it is not a script in the loop, and online the engine refuses Lua gameplay writes anyway).
4. The state that crosses the boundary is **not** in a snapshot and does not need to be: it is the run record plus the builds, small, digest-checked, and rebuilt identically on both sides (a pure function of the agreed history). That is the same decision the study made for builds (stage 3: "builds restage per game").
5. The one thing that must hold at the boundary is that nothing can still roll back across it: the exit must happen at a *confirmed* frame. Retail's end-of-stage sequence (KO, "GAME!", stage-clear text) runs far more than the 7-frame rollback depth before the scene exits, which is why sets already work [I, soaked by Turbo: 12,300 ticks, 0 desyncs]. R2 does not rely on that: section 5 makes it an explicit barrier.

A subtlety worth recording: the session layer would let a *single* `gw_net` connection carry several consecutive VS scenes (epochs, early inputs), but `gw_net` numbers its frames from `first_frame` once per connection and has no re-arm [R `gw_net.c`: no transition RUNNING to ACCEPTED]. Section 6 picks between "reconnect per stage" (works today) and "re-arm" (new packet).

---

## 5. The stage-end barrier (new, small)

At scene exit each peer sends `(epoch, exit_frame, hash_at_exit, outcome)` on the lobby channel (it is still open: the session closes only after `MatchOver`), and does not tear the scene down until it has the other side's tuple, bounded by the existing 5 s disconnect timeout.

- equal tuples: proceed, both then compute the next record from the same outcome.
- different outcome (the case rollback is supposed to make impossible): `np_cb_desync`-style stop, the run ends, both keep the last boundary record.
- the host alone decides the *next* record; the guest only verifies. This reuses the Envoy reward-phase shape (host validates, rebroadcasts).

Today the same job is done implicitly by `Netplay_GameResult` being called on both sides from `gmVsMelee_ExitResults`. Cost to build: a lobby message type and ~60 lines; it must land before stage 7's real work, because it is the first thing that makes a 25-stage run safe. Not built in the spike (the spike shows the next layer works on top of the existing implicit one).

---

## 6. The transition itself: reconnect or re-arm

| | reconnect per stage (today) | re-arm the transport (`gw_net_rearm`) |
|---|---|---|
| mechanism | `MatchOver` closes the `gw_net`, keeps the room; `gw_Netplay_Rejoin`; lobby; `G` | after the stage-end barrier the host sends `REARM <session> <seed> <blob>`, both reset the transport to ACCEPTED, hold-start again, no socket close, no server |
| server load | a REG/JOIN (or the keepalive reopen) per stage per player; cost grows with run length | none after the introduction: peer to peer, which is the owner's 2026-10-05 constraint ("cost must not grow with match length") |
| time | measured by the spike [T]: section 8 | one RTT plus the load |
| risk | the guest's 30 s rejoin window, NAT mappings expiring on a long interstitial (keepalives exist) | a new packet type and state transition in `gw_net.c`, tested headless in virtual time (`gw_net_tests.c`) |
| protocol | none | **bump** (an unknown packet type to a v5 peer) |

Recommendation: ship the reconnect path first (it is what the spike uses and it is proven by sets), build `gw_net_rearm` as a separate, headless-testable change behind the same director API, and only after the owner has decided on the protocol bump (section 10, decision 3). The director API (`lb_run_*`, the record, the scene token) is identical either way.

---

## 7. Determinism hazards in the retail 1P code (the reasons for R2)

| hazard | where | what R2 does |
|---|---|---|
| `HSD_Randi` in the matchup order | `gmClassic_InitMatchupOrder`, `gm_Mode_Classic_OnLoad` | not used: the plan is `gw_nr_stage_index(seed, ...)` over integers |
| unlock state from the save | `gm_IsCKindUnlocked`, `gm_80164430` in `gmClassic_801B2BA4` | an agreed mask: the intersection of both players' content identities (`gw_MexId_*`), as the lobby already does for stages |
| single human data | `UnkAllstarData.x0.x0.{ckind,color,cpu_level,stocks}` | not used: both humans are ordinary VS slots (team 0) |
| ally CPUs for team rows | `ad->x0.xC.x24[3]`, `gm_8017DB88` | stage 6 CPU slots + `teams=1` |
| wall-clock interstage hold | `gs_1p_hold_clock` (`gs_now_ms`) | lobby-tick countdown, host-counted (already done for Envoy rewards: `LB_ENV_TICKS`) |
| host-only run state outside the snapshot | `gs_1p` | the run record, digest-checked; nothing about it is in a rollback window |
| save writes at stage exit | `gmClassic_801B3B40` (best times, unlock bits) | not run online; if the owner wants online clears recorded, a separate local-only write after the run |
| per-peer RNG for the run seed | `classic.lua:50` (`math.random`) | the host's seed, one number in the lobby (`R`) |
| scripts refuse to run | `gs_1p_offline`, `gs_require_offline` | unchanged and irrelevant: the director is native netplay code, not a script write |

---

## 8. The spike (done) and its result

**What was built** (game `agent/envoy7`, workspace `ws/envoy-stage7`; every shared file changed additively):

- `pc/platform/gw_netrun.h` (new, header only, integers only): the run record `RN1|seed|stage|loop|score0|score1|flags|ext|digest16` (digest = two salted FNV-1a words, the EB1 family), strict parse, and the plan `gw_nr_stage_index(seed, stage, n)` (pure; never the same stage twice in a row).
- `gw_netplay.c`: a **stage run** mode of the lobby behind a host preference (`MELEE_NETPLAY_RUN=1` or `gd.netplay_act("run", true)`; no menu row). In a run: no strike/ban/pick (blind characters, then straight to Ready; from game 2 straight to Ready with the characters kept), the host's `R <on> <seed>` message on entering the lobby, the stage chosen by the plan, the scene carries `;run=<digest>`, the guest recomputes its own record and **refuses** (`X`, leaves) on a difference, and each peer logs `netrun: ARRIVED in stage N of the run - <record>` when the stage begins.
- `gw_script.c`: `gd.netplay().run = {on, seed, stage, record, digest, refused, fail}` (read-only) and `gd.netplay_act("run", on)`. `gw_runtime.c`: the scene launcher accepts `run=`.
- test-only hooks: `MELEE_NETPLAY_RUN_STOCKS/_MINUTES` (short matches), `MELEE_NETRUN_POISON=1` on the guest (computes from another seed: the negative control).
- native tests `netplay_run_record` and `netplay_lobby_run`.
- `tools/netplay/run/run_pair.py` + `run_host.lua` + `run_guest.lua` (workspace): two real clients over loopback through the real menus and lobby, local matchmaking server on 127.0.0.1, both bound to 127.0.0.1 (a firewall prompt is what stalls a run otherwise), windows parked offscreen, Envoy off (no mods), `--poison` for the negative control.

**Result:** **PASS, on the exe built from `agent/envoy7` (`grep -a "netrun: ARRIVED"` finds the string in `melee-pc.exe`; native tests 332 of 332, the two new ones `netplay_run_record` and `netplay_lobby_run` among them; ABI audit 0).** Two real clients, vanilla disc, Envoy off, local server and both clients on 127.0.0.1, windows offscreen, driven through the real Atlas menus and the lobby by `run_pair.py`; evidence in `_build/netrun/<tag>/` (`trace.txt`, `result.json`, both game logs and both curated hash logs).

| run | what | result |
|---|---|---|
| `spike1` | 2 stages, no network sim | stage 1 `RN1\|8910202\|0\|0\|0\|0\|0\|8\|cff9c01aa8f355ca` (Yoshi's Story), stage 2 `RN1\|8910202\|1\|0\|1\|0\|0\|31\|ba14d95a764ad8ca` (Battlefield, score 1-0 carried): **identical on host and guest in both logs** (`netrun: ARRIVED in stage N`), and `gd.netplay().run.record` equal on both consoles at frame 221 and 610. Curated rollback hash logs compared frame by frame: stage 1 **1672 frames, 0 mismatches**, stage 2 **612 frames, 0 mismatches**. Logs: `desyncs 0`, no `CHECKSUM DESYNC`. |
| `spike2` | 3 stages, `lag=40,jitter=10,loss=2` | all three records equal on both sides; hash logs 3834, 3836 and 670 frames compared, **0 mismatches**; `desyncs 0`. |
| `poison1` | negative control: the guest computes its record from another seed | the stage is **refused before it loads**: host `netrun: the other side REFUSED the stage: run records differ (host ef0bc99bd51bbdcb, guest 785ed4a8e67c81d8)`, guest `netrun: REFUSED the stage`; no match started on either side; both left the room. |

**Transition cost [T], from `spike1`'s host log (loopback, local server; the retail results screen and a 3 s lobby countdown are part of what is timed):** match over 54.3 s, results screen and `Netplay_GameResult` 62.3 s, `Reopening room` 62.4 s, `Opponent found` 67.8 s (**5.4 s to reconnect through the server**), countdown done 71.1 s, `ARRIVED` in stage 2 at 72.5 s (**1.3 s from the `G` message to frame -123**). Under R2 the 8 s retail results screen goes away and the countdown can shrink; the 5.4 s reconnect is what the transport re-arm (section 6) removes.

**A hazard the spike found by accident [T], independent of stage 7 and present in today's sets:** in `spike2` games 1 and 2 timed out level (1 stock, 1 minute), and retail went to **`GS_SUDDEN_DEATH` (scene kind 3)**. That is a non-VS scene, so `gw_RB_SceneBegin` closed the net session ("match over - closing the session") and **each peer then played sudden death offline and alone**: host 22.7 s, guest 5.3 s in the same sudden death (`spike2/h.log` vs `g.log`, `perf: scene="GS_SUDDEN_DEATH/GM_VS"`), and the set score recorded `winner P0` on both. Both clients still reached the next stage with equal records because the record does not depend on who won sudden death, but the winner is not agreed. Any scene the retail flow inserts *inside* a stage must be removed or made part of the agreed flow: for runs, `time=0` (no timer) and the director's own tie rule. Worth a separate fix for ordinary sets (e.g. no timer online, or play sudden death as a fresh agreed session). Not done here.

**What the spike does not show:** a CPU opponent (stage 6), a build or a reward between stages (stages 3 and 5 exist for human sets; the spike runs Envoy off), any non-human stage content, the stage-end barrier of section 5, a Linux peer, any UI, anything over a real network. The stage lists in the runs were the lobby's competitive list (six stages).

---

## 9. Sequencing with stages 4, 5 and 6

```
stage 4  triggered drives in a match     (native evaluator, hash words)         \
stage 5  co-op run state, resume          (run record, digest, restage)           > all three feed stage 7
stage 6  CPUs online                      (CPU slots, teams, ownership)          /

stage 7a  run director skeleton + stage-end barrier          needs: nothing (spike proves the seam)   -- can start now
stage 7b  Classic plan over the 1P tables (agreed unlock mask, seeded selection, flags)   needs: nothing native; content only
stage 7c  a real Classic run with CPU opponents, 3-5 stages  needs: stage 6 (CPU slots + teams)
stage 7d  Envoy builds across the run, rewards                needs: stage 5 (run record, restage); stage 4 optional (passives work without)
stage 7e  boss stage, bonus stages, game over / continue / New Game+   needs: 7c and stage 6's boss/CPU feasibility
stage 7f  Adventure: stage list, interstitial story beats, special stages   needs: 7e
stage 7g  re-arm (no server round trip per stage)             needs: owner decision on the protocol bump
```

Seams to agree with the other leads **before** they merge (all additive):

1. **One run record.** Stage 5's co-op run record and this `RN1` record should be one format. The spike's `RN1` carries only (seed, stage, loop, two scores, flags, chosen stage). If stage 5 already has a record with a digest (it will, the study asks for "sorted versioned run record plus 64-bit digest"), keep its fields and give `RN1` a `bag` digest field or embed it; the digest check at `G` is the same code. Whoever merges second reconciles; the check function is two lines (`lb_run_check_scene`).
2. **The scene builder.** Stage 6 changes `np_build_scene` (CPU slots, teams, ownership). Stage 7 appends `;run=` after it in `lb_go` and does not edit `np_build_scene`. Keep it that way.
3. **The lobby phase machine.** The spike adds three guarded branches (`lb_apply_` CHAR, `lb_reset_game`, `lb_go`) and one message type (`R`). Stage 5's lobby additions (resume, mode flag) touch the same functions; resolve by keeping the `run_on` branches first.
4. **Hash words.** Stage 4's status words and stage 2's build word are in `RB_GameHash`; stage 7 adds none (a stage starts at frame -123 with a build word, not a carried status). A carried status across stages (a Burn stack that survives a clear?) is a design choice for stage 4/5: if it exists, it belongs in the record, not in a snapshot.

---

## 10. Decisions (the owner's, not made here)

1. **Architecture**: R2 (run director over `GS_VS` stages) as recommended, or R1 (retail 1P state machine, single human plus the other as a spectator / or not at all).
2. **Retail content online**: the retail cutscenes, intro cards, continue screen, ending and save side effects (unlocks, trophies, clear times) do not run online under R2. Replace with the director interstitial and a local-only post-run write, or accept loss.
3. **Protocol**: a run mode word (an Envoy mode word V2, which v5 peers refuse cleanly at the first packet without a version bump) versus protocol 6; and the transport re-arm packet (section 6) is a bump. The server stays introduction-only either way.
4. **Game over and continue**: shared stock pool or per-player, a run-level continue token, whether a lost stage ends the run for both.
5. **Adventure scope**: platforming/escape/race stages (Brinstar escape, F-Zero race) and the bonus target stages need either a cooperative redesign or to be skipped online.
6. **Unlock mask**: intersection of both players' content, or everything both have installed (as the lobby's stage list does).

---

## 11. Not verified (so a Windows agent knows what to check)

- Everything in section 8 beyond what the cited run shows; in particular **Windows-Linux determinism of the run director** (integer-only by construction, never run cross-platform here; `tools/xplat/envoy_set.py` is the harness to extend).
- CPU AI exactness and boss fights under rollback (stage 6 owns the first, nobody owns the second yet).
- How a 20+ stage run behaves over a real network (NAT mapping lifetime across a long interstitial, rejoin windows, the cost of a server round trip per stage).
- How anything looks: there is no UI for the run (the spike drives the lobby by script).

## Owner decisions (2026-10-08, the coordinator's recommendations accepted by the owner)

1. **Architecture: R2**, a run director over `GS_VS` stages with the 1P tables as data. R1 is not pursued.
2. **Retail content online:** a director interstitial between stages replaces the retail cutscenes, continue
   screen and ending; unlocks, trophies and clear times are written locally after the run (optional, per player).
3. **Protocol:** an Envoy mode word V2 first (v5 peers refuse it cleanly). The transport re-arm packet only if
   the ~7 s stage transition is judged too slow or per-stage server load matters.
4. **Game over and continues:** shared stocks for the pair; a lost stage ends the run for both; one continue
   token per run, spent by agreement.
5. **Adventure special stages** (Brinstar escape, F-Zero race, target bonus stages): skipped online for now;
   redesign for co-op is a later decision.
6. **Content:** the intersection of both players' unlocks and installed content, as the lobby's stage list does.
7. **The regenerated bridge** stays committed separately, as in earlier lanes.

Next: 7a (director skeleton + stage-end barrier) and 7b (Classic plan over the 1P tables) can start now;
7c needs stage 6, 7d needs stage 5.
