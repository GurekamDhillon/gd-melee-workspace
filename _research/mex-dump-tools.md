# `dump_ftfunction.py` / `dump_mxdt.py` — offline m-ex format dumpers

**Date: 2026-09-19.** Analysis only: nothing was built, nothing was run, no ISO and no file under
`C:/gdm/melee/` was modified. Both ISOs were opened read-only.

These two tools make permanent the throwaway analysis recorded in
[`mex-data-layer-design.md`](mex-data-layer-design.md) §1.6–§1.8 and §2.2. Everything below was
re-derived from scratch by these scripts, not copied from that report; where the two disagree it is
called out under [Corrections](#corrections).

- `C:/gdm/tools/mex_port/mex_hsd.py` — shared read-only GCM/FST and HSD-archive readers.
- `C:/gdm/tools/mex_port/dump_ftfunction.py` — the `ftFunction` blob in a fighter `.dat`.
- `C:/gdm/tools/mex_port/dump_mxdt.py` — `MxDt.dat` / the `mexData` struct.

Both take either a loose file or `--iso <image> <name-on-disc>`, both are non-interactive, both have
`--help`, and neither ever opens a file for writing except the explicit `--emit-blob` target.

---

## 1. Usage

### `dump_ftfunction.py`

```
python dump_ftfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --header --overrides
python dump_ftfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --symbols
python dump_ftfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --check-symbols
python dump_ftfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --resolve 0x800034F8
python dump_ftfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --emit-blob sn.bin
python dump_ftfunction.py ./PlSn.dat --relocs --limit 20        # loose file, no ISO
```

| flag | what it does |
|---|---|
| `--header` | archive header, public symbols, and the 8-word `MEXFunction` header |
| `--overrides` | the `functionRelocTable`, each slot named from **the blob's own debug symbols** and alongside the port's guessed name |
| `--relocs` | the `instructionRelocTable`, with a per-flag histogram |
| `--symbols` | the `MEXDebugSymbol` table as `start..end  name` |
| `--check-symbols` | empirically decides end-offset vs length (see §2.3) |
| `--resolve ADDR` | guest address (or bare code offset) → `name+0xNN`; repeatable |
| `--emit-blob PATH` | write the **relocated** flat blob — what the interpreter actually executes |
| `--code-base` | guest VA the blob is relocated to (default `0x80000000`) |
| `--symbol` | public symbol to parse (default `ftFunction`) |
| `--second-word-is-length` | deliberately use the wrong interpretation, to demonstrate the failure |

The relocated blob feeds the existing disassembler unchanged:

```
python dump_ftfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --emit-blob sn.bin
python ppc_disasm.py --raw sn.bin --base 0x80000000 --start 0x800034C4 --count 8
```

### `dump_mxdt.py`

```
python dump_mxdt.py --iso C:/iso/Akaneia.iso MxDt.dat --all
python dump_mxdt.py --iso C:/iso/Akaneia.iso MxDt.dat --validate     # the one that matters
python dump_mxdt.py --iso C:/iso/Akaneia.iso MxDt.dat --item-lookup --kind 31
python dump_mxdt.py --iso C:/iso/Akaneia.iso MxDt.dat --item --runtime-index
```

`--root`, `--metadata`, `--fighter`, `--item-lookup`, `--item`, `--runtime-index`, `--validate`,
`--all`. Exit status is **2** if `--metadata` or `--validate` finds a disagreement, 0 otherwise —
so it can be wired into a check without parsing the text.

Offline the archive is relocated with base 0, so **every pointer printed is a data-section
offset** — the same number the port sees before adding its own guest base.

---

## 2. `ftFunction` — verified facts

Source of every number below: `PlSn.dat` on `C:\iso\Akaneia.iso`.

### 2.1 Archive and header

```
PlSn.dat  267,926 bytes
archive: fileSize 0x41696  dataSize 0x3D8FC  relocs 3920  publics 3  externs 0
  ftDataSonic  data+0x2FA90
  ftFunction   data+0x3BB70
  itFunction   data+0x3D648
```

`MEXFunction` header at `data+0x3BB70`, all pointer fields being data offsets that the archive's
own relocation pass fixes up:

| off | field | Sonic's value |
|---|---|---|
| +0x00 | `code` | `data+0x23E0` |
| +0x04 | `instructionRelocTable` | `data+0x660` |
| +0x08 | `instructionRelocTableNum` | 944 |
| +0x0C | `functionRelocTable` | `data+0x7B60` |
| +0x10 | `functionRelocTableNum` | 25 |
| +0x14 | `codeSize` | `0x5778` |
| **+0x18** | **`debugSymbolNum`** | **207** |
| **+0x1C** | **`debugSymbol`** | **`data+0x3BB90`** |

The port's C loader (`melee/pc/platform/gw_mex_ftfunction.c`) defines `FTFUNC_OFF_CODE`…
`FTFUNC_OFF_CODE_SIZE` identically and stops at `+0x14`. `+0x18`/`+0x1C` are the two words it is
being taught to read; the values above are what it must produce.

### 2.2 `MEXDebugSymbol` — offsets, stride, field meanings

- Table base: **`data+0x3BB90`**, i.e. **`ftFunction + 0x20`** in this blob (immediately after the
  8-word header — convenient, but read `+0x1C`, do not assume adjacency).
- Count: **207**, from `ftFunction+0x18`.
- **Stride: 12 bytes.** Table spans `data+0x3BB90 .. data+0x3C544`.
- Entry: `{ u32 code_offset; u32 code_end; char *symbol; }`. All three are relocated by the
  archive, so `symbol` is a data offset to a NUL-terminated ASCII name.
- `code_offset` is relative to the **code blob**, not to the data section. Guest VA =
  `code_base + code_offset`.

First rows (`--symbols`, at `--code-base 0x80000000`):

```
   0  0x80000000..0x80000124  OnLoad
   1  0x80000124..0x80000194  OnRespawn
   2  0x80000194..0x800001D4  OnDestroy
   3  0x800001D4..0x800005B4  move_logic
   4  0x800005B4..0x800005D4  SpecialN
```

### 2.3 The second word is an END OFFSET — proven, not assumed

m-ex's own header (`MexTK/include/mxdt.h:115-120`) names it `code_length`. **It is not a length.**
`--check-symbols` decides this from the data alone:

```
  as END OFFSET end<=start:0  end>codeSize:0    end==next.start:202/206  overlaps:0
  as LENGTH     end<=start:0  end>codeSize:73   end==next.start:1/206    overlaps:205
  VERDICT: the second word is an END OFFSET.
  entry 0: start 0x0 second 0x124 OnLoad
  entry 1: start 0x124 second 0x194 OnRespawn   <- entry 0's second word == entry 1's start
  max(start+second) = 0xAE18 vs codeSize 0x5778 (past the end of the code)
```

Three independent proofs in that block:

1. **Chaining.** 202 of 206 adjacent pairs satisfy `entry[i].second == entry[i+1].start` exactly.
   Under the length reading only 1 pair does, and 205 pairs *overlap*.
2. **Bounds.** Under the length reading, 73 of 207 symbols claim to end past `codeSize 0x5778`,
   and the furthest claims `0xAE18` — nearly double the code. Under the end-offset reading, zero
   do.
3. **Monotonicity.** Under the end-offset reading the table is a clean, non-overlapping,
   almost-gapless partition of `[0, codeSize)`.

**Consequence for the port:** a loader that does `end = start + second` reads past the table's own
code region and will attribute crash addresses to the wrong function — usually a function several
entries earlier, because the bogus ranges overlap almost everything. This is a silent
mis-attribution, not a crash, so it will not announce itself. `--second-word-is-length` reproduces
the wrong behaviour on demand for a side-by-side test.

Checked on **all seven** Akaneia custom fighters; the verdict is END OFFSET for every one:

| file | debug symbols | codeSize |
|---|---:|---:|
| `PlSn.dat` | 207 | 0x5778 |
| `PlTs.dat` | 214 | 0x64DC |
| `PlWf.dat` | 184 | 0x3F88 |
| `PlDd.dat` | 246 | 0x6138 |
| `PlDe.dat` | 292 | 0x6C7C |
| `PlLc.dat` | 233 | 0x7DC8 |
| `PlLz.dat` | 132 | 0x36F4 |

### 2.4 The 25 override slots, named

`--overrides` reproduces the previous report's table exactly. The blob's own names disagree with
three of the port's guessed names in `gw_mex_ftfunction.c`:

| slot | blob symbol | port's `gw_ftfunction_slot_names[]` | verdict |
|---|---|---|---|
| 1 | `OnRespawn` | `onDeath` | **port name is wrong or at best misleading** |
| 21 | `EyeTextureDamaged` | `onKnockbackEnter` | **port name is wrong** |
| 22 | `EyeTextureNormal` | `onKnockbackExit` | **port name is wrong** |
| 14/15 | `OnSetItemInvisible` / `OnSetItemVisible` | `onMakeItemInvisible` / `onMakeItemVisible` | same thing, cosmetic |
| 17 | `OnItemCatch` | `OnItemPickup2` | same slot, better name in the blob |
| 25 | `ResetAttributes` | `onReapplyAttr` | same thing |
| all others | — | — | agree |

Slots 1, 21 and 22 are worth fixing: a log line saying `onDeath` when the blob calls it
`OnRespawn` will mislead whoever reads it. Note these names come from *Sonic's* blob; they are that
author's names for the slot, which is still better evidence than a guess.

### 2.5 Relocation, applied

`--emit-blob` applies the `instructionRelocTable` with the same four flag semantics the port
implements (`gw_ftfunction_reloc`): `0x01` abs32, `0x04` lo16, `0x06` hi16, `0x0A` branch-LI-OR,
`0x1A` rel32; a target whose top nibble is `0x8` is an absolute guest address, otherwise it is
code-relative. Sonic's histogram: **0x01=155, 0x04=250, 0x06=250, 0x0A=289** (944 total, no
unknown flags).

