# Chao genetics as a base for the Envoy gene system (2026-10-03)

Research note for `docs/PLAN-ENVOY-EDITOR-MISSIONS-2026-10-03.md` section 10. Read-only research: nothing was
built, edited or copied from the WSL folder. Quotes are limited to a few lines.

Paths: `MT/` = `/home/gd/projects/rust-port-testing/modding-tools/` (WSL). Line numbers are for the files as cloned there
(shallow clones).

Tags: **CONFIRMED** = read in code or a data structure. **DOCUMENTED** = a doc or community claim, not checked against code.
**UNCERTAIN** = not recoverable from these repos (the logic or constants sit in the retail binary), or only inferred.

## 0. What the sources do and do not contain

- `SA2B` (GameCube decomp, CC0) has only two Chao C files: `MT/SA2B/src/chao/al_gene.c` (729 lines) and `al_face.c`. The gene code
  (creation, blending, expression, grade growth, reincarnation) is all there. Stat growth (`AL_ParameterGrow`, listed in
  `MT/SA2B/config/GSNE8P/ChaoMain/symbols.txt:585`, size 0x1D4), fruit, animals, drives, evolution and mating are **not** decompiled.
- `sa2dc` (Dreamcast SA2 matching decomp, no licence) has much more C: `src/Chao/al_gene.c`, `al_parameter.c`, `al_behavior/albhv_life.c`
  (evolution, reincarnation), `albhv_nest.c` (mating). It is the **Dreamcast** game. It matches the GC/PC logic where both exist, but
  its stat model is older (see section 1.8).
- `CWE` (Chao World Extended, no licence) hooks the PC game, so it shows what it changes. The unchanged logic is called through
  fixed addresses, not reproduced.
- The numeric tuning (`ChaoGlobal`: boundaries, growth rates, limits) is data inside the user's own `ChaoMain.prs`. The struct is in
  `MT/SA2B/include/samt/sonic/chao/al_global.h`; the values are not in any repo.
- The owner's own project (`/home/gd/projects/rust-port-testing/{docs,crates}`) has no Chao code or docs. Its `crates/formats` has PRS and
  GVM/GVR readers (`prs.rs`, `gvm.rs`, `gvr.rs`, `docs/gvm-gvr.md`), which matter for content (section 3).

## 1. The real Chao mechanics

### 1.1 What a Chao carries

The save record is `CHAO_PARAM_GC`, `MT/SA2B/include/samt/sonic/chao/al_chao_info.h:259-308` (CONFIRMED). Fields that matter:

| Field | Meaning | Source |
|---|---|---|
| `Abl[8]` | stat **grade** E..S, values 0..5 (`AL_MAX_SKILL 5`) | al_chao_info.h:10, 278 |
| `Lev[8]` | stat **level** 0..99 | :279 |
| `Skill[8]` | stat **points** (u16; docs say 0..9999) | :280; `MT/ChaoModding_Docs/docs/ChaoDataStruct.md` |
| `Exp[8]` | progress to next level, 0..100 | :277 |
| stats | order: Swim, Fly, Run, Power, Stamina, Guts(Luck), Intellect, and an unused eighth | :67-75 |
| `type` | Child, adult by (alignment x stat type), Chaos, character Chao | :31-62 |
| `like` | happiness toward the player, -100..100 | :287; sa2dc `al_parameter.c:378-383` |
| `age`, `old`, `life`, `LifeMax`, `nbSucceed` | clock rollovers, adult rollovers, life counter, life ceiling, reincarnation count | :289-293 |
| `body.HPos/VPos/APos/growth` | Run-Power axis, Swim-Fly axis, Dark-Hero axis, growth ("magnitude") | :91-97 |
| `body.ColorNum/NonTex/JewelNum/MultiNum/EggColor` | colour, monotone, jewel/texture, shiny | :109-113 |
| `emotion.Personality[13]` | -128..127 traits (Curiosity, Kindness, Aggressive, Sleepy, Solitude, Vitality, Glutton, Regain, Skillful, Charm, Chatty, Calm, Fickle) | :164, :15-28 |
| `emotion.Taste/Tv/Music` | favourite fruit, TV and music kind | :165-167 |
| `race`, `karate` | race records, karate rank and wins | :130-147 |
| `gene` | the DNA struct below | :302 |

The PC/Windows names for the same fields are in `MT/sa2-mod-loader/SA2ModLoader/include/SA2Structs.h:964-1100` (`ChaoDNA`,
`ChaoDataBase`: `StatGrades[8]`, `StatLevels[8]`, `StatPoints[8]`, `PowerRun`, `FlySwim`, `Alignment`, `EvolutionProgress`,
`Reincarnations`). CWE's documentation table matches (`ChaoDataStruct.md`: "Alignment: -1 for Dark, 0 for Normal, 1 for Hero").

### 1.2 The DNA (`AL_GENE`)

