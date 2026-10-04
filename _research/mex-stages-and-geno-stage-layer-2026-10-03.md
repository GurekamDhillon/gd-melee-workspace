# m-ex stages, and what a Geno stage layer would add (2026-10-03)

Read-only research. No tracked file edited, nothing built or launched. Scratch (clones, not committed) is in
`_build/tmp/mex-stage-research/` (`m-ex-up/` = akaneia/m-ex at c9f25da; `tm/` = UnclePunch/Training-Mode at fa0b9ef).
Companion notes: `_research/mex-stages.md` (our dump of the stage tables, still the best reference),
`_research/seamless-stage-switch-2026-10-03.md` (the switching feasibility study, which wins on anything about
switching). Tags: **VERIFIED** (read at the cited place) / **INFERRED**.

Upstream is cited as `m-ex:<path>` = `https://github.com/akaneia/m-ex/blob/master/<path>` (commit above). The same tree is
checked out locally at `_build/m-ex/`. m-ex has **no licence** (GitHub reports none); we consulted, quoted a few words at most,
copied nothing (matches `DEPENDENCIES.md`).

## Short answer

- m-ex has **no** mid-match stage switching and **no** data-described stage behaviour. A stage is a table row plus a `Gr*.dat` plus
  optionally one block of PowerPC that fills the stage row's callback words. Your statement to the owner was right in substance.
- It is slightly less bare than "table rows and files": the PowerPC callback set is fuller than "on load", there is a small helper
  API (collision-group enable/disable, moving collision, map-GObj animation state, hazards, colour animation) and a per-map-GObject
  `onDeletion`. Those are helpers called from hand-written code, not descriptions.
- Alternate layouts exist, but as a **file swap before the match**, not a live change.

## A. What m-ex provides for stages

| capability | how m-ex expresses it | our port today |
|---|---|---|
| Add a stage (internal id) | `mexData +0x2C` `Arch_grFunction`: array of 13-word `GrDesc` rows, the same layout as the game's `StageData` (m-ex:`MexTK/include/stage.h` `struct GrDesc`; `MexTK/include/mxdt.h:354`) | Yes. `Ground_MexStageDatas`, `gw_Mex_GrFile`; 96 (Akaneia) and 155 (ACE) rows (`_research/mex-stages.md` s1, s5, s9) |
| Add a stage select entry / external id | `Arch_Map.StageIDs` (external to internal, 12 bytes) and the SSS icon table (`MnSlMapIcon`, `mxdt.h:161`) | IDs yes (`gw_Mex_GrKindForExt`); SSS widening was listed as work (`mex-stages.md` s7); `gw_mex_sss.c` exists. Re-verify before claiming |
| Stage file | `GrXx.dat` named in word 2 of the row | Yes, mounted mod DATs resolve (`gw_Mex_GrFile`) |
| Name, SFX bank, echo | `Arch_Map.StageNames` / `.Audio` (`MexStageSound {ssmid, reverb, x03}`, `mxdt.h:198`) | Yes (`lbAudioAx_MexStageAudio`, banks past 63 by index; `mex-stages.md` s6) |
| Music playlist | `Arch_Map.Playlists` (`{u16 bgm; u16 chance}` entries) | Yes (`Mex_GrBgmCount/Id/Chance`, `ground.c:292-294, 2030-2046`) |
| Line types, friction | `Arch_Map.LineTypeData`, an absolute address into vanilla's 71 tables; m-ex authors no new line-type data (`mex-stages.md` s6) | Yes, as a row index (`gw_Mex_GrLineTypeRow`) |
| Stage-local item list | `Arch_Map.StageItemLookup` (`{count, u16* kinds}`), `MEX_GetGrItemID` (`mxdt.h:367`) | Yes (`gw_mex_items_query.inc`, `gw_Mex_UnloadStageItems`); custom item 237 for GrOPc noted as a dependency |
| Per-stage code | `grFunction` public symbol in `Gr*.dat`: relocatable PPC `MEXFunction`; `ReplaceThis` is a word index into the stage's own row, `Overload` writes the code address there (`m-ex:asm/m-ex/SSS Expansion/Init grFunction.asm`, inserted at 0x801C60C8). Names of the 13 words: `m-ex:MexTK/grFunction.txt` | Yes: blob relocated in the stage's own archive, native trampolines, interpreter (`gw_mex_grfunction.c`, `mex-ppc-interpreter.md`) |
| Callbacks a stage can supply | row words: `oninit`(3), `ondemoinit`(4), `onload`(5), `ongo`(6), `onunused`(7), `ontouchline`(8), `oncheckshadowrender`(9). Hooks: `StageOnGO.asm` (0x801C0FD8), `StageOnStart.asm` (0x801C0F8C), `Stage_Init.asm` (0x801C0828), `StageFileLoad*.asm` | Yes, seven trampolines `gw_Mex_GrOn*` |
| Per-map-GObject callbacks | `map_gobjs` (row word 1, DATA): `MapDesc {onCreation, onUnk, onFrame, onDeletion, flags}` (`stage.h:110`) | Yes (`gw_Mex_GrBind`, `grTSeak_80223908` redirected) |
| Moving collision | row words 11/12 ("moving_coll_count / moving_coll" in `grFunction.txt`), consumed by m-ex's repointed `Stages_MovingCollisionPoints{Initialize,Remove,UpdateALl}.asm`; helpers `Stage_InitMovingColl`, `Stage_UpdateMovingColl` (`stage.h`) | Words carried through (`GW_MEX_GR_SLOT_JOINTS/JOINT_COUNT`); never overridden on the shipped stages (`gw_mex_grfunction.h`) |
| Collision groups on and off | helpers `Stage_EnableLineGroup/DisableLineGroup/LinkLineGroups`, `Stage_SetGroundCallback` | Engine functions exist; the interpreter reaches them only if in the bridge table |
| Animation and states | `Stage_SetMapJOBJAnim`, `Stage_MapStateChange`, `Stage_CheckAnimEnd`, `anim_behave` in `MapGObjDesc` | same |
| Hazards | `Stage_InitDamageHazard/MoveHazard/CatchHazard`, `LineHazardDesc`, `Stage_CreateMapItem` | same |
| Colour animation (ColAnim) | `Stage_InitColAnim/ApplyColAnim/DisableColAnim` | same |
| Stage-select pages | `SSSPages/LRCheck.asm` (R press pages the icon grid), `mexMapData` | not a gameplay feature |
| Alternate stage name | `Slippi Compatibility/CheckAltStageName.asm`, `mexMapData/StageName - Alt Index.asm` (display text only) | n/a |

