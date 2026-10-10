# Author a fighter: Blender to a landed hit

**As of 2026-10-10.** This is the start-to-finish path for an original fighter with
today's artist tools. Commands, APIs and current add-on labels were checked against
source; this walkthrough has **not been run end to end**. Controls marked **new**
describe the intended Workbench hitbox flow being built, not controls verified in
the current add-on. This dated guide supersedes older authoring claims in packets
04–09; those packets remain unrun outlines.

You will make `tutorial-fighter`, build its own model and animation bank as a
`base: "none"` define, watch its jab in Blender, move a hitbox, and test contact in
the LAB. The starter supplies a Striker-derived move set and fallback animations;
finishing the fighter still means replacing and checking those placeholders.

## 1. Prepare the tools and make the starter

Complete [SETUP](../../SETUP.md) first. You need Windows, a working game executable
and your own Melee disc image for playtesting; Python 3.10+, NumPy, SciPy and Pillow;
Blender 4.2+; and the .NET/HSDLib `fighterbuild` setup for converting models.
Creating and building the original art reads no disc.

Open **Git Bash at the workspace root**. The commands below use that shell.
Configure your local environment before starting Blender:

| Setting | What to configure |
|---|---|
| `GW_MELEE` | Your game checkout, if it is not the default `melee/` |
| `BLENDER` | Blender executable for the artist CLI, if it is not on PATH |
| `GW_BLENDER` | Blender executable for the Workbench launch helper |
| `GW_LAUNCHER` | Qt launcher executable with Workbench support |
| `GW_QT_BIN` | Qt runtime directory for that launcher |
| `GW_ENGINE_EXE` | Working game executable for the Workbench helper to copy |
| `GW_ISO_VANILLA` | Your locally configured disc image; keep it private |

If these settings are in your local `.env`, export them to child processes:

```bash
set -a
source .env
set +a
python -m pip install -r tools/geno/requirements.txt
python -m pip install numpy scipy Pillow
python -m tools.geno.artist new authoring/tutorial-fighter --key tutorial-fighter --name "Tutorial Fighter"
```

**Expected:** `created ...tutorial-fighter.blend and ...fighter.json`, followed by
`next: python -m tools.geno.artist build ...`. The directory contains the starter
blend and its configuration. It does not yet contain the exported GLB.

**If it fails:** `Blender was not found` means set `BLENDER` to your executable.
`make_starter failed` includes a Blender output tail; fix that failure before
continuing. Use a new destination/key for a second fighter so you keep the first.

**Timing:** the authoring audit recorded 1.6 s for a starter; tool installation is
extra. Do not run CLI validation yet: it reads the GLB, which the next steps export.

## 2. Model and animate in Blender

In Blender, **File > Open** the new `tutorial-fighter.blend`.
To enable the artist sidebar without installing an add-on, switch an area to
**Text Editor > Open**, choose `tools/geno/artist/blender/geno_panel.py`, and press
**Alt+P** once. In the 3D View, press **N > Geno > Geno fighter**.

Set the panel fields:

| Field | Value |
|---|---|
| `glb` | `//art/tutorial-fighter.glb` |
| `fighter.json` | `//fighter.json` |
| `Repo folder` | Workspace root, selected with the folder picker |
| `Python` | Your Python executable, or `python` if available to Blender |

The panel's default GLB name is `fighter.glb`; change it to match the
`art.glb` in your configuration.

Select the skinned mesh in the Outliner, **Tab into Edit Mode**, and change its
silhouette with **G** or **S**. Keep one skinned mesh, one material, UVs and at most
two bone influences per vertex. Keep the export skeleton's role assignments.

For the first move, select the armature, enter **Pose Mode**, and use
**Dope Sheet > Action Editor > Attack11**. Adjust its strike pose at frame 3 and
key the changed bone transforms. Keep the recovery frames. The starter has 13
template actions, including idle, movement, jump, shield, jab, grab and throw.

