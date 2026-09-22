# m-ex stock icons (in-match HUD and 1P CSS) for Sonic

**Date: 2026-09-19.** Research only. Nothing was built or run, and nothing under `C:/gdm/melee/` or
`C:/iso/` was modified. m-ex is used as a **specification only**: its behaviour is described here
in my own words, and no m-ex `.asm`, `.h` or `.dat` content is reproduced. Every m-ex claim below was
checked against the **bytes Akaneia actually ships** (the `codes.gct` payloads, disassembled), not
only against the m-ex source tree.

Evidence labels: **VERIFIED** means read directly in a file or a disassembly (the location is
given). **INFERRED** means reasoned from verified facts but not observed.

New tools (read-only, in `C:/gdm/tools/mex_port/`):
- `dump_gct.py` lists, extracts and disassembles Gecko codes from Akaneia's `codes.gct`. Use `--addr`,
  `--range` and `--disasm`.
- `dump_stc_icns.py` decodes IfAll's `Stc_icns`. It maps frames to images for any internal id, can
  render PNGs, and with `--retail-iso` checks the m-ex formula against the retail icons, image by image.

Index spaces used below (always stated explicitly):
- **CK**: retail `CharacterKind` (`ft/forward.h`: CF=0 .. Ganon=0x19, MH=0x1A, Boy, Girl, Giga, CH,
  Sandbag=0x1F, Popo=0x20). **The port reuses CK 0x20 as Sonic** (`pl/player.c:78`).
- **FK**: the port's `FighterKind` (Mario=0 .. Sandbag=0x20, **Sonic=0x21=33**).
- **mINT**: m-ex internal id (Akaneia `mexData`). 0..26 are the same as retail FK. 27..33 are the
  customs (27 Wolf, 28 Diddy, 29 Lucario, 30 Lucas, **31 Sonic**, 32 Dedede, 33 Tails). 34 is an
  empty slot, and 35..40 are MH, CH, Boy, Girl, Giga and Sandbag. There are 41 in total.
  (`dump_mxdt.py`: `pl_file[i]` for i=0..40.)
- **mEXT**: m-ex external id. 0..25 are the same as retail CK, 26..32 are the customs, and
  **Sonic is 30**.

---

## TL;DR

1. **The real GetStockFrame** is shipped as a `C2` at `0x803D7060` (gct offset `0xE028`, 176 bytes).
   Its semantics: `frame = Stc_icns.reserved + costume * Stc_icns.stride + mINT`, except that the
   **last six mINTs** (35..40) map to fixed frames `{3,2,1,1,5,6}`. It reads **no mexData table**
   apart from `metadata.internal_id_count` (41). Both constants come from **IfAll's `Stc_icns` header**:
   reserved = **8**, stride = **41**. **Sonic (mINT 31) → frames 39, 80, 121, 162, 203** for costumes
   0..4 (and 244, 285 for costumes 5 and 6). Each is a distinct Sonic image (images 208..214), and
   they were checked visually.
2. The formula reproduces retail's stock art for **120 of 122** vanilla fighter/costume pairs, image
   and palette byte-identical. Only the costume-0 icons of Pikachu and Pichu differ, and that
   difference is in the art itself (INFERRED: Akaneia redrew them), not in the frame.
3. **`Stc_icns` = `{u16 reserved; u16 stride; HSD_MatAnimJoint* matanim; u32 egg_num; void* eggs;}`**
   (IfAll.usd data+0xDF61C). The MatAnimJoint is a single joint (no child and no next) holding one
   MatAnim, which has one TexAnim (texmap 0) with **229 images, 229 TLUTs, end frame 309**, and FObjs
   TIMG and TCLT (constant keys, u8 values). The symbol exists **only in Akaneia's `IfAll.usd`**. It is
   not in `IfAll.dat`, and not in retail.
4. **In-match HUD needs 5 changes:** (a) replace `gm_80168B34`; (b) add the Stc_icns matanim to the
   stock joints in `ifStock_802F98E8` (VS: 7 joints), `ifStock_802F96D0` (All-Star: 1) and
   `ifStock_802F9F48` (Multispawn: 1); (c) in the last two, pass the internal id where retail passes 0.
   **The port must also map FK 33 (Sonic) to mINT 31** before applying the formula.
5. **1P CSS (regend joints 53..57):** the scene build adds Stc_icns to the 5 joints. On every
   costume or character change, all 5 are set to `GetStockFrame(mINT(icon), costume)` with rate 0.
   When the slot is empty (the character is hidden), m-ex sets them to **frame 7, the red ring**.

