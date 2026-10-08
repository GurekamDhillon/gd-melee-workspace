# Geno slice 7: online identity and rollback certification (brief, 2026-10-08)

**Status: built and run 2026-10-08 (resumed lane); results in section 7.** Lane `geno-s7` (game `agent/geno-s7`,
workspace `ws/geno-s7`), from the 2026-10-07 integration heads (game `47e2c09b2`, workspace `ea760c8`). Road: slice 2 plan
`2026-10-05-geno-full-fighter-slice2.md` (roadmap, D2, D8, section "Slice 7"), `melee/docs/geno.md` sections 22 and 23.
Tags: **[R]** read from source, **[I]** inferred, **[U]** unverified.

## 1. Where online stands today [R]

Defines are refused online at four places: `ftdata.c` -> `GenoDefine_Load` asserts `!Netplay_Enabled()` (`pc/geno/geno_define_data.inc`),
`gw_runtime.c` `gw_sl_parse_char` refuses `ck:N` and `geno:` tokens while netplay is enabled, the online character select does not list
them (`fs_css_roster`, `src/melee/gm/gmfrontend_select.inc`: defines are appended only when `!fcs.online`), and `docs/geno.md` 22 says so.

What already exists and is reused: `gw_mexid.c` gives every fighter and stage a CONTENT IDENTITY, both peers exchange the table on the
lobby channel (`MXE` chunks), play the INTERSECTION and name content in the scene string by `id:<16 hex>` so each side loads its own local
CharacterKind. m-ex fighters already ride this. `RB_GameHash` already folds `GenoDefine_StateDigest` for defined kinds (slice 2 D8, slice 3
articles, slice 5 Lua block).

## 2. Design (decisions taken; the ones that are not routine are listed for the owner in the report)

