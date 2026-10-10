# Geno Workbench Blender add-on

Geno Workbench requires Blender 4.x. Its pure Python modules use the standard
library. The add-on communicates with the workbench server at `127.0.0.1`;
project edits are workbench tool calls.

The add-on provides connection controls, rig and pose inspection, editing,
timeline controls, splice authoring and independent playtesting.

## Install

Copy `tools/blender/geno_workbench` into the `scripts/addons` directory for
your Blender version, or create a symlink or directory junction there named
`geno_workbench` pointing to this package. Enable **Geno Workbench** in
Blender's Add-ons preferences.

On Windows, the usual directory is
`%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons`.
Use Blender's Python console to find its configured scripts location:

    import bpy
    print(bpy.utils.user_resource("SCRIPTS", path="addons"))

Open the 3D View sidebar with **N**, then select **Geno**.

1. Set **Project** to the directory containing `workbench.json`.
2. Set **Launcher** if automatic discovery is insufficient. Discovery uses
   `GW_LAUNCHER`, the project's nearest `.git` ancestor, and `PATH`.
3. Click **Start server**, which starts the persistent launcher server with
   headless engine support and fills **Port**.
4. Click **Connect**.

To use an existing Creator hub listener or server, enter its port and click
**Connect**. The host field accepts loopback aliases and normalizes them to
`127.0.0.1`; other hosts are rejected.

**Disconnect** closes the session and stops the launcher process started by
this add-on, if any. Unregistering the add-on performs the same cleanup.
An externally started launcher or hub remains owned by its original caller.

TCP calls use a ten-second timeout. Server startup uses a thirty-second
timeout. Owned-process shutdown uses a one-second terminate wait followed,
if necessary, by a one-second kill wait.

## Playtest

The **Geno > Playtest** panel provides **Play in LAB** and **Play vs CPU** using the current **Project**. Project can be a workbench directory or an artist `fighter.json`. No workbench server connection is needed to launch.

LAB opens the selected Move/row directly in CLIPS; with no selection it opens regular LAB. VS gives you a live level 9 Mario CPU. Both use a fresh run directory and a real-time window. The status reports the log path after launch, and the game continues independently of the add-on.

If authored source is newer than the package, the dialog offers **Rebuild gameplay first**. Accepting reuses cached art; cancelling starts nothing. Changed art or an artist package built before the gameplay-cache support needs a full build first. The async helper keeps Blender responsive during a gameplay rebuild.

Engine, Mods and Disc image settings in Connect also apply to play. Local `.env` disc settings are used when no override is provided. Install Python and Git Bash or set `GW_PYTHON` / `GW_BASH`. A copied add-on locates `tools/geno/play.py` from the selected project's nearest checkout; for an external project, set `GW_ROOT` to its tools workspace.

## Bootstrap without installation

From the workspace root, substitute an existing project directory and the
port of an already running server:

    blender --python tools/blender/geno_workbench/bootstrap.py -- --project "C:/GenoProject" --port 51877

The script adds the package parent to `sys.path`, registers the add-on, sets
the project and port, and connects. When Task 7's `geno_wb.load_fighter`
operator is registered, the script calls it after connecting.

The bootstrap does not start a second server. It can be used with the
persistent server launched by the Creator hub.

## Session API and agent recipes

Send these Python snippets through the Blender MCP's `execute_blender_code`
tool. The snippets require the add-on to be registered and connected:

    import geno_workbench.api as a
    s = a.session()
    assert s.refresh_rows(), s.last_error
    print([row["name"] for row in s.rows])

    import geno_workbench.api as a
    s = a.session()
    assert s.load_row("jab"), s.last_error
    assert s.set_frame(8), s.last_error
    print(s.row, s.frame, s.pose_problem())

    import geno_workbench.api as a
    s = a.session()
    assert s.refresh_hitboxes(), s.last_error
    assert s.run_checks(), s.last_error
    print(s.hitboxes)
    print(s.problems)

For a source edit and subsequent rebuild:

    import geno_workbench.api as a
    s = a.session()
    assert s.load_row("jab"), s.last_error
    assert s.edit_hitbox(ordinal=0, size=4.0), s.last_error
    print(s.status, s.stale)
    if s.stale:
        assert s.rebuild_reload(), s.last_error
    print(s.status)

