# Mods: how they are packaged, loaded, toggled, and played online

This describes what the code does as of D1 (lane delta, 2026-09-22). File references are to the
melee fork (`pc/platform/...`, `src/melee/...`) and to this repo (`tools/mex_port/...`).

## 1. The short version

- The port never runs a mod's PowerPC code (no DOL patches, no `codes.gct`). m-ex behaviour is
  reimplemented in C (`pc/platform/gw_mex_*`), and a mod's **content** is data: disc files plus
  m-ex's table archive `MxDt.dat`.
- Every file the game opens goes through one place, `shim_dvd.c`. It reads the ISO and **overlays
  loose files from a mods folder** on top of it. That is how "vanilla ISO + ACE" works, and it is
  the only mod mechanism there is.
- New in D1: each mod folder may carry a `mod.json`; `mods/enabled.txt` picks which mods mount at
  boot; a native API lists and toggles them for the next boot (for the in-game menu); a tool splits
  ACE and Akaneia into **one mod per added fighter and per added stage** plus a shared base; and
  netplay matches fighters and stages **by content identity**, so players with different mods can
  play whatever they have in common.

## 2. How content is loaded today, file by file

### 2.1 Where files come from

`shim_dvd.c` implements the SDK's DVD calls on top of a plain GameCube ISO (FST at 0x424/0x428).
At `DVDInit` it also mounts the mods:

1. `gw_mods.c` scans the mods folder: `MELEE_MODS_DIR`, else `mods\` next to `melee-pc.exe`.
   `tools/port/run.sh` points `MELEE_MODS_DIR` at `_build/mods` for every sandboxed run (including
   `--test`); `_build/netplay_local.ps1` points it at an empty `_build/nomods` unless
   `-EnvHost/-EnvGuest` override it.
2. It decides which mods mount and in what order (section 4). `MELEE_MODS=0` mounts nothing.
3. For each mounting mod, every file under its payload folder answers the disc path of its
   position: `mods/ace-wolf/files/PlWf.dat` is `/PlWf.dat`, `.../files/audio/us/wolf.ssm` is
   `/audio/us/wolf.ssm`. Names match case-insensitively.
   - A path the disc has is **overridden in place**: it keeps the disc's FST entry number, so any
     code that cached the number is unaffected.
   - A path the disc lacks is **added** with a fresh entry number past the end of the FST.
   - A later mod in mount order wins a path two mods provide (logged: `gw: mods: X overrides Y's /path`).
   - The overlay can add and replace but **cannot delete** a disc file.
4. `DVDFastOpen` of a mod file stores `0x80000000 | index` in the disc-offset field; reads of it go
   to the host file (`fopen/fseek/fread` per request) instead of the ISO. Synchronous helpers
   (`gw_DVDReadFileAlloc`, `gw_DVDReadPrefix`, new `gw_DVDFileExists`) see the overlay too.
5. Every mounted path is reported back to `gw_mods.c` (`gw_Mods_NoteFile`) and logged:
   `gw: mods:   /PlWf.dat <- ace-wolf (new file, ...)`. `MELEE_DVD_TRACE=1` logs every path the
   game resolves and whether the disc or a mod answered.

So "a mod disc" and "vanilla + that disc's pack" are the same thing to the engine: the bytes of a
given path are identical either way.

### 2.2 Packs: a mod disc turned into a mods folder

`tools/mex_port/make_mod_from_disc.py --vanilla <retail ISO> --mod <mod ISO> --name ace` diffs the
two FSTs and writes `_build/packs/<name>/` with exactly the files that are NEW on the mod disc or
whose CONTENT differs (same-size files are hashed on both sides), plus a manifest beside it
(`<name>.gdm_pack.json`: size + sha256 per file). ACE 2.0 is 990 new + 75 modified files (1.08 GB),
Akaneia 1.0.1 is 65 modified + the rest new (369 MB). The modified vanilla files are menus
(`MnSlChr.usd`, `MnSlMap.usd`, `IfAll.usd`, `GmRst.usd`, ...), `PlCo.dat`, `SmSt.dat`, trophy data,
nearly every `audio/us/*.ssm`, and (ACE only) six vanilla fighters' effect banks. No vanilla `Pl*`
fighter file and no vanilla `Gr*` stage file is modified by either pack. Packs are disc-derived and
never committed (`.gitignore` refuses `/_build/packs/`).

