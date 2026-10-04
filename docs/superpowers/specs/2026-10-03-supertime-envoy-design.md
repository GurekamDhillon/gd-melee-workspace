# Supertime Envoy: design (2026-10-03)

Status: draft for GD's review. Nothing in this document is built. It replaces the old Envoy
(`docs/ENVOY-PROBLEMS-2026-10-02.md` is the record of why) and follows section 11 of
`docs/PLAN-ENVOY-EDITOR-MISSIONS-2026-10-03.md`. It depends on the mission-folder pipeline in
`2026-10-03-mission-folders-and-large-levels-design.md`, which is built but not yet proven in the game.

Sources, with credit: the companion and garden are modelled on Sonic Adventure's Chao Garden (Sega,
Sonic Team); the rules were read from the SA2 decompilations and Chao World Extended
(`_research/chao-genetics-for-envoy-2026-10-03.md`); benching a fighter for boss rooms is Joyastick's
MeleeVS technique (`_research/tagfighter-insights-2026-10-03.md`). No code or data is copied from any
of them. `CREDITS.md` carries the names and links.

A second design reference, noted by GD on 2026-10-03: Super Smash Bros. Ultimate's **Spirits** (Nintendo, Bandai Namco,
Sora Ltd.): an equipped companion that changes the fighter's stats, levels up by being fed, belongs to a type, and can
be enhanced into a stronger form. The companion here overlaps with that; where a rule is undecided, Spirits and the Chao
Garden are the two places to look. Ideas only.

## 1. What GD asked for

- Envoy rebuilt from scratch.
- Both maze-style generated levels and hand-built levels, authored in Blender.
- A gene system based on the Chao Garden; one companion ("sure that works").
- "A hub area with more of the garden mechanics."
- "Enemies dropping our own flavour/variation on chaos drives."
- The companion is hub-only first; following the fighter in levels is a later step.
- C-stick stays attacks. Mods work on the vanilla disc as one folder.

## 2. The game in one paragraph

You start in the hub, a small garden where your companion lives. You pick a fighter and walk through
the exit into a run: a short chain of levels, some generated mazes and some hand-built, ending in a
boss. Enemies drop drives. Each drive you pick up feeds one of your companion's stats. Beating the
boss makes the companion evolve into a type decided by what you fed it, and that type gives your
fighter a passive for later runs. Back in the hub you see the companion changed, and over many runs
you raise its grades, let it reincarnate, and breed it for better eggs.

## 3. The loop and what each part is for

| Part | What the player does | Why it exists |
|---|---|---|
| Hub | Walks around, sees the companion, picks a fighter, starts a run, later breeds | Makes progress visible; holds the garden mechanics |
| Run | Fights through 3 levels and a boss, about 10 to 15 minutes | The actual game |
| Drives | Chooses which enemies to fight and which drives to pick up | Ties fighting to raising; gives enemies a purpose |
| Evolution | Beats the boss | The reward for finishing a run |
| Aging, reincarnation, breeding | Decides between runs | The long game |

Run length (3 levels and a boss) is my choice; GD has not said. Decision 1 below.

## 4. The companion

One companion is active. It has four stats, named for what they do to your fighter:

| Stat | Drive colour | Effect on the fighter, per level |
|---|---|---|
| Power | red | damage dealt, small steps |
| Speed | green | run and air speed, small steps |
| Guard | blue | damage taken reduced, shield health |
| Reach | yellow | drive pickup radius and drop rate |

Each stat has three numbers, as in the Chao Garden:

- **Points and level.** Drives add points; 100 points is a level. Levels are what change the fighter.
  The effect per level is small and capped, so a companion helps but never replaces playing well.
- **Grade, E to S.** The grade multiplies the points a drive gives. A high grade means the stat
  grows fast.
- **Two alleles** for the grade in its DNA, one from each parent.

The real rules that make raising and breeding feed each other are kept exactly:

- A stat's grade can rise during a life (section 6), and when it does it is written into the DNA.
- When breeding, each trait takes one random allele from each parent, with no mutation.
- For grades, the higher of the two alleles shows 70% of the time.

It also carries cosmetic traits (colour, two-tone, shiny), inherited by the same rules, which is
where the rare things to chase come from.

