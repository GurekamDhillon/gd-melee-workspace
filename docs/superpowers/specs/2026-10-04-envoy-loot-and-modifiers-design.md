# Supertime Envoy: loot and modifiers (design)

Date: 2026-10-04. Status: for the owner's review; nothing here is built.
Supersedes, for what a run is and what a reward is: `2026-10-03-supertime-envoy-design.md` sections on runs, rooms and
the four-stat reward loop. The companion, its life cycle and the garden in that document still stand.

## 1. Why this exists

Three attempts taught us what does not work. Generated levels were a lot of machinery for a place that "read lightly as
a maze". Classic mode with a drive choice after each stage worked end to end and was, in the owner's words, "mostly
normal classic ... Nothing was particularly great": a menu of small percentage bonuses on top of real Melee is not felt.
Two things survived every round: the fights should be real Melee, and picking up a physical drive "felt nice".

The owner's direction: "whats path of exile doing? They have items with actives/passives, suffix/prefix
modifiers/uniques/etc. We need to make emergent gameplay with synergies".

So the reward stops being a number and becomes an item with rules on it, and the fun is in how separately written rules
combine.

## 2. The idea in one paragraph

A run is the game's own Classic mode (Adventure next). Opponents drop drives. A drive is a piece of loot: a base type,
a rarity, and a few rolled modifiers, each a small rule such as "aerials apply Burn" or "on shield, gain speed for three
seconds". You equip a handful of them on your companion. Modifiers never name each other: they share tags and events, so
two drives written separately can chain. Opponents roll modifiers of their own, shown on a nameplate. After Master Hand
the run loops, harder, with your build intact.

## 3. Where emergence comes from (the four rules every modifier obeys)

1. **Tags, never names.** A modifier refers to `aerial`, `smash`, `projectile`, `fire`, `burning`, never to a specific
   move or another modifier.
2. **Trigger, condition, effect.** Every modifier is "when X happens, if Y holds, do Z". Effects raise events and apply
   statuses that other modifiers can trigger on.
