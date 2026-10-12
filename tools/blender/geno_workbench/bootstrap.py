"""Entry point for blender --python bootstrap.py -- --project P --port N."""

import argparse
import os
from pathlib import Path
import sys


def _script_arguments(argv):
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1:]


def main(argv=None):
    package_parent = str(Path(__file__).resolve().parent.parent)
    if package_parent not in sys.path:
        sys.path.insert(0, package_parent)

    import bpy
    import geno_workbench

    from geno_workbench import api
    from geno_workbench.props import STRINGS

    parser = argparse.ArgumentParser(
        description=STRINGS["bootstrap_description"]
    )
    parser.add_argument(
        "--project",
        required=True,
        help=STRINGS["project_argument"],
    )
    parser.add_argument(
        "--port",
        required=True,
        type=int,
        help=STRINGS["port_argument"],
    )
    parser.add_argument("--art", default="", help="path to the fighter .blend/.glb (sets Blender art)")
    parser.add_argument("--launcher", default="", help="gd-melee-launcher executable (fills the panel's Launcher field)")
    parser.add_argument("--engine", default="", help="melee-pc.exe the server runs (fills the Engine field)")
    parser.add_argument("--mods", default="", help="mods directory (fills the Mods dir field)")
    parser.add_argument("--iso", default="", help="disc image (fills the Disc field; never stored in the repo)")
    parser.add_argument("--row", default="", help="load this move row after the fighter")
    parser.add_argument("--frame", type=int, default=0, help="go to this engine frame after loading the row")
    parser.add_argument("--exercise", default="", help="comma list of rows: play each to its end (and 3 past), switch between them, restart the engine, load again; print GENO_WB_REPORT lines")
    parser.add_argument("--report", action="store_true", help="print GENO_WB_REPORT lines and exit Blender")
    arguments = _script_arguments(sys.argv) if argv is None else argv
    args = parser.parse_args(arguments)

    if not 1 <= args.port <= 65535:
        parser.error(STRINGS["invalid_port"])

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        parser.error(STRINGS["invalid_project"].format(path=project))

    geno_workbench.register()
    settings = bpy.context.scene.geno_wb
    settings.project = str(project)
    settings.host = "127.0.0.1"
    settings.port = args.port
    # The panel's Start server / Restart engine use these; empty fields once spawned a launcher with no engine.
    if args.launcher:
        settings.launcher_exe = str(Path(args.launcher).expanduser())
    if args.engine:
        settings.engine_exe = str(Path(args.engine).expanduser())
    if args.mods:
        settings.mods_dir = str(Path(args.mods).expanduser())
    if args.iso:
        settings.iso_path = str(Path(args.iso).expanduser())
    if args.art:
        settings.blender_art = str(Path(args.art).expanduser().resolve())

    result = bpy.ops.geno_wb.connect()
    if "FINISHED" not in result:
        raise RuntimeError(
            api.session().last_error or STRINGS["bootstrap_connect_failed"]
        )

    # A fresh engine's first row load can report a pose that is not that row's frame 1 (seen on Geno Falcon;
    # the second load is right). Load the first row once so calibration below sees the real reference pose.
    _prime = api.session()
    # (the wait row, never a row the engine cannot pose: the first row of Falcon is Rebirth)
    from geno_workbench import rigmap as _rigmap
    _first = _rigmap.wait_row_name([r for r in getattr(_prime, "rows", []) if isinstance(r, dict)])
    if _first:
        try:
            _prime.load_row(_first)
        except Exception as exc:  # priming is best effort; calibration reports its own failures
            print("GENO_WB_REPORT prime_warning %s" % exc)

    if hasattr(bpy.ops.geno_wb, "load_fighter"):
        load_fighter = bpy.ops.geno_wb.load_fighter
        try:
            load_fighter.get_rna_type()
        except (AttributeError, KeyError, RuntimeError):
            # bpy.ops can fabricate an attribute for an unregistered operator.
            # Task 6 must also work before Task 7 supplies load_fighter.
            return

        result = load_fighter()
        if "FINISHED" not in result:
            raise RuntimeError(
                api.session().last_error or STRINGS["bootstrap_fighter_failed"]
            )
        _after_load(bpy, api, args)


