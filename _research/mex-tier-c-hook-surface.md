# m-ex "Tier C" hook surface — native API design

Status: design only. No code was changed. No linker run, no game launched, nothing
committed.

This document tells an implementer how to expose m-ex's **Tier C** surface natively.
"Tier C" (from `_research/mex-content-expansion.md` §5) is the set of m-ex features that
depend on executing PowerPC stored inside `.dat` files at runtime — which this port
cannot do, because it retargets PPC→x86 at **build** time and has no PPC interpreter/JIT.
Every Tier C hook must therefore be re-expressed as a native C callback surface.

Grounding: all claims are backed by (a) the m-ex assembly under
`/mnt/c/gdm/_build/m-ex/asm/m-ex/`, (b) the decomp source under `src/melee/`, and (c)
`config/GALE01/symbols.txt`. Address→symbol resolution was done with
`tools/mex_port/resolve_patches.py` plus direct `ppc_disasm.py` disassembly of
`_build/orig_main.dol` to recover the instruction each patch replaces.

---

## 0. The one mechanism that explains every "Fighter On*" hook

m-ex's fighter hooks are not calls inserted from nowhere. In the vanilla DOL, nearly all
of them are **per-character function-pointer tables indexed by `fp->kind` (internal
character ID, `0..Ft_Kind_Max-1`)**. The vanilla pattern at every clean site is:

```asm
lwz  r4,4(rXX)         ; r4 = fp->kind
addis r3,r0,-32708     ; r3 = 0x803C0000
addi r0,r3,<lo16>      ; r0 = table base  (0x803C0000 + lo16)   <-- patched
slwi r3,r4,2           ; r3 = kind*4
add  r3,r0,r3          ; r3 = &table[kind]
lwz  r12,0(r3)         ; r12 = table[kind]
cmpli r0,r12,0         ; if (r12 != NULL)
beq  skip
mtctr r12 / bctrl      ;   call r12(gobj)
```

m-ex replaces **one instruction** — the `addi r0,r3,<lo16>` that computes the table base —
with a load of m-ex's own table pointer (from an rtoc slot `OFST_*` or from the
`Arch_FighterFunc` table in the `MxDt` archive). The surrounding `slwi / add / lwz /
cmpli / bctrl` is left intact, so m-ex's pointer must itself be a *per-kind table* whose
`[kind]` entry is the replacement function (or NULL).

Consequences for this design:

1. **Every hook is semantically "a per-fighter function pointer table indexed by
   `fp->kind`", invoked with the fighter's `HSD_GObj*` (or `Fighter*`) as first
   argument.** There is one slot per (hook, kind). m-ex is single-slot: a custom
   fighter's callback *replaces* the vanilla one.
2. **Most families already have a clean decomp call site** — a line of the form
   `if (ftData_XXX[fp->kind]) ftData_XXX[fp->kind](gobj);`. For those, porting the hook is
   *not* a call-site change at all: it is a **write into the existing `ftData_XXX` slot**.
3. A smaller set has **no such table** in vanilla — m-ex injects a manual per-kind lookup
   plus a call (or a control-flow override). Those need a *new* native call site.

`Arch_FighterFunc` (`asm/m-ex/Header.s`) and the rtoc offsets (`OFST_FighterOnLoad=0x30`,
`OFST_FighterOnSpawn=0x34`, `OFST_onFloat=0x9C`, `OFST_onDoubleJump=0xA0`,
`OFST_onZair=0xA4`, `OFST_onLanding=0xA8`, `OFST_onWallJump=0xAC`, `OFST_onFSmash=0xB4`,
`OFST_onUSmash=0xB8`, `OFST_onDSmash=0xBC`, …) are all just two representations of the
same thing — a pointer to a per-kind table — and are populated at boot by
`Init ftFunction.asm` / `Load MxDt.asm`. This design ignores that plumbing entirely and
exposes the tables the decomp already calls.

---

## 1. Tier C families → decomp mapping

### 1.1 Clean 1:1 families — register into an existing `ftData_*[Ft_Kind_Max]` table

These need **no call-site change**. The decomp already does
`ftData_XXX[fp->kind](gobj)`; the port exposes a way to write a native function pointer
into `ftData_XXX[kind]`.

All tables are declared in `src/melee/ft/ftdata.h` (addresses are the `// 3Cxxxx` comment
on each line). Signatures come from `src/melee/ft/forward.h`.