VERIFIED sources for the row above: `m-ex:MexTK/include/stage.h` lines 110-119, 494-530, 585-659; `m-ex:MexTK/grFunction.txt`;
`m-ex:MexTK/include/mxdt.h:148-213, 340-371`; the `asm/m-ex/SSS Expansion/` tree. Everything in the "our port" column is from
`_research/mex-stages.md`, `docs/MEX_PORT_STATUS.md`, `gw_mex_grfunction.h/.c`, not re-run today.

Small discrepancy to settle: `grFunction.txt` names word 11 `moving_coll_count` and word 12 `moving_coll`; the decomp's `StageData`
(`melee/src/melee/gr/types.h:168-169`) has `joints` at 11 and `joint_count` at 12. One of the two naming orders is off. It does not
matter while no shipped stage overrides either word.

## B. Mid-match stage switching in m-ex: does not exist

- VERIFIED: the stage row is selected once per scene. `Stage_Init.asm` patches 0x801C0828 to read `Arch_grFunction[internal id]`;
  `Init grFunction.asm` runs once at stage file load (0x801C60C8) and reads the id from `stage_info.grkind` (0x8049E6C8 + 0x88).
  There is no entry point, helper or header function that reloads a stage, swaps `Arch_grFunction` rows, or tears the stage down.
  `stage.h` has no "load stage" function at all (it has `Stage_GetStageFiles` and `Stage_GetStageFile`, which read).
- What *does* exist and could be mistaken for it, VERIFIED:
  1. **Pokemon Stadium's own transformations** (vanilla, `gr/grpstadium.c`): the merged collision table is loaded once; each form
     toggles joint groups and loads a visual `GrPs*.dat` into a spare archive slot (`seamless-stage-switch` s2). m-ex's preload header
     even reserves file-entry numbers above 2000 for "pokemon stadium transformation" (`m-ex:MexTK/include/preload.h:121`). Same
     stage, same row.
  2. **Alternate layouts / "alternate stages"**. The one widely used mod in this class is *Dynamic Alternate Stages* (ssbmtextures.com,
     listing "requires m-ex, console and Slippi Online safe"): extra stage files are dropped next to the original and one is picked when
     the stage loads, with a held button (`(L)` in the file name, buttons LRZBXY) or at random. That is a **file chosen before the match**,
     not a change during it. VERIFIED from the listing text only; the page was unreachable on a direct fetch (HTTP 410), author and licence
     were not read, so I give no author for it here. Our own mod-packaging doc calls such things content variants (`docs/mods-packaging.md`).
  3. m-ex's **SSS pages** and **alternate stage name** are stage-select UI only.
  4. Training Mode (TM-CE, UnclePunch) edits a loaded stage per event, e.g. removing Randall and Shy Guys on Yoshi's Story with
     `Stage_DestroyMapGObj` and `GObj_RemoveProc` (`tm:patch/tmdata/source/events.c:2405-2418`, VERIFIED). That is a one-time edit for a
     drill, not a stage change.
