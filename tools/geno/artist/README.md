# Geno artist pipeline: Blender project to a playable `base: "none"` fighter

One command from a `.blend` to a fighter you can walk, jump, hit, shield and grab with, in an isolated test mods folder:

```text
python -m tools.geno.artist new  my-fighter --key my-fighter --name "My Fighter"   # starter .blend + fighter.json (headless Blender)
   ...model, rig, animate in my-fighter/my-fighter.blend...
python -m tools.geno.artist build my-fighter/fighter.json                        # export -> validate -> convert -> build -> install
```

For the complete human walkthrough, start with [Author a fighter](../../../docs/learn/author-a-fighter.md)
(2026-10-10; source-checked, not run end to end).

`build` prints the command that opens it in the LAB. Rules, limits and who enforces them: [`docs/geno-artist-spec.md`](../../../docs/geno-artist-spec.md).
What to animate: [`docs/geno-artist-checklist.md`](../../../docs/geno-artist-checklist.md) and the generated [`docs/geno-artist-rows.md`](../../../docs/geno-artist-rows.md).
Gameplay authoring (attributes, states, hitboxes, fighter Lua, online identity and the built Pip special):
[`docs/geno-fighter-guide.md`](../../../docs/geno-fighter-guide.md).
Plan and gap assessment: `docs/superpowers/plans/2026-10-08-geno-artist-pipeline.md`.

## What you need

Python 3.10+ with `numpy`, `scipy`, `Pillow`; the .NET 8+ SDK and the HSDLib checkout (`experiment/tooling/HSDLib`, see `SETUP.md`) for `fighterbuild`
(or `GW_FIGHTERBUILD=<fighterbuild.dll>`); the game checkout in `GW_MELEE` (the Striker move set and the `geno-lab` mod are copied from it);
Blender 4.2+ (tested 5.2.2) only for `new`, for `build` from a `.blend`, and to author. A player needs none of this. No disc is read.
Tool paths use [the shared authoring-tool config](../../port/TOOLS_CONFIG.md): `GW_BLENDER` in the environment or `.env`, then the local `_build/tools.json`, then discovery. `BLENDER` remains a compatibility alias.

## Commands

| command | does |
|---|---|
| `new DIR --key K [--name N] [--params params.json]` | headless Blender writes `DIR/K.blend` (parametric starter) and `DIR/fighter.json` |
| `validate fighter.json-or-DIR [-v] [--json]` | blockers/warnings with the object, bone, vertex or action and the fix; exit 1 on a blocker |
| `build fighter.json [--out DIR] [--export] [--strict]` | [0] export the glb from `art.blend` if stale, [1] validate, [2] plan/mesh/bank, [3] models, [4] moves + `geno.json` (+ `geno check`), [5] install into `<out>/mods` |
| `build fighter.json [--out DIR] --gameplay-only` | rebuild gameplay against unchanged cached art; check before replacing the fighter package |
| `run-command fighter.json` | the LAB launch line |
| `joints fighter.json` | the joint numbers the LAB shows (INSPECT `J`) with bone name, role, Melee part and parent: the key to hitbox `joint=N`, `gd.joints` and sockets |
| `clips [--tier ...] [--markdown]` | the clip checklist |
| `python -m tools.geno.artist.proof_report LOG` | summarise a scripted run (`proof.lua`) |

Outputs go to `<workspace>/_build/artist/<key>/` (override with `--out` or `fighter.json` `output`): `build/` (plan, models, bank, `build-report.md`) and
`mods/` (`geno-lab/`, `<key>/`, `enabled.txt`). Point `MELEE_MODS_DIR` at `mods/` and nothing else is touched: no file in the game checkout is written.


`build --gameplay-only` reuses the last full build's plan, models, animation bank and measured speeds. It accepts changes to `attributes`, `jumps`, `moves` and the display `name`; it validates a staged package before replacing the installed fighter and preserves the LAB and `enabled.txt`. It never starts Blender or fighterbuild. A full build writes `build/gameplay-cache.json`; existing outputs without that cache, or changed art/clip configuration, need one full build before this path is available.

Play either mode with `python tools/geno/play.py --project fighter.json --lab [--clip ROW]` or `--vs cpu`. `--rebuild` runs only this cached gameplay path when the package is stale. Use `--mods-dir <out>/mods` for a custom output that is not declared in the config.

## The starter (`blender/`)

`new` writes the `.blend` and `fighter.json`; the first `build` exports `art.glb`. Until that export, `validate` reports the exact `run: python -m tools.geno.artist build <fighter.json>` recovery command, including quotes for paths with spaces. It also accepts the containing directory.

`make_starter.py` builds, from a parameter file, a rigged, textured, animated character that passes the Blender checks and validates after export:

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
(NLA tracks, always-sampled, Y up, extras) and writes `<glb>.geno.json`. Failed exports show separate Blender stderr/stdout tails; a missing output is a failure even if Blender exited 0. Every blocker and warning includes a repair. `geno_panel.py` is the same as a **Geno** sidebar tab: Validate, Export, Export + Build + Install, set a bone's role,
mark the hit frame. `control_rig.py` bakes your own control rig onto the export skeleton (spec section 8).

## Build -> preview -> iterate

1. `build` (content-dependent; the 2026-10-10 audit recorded 11 s for a small starter). Read the findings: blockers stop; warnings and `build-report.md` list placeholders. Large animation banks take minutes; see the tutorial's measured full Goku build.
2. Run the printed `run-command` line (or `python tools/geno/play.py --project fighter.json --lab`) from the workspace root (the LAB, Mario as P2). INSPECT mode (`S` skeleton, `J` joint numbers), HITBOXES (`B`, `L`), FRAMES (`Q`/`E` scrub).
3. **Restart the engine process after every rebuild.** F8 / `gd.hot_reload()` refuses native defines; restarting only the match keeps the animation-bank cache. Workbench **Rebuild + reload** performs a build plus a process restart, then restores the selected row/frame.
4. Scripted check: `proof.lua` covers the default movement/jab/shield/grab/throw set via `tools/geno/moves_check/run_scene.sh`. The existing 40 move scenarios are tuned to the Courier/Striker move set; adapt selectors and expectations for another fighter. They are not acceptance coverage for arbitrary custom moves.

Generated hurtbox capsules are proposals to inspect in the LAB. The generated
`plan.json` ECB proposal is **not read by the engine** today; collision still uses
the donor offsets. There is no hurtbox/ECB editing panel.

To install the artist sidebar for a session, open `blender/geno_panel.py` in
Blender's Text Editor and press Alt+P. Set **Repo folder**, **fighter.json** and
**glb** to your project; the GLB field must match `art.glb`. Blender preflight
results are in **Geno Report**, build output in **Geno Build**. The artist panel
and Workbench are separate add-ons; a generic editable Workbench source adapter
is not generated by `new`.

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