Use **Mark hit frame** (`geno.mark_hit`) at the strike if you change it. This
stores action metadata; it does not automatically move the gameplay hitbox window.
For a renamed bone, select the active bone, enter its canonical role in **Role**,
then click **Set role of active bone** (`geno.set_role`). This artist-panel field
is currently free text. Save with **Ctrl+S**.

**Expected:** your edited model and jab remain rigged; the sidebar is visible.
Click **Validate** (`geno.validate`), then open the **Geno Report** text block to
read Blender preflight findings. This check works before exporting.

**Typical fixes:**

| Finding | Fix |
|---|---|
| `OBJECT_TRANSFORM` | Select mesh and armature in Object Mode; **Object > Apply > All Transforms** |
| `MESH_COUNT` / multiple materials | Join skinned pieces with **Ctrl+J**, then use one material |
| `INFLUENCES` | **Weight Paint > Weights > Limit Total**, set 2, then **Normalize All** |
| Missing/unknown role | Restore the canonical role spelling and the bone mapping |
| Missing action / wrong pose | Select the intended action and keep its keyed recovery |

**Timing:** modeling and animation depend on the work; no measured authoring time
is available. The [clip checklist](../geno-artist-checklist.md) and
[row map](../geno-artist-rows.md) show what to replace after the jab.

## 3. Export, validate and build the playable package

Click **Export glb** (`geno.export`). Expect `Exported ... (N actions)` and
`art/tutorial-fighter.glb` plus its `.geno.json` sidecar.
Then run:

```bash
python -m tools.geno.artist validate authoring/tutorial-fighter/fighter.json
python -m tools.geno.artist build authoring/tutorial-fighter/fighter.json
python -m tools.geno.check _build/artist/tutorial-fighter/mods/tutorial-fighter
python -m tools.geno.report _build/artist/tutorial-fighter/mods/tutorial-fighter --frames
python -m tools.geno.artist joints authoring/tutorial-fighter/fighter.json
```

Alternatively, **Export + Build + Install** (`geno.build`) performs the export
and artist build; its captured output is the **Geno Build** text block.

**Expected:** validation lists findings without blockers. Build prints stages
`[0/5]` through `[5/5]` (or skips a current export), then `OK in N s` and a
`Preview (LAB)` command. The checker prints
`OK: Geno fighter package and mod metadata validated` with a reminder that
gameplay still needs LAB checks. The report lists rows and static frame windows.
`joints` prints joint number, bone, role, Melee part and parent.

Outputs are:

```text
_build/artist/tutorial-fighter/
  build/build-report.md
  mods/enabled.txt
  mods/geno-lab/
  mods/tutorial-fighter/
    mod.json
    geno.json
    moves/
    files/
```

Read `build-report.md`: it names warnings and placeholder clips.
`enabled.txt` should contain `geno-lab` and `tutorial-fighter`.

**If it fails:** give `validate` the **fighter.json file**, not its directory;
a directory currently produces a misleading `Permission denied` LOAD error.
A missing GLB on a fresh starter means **Export glb**, or run `build`, which
exports it first. Missing `fighterbuild`/.NET/HSDLib dependencies belong in
[SETUP](../../SETUP.md). Blockers stop the build; `--strict` also stops on warnings.
If Blender crashes and the build shows no useful tail, run the exporter directly
to see its full output:

```bash
blender --background authoring/tutorial-fighter/tutorial-fighter.blend --python tools/geno/artist/blender/export_fighter.py -- --out authoring/tutorial-fighter/art/tutorial-fighter.glb
```

Use your configured Blender executable if `blender` is not on PATH.

**Timing:** the audit recorded about 11 s for a fresh small starter build.
Large banks cost much more; see step 7. These are content builds, not engine builds.

## 4. Open your jab in Workbench in Blender

The artist CLI does not create a Workbench project. For this tutorial, save these
two text files beside your source `fighter.json`.

`authoring/tutorial-fighter/workbench.json`:

```json
{
  "schema": "workbench/1",
  "id": "tutorial-fighter",
  "mod_id": "tutorial-fighter",
  "gameplay": "gameplay.json",
  "plan_abs": "_build/artist/tutorial-fighter/mods/tutorial-fighter/files/plan.json",
  "art_blend": "authoring/tutorial-fighter/tutorial-fighter.blend",
  "rebuild": [
    "python", "-m", "tools.geno.artist", "build", "{project}/fighter.json"
  ]
}
```

