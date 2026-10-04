# Codex packet E2: Supertime Envoy slices 2, 3 and 4: progression (2026-10-03)

Same rules as the earlier Envoy packets (Lua/Python/JSON/Markdown only, your mod and tests, no C, no build, no game launch,
no commits; menus are built from existing kit components with NO new art; no game-derived data in the repositories; every
engine capability you need but cannot find registered is reported as an engine request, never faked). Two jobs have just
finished in files you depend on: a crash fix in the mission runtime's staged install
(`_build/tmp/codex-envoy-play-crash-report.md`) and the drive pickup polish (`_build/tmp/codex-drive-polish-report.md`):
read both and build on that state; re-bundle last.

## Where the owner is
The owner played slice 1 on the vanilla disc: a full run was completed and won; "drives as a pick up felt nice"; and on
stats: "I didn't notice any stat changes but that makes sense ... we just need more slices I think ... for progression to
let the stat changes be expressed". So the loop is approved and the next job is progression: enough structure across runs
that raising the companion visibly changes how the fighter plays. Design: `docs/superpowers/specs/2026-10-03-supertime-envoy-design.md`
(sections 4-8 and the build order in 11; decision 6 on a type triangle stays open: do not build it). References for
undecided details, ideas only: the Chao Garden rules in `_research/chao-genetics-for-envoy-2026-10-03.md` and Super Smash
Bros. Ultimate's Spirits as noted in the spec. The data model for all of this already exists in your slice-1 code
(two alleles per trait, grades, points, levels, age, type).

## Why stats were not felt, and what to change in tuning
One run gave about 20 points per drive against 100 points per level and +0.2% per level: nothing a player can feel. Make
progression legible without making the companion a win button:
- Rework the curve so the first few levels come quickly and each early level is a perceptible step (state the numbers and
  the caps; damage modifiers also scale knockback, so keep Power's cap modest), with diminishing returns later.
- Within a run, show growth: the HUD bar fills visibly per drive, a level-up has a clear moment (the pickup effects exist
  now), and the results screen shows before/after per stat.
- Put every number in the one tuning table, with a short comment on what the player should feel at levels 1, 5, 10, 25.

## Slice 2: the hub and evolution
- The hub as a walkable level (a mission-folder level, authored as data from kit pieces like the sample levels; the Blender
  exporter and kit fill the models) with stations the player walks to and activates: start a run, fighter select, the
  companion's stats, records; the nest is present but closed until slice 5. Keep the existing menu screens as what each
  station opens. Until a companion model exists, the companion in the hub is a placeholder object tinted by its colour
  traits, with its name and type on a label.
- Evolution: beating a run's boss evolves a young companion into the type of the stat that gained most this life (Power,
  Speed, Guard, Reach, or Balanced); the type gives the fighter one named passive (define five, each simple, each built on
  engine calls that exist) and raises that stat's grade by one, written into its DNA as the spec says. An evolution moment
  on the results screen.
## Slice 3: longer runs with mazes
- A run is three levels and a boss: a generated maze from the maze generator (`mission maze <seed>`:
  `_build/tmp/codex-maze-generator-report.md`), a hand-authored level, a second maze or level, then the boss room; the seed
  is chosen at run start and saved with the run so a run can be retried. Enemy budgets and drive drops scale with depth.
- Between levels, a short interlude screen (drives gained so far, levels gained, next level's theme).
## Slice 4: grades, aging and reincarnation
- Grades multiply points gained; rare white drives raise a grade for this life; aging by one per run started; at the end of
  its life the companion reincarnates as an egg keeping grades, DNA and colours, levels reset, a tenth of points carried.
  Show age and remaining life on the companion screen; a reincarnation moment in the hub.
- Records: runs, wins, best time, companions raised, highest grade.

## Tests and deliverables
Offline tests for every rule (deterministic with the injected random source), a three-run and a full-life simulation test
asserting nothing accumulates and the save stays valid, updated `MENUS.md`, an updated `NATIVE-TEST-PLAN.md`, and a short
`PLAYTEST.md` telling the owner what to try and what each stat should feel like at each stage of a companion's life.
Report `_build/tmp/codex-envoy-slices-2-4-report.md`: what is built per slice, the tuning numbers and the reasoning, engine
requests, and what only the owner can judge. If the three slices are too much for one pass, finish 2 completely, then 3,
then 4, and say where you stopped.
