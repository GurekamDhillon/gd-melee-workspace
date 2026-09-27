# Ultimate Kirby proof of life

**Current status:** this folder is being expanded into a full native Kirby
port. The movement/side-B LAB probe passed 19/19, a separate normal-attack
LAB probe passed 25/25 (24 ftcmd rows plus LAB startup), and the throw timeline
probe passed 5/5; grab windows pass 3/3; and Final Cutter's rising sword
hitboxes pass 3/3. These checks cover
their named mechanics, not the full fighter.
An explicitly staged m-ex slot now spawns in LAB (5/5 with both stock and
experimental visuals). Its native Hammer hold/release probe passes 14/14,
Stone/composed-fighter probe 16/16, and live Final Cutter input probe 12/12
in the isolated `kirby_native` build. The native slot and Hammer builder are
still staged separately from this default overlay runner.
The model and 20 converted motion rows are experimental: clean paired captures
still show missing face detail and disappearing limbs in some poses. See
[FULL_PORT_PLAN.md](FULL_PORT_PLAN.md) for the remaining completion gate.

This pack attaches to Melee Kirby and applies movement values from the locally built *Ultimate*
13.0.2 Kirby IR. It covers walk, dash/run, crouch, ground jump, and five aerial jumps. Crouch and
action transitions use Melee Kirby's existing logic; the Ultimate IR supplies movement parameters.
Jump heights are converted to approximate Melee launch speeds, and the five aerial impulses retain
Melee Kirby's decreasing per-hop ratios. The generated `source-manifest.json` records every mapping.

The pack also replaces Melee Kirby's **uncharged ground and aerial side B hitbox scripts** using
Ultimate IR events. Ground side B has two 19% fire hitboxes at active frame 12. Aerial side B has
two 16% fire hitboxes at frames 12 and 26. Both use Ultimate's 78 KBG and 60 BKB. Ground and
aerial release animations come from Ultimate's c00 clips. Melee Kirby still supplies the hammer
model, offsets, sound, cleanup, and action logic in this overlay. A separate
native-slot prototype implements Hammer charge, hold-walk and weak/full release;
the Ultimate hammer article and remaining state/visual fidelity are still being ported.

The default runner now also installs Ultimate-derived hitbox timelines for 24
normal-attack rows: jab, dash attack, angled tilts and forward smashes,
up/down tilts and smashes, five aerials, get-up attacks, ledge attacks, and
pummel. Down air's five multihits and finisher are expanded from the source
loop. LAB checked each installed row's
active frames and damage. Four throws also have Ultimate absolute damage,
knockback and release frames, checked in a separate LAB timeline. Their host
victim animations and other status behavior still need conversion, as do
grab-box geometry, pivot grab, special hitbox flags, and matching attack motion.
Rapid jab's separate row now has the source eight pulses per 16-frame loop and
eight input-exit checks. Melee ftcmd stores whole-percent damage, so the loop
uses two 1% pulses and six 0% pulses per cycle, the closest whole-percent total
to Ultimate's eight 0.2% hits. Its archive/loop tests and a live LAB input
probe pass 4/4, including loop entry and release into the finisher.
The default runner also installs Ultimate Final Cutter's rising sword hitboxes
in ground and air up-B script rows. Its LAB timeline passes for both rows;
the native slot also reaches the up-B states and spawns a wave with Ultimate
travel values and 5%/6% hitbox phases. A ranged LAB hit dealt 6% once after
clearing Melee's inherited 16-frame repeat timer. Source collision policy,
the wave's appearance, and Ultimate up-B physics still need review.

The experimental visual pack retargets Ultimate Kirby's c00 body, arms, feet and open-eye atlas onto
Melee Kirby's existing 46-joint costume tree. An eye-mesh candidate is under visual test. It converts 20 Ultimate body clips for idle, walk,
dash/run, ground and five aerial jumps, fall, crouch transitions, and side B release. The converter
removes Ultimate's cumulative root travel from physics-driven walk/run clips; otherwise the model
snaps backward when a loop restarts. Dash keeps Melee's native root travel. Facial variant
switching, Ultimate's collision body, and its status system remain open. These
conversions are structurally valid but still require pose and face fixes.

The local IR is `experiment/character-ir/instances/kirby.ultimate.ir.json`, built from extracted
Ultimate data by `experiment/character-ir/tools/build_kirby_ultimate.py`. Its movement entries
include decoded `fighter_param_motion.prc` values, and its special/projectile
data has 115 typed fields from Kirby's `vl.prc`. It identifies eight symbolic
articles without inventing numeric indices. The readable ACMD events came from a public dump and
have not been binary matched to the local 13.0.2 `lua2cpp_kirby.nro`.

## Build and play in the LAB

From the workspace root on Windows, with `.env` pointing `GW_ISO_ACE` at your own ACE disc:

```bash
tools/port/build.sh
bash ports/kirby-ultimate/run.sh
```

