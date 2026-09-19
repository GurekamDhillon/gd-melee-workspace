# m-ex CSS: making Sonic selectable on the Character Select Screen

Status: research complete (2026-09-19). Nothing was built or run; every claim is marked VERIFIED (read from source or decoded from the disc) or INFERRED.

Index spaces used below (always stated explicitly):
- **port kind (FTKIND)** - the port's `FighterKind`; Sonic = 33 (vanilla 0..32).
- **m-ex internal kind** - Akaneia's m-ex internal fighter id; Sonic = 31.
- **m-ex external id** - index into mexData `fighter.names`; Sonic = 30.
- **CSS icon index** - position in the CSS icon table (vanilla 0..24/25).
- **CSS "char id" (CKIND / external char id)** - the vanilla CSS/`CharacterKind` space (Mario=0 ... ), used by `PlayerData`/scene data.

## 1. Vanilla CSS: how the icon grid is built (VERIFIED from decomp source)

All in `melee/src/melee/mn/mncharsel.c` unless noted.

### Data sources
- **`MnSlChr.usd`** (JP: `MnSlChr.dat`) is loaded in `mnCharSel_Scene_OnEnter` (`lbArchive_LoadArchive`),
  together with `MnExtAll.usd`. The only public symbol read is **`MnSelectChrDataTable`**
  (`MnSelectChrDataTable` struct at top of `mncharsel.c`: cam, 2 lights, fog, then 9 `StaticModelDesc`s:
  background, hand, token (puck), **menu**, press_start, debug_camera, **regend_menu** (1P layout),
  regend_options, door).
- **The icons are joints inside the single `menu` (VS) / `regend_menu` (1P) model.** Nothing in the
  disc file lists icons; the file just contains a hand-authored JObj tree where joint N is
  a given icon's background/face. There is no per-icon model or texture list the code iterates.
- **The icon -> character mapping, hit boxes and joint ids are a C table**: `static CSSIcon icons[]`
  (`mncharsel.c` ~line 173; DOL `0x803F0B24`, 25 entries + 1 trailing, 0x1C bytes each). `struct CSSIcon`
  is in `melee/src/melee/mn/types.h`:
  `ft_hudindex` (u8, portrait texture-anim frame base; `ICONHUD_*` in `mn/forward.h`),
  `char_kind` (u8, **CharacterKind / CKind space**), `state` (locked/temp/unlocked),
  `anim_timer`, `joint_id_vs` / `joint_id_1p` (joint index into `menu` / `regend_menu`; `ICONJOINT_*`
  in `mn/types.h`, range 0x04..0x22), `sfx` (announcer voice), `bound_l/r/u/d` (floats, cursor hit box).
- Icon **positions on screen** come from the joints' transforms baked into `menu`/`regend_menu`; the
  C bounds only mirror them for hit-testing. Exception: `mnCharSel_802640A0` moves the Luigi/Falco-row
  icons (`row_a`/`row_b` = icon 2 and 0x13) at runtime depending on `gm_IsCKindUnlocked(CKind_Luigi)`
  (sets `HSD_JObjSetTranslateY` and rewrites `bound_u/bound_d`).
- **Portraits (CSPs)**: `mnCharSel_8025D5AC(door, frame, hidden)` drives the door's
  `costume_joint`/`emblem_joint` (`mnCharSel_803F0DFC.doors[]`, a `CSSDoorsData`) to texture-anim
  frame `ft_hudindex + costume * 0x1E` (computed at the end of `mnCharSel_8025DB34`). So every
  portrait (all characters x all costumes) is a frame of one TObj animation inside `MnSlChr.usd`,
  laid out as 30 frames per costume row. A new character needs a new frame in that animation.
- Nametag text: `gm_80160980(icons[i].char_kind)` (`melee/src/melee/gm/gm_1601.c`) -> `lbl_803D4FDC`
  / `lbl_803D4D74` (CKind-indexed SJIS names, 32 entries + NULL). G&W special-cased by icon index 0x16.