def _after_load(bpy, api, args):
    session = api.session()
    names = [r.get("name") or r.get("row") for r in session.rows if isinstance(r, dict)]

    def resolve(name):
        # a special's row is "side_b (Rush)"; "side_b" alone names it
        if name in names:
            return name
        hits = [n for n in names if isinstance(n, str) and n.startswith(name + " (")]
        return hits[0] if hits else name

    args.row = resolve(args.row) if args.row else args.row
    if args.exercise:
        args.exercise = ",".join(resolve(r) for r in args.exercise.split(",") if r)
    if args.row:
        if args.row not in names:
            raise RuntimeError("row %r not in engine rows %r" % (args.row, names[:20]))
        result = bpy.ops.geno_wb.load_row(row=args.row)
        if "FINISHED" not in result:
            raise RuntimeError(session.last_error or "load_row failed")
        if args.frame:
            bpy.ops.geno_wb.step(n=args.frame - bpy.context.scene.geno_wb.frame)
    if args.exercise:
        _exercise(bpy, session, [r for r in args.exercise.split(",") if r])
    if args.report:
        _report(bpy, session, names, args)
    else:
        bpy.app.timers.register(lambda: _present(bpy), first_interval=1.0)
        driver = os.environ.get("GW_WB_DRIVER", "")
        if driver:   # a measurement/automation script (live_bench.py), run once the window has settled
            bpy.app.timers.register(lambda: _run_driver(driver), first_interval=6.0)


def _run_driver(path):
    import runpy
    import bpy
    try:
        window = bpy.context.window_manager.windows[0]
        for x, y in ((600, 500), (200, 200), (250, 220)):   # a mouse move closes the splash popup
            window.event_simulate(type="MOUSEMOVE", value="NOTHING", x=x, y=y)
        window.event_simulate(type="ESC", value="PRESS", x=250, y=220)
        window.event_simulate(type="ESC", value="RELEASE", x=250, y=220)
    except Exception as exc:
        print("GENO_WB_REPORT splash_warning %s" % exc)
    try:
        runpy.run_path(path)
    except Exception:
        import traceback
        traceback.print_exc()
    return None


def _exercise(bpy, session, rows):
    """Live check of the failures seen on Goku: play past a move's end, switch moves, restart the engine."""
    from geno_workbench import travel

    def root(label):
        info = session.info or {}
        bones = info.get("bones") or []
        top = next((b for b in bones if b.get("parent", -1) == -1), None)
        pos = (top or {}).get("pos") or {}
        shown = travel.in_place(info, session.travel_anchor) if info else {}
        spos = ((shown.get("root") or {}).get("pos")) or {}
        print("GENO_WB_REPORT ex %s row=%s frame=%s connected=%s root=(%.2f,%.2f) in_place=(%.2f,%.2f) status=%s" % (
            label, session.row, session.frame, session.connected, pos.get("x", 0.0), pos.get("y", 0.0),
            spos.get("x", 0.0), spos.get("y", 0.0), session.status))
    for name in rows:
        ok = bpy.ops.geno_wb.load_row(row=name) == {"FINISHED"}
        length = session.row_frames()
        print("GENO_WB_REPORT ex load %s ok=%s length=%s" % (name, ok, length))
        root("loaded")
        for f in list(range(1, (length or 40) + 4)):
            ok = session.set_frame(f)
            if not session.connected:
                print("GENO_WB_REPORT ex DISCONNECTED at frame %d: %s" % (f, session.last_error))
                return
            if f in (1, 2, 8, 20, length, (length or 40) + 3):
                root("f%d ok=%s" % (f, ok))
        print("GENO_WB_REPORT ex learned_length %s=%s" % (name, session.row_lengths.get(name)))
        # Play to the end the way the modal does: step until the row's length, stop (never spin on one frame)
        session.set_frame(1)
        calls = 0
        while True:
            limit = session.row_frames()
            if not limit or session.frame >= limit or calls > (limit or 60) + 5:
                break
            session.step(1)
            calls += 1
        print("GENO_WB_REPORT ex play %s end_frame=%s limit=%s step_calls=%d" % (name, session.frame, session.row_frames(), calls))
    # switch back and forth, root should be stable per row start
    for name in rows + rows[::-1]:
        bpy.ops.geno_wb.load_row(row=name)
        session.set_frame(1)
        root("switch %s f1" % name)
    ok = session.engine_restart()
    print("GENO_WB_REPORT ex restart ok=%s status=%s" % (ok, session.status))
    ok = bpy.ops.geno_wb.load_row(row=rows[0]) == {"FINISHED"}
    root("after restart load %s ok=%s" % (rows[0], ok))


