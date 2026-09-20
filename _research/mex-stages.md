# m-ex custom stages: `grFunction`, the stage tables, SSS and stage audio

Companion to [`mex-ppc-interpreter.md`](mex-ppc-interpreter.md) (the interpreter and the
`ftFunction` blob format, all of which applies unchanged here), [`mex-item-spawn.md`](mex-item-spawn.md)
(`itFunction`, the closest structural analogue) and [`mex-data-layer-design.md`](mex-data-layer-design.md)
(`MxDt.dat` / `mexData`).

Everything below was **dumped off the real discs** before any code was written. Where a claim rests
on evidence, the evidence is named. Reproduce with `tools/mex_port/dump_mxdt.py`,
`dump_ftfunction.py --symbol grFunction` and `ppc_disasm.py`.

Discs used: `C:/iso/Akaneia.iso` and `C:/iso/SSBM ACE Build v2.0.0.iso`.

---

## 1. The headline: the port already has m-ex's stage table

`grFunction` is to stages what `ftFunction` is to fighters, but the stage path is **far simpler than
the fighter path**, because m-ex did not invent a new table. It reuses the game's own.

`mexData` root word `+0x2C` (m-ex `Arch_grFunction`, which `dump_mxdt.py` labels `stage_desc`) is an
array of `internal_stage_count` pointers to 13-word rows, and those rows are laid out
**byte-for-byte like the port's `struct StageData`** in `src/melee/gr/types.h`. The port's
`stage_datas[]` in `src/melee/gr/ground.c` *is* that array.

| word | `StageData` field | evidence it is this field |
|---|---|---|
| 0 | `grkind` | equals the row index on every non-empty row, 0..95 |
| 1 | `callbacks` (`StageCallbacks*`) | `0x803Exxxx` on vanilla rows; `0xFFFFFFFF` on added ones; m-ex's `Get grFunction.asm` loads `0x4(row)` |
| 2 | `data1` (`char*`) | an in-archive `"/GrXx.dat"` string, immediately after the row |
| 3 | `on_init` | |
| 4 | `on_demo_init` | |
| 5 | `on_load` | |
| 6 | `on_start` | |
| 7 | `callback4` (`Predicate`) | |
| 8 | `on_touch_line` | |
| 9 | `on_check_shadow_render` | |
| 10 | `flags2` | `1` on every populated row |
| 11 | `joints` | |
| 12 | `joint_count` | |

13 words = **0x34**, which is exactly the `subi r28, r28, 0x34` in m-ex's
`SSS Expansion/grFunction References/Unk.asm`. Row-to-row stride in the archive varies (0x34..0x40)
only because each row's filename string is stored inline right behind it.

**Rows 0..70 reproduce the port's compiled-in `stage_datas[]` exactly** — including the two NULL
holes at internal 23 and 26 and the `grTe` alias at 35. Rows 71+ are the added stages.

## 2. `grFunction` blob shape — and the one real difference from `ftFunction`

The header is the identical `MEXFunction` struct (`mex-ppc-interpreter.md` §1/§9), and `Reloc` is
bit-for-bit the same algorithm — `gw_ftfunction_reloc()` is shared between the two loaders with no
changes.

**The difference is `Overload`.** For a fighter, `ReplaceThis` selects a slot in a *separate*
`Arch_FighterFunc[slot][kind]` table. For a stage:

> **`ReplaceThis` is a WORD INDEX INTO `StageData` ITSELF** (0..12), and `Overload` writes
> `code_base + ReplaceWith` straight into that word of the stage's own row.

m-ex's `Init grFunction.asm` makes this explicit: it computes `Arch_grFunction[internalID]` (one
pointer per stage) and passes *that row* as `Overload`'s table. There is no per-kind indirection
layer at all.

So a stage blob's `functionRelocTable` is a machine-readable list of *which `StageData` fields this
stage supplies*. Slot 1 is the interesting one: it is **data, not code** — the blob's own
`StageCallbacks[]` array, which m-ex's debug symbols name `map_gobjs`.

Across all 25 of Akaneia's added stages, the overridden slots are always a subset of
`{1, 3, 4, 5, 6, 7, 8, 9}`. Words 0, 2, 10, 11 and 12 are **never** overridden — those come from
the MxDt row.

### Where it installs

m-ex inserts `Init grFunction` at guest `0x801C60C8`, which is inside `grDatFiles_801C6038` — right
after the stage archive's public symbols have been pulled out. The blob is relocated **in place
inside the stage's own loaded archive**, so it lives exactly as long as the file and costs no
persistent memory. The port does the same (`Ground_801C0754`, just after the `grDatFiles_801C6038`
call, using `grDatFiles_GetArchive()->unk0`).

