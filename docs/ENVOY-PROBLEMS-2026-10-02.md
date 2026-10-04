# SuperTime Envoy: problems and missing work

Recorded 2026-10-02 from the user's controller sessions and source/log checks.
This supersedes earlier optimistic acceptance summaries for **Envoy gameplay readiness**.
Keep `ACCEPTANCE-SESSION-2026-10-01.md` for individual verification results; passing
tests do not mean the game is fun, understandable, complete, or accepted.

## The central failure

The user reports: **"The level sends me back around."** This is confirmed.
The default generator in `melee/pc/scripts/examples/roguelite/traversal.lua`
produces one playable entry level and a terminal exit. Leaving the level ends the
run; starting again produces essentially the same level. It has only six layout
variants (three horizontal offsets and two branch sides), no encounters, and no
meaningful campaign progression. The fresh-run log records repeated physical
traversal starts followed by `Run complete`.

The agent made this traversal prototype the default too early. It demonstrates
movement, collision, and rendering, but does not deliver the requested game.
Do not describe it as a completed maze, campaign, or roguelite.

## User feedback and outstanding work

| Problem | Evidence / current status | What remains |
|---|---|---|
| Gameplay is confusing; the purpose and loop are unclear | User explicitly said they do not understand the game loop and asked to simplify it. The current prototype has no encounters or upgrade progression. | Establish a clear objective, readable progression, encounters, earned rewards, and an understandable finish. Make the UI describe what actually exists. |
| Repetitive level loop | Confirmed in current generator and fresh-run log. | Replace the one-level repeat with meaningful progression. More offsets of the same geometry are insufficient. |
| No convincing maze generation | Original live v1 was a mostly fixed eight-room route; v2 recipes were refused as uncertified. Gen3 introduced a graph through doors. Current gen4 is one physical level with six variants. | Build varied, substantial traversal within the playable level, with actual spatial branches and purposeful routes. |
| Maze was abstracted through doors | User expected longer physical traversal within each room, rather than choosing doors between small rooms. | Honor the spatial requirement; do not substitute a room graph and call it the requested maze. |
| Current traversal is easy to bypass | Gen4 has a continuous ground route from spawn to exit beneath the overhead structure. Upper stairs and branch are optional; there is no gameplay reason to visit them. | Give routes, exploration, and platform traversal a purpose. Avoid decorative branching with a straight walk to completion. |
| Menus do not make sense | User selected "All of the above" when discussing menu problems. Free breeding was removed and layout adjusted, but a complete human usability pass has not happened. | Simplify navigation, labels, objectives, and feedback. Explain collection versus active-run actions. Verify with controller input. |
| Instructions promise nonexistent gameplay | Collection hints mention defeating enemies and upgrading, while default gen4 has no enemies. Entry notice says to explore/use Down at a doorway; the exit just finishes the level. | Align instructions with implemented behavior and clearly communicate progress and completion. |
| CPU always present / empty exploration isolation | User wanted maps loaded without CPUs. Later reported "Empty playfield isolation was lost" after defeating Fox and going through a door. Native old-route reward/transition probe passed after fixes; gen4 has no P2, but also no fights. | Verify the full fight-to-exploration loop with the controller and in the eventual physical campaign. Removing every encounter is not a solution to the game loop. |
| Invisible walls and gaps between floors | User reported both in the previous live route. Solid-wall art alignment was corrected; new native underpass walk passed. | Revisit the originally failing route and test all generated paths, transitions, and collision/art seams. One successful walk is limited evidence. |
| Platforms had ledge grabs | User asked for no platform ledges. Platform recipes now use `ledges=false`; floor ledges remain intentional. | Confirm controller behavior on all relevant layouts. Preserve this requirement in new content. |
| Platforms too low | User asked to raise them. New prototype includes stairs up to y=130 and branch up to y=156. Falco climb was demonstrated. | Test reachability for the supported roster; one fighter and analytical checks are not all-character acceptance. |
| Scaling request was misunderstood | User explicitly clarified: double each stage/editor grid cell and scale assets, **not merely double horizontal map length**. Physical prototype uses grid 26, bay 52, unit 13 and scaled assets. | Ensure the eventual generator/editor content consistently honors this scale while preserving usable platform dimensions and movement. |
| Camera framing was bad | User reported Falco at the bottom of the screen and asked to pan down. Prototype now follows the player with local framing. | Controller acceptance across ground, upper routes, falls, respawns, fights, and transitions; avoid losing sight of upcoming geometry. |
| Custom map art covered effects | User saw vanilla shield and Falco laser occluded and suspected custom effects were also hidden. Renderer changes and native captures show shield and laser visible in front of custom art. | Verify custom effects independently, across relevant materials and camera angles. Vanilla captures do not prove custom FX correctness. |
| Widescreen menus wasted the right side | User reported a 4:3 menu pinned left in a widescreen game. Menu and roster layout now use safe-area reflow; tests cover 4:3, 16:9, and ultrawide. | Visually inspect the actual menu overlay and controller hit targets. Game screenshots omit Lua overlays and cannot establish this acceptance. |
| Infinite gene duplication | User could create unlimited genes by clicking collection controls. Free collection breeding/locks were removed; transactional persistence tests remain. | Human adversarial testing of collection actions, run fusion, discard, Restore, save failures, and reloads. Do not claim the entire economy is proven. |
| Persistence defects undermined trust | Discard/Restore/history work was needed. Additional native play found history serialization failures after repeated completed runs; normalization/round-trip fixes landed locally. | Preserve regression coverage and verify repeated real sessions. Durable completion alone does not make the reward loop meaningful. |
| Name and wording inconsistent | User chose **SuperTime Envoy**, a reference to Brawl's Subspace Emissary; earlier prototype entry was `TBD`. | Audit remaining player-facing placeholders and old names without changing historical provenance. |
| Showcase did not communicate progress | User did not see the first pilot and asked to repeat it. Captures/slideshow exist, but they demonstrate a prototype. | Show a visible, understandable gameplay sequence with actual goals and progression, and distinguish still captures from video/live play. |