| # | decision | why |
|---|---|---|
| S7-D1 | **A define is a fighter in the mexid table**: kind FIGHTER, local id = its resident alias CK, hash = its ONLINE IDENTITY. It then flows through the lobby list, availability (`gw_Netplay_FighterAvailable`), the peer<->local CK mapping and `id:` scene tokens with no new transport. | the m-ex route is the proven one; a second identity mechanism would be a second thing to desync |
| S7-D2 | **Online identity** = mix("define", the entry's content id [whole entry JSON, overlay words, Lua module], and the RESOURCES the simulation reads: for `base: "mario"` the bytes of `PlMr.dat` + `PlMrAJ.dat` (not the retail Mario identity, which an attach overlay on Mario would change), for `base: "none"` the bytes of the animation bank, the plan and every costume model of `fighter`). A define whose resource file is absent is not online-eligible (logged). The Lua source and compiler are already in the content id (slice 5). Presentation art, FX packages, sounds tables and costume names are cosmetic or already in the entry. | the entry id alone does not cover files the entry names; clips decide hitbox positions |
| S7-D3 | **Alias numbers may differ between peers** (a peer with an extra define shifts the aliases). The mapping exists (`gw_MexId_LocalCkForPeer`); slice 7 PROVES the simulation does not depend on the numeric alias with a mismatched-install run. If it did, the fallback would be to require the same define set. | the m-ex design plays the intersection; requiring identical sets would make a stray installed define poison every online game |
| S7-D4 | A define the opponent lacks, or has with a different package, is **not selectable** (greyed with the reason on the select; a script/Lua pick, a scripted HELLO pick, or a lobby action naming it is REFUSED with the reason, never replaced by Marth). The reason names the define and says "missing" or "different version (yours X, theirs Y)". The names travel in one additive lobby message `MXD` (define key + short id), ignored by older builds. | "refused with a clear reason" |
| S7-D5 | The four refusals are replaced by ONE condition: online, a define is allowed only when it is in the mexid table (it has an identity). Offline behaviour is unchanged. | |
| S7-D6 | **Digest coverage is a test, not a review.** A native test perturbs every 32-bit word of `GenoState` and `GenoLuaBlock` and asserts the digest changes unless the word is in a short, reasoned exclusion list. A new field added by a later slice fails the test until it is hashed or excluded on purpose. | slices 2-6 added state "as they went"; this makes the audit permanent |
| S7-D7 | Lua faults online: see section 5. | |

Not in this slice: replay headers for netplay matches (no `.slp` can hold a define: ELEVATED), a protocol-version bump (none taken: the
handshake is unchanged; `MXD` is an additive lobby message), voice/announcer, Kirby copy.

## 3. Audit of Geno state against snapshots and the hash (S7-1)

Done: test `geno_digest_coverage` walks every word of `GenoState` and `GenoLuaBlock` (`melee/docs/geno.md` section 24.2). Findings: `last_check` and `counters` were not hashed (both fixed); everything else is hashed or excluded with a written reason. The Geno blocks are game memory, which the savestate covers whole.

## 4. Proof plan

1. Native: define identity stable and independent of the alias; identity changes with a changed overlay word, a Lua source byte, a changed
   resource file; the wire carries it; `OnlineFighter`/mapping for a define; the reason text for missing and for different; the digest
   coverage test; a registry-level test that a define without a resource is not eligible.
2. Two clients over loopback (`netplay_local.ps1` / `np_drive.py --local-server --offscreen`, `MELEE_NETPLAY_BIND=127.0.0.1`, local server
   on 127.0.0.1), `MELEE_NET_SIM` lag/jitter/loss, `MELEE_PAD_BOT` on both, `MELEE_RB_HASHLOG`: Striker, Courier, Charger as mirror and
   against retail Fox/Marth; long sets (lobby, several games); desyncs counted from the log (`netplay: DESYNC`), confirmed-frame hash
   logs compared.
3. Refusals: package different on one side; define missing on one side; mismatched alias order (must play, 0 desyncs).
4. Windows against Linux (WSL) with a define, if the firewall and WSL network allow it without a prompt (otherwise reported as owed).
5. Before reporting: merge the latest integration heads, rebuild, re-run the proofs.

## 5. Lua fault policy online (decision to ELEVATE)

Today a fault drops the call's writes and commands, adds one to `Geno_LuaBlock.faults` (hashed) and sends the fighter to `auto`. Budgets
are counted in VM instructions and allocated bytes, never time, so a fault happens on the same tick on both peers when the package is the
same: it is deterministic and cannot itself desync. Recommendation: **keep the soft fault online** (a hard match fault disconnects both
players for an author's bug, and nothing is gained in determinism), log it on both sides, and show it in the LAB only. One real hazard
found while reading: the heap budget counts bytes Lua asks for, and Lua's value size differs between the i686 Windows and i686 Linux ABIs
(a `double` is 8-aligned in a struct on Windows, 4-aligned on Linux, so a 16-byte value is 12 bytes), so a call that grows the heap to
within about a quarter of the 64 KB budget could fault on one OS only. The flag is built (2026-10-08): `MELEE_GENO_FAULT_ONLINE=hard` ends the match on a CONFIRMED faulting frame; default soft. No fixture faults, so peak heap growth was not measured. Recommendation:
`tools.geno.check` warns above 32 KB peak growth; owner decides whether to make the accounting ABI-neutral.

## 6. Owed / not claimable from a headless or offscreen run

Anything that must be seen on a monitor (the online select's greyed tile and the reason text on screen) is owed to a person; the evidence
here is logs and state read over the console.

## 7. Results (build id `8c100b8c47a12269`, game `agent/geno-s7` 7334bf0c0 plus the workspace tools, 2026-10-08)

All runs: two clients on loopback (`MELEE_NETPLAY_BIND=127.0.0.1`, a matchmaking server of our own on 127.0.0.1, UDP ports 54700-54999, windows parked at 30000,30000), `MELEE_PAD_BOT` fuzz on both, `MELEE_RB_HASHLOG` on both; "frames" = confirmed-frame checksums both sides logged and that agree (mismatch 0 on every row); desync = `netplay: DESYNC` lines (0 on every row). Sim presets: lag=60 is `lag=60,jitter=15,loss=5`; lag=100 is `lag=100,jitter=40,loss=10,burst=3,dup=2,spike=6000:350`.

### 7.1 Scripted matrix (`tools/netplay/geno_matrix.py`; 110 s each, rollbacks in the hundreds)

| scenario | fighters | sim | frames | desyncs | verdict |
|---|---|---|---|---|---|
| mir_striker | v v sim=lag=60 | frames=5508 | 5508 | 0 | play |
| mir_courier | v v sim=lag=60 | frames=6124 | 6124 | 0 | play |
| mir_riposte | v v sim=lag=60 | frames=6223 | 6223 | 0 | play |
| mir_caster | v v sim=lag=60 | frames=6178 | 6178 | 0 | play |
| striker_v_fox | v v sim=lag=60 | frames=5487 | 5487 | 0 | play |
| fox_v_courier | v v sim=lag=100 | frames=4802 | 4802 | 0 | play |
| charger_v_marth | v v sim=lag=60 | frames=6158 | 6158 | 0 | play |
| marth_v_riposte | v v sim=lag=100 | frames=4017 | 4017 | 0 | play |
| courier_v_striker | v v sim=lag=60 | frames=5499 | 5499 | 0 | play |
| charger_v_riposte | v v sim=lag=100 | frames=4364 | 4364 | 0 | play |
| caster_v_fox | v v sim=lag=60 | frames=6121 | 6121 | 0 | play |
| alias_striker | v v sim=lag=60 | frames=6224 | 6224 | 0 | play |
| alias_hero_v_striker | v v sim=lag=100 | frames=4753 | 4753 | 0 | play |
| lan_striker | v v sim=lan | frames=4879 | 4879 | 0 | play |
| mir_charger | v v sim=lag=100 | frames=4883 | 4883 | 0 | play |
| soak_courier_v_charger | v v sim=lag=60 | frames=24088 | 24088 | 0 | play |
| soak_striker_v_riposte | v v sim=lag=100 | frames=19876 | 19876 | 0 | play |

(The soaks are 600 s each: Courier v Charger 24088 frames, Striker v Riposte 19876 frames.) `alias_*` rows give the guest the "less" install (hero, striker only), so the same fighter has a DIFFERENT resident alias on the two peers: 0 desyncs, which proves the simulation does not depend on the numeric alias (S7-D3). A first run of `mir_charger` was lost to a UDP port collision with another lane's server (`Could not open UDP port 51892`); the tools now pick free ports in this lane's range and it passed on the rerun.

### 7.2 Through the real lobby (`geno_lobby.py`: Atlas menu, room code by `gd.netplay_act("code", ...)`, a pick, strikes, ready, 3 games of a set, results screens)

| run | fighters | sim | games | desyncs | rollbacks |
|---|---|---|---|---|---|
| q7 | Striker v Striker | none | 3 of 3 started and ended | 0 | n/a |
| q8 | Courier (host) v Riposte (guest) | lag=60 | 3 of 3 started and ended | 0 | 1029 (max depth 7) |

### 7.3 Refusals

| run | what differs | result |
|---|---|---|
| p4 lobby | the host picks Courier, the guest has no Courier | host: `GENOLOBBY pick refused: Vanilla Courier: your opponent doesn't have it`; log `mexid: define Vanilla Courier is not in common: the peer does not have it`; no match started |
| p5 lobby | Riposte on both, the guest's Lua has one constant changed (1.5 to 1.6) | both sides: `pick refused: Vanilla Riposte: your opponent has another version`; no match |
| p1 scripted | the same one-constant difference | the guest refuses the host's scene: `content you don't have: fighter <id>` (no lobby traffic on this path, so no define name) |
| p2 scripted | host picks Courier, guest has hero+striker only | `content you don't have: fighter <id>` |

### 7.4 Native tests

`run.sh --test`: 338 of 338 pass (includes `mexid_define_online`, `geno_digest_coverage`, `geno_lua_fault_policy`).

### 7.5 Windows against Linux (WSL)

One match, Windows host (P1, Vanilla Striker, alias 122) against a Linux guest (WSL Debian rootfs, i686 ELF built from the same game commit, P2, Vanilla Courier, alias 125), `tools/xplat/net_pair.py s7_xp1 --mode direct --bind --offscreen` (new flags: `--win-mods/--lin-mods`, `--bind` binds each client to its own address on the WSL link, 172.21.48.1 and 172.21.63.92, never 0.0.0.0; this is the only run that used a non-loopback address, on the machine's private WSL link), `MELEE_NET_SIM lag=60,jitter=15,loss=5`, 2 stocks / 2 minutes, both sides with the six fixtures from one folder (copied to `~/lb2/s7mods`).

- Both builds print the same build id: `build id 7379f7b7a4bac4cb = sources 8c100b8c47a12269 ... + numerics c5bfbfa7f19e2d9c`. Both log `61 fighter/stage identities; mods: vanilla-caster#6d46,...` and the same `match agreed - "...p1=id:5bf681dbe8ece6d8/c0/hu;p2=id:29adb1cbbbc5b64d/c0/hu..."`. The match ran to its end: 7434 shared confirmed frames, Windows `rollbacks 538 (avg depth 4.70, max 7), desyncs 0`, **0 `netplay: DESYNC` lines on either side**, `netplay: match over` on both.
- The per-frame hash logs (`MELEE_RB_HASHLOG`, compared by net_pair) differ in 237 of 7434 frames, every one an ISOLATED single frame (no run longer than one). The same run with retail Fox v Marth and no mods (same builds, same sim) differs in 127 of 7433. So the isolated differences are a Windows-vs-Linux property of that log that does not involve a define, and the game's own checksum exchange never flagged one. Windows-vs-Windows runs in 7.1 and 7.2 have 0 differing frames. OWED (not this slice): why the log differs cross-OS (suspect: the log hashes something the detector's checksum leaves out, or the order a rolled-back frame is logged); it is not evidence of a define desync, and it is not evidence of its absence at the hash-log level.
- The first two attempts connected only after ~150 s: a freshly named Windows sandbox exe (`runs/n_s7_xp1/melee-pc.exe`) had no firewall rule yet for the non-loopback bind and Windows asked; once the rule existed (Allow) the connection was immediate. Reuse the run name.



### 7.6 Found and fixed in this slice

`last_check` and `counters` were not in the rollback hash (section 3 audit); the lobby proof exposed that a script's pad claim keeps pad 1 neutral and silences `MELEE_PAD_BOT` (the proof script releases it for the match); a port collision between lanes (tools now pick free ports).