Spot-check of the relocated output against the previous report's disassembly — both match
byte-for-byte:

```
0x8000003C  81290048  lwz r9,72(r9)        ; ftData->x48_items
0x8000004C  483D700D  bl 0x803D7058        ; MEX_IndexFighterItem
...
0x800034C4  3D20804D  addis r9,r0,-32691   ; HSD_GObjPLinkHead
0x800034CC  81290000  lwz r9,0(r9)
0x800034D0  83E90024  lwz r31,36(r9)       ; [HSD_GOBJ_PLINK_ITEM]
```

`--resolve` turns the reported fault address into a name directly:

```
0x800034F8 -> code+0x34F8 -> SpecialN_SearchTarget_EnterAttack+0x118 [0x800033E0..0x800035B4]
0x80000BDC -> code+0xBDC  -> GXLink_Sonic+0x0
0x80000C74 -> code+0xC74  -> ProcessMouth+0x0
```

---

## 3. `MxDt.dat` — verified facts

```
MxDt.dat  115,396 bytes
archive: fileSize 0x1C2C4  dataSize 0x199F4  relocs 2600  publics 1  externs 0
  mexData  data+0x98A8
```

### 3.1 The 14 root words

Reproduced exactly as previously reported:

| +off | field | value | | +off | field | value |
|---|---|---|---|---|---|---|
| +0x00 | `metadata` | `data+0x1992C` | | +0x1C | `item` | `data+0x17D4C` |
| +0x04 | `menu` | `data+0x199CC` | | +0x20 | `kirby_data` | `data+0x15CF8` |
| +0x08 | `fighter` | `data+0x0D754` | | +0x24 | `kirby_function` | `data+0x17474` |
| +0x0C | `fighter_function` | `data+0x15BF8` | | +0x28 | `stage` | `data+0x0AE74` |
| +0x10 | `ssm` | `data+0x19408` | | +0x2C | `stage_desc` | `data+0x0BE0C` |
| +0x14 | `music` | `data+0x098E0` | | +0x30 | `scene` | `data+0x18920` |
| +0x18 | `effect` | `data+0x174D0` | | +0x34 | `misc` | `data+0x17498` |

