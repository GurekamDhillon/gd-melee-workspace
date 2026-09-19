# Akaneia dependency scope — what must be supplied beyond `PlSn*.dat`

**Date: 2026-09-19.** Research only: nothing was built, run, or modified. Both ISOs and
`C:/gdm/melee/` were read-only.

**Short answer.** Beyond the ten `PlSn*.dat` files, Sonic *as he runs today* needs exactly one
more disc file: **`PlCo.dat`** (Akaneia's, +3,344 B). Everything else Akaneia adds is content for
the other six new fighters, stages, trophies, music and menus. **But** the Akaneia `main.dol` is
patched, and that patch is a 4-word bootstrap that loads `codes.gct` — a 77 KB file containing the
entire m-ex engine (1,163 codes, 775 asm hooks over 578 distinct vanilla functions). The port does
not apply any of it; it reimplements the needed slices in native C. A files-only `mods/` overlay
therefore **cannot** carry m-ex's code layer, and does not need to — but it also cannot carry
`PlCo.dat`'s per-kind widening as a purely additive file. Details and the exact recommendation
below.

---

## 0. Method and provenance

Both discs were parsed with a throwaway FST reader (session scratchpad, not committed) modelled on
`C:/gdm/tools/gc_extract.py` — that tool exists but prints only bare names, not full paths, so the
walk was re-derived from the boot-block layout documented in
`C:/gdm/melee/pc/platform/shim_dvd.c`. HSD archive headers were parsed directly
(`u32 file_size, data_size, n_reloc, n_public, n_extern`, data at `0x20`).

- Vanilla: `C:\iso\Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso`
- Akaneia: `C:\iso\Akaneia.iso`

VERIFIED disc headers:

| | vanilla | Akaneia |
|---|---|---|
| game id (`0x000`) | `GALE01` | `GALE01` |
| `main.dol` offset (`0x420`) | `0x1E800` | `0x1E800` |
| FST offset (`0x424`) | `0x456E00` | `0x456E00` |
| FST size (`0x428`) | 29,993 B | 39,048 B |
| FST nodes | 1212 | 1596 |
| files (non-dir nodes) | 1209 | 1592 |
| `main.dol` size (summed from its DOL header) | 4,425,184 B (`0x4385E0`) | 4,425,184 B (`0x4385E0`) |
| `main.dol` SHA-1 | `08e0bf20134dfcb260699671004527b2d6bb1a45` | `4963ea2dd7528851f2f8340f253052c9e38ce05a` |

---

## 1. Full FST diff

VERIFIED totals:

- **386** files exist only on Akaneia (325.8 MiB)
- **3** files exist only on vanilla
- **55** files exist on both with a **different size**
- **10** files exist on both at the **same size but different content** (SHA-1 taken over all 1151
  same-size shared files)
- 1141 files are byte-identical

### 1a. Only on vanilla (3) — removed by Akaneia to reclaim space

`MvHowto.mth`, `MvOmake15.mth`, `MvOpen.mth`. Akaneia ships a `$!QOL | Disable Movies` code
(`codes.ini` line 1177), so these are deleted and the space reused for the new `.thp`/`.mth`
endings. **Consequence for the port: none** — but note the dependency direction is *reversed*
here: a vanilla disc has these files and Akaneia's code expects them gone. The port ignores both.

### 1b. Only on Akaneia (386), grouped

| group | files | bytes | notes |
|---|---:|---:|---|
| fighter data + costumes (`Pl*`) | 137 | 57.3 MiB | see breakdown below |
| audio (`audio/*.hps`, `audio/us/*.ssm`) | 64 | 171.7 MiB | 41 new BGM streams, 23 new sample banks |
| stages (`Gr*`) | 52 | 21.4 MiB | incl. 20 `GrAcV*` Animal Crossing villagers, 7 new `GrT??` Target Test stages |
| trophies (`Ty*`) | 51 | 23.8 MiB | incl. `TySonic.dat`, `TySonicR.dat`, `TySonicR2.dat`, `TySSonic.dat` |
| movies (`Mv*.mth`, `GmRegend*.thp`) | 28 | 46.1 MiB | 7 new fighters × 3 endings + 7 `MvEnd*` |
| results / demo poses (`GmRstM*`, `ftDemo*`) | 21 | 0.7 MiB | `GmRstMSn.dat`, `ftDemoIntroSonic.dat`, `ftDemoEndingSonic.dat` |
| UI / menus | 10 | 2.5 MiB | `mexSelectChr.dat`, `ImSlChr.usd`, `ImSlRl.usd`, `ScMnImSlChr.dat`, `IfTag.dat`, `IfTrb.dat`, `ScMjIm.dat`, `ScMjTg.dat`, `ScMjTrb.dat`, `scVb.dat` |
| m-ex plugins | 8 | 0.1 MiB | `plugins/{bgm_display,collection,debug_ext,item_switch_ext,random_stage,rules_ext,stage_hazards,stage_select_ext}.dat` |
| effects (`Ef*Data.dat`) | 7 | 1.1 MiB | `EfSnData.dat` (197,947 B) is Sonic's |
| m-ex core data (`Mx*`) | 6 | 1.0 MiB | see §1e |
| m-ex code payload | 2 | 0.1 MiB | `codes.gct` (77,064 B), `codes.ini` (37,881 B) |

**Fighter breakdown.** Seven genuinely new fighters, each with the same file shape
(`Pl??.dat`, `Pl??AJ.dat`, `Pl??DViWaitAJ.dat`, plus costumes): **Sn** (Sonic, 10 files),
**Ts** (Tails, 10), **Lc** (Lucas, 10), **De** (Dedede, 10), **Dd** (Diddy, 9),
**Lz** (Lizardon/Charizard, 9), **Wf** (Wolf, 9). Plus:

- 19 `PlKb*` — Kirby copy-hat models, incl. **`PlKbCpSn.dat`** (Sonic's hat, 182,322 B)
- ~50 extra costumes for *vanilla* fighters (`PlFxPr.dat`, `PlFxYe.dat`, `PlMrAq.dat`, …) — pure
  additions; the vanilla costume files themselves are byte-identical

### 1c. Present on both, DIFFERENT size (55) — the modified vanilla files

The ones that matter:

| file | vanilla | Akaneia | delta | what it is |
|---|---:|---:|---:|---|
| **`PlCo.dat`** | 149,101 | 152,445 | **+3,344** | fighter common data; **the one hard dependency** (§2) |
| `MnSlChr.usd` | 3,811,401 | 2,312,578 | −1,498,823 | CSS; gutted, replaced by `mexSelectChr.dat` |
| `MnSlMap.usd` | 636,811 | 1,197,614 | +560,803 | stage select, expanded |
| `IfAll.usd` | 901,564 | 957,212 | +55,648 | item archive; cause of the heap-3 OOM (`sonic-clone-boot.md` §2) |
| `SmSt.dat` | 138,772 | 166,972 | +28,200 | stage table |
| `GmRst.usd` | 476,318 | 508,462 | +32,144 | results screen |
| `SdToy.usd` / `SdToyExp.usd` | 9,866 / 221,649 | 11,905 / 261,916 | +2,039 / +40,267 | sound test |
| `TyDataf.dat` / `TyDatai.usd` | 25,112 / 19,347 | 29,256 / 22,507 | +4,144 / +3,160 | trophy registry |

The remaining **46** are all `audio/us/*.ssm` sample banks plus `audio/us/smash2.sem` (+7,488).
Most deltas are tiny (±8 … ±160 B) — consistent with a repack of every bank rather than meaningful
content change. The two real ones are `audio/us/nr_name.ssm` (+136,568 — announcer calls for the
new fighters) and `audio/us/venom.ssm` (−1,184).

### 1d. Present on both, SAME size, DIFFERENT content (10) — easy to miss

`LbMcGame.usd` (20,158), `opening.bnr` (6,496), and 8 sample banks:
`audio/us/{1pend,ending,fox,garden,mars,peach,yoshi,zs}.ssm`. `opening.bnr` is the disc banner
(cosmetic). `LbMcGame.usd` is the memory-card save banner — Akaneia ships a
`$!ADDITIONAL | Use Save Banner #1` code (`codes.ini` line 1). None of these touch Sonic.

### 1e. The m-ex core data files

VERIFIED by parsing each archive's public-symbol table:

| file | data size | relocs | public symbol |
|---|---:|---:|---|
| `MxDt.dat` | `0x199F4` | 2600 | `mexData` |
| `MxMn.dat` | `0x6BE5C` | 313 | `mexMenu` |
| `MxDb.dat` | `0x664D8` | 6469 | `mexDebug` |
| `MxPt.dat` | `0x2CFC` | 40 | `patch_loader` |
| `MxSr.dat` | `0x1A4` | 2 | `series_table` |
| `MxPt_.dat` | `0x0` | 0 | (empty, 32 B placeholder) |
| `mexSelectChr.dat` | `0x1A41B4` | 2080 | `mexSelectChr` |

And the decisive one for fighters:

| file | public symbols |
|---|---|
| vanilla `PlFx.dat` | `ftDataFox` |
| Akaneia `PlSn.dat` | **`ftDataSonic`, `ftFunction`, `itFunction`** |

**Sonic's code ships inside his own `.dat`.** That is the single most important structural fact in
this report: m-ex puts a fighter's moveset (`ftFunction`) and his article/item code (`itFunction`)
in the fighter archive as relocatable PPC, not in the DOL. This is exactly what
`C:/gdm/melee/pc/platform/gw_mex_ftfunction.c` already loads and interprets.

---

## 2. What Sonic actually depends on

Cross-referenced against how the port reaches him: `src/melee/ft/ftdata.c`
(`ftData_SonicHasOwnData`, `ftData_SonicFallback`, `ftData_8008572C`, `ftData_80085820`),
`src/melee/ft/kinds/ftSonic/ftsonic.c`, `src/melee/ft/fighter.c` (`Fighter_LoadCommonData`), and
`pc/platform/gw_mex_ftfunction_runtime.c`.

### CONFIRMED HARD dependencies (11 files)

**1–10. The ten `PlSn*.dat`.** Seven are named literally in
`C:/gdm/melee/src/melee/ft/kinds/ftSonic/ftsonic.c`: `PlSn.dat` (+ symbol `ftDataSonic`),
`PlSnAJ.dat`, and costumes `PlSnNr/Re/Gr/Ye/Bk/Or/Wh.dat` with their
`PlySonic5K*_Share_joint` / `_matanim_joint` symbols. `PlSn.dat` is opened a **second** time by
`pc/platform/gw_mex_ftfunction_runtime.c:37` (`#define GW_MEX_FTFUNC_DAT "PlSn.dat"`) for the
`ftFunction` blob. The tenth, `PlSnDViWaitAJ.dat` (29,626 B), is the victory-pose anim set — it is
**not referenced by the port today** (a grep of `src/melee/ft/kinds/ftSonic/` finds no `DViWait`);
it appears in `MxDt.dat` as `ftDemoViWaitSonic` and will be needed once results screens work.

**11. `PlCo.dat` — Akaneia's, not vanilla's.** VERIFIED by parsing both:

```
vanilla PlCo.dat: data 0x239A0, 805 relocs, 1 public symbol `ftLoadCommonData`
  pData[4] (ftPartsTable) @ 0xEB38 -- entries[27..32] are pointers, entry[33] = 0x07060107
                                      (not a pointer: it is unrelated data past the table)
akaneia PlCo.dat: data 0x24630, 837 relocs, 1 public symbol `ftLoadCommonData`
  pData[4] (ftPartsTable) @ 0xE828 -- entries[27..41] are ALL pointers, into 0x24064..0x24554,
                                      a region that lies BEYOND vanilla's entire 0x239A0 data
                                      section. entry[31] = 0x241F8 = Sonic's parts table.
```

`C:/gdm/melee/src/melee/ft/fighter.c:202` reads exactly that slot:

```c
out[Ft_Kind_Sonic] = ftData_SonicHasOwnData() ? loaded[31] : loaded[Ft_Kind_Fox];
```

Prior in-game evidence (`C:/gdm/_research/sonic-clone-boot.md`, section "m4") confirms
`parts_num=71` from that entry, matching Sonic's skeleton (Fox has 73). With a vanilla `PlCo.dat`,
index 31 is a vanilla boss's parts table and `ftParts_SetupParts` will mismatch.

Note `pData[5]` (`Fighter_804D6540`): on Akaneia indices 27..40 are all **NULL**, so
`ftCommonData_ExtendKindTable` hands `Ft_Kind_Sonic` a NULL there. That matches vanilla's sparse
layout for 27..32 and is probably fine, but it is *not* "Sonic's own entry" as the code comment
implies. Flagged in §5.

### LIKELY needed for the open gaps (medium confidence)

- **`MxDt.dat` (`mexData`, 105,460 B)** — for gap 2 in `C:/gdm/docs/HANDOFF.md` (neutral-B → guest
  access violation walking an m-ex item list). The port currently **synthesizes** mexData: a zeroed
  `0x2000` block (`pc/platform/gw_mex_ftfunction_runtime.c:69`, `GW_MEX_MEXDATA_SIZE`). The real
  tables live in `MxDt.dat`, and the m-ex code's own error strings name them — extracted verbatim
  from `codes.gct`:
  `"error: MxDt does not contain item %d for fighter %d"`,
  `"error: fighter %d does not have item %d"`,
  `"error: MxDt does not have article ID %d"`,
  `"error: MxDt does not contain any items for %s %d"`.
  The `MexData.fighter[]` layout is documented in
  `C:/gdm/_build/m-ex/MexTK/include/mxdt.h:247` and includes `item_lookup`, `ft_archives`,
  `target_test_lookup`, `effect_index`, `anim_num`, `costume_file`.
  Confidence the item crash traces to missing `mexData`: **high**. Confidence that shipping the
  file alone fixes it: **low** — the port would have to parse `mexData` and marshal it, which is
  code work, not a file drop.
  Corroborating: a string scan of `MxDt.dat` finds *every* Sonic string the port currently
  hardcodes — `PlSn.dat`, `ftDataSonic`, all seven costume `.dat`s with both joint symbols each,
  `PlSnAJ.dat`, `PlSnDViWaitAJ.dat`, `/GrTSn.dat`, `GmRstMSn.dat`, `Targets!Sonic`,
  `ftDemoIntroSonic` / `ftDemoEndingSonic` / `ftDemoResultSonic` / `ftDemoViWaitSonic`,
  `sonic.hps`, `ff_sonic.hps`. So `ftsonic.c` is, in effect, a hand-transcription of `MxDt.dat`'s
  fighter row 31.
- **`EfSnData.dat` (197,947 B)** — Sonic's effect archive. NOT referenced by the port today:
  `src/melee/ef/efasync.c` has a fixed vanilla list (`EfCoData.dat`, `EfFxData.dat` …
  `EfGnData.dat`) with no `EfSn` entry, so Sonic borrows Fox's effects. Needed for visual fidelity
  of his specials, and the m-ex error `"Error: fighter %d does not have %s effect %d"` suggests his
  `ftFunction` will request effect ids Fox's archive does not have. Confidence it is *eventually*
  required: **high**. Confidence it is required *now*: **low**.

### NOT needed for the current boot path (with reasoning)

- **`GrTSn.dat` (Sonic's Target Test stage, 494,736 B).** The port reaches Sonic by remapping
  `ftMapping_list[ChKind_Popo]`, so Target Test loads the *Ice Climbers'* vanilla stage. The
  Sonic→`/GrTSn.dat` mapping lives in `MxDt.dat`'s `target_test_lookup`, which the port never
  reads.
- **`mexSelectChr.dat`, `MnSlChr.usd`, `ImSlChr.usd`, `ScMnImSlChr.dat`, `IfTag.dat`.** CSS assets.
  Sonic is reached by a dev remap plus `MELEE_TARGET_TEST=32`, never by picking him on the CSS.
  These become required the moment he should be normally selectable.
- **`IfAll.usd`.** Akaneia's is 55,648 B larger (custom items) and is the *cause* of the heap-3 OOM
  worked around in commit `9a3922df1`. Running against a vanilla disc means the smaller vanilla
  archive — strictly better. The +128 KB heap-3 growth becomes unnecessary (harmless to keep).
- `MxMn.dat`, `MxDb.dat`, `MxPt.dat`, `MxSr.dat`, `plugins/*`, all `Ty*`, all other `Gr*`, all
  `Mv*` / `*.thp`, all `audio/*`, the other six fighters' `Pl*`, the 19 `PlKb*` copy hats,
  `GmRstMSn.dat`, `ftDemo*Sonic.dat`, `SmSt.dat`, `GmRst.usd`, `TyData*`, `LbMcGame.usd`,
  `opening.bnr`, and all 54 resized files other than `PlCo.dat`.

---

## 3. The DOL question

### 3a. What the patch is

VERIFIED byte-for-byte. Akaneia's `main.dol` is the **same length** as vanilla's (4,425,184 B) and
has a **byte-identical section table** — same 10 sections, same file offsets, same load addresses,
same sizes, same `bss` (`0x804316C0` / `0xA6309`) and same entry point (`0x8000522C`). It is
**patched in place, not extended**.

Exactly **5 byte-runs differ, 11,993 bytes total**:

| file offset | VA | size | what |
|---|---|---:|---|
| `0x0000E4`–`0x0000F8` | (DOL header pad) | 20 | ASCII `"NTSC 1.02\0MCM v4.2.1"` |
| `0x012FF0` | `0x80016410` | 4 | inside `lbFileGetSize` (`0x800163D8`) |
| `0x15CB43` | `0x8015FF60` | 1 | inside `main` (`0x8015FEB4`) |
| `0x3287A4`–`0x32B660` | `0x8032BBC4`–`0x8032EA80` | **11,964** | overwrites `HIOEnumDevices` … `MCCWrite` |
| `0x371F64` | `0x80375384` | 4 | inside `HSD_OSInit` (`0x80375304`) |

The header signature names the tool: **Melee Code Manager v4.2.1**. The 11,964-byte region it
overwrites is the dead EXI2/HIO debugger-mailbox code (`HIOEnumDevices`, `HIOInit`,
`HIOReadMailbox`, `DBGHandler`, `FIOInit`, `MCCWrite` — per
`C:/gdm/melee/config/GALE01/symbols.txt`), never reached on retail hardware. That is MCM's standard
free-space region. `C:/gdm/_build/m-ex/dol patcher/patch.xdelta` (2,502 B) is the shipped form of
this same patch.

### 3b. What it does — disassembled

`HSD_OSInit+0x80` (`0x80375384`), vanilla `387F001F addi r3,r31,31`, becomes
`4BFB71BC b 0x8032C540`. At `0x8032C540`
(via `C:/gdm/tools/mex_port/ppc_disasm.py`, abridged):

```
0x8032C540  mfspr r0,lr / stwu r1,-256 / stmw r20,8(r1)   prologue
0x8032C554  bl 0x8032C630          -> `bclr` at 0x8032C630, so lr lands just past it
0x8032C558  mflr r30               r30 = the string at 0x8032C634 = "codes.gct"
0x8032C560  bcctr -> 0x800163D8    lbFileGetSize("codes.gct")
0x8032C570  cmpwi r3,-1 ; beq      not on disc -> restore and leave
0x8032C580  ...                    round size up, shrink the HSD arena by size+0x500
0x8032C5A0  bcctr -> 0x803440E8    (HSD heap setup)
0x8032C5C0  bcctr -> 0x80343EF0    (HSD alloc)
0x8032C5DC  bcctr -> 0x8001668C    (lbFile read -> load codes.gct)
0x8032C5EC  stw r27,-3488(r2)      stash the GCT base in an r2-relative global
0x8032C604  bcctr -> 0x8032BC64    run the code handler over it
0x8032C618  bcctr -> 0x80328F50    flush/invalidate 0x80000000..0x80430000
0x8032C640  epilogue ; addi r3,r31,31 (the displaced instruction) ; b 0x80375388
```

`0x8032BC64` is the **standard Gecko code handler** — it checks the payload's first two words
against `0x00D0C0DE 00D0C0DE` (built in-line with `addis r3,0x00D0 / ori r3,0xC0DE`), which is
exactly `codes.gct`'s header (VERIFIED: `codes.gct` begins `00 D0 C0 DE 00 D0 C0 DE` and ends
`F0000000 00000000`).

The other two patches are support, not payload:

- `lbFileGetSize+0x38` (`0x80016410`): `389E0000 addi r4,r30,0` → `41820078 beq 0x80016488`. This
  makes a missing file return cleanly instead of falling into the `OSError`/assert path — required
  because the loader probes for `codes.gct` before knowing whether it exists.
- `main+0xAC` (`0x8015FF60`): `38800004 li r4,4` → `38800005 li r4,5`. A one-nibble constant bump
  inside `main`. INFERRED, not proven: an arena/heap-count or init-stage argument. See §5.

### 3c. So: does Sonic depend on DOL patches?

**Yes — on a real GameCube. No — for this port.** Two separate statements, and the distinction is
the whole answer.

`codes.gct` is **1,163 codes** (VERIFIED by parsing it end to end; all 77,064 bytes consumed
exactly, no slack): **775 `C2` insert-asm hooks totalling 67,744 bytes of injected PPC**, plus
**388 `04` single-word writes**. Mapped against `config/GALE01/symbols.txt`, those hooks land in
**578 distinct vanilla functions**, concentrated in:

| module (prefix of the containing symbol) | hooks |
|---|---:|
| `ft*` (fighter) | 284 |
| `gm*` (game modes) | 189 |
| `mn*` (menus) | 165 |
| unnamed `fn_*` | 165 |
| `lb*` (library, incl. `lbAudioAx`) | 138 |
| `Fighter_*` | 27 |
| `HSD*` | 20 |
| `ef*` | 20 |
| `Gr*` / `gr*` | 26 |
| everything else | ~79 |

Heaviest single targets: `mnCharSel_CursorThink` (26), `mnStageSel_Scene_OnEnter` (26),
`lbAudioAx_80028690` (25), `mnCharSel_802640A0` (22), `gmResultCharacterData` (20).
Fighter-path ones the port cares about: `ftData_800855C8` (9), `efAsync_LoadSync` (7),
`lbDvd_80017960` (7), `ftParts_800750C8` (6), `ftCo_SpecialAir_CheckInput` (6),
`Fighter_Create` (5), `Fighter_UnkInitLoad_80068914` (5), `ftDemo_CreateFighter` (4).

String-mining `codes.gct` shows what that 67 KB *is*: the whole m-ex runtime. Symbol names it looks
up — `!ftFunction`, `!kbFunction`, `!mexPatch`, `!MxDt.dat` / `!mexData`, `!MxPt.dat`,
`!MxMn.dat` / `!mexMenu` / `!menuFunction`, `!MxDb.dat` / `!mexDebug`, `!mexSelectChr`,
`!mexCostume`, `!itFunction`, `!grFunction`, `!mjFunction`, `!mnFunction`, `!effBehaviorTable`,
`!ftcmd` — plus errors like `"Error: MxDt.dat not found on disc"` and `"Error: MxDt.dat is out of
date; please update with mexTool"`.

Now the port. **It applies none of these 1,163 codes.** It does not read `codes.gct` at all (grep
of `C:/gdm/melee/pc/`, `tools/` and `src/melee/ft/` for `codes.gct`: no hits). Instead the
decompiled C *is* the engine, and each m-ex behaviour the port needs is reimplemented natively —
e.g. `ftCommonData_ExtendKindTable` (`src/melee/ft/fighter.c:192`) replaces m-ex's `ftPartsTable`
widening, and `src/melee/gm/gmmultiman.c:432` documents one such port explicitly:
`/* Ported from m-ex … asm/m-ex/External Character ID Shifts/Null ID/TargetTest.asm, @ 0x801B67EC. */`

The reason this works is §1e: **Sonic's own behaviour is not in the DOL and not in `codes.gct`.**
It is `ftFunction` + `itFunction` inside `PlSn.dat`, which `pc/platform/gw_mex_ftfunction.c`
already loads, relocates and resolves (25 overrides) and `pc/platform/gw_ppc.c` interprets.
`codes.gct` supplies the *dispatcher* that would call those functions on real hardware; the port
supplies a native dispatcher (`gw_Mex_GObjDispatch`) instead.

**Conclusion.** A files-only `mods/` overlay cannot deliver DOL patches — and for Sonic it does not
have to. The Akaneia DOL patch is a 4-word bootstrap whose entire purpose is to load a file the
port ignores. What the port needs from that 67 KB is *reimplementation work in C*, not bytes on
disc. That is a constraint on the roadmap, not on the `mods/` format.

The honest caveat: the port has reimplemented the slice needed to *render and partly drive* Sonic.
`docs/HANDOFF.md` gaps 2, 3 and 5 (m-ex item system, guest render/proc callbacks, MoveLogic
callbacks never firing) each correspond to m-ex code in `codes.gct` that has **not** been ported.
Those are C work, and the figure above (578 hooked functions) is the upper bound on how much of it
exists in total.

---

## 4. Recommendation

### 4a. What `mods/sonic/` must contain

```
mods/sonic/
  PlSn.dat            267,926   fighter data + ftFunction + itFunction
  PlSnAJ.dat        2,053,792   animations (321 used)
  PlSnNr.dat          497,232   costume 0   PlySonic5K_Share_joint
  PlSnRe.dat          497,940   costume 1
  PlSnGr.dat          493,380   costume 2
  PlSnYe.dat          501,860   costume 3
  PlSnBk.dat          492,020   costume 4
  PlSnOr.dat          495,028   costume 5
  PlSnWh.dat          514,564   costume 6
  PlSnDViWaitAJ.dat    29,626   victory poses (unreferenced today; ship it anyway)
                    ~5.84 MiB total
```

plus, for the later phases:

```
  EfSnData.dat        197,947   Sonic's effects (special-move VFX fidelity)
  GrTSn.dat           494,736   his Target Test stage (once TT routing uses it)
  PlKbCpSn.dat        182,322   Kirby's Sonic hat (once Kirby can copy him)
  GmRstMSn.dat        129,551   results screen
  ftDemoIntroSonic.dat  6,134 / ftDemoEndingSonic.dat 5,594
```

### 4b. What CANNOT be expressed as a plain additive file

1. **`PlCo.dat`.** It is a *modification of a vanilla file*, not an addition, and the port needs
   entry 31 of its parts table. Three options, in order of preference:
   - **(a) Synthesize it.** Extract Akaneia's `ftPartsTable[31]` (data offset `0x241F8` within
     `PlCo.dat`'s data section) and ship it as e.g. `mods/sonic/parts.bin` plus a small native
     loader that points `ftPartsTable[Ft_Kind_Sonic]` at it. Keeps the overlay purely additive and
     leaves vanilla `PlCo.dat` untouched. Requires resolving that sub-tree's relocations by hand.
     **Recommended.**
   - **(b) Ship Akaneia's whole `PlCo.dat` (152,445 B) as a file override.** Simplest; works with
     today's `loaded[31]` code unchanged. Costs 149 KB of redistributed vanilla-derived data and
     drags in the other six fighters' parts tables.
   - **(c) Widen the table at runtime from Sonic's own model.** Cleanest, most work.
2. **The DOL patch.** Not deliverable and not needed (§3c). Any future m-ex behaviour goes into
   `pc/platform/` as C, not into `mods/`.
3. **`mexData`.** Today it is synthesized (a zeroed `0x2000` block). For the item system to work,
   either `MxDt.dat` ships as a mod file *and* the port learns to parse `mexData`, or the handful
   of Sonic-relevant rows get transcribed into C the way `ftsonic.c` already transcribes the
   filename row. Given `ftsonic.c` is already a hand-copy of `MxDt.dat` row 31, **transcription is
   the consistent choice** — and a `mods/sonic/sonic.json`-style manifest read by the port would be
   better still, since it turns "edit C and rebuild" into "edit a file".

### 4c. The `mods/` design implication

The overlay needs two mechanisms, not one:

- **additive files** — a path-resolution shim in `pc/platform/shim_dvd.c` that checks
  `mods/<name>/` before the ISO FST. This covers 10 of the 11 hard dependencies and every optional
  file in §4a.
- **per-record overrides inside vanilla archives** — for `PlCo.dat`. A whole-file override is the
  cheap version; a "patch entry N of table T under symbol S" manifest is the right version, and
  would also cover `SmSt.dat`, `IfAll.usd` and `MnSlChr.usd` when stages, items and the CSS arrive.

---

## 5. Open questions and limits of this analysis

Stated plainly; these are the things I did **not** verify.

1. **`Fighter_804D6540[31]` is NULL on Akaneia** (VERIFIED), yet `src/melee/ft/fighter.c:202`
   assigns it to `Ft_Kind_Sonic` through the same `ftCommonData_ExtendKindTable`. Vanilla's
   `[27..32]` are also NULL, so this may be correct-by-sparseness — but the code comment ("Sonic's
   own entry is used there") is not accurate for `pData[5]`. Someone should confirm nothing
   dereferences it unguarded.
2. **The one-nibble `main+0xAC` patch** (`li r4,4` → `li r4,5`). I located it but did not determine
   its meaning. It sits in `main` shortly after `gmMain_8015FDA4`. Worth ten minutes with the
   decomp if anything about boot-time arena sizing ever looks wrong.
3. **I did not verify that the 11,964-byte free-space region equals
   `_build/m-ex/dol patcher/patch.xdelta` applied to vanilla.** That is INFERRED from the MCM
   signature and the matching shape. Applying the xdelta would settle it; I did not, to stay clear
   of the build.
4. **Which of the 775 `C2` hooks are load-bearing for Sonic specifically.** I enumerated all of
   them and their target functions, but attributing a hook to "Sonic needs this" requires reading
   each one's injected asm. I did not. The 284 `ft*` hooks are the candidate set; the port has
   already reimplemented an unknown fraction.
5. **Whether `MxDt.dat` alone closes gap 2 (the neutral-B item crash).** I established that the
   m-ex item tables live in `mexData` and that the port zeroes them. I did not trace the specific
   guest access (`ea=0x00000010`, a NULL `user_data`) back to a named `MexData` field.
6. **`PlSnDViWaitAJ.dat`** is unreferenced by the port today. I assert it will be needed from its
   presence in `MxDt.dat` as `ftDemoViWaitSonic`, not from any code path.
7. **The `.ssm` size churn (46 files, mostly ±8–160 B)** — I assumed repack noise rather than
   content change. I did not diff any bank internally.
8. **`codes.ini` (37,881 B) lists only 50 code groups**, all QOL / debug / menu / gameplay, and
   does **not** describe the m-ex core codes that make up the bulk of `codes.gct`. It is a partial
   manifest; do not treat it as the code inventory. The `.gct` parse (1,163 codes) is
   authoritative.
9. **Licensing / redistribution is out of scope here.** Several files above are vanilla-derived
   (`PlCo.dat` especially). Someone else's call.

### Reproducing this

The FST reader, the two extracted DOLs and the parsed outputs live in the session scratchpad and
were deliberately not committed. Everything here is re-derivable from:

- `C:/gdm/tools/gc_extract.py` — FST walk (names only; full paths need the prefix stack)
- `C:/gdm/tools/mex_port/ppc_disasm.py --dol <dol> --start <va> --count <n>` — disassembly
- the HSD archive header layout in §0 — public-symbol tables
- the two DOLs: file offset `0x1E800`, length `0x4385E0`, on each ISO

---

## Appendix A — complete file lists (VERIFIED)

### A1. The 386 files present only on Akaneia

**fighter data + costumes (Pl*)** (137)

```
PlCaAq.dat PlCaBk.dat PlCaYe.dat PlClLa.dat PlClOr.dat PlDd.dat PlDdAJ.dat PlDdBu.dat
PlDdDViWaitAJ.dat PlDdGr.dat PlDdNr.dat PlDdPi.dat PlDdWh.dat PlDdYe.dat PlDe.dat PlDeAJ.dat
PlDeBk.dat PlDeBu.dat PlDeDViWaitAJ.dat PlDeGr.dat PlDeNr.dat PlDeOr.dat PlDePi.dat PlDeWh.dat
PlDkWh.dat PlDkYe.dat PlDrLa.dat PlDrYe.dat PlFcOr.dat PlFcPi.dat PlFePi.dat PlFePr.dat PlFxPr.dat
PlFxYe.dat PlGnWh.dat PlGnYe.dat PlKbBr.dat PlKbBrCpDk.dat PlKbBrCpFc.dat PlKbBrCpGw.dat
PlKbBrCpMt.dat PlKbBrCpPr.dat PlKbCpDd.dat PlKbCpDe.dat PlKbCpLc.dat PlKbCpLz.dat PlKbCpSn.dat
PlKbCpTs.dat PlKbCpWf.dat PlKbLa.dat PlKbLaCpDk.dat PlKbLaCpFc.dat PlKbLaCpGw.dat PlKbLaCpMt.dat
PlKbLaCpPr.dat PlKpWh.dat PlKpYe.dat PlLc.dat PlLcAJ.dat PlLcBk.dat PlLcBu.dat PlLcDViWaitAJ.dat
PlLcGr.dat PlLcNr.dat PlLcOr.dat PlLcPi.dat PlLcRe.dat PlLgLa.dat PlLgYe.dat PlLkCy.dat PlLkYe.dat
PlLz.dat PlLzAJ.dat PlLzBu.dat PlLzDViWaitAJ.dat PlLzGr.dat PlLzLa.dat PlLzNr.dat PlLzRe.dat
PlLzYe.dat PlMrAq.dat PlMrWh.dat PlMsLa.dat PlMsYe.dat PlMtBk.dat PlMtYe.dat PlNnBu.dat PlNnGr.dat
PlNsBk.dat PlNsPi.dat PlPcCy.dat PlPcYe.dat PlPeBk.dat PlPeRe.dat PlPkBk.dat PlPkWh.dat PlPpBr.dat
PlPpBu.dat PlPrLa.dat PlPrWh.dat PlSkBk.dat PlSkYe.dat PlSn.dat PlSnAJ.dat PlSnBk.dat
PlSnDViWaitAJ.dat PlSnGr.dat PlSnNr.dat PlSnOr.dat PlSnRe.dat PlSnWh.dat PlSnYe.dat PlSsAq.dat
PlSsWh.dat PlTs.dat PlTsAJ.dat PlTsBk.dat PlTsBu.dat PlTsDViWaitAJ.dat PlTsGr.dat PlTsNr.dat
PlTsPr.dat PlTsRe.dat PlTsWh.dat PlWf.dat PlWfAJ.dat PlWfBr.dat PlWfBu.dat PlWfDViWaitAJ.dat
PlWfGr.dat PlWfNr.dat PlWfRd.dat PlWfYe.dat PlYsBk.dat PlYsWh.dat PlZdBk.dat PlZdYe.dat
```

**stages (Gr*)** (52)

```
GrAc.dat GrAcDn.dat GrAcDy.dat GrAcHm.dat GrAcKk.dat GrAcNt.dat GrAcNy.dat GrAcSs.dat
GrAcVBlanca.dat GrAcVBlathers.dat GrAcVBooker.dat GrAcVBoy1.dat GrAcVBoy2.dat GrAcVCopper.dat
GrAcVGirl1.dat GrAcVGirl2.dat GrAcVJack.dat GrAcVJingle.dat GrAcVJoan.dat GrAcVKatrina.dat
GrAcVMable.dat GrAcVMayor.dat GrAcVPelly.dat GrAcVPorter.dat GrAcVRover.dat GrAcVSable.dat
GrAcVTom.dat GrBx.dat GrBxTt.csv GrDo.dat GrDp.dat GrFc.dat GrGc.dat GrGh.dat GrLm.dat GrMVb.dat
GrOHy.dat GrOMc.dat GrOMk.dat GrOPc.dat GrOPz.dat GrOSf.dat GrOSz.dat GrSp.dat GrSv.dat GrTDd.dat
GrTDe.dat GrTLc.dat GrTLz.dat GrTSn.dat GrTTs.dat GrTWf.dat
```

**trophies (Ty*)** (51)

```
TyAkaneia.dat TyAmy.dat TyChao.dat TyDededeC.dat TyDededeR.dat TyDededeR2.dat TyDiddy.dat
TyDiddyR.dat TyDiddyR2.dat TyExt.dat TyGadd.dat TyGameBoy.dat TyGanma.dat TyGhost.dat TyGold.dat
TyGordo.dat TyHakkun.dat TyKbHat6.dat TyKbHat7.dat TyKbHat8.dat TyKnuck.dat TyKris.dat TyLizd.dat
TyLizdR.dat TyLizdR2.dat TyLoloLala.dat TyLucas.dat TyLucasR.dat TyLucasR2.dat TyMarx.dat TyNova.dat
TyPepper.dat TyRed.dat TySMario.dat TySSonic.dat TySatebo.dat TyShadow.dat TySonic.dat TySonicR.dat
TySonicR2.dat TyTails.dat TyTailsC.dat TyTailsR.dat TyTailsR2.dat TyTonzra.dat TyTornado.dat
TyToru.dat TyVolley.dat TyWolf.dat TyWolfR.dat TyWolfR2.dat
```

**effects (Ef*Data)** (7)

```
EfDdData.dat EfDeData.dat EfLcData.dat EfLzData.dat EfSnData.dat EfTsData.dat EfWfData.dat
```

**m-ex core data (Mx*)** (6)

```
MxDb.dat MxDt.dat MxMn.dat MxPt.dat MxPt_.dat MxSr.dat
```

**m-ex code payload** (2)

```
codes.gct codes.ini
```

**m-ex plugins** (8)

```
plugins/bgm_display.dat plugins/collection.dat plugins/debug_ext.dat plugins/item_switch_ext.dat
plugins/random_stage.dat plugins/rules_ext.dat plugins/stage_hazards.dat
plugins/stage_select_ext.dat
```

**UI / menus** (10)

```
IfTag.dat IfTrb.dat ImSlChr.usd ImSlRl.usd ScMjIm.dat ScMjTg.dat ScMjTrb.dat ScMnImSlChr.dat
mexSelectChr.dat scVb.dat
```

**results / demo poses** (21)

```
GmRstMDd.dat GmRstMDe.dat GmRstMLc.dat GmRstMLz.dat GmRstMSn.dat GmRstMTs.dat GmRstMWf.dat
ftDemoEndingDedede.dat ftDemoEndingDiddy.dat ftDemoEndingLizardon.dat ftDemoEndingLucas.dat
ftDemoEndingSonic.dat ftDemoEndingTails.dat ftDemoEndingWolf.dat ftDemoIntroDedede.dat
ftDemoIntroDiddy.dat ftDemoIntroLizardon.dat ftDemoIntroLucas.dat ftDemoIntroSonic.dat
ftDemoIntroTails.dat ftDemoIntroWolf.dat
```

**movies (mth/thp)** (28)

```
GmRegendAdventureDedede.thp GmRegendAdventureDiddy.thp GmRegendAdventureLizardon.thp
GmRegendAdventureLucas.thp GmRegendAdventureSonic.thp GmRegendAdventureTails.thp
GmRegendAdventureWolf.thp GmRegendAllstarDedede.thp GmRegendAllstarDiddy.thp
GmRegendAllstarLizardon.thp GmRegendAllstarLucas.thp GmRegendAllstarSonic.thp
GmRegendAllstarTails.thp GmRegendAllstarWolf.thp GmRegendSimpleDedede.thp GmRegendSimpleDiddy.thp
GmRegendSimpleLizardon.thp GmRegendSimpleLucas.thp GmRegendSimpleSonic.thp GmRegendSimpleTails.thp
GmRegendSimpleWolf.thp MvEndDedede.mth MvEndDiddy.mth MvEndLizardon.mth MvEndLucas.mth
MvEndSonic.mth MvEndTails.mth MvEndWolf.mth
```

**audio** (64)

```
audio/1am.hps audio/2pm.hps audio/5pm.hps audio/7am.hps audio/Fichina.hps audio/ac_title.hps
audio/area6.hps audio/castleisland.hps audio/dedede.hps audio/delfino.hps audio/doltitle.hps
audio/ff_sonic.hps audio/flippant.hps audio/gcnrealm.hps audio/ghz.hps audio/ghz2.hps
audio/goldenland.hps audio/kk_euro.hps audio/kk_go.hps audio/kk_new.hps audio/kk_peru.hps
audio/kk_rock.hps audio/kk_urban.hps audio/kk_west.hps audio/kouhi.hps audio/mansion.hps
audio/mcavern.hps audio/mtdedede.hps audio/old_castle.hps audio/old_hyrule.hps audio/old_mush.hps
audio/old_saffron.hps audio/old_sectorz.hps audio/old_zebes.hps audio/pgym.hps audio/ricco.hps
audio/sonic.hps audio/sonic2.hps audio/starwolf.hps audio/tails.hps audio/us/bios.ssm
audio/us/boxing.ssm audio/us/dedede.ssm audio/us/delfino.ssm audio/us/diddy.ssm audio/us/dolpark.ssm
audio/us/fichina.ssm audio/us/greenhill.ssm audio/us/hyrule.ssm audio/us/lizardon.ssm
audio/us/lucas.ssm audio/us/mansion.ssm audio/us/mk64.ssm audio/us/null.ssm audio/us/old_zebes.ssm
audio/us/pcastle64.ssm audio/us/saffron64.ssm audio/us/saturn.ssm audio/us/sonic.ssm
audio/us/tails.ssm audio/us/village.ssm audio/us/volley.ssm audio/us/wolf.ssm audio/violet.hps
```

### A2. The 55 files present on both at a different size

```
file                          vanilla    akaneia      delta
GmRst.usd                      476318     508462     +32144
IfAll.usd                      901564     957212     +55648
MnSlChr.usd                   3811401    2312578   -1498823
MnSlMap.usd                    636811    1197614    +560803
PlCo.dat                       149101     152445      +3344
SdToy.usd                        9866      11905      +2039
SdToyExp.usd                   221649     261916     +40267
SmSt.dat                       138772     166972     +28200
TyDataf.dat                     25112      29256      +4144
TyDatai.usd                     19347      22507      +3160
audio/us/1padv.ssm             161184     161168        -16
audio/us/bigblue.ssm            35200      35096       -104
audio/us/captain.ssm           433344     433368        +24
audio/us/castle.ssm            176736     176128       -608
audio/us/clink.ssm             301312     301304         -8
audio/us/corneria.ssm          400000     399488       -512
audio/us/dk.ssm                208064     208048        -16
audio/us/drmario.ssm           416480     416472         -8
audio/us/emblem.ssm            484928     484960        +32
audio/us/end.ssm                 1632       1664        +32
audio/us/falco.ssm             511392     511424        +32
audio/us/fourside.ssm           78752      78688        -64
audio/us/ganon.ssm             419744     419736         -8
audio/us/gkoopa.ssm            490464     490480        +16
audio/us/greatbay.ssm          491200     491184        -16
audio/us/gw.ssm                161408     161440        +32
audio/us/ice.ssm               465888     465880         -8
audio/us/kirby.ssm             580704     580440       -264
audio/us/kirbytm.ssm           576640     576512       -128
audio/us/klaid.ssm             305024     305040        +16
audio/us/koopa.ssm             518176     518112        -64
audio/us/last.ssm              663584     663568        -16
audio/us/link.ssm              320000     319904        -96
audio/us/luigi.ssm             375552     375536        -16
audio/us/main.ssm             2065152    2064992       -160
audio/us/mario.ssm             375072     375096        +24
audio/us/mewtwo.ssm            454912     454808       -104
audio/us/mhands.ssm            565376     565368         -8
audio/us/mutecity.ssm          150976     150960        -16
audio/us/ness.ssm              511648     511632        -16
audio/us/nr_1p.ssm             122720     122704        -16
audio/us/nr_name.ssm           339328     475896    +136568
audio/us/nr_select.ssm         240960     240944        -16
audio/us/nr_title.ssm          153408     153440        +32
audio/us/nr_vs.ssm              54720      54704        -16
audio/us/onett.ssm              54752      54608       -144
audio/us/pichu.ssm             561408     561432        +24
audio/us/pikachu.ssm           607072     607064         -8
audio/us/pokemon.ssm           497792     497656       -136
audio/us/pupupu.ssm            123488     123520        +32
audio/us/purin.ssm             336224     336208        -16
audio/us/samus.ssm             311392     311424        +32
audio/us/smash2.sem            132184     139672      +7488
audio/us/venom.ssm             340576     339392      -1184
audio/us/zebes.ssm             388960     388880        -80
```

### A3. The 10 files present on both at the same size but different SHA-1

```
LbMcGame.usd                    20158
audio/us/1pend.ssm             364160
audio/us/ending.ssm           1170784
audio/us/fox.ssm               478240
audio/us/garden.ssm            429408
audio/us/mars.ssm              516416
audio/us/peach.ssm             404832
audio/us/yoshi.ssm             323872
audio/us/zs.ssm                584544
opening.bnr                      6496
```

### A4. The 3 files present only on vanilla

```
MvHowto.mth                 103531584
MvOmake15.mth               488622656
MvOpen.mth                  127036704
```