Every session operation returns a success boolean. Failures populate
`last_error` and `status`. Application errors retain the connection.
Closed, refused, or timed-out connections are marked disconnected and
closed locally. A failed data request preserves the last cached frame.

Data calls accept schema-1 replies for inspection. `pose_problem()` invokes
the shared schema validator and explains why such a reply cannot be posed.
Geometry consumers must check that result before applying a pose.

`edit_hitbox` changes source through the workbench server. It does not
rewrite cached engine hitbox positions. Successful direct edits mark the
session stale and invalidate the source hitbox list; call
`refresh_hitboxes()` to fetch source rows again. Proposal replies show
`proposal created: accept it in the Creator hub` and leave `stale` false,
as specified by the proposal interface.

`rebuild_reload()` rebuilds, reloads, refreshes rows, and restores the selected
row and frame. It clears `stale` after that complete sequence succeeds.
A restoration failure retains the stale marker and the previous cached
frame.

`suggest_bone(ordinal)` stores its reply in `s.suggestion`.
`jointmap` and `calibration` are reserved for the rig and pose integration.
A successful new connection clears frame and rig caches. Disconnecting
preserves cached data for inspection.

The shell injects `props.sync_from_session` as `s.on_change`, so API calls
also update scene status, row, frame, and stale properties. Frame-property
synchronization suppresses its update callback. Task 9 installs its
coalescing scrub callback with `props.set_frame_handler`.

All add-on labels and status templates live in `props.STRINGS`.
`GenoWBProps` is constructed lazily so importing those strings from the
pure session module does not import `bpy`.

## Verification

Run the supplied session tests:

    python -m pytest tools/blender/geno_workbench/tests/test_api.py -q

Run the complete pure-module suite:

    python -m pytest tools/blender/geno_workbench/tests -q

Check package import outside Blender:

    python -c "import sys; sys.path.insert(0,'tools/blender'); import geno_workbench"

Check registration and cleanup in headless Blender:

    blender --background --python-expr "import sys; sys.path.insert(0,'tools/blender'); import geno_workbench as g; g.register(); print('REG', hasattr(__import__('bpy').types.Scene,'geno_wb')); g.unregister()"

The registration command should print `REG True`.

Once Task 8 supplies `selftest.py`, run its synthetic end-to-end test:

    blender --background --python-exit-code 1 --python tools/blender/geno_workbench/selftest.py

The Task 8 self-test and owner-observed live visual checks remain owed.
The pure tests use the synthetic fake workbench and no disc-derived data.


## scipy and Pillow (GW_SITE)

The Splice/NLA features need scipy and Pillow, which Blender's Python lacks.
Install them into a private directory, never globally:

    <blender python> -m pip install --target _build/wbnla-site scipy Pillow

`register()` (so the installed add-on and every launch script alike) calls
`geno_workbench.add_site_dirs()`: it prepends each directory in the `GW_SITE`
environment variable (os.pathsep separated) to `sys.path`; when `GW_SITE` is
unset it uses `<workspace>/_build/wbnla-site` if that directory exists.

## Splice authoring

The **Geno > Splice** panel works without a workbench server. Select the fighter's
export armature in Object Mode, set **Project** to its source project directory
(the one containing workbench.json, splices.json and tools/splice.py), and set
**Source height** to the height used when building that armature.

- **Import clip** accepts an XV2 clip name or a melee:<fighter>/<action> reference.
  It calls xv2_to_artist.splice_context and its resolver, including the existing
  cross-port loader. The source skeleton must match the active armature.
- **Lay out recipe** reads the selected entry from splices.json. **Recipe file**
  can also select splices.authored.json. Each recipe gets one NLA track; laying
  it out again replaces only that recipe's managed track.
- In the NLA Editor, select that track and edit its source strips' crops, reverse,
  scale and spacing. Crop action times are segment-local sample indices. A
  strip's initial scale is the recipe's global retime; stretching it changes
  its effective source speed. Snap timing to whole logic frames before retime.
- **Save strips as recipe** appends a new entry to splices.authored.json beside
  workbench.json, preserving existing entries and adding a numeric suffix on a
  name collision. Entries are AUTHORED and unwired. splices.json is never changed.