| m-ex family | patch file (`asm/m-ex/…`) | insn addr | decomp table (addr) | type (typedef) | signature | call site (file:line) |
|---|---|---|---|---|---|---|
| **OnLoad** | `Fighter OnLoad/AllocateAndInitPlayer.asm` | `0x800690F0` | `ftData_OnLoad` (`0x803C1154`) | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/fighter.c:890` (`Fighter_Create`) |
| OnLoad (results screen) | `Fighter OnLoad/AllocateAndInitPlayer - Results Screen.asm` | `0x800BEA28` | `ftData_OnLoad` | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/ftdemo.c:120` (`ftDemo_CreateFighter`) |
| **OnDeath** | `Fighter OnDeath/InitializePlayerDataValues.asm` | `0x80068660` | `ftData_OnDeath` (`0x803C11D8`) | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/fighter.c:557` (`Fighter_UnkProcessDeath_80068354`) |
| **OnDestroy** | `Fighter OnDestroy/Destroy.asm` | `0x8006DAE8` | `ftData_OnUserDataRemove` (`0x803C125C`) | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/fighter.c:3124` (`Fighter_Unload_8006DABC`) |
| **OnFrame** | `Fighter OnFrame/Fighter_OnFrame.asm` | `0x8006AA28` | `ftData_UnkMotionStates3` (`0x803C1DB4`) | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/fighter.c:1656` (`Fighter_8006A360`) |
| **OnAbsorb** | `Fighter OnAbsorb/Absorb.asm` | `0x8006D654` | `ftData_OnAbsorb` (`0x803C1808`) | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/fighter.c:2979` (`Fighter_ProcessHit_8006D1EC`) |
| **OnApplyHeadItem** | `Fighter OnApplyHeadItem/Fighter_OnApplyHeadItem.asm` | `0x8007FB9C` | `ftData_UnkMotionStates1` (`0x803C1BA4`) | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/ftcommon.c:1515` (`ftCommon_8007FA58`) |
| **OnRemoveHeadItem** | `Fighter OnRemoveHeadItem/Fighter_OnRemoveHeadItem.asm` | `0x8007F918` | `ftData_UnkMotionStates2` (`0x803C1C28`) | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/ftcommon.c:1503` (`ftCommon_8007F8E8`) |
| **OnItemPickup** (fighter-specific) | `Fighter OnItem/onItemCatch.asm` + `onItemPickup.asm` | `0x80094860`, `0x80094924` | `ftData_OnItemPickupExt` (`0x803C188C`) | `Fighter_ItemEvent` | `void(*)(HSD_GObj*, bool)` | `ft/kinds/ftCommon/ftpickupitem.c:262` (two functions: `ftpickupitem_80094818`, `ftpickupitem_800948A8`) |
| OnItemPickup (common) | `Fighter OnItem/onItemCatch2.asm` | `0x8007E7F0` | `ftData_OnItemPickup` (`0x803C1A9C`) | `Fighter_ItemEvent` | `void(*)(HSD_GObj*, bool)` | `ft/ftcommon.c:1046` (`ftCommon_8007E7E4`) |
| OnItemRelease (common) | `Fighter OnItem/onItemRelease.asm` | `0x8007E740` | `ftData_OnItemDrop` (`0x803C1B20`) | `Fighter_ItemEvent` | `void(*)(HSD_GObj*, bool)` | `ft/ftcommon.c:1038` (`ftCommon_8007E6DC`) |
| OnItemRelease (fighter-specific) | `Fighter OnItem/onItemRelease2.asm` | `0x8007E7A8` | `ftData_OnItemDropExt` (`0x803C1A18`) | `Fighter_ItemEvent` | `void(*)(HSD_GObj*, bool)` | `ft/ftcommon.c:1028` (`ftCommon_8007E79C`) |
| **OnItemVisibility** (invisible) | `Fighter OnItemVisibility/onSetItemInvisible.asm` + `onSetItemInvisible2.asm` | `0x8007F61C`, `0x8007F59C` | `ftData_OnItemInvisible` (`0x803C1910`) | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/ftcommon.c:1413` (`ftCommon_8007F5CC`, `ftCommon_8007F578`) |
| OnItemVisibility (visible) | `Fighter OnItemVisibility/onSetItemVisible.asm` | `0x8007F650` | `ftData_OnItemVisible` (`0x803C1994`) | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/ftcommon.c:1429` (`ftCommon_8007F5CC`) |
| **OnKnockback** (enter) | `Fighter OnKnockback/OnKnockback.asm` | `0x8007F830` | `ftData_OnKnockbackEnter` (`0x803C1CAC`) | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/ftcommon.c:1477` (`ftCommon_8007F824`) |
| **OnKnockbackExit** | `Fighter OnKnockbackExit/OnKnockbackExit.asm` | `0x8007F878` | `ftData_OnKnockbackExit` (`0x803C1D30`) | `HSD_GObjEvent` | `void(*)(HSD_GObj*)` | `ft/ftcommon.c:1485` (`ftCommon_8007F86C`) |
| **OnRender** (model) | `Fighter OnRender/Model.asm` + `Model - Offscreen.asm` | `0x80080BA0`, `0x80080D9C` | `ftData_UnkMtxFunc0` (`0x803C20CC`) | `Fighter_UnkMtxEvent` | `void(*)(HSD_GObj*, int, Mtx)` | `ft/ftdrawcommon.c:251,297` (`ftDrawCommon_800805C8`, `ftDrawCommon_80080C28`) |
| **OnRender** (shadow) | `Fighter OnRender/Shadow.asm` + `Shadow2.asm` + `Shadow3.asm` | `0x8007512C/90/F8` | `ftData_UnkIntBoolFunc0.model_events` (`0x803C2150`) | `Fighter_ModelEvent` | `void(*)(Fighter*, int, bool)` | `ft/ftparts.c:738,746,755` (`ftParts_800750C8`) |

The typedefs (from `src/melee/ft/forward.h`):
- `HSD_GObjEvent` — standard sysdolphin `void (*)(HSD_GObj*)`.
- `Fighter_ItemEvent` — `void (*)(HSD_GObj* gobj, bool arg1)` (forward.h:83).
- `Fighter_UnkMtxEvent` — `void (*)(HSD_GObj* gobj, int arg1, Mtx vmtx)` (forward.h:85).
- `Fighter_ModelEvent` — `void (*)(Fighter* fp, int arg1, bool arg2)` (forward.h:84);
  `ftData_UnkIntBoolFunc0` is `ftData_UnkModelStruct { Fighter_ModelEvent
  model_events[Ft_Kind_Max]; }` (`types.h:1824`).

**Two non-1:1 notes to record, not paper over:**

- `ftData_UnkIntBoolFunc0` (OnRender shadow) has symbol size `0x108` (= 264 = 2×132), but
  the declared struct is a single `Fighter_ModelEvent[33]` = `0x84` bytes. The symbol is
  two per-kind arrays' worth of space. The OnRender/shadow table shape must be
  double-checked against `ftdata.c:1283` before registering (see §8). It does not block
  the other families.
- `OnItemPickup` and `OnItemPickupExt` are **two different tables** (two call sites, two
  spellings of the same event family), as are `OnItemDrop`/`OnItemDropExt`. m-ex patches
  both, so a faithful port must expose both slots. This is a deliberate 2-slot mapping, not
  a guess.

### 1.2 Bespoke families — no clean vanilla table; need a new native call site

These m-ex patches either (a) inject a manual per-kind lookup + call into the function
epilogue/middle, (b) replace an entire small predicate function at its entry, or (c)
override a byte/control-flow decision. None map to a single existing `ftData_*` table, so
each needs a **new** `TARGET_PC`-guarded call inserted at the exact decomp location.

| m-ex family | patch file | insn addr | decomp function | file | hook shape |
|---|---|---|---|---|---|
| **OnLanding** | `Fighter OnLanding/onLanding.asm` | `0x80069924` | `Fighter_ChangeMotionState` | `ft/fighter.c:937` | per-kind `void(*)(HSD_GObj*)`, call-if-present when entering a grounded state |
| **OnCatch** | `Fighter OnCatch/OnCatch.asm` | `0x800D8CB4` | `ftCo_800D8C54` | `ft/kinds/ftCommon/ftCo_Catch.c` | per-kind `void(*)(HSD_GObj*)`, call-if-present (epilogue inject) |
| **OnTaunt** | `Fighter OnTaunt/OnTaunt.asm` | `0x800DECDC` | `ftCo_800DEBD0` | `ft/kinds/ftCommon/ftCo_AppealS.c` | per-kind `void(*)(HSD_GObj*)`, call-if-present (epilogue inject) |
| **OnIntro L** | `Fighter OnIntro/OnIntroL.asm` | `0x800BF0EC` | `ftCo_800BF034` | `ft/ft_0BF0.c` | per-kind `void(*)(HSD_GObj*)`, call-if-present (epilogue inject) |
| **OnIntro R** | `Fighter OnIntro/OnIntroR.asm` | `0x800BF20C` | `ftCo_800BF108` | `ft/ft_0BF0.c` | per-kind `void(*)(HSD_GObj*)`, call-if-present (epilogue inject) |
| **OnSmash F** | `Fighter OnSmash/OnFSmash.asm` | `0x8008C360` | `decideFighter` (local, `0x8008C348`) | `ft/kinds/ftCommon/ftCo_AttackS4.c` | per-kind `void(*)(HSD_GObj*)`, call-if-present then skip vanilla |
| **OnSmash U** | `Fighter OnSmash/OnUSmash.asm` | `0x8008C900` | `ftCo_AttackHi4_CheckInput` | `ft/kinds/ftCommon/ftCo_AttackHi4.c` | per-kind `void(*)(HSD_GObj*)` |
| **OnSmash U (alt)** | `Fighter OnSmash/OnUSmash2.asm` | `0x8008C9F0` | `ftCo_AttackHi4_CheckInputNoD0` | `ft/kinds/ftCommon/ftCo_AttackHi4.c` | per-kind `void(*)(HSD_GObj*)` |
| **OnSmash D** | `Fighter OnSmash/OnDSmash.asm` | `0x8008CC14` | `ftCo_AttackLw4_CheckInput` | `ft/kinds/ftCommon/ftCo_AttackLw4.c` | per-kind `void(*)(HSD_GObj*)` |
| **OnDoubleJump** | `Fighter OnDoubleJump/DJ.asm` | `0x800CBA30` | `ftCo_JumpAerial_CheckInput` | `ft/kinds/ftCommon/ftCo_JumpAerial.c` | per-kind `void(*)(HSD_GObj*)`, call-if-present else vanilla DJ check |
| **OnZair** | `Fighter OnZair/Zair.asm` | `0x800C3B54` | `ftCo_800C3B10` | `ft/ft_0D4D.c` | per-kind `void(*)(HSD_GObj*)`, call-if-present (tether detect) |
| **OnWalljump** | `Fighter OnWalljump/onWallJump.asm` | `0x800816C4` | `ftWallJump_8008169C` | `ft/ftwalljump.c` | per-kind **byte** gate (not a fn ptr): if `byte[kind]!=0` skip walljump |
| **OnFloat** (Down+XY) | `Fighter OnFloat/onFloat - Down+XY.asm` | `0x8011BA54` | `ftPe_8011BA54` | `ft/kinds/ftPeach/ftpeachfloat.c:33` | **replaces whole `bool` predicate** `bool(*)(HSD_GObj*)` |
| **OnFloat** (JumpPeak) | `Fighter OnFloat/onFloat - JumpPeak.asm` | `0x8011BAD8` | `ftPe_8011BAD8` | `ft/kinds/ftPeach/ftpeachfloat.c:44` | **replaces whole `bool` predicate** `bool(*)(HSD_GObj*)` |

Notes on the two float hooks: `ftPe_8011BA54` / `ftPe_8011BAD8` are tiny `bool` predicates
(`ftpeachfloat.c:33` / `:44`). m-ex patches them **at their entry** (both disassemble to
`mfspr r0,lr` prologues), so the m-ex hook *is* the function — the hook's return value is
the predicate result. This is the one family where the **return value** flows directly
into game logic (see §2.4). `OnZair`, `OnDoubleJump`, `OnSmash*`, and `OnWalljump` are the
other return-/control-flow-sensitive ones: the hook's presence (or byte) decides whether
vanilla logic runs.

### 1.3 Extension-function and data families (Tier C, but not "fighter callbacks")

These are the remaining Tier C entries named in the goal. They are the `.dat`-code and
`.dat`-table mechanisms, not per-fighter callbacks, and they deserve a **separate** design
(they are the "content-expansion data pipeline", overlapping Tier B). Grounding for each:

| Family | what it is (grounded in m-ex sources) |
|---|---|
| **xFunction** | Arbitrary code stored in `.dat`, relocated, indexed by `XFunctionLookup` (max 30; `asm/m-ex/Header.s`). Consumed on scene transition: `xFunction/ClearOnMajorExit.asm` patches `runGameMode` (`gm/gm_1A3F.c`), `ClearOnMinorExit.asm` patches `gm_801A4014`. Native form: a registered list of C functions run on major/minor exit. |
| **ftFunction** | Per-fighter arbitrary code, the *mechanism* behind §1.1: `Init ftFunction.asm` (`@ 0x80068B40`, inside `Fighter_UnkInitLoad_80068914`) locates the `"ftFunction"` symbol in the fighter's `.dat`, relocates it, and runs the `Overload` routine to replace entries in the per-kind tables. In the native port this is *replaced* by §2's registration API — there is nothing left to "port". |
| **grFunction** | Per-stage function table (`Arch_grFunction`, `asm/m-ex/Header.s`), overloaded by `SSS Expansion/Init grFunction.asm` (`@ 0x801C60C8`). Call sites: `SSS Expansion/grFunction References/*.asm` → `StageCreate_map_gobj`, `StageFileLoad`, `StageInitBG`, `StageInitLighting`, `StageOnGO`, `StageOnStart`, moving-collision-points, `Stage_Init`, `Unk`. Native form: a per-stage callback table exactly like §1.1 but keyed by stage ID. |
| **itFunction** | Per-item function table, overloaded by `Standalone Functions/Init itFunction.asm` (`itFunctionInit`, `@ 0x803D7070`), which maps internal item IDs → item tables and overwrites their function pointers. Native form: a per-item callback table keyed by item ID. |
| **mexSelectChr** | CSS character-select expansion. `CSS Expansion/mexSelectChr/Load mexSelectChr.asm` (`@ 0x80266984`) loads a `"mexSelectChr"` symbol from the `.dat`; `Init mexSelectChr.asm` (`@ 0x802647FC`) scales the cursor radii from `MenuParam` and rebuilds the CSS icon struct. Native form: Tier B data tables (CSS icon list) + a cursor-scale parameter table — data, not a hook. |
| **mexMapData** | Stage map data (`OFST_mexMapData = -0x4A08` rtoc; `Arch_Map_StageIDs`, `Arch_Map_Audio`, `Arch_Map_LineTypeData`, `Arch_Map_StageItemLookup`, `Arch_Map_StageNames`, `Arch_Map_Playlists` in `Header.s`). Native form: Tier B data tables. |
| **mexMenu** | Main-menu expansion: `MenuDef`/`OptDef` tables with a per-option `MenuDef_Callback` (`@ 0x10`), consumed via `MenuThink` (`0x803D7090`) and `MainMenu Expansion/Define Table - *.asm`. Native form: a menu-definition table where each option's callback is an ordinary C function pointer (one more table hook, but scoped to the menu subsystem). |

**Recommendation:** §1.1 and §1.2 are *this* design. §1.3 (xFunction/grFunction/
itFunction/mexSelectChr/mexMapData/mexMenu) is a parallel "extension data + callback
tables" design and should be split out — it shares the §2 registration mechanics but is
driven by content data, not by fixed hook points.

---

## 2. Native API shape

### 2.1 Placement and the ABI boundary

Hooks live at the **game↔platform boundary** described in `pc/platform/gw.h`. Recall the
contract (gw.h header comment):

- scalars (ints, floats, pointers) pass **natively** in registers;
- game memory stays **big-endian**; every multi-byte field behind a game pointer must be
  read/written with `gw_r8/r16/r32/r64`, `gw_rf32`, `gw_rptr` etc.;
- a function the game calls is an ordinary symbol named `gw_<name>` (gwtool maps the
  unprefixed name onto it).

Therefore a native hook is an ordinary C function (no special prologue), defined in the
**platform layer** (`pc/platform/`) or in a game TU under `#if defined(TARGET_PC)`, that
receives the fighter's `HSD_GObj*`/`Fighter*` as a real pointer and reads/writes fields
through the `gw_` accessors. This is exactly the existing shim pattern (`gw_TTMod_*`,
`gw_TestTargetTestCKind` in `gw_runtime.c`).

### 2.2 Declaration (new header `pc/platform/gw_hooks.h`, included by `gw.h`)

```c
/* ---- m-ex Tier C fighter hook surface (native re-expression) ----------------------- */

