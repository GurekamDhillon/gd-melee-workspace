# m-ex content expansion — findings and port plan

Companion to [`mex-port-triage.md`](mex-port-triage.md). Written to be durable: the
evidence behind it came from long agent transcripts and would otherwise be lost.

## 1. The big correction — the patch corpus is 6.5x larger than first believed

m-ex marks each patch's insertion point in a comment header. **Two spellings are in use:**

| Directive | Files |
|---|---:|
| `#To be inserted @ <hex>` | 991 |
| `#To be inserted at <hex>` | 178 |

An earlier pass matched only the word `at` and so silently discarded 85% of the corpus.
With both accepted (`tools/mex_port/resolve_patches.py`), **all 1169 `.asm` files yield an
address** and **1130 (96.7%) resolve to a decomp function**. Under `asm/m-ex/` alone:
**1041 files, 1009 resolved.**

m-ex assembles these with `gecko assemble -p m-ex/ -o codes.gct`; the directive address
becomes the per-file `GTI_FILE_INJECTION_ADDRESS` symbol.

## 2. `MxDb.dat` is a symbol table, not a patch index

`MxDb.dat` (444,957 bytes) is an **HSD DAT archive** with exactly one root, `mexDebug`:

```c
struct MexDebug {        // root "mexDebug"
    u32      SymbolCount;  // 0x00
    Symbol*  Symbols;      // 0x04
};
struct Symbol {          // 0x0C stride
    u32   Start;           // 0x00  absolute DOL address
    u32   End;             // 0x04
    char* Name;            // 0x08
};
```

- **Writer**: `akaneia/MexTK` → `CmdDebugSymbols.cs` (the `-db` command).
- **Reader**: m-ex assembly — `asm/m-ex/xFunction/Output Symbols.asm` loads it and calls
  `File_GetSymbol` (`0x80380358`); `asm/m-ex/xFunction/StackTrace.asm` binary-searches the
  table to name stale-LR frames.
- The shipped table holds ~20,604 symbols; the early entries in the published copy carry
  placeholder names, so it was generated with an incomplete map.

**Conclusion: `MxDb.dat` cannot locate m-ex patches.** It is a symbol database for crash
stack traces. The addresses were never missing — they are in the directives (§1).

## 3. How content expansion actually works

The limit is **not** a constant in m-ex. Patches rewrite hardcoded vanilla comparisons into
runtime metadata reads:

```
lwz  r12, OFST_Metadata_<Field>(rtoc)   # count from the MxDt metadata blob
cmpw r0,  r12
```

So m-ex's slot counts are data, supplied per-build. The authoritative C definitions are in
`akaneia/MexTK/include/mxdt.h`; the build-side generator is `MxDtCompiler.cs` in
`Ploaj/MexManager`. Fields of interest include `NumOfInternalIDs`, `NumOfExternalIDs`,
`NumOfCSSIcons`, `NumOfSSSIcons`, `NumOfInternalStage`, `NumOfExternalStage`.

For scale, the flagship `akaneia/akaneia-build` ships **41 fighters**, **96 stages**,
**32 CSS icons** on the Melee page and **35** on the Akaneia page (**67 SSS icons total**),
**51 major scenes** and **47 minor scene functions**.

`MEXDebugSymbol { uint code_offset; uint code_length; char* symbol; }` (in `mxdt.h`) is a
*different* thing from the global `MxDb.dat` table: it is per-`xFunction` debug info stored
with the code inside `.dat` files.

## 4. Vanilla limits and the decomp structures that hold them

| System | Decomp structure | Vanilla | Source |
|---|---|---|---|
| Characters (internal) | `gFtDataList[Ft_Kind_Max]` | `Ft_Kind_Max = 0x21` (33) | `ft/ftdata.c` |
| CSS icons | `mnCharSel_803F0A48` (CSSIconsData, 0xDC) + `icons[26]` (`CSSIcon`, 0x1C stride) | 26 | `mn/mncharsel.c` |
| SSS icons | `mnStageSel_803F06D0[30]` (29 stages + random) | 30 | `mn/mnstagesel.c` |
| Major scenes | `gm_GetAllGameModes` | table | `gm/gmscdata.c` |
| Minor scenes | `gm_GetAllGameScenes` | table | `gm/gmscdata.c` |
| Scene iteration | `runGameMode` | — | `gm/gm_1A3F.c` |
| Persistent heaps | `lbHeap_803BA380[5]` (4 + terminator) | 5 | `lb/lbheap.c` |
| Items | custom IDs | — | start at 237 in m-ex |
| Effects | custom IDs | vanilla 1211+ | start at 5000 in m-ex |
| Classic save | save-slot logic | limit `0x1A` | `gm/` |

Notable: m-ex's SSS struct stride is `0x20`, not vanilla's `0x1C` — it appends an external
stage ID field at `+0x1C`.

m-ex repurposes `gmResultCharacterData` (`0x803D7058`, a `.data` blob in
`gm/gmresultplayer.c`) as **code storage** for its ~30 "standalone functions". Those are not
hooks into a game function at all; in a native port they become ordinary C functions.

## 5. Portability tiers

**Tier A — portable directly** (constant/table-bound changes, no m-ex runtime):
`Persistent Heap Expansion` (extend the heap table, widen loop bounds), the ID-shift
families that only threshold against counts, `Save Expansion`, `Disable Special Records`,
`qol/Disable Movies`, and the MnSlChrData count/stride patches.

**Tier B — portable as a behaviour, not as a patch** (needs equivalent data plumbing):
CSS/SSS icon tables, scene tables, costume/file-name tables. m-ex points these at `MxDt`
metadata; a port can read the same shape from its own data — which is where `stagec` /
`HSDLib` tooling already points.