- **Bake & export** rebuilds transition poses after structural source-strip edits,
  samples the NLA into one action, then calls the artist exporter's preflight and
  do_export on temporary copies. The editable track survives. AUTHORED is stored
  on the action and in the GLB's Geno sidecar; target rows and hit marks follow it.
  Choose an output GLB in your local generated-assets directory.

A crop with N samples occupies output poses 0 through N-1. Explicit **Hold**
and **Blend** helper strips share endpoint poses with their adjacent segments.
A B-frame blend spans B+1 intervals and inserts B smoothstep/slerp samples;
blend_in/out are zero, so source strikes are never shortened by an overlap.
The project path delegates mirror, yaw, alignment, bone scales, retime and loop
poses to splice.bake. Integer output frames are keyed explicitly after retime.

Helpers are maintained from source-strip timing. Do not independently move,
reverse, mute or remove a helper. Until Bake rebuilds them, helpers may show
old transitions after moving source strips. Overlaps, repeats, animated time,
partial influence and off-grid timings are rejected when saving a recipe.
Free pose/key edits bake visually, but a recipe stores source references and
splice operations, not arbitrary action keys; structural edits regenerate the
sampled actions from source. Keep the .blend for free pose edits.

The source-tools checkout must supply xv2_to_artist.splice_context (as used by
splice.py). Blender's Python needs those tools' NumPy, SciPy and Pillow
dependencies; source IR and cross-port data stay local. The synthetic headless
check below requires none of those source dependencies and writes no game data:

    python -m pytest tools/blender/geno_workbench/tests/test_nla_layout.py -q
    python -m pytest tools/blender/geno_workbench/tests -q
    blender --background --factory-startup --python-exit-code 1 --python tools/blender/geno_workbench/selftest_nla.py

The Blender check must print GENO_WB_CHECK nla OK. Execution and live source
import/export validation are owed to the lead; this packet was authored with
file tools only.

## Open Goku in Blender with one command

    python tools/blender/geno_workbench/launch_goku.py            # interactive Blender
    python tools/blender/geno_workbench/launch_goku.py --check    # background run, prints GENO_WB_REPORT lines
    python tools/blender/geno_workbench/launch_goku.py --row dair --frame 8

`launch_goku.py` starts the Qt launcher's `--serve` session (which starts the headless engine on
the Goku mod with the project's own `mods_dir`), then Blender with `bootstrap.py` (`--art`
`--row` `--frame` `--report`). Paths default to this machine and are overridable by `GW_ROOT`,
`GW_BLENDER`, `GW_LAUNCHER`, `GW_QT_BIN`, `GW_ENGINE_EXE`, `GW_ISO_VANILLA` (read from `.env`).
Closing Blender stops the server and the engine. Blender's splash screen may cover the viewport
until the mouse moves.

## Captain Falcon (Geno Falcon) in Blender

`launch_falcon.py` opens the Workbench on the Geno Falcon fighter (the retail Captain Falcon as a Geno define),
the same way `launch_goku.py` does for Goku. One command, from your own disc, nothing disc-derived committed:

    python tools/blender/geno_workbench/launch_falcon.py            # interactive Blender
    python tools/blender/geno_workbench/launch_falcon.py --check    # background report (rows, bones, pose error, overlays)

First run builds `_build/geno-falcon-art/falcon.blend` (about 35 s, needs the dotnet SDK and network once) with
`falcon/make_falcon_art.py`: HSDRaw (Ploaj/HSDLib, MIT) exports the model (glTF with textures), the skeleton (.smd)
and the 212 animation clips (.smd) through the small driver in `falcon/HsdExport/`; Blender Source Tools
(Artfunkel, GPL-2.0+) imports the skeleton and clips (Blender 5.x has no Collada, so .smd); `falcon/build_blend.py`
skins the meshes to that rig and stores every clip as an Action. Both tools are fetched into `_build/tools-ext/`
and used as external programs. The project is `falcon/project/` (rows = Melee action-state ids with the clip named
in `pick.clip`; `art.bone_aliases` maps plan joints `jN` to bones `JOBJ_N`; `art.calibration_frame` = 10 because
retail rows blend in from the previous pose for the first frames, so frame 1 is not the clip's first frame).
`launch_goku.py` takes `--project/--art/--mods/--work` for any other fighter.