### Calling into a blob from the port

`StageData`'s function fields are read by gwtool-compiled game code, which would call a guest
address as if it were native x86. Two seams are therefore needed, and both already existed for
fighters:

- The seven function words get **native trampolines** that interpret the override, or fall back to
  the clone-base function (§4). See `gw_Mex_GrOnInit` and friends.
- A custom stage's `StageCallbacks[]` lives *in the blob*, so its `on_init` / `gobj_proc` /
  `callback3` are guest addresses. `Ground_SetupStageCallbacks` (`src/melee/gr/inlines.h`) binds
  each through `gw_Mex_GrBind` → the shared thunk pool.

The `flags` word of a `StageCallbacks` entry needs **no** shim: game code reads it through a guest
pointer, and guest MEM1 is directly dereferenceable with gwtool byte-swapping.

One more site: **`grTSeak_80223908` is the generic map-gobj creator that every custom stage's
`onInit` calls** — it is the function m-ex repoints at `Get grFunction`
(`grFunction References/Create_map_gobj/GrTSk.asm`). It must index the *running* stage's callbacks
table, not the compiled-in `grTSk_StageCallbacks`.

---

## 3. The index spaces — there are only TWO

Unlike fighters (four spaces: m-ex internal, m-ex external, port `FighterKind`, port
`CharacterKind`), stages have two, and **both are the port's existing ones**. m-ex keeps the vanilla
numbering and appends.

- **INTERNAL** = the port's `GrKind`. What `stage_info.grkind` and `stage_datas[]` use.
- **EXTERNAL** = the port's `StKind`. What `stage_id_map[]` and the stage-select screen use.

### Evidence: the 286-entry diff

`Arch_Map_StageIDs` is `external_stage_count` × 12 bytes, and it is the **same
`struct StageIdMapEntry { GrKind grkind; s32 unk1; s32 unk2; }`** the port already declares. Two
independent proofs of the stride: the table ends exactly where the `mexData` root begins
(`0x89FC + 313*12 = 0x98A8`), and:

> Extracting all 286 entries of the port's `stage_id_map[]` from `stage.c`, resolving the
> `Gr_Kind_*` enum from `forward.h`, and diffing against `Arch_Map_StageIDs` gives
> **zero mismatches on Akaneia AND on ACE.**

The mapping rule for added stages is the same on both discs:

```
external 286 -> internal 23   (a vanilla empty row)
external 287 -> internal 35   (the grTe alias)
external 288 + k -> internal 71 + k        for every added stage
```

### Which space indexes which table — THE TRAP

`Arch_Map` (`mexData` root `+0x28`) holds six tables and they are **not all indexed the same way**.
Five of the six are INTERNAL; only `StageIDs` is EXTERNAL.

| `Arch_Map` field | offset | indexed by | stride | element |
|---|---|---|---|---|
| `StageIDs` | `+0x00` | **EXTERNAL** | 12 | `{GrKind grkind; s32; s32}` |
| `Audio` | `+0x04` | **INTERNAL** | 3 | `{u8 ssm_id; u8 echo; u8 echo2}` |
| `LineTypeData` | `+0x08` | **INTERNAL** | 8 | `{s32 index; void* }` (an absolute `0x803Bxxxx` vanilla address, not a data offset, not relocated) |
| `StageItemLookup` | `+0x0C` | **INTERNAL** | 8 | `{s32 count; u16* global_item_kinds}` |
| `StageNames` | `+0x10` | **INTERNAL** | 4 | `char*` |
| `Playlists` | `+0x14` | **INTERNAL** | 8 | `{s32 count; PlaylistEntry* }` |

`StageNames` and `Playlists` being internal-indexed is the trap, and it cost real time: indexing
them with an *external* id runs off the end of the pointer array into the string pool and returns
**plausible-looking text**. Reading `StageNames[284..312]` with the external space yields
`'0x54617267'`, `'0x65747321'` … which is `"Targ" "ets!"` — the raw bytes of the name strings
themselves, reinterpreted as pointer words. Nothing errors; it just quietly lies.

The reliable way to find the true count of a pointer-array table is the archive's **relocation
set**: a real pointer word is in it, a string byte is not. Both tables stop at exactly
`internal_stage_count`.

Independent confirmation from m-ex's own sources: `GetMEXPlaylist.asm` and `GetGrItemID.asm` both
read the stage id from `0x88(0x8049E6C8)` — that is `stage_info.grkind`, the **internal** id.

