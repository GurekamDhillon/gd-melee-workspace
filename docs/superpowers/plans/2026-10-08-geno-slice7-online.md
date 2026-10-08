# Geno slice 7: online identity and rollback certification (brief, 2026-10-08)

**Status: brief written before the build; results are filled in at the bottom as they are proven.** Lane `geno-s7` (game `agent/geno-s7`,
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

Filled in below (section 7) with the method and the findings.

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
within about a quarter of the 64 KB budget could fault on one OS only. Measured numbers for the fixtures are in section 7. Recommendation:
`tools.geno.check` warns above 32 KB peak growth; owner decides whether to make the accounting ABI-neutral.

## 6. Owed / not claimable from a headless or offscreen run

Anything that must be seen on a monitor (the online select's greyed tile and the reason text on screen) is owed to a person; the evidence
here is logs and state read over the console.

## 7. Results

(filled in as proven)