### Functions that read the icon table
| function | role |
|---|---|
| `mnCharSel_Scene_OnEnter` | loads `MnSlChr.usd`, `MnExtAll.usd`, `SdSlChr.usd`, calls `mnCharSel_802640A0` |
| `mnCharSel_802640A0` | builds the scene: loads `menu`/`regend_menu` JObj, Luigi-row relocation, loop `icon < SELKIND_COUNT` sets `icons[i].state = gm_IsCKindUnlocked(char_kind)` and hides/animates locked icon joints (switch on icon index 0,8,9,17,18,24 = the unlockable ones), spawns cursors (`mnCharSel_CursorThink`) and pucks (`fn_80262648`), maps each player's saved `ckind` back to an icon by linear search `found < SELKIND_COUNT` |
| `mnCharSel_CursorThink` (~2394..3395) | hit-tests the puck against `icons[i].bound_*` for `i < SELKIND_COUNT`; on A writes `players[p].ckind = icons[sel_icon].char_kind`, plays `icons[sel].sfx` and `gm_80168C5C(char_kind)` (announcer) |
| `mnCharSel_8025DB34` | per-door refresh: name text, costume de-dup, CSP frame, team colours (`gm_80169264/80169290/801692BC(ckind)`) |
| `mnCharSel_8025D5AC` | portrait texture frame |
| `fn_8025F0E0` (~1675) | per-frame icon "pressed" animation, loop `i < SELKIND_COUNT` over `joint_id_1p/vs` |
| `mnCharSel_8025FB50` | random character (`HSD_Randi(SELKIND_COUNT)` until `state != 0`) |
| `mnCharSel_8025FDEC` | puck returned to a door: maps `players[].ckind` back to icon (`icon_idx < SELKIND_COUNT`) |
| `mnCharSel_CostumeChange` | `gm_GetNumCostumesForCKind(icons[sel].char_kind)` |
| `fn_802633B0`, `fn_80262648` | nametag / puck think; bounds and `sel_icon < 0x19` checks |
| `mnCharSel_Scene_OnExit` | `lbAudioAx_80026E84(players[].ckind)` to choose which fighter SFX banks to load for the match |

### The `0x19` sentinel (critical)
`CSSDoor.sel_icon == 0x19` (== `SELKIND_COUNT` == 25) means **"no character"** (puck in the door /
nothing hovered). This literal `0x19` / `0x19U` is hard-coded ~25 times in `mncharsel.c` (e.g. lines
1053, 1096, 1232, 1278, 1541, 1551, 2201, 2472, 2598, 3265, 3311, 3354, 3442, 3508, 3674, 3686,
3868, 4038) and the "no char" icon row is `icons[25]` (the `+1` entry). The G&W name hack uses
`sel_icon == 0x16`. **Appending Sonic as icon 25 collides with the sentinel.** The port already made
the array `icons[CSS_ICON_COUNT]` with `CSS_ICON_COUNT = SELKIND_COUNT + 1` (`TARGET_PC` branch,
~line 170) in anticipation of m-ex's "Icon Num" patches, but every literal `0x19` is still vanilla.

## 2. From icon to match: the index spaces (VERIFIED)

1. **Icon index** (`CSSDoor.sel_icon`, 0..24, 25 = none) -> `icons[sel_icon].char_kind`.
2. **CharacterKind / CKind** (`ft/forward.h` `enum CharacterKind`, 0..0x19 playable, 0x1A..0x20
   specials, `ChKind_None = ChKind_Max = 0x21`) is what the CSS writes:
   `mnCharSel_804D6CB0->vs.start.players[p].ckind` (`CSSData` -> `VsModeData` -> `StartMeleeData`
   -> `PlayerInitData[4]`, `mn/types.h` / `gm/types.h`). Also `.color` (costume) and `.team`.
   The `CSSData*` is the scene's enter-data pointer; the gm scene code copies `StartMeleeData` into
   the match.
3. **SelKind** (`SelectableCharacterKind`, `mn/types.h`, 0..0x18, `SELKIND_COUNT = 0x19`) - used by
   unlock logic and records. `ckind_to_selkind_map[ChKind_Max]` / `selkind_to_ckind_map[0x1C]`
   in `gm/gm_1601.static.h`. Many save-data/records arrays are `[SELKIND_COUNT]` (`gm/types.h`).
4. **FighterKind / port kind** (`ft/forward.h`, Sonic = `Ft_Kind_Sonic` = 0x21 = 33): at match
   start `pl/player.c` resolves `ftMapping_list[player->ckind].internal_id` (~line 229;
   `ftMapping_list[ChKind_Max]`).

**How the dev shortcut reaches Sonic (VERIFIED):** `pl/player.c` has, under `TARGET_PC`,
`ftMapping_list[ChKind_Popo /*0x20*/] = { Ft_Kind_Sonic, 0xFF }`. So in the port **Sonic's CKind is
0x20** (the vanilla "solo Popo" slot; its only other producer is an event-match special case in `gm/gm_17C0.c` ~line 655, see section 5). `MELEE_TARGET_TEST=32` writes ckind 32
(`gw_TestTargetTestCKind`, `melee/pc/platform/gw_runtime.c` ~line 818). This is a good choice for the
CSS too: CKind 0x20 is **inside** every `[ChKind_Max]` table (0x21 entries), so CKind-indexed C
tables do not overflow, but their entry 0x20 holds Popo/garbage data (see section 5).

## 3. What m-ex changes (VERIFIED from m-ex asm + Akaneia's `codes.gct`; described, not copied)

Tool: `tools/mex_port/dump_css.py` (new, read-only) decodes the data below from the ISO.

### 3a. Akaneia really ships these patches
`codes.gct` on `C:/iso/Akaneia.iso` parses to 1,163 Gecko codes (the same count as
`akaneia-dependency-scope.md`). **114 of them insert inside `mncharsel` (0x8025BC20..0x80266F3C)**, and
all 114 match the insertion address of an `asm/**` file in `C:/gdm/_build/m-ex`. (Checked with a
throwaway script: parse the C2/04/06 records, then index every m-ex `.asm`/`.s` by its
`#To be inserted at|@` address.)

