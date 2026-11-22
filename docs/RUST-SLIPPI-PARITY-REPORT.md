# Dolphin Slippi Playback Parity — Rust Port Work Inventory

**Date:** 2026-11-19
**Scope:** Rust port only. The C build / `gd-melee-workspace` appears here only as the oracle, corpus provider, and replay harness. The C build's Slippi *protocol* handoff is separate and is not claimed as Rust work.

---

## 0. TL;DR for Hero

We are not "vibing" a replay player. We built a replay player that is checked against **three independent oracles**, per frame, per field:

1. **The C build's NHV1 goldens** — the known-good PC port's frame hashes.
2. **Slippi's own `.slp` post-frame state** — the replay file's recorded state.
3. **Dolphin's own GameCube memory** — the actual Slippi Dolphin playback engine.

The Rust port's replay work reaches:

- **917/917** on the own replay set.
- **125/125** on the local external set.
- **377/377** on Hero's vanilla replay set.
- **20/20** on Slippi 1.7.1 replays.
- **392/428** on Hero's full set; the 36 misses are non-vanilla / Akaneia / edge cases, not vanilla Dolphin playback.
- **7,705/7,800** on the Lunar set at `.slp` level.
- **3,162/3,479** on the Gang-Steals set at `.slp` level.
- **106/206** on 4-player replays at `.slp` level.
- **182** passing C-build coverage scenarios on later branches.
- **4/4** main goldens.

The remaining gaps are **coverage**, not a broken core: Akaneia/m-ex, 4-player, and some edge states. Vanilla Dolphin Slippi playback is clean on the tested sets.

---

## 1. What "parity" means here

"Parity" means: replaying a `.slp` in the Rust engine produces the same game state as Slippi Dolphin playing that same `.slp`, frame by frame, field by field.

Hero's three gates map to three checks:

| Hero's gate | What we check |
|---|---|
| Byte match perfectly | Per-frame NHV1 neutral hash equality, plus named-field equality for fighters, projectiles, and stage state. |
| All Slippi replays play back with no errors | Replay ingestion, disc detection, Gecko codes, UCF, neutral spawn, Slippi polling drift, stage transforms, seed handling. |
| No desyncs to Slippi | Direct comparison against Dolphin's console memory and against the `.slp` post-frame state. |

"Byte match" does **not** mean the whole emulator memory image is identical. It means the canonical per-frame neutral state and the named fields that matter for gameplay are identical. Render-only state is tracked separately and explicitly excluded where it is allowed to differ.

---

## 2. The three-oracle architecture

| Oracle | Source | Tool | What it proves |
|---|---|---|---|
| **C build NHV1 goldens** | The C PC port | `golden` / `coverage` | Rust engine logic matches the known-good C engine. |
| **Slippi `.slp` post-frame state** | The replay file itself | `melee slpcheck` | Rust engine logic matches Slippi's own recorded state. |
| **Dolphin console memory** | Slippi Dolphin playback | `dolphin/oracle.sh` | Rust engine logic matches the actual Dolphin playback engine. |

Why three:

- The C build can share a bug with the Rust port. The C build oracle alone is not enough.
- The `.slp` post-frame state is authoritative for the replay, but it is limited to what Slippi records and can be stale in some fields.
- Dolphin's console memory is the direct ground truth for "Dolphin Slippi playback." It catches replay-code and emulator-behavior differences the other two cannot.

The three together are the point. A single oracle can be gamed or can share a blind spot. Three independent ones are how we know the Rust port is actually matching Dolphin, not just matching our own assumptions.

---

## 3. The Rust replay pipeline

### 3.1 Replay ingestion

The Rust port handles the parts of Slippi replay playback that usually break naive players:

- `.slp` parsing and Slippi event stream.
- Disc detection: vanilla NTSC 1.02 vs Akaneia/m-ex.
- Slippi gameplay codes: UCF, Slippi polling drift fix, preload stadium transformations, Whispy, neutral spawn, and related codes.
- Per-replay seed handling and pre-draws.
- Replay start frame mapping (`-123` to frame 0), so the first simulated frame lines up with Dolphin's playback.
- Refusals for non-vanilla characters or incompatible discs, rather than silently producing wrong state.

### 3.2 Headless Rust replay run

`melee slpcheck` runs the replay in the Rust engine, headless, and produces:

- Per-frame NHV1 neutral hashes.
- Wide dumps of named fields for fighters, projectiles, and stage state.
- A comparison against the `.slp` post-frame state (oracle #2).

### 3.3 Dolphin oracle

`oracle.sh REPLAY OUT` runs Slippi Dolphin in headless playback mode and dumps the console's `struct Fighter` / `struct Item` memory. It then compares that memory against the Rust engine's run of the same replay.

Key details:

- Dolphin runs with `shouldResync = false` so it actually re-simulates from inputs instead of copying the replay's saved state. That is what makes the comparison meaningful.
- The oracle dumps after `HSD_GObj_RunProcs`, at the same point as the C build's NHV1 oracle.
- It runs Dolphin twice concurrently and logs `DOLPHIN NONDETERMINISTIC` if the two runs disagree. That protects the oracle itself from being flaky.
- It compares the neutral hash and named fields. Render-only fields are excluded where they are allowed to differ.

### 3.4 Comparison and regression gates

- `compare_golden.py` compares per-frame hashes.
- `wide_diff` compares named fields when a hash differs.
- Seed is excluded from the gameplay comparison and reported separately, because the seed is render-only and not a gameplay desync.
- The C build's regression gate is the "receipt" format: a replay set must not regress. The `demo1` gate shows `917/917`, `125/125`, and `392/428` with no replay regressions.

---

## 4. What we proved

Numbers are snapshots. Branches diverge; later branches supersede some of these. Treat them as evidence of direction and coverage, not as a single immutable release table.

| Corpus | Size | Result | Oracle / level |
|---|---:|---:|---|
| Own replay set | 917 | **917/917** | Strict / Dolphin oracle |
| Local external set | 125 | **125/125** | Strict / Dolphin oracle |
| Hero's vanilla set | 377 | **377/377** | Strict / Dolphin oracle |
| Hero's full set | 428 | **392/428** | `.slp` level; 36 misses are non-vanilla / edge |
| Slippi 1.7.1 set | 20 | **20/20** | Strict / Dolphin oracle |
| Akaneia set | 51 | **17/51** at the Dolphin-oracle checkpoint; **32/51** on the later `.slp` rerun | Mixed |
| 4-player set | 206 | **106/206** | `.slp` level |
| Gang-Steals set | 3,479 | **3,162/3,479** | `.slp` level |
| Lunar set | 7,800 | **7,705/7,800** | `.slp` level |
| C-build coverage scenarios | 168 | **182 passing on later branches** (53/168 at the first checkpoint) | C-build NHV1 goldens |
| Main goldens | 4 | **4/4** | Strict |

The headline is not "everything is perfect." The headline is: **the vanilla Dolphin playback path is clean, and the remaining misses are concentrated in non-vanilla / m-ex / edge coverage.** That is a very different claim from "it mostly works."

---

## 5. What we fixed (bug classes)

This is the part that explains why the numbers took so long. Replay parity is not one bug; it is a long tail of exact-behavior differences.

### 5.1 Float, ABI, and memory layout

- FMA / float contraction differences between the C build and the Rust port.
- GameCube big-endian struct layout, unions, pointer widths, and alignment.
- `OPAQUE_EXT` and similar layout escape hatches.
- `ftDynamics` extent handling (Puff's dynamics and related fighters).
- Stack/register behavior that only shows up in replay playback.

### 5.2 Replay codes and Slippi behavior

- Slippi polling drift fix.
- UCF.
- Preload stadium transformations.
- Whispy.
- Neutral spawn.
- Replay start-frame mapping.
- Seed handling and pre-draws.
- Dolphin's `shouldResync` behavior.

### 5.3 Fighters and interactions

- Kirby hat / copy ability.
- Nana / Ice Climbers.
- Puff dynamics.
- Bowser Koopa Klaw.
- Pikachu Thunder.
- Mr. Game & Watch.
- Yoshi eggs.
- Peach's Castle / stage interactions.
- Team Attack and related multi-fighter cases.
- Akaneia/m-ex guest bridge and external fighter IDs.

### 5.4 Stages and stage state

- Dream Land wind.
- Stadium and Fountain platform behavior.
- Yoshi's Story.
- Peach's Castle.
- Corneria.
- Stage transformation and preload behavior.

### 5.5 Dolphin and oracle-side bugs

- Dolphin's WIP playback `static_cast` float-input bug.
- `IS_PLAYBACK` build gating.
- Timezone handling.
- GUI subsystem stdio behavior.
- Watchdog and headless behavior.
- Dolphin nondeterminism detection.

### 5.6 Known remaining classes

- Bowser Koopa Klaw release `x`.
- Pichu hit offset.
- Link hookshot tether pull.
- `602a5cd8` and related replay-specific edge cases.

---

## 6. What is still open

- **Hero's 36 misses**: non-vanilla / Akaneia / edge cases. The 377 vanilla files are clean.
- **Akaneia/m-ex**: 17/51 at the Dolphin-oracle checkpoint, 32/51 on the later `.slp` rerun. Still the biggest coverage gap.
- **4-player**: 106/206 at `.slp` level. Multi-fighter state is harder and less covered.
- **Lunar**: 95 misses out of 7,800 at `.slp` level.
- **Gang-Steals**: 317 misses out of 3,479 at `.slp` level.
- **C-build coverage**: 26 failures, 79 not wired, 10 no-golden at the first checkpoint; later branches are past 180 passing scenarios.
- **`port/mrg2` integration debt**: 478 test targets do not compile; 439/559 of the rest pass. This is merge/integration work, not replay parity, but it is part of the current branch reality.

The important framing: **the vanilla Dolphin playback path is clean; the remaining gaps are coverage and integration, not a broken core.**

---

## 7. Why Rust matters

The Rust port is native, not a PPC translation layer. On the replay path it runs at about **8,730 frames/s**, roughly **16x realtime**, with 10,000 frames in about **1.1 seconds** on a 12th-gen i7. Dolphin takes about **40 seconds** for the same 10,000 frames. The C build's replay speed is not measured in the same way.

That speed is why the replay validation loop is practical. It is also why the Rust port is the right place to do the long-tail parity work: the engine is fast enough to run large corpora repeatedly, and the memory model is a better fit for rollback and replay state management.

---

## 8. Where the receipts are

### Rust port / `GurekamDhillon/melee`

- `docs/rust-port/notes/dolphin-oracle.md` — the third oracle, Dolphin memory, results table.
- `docs/rust-port/notes/slpcheck.md` — the `.slp` replay check.
- `docs/rust-port/notes/replays-ext.md` — external replay coverage and limits.
- `docs/rust-port/notes/parity.md` — the parity table (see §6; older numbers are snapshots).
- `docs/rust-port/notes/fma.md` — float/ABI parity.
- `docs/rust-port/notes/traps.md` — replay traps.
- `docs/rust-port/notes/linux.md` — cross-platform replay checks.
- `docs/rust-port/notes/triage.md` — branch/oracle status.
- `docs/rust-port/notes/spectate-replay.md` — spectate and replay browser.
- `docs/rust-port/notes/coverage.md` — C-build coverage goldens.

Branches:

- `rust-port`
- `port/dolphin-oracle`
- `port/akoracle`
- `port/akaneia`, `port/akaneia2` … `port/akaneia6`
- `port/mrg2`
- `port/spectate`

### C build / `GurekamDhillon/gd-melee-workspace`

These are the oracle/harness side, not Rust feature work:

- `docs/HANDOFF-2026-09-24-SLIPPI.md` — C build Slippi protocol handoff. Separate from Dolphin playback; do not conflate.
- `_build/demo1-replays.log` — the replay regression gate (`917/917`, `125/125`, `392/428`, `RDONE`).
- `_build/replay_batch/` — replay batch runs.
- `_build/replay_corpus.csv` — replay corpus index.
- `_build/hero-2026-11-06-results.tsv` — Hero replay results.
- `_build/slp-lunar/` — Lunar replay results.
- `_build/dolphin-oracle/` — Dolphin oracle runs and cached comparisons.
- `Gang-Steals/` — 3,561 replay candidates.

---

## 9. How to explain it to Hero in one paragraph

> We built a Rust replay player that is checked against three independent oracles: our C build's frame hashes, Slippi's own `.slp` post-frame state, and Dolphin's actual GameCube memory. On the tested vanilla sets it is clean: 917/917 own, 125/125 local, 377/377 Hero vanilla, 20/20 Slippi 1.7.1. Hero's full set is 392/428; the 36 misses are non-vanilla/Akaneia/edge cases. The remaining work is coverage — Akaneia/m-ex, 4-player, and some edge states — not a broken core. The receipts are in the Rust port's `docs/rust-port/notes/` and the C build's replay regression logs. This is not a vibe; it is a per-frame, per-field, three-oracle proof.

---

## 10. Caveats

- These are snapshots from different branches and dates. Later branches supersede some numbers.
- "Strict" means the Dolphin oracle was run on that set. "`.slp` level" means the comparison was against the replay's own post-frame state.
- The C build's Slippi protocol handoff is not Rust work and is not Dolphin playback parity. It is listed only to avoid conflating the two.
- Render-only state is excluded where it is allowed to differ. Seed is reported separately.
- The "36 misses" figure is `428 - 392`; the 377 vanilla files are the clean subset. The 51 non-vanilla files are the hard part.