`authoring/tutorial-fighter/gameplay.json`:

```json
{
  "moves": [
    {
      "name": "jab",
      "motions": [44],
      "tag": "jab",
      "pick": {"clip": "Attack11"}
    }
  ]
}
```

These fields use the current project parser; motion 44 is the artist row table's
`Attack11`. This is a **playback project**: it has no editable `script` entry.
It does not connect Workbench hitbox edits to the artist importer. That source
integration still needs a project-specific build adapter.

Save and close your authoring Blender window. From the same configured terminal:

```bash
python tools/blender/geno_workbench/launch_goku.py --project authoring/tutorial-fighter --art authoring/tutorial-fighter/tutorial-fighter.blend --mods _build/artist/tutorial-fighter/mods --work _build/workbench-tutorial-fighter --row jab --frame 3
```

Despite its name, this existing helper accepts those project/art/mods/work
overrides. Set the `GW_*` executables above explicitly: some of its defaults
are specific to its original developer setup. It copies the engine into the
chosen work directory, starts a headless server and bootstraps a fresh Blender
preview. It registers the add-on without a permanent install.

**Expected:** `starting launcher --serve ...`, `WB_SERVE port=N`,
`starting Blender ...`; the **Geno** sidebar has Connect, Timeline, Problems,
Hitbox, Splice and Fighter panels. The helper connects, loads the fighter and
selects `jab`. Closing that preview stops its server and engine.
Do not save the posed preview over your authoring blend.

