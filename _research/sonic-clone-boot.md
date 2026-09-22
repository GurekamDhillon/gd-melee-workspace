# Sonic clone boot — blockers and findings (work in progress)

Goal: boot the new `Ft_Kind_Sonic` (added in melee commit `0c41100eb`) reached via the dev remap
`ftMapping_list[ChKind_Popo] -> { Ft_Kind_Sonic, 0xFF }` (uncommitted, `TARGET_PC`-guarded) and
`MELEE_TARGET_TEST=32`.

## What works
- The remap reaches the new kind: log shows `MELEE_TARGET_TEST="32" -> ckind 32` then
  `Target Test direct launch: starting with ckind=32`, and `fp->kind == 33`.
- **Vanilla ISO: Sonic boots and renders in Target Test** (~1692 frames, no FATAL) — fixed via the
  `x10_animCurrFlags` kind-bit rewrite in `ftData_8008572C` (see blocker 1 below).
- Control: `MELEE_TARGET_TEST=fox` on the vanilla ISO boots and renders (~1680 frames) — so Target
  Test mode and the vanilla engine are healthy.

## The central lesson
A new kind index (33) is outside **every vanilla-sized per-kind structure**. Two classes:
1. **C tables** — handled by commit `0c41100eb` (widened to `Ft_Kind_Max`, Sonic = Fox's entry).
2. **Disc-loaded tables** (inside `PlCo.dat`, loaded by `Fighter_LoadCommonData`, assigned from
   `pData[]`) — vanilla 33 entries; index 33 reads out of bounds. Fixed so far via
   `ftCommonData_ExtendKindTable()` in `src/melee/ft/fighter.c` (uncommitted), applied to:
   - `ftPartsTable` (`pData[4]`) — caused `ftParts_80074194` "fighter parts num not match" (part=74
     vs Fox parts_num=73) — FIXED.
   - `Fighter_804D6540` (`pData[5]`) — per-kind table read by `ftParts_8007506C(ftkind, part)` —
     FIXED.
   Other `pData[]` tables are indexed by non-kind things (swing type, colour, damage) — checked, not
   kind-indexed: `Fighter_804D6548[i<9]`, `Fighter_804D654C[swing_type]`, `Fighter_803C..`.
   **Re-audit if more disc tables surface.**
3. **Kind encoded *inside* disc data** (not a table index) — the per-anim wait-anim table
   `xC[i].x10_animCurrFlags` packs the figatree's FighterKind into its low 6 bits. Reusing Fox's data
   verbatim left it saying Fox, which misrouted Sonic to the cross-kind animation path. Fixed by
   rewriting those bits in `ftData_8008572C` (blocker 1).

## Remaining blockers
### 1. Vanilla ISO — animation crash — FIXED (2026-09-15)
The crash was NOT a NULL `ftData_80085E50` (that was a red herring — the actual write-to-NULL was
deeper). Real chain, resolved from the crash RVA + objdump:

`Fighter_ChangeMotionState -> ftAnim_8006EBE8 -> ftAnim_8006FE08 -> ftAnim_8006FCE4 ->
lbAnim_8001E7E8` (`src/melee/lb/lbanim.c`). The faulting instruction is `movl $0x0,(%ecx)` with
`ecx=0` — `fobj->next = NULL` at the end of `fn_8001E60C` (inlined into `lbAnim_8001E7E8`), after the
loop skipped every `FigaTrack` because each had `obj_type` 5/6/7.

Root cause: `fp->x597_bits` ("kind of this fighter's figatree") is read from the wait-anim table's
`x10_animCurrFlags`, which Fox's disc data encodes as kind 1 (Fox). For Sonic `fp->kind` = 33, so
`fp->kind != fp->x597_bits` and the engine routes the clone down the **cross-kind remap path**
(`ftAnim_8006FCE4`), which uses `lbAnim_8001E7E8` and *skips* the constant track types (5/6/7) that a
native Fox figatree legitimately contains -> zero FObjs -> NULL write. Fox never hits it because its
kind matches (native path `ftAnim_8006F4C8 -> lbAnim_8001E6D8`, no skip).

**Bit-layout gotcha:** `x597_bits : 6` is the *trailing* `u32` bitfield; on the big-endian PPC target
bitfields allocate MSB-first, so it lives in **bits 0-5** of `x10_animCurrFlags`, NOT the top 6 bits.
(Confirmed empirically: `x594_s32 = 0x84000001` printed `x597_bits = 1`.)

**Fix:** in `ftData_8008572C` (`ftdata.c`), after `gFtDataList[kind]` loads, a `TARGET_PC` block
rewrites the low 6 bits of every `xC[i].x10_animCurrFlags` to the fighter's own kind for
`Ft_Kind_Sonic`. Only those bits change; the parts mask/flag bits stay Fox's (correct, since Sonic's
parts table is Fox's). Sonic now boots + renders Target Test (~1692 frames) with no FATAL.

### 2. Akaneia ISO — ~956 KB `memp` OOM — FIXED (2026-09-16)
`lbMemory_80014FC8: ALLOC_FAIL size=0xE9B20 lo=0x801F1940 hi=0x806EBFD0` → `memp_kouho` assert
(`src/melee/lb/lbmemory.c:163`). The pool is **heap 3 (0x4FA690)**. Reproduced:
- Akaneia + card save → OOM at boot.
- Akaneia + `MELEE_TARGET_TEST=32` → OOM in the match/TT setup (frame ~3).

**Root cause (measured).** The failing allocation is **`IfAll.usd`** (the "all items" archive),
preloaded into heap 3 by `lbDvd` `inline2` (`EfMnData.dat`, `EfCoData.dat`, `ItCo.usd`, `IfAll.usd`,
all `lbDvd_80017740(..., heap=3)`). Akaneia's `IfAll.usd` is `0xE9B1C` (957,212 B) vs vanilla's
`0xDC1BC` (901,564 B) — **+0x55B8 (55,648 B)** because Akaneia adds many custom items. The measured
heap-3 shortfall is **0xB6B0 (46,768 B)**; `EfCoData.dat` (0x145B5F) and `ItCo.usd` (0x2D5EEC) are
identical on both discs. So it is a genuine memory-budget issue: the *same* files load on vanilla,
only the item archive grew.

**Fix.** Grow heap 3 in `lbHeap_803BA380` (`TARGET_PC` only) from `0x4FA690` to `0x51A690`
(+0x20000 = 128 KB). Donor = the main heap (heap 0), ~0xAC8C10 (~11.3 MB) with ~35 KB used at that
point, so it shrinks to ~11.2 MB. Headroom ≈ 0x14950 (~84 KB). Only the numeric size field changes
— no struct-size/layout change; the matching (non-`TARGET_PC`) table keeps vanilla `0x4F8800`.

**Verified:** Akaneia `MELEE_TARGET_TEST=32` boots Target Test and renders 1920+ frames with no
`ALLOC_FAIL`/`memp_kouho`/FATAL. Controls: vanilla boots + renders, vanilla Sonic/fox TT render,
`run_tests.bat` 18/18. Evidence: `.omo/evidence/task-akaneia-oom.log`.

## m4: Sonic's own DATA (model/anims/costumes) mounted — DONE (2026-09-16)

The next step after the OOM fix: point `Ft_Kind_Sonic`'s per-kind DATA tables at Sonic's own
Akaneia files (`PlSn.dat` / `ftDataSonic`, 7 costumes `PlSnNr/Re/Gr/Ye/Bk/Or/Wh.dat`, anim
`PlSnAJ.dat`, anim count 321), while the **behaviour/moveset stays Fox's**. Evidence:
`.omo/evidence/task-m4-sonic-data.log`.

### What works
- Sonic's data loads: `ftData_8008572C kind=33 file=PlSn.dat sym=ftDataSonic` and
  `ftData_80085820 kind=33 costume=0 file=PlSnNr.dat joint=PlySonic5K_Share_joint`.
- Parts table: `ftCommonData_ExtendKindTable` now gives Ft_Kind_Sonic **m-ex's Sonic entry** —
  `loaded[31]` (Akaneia's per-kind tables are authored under m-ex's numbering, which moves the six
  bosses to 35..40 and puts the new fighters at 27..33, Sonic = 31). Verified `parts_num=71`
  (Sonic) vs Fox 73; `ftParts_SetupParts` ends `part=71 == parts_num=71`, no mismatch.
- Disc detection: `ftData_SonicHasOwnData()` probes the disc FST for `PlSn.dat`
  (`DVDConvertPathToEntrynum`); on a vanilla disc `ftData_SonicFallback()` restores Fox's entries,
  so the vanilla clone boot still renders Fox (verified: `file=PlFx.dat sym=ftDataFox`).
- The `ftData_8008572C` kind-bits rewrite is still needed and still correct: m-ex authors Sonic's
  figatree with kind **31**, the port's kind is **33**, so the low 6 bits must be rewritten to 33
  or `ftAnim` takes the cross-kind path. Comment updated accordingly.
- Controls green: `run_tests.bat` 18/18, vanilla boot renders, vanilla `TT=32` renders Fox clone.

### Remaining blocker: Aurora/GX render crash — FIXED (2026-09-16)
On Akaneia, after the model loads and parts match, the first model draw at frame ~4 died with
`Exception code: 0xc0000409` in `ucrtbase.dll`. The `/GS`-cookie theory was a **misdiagnosis**:
the real fault is `abort()`. `ucrtbase.dll` (32-bit) `abort` is at RVA `0x2da40`, and the fault
offset `0x2da71` = `abort+0x31`, the `int 29h` fast-fail inside `abort()`. Proven by overriding
`__security_check_cookie` (never sees a mismatch) and by catching `SIGABRT`, whose stack resolves
to `process -> handle_draw -> draw_prim -> push_gx_draw -> gfx::push -> ByteBuffer::append ->
ByteBuffer::resize -> if (!m_owned) abort()` (`internal.hpp:337`).

**Root cause.** `frame.storage` (and verts/indices/uniforms) are **non-owning** `ByteBuffer`
views mapped over a fixed staging region — `StorageBufferSize = 8 MiB` (`lib/gfx/resources.hpp`).
Sonic's m-ex model is drawn as many **per-triangle indexed draws** (each `GXBegin(GX_TRIANGLES,3)`
references its arrays via a monotonically *growing* max index), unlike vanilla fighters whose
display lists carry vertex data inline. In `push_gx_draw`, `needed = max_index*stride+…` grows
every triangle, so the cached snapshot re-uploads the whole array once per triangle — **O(n²)**
bytes into the 8 MiB storage buffer, overflowing it on the first draw.

