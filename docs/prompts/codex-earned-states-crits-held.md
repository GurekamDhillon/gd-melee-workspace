# EM5 follow-up 1: narrow where afterimages and echoes appear (2026-10-04)

Same rules as EM5 (`docs/prompts/codex-echo-hitboxes.md`); build on your EM5 state; no commits, build or game launch.

After EM5 was sent the owner added, verbatim: "maybe we should also narrow their use a bit as well". The integrator's
reading (recorded as an interpretation, not the owner's words): afterimages and echoes should be a specific, earned,
recognisable thing, not something that is on all the time or handed out by many modifiers. Apply that everywhere:

1. **Afterimages are not a general decoration.** In the Envoy modifier looks, remove afterimages from anything that
   merely has a status or is moving (for example Haste leaving them constantly): keep them for the echo family and for
   at most one or two signature moments (a big launch; a keystone's signature). Other looks use surface treatments and
   tracers. A fighter with no echo modifier leaves no afterimages in normal play.
2. **Echoes come from few sources.** One modifier family grants afterimages at all (how many copies is that family's
   tier: one, then two, then three), and separate modifiers ARM specific copies for specific move tags. Without the
   granting modifier, arming modifiers do nothing (a deliberate dead roll, like the rest of the pool). No more than one
   granting source stacks.
3. **Narrow conditions rather than always-on.** Copies exist only in defined windows: prefer "for N frames after a dash,
   an air jump or a dodge" or "while a specific status is active" over "always"; an armed copy repeats only the move
   tags its modifier names (aerials; or one named class such as neutral air where the tag vocabulary allows: say what
   granularity the engine can really tell apart), and each copy echoes a given move once.
4. **Readable**: at most three copies per fighter in the Envoy pool regardless of the engine cap of twelve; an armed
   copy is visibly different from an unarmed one; opponents' echoes are as readable as the player's.
5. Rarity: the granting modifier is Rare-tier or above; the "every move echoes" idea stays a single unique.
Update the pool, the synergy table, the tests and `PLAYTEST.md`; report
`_build/tmp/codex-echo-hitboxes-fix1-report.md` with the final rules as a short table (source, window, copies, what is
echoed) so the owner can correct the reading quickly.

## ADDED: the owner confirmed it as a hard rule (verbatim): "no always on afterimages"
So items 1 and 3 are not suggestions: no modifier, look, demo default or engine default may leave afterimages on
continuously. Every afterimage has a start event and an end (a window in frames, or a status that itself expires).
Enforce it in the modifier schema validator (a `visual` or `echo` record with an unbounded afterimage is rejected) and
change the afterimages catalogue demo so its default is windowed (for example: for 40 frames after a dash or an air
jump), keeping a debug key for a continuous view that is clearly labelled as debug.

## ADDED: afterimages are attached to an EARNED state (owner, verbatim)
"afterimages need to be attached to a state(?) (like the after image only shows up after an attack hits, and you L
cancel its landing, and its a blue after image because you got a speedboost. idk shallow thought about it. You probably
have better telemetry to figure out how to do this"

This is the design rule that replaces "a window after any dash": **an afterimage is the visible sign of a status the
player earned through play, in that status's colour, for exactly as long as the status lasts.** In the owner's example:
land an aerial hit, L-cancel the landing, gain a speed boost, and blue afterimages run while the boost is active. No
status, no afterimage. So afterimages become information ("I am boosted, and this is which boost"), which also
satisfies "no always on".

Build it:
1. **Skill events (engine telemetry).** The modifier vocabulary needs triggers for technique, read from the game's own
   decisions, not guessed from inputs. Find where retail decides each and raise a script event with a tagged payload:
   - **L-cancel**: success or miss, and which aerial (`src/melee/ft/kinds/ftCommon/ftCo_LandingAir.c`,
     `ftCo_LandingAir_EnterWithLag`: where the landing lag is chosen and halved; `ftCo_AttackAir.c` ~191), plus whether
     that aerial HIT something before landing (hit-confirm: the fighter's hitboxes connected during this action).
   - tech (in place, roll, wall, ceiling) and missed tech; wavedash and waveland (an air dodge that lands with
     horizontal speed); dash dance turn; jump-cancelled grab or up-smash; shield drop; perfect shield (exists);
     ledge dash (ledge release to an actionable landing within N frames); teching a throw is out of scope.
   - combo telemetry already implied by the engine: hits in a row on the same target without it touching ground or
     acting (a combo count), time since last hit dealt, a kill off a combo.
   For each: file:line of the retail decision, the event name and payload, and which you could not find a clean decision
   point for (report those rather than approximating from inputs). Events are read-only observers, deterministic,
   offline and online safe; document them in `docs/scripting.md` and add them to the contact trace so a tester can see
   them fire.
2. **Statuses own their afterimage.** In the modifier schema a status may declare an afterimage look (colour from the
   status, copies, spacing); it shows only while the status is active on that fighter and ends with it. Equipment and
   plain movement cannot declare one. This is the only way afterimages appear in Envoy (the echo family from EM5 then
   ARMS copies that a status is already showing: no status, nothing to arm).
3. **A first set of earned statuses**, each with a distinct colour so the afterimage tells you what you have: for
   example Haste (blue: speed) from an L-cancelled aerial that hit; Guarded (teal) from a perfect shield or a tech;
   Momentum (gold) from a combo count; something offensive (red) from a hit-confirmed landing into a dash. Keep the set
   small; every one must be expressible as "technique event -> status -> effect + afterimage", as data.
4. Modifiers that grant these are ordinary rolled modifiers ("of the Clean Landing: an L-cancelled aerial that hit
   grants Haste for 120 frames"), sit inside the power-budget families, and can roll on opponents: say how a CPU earns
   them (retail CPUs L-cancel and tech at some levels: report what they actually do).
5. The catalogue demo for afterimages becomes this: land an aerial on a standing opponent, L-cancel, and see blue
   afterimages for the boost's duration; miss the L-cancel and see none. The debug overlay names the skill event and
   the status it granted.
Tests: each skill event fires exactly once at the right frame (fixtures drive the retail decision points), the
afterimage's lifetime equals the status's, and the validator rejects an afterimage with no owning status.

## ADDED: the owner named a second reference case: "perfect shield"
Treat a perfect shield (powershield) as a first-class earned trigger beside the L-cancelled hit: it grants a status with
its own colour and afterimage for the status's duration, and the catalogue demo shows both cases (a CPU or scripted
opponent attacks; the player perfect-shields and sees the afterimage; an ordinary shield gives none). The perfect-shield
event already exists from EM1: confirm it distinguishes a physical-hit powershield from a projectile reflect, fires
once per shield, and say what the retail timing window is so the tooltip is truthful.

## ADDED: technique abilities, and a specific home for tracers (owner, verbatim)
"we can also have characters have like an abilitiy where on wavedash do xyz, like wavedash into superarmour for 0.1
second. It would have a dope look with all of our shader work and after images. Tracers need to be fit onto/into
something somewhere more specifically I think"

A. **Technique -> effect, as a general shape.** With the skill events of this packet as triggers, "on wavedash, gain
   super armour for 6 frames" must be one data record. A parallel job (`docs/prompts/codex-armour-types.md`, report
   `_build/tmp/codex-armour-types-report.md` when it lands) is adding named armour types (knockback, damage-threshold,
   super armour for a window, hit-count, damage-pool) with an `on_armor` event: add an `armor` effect kind to the
   modifier schema that maps to that API (guarded for its absence), plus `on_armor` absorbed/broke as triggers.
   First records: the owner's example (wavedash -> super armour ~6 frames, with a status so it has a look and, per the
   earned-state rule, its afterimage for those frames); an L-cancelled hit -> a few frames of damage-threshold armour;
   perfect shield -> hit-count armour 1; "when your armour absorbs a hit" -> something offensive. These may be rolled
   modifiers, and ALSO a fighter's own innate ability: say how a character-level ability (belonging to the fighter, not
   to loot) should be declared so the Geno fighter format can carry it later; do not edit the Geno engine, report it.