/* One slot per (hook, fighter kind). kind is the internal CharacterKind (ft/forward.h,
 * Ft_Kind_*), 0..Ft_Kind_Max-1. fn may be NULL to clear. */
typedef enum {
    GW_HOOK_ON_LOAD,          /* ftData_OnLoad                  void(*)(HSD_GObj*)        */
    GW_HOOK_ON_DEATH,         /* ftData_OnDeath                 void(*)(HSD_GObj*)        */
    GW_HOOK_ON_DESTROY,       /* ftData_OnUserDataRemove        void(*)(HSD_GObj*)        */
    GW_HOOK_ON_FRAME,         /* ftData_UnkMotionStates3        void(*)(HSD_GObj*)        */
    GW_HOOK_ON_ABSORB,        /* ftData_OnAbsorb                void(*)(HSD_GObj*)        */
    GW_HOOK_ON_APPLY_HEADITEM,/* ftData_UnkMotionStates1        void(*)(HSD_GObj*)        */
    GW_HOOK_ON_REMOVE_HEADITEM,/* ftData_UnkMotionStates2       void(*)(HSD_GObj*)        */
    GW_HOOK_ON_KNOCKBACK_ENTER,/* ftData_OnKnockbackEnter       void(*)(HSD_GObj*)        */
    GW_HOOK_ON_KNOCKBACK_EXIT,/* ftData_OnKnockbackExit         void(*)(HSD_GObj*)        */
    GW_HOOK_ON_ITEM_INVISIBLE,/* ftData_OnItemInvisible         void(*)(HSD_GObj*)        */
    GW_HOOK_ON_ITEM_VISIBLE,  /* ftData_OnItemVisible           void(*)(HSD_GObj*)        */
    /* ... item/matrix/shadow variants take extra args; see §2.4 ... */
    /* Bespoke families (§1.2) backed by NEW native tables, dispatched from a new call
     * site; see §2.5. */
    GW_HOOK_ON_LANDING,       /* void(*)(HSD_GObj*)   new call site: fighter.c (ChangeMotionState) */
    GW_HOOK_ON_CATCH,         /* void(*)(HSD_GObj*)   new call site: ftCo_Catch.c              */
    GW_HOOK_ON_TAUNT,         /* void(*)(HSD_GObj*)   new call site: ftCo_AppealS.c            */
    GW_HOOK_ON_INTRO_L,       /* void(*)(HSD_GObj*)   new call site: ft_0BF0.c                 */
    GW_HOOK_ON_INTRO_R,       /* void(*)(HSD_GObj*)   new call site: ft_0BF0.c                 */
    GW_HOOK_ON_FSMASH,        /* void(*)(HSD_GObj*)   new call site: ftCo_AttackS4.c           */
    GW_HOOK_ON_USMASH,        /* void(*)(HSD_GObj*)   new call site: ftCo_AttackHi4.c          */
    GW_HOOK_ON_DSMASH,        /* void(*)(HSD_GObj*)   new call site: ftCo_AttackLw4.c          */
    GW_HOOK_ON_DOUBLE_JUMP,   /* void(*)(HSD_GObj*)   new call site: ftCo_JumpAerial.c         */
    GW_HOOK_ON_ZAIR,          /* void(*)(HSD_GObj*)   new call site: ft_0D4D.c                 */
    GW_HOOK_ON_FLOAT,         /* bool(*)(HSD_GObj*)   replaces ftPe_8011BA54/8011BAD8         */
    GW_HOOK_ON_WALLJUMP,      /* u8 gate               new call site: ftwalljump.c             */
} GwMexHook;
```

The header also declares the registration entry points and the per-hook *native* tables.

### 2.3 Registration and invocation — the two shapes

**Shape A — table write (families in §1.1).** The decomp call site already exists and
already calls through the game table. Registration is a single byte-swapped store into the
existing slot. Provided as a typed helper:

```c
/* store a native fn into slot [kind] of a game-resident (big-endian) pointer table */
void gw_mex_set_event_ptr(void **game_table, int kind, void *native_fn); /* gw_wptr */
/* typed wrappers */
void gw_mex_set_gobj_event(HSD_GObjEvent *tbl, int kind, HSD_GObjEvent fn);
void gw_mex_set_item_event(Fighter_ItemEvent *tbl, int kind, Fighter_ItemEvent fn);
void gw_mex_set_mtx_event(Fighter_UnkMtxEvent *tbl, int kind, Fighter_UnkMtxEvent fn);
void gw_mex_set_model_event(Fighter_ModelEvent *tbl, int kind, Fighter_ModelEvent fn);
```

The invocation is the **existing decomp line** — no change. For example OnLoad remains
`if (ftData_OnLoad[fp->kind]) ftData_OnLoad[fp->kind](gobj);` in `Fighter_Create`. The
native pointer stored via `gw_wptr` is loaded (byte-swapped to native) and called by the
gwtool-rewritten indirect call site, exactly as the game's own `gw_`-prefixed functions
are called.

**Shape B — new call site (families in §1.2).** A `TARGET_PC` block is added at the exact
decomp location, backed by a native-side per-kind table in `gw_runtime.c`:

```c
/* fighter.c — Fighter_ChangeMotionState, inside the "entered a grounded state" branch */
#if defined(TARGET_PC)
    gw_mex_dispatch(GW_HOOK_ON_LANDING, fp->kind, gobj);   /* + the "was grounded" guard */