`al_chao_info.h:214-245` (CONFIRMED). Every trait is an **array of two alleles**, one from each parent:

- `Abl[8][2]` grade alleles (u8, 0..5), `LifeTime[2]` (0..9), `HPos/VPos/APos[2]` (signed, 0 by default; Hero eggs set APos to +5, Dark to -5:
  `al_gene.c:294-302`), `Personality[13][2]`, `Taste/Tv/Music[2]`, `Color[2]`, `NonTex[2]` (monotone), `Jewel[2]` (texture), `Multi[2]` (shiny),
  `EggColor`, and parent IDs and names (mother, father and the two grandparent pairs: `:219-226`).
- CWE replaces the unused `EyePos` with a `Negative[2]` allele (inverted palette): `MT/CWE/CWE/SA2Structs.h:751`.

Fresh (non-bred) DNA (`AL_GeneCreate`, `al_gene.c:92-164`, CONFIRMED): one third of the time the grade alleles are a shuffle of 0..4;
one third each stat is 1..3; one third 14 points are spread randomly with a cap of 5 per stat. Personality alleles are 0..4
(trait = (allele-2)x40, so -80..+80: `al_gene.c:147-148, 358, 531`). Taste/TV/music are 0..5. Colour, monotone, jewel and shiny start at 0 (normal).
There is a source bug: the shuffle array has 5 entries but is read for 8 stats (`al_gene.c:108`, comment "@BUG").

### 1.3 How DNA turns into a body (dominance)

`AL_GeneAnalyzeCommon` (`al_gene.c:481-711`, CONFIRMED), run once when an egg hatches:

- **Grade**: take the higher allele with 70% probability, the lower with 30% (`:499-515`). So a high allele is favoured but not dominant.
- **Colour**: if both alleles are non-normal, pick one at random; if only one is non-normal it is used. Colour-vs-normal: coloured always shows (`:676-686`).
- **Jewel texture**: same rule as colour (`:688-698`).
- **Monotone**: pick one allele at random, so a carrier shows it 50% of the time (`:700-704`).
- **Shiny**: shown if **either** allele is set (dominant) (`:706-710`).
- **Personality, taste, TV, music, lifetime, body offsets**: one allele at random (`:517-534`). Life ceiling = base + larger lifetime allele x multiplier (`:517-523`).
- **Face**: the three personality bands (below -45, below 45, else) pick default eyes and mouth from two 3x3x3 tables (`:35-73, 540-560`).
- **Egg colour** (an overriding value used by shop/special eggs) rewrites the colour, jewel, monotone and shiny alleles before expression (`:562-674`).

CWE additions (all gated by config switches, `MT/CWE/CWE/ChaoMain.h:33-109`): colour **mixing** when the two colour alleles differ
(lookup table `MT/CWE/CWE/data/color_mix_table.h`, `al_gene.cpp:46-77`; vanilla just picks one); "varying shades" for same-colour newborns
(`:79-139`); personality-based extra faces (`:141-201`); a 1 in 60 "lucky Chao" with a random hat or accessories (`:221-256`); medals and
normal-coloured evolved Chao can seed colour/jewel alleles into their offspring (`:314-465`; the normal-colour rule needs
`EvolutionProgress >= 0.8`, `:44-46`).

### 1.4 Breeding and inheritance

- **Egg DNA**: `AL_BlendGene` (`al_gene.c:438-467`, CONFIRMED). For **every** field, the child's allele 0 is a random allele of parent 1
  and allele 1 is a random allele of parent 2 (macro `BLEND`, "field[RAND_BOOL()]"). No mutation exists. Applied to grades, lifetime,
  alignment offsets, personality, tastes, colour, monotone, jewel and shiny alike.
- **Grade inheritance is of the stored alleles, not of the earned level.** What a parent earned only passes on because
  `AL_AblLevelUp` (`:392-401`, CONFIRMED) raises the allele equal to the current grade whenever the Chao's grade rises. This is the
  "learned becomes heritable" step.
- **Reincarnation also writes personality back into DNA** (one random allele per trait is set to trait/40+2): `AL_SucceedGeneParam`, `:337-340` (CONFIRMED).
- **Mating conditions** (sa2dc, Dreamcast code, `albhv_nest.c`, `al_intention.c:184-232`; CONFIRMED for DC, same logic expected on PC):
  adults only (Child and all three Chaos types are excluded), "breed urge" state at least 10000, the garden holds fewer than 8 Chao
  (otherwise the urge is reset to 0), both Chao go to a nest, a ~300-frame dance, then an egg is created at the nest
  (`AL_CreateChildGene`, `albhv_nest.c:279`). The urge grows with the Vitality trait (`al_parameter.c:163-167`) and is zeroed after mating (`albhv_nest.c:247`).
  There is no sex, no "like" requirement in this code, and no stat requirement.
