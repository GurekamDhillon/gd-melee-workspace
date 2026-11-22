# Codex packet EC: Supertime Envoy on top of Classic and Adventure (2026-10-03)

Workspace `<workspace>` (the folder this file is in is `<workspace>/docs/prompts`); game checkout `melee/` (read
`CLAUDE.md`, `melee/CLAUDE.md`, `melee/pc/platform/CLAUDE.md`, `melee/src/melee/gm/CLAUDE.md`, `docs/scripting.md`,
`docs/superpowers/specs/2026-10-03-supertime-envoy-design.md`, `_build/tmp/codex-envoy-slices-2-4-report.md`,
`_build/tmp/codex-envoy-replace-reach-report.md`). Both trees are deliberately dirty: do NOT commit, reset, stash, revert
or reformat. Do NOT run `tools/port/build.sh`, do NOT launch the game. Keep every file compilable at every save.
Another job is editing engine C right now: do the research and design first, and make NO C edits until
`_build/tmp/codex-no-hitch-engine-last.txt` exists; then re-read the files you touch. Do not stop to ask for design
approval: the integrator has approved this packet; record your choices in the report.

## The owner's new direction (verbatim)
"you know what, maybe we're over doing it with all this maze junk anyways. If we just play out a classic/adventure mode
setting, with a drive choice/reward at the end, and any CPU fighters get randomized drive stats normalized around ours,
and letting the game run after the end of masterhand, looping/starting a new game+ dealio with the same stats carrying on"

So the run is no longer our own generated levels. The run IS the game's own Classic mode (and Adventure mode), played
as shipped, with the Envoy layer on top. Maze and mission-level work is parked (kept, not deleted, not extended).

## The design to build
1. **A run = one playthrough of Classic (first) or Adventure (second)**, started from the Envoy hub/menu with the
   companion's stats (Power, Speed, Guard, Jump) applied to the player's fighter exactly as today. The retail mode's own
   stage order, opponents, bonus stages, intermissions and Master Hand are untouched: it must look and feel vanilla.
2. **A drive choice as the reward at the end of each cleared stage** (the integrator's reading of "at the end": per
   stage, with a bigger reward after the final boss; put the cadence in the tuning table so it can become end-of-run
   only): a small Envoy panel over or after the retail stage-clear flow offers a choice (suggest three options: drives
   of different colours and sizes, occasionally a rare white drive or a grade raise), the pick is applied to the
   companion at once and shown as before/after. Controller-only, built from existing kit components, no new art.
   Whether enemies still physically drop drive items during stages is a tuning switch, default OFF in Classic (retail
   feel), so progression comes from the choice.
3. **CPU opponents get randomized drive stats normalized around the player's**: for each CPU fighter in a stage (single
   opponents, teams, the giant, the metal fighter, the fighting wire frames, and the bosses where modifiers apply),
   roll a stat spread whose total budget is centred on the player's current total (a seeded roll per run and stage so a
   retry is the same; spread width, floor and ceiling in the tuning table; multi-opponent stages split or scale the
   budget so a team is not a wall), apply it through the same engine modifiers the player uses, and show the opponent's
   leaning stat in a small tag at stage start so the player can read it. Retail handicaps (giant, metal, team size) stay
   and stack with it sensibly; state the rule. Never touch retail AI level logic except through a documented switch.
4. **After Master Hand, the game keeps going: New Game+.** Instead of ending at credits and the title, the run loops into
   a new playthrough with the same companion, stats and age carrying on, a loop counter (NG+1, NG+2, ...), and the
   opponents' stat budget scaling with the loop so it stays a contest. Decide and state what happens to: the retail
   credits/trophy/congratulations flow (skippable, shown once per loop, or skipped: prefer keeping the trophy and a
   short congratulations then straight on), retail difficulty and stock settings (carried), continues and game over
   (a game over ends the Envoy run and settles it: aging, records), Crazy Hand conditions, saving retail records
   (do not corrupt or inflate the memory card's own Classic records: say what is written).
5. Keep from the existing Envoy mod: the companion, DNA, grades, evolution at a win (now at each Master Hand), aging per
   run, reincarnation, the hub and its stations, saves and migration, the tuning table, the HUD stat bars, the drive
   models as reward icons. Drop from the default flow (keep the code): generated rooms, mission campaigns, wave enemies.
6. Vanilla disc, one folder, as always; everything offline; nothing here runs in netplay.

## Engine work (find it properly in the decomp first)
Research and write down, with file:line: how Classic and Adventure are structured in this codebase (the 1P scene
majors/minors under `melee/src/melee/gm/` e.g. the regular-1P and adventure flows, their per-stage tables, how the next
stage is chosen, the stage-clear / intermission / continue / game-over / credits / congratulations minors, where Master
Hand's defeat is detected, how opponents are spawned and with which handicaps, how the match settings are built per
stage); which of the script layer's hooks and gameplay calls already work in those modes (the LAB events are armed only
in the LAB today: what is mode-gated, e.g. `gd.fighter_mod`, `on_match_start`, overlays, input capture for a menu while
the retail scene is between matches) and what must be opened up, safely and offline-only.
Then add the minimum general capabilities, each documented in `docs/scripting.md`, tested in the suite pattern, with a
catalogue demo where it is a new capability (project rule: one single-feature demo per capability):
- 1P mode awareness for scripts: `gd.mode_1p()` -> which mode, stage index, stage kind, opponents, loop; hooks
  `on_1p_stage_start`, `on_1p_stage_clear`, `on_1p_game_over`, `on_1p_boss_defeated`, `on_1p_complete`.
- A way for a script to HOLD the retail flow at a safe point between stages (after stage clear, before the next
  stage loads) while it shows a panel and takes input, then release it; with a timeout so a broken script can never
  strand the game.
- Fighter modifiers and tints applied to 1P opponents at spawn, per entity (teams, wire frames), cleared when the mode
  ends.
- A way to start Classic/Adventure from a script or the scene string with a chosen fighter, difficulty and stocks
  (the port's scene launch already exists: extend it), and to continue into a new playthrough on completion instead
  of returning to the title (the New Game+ loop), with a documented switch.
Report anything that cannot be done without changing how retail behaves, rather than doing it quietly.

## Lua work (the Envoy mod)
A new default run type `classic` (and `adventure`) built on those hooks, the reward panel, the opponent stat roll, the
NG+ loop, settlement on game over, the hub entry points; all rules in the tuning table; guarded for missing engine calls
so the mod still loads on an older build (it then says the mode is unavailable). Offline tests with a stubbed 1P flow:
a full Classic run to Master Hand, an NG+ loop twice, a game over mid-run, the opponent roll's determinism and its
normalisation (mean total within a stated tolerance of the player's over 1,000 rolls), no stat or tint left on anyone
after the mode ends. Update `MENUS.md`, `PLAYTEST.md`, `NATIVE-TEST-PLAN.md`; regenerate the bundle last.

Report `_build/tmp/codex-envoy-classic-report.md`: the retail flow map with file:line, each new call and hook, the rules
you chose and why (reward cadence, opponent budget, NG+ scaling, credits handling, records), what the integrator must
build and what a tester should play (a Classic run on Normal with Mario: stage 1 opponent tag, reward panel after each
stage, Master Hand, the loop), and what only the owner can judge.