#endif
```

`gw_mex_dispatch` lives in the platform layer and owns the native tables:

```c
/* platform-side: one function-pointer slot per (hook, kind). Table of tables, all NULL
 * by default. Bespoke hooks only. */
void gw_mex_dispatch(GwMexHook hook, int kind, HSD_GObj *gobj); /* calls table[hook][kind](gobj) if set */
```

Registration for Shape B is:

```c
void gw_mex_hook_set(GwMexHook hook, int kind, void (*fn)(HSD_GObj*));
/* special-cased: bool-predicate (OnFloat) and byte-gate (OnWalljump) variants */
void gw_mex_hook_set_bool(GwMexHook hook, int kind, bool (*fn)(HSD_GObj*));
```

### 2.4 Calling convention and return values

- **Arguments.** The first argument is always the fighter's `HSD_GObj*` (or `Fighter*` for
  OnRender/shadow, matching the table typedefs). Extra arguments follow the decomp
  typedef exactly: `Fighter_ItemEvent` takes `(gobj, bool)`, `Fighter_UnkMtxEvent` takes
  `(gobj, int, Mtx)`, `Fighter_ModelEvent` takes `(Fighter*, int, bool)`. They are passed
  natively; the hook reads the fighter struct fields it needs through `gw_` accessors.
- **Return value.** Only two families use the hook's return value:
  1. **OnFloat** (`ftPe_8011BA54`/`ftPe_8011BAD8`) — the hook *is* the predicate; it
     returns `bool` ("should Peach float"), which `ftCo_JumpAerial.c` / `ftCo_Fall.c` etc.
     consume. The native call site is a direct replacement: the `TARGET_PC` build calls
     the registered `bool(*)(HSD_GObj*)` (or falls back to the vanilla predicate body when
     none is registered).
  2. **OnWalljump** — m-ex uses a per-kind **byte** (`lbzx r3,r4,r3`), not a function
     pointer: non-zero means "skip walljump". Native form: a `u8 gate[kind]` table; the
     call site becomes `if (gate[kind] == 0) { /* vanilla walljump */ }`.
  All other hooks are `void` and their return value is ignored — matching the vanilla
  `cmpli/beq/mtctr/bctrl` pattern where m-ex calls `bctrl` and discards `r3`.

### 2.5 The `Init ftFunction.asm` mechanism has no native analogue to write

`Init ftFunction.asm` exists to run PPC from a `.dat`. Its *observable effect* is exactly
"overwrite slots in the per-kind tables", which Shape A reproduces by a direct table
write. There is **no** native counterpart to the `Reloc`/`Overload`/`FlushCache` code
itself — that is dead machinery once code is compiled C. Documenting this prevents an
implementer from trying to "port" the relocator.

---

## 3. Interaction with `gw_Mex_Enabled` and per-hook gating

`gw_Mex_Enabled(name)` (`pc/platform/gw_runtime.c:964`) reads the `MELEE_MEX` env var +
`mods\mex.txt`; game C calls the unprefixed `Mex_Enabled`, mapped by gwtool to
`gw_Mex_Enabled`. It is a **string → bool** registry (lowercased, 64 features max), not a
code table.

Design rule — **hooks are gated at registration time, not at dispatch time**:

1. Each hook has a canonical feature name (e.g. `mex-onframe`, `mex-onload`, …). A mod
   registers a hook only if `Mex_Enabled("mex-onframe")` is true. Registration happens
   once, lazily, in the platform layer (same "read env once and cache" pattern as
   `gw_mex_load`), or from a game TU at a fixed init point (`Fighter_Create` for OnLoad,
   or a one-time init for the rest).
2. **Shape A** (table write): if the feature is disabled, the slot is simply never written,
   so the decomp keeps its vanilla `NULL`/vanilla pointer and behaviour is byte-for-byte
   the original. No per-frame `Mex_Enabled` check is added to any hot path.
3. **Shape B** (new call site): the `TARGET_PC` dispatch is compiled in, but
   `gw_mex_dispatch` short-circuits on an all-NULL table (a single pointer fetch + NULL
   test). A per-hook `Mex_Enabled` string lookup is **not** done per call — the feature
   string is checked once at registration, and the presence/absence of a non-NULL slot is
   the runtime flag.
4. **Individual gating is required, not optional.** The port's convention (README +
   `_research/mex-content-expansion.md`) is that every ported behavior is opt-in and
   attributed. Expose a per-family flag; do **not** put all Tier C hooks behind one
   catch-all flag, because OnFrame/OnRender are hot and a single master switch would force
   a global code path change to flip one hook.

Net: the existing flag mechanism is reused unchanged. The only addition is a registration
entry point that reads `Mex_Enabled("<feature>")` once and writes the slot.

---

## 4. Ordering / priority semantics

m-ex is **single-slot**: one function pointer per (hook, kind); a custom fighter's
callback *replaces* the vanilla one. There is no chain. To stay faithful (and because the
decomp tables are single-slot), the default is:

- **Shape A**: last registration wins for a given `(hook, kind)`. This matches m-ex's
  "overload" exactly. Multiple independent mods targeting the same `(hook, kind)` would
  collide — which is also true in m-ex (one `.dat` per character wins).
- **Shape B**: same default (one slot per `(hook, kind)`), but because `gw_mex_dispatch`
  owns the table, it can cheaply be extended to a **small fixed chain** (e.g. 4 slots with
  a priority int) if multi-mod composition is later required. Recommended only for the
  low-frequency bespoke hooks, not for OnFrame/OnRender.

**Recommended semantics to document now:**
1. Priority is **per (hook, kind)**, never global.
2. A registration of `NULL` clears the slot (needed for teardown, §5).
3. If a chain is added, order is registration order (FIFO) unless an explicit priority
   `int` is supplied; higher priority runs first; the vanilla behavior is the implicit
   lowest-priority "default" for the bespoke override hooks (OnSmash/OnDoubleJump/OnZair).
4. **Do not** chain the `bool`-predicate hooks (OnFloat) or the byte gate (OnWalljump) —
   their semantics are single-decision, not "everyone runs".

---

## 5. Risks

### 5.1 Performance (hot paths)

- **OnFrame** runs once per fighter per frame (`Fighter_8006A360`, registered as a GObj
  proc). At 60 Hz, 4 fighters = **240 calls/s** — negligible. The cost added by Shape A is
  **zero** (the call site already exists; registration only changes the pointer that was
  already loaded). Shape B adds one indirect call + NULL test.
- **OnRender (model/shadow)** runs per fighter per frame per view, and the model hook
  takes an `Mtx` by pointer. Still small (~hundreds of calls/s), but a hook that mutates
  the matrix or allocates is a footgun — document that render hooks must not allocate or
  re-enter the draw state.
- The one real hot-path constraint: **never put a `Mex_Enabled` string lookup on the
  per-call path** (§3). String hashing/find per frame per fighter is the only meaningful
  regression risk and it is avoided by gating at registration.

### 5.2 Lifetime / teardown

- Hooks are per-fighter and statically registered; there is no dynamic `.dat` load/unload
  to mirror. The natural teardown is `Fighter_Unload_8006DABC` (`ftData_OnUserDataRemove`),
  which already runs per-fighter destruction. Any hook that allocates per-fighter state
  must free it in its own OnDestroy registration (or via `ftData_OnUserDataRemove`).
- On **scene/mode exit** the fighters are destroyed and recreated; there is no need to
  reset the tables themselves (they are static data), only per-fighter heap state.
- Registration should be idempotent and cheap enough to re-run per `Fighter_Create` if the
  mod opts to (in case a later content load wants to re-register). Cache the
  `Mex_Enabled` result so re-registration is a compare-and-store.

### 5.3 Failure isolation

- A misbehaving hook runs on the game thread. The port's existing
  `gw_unhandled_exception` SEH handler (`gw_runtime.c`) already turns a hook fault into a
  logged address + `.map` RVA + frame walk; it will not silently take down the process
  without a trace. That is the minimum guarantee.
- Stronger isolation is **out of scope for v1** but should be stated as a contract:
  hooks are trusted C, same trust domain as the engine. A per-call `__try/__except`
  wrapper around `gw_mex_dispatch` is possible but costs an SEH frame on hot paths — do
  **not** enable it for OnFrame/OnRender; if added, apply it only to the low-frequency
  bespoke hooks.
- The biggest *silent* corruption risk is a hook that writes game memory with a native
  (host-endian) store instead of `gw_w32`/`gw_wf32`. This is the same hazard every shim in
  `pc/platform` already carries, and the mitigations are the same: expose only the `gw_`
  accessors in the hook header, and put a comment at every hook typedef spelling out that
  game memory is big-endian.

### 5.4 Layout hazard on the game-data tables

`ftData_OnLoad` etc. are game-resident globals whose address/layout is pinned by the
matching build. Writing a slot is safe (same size as the existing pointer); **do not**
resize or relocate these tables on the PC port without the `ASSERT_SIZE`/layout
verification called out for `lbHeap` in `mex-content-expansion.md` §6.1. The hook surface
needs no such change.

---

## 6. Worked example — `OnFrame`, end to end

### 6.1 Decomp call site (already exists)

`src/melee/ft/fighter.c:1656`, inside `Fighter_8006A360` (the per-frame fighter proc):

```c
if (ftData_UnkMotionStates3[fp->kind]) {
    ftData_UnkMotionStates3[fp->kind](gobj);
}
```

`ftData_UnkMotionStates3` is `HSD_GObjEvent ftData_UnkMotionStates3[Ft_Kind_Max]`
(`ftdata.h:50`, `/* 3C1DB4 */`). This is the m-ex `onFrame` hook point: the
`Fighter OnFrame/Fighter_OnFrame.asm` patch at `0x8006AA28` replaces the `addi r0,r3,7604`
(table-base compute for `0x803C1DB4`) with a load of `Arch_FighterFunc_onFrame`.

### 6.2 API

```c
/* pc/platform/gw_hooks.h */
#include <melee/ft/ftdata.h>   /* for ftData_UnkMotionStates3, HSD_GObjEvent */
void gw_mex_set_gobj_event(HSD_GObjEvent *tbl, int kind, HSD_GObjEvent fn);
/* and the feature gate is checked by the caller, e.g.: */
```

### 6.3 Sample hook implementation + registration (native, `pc/platform/`)

```c
/* my_mex_mod.c */
#include "gw.h"
#include "gw_hooks.h"
#include <melee/ft/ftdata.h>          /* ftData_UnkMotionStates3, Fighter, GET_FIGHTER shape */
#include <melee/ft/forward.h>         /* FighterKind */

