# EM4 follow-up 1: the owner wants absurd power late, with opponents keeping pace (2026-10-04)

Same rules as EM4 (`docs/prompts/codex-envoy-balance-and-opponents.md`); build on your EM4 state; regenerate the bundle
last. No commits, no build, no game launch.

EM4 told you to cap families tightly ("strong, not trivial"). The integrator then asked the owner whether they would
rather it be possible to get absurdly strong late in a run, provided opponents keep pace. The owner: "Yes exactly".
So change the TARGET, not the structure. Keep from EM4: damage separated from launch (A), families and additive
stacking within a family, the validator, the bag showing totals, opponents rolling from the same pool (D).

1. **Caps become a curve, not a ceiling.** Early in a run a build is modest (the EM4 numbers are a fine starting
   point at depth 0). Power is allowed to grow without a hard limit as the run goes deeper and through New Game+
   loops: modifier tiers rise with depth, slots grow (four, then five and six), uniques and keystones stack their rule
   breaks, and multiplicative interactions BETWEEN families are welcome (that is where builds get absurd). Keep only
   the safety limits that protect the game itself: no infinite loops, chain depth and per-frame budget, values that
   would break physics or the percent display, and a sane floor on damage taken so nobody is literally unkillable.
2. **Opponents keep pace by construction.** One strength number for a build (from the family totals and rule-breakers);
   an opponent's rolled budget is that number times a difficulty factor that rises with depth and loop, so a player who
   is ten times vanilla meets opponents who are in the same league: more modifiers, higher tiers, their own uniques and
   keystones, and at high strength, defensive families that answer the player's offence (a glass cannon meets armour;
   a status build meets resistance or cleansing), chosen by weight, never by reading the player's exact build.
   Bosses and the final boss get a larger factor. State the curve and show, as a table over depth 0-12 and loops 0-3,
   the player's plausible strength range and the opponent's, and how many hits a kill takes each way.
3. **The contest stays readable at high power.** When both sides are absurd, fights must not collapse into one-hit
   kills both ways: prefer opponents scaling their toughness and their own threat through chains and statuses over raw
   launch; say how you keep a stock lasting a reasonable number of exchanges at depth 12 loop 3.
4. **A LAB dial for the owner to feel it now**: `depth <n> [loop]` sets the depth used for rolling drives and
   opponents, so they can drop late-run drives, roll a late-run opponent and fight it.
5. Tests: the curve is monotonic; the opponent tracks the player within a stated band across the table; the safety
   limits hold at extreme inputs; determinism.
Report `_build/tmp/codex-envoy-balance-fix1-report.md` with the table from item 2 and a play script: an early build
against an early opponent, then `depth 12 3` and an absurd build against an absurd opponent.
