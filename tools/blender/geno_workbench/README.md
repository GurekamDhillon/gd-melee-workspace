# Geno Workbench Blender add-on

Geno Workbench requires Blender 4.x. Its pure Python modules use the standard
library. The add-on communicates with the workbench server at `127.0.0.1`;
project edits are workbench tool calls.

This Task 6 shell provides connection controls, scene properties, and the
session API. Rig loading, posing, overlays, timeline controls, and editing
panels arrive in their respective later tasks.

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
