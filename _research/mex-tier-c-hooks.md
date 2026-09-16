# Tier C: native hook surface for m-ex fighter callbacks

Design reference. Tier C is the m-ex surface that cannot be ported as patches, because it
executes PowerPC stored inside `.dat` files at runtime and this engine retargets PPC→x86 at
**build** time (no interpreter/JIT). This document records what those hooks actually *are* in
the decompilation, and the native replacement.

## 1. The mechanism, demystified

Each m-ex `Fighter On*` patch replaces **one instruction** — the `addi r0,r3,<lo16>` that
computes the base address of a per-character callback table. The vanilla code that follows is
unchanged:

```
lwz   r4,4(rXX)        ; r4 = fp->kind
addis r3,r0,-32708     ; r3 = 0x803C0000
addi  r0,r3,<lo16>     ; r0 = table base          <-- the PATCHED instruction
slwi  r3,r4,2          ; r3 = kind * 4
add   r3,r0,r3         ; r3 = &table[kind]
lwz   r12,0(r3)        ; r12 = table[kind]
cmpli cr0,0,r12,0
beq   skip             ; null -> skip
mtctr r12
bctrl                  ; table[kind](gobj)
```

So a hook is **not** arbitrary code injection. It is: *"point this per-character table at my
table instead."* `Arch_FighterFunc_*` and the `OFST_*` rtoc slots are both just holders for a
pointer to a per-kind table — the distinction is irrelevant to the port.

**Consequence:** the decomp already calls `ftData_<X>[fp->kind](gobj)` at most of these sites.
Ported hooks need **no new call site** — only a way to write into the existing table.

## 2. Category 1 — clean per-kind table hooks (portable directly)

The decomp table already exists; the hook is "override `table[kind]`".

| m-ex hook | decomp table | call site |
|---|---|---|
| OnLoad | `ftData_OnLoad` | `Fighter_Create` (`ft/fighter.c`) |
| OnLoad (results) | `ftData_OnLoad` | `ftDemo_CreateFighter` |
| OnDeath | `ftData_OnDeath` | `Fighter_UnkProcessDeath_80068354` |
| OnDestroy | `ftData_OnUserDataRemove` | `Fighter_Unload_8006DABC` |
| OnFrame | `ftData_UnkMotionStates3` | `Fighter_8006A360` |
| OnAbsorb | `ftData_OnAbsorb` | `Fighter_ProcessHit_8006D1EC` |
| OnApplyHeadItem | `ftData_UnkMotionStates1` | `ftCommon_8007FA58` |
| OnRemoveHeadItem | `ftData_UnkMotionStates2` | `ftCommon_8007F8E8` |
| OnItem pickup | `ftData_OnItemPickup` + `_Ext` | `ftpickupitem_80094818`, `ftCommon_8007E7E4` |
| OnItem drop | `ftData_OnItemDrop` + `_Ext` | `ftCommon_8007E6DC`, `ftCommon_8007E79C` |
| OnItem invisible / visible | `ftData_OnItemInvisible`, `ftData_OnItemVisible` | `ftCommon_8007F5CC`, `ftCommon_8007F578` |
| OnKnockback enter / exit | `ftData_OnKnockbackEnter`, `ftData_OnKnockbackExit` | `ftCommon_8007F824`, `ftCommon_8007F86C` |
| OnRender model | `ftData_UnkMtxFunc0` | `ftDrawCommon_800805C8`, `ftDrawCommon_80080C28` |
| OnRender shadow | `ftData_UnkIntBoolFunc0` | `ftParts_800750C8` (3 sites) |

All are `void (*)(HSD_GObj* gobj)`, indexed by `fp->kind` over `Ft_Kind_Max` (0x21).

## 3. Category 2 — no clean call site (needs a new native hook point)

These patch mid-function control flow or epilogues rather than a table load, so each needs a
bespoke callback inserted at a specific decomp line. m-ex still conceives of them as per-kind
tables; it just does the lookup by hand.

`OnCatch`, `OnDoubleJump`, `OnFloat` (Down+XY / JumpPeak), `OnIntro` (L/R), `OnLanding`,
`OnSmash` (F/U/D), `OnTaunt`, `OnWalljump`, `OnZair`.

Two of these are not callbacks at all and must **not** be modelled as such:

- **OnWalljump** consults a per-kind **byte** table (`lbzx`) — a boolean, not a function.
- **OnFloat** replaces a whole small predicate function whose **return value** decides whether
  the float fires. The port needs a predicate hook (`bool (*)(HSD_GObj*)`), not `void`.

## 4. Category 3 — not hooks

`xFunction`, `grFunction`, `itFunction`, `mexSelectChr`, `mexMapData`, `mexMenu` are m-ex's
*extension function / data table* mechanism (arbitrary code called by index, plus stage /
character / menu data). They are not per-kind callbacks and need separate treatment.

## 5. Proposed native API

Registration happens from the platform side at boot; the game side applies overrides once the
`ftData_*` tables are populated.

```c
/* gw.h */
typedef void (*gwmex_gobj_fn)(void *gobj);
typedef bool (*gwmex_gobj_pred)(void *gobj);

/* event ids mirror the ftData_* table families above */
bool gw_Mex_HookRegister(int event, int kind, gwmex_gobj_fn fn);
bool gw_Mex_PredicateRegister(int event, int kind, gwmex_gobj_pred fn);
```

Game side exposes the tables to the platform layer, which writes `table[kind] = fn` after the
vanilla initialisation pass. Category 2 events get explicit call sites in decomp C.

Ordering: overrides are applied **after** vanilla table init and are last-write-wins per
`(event, kind)`; no chaining, because m-ex does not chain either.

## 6. Risks to respect

- **OnFrame is per-fighter, per-frame** — it is called from `Fighter_8006A360`, so a slow hook
  costs `n_fighters × 60 Hz`. Keep the dispatch table-array, not a linked list of chains.
- **Null entries are meaningful**: the vanilla `cmpli/beq` means "no callback". Registration
  must be able to *clear* an entry, not only set one, or vanilla behaviour is lost.
- **Lifetime**: `ftData_*` are static tables; overrides must be applied once and re-applied
  after any mode that reinitialises them.

## 7. Implementation order

1. **Category 1, starting with `OnFrame`** — highest value, cleanest call site, already a table.
2. Remaining Category 1 families — mechanical once the API exists (one table each).
3. Category 2 — deferred until Category 1 proves the shape; these need per-site design.
4. Category 3 — separate workstream.
