# m-ex content, option B: execute `ftFunction` PowerPC blobs natively

Companion to [`mex-content-expansion.md`](mex-content-expansion.md). Decision: to run m-ex custom
fighters (starting with Sonic), **run the PPC `ftFunction` code the content ships**, rather than
reimplement each moveset in C. This is the only path that scales to all ~15 custom fighters.

## 1. The artifact

A fighter `.dat` (e.g. `PlSn.dat`) is an HSD archive with public symbols `ftDataSonic`, `itFunction`
and **`ftFunction`**. `ftFunction` (HSD archive header, big-endian) is:

| off | field |
|---|---|
| 0x00 | `code` — pointer to the relocatable PPC code |
| 0x04 | `instructionRelocTable` |
| 0x08 | `instructionRelocTableCount` |
| 0x0C | `functionRelocTable` — array of `{ReplaceThis, ReplaceWith}` (8 bytes each) |
| 0x10 | `functionRelocTableCount` |
| 0x14 | `codeSize` |

m-ex's `Init ftFunction.asm` (spec reference at `_build/m-ex/asm/m-ex/Init ftFunction.asm`, guest
`0x80068b40`) extracts the symbol, `Reloc`s it, then `Overload`s it into the engine, then flushes the
icache.

- **Reloc** rewrites embedded absolute addresses and self-relative branches in the code, driven by
  `instructionRelocTable`.
- **Overload** walks `functionRelocTable`:
  - top bit of `ReplaceThis` **clear** → *table-index* case: `Arch_FighterFunc[ReplaceThis][kind] =
    code + ReplaceWith`.
  - top bit **set** → *func-address* case: patch a `b <offset>` (opcode `0x48000000`) at the absolute
    guest address `ReplaceThis` to jump into the relocated code.

**`functionRelocTable` is a machine-readable to-do list**: it names exactly which engine slots a
fighter overrides and which engine functions it hooks. Coverage work is therefore content-driven, not
"all 46 slots upfront".

## 2. Memory model (the key simplification)

- Guest MEM1 (24 MB) is mapped at the literal native address `0x80000000`
  (`gw_runtime.c:GW_MEM1_BASE`). **Heap data — fighter structs, HSD objects, archive loads — lives in
  guest memory at its true guest address, so a guest pointer is directly dereferenceable natively**
  (big-endian fields via `gw_r32`/`gw_w32`/`gw_rf32`).
- **Game static globals** (`0x804xxxxx`) live in **native** memory (the retargeted exe), *not* in
  guest memory. Only these need a guest→native bridge.
- `rtoc` (r2) / m-ex's `OFST_*` slots and its `mexData`/`Arch_FighterFunc` tables: **keep them
  entirely in guest memory** — allocate a guest "mexData" region, set the interpreter's r2 to it.
  Then rtoc-relative loads/stores hit guest memory directly. **No bridge for rtoc.**
- `gw_apply_fixups` only byte-swaps linker-filled pointer slots; it does not translate addresses.

So only two things need the guest→native bridge: **(a) calls to game/SDK functions by absolute guest
address, (b) access to native static globals by absolute guest address.**

## 3. The incoming-call problem (engine → fighter override)

For interpreted code to override an engine behaviour, the engine call site must read the override
*indirectly*. `Arch_FighterFunc` has **46 slots** (`Header.s`: `onLoad` 0x00 … `GetTrailData` 0xB4).

- **11 slots already dispatched** via the existing `gw_Mex_GObjDispatch` surface
  (`pc/platform/gw.h`): onLoad, onDeath, onDestroy, onFrame, onAbsorb, onApplyHeadItem,
  onRemoveHeadItem, onMakeItemInvisible, onMakeItemVisible, onKnockbackEnter, onKnockbackExit.
- **~15 clean per-kind callback tables** need a new dispatch site each (mechanical): OnItemPickup,
  OnItemRelease/drop, onModelRender, onShadowRender, onActionStateChange, onReapplyAttr,
  onTwoEntryTable, MoveLogic, MoveLogicDemo, result-anim, GetTrailData, onUnknownMultijump, …
- **~12 Category-2 bespoke sites** (no clean table): onFloat (predicate), onDoubleJump, onZair,
  onLanding, F/U/D-Smash, onIntroL/R, onTaunt, onCatch, onWalljump, …
- **8 specials** (N/Hi/Lw + air) — routed through the per-kind action-state table, a different
  mechanism from the gobj-callback tables.

There is **no single existing funnel**, so full coverage is ~35 new sites. But for a given fighter the
`functionRelocTable` says which are actually needed — Sonic ≈ the 11 already done + MoveLogic +
specials + onActionStateChange + onLoad/onFrame.

