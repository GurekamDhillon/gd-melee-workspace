# Geno slice 6: presentation and integration, brief and first increments (2026-10-07)

**Status: brief for the slice 6 lane, with the first increments built (game `agent/geno-s6`, workspace `ws/geno-s6`, not merged).**
It continues `docs/superpowers/plans/2026-10-05-geno-full-fighter-slice2.md` (its "Slice 6" section and decisions D2 and D11 are
the contract; this document is the grain that section promised) and reads the state after slice 4 (the Courier, `base: "none"`,
format 9). Written from source first, then built: every "built" below is stated with the evidence in section 6; "owed" means it
needs a person with a monitor.

Tags: **[R]** read from source (`path:line`, relative to the game checkout `melee/` unless it begins `tools/`, `docs/`, `_build/`;
lines are those of the tree before this lane's edits, and they move: re-grep), **[I]** inferred, **[U]** unverified, **[B]** built
and checked in this lane (evidence in section 6).

## 1. What a define shows today, per item (read from source)

A define is a resident CK in 34..127 (FighterKind = CK - 1). Almost every presentation table is indexed by retail kind, and
`Geno_DefineBaseCK(ck)` answers 8 (Mario) for **every** define, `base: "none"` included [R `pc/platform/geno_define_registry.inc:199-207`:
`return p >= 0 ? 0 : -1; /* native Mario only in slice 1 */`, `gw_Geno_DefineBaseCK ... ? 8 : -1`]. So a define is shown through Mario's rows
wherever code asks "what is the base": that is decision D11 of the slice 2 plan at work, and it is the whole reason this slice exists.

| item | what a define gets today | what is wrong | [R] |
|---|---|---|---|
| CSS tile and portrait | the **Atlas** adapter borrows Mario's icon (`fs_css_roster` copies the base kind's tile) and draws Mario's portrait (`mnCharSel_PcArtPortrait` maps the CK to its base) with the define's name | a Courier select tile with Mario's face. The retail CSS (`mncharsel.c`) never lists defines: only the native screens do | `gmfrontend_select.inc:389-396`, `mncharsel.c:6523-6524`, `gmfrontend_atlas_select.inc:420,474` |
| name | right: `Geno_DefineName` on every native path | none | `gm_1601.c:803-805`, `gmfrontend_atlas_select.inc:187` |
| HUD stock icon | Mario's head, in Mario's costume colour | in every match | `gm_1601.c:4167-4180` (`gm_80168BF8` -> `gm_80168B34(base)`), `ifstock.c` (eleven `HSD_TObjReqAnimAll` sites) |
| results screen | the name strip is **blank** (a define is no m-ex slot: `Mex_PortCKindToExt` is -1, so the "draw the name from MxDt" path has no name); the emblem is hidden; the 3D pose is the own Wait clip (b9ab68fb6) and the victory theme is Mario's | a blank name plate | `gmresultplayer.c:626-627,599-600,716`; `gm_1601.c:470-481` |
| announcer | Mario's call ("Mario!") when the native CSS or the results screen announces the pick | names the wrong fighter. The Atlas and legacy kit selects play no announcer at all | `gm_1601.c:4184-4223`, `mncharsel.c:2297,2380,2913`, `gmfrontend_atlas_select.inc:232-241` |
| voice | Mario's sound bank (`lbAudioAx_80026E84` maps the CK to the base); no bank is read from a package | Mario's voice | `lbaudio_ax.c:1752-1779`, `ft_0877.c:313-316` |
| costumes | the count is **Mario's** (`gm_GetNumCostumesForCKind` remaps to the base): the select offers 5 costumes for the Courier's 4 files, and index 4 reaches `CostumeListsForeachCharacter[fk].numCostumes` = 4 [I: an out-of-range costume file, to be seen]. Team colours are Mario's `x1/x2/x3` (red 0, blue 3, green 4 [I: values not read]) | a count past the real list; a team match picks costume indices that are not the define's | `gm_1601.c:4410,4457,4474,4491`, `gmfrontend_select.inc:334-338,607-609`, `geno_define_data.inc:127-130` |
| Kirby copy | a define's kind goes into `hat.kind` unchanged and every per-kind table is indexed by it without a guard; a define is inside every table (`Ft_Kind_Max` is 127) so nothing reads out of bounds, and the rows are empty (`ftKb_Init_803C9DD0[kind]` NULL falls back to Kirby's own inhale) | no copy ability, no crash [I]; not run | `ftkirby.c:3907-3909,2285,2358,2437`, `ftCo_ThrownKirby.c:43-58`, `ftdata.c:1797-1798` (the m-ex data path, not for defines) |
| CPU AI | every `fp->kind` switch takes its default arm (no special-move roll, no ranged-attack choice, recovery = `ftCo_CpuRecoverDiagonally`); the per-kind AI table copy reads the **base** row (`gm_MexVanillaKind` -> Mario's), so a define's CPU has Mario's ground/air/edge-guard tables | a CPU Courier plays like a Mario with no specials | `ftcpuattack.c:1106,1445,2308,2821`, `ftCo_0A01.c:552,832,4486`, `fighter.c:281-287` |
| records | the save's per-fighter rows are indexed by selkind and `gm_CKindToSelKind` sends **every m-ex or define CK to one retail row** (`ckind_to_selkind_map[ChKind_Popo]`, which the table spells `SELKIND_CAPTAIN`): a define's KOs, play time and stats are written into Captain Falcon's record | a Courier match edits a retail fighter's record | `gm_1601.c:743-744,1290-1320,1359-1366`, `gm_1601.static.h:115` |
| intro, target test, credits | not read this lane (the intro copy has 16 subaction rows and the overlay is skipped quietly, slice 2) | unknown | `docs/geno.md` 22 |

## 2. Ranking: player impact against cost, and where each goes

"Atlas" is the Atlas select adapter (`gmfrontend_atlas_select.inc`, drawn by the host screens of step 4; its roster, art and costume counts are fed
by the shims). "Retail" is the game's own scene code (HUD, results, save) that runs under both menus. The CSS state machine is not touched here: the
Atlas lane owns it.

| rank | item | impact | cost | goes on | first increment |
|---|---|---|---|---|---|
| 1 | costumes as declared colour sets | high: a select that offers 5 of 4 costumes and team colours that are not the define's | low: three accessors, two keys of an existing block | retail accessors (`gm_1601.c`) + the one shared count the Atlas adapter reads (`fs_costumes`) | **built [B]** |
| 2 | records | high for the owner's save (a retail fighter's record is edited by a define's match) | low: skip the writes for a define | retail (`gm_1601.c`) | **built [B]**: not written; a define's own records (a stable key) is open, see D7 |
| 3 | CSS icon, portrait, name | high: it is the first thing a player sees of the fighter | medium: one asset route (a `.gxtex` of the package), one host loader, the adapter's art call | **Atlas** (the legacy kit select keeps the donor's art until it is retired; the retail CSS never lists a define) | **built [B]** |
| 4 | HUD stock icon | high: it is on screen for the whole match | medium: a frame sentinel and a TObj image swap | retail (`ifstock.c`) | **built [B]** |
| 5 | results: name plate, emblem, pose, stock icon | medium: once per match, a blank plate | low (name) to medium (package emblem and results stock icon) | retail, and the **Atlas results** stand-in when the owner enables it (`MELEE_ATLAS_SCENES=5:replace`) | name **built [B]**; emblem, results stock icon and the Atlas results later |
| 6 | announcer and voice | medium: "Mario!" on a Courier pick; Mario's voice | **high**: a package needs an audio container and a source (original audio) | retail (`gm_80168C5C`, the bank mask) | interim: a define is silent in the announcer **built [B]**; own audio is an elevated decision (D8) |
| 7 | CPU AI hints | medium: CPU Courier matches | **high**: a strategy, not a patch (D9) | retail (`ftcpuattack.c`, `fighter.c` tables) | none: elevated |
| 8 | Kirby copy | low: a define as a copy source is rare | high for an ability (a hat model, a move); low for the `none` policy | retail (`ftkirby.c`) | none built: the `none` policy needs a run to be called safe (owed, section 7) |

