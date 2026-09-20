# Trophies — the retail system, why it never ran, and what m-ex adds

> Mirrored from `melee/pc/docs/TROPHIES.md`, which is where it was written. Kept here so it sits
> beside `scene-launch.md` and the rest of the research notes.

**Written 2026-09-20.** Code: `src/melee/ty/` (`toy.c`, `tydisplay.c`, `tyfigupon.c`,
`tylist.c`), `src/melee/gm/gmscdata.c` (the scene table), `src/melee/gm/gmtoy*.c` (the three
modes), `src/melee/mn/mnmain.c` (the menu that routes to them),
`pc/platform/gw_runtime.c` (`gw_sl_modes`, the scene-launch keywords).

Companion to `_research/scene-launch.md` in the root repo; this file mirrors that series and
belongs beside it if the two trees are ever reconciled.

---

## 1. The diagnosis, and the evidence for it

Three hypotheses were on the table: the trophy scenes are never entered; they are entered but
fail early; or they run and nothing triggers an unlock.

**The truth was a mix of the first two, and the third was never true at all.**

* **Nothing in the port could ask for those screens.** `GM_TOY_GALLERY` / `GM_TOY_LOTTERY` /
  `GM_TOY_COLLECTION` are in `gmscdata.c`'s mode table, their `GS_TOY_*` scenes are in its
  scene table pointing at `Toy_Scene_OnEnter` / `tyFigupon_Scene_OnEnter` /
  `tyDisplay_Scene_OnEnter`, and `mnmain.c:2384 mn_8022D34C` routes all three from the
  Trophies submenu. None of that was ever a stub. But `MELEE_SCENE` had no keyword for them,
  and no unattended run drives the main menu, so nothing had ever executed a single line of
  `src/melee/ty/`.
* **Once asked for, the gallery and the collection came up on the first try** — on vanilla,
  in a capture. **The lottery faulted on entry**, every time, in `_gw_Toy_80306D70+0x7E`
  reading `0x9483D34C`, called from `tyFigupon_Scene_OnEnter+0x1A3`.
* Unlocks, when the lottery was made to run, fired correctly and **persisted through the
  existing memory card with no work at all** (§4).

## 2. The bug class: retail reaches data by aliasing the symbol next to it

`Toy_80306D70` loads the trophy room's light set. The decomp reads:

```c
base = (TyLightFile*) _Toy_str_TyLight_dat;   /* a char[] holding "TyLight.dat" */
idx  = base->entries[arg0].idx;
sym  = base->symbols[idx].name;
```

`TyLightFile` begins with `u8 pad0[0xCC]`. That is not padding, it is a **distance**:
`_Toy_str_TyLight_dat` lives at `0x3FDD18` and the real table `_Toy_803FDDE4` at `0x3FDDE4`,
exactly `0xCC` apart in retail's `.data`. So on the disc the cast lands on the table. Nothing
makes a host linker reproduce that adjacency, and on PC the read walked off the end of a
12-byte string.

`toy.c` does it three times, all from the same base:

| site | expression | what it really means |
|---|---|---|
| `Toy_80306D70` | `(TyLightFile*) _Toy_str_TyLight_dat` | `_Toy_803FDDE4` (`0x3FDD18 + 0xCC`) |
| `Toy_80307470` | `&data->ptrs[arg0]` then `+= 0x188/4` | `_Toy_803FDEA0[arg0]` (`+0x188`) |
| `_Toy_803075E8` | `(char**)(data + arg0*4)` then `+= 0x69` | `_Toy_803FDEBC[arg0]` (`+0x1A4`) |

All three now name the real symbol under `TARGET_PC`, with the retail expression kept under
`#else`. The declarations agree field for field — `TyLightFile::symbols[6]` is
`lbl_803FDDE4_t::symbols[6]`, and the `0xC`-stride `entries[]` is `::values[6]` of
`{int index; GXColor color; bool flag;}` — so this is a renaming, not a reinterpretation.

**Look for more of these.** The marker is a `.data`/`.sdata` "order hack" comment next to a
struct whose first member is a large `pad`. `toy.c` has six such comments; `tydisplay.c`,
`tyfigupon.c` and `tylist.c` have nine more between them, though none of those currently
aliases across a symbol boundary.

## 3. The second bug: a stack write four elements past a one-element local

`Toy_80310324` (the gallery/collection scene build-up) calls

```c
UNK_T sym[1];
... = lbArchive_LoadSymbols("TyMnView.dat", sym + 4, _Toy_803FDEA0[0], NULL);
```

`sym + 4` is sixteen bytes past a four-byte local. Retail gets away with it because of where
its compiler put the neighbouring slot. On PC it smashed the frame, and the tell was precise:
the gallery crashed in `gm_801A4014` at `mov eax, [esi+4]` **immediately after the
`scene->on_enter` call returned**, with `esi` holding `0x08567680` — a callee-saved register
that the callee had destroyed. `[esi+8]` had been read successfully four instructions
earlier, so the register was good going in and garbage coming out.

The out-parameter is discarded at this call site anyway (the function's *return* is what is
kept), so the PC build writes inside the array.

**This one only fired on Akaneia and ACE**, because what lands on the smashed slot depends on
the heap layout, which depends on the disc. Vanilla wrote a value the frame survived. That is
worth remembering: *a stack-smashing decomp artifact can be disc-dependent, and "it works on
vanilla" is not evidence that the write is in bounds.*

## 4. What works now

Verified in captures under `_build/runs/`, on a **copy** of the unlocked card
(`_build/card-trophy`, never `_build/card`):

