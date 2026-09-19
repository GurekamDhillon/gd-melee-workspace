# m-ex item spawn for Sonic's spring (global ItemKind 277)

**Date: 2026-09-19.** Research only. Nothing was built, nothing was run, no ISO and nothing under
`C:/gdm/melee/` was modified. m-ex is used as a **specification only**: every m-ex behaviour below
is paraphrased in my own words; no m-ex `.asm`/`.h`/`.dat` content is reproduced. Where m-ex's
source was read, the **shipped bytes** (Akaneia's `codes.gct`) were disassembled as well, so the
claims rest on what the disc actually runs, not on a source tree that might differ from it.

Evidence labels: **VERIFIED** = read directly in a file or a disassembly (location given).
**INFERRED** = reasoned from verified facts, not observed.

New tool: `C:/gdm/tools/mex_port/dump_itfunction.py` (see [Tooling](#tooling)).

---

## TL;DR

1. **`itFunction` = `{ u32 count; MEXFunction *item[count]; }`**: a count followed by an inline
   array of pointers, one per *article index*. Each element is an ordinary 8-word `MEXFunction`
   (same struct as `ftFunction`: code, instruction relocs, function relocs, code size, debug
   symbols). The previous agent parsed the 2-word *outer* header as a `MEXFunction`. The element's
   function reloc table is `{slot, code_offset}` pairs where `slot` is a **word index into the
   0x3C-byte `ItemLogicTable`**. The layout agrees across all 7 Akaneia custom fighters.
2. **`item.Custom[40]` is filled by m-ex's `itFunction` loader (guest `0x803D7070`), NOT by
   `MEX_IndexFighterItem` (`0x803D7058`).** `MEX_IndexFighterItem` writes *only*
   `item.RuntimeIndex[global-237] = desc`. The `itFunction` loader is called from m-ex's
   fighter-init hook at `0x80068B40` (inside `Fighter_UnkInitLoad_80068914`), right after
   `ftFunction` is relocated and overloaded. Both verified by disassembling the payloads in
   Akaneia's `codes.gct`.
3. **The native fix site is `Item_80267978` in `C:/gdm/melee/src/melee/it/item.c:532`.** For kind
   `>= 237`: `xB8_itemLogicTable = &item.Custom[kind-237]` (the *address of* the 0x3C entry, not a
   function pointer), `xC4_article_data = item.RuntimeIndex[kind-237]`, assert if the latter is
   NULL, then fall through to the existing `xBC_itemStateContainer = xB8->states` (item.c:559).
   **Two more m-ex patches are on Sonic's spawn path and are also required**: the render callback
   in `Item_8026862C` (item.c:912) and **growing the item struct by 4 bytes, with the original
   owner stored at `Item+0xFCC`**. Sonic's spring `OnSpawn` dereferences `Item+0xFCC`
   unconditionally.
4. **Yes, every spring callback is guest PPC** (8 logic-table slots + 9 state-table functions,
   all inside `itFunction`'s own code blob, including the state table itself). Native item code
   will call guest addresses from **three** places: `xB8` slots, the `ItemStateTable` rows that
   `Item_80268E5C` copies into `Item.animated/physics_updated/collided`, and **`Item.jumped_on`,
   which the guest writes directly with a raw store** (no bridged call to intercept). The port's
   `gw_mex_callable()` currently only recognises the `ftFunction` blob range.

---

## Q1. `itFunction`'s layout

### 1.1 Outer header: VERIFIED

Source: `PlSn.dat` on `C:/iso/Akaneia.iso`, `itFunction` public symbol at **data+0x3D648**
(archive relocated at base 0, so every pointer below is a data-section offset). `R` = the word is
in the archive's relocation table.

| data off | field | value |
|---|---|---|
| 0x3D648 | `count` | 1 |
| 0x3D64C | `item[0]` | data+0x3D650 **R** |

m-ex's loader (source `Standalone Functions/Init itFunction.asm`; shipped bytes: `codes.gct` C2
hook at `0x803D7070`, gct file offset `0xD0A8`, 640 bytes) confirms the shape. It reads `count` at
`+0`, then for `n = 0..count-1` loads `item[n]` from `+4 + 4n` (instructions
`addi r3,r29,4 / mulli r4,r21,4 / lwzx r22,r3,r4`), **skips NULL entries**, and treats each
non-NULL entry as a `MEXFunction` (passes it to m-ex's `Reloc`, then reads `+0x0C`/`+0x10`/`+0x00`
from it). So it is an **inline pointer array**, not `{count, pointer-to-array}`. The two readings
cannot be told apart for Sonic (count 1) but they can for Wolf/Diddy/Lucas (see 1.5).

### 1.2 `item[0]` (Sonic's spring): VERIFIED

`MEXFunction` at **data+0x3D650** (identical field layout to `ftFunction`, `mex-dump-tools.md` §2.1):

| off | field | value |
|---|---|---|
| +0x00 | code | data+0x160 |
| +0x04 | instructionRelocTable | **data+0x0** (yes, offset zero, and valid) |
| +0x08 | instructionRelocTableNum | 41 (0x29) |
| +0x0C | functionRelocTable | data+0x3D670 |
| +0x10 | functionRelocTableNum | 8 |
| +0x14 | codeSize | 0x500 |
| +0x18 | debugSymbolNum | 22 (0x16) |
| +0x1C | debugSymbol | data+0x3D6B0 |

So the article's code lives at **data+0x160 .. data+0x660** of `PlSn.dat`, *before* `ftFunction`'s
own code (data+0x23E0). Its 41 instruction relocs occupy data+0x0 .. data+0x148. The function
reloc table sits between the `MEXFunction` and its debug symbols (0x3D670..0x3D6B0 = 8 × 8 bytes).

Instruction reloc flags (41): abs32 = 9, lo16 = 4, hi16 = 4, branch = 24. These are the same four
flags with the same meaning as in `ftFunction`, so the port's existing `gw_ftfunction_reloc`
handles them unchanged.

### 1.3 The function reloc table writes `ItemLogicTable` slots: VERIFIED

Each 8-byte entry is `{ u32 slot; u32 code_offset; }`. The loader writes
`table[slot] = code + code_offset` (disassembly of the `0x803D7070` payload `+0x94..+0xAC`:
`lwz r3,4(r5); add r3,r3,r10; lwz r4,0(r5); mulli r4,r4,4; stwx r3,r4,r9`). `table` is the
0x3C-byte entry for the article's global kind (see Q2). The 15 words of that entry are
`struct ItemLogicTable`, `C:/gdm/melee/src/melee/it/kinds/types.h:26-71`: `states, spawned,
destroyed, picked_up, dropped, thrown, dmg_dealt, dmg_received, entered_air, reflected, clanked,
absorbed, shield_bounced, hit_shield, evt_unk`. 15 × 4 = 0x3C, which matches m-ex's stride.

Sonic's 8 entries, named by the blob's own debug symbols (`dump_itfunction.py` output):

| slot | `ItemLogicTable` field | code off | debug symbol |
|---:|---|---:|---|
| 0 | `states` (+0x00) | 0x000 | `item_state_table` |
| 1 | `spawned` (+0x04) | 0x030 | `OnSpawn` |
| 2 | `destroyed` (+0x08) | 0x0B4 | `OnDestroy` |
| 6 | `dmg_dealt` (+0x18) | 0x0D4 | `OnGiveDamage` |
| 7 | `dmg_received` (+0x1C) | 0x0F8 | `OnTakeDamage` |
| 9 | `reflected` (+0x24) | 0x100 | `OnReflect` |
| 12 | `shield_bounced` (+0x30) | 0x120 | `OnHitShieldBounce` |
| 13 | `hit_shield` (+0x34) | 0x144 | `OnHitShieldDetermineDestroy` |

Slots 3, 4, 5, 8, 10, 11 and 14 (`picked_up, dropped, thrown, entered_air, clanked, absorbed,
evt_unk`) are not written. Every native use of those fields in `item.c` either checks for NULL or
goes through `RunGObjCallback`/`processCallback` (list: `grep xB8_itemLogicTable-> item.c`), so
zero is a valid "no callback". Both helpers check for NULL (VERIFIED: `processCallback` tests
`if (cb && cb(gobj))`, `RunGObjCallback` tests `if (arg1 != NULL)`). One exception outside
`item.c`: `kinds/itlinkboomerang.c:252` calls `thrown` without a check, but only for Link's
boomerang.

**Line numbers note:** `item.c` is being edited in parallel. The line numbers in this document
were read on 2026-09-19 and have already drifted by about 12 lines in places, so search by function
name.

The debug-symbol names match the decomp field meanings one-for-one (`OnSpawn`↔`spawned`,
`OnGiveDamage`↔`dmg_dealt`, `OnHitShieldBounce`↔`shield_bounced`, ...). That independently confirms
both the slot numbering and the decomp's `ItemLogicTable` field order.

### 1.4 The per-state table lives INSIDE the code blob: VERIFIED

Slot 0 (`states`) = code+0x000. The debug symbol `item_state_table` spans code 0x000..0x030 =
**3 rows** of `struct ItemStateTable` (`kinds/types.h:12-24`: `anim_id, animated,
physics_updated, collided`, stride 0x10). The first 9 **abs32** instruction relocs
(code+0x04/08/0C/14/18/1C/24/28/2C, all code-relative) fix up its 9 function words:

| state | anim_id | animated | physics_updated | collided |
|---:|---:|---|---|---|
| 0 | 1 | `Idle_Anim` 0x14C | `Idle_Phys` 0x16C | `Idle_Coll` 0x174 |
| 1 | 2 | `Fall_Anim` 0x1BC | `Fall_Phys` 0x1DC | `Fall_Coll` 0x244 |
| 2 | 3 | `Rebound_Anim` 0x270 | `Rebound_Phys` 0x2D0 | `Rebound_Coll` 0x304 |

Offsets are code-relative; guest VA = item code base + offset. The blob also contains functions
that no table reaches: `Idle_Enter` 0x30C, `Fall_Enter` 0x374, `Rebound_Enter` 0x3AC and
`Spring_JumpedOn` 0x418..0x500. There is also a 4-byte float constant, `.rodata.cst4`, at 0x3A8.

### 1.5 Cross-check across all Akaneia custom fighters: VERIFIED

`python dump_itfunction.py --iso C:/iso/Akaneia.iso --survey PlSn.dat PlTs.dat PlWf.dat PlDd.dat PlDe.dat PlLc.dat PlLz.dat`:

| file | count | items (code off+size, instr relocs, slots written) | `item_lookup` count |
|---|---:|---|---:|
| PlSn | 1 | [0] 0x160+0x500, 41, {0,1,2,6,7,9,12,13} | 1 |
| PlTs | 1 | [0] 0x120+0x454, 36, {0,1,2,6,7,9,10,12,13} | 2 |
| PlWf | 2 | [0] 0x100+0x2A0 {0,1,6,7,9,10,13}; [1] 0x4CEF8+0x34 {0,3} | 4 |
| PlDd | 3 | [0] {0}; [1] {0,1,6,7,9,10,13}; [2] {0,1,2,3,4,5,6,7,9,12,13} | 5 |
| PlDe | 4 | [0] **NULL**; [1] {0,14}; [2] {0,2,6,7,9,12,13,14}; [3] {0,6,9,12,13,14} | 6 |
| PlLc | 10 | [2] **NULL**; 9 others, all include slot 0 | 11 |
| PlLz | 3 | [0] {0,6,13}; [1] {0,2,3}; [2] {0,2,13}. **codeSize 0, no debug syms** | 4 |

The evidence for the layout:
- In all 7 files the outer words parse as `{count, relocated ptr ...}`.
- Every non-NULL element parses as a `MEXFunction` whose fields stay in bounds.
- Every `slot` is in 0..14, so it fits the 15-word table.
- **Every article writes slot 0 (`states`).**
- NULL holes occur exactly where the loader's NULL check would need them.

`count` is always ≤ that fighter's `item_lookup` count. Articles past `count` get no `itFunction`
code. They keep whatever `item.Custom` shipped with: for example, Wolf's 255 ships statically
populated (`mex-dump-tools.md` Corrections §1).

One anomaly I did not investigate: PlLz's three items report `codeSize 0` and no debug symbols, yet
they still have relocs and slot writes. It is probably an older MexTK output format. It does not
affect Sonic.

### 1.6 Where the struct is declared

m-ex does **not** declare an `itFunction` struct in `MexTK/include/mxdt.h`. The only definition is
implicit in the loader. m-ex's `Header.s` names the 8 `MEXFunction` fields (`ftX_*`, +0x00..+0x1C),
and the loader indexes `item[n]` at `+4+4n`. The layout above is reconstructed from that loader's
behaviour plus the shipped data.

---

## Q2. Who fills `item.Custom[277-237]`, and with what

### 2.1 `MEX_IndexFighterItem` (0x803D7058) does NOT touch `item.Custom`: VERIFIED

At `0x803D7058` the Akaneia **DOL** still holds the vanilla `gmResultCharacterData` floats
(`3F59999A 3F4CCCCD ...`, disassembled from section 12 of the ISO's `main.dol`). The code is
installed at boot by a **`C2` hook in `codes.gct` that targets `0x803D7058`** (gct offset `0xCF98`,
264-byte payload). On hardware, then, the "function" is a branch into the Gecko code handler. Each
standalone function's `C2` target is its 4-byte entry slot, and the payload ends in `blr` before it
could fall through to the next slot.

Disassembly of that payload (args: r3 = fighter kind, r4 = desc, r5 = article index):

1. `item_lookup = mexData(r2+0x178)->fighter(+0x08)->item_lookup(+0x4C)`; entry = `item_lookup + kind*8`.
2. If `article >= entry.count` → `OSReport("...does not contain item %d for fighter %d")` + `__assert`.
3. `global = entry.ids[article]` (u16).
4. `item = *(r2+0x88)` (`OFST_ItemsAdded`, i.e. `mexData->item`); `item->RuntimeIndex(+0x14)[global-237] = desc`.
5. Return. **That is the whole function**: one store, into `RuntimeIndex` only. It does not check
   that `global >= 237`, so a vanilla-range id would write at a negative index.

The port already implements exactly this (`gw_mex_shim_index_item`,
`C:/gdm/melee/pc/platform/gw_mex_ftfunction_runtime.c`). The comment there says it is not yet
known whether this call also fills item.Custom. That question is now settled: **it does not.**

### 2.2 The `itFunction` loader (0x803D7070) fills `item.Custom`: VERIFIED

`codes.gct` `C2` hook at `0x803D7070` (gct offset `0xD0A8`, 640 bytes). Args: r3 = the fighter's
archive (HSD archive header), r4 = m-ex internal kind, r5 = 0 for fighter / 1 for stage. Behaviour:

1. `itf = HSD_ArchiveGetPublicAddress(archive, "itFunction")` (`0x80380358`,
   `symbols.txt:19487`). If there is none, return 0.
2. For each `n < itf->count` with `itf->item[n] != NULL`:
   a. Run m-ex `Reloc` (`0x803D7074`) on `item[n]`. It applies the element's instruction relocs to
      its code **in place**. It deduplicates through m-ex's xFunction lookup list (max 30), so
      running it again on the same `MEXFunction` does nothing (source `Reloc.asm`; payload at gct
      `0xDCA0`).
   b. `table = TableFor(kind, type, n)`. First the global id: `global = item_lookup[kind].ids[n]`
      for a fighter, or the stage equivalent (`mexData+0x28 -> +0x0C`). Then the **same five-way
      range split as Create Item**: `<43` Common, `<161` Fighter−43, `<208` Pokemon−161, `<237`
      Stages−208, else Custom−237. Finally `table = rangeTable + index*0x3C`. If
      `item_lookup[kind].ids` is NULL, it calls OSReport and asserts. It does **not** check
      `n < item_lookup[kind].count`.
   c. For each function reloc `{slot, off}`: `table[slot] = item[n].code + off`.
3. Return 1. The caller uses this to decide whether to flush the icache.

So an article's code **overlays** its 0x3C entry: listed slots are overwritten and unlisted slots
keep their shipped values. For Sonic, `item.Custom[40]` ships all-zero, so after this runs it holds
exactly the 8 slots of §1.3 and zeros everywhere else. Under m-ex's design a fighter article could
also target a *vanilla* table (ids < 237). No Akaneia fighter does this; all their ids are 253..285.

### 2.3 Who calls the loader, and when: VERIFIED

The caller is the `codes.gct` `C2` hook at **`0x80068B40`** (gct offset `0x8`, 384 bytes; source
`Init ftFunction.asm`). `0x80068B40` is inside **`Fighter_UnkInitLoad_80068914`**
(`symbols.txt:1396`, size 0x52C). It is the instruction right after the `bl 0x800D0FA0` that
follows the `fp->ft_data` store (`stw r0,0x10C(r31)` at `0x80068B38`). The payload, with
r31 = fighter data:

1. `kind = fp->kind (+0x4)`; `archive = ftDataPointers(r2+0x98)[kind].+4` (stride 8).
2. `ftFunction` → `Reloc` → overload into `Arch_FighterFunc`. The port already does this step.
3. **`itFunctionInit(archive, kind, 0)`** (`bctrl` to `0x803D7070`).
4. If anything loaded, flush the icache for the archive.

So `item.Custom` is filled **at every fighter init**. That is before the fighter's `OnLoad` runs
(`OnLoad` is what calls `MEX_IndexFighterItem`), and long before any special. **INFERRED:** because
it runs on every fighter init, a second Sonic (or a rematch) runs it again. m-ex relies on
`Reloc`'s dedupe and on the writes being idempotent.

### 2.4 Therefore, for kind 277 on the port

| table | slot | filled by | port status |
|---|---|---|---|
| `item.RuntimeIndex[40]` | `ftDataSonic->x48_items[0]` (the `Article*`) | `MEX_IndexFighterItem`, from Sonic's `OnLoad` | **done** (`gw_mex_shim_index_item`) |
| `item.Custom[40]` (0x3C) | 8 slots of §1.3, pointing into the relocated `itFunction` code | `itFunctionInit` at fighter init | **missing**: the port never reads `itFunction` (a grep of `melee/` for `itFunction` finds nothing) |

---

## Q3. What a native re-expression of `Create Item.asm` must do

### 3.1 The patch itself: VERIFIED (shipped bytes, gct `0x6800`, 320 bytes)

The hook site is `0x80267990`. Vanilla context (Akaneia DOL, text section 1): the `Item_80267978`
prologue, `lwz r31,0x2C(r3)` (r31 = `Item*`), `lwz r3,0x10(r31)` (r3 = `item->kind`), then
**`0x80267990` `cmpwi r3,43`**, which is the first instruction of the vanilla range split. The
payload:

1. `item = *(r2+0x88)` (`mexData->item`).
2. Range split on `kind`: `<43`, `<161`, `<208`, `<237`, else custom. Custom:
   `idx = kind - 237`, `funcs = item->Custom (+0x10)`, `descs = item->RuntimeIndex (+0x14)`.
   The vanilla ranges pick the vanilla tables: descriptors from `r13-0x497C`/`-0x4968`/`-0x4970`
   and `0x804A0F60`, function tables from `item->Common/Fighter/Pokemon/Stages`.
3. `entry = funcs + idx*0x3C`. This is **the address of the entry, not a word loaded from it**.
4. `desc = descs[idx]` (stride 4).
5. **If `desc == NULL`: `OSReport("error: item not initialized\n")` then `__assert("m-ex", 0, ...)`.**
   Under m-ex this check applies to *every* range; vanilla only asserts for stage items. The
   function-table entry is **never** checked.
6. Otherwise `item->xB8 = entry` (`stw r30,0xB8(r31)`) and `item->xC4 = desc` (`stw r29,0xC4(r31)`).
7. Jump to **`0x80267A88`**. That is vanilla `lwz r3,0xB8(r31); lwz r0,0(r3); stw r0,0xBC(r31)`,
   i.e. `xBC_itemStateContainer = xB8->states`, followed by the epilogue.

Previous research said the patch stores "the function pointer" at `+0xB8`. Correction: it stores
the **pointer to the 0x3C `ItemLogicTable` entry**, which is exactly what the decomp field type
`ItemLogicTable* xB8_itemLogicTable` expects. `+0xC4` = `Article* xC4_article_data`. I verified
both offsets against `C:/gdm/melee/src/melee/it/types.h:281-284`.

### 3.2 Where it goes in the decomp: VERIFIED

**`C:/gdm/melee/src/melee/it/item.c`, `void Item_80267978(HSD_GObj* gobj)`, line 532**
(`symbols.txt:12978`, `.text:0x80267978`, size 0x130; 0x80267990 is +0x18 into it). Its
`if/else if` chain is the vanilla range split. Kind 277 currently lands in the final `else` (stage
items, `kind - It_Kind_Old_Kuri`), which indexes `it_804A0F60[69]` and `it_803F4D20[69]`. The
second is a 30-entry table, so both reads are out-of-bounds garbage. The native fix is one more
branch **before** the stage-items `else`: `kind >= 237` → Custom/RuntimeIndex as in 3.1, then fall
through to the shared line 559 (`xBC = xB8->states`).

Pseudocode (my own wording, not m-ex's):

```c
} else if (item_data->kind >= GW_MEX_CUSTOM_ITEM_START) {       /* 237 */
    u32 idx = item_data->kind - GW_MEX_CUSTOM_ITEM_START;
    item_data->xB8_itemLogicTable = mex_item_custom_entry(idx);  /* &Custom[idx], stride 0x3C */
    item_data->xC4_article_data   = mex_item_runtime_desc(idx);  /* RuntimeIndex[idx]       */
    if (item_data->xC4_article_data == NULL) {
        OSReport("item not initialized\n");  __assert(...);      /* hard failure, as m-ex */
    }
}
```

m-ex does no further checking. I recommend two extra checks: bounds-check `idx < 49`, and assert
that `entry->states != NULL`. Without the second, an unpopulated Custom entry becomes a NULL
dereference later, in the consumer of line 559 (`Item_80268E5C`, `item.c:1181`), far from the
actual cause.

### 3.3 Other m-ex patches on Sonic's spawn path: VERIFIED present in `codes.gct`

The brief asked only about `Create Item.asm`. These patches are on the same path, though, and the
spawn still fails without them:

| patch | site (decomp) | what it does for the spring | needed? |
|---|---|---|---|
| **GXLink** (C2 `0x80268684`, 208 B) | `Item_8026862C` `item.c:912`, the `GObj_SetupGXLink` range split | for kind ≥ 237 it uses the generic item renderer **`it_8026EECC`** (`symbols.txt:13165`) instead of indexing `it_803F4CA8[kind-208]`, which is out of bounds for 277 | **yes** |
| **Adjust Size** (`04` write `0x80266FD8` = `li r4,0xFD0`) | `item.c:113` `HSD_ObjAllocInit(&item_alloc_data, sizeof(Item), 4)` | item allocation grows 0xFCC → **0xFD0** | **yes** |
| **StoreOrigOwner** (C2 `0x8026717C`, 16 B) | `Item_80267130` `item.c:204` `item_data->owner = spawnItem->x0_parent_gobj` | also stores the same value at **`Item+0xFCC`** ("original owner") | **yes** |
| Initialize Item Data (C2 `0x80268754`) | after `HSD_ObjAlloc` in `Item_8026862C` | zeroes the first 0xFCC bytes of the new item | the port probably already does the equivalent |
| Determine Item Type (C2 `0x802674AC`) | `Item_802674AC` `item.c:282` | kind ≥ 237 → `hold_kind = 8` | not on Sonic's path (see below) |
| SpawnMEXItem (C2 `0x80268648`) | `Item_8026862C` entry | spawn kinds ≥ 5000 mean "article N of the spawner" | not on Sonic's path |

Why the owner field is mandatory: the spring's `OnSpawn` (code+0x30) does
`lwz r9,0xFCC(r30); lwz r3,0x2C(r9); ... bl ft_80088478`. It reads `Item+0xFCC` as a GObj and
dereferences that GObj's `user_data` to play SFX 5019 on the owner fighter. With the vanilla
0xFCC-byte item (`ASSERT_SIZE(struct Item, 0xFCC)`, `it/types.h:669`) that read goes **past the
end of the allocation**.

Why Determine Item Type is not needed for Sonic: Sonic's `Spawn_Spring` (ftFunction code
0x4AF0..0x4BE8) fills the `SpawnItem` itself. It puts `kind` at `+0x08` from `MEX_GetFtItemID` and
sets `hold_kind` at `+0x0C` **to 8 explicitly** (`li r9,8; stw r9,20(r1)`, with the struct at
`r1+8`). It then calls `Item_8026862C` directly (`bl 0x8026862C` at 0x4BB0). It never goes through
the `Item_80268B18`-family prefunctions, which are what call `Item_802674AC`. After the spawn it
stores the Sonic GObj at `Item+0xDD8` (`xDD4_itemVar`+4) and the item GObj at `fighter+0x222C`.

---

## Q4. Are the spring's callbacks guest code? Yes. VERIFIED

Every function the spring runs is PPC inside `itFunction`'s code blob (§1.3, §1.4). None of them
is a vanilla function. The native engine reaches guest code by three routes:

1. **`ItemLogicTable` slots**: `item->xB8->spawned(gobj)` at `item.c:1846`,
   `RunGObjCallback(... destroyed)` at 1928, and `dmg_dealt`/`dmg_received`/`reflected`/
   `shield_bounced`/`hit_shield` at 1552-1736. These are native indirect calls on guest addresses.
2. **State rows**: `Item_80268E5C` (`item.c:1120`) copies `xBC[msid].animated/physics_updated/
   collided` into `Item.animated`/`physics_updated`/`collided` (`item.c:1229-1231`), and native
   procs then call them. The guest's `Idle_Enter`/`Fall_Enter`/`Rebound_Enter` reach
   `Item_80268E5C` through the bridge.
3. **`Item.jumped_on` (`Item+0xD30`), written by a raw guest store.** `Idle_Enter` (code+0x30C)
   builds `code_base+0x418` (`Spring_JumpedOn`) with a hi16/lo16 reloc pair and does
   `stw r9,0xD30(r31)`. Native `Item_80269B60` (`item.c:1442-1443`) later calls
   `item_data->jumped_on(gobj)`. **No bridged call happens at the store.** The existing
   `gw_mex_callable()` intercepts bridged `GObj_SetupGXLink`/`HSD_GObj_SetupProc` calls, so it
   never sees this pointer. It needs its own solution (see checklist step 7).

One more callback is passed *through* a bridged call. `Fall_Coll` (code+0x244) passes
`code_base+0x3AC` (`Rebound_Enter`) as the `HSD_GObjEvent` argument of `it_8026E15C`
(`itgroundcoll.h:34`). `Idle_Coll` passes NULL to `it_8026D8A4`, which has the same shape
(`itgroundcoll.h:18`).

Current port constraint (VERIFIED by reading, not changed): `gw_mex_callable()` in
`gw_mex_ftfunction_runtime.c` accepts a guest address in only two cases. Either `gw_mex_in_blob()`
is true, which tests the **`ftFunction`** code range `[gw_mex_ff.code_base, +code_size)`, or the
address is a bridged vanilla function. Anything else panics. The spring's code is a separate blob,
so today every spring callback passed through a bridged call (such as `Rebound_Enter` above) would
hit that panic. The pointers on routes 1-3 never reach `gw_mex_callable()` at all: native code
would call them directly as x86 and fault. The thunk pool is `GW_MEX_THUNK_MAX 64`. The spring
adds at most ~19 distinct addresses (8 slots + 9 state functions + `Spring_JumpedOn` +
`Rebound_Enter`, with some overlap).

Other facts about the blob that make it easy to host (VERIFIED by disassembling all 0x500 bytes):
- It uses **no `r2` or `r13`** anywhere, so there is no rtoc/sda dependency.
- It reads `Item` fields directly by offset: `+0xC0` ground_or_air, `+0xC4` article data
  (`->x4` attrs, floats at +0/+4), `+0xDD4..` itemVar, `+0xDD0` flags, `+0x40/+0x44` and `+0xFCC`
  (orig owner). So the item struct must be guest-addressable and use the decomp layout.
- Its vanilla callees (all `bl` targets from branch relocs) are `it_80275158`, `ft_80088478`,
  `itColl_BounceOffVictim`, `it_80273030`, `itColl_BounceOffShield`, `it_80273130`,
  `it_8026D8A4`, `it_80272860` (2 floats), `it_8026E15C`, `it_80272CC0`, `Item_80268E5C`,
  `it_802762B0`, `ftCommon_8007DB58`, `ftCo_800DCFD4`, `ftCo_800DC920` and
  `ftCo_JumpAerial_Enter_Basic`. **All 16 appear in `gw_mex_bridge.c`'s address table** (checked
  by grep). I did not check that the float signatures are right for `it_80275158(gobj, f32)` and
  `it_80272860(gobj, f32, f32)`.
- The spring code never reads `xB8`/`xBC` itself.

---

## Implementation checklist: spawning kind 277

The steps are ordered, and each one can be tested on its own. Steps 1-4 make the tables right,
steps 5-8 make the guest code callable, and steps 9-10 do the spawn.

1. **Load `itFunction` alongside `ftFunction`.** Do this in the port's fighter-init path (the
   equivalent of the `0x80068B40` hook), after `ftFunction` is loaded: find public `itFunction` in
   the same `PlSn.dat`. Read `count` and `item[n]` (at `+4+4n`; these are data offsets). The port
   reads the raw file, so it can use these offsets without applying the archive's relocation, just
   as `gw_ftfunction_load_from_memory_at` does for `ftFunction`. Skip NULL entries.
2. **Copy and relocate each article's code** into its own guest region (Sonic: 0x500 bytes). The
   region must **not** overlap the `ftFunction` code at `GW_FTFUNC_CODE_BASE` (0x802F0000,
   0x5778 bytes). Apply its instruction relocs with the existing `gw_ftfunction_reloc` (same four
   flags). Sonic's reloc table is at data offset **0**, so never treat offset 0 as "absent". The
   9 abs32 relocs are what turn the in-blob state table into real guest addresses.
3. **Fill `item.Custom[kind-237]`** in the loaded `MxDt.dat`. Take `global = item_lookup[31].ids[n]`
   (= 277) and entry = `Custom + (global-237)*0x3C`. Then, for each function reloc, set
   `entry[slot] = code_base + off`. Leave the other slots as shipped. Guard `slot < 15`,
   `global` in 237..285, and `n < item_lookup[31].count`.
4. **Keep `MEX_IndexFighterItem` as it is.** It writes RuntimeIndex only, which is now confirmed
   correct. Add a test: after Sonic's `OnLoad`, `RuntimeIndex[40] == ftDataSonic->x48_items[0]` and
   `Custom[40].states == spring code_base`.
5. **Teach `gw_mex_callable()` the item blob range.** Replace the single `gw_mex_ff` range with a
   list of registered code ranges, so thunks can be created for spring addresses.
6. **Decide who holds native pointers and who holds guest pointers in the tables.** Native `item.c`
   calls through `xB8` and through the `ItemStateTable` rows, so those words must be callable from
   native code. There are two options:
   - (a) Write **thunk addresses** into `Custom[40]`. Build a **native copy** of the 3-row
     `ItemStateTable` (keep `anim_id`, thunk the 9 functions) and point `Custom[40].states` at it.
     The spring code never reads these tables, so the guest is unaffected.
   - (b) Leave the guest addresses in place and make the native call sites dispatch guest
     addresses through the interpreter.

   Option (a) stays inside the loader and needs no changes at `item.c` call sites. **INFERRED**
   preferable.
7. **Handle the raw `Item.jumped_on` store** (the guest writes `Spring_JumpedOn` at `Item+0xD30`).
   With option 6(a) this is the one raw guest pointer left. Minimal fix: at the native call site
   `Item_80269B60` (`item.c:1442`), if `jumped_on` falls inside a registered guest code range,
   route it through `gw_mex_callable()`/the interpreter. For Sonic, `jumped_on` is the only such
   field: the blob has exactly two hi16/lo16 code-address pairs, and the other one loads a float
   constant. Audit the other `Item` callback fields the same way if other articles write them.
8. **Wrap guest callbacks passed to `it_8026E15C` / `it_8026D8A4`** (arg 1) with
   `gw_mex_callable()` in the bridge, as is already done for `GObj_SetupGXLink`/`HSD_GObj_SetupProc`.
9. **Make the native `item.c` changes** (the three required m-ex behaviours):
   a. `Item_80267978` (`item.c:532`): add the kind ≥ 237 branch of §3.2, with the NULL-descriptor
      assert.
   b. `Item_8026862C` (`item.c:912`): kind ≥ 237 → `GObj_SetupGXLink(gobj, it_8026EECC, 6, 0)`.
   c. Grow the item allocation to 0xFD0: add a 4-byte "original owner" field at `+0xFCC` and update
      `ASSERT_SIZE` (`it/types.h:669`). Set the field in `Item_80267130` (`item.c:204`) to the same
      value as `owner`. Check that nothing else relies on `sizeof(Item) == 0xFCC`.
10. **Spawn test.** Sonic down-special → `Spawn_Spring` → `MEX_GetFtItemID == 277` →
    `Item_8026862C` returns non-NULL. Check that `xB8 == &Custom[40]`, `xC4 == RuntimeIndex[40]`
    and `xBC[0].anim_id == 1`. Check that `OnSpawn` runs (SFX 5019 on Sonic) and that the item
    enters state 0 (`Idle_Enter` → `Item_80268E5C(gobj, 0, 2)`). Per the user's memory notes, any
    run must be off-screen and needs a pad script.

---

## Open questions

1. **How many state rows are there when no debug symbol says so?** Sonic's state-table size
   (3 rows) comes from the extent of the `item_state_table` debug symbol (0x30). Nothing in the
   `MEXFunction` records a row count. That is fine for Sonic. For a blob without symbols (PlLz),
   the count would have to come from the largest `msid` the code passes to `Item_80268E5C`.
2. **PlLz's `codeSize 0`** items (§1.5). Not needed for Sonic; unexplained.
3. **Does anything else in m-ex read `Item+0xFCC`** (e.g. kill credit, or item ownership after a
   reflect)? I checked only the store site and the read in Sonic's `OnSpawn`.
4. **Float signatures** of `it_80275158(gobj, f32)` and `it_80272860(gobj, f32, f32)` in the bridge.
   The entries exist; I did not check whether `gen_sigs` marks them as taking floats.
5. **Which `SpawnItem` fields does Sonic set** beyond kind/hold_kind? I decoded only enough to rule
   out `Item_802674AC`. The port's `SpawnItem` layout must match the guest's 0x4C-byte fill
   (`r1+8 .. r1+0x54` in `Spawn_Spring`). I assume it matches because it is the decomp struct.
6. **Other kind-indexed tables outside `item.c`.** m-ex patches exactly the sites in §3.3. That is
   strong evidence that they are the only kind-indexed lookups on the create path. I did not audit
   other item subsystems for kind ≥ 237 (for example per-kind sound or attribute tables used later
   in the item's life).
7. **Stage items (`type == 1`)** use `mexData+0x28 -> +0x0C` for their lookup. Sonic does not need
   this, and I did not validate it against `MxDt.dat`.

---

## Tooling

`C:/gdm/tools/mex_port/dump_itfunction.py` is a read-only parser for `itFunction`. It reuses
`mex_hsd.py` and the `MEXFunction` parser in `dump_ftfunction.py`, and it writes nothing except an
explicit `--emit-blob` target.

```
python dump_itfunction.py --iso C:/iso/Akaneia.iso PlSn.dat                      # slots, names
python dump_itfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --states 8           # state rows (auto-bounded by debug symbol)
python dump_itfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --symbols --relocs   # full listing
python dump_itfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --emit-blob it_sn.bin
python ppc_disasm.py --raw it_sn.bin --base 0x80000000 --start 0x8000030C --count 28
python dump_itfunction.py --iso C:/iso/Akaneia.iso --survey PlSn.dat PlTs.dat PlWf.dat PlDd.dat PlDe.dat PlLc.dat PlLz.dat
```

Flags: `--item N` (one article), `--code-base` (default `0x80000000`), `--symbols`, `--relocs`,
`--states N`, `--emit-blob PATH`, `--survey`.

### Reproduction notes (not saved as tools)

- **`codes.gct` payloads:** read `codes.gct` from `C:/iso/Akaneia.iso`. The header is
  `00D0C0DE 00D0C0DE` and the terminator is `F0000000`. A `C2` code is
  `{0xC2 | addr&0x1FFFFFF, nlines}` followed by nlines×8 bytes; an `04` code is a one-word write.
  There are 1163 codes, and the terminator is at file offset `0x12D00`. The relevant hooks and
  their gct offsets: `0x80068B40`@0x8, `0x80267990`@0x6800, `0x803D7058`@0xCF98,
  `0x803D7070`@0xD0A8, `0x803D7074`@0xDCA0, `0x803D7088`@0xCB30 (GetFtItemID). To disassemble a
  payload, dump it to a file and run `ppc_disasm.py --raw <file> --base 0x81000000`. The payloads
  are position-independent: they `bl` to local strings and make absolute calls via
  `lis/ori r12; mtctr; bctrl`.
- **Akaneia DOL sections** (from the ISO's DOL header): text1 is `0x80005940`, size `0x3B1900`, at
  DOL offset `0x2520`. Data section 12 is `0x803B9840`, size `0x77E80`, at `0x3B6840`, and contains
  `0x803D7058`. `ppc_disasm.py --dol`'s `DOL_SECTIONS` maps only text0/text1, which is why it
  cannot reach `0x803D7058`. There is no m-ex code there anyway, only `gmResultCharacterData`.