**Tier C — not portable in this engine** (depends on executing PPC stored in `.dat`):
anything referencing `OFST_MexData`/`Arch_*`, `xFunction`, `ftFunction`, `grFunction`,
`itFunction`, `mexSelectChr`, `mexMapData`, `mexMenu`, `Reloc`. The port retargets PPC→x86 at
**build** time, so there is no runtime PPC execution — these hooks must be re-expressed as
native C hook points. This is the architectural wall, not a licensing one.

## 6. Port plan

### 6.1 Persistent heap expansion — exact change, and a hazard

m-ex replaces the whole descriptor table. Vanilla vs m-ex:

```c
/* vanilla, lbHeap_803BA380[5] */
{ 2, 1, 6, 0x800 }, { 3, 1, 2, 0x4F8800 }, { 4, 2, 6, 0x64B400 },
{ 5, 4, 6, 0x96C800 }, { 6, 0, 0, 0 },              /* terminator idx 6 */

/* m-ex, terminator idx 7  (PersistHeapNum = 5 + 2) */
{ 2, 1, 6, 0x800 }, { 3, 1, 2, 0x4FA690 }, { 4, 2, 6, 0x64B400 },
{ 5, 4, 6, 0x96C800 }, { 6, 1, 3, 0x20 }, { 7, 0, 0, 0 },
```

m-ex's only structural addition is heap **6** — `{6, 1, 3, 0x20}`, its "CUSTOM scene file
heap", 32 bytes. (`0x64B400` is already `6599680`; m-ex's `FighterHeapReduction` is `000`,
i.e. no-op.) m-ex also raises heap 3 from `0x4F8800` to `0x4FA690`.

Five sites assume 6 and must all move together:

| Site | Change |
|---|---|
| `lbHeap_803BA380[5]` (lbheap.c:21) | add heap 6, terminator → 7 |
| `heap_array[6]` (lbheap.static.h:25) | → 7 |
| `for (; destroy_i < 6; ...)` (lbheap.c:114) | → 7 |
| `for (bounds_i = 2; bounds_i < 6; ...)` (lbheap.c:128) | → 7 |
| `for (create_i = 2; ... create_i < 6; ...)` (lbheap.c:171) | → 7 |
| `for (i = 0; i < 6; i++)` (lbheap.c:256) | → 7 |
| `while ((curr_idx = desc->idx) != 6)` (lbheap.c:299) | → 7 |

The clean shape is a pair of macros (`LBHEAP_HEAP_COUNT` 6/7, `LBHEAP_DESC_COUNT` 5/6) set
under `#if defined(TARGET_PC)`, so the matching build is byte-identical.

**Hazard — do not land this blind.** `lbHeap_80431FA0` is a *fixed-address* global
(`/* 431FA0 */`) carrying `ASSERT_SIZE(struct lbHeap_HeapState, 0xB8)`. Going from 6 heaps to
7 grows it `0xB8 → 0xD4` (0x10 + 7×0x1C):

- the `ASSERT_SIZE` must be made conditional, or the port build fails;
- more seriously, growing the struct **shifts every global laid out after it**. In the
  matching build the layout is pinned by the splits/linker script; on the PC port placement
  is linker-driven, so it may be benign — but it must be *verified*, not assumed, because the
  heap subsystem is memory-critical.

So this item needs an experiment before it is a change: grow the struct, confirm the port
still boots and the smoke test stays clean, then wire a consumer. Without a consumer (a
custom scene file heap has nothing to hold yet) the added heap is inert.

### 6.2 Character ID shifts — identity under vanilla counts

The 93 patches under `asm/m-ex/External Character ID Shifts/` (and the `Internal` siblings) are
the most numerous family, but they **change no behaviour until content is actually added**. Example:
`Adventure Mode Special Fighters.asm` (`@ 0x801B5204`, inside `gm_Mode_Adventure_OnInit`,
`src/melee/gm/gmadventure.c`) rewrites a preload character-ID table:

```
SpecialStart = FtExtNum - 7                              ; 7 specials counted from the top
for ext IDs 0x1A..0x20:  newID = SpecialStart + (extID - 0x1A)
for ext ID >= 0x21:      newID = FtExtNum                ; null
```

It moves the seven special fighters (Master Hand, Crazy Hand, Giga Bowser, Sandbag, Popo, wire
male, wire female) to the **top** of the external ID range, freeing the low IDs for custom
characters.

Under vanilla counts this is the **identity transform**: `FtExtNum = 0x21` (33), so
`SpecialStart = 33 - 7 = 26 = 0x1A`, and `newID == extID` for every entry. The decomp's count is
`Ft_Kind_Max = Ft_Kind_None = 0x21` (`src/melee/ft/forward.h`).

So the port shape is: express the thresholds in terms of a single count constant so that adding
characters later is a data change, not code surgery. **Today that means zero behaviour change and
zero memory-layout risk** (unlike §6.1) — which also means it cannot be validated in-game beyond
"still boots", because it intentionally does nothing.

### 6.3 Remaining tiers

1. **Character ID shifts (Tier A, highest count)** — make the internal/external thresholds
   derive from one count constant instead of literals. No memory-layout risk.
2. **CSS/SSS icon tables (Tier B)** — replace fixed `icons[26]` / `mnStageSel_803F06D0[30]`
   with data-driven tables of the same shape, fed from our own loader.
3. **Scene tables (Tier B)** — same treatment for `gmscdata.c`.
4. **Tier C hooks** — choose the native hook surface for m-ex's `Fighter On*` callback
   families and expose it as C callbacks.

Everything is opt-in behind `gw_Mex_Enabled("...")` and attributed per the rules in
[`../../tools/mex_port/README.md`](../../tools/mex_port/README.md).