**Fix.** `melee/extern/aurora/lib/gx/command_processor.cpp`, in `push_gx_draw`: grow the indexed
array's cached snapshot **geometrically** (double, clamped to the reported array size) instead of
re-uploading exactly `needed`; doubling applies only to *bounded* (MEM1) arrays, unbounded
(`UINT32_MAX`) arrays still upload exactly `needed`. Amortized O(n), total stays well under 8 MiB.
Documented in `extern/aurora/PORT_PATCHES.md` §3. Evidence:
`.omo/evidence/task-aurora-sonic-render.log`.

**Verified:** Akaneia `MELEE_TARGET_TEST=32` renders Sonic for 1655+ frames (~27 s) with no
crash — `PlSn.dat/ftDataSonic` + `PlySonic5K_Share_joint` loaded, `parts_num=71` matched,
`aurora drawcalls=318 verts=122596`, envelope `bad_weight_sum=0`. PrintWindow screenshot confirms
a blue Sonic (white gloves, red shoes) on the Target Test stage. Controls: vanilla boot + vanilla
`TT=32` Fox clone render, `run_tests.bat` 18/18.

## Diagnostics
- `MELEE_TARGET_TEST=<ckind|name>` → `gw_TestTargetTestCKind` (`pc/platform/gw_runtime.c`).
- Resolve a crash RVA: `"/mnt/c/Program Files/Git/bin/bash.exe" -lc 'bash /c/gdm/_build/masstest/mapsym.sh 0x<rva>'`
- A temporary `OSReport` at the assert site prints `kind`, `part`, `parts_num` (removed after use).
