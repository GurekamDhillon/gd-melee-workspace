# Parametric effects lab implementation plan

Full implementation handoff: [TBD roguelite completion and polish plan](ROGUELITE-COMPLETION-PLAN.md)
defines the expanded offline completion scope, execution order and acceptance gates.
The checkpoints below remain dated evidence and research, not claims that the full plan is implemented.

The completion plan's Gate 9 now also specifies the expanded visual vocabulary:
fighter afterimages, movement/weapon tracers and ribbons, segmented halos, orbitals,
continuous fields, persistent surface treatments, silhouette attachments, contact/world
traces and combat/UI connections. These are planned techniques with explicit native
support and motion-validation requirements, not additional implemented presets.
See [Expanded visual vocabulary — beyond bursts](ROGUELITE-COMPLETION-PLAN.md#expanded-visual-vocabulary--beyond-bursts).

Status (2026-09-30 audit): partial prototype implemented; first milestone is **not complete**.
Recorded 2026-09-29. This document consolidates the effect, blending, genetics, and
synergy proposals from the planning conversation. It is not a runtime validation report.

Implementation checkpoint: script-owned handles, seeded playback, finite lab lifetimes,
parameter tweening, two procedural sprite-based founder sketches, a fire/ice crossfade,
and a manually triggered Thermal Shock sequence exist. The native FX tests and four
authoring/workflow tests pass. Nine recorded runtime cases reached 107–173 particles
and ended with no live particles/emitters or refused emissions. These results establish
basic execution and cleanup, not artistic quality or the full plan's acceptance criteria.
Recipe v2 now uses the 16 approved original assets from `menu/out_effects_study`,
with SHA-256 verification and correct R/A offset swizzles. All nine v2 runtime
cases passed nonempty emission, phase capture, lifetime refusal tracking, and
complete cleanup. Fire, ice and midpoint were reviewed at both camera distances.
The earlier v1 audit sampled refusals only at the end; v2 fixes that blind spot.

The mouse panel has now been verified with compositor captures and real pointer input:
loop playback, both blend endpoints, the midpoint, and Thermal Shock. The layout keeps
Falco clear of the stats box. Expired previews show FINISHED; editing them replays the
selected recipe. Editing a reaction returns to the ordinary 14-emitter preview instead
of sending those controls to the reaction's different emitter layout. Current controls
are simpler than the planned traits:
palette biases hot/cool lightness, rhythm adjusts density, cohesion scales sprites, and
turbulence scales the shader parameter. UI labels identify these narrower behaviours.
There are no mesh shells/shards, general synergy rule engine, genetics, remaining three
founders, or remaining pairwise blends. Saved settings carry a recipe number but do not
yet preserve resolved configurations/assets against future authoring changes.

Audit correction: lab emission-window and natural-decay changes are restricted to
script-owned lab effects; existing fighter/article bindings retain their prior timing
and fade behaviour, with a regression check added. Model-part capture failures have
been resolved: 28 stored character/costume reports pass, including full 36-pair scans
of Falco, Link, Marth, Pikachu costume 1, and Jigglypuff costume 1. Other reports use
the four-pair smoke scan. The part panel's recolour, restore, and rotation controls
were checked with actual pointer input. Its Lua workflow test additionally covers
asset binding, report refresh without moving raw selection, and expired equipment.
These checks establish the foundation; polished founders, richer traits and the
remaining delivery stages below are still outstanding.

Purpose clarified 2026-09-30: this lab supplies the visual vocabulary for the
standalone TBD roguelite. The design extension at the end of this document connects
build genetics, gameplay rules, model regions, equipment and visual expression.
That extension is a proposal, not authorization to implement the gamemode.

Build a parametric effects lab with five founder effects, smooth blending, editable
traits, and an optional genetics system. The founders use the layering and timing
techniques behind Sora's effects. Mesh morphing is outside the scope.

## Founder effects

Each founder has a recognisable silhouette and a complete charge, release, and decay sequence.

| Founder | Visual identity | Main layers |
|---|---|---|
| Solar Eruption | Gathering heat followed by a fiery eruption | Flame core, curling flames, shock ring, sparks, embers, smoke, heat distortion |
| Glacial Shatter | Frost gathers, fractures, and scatters | Frost shell, crystalline shards, fracture flashes, ice dust, mist, refraction |
| Thunder Crown | Electrical charge followed by staggered strikes | Branching arcs, bolt cores, coloured glow, charge sparks, impact rings, afterglow |
| Astral Vortex | Rotating energy gathers inward and releases | Counter-rotating bands, dark centre, inward motes, bright rim, shockwave, fragments |
| Comet Crescent | A luminous sweep with a lingering, fragmented trail | Crescent, arc echoes, streaks, stars, impact flare, expanding ring |

Existing mesh particles can supply shells, shards, and crescents. Their motion,
scale, materials, and visibility can change without morphing their geometry.
Initially, animated textures and authored sequences can supply branching arcs
and sweeps; genuine dynamic branching and arbitrary weapon-following trails are
separate runtime extensions.

## Shared traits

Controls describe visual behaviour. Each control maps to several coordinated
emitter parameters rather than exposing raw implementation fields.

| Trait | Controls |
|---|---|
| Palette | Core, body, accent, and lifetime colour progression |
| Energy | Speed, burst strength, brightness, and distortion |
| Turbulence | Texture flow and supported motion variation |
| Cohesion | Concentrated cores versus dispersed particles |
| Rhythm | Continuous emission, pulses, and clustered bursts |
| Persistence | Lifetimes, trails, and lingering aftermath |
| Structure | Contributions from cores, rings, streaks, sparks, mist, and arcs |

Artistic intensity and particle count have separate limits, so increasing Energy
does not automatically make an effect expensive.

## Blending and tweening

Establish good blending before adding genetics. Provide a founder A to founder B
slider alongside the individual trait controls.

Effects share semantic layer roles and normalised charge, release, and decay
phases. Blend corresponding layers and align their timing through these roles.

- Interpolate numeric parameters within authored ranges.
- Blend colour ramps with brightness handled separately.
- Transition different textures or shader types through coordinated layer fades.
- Introduce and remove optional layers smoothly.
- Apply emission changes to newly spawned particles while existing particles finish.
- Tween compatible live appearance parameters on active particles without abrupt resets.

Every founder pair gets an authored midpoint and adjustments where necessary.
Fire to lightning should pass through a convincing plasma effect. Blindly
averaging arbitrary effect JSON fields is not the blending strategy.

The first catalogue target is five polished founders and ten convincing unordered
pairwise blends. Multi-founder blending follows that foundation. Activation order
can matter for synergies without making the ordinary blend slider order-dependent.

Five founders yield ten distinct unordered pairs, twenty ordered pairs, and
twenty-six subsets containing two or more founders. Sliders and mutations create
a much larger parameter space, but visual quality and meaningful diversity are
the acceptance criteria. Breeding recombines authored capabilities; it does not
invent new rendering or simulation techniques.

## Genetics

Each saved effect has a genome containing:

- Founder ancestry and trait values.
- Discrete features, such as branching arcs or a double shock ring.
- A deterministic variation seed.
- Parent references and recipe/schema versions.

Breeding combines compatible trait groups from two parents and applies bounded
mutations. Keep related properties, such as burst timing and its supporting
flash, grouped where independent inheritance would break the composition.

Provide Breed, Mutate, Lock Trait, Save, and Compare. Generate several children,
preserve desirable traits, and continue breeding selected results. Mutation
strength controls variation; locks preserve chosen traits.

Paired alleles and recessive features are a later extension. The initial system
prioritises useful, controllable inheritance. Reproducibility means the same
genome, recipe/assets, seed, and playback conditions produce the same result.
Version recipes and preserve the required assets or resolved configurations so
later authoring changes do not silently alter saved favourites.

## Synergies

Blending creates an effect's appearance. Synergies describe what happens when
active effects interact. Combination rules specify ingredients, activation order,
timing window, consumption, cooldown, and resulting sequence. Result parameters
can depend on the ingredients' traits.

| Ingredients | Result |
|---|---|
| Fire + ice | Thermal shock: fracture, steam, and hot fragments |
| Fire + lightning | Plasma surge |
| Ice + lightning | Charged crystals with sequential discharges |
| Vortex + fire | Fire cyclone |
| Vortex + ice | Orbital shard storm |
| Comet + elemental field | Infused trail and impact |

Start with scripted lab triggers. Spatial detection, genuine orbital forces, and
arbitrary motion-following trails are later runtime extensions. Use priorities,
cooldowns, and explicit consumption rules to prevent reactions from repeatedly
triggering themselves.

Any gameplay consequences belong to deterministic gameplay logic, with effects
following its events. Cosmetic parameters and host performance must not decide
damage, collision, or projectile behaviour.

## Implementation structure

| Layer | Responsibility |
|---|---|
| Authoring tools | Generate original textures, existing-format meshes, founder recipes, and blend mappings |
| Expression system | Convert genomes and slider values into validated emitter configurations |
| Runtime controls | Manage individual instances, parameter tweening, playback, transitions, and cleanup |

The existing `.gfx.json` packages and `sprite`, `warp`, and `distortion` shaders
remain the rendering foundation. Explicitly identify unsupported behaviours
rather than writing configuration fields that the runtime ignores.

Relevant existing files, relative to the workspace repository:

- `tools/model_parts/make_presets.py`: current simple preset generator; starting point for reusable authoring helpers and founder recipes.
- `tools/model_parts/prepare.py`: lab installation and asset generation.
- `ports/ir/schema/effects.schema.json`: effect package schema.
- `ports/ir/tools/ultimate_vfx_geno.py`: reference for Sora's importer and effect field mapping.

Relevant files in the game checkout (the inspected checkout is `melee/worktrees/linux`):

- `pc/scripts/examples/character_parts_lab/main.lua`: existing lab controls and showcase playback.
- `pc/platform/gw_fx.c`: package loading, simulation, and lab attachment lifecycle.
- `pc/platform/gw_fx_query.h`: effect query and lab interface.
- `pc/platform/gw_script.c`: Lua API registration and bindings.
- `pc/platform/gw_fx_render.cpp`: effect rendering and live material parameter delivery.

Split reusable authoring helpers from effect recipes as their complexity grows.
Keep original generated assets distinct from imported reference content. No
disc-derived assets are to be committed.

Before adding complex sequences, fix finite-duration lab attachments and add
individual effect handles so one effect can fade, stop, or change independently.
Source inspection found the current lab attachment does not enable the runtime's
emitter-lifetime handling, so `duration` alone is insufficient on that path.
Verify the correction in the executable used for validation.

## Lab workflow

- Founder selectors, blend slider, and trait controls.
- Play, Replay, Loop, Stop, pause, and frame stepping.
- Layer isolation for inspecting composition.
- Parent/child comparison, trait locks, mutation strength, and saved favourites.
- Particle/emitter counts and frame-cost measurements.

Playback uses game frames. Editing a saved recipe is distinct from temporarily
changing a running instance. Replaying a preview should restore its known start
state and seed; cycling should allow a complete sequence to finish.

## Delivery stages

1. Foundation: instance handles, finite lifetimes, cleanup, deterministic seeds, and live controls.
2. Visual benchmark: finish Solar Eruption and Glacial Shatter.
3. Blending benchmark: complete their full slider range and Thermal Shock transition.
4. Founder catalogue: complete all five founders and ten pairwise blends.
5. Genetics: breeding, mutations, locks, lineage, and reproducible saves.
6. Advanced interactions: remaining synergies, multi-founder blends, and justified simulation extensions.

## Validation and completion criteria

Initial targets are approximately 7–12 emitters and 100–250 peak particles per
standalone founder, adjusted through measurement. Blends share a budget rather
than doubling it. These are design targets, not measured performance results.

Validate intermediate slider positions, extreme traits, repeated playback,
movement and attachment, cleanup, deterministic reproduction, and performance.
Check switching or stopping during every phase. Test multiple simultaneous
effects against the runtime's shared limits and inspect refusal/drop counters.

Use meaningful automated checks for valid generated packages, referenced assets,
bounded parameters, inheritance locks, seeded reproduction, and finite lifecycle
behaviour. Visual review must include the normal gameplay camera as well as
close-ups, so effects remain readable during play.

The first milestone is complete when two polished founders blend smoothly,
produce one convincing synergy, and support repeatable editing without leaks or
abrupt transitions. Genetics follows that foundation.

## Roguelite connection proposal — 2026-09-30

The experience: a recognizable Smash fighter develops an increasingly distinctive
combat style and appearance during a run. Player actions charge, activate and
combine powers. Upgrades change both the decisions worth making and the visible
state of the affected body/equipment regions. Entry remains Load game → Main menu
→ TBD → custom gamemode, independent of the post–Master Hand sequence. Offline.

### Research basis and limits

This is light research using publisher descriptions, contents and available
excerpts, plus the author's description of Designing Games. It is not a claim to
have read all seven books. The specific design below is our proposed application.

- [Michael Sellers, Advanced Game Design](https://www.pearson.de/media/muster/ext/9780134668239.pdf): the available interactivity chapter links player mental models, actions, feedback and cognitive load. Use this to make cause and effect legible on the fighter.
- [Elias, Garfield and Gutschera, Characteristics of Games](https://mitpress.mit.edu/9780262300445/characteristics-of-games/): compare skill, luck and reward/effort. Apply this to reward drafting and the balance between execution and build power.
- [Tynan Sylvester, Designing Games](https://tynansylvester.com/book/): systems generate experiences; mechanics and audiovisual presentation contribute to emotional meaning. Start with experiences we want, then test whether the rules produce them.
- [Salen and Zimmerman, Rules of Play](https://mitpress.mit.edu/9780262240451/rules-of-play/): emergence and information provide a foundation for making build interactions understandable.
- [Adams and Dormans, Game Mechanics](https://www.peachpit.com/store/game-mechanics-advanced-game-design-9780132946704): contents cover internal economies, Machinations, feedback, simulation and level design. Use this beside Sellers when mapping resource loops; prioritize chapters 4–8 and 10 for this project.
- [Engelstein and Shalev, Building Blocks of Tabletop Game Design](https://www.routledge.com/Building-Blocks-of-Tabletop-Game-Design-An-Encyclopedia-of-Mechanisms/Engelstein-Shalev/p/book/9781032985107): a mechanism reference, including uncertainty, economics and set collection. Consult it for specific reward/fusion problems rather than importing an entire board-game structure.
- [Schell, The Art of Game Design](https://www.routledge.com/The-Art-of-Game-Design-A-Book-of-Lenses-Third-Edition/Schell/p/book/9781315208435): evaluate a prototype through different questions and perspectives. Use as a recurring playtest review.

Suggested working order: Sellers for the system map, Sylvester for the experience
brief, Adams/Dormans for the economy. Consult the remaining works as questions arise.

### Ownership, rules and appearance

Use precise internal vocabulary, with simpler player-facing names:

| Concept | Responsibility |
|---|---|
| Gene definition | Authored capability: compatible hosts, trigger, action, parameters, limits, visuals and interactions |
| Gene instance | This copy's seed, rolled traits, upgrades, source, version and optional ancestry |
| Host | Character, logical slot, owned item, or run-wide modifier; determines scope and lifetime |
| Build | All active hosts and instances resolved together; derived rather than a second independent copy of every bonus |
| Combat role | The action family affected: pressure, movement, guard, projectile, command, etc. |
| Visual binding | Reviewed model regions, attachment anchors, optional equipment and fallback for a fighter/costume |
| Expression | Current visible state, derived from resolved traits and actual charge, activation, cooldown and status |

Every gene needs at least one reviewed visible association. One gene may affect
several regions; several genes may share one region through an explicit composition
policy. A gene's mechanical scope need not match the surface where it is displayed.
For example, a run-wide command modifier can have a small core emblem and flash the
casting hand only on use. Its display location does not limit its mechanics to hands.

User-confirmed direction — 2026-09-30: gene placement changes the ability through
authored variants. Each supported gene/placement pairing defines its trigger,
action, parameters and visual binding; moving a gene previews the resulting
behavior, not just its colour. This does not imply arbitrary combinations can
be generated safely from mesh anatomy. Start with a few reviewed placements and
show unsupported pairings as unavailable.

Use a small fixed number of logical capacity slots as a first prototype: Assault,
Traversal, Guard and Focus are working labels, not final UI. Capabilities can accept
multiple slots when placement creates a real mechanical choice. Characters get equal
capacity regardless of their raw mesh count. Item bonuses have their own explicit
budget; they do not bypass slot costs by being worn or held. Merely viewing/selecting
an inventory item never activates it.

### Model and equipment mapping

Create a reviewed per-fighter/costume binding table over the existing measured
groups. Separate recolour/material surfaces, skeleton anchors and gameplay move
tags: none is interchangeable with the others.

| Visual role | Candidate presentation | Examples requiring individual review |
|---|---|---|
| Striking | Hands, forearms, weapon edge, relevant foot for kicks | Falco hands/feet; Marth blade versus hilt |
| Traversal | Feet, lower legs, permitted tail/body accent | Falco boots; Pikachu feet/tail; compact round fighters |
| Guard/core | Torso, armor, shield, compact body accent | Link shield separately from tunic and scabbard |
| Focus | Head accessory, casting hand, small core detail | Hats, tiaras, headgear, alternate costume details |
| Equipment | Owned object's reviewed surfaces and anchors | Held sword, spawned projectile/article, temporary prop |

Review the geometry and visible states; do not infer anatomy from size alone. A
sword's blade, hilt and scabbard may have different roles; a hat may be cosmetic
rather than a gameplay item. A fighter whose attacks use a tail can map striking to
it. A broad shared mesh may require a new mask or an anchor-only accent. Do not
pretend a shader can isolate an arbitrary region inside one draw without extra data.

Bind persistent definitions to asset/costume fingerprints and stable reviewed
selectors. Resolve live IDs after spawn/equip/transform; never save raw pointers or
temporary item ordinals. Restore overrides and retire attachments on destruction,
unequip, scene change, stock loss or script failure. A missing optional surface uses
an authored fallback; a missing required weapon makes that capability ineligible
and the reason visible before selection. Partners and transformations need explicit
policies, including which entity owns charges and which entities display them.

### Combat and stat design

Preserve the value of movement, spacing, shielding, DI, edgeguards, combos and
recoveries. Build power should create new opportunities for those skills. Arbitrary
attack-speed scaling or repeated forced hitstun can destroy the interactions that
make Melee feel good, so introduce them only as deliberate later experiments.

Author every gene with: activation condition, benefit, expenditure/recovery, one
important build decision, visible states and counterplay. Start with a few loops:
pressure → charge → finisher; successful defense → stored response → release;
movement → stored momentum → committed attack. A deterministic activation condition
is easier to learn initially than a large collection of hidden on-hit chances.

Illustrative genes (all mechanics proposed, not existing APIs):

- **Cinder Drive:** eligible direct attacks earn capped heat, at most once per move
  instance. The next eligible smash hit can spend it on a short local eruption.
  Striking surfaces warm as charge accumulates; the release consumes that cue.
  Do not add a persistent third HUD meter just for this first example.
- **Rime Guard:** a successful defense earns a bounded frost charge. A subsequent
  eligible direct hit transfers a short frost mark. Guard surfaces develop angular
  accents; the mark appears on the target with a visible expiry. Avoid a general
  movement/animation slow in the first slice.
- **Thermal Shock:** a sufficiently charged fire strike consumes a frost mark for a
  brief fracture/steam reaction. Display the incoming charge and target mark before
  impact. Explicit consumption and per-target gating stop repeated self-triggering.
  Reactions do not produce more charge or count as fresh direct hits by default.
- **Later traversal candidate:** ground movement earns a bounded charge, spent on
  an attack extension rather than free invulnerability or another air jump. Test
  whether it adds movement decisions rather than rewarding running in circles.

Gene parameters include potency, charge capacity, gain, reach, lifetime, recovery
and conversion efficiency as appropriate. Do not expose every parameter on every
gene. Define units and caps: longer status lifetime may be beneficial; longer
cooldown is a penalty. A numerical increase is not universally a stat-up.

Base traits + permanent run upgrades + compatible slot/item contributions + active
temporary modifiers resolve once into effective mechanics and visual targets.
Scope modifiers explicitly to a gene instance, slot, item or the character. Removing
an item removes its contribution; a temporary penalty expires without rewriting the
inherited base. Recompute from sources instead of repeatedly multiplying live stats.
Specify additive/multiplicative order per stat family and clamp only as designed.

Offer three kinds of rewards: ordinary improvement, specialization tradeoff, and
behavior mutation. Not every reward needs a downside. Example choices for Cinder:
more stored heat; stronger release with slower recharge; or easier access to a weaker
release on a different move family. Preview the actual effective difference and
affected regions before accepting. Exact numbers remain playtest variables.

Save base genome, modifications and ancestry separately. An ordinary +potency reward
is an upgrade, not a new parent. Fusion/recombination later mixes compatible authored
modules, preserves player-locked traits and records versions/seeds. Temporary buffs
are not inherited. Explicitly classify incompatibilities, neutral combinations and
supported reactions; avoid needing custom behavior for every possible gene pair.

User-confirmed direction — 2026-09-30: support both a permanent collection/breeding
system and acquisition, upgrades and fusion during runs. Permanent individual genes
and their ancestry therefore need separate ownership/lifetime records from run
copies and run modifications; persistent progression is not limited to unlocks.
The unresolved consequence is what death, successful extraction and fusion export
back to the collection, including whether a run upgrade becomes heritable.
Proposed reversible prototype default, not approved: entering a run copies selected
collection genes without consuming the originals; failure discards run changes;
success offers one explicitly previewed collection addition. Run numerical upgrades
and temporary buffs are not inherited automatically. Keep collection breeding as
an explicit compatible-parent transaction so its inheritance rules can be tested
separately from the run reward economy.

### Visual expression and spectacle

Use a shared visual grammar: region says where the power belongs, shape/motion says
which family it is, and timing says its state. Colour supports these cues. Maintain
separate dormant, charging, ready, activation and recovery presentations. Stat-ups
must change a relevant quality: capacity may add discrete lit segments, potency a
denser core, duration a longer appropriate aftermath. Particle count is a separate
budget. Visual radius must not falsely advertise mechanical hit radius.

Give each region one dominant persistent material treatment and a small number of
compatible accents. Resolve conflicts deterministically by state and authored
priority. Save the biggest compositions for earned releases, reactions, upgrades
and major encounter moments. Preserve faces, attack silhouettes, opponent tells,
ledges and platform edges. Evaluate at gameplay distance with multiple actors;
showiness includes contrast and quiet intervals. A lower-FX setting must preserve
all gameplay information, and culled visual instances must never cancel gameplay.

The current model override is diagnostic solid fill and loses texture/cutout
detail. A production tint/emissive overlay that preserves base shading and alpha,
plus selectable surface masks where required, is a real next implementation task.
Current particle attachment and finite handles are useful foundations; arbitrary
mesh-surface emission, real weapon trails and automatic semantic anatomy are not
established by the existing demos.

### Run and command flow

First loop: choose fighter and starter → fight a short encounter → choose a reward
with a before/after fighter preview → test the new behavior → choose a route → face
a mixed challenge. Introduce optional fusion after players recognize the genes.
Use offered rewards and route choices for most early randomness, keeping activation
rules predictable. Provide a useful broad option and occasional change-of-direction
options so early rolls do not lock a run. Show mutation risks before commitment.

User-confirmed direction — 2026-09-30: combine branching combat arenas with
connected exploration/platforming. The first small run must include a traversable
connection and an authored route choice between combat encounters, with one
placement variant relevant to traversal. A combat-only sequence does not satisfy
this direction. Large seamless worlds, procedural level generation and broad
platforming content are not prerequisites; room transitions may be used initially
while maintaining a connected route and coherent run state.

Use the agreed Kingdom Hearts-style Magic / Item / Special command concept. Keep
normal combat inputs intact. Confirmed controls: D-pad left, right and down select
the three branches at the current menu node, recursively descending through
three-way forks to leaf actions. Up returns one level below the root and is
consumed there, including until that press is released so it cannot become a taunt
when returning to the root. At the root, Up retains its normal taunt. Full movement
and ordinary combat inputs remain usable. Do not require a long menu sequence
during neutral. Put detailed inventory,
gene placement and fusion between encounters; a fast preset/shortcut should handle
repeated combat use. Resource costs and startup/recovery remain real commitments.
Whether opening commands slows time remains a playtest decision, not an assumption.

Encounter design must exercise the system: pressure opportunities, shielded or
spaced opponents, recovery/edgeguard situations, and mixed targets. Avoid a final
test consisting only of a stationary damage sponge. Ring-outs and positioning
remain relevant. Persistent progression includes the confirmed collection/breeding
system as well as options, starting choices and visual variations; its raw-power
economy and inheritance limits remain open design decisions.

User decision — 2026-09-30: opponents should include varied enemy types that use
the shared gene rules, with encounter-authored modifiers that strengthen them
against the player. Fighter CPUs, custom enemies and bosses resolve compatible
gene definitions, charge, costs, upgrades and reactions through the same system;
their host bindings and available actions still require individual authoring.
Enemy modifiers must have explicit scope and visible tells. Variety should come
from behavior, gene combinations, positioning and encounter composition as well
as bounded stat changes, rather than difficulty consisting only of stat inflation.

20XX CPU logic is now a candidate rather than a confirmed integration choice: the
user raised its age and requested investigation of UnclePunch and other training
hacks before choosing a source of technical fighter AI. Training tools and skilled
opponent controllers must be distinguished in that audit; neither availability
nor integration in the current port is assumed. Custom enemies and bosses need their own
controllers; fighter CPU logic cannot be assumed to control them. All controllers
need gene action/activation support: knowing when an ability is ready, choosing
its target and committing its costs/startup/recovery. AI uses the same resolved
command action as the player without needing to navigate the player's visual
menu. Proposed default: enemies obey the same charge and activation constraints;
any encounter-specific exceptions are authored and communicated explicitly.
Reaction windows, simultaneous threats and telegraphs remain encounter tuning
choices so technical execution does not remove readable counterplay.

AI research checkpoint — 2026-09-30: newer training tools do not by themselves
establish stronger free-fighting AI. The following is a read-only review of official
project descriptions, release metadata and selected code, not a performance test.
Dates are GitHub release dates or latest default-branch commit dates checked during
the audit; recent activity alone does not establish AI quality.

| Candidate | Verified role and maintenance evidence | Native integration/source limits |
|---|---|---|
| [20XX Hack Pack](https://github.com/DRGN-DRC/20XX-HACK-PACK) | Modified fighting CPU; original Achilles library explicitly includes CPU auto L-cancel and other behavior changes. v5.0.2 released 2023-01-21; latest branch commit 2023-09-19 updates README. | Public ASM/library. The [v5 loader](https://github.com/DRGN-DRC/20XX-HACK-PACK/blob/main/Notes%20%26%20Source%20Codes/Source%20Codes/20XX%20AI%20Engine%20Loader.asm) reads `AI_Engine.bin` and patches PPC `PlayerThink_Interrupt`; native behavior needs adaptation. Complete readable v5 engine source and reuse license remain unverified. |
| [UnclePunch Training Mode](https://github.com/UnclePunch/Training-Mode) | Predefined technical practice scenarios, savestates and diagnostics; no strong general fighting policy established by its README. Latest listed release v3.0-alpha.7.2 dated 2022-05-31; default-branch commit 2021-02-16. | Public ASM/mod tooling targets patched Melee. License unresolved. Release activity and default-branch activity differ. |
| [TM Community Edition](https://github.com/AlexanderHarrison/TrainingMode-CommunityEdition) | Actively maintained expansion of UnclePunch: DI/SDI/ASDI, shield angles, counter actions, playback and recovery drills. CE-v1.4 released 2026-04-09 (notes offer v1.4.1 patch); dev1 2026-06-03; branch commit 2026-09-22. | Public C/ASM. Selected [lab CPU code](https://github.com/AlexanderHarrison/TrainingMode-CommunityEdition/blob/master/src/lab.c) handles training states such as counters, techs and recovery; this does not demonstrate strong open-ended neutral. Native adaptation required; license unresolved. |
| [SmashBot](https://github.com/altf4/SmashBot) | Actual combat policy organized into strategies, tactics and input chains. Author documents Fox-only local VS through libmelee/Slippi. Branch commit 2024-05-16. | Public Python, GPL-3.0. Emulator observation/controller dependencies need a native bridge or port; roster limited. |
| [Slippi-AI / Phillip II](https://github.com/vladfi1/slippi-ai) | Author describes human-replay imitation followed by self-play RL, offers a 12-character medium-v2 model, and documents 18+ frame delay. Branch commit 2026-09-23. These capabilities were not independently benchmarked here. | [Code is MIT licensed](https://github.com/vladfi1/slippi-ai/blob/main/LICENSE). Documented play uses Slippi/Dolphin; native observation/input adapters are additional work. Model-weight redistribution terms were not inspected. |

Official feature/release references: [TM-CE README](https://github.com/AlexanderHarrison/TrainingMode-CommunityEdition/blob/master/README.md),
[TM-CE releases](https://github.com/AlexanderHarrison/TrainingMode-CommunityEdition/releases),
[20XX releases](https://github.com/DRGN-DRC/20XX-HACK-PACK/releases),
[UnclePunch releases](https://github.com/UnclePunch/Training-Mode/releases), and
[Slippi-AI README](https://github.com/vladfi1/slippi-ai/blob/main/README.md).
20XX Tournament Edition is separate: its [official FAQ](https://www.20xx.me/faq.html)
documents random DI/tech and shield-holding practice, not advanced training tools.

Local `tools/release/notes/0.1.0.md` and `tools/release/README-user.txt` explicitly
say TM-CE and 20XX discs boot but their special features are unsupported;
`tm_lite` is a smaller stand-in. Loading a patched disc does not establish native AI
support. No project, model or game content was downloaded during this audit.

Proposed selection gate: keep the foundation undecided; inspect Slippi-AI for
general combat, TM-CE for readable technical/recovery behaviors, and 20XX as a
known behavior baseline. Establish one native observation → decision → controller
input interface, verify source/model reuse terms, and compare one fighter at normal
speed on recovery reliability, technical execution, neutral decisions, latency and
readable counterplay before committing to broader integration. This is a proposed
future validation gate, not authorization for downloads or implementation.

All enemies still use the shared gene resolver. Ordinary combat can naturally
activate passive triggers, but none of these projects documents awareness of our
new charges, mutations or commands. Modified reach/knockback may invalidate vanilla
policy assumptions. Deliberate gene targeting/spending requires additional policy
and observations, possibly retraining for learned agents; custom enemies and bosses
remain separately authored controllers.

### Reuse in-engine menus, HUD and notifications

User direction — 2026-09-30: make better use of existing in-engine menus and toast
popups. Reuse the current kit's panels, list rows, typography, icons, dialog and
toast art rather than building another UI framework. Verified script drawing
primitives are `gd.kit.panel`, `gd.kit.button`, `gd.kit.list`, `gd.kit.text` and
`gd.kit.icon` (`docs/scripting.md`, Kit UI). They draw presentation; selection,
navigation and acceptance still need the roguelite's small controller/state layer.
Use these panels for reward comparisons and before/after stat/region previews,
equipment choices, route choices and later fusion confirmation, chiefly between
encounters. Keep command selection compact during combat.

Use concise notifications for pickups, accepted upgrades or downgrades, meaningful
stat changes, equip/unequip, fusion results, newly discovered synergies and enemy
elite mutations. Show the actual consequence, for example a changed charge cap
or a new reaction, rather than only an effect name. Persistent build state and
readiness belong in the HUD and body/equipment expression; hits, charge increments
and repeated procs do not each produce a toast. Enemy mutation notifications
introduce the change; the enemy's ongoing tells must remain readable afterward.

Existing native `gw_Overlay_Toast` stores a single message and timestamp
(`melee/pc/platform/gw_overlay.cpp`); `gw_Overlay_GetToast` exposes it for 2.5 seconds
only while the diagnostic overlay is enabled. It is evidence of working toast
plumbing, not yet a player-facing roguelite notification service. The kit already
authors toast/dialog layout and `toast_in` / `toast_out` motion
(`menu/pipeline/kit_ui.py`, `menu/out_kit/dialog_layout.json` and
`menu/out_kit/kit_motion.json`). A script toast wrapper and production presentation
independent of the diagnostic overlay are not verified; add only the narrow bridge
needed by the chosen implementation, reusing these assets and conventions.

Apply a small explicit notification policy: urgent enemy mutations outrank routine
pickups; combine related stat changes from one reward/equip/fusion transaction;
collapse duplicates and apply a repeat cooldown to recurring notices. Bound any
pending messages and discard stale low-priority notices so rewards cannot flood
combat or hide a fresh threat. Show one concise toast at a time in a reviewed safe
area, preserving fighters, ledges, command selection and HUD readability. Exact
durations, priority values and cooldowns are playtest defaults, not a request for
a generalized notification framework.

### Resolution, limits and evidence

One authoritative event carries resolved gameplay data to both combat and
presentation. Shader brightness or spawned particle count never determines damage.
Use separate deterministic streams for combat outcomes and cosmetic variation.
Give events attack instance, source host, target and reaction lineage identifiers
so a multi-hit move, simultaneous trade, projectile or reflected article has defined
ownership and cannot recursively trigger itself without an explicit rule.

Measure damage, knockback and launch-angle changes separately. More knockback can
make a combo harder while improving kill power, so a single DPS score is inadequate.
Track resource earned/spent/wasted, activation opportunities taken, time spent in
commands, deaths/recovery failures, encounter outcomes, reward choices and visual
readability. Attribute changes to the rules the player actually used.

Allow exciting temporary power spikes with costs in timing, positioning, charge or
capacity. Put bounds on recursive procs, infinite defense/recovery and guaranteed
control loops. Simulations can find arithmetic runaway; real matches must establish
whether movement and decisions remain fun. Offer a respec/test opportunity early
enough that experimenting is affordable.

### Implementation sequence and gates

1. **Association prototype:** review Falco's first regions and contrast them with
   Marth's weapon and Pikachu's compact anatomy/accessory. Build a debug resolver
   showing host → gene → gameplay role → visual binding. Do not map the whole roster
   before proving three structurally different fighters.
2. **One complete gene:** implement one verified combat trigger, its resource and
   upgrade/downgrade resolution, and production surface treatment. Test on/off,
   charge/release, temporary modifier expiry, save/load and object lifetime.
3. **Two genes and one reaction:** Cinder/Rime/Thermal Shock are candidate content.
   Verify direct-hit versus shield-hit rules, multi-hit gating, order/consumption,
   cooldown, real damage ownership and clear visual state. These are proposed rules
   to prototype, not an assertion that the FX names already implement them.
   Verify the same gene on an enemy host, including controller activation and
   readable charge/release cues. Audit 20XX integration separately from custom
   enemy/boss controller support before promising the broader opponent roster.
4. **A short playable run:** TBD entry, a small permanent collection with one
   compatible breeding recipe, run copies/acquisition and one compatible fusion,
   three short encounters, reward previews, one prepared command and a final mixed
   challenge. Include one gene with two authored placement abilities and a connected
   traversal section with a branching arena route. Add simple +/− upgrades and a
   meaningful alternate specialization. Run it at normal game speed. Build these
   as incremental slices: prove combat/placement first, then collection/breeding
   and run fusion, then connect the encounters through traversal/route selection.
5. **Broaden only after playtest:** more fighters/slots, compatible item hosts,
   additional traversal genes, fusion/locks, further effects and encounter variety. Author the
   next founder because it serves a mechanic or needed visual role. Five founders
   and every pairwise visual blend are no longer a prerequisite for a playable slice.

Acceptance questions: Can players identify the active region, readiness and reason
for a proc? Can they explain why an upgrade changed their next combat decision?
Do at least two builds produce distinct strategies across different encounters?
Does the fighter still feel controllable and recognizable? Does removing/destroying
equipment restore the correct state? Are mechanics identical with particles culled?
Do fully stacked effects stay readable at gameplay distance? Is there a desirable
reward choice that is not simply the largest number?

Open decisions for the first playtest: final slot count/names, exact stat ranges,
resource terminology, command navigation/slowdown, run length and failure economy,
collection export on victory/death, heritable versus run-only upgrades, breeding
costs/parent consumption and permanent power limits. Collection/breeding plus run
acquisition/fusion, authored placement abilities and connected traversal with
branching arenas are confirmed directions, not open either/or choices. None needs
a full genetics simulator before the first incremental combat loop can be tested.

### Validation contract for the confirmed playable slice

User instruction — 2026-09-30: remember to test it all. The matrix below is planned
validation, not recorded pass evidence. Existing parts-lab checks documented in
`tools/model_parts/README.md` validate their diagnostic tools only; they do not
prove roguelite gameplay, production tint, AI or persistence. Record each result
with build/disc/mod configuration, test procedure, expected/actual behavior and
relevant log/capture. Mark unrun and unavailable checks explicitly.

| Area | Required check and observable acceptance |
|---|---|
| Stat resolution | Meaningful unit invariants for modifier order/caps and upgrade/downgrade polarity; removing equipment or expiring a penalty restores the source-derived value without drift. Repeat equip/remove and recomputation. |
| Placement variants | Move one gene between two supported placements; verify the authored trigger/action and effective parameters change, the preview agrees and old bindings/actions disappear. Reject unsupported placements with a visible reason. |
| Collection and breeding | Breed compatible permanent parents under the selected policy; verify seeds, ancestry, trait locks, compatibility and parent ownership/consumption. Run copies cannot accidentally mutate their permanent originals. |
| Run acquisition and fusion | Acquire and upgrade a run copy, fuse a compatible pair and reject an incompatible pair. Verify costs, source ownership, selected inheritance and preview against resulting mechanics; temporary effects never silently become base traits. |
| Saves and failure | Round-trip collection, run copies, modifications, ancestry and scene state; test restart, stock loss, run failure and victory/export under the documented policy. Verify charge and controller bookkeeping after supported state loads. Test malformed/unsupported schema handling without overwriting a valid collection. |
| Shared player/enemy genes | Run the same definition on player and enemy hosts. Verify direct versus shield hits, multihits, simultaneous trades, projectiles/reflection and source/target ownership where supported. Demonstrate bounded reaction chains, no unintended charge from reaction hits and correct consumption/cooldown. |
| AI adapter | Record legal observations and emitted inputs/actions; compare the same encounter to its unmodified vanilla CPU baseline. Verify ordinary movement/recovery remains functional and gene activation obeys charge, target, startup/recovery and costs. Separate scripted training routines from demonstrated general opponent behavior. |
| Connected route and arenas | Traverse a connected section, choose each branch and enter/exit its arena. Confirm run genes, stocks, rewards and enemy ownership persist as intended; retired attachments and stale targets do not survive transitions. Exercise platform/ledge/recovery and failure paths, not only room launch. |
| Commands and notifications | Use a real controller to test left/right/down, repeat presses, selection/activation and any return gesture at normal speed. Verify combat inputs remain usable. Test reward/placement/equip/fusion previews and notification priority, coalescing, repeat cooldown and elite mutation tells under simultaneous events. |
| Regions and object lifetime | Inspect production texture/alpha-preserving treatment, two placement regions, accessories, supported costumes and owned equipment. Unequip/destroy an item, respawn and change scene; expired IDs must fail safely and normal rendering must restore. Exercise missing-binding fallback/rejection. |
| Normal-speed gameplay and camera | Play complete encounters and both routes at normal simulation speed with the intended game camera and multiple actors. Capture charging, ready, release, recovery, fusion/upgrade and elite mutation states at gameplay distance. Verify faces, opponents, ledges, platform edges and HUD remain legible; lower FX/culled particles preserve mechanics and information. No turbo validation substitutes for these checks. |
| Build and platform integration | Build the touched native/script interfaces and run relevant native ABI checks plus Linux gameplay coverage. Run Windows build/CI and applicable runtime checks when available; report unavailable platform coverage as a limitation. Use existing appropriate checks rather than claiming a script smoke test establishes cross-platform correctness. |

Minimum complete-slice acceptance: enter through Main menu → TBD, select a starter
from a permanent collection, demonstrate one compatible breeding transaction,
play a short connected run with a branching arena route, acquire/upgrade/fuse run
genes, use two mechanically different placements and a prepared command, and face
a gene-bearing opponent plus a contrasting enemy controller. Demonstrate normal
speed victory and failure, the documented persistence/export policy and restoration
after save/load. The HUD/body/menu/toast feedback must agree with resolved mechanics.
Required checks above must have recorded results for the implemented slice; a boot,
scene-launch or automated smoke pass alone cannot count as complete.

Completion blockers must be named concretely: an unresolved inheritance/export
policy, unverified combat trigger/ownership semantics, missing production region
treatment, unavailable controller integration, absent connected-route behavior or
failed persistence/lifetime checks blocks the corresponding claim. An unavailable
Windows runner is a reported coverage limitation, not an invented Windows pass.
Any temporary fallback must be described with its affected acceptance check; do not
silently replace a confirmed feature with a diagnostic demo.

### Dungeon and stage generation research

Research checkpoint — 2026-09-30, read-only audit plus primary-source research.
Recommendation: generate the route/objective graph first, realize it with authored
side-view room templates and typed connectors, then validate directed fighter
movement and progression. Both exploration and combat arenas remain requirements;
a top-down maze or arena-selection menu alone does not satisfy this direction.

**Available pieces and limits.** Current source has more runtime support than older
research notes report. `melee/pc/platform/gw_script_model_api.inc` implements and
`gw_script.c` registers `gd.model_load/spawn/move/set/despawn` and
`gd.stage_bounds`. Spawning imports a model's collision sidecar unless
`collision=false`; `floor_flags` overrides pass-through/ledge flags. Bounds are
read-only here: there is no setter in `l_stage_bounds`. The documented
`gd.stage_add_line/platform` path adds real offline-match collision, with oriented
floor/ceiling/wall segments, drop-through floors and optional grabbable ends.
This establishes bounded runtime assembly, not unrestricted world generation.

`melee/pc/scripts/examples/bf_interior_room/README.md` and `scripts/main.lua`
describe a fixed open-front layout: 43 placements from 19 models, including floor
segments, stairs, ramp, balcony, floor opening, doorway/window/solid walls, door
leaf, returns/corners, beams/posts, trims and glass. Sidecars are committed; mesh
and atlas binaries are generated and uncommitted. The revised glass/mirrored
layout is explicitly not yet built/run; older opaque layout tests are historical
evidence only. Wall/door scenery has no collision (`bf_wall_doorway_4m.coll.json`
has `lines: []`); a visible doorway is not an implemented entrance, physical gate
or transition. The ramp sidecar supplies a sloped floor. Interior joins explicitly
disable ledges in the example; seam traversal still needs gameplay verification.

`melee/pc/gameworld/script_model.h` allows 128 live model instances and 32
collision lines per asset; `script_game.c` caps added lines at 200, further limited
by the base stage's spare collision capacity. Budget the active room and connectors,
including temporary gates, before instantiation. This fixed room alone uses 43
instances. Scene-end cleanup exists; same-scene room switching needs explicit
despawn/reference handling and safe fighter placement. No dungeon generator,
typed gameplay sockets or gameplay room-transition controller was found in the
reviewed kit. Kit HUD/menu art is presentation, not traversable world geometry.

The older `_build/stagec/Program.cs` DAT/OBJ tool and `docs/DEVLOG.md` §§30–33
describe valid DAT round-tripping but invisible grafted meshes and failing
replacement collision. Do not assume that older offline compiler can bake the
runtime kit into arbitrary working stages. The current GXMS/atlas/collision-sidecar
export path (`melee/pc/assets_src/bf_interior/export_kit.py`) is the relevant
prototype path; rebuilding and normal-speed validation are still future work.

**Algorithm comparison and primary references.** These suitability assessments
are project-specific inferences, not claims that an external generator handles Melee.

| Method | Appropriate use here | Main limitation |
|---|---|---|
| Mission graph / graph grammar | Critical path, arena/reward/traversal roles, key-before-lock dependencies and optional branches before geometry. Dormans separates mission and spatial generation in [Adventures in Level Design](https://pcgworkshop.com/archive/dormans2010adventures.pdf). Start with a few explicit graph rewrite rules rather than a large grammar engine. | Abstract connectivity does not prove jumps, return routes or room packing. |
| BSP | Reserve non-overlapping room rectangles within a bounded side-view layout; optional packing stage. [libtcod BSP documentation](https://python-tcod.readthedocs.io/en/latest/tcod/bsp.html) exposes recursive splitting with minimum dimensions/aspect controls and seeded random input. | Rectangular partitioning does not produce useful combat space or fighter-reachable vertical links automatically. |
| Spanning-tree maze plus selected loops | Cheap connected route skeleton; an explicit stack/backtracker is simple. [Jamis Buck's original explanation](https://weblog.jamisbuck.org/2010/12/27/maze-generation-recursive-backtracking) describes visiting unvisited neighbors and backing up. Add authored shortcuts/loops after dependency validation. | Long winding routes and dead ends can become tedious; undirected graph edges are not bidirectional Melee movement. Avoid literal narrow maze corridors. |
| Socket modules / WFC | Typed room connectors first; optionally use adjacency constraints for local compatible piece variants or decoration after reserving the route. [Original WFC repository](https://github.com/mxgmn/WaveFunctionCollapse) documents adjacency propagation and possible contradictions. | Matching local edges does not establish global progression or jump reachability; bounded retries/fallback required. Full WFC is unnecessary for the first room catalogue. |
| Movement-model validation | Treat room landing surfaces and exits as a directed graph with tested action edges. [Tanagra](https://ojs.aaai.org/index.php/AIIDE/article/view/12379) combines planning/constraints and a player movement model to ensure playability in its own platformer. | Its guarantees do not transfer to Melee; derive our own profiles and validate real engine behavior. |

**Minimal hybrid contract.** Each authored room needs stable ID/version, local
origin/grid units, visual bounds versus collision, floor/ledge/seam policy,
entrance/exit sockets (position, facing, safe landing area, clear height, direction),
supported mobility profiles, camera/KO envelope, encounter/spawn safe zones,
recovery space, trigger/gate ownership and model/line/draw budgets. Initially author
a traversal lane, spacious arena, branch/reward room and return/shortcut connector.
Existing doorway art needs a gameplay socket/trigger and actual barrier if locked;
it cannot gate movement by appearance. Do not mirror/rotate collision-bearing
pieces freely: the API can reject transforms that reverse collision kinds.

Generate a small explicit critical path and optional reward branch, with a loop
only when it preserves progression. Separate RNG streams for topology, room
variants, encounters/rewards and cosmetics; save seed, generator/catalogue versions,
resolved room IDs/transforms and progression state, not only a seed. Stable ordering,
bounded attempts and a known valid authored fallback make failed generation
reproducible. No retry should silently replace exploration with disconnected arenas.

Check progression over `(room/socket, keys, retained capabilities, gate state)`,
not just room IDs. Place keys before their locks; consumable keys require resource
accounting, and shortcuts must not bypass mandatory gates. Gene gates should first
be optional reward routes. Any required capability must be guaranteed, affordable
and retained through the gate and return route: selling, swapping or losing its
equipment cannot strand the player. Include an escape/reset route that does not
consume a unique progression resource. One-way drops need a verified forward exit
or recovery/reset policy; respawn/checkpoint location must remain reachable.

Use conservative, empirically measured mobility profiles for admitted fighters
and supported stat penalties, including jump height, horizontal travel, clearance,
landing margin, drop-through and recovery behavior. Validate travel in both
directions where backtracking is required. Base completion routes should support
the least capable admitted profile without advanced tech or random proc activation;
alternate ramps/platforms/transport can provide an authored accessibility fallback.
Optional skill routes can demand more, with clear tells and a safe return. Arena
templates need spacing, platform/ledge recovery and readable attacks; traversal
clearance alone cannot validate combat.

**Phased gates.** (1) Inventory/export and run the existing revised room; measure
seams, slopes, collision, camera/KO bounds and budgets with contrasting fighters.
(2) Author two connected traversal spaces and one arena, plus typed sockets and
door/gate transitions; prove normal-speed entry, safe landing, return, checkpoint
and cleanup. Until a bounds-setting/streaming contract is implemented and tested,
keep layouts inside existing bounds; scene transitions are a separate authored
integration task, not a presumed API. (3) Generate only this catalogue from a
seeded graph, reject invalid progression/movement/budgets before spawn, and use a
known valid fallback. (4) Broaden rooms, loops, locks and gene gates after the
connected slice passes; add BSP packing or WFC variation only for a demonstrated need.

Validation should cover many replayable seeds and catalogue combinations, directed
mobility/progression checks, unavailable-key and removed-gene cases, spawn overlap,
pool exhaustion/failure cleanup, scene/save/load reconstruction and same-seed output.
Replay sampled movement edges in the real engine and human-test at normal speed
with different fighters, penalties and a real controller. Check camera framing,
unintended KOs, getting launched through exits, gate fights, return routes and
arena readability. Record rejection/fallback rates and failing seed/version;
connected graphs or simulation success alone are not evidence of enjoyable or
softlock-free gameplay. This section is a plan, not implementation or a claim of
complete stage-piece sufficiency.
