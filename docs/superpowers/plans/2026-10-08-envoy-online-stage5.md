# Envoy online stage 5: unified run record and reconnect groundwork (2026-10-08)

This revision supersedes the interrupted stage-5 draft in this file. User packet dated 2026-10-08 is binding.
Game edits: `worktrees/envoy-s5`, branch `agent/envoy-s5`; workspace edits: `worktrees/ws-envoy-s5`, branch `ws/envoy-s5`.
Inherited game implementation: `259ee2e6c`. No git writes, merges, commits, windowed runs or netplay runs in this lane.
Coordinator commits and runs the two-client proof. Build root: `_build/agents/envoy-s5`.

## Authority and scope

Stage 5 of `_research/envoy-netplay-scoping-2026-10-05.md` section 5: co-op run state, peer-to-peer resume,
abandon, continue offline and a lobby mode flag. Stage 6 owns online CPUs and playable co-op; stage 7 owns the
run director. Its accepted owner decisions are shared stocks for the pair, a lost stage ends both players' run,
and one continue token per run, spent by both players' agreement. The existing `E` lobby message gains three optional resource integers for V1; V2 requires them, so a
fresh guest takes the host's shared pool even when its own stock menu setting differs. No new message type.
Protocol stays 5; Envoy mode V2
`GW_ENVOY_MODE_COOP = 0x45560002` fits the existing handshake field. Server unchanged.

The specified `git show integration/2026-10-01/roguelite-100:docs/superpowers/plans/2026-10-08-envoy-online-stage7.md`
returned ?path does not exist?. Read the existing stage-7 workspace worktree's copy instead,
including its dated Owner decisions. This lane does not change that file or integration refs.

## One record for stages 5 and 7

`pc/platform/gw_netrun.h` owns RN2, a superset of the stage-7 spike's RN1. Keep its first seven fields,
`gw_nr_format` signature, `gw_nr_stage_index`, `gw_nr_parse` and `gw_nr_digest_of` so the coordinator can reconcile
both lanes without a second run format. The completed record has 19 fields:

```
RN2|seed|stage|loop|score0|score1|flags|ext|mode|round|winner|picks|stages|bw|x|stocks|continues|lost|digest
```

- `seed`: host-selected run seed, 1..2147483646. `stage`: zero-based depth (`game - 1`). `loop`: NG+ pass.
- `score0/1`: seat scores; `flags`: stage-director bits; `ext`: chosen external stage ID. Resume preserves
  all of these, including fields this stage does not itself author.
- `mode`: 8 hex digits, Versus V1 or co-op V2 (0 for a plain stage run).
- `round`: latest resolved reward. `winner`: `0`, `1`, or `n`.
- `picks`: two choices per resolved game beginning at game 2. With the seed, these are the causal,
  canonical representation of BOTH seats' bags/builds and keystones (`mod_progression.set_build`).
  This stage has no arbitrary online co-op drops: those need the stage-6/7 director to extend the record.
- `stages`: ordered content identity words, six hex digits per started game. `bw`: verified native build word.
- `x`: optional 16-hex script digest, or `-`. It is a comparison digest, not a recoverable bag payload.
- `stocks`: shared pair pool 0..198; a fresh co-op room reserves twice the configured per-seat stocks
  (4 per seat fallback). Versus uses 0. `continues`: 1 at run creation, 0 after spending it.
- `lost`: 0/1. Lost stage means stocks=0 and both seats stop. A disconnect is interruption, not a loss.
- `digest`: two salted FNV-1a words over the entire preceding body, salt `netrun:`; same as Lua
  `mod_codec.digest64`. Vector: `RN2|123456789|2|0|1|1|0|0|45560001|3|1|1302|abcdef123456|deadbeef|-|0|1|0`
  gives `235fd23981123889`.

State (`active`, `interrupted`, `abandoned`, `continued`) and local seat stay beside the text in settings.cfg.
Records fit its 511-byte value limit through 31 games and travel in 120-byte reliable lobby chunks.
Strict parsing rejects malformed/noncanonical numbers, invalid resource ranges, missing fields and bad digests.
The earlier unpublished 16-field RN2 draft is refused rather than guessing missing stocks/token values.
There is no transport or protocol bump; both clients must use the same source build as usual.

Native director helpers: `gw_nr_lose_stage` ends the pair; `gw_nr_continue(record, agreed_mask, restored_stocks)`
accepts only mask 3 (both seats), an existing loss, one remaining token and a valid positive pool. It consumes
the token once. These are record transitions; stage 7 must invoke them at its agreed stage-end barrier and
persist/broadcast the resulting record. Stage 5 does not insert a gameplay director into the co-op lobby.

## Resume and persistence

Both peers save at game start, result and resolved reward. A co-op room begins a record before gameplay.
On a reconnect, unfinished games are detected at lobby entry and retained as interrupted; resume replays
that stage from its recorded start. Ordinary completed-game rematches retain the live set.