| m-ex folder | codes | what it does |
|---|---:|---|
| `CSS Expansion/Icon Num` | 36 | Every compare against the retail icon count or the `0x19` sentinel is replaced by a load of the metadata **CSS icon count** (`OFST_Metadata_CSSIconCount`). "No character" becomes `sel_icon == icon_count`, and the loops run `< icon_count`. `SceneLoad2` (0x80264EEC) uses `count + 1` (the terminator row). |
| `CSS Expansion/Icon Data Ptr/Swap` (+4 `Orig`) | 35 (+4) | Every access to the retail icon table (`0x803F0A48 + 0xDC`) is redirected to a **pointer** (`OFST_MnSlChrIconData`) = `mexData.menu.css` (see 3b). The stride (0x1C) and field layout are the same, but field `+0x01` now holds an **m-ex EXTERNAL id**. |
| `CSS Expansion/HUD` | 10 | Rewrites the CSP (portrait) and emblem code. `Use External ID For CSP` (0x8025DB74) takes the portrait base from `icon.char_kind` (+0x01, the external id) instead of `ft_hudindex` (+0x00). `Costume Change Rewrite` replaces `mnCharSel_8025D5AC` (0x8025D5AC): the portrait frame is `ext_id + costume * mexSelectChr.CSPStride`, and the emblem frame is `fighter.insignia_idx[ext_id]`. `Replace CSS VS/SinglePlayer/Training Emblem` (0x80264574/0x80264548/0x80264A74): at scene build it attaches `mexSelectChr.CSPMatAnim` (an `HSD_MatAnim`) to each portrait DObj (VS `menu` joints 51..54) and IfAll's `Eblm_matanim_joint` to the emblem DObjs (joints 46..49), via `HSD_DObjAddAnim` (0x8035DEA0). It also patches the stock dots. |
| `CSS Expansion/mexSelectChr` | 7 (+2 Random) | `Load mexSelectChr` (0x80266984, in `mnCharSel_Scene_OnEnter`) looks up the public symbol `mexSelectChr` in the loaded MnSlChr archive (`mnCharSel_804D6CD0`) and stores it, or NULL. **Everything below runs only when that pointer is non-NULL; otherwise the retail code runs.** `Init mexSelectChr` (0x802647FC, inside `mnCharSel_802640A0`) scales the puck/cursor radii by `menu.param[0]`, hides the 25 retail icon joints in `menu`, and sets every m-ex icon to `state = 2` (unlocked, with **no unlock check**). It then creates a new GObj for the `mexSelectChr` icon model (with its animjoint/matanim) and skips the retail per-icon unlock loop (it branches to 0x80264924). `Skip Luigi Relocation` (0x802645F4) skips the Luigi/Falco row swap. `Cursor Detection` (0x80260BD4) hit-tests the cursor against `icon.bound_*` for `i < icon_count`, with +2.7/-2.0 offsets. `Icon Blink` (0x80260C8C) animates joint `i + 1` of the new icon model instead of `joint_id_vs`. `Random Fighter/*` turns off the retail bottom-corner random zones, re-routes random selection, and moves the right edge to 29.0 (float at 0x804DC49C). |
| `CSS Expansion/Misc` | 5 | The G&W name check moves from icon index (`sel_icon == 0x16`) to id (`char_kind == 3`). Kirby-costume preservation hard-codes CKind 4 instead of "icon 13". The 1P nametag Y comes from joint 78. Also `SkipResetMinorKind`. |
| `MnSlChrData Overwrites - ExtID Count` | 6 | In `Scene_OnFrame` and the think functions, the `ckind` range checks use metadata `FtExtNum` (41) instead of the retail count. |
| others (`HUD`, `MainMenu Expansion`, `menu`, `qol`, `gameplay`) | 7 | Not related to the character grid. |

Outside `mncharsel`, these patches are also on the CSS path:
- `Fighter Names/CSS.asm` (0x801609A8, in `gm_80160980`) reads names from `fighter.names[ext]`.
- `Icon Num/Get{Max,Red,Green,Blue}CostumeID` (0x8016923C..0x801692C0, in
  `gm_GetNumCostumesForCKind`/`gm_80169264`/`gm_80169290`/`gm_801692BC`) bound-check against
  `FtExtNum` and read m-ex's costume tables.
- `UserSelect ID/InitCSSPlayerStruct` (0x80167978).

### 3b. m-ex's CSS data (VERIFIED with `dump_css.py --iso C:/iso/Akaneia.iso`)
- `mexData` root +0x04 `menu` = { +0x0 `param` (floats 0.95, 0, -17, 0: hand/puck scale and SSS cursor),
  +0x4 **`css`**, +0x8 `sss` (0 here) }.
