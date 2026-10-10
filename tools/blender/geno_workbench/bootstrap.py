"""Entry point for blender --python bootstrap.py -- --project P --port N."""

import argparse
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
    parser.add_argument("--row", default="", help="load this move row after the fighter")
    parser.add_argument("--frame", type=int, default=0, help="go to this engine frame after loading the row")
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
    if args.art:
        settings.blender_art = str(Path(args.art).expanduser().resolve())

    result = bpy.ops.geno_wb.connect()
    if "FINISHED" not in result:
        raise RuntimeError(
            api.session().last_error or STRINGS["bootstrap_connect_failed"]
        )

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
    if args.row:
        if args.row not in names:
            raise RuntimeError("row %r not in engine rows %r" % (args.row, names[:20]))
        result = bpy.ops.geno_wb.load_row(row=args.row)
        if "FINISHED" not in result:
            raise RuntimeError(session.last_error or "load_row failed")
        if args.frame:
            bpy.ops.geno_wb.step(n=args.frame - bpy.context.scene.geno_wb.frame)
    if args.report:
        _report(bpy, session, names, args)
    else:
        bpy.app.timers.register(lambda: _present(bpy), first_interval=1.0)


def _present(bpy):
    """Interactive only: drop the startup Cube, frame Goku and his overlays, solid shading."""
    try:
        cube = bpy.data.objects.get("Cube")
        if cube is not None and cube.type == "MESH" and len(cube.data.vertices) == 8:
            bpy.data.objects.remove(cube, do_unlink=True)
        arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type != "VIEW_3D":
                    continue
                region = next(r for r in area.regions if r.type == "WINDOW")
                with bpy.context.temp_override(window=window, area=area, region=region):
                    bpy.ops.object.select_all(action="DESELECT")
                    if arm is not None:
                        arm.select_set(True)
                        bpy.context.view_layer.objects.active = arm
                    bpy.ops.view3d.view_selected()
                    area.spaces.active.clip_end = 100000.0
                    area.spaces.active.show_region_ui = True  # the Geno panel lives in the N sidebar
    except Exception as exc:  # presentation is best effort
        print("GENO_WB_REPORT present_warning %s" % exc)
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
    print("GENO_WB_REPORT status=%s" % session.status)
    _sys.stdout.flush()
    bpy.ops.wm.quit_blender()


if __name__ == "__main__":
    main()