Guest advertises a resumable record with `U`. Host requests differing text with `Q`; either side sends
`T` chunks; host sends `Y` after its decision. Equal records resume, compatible later boundaries win,
and divergent/missing/finished/wrong-seat/wrong-mode records start fresh. READY waits for the check.
Conflicting records can be chosen by host `gd.netplay_act("rresume", 1|2)`. The previous run is kept.
Resource differences at an equal boundary conflict; a prefix cannot restore a spent token or silently
advance past a lost stage. Record application preserves stocks, token, loss, loop, flags and external stage.

`gd.netplay_act("rabandon")` works from either seat in the lobby. Host sends the exact record in `T` chunks, then `Z`; both mark the old
record abandoned, clear the live history and begin a fresh seed. In a co-op room the new active record
immediately replaces the saved slot; therefore proof checks the new shared record and abandonment counters.

The survivor can leave and use `envoy continue [classic|adventure] [fighter]` for a saved Versus build.
The carry regenerates its local seat's records and keystones, preserves depth/loop, and raises only records
whose offline tier floor requires it. It then marks the saved record continued, preventing the pair from
resuming that record. This is a solo retail continuation, not restoration of a stage-7 co-op director.
Co-op offline continuation is still explicitly refused until that director has recoverable co-op state.

Read-only Lua API: `gd.netplay_run([live|saved|previous])` includes depth, loop, stocks, continues and lost
alongside the inherited seed, score, picks, stages, build word and digest. Lobby mode uses
`gd.netplay_act("envoymode", "off"|"versus"|"coop")` or `MELEE_NETPLAY_ENVOY=coop`. Co-op READY remains
refused with the stage-6 explanation. No new simulation writes, rollback state or hash word in this stage.

## Work and verification ledger

1. Read inherited diff and scoping/owner requirements; keep generated bridge separate for coordinator.
2. RED: native resource test rejected the 16-field record; Lua saved-depth test failed.
3. GREEN: append resources to RN2; parse/digest/bounds and agreed single-continue transitions tested;
   expose resource/depth fields to Lua; preserve depth and loop in offline carry.
4. Review found unified stage-7 flags/ext discarded during adoption. Add regression, observe failure,
   preserve those fields and verify exact adopted digest.
5. Run ALL `pc/tests/envoy_*.lua` suites from workspace root with path redirection into the game worktree.
   Clear wrapper arg[1] so `envoy_core_review.lua` runs its full suite rather than treating the filename as a case.
6. Further RED/GREEN: abandon with a divergent script note adopts the host's exact T-chunk record;
   a fresh co-op guest with a different local stock setting adopts the host's resource fields from E.
7. Build via root `tools/port/build.sh` with GW_MELEE/GW_BUILD_ROOT set to this lane; audit final bridge.
8. Run headless suite with vanilla ISO. Inspect failing game log; quote actual result in report.
9. Native standalone resources: workspace worktree `tools/port/native_test.sh envoy-netrun` with GW_ROOT set
   to root; source `pc/tests/envoy_netrun_test.c`. No game TU is compiled directly.
10. Proof driver Python syntax checked. Two real clients are NOT run in this sandbox. Exact coordinator
   commands and evidence expectations are in `_build/tmp/codex-envoy-s5-report.md`.

Ruling: existing isolated worktrees and coordinator-owned commits override draft merge/commit steps.
Ruling: RN2 causal pick history represents the currently supported deterministic builds; opaque x cannot
restore arbitrary future co-op drops. Director wiring and playable co-op remain stages 6/7.
Ruling: shared-stock initial amount is twice the room per-seat setting; owner specified shared semantics,
not a number. Stage-7 director may author a different agreed initial pool without changing RN2.

## Files and proof owed

Game: `gw_netrun.h`, additive run bookkeeping/tests in `gw_netplay.c`, bindings in `gw_script.c`,
`mod_progression.lua`, `retail_app.lua`, regenerated `main.lua`, `envoy_online_run.lua`,
`envoy_netrun_test.c`, ONLINE.md and COOP.md. Generated `gw_mex_bridge.c` is a separate commit.
Workspace: this brief, native-test selector, `tools/netplay/np_envoy_resume.py`, `np_s5_host.lua`, `np_s5_guest.lua`.

Proof driver starts its own server on 127.0.0.1, clients bind 127.0.0.1, uses explicit private ports,
joins guest by room code through Lua, simulates lag/jitter/loss and blackout, and covers reconnect,
process restart, mid-match replay, abandon and co-op READY refusal. Unique proof tags preserve prior
output; copied mods belong to each tag. No public server, merges or window launches here.

Still owed: two-client proof, menu/controller inspection, cross-platform proof, and stage-6/7 integration
of shared stocks, losses, agreed continue and recoverable co-op director builds. Unit tests do not prove
those gameplay paths. Full detailed command/output evidence belongs to the final report.

Final verification: build ID `8352b06b9acc081b` (`259ee2e6c+local`); bridge audit 18,829/18,829 resolved,
0 ECX/EDX prologues. Envoy native `pass=5 fail=0`; standalone resources PASS; Envoy Lua 74/74 PASS.
Full vanilla headless `pass=334 fail=1 total=335`: `mexid_disc_table` found 0 fighter/stage identities
(`MxDt.dat not on this disc`). This file and its test are unchanged by the lane; no baseline EXE was rebuilt
to claim a baseline reproduction. The complete suite is not green. Two-client proof remains owed.
