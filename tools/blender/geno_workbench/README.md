# Geno Workbench Blender add-on

**Current as of 2026-10-10; source-checked, not visually exercised for this docs update.**
Geno Workbench is a local fighter viewer and source editor with live engine poses,
overlays, row selection, playback, checks and a Fighter loading/calibration panel.
Use Blender 4.2+ for the artist workflow (the Workbench add-on metadata declares
4.0 as its minimum). Its core session modules use the standard library; source
Splice/NLA imports additionally need NumPy, SciPy and Pillow.

For the whole original-fighter path, start with
[Author a fighter](../../../docs/learn/author-a-fighter.md).
An artist starter does not automatically have an editable Workbench project.
The tutorial supplies a playback project and explains the source adapter still
needed for hitbox editing.

## Install

Copy `tools/blender/geno_workbench` into your Blender version's `scripts/addons`
directory, or create a symlink/directory junction there named `geno_workbench`
pointing to this package. Enable **Geno Workbench** in Blender's Add-ons
preferences. Use Blender's Python console to find the configured directory:

```python
import bpy
print(bpy.utils.user_resource("SCRIPTS", path="addons"))
```

Open the 3D View sidebar with **N**, then select **Geno**.

1. In **Connect**, set **Project** to the directory containing `workbench.json`.
2. Set **Launcher** if discovery is insufficient. It uses `GW_LAUNCHER`, built
   launchers under the workspace's `_build/`, then PATH.
3. Set **Engine exe**, **Mods dir** (the mods parent) and **Disc image**, or
   launch Blender with their environment overrides below.
4. Click **Start server**. It starts the persistent launcher and a headless
   engine when one is configured, then fills **Port**.
5. Click **Connect** to read the project rows. Choose **Timeline > Move**.
6. In **Fighter**, set **Art override** if needed, then **Load Fighter**.
   It imports local art and calibrates the joint mapping. **Calibrate** repeats
   that operation; **Verify Pose** reports position/rotation errors and missing
   or mirrored joints.

A server without an engine can expose source data, but cannot supply live poses.
Use a separate preview scene and keep your authoring blend saved independently.

To use an existing Creator hub listener/server, enter its port and click
**Connect**. Only loopback hosts are accepted and normalized to `127.0.0.1`.
**Start server** reports when it reuses a listener already on that port; check
that listener is serving the intended project.

**Disconnect** closes the session and stops the launcher this add-on started,
if any. Unregistering performs the same cleanup. An externally started launcher
or hub remains owned by its original caller.

Normal TCP calls have a ten-second timeout. Rebuild calls allow 2,000 s;
reload/restart allow 300 s. The launcher caps a build at 30 minutes.
The sidebar and launch helper allow 120 s for server startup. These are timeout
budgets, not expected durations.

## Panels and the edit loop

| Panel | Current controls |
|---|---|
| Connect | Project and executable/mods/disc fields; Start server, Connect, Disconnect, Restart engine; status |
| Timeline | Move dropdown/refresh, Frame, -1/+1, Play/Pause, Speed, Loop, Show travel, cache progress |
| Fighter | Load Fighter, Calibrate, Verify Pose, art/armature and mapping diagnostics |
| Hitbox | Source hitbox list; Bone, Damage, Size, offsets, angle/knockback and frame fields; Suggest limb, Apply, Rebuild + reload |
| Problems | Run checks, results and Go to problem |
| Splice | Import clip, Lay out recipe, Save strips as recipe, Bake & export |

Timeline frames are engine logic frames, independent of Blender's scene timeline.
The UI caps the frame at 600; **>|** goes to that cap, not the move's last frame.
Playback uses the known row length for stopping/looping. **Speed** includes
1x (60 logic frames/s), 0.5x, 0.25x and Scene fps. **Show travel** includes the
engine's world movement; off keeps the pose at its starting position.

An editable project needs each gameplay row's `script` to name maintained source
and a `rebuild` argv that actually packages it. **Apply** writes that source.
It shows a rebuild-needed banner; engine overlays still show the previous build.
**Run checks** inspects source/engine samples; **Rebuild + reload** builds,
restarts the engine process, then restores the selected row/frame and refetches
poses and source hitboxes. Run checks again on the new build.

