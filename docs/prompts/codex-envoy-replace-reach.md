# Envoy follow-up: replace the Reach stat (2026-10-03)

Same rules as your earlier Envoy packets (Lua/Python/JSON/Markdown only, your mod and tests, no C, no build, no game
launch, no commits); regenerate the Envoy bundle last. The missions mod is being edited by another job: do not touch it.

The owner, verbatim: "Reach is a stupid stat." Reach (yellow drives: pickup radius and drop chance; passives Finder and
Lucky Garden) changes how much you collect, not how the fighter plays, so it never shows up in the player's hands.

1. **Remove Reach and replace it with Jump** (the integrator's choice; keep the name and numbers in the one tuning table
   so the owner can change them): yellow drives raise Jump. Jump changes the fighter's mobility in a way a player feels
   in a maze: jump height (ground and air jump), and at the cap a modest air-mobility bonus. Use only fighter attributes
   the engine's `gd.fighter_mod` actually registers (check the registration tables; if jump height or air jump height is
   not modifiable, report it as an engine request and use what is: do not fake it by teleporting or velocity pokes).
   Choose caps deliberately: the maze generator's reachability and clearance rules assume measured jump reach (full hop
   about 29 units, double jump about 52 for Mario), so a Jump bonus must never make a level unfair by its absence; state
   the cap (a suggestion: +15% jump height at cap) and note for the maze job that levels are always solvable at Jump 0.
   The Jump evolution type gets a named passive in the same spirit (for example a slightly higher air jump); the Balanced
   passive must not depend on Reach either: replace Lucky Garden with something a player feels.
2. **Pickup radius and drop chance become fixed values** in the tuning table, no longer driven by any stat. Drop the
   engine request for a per-instance collection radius from your report (say it is withdrawn).
3. **Saves and DNA**: migrate existing profiles (the reach trait, alleles, grades, points, life gains and evolved type
   `reach`) to Jump one-to-one so nothing is lost; bump the save version; old versions migrate in memory as before.
4. Every screen, the hub stations, the HUD bars, results, `MENUS.md`, `PLAYTEST.md` and the tests updated; no string
   "Reach" left in the player-facing text.
5. While here, say in the report what each remaining stat does to the fighter at levels 1, 5, 10 and 25 in plain words
   (Power, Speed, Guard, Jump), and whether any of them is at risk of the same complaint (not felt in the hands).
Tests; report `_build/tmp/codex-envoy-replace-reach-report.md`.