3. **Conversion.** Some modifiers change what a thing counts as ("your throws count as smash attacks", "half your
   damage is dealt as fire"), which makes every modifier keyed to the new tag matter.
4. **Rule-breakers are rare and loud.** Uniques and keystones change what is possible, at a stated cost.

A synergy is not designed. It is two modifiers that share a tag or an event. The design work is choosing a vocabulary
small enough that sharing is common.

## 4. Vocabulary (first version)

**Move tags** (from the fighter's action state and hitbox data): `jab`, `tilt`, `smash`, `aerial`, `special`, `grab`,
`throw`, `projectile`, `dash_attack`; plus `grounded` / `airborne` at the time of the hit.

**Element tags** (Melee already has these as hit elements): `normal`, `fire`, `electric`, `ice`, `darkness`.

**Triggers**: on hit dealt, on hit taken, on KO dealt, on stock lost, on shield hit, on perfect shield, on clank,
on jump, on air jump, on landing, on ledge grab, on grab, on throw, on taunt, on item pickup, on stage start,
every N seconds.

**Conditions**: airborne, grounded, own damage above or below a value, target's damage above a value, on last stock,
target has a status, self has a status, within N seconds of an event ("recently"), stage kind (team, giant, metal).

**Statuses** (timed, stackable, visible as a tint or a small icon): `Burn` (damage over time), `Shock` (next hit taken
has more hitstun), `Chill` (slower movement), `Curse` (takes more knockback), `Haste`, `Guarded`, `Momentum` (a generic
stack that modifiers can build and spend).

**Effects**: change a fighter value for a duration (damage dealt, knockback dealt or taken, run and air speed, jump
height, number of air jumps, fall speed, weight, shield size and regeneration, size), heal or deal damage, apply or
remove a status, add or spend stacks, change a hit's element, add hitstop, spawn an item or a projectile, grant brief
intangibility, turn metal for a duration.

Every effect is one the engine can really do; anything it cannot do is listed in section 10 and left out until it can.

## 5. Drives as loot

- **Base type** = the drive's colour, with one fixed built-in property (its implicit). Red: damage dealt. Green: run and
  air speed. Blue: knockback taken. Yellow: jump height. Purple: status duration. White: no implicit, one extra
  modifier slot.
- **Rarity** sets how many rolled modifiers it carries: Common (none, implicit only), Magic (one prefix, one suffix),
  Rare (up to two of each), Unique (fixed, hand-written).
- **Prefixes** are steady properties and conversions ("Burning: your `smash` hits are `fire`"). **Suffixes** are
  triggered rules ("of the Updraft: on `aerial` hit, +1 Momentum; at 5, your next air jump is refunded").
- **Tiers.** Each modifier has tiers; the tier that can roll rises with depth in the run and with the loop count.
- **Names are generated** from the modifiers: "Burning Red Drive of the Updraft". The name is the tooltip.
- **Drops.** Defeated opponents drop drives physically (the pickup that already exists and "felt nice"); bosses and
  bonus stages drop better ones. Rolls are seeded per run and stage, so a retry is the same.

## 6. The build

- The companion carries a small number of equipped drives: **four slots** at first, a fifth and sixth earned as it
  grows. Slots are the constraint that makes choices matter.
- Unequipped drives sit in a small bag (twelve). Between stages, on the screen that already exists after a stage clear,
  you equip, swap or discard. Controller only.
- **Keystones** are not loot. A companion gets one keystone choice each time it evolves (at each Master Hand). They are
  the big trade-offs.
- The four stats do not disappear: they are the implicit properties and some of the modifier families. There is no
  separate stat screen to grind.

## 7. Opponents

- Each CPU opponent rolls modifiers from the same pool, with a budget centred on the strength of the player's build and
  rising with depth and loop count. They are shown on a **nameplate** at stage start ("Hasted, Burning Fox") and by a
  tint, so the player can read the fight before it starts.
- Retail handicaps (giant, metal, team size) stay and stack.
- Opponents use the same modifier engine, so anything that is fun on the player is also a threat on an enemy.

## 8. The first pool (enough to prove emergence, small enough to tune)

About thirty modifiers, five uniques, three keystones. Examples, to show the shape rather than to fix the list:

Prefixes: Burning (`smash` hits are `fire`); Charged (`aerial` hits are `electric`); Heavy (more knockback dealt, slower
run); Featherweight (higher jumps, more knockback taken); Lingering (statuses you apply last longer).
Suffixes: of Kindling (`fire` hits apply Burn); of the Pyre (targets with Burn take more knockback); of Feasting (on KO
of a target with any status, heal 10%); of the Updraft (on `aerial` hit gain Momentum; at five, refund an air jump); of
Reprisal (on perfect shield, your next hit has extra hitstop and damage); of the Ledge (on ledge grab, gain Haste).
Uniques: **Second Wind** (one extra air jump; you cannot air dodge); **Glass Core** (double damage dealt and taken);
**Conductor** (your `electric` hits chain Shock to the nearest other opponent); **Hoarder** (start each stage holding a
random item); **Mirror Shard** (on clank, the opponent takes the damage of both attacks).
Keystones: **Aerialist** (five air jumps; you cannot shield); **Juggernaut** (you do not flinch below 30 damage taken
per hit; you cannot run); **Pyromancer** (all your damage is `fire`; `ice` hits against you are doubled).

The test of the pool: a tester can name at least five two-modifier combinations and two three-modifier combinations
that nobody wrote as a set.

## 8b. Every modifier is visible (shaders)

The owner's requirement: "make it have visual components via shaders". The last version failed partly because nothing
on screen told you your build existed. So a modifier is not only a rule: it has a look, drawn with the shader systems
the engine already has (fighter surface shaders, stage surface shaders, post passes, script lights, world effects).

- **Each element and status owns one shader treatment**, used everywhere it appears, so the screen teaches the
  vocabulary: Burn = an animated ember rim and heat shimmer on the fighter's surface; Shock = crawling arcs and a
  flicker; Chill = a frost creep from the extremities with a desaturated body; Curse = a dark, inverted rim; Haste =
  streaked afterimages; Guarded = a faceted glass shell that flashes on an absorbed hit; Momentum = a glow that climbs
  the body with each stack and discharges when spent.
- **Your build is on your fighter.** Each equipped drive contributes a small, layered surface treatment in its colour
  and element (a red ember trim, a yellow updraft at the feet), composited in a fixed order, so two players with
  different builds look different at a glance. Rarity raises the intensity: Common none, Magic subtle, Rare clear,
  Unique a signature effect of its own.
- **Uniques and keystones get a signature look**, hand-written like their rule: Glass Core makes the fighter
  translucent and refractive; Aerialist leaves wing-like trails on air jumps; Pyromancer turns every hit spark to
  fire; Conductor draws the chain between opponents.
- **Opponent modifiers are read from their surface** as well as the nameplate, using the same treatments, so "Burning,
  Hasted Fox" looks like it.
- **Triggers get a moment**: a short post pass (a pulse, a chromatic kick, an impact frame for the rare big ones) when a
  chain fires, scaled by how many modifiers took part, so a three-modifier synergy looks like an event.
- **Drives themselves** carry it: the pickup's core glows in its element, rarity sets the beam and sparkle, and a
  unique has its own look on the ground.
- **Rules for readability**: at most three surface layers per fighter are drawn at full strength (the rest fold into a
  combined tint); statuses outrank equipment; effects never hide the fighter's silhouette or hurt animation; a setting
  reduces intensity; photosensitive-safe limits on flashes.
- **Data, not code**: a modifier's record names its visual (`surface`, `post`, `light`, `fx`, parameters, layer,
  priority), drawn from a small library of shader bodies, so adding a modifier does not mean writing a shader, and the
  overlay can show which layer came from which drive.
- **Cost**: every treatment is declared to the warm-up system at stage load so none compiles during play, and the whole
  layer has a frame budget measured by the profiler against the 120 fps target.

## 9. The modifier engine

One new system, and the only large piece of work.

- **Modifiers are data**: `{id, tags, tier values, trigger, conditions, effects, stacking rule, text template,
  visual}`. Adding one is a few lines in a table, not code. The same record produces the tooltip and the look (section
  8b), so text, behaviour and visuals cannot drift.
- **An event bus**: the game raises events (hit, KO, shield, clank, jump, landing, ledge, item pickup, stage start) with
  tagged payloads; the engine matches triggers, checks conditions, runs effects, and effects may raise further events,
  with a depth limit and a per-frame budget so a chain cannot run away.
- **Statuses and stacks** are owned by the engine: duration, maximum stacks, refresh rule, visible marker.
- **Deterministic**: seeded rolls, fixed evaluation order, no wall-clock; the state lives where the offline rewind can
  capture it. Offline only; nothing here runs in netplay.
- **Where it lives**: evaluation in Lua first (fast to iterate and to add modifiers), on top of engine events and
  fighter modifiers; hot paths move into the engine only if the profiler says so.
- **Debuggable**: a console command and overlay that list a fighter's active modifiers, statuses and stacks, and a trace
  of the last chain ("Burn applied by Kindling, +knockback from Pyre, heal from Feasting").

## 10. What the engine must provide (to verify before promising)

Believed to exist already: hit, clank, KO and contact events; fighter modifiers for damage, knockback, speed; tints and
effects; standalone items; 1P stage hooks; a hold between stages.
To verify or add: the move tag and element of a hit, readable at hit time; changing a hit's element; jump height and
air-jump count; fall speed and weight; flinch resistance; healing; brief intangibility; spawning an item into a
fighter's hands; a visible status marker; reading shield and perfect-shield events; applying all of these to CPU
opponents in every 1P stage kind. Anything missing becomes an engine request, and its modifiers wait.
For the visuals (section 8b), believed to exist: fighter and stage surface shaders, post passes, script lights, world
effects, shader warm-up. To verify or add: several surface layers composited on one fighter in a set order with
per-layer parameters; a surface shader on a CPU opponent and on sub-fighters; driving shader parameters per frame from
status stacks without recompiling; a layer that survives costume, metal and size changes; the cost of three layers on
six fighters.

## 11. Build order

1. **The modifier engine and the event vocabulary**, with a debug overlay and the first ten modifiers, each with its
   shader treatment from the start (section 8b: the status looks and layered fighter surfaces are part of step 1, not
   polish), tested offline and in the LAB against a standing opponent.
2. **Drives as rolled loot**: generation, names, tooltips, drops, the bag and the slots.
3. **The full first pool** (thirty, five, three) and the synergy test.
4. **Opponent modifiers and nameplates.**
5. **On Classic**: drops per stage, the between-stage equip screen, keystone at evolution, New Game+ scaling.
6. The garden and the companion as the place the build lives (the earlier spec), once the loop is fun.

Each step ends with something the owner can play.

## 12. Out of scope for now

Crafting currency, trading, sockets and links between drives, a passive tree, generated levels, new art. Each could
come later; none is needed to find out whether the loop is fun.

## 13. Risks

- **Balance is impossible to get right up front.** Accepted: caps on every numeric family, a hard limit on chain depth,
  and tuning by play. Broken combinations are part of the appeal in single-player; degenerate ones (infinite loops,
  unkillable) are bugs.
- **Readability.** Melee is fast. Statuses and opponent modifiers must be few on screen and distinct; the nameplate and
  tints carry most of it.
- **Engine reach.** Section 10 decides how rich the vocabulary can be. The first step exists partly to find that out.
- **It could still be flat.** If thirty modifiers on Classic are not fun, more modifiers will not fix it, and the
  question becomes the fights themselves.

## 14. Decisions (owner, 2026-10-04)

1. Equipped slots: the owner has no preference ("idc"). Four to start, in the tuning table.
2. Whether drives persist between runs: undecided ("idk"). Built as a fresh build per run, kept through New Game+
   loops, with persistence behind one switch so both can be played before deciding.
3. Opponents may roll uniques and keystones: yes.