- **Parents' own Chao is untouched**: the DC helper also writes the blend back into the second parent and sets its type to Egg
  (`sa2dc al_gene.c:100-125`). That is a different helper, used for transfers; on PC, `AL_CreateChildGene` just fills a new gene
  (`SA2B al_gene.c:469-479`, CONFIRMED).
- **Free eggs from nothing**: only shops/specials (`AL_GeneCreate`) and breeding create new DNA. The only brake on breeding in vanilla is
  time, space (8 per garden) and the urge timer. This is the exact infinite-duplication property the owner objected to in Envoy.

### 1.5 Growth: fruit, animals, drives, time

- **Fruit** carries a `ChaoItemStats` block: Mood, Belly, Swim, Fly, Run, Power, Stamina, Luck, Intelligence (all s16, `MT/CWE/CWE/SA2Structs.h:1087-1099`, CONFIRMED).
  Values are stat **points**. CWE's examples show the scale: a Hyper fruit is +160 to one stat, a generic stamina fruit +40, spoiled -30 to -50
  (`MT/CWE/CWE/register/api_fruit.cpp:7-14`). Vanilla fruit values are in the game data (UNCERTAIN). A fruit's "last bite" callback can change
  other fields (`LastBiteFruitFuncPtr`, `MT/CWE/api/cwe_api.h:19`). Shiny fruit flips shiny state (`api_fruit.cpp:49-54`).
- **Points to levels**: level = points / 100, 0..99; CWE's Health-Center upgrade does `Lev=1; Skill/=100` (`MT/CWE/CWE/alg_kinder_he.cpp:209-211`), which
  confirms the 100 ratio (CONFIRMED).
- **Grade** is a separate 0..5 value. Its exact effect on growth speed lives in `AL_ParameterGrow` (binary only). **UNCERTAIN.** The Dreamcast
  version shows the original idea: `Abl` is a remembered best value, and while the current skill is below `Abl` every gain is **doubled**
  (`sa2dc al_parameter.c:225-248`, CONFIRMED for DC). Community material says GC/PC grades scale how fast points turn into level
  (DOCUMENTED, not verifiable here).
- **Grade ups**: evolution raises the grade of the matching stat by one via `AL_GrowGeneParam` (Normal and Chaos types raise Stamina; Swim, Fly,
  Run, Power raise their own): `al_gene.c:403-436`, CONFIRMED function; the call site is in the binary (UNCERTAIN, but consistent with the
  well-known "evolving raises that stat's grade"). CWE adds paid grade-ups at the Health Center: levels must be 99, grade below A, costs
  {10000, 20000, 30000, 40000} rings for E->D, D->C, C->B, B->A, **three upgrades per Chao**, then the level restarts
  (`alg_kinder_he.cpp:103, 147-158, 176-216`, CONFIRMED). It also adds an "X grade" flag set by Hyper fruit eaten at grade S (`api_fruit.cpp:41-47`).
- **Alignment drift**: a Child gains growth each life tick and its Dark-Hero value moves toward Hero in the Hero garden and Dark in the Dark garden
  (`sa2dc al_parameter.c:60-72`; the PC game applies the same, CONFIRMED for DC). Being petted or hit also moves it (`AL_ParameterAddUserLike`, `:372-405`, depends on which character
  the player is using, CONFIRMED DC).
- **Animals** (small creatures that give parts): in vanilla they add stat points of one type and, when absorbed, give body parts (Chaos
  Chao need all parts, below). CWE's API shows the shape: a custom animal is a `CWE_MINIMAL` with a `ChaoItemStats`, a colour category
  (Swim/Fly/Run/Power/random) and parts, and each is bound to a fruit with a chance range (`MT/CWE/api/cwe_api.h:55-70, 108-110`).
  The vanilla per-animal numbers are **UNCERTAIN**.
- **Chaos Drives**: they raise a stat and spawn animals' stat gain in the stage; `al_chaosdrive.c` in sa2dc is unrecovered assembly, so the
  details are **DOCUMENTED/UNCERTAIN** (community: one drive of a colour gives about +10 points to the matching stat).
- **Time**: the adult life ceiling shrinks each clock tick by (old+100)/15 for every non-Chaos type (`sa2dc al_parameter.c:93-99`, CONFIRMED DC),
  so Chao do age; Chaos Chao do not. Illness has a 1 in 6000 chance per tick (`:116-123`).

### 1.6 Evolution (child to adult)

`DecideNextType`, `sa2dc albhv_life.c:54-114` (CONFIRMED for DC; same structure on PC):

1. Take `HPos` (Run-Power axis), `VPos` (Swim-Fly axis), `APos` (Dark-Hero).
2. If both axes are inside `+-NormalBoundary` the type is **Normal**. Otherwise the larger axis wins: `VPos > HPos` then Fly if `VPos > -HPos`
   else Run; else Power if `VPos > -HPos` else Swim.