- `menu.css` is a relocated copy of the whole retail CSS data block that starts at DOL 0x803F0A48
  (`mnCharSel_803F0A48` in the decomp): 0x1C bytes of G&W name, then 24x8 bytes of mode info, then
  **the icons at +0xDC**.
- MexMetaData: internal 41, external 41, **CSS icon count 32**.
- The icon table has 32 icons in rows of 11/11/10. The relevant rows:

  | icon | ext id | name | joint | bounds l/r/u/d | sfx |
  |---:|---:|---|---:|---|---|
  | 0 | 22 | Dr. Mario | 1 | -32.96/-26.97/18.43/12.31 | 0xC5 |
  | 13 | 26 | Wolf | 14 | ... | 0xC7 (Fox's) |
  | 22 | 32 | Tails | 23 | -29.96/-23.97/6.19/0.07 | 0xCD |
  | **31** | **30** | **Sonic** | **32** | **23.97/29.96/6.19/0.07** | **0xC7 (Fox's)** |
  | 32 | - | terminator row, filled with 0x23 bytes | | | |

  `ft_hudindex` is 0 for every icon. It is unused, because m-ex takes the portrait base from the ext id.
  The table also has icons for characters the port cannot play (ext 26..29, 31 and 32: Wolf, Diddy,
  Charizard, Lucas, Dedede and Tails).
- `fighter.names` (+0x00) and the ext->internal map (`fighter` +0x0C, 3 bytes per ext id, the same
  shape as `ftMapping_list`):
  - ext 0..0x19 are the retail CKinds in retail order, with the retail internal kinds.
  - **ext 30 (0x1E) = "Sonic" -> internal 31.**
  - ext 0x20 = Tails -> internal 33.
  - ext 0x21 is "NONE".
  - ext 0x22.. are Master Hand, the Wireframes, Giga Bowser, Crazy Hand, Sandbag and Popo (retail
    0x1A..0x20, shifted by +8).

**Index-space warning (VERIFIED):** the same byte means different characters in the port and in m-ex:

| value | port CKind (`ft/forward.h`) | m-ex ext id (Akaneia) |
|---|---|---|
| 0x1E (30) | `CKind_CrezyH` | **Sonic** |
| 0x20 (32) | `ChKind_Popo` = **the port's Sonic** (via `ftMapping_list`) | **Tails** |
| 0x21 (33) | `ChKind_None` | "NONE" |

For port kinds: Sonic is `Ft_Kind_Sonic` = 33, and m-ex internal 33 is Tails. The m-ex icon table's
`char_kind` must **never** be written straight into `PlayerInitData.ckind`; it has to be translated.

### 3c. `mexSelectChr` (inside Akaneia's `MnSlChr.usd`, VERIFIED)
The retail `MnSlChr.usd` has one public symbol, `MnSelectChrDataTable`. Akaneia's has two:
`MnSelectChrDataTable` and **`mexSelectChr`**. The disc also has a standalone `mexSelectChr.dat`
(1.7 MB, public `mexSelectChr`), but the runtime patch reads the symbol from the MnSlChr archive. The
loose file is probably a mexTool export (INFERRED). Layout, from m-ex `Header.s` `SlChr_*`:

| off | field | Akaneia value |
|---|---|---|
| 0x00 | icon model `HSD_JObjDesc`: a root plus 32 child joints, one per icon (joint `i+1` = icon `i`). Each child has its own DObj with a 64x56 texture. | data+0x21ECF8 |
| 0x04 | icon `animjoint` | data+0x224D38 |
| 0x08 | icon `matanim_joint`: 32 texanims with no image lists, so it animates colour/blink only | data+0x224FCC |
| 0x0C | **CSP `HSD_MatAnim`**: one texanim with **221 images**, 136x188 CI8, plus 221 TLUTs. Only 56 pixel buffers are distinct, because costumes share indices and differ by palette. | data+0x2268D8 |
| 0x10 | **CSP stride** = 41 (the external id count) | 41 |

Sonic's portraits are CSP frames `30 + 41*c` for c = 0..4 (frames 30, 71, 112, 153 and 194), each with
a distinct image. HANDOFF says Sonic's `PlSn.dat` has 7 costumes, but the CSP anim covers only 5 rows
(221 = 5*41 + 16). So the CSS costume count has to come from m-ex's costume table, not from the CSP
(INFERRED; check `fighter.costume_info` before relying on this).

Note on `Init mexSelectChr`: it reads the field at +0x00 through a symbol, `SlChr_PositionModel`, that
`Header.s` never defines. That only assembles if the name resolves to 0, the same offset as
`SlChr_IconModel` (INFERRED; the Akaneia data at +0x00 is a valid JObjDesc tree, which supports this).

## 4. What Akaneia's `MnSlChr.usd` changes, and whether one icon can be added alone

### VERIFIED facts (a scratch script compared the `MnSelectChrDataTable` models on both discs)
| model | retail joints / texanims | Akaneia joints / texanims |
|---|---|---|
| `menu` (VS) | 173 / 87. **Joints 51..54 each have a 118-image texanim.** These are the 4 portrait (CSP) joints, `CSSDoor.costume_joint` 0x33..0x36. | 173 / **83. The 4 CSP texanims are gone.** |
| `regend_menu` (1P) | 79 / 43. Joint 45 (the portrait, 0x2D) has 118 images; joints 53..57 are stock icons with 129. | 79 / 42. **Joint 45's CSP texanim is gone**; the stock icons are kept. |
| `door` (1P CPU) | 10 / 2. Joint 6 has 118 images. | 10 / 1. **The CSP texanim is gone.** |
| everything else | identical counts | identical counts |

So Akaneia removed every retail portrait animation, which accounts for most of the 1.5 MB. It moved all
portraits into `mexSelectChr.CSPMatAnim` and added the `mexSelectChr` icon model. The 25 retail icon
joints are **still inside `menu`**; m-ex hides them at runtime. Akaneia's `IfAll.usd` also adds
`Eblm_matanim_joint` and `Stc_icns`, which retail does not have.

**Consequence (INFERRED from the data, not seen in a run):** on the Akaneia disc, the port's current
*retail* CSS code already shows **no portrait for any character**. `mnCharSel_8025D5AC` requests a
texture frame on joints that no longer have a texanim. So any CSS work on the Akaneia disc has to
implement m-ex's CSP path anyway, for all 25 retail characters and not just Sonic. This is cheap to
confirm: open the CSS on the Akaneia disc and look at a door.

### Option A: one extra icon on the retail layout
Keep the retail `menu` icons and code, and append one icon. This needs:
1. Art: an icon texture and CSPs for Sonic. On Akaneia these exist only in `mexSelectChr` (icon joint 32
   and CSP frames 30+41c), so the port has to read `mexSelectChr` regardless.
2. Portraits for *all* characters on the Akaneia disc (see the consequence above), which means the m-ex
   CSP path.
3. A free cell. The retail grid is 9/9/7, and the **bottom-row corners are the "random" hit zones**
   (`mnCharSel_CursorThink`: x in (-30,-24.4) or (24.4,30.2), y in (-1,6)). There is no spare cell:
   Sonic would have to replace a random corner, or the layout would have to be re-authored by hand
   (JObj translations and bounds).
4. Every `0x19` sentinel from section 1 still has to change, because index 25 becomes a character.

Verdict: on the Akaneia disc, A is **not** smaller than B. Items 1, 2 and 4 are exactly m-ex's work, and
item 3 is extra work that B avoids, because m-ex's data already has a 32-icon layout with bounds. A is
only cheaper on a *retail* disc, and Sonic does not exist there.

### Option B: adopt Akaneia's CSS data and reimplement m-ex's CSS logic in C
Use Akaneia's `MnSlChr.usd` as it is (it is what the disc has). Read `mexSelectChr` and
`mexData.menu.css`, and reimplement the m-ex behaviour in the decomp, with no PPC and no copied code:
- a data-driven icon table and icon count
- the icon model
- the CSP matanim and stride
- the emblems
- a count-based "no character" sentinel

Then **filter**: icons whose ext id has no port fighter (Wolf, Diddy, Charizard, Lucas, Dedede, Tails)
get `state = 0` and a hidden joint. The grid then shows 26 selectable icons with 6 gaps. Any CSS on
this disc needs all of this, so none of it is thrown away.

## 5. Vanilla-sized tables between the CSS icon and match start

Chain: **icon index** -> `icons[i].char_kind` (**CKind**) -> `PlayerInitData.ckind` -> `ftMapping_list[ckind]`
-> **FighterKind 33**. With the port's choice of CKind **0x20** for Sonic, every CKind table
`[ChKind_Max]` (0x21 entries) is *in bounds*, but entry 0x20 was authored for solo Popo or left as a
terminator. Tables sized to `CKind_Playable_Count` (0x1A), to `SELKIND_COUNT` (0x19), or to the icon
count are the real risk. "Crash?" says what happens at 0x20: **OOB** = read past the table,
**NULL/0** = in bounds but a fatal value, **wrong** = silently wrong data.

All entries below are VERIFIED by reading the source, unless marked INFERRED. None has been run.

### 5a. Inside the CSS (`mn/mncharsel.c`)
| # | table / site | sized | at Sonic | effect |
|---|---|---|---|---|
| 1 | `icons[]` (`CSSIcon`, 0x803F0B24) | 25 + 1 (port: `CSS_ICON_COUNT` = 26) | a new icon would be index 25 = the "no char" row | **OOB/aliasing.** Needs a table sized to the real count + 1. |
| 2 | literal `0x19` / `SELKIND_COUNT` sentinels and loops (~25 sites, listed in section 1) | 25 | icon 25 reads as "none"; an icon >= 25 never gets hit-tested, un-hidden, randomised or restored | **Sonic unselectable** until every site uses the icon count (m-ex `Icon Num` semantics). |
| 3 | `sel_icon == 0x16` G&W name special case (`mnCharSel_8025DB34`, `fn_802633B0` ~3870/4026) | icon index | wrong character gets G&W's name once icons move | **wrong**; compare `char_kind == CKind_GameWatch` instead (m-ex `Misc/GameWatchNameCheck*`). |
| 4 | `lbl_803D4FDC` / `lbl_803D4D74` names via `gm_80160980(ckind)` (`gm/gm_1601.c`) | 33 (32 + NULL) | index 0x20 = **NULL** | **NULL** string into `HSD_SisLib_803A70A0` (`sysdolphin/baselib/hsd_3A64.c`, a printf-style formatter) on every hover/select. Probable crash (INFERRED). The same table also feeds the in-match and results names. |
| 5 | `lbl_803D51A0` via `gm_GetNumCostumesForCKind` / `gm_80169264` / `gm_80169290` / `gm_801692BC` | `CKind_Playable_Count` (26), bounds-checked | returns **0** | `mnCharSel_CostumeChange` does `(costume + 1) % 0` on X: **integer divide by zero -> crash** on x86. Random-costume `HSD_Randi(0)` (random char, `mnCharSel_802640A0` training door). Team colour -> costume 0. `gmvs.c` ~1773 (`limit_costume_id`) forces costume 0. |
| 6 | `mnCharSel_802640A0` training/1P door guard `(s8) ck >= CKind_Playable_Count` (~4476) | 0x1A | 0x20 fails | Sonic is **replaced by a random character** in Training/1P. |
| 7 | `mnCharSel_802640A0` restore loop `found < SELKIND_COUNT` matching `players[].ckind` to an icon (~4569) | 25 | not found | ckind is reset to `CKind_Playable_Count` and a CPU slot is **closed**: Sonic's pick is lost every time you come back to the CSS. |
| 8 | `mnCharSel_8025FDEC` (puck return) `c_kind < CKind_Playable_Count` (~2129) | 0x1A | skipped | costume/icon restore is skipped (**wrong**, not fatal). |
| 9 | CSP frame `ft_hudindex + costume * 0x1E` (`mnCharSel_8025DB34` -> `mnCharSel_8025D5AC`) | the retail texanim has 118 images | there is no Sonic row. On Akaneia there is **no texanim at all** (section 4). | Portrait missing. It does not crash (INFERRED: an AObj request on a joint without a TObj anim is a no-op). |
| 10 | `icons[].sfx` announcer + `gm_80168C5C(ckind)` switch (`gm/gm_1601.c` ~4032) | switch | no case for 0x20 | silence (**wrong**). Akaneia itself gives Sonic 0xC7 (Fox's call). |
| 11 | `ckind_to_selkind_map[0x20]` (`gm/gm_1601.static.h`) -> `gm_IsCKindUnlocked` | 0x21 | `SELKIND_CAPTAIN` | Unlock check passes. Every SelKind consumer (records, KO counts, play time, `gmMainLib_8015D00C` in `gmvs.c` ~2310) books Sonic as **Captain Falcon** (**wrong**; no overflow). |

### 5b. CSS exit -> preload -> match start
| # | table / site | sized | at Sonic | effect |
|---|---|---|---|---|
| 12 | `lbAudioAx_80026E84(ckind)` -> `lbl_803BB3C0[ChKind_Max]` (`lb/lbaudio_ax.static.h`), called by `mnCharSel_Scene_OnExit` | 0x21 | entry 0x20 = `{0x0D, 0x2000}` (**Ice Climbers' voice bank**) | The match loads the IC SSM instead of Sonic's (**wrong**). Sonic's own sounds are in m-ex's SSM tables (`OFST_SSM*`), which the port does not read (INFERRED). |
| 13 | `mnCharSel_Scene_OnFrame` preload cache `entries[i].char_id = ckind` -> `lbDvd` -> `Player_80031CB0` -> `ftMapping_list[0x20]` -> `ftData_800855C8(33, color)` | `[ChKind_Max]` then `[Ft_Kind_Max]` | in bounds | OK: widened by the Sonic-clone work (`ft/ftdata.c` `ftData_SonicFallback`; `ft/fighter.c` `ftCommonData_ExtendKindTable`). Target Test already goes through this. |
| 14 | `ftMapping_list[ChKind_Max]` (`pl/player.c`) | 0x21 | `{Ft_Kind_Sonic, 0xFF}` under `TARGET_PC` | OK, this is the bridge. |
| 15 | every `[Ft_Kind_Max]` C table and the widened `PlCo.dat` tables | 34 | in bounds | OK for match start (HANDOFF section 4). |
| 16 | `gm_80168B34(ckind, ..)` stock/HUD icon frame (`gm/gm_1601.c` ~3982; in-match HUD `if/ifstatus.c` `ifStatus_802F61FC`) | branch on `ChKind_Popo` | frame 0xE (**IC's stock icon**) | **wrong** icon in VS HUD and on the CSS stock dots. m-ex swaps the stock matanim for IfAll's `Stc_icns` (`HUD/Replace Match Stock Matanim`), which the port does not do. |
| 17 | `gm/gm_17C0.c` ~655: an event-match special case writes `ChKind_Popo` (solo Popo) | - | now spawns **Sonic** | Pre-existing side effect of reusing 0x20. Only affects that event. |

### 5c. After the match (results; not needed for "selectable", listed so it is not a surprise)
| # | table | at Sonic | effect |
|---|---|---|---|
| 18 | `gm_80160438` -> `lbl_803D53A8[0x1B]` (results animation file per ckind, `gm/gm_1601.c` ~492) | no entry: it returns the terminator's path | Probably a NULL/garbage file name for the results screen: **likely crash** (INFERRED). m-ex uses `fighter.result_file` / `GmRst_AnimFiles[ext]`. `gm/gm_1798.c` ~571 null-checks one caller. |
| 19 | `ckind_victory_themes[0x1B]` (`gm_1601.c` ~285) | -1 | no victory theme (**wrong**). |
| 20 | `gm_80160474` -> `lbl_803B7978` / `79BC` / `7A00` (34 entries) | index 0x20 = 0 | in bounds; returns Mario's trophy/id 0 (**wrong**). 1P modes only. |

### 5d. Port kind 33 vs m-ex internal 31
On the CSS path, **nothing indexes by m-ex internal 31**. It appears only inside the fighter-data
widening (`loaded[31]` in `ftCommonData_ExtendKindTable`). The m-ex **ext id 30** does appear if m-ex's
icon table is read: portrait frame, emblem (`fighter.insignia_idx[30]`), name (`fighter.names[30]`),
m-ex costume tables. It must be translated to port CKind 0x20 before it reaches any retail table
(section 3b warning).

## 6. Recommendation

**Option B: reimplement m-ex's data-driven CSS in C, gated on `mexSelectChr` being present, with the
m-ex ext id translated to a port CKind at load time.**

Why:
- On the Akaneia disc (the only disc with Sonic), the retail portrait data is gone. The port *must*
  implement m-ex's CSP path to have a working CSS at all, so Option A saves nothing.
- m-ex's icon table already carries a correct 32-icon layout, with bounds, joint ids and art. No hand
  layout work is needed.
- It follows the project's established rule (port m-ex *behaviour*, attribute the source patch, copy
  nothing), and the port already loads `MxDt.dat` (`pc/platform/gw_mex_ftfunction_runtime.c`).
- Gating on `mexSelectChr` (as m-ex does) keeps the retail disc on the untouched retail path.

Trade-offs:
- It touches about 40 sites in `mncharsel.c` (the `Icon Num` and `Icon Data Ptr` equivalents). Each is
  mechanical but must be done completely: one missed `0x19` means a dead or aliased icon.
- The 6 unported characters' icons are present and must be hidden or locked, which leaves gaps in the
  grid. That is acceptable, but it is visible.
- Emblems, stock icons, names and sounds come from m-ex tables. Each needs a small port-side lookup
  keyed by ext id, so the ext<->port-CKind map becomes a load-bearing table.
- The CSS relies on Akaneia's asset layout (joint numbers 46..54, the `mexSelectChr` field order). Those
  are Akaneia/mexTool conventions, not something the port controls.

Rejected alternative: switch the port's CKind space wholesale to m-ex ext ids. That touches every
retail CKind table and save format, which is far too much for "one selectable fighter".

## 7. Ordered implementation checklist

Each step should be verifiable on its own (off-screen run, per memory rules; a pad script is needed to
drive the CSS).

1. **Measure first.** Boot the Akaneia disc to the VS CSS with no changes. Confirm the portraits are
   blank (section 4 inference) and that nothing crashes. This sets the baseline.
2. **Port-side accessors for m-ex menu data** (next to the existing MxDt loader): `menu.css` icon array
   pointer, `metadata.css_icon_count`, `fighter.names`, `fighter.insignia_idx`, the ext->internal map,
   and `mexSelectChr` lookup in the loaded MnSlChr archive (`HSD_ArchiveGetPublicAddress(mnCharSel_804D6CD0,
   "mexSelectChr")`, NULL on retail). Add the offsets to `tools/mex_port/dump_css.py` cross-checks.
3. **ext -> port CKind map** (one function): ext 0..0x19 -> identity. ext 30 -> `0x20` (the port's Sonic
   CKind; give it a name, for example `CKind_PortSonic`, instead of the bare `ChKind_Popo`). Anything
   else -> "not available". Also the reverse port CKind -> ext, for portraits/emblems/names.
4. **Data-driven icon table in `mncharsel.c`:** replace the static `icons[]` uses with a pointer and a
   count. In m-ex mode, fill a port-owned array of `count + 1` rows from `menu.css`: `char_kind`
   rewritten to port CKind, ext kept in a side array, and `state = 0` for "not available". The retail
   path keeps `icons[]` and count 25.
5. **Sentinel sweep:** every literal `0x19`/`0x19U` and `SELKIND_COUNT` loop in `mncharsel.c` that means
   "icon count" becomes the count (section 1 list; m-ex `Icon Num` is the checklist of sites, and
   `resolve_patches.py` maps each address to its decomp function). The G&W check (`0x16`) becomes a
   CKind compare.
6. **Icon model:** in `mnCharSel_802640A0`, when `mexSelectChr` is present: hide the 25 retail icon
   joints, spawn the `mexSelectChr` icon model GObj with its anims, skip the Luigi-row relocation, and
   use joint `i + 1` of that model wherever the code does `lb_80011E24(..., joint_id_vs/1p)` (blink,
   select animation, lock hiding). Hide the joints of "not available" icons.
7. **Portraits:** at scene build, attach `mexSelectChr.CSPMatAnim` to the portrait DObjs (VS 51..54,
   1P joint 45, the CPU door model's joint 6). In `mnCharSel_8025D5AC`, use frame
   `ext + costume * CSPStride`.
8. **Fix the section-5a fatal values for CKind 0x20:** name (from `fighter.names[ext]`, or a port-side
   name), costume count (non-zero; take it from m-ex's costume data or
   `CostumeListsForeachCharacter[Ft_Kind_Sonic].numCostumes`), and the `CKind_Playable_Count` guards
   in steps 6/7/8 of 5a (allow the port Sonic CKind).
9. **Emblems:** IfAll `Eblm_matanim_joint` plus `fighter.insignia_idx[ext]`. Optional for
   "selectable": without it the emblem shows a wrong/retail frame.
10. **Match-start correctness** (5b): Sonic's SSM bank instead of IC's (item 12) and the stock icon
    (item 16). Not needed to *pick* him, but needed so the match does not sound or look like IC.
11. **Results screen** (5c item 18) before calling it done: a VS match ends on the results screen, which
    is the first *crash* after the match.
12. Keep `MELEE_TARGET_TEST=32` working as the regression check for the fighter side.

## 8. Open questions

1. **Does the retail CSS code already run without crashing on the Akaneia disc** (blank portraits, 25
   retail icons)? The data says "blank portraits", but no run has shown it. Checklist step 1.
2. **Sonic's costume count on the CSS:** `PlSn.dat` reportedly has 7 costumes (HANDOFF), but the CSP
   anim has 5 rows (221 = 5*41 + 16). Which m-ex table does the CSS use for the count
   (`fighter.costume_info`? `Icon Num/GetMaxCostumeID` reads it), and what does it say for ext 30?
3. **Does `HSD_SisLib_803A70A0` accept m-ex's ASCII names** (`"Sonic"`), given that the retail names are
   full-width SJIS? m-ex feeds its ASCII names through the same function, which suggests yes
   (INFERRED).
4. **Random-select behaviour in m-ex mode:** `Random Fighter/*` turns off the retail corner zones and
   re-routes random selection. Which region selects random in Akaneia's layout, and should random
   include Sonic?
5. **The `Init mexSelectChr` field at +0x00** is read through an undefined assembler symbol
   (`SlChr_PositionModel`). The data is consistent with +0x00, but that is inferred, not proven.
6. **Unported characters:** hide their icons (gaps) or lock them (greyed)? Hiding matches the "icon
   joint hidden" mechanism already used for locked retail icons.
7. **Outside the CSS, found in passing:** `ftCommonData_ExtendKindTable` copies Akaneia's `PlCo.dat`
   entries 0..32 one-to-one. On Akaneia, 27..33 are m-ex's added fighters and the bosses moved to
   35..40 (per the comment in `ft/fighter.c`), so the port's `Ft_Kind_MasterH`..`Ft_Kind_Sandbag` read
   Wolf..Tails' entries there. This does not matter for Sonic, but it matters for boss modes and
   Sandbag (Home-Run Contest).
8. **1P modes** (Classic/Adventure/All-Star) use the same CSS through `regend_menu`. They add more
   per-CKind tables (`gm_80160474`, All-Star `gm_803DEBE8[CKind_Playable_Count - 1]`, the Classic
   opponent pools). Scope them out of the first pass (VS + Training) or audit them separately.

## Appendix: evidence commands (read-only)

```
python tools/mex_port/dump_css.py --iso C:/iso/Akaneia.iso            # mexData CSS table, names, ext map, mexSelectChr
python tools/mex_port/dump_css.py --iso C:/iso/Akaneia.iso --joints   # the icon model's 32 joints + translations
python tools/mex_port/dump_css.py --iso "C:/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"  # retail: no MxDt, no mexSelectChr
```
The retail-vs-Akaneia `MnSelectChrDataTable` texanim comparison and the `codes.gct` -> m-ex asm mapping
were one-off scripts. Their results are in sections 3a and 4; they are simple to re-derive with
`mex_hsd.Gcm`/`Archive`.