All 14 land inside the `0x199F4`-byte data section.

### 3.2 `metadata` — the expected counts reproduce

`v1.1, flags 0`, then: `internal_id_count 41`, `external_id_count 41`, **`css_icon_count 32`**,
**`internal_stage_count 96`**, `external_stage_count 313`, **`sss_icon_count 67`**, `ssm_count 78`,
`bgm_count 139`, `effect_count 51`, `bootup_scene 2`, `last_major 45`, `last_minor 45`,
`trophy_count 342`, `trophy_sd_offset 351`.

**41 fighters / 32 CSS icons / 96 stages / 67 SSS icons — confirmed, no discrepancy.** The tool
asserts these four against the independently recorded values in
[`mex-content-expansion.md`](mex-content-expansion.md) and exits 2 on a mismatch.

### 3.3 `fighter.item_lookup` at `data+0x14744` — the Sonic triple is REPRODUCED

Independent confirmation, in three steps that do not rely on `mxdt.h`'s field order:

1. **Kind 31 is Sonic.** `fighter.pl_file[31]` (stride 8, `{char *name; char *symbol;}`) is
   `("PlSn.dat", "ftDataSonic")`. Not inferred — the strings are in the file.
2. **Stride 8, pointer in the second word.** Over the 41-entry table, the archive's relocation
   list touches **0** of the `+0` words and **7** of the `+4` words. A `{count, ptr}` layout is the
   only reading consistent with that; a `{ptr, count}` or stride-4 reading is not.
