# m-ex sound banks: what Sonic needs to play his own SSM

Status: COMPLETE (research only, 2026-09-19).
Research only - nothing built, nothing run. m-ex has no licence: behaviour is described, not copied.

## Sources
- m-ex asm: `C:/gdm/_build/m-ex/asm/m-ex/SSM/` (bank loader rewrites), `.../SFX/`, `Header.s`
- m-ex headers: `C:/gdm/_build/m-ex/MexTK/include/mxdt.h`
- decomp: `C:/gdm/melee/src/melee/lb/lbaudio_ax.c`, `lbaudio_ax.static.h`
- Akaneia disc: `C:/iso/Akaneia.iso` (MxDt.dat, audio/us/*.ssm, audio/us/smash2.sem)

## 0. Headline (VERIFIED unless marked)

- **Sonic's bank is `audio/us/sonic.ssm`, m-ex SSM id 66, 481,688 bytes on the Akaneia disc.**
  His SFX ids are therefore **660000..669999** (`id = ssm_id * 10000 + index`).
- The brief's "Sonic ssm_id 72" was read at the wrong index: `fighter.ssm_files` is indexed by the
  **EXTERNAL** character id (CharacterKind), not the internal kind. Entry [31] (ssm 72,
  `dedede.ssm`) is King Dedede; Sonic is external **30** -> ssm 66. Likewise "Fox = 8" was entry
  [1] = Donkey Kong (`dk.ssm`); Fox is entry [2] -> 11 = `fox.ssm`, identical to retail 0x0B.
  **m-ex numbering for the 55 retail banks IS retail numbering** (0..54 identical names/order);
  m-ex only appends banks 55.. (55 = `null.ssm`).
- `MexMetaData.ssm_count` on Akaneia is **78**, not 67 (67 is `sss_icon_count`).
- The u64 in each `ssm_files` entry is **vestigial**: m-ex never reads it. Every m-ex load path
  reads only the byte at +0 (`lbzx r3, ext_id*0x10, table`) and queues that ONE bank by index
  (`Audio_RequestSSMLoad`, m-ex standalone function at 0x800056A8). New fighters' masks are just
  their clone base's retail mask left over from mexTool (Wolf 0x800 = Fox's; Diddy/Sonic/Dedede/
  Tails 0x40000 = Mario's; Charizard 0x8000 = Bowser's; Lucas 0x200000 = Ness's). So "mask !=
  1<<id" is expected and meaningless. The u64 bank mask is not widened - it is **bypassed**.

Evidence: `python tools/mex_port/dump_ssm.py --iso C:/iso/Akaneia.iso` (new tool, read-only),
output reproduced in section 1.

## 1. `mexData.ssm` (root +0x10) decoded - VERIFIED

m-ex calls this block `Arch_FGM` (`_build/m-ex/asm/m-ex/Header.s:277-288`). It is 4 pointers.
`Load MxDt.asm` (`asm/m-ex/Load MxDt.asm:235-263`) copies them into the rtoc slot block:
`OFST_MnSlChrSSMFileNames` 0x24 <- Files, `OFST_SSMStruct` 0x60 <- RuntimeStruct,
`OFST_SSMIDDef` 0x64 <- FGM+0x0 (commented "unused now"), `OFST_SSMBankSizes` 0x68 <- Flags,
`OFST_AudioGroups` 0x90 <- LookupTable. Akaneia `MxDt.dat` data offsets (relocated at base 0):

| off | m-ex name | layout (per bank, `ssm_count` entries) | what it replaces in retail |
|---|---|---|---|
| +0x00 | `Files` @0x19418 | `char*` file name, no path (`"sonic.ssm"`) | `ssm_files[]` (`lbaudio_ax.static.h:~234`) |
| +0x04 | `Flags` @0x15EC | `{u32 size; u32 flag}` stride 8 ("ssm buffer sizes") | `offsets_arr_803BC4E4[][2]` |
| +0x08 | `LookupTable` @0x14B0 | `{s8 group; s8 load_prio; s8 unload_prio; s8 pitch_thresh}` stride 4 ("audio groups") | `s32_arr_803BB5D0[0x38][4]` |
| +0x0C | `RuntimeStruct` @0x19914 | 6 pointers: Header, ToLoadOrig, ToLoadCopy, IsLoadedOrig, IsLoadedCopy, Footer (s32 arrays) | the static block at `0x80433710` and `lbl_804337C4 / 804338A4 / 80433984 / 80433A64 / 80433B44` |

Field meanings, each cross-checked against the decomp:
- `size` = the .ssm file's header word [1] (sample-data byte count, i.e. ARAM needed). VERIFIED for
  sonic.ssm (`0x74E40` = 478,784 both in the file header and in the table) and main.ssm
  (2,045,664). Retail uses `offsets_arr_803BC4E4[i][0]` only for ARAM budget accounting
  (`fn_800268B4`, `fn_800267B0`, `fn_80026C04`, `lbAudioAx_8002838C`). m-ex also ships
  `CalculateBankSizes_Boot.s` / `_LangSwitch.s` (recompute sizes from the disc at boot) but they are
  NOT in Akaneia's codes.gct; Akaneia relies on the table.
- `flag` = retail's second column verbatim for 0..54 (main 0, pokemon 1, nr_select 1, captain 1,
  clink 0 ...). No decomp code reads it. Meaning UNKNOWN (INFERRED: a per-language flag).
- `group` = retail `s32_arr_803BB5D0[i][0]`: 1 = always resident (main, pokemon, end), 2 = nr_name,
  3 = menu narrator, 4 = fighter, 5 = stage, 6 = ending, 0 = null. Used by `fn_80023254` (budget
  sort) and, after m-ex, by `lbAudioAx_80026F2C` (m-ex rewrote it to reset by group instead of by
  the hard-coded u64 masks: flag 1 -> groups 1,2; 2 -> 3; 4 -> 4; 8 -> 5; 0x10 -> 6).
- `load_prio` = `[1]` (`fn_80026650` picks the next pending bank by this, 4 down to 0; 5 = never
  unloaded). `unload_prio` = `[2]` (`fn_800267B0`). `pitch_thresh` = `[3]`
  (`lbAudioAx_80023220`; `ft_80087D0C` applies the tiny/giant +1/+2 voice variant `ft_80087C70` to
  ids `>= bank*10000 + pitch_thresh`).
- For 0..54 the names, groups and priorities are identical to the retail tables; 55..77 are appended.
  Retail's 56th slot (index 55, "none") became `null.ssm` `{0,0,0,0}`. **m-ex numbering of the
  retail banks IS retail numbering.**
- RuntimeStruct arrays on Akaneia are 0x138 bytes = 78 words apart (Header 0x1330, ToLoadOrig
  0x11F8, ToLoadCopy 0x10C0, IsLoadedOrig 0xF88, IsLoadedCopy 0xE50, Footer 0xD18). m-ex's loops run
  to `ssm_count + 1` (79), one word past each array (latent m-ex overrun, harmless there because the
  arrays are packed). A port sizes them `ssm_count + 1`. The "Header" pointer exists only because
  the original code addressed the whole block from one base register (`0x80433710`, the m-ex
  "addi 14096" comments); a C port does not need it. m-ex's names map to the decomp as:
  ToLoadOrig = `lbl_804337C4` (requested), ToLoadCopy = `lbl_804338A4`, IsLoadedOrig =
  `lbl_80433984` (-1 / 1 loaded / 2 locked), IsLoadedCopy = `lbl_80433A64` (synth load handle),
  Footer = `lbl_80433B44` (size-sorted order from `fn_80023254`).

### All 78 banks on Akaneia (`dump_ssm.py` output; `disc` = file size, `tbl` = table size)

```
 id  file            disc_size  tbl_size flag grp lprio uprio thr
  0  main.ssm          2064992   2045664    0   1   5    5    0
  1  pokemon.ssm        497656    494336    1   1   5    5    0
  2  nr_title.ssm       153440    153056    0   3   0    0    0
  3  nr_select.ssm      240944    239264    1   3   0    0    0
  4  nr_1p.ssm          122704    121888    0   3   4    4    0
  5  nr_vs.ssm           54704     54176    0   3   4    4    0
  6  captain.ssm        433368    431328    1   4   2    3    4
  7  clink.ssm          301304    298400    0   4   2    3    7
  8  dk.ssm             208048    206368    0   4   2    3    7
  9  drmario.ssm        416472    413856    1   4   2    3    6
 10  falco.ssm          511424    507392    1   4   2    3    6
 11  fox.ssm            478240    474496    1   4   2    3    4
 12  gkoopa.ssm         490480    487968    0   4   2    1    0
 13  ice.ssm            465880    462688    1   4   2    3    9
 14  kirby.ssm          580440    576672    1   4   2    3    1
 15  koopa.ssm          518112    515392    1   4   2    3    8
 16  link.ssm           319904    317216    1   4   2    3    7
 17  luigi.ssm          375536    372992    1   4   2    3    2
 18  mario.ssm          375096    372768    0   4   2    3    1
 19  mars.ssm           516416    513088    1   4   2    3    7
 20  mewtwo.ssm         454808    451200    1   4   2    3    1
 21  ness.ssm           511632    509024    0   4   2    3    6
 22  peach.ssm          404832    402656    1   4   2    3    1
 23  pichu.ssm          561432    558976    1   4   2    3    1
 24  pikachu.ssm        607064    604320    1   4   2    3    7
 25  purin.ssm          336208    334528    1   4   2    3    1
 26  samus.ssm          311424    309536    1   4   2    3    6
 27  zs.ssm             584544    580064    1   4   2    3    2
 28  yoshi.ssm          323872    321472    1   4   2    3    1
 29  gw.ssm             161440    159904    1   4   2    3    6
 30  ganon.ssm          419736    417696    1   4   2    3    7
 31  emblem.ssm         484960    481696    1   4   2    3    6
 32  mhands.ssm         565368    563712    0   4   2    1    0
 33  kirbytm.ssm        576512    572704    0   4   2    1    0
 34  castle.ssm         176128    175616    0   5   2    2    0
 35  corneria.ssm       399488    397760    1   5   2    2    0
 36  greatbay.ssm       491184    490240    0   5   2    2    0
 37  kongo.ssm          360288    360064    0   5   2    2    0
 38  mutecity.ssm       150960    150144    0   5   2    2    0
 39  onett.ssm           54608     54080    0   5   2    2    0
 40  zebes.ssm          388880    387808    0   5   2    2    0
 41  garden.ssm         429408    428896    0   5   2    2    0
 42  klaid.ssm          305040    304128    0   5   2    2    0
 43  greens.ssm         144928    144480    0   5   2    2    0
 44  venom.ssm          339392    337600    1   5   2    2    0
 45  bigblue.ssm         35096     34784    0   5   2    2    0
 46  fourside.ssm        78688     78528    0   5   2    2    0
 47  pupupu.ssm         123520    123136    0   5   2    2    0
 48  pstadium.ssm       101792    101504    0   5   2    2    0
 49  1padv.ssm          161168    160576    0   5   2    4    0
 50  ending.ssm        1170784   1168864    0   6   1    1    0
 51  nr_name.ssm        475896    471168    1   2   5    5    0
 52  1pend.ssm          364160    363936    0   6   1    1    0
 53  last.ssm           663568    663136    0   5   2    2    0
 54  end.ssm              1664      1568    0   1   5    5    0
 55  null.ssm             1664      1568    0   0   0    0    0
 56  pcastle64.ssm       33376     33216    0   5   2    2    0
 57  hyrule.ssm          81296     81056    0   5   2    2    0
 58  mk64.ssm            18560     18336    0   5   2    2    0
 59  saffron64.ssm      181696    180864    0   5   2    2    0
 60  old_zebes.ssm      144440    143872    0   5   2    2    0
 61  volley.ssm         190080    189440    0   5   2    2    0
 62  wolf.ssm           314704    312032    0   4   2    3    7
 63  diddy.ssm          322864    320608    0   4   2    3    7
 64  lizardon.ssm       494176    491424    0   4   2    3    7
 65  lucas.ssm          564176    561280    0   4   2    3    6
 66  sonic.ssm          481688    478784    0   4   2    3    7   <-- Sonic
 67  village.ssm        223904    223328    0   5   2    2    0
 68  delfino.ssm        246336    245600    0   5   2    2    0
 69  greenhill.ssm      289632    289056    0   5   2    2    0
 70  mansion.ssm        350912    349888    0   5   2    2    0
 71  fichina.ssm        438112    435936    0   5   2    2    0
 72  dedede.ssm         286752    284352    0   4   2    3    1
 73  dolpark.ssm        755840    755040    0   5   2    2    0
 74  tails.ssm          304504    302048    0   4   2    3    7
 75  boxing.ssm         224352    223904    0   5   2    2    0
 76  bios.ssm           668960    667360    0   5   2    2    0
 77  saturn.ssm         227288    226144    0   5   2    2    0
```

**Sonic: bank 66, `audio/us/sonic.ssm`, 481,688 bytes on disc, 478,784 bytes of sample data,
header `{hdr 0xB40, data 0x74E40, 40 samples, global sample ids 1708..1747}`, group 4 (fighter),
pitch threshold 7.** All 23 appended files exist on the disc under `audio/us/`.

## 2. `fighter.ssm_files` (mexData.fighter +0x38) - VERIFIED

Layout `{u8 ssm_id; u8 pad[7]; u64 mask}`, stride 0x10: byte-for-byte the retail
`lbl_803BB3C0[ChKind_Max]` layout (`lbaudio_ax.static.h:~105`). m-ex's `mxdt.h` spells it
`{u8 ssm_id; int x04; int x08; int x0C}`, so "x08:x0C" is the u64 mask (hi:lo) and x04 is padding.
It is indexed by **EXTERNAL** character id (CharacterKind order: 0 C.Falcon, 1 DK, 2 Fox ...),
because every m-ex reader indexes it with `Player_GetPlayerCharacter` (`0x80032330`) or the CSS
match-info ckind. The m-ex header comment "indexed by ft_kind" is wrong for this table.

```
[ 0] 6 captain  [ 1] 8 dk      [ 2] 11 fox     [ 3] 29 gw      [ 4] 14 kirby  [ 5] 15 koopa
[ 6] 16 link    [ 7] 17 luigi  [ 8] 18 mario   [ 9] 19 mars    [10] 20 mewtwo [11] 21 ness
[12] 22 peach   [13] 24 pikachu[14] 13 ice     [15] 25 purin   [16] 26 samus  [17] 28 yoshi
[18] 27 zs      [19] 27 zs     [20] 10 falco   [21]  7 clink   [22]  9 drmario[23] 31 emblem
[24] 23 pichu   [25] 30 ganon  [26] 62 wolf    [27] 63 diddy   [28] 64 lizardon [29] 65 lucas
[30] 66 sonic   [31] 72 dedede [32] 74 tails   [33] 255 (NONE) [34] 32 mhands [35] 55 null (Boy)
[36] 55 null    [37] 12 gkoopa [38] 32 mhands  [39] 55 null (Sandbag) [40] 13 ice (Popo)
```

- For entries 0..25 and 34..40 the mask equals `1 << ssm_id` (retail values).
- For the 7 new fighters the mask is the **clone base's retail mask** left over by mexTool: Wolf
  0x800 (Fox's), Diddy / Sonic / Dedede / Tails 0x40000 (Mario's), Charizard 0x8000 (Bowser's),
  Lucas 0x200000 (Ness's). It is not an encoding of the id and there is no multi-word mask.
- **m-ex never reads the mask on its own load paths.** `Audio_LoadAll_Rewrite.asm` (C2
  `0x8002785C`, replaces all of `lbAudioAx_8002785C`), `Audio_CSSLeave_Rewrite.asm` (C2
  `0x801A56F4`, `gmVsMelee_ExitCss+0x74`) and `GetSSMIndex.asm` (`MEX_GetSSMID`, `0x800056A0`) all do
  `lbzx ssm, ext*0x10, table` and hand the byte to `Audio_RequestSSMLoad` (`0x800056A8`), which is
  just `if (ssm != 55 && ssm < ssm_count) ToLoadOrig[ssm] = 1;`. This is why banks >= 64 work at
  all: the u64 path (`lbAudioAx_8002702C`) can only name banks 0..63 (m-ex widened its loop bound to
  `ssm_count` at `0x80027140`, but the u64 shifts to 0 after bit 63).
- Where the vestigial mask still matters (INFERRED from call sites): the non-VS mode preloaders
  still call `lbAudioAx_80026E84` + `lbAudioAx_8002702C` (`gmclassic.c:940-975`,
  `gmadventure.c:1219-1236`, `gmallstar.c:474-484`, `gmevent.c:235-240`, `gmcameramode.c:153`,
  `gmdebugmode.c:442`); m-ex only re-pointed the table (`LoadCharID.asm`, 04 write `0x80026EA4`) and
  bounded it by `FtExtNum` (`CharSSM.asm`, C2 `0x80026E8C`). So in Classic etc. m-ex prefetches
  mario.ssm for Sonic. It is harmless because `lbAudioAx_8002785C` (m-ex rewrite, byte id) runs in
  `fn_8016E730` (`gmvs.c:2206`), the common match-start loader, and loads sonic.ssm synchronously.

## 3. `smash2.sem`: the other half of "SFX id -> sound" - VERIFIED

Retail's SFX-id scheme is already `bank * 10000 + index`. `AXDriver_8038CFF4`
(`src/sysdolphin/baselib/axdriver.c:547-563`) does `bank = id / 10000; mem = id % 10000;
script = bank_start[bank] + mem` and rejects `bank >= bank_count` or a script past the bank's end.
`bank_count` and `bank_start[]` come from `audio/us/smash2.sem`, parsed by `AXDriver_8038DA70`
(`axdriver.c:838-905`). The retail range table `s32_arr_803BB8D4` is just
`{b*10000, b*10000 + n_b - 1}`.

| disc | smash2.sem size | banks | scripts | bank 66 |
|---|---|---|---|---|
| vanilla v1.02 | 132,184 | 55 | 4,035 | - |
| Akaneia | 139,672 | **78** | 4,958 | start 4542, **118 scripts** |

Banks 0..50 are unchanged (51 `nr_name` grows 54 -> 62 scripts for the new announcer calls).
So **Sonic's SFX ids are 660000..660117.** The port reads `smash2.sem` from whichever disc it runs
(`lbAudioAx_80028690`, `lbaudio_ax.c:~2185`), so on Akaneia the AX driver ALREADY accepts bank-66
ids. What is missing is (a) the bank loaded into ARAM and (b) the ids being produced.
The sem scripts refer to samples by global sample id (1708..1747 for Sonic); the .ssm header
carries its own base id (`HSD_SynthSFXSampleLoadCallback`, `synth.c:65-110`, reads
`{hdr, data, count, base}`), so the synth needs no change.

## 4. How Sonic's code names his sounds: the 5000-relative convention - VERIFIED

Sonic's data never contains 66xxxx. It uses **ids 5000..9999 meaning "index (id - 5000) in the
OWNER FIGHTER's own bank"**:
- his ftcmd sound commands (opcode 0x11, `ftAction_80071B50`): relative ids 5001, 5004, 5007 ...
  5109 (21 distinct), plus ordinary main.ssm ids (0..527). Fox by contrast uses absolute 110001..,
  Mario 180001.. (scan of `PlSn/PlFx/PlMr.dat` for the 3-word SFX command).
- his `ftData->x4C_sfx` (`FtSFX`, `ft/types.h:563`): x4 5079, xC 5052, x18 5076, x28 5046,
  x2C 5067, x34 5000; smash-charge array 5031..5043; x20 {5088, 5091}. (Fox: 110070, 110040 ...
  110000.)
- the spring (`PlSn.dat` itFunction, OnSpawn code+0x70): `li r4, 5019; bl ft_80088478`.

m-ex turns these into absolute ids in four places (all four present in Akaneia's codes.gct):

| m-ex file | hook | decomp site | covers |
|---|---|---|---|
| `Subaction ID Override/SFX/FighterPitchShift.asm` | C2 `0x80087D28` | `ft_80087D0C+0x1C`, replaces `mr r3,r4` before `bl lbAudioAx_800233EC` | every fighter SFX path (`ft_PlaySFX`, `ft_800881D8`, `ft_80088328`, `ft_80088478`, `ft_80088510`, `ft_800885A8`, `ft_80088640`) |
| `.../ItemSFXBehavior0.asm` | C2 `0x8026AEBC` | `Item_8026AE84+0x38` (`item.c:2094`) | item SFX, owner = `Item+0xFCC` |
| `.../ItemSFXBehavior1.asm` | C2 `0x8026AF2C` | `Item_8026AF0C+0x20` | item SFX slot 1 |
| `.../ItemSFXBehavior2.asm` | C2 `0x8026AFC0` | `Item_8026AFA0+0x20` | item SFX slot 2 |

Semantics (my words): if `id / 10000 == 0` and `id >= 5000` (and, for items, the item has an owner
at `+0xFCC`), then `id = (id - 5000) + ssm_id(owner) * 10000`, where
`ssm_id(owner) = mexData.fighter.ssm_files[ext].ssm_id` and `ext` is the owner's EXTERNAL
character id read from the player block (`0x80453080 + fp->player_id * 0xE90 + 4`). Kirby (internal
kind 4) instead uses his copied ability's internal kind (`fp+0x2238`) and maps it to an external id
by searching `MnSlChrDefineIDs` (3-byte entries holding two internal ids each). Ids below 5000
(main.ssm commons) and absolute ids pass through unchanged. Because the remap runs first,
`lbAudioAx_800233EC` (KirbyTM swap) and the pitch-shift logic then see the absolute id.

So for Sonic: spring 5019 -> **660019**; 5001 -> 660001; smash charge 5031 -> 660031. All of his
relative ids (max 5109) are inside his 118 scripts.

**What the port does today (INFERRED from the decomp, not run):** 5001 reaches
`lbAudioAx_80023130`, which finds no retail range (main is 0..0x20F) and returns 55; nothing rewrites
it; `AXDriver_8038CFF4` computes bank 0, script 5001 >= 528 and returns -1. **Every Sonic-specific
sound is currently silent**; the ice.ssm load (port ckind 0x20 = `ChKind_Popo` via the dev remap,
`lbl_803BB3C0[0x20] = {0x0D, 0x2000}`) is wasted but harmless. Only his main.ssm ids play.

## 5. How m-ex loads banks beyond retail's 55 - VERIFIED (patch inventory)

m-ex does NOT widen the u64. It turns every fixed-size per-bank loop and table in `lbaudio_ax.c`
into one sized by `MexMetaData.ssm_count` (+1), with the tables coming from `mexData.ssm`, and it
adds a by-index request function. 141 injection sites under `asm/m-ex/SSM`, `Subaction ID
Override/SFX`, `SFX`, `SSS Expansion/StageAudio References` and `MnSlChrData Overwrites - IntID
Count` were mapped to decomp functions (scratch script over `resolve_patches.load_symbols` +
`config/GALE01/symbols.txt`). **136 of the 141 are present in Akaneia's codes.gct**
(`dump_gct.py --iso C:/iso/Akaneia.iso`); the 5 absent are `GetSFXIDBounds1/2` (0x800230F8 /
0x80023114, superseded), `CalculateBankSizes_Boot/_LangSwitch` (0x800286C4 / 0x80027ADC; sizes come
from the table) and `DEBUGFGM.s` (debug overlay).

Grouped by what they change (decomp function names; `+off` is the hook offset):

| concern | retail function(s) | m-ex change |
|---|---|---|
| bank of an SFX id | `lbAudioAx_80023130` (+0xC, +0x18) | body replaced by `id / 10000` (magic multiply `0x68DB8BAD`, `>>12`); upper bound `0x83D60` -> `(ssm_count+1)*10000` |
| same, inlined copies | `lbAudioAx_800233EC` +0x180/+0x18C/+0x244, `lbAudioAx_80023B24` +0x2C/+0x38 (sound test), `lbAudioAx_800237A8` +0xC | same `id/10000`, bound `(ssm_count+1)*10000`. **`lbAudioAx_800237A8` retail turns any id >= 540001 into silence - every Sonic id would be muted there without this** |
| bank bounds lookup | `lbAudioAx_800230C8` +0x10 | count check -> `ssm_count` (the table itself stays retail; its one real caller `ft_80087D0C` is patched at +0x2FC to use `lo = ssm*10000` instead) |
| pitch-variant threshold | `lbAudioAx_80023220` +0x8/+0x14 | bound -> `ssm_count`, table -> LookupTable `[3]` |
| fighter-bank voice variants | `ft_80087D0C` +0x30 (`Pitch Shift/Lookup.asm`) | retail `switch(ssm)` with hard-coded cases 6..33 replaced by "is this ssm id any fighter's `ssm_files[].ssm_id`" (searches `FtIntNum` entries); 0 and 13 keep their retail branches |
| relative ids 5000..9999 | `ft_80087D0C` +0x1C, `Item_8026AE84` +0x38, `Item_8026AF0C` +0x20, `Item_8026AFA0` +0x20 | section 4 |
| per-character bank | `lbAudioAx_80026E84` +0x8 (bound `FtExtNum`), +0x20 (table -> `ssm_files`) | mask path kept for prefetch only |
| per-stage bank | `lbAudioAx_80026EBC` +0x34, `lbAudioAx_8002785C` +0x1B8 | table -> `Map_Audio` (`MexStageSound {u8 ssm; u8 reverb; u8 x2}` stride 3, per internal stage id) |
| match-start load | `lbAudioAx_8002785C` (whole function, 592 B) | per player: `ssm_files[ext].ssm_id` -> `Audio_RequestSSMLoad`; stage: `Map_Audio[gr].ssm`; keeps the Kirby-event (stage 217/229 -> mask 0x200004000) and stage 70/71 (0xC00) extras via the u64 path; sets DSP/echo from `Map_Audio[gr].reverb`; then `lbAudioAx_80027168` + wait on `fn_80027488` |
| CSS / SSS exit | `gmVsMelee_ExitCss` +0x74, `gmVsMelee_ExitSss` +0x54 | same by-index request (CSS: 6 match-info slots, stride 36, ckind at +0x70) |
| request by index | new `Audio_RequestSSMLoad` @ `0x800056A8` | `ToLoadOrig[ssm] = 1` if `ssm != 55 && ssm < ssm_count` |
| cache reset | `lbAudioAx_80026F2C` (whole) | reset `ToLoadOrig[i]` by LookupTable group instead of u64 constants |
| mask -> request | `lbAudioAx_8002702C` +0xA4 (array), +0x114 (bound) | loop to `ssm_count` (still u64-limited to banks 0..63) |
| loader state machine | `fn_80026650` +0x14/+0x30, `fn_800267B0` +0x14..+0xD0, `fn_800268B4` +0x4..+0x2C, `fn_800269AC` +0x30/+0x4C, `fn_80026C04` +0x24..+0x234, `fn_80026E58` +0x8, `lbAudioAx_80027168` +0x30..+0x2FC, `fn_80027488` +0x14, `lbAudioAx_80027648` +0x24/+0x4C | every `55`/`56` loop -> `ssm_count(+1)`, every array -> RuntimeStruct, every size -> Flags table, every group/priority -> LookupTable, every `ssm_files[i]` -> Files |
| budget sort | `fn_80023254` (whole, `InitFooter - Rewrite.asm`) | same insertion sort over `ssm_count` banks, heap temp array |
| audio init | `lbAudioAx_8002838C` +0x1C..+0x23C, `lbAudioAx_80028690` +0x20..+0x358 | arrays/sizes from mexData; bank-2 budget still = largest group-3 + 4 largest group-4 + largest group-5 (now over all 78) |
| language | `lbLang_IsSavedLanguageJP/US` +0x10, `lbAudioAx_80027AB0` +0x20..+0x2A0 | forces US: the size table only describes `audio/us/` files |
| synth | `HSD_SynthSFXLoad` +0x7C | assert with "audio file %s does not exist" when a bank file is missing; `HSD_SynthSFXSampleLoadCallback` +0x44 is a no-op rewrite of the original `addi r4,r4,55` |
| narrator name | `gm_80168C5C` +0x10 | `lbAudioAx_800243F4(announcer_call[ext])` (Sonic ext 30 -> **510059**, in nr_name.ssm, whose sem grew to 62 scripts) |
| misc | `lbAudioAx_80027DF8` +0x400 (`PersistentSoundOverride`, 04 `bne +0x20`), `un_802FF7DC` +0x94 (SFX debug menu bound) | not needed for Sonic (open question 4) |

## 6. What the port must change - ordered checklist

The port runs the DECOMP (C) audio code, so each m-ex patch becomes a C change in
`src/melee/lb/lbaudio_ax.c` / `.static.h` (TARGET_PC-guarded), not guest code. `shim_ax.c` (the AX
voice mixer) needs **no change**: it plays whatever ARAM the synth fills, and ARAM is 16 MiB
(`pc/platform/gw_runtime.c:48`).

1. **mexData accessors** (`pc/platform/gw_mex_ftfunction_runtime.c`, next to the item-lookup
   ones). Expose, when MxDt.dat is loaded: `ssm_count` (metadata +0x1C), `Files`, `Flags`,
   `LookupTable` (mexData +0x10 -> +0x0/+0x4/+0x8) and `fighter.ssm_files` (fighter +0x38,
   stride 0x10, **EXTERNAL** index) and `fighter.announcer_call` (+0x34). Add a port-kind ->
   m-ex EXTERNAL id map beside the existing port-kind -> internal map (`GW_MEX_KIND_SONIC` 33 ->
   external **30**; internal 31 is a different index space). Hard-error on unknown kinds, as the
   item code does.
2. **Bank table source.** Replace the fixed `ssm_files[]`, `offsets_arr_803BC4E4`,
   `s32_arr_803BB5D0` reads with accessors returning the mexData entry when loaded and the retail
   one otherwise (vanilla disc keeps working). Bank count `N = mex ? ssm_count : 55`.
3. **Widen the runtime arrays.** `lbl_804337C4/804338A4/80433984/80433A64/80433B44` are
   `[0x38]`; make them `[GW_MEX_SSM_MAX + 1]` (m-ex's own ceiling is `SSM_MaxID = 100*10000`, so
   101 is safe) and change every `55`/`56`/`0x38` loop in `fn_80023254`, `fn_80026650`,
   `fn_800267B0`, `fn_800268B4`, `fn_800269AC`, `fn_80026C04`, `lbAudioAx_80026F2C`,
   `lbAudioAx_8002702C`, `lbAudioAx_80027168`, `fn_80027488`, `lbAudioAx_8002838C`,
   `lbAudioAx_80028690` to `N` (keep the special indices 0, 1, 0x33, 0x36, 0x21 - they are the same
   banks in both numberings).
4. **SFX id -> bank.** `lbAudioAx_80023130`: return `id / 10000` when `0 <= id < (N+1)*10000`,
   else `N`-as-none (retail returns 55 = "none"; with mexData 55 is `null.ssm`, so use a separate
   sentinel or keep 55 and make callers treat it as none - m-ex keeps 55 as the "no bank" value in
   `Audio_RequestSSMLoad`). Same bound in `lbAudioAx_800233EC`, `lbAudioAx_80023B24` and, most
   importantly, **`lbAudioAx_800237A8` (`id >= 0x83D61` -> silence) must become `>= (N+1)*10000`**.
   `lbAudioAx_800230C8` / `lbAudioAx_80023220`: bound `N`; lo = `ssm*10000`; thresh = LookupTable[3].
5. **Request by index; stop using the mask for mex fighters.** Add
   `lbAudioAx_RequestBank(int ssm)` (= `Audio_RequestSSMLoad`). In `lbAudioAx_8002785C` and
   `gmVsMelee_ExitCss`, for each player use `ssm_files[ext].ssm_id` (mex) instead of OR-ing
   `lbAudioAx_80026E84` masks; keep the mask path for the Kirby/stage extras and the other modes'
   prefetchers (harmless, section 2). Minimal Sonic-only variant: when a player's port kind is
   `Ft_Kind_Sonic`, request bank 66 and skip his mask. `ChKind_Popo`'s own entry
   (`lbl_803BB3C0[0x20]`) is shared with real Popo, so do NOT edit that table entry.
6. **Relative ids (5000..9999).** In `ft_80087D0C` before `lbAudioAx_800233EC`: if
   `id / 10000 == 0 && id >= 5000` -> `id = id - 5000 + ssm_of(fp) * 10000`, with `ssm_of` = the
   owner's `ssm_files[ext].ssm_id`, and Kirby resolved through his copied kind (`fp+0x2238`,
   `MnSlChrDefineIDs`). Same rule in `Item_8026AE84`, `Item_8026AF0C`, `Item_8026AFA0` using
   `Item+0xFCC` (the port already grew `Item` to 0xFD0 with the original owner at +0xFCC). This is
   the step that makes the spring's 5019 play (660019) and all his moves/voice.
7. **Voice-variant generalisation.** `ft_80087D0C`'s `case 6..31, 33` list: treat any bank that
   is some fighter's `ssm_id` (m-ex searches the table) like those cases, with `lo = ssm*10000`
   and `thresh = LookupTable[ssm][3]` (Sonic: 7). Without it tiny/giant Sonic just uses the normal
   pitch - cosmetic.
8. **Budget.** Nothing to change for Sonic alone: bank 2 is sized from the retail table (4
   largest group-4 banks, ~2.37 MB), and sonic.ssm (478,784) is smaller than the 4th largest, so any
   4-fighter mix fits. If step 2 swaps in the mexData sizes, recompute the budget from them (m-ex
   does, `lbAudioAx_8002838C`); `dolpark.ssm` (755,040) would then raise the stage slot.
9. **Language.** Load from `/audio/us/` whenever mexData is present (m-ex forces US; the new banks
   exist only there). `smash2.sem` is read from the same directory and is already the widened one
   on Akaneia.
10. **Announcer / results (with the CSS work).** `gm_80168C5C`: for mex fighters play
    `announcer_call[ext]` (Sonic 510059). Victory theme is `victory_theme[ext]` (Sonic 125, a BGM
    index - out of scope here).
11. **Verify** (for whoever may run the game): pad script into a VS match as Sonic; log
    `lbAudioAx_80023870`/`AXDriver_8038CFF4` ids and return values; expect 660xxx ids with a voice
    id >= 0, and `sonic.ssm` in the loaded set (`lbl_80433984[66] == 2`). Test the spring
    (660019), a smash charge (660031..660043), and a vanilla fighter in the same match (their
    bank must still load). Memory note: audio tests need a pad script, the opening cinematic is
    silent.

## 7. Open questions

1. `Flags[i].flag` (second word) is unused by all decomp code seen; its meaning is unknown.
2. Crowd cheer (`ftLib_8008746C` -> `FtSFX.x34`, `crowdsfx.c:247`) is 5000 for Sonic and is
   played WITHOUT going through `ft_80087D0C`, so m-ex plays bank 0 script 5000 = nothing
   (INFERRED). The port can match that (silent) or remap it; no m-ex patch covers it.
3. Other fighter SFX paths that bypass `ft_80087D0C` (e.g. direct `lbAudioAx_80023870` /
   `lbAudioAx_800263E8` sound objects from common fighter code) would also not remap a relative
   id. Not audited exhaustively; the 7 ft_ play helpers + 3 item helpers are what m-ex patches.
4. `PersistentSoundOverride.asm` (04 `bne +0x20` at `lbAudioAx_80027DF8+0x400`) - its effect was
   not traced; `lbAudioAx_80027DF8` is the per-frame audio process. Not needed to hear Sonic.
5. Runtime cost: `lbAudioAx_8002785C` loads synchronously; sonic.ssm is 478 KB from DVD emulation
   - irrelevant on PC, noted only.
6. Where the port will get "external id" for a player whose CharacterKind is the dev remap
   (`ChKind_Popo` -> Sonic): step 1's map should key on the FIGHTER (port kind 33), not on the
   player's ckind, until the proper m-ex CSS lands (`_research/mex-css.md`).

## Tools / reproduction

- `tools/mex_port/dump_ssm.py --iso C:/iso/Akaneia.iso` (new, read-only): mexData.ssm tables, bank
  list with disc and table sizes, and `fighter.ssm_files` by external id.
- smash2.sem bank table: parse `{n0,[n0]} {n1,[n1]} {nbanks, start[nbanks]} {nscripts, ...}` per
  `AXDriver_8038DA70` (a 20-line script; not committed).
- `.ssm` header: 4 big-endian words `{header_size, data_size, sample_count, first_sample_id}`.
- `dump_gct.py --iso C:/iso/Akaneia.iso --addr <hook>` confirms each hook is shipped;
  `ppc_disasm.py --dol C:/gdm/_build/orig_main.dol --start 0x80087D0C` shows the vanilla code the
  hooks land on.
