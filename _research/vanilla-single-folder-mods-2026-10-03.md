# Every mod works on the vanilla disc, as ONE folder - design (2026-10-03)

**Supersedes** the "approach C (filtered base) is the chosen design" conclusion of `docs/mods-packaging.md` section 3
and the "entity mods combine only within one pack; at most one base" limits of its section 8, *as the target
state*. Those sections still describe what the code does today. It does not supersede anything about the file overlay,
netplay identity or `mod.json` resolution, which stay.
Evidence for every "VERIFIED" tag is either a run in `_build/audit-20261003/vanilla-mods/RUNS.md` (cited as RUNS case N)
or a read of the cited code. "INFERRED" means reasoned, not run.

Owner requirement (verbatim): "moving forward. we need all mods to work on vanilla, with ONE mod file/archive/folder. Like
Sora in one, the lab in one, etc, etc. idk how we did it previously. at some point I launched the game with a vanilla disk,
but a modded character in the mod loader, and it didn't work."

---

## 0. The headline, because it corrects the brief

1. **Vanilla + the Sora mod works at the engine level today** (VERIFIED, RUNS case 2, 2b). The mod loads, its files mount, the m-ex
   runtime activates, Sora is CharacterKind 34 / FighterKind 33, spawns in the LAB, the CSS roster lists it (`roster ...,34`), Geno
   loads its profile. Nothing stops. Sora is not broken on vanilla; it is **only legal and only coherent because it smuggles a
   whole ACE disc's tables in with it**.