---

## 4. The clone-base trap, stage edition

The fighter-side rule ("an unregistered m-ex slot does not fail — it silently runs the clone base's
handler") applies here verbatim, and the shipped data is built to rely on it.

Rows 71..86 ship with an **existing stage's** `on_*` words. Row 71 (`GrOPc`) carries
`grOldPupupu`'s set; rows 76..86 carry various others. A slot the blob does not override therefore
runs that base stage's handler.

Consequences for the port:

- Those words are absolute guest addresses and must be resolved through `gw_mex_bridge_lookup` to
  the native `gw_` function, exactly as `gw_Mex_FtFunc` does for fighters.
- Rows 87..95 have all-zero function words, so an unoverridden slot there is genuinely empty.
- The trampolines should **log every clone-base resolution once**, so an unregistered slot is
  visible rather than mysterious.

Related, and the reason rows must be **dense**: a row is only worth synthesising when the stage's
file is actually on this disc (`gw_DVDConvertPathToEntrynum >= 0`). A declared-but-absent stage that
gets a row sends the first load at a missing file. This also matters on a *vanilla* disc, because
Akaneia's `MxDt.dat` ships inside the Sonic mod — so a vanilla run can see the full 96-row table and
none of the 25 stage files.

---

## 5. Vanilla-sized structures a new stage index falls outside

| structure | where | vanilla size | Akaneia needs | ACE needs |
|---|---|---|---|---|
| `stage_datas[]` | `gr/ground.c` | **111** | 96 — fits | **155 — OVERFLOWS** |
| `stage_id_map[]` | `gr/stage.c` | **286** | 313 — overflows | 372 — overflows |
| `s32_arr_803BB6B0[0x6F][3]` | `lb/lbaudio_ax.static.h` | **111** | 96 — fits | **155 — OVERFLOWS** |
| `mnStageSel_803F06D0[]` | `mn/mnstagesel.static.h` | **30** | 67 — overflows | 163 — overflows |
| `1ULL << ssm_id` | `lbAudioAx_80026EBC` | **64 banks** | ids to 77 — overflows | ids to 100 — overflows |

Sizing off Akaneia alone gives the wrong answer twice: `stage_datas[]` and the audio table look
"already big enough" at 96 and are not at 155. **Size against ACE, not Akaneia.**

---

## 6. Stage audio

### SFX — `Arch_Map_Audio[internal]`, 3 bytes

The vanilla counterpart is **`s32_arr_803BB6B0[0x6F][3]`** in `src/melee/lb/lbaudio_ax.static.h`,
and its first rows are byte-identical to the dumped table (`{0x37,0x01,0x01}`, `{0x37,0x01,0x01}`,
`{0x22,0x01,0x01}`, `{0x37,0x01,0x01}`, `{0x25,0x01,0x01}` …). Filling `[71..]` from mexData is a
short loop.

| byte | meaning | evidence |
|---|---|---|
| 0 | SSM (sound bank) file id | `SFX_PlayStageSFX.asm` reads `0x0(row)`, computes `ssm_id * 10000 + sfx_id`, calls `Ground_801C53EC`; `StageAudio References/GetStageSSMID.asm` patches `0x80027A14` to read the same byte |
| 1 | echo / reverb | `StageAudio References/SetEcho.asm` reads `0x1(row)` |
| 2 | second echo parameter | always equal to byte 1 in every row sampled |

### The `1ULL << ssm_id` overflow (FOUND, NOT FIXED)

```c
u64 lbAudioAx_80026EBC(StKind stkind) {
    GrKind grkind = Stage_8022519C(stkind);
    ...
    if ((shift = s32_arr_803BB6B0[grkind][0]) == 55) return 0;
    return 1ULL << shift;          /* <-- shift can be 56..100 */
}
```

Added stages' SSM ids are **55..77 on Akaneia** (9 of 25 above 63) and **38..100 on ACE** (11 of 84
above 63). `1ULL << 77` is undefined behaviour and the bank never loads, silently.