- Verdict: **does not exist.** "Partial" would be wrong: nothing in m-ex advances toward it.

## C. Data-described stage behaviour in m-ex: does not exist

- VERIFIED: a `grFunction` is only code. What a mod author writes today to make something move or fire: C compiled with MexTK
  (`MexTK.exe` plus `ELFToDAT.exe`, `m-ex:MexTK/`) against `stage.h`, producing PowerPC stored in the stage DAT and called through the
  row words above.
- What is data is the game's own stage format, which m-ex did not touch: `map_head` (general points, splines, lights, map-GObj
  descriptors, `coll_links` that bind collision groups to joints, `anim_behave`; `stage.h:466-506`), joint animation, `yakumono_param`,
  `grGroundParam`, `coll_data`. That makes a *moving platform's path* data (joint animation, collision follows the joint via
  `coll_links`), but starting, stopping, timing it, and any hazard, wind or transformation are code: `onFrame` of a `MapDesc`, calling
  `Stage_MapStateChange`, `Stage_EnableLineGroup`, `Stage_InitDamageHazard` and the like. INFERRED from the header surface and
  from vanilla stage source patterns (`seamless-stage-switch` s2); I did not disassemble an m-ex stage blob today (we did for GrOMc
  in `mex-stages.md` s8: 488 bytes of code, calls `Ground_InitMapColl`, `Ground_UpdateMapColl`, `grAnime_*`).
- No scripting, no declarative event table, no stage JSON, no timeline. Searched `asm/` and `MexTK/include/` for variant, alternate,
  transform, morph, schedule: only the hits listed in B.

## D. A Geno stage layer

Rules it must keep (`melee/docs/geno.md` s1-4, s19.13): opt-in per piece of content (a `*.json` in a mounting mod); never edit the m-ex
tables or numbering (s2, s3.4); all mutable state is game state, inside the snapshot, no pointers in it, no host time or randomness
(s4); registries built at install time, fixed during a match; identity of changed content mixed into netplay identity (s3.5). Geno's
fighters and standalone items already work this way, and standalone items already do stage-kind range checks against the m-ex item table
(s19.13: refuses overlap).

**What it would add that m-ex does not**
1. **Declarative stage behaviour**: platform paths, timed toggles of line groups, on/off hazards and wind zones, as rows in a JSON,
   executed by native code. m-ex's only route is PowerPC.
2. **Live stage change**: a queue of switch rules plus the transition, with a defined handoff of fighters, items, camera, blast
   zones and music. m-ex has nothing here. The prior note found the design (A dressed swap, then C pre-loaded merged collision, B full
   re-init is XL).
3. **Rules that apply to a stage without touching its code**: a Geno description attached to a vanilla or m-ex stage by file name,
   exactly as a fighter overlay attaches by `Pl*.dat` name (s3.4).
4. **Deterministic, rollback-safe stage state**: today stage hazards live in the stage's own GObjs. A Geno state block gives a place for
   "which layout is active, frame of the next switch", which the snapshot already covers.

**What it should NOT duplicate** (m-ex already covers it, our port already supports it)
- Stage slots in the roster, external/internal ids, stage-select entries and icons, stage files, names, SFX banks, playlists, line types,
  stage item lists. Geno should *reference* a stage by its file name / content identity and let m-ex's layer own the slot. Same
  discipline as fighters.
- A second DAT loader: use the existing script-DAT path (`gd.stage_add_model` loads any root-level disc DAT; seamless note s0) or the
  m-ex file path.
- The 13-word row model and the `map_gobjs` callbacks. Geno behaviours should be new native callbacks that sit *beside* a stage's row, not
  replace its words.