The order of the first increments is the order of the table down to row 5. The slice 2 plan's S6-1 to S6-9 stay as the task list; this
document re-orders them by impact and says what moved.

## 3. Decisions taken

| # | Decision | Reason | Reversed if |
|---|---|---|---|
| D1 | A package's own menu and HUD art is **`.gxtex` files in its `files/` folder** (the container `pc/tools/png2gx.py` already writes and `gw_kit.c` and `gw_runtime.c` already read), named by an optional entry-level `"presentation": {"icon", "portrait", "stock"}`; `portrait` and `stock` are one name or a list per costume (a costume past the list uses the first). No new asset format. | Three readers of this container already exist [R `gw_kit.c` `kt_load`, `gw_runtime.c` `gw_gxtex_*`, `pc/tools/png2gx.py`]; the same bytes feed the kit pool (host) and an `HSD_ImageDesc` (game), because GX texture data is byte-order independent. | the owner wants PNG authoring in the package (a decoder in the host; the engine would still keep `.gxtex`) |
| D2 | Slice 6 adds keys to **`"geno": 9`**, with no version bump: `presentation` (entry level) and `name`, `team` (inside `fighter.costumes[]`). `presentation` is refused below 9; an engine that does not know it ignores it (nothing in it is simulation state). **ELEVATED**: if the owner wants a visible mismatch, the bump is 10 and the slice 5 lane may be taking it. | D4 of the slice 2 plan bumps because a dropped key silently changes *behaviour*; art and costume names do not. The entry's content id changes when the keys are present (it hashes the entry), and not otherwise (a test pins the Hero-shaped id). | the owner wants an old engine to refuse a package with art |
| D3 | A base `"none"` define never shows donor art: its select tile is letters (`DISC ART`), its portrait the same, until it declares its own. A donor-based define (`base: "mario"`) keeps the borrowed art unless it declares. | Showing Mario's face on the Courier is wrong; the placeholder frame is already the shipped look for missing art [R step 4 plan, "Disc art is never stored"]. | never |
| D4 | The select art is the **Atlas** adapter's. The legacy kit select (`gmfrontend_select.inc`) keeps the donor's tile for a donor-based define and none for a `none` define; its retirement is step 4 Task 14, not this slice. | Two drawings of one select is the state the Atlas lane is already retiring; spending slice 6 on the legacy one is waste. | the owner keeps the legacy select longer than planned |
| D5 | Costumes are **declared colour sets**: `fighter.costumes[i].name` (select label) and `.team` (`red`, `blue`, `green`: the team battle colour that costume is). Undeclared: red is costume 0, blue 1, green 2, each wrapping to 0 when there are fewer. A donor-based define keeps Mario's list. | The costume files and their count were already the package's; the count and team indices still came from Mario's table. | a colour needs more than a name (a palette swap of a donor model: a later slice) |
| D6 | The HUD stock icon is swapped **per TObj** (the icon's own image table is pointed at the package's image), not by editing the shared IfAll atlas. The frame number carries the request (a sentinel no atlas has), so every stock-icon site is covered by one wrapper in `ifstock.c`. RGB5A3 or RGBA8 only (the swap carries no TLUT). | One chokepoint instead of eleven edits; the shared atlas stays the disc's; the images live in the scene heap and are rebuilt per scene. | an Atlas HUD replaces the retail stock HUD (then the Atlas HUD draws the kit texture directly) |
| D7 | **Records**: a define's matches do not write retail rows (built). Its own records live under a **stable key** (the define key), in a store of their own: **ELEVATED** (save-file shape: a new file beside the save, or a block in the existing one; the owner's call on retail-save compatibility). | The alternatives write into a retail fighter's row or change the save layout. | never for the guard |
| D8 | **Announcer and voice**: **ELEVATED**. Interim built: a define is silent in the announcer. Options: (a) package ships its own audio (WAV converted offline to the engine's sound container; needs the offline converter, the mixer representation and named events for rollback suppression, listed in `docs/geno.md` 22.2 as slice 6 work) [recommended], (b) a define names an engine sound id that already exists (the v8 `sounds` resolver; no new audio, limited to the disc's own sounds), (c) text-only callout. | Audio is the one asset class with no original source in the repo today and the one the owner must hear. | n/a |
| D9 | **CPU AI**: **ELEVATED**, no code. Options: (a) `ai.like: "<retail fighter>"` makes every kind switch and the per-kind AI table copy answer as that fighter (cheap, honest, one key) [recommended first]; (b) declarative hints (recovery kind, ranged yes/no, approach distance, edge-guard) mapped to the same rows; (c) a Lua policy (slice 5). The default arms are harmless for ground-and-air fighters (D11 of the slice 2 plan) and bad only for fighters whose recovery is an up-B. | A strategy choice, not a patch: it fixes how authors express a fighter's character to the CPU. | n/a |
| D10 | **Kirby copy**: policy key `kirby_copy: "none" | "retail:<fighter>"` (an `ability` policy, a hat model and a move, is out of this slice). `none` is today's behaviour made explicit and guarded. **ELEVATED**: whether a `retail:<fighter>` copy (Kirby wears another fighter's hat for the Courier) is wanted; it needs the hat model's visual sign-off. | A define has no hat model; reusing a retail one is a visual-policy choice. | n/a |
| D11 | Atlas Results (`MELEE_ATLAS_SCENES=5:replace`, step 8, off by default) reads names and art through the same accessors (`Geno_DefineName`, the presentation art); it is not edited here. | The Atlas lanes own it; the accessors are the contract. | n/a |