### 2.3 What `MxDt.dat` carries, and who reads it

`MxDt.dat` is an HSD archive with one public symbol, `mexData`: 14 root pointers
(`tools/mex_port/dump_mxdt.py`). `gw_mex_ftfunction_runtime.c` loads it once
(`gw_mexdt_load` -> `gw_mex_load_hsd`, read through `gw_DVDReadFileAlloc`, so a mod's copy wins)
into a persistent guest buffer and relocates it; everything else reads through bounds-checked
accessors. A disc without it (vanilla) simply has no m-ex content.

| root | contents | read by |
|---|---|---|
| +0x00 metadata | counts: internal/external fighter ids, CSS icons, internal/external stages, SSS icons, ssm, bgm, effects | everyone, for bounds |
| +0x04 menu | CSS icon table (menu+0x04, rows of 0x1C at +0xDC), SSS icon table (menu+0x08, rows of 0x20, external stage id at +0x1C) | `gw_Mex_CssIconTable` -> `mncharsel.c mnCharSel_MexSetup`; `gw_Mex_SssTable` -> `mnstagesel.c mnStageSel_MexSetup` |
| +0x08 fighter | ~33 parallel per-fighter arrays: names, Pl file + symbol, costume counts/files, anim file, effect index, result file, victory theme, announcer, sound bank, item lookup, demo files, ending files, target-test stage, ... Indexed by INTERNAL id except names/costume info/sound/results/victory/announcer/ending files (EXTERNAL id) | `gw_Mex_Ft*` -> `ftdata.c ftData_MexInitKinds` fills the port's per-kind tables |
| +0x0C fighter_function | per-slot tables of vanilla callback addresses per internal fighter (the clone base's behaviour) | `gw_Mex_FtFunc`, via the PPC bridge |
| +0x10 ssm | sound bank file names, sizes, lookup groups | `gw_Mex_Ssm*` (the ARAM size is re-read from the actual file's header, `gw_Mex_SsmSize`) |
| +0x14 music | BGM file names, menu playlist | `gw_Mex_Bgm*`, `gw_Mex_MenuPlaylist*` |
| +0x18 effect | effect bank files `{file, symbol, flags}` stride 12 | not wired yet (task D2) |
| +0x1C item | custom item descriptors and runtime index (ids >= 237) | `gw_Mex_ItemCustom*`, `MEX_IndexFighterItem` |
| +0x20/+0x24 kirby | Kirby copy files, costumes, effect ids, copy-ability functions | `gw_Mex_Kirby*` -> `ftKb_MexCopyKindData` |
| +0x28 stage (Arch_Map) | external -> internal stage ids (stride 12), stage names (+0x10, by internal id), item lookup, playlists | `gw_mex_grfunction.c` |
| +0x2C stage_desc | per internal stage: a 13-word StageData row (file name at word 2, clone-base callbacks) | `gw_Mex_GrFile`, `ground.c Ground_MexStageDatas` |
| +0x30/+0x34 scene, misc | scene table, misc | not used by the port |

The per-fighter/per-stage code itself (m-ex `ftFunction` / `grFunction` blobs) lives inside the
fighter's `Pl*.dat` and the stage's `Gr*.dat`; `gw_mex_ftfunction*.c` / `gw_mex_grfunction.c`
relocate it and run it in the PPC interpreter.

### 2.4 How content is registered

- **Fighters** - `gw_mex_slots_build` walks the fighter rows from internal id 27 up to (but not
  including) the six bosses m-ex keeps last, and gives a port slot to every row **whose Pl file
  resolves** (disc or mounted mod). Slot *s* is FighterKind `0x21+s` and CharacterKind `0x22+s`.
  The table is **dense**: a fighter whose file is absent leaves no hole, so CharacterKinds of m-ex
  fighters depend on which ones are present. (Full ACE: Wolf 34 ... Sonic 38; vanilla + Wolf and
  Sonic only: Wolf 34, Sonic 35.) `ftData_MexInitKinds` then fills the port's per-kind tables.
- **CSS** - `mnCharSel_MexSetup` copies m-ex's icon table and the `mexSelectChr` model from
  `MnSlChr.usd`; an icon whose external id maps to no port CharacterKind (`gw_Mex_ExtToPortCKind`
  = -1, i.e. its fighter has no slot) is marked unavailable and the grid is re-packed without it.
- **Stages** - internal ids >= 71 are m-ex additions. `gw_Mex_GrFile(k)` returns the row's file
  name, and (new in D1) **NULL when an added stage's file is not on the disc or in a mounted mod**;
  `gw_Mex_GrIsMex` and `Ground_MexStageDatas` only give such a stage a row when its file exists.
- **SSS** - `mnStageSel_MexSetup` copies m-ex's icon table and uses the `mexMapData` models from
  `MnSlMap.usd`; `mnStageSel_MexScanUnlocked` locks (shows "?") an added stage whose `GrFile` is
  NULL, and otherwise asks the save file whether the stage is unlocked.
- **Effects** - m-ex fighter effect banks (`Ef*Data.dat`, ids >= 5000 in `efSync/efAsync`) are
  not wired yet (D2). **Audio** - banks come from the ssm table; the file is read through the
  overlay, so a mod's bank wins. **Kirby hats** - `gw_Mex_KirbyCapFile` returns NULL when the copy
  file is absent, and Kirby keeps the clone base's hat instead of faulting later.

## 3. Why one baked MxDt.dat makes per-entity mods hard

m-ex's tables are **index-dependent**: an internal fighter id picks a row in ~33 arrays; external
ids pick CSS icons, names, sound banks and results; CSS and SSS icon models are baked into
`MnSlChr.usd` / `MnSlMap.usd` with one joint per icon; effect and sound bank numbers are global;
custom item kinds are numbered 237.. across all fighters and stages; per-kind tables in `PlCo.dat`
are extended for the roster; and a fighter's own guest code can hold numbers from all of these.
"One mod per fighter" therefore cannot be "one folder of files" unless something produces the
tables for the combination that is enabled. Three ways to get there:

| | approach | cost |
|---|---|---|
| A | **Build `MxDt.dat` at boot** from per-entity fragments (what m-ex's MexTool does offline from `akaneia-build/data/fighters/*.json` etc.) | Reimplementing MexTool's compiler: every table, id renumbering (item kinds, effect/sound banks), and **generating the CSS/SSS icon models and art** for the enabled set. Fighter guest code that embeds global ids would also need patching. Weeks, and needs source fragments ACE does not publish. |
| B | **Merge per-entity table fragments** into a base table | Same renumbering problem as A without the art problem solved; still needs a CSS/SSS that is not baked. |
| C | **Filtered base** (chosen): one base mod ships the pack's full `MxDt.dat` + menus + shared data; each entity mod carries only that entity's files; the runtime offers a row only when its entity's files are present | The table and menu art are the pack's, so entity mods only combine **within one pack** (ACE fighters with the ACE base, not with Akaneia's), and at most one base mounts. Everything else already worked: the dense fighter slots, the CSS repack and the stage-row presence checks were built for "row declared, file missing". |

C costs nothing at runtime and needed no new table code: the D1 changes were making
`gw_Mex_GrFile` presence-aware, the mount/enable logic, and the tool. Cross-pack mixing (ACE Wolf
next to Akaneia Sonic) is the real limitation; it becomes possible once the CSS/SSS stop depending
on baked models (alpha's A2 remake enumerates fighters/stages at runtime through
`gw_UI_FighterAt/StageAt`) and a table builder (A) exists. The runtime side is ready for that: it
already reads every table through accessors, never through a baked layout.

## 4. The mods folder (implemented)

```
mods/                         next to melee-pc.exe, or MELEE_MODS_DIR
  enabled.txt                 one mod id per line, '#' comments. ABSENT = every mod is enabled
  ace-base/
    mod.json
    files/MxDt.dat ...        the payload: paths inside files/ are disc paths
  ace-wolf/
    mod.json                  {"kind": "fighter", "requires": ["ace-base"], ...}
    files/PlWf.dat, files/PlWfAJ.dat, files/audio/us/wolf.ssm ...
  sonic/                      legacy layout (no files/, no mod.json): the folder is the payload
  targettest/                 not a mod (Target Test layouts) - skipped
```

`mod.json` is a flat object; every field is optional:

```json
{ "id": "ace-wolf", "name": "Wolf", "version": "2.0.0", "kind": "fighter", "pack": "ace",
  "description": "Wolf from ACE 2.0.0", "requires": ["ace-base"], "conflicts": [],
  "hash": "<content digest written by the packer>" }
```

- The **folder name is the id** (a different `"id"` is logged and ignored). `kind` is `base`,
  `fighter`, `stage` or `misc` (unknown -> misc). A `mod.json` at the top of a legacy-layout mod
  is never mounted as a disc file.
- **Resolution at boot** (`gw_mods.c set_resolve`): start from the enabled set; drop a mod whose
  `requires` are not all mounting (`needs X`); drop a mod that conflicts with one already kept -
  an explicit `conflicts` entry either way, or a **second base** (only one `MxDt.dat` can be the
  tables); repeat until stable. **Mount order**: requirements first, then base < misc <
  fighter/stage, then id. Every mod's outcome is logged at boot.
- **Enable/disable happens for the next boot only.** The overlay and the m-ex tables are built
  once; nothing is unmounted at runtime.

### Loose files, not zips

The mounted form is loose files, the "furthest base layer": the overlay serves random-access reads
of individual files (`DVDReadAsyncPrio` with offsets), a loose file is exactly what it replaces,
and a person can drop in or edit one file. A zip would need a reader in the file layer and either
decompression on every read or a stored-only zip, which gains nothing over a folder. Zips are the
**distribution** form: the mods browser (charlie, C2) downloads and verifies an archive and unpacks
it into `mods/<id>/` (`files/` + `mod.json`), then appends the id to `enabled.txt` if it should be on.

### The toggle API (for the in-game mods menu)

Native functions in `pc/platform/gw_mods.h`. Game code declares them **without** the `gw_` prefix
(`extern int Mods_Count(void);`). Ints and `const char*` only; strings stay valid until exit.

| call | meaning |
|---|---|
| `int Mods_Count(void)` | mods found (enabled or not), index 0..n-1 in id order, stable for the session |
| `const char *Mods_Id/Name/Version/Kind/Pack/Description/Requires(int i)` | metadata; `Requires` is comma-separated; `""` for a bad index |
| `int Mods_Find(const char *id)` | index or -1 |
| `int Mods_IsActive(int i)` | mounted this boot |
| `int Mods_Status(int i)` / `const char *Mods_StatusText(int i)` | 0 active, 1 off, 2 missing requirement, 3 conflict; text like `needs ace-base` |
| `int Mods_IsEnabled(int i)` | in the set for the next boot |
| `int Mods_SetEnabled(int i, int on)` | toggle for the next boot. On also enables its requirements and turns off enabled mods that conflict with it (and their dependents); off also turns off everything that requires it. Returns how many mods changed |
| `int Mods_Save(void)` | writes `mods/enabled.txt` (write-then-rename); 0 ok, -1 failed |
| `int Mods_RestartNeeded(void)` | the next-boot set differs from what is mounted |
| `const char *Mods_Dir(void)` | the folder in use |

## 5. The split tool

`tools/mex_port/split_modpack.py --pack _build/packs/ace-set/ace --name ace --version 2.0.0`
writes `_build/mods-split/ace/` - a mods folder the port can use directly
(`MELEE_MODS_DIR=_build/mods-split/ace`). Files are hard-linked from the pack (no extra disk).
Everything assigned comes from `MxDt.dat`:

- a **fighter mod** per m-ex fighter row with a Pl file: its Pl file, animation file, costume
  files, result-screen file, demo files named by its ftDemo symbols, effect bank, sound bank, Kirby
  copy file and copy effect bank, ending movies/videos, and the Target Test stage its row names;
- a **stage mod** per stage-select icon naming an added stage (external id >= 33): its Gr file,
  named from m-ex's stage-name table (`ace-stage-bowser-s-castle-paper-mario` is `GrKcs.dat`);
- a file two entities both claim (Wolf and Wolf SSBU share a result file and demo files; B. Falcon
  uses Captain Falcon's sound bank) stays in the **base**, as does everything unclaimed: `MxDt.dat`,
  menus, `PlCo.dat`, shared banks, all music, trophies.

Result: ACE -> base (413 files, 653 MB) + 31 fighters + 71 stages; Akaneia -> base (289 files,
261 MB) + 7 fighters + 18 stages. `--enable id,id,...` writes `enabled.txt`; `--dry-run` prints.

## 6. Netplay: mods online, matched per fighter and per stage

Two players may run different mods. Nothing is refused for having different mods; instead:

**Content identity** (`pc/platform/gw_mexid.c`). Every fighter and selectable stage gets a 64-bit
hash over the files that define it, read through the file layer - so the same stage baked into a
mod ISO and as a loose mod hashes the same (file names and the source are not inputs):

- fighter: `Pl<xx>.dat` (attributes, subactions, m-ex code, articles) and `Pl<xx>AJ.dat`
  (animations move the hitboxes); Zelda/Sheik and Ice Climbers include their partner's pair; an
  m-ex fighter includes its Kirby copy file. **Excluded as cosmetic**: costumes, effect banks,
  sound banks, CSS art.
- stage: its Gr file(s) (`<prefix>.dat` and `<prefix>1..9.dat` for prefix names like `/GrPs`).
  Excluded: music, SSS art, `.usd` language variants.
- The table covers the 26 retail fighters, the m-ex fighter slots, the 29 retail VS stages and every
  m-ex stage-select icon whose stage is present (157 entries on full ACE; hashing ~220 MB took
  0.3 s with the files in the OS cache).

Verified: Wolf is `fad2e7c835a66f21`, Sonic `b1d4e1442c26296d` and Bowser's Castle (Paper Mario)
`260f238b5d0edb92` both on the ACE ISO and on the vanilla ISO with the split ACE mods, where Sonic is
CharacterKind 35 instead of 38. Retail fighters and stages hash the same on vanilla, ACE and Akaneia
(neither pack modifies their files).

**Global game data** must match exactly - it is the only thing that refuses a connection. It is
sent as `mods_hash` in the existing HELLO, and a refusal names what differs
(`Refused: game data differs from the host's: m-ex feature flags (MELEE_MEX / mods\mex.txt)`):

- `PlCo.dat`'s 21 global tables (all but the two per-kind tables `ftPartsTable`/[5], which an m-ex
  build extends for its roster) at their retail sizes. An offline walk of every retail table and
  everything under it found vanilla, ACE 2.0 and Akaneia 1.0.1 identical (m-ex only appends, and
  edits rows >= 27 of the per-kind tables), so they agree; the hash does **not** descend into nested
  tables, so a mod that edits those is not caught.
- `ItCo.dat` whole (common items).
- the port's m-ex feature flags: `MELEE_MEX` plus `<exe>\mods\mex.txt` (what `gw_Mex_Enabled` reads).
- The disc image hash is **no longer compared** (`iso_hash = 0`); the exe hash still is.

**Exchange and intersection.** After the handshake each side sends its identity list
(kind, 48-bit identity, local id; 21 entries per 200-byte message) over gw_net's lobby channel,
tagged `MXE`, paced one message every 4 polls. Each side then knows which entities are common and
how the other side numbers them. **Match setup names content by identity**: the scene string the
host sends says `p1=id:<16 hex>/c0/hu;...;stage=id:<16 hex>`, the guest's HELLO names its fighter
as `id:<hex>`, and the scene parser (`gw_runtime.c`) resolves `id:` to the local CharacterKind or
external stage id. A guest that lacks something the host picked stops with
`The host's match uses content you don't have: fighter fad2e7c835a66f21`.

API for the online CSS/SSS (`gw_mexid.h`, game code without the `gw_` prefix):

| call | meaning |
|---|---|
| `int MexId_PeerReady(void)` | the peer's list has arrived |
| `int MexId_OnlineFighter(int ck)` / `MexId_OnlineStage(int ext)` | 1 both have it, 0 not common, -1 list not here yet |
| `int MexId_PeerCkForLocal(int ck)` / `MexId_LocalCkForPeer(int peer_ck)` | CharacterKind mapping, -1 if not common |
| `int MexId_PeerExtForLocal(int ext)` / `MexId_LocalExtForPeer(int peer_ext)` | stage mapping |
| `int MexId_CommonFighterCount/CommonStageCount(void)` | -1 until the list is here |
| `int MexId_Count/Kind/LocalId(int i)`, `const char *MexId_Name/HashHex(int i)` | this install's table |
| `const char *MexId_TokenForCk(int ck)` / `MexId_TokenForExt(int ext)` | `id:<hex>` scene tokens |
| `int MexId_SceneCheck(const char *scene, char *why, int cap)` | unresolvable `id:` tokens in a scene |

The lobby's `CHAR` actions and state broadcasts are translated with `LocalCkForPeer`, so each side
keeps CharacterKinds in its own numbering.

## 7. What was tested

- Headless suite (after syncing with pc-port): 108/108 on the ACE ISO (with and without run.sh's
  default `_build/mods`), 108/108 on the vanilla ISO with the split ACE mods (ace-base, ace-wolf,
  ace-sonic, ace-stage-bowser-s-castle-paper-mario), 108/108 on the vanilla ISO with no mods.
- Vanilla ISO + those split mods: Wolf and Sonic on the CSS (25 retail + 2), a Wolf vs Sonic match
  on Bowser's Castle (Paper Mario).
- Two local netplay clients (`_build/netplay_local.ps1 -Exe ... -EnvHost @{MELEE_MODS_DIR=...}`):
  same mods -> Wolf vs Sonic on the ACE stage, 0 desyncs; host with Wolf+Sonic vs guest with only
  Sonic -> Sonic (host ck 35) vs Sonic (guest ck 34) by identity, 0 desyncs; host picks Wolf ->
  guest stops with the missing-content message; guest with a different `MELEE_MEX` -> refused,
  naming the feature flags; vanilla with no mods vs vanilla + ACE mods -> Fox vs Marth, 0 desyncs.

## 8. Known limits and open ends

- Entity mods combine only within one pack (section 3); a second base is refused.
- On a vanilla save file, m-ex added stages are shown locked ("?") on the SSS: the save has no
  unlock bits for them (`gm_80164430` in `mnStageSel_MexScanUnlocked`). They load fine by scene.
  Suggested fix for the SSS owner: treat a present added stage as unlocked.
- m-ex CharacterKinds shift with the enabled set (dense slots). Anything that stores a
  CharacterKind across boots (saved CSS picks, scripts, `LANES.md`'s ACE numbers) assumes a set.
- Identity gaps: fighter identity does not cover MxDt's per-fighter function-table row, item
  descriptors, or the fighter's `PlCo.dat` per-kind rows; stage identity does not cover the MxDt row
  or stage item tables. Two installs whose content differs only there would be "common" and could
  desync. Cross-pack play (ACE base vs Akaneia base) passes the global check but was not tested;
  custom item kind numbers differ between packs, which is harmless unless they reach the state
  checksum.
- The identity exchange rides the lobby channel, so in the boot-time path (`MELEE_NETPLAY=` at
  boot, no lobby) the lists are not exchanged; that path relies on `id:` tokens alone. The exchange
  over the real channel is covered by a unit test through the real encoder, but it has not been
  observed end to end in the menu lobby yet.
- The identity table is built on first use (at netplay start): about 0.1-0.3 s with warm file
  caches, more cold.
