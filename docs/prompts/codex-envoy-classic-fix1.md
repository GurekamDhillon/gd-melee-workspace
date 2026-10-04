# Envoy on Classic, follow-up 1: the owner played seven stages (2026-10-04)

Same rules as packet EC (`docs/prompts/codex-envoy-classic.md`): both trees are dirty on purpose, no commits, no
`tools/port/build.sh`, no game launch, keep every file compilable; record choices in the report; do not stop for design
approval. Since your last turn the integrator added one thing in `melee/src/melee/ft/fighter.c`: the port now defaults
the C-stick to attacks in 1P modes (settings key `cstick_1p_attacks`, default 1); leave it.

The owner played a Classic run through Envoy for about 15 minutes, seven stages, on the vanilla disc
(log `_build/runs/envoy-classic-play1/melee-pc.log`). Verdict, verbatim: "It was mostly normal classic/adventure, the
menus for choosing drives was there. Reward panel was there. Nothing was particularly great." So the flow works and the
layer is not felt. No crash, no hold timeout.

1. **Stage-start hook fires on few stages.** The log has `envoy: reward choice stage=N` for N=0..6 but
   `envoy: classic stage=N NG+0` only for N=2, 5 and 7. Find why `on_1p_stage_start` (or the Lua that logs it) is missed
   on the others (stage kinds: single, team, giant, metal, bonus; a hook armed too late; a de-duplication on stage
   index), fix it, and prove with a fixture that every fight stage and every bonus stage raises exactly one start and
   one clear. Whatever hangs off the start hook (opponent stat roll, the opponent tag, modifiers) was therefore missing
   on most stages: say which.
2. **After the run ended**: `envoy: garden placeholder unavailable; prepare the room kit`. Returning to Envoy after a
   retail run must land somewhere that works with no extra assets: a results screen, then the menu; the walkable garden
   is used only when its models resolve. Never show a broken or empty hub.
3. **Make the stats felt.** At a new companion's levels the bonuses are a few percent and the opponents roll around
   zero, so the run is indistinguishable from retail. Rework the retail tuning so a pick changes the next fight in a way
   the player notices within one stage, while the caps stop it becoming a win button: state the new numbers and what the
   player should feel after 1, 3 and 7 picks. Add engine support for **jump height** in the fighter modifiers (ground
   jump, air jump; the attribute fields the jump code reads; cleared with the other modifiers) so Jump is not just air
   speed, and give Guard something visible (for example knockback resistance and a brief flash when it absorbs a hit),
   using only what the engine can really do.
4. **Make the opponents' stats visible and real**: the leaning-stat tag at every stage start (item 1), a tint or small
   marker on the opponent in its stat colour for the first seconds, and a fixture proving the rolled modifiers are
   applied to every opponent entity in single, team, giant and metal stages.
5. **Make the reward moment land**: the panel shows each option's concrete effect in plain words ("+12% run speed",
   not "+30 points"), the pick plays the existing drive pickup effects and sounds, the stat bar animates, and a level-up
   gets its moment. Controller-only, existing kit components, no new art.
Tests for each; regenerate the bundle last; report `_build/tmp/codex-envoy-classic-fix1-report.md` with the cause of
item 1, the new tuning table, and what a tester should play.
