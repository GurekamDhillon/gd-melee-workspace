# m-ex patch triage — insertion addresses resolved to decomp symbols

- m-ex checkout: `/mnt/c/gdm/_build/m-ex`
- symbol table: `melee/config/GALE01/symbols.txt` (34690 sized symbols)
- `.asm` files scanned: 1169
- files with an `#To be inserted at <addr>` directive: 1169
- insertion addresses: 1169

**Resolved to a decomp function: 1130/1169 (96.7%)**

## By category

| inserted | resolved to a function | category |
|---:|---:|---|
| 1041 | 1009 | `asm/m-ex` |
| 36 | 31 | `asm/qol` |
| 30 | 29 | `asm/debug` |
| 26 | 25 | `asm/menu` |
| 22 | 22 | `asm/Additional` |
| 14 | 14 | `asm/gameplay` |

## Most-patched decomp functions

| patches | function |
|---:|---|
| 26 | `mnCharSel_CursorThink` |
| 26 | `mnStageSel_Scene_OnEnter` |
| 25 | `lbAudioAx_80028690` |
| 22 | `mnCharSel_802640A0` |
| 14 | `gm_8017CE34` |
| 14 | `lbAudioAx_80027168` |
| 13 | `mnCharSel_8025DB34` |
| 13 | `lbAudioAx_8002838C` |
| 11 | `fn_80262648` |
| 11 | `fn_80026C04` |
| 10 | `fn_8018325C` |
| 10 | `gmClassic_801B3500` |
| 10 | `ftKb_SpecialN_800EED50` |
| 9 | `fn_80184138` |
| 9 | `ftData_800855C8` |
| 9 | `lbAudioAx_80027AB0` |
| 7 | `fn_802633B0` |
| 7 | `mnCharSel_8025FDEC` |
| 7 | `gmRegSetupEnemyColorTable` |
| 7 | `efAsync_LoadSync` |
| 7 | `lbDvd_80017960` |
| 7 | `runGameMode` |
| 6 | `mnCharSel_CostumeChange` |
| 6 | `gm_80182174` |
| 6 | `ftParts_800750C8` |
| 6 | `mn_8022B3A0` |
| 6 | `mnStageSel_Scene_OnFrame` |
| 6 | `mnStageSel_80259ED8` |
| 6 | `fn_8025A090` |
| 6 | `fn_8025A560` |
| 6 | `ftCo_SpecialAir_CheckInput` |
| 5 | `Fighter_Spaghetti_8006AD10` |
| 5 | `fn_80185D64` |
| 5 | `mnCharSel_8025FB50` |
| 5 | `Fighter_Create` |
| 5 | `Fighter_UnkInitLoad_80068914` |
| 5 | `ftKb_SpecialN_800EEC34` |
| 5 | `fn_8017A318` |
| 5 | `fn_800267B0` |
| 5 | `Camera_8002C5B4` |

## Unresolved addresses

| address | patch |
|---|---|
| `0x80005694` | `asm/m-ex/Slippi Compatibility/AdjustNullCharID.asm` |
| `0x800056BC` | `asm/m-ex/Slippi Compatibility/CSPUpdate.asm` |
| `0x80005690` | `asm/m-ex/Slippi Compatibility/CheckAltStageName.asm` |
| `0x800056B8` | `asm/m-ex/Slippi Compatibility/GetCSSIconData.asm` |
| `0x80005698` | `asm/m-ex/Slippi Compatibility/GetCSSIconNum.asm` |
| `0x8000569C` | `asm/m-ex/Slippi Compatibility/GetFighterNum.asm` |
| `0x8000561C` | `asm/m-ex/Slippi Compatibility/SceneCheck.asm` |
| `0x800056A8` | `asm/m-ex/Standalone Functions/Audio_RequestFileLoad_Rewrite.asm` |
| `0x800056A0` | `asm/m-ex/Standalone Functions/GetSSMIndex.asm` |