**Where the two must interoperate** (VERIFIED facts, INFERRED consequences)
- *Switching to an m-ex stage with `grFunction` code*: the blob is relocated inside the stage's archive at load by
  `Mex_GrFunctionInit` and exactly one stage can be "current" (`gw_Mex_GrSelect`/`gr_loaded`, `gw_mex_grfunction.c:340-366`: a different
  kind drops the old code range, releases its thunks and stage items). So the destination must go through the same init, with the
  previous one torn down first; two m-ex stage blobs live at once is not supported by `Mex_GrSelect`. For design C (preloaded
  destinations) the blob must be relocated at preload, which today is not separable from "make it current".
- *Switching from an m-ex stage*: its map GObjs have `onDeletion` (`MapDesc`), so `Stage_DestroyMapGObj` has a clean per-object
  teardown hook (VERIFIED existence of the field; INFERRED that destroy invokes it, TM-CE relies on destroy working). The row level has
  **no** unload callback, only `Remove` for moving collision points (`Stages_MovingCollisionPointsRemove.asm`, 0x801C3154).
  Our own teardown is `gr_unload()`, which is port code, not an m-ex feature.
- *Geno rules for an m-ex stage with no code change*: key the description by the stage's file name; Geno toggles line groups and
  joint animations from outside through the same engine helpers m-ex's own header lists. It must not write the stage's row words.
- *Netplay*: m-ex stages are matched by content identity (`gw_mexid.c`); a Geno stage description changes how a stage plays, so it
  must be mixed into that stage's identity only when present, as fighters do (s3.5).

## E. Design consequences for us

1. Say "m-ex adds stages; Geno changes them" and keep that line. m-ex is the catalogue and loader; Geno would be the behaviour and
   switching layer, opt-in per mod, never editing the m-ex layer.
2. Start with description-by-reference: a stage-layer JSON keyed by stage file name that attaches to vanilla stages and to m-ex
   stages alike; no stage-slot allocation in Geno.
3. Make the first Geno stage primitive the one m-ex already exposes as engine calls: **line-group enable/disable, joint animation
   state, a timed on/off table**. That covers moving platforms and toggled hazards with no PowerPC, and it is the same mechanism the
   switching study found underlies Stadium, Big Blue and the other precedents (merge once, toggle groups).
4. Build switching as design C-shaped from the start (one merged collision table, visuals preloaded, destination params applied,
   a single atomic `stage_switch` event), so the later native, frame-triggered, rollback-safe form is the same code; scripted
   Lua writes stay offline/LAB (every `gd.stage_*` write is refused online today).
5. Teardown/init for a mid-match stage is *our* work, not m-ex's: expect to write a stage-level `unload` (destroy `HSD_GOBJ_CLASS_STAGE`
   GObjs, clear joint list, release `gr_unload`), because retail resets by zeroing (`Ground_801BFFB0`) and `mpLibLoad` leaks per call
   (seamless note s1). m-ex helps only at the object level (`onDeletion`) and at the blob level (`gr_unload` is already port code).
6. Constrain the m-ex case explicitly: at most one m-ex-code stage current at a time; a switch to or from one runs the full
   `Mex_GrSelect` / `Mex_GrFunctionInit` / `gr_unload` path behind the transition. A stage whose `grFunction` code never runs again after unload
   is fine; its stage items and thunks are released by that path.
7. Treat "what holds stage state" as part of the contract. Slippi had to record Stadium's transformation ids in replays
   (`project-slippi/slippi-ssbm-asm` `Recording/Stages/SendStadiumInfo.asm`) and offers a Frozen Stadium that removes the behaviour
   (`list_console_stages_stadium.json`, "Disables Pokemon Stadium transformations"). A Geno stage layer should put its schedule
   (current layout, next switch frame, rng draws) in the snapshot-covered state block from day one.
8. Define the fighter handoff rules before any visuals: Ultimate's Stage Morph kills fighters outside the new blast zone and freezes
   both stages during the morph (SmashWiki "Stage Morph", already cited in the seamless note); the prior probe showed a fighter outside
   the new floor falls. Pick the rule, make it a field of the switch rule.

## F. Adjacent work (one paragraph each, facts only)

- **Vanilla Pokemon Stadium**: transformations are the stage's own code, driven by a timer and archive loads into a spare slot, one
  collision table loaded once (our `seamless-stage-switch` s2, `grpstadium.c`). SmashWiki "Stage transformation".