## 4. The outgoing-call bridge (interpreted PPC → engine/SDK)

Interpreted code calls by absolute guest address (e.g. `branchl r12, 0x80380358`). In the port that
function is a native `gw_`-prefixed x86 function at an unrelated address. Options: build-time table
(best), runtime registry, trapping. **Recommended: build-time table.**

- `melee/config/GALE01/symbols.txt` gives guest address → symbol name.
- `melee-pc.map` (linked with `/BASE:0x10000000 /DYNAMICBASE:NO`) gives `gw_<name>` → native RVA.
- Pair by name → `guest_addr → native_fn` table, linked into the exe. Covers functions *and* static
  globals uniformly.
- m-ex-specific helpers with no vanilla symbol (`Reloc`, `Overload`, `itFunctionInit`, the `Arch_*`
  tables) are provided **natively** and registered at their m-ex guest addresses.

## 5. Execution strategy

Interpreter, not JIT: target is **32-bit** i686; Dolphin's JIT is x86-64-only. A Gekko-subset
interpreter in C is arch-neutral and reentrant.

- Instruction subset: integer (add/sub/mullw/mulli/divw/and/or/xor/nor/rlwinm/slwi/srwi/srawi/
  exts*/cmp*/cntlzw/mfspr/mtspr/mflr/mtlr), load/store (lwz/lhz/lha/lbz/stw/sth/stb/lwzx/stwx/lfs/
  stfs/lfd/stfd/lhbrx/stwbrx/…), branch (b/bl/bc/bclr/bctr/bctrl), float (fadds/fmuls/frsp/fcmpu/
  fsel/fctiwz/…), and paired-single `ps_*` where content needs it (`gekko_fp.c` already has the
  estimate ops).
- ~40–60 ops (integer+memory+branch+basic float) is the first working slice, ~800–1200 LOC; a
  complete-enough core is ~1500–2500 LOC.
- FPRs modeled as 64-bit (double) with `frsp`/single ops rounding to single; `ps_*` split the 64-bit
  union into two 32-bit floats.
- Guest stack (r1) in guest memory; r2 = guest mexData base; r13 if needed = guest SDA base.

## 6. Integration point

After `ftData_8008572C(kind)` has loaded the `.dat` (`src/melee/ft/ftdata.c`), i.e. at the end of
that function or right after `fp->ft_data = gFtDataList[fp->kind]`
(`src/melee/ft/fighter.c`). Gate on `gw_Mex_Enabled("mex_ftfunction")` and on the archive actually
containing an `ftFunction` public symbol.

## 7. Phased plan

1. **Interpreter core + guest memory + bridge seam** — integer/memory/branch subset; a native
   `gw_ppc_call(guest_fn, r3..)` entry; memory access through guest (big-endian) accessors.
2. **Smallest proof** — a hand-built PPC test blob in the in-engine test suite (`--test`): a function
   that calls one bridged native function and stores a result to a guest address; assert the side
   effect. Proves core + memory + bridge.
3. **Blob loader** — `Reloc` + `Overload` over a real `ftFunction` symbol from `PlSn.dat`.
4. **Install into the OnLoad slot** for `Ft_Kind_Sonic`, boot `MELEE_TARGET_TEST=sonic`, observe.
5. **Grow coverage** driven by Sonic's `functionRelocTable` (specials, MoveLogic, onActionStateChange…).
6. **Float/paired-single** as content demands.

## 8. Traps

- **Big-endian guest memory**: every interpreted load/store must byte-swap. Forgetting it is the
  classic silent corruption.
- **CR fields**: `cmpwi` sets CR0; branches test CR bits — a wrong CR model gives wrong branches that
  never crash.
- **LR/CTR save-restore** across the native boundary; the interpreter must be reentrant (native code
  can call back into interpreted code through a dispatch site).
- **`sret`/struct-by-value ABI** at bridge calls (see `gw.h`); a wrong sret size corrupts silently.
- **The func-address case** patches a guest instruction word — in the port that address maps to native
  code we must not write. Intercept it and re-express as a native hook registration instead.
- **icache flush is a no-op natively** (we never execute guest bytes as x86); with an interpreter,
  self-modifying patches just work because decodes are re-read.
- **Address validation**: interpreter-generated loads must be bounds-checked and raise a clean panic
  with the guest PC + EA, not a bare native fault.
- `rtoc` (r2) unset → `OFST_*` loads read garbage near NULL (usually a crash, sometimes silent zeros).
