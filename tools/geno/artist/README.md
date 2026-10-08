# Geno artist pipeline: Blender project to a playable `base: "none"` fighter

One command from a `.blend` to a fighter you can walk, jump, hit, shield and grab with, in an isolated test mods folder:

```text
python -m tools.geno.artist new  my-fighter --key my-fighter --name "My Fighter"   # starter .blend + fighter.json (headless Blender)
   ...model, rig, animate in my-fighter/my-fighter.blend...
python -m tools.geno.artist build my-fighter/fighter.json                        # export -> validate -> convert -> build -> install
```

`build` prints the command that opens it in the LAB. Rules, limits and who enforces them: [`docs/geno-artist-spec.md`](../../../docs/geno-artist-spec.md).
What to animate: [`docs/geno-artist-checklist.md`](../../../docs/geno-artist-checklist.md) and the generated [`docs/geno-artist-rows.md`](../../../docs/geno-artist-rows.md).
Plan and gap assessment: `docs/superpowers/plans/2026-10-08-geno-artist-pipeline.md`.

## What you need

Python 3.10+ with `numpy`, `scipy`, `Pillow`; the .NET 8+ SDK and the HSDLib checkout (`experiment/tooling/HSDLib`, see `SETUP.md`) for `fighterbuild`
(or `GW_FIGHTERBUILD=<fighterbuild.dll>`); the game checkout in `GW_MELEE` (the Striker move set and the `geno-lab` mod are copied from it);
Blender 4.2+ (tested 5.2.2) only for `new`, for `build` from a `.blend`, and to author. A player needs none of this. No disc is read.
`BLENDER=<blender.exe>` overrides the lookup.

## Commands

| command | does |
|---|---|
| `new DIR --key K [--name N] [--params params.json]` | headless Blender writes `DIR/K.blend` (parametric starter) and `DIR/fighter.json` |
| `validate fighter.json [-v] [--json]` | blockers/warnings with the object, bone, vertex or action and the fix; exit 1 on a blocker |
| `build fighter.json [--out DIR] [--export] [--strict]` | [0] export the glb from `art.blend` if stale, [1] validate, [2] plan/mesh/bank, [3] models, [4] moves + `geno.json` (+ `geno check`), [5] install into `<out>/mods` |
| `run-command fighter.json` | the LAB launch line |
| `clips [--tier ...] [--markdown]` | the clip checklist |
| `python -m tools.geno.artist.proof_report LOG` | summarise a scripted run (`proof.lua`) |

Outputs go to `<workspace>/_build/artist/<key>/` (override with `--out` or `fighter.json` `output`): `build/` (plan, models, bank, `build-report.md`) and
`mods/` (`geno-lab/`, `<key>/`, `enabled.txt`). Point `MELEE_MODS_DIR` at `mods/` and nothing else is touched: no file in the game checkout is written.

## The starter (`blender/`)

`make_starter.py` builds, from a parameter file, a rigged, textured, animated character that already passes every check:

- the **export skeleton** (31 bones, named exactly like their roles, `.L/.R`; sockets and anchors are labelled bones: `item_socket.R`, `grab_anchor`, `victim_anchor`,
  `camera_focus`, `shield_origin`, `reflect_origin`, `absorb_origin`, `head_top`), A-pose, Z up facing -Y;
- a one-mesh body of primitives weighted with at most 2 influences, a packed 160x160 texture, one material;
- **13 example actions** written against roles, readable as templates (`actions.py`): `Wait WalkMiddle Run JumpF JumpAerialF Fall Landing Guard GuardOn Attack11 Catch CatchWait ThrowF`;
  the jab's strike pose is on frame 3, the grab's on 6, as the default moves expect;
- **adjustable proportions** (`skeleton.DEFAULT_PROPORTIONS`: leg, torso, neck, head, arm lengths, shoulder/hip width, foot length, thickness, head and torso size), **bone names**
  (`names`: role -> your name) and colours: see `ports/geno-artist-samples/pip/params.json` (a short, big-headed character with its own bone names).

Everything the importer needs is stored in the file: the armature's `geno` property (roles, costumes), `geno_loop`/`geno_hit_frames`/`geno_rows`/`geno_root_motion` on actions.

`export_fighter.py` (also run by `build` when `art.blend` is set) first checks the Blender project (unapplied transforms, unapplied modifiers, more than one skinned mesh or material,
more than 2 weights or no weight on named vertices, missing roles, wrong facing, actions that key bones that do not exist), then exports the glb with the right settings
(NLA tracks, always-sampled, Y up, extras) and writes `<glb>.geno.json`. `geno_panel.py` is the same as a **Geno** sidebar tab: Validate, Export, Export + Build + Install, set a bone's role,
mark the hit frame. `control_rig.py` bakes your own control rig onto the export skeleton (spec section 8).

## Build -> preview -> iterate

1. `build` (a few seconds). Read the printed findings: blockers stop; warnings and `build-report.md` list placeholders.
2. Run the printed `run-command` line from the workspace root (the LAB, Mario as P2). INSPECT mode (`S` skeleton, `J` joint numbers), HITBOXES (`B`, `L`), FRAMES (`Q`/`E` scrub).
3. **Restart the game after every rebuild.** The define (`geno.json`, `plan.json`, models, bank) is read once at start (geno.md 22).
4. Scripted check: `proof.lua` via `tools/geno/moves_check/run_scene.sh` (idle, walk, run, jump, jab, shield, grab, throw) and the existing `tools/geno/moves_check` (40 move scenarios).

## Files

| file | role |
|---|---|
| `model.py` | derives bones, roles, clips, rows, costumes from the glb + `fighter.json` (+ sidecar, extras) |
| `validate.py` | the checks and their wording |
| `convert.py`, `hurt.py`, `loco.py` | plan/mesh/bank, hurtboxes, measured locomotion speeds |
| `assemble.py` | moves retargeted by role, `geno.json`, `mod.json`, `files/` |
| `pipeline.py`, `__main__.py` | the commands |
| `spec.py`, `data/` | limits, roles, the 351-row clip table (`gen_clip_table.py` regenerates it), 46 default attributes |
| `blender/` | starter, example actions, exporter + preflight, panel, control-rig bake, self-test |
| `proof.lua`, `proof_report.py` | the scripted in-game check |
| `test_artist.py` | unit and integration tests (`python -m pytest tools/geno/artist`) |

The Courier (`ports/vanilla-original/fighter.json`) goes through the same code and reproduces its previous model, bank and plan bit for bit (the one deliberate difference: `plan.json`
`roles` uses canonical role names, which the engine does not read). Its hand-kept `manifest.json` is only used for its 351-row map (`clips.legacy_manifest`); new characters need none of it.