3. **Chaos Chao** replaces Normal if every one of the 21 animal-part flags is set, `like > 80` and `nbSucceed >= 2` (`:68-83`; on the GC the
   reincarnation threshold might differ: UNCERTAIN).
4. **Alignment**: if `APos` is outside `+-NeutralBoundary`, the type shifts to Hero (+1) or Dark (+2) (`:95-105`). The values of both boundaries are binary data (UNCERTAIN).
5. After evolving, `growth`, `HPos` and `VPos` reset to 0 (`:109-111`, CONFIRMED). The alignment is kept.
6. The type rows in the enum are Normal, Swim, Fly, Run, Power, Chaos, each in Neutral/Hero/Dark (`al_chao_info.h:38-55`); `AL_IsHero/AL_IsDark` test
   `(type - base) % 3` (`sa2dc al_parameter.c:11-25`).

**Second evolution** (DOCUMENTED + partly CONFIRMED): model files are named for alignment + first type + second type (`al_dff` = Dark Fly Fly;
`MT/ChaoModding_Docs/docs/RefChaoFiles.md`), and because step 5 zeroes the axes, the adult's later drift changes the morph (CWE: `ChaoGlobal.GrowthLimit`
2.4 and `DeformLimit` 2.0 in its Monster Evolution code, `code_system/codes/code_monsterevo.cpp:6-29`, which also **caps** the axes
unless the matching stat points are at least 2000 / 3000). The exact morph rule is in the binary (UNCERTAIN).

**Character Chao** (Tails, Knuckles, Amy: types 0x17-0x19) are special-event Chao, not bred or evolved (`al_chao_info.h:56-58`; CWE adds
custom ones via `CWE_API_CHAO_DATA` with an optional evolve callback, `MT/CWE/api/cwe_api_chao.h:15-32`).

### 1.7 Reincarnation and death

- Death comes when the life counter runs out. The Chao is dead, goes into the cocoon, and **reincarnates only if**
  `like > SucceedBoundaryUserLike` **and** `stress < SucceedBoundaryStress` (`sa2dc albhv_life.c:339-350, 399-403`, CONFIRMED DC; the GC struct has two more
  boundaries, Condition and Mood, `SA2B al_global.h:59-62`, so the PC rule may be stricter: UNCERTAIN). Otherwise it is gone.
- On reincarnation (`AL_SucceedGeneParam`, `al_gene.c:326-390`, CONFIRMED): the **grade stays** (`Abl` is untouched), level resets to 1, exp to 0,
  stat points are capped at 5000 and **divided by 10** (so at most 500 points, 10% of the old total, survive), personality is written back into the DNA
  (1.4), life ceiling = base + lifetime allele x multiplier + **LifeMax/10** (a tenth of the old ceiling carries over), age resets, alignment resets
  to full Hero (+1) or Dark (-1) or 0, growth and axes reset, 30% of the animal parts are lost, `nbSucceed` is incremented by the caller. The
  DNA stays, including colour, so reincarnation is how a coloured Chao keeps its look.
- Grade is therefore the real long-term currency: it survives death, is partly written into the DNA, and is what the child can inherit.

### 1.8 Where the stats matter, briefly (DOCUMENTED, community)

Races: Swim, Fly, Run and Power set speed on the matching terrain; Stamina sets endurance; Intelligence sets how well it takes corners and uses
shortcuts; Luck affects items. Karate: all six stats feed the fight struct (`MT/CWE/CWE/alg_karate_main.h:51-60` has Swim/Fly/Run/Power/
Stamina/Luck floats, CONFIRMED), with Power as damage and Stamina as health in common knowledge (DOCUMENTED). Numbers are not in the repos.

### 1.9 SA1/SADX versus SA2

- SADX structs (`MT/DreamcastChao/.../SADXStructs.h:968-1100`) have the same DNA layout concept with only some traits (stat grade pairs
  `SwimStatGrade1/2`..., favourite fruit, colour, monotone, texture, shiny, egg colour) and `ChaoDataBase` carries `SwimGrade/Level/Stat` arrays and fractions. It shares the
  type enum and alignment fields with SA2 in the mod-loader header (`SADXEnums.h:768-795`), but how much of Hero/Dark is live in the retail SADX
  is UNCERTAIN.
- The SA2 Dreamcast build has the "child gains +4 on six stats per tick while under 150" training in `al_parameter.c:74-86`, marked "only in sa2dc" in
  the source. That is a real difference from PC/GC (CONFIRMED comment).
- SA2 has the full Dark/Hero axis, Chaos Chao conditions, animal parts, 13 personality traits and breeding with two-allele DNA. SADX has no real
  breeding genetics in the retail game (DOCUMENTED); CWESADX/CWESADX2/DreamcastChao are mods porting parts back.

### 1.10 What CWE's modding API exposes (extension points)