## Verification limits and remaining technical questions

- Latest local Lua/tool suite: **274 tests, OK, one skipped**. This is useful
  regression evidence, not gameplay acceptance or the historical native roguelite tier.
- Native physical probe established 48 models / 24 colliders, no P2, a continuous
  ground walk, camera ownership, and durable terminal completion. Its upper-cap
  check used a probe teleport. A separate controller-input pilot climbed with Falco.
- Generator 4 remains `certified=false`; admission is explicitly an analytical
  prototype path. It is not native certification of every seed or character.
- The certified v2 catalogue still refuses generation. The startup log explains
  that fallback; do not silently imply that v2 maze generation is working.
- Existing generation-3 saves resume the older door graph. A fresh generation-4
  save exercises different gameplay. Always record which one is under test.
- Lua console hotkey availability was asked about earlier; this note does not
  establish a verified hotkey. Check the actual bindings before answering.
- Sora fidelity/showcase and broader Ultimate-port completion remain separate open
  work; this Envoy session supplies no new evidence that those are complete.
- There is no defensible **100/100** completion claim or current reliable ETA for
  the remaining gameplay. Define acceptance against the user's requirements.

## Handoff priorities

1. Design and implement the actual spatial game loop: traversal with meaningful
   branches, encounters, rewards, and progression toward a clear finish.
2. Make menus and instructions match that loop and explain it with minimal friction.
3. Re-test the user's failures with a controller: fight-to-exploration isolation,
   collision/art seams, camera, widescreen UI, and gene economy/persistence.
4. Verify supported fighters and custom FX; retain existing automated regression tests.

Latest tested fresh bundle: `_build/acceptance/envoy-fresh-20261002-133256`.
Log: `_build/runs/envoy-fresh-20261002-133256/melee-pc.log`.
The user closed that game; the log ends with normal exit 0 and a teardown warning.
Workspace/game changes are uncommitted; preserve unrelated work and earlier saves.