**The companion's colours paint your fighter.** Its expressed colour traits (colour, two-tone,
shiny) and its type recolour the player's model for the run, through the engine's per-part tint
(`gd.dobj_tint`), which keeps texture and shading. Two-tone uses two body regions. Regions carry no
gameplay meaning (the old Envoy tied genes to body regions; GD, 2026-10-03: "the companion's colours
paint the fighter is also good. honestly do what you think fits"). So breeding for colour is visible
in play, and that is the whole of it for now.

In levels the companion is not present. It appears as a small panel on the HUD showing its four stat
bars filling as drives are picked up.

## 5. Drives

- Every enemy kind has a drive colour it mostly drops. The seven enemy kinds we have (goomba, koopa,
  redead, like-like, octorok, polar bear, topi) are spread across the four colours, so the route and
  the fights you choose shape the companion.
- A drive is a small pickup that drops where the enemy dies, sits for a few seconds, and is
  collected by touching it. It adds points to its stat immediately.
- A rare white drive raises one stat's grade by one step for this life.
- Drives picked up are kept even if the run fails. Losing a run costs the evolution and the boss
  reward, not what was already fed. (The old Envoy discarded run progress; this is deliberate.)

## 6. Evolution, aging and reincarnation

- **Evolution.** Beating a run's boss evolves a young companion. Its type is the stat that gained
  the most points this life: Power, Speed, Guard or Reach type, or Balanced if none leads. The type
  gives the fighter one named passive and raises that stat's grade by one.
- **Aging.** A companion ages by one for every run started. After a set number of runs (my guess is
  6) its life ends.
- **Reincarnation.** At the end of its life it returns as an egg: grades, DNA and colours stay,
  levels reset, and a tenth of its points carry over. It can then evolve again, differently.
- Hero and Dark alignment are left out. Decision 2.

## 7. The hub

A hand-built level made in Blender and loaded as a mission folder, the same as any level. It is
small and has no enemies.

- **The companion** stands in it as a visible model, tinted by its colour traits. Static at first;
  animation later.
- **Stations**, each a marked spot you walk to and press a button:
  - the exit, which starts a run;
  - fighter select;
  - the companion's stats screen;
  - later, the nest, for breeding.
- **Breeding** (last slice): two adult companions make one egg. Up to four companions are kept.
  A parent must have finished a run since it last bred, and breeding costs the parent one run of its
  remaining life. Nothing is ever copied. These three limits close the duplication hole the old
  system had.

## 8. Runs and levels

- A run is a list of levels chosen when it starts: a generated maze, a hand-built level, a second
  maze or hand-built level, then the boss room.
- Mazes are stitched from Blender-made chunks (the maze generator is its own spec).
- **Fighter enemies and the boss** are CPU fighters. The game has six player slots
  (`Gm_Player_NumMax`), and Multi-Man Melee already runs one human against five enemies that are
  recycled through slots 1 to 5 (`gm/gmmultiman.c:597-607`). So a room can hold up to five fighter
  enemies at once, and a wave can send more by reusing slots. Fighters exist from the start of the
  match and are kept frozen, invisible and intangible until needed (Joyastick's finding: creating
  one mid-match is not safe). Open: memory when the five are different characters (Multi-Man's are
  all wireframes) is unmeasured, and our scene launcher and the LAB set up four slots today, so
  six-slot matches are engine work. Item-based enemies stay as the cheap kind.
- Camera: as section 8 of the mission-folder spec.
- Runs are offline. Online play needs the run's state held natively, which is a later project.

## 9. Saving

One save file per profile in the mod's data folder: the companions (DNA, stats, age, type), which is
active, and unlock flags. Every action that changes it (a run ending, an evolution, a reincarnation,
a breeding) is written as one complete replacement of the file, so a crash can never leave half an
action saved or allow something to be claimed twice.

## 10. How it is built

Small Lua modules in one mod folder, each with one job and its own offline tests against a stub:
genetics (pure rules, no game calls), companion (stats, aging, evolution), drives (drops and
pickups), run (level list and flow), hub (stations), save, HUD. The mission runtime loads the
levels; Envoy sits on top of it and does not fork it.

## 11. Build order

Each slice ends with something GD can play.

| Slice | What you can do at the end |
|---|---|
| 1 | One run: one hand-built level and a boss, enemies drop drives, the HUD panel shows stats filling, levels change the fighter |
| 2 | The hub: walk around, see the companion, start a run, results come back to it. Evolution at the boss |
| 3 | Mazes in the run (after the maze generator) |
| 4 | Grades, aging and reincarnation |
| 5 | Eggs and breeding; rare colours |
| Later | Companion following in levels; animated companion; online |

## 12. Testing

- The rules (genetics, stats, save) are tested offline, exhaustively.
- Each slice is checked in the game by a probe using the fly commands to reach rooms and clear
  waves, on the vanilla disc, in the LAB.
- How it plays is GD's call by hand. Nothing here is reported as working until GD has played it.

## 13. Decisions for GD

1. **Run length.** Three levels and a boss, 10 to 15 minutes. Longer or shorter?
2. **Hero and Dark alignment.** Left out. Wanted?
3. **Companion lifespan.** Six runs per life.
4. **The companion's model.** A converted Chao model shipped as a separate asset mod folder, or
   original creature art. GD has said shipping Chao assets is probably fine; where they live
   (separate folder, or committed with an exception to the no-game-data rule) is still open.
5. **The four stats and what they do** (section 4). They are my proposal, not GD's words.
6. **A type triangle (from Spirits)?** Open, not planned. It only matters if the player can respond: either the
   hub offers two or three runs showing each boss's type and reward ("pick your fight", works with one companion, small),
   or the player chooses among several companions (only after breeding exists). With one companion and one fixed boss it
   would be luck. Decide after GD has played slice 1.