2. Why it works: the m-ex layer is not keyed to the disc. It keys on "does `MxDt.dat` resolve through the file layer?"
   (`gw_mex_ftfunction_runtime.c:392-420`, `gw_mexdt_load` reading through `gw_mex_load_hsd("MxDt.dat",...)`, which goes through the
   DVD overlay so a mod's copy wins). Sora's `files/` contains `MxDt.dat`, `MnSlChr.usd`, `PlCo.dat`, `IfAll.usd`, all cloned
   from the ACE disc (`INSTALL.json` -> `slot_files.base`: `"disc"`; byte-identical to the ones on the ACE run, RUNS case 6).
   On vanilla the mod's `MxDt.dat` is the first and only one, so the m-ex layer turns on with ACE's 65-row fighter table, 155 stages, 103 sound banks;
   all fighter rows except row 52 are then dropped with `m-ex fighter N's PlXx.dat is not on the disc or in a mod - skipped`
   (`gw_mex_ftfunction_runtime.c:1066-1100`) and 1 slot remains.
3. What the owner most likely saw ("it didn't work") is therefore **not established**. I could not reproduce a failure of the
   engine path. Candidates, none proven: (a) a mod whose `files/` lacked the four table files and that relied on `requires: ace-base`
   (every `split_modpack.py` fighter mod `requires: ["ace-base"]`, `docs/mods-packaging.md` section 4/5; with the base absent the
   resolver drops it as `needs ace-base (not installed)`, `gw_mods.c:394-440`), i.e. any mod from the 2026-09-22 split packs; (b) Brawl
   Kirby / Meta Knight built before the tables were carried inside the mod (the Meta Knight mod today says "Carries brawl-kirby-slot's shared tables
   too", `ports/halberd/mods-slot/metaknight-slot/mod.json`); (c) the CSS or in-match audio on vanilla, which I did not drive
   (no pad, no audio check). **The owner should be asked which mod and how it failed** (decision D1 below); until then treat the
   vanilla failure as "unreproduced".
4. The real problems with the current approach are exactly the two the owner named plus a third:
   - **Legal:** the Sora folder ships ~38 MB of which 4 files are disc-derived whole files (MxDt, MnSlChr, PlCo, IfAll) and `PlUs.dat` /
     `PlUsAJ.dat` embed bytes of the ACE (= vanilla) host fighter's `PlMs.dat` / `PlMsAJ.dat` (`install_ultimate.py:962-967`,
     `host_aj[off:off+size]`; header line 16, 35-36: "Output is disc-derived"). The project's rule ("No disc-derived data is ever committed", `CLAUDE.md`)
     therefore only holds because mod folders live under git-ignored `_build/`. They can never be a release artifact.
   - **Coupling:** the mod's row 52/51 *replaces* ACE's "Wolf SSBU" row (`INSTALL.json` -> `row.replaces`); it silently deletes an ACE fighter, and it
     can never coexist with Meta Knight (same row; `conflicts: ["metaknight-slot"]`).
   - **Wrong on Akaneia:** the mod's `MxDt.dat` overrides Akaneia's (INFERRED from the overlay rule, `shim_dvd.c:232`, later mod wins a path); Akaneia's 7 fighters
     would vanish and ACE rows would point at files Akaneia lacks.

---

## 1. How it works today (VERIFIED by code unless tagged)

### 1.1 Mod discovery and mounting
- Folder: `MELEE_MODS_DIR`, else `mods\` beside `melee-pc.exe`; `tools/port/run.sh` sets `MELEE_MODS_DIR` to `_build/mods` (`run.sh:106`).
  `docs/HANDOFF.md` section 6 "Content selection": `MELEE_MODS_DIR` is the parent of packs, not one pack.
- `enabled.txt` (`gw_mods.c:342-370`, layout comment `gw_mods.h:1-35`): one id per line, `#` comments; ABSENT = every mod enabled; names not installed are ignored with a log line.
- `mod.json` is a flat object (`gw_mods.c:199-217`): `name version kind pack description hash` as strings, `requires`, `conflicts` as string lists (max 8 each, `GW_MODS_LIST_MAX`),
  `engine` as `{feature: version}` (`gw_mods.c:219-290`; the only feature this build knows is `pobj_palette: 1`). Folder name is the id; a different `"id"` is logged and ignored (`gw_mods.c:200-206`).
  `kind` is `base|fighter|stage|misc|script`; anything else becomes `misc` (`gw_mods.c:329-333`). Fields the loader does NOT read: `api_version`, `gameplay`, `rollback_safe`, `entry`, `author`: those are Lua-side
  manifest fields read by `gw_script.c` (`docs/scripting.md` line 79 onward).
- Resolution (`gw_mods.c:375-470`): drop mods whose `requires` is not mounting (`needs X`), drop mods that `conflicts` with an earlier one in pass order, and **two `base` mods always conflict** (`mods_conflict`, `gw_mods.c:381-391`). Pass/mount order: requirements first, then base < misc/script < fighter/stage, then id.
- Overlay (`shim_dvd.c:203-283`): every file under `<mod>/files/` (or, with no `files/` folder, the whole mod folder: "legacy layout") answers the disc path of its relative position; it overrides the disc entry in place (keeps the entry number) or is added past the FST end; a later mod wins a path (`shim_dvd.c:232`, logged). For a no-`files/` mod, `mod.json` and `scripts/` are skipped (`shim_dvd.c:214-217`) but everything else (art/, ui/, models/, geno.json) is mounted as disc paths: LAB 90 paths, map editor 50 paths (RUNS case 3, 4). Harmless but it pollutes the netplay mod fingerprint (`gw_Mods_NoteFile`).
- Not disc files and read by name from the mod folder: `scripts/*.lua` (`gw_script.c`), `geno.json` (`geno_registry.c:1271`, `<dir>\<id>\geno.json`), `fx/<package>/*.gfx.json` and `fx/fx_bindings.json` (`gw_fx.c:514`, `:1227`), kit UI art in `ui/` with `*_ui.json` (RUNS case 3: "kit: ...geno-lab\ui - 83 texture entries"), `models/` read by Lua (`script model`), `scripts-data/<mod>_<script>/` for `gd.data_read/write` (`gw_script.c:6552`, outside the mod folder).

### 1.2 When the m-ex runtime turns on
- Not a setting, not the disc: **the presence of a resolvable `MxDt.dat`** (`gw_mexdt_load`, line 392; `gw_Mex_CssIconCount()` loads it lazily and returns 0 when absent, line 655-668, which "turns the whole m-ex layer off"). Vanilla alone: `mexdata: MxDt.dat not on this disc` (RUNS case 1).
- The separate `MELEE_MEX` / `mods\mex.txt` flags (`gw_mexid.c:449`) are the *patch* flags (`Mex_Enabled("...")`, 49 of them, `docs/MEX_PORT_STATUS.md`), not the data layer.

### 1.3 What the runtime reads, and what a NEW fighter row needs at minimum
Table list is `INSTALL.json` -> `slot_files.mxdt_clone.tables` (the exact tables the installer must write for one new row) plus
`docs/mods-packaging.md` section 2.3 and `ftdata.c:1590-1840` (`ftData_MexInitKinds`):

| need | where it lives today | consumer | who authors it for a port |
|---|---|---|---|
| fighter data file + symbol (`pl_file`) | MxDt `fighter` array, internal id | `gw_Mex_FtPlFile` -> `ftData_803C1F40[fk]` | mod author (but built from the host's bytes, see 1.4) |
| costume count/files (`costume_info`, `costume_file`) | MxDt, external + internal | `ftData_MexCostumeStrings`, cap 16 (`ftdata.c:1745`) | mod author |
| animation file + row count (`anim_file`, `anim_num`) | MxDt | `ftData_803C23E4`, `Table_Unk0.count` | mod author |
| demo strings (`ftdemo`) | MxDt | `ftData_803C2468` | mod author / host's |
| effect bank index (`effect_index`) | MxDt (255 = none -> clone base's bank, `ftdata.c:1771-1788`) | `ftData_UnkBytePerCharacter` | host's bank is fine |
| result screen file/scale, victory theme, announcer call, sound banks (`result_file`, `result_scale`, `victory_theme`, `announcer_call`, `ssm_files`), fighter music | MxDt, **external** id | results screen (melee `ce40af751`), `lbAudioAx` | mostly the host's values; announcer/name call needs audio |
| insignia (series emblem), name string | MxDt `insignia`, names table | CSS, results | mod author |
| item lookup (`item_lookup`) | MxDt | `MEX_IndexFighterItem` | empty for Sora |
| the fighter function table: 46 `fighter_function[]` entries (onLoad, special moves, ...) + 9 `kirby_function[]` + Kirby capfiles/costumes/effects | MxDt `fighter_function` | `ftData_On*`/`Special*` tables | **already optional**: `ftData_MexInitKinds` falls back to the clone base's entry whenever the row gives NULL (`ftdata.c:1623-1757`); `gw_Mex_FtBaseKind` infers the base from the row (`gw_mex_ftfunction_runtime.c:1395-1410`) |
| per-kind tables inside `PlCo.dat`: parts table (`pData[4]`) and `Fighter_804D6540` (`pData[5]`) | patched ACE `PlCo.dat` | `ftCommonData_ExtendKindTable` (`fighter.c:201-232`) rebuilds them in the port's kind order | mod author (the parts plan; Sora: 175 parts) |
| CSS: an icon in `MnSlChr.usd`'s icon table (joint, 0x1C row), the CSPs (portraits), the fighter's name text | patched ACE `MnSlChr.usd` | `gw_Mex_CssIconTable`, `mnCharSel_MexSetup`, kit CSS `gmfrontend_select.inc:82` | art: author; the *archive* is ACE's |
| stock icons (16 frames) and HUD name | patched `IfAll.usd` | in-match HUD | art: author; archive ACE's |
| a slot: dense port kind `0x21+i`, ck `0x22+i` | `gw_mex_slots_build` (`:1066`), 94 max (`gw.h:247`) | everything | engine |

Also consumed by the engine but not authored per fighter: the CPU AI tables (a new kind takes its host's rows, `fighter.c` `ftCommonData_ExtendCpuTables`, `gm_MexVanillaKind`).

### 1.4 What in a cloned slot is disc-derived, and what the author owns
- **Disc-derived whole files** (the four): `MxDt.dat` (everyone's rows, stages, banks), `MnSlChr.usd` (the entire CSS archive),
  `PlCo.dat` (the common fighter data), `IfAll.usd` (the entire HUD archive). These are what makes the mod undistributable and disc-specific.
- **Disc-derived bytes inside the author's own files** (VERIFIED, `install_ultimate.py:2-36, 955-975`): `PlUs.dat` is the host's (ACE `PlMs.dat`) fighter data and scripts with the
  author's parts/hurtboxes/rows rewritten; `PlUsAJ.dat` keeps ranges of the host's `PlMsAJ.dat` for rows whose clips are for other skeletons (`host_clips_kept_for_other_skeletons`).
  The host files are identical on vanilla, ACE and Akaneia (`docs/mods-packaging.md` section 2.2: "No vanilla `Pl*` fighter file ... is modified by either pack") so the same patch applies on all three (INFERRED for the new patch; the identity claim is VERIFIED by that doc's tests).
- **Author-owned:** the converted model/costumes (`PlUs<cc>.dat`, from Ultimate), animation clips, Geno profile/states/articles (`geno.json`, `geno/`, `GnTrail*.dat` article models), FX packages (`fx/`), the CSS icon/CSP/stock art converted from Ultimate, the parts table, the row's string/number values (file names, counts, emblem), the Ultimate attribute calibrations.
  (Ultimate/Brawl-derived assets are of course also third-party material built locally from the user's own copies; same rule as `ports/halberd/README.md`: built locally, never committed. That is a separate rule from "no disc data".)

### 1.5 What Geno adds, and does it need m-ex?
- Geno (`melee/docs/geno.md` section 2-3, `geno_registry.c`) is **opt-in per mod, via `geno.json`**; it layers over retail or m-ex fighters. **It does not depend on m-ex** for overlays: VERIFIED on vanilla, RUNS case 5 (`attach: "marth"`, attributes overridden, on_init hook fired, no MxDt).
- What it does not do yet: **`define` (a brand-new fighter) is reserved and skipped** (`geno_registry.c:18, 1084-1085`; roadmap "v3" in `docs/geno.md` section 13: "their own kind range and content ids, independent of m-ex's dense slots, CSS/SSS entries via gw_uigen"). The whole of Sora's "own fighter" part (row, model, CSS) is m-ex rows today; Geno only adds the moveset.
- Geno `attach` to an m-ex fighter by Pl file (`"attach": "PlUs.dat"`, Sora) resolves through `gw_Mex_SlotInternal`/`gw_Mex_FtPlFile` (`geno_registry.c:359-362`), so it also depends on the slot existing.

### 1.6 What vanilla lacks
No `MxDt.dat`; PlCo.dat with 33-entry per-kind tables (the engine already rebuilds them in port order, `fighter.c:201-232`, with retail row 0x21 preserved); an MnSlChr/IfAll with no added icons/frames; the m-ex stage, audio and effect tables (the m-ex layer's *other* consumers: `grfunction`, `lbAudioAx`, `mexeffect`; these all switch on when MxDt appears, see log lines in RUNS case 2: 155 stages, 103 sound banks, 56 effect banks).
This last point is the main design constraint: **an engine that fakes a whole MxDt on vanilla flips the stage, audio and effect systems into m-ex mode too**; so on vanilla the new fighter path must not do that (section 3.1).

---

## 2. Every other mod and example: does it satisfy "vanilla + one folder"?

| mod | works on vanilla? | one folder? | what it needs beyond its folder |
|---|---|---|---|
| `geno-lab` (`melee/pc/geno/mods/geno-lab`) | YES (VERIFIED RUNS 3) | YES | nothing. The LAB mode is engine code; the mod is Lua + `ui/` + `art/`. No `files/`, so 90 UI paths mount as disc paths (cosmetic) |
| `map_editor` | YES (VERIFIED RUNS 4; vanilla item files supply enemies) | **NO** | kit models (`models/`, 23 MB, a Blender build product, "Generated model binaries are not included in this checkout", `README.md`) must be copied in from `_build/agents/...`; the mission samples must be copied to `scripts-data/map_editor_main/`; layouts it saves go to `scripts-data` too |
| `bf_interior_room`, `bf_platform`, `runtime_models`, `fd_stage_content`, `boss_bonus`, `enemy_spawn_demo`, `tm_lite`, `camera_cinematic`, `scene_setup`, `kit_hud`, `gamemode_demo`, `boss_gamemode_bonus` | INFERRED yes (script mods; none greps for an m-ex fighter, `requires` is empty in every mod.json; not run) | yes where `models/` is checked in; `bf_*`/`runtime_models` models are build outputs (`export_kit.py`, `make_models.py`) | the generated models |
| `character_parts_lab`, `effects_lab`, `roguelite`, `roguelite_certification` (examples dir) | n/a | **no mod.json**: raw scripts loaded by the console/`MELEE_SCRIPT`, not packages | `roguelite` is packaged by `tools/roguelite/prepare.py` into `<app>/mods/roguelite` (one folder: bundle + `models/` room kit from `menu/out_roguelite` + `ui/` + effects + fx), plus an optional `scripts-data/roguelite_main/config.txt` outside the folder; no m-ex dependency found (`grep -i "m-ex\|mex\|ace\|akaneia"` empty). Satisfies the requirement once prepared (INFERRED, not run) |
| `ultimate-trail-slot` (Sora) | works (VERIFIED RUNS 2) but only by carrying ACE tables | one folder, **but** contains disc-derived files (illegal to distribute) and an ACE row replacement | the ACE disc at *install* time (the installer reads `GW_ISO_ACE`, `install_ultimate.py:71`) |
| `metaknight-slot` (Halberd) | INFERRED same as Sora (same installer lineage, `requires: []`, carries the tables) | same | same; row 52/51; conflicts with Sora; also needs its own effect bank and 76-sound bank (built from Brawl, local) |
| Brawl Kirby (`brawl-kirby-slot`) | DEPRECATED (memory: no more work) | n/a | n/a |
| `ports/kirby-ultimate` overlay pack | the **attach-to-Melee-Kirby** overlay works on vanilla by construction (Geno attach, no new row; INFERRED from RUNS 5) | yes | the *native slot* variant is a separate staged m-ex slot, not the default overlay |
| ACE / Akaneia packs (`split_modpack.py`) | YES on vanilla (`docs/mods-packaging.md` section 7: 108/108 on vanilla with split ACE mods; not re-run today) | `ace-base` + one per fighter: NOT one folder; every fighter `requires ace-base` | disc-derived by definition (built on the user's machine from their ACE ISO, never shipped) |

Mod-browser / launcher side (VERIFIED by reading): `tools/mods_browser/gdmelee-mods.schema.json` and `docs/mods-browser.md` describe an index of zips unpacked into `mods/<id>/` with `id kind pack requires conflicts url sha256 size`; the Qt launcher lists local mods and toggles `enabled.txt`, with **no install path** (`docs/mods-browser.md` top). The launcher classifies a disc as vanilla / ACE ("ACE (m-ex mod)" by file names, `launcher_core.cpp:81-83`) / modified and applies **no gating of mods by disc**; it enforces `requires`/`conflicts` when writing `enabled.txt` (`launcher_core.cpp:200-244`). The `pack` field exists but nothing in the engine enforces it.

---

## 3. "How did we do it previously?"

Findings (git + docs; VERIFIED by reading, not re-run):

1. **2026-09-15..19, Sonic from Akaneia on a vanilla disc.** The first m-ex fighter on a vanilla ISO was Sonic, with **Akaneia's `MxDt.dat` shipped inside the Sonic mod** (`_research/mex-stages.md:180`: "Akaneia's MxDt.dat ships inside the Sonic mod - so a vanilla run can see the full 96-row table and none of the 25 stage files"). Even earlier (`_research/sonic-clone-boot.md`) the new kind was a *remap onto Fox's data* with a vanilla-disc fallback (`ftData_SonicFallback()` restored Fox's entries when `PlSn.dat` was absent). Same family: a disc-derived table travelling in the mod.
2. **2026-09-20 `cd09bf8` / 2026-09-22 `273927b` (`make_mod_from_disc.py`, `split_modpack.py`), the "filtered base" design** (`docs/mods-packaging.md` section 3 approach C, "chosen"): the user's own mod disc is diffed against their vanilla ISO on their machine to build a pack; `split_modpack.py` splits it into one `ace-base` (MxDt + menus + shared data, 413 files, 653 MB) plus one mod per fighter/stage. Tested: vanilla ISO + `ace-base`, `ace-wolf`, `ace-sonic`, a stage: 108/108 headless, Wolf and Sonic on CSS, a match (`docs/mods-packaging.md` section 7). **This is the previous "vanilla + modded character" path, and it did work** (not re-run today). Its limitation is in its own text: entity mods only combine within one pack and need the base.
3. **2026-09-22 onward, Halberd (Meta Knight) and Brawl Kirby slot mods** (`ports/halberd/mods-slot/metaknight-slot`), and 2026-10 `install_ultimate.py` (Ultimate Kirby, Sora): a **self-contained slot mod**: the fighter's own `files/` plus patched copies of the four ACE table files ("Carries brawl-kirby-slot's shared tables too, so both mods can be on together"). That is today's mechanism and what RUNS case 2 exercises. State: works (case 2), single row 52/51, mutually exclusive.
4. **Geno overlays (`attach`)**: the only mechanism that never needed m-ex or any disc table; works on vanilla (RUNS 5); but it can only change behaviour of an existing fighter (no new model, no CSS entry). `ports/kirby-ultimate`'s default pack is of this kind.
5. **Geno `define`** (the intended long-term answer: "independent of m-ex's dense slots") was designed (`docs/geno.md` section 13, v3) and never built (`geno_registry.c:1084`).

So: a modded character on the vanilla disc worked **only ever by shipping a disc-derived MxDt in the mod**, in every era. That is the thing to remove.
Why the owner may have seen failure: see 0.3. Also consider that `tools/port/run.sh` defaults `MELEE_MODS_DIR` to `_build/mods`, whose contents vary per lane (`run.sh:105-106` comment: legacy mods "moved to `_build/mods-legacy`"), so a launch from the shipped launcher with a `mods\` folder lacking the table files would give "needs ace-base" or an absent fighter (INFERRED).

---

## 4. Design

### 4.1 Principles
1. A mod folder contains **only what the mod author owns** (plus references to host data by name). No disc-derived bytes, so it is legal to ship and identical for every user.
2. Anything the old design got by cloning disc tables is **derived at load, in memory, from the user's own disc** (the host fighter's rows/files) plus the mod's manifest.
3. The m-ex layer stays exactly as is for discs that are m-ex builds. On vanilla it must not be switched on as a side effect (it also switches on stage/audio/effect tables, section 1.6).
4. Added fighters never *replace* an existing row; they are appended. Two fighter mods never fight over a row.
5. Retail fighters on vanilla keep taking the retail path; added fighters take a new "native row" path that is **parallel** to the MxDt path, feeding the same per-kind tables.

### 4.2 The engine: a native fighter registry feeding the same per-kind tables
Introduce `FighterRow` (a plain struct per added fighter) and make the existing `gw_Mex_Ft*` accessors that `ftData_MexInitKinds` calls
(`SlotInternal, FtPlFile, FtPlSymbol, FtAnimFile, FtAnimCount, FtCostumeCount, FtCostumeString, FtDemoStrings, FtFunc, FtBaseKind, FtEffectIndex`,
`ftdata.c:1592-1604`, plus Kirby copy, result/victory/announcer/sound/emblem/name accessors) answer from **either** the loaded `mexData` (existing code, unchanged) **or** a native row.
Slots: m-ex rows get slots first (existing dense build, `gw_mex_slots_build`), native rows are appended after them; total stays under `GW_MEX_SLOT_COUNT` 94 (`gw.h:247`): up to 94 added fighters on vanilla, up to 94 minus the disc's present m-ex fighters on ACE (ACE: 31, so 63).

Row synthesis ("clone the host in memory"): the manifest names a `host` (a retail fighter, or any resolvable fighter by name). Per field:
- **function table** (46 + 9 slots): NULL, base kind = the host's retail kind. `ftData_MexInitKinds` already falls back to `[base]` for every NULL (`ftdata.c:1623+`); this reproduces exactly what Sora's cloned row encodes today (its `fighter_function[]` values are the host's own addresses, `INSTALL.json`). No table to ship. (INFERRED equivalence; the fallback code is VERIFIED.)
- **Pl file / costume / anim / demo**: file names from the manifest, found in the mod folder, mounted through the overlay (as today) or a synthetic file (4.3).
- **result file, result scale, victory theme, announcer, sound banks, effect bank, item lookup, Kirby copy**: manifest value else the host's row (NULL effect index keeps the host's bank: existing code, `ftdata.c:1771-1788`; Kirby hat absent keeps the base's, existing `gw_Mex_KirbyCapFile` returns NULL).
- **PlCo per-kind rows** (parts table, `Fighter_804D6540`): from a `parts` file in the mod (author-owned data produced from the Ultimate skeleton plan; today it is patched into PlCo.dat) else the host's row; plugged in `ftCommonData_ExtendKindTable` where `out[i] = loaded[k]` is chosen (`fighter.c:201-232`): one extra branch for native kinds. CPU AI rows already follow the host (`gm_MexVanillaKind`).
- **name / emblem / CSS icon**: manifest. Name audio ("announcer call"): fallback order mod's own `.hps`/ssm cue, the host's, none (silent).
- On an m-ex disc the same rows are appended in the same way: **the mod never carries or edits MxDt**, so ACE/Akaneia keep every one of their fighters (no "Wolf SSBU" displacement), and the same folder works on all three discs (the Geno profile id is already identical on vanilla vs ACE, RUNS 2 vs 6: `4b11c546...`).

On vanilla (no MxDt), `gw_Mex_*` returns 0/NULL for everything about the *disc* (CSS icon count 0 etc.), unchanged; added fighters become reachable through a separate, small path: `gw_UI_FighterAt` / the kit CSS enumerate "retail icons + native rows" (they currently enumerate `gw_Mex_CssIconCount`, `gw_uigen.c:403-428`; `gmfrontend_select.inc:82` reads MnSlChr's icon table and would be taught to append native entries drawn from textures in the mod's `ui/`). The legacy native CSS (`MELEE_NATIVE_CSS=1`) is not extended on vanilla (it is the deprecated comparison path, `gw_uigen.c:372`); it lists native fighters only when it is on an m-ex disc via the existing path or not at all. Stage, audio and effect systems stay in retail mode on vanilla (no MxDt faked), which is the safe parallel path.

### 4.3 Host-relative patches instead of derived bytes (the Pl and AJ files)
`PlUs.dat` and `PlUsAJ.dat` embed host bytes today. Replace them in the package with **`PlUs.dat.gdpatch` and `PlUsAJ.dat.gdpatch`**: a tiny op list (`copy host[off,len]`, `insert bytes`, plus `host: "PlMs.dat"`, `host_sha256`, `result_sha256`), written by the installer (it already knows `kept` ranges and writes with an offset writer, `install_ultimate.py:962-975`, `w.put`). The engine applies it at first open of the file (synthetic in-memory file served through the overlay: `shim_dvd.c` gains "a mod path whose content is produced on demand", the existing `0x80000000|index` scheme reading from memory instead of `fopen`), verifying `host_sha256` against the host file read from the *user's* disc/mods (PlMs.dat is identical on all three discs; if a disc's host differs, e.g. a modded base, log and skip the fighter rather than load garbage).
The patch contains no host bytes (only `copy` ranges and author bytes); the `host` file is the user's. The 5 MB AJ becomes mostly `insert` of author clips plus a few `copy` ranges. Cost per boot: ms (256 KB + 5 MB; apply once at first read).
A cleaner end state (not needed now): fighters whose Pl data is authored from the IR with no host bytes at all; Geno states and `attributes` already override most of the host's behaviour; large.

### 4.4 Menus and HUD art without cloning MnSlChr / IfAll
- CSS icon, CSPs (8 costumes), name: textures in `ui/` (the kit already loads a mod's `ui/*_ui.json` and gxtex: RUNS 3 shows 83 texture entries from the LAB mod). The kit CSS draws them for native rows.
- Stock icons and the in-match HUD name plate (IfAll) and the results-screen emblem/name: the engine draws the mod's textures for native kinds at the HUD hooks, falling back to the host's icon (tier T0, no art needed, immediate). Doing the in-memory patching of `MnSlChr.usd`/`IfAll.usd` (what the Python installer does with HSD surgery) in C is not recommended (large, brittle); texture hooks are smaller.
- Tiers: **T0** host's icon/CSP/stock (works on day one, zero art); **T1** mod's textures in kit CSS and HUD; **T2** legacy native CSS support only on m-ex discs.

### 4.5 Conflicts, counts, costumes, saves
- Two fighter mods: independent rows, both can be on (conflict only on equal `id`, or an optional author-declared `conflicts`). No more `conflicts: ["metaknight-slot"]`.
- Costume slots: up to 16 per fighter (existing cap, `ftdata.c:1745`), manifest `costumes[]` in order; costume 0 is the default.
- Number of added fighters: hard limit 94 minus m-ex rows present; log which fighter was left out (existing message style, `gw_mex_ftfunction_runtime.c:1085-1095`).
- CharacterKinds shift with the enabled set (dense slots; already true, `docs/mods-packaging.md` section 8). Native rows are ordered by mod id, appended after the disc's m-ex fighters, so a given enabled set gives a stable numbering; anything that persists a CharacterKind must persist the identity token (`id:<hex>`), which `gw_mexid.c` already provides.
- Memory-card/save rows: unlock bits for added fighters do not exist in a vanilla save (same limit as added stages: "shown locked ('?')", `docs/mods-packaging.md` section 8). Treat a present native fighter as unlocked (a one-line decision in the unlock check); never write native fighters into the save's unlock table. The LAB and scene launch skip the memcard (`skip_memcard=1`, RUNS logs) so this is menu-only.

### 4.6 Netplay and rollback determinism
- `gw_mexid.c` identity of a fighter = hash of `Pl*.dat` + `Pl*AJ.dat` (read through the file layer) + the Geno profile id salt (`gw_mexid.c`, `geno_registry.c:1626`). With patch files the file layer returns the synthesized bytes, so the identity of Sora is the same as today's iff the bytes are the same (they will be, as the patch reproduces the existing file; verify with a hash equality test). **Add the native row's manifest values (costume count, anim count, base kind, parts hash) to the identity**: today's documented gap ("fighter identity does not cover MxDt's per-fighter function-table row, item descriptors, or PlCo per-kind rows", `docs/mods-packaging.md` section 8) is closed for native rows by construction because every input is in the hashed manifest.
- Global data: the `mods_hash` global check hashes `PlCo.dat` (21 tables) and `ItCo.dat` (`docs/mods-packaging.md` section 6). Today Sora's carried ACE `PlCo.dat` is the hashed one on vanilla (retail tables are identical so it agrees; VERIFIED only by that doc). With no carried PlCo the disc's own file is hashed: vanilla vs vanilla agrees trivially; ACE vs vanilla already agreed. No new rollback state: native rows are boot-time constants; the per-kind tables are rebuilt every PlCo load by the same code path (`fighter.c:201`, rebuilt "on every load" because PlCo reloads per scene) so a snapshot restore (`gw_Mex_InvalidateAfterMem1Restore`) must also re-run the native branch (test it).
- Fingerprint: stop mounting `ui/`, `art/`, `models/`, `geno.json` etc. of no-`files/` mods as disc paths (`shim_dvd.c:214-217`: skip everything except `files/` for packages with a v2 manifest), so the mod fingerprint covers what the engine reads by name via the manifest's hash instead of 90 spurious paths.

### 4.7 The single-folder package format ("gdmod v2"), and the optional archive
```
mods/ultimate-trail/                 (the folder name is the id; or ultimate-trail.gdmod, a zip of this folder)
  mod.json                           id name version author kind=fighter  requires=[]  conflicts=[]  engine={...}
                                     schema=2  fighters=["fighter.json"]  (loader reads: schema, content hash)
  fighter.json                       one or more fighter rows: host, name, emblem, costumes[], anim/pl/patch refs,
                                     counts, css{icon,csps[],stock[]}, audio{announcer,victory,ssm}, parts, effect bank,
                                     "geno": "geno.json" (or inline geno profile with define:...)
  fighter/  PlUs.dat.gdpatch PlUsAJ.dat.gdpatch  PlUsNr.dat ... PlUsBk.dat  parts.bin
  geno.json geno/                    the Geno profile, states, articles (as today)
  fx/                                FX packages and fx_bindings.json (as today)
  ui/                                css icon, csp, stock textures + *_ui.json
  audio/                             optional name call / sound bank
  scripts/                           Lua (as today)
  models/ samples/ data/             script mods' kit models, sample layouts, default script data
```
- `files/` (raw disc-path overlay) remains for *replacement* mods that genuinely override a disc file (stage swaps, texture packs); packages with `schema: 2` and fighters/stages declared use the manifest instead and **mount nothing** by directory walking.
- **Script data and samples live inside the folder:** `gd.data_read(name)` falls back to `<mod>/data/<name>` when the writable store (`scripts-data/<id>_<script>/`) lacks it (writes still go to the store, `gw_script.c:6552`). Map editor: `samples/first_mission.lua` loads via `map play samples/first_mission.lua` (`load_map` reads `gd.data_read`; small Lua change). Models: `models/` inside the folder is already how the kit mods work (`bf_interior_room`, `map_editor`); the fix is packaging (a `pack_mod.py` that fails if a referenced model is missing and copies the build output in), not engine.
- **Archive form:** `mods/<id>.gdmod` = a zip (stored or deflate) of the same layout with `mod.json` at the root. The loader **unpacks it once into a cache** (`mods/.cache/<id>-<sha256 prefix>/`) when the archive is newer or its hash changed, then mounts the cache exactly as a folder. Rationale (also `docs/mods-packaging.md` "Loose files, not zips"): random-access reads of loose files, trivial overlay; the archive is the *distribution* form and the mods browser already downloads and verifies a zip (`sha256`, `size`). A direct in-process zip reader (stored-only) is possible later but gains nothing and adds a reader to the file layer.
- Launcher: lists folders and `.gdmod` files; nothing gates by disc anymore (drop the `pack` field's role); shows "needs host fighter X" if the host is absent.

### 4.8 Migration of existing mods
- **Sora:** installer (`install_ultimate.py`) gets `--package v2`: instead of `mk_slot_files`-style table cloning it writes `fighter.json`, the two `.gdpatch` files, `parts.bin`, `ui/` textures (it already converts them: CSS icon, CSP frames, stock frames to CI8/CI4 + RGB5A3 for the HSD archives; emit gxtex or PNG for the kit instead), keeps `geno.json`/`geno/`/`fx/`, and no longer reads `GW_ISO_ACE` for tables (still reads the host `PlMs.dat`/`PlMsAJ.dat` from any disc, to compute the patch; so installer input becomes "vanilla ISO or ACE ISO"). Geno `attach: "PlUs.dat"` stays valid (the Pl file resolves through the native row).
- **LAB:** add `schema: 2`, move nothing; stop mounting `ui/` and `art/` as disc paths. Works today (RUNS 3).
- **Map editor:** `pack_mod.py` bundles `models/` (from the Blender export) and `samples/` into the folder; `data/` fallback. Works today once the models are copied (RUNS 4).
- **Envoy (roguelite):** already one folder; move `scripts-data/roguelite_main/config.txt` default to `data/config.txt`; keep `prepare.py` as the packer.
- **Meta Knight (Halberd):** same as Sora plus an effect bank and a sound bank. Needs the two native-row extras: (a) **effect bank append** to the effect table the retail path uses, (b) **sound bank append** (new `ssm`) with the announcer cue. These are the only parts of MK not covered by the Sora path; size M.
- **ACE/Akaneia packs:** unchanged and still valid on vanilla (a pack is the user's own derived data, never shipped). They simply stop being a dependency of any mod.

---

## 5. Work breakdown (S under a day, M a few days, L about a week or more)

Order matters: engine first, then installer, then migration, then UI art, then launcher/docs.

| # | work | area | size | depends |
|---|---|---|---|---|
| 1 | `FighterRow` struct + loader reading `fighter.json` from mounted mods; `gw_Mex_Ft*` accessors answer native rows; slot allocation after m-ex slots; clone-by-host defaults (NULL function table, base kind, host effect/victory/result) | engine `melee/pc/platform/gw_mex_ftfunction_runtime.c`, `ftdata.c` | L | none |
| 2 | Native kind in `ftCommonData_ExtendKindTable` (parts table / 804D6540 from `parts.bin`, else host row); CPU rows follow host (exists) | engine `fighter.c` | S | 1 |
| 3 | Synthetic (generated-on-open) overlay files + `.gdpatch` applier + host hash check | engine `shim_dvd.c` | M | none |
| 4 | Kit CSS/SSS enumeration appends native rows; icon/CSP from mod `ui/`; "unlocked when present"; `gw_UI_FighterAt/Count` | engine + frontend (`gw_uigen.c`, `gmfrontend_select.inc`) | M | 1 |
| 5 | HUD stock icon + results screen name/emblem for native kinds (texture hooks, host fallback) | engine/game `if*`, `gm_1798`-area | M | 1, 4 |
| 6 | Name/announcer/victory audio: manifest cue, host fallback, silent last | engine audio (`lbAudioAx`) | S-M | 1 |
| 7 | Effect-bank append and sound-bank (ssm) append on vanilla/retail tables (for Meta Knight) | engine | M | 1 |
| 8 | Geno: implement `define` as the manifest carrier (geno v6) or make `fighter.json` primary and keep geno.json for moveset; `attach` by native Pl name | Geno `geno_registry.c` | S-M | 1 |
| 9 | Identity: add manifest/row hash to `gw_mexid.c`; test equality of Sora's identity old vs new | engine netplay | S | 1, 3 |
| 10 | `mod.json` schema 2: parse `schema`, `fighters`; stop walking non-`files/` folders; `gd.data_read` fallback to `<mod>/data/`; `.gdmod` unpack-to-cache | engine `gw_mods.c`, `shim_dvd.c`, `gw_script.c` | M | none |
| 11 | Installer `--package v2` for Ultimate fighters (patch writer, `fighter.json`, `parts.bin`, ui textures; drop table cloning and the `Wolf SSBU` replacement) | `ports/ir/tools/install_ultimate.py` (+ Halberd `build_mk_slot.py`) | L | 1, 3 |
| 12 | `pack_mod.py` / `prepare.py` for script mods (models + samples + data inside the folder; fail on missing) | tools | S | 10 |
| 13 | Launcher: list `.gdmod`, show missing host, drop disc gating of `pack`; `check_strings.py` if text changes | `tools/release/launcher`, `tools/mods_browser` schema | S | 10 |
| 14 | Docs: rewrite `docs/mods-packaging.md` sections 3/8 and `docs/scripting.md` manifest, `ports/README.md`; add the schema | docs | S | all |
| 15 | Migrate Sora, LAB, map editor, Envoy; then Meta Knight (needs 7) | per mod | M each; MK L | 11, 12, 7 |

Critical path: 1 -> 3 -> 11 -> 15 (Sora). Roughly 3 to 4 weeks for one engineer; Sora + LAB + map editor + Envoy one-folder on vanilla in about two weeks if UI tier T0 is accepted first (host's icon/CSP/stock) and T1 art follows.

### Verification on the vanilla disc (per step)
All run with `GW_ISO_VANILLA`, a new sandbox name, LAB mode, `cpu0` opponents, a probe script (as in RUNS) - no screenshots, except "how it looks" checks that GD does:
1. Step 1/2: `p1=ultimatesora` logs `kind=33`, `ck=34`, no `mexdata: MxDt.dat loaded` line (the m-ex layer stays OFF on vanilla), `mexdata: MxDt.dat not on this disc` still present, and **no ACE file in the mod folder** (grep `files/` for `MxDt.dat|PlCo.dat|MnSlChr|IfAll`: empty). Assert: Geno profile id equals `4b11c54684209d43`.
2. Step 3: the synthesized `PlUs.dat`/`PlUsAJ.dat` SHA-256 equals today's shipped files'; a deliberately wrong host (tamper copy of a disc is not possible; use a unit test with a fabricated host) logs "host differs - skipped".
3. Same folder, three discs: vanilla -> FighterKind 33 (ck 34), Akaneia (7 m-ex fighters) -> 40 (ck 41), ACE (31 m-ex slots, `Wolf SSBU` kept) -> 64 (ck 65); appended, no row replaced; check the roster still lists ACE's `Wolf SSBU`.
4. Two fighter mods together (Sora + a second fixture) both present, distinct CharacterKinds.
5. CSS: `at=css` roster lists the native fighters (roster log line as RUNS 2b); selection through a pad script, then a match; GD checks the icon/portrait.
6. Netplay: `_build/netplay_local.ps1` host with the mod vs guest vanilla-without-mod ("content you don't have", existing path) and host+guest both with it: identity equal, 0 desyncs; snapshot restore re-applies the native per-kind rows.
7. Native test suite on vanilla (`tools/port/run.sh --test`): new tests for row synthesis (host fallback, slot count, limit message), patch applier, `schema 2` mounting.
8. Packaging: a script that fails the build if a package folder contains `MxDt.dat`, `PlCo.dat`, `MnSlChr.*`, `IfAll.*` or any file whose bytes match the disc (the release guard `tools/release/test_release_guard.py` pattern).

---

## 6. Risks
- **Memory/speed:** synthetic files add RAM only for the patched Pl (256 KB) and AJ (5 MB) once; Sora is already 18.7 ms/frame against the 120 fps target (memory note); not made worse by this, not improved.
- **Netplay desyncs from rows not in the identity:** closed by hashing the manifest (4.6). Identity of existing Sora must stay equal across the migration (test 2 above) or old/new builds cannot play each other.
- **Per-kind C arrays and disc tables:** `docs/HANDOFF.md` section 6 "Counts belong to the data": "A new fighter kind also reaches per-kind tables loaded from disc; widening a C array alone is insufficient" (and `_research/sonic-clone-boot.md` finding 2/3). The registry must enumerate every kind-indexed structure; `ftCommonData_ExtendKindTable`/`ExtendCpuTables` are two known; the stage/stock/result code may hold others. Budget a sweep (tests `mex_ftdata_rows`-style over native kinds).
- **m-ex attribution rule** (`tools/mex_port/README.md` lines 22-30): consult m-ex, do not copy `.asm/.s/.h/.dat`. This design does not copy m-ex structures into the repo: the native row is the port's own struct; the manifest is our schema; the MxDt layout is still only *read* from the user's disc. Each new accessor that mirrors an m-ex table keeps an attribution comment ("m-ex Fighter data tables, consulted") as the existing code does (`ftdata.c:1770` style). Do not paste m-ex's `mxdt.h` field list.
- **Behaviour regression for ACE/Akaneia users**: native rows appended after m-ex rows change the CharacterKinds of nothing existing (they come last), but Sora's own ck changes (58 -> 65 on ACE) and anything stored by number breaks; identity tokens already handle online, scripts must use names (`p1=ultimatesora`, as today).
- **Legacy native CSS on vanilla won't list native fighters** (4.2): acceptable only if the kit CSS is the default everywhere (it is, `MELEE_NATIVE_CSS` is the opt-out, `gw_uigen.c:372`); confirm with the owner (D3).
- **Host dependency:** a Geno fighter's moveset assumes its host (`marth`/`kirby`); if the host's file differs (a modded disc), the fighter is skipped with a log line rather than loading garbage.
- **Unknowns not tested today:** audio/name call of Sora on vanilla (row points at ACE audio indices, case 2); selecting Sora with a real pad on vanilla's CSS; Akaneia + Sora (INFERRED to fail); Meta Knight on vanilla (INFERRED to work like Sora).

---

## 7. Alternatives considered
1. **Keep slot mods, but generate the table files at install time per disc on the user's machine** (the installer reads the user's vanilla/ACE/Akaneia and writes a mod folder for that disc): legally fine (nothing shipped), and it is what `make_mod_from_disc.py` already does for packs. Worse: the mod is no longer one *portable* archive (every user must run a Python installer with the toolchain and their disc; release users have no Python/Blender), it is per-disc, and the row replacement/mutual exclusion stays. **Acceptable as a stopgap** if the owner needs vanilla-with-Sora in a release before the native path lands: ship the installer, not the mod.
2. **A tiny "m-ex base" mod everything requires** (an `mex-base` carrying one generated table set): violates "ONE folder" and, if disc-derived, "ships no disc data"; if hand-authored (a minimal MxDt we write ourselves), it is the same engine work as 4.2 hidden inside a file format, and it flips stage/audio/effects into m-ex mode on vanilla (section 1.6). Rejected, except as the internal shape of 4.2's m-ex-disc path (which exists already).
3. **Build a full `MxDt.dat` at boot from fragments (`docs/mods-packaging.md` approach A/B)**: compiles every table, renumbers item/effect/sound ids, generates CSS/SSS art; "weeks, and needs source fragments ACE does not publish" (same doc, section 3). Over-scoped for fighters; it is the right long-term answer for *stages* and custom items (later).
4. **Geno `define` only** (no m-ex layer at all, new kind range): the cleanest end state (`docs/geno.md` roadmap v3), but the per-kind plumbing (`ftdata.c`, `PlCo` rows, CSS, results, audio) is the same work as 4.2; do 4.2 first and expose it through `define`. They converge; no separate project.
5. **Zip mounted directly by the file layer**: rejected for now (random-access reads of 5 MB animation files, no benefit over unpack-to-cache; the earlier decision in `docs/mods-packaging.md` section 4 stands).
6. **Do nothing; document that Sora works on vanilla**: true, but it fails the owner's own requirement (a disc-free one-folder mod) and leaves the shipping blocker.

---

## 8. Decisions that are genuinely the owner's

| # | decision | recommendation |
|---|---|---|
| D1 | Which mod, on which launch path, failed on vanilla (I could not reproduce) | Ask for the mod name and where it was launched (launcher or `run.sh`); also run it once more with the log; nothing else in this design waits on the answer |
| D2 | Stopgap: ship the installer so users generate disc-derived Sora tables on their own machine, in parallel with the native work? | Yes for ACE users only if a release needs Sora soon; otherwise skip and do the native path first (about two weeks to Sora) |
| D3 | Is it acceptable that on vanilla the **legacy native CSS does not list added fighters** (only the kit CSS does) | Yes; the kit CSS is the default and the native one is flagged "for comparison" in `gw_uigen.c:372` |
| D4 | UI art tiers: ship T0 (host's icon/CSP/stock, no art) first, T1 (Ultimate/Brawl art in the kit CSS/HUD) after | T0 first |
| D5 | Announcer/name call for added fighters: silent, host's, or require the mod's own cue | The mod's own cue if it ships one; otherwise silent (a host's call would announce the wrong name) |
| D6 | Should added fighters be selectable on a fresh save (unlock rule) | Yes, treat present = unlocked; never write them to the save |
| D7 | Native CharacterKind numbering when the enabled set changes (dense, appended after disc rows) | Keep; scripts/tests must name fighters, not number them (already the practice) |
| D8 | Where `pack` / disc gating goes: none; but should a mod be able to declare "needs host fighter X"? | Yes, manifest field `host` is enough; no `pack` gating |