3. **Sonic has one article, global ItemKind 277.** `item_lookup[31] = { count: 1, ids:
   data+0x148C0 }` → `[277]`.

> **`MEX_GetFtItemID(sonic_gobj, 0) == 277` — independently reproduced. The triple
> (internal kind 31, exactly 1 article, global ItemKind 277) is safe to hard-code in a test.**

The full populated table, with the fighter identified from `pl_file` rather than assumed:

| kind | fighter (`pl_file`) | count | ids @ | global ItemKinds |
|---:|---|---:|---|---|
| 27 | `PlWf.dat` Wolf | 4 | `data+0x1488C` | 253–256 |
| 28 | `PlDd.dat` Diddy | 5 | `data+0x14894` | 257–261 |
| 29 | `PlLz.dat` Lizardon | 4 | `data+0x148A0` | 262–265 |
| 30 | `PlLc.dat` Lucas | 11 | `data+0x148A8` | 266–276 |
| **31** | **`PlSn.dat` Sonic** | **1** | **`data+0x148C0`** | **277** |
| 32 | `PlDe.dat` Dedede | 6 | `data+0x148C4` | 278–283 |
| 33 | `PlTs.dat` Tails | 2 | `data+0x148D0` | 284, 285 |

34 of 41 entries are `{0, 0}`; vanilla articles stay hardcoded.

### 3.4 `MexData.item` and `RuntimeIndex`

```
+0x00  Common        0x803F14C4  absolute guest address (vanilla table)
+0x04  Fighter       0x803F3100  absolute guest address
+0x08  Pokemon       0x803F23CC  absolute guest address
+0x0C  Stages        0x803F4D20  absolute guest address
+0x10  Custom        data+0x17D64   (relocated — an in-file table)
+0x14  RuntimeIndex  data+0x364C    (relocated — an in-file table)
```

