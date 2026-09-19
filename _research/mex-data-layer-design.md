# m-ex data layer — design for the native PC port

**Status: research + design only. Nothing here has been built or run.** Written 2026-09-19.

Companion to [`mex-ppc-interpreter.md`](mex-ppc-interpreter.md) (option B: the fighter's PPC
`ftFunction` blob is executed by an interpreter) and
[`mex-content-expansion.md`](mex-content-expansion.md).

Convention used throughout: **VERIFIED** = read in a named file at a named line. **INFERRED** =
my reading of how the pieces fit, not something any single file states.

## 0. Why this document exists

Sonic's interpreted `ftFunction` calls an m-ex runtime API that the port currently stubs
(`C:/gdm/melee/pc/platform/gw_mex_ftfunction_runtime.c`):

| shim | line | behaviour today |
|---|---|---|
| `gw_mex_shim_index_item` (`MEX_IndexFighterItem`) | 105-116 | logged no-op, returns 0 |
| `gw_mex_shim_get_data` (`MEX_GetData`) | 118-132 | returns one zeroed 0x1000 buffer for id 8, else 0 |
| `gw_mex_shim_get_ft_item_id` (`MEX_GetFtItemID`) | 134-153 | returns 0 always |
| `gw_mex_shim_gxlink_clear` (`HSD_GObjGXLink_8039084C`) | 155-159 | logged no-op |
| `gw_mex_shim_setup_gxlink` (`GObj_SetupGXLink`) | 161-172 | logged no-op |
| `gw_mex_shim_setup_proc` (`HSD_GObj_SetupProc`) | 174-184 | logged no-op |

The guest addresses they are hooked at are declared at `gw_mex_ftfunction_runtime.c:59-65`.
**VERIFIED**: the three m-ex-only addresses match m-ex's own linker script —
`C:/gdm/_build/m-ex/MexTK/links/melee.link:1176` (`803D7058:MEX_IndexFighterItem`), `:1184`
(`803D7088:MEX_GetFtItemID`), `:1186` (`803D7094:MEX_GetData`). So the port's hook *points* are
correct; only the bodies are missing.

Consequence (`C:/gdm/docs/HANDOFF.md:86-89`, gap 2): neutral-B walks an m-ex fighter-item list that
was never built, `MEX_GetFtItemID` answers 0 forever, and the guest search never terminates.

---

## 1. The `mexData` layout

### 1.1 Three different things are all called "mexData" — do not conflate them

This is the biggest source of confusion in the existing port notes, so it is stated first.

1. **The rtoc slot block.** m-ex reserves a run of **rtoc-relative word slots** named `OFST_*`.
   Each slot holds *one pointer* (or one count). Patched vanilla code reaches a table with a single
   `lwz rX, OFST_Foo(rtoc)`. **VERIFIED** in `C:/gdm/_build/m-ex/asm/m-ex/Header.s:350-464` (the
   `.set OFST_…, 0x…` block) and at the use sites, e.g.
   `.../asm/m-ex/Fighter Costume Pointers/FetchCostumePointer.asm:5`
   (`lwz r0,OFST_Char_CostumeRuntimePointers(rtoc)`),
   `.../asm/m-ex/Fighter PlXXSymbols/fileLoad_PlXX - Load Pointer.asm:5`
   (`lwz r0,OFST_ftDataPointers(rtoc)`),
   `.../asm/m-ex/Item Extension/Create Item.asm:12` (`lwz r4,OFST_ItemsAdded(rtoc)`).
   The writer side is `.../asm/m-ex/Main.s` (e.g. `:185`
   `stw r3,OFST_Char_CostumeRuntimePointers(rtoc)`).

2. **The `MexData` struct** — the root object of m-ex's metadata, reached by
   `MEX_GetData(MXDT_MEXDATA)`. **VERIFIED** as a C declaration in
   `C:/gdm/_build/m-ex/MexTK/include/mxdt.h:246-320`. `Header.s:449` defines `OFST_mexData` as
   *one of the rtoc slots*, i.e. the rtoc block contains a pointer to this struct. They are nested,
   not alternatives.

3. **`Arch_FighterFunc`** — the 46-slot array of per-kind override tables that the `ftFunction`
   `Overload` step writes into (`mex-ppc-interpreter.md:28-32`). The port's
   `GW_MEX_MEXDATA_SIZE` region (`gw_mex_ftfunction_runtime.c:70`) is **this**, not (1) or (2).
   Calling it `mexData` in the port is a mis-naming that should be fixed when this design lands;
   it is what the interpreter's r2 currently points at, which is wrong (see §1.5).

### 1.2 The rtoc slot block (`OFST_*`)

**VERIFIED**, `C:/gdm/_build/m-ex/asm/m-ex/Header.s:350-464`. Offsets are byte offsets *from r2*,
one word each, starting at `0x00` and running contiguously. The ordered list, with the m-ex name
and (my paraphrase of) what the slot points at:

| off | slot | holds |
|---|---|---|
| 0x00 | `MnSlChrIconData` | CSS icon descriptor table |
| 0x04 | `MnSlChrNames` | `char*` array of fighter names |
| 0x08 | `MnSlChrDefineIDs` | external→internal id map |
| 0x0C | `MnSlChrCostumeFileSymbols` | per-character costume symbol tables |
| 0x10 | `MnSlChrCharFileNames` | per-character `PlXX.dat` names |
| 0x14 | `MnSlChrAnimFileNames` | per-character `PlXXAJ.dat` names |
| 0x18 | `MnSlChrEffectFileIDs` | per-character effect file id |
| 0x1C | `MnSlChrEffectFilesSymbols` | effect archive symbols |
| 0x20 | `MnSlChrSSMFileIDs` | per-character soundbank id |
| 0x24 | `MnSlChrSSMFileNames` | soundbank file names |
| 0x28 | `MnSlChrAnimCount` | per-character animation count |
| 0x2C | `FighterMoveLogic` | per-kind `FtState*` (MotionState table) pointer array |
| 0x30 | `FighterOnLoad` | per-kind onLoad fn-ptr array |
| 0x34 | `FighterOnSpawn` | per-kind fn-ptr array |
| 0x38–0x54 | `FighterSpecialLw/LwAir/S/SAir/N/NAir/Hi/HiAir` | the 8 per-kind special fn-ptr arrays |
| 0x58 | `MnSlChrCostumeIDs` | per-character costume count/colour info |
| **0x5C** | **`Char_CostumeRuntimePointers`** | per-character `MexCostumeRuntimeDesc` |
| 0x60–0x68 | `SSMStruct`, `SSMIDDef`, `SSMBankSizes` | audio |
| 0x6C–0x74 | `GmRstAnimFileNames`, `GmRstInsigniaIDs`, `GmRstScale` | results screen |
| 0x78 | `FtDemoSymbols` | per-character demo/result anim symbols |
| 0x7C | `SFXNameDef` | sfx name definitions |
| 0x80 | `GmRstVictoryTheme` | per-character victory theme |
| 0x84 | `effBehaviorTable` | per-fighter effect behaviour table |
| **0x88** | **`ItemsAdded`** | the custom-item registry (see §2) |
| 0x8C | `ItemIndex` | marked `#unused` in `Header.s:385` |
| 0x90 | `AudioGroups` | |
| 0x94 | `BGMFileNames` | |
| **0x98** | **`ftDataPointers`** | per-kind loaded `PlXX.dat` archive/ftData pointers |
| 0x9C–0xAC | `onFloat`, `onDoubleJump`, `onZair`, `onLanding`, `onWallJump` | the Category-2 per-kind tables |
| 0xB0 | `GmRstPointers` | |
| 0xB4–0xBC | `onFSmash`, `onUSmash`, `onDSmash` | per-kind smash tables |
| 0xC0–0xC8 | `FighterOnItemPickup`, `…Pickup2`, `…ItemRelease` | per-kind item hooks |
| 0xCC… | `FighterBGM`, `FighterViWaitFileNames`, `MajorScenes`, `MinorScenes` | chained `+0x4` defs |
| … | `PtclRuntime1/3/TexGrNum/TexGrData/4/PtclLast/PtclData` | particle runtime |
| … | `XFunctionLookup` | the `MEXFunctionLookup` (`mxdt.h:118-122`) |
| … | `Menu_Param`, `Menu_SSS`, `Map_StageIDs`, `Map_Audio`, `grFunction`, `LineTypeData` | menu/stage |
| … | `KirbyHat*`, `KirbyAbility*`, `KirbyFtCmdRuntime`, `KirbyOnAbility*`, `KirbySpecial*`, `KirbyOnHit`, `KirbyInitItem`, `KirbyMoveLogicRuntime` | Kirby copy-ability |
| … | `Metadata_FtIntNum`, `…FtExtNum`, `…CSSIconCount`, `…SSSIconCount`, `…SSMCount`, `…BGMCount`, `…EffectCount`, `MetaData_TermMajor`, `…TermMinor`, `…GrIntNum`, `…GrExtNum`, `Metadata` | the scalar counts that replace vanilla's hardcoded limits |
| … | **`mexData`** | pointer to the `MexData` struct of §1.3 |
| … | `EasterEgg` (note: `+0x8` to the next slot), `HeapRuntime`, `ClassicTrophyLookup`, `AdventureTrophyLookup`, `AllStarTrophyLookup`, `TrophyFallScale`, `MetaData_TrophyCount`, `MetaData_TrophySDOff`, `MexPatch` | tail |

Two cautions, both **VERIFIED**:

- **The tail offsets are chained, not literal.** From `Header.s:401` onward the `.set`s are written
  as `OFST_X, OFST_Prev + 0x4`, with one deliberate `+0x8` gap after `OFST_EasterEgg`
  (`Header.s:452-453`). A port must *compute* the tail, not transcribe guessed numbers. The
  reliable way to get exact tail values is to re-derive the chain mechanically from `Header.s`
  (a ~30-line Python pass) and emit a generated C header — not to hand-copy.
- **`OFST_*` names are re-defined, and part of the block is negative.** `Header.s:16-17` define
  `OFST_mexMapData`/`OFST_mexSelectChr` as *negative* rtoc offsets (`-0x4A08`, `-0x4A0C`), and
  `:62-66` redefine `OFST_mexSelectChr` to `-0x472C` and add `OFST_stc_icons` / `OFST_mexMenu`
  around `-0x4720`, carrying m-ex's own `# TODO: THIS WILL BREAK STUFF` comments. So the slot block
  is **two disjoint ranges**: a small negative range that squats on real vanilla rtoc globals, and
  the positive `0x00…~0x130` range that is m-ex's own. A port that allocates only a positive-side
  region will fault (or silently read the wrong thing) on any blob that touches the negative side.

### 1.3 The `MexData` struct

**VERIFIED**, `C:/gdm/_build/m-ex/MexTK/include/mxdt.h:246-320`. Field order, all one-word
pointers: `metadata`, `menu`, `fighter`, `fighter_function`, `ssm`, `music`, `effect`, `item`,
`kirby_data`, `kirby_function`, `stage`, `stage_desc`, `scene`, `misc`.

- `metadata` → `MexMetaData` (`mxdt.h:139-158`): a version byte pair, flags, then the counts
  (`internal_id_count`, `external_id_count`, `css_icon_count`, `internal_stage_count`,
  `external_stage_count`, `sss_icon_count`, `ssm_count`, `bgm_count`, `effect_count`,
  `bootup_scene`, `last_major`, `last_minor`, `trophy_count`, `trophy_sd_offset`). This is the
  struct that makes m-ex's content limits data rather than constants.
- `fighter` → an anonymous struct of ~35 parallel **arrays indexed by internal fighter kind**
  (`mxdt.h:250-307`): `names`, `pl_file{name,symbol}`, `insignia_idx`, `ft_kind_desc`,
  `costume_info`, `costume_file`, `ftdemo`, `anim_filenames`, `anim_num`, `effect_index`,
  `result_file`, `result_scale`, `victory_theme`, `announcer_call`, `ssm_files`,
  **`costume_pointers`**, `ft_archives`, `walljump`, `rst_runtime`, **`item_lookup`**,
  `target_test_lookup`, `fighter_music`, `vi_files`, four ending-file arrays, `race_to_finish`,
  `demo_params`, three trophy-id arrays, `ending_fall_scale`. m-ex's own comment (`mxdt.h:274`)
  admits the list is incomplete ("theres more im just lazy") — **this is a real gap**, see §5.