## 4. Ordered tasks

Test registration pattern: the registry half in `pc/platform/geno_define_tests.inc` (included by `geno_registry.c`), registered in
`geno_registry_tests_register`; Python in `tools/geno/test_define.py`. All additive; no shared header or format version is touched.

| task | what | files | state |
|---|---|---|---|
| S6-1 | costumes: `fighter.costumes[].name/.team`; `gw_Geno_DefineCostumeCountCK`, `_TeamCostume`, `_CostumeName`; `gm_GetNumCostumesForCKind`, `gm_80169264/801692BC/80169290` answer a `none` define's own; the select's `fs_costumes` and the card/stepper labels use them | `geno_define_registry.inc`, `geno_registry.c`, `gm_1601.c`, `gmfrontend_select.inc`, `gmfrontend_atlas_select.inc` | **built [B]** |
| S6-2 | the presentation route: `"presentation"` parse (strict), `gw_Geno_DefineArtTex` (kit texture) and `gw_Geno_DefineArtOpen` (a gxtex handle), `gw_Kit_TexAddGxtex`, `gw_GxTex_OpenBlob`, the shim `Ui_ArtGeno` | `geno_define_registry.inc`, `gw_kit.c/.h`, `gw_runtime.c`, `gw_script_ui_sel.inc` | **built [B]** |
| S6-3 | the Atlas CSS: tile and portrait from the package; none for a `none` define without art; costume names on the card and stepper | `gmfrontend_atlas_select.inc`, `gmfrontend_select.inc` (roster) | **built [B]**; owner's look owed |
| S6-4 | the HUD stock icon from the package (`gm_GenoStockFrame`, the wrapper in `ifstock.c`) | `gm_1601.c`, `ifstock.c` | **built [B]**, seen in a headless capture |
| S6-5 | results: the name plate from the define's name | `gmresultplayer.c` | **built [B]**; not seen (a results screen needs a finished match) |
| S6-6 | records: a define writes no retail row | `gm_1601.c` | **built [B]** (read and syntax; a played match is owed) |
| S6-7 | announcer: a define is silent (interim, D8) | `gm_1601.c` | **built [B]** |
| S6-8 | the Courier's own art: `ports/vanilla-original/ui_art.py` renders an icon, a portrait and a stock icon per costume from its own model; `build_courier.sh` converts them with `png2gx.py`; the fixture declares them and its costume names and teams | `ports/vanilla-original/ui_art.py`, `tools/geno/build_courier.sh`, `pc/geno/mods/vanilla-courier/geno.json` | **built [B]**; placeholder-grade, the owner chooses the look |
| S6-9 | tools: `schema.py` (the keys), `define.py` (`geno: 9` for presentation, duplicate team, list length), `check.py` (the files of `files/`: a v1 container that fits, no palette for a stock icon, a missing file is a warning), `export_package` carries the art | `tools/geno/*` | **built [B]** |
| S6-10 | results, the rest: the winner's **card picture** (blank for a define: seen), a package emblem, the results stock icon (`gm_80168B34` at `gmresultplayer.c:1353,1383,1401`) through the same sentinel; the Atlas results stand-in reads the accessors | `gmresultplayer.c`, `gmfrontend_atlas_data.inc` | open |
| S6-11 | `kirby_copy` policy and its guard; a run of Kirby inhaling a define | `ftkirby.c`, registry | open (D10) |
| S6-12 | CPU AI hints (D9) | `ftcpuattack.c`, `ftCo_0A01.c`, `fighter.c`, registry | open (elevated) |
| S6-13 | a define's own records under a stable key (D7) | save layer | open (elevated) |
| S6-14 | announcer and voice audio (D8) | audio container | open (elevated) |
| S6-15 | resident-index census and widening plan (the slice 2 plan's S6-8): the define aliases 127 down to 34 are the m-ex range; every table indexed by CK, kind or selkind is listed with its bound | `docs/geno.md` | open |
| S6-16 | the sweep: versus and Classic with the Courier on the CSS, results, team costumes, CPU recovery, a Kirby inhale, the intro and credits | in game | open (owed) |

## 5. Coordination with the parallel lanes

- **Slice 5 (fighter Lua)** and the **slice 4 closeout** edit `pc/geno/*` and `geno_registry.c`; this lane's edits there are additive:
  new functions and one new struct pointer in `gn_profile`, new keys read by new functions, tests appended at the end of
  `geno_define_tests.inc`, registered after `geno_define_resolver`. **No format version is taken.** If slice 5 bumps to 10, `presentation`
  keeps working at 9 and above (the gate is `version < 9`).
- **Atlas lanes**: the adapter edits are a handful of lines at the cell, the portrait and the card label (`gmfrontend_atlas_select.inc`);
  they route through one new shim (`Ui_ArtGeno`). The select's state machine, profiles and the host models are not touched. If step 4's
  Task 14 retires the legacy kit select first, `fs_css_roster` (the `fcs.icon` borrow) goes with it and only the Atlas lines remain.
- **Release**: nothing under `tools/release` is touched. A build that includes the Courier's `.gxtex` files in a package is not covered by
  `original-assets.json` (its record lists the `.dat` files and the plan); custom fighters are not shipped in 0.2.0.

## 6. Test plan and evidence

Native (registered, headless, `run.sh --test`): `geno_define_presentation` (costume colours and names declared, undeclared defaults for 4, 2 and 1
costumes, refusals; art files resolve per costume and fall back to the first; refusals for format 8, unknown key, `.png`, a path, `..`, an icon
list, a non-object, 17 entries; a define without `presentation` keeps its id), `geno_gxtex_art` (a 4x4 RGB5A3 file decodes into the kit pool to the right
texel, the same key is the same slot, a short file, a wrong magic, version 2 and an unknown format are refused; the game-side handle API round
trips the payload bytes), `geno_define_presentation_ck` (the live registry by CK: costume count, team colours, names, art flags; a missing art file
answers -1; a retail CK answers nothing). Python (`tools/geno/test_define.py`): the Courier declares colours and art and checks clean, the
version gate, the key rules, the file checks. Suite: 321 before, 324 after, `fail=0`.

In the exe (this lane's build, 2026-10-07, vanilla disc, the window parked off screen, the Courier mounted through `MELEE_MODS_DIR`):

- **HUD** (`MELEE_SCENE="mode=vs;p1=geno:vanilla-courier;p2=mario/cpu0;stage=fd"`, `gd.screenshot`): the P1 stock icon is the Courier's helmet next to Mario's
  head on the P2 side; log `geno: stock icon of ck 127 costume 0: 32x32 format 5 from its package`. (`gd.screenshot` omits the host overlay, so the **Atlas
  screens cannot be captured**: the select's evidence is the log.)
- **Select** (`mode=vs;at=css;p1=geno:vanilla-courier`): `geno: Vanilla Courier: select icon from its package: GnCourier_icon.gxtex as kit texture 398`,
  `frontend: character select - ck 127 icon from its package (kit texture 398)`, the same two lines for `portrait ... GnCourier_csp_default.gxtex ... 400`.
- **Results** (a one-stock match ended with the debug cursor, `match=stock;stocks=1`): the banner and the plate read `VANILLA COURIER`
  (`gw: results: ck 127 (m-ex ext -1) has no name art of its own - drawn "VANILLA COURIER" 256x28` and `120x24`); capture seen. **New finding**: the winner's
  **card picture is blank** (Mario's card shows his face): a results card face and the small stock icon are S6-10.
- Not seen: team costumes (no team match was played), a played match's save, the announcer, Kirby. Two scripted attempts to make Kirby inhale a Courier did not start the
  inhale (Kirby ended in Wait with B held), so the Kirby claim in section 1 stays [I].

## 7. Owed (a person with a monitor) and what to look at

0. **Everything below was built and logged, and only the HUD and the results were captured**: the host overlay is not in a screenshot, so the Atlas select has not been seen by anyone.
1. **Character select, Atlas** (`MELEE_SCENE="mode=vs;at=css"` with the Courier mounted): the Courier's tile shows its own head, the portrait panel its three-quarter
   figure per costume (X/Y cycles; the stepper reads `1 / 4 Teal`), and a card with the Courier says `Teal`, not `Costume 1`; the Hero (Mario-based) still shows Mario's face.
   A `none` define without art shows letters and `DISC ART`.
2. **Team battle**: three Couriers on red, blue and green teams wear costumes 1, 2 and 3 (red, blue, green), never a fifth.
3. **HUD**: the Courier's stock icon is its helmet, in its costume's colour, beside the retail icons.
4. **Results** after a finished match: the Courier's name on the plate (before: blank). The emblem stays hidden.
5. **Announcer**: no "Mario!" when picking the Courier on the native CSS.
6. **A played match**: a Courier match leaves Captain Falcon's record as it was.
7. **Kirby inhale** of a define: no crash, no copy (not run).
8. The art is a placeholder rendered from the model; the real look is the owner's.

## 8. Evidence limits

Read: the slice 2 plan, `docs/geno.md` 22, the Atlas step 4 plan's constraints, `NEXT-SESSION.md`; the sources cited. Four surveys (announcer and voice, Kirby
copy, CPU AI and records) were made by reading only; items 5 to 8 of section 1 rest on them, and the claims marked [I] have not been run.