/* The hook. NOTE the ABI: `gobj` is a real pointer into guest MEM1; every multi-byte
 * field behind it is big-endian and must go through the gw_ accessors. */
static void my_on_frame(HSD_GObj *gobj) {
    /* GET_FIGHTER(gobj) = the fighter struct; its fields are big-endian. */
    void *fp = gw_rptr((void *)((char *)gobj + 0x2C)); /* fp = gobj->user_data (Fighter*) */
    uint32_t kind = gw_r32((char *)fp + 0x04);          /* fp->kind (big-endian) */
    if (kind == Ft_Kind_Fox) {
        /* e.g. log once a second; real mods mutate state via gw_w32/gw_wf32 */
        gw_log("mex: onFrame fox");
    }
}

/* Register once, gated on the feature flag (run from any one-time init). */
void my_mex_mod_init(void) {
    if (gw_Mex_Enabled("mex-onframe")) {
        gw_mex_set_gobj_event(ftData_UnkMotionStates3, Ft_Kind_Fox, my_on_frame);
    }
}
```

`gw_mex_set_gobj_event` is a thin wrapper over `gw_wptr`:

```c
void gw_mex_set_gobj_event(HSD_GObjEvent *tbl, int kind, HSD_GObjEvent fn) {
    /* table is game-resident big-endian; store the native pointer byte-swapped */
    gw_wptr(&tbl[kind], (void *)fn);
}
```

After this, the unchanged decomp line `ftData_UnkMotionStates3[fp->kind](gobj)` loads the
stored pointer (byte-swapped to native by the gwtool-rewritten load) and calls
`my_on_frame(gobj)` every frame for Fox. No call-site edit, no dispatch layer, no
per-frame flag check.

---

## 7. Implementation order (value vs. risk)

Order is chosen to ship the highest-value hooks with the least risk first, all behind
individual flags, all attributed per `tools/mex_port/README.md`.

| Phase | Work | Value | Risk |
|---|---|---|---|
| **1** | Shape A plumbing: `gw_hooks.h`, `gw_mex_set_*` helpers, one-time registration entry. Ship **OnFrame, OnLoad, OnDeath, OnDestroy** (all `HSD_GObjEvent`, all in `ft/fighter.c`, all the "lifecycle" hooks modders want first). | High — the four most-used hooks; proves the whole surface. | Very low — zero call-site change, no layout change. |
| **2** | Remaining `HSD_GObjEvent` Shape A families: OnAbsorb, OnApplyHeadItem, OnRemoveHeadItem, OnItemInvisible/Visible, OnKnockbackEnter/Exit. | Medium. | Very low (same mechanism). |
| **3** | Typed Shape A families: OnItem* (`Fighter_ItemEvent`) and OnRender model (`Fighter_UnkMtxEvent`). OnRender shadow (`ftData_UnkIntBoolFunc0`) only after resolving the `0x108`-vs-`0x84` size question (§8). | Medium. | Low — but the extra args make signature mistakes easier; need the §8 shadow check first. |
| **4** | Shape B — first bespoke hook **OnLanding** (`Fighter_ChangeMotionState`), then OnCatch, OnTaunt, OnIntro L/R, OnSmash F/U/D, OnDoubleJump, OnZair. Establish the `gw_mex_dispatch` native-table pattern on OnLanding, then replicate. | High for OnLanding; medium for the rest. | Medium — each needs a `TARGET_PC` call-site edit and a correct guard ("was grounded", "is this character a tether", …) that must be verified against the disassembly in §1.2. |
| **5** | OnFloat (`bool` predicate replacement) and OnWalljump (`u8` gate) — the two return-/control-flow-sensitive bespoke hooks. | Medium. | Medium — return value flows into logic; needs care. |
| **6 (defer)** | xFunction, grFunction, itFunction, mexSelectChr, mexMapData, mexMenu — separate "extension data + callback tables" design (§1.3). | High for content expansion, but a different subsystem. | High if attempted in this design; split it out. |

Recommended first landable increment: **Phase 1 only** (four lifecycle hooks). It is a
pure additive platform API plus one header, no decomp source change, and can be validated
by enabling `mex-onframe`/`mex-onload` and observing the hooks fire in `melee-pc.log`.

---

## 8. Unresolved / explicitly non-1:1 items

1. **OnRender shadow table size.** `ftData_UnkIntBoolFunc0` is declared
   `ftData_UnkModelStruct { Fighter_ModelEvent model_events[Ft_Kind_Max]; }`
   (`types.h:1824`) = `0x84` bytes, but `symbols.txt` records size `0x108`. Confirm
   against `ftdata.c:1283` before registering; possibly two adjacent per-kind arrays
   (shadow + something). Does not block phases 1–2.
2. **`decideFighter` (OnFSmash) is a `scope:local` symbol** reused four times
   (`0x8008B498`, `0x8008BC34`, `0x8008C348`, `0x8008CE0C`). The OnFSmash patch lands in
   the `0x8008C348` instance, whose containing TU is `ft/kinds/ftCommon/ftCo_AttackS4.c`.
   The exact line inside that function must be re-derived from the disassembly when
   writing the call site (it is a switch/jump-table dispatch over `kind`), not assumed.
3. **OnItemPickup/OnItemDrop are two tables each** (Ext + non-Ext), and OnItemPickup has
   **two** call sites in `ftpickupitem.c` (`ftpickupitem_80094818` and
   `ftpickupitem_800948A8`). Faithful porting means registering into both spellings; this
   is a 2-slot mapping by design, not an ambiguity to hide.
4. **No coherent single call site for OnCatch/OnTaunt/OnIntro L/OnIntro R** — m-ex
   patches the function *epilogue* (`lwz r0,36(r1)` etc.), so the natural native point is
   the top of the function (entry), not the epilogue. The design picks the function entry
   as the call site; the "call-if-present" semantics are equivalent, but the *exact*
   invocation position differs from m-ex's and must be noted in the change-site
   attribution.
5. The `ppc_disasm.py`/`symbols.txt` resolution is complete for every family listed here;
   no unresolved addresses remain in the Tier C fighter set. (The 9 unresolved addresses
   in the triage are all Slippi-compat / standalone-function patches outside this scope.)

---

## Appendix — file/address index for the implementer

- Feature flag: `pc/platform/gw_runtime.c:964` (`gw_Mex_Enabled`), `gw.h:151`.
- ABI contract: `pc/platform/gw.h:1-16`.
- Accessors: `pc/platform/gw.h:32-96` (`gw_r32/w32/rptr/wptr/rf32/…`).
- Per-kind tables: `src/melee/ft/ftdata.h:37-53`; typedefs `src/melee/ft/forward.h:83-85`.
- m-ex spec: `asm/m-ex/Header.s` (`Arch_FighterFunc` offsets 0xC+), `Init ftFunction.asm`,
  and each `Fighter On*/…asm` cited in §1.
- Attribution format: `tools/mex_port/README.md` ("Change-site attribution").