For a manual session, follow the [add-on installation](../../tools/blender/geno_workbench/README.md#install),
then **Geno > Connect**: select **Project**, **Launcher**, **Engine exe**,
**Mods dir** (the parent containing both mods), and **Disc image** using the pickers;
click **Start server**, then **Connect**. Choose **Timeline > Move > jab**.
In **Fighter**, click **Load Fighter** (`geno_wb.load_fighter`);
**Calibrate** and **Verify Pose** show mapping and pose diagnostics.

**If it fails:** `missing ...` identifies a path setting; Qt DLL failures need
`GW_QT_BIN` or the launcher's deployed runtime. Check
`_build/workbench-tutorial-fighter/blender.log` and
`_build/workbench-tutorial-fighter/engine/melee-pc.log`.
`workbench.json not found` means Project is the wrong directory.
A missing role map requires the generated plan; missing mapped bones require
matching art or explicit `art.bone_aliases` in `workbench.json`.
If a port already has a server, confirm it is your intended project before
connecting. Read the status line when a control is disabled.

**Timing:** the measured headless engine restart-to-ready was 1.0–1.3 s.
Blender launch, rig import and first frame caching are extra and were not measured.

## 5. Use rows, Play and the hitbox panel

In **Timeline**, select **jab** in **Move**, set **Frame**, and click **Play**
(`geno_wb.play`); click **Pause** to stop. Use **-1 / +1**, **Speed**, **Loop**
and **Show travel**. Workbench Frame is an engine logic frame, separate from the
Blender scene timeline. The UI is capped at frame 600; **>|** seeks to that cap,
not the clip's last frame. Playback stops or loops at the known move length.

**Expected:** the posed fighter and live overlays follow the engine frames.
If Play is disabled, connect and load a row/frame first. If the pose does not
update, inspect the Fighter mapping and the status/log for a frame-hook error.

For this starter, **Hitbox** says **No source hitboxes for this move.** That means
the playback project has no source script; it does not mean the running jab
cannot hit. Use this current fallback to move its first hitbox: merge the following
`moves` object into your source `fighter.json`, preserving its other fields.

```json
{
  "moves": {
    "hitboxes": {
      "jab1": {
        "0": {"joint": "hand.R", "size": 4.0, "x": 0, "y": 0, "z": 0}
      }
    },
    "delay": {"jab1": 1}
  }
}
```

This is a fragment to merge, not a replacement configuration. `jab1` is the
starter script stem; `0` is its first hitbox occurrence. Use the bone **name**
printed by `artist joints` if you renamed `hand.R`. Size and offsets are
joint-local Melee units. `delay` adds a positive startup delay using the current
artist retargeter. These overrides handle joint, size, offsets and delay;
new scripts, damage/angle changes and extra hitboxes need maintained package
sources and their own build driver, as described in the
[fighter guide](../geno-fighter-guide.md#a-repeatable-lab-authoring-loop).
Never keep source edits only inside the generated mod: the next artist build
replaces it.

### New: intended hitbox editing flow for a wired project

**Being built; not verified in the current add-on.** An editable Workbench project
needs each row's `script` to name a maintained `.genoasm` and its `rebuild`
command to assemble/install that source. Adding the two playback files above
does not supply that adapter.

Once the new controls and a wired project are available, the intended clicks are:

1. **Timeline > Move**, select the move, then **Hitbox**, select a source hitbox.
2. Choose its bone role in the **role dropdown**; for example `HAND_R` resolves
   the plan's `hand.R`. Set Damage, Size, X/Y/Z, Angle, KBG, FKB, BKB and the
   start/end frames.
3. Click **Add** to create a hitbox or **Delete** to remove the selected one.
4. Click **Apply**, then **Run checks**, then **Rebuild + reload**.

Today's wired-project editor already has the numeric fields, a free-text **Bone**
field, **Suggest limb** (`geno_wb.suggest_bone`) and **Apply**
(`geno_wb.edit_hitbox`). The dropdown/Add/Delete are the **new** part; no current
operator names are claimed for them. Apply edits source and shows
**Source edited: rebuild + reload needed**; overlays still depict the old build.

**Typical fixes:** an unknown role needs the plan mapping; `changed externally`
means reopen/reconnect the project after the hand edit. Missing source boxes need
a row `script` and build adapter. Add/Delete change script length, so expect a
restart after rebuilding. Placement gizmos and a generic artist-to-Workbench
hitbox adapter are not established by this tutorial.

**Timing:** field changes are source edits; seeing them in game costs the rebuild
and restart in step 7. No dropdown/Add/Delete interaction timing is verified.

## 6. Run checks and understand the result

Click **Problems > Run checks** (`geno_wb.run_checks`). Select a problem and click
**Go to problem** to return to its row/hitbox. A completed check reports
`checks: N problem(s)` and restores your selected row/frame.

**Expected for the playback-only starter:** `swing_without_hitbox` is possible
because the declared jab has no source script to analyze. This identifies the
source integration gap; use package checks and the LAB to judge the actual jab.
A clean list would not prove its gameplay windows. Wired projects can additionally
report `wrong_limb`, `below_floor`, `duplicate_clip` and
`grounded_clip_on_aerial`.

**If disabled:** connect first; `no_roles` requires a plan with canonical roles.
A source change can precede the engine change, so rebuild and run checks again
before accepting the result. **No problems listed. Run checks to refresh.**
is an empty-state message, not evidence that checks passed.

**Timing:** checks sample engine rows/frames; no measured duration is available.
The [package checker](../../tools/geno/README.md) covers file/schema/script errors,
not visual correctness, contact or the feel of the move.

## 7. Rebuild + reload, with the right time budget

For the starter's saved JSON edit, click **Hitbox > Rebuild + reload**
(`geno_wb.rebuild_reload`). Its configured command is the artist build.
Expect **rebuilt and reloaded**, the same selected move/frame, fresh overlays
and a cleared rebuild-needed marker. Run checks again.

If the button is disabled, Project needs a nonempty `rebuild` argv.
A failed build leaves the old frame and stale marker visible: read the error,
fix the source and retry. **Restart engine** restarts without building;
it cannot compile your source change.

The existing Goku build driver has a separate fast path. For a prepared Goku
project, the exact commands are:

```bash
python ports/goku-xv2/tools/build.py --fighter _build/goku-xv2/author-source/fighter.json --auto
python ports/goku-xv2/tools/build.py --fighter _build/goku-xv2/author-source/fighter.json --gameplay-only
```

These are **Goku-project commands**, not flags accepted by `tools.geno.artist`.
Its Workbench config already uses `--auto`: current art uses gameplay-only;
changed art, animation inputs or a missing full-build stamp use a full build.
An explicit `--gameplay-only` refuses stale/missing Stage A output; run a full
build first. Fast builds retain gameplay auditing and static package checks,
but omit the ground audit. Do not skip audits to make the loop appear faster.

| Round trip | Time and evidence |
|---|---|
| Small artist starter build | About 11 s, recorded in the authoring audit |
| Gameplay-only Goku hitbox edit + restart | About 15 s, reported for the implemented fast path; not remeasured here |
| Gameplay reapply alone | 3.5–3.7 s, measured Stage B |
| Full Goku package, 725 clips | 278.0–295.4 s, about 5 min; measured with GLB already current |
| Of that full build, Stage A | 244.2–257.9 s; bank conversion dominates |
| Engine restart-to-ready | 1.0–1.3 s in headless Workbench; Blender/UI work is extra |

The [hot-reload note's Measurements section](../../_research/hot-reload-2026-10-10.md#measurements-2026-10-10-measurement-lane-no-code-changed)
supersedes its earlier unmeasured estimates. The
[authoring audit](../../_research/authoring-tools-audit-2026-10-10.md) records the
starter and reported fast-path timings. Large animation/model edits use the
full build; a stale GLB adds export time not included in those measurements.

**Native defines require a process restart.** F8 / `gd.hot_reload()` refuses
them with `native definitions require a process restart; current data kept`.
Workbench reload performs that process restart. Restarting only the match does
not reread a changed animation bank: the measurement explicitly tested that.
Numeric hitbox edits kept word counts in the measurement; adding a hitbox added
five words. Neither observation makes native-define F8 reload available.

## 8. Land the hit in the LAB, then inspect the clip

Close the Workbench preview. Print and run the artist's LAB command:

```bash
python -m tools.geno.artist run-command authoring/tutorial-fighter/fighter.json
```

Paste its printed line into Git Bash at the workspace root. It sets
`MELEE_MODS_DIR` to the mods **parent**, and uses
`mode=lab;p1=geno:tutorial-fighter/hu;p2=mario/cpu0;stage=fd` with `run.sh`.

**Expected:** your fighter and Mario appear on Final Destination in the LAB.
The run's log is `_build/runs/tutorial-fighter-lab/melee-pc.log` under the
default build root. Check it for mounted `geno-lab`, your fighter key and
`geno:` warnings. A missing fighter usually means the wrong mods parent,
missing `enabled.txt`, or a failed/incompatible package; read the log first.

Focus the game window. Press the **backtick/tilde key** to open the console,
enter `lab mode hitboxes`, then close the console with the same key.
In HITBOXES, **B** toggles hit/hurtboxes, **L** labels and **E** the ECB
(off by default). **Space** pauses/resumes; **Right/Left** step forward/back.
Use **lab mode inspect** and **J** for joint numbers, or
**lab mode frames** and **Q/E** to scrub the timeline.
Close the console before using LAB hotkeys.

Walk within jab range of Mario using your configured controller, face him,
then press **A** with the stick neutral. Pause and step through startup,
contact and recovery; confirm the hit sphere is on your hand, Mario takes
damage, and the jab exits correctly. Use a fighter-alone run for frame timings:
contact hitlag stretches an opponent-in-range measurement.

For a console-driven jab, type these on separate console lines:

```text
pause
input 1 A 1
step 1
step 8
= gd.release_pad(1)
```

Start from idle within range. Expect a jab and a damage event if it contacts
Mario. `input` claims P1, so release it before returning to your physical pad.
If there is no contact, fix spacing/facing first, then inspect joint, size,
offsets and active frames. Do not use a static timeline as proof of a landed hit.

For animation study, enter these console commands:

```text
lab mode clips
lab clips find Attack11
lab clips play Attack11 1
```

Expect a listed clip/move and playback. If the name is absent, choose the exact
row/name printed by `find`; do not substitute Workbench's `jab` row id.
CLIPS is pose-only: it previews animation without running the move script.
Its source-move entries chain animation events through the same preview API;
they also do not execute gameplay. Use the LAB input test above for contact.

In a clip preview, **Space** pauses, **Left/Right** step one frame,
**Page Up/Page Down** step -10/+10, and **Home/End** select first/last frame.
On a controller: **D-pad Left/Right** -1/+1, **Up/Down** +10/-10,
**Y** pause/play, **X** first, **Z** last. Enter `lab clips stop` to leave
the preview. The Atlas pause menu is opt-in: console `lab ui on`, then
close the console and press **Escape**; the fallback menu remains available.

**Timing:** measured engine-ready time is about a second in headless Workbench;
visible LAB launch and these manual checks have no measured total. Keyboard,
controller, GUI layout and this starter's contact still need a human walkthrough.

## 9. Iterate from the source

Return to your authoring blend or `fighter.json`, make one change, save,
export/build, restart the process and repeat the same jab test.
For a wired Workbench project: edit source, Apply, Run checks,
Rebuild + reload, Run checks again, then repeat LAB contact and CLIPS pose checks.

Keep these boundaries in view:

- Change source `attributes`/`jumps` in `fighter.json` for this starter.
  LAB INSPECT's attribute comparison is read-only.
- Generated hurtbox capsules are proposals; inspect them in HITBOXES.
  The artist's `plan.json` ECB proposal is **not read by the engine** today;
  editing it does not change collision. There is no hurtbox/ECB authoring UI.
- `Mark hit frame`, clip preview and static frame reports do not replace a
  gameplay test. A very short recovery clip can end before a later hitbox opens.
- LAB exports go to the run's `scripts-data/`, not back to your source.
  Saved states may refuse changed fighter identities; recreate the baseline.
- Effects, sound and presentation still require source files/build tooling;
  this workflow does not provide audition or generic presentation-art panels.
- Keep disc-derived files out of commits and shared packages. The original
  starter art is yours; any source-game port data needs a separate provenance check.

The goal for this pass is modest and observable: your model loads, its jab
plays, the edited hand hitbox contacts Mario, and another rebuild repeats it.
Use [the fighter guide](../geno-fighter-guide.md) for new states and fighter Lua.

## Source checks for this walkthrough

| Names/behavior | Source checked |
|---|---|
| Artist CLI and emitted LAB command | [CLI](../../tools/geno/artist/__main__.py), [pipeline](../../tools/geno/artist/pipeline.py) |
| Artist clicks, role/hit metadata | [panel](../../tools/geno/artist/blender/geno_panel.py), [actions](../../tools/geno/artist/blender/actions.py) |
| Artist overrides, generated files, ECB limit | [assembler](../../tools/geno/artist/assemble.py), [hurtboxes](../../tools/geno/artist/hurt.py) |
| Workbench clicks and current operator ids | [panels](../../tools/blender/geno_workbench/panels.py), [operators](../../tools/blender/geno_workbench/operators.py), [fighter operators](../../tools/blender/geno_workbench/operators_fighter.py) |
| Project fields, rows and check coverage | [project](../../tools/release/launcher/qt/workbench/project.cpp), [data](../../tools/release/launcher/qt/workbench/geno_data.cpp), [checks](../../tools/release/launcher/qt/workbench/checks.cpp) |
| Generic launch overrides, rebuild and restart | [helper](../../tools/blender/geno_workbench/launch_goku.py), [session](../../tools/blender/geno_workbench/api.py), [rebuild command](../../tools/release/launcher/qt/workbench/commands_save.cpp) |
| Fast-path flags and stale-input gate | [Goku build driver](../../ports/goku-xv2/tools/build.py) |

The read-only game sources checked were `pc/platform/gw_script.c` registration
tables and console dispatch, `pc/platform/gw_console.cpp` for the console key,
`pc/platform/geno_registry.c` for define reload refusal, and
`pc/geno/mods/geno-lab/scripts/lab.lua` for LAB/CLIPS commands and keys.
No API or Add/Delete operator is inferred from an unimplemented control.
