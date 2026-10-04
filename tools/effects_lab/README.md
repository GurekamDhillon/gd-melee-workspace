# Fire/ice effects prototype

This is the first implementation slice of
[`EFFECTS-LAB-PLAN.md`](../../docs/EFFECTS-LAB-PLAN.md), with Solar Eruption,
Glacial Shatter, a continuous fire/ice crossfade, and a Thermal Shock sequence.
Recipe version 2 installs the 16 approved original textures from
`menu/out_effects_study` for the existing sprite, warp and distortion shaders.
Installation verifies the review manifest SHA-256 hashes; it does not regenerate
or alter the approved PNGs. Vector-field G is swizzled into runtime A for the
renderer's R/A distortion convention. Asset anchors remain authoring hints;
particles currently use centered pivots. The full founder catalogue and genetics are not implemented.

From the workspace repository in Git Bash. Source comes from `GW_MELEE` or
`melee`; installed packages use `GW_BUILD_ROOT` or `_build` by default:

```sh
python3 tools/effects_lab/prepare.py --enable
MELEE_SCRIPT_DATA_DIR="$(pwd -W)/_build/scripts-data" bash tools/port/run.sh effects-lab --iso /path/to/melee.iso
```

Falco loads on Final Destination with a neutral virtual P4 controller. Click
**Loop** for repeated sequences, or **Replay** for one sequence. The blend slider
uses the two selected founders; other controls adjust lightness, energy, shader
distortion, sprite size, density, lifetime and layer balance. Layer isolation is
the button below the sliders. These controls are narrower than the final plan's
semantic traits.

Edits tween an active preview over 12 game frames. Editing an expired preview
replays it; editing Thermal Shock starts the ordinary blend preview, whose
emitter layout matches the controls. Stop fades the current instance and disables
looping. Pause/Step inspect game frames. Game Camera switches from the panel's
close framing to normal gameplay framing. Thermal Shock consumes/fades the
current preview and starts a bounded reaction with a 90-game-frame cooldown.

Save/Load stores settings and the seed in
`_build/scripts-data/effects_lab_main/favourite.lua`. The save includes
a recipe version but not resolved assets, so it is reproducible only while that
recipe version and its pinned assets remain unchanged. Version 1 favourites are
rejected, since version 2 changes the artwork. This is a prototype
favourite, not the planned immutable genome format.

Preparation without `--enable` only installs the mod. `--restore` restores the
previously backed-up enabled-mod list. To return to the character-part panel:

```sh
python3 tools/model_parts/prepare.py --iso /path/to/melee.iso --fighters falco --interactive --no-scan --showcase
```

## Validation

```sh
python3 -m unittest discover -s tools/effects_lab -p 'test_*.py'
MELEE_TEST_FILTER=fx bash tools/port/run.sh --test fx-tests --iso /path/to/melee.iso
```

Use `prepare.py --enable --validate` for nine bounded runtime capture cases;
completion must say `complete recipe=2` and match the run ID from that validation
configuration. Refusal counters are tracked throughout each case, emission must
be nonempty, phase captures must occur, and the instance must clean up completely.
`--loop` starts interactive looping; ordinary preparation resets validation mode.

Four authoring/Lua workflow tests and two native FX tests pass. The native checks
cover finite lifetimes, seeded reproduction, ownership, bounded controls, and
preserving existing fighter/article timing. Recorded runtime checks cover five
blend positions, Thermal Shock, and three cases at the gameplay camera. They
reached 107–173 particles, then returned to zero particles and emitters with no
refused emissions. Those counters establish execution and cleanup, not polished
artistic quality or GPU-only frame cost.

The panel has also been checked with actual compositor pointer input and
screenshots: loop, endpoints, midpoint and Thermal Shock. The stats box sits above
the preview rather than covering Falco. The larger plan's first artistic milestone
remains open; there are no mesh shells, general synergy rules, remaining founders,
breeding, or immutable asset-backed saves yet.

## Native visual tour

The installed catalogue has seven character-part presets, two founder prototypes,
one fire/ice blend, one scripted reaction and two immediate-release gameplay
variants: 13 packages using three shared particle shader modes. These are not
13 independent shader algorithms or a completed five-founder catalogue.

Capture them with the existing native binary, separate mods/data/card/settings
and attack-disabled, intangible fixed-position fighters:

```sh
python3 tools/effects_lab/capture_tour.py --iso /path/to/melee.iso
python3 tools/effects_lab/showcase.py
```

The first command requires exclusive game/GPU use for the approximately
30-second capture run. It never enables or rewrites the normal profile's mods
or roguelite save. Screenshots and emission/cleanup evidence land in
`_build/effects-tour-profile/data/effects_tour_main`. Inspect every screenshot
for framing before building with `showcase.py --reviewed`. The resulting
`_build/effects-showcase/index.html` starts paused; use arrows or Play tour.

The tour labels native cosmetic attachment captures, source texture previews
and illustrative build art separately. Joint/region attachment suggestions
are design direction; current reviewed body tint coverage and unsupported
transient-equipment/partner bindings are described explicitly. The current
renderer treatments are sprite, warp, distortion and texture-preserving
fighter-part tint. Thunder Crown, Astral Vortex, Comet Crescent and the other
nine founder-pair blends are still proposals.