This is the **identical** bug the fighter side already hit and worked around — see the `TARGET_PC`
block in `lbAudioAx_8002785C`, whose comment reads "each player's bank is requested BY INDEX, which
reaches the banks past the u64 mask", and the one in `lbAudioAx_80027648` ("a bank past the u64
mask (Sonic's 66) has no bit to set"). Stage banks need the same by-index request path.
Expect *no stage SFX at all* on the affected stages until this is done.

### BGM — `Arch_Map_Playlists[internal]`

`{ s32 count; PlaylistEntry* entries; }`, entry = 4 bytes `{ u16 bgm_id; u8 unk; u8 chance; }` where
`chance` is a percentage weight. `count == 0` means no playlist. Track names come from
`mexData.music +0x0C` (`Arch_BGM_Labels`); `bgm_count` is 139 on Akaneia, 231 on ACE.

Decoded examples (Akaneia):

```
[ 7] Hyrule Temple  3: 0x4B/90 "Temple", 0x82/50 "Dark Golden Land", 0x01/16 "Fire Emblem"
[71] Peach's Castle 64  1: 0x63/100 "Peach's Castle 64"
[76] Metal Cavern       1: 0x62/100 "Metal Mario Fight"
[84] Delfino Plaza      2: 0x73/75 "Delfino Plaza", 0x74/64 "Ricco Harbor"
[85] Green Hill Zone    5: 0x72/82, 0x8A/61, 0x69/56, 0x86/50, 0x87/36
[83] Village           12: the K.K. Slider set plus four time-of-day tracks
```

---

## 7. SSS (stage select screen) expansion

The port's `mnStageSel_803F06D0[]` in `src/melee/mn/mnstagesel.static.h` maps one-to-one onto
`Arch_Menu_SSS` (`mexData.menu +0x08`), with **one difference, and that difference is the whole
expansion**:

| | port (vanilla) | m-ex |
|---|---|---|
| stride | **0x1C** | **0x20** |
| external stage id | `u8 stkind`, word 2 byte 3 | **`s32` at `+0x1C`** |

313 (let alone 372) external ids do not fit in a `u8`, so m-ex widened the field and moved it to its
own word. Word 2's byte 3 is **zero in every m-ex row**, which is the confirming detail.

Everything else lines up exactly: `x8`/`x9`/`xA` packed into word 2, the four floats in words 3..6,
words 0..1 runtime (`HSD_JObj*` and the random-picker cooldown). Spot check, port entry `[1]`
`{0x2, 0x01, 0x0C, stkind=0x0B, 3.1, 2.7, 1.0, 1.0}` against m-ex `[1]`
`w2=0x02010C00, w3..w6 = 3.1 2.7 1.0 1.0, w7=0x0B`.

The work, therefore:

1. `NUM_STAGES` 29 → `metadata.sss_icon_count - 1`; `SSS_ICON_COUNT` 30 → `sss_icon_count`
   (67 Akaneia / 163 ACE). The port's `mnstagesel.static.h` already derives `NUM_STAGES` from
   m-ex's count in a comment — it is hard-coded 29 today.
2. Widen `stagelistinfo.stkind` to `s32` under `TARGET_PC` and fill the table from
   `mexData.menu.SSS`.
3. m-ex's `MnSlMap References/` icon-index, pointer and stride adjustments.

Entries with `w2 = 0x01000000` and `w7 = 0` are **blank slots** (the type byte is 1); `0x03` is the
"Random" icon. Confirming entry: SSS `[61]` has `w7 = 0x125` = external 293 = Meta Crystal.

**Until this lands a custom stage is only reachable programmatically, not selectable.**

---

## 8. Picking the first stage to land: GrOMc / Meta Crystal

Choose by **dependency count, not file size**. Dumping every added stage's `functionRelocTable`
and `instructionRelocTable` (`dump_ftfunction.py --symbol grFunction`) gives the whole comparison at
a glance; the branch targets tell you what the blob needs from the engine.

`GrOMc.dat` — internal **76**, external **293** — wins on every axis:

- 0x1E8 (488) bytes of code, 25 instruction relocs.
- **All 8 function slots overridden** (`1,3,4,5,6,7,8,9`), so nothing falls through to a clone base:
  the §4 trap cannot bite on the very first stage.
- 13 branch targets, **every one a vanilla engine function already in the bridge**:
  `grTSeak_80223908`, `Ground_801C39C0`, `Ground_801C3BB4`, `Ground_InitMapColl`,
  `Ground_UpdateMapColl`, `grAnime_801C8138`, `grMaterial_801C8858`, `lb_800115F4`.
- **No m-ex standalone functions.** (`GrOPc` needs `GetGrItemID` at guest `0x803D708C`; `GrOPz`
  needs `SFX_PlayStageSFX` at `0x803D7078`. Those are the `0x803D7xxx` block — m-ex injects its
  helpers over `gmResultCharacterData`, which is why a branch there looks like a branch into
  `.data`.)
- **No stage items** — `StageItemLookup[76].count == 0`. (`GrOPc` needs custom item 237.)
- **No floating point at all**, so none of the bridge's known float-marshalling gaps are on the
  path.

Its `map_gobjs` is 3 `StageCallbacks` entries; entry 2's flags word is `0xC0000000`, i.e. `flags_b0`
(lighting source) and `flags_b1` (fog source) — both read by `ground.c` straight out of guest
memory.

Runners-up if GrOMc ever proves unsuitable: `GrTWf`/`GrTDd`/`GrTLc` (target-test stages, 5 slots,
but they depend on the corresponding m-ex fighter existing) and `GrOPz` (Planet Zebes 64, 3 slots,
but floats and `SFX_PlayStageSFX`).

---

## 9. ACE

**ACE has a built ISO: `C:/iso/SSBM ACE Build v2.0.0.iso`.** (An earlier note of mine claimed only a
patcher + zip existed under `_build/ace/`; that was wrong. Dump the ISO.)

| | Akaneia | ACE |
|---|---|---|
| `internal_stage_count` | 96 | **155** |
| `external_stage_count` | 313 | **372** |
| `sss_icon_count` | 67 | **163** |
| `ssm_count` | 78 | 103 |
| `bgm_count` | 139 | 231 |

The layout is identical — same strides, same two index spaces, same `external 288+k → internal 71+k`
rule, zero mismatches against the port's `stage_id_map[0..285]`. ACE **preserves Akaneia's
0..95 numbering** (internal 71 is still `/GrOPc.dat`) and appends 59 more at 96..154: Arena Ferox,
Awakening Wood, Castle Siege, Cool Cool Mountain, Delfino-era stages, and so on.

So supporting ACE stages is a matter of **sizing**, not of new mechanism — see §5, where two
structures that look sufficient on Akaneia are not on ACE.

---

## 10. Trap: cached mexData pointers vs. the test harness

`gw_test.c` restores a MEM1 snapshot between tests, and its own comment says "a test must set up any
platform state it depends on". Platform **statics** are not restored. Any module that caches a guest
address into `mexData` therefore keeps a pointer to a region whose contents have been wiped — the
whole 104,948-byte archive reads back as zero, with no fault.

The fighter accessors merely degraded to "no mexData", which is why this went unseen for a long
time; the first *stage* read of the same data failed loudly (`grfunction_rows`, on its first-ever
execution).

Fixed in `melee` commit `579c257bf`: `gw_Mex_InvalidateAfterMem1Restore()` drops the mexData and
persist caches and calls `gw_Mex_GrInvalidate()`; `gw_test.c` calls it after each restore. Two
things fell out of that:

- `gw_mex_persist_alloc` is a **bump allocator that never frees**, so re-initialising leaked its
  384 KB region once per cycle. Its `base`/`cap`/`used` moved to file scope so the invalidation can
  rewind instead of re-allocating.
- The snapshot restores the persist region's *contents* too, so rewinding is correct, not merely
  cheaper.

**Rule for any new module that reads `mexData`:** cache nothing across a MEM1 restore, or hook
`gw_Mex_InvalidateAfterMem1Restore`.

---

## 11. Status and what is left

Landed (`melee` `79213f55f`, "Merge agent/stages"): `pc/platform/gw_mex_grfunction.[ch]` — the stage
tables, the blob loader, the seven `StageData` trampolines and three `--test` cases; plus the
game-side wiring in `gr/ground.c`, `gr/stage.c`, `gr/inlines.h` and `gr/grtseak.c`, and four
additive exports from `gw_mex_ftfunction_runtime.c` (`gw_Mex_RuntimeInit`, `gw_Mex_Rtoc`,
`gw_Mex_StackTop`, `gw_Mex_Callable`, `gw_Mex_MexData`) so stage blobs share the fighter path's
interpreter environment rather than standing up a second one.

Not done, roughly in dependency order:

1. **Meta Crystal has never been run.** A windowed run on external 293 is the outstanding
   verification. Expect `grfunction:` log lines naming the install and each overridden word.
2. **Stage audio**: fill `s32_arr_803BB6B0[71..]`, and fix the `1ULL << ssm_id` overflow (§6) —
   without it the affected stages are silent.
3. **SSS expansion** (§7) — until then a custom stage is not selectable.
4. **ACE sizing** (§5, §9): `stage_datas[]` and `s32_arr_803BB6B0` both need 155 rows, and
   `GW_MEX_GR_MAX` / `GR_MEX_ROWS` in the port move with them.
5. `LineTypeData` (§3) is dumped but unused by the port; m-ex's `Line Type References/` patches
   repoint the vanilla 0x50-stride `mpLib_803BDC18`-family table at it.