def _present(bpy):
    """Interactive only: drop the startup Cube, then a clean first view of Goku.

    The mesh is framed (not the armature, whose stray bones would shrink him), seen from an angled
    perspective, with the armature behind the mesh instead of drawn over it and the hurtbox wires pale.
    """
    import math
    try:
        cube = bpy.data.objects.get("Cube")
        if cube is not None and cube.type == "MESH" and len(cube.data.vertices) == 8:
            bpy.data.objects.remove(cube, do_unlink=True)
        arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
        meshes = [o for o in bpy.data.objects if o.type == "MESH" and arm is not None and o.parent == arm]
        if arm is not None:
            arm.show_in_front = False       # bones hide behind the mesh instead of striping it
            arm.data.display_type = "STICK"
            # Helper sockets (grab_anchor holds the victim 5 units in front of the chest) are real joints but
            # draw as a bone as long as the torso standing apart from Goku. Hide them in the viewport only;
            # they are still posed and still map to the engine.
            for bone in arm.data.bones:
                if bone.name == "grab_anchor" or bone.name.startswith("item_socket"):
                    bone.hide = True
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type != "VIEW_3D":
                    continue
                region = next(r for r in area.regions if r.type == "WINDOW")
                space = area.spaces.active
                with bpy.context.temp_override(window=window, area=area, region=region):
                    bpy.ops.object.select_all(action="DESELECT")
                    for obj in meshes or ([arm] if arm is not None else []):
                        obj.select_set(True)
                    if arm is not None:
                        bpy.context.view_layer.objects.active = arm
                    space.region_3d.view_perspective = "PERSP"
                    space.region_3d.view_rotation = __import__("mathutils").Euler(
                        (math.radians(78), 0.0, math.radians(-35)), "XYZ").to_quaternion()
                    bpy.ops.view3d.view_selected()
                    space.clip_end = 100000.0
                    space.shading.type = "SOLID"
                    space.shading.show_xray = False
                    space.shading.color_type = "TEXTURE"   # textures without Material Preview's cost
                    space.overlay.show_extras = True
                    space.show_region_ui = True  # the Geno panel lives in the N sidebar
                    bpy.ops.object.select_all(action="DESELECT")
                    if arm is not None:
                        arm.select_set(True)
    except Exception as exc:  # presentation is best effort
        print("GENO_WB_REPORT present_warning %s" % exc)
    try:
        from geno_workbench import geno_workspace
        geno_workspace.on_session_ready()
    except Exception as exc:  # the Geno tab is a convenience
        print("GENO_WB_REPORT geno_workspace_warning %s" % exc)
    shot = os.environ.get("GW_WB_SHOT", "")
    if shot:
        # Blender's own screenshot of its window (no desktop capture); GW_WB_SHOT=path.png, then it quits
        def dismiss():
            try:   # a mouse move closes the splash popup that otherwise sits over the viewport
                window = bpy.context.window_manager.windows[0]
                for x, y in ((600, 500), (200, 200), (250, 220)):
                    window.event_simulate(type="MOUSEMOVE", value="NOTHING", x=x, y=y)
            except Exception as exc:
                print("GENO_WB_REPORT splash_warning %s" % exc)
            return None

        def take():
            try:
                for window in bpy.context.window_manager.windows:
                    with bpy.context.temp_override(window=window):
                        bpy.ops.screen.screenshot(filepath=shot)
                    print("GENO_WB_REPORT screenshot %s" % shot)
                    area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), None)
                    if area is not None:   # the viewport alone, without any popup drawn over it
                        region = next(r for r in area.regions if r.type == "WINDOW")
                        with bpy.context.temp_override(window=window, area=area, region=region):
                            bpy.ops.screen.screenshot_area(filepath=shot.replace(".png", "_view.png"))
                    break
            except Exception as exc:
                print("GENO_WB_REPORT screenshot_error %s" % exc)
            if os.environ.get("GW_WB_SHOT_QUIT"):
                bpy.ops.wm.quit_blender()
            return None
        bpy.app.timers.register(dismiss, first_interval=3.0)
        bpy.app.timers.register(dismiss, first_interval=4.0)
        bpy.app.timers.register(take, first_interval=7.0)
    return None