`MT/CWE/api/cwe_api.h` (CONFIRMED): register fruit with stats, animals (`AddChaoMinimal`) and fruit-to-animal chances, trees, accessories (4
slots per Chao), special items with conditions, custom Chao types with an evolve callback and second-evolution models, custom animations and
transitions, Black Market items and prices, extra save blocks (`RegisterSaveLoad`), transporter menu entries. The CWE parameter block adds
birthday, mother/father names, `Negative`, accessories, `XGradeValue`, `UpgradeCounter`, a `Guest` slot (`MT/CWE/CWE/al_parameter.h:23-63`).
The example repos (`CWEAPI_Example*`) are small C++ projects showing each call.

## 2. The old Envoy gene system, as built

Files: `melee/pc/scripts/examples/roguelite/` (`core.lua` 561 lines is the rules; `inventory.lua`, `equipment.lua`, `menus.lua`,
`gene_actions.lua`, `gene_behaviors.lua`, `runtime_gene_world.lua`, `codec.lua`, `checkpoint.lua`). README: `tools/roguelite/README.md`.

**Data model.** A *gene* is an individual with `kind` (family), `seed`, five stats `base={potency,capacity,gain,reach,cooldown}` and
`upgrades`, `parents={a,b}`, per-stat `locks` (`core.lua:20-22`, `limits` :5). `profile` = the collection kept between runs (`genes`, `starter`, `seed`, `world_seed`,
`next_id`, `next_run`, a `finished` ledger of up to 512 runs, `history`) (`:29-36`). `run` = a copy of the genes plus `hosts` (what is placed where), `marks`,
`runtime` (charge/cooldown per gene), `progress`, `inventory`, `equipment` (`:46-48`). Only two families were offered: Cinder Drive (fire) and Rime Guard (frost);
four more existed as data (`gene_behaviors.lua:11-22`).

**Use in a run.** A gene is **placed in one of three slots** (assault, traversal, guard); each family has a different ability per slot, triggered by
a direct hit, movement or a defend (`core.lua:7-14`). Hits charge it; when charge reaches `capacity` it can fire (a "reaction", cooldown, reach, damage) (`:210-250`).
Marks and Cinder-Rime combos give a thermal-shock bonus (`:244-250`). The same engine drives enemy-owned genes (the README says enemies use genes too).

**Obtaining.** Start: three fixed genes g1 Cinder, g2 Rime, g3 Cinder (`:21-29`). During a run: `acquire(kind)` mints a new gene (`:289-292`, capped at 128 per run), rewards
raise one stat by a delta for the run only (`:281-288`). Between runs: **breed** two same-family genes in the collection; each stat comes from one parent at
random, locked stats are forced (`offspring`, `:300-308`, `breed` :318-323). A completed run **exports** one gene back (`finish`, :381-408), without
the run's upgrades. Collection cap 128, discard rules that protect lineage (`:333-355`).

**Fusion in a run.** `fuse` consumes two same-family run genes (they must be unequipped) and makes one with inherited base and averaged upgrades (`:325-332`).

**Economy.** `inventory.lua` later added a bounded currency with a breeding cost depending on the parents (`Inventory.Economy.breed_cost`, :481). The UI
later removed breeding and locks from the collection screen (`menus.lua:365-367`: "Collection genes are kept from completed runs").

**Persisted.** The profile (all genes and ancestry, starter, counters, finished ledger, history) and the run checkpoint (genes, placements, runtime,
marks, progress, inventory, equipment), as bounded JSON through `codec.lua`, with two-slot generations (README lines 139-150).

### Where it diverges from the Chao model

| Chao | Old Envoy |
|---|---|
| Two alleles per trait, with dominance rules and expression | One value per stat, no alleles, no hidden half; "locks" were the only inheritance control |
| Offspring takes one allele from **each** parent per trait | Each stat is a coin flip between parents (same idea) but with no hidden carrier so nothing surprising can come back |
| Grade (E..S) is the long-term value; level is per-life | Stats are free numbers 1..30 with no grade, level or cap structure beyond clamps |
| Growth comes from things you give it (fruit, animals, drives) over time | Stats come from run rewards that vanish after the run, and from breeding choices |
| Type/alignment is **decided by how it was raised** at evolution | Family is fixed from birth (Cinder/Rime); nothing is decided by play |
| Breeding limited by time, urge, a garden cap of 8, and a Chao's life | Breeding was limited only by a cap of 128 and (later) a currency; free until removed |
| A Chao dies and reincarnates; grade survives, points mostly do not | Genes never die; `discard` is manual |
| A Chao is a *companion* with a body and personality | A gene is an *ability card* placed in a slot |

### Plausible reasons it was confusing

1. **Three nested layers with no named purpose**: profile collection, run copies ("independent individuals"), and run upgrades that are discarded;
   plus fusion in a run and breeding between runs. Players had to learn "this copy ends with the run, that one stays", which the UI itself had to
   explain (`menus.lua:203-205`).