---

## Q1. GetStockFrame(internal, costume)

### 1.1 The shipped routine: VERIFIED

Source: `C:/iso/Akaneia.iso` → `codes.gct`, `C2 0x803D7060`, gct+0xE028, 176-byte payload
(`python dump_gct.py --iso C:/iso/Akaneia.iso --addr 0x803D7060 --disasm`). The disassembly matches
m-ex's `Standalone Functions/Stock Icon Get Frame.asm` instruction for instruction. What it does:

- args: `r3` = mINT, `r4` = costume. Returns `f1` = frame (float).
- `stc = *(r13 - 0x4724)` (the saved `Stc_icns` pointer; that address is `0x804D6F7C`, which is retail
  `erase_colors_vi0501` in `.sbss`. m-ex's own header flags the address as a hack). **If `stc` is NULL,
  it returns without writing `f1`**, so the caller gets whatever `f1` held. That is an m-ex bug; the
  port should fall back to the retail formula instead.
- `n = *(rtoc + 0x148)` = `mexData.metadata.internal_id_count` (**41** on Akaneia).
- If `n-6 <= mINT <= n-1`, the result is `table[mINT-(n-6)]`, with the byte table `03 02 01 01 05 06`
  (visible at payload +0x90).
- Otherwise it is `u16 stc[0] + u16 stc[2] * costume + mINT`.
- Int→float uses the standard `0x43300000` / `rtoc-0x35F8` magic-double trick.

So the only mexData value it reads is the internal count. There are **no per-fighter stock
tables**: the layout of the icon atlas is fixed entirely by `Stc_icns.reserved` and `.stride`.

### 1.2 Hook at gm_80168B34: VERIFIED

`C2 0x80168B34` (gct+0x6128, 80 bytes) sits at the **first instruction** of `gm_80168B34`
(`gm/gm_1601.c:3992`, range `0x80168B34..0x80168BF8`). It saves registers, calls
`0x803D7060(r4, r5)` and `blr`s, so the **whole retail function is replaced**.
`gm_80168B34(ckind, arg1, costume)` becomes `GetStockFrame(arg1, costume)`, and **`ckind` is
ignored**. The m-ex source names `r4` the internal id and `r5` the costume.

### 1.3 Who calls it, and what arg1 is: VERIFIED

All `bl` sites in retail `main.dol` that target `0x80168B34` or `0x80168BF8` (found by a text-section
scan and resolved with the decomp symbol table):

| call site | function | arg1 in retail | m-ex handling (hook shipped in gct?) |
|---|---|---|---|
| 0x80168C3C | `gm_80168BF8(slot)` (`gm_1601.c:4029`) | `Player_80036394(slot)` = **current FighterKind** (after a Zelda/Sheik transform) | nothing needed: arg1 is already the internal id. A separate egg hook sits at 0x80168C10 (see Q5) |
| 0x802F988C | `ifStock_802F96D0` (All-Star) | **0** | `C2 0x802F9888` (gct+0x5F28): arg1 = `Player_800325C8(ckind, 0)` = `ftMapping_list[ckind].internal_id` |
| 0x802FA0B8 | `ifStock_802F9F48` (Multispawn) | **0** | `C2 0x802FA0B4` (gct+0x6180): same, with ckind = `ifStock_804A1774.x83[arg]` |
| 0x802F6320 | `ifStatus_802F61FC` | 0 | **This is the percent-box emblem, not a stock icon.** `C2 0x802F6320` replaces it with `insignia_idx[mEXT]` (see Q3.4) |
| 0x801777C8 | `fn_80177748` (results) | – | results emblem (`Results - Change Emblem Frame`) |
| 0x80178EDC/0x80178FD8 | `fn_80178BB4` (results) | – | results texture names |

Every stock-icon caller in the in-match HUD (`ifStock_802F8298`, `ifStock_802F89F8`,
`fn_802F9410` and `ifStock_802F98E8`) reaches the formula through `gm_80168BF8`. The VS HUD therefore
needs **only** the `gm_80168B34` replacement plus the matanim swap.

### 1.4 Sonic's frames: VERIFIED

Stc_icns reserved = 8, stride = 41, and mINT(Sonic) = 31, which is not in the special range 35..40:

| costume | frame | Stc_icns image/TLUT index | image |
|---:|---:|---:|---|
| 0 | **39** | 208 | 24x24 CI4, blue Sonic |
| 1 | **80** | 209 | purple |
| 2 | **121** | 210 | green |
| 3 | **162** | 211 | cyan |
| 4 | **203** | 212 | dark navy |
| 5 | 244 | 213 | orange |
| 6 | 285 | 214 | silver |

All 7 frames are explicit TIMG keys and their images are **unique** (no other frame in the atlas
shares their hash). I rendered them with `dump_stc_icns.py --png-dir` and they are clearly Sonic's
head in 7 colours. Costume 7 would be frame 326, which is past the end frame (309) and falls back to
an unrelated image. Akaneia's `fighter.costume_info[mEXT 30]` = `07 01 00 02`. **INFERRED**: byte 0 is
the costume count (7), and bytes 1..3 are the red/blue/green team costumes. The port currently allows
only **5** Sonic costumes (`gm_1601.c:4275`). Frames exist for all 7.

### 1.5 Formula vs retail: VERIFIED (by image, not by frame number)

Retail `gm_80168B34`: `base + costume*30`, where `base` = CK for CK ≤ 0x11, 0x12 for Zelda,
0x19 for Sheik (arg1 == FK 7), CK-1 for CK > 0x13, and 0xE for CK 0x20. The specials are fixed:
Boy/Girl 26, CH 27, MH 28, Giga 58, Sandbag 59. Retail's atlas is ordered by **CK**. Stc_icns is
ordered by **mINT** with a different stride, so the frame numbers never match (for example Fox is
retail frame 2 but m-ex frame 9). The meaningful test is whether both frames show the **same picture**.

`dump_stc_icns.py --retail-iso` compares the retail IfAll `Stc_scemdls` stock TexAnim (stock joint 1;
130 images, end 250) at the retail frame with Stc_icns at the m-ex frame. It hashes image bytes plus
TLUT, for every vanilla CK and every retail costume:

- **120/122 identical.** Examples: Mario c0 (retail 8 → m-ex 8), Fox c0 (2 → 9), CF c0 (0 → 10),
  Sheik c0 (retail 25 via arg1=7 → m-ex mINT 7 = 15), and GW, Roy and Ganon at every costume.
- The 6 specials also match (MH 28→3, CH 27→2, Boy/Girl 26→1, Giga 58→5, Sandbag 59→6).
- **Differ**: Pikachu c0 (13 vs 20) and Pichu c0 (23 vs 31). The images are the same size, but the
  pixels and all 16 palette entries differ. INFERRED: Akaneia replaced that art. The frame mapping
  itself is consistent (the other Pikachu and Pichu costumes match).
- Akaneia's own `Stc_scemdls` is byte-identical to retail over all 251 frames. m-ex does not edit the
  retail atlas: it replaces it at runtime.

---

## Q2. Stc_icns

VERIFIED (`dump_stc_icns.py`; `C:/iso/Akaneia.iso` → `IfAll.usd`, public `Stc_icns` at data+0xDF61C):

| off | field | value |
|---|---|---|
| +0x00 | u16 reserved_frames | **8** |
| +0x02 | u16 stride | **41** (= internal count) |
| +0x04 | `HSD_MatAnimJoint*` | data+0xDF62C (reloc) |
| +0x08 | u32 egg_num | 0 |
| +0x0C | eggs* | data+0xE2FD8 (reloc) |

The m-ex `Header.s` names are `StcIcons_ReservedFrames/Stride/MatAnimJoint/EggNum/Eggs`. Every m-ex
patch reads the anim as `*(Stc_icns + 4)`.

- MatAnimJoint @0xDF62C: child = 0, next = 0, matanim = 0xDF638. **It is a single joint**, so
  `HSD_JObjAddAnimAll` applies it only to the JObj it is given.
- MatAnim @0xDF638: next = 0, aobjdesc = 0, texanim = 0xDF648, renderanim = 0.
- TexAnim @0xDF648: texmap GX_TEXMAP0, **229 images / 229 TLUTs**, AObj end frame **309.0**, with 2
  FObjs: TIMG (type 1) and TCLT (type 10). Both have 241 constant (CON) keys with u8 values and
  identical key lists, and frames share images.
- The largest m-ex frame for a normal fighter is `8 + 41*c + 33`. At 7 costumes (c = 6) that is 287,
  which is under 309.
- Reserved frames 0..7 (rendered): 0 = 5x5 blank, 1 = wireframe/Smash logo (Boy and Girl),
  2 = Crazy Hand, 3 = Master Hand, 4 = target, 5 = Giga Bowser, 6 = Sandbag, **7 = red ring** (the
  CSS "empty slot" dot).
- **Only `IfAll.usd`** carries `Stc_icns` (and `Eblm_matanim_joint`). `IfAll.dat` (the Japanese
  file) on Akaneia and retail `IfAll.usd` do not. The port has to load the US file, or fall back
  when the symbol is missing.

How m-ex looks it up (VERIFIED in gct): `HSD_ArchiveGetPublicAddress(archive, "Stc_icns")` is stored
at r13-0x4724:
- in-match: `C2 0x802F6770` in `ifStatus_802F66A4` (HUD init), using the IfAll archive at `0x804D6D5C`
  (`ifAll` archive). It stores `Eblm_matanim_joint` at the same time.
- CSS: `C2 0x80266994` in `mnCharSel_Scene_OnEnter` (+0x108), via `lbDvd_8001819C("IfAll")`. It
  writes NULL if the symbol is missing.

---

## Q3. In-match HUD: every retail site to change

All of these hooks are shipped in Akaneia's gct (VERIFIED with `dump_gct.py --addr`). Functions were
resolved with the decomp symbols (`config/GALE01/symbols.txt`).

| # | m-ex patch | hook addr (gct off) | decomp function (+off) | retail at hook | what m-ex does |
|---|---|---|---|---|---|
| 1 | `HUD/Match - Change Stock Frame` | 0x80168B34 (0x6128) | `gm_80168B34` +0 (`gm_1601.c:3992`) | function entry | whole function becomes `GetStockFrame(arg1, arg2)` |
| 2 | `HUD/Replace Match Stock Matanim` | 0x802F99C0 (0x62C0) | `ifStock_802F98E8` +0xD8 (`ifstock.c:579`), VS/per-player stock HUD | right after `gm_8016895C(jobj, *stock->x0, 0)` | for jobj **indices 1..7** (`lb_80011E24(root, &j, i, -1)`) it calls `HSD_JObjAddAnimAll(j, NULL, stc->matanim, NULL)`, then replays `mr r3,r29` |
| 3 | `HUD/All Star - Replace Stock Matanim` | 0x802F9764 (0x5F58) | `ifStock_802F96D0` +0x94 (`ifstock.c:541`), All-Star | right after `gm_8016895C` | the same, for **index 1** only |
| 4 | `HUD/All Star - Change Stock Frame` | 0x802F9888 (0x5F28) | `ifStock_802F96D0` +0x1B8 | `li r4,0` before `bl gm_80168B34` | arg1 = `Player_800325C8(ckind, 0)` |
| 5 | `HUD/Multispawn - Replace Stock Matanim` | 0x802F9FD4 (0x61B8) | `ifStock_802F9F48` +0x8C (`ifstock.c:749` inline) | right after `gm_8016895C` | the same, for **index 1** only |
| 6 | `HUD/Multispawn - Change Stock Frame` | 0x802FA0B4 (0x6180) | `ifStock_802F9F48` +0x16C | arg setup before `bl gm_80168B34` | arg1 = `Player_800325C8(x83[arg], 0)` |
| 7 | `HUD/Index Custom IfAll Symbols` | 0x802F6770 (0x5FD8) | `ifStatus_802F66A4` +0xCC (`ifstatus.c:890`) | epilogue | caches `Stc_icns` and `Eblm_matanim_joint` |

Notes (VERIFIED from the decomp and disassembly):
- In each case the matanim swap goes in **after** `gm_8016895C` has attached the retail
  anim/matanim, and **before** the `HSD_TObjReqAnimAll(tobj, frame)` / `HSD_AObjSetRate(0)` /
  `HSD_JObjAnimAll` calls. `HSD_JObjAddAnimAll` → `HSD_TObjAddAnim` replaces the TObj's AObj and
  texanim, so later frame requests index Stc_icns.
- The VS loop covers indices 1..7 because `ifStock_802F98E8` caches `x4[1..7]` as the 7 icon jobjs
  (`ifstock.c` `for i<7 ... x4[i+1]`). Retail `Stc_scemdls` also has 7 stock TexAnims (130 images each)
  on those joints.
- The per-frame updates (`ifStock_802F8298`, `ifStock_802F89F8`, `fn_802F9410`) re-request the TObj
  frame through `gm_80168BF8`, so they need no further change.

### 3.4 Not a stock icon: the percent-box emblem (for completeness)

`ifStatus_802F61FC` ("ifAddMark", `ifstatus.c:~790`) calls `gm_80168B34(chara,0,0)` to pick the
**series emblem** behind the damage percent. m-ex changes three things here:
- `C2 0x802F62FC` skips retail's MH/Giga → Boy remap.
- `C2 0x802F6320` turns the frame into `insignia_idx[mEXT]` (`OFST_GmRstInsigniaIDs`).
- `C2 0x802F62F8` (`Replace Match Emblem Matanim`) swaps in `Eblm_matanim_joint`.

`_research/mex-css.md` item 16 lumps this call in with the stock icon. It is a separate fix, and the
port already has `gw_Mex_InsigniaForExt` for it.

---

## Q4. 1P CSS stock icons (regend joints 53..57)

VERIFIED from the m-ex source and the shipped gct payloads (all present):

| m-ex patch | hook (gct off) | decomp function | behaviour |
|---|---|---|---|
| `CSS Expansion/HUD/Replace CSS SinglePlayer Stock And Emblem` | 0x80264548 (0x23A8) | `mnCharSel_802640A0` +0x4A8 (1P scene build; the original `bl HSD_JObjAddAnimAll` is replayed first) | IfAll `Stc_icns` → `matanim`. For regend (`mnCharSel_804D6CC0` = r13-0x49E0) jobj **indices 53..57** it calls `HSD_JObjAddAnimAll(j, NULL, matanim, NULL)`. It also attaches the emblem (joint 43, second DObj, `Eblm_matanim_joint->+8`) and the CSP (joint 45, `mexSelectChr.CSPMatAnim`) via `HSD_DObjAddAnimAll` |
| `CSS Expansion/HUD/Index Stc_icons` | 0x80266994 (0x6068) | `mnCharSel_Scene_OnEnter` +0x108 | caches Stc_icns (or NULL) at r13-0x4724 |
| `CSS - Costume Change Rewrite` | 0x8025D5AC (0x1F50) | `mnCharSel_8025D5AC` +0 (whole function; its signature becomes `(port, mEXT, costume, isNull)`) | 1P and port 0: CSP and emblem as already documented in mex-css.md, then **stock icons**: `mINT = MnSlChrDefineIDs[icons[sel].ext*3]` (m-ex's copy of `ftMapping_list`, byte 0 = internal) and `f = GetStockFrame(mINT, costume)`. For jobj 53..57: `HSD_TObjReqAnimAll(j->dobj->mobj->tobj, f)`, `HSD_AObjSetRate(tobj->aobj, 0.0)`, `HSD_JObjAnimAll(j)`. Hidden and shown state is **not** touched for the stocks |
| `CSS - Change Stock Frame Dot 2` | 0x8025DB80 (0x1D50) | `mnCharSel_8025DB34` +0x4C, right after its `mnCharSel_8025D5AC(door, 0, hidden=1)` | if 1P CSS (`*(u8*)0x804D6CF5 == 1`) and Stc_icns exists: the same 3-call sequence on 53..57 with **frame 7** |
| `CSS - Change Stock Frame Dot` | 0x80260DB4 (0x1E50) | `mnCharSel_CursorThink` +0xB14, right after `mnCharSel_8025D5AC(r19, 0, 1)` | the same: **frame 7** |

The answer to "what frame": when a character is selected, all five stock joints show
`GetStockFrame(mINT, costume)`. For Sonic that is 39, 80, 121, 162 or 203 for costumes 0..4.
**When the slot is empty (portrait hidden), frame 7 (the red ring).**

For comparison, retail `mnCharSel_8025D5AC` (`mncharsel.c:1024`) drives joints
`data2.xf0 = {0x35,0x39,0x36,0x38,0x37}` with **the portrait frame** on the regend's own 129-image
stock anim, and uses frame **0xB9** when hidden. The port's current `mnCharSel_MexPortrait` still
calls the retail routine for 1P, so the 1P stock dots show retail frames from the retail atlas. That
is wrong for Sonic.

---

## Q5. Other m-ex stock-icon touch points (outside the brief, listed so nothing is missed)

- `Easter Eggs/Apply Stock Icon`: `C2 0x80168C10` (gct+0x3538), inside `gm_80168BF8`. If the
  per-slot easter-egg byte (`rtoc + OFST_EasterEgg`) is not -1, the frame comes from
  `Stc_icns.eggs[egg].StockID` instead. Akaneia's `egg_num` = 0. The port can treat every slot as
  "no egg". INFERRED: it is only set by the easter-egg input code.
- `ResultScreen/Replace Results Stock and Emblem Matanim`: 0x80175E4C, which attaches Stc_icns to the
  results-screen stock jobjs. The results screen calls `gm_80168B34(ckind, cid, 0)` from
  `gmresultplayer.c:453/1067/1085/1102`, so once #1 is in place those take `cid` as the internal
  id. **Not verified** whether `cid` really is a FighterKind at every one of those sites.

---

## Implementation checklist (ordered)

1. **Load and cache Stc_icns natively.** On HUD init (`ifStatus_802F66A4`) and on CSS enter
   (`mnCharSel_Scene_OnEnter`), call `HSD_ArchiveGetPublicAddress(ifall, "Stc_icns")` on the
   IfAll archive (the US `IfAll.usd`). Keep it in a port global (not r13-0x4724). NULL means
   "not m-ex": keep retail behaviour everywhere below.
2. **Add an FK→mINT map** for the port: FK 0..26 → the same value; FK 27 MH → 35, 28 CH → 36, 29 Boy → 37,
   30 Girl → 38, 31 Giga → 39, 32 Sandbag → 40, **33 Sonic → 31**. Better, derive it from mexData
   `pl_file` names. Also a CK→mINT map for the All-Star/Multispawn path: `ftMapping_list[ck].internal_id`
   → FK → mINT, which covers CK 0x20 → FK 33 → mINT 31.
3. **Replace `gm_80168B34`** (`gm_1601.c:3992`). If `stc != NULL`, return
   `GetStockFrame(FK→mINT(arg1), arg2)` using the §1.1 formula (with `n = metadata.internal_id_count`,
   specials `{3,2,1,1,5,6}` for the last six). Otherwise keep retail. **Do not route
   `ifStatus_802F61FC`'s emblem call through this.** Give that call site its own
   `insignia_idx[mEXT]` path (Q3.4), or it will show a stock frame on the emblem atlas.
4. **Fix the arg1 = 0 callers:** `ifStock_802F96D0` (`ifstock.c:556`) and `ifStock_802F9F48_inline`
   (`ifstock.c:768`) pass `ftMapping_list[ckind].internal_id` (the port's FK) as arg1 when m-ex is active.
5. **Swap the matanim** after `gm_8016895C(...)` in `ifStock_802F98E8` (jobj indices 1..7),
   `ifStock_802F96D0` (index 1) and `ifStock_802F9F48` (index 1):
   `lb_80011E24(root, &j, idx, -1); HSD_JObjAddAnimAll(j, NULL, stc->matanim, NULL);`.
6. **1P CSS:**
   - At the 1P scene build (`mnCharSel_802640A0`, next to the existing `mnCharSel_MexAttach`), add
     `stc->matanim` to regend jobjs 53..57.
   - In `mnCharSel_MexPortrait`'s 1P/door-0 branch, after the retail call, set each of 53..57 to
     `GetStockFrame(mINT(icon), costume)` with `HSD_TObjReqAnimAll`, `AObjSetRate(0)` and
     `HSD_JObjAnimAll`.
   - Where the retail routine is called with hidden=1 in 1P (`mnCharSel_8025DB34` and
     `mnCharSel_CursorThink`), set frame 7 instead of 0xB9.
7. Optional: raise the port's Sonic costume count from 5 toward Akaneia's 7 (frames exist for all 7).
   Also apply Stc_icns on the results screen.
8. Verify: a VS match as Sonic (costumes 0..4) should show the icon at image 208+c; Fox, Sheik and
   GW should look unchanged; the 1P CSS dots should show Sonic, and the red ring when the slot is
   empty. Per memory, run off-screen with a pad script.

## Open questions

- **O1.** Will the port always load `IfAll.usd`? `IfAll.dat` (Japanese) has no `Stc_icns`, and
  without it every fix above silently reverts to retail. The IC-icon bug would return.
- **O2.** m-ex returns an undefined `f1` when Stc_icns is missing. The port should use the retail
  formula there. This needs a decision, not research.
- **O3.** The results screen (`gmresultplayer.c`): is its `cid` argument an FK at every call site?
  Is the Stc_icns attach at 0x80175E4C needed for Sonic's results icon? Not checked.
- **O4.** `costume_info` byte layout (count and team costumes) is INFERRED from the values. It
  should be checked against m-ex's `Icon Num/GetMaxCostumeID` before relying on 7 costumes.
- **O5.** Pikachu and Pichu costume-0 icons differ from retail in Akaneia's atlas. I assume this is
  intentional art, not a frame error.