def _report(bpy, session, names, args):
    import sys as _sys
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    info = session.info or {}
    coll = bpy.data.collections.get("GenoWB Overlays")
    kinds = {}
    for o in (coll.all_objects if coll else []):
        k = o.name.split(".")[0].split("_")[0]
        kinds[k] = kinds.get(k, 0) + 1
    try:
        bpy.ops.geno_wb.verify_pose()
    except Exception as exc:  # report, do not hide
        print("GENO_WB_REPORT verify_pose_error %s" % exc)
    print("GENO_WB_REPORT rows=%d row=%s frame=%s" % (len(names), args.row, info.get("frame")))
    print("GENO_WB_REPORT armature=%s bones=%d meshes=%d" % (
        arm.name if arm else None, len(arm.data.bones) if arm else 0,
        sum(1 for o in bpy.data.objects if o.type == "MESH" and o.parent == arm)))
    print("GENO_WB_REPORT engine bones=%d hitboxes=%d hurtboxes=%d schema=%s" % (
        len(info.get("bones", [])), len(info.get("hitboxes", [])), len(info.get("hurtboxes", [])), info.get("schema")))
    print("GENO_WB_REPORT overlay_objects=%s pose_error=%s" % (kinds, bpy.context.scene.geno_wb.pose_error))
    if arm is not None:
        # bones far from the body (a stray one sits apart from Goku): name, parent, head/tail in world space
        import statistics
        mw = arm.matrix_world
        posed = {pb.name: (mw @ pb.head, mw @ pb.tail) for pb in arm.pose.bones}
        if posed:
            med = [statistics.median(h[i] for h, _t in posed.values()) for i in range(3)]
            def dist(v):
                return sum((v[i] - med[i]) ** 2 for i in range(3)) ** 0.5
            def blen(n):
                return (posed[n][1] - posed[n][0]).length
            meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm]
            if meshes:
                pts = [meshes[0].matrix_world @ __import__("mathutils").Vector(c) for c in meshes[0].bound_box]
                lo = [min(p[i] for p in pts) for i in range(3)]
                hi = [max(p[i] for p in pts) for i in range(3)]
                print("GENO_WB_REPORT mesh_bbox lo=(%.1f,%.1f,%.1f) hi=(%.1f,%.1f,%.1f)" % (*lo, *hi))
                for n, (h, t) in posed.items():
                    out = [i for i in range(3) if max(h[i], t[i]) > hi[i] + 1.0 or min(h[i], t[i]) < lo[i] - 1.0]
                    if out:
                        print("GENO_WB_REPORT outside_bone %s parent=%s axes=%s head=(%.1f,%.1f,%.1f) tail=(%.1f,%.1f,%.1f)" % (
                            n, arm.data.bones[n].parent.name if arm.data.bones[n].parent else None, out, *h, *t))
            for n in sorted(posed, key=lambda k: -max(dist(posed[k][0]), dist(posed[k][1]), blen(k)))[:4]:
                b = arm.data.bones[n]
                print("GENO_WB_REPORT far_bone %s parent=%s dist_head=%.2f dist_tail=%.2f len=%.2f head=(%.2f,%.2f,%.2f)" % (
                    n, b.parent.name if b.parent else None, dist(posed[n][0]), dist(posed[n][1]), blen(n), *posed[n][0]))
    missing = []
    for img in bpy.data.images:
        if img.source in ("FILE", "SEQUENCE", "MOVIE") and not img.packed_file:
            path = bpy.path.abspath(img.filepath)
            if not img.has_data and not (path and os.path.isfile(path)):
                missing.append("%s -> %s" % (img.name, path))
    print("GENO_WB_REPORT images=%d missing=%d %s" % (len(bpy.data.images), len(missing), missing[:8]))
    print("GENO_WB_REPORT status=%s" % session.status)
    _sys.stdout.flush()
    bpy.ops.wm.quit_blender()


if __name__ == "__main__":
    main()