2. **Abstract stats with no readable meaning**: potency, capacity, gain, reach, cooldown, and charge by trigger. A Chao's stats are Swim/Fly/Run/
   Power: each is a thing you can *see* (it races, it evolves). Charge-by-hit-type needs a tutorial.
3. **No cause-and-effect between what you do and what the gene becomes**, and **no loop around it** (the owner said they did not understand the loop; the
   problems doc says collection hints promised combat and upgrades that did not exist).
4. **Free breeding** gave unlimited duplicates and no reason to prefer one gene over another (the owner reported infinite duplication).
5. Only two families, so choice was shallow; the collection screen exposed all the machinery (locks, parents, discard rules, exports, deferred claims).

## 3. What is usable from the folder

### 3(a) Mechanics as reference (rules, tables, formulas)

Directly usable as reference, with restrictions: **consult, never copy** (project rule, `tools/mex_port/README.md:24`). Use the rules in section 1 as a
design reference and re-implement them in Lua. The best sources: `SA2B/src/chao/al_gene.c` is **CC0** (`MT/SA2B/LICENSE`), so it can be read and
adapted freely, even though the project should still re-derive instead of pasting; `sa2dc` and `CWE` carry **no licence** (all rights reserved by default).
Cost: rules are small (blend, expression, evolution fit in about 200 lines of Lua), a day or two with tests. Tuning constants (boundaries, growth rates) are
not in the repos, so Envoy picks its own.

### 3(b) Tools

- `SA2SaveUtility` (GPL-3.0, `MT/SA2SaveUtility/LICENSE`): C# editor for Chao saves (PC, GC, 360, PS3); a good way to see real values and make test Chao.
  Needs .NET on Windows. Useful for understanding, not for Envoy runtime.
- `cweedit` (no licence, Rust, egui/wgpu): accessory editor with a Chao renderer ported from the decomps; it parses chunk models and GVM/PAK textures
  (README). A **reference** for reading Chao models in Rust; the owner's `crates/formats` already has PRS and GVM/GVR readers.
- `ChaoGCtoPC` (no licence): extracts `.chao` files from GC saves; `ROFSDecode` (PS2 files).
- `SonicAdventureBlenderIO` (SAIO, GPL-3.0) and `SA3D.*` libraries (GPL-3.0): the Blender import/export of Sonic Adventure models (Ninja basic and chunk),
  animations and textures. This is the realistic bridge to Blender, and so to the Melee kit pipeline. GPL applies if code is copied into the project;
  using the tool to produce files does not.
- `StatPanelPlus`, `Sa2CustomGarden`, `DCGarden`, `DreamcastChao`, `CWEAPI_*`: examples for reading how mods hook the game; not useful for Envoy.
- `ChaoModding_Docs` (no licence stated): tables of file names (`RefChaoFiles.md`), the Chao data table, tutorials. Reference.
- `ChaoAdventure2` (GBA disassembly, no licence): assembly listing; not checked for relevance.

### 3(c) Chao content itself (models, animations, textures, sounds)

**What exists on the owner's installs** (listed by name and size only; nothing was opened or copied):

- SA2 PC: `sonic-adventure-2/resource/gd_PC/` has about 226 Chao-named or `al_*` files totalling about 14.5 MB. Key ones: `ChaoMain.prs`
  (2.5 MB), `al_body.prs` (63 KB), `al_object.prs` (106 KB), `al_parts.prs` (31 KB), `al_minimal_tex.prs` (77 KB, animals), `al_icon.prs`, `al_jewel.prs`,
  `al_eye.prs`, `al_mouth.prs`, `al_palette.plt` (4.5 KB), `ChaoMotionsD.rel` (523 KB, the animation table), `chaos0mdl.prs` (102 KB), many `al_*.GVP` palettes
  (112 B each), and 42 `chao_*.adx` music and jingle files in `ADX/`. Formats: PRS-compressed archives of Ninja Chunk models, GVM/GVR textures, GVP palettes,
  ADX audio.
- SADX: `sonic-adventure-dx/system/` has 127 `AL_*` files totalling about 13.3 MB (for example `AL_BODY.PVM`, 404 KB); `SoundData/` has `chao_g_*.adx`,
  `CHAOVOICE_BANK*.dat`, `CHAO_EFX_BANK01.dat`.

**It is copyrighted game data.** Sega's attitude to fan projects is an informal tolerance of non-commercial fan works, not a licence; that tolerance
could change, and it does not cover redistribution as such. The decision about shipping is the owner's. The owner has said shipping looks acceptable
("honestly probably fine to ship chao garden assets"); this note does not decide that.

**Conversion path (technically).**