- `fighter_function` → per-kind **arrays of function pointers** (`mxdt.h:308-322`): `OnLoad`,
  `OnDeath`, `OnUnk`, `move_logic` (`FtState**`), then
  `SpecialN/NAir/S/SAir/Hi/HiAir/Lw/LwAir`, then "and various more". **INFERRED**: this is the same
  content as the `OFST_Fighter*` rtoc slots — the rtoc slots are a flattened, one-load view of
  `MexData.fighter_function`, and the two must be kept consistent by construction (build one, point
  the other at it) rather than maintained twice.
- `item` → the custom-item table (§2). `stage`, `scene`, `kirby_*`, `music`, `effect`, `misc` are
  not on Sonic's path.

### 1.4 What `MEX_GetData(id)` actually is

**VERIFIED**: the id space is `enum MEX_GETDATA` (`mxdt.h:12-33`), in declaration order:
`MXDT_FTINTNUM`(0), `MXDT_FTEXTNUM`(1), `MXDT_FTICONNUM`(2), `MXDT_FTICONDATA`(3),
`MXDT_GRINTNUM`(4), `MXDT_GREXTNUM`(5), `MXDT_GRICONNUM`(6), `MXDT_GRICONDATA`(7),
**`MXDT_FTCOSTUMEARCHIVE`(8)**, `MXDT_GRDESC`(9), `MXDT_GREXTLOOKUP`(10), `MXDT_GRNAME`(11),
`MXDT_FTNAME`(12), `MXDT_FTDAT`(13), `MXDT_FTKINDDESC`(14), `MXDT_FTEMBLEMLOOKUP`(15),
`MXDT_MEXDATA`(16), `MXDT_PRELOADHEAP`(17), `MXPT_FILE`(18).

The id the port's shim special-cases is **8**, which is `MXDT_FTCOSTUMEARCHIVE`, **not**
`OFST_Char_CostumeRuntimePointers` as `gw_mex_ftfunction_runtime.c:128` claims. The comment there
is wrong; the *effect* (hand back a costume-related pointer) is right by accident. Fix the comment.

`MEX_GetData` is a **pure switch over an id that returns a pointer or a scalar count** — mostly by
reading one rtoc slot, sometimes by returning a count out of `MexMetaData`. It never allocates.
m-ex's implementation is `.../asm/m-ex/Standalone Functions/Get MxDt Data.asm`; its error string at
`:138` (`"error: MEX_GetData() does not have data for id %d\n"`) confirms the contract: an unknown
id is a hard error, not a silent 0.

**Therefore the port's shim returning 0 for every id but 8 is not a conservative stub.** m-ex
guarantees a valid pointer for every defined id, so guest code is entitled to dereference the
result without a null check. Any blob path that calls `MEX_GetData` with an id other than 8 will
fault or loop. This is a second latent bug class beyond the known neutral-B loop.

### 1.5 Proposed C layout for the port