- **Slippi / Ishiiruka**: Frozen Stadium (an injection list that disables the transformations, `Data/Sys/Slippi/InjectionLists/
  list_console_stages_stadium.json`, Ishiiruka) and stage-state recording for replays (`slippi-ssbm-asm` `SendStadiumInfo.asm`, wiki
  `SPEC.md` event 0x41 "Stadium Transformations", since 3.18.0). A third-party analysis (briandle00, `kyhavlov/melee-sim-light` PRs #37,
  #61) reports that unfrozen transformations are reproducible only under the "preload" or Slippi 3.18+ timing, which shows the state
  that must be pinned. This is the closest community example of "what holds stage state".
- **20XX / UnclePunch Training Mode**: Training Mode CE builds on m-ex headers (it vendors `MexTK/include/stage.h`) and edits stages per
  event (the Randall and Shy Guy removal above); no stage switching found in the tree (`grep` of `tm/` for `grFunction`,
  `Stage_MapStateChange`, `Stage_EnableLineGroup` finds only a stage header, `Get grFunction.asm` and `events.c`).
- **Dynamic Alternate Stages** (ssbmtextures.com, m-ex based): file-swap variants chosen at load (B.2). Author and licence not read.
- **Akaneia build**: adds 25 stages as rows, files and PowerPC (`mex-stages.md`). I found no stage-morph or data-driven stage
  feature in its stage set or in `asm/`.
- **Project M / Project+ / Brawl**: no comparable in-match "stage morph" mod found by search (results were Ultimate's Stage Morph
  and Project M's mid-game *character* switching in All-Star, which is not stages). Not verified further.
- **Smash Ultimate Stage Morph**: both stages are loaded at once and one runs hidden; terrain rises through the sinking terrain;
  fighters outside the new blast zone are KO'd (SmashWiki, CC BY-SA 4.0).

## Credits

| work | author / owner | link | licence |
|---|---|---|---|
| m-ex framework, headers (`stage.h`, `mxdt.h`), `grFunction.txt`, asm hooks | UnclePunch and contributors (Ploaj, sadkellz, Savestate2A03, Super4ng, rapito, Janthor, per GitHub contributors); repo owner org `akaneia` | https://github.com/akaneia/m-ex | none published; consulted only, nothing copied |
| mexTool (installer / manager) | akaneia | https://github.com/akaneia/mexTool | none published; not read beyond its description |
| Training Mode / TM-CE | UnclePunch | https://github.com/UnclePunch/Training-Mode | none published (GitHub reports none); read `events.c` lines cited |
| Slippi Ishiiruka injection lists | Project Slippi | https://github.com/project-slippi/Ishiiruka | GPL-2.0 per the repo family; only a listing name read |
| Slippi `slippi-ssbm-asm`, `slippi-wiki` | Project Slippi | https://github.com/project-slippi/slippi-ssbm-asm, https://github.com/project-slippi/slippi-wiki | GPL-3.0 (`slippi-ssbm-asm`, per GitHub API); wiki licence not read |
| Unfrozen Stadium / Slippi patch-set analysis | briandle00 | https://github.com/kyhavlov/melee-sim-light/pull/37 , /pull/61 | repo licence not checked |
| Dynamic Alternate Stages | author not read | https://ssbmtextures.com/stages/other/dynamic-alternate-stages-v1-0/ | not read |
| Stage Morph, Stage transformation | SmashWiki contributors | https://www.ssbwiki.com/Stage_Morph , https://www.ssbwiki.com/Stage_transformation | CC BY-SA 4.0 (Stage Morph; the other page not checked) |

`CREDITS.md` has no m-ex entry; `DEPENDENCIES.md:58-69` is where m-ex is credited today ("consulted, not redistributed").

## What I could not verify

- Whether an m-ex stage's `onDeletion` runs when `Stage_DestroyMapGObj` is called (field exists; behaviour inferred).
- Whether `Mex_GrSelect` can hold a second stage's blob relocated but not current (code read says no; not tested).
- The `moving_coll_count` / `moving_coll` versus `joints` / `joint_count` word order (above).
- Our SSS widening status for 163 ACE icons: the older note listed it as work; I did not re-check the code today.
- The authors, licence and mechanism details of Dynamic Alternate Stages beyond the listing text; any Project M / Project+ stage-morph project.
- Anything about Akaneia's stage logic beyond `mex-stages.md` (no disassembly today); the Slippi licence of Ishiiruka's injection list and of the wiki.
- That nothing exists in private or closed-source m-ex forks (this is the public `akaneia/m-ex` master only).
