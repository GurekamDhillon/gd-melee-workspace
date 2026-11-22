# Codex packet EM2: native hit rules, so modifiers can change a hit (2026-10-04)

Workspace root is two levels above this file; game checkout `melee/`. Same rules as packet EM1
(`docs/prompts/codex-envoy-modifiers-step1.md`): both trees are deliberately dirty, no commits, no
`tools/port/build.sh`, no game launch, keep every file compilable; do not stop for design approval (the owner said "go,
queue it on codex"); record your choices in the report. You have just finished EM1: build on that state.

## Why
EM1's audit found that `on_hit` reaches Lua after damage is applied, and left out every rule that changes a connecting
hit (conversions such as "your smash hits are fire", "more damage against cursed targets", the Pyromancer keystone).
Conversion is one of the four emergence rules of the approved design
(`docs/superpowers/specs/2026-10-04-envoy-loot-and-modifiers-design.md` section 3). The integrator read the hit code and
the scope is small if Lua never runs at hit time:

- A move creates a `HitCapsule` with its damage, angle, knockback and element; on contact the game logs a POINTER to it
  (`ftcoll.c` damage log, `entry->hit0`), and later in the frame knockback, element, hit effect and sound are read from
  that same capsule (`ftcoll.c` ~2890-2940, `hit_effect_ids[...]`). So a hitbox changed when it is CREATED is consistent
  everywhere downstream.
- Creation sites: fighter move scripts `src/melee/ft/ftaction.c` ~342 (`create_hitbox_4`), throws `ftaction.c` ~721
  (`set_throw_hitbox_2`), items and projectiles `src/melee/it/itanimlist.c` ~121, Geno articles
  `pc/geno/geno_game_articles.inc` ~389; hand-set cases exist (e.g. `ftPurin/ftpurinspecialhi.c` Rest, Samus grapple,
  stage hazards in `gr/`). Verify all of this yourself and find any site missed.
- Precedent for native work at the hit: `Geno_HitStunBonus` / `Geno_HitFlags` at `ftcoll.c` ~745.

## Build
1. **A native rule table set ahead of time by script; nothing in Lua runs during collision.** Per fighter entity
   (all six slots, sub-fighters, CPU opponents), a small fixed-capacity list of rules, each
   `{match, change}`:
   - match: move tag (jab, dash attack, tilt, smash, aerial, special, grab, throw, projectile/item owned by this
     fighter, any), grounded/airborne at creation, the hitbox's original element (or any);
   - change, applied when the hitbox is created: set element (only Normal, Fire, Electric, Ice, Darkness: refuse the
     special ones such as Sleep, Catch, Inert, Lipstick, and never touch a hitbox whose original element is one of
     those); scale damage; scale knockback growth and base; add shield damage; add hitstun; optional fraction
     ("half your damage as fire" = say how you represent a split honestly: a second damage component of the other
     element applied with the hit, or a documented approximation: do not pretend).
   - rules that depend on the TARGET, applied on contact: scale damage if the victim carries a status bit; scale
     knockback taken likewise. Statuses are a per-fighter bitmask the script sets and clears (the modifier engine owns
     their meaning). Sites: where contact damage is computed for fighter hits and for item hits, and where knockback is
     resolved; one shared helper.
   Evaluation order and stacking are fixed and documented (rules in insertion order; multipliers multiply; the last
   element set wins); caps on every multiplier.
2. **One shared helper** called at each creation site, in a new file, with the move tag derived at creation from the
   fighter's action state. Improve the tag: "special" is ambiguous (fighter-specific states are not all specials): give
   each fighter family a mapping or return `unknown` honestly, and say which fighters are covered.
3. **Script API** (offline-only gameplay writes, the usual gate; registration tables; `docs/scripting.md`):
   `gd.hit_rule_add(port, {...})` -> handle, `gd.hit_rule_remove(handle)`, `gd.hit_rules(port)`,
   `gd.hit_rules_clear(port)`, `gd.fighter_status(port, bits)` / read; rules and status bits cleared on KO respawn only
   if the script says so, always cleared on scene change and when the owning script unloads.
4. **Deterministic and snapshot-safe**: the table and status bits live in game memory covered by the LAB savestate and
   rewind; prove 0 differing bytes with rules active.
5. **Retail side effects are kept and documented**: electric lengthens hitlag, fire ignites, ice can freeze, darkness
   has its own effect; scaled damage changes clank priority and staling input; say exactly what a converted hit does
   differently from the original.
6. **The modifier engine uses it**: add `convert` and `versus-status` effect kinds to the Lua engine's schema, mapped to
   these calls; restore the modifiers EM1 left out (a conversion prefix or two, "of the Pyre" as a real knockback
   multiplier on burning targets, the Pyromancer keystone), each with its shader look; the debug trace names the rule
   that changed a hit.
7. A catalogue demo ("hit rules": Mario's smash attacks become fire, aerials electric, shown with the game's own hit
   effects), tests in the suite pattern (each creation site, each element, refusal of special elements, target-status
   scaling, caps, cleanup, rewind exactness), and Lua tests for the new modifier kinds.
Report `_build/tmp/codex-hit-rules-report.md`: every creation site with file:line and whether it is covered, the
fighters whose special tag is mapped, how a split-element hit is represented, the side effects, what the integrator
must build, and what a tester should do (which modifiers to add, which moves to use, what they should see and hear).