B. **Tracers get one job.** Like afterimages, tracers must mean something. Rule: **a tracer marks a hit that carries
   something extra**, on the attacking limb or weapon (the active-hitbox anchor), in the colour of what it carries, for
   as long as that hitbox is active: a converted element (fire arc on a Burning smash, electric on Charged aerials), a
   hit empowered by a status or a stored bonus (Reprisal's next hit, a Momentum spend), an armed echo's repeat of the
   move, a hit during an armour window. An ordinary, unmodified hit has no tracer. Retail sword trails are left alone.
   No tracer is attached to plain movement, joints "because they move", or statuses with no hit involved (those are
   surface looks or, when earned, afterimages). Enforce in the schema: a tracer `visual` must name the hit condition it
   marks. Width and length scale modestly with the bonus so a big empowered hit reads bigger.
C. So the visual language is three channels with one meaning each, and the report should state it as a table the owner
   can correct: **surface treatment** = what you have equipped or which status is on you; **afterimage** = a status you
   earned through technique, while it lasts; **tracer** = this particular hit carries something extra.

## ADDED: critical hits, with impact frames scaled to the crit (owner, verbatim)
"we can add crits in btw, our impact frames can be toned down, and made tuneable based on how hard of a crit strike it
is."

D. **Crits as part of the same vocabulary, not a side system.**
   - Two new families inside the power budget: **crit chance** and **crit multiplier**, with a small base for everyone
     (state it; a suggestion: 5% chance, x1.5). A crit multiplies the hit's PERCENT damage through the percent-only
     damage path (so it does not buy launch twice); whether a crit also adds launch is a separate, smaller, explicitly
     worded bonus that only some modifiers grant.
   - **Deterministic**: the roll uses the modifier engine's seeded generator, decided when the hit is resolved in a fixed
     order, recorded in the rewind journal; the same inputs give the same crits. Say how it stays stable under rewind
     and what would be needed for netplay.
   - **Guaranteed and conditional crits** are where it joins the rest: "your next hit after a perfect shield crits",
     "hits on a Burning target crit", "an L-cancelled aerial's follow-up crits", "an armed echo's hit always crits",
     "the hit that breaks armour crits". A crit is also a TRIGGER (`on_crit`, with its strength) and a CONDITION, so
     other modifiers chain off it ("on crit: apply Shock", "on crit: gain Momentum"), and it is a hit tag opponents and
     echoes carry like any other.
   - Strength is one number the whole system shares: crit strength = the extra damage the crit added, normalised
     (state the formula), so a small crit and a huge one are distinguishable everywhere.
E. **Impact frames, toned down and scaled.** The clank impact-frame experiment
   (`melee/pc/scripts/examples/experiment/clank_impact/`, the post-pass and timed-hitstop capabilities it added) is the
   source of the effect: reuse it as the crit moment, much quieter by default. One function maps crit strength to the
   presentation: at the bottom a brief punch (a few frames of extra hitstop, a small flash on the tracer, a short screen
   kick); at the top the full impact frame (inverted or high-contrast frame, speed lines, longer hitstop). Everything is
   in the tuning table: the strength thresholds, duration, hitstop frames, contrast, shake, and a global intensity
   setting, with photosensitive-safe limits that the top end still respects (no full-screen flashes above the safe
   rate) and a setting to turn impact frames off entirely while keeping the hitstop. A crit's tracer follows the tracer
   rule (this hit carries something extra): the crit colour and a thickness that grows with strength.
   An ordinary non-crit hit gets none of this.
   A LAB command to preview the curve without fighting: `crit preview <strength>` plays the moment at that strength.
F. Rolled modifiers for the first set (crit chance, crit multiplier, a conditional guaranteed crit or two, an on-crit
   trigger or two, one unique built around crits), opponents can roll them, and the synergy table updated.
Tests: the roll's determinism and distribution over 10,000 hits, percent-only application, conditional crits, the
strength formula, the presentation curve's monotonicity and safe limits.

