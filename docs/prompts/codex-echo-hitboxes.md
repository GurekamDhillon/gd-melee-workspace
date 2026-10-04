# Parallel packet EM5: echoes: afterimages that can hit (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md` (read it again: the Geno `define` slice 1 job is editing roster and
fighter-definition code now; stay out of it). You own the Envoy mod, the hit rules, and NEW files named
`script_echo*` / `gw_script_echo*`. No commits, no build, no game launch. Do not stop for design approval; record
choices in the report.

## The owner's idea (verbatim)
"Is it possible to read location/state data from the after images? It would be an awesome ability/item/something idk if
we could give after images hitboxes or something. For example, in a run we got 3 after images, and something something
something, an upgrade turned on the hitbox for nair on after images for image 2 and 1, or something, idk"

## What exists and why it is not enough
Afterimages (`gd.afterimage_add`, `melee/pc/platform/gw_fx_motion.cpp`) are presentation only: a captured DRAW of the
fighter, kept outside the simulation on purpose, with no position, state or hitbox data a rule could use, and nothing
there may affect gameplay. So the gameplay side needs its own history, in game memory, and the picture and the rule
must be driven from the same delay so they line up.

## Build
1. **A gameplay history per fighter** (all six slots, sub-fighters, CPUs), recorded every logic frame into a small ring
   in game memory covered by the LAB snapshot and rewind (prove 0 differing bytes): position, facing, grounded or
   airborne, action state and its frame, move tag, and for each ACTIVE hitbox its world-space capsule (both ends and
   radius as the game resolved them that frame), damage, angle, knockback values, element, and the hitbox's identity for
   "already hit this target" bookkeeping. State the depth (enough for the afterimage maximum of 60 frames) and the cost.
   Read API (no gameplay gate): `gd.fighter_history(port, age)` -> that record, or nil; `gd.fighter_history_depth()`.
2. **Echo hitboxes**: a native, data-driven rule (same philosophy as the hit rules: declared ahead by script, no Lua
   during collision) that replays a fighter's recorded hitboxes `delay` frames later at their recorded world positions,
   as real hitboxes owned by that fighter (so damage, knockback, element, hit rules, statuses, KO credit and the
   existing hit events all work, and the echo cannot hit its owner or the owner's team unless team attack says so).
   `gd.echo_add(port, {delay=frames, match={move=..., element=..., airborne=...}, damage=scale, knockback=scale,
   element=..., once_per_move=true|false})` -> handle; `gd.echo_remove`; several echoes per fighter at different delays
   (capacity stated). Find the right carrier in this engine for a hitbox that is not attached to the fighter's bones
   (an invisible standalone Geno article or item hitbox positioned each frame from the history; the scripted-hit path in
   `script_game.c`; or a new minimal capsule list tested in the same collision pass) and say why; it must go through the
   normal collision so shields, clanks, hitlag (define what an echo hit does to the OWNER's hitlag: recommend none),
   staling and rebound behave sensibly. An echo of a hitbox that already hit a target with the live move follows a
   stated rule (default: an echo is a separate hit, with its own once-per-target memory).
3. **Picture and rule aligned**: an echo at delay N lines up with the afterimage copy whose age is N: give
   `gd.afterimage_add` copies a way to be addressed by index/age (so copy 2 can be tinted or flashed when its echo is
   active or connects), and a helper that creates an afterimage emitter and its echoes from one description so they
   cannot drift. A copy whose echo is armed should look armed (brighter, in the hit's element colour) and flash on hit.
4. **In the modifier engine** (data records, with shader looks): an `echo` effect kind and a first family, tunable and
   inside the power-budget families so they scale with depth like everything else. Suggestions, improve them: a prefix
   that grants afterimages while a status is active (Haste already leaves them); a suffix "of Echoes: your first
   afterimage repeats your aerial hitboxes at 40% damage"; higher tiers arm the second and third copies; a unique whose
   echoes repeat EVERY move but you deal less with the live hit; a keystone trade-off; synergies through the existing
   vocabulary (an echo hit counts as its move tag and element, so Kindling, Pyre, Updraft and the rest chain off echoes
   without being written for them). The owner's own example must be expressible: three afterimages, an upgrade arms the
   neutral-air hitbox on copies 1 and 2.
5. LAB commands to try it without loot: `echo add <delay> [move] [scale]`, `echo clear`, and a catalogue demo ("echoes":
   a fighter with three afterimages whose second copy repeats aerials, hitting a standing opponent).
6. Tests in the suite pattern: history recording and snapshot exactness; an echo hit landing at the recorded place and
   frame; owner immunity; shield and clank; the once-per-target rule; cleanup on KO, respawn, scene change and unload;
   determinism; Lua tests for the modifier records. Docs updated.
Report `_build/tmp/codex-echo-hitboxes-report.md`: the carrier you chose and why, the APIs, cost, what cannot be done,
shared-file edits, what the integrator must rebuild, and a play script for the owner.