**New, intended flow:** a role dropdown and **Add/Delete** hitbox controls are
being built. They are not present in the source checked for this update.
The current **Bone** field is text; **Suggest limb** fills it and **Apply** saves.
See the tutorial for the intended clicks and the current artist JSON fallback.

Disabled controls depend on their preconditions: connection/frame, a role map in
the plan, selected source hitbox, or nonempty `workbench.json.rebuild`.
Read the panel explanation and status. An empty Problems list before
**Run checks** is not a passing result. Missing source hitboxes can mean a
playback-only project, even when the live move has hitboxes.

**Restart engine** does not build. Native define fighters cannot use F8 /
`gd.hot_reload()`: they require a process restart. A match restart also keeps
the cached animation bank. For the Goku driver, `--auto` chooses gameplay-only
for current art and a full build otherwise; the artist CLI has no such flag.
The large-bank full build was measured at 278–295 s; its gameplay-only loop was
reported at about 15 s, not remeasured here. Evidence and limits:
[hot-reload measurements](../../../_research/hot-reload-2026-10-10.md#measurements-2026-10-10-measurement-lane-no-code-changed).

## Environment settings

These settings are local; executable and disc paths do not belong in public docs
or a shared project. The installed add-on inherits its environment; it does not
read `.env` itself. Use the pickers when Blender was started without these values.

| Variable | Used for |
|---|---|
| `GW_LAUNCHER` | Launcher executable discovery |
| `GW_ENGINE_EXE` | Engine executable for Start server |
| `GW_MODS_DIR` | Mods parent for Start server |
| `GW_ISO_VANILLA` | Disc image, passed to the engine as `MELEE_ISO` |
| `GW_QT_BIN` | Qt runtime directory prepended to the server's PATH |
| `GW_BLENDER` | Blender executable for the hub/launch helpers |
| `GW_ROOT` | Workspace root override in the Goku launch helper |
| `GW_WB_WORK` | Work directory override in the Goku launch helper |
| `GW_SITE` | Extra Python package directories for Splice/NLA |
| `BLENDER` | Artist CLI's separate Blender executable override |

The hub's **Open in Blender** uses its Settings path, then `GW_BLENDER`, then
PATH. It currently finds the add-on through a repository ancestor, so a release
directory alone does not supply it. Use the bootstrap or an installed add-on
for your own configured session.

## Bootstrap without installation

From the workspace root, substitute your project and an existing server's port:

```bash
blender --python tools/blender/geno_workbench/bootstrap.py -- --project authoring/my-fighter --port 51877
```

The script adds the package parent to `sys.path`, registers the add-on, connects
and calls `geno_wb.load_fighter`. `--art` overrides the local blend/GLB;
`--row` and `--frame` select a move and engine frame after loading.
It does not start a second server. The tutorial shows the existing launch
helper's project/art/mods/work overrides for starting both server and Blender.

## Session API and agent recipes

Send these Python snippets through the Blender MCP's `execute_blender_code`
tool. The snippets require the add-on to be registered and connected. The `jab1`
examples use the Goku project; for another project, use a name returned by
`refresh_rows()` rather than a clip name or engine display label:

    import geno_workbench.api as a
    s = a.session()
    assert s.refresh_rows(), s.last_error
    print([row["name"] for row in s.rows])

    import geno_workbench.api as a
    s = a.session()
    assert s.load_row("jab1"), s.last_error
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
    assert s.load_row("jab1"), s.last_error
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

The add-on injects `props.sync_from_session` as `s.on_change`, so API calls
also update scene status, row, frame, and stale properties. Frame-property
synchronization suppresses its update callback. The timeline installs its
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

Run the supplied synthetic end-to-end self-test:

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
`--row` `--frame` `--report`). Paths use [the shared authoring-tool config](../../port/TOOLS_CONFIG.md): `.env`/`GW_*`,
the git-ignored `_build/tools.json`, then discovery. This covers modern Blender, the separate
Blender 3.5.1 path, launcher, Qt bin, engine and all three disc paths. Run
`python tools/port/tools_config.py --detect --check` to configure and list missing items.
The launch scripts and add-on use the same resolver; an installed add-on needs `GW_ROOT`.
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
`launch_goku.py` accepts `--project`, `--art`, `--mods` and `--work` for another
configured fighter project. Those overrides do not create its source/build adapter.