The design goal is: **one native owner, one guest mirror.** Native C holds the real tables (so the
port's own C can use them); a guest-memory mirror exists only so interpreted rtoc-relative loads
resolve, and holds *guest addresses* of those tables.

```c
/* gw_mex_data.h  (new)  — all offsets generated from Header.s, never hand-typed */
#define GW_MEX_RTOC_NEG_SIZE 0x4A10u   /* covers OFST_mexMapData .. OFST_mexSelectChr */
#define GW_MEX_RTOC_POS_SIZE 0x0200u   /* covers 0x00 .. OFST_MexPatch, rounded up  */

typedef struct gw_mex_rtoc {           /* the guest-memory image; r2 points at `pos` */
    uint8_t  neg[GW_MEX_RTOC_NEG_SIZE];   /* r2 - GW_MEX_RTOC_NEG_SIZE .. r2 */
    uint32_t pos[GW_MEX_RTOC_POS_SIZE/4]; /* big-endian guest words, index = OFST_x/4 */
} gw_mex_rtoc;
```

Rules the layout must obey:

1. **r2 points at the positive base.** The interpreter must be able to form both `r2 + 0x88` and
   `r2 - 0x472C` within the same allocation, so the allocation starts `GW_MEX_RTOC_NEG_SIZE` bytes
   *before* the value placed in r2. (Today `gw_mex_ftfunction_runtime.c` sets r2 to the
   `Arch_FighterFunc` region — one allocation of `GW_MEX_MEXDATA_SIZE` = 0x2000 with nothing below
   it, so a negative-offset load is out of range. **VERIFIED** at
   `gw_mex_ftfunction_runtime.c:70` and the `r2 = mexData` comment at `:231`.)
2. **Every word in the mirror is a guest address, stored big-endian** (`gw_w32`). Never a native
   pointer: the interpreter will dereference it as guest memory.
3. **The tables the slots point at live in guest memory too**, allocated from the fighter heap the
   same way the code blob is. A native C mirror struct may alias them, but the guest copy is
   authoritative for anything the blob writes.
4. **Offsets are generated.** Add a `tools/mex_port/gen_mexdata_offsets.py` that parses
   `Header.s`'s `.set OFST_*` chain (literal and `PREV + 0x4` forms) and emits
   `gw_mex_ofst.h` as `#define GW_MEX_OFST_ITEMSADDED 0x88u` etc. This is a *derivation of offsets*,
   not vendoring of m-ex content, and it keeps the port honest when m-ex's header moves.
5. **Unpopulated slots must be diagnosable, not zero.** Fill the mirror with a poison guest address
   inside a dedicated read-only guard page rather than 0, so the first blob to read an unbuilt slot
   raises the interpreter's clean bounds panic (naming the guest PC and the slot offset) instead of
   silently reading NULL. This directly converts the current class of hangs into a named failure.

### 1.6 What Sonic's blob actually reads — **ZERO rtoc slots**

**VERIFIED by static analysis of the shipped blob.** I extracted `PlSn.dat` from
`C:\iso\Akaneia.iso` (read-only; GCM FST walk), parsed its HSD archive
(`filesize 0x41696, datasize 0x3D8FC, 3920 relocs, 3 publics: ftDataSonic 0x2FA90,
ftFunction 0x3BB70, itFunction 0x3D648`), took the `ftFunction` code
(`code 0x23E0, codeSize 0x5778`, matching `mex-ppc-interpreter.md:150-156`), applied the
instruction relocations, and histogrammed the `rA` field of every D-form load/store/`addi`:

```
rA histogram: {r0:610, r1:1319, r3:136, r4:8, r6:2, r7:5, r8:6, r9:356, r10:51,
               r25:2, r26:6, r27:3, r28:18, r29:42, r30:139, r31:444}
```

**There is no `rA == 2` and no `rA == 13` anywhere in Sonic's blob.** The blob never performs an
rtoc-relative or SDA-relative access. It reaches every piece of m-ex data through **`MEX_GetData`
calls** instead (two call sites, see below).

Consequences, and they are large:

- **Setting r2 is not on Sonic's critical path at all.** Phase-3 item 6 in
  `mex-ppc-interpreter.md:179` ("set r2 = guest mexData base so rtoc-relative `OFST_*` loads hit
  guest memory") is a **no-op for this fighter**. The whole `OFST_*` slot block of §1.2 is
  m-ex's *engine-patch* surface (the 1169 `.asm` patches), not its *content* surface. A ported
  fighter blob compiled by MexTK talks to the runtime through function calls only.
- The `OFST_*` design in §1.5 is therefore **not a prerequisite** for Sonic. Keep it as the record
  of what the rtoc block is, but do not build it first. (It becomes relevant only if some other
  content blob is found to use r2 — re-run the histogram above per blob; it is a 20-line script.)
- The port's r2 currently points at the `Arch_FighterFunc` region. That is harmless for Sonic, but
  it should be pointed at a poisoned guard address instead, so that the first blob that *does* use
  r2 faults loudly rather than reading override pointers as if they were `OFST_*` slots.

**VERIFIED** — the blob's `functionRelocTable` (25 entries) paired against its own
`MEXDebugSymbol` table (207 entries, at `data+0x3BB90`, which the port's loader does not currently
read) gives the exact override map, and it corrects several slot names guessed in
`gw_mex_ftfunction_runtime.c:40-56`:

| slot | blob symbol | port's current name |
|---|---|---|
| 0 | `OnLoad` | `GW_MEX_SLOT_ON_LOAD` ✔ |
| 1 | `OnRespawn` | (unnamed) |
| 2 | `OnDestroy` | (unnamed) |
| 3 | `move_logic` | `GW_MEX_SLOT_MOVE_LOGIC` ✔ |
| 4-11 | `SpecialN`, `SpecialAirN`, `SpecialS`, `SpecialAirS`, `SpecialHi`, `SpecialAirHi`, `SpecialLw`, `SpecialAirLw` | ✔ but note the **air variant is the odd slot** and the port's `SPECIAL_N_AIR=5` ordering matches |
| 13 | `OnItemPickup` | ✔ |
| 14 | `OnSetItemInvisible` | (unnamed) |
| 15 | `OnSetItemVisible` | (unnamed) |
| 16 | `OnItemRelease` | (unnamed) |
| 17 | `OnItemCatch` | (unnamed) |
| 18 | `OnUnknownItemRelated` | (unnamed) |
| 21 | `EyeTextureDamaged` | (unnamed) |
| 22 | `EyeTextureNormal` | (unnamed) |
| 23 | `OnFrame` | ✔ |
| 24 | `OnActionStateChange` | ✔ |
| 25 | `ResetAttributes` | `ON_REAPPLY_ATTR` ✔ (same thing) |
| 32 | `EnterDoubleJump` | `ON_DOUBLE_JUMP` ✔ |
| 36 | `OnSmashHi` | `ON_USMASH` ✔ |

**Actionable**: the port's loader should read `ftFunction+0x18/+0x1C`
(`debug_symbol_num` / `debug_symbol`, **VERIFIED** present: 207 symbols) and log the real symbol
name for every override and every guest PC. That alone turns future interpreter panics from
addresses into named functions, for free. (`MEXDebugSymbol` is declared at
`C:/gdm/_build/m-ex/MexTK/include/mxdt.h:111-116`; in the shipped blob its second word is the
**end** offset, not a length — `OnLoad` reports `0x124`, which is the next symbol's start.)

### 1.7 `MxDt.dat` already *is* the mexData — do not synthesize it

**VERIFIED.** `MxDt.dat` is on the Akaneia disc (FST entry, 115396 bytes) and is an HSD archive
with **exactly one public symbol, literally named `mexData`**, at data offset `0x98A8`
(`filesize 0x1C2C4, datasize 0x199F4, 2600 relocs, 1 public, 0 externs`). Its 14 root words decode
one-to-one against `MexData` in `mxdt.h:246-320`:

| field | data offset |
|---|---|
| `metadata` | 0x1992C |
| `menu` | 0x199CC |
| `fighter` | 0x0D754 |
| `fighter_function` | 0x15BF8 |
| `ssm` | 0x19408 |
| `music` | 0x098E0 |
| `effect` | 0x174D0 |
| `item` | 0x17D4C |
| `kirby_data` | 0x15CF8 |
| `kirby_function` | 0x17474 |
| `stage` | 0x0AE74 |
| `stage_desc` | 0x0BE0C |
| `scene` | 0x18920 |
| `misc` | 0x17498 |

`metadata` decodes to `v1.1, flags 0`, `internal_id_count 41`, `external_id_count 41`,
`css_icon_count 32`, `internal_stage_count 96`, `external_stage_count 313`, `sss_icon_count 67`,
`ssm_count 78`, `bgm_count 139`, `effect_count 51`, `bootup_scene 2`, `last_major 45`,
`last_minor 45`, `trophy_count 342`, `trophy_sd_offset 351` — the 41/32/96/67 values match the
counts already recorded in `mex-content-expansion.md:56-59` from an independent source, which
cross-validates the field order.

**This changes the whole design.** The port does not need to *build* a mexData layout; it needs to
**load `MxDt.dat` the same way it already loads `PlSn.dat`** (`gw_mex_ftfunction.c` already does
HSD archive + public-symbol extraction + relocation), keep the resulting `mexData` in guest memory,
and have `MEX_GetData(id)` return pointers into it. Everything in §1.3 stops being a struct the
port must author and becomes a read-only view over shipped data.

The one thing the port *must* still author is the handful of **runtime-filled** sub-tables inside
that archive (they ship zeroed): see §2.

`MexData.fighter` was confirmed field-by-field by walking the 33 array pointers at `0xD754`; every
one resolves inside the data section, and the ones the port needs are
`fighter.costume_pointers = 0x14540` and `fighter.item_lookup = 0x14744`.
`MexData.fighter_function` at `0x15BF8` likewise holds the per-kind arrays in `mxdt.h` order
(`OnLoad 0x629C, OnDeath 0x61F8, OnUnk 0x6154, move_logic 0x60B0, SpecialN 0x600C,
SpecialNAir 0x5F68, SpecialS 0x5C34, SpecialSAir 0x5B90, SpecialHi 0x5EC4, SpecialHiAir 0x5E20,
SpecialLw 0x5D7C, SpecialLwAir 0x5CD8`).

### 1.8 The exact contract of `MEX_GetData(8)` — derived from Sonic's own code

**VERIFIED** by disassembling `OnLoad` (blob `+0x84 … +0xBC`):

```
addi r3, 8                     ; MXDT_FTCOSTUMEARCHIVE
bl   MEX_GetData
lwz  r9, 4(r31)                ; r31 = fp (FighterData), +4 = fp->kind
rlwinm r9, r9, 3, 0, 28        ; kind * 8
lbz  r10, 0x619(r31)           ; fp->costume_id
lwzx r9, r3, r9                ; base[kind].runtimes        <-- 8-byte stride
mulli r10, r10, 24             ; costume_id * 0x18
add  r9, r9, r10
lwz  r3, 0x14(r9)              ; runtimes[costume_id].archive
cmpwi r3, 0 ; beq skip
```

So `MEX_GetData(MXDT_FTCOSTUMEARCHIVE)` returns **`MexCostumeRuntimeDesc *` indexed by internal
fighter kind** — 8-byte stride `{ MexCostumeRuntime *runtimes; int count; }`, with
`MexCostumeRuntime` at 0x18 bytes and its `HSD_Archive *archive` at `+0x14`. That matches
`mxdt.h:85-100` exactly (`joint_desc, matanim_desc, x08, x0C, x10, archive`). Sonic uses the
archive to `Archive_GetPublicAddress` a symbol and stash the result in his custom FighterData word
`fp+0x2234`.

The port's current synthetic buffer (`gw_mex_ftfunction_runtime.c:550-552`) is shaped correctly for
this access — per-kind slot → zeroed sub-region → `+0x14` reads 0 → branch skips. That is why
onLoad survives today. It is also why Sonic's costume-specific accessory data never loads.


---

## 2. The fighter-item system

### 2.1 What the two functions mean

**VERIFIED** from Sonic's own code plus m-ex's item-creation patch.

`MEX_IndexFighterItem(int fighter_kind, ItemDesc *desc, int item_id)` — declared
`mxdt.h:363`. Sonic calls it exactly **once**, at the top of `OnLoad` (blob `+0x38 … +0x4C`):

```
lwz  r9, 0x10C(r31)   ; fp->ft_data
lwz  r9, 0x48(r9)     ; ftData->x48_items   (the article/ItemDesc array)
addi r5, r0, 0        ; item_id = 0
lwz  r4, 0(r9)        ; &items[0]
lwz  r3, 4(r31)       ; fp->kind
bl   MEX_IndexFighterItem
```

`ftData.x48_items` is **VERIFIED** in the decomp at `C:/gdm/melee/src/melee/ft/types.h:655`
(`/* +48 */ UNK_T* x48_items;`). So: *"register this fighter's article #N with the global item
system."*

`MEX_GetFtItemID(GOBJ *fighter_gobj, int item_id)` — declared `mxdt.h:366`. Sonic calls it exactly
**once**, inside `Spawn_Spring` (blob `+0x4B2C`), and feeds the result straight into the spawn
descriptor that goes to the vanilla `Item_CreateItem` (`0x8026862C`):

```
stw  r30, 8(r1)  ; spawn.parent_gobj
stw  r30, 12(r1) ; spawn.owner_gobj
addi r4, r0, 0   ; item_id = 0
or   r3, r30     ; the fighter gobj
bl   MEX_GetFtItemID
stw  r3, 16(r1)  ; spawn.kind  <-- the GLOBAL ItemKind
...
addi r3, r1, 8
bl   Item_CreateItem
```

So: *"translate (this fighter, article #N) into the global `ItemKind` that was assigned at
registration time."* Returning 0 (today's shim) makes Sonic spawn global item kind 0 instead of his
spring — a silently wrong item, not a crash.

### 2.2 The tables they index — all three are in `MxDt.dat`

**VERIFIED** by decoding `MxDt.dat`.

**(a) `MexData.fighter.item_lookup` (data offset `0x14744`, 400 bytes).** An array indexed by
**internal fighter kind**, stride 8, of `{ s32 count; u16 *global_item_kinds; }`. Only the custom
fighters have entries; everything below index 27 is zeroed (vanilla articles stay hardcoded). The
populated entries are:

| kind | count | id array | ids |
|---|---|---|---|
| 27 | 4 | 0x1488C | 253, 254, 255, 256 |
| 28 | 5 | 0x14894 | 257 … 261 |
| 29 | 4 | 0x148A0 | 262 … 265 |
| 30 | 11 | 0x148A8 | 266 … 276 |
| **31** | **1** | **0x148C0** | **277** |
| 32 | 6 | 0x148C4 | 278 … 283 |
| 33 | 2 | 0x148D0 | 284, 285 |

The seven `u16*` fields at `0x14820/28/30/38/40/48/50` are the only relocations in that range, which
confirms the `{count, ptr}` stride-8 reading.

**Kind 31 is Sonic** (`GW_MEX_INTERNAL_SONIC 31`, `gw_mex_ftfunction_runtime.c:35`), he has
**exactly one** article, and its global `ItemKind` is **277 (0x115)**. That is exactly consistent
with his `OnLoad` registering one article with `item_id = 0`. So:

> `MEX_GetFtItemID(gobj, n)` == `mexData->fighter->item_lookup[fp->kind].ids[n]`,
> and for Sonic the only correct answer is `MEX_GetFtItemID(sonic, 0) == 277`.

**(b) `MexData.item` (data offset `0x17D4C`).** Six words, matching m-ex's `Arch_ItemsAdded`
(`Header.s:300-306`): `Common`, `Fighter`, `Pokemon`, `Stages`, `Custom`, `RuntimeIndex`. The
shipped values are `0x803F14C4`, `0x803F3100`, `0x803F23CC`, `0x803F4D20` (the four **vanilla**
item function tables, as absolute game addresses), then `Custom = 0x17D64` and
`RuntimeIndex = 0x364C`, both in-file. **Both in-file tables ship all-zero and carry no
relocations — they are runtime-filled.**

**(c) How the global kind is consumed.** **VERIFIED** in
`C:/gdm/_build/m-ex/asm/m-ex/Item Extension/Create Item.asm` (patch site `@0x80267990`, i.e. inside
item creation). m-ex replaces the vanilla "which table does this item id belong to" decision with a
range split, all driven off `OFST_ItemsAdded(rtoc)`:

| id range | function table | descriptor table |
|---|---|---|
| `< 43` | `item.Common` | vanilla `r13-0x497C` |
| `43 … 160` | `item.Fighter` (id−43) | vanilla `r13-0x4968` |
| `161 … 207` | `item.Pokemon` (id−161) | vanilla `r13-0x4970` |
| `208 … 236` | `item.Stages` (id−208) | vanilla `0x804A0F60` |
| `>= 237` (`CustomItemStart`, `Header.s:14`) | `item.Custom` (id−237) | **`item.RuntimeIndex` (id−237)** |

Function-table stride is `0x3C`; descriptor-table stride is 4. The patch then writes the function
pointer to `ItemGObjData+0xB8` and the descriptor to `+0xC4`. If the `RuntimeIndex` slot is NULL it
**asserts** ("ItemNotInitialized" → `OSReport` + assert). That is the hard contract:
*every global item kind ≥ 237 that is ever spawned must have had its slot filled first.*

### 2.3 What `MEX_IndexFighterItem` must therefore do

**INFERRED** (this is a reconstruction, not a line I read — m-ex's implementation of the function
itself is one of the "standalone functions" stored as raw code in the repurposed
`gmResultCharacterData` blob, `mex-content-expansion.md:96-98`, so there is no source to read):

```
void MEX_IndexFighterItem(int fighter_kind, ItemDesc *desc, int item_id)
{
    FtItemLookup *e = &mexData->fighter->item_lookup[fighter_kind];
    if (item_id >= e->count) return;          /* or assert */
    int global = e->ids[item_id];             /* 277 for Sonic article 0 */
    mexData->item->RuntimeIndex[global - CUSTOM_ITEM_START] = desc;
    /* and, if not already static, item->Custom[global-237] gets the item's state/function table */
}
```

Two things support this shape and nothing contradicts it: `RuntimeIndex` ships zeroed with no
relocations (so somebody fills it at runtime), and the only runtime call that has an `ItemDesc` in
hand is `MEX_IndexFighterItem`. What I could **not** determine is whether the same call also
populates `item.Custom` (the 0x3C-stride function table) or whether that is derived from the
`ItemDesc` at creation time — see §5.

### 2.4 When the port must build it

Ordering, **INFERRED** but tightly constrained by the code above:

1. **Once per boot**, after `MxDt.dat` is loaded: nothing — `item_lookup` and the id arrays are
   static file data and are already correct.
2. **Once per fighter load**, from the *fighter's own* `OnLoad` — which already happens, because
   Sonic's `OnLoad` makes the call. The port's job is only to make the shim do real work. The
   `RuntimeIndex` slot must be filled **before** the first `Item_CreateItem` for that kind, and
   `OnLoad` runs long before any special, so the existing ordering is sufficient.
3. **`MEX_GetFtItemID` needs no build step at all** — it is a pure lookup into static file data.
   It can be made correct *immediately*, independently of everything else in this document.

That last point is the highest-value single change available: three table dereferences, no new
allocation, no new lifetime.

### 2.5 The neutral-B crash is **not** an item-table bug — root cause located

`HANDOFF.md:86-89` attributes the neutral-B failure to "the m-ex item system / `mexData` item
tables are not built". **That attribution is wrong.** The faulting code contains no m-ex call at
all.

**VERIFIED** by disassembling `SpecialN_SearchTarget_EnterAttack` (blob `+0x33E0 … +0x35B4`, name
from the blob's own debug symbols). It is the homing-attack target search and it has two loops:

*Loop 1* — players 0..5 via `Fighter_GetGObj` (`0x80034110`), skipping self and same-team
(`Fighter_CheckSameTeam`), then a squared-distance test against `Vec3_DistSquared`.

*Loop 2* — the item list:

```
34c4: lis  r9, 0x804D ; ori r9, 0x782C
34cc: lwz  r9, 0(r9)        ; r9 = HSD_GObjPLinkHead   (the ARRAY pointer)
34d0: lwz  r31, 0x24(r9)    ; r31 = HSD_GObjPLinkHead[9]  == HSD_GOBJ_PLINK_ITEM
34d4: cmpwi r31, 0 ; beq done
34e8: lwz  r31, 8(r31)      ; gobj = gobj->next
34ec: cmpwi r31, 0 ; beq done
34f4: lwz  r30, 0x2C(r31)   ; item = gobj->user_data
34f8: lwz  r9,  0x10(r30)   ; item->kind            <-- FAULTS when user_data == NULL
34fc: cmpwi r9, 209 ; bne next
```

- `0x804D782C` is **`HSD_GObjPLinkHead`** — **VERIFIED**,
  `C:/gdm/melee/config/GALE01/symbols.txt:29538` (`.sbss`, size 4), declared
  `HSD_GObj** HSD_GObjPLinkHead;` at `C:/gdm/melee/src/sysdolphin/baselib/gobj.h:73`. Index
  `0x24/4 = 9` is `HSD_GOBJ_PLINK_ITEM` (`C:/gdm/melee/src/melee/it/forward.h:8`).
- `gobj->next` at `+8` and `gobj->user_data` at `+0x2C` are **VERIFIED** in `gobj.h:14-33`.
- `Item.kind` at `+0x10` is **VERIFIED** in `C:/gdm/melee/src/melee/it/types.h:213-226`.
- `209 == 0xD1 == It_Kind_Mato` — the **Target Test target** (`it/forward.h`, the MONSTERS 2 block:
  `0xD0 It_Kind_Old_Kuri`, then `It_Kind_Mato`). So the homing attack homes onto Target-Test
  targets as well as onto players — which is precisely why this fires under `MELEE_TARGET_TEST=32`.

The reported fault `ea = 0x00000010` is **exactly** instruction `34f8: lwz r9, 0x10(r30)` with
`r30 == 0`. That is a definitive match, not a guess.

So the real question is *"why does a gobj on the port's `HSD_GObjPLinkHead[9]` list have a NULL
`user_data`, or why is that list malformed/cyclic?"*, and the suspects are, in order:

1. **The static-global bridge.** `HSD_GObjPLinkHead` is a native `.sbss` word (commit `108fa831e`
   bridges static-global reads). The blob does a *double* indirection: read the native word, then
   dereference `+0x24` **as guest memory**. If the bridge returns the correct value but the array it
   points at is not reachable at that guest address, `r31` is garbage and the walk is unbounded —
   which is the "infinite loop" symptom; if it is partly right, it is the NULL-`user_data` symptom.
   **This single read is the thing to instrument first.**
2. A genuinely NULL `user_data` on an item gobj mid-construction, which would also affect vanilla.
3. The list being walked before item creation completes.

**Do not null-guard the guest code** (the handoff already says this). Instrument the two loads at
`34CC`/`34D0` and compare the resulting `r31` against what native C sees for
`HSD_GObjPLinkHead[HSD_GOBJ_PLINK_ITEM]` at the same frame. If they differ, it is (1).

---

## 3. The render-context tables

### 3.1 The hypothesis in the brief is refuted for Sonic

The brief (and `HANDOFF.md:90-91`) says the guest render/proc callbacks "hang the render loop
without m-ex's render-context tables". **VERIFIED: there are no such tables in play.** Sonic's
`OnLoad` installs exactly three guest callbacks, and I disassembled all of the relevant bodies:

| call in OnLoad | guest fn | blob symbol | reads any m-ex data? |
|---|---|---|---|
| `GObj_DestroyGXLink(gobj)` (`0x8039084C`) | — | — | n/a |
| `GObj_AddGXLink(gobj, cb, 5, 0)` (`0x8039069C`) | `code+0xBDC` | `GXLink_Sonic` | **no** |
| `GObj_AddProc(gobj, cb, 15)` (`0x8038FD54`) | `code+0xC74` | `ProcessMouth` | **no** |
| `GObj_AddProc(gobj, cb, 9)` (results-screen path only) | `code+0xD58` | `Sonic_CheckWinAudio` | **no** |

(The port's names `GObj_SetupGXLink` / `HSD_GObj_SetupProc` in
`gw_mex_ftfunction_runtime.c:63-64` are aliases for the same guest addresses; the m-ex link map
calls them `GObj_AddGXLink` / `GObj_AddProc`. The `cb=guest 0x80000BDC` / `0x80000C74` in the
existing log lines are `GXLink_Sonic` and `ProcessMouth` — now confirmed by name.)

`GXLink_Sonic` (blob `+0xBDC … +0xC64`):

```
bl   GXLink_Fighter (0x80080E18)     ; vanilla per-pass fighter render
cmpwi r30, 2 ; bne return            ; r30 = the pass/gx_link argument
lbz  r9, 0x21FC(r29) ; andi. 2       ; a custom FighterData flag bit
lwz  r9, 0x10(r29) ; cmpwi 343       ; fp->motion_id == 0x157
   -> GXLink_SonicDrawRadius (code+0x3130)
lwz  r9, 0x10(r29) ; cmpwi 345       ; fp->motion_id == 0x159
   -> GXLink_SonicDrawTarget (code+0x2FD8)
```

`ProcessMouth` (blob `+0xC74 … +0xD58`) only touches `FighterData` words
(`+0x197C`, `+0x1980` — two model gobjs; `+0x5F5`, `+0x5F8/F9/FB` — mouth/eye texture indices) and
a JObj flag byte at `+0xDAA`. No table, no m-ex call.

### 3.2 So the blocker is purely the incoming-call problem

`GObj_AddGXLink` stores the callback into `HSD_GObj.render_cb` (`gobj.h:29`, `/* +1C */
GObj_RenderFunc render_cb`) and `GObj_AddProc` stores it in an `HSD_GObjProc`. In the port both of
those are **native** structures read by a **native** render/proc loop, which would call
`0x80000BDC` as an x86 function pointer. That is the hang/crash — not missing data.

The fix is a **native trampoline**, and it is small:

```c
/* one trampoline per (gobj, guest_cb) pair, allocated from a small fixed pool */
typedef struct { uint32_t guest_cb; } gw_mex_cb;
static void gw_mex_render_tramp(HSD_GObj *gobj, int pass) {
    gw_ppc_call(guest_cb_for(gobj, RENDER), (uint32_t)(uintptr_t)gobj, (uint32_t)pass);
}
```

Requirements, each of which the existing runtime already has a piece of:

1. **Reentrancy** — the trampoline runs inside the native render loop and the guest will call back
   out to `GXLink_Fighter`. `gw_ppc_call` is already reentrant and now nests correctly on the guest
   stack (`HANDOFF.md:74-83`).
2. **Re-entry guard** — `GXLink_Sonic` calls `GXLink_Fighter`, which is *not* the function that
   dispatched it, so the `gw_Mex_GObjDispatch` same-hook-on-stack rule does not apply and must not
   be extended to block it.
3. **Lifetime** — the trampoline must be torn down when the gobj dies; `GObj_DestroyGXLink` is
   already on the shim list (`GW_MEX_GUEST_GXLINK_CLEAR`) and is the natural place.
4. **The `pass` argument matters** — `GXLink_Sonic` returns immediately unless `pass == 2`, so the
   trampoline must forward the second argument, not just the gobj.
5. A proc callback takes **only** the gobj (`ProcessMouth` uses `r3` alone) and returns void.

There is **no dependency on mexData at all** for this workstream.

---

## 4. Dependency order

**The hypothesis in the brief — "mexData layout is a shared prerequisite for the other two" — is
REFUTED.** The three workstreams are independent, and the cheapest one is also the one that
unblocks the reported bug.

Recommended order:

1. **`MEX_GetFtItemID` (§2.2).** Load `MxDt.dat`, keep `mexData` in guest memory, implement the
   lookup `item_lookup[kind].ids[n]`. Pure data, no allocation, no lifetime, testable offline
   (assert `MEX_GetFtItemID(sonic, 0) == 277`). Unblocks the spring actually spawning.
   *Prerequisite: the `MxDt.dat` load only. Not the `OFST_*` block.*
2. **`MEX_IndexFighterItem` (§2.3)** — needs (1)'s `MxDt.dat` load and nothing else. Fills
   `item.RuntimeIndex` so `Item_CreateItem` for kind 277 finds a descriptor instead of asserting.
3. **`MEX_GetData` as a real switch (§1.4, §1.8)** — needs (1)'s load; turns the synthetic buffer
   into real pointers, which is what makes Sonic's costume accessories load. Also make unknown ids
   a loud panic, matching m-ex's own behaviour.
4. **The render/proc trampolines (§3)** — completely independent of 1-3; can proceed in parallel
   by a different person. Needs nothing from mexData.
5. **The neutral-B list walk (§2.5)** — independent of all of the above; it is a static-global
   bridge question, and should be instrumented first because it may be a one-line fix and it is
   currently mis-attributed in the handoff.
6. **The `OFST_*` rtoc block (§1.2, §1.5)** — **do this last, or not at all.** Sonic's blob never
   uses r2 (§1.6). Build it only when a content blob is measured to need it.

The one genuinely shared prerequisite is small and concrete: **an `MxDt.dat` loader** that parses
the archive, relocates it into guest memory, and exposes the `mexData` guest address. Everything in
§1.3/§1.7/§2 hangs off that single step; nothing else is shared.

---

## 5. Open questions and gaps

Stated plainly, with what would settle each.

1. **`item.Custom` (the 0x3C-stride function table) — who fills it?** It ships zeroed with no
   relocations, exactly like `RuntimeIndex`, but `Create Item.asm` reads both. Either
   `MEX_IndexFighterItem` fills both, or something else does. *Settle it by:* dumping a live
   `mexData->item` from a running Akaneia build after a Sonic match starts, or by disassembling
   m-ex's `MEX_IndexFighterItem` out of the DOL at `0x803D7058` (it is raw code in the repurposed
   `gmResultCharacterData` region; I did not disassemble it here).
2. **The exact layout of an `ItemDesc`** (what `ftData.x48_items[0]` points at). The decomp calls it
   `UNK_T* x48_items` (`ft/types.h:655`), i.e. it is not typed in the decomp either. Needed before
   `MEX_IndexFighterItem` can do more than store a pointer.
3. **`MexData.fighter`'s field list is incomplete in m-ex's own header** — `mxdt.h:274` says
   "theres more im just lazy" mid-struct. I validated the ordering by checking that all 33 pointers
   at `0xD754` land inside the data section and that `costume_pointers`/`item_lookup` decode
   correctly at the predicted indices, but **an off-by-one in that struct would be silent**.
   *Settle it by:* cross-checking against `Ploaj/MexManager`'s `MxDtCompiler.cs`
   (named in `mex-content-expansion.md:47-49`), which is the writer.
4. **The exact tail offsets of the `OFST_*` chain** (§1.2) — I did not expand the `PREV + 0x4`
   chain numerically. Low priority given §1.6.
5. **Whether the negative-range rtoc slots (`OFST_mexSelectChr` etc.) are ever touched by fighter
   content.** Not by Sonic (no `rA == 2` at all). Unknown for other blobs.
6. **Why the port's `HSD_GObjPLinkHead[9]` walk misbehaves (§2.5).** I located the faulting
   instruction with certainty but cannot distinguish the three candidate causes without running the
   game, which this task forbids.
7. **Whether any *other* m-ex custom fighter uses r2.** The check is a 20-line script (the `rA`
   histogram of §1.6) and should be run over every `Pl??.dat` on the disc before anyone builds the
   `OFST_*` block.
8. **`MEX_GetData` ids other than 8 and 16.** Sonic calls `MEX_GetData` at only two sites — `OnLoad`
   (id 8) and `DidHeLose` (blob `+0x329C`, id not decoded here). Other ids' return shapes are
   inferred from `mxdt.h` and the `MxDt.dat` layout, not observed.

### Reproduction notes

Everything in §1.6-§1.8 and §2.2 was produced offline from two files read out of
`C:\iso\Akaneia.iso` (GCM FST walk, read-only — the ISO was not modified and the game was not
run). No file under `C:\gdm\melee\` was modified. No m-ex `.asm`/`.h`/`.dat` content was copied
into this document; all structure descriptions are paraphrases written to be reimplemented in
original C.

The scripts used (FST extract, HSD archive parse, `ftFunction` reloc, PPC disassembly, `MxDt.dat`
decode) live in the session scratchpad and are ~250 lines total; they are worth re-creating under
`tools/mex_port/` as `dump_ftfunction.py` and `dump_mxdt.py`, because every question in §5 is
answered by re-running them with a different argument.