The first four words are **not** in the relocation list; the last two are. That is the mechanical
proof of which fields are in-file tables and which are absolute pointers into the retail DOL.

**`item.RuntimeIndex` ships fully zeroed.** Stride 4, and the table length is pinned by the data
itself: the zero run starting at `data+0x364C` is **exactly 196 bytes = 49 words**, and
`285 − 237 + 1 = 49` is exactly the number of custom item kinds derived from `item_lookup`. Two
independent derivations of 49 agreeing is strong evidence for both the stride and the extent. No
relocations point into it. Runtime-filled, as expected — Sonic's 277 is index `277 − 237 = 40`.

---

## Corrections

Things these tools found that **contradict or refine** `mex-data-layer-design.md`.

1. **`item.Custom` does NOT ship all-zero.** §2.2(b) of that report says "Both in-file tables ship
   all-zero and carry no relocations". `RuntimeIndex` does; **`item.Custom` does not.** At stride
   `0x3C` over 49 entries, three entries ship populated:

   | global kind | idx | contents |
   |---:|---:|---|
   | 244 | 7 | `+0x00 = data+0x3710` (relocated), then 12 absolute `0x8027Cxxx/0x8027Dxxx` function pointers |
   | 253 | 16 | `+0x00 = data+0x188E0` (relocated), then 7 absolute `0x8029Cxxx` pointers |
   | 255 | 18 | `+0x00 = data+0x18900` (relocated), then 7 absolute `0x8029Cxxx` pointers |

   This is a partial answer to that report's open question §5.1 ("`item.Custom` — who fills it?").
   Some custom items ship their function table statically in `MxDt.dat`; **Sonic's 277 (index 40)
   is not one of them**, so for Sonic something still has to supply it at runtime, or item creation
   has to derive it from the `ItemDesc`. The question is narrowed, not closed.

2. **`fighter.names` is indexed by EXTERNAL id, `fighter.pl_file` by INTERNAL kind.** They are
   different index spaces inside the same struct. `names[0] = "C. Falcon"` (vanilla external id 0)
   while `pl_file[0] = ("PlMr.dat", "ftDataMario")` (vanilla internal kind 0). **Sonic is internal
   kind 31 but external id 30** (`names[30] == "Sonic"`; `names[31] == "King Dedede"`). mxdt.h
   labels the whole `MexData.fighter` struct "indexed by ft_kind", which is **not true of every
   member**. Anyone adding a field to the port's view of this struct must determine the index space
   per array, not per struct. `--validate` prints this explicitly.

3. **`itFunction` is not a `MEXFunction`.** Parsing `PlSn.dat`'s third public symbol with the
   `MEXFunction` layout produces nonsense (`code = data+0x1`, `codeSize = 0x3D670`,
   `functionRelocTable = 0` with count 41). The tool now bounds-checks the header and refuses with
   a named warning and exit 1 rather than printing garbage. `itFunction`'s real shape is
   **undecoded** — see open questions.

Everything else in `mex-data-layer-design.md` §1.6–§1.8 and §2.2 that these tools touch is
**confirmed**: the archive header numbers, all three public symbols and their offsets, the
`MEXFunction` field offsets, 207 debug symbols at `data+0x3BB90`, the end-offset gotcha, the 25
overrides and their names, the four reloc flag semantics, the 14 root words, all 15 metadata
fields, `fighter = 0xD754`, `costume_pointers = 0x14540`, `item_lookup = 0x14744`, and the whole
item-lookup table including Sonic's `{1, [277]}`.

---

## Trustworthy vs not

Because `mxdt.h`'s `MexData.fighter` is self-admittedly incomplete
("`// theres more im just lazy`", `mxdt.h:274`), an off-by-one in that struct would be silent. What
these tools establish, ranked:

**Trust (cross-checked against evidence inside the file, independent of the struct declaration):**

- `MEXFunction`'s `+0x18`/`+0x1C` debug-symbol fields, the 12-byte stride, and the end-offset
  meaning — proven from the table's self-consistency, on 7 separate files.
- The 25 override slots and their target addresses — the `functionRelocTable` and the debug symbol
  table agree with each other.
- The 14 `MexData` root words — all land in the data section and decode to plausible sub-structs.
- `MexMetaData` field order — four of its counts match an independently recorded source.
- `fighter.names` (readable strings, 41/41) and `fighter.pl_file` (filenames + `ftData*` symbols
  that match the disc's actual files).
- `fighter.item_lookup` at `data+0x14744` — layout proven by the relocation table, content proven
  by `pl_file`, extent cross-confirmed by the `RuntimeIndex` zero run.
- `MexData.item`'s six fields — which are in-file and which are absolute is proven by relocation
  membership, not by the declared types.
- `item.RuntimeIndex` stride 4 and length 49.

**Do not trust (decoded only by taking `mxdt.h`'s declaration order on faith):**

- Every `MexData.fighter` array *other than* `names`, `pl_file`, `costume_pointers` and
  `item_lookup`. The `--fighter` dump labels them, and all 33 pointers do land inside the data
  section, but "lands in the data section" is a weak test with a `0x199F4`-byte section — a
  one-slot shift would still pass it. `--fighter` prints a warning to this effect.
- The index space of any `MexData.fighter` array not named above (see correction 2).
- `MexData.fighter_function`'s field order (not exercised by these tools).
- `item.Custom`'s internal field layout. Stride `0x3C` comes from m-ex's
  `Item Extension/Create Item.asm`, and the populated entries are consistent with it, but the
  meaning of each of the 15 words is not established here.

---

## Open questions

1. **Who fills `item.Custom[277-237]`?** Three of 49 entries ship populated; Sonic's does not.
   Either `MEX_IndexFighterItem` writes it from the `ItemDesc`, or `Item_CreateItem` derives it.
   *Settle it by* disassembling m-ex's `MEX_IndexFighterItem` at guest `0x803D7058` out of the
   Akaneia DOL. (`ppc_disasm.py --dol` cannot reach it — `0x803D7058` is outside the two text
   ranges that script maps. Extend `DOL_SECTIONS`, or dump the region with `--raw`/`--base`.)
2. **What are the three populated `item.Custom` entries (244, 253, 255)?** They belong to Wolf
   (253) and to no fighter in `item_lookup` at all (244 is below Wolf's 253, so it is a *stage* or
   *misc* custom item). Worth knowing before assuming the table is fighter-only.
3. **`itFunction`'s header shape** is undecoded. Its first two words look like
   `{count = 1, ptr = data+0x3D650}`, but the struct at `data+0x3D650` does not parse as a
   `MEXFunction` under any field order tried. m-ex's headers do not declare it. Sonic's article
   code lives there, so this matters for the spring.
4. **Does `MEXDebugSymbol`'s second word ever behave as a length?** Only MexTK-built blobs on this
   disc were checked (all 7 agree it is an end offset). If MexTK ever changes, a loader that
   hard-assumes end-offset would silently mis-attribute. Keeping `--check-symbols` and running it
   on any new blob is the cheap defence.
5. **The 4 non-chaining pairs** in Sonic's debug symbol table (202 of 206 chain exactly). These are
   alignment gaps or dead code between functions; `--resolve` reports an address in such a gap as
   `(PAST this symbol - address is in a gap)` rather than silently attributing it. Not investigated
   further.
6. **The exact end of `MexData.fighter`.** `mxdt.h` lists 33 pointers; nothing here proves 33 is
   the real count rather than the count m-ex bothered to declare. The reliable cross-check is
   `Ploaj/MexManager`'s `MxDtCompiler.cs` (the writer), which was not consulted.