The runner rebuilds the local mod from the IR and Melee Kirby baseline, installs the locally
derived model and animations, adds the LAB script, and opens Kirby directly in LAB on Final
Destination. It stays open until you close the game. The mod is generated under
`_build/tmp/ultimate-kirby-mods/`; its modified `PlKb.dat`, `PlKbAJ.dat`, and `PlKbNr.dat` are
never committed. P1 is the player and P2 is a Fox CPU. The LAB starts in model-only Inspect mode
so the hitbox overlay does not cover the costume; switch LAB modes to inspect side B hitboxes.

The derived costume and animation archives are cached under `_build/tmp/ultimate-kirby-model/`
and `_build/tmp/ultimate-kirby-anims/`. Rebuild them after converter changes with
`bash ports/kirby-ultimate/run.sh --refresh-visuals`. The local Ultimate extraction and ignored
Melee baseline assets are required. See [model/README.md](model/README.md) and
[animations/README.md](animations/README.md) for the source mapping and converter details.

The native prototype can be left open for an interactive LAB session with
`bash ports/kirby-ultimate/run_native.sh`. It uses the isolated `kirby_native`
game build and defaults to the locally staged, ignored
`_build/tmp/ultimate-kirby-additive-lab/mods` pack. This adds Ultimate Kirby
at m-ex internal 59 / external 65, retains eight costume slots, and preserves
Lucina, Brawl Kirby, and Brawl Meta Knight. The three existing fighters each
spawned opposite Ultimate Kirby in LAB, with 6/6 checks per run and no fatal
errors. The additive pack alone passed the host's 186/186 headless checks.
With the older Brawl and Meta Knight packs also mounted, one pre-existing
headless check fails because their seventh costume rows refer to Melee Kirby's
`PlKbLa.dat`; their normal costumes spawned in the coexistence LAB runs.
Pass `--mod-dir PATH` for another additive pack. An older pack that replaces
Lucina requires both `--mod-dir PATH` and `--replace-lucina`, so the runner
checks that displacement explicitly. It stays open until you close the game.
The current costume and animation conversion still need visual fixes.

For the automated LAB gameplay probe:

```bash
python -m unittest discover -s ports/kirby-ultimate/tests -v
bash ports/kirby-ultimate/run.sh --probe
bash ports/kirby-ultimate/probe/run_normals.sh
bash ports/kirby-ultimate/probe/run_throws.sh
bash ports/kirby-ultimate/probe/run_grabs.sh
bash ports/kirby-ultimate/probe/run_final_cutter.sh
bash ports/kirby-ultimate/probe/run_rapid_jab.sh
```

The probe uses an idle human P2 and logs `ultimate-kirby movement RESULT` to
`_build/runs/ultimate-kirby-probe/melee-pc.log`. It checks live movement states and positions,
all six jumps, `gd.timeline` side B scripts, and live ground and aerial fire hitboxes. The
2026-09-25 LAB run passed **19/19** checks. This is a playable proof on Melee Kirby's fighter
slot, not a full transfer of Ultimate's article, collision, facial, or status systems. LAB gameplay
checks establish action and hitbox behavior; model and motion appearance also need direct visual
inspection.

The separate normal-attack LAB run logs `ultimate-kirby normals RESULT PASS (25/25 checks passed)`
in `_build/runs/ultimate-kirby-normals-probe/melee-pc.log`.
The throw LAB run logs `ultimate-kirby throws RESULT PASS (5/5 checks passed)`
in `_build/runs/ultimate-kirby-throws-probe/melee-pc.log`. It reads the active
script timelines; a live grab/throw regression remains necessary.
The grab-window LAB run logs `ultimate-kirby grabs RESULT PASS (3/3 checks passed)`
in `_build/runs/ultimate-kirby-grabs-probe/melee-pc.log`. Standing and dash grab
active/clear frames match the source; grab-box geometry and pivot grab remain.
The Final Cutter LAB run logs `ultimate-kirby final-cutter RESULT PASS (3/3 checks passed)`
in `_build/runs/ultimate-kirby-final-cutter-probe/melee-pc.log`. It checks ten
source rising-hitbox events on both the ground and aerial up-B rows.
The isolated native-slot live up-B log is
`_build/agents/kirby_native/runs/ultimate-kirby-cutter-live/melee-pc.log`
(12/12): real ground/air inputs reach the up-B states and expose 5%/2% sword
hitboxes. A separate native trace verified ground and air cutter-wave item
spawns with speed 4.8, lifetime 19, brake 0.28 and the 5%/6% phases. The
range-collision run at
`_build/agents/kirby_native/runs/ultimate-kirby-wave-hit-v2/melee-pc.log`
recorded one 6% item hit on Fox (exit 0, FATAL 0). The remaining projectile
collision and visual differences are recorded in the native pack manifest.
The separate rapid-jab live log is
`_build/runs/ultimate-kirby-rapid-jab/melee-pc.log` (4/4): real A presses
reach the loop, expose both encoded pulse damages, and release to the finisher.
The native Inhale/copy LAB matrix passed nine live swallow, copy, and copied
neutral-B checks for each of the 25 reachable Melee opponents (excluding the
Kirby target); the per-opponent logs are under
`_build/agents/kirby_copy/runs/ultimate-kirby-copy-<id>/`.