1. Decompress PRS (the owner's `crates/formats` already does) and read the Ninja Chunk model: SA Tools/SA3D or SAIO read `.sa2mdl` chunk models and
   `.saanim`/`.rel` motions. A Chao is a 40-node hierarchy with morph "shape" data for evolution/growth (the docs say "character Chao are 40 nodes").
2. Load in Blender with SAIO (`SonicAdventureBlenderIO`), bake the Chao palettes (colour, jewel, monotone) to a texture, and pick a pose or sample
   animation frames.
3. Export through the project's own Blender exporter to `.gxmesh` (indexed GX triangle mesh, big-endian positions, UVs and indices) plus `.gxtex` (GXTX RGBA8
   atlas): the pipeline in `melee/docs/scripting.md:10-60` and `melee/pc/assets_src/bf_platform/export.py`. The runtime API is `gd.model_load`, `gd.model_spawn`, `gd.model_move`,
   `gd.model_set` with tint (`scripting.md:60-121`). Audio would need conversion from ADX (vgmstream is in the folder as `bass-vgmstream`).
4. The kit loads **static** meshes. A walking Chao would be done as many rigid parts moved from Lua (similar to the model-parts lab, `tools/model_parts/README.md`) or as
   baked frame meshes swapped per frame; skinned animation would need a new engine feature.

**How big a job.** Roughly: a static posed Chao in one colour (one mesh, one atlas, a tint for the palette): small, a few days including tooling, and tint covers many
colours. A set of body types (Child, Normal, Swim/Fly/Run/Power, each Neutral/Hero/Dark, Chaos): about 30 models with texture variants; a converter makes it
repeatable, medium. Animals, fruit, eggs, the Chaos Drive: small static models. Animated Chao: large, because of the animation side.