| screen | disc | run |
|---|---|---|
| Gallery — model, name, description, series counter | vanilla | `tygal` |
| Gallery | Akaneia | `tygal_ak3` |
| Collection room | vanilla | `tycoll`, `tysave` |
| Collection room, showing m-ex trophies | ACE | `tycoll_ace` |
| Lottery — machine, coin counter, "chance of a new trophy" | vanilla | `tylot2` |
| **"GOT IT! A NEW TROPHY!" popup**, model + name | vanilla | `tylot7` frame 08s |

**Save data needed nothing.** A lottery run with `skipmemcard=0` started at 97.8% / 3 coins;
the next run on the same card started at 93.6% / 0 coins. Unlocks and the coin balance both
survived the restart through `shim_card.c` as it already stood. Note that a scene launch
*defaults* to `skipmemcard=1`, which disables saving for the run — a trophy run that wants the
save has to say `skipmemcard=0`.

`MELEE_SCENE` keywords added: `trophygallery`/`tygallery`, `trophylottery`/`tylottery`/
`lottery`, `trophycollection`/`tycollection`/`trophies`. None has a `VsModeData` row, so they
seed nothing and simply boot.

```
MELEE_SCENE="mode=trophylottery;skipmemcard=0"
MELEE_SCENE="mode=trophygallery"
MELEE_SCENE="mode=trophycollection"
```

## 5. The m-ex side — what the discs actually ship

Read straight off the discs with `tools/mex_port/mex_hsd.py`; nothing here is inferred.

**`TyExt.dat` is NOT a trophy extension table.** It is 791,989 bytes with five publics:
`ToyDspExt_Top_joint`, `ToyDspExt_Top_matanim_joint`, `ToyDspExt_Top_animjoint`,
`trophy_icon_param` and `scene_data`. That is a *display* asset — an extra collection-screen
panel plus its icon parameters — not the `MxDt.dat`-shaped table the name suggests. The port
does not need a new table reader for it.

**The trophy table that IS extended is `TyDataf.dat`**, and this is the number that matters:

| disc | `tyModelFileTbl` entries (stride 84) | `TyDatai.dat` |
|---|---|---|
| vanilla | **293**, ids 0..292, last `TyGmCube.dat` | 19,347 bytes |
| Akaneia | **342**, ids 0..341; 293 = `TyWolf.dat`, 341 = `TyKbHat8.dat` | **byte-identical to vanilla** |
| ACE | **342** — `TyDataf.dat` is byte-identical to Akaneia's | byte-identical to vanilla |

Two things fall out of that table:

1. **ACE adds no trophies of its own.** Its `TyDataf.dat` is the same file as Akaneia's, and
   the set of `Ty*.dat` on the two discs is identical (408 each, 51 more than vanilla's 357).
   ACE's 31 extra fighters have no trophies. Its extra `GmRstM*.dat` results-screen models are
   a separate, larger set (58 vs Akaneia's 33 vs vanilla's 26) and do **not** live in this
   table.
2. **`TyDatai.dat` was never extended.** `tyDisplayModelTbl`, `tyInitModelTbl`,
   `tyModelSortTbl`, `tyExpDifferentTbl` and the two `Us` tables are all still retail-sized.
   Whatever m-ex does for the added trophies' sort order and display data, it does not do it
   in that file — its code patches are the place to look.

### The trap, stated exactly

`TY_TROPHY_COUNT` is **293** (`src/melee/ty/forward.h:4`), and it sizes *every* per-trophy
structure in the game:

* `Toy26B8::trophyTable[293]` and `Toy::trophy_flags[293]` (`ty/types.h:93,180`)
* the save block's `trophy_flags[293]` and two `[(293+31)/32]` bitfields
  (`gm/types.h:325,332,409`) and `times[293]` (`gm/types.h:410`)
* **two 293-entry arrays on the stack** in `toy.c:830` (`obtained_arr`, `new_arr`)
* the `HSD_MemAlloc(sizeof(*x) * TY_TROPHY_COUNT)` block in `Toy_Scene_OnEnter`
* ~20 `for (i = 0; i < TY_TROPHY_COUNT; ...)` loops across `toy.c`, `tydisplay.c`,
  `tyfigupon.c`

An m-ex trophy id runs to **341**, so any of those indexed by a disc-derived id overruns by up
to 49 entries — and two of them are on the stack. This is `docs/HANDOFF.md` §6's recurring bug
in its purest form. **Today it does not fire**, because every loop is bounded by the constant
rather than by the disc, so the port simply ignores trophies 293..341. That is the right
failure, and it is why the mod discs' trophy screens work at all.

`Toy_SetUnlockState` now logs every unlock and says `*** OUT OF RANGE ***` for an id outside
`[0, TY_TROPHY_COUNT)`, so the day something does feed it an m-ex id, the log says so instead
of quietly corrupting the save block.

Raising the constant is **not** the next step on its own: `trophy_flags[293]` is part of an
on-card structure, so widening it is a save-format change, exactly as `docs/HANDOFF.md` §1
gap 7 said.

### Known cosmetic difference, seen in a capture

On Akaneia the gallery's series box shows two stacked series names ("The Legend of Zelda" /
"Pokémon Red & Blue") where vanilla shows one name and an "N/99" counter (`tygal_ak3` vs
`tygal`). Not investigated.

## 6. Unrelated finding: the loading overlay never stands down on the collection screen

`shim_gx.c:546` tells the overlay how much content the frame drew with
`gw_Overlay_NoteContent(gw_gx_prim_count)`. The trophy collection room draws entirely through
display lists — its DIAG line reads `prim=0 dlist=129` — so the count stays at zero, the
overlay decides the game is still booting, and a "LOADING … TyQuesD.dat" panel sits over the
screen for the whole run. Nothing is actually stuck.

`shim_gx.c` belongs to another agent, so the one-line change is left as
`_build/patches/overlay-count-dlists.patch` rather than applied here.
