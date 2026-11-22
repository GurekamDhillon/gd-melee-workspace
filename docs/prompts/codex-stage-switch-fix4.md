# Packet O follow-up 4: the owner watched the six-stage tour; go to Phase C for Yoshi's Story and Fountain of Dreams (2026-10-03)

Same rules (no commits/reset, no build, no game launch, keep every file compilable). Other Codex jobs are in
`gw_script_items.inc` / the Geno item files and in Lua mods: re-read shared files before editing.

The owner watched a tour through all six legal stages and back (Final Destination -> Battlefield -> Yoshi's Story ->
Dream Land -> Fountain of Dreams -> Pokemon Stadium -> Final Destination, looping) on a build containing your follow-ups 2
and 3. All six slots load together (about 3.0 MB of the stage heap left) and the queue runs. The owner's words:
"randal doesnt work exactly right, FoD platforms dont work at all it seems".

That is the limit of Phases A and B showing: Randall and Fountain's platforms are driven by stage CODE in the real game,
not by a looping animation clip. Your own report said so (Yoshi's: "Shy Guys, Randall puff timer/effects and full stage
initialization missing"; Fountain: "Random platform heights/controller, reflection pass/cameras and stage effects
missing"), and you chose design B (one active native stage re-initialised behind the transition) with a costed plan.
Execute that plan now for these two stages, in this order, each complete before the next:

1. **Yoshi's Story.** Run the stage's real initialisation and per-frame callbacks (`melee/src/melee/gr/grstory.c` and what
   it calls) when the slot becomes active, so Randall follows the game's own path and timing (the cloud's route around the
   stage, its timer, the disappearing puff, its collision carrying fighters and items, behaviour at the blast zone), and
   the Shy Guys spawn, fly and can be hit as in the original. Establish from the code exactly what the real stage does and
   list any difference that remains. Everything the stage code creates (GObjs, items, effects, sounds) is owned by the
   slot and removed at the next switch; nothing leaks into the following stage; re-entering the stage starts it clean.
2. **Fountain of Dreams.** The two side platforms rise, fall and disappear under the stage's controller with its random
   timing (`grizumi.c` and what it calls); their collision follows them and carries fighters; a platform that is below the
   water or absent has no collision. Do the reflection pass and water effects only if they come with running the stage's
   own code safely; if they need render-order work, leave them out and say so, but the platforms must work.
3. If the teardown/re-init machinery those two need is general, apply it to Battlefield and Dream Land (Whispy's wind and
   apples) and Pokemon Stadium (transformations) as far as it goes cleanly, and list what each still lacks. Do not let
   those block items 1 and 2.
Requirements that still hold: the Lua API is unchanged; a switch is atomic and offline; fighters are made safe before any
line is removed (ledge hang fix); the CPU mode selected by a script survives; stage scale, blast zones, camera bounds,
spawns and music are the destination's; LAB savestates across a switch are refused clearly; the stage heap accounting stays
correct with stage code allocating (measure and report headroom with all six loaded and each one active in turn); the
random controller uses the game's own RNG so replays of a fixed seed are repeatable (state what it draws from).
Tests: fixtures for the init/teardown pairing (no GObj, item or effect left after a switch away; a second visit starts
clean), platform collision following its joint through a full Fountain cycle, Randall's path period matching the stage
code's own constants. Report `_build/tmp/codex-stage-switch-fix4-report.md`: what now behaves like the original per stage,
what does not, file:line, heap numbers, and exactly what the owner should look at (how long Randall takes per lap, where
he disappears; the Fountain platforms' range and timing) so it can be judged against the real game.