**Packaging options (the owner's decision).**

1. **A separate, self-contained Chao asset mod folder**, built by a converter from the user's own game files and distributed apart from the main repositories.
   This fits the project's one-folder-per-mod rule and keeps the main repos clean; it is my recommendation to the owner.
2. **Commit the converted assets into the project repos.** This needs an explicit exception to `CLAUDE.md`: "No disc-derived data is ever committed".
3. **Local-only conversion** from the user's own install, as the Ultimate fighters work today (`ports/README.md`: generated models stay local and ignored).

Option 3 is the lowest-risk default until the owner decides on 1 or 2. Original SA2 music and voices carry the same considerations; Envoy needs none of it
for its mechanics.

### 3(d) Licences of the reference repos where stated

| Repo | Licence |
|---|---|
| SA2B (GC decomp) | CC0 1.0 (`MT/SA2B/LICENSE`) |
| SonicAdventureBlenderIO, SA3D.* | GPL-3.0 |
| SA2SaveUtility | GPL-3.0 |
| SA-Mod-Manager | MIT (per `MT/INDEX.md:116`) |
| CWE, CWESADX, cwe_main, cweedit, cwesamples, sa2dc, sa1dc, SADXPC, sa_tools, mod loaders | none stated; treat as all-rights-reserved (`INDEX.md:116`) |
| ChaoModding_Docs, CWE API examples, ChaoGCtoPC, StatPanelPlus | none found in the clone |

Project rule: consult, never copy, for unlicensed code (as with m-ex).

## 4. Proposal: a small Chao-style gene system for a roguelike Melee run

Principle: keep the **parts of Chao that make a player care and are easy to state**, and drop the rest. The parts worth keeping: two-allele
DNA with a hidden half (a surprise from breeding), grades E..S as the long-term goal, what you feed it changes it, evolution that is decided by how it was
raised, and a cost to making a new one (a Chao's time and life). Drop: 13 personality traits, moods, illness, garden care, races, hats.

Rule of the plan: add this only after the basic run (levels, rewards, boss) is fun. Everything below is built on top of that.

### Shape A (recommended): "Companion gene": a creature you raise that changes your fighter

- **What it is**: a **Chao-like companion** (call it a Gene for continuity). It has 4 stats (**Power, Speed, Guard, Reach**: one per readable thing it does for the
  fighter), each with a **grade E..S** and a run-level 0..9. It has a **type** (one of four, like Swim/Fly/Run/Power) that decides a **named passive** for the
  fighter (Power: harder hits; Speed: faster dash; Guard: shield/damage reduction; Reach: knockback range, for example) and a colour from DNA.
- **What it does in a run**: you bring **one** companion. Its type gives a fixed passive; its stat levels set how strong it is. It is the *only* gene system the
  player must understand.
- **Getting them**: *level pickups* replace animals/fruit: a fruit-like pickup gives +points to one stat (by colour); a rare "drive" pickup raises one grade
  for this life. Bosses drop an **egg**.
- **Evolution at a milestone**: when the run's first boss falls the companion evolves. Its type is **chosen by which stat got the most points this life**
  (the Chao rule: biggest axis wins; if none stands out, Normal). Alignment becomes "style": taken from play (aggressive kills versus no-damage rooms) -> Hero-like or
  Dark-like variant of the passive (the Chao alignment rule).
- **Between runs**: the companion **does not die at the end of a run**; it gets *old*: each run costs one life tick. When it is out of ticks (about 6 runs) it
  **reincarnates**: level and points reset to 10%, **grade stays**, colour stays, and it asks to be paired (see below). That is exactly the Chao loop: raise,
  evolve, age, reincarnate, with grade as the carry-over.
- **Breeding** (between runs only, in one small screen): pick two companions, get **one egg**. For each trait the egg takes one random allele from each parent (the
  real `BLEND` rule); expression uses the real dominance (grade: higher allele 70%; colour: coloured beats normal; shiny: either parent's allele). **Costs and
  caps** (below) prevent duplicating.
- **No infinite duplication**: (1) a **nest cap of 4**, (2) an egg needs **both parents to be "ready"**; a parent is ready only after one **completed run** since its last
  mating (the Chao breed urge), and mating **ages it by a life tick** (new rule; the real game's cost is time), (3) an egg can only be made from **two companions that
  exist**, and the parents are not copied (the real game keeps them; we say each mating **uses up one of the parent's remaining lives**), (4) every action is a
  single transaction, saved before the screen updates (the old system's lesson).
- **Long-term goals**: get an S grade in a stat (grades rise through inheritance of earned grade alleles: a grade-up writes into the allele, as in `AL_AblLevelUp`); a
  shiny; a rare colour by breeding two colours; a "Chaos" form (all four stats at least B and X pickups collected over several lives, the Chao rule).
- **Persists between runs**: the companions (DNA, grades, colour, type, lives left, name). **Within one run only**: stat points, run level, the pickups.
- **Minimum first version**: one companion, 4 stats with levels only (no grades), fruit pickups, type chosen at the first boss, a fixed passive per type.
  No breeding, no reincarnation yet. Second step: grades and lives. Third: eggs and breeding.
- **Keeps from Chao**: type from raised stats; grade as a long-term value; the evolution rule; reincarnation keeping grade and colour; two-allele DNA with the exact blend and
  dominance; the aging cost. **Simplifies**: 4 stats, no personality or mood, one nest, fixed lives.

### Shape B: "Genes as equippable traits, bred between runs"

- Closest to what the old system tried. A gene is a **trait card** with two alleles of a trait family (for example Fire/Frost); equip 3 in slots. Breed two
  cards into one with the real blend rule; expression decides the effect shown.
- Pros: reuses the old slot/ability code, so the least engine work. Cons: it is the same abstraction the owner found confusing (cards and slots), a trait card
  has no life or personality so there is nothing to care about, and breeding is easy to farm without a time cost. It keeps: DNA blend and dominance. It drops: growth,
  evolution, reincarnation, grades as a journey.
- Keep only if Shape A proves too heavy to build.

### Shape C: "The fighter itself has DNA"

- Your fighter gets a DNA record (allele pairs for **stat bias, colour, passive**), and the *run* is the garden: levels give "fruit", and at the end of a run the
  fighter "reincarnates" into the next run with grade carried. No separate creature.
- Pros: nothing new to explain; no breeding screen. Cons: **no breeding at all** (single lineage) unless you add co-op or sharing; no visual companion;
  inheritance has no second parent so most of what makes Chao genetics interesting disappears. It keeps: grades, reincarnation and carry-over. It drops: two parents.

### Recommendation

Shape A, built in the three steps above, and shipped only after the run itself is fun. Why: it is the only one where each real rule has a visible reason (a
creature on screen whose type you chose by what you fed it), the **loop is named and short** (collect, evolve at the boss, age, reincarnate, breed), and the
economy brake is natural (lives and readiness) instead of a currency. Step 1 is already a complete feature; steps 2 and 3 add depth without changing what step 1 means.
Visual Chao models are optional: step 1 can use a tinted placeholder shape, and the Chao assets of section 3(c) only matter if the owner wants the real look.

### Questions only the owner can answer

1. Should the companion be a **visible Chao-like creature** (needing models; see 3(c)) or an **icon with a passive**?
2. Is shipping converted Chao Garden assets wanted (packaging option 1, 2 or 3), or should Envoy use original art (a Melee-style creature)?
3. How much **loss** is acceptable: do companions age out and reincarnate (a Chao-like loss), or should they be permanent?
4. Is breeding a **core pillar** or an optional late feature?
5. Is it one companion at a time, or a small team (2-3) as in the old three slots?
6. Should **alignment** (Hero/Dark style from play) exist in Envoy at all, or only the stat type?
7. Is **co-op or online sharing** of eggs a goal (Chao have no sex, so any two can mate)?
8. Are shiny/colour rarities something to chase, or just cosmetics?
9. How long should a companion live in runs (about 6 is my guess)?
10. Does the existing roster of fighters change what a companion can do (passives per fighter)?
